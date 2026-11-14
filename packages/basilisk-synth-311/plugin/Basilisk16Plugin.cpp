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
#include <sstream>
#include "V3Voice.h"
#include "V3Alloc.h"

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

// (new parameters go at the end: hosts store automation by index)
enum { pAttack, pDecay, pSustain, pRelease, pVelocity, pBend, pGain, pTranspose, pMacro1, pMacro2, pMacro3, pMacro4,
       pKey, pScale, pUsePreset, pSnap, pRemap, pAnchor, pLabels, pCount };   // key and scale: PRESET-ENGINE-2 18.2
static const char *const kGlobalLetter = "ADSRVBG";

#include "presets_gen.h"   // kPresets[]: "Category: Name" + DNA (tools/make_presets311.py; the same list as \\PRESETS.TSV in Windows)
static constexpr uint32_t kPresetCount = sizeof(kPresets) / sizeof(kPresets[0]);

static double nowSec()
{
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}

// Windows: no inheritable handle may exist on these files, even for a moment: another plugin in the same host may
// start a process (BASILISK SYNTH starts QEMU), which would inherit it and keep the core locked.
static bool writeText(const std::string &path, const std::string &text)
{
#ifdef _WIN32
    HANDLE h = CreateFileA(path.c_str(), GENERIC_WRITE, 0, nullptr /* not inheritable */, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    DWORD n = 0;
    const BOOL ok = WriteFile(h, text.data(), (DWORD)text.size(), &n, nullptr);
    CloseHandle(h);
    return ok && n == text.size();
#else
    FILE *f = std::fopen(path.c_str(), "wb");
    if (!f) return false;
    const bool ok = std::fwrite(text.data(), 1, text.size(), f) == text.size();
    std::fclose(f);
    return ok;
#endif
}

static bool copyFile(const std::string &from, const std::string &to)
{
#ifdef _WIN32
    return CopyFileA(from.c_str(), to.c_str(), FALSE) != 0;
#endif
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

#ifdef _WIN32
// Windows keeps a loaded DLL's file locked, and the core copy can outlive its instance for a moment (or for good, if
// the host crashed). Every new instance removes the folders of processes that are gone.
static void sweepTemp(const std::string &tmp)
{
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA((tmp + "basilisk16-*").c_str(), &fd);
    if (h == INVALID_HANDLE_VALUE) return;
    do {
        if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) continue;
        const DWORD pid = (DWORD)std::strtoul(fd.cFileName + 11, nullptr, 10);
        if (!pid || pid == GetCurrentProcessId()) continue;
        HANDLE p = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
        if (p) {   // alive, and the same process (a reused pid started after the folder was made is not)
            DWORD code = 0; FILETIME c, x, k, u;
            bool alive = GetExitCodeProcess(p, &code) && code == STILL_ACTIVE;
            if (alive && GetProcessTimes(p, &c, &x, &k, &u) && CompareFileTime(&c, &fd.ftCreationTime) > 0) alive = false;
            CloseHandle(p);
            if (alive) continue;
        } else if (GetLastError() == ERROR_ACCESS_DENIED) continue;   // alive, someone else's
        const std::string dir = tmp + fd.cFileName;
        WIN32_FIND_DATAA f2;
        HANDLE h2 = FindFirstFileA((dir + "\\*").c_str(), &f2);
        if (h2 != INVALID_HANDLE_VALUE) {
            do { if (!(f2.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) DeleteFileA((dir + "\\" + f2.cFileName).c_str()); } while (FindNextFileA(h2, &f2));
            FindClose(h2);
        }
        RemoveDirectoryA(dir.c_str());
    } while (FindNextFileA(h, &fd));
    FindClose(h);
}
#endif

class Basilisk16 : public Plugin
{
public:
    Basilisk16()
        : Plugin(pCount, kPresetCount, 1)
    {
        created_ = nowSec();
        vo_.reserve(256);   // the audio thread never allocates for an ordinary chord
        setKeyParams(b16v3::KeyParams());
        testLive_ = std::getenv("BASILISK16_TEST_LIVE") != nullptr;   // test: take the live path in an offline host
        if (const char *d = std::getenv("BASILISK16_TEST_DUMP_DAC")) if (*d && !isDummyInstance()) dump_ = std::fopen(d, "wb");
        if (const char *d = std::getenv("BASILISK16_TRACE")) if (*d && !isDummyInstance()) {
            std::string f = std::string(d) + "/trace-" + std::to_string(processId()) + "-" + std::to_string(gInstanceCounter.load() + 1) + ".txt";
            trace_ = std::fopen(f.c_str(), "w");
            if (trace_) setvbuf(trace_, nullptr, _IONBF, 0);
        }
        sh_.S = (bshm *)std::calloc(1, sizeof(bshm));
        bshm *S = sh_.S;
        S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING;
        S->lead = kLead; S->realtime = 0;
        loadLibraryNames();
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
        if (trace_) std::fclose(trace_);
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
    uint32_t getVersion() const override { return d_version(1, 2, 1); }

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
        case pKey: {   // the key and scale (PRESET-ENGINE-2 18.2): host-side pitches only, never the DNA
            static const char *nm[12] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
            static ParameterEnumerationValue ev[12];
            for (int k = 0; k < 12; k++) { ev[k].value = (float)k; ev[k].label = nm[k]; }
            p.name = "Key"; p.symbol = "key"; p.ranges = ParameterRanges(0, 0, 11); p.hints |= kParameterIsInteger;
            p.enumValues.count = 12; p.enumValues.restrictedMode = true; p.enumValues.values = ev; p.enumValues.deleteLater = false;
            break; }
        case pScale: {
            const auto &lib = bsynth3::scaleLibrary();
            static std::vector<ParameterEnumerationValue> ev;
            if (ev.empty()) for (const auto &x : lib) { ParameterEnumerationValue v; v.value = (float)x.id; v.label = x.label; ev.push_back(v); }
            p.name = "Scale"; p.symbol = "scale"; p.ranges = ParameterRanges(0, 0, lib.empty() ? 0 : (float)lib.back().id); p.hints |= kParameterIsInteger;
            p.enumValues.count = (uint32_t)ev.size(); p.enumValues.restrictedMode = true; p.enumValues.values = ev.data(); p.enumValues.deleteLater = false;
            break; }
        case pUsePreset: p.name = "Use Preset Scale"; p.symbol = "usepresetscale"; p.ranges = ParameterRanges(0, 0, 1); p.hints |= kParameterIsBoolean | kParameterIsInteger; break;
        case pSnap: {
            static ParameterEnumerationValue ev[4];
            static const char *nm[4] = {"Nearest", "Down", "Up", "Off"};
            for (int k = 0; k < 4; k++) { ev[k].value = (float)(k + 1); ev[k].label = nm[k]; }
            p.name = "Snap"; p.symbol = "snap"; p.ranges = ParameterRanges(1, 1, 4); p.hints |= kParameterIsInteger;
            p.enumValues.count = 4; p.enumValues.restrictedMode = true; p.enumValues.values = ev; p.enumValues.deleteLater = false;
            break; }
        case pRemap: p.name = "Remap Keys"; p.symbol = "remap"; p.ranges = ParameterRanges(0, 0, 1); p.hints |= kParameterIsBoolean | kParameterIsInteger; break;
        case pAnchor: p.name = "Remap Anchor"; p.symbol = "anchor"; p.ranges = ParameterRanges(60, 0, 127); p.hints |= kParameterIsInteger; break;
        case pLabels: {
            static ParameterEnumerationValue ev[5];
            static const char *nm[5] = {"None", "Degrees", "Sargam", "Names", "Cents"};
            for (int k = 0; k < 5; k++) { ev[k].value = (float)k; ev[k].label = nm[k]; }
            p.name = "Key Labels"; p.symbol = "keylabels"; p.ranges = ParameterRanges(0, 0, 4); p.hints |= kParameterIsInteger;
            p.enumValues.count = 5; p.enumValues.restrictedMode = true; p.enumValues.values = ev; p.enumValues.deleteLater = false;
            break; }
        case pMacro1: case pMacro2: case pMacro3: case pMacro4: {   // DNA v2 macros (DNA.md 5.3): what each moves is in the DNA
            const int k = (int)(i - pMacro1) + 1;
            p.name = String("Macro ") + String(k); p.symbol = String("macro") + String(k); p.unit = "%";
            p.ranges = ParameterRanges(0, 0, 100); p.hints |= kParameterIsInteger;
            break; }
        }
    }

    float getParameterValue(uint32_t i) const override { return i < pCount ? param_[i].load() : 0.f; }

    void setParameterValue(uint32_t i, float v) override
    {
        if (i >= pCount) return;
        if (param_[i].load() == v) return;
        param_[i] = v;
        if (i >= pKey) { keyVer_++; return; }   // the key: pitches of new notes only (no DNA change)
        paramsDirty_ = true;
        paramSeq_++;
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
        const b16v3::KeyParams kp = keyParams();
        if (kp != b16v3::KeyParams()) {   // (absent: the defaults, so an old state stays byte-identical)
            s.extra["key"] = std::to_string(kp.root) + " " + std::to_string(kp.scale);
            s.extra["keyopt"] = std::to_string(kp.usePreset) + " " + std::to_string(kp.snap) + " " + std::to_string(kp.remap) + " " +
                                std::to_string(kp.labels) + " " + std::to_string(kp.anchor);
        }
        return String(s.write().c_str());
    }

    void setState(const char *key, const char *value) override
    {
        if (std::strcmp(key, "state")) return;
        bsynth::State s;
        if (s.read(value ? value : "")) {
            b16v3::KeyParams kp;
            if (s.extra.count("key")) kp.readLine("key " + s.extra["key"]);
            if (s.extra.count("keyopt")) kp.readLine("keyopt " + s.extra["keyopt"]);
            setKeyParams(kp);
            setDna(s.dna, true);
        }
    }

    void sampleRateChanged(double) override { updateLatency(); }
    void bufferSizeChanged(uint32_t) override { updateLatency(); }
    void activate() override { anchor_ = -1; }

    // the inputs are a stereo sidechain (hosts that ignore it see an instrument with no input); the outputs as DPF has them
    void initAudioPort(bool input, uint32_t index, AudioPort &port) override
    {
        if (!input) { Plugin::initAudioPort(input, index, port); return; }
        port.hints = kAudioPortIsSidechain;
        port.name = index ? "Record In R" : "Record In L";
        port.symbol = index ? "rec_in_r" : "rec_in_l";
    }

    void run(const float **in, float **out, uint32_t frames, const MidiEvent *ev, uint32_t nev) override
    {
        bshm *S = sh_.S;
        float *L = out[0], *R = out[1];
        S->host_beat++;
        audioAlive_ = nowSec();
        const double sr = getSampleRate(), ratio = 48000.0 / sr;
        housekeeping();
        // Offline (a render), the plugin waits for whatever Windows is still doing, so renders are exact:
        // the machine resuming, the assembly, a DNA being built. Live it never waits (a new sound takes over
        // when it is built; until then the old one plays).
        // (live, process() never waits: silence until Windows is ready, and a late block is played as it is)
        const bool offline = !testLive_ && isProcessingOffline();
        S->offline = offline ? 1 : 0;
        bool waited = false;
        if (engine_ && offline && S->state < BS_RUNNING) {
            for (int k = 0; k < 20000 && S->state < BS_RUNNING && S->state != BS_FAILED && !quit_; k++) std::this_thread::sleep_for(std::chrono::milliseconds(1));
            waited = true;
        }
        if (S->state < BS_RUNNING || S->state == BS_FAILED) {
            std::memset(L, 0, frames * sizeof(float)); std::memset(R, 0, frames * sizeof(float));
            return;
        }
        S->realtime = 1;
        // offline: a parameter change of this block becomes the DNA before its notes are stamped (if it needs a rebuild,
        // the wait below covers it; the notes come after the new sound is built)
        for (int k = 0; offline && k < 4000 && paramSeq_.load() != paramDone_.load() && !quit_; k++)
            std::this_thread::sleep_for(std::chrono::microseconds(250));
        if (offline && S->state >= BS_RUNNING && (!ready_ || building_ || inFlightAtomic())) {
            // the engine may run on while we wait (Windows needs the time); its sound in that stretch is skipped
            // (also the assembly: until it is done, Windows serves notes only between animation frames)
            for (int k = 0; k < 30000 && (!ready_ || building_ || inFlightAtomic()) && S->state != BS_FAILED && !S->quit && !quit_; k++) {
                S->grant_until = S->dac_w + 48000; S->host_beat++;
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            S->grant_until = 0;
            housekeeping();
            waited = true;
        }
        // The host's samples map onto the card's DAC samples from an integer anchor: DAC position = anchor + n * ratio.
        // The anchor is reset when the host's transport starts, so a render (or a replay) always stamps its notes on
        // the same DAC samples and resamples with the same phase: identical output every time.
        {
            const TimePosition &tp = getTimePosition();
            if (tp.bbt.valid && tp.bbt.beatsPerMinute > 1 && std::fabs(tp.bbt.beatsPerMinute - bpm_.load()) > 0.01) {   // v3 Wt, Wb, Wg
                bpm_ = tp.bbt.beatsPerMinute;
                if (d3Audio_.layers.size() && std::any_of(d3Audio_.layers.begin(), d3Audio_.layers.end(), [](const bsynth3::Layer3 &L) { return L.has[0] && L.w.tempo; })) tempoDirty_ = true;
            }
            const double cur = anchor_ < 0 ? -1 : anchor_ + (double)hcount_ * ratio;
            const bool start = tp.playing && !wasPlaying_;
            wasPlaying_ = tp.playing;
            if (anchor_ < 0 || start || ratio != lastRatio_) {
                // a fresh, integer anchor (never behind what the engine already made, else notes would be late)
                double a = cur < 0 ? (double)S->dac_w : std::ceil(cur);
                if ((double)S->dac_w > a + kLead) a = (double)S->dac_w - kLead;
                anchor_ = std::floor(a); hcount_ = 0; lastRatio_ = ratio;
            } else if (waited || (double)S->dac_w > cur + kLead + 24000) {
                // the engine ran on (we waited, or the host stalled): jump forward a whole number of DAC samples,
                // so the resampling phase, and with it the output, stays the same as if nothing had happened
                const double jump = std::ceil((double)S->dac_w - kLead - cur);
                if (jump > 0) anchor_ += jump;
            }
        }
        dacPos_ = anchor_ + (double)hcount_ * ratio;
        // the sidechain into the card's ADC (RECORDING.md 1.1, 1.3): live only, on the DAC clock, stamped like the
        // notes (kLatency48 ahead), so a take lines up with what was played; resampled linearly to 48 kHz
        S->in_src = recSelf_.load() ? 1 : 0;
        if (!offline && in && in[0] && in[1] && !recSelf_.load()) {
            const double d0 = dacPos_ + kLatency48, d1 = d0 + frames * ratio;
            uint64_t d = (uint64_t)std::ceil(d0);
            if (d < inNext_) d = inNext_;   // never write a sample twice
            if (inNext_ && d > inNext_)      // a jump of the anchor leaves a gap: silence, not what the ring held before
                for (uint64_t g = std::max(inNext_, d > BSHM_INRING ? d - BSHM_INRING : 0); g < d; g++) { const uint32_t k = (uint32_t)(g % BSHM_INRING); S->in_ring[k * 2] = S->in_ring[k * 2 + 1] = 0.f; }
            for (; (double)d < d1; d++) {
                const double x = ((double)d - d0) / ratio; const uint32_t i = (uint32_t)x; const float f = (float)(x - i);
                const uint32_t j = i + 1 < frames ? i + 1 : i;
                const uint32_t k = (uint32_t)(d % BSHM_INRING);
                S->in_ring[k * 2] = in[0][i] + (in[0][j] - in[0][i]) * f;
                S->in_ring[k * 2 + 1] = in[1][i] + (in[1][j] - in[1][i]) * f;
            }
            if (d > inNext_) { __sync_synchronize(); S->in_w = d; inNext_ = d; }
        }
        // the keyboard strip in Windows (DNA.md 5.4): its keys and wheels play at the start of this block
        MidiEvent kev[64]; uint32_t nk = 0;
        for (uint32_t r = keyR_.load(), w = keyW_.load(std::memory_order_acquire); r != w && nk < 64; r++, nk++) {
            const uint32_t k = keyQ_[r % kKeyQ];
            kev[nk].frame = 0; kev[nk].size = 3;
            kev[nk].data[0] = (uint8_t)(k >> 16); kev[nk].data[1] = (uint8_t)(k >> 8); kev[nk].data[2] = (uint8_t)k;
            keyR_.store(r + 1);
        }
        // the notes of this block: each one is stamped with the DAC sample at which it must sound
        for (uint32_t i = 0; i < nk + nev; i++) {
            const bool fromWindows = i < nk;
            const MidiEvent &e = fromWindows ? kev[i] : ev[i - nk];
            const uint8_t *d = e.size > 4 ? e.dataExt : e.data;
            if (e.size < 2) continue;
            const uint64_t at = (uint64_t)std::floor(anchor_ + (double)(hcount_ + e.frame) * ratio) + kLatency48;
            const uint8_t st = d[0] & 0xF0;
            Cmd c[kMaxCmds]; int n = 0;
            vo_.clear();   // DNA v3: the layers with N, S or D (V3Alloc.h), and live bend
            v3_.setBpm(bpm_);
            if (st == 0x90 && e.size >= 3 && d[2] > 0) { n = voices_.noteOn(d[1], d[2], at, c); v3_.noteOn(d[1], d[2], at, vo_); if (!fromWindows) show(0, d[1], d[2]); }
            else if (st == 0x80 || (st == 0x90 && e.size >= 3)) { n = voices_.noteOff(d[1], at, c); v3_.noteOff(d[1], at, vo_); if (!fromWindows) show(0, d[1], 0); }
            else if (st == 0xB0 && e.size >= 3) {
                if (d[1] == 64) { n = voices_.sustain(d[2] >= 64, at, c); v3_.sustain(d[2] >= 64, at, vo_); }
                else if (d[1] == 120 || d[1] == 123) { n = voices_.allOff(c); v3_.allOff(); }
                else if (d[1] == 1) { cc1_ = d[2]; if (!fromWindows) show(1, 1, d[2]); }   // the mod wheel: adds to Macro 1
            } else if (st == 0xE0 && e.size >= 3) {
                const int v = (d[1] | (d[2] << 7)) - 8192;
                voices_.bend(v / 8192.0);
                if (capRate_) v3_.bend(v / 8192.0, at, vo_);   // what already sounds follows the wheel
                if (!fromWindows) show(2, 0, (uint32_t)(v + 8192));
            }
            const int vel = (st == 0x90 && e.size >= 3) ? d[2] : 100;
            for (int k = 0; k < n; k++) v3_.follow(c[k], c[k].layer < kMaxLayers && audioFixed_[c[k].layer]);
            auto sendCmd = [&](Cmd cm, uint32_t wf = 0, uint32_t wt = 0) {
                char line[128];
                if (cm.kind != Cmd::Panic && cm.rec < 16 && (recBusy_.load() >> cm.rec & 1)) return;   // recording there
                uint64_t when = at;
                if (cm.kind == Cmd::On) { when += b16v3::delay48(d3Audio_, cm, bpm_); cm.delayMs = 0; }   // O (v3: Wo, Wb, Wt; S strum): a later stamp
                if (cm.kind == Cmd::On && wt > wf && capWin_) {   // a kit pad's window (its segment, start and end): exact
                    std::snprintf(line, sizeof line, "on %d %u %u %d 0 %d %u %u", cm.rec, cm.rateHz, cm.vol, cm.pan, cm.layer, wf, wt);
                    sendLine(line, ++nextId_, when);
                    if (cm.rateHz) { char cl[32]; std::snprintf(cl, sizeof cl, "cut %d", cm.rec); sendLine(cl, ++nextId_, when + (uint64_t)((double)(wt - wf) * 48000.0 / cm.rateHz)); }
                    return;
                }
                if (cm.kind == Cmd::On && capWin_) {   // DNA v3: the window and the per-note random draws (V3Voice.h)
                    const int L = cm.layer < kMaxLayers ? cm.layer : 0;
                    const b16v3::NoteOut o = b16v3::note(d3Audio_, cm, vel, when, audioFrames_[L], audioRate_[L], v3Counter_, d3Salt_, true, bpm_);
                    std::snprintf(line, sizeof line, "%s", o.on);
                    when = o.when;
                    sendLine(line, ++nextId_, when);
                    if (o.cut) { char cl[32]; std::snprintf(cl, sizeof cl, "cut %d", cm.rec); sendLine(cl, ++nextId_, o.cutAt); }
                    if (o.gate && (!o.cut || o.gateAt < o.cutAt)) { char cl[32]; std::snprintf(cl, sizeof cl, "off %d", cm.rec); sendLine(cl, ++nextId_, o.gateAt); }
                    if (trace_) std::fprintf(trace_, "%s id %u at %llu%s\n", line, nextId_, (unsigned long long)when, o.cut ? " (window cut stamped)" : "");
                    return;
                }
                proto::cmd(line, sizeof line, cm);
                line[std::strlen(line) - 1] = 0;
                sendLine(line, ++nextId_, when);
                if (trace_) std::fprintf(trace_, "%s id %u at %llu dacPos %.0f dac_w %llu late %u/%u max %u\n", line, nextId_,
                                         (unsigned long long)when, dacPos_, (unsigned long long)S->dac_w, S->sched_late, S->sched_ontime, S->sched_latemax);
            };
            for (int k = 0; k < n; k++) sendCmd(c[k]);
            for (const b16v3::Out &o : vo_) {   // then v3's, in order (a Rate after the On it moves)
                if (o.kind == b16v3::Out::Cmd) { sendCmd(o.c, o.winFrom, o.winTo); continue; }
                if (o.kind == b16v3::Out::Choke) {   // a kit's cut group: the voice fades out over the pad's fade
                    char line[48]; std::snprintf(line, sizeof line, "choke %d %d", o.rec, o.fadeMs);
                    sendLine(line, ++nextId_, o.at);
                    continue;
                }
                if (!capRate_) continue;
                char line[64];
                std::snprintf(line, sizeof line, "rate %d %u %d %d", o.rec, o.hz, o.glideMs, o.regate ? 1 : 0);
                sendLine(line, ++nextId_, o.at);
            }
        }
        // wait for the machine if it is behind (offline rendering runs faster than real time)
        const double need = dacPos_ + frames * ratio + 3;
        for (int k = 0; offline && k < 400 && (double)S->dac_w < need && S->state != BS_FAILED && !S->quit && !quit_; k++) {
            S->grant_until = (uint64_t)need > kLead ? (uint64_t)need - kLead : 0; S->host_beat++;   // waiting: the engine runs to `need`
            std::this_thread::sleep_for(std::chrono::microseconds(500));
        }
        S->grant_until = 0;
        if ((double)S->dac_w < need) S->underruns++;
        const float g = gain_;
        for (uint32_t i = 0; i < frames; i++) {
            const double p = anchor_ + (double)(hcount_ + i) * ratio;
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
        }
        hcount_ += frames;
        dacPos_ = anchor_ + (double)hcount_ * ratio;
        S->host_r = (uint64_t)std::max(0.0, dacPos_ - 4);
    }

private:
    // the card runs at 48 kHz; the engine keeps kLead DAC samples ahead of the host, and every note is stamped
    // kLatency48 samples ahead: enough for Windows to press Play before the card gets there
    static constexpr uint32_t kLead = 1024;
    // The latency covers what the engine may already have made beyond the host (its lead, plus up to two emulated
    // frames of ~672 samples) plus the host's block, plus time for Windows to press Play: so no note is ever late.
    uint32_t kLatency48 = kLead + 1536;

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
    bool lenvDirty_ = false;           // worker: send every layer's effective envelopes (lenv)
    // DNA v3 (design/PRESET-ENGINE-2.md): the parsed v3 tokens, beside the v2 DNA (same staging); the guest's caps
    bsynth3::Dna3 d3ForAudio_, stagedD3_;
    uint32_t d3SaltPending_ = 0;
    std::atomic<bool> capWin_{false}, capDesk_{false}, capLoop_{false}, capRate_{false};
    std::atomic<double> bpm_{120};   // the host's tempo (v3 Wt, Wb, Wg)
    std::atomic<bool> tempoDirty_{false};
    std::atomic<bool> recSelf_{false};
    std::atomic<uint32_t> keyVer_{1};    // the key parameters changed (audio: the key; engine: the guest's display)
    uint32_t keyVerAudio_ = 0, keyVerGuest_ = 0;
    b16v3::KeyParams keyAudio_;
    bool keyDnaChanged_ = true;
    std::vector<uint32_t> pendSegs_[kMaxLayers]; bool segsDirty_ = false;   // the guest's seg lines (mtx_)
    b16v3::KeyParams keyParams() const
    {
        b16v3::KeyParams k;
        k.root = (int)std::lround(param_[pKey].load()); k.scale = (int)std::lround(param_[pScale].load());
        k.usePreset = param_[pUsePreset].load() >= 0.5f; k.snap = (int)std::lround(param_[pSnap].load());
        k.remap = param_[pRemap].load() >= 0.5f; k.anchor = (int)std::lround(param_[pAnchor].load()); k.labels = (int)std::lround(param_[pLabels].load());
        return k;
    }
    void setKeyParams(const b16v3::KeyParams &k)
    {
        param_[pKey] = (float)k.root; param_[pScale] = (float)k.scale; param_[pUsePreset] = (float)k.usePreset; param_[pSnap] = (float)k.snap;
        param_[pRemap] = (float)k.remap; param_[pAnchor] = (float)k.anchor; param_[pLabels] = (float)k.labels;
        keyVer_++;
    }
    // audio thread: the effective key for new notes (the parameters, or the DNA's suggestion), and which layers core
    // or V3Alloc plays
    void applyKey()
    {
        keyAudio_ = keyParams();
        v3_.setKey(b16v3::effectiveKey(keyAudio_, d3Audio_));
        for (int i = 0; i < kMaxLayers; i++)
            if (layerCache_[i].known) voices_.setLayerInfo(i, layerCache_[i].first, v3_.owns(i) ? 0 : layerCache_[i].count, layerCache_[i].rate, layerCache_[i].frames);
    }
    std::atomic<uint32_t> recBusy_{0};   // recorders that record now: notes leave them alone (a Stop would end the take)
    b16v3::V3Alloc v3_;                  // DNA v3 voice modes, stacking, degree chords, live bend (audio thread)
    std::vector<b16v3::Out> vo_;
    bool audioFixed_[kMaxLayers] = {};   // the ADC records the synth's own output (else the sidechain)
    uint64_t inNext_ = 0;                // the next DAC sample of input to write
    double lastParamEdit_ = 0;         // a DNA from parameters (automation) goes to Windows 300 ms after the last change
    // the keyboard strip: Windows' keys to the audio thread, and incoming MIDI to Windows' keys (single producer and
    // consumer each, no locks: kind << 24 | a << 16 | b for the display, status << 16 | data1 << 8 | data2 for keys)
    static constexpr uint32_t kKeyQ = 256;
    uint32_t keyQ_[kKeyQ] = {}, showQ_[kKeyQ] = {};
    std::atomic<uint32_t> keyR_{0}, keyW_{0}, showR_{0}, showW_{0};
    std::atomic<int> cc1_{0};          // the mod wheel (MIDI or Windows): added to Macro 1
    int cc1Applied_ = 0;
    void show(uint32_t kind, uint32_t a, uint32_t b)
    {
        const uint32_t w = showW_.load();
        if (w - showR_.load() >= kKeyQ) return;
        showQ_[w % kKeyQ] = kind << 24 | (a & 0xFF) << 16 | (b & 0xFFFF);
        showW_.store(w + 1, std::memory_order_release);
    }
    void keyFromWindows(uint8_t st, uint8_t a, uint8_t b)
    {
        const uint32_t w = keyW_.load();
        if (w - keyR_.load() >= kKeyQ) return;
        keyQ_[w % kKeyQ] = (uint32_t)st << 16 | (uint32_t)a << 8 | b;
        keyW_.store(w + 1, std::memory_order_release);
    }
    bool inFlight_ = false;            // a DNA Windows is building (its `layer` replies are staged until `built`)
    Dna stagedDna_; std::string stagedSig_;
    LayerInfo stagedLayers_[kMaxLayers];

    std::atomic<float> param_[pCount];
    std::atomic<bool> paramsDirty_{false};
    std::atomic<uint32_t> paramSeq_{0}, paramDone_{0};   // parameter changes made / taken into the DNA (offline waits for it)
    bool rebuildQueued_ = false;       // a DNA that needs Sound Recorder is waiting to go to Windows
    std::atomic<bool> building_{false};
    std::atomic<bool> ready_{false};       // Windows has assembled the instrument
    std::atomic<double> audioAlive_{0};
    double created_ = 0;
    bool testLive_ = false;
    FILE *dump_ = nullptr;
    FILE *trace_ = nullptr;    // test: BASILISK16_TRACE=dir writes each note's stamps (one file per instance)     // test: BASILISK16_TEST_DUMP_DAC=file writes the card's DAC samples behind each output sample

    // audio thread only
    Voices voices_{48000};
    bsynth3::Dna3 d3Audio_;
    uint32_t d3Salt_ = 0, v3Counter_ = 0;
    uint32_t audioFrames_[kMaxLayers] = {}; int audioRate_[kMaxLayers] = {};
    double dacPos_ = -1, anchor_ = -1, lastRatio_ = 0;
    uint64_t hcount_ = 0;
    bool wasPlaying_ = false;
    uint32_t nextId_ = 0;
    float gain_ = 1.f;

    void updateLatency()
    {
        const uint32_t block48 = (uint32_t)std::ceil(getBufferSize() * 48000.0 / getSampleRate());
        kLatency48 = std::max<uint32_t>(kLead + 1536, block48 + 2 * 672 + 1024);
        setLatency((uint32_t)std::lround(kLatency48 * getSampleRate() / 48000.0));
    }

    static std::string sigOf(const Dna &d)
    {
        std::string s;
        for (auto &L : d.layers) {
            s += std::to_string(L.source) + L.sourceName + ":" + std::to_string(L.first) + ":" + std::to_string(L.count) + ":";
            for (auto &st : L.steps) { s += st.op; s += std::to_string(st.arg) + "." + std::to_string(st.ms) + "." + std::to_string(st.sound) + st.name; }
            s += "|";
        }
        return s;
    }

    // a new DNA from a preset, the state, a parameter or (fromGuest) Windows itself
    void setDna(const std::string &text, bool toGuest, bool fromGuest = false)
    {
        const Dna written = parse(text);
        Dna d = effective(written);      // what sounds: the macros' mapped genes, Z-scaled envelopes, N repeats
        bsynth3::Dna3 d3;                // DNA v3: its tokens, with the v3 macro maps applied (mod wheel included)
        {
            int mac[4];
            for (int k = 0; k < 4; k++) mac[k] = written.g.macro[k];
            mac[0] = std::min(100, mac[0] + (cc1_.load() * 100 + 63) / 127);
            d3 = bsynth3::applyMacros3(bsynth3::parse3(written.canonical), mac);
        }
        std::lock_guard<std::mutex> l(mtx_);
        dnaText_ = written.canonical;
        lenvDirty_ = true;               // the card gets every layer's effective envelopes again
        if (toGuest && !fromGuest) dnaToGuest_ = true;
        const std::string sig = sigOf(d);
        if (sig == cacheSig_ || (cacheSig_.empty() && sig == sigOf(parse(kDefaultDna)))) {
            // the recorders already hold this sound (only genes or globals differ): the audio adopts it now.
            // (At first the snapshot's machine holds DING in all sixteen: the default plays before Windows replies.)
            if (cacheSig_.empty()) layerCache_[0] = LayerInfo{0, 16, 22050, 11466, true};
            cacheSig_ = sig;
            if (!inFlight_) rebuildQueued_ = false;
            dnaForAudio_ = d;
            d3ForAudio_ = d3; d3SaltPending_ = b16v3::salt(written.canonical);
            dnaPending_ = true;
        } else {
            // Sound Recorder must rebuild: the audio keeps the old sound until Windows says `built`, so notes never
            // stop sounding (Windows rebuilds one recorder at a time and serves notes in between)
            stagedDna_ = d; stagedSig_ = sig; stagedD3_ = d3;
            for (auto &c : stagedLayers_) c = LayerInfo();
            if (fromGuest) inFlight_ = true;   // Windows is already building it
            else if (toGuest) rebuildQueued_ = true;
        }
        param_[pAttack] = (float)d.g.attack; param_[pDecay] = (float)d.g.decay; param_[pSustain] = (float)d.g.sustain;
        param_[pRelease] = (float)d.g.release; param_[pVelocity] = (float)d.g.velocity; param_[pBend] = (float)d.g.bendRange;
        param_[pGain] = (float)d.g.gainDb; param_[pTranspose] = written.layers.empty() ? 0.f : (float)written.layers[0].transpose;
        for (int k = 0; k < kMacros; k++) param_[pMacro1 + k] = (float)written.g.macro[k];
        paramsDirty_ = false;
    }

    // the DNA as it sounds: macros applied, the mod wheel added to Macro 1 (DNA.md 5.4). A mapped N follows the
    // parameter only: the wheel never makes Sound Recorder rebuild.
    Dna effective(const Dna &written)
    {
        const Dna base = applyMacros(written);
        const int cc = cc1_.load();
        cc1Applied_ = cc;
        if (!cc) return base;
        Dna w = written;
        w.g.macro[0] = std::min(100, std::max(0, written.g.macro[0] + (cc * 100 + 63) / 127));
        Dna d = applyMacros(w);
        return sigOf(d) == sigOf(base) ? d : base;
    }

    // offline waits only for what changes the recorders' buffers (a DNA that only moves genes, macros or envelopes
    // takes effect at once, and an offline render never stalls on it)
    bool inFlightAtomic() { std::lock_guard<std::mutex> l(mtx_); return inFlight_ || rebuildQueued_; }

    // audio thread, start of every block: adopt what the worker prepared (never waits for it)
    void housekeeping()
    {
        if (!mtx_.try_lock()) return;
        if (dnaPending_) {
            Cmd c[1];
            voices_.setDna(dnaForAudio_, c);
            d3Audio_ = d3ForAudio_; d3Salt_ = d3SaltPending_;
            v3_.setDna(dnaForAudio_, d3Audio_);
            keyDnaChanged_ = true;   // (the DNA's q may be the key)
            for (int i = 0; i < kMaxLayers; i++) audioFixed_[i] = i < (int)dnaForAudio_.layers.size() && dnaForAudio_.layers[i].fixed;
            for (int i = 0; i < kMaxLayers; i++)
                if (layerCache_[i].known) {
                    v3_.setLayerInfo(i, layerCache_[i].first, layerCache_[i].count, layerCache_[i].rate, layerCache_[i].frames);
                    voices_.setLayerInfo(i, layerCache_[i].first, v3_.owns(i) ? 0 : layerCache_[i].count, layerCache_[i].rate, layerCache_[i].frames);
                    audioFrames_[i] = (uint32_t)layerCache_[i].frames; audioRate_[i] = layerCache_[i].rate;
                }
            gain_ = (float)std::pow(10.0, dnaForAudio_.g.gainDb / 20.0);
            dnaPending_ = false;
        }
        for (size_t i = 0; i < pendLayers_.size(); i++) {
            v3_.setLayerInfo(pendLayerIdx_[i], pendLayers_[i].first, pendLayers_[i].count, pendLayers_[i].rate, pendLayers_[i].frames);
            voices_.setLayerInfo(pendLayerIdx_[i], pendLayers_[i].first, v3_.owns(pendLayerIdx_[i]) ? 0 : pendLayers_[i].count, pendLayers_[i].rate, pendLayers_[i].frames);
            if (pendLayerIdx_[i] >= 0 && pendLayerIdx_[i] < kMaxLayers) { audioFrames_[pendLayerIdx_[i]] = (uint32_t)pendLayers_[i].frames; audioRate_[pendLayerIdx_[i]] = pendLayers_[i].rate; }
        }
        pendLayers_.clear(); pendLayerIdx_.clear();
        for (int r : pendEnds_) { voices_.end(r); v3_.end(r); }
        if (segsDirty_) { for (int i = 0; i < kMaxLayers; i++) v3_.setSegments(i, pendSegs_[i]); segsDirty_ = false; }
        if (keyVerAudio_ != keyVer_.load() || keyDnaChanged_) { keyVerAudio_ = keyVer_.load(); keyDnaChanged_ = false; applyKey(); }
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
            const int words = 3 + (m + 1) / 2;
            uint16_t w[136];
            w[0] = (uint16_t)(((last ? 4 : 8) << 8) | words);
            w[1] = (uint16_t)(last ? id : 0); w[2] = (uint16_t)((last ? id : 0) >> 16);
            for (int k = 0; k < (m + 1) / 2; k++) {
                const uint8_t a = (uint8_t)text[pos + 2 * k], b = 2 * k + 1 < m ? (uint8_t)text[pos + 2 * k + 1] : 0;
                w[3 + k] = (uint16_t)(a | (b << 8));
            }
            // straight to the card when the machine runs (no wait for the engine's next loop); else the ring
            if (S->ev_w == S->ev_r && bs_engine_event(engine_, w, words, last ? id : 0, last ? at : 0)) { pos += m; continue; }
            if (S->ev_w - S->ev_r >= BSHM_EV) break;
            bshm_ev &e = S->ev[S->ev_w % BSHM_EV];
            std::memcpy(e.w, w, sizeof(uint16_t) * words);
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
#ifdef _WIN32
        sweepTemp(tempDir());
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
            if (!f) { status("BASILISK 16: cannot read the machine settings."); sh_.S->state = BS_FAILED; return; }
            std::string out;
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
                out += s;
            }
            std::fclose(f);
            if (!writeText(conf_, out)) { status("BASILISK 16: cannot write the machine settings."); sh_.S->state = BS_FAILED; return; }
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
#ifdef _WIN32
        for (int k = 0; k < 20 && !DeleteFileA(coreCopy_.c_str()) && GetLastError() != ERROR_FILE_NOT_FOUND; k++) Sleep(25);   // the core may take a moment to unmap
#endif
        std::remove(coreCopy_.c_str());
        std::remove(conf_.c_str());
#ifdef _WIN32
        RemoveDirectoryA(tmp_.c_str());
#else
        rmdir(tmp_.c_str());
#endif
    }

    void status(const char *s) { std::snprintf(sh_.status, sizeof sh_.status, "%s", s); }

    // the library disc's sound names (machine/library.names.txt, written with library.zip): a DNA may use them
    void loadLibraryNames()
    {
        static std::once_flag once;
        std::call_once(once, [this] {
            const char *bundle = getBundlePath();
            const char *res = bundle ? getResourcePath(bundle) : nullptr;
            if (!res) return;
            FILE *f = std::fopen((std::string(res) + "/machine/library.names.txt").c_str(), "rb");
            if (!f) return;
            std::vector<std::string> names; char line[256];
            while (std::fgets(line, sizeof line, f)) {
                std::string s = line;
                while (!s.empty() && (s.back() == '\n' || s.back() == '\r' || s.back() == ' ')) s.pop_back();
                if (!s.empty()) names.push_back(s);
            }
            std::fclose(f);
            setLibrary(names);
        });
    }

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
                trimSend(std::strcpy(b, "hi 3"));   // DNA v3: the guest answers with its caps (v2 guests answer hi 2)
                proto::time(b, sizeof b, lt.tm_year + 1900, lt.tm_mon + 1, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec); trimSend(b);
                proto::go(b, sizeof b); trimSend(b);
                for (const auto &x : bsynth3::scaleLibrary()) {   // the scale library, for Windows' Scale box (category: _ for spaces)
                    std::string cat = x.category; for (auto &ch : cat) if (ch == ' ') ch = '_';
                    const std::string line = "scale " + std::to_string(x.id) + " " + cat + " " + x.label;
                    sendLine(line.c_str(), 0, 0);
                }
                keyVerGuest_ = 0;   // and the key
                std::lock_guard<std::mutex> l(mtx_);
                dnaToGuest_ = true;
            }
            const uint32_t seq = paramSeq_.load();
            if (paramsDirty_.exchange(false)) {
                std::string d;
                { std::lock_guard<std::mutex> l(mtx_); d = dnaText_; }
                for (int i = 0; i < 7; i++) d = setGlobal(d, kGlobalLetter[i], (int)std::lround(param_[i].load()));
                d = setLayerGene(d, 0, 'T', (int)std::lround(param_[pTranspose].load()));
                {
                    const Dna cur = parse(d);
                    for (int k = 0; k < kMacros; k++) {
                        const int v = (int)std::lround(param_[pMacro1 + k].load());
                        if (v != cur.g.macro[k]) d = setMacro(d, k + 1, v);
                    }
                }
                lastParamEdit_ = nowSec();
                bool changed;
                { std::lock_guard<std::mutex> l(mtx_); changed = d != dnaText_; }
                if (changed) setDna(d, true);
            }
            paramDone_ = seq;
            if (hello && keyVerGuest_ != keyVer_.load()) {   // the key, for Windows' Key and Scale boxes and its strip
                keyVerGuest_ = keyVer_.load();
                bsynth3::Dna3 d3k; { std::lock_guard<std::mutex> l(mtx_); d3k = d3ForAudio_; }
                const b16v3::KeyParams kp = keyParams();
                const bsynth3::Key k = b16v3::effectiveKey(kp, d3k);
                std::string line = "key " + std::to_string(k.root) + " " + std::to_string(kp.scale) + " " + std::to_string(k.tuning.size()) + " " +
                                   std::to_string((int)std::lround(k.tuning.period)) + " ";
                for (size_t j = 0; j < k.tuning.steps.size(); j++) line += (j ? "," : "") + std::to_string((int)std::lround(k.tuning.steps[j]));
                line += " " + std::to_string(kp.remap) + " " + std::to_string(kp.anchor) + " " + std::to_string(kp.labels) + " " +
                        std::to_string(bsynth3::tuningMask(k.tuning)) + " " + std::to_string(kp.usePreset) + " " + std::to_string(kp.snap);
                if (line.size() < 240) sendLine(line.c_str(), 0, 0);
                // the keyboard strip (PRESET-ENGINE-2 18.5): per key 36..96 its label ('' none), '~' = out of the scale
                // (a 12-note scale without remap: dimmed); two lines
                const bool showOut = !kp.remap && k.tuning.twelve() && k.tuning.size() < 12;
                for (int half = 0; half < 2; half++) {
                    const int n0 = half ? 67 : 36, n1 = half ? 96 : 66;
                    std::string kl = "klabels " + std::to_string(n0) + " ";
                    for (int n = n0; n <= n1; n++) {
                        const bsynth3::Played pl = bsynth3::playKey(k, n, bsynth3::SnapOff);
                        std::string lb;
                        if (!pl.inScale && showOut) lb = "~";
                        else if (pl.inScale || kp.remap || !k.tuning.twelve()) lb = bsynth3::stepLabel(k, pl.step, kp.labels);
                        for (auto &ch : lb) if (ch == '|' || ch == ' ') ch = '_';
                        kl += (n > n0 ? "|" : "") + lb;
                    }
                    if (kl.size() < 245) sendLine(kl.c_str(), 0, 0);
                }
            }
            if (cc1_.load() != cc1Applied_) {   // the mod wheel moved: the sound follows (no DNA to Windows)
                std::string cur;
                { std::lock_guard<std::mutex> l(mtx_); cur = dnaText_; }
                setDna(cur, false, false);
            }
            for (uint32_t r = showR_.load(), w = showW_.load(std::memory_order_acquire); r != w && hello; r++) {
                const uint32_t q = showQ_[r % kKeyQ], kind = q >> 24, a = (q >> 16) & 0xFF, b = q & 0xFFFF;
                char t[48];
                if (kind == 0) std::snprintf(t, sizeof t, "show %u %u", a, b);
                else if (kind == 1) std::snprintf(t, sizeof t, "cc %u %u", a, b);
                else std::snprintf(t, sizeof t, "bend %d", (int)b - 8192);
                sendLine(t, 0, 0);
                showR_.store(r + 1);
            }
            bool send = false, sendEnv = false, rebuild = false; std::string d; Globals g; Dna eff; bsynth3::Dna3 d3e;
            {
                std::lock_guard<std::mutex> l(mtx_);
                if (tempoDirty_.exchange(false)) lenvDirty_ = true;   // Wt envelope times follow the host tempo
                // automation: Windows hears the DNA 300 ms after the last change (the sound already follows: genes,
                // pan, offsets and envelopes are the host's; only a repeat count N makes Sound Recorder rebuild)
                const bool settled = nowSec() - lastParamEdit_ > 0.3 || isProcessingOffline();
                if (hello && dnaToGuest_ && !inFlight_ && settled) {
                    send = true; dnaToGuest_ = false; d = dnaText_;
                    g = parse(d).g;
                    rebuild = sigOf(applyMacros(parse(d))) != cacheSig_;
                    if (rebuild) { inFlight_ = true; for (auto &c : stagedLayers_) c = LayerInfo(); }
                    rebuildQueued_ = false;
                }
                if (hello && lenvDirty_ && !send && !inFlight_) { sendEnv = true; lenvDirty_ = false; eff = effective(parse(dnaText_)); d3e = d3ForAudio_; }
            }
            if (send) {
                std::string line = "dna " + d;   // as written: Windows shows it, and does N itself
                building_ = rebuild;   // ("built 0" for a DNA that Sound Recorder has nothing to do for)
                sendLine(line.c_str(), 0, 0);
                char b[96]; proto::env(b, sizeof b, g); trimSend(b);
                std::lock_guard<std::mutex> l(mtx_);
                lenvDirty_ = true;
            }
            if (sendEnv) {   // after the DNA (Windows resets them when it parses one): the macro-applied envelopes
                for (int i = 0; i < kMaxLayers; i++) {
                    static const Env none;
                    char b[160];
                    const Layer *L = i < (int)eff.layers.size() ? &eff.layers[i] : nullptr;
                    (void)b;
                    sendLine(b16v3::lenvLine(i, 'a', L ? L->envA : none, d3e, bpm_, capLoop_).c_str(), 0, 0);
                    sendLine(b16v3::lenvLine(i, 'p', L ? L->envP : none, d3e, bpm_, capLoop_).c_str(), 0, 0);
                }
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
        if (line.rfind("keyset ", 0) == 0 || line.rfind("keyopt ", 0) == 0) {   // the visitor changed the key in Windows
            b16v3::KeyParams kp = keyParams();                                       // (`key <note> <vel>` is the strip's)
            if (kp.readLine(line.rfind("keyset ", 0) == 0 ? "key " + line.substr(7) : line)) setKeyParams(kp);
            return;
        }
        if (line == "state save" || line == "state load") {   // design/STATE.md: the editor opens the file dialog
            if (line == "state save") { const String st = getState("state"); std::lock_guard<std::mutex> l(sh_.fileMtx); sh_.stateText = st.buffer(); }
            sh_.fileReq = line == "state save" ? 1 : 2;
            if (sh_.editors.load() == 0) sendLine("state error open the plugin's editor to save or load a state", 0, 0);
            return;
        }
        if (line.rfind("seg ", 0) == 0) {   // seg <layer> <f0> <f1> ...: where a layer's segments start (kit pads)
            std::istringstream in(line.substr(4)); int L = -1; in >> L;
            std::vector<uint32_t> v; uint32_t f; while (in >> f) v.push_back(f);
            std::lock_guard<std::mutex> l(mtx_);
            if (L >= 0 && L < kMaxLayers) { pendSegs_[L] = v; segsDirty_ = true; }
            return;
        }
        if (line.rfind("rsrc ", 0) == 0) { recSelf_ = line.compare(5, 4, "self") == 0; return; }   // the visitor chose the input (RECORDING.md 4.3)
        if (line.rfind("rec start ", 0) == 0) { const int r = std::atoi(line.c_str() + 10); if (r >= 0 && r < 16) recBusy_ |= 1u << r; return; }
        if (line.rfind("rec stop ", 0) == 0) { const int r = std::atoi(line.c_str() + 9); if (r >= 0 && r < 16) recBusy_ &= ~(1u << r); return; }
        proto::Reply r = proto::parse(line);
        switch (r.kind) {
        case proto::Reply::Ready: status(""); ready_ = true; break;
        case proto::Reply::Hi: {
            const std::vector<std::string> caps = bsynth3::parseHi3(line);
            capWin_ = bsynth3::hasCap(caps, "win"); capDesk_ = bsynth3::hasCap(caps, "desk");
            capLoop_ = bsynth3::hasCap(caps, "loop"); capRate_ = bsynth3::hasCap(caps, "rate");
            break; }
        case proto::Reply::Built: {
            std::lock_guard<std::mutex> l(mtx_);
            if (inFlight_) {   // the new sound is in the recorders: the audio switches to it now
                dnaForAudio_ = stagedDna_; cacheSig_ = stagedSig_;
                d3ForAudio_ = stagedD3_; d3SaltPending_ = b16v3::salt(dnaText_);
                for (int i = 0; i < kMaxLayers; i++) layerCache_[i] = stagedLayers_[i];
                dnaPending_ = true;
                inFlight_ = false;
            }
            building_ = false;
            break; }
        case proto::Reply::Layer: {
            std::lock_guard<std::mutex> l(mtx_);
            if (r.layer >= 0 && r.layer < kMaxLayers) {
                LayerInfo li{r.first, r.count, r.rate, r.frames, true};
                if (inFlight_) stagedLayers_[r.layer] = li;
                else {
                    layerCache_[r.layer] = li;
                    pendLayers_.push_back(li); pendLayerIdx_.push_back(r.layer);
                }
            }
            break; }
        case proto::Reply::End: { std::lock_guard<std::mutex> l(mtx_); pendEnds_.push_back(r.rec); break; }
        case proto::Reply::Edit: setDna(r.text, false, true); break;   // Windows already rebuilt; the host adopts it
        default: {   // the keyboard strip in Windows (DNA.md 5.4)
            int a = 0, b = 0;
            if (std::sscanf(line.c_str(), "key %d %d", &a, &b) == 2) keyFromWindows(b > 0 ? 0x90 : 0x80, (uint8_t)(a & 0x7F), (uint8_t)(b & 0x7F));
            else if (std::sscanf(line.c_str(), "cc %d %d", &a, &b) == 2) keyFromWindows(0xB0, (uint8_t)(a & 0x7F), (uint8_t)(b & 0x7F));
            else if (std::sscanf(line.c_str(), "bend %d", &a) == 1) { a += 8192; a = a < 0 ? 0 : a > 16383 ? 16383 : a; keyFromWindows(0xE0, (uint8_t)(a & 0x7F), (uint8_t)(a >> 7)); }
            break; }
        }
    }

    DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(Basilisk16)
};

Plugin *createPlugin() { return new Basilisk16(); }

Basilisk16Shared *basilisk16Shared(void *plugin) { return plugin ? static_cast<Basilisk16 *>(plugin)->shared() : nullptr; }

END_NAMESPACE_DISTRHO
