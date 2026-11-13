// Keys, scales and tunings. See scales.h and design/PRESET-ENGINE-2.md section 18.
#include "scales.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sstream>

namespace bsynth3 {

namespace {
struct Def { int id; const char *word, *category, *label; int n; double c[32]; int edo; };
// 12-TET scales in semitones x 100; maqam steps in cents (24-TET approximations); EDOs built by edo()
const Def kDefs[] = {
    {0, "major", "Western", "Major (Ionian)", 7, {0, 200, 400, 500, 700, 900, 1100}, 0},
    {1, "minor", "Western", "Minor (Aeolian)", 7, {0, 200, 300, 500, 700, 800, 1000}, 0},
    {2, "dorian", "Western", "Dorian", 7, {0, 200, 300, 500, 700, 900, 1000}, 0},
    {3, "phrygian", "Western", "Phrygian", 7, {0, 100, 300, 500, 700, 800, 1000}, 0},
    {4, "lydian", "Western", "Lydian", 7, {0, 200, 400, 600, 700, 900, 1100}, 0},
    {5, "mixolydian", "Western", "Mixolydian", 7, {0, 200, 400, 500, 700, 900, 1000}, 0},
    {6, "locrian", "Western", "Locrian", 7, {0, 100, 300, 500, 600, 800, 1000}, 0},
    {7, "harmonic-minor", "Western", "Harmonic minor", 7, {0, 200, 300, 500, 700, 800, 1100}, 0},
    {8, "major-pent", "Western", "Major pentatonic", 5, {0, 200, 400, 700, 900}, 0},
    {9, "minor-pent", "Western", "Minor pentatonic", 5, {0, 300, 500, 700, 1000}, 0},
    {10, "whole-tone", "Western", "Whole tone", 6, {0, 200, 400, 600, 800, 1000}, 0},
    {11, "blues", "Western", "Blues", 6, {0, 300, 500, 600, 700, 1000}, 0},
    {12, "chromatic", "Western", "Chromatic", 12, {0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100}, 0},
    {13, "melodic-minor", "Western", "Melodic minor", 7, {0, 200, 300, 500, 700, 900, 1100}, 0},
    {14, "hirajoshi", "Japanese", "Hirajoshi", 5, {0, 200, 300, 700, 800}, 0},
    {15, "in", "Japanese", "In (Miyako-bushi)", 5, {0, 100, 500, 700, 800}, 0},
    {16, "yo", "Japanese", "Yo", 5, {0, 200, 500, 700, 900}, 0},
    {17, "kumoi", "Japanese", "Kumoi", 5, {0, 200, 300, 700, 900}, 0},
    {18, "iwato", "Japanese", "Iwato", 5, {0, 100, 500, 600, 1000}, 0},
    {19, "bhairav", "Raga (pitch sets)", "Bhairav", 7, {0, 100, 400, 500, 700, 800, 1100}, 0},
    {20, "yaman", "Raga (pitch sets)", "Yaman", 7, {0, 200, 400, 600, 700, 900, 1100}, 0},
    {21, "kafi", "Raga (pitch sets)", "Kafi", 7, {0, 200, 300, 500, 700, 900, 1000}, 0},
    {22, "todi", "Raga (pitch sets)", "Todi", 7, {0, 100, 300, 600, 700, 800, 1100}, 0},
    {23, "bhairavi", "Raga (pitch sets)", "Bhairavi", 7, {0, 100, 300, 500, 700, 800, 1000}, 0},
    {24, "marwa", "Raga (pitch sets)", "Marwa", 7, {0, 100, 400, 600, 700, 900, 1100}, 0},
    {25, "purvi", "Raga (pitch sets)", "Purvi", 7, {0, 100, 400, 600, 700, 800, 1100}, 0},
    {26, "rast", "Maqam (24-TET)", "Maqam Rast", 7, {0, 200, 350, 500, 700, 900, 1050}, 0},
    {27, "bayati", "Maqam (24-TET)", "Maqam Bayati", 7, {0, 150, 300, 500, 700, 800, 1000}, 0},
    {28, "hijaz", "Maqam (24-TET)", "Maqam Hijaz", 7, {0, 100, 400, 500, 700, 800, 1000}, 0},
    {29, "saba", "Maqam (24-TET)", "Maqam Saba", 7, {0, 150, 300, 400, 700, 800, 1000}, 0},
    {30, "16tet", "Equal temperaments", "16-TET", 0, {0}, 16},
    {31, "19tet", "Equal temperaments", "19-TET", 0, {0}, 19},
    {32, "22tet", "Equal temperaments", "22-TET", 0, {0}, 22},
    {33, "24tet", "Equal temperaments", "24-TET (quarter tones)", 0, {0}, 24},
    {34, "31tet", "Equal temperaments", "31-TET", 0, {0}, 31},
    {35, "just-major", "Just intonation", "Just major (5-limit)", 7, {0}, -1},
    {36, "just-12", "Just intonation", "Just chromatic (5-limit)", 12, {0}, -2},
};
double rc(double num, double den) { return 1200.0 * std::log2(num / den); }
long floorDiv(long a, long b) { long q = a / b; if ((a % b != 0) && ((a < 0) != (b < 0))) q--; return q; }
}

bool Tuning::twelve() const { return tuningMask(*this) != 0; }

const std::vector<LibScale> &scaleLibrary()
{
    static std::vector<LibScale> v;
    if (v.empty()) for (auto &d : kDefs) v.push_back({d.id, d.word, d.category, d.label});
    return v;
}

Tuning edo(int n)
{
    Tuning t;
    t.name = std::to_string(n) + "-TET";
    t.steps.clear();
    for (int i = 0; i < n; i++) t.steps.push_back(1200.0 * i / n);
    return t;
}

bool libraryTuning(int id, Tuning &t)
{
    for (auto &d : kDefs) {
        if (d.id != id) continue;
        if (d.edo > 0) { t = edo(d.edo); t.name = d.label; return true; }
        t = Tuning();
        t.name = d.label;
        t.steps.clear();
        if (d.edo == -1) for (double r : {1.0, 9.0 / 8, 5.0 / 4, 4.0 / 3, 3.0 / 2, 5.0 / 3, 15.0 / 8}) t.steps.push_back(rc(r, 1));
        else if (d.edo == -2) for (double r : {1.0, 16.0 / 15, 9.0 / 8, 6.0 / 5, 5.0 / 4, 4.0 / 3, 45.0 / 32, 3.0 / 2, 8.0 / 5, 5.0 / 3, 9.0 / 5, 15.0 / 8}) t.steps.push_back(rc(r, 1));
        else for (int i = 0; i < d.n; i++) t.steps.push_back(d.c[i]);
        return true;
    }
    return false;
}

int libraryId(const std::string &w) { for (auto &d : kDefs) if (w == d.word) return d.id; return -1; }

Tuning maskTuning(unsigned mask, const std::string &name)
{
    Tuning t;
    t.name = name;
    t.steps.clear();
    mask |= 1;
    for (int k = 0; k < 12; k++) if (mask & (1u << k)) t.steps.push_back(100.0 * k);
    return t;
}

unsigned tuningMask(const Tuning &t)
{
    if (std::fabs(t.period - 1200) > 0.01) return 0;
    unsigned m = 0;
    for (double c : t.steps) {
        double s = c / 100;
        long k = std::lround(s);
        if (std::fabs(s - k) > 0.0001 || k < 0 || k > 11) return 0;
        m |= 1u << k;
    }
    return m;
}

static bool lines(const std::string &text, std::vector<std::string> &out)
{
    std::istringstream in(text);
    std::string l;
    while (std::getline(in, l)) {
        if (!l.empty() && l.back() == '\r') l.pop_back();
        if (!l.empty() && l[0] == '!') continue;
        out.push_back(l);
    }
    return true;
}
static bool pitchValue(const std::string &raw, double &cents)
{
    std::istringstream in(raw);
    std::string w;
    if (!(in >> w)) return false;
    if (w.find('.') != std::string::npos) { char *e; cents = std::strtod(w.c_str(), &e); return *e == 0; }
    size_t sl = w.find('/');
    char *e1, *e2;
    double a = std::strtod(w.c_str(), &e1), b = 1;
    if (sl != std::string::npos) { if (e1 != w.c_str() + sl) return false; b = std::strtod(w.c_str() + sl + 1, &e2); if (*e2) return false; }
    else if (*e1) return false;
    if (a <= 0 || b <= 0) return false;
    cents = rc(a, b);
    return true;
}

bool parseScl(const std::string &text, Tuning &t, std::string *err)
{
    std::vector<std::string> L;
    lines(text, L);
    auto fail = [&](const std::string &m) { if (err) *err = m; return false; };
    if (L.size() < 2) return fail("a .scl file needs a description line and a count");
    long n = std::strtol(L[1].c_str(), nullptr, 10);
    if (n < 1 || n > 128 || (long)L.size() < 2 + n) return fail("the count of pitches is missing or wrong");
    std::vector<double> v;
    for (long i = 0; i < n; i++) {
        double c;
        if (!pitchValue(L[2 + i], c)) return fail("pitch line " + std::to_string(i + 1) + " is not cents (with a '.') or a ratio");
        v.push_back(c);
    }
    Tuning r;
    r.name = L[0];
    while (!r.name.empty() && r.name[0] == ' ') r.name.erase(0, 1);
    r.period = v.back();
    if (r.period <= 0) return fail("the last pitch (the period) must be above the root");
    r.steps.assign(1, 0.0);
    for (long i = 0; i + 1 < n; i++) if (v[i] > 0 && v[i] < r.period) r.steps.push_back(v[i]);
    std::sort(r.steps.begin(), r.steps.end());
    r.steps.erase(std::unique(r.steps.begin(), r.steps.end(), [](double a, double b) { return std::fabs(a - b) < 1e-6; }), r.steps.end());
    t = r;
    return true;
}

bool parseKbm(const std::string &text, Tuning &t, std::string *err)
{
    std::vector<std::string> L;
    lines(text, L);
    auto fail = [&](const std::string &m) { if (err) *err = m; return false; };
    if (L.size() < 7) return fail("a .kbm file needs 7 header lines");
    long size = std::strtol(L[0].c_str(), nullptr, 10), middle = std::strtol(L[3].c_str(), nullptr, 10);
    double hz = std::strtod(L[5].c_str(), nullptr);
    // only linear maps (size 0, or the identity): consecutive keys -> consecutive steps (section 18.4)
    for (long i = 0; i < size && 7 + i < (long)L.size(); i++) {
        std::string m = L[7 + i];
        if (std::strtol(m.c_str(), nullptr, 10) != i) return fail("only linear keyboard maps are supported (the remap walks every step)");
    }
    if (middle < 0 || middle > 127 || hz <= 0) return fail("the middle note or the reference frequency is out of range");
    t.refNote = (int)middle;
    t.refHz = hz;
    return true;
}

std::string tuningText(const Tuning &t)
{
    std::string n = t.name;
    for (auto &c : n) if (c == ';' || c < 0x20 || c > 0x7E) c = ' ';
    std::string o = "t1;" + n + ";";
    char b[40];
    auto num = [&](double v) { std::snprintf(b, sizeof b, "%.3f", v); std::string s = b; while (s.back() == '0') s.pop_back(); if (s.back() == '.') s.pop_back(); return s; };
    o += num(t.period) + ";";
    for (size_t i = 0; i < t.steps.size(); i++) o += (i ? "," : "") + num(t.steps[i]);
    o += ";" + std::to_string(t.refNote) + ";" + num(t.refHz);
    return o;
}

bool tuningFromText(const std::string &s, Tuning &t)
{
    std::vector<std::string> f;
    size_t b = 0;
    while (b <= s.size()) { size_t e = s.find(';', b); if (e == std::string::npos) e = s.size(); f.push_back(s.substr(b, e - b)); b = e + 1; }
    if (f.size() != 6 || f[0] != "t1") return false;
    Tuning r;
    r.name = f[1];
    r.period = std::strtod(f[2].c_str(), nullptr);
    r.steps.clear();
    size_t p = 0;
    while (p <= f[3].size()) { size_t e = f[3].find(',', p); if (e == std::string::npos) e = f[3].size(); r.steps.push_back(std::strtod(f[3].substr(p, e - p).c_str(), nullptr)); p = e + 1; }
    r.refNote = std::atoi(f[4].c_str());
    r.refHz = std::strtod(f[5].c_str(), nullptr);
    if (r.period <= 0 || r.steps.empty() || r.steps[0] != 0) return false;
    t = r;
    return true;
}

Key::Key() { libraryTuning(0, tuning); }

// the absolute cents of tuning step s (s counted from the root of the octave/period that base is in)
static double stepCents(const Key &k, double base, long s)
{
    long N = k.tuning.size();
    long o = floorDiv(s, N);
    return base + o * k.tuning.period + k.tuning.steps[(size_t)(s - o * N)];
}
static double keyBase(const Key &k)
{
    if (k.remap) return 1200.0 * floorDiv(k.anchor, 12) + 100.0 * k.root;   // the root in the anchor's octave
    return 100.0 * k.root;                                                     // C-1 + root: step 0
}

Played playKey(const Key &k, int note, int snap)
{
    Played r{100.0 * note, 0, true};
    long N = k.tuning.size();
    double base = keyBase(k);
    if (k.remap) {
        r.step = note - k.anchor;
        r.cents = stepCents(k, base, r.step);
        return r;
    }
    double x = 100.0 * note - base;
    long o = (long)std::floor(x / k.tuning.period);
    double w = x - o * k.tuning.period;
    long dn = 0;
    for (long i = 0; i < N; i++) if (k.tuning.steps[(size_t)i] <= w + 0.5) dn = i;   // the step at or below (0.5 cent tolerance)
    double dDown = w - k.tuning.steps[(size_t)dn];
    if (std::fabs(dDown) <= 0.5) { r.step = o * N + dn; return r; }      // in the scale: the note plays as itself
    double upC = dn + 1 < N ? k.tuning.steps[(size_t)dn + 1] : k.tuning.period;
    double dUp = upC - w;
    r.inScale = false;
    long down = o * N + dn, up = down + 1;
    switch (snap == SnapDefault ? k.snap : snap) {
    case SnapDown: r.step = down; r.cents = stepCents(k, base, down); break;
    case SnapUp: r.step = up; r.cents = stepCents(k, base, up); break;
    case SnapOff: r.step = down; break;   // chromatic: the note itself; the chord takes the shape of the step below
    default: r.step = dUp < dDown ? up : down; r.cents = stepCents(k, base, r.step); break;   // nearest, a tie goes down
    }
    return r;
}

std::vector<double> degreeVoices(const Key &k, const Degrees &d, int note, int snapDefault)
{
    int snap = d.snap ? d.snap : snapDefault;
    Played p = playKey(k, note, snap);
    double base = keyBase(k);
    double shift = p.cents - stepCents(k, base, p.step);   // 0, or the chromatic offset of a passed-through note
    std::vector<double> v;
    for (int g : d.up) v.push_back(stepCents(k, base, p.step + (g - 1)) + shift);
    for (int g : d.down) v.push_back(stepCents(k, base, p.step - (g - 1)) + shift);
    if (v.empty()) v.push_back(p.cents);
    std::sort(v.begin(), v.end());
    for (int i = 0; i < d.inversion && !v.empty(); i++) { v.front() += k.tuning.period; std::sort(v.begin(), v.end()); }
    return v;
}

std::vector<double> voiceOffsets(const Key &k, const Degrees &d, int note, int snapDefault)
{
    std::vector<double> v = degreeVoices(k, d, note, snapDefault);
    for (auto &c : v) c -= 100.0 * note;
    return v;
}

std::string stepLabel(const Key &k, long step, int mode)
{
    long N = k.tuning.size();
    long o = floorDiv(step, N), i = step - o * N;
    double c = k.tuning.steps[(size_t)i];
    bool tw = k.tuning.twelve();
    static const char *sargam[12] = {"Sa", "re", "Re", "ga", "Ga", "ma", "Ma'", "Pa", "dha", "Dha", "ni", "Ni"};
    static const char *names[12] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    switch (mode) {
    case 1: return std::to_string(i + 1);
    case 2: if (tw) return sargam[std::lround(c / 100) % 12]; break;
    case 3: if (tw) return names[(k.root + std::lround(c / 100)) % 12]; break;
    case 4: break;
    default: return "";
    }
    return std::to_string(std::lround(c));   // cents: for non-12 tunings every label mode falls back to cents
}

}  // namespace bsynth3
