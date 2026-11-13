// BASILISK 16: the DNA v3 part of a note (design/PRESET-ENGINE-2.md sections 3-5), shared by the plugin and render311.
// A v2 `on` command from the voice allocator becomes the v3 `on` line: the layer's window (W) and the per-note
// random draws (Y: detune, level, late start, pan), seeded so a render repeats. The window's end (and Wm, the tape
// length) is a `cut` stamped at the DAC sample where it must end: the card ends it there, with its 5 ms fade.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>
#include "../../basilisk-synth/core/dna3.h"
#include "../../basilisk-synth/core/engine3.h"
#include "../../basilisk-synth/core/voices.h"

namespace b16v3 {

struct NoteOut {
    char on[128];            // the `on` line (without '\n')
    uint64_t when = 0;       // its DAC stamp (Y's late start added)
    bool cut = false;        // a window end (or Wm) to stamp
    uint64_t cutAt = 0;
    bool gate = false;       // Wg: an `off` (the release) to stamp, n/16 beats after the start
    uint64_t gateAt = 0;
};
// Time and tempo (W o b g t). bpm: the host's tempo (120 when it has none).
inline double tempoScale(const bsynth3::Layer3 *L, double bpm)   // Wt: a layer's ms count at 120 bpm
{
    return L && L->has[0] && L->w.tempo && bpm > 1 ? 120.0 / bpm : 1.0;
}
inline uint64_t ms48(double ms) { return ms > 0 ? (uint64_t)std::llround(ms * 48.0) : 0; }
// the start delay of an On, in DAC samples: v2's O (or Wo, which reaches 30 s), scaled by Wt, plus Wb sixteenths
inline uint64_t delay48(const bsynth3::Dna3 &d3, const bsynth::Cmd &c, double bpm)
{
    const bsynth3::Layer3 *L = c.layer < d3.layers.size() ? &d3.layers[c.layer] : nullptr;
    double ms = c.delayMs;
    if (L && L->has[0] && L->w.offMs) ms = L->w.offMs;
    ms *= tempoScale(L, bpm);
    if (L && L->has[0] && L->w.beat16) ms += L->w.beat16 * (60000.0 / (bpm > 1 ? bpm : 120.0)) / 16.0;
    return ms48(ms);
}
// a layer's drawn envelope for the guest: Wt scales its times, Wr / Wp loop its last points while the key is held
// (`lenv <layer> <a|p> <t,l.t,l...|-> [<loop>]`; the loop only for a guest with the `loop` cap)
inline std::string lenvLine(int layer, char which, const bsynth::Env &e, const bsynth3::Dna3 &d3, double bpm, bool loopCap)
{
    const bsynth3::Layer3 *L = layer < (int)d3.layers.size() ? &d3.layers[layer] : nullptr;
    const double k = tempoScale(L, bpm);
    bsynth::Env s = e;
    if (k != 1.0) for (auto &p : s) p.first = (int)std::min(65535L, std::lround(p.first * k));
    std::string out = "lenv " + std::to_string(layer) + " " + which + " " + bsynth::envText(s);
    const int loop = L && L->has[0] ? (which == 'a' ? L->w.loopA : L->w.loopP) : 0;
    if (loopCap && loop >= 2 && (int)s.size() >= 2) out += " " + std::to_string(std::min(loop, (int)s.size()));
    return out;
}
// A string hash, so two presets draw different random values for the same note.
inline uint32_t salt(const std::string &dna)
{
    uint32_t h = 2166136261u;
    for (unsigned char c : dna) { h ^= c; h *= 16777619u; }
    return h;
}
// c: an On command; vel: the note's velocity; at: its DAC stamp (48 kHz); frames, rate: the layer's buffer, as the
// guest reported it; counter: notes so far (the default seed); win: the guest has the `win` cap.
inline NoteOut note(const bsynth3::Dna3 &d3, const bsynth::Cmd &c, int vel, uint64_t at, uint32_t frames, int rate,
                    uint32_t &counter, uint32_t dnaSalt, bool win, double bpm = 120)
{
    NoteOut o;
    o.when = at;
    unsigned hz = c.rateHz, vol = c.vol;
    int pan = c.pan;
    bsynth3::Span w{0, 0};
    const bsynth3::Layer3 *L = c.layer < d3.layers.size() ? &d3.layers[c.layer] : nullptr;
    counter++;
    if (L && win && (L->has[0] || L->has[3])) {
        bsynth3::Rng rng(bsynth3::voiceSeed(L->y, c.note, c.rec, counter, dnaSalt));
        if (L->has[0] && frames > 0 && rate > 0) w = bsynth3::window(L->w, frames, rate, vel, rng);
        if (L->has[3]) {
            const bsynth3::HumanDraw h = bsynth3::humanize(L->y, rng);
            hz = (unsigned)std::lround(hz * std::pow(2.0, h.cents / 1200.0));
            vol = (unsigned)std::min(65535L, std::lround(vol * h.levelPct / 100.0));
            o.when += ms48(h.lateMs * tempoScale(L, bpm));
            pan = std::max(-100, std::min(100, pan + h.pan));
        }
        // the end: the window (when it ends before the buffer does) and the real-time cap Wm
        uint64_t end = 0;
        if (w.to > w.from && w.to < frames && hz) end = o.when + (uint64_t)((double)(w.to - w.from) * 48000.0 / hz);
        if (L->has[0] && L->w.maxMs > 0) { const uint64_t m = o.when + ms48(L->w.maxMs * tempoScale(L, bpm)); if (!end || m < end) end = m; }
        if (end) { o.cut = true; o.cutAt = end; }
    }
    if (L && L->has[0] && L->w.gate16 > 0) { o.gate = true; o.gateAt = o.when + ms48(L->w.gate16 * (60000.0 / (bpm > 1 ? bpm : 120.0)) / 16.0); }
    if (w.to > w.from && w.from > 0) std::snprintf(o.on, sizeof o.on, "on %d %u %u %d 0 %d %u %u", c.rec, hz, vol, pan, c.layer, w.from, w.to);
    else std::snprintf(o.on, sizeof o.on, "on %d %u %u %d 0 %d", c.rec, hz, vol, pan, c.layer);
    return o;
}

}  // namespace b16v3
