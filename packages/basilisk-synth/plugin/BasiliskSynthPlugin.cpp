// BASILISK SYNTH - the plugin: MIDI in, Windows XP's sound out.
//
// The audio thread turns MIDI into DNA.md protocol lines (the shared core's voice allocator picks the recorder)
// and plays back what XP's sound card produced, delayed by a fixed, reported latency. It never synthesises a
// note itself: every sample comes from a real Sound Recorder inside the machine (see Machine.hpp).
#include "../../basilisk-synth-311/plugin/V3Host.h"   // DNA v3 notes (PRESET-ENGINE-2): the same NoteHost as BASILISK 16
#include "DistrhoPlugin.hpp"
#include "BasiliskSynthShared.hpp"

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <thread>

START_NAMESPACE_DISTRHO

using namespace bsynth;

#include <mutex>
#include <algorithm>
#include "presets_gen.h"   // kPresets[]: "Category: Name" + DNA (tools/make_presets.py, from library/presets)
static constexpr int kNumPresets = sizeof(kPresets) / sizeof(kPresets[0]);

class BasiliskSynthPlugin : public Plugin, public SynthHost
{
public:
    BasiliskSynthPlugin()
        : Plugin(kParamCount, kNumPresets, 1)
    {
        {
            // the library disc's names (DNA.md 5.6), so DNA that names them parses before the machine is up
            static std::once_flag once;
            std::call_once(once, [] { std::vector<std::string> n; for (int i = 0; kLibraryNames[i]; i++) n.push_back(kLibraryNames[i]); setLibrary(n); });
        }
        dna_ = kPresets[0].dna;
        parsed_ = parse(dna_);
        globalsToParams(parsed_);
        pendingDna_ = new Dna(parsed_);       // the audio thread's voice allocator takes it on its first block
        std::memset(noteMap_, -1, sizeof noteMap_);
        if (std::getenv("BSYNTH_AUTOGO")) wantGo_ = true;    // tests: assemble without an editor

        pump_ = std::thread([this] { pump(); });
    }

    ~BasiliskSynthPlugin() override
    {
        quit_ = true;
        if (pump_.joinable()) pump_.join();
        machine_.stop();
        delete cur_;
        Dna *p = pendingDna_.exchange(nullptr);
        delete p;
        Dna *t;
        while (trash_.pop(t)) delete t;
    }

    // ------------------------------------------------------------------ SynthHost (for the UI)
    Machine &machine() override { return machine_; }
    void uiOpened() override { wantGo_ = true; editors_++; }
    void uiClosed() override { editors_--; }
    bool takeEdit(std::string &dna) override
    {
        std::lock_guard<std::mutex> g(mu_);
        if (pendingEdit_.empty()) return false;
        dna = pendingEdit_;
        pendingEdit_.clear();
        return true;
    }
    std::string dnaText() override { std::lock_guard<std::mutex> g(mu_); return dna_; }
    int latencyMs() const override { return kLatencyMs; }

protected:
    // ------------------------------------------------------------------ information
    const char *getLabel() const override { return "BasiliskSynth"; }
    const char *getDescription() const override
    {
        return "Sixteen Windows XP Sound Recorders, played from MIDI. The sound is made inside Windows XP, by "
               "sndrec32.exe, through XP's own sound card.";
    }
    const char *getMaker() const override { return "williamsharkey.com"; }
    const char *getHomePage() const override { return "https://williamsharkey.com/basilisk-download.html"; }
    const char *getLicense() const override { return "GPL-2.0-or-later"; }
    uint32_t getVersion() const override { return d_version(1, 3, 0); }

    void initAudioPort(bool input, uint32_t index, AudioPort &port) override
    {
        Plugin::initAudioPort(input, index, port);
        if (input) {
            // the recording input is a sidechain: hosts that route audio into instruments offer it there, and the
            // instrument's main output is unchanged for those that don't (RECORDING.md 1.1)
            port.hints = kAudioPortIsSidechain;
            port.name = index ? "Record In R" : "Record In L";
            port.symbol = index ? "rec_in_r" : "rec_in_l";
            port.groupId = kPortGroupStereo;
        } else port.groupId = kPortGroupStereo;
    }

    void initParameter(uint32_t i, Parameter &p) override
    {
        p.hints = kParameterIsAutomatable;
        switch (i) {
        case kGain: p.name = "Gain"; p.symbol = "gain"; p.unit = "dB"; p.ranges.min = -60; p.ranges.max = 24; p.ranges.def = 0; break;
        case kAttack: p.name = "Attack"; p.symbol = "attack"; p.unit = "ms"; p.ranges.min = 0; p.ranges.max = 5000; p.ranges.def = 0; break;
        case kDecay: p.name = "Decay"; p.symbol = "decay"; p.unit = "ms"; p.ranges.min = 0; p.ranges.max = 5000; p.ranges.def = 0; break;
        case kSustain: p.name = "Sustain"; p.symbol = "sustain"; p.unit = "%"; p.ranges.min = 0; p.ranges.max = 100; p.ranges.def = 100; break;
        case kRelease: p.name = "Release"; p.symbol = "release"; p.unit = "ms"; p.ranges.min = 0; p.ranges.max = 10000; p.ranges.def = 120; break;
        case kVelocity: p.name = "Velocity"; p.symbol = "velocity"; p.unit = "%"; p.ranges.min = 0; p.ranges.max = 100; p.ranges.def = 100; break;
        case kBend: p.name = "Bend Range"; p.symbol = "bend"; p.unit = "st"; p.ranges.min = 0; p.ranges.max = 24; p.ranges.def = 2; p.hints |= kParameterIsInteger; break;
        case kTranspose: p.name = "Transpose"; p.symbol = "transpose"; p.unit = "st"; p.ranges.min = -48; p.ranges.max = 48; p.ranges.def = 0; p.hints |= kParameterIsInteger; break;
        case kMacro1: case kMacro2: case kMacro3: case kMacro4: {
            int k = (int)(i - kMacro1) + 1;
            char nm[16], sy[16];
            snprintf(nm, sizeof nm, "Macro %d", k);
            snprintf(sy, sizeof sy, "macro%d", k);
            p.name = nm; p.symbol = sy; p.unit = "%"; p.ranges.min = 0; p.ranges.max = 100; p.ranges.def = 0;
            break; }
        }
    }

    float getParameterValue(uint32_t i) const override { return i < kParamCount ? params_[i].load() : 0.f; }

    void setParameterValue(uint32_t i, float v) override
    {
        if (i >= kParamCount) return;
        if (params_[i].load() == v) return;
        params_[i] = v;
        if (i != kGain && i != kTranspose) paramsDirty_ = true;   // the pump folds these into the DNA
    }

    void initProgramName(uint32_t i, String &name) override { name = kPresets[i].name; }
    void loadProgram(uint32_t i) override { if (i < (uint32_t)kNumPresets) applyDna(kPresets[i].dna, true); }

    void initState(uint32_t, State &s) override
    {
        s.key = "dna";
        s.label = "DNA";
        s.defaultValue = (std::string("BASILISK-SYNTH 1\ndna ") + kPresets[0].dna + "\nreference 0\nver 1.2.1\n").c_str();
        s.hints = kStateIsHostReadable;
    }
    // The state is core's State text with "ver 1.2.1": from 1.2.1 a bare chimes chord ding tada is the Windows 3.x
    // recording (DNA.md 2.4). A state without "ver" was saved by 1.2.0 or earlier, when those names meant XP's own
    // files: they become chimesxp ... so it sounds as it did.
    String getState(const char *key) const override
    {
        if (std::strcmp(key, "dna")) return String();
        bsynth::State st;
        { std::lock_guard<std::mutex> g(mu_); st.dna = dna_; }
        st.extra["ver"] = kStateVer;
        return String(st.write().c_str());
    }
    void setState(const char *key, const char *value) override
    {
        if (std::strcmp(key, "dna") || !value) return;
        bsynth::State st;
        if (!st.read(value)) { Machine::log("setState: unreadable (%.60s)", value); return; }
        Machine::log("setState: %s%s", st.dna.c_str(), st.extra.count("ver") ? "" : " (<= 1.2.0: migrated)");
        if (!st.extra.count("ver")) st.dna = bsynth::migrateXp120(st.dna);
        applyDna(st.dna, true);
    }
    static constexpr const char *kStateVer = "1.2.1";

    // ------------------------------------------------------------------ processing
    void activate() override
    {
        sr_ = getSampleRate();
        voices_.setSampleRate(sr_);
        setLatency((uint32_t)(kLatencyMs * sr_ / 1000.0));
        primed_ = false;
        wallStart_ = 0;
        processed_ = 0;
        if (!isDummyInstance()) machine_.start();
    }

    void run(const float **inputs, float **outputs, uint32_t frames, const MidiEvent *ev, uint32_t nev) override
    {
        blockClock_ = sampleClock_;
        feedInput(inputs, frames);
        float *L = outputs[0], *R = outputs[1];
        // a new DNA from the pump: hand it to the voice allocator
        if (Dna *d = pendingDna_.exchange(nullptr)) {
            Cmd c[kMaxCmds];
            int n = voices_.setDna(*d, c);   // (core's own rule: new sounds stop what sounds; genes alone do not)
            sendCmds(c, n);
            {
                // the notes (V3Host.h): the macro-applied DNA, its v3 tokens with the v3 macro maps, seeded by the text
                int mac[4];
                for (int k = 0; k < 4; k++) mac[k] = d->g.macro[k];
                host_.adopt(*d, bsynth3::applyMacros3(bsynth3::parse3(d->canonical), mac), b16v3::salt(d->canonical));
                for (int i = 0; i < bsynth::kMaxLayers; i++) if (layerKnown_[i].known) host_.layerInfo(i, layerKnown_[i].first, layerKnown_[i].count, layerKnown_[i].rate, layerKnown_[i].frames);
            }
            if (cur_) trash_.push(cur_);
            cur_ = d;
            // new sounds (a program change, a macro on N) in an offline render: this block's notes and every later
            // one must sound with them, so wait here until Windows has built them (the wait is not part of the song).
            // Live, notes keep going to the old sounds meanwhile (DNA.md 4)
            if (n > 0 && offlineSynced_ && machine_.phase == Machine::Running) {
                const double w0 = Machine::now();
                const size_t want = std::hash<std::string>()(d->layersText());
                dnaDirty_ = true;   // the pump sends the new layers now (or already has)
                while (sentLayersHash_.load() != want && Machine::now() - w0 < 2.0) std::this_thread::sleep_for(std::chrono::milliseconds(5));
                while (layersBuilt_.load() < layersSent_.load() && Machine::now() - w0 < 15.0) std::this_thread::sleep_for(std::chrono::milliseconds(10));
                const double waited = Machine::now() - w0;
                wallStart_ += waited;
                if (waited > 0.05) Machine::log("offline: waited %.2f s for new sounds before this block's notes", waited);
            }
        }
        LayerMsg lm;
        while (layerMsgs_.pop(lm)) {
            if (lm.layer >= 0) {
                voices_.setLayerInfo(lm.layer, lm.first, lm.count, lm.rate, lm.frames);
                host_.layerInfo(lm.layer, lm.first, lm.count, lm.rate, lm.frames);
                if (lm.layer < bsynth::kMaxLayers) layerKnown_[lm.layer] = bsynth::LayerInfo{lm.first, lm.count, lm.rate, lm.frames, true};
            } else { voices_.end(lm.first); host_.end(lm.first); }
        }
        SegMsg sm;
        while (segMsgs_.pop(sm)) host_.segments(sm.layer, std::vector<uint32_t>(sm.f, sm.f + sm.n));
        host_.capWin = machine_.capWin.load(); host_.capRate = machine_.capRate.load();
        {
            const auto tp = getTimePosition();
            if (tp.bbt.valid && tp.bbt.beatsPerMinute > 0) host_.bpm = tp.bbt.beatsPerMinute;
        }
        // the keyboard, wheels and Hold inside XP (DNA.md 6): they play like MIDI at the start of this block
        MidiEvent kev[64];
        uint32_t nk = 0;
        KbdMsg km;
        while (nk < 64 && kbdMsgs_.pop(km)) {
            MidiEvent &e = kev[nk++];
            e.frame = 0; e.size = 3; e.dataExt = nullptr;
            e.data[0] = km.st; e.data[1] = km.a; e.data[2] = km.b;
        }
        // MIDI (XP's own first)
        for (uint32_t i = 0; i < nk + nev; i++) {
            const MidiEvent &me = i < nk ? kev[i] : ev[i - nk];
            const bool fromXp = i < nk;
            if (me.size > 3) continue;
            const uint8_t *d = me.data;
            uint8_t st = d[0] & 0xF0;
            const uint64_t t = sampleClock_ + me.frame;
            const uint64_t at48 = (uint64_t)((double)t * 48000.0 / sr_);   // NoteHost's clock: 48 kHz samples
            int tr = (int)params_[kTranspose].load();
            auto sink = [this](const char *line, uint64_t when48) { queueLine(line, (uint64_t)((double)when48 * sr_ / 48000.0)); };
            if (st == 0x90 && d[2] > 0) {
                int note = d[1] + tr;
                if (note >= 0 && note < 128) { host_.midi(0x90, (uint8_t)note, d[2], at48, sink); noteMap_[d[1]] = (int8_t)(note); heldNotes_++; lastNoteAt_ = t; }
            } else if (st == 0x80 || (st == 0x90 && d[2] == 0)) {
                int note = noteMap_[d[1]] >= 0 ? noteMap_[d[1]] : d[1] + tr;
                if (note >= 0 && note < 128) host_.midi(0x80, (uint8_t)note, 0, at48, sink);
                if (noteMap_[d[1]] >= 0 && heldNotes_ > 0) heldNotes_--;
                noteMap_[d[1]] = -1;
                lastNoteAt_ = t;
            } else if (st == 0xB0 && (d[1] == 64 || d[1] == 120 || d[1] == 123)) {
                host_.midi(0xB0, d[1], d[2], at48, sink);
                if (d[1] != 64) heldNotes_ = 0;
            }
            else if (st == 0xB0 && d[1] == 1) { wheel_.store(d[2]); if (!fromXp) showWheel_.store(true); }
            else if (st == 0xE0) { host_.midi(0xE0, d[1], d[2], at48, sink); bendShown_.store((d[2] << 7 | d[1]) - 8192); if (!fromXp) showBend_.store(true); }
            // the DAW's notes show on XP's keyboard as keys held down
            if (!fromXp && (st == 0x90 || st == 0x80)) {
                char kl[24];
                snprintf(kl, sizeof kl, "show %d %d\n", d[1], st == 0x90 ? d[2] : 0);
                machine_.send(kl);
            }
        }
        releaseHeld(sampleClock_ + frames);
        flushLines(sampleClock_ + frames);
        sampleClock_ += frames;
        // held or recent notes, and a playing transport, keep XP awake (waking costs the first note some time)
        if (heldNotes_ > 0 || sampleClock_ - lastNoteAt_ < (uint64_t)(sr_ * 3) || nLines_ > 0 || getTimePosition().playing) machine_.touch();

        // XP's sound, 96 kHz from the machine, resampled to the host rate with a gentle drift correction
        const double target = kJitterMs * 96.0;              // frames kept in hand
        uint64_t w = machine_.audio.written();
        double gain = std::pow(10.0, params_[kGain].load() / 20.0) * std::pow(10.0, globalGainDb_.load() / 20.0);
        if (!primed_) {
            // (re)start once a jitter buffer's worth has arrived since the stream stopped
            if (w >= unprimedAt_ + (uint64_t)target) { pos_ = (double)w - target; primed_ = true; ratioTrim_ = 1.0; }
        } else {
            double avail = (double)w - pos_;
            if (avail < minAvail_) minAvail_ = avail;
            if (avail > maxAvail_) maxAvail_ = avail;
            if (avail < 4) { primed_ = false; unprimedAt_ = w; unprimes_++; }          // the stream stopped (XP asleep)
            else if (avail > target * 4) pos_ = (double)w - target;                     // far behind: catch up
            else ratioTrim_ = 0.999 * ratioTrim_ + 0.001 * (1.0 + 0.02 * (avail - target) / target);
        }
        double step = 96000.0 / sr_ * (primed_ ? ratioTrim_ : 1.0);
        for (uint32_t i = 0; i < frames; i++) {
            if (!primed_) { L[i] = R[i] = 0; continue; }
            if (pos_ + 3 >= (double)w) {
                // the stream ran short inside this block (it arrives in 10 ms pieces): hold the last sample and let it
                // fade instead of cutting to silence; the drift trim catches up from the next block
                holdL_ *= 0.995f; holdR_ *= 0.995f;
                L[i] = holdL_; R[i] = holdR_;
                if (i == 0 || !shortNow_) { shortNow_ = true; starved_++; }
                continue;
            }
            shortNow_ = false;
            uint64_t k = (uint64_t)pos_;
            float x = (float)(pos_ - (double)k);
            // 4-point Hermite
            auto h = [x](float a, float b, float c, float d) {
                float c1 = 0.5f * (c - a), c2 = a - 2.5f * b + 2.f * c - 0.5f * d, c3 = 0.5f * (d - a) + 1.5f * (b - c);
                return ((c3 * x + c2) * x + c1) * x + b;
            };
            const AudioRing &A = machine_.audio;
            L[i] = (float)(gain * h(A.L(k - 1), A.L(k), A.L(k + 1), A.L(k + 2)));
            R[i] = (float)(gain * h(A.R(k - 1), A.R(k), A.R(k + 1), A.R(k + 2)));
            holdL_ = L[i]; holdR_ = R[i];
            pos_ += step;
        }

        // an offline render runs faster than real time; the machine cannot, so wait for it
        double nowS = Machine::now();
        if (wallStart_ == 0 || nowS - lastRun_ > 1.0) { wallStart_ = nowS; processed_ = 0; }
        lastRun_ = nowS;
        processed_ += frames;
        double ahead = (double)processed_ / sr_ - (nowS - wallStart_);
        // once an offline render is known, keep it at most kAheadS ahead of the clock: its notes go that far ahead,
        // each with the delay that puts it in its place (sendAhead), so the host's own timing does not show
        if (offlineSynced_ && machine_.phase == Machine::Running && (ahead > kAheadS || guestBuilding_)) {
            // a sound being rebuilt (a program change): the render waits for it (at most 15 s), and the time it took
            // is not part of the song
            double w0 = Machine::now();
            while (guestBuilding_ && Machine::now() - w0 < 15.0) std::this_thread::sleep_for(std::chrono::milliseconds(20));
            wallStart_ = wallStart_ + (Machine::now() - w0);
            ahead = (double)processed_ / sr_ - (Machine::now() - wallStart_);
            if (ahead > kAheadS) std::this_thread::sleep_for(std::chrono::duration<double>(ahead - (kAheadS - 0.01)));
        } else if (ahead > 0.35) {
            // a host this far ahead of the clock is rendering offline: first let XP finish waking (and link up),
            // then keep pace with it
            // at most 60 s in all: a machine that never comes renders silence rather than hang the host. A machine
            // that failed to start is started again (twice at most) instead of rendering silence
            for (int k = 0; k < 1200 && offlineWaited_ < 60.0 && !(machine_.phase == Machine::Running && machine_.linked); k++) {
                // Off: not started yet (activate() starts it): wait. Failed: start it again, twice at most
                if (machine_.phase == Machine::Failed && offlineRestarts_ < 2) {
                    offlineRestarts_++;
                    Machine::log("offline render: the machine failed (%s); starting it again", machine_.error().c_str());
                    machine_.restart();
                } else if (machine_.phase == Machine::Failed) break;
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                offlineWaited_ += 0.05;
            }
            // and the sound being built (a new DNA): an offline render plays what a live one would after the build
            for (int k = 0; k < 600 && offlineWaited_ < 60.0 && machine_.phase == Machine::Running &&
                            (guestBuilding_ || !machine_.linked || !dnaSentOnce_); k++) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                offlineWaited_ += 0.05;
            }
            if (machine_.phase == Machine::Running) {
                if (!offlineSynced_) {   // count from now: the time spent waking is not part of the song
                    offlineSynced_ = true;
                    wallStart_ = Machine::now() - (double)processed_ / sr_;
                }
            }
        }
    }

private:
    // the DAW's sidechain into XP's recording card: resampled to the card's 48 kHz, s16, with the drift held by the
    // ring's fill level (a slow trim, at most +-0.2 %, aiming at 40 ms). Live only: an offline render ignores it.
    void feedInput(const float **in, uint32_t frames)
    {
        bsynth::DBusIn &di = machine_.input;
        if (!in || !in[0] || !in[1] || !di.connected() || !di.enabled() || offlineSynced_) { inPos_ = 0; return; }
        const double target = 0.040 * 48000;
        double fill = (double)di.ring.fill();
        inTrim_ = 0.999 * inTrim_ + 0.001 * (1.0 + 0.01 * (target - fill) / target);
        if (inTrim_ > 1.002) inTrim_ = 1.002;
        if (inTrim_ < 0.998) inTrim_ = 0.998;
        const double step = sr_ / 48000.0 / inTrim_;
        int16_t lr[2 * 512];
        size_t n = 0;
        // linear interpolation from the host's rate; inPos_ is the read position in this block (it may start < 0
        // into the previous block's last frame)
        while (inPos_ < (double)frames - 1) {
            int i = (int)inPos_;
            double f = inPos_ - i;
            float l = i < 0 ? inLast_[0] : in[0][i], r = i < 0 ? inLast_[1] : in[1][i];
            float l2 = in[0][i + 1 < 0 ? 0 : i + 1], r2 = in[1][i + 1 < 0 ? 0 : i + 1];
            float L = (float)(l + (l2 - l) * f), R = (float)(r + (r2 - r) * f);
            lr[2 * n] = (int16_t)(L > 1 ? 32767 : L < -1 ? -32767 : L * 32767);
            lr[2 * n + 1] = (int16_t)(R > 1 ? 32767 : R < -1 ? -32767 : R * 32767);
            if (++n == 512) { di.ring.write(lr, n); n = 0; }
            inPos_ += step;
        }
        if (n) di.ring.write(lr, n);
        inPos_ -= frames;
        inLast_[0] = in[0][frames - 1]; inLast_[1] = in[1][frames - 1];
    }
    double inPos_ = 0, inTrim_ = 1.0;
    float inLast_[2] = {0, 0};

    enum { kGain, kAttack, kDecay, kSustain, kRelease, kVelocity, kBend, kTranspose, kMacro1, kMacro2, kMacro3, kMacro4, kParamCount };
    // measured: MIDI in -> first sample of that note in XP's stream, plus the jitter buffer (README: Timing)
#ifdef _WIN32
    static constexpr int kLatencyMs = 150, kJitterMs = 70;   // 50 ran short under load (the pipe comes in 10 ms pieces); 150: harness onsets centred (120 left them +30-39 ms late)
#else
    static constexpr int kLatencyMs = 100, kJitterMs = 55;   // 40 underran on a busy Mac
#endif

    struct LayerMsg { int layer, first, count, rate, frames; };
    struct KbdMsg { uint8_t st, a, b; };

    // a layer's start offset (O) is waited out here, to the sample, and the line goes with delay 0
    struct Held { Cmd c; uint64_t due; bool used; };
    static constexpr int kHeld = 128;
    Held held_[kHeld] = {};
    // NoteHost's lines, each due at a host sample: sent in the block they fall in, as "at <ms> <line>" so Windows runs
    // them at their place (live: their offset in the block; offline: their place in the song, sendAhead's rule)
    struct QLine { uint64_t due; char line[112]; };
    static constexpr int kQLines = 512;
    QLine qlines_[kQLines];
    int nLines_ = 0;
    void queueLine(const char *line, uint64_t due)
    {
        if (nLines_ >= kQLines) { Machine::log("note lines: queue full, one dropped"); return; }
        QLine &q = qlines_[nLines_++];
        q.due = due;
        std::snprintf(q.line, sizeof q.line, "%s", line);
    }
    void flushLines(uint64_t until)
    {
        // in due order (stable: lines due together keep the order NoteHost gave them, a choke before its on)
        for (;;) {
            int best = -1;
            for (int i = 0; i < nLines_; i++) if (qlines_[i].due < until && (best < 0 || qlines_[i].due < qlines_[best].due)) best = i;
            if (best < 0) break;
            const QLine q = qlines_[best];
            for (int i = best; i + 1 < nLines_; i++) qlines_[i] = qlines_[i + 1];
            nLines_--;
            double ms;
            if (offlineSynced_ && machine_.phase == Machine::Running) {
                const double dueWall = wallStart_ + ((double)processed_ + (double)((int64_t)q.due - (int64_t)blockClock_)) / sr_;
                ms = (dueWall - Machine::now()) * 1000.0;
            } else ms = (double)((int64_t)q.due - (int64_t)blockClock_) * 1000.0 / sr_;
            char b[140];
            const int d = ms < 1 ? 0 : ms > 5000 ? 5000 : (int)(ms + 0.5);
            if (d > 0) std::snprintf(b, sizeof b, "at %d %s\n", d, q.line); else std::snprintf(b, sizeof b, "%s\n", q.line);
            machine_.send(b);
            if (!std::strncmp(q.line, "on ", 3)) sentNotes_++;
        }
    }

    void sendNow(const Cmd &c)
    {
        char b[96];
        if (proto::cmd(b, sizeof b, c) > 0) { machine_.send(b); sentNotes_++; }
    }
    // an offline render (DNA.md 4, XP 1.3): every line goes ahead of time with the delay that makes Windows run it at
    // its place in the song (wallStart_ + song time), on Windows' own millisecond clock: the timing no longer depends
    // on when the host got to this block. Live: sent now, as before
    bool sendAhead(Cmd x, uint64_t due)
    {
        if (!offlineSynced_ || machine_.phase != Machine::Running || x.kind == Cmd::Panic) return false;
        const double dueWall = wallStart_ + ((double)processed_ + (double)((int64_t)due - (int64_t)blockClock_)) / sr_;
        double ms = (dueWall - Machine::now()) * 1000.0;
        if (ms < 0) ms = 0;
        if (ms > 5000) ms = 5000;
        x.delayMs = (uint16_t)(ms + 0.5);
        sendNow(x);
        return true;
    }
    void sendCmds(const Cmd *c, int n, uint64_t t = 0)
    {
        for (int i = 0; i < n; i++) {
            Cmd x = c[i];
            if (offlineSynced_ && machine_.phase == Machine::Running && x.kind != Cmd::Panic) {
                // the layer's O is part of the due time; ons and offs keep their order on Windows' clock
                uint64_t due = t ? t : blockClock_;
                if (x.kind == Cmd::On && x.delayMs > 0) due += (uint64_t)(x.delayMs * sr_ / 1000.0);
                x.delayMs = 0;
                if (sendAhead(x, due)) continue;
            }
            if (x.kind == Cmd::On && x.delayMs > 0) {
                uint64_t due = t + (uint64_t)(x.delayMs * sr_ / 1000.0);
                x.delayMs = 0;
                for (auto &h : held_) if (!h.used) { h.c = x; h.due = due; h.used = true; break; }
                continue;
            }
            if (x.kind == Cmd::Off || x.kind == Cmd::Cut) {   // a note let go before its layer started: never starts
                bool dropped = false;
                for (auto &h : held_) if (h.used && h.c.rec == x.rec) { h.used = false; dropped = true; }
                if (dropped) { voices_.end(x.rec); continue; }
            }
            if (x.kind == Cmd::Panic) for (auto &h : held_) h.used = false;
            sendNow(x);
        }
    }
    void releaseHeld(uint64_t until)
    {
        for (auto &h : held_) if (h.used && h.due < until) { h.used = false; sendNow(h.c); }
    }

    // the guest's layer lines describe this DNA: the same layers on the same recorders
    static bool matches(const std::vector<LayerMsg> &rep, const Dna &d)
    {
        size_t n = 0;
        for (size_t i = 0; i < d.layers.size(); i++) if (d.layers[i].count > 0) n++;
        if (rep.size() != d.layers.size() && rep.size() != n) return false;
        for (auto &m : rep) {
            if (m.layer < 0 || (size_t)m.layer >= d.layers.size()) return false;
            const auto &l = d.layers[(size_t)m.layer];
            if (l.first != m.first || l.count != m.count) return false;
        }
        return true;
    }

    void globalsToParams(const Dna &d)
    {
        params_[kAttack] = (float)d.g.attack; params_[kDecay] = (float)d.g.decay; params_[kSustain] = (float)d.g.sustain;
        params_[kRelease] = (float)d.g.release; params_[kVelocity] = (float)d.g.velocity; params_[kBend] = (float)d.g.bendRange;
        globalGainDb_ = (float)d.g.gainDb;
        for (int k = 0; k < kMacros; k++) params_[kMacro1 + k] = (float)d.g.macro[k];
    }

    // a DNA from the host, a preset or the parameters: keep it, give it to the audio thread and the guest
    void applyDna(const std::string &text, bool fromOutside)
    {
        Dna d = parse(text);
        {
            std::lock_guard<std::mutex> g(mu_);
            if (d.canonical == dna_ && !fromOutside) return;
            dna_ = d.canonical;
            parsed_ = d;
        }
        if (fromOutside) globalsToParams(d);
        Dna *nd = new Dna(applyMacros(d));   // what sounds: macros applied
        Dna *old = pendingDna_.exchange(nd);
        delete old;
        dnaDirty_ = true;
    }

    // the plugin's own thread: guest replies, parameters, and what to tell the guest
    void pump()
    {
        bool sentDna = false, sentGo = false;
        double lastLog = 0;
        std::string lastSentDna, lastEnv, lastLenv;
        int lastWheel = -1, sentVis = -1, restarts = 0;
        std::string lastGlobals;
        double lastGlobalsSent = 0;
        int builtFrames[bsynth::kMaxLayers] = {0};   // what the guest reported for each layer since the last "dna"
        std::vector<LayerMsg> reported, stale;        // layer lines before a "built"; a build that was not ours
        uint64_t wdFrames = 0;
        double wdSince = Machine::now(), wdStart = 0;
        while (!quit_) {
            std::this_thread::sleep_for(std::chrono::milliseconds(4));
            Dna *t;
            while (trash_.pop(t)) delete t;
            if (paramsDirty_.exchange(false)) {
                std::string d;
                { std::lock_guard<std::mutex> g(mu_); d = dna_; }
                d = setGlobal(d, 'A', (int)params_[kAttack].load());
                d = setGlobal(d, 'D', (int)params_[kDecay].load());
                d = setGlobal(d, 'S', (int)params_[kSustain].load());
                d = setGlobal(d, 'R', (int)params_[kRelease].load());
                d = setGlobal(d, 'V', (int)params_[kVelocity].load());
                d = setGlobal(d, 'B', (int)params_[kBend].load());
                for (int k = 0; k < kMacros; k++) {
                    int v = (int)std::lround(params_[kMacro1 + k].load());
                    if (k == 0 && wheel_.load() > 0) v = std::min(100, v + (int)std::lround(wheel_.load() * 100.0 / 127));
                    if (v != parse(d).g.macro[k]) d = setMacro(d, k + 1, v);
                }
                applyDna(d, false);
            }
            std::string line;
            while (machine_.popReply(line)) {
                int ka = 0, kb = 0;
                // the keyboard and wheels inside Windows (DNA.md 5.4): like MIDI, through the same voice allocator
                if (sscanf(line.c_str(), "key %d %d", &ka, &kb) == 2) {
                    if (kb > 0) kbdMsgs_.push({0x90, (uint8_t)(ka & 127), (uint8_t)std::min(127, kb)});
                    else kbdMsgs_.push({0x80, (uint8_t)(ka & 127), 0});
                    machine_.touch();
                    continue;
                }
                if (sscanf(line.c_str(), "cc %d %d", &ka, &kb) == 2) { kbdMsgs_.push({0xB0, (uint8_t)(ka & 127), (uint8_t)std::max(0, std::min(127, kb))}); continue; }
                if (sscanf(line.c_str(), "bend %d", &ka) == 1) { ka = std::max(-8192, std::min(8191, ka)) + 8192; kbdMsgs_.push({0xE0, (uint8_t)(ka & 127), (uint8_t)(ka >> 7)}); continue; }
                proto::Reply r = proto::parse(line);
                if (r.kind == proto::Reply::Layer) {
                    // held until its "built": only a build of the layers we sent may route notes (below)
                    if (r.layer == 0) reported.clear();
                    reported.push_back({r.layer, r.first, r.count, r.rate, r.frames});
                }
                else if (r.kind == proto::Reply::End) layerMsgs_.push({-1, r.rec, 0, 0, 0});
                else if (line.rfind("seg ", 0) == 0) {   // seg <layer> <f0> <f1> ...: a layer's segments (kit pads)
                    SegMsg sm{}; const char *q = line.c_str() + 4; char *e;
                    sm.layer = (int)std::strtol(q, &e, 10); q = e;
                    while (sm.n < 16) { long v = std::strtol(q, &e, 10); if (e == q) break; sm.f[sm.n++] = (uint32_t)v; q = e; }
                    if (sm.layer >= 0 && sm.layer < bsynth::kMaxLayers) segMsgs_.push(sm);
                }
                else if (r.kind == proto::Reply::Built) {
                    // the build is done only when every layer that can sound has been reported with a sound in it:
                    // a "built" can also be a stale one, or come before the library disc was read
                    Dna d;
                    { std::lock_guard<std::mutex> g(mu_); d = applyMacros(parsed_); }
                    // a "built" can be another DNA's: the one Windows was still building when ours arrived (at
                    // startup, its default sound), finished before it starts ours. Its layers (recorders) differ from
                    // ours: those must not route our notes, nor end the wait (1.2.2: notes played the default sound)
                    if (matches(reported, d)) {
                        for (auto &m : reported) {
                            layerMsgs_.push(m);
                            if (m.layer >= 0 && m.layer < bsynth::kMaxLayers) builtFrames[m.layer] = m.frames;
                        }
                        bool all = true;
                        for (size_t i = 0; i < d.layers.size() && i < (size_t)bsynth::kMaxLayers; i++)
                            if (d.layers[i].valid() && builtFrames[i] <= 0) all = false;
                        if (all || Machine::now() - buildSentAt_ > 20.0) { guestBuilding_ = false; machine_.keepAwake = false; layersBuilt_.store(layersSent_.load()); }
                        else Machine::log("built, but not every layer has its sound yet: still waiting");
                    } else {
                        Machine::log("built: another DNA's layers (%d reported, %d sent): still waiting for ours", (int)reported.size(), (int)d.layers.size());
                        stale = reported;
                        if (Machine::now() - buildSentAt_ > 20.0) { guestBuilding_ = false; machine_.keepAwake = false; }
                    }
                    reported.clear();
                }
                else if (r.kind == proto::Reply::Edit) {
                    // changed inside XP: it is already built there; adopt it
                    Dna d = parse(r.text);
                    {
                        std::lock_guard<std::mutex> g(mu_);
                        dna_ = d.canonical;
                        parsed_ = d;
                        pendingEdit_ = d.canonical;
                        lastSentDna = applyMacros(d).layersText();
                    }
                    globalsToParams(d);
                    Dna *nd = new Dna(applyMacros(d));
                    if (matches(stale, *nd)) for (auto &m : stale) layerMsgs_.push(m);   // built in XP before its edit line
                    stale.clear();
                    delete pendingDna_.exchange(nd);
                }
            }
            if (guestBuilding_ && Machine::now() - buildSentAt_ > 30.0) {
                // never left waiting: a build that does not report within 30 s is given up (its notes play what is there)
                Machine::log("build: no matching report in 30 s; going on");
                guestBuilding_ = false; machine_.keepAwake = false; layersBuilt_.store(layersSent_.load());
            }
            if (Machine::now() - lastLog > 2 && machine_.phase == Machine::Running) {
                lastLog = Machine::now();
                Machine::log("audio: %llu frames in, primed %d, notes sent %d, buffer %.1f..%.1f ms, restarts %d, short blocks %d, gaps in XP's stream %llu, screen updates %llu%s, input reads %llu underruns %llu", (unsigned long long)machine_.audio.written(), (int)primed_, sentNotes_.load(),
                             minAvail_ / 96.0, maxAvail_ / 96.0, unprimes_.load(), starved_.load(), (unsigned long long)machine_.gapsIn_.load(),
                             (unsigned long long)machine_.input.displayUpdates(), machine_.input.displayMapped() ? " (mapped)" : "",
                             (unsigned long long)machine_.input.reads(), (unsigned long long)machine_.input.ring.underruns());
                minAvail_ = 1e9; maxAvail_ = 0;
            }
            // "go" leaves with the first lines on COM1, without waiting for the guest's hello
            if (wantGo_ && !sentGo && machine_.phase == Machine::Running) {
                machine_.send("go\n");
                sentGo = true;
            }
            // builds are shown (each step picked from the recorder's menu) only while someone is watching; batch
            // renders can force it either way (BSYNTH_VISIBLE_BUILD)
            if (machine_.linked) {
                const char *ev = std::getenv("BSYNTH_VISIBLE_BUILD");
                int vis = ev ? atoi(ev) : editors_.load() > 0;
                if (vis != sentVis) { char l[16]; snprintf(l, sizeof l, "vis %d\n", vis); machine_.send(l); sentVis = vis; }
            } else sentVis = -1;
            if (wantGo_ && !machine_.ready) machine_.touch();     // awake until the assembly is done
            // a test hook (RECORDING.md TR1): BSYNTH_RECTEST="SECONDS@DELAY" asks Windows to record from its recording
            // card DELAY s after the link is up and report the tone's quality in the log ("guest: rectest ...")
            if (const char *rt = std::getenv("BSYNTH_RECTEST")) {
                static double linkedAt = 0; static bool sentRt = false;
                if (machine_.linked && linkedAt == 0) linkedAt = Machine::now();
                double delay = 0; int secs = std::atoi(rt);
                if (const char *at = std::strchr(rt, '@')) delay = std::atof(at + 1);
                if (!sentRt && linkedAt > 0 && Machine::now() - linkedAt > delay) {
                    char l[32]; snprintf(l, sizeof l, "rectest %d\n", secs); machine_.send(l); sentRt = true;
                    Machine::log("rectest sent (input %s, rate %u, reads %llu)", machine_.input.connected() ? "connected" : "not connected",
                                 machine_.input.rate(), (unsigned long long)machine_.input.reads());
                }
            }
            // the watchdog: a machine that stays silent (no sound frames from QEMU while awake), or never gets
            // running, is restarted (at most 3 times)
            {
                double t = Machine::now();
                uint64_t w = machine_.audio.written();
                int ph = machine_.phase.load();
                if (w != wdFrames || machine_.asleep || ph != Machine::Running) { wdFrames = w; wdSince = t; }
                if (ph != Machine::Running && ph != Machine::Fetching && ph != Machine::Unpacking && ph != Machine::Off) {
                    if (wdStart == 0) wdStart = t;
                } else wdStart = 0;
                bool silent = ph == Machine::Running && t - wdSince > 8.0 && t - machine_.resumedAt.load() > 8.0;
                bool stuck = wdStart > 0 && t - wdStart > 90.0;
                if ((silent || stuck) && restarts < 3) {
                    restarts++;
                    Machine::log("watchdog: %s; restart %d", silent ? "no sound from QEMU for 8 s" : "not running after 90 s", restarts);
                    machine_.restart();
                    sentGo = false; sentDna = false; wdStart = 0; wdSince = Machine::now();
                    continue;
                }
            }
            // the wheels: the DAW's moves show on Windows' sliders; the mod wheel adds to Macro 1 (DNA.md 5.4)
            {
                int wv = wheel_.load();
                if (wv >= 0 && wv != lastWheel) { lastWheel = wv; paramsDirty_ = true; }
                char wl[32];
                if (machine_.linked && showWheel_.exchange(false)) { snprintf(wl, sizeof wl, "cc 1 %d\n", wv); machine_.send(wl); }
                if (machine_.linked && showBend_.exchange(false)) { snprintf(wl, sizeof wl, "bend %d\n", bendShown_.load()); machine_.send(wl); }
            }
            if (!machine_.linked) { sentDna = false; continue; }
            if (!sentDna || dnaDirty_.exchange(false)) {
                Dna d;
                { std::lock_guard<std::mutex> g(mu_); d = parsed_; }
                Dna eff = applyMacros(d);
                char b[160];
                // the buffers are rebuilt only when the (effective) layers changed; envelopes and pan are lines
                std::string globals;
                size_t semi = d.canonical.find(';');
                if (semi != std::string::npos) globals = d.canonical.substr(semi);
                if (!sentDna || eff.layersText() != lastSentDna) {
                    // a macro on N changes the layers: Windows gets the layers as they sound, with the DNA's own
                    // globals (macros included), so its editor still shows the mappings
                    machine_.sendLong("dna " + eff.layersText() + globals + "\n");
                    guestBuilding_ = true; machine_.keepAwake = true; buildSentAt_ = Machine::now(); dnaSentOnce_ = true;
                    sentLayersHash_ = std::hash<std::string>()(eff.layersText());
                    layersSent_++;
                    for (auto &f : builtFrames) f = 0;
                    lastSentDna = eff.layersText();
                    lastGlobals = globals; lastGlobalsSent = Machine::now();
                    lastLenv.clear();
                } else if (globals != lastGlobals) {
                    // only globals moved (a macro, the mod wheel, ADSR): Windows' DNA box and Macros panel follow,
                    // at most 10 times a second; nothing is rebuilt (the layers are the same)
                    if (Machine::now() - lastGlobalsSent > 0.1) {
                        machine_.sendLong("dna " + eff.layersText() + globals + "\n");
                        lastGlobals = globals; lastGlobalsSent = Machine::now();
                    } else dnaDirty_ = true;
                }
                proto::env(b, sizeof b, d.g);
                if (!sentDna || lastEnv != b) { machine_.send(b); lastEnv = b; }
                std::string le;
                for (size_t i = 0; i < eff.layers.size(); i++) {
                    proto::lenv(b, sizeof b, (int)i, 'a', eff.layers[i].envA); le += b;
                    proto::lenv(b, sizeof b, (int)i, 'p', eff.layers[i].envP); le += b;
                }
                if (le != lastLenv) { machine_.sendLong(le); lastLenv = le; }
                globalGainDb_ = (float)d.g.gainDb;
                sentDna = true;
            }
        }
    }

    Machine machine_;
    Voices voices_{48000};               // only for "new sounds stop what sounds" (setDna); the notes are NoteHost's
    b16v3::NoteHost host_;               // the notes: core's voices, V3Alloc and the v3 draws (V3Host.h), audio thread
    bsynth::LayerInfo layerKnown_[bsynth::kMaxLayers];
    int heldNotes_ = 0;
    uint64_t lastNoteAt_ = 0;
    struct SegMsg { int layer; int n; uint32_t f[16]; };
    Spsc<SegMsg> segMsgs_{64};
    Dna *cur_ = nullptr;
    std::atomic<Dna *> pendingDna_{nullptr};
    Spsc<Dna *> trash_{64};
    Spsc<LayerMsg> layerMsgs_{256};
    Spsc<KbdMsg> kbdMsgs_{256};
    std::atomic<int> wheel_{-1}, bendShown_{0}, editors_{0};
    std::atomic<bool> guestBuilding_{false}, dnaSentOnce_{false};
    std::atomic<uint32_t> layersSent_{0}, layersBuilt_{0};
    uint64_t blockClock_ = 0;                 // sampleClock_ at the start of this block
    static constexpr double kAheadS = 0.08;   // an offline render runs at most this far ahead of the clock (notes go ahead)
    std::atomic<size_t> sentLayersHash_{0};   // dna lines with new layers sent / built by Windows
    std::atomic<double> buildSentAt_{0};
    std::atomic<bool> showWheel_{false}, showBend_{false};
    std::thread pump_;
    std::atomic<bool> quit_{false}, paramsDirty_{false}, dnaDirty_{false}, wantGo_{false};
    std::atomic<float> params_[kParamCount] = {{0}, {0}, {0}, {100}, {120}, {100}, {2}, {0}, {0}, {0}, {0}, {0}};
    std::atomic<float> globalGainDb_{0};
    std::atomic<int> sentNotes_{0}, unprimes_{0};
    double minAvail_ = 1e9, maxAvail_ = 0;
    mutable std::mutex mu_;
    std::string dna_, pendingEdit_;
    Dna parsed_;
    double sr_ = 48000, pos_ = 0, ratioTrim_ = 1, wallStart_ = 0, lastRun_ = 0;
    bool primed_ = false, offlineSynced_ = false, shortNow_ = false;
    float holdL_ = 0, holdR_ = 0;
    std::atomic<int> starved_{0};
    double offlineWaited_ = 0;
    int offlineRestarts_ = 0;
    uint64_t sampleClock_ = 0, processed_ = 0, unprimedAt_ = 0;
    int8_t noteMap_[128];

    DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(BasiliskSynthPlugin)
};

Plugin *createPlugin() { return new BasiliskSynthPlugin(); }

END_NAMESPACE_DISTRHO

SynthHost *synthHostOf(void *p) { return p ? static_cast<DISTRHO_NAMESPACE::BasiliskSynthPlugin *>(static_cast<DISTRHO_NAMESPACE::Plugin *>(p)) : nullptr; }
