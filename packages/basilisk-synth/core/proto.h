// BASILISK SYNTH shared core: the guest-link lines of DNA.md section 4, built and parsed identically by both editions.
// Builders write into a caller buffer (real-time safe, no allocation) and return the length, '\n' included.
#pragma once
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include "voices.h"

namespace bsynth {
namespace proto {

constexpr int kVersion = 2;
inline int hi(char *b, int n) { return std::snprintf(b, n, "hi %d\n", kVersion); }
inline int go(char *b, int n) { return std::snprintf(b, n, "go\n"); }
inline int dna(char *b, int n, const std::string &d) { return std::snprintf(b, n, "dna %s\n", d.c_str()); }
inline int on(char *b, int n, int rec, unsigned rate, unsigned vol) { return std::snprintf(b, n, "on %d %u %u\n", rec, rate, vol); }
// v2: on <rec> <rate> <vol> <pan> <delay_ms> <layer>
inline int on2(char *b, int n, int rec, unsigned rate, unsigned vol, int pan, unsigned delayMs, int layer)
{
    return std::snprintf(b, n, "on %d %u %u %d %u %d\n", rec, rate, vol, pan, delayMs, layer);
}
// v2: lenv <layer> <a|p> <t,l.t,l...|->
inline int lenv(char *b, int n, int layer, char which, const Env &e) { return std::snprintf(b, n, "lenv %d %c %s\n", layer, which, envText(e).c_str()); }
inline int off(char *b, int n, int rec) { return std::snprintf(b, n, "off %d\n", rec); }
inline int cut(char *b, int n, int rec) { return std::snprintf(b, n, "cut %d\n", rec); }
// XP 1.3: an offline render sends notes ahead; "off <rec> <delay_ms>" and "cut <rec> <delay_ms>" run that much later
// (only when the delay is not 0, so every other line is unchanged)
inline int off(char *b, int n, int rec, unsigned delayMs) { return delayMs ? std::snprintf(b, n, "off %d %u\n", rec, delayMs) : off(b, n, rec); }
inline int cut(char *b, int n, int rec, unsigned delayMs) { return delayMs ? std::snprintf(b, n, "cut %d %u\n", rec, delayMs) : cut(b, n, rec); }
inline int panic(char *b, int n) { return std::snprintf(b, n, "panic\n"); }
inline int env(char *b, int n, int a, int d, int s, int r) { return std::snprintf(b, n, "env %d %d %d %d\n", a, d, s, r); }
inline int time(char *b, int n, int Y, int M, int D, int h, int m, int s) { return std::snprintf(b, n, "time %d %d %d %d %d %d\n", Y, M, D, h, m, s); }
inline int sel(char *b, int n, int layer) { return std::snprintf(b, n, "sel %d\n", layer); }
inline int env(char *b, int n, const Globals &g) { return env(b, n, g.attack, g.decay, g.sustain, g.release); }
inline int cmd(char *b, int n, const Cmd &c)
{
    switch (c.kind) {
    case Cmd::On: return on2(b, n, c.rec, c.rateHz, c.vol, c.pan, c.delayMs, c.layer);
    case Cmd::Off: return off(b, n, c.rec, c.delayMs);
    case Cmd::Cut: return cut(b, n, c.rec, c.delayMs);
    case Cmd::Panic: return panic(b, n);
    }
    return 0;
}

// Guest -> host
struct Reply {
    enum Kind { Unknown, Hi, Ready, Layer, Built, End, Edit, Log } kind = Unknown;
    int version = 0;
    std::string edition, state, text;   // hi: edition/state; edit: DNA; log: text
    int layer = 0, first = 0, count = 0, rate = 0, frames = 0, ms = 0, rec = 0;
};
inline Reply parse(const std::string &line0)
{
    Reply r;
    std::string line = line0;
    while (!line.empty() && (line.back() == '\n' || line.back() == '\r')) line.pop_back();
    auto sp = line.find(' ');
    std::string w = line.substr(0, sp), rest = sp == std::string::npos ? "" : line.substr(sp + 1);
    if (w == "hi") {
        char ed[32] = {0}, st[32] = {0};
        if (std::sscanf(rest.c_str(), "%d %31s %31s", &r.version, ed, st) >= 1) { r.kind = Reply::Hi; r.edition = ed; r.state = st; }
    } else if (w == "ready") r.kind = Reply::Ready;
    else if (w == "layer") { if (std::sscanf(rest.c_str(), "%d %d %d %d %d", &r.layer, &r.first, &r.count, &r.rate, &r.frames) == 5) r.kind = Reply::Layer; }
    else if (w == "built") { r.kind = Reply::Built; r.ms = std::atoi(rest.c_str()); }
    else if (w == "end") { r.kind = Reply::End; r.rec = std::atoi(rest.c_str()); }
    else if (w == "edit") { r.kind = Reply::Edit; r.text = rest; }
    else if (w == "log") { r.kind = Reply::Log; r.text = rest; }
    return r;
}

}  // namespace proto
}  // namespace bsynth
