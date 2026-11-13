// DNA v3 tokens. See dna3.h and design/PRESET-ENGINE-2.md section 2.
#include "dna3.h"
#include "dna.h"
#include <algorithm>
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
    {"chromatic", 12, {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11}},
};

int degreeToSemis(int scale, int degree)
{
    if (scale < 0 || scale >= kScaleCount) scale = 0;
    const Scale &s = kScales[scale];
    int oct = degree >= 0 ? degree / s.n : -((-degree + s.n - 1) / s.n);
    return oct * 12 + s.step[degree - oct * s.n];
}

bool isLayerLetter(char c) { return c && std::strchr(kLayerLetters, c) != nullptr; }
bool isGlobalLetter(char c) { return c == 'q' || c == 'x' || c == 'k'; }
bool isMacroParam3(char c) { return c && std::strchr(kMacroParams3, c) != nullptr; }
static bool valch(char c) { return (c >= '0' && c <= '9') || c == '.' || c == ',' || c == '~'; }
static bool lower(char c) { return c >= 'a' && c <= 'z'; }
// DNA.md 5.7: the body of a token. In the globals 'm' ends it, and (v3) so do the global letters q and x.
static bool bodych(char c, bool global) { return valch(c) || (lower(c) && !(global && (c == 'm' || isGlobalLetter(c)))); }
static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }
static int letterIndex(char c) { const char *p = std::strchr(kLayerLetters, c); return p ? (int)(p - kLayerLetters) : -1; }

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
    char b[24];
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
static int readSigned(const std::string &s, size_t &p, int dflt)
{
    bool neg = false;
    if (p < s.size() && (s[p] == '-' || s[p] == '+')) { neg = s[p] == '-'; p++; }
    int v = readInt(s, p, dflt);
    return neg ? -v : v;
}
static Range readFracRange(const std::string &s, size_t &p, int hiMax)
{
    Range r;
    r.lo = r.hi = clampi(readFrac(s, p), 0, hiMax);
    if (p < s.size() && s[p] == '~') { p++; r.hi = clampi(readFrac(s, p), 0, hiMax); if (r.hi < r.lo) std::swap(r.hi, r.lo); }
    return r;
}
static std::string rangeText(const Range &r) { return fracText(r.lo) + (r.random() ? "~" + fracText(r.hi) : ""); }
static void skipVals(const std::string &s, size_t &p) { while (p < s.size() && valch(s[p])) p++; }

// One v3 layer token starting at s[p] (the letter). Fills L, advances p past the token (DNA.md 5.7 boundary).
static void layerToken(const std::string &s, size_t &p, Layer3 &L)
{
    char letter = s[p++];
    int li = letterIndex(letter);
    L.has[li] = true;
    if (letter == 'Z') {   // Z<lo>,<hi>[,<root>]: MIDI notes, then (only) unknown subkeys
        Zone z;
        z.lo = clampi(readInt(s, p, 0), 0, 127);
        if (p < s.size() && s[p] == ',') { p++; z.hi = clampi(readInt(s, p, 127), 0, 127); }
        if (p < s.size() && s[p] == ',') { p++; z.root = clampi(readInt(s, p, 60), 0, 127); }
        if (z.hi < z.lo) std::swap(z.lo, z.hi);
        L.z = z;
    }
    while (p < s.size() && bodych(s[p], false)) {
        if (!lower(s[p])) { p++; continue; }      // a value with no subkey: not meaningful, dropped
        size_t k0 = p;
        char k = s[p++];
        bool known = true;
        switch (letter) {
        case 'W':
            if (k == 's') L.w.s = readFracRange(s, p, kOne);
            else if (k == 'e') L.w.e = readFracRange(s, p, kOne);
            else if (k == 'l') L.w.l = readFracRange(s, p, kOne);
            else if (k == 'v') L.w.vel = clampi(readFrac(s, p), 0, kOne);
            else if (k == 'm') L.w.maxMs = clampi(readInt(s, p, 0), 0, 30000);
            else if (k == 'o') L.w.offMs = clampi(readInt(s, p, 0), 0, 30000);
            else if (k == 'b') L.w.beat16 = clampi(readInt(s, p, 0), 0, 1024);
            else if (k == 'g') L.w.gate16 = clampi(readInt(s, p, 0), 0, 1024);
            else if (k == 't') L.w.tempo = true;
            else if (k == 'r') { int n = clampi(readInt(s, p, 2), 0, 8); L.w.loopA = n == 1 ? 2 : n; }
            else if (k == 'p') { int n = clampi(readInt(s, p, 2), 0, 8); L.w.loopP = n == 1 ? 2 : n; }
            else known = false;
            break;
        case 'N':
            if (k == 'p') { L.n.mode = 'p'; L.n.poly = clampi(readInt(s, p, 0), 0, 16); }
            else if (k == 'm' || k == 'l' || k == 'c') L.n.mode = k;
            else if (k == 'g') L.n.glideMs = clampi(readInt(s, p, 0), 0, 5000);
            else if (k == 'k') { if (p < s.size() && (s[p] == 'n' || s[p] == 'h' || s[p] == 'l')) L.n.prio = s[p++]; }
            else known = false;
            break;
        case 'S':
            if (k == 'r') L.s.roundRobin = true;
            else if (k == 'x') { if (L.s.group) L.s.groupRandom = true; else L.s.randomPick = true; }
            else if (k == 'p') L.s.randomRec = true;
            else if (k == 'g') L.s.group = clampi(readInt(s, p, 1), 1, 8);
            else if (k == 's') L.s.strumMs = clampi(readInt(s, p, 0), 0, 500);
            else if (k == 'w') L.s.width = clampi(readFrac(s, p), 0, kOne);
            else known = false;
            break;
        case 'Y':
            if (k == 'd') L.y.detune = clampi(readInt(s, p, 0), 0, 100);
            else if (k == 'l') L.y.level = clampi(readInt(s, p, 0), 0, 100);
            else if (k == 't') L.y.timeMs = clampi(readInt(s, p, 0), 0, 200);
            else if (k == 'q') L.y.pan = clampi(readInt(s, p, 0), 0, 100);
            else if (k == 'k') L.y.perKey = true;
            else if (k == 'r') L.y.perRec = true;
            else known = false;
            break;
        case 'V':
            if (k == 'w' || k == 'f' || k == 's') {
                int a = readInt(s, p, 0), b = 0;
                if (p < s.size() && s[p] == ',') { p++; b = readInt(s, p, 0); }
                if (k == 'w') { L.v.wowCents = clampi(a, 0, 100); L.v.wowDeciHz = clampi(b, 1, 100); }
                else if (k == 'f') { L.v.fluCents = clampi(a, 0, 50); L.v.fluHz = clampi(b, 1, 30); }
                else { L.v.scoopCents = clampi(a, 0, 200); L.v.scoopMs = clampi(b, 0, 2000); }
            } else known = false;
            break;
        case 'G':
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
            else known = false;
            break;
        case 'D': {
            auto list = [&](std::vector<int> &v) { v.clear(); do { if (p < s.size() && s[p] == ',') p++; int d = readInt(s, p, 0); if (d >= 1) v.push_back(clampi(d, 1, 64)); } while (p < s.size() && s[p] == ',' && v.size() < 8); };
            if (k == 'h') list(L.d.up);
            else if (k == 'b') list(L.d.down);
            else if (k == 'i') L.d.inversion = clampi(readInt(s, p, 0), 0, 8);
            else if (k == 's') L.d.snap = clampi(readInt(s, p, 0), 0, 4);
            else known = false;
            L.d.given = true;
            break; }
        default: known = false;   // Z has no subkeys
        }
        if (known) skipVals(s, p);                         // a malformed value tail is dropped
        else { skipVals(s, p); L.extra[li] += s.substr(k0, p - k0); }   // an unknown subkey: kept verbatim
    }
}

static void globalToken(const std::string &s, size_t &p, Globals3 &g)
{
    char letter = s[p++];
    Pad pad;
    bool isPad = false;
    if (letter == 'q') { g.hasQ = true; g.scale = clampi(readInt(s, p, 0), 0, 999); }
    else if (letter == 'k') {
        if (p < s.size() && isdigit((unsigned char)s[p])) {
            isPad = true;
            pad.lo = pad.hi = clampi(readInt(s, p, 0), 0, 127);
            if (p < s.size() && s[p] == ',') { p++; pad.hi = clampi(readInt(s, p, pad.lo), 0, 127); }
            if (pad.hi < pad.lo) std::swap(pad.lo, pad.hi);
        }
    }
    else g.x.on = true;
    while (p < s.size() && bodych(s[p], true)) {
        if (!lower(s[p])) { p++; continue; }
        size_t k0 = p;
        char k = s[p++];
        bool known = true;
        if (letter == 'q') {
            if (k == 'r') g.rootPc = clampi(readInt(s, p, 0), 0, 11);
            else if (k == 'n') g.mask = clampi(readInt(s, p, 0), 0, 4095) | 1;
            else if (k == 'e') g.edo = clampi(readInt(s, p, 12), 5, 72);
            else known = false;
        } else if (letter == 'k' && !isPad) {
            if (k == 'd') g.kitOff = true;
            else known = false;
        } else if (letter == 'k') {
            switch (k) {
            case 'l': pad.layer = clampi(readInt(s, p, 1), 1, 8); break;
            case 'j': pad.seg = clampi(readInt(s, p, 0), 0, 64); break;
            case 's': pad.s = readFracRange(s, p, kOne); break;
            case 'e': pad.e = readFracRange(s, p, kOne); break;
            case 'r': pad.root = clampi(readInt(s, p, 60), 0, 127); break;
            case 'p': pad.pitchPct = clampi(readInt(s, p, 100), 0, 100); break;
            case 'w': pad.rangeSemis = clampi(readInt(s, p, 0), 0, 48); break;
            case 't': pad.tuneCents = clampi(readInt(s, p, 0), 0, 1200); break;
            case 'b': pad.tuneCents = -clampi(readInt(s, p, 0), 0, 1200); break;
            case 'i': pad.level = clampi(readInt(s, p, 100), 0, 400); break;
            case 'h': pad.pan = clampi(readInt(s, p, 100), 0, 200) - 100; break;
            case 'v': pad.curve = clampi(readInt(s, p, 0), 0, 3); break;
            case 'a': pad.velAmount = clampi(readInt(s, p, 100), 0, 100); break;
            case 'y': pad.velLo = clampi(readInt(s, p, 1), 1, 127); pad.velHi = 127;
                      if (p < s.size() && s[p] == ',') { p++; pad.velHi = clampi(readInt(s, p, 127), 1, 127); }
                      if (pad.velHi < pad.velLo) std::swap(pad.velLo, pad.velHi);
                      break;
            case 'g': pad.gated = true; break;
            case 'c': pad.cut = clampi(readInt(s, p, 0), 0, 16); break;
            case 'f': pad.fadeMs = clampi(readInt(s, p, 10), 0, 2000); break;
            case 'u': pad.mutes.clear();
                      do { if (p < s.size() && s[p] == ',') p++; int m = readInt(s, p, -1); if (m >= 1 && m <= 16) pad.mutes.push_back(m); }
                      while (p < s.size() && s[p] == ',');
                      break;
            case 'n': pad.voices = clampi(readInt(s, p, 0), 0, 16); break;
            case 'o': pad.out = clampi(readInt(s, p, 1), 1, 8); break;
            case 'z': pad.random = true; break;
            default: known = false;
            }
        } else {
            Seq &x = g.x;
            switch (k) {
            case 'd': { int d = readInt(s, p, 16); x.div = d <= 4 ? 4 : d <= 8 ? 8 : d <= 16 ? 16 : 32;
                        if (p < s.size() && s[p] == 't') { p++; x.triplet = true; } break; }
            case 'g': x.gate = clampi(readInt(s, p, 80), 5, 100); break;
            case 's': x.swing = clampi(readInt(s, p, 0), 0, 75); break;
            case 'n': x.kind = clampi(readInt(s, p, 0), 0, 2); break;
            case 'p': x.poly = clampi(readInt(s, p, 4), 1, 16); break;
            case 'a': x.autodig = clampi(readInt(s, p, 3), 0, 30); break;
            case 'o': x.octaves = clampi(readInt(s, p, 2), 1, 4); break;
            case 'l': x.len = clampi(readInt(s, p, 0), 0, 30); break;
            case 'b': x.bpm = clampi(readInt(s, p, 120), 20, 300); break;
            case 'f': x.freeRun = true; break;
            case 'h': x.latch = true; break;
            default: known = false;
            }
        }
        skipVals(s, p);
        if (!known) (letter == 'q' ? g.qExtra : letter == 'x' ? g.xExtra : isPad ? pad.extra : g.kExtra) += s.substr(k0, p - k0);
    }
    if (isPad) g.pads.push_back(pad);
}

std::string Pad::token() const
{
    Pad d;
    std::string t = "k" + std::to_string(lo) + (hi != lo ? "," + std::to_string(hi) : "");
    if (layer != d.layer) t += "l" + std::to_string(layer);
    if (seg) t += "j" + std::to_string(seg);
    if (s.lo || s.hi) t += "s" + rangeText(s);
    if (e.lo != kOne || e.hi != kOne) t += "e" + rangeText(e);
    if (root >= 0 && root != lo) t += "r" + std::to_string(root);
    if (pitchPct) t += "p" + std::to_string(pitchPct);
    if (rangeSemis) t += "w" + std::to_string(rangeSemis);
    if (tuneCents > 0) t += "t" + std::to_string(tuneCents);
    if (tuneCents < 0) t += "b" + std::to_string(-tuneCents);
    if (level != 100) t += "i" + std::to_string(level);
    if (pan) t += "h" + std::to_string(pan + 100);
    if (curve) t += "v" + std::to_string(curve);
    if (velAmount >= 0) t += "a" + std::to_string(velAmount);
    if (velLo != 1 || velHi != 127) t += "y" + std::to_string(velLo) + "," + std::to_string(velHi);
    if (gated) t += "g";
    if (cut) t += "c" + std::to_string(cut);
    if (fadeMs != d.fadeMs) t += "f" + std::to_string(fadeMs);
    if (!mutes.empty()) { t += "u"; for (size_t i = 0; i < mutes.size(); i++) t += (i ? "," : "") + std::to_string(mutes[i]); }
    if (voices) t += "n" + std::to_string(voices);
    if (out != 1) t += "o" + std::to_string(out);
    if (random) t += "z";
    return t + extra;
}

// A macro token at s[p] == 'm', consumed as core consumes it (DNA.md 5.7). Returns true (and fills mm) when it is
// a v3 map: K 1..4, layer 0..8, parameter in kMacroParams3.
static bool macroToken(const std::string &s, size_t &p, MacroMap3 &mm)
{
    size_t from = ++p;
    if (p < s.size()) p++;                                             // K
    if (p < s.size() && s[p] == '=') p++;
    else {
        if (p < s.size() && isdigit((unsigned char)s[p])) p++;         // layer
        if (p < s.size() && isalpha((unsigned char)s[p]) && s[p] != 'm') p++;   // parameter
    }
    size_t vals = p;
    while (p < s.size() && (isdigit((unsigned char)s[p]) || std::strchr(",.~-", s[p]))) p++;
    if (vals - from != 3) return false;
    char K = s[from], L = s[from + 1], P = s[from + 2];
    if (K < '1' || K > '4' || L < '0' || L > '8' || !isMacroParam3(P)) return false;
    size_t q = vals;
    mm.macro = K - '0'; mm.layer = L - '0'; mm.param = P;
    mm.lo = mm.hi = readSigned(s, q, 0);
    if (q < p && s[q] == ',') { q++; mm.hi = readSigned(s, q, mm.lo); }
    return true;
}

// Walk the DNA as core does. Layers: skip the source NAME and every I/M NAME (lowercase, so they never hold a v3
// letter); a v3 letter starts a token. Globals: q and x start a token; a macro token is one unit.
// keep(b, e): text [b, e) that is not v3.
template <class OnLayer, class OnGlobal, class OnMacro, class Keep>
static void walk(const std::string &s, OnLayer onLayer, OnGlobal onGlobal, OnMacro onMacro, Keep keep)
{
    size_t p = 0;
    int li = 0;
    auto name = [&](size_t &q) { while (q < s.size() && (lower(s[q]) || isdigit((unsigned char)s[q]) || s[q] == '_')) q++; };
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
            if (s[p] == 'm') {
                size_t b = p;
                MacroMap3 mm;
                if (macroToken(s, p, mm)) onMacro(mm);
                else keep(b, p);
                continue;
            }
            keep(p, p + 1); p++;
        }
    }
}

// As core: at most 1024 bytes, then no spaces or non-printable characters.
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
    std::vector<Layer3> all;
    walk(s,
         [&](int li, size_t &p) { while ((int)all.size() <= li) all.emplace_back(); layerToken(s, p, all[li]); },
         [&](size_t &p) { globalToken(s, p, d.g); },
         [&](const MacroMap3 &m) { d.g.maps.push_back(m); },
         [&](size_t, size_t) {});
    // one entry per core layer (core keeps at most 8; the rest are parsed and dropped)
    int n = !s.empty() && s[0] != ';' ? 1 : 0;
    for (size_t i = 0; n && i < s.size() && s[i] != ';'; i++) if (s[i] == '/') n++;
    all.resize((size_t)n);
    if (all.size() > 8) all.resize(8);
    d.layers = all;
    return d;
}

std::string strip3(const std::string &in)
{
    std::string s = clean(in), out;
    walk(s,
         [&](int, size_t &p) { Layer3 L; layerToken(s, p, L); },
         [&](size_t &p) { Globals3 g; globalToken(s, p, g); },
         [&](const MacroMap3 &) {},
         [&](size_t b, size_t e) { out.append(s, b, e - b); });
    return out;
}

std::string Layer3::tokens() const
{
    std::string t;
    if (has[0]) {
        Window def;
        std::string w;
        if (this->w.s.lo || this->w.s.hi) w += "s" + rangeText(this->w.s);
        if (this->w.e.lo != def.e.lo || this->w.e.hi != def.e.hi) w += "e" + rangeText(this->w.e);
        if (this->w.l.lo >= 0) w += "l" + rangeText(this->w.l);
        if (this->w.vel) w += "v" + fracText(this->w.vel);
        if (this->w.maxMs) w += "m" + std::to_string(this->w.maxMs);
        if (this->w.offMs) w += "o" + std::to_string(this->w.offMs);
        if (this->w.beat16) w += "b" + std::to_string(this->w.beat16);
        if (this->w.gate16) w += "g" + std::to_string(this->w.gate16);
        if (this->w.tempo) w += "t";
        if (this->w.loopA) w += "r" + std::to_string(this->w.loopA);
        if (this->w.loopP) w += "p" + std::to_string(this->w.loopP);
        w += extra[0];
        if (!w.empty()) t += "W" + w;
    }
    if (has[1]) {
        std::string x = n.mode == 'p' ? "p" + (n.poly ? std::to_string(n.poly) : std::string()) : std::string(1, n.mode);
        if (n.glideMs) x += "g" + std::to_string(n.glideMs);
        if (n.prio != 'n') x += std::string("k") + n.prio;
        t += "N" + x + extra[1];
    }
    if (has[2]) {
        std::string x;
        if (s.roundRobin) x += "r";
        if (s.randomPick) x += "x";
        if (s.randomRec) x += "p";
        if (s.group) x += "g" + std::to_string(s.group) + (s.groupRandom ? "x" : "");
        if (s.strumMs) x += "s" + std::to_string(s.strumMs);
        if (s.width) x += "w" + fracText(s.width);
        x += extra[2];
        if (!x.empty()) t += "S" + x;
    }
    if (has[3]) {
        std::string x;
        if (y.detune) x += "d" + std::to_string(y.detune);
        if (y.level) x += "l" + std::to_string(y.level);
        if (y.timeMs) x += "t" + std::to_string(y.timeMs);
        if (y.pan) x += "q" + std::to_string(y.pan);
        if (y.perKey) x += "k";
        if (y.perRec) x += "r";
        x += extra[3];
        if (!x.empty()) t += "Y" + x;
    }
    if (has[4]) {
        std::string x;
        if (v.wowCents) x += "w" + std::to_string(v.wowCents) + "," + std::to_string(v.wowDeciHz);
        if (v.fluCents) x += "f" + std::to_string(v.fluCents) + "," + std::to_string(v.fluHz);
        if (v.scoopCents) x += "s" + std::to_string(v.scoopCents) + "," + std::to_string(v.scoopMs);
        x += extra[4];
        if (!x.empty()) t += "V" + x;
    }
    if (has[5]) t += "Z" + std::to_string(z.lo) + "," + std::to_string(z.hi) + (z.root >= 0 ? "," + std::to_string(z.root) : "") + extra[5];
    if (has[6]) {
        Grain d;
        std::string x;
        if (g.pos) x += "p" + fracText(g.pos);
        if (g.spray) x += "j" + fracText(g.spray);
        if (g.sizeMs != d.sizeMs || g.sizeHiMs != d.sizeHiMs)
            x += "z" + std::to_string(g.sizeMs) + (g.sizeHiMs != g.sizeMs ? "~" + std::to_string(g.sizeHiMs) : "");
        if (g.density != d.density) x += "n" + std::to_string(g.density);
        if (g.cents) x += "c" + std::to_string(g.cents);
        if (g.octPct) x += "o" + std::to_string(g.octPct);
        if (g.shape != d.shape) x += "e" + std::to_string(g.shape);
        if (g.scan) x += "s" + fracText(g.scan);
        if (g.back) x += "b";
        if (g.freeze) x += "f";
        if (g.streams != d.streams) x += "v" + std::to_string(g.streams);
        if (g.width) x += "w" + fracText(g.width);
        if (g.sync) x += "y";
        t += "G" + x + extra[6];     // a bare "G" stays: grains on with every default
    }
    if (has[7]) {   // D: degree harmony
        std::string x;
        auto list = [](const std::vector<int> &v) { std::string o; for (size_t i = 0; i < v.size(); i++) o += (i ? "," : "") + std::to_string(v[i]); return o; };
        if (!d.up.empty()) x += "h" + list(d.up);
        if (!d.down.empty()) x += "b" + list(d.down);
        if (d.inversion) x += "i" + std::to_string(d.inversion);
        if (d.snap) x += "s" + std::to_string(d.snap);
        x += extra[7];
        if (!x.empty()) t += "D" + x;
    }
    return t;
}

std::string Globals3::tokens() const
{
    std::string t;
    if (hasQ) t += "q" + std::to_string(scale) + (rootPc >= 0 ? "r" + std::to_string(rootPc) : "") + (mask ? "n" + std::to_string(mask) : "") + (edo ? "e" + std::to_string(edo) : "") + qExtra;
    if (x.on) {
        Seq d;
        t += "x";
        if (x.div != d.div || x.triplet) t += "d" + std::to_string(x.div) + (x.triplet ? "t" : "");
        if (x.gate != d.gate) t += "g" + std::to_string(x.gate);
        if (x.swing) t += "s" + std::to_string(x.swing);
        if (x.kind) t += "n" + std::to_string(x.kind);
        if (x.poly != d.poly) t += "p" + std::to_string(x.poly);
        if (x.autodig != d.autodig) t += "a" + std::to_string(x.autodig);
        if (x.octaves != d.octaves) t += "o" + std::to_string(x.octaves);
        if (x.len) t += "l" + std::to_string(x.len);
        if (x.bpm != d.bpm) t += "b" + std::to_string(x.bpm);
        if (x.freeRun) t += "f";
        if (x.latch) t += "h";
        t += xExtra;
    }
    if (kitOff || !kExtra.empty()) t += std::string("k") + (kitOff ? "d" : "") + kExtra;
    for (auto &p : pads) t += p.token();
    for (auto &m : maps) t += "m" + std::to_string(m.macro) + std::to_string(m.layer) + m.param + std::to_string(m.lo) + "," + std::to_string(m.hi);
    return t;
}

std::string canonical3(const std::string &in)
{
    std::string s = clean(in);
    std::string v2 = bsynth::canonical(strip3(s));
    Dna3 d = parse3(s);
    size_t semi = v2.find(';');
    std::string lay = v2.substr(0, semi), glob = semi == std::string::npos ? "" : v2.substr(semi + 1);
    std::vector<std::string> L;
    if (semi != 0) {
        size_t b = 0;
        for (;;) { size_t e = lay.find('/', b); L.push_back(lay.substr(b, e - b)); if (e == std::string::npos) break; b = e + 1; }
    }
    std::string out;
    for (size_t i = 0; i < L.size(); i++) {
        if (i) out += '/';
        out += L[i];
        if (i < d.layers.size()) out += d.layers[i].tokens();
    }
    std::string g = glob + d.g.tokens();
    if (!g.empty()) out += ";" + g;
    return out;
}

Dna3 applyMacros3(const Dna3 &in, const int macro[4])
{
    Dna3 d = in;
    // per (layer, param): the summed value, the v2 way: the first map gives its value, each further map adds
    // (value - its lo)
    struct Acc { bool any = false; double v = 0; };
    Acc acc[9][sizeof kMacroParams3];
    for (auto &m : in.g.maps) {
        int pi = (int)(std::strchr(kMacroParams3, m.param) - kMacroParams3);
        double v = m.lo + (m.hi - m.lo) * clampi(macro[m.macro - 1], 0, 100) / 100.0;
        Acc &a = acc[m.layer][pi];
        a.v = a.any ? a.v + (v - m.lo) : v;
        a.any = true;
    }
    for (size_t li = 0; li < d.layers.size(); li++) {
        Layer3 &L = d.layers[li];
        for (int pi = 0; kMacroParams3[pi]; pi++) {
            const Acc &a = acc[li + 1 <= 8 ? li + 1 : 8][pi], &all = acc[0][pi];
            if (!a.any && !all.any) continue;
            double v = a.any ? a.v : all.v;
            if (a.any && all.any) v += all.v;    // layer 0 (every layer) adds to a layer's own maps
            int iv = (int)(v < 0 ? v - 0.5 : v + 0.5);
            switch (kMacroParams3[pi]) {
            case 'W': L.w.s.lo = L.w.s.hi = clampi(iv * 10, 0, kOne); L.has[0] = true; break;
            case 'E': L.w.e.lo = L.w.e.hi = clampi(iv * 10, 0, kOne); L.has[0] = true; break;
            case 'Y': L.w.l.lo = L.w.l.hi = clampi(iv * 10, 0, kOne); L.has[0] = true; break;
            case 'P': L.g.pos = clampi(iv * 10, 0, kOne); break;
            case 'I': L.g.spray = clampi(iv * 10, 0, kOne); break;
            case 'X': L.g.sizeMs = L.g.sizeHiMs = clampi(iv, 5, 2000); break;
            case 'U': L.g.density = clampi(iv, 1, 200); break;
            case 'F': L.g.scan = clampi(iv * 10, 0, 4 * kOne); break;
            case 'H': L.v.wowCents = clampi(iv, 0, 100); if (!L.v.wowDeciHz) L.v.wowDeciHz = 6; L.has[4] = true; break;
            case 'J': L.n.glideMs = clampi(iv, 0, 5000); break;
            }
        }
    }
    return d;
}

}  // namespace bsynth3
