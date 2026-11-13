// DNA recipes. See recipe.h and design/PRESET-ENGINE-2.md section 17.
//
// How it stays lossless: toRecipe() cuts canonical3(dna) into tokens (the canonical text of each step, gene and
// global) and writes one phrase per token (sugar phrases cover a few tokens: double, trim, cut at, x N). fromRecipe()
// turns every phrase back into exactly those token texts. A sugar phrase is only written when parsing it back gives
// the same tokens (checked at print time). So fromRecipe(toRecipe(d)) == canonical3(d) by construction; the fuzz
// test checks it anyway.
#include "recipe.h"
#include "dna3.h"
#include "dna.h"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <vector>

namespace bsynth3 {
namespace {

// ------------------------------------------------------------------------------------------------ text helpers
// The pretty display symbols (UTF-8). Recipes are written in ASCII; prettify() puts these in for display, and
// the parser accepts them too.
const char *kMinus = "\xE2\x88\x92", *kTimes = "\xC3\x97", *kPm = "\xC2\xB1", *kCent = "\xC2\xA2", *kDash = "\xE2\x80\x93",
           *kDot = "\xC2\xB7", *kEll = "\xE2\x80\xA6";

std::string itos(long v) { return std::to_string(v); }
std::string sgn(long v) { return (v < 0 ? "-" : "+") + itos(std::labs(v)); }   // +12, -5 (ASCII, as typed)
bool isnum(const std::string &s) { if (s.empty()) return false; for (char c : s) if (!isdigit((unsigned char)c)) return false; return true; }

std::string msText(long ms)            // 350ms, 1.5s, 2s
{
    if (ms >= 1000 && ms % 100 == 0) {
        char b[32]; std::snprintf(b, sizeof b, "%.1f", ms / 1000.0);
        std::string t = b; if (t.size() > 2 && t.substr(t.size() - 2) == ".0") t.resize(t.size() - 2);
        return t + "s";
    }
    return itos(ms) + "ms";
}
std::string pct(int frac)               // a 1/10000 fraction as percent: 2500 -> 25, 3333 -> 33.33
{
    char b[32]; std::snprintf(b, sizeof b, "%d.%02d", frac / 100, frac % 100);
    std::string t = b;
    while (t.back() == '0') t.pop_back();
    if (t.back() == '.') t.pop_back();
    return t;
}
const char *kNotes[] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
std::string noteName(int n) { return std::string(kNotes[((n % 12) + 12) % 12]) + itos(n / 12 - 1); }   // 60 -> C4

// ------------------------------------------------------------------------------------------------ tokens
// The canonical DNA (canonical3) cut into tokens. Layer: the source NAME, then one string per step/gene/v3 token.
struct Tok { std::string t; };
struct Cut { std::vector<std::vector<std::string>> layers; std::vector<std::string> globals; bool hasGlobals = false; };

bool lowerc(char c) { return c >= 'a' && c <= 'z'; }
bool namech(char c) { return lowerc(c) || isdigit((unsigned char)c) || c == '_'; }
bool bodych(char c) { return lowerc(c) || isdigit((unsigned char)c) || c == '.' || c == ',' || c == '~'; }

Cut cut(const std::string &s)
{
    Cut c;
    size_t p = 0;
    auto run = [&](size_t &q, auto pred) { while (q < s.size() && pred(s[q])) q++; };
    auto signedInt = [&](size_t &q) { if (q < s.size() && (s[q] == '-' || s[q] == '+')) q++; run(q, [](char x) { return isdigit((unsigned char)x) != 0; }); };
    if (!s.empty() && s[0] != ';') {
        for (;;) {
            std::vector<std::string> L;
            size_t b = p; run(p, namech); L.push_back(s.substr(b, p - b));
            while (p < s.size() && s[p] != '/' && s[p] != ';') {
                b = p;
                char ch = s[p++];
                if (std::strchr("+-><ER[]CPX", ch)) {}
                else if (ch == '@') { if (p < s.size() && s[p] == 't') p++; run(p, [](char x) { return isdigit((unsigned char)x) != 0; }); }
                else if (ch == 'I' || ch == 'M') run(p, namech);
                else if (ch == '#' || ch == 'L' || ch == 'O') run(p, [](char x) { return isdigit((unsigned char)x) != 0; });
                else if (ch == 'T' || ch == 'Q') signedInt(p);
                else if (ch == 'H') { signedInt(p); while (p < s.size() && s[p] == ',') { p++; signedInt(p); } }
                else if (ch == 'U') { run(p, [](char x) { return isdigit((unsigned char)x) != 0; }); if (p < s.size() && s[p] == '~') { p++; run(p, [](char x) { return isdigit((unsigned char)x) != 0; }); } }
                else if (ch == 'F') {}
                else if (ch == 'J') {   // a '-' is a sign only at the start of a number (after a, p, ',' or '.'), else the softer step
                    if (p < s.size() && (s[p] == 'a' || s[p] == 'p')) p++;
                    while (p < s.size() && (isdigit((unsigned char)s[p]) || s[p] == ',' || s[p] == '.' ||
                                            (s[p] == '-' && p + 1 < s.size() && isdigit((unsigned char)s[p + 1]) && std::strchr("ap,.", s[p - 1])))) p++;
                }
                else if (ch >= 'A' && ch <= 'Z') run(p, bodych);      // v3 and later layer tokens
                L.push_back(s.substr(b, p - b));
            }
            c.layers.push_back(L);
            if (p < s.size() && s[p] == '/') { p++; continue; }
            break;
        }
    }
    if (p < s.size() && s[p] == ';') {
        c.hasGlobals = true;
        p++;
        while (p < s.size()) {
            size_t b = p;
            char ch = s[p++];
            if (std::strchr("ADSRBVKG", ch)) signedInt(p);
            else if (ch == 'm') {   // as core consumes it (DNA.md 5.7)
                if (p < s.size()) p++;
                if (p < s.size() && s[p] == '=') p++;
                else { if (p < s.size() && isdigit((unsigned char)s[p])) p++; if (p < s.size() && isalpha((unsigned char)s[p]) && s[p] != 'm') p++; }
                run(p, [](char x) { return isdigit((unsigned char)x) || x == ',' || x == '.' || x == '~' || x == '-'; });
            }
            else if (ch == 'q' || ch == 'x' || ch == 'k') run(p, [](char x) { return bodych(x) && x != 'm' && x != 'q' && x != 'x' && x != 'k'; });
            else if (isalpha((unsigned char)ch)) run(p, [](char x) { return bodych(x) && x != 'm'; });
            c.globals.push_back(s.substr(b, p - b));
        }
    }
    return c;
}

// ------------------------------------------------------------------------------------------------ words
// Every keyword has three spellings: multi-line, one-line, short. The parser accepts all of them.
enum W {
    wLouder, wSofter, wFaster, wSlower, wEcho, wReverse, wCopy, wPaste, wMixPaste, wCutBefore, wCutAfter, wAt, wInsert,
    wMix, wDouble, wTrim, wRec, wTranspose, wNotes, wUnison, wFixed, wLevel, wOffset, wPan, wAmp, wPanEnv,
    // v3 layer
    wStart, wEnd, wLength, wVelStart, wTape, wPoly, wMono, wLegato, wContinue, wGlide, wPrio, wRoundRobin, wRandomNote,
    wRandomRec, wGroup, wStrum, wChord, wSpread, wRand, wSeed, wWow, wFlutter, wScoop, wKeys, wRoot, wGrains,
    // globals
    wAttack, wDecay, wSustain, wRelease, wBend, wVelocity, wGain, wMacro, wScale, wSeq, wPad, wKitOff,
    wCount
};
struct Spell { const char *lng, *one, *sht; };
const Spell kW[wCount] = {
    {"louder", "louder", "loud"}, {"softer", "softer", "soft"}, {"faster", "faster", "fast"}, {"slower", "slower", "slow"},
    {"echo", "echo", "echo"}, {"reverse", "reverse", "rev"}, {"copy", "copy", "copy"}, {"paste", "paste", "paste"},
    {"mix paste", "mix paste", "mixp"}, {"cut before", "cut before", "cut<"}, {"cut after", "cut after", "cut>"},
    {"at", "at", "@"}, {"insert", "insert", "ins"}, {"mix", "mix", "mix"}, {"double", "double", "dbl"}, {"trim", "trim", "trim"},
    {"recorders", "rec", "r"}, {"transpose", "transpose", "tr"}, {"notes", "notes", "h"}, {"unison", "unison", "u"},
    {"fixed pitch", "fixed", "fix"}, {"level", "level", "lv"}, {"offset", "offset", "o"}, {"pan", "pan", "pan"},
    {"amp env", "amp", "amp"}, {"pan env", "panenv", "panenv"},
    {"start", "start", "st"}, {"end", "end", "end"}, {"length", "length", "len"}, {"velocity start", "velstart", "vst"},
    {"tape", "tape", "tape"}, {"poly", "poly", "poly"}, {"mono", "mono", "mono"}, {"legato", "legato", "leg"},
    {"continue", "continue", "cont"}, {"glide", "glide", "gl"}, {"priority", "prio", "prio"},
    {"round-robin", "round-robin", "rr"}, {"random note", "random-note", "rnote"}, {"random recorder", "random-recorder", "rrec"},
    {"group", "group", "grp"}, {"strum", "strum", "strum"}, {"chord", "chord", "chord"}, {"spread", "spread", "spr"},
    {"random", "rand", "rnd"}, {"seed", "seed", "seed"}, {"wow", "wow", "wow"}, {"flutter", "flutter", "flut"},
    {"scoop", "scoop", "scoop"}, {"keys", "keys", "keys"}, {"root", "root", "root"}, {"grains", "grains", "gr"},
    {"attack", "atk", "a"}, {"decay", "dec", "d"}, {"sustain", "sus", "s"}, {"release", "rel", "r"}, {"bend", "bend", "b"},
    {"velocity", "vel", "v"}, {"gain", "gain", "g"}, {"macro", "m", "m"}, {"scale", "scale", "scale"}, {"sequencer", "seq", "seq"},
    {"pad", "pad", "pad"}, {"kit off", "kit off", "kitoff"},
};
const char *spell(W w, RecipeForm f) { return f == RecipeForm::Lines ? kW[w].lng : f == RecipeForm::OneLine ? kW[w].one : kW[w].sht; }

const char *kScaleWords[kScaleCount] = {"major", "minor", "dorian", "phrygian", "lydian", "mixolydian", "locrian",
                                        "harmonic-minor", "major-pent", "minor-pent", "whole-tone", "blues", "chromatic"};
const char *kMacroParams = "OQLTCZNWEYPIXUFHJ";
const char *kMacroWords[] = {"offset", "pan", "level", "transpose", "spread", "envtime", "repeat", "start", "end", "length",
                             "grainpos", "spray", "grainsize", "density", "scan", "wow", "glide"};
const char *kShapes[] = {"rect", "triangle", "smooth", "hit"};
const char *kCurves[] = {"linear", "soft", "hard", "fixed"};
const char *kKinds[] = {"field", "count", "arp"};

// ------------------------------------------------------------------------------------------------ printing
struct Item { std::string text; bool step; std::vector<std::string> toks; };

std::string panText(int v) { return v == 0 ? "C" : (v < 0 ? "L" : "R") + itos(std::abs(v)); }
std::string pmCents(int c, RecipeForm) { return std::string("+-") + itos(c) + "c"; }
std::string rangeText(const Range &r) { return r.random() ? pct(r.lo) + "-" + pct(r.hi) : pct(r.lo); }
std::string join(const std::vector<std::string> &v, const std::string &sep) { std::string o; for (size_t i = 0; i < v.size(); i++) o += (i ? sep : "") + v[i]; return o; }
// keyword + value: "level 80%" (Lines, OneLine) or "lv80" (Short)
std::string kv(W w, const std::string &val, RecipeForm f)
{
    bool glue = f == RecipeForm::Short && !val.empty() &&
                (isdigit((unsigned char)val[0]) || val[0] == '+' || val[0] == '-' || val[0] == '.' || w == wPan || w == wRoot || w == wKeys);
    return std::string(spell(w, f)) + (glue ? "" : " ") + val;
}
std::string unitless(const std::string &v, RecipeForm f, const char *unit)   // Short drops the default unit
{
    if (f == RecipeForm::Short && v.size() > strlen(unit) && v.compare(v.size() - strlen(unit), std::string::npos, unit) == 0) return v.substr(0, v.size() - strlen(unit));
    return v;
}

std::string envText(const std::string &body, bool pan)    // "0,0.30,100" -> "0:0 30:100" (ms:% or ms:pan)
{
    std::vector<std::string> pts;
    size_t b = 0;
    while (b <= body.size()) {
        size_t e = body.find('.', b);
        if (e == std::string::npos) e = body.size();
        std::string pt = body.substr(b, e - b);
        size_t c = pt.find(',');
        if (c != std::string::npos) pts.push_back(pt.substr(0, c) + ":" + pt.substr(c + 1));
        b = e + 1;
    }
    (void)pan;
    return join(pts, ",");
}

std::string v3Layer(const std::string &tok, RecipeForm f)
{
    Dna3 d = parse3("a" + tok);
    if (d.layers.empty()) return "{" + tok + "}";
    const Layer3 &L = d.layers[0];
    int li = (int)(std::strchr(kLayerLetters, tok[0]) - kLayerLetters);
    if (!L.extra[li].empty()) return "{" + tok + "}";   // a later version's subkey: verbatim
    bool sh = f == RecipeForm::Short;
    std::vector<std::string> o;
    switch (tok[0]) {
    case 'W': {
        Window def;
        if (L.w.s.lo || L.w.s.hi) o.push_back(kv(wStart, rangeText(L.w.s) + (sh ? "" : "%"), f));
        if (L.w.e.lo != def.e.lo || L.w.e.hi != def.e.hi) o.push_back(kv(wEnd, rangeText(L.w.e) + (sh ? "" : "%"), f));
        if (L.w.l.lo >= 0) o.push_back(kv(wLength, rangeText(L.w.l) + (sh ? "" : "%"), f));
        if (L.w.vel) o.push_back(kv(wVelStart, pct(L.w.vel) + (sh ? "" : "%"), f));
        if (L.w.maxMs) o.push_back(kv(wTape, unitless(msText(L.w.maxMs), f, "ms"), f));
        break; }
    case 'N':
        if (L.n.mode == 'p') o.push_back(L.n.poly ? kv(wPoly, itos(L.n.poly), f) : spell(wPoly, f));
        else o.push_back(spell(L.n.mode == 'm' ? wMono : L.n.mode == 'l' ? wLegato : wContinue, f));
        if (L.n.glideMs) o.push_back(kv(wGlide, unitless(msText(L.n.glideMs), f, "ms"), f));
        if (L.n.prio != 'n') o.push_back(kv(wPrio, L.n.prio == 'h' ? "high" : "low", f));
        break;
    case 'S':
        if (L.s.roundRobin) o.push_back(spell(wRoundRobin, f));
        if (L.s.randomPick) o.push_back(spell(wRandomNote, f));
        if (L.s.randomRec) o.push_back(spell(wRandomRec, f));
        if (L.s.group) o.push_back(kv(wGroup, itos(L.s.group), f) + (L.s.groupRandom ? (sh ? "r" : " random") : ""));
        if (L.s.strumMs) o.push_back(kv(wStrum, unitless(msText(L.s.strumMs), f, "ms"), f));
        if (L.s.diatonic) o.push_back(kv(wChord, itos(L.s.diatonic), f));
        if (L.s.width) o.push_back(kv(wSpread, pct(L.s.width) + (sh ? "" : "%"), f));
        break;
    case 'Y':
        if (L.y.detune) o.push_back(std::string(spell(wRand, f)) + " " + (sh ? "" : "pitch ") + pmCents(L.y.detune, f));
        if (L.y.level) o.push_back(std::string(spell(wRand, f)) + " " + (sh ? "lv" : "level ") + itos(L.y.level) + (sh ? "" : "%"));
        if (L.y.timeMs) o.push_back(std::string(spell(wRand, f)) + " " + (sh ? "late" : "late ") + unitless(msText(L.y.timeMs), f, "ms"));
        if (L.y.pan) o.push_back(std::string(spell(wRand, f)) + " " + (sh ? "pan" : "pan ") + itos(L.y.pan));
        if (L.y.perKey) o.push_back(kv(wSeed, "key", f));
        if (L.y.perRec) o.push_back(kv(wSeed, "recorder", f));
        break;
    case 'V': {
        auto hz = [](int deci) { char b[16]; std::snprintf(b, sizeof b, "%g", deci / 10.0); return std::string(b); };
        if (L.v.wowCents) o.push_back(kv(wWow, itos(L.v.wowCents) + "c" + (sh ? "," : " ") + hz(L.v.wowDeciHz) + (sh ? "" : "Hz"), f));
        if (L.v.fluCents) o.push_back(kv(wFlutter, itos(L.v.fluCents) + "c" + (sh ? "," : " ") + itos(L.v.fluHz) + (sh ? "" : "Hz"), f));
        if (L.v.scoopCents) o.push_back(kv(wScoop, itos(L.v.scoopCents) + "c" + (sh ? "," : " ") + unitless(msText(L.v.scoopMs), f, "ms"), f));
        break; }
    case 'Z':
        o.push_back(kv(wKeys, noteName(L.z.lo) + "-" + noteName(L.z.hi), f) + (L.z.root >= 0 ? " " + kv(wRoot, noteName(L.z.root), f) : ""));
        break;
    case 'G': {
        Grain g = L.g, dg;
        std::vector<std::string> x{spell(wGrains, f)};
        auto add = [&](const char *k, const std::string &v) { x.push_back(sh ? std::string(k) + v : std::string(k) + " " + v); };
        if (g.pos) add("pos", pct(g.pos) + (sh ? "" : "%"));
        if (g.spray) add("spray", pct(g.spray) + (sh ? "" : "%"));
        if (g.sizeMs != dg.sizeMs || g.sizeHiMs != dg.sizeHiMs) add("size", itos(g.sizeMs) + (g.sizeHiMs != g.sizeMs ? "-" + itos(g.sizeHiMs) : "") + (sh ? "" : "ms"));
        if (g.density != dg.density) add("density", itos(g.density) + (sh ? "" : "/s"));
        if (g.cents) add("pitch", pmCents(g.cents, f));
        if (g.octPct) add("oct", itos(g.octPct) + (sh ? "" : "%"));
        if (g.shape != dg.shape) add("shape", kShapes[g.shape]);
        if (g.scan) add("scan", pct(g.scan * 100 / 100) == "" ? "0" : [&] { char b[16]; std::snprintf(b, sizeof b, "%g", g.scan / 10000.0); return std::string(b) + (sh ? "" : "x"); }());
        if (g.back) x.push_back("back");
        if (g.freeze) x.push_back("freeze");
        if (g.streams != dg.streams) add("streams", itos(g.streams));
        if (g.width) add("width", pct(g.width) + (sh ? "" : "%"));
        if (g.sync) x.push_back("sync");
        o.push_back(join(x, " "));
        break; }
    }
    if (o.empty()) return "{" + tok + "}";       // a v3 token with only defaults ("Ws0"): verbatim
    return join(o, f == RecipeForm::Lines ? std::string("  ") : " ");
}

std::string macroParamWord(char p) { const char *q = std::strchr(kMacroParams, p); return q ? kMacroWords[q - kMacroParams] : ""; }

std::string globalPhrase(const std::string &tok, RecipeForm f)
{
    bool sh = f == RecipeForm::Short;
    char c = tok[0];
    if (std::strchr("ADSRBVKG", c) && tok.size() > 1) {
        long v = std::strtol(tok.c_str() + 1, nullptr, 10);
        switch (c) {
        case 'A': return kv(wAttack, unitless(msText(v), f, "ms"), f);
        case 'D': return kv(wDecay, unitless(msText(v), f, "ms"), f);
        case 'R': return kv(wRelease, unitless(msText(v), f, "ms"), f);
        case 'S': return kv(wSustain, itos(v) + (sh ? "" : "%"), f);
        case 'V': return kv(wVelocity, itos(v) + (sh ? "" : "%"), f);
        case 'B': return kv(wBend, "+-" + itos(v), f);
        case 'K': return kv(wRoot, noteName((int)v), f);
        case 'G': return kv(wGain, sgn(v) + (sh ? "" : "dB"), f);
        }
    }
    if (c == 'm') {
        // mK=V or mKLPlo,hi; anything else verbatim
        if (tok.size() >= 3 && tok[1] >= '1' && tok[1] <= '4' && tok[2] == '=' && isnum(tok.substr(3)))
            return std::string(spell(wMacro, f)) + tok[1] + " " + tok.substr(3) + (sh ? "" : "%");
        if (tok.size() >= 5 && tok[1] >= '1' && tok[1] <= '4' && tok[2] >= '0' && tok[2] <= '8' && !macroParamWord(tok[3]).empty()) {
            std::string vals = tok.substr(4);
            size_t cm = vals.find(',');
            if (cm != std::string::npos) {
                char *e1, *e2;
                long lo = std::strtol(vals.c_str(), &e1, 10), hi = std::strtol(vals.c_str() + cm + 1, &e2, 10);
                if (*e1 == ',' && !*e2 && itos(lo) + "," + itos(hi) == vals) {
                    std::string layer = tok[2] == '0' ? "all" : (f == RecipeForm::Lines ? "layer" : "L") + std::string(1, tok[2]);
                    return std::string(spell(wMacro, f)) + tok[1] + " " + layer + " " + macroParamWord(tok[3]) + " " + itos(lo) + "-" + itos(hi);
                }
            }
        }
        return "{" + tok + "}";
    }
    if (c == 'q') {
        Dna3 d = parse3(";" + tok);
        if (!d.g.qExtra.empty() || d.g.tokens() != tok) return "{" + tok + "}";
        std::string t = kv(wScale, kScaleWords[d.g.scale], f);
        if (d.g.rootPc >= 0) t += f == RecipeForm::Lines ? std::string(" root ") + kNotes[d.g.rootPc] : std::string(" ") + kNotes[d.g.rootPc];
        return t;
    }
    if (c == 'x') {
        Dna3 d = parse3(";" + tok);
        if (!d.g.xExtra.empty() || d.g.tokens() != tok) return "{" + tok + "}";
        const Seq &x = d.g.x; Seq df;
        std::vector<std::string> o{spell(wSeq, f)};
        if (x.div != df.div || x.triplet) o.push_back("1/" + itos(x.div) + (x.triplet ? "t" : ""));
        if (x.gate != df.gate) o.push_back(std::string("gate") + (sh ? "" : " ") + itos(x.gate) + (sh ? "" : "%"));
        if (x.swing) o.push_back(std::string("swing") + (sh ? "" : " ") + itos(x.swing) + (sh ? "" : "%"));
        if (x.kind) o.push_back(kKinds[x.kind]);
        if (x.poly != df.poly) o.push_back(std::string("max") + (sh ? "" : " ") + itos(x.poly));
        if (x.autodig != df.autodig) o.push_back(std::string("dig") + (sh ? "" : " ") + itos(x.autodig));
        if (x.octaves != df.octaves) o.push_back(std::string("octaves") + (sh ? "" : " ") + itos(x.octaves));
        if (x.len) o.push_back(std::string("steps") + (sh ? "" : " ") + itos(x.len));
        if (x.bpm != df.bpm) o.push_back(std::string("bpm") + (sh ? "" : " ") + itos(x.bpm));
        if (x.freeRun) o.push_back("free-run");
        if (x.latch) o.push_back("latch");
        return join(o, " ");
    }
    if (c == 'k') {
        Dna3 d = parse3(";" + tok);
        if (tok == "kd") return spell(wKitOff, f);
        if (d.g.pads.size() != 1 || !d.g.pads[0].extra.empty() || d.g.pads[0].token() != tok) return "{" + tok + "}";
        const Pad &p = d.g.pads[0]; Pad df;
        std::vector<std::string> o{std::string(spell(wPad, f)) + (sh ? "" : " ") + itos(p.lo) + (p.hi != p.lo ? "-" + itos(p.hi) : "")};
        auto add = [&](const char *k, const std::string &v) { o.push_back(sh ? std::string(k) + v : std::string(k) + " " + v); };
        if (p.layer != df.layer) add("layer", itos(p.layer));
        if (p.seg) add("seg", itos(p.seg));
        if (p.s.lo || p.s.hi) add("start", rangeText(p.s) + (sh ? "" : "%"));
        if (p.e.lo != kOne || p.e.hi != kOne) add("end", rangeText(p.e) + (sh ? "" : "%"));
        if (p.root >= 0 && p.root != p.lo) add("root", itos(p.root));
        if (p.pitchPct) add("pitch", itos(p.pitchPct) + (sh ? "" : "%"));
        if (p.rangeSemis) add("range", "+-" + itos(p.rangeSemis));
        if (p.tuneCents) add("tune", sgn(p.tuneCents) + "c");
        if (p.level != 100) add("level", itos(p.level) + (sh ? "" : "%"));
        if (p.pan) add("pan", panText(p.pan));
        if (p.curve) add("curve", kCurves[p.curve]);
        if (p.velAmount >= 0) add("vel", itos(p.velAmount) + "%");
        if (p.velLo != 1 || p.velHi != 127) add("vel", itos(p.velLo) + "-" + itos(p.velHi));
        if (p.gated) o.push_back("gated");
        if (p.cut) add("cut", itos(p.cut));
        if (p.fadeMs != df.fadeMs) add("fade", unitless(msText(p.fadeMs), f, "ms"));
        if (!p.mutes.empty()) { std::vector<std::string> m; for (int g : p.mutes) m.push_back(itos(g)); add("mutes", join(m, ",")); }
        if (p.voices) add("voices", itos(p.voices));
        if (p.out != 1) add("out", itos(p.out));
        if (p.random) o.push_back("random");
        return join(o, " ");
    }
    return "{" + tok + "}";
}

// one layer token (not the source) -> phrase. step: true for Sound Recorder steps (they take x N)
Item layerPhrase(const std::string &t, RecipeForm f)
{
    bool sh = f == RecipeForm::Short;
    Item it{"", false, {t}};
    char c = t[0];
    const char *steps = "+-><ERCPX[]";
    if (t.size() == 1 && std::strchr(steps, c)) {
        static const W map[] = {wLouder, wSofter, wFaster, wSlower, wEcho, wReverse, wCopy, wPaste, wMixPaste, wCutBefore, wCutAfter};
        it.text = spell(map[std::strchr(steps, c) - steps], f); it.step = true; return it;
    }
    if (c == '@' && t.size() > 1 && t[1] == 't') {   // the unit always shows: "at 250ms" is a time, "at 25%" a percent
        it.text = std::string(spell(wAt, f)) + (sh ? "" : " ") + msText(std::atol(t.c_str() + 2)); it.step = true; return it; }
    if (c == '@') { it.text = std::string(spell(wAt, f)) + (sh ? "" : " ") + t.substr(1) + "%"; it.step = true; return it; }
    // sound names in their readable form: dingxp is shown ding-xp (DNA.md 2.4, core displayName)
    if (c == 'I') { it.text = std::string(spell(wInsert, f)) + " " + bsynth::displayName(t.substr(1)); it.step = true; return it; }
    if (c == 'M') { it.text = std::string(spell(wMix, f)) + " " + bsynth::displayName(t.substr(1)); it.step = true; return it; }
    if (c == '#') { it.text = t.substr(1) + (f == RecipeForm::Lines ? (t == "#1" ? " recorder" : " recorders") : spell(wRec, f)); return it; }
    if (c == 'T') { it.text = kv(wTranspose, sgn(std::atol(t.c_str() + 1)), f); return it; }
    if (c == 'H') {
        std::vector<std::string> v; size_t b = 1;
        while (b <= t.size()) { size_t e = t.find(',', b); if (e == std::string::npos) e = t.size(); v.push_back(sgn(std::atol(t.substr(b, e - b).c_str()))); b = e + 1; }
        it.text = std::string(spell(wNotes, f)) + (sh ? "" : " ") + join(v, " "); return it;   // "notes +0 -12": spaced, so - is a sign
    }
    if (c == 'U') {
        size_t tl = t.find('~');
        std::string n = t.substr(1, tl - 1), cc = t.substr(tl + 1);
        it.text = std::string(spell(wUnison, f)) + (sh ? "" : " ") + n + (cc == "0" ? "" : (sh ? "" : " ") + pmCents(std::atoi(cc.c_str()), f)); return it;
    }
    if (t == "F") { it.text = spell(wFixed, f); return it; }
    if (c == 'L') { it.text = kv(wLevel, t.substr(1) + (sh ? "" : "%"), f); return it; }
    if (c == 'O') { it.text = kv(wOffset, unitless(msText(std::atol(t.c_str() + 1)), f, "ms"), f); return it; }
    if (c == 'Q') { it.text = kv(wPan, panText(std::atoi(t.c_str() + 1)), f); return it; }
    if (c == 'J' && t.size() > 1 && (t[1] == 'a' || t[1] == 'p')) { it.text = kv(t[1] == 'a' ? wAmp : wPanEnv, envText(t.substr(2), t[1] == 'p'), f); return it; }
    if (isLayerLetter(c)) { it.text = v3Layer(t, f); return it; }
    it.text = "{" + t + "}";
    return it;
}

}  // namespace

// ------------------------------------------------------------------------------------------------ parsing
namespace {

struct Word { std::string w; size_t pos; };
struct P {
    std::vector<Word> ws; size_t i = 0; RecipeError err; bool bad = false;
    bool end() const { return i >= ws.size(); }
    const std::string &peek() const { static std::string e; return end() ? e : ws[i].w; }
    bool fail(const std::string &m) { if (!bad) { bad = true; err.message = m; if (!end()) { err.word = ws[i].w; err.pos = ws[i].pos; } else { err.word = ""; err.pos = ws.empty() ? 0 : ws.back().pos; } } return false; }
};

std::string lower(std::string s) { for (auto &c : s) c = (char)tolower((unsigned char)c); return s; }
// the ASCII form of a word: x for times, +- for plus-minus, c for cent, .. for en dash, - for minus
std::string ascii(std::string s)
{
    auto rep = [&](const char *a, const char *b) { size_t p; while ((p = s.find(a)) != std::string::npos) s.replace(p, strlen(a), b); };
    rep(kTimes, "x"); rep(kPm, "+-"); rep(kCent, "c"); rep(kDash, ".."); rep(kMinus, "-"); rep(kEll, "...");
    return s;
}

std::map<std::string, W> &keywords()
{
    static std::map<std::string, W> m;
    if (m.empty())
        for (int i = 0; i < wCount; i++)
            for (const char *s : {kW[i].lng, kW[i].one, kW[i].sht})
                if (!std::strchr(s, ' ')) m[s] = (W)i;
    return m;
}

// a keyword glued to its value ("lv80", "panl40", "h+0+12"), split where a phrase starts. vocab: extra words of
// the current scope (grains, seq, pad, rand)
void unglue(P &p, std::initializer_list<const char *> vocab = {})
{
    if (p.end()) return;
    std::string w = p.ws[p.i].w;
    auto &kw = keywords();
    auto known = [&](const std::string &x) { if (kw.count(x)) return true; for (const char *v : vocab) if (x == v) return true; return false; };
    if (w.empty() || w[0] == '{' || known(w)) return;
    size_t best = 0;
    for (size_t k = 1; k < w.size(); k++) {
        std::string pre = w.substr(0, k); char nx = w[k];
        if (!known(pre)) continue;
        bool alphaOk = pre == "pan" || pre == "root" || pre == "keys" || pre == "shape" || pre == "curve" || pre == "@";
        if (isdigit((unsigned char)nx) || nx == '+' || nx == '-' || nx == '.' || (alphaOk && isalpha((unsigned char)nx))) best = k;
    }
    if (!best) return;
    Word a{w.substr(0, best), p.ws[p.i].pos}, b{w.substr(best), p.ws[p.i].pos + best};
    p.ws[p.i] = a;
    p.ws.insert(p.ws.begin() + (long)p.i + 1, b);
}
// "a..b", "a-b" (ASCII), "a–b" (already "..") -> a, b. A leading '-' is a sign.
bool splitRange(const std::string &s, std::string &a, std::string &b)
{
    size_t r = s.find("..");
    size_t n = 2;
    if (r == std::string::npos) { r = s.find('-', 1); n = 1; }
    if (r == std::string::npos || r == 0) return false;
    a = s.substr(0, r); b = s.substr(r + n);
    return !a.empty() && !b.empty();
}

// numbers
bool readInt(const std::string &s, size_t &p, long &v)
{
    size_t b = p; bool neg = false;
    if (p < s.size() && (s[p] == '+' || s[p] == '-')) { neg = s[p] == '-'; p++; }
    if (p >= s.size() || !isdigit((unsigned char)s[p])) { p = b; return false; }
    v = 0; while (p < s.size() && isdigit((unsigned char)s[p])) v = v * 10 + (s[p++] - '0');
    if (neg) v = -v;
    return true;
}
bool readDec(const std::string &s, size_t &p, double &v)
{
    size_t b = p; char *e;
    v = std::strtod(s.c_str() + p, &e);
    p = (size_t)(e - s.c_str());
    return p > b;
}
// a duration: "350ms", "350", "1.5s"
bool parseMs(const std::string &w, long &ms)
{
    size_t p = 0; double v;
    if (!readDec(w, p, v)) return false;
    std::string u = w.substr(p);
    if (u == "s") ms = std::lround(v * 1000);
    else if (u == "ms" || u.empty()) { ms = std::lround(v); if (std::fabs(v - ms) > 1e-9) return false; }
    else return false;
    return true;
}
// a percent "80%" / "80" -> int
bool parsePctInt(const std::string &w, long &v)
{
    size_t p = 0;
    if (!readInt(w, p, v)) return false;
    std::string u = w.substr(p);
    return u.empty() || u == "%";
}
// a fraction written as percent "33.33%" -> 1/10000 text (".3333"); ranges "20..40%"
bool parseFracRange(const std::string &w, std::string &out)
{
    std::string s = w;
    if (!s.empty() && s.back() == '%') s.pop_back();
    auto one = [](const std::string &x, std::string &o) {
        size_t p = 0; double v;
        if (!readDec(x, p, v) || p != x.size() || v < 0) return false;
        long f = std::lround(v * 100);
        if (std::fabs(v * 100 - f) > 1e-6) return false;
        o = fracText((int)f);
        return true;
    };
    std::string a, b, ra, rb;
    if (!splitRange(s, ra, rb)) return one(s, out);
    if (!one(ra, a) || !one(rb, b)) return false;
    out = a + "~" + b;
    return true;
}
bool parseNote(const std::string &w, long &n)    // "c#4", "60"
{
    size_t p = 0;
    if (readInt(w, p, n) && p == w.size()) return true;
    if (w.empty()) return false;
    int pc = -1;
    switch (w[0]) { case 'c': pc = 0; break; case 'd': pc = 2; break; case 'e': pc = 4; break; case 'f': pc = 5; break;
                    case 'g': pc = 7; break; case 'a': pc = 9; break; case 'b': pc = 11; break; default: return false; }
    p = 1;
    if (p < w.size() && w[p] == '#') { pc++; p++; } else if (p < w.size() && w[p] == 'b' && p + 1 < w.size()) { pc--; p++; }
    long oct;
    if (!readInt(w, p, oct) || p != w.size()) return false;
    n = (oct + 1) * 12 + pc;
    return true;
}
int pitchClass(const std::string &w)
{
    for (int i = 0; i < 12; i++) if (lower(kNotes[i]) == w) return i;
    return -1;
}
bool parsePmCents(const std::string &w, long &c)    // "+-9c", "9c", "9"
{
    std::string s = w;
    if (s.compare(0, 2, "+-") == 0) s = s.substr(2);
    if (!s.empty() && s.back() == 'c') s.pop_back();
    return isnum(s) && (c = std::atol(s.c_str()), true);
}
bool parsePan(const std::string &w, long &v)     // L40, R40, C, -40, 40
{
    if (w == "c" || w == "0") { v = 0; return true; }
    if ((w[0] == 'l' || w[0] == 'r') && isnum(w.substr(1))) { v = std::atol(w.c_str() + 1) * (w[0] == 'l' ? -1 : 1); return true; }
    size_t p = 0;
    return readInt(w, p, v) && p == w.size();
}

// split glued words: "slower×2" -> "slower","x2"; "lv80" -> "lv","80"; "4rec" -> "4","rec"
std::vector<Word> lex(const std::string &in, size_t base, bool keepFirst = false)
{
    std::vector<Word> out;
    size_t p = 0;
    while (p < in.size()) {
        while (p < in.size() && (isspace((unsigned char)in[p]) || in[p] == ',' || (in.compare(p, 2, kDot) == 0) || in[p] == '|' || in[p] == '/')) {
            if (in.compare(p, 2, kDot) == 0) p += 2;
            else if (in[p] == ',' || isspace((unsigned char)in[p])) p++;
            else break;
        }
        if (p >= in.size()) break;
        size_t b = p;
        if (in[p] == '{') { size_t e = in.find('}', p); if (e == std::string::npos) e = in.size() - 1; out.push_back({in.substr(p, e - p + 1), base + b}); p = e + 1; continue; }
        while (p < in.size() && !isspace((unsigned char)in[p]) && !(in.compare(p, 2, kDot) == 0)) {
            if (in[p] == ',') {   // a comma inside a word belongs to lists like "+0,+12" or "0:0,30:100" or "mutes 1,2"
                if (p + 1 < in.size() && !isspace((unsigned char)in[p + 1]) && p > b) { p++; continue; }
                break;
            }
            p++;
        }
        std::string w = ascii(lower(in.substr(b, p - b)));
        out.push_back({w, base + b});
    }
    // un-glue
    std::vector<Word> r;
    auto &kw = keywords();
    for (auto &x : out) {
        std::string w = x.w;
        if (w[0] == '{' || (keepFirst && &x == &out[0])) { r.push_back(x); continue; }
        // a repeat glued to a step: slower x2
        size_t xp = w.rfind('x');
        if (xp != std::string::npos && xp > 0 && xp + 1 < w.size() && isnum(w.substr(xp + 1)) && kw.count(w.substr(0, xp))) {
            r.push_back({w.substr(0, xp), x.pos}); r.push_back({w.substr(xp), x.pos + xp}); continue;
        }
        // number first: 4rec, 4r, 4recorders
        size_t d = 0; while (d < w.size() && isdigit((unsigned char)w[d])) d++;
        if (d > 0 && d < w.size() && (w.substr(d) == "rec" || w.substr(d) == "r" || w.substr(d) == "recorders" || w.substr(d) == "recorder")) {
            r.push_back({w.substr(0, d), x.pos}); r.push_back({"rec", x.pos + d}); continue;
        }
        r.push_back({w, x.pos});
    }
    return r;
}

bool kwIs(const std::string &s, W w) { auto &kw = keywords(); auto it = kw.find(s); return it != kw.end() && it->second == w; }

// v3 layer subkeys collected while a line is read; written as one token per letter at the end of the layer
struct V3 { std::string W_, N_, S_, Y_, V_, Z_, G_; bool hasG = false, hasN = false; };

bool parseStep(P &p, std::vector<std::string> &toks)
{
    unglue(p);
    std::string w = p.peek();
    auto &kw = keywords();
    auto it = kw.find(w);
    std::string next = p.i + 1 < p.ws.size() ? p.ws[p.i + 1].w : "";
    if (w == "mix" && next == "paste") { p.i += 2; toks = {"X"}; return true; }
    if (w == "cut" && (next == "before" || next == "after")) {
        p.i += 2;
        std::string op = next == "before" ? "[" : "]";
        // an optional position: "cut before 30%", "cut before 250ms"
        if (!p.end()) {
            std::string a = p.peek(); long v;
            if (a.size() > 1 && a.back() == '%' && parsePctInt(a, v)) { p.i++; toks = {"@" + itos(v), op}; return true; }
            if (a.size() > 2 && (a.compare(a.size() - 2, 2, "ms") == 0 || (a.back() == 's' && isdigit((unsigned char)a[0]))) && parseMs(a, v)) { p.i++; toks = {"@t" + itos(v), op}; return true; }
        }
        toks = {op};
        return true;
    }
    if (it == kw.end()) return false;
    static const std::map<W, std::string> simple = {{wLouder, "+"}, {wSofter, "-"}, {wFaster, ">"}, {wSlower, "<"}, {wEcho, "E"},
        {wReverse, "R"}, {wCopy, "C"}, {wPaste, "P"}, {wMixPaste, "X"}, {wCutBefore, "["}, {wCutAfter, "]"}};
    auto s = simple.find(it->second);
    if (s != simple.end()) {
        p.i++;
        if (it->second == wCutBefore || it->second == wCutAfter) {   // short "cut<30" / "cut<250ms"
            if (!p.end()) { std::string a = p.peek(); long v;
                if (a.size() > 1 && a.back() == '%' && parsePctInt(a, v)) { p.i++; toks = {"@" + itos(v), s->second}; return true; }
                if (parseMs(a, v) && !isnum(a)) { p.i++; toks = {"@t" + itos(v), s->second}; return true; } }
        }
        toks = {s->second};
        return true;
    }
    switch (it->second) {
    case wAt: {
        p.i++;
        if (p.end()) return p.fail("a position after 'at': 45% or 250ms");
        std::string a = p.peek(); long v;
        if (a.back() == '%' && parsePctInt(a, v) && v >= 0 && v <= 99) { p.i++; toks = {"@" + itos(v)}; return true; }
        if (!isnum(a) && parseMs(a, v) && v >= 0) { p.i++; toks = {"@t" + itos(v)}; return true; }
        return p.fail("a position: 0% to 99%, or a time such as 250ms or 1.5s");
    }
    case wInsert: case wMix: {
        p.i++;
        if (p.end()) return p.fail("a sound name");
        std::string n = bsynth::dnaName(p.peek());   // ding-xp -> dingxp
        for (char c : n) if (!namech(c)) return p.fail("a sound name (letters, digits, _; ding-xp for XP's ding)");
        p.i++;
        toks = {std::string(it->second == wInsert ? "I" : "M") + n};
        return true;
    }
    case wDouble: p.i++; toks = {"@0", "C", "P"}; return true;
    case wTrim: {
        p.i++;
        if (p.end()) return p.fail("a range: 5..45% or 250ms..750ms");
        std::string a = p.peek(), lo, hi;
        if (!splitRange(a, lo, hi)) return p.fail("a range: 5..45% or 250ms..750ms");
        if (!hi.empty() && hi.back() == '%') {
            long A, B; if (!parsePctInt(lo + "%", A) || !parsePctInt(hi, B) || A <= 0 || B <= A || B > 99) return p.fail("a percent range from more than 0 to at most 99");
            long C = std::lround(100.0 * A / B);
            p.i++; toks = {"@" + itos(B), "]", "@" + itos(C), "["}; return true;
        }
        long A, B;
        std::string unit = hi.size() > 2 && hi.compare(hi.size() - 2, 2, "ms") == 0 ? "ms" : (hi.back() == 's' ? "s" : "ms");
        if (!parseMs(lo.find_first_not_of("0123456789.") == std::string::npos ? lo + unit : lo, A) || !parseMs(hi, B) || B <= A) return p.fail("a time range such as 250ms..750ms");
        p.i++; toks = {"@t" + itos(B), "]", "@t" + itos(A), "["}; return true;
    }
    default: return false;
    }
}

bool parseEnvPts(const std::string &a, bool pan, std::string &out)   // "0:0,30:100" -> "0,0.30,100"
{
    std::vector<std::string> pts;
    size_t b = 0;
    while (b <= a.size()) {
        size_t e = a.find(',', b); if (e == std::string::npos) e = a.size();
        std::string pt = a.substr(b, e - b);
        size_t c = pt.find(':');
        if (c == std::string::npos) return false;
        size_t q = 0; long t, l;
        std::string ts = pt.substr(0, c), ls = pt.substr(c + 1);
        if (ts.size() > 2 && ts.compare(ts.size() - 2, 2, "ms") == 0) ts.resize(ts.size() - 2);
        if (!ls.empty() && ls.back() == '%') ls.pop_back();
        if (!readInt(ts, q, t) || q != ts.size()) return false;
        q = 0;
        if (!readInt(ls, q, l) || q != ls.size()) return false;
        (void)pan;
        pts.push_back(itos(t) + "," + itos(l));
        b = e + 1;
    }
    out = join(pts, ".");
    return !pts.empty();
}

bool parseGene(P &p, std::vector<std::string> &toks, V3 &v3)
{
    unglue(p);
    std::string w = p.peek();
    std::string next = p.i + 1 < p.ws.size() ? p.ws[p.i + 1].w : "";
    auto &kw = keywords();
    if (!w.empty() && w[0] == '{') { if (w.back() != '}') return p.fail("a closing }"); p.i++; toks = {w.substr(1, w.size() - 2)}; return true; }
    if (isnum(w) && kwIs(next, wRec)) { p.i += 2; toks = {"#" + w}; return true; }
    if (isnum(w) && (next == "recorder" || next == "recorders")) { p.i += 2; toks = {"#" + w}; return true; }
    if (w == "fixed" && next == "pitch") { p.i += 2; toks = {"F"}; return true; }
    if (w == "amp" && next == "env") { p.ws[p.i + 1].w = "amp"; p.i++; }
    if (w == "velocity" && next == "start") { p.ws[p.i + 1].w = "velstart"; p.i++; }
    if (w == "pan" && next == "env") { p.ws[p.i + 1].w = "panenv"; p.i++; w = "panenv"; }
    auto it = kw.find(p.peek());
    if (it == kw.end()) return false;
    W k = it->second;
    long v;
    auto arg = [&]() -> std::string { p.i++; return p.end() ? std::string() : p.peek(); };
    switch (k) {
    case wFixed: p.i++; toks = {"F"}; return true;
    case wTranspose: { std::string a = arg(); size_t q = 0; if (!readInt(a, q, v) || q != a.size()) return p.fail("semitones such as +7 or -5"); p.i++; toks = {"T" + itos(v)}; return true; }
    case wNotes: {
        p.i++;
        std::vector<std::string> h;
        while (!p.end()) {
            std::string a = p.peek(); size_t q = 0; bool any = false;
            if (a.empty() || (a[0] != '+' && a[0] != '-')) break;   // intervals are always signed: +0 +12 -12
            while (q < a.size()) { if (!readInt(a, q, v)) break; h.push_back(itos(v)); any = true; }
            if (!any || q != a.size()) return p.fail("intervals such as +0 +12 +7");
            p.i++;
        }
        if (h.empty()) return p.fail("intervals such as +0 +12 +7");
        toks = {"H" + join(h, ",")}; return true;
    }
    case wUnison: {
        std::string a = arg(); size_t q = 0;
        if (!readInt(a, q, v) || v < 1) return p.fail("a voice count such as 2");
        std::string rest = a.substr(q);
        p.i++;
        if (rest.empty() && !p.end() && (p.peek().compare(0, 2, "+-") == 0)) { rest = p.peek(); p.i++; }
        long c = 0;
        if (!rest.empty() && !parsePmCents(rest, c)) { p.i--; return p.fail("a spread such as \xC2\xB1" "9\xC2\xA2"); }
        toks = {"U" + itos(v) + "~" + itos(c)}; return true;
    }
    case wLevel: { std::string a = arg(); if (!parsePctInt(a, v)) return p.fail("a level such as 80%"); p.i++; toks = {"L" + itos(v)}; return true; }
    case wOffset: { std::string a = arg(); if (!parseMs(a, v)) return p.fail("a time such as 120ms"); p.i++; toks = {"O" + itos(v)}; return true; }
    case wPan: { std::string a = arg(); if (a.empty() || !parsePan(a, v)) return p.fail("a pan such as L40, R40 or C"); p.i++; toks = {"Q" + itos(v)}; return true; }
    case wAmp: case wPanEnv: {
        std::string a = arg(), e;
        if (!parseEnvPts(a, k == wPanEnv, e)) return p.fail("points such as 0:0,30:100 (ms:level)");
        p.i++; toks = {std::string(k == wAmp ? "Ja" : "Jp") + e}; return true;
    }
    // ---- v3 window
    case wStart: case wEnd: case wLength: case wVelStart: {
        std::string a = arg(), f;
        if (!parseFracRange(a, f)) return p.fail("a percent of the sound, such as 20% or 20..40%");
        p.i++;
        v3.W_ += std::string(k == wStart ? "s" : k == wEnd ? "e" : k == wLength ? "l" : "v") + f; return true;
    }
    case wTape: { std::string a = arg(); if (!parseMs(a, v)) return p.fail("a time such as 8000ms or 8s"); p.i++; v3.W_ += "m" + itos(v); return true; }
    // ---- v3 voice mode
    case wPoly: { p.i++; v3.hasN = true; if (!p.end() && isnum(p.peek())) { v3.N_ += "p" + p.peek(); p.i++; } else v3.N_ += "p"; return true; }
    case wMono: p.i++; v3.hasN = true; v3.N_ += "m"; return true;
    case wLegato: p.i++; v3.hasN = true; v3.N_ += "l"; return true;
    case wContinue: p.i++; v3.hasN = true; v3.N_ += "c"; return true;
    case wGlide: { std::string a = arg(); if (!parseMs(a, v)) return p.fail("a time such as 80ms"); p.i++; v3.hasN = true; v3.N_ += "g" + itos(v); return true; }
    case wPrio: { std::string a = arg(); if (a != "high" && a != "low" && a != "new") return p.fail("high, low or new"); p.i++; v3.hasN = true; v3.N_ += std::string("k") + (a == "high" ? 'h' : a == "low" ? 'l' : 'n'); return true; }
    // ---- v3 stacking
    case wRoundRobin: p.i++; v3.S_ += "r"; return true;
    case wRandomRec: p.i++; v3.S_ += "p"; return true;
    case wGroup: {
        std::string a = arg(); std::string rnd;
        if (!a.empty() && a.back() == 'r' && isnum(a.substr(0, a.size() - 1))) { rnd = "x"; a.pop_back(); }
        if (!isnum(a)) return p.fail("a group number");
        p.i++;
        if (rnd.empty() && !p.end() && (p.peek() == "random" || p.peek() == "rand")) { rnd = "x"; p.i++; }
        // a random pick in the group needs its 'x' after 'g'; a plain random note before it
        v3.S_ += "g" + a + rnd; return true;
    }
    case wStrum: { std::string a = arg(); if (!parseMs(a, v)) return p.fail("a time such as 30ms"); p.i++; v3.S_ += "s" + itos(v); return true; }
    case wChord: { std::string a = arg(); if (!isnum(a)) return p.fail("a note count such as 3"); p.i++; v3.S_ += "d" + a; return true; }
    case wSpread: { std::string a = arg(), f; if (!parseFracRange(a, f) || f.find('~') != std::string::npos) return p.fail("a width such as 50%"); p.i++; v3.S_ += "w" + f; return true; }
    case wRand: {
        p.i++; unglue(p, {"pitch", "level", "lv", "late", "pan"}); p.i--;
        std::string a = arg();
        if (a == "pitch") { std::string c = arg(); long cc; if (!parsePmCents(c, cc)) return p.fail("cents such as \xC2\xB1" "8\xC2\xA2"); p.i++; v3.Y_ += "d" + itos(cc); return true; }
        if (a.compare(0, 2, "+-") == 0) { long cc; if (!parsePmCents(a, cc)) return p.fail("cents"); p.i++; v3.Y_ += "d" + itos(cc); return true; }
        if (a == "level" || a == "lv") { std::string c = arg(); if (!parsePctInt(c, v)) return p.fail("a percent"); p.i++; v3.Y_ += "l" + itos(v); return true; }
        if (a == "late") { std::string c = arg(); if (!parseMs(c, v)) return p.fail("a time"); p.i++; v3.Y_ += "t" + itos(v); return true; }
        if (a == "pan") { std::string c = arg(); if (!isnum(c)) return p.fail("a pan amount"); p.i++; v3.Y_ += "q" + c; return true; }
        if (a == "note") { p.i++; v3.S_ += "x"; return true; }
        if (a == "recorder") { p.i++; v3.S_ += "p"; return true; }
        return p.fail("pitch, level, late or pan");
    }
    case wRandomNote: p.i++; v3.S_ += "x"; return true;
    case wSeed: { std::string a = arg(); if (a != "key" && a != "recorder") return p.fail("key or recorder"); p.i++; v3.Y_ += a == "key" ? "k" : "r"; return true; }
    case wWow: case wFlutter: case wScoop: {
        std::string a = arg();
        size_t cm = a.find(',');
        std::string c1 = cm == std::string::npos ? a : a.substr(0, cm), c2;
        p.i++;
        if (cm != std::string::npos) c2 = a.substr(cm + 1);
        else { if (p.end()) return p.fail("a second value"); c2 = p.peek(); p.i++; }
        if (!c1.empty() && c1.back() == 'c') c1.pop_back();
        if (!isnum(c1)) { p.i--; return p.fail("cents such as 6\xC2\xA2"); }
        if (k == wWow) {
            if (c2.size() > 2 && c2.compare(c2.size() - 2, 2, "hz") == 0) c2.resize(c2.size() - 2);
            double hz; size_t q = 0;
            if (!readDec(c2, q, hz) || q != c2.size()) return p.fail("a rate such as 0.6Hz");
            v3.V_ += "w" + c1 + "," + itos(std::lround(hz * 10));
        }
        else if (k == wFlutter) { if (c2.size() > 2 && c2.compare(c2.size() - 2, 2, "hz") == 0) c2.resize(c2.size() - 2); if (!isnum(c2)) return p.fail("a rate such as 11Hz"); v3.V_ += "f" + c1 + "," + c2; }
        else { if (!parseMs(c2, v)) return p.fail("a time such as 80ms"); v3.V_ += "s" + c1 + "," + itos(v); }
        return true;
    }
    case wKeys: {
        std::string a = arg();
        long lo = 0, hi = 0;
        bool ok = false;   // "c2-b3", "c-1-g9", "c2..b3": try each dash until both sides are notes
        for (size_t r = 1; r < a.size() && !ok; r++) {
            if (a.compare(r, 2, "..") == 0) ok = parseNote(a.substr(0, r), lo) && parseNote(a.substr(r + 2), hi);
            else if (a[r] == '-') ok = parseNote(a.substr(0, r), lo) && parseNote(a.substr(r + 1), hi);
        }
        if (!ok) return p.fail("a key range such as C2-B3");
        p.i++;
        v3.Z_ = itos(lo) + "," + itos(hi);
        unglue(p);
        if (!p.end() && kwIs(p.peek(), wRoot)) { std::string rt = arg(); long n; if (!parseNote(rt, n)) return p.fail("a root note such as C3"); p.i++; v3.Z_ += "," + itos(n); }
        return true;
    }
    case wGrains: {
        p.i++; v3.hasG = true;
        while (!p.end()) {
            unglue(p, {"pos", "spray", "size", "density", "pitch", "oct", "shape", "scan", "streams", "width"});
            std::string a = p.peek();
            auto val = [&]() -> std::string { p.i++; return p.end() ? std::string() : p.peek(); };
            std::string f;
            if (a == "pos" || a == "spray" || a == "width") { std::string x = val(); if (!parseFracRange(x, f) || f.find('~') != std::string::npos) return p.fail("a percent"); v3.G_ += std::string(a == "pos" ? "p" : a == "spray" ? "j" : "w") + f; p.i++; }
            else if (a == "size") { std::string x = val(); if (x.size() > 2 && x.compare(x.size() - 2, 2, "ms") == 0) x.resize(x.size() - 2); { std::string ra, rb; if (splitRange(x, ra, rb)) x = ra + "~" + rb; } for (char c : x) if (!isdigit((unsigned char)c) && c != '~') return p.fail("a size such as 60..120ms"); v3.G_ += "z" + x; p.i++; }
            else if (a == "density") { std::string x = val(); if (x.size() > 2 && x.compare(x.size() - 2, 2, "/s") == 0) x.resize(x.size() - 2); if (!isnum(x)) return p.fail("grains per second"); v3.G_ += "n" + x; p.i++; }
            else if (a == "pitch") { std::string x = val(); long c; if (!parsePmCents(x, c)) return p.fail("cents"); v3.G_ += "c" + itos(c); p.i++; }
            else if (a == "oct") { std::string x = val(); if (!parsePctInt(x, v)) return p.fail("a percent"); v3.G_ += "o" + itos(v); p.i++; }
            else if (a == "shape") { std::string x = val(); int s = -1; for (int i = 0; i < 4; i++) if (x == kShapes[i]) s = i; if (s < 0) return p.fail("rect, triangle, smooth or hit"); v3.G_ += "e" + itos(s); p.i++; }
            else if (a == "scan") { std::string x = val(); if (!x.empty() && x.back() == 'x') x.pop_back(); double m; size_t q = 0; if (!readDec(x, q, m) || q != x.size()) return p.fail("a speed such as 1x"); v3.G_ += "s" + fracText((int)std::lround(m * 10000)); p.i++; }
            else if (a == "streams") { std::string x = val(); if (!isnum(x)) return p.fail("a count"); v3.G_ += "v" + x; p.i++; }
            else if (a == "back") { v3.G_ += "b"; p.i++; }
            else if (a == "freeze") { v3.G_ += "f"; p.i++; }
            else if (a == "sync") { v3.G_ += "y"; p.i++; }
            else break;
        }
        return true;
    }
    default: return false;
    }
}

bool parseGlobal(P &p, std::vector<std::string> &toks)
{
    unglue(p);
    std::string w = p.peek();
    std::string next = p.i + 1 < p.ws.size() ? p.ws[p.i + 1].w : "";
    if (!w.empty() && w[0] == '{') { if (w.back() != '}') return p.fail("a closing }"); p.i++; toks = {w.substr(1, w.size() - 2)}; return true; }
    if (w == "kit" && next == "off") { p.i += 2; toks = {"kd"}; return true; }
    auto &kw = keywords();
    // macros: "macro1 50%", "m1 50%", "m1 layer2 pan -100..100", "m1 all start 200..400"
    if ((w.compare(0, 5, "macro") == 0 && w.size() == 6) || (w.size() == 2 && w[0] == 'm') || ((w == "macro" || w == "m") && next.size() == 1 && isdigit((unsigned char)next[0]))) {
        char K = w.back();
        if (w == "macro" || w == "m") { K = next[0]; p.i++; }
        if (K < '1' || K > '4') return p.fail("a macro number 1..4");
        p.i++;
        std::string a = p.peek();
        long v;
        if (a.empty()) return p.fail("a value such as 50% or a mapping such as layer2 pan -100..100");
        if (parsePctInt(a, v) && a.find("..") == std::string::npos) { p.i++; toks = {std::string("m") + K + "=" + itos(v)}; return true; }
        char L;
        if (a == "all") L = '0';
        else if ((a.compare(0, 5, "layer") == 0 && a.size() == 6) || (a.size() == 2 && a[0] == 'l')) L = a.back();
        else if (a == "layer" && p.i + 1 < p.ws.size() && p.ws[p.i + 1].w.size() == 1) { p.i++; L = p.peek()[0]; }
        else return p.fail("all, layer1..layer8 or L1..L8");
        if (L < '0' || L > '8') return p.fail("a layer 1..8");
        p.i++;
        std::string pw = p.peek(); char P_ = 0;
        for (int i = 0; kMacroParams[i]; i++) if (pw == kMacroWords[i]) P_ = kMacroParams[i];
        if (!P_) return p.fail("a macro target such as pan, level, start");
        p.i++;
        std::string r = p.peek(), a1, a2; size_t q = 0; long lo, hi;
        if (!splitRange(r, a1, a2)) return p.fail("a range such as -100..100");
        if (!readInt(a1, q, lo) || q != a1.size()) return p.fail("a range such as -100..100");
        q = 0;
        if (!readInt(a2, q, hi) || q != a2.size()) return p.fail("a range such as -100..100");
        p.i++;
        toks = {std::string("m") + K + L + P_ + itos(lo) + "," + itos(hi)}; return true;
    }
    auto it = kw.find(w);
    if (it == kw.end()) return false;
    W k = it->second;
    auto arg = [&]() -> std::string { p.i++; return p.end() ? std::string() : p.peek(); };
    long v;
    switch (k) {
    case wAttack: case wDecay: case wRelease: { std::string a = arg(); if (!parseMs(a, v)) return p.fail("a time such as 350ms"); p.i++; toks = {std::string(1, k == wAttack ? 'A' : k == wDecay ? 'D' : 'R') + itos(v)}; return true; }
    case wSustain: case wVelocity: { std::string a = arg(); if (!parsePctInt(a, v)) return p.fail("a percent such as 70%"); p.i++; toks = {std::string(1, k == wSustain ? 'S' : 'V') + itos(v)}; return true; }
    case wBend: { std::string a = arg(); if (a.compare(0, 2, "+-") == 0) a = a.substr(2); if (!isnum(a)) return p.fail("semitones such as \xC2\xB1" "12"); p.i++; toks = {"B" + a}; return true; }
    case wRoot: { std::string a = arg(); if (!parseNote(a, v)) return p.fail("a note such as C4 or 60"); p.i++; toks = {"K" + itos(v)}; return true; }
    case wGain: { std::string a = arg(); if (a.size() > 2 && a.compare(a.size() - 2, 2, "db") == 0) a.resize(a.size() - 2); size_t q = 0; if (!readInt(a, q, v) || q != a.size()) return p.fail("decibels such as -6dB"); p.i++; toks = {"G" + itos(v)}; return true; }
    case wKitOff: p.i++; toks = {"kd"}; return true;
    case wScale: {
        std::string a = arg(); int sc = -1;
        for (int i = 0; i < kScaleCount; i++) if (a == kScaleWords[i]) sc = i;
        if (sc < 0) return p.fail("a scale such as major, minor, dorian, blues");
        p.i++;
        std::string t = "q" + itos(sc);
        if (!p.end() && p.peek() == "root") p.i++;
        if (!p.end() && pitchClass(p.peek()) >= 0) { t += "r" + itos(pitchClass(p.peek())); p.i++; }
        toks = {t}; return true;
    }
    case wSeq: {
        p.i++;
        std::string t = "x";
        while (!p.end()) {
            unglue(p, {"gate", "swing", "max", "dig", "octaves", "steps", "bpm"});
            std::string a = p.peek();
            auto num = [&](const char *key) { p.i++; std::string x = p.end() ? "" : p.peek(); if (!x.empty() && x.back() == '%') x.pop_back(); if (!isnum(x)) return p.fail("a number"); t += key + x; p.i++; return true; };
            if (a.compare(0, 2, "1/") == 0) { std::string d = a.substr(2); bool tr = !d.empty() && d.back() == 't'; if (tr) d.pop_back(); if (!isnum(d)) return p.fail("a division such as 1/16"); t += "d" + d + (tr ? "t" : ""); p.i++; }
            else if (a == "gate") { if (!num("g")) return false; }
            else if (a == "swing") { if (!num("s")) return false; }
            else if (a == "max") { if (!num("p")) return false; }
            else if (a == "dig") { if (!num("a")) return false; }
            else if (a == "octaves") { if (!num("o")) return false; }
            else if (a == "steps") { if (!num("l")) return false; }
            else if (a == "bpm") { if (!num("b")) return false; }
            else if (a == "count") { t += "n1"; p.i++; }
            else if (a == "arp") { t += "n2"; p.i++; }
            else if (a == "field") { t += "n0"; p.i++; }
            else if (a == "free-run") { t += "f"; p.i++; }
            else if (a == "latch") { t += "h"; p.i++; }
            else break;
        }
        toks = {t}; return true;
    }
    case wPad: {
        std::string a = arg(), ra, rb;
        std::string t = "k";
        if (!splitRange(a, ra, rb)) { if (!isnum(a)) return p.fail("a note number such as 36 or 47..53"); t += a; }
        else { if (!isnum(ra) || !isnum(rb)) return p.fail("a note range such as 47..53"); t += ra + "," + rb; }
        p.i++;
        while (!p.end()) {
            unglue(p, {"layer", "seg", "start", "end", "root", "pitch", "range", "tune", "level", "pan", "curve", "vel", "cut", "fade", "mutes", "voices", "out"});
            std::string b = p.peek();
            auto val = [&]() -> std::string { p.i++; return p.end() ? std::string() : p.peek(); };
            std::string f;
            if (b == "layer" || b == "seg" || b == "root" || b == "voices" || b == "out" || b == "cut") {
                std::string x = val(); if (!isnum(x)) return p.fail("a number");
                t += std::string(b == "layer" ? "l" : b == "seg" ? "j" : b == "root" ? "r" : b == "voices" ? "n" : b == "out" ? "o" : "c") + x; p.i++;
            }
            else if (b == "start" || b == "end") { std::string x = val(); if (!parseFracRange(x, f)) return p.fail("a percent such as 20%"); t += (b == "start" ? "s" : "e") + f; p.i++; }
            else if (b == "pitch" || b == "level") { std::string x = val(); if (!parsePctInt(x, v)) return p.fail("a percent"); t += (b == "pitch" ? "p" : "i") + itos(v); p.i++; }
            else if (b == "range") { std::string x = val(); if (x.compare(0, 2, "+-") == 0) x = x.substr(2); if (!isnum(x)) return p.fail("semitones such as \xC2\xB1" "12"); t += "w" + x; p.i++; }
            else if (b == "tune") { std::string x = val(); if (!x.empty() && x.back() == 'c') x.pop_back(); size_t q = 0; if (!readInt(x, q, v) || q != x.size()) return p.fail("cents such as +20\xC2\xA2"); t += (v < 0 ? "b" : "t") + itos(std::labs(v)); p.i++; }
            else if (b == "pan") { std::string x = val(); if (x.empty() || !parsePan(x, v)) return p.fail("a pan such as L30"); t += "h" + itos(v + 100); p.i++; }
            else if (b == "curve") { std::string x = val(); int c = -1; for (int i = 0; i < 4; i++) if (x == kCurves[i]) c = i; if (c < 0) return p.fail("linear, soft, hard or fixed"); t += "v" + itos(c); p.i++; }
            else if (b == "vel") {
                std::string x = val(), ra, rb;
                if (x.back() != '%' && splitRange(x, ra, rb)) { if (!isnum(ra) || !isnum(rb)) return p.fail("a velocity range such as 1..100"); t += "y" + ra + "," + rb; }
                else { if (!parsePctInt(x, v)) return p.fail("a velocity amount such as 80% or a range such as 1..100"); t += "a" + itos(v); }
                p.i++;
            }
            else if (b == "fade") { std::string x = val(); if (!parseMs(x, v)) return p.fail("a time such as 20ms"); t += "f" + itos(v); p.i++; }
            else if (b == "mutes") { std::string x = val(); for (char c : x) if (!isdigit((unsigned char)c) && c != ',') return p.fail("groups such as 1,2"); t += "u" + x; p.i++; }
            else if (b == "gated") { t += "g"; p.i++; }
            else if (b == "random") { t += "z"; p.i++; }
            else break;
        }
        toks = {t}; return true;
    }
    default: return false;
    }
}

}  // namespace


// ------------------------------------------------------------------------------------------------ API
std::string toRecipe(const std::string &dna, RecipeForm f, size_t maxLen)
{
    Cut c = cut(canonical3(dna));
    std::vector<std::string> lines;
    for (auto &L : c.layers) {
        std::vector<Item> items;
        for (size_t i = 1; i < L.size(); i++) {
            // sugar first, each checked by parsing it back
            auto tryItem = [&](const std::string &text, size_t n) {
                if (i + n > L.size()) return false;
                std::vector<std::string> want(L.begin() + i, L.begin() + i + n);
                P p; p.ws = lex(text, 0);
                std::vector<std::string> got;
                if (!parseStep(p, got) || !p.end() || got != want) return false;
                items.push_back({text, true, want}); i += n - 1; return true;
            };
            bool sh = f == RecipeForm::Short;
            const std::string &a = L[i];
            std::string b = i + 1 < L.size() ? L[i + 1] : "", c2 = i + 2 < L.size() ? L[i + 2] : "", d = i + 3 < L.size() ? L[i + 3] : "";
            if (a == "@0" && b == "C" && c2 == "P" && tryItem(spell(wDouble, f), 3)) continue;
            if (a.size() > 2 && a.compare(0, 2, "@t") == 0 && b == "]" && c2.size() > 2 && c2.compare(0, 2, "@t") == 0 && d == "[") {
                long B = std::atol(a.c_str() + 2), A = std::atol(c2.c_str() + 2);
                std::string lo = msText(A), hi = msText(B);
                if (lo.back() == 's' && lo[lo.size() - 2] != 'm' && hi.back() == 's' && hi[hi.size() - 2] != 'm') lo.pop_back();
                else if (lo.size() > 2 && lo.compare(lo.size() - 2, 2, "ms") == 0 && hi.size() > 2 && hi.compare(hi.size() - 2, 2, "ms") == 0) lo.resize(lo.size() - 2);
                if (A < B && tryItem(std::string(spell(wTrim, f)) + " " + lo + "-" + hi, 4)) continue;
            }
            if (a.size() > 1 && a[0] == '@' && a[1] != 't' && b == "]" && c2.size() > 1 && c2[0] == '@' && c2[1] != 't' && d == "[") {
                long B = std::atol(a.c_str() + 1), C = std::atol(c2.c_str() + 1), A = std::lround(C * B / 100.0);
                if (A > 0 && A < B && tryItem(std::string(spell(wTrim, f)) + " " + itos(A) + "-" + itos(B) + "%", 4)) continue;
            }
            if (a.size() > 1 && a[0] == '@' && (b == "[" || b == "]")) {
                std::string pos = a[1] == 't' ? msText(std::atol(a.c_str() + 2)) : a.substr(1) + "%";
                if (tryItem(std::string(spell(b == "[" ? wCutBefore : wCutAfter, f)) + (sh ? "" : " ") + pos, 2)) continue;
            }
            items.push_back(layerPhrase(a, f));
        }
        // repeats: the same step phrase n times in a row -> "phrase ×n"
        std::vector<std::string> parts;
        std::vector<bool> isStep;
        for (size_t i = 0; i < items.size();) {
            size_t j = i + 1;
            if (items[i].step) while (j < items.size() && items[j].step && items[j].text == items[i].text) j++;
            std::string t = items[i].text;
            // x N: glued to a one-word step in the compact forms ("slower×2"), spaced after a phrase ("mix tada ×2")
            if (j - i > 1) t += " x" + itos((long)(j - i));   // always spaced: "slower x2" (pretty: "slower ×2")
            parts.push_back(t); isStep.push_back(items[i].step);
            i = j;
        }
        std::string src = L[0].empty() ? "-" : bsynth::displayName(L[0]), line = src;
        if (f == RecipeForm::Lines) {
            // steps joined by ", ", genes by " · ", a wide gap where steps and genes meet
            for (size_t k = 0; k < parts.size(); k++) {
                if (k == 0) line += std::string(std::max<int>(3, 9 - (int)src.size()), ' ');   // never exactly 2: that is the separator
                else if (isStep[k] != isStep[k - 1]) line += "   ";
                else line += isStep[k] ? ", " : std::string("  ");
                line += parts[k];
            }
        } else for (auto &x : parts) line += " " + x;
        lines.push_back(line);
    }
    std::vector<std::string> g;
    for (auto &t : c.globals) g.push_back(globalPhrase(t, f));
    std::string out;
    if (f == RecipeForm::Lines) {
        out = join(lines, "\n");
        if (c.hasGlobals) out += (lines.empty() ? "" : "\n") + std::string("env      ") + join(g, std::string("  "));
        return out;
    }
    out = join(lines, " / ");
    if (c.hasGlobals) out += (lines.empty() ? "" : " ") + std::string("| ") + join(g, " ");
    if (f == RecipeForm::Short && maxLen && out.size() > maxLen) {
        // cut at a word, mark it: no longer a recipe ("…" makes fromRecipe refuse it)
        size_t cutAt = out.rfind(' ', maxLen - 3);
        if (cutAt == std::string::npos || cutAt == 0) cutAt = maxLen - 3;
        out = out.substr(0, cutAt) + "...";
    }
    return out;
}

// ------------------------------------------------------------------------------------------------ display form
// prettify: a pure character substitution of the ASCII recipe, for reading. asciify undoes it exactly.
//   " x<digits>" (a repeat, before a space, ',' or the end) -> " ×<digits>"
//   "+-"                                           -> "±"
//   "<digit>c" before a space, ',', '|', end       -> "<digit>¢"
//   "-" after a digit, before a digit, A-G or '-'  -> "–"   (a range; a sign never follows a digit)
//   exactly two spaces between two words           -> " · " (the separator of voice words)
//   "..." (a cut short form)                       -> "…"
std::string prettify(const std::string &a)
{
    std::string o;
    size_t n = a.size();
    for (size_t i = 0; i < n; i++) {
        char c = a[i];
        if (c == 'x' && i > 0 && a[i - 1] == ' ' && i + 1 < n && isdigit((unsigned char)a[i + 1])) {
            size_t j = i + 1; while (j < n && isdigit((unsigned char)a[j])) j++;
            if (j == n || a[j] == ' ' || a[j] == ',' || a[j] == '\n') { o += kTimes; continue; }
        }
        if (c == '+' && i + 1 < n && a[i + 1] == '-') { o += kPm; i++; continue; }
        if (c == 'c' && i > 0 && isdigit((unsigned char)a[i - 1]) && (i + 1 == n || std::strchr(" ,|\n", a[i + 1]))) { o += kCent; continue; }
        if (c == '-' && i > 0 && isdigit((unsigned char)a[i - 1]) && i + 1 < n && (isdigit((unsigned char)a[i + 1]) || std::strchr("ABCDEFGabcdefg-", a[i + 1]))) { o += kDash; continue; }
        if (c == ' ' && i + 1 < n && a[i + 1] == ' ' && i > 0 && a[i - 1] != ' ' && a[i - 1] != '\n' && i + 2 < n && a[i + 2] != ' ' && a[i + 2] != '\n') { o += std::string(" ") + kDot + " "; i++; continue; }
        if (c == '.' && a.compare(i, 3, "...") == 0) { o += kEll; i += 2; continue; }
        o += c;
    }
    return o;
}
std::string asciify(const std::string &p)
{
    std::string o;
    for (size_t i = 0; i < p.size();) {
        auto at = [&](const char *u) { return p.compare(i, strlen(u), u) == 0; };
        if (at(" \xC2\xB7 ")) { o += "  "; i += 4; }
        else if (at(kTimes)) { o += 'x'; i += 2; }
        else if (at(kPm)) { o += "+-"; i += 2; }
        else if (at(kCent)) { o += 'c'; i += 2; }
        else if (at(kDash)) { o += '-'; i += 3; }
        else if (at(kEll)) { o += "..."; i += 3; }
        else if (at(kMinus)) { o += '-'; i += 3; }
        else if (at(kDot)) { o += ' '; i += 2; }
        else o += p[i++];
    }
    return o;
}

bool fromRecipe(const std::string &text, std::string &dna, RecipeError *errOut)
{
    RecipeError err;
    auto fail = [&](size_t pos, const std::string &w, const std::string &m) { err.pos = pos; err.word = w; err.message = m; if (errOut) *errOut = err; return false; };
    if (text.find(kEll) != std::string::npos || text.find("...") != std::string::npos)
        return fail(text.find(kEll) != std::string::npos ? text.find(kEll) : text.find("..."), "...", "a shortened recipe (it ends in ...): it cannot be read back; use the one-line form");
    // split into layer chunks and the globals. Each line: "env ..." = globals (multi-line form); otherwise layers
    // separated by " / ", then optionally " | " and the globals (one-line form). A line may also start with "| ".
    struct Chunk { std::string s; size_t base; bool globals; };
    std::vector<Chunk> chunks;
    if (text.find_first_not_of(" \t\r\n") == std::string::npos) { dna = canonical3(""); return true; }
    size_t b0 = 0;
    while (b0 <= text.size()) {
        size_t e0 = text.find('\n', b0); if (e0 == std::string::npos) e0 = text.size();
        std::string line = text.substr(b0, e0 - b0);
        while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
        size_t f0 = line.find_first_not_of(" \t");
        if (f0 != std::string::npos) {
            size_t sp = line.find_first_of(" \t", f0);
            std::string first = lower(line.substr(f0, sp == std::string::npos ? std::string::npos : sp - f0));
            if (first == "env") chunks.push_back({line.substr(f0 + 3), b0 + f0 + 3, true});
            else {
                size_t bar = line.compare(f0, 2, "| ") == 0 || line.substr(f0) == "|" ? f0 : line.find(" | ");
                std::string lay = bar == std::string::npos ? line : line.substr(0, bar);
                if (lay.find_first_not_of(" \t") != std::string::npos) {
                    size_t b = 0;
                    while (b <= lay.size()) {
                        size_t e = lay.find(" / ", b); if (e == std::string::npos) e = lay.size();
                        chunks.push_back({lay.substr(b, e - b), b0 + b, false});
                        b = e + 3;
                    }
                }
                if (bar != std::string::npos) { size_t gb = bar == f0 ? f0 + 1 : bar + 3; chunks.push_back({line.substr(std::min(gb, line.size())), b0 + gb, true}); }
            }
        }
        b0 = e0 + 1;
    }
    std::vector<std::string> layers;
    std::string globals;
    bool hasGlobals = false;
    for (auto &ch : chunks) {
        P p;
        p.ws = lex(ch.s, ch.base, !ch.globals);
        if (ch.globals) {
            hasGlobals = true;
            while (!p.end()) {
                std::vector<std::string> toks;
                size_t at = p.i;
                if (!parseGlobal(p, toks)) {
                    if (p.bad) return fail(p.err.pos, p.err.word, p.err.message);
                    p.i = at;
                    return fail(p.ws[at].pos, p.ws[at].w, "a global word: attack, decay, sustain, release, bend, velocity, root, gain, macro, scale, seq, pad, kit off or {raw}");
                }
                for (auto &x : toks) globals += x;
            }
            continue;
        }
        if (p.end()) return fail(ch.base, "", "an empty layer: write - for a layer with no sound");
        std::string src = p.peek();
        if (src == "-") src = "";
        src = bsynth::dnaName(src);   // ding-xp -> dingxp
        for (char c : src) if (!namech(c)) return fail(p.ws[0].pos, p.ws[0].w, "a sound name first (letters, digits, _; ding-xp for XP's ding), or - for none");
        p.i++;
        std::string L = src;
        V3 v3;
        while (!p.end()) {
            std::vector<std::string> toks;
            size_t at = p.i;
            if (parseStep(p, toks)) {
                long n = 1;
                if (!p.end() && p.peek().size() > 1 && p.peek()[0] == 'x' && isnum(p.peek().substr(1))) { n = std::atol(p.peek().c_str() + 1); p.i++; }
                else if (!p.end() && p.peek() == "x" && p.i + 1 < p.ws.size() && isnum(p.ws[p.i + 1].w)) { n = std::atol(p.ws[p.i + 1].w.c_str()); p.i += 2; }
                if (n < 1 || n > 64) return fail(p.ws[p.i - 1].pos, p.ws[p.i - 1].w, "a repeat from x1 to x64");
                for (long k = 0; k < n; k++) for (auto &x : toks) L += x;
                continue;
            }
            if (p.bad) return fail(p.err.pos, p.err.word, p.err.message);
            p.i = at;
            if (parseGene(p, toks, v3)) { for (auto &x : toks) L += x; continue; }
            if (p.bad) return fail(p.err.pos, p.err.word, p.err.message);
            return fail(p.ws[at].pos, p.ws[at].w, "a Sound Recorder step (faster, slower, louder, softer, echo, reverse, at, cut before/after, copy, paste, mix paste, insert, mix, double, trim) or a voice word (recorders, transpose, notes, unison, fixed, level, offset, pan, amp, ...)");
        }
        if (!v3.W_.empty()) L += "W" + v3.W_;
        if (v3.hasN) L += "N" + v3.N_;
        if (!v3.S_.empty()) L += "S" + v3.S_;
        if (!v3.Y_.empty()) L += "Y" + v3.Y_;
        if (!v3.V_.empty()) L += "V" + v3.V_;
        if (!v3.Z_.empty()) L += "Z" + v3.Z_;
        if (v3.hasG) L += "G" + v3.G_;
        layers.push_back(L);
    }
    std::string d = join(layers, "/");
    // core reads "a/" as one layer but writes two layers with an empty last one as "a/": to get that form back the
    // text must end in "//" (core's canonical form is not idempotent there; noted in PRESET-ENGINE-2.md 14)
    if (layers.size() > 1 && strip3(layers.back()).empty()) d += "/";
    if (hasGlobals) d += ";" + globals;
    dna = canonical3(d);
    return true;
}

}  // namespace bsynth3
