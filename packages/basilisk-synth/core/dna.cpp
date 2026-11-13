#include "dna.h"
#include <algorithm>
#include <cctype>
#include <cstdio>

namespace bsynth {

const char *const kSoundNames[kSoundCount] = {
    "chimes", "chord", "ding", "notify", "recycle", "ringin", "ringout", "start", "tada",
    "balloon", "batcrit", "batlow", "critstop", "default", "xpding", "error", "exclaim", "hwfail",
    "hwin", "hwout", "infobar", "logoff", "logon", "menu", "minimize", "xpnotify", "popup", "print",
    "xprecycle", "restore", "xpringin", "xpringout", "shutdown", "startup", "xpstart"};
const char *const kSoundFilesXP[kSoundCount] = {
    "chimes.wav", "chord.wav", "ding.wav", "notify.wav", "recycle.wav", "ringin.wav", "ringout.wav", "start.wav", "tada.wav",
    "Windows XP Balloon.wav", "Windows XP Battery Critical.wav", "Windows XP Battery Low.wav", "Windows XP Critical Stop.wav",
    "Windows XP Default.wav", "Windows XP Ding.wav", "Windows XP Error.wav", "Windows XP Exclamation.wav",
    "Windows XP Hardware Fail.wav", "Windows XP Hardware Insert.wav", "Windows XP Hardware Remove.wav",
    "Windows XP Information Bar.wav", "Windows XP Logoff Sound.wav", "Windows XP Logon Sound.wav",
    "Windows XP Menu Command.wav", "Windows XP Minimize.wav", "Windows XP Notify.wav", "Windows XP Pop-up Blocked.wav",
    "Windows XP Print complete.wav", "Windows XP Recycle.wav", "Windows XP Restore.wav", "Windows XP Ringin.wav",
    "Windows XP Ringout.wav", "Windows XP Shutdown.wav", "Windows XP Startup.wav", "Windows XP Start.wav"};

int soundIndex(const std::string &name)
{
    for (int i = 0; i < kSoundCount; i++) if (name == kSoundNames[i]) return i;
    return -1;
}

const char *soundFile311(int i)
{
    switch (i) {
    case 0: return "C:\\WINDOWS\\CHIMES.WAV";
    case 5: return "C:\\WINDOWS\\RINGIN.WAV";
    case 6: return "C:\\WINDOWS\\RINGOUT.WAV";
    default: return "C:\\WINDOWS\\DING.WAV";
    }
}

static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

int clampGlobal(char c, int v)
{
    switch (c) {
    case 'A': case 'D': case 'R': return clampi(v, 0, 20000);
    case 'S': return clampi(v, 0, 100);
    case 'B': return clampi(v, 0, 48);
    case 'V': return clampi(v, 0, 100);
    case 'K': return clampi(v, 0, 127);
    case 'G': return clampi(v, -60, 24);
    }
    return v;
}

namespace {
struct Reader {
    const std::string &s; size_t p = 0;
    explicit Reader(const std::string &t) : s(t) {}
    bool end() const { return p >= s.size(); }
    char peek() const { return p < s.size() ? s[p] : 0; }
    static bool namech(char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'); }
    std::string name() { size_t b = p; while (p < s.size() && namech(s[p])) p++; return s.substr(b, p - b); }
    bool hasInt() const {
        size_t q = p;
        if (q < s.size() && (s[q] == '-' || s[q] == '+')) q++;
        return q < s.size() && isdigit((unsigned char)s[q]);
    }
    int integer(int dflt = 0) {   // INT := ['-'|'+']? [0-9]+ ; absent -> dflt
        if (!hasInt()) return dflt;
        bool neg = false;
        if (s[p] == '-' || s[p] == '+') { neg = s[p] == '-'; p++; }
        long v = 0;
        while (p < s.size() && isdigit((unsigned char)s[p])) { if (v < 100000000) v = v * 10 + (s[p] - '0'); p++; }
        return (int)(neg ? -v : v);
    }
};
std::string num(int v) { return std::to_string(v); }

void parseLayer(Reader &r, Layer &L)
{
    std::string nm = r.name();
    L.source = soundIndex(nm);
    L.tokens.push_back(nm);
    while (!r.end() && r.peek() != '/' && r.peek() != ';') {
        char c = r.peek(); r.p++;
        switch (c) {
        case '+': case '-': case '>': case '<': case 'E': case 'R': case '[': case ']': case 'C': case 'P': case 'X':
            if ((int)L.steps.size() < kMaxSteps) { Step s; s.op = c; L.steps.push_back(s); L.tokens.push_back(std::string(1, c)); }
            break;
        case '@': {
            int v = clampi(r.integer(0), 0, 99);
            if ((int)L.steps.size() < kMaxSteps) { Step s; s.op = '@'; s.arg = v; L.steps.push_back(s); L.tokens.push_back("@" + num(v)); }
            break; }
        case 'I': case 'M': {
            std::string n = r.name();
            int si = soundIndex(n);
            if (si >= 0 && (int)L.steps.size() < kMaxSteps) { Step s; s.op = c; s.sound = si; L.steps.push_back(s); L.tokens.push_back(std::string(1, c) + n); }
            break; }
        case '#': { int v = clampi(r.integer(1), 1, kRecorders); L.pool = v; L.tokens.push_back("#" + num(v)); break; }
        case 'T': { int v = clampi(r.integer(0), -48, 48); L.transpose = v; L.tokens.push_back("T" + num(v)); break; }
        case 'H': {
            std::vector<int> h; std::string t = "H";
            do {
                if (!h.empty()) r.p++;   // the comma
                int v = clampi(r.integer(0), -48, 48);
                if ((int)h.size() < kMaxHarmony) { if (!h.empty()) t += ","; h.push_back(v); t += num(v); }
            } while (r.peek() == ',' );
            L.harmony = h; L.tokens.push_back(t);
            break; }
        case 'U': {
            int n = clampi(r.integer(1), 1, 8), cents = 0;
            if (r.peek() == '~') { r.p++; cents = clampi(r.integer(0), 0, 100); }
            L.unison = n; L.spreadCents = cents; L.tokens.push_back("U" + num(n) + "~" + num(cents));
            break; }
        case 'F': L.fixed = true; L.tokens.push_back("F"); break;
        case 'L': { int v = clampi(r.integer(100), 0, 400); L.level = v; L.tokens.push_back("L" + num(v)); break; }
        default: break;   // unknown character: skipped (and dropped from the canonical form)
        }
    }
}

void parseGlobals(Reader &r, Globals &g)
{
    while (!r.end()) {
        char c = r.peek(); r.p++;
        int *f = nullptr;
        switch (c) {
        case 'A': f = &g.attack; break; case 'D': f = &g.decay; break; case 'S': f = &g.sustain; break;
        case 'R': f = &g.release; break; case 'B': f = &g.bendRange; break; case 'V': f = &g.velocity; break;
        case 'K': f = &g.root; break; case 'G': f = &g.gainDb; break;
        default: continue;
        }
        if (!r.hasInt()) continue;           // a letter with no number is ignored
        *f = clampGlobal(c, r.integer());
        g.tokens.push_back(std::string(1, c) + num(*f));
    }
}

std::string join(const Dna &d, bool withGlobals)
{
    std::string out;
    for (size_t i = 0; i < d.layers.size(); i++) {
        if (i) out += '/';
        for (auto &t : d.layers[i].tokens) out += t;
    }
    if (withGlobals && !d.g.tokens.empty()) { out += ';'; for (auto &t : d.g.tokens) out += t; }
    return out;
}
}  // namespace

std::string Dna::layersText() const { return join(*this, false); }

void assignPools(Dna &d)
{
    int left = kRecorders, at = 0;
    std::vector<int> valid;
    for (size_t i = 0; i < d.layers.size(); i++) { d.layers[i].first = 0; d.layers[i].count = 0; if (d.layers[i].valid()) valid.push_back((int)i); }
    // fixed #N in layer order. Each keeps one recorder back for every non-empty layer after it and for every
    // earlier layer without #, so every non-empty layer gets at least one (8 layers always fit in 16 recorders).
    for (size_t k = 0; k < valid.size(); k++) {
        Layer &L = d.layers[valid[k]];
        if (!L.pool) continue;
        int later = (int)(valid.size() - k - 1);
        for (size_t j = 0; j < k; j++) if (!d.layers[valid[j]].pool) later++;
        int cap = left - later;
        int give = L.pool < cap ? L.pool : cap;
        if (give < 1) give = left > 0 ? 1 : 0;
        L.count = give; left -= give;
    }
    // the rest split evenly among the layers without #, earlier layers taking the remainder
    std::vector<int> free;
    for (int i : valid) if (!d.layers[i].pool) free.push_back(i);
    if (!free.empty() && left > 0) {
        int each = left / (int)free.size(), rem = left % (int)free.size();
        for (size_t k = 0; k < free.size(); k++) {
            int give = each + ((int)k < rem ? 1 : 0);
            d.layers[free[k]].count = give;
        }
    }
    for (auto &L : d.layers) { L.first = at; at += L.count; }
}

Dna parse(const std::string &in)
{
    Dna d;
    std::string text = in.substr(0, kMaxDnaBytes);
    // spaces and anything non-printable are not part of a DNA
    text.erase(std::remove_if(text.begin(), text.end(), [](char c) { return c <= ' ' || c > '~'; }), text.end());
    Reader r(text);
    while (!r.end() && r.peek() != ';') {
        Layer L;
        parseLayer(r, L);
        if ((int)d.layers.size() < kMaxLayers) d.layers.push_back(L);
        if (r.peek() == '/') r.p++;
    }
    if (r.peek() == ';') { r.p++; parseGlobals(r, d.g); }
    assignPools(d);
    d.canonical = join(d, true);
    return d;
}

std::string canonical(const std::string &t) { return parse(t).canonical; }

std::string setGlobal(const std::string &dna, char c, int v)
{
    Dna d = parse(dna);
    v = clampGlobal(c, v);
    std::string tok = std::string(1, c) + std::to_string(v);
    bool done = false;
    for (int i = (int)d.g.tokens.size() - 1; i >= 0 && !done; i--)
        if (d.g.tokens[i][0] == c) { d.g.tokens[i] = tok; done = true; }
    if (!done) d.g.tokens.push_back(tok);
    return parse(join(d, true)).canonical;
}

std::string setLayerGene(const std::string &dna, int li, char c, int v, int v2)
{
    Dna d = parse(dna);
    if (li < 0 || li >= (int)d.layers.size()) return d.canonical;
    std::string tok;
    switch (c) {
    case 'T': tok = "T" + std::to_string(clampi(v, -48, 48)); break;
    case 'L': tok = "L" + std::to_string(clampi(v, 0, 400)); break;
    case '#': tok = "#" + std::to_string(clampi(v, 1, kRecorders)); break;
    case 'U': tok = "U" + std::to_string(clampi(v, 1, 8)) + "~" + std::to_string(clampi(v2, 0, 100)); break;
    case 'F': tok = v ? "F" : ""; break;
    default: return d.canonical;
    }
    auto &T = d.layers[li].tokens;
    bool done = false;
    for (int i = (int)T.size() - 1; i >= 1 && !done; i--)
        if (T[i][0] == c) { if (tok.empty()) T.erase(T.begin() + i); else T[i] = tok; done = true; }
    if (!done && !tok.empty()) T.push_back(tok);
    return parse(join(d, true)).canonical;
}

std::string setLayerSource(const std::string &dna, int li, const std::string &name)
{
    Dna d = parse(dna);
    if (li < 0 || li >= (int)d.layers.size()) return d.canonical;
    d.layers[li].tokens[0] = name;
    return parse(join(d, true)).canonical;
}

std::string appendStep(const std::string &dna, int li, char op, int arg, const std::string &name)
{
    Dna d = parse(dna);
    if (li < 0 || li >= (int)d.layers.size()) return d.canonical;
    std::string tok(1, op);
    if (op == '@') tok += std::to_string(clampi(arg, 0, 99));
    if (op == 'I' || op == 'M') tok += name;
    d.layers[li].tokens.push_back(tok);
    return parse(join(d, true)).canonical;
}

}  // namespace bsynth
