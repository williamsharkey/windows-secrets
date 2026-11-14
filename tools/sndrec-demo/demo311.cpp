// demo311: a scripted capture of BASILISK 16 in use, for the demo videos on sndrec.html. Linux.
//
//   demo311 --machine DIR --core FILE --script FILE --video OUT.mkv --audio OUT.wav [--fps 30]
//
// It is tools/render311.cpp (packages/basilisk-synth-311) with the screen turned on: the same engine, the same
// machine snapshot, the same shared core (DNA, voice allocator, protocol), and it plays the plugin's part as the
// plugin does (Basilisk16Plugin.cpp): hi / time / go at load, `dna` then `env` and the layers' `lenv`, notes stamped
// with their DAC sample, `show` for every incoming note so its key goes down in Windows, `cc 1` for the mod wheel
// (which adds to Macro 1 and re-applies the DNA's macro mappings), and a preset change that keeps the old sound until
// Windows says `built`. Nothing is synthesized here: the audio is the BSYN card's DAC, the picture is the emulated VGA.
//
// Time is the DAC's: one video frame is grabbed every 48000/fps DAC samples, after the engine has produced them, so
// picture and sound stay in step whatever the speed of this PC. Output: lossless video (ffmpeg, FFV1) and a 48 kHz
// float WAV of the same length.
//
// Script: one command per line, run in order; '#' comments. Times are seconds.
//   go                         hello, clock, and the assembly (as the plugin at load)
//   dna DNA                    a new sound (a preset change once Windows is up)
//   waitfor ready|built        hold the script until Windows says so (the capture keeps running)
//   sleep S                    let S seconds pass
//   note N VEL DUR             a note now (its key lights up), released after DUR
//   midi FILE.mid [VEL%]       schedule a Standard MIDI File from now (does not wait; follow with sleep)
//   cc1 FROM TO S              move the mod wheel from FROM to TO (0..127) over S seconds, in 30 steps a second
//   rec on|off                 start or stop writing frames and audio (the machine runs either way)
//   end                        stop
#include "../../packages/basilisk-synth-311/engine/engine.h"
#include "../../packages/basilisk-synth/core/dna.h"
#include "../../packages/basilisk-synth/core/voices.h"
#include "../../packages/basilisk-synth/core/proto.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <unistd.h>

using namespace bsynth;

static void nap() { std::this_thread::sleep_for(std::chrono::microseconds(200)); }

struct MidiEv { double t; uint8_t st, a, b; };
static uint32_t be32(const uint8_t *p) { return (p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3]; }
static uint16_t be16(const uint8_t *p) { return (p[0] << 8) | p[1]; }

static bool readMidi(const std::string &path, std::vector<MidiEv> &out)
{
    std::ifstream f(path, std::ios::binary);
    std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    if (d.size() < 14 || std::memcmp(d.data(), "MThd", 4)) return false;
    const int ntrk = be16(&d[10]), div = be16(&d[12]);
    struct Raw { uint64_t tick; uint8_t st, a, b; uint32_t tempo; bool isTempo; };
    std::vector<Raw> raw;
    size_t p = 8 + be32(&d[4]);
    for (int t = 0; t < ntrk && p + 8 <= d.size(); t++) {
        size_t end = p + 8 + be32(&d[p + 4]); p += 8;
        uint64_t tick = 0; uint8_t run = 0;
        while (p < end) {
            uint32_t dt = 0; uint8_t c;
            do { c = d[p++]; dt = (dt << 7) | (c & 0x7F); } while (c & 0x80);
            tick += dt;
            uint8_t st = d[p];
            if (st & 0x80) p++; else st = run;
            if (st == 0xFF) {
                uint8_t type = d[p++]; uint32_t len = 0;
                do { c = d[p++]; len = (len << 7) | (c & 0x7F); } while (c & 0x80);
                if (type == 0x51 && len == 3) raw.push_back({tick, 0, 0, 0, (uint32_t)((d[p] << 16) | (d[p + 1] << 8) | d[p + 2]), true});
                p += len;
            } else if (st == 0xF0 || st == 0xF7) {
                uint32_t len = 0;
                do { c = d[p++]; len = (len << 7) | (c & 0x7F); } while (c & 0x80);
                p += len;
            } else {
                run = st;
                const int n = ((st & 0xF0) == 0xC0 || (st & 0xF0) == 0xD0) ? 1 : 2;
                uint8_t a = d[p++], b = n == 2 ? d[p++] : 0;
                raw.push_back({tick, st, a, b, 0, false});
            }
        }
        p = end;
    }
    std::stable_sort(raw.begin(), raw.end(), [](const Raw &x, const Raw &y) { return x.tick < y.tick; });
    double sec = 0, spt = 0.5 / div; uint64_t last = 0;
    for (auto &r : raw) {
        sec += (r.tick - last) * spt; last = r.tick;
        if (r.isTempo) { spt = r.tempo / 1e6 / div; continue; }
        out.push_back({sec, r.st, r.a, r.b});
    }
    return true;
}

static void writeWavFloat(const std::string &path, const std::vector<float> &lr)
{
    FILE *f = std::fopen(path.c_str(), "wb");
    const uint32_t frames = (uint32_t)(lr.size() / 2), data = frames * 8;
    auto u32 = [&](uint32_t v) { std::fwrite(&v, 4, 1, f); };
    auto u16 = [&](uint16_t v) { std::fwrite(&v, 2, 1, f); };
    std::fwrite("RIFF", 1, 4, f); u32(36 + data); std::fwrite("WAVEfmt ", 1, 8, f);
    u32(16); u16(3); u16(2); u32(48000); u32(48000 * 8); u16(8); u16(32);
    std::fwrite("data", 1, 4, f); u32(data);
    std::fwrite(lr.data(), 4, lr.size(), f);
    std::fclose(f);
}

struct Machine {
    bshm *S = nullptr; bs_engine *e = nullptr;
    std::vector<uint16_t> words; std::string frag;
    void send(const std::string &text, uint32_t id = 0, uint64_t at = 0)
    {
        int len = (int)text.size(), pos = 0;
        do {
            const int m = len - pos > 240 ? 240 : len - pos;
            const bool last = pos + m >= len;
            const int nw = 3 + (m + 1) / 2;
            uint16_t w[136];
            w[0] = (uint16_t)(((last ? 4 : 8) << 8) | nw);
            w[1] = (uint16_t)(last ? id : 0); w[2] = (uint16_t)((last ? id : 0) >> 16);
            for (int k = 0; k < (m + 1) / 2; k++) {
                const uint8_t a = (uint8_t)text[pos + 2 * k], b = 2 * k + 1 < m ? (uint8_t)text[pos + 2 * k + 1] : 0;
                w[3 + k] = (uint16_t)(a | (b << 8));
            }
            while (!bs_engine_event(e, w, nw, last ? id : 0, last ? at : 0)) nap();
            pos += m;
        } while (pos < len);
    }
    void lines(std::vector<std::string> &out)
    {
        while (S->rep_r != S->rep_w) { words.push_back((uint16_t)S->rep[S->rep_r % BSHM_REP]); __sync_synchronize(); S->rep_r++; }
        size_t i = 0;
        while (i < words.size()) {
            const int n = words[i] & 0xFF ? words[i] & 0xFF : 1;
            if (i + n > words.size()) break;
            const int ty = words[i] >> 8;
            if (ty == 3 || ty == 7) {
                for (int k = 1; k < n; k++) {
                    const char a = (char)(words[i + k] & 0xFF), b = (char)(words[i + k] >> 8);
                    if (a) frag += a; if (a && b) frag += b;
                }
                if (ty == 3) { out.push_back(frag); frag.clear(); }
            }
            i += n;
        }
        words.erase(words.begin(), words.begin() + i);
    }
};

struct LInfo { int first = 0, count = 0, rate = 0, frames = 0; bool known = false; };

static std::string sigOf(const Dna &d)   // as the plugin: what makes Sound Recorder rebuild
{
    std::string s;
    for (auto &L : d.layers) {
        s += std::to_string(L.source) + L.sourceName + ":" + std::to_string(L.first) + ":" + std::to_string(L.count) + ":";
        for (auto &st : L.steps) { s += st.op; s += std::to_string(st.arg) + "." + std::to_string(st.ms) + "." + std::to_string(st.sound) + st.name; }
        s += "|";
    }
    return s;
}

int main(int argc, char **argv)
{
    std::map<std::string, std::string> a;
    for (int i = 1; i + 1 < argc; i += 2) a[argv[i]] = argv[i + 1];
    if (!a.count("--machine") || !a.count("--core") || !a.count("--script") || !a.count("--video") || !a.count("--audio")) {
        std::fprintf(stderr, "demo311 --machine DIR --core FILE --script FILE --video OUT.mkv --audio OUT.wav [--fps 30]\n");
        return 2;
    }
    const int fps = a.count("--fps") ? std::atoi(a["--fps"].c_str()) : 30;
    const uint32_t spf = 48000 / fps;
    std::vector<std::vector<std::string>> script;
    {
        std::ifstream in(a["--script"]); std::string l;
        while (std::getline(in, l)) {
            if (l.empty() || l[0] == '#') continue;
            std::istringstream ss(l); std::vector<std::string> w; std::string x;
            while (ss >> x) w.push_back(x);
            if (!w.empty()) script.push_back(w);
        }
    }
    const std::string machine = a["--machine"];
    {
        std::ifstream in(machine + "/library.names.txt"); std::vector<std::string> names; std::string l;
        while (std::getline(in, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) names.push_back(l); }
        setLibrary(names);
    }
    std::string conf = std::string(std::getenv("TMPDIR") ? std::getenv("TMPDIR") : "/tmp") + "/demo311-" + std::to_string((long)getpid()) + ".conf";
    {
        std::ifstream in(machine + "/w31.conf"); std::string s((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        size_t p;
        while ((p = s.find("@MACHINE@")) != std::string::npos) s.replace(p, 9, "\"" + machine + "\"");
        while ((p = s.find("@DRIVE@")) != std::string::npos) s.replace(p, 7, "\"" + machine + "/drive\"");
        std::ofstream o(conf); o << s;
    }
    Machine M;
    M.S = (bshm *)std::calloc(1, sizeof(bshm));
    bshm *S = M.S;
    S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING;
    S->lead = 256; S->offline = 1; S->vid_want = 1;
    M.e = bs_engine_start(S, a["--core"].c_str(), conf.c_str(), (machine + "/w31.state").c_str(), nullptr, nullptr);
    while (S->state < BS_RUNNING && S->state != BS_FAILED) { S->grant_until = S->dac_w + 4800; S->host_beat++; nap(); }
    if (S->state == BS_FAILED) { std::fprintf(stderr, "demo311: %s\n", S->error); return 3; }

    std::string ff = "ffmpeg -y -hide_banner -loglevel error -f rawvideo -pix_fmt bgr0 -s 1024x768 -r " + std::to_string(fps) +
                     " -i - -c:v ffv1 -level 3 -pix_fmt bgr0 '" + a["--video"] + "'";
    FILE *vid = popen(ff.c_str(), "w");
    if (!vid) { std::fprintf(stderr, "demo311: cannot start ffmpeg\n"); return 3; }

    // the plugin's state
    Voices voices(48000); Cmd c[kMaxCmds];
    LInfo cache[kMaxLayers], staged[kMaxLayers];
    std::string written = "ding#16;R120",   // kDefaultDna (core/state.h)
                stagedText;
    Dna audioDna = applyMacros(parse(written)), stagedDna;
    bool inFlight = false, ready = false, built = false;
    cache[0] = {0, 16, 22050, 11466, true};   // the snapshot: DING in all sixteen
    voices.setDna(audioDna, c);
    voices.setLayerInfo(0, 0, 16, 22050, 11466);
    int cc1 = 0;
    uint32_t nextId = 0;
    const uint32_t kLat = 2880;
    const uint64_t anchor = S->dac_w + 1;
    const uint64_t kAhead = kLat + spf;   // a note asked for now sounds this much later (the plugin's latency, plus a frame)
    while (S->dac_w < anchor + kLat) { S->grant_until = anchor + kLat - S->lead; S->host_beat++; nap(); }
    auto sendEnvs = [&](const Dna &eff) {
        char b[200];
        for (int i = 0; i < kMaxLayers; i++) {
            static const Env none;
            const Layer *L = i < (int)eff.layers.size() ? &eff.layers[i] : nullptr;
            proto::lenv(b, sizeof b, i, 'a', L ? L->envA : none); b[std::strlen(b) - 1] = 0; M.send(b);
            proto::lenv(b, sizeof b, i, 'p', L ? L->envP : none); b[std::strlen(b) - 1] = 0; M.send(b);
        }
    };
    auto effective = [&](const std::string &text) {
        const Dna w0 = parse(text), base = applyMacros(w0);
        if (!cc1) return base;
        Dna w = w0; w.g.macro[0] = std::min(100, std::max(0, w0.g.macro[0] + (cc1 * 100 + 63) / 127));
        Dna d = applyMacros(w);
        return sigOf(d) == sigOf(base) ? d : base;
    };
    float gain = 1.f;   // the DNA's output gain G, applied as the plugin applies it (render311 from 1.2.1 does the same)
    auto adoptAudio = [&](const Dna &d) {
        gain = (float)std::pow(10.0, d.g.gainDb / 20.0);
        voices.setDna(d, c);
        for (int i = 0; i < kMaxLayers; i++) if (cache[i].known) voices.setLayerInfo(i, cache[i].first, cache[i].count, cache[i].rate, cache[i].frames);
    };

    // timeline: h (samples from the anchor) is what is on screen and heard at DAC sample anchor + h + kLat. Notes at
    // timeline t are stamped anchor + t + kLat; unstamped lines (show, cc, dna, go) for t are sent when h reaches t,
    // so a key goes down in the frame its note sounds
    struct Pending { uint64_t t; int kind; int a, b; };   // kind 0 note-on, 1 note-off
    std::vector<Pending> pend;
    std::vector<std::pair<uint64_t, std::string>> unstamped;
    uint64_t now = 0;                 // script clock, samples
    size_t pc = 0;
    std::string waiting;              // "ready" / "built"
    bool rec = true;
    std::vector<float> audio;
    uint64_t frames = 0, h = 0;
    std::vector<uint8_t> px(1024 * 768 * 4);
    int ccFrom = 0, ccTo = 0; uint64_t ccT0 = 0, ccT1 = 0; bool ccMove = false; int ccLast = -1;
    bool done = false;
    while (!done) {
        // run the script up to the present
        while (!done && waiting.empty() && pc < script.size()) {
            auto &w = script[pc];
            if (w[0] == "sleep") { const uint64_t until = now + (uint64_t)(std::atof(w[1].c_str()) * 48000); if (h < until) break; }
            pc++;
            if (w[0] == "sleep") continue;
            if (w[0] == "go") {
                char b[96];
                proto::hi(b, sizeof b); b[std::strlen(b) - 1] = 0; unstamped.push_back({h, b});
                proto::time(b, sizeof b, 1993, 11, 8, 12, 0, 0); b[std::strlen(b) - 1] = 0; unstamped.push_back({h, b});
                unstamped.push_back({h, "go"});
            } else if (w[0] == "dna") {
                std::string t = w[1];
                const Dna wr = parse(t);
                written = wr.canonical;
                const Dna d = effective(written);
                if (sigOf(d) == sigOf(audioDna)) { audioDna = d; adoptAudio(d); }
                else { stagedDna = d; inFlight = true; for (auto &s : staged) s = LInfo(); }
                unstamped.push_back({h, "dna " + written});
                char b[96]; proto::env(b, sizeof b, d.g); b[std::strlen(b) - 1] = 0; unstamped.push_back({h, b});
                built = false;
            } else if (w[0] == "waitfor") {
                if ((w[1] == "ready" && !ready) || (w[1] == "built" && !(built && !inFlight))) waiting = w[1];
            } else if (w[0] == "note") {
                const double du = std::atof(w[3].c_str());
                pend.push_back({h + kAhead, 0, std::atoi(w[1].c_str()), std::atoi(w[2].c_str())});
                pend.push_back({h + kAhead + (uint64_t)(du * 48000), 1, std::atoi(w[1].c_str()), 0});
            } else if (w[0] == "midi") {
                std::vector<MidiEv> ev; readMidi(w[1], ev);
                const double vs = w.size() > 2 ? std::atof(w[2].c_str()) / 100.0 : 1.0;
                for (auto &e : ev) {
                    const uint64_t t = h + kAhead + (uint64_t)(e.t * 48000);
                    if ((e.st & 0xF0) == 0x90 && e.b) pend.push_back({t, 0, e.a, std::max(1, std::min(127, (int)std::lround(e.b * vs)))});
                    else if ((e.st & 0xF0) == 0x80 || (e.st & 0xF0) == 0x90) pend.push_back({t, 1, e.a, 0});
                }
            } else if (w[0] == "cc1") {
                ccFrom = std::atoi(w[1].c_str()); ccTo = std::atoi(w[2].c_str());
                ccT0 = h; ccT1 = h + (uint64_t)(std::atof(w[3].c_str()) * 48000); ccMove = true;
            } else if (w[0] == "rec") rec = w[1] == "on";
            else if (w[0] == "end") done = true;
            now = h;
        }
        if (pc >= script.size() && waiting.empty()) done = true;
        if (done) break;

        const uint64_t blockEnd = h + spf;
        // mod wheel: one step per frame
        if (ccMove) {
            const double f = ccT1 > ccT0 ? std::min(1.0, (double)(h - ccT0) / (double)(ccT1 - ccT0)) : 1.0;
            const int v = (int)std::lround(ccFrom + (ccTo - ccFrom) * f);
            if (v != ccLast) {
                ccLast = v; cc1 = v;
                unstamped.push_back({h, "cc 1 " + std::to_string(v)});
                if (!inFlight) { const Dna d = effective(written); audioDna = d; adoptAudio(d); sendEnvs(d); }
            }
            if (f >= 1) ccMove = false;
        }
        // notes are sent kLat before they sound (Windows needs that long to arm the recorder), stamped with their DAC
        // sample; their keys go down when they sound
        std::stable_sort(pend.begin(), pend.end(), [](const Pending &x, const Pending &y) { return x.t < y.t || (x.t == y.t && x.kind > y.kind); });
        while (!pend.empty() && pend.front().t < blockEnd + kLat) {
            Pending p = pend.front(); pend.erase(pend.begin());
            const uint64_t at = anchor + p.t + kLat;
            int n = p.kind == 0 ? voices.noteOn(p.a, p.b, at, c) : voices.noteOff(p.a, at, c);
            for (int k = 0; k < n; k++) {
                uint64_t when = at;
                if (c[k].kind == Cmd::On && c[k].delayMs) { when += (uint64_t)c[k].delayMs * 48; c[k].delayMs = 0; }
                char line[64]; proto::cmd(line, sizeof line, c[k]); line[std::strlen(line) - 1] = 0;
                M.send(line, ++nextId, when);
            }
            unstamped.push_back({p.t, "show " + std::to_string(p.a) + " " + std::to_string(p.kind == 0 ? p.b : 0)});
        }
        // unstamped lines whose time has come (DAC at t + kLat)
        for (size_t i = 0; i < unstamped.size();) {
            if (unstamped[i].first <= h) { M.send(unstamped[i].second); unstamped.erase(unstamped.begin() + i); }
            else i++;
        }
        // Windows' replies
        std::vector<std::string> ls; M.lines(ls);
        for (auto &l : ls) {
            proto::Reply r = proto::parse(l);
            if (r.kind == proto::Reply::Ready) { ready = true; std::fprintf(stderr, "demo311: ready at %.2f s\n", h / 48000.0); }
            if (r.kind == proto::Reply::Layer && r.layer >= 0 && r.layer < kMaxLayers) {
                LInfo li{r.first, r.count, r.rate, r.frames, true};
                if (inFlight) staged[r.layer] = li;
                else { cache[r.layer] = li; voices.setLayerInfo(r.layer, r.first, r.count, r.rate, r.frames); }
            }
            if (r.kind == proto::Reply::Built) {
                std::fprintf(stderr, "demo311: built at %.2f s\n", h / 48000.0);
                if (inFlight) {
                    for (int i = 0; i < kMaxLayers; i++) cache[i] = staged[i];
                    audioDna = effective(written); adoptAudio(audioDna); inFlight = false;
                }
                built = true;
                sendEnvs(effective(written));
            }
            if (r.kind == proto::Reply::End) voices.end(r.rec);
        }
        if (waiting == "ready" && ready) { waiting.clear(); now = h; }
        if (waiting == "built" && built && !inFlight) { waiting.clear(); now = h; }

        // run the machine to the end of this frame (plus the latency), then take the DAC and the screen
        const uint64_t need = anchor + blockEnd + kLat;
        S->host_r = need - S->lead;
        while (S->dac_w < need && S->state != BS_FAILED) { S->grant_until = need - S->lead; S->host_beat++; nap(); }
        if (S->state == BS_FAILED) { std::fprintf(stderr, "demo311: %s\n", S->error); return 3; }
        if (rec) {
            for (uint64_t k = anchor + h + kLat; k < need; k++) {
                const uint32_t j = (uint32_t)(k % BSHM_RING);
                audio.push_back(S->ring[j * 2] * gain); audio.push_back(S->ring[j * 2 + 1] * gain);
            }
            for (int tries = 0; tries < 1000; tries++) {
                const uint32_t s0 = S->vid_seq;
                if (s0 & 1) { nap(); continue; }
                std::memcpy(px.data(), (const void *)S->vid, px.size());
                if (S->vid_seq == s0) break;
            }
            std::fwrite(px.data(), 1, px.size(), vid);
            frames++;
        }
        h = blockEnd;
    }
    pclose(vid);
    writeWavFloat(a["--audio"], audio);
    bs_engine_stop(M.e);
    std::remove(conf.c_str());
    std::fprintf(stderr, "demo311: %llu frames, %.2f s; late notes %u of %u\n", (unsigned long long)frames, frames / (double)fps,
                 S->sched_late, S->sched_late + S->sched_ontime);
    std::free(S);
    return 0;
}
