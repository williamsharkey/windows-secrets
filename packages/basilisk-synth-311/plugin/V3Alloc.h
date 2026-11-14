// BASILISK 16: the DNA v3 voice allocator (design/PRESET-ENGINE-2.md section 5), shared by the plugin and render311.
// It plays the layers that have a v3 voice token (N voice mode, S stacking, D degree harmony); core's Voices plays
// the others (the caller gives core a pool of 0 recorders for the layers this one owns). It also follows every
// sounding recorder (its own and core's) for live pitch bend: a bend sends `rate` lines to what sounds.
//   - N: poly with a limit (Np<n>), mono (Nm), legato (Nl), continue (Nc), glide (Ng), note priority (Nk)
//   - S: round-robin and random intervals (Sr Sx), random recorder (Sp), layer groups (Sg), strum (Ss), width (Sw)
//   - D: degree chords in the key (scales.h; the key is the plugin's, C major until the Key parameters exist)
// Times are DAC samples (48 kHz). The caller turns each Out into lines: an On goes through b16v3::note() (window,
// humanize, delays) like core's; a Rate becomes `rate <rec> <hz> <glide> <regate>` stamped at `at`.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
#include "../../basilisk-synth/core/dna.h"
#include "../../basilisk-synth/core/dna3.h"
#include "../../basilisk-synth/core/engine3.h"
#include "../../basilisk-synth/core/scales.h"
#include "../../basilisk-synth/core/voices.h"

namespace b16v3 {

struct Out {
    enum Kind { Cmd, Rate } kind = Cmd;
    bsynth::Cmd c{bsynth::Cmd::On, 0, 0, 0, 0};   // Cmd: an On (delayMs = O plus strum), Off or Cut
    int rec = 0; uint32_t hz = 0; int glideMs = 0; bool regate = false;   // Rate
    uint64_t at = 0;                                                       // Rate: its stamp
};

class V3Alloc {
public:
    // eff: the macro-applied v2 DNA (as core gets it); d3: its v3 tokens. Keeps the layers' info when only genes
    // change (as core does); the caller re-sends setLayerInfo after a rebuild.
    void setDna(const bsynth::Dna &eff, const bsynth3::Dna3 &d3)
    {
        const int n = std::min<int>((int)eff.layers.size(), bsynth::kMaxLayers);
        nlay_ = n;
        root_ = eff.g.root; velocity_ = eff.g.velocity; bendRange_ = eff.g.bendRange;
        for (int i = 0; i < bsynth::kMaxLayers; i++) {
            Lay &L = lay_[i];
            const bool had = L.own;
            L = Lay{};
            L.info = infoKeep_[i];
            if (i >= n) continue;
            const bsynth::Layer &v = eff.layers[i];
            L.valid = v.valid(); L.fixed = v.fixed; L.T = v.transpose; L.U = std::max(1, v.unison); L.C = v.spreadCents;
            L.level = v.level; L.pan = v.pan; L.offset = v.offset; L.H = v.harmony.empty() ? std::vector<int>{0} : v.harmony;
            if (i < (int)d3.layers.size()) {
                const bsynth3::Layer3 &x = d3.layers[i];
                L.own = x.has[1] || x.has[2] || x.has[7];
                L.n = x.n; L.s = x.s; L.d = x.d; L.hasD = x.has[7]; L.tempo = x.has[0] && x.w.tempo;
            }
            L.mono = L.own && L.n.mode != 'p';
            L.plan = bsynth3::MonoPlan(L.n);
            (void)had;
        }
        for (int r = 0; r < bsynth::kRecorders; r++) if (rec_[r].layer >= 0 && (rec_[r].layer >= n || !lay_[rec_[r].layer].own)) rec_[r].layer = -1;
    }
    void setLayerInfo(int i, int first, int count, int rate, int frames)
    {
        if (i < 0 || i >= bsynth::kMaxLayers) return;
        bsynth::LayerInfo in; in.first = first; in.count = count; in.rate = rate; in.frames = frames; in.known = true;
        infoKeep_[i] = in; lay_[i].info = in;
    }
    // A layer is ours when it has N, S or D, or when the key maps every note (remap, or a tuning that is not 12-TET:
    // section 18.4); core plays the rest chromatically, as always.
    bool owns(int i) const { return i >= 0 && i < nlay_ && lay_[i].valid && (lay_[i].own || (keyMap_ && !lay_[i].fixed)); }
    void setBpm(double bpm) { bpm_ = bpm > 1 ? bpm : 120; }
    void setKey(const bsynth3::Key &k) { key_ = k; keyMap_ = k.remap || !k.tuning.twelve(); }
    bool keyMaps() const { return keyMap_; }

    // ---- notes
    void noteOn(int note, int vel, uint64_t t, std::vector<Out> &out)
    {
        counter_++;
        groupsDone_.clear();
        for (int li = 0; li < nlay_; li++) {
            Lay &L = lay_[li];
            if (!owns(li) || !L.info.known || L.info.count <= 0) continue;
            if (L.s.group && !groupTurn(li)) continue;
            if (L.mono) { monoActs(li, L.plan.keyDown(note, ms(t), ms(soundingUntil(li))), note, vel, t, out); continue; }
            polyOn(li, note, vel, t, out);
        }
    }
    void noteOff(int note, uint64_t t, std::vector<Out> &out)
    {
        for (int li = 0; li < nlay_; li++) {
            Lay &L = lay_[li];
            if (!owns(li)) continue;
            if (L.mono) {
                if (sustain_) { L.sustained.push_back(note); continue; }
                monoActs(li, L.plan.keyUp(note, ms(t), ms(soundingUntil(li))), note, L.vel, t, out);
                continue;
            }
            for (int r = L.info.first; r < L.info.first + L.info.count && r < bsynth::kRecorders; r++) {
                Rec &R = rec_[r];
                if (R.layer != li || R.note != note || R.released || !playing(r, t)) continue;
                if (sustain_) { R.held = true; continue; }
                R.released = true;
                pushCmd(out, bsynth::Cmd::Off, r, note);
            }
        }
    }
    void sustain(bool down, uint64_t t, std::vector<Out> &out)
    {
        sustain_ = down;
        if (down) return;
        for (int li = 0; li < nlay_; li++) {
            Lay &L = lay_[li];
            if (!owns(li)) continue;
            std::vector<int> s; s.swap(L.sustained);
            for (int n : s) monoActs(li, L.plan.keyUp(n, ms(t), ms(soundingUntil(li))), n, L.vel, t, out);
        }
        for (int r = 0; r < bsynth::kRecorders; r++) {
            Rec &R = rec_[r];
            if (R.layer < 0 || !R.held) continue;
            R.held = false;
            if (!R.released && R.finish > t) { R.released = true; pushCmd(out, bsynth::Cmd::Off, r, R.note); }
        }
    }
    void end(int r) { if (r >= 0 && r < bsynth::kRecorders) { if (rec_[r].layer >= 0) rec_[r] = Rec{}; live_[r].on = false; } }
    void allOff() { for (auto &r : rec_) r = Rec{}; for (auto &l : live_) l.on = false; for (int i = 0; i < bsynth::kMaxLayers; i++) { lay_[i].plan.reset(); lay_[i].sustained.clear(); } sustain_ = false; }

    // ---- live bend: every sounding recorder (ours and core's) follows the wheel
    // follow: each On/Off/Cut the caller sends (core's and ours), with the bend it was made with
    void follow(const bsynth::Cmd &c, bool fixedLayer)
    {
        if (c.rec >= bsynth::kRecorders) return;
        Live &L = live_[c.rec];
        if (c.kind == bsynth::Cmd::On) { L.on = true; L.fixed = fixedLayer; L.base = c.rateHz / bendFactor(bend_); }
        else if (c.kind == bsynth::Cmd::Cut || c.kind == bsynth::Cmd::Panic) { if (c.kind == bsynth::Cmd::Panic) for (auto &x : live_) x.on = false; else L.on = false; }
    }
    // the wheel moved (-1..1): `rate` lines for every recorder that sounds, stamped at t
    void bend(double norm, uint64_t t, std::vector<Out> &out)
    {
        norm = std::max(-1.0, std::min(1.0, norm));
        if (norm == bend_) return;
        bend_ = norm;
        const double f = bendFactor(norm);
        for (int r = 0; r < bsynth::kRecorders; r++) {
            Live &L = live_[r];
            if (!L.on || L.fixed || L.base <= 0) continue;
            Out o; o.kind = Out::Rate; o.rec = r; o.hz = (uint32_t)std::lround(L.base * f); o.at = t;
            out.push_back(o);
            if (rec_[r].layer >= 0) retime(r, t, o.hz);
        }
    }
    double bendNow() const { return bend_; }

private:
    struct Lay {
        bool valid = false, own = false, mono = false, fixed = false, hasD = false, tempo = false;
        int T = 0, U = 1, C = 0, level = 100, pan = 0, offset = 0, vel = 100;
        std::vector<int> H{0};
        bsynth3::VoiceMode n; bsynth3::Stack s; bsynth3::Degrees d;
        bsynth::LayerInfo info;
        bsynth3::MonoPlan plan{bsynth3::VoiceMode{}};
        std::vector<int> cur;          // mono: the recorders sounding the layer's note now
        std::vector<int> sustained;    // mono: key-ups held back by the pedal
    };
    struct Rec {
        int layer = -1, note = -1; bool released = false, held = false;
        uint64_t start = 0, finish = 0;
        double pos = 0; uint64_t posAt = 0; uint32_t hz = 0;   // where it plays (frames) and how fast, for the finish
        double cents = 0, semis = 0;                          // its unison detune and pitch (unbent), for Rate
    };
    struct Live { bool on = false, fixed = false; double base = 0; };
    Lay lay_[bsynth::kMaxLayers];
    bsynth::LayerInfo infoKeep_[bsynth::kMaxLayers];
    Rec rec_[bsynth::kRecorders];
    Live live_[bsynth::kRecorders];
    bsynth3::Key key_;
    bool keyMap_ = false;
    int nlay_ = 0, root_ = 60, velocity_ = 100, bendRange_ = 2;
    double bend_ = 0, bpm_ = 120;
    bool sustain_ = false;
    uint32_t counter_ = 0, groupCount_[9] = {0};
    int groupPick_[9] = {0};
    std::vector<int> groupsDone_;

    static double ms(uint64_t t) { return t / 48.0; }
    double bendFactor(double norm) const { return std::pow(2.0, norm * bendRange_ / 12.0); }
    double tscale(const Lay &L) const { return L.tempo ? 120.0 / bpm_ : 1.0; }
    bool playing(int r, uint64_t t) const { return rec_[r].layer >= 0 && (rec_[r].finish > t || rec_[r].held); }
    void pushCmd(std::vector<Out> &out, bsynth::Cmd::Kind k, int r, int note)
    {
        Out o; o.c = bsynth::Cmd{k, (uint8_t)r, (uint8_t)note, 0, 0}; out.push_back(o);
        if (k == bsynth::Cmd::Cut) { rec_[r] = Rec{}; live_[r].on = false; }
    }
    // the finish of a recorder after a rate change at t
    void retime(int r, uint64_t t, uint32_t hz)
    {
        Rec &R = rec_[r];
        const Lay &L = lay_[R.layer];
        if (t > R.posAt && R.hz) R.pos += (double)(t - R.posAt) * R.hz / 48000.0;
        R.posAt = std::max<uint64_t>(t, R.posAt); R.hz = hz;
        if (hz && L.info.frames) R.finish = R.posAt + (uint64_t)(std::max(0.0, L.info.frames - R.pos) * 48000.0 / hz);
    }
    uint64_t soundingUntil(int li) const
    {
        uint64_t u = 0;
        for (int r : lay_[li].cur) if (rec_[r].layer == li) u = std::max(u, rec_[r].finish);
        return u;
    }
    // Sg: is this layer the one of its group that plays this note?
    bool groupTurn(int li)
    {
        const int g = lay_[li].s.group;
        std::vector<int> members;
        for (int k = 0; k < nlay_; k++) if (owns(k) && lay_[k].s.group == g) members.push_back(k);
        bsynth3::Rng rng(0x51ED27u ^ (counter_ * 2654435761u) ^ (uint32_t)g);
        if (std::find(groupsDone_.begin(), groupsDone_.end(), g) == groupsDone_.end()) {
            groupPick_[g] = bsynth3::groupPick(members, lay_[li].s.groupRandom, groupCount_[g]++, rng);
            groupsDone_.push_back(g);
        }
        return groupPick_[g] == li;
    }
    // the pitch offsets (semitones, fractional with D) of one note's harmony voices, low to high
    std::vector<double> intervals(const Lay &L, int note)
    {
        if (L.hasD) {
            std::vector<double> c = bsynth3::voiceOffsets(key_, L.d, note, key_.snap);
            std::vector<double> s; for (double x : c) s.push_back(x / 100.0);
            if (L.H.size() > 1 || L.H[0] != 0) {   // D and H together: each degree voice carries the H intervals
                std::vector<double> o; for (double x : s) for (int h : L.H) o.push_back(x + h); return o;
            }
            return s;
        }
        bsynth3::Rng rng(0xC0FFEEu ^ (counter_ * 2246822519u));
        std::vector<int> h = bsynth3::noteIntervals(L.s, L.H, counter_, rng);
        if (keyMap_ && !L.fixed) {   // the key maps the played note (remap, or a non-12 tuning): its pitch, then H
            const bsynth3::Degrees one;
            const std::vector<double> c = bsynth3::voiceOffsets(key_, one, note, key_.snap);
            const double off = c.empty() ? 0.0 : c[0] / 100.0;
            std::vector<double> o; for (int x : h) o.push_back(off + x); return o;
        }
        return std::vector<double>(h.begin(), h.end());
    }
    // one voice: a recorder (free with the oldest finish, else steal the oldest; Sp: a random free one)
    int pickRec(int li, uint64_t t, const bool *taken, std::vector<Out> &out)
    {
        const Lay &L = lay_[li];
        int best = -1, nfree = 0;
        for (int r = L.info.first; r < L.info.first + L.info.count && r < bsynth::kRecorders; r++) {
            if (taken[r] || playing(r, t)) continue;
            nfree++;
            if (best < 0 || rec_[r].finish < rec_[best].finish) best = r;
        }
        if (best >= 0 && L.s.randomRec && nfree > 1) {
            bsynth3::Rng rng(0xA5A5u ^ (counter_ * 0x9E3779B1u) ^ (uint32_t)li);
            int k = rng.in(0, nfree - 1);
            for (int r = L.info.first; r < L.info.first + L.info.count && r < bsynth::kRecorders; r++) {
                if (taken[r] || playing(r, t)) continue;
                if (k-- == 0) { best = r; break; }
            }
        }
        if (best < 0) {
            for (int r = L.info.first; r < L.info.first + L.info.count && r < bsynth::kRecorders; r++) {
                if (taken[r]) continue;
                if (best < 0 || rec_[r].start < rec_[best].start) best = r;
            }
            if (best < 0) return -1;
            pushCmd(out, bsynth::Cmd::Cut, best, rec_[best].note);
        }
        return best;
    }
    // start one voice on recorder r: the On (strum delay in delayMs) and the bookkeeping
    void startVoice(int li, int r, int note, int vel, uint64_t t, double semis, double cents, int panAdd, int strumMs, std::vector<Out> &out)
    {
        Lay &L = lay_[li];
        const double bend = L.fixed ? 0 : bend_ * bendRange_;
        const uint32_t rate = bsynth::Voices::rateFor(L.info.rate, semis + bend, cents);
        Rec &R = rec_[r];
        R = Rec{}; R.layer = li; R.note = note; R.start = t; R.semis = semis; R.cents = cents;
        const uint64_t begin = t + (uint64_t)std::llround((L.offset + strumMs) * tscale(L) * 48.0);
        R.pos = 0; R.posAt = begin; R.hz = rate;
        R.finish = L.info.frames && rate ? begin + (uint64_t)((double)L.info.frames * 48000.0 / rate) : t;
        Out o;
        o.c = bsynth::Cmd{bsynth::Cmd::On, (uint8_t)r, (uint8_t)note, rate, bsynth::Voices::volumeFor(vel, velocity_, L.level)};
        o.c.pan = (int8_t)std::max(-100, std::min(100, L.pan + panAdd));
        o.c.delayMs = (uint16_t)std::min(65535.0, L.offset + strumMs * tscale(L));   // b16v3::delay48 scales O by Wt itself
        o.c.layer = (uint8_t)li;
        out.push_back(o);
        follow(o.c, L.fixed);
    }
    double voiceSemis(const Lay &L, int note, double iv) const { return L.fixed ? L.T + iv : (note - root_) + L.T + iv; }
    double voiceCents(const Lay &L, int ui) const { return L.U > 1 ? -L.C + 2.0 * L.C * ui / (L.U - 1) : 0; }

    void polyOn(int li, int note, int vel, uint64_t t, std::vector<Out> &out)
    {
        Lay &L = lay_[li];
        if (L.n.poly > 0) {   // Np<n>: at most n notes at once; the oldest note goes
            for (;;) {
                std::vector<int> notes; uint64_t oldest = UINT64_MAX; int oldNote = -1;
                for (int r = L.info.first; r < L.info.first + L.info.count && r < bsynth::kRecorders; r++) {
                    if (rec_[r].layer != li || !playing(r, t)) continue;
                    if (std::find(notes.begin(), notes.end(), rec_[r].note) == notes.end()) notes.push_back(rec_[r].note);
                    if (rec_[r].start < oldest) { oldest = rec_[r].start; oldNote = rec_[r].note; }
                }
                if ((int)notes.size() < L.n.poly || oldNote < 0) break;
                for (int r = L.info.first; r < L.info.first + L.info.count && r < bsynth::kRecorders; r++)
                    if (rec_[r].layer == li && rec_[r].note == oldNote) pushCmd(out, bsynth::Cmd::Cut, r, oldNote);
            }
        }
        const std::vector<double> iv = intervals(L, note);
        bool taken[bsynth::kRecorders] = {false};
        int nv = (int)iv.size() * L.U;
        if (nv > L.info.count) nv = L.info.count;
        for (int k = 0; k < nv; k++) {
            const int hi = k / L.U, ui = k % L.U;
            const int r = pickRec(li, t, taken, out);
            if (r < 0) break;
            taken[r] = true;
            startVoice(li, r, note, vel, t, voiceSemis(L, note, iv[hi]), voiceCents(L, ui), bsynth3::unisonPan(L.s, ui, L.U), bsynth3::strumDelayMs(L.s, hi), out);
        }
    }

    // mono, legato, continue: MonoPlan's actions on the layer's current recorders (U unison voices move together)
    void monoActs(int li, const std::vector<bsynth3::Action> &acts, int key, int vel, uint64_t t, std::vector<Out> &out)
    {
        Lay &L = lay_[li];
        L.vel = vel;
        for (const bsynth3::Action &a : acts) {
            switch (a.kind) {
            case bsynth3::Action::Cut:
                for (int r : L.cur) if (rec_[r].layer == li) pushCmd(out, bsynth::Cmd::Cut, r, rec_[r].note);
                L.cur.clear();
                break;
            case bsynth3::Action::Off:
                for (int r : L.cur) if (rec_[r].layer == li && !rec_[r].released) {
                    if (sustain_) { rec_[r].held = true; continue; }
                    rec_[r].released = true; pushCmd(out, bsynth::Cmd::Off, r, rec_[r].note);
                }
                break;
            case bsynth3::Action::On: {
                L.cur.clear();
                bool taken[bsynth::kRecorders] = {false};
                const int nv = std::min(L.U, L.info.count);
                for (int ui = 0; ui < nv; ui++) {
                    const int r = pickRec(li, t, taken, out);
                    if (r < 0) break;
                    taken[r] = true;
                    startVoice(li, r, a.note, vel, t, voiceSemis(L, a.note, 0), voiceCents(L, ui), bsynth3::unisonPan(L.s, ui, L.U), 0, out);
                    L.cur.push_back(r);
                }
                break; }
            case bsynth3::Action::Rate: {
                const double bend = L.fixed ? 0 : bend_ * bendRange_;
                const int glide = (int)std::lround(a.glideMs * tscale(L));
                for (int r : L.cur) {
                    Rec &R = rec_[r];
                    if (R.layer != li) continue;
                    R.semis = voiceSemis(L, a.note, 0); R.note = a.note;
                    if (a.regate) R.released = false;
                    const uint32_t hz = bsynth::Voices::rateFor(L.info.rate, R.semis + bend, R.cents);
                    Out o; o.kind = Out::Rate; o.rec = r; o.hz = hz; o.glideMs = glide; o.regate = a.regate; o.at = t;
                    out.push_back(o);
                    live_[r].base = hz / bendFactor(bend_);
                    retime(r, t, hz);
                }
                break; }
            }
        }
        (void)key;
    }
};

}  // namespace b16v3

namespace b16v3 {
// The key and scale parameters (PRESET-ENGINE-2 section 18.2), as the plugin, render311 and the state hold them.
struct KeyParams {
    int root = 0;        // 0..11 (C..B)
    int scale = 0;       // a library id (scales.h)
    int usePreset = 0;   // 1: the DNA's q (its suggestion) wins
    int snap = 1;        // 1 nearest, 2 down, 3 up, 4 off
    int remap = 0;       // 1: consecutive keys walk consecutive scale steps
    int anchor = 60;     // remap: this key plays the root
    int labels = 0;      // the keyboard strip's labels: 0 none, 1 degrees, 2 sargam, 3 names, 4 cents
    bool operator==(const KeyParams &o) const { return root == o.root && scale == o.scale && usePreset == o.usePreset && snap == o.snap && remap == o.remap && anchor == o.anchor && labels == o.labels; }
    bool operator!=(const KeyParams &o) const { return !(*this == o); }
    // state lines (STATE.md): key <root> <scale> / keyopt <usePreset> <snap> <remap> <labels> <anchor>
    std::string lines() const
    {
        return "key " + std::to_string(root) + " " + std::to_string(scale) + "\nkeyopt " + std::to_string(usePreset) + " " +
               std::to_string(snap) + " " + std::to_string(remap) + " " + std::to_string(labels) + " " + std::to_string(anchor) + "\n";
    }
    bool readLine(const std::string &l)
    {
        int a = 0, b = 0, c = 0, d = 0, e = 60;
        if (std::sscanf(l.c_str(), "key %d %d", &a, &b) == 2) { root = (a % 12 + 12) % 12; scale = b < 0 ? 0 : b; return true; }
        int n = std::sscanf(l.c_str(), "keyopt %d %d %d %d %d", &a, &b, &c, &d, &e);
        if (n >= 4) { usePreset = a ? 1 : 0; snap = b >= 1 && b <= 4 ? b : 1; remap = c ? 1 : 0; labels = d >= 0 && d <= 4 ? d : 0; if (n == 5 && e >= 0 && e <= 127) anchor = e; return true; }
        return false;
    }
};
// The effective key: the DNA's suggestion (q) when "use the preset's scale" is on and it has one, else the parameters.
inline bsynth3::Key effectiveKey(const KeyParams &p, const bsynth3::Dna3 &d3)
{
    bsynth3::Key k;
    int root = p.root, id = p.scale; unsigned mask = 0; int edo = 0;
    if (p.usePreset && d3.g.hasQ) {
        if (d3.g.scale >= 0) id = d3.g.scale;
        if (d3.g.rootPc >= 0) root = d3.g.rootPc;
        mask = (unsigned)d3.g.mask; edo = d3.g.edo;
    }
    if (mask) k.tuning = bsynth3::maskTuning(mask);
    else if (edo > 0) k.tuning = bsynth3::edo(edo);
    else if (!bsynth3::libraryTuning(id, k.tuning)) bsynth3::libraryTuning(0, k.tuning);
    k.root = root; k.remap = p.remap != 0; k.anchor = p.anchor; k.snap = p.snap;
    return k;
}
}  // namespace b16v3
