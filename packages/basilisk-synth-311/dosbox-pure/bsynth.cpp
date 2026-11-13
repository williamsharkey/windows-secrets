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
/* a drawn envelope: up to 8 breakpoints, time in DAC samples from the voice's start, level 0..1 (or pan -1..1);
   linear between points, the last level holds */
struct BSEnv { int n; Bit32u t[8]; float l[8]; int loop; };   /* loop: the last `loop` points repeat while the voice is held (v3 Wr / Wp) */
static float env_at(const BSEnv &e, Bit64u age)
{
	if (e.n <= 0) return 1.f;
	if (age <= e.t[0]) return e.n == 1 || e.t[0] == 0 ? e.l[0] : e.l[0] * (float)age / (float)e.t[0];
	for (int k = 1; k < e.n; k++)
		if (age < e.t[k]) return e.l[k - 1] + (e.l[k] - e.l[k - 1]) * (float)(age - e.t[k - 1]) / (float)(e.t[k] - e.t[k - 1]);
	return e.l[e.n - 1];
}
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
	Bit64u age_a, age_p;   /* the drawn envelopes' own clocks: they go back to the loop start while the voice is held */
	float pan;             /* -1 (left) .. 1 (right), the arm's; the pan envelope adds to it */
	BSEnv ea, ep;          /* drawn envelopes (DNA v2 Ja / Jp), copied from the layer when the voice opens */
	int owner;             /* logical channel that owns it, -1 = ghost (fading after reset) */
	Bit16u task;           /* the Windows task that opened it (kept by its ghost), for RATETASK / STOPTASK */
	/* v3 rate changes (RATETASK), queued in time order: from DAC sample at the arm rate glides (linear in cents)
	   to `to` over len samples; the host sends them ahead of time, so several can wait */
	struct Rt { Bit64u at; Bit32u len; float to; bool regate; } rq[8];
	int rqn;               /* rate changes waiting (rq[0] is the next) */
	bool rt_on; Bit64u rt_at; Bit32u rt_len; float rt_from, rt_to;   /* the glide in progress */
	Bit64u kill_at;        /* STOPTASK: a stop no regate takes back (~0 = none) */
	/* MUTEAT: from mute_at the voice fades out over mute_len exactly as a stop would, then plays on silently, so
	   Sound Recorder (which owns it) still sees it play and its wave view follows; the guest presses Stop later */
	Bit64u mute_at; Bit32u mute_len, mute_left; bool muted;
	Bit64u mute_next_at; Bit32u mute_next_len;   /* a later end, sent ahead, that a regate before it brings into force */
	Bit32u kill_fade;
};

static struct {
	std::mutex mtx;
	std::vector<Bit16u> args, results;
	BSVoice v[BS_CH * 2];          /* first BS_CH: logical channels; rest: ghosts */
	bool chopen[BS_CH];
	Bit16u chtask[BS_CH];
	Bit64u dac;                    /* DAC samples produced so far */
	/* arms: task -> (event id, rate, gain) for the next open / stop by that task */
	struct Arm { Bit16u task; Bit32u id; Bit32u hz; float gain; float pan; int layer; Bit32u fade; bool stop; bool used; } arms[64];
	BSEnv lenv_a[8], lenv_p[8];          /* the layers' envelopes (LENV), for voices armed with a layer */
	Bit32u env_a, env_d; float env_s;   /* the envelope new voices get (ENV) */
	/* host -> guest events, guest -> host reports */
	std::deque<Bit16u> events, reports;
	/* event id -> DAC sample (target) */
	Bit32u tgt_id[4096]; Bit64u tgt_at[4096];
	float master;                  /* master pitch multiplier (pitch bend) */
	/* the ADC (RECORDING.md 1.3): one capture channel. Its source is the host's input (the plugin's sidechain),
	   stamped on the DAC clock, or the card's own output ("Synth output", resampling). The guest's buffers are
	   filled with 8/16-bit PCM at the open rate through the same Hermite converter the voices use. */
	struct InBuf { Bit32u lin, len, cookie, filled; };
	struct {
		bool open, running; Bit32u rate; int bits, nch;
		std::deque<InBuf> q; std::vector<Bit32u> done_ck, done_n;   /* finished buffers: cookie, bytes */
		double spos;            /* the DAC sample (fractional) the next output frame is taken at */
		Bit32u bytes;           /* bytes recorded since start (GETPOS) */
		Bit64u start_at;        /* the DAC sample of the take's first frame */
		Bit32u overruns;        /* frames lost because no buffer was queued */
	} in;
	float *iring; Bit32u iring_len; Bit64u iring_hi;   /* the input, by DAC sample: valid in (hi - len, hi] */
	int insrc;                                         /* 0 the host's input, 1 the card's own output */
	/* the host's pointer (event type 6): once the driver polls it (PTRGET), it is kept here, not queued */
	bool ptr_polled; Bit16u ptr_x, ptr_y, ptr_seq;
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
	if (bs.ptr_polled && n >= 3 && (w[0] >> 8) == 6) { bs.ptr_x = w[1]; bs.ptr_y = w[2]; bs.ptr_seq++; return; }
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
/* the host's input (the sidechain), n stereo frames stamped from DAC sample `at` (the same clock as notes) */
BSYN_API void bsyn_host_input(Bit64u at, const float *lr, int n)
{
	std::lock_guard<std::mutex> l(bs.mtx);
	if (!bs.iring || bs.insrc != 0) return;
	for (int k = 0; k < n; k++) { Bit32u i = (Bit32u)((at + k) % bs.iring_len); bs.iring[i * 2] = lr[k * 2]; bs.iring[i * 2 + 1] = lr[k * 2 + 1]; }
	if (at + n > bs.iring_hi) bs.iring_hi = at + n;
}
/* the ADC's source: 0 the host's input, 1 the synth's own output */
BSYN_API void bsyn_host_insrc(int src) { std::lock_guard<std::mutex> l(bs.mtx); bs.insrc = src ? 1 : 0; }
/* recording state: 1 while a take runs; *start = its first frame's DAC sample, *bytes so far, *overruns */
BSYN_API int bsyn_host_instate(Bit64u *start, Bit32u *bytes, Bit32u *overruns)
{
	std::lock_guard<std::mutex> l(bs.mtx);
	if (start) *start = bs.in.start_at; if (bytes) *bytes = bs.in.bytes; if (overruns) *overruns = bs.in.overruns;
	return bs.in.running ? 1 : 0;
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
		const float master = bs.master;
		const bool panning = v.pan != 0.f || v.ep.n > 0;
		for (Bitu s = 0; s < len; s++) {
			Bit64u t = bs.dac + s;
			if (t < v.start_at) continue;
			if (v.q.empty()) { if (v.owner < 0) v.on = false; break; }
			if (v.rqn && t >= v.rq[0].at) {   /* the next stamped rate change starts: sample-exact, phase-continuous */
				const BSVoice::Rt r = v.rq[0];
				for (int k = 1; k < v.rqn; k++) v.rq[k - 1] = v.rq[k];
				v.rqn--;
				v.rt_on = true; v.rt_at = r.at; v.rt_len = r.len; v.rt_from = v.armrate; v.rt_to = r.to;
				if (r.regate) {   /* continue: the release is taken back (a later end sent meanwhile comes into force) */
					v.stop_at = ~(Bit64u)0; v.fade_left = 0; v.muted = false; v.mute_left = 0;
					v.mute_at = v.mute_next_at; v.mute_len = v.mute_next_len; v.mute_next_at = ~(Bit64u)0;
				}
			}
			if (v.rt_on) {
				Bit64u k = t - v.rt_at;
				if (k >= v.rt_len || v.rt_from <= 0.f) { v.armrate = v.rt_to; v.rt_on = false; }
				else v.armrate = v.rt_from * powf(v.rt_to / v.rt_from, (float)k / (float)v.rt_len);
				step = (double)v.srate * v.rate * v.armrate * master / BS_RATE;
			}
			if (t >= v.kill_at && !v.fade_left) { v.fade_len = v.kill_fade; v.fade_left = v.kill_fade; v.kill_at = ~(Bit64u)0; v.stop_at = ~(Bit64u)0; }
			float fg = 1.f;
			if (t >= v.stop_at) {
				if (!v.fade_left) { v.fade_left = v.fade_len ? v.fade_len : 1; v.stop_at = 0; }
			}
			if (v.fade_left) {
				fg = (float)v.fade_left / (float)(v.fade_len ? v.fade_len : 1);
				if (--v.fade_left == 0) { v.on = false; v.q.clear(); break; }
			}
			if (t >= v.mute_at && !v.muted) {   /* the same fade as a stop's, then silence while it plays on */
				if (!v.mute_left) v.mute_left = v.mute_len ? v.mute_len : 1;
				fg *= (float)v.mute_left / (float)(v.mute_len ? v.mute_len : 1);
				if (--v.mute_left == 0) v.muted = true;
			}
			if (v.muted) fg = 0.f;
			if (v.ea.n) fg *= env_at(v.ea, v.age_a);
			else if (v.env_a || v.env_d || v.env_s < 1.f) {
				float eg;
				if (v.age < v.env_a) eg = (float)v.age / (float)v.env_a;
				else if (v.age < (Bit64u)v.env_a + v.env_d) eg = 1.f - (1.f - v.env_s) * (float)(v.age - v.env_a) / (float)v.env_d;
				else eg = v.env_s;
				fg *= eg;
			}
			float gl = v.voll * v.gain, gr = v.volr * v.gain;
			if (panning) {   /* pan: the voice's left/right volume, never in the buffer */
				float p = v.pan + (v.ep.n ? env_at(v.ep, v.age_p) : 0.f);
				p = p < -1.f ? -1.f : p > 1.f ? 1.f : p;
				if (p > 0) gl *= 1.f - p; else gr *= 1.f + p;
			}
			v.age++;
			v.age_a++; v.age_p++;
			if (v.owner >= 0) {   /* held (not yet a releasing ghost): a looping envelope goes back to its loop start */
				if (v.ea.loop >= 2 && v.ea.n >= v.ea.loop && v.age_a >= v.ea.t[v.ea.n - 1]) { Bit32u s0 = v.ea.t[v.ea.n - v.ea.loop]; if (v.ea.t[v.ea.n - 1] > s0) v.age_a = s0 + (v.age_a - v.ea.t[v.ea.n - 1]); }
				if (v.ep.loop >= 2 && v.ep.n >= v.ep.loop && v.age_p >= v.ep.t[v.ep.n - 1]) { Bit32u s0 = v.ep.t[v.ep.n - v.ep.loop]; if (v.ep.t[v.ep.n - 1] > s0) v.age_p = s0 + (v.age_p - v.ep.t[v.ep.n - 1]); }
			}
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

static float in_at(Bit64s t, int c)   /* the input at DAC sample t (0 outside what the ring holds) */
{
	if (t < 0 || (Bit64u)t >= bs.iring_hi || (Bit64u)t + bs.iring_len <= bs.iring_hi) return 0.f;
	return bs.iring[(Bit32u)((Bit64u)t % bs.iring_len) * 2 + c];
}
/* the ADC: output frames whose input (4 samples around them) the ring already holds, up to DAC sample `upto` */
static void adc_run(Bit64u upto)
{
	if (!bs.in.running || !bs.in.rate) return;
	const double step = (double)BS_RATE / bs.in.rate;
	const int fb = (bs.in.bits / 8) * bs.in.nch;
	while (bs.in.spos + 2 < (double)upto) {
		Bit64s i = (Bit64s)floor(bs.in.spos); float f = (float)(bs.in.spos - i);
		float y[2];
		for (int c = 0; c < 2; c++) {
			float y0 = in_at(i - 1, c), y1 = in_at(i, c), y2 = in_at(i + 1, c), y3 = in_at(i + 2, c);
			float c1 = 0.5f * (y2 - y0), c2 = y0 - 2.5f * y1 + 2.f * y2 - 0.5f * y3, c3 = 0.5f * (y3 - y0) + 1.5f * (y1 - y2);
			y[c] = ((c3 * f + c2) * f + c1) * f + y1;
		}
		bs.in.spos += step;
		if (bs.in.q.empty()) { bs.in.overruns++; continue; }
		auto &b = bs.in.q.front();
		Bit8u px[4];
		for (int c = 0; c < bs.in.nch; c++) {
			float x = bs.in.nch == 1 ? 0.5f * (y[0] + y[1]) : y[c];
			x = x > 1.f ? 1.f : x < -1.f ? -1.f : x;
			if (bs.in.bits == 16) { Bit16s s = (Bit16s)lrintf(x * 32767.f); px[c * 2] = (Bit8u)s; px[c * 2 + 1] = (Bit8u)((Bit16u)s >> 8); }
			else px[c] = (Bit8u)lrintf(128.f + x * 127.f);
		}
		for (int k = 0; k < fb && b.filled < b.len; k++) mem_writeb_checked(b.lin + b.filled++, px[k]);
		bs.in.bytes += fb;
		if (b.filled + fb > b.len) { bs.in.done_ck.push_back(b.cookie); bs.in.done_n.push_back(b.filled); bs.in.q.pop_front(); }
	}
}
static void BSYN_CallBack(Bitu len)
{
	static std::vector<float> tmp; static std::vector<Bit16s> pcm;
	if (tmp.size() < len * 2) { tmp.resize(len * 2); pcm.resize(len * 2); }
	{
		std::lock_guard<std::mutex> l(bs.mtx);
		render(&tmp[0], len);
		if (bs.insrc == 1 && bs.iring) {   /* Synth output: the card's own mix is the input, on the same samples */
			for (Bitu s = 0; s < len; s++) { Bit32u i = (Bit32u)((bs.dac + s) % bs.iring_len); bs.iring[i * 2] = tmp[s * 2]; bs.iring[i * 2 + 1] = tmp[s * 2 + 1]; }
			bs.iring_hi = bs.dac + len;
		}
		adc_run(bs.dac + len);
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
			BSVoice &G = bs.v[g];
			G = v; G.owner = -1; G.done.clear();
			G.stop_at = stop_at; G.fade_len = fade ? fade : BS_FADE; G.fade_left = 0;
			if (v.mute_at != ~(Bit64u)0) {   /* an end already set by MUTEAT keeps its own sample and fade */
				if (v.muted) { G.on = false; G.q.clear(); }
				else if (v.mute_left) { G.fade_len = v.mute_len; G.fade_left = v.mute_left; G.stop_at = ~(Bit64u)0; }
				else if (v.mute_at <= stop_at) { G.stop_at = v.mute_at; G.fade_len = v.mute_len; }
				G.mute_at = ~(Bit64u)0; G.muted = false; G.mute_left = 0; G.mute_next_at = ~(Bit64u)0;
			}
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
		v.rate = 1.f; v.armrate = 1.f; v.voll = v.volr = 1.f; v.gain = 1.f; v.stop_at = ~(Bit64u)0; v.kill_at = ~(Bit64u)0; v.mute_at = ~(Bit64u)0; v.mute_next_at = ~(Bit64u)0;
		bs.chopen[ch] = true; bs.chtask[ch] = arg(0); v.task = arg(0);
		int a = find_arm(arg(0), false);
		v.start_at = bs.dac;
		v.env_a = 0; v.env_d = 0; v.env_s = 1.f; v.age = 0; v.pan = 0; v.ea.n = 0; v.ep.n = 0;
		if (a >= 0) {
			v.voice_id = bs.arms[a].id; v.start_at = target_of(bs.arms[a].id);
			v.armrate = (bs.arms[a].hz && v.srate) ? (float)bs.arms[a].hz / (float)v.srate : 1.f;
			v.gain = bs.arms[a].gain; bs.arms[a].used = false;
			v.env_a = bs.env_a; v.env_d = bs.env_d; v.env_s = bs.env_s;
			v.pan = bs.arms[a].pan;
			if (bs.arms[a].layer >= 0 && bs.arms[a].layer < 8) {
				v.ea = bs.lenv_a[bs.arms[a].layer]; v.ep = bs.lenv_p[bs.arms[a].layer];
				if (v.ea.n) { v.env_a = 0; v.env_d = 0; v.env_s = 1.f; }   /* a drawn envelope replaces A, D, S */
			}
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
		if (c == 21) {
			A.hz = arg32(3); A.gain = arg(5) / 65535.f;
			/* v2: pan (0..200 = -100..100) and layer (0 = none, else layer + 1) */
			A.pan = bs.args.size() > 6 ? ((int)arg(6) - 100) / 100.f : 0.f;
			A.layer = bs.args.size() > 7 ? (int)arg(7) - 1 : -1;
		}
		else A.fade = (Bit32u)arg(3) * (BS_RATE / 1000);
		break; }
	case 30: { /* RATETASK task id_lo id_hi hz_lo hz_hi glide_ms regate: every voice of the task (and its ghosts)
	              changes its arm rate to hz at the event's DAC sample, gliding over glide_ms; regate (the newest voice
	              only) takes back a release that has begun (mono "continue": the recorder keeps its place) */
		Bit16u task = arg(0); Bit32u id = arg32(1), hz = arg32(3); Bit32u glide = (Bit32u)arg(5) * (BS_RATE / 1000);
		bool regate = arg(6) != 0;
		Bit64u at = target_of(id);
		int newest = -1;
		for (int i = 0; i < BS_CH * 2; i++) {
			BSVoice &v = bs.v[i];
			if (!v.on || v.task != task || !v.srate || !hz || v.kill_at != ~(Bit64u)0) continue;
			if (newest < 0 || v.start_at > bs.v[newest].start_at) newest = i;
			int k = v.rqn;
			while (k > 0 && v.rq[k - 1].at > at) k--;         /* time order (a later stamp replaces nothing) */
			if (v.rqn == 8) { for (int j = 1; j < 8; j++) v.rq[j - 1] = v.rq[j]; v.rqn--; if (k) k--; }   /* full: the oldest goes */
			for (int j = v.rqn; j > k; j--) v.rq[j] = v.rq[j - 1];
			v.rq[k].at = at; v.rq[k].len = glide; v.rq[k].to = (float)hz / (float)v.srate; v.rq[k].regate = false;
			v.rqn++;
		}
		if (regate && newest >= 0) {   /* the newest voice's matching entry takes back its release */
			BSVoice &v = bs.v[newest];
			for (int k = 0; k < v.rqn; k++) if (v.rq[k].at == at) v.rq[k].regate = true;
		}
		if (trace) fprintf(stderr, "bsyn rate task %04x hz %u at %llu glide %u regate %d newest %d\n", task, hz, (unsigned long long)at, glide, regate, newest);
		break; }
	case 31: { /* STOPTASK task id_lo id_hi fade_ms: stop the task's ghosts that a regate kept sounding */
		Bit16u task = arg(0); Bit64u at = target_of(arg32(1)); Bit32u fade = (Bit32u)arg(3) * (BS_RATE / 1000);
		for (int i = BS_CH; i < BS_CH * 2; i++) {
			BSVoice &v = bs.v[i];
			if (!v.on || v.task != task) continue;
			if (v.kill_at > at) { v.kill_at = at; v.kill_fade = fade ? fade : BS_FADE; }
		}
		break; }
	case 40: { /* INOPEN rate_lo rate_hi bits nch -> 1 ok / 0 (busy or a format the ADC has not) */
		Bit32u rate = arg32(0); int bits = arg(2), nch = arg(3);
		if (bs.in.open || (bits != 8 && bits != 16) || (nch != 1 && nch != 2) || rate < 4000 || rate > 48000) { bs.results.push_back(0); break; }
		bs.in.open = true; bs.in.running = false; bs.in.rate = rate; bs.in.bits = bits; bs.in.nch = nch;
		bs.in.q.clear(); bs.in.done_ck.clear(); bs.in.done_n.clear(); bs.in.bytes = 0; bs.in.overruns = 0;
		bs.results.push_back(1); break; }
	case 41: /* INCLOSE */
		bs.in.open = bs.in.running = false; bs.in.q.clear(); break;
	case 42: { /* INADD lin_lo lin_hi len_lo len_hi cookie_lo cookie_hi */
		if (!bs.in.open) break;
		bs.in.q.push_back({arg32(0), arg32(2), arg32(4), 0}); break; }
	case 43: /* INSTART: the take starts at the next DAC sample */
		if (bs.in.open && !bs.in.running) { bs.in.running = true; bs.in.spos = (double)bs.dac; bs.in.start_at = bs.dac; bs.in.bytes = 0; bs.in.overruns = 0; }
		break;
	case 44: /* INSTOP: the buffer being filled is returned (with what it holds) */
		if (bs.in.running) {
			bs.in.running = false;
			if (!bs.in.q.empty() && bs.in.q.front().filled) { bs.in.done_ck.push_back(bs.in.q.front().cookie); bs.in.done_n.push_back(bs.in.q.front().filled); bs.in.q.pop_front(); }
		}
		break;
	case 45: /* INRESET: stop; every queued buffer is returned */
		bs.in.running = false;
		for (auto &b : bs.in.q) { bs.in.done_ck.push_back(b.cookie); bs.in.done_n.push_back(b.filled); }
		bs.in.q.clear(); bs.in.bytes = 0; break;
	case 46: { /* INPOLL -> n, then (cookie_lo, cookie_hi, bytes_lo, bytes_hi) * n; at most 15 */
		size_t n = bs.in.done_ck.size() > 15 ? 15 : bs.in.done_ck.size();
		bs.results.push_back((Bit16u)n);
		for (size_t k = 0; k < n; k++) {
			bs.results.push_back((Bit16u)bs.in.done_ck[k]); bs.results.push_back((Bit16u)(bs.in.done_ck[k] >> 16));
			bs.results.push_back((Bit16u)bs.in.done_n[k]); bs.results.push_back((Bit16u)(bs.in.done_n[k] >> 16));
		}
		bs.in.done_ck.erase(bs.in.done_ck.begin(), bs.in.done_ck.begin() + n); bs.in.done_n.erase(bs.in.done_n.begin(), bs.in.done_n.begin() + n);
		break; }
	case 47: /* INGETPOS -> bytes lo hi */
		bs.results.push_back((Bit16u)bs.in.bytes); bs.results.push_back((Bit16u)(bs.in.bytes >> 16)); break;
	case 34: { /* MUTEAT task id_lo id_hi fade_ms: the task's playing voice fades out at the event's sample as a stop
	              would, then plays on silently until the guest presses Stop */
		Bit16u task = arg(0); Bit64u at = target_of(arg32(1)); Bit32u fade = (Bit32u)arg(3) * (BS_RATE / 1000);
		for (int i = 0; i < BS_CH; i++) {
			BSVoice &v = bs.v[i];
			if (!v.on || v.task != task || v.muted) continue;
			if (v.mute_at == ~(Bit64u)0) { v.mute_at = at; v.mute_len = fade ? fade : BS_FADE; v.mute_left = 0; }
			else if (at > v.mute_at) { v.mute_next_at = at; v.mute_next_len = fade ? fade : BS_FADE; }
		}
		break; }
	case 33: { /* STAMPOF id_lo id_hi -> the event's DAC sample (4 words; the DAC now if it is not known) */
		Bit32u id = arg32(0); Bit64u at = (id && bs.tgt_id[id & 4095] == id) ? bs.tgt_at[id & 4095] : bs.dac;
		for (int i = 0; i < 4; i++) bs.results.push_back((Bit16u)(at >> (16 * i)));
		break; }
	case 32: /* PTRGET -> seq x y: the host's pointer for the driver's timer, which moves it with USER's mouse_event
	            (at interrupt time, so it also moves while a scroll bar's tracking loop holds the synth program) */
		bs.ptr_polled = true;
		bs.results.push_back(bs.ptr_seq); bs.results.push_back(bs.ptr_x); bs.results.push_back(bs.ptr_y); break;
	case 22: /* REPORT words... */
		for (Bit16u w : bs.args) bs.reports.push_back(w);
		break;
	case 29: { /* LENV layer kind(0 amp, 1 pan) n  t_ms l  t_ms l ... [loop]  (l: amp 0..100, pan 0..200 = -100..100;
	              loop (v3): the last `loop` points repeat while the voice is held) */
		int L = arg(0), kind = arg(1), n = arg(2);
		if (L < 0 || L >= 8) break;
		BSEnv &e = kind ? bs.lenv_p[L] : bs.lenv_a[L];
		e.n = n > 8 ? 8 : n;
		for (int k = 0; k < e.n; k++) {
			e.t[k] = (Bit32u)arg(3 + 2 * k) * (BS_RATE / 1000);
			e.l[k] = kind ? ((int)arg(4 + 2 * k) - 100) / 100.f : arg(4 + 2 * k) / 100.f;
		}
		e.loop = bs.args.size() > (size_t)(3 + 2 * n) ? (int)arg(3 + 2 * n) : 0;
		if (e.loop > e.n) e.loop = e.n;
		break; }
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
		if (!bs.iring) { bs.iring_len = BS_RATE * 2; bs.iring = (float *)calloc(bs.iring_len * 2, sizeof(float)); }
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
		memset(bs.lenv_a, 0, sizeof bs.lenv_a); memset(bs.lenv_p, 0, sizeof bs.lenv_p);
		bs.args.clear(); bs.results.clear(); bs.master = 1.f; bs.env_a = bs.env_d = 0; bs.env_s = 1.f;
		bs.in.open = bs.in.running = false; bs.in.q.clear(); bs.in.done_ck.clear(); bs.in.done_n.clear();
	}
}
