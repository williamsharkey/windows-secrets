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

static const struct { const char *name, *dna; } kPresets[] = {
    {"Chord Organ", "chord#10/ding>>E#6;A2D300S70R250"},
    {"Tada Brass", "tada@20[]#16;A5S100R300"},
    {"Ding Bells", "ding#8H0,12/xpding#8T12;R600"},
    {"Startup Pad", "startup<#16U2~8;A400D800S80R1200"},
    {"Reverse Chimes", "chimesR#12U2~6/ding>E#4;A30R500"},
    {"Logoff Strings", "logoff@40[#16U3~12;A250S90R900"},
    {"Error Pluck", "errorE#16;A0D250S0R150"},
    {"Recycle Perc", "recycle>>#8F/xprecycle#8T-12;R80"},
    {"Notify Choir", "notify<-E#16H0,7;A300S85R1000"},
    {"Critical Bass", "critstop<<#16T-12;A5D400S60R200"},
    {"Balloon Keys", "balloonMding#16H0,12;R300"},
    {"Shutdown Drone", "shutdown<R#16U3~15;A900S100R2000"},
};
static constexpr int kNumPresets = sizeof(kPresets) / sizeof(kPresets[0]);

class BasiliskSynthPlugin : public Plugin, public SynthHost
{
public:
    BasiliskSynthPlugin()
        : Plugin(kParamCount, kNumPresets, 1)
    {
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
    void uiOpened() override { wantGo_ = true; }
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
    uint32_t getVersion() const override { return d_version(1, 0, 0); }

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
        // MIDI
        for (uint32_t i = 0; i < nev; i++) {
            if (ev[i].size > 3) continue;
            const uint8_t *d = ev[i].data;
            uint8_t st = d[0] & 0xF0;
            Cmd c[kMaxCmds];
            int n = 0;
            uint64_t t = sampleClock_ + ev[i].frame;
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
            else if (st == 0xE0) voices_.bend(((d[2] << 7 | d[1]) - 8192) / 8192.0);
            sendCmds(c, n);
        }
        sampleClock_ += frames;
        // sounding notes, and a playing transport, keep XP awake (waking costs the first note some time)
        if (voices_.activeCount(sampleClock_) > 0 || getTimePosition().playing) machine_.touch();

        // XP's sound, 44.1 kHz from the machine, resampled to the host rate with a gentle drift correction
        const double target = kJitterMs * 44.1;              // frames kept in hand
        uint64_t w = machine_.audio.written();
        double gain = std::pow(10.0, params_[kGain].load() / 20.0) * std::pow(10.0, globalGainDb_.load() / 20.0);
        if (!primed_) {
            // (re)start once a jitter buffer's worth has arrived since the stream stopped
            if (w >= unprimedAt_ + (uint64_t)target) { pos_ = (double)w - target; primed_ = true; ratioTrim_ = 1.0; }
        } else {
            double avail = (double)w - pos_;
            if (avail < 4) { primed_ = false; unprimedAt_ = w; }                       // the stream stopped (XP asleep)
            else if (avail > target * 4) pos_ = (double)w - target;                     // far behind: catch up
            else ratioTrim_ = 0.999 * ratioTrim_ + 0.001 * (1.0 + 0.02 * (avail - target) / target);
        }
        double step = 44100.0 / sr_ * (primed_ ? ratioTrim_ : 1.0);
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
        if (ahead > 0.35) {
            // a host this far ahead of the clock is rendering offline: first let XP finish waking (and link up),
            // then keep pace with it
            for (int k = 0; k < 600 && !(machine_.phase == Machine::Running && machine_.linked) &&
                            machine_.phase != Machine::Failed && machine_.phase != Machine::Off; k++)
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            if (machine_.phase == Machine::Running) {
                if (!offlineSynced_) {   // count from now: the time spent waking is not part of the song
                    offlineSynced_ = true;
                    wallStart_ = Machine::now() - (double)processed_ / sr_ + 0.25;
                } else std::this_thread::sleep_for(std::chrono::duration<double>(ahead - 0.25));
            }
        }
    }

private:
    enum { kGain, kAttack, kDecay, kSustain, kRelease, kVelocity, kBend, kTranspose, kParamCount };
    // measured: MIDI in -> first sample of that note in XP's stream, plus the jitter buffer (README: Timing)
#ifdef _WIN32
    static constexpr int kLatencyMs = 370, kJitterMs = 45;
#else
    static constexpr int kLatencyMs = 200, kJitterMs = 45;
#endif

    struct LayerMsg { int layer, first, count, rate, frames; };

    void sendCmds(const Cmd *c, int n)
    {
        char b[96];
        for (int i = 0; i < n; i++) if (proto::cmd(b, sizeof b, c[i]) > 0) { machine_.send(b); sentNotes_++; }
    }

    void globalsToParams(const Dna &d)
    {
        params_[kAttack] = (float)d.g.attack; params_[kDecay] = (float)d.g.decay; params_[kSustain] = (float)d.g.sustain;
        params_[kRelease] = (float)d.g.release; params_[kVelocity] = (float)d.g.velocity; params_[kBend] = (float)d.g.bendRange;
        globalGainDb_ = (float)d.g.gainDb;
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
        Dna *nd = new Dna(d);
        Dna *old = pendingDna_.exchange(nd);
        delete old;
        dnaDirty_ = true;
    }

    // the plugin's own thread: guest replies, parameters, and what to tell the guest
    void pump()
    {
        bool sentDna = false, sentGo = false;
        double lastLog = 0;
        std::string lastSentDna, lastEnv;
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
                applyDna(d, false);
            }
            std::string line;
            while (machine_.popReply(line)) {
                proto::Reply r = proto::parse(line);
                if (r.kind == proto::Reply::Layer) layerMsgs_.push({r.layer, r.first, r.count, r.rate, r.frames});
                else if (r.kind == proto::Reply::End) layerMsgs_.push({-1, r.rec, 0, 0, 0});
                else if (r.kind == proto::Reply::Edit) {
                    // changed inside XP: it is already built there; adopt it
                    Dna d = parse(r.text);
                    {
                        std::lock_guard<std::mutex> g(mu_);
                        dna_ = d.canonical;
                        parsed_ = d;
                        pendingEdit_ = d.canonical;
                        lastSentDna = d.layersText();
                    }
                    globalsToParams(d);
                    Dna *nd = new Dna(d);
                    delete pendingDna_.exchange(nd);
                }
            }
            if (Machine::now() - lastLog > 2 && machine_.phase == Machine::Running) {
                lastLog = Machine::now();
                Machine::log("audio: %llu frames in, primed %d, notes sent %d", (unsigned long long)machine_.audio.written(), (int)primed_, sentNotes_.load());
            }
            if (!machine_.linked) { sentDna = false; continue; }
            if (!sentDna || dnaDirty_.exchange(false)) {
                Dna d;
                { std::lock_guard<std::mutex> g(mu_); d = parsed_; }
                char b[96];
                // the buffers are rebuilt only when the layers changed; the envelope is just a line
                if (!sentDna || d.layersText() != lastSentDna) {
                    std::string full = "dna " + d.canonical + "\n";
                    machine_.sendLong(full);
                    lastSentDna = d.layersText();
                }
                proto::env(b, sizeof b, d.g);
                if (!sentDna || lastEnv != b) { machine_.send(b); lastEnv = b; }
                globalGainDb_ = (float)d.g.gainDb;
                sentDna = true;
            }
            if (wantGo_ && !sentGo) { machine_.send("go\n"); sentGo = true; }
        }
    }

    Machine machine_;
    Voices voices_{48000};
    Dna *cur_ = nullptr;
    std::atomic<Dna *> pendingDna_{nullptr};
    Spsc<Dna *> trash_{64};
    Spsc<LayerMsg> layerMsgs_{256};
    std::thread pump_;
    std::atomic<bool> quit_{false}, paramsDirty_{false}, dnaDirty_{false}, wantGo_{false};
    std::atomic<float> params_[kParamCount] = {{0}, {0}, {0}, {100}, {120}, {100}, {2}, {0}};
    std::atomic<float> globalGainDb_{0};
    std::atomic<int> sentNotes_{0};
    mutable std::mutex mu_;
    std::string dna_, pendingEdit_;
    Dna parsed_;
    double sr_ = 48000, pos_ = 0, ratioTrim_ = 1, wallStart_ = 0, lastRun_ = 0;
    bool primed_ = false, offlineSynced_ = false;
    uint64_t sampleClock_ = 0, processed_ = 0, unprimedAt_ = 0;
    int8_t noteMap_[128];

    DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(BasiliskSynthPlugin)
};

Plugin *createPlugin() { return new BasiliskSynthPlugin(); }

END_NAMESPACE_DISTRHO

SynthHost *synthHostOf(void *p) { return p ? static_cast<DISTRHO_NAMESPACE::BasiliskSynthPlugin *>(static_cast<DISTRHO_NAMESPACE::Plugin *>(p)) : nullptr; }
