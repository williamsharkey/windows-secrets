#include "voices.h"
#include <cmath>

namespace bsynth {

uint32_t Voices::rateFor(int layerRate, double semis, double cents)
{
    double r = layerRate * std::pow(2.0, semis / 12.0 + cents / 1200.0);
    if (r < 2000) r = 2000;
    if (r > 192000) r = 192000;
    return (uint32_t)std::lround(r);
}

// vol = velocity curve (squared, blended with full volume by V%) x L%, clamped to 65535
uint16_t Voices::volumeFor(int vel, int velocityPct, int levelPct)
{
    double v = vel < 1 ? 1 : vel > 127 ? 127 : vel;
    double curve = (v / 127.0) * (v / 127.0);
    double k = velocityPct / 100.0;
    double a = (1.0 - k) + k * curve;
    double x = a * levelPct / 100.0 * 65535.0;
    if (x > 65535) x = 65535;
    if (x < 0) x = 0;
    return (uint16_t)std::lround(x);
}

static uint64_t bufferKey(const Layer &s)
{
    uint64_t h = 1469598103934665603ull;
    auto mix = [&](const void *p, size_t n) { for (size_t i = 0; i < n; i++) { h ^= ((const unsigned char *)p)[i]; h *= 1099511628211ull; } };
    mix(s.sourceName.data(), s.sourceName.size());
    for (auto &st : s.steps) { mix(&st.op, 1); mix(&st.arg, sizeof st.arg); mix(&st.ms, sizeof st.ms); mix(st.name.data(), st.name.size()); }
    mix(&s.first, sizeof s.first); mix(&s.count, sizeof s.count);
    return h;
}

int Voices::setDna(const Dna &d, Cmd *out)
{
    // the same buffers on the same recorders: only genes changed, nothing needs to stop
    bool same = (int)d.layers.size() == nlay_;
    for (int i = 0; same && i < nlay_ && i < kMaxLayers; i++) same = bufferKey(d.layers[i]) == buf_[i];
    nlay_ = (int)d.layers.size();
    for (int i = 0; i < kMaxLayers; i++) {
        lay_[i] = L();
        // a new sound: until the guest reports the new layers, notes go to the recorders as they were, which still
        // hold the old sounds (the guest plays them during the build, DNA.md 4); a layer that is new stays silent
        if (!same && !info_[i].known) info_[i] = LayerInfo();
        buf_[i] = 0;
        if (i >= nlay_) continue;
        const Layer &s = d.layers[i];
        buf_[i] = bufferKey(s);
        lay_[i].valid = s.valid() && s.count > 0;
        lay_[i].fixed = s.fixed; lay_[i].T = s.transpose; lay_[i].U = s.unison; lay_[i].C = s.spreadCents; lay_[i].level = s.level; lay_[i].pan = s.pan; lay_[i].offset = s.offset;
        lay_[i].nh = (int)s.harmony.size();
        for (int k = 0; k < lay_[i].nh && k < kMaxHarmony; k++) lay_[i].h[k] = s.harmony[k];
        if (!same && !info_[i].known) { info_[i].first = s.first; info_[i].count = s.count; }
    }
    root_ = d.g.root; velocity_ = d.g.velocity; bendRange_ = d.g.bendRange;
    if (same) return 0;
    for (auto &r : rec_) r = Rec();
    sustain_ = false;
    out[0] = Cmd{Cmd::Panic, 0, 0, 0, 0};
    return 1;
}

void Voices::setLayerInfo(int i, int first, int count, int rate, int frames)
{
    if (i < 0 || i >= kMaxLayers) return;
    info_[i].first = first; info_[i].count = count; info_[i].rate = rate; info_[i].frames = frames; info_[i].known = true;
}

uint64_t Voices::finishOf(int layer, uint32_t rate, uint64_t t) const
{
    const LayerInfo &li = info_[layer];
    if (!li.frames || !rate) return t;
    return t + (uint64_t)((double)li.frames / rate * sr_);
}

bool Voices::playing(int r, uint64_t t) const { return rec_[r].busy && (rec_[r].finish > t || rec_[r].held); }

int Voices::activeCount(uint64_t t) const { int n = 0; for (int r = 0; r < kRecorders; r++) if (playing(r, t)) n++; return n; }

int Voices::noteOn(int note, int vel, uint64_t t, Cmd *out)
{
    int n = 0;
    bool taken[kRecorders] = {false};
    for (int li = 0; li < nlay_; li++) {
        const L &l = lay_[li];
        const LayerInfo &inf = info_[li];
        if (!l.valid || !inf.known || inf.count <= 0) continue;
        int nv = l.nh * l.U;
        if (nv > inf.count) nv = inf.count;   // more voices than recorders: the extra harmony/unison voices are dropped
        uint16_t vol = volumeFor(vel, velocity_, l.level);
        for (int k = 0; k < nv; k++) {
            int hi = k / l.U, ui = k % l.U;
            double cents = l.U > 1 ? -l.C + 2.0 * l.C * ui / (l.U - 1) : 0;
            double semis = l.fixed ? (double)(l.T + l.h[hi]) : (double)(note - root_ + l.T + l.h[hi]) + bend_ * bendRange_;
            uint32_t rate = rateFor(inf.rate, semis, cents);
            // the free recorder with the oldest finish; else the oldest playing one (stolen: cut first)
            int best = -1;
            for (int r = inf.first; r < inf.first + inf.count; r++) {
                if (taken[r] || playing(r, t)) continue;
                if (best < 0 || rec_[r].finish < rec_[best].finish) best = r;
            }
            if (best < 0) {
                for (int r = inf.first; r < inf.first + inf.count; r++) {
                    if (taken[r]) continue;
                    if (best < 0 || rec_[r].start < rec_[best].start) best = r;
                }
                if (best < 0) break;
                out[n++] = Cmd{Cmd::Cut, (uint8_t)best, (uint8_t)rec_[best].note, 0, 0};
            }
            taken[best] = true;
            Rec &R = rec_[best];
            R.busy = true; R.released = false; R.held = false; R.note = note; R.layer = li; R.start = t;
            uint64_t start = t + (uint64_t)(l.offset * sr_ / 1000.0);
            R.finish = finishOf(li, rate, start);
            Cmd c{Cmd::On, (uint8_t)best, (uint8_t)note, rate, vol};
            c.pan = (int8_t)l.pan; c.delayMs = (uint16_t)l.offset; c.layer = (uint8_t)li;
            out[n++] = c;
            if (n >= kMaxCmds - 1) return n;
        }
    }
    return n;
}

int Voices::noteOff(int note, uint64_t t, Cmd *out)
{
    int n = 0;
    for (int r = 0; r < kRecorders; r++) {
        Rec &R = rec_[r];
        if (!R.busy || R.released || R.note != note || !playing(r, t)) continue;
        if (sustain_) { R.held = true; continue; }
        R.released = true;
        out[n++] = Cmd{Cmd::Off, (uint8_t)r, (uint8_t)note, 0, 0};
    }
    return n;
}

int Voices::sustain(bool down, uint64_t t, Cmd *out)
{
    int n = 0;
    sustain_ = down;
    if (down) return 0;
    for (int r = 0; r < kRecorders; r++) {
        Rec &R = rec_[r];
        if (!R.held) continue;
        R.held = false;
        if (R.busy && !R.released && R.finish > t) { R.released = true; out[n++] = Cmd{Cmd::Off, (uint8_t)r, (uint8_t)R.note, 0, 0}; }
    }
    return n;
}

void Voices::end(int r)
{
    if (r < 0 || r >= kRecorders) return;
    rec_[r].busy = false; rec_[r].held = false; rec_[r].released = false;
}

int Voices::allOff(Cmd *out)
{
    for (auto &r : rec_) { r.busy = false; r.held = false; r.released = false; }
    sustain_ = false;
    out[0] = Cmd{Cmd::Panic, 0, 0, 0, 0};
    return 1;
}

}  // namespace bsynth
