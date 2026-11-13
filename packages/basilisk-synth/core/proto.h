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

constexpr int kVersion = 1;
inline int hi(char *b, int n) { return std::snprintf(b, n, "hi %d\n", kVersion); }
inline int go(char *b, int n) { return std::snprintf(b, n, "go\n"); }
inline int dna(char *b, int n, const std::string &d) { return std::snprintf(b, n, "dna %s\n", d.c_str()); }
inline int on(char *b, int n, int rec, unsigned rate, unsigned vol) { return std::snprintf(b, n, "on %d %u %u\n", rec, rate, vol); }
inline int off(char *b, int n, int rec) { return std::snprintf(b, n, "off %d\n", rec); }
inline int cut(char *b, int n, int rec) { return std::snprintf(b, n, "cut %d\n", rec); }
inline int panic(char *b, int n) { return std::snprintf(b, n, "panic\n"); }
inline int env(char *b, int n, int a, int d, int s, int r) { return std::snprintf(b, n, "env %d %d %d %d\n", a, d, s, r); }
inline int time(char *b, int n, int Y, int M, int D, int h, int m, int s) { return std::snprintf(b, n, "time %d %d %d %d %d %d\n", Y, M, D, h, m, s); }
inline int sel(char *b, int n, int layer) { return std::snprintf(b, n, "sel %d\n", layer); }
inline int env(char *b, int n, const Globals &g) { return env(b, n, g.attack, g.decay, g.sustain, g.release); }
inline int cmd(char *b, int n, const Cmd &c)
{
    switch (c.kind) {
    case Cmd::On: return on(b, n, c.rec, c.rateHz, c.vol);
    case Cmd::Off: return off(b, n, c.rec);
    case Cmd::Cut: return cut(b, n, c.rec);
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
