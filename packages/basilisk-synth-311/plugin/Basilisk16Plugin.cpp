/*
 * BASILISK 16 - the plugin side.
 *
 * Every instance runs its own Windows for Workgroups 3.11 (the engine thread: DOSBox Pure with the BSYN card),
 * resumed from the snapshot in the bundle. Sixteen real Sound Recorders play the notes; this side only decides
 * which recorder plays (the shared voice allocator, packages/basilisk-synth/core), tells Windows the rate and the
 * volume, and takes the card's DAC output. Every note is stamped with a DAC sample number, so it starts exactly
 * a fixed latency after the host asked for it; that latency is reported to the host.
 */
#include "DistrhoPlugin.hpp"
#include "DistrhoPluginUtils.hpp"
#include "Shared.hpp"
#include "../engine/engine.h"
#include "../../basilisk-synth/core/dna.h"
#include "../../basilisk-synth/core/voices.h"
#include "../../basilisk-synth/core/proto.h"
#include "../../basilisk-synth/core/state.h"

#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/stat.h>
#include <unistd.h>
#endif

START_NAMESPACE_DISTRHO

using namespace bsynth;

enum { pAttack, pDecay, pSustain, pRelease, pVelocity, pBend, pGain, pTranspose, pCount };
static const char *const kGlobalLetter = "ADSRVBG";

struct Preset { const char *name, *dna; };
static const Preset kPresets[] = {
    {"Ding Piano", "ding#16;R250"},
    {"Chime Octaves", "chimesH0,12;R500"},
    {"Telephone Choir", "ringinU3~12;A60S90R700"},
    {"Reverse Ding Swell", "dingR;A10R300"},
    {"Echo Bells", "chimesE+;R900"},
    {"Slow Ring Pad", "ringout<<E;A400D300S80R1500"},
    {"Fifth Stack", "dingH0,7,12;R300"},
    {"Major Ding", "dingH0,4,7;R250"},
    {"Ding and Chimes", "ding#8/chimes#8T12;R350"},
    {"Chopped Ring", "ringin@50]>;R120"},
    {"Insert and Mix", "dingIchimesMringin;R300"},
    {"Triple Echo Reverse", "chimesEEER-;A20R1000"},
    {"Bass Ding", "ding<T-12;R250"},
    {"Detuned Unison", "dingU4~25;R300"},
    {"Ring Out Octaves", "ringout>H0,12,24;R160"},
    {"Copy Paste Stutter", "ding@30]CPPP;R160"},
};
static constexpr uint32_t kPresetCount = sizeof(kPresets) / sizeof(kPresets[0]);

static double nowSec()
{
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

static bool copyFile(const std::string &from, const std::string &to)
{
    FILE *a = std::fopen(from.c_str(), "rb");
    if (!a) return false;
    FILE *b = std::fopen(to.c_str(), "wb");
    if (!b) { std::fclose(a); return false; }
    char buf[65536]; size_t n;
    while ((n = std::fread(buf, 1, sizeof buf, a)) > 0) std::fwrite(buf, 1, n, b);
    std::fclose(a); std::fclose(b);
    return true;
}

static std::string tempDir()
{
#ifdef _WIN32
    char t[MAX_PATH]; GetTempPathA(MAX_PATH, t);
    std::string s = t;
#else
    const char *t = std::getenv("TMPDIR");
    std::string s = t && *t ? t : "/tmp/";
#endif
    if (!s.empty() && s.back() != '/' && s.back() != '\\') s += '/';
    return s;
}

static int processId()
{
#ifdef _WIN32
    return (int)GetCurrentProcessId();
#else
    return (int)getpid();
#endif
}

static std::atomic<int> gInstanceCounter{0};

class Basilisk16 : public Plugin
{
public:
    Basilisk16()
        : Plugin(pCount, kPresetCount, 1)
    {
        created_ = nowSec();
        if (const char *d = std::getenv("BASILISK16_TEST_DUMP_DAC")) if (*d && !isDummyInstance()) dump_ = std::fopen(d, "wb");
        sh_.S = (bshm *)std::calloc(1, sizeof(bshm));
        bshm *S = sh_.S;
        S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING;
        S->lead = kLead; S->realtime = 0;
        setDna(kDefaultDna, false);
        updateLatency();
        if (!isDummyInstance()) start();
    }

    ~Basilisk16() override
    {
        quit_ = true;
        if (worker_.joinable()) worker_.join();
        if (engine_) bs_engine_stop(engine_);
        engine_ = nullptr;
        cleanupTemp();
        if (dump_) std::fclose(dump_);
        std::free(sh_.S);
    }

    Basilisk16Shared *shared() { return &sh_; }

protected:
    const char *getLabel() const override { return "Basilisk16"; }
    const char *getDescription() const override
    {
        return "Sixteen Windows 3.11 Sound Recorders assembled into one instrument. The sound is Sound Recorder's own, "
               "played by Windows for Workgroups 3.11 in an emulated PC; a DNA string of Sound Recorder commands shapes it.";
    }
    const char *getMaker() const override { return "William Sharkey"; }
    const char *getHomePage() const override { return "https://williamsharkey.com/basilisk-download.html"; }
    const char *getLicense() const override { return "GPL-2.0-or-later"; }
    uint32_t getVersion() const override { return d_version(1, 0, 0); }

    void initParameter(uint32_t i, Parameter &p) override
    {
        p.hints = kParameterIsAutomatable;
        switch (i) {
        case pAttack: p.name = "Attack"; p.symbol = "attack"; p.unit = "ms"; p.ranges = ParameterRanges(0, 0, 5000); break;
        case pDecay: p.name = "Decay"; p.symbol = "decay"; p.unit = "ms"; p.ranges = ParameterRanges(0, 0, 5000); break;
        case pSustain: p.name = "Sustain"; p.symbol = "sustain"; p.unit = "%"; p.ranges = ParameterRanges(100, 0, 100); break;
        case pRelease: p.name = "Release"; p.symbol = "release"; p.unit = "ms"; p.ranges = ParameterRanges(120, 0, 5000); break;
        case pVelocity: p.name = "Velocity"; p.symbol = "velocity"; p.unit = "%"; p.ranges = ParameterRanges(100, 0, 100); break;
        case pBend: p.name = "Bend Range"; p.symbol = "bend"; p.unit = "st"; p.ranges = ParameterRanges(2, 0, 24); p.hints |= kParameterIsInteger; break;
        case pGain: p.name = "Output Gain"; p.symbol = "gain"; p.unit = "dB"; p.ranges = ParameterRanges(0, -24, 12); p.hints |= kParameterIsInteger; break;
        case pTranspose: p.name = "Transpose"; p.symbol = "transpose"; p.unit = "st"; p.ranges = ParameterRanges(0, -24, 24); p.hints |= kParameterIsInteger; break;
        }
    }

    float getParameterValue(uint32_t i) const override { return i < pCount ? param_[i].load() : 0.f; }

    void setParameterValue(uint32_t i, float v) override
    {
        if (i >= pCount) return;
        if (param_[i].load() == v) return;
        param_[i] = v;
        paramsDirty_ = true;
    }

    void initProgramName(uint32_t i, String &name) override { name = kPresets[i].name; }
    void loadProgram(uint32_t i) override { if (i < kPresetCount) setDna(kPresets[i].dna, true); }

    void initState(uint32_t, State &st) override
    {
        st.key = "state";
        st.defaultValue = bsynth::State().write().c_str();
        st.label = "Sound";
        st.hints = kStateIsOnlyForDSP;
    }

    String getState(const char *key) const override
    {
        if (std::strcmp(key, "state")) return String();
        std::lock_guard<std::mutex> l(mtx_);
        bsynth::State s; s.dna = dnaText_;
        return String(s.write().c_str());
    }

    void setState(const char *key, const char *value) override
    {
        if (std::strcmp(key, "state")) return;
        bsynth::State s;
        if (s.read(value ? value : "")) setDna(s.dna, true);
    }

    void sampleRateChanged(double) override { updateLatency(); }
    void bufferSizeChanged(uint32_t) override { updateLatency(); }
    void activate() override { dacPos_ = -1; }

    void run(const float **, float **out, uint32_t frames, const MidiEvent *ev, uint32_t nev) override
    {
        bshm *S = sh_.S;
        float *L = out[0], *R = out[1];
        S->host_beat++;
        audioAlive_ = nowSec();
        const double sr = getSampleRate(), ratio = 48000.0 / sr;
        housekeeping();
        // a host that renders right after creating us (a command-line renderer) waits for the machine to resume
        if (engine_ && S->state < BS_RUNNING && nowSec() - created_ < 3.0)
            for (int k = 0; k < 3000 && S->state < BS_RUNNING && !quit_; k++) std::this_thread::sleep_for(std::chrono::milliseconds(1));
        if (S->state < BS_RUNNING || S->state == BS_FAILED) {
            std::memset(L, 0, frames * sizeof(float)); std::memset(R, 0, frames * sizeof(float));
            return;
        }
        S->realtime = 1;
        // Windows is rebuilding the recorders (a new DNA): notes would be dropped, so wait for it (a preset change
        // costs a moment of silence; an offline render stays exact)
        for (int k = 0; k < 5000 && building_ && S->state != BS_FAILED && !S->quit && !quit_; k++)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        if (dacPos_ < 0 || (double)S->dac_w > dacPos_ + BSHM_RING / 2) dacPos_ = (double)S->dac_w;   // (re)sync
        // the notes of this block: each one is stamped with the DAC sample at which it must sound
        for (uint32_t i = 0; i < nev; i++) {
            const uint8_t *d = ev[i].size > 4 ? ev[i].dataExt : ev[i].data;
            if (ev[i].size < 2) continue;
            const uint64_t at = (uint64_t)(dacPos_ + ev[i].frame * ratio) + kLatency48;
            const uint8_t st = d[0] & 0xF0;
            Cmd c[kMaxCmds]; int n = 0;
            if (st == 0x90 && ev[i].size >= 3 && d[2] > 0) n = voices_.noteOn(d[1], d[2], at, c);
            else if (st == 0x80 || (st == 0x90 && ev[i].size >= 3)) n = voices_.noteOff(d[1], at, c);
            else if (st == 0xB0 && ev[i].size >= 3) {
                if (d[1] == 64) n = voices_.sustain(d[2] >= 64, at, c);
                else if (d[1] == 120 || d[1] == 123) n = voices_.allOff(c);
            } else if (st == 0xE0 && ev[i].size >= 3) {
                const int v = (d[1] | (d[2] << 7)) - 8192;
                voices_.bend(v / 8192.0);
            }
            for (int k = 0; k < n; k++) {
                char line[64];
                proto::cmd(line, sizeof line, c[k]);
                line[std::strlen(line) - 1] = 0;
                sendLine(line, ++nextId_, at);
            }
        }
        // wait for the machine if it is behind (offline rendering runs faster than real time)
        const double need = dacPos_ + frames * ratio + 3;
        for (int k = 0; k < 400 && (double)S->dac_w < need && S->state != BS_FAILED && !S->quit && !quit_; k++)
            std::this_thread::sleep_for(std::chrono::microseconds(500));
        if ((double)S->dac_w < need) S->underruns++;
        const float g = gain_;
        for (uint32_t i = 0; i < frames; i++) {
            const double p = dacPos_;
            const int64_t k = (int64_t)std::floor(p);
            const float f = (float)(p - (double)k);
            if ((double)(k + 2) >= (double)S->dac_w) { L[i] = R[i] = 0.f; }
            else {
                for (int ch = 0; ch < 2; ch++) {
                    auto at = [&](int64_t j) { return S->ring[(uint32_t)((uint64_t)j % BSHM_RING) * 2 + ch]; };
                    const float y0 = at(k - 1), y1 = at(k), y2 = at(k + 1), y3 = at(k + 2);
                    const float c1 = 0.5f * (y2 - y0), c2 = y0 - 2.5f * y1 + 2.f * y2 - 0.5f * y3, c3 = 0.5f * (y3 - y0) + 1.5f * (y1 - y2);
                    const float y = ((c3 * f + c2) * f + c1) * f + y1;
                    (ch ? R : L)[i] = y * g;
                }
            }
            if (dump_) { float d2[2] = {S->ring[(uint32_t)((uint64_t)k % BSHM_RING) * 2], S->ring[(uint32_t)((uint64_t)k % BSHM_RING) * 2 + 1]}; std::fwrite(d2, 4, 2, dump_); }
            dacPos_ += ratio;
        }
        S->host_r = (uint64_t)std::max(0.0, dacPos_ - 4);
    }

private:
    // the card runs at 48 kHz; the engine keeps kLead DAC samples ahead of the host, and every note is stamped
    // kLatency48 samples ahead: enough for Windows to press Play before the card gets there
    static constexpr uint32_t kLead = 1024;
    static constexpr uint32_t kLatency48 = kLead + 1536;

    Basilisk16Shared sh_;
    bs_engine *engine_ = nullptr;
    std::thread worker_;
    std::atomic<bool> quit_{false};
    std::string tmp_, coreCopy_, conf_;

    mutable std::mutex mtx_;          // guards the fields below
    std::string dnaText_;
    Dna dnaForAudio_;
    bool dnaPending_ = false;          // audio thread: adopt dnaForAudio_
    std::vector<LayerInfo> pendLayers_; std::vector<int> pendLayerIdx_;
    std::vector<int> pendEnds_;
    LayerInfo layerCache_[kMaxLayers];
    std::string cacheSig_;
    bool dnaToGuest_ = false;          // worker: send the DNA to Windows

    std::atomic<float> param_[pCount];
    std::atomic<bool> paramsDirty_{false};
    std::atomic<bool> building_{false};
    std::atomic<double> audioAlive_{0};
    double created_ = 0;
    FILE *dump_ = nullptr;     // test: BASILISK16_TEST_DUMP_DAC=file writes the card's DAC samples behind each output sample

    // audio thread only
    Voices voices_{48000};
    double dacPos_ = -1;
    uint32_t nextId_ = 0;
    float gain_ = 1.f;

    void updateLatency() { setLatency((uint32_t)std::lround(kLatency48 * getSampleRate() / 48000.0)); }

    static std::string sigOf(const Dna &d)
    {
        std::string s;
        for (auto &L : d.layers) {
            s += std::to_string(L.source) + ":" + std::to_string(L.first) + ":" + std::to_string(L.count) + ":";
            for (auto &st : L.steps) { s += st.op; s += std::to_string(st.arg) + "." + std::to_string(st.sound); }
            s += "|";
        }
        return s;
    }

    // a new DNA from a preset, the state, a parameter or (fromGuest) Windows itself
    void setDna(const std::string &text, bool toGuest, bool fromGuest = false)
    {
        Dna d = parse(text);
        std::lock_guard<std::mutex> l(mtx_);
        dnaText_ = d.canonical;
        dnaForAudio_ = d;
        dnaPending_ = true;
        if (toGuest && !fromGuest) dnaToGuest_ = true;
        const std::string sig = sigOf(d);
        if (sig != cacheSig_) {
            for (auto &c : layerCache_) c = LayerInfo();
            // the snapshot's machine holds DING in all sixteen recorders: the default plays before Windows replies
            if (sig == sigOf(parse(kDefaultDna))) layerCache_[0] = LayerInfo{0, 16, 22050, 11466, true};
            cacheSig_ = sig;
        }
        param_[pAttack] = (float)d.g.attack; param_[pDecay] = (float)d.g.decay; param_[pSustain] = (float)d.g.sustain;
        param_[pRelease] = (float)d.g.release; param_[pVelocity] = (float)d.g.velocity; param_[pBend] = (float)d.g.bendRange;
        param_[pGain] = (float)d.g.gainDb; param_[pTranspose] = d.layers.empty() ? 0.f : (float)d.layers[0].transpose;
        paramsDirty_ = false;
    }

    // audio thread, start of every block: adopt what the worker prepared (never waits for it)
    void housekeeping()
    {
        if (!mtx_.try_lock()) return;
        if (dnaPending_) {
            Cmd c[1];
            voices_.setDna(dnaForAudio_, c);
            for (int i = 0; i < kMaxLayers; i++)
                if (layerCache_[i].known) voices_.setLayerInfo(i, layerCache_[i].first, layerCache_[i].count, layerCache_[i].rate, layerCache_[i].frames);
            gain_ = (float)std::pow(10.0, dnaForAudio_.g.gainDb / 20.0);
            dnaPending_ = false;
        }
        for (size_t i = 0; i < pendLayers_.size(); i++)
            voices_.setLayerInfo(pendLayerIdx_[i], pendLayers_[i].first, pendLayers_[i].count, pendLayers_[i].rate, pendLayers_[i].frames);
        pendLayers_.clear(); pendLayerIdx_.clear();
        for (int r : pendEnds_) voices_.end(r);
        pendEnds_.clear();
        mtx_.unlock();
    }

    // one line to Windows, as packets of the card's mailbox: [type<<8|words][id lo][id hi][text...]
    void sendLine(const char *text, uint32_t id, uint64_t at)
    {
        bshm *S = sh_.S;
        const int len = (int)std::strlen(text);
        while (sh_.shmLock.test_and_set(std::memory_order_acquire)) {}
        int pos = 0;
        do {
            const int m = len - pos > 240 ? 240 : len - pos;
            const bool last = pos + m >= len;
            if (S->ev_w - S->ev_r >= BSHM_EV) break;
            bshm_ev &e = S->ev[S->ev_w % BSHM_EV];
            const int words = 3 + (m + 1) / 2;
            e.w[0] = (uint16_t)(((last ? 4 : 8) << 8) | words);
            e.w[1] = (uint16_t)(last ? id : 0); e.w[2] = (uint16_t)((last ? id : 0) >> 16);
            for (int k = 0; k < (m + 1) / 2; k++) {
                const uint8_t a = (uint8_t)text[pos + 2 * k], b = 2 * k + 1 < m ? (uint8_t)text[pos + 2 * k + 1] : 0;
                e.w[3 + k] = (uint16_t)(a | (b << 8));
            }
            e.n = (uint32_t)words; e.id = last ? id : 0; e.at = last ? at : 0;
            __sync_synchronize();
            S->ev_w++;
            pos += m;
        } while (pos < len);
        sh_.shmLock.clear(std::memory_order_release);
    }

    // ------------------------------------------------------------------ start, stop
    void start()
    {
        const char *bundle = getBundlePath();
        const char *res = bundle ? getResourcePath(bundle) : nullptr;
        if (!res) { status("BASILISK 16: the machine files were not found next to the plugin."); sh_.S->state = BS_FAILED; return; }
        std::string machine = std::string(res) + "/machine/";
#ifdef _WIN32
        const char *coreName = "dosbox_pure_libretro.dll";
#else
        const char *coreName = "dosbox_pure_libretro.dylib";
#endif
        tmp_ = tempDir() + "basilisk16-" + std::to_string(processId()) + "-" + std::to_string(++gInstanceCounter);
#ifdef _WIN32
        CreateDirectoryA(tmp_.c_str(), nullptr);
#else
        mkdir(tmp_.c_str(), 0700);
#endif
        // a private copy of the core: each instance its own machine, even in one process
        coreCopy_ = tmp_ + "/" + coreName;
        conf_ = tmp_ + "/w31.conf";
        if (!copyFile(machine + coreName, coreCopy_)) { status("BASILISK 16: cannot copy the emulator core."); sh_.S->state = BS_FAILED; return; }
        {
            FILE *f = std::fopen((machine + "w31.conf").c_str(), "rb");
            FILE *o = std::fopen(conf_.c_str(), "wb");
            if (!f || !o) { if (f) std::fclose(f); if (o) std::fclose(o); status("BASILISK 16: cannot write the machine settings."); sh_.S->state = BS_FAILED; return; }
            char line[1024];
            std::string mdir = machine.substr(0, machine.size() - 1);
#ifdef _WIN32
            for (auto &ch : mdir) if (ch == '/') ch = '\\';
#endif
            while (std::fgets(line, sizeof line, f)) {
                std::string s = line;
                const size_t p = s.find("@MACHINE@");
                if (p != std::string::npos) s.replace(p, 9, "\"" + mdir + "\"");
                const size_t q = s.find("@DRIVE@");
                if (q != std::string::npos) s.replace(q, 7, "\"" + mdir + "/drive\"");
                std::fputs(s.c_str(), o);
            }
            std::fclose(f); std::fclose(o);
        }
        const char *logEnv = std::getenv("BASILISK16_LOG");
        status("Starting Windows for Workgroups 3.11...");
        // the snapshot is per CPU (the emulator's saved state follows the host's data layout)
#if defined(__APPLE__) && defined(__aarch64__)
        const char *stateName = "w31-arm64.state";
#elif defined(__APPLE__)
        const char *stateName = "w31-x86_64.state";
#else
        const char *stateName = "w31.state";
#endif
        engine_ = bs_engine_start(sh_.S, coreCopy_.c_str(), conf_.c_str(), (machine + stateName).c_str(), nullptr,
                                  logEnv && *logEnv ? logEnv : nullptr);
        worker_ = std::thread([this] { work(); });
    }

    void cleanupTemp()
    {
        if (tmp_.empty()) return;
        std::remove(coreCopy_.c_str());
        std::remove(conf_.c_str());
#ifdef _WIN32
        RemoveDirectoryA(tmp_.c_str());
#else
        rmdir(tmp_.c_str());
#endif
    }

    void status(const char *s) { std::snprintf(sh_.status, sizeof sh_.status, "%s", s); }

    // ------------------------------------------------------------------ the worker: Windows' replies, hello, DNA
    void work()
    {
        bshm *S = sh_.S;
        std::vector<uint16_t> words;
        std::string frag;
        bool hello = false;
        uint32_t lastState = 0;
        const char *stopEnv = std::getenv("BASILISK16_TEST_STOP_EMULATOR");   // test: freeze the machine, prove the silence
        while (!quit_) {
            if (stopEnv && S->state >= BS_RUNNING && !S->quit) S->quit = 1;
            // the host may not be running audio: keep the heartbeat ourselves so the machine paces itself
            if (nowSec() - audioAlive_.load() > 0.2) { S->realtime = 0; S->host_beat++; }
            if (S->state != lastState) {
                lastState = S->state;
                if (S->state == BS_FAILED) status(S->error);
            }
            if (!hello && S->state >= BS_RUNNING && S->state != BS_FAILED) {
                hello = true;
                char b[128];
                std::time_t t = std::time(nullptr);
                std::tm lt;
#ifdef _WIN32
                localtime_s(&lt, &t);
#else
                localtime_r(&t, &lt);
#endif
                proto::hi(b, sizeof b); trimSend(b);
                proto::time(b, sizeof b, lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec); trimSend(b);
                proto::go(b, sizeof b); trimSend(b);
                std::lock_guard<std::mutex> l(mtx_);
                dnaToGuest_ = true;
            }
            if (paramsDirty_.exchange(false)) {
                std::string d;
                { std::lock_guard<std::mutex> l(mtx_); d = dnaText_; }
                for (int i = 0; i < 7; i++) d = setGlobal(d, kGlobalLetter[i], (int)std::lround(param_[i].load()));
                d = setLayerGene(d, 0, 'T', (int)std::lround(param_[pTranspose].load()));
                bool changed;
                { std::lock_guard<std::mutex> l(mtx_); changed = d != dnaText_; }
                if (changed) setDna(d, true);
            }
            bool send = false; std::string d; Globals g;
            {
                std::lock_guard<std::mutex> l(mtx_);
                if (hello && dnaToGuest_) { send = true; dnaToGuest_ = false; d = dnaText_; g = dnaForAudio_.g; }
            }
            if (send) {
                std::string line = "dna " + d;
                building_ = true;
                sendLine(line.c_str(), 0, 0);
                char b[96]; proto::env(b, sizeof b, g); trimSend(b);
            }
            // Windows' replies
            while (S->rep_r != S->rep_w) {
                words.push_back((uint16_t)S->rep[S->rep_r % BSHM_REP]);
                __sync_synchronize();
                S->rep_r++;
            }
            size_t i = 0;
            while (i < words.size()) {
                const int n = words[i] & 0xFF ? words[i] & 0xFF : 1;
                if (i + n > words.size()) break;
                const int ty = words[i] >> 8;
                if (ty == 3 || ty == 7) {
                    for (int k = 1; k < n; k++) {
                        const char a = (char)(words[i + k] & 0xFF), b = (char)(words[i + k] >> 8);
                        if (a) frag += a; if (a && b) frag += b;
                    }
                    if (ty == 3) { onLine(frag); frag.clear(); }
                }
                i += n;
            }
            words.erase(words.begin(), words.begin() + i);
            std::this_thread::sleep_for(std::chrono::milliseconds(4));
        }
    }

    void trimSend(char *b)
    {
        size_t n = std::strlen(b);
        if (n && b[n - 1] == '\n') b[n - 1] = 0;
        sendLine(b, 0, 0);
    }

    void onLine(const std::string &line)
    {
        proto::Reply r = proto::parse(line);
        switch (r.kind) {
        case proto::Reply::Ready: status(""); break;
        case proto::Reply::Built: building_ = false; break;
        case proto::Reply::Layer: {
            std::lock_guard<std::mutex> l(mtx_);
            if (r.layer >= 0 && r.layer < kMaxLayers) {
                LayerInfo li{r.first, r.count, r.rate, r.frames, true};
                layerCache_[r.layer] = li;
                pendLayers_.push_back(li); pendLayerIdx_.push_back(r.layer);
            }
            break; }
        case proto::Reply::End: { std::lock_guard<std::mutex> l(mtx_); pendEnds_.push_back(r.rec); break; }
        case proto::Reply::Edit: setDna(r.text, false, true); break;   // Windows already rebuilt; the host adopts it
        default: break;
        }
    }

    DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(Basilisk16)
};

Plugin *createPlugin() { return new Basilisk16(); }

Basilisk16Shared *basilisk16Shared(void *plugin) { return plugin ? static_cast<Basilisk16 *>(plugin)->shared() : nullptr; }

END_NAMESPACE_DISTRHO
