// BASILISK 16: the host's note logic, one copy for the plugin (Basilisk16Plugin.cpp), render311 and the web edition
// (tools/basilisk16-web/host.cpp): a MIDI event in, the guest-link lines out, each stamped with the DAC sample at
// which it must happen. It holds core's voice allocator (the layers without v3 voice tokens), V3Alloc (N, S, D, the
// key, kits, live bend) and the per-note v3 draws (V3Voice.h): windows, humanize, delays, gates, kit windows, chokes,
// rate lines. The caller owns the clock, the transport and the guest link; it calls this on its audio thread.
#pragma once
#include <cstdio>
#include <cstring>
#include <functional>
#include <vector>
#include "../../basilisk-synth/core/proto.h"
#include "V3Voice.h"
#include "V3Alloc.h"

namespace b16v3 {

class NoteHost {
public:
    // a line for the guest and its DAC stamp (every note line is stamped; the caller gives it an event id)
    using Sink = std::function<void(const char *line, uint64_t at)>;

    double bpm = 120;          // the host's tempo (v3 Wt, Wb, Wg)
    bool capWin = false;       // the guest's caps (hi 3): v3 windows, rate lines
    bool capRate = false;
    uint32_t recBusy = 0;      // recorders that record now: notes leave them alone (RECORDING.md 4.3)

    // a DNA the audio adopts: the macro-applied v2 DNA, its v3 tokens and their salt (V3Voice salt)
    void adopt(const bsynth::Dna &eff, const bsynth3::Dna3 &d3, uint32_t salt)
    {
        bsynth::Cmd c[1];
        voices_.setDna(eff, c);
        d3_ = d3; salt_ = salt;
        v3_.setDna(eff, d3_);
        for (int i = 0; i < bsynth::kMaxLayers; i++) fixed_[i] = i < (int)eff.layers.size() && eff.layers[i].fixed;
        v3_.setKey(bsynth3Key_ = effectiveKey(key_, d3_));
        relayer();
    }
    // the guest's `layer i first count rate frames`
    void layerInfo(int i, int first, int count, int rate, int frames)
    {
        if (i < 0 || i >= bsynth::kMaxLayers) return;
        info_[i].first = first; info_[i].count = count; info_[i].rate = rate; info_[i].frames = frames; info_[i].known = true;
        frames_[i] = (uint32_t)frames; rate_[i] = rate;
        v3_.setLayerInfo(i, first, count, rate, frames);
        voices_.setLayerInfo(i, first, v3_.owns(i) ? 0 : count, rate, frames);
    }
    void segments(int layer, const std::vector<uint32_t> &starts) { v3_.setSegments(layer, starts); }   // `seg`
    void end(int rec) { voices_.end(rec); v3_.end(rec); }                                                // `end`
    // the key parameters (PRESET-ENGINE-2 18.2): new notes follow them; which layers core or V3Alloc plays follows too
    void setKey(const KeyParams &k) { key_ = k; v3_.setKey(bsynth3Key_ = effectiveKey(key_, d3_)); relayer(); }
    const bsynth3::Dna3 &dna3() const { return d3_; }

    // one MIDI event (status with its channel bits, two data bytes) at DAC sample `at`
    void midi(uint8_t status, uint8_t d1, uint8_t d2, uint64_t at, const Sink &sink)
    {
        const uint8_t st = status & 0xF0;
        bsynth::Cmd c[bsynth::kMaxCmds]; int n = 0;
        vo_.clear();
        v3_.setBpm(bpm);
        if (st == 0x90 && d2 > 0) { n = voices_.noteOn(d1, d2, at, c); v3_.noteOn(d1, d2, at, vo_); }
        else if (st == 0x80 || st == 0x90) { n = voices_.noteOff(d1, at, c); v3_.noteOff(d1, at, vo_); }
        else if (st == 0xB0) {
            if (d1 == 64) { n = voices_.sustain(d2 >= 64, at, c); v3_.sustain(d2 >= 64, at, vo_); }
            else if (d1 == 120 || d1 == 123) { n = voices_.allOff(c); v3_.allOff(); }
        } else if (st == 0xE0) {
            const int v = (d1 | (d2 << 7)) - 8192;
            voices_.bend(v / 8192.0);
            if (capRate) v3_.bend(v / 8192.0, at, vo_);   // what already sounds follows the wheel
        }
        const int vel = st == 0x90 ? d2 : 100;
        for (int k = 0; k < n; k++) v3_.follow(c[k], c[k].layer < bsynth::kMaxLayers && fixed_[c[k].layer]);
        for (int k = 0; k < n; k++) sendCmd(c[k], vel, at, 0, 0, sink);
        for (const Out &o : vo_) {   // then v3's, in order (a Rate after the On it moves)
            if (o.kind == Out::Cmd) { sendCmd(o.c, vel, at, o.winFrom, o.winTo, sink); continue; }
            char line[64];
            if (o.kind == Out::Choke) { std::snprintf(line, sizeof line, "choke %d %d", o.rec, o.fadeMs); sink(line, o.at); continue; }   // a kit's cut group
            if (!capRate) continue;
            std::snprintf(line, sizeof line, "rate %d %u %d %d", o.rec, o.hz, o.glideMs, o.regate ? 1 : 0);
            sink(line, o.at);
        }
    }

private:
    bsynth::Voices voices_{48000};
    V3Alloc v3_;
    bsynth3::Dna3 d3_;
    uint32_t salt_ = 0, counter_ = 0;
    uint32_t frames_[bsynth::kMaxLayers] = {};
    int rate_[bsynth::kMaxLayers] = {};
    bool fixed_[bsynth::kMaxLayers] = {};
    bsynth::LayerInfo info_[bsynth::kMaxLayers];
    KeyParams key_;
    bsynth3::Key bsynth3Key_;
    std::vector<Out> vo_;

    void relayer()   // core gets a 0-recorder pool for the layers V3Alloc plays
    {
        for (int i = 0; i < bsynth::kMaxLayers; i++)
            if (info_[i].known) voices_.setLayerInfo(i, info_[i].first, v3_.owns(i) ? 0 : info_[i].count, info_[i].rate, info_[i].frames);
    }
    void sendCmd(bsynth::Cmd cm, int vel, uint64_t at, uint32_t wf, uint32_t wt, const Sink &sink)
    {
        char line[128];
        if (cm.kind != bsynth::Cmd::Panic && cm.rec < 16 && (recBusy >> cm.rec & 1)) return;   // recording there
        uint64_t when = at;
        if (cm.kind == bsynth::Cmd::On) { when += delay48(d3_, cm, bpm); cm.delayMs = 0; }   // O (v3: Wo, Wb, Wt; S strum)
        if (cm.kind == bsynth::Cmd::On && wt > wf && capWin) {   // a kit pad's window (its segment, start and end): exact
            std::snprintf(line, sizeof line, "on %d %u %u %d 0 %d %u %u", cm.rec, cm.rateHz, cm.vol, cm.pan, cm.layer, wf, wt);
            sink(line, when);
            if (cm.rateHz) { char cl[32]; std::snprintf(cl, sizeof cl, "cut %d", cm.rec); sink(cl, when + (uint64_t)((double)(wt - wf) * 48000.0 / cm.rateHz)); }
            return;
        }
        if (cm.kind == bsynth::Cmd::On && capWin) {   // the v3 window and the per-note random draws (V3Voice.h)
            const int L = cm.layer < bsynth::kMaxLayers ? cm.layer : 0;
            const NoteOut o = note(d3_, cm, vel, when, frames_[L], rate_[L], counter_, salt_, true, bpm);
            sink(o.on, o.when);
            if (o.cut) { char cl[32]; std::snprintf(cl, sizeof cl, "cut %d", cm.rec); sink(cl, o.cutAt); }
            if (o.gate && (!o.cut || o.gateAt < o.cutAt)) { char cl[32]; std::snprintf(cl, sizeof cl, "off %d", cm.rec); sink(cl, o.gateAt); }
            return;
        }
        bsynth::proto::cmd(line, sizeof line, cm);
        line[std::strlen(line) - 1] = 0;
        sink(line, when);
    }
};

}  // namespace b16v3
