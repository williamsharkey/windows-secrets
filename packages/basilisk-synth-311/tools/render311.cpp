// render311: DNA + MIDI -> WAV through the real Windows 3.11 machine (DOSBox Pure with the BSYN card), headless.
//
//   render311 --machine DIR --core FILE --dna "DNA" (--midi in.mid | --score "t:note:vel:dur,...") --out out.wav
//             [--tail SECONDS] [--log FILE] [--bits 24|32] [--bpm BPM]   (BPM: the tempo for v3 Wt, Wb, Wg; 120)
//
// --score: notes as t:note:velocity:duration in seconds (the format of packages/basilisk-synth/tools/batch_render.py).
// DNA v2 (DNA.md 5): library NAMEs come from DIR/library.names.txt; macros are applied as the plugin applies them.
//
// The machine resumes from its snapshot, skips the assembly animation (no screen), builds the DNA with Sound
// Recorder's own commands, and plays the MIDI file note by note through the recorders, exactly as the plugin does
// offline: every note is stamped with the DAC sample it must start on. It runs as fast as the emulator can (no real
// time pacing). Output: 48 kHz stereo WAV (24-bit, or 32-bit float with --bits 32), aligned to the notes (the latency
// is already removed).
#include "../engine/engine.h"
#include "../../basilisk-synth/core/dna.h"
#include "../../basilisk-synth/core/voices.h"
#include "../../basilisk-synth/core/proto.h"
#include "../plugin/V3Voice.h"
#include "../plugin/V3Alloc.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <string>
#include <thread>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

using namespace bsynth;

static double nowSec() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
static void nap() { std::this_thread::sleep_for(std::chrono::microseconds(200)); }

struct MidiEv { double t; uint8_t st, a, b; };

static uint32_t be32(const uint8_t *p) { return (p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3]; }
static uint16_t be16(const uint8_t *p) { return (p[0] << 8) | p[1]; }

// a Standard MIDI File (format 0 or 1) -> events in seconds (tempo map applied)
static bool readMidi(const std::string &path, std::vector<MidiEv> &out)
{
    std::ifstream f(path, std::ios::binary);
    std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    if (d.size() < 14 || std::memcmp(d.data(), "MThd", 4)) return false;
    const int ntrk = be16(&d[10]), div = be16(&d[12]);
    if (div & 0x8000) return false;   // SMPTE timing: not supported
    struct Raw { uint64_t tick; int order; uint8_t st, a, b; uint32_t tempo; bool isTempo; };
    std::vector<Raw> raw;
    size_t p = 8 + be32(&d[4]);
    int order = 0;
    for (int t = 0; t < ntrk && p + 8 <= d.size(); t++) {
        if (std::memcmp(&d[p], "MTrk", 4)) return false;
        size_t end = p + 8 + be32(&d[p + 4]); p += 8;
        uint64_t tick = 0; uint8_t run = 0;
        while (p < end && p < d.size()) {
            uint32_t dt = 0; uint8_t c;
            do { c = d[p++]; dt = (dt << 7) | (c & 0x7F); } while ((c & 0x80) && p < end);
            tick += dt;
            uint8_t st = d[p];
            if (st & 0x80) p++; else st = run;
            if (st == 0xFF) {
                uint8_t type = d[p++]; uint32_t len = 0;
                do { c = d[p++]; len = (len << 7) | (c & 0x7F); } while (c & 0x80);
                if (type == 0x51 && len == 3) raw.push_back({tick, order++, 0, 0, 0, (uint32_t)((d[p] << 16) | (d[p + 1] << 8) | d[p + 2]), true});
                p += len;
            } else if (st == 0xF0 || st == 0xF7) {
                uint32_t len = 0;
                do { c = d[p++]; len = (len << 7) | (c & 0x7F); } while (c & 0x80);
                p += len;
            } else {
                run = st;
                const int n = ((st & 0xF0) == 0xC0 || (st & 0xF0) == 0xD0) ? 1 : 2;
                uint8_t a = d[p++], b = n == 2 ? d[p++] : 0;
                raw.push_back({tick, order++, st, a, b, 0, false});
            }
        }
        p = end;
    }
    std::stable_sort(raw.begin(), raw.end(), [](const Raw &x, const Raw &y) { return x.tick < y.tick; });
    double sec = 0; uint64_t last = 0; double spt = 0.5 / div;   // 120 bpm
    for (auto &r : raw) {
        sec += (r.tick - last) * spt; last = r.tick;
        if (r.isTempo) { spt = r.tempo / 1e6 / div; continue; }
        out.push_back({sec, r.st, r.a, r.b});
    }
    return true;
}

static bool readScore(const std::string &s, std::vector<MidiEv> &out)
{
    size_t p = 0;
    while (p < s.size()) {
        size_t q = s.find(',', p); if (q == std::string::npos) q = s.size();
        double t, du; int n, v;
        if (std::sscanf(s.substr(p, q - p).c_str(), "%lf:%d:%d:%lf", &t, &n, &v, &du) != 4) return false;
        out.push_back({t, 0x90, (uint8_t)n, (uint8_t)(v < 1 ? 1 : v > 127 ? 127 : v)});
        out.push_back({t + du, 0x80, (uint8_t)n, 0});
        p = q + 1;
    }
    std::stable_sort(out.begin(), out.end(), [](const MidiEv &x, const MidiEv &y) { return x.t < y.t; });
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

static void writeWav(const std::string &path, const std::vector<float> &lr)
{
    FILE *f = std::fopen(path.c_str(), "wb");
    const uint32_t frames = (uint32_t)(lr.size() / 2), data = frames * 6;
    auto u32 = [&](uint32_t v) { std::fwrite(&v, 4, 1, f); };
    auto u16 = [&](uint16_t v) { std::fwrite(&v, 2, 1, f); };
    std::fwrite("RIFF", 1, 4, f); u32(36 + data); std::fwrite("WAVEfmt ", 1, 8, f);
    u32(16); u16(1); u16(2); u32(48000); u32(48000 * 6); u16(6); u16(24);
    std::fwrite("data", 1, 4, f); u32(data);
    for (float x : lr) {
        double v = x < -1 ? -1 : x > 1 ? 1 : x;
        int32_t s = (int32_t)std::lround(v * 8388607.0);
        uint8_t b[3] = {(uint8_t)s, (uint8_t)(s >> 8), (uint8_t)(s >> 16)};
        std::fwrite(b, 1, 3, f);
    }
    std::fclose(f);
}

struct Machine {
    bshm *S = nullptr;
    bs_engine *e = nullptr;
    std::vector<uint16_t> words; std::string frag;
    uint32_t nextId = 0;

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
            // through the event ring, delivered by the engine thread between frames (calling into the card from this
            // thread hangs Sound Recorder's first playback under Rosetta on macOS x86_64)
            while (S->ev_w - S->ev_r >= BSHM_EV) nap();
            bshm_ev &q = S->ev[S->ev_w % BSHM_EV];
            std::memcpy(q.w, w, sizeof(uint16_t) * nw); q.n = (uint32_t)nw; q.id = last ? id : 0; q.at = last ? at : 0;
            __sync_synchronize();
            S->ev_w++;
            pos += m;
        } while (pos < len);
    }
    // Windows' replies, as lines
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
    // let the engine run (no host to pace it): up to `upto` DAC samples
    void runTo(uint64_t upto)
    {
        S->grant_until = upto > S->lead ? upto - S->lead : 0;
        S->host_beat++;
    }
};

static std::string tempConf()
{
#ifdef _WIN32
    char d[MAX_PATH]; GetTempPathA(MAX_PATH, d);
    return std::string(d) + "render311-" + std::to_string((unsigned long)GetCurrentProcessId()) + ".conf";
#else
    const char *t = std::getenv("TMPDIR");
    return std::string(t && *t ? t : "/tmp") + "/render311-" + std::to_string((long)getpid()) + ".conf";
#endif
}

int main(int argc, char **argv)
{
    std::map<std::string, std::string> a;
    for (int i = 1; i + 1 < argc; i += 2) a[argv[i]] = argv[i + 1];
    if (!a.count("--machine") || !a.count("--core") || !a.count("--dna") || (!a.count("--midi") && !a.count("--score")) || !a.count("--out")) {
        std::fprintf(stderr, "render311 --machine DIR --core FILE --dna DNA (--midi IN.mid | --score t:note:vel:dur,...) --out OUT.wav [--tail SECONDS] [--log FILE] [--bits 24|32]\n");
        return 2;
    }
    std::vector<MidiEv> ev;
    if (a.count("--score")) { if (!readScore(a["--score"], ev)) { std::fprintf(stderr, "render311: bad --score\n"); return 2; } }
    else if (!readMidi(a["--midi"], ev)) { std::fprintf(stderr, "render311: cannot read %s\n", a["--midi"].c_str()); return 2; }
    const double tail = a.count("--tail") ? std::atof(a["--tail"].c_str()) : 3.0;
    const double bpm = a.count("--bpm") ? std::atof(a["--bpm"].c_str()) : 120.0;   // v3 Wt, Wb, Wg
    const std::string machine = a["--machine"];
    const double t0 = nowSec();
    {   // the library disc's NAMEs (DNA.md 5.5)
        std::ifstream in(machine + "/library.names.txt"); std::vector<std::string> names; std::string l;
        while (std::getline(in, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) names.push_back(l); }
        setLibrary(names);
    }

    // the machine's settings, with its own folder filled in
    // (its own file: batch jobs run side by side on one machine folder)
    std::string conf = tempConf();
    {
        std::ifstream in(machine + "/w31.conf"); std::string s((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
        size_t p;
        while ((p = s.find("@MACHINE@")) != std::string::npos) s.replace(p, 9, "\"" + machine + "\"");
        while ((p = s.find("@DRIVE@")) != std::string::npos) s.replace(p, 7, "\"" + machine + "/drive\"");
        std::ofstream o(conf); o << s;
    }
#if defined(__APPLE__) && defined(__aarch64__)
    std::string state = machine + "/w31-arm64.state";
#elif defined(__APPLE__)
    std::string state = machine + "/w31-x86_64.state";
#else
    std::string state = machine + "/w31.state";
#endif
    Machine M;
    M.S = (bshm *)std::calloc(1, sizeof(bshm));
    bshm *S = M.S;
    S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING;
    S->lead = 1024; S->offline = 1; S->vid_want = 0;
    M.e = bs_engine_start(S, a["--core"].c_str(), conf.c_str(), state.c_str(), nullptr, a.count("--log") ? a["--log"].c_str() : nullptr);
    while (S->state < BS_RUNNING && S->state != BS_FAILED) { M.runTo(S->dac_w + 48000); nap(); }
    if (S->state == BS_FAILED) { std::fprintf(stderr, "render311: %s\n", S->error); return 3; }

    // the DNA, built by Sound Recorder (no assembly animation: nobody is watching)
    const Dna written = parse(a["--dna"]);
    const Dna dna = applyMacros(written);   // what sounds (as the plugin does it)
    const bsynth3::Dna3 d3 = bsynth3::applyMacros3(bsynth3::parse3(written.canonical), written.g.macro);   // DNA v3
    const uint32_t d3salt = b16v3::salt(written.canonical);
    uint32_t v3counter = 0, lframes[kMaxLayers] = {}; int lrate[kMaxLayers] = {};
    bool win = false, loopCap = false;
    Voices voices(48000); Cmd c[kMaxCmds];
    voices.setDna(dna, c);
    b16v3::V3Alloc v3; v3.setDna(dna, d3); v3.setBpm(bpm);   // the layers with N, S or D, and live bend (as the plugin)
    std::vector<b16v3::Out> vo;
    bool rateCap = false;
    M.send("hi 3");   // DNA v3: the guest answers with its caps
    for (bool hi = false; !hi && S->state != BS_FAILED;) {   // Windows answers before it gets the sound (as the plugin does)
        M.runTo(S->dac_w + 4800); nap();
        std::vector<std::string> ls; M.lines(ls);
        for (auto &l : ls) { if (std::getenv("RENDER311_VERBOSE")) std::fprintf(stderr, "windows: %s\n", l.c_str()); if (l.rfind("hi ", 0) == 0) { hi = true; win = bsynth3::hasCap(bsynth3::parseHi3(l), "win"); loopCap = bsynth3::hasCap(bsynth3::parseHi3(l), "loop"); rateCap = bsynth3::hasCap(bsynth3::parseHi3(l), "rate"); } }
    }
    M.send("dna " + written.canonical);     // as written: Windows does N itself
    char b[160]; proto::env(b, sizeof b, dna.g); b[std::strlen(b) - 1] = 0; M.send(b);
    for (bool built = false; !built;) {
        M.runTo(S->dac_w + 48000); nap();
        std::vector<std::string> ls; M.lines(ls);
        for (auto &l : ls) {
            if (std::getenv("RENDER311_VERBOSE")) std::fprintf(stderr, "windows: %s\n", l.c_str());   // Windows' replies, for debugging
            proto::Reply r = proto::parse(l);
            if (r.kind == proto::Reply::Layer) {
                v3.setLayerInfo(r.layer, r.first, r.count, r.rate, r.frames);
                voices.setLayerInfo(r.layer, r.first, v3.owns(r.layer) ? 0 : r.count, r.rate, r.frames);
                if (r.layer >= 0 && r.layer < kMaxLayers) { lframes[r.layer] = (uint32_t)r.frames; lrate[r.layer] = r.rate; }
            }
            if (r.kind == proto::Reply::Built) built = true;
        }
        if (S->state == BS_FAILED) { std::fprintf(stderr, "render311: %s\n", S->error); return 3; }
    }
    for (int i = 0; i < kMaxLayers; i++) {   // the layers' drawn envelopes, macros applied
        static const Env none;
        const Layer *L = i < (int)dna.layers.size() ? &dna.layers[i] : nullptr;
        M.send(b16v3::lenvLine(i, 'a', L ? L->envA : none, d3, bpm, loopCap).c_str());
        M.send(b16v3::lenvLine(i, 'p', L ? L->envP : none, d3, bpm, loopCap).c_str());
    }
    const double tBuilt = nowSec();

    // play: every note stamped kLat DAC samples after its time; the output starts kLat after the anchor
    const uint32_t kLat = 2880, kBlock = 512;
    const uint64_t anchor = S->dac_w + 1;
    const double endSec = (ev.empty() ? 0 : ev.back().t) + tail;
    const uint64_t total = (uint64_t)(endSec * 48000) + kLat;   // the first kLat samples are dropped at the end
    std::vector<float> out; out.reserve(total * 2);
    size_t ei = 0;
    double bend = 0;
    for (uint64_t h = 0; h < total; h += kBlock) {
        const uint64_t blockEnd = h + kBlock;
        while (ei < ev.size() && (uint64_t)(ev[ei].t * 48000) < blockEnd) {
            const MidiEv &m = ev[ei++];
            const uint64_t at = anchor + (uint64_t)(m.t * 48000) + kLat;
            const uint8_t st = m.st & 0xF0;
            int n = 0;
            vo.clear();
            if (st == 0x90 && m.b > 0) { n = voices.noteOn(m.a, m.b, at, c); v3.noteOn(m.a, m.b, at, vo); }
            else if (st == 0x80 || st == 0x90) { n = voices.noteOff(m.a, at, c); v3.noteOff(m.a, at, vo); }
            else if (st == 0xB0 && m.a == 64) { n = voices.sustain(m.b >= 64, at, c); v3.sustain(m.b >= 64, at, vo); }
            else if (st == 0xB0 && (m.a == 120 || m.a == 123)) { n = voices.allOff(c); v3.allOff(); }
            else if (st == 0xE0) { bend = (((m.b << 7) | m.a) - 8192) / 8192.0; voices.bend(bend); if (rateCap) v3.bend(bend, at, vo); }
            for (int k = 0; k < n; k++) v3.follow(c[k], c[k].layer < dna.layers.size() && dna.layers[c[k].layer].fixed);
            auto sendCmd = [&](Cmd cm) {
                uint64_t when = at;
                if (cm.kind == Cmd::On) { when += b16v3::delay48(d3, cm, bpm); cm.delayMs = 0; }   // O (v3: Wo, Wb, Wt; S strum), as the plugin
                if (cm.kind == Cmd::On && win) {   // DNA v3 window and random draws, as the plugin (V3Voice.h)
                    const int L = cm.layer < kMaxLayers ? cm.layer : 0;
                    const b16v3::NoteOut o = b16v3::note(d3, cm, m.b, when, lframes[L], lrate[L], v3counter, d3salt, true, bpm);
                    M.send(o.on, ++M.nextId, o.when);
                    if (o.cut) { char cl[32]; std::snprintf(cl, sizeof cl, "cut %d", cm.rec); M.send(cl, ++M.nextId, o.cutAt); }
                    if (o.gate && (!o.cut || o.gateAt < o.cutAt)) { char cl[32]; std::snprintf(cl, sizeof cl, "off %d", cm.rec); M.send(cl, ++M.nextId, o.gateAt); }
                    return;
                }
                char line[64]; proto::cmd(line, sizeof line, cm); line[std::strlen(line) - 1] = 0;
                M.send(line, ++M.nextId, when);
            };
            for (int k = 0; k < n; k++) sendCmd(c[k]);
            for (const b16v3::Out &o : vo) {
                if (o.kind == b16v3::Out::Cmd) { sendCmd(o.c); continue; }
                if (!rateCap) continue;
                char line[64]; std::snprintf(line, sizeof line, "rate %d %u %d %d", o.rec, o.hz, o.glideMs, o.regate ? 1 : 0);
                M.send(line, ++M.nextId, o.at);
            }
        }
        // Windows' `end` replies free recorders, as in the plugin
        std::vector<std::string> ls; M.lines(ls);
        for (auto &l : ls) { proto::Reply r = proto::parse(l); if (r.kind == proto::Reply::End) { voices.end(r.rec); v3.end(r.rec); } }
        // the DAC for this block, exactly as the plugin reads it (host time h = DAC anchor + h); a note stamped at
        // t + kLat comes out kLat later, which is taken off at the end
        const uint64_t need = anchor + blockEnd;
        S->host_r = anchor + h;
        while (S->dac_w < need && S->state != BS_FAILED) { M.runTo(need); nap(); }
        for (uint64_t k = anchor + h; k < need; k++) {
            const uint32_t j = (uint32_t)(k % BSHM_RING);
            out.push_back(S->ring[j * 2]); out.push_back(S->ring[j * 2 + 1]);
        }
    }
    out.erase(out.begin(), out.begin() + 2 * (size_t)kLat);
    {   // the DNA's output gain G, applied as the plugin applies it
        const float g = (float)std::pow(10.0, dna.g.gainDb / 20.0);
        if (g != 1.f) for (float &x : out) x *= g;
    }
    if (a.count("--bits") && a["--bits"] == "32") writeWavFloat(a["--out"], out); else writeWav(a["--out"], out);
    bs_engine_stop(M.e);
    std::remove(conf.c_str());
    const double t1 = nowSec();
    std::fprintf(stderr, "render311: %.2f s of audio in %.2f s (resume+build %.2f s, play %.2f s: %.1fx real time); late notes %u of %u\n",
                 endSec, t1 - t0, tBuilt - t0, t1 - tBuilt, endSec / (t1 - tBuilt), S->sched_late, S->sched_late + S->sched_ontime);
    std::free(S);
    return 0;
}
