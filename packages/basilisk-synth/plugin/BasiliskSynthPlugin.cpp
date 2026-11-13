// BASILISK SYNTH - the plugin: MIDI in, Windows XP's sound out.
//
// The audio thread turns MIDI into DNA.md protocol lines (the shared core's voice allocator picks the recorder)
// and plays back what XP's sound card produced, delayed by a fixed, reported latency. It never synthesises a
// note itself: every sample comes from a real Sound Recorder inside the machine (see Machine.hpp).
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
    uint32_t getVersion() const override { return d_version(1, 2, 0); }

    void initAudioPort(bool input, uint32_t index, AudioPort &port) override
    {
        port.groupId = kPortGroupStereo;
        Plugin::initAudioPort(input, index, port);
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
        s.defaultValue = kPresets[0].dna;
        s.hints = kStateIsHostReadable;
    }
    String getState(const char *key) const override
    {
        if (std::strcmp(key, "dna")) return String();
        std::lock_guard<std::mutex> g(mu_);
        return String(dna_.c_str());
    }
    void setState(const char *key, const char *value) override
    {
        if (std::strcmp(key, "dna") || !value) return;
        bsynth::State st;
        if (!st.read(value)) return;
        applyDna(st.dna, true);
    }

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

    void run(const float **, float **outputs, uint32_t frames, const MidiEvent *ev, uint32_t nev) override
    {
        float *L = outputs[0], *R = outputs[1];
        // a new DNA from the pump: hand it to the voice allocator
        if (Dna *d = pendingDna_.exchange(nullptr)) {
            Cmd c[kMaxCmds];
            int n = voices_.setDna(*d, c);
            sendCmds(c, n);
            if (cur_) trash_.push(cur_);
            cur_ = d;
        }
        LayerMsg lm;
        while (layerMsgs_.pop(lm)) {
            if (lm.layer >= 0) voices_.setLayerInfo(lm.layer, lm.first, lm.count, lm.rate, lm.frames);
            else voices_.end(lm.first);
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
            Cmd c[kMaxCmds];
            int n = 0;
            uint64_t t = sampleClock_ + me.frame;
            int tr = (int)params_[kTranspose].load();
            if (st == 0x90 && d[2] > 0) {
                int note = d[1] + tr;
                if (note >= 0 && note < 128) { n = voices_.noteOn(note, d[2], t, c); noteMap_[d[1]] = (int8_t)(note); }
            } else if (st == 0x80 || (st == 0x90 && d[2] == 0)) {
                int note = noteMap_[d[1]] >= 0 ? noteMap_[d[1]] : d[1] + tr;
                if (note >= 0 && note < 128) n = voices_.noteOff(note, t, c);
                noteMap_[d[1]] = -1;
            } else if (st == 0xB0 && d[1] == 64) n = voices_.sustain(d[2] >= 64, t, c);
            else if (st == 0xB0 && (d[1] == 120 || d[1] == 123)) n = voices_.allOff(c);
            else if (st == 0xB0 && d[1] == 1) { wheel_.store(d[2]); if (!fromXp) showWheel_.store(true); }
            else if (st == 0xE0) { voices_.bend(((d[2] << 7 | d[1]) - 8192) / 8192.0); bendShown_.store((d[2] << 7 | d[1]) - 8192); if (!fromXp) showBend_.store(true); }
            sendCmds(c, n, t);
            // the DAW's notes show on XP's keyboard as keys held down
            if (!fromXp && (st == 0x90 || st == 0x80)) {
                char kl[24];
                snprintf(kl, sizeof kl, "show %d %d\n", d[1], st == 0x90 ? d[2] : 0);
                machine_.send(kl);
            }
        }
        releaseHeld(sampleClock_ + frames);
        sampleClock_ += frames;
        // sounding notes, and a playing transport, keep XP awake (waking costs the first note some time)
        if (voices_.activeCount(sampleClock_) > 0 || getTimePosition().playing) machine_.touch();

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
            if (!primed_ || pos_ + 3 >= (double)w) { L[i] = R[i] = 0; continue; }
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
            pos_ += step;
        }

        // an offline render runs faster than real time; the machine cannot, so wait for it
        double nowS = Machine::now();
        if (wallStart_ == 0 || nowS - lastRun_ > 1.0) { wallStart_ = nowS; processed_ = 0; }
        lastRun_ = nowS;
        processed_ += frames;
        double ahead = (double)processed_ / sr_ - (nowS - wallStart_);
        // once an offline render is known, keep it within 20 ms of the clock: a note is sent to XP when its block is
        // processed, so running further ahead would make it sound early by that much
        if (offlineSynced_ && machine_.phase == Machine::Running && (ahead > 0.02 || guestBuilding_)) {
            // a sound being rebuilt (a program change): the render waits for it (at most 15 s), and the time it took
            // is not part of the song
            double w0 = Machine::now();
            while (guestBuilding_ && Machine::now() - w0 < 15.0) std::this_thread::sleep_for(std::chrono::milliseconds(20));
            wallStart_ = wallStart_ + (Machine::now() - w0);
            ahead = (double)processed_ / sr_ - (Machine::now() - wallStart_);
            if (ahead > 0.02) std::this_thread::sleep_for(std::chrono::duration<double>(ahead - 0.01));
        } else if (ahead > 0.35) {
            // a host this far ahead of the clock is rendering offline: first let XP finish waking (and link up),
            // then keep pace with it
            // at most 60 s in all: a machine that never comes renders silence rather than hang the host
            for (int k = 0; k < 600 && offlineWaited_ < 60.0 && !(machine_.phase == Machine::Running && machine_.linked) &&
                            machine_.phase != Machine::Failed && machine_.phase != Machine::Off; k++) {
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
    enum { kGain, kAttack, kDecay, kSustain, kRelease, kVelocity, kBend, kTranspose, kMacro1, kMacro2, kMacro3, kMacro4, kParamCount };
    // measured: MIDI in -> first sample of that note in XP's stream, plus the jitter buffer (README: Timing)
#ifdef _WIN32
    static constexpr int kLatencyMs = 100, kJitterMs = 50;
#else
    static constexpr int kLatencyMs = 100, kJitterMs = 40;
#endif

    struct LayerMsg { int layer, first, count, rate, frames; };
    struct KbdMsg { uint8_t st, a, b; };

    // a layer's start offset (O) is waited out here, to the sample, and the line goes with delay 0
    struct Held { Cmd c; uint64_t due; bool used; };
    static constexpr int kHeld = 128;
    Held held_[kHeld] = {};
    void sendNow(const Cmd &c)
    {
        char b[96];
        if (proto::cmd(b, sizeof b, c) > 0) { machine_.send(b); sentNotes_++; }
    }
    void sendCmds(const Cmd *c, int n, uint64_t t = 0)
    {
        for (int i = 0; i < n; i++) {
            Cmd x = c[i];
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
                if (r.kind == proto::Reply::Layer) layerMsgs_.push({r.layer, r.first, r.count, r.rate, r.frames});
                else if (r.kind == proto::Reply::End) layerMsgs_.push({-1, r.rec, 0, 0, 0});
                else if (r.kind == proto::Reply::Built) guestBuilding_ = false;
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
                    delete pendingDna_.exchange(nd);
                }
            }
            if (Machine::now() - lastLog > 2 && machine_.phase == Machine::Running) {
                lastLog = Machine::now();
                Machine::log("audio: %llu frames in, primed %d, notes sent %d, buffer %.1f..%.1f ms, restarts %d", (unsigned long long)machine_.audio.written(), (int)primed_, sentNotes_.load(),
                             minAvail_ / 96.0, maxAvail_ / 96.0, unprimes_.load());
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
                if (!sentDna || eff.layersText() != lastSentDna) {
                    // a macro on N changes the layers: Windows gets the layers as they sound, with the DNA's own
                    // globals (macros included), so its editor still shows the mappings
                    std::string globals;
                    size_t semi = d.canonical.find(';');
                    if (semi != std::string::npos) globals = d.canonical.substr(semi);
                    machine_.sendLong("dna " + eff.layersText() + globals + "\n");
                    guestBuilding_ = true; buildSentAt_ = Machine::now(); dnaSentOnce_ = true;
                    lastSentDna = eff.layersText();
                    lastLenv.clear();
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
    Voices voices_{48000};
    Dna *cur_ = nullptr;
    std::atomic<Dna *> pendingDna_{nullptr};
    Spsc<Dna *> trash_{64};
    Spsc<LayerMsg> layerMsgs_{256};
    Spsc<KbdMsg> kbdMsgs_{256};
    std::atomic<int> wheel_{-1}, bendShown_{0}, editors_{0};
    std::atomic<bool> guestBuilding_{false}, dnaSentOnce_{false};
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
    bool primed_ = false, offlineSynced_ = false;
    double offlineWaited_ = 0;
    uint64_t sampleClock_ = 0, processed_ = 0, unprimedAt_ = 0;
    int8_t noteMap_[128];

    DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(BasiliskSynthPlugin)
};

Plugin *createPlugin() { return new BasiliskSynthPlugin(); }

END_NAMESPACE_DISTRHO

SynthHost *synthHostOf(void *p) { return p ? static_cast<DISTRHO_NAMESPACE::BasiliskSynthPlugin *>(static_cast<DISTRHO_NAMESPACE::Plugin *>(p)) : nullptr; }
