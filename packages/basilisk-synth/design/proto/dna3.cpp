// PRESET ENGINE 2 prototype: DNA v3 PROPOSAL tokens. See dna3.h and design/PRESET-ENGINE-2.md.
#include "dna3.h"
#include <cctype>
#include <cstdio>
#include <cstring>

namespace bsynth3 {

const Scale kScales[kScaleCount] = {
    {"major", 7, {0, 2, 4, 5, 7, 9, 11}},        {"minor", 7, {0, 2, 3, 5, 7, 8, 10}},
    {"dorian", 7, {0, 2, 3, 5, 7, 9, 10}},       {"phrygian", 7, {0, 1, 3, 5, 7, 8, 10}},
    {"lydian", 7, {0, 2, 4, 6, 7, 9, 11}},       {"mixolydian", 7, {0, 2, 4, 5, 7, 9, 10}},
    {"locrian", 7, {0, 1, 3, 5, 6, 8, 10}},      {"harmonic minor", 7, {0, 2, 3, 5, 7, 8, 11}},
    {"major pentatonic", 5, {0, 2, 4, 7, 9}},    {"minor pentatonic", 5, {0, 3, 5, 7, 10}},
    {"whole tone", 6, {0, 2, 4, 6, 8, 10}},      {"blues", 6, {0, 3, 5, 6, 7, 10}},
    {"chromatic", 8, {0, 1, 2, 3, 4, 5, 6, 7}},  // chromatic: handled in degreeToSemis (12 steps)
};

int degreeToSemis(int scale, int degree)
{
    if (scale < 0 || scale >= kScaleCount) scale = 0;
    if (scale == 12) return degree;   // chromatic
    const Scale &s = kScales[scale];
    int oct = degree >= 0 ? degree / s.n : -((-degree + s.n - 1) / s.n);
    int d = degree - oct * s.n;
    return oct * 12 + s.step[d];
}

bool isLayerLetter(char c) { return c == 'W' || c == 'N' || c == 'S' || c == 'Y' || c == 'V' || c == 'Z' || c == 'G'; }
bool isGlobalLetter(char c) { return c == 'q' || c == 'x'; }
static bool valch(char c) { return (c >= '0' && c <= '9') || c == '.' || c == ',' || c == '~'; }
// Each token letter has a closed set of subkeys. Any other character ends the token, so a v2 token that follows
// (for example a macro "m21L0,200" after "q0") is never read as part of it.
static const char *subkeys(char letter)
{
    switch (letter) {
    case 'W': return "selvm";
    case 'N': return "pmlcgk";
    case 'S': return "rxpgsdw";
    case 'Y': return "dltqkr";
    case 'V': return "wfs";
    case 'G': return "pjzncoesbfvwy";
    case 'q': return "r";
    case 'x': return "dgskpaolbfh";
    }
    return "";
}
static bool subOf(char letter, char c) { return c >= 'a' && c <= 'z' && std::strchr(subkeys(letter), c); }
static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

int readFrac(const std::string &s, size_t &p)
{
    long whole = 0, frac = 0, scale = kOne;
    bool any = false;
    while (p < s.size() && isdigit((unsigned char)s[p])) { if (whole < 100000) whole = whole * 10 + (s[p] - '0'); p++; any = true; }
    if (p < s.size() && s[p] == '.') {
        p++;
        while (p < s.size() && isdigit((unsigned char)s[p])) {
            if (scale > 1) { scale /= 10; frac += (s[p] - '0') * scale; }
            p++; any = true;
        }
    }
    if (!any) return 0;
    long v = whole * kOne + frac;
    return (int)(v > 4L * kOne ? 4L * kOne : v);   // callers clamp to their own range (scan allows up to 4x)
}
std::string fracText(int v)
{
    if (v <= 0) return "0";
    if (v % kOne == 0) return std::to_string(v / kOne);
    char b[16];
    std::snprintf(b, sizeof b, "%d.%04d", v / kOne, v % kOne);
    std::string t = b;
    while (t.back() == '0') t.pop_back();
    if (t[0] == '0') t.erase(0, 1);   // ".25"
    return t;
}
static int readInt(const std::string &s, size_t &p, int dflt)
{
    if (p >= s.size() || !isdigit((unsigned char)s[p])) return dflt;
    long v = 0;
    while (p < s.size() && isdigit((unsigned char)s[p])) { if (v < 100000000) v = v * 10 + (s[p] - '0'); p++; }
    return (int)v;
}
static Range readFracRange(const std::string &s, size_t &p, int hiMax)
{
    Range r;
    r.lo = r.hi = clampi(readFrac(s, p), 0, hiMax);
    if (p < s.size() && s[p] == '~') { p++; r.hi = clampi(readFrac(s, p), 0, hiMax); if (r.hi < r.lo) std::swap(r.hi, r.lo); }
    return r;
}
static std::string rangeText(const Range &r) { return fracText(r.lo) + (r.random() ? "~" + fracText(r.hi) : ""); }

// One v3 layer token starting at s[p] (the letter). Fills L, advances p past the token.
static void layerToken(const std::string &s, size_t &p, Layer3 &L)
{
    char letter = s[p++];
    if (letter == 'Z') {   // Z<lo>,<hi>[,<root>]: MIDI notes, no subkeys
        L.z.given = true;
        L.z.lo = clampi(readInt(s, p, 0), 0, 127);
        L.z.hi = 127;
        if (p < s.size() && s[p] == ',') { p++; L.z.hi = clampi(readInt(s, p, 127), 0, 127); }
        if (p < s.size() && s[p] == ',') { p++; L.z.root = clampi(readInt(s, p, 60), 0, 127); }
        if (L.z.hi < L.z.lo) std::swap(L.z.lo, L.z.hi);
        while (p < s.size() && valch(s[p])) p++;
        return;
    }
    while (p < s.size() && subOf(letter, s[p])) {
        char k = s[p++];
        switch (letter) {
        case 'W':
            L.w.given = true;
            if (k == 's') L.w.s = readFracRange(s, p, kOne);
            else if (k == 'e') L.w.e = readFracRange(s, p, kOne);
            else if (k == 'l') L.w.l = readFracRange(s, p, kOne);
            else if (k == 'v') L.w.vel = clampi(readFrac(s, p), 0, kOne);
            else if (k == 'm') L.w.maxMs = clampi(readInt(s, p, 0), 0, 30000);
            break;
        case 'N':
            L.n.given = true;
            if (k == 'p') { L.n.mode = 'p'; L.n.poly = clampi(readInt(s, p, 0), 0, 16); }
            else if (k == 'm' || k == 'l' || k == 'c') L.n.mode = k;
            else if (k == 'g') L.n.glideMs = clampi(readInt(s, p, 0), 0, 5000);
            else if (k == 'k' && p < s.size() && (s[p] == 'n' || s[p] == 'h' || s[p] == 'l')) L.n.prio = s[p++];
            break;
        case 'S':
            L.s.given = true;
            if (k == 'r') L.s.roundRobin = true;
            else if (k == 'x') { if (L.s.group) L.s.groupRandom = true; else L.s.randomPick = true; }
            else if (k == 'p') L.s.randomRec = true;
            else if (k == 'g') L.s.group = clampi(readInt(s, p, 1), 1, 8);
            else if (k == 's') L.s.strumMs = clampi(readInt(s, p, 0), 0, 500);
            else if (k == 'd') L.s.diatonic = clampi(readInt(s, p, 3), 2, 5);
            else if (k == 'w') L.s.width = clampi(readFrac(s, p), 0, kOne);
            break;
        case 'Y':
            L.y.given = true;
            if (k == 'd') L.y.detune = clampi(readInt(s, p, 0), 0, 100);
            else if (k == 'l') L.y.level = clampi(readInt(s, p, 0), 0, 100);
            else if (k == 't') L.y.timeMs = clampi(readInt(s, p, 0), 0, 200);
            else if (k == 'q') L.y.pan = clampi(readInt(s, p, 0), 0, 100);
            else if (k == 'k') L.y.perKey = true;
            else if (k == 'r') L.y.perRec = true;
            break;
        case 'V': {
            L.v.given = true;
            int a = readInt(s, p, 0), b = 0;
            if (p < s.size() && s[p] == ',') { p++; b = readInt(s, p, 0); }
            if (k == 'w') { L.v.wowCents = clampi(a, 0, 100); L.v.wowDeciHz = clampi(b, 1, 100); }
            else if (k == 'f') { L.v.fluCents = clampi(a, 0, 50); L.v.fluHz = clampi(b, 1, 30); }
            else if (k == 's') { L.v.scoopCents = clampi(a, 0, 200); L.v.scoopMs = clampi(b, 0, 2000); }
            break; }
        case 'G':
            L.g.on = true;
            if (k == 'p') L.g.pos = clampi(readFrac(s, p), 0, kOne);
            else if (k == 'j') L.g.spray = clampi(readFrac(s, p), 0, kOne);
            else if (k == 'z') {
                L.g.sizeMs = L.g.sizeHiMs = clampi(readInt(s, p, 80), 5, 2000);
                if (p < s.size() && s[p] == '~') { p++; L.g.sizeHiMs = clampi(readInt(s, p, L.g.sizeMs), L.g.sizeMs, 2000); }
            }
            else if (k == 'n') L.g.density = clampi(readInt(s, p, 20), 1, 200);
            else if (k == 'c') L.g.cents = clampi(readInt(s, p, 0), 0, 1200);
            else if (k == 'o') L.g.octPct = clampi(readInt(s, p, 0), 0, 100);
            else if (k == 'e') L.g.shape = clampi(readInt(s, p, 2), 0, 3);
            else if (k == 's') L.g.scan = clampi(readFrac(s, p), 0, 4 * kOne);
            else if (k == 'b') L.g.back = true;
            else if (k == 'f') L.g.freeze = true;
            else if (k == 'v') L.g.streams = clampi(readInt(s, p, 4), 1, 16);
            else if (k == 'w') L.g.width = clampi(readFrac(s, p), 0, kOne);
            else if (k == 'y') L.g.sync = true;
            break;
        }
        while (p < s.size() && valch(s[p])) p++;   // an unknown subkey's value: skipped
    }
    while (p < s.size() && valch(s[p])) p++;
}

static void globalToken(const std::string &s, size_t &p, Globals3 &g)
{
    char letter = s[p++];
    if (letter == 'q') {
        g.scale = clampi(readInt(s, p, 0), 0, kScaleCount - 1);
        if (p < s.size() && s[p] == 'r') { p++; g.rootPc = clampi(readInt(s, p, 0), 0, 11); }
        return;
    }
    g.x.on = true;
    while (p < s.size() && subOf(letter, s[p])) {
        char k = s[p++];
        if (letter == 'x') {
            Seq &x = g.x;
            switch (k) {
            case 'd': { int d = readInt(s, p, 16); x.div = d <= 4 ? 4 : d <= 8 ? 8 : d <= 16 ? 16 : 32;
                        if (p < s.size() && s[p] == 't') { p++; x.triplet = true; } break; }
            case 'g': x.gate = clampi(readInt(s, p, 80), 5, 100); break;
            case 's': x.swing = clampi(readInt(s, p, 0), 0, 75); break;
            case 'k': x.kind = clampi(readInt(s, p, 0), 0, 2); break;
            case 'p': x.poly = clampi(readInt(s, p, 4), 1, 16); break;
            case 'a': x.autodig = clampi(readInt(s, p, 3), 0, 30); break;
            case 'o': x.octaves = clampi(readInt(s, p, 2), 1, 4); break;
            case 'l': x.len = clampi(readInt(s, p, 0), 0, 30); break;
            case 'b': x.bpm = clampi(readInt(s, p, 120), 20, 300); break;
            case 'f': x.freeRun = true; break;
            case 'h': x.latch = true; break;
            }
        }
        while (p < s.size() && valch(s[p])) p++;
    }
    while (p < s.size() && valch(s[p])) p++;
}

// Walk the DNA as core does. For each layer: skip the source NAME and every I/M NAME (lowercase, so they never hold
// a v3 letter); any v3 letter starts a token. In the globals no v2 token holds 'q' or 'x'.
// keep(b, e): text [b, e) that is not a v3 token.
template <class OnLayer, class OnGlobal, class Keep>
static void walk(const std::string &s, OnLayer onLayer, OnGlobal onGlobal, Keep keep)
{
    size_t p = 0;
    int li = 0;
    auto name = [&](size_t &q) { while (q < s.size() && ((s[q] >= 'a' && s[q] <= 'z') || isdigit((unsigned char)s[q]) || s[q] == '_')) q++; };
    while (p < s.size() && s[p] != ';') {
        size_t b = p; name(p); keep(b, p);
        while (p < s.size() && s[p] != '/' && s[p] != ';') {
            if (isLayerLetter(s[p])) { onLayer(li, p); continue; }
            size_t b3 = p;
            char c = s[p++];
            if (c == 'I' || c == 'M') name(p);
            keep(b3, p);
        }
        li++;
        if (p < s.size() && s[p] == '/') { keep(p, p + 1); p++; }
    }
    if (p < s.size() && s[p] == ';') {
        keep(p, p + 1); p++;
        while (p < s.size()) {
            if (isGlobalLetter(s[p])) { onGlobal(p); continue; }
            keep(p, p + 1); p++;
        }
    }
}

static std::string clean(const std::string &in)
{
    std::string t;
    for (char c : in.substr(0, 1024)) if (c > ' ' && c <= '~') t += c;
    return t;
}

Dna3 parse3(const std::string &in)
{
    std::string s = clean(in);
    Dna3 d;
    walk(s,
         [&](int li, size_t &p) {
             while ((int)d.layers.size() <= li) d.layers.emplace_back();
             layerToken(s, p, d.layers[li]);
         },
         [&](size_t &p) { globalToken(s, p, d.g); },
         [&](size_t, size_t) {});
    // layers with no v3 token still get an entry, so indices match core's layers
    int n = 1;
    for (char c : s) { if (c == ';') break; if (c == '/') n++; }
    while ((int)d.layers.size() < n && (int)d.layers.size() < 8) d.layers.emplace_back();
    if ((int)d.layers.size() > 8) d.layers.resize(8);
    for (auto &L : d.layers) { std::string t = layerTokens(L); if (!t.empty()) L.tokens.push_back(t); }
    std::string gt = globalTokens(d.g);
    if (!gt.empty()) d.g.tokens.push_back(gt);
    return d;
}

std::string strip3(const std::string &in)
{
    std::string s = clean(in), out;
    Dna3 scratch;
    walk(s,
         [&](int, size_t &p) { Layer3 L; layerToken(s, p, L); },
         [&](size_t &p) { globalToken(s, p, scratch.g); },
         [&](size_t b, size_t e) { out.append(s, b, e - b); });
    return out;
}

std::string layerTokens(const Layer3 &L)
{
    std::string t;
    if (L.w.given) {
        Window def;
        std::string w;
        if (L.w.s.lo || L.w.s.hi) w += "s" + rangeText(L.w.s);
        if (L.w.e.lo != def.e.lo || L.w.e.hi != def.e.hi) w += "e" + rangeText(L.w.e);
        if (L.w.l.lo >= 0) w += "l" + rangeText(L.w.l);
        if (L.w.vel) w += "v" + fracText(L.w.vel);
        if (L.w.maxMs) w += "m" + std::to_string(L.w.maxMs);
        if (!w.empty()) t += "W" + w;
    }
    if (L.n.given) {
        std::string n = L.n.mode == 'p' ? "p" + (L.n.poly ? std::to_string(L.n.poly) : std::string()) : std::string(1, L.n.mode);
        if (L.n.glideMs) n += "g" + std::to_string(L.n.glideMs);
        if (L.n.prio != 'n') n += std::string("k") + L.n.prio;
        t += "N" + n;
    }
    if (L.s.given) {
        std::string x;
        if (L.s.roundRobin) x += "r";
        if (L.s.randomPick) x += "x";
        if (L.s.randomRec) x += "p";
        if (L.s.group) x += "g" + std::to_string(L.s.group) + (L.s.groupRandom ? "x" : "");
        if (L.s.strumMs) x += "s" + std::to_string(L.s.strumMs);
        if (L.s.diatonic) x += "d" + std::to_string(L.s.diatonic);
        if (L.s.width) x += "w" + fracText(L.s.width);
        if (!x.empty()) t += "S" + x;
    }
    if (L.y.given) {
        std::string y;
        if (L.y.detune) y += "d" + std::to_string(L.y.detune);
        if (L.y.level) y += "l" + std::to_string(L.y.level);
        if (L.y.timeMs) y += "t" + std::to_string(L.y.timeMs);
        if (L.y.pan) y += "q" + std::to_string(L.y.pan);
        if (L.y.perKey) y += "k";
        if (L.y.perRec) y += "r";
        if (!y.empty()) t += "Y" + y;
    }
    if (L.v.given) {
        std::string v;
        if (L.v.wowCents) v += "w" + std::to_string(L.v.wowCents) + "," + std::to_string(L.v.wowDeciHz);
        if (L.v.fluCents) v += "f" + std::to_string(L.v.fluCents) + "," + std::to_string(L.v.fluHz);
        if (L.v.scoopCents) v += "s" + std::to_string(L.v.scoopCents) + "," + std::to_string(L.v.scoopMs);
        if (!v.empty()) t += "V" + v;
    }
    if (L.z.given) {
        t += "Z" + std::to_string(L.z.lo) + "," + std::to_string(L.z.hi) + (L.z.root >= 0 ? "," + std::to_string(L.z.root) : "");
    }
    if (L.g.on) {
        Grain d;
        std::string g;
        if (L.g.pos) g += "p" + fracText(L.g.pos);
        if (L.g.spray) g += "j" + fracText(L.g.spray);
        if (L.g.sizeMs != d.sizeMs || L.g.sizeHiMs != d.sizeHiMs)
            g += "z" + std::to_string(L.g.sizeMs) + (L.g.sizeHiMs != L.g.sizeMs ? "~" + std::to_string(L.g.sizeHiMs) : "");
        if (L.g.density != d.density) g += "n" + std::to_string(L.g.density);
        if (L.g.cents) g += "c" + std::to_string(L.g.cents);
        if (L.g.octPct) g += "o" + std::to_string(L.g.octPct);
        if (L.g.shape != d.shape) g += "e" + std::to_string(L.g.shape);
        if (L.g.scan) g += "s" + fracText(L.g.scan);
        if (L.g.back) g += "b";
        if (L.g.freeze) g += "f";
        if (L.g.streams != d.streams) g += "v" + std::to_string(L.g.streams);
        if (L.g.width) g += "w" + fracText(L.g.width);
        if (L.g.sync) g += "y";
        t += "G" + g;
    }
    return t;
}

std::string globalTokens(const Globals3 &g)
{
    std::string t;
    if (g.scale >= 0) t += "q" + std::to_string(g.scale) + (g.rootPc >= 0 ? "r" + std::to_string(g.rootPc) : "");
    if (g.x.on) {
        Seq d;
        const Seq &x = g.x;
        t += "x";
        if (x.div != d.div || x.triplet) t += "d" + std::to_string(x.div) + (x.triplet ? "t" : "");
        if (x.gate != d.gate) t += "g" + std::to_string(x.gate);
        if (x.swing) t += "s" + std::to_string(x.swing);
        if (x.kind) t += "k" + std::to_string(x.kind);
        if (x.poly != d.poly) t += "p" + std::to_string(x.poly);
        if (x.autodig != d.autodig) t += "a" + std::to_string(x.autodig);
        if (x.octaves != d.octaves) t += "o" + std::to_string(x.octaves);
        if (x.len) t += "l" + std::to_string(x.len);
        if (x.bpm != d.bpm) t += "b" + std::to_string(x.bpm);
        if (x.freeRun) t += "f";
        if (x.latch) t += "h";
    }
    return t;
}

}  // namespace bsynth3
