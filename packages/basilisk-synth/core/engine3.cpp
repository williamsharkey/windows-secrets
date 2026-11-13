// DNA v3 host-side logic. See engine3.h and design/PRESET-ENGINE-2.md.
#include "engine3.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <sstream>

namespace bsynth3 {

static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

uint32_t voiceSeed(const Human &y, int note, int rec, uint32_t noteCounter, uint32_t salt)
{
    uint32_t h = 2166136261u ^ salt;
    auto mix = [&](uint32_t v) { for (int i = 0; i < 4; i++) { h ^= (v >> (8 * i)) & 0xFF; h *= 16777619u; } };
    if (y.perKey || y.perRec) {
        if (y.perKey) mix(0x100u + (uint32_t)note);
        if (y.perRec) mix(0x200u + (uint32_t)rec);
    } else mix(noteCounter);
    return h ? h : 1;
}

// ---------------------------------------------------------------- 1. the playback window
Span window(const Window &w, uint32_t frames, int rate, int vel, Rng &rng, int minMs)
{
    Span sp;
    if (!frames) return sp;
    int s = rng.in(w.s.lo, w.s.hi);
    if (w.vel) s = (int)((long long)s * (kOne - (long long)w.vel * clampi(vel, 0, 127) / 127) / kOne);
    int e = rng.in(w.e.lo, w.e.hi);
    if (w.l.lo >= 0) e = std::min(e, s + rng.in(w.l.lo, w.l.hi));
    e = clampi(e, 0, kOne);
    uint64_t from = (uint64_t)s * frames / kOne, to = (uint64_t)e * frames / kOne;
    uint64_t minF = rate > 0 ? (uint64_t)minMs * (uint64_t)rate / 1000 : 1;
    if (minF > frames) minF = frames;
    if (to < from + minF) to = from + minF;
    if (to > frames) { to = frames; from = to - minF; }
    sp.from = (uint32_t)from; sp.to = (uint32_t)to;
    return sp;
}

std::string bakeSteps(const Window &w, uint32_t frames, int rate)
{
    if (w.s.random() || w.e.random() || w.l.random() || w.vel || !rate || !frames) return "";
    int s = w.s.lo, e = w.e.lo;
    if (w.l.lo >= 0) e = std::min(e, s + w.l.lo);
    long long total = (long long)frames * 1000 / rate;
    long long eMs = (long long)e * total / kOne;
    std::string t;
    if (eMs < total) t += "@t" + std::to_string(eMs) + "]";   // the end first: the start position stays valid
    // after the delete the buffer is eMs long, and the start is still s of the ORIGINAL length
    long long sMs = (long long)s * total / kOne;
    if (sMs > 0 && sMs < eMs) t += "@t" + std::to_string(sMs) + "[";
    return t;
}

// ---------------------------------------------------------------- 2. mono, legato, continue
int MonoPlan::pick() const
{
    if (held_.empty()) return -1;
    if (m_.prio == 'h') return *std::max_element(held_.begin(), held_.end());
    if (m_.prio == 'l') return *std::min_element(held_.begin(), held_.end());
    return held_.back();
}

// the layer moves from cur_ to n (both held-note transitions use this)
void MonoPlan::moveTo(int n, bool alive, std::vector<Action> &a)
{
    switch (m_.mode) {
    case 'm':   // mono: a new attack from the window start; with glide it starts at the old pitch and slides
        if (alive) a.push_back({Action::Cut, cur_});
        if (m_.glideMs && cur_ >= 0) { a.push_back({Action::On, cur_}); a.push_back({Action::Rate, n, m_.glideMs}); }
        else a.push_back({Action::On, n});
        break;
    case 'l':   // legato (only called while notes overlap): keep the position, glide, no new attack
    case 'c':   // continue: never restart while the recorder still sounds
        if (alive) a.push_back({Action::Rate, n, m_.glideMs, !gated_});
        else { a.push_back({Action::On, n}); }
        break;
    default: a.push_back({Action::On, n}); break;
    }
}

std::vector<Action> MonoPlan::keyDown(int note, double t, double soundingUntil)
{
    std::vector<Action> a;
    held_.erase(std::remove(held_.begin(), held_.end(), note), held_.end());   // a repeated note-on: once
    bool wasHeld = !held_.empty();
    held_.push_back(note);
    int n = pick();
    if (n == cur_ && gated_ && note != n) return a;     // the priority keeps the sounding note
    bool alive = cur_ >= 0 && t < soundingUntil;        // the recorder still plays (held or releasing)
    if (m_.mode == 'l' && !wasHeld) {                    // legato, detached: a new attack
        if (alive) a.push_back({Action::Cut, cur_});
        a.push_back({Action::On, n});
    } else if (m_.mode == 'p') {
        a.push_back({Action::On, n});
    } else moveTo(n, alive, a);
    cur_ = n;
    gated_ = true;
    return a;
}

std::vector<Action> MonoPlan::keyUp(int note, double t, double soundingUntil)
{
    std::vector<Action> a;
    auto it = std::find(held_.begin(), held_.end(), note);
    if (it == held_.end()) return a;
    held_.erase(it);
    if (held_.empty()) {
        if (cur_ >= 0 && gated_) a.push_back({Action::Off, cur_});
        gated_ = false;
        return a;
    }
    int n = pick();
    if (n == cur_) return a;
    if (m_.mode == 'p') return a;
    moveTo(n, t < soundingUntil, a);   // back to a note still held (legato and continue glide; mono re-attacks)
    cur_ = n;
    return a;
}

// ---------------------------------------------------------------- 3. stacking and humanize
std::vector<int> noteIntervals(const Stack &s, const std::vector<int> &H, uint32_t counter, Rng &rng)
{
    std::vector<int> out;
    std::vector<int> h = H.empty() ? std::vector<int>{0} : H;
    if (s.roundRobin) return {h[counter % h.size()]};
    if (s.randomPick) return {h[(size_t)rng.in(0, (int)h.size() - 1)]};
    return h;
}

int unisonPan(const Stack &s, int u, int n)
{
    if (n <= 1 || !s.width) return 0;
    double f = -1.0 + 2.0 * u / (n - 1);                   // -1 .. 1
    return (int)std::lround(f * s.width * 100.0 / kOne);
}

int groupPick(const std::vector<int> &groupLayers, bool random, uint32_t counter, Rng &rng)
{
    if (groupLayers.empty()) return -1;
    if (random) return groupLayers[(size_t)rng.in(0, (int)groupLayers.size() - 1)];
    return groupLayers[counter % groupLayers.size()];
}

HumanDraw humanize(const Human &y, Rng &rng)
{
    HumanDraw d;
    d.cents = y.detune ? rng.in(-y.detune, y.detune) : 0;
    d.levelPct = 100 - (y.level ? rng.in(0, y.level) : 0);
    d.lateMs = y.timeMs ? rng.in(0, y.timeMs) : 0;
    d.pan = y.pan ? rng.in(-y.pan, y.pan) : 0;
    return d;
}

// ---------------------------------------------------------------- 4. rate modulation
double modCents(const Mod &m, double tMs, double phase)
{
    const double tau = 6.283185307179586;
    double c = 0;
    if (m.wowCents) c += m.wowCents * std::sin(tau * (phase + tMs / 1000.0 * m.wowDeciHz / 10.0));
    if (m.fluCents) c += m.fluCents * std::sin(tau * (phase * 7.0 + tMs / 1000.0 * m.fluHz));
    if (m.scoopCents && tMs < m.scoopMs) c -= m.scoopCents * (1.0 - tMs / m.scoopMs);
    return c;
}

std::vector<RateStep> xpStaircase(const Mod &m, int durMs, double phase, int stepMs, int qCents)
{
    Mod nf = m;
    nf.fluCents = 0;                       // flutter: unison on XP, not swaps
    std::vector<RateStep> out;
    int last = 1 << 30;
    for (int t = 0; t < durMs; t += stepMs) {
        int c = (int)std::lround(modCents(nf, t, phase) / qCents) * qCents;
        if (c != last) { out.push_back({t, c}); last = c; }
    }
    return out;
}

// ---------------------------------------------------------------- 6. the mine grid
bool Grid::parse(const std::string &line)
{
    std::istringstream in(line);
    std::string word, st, c;
    int W = 0, H = 0;
    if (!(in >> word >> W >> H >> st >> c) || word != "grid") return false;
    if (W < 1 || H < 1 || W > 30 || H > 24 || (int)c.size() != W * H || st.size() != 1) return false;
    for (char ch : c) if (!std::strchr(".012345678F?*Xx", ch)) return false;
    w = W; h = H; state = st[0]; cells = c;
    return true;
}

std::vector<StepNote> stepNotes(const Grid &g, int col, const Seq &x, int scale, int rootPc, const std::vector<int> &held, int K)
{
    std::vector<StepNote> out;
    int len = x.len > 0 ? std::min(x.len, g.w) : g.w;
    if (col < 0 || col >= len) return out;
    int base = held.empty() ? K : held.front();
    if (rootPc >= 0) base -= ((base - rootPc) % 12 + 12) % 12;
    int sc = scale < 0 || scale >= kScaleCount ? 0 : scale;
    int lanes = kScales[sc].n * x.octaves;
    bool octUp = false, mute = false;
    for (int r = 0; r < g.h; r++) {
        char c = g.at(col, r);
        if (c == '*' || c == 'X') octUp = true;
        if (c == 'x') mute = true;
    }
    if (mute) return out;
    for (int r = 0; r < g.h; r++) {
        char c = g.at(col, r);
        bool num = c >= '1' && c <= '8', flag = c == 'F';
        if (!num && !flag) continue;
        int n = num ? c - '0' : 0;
        int note = -1, vel = flag ? 127 : std::min(127, 40 + n * 11);
        int band = r * x.octaves / g.h;   // count/arp: the row picks one of xo octave bands, bottom = lowest
        switch (x.kind) {
        case 0: note = base + degreeToSemis(sc, r % lanes); break;
        case 1: note = base + degreeToSemis(sc, flag ? 0 : n - 1) + 12 * band; break;
        case 2:
            if (held.empty()) break;
            {
                int k = flag ? 0 : n - 1;
                note = held[(size_t)k % held.size()] + 12 * (int)(k / held.size()) + 12 * band;
            }
            break;
        }
        if (note < 0) continue;
        if (octUp) note += 12;
        int steps = 1;
        for (int c2 = col + 1; c2 < len && g.at(c2, r) == '?'; c2++) steps++;   // '?' ties the note on
        out.push_back({clampi(note, 0, 127), vel, steps});
    }
    // too many notes in one column: keep the accents, then the loudest, then the lowest
    std::stable_sort(out.begin(), out.end(), [](const StepNote &a, const StepNote &b) { return a.vel != b.vel ? a.vel > b.vel : a.note < b.note; });
    // no note twice (keep the louder / longer one), then the poly limit
    std::vector<StepNote> uniq;
    for (auto &s : out) if (std::none_of(uniq.begin(), uniq.end(), [&](const StepNote &u) { return u.note == s.note; })) uniq.push_back(s);
    if ((int)uniq.size() > x.poly) uniq.resize((size_t)x.poly);
    std::sort(uniq.begin(), uniq.end(), [](const StepNote &a, const StepNote &b) { return a.note < b.note; });
    return uniq;
}

// The ppq (quarter notes) of step k: k step lengths, odd steps delayed by swing % of a step.
double stepPpq(const Seq &x, long k)
{
    double step = 4.0 / x.div * (x.triplet ? 2.0 / 3.0 : 1.0);
    return k * step + ((k & 1) ? step * x.swing / 100.0 : 0.0);
}

// ---------------------------------------------------------------- 15. kit mode
int pickPad(const std::vector<Pad> &pads, int note, int vel, uint32_t counter, Rng &rng)
{
    std::vector<int> m;
    bool rnd = false;
    for (size_t i = 0; i < pads.size(); i++) {
        const Pad &p = pads[i];
        if (note >= p.lo && note <= p.hi && vel >= p.velLo && vel <= p.velHi) { m.push_back((int)i); rnd = rnd || p.random; }
    }
    if (m.empty()) return -1;
    return rnd ? m[(size_t)rng.in(0, (int)m.size() - 1)] : m[counter % m.size()];
}

double padCents(const Pad &p, int note)
{
    int root = p.root >= 0 ? p.root : p.lo;
    double semis = (note - root) * p.pitchPct / 100.0;
    if (p.rangeSemis) semis = std::max(-(double)p.rangeSemis, std::min((double)p.rangeSemis, semis));
    return semis * 100.0 + p.tuneCents;
}

double padGain(const Pad &p, int vel, int globalV)
{
    double v = clampi(vel, 0, 127) / 127.0, c;
    switch (p.curve) {
    case 1: c = std::sqrt(v); break;          // soft: quiet hits come up
    case 2: c = v * v; break;                 // hard: needs a firm hit
    case 3: c = 1; break;                     // fixed
    default: c = v;
    }
    double amt = (p.velAmount >= 0 ? p.velAmount : clampi(globalV, 0, 100)) / 100.0;
    return (1 - amt + amt * c) * p.level / 100.0;
}

std::vector<int> chokeTargets(const std::vector<Pad> &pads, int i)
{
    std::vector<int> out;
    if (i < 0 || i >= (int)pads.size()) return out;
    const Pad &me = pads[(size_t)i];
    for (size_t k = 0; k < pads.size(); k++) {
        const Pad &o = pads[k];
        bool hit = me.cut && o.cut == me.cut;
        for (int g : me.mutes) hit = hit || (o.cut == g && (int)k != i);
        if (hit) out.push_back((int)k);
    }
    return out;
}

Span padWindow(const Pad &p, const std::vector<uint32_t> &segStarts, uint32_t frames, int rate, Rng &rng)
{
    uint32_t a = 0, b = frames;
    if (p.seg > 0 && (size_t)p.seg <= segStarts.size()) {
        a = segStarts[(size_t)p.seg - 1];
        b = (size_t)p.seg < segStarts.size() ? segStarts[(size_t)p.seg] : frames;
        if (b > frames) b = frames;
        if (a >= b) return Span{0, 0};
    }
    Window w; w.s = p.s; w.e = p.e;
    Span s = window(w, b - a, rate, 127, rng, 10);
    s.from += a; s.to += a;
    return s;
}

// ---------------------------------------------------------------- the v3 wire
std::vector<std::string> parseHi3(const std::string &line, std::string *edition)
{
    std::istringstream in(line);
    std::string hi, v, ed, state, caps;
    std::vector<std::string> out;
    if (!(in >> hi >> v >> ed >> state) || hi != "hi" || v != "3") return out;
    if (edition) *edition = ed;
    in >> caps;
    size_t b = 0;
    while (b < caps.size()) {
        size_t e = caps.find(',', b);
        if (e == std::string::npos) e = caps.size();
        if (e > b) out.push_back(caps.substr(b, e - b));
        b = e + 1;
    }
    if (out.empty()) out.push_back("");   // a v3 guest with no optional features
    return out;
}
bool hasCap(const std::vector<std::string> &caps, const std::string &c) { return std::find(caps.begin(), caps.end(), c) != caps.end(); }

std::string onLine(int rec, int rate, int vol, int pan, int delayMs, int layer, Span w)
{
    char b[128];
    std::snprintf(b, sizeof b, "on %d %d %d %d %d %d %u %u", rec, rate, vol, pan, delayMs, layer, w.from, w.to);
    return b;
}
std::string rateLine(int rec, int hz, int glideMs, bool regate)
{
    char b[64];
    std::snprintf(b, sizeof b, "rate %d %d %d %d", rec, hz, glideMs, regate ? 1 : 0);
    return b;
}
std::string lmodLine(int layer, const Mod &m)
{
    char b[96];
    std::snprintf(b, sizeof b, "lmod %d %d %d %d %d %d %d", layer, m.wowCents, m.wowDeciHz, m.fluCents, m.fluHz, m.scoopCents, m.scoopMs);
    return b;
}
std::string lgrainLine(int layer, const Grain &g)
{
    std::string f;
    if (g.back) f += 'b';
    if (g.freeze) f += 'f';
    if (g.sync) f += 'y';
    if (f.empty()) f = "-";
    char b[160];
    std::snprintf(b, sizeof b, "lgrain %d %d %d %d %d %d %d %d %d %d %s %d %d", layer, g.pos, g.spray, g.sizeMs, g.sizeHiMs,
                  g.density, g.cents, g.octPct, g.shape, g.scan, f.c_str(), g.streams, g.width);
    return b;
}

}  // namespace bsynth3
