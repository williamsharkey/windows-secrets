/*
 *  BSYN: the "BASILISK 16" sound card, an emulated multi-voice wave-output card for Windows 3.11.
 *
 *  Windows 3.11's Sound Blaster driver plays one sound at a time; a second Sound Recorder pressing Play gets
 *  "device in use". This card has 32 independent wave voices (like a Gravis Ultrasound): its Windows driver
 *  (BSYNTH.DRV, a normal Win16 wave driver) opens one voice per waveOutOpen, so sixteen Sound Recorders can play
 *  at once. Each voice reads the PCM that Sound Recorder hands to waveOutWrite (8 or 16 bit, mono or stereo, any
 *  rate), and plays it through its own sample-rate converter (4-point Hermite) at the card's output rate, with a
 *  per-voice playback rate (waveOutSetPlaybackRate) and volume (waveOutSetVolume), into a 48 kHz stereo DAC.
 *
 *  The DAC's samples are numbered from power-on. The host (the BASILISK synth plugin) reads the DAC stream and
 *  can attach a DAC sample number to each MIDI event it hands the guest; when the guest synth program "arms" a
 *  voice with that event id before pressing Play (or Stop), the card starts (or fades) that voice exactly at that
 *  sample: a fixed latency instead of jitter. Without an armed id a voice starts at once, as on real hardware.
 *
 *  Ports (16 bit): base+0 write = push argument, read = pop result; base+2 write = command; base+4 read = 'BS'.
 */
#include "dosbox.h"
#include "inout.h"
#include "mixer.h"
#include "paging.h"
#include "pic.h"
#include "setup.h"
#include "cpu.h"
#include <math.h>
#include <string.h>
#include <mutex>
#include <vector>
#include <deque>
#include <stdio.h>
#include <stdlib.h>

#define BS_BASE 0x2C0
#define BS_CH 32
#define BS_RATE 48000
#define BS_FADE 240          /* 5 ms declick at stop/steal */
static Bit32u late_n, late_max, ontime_n;   /* scheduling statistics: armed starts/stops that came too late */

struct BSBuf { std::vector<Bit8u> data; Bit32u cookie; Bit32u frames; };
struct BSVoice {
	bool on;               /* producing sound (or waiting for its start sample) */
	Bit8u nch, bits;       /* source format */
	Bit32u srate;          /* source rate */
	float rate;            /* playback-rate multiplier (driver) */
	float armrate;         /* multiplier from the arm (pitch) */
	float voll, volr, gain;
	Bit64u start_at;       /* DAC sample at which it starts */
	Bit64u stop_at;        /* DAC sample at which it starts fading out (~0 = never) */
	Bit32u fade_len;       /* fade length in samples */
	Bit32u fade_left;      /* samples left in the fade (0 = not fading) */
	double pos;            /* position in the front buffer, source frames */
	Bit32u played;         /* source frames played, for GETPOS */
	bool paused;
	std::deque<BSBuf> q;
	std::vector<Bit32u> done;  /* cookies of buffers finished (for POLLDONE) */
	Bit32u voice_id;       /* armed event id, for reports */
	Bit32u env_a, env_d;   /* envelope: attack and decay in samples */
	float env_s;           /* sustain level */
	Bit64u age;            /* samples played since start (for the envelope) */
	int owner;             /* logical channel that owns it, -1 = ghost (fading after reset) */
};

static struct {
	std::mutex mtx;
	std::vector<Bit16u> args, results;
	BSVoice v[BS_CH * 2];          /* first BS_CH: logical channels; rest: ghosts */
	bool chopen[BS_CH];
	Bit16u chtask[BS_CH];
	Bit64u dac;                    /* DAC samples produced so far */
	/* arms: task -> (event id, rate, gain) for the next open / stop by that task */
	struct Arm { Bit16u task; Bit32u id; Bit32u hz; float gain; Bit32u fade; bool stop; bool used; } arms[64];
	Bit32u env_a, env_d; float env_s;   /* the envelope new voices get (ENV) */
	/* host -> guest events, guest -> host reports */
	std::deque<Bit16u> events, reports;
	/* event id -> DAC sample (target) */
	Bit32u tgt_id[4096]; Bit64u tgt_at[4096];
	float master;                  /* master pitch multiplier (pitch bend) */
	/* DAC output ring for the host */
	float *ring; Bit32u ring_len; Bit64u ring_w;
	MixerChannel *chan; MixerObject *mo;
} bs;

#ifdef _WIN32
#define BSYN_API __declspec(dllexport)
#else
#define BSYN_API __attribute__((visibility("default")))
#endif
extern "C" {
/* ------------------------------------------------------------------ host API (called by the frontend) */
BSYN_API void bsyn_host_event(const Bit16u *w, int n, Bit32u id, Bit64u at)
{
	std::lock_guard<std::mutex> l(bs.mtx);
	if (id) { bs.tgt_id[id & 4095] = id; bs.tgt_at[id & 4095] = at; }
	for (int i = 0; i < n; i++) bs.events.push_back(w[i]);
}
BSYN_API int bsyn_host_reports(Bit16u *w, int max)
{
	std::lock_guard<std::mutex> l(bs.mtx);
	int n = 0;
	while (n < max && !bs.reports.empty()) { w[n++] = bs.reports.front(); bs.reports.pop_front(); }
	return n;
}
BSYN_API Bit64u bsyn_host_dac(void) { return bs.ring_w; }
/* copy DAC samples [from, from+n) (stereo float) if still in the ring; returns how many were available */
BSYN_API int bsyn_host_read(Bit64u from, float *out, int n)
{
	std::lock_guard<std::mutex> l(bs.mtx);
	if (!bs.ring) return 0;
	int got = 0;
	for (; got < n; got++) {
		Bit64u s = from + got;
		if (s >= bs.ring_w || s + bs.ring_len <= bs.ring_w) break;
		Bit32u i = (Bit32u)(s % bs.ring_len);
		out[got * 2] = bs.ring[i * 2]; out[got * 2 + 1] = bs.ring[i * 2 + 1];
	}
	return got;
}
BSYN_API void bsyn_host_stats(Bit32u *ontime, Bit32u *late, Bit32u *latemax)
{
	*ontime = ontime_n; *late = late_n; *latemax = late_max;
}
BSYN_API int bsyn_host_active(void)
{
	std::lock_guard<std::mutex> l(bs.mtx);
	int n = 0;
	for (int i = 0; i < BS_CH * 2; i++) if (bs.v[i].on) n++;
	return n;
}
}

static float sample_at(const BSVoice &v, const BSBuf &b, Bit32s frame, int c)
{
	/* frame may run past this buffer: look into the next queued buffers (seamless across waveOutWrites) */
	const BSBuf *bb = &b; size_t qi = 0;
	while (frame >= (Bit32s)bb->frames) { frame -= bb->frames; if (++qi >= v.q.size()) return 0.f; bb = &v.q[qi]; }
	if (frame < 0) return 0.f;
	int ch = (v.nch == 2 ? c : 0);
	if (v.bits == 16) { const Bit16s *p = (const Bit16s *)&bb->data[0]; return p[frame * v.nch + ch] / 32768.f; }
	return ((int)bb->data[frame * v.nch + ch] - 128) / 128.f;
}

static void voice_finish_front(BSVoice &v)
{
	BSBuf &b = v.q.front();
	v.played += b.frames;
	v.pos -= b.frames;
	if (v.owner >= 0) v.done.push_back(b.cookie);
	v.q.pop_front();
}

static void render(float *out, Bitu len)
{
	memset(out, 0, len * 2 * sizeof(float));
	for (int vi = 0; vi < BS_CH * 2; vi++) {
		BSVoice &v = bs.v[vi];
		if (!v.on || v.paused) continue;
		double step = (double)v.srate * v.rate * v.armrate * bs.master / BS_RATE;
		float gl = v.voll * v.gain, gr = v.volr * v.gain;
		for (Bitu s = 0; s < len; s++) {
			Bit64u t = bs.dac + s;
			if (t < v.start_at) continue;
			if (v.q.empty()) { if (v.owner < 0) v.on = false; break; }
			float fg = 1.f;
			if (t >= v.stop_at) {
				if (!v.fade_left) { v.fade_left = v.fade_len ? v.fade_len : 1; v.stop_at = 0; }
			}
			if (v.fade_left) {
				fg = (float)v.fade_left / (float)(v.fade_len ? v.fade_len : 1);
				if (--v.fade_left == 0) { v.on = false; v.q.clear(); break; }
			}
			if (v.env_a || v.env_d || v.env_s < 1.f) {
				float eg;
				if (v.age < v.env_a) eg = (float)v.age / (float)v.env_a;
				else if (v.age < (Bit64u)v.env_a + v.env_d) eg = 1.f - (1.f - v.env_s) * (float)(v.age - v.env_a) / (float)v.env_d;
				else eg = v.env_s;
				fg *= eg;
			}
			v.age++;
			BSBuf &b = v.q.front();
			Bit32s i = (Bit32s)floor(v.pos); float f = (float)(v.pos - i);
			for (int c = 0; c < 2; c++) {
				float y0 = sample_at(v, b, i - 1, c), y1 = sample_at(v, b, i, c), y2 = sample_at(v, b, i + 1, c), y3 = sample_at(v, b, i + 2, c);
				/* 4-point, 3rd-order Hermite */
				float c1 = 0.5f * (y2 - y0), c2 = y0 - 2.5f * y1 + 2.f * y2 - 0.5f * y3, c3 = 0.5f * (y3 - y0) + 1.5f * (y1 - y2);
				float y = ((c3 * f + c2) * f + c1) * f + y1;
				out[s * 2 + c] += y * (c ? gr : gl) * fg;
			}
			v.pos += step;
			while (!v.q.empty() && v.pos >= v.q.front().frames) voice_finish_front(v);
		}
		if (v.on && v.q.empty() && v.owner < 0) v.on = false;
	}
}

static void BSYN_CallBack(Bitu len)
{
	static std::vector<float> tmp; static std::vector<Bit16s> pcm;
	if (tmp.size() < len * 2) { tmp.resize(len * 2); pcm.resize(len * 2); }
	{
		std::lock_guard<std::mutex> l(bs.mtx);
		render(&tmp[0], len);
		for (Bitu s = 0; s < len; s++) {
			Bit32u i = (Bit32u)((bs.ring_w + s) % bs.ring_len);
			bs.ring[i * 2] = tmp[s * 2]; bs.ring[i * 2 + 1] = tmp[s * 2 + 1];
		}
		bs.ring_w += len;
		bs.dac += len;
	}
	for (Bitu s = 0; s < len * 2; s++) { float x = tmp[s] * 32767.f; pcm[s] = (Bit16s)(x > 32767.f ? 32767 : x < -32768.f ? -32768 : x); }
	bs.chan->AddSamples_s16(len, &pcm[0]);
}

static Bit16u arg(size_t i) { return i < bs.args.size() ? bs.args[i] : 0; }
static Bit32u arg32(size_t i) { return arg(i) | ((Bit32u)arg(i + 1) << 16); }

static BSBuf read_guest(Bit32u lin, Bit32u len, bool &ok)
{
	BSBuf b; b.data.resize(len); ok = true;
	for (Bit32u i = 0; i < len; i++) if (mem_readb_checked(lin + i, &b.data[i])) { ok = false; break; }
	return b;
}

static int find_arm(Bit16u task, bool stop)
{
	for (int i = 0; i < 64; i++) if (bs.arms[i].used && bs.arms[i].task == task && bs.arms[i].stop == stop) return i;
	return -1;
}
static Bit64u target_of(Bit32u id)
{
	if (id && bs.tgt_id[id & 4095] == id) {
		Bit64u at = bs.tgt_at[id & 4095];
		if (at > bs.dac) { ontime_n++; return at; }
		late_n++; if (bs.dac - at > late_max) late_max = (Bit32u)(bs.dac - at);
	}
	return bs.dac;
}

/* move a logical channel's sound to a ghost voice that keeps playing until its stop sample, then fades */
static void ghost(int ch, Bit64u stop_at, Bit32u fade)
{
	BSVoice &v = bs.v[ch];
	if (v.on && !v.q.empty()) {
		for (int g = BS_CH; g < BS_CH * 2; g++) if (!bs.v[g].on) {
			bs.v[g] = v; bs.v[g].owner = -1; bs.v[g].done.clear();
			bs.v[g].stop_at = stop_at; bs.v[g].fade_len = fade ? fade : BS_FADE; bs.v[g].fade_left = 0;
			break;
		}
	}
	/* every queued buffer is now "done" for Windows */
	for (auto &b : v.q) v.done.push_back(b.cookie);
	v.q.clear(); v.on = false; v.pos = 0;
}

static int trace = -1;
static void command(Bit16u c)
{
	std::lock_guard<std::mutex> l(bs.mtx);
	if (trace < 0) trace = getenv("BSYN_TRACE") ? atoi(getenv("BSYN_TRACE")) : 0;
	if (trace && c != 20 && c != 26 && (c != 5 || trace > 1)) { fprintf(stderr, "bsyn %llu cmd %d:", (unsigned long long)bs.dac, c); for (Bit16u a : bs.args) fprintf(stderr, " %04x", a); fprintf(stderr, "\n"); }
	bs.results.clear();
	switch (c) {
	case 1: { /* OPEN task nch bits rate_lo rate_hi -> ch */
		int ch = -1;
		for (int i = 0; i < BS_CH; i++) if (!bs.chopen[i] && !bs.v[i].on) { ch = i; break; }
		if (ch < 0) for (int i = 0; i < BS_CH; i++) if (!bs.chopen[i]) { ch = i; break; }
		if (ch < 0) { bs.results.push_back(0xFFFF); break; }
		BSVoice &v = bs.v[ch];
		v = BSVoice(); v.owner = ch;
		v.nch = (Bit8u)arg(1); v.bits = (Bit8u)arg(2); v.srate = arg32(3);
		v.rate = 1.f; v.armrate = 1.f; v.voll = v.volr = 1.f; v.gain = 1.f; v.stop_at = ~(Bit64u)0;
		bs.chopen[ch] = true; bs.chtask[ch] = arg(0);
		int a = find_arm(arg(0), false);
		v.start_at = bs.dac;
		v.env_a = 0; v.env_d = 0; v.env_s = 1.f; v.age = 0;
		if (a >= 0) {
			v.voice_id = bs.arms[a].id; v.start_at = target_of(bs.arms[a].id);
			v.armrate = (bs.arms[a].hz && v.srate) ? (float)bs.arms[a].hz / (float)v.srate : 1.f;
			v.gain = bs.arms[a].gain; bs.arms[a].used = false;
			v.env_a = bs.env_a; v.env_d = bs.env_d; v.env_s = bs.env_s;
		}
		if (trace) fprintf(stderr, "bsyn open ch%d task %04x arm %d id %u start %llu dac %llu tgt_id %u tgt_at %llu\n", ch, arg(0), a, v.voice_id,
			(unsigned long long)v.start_at, (unsigned long long)bs.dac, a >= 0 ? bs.tgt_id[v.voice_id & 4095] : 0, a >= 0 ? (unsigned long long)bs.tgt_at[v.voice_id & 4095] : 0ULL);
		bs.results.push_back((Bit16u)ch);
		break; }
	case 2: { /* CLOSE ch */
		int ch = arg(0) & (BS_CH - 1);
		ghost(ch, bs.dac, 0);
		bs.chopen[ch] = false;
		break; }
	case 3: { /* WRITE ch lin_lo lin_hi len_lo len_hi cookie_lo cookie_hi -> 1 ok / 0 */
		int ch = arg(0) & (BS_CH - 1);
		BSVoice &v = bs.v[ch];
		bool ok; BSBuf b = read_guest(arg32(1), arg32(3), ok);
		if (!ok) { bs.results.push_back(0); break; }
		b.cookie = arg32(5);
		b.frames = (Bit32u)(b.data.size() / (v.nch * (v.bits / 8)));
		if (!b.frames) { v.done.push_back(b.cookie); bs.results.push_back(1); break; }
		if (!v.on) { v.on = true; if (v.start_at < bs.dac) v.start_at = bs.dac; }
		v.q.push_back(b);
		bs.results.push_back(1);
		break; }
	case 4: { /* RESET ch: stop (at the armed stop sample, if the task armed one), return all buffers */
		int ch = arg(0) & (BS_CH - 1);
		Bit64u at = bs.dac; Bit32u fade = 0;
		int a = find_arm(bs.chtask[ch], true);
		if (a >= 0) { at = target_of(bs.arms[a].id); fade = bs.arms[a].fade; bs.arms[a].used = false; }
		ghost(ch, at, fade);
		bs.v[ch].played = 0;
		break; }
	case 5: { /* POLLDONE -> n, then (ch, cookie_lo, cookie_hi) * n; at most 20 */
		int n = 0; bs.results.push_back(0);
		for (int ch = 0; ch < BS_CH && n < 20; ch++) {
			BSVoice &v = bs.v[ch];
			while (!v.done.empty() && n < 20) {
				Bit32u ck = v.done.front(); v.done.erase(v.done.begin());
				bs.results.push_back((Bit16u)ch); bs.results.push_back((Bit16u)ck); bs.results.push_back((Bit16u)(ck >> 16)); n++;
			}
		}
		bs.results[0] = (Bit16u)n;
		if (trace && n) fprintf(stderr, "bsyn %llu done x%d\n", (unsigned long long)bs.dac, n);
		break; }
	case 6: { /* GETPOS ch -> frames lo hi */
		BSVoice &v = bs.v[arg(0) & (BS_CH - 1)];
		Bit32u p = v.played + (v.on && bs.dac >= v.start_at ? (Bit32u)v.pos : 0);
		bs.results.push_back((Bit16u)p); bs.results.push_back((Bit16u)(p >> 16));
		break; }
	case 7: bs.v[arg(0) & (BS_CH - 1)].paused = true; break;
	case 8: bs.v[arg(0) & (BS_CH - 1)].paused = false; break;
	case 9: { BSVoice &v = bs.v[arg(0) & (BS_CH - 1)]; v.voll = arg(1) / 65535.f; v.volr = arg(2) / 65535.f; break; }
	case 10: bs.v[arg(0) & (BS_CH - 1)].rate = arg32(1) / 65536.f; break;
	case 11: { BSVoice &v = bs.v[arg(0) & (BS_CH - 1)]; bs.results.push_back((Bit16u)(v.voll * 65535)); bs.results.push_back((Bit16u)(v.volr * 65535)); break; }
	case 12: { Bit32u r = (Bit32u)(bs.v[arg(0) & (BS_CH - 1)].rate * 65536); bs.results.push_back((Bit16u)r); bs.results.push_back((Bit16u)(r >> 16)); break; }

	case 20: { /* EVPOLL -> one event: n words (0 = none), then the words */
		if (bs.events.empty()) { bs.results.push_back(0); break; }
		Bit16u n = bs.events.front() & 0xFF; if (!n) n = 1;
		bs.results.push_back(n);
		for (int i = 0; i < n && !bs.events.empty(); i++) { bs.results.push_back(bs.events.front()); bs.events.pop_front(); }
		break; }
	case 21: case 23: { /* ARM task id_lo id_hi rate_lo rate_hi gain(0..65535) | ARMSTOP task id_lo id_hi fade_ms */
		int a = find_arm(arg(0), c == 23);
		if (a < 0) for (a = 0; a < 64 && bs.arms[a].used; a++) {}
		if (a >= 64) a = 0;
		auto &A = bs.arms[a];
		A.used = true; A.task = arg(0); A.id = arg32(1); A.stop = (c == 23);
		if (c == 21) { A.hz = arg32(3); A.gain = arg(5) / 65535.f; }
		else A.fade = (Bit32u)arg(3) * (BS_RATE / 1000);
		break; }
	case 22: /* REPORT words... */
		for (Bit16u w : bs.args) bs.reports.push_back(w);
		break;
	case 27: /* ENV attack_ms decay_ms sustain_pct */
		bs.env_a = (Bit32u)arg(0) * (BS_RATE / 1000); bs.env_d = (Bit32u)arg(1) * (BS_RATE / 1000); bs.env_s = arg(2) / 100.f; break;
	case 28: /* IDLE: the synth program has nothing to do: end this millisecond's CPU slice now (like HLT does), so
	            an idle Windows costs the host almost nothing; time, timers and the DAC go on as before */
		CPU_IODelayRemoved += CPU_Cycles;
		CPU_Cycles = 0; CPU_CycleLeft = 0;
		bs.args.clear();
		return;
	case 24: bs.master = arg32(0) / 65536.f; if (bs.master <= 0) bs.master = 1.f; break;
	case 25: { /* DACNOW -> 4 words */
		Bit64u d = bs.dac; for (int i = 0; i < 4; i++) bs.results.push_back((Bit16u)(d >> (16 * i))); break; }
	case 26: { /* VOICES -> bitmask of logical channels sounding (2 words) + ghosts count */
		Bit32u m = 0; int g = 0;
		for (int i = 0; i < BS_CH; i++) if (bs.v[i].on && bs.dac >= bs.v[i].start_at) m |= 1u << i;
		for (int i = BS_CH; i < BS_CH * 2; i++) if (bs.v[i].on) g++;
		bs.results.push_back((Bit16u)m); bs.results.push_back((Bit16u)(m >> 16)); bs.results.push_back((Bit16u)g); break; }
	}
	bs.args.clear();
}

static void bs_write(Bitu port, Bitu val, Bitu /*iolen*/)
{
	switch (port - BS_BASE) {
	case 0: { std::lock_guard<std::mutex> l(bs.mtx); bs.args.push_back((Bit16u)val); if (bs.args.size() > 4096) bs.args.clear(); break; }
	case 2: command((Bit16u)val); break;
	}
}
static Bitu bs_read(Bitu port, Bitu /*iolen*/)
{
	switch (port - BS_BASE) {
	case 0: { std::lock_guard<std::mutex> l(bs.mtx); if (bs.results.empty()) return 0; Bit16u w = bs.results.front(); bs.results.erase(bs.results.begin()); return w; }
	case 4: return 0x5342; /* 'BS' */
	}
	return 0xFFFF;
}

class BSYNTH : public Module_base {
	IO_ReadHandleObject rh; IO_WriteHandleObject wh;
public:
	BSYNTH(Section *conf) : Module_base(conf) {
		wh.Install(BS_BASE, bs_write, IO_MW, 6);
		rh.Install(BS_BASE, bs_read, IO_MW, 6);
		bs.master = 1.f; bs.env_s = 1.f;
		if (!bs.ring) { bs.ring_len = BS_RATE * 4; bs.ring = (float *)calloc(bs.ring_len * 2, sizeof(float)); }
		bs.mo = new MixerObject();
		bs.chan = bs.mo->Install(&BSYN_CallBack, BS_RATE, "BSYNTH");
		bs.chan->Enable(true);
	}
	~BSYNTH() {
		delete bs.mo; bs.mo = NULL; bs.chan = NULL;
		std::lock_guard<std::mutex> l(bs.mtx);
		for (int i = 0; i < BS_CH * 2; i++) bs.v[i] = BSVoice();
		memset(bs.chopen, 0, sizeof bs.chopen);
	}
};
static BSYNTH *bsynth;
static void BSYNTH_ShutDown(Section *) { delete bsynth; bsynth = NULL; }
void BSYNTH_Init(Section *sec) { bsynth = new BSYNTH(sec); sec->AddDestroyFunction(&BSYNTH_ShutDown, true); }

#include <dbp_serialize.h>
/* Snapshots are taken with every voice idle; the card state is just "closed", restored as such. The DAC
   counter keeps running from where this process is (the host's sample clock never jumps backwards). */
void DBPSerialize_BSYNTH(DBPArchive &ar)
{
	Bit32u ver = 1; ar << ver;
	if (ar.mode == DBPArchive::MODE_LOAD) {
		std::lock_guard<std::mutex> l(bs.mtx);
		for (int i = 0; i < BS_CH * 2; i++) bs.v[i] = BSVoice();
		memset(bs.chopen, 0, sizeof bs.chopen);
		memset(bs.arms, 0, sizeof bs.arms);
		bs.args.clear(); bs.results.clear(); bs.master = 1.f; bs.env_a = bs.env_d = 0; bs.env_s = 1.f;
	}
}
