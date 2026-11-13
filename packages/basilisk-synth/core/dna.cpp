#include "dna.h"
#include <algorithm>
#include <cmath>
#include <cctype>
#include <cstdio>
#include <cstring>

namespace bsynth {

const char *const kSoundNames[kSoundCount] = {
    "chimes", "chord", "ding", "notify", "recycle", "ringin", "ringout", "start", "tada",
    "balloon", "batcrit", "batlow", "critstop", "default", "xpding", "error", "exclaim", "hwfail",
    "hwin", "hwout", "infobar", "logoff", "logon", "menu", "minimize", "xpnotify", "popup", "print",
    "xprecycle", "restore", "xpringin", "xpringout", "shutdown", "startup", "xpstart",
    "w31chimes", "w31chord", "w31ding", "w31ringin", "w31ringout", "w31tada",
    "wxpchimes", "wxpchord", "wxpding", "wxpringin", "wxpringout", "wxptada"};
const char *const kSoundFilesXP[kSoundCount] = {
    "chimes.wav", "chord.wav", "ding.wav", "notify.wav", "recycle.wav", "ringin.wav", "ringout.wav", "start.wav", "tada.wav",
    "Windows XP Balloon.wav", "Windows XP Battery Critical.wav", "Windows XP Battery Low.wav", "Windows XP Critical Stop.wav",
    "Windows XP Default.wav", "Windows XP Ding.wav", "Windows XP Error.wav", "Windows XP Exclamation.wav",
    "Windows XP Hardware Fail.wav", "Windows XP Hardware Insert.wav", "Windows XP Hardware Remove.wav",
    "Windows XP Information Bar.wav", "Windows XP Logoff Sound.wav", "Windows XP Logon Sound.wav",
    "Windows XP Menu Command.wav", "Windows XP Minimize.wav", "Windows XP Notify.wav", "Windows XP Pop-up Blocked.wav",
    "Windows XP Print complete.wav", "Windows XP Recycle.wav", "Windows XP Restore.wav", "Windows XP Ringin.wav",
    "Windows XP Ringout.wav", "Windows XP Shutdown.wav", "Windows XP Startup.wav", "Windows XP Start.wav",
    "W31\\CHIMES.WAV", "W31\\CHORD.WAV", "W31\\DING.WAV", "W31\\RINGIN.WAV", "W31\\RINGOUT.WAV", "W31\\TADA.WAV",
    "chimes.wav", "chord.wav", "ding.wav", "ringin.wav", "ringout.wav", "tada.wav"};
// Windows 3.11: its own six in C:\WINDOWS; XP's, converted to PCM SOUNDREC opens, in C:\XPSOUNDS as X<index>.WAV
const char *const kSoundFiles311[kSoundCount] = {
    "C:\\WINDOWS\\CHIMES.WAV", "C:\\WINDOWS\\CHORD.WAV", "C:\\WINDOWS\\DING.WAV", "C:\\XPSOUNDS\\X03.WAV",
    "C:\\XPSOUNDS\\X04.WAV", "C:\\WINDOWS\\RINGIN.WAV", "C:\\WINDOWS\\RINGOUT.WAV", "C:\\XPSOUNDS\\X07.WAV",
    "C:\\WINDOWS\\TADA.WAV", "C:\\XPSOUNDS\\X09.WAV", "C:\\XPSOUNDS\\X10.WAV", "C:\\XPSOUNDS\\X11.WAV",
    "C:\\XPSOUNDS\\X12.WAV", "C:\\XPSOUNDS\\X13.WAV", "C:\\XPSOUNDS\\X14.WAV", "C:\\XPSOUNDS\\X15.WAV",
    "C:\\XPSOUNDS\\X16.WAV", "C:\\XPSOUNDS\\X17.WAV", "C:\\XPSOUNDS\\X18.WAV", "C:\\XPSOUNDS\\X19.WAV",
    "C:\\XPSOUNDS\\X20.WAV", "C:\\XPSOUNDS\\X21.WAV", "C:\\XPSOUNDS\\X22.WAV", "C:\\XPSOUNDS\\X23.WAV",
    "C:\\XPSOUNDS\\X24.WAV", "C:\\XPSOUNDS\\X25.WAV", "C:\\XPSOUNDS\\X26.WAV", "C:\\XPSOUNDS\\X27.WAV",
    "C:\\XPSOUNDS\\X28.WAV", "C:\\XPSOUNDS\\X29.WAV", "C:\\XPSOUNDS\\X30.WAV", "C:\\XPSOUNDS\\X31.WAV",
    "C:\\XPSOUNDS\\X32.WAV", "C:\\XPSOUNDS\\X33.WAV", "C:\\XPSOUNDS\\X34.WAV",
    "C:\\WINDOWS\\CHIMES.WAV", "C:\\WINDOWS\\CHORD.WAV", "C:\\WINDOWS\\DING.WAV", "C:\\WINDOWS\\RINGIN.WAV",
    "C:\\WINDOWS\\RINGOUT.WAV", "C:\\WINDOWS\\TADA.WAV",
    "C:\\XPSOUNDS\\X00.WAV", "C:\\XPSOUNDS\\X01.WAV", "C:\\XPSOUNDS\\X02.WAV", "C:\\XPSOUNDS\\X05.WAV",
    "C:\\XPSOUNDS\\X06.WAV", "C:\\XPSOUNDS\\X08.WAV"};

static std::vector<std::string> g_library;
void setLibrary(const std::vector<std::string> &names) { g_library = names; }
bool inLibrary(const std::string &name) { for (auto &n : g_library) if (n == name) return true; return false; }

int soundIndex(const std::string &name)
{
    for (int i = 0; i < kSoundCount; i++) if (name == kSoundNames[i]) return i;
    return -1;
}

const char *soundFile311(int i) { return i >= 0 && i < kSoundCount ? kSoundFiles311[i] : kSoundFiles311[2]; }

int soundOrigin(const std::string &name)
{
    int i = soundIndex(name);
    if (i < 0) return inLibrary(name) ? kOriginLibrary : 0;
    if (i == 0 || i == 1 || i == 2 || i == 5 || i == 6 || i == 8) return kOriginNative;   // chimes chord ding ringin ringout tada
    if (i >= 35 && i <= 40) return kOrigin31;
    return kOriginXP;
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
    static bool namech(char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_'; }
    std::string name() { size_t b = p; while (p < s.size() && namech(s[p])) p++; return s.substr(b, p - b); }
    // the body of an unknown (later-version) token: lowercase subkeys, digits, '.', ',' and '~' (DNA.md 5.8);
    // in the globals 'm' always starts a macro, so it ends the token
    std::string later(bool global) {
        size_t b = p;
        while (p < s.size()) {
            char c = s[p];
            if ((c >= '0' && c <= '9') || c == '.' || c == ',' || c == '~' || (c >= 'a' && c <= 'z' && !(global && c == 'm'))) p++;
            else break;
        }
        return s.substr(b, p - b);
    }
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

// t,l.t,l... (DNA.md 5.1): times never decrease, at most 8 points
Env readEnv(Reader &r, int lo, int hi)
{
    Env e;
    for (;;) {
        if (!r.hasInt()) break;
        int t = clampi(r.integer(0), 0, 20000);
        int l = 0;
        if (r.peek() == ',') { r.p++; l = clampi(r.integer(0), lo, hi); }
        if (!e.empty() && t < e.back().first) t = e.back().first;
        if ((int)e.size() < kMaxEnvPoints && !(!e.empty() && e.back().first == t && e.back().second == l)) e.push_back({t, l});
        if (r.peek() == '.') { r.p++; continue; }
        break;
    }
    return e;
}

void parseLayer(Reader &r, Layer &L)
{
    std::string nm = r.name();
    L.source = soundIndex(nm);
    L.sourceName = nm;
    L.lib = L.source < 0 && inLibrary(nm);
    L.tokens.push_back(nm);
    while (!r.end() && r.peek() != '/' && r.peek() != ';') {
        char c = r.peek(); r.p++;
        switch (c) {
        case '+': case '-': case '>': case '<': case 'E': case 'R': case '[': case ']': case 'C': case 'P': case 'X':
            if ((int)L.steps.size() < kMaxSteps) { Step s; s.op = c; L.steps.push_back(s); L.tokens.push_back(std::string(1, c)); }
            break;
        case '@': {
            if (r.peek() == 't') {   // v2 @t<ms>
                r.p++;
                int ms = clampi(r.integer(0), 0, kMaxBufferMs);
                if ((int)L.steps.size() < kMaxSteps) { Step s; s.op = '@'; s.ms = ms; L.steps.push_back(s); L.tokens.push_back("@t" + num(ms)); }
                break;
            }
            int v = clampi(r.integer(0), 0, 99);
            if ((int)L.steps.size() < kMaxSteps) { Step s; s.op = '@'; s.arg = v; L.steps.push_back(s); L.tokens.push_back("@" + num(v)); }
            break; }
        case 'I': case 'M': {
            std::string n = r.name();
            int si = soundIndex(n);
            if ((si >= 0 || inLibrary(n)) && (int)L.steps.size() < kMaxSteps) {
                Step s; s.op = c; s.sound = si; s.name = n; L.steps.push_back(s); L.tokens.push_back(std::string(1, c) + n);
            }
            break; }
        case 'O': { int v = clampi(r.integer(0), 0, 4000); L.offset = v; L.tokens.push_back("O" + num(v)); break; }
        case 'Q': { int v = clampi(r.integer(0), -100, 100); L.pan = v; L.tokens.push_back("Q" + num(v)); break; }
        case 'J': {
            char w = r.peek();
            if (w != 'a' && w != 'p') break;
            r.p++;
            Env e = readEnv(r, w == 'a' ? 0 : -100, 100);
            if (w == 'a') L.envA = e; else L.envP = e;
            if (!e.empty()) L.tokens.push_back(std::string("J") + w + envText(e));
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
        default:
            // an unknown gene of a later version (an uppercase letter, then its lowercase subkeys, digits . , ~):
            // kept verbatim so saving does not lose it (forward compatibility); anything else is skipped
            if (c >= 'A' && c <= 'Z') L.tokens.push_back(std::string(1, c) + r.later(false));
            break;
        }
    }
}

void parseGlobals(Reader &r, Globals &g)
{
    while (!r.end()) {
        char c = r.peek(); r.p++;
        int *f = nullptr;
        if (c == 'm') {   // v2 macros: mK=V or mKLPlo,hi
            char kc = r.peek();
            // a macro token that this version cannot read is consumed whole and kept verbatim: its letters are
            // never read again as globals (`m11S50` must not set sustain)
            auto keep = [&](size_t from) {
                r.p = from;
                if (!r.end()) r.p++;                                          // K
                if (r.peek() == '=') r.p++;
                else {
                    if (isdigit((unsigned char)r.peek())) r.p++;              // L
                    if (isalpha((unsigned char)r.peek()) && r.peek() != 'm') r.p++;   // P
                }
                while (!r.end() && (isdigit((unsigned char)r.peek()) || strchr(",.~-", r.peek()))) r.p++;
                g.tokens.push_back("m" + r.s.substr(from, r.p - from));
            };
            size_t from = r.p;
            if (kc < '1' || kc > '4') { keep(from); continue; }
            r.p++;
            int k = kc - '0';
            if (r.peek() == '=') {
                r.p++;
                int v = clampi(r.integer(0), 0, 100);
                g.macro[k - 1] = v;
                g.tokens.push_back("m" + num(k) + "=" + num(v));
                continue;
            }
            char lc = r.peek();
            if (lc < '0' || lc > '8') { keep(from); continue; }
            r.p++;
            char pc = r.peek();
            if (!pc || !strchr("OQLTCZN", pc)) { keep(from); continue; }
            r.p++;
            int lo = r.integer(0), hi = lo;
            if (r.peek() == ',') { r.p++; hi = r.integer(lo); }
            auto lim = [&](int v) {
                switch (pc) {
                case 'O': return clampi(v, 0, 4000); case 'Q': return clampi(v, -100, 100); case 'L': return clampi(v, 0, 400);
                case 'T': return clampi(v, -48, 48); case 'C': return clampi(v, 0, 100); case 'Z': return clampi(v, 10, 1000);
                default: return clampi(v, 0, 8);
                }
            };
            MacroMap mm; mm.macro = k; mm.layer = lc - '0'; mm.param = pc; mm.lo = lim(lo); mm.hi = lim(hi);
            g.maps.push_back(mm);
            g.tokens.push_back("m" + num(k) + std::string(1, lc) + std::string(1, pc) + num(mm.lo) + "," + num(mm.hi));
            continue;
        }
        switch (c) {
        case 'A': f = &g.attack; break; case 'D': f = &g.decay; break; case 'S': f = &g.sustain; break;
        case 'R': f = &g.release; break; case 'B': f = &g.bendRange; break; case 'V': f = &g.velocity; break;
        case 'K': f = &g.root; break; case 'G': f = &g.gainDb; break;
        default:
            if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {      // a later version's global: kept verbatim
                std::string body = r.later(true);
                g.tokens.push_back(std::string(1, c) + body);
            }
            continue;
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
    // trailing empty layers say nothing ("a//" and "a/" are "a"): dropped, so canonical() is a fixed point
    auto emptyLayer = [](const Layer &L) { for (auto &t : L.tokens) if (!t.empty()) return false; return true; };
    while (!d.layers.empty() && emptyLayer(d.layers.back())) d.layers.pop_back();
    if (r.peek() == ';') { r.p++; parseGlobals(r, d.g); }
    assignPools(d);
    d.canonical = join(d, true);
    return d;
}

std::string canonical(const std::string &t) { return parse(t).canonical; }

int dnaOrigins(const Dna &d)
{
    int o = 0;
    for (auto &L : d.layers) {
        if (!L.sourceName.empty()) o |= soundOrigin(L.sourceName);
        for (auto &st : L.steps) if ((st.op == 'I' || st.op == 'M') && !st.name.empty()) o |= soundOrigin(st.name);
    }
    return o;
}

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
    case 'O': tok = "O" + std::to_string(clampi(v, 0, 4000)); break;
    case 'Q': tok = "Q" + std::to_string(clampi(v, -100, 100)); break;
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
    if (op == '@') tok += arg < 0 ? "t" + std::to_string(-arg) : std::to_string(clampi(arg, 0, 99));   // arg < 0: @t(-arg) ms
    if (op == 'I' || op == 'M') tok += name;
    d.layers[li].tokens.push_back(tok);
    return parse(join(d, true)).canonical;
}

std::string envText(const Env &e)
{
    if (e.empty()) return "-";
    std::string s;
    for (size_t i = 0; i < e.size(); i++) s += (i ? "." : "") + std::to_string(e[i].first) + "," + std::to_string(e[i].second);
    return s;
}

std::string setLayerEnv(const std::string &dna, int li, char which, const Env &env)
{
    Dna d = parse(dna);
    if (li < 0 || li >= (int)d.layers.size() || (which != 'a' && which != 'p')) return d.canonical;
    auto &T = d.layers[li].tokens;
    std::string head = std::string("J") + which;
    for (int i = (int)T.size() - 1; i >= 1; i--) if (T[i].compare(0, 2, head) == 0) T.erase(T.begin() + i);
    if (!env.empty()) T.push_back(head + envText(env));
    return parse(join(d, true)).canonical;
}

std::string setMacro(const std::string &dna, int k, int v)
{
    Dna d = parse(dna);
    if (k < 1 || k > kMacros) return d.canonical;
    std::string tok = "m" + std::to_string(k) + "=" + std::to_string(clampi(v, 0, 100)), pre = "m" + std::to_string(k) + "=";
    bool done = false;
    for (auto &t : d.g.tokens) if (t.compare(0, pre.size(), pre) == 0) { t = tok; done = true; }
    if (!done) d.g.tokens.push_back(tok);
    return parse(join(d, true)).canonical;
}

Dna applyMacros(const Dna &d0)
{
    Dna d = d0;
    if (d.g.maps.empty()) return d;
    for (size_t li = 0; li < d.layers.size(); li++) {
        Layer &L = d.layers[li];
        // per parameter: first mapping contributes lo + (hi - lo) v, later ones (hi - lo) v (DNA.md 5.3)
        const char params[] = "OQLTCZN";
        for (const char *pp = params; *pp; pp++) {
            bool any = false;
            double val = 0;
            for (auto &m : d.g.maps) {
                if (m.param != *pp || (m.layer != 0 && m.layer != (int)li + 1)) continue;
                double v = d.g.macro[m.macro - 1] / 100.0;
                val += (any ? 0 : m.lo) + (m.hi - m.lo) * v;
                any = true;
            }
            if (!any) continue;
            int iv = (int)std::lround(val);
            switch (*pp) {
            case 'O': L.offset = clampi(iv, 0, 4000); break;
            case 'Q': L.pan = clampi(iv, -100, 100); break;
            case 'L': L.level = clampi(iv, 0, 400); break;
            case 'T': L.transpose = clampi(iv, -48, 48); break;
            case 'C': L.spreadCents = clampi(iv, 0, 100); break;
            case 'Z': {
                double z = clampi(iv, 10, 1000) / 100.0;
                for (auto &p : L.envA) p.first = (int)std::lround(p.first * z);
                for (auto &p : L.envP) p.first = (int)std::lround(p.first * z);
                break; }
            case 'N': {
                if (L.steps.empty()) break;
                int n = clampi(iv, 0, 8);
                Step last = L.steps.back();
                std::string tok;   // the last step's token is the last step-ish token of the layer
                for (int i = (int)L.tokens.size() - 1; i >= 1; i--) {
                    char c = L.tokens[i][0];
                    if (strchr("+-><ER@[]CPXIM", c)) { tok = L.tokens[i]; L.tokens.erase(L.tokens.begin() + i); break; }
                }
                L.steps.pop_back();
                for (int k = 0; k < n && (int)L.steps.size() < kMaxSteps; k++) { L.steps.push_back(last); L.tokens.push_back(tok); }
                break; }
            }
        }
    }
    return d;
}

}  // namespace bsynth
