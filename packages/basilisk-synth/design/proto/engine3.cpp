// PRESET ENGINE 2 prototype: host-side logic of the v3 PROPOSAL. See engine3.h.
#include "engine3.h"
#include <algorithm>
#include <cstdio>
#include <sstream>

namespace bsynth3 {

static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

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
    long long sMs = (long long)s * total / kOne, eMs = (long long)e * total / kOne;
    std::string t;
    if (eMs < total) t += "@t" + std::to_string(eMs) + "]";   // the end first: the start position stays valid
    if (sMs > 0) t += "@t" + std::to_string(sMs) + "[";
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

std::vector<Action> MonoPlan::keyDown(int note, double t, double soundingUntil)
{
    std::vector<Action> a;
    bool wasHeld = !held_.empty();
    held_.push_back(note);
    int n = pick();
    if (n == cur_ && gated_) return a;                  // the priority keeps the sounding note
    bool alive = cur_ >= 0 && t < soundingUntil;       // the recorder still plays (held or releasing)
    switch (m_.mode) {
    case 'm':
        if (alive) a.push_back({Action::Cut, cur_});
        if (m_.glideMs && cur_ >= 0) { a.push_back({Action::On, cur_}); a.push_back({Action::Rate, n, m_.glideMs}); }
        else a.push_back({Action::On, n});
        break;
    case 'l':   // overlapped: glide, keep the position, no new attack. Not overlapped: a new note.
        if (wasHeld && alive) a.push_back({Action::Rate, n, m_.glideMs});
        else { if (alive) a.push_back({Action::Cut, cur_}); a.push_back({Action::On, n}); }
        break;
    case 'c':   // continue: never restart while the recorder still sounds, even in its release
        if (alive) a.push_back({Action::Rate, n, m_.glideMs, !gated_});
        else a.push_back({Action::On, n});
        break;
    default: a.push_back({Action::On, n}); break;
    }
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
    bool alive = t < soundingUntil;
    if (m_.mode == 'm') { if (alive) a.push_back({Action::Cut, cur_}); a.push_back({Action::On, n}); }
    else if (alive) a.push_back({Action::Rate, n, m_.glideMs});
    else a.push_back({Action::On, n});
    cur_ = n;
    return a;
}

// ---------------------------------------------------------------- 6. the mine grid
bool Grid::parse(const std::string &line)
{
    std::istringstream in(line);
    std::string word, st, c;
    int W = 0, H = 0;
    if (!(in >> word >> W >> H >> st >> c) || word != "grid") return false;
    if (W < 1 || H < 1 || W > 30 || H > 24 || (int)c.size() != W * H || st.size() != 1) return false;
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
    int perOct = scale == 12 ? 12 : kScales[scale < 0 || scale >= kScaleCount ? 0 : scale].n;
    int lanes = perOct * x.octaves;
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
        int band = r * x.octaves / g.h;   // count/arp: the row picks the octave
        switch (x.kind) {
        case 0: note = base + degreeToSemis(scale, r % lanes); break;
        case 1: note = base + degreeToSemis(scale, flag ? 0 : n - 1) + 12 * band; break;
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
    if ((int)out.size() > x.poly) out.resize((size_t)x.poly);
    // and no note twice
    std::sort(out.begin(), out.end(), [](const StepNote &a, const StepNote &b) { return a.note < b.note; });
    out.erase(std::unique(out.begin(), out.end(), [](const StepNote &a, const StepNote &b) { return a.note == b.note; }), out.end());
    return out;
}

}  // namespace bsynth3
