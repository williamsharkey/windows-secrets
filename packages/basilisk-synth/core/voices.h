// BASILISK SYNTH shared core: the voice allocator (DNA.md section 4, host-side rules). Real-time safe: no allocation
// after setDna(); every call fills a caller-provided fixed array of commands for the guest.
#pragma once
#include <cstdint>
#include "dna.h"

namespace bsynth {

struct Cmd {
    enum Kind : uint8_t { On, Off, Cut, Panic } kind;
    uint8_t rec;        // recorder 0..15
    uint8_t note;       // the MIDI note it belongs to
    uint32_t rateHz;    // On
    uint16_t vol;       // On: 0..65535
    int8_t pan = 0;     // On (v2): -100..100, the layer's Q
    uint16_t delayMs = 0;   // On (v2): the layer's O; the host may wait this long itself and send 0
    uint8_t layer = 0;  // On (v2): the layer it plays (its envelope applies)
};
constexpr int kMaxCmds = 2 * kRecorders + 4;

struct LayerInfo { int first = 0, count = 0, rate = 0, frames = 0; bool known = false; };

class Voices {
public:
    explicit Voices(double sampleRate = 48000) : sr_(sampleRate) {}
    void setSampleRate(double sr) { sr_ = sr; }
    // New DNA: layer pools, genes and globals. Call off the audio thread or between blocks. When a layer's buffer
    // (source, steps) or pool changes, everything is silenced (returns one Panic); when only voice genes, pan,
    // offsets, envelopes or globals change (macros, the mod wheel), sounding notes go on and the guest's layer
    // info is kept (returns 0 commands).
    int setDna(const Dna &d, Cmd *out);
    // The guest's `layer i first count rate frames` reply.
    void setLayerInfo(int i, int first, int count, int rate, int frames);
    // A note at host sample `t`. Returns the number of commands written (Cut before On for stolen recorders).
    int noteOn(int note, int vel, uint64_t t, Cmd *out);
    int noteOff(int note, uint64_t t, Cmd *out);
    int sustain(bool down, uint64_t t, Cmd *out);
    void bend(double norm) { bend_ = norm < -1 ? -1 : norm > 1 ? 1 : norm; }   // -1..1, times B semitones
    void end(int rec);                                                           // guest: `end <rec>`
    int allOff(Cmd *out);
    // the rate formula of DNA.md section 3 (exposed for tests and for the reference renderer)
    static uint32_t rateFor(int layerRate, double semis, double cents);
    static uint16_t volumeFor(int vel, int velocityPct, int levelPct);
    int activeCount(uint64_t t) const;
    bool playing(int rec, uint64_t t) const;

private:
    struct Rec { bool busy = false, released = false, held = false; int note = -1, layer = -1; uint64_t start = 0, finish = 0; };
    Rec rec_[kRecorders];
    LayerInfo info_[kMaxLayers];
    uint64_t buf_[kMaxLayers] = {0};     // what each layer's buffer depends on (a hash of source and steps)
    struct L { bool valid = false, fixed = false; int T = 0, U = 1, C = 0, level = 100, nh = 1, pan = 0, offset = 0; int h[kMaxHarmony] = {0}; } lay_[kMaxLayers];
    int nlay_ = 0, root_ = 60, velocity_ = 100, bendRange_ = 2;
    double sr_, bend_ = 0;
    bool sustain_ = false;
    uint64_t finishOf(int layer, uint32_t rate, uint64_t t) const;
};

}  // namespace bsynth
