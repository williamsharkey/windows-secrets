/*
 * SNDWAVE1993 Ensemble (experiment, design/ENSEMBLE.md) - the plugin side.
 *
 * One Windows for Workgroups 3.11 (DOSBox Pure with the 128-voice BSYN card), ten lanes. MIDI channel k+1 plays lane
 * k: its own preset, built by its own Sound Recorders, its notes chosen by its own copy of SNDWAVE1993's note logic
 * (V3Host.h). Every note is stamped with a DAC sample, as in SNDWAVE1993. The card sums each lane on its own bus; the
 * plugin reads the buses, applies each lane's level, pan, mute and solo, and outputs the mix and every lane's pair.
 */
#include "DistrhoPlugin.hpp"
#include "DistrhoPluginUtils.hpp"
#include "../../plugin/Shared.hpp"
#include "../../engine/engine.h"
#include "../../../basilisk-synth/core/dna.h"
#include "../../../basilisk-synth/core/voices.h"
#include "../../../basilisk-synth/core/proto.h"
#include "../../plugin/V3Voice.h"
#include "../../plugin/V3Alloc.h"
#include "../../plugin/V3Host.h"

#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <map>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#include <algorithm>
#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

START_NAMESPACE_DISTRHO

using namespace bsynth;

static constexpr int NB = 10;          // lanes (ENSEMBLE.EXE's NB_LANES)
static constexpr int kRecBudget = 130; // Sound Recorders for every lane together (Windows' USER heap holds about 165)
// parameters: each lane's level (0..127), pan (-64..63), mute, solo; then the master gain
enum { pLaneBase = 0, pPerLane = 4, pMaster = NB * pPerLane, pCount };

static double nowSec() { using namespace std::chrono; return duration<double>(steady_clock::now().time_since_epoch()).count(); }
static bool writeText(const std::string &path, const std::string &text)
{
#ifdef _WIN32
    HANDLE h = CreateFileA(path.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    DWORD n = 0; const BOOL ok = WriteFile(h, text.data(), (DWORD)text.size(), &n, nullptr); CloseHandle(h);
    return ok && n == text.size();
#else
    FILE *f = std::fopen(path.c_str(), "wb"); if (!f) return false;
    const bool ok = std::fwrite(text.data(), 1, text.size(), f) == text.size(); std::fclose(f); return ok;
#endif
}
static bool copyFile(const std::string &from, const std::string &to)
{
#ifdef _WIN32
    return CopyFileA(from.c_str(), to.c_str(), FALSE) != 0;
#else
    FILE *a = std::fopen(from.c_str(), "rb"); if (!a) return false;
    FILE *b = std::fopen(to.c_str(), "wb"); if (!b) { std::fclose(a); return false; }
    char buf[65536]; size_t n; while ((n = std::fread(buf, 1, sizeof buf, a)) > 0) std::fwrite(buf, 1, n, b);
    std::fclose(a); std::fclose(b); return true;
#endif
}
static std::string tempDir()
{
#ifdef _WIN32
    char t[MAX_PATH]; GetTempPathA(MAX_PATH, t); std::string s = t;
#else
    const char *t = std::getenv("TMPDIR"); std::string s = t && *t ? t : "/tmp/";
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

// the preset catalogue: every pack disc's PRESETS.TSV (category, name, DNA), as the Library tab lists them
struct Preset { std::string pack, name, dna; };
static std::mutex gCatMtx;
static std::vector<Preset> gCat;
static void loadCatalogue(const std::string &machine)
{
    std::lock_guard<std::mutex> l(gCatMtx);
    if (!gCat.empty()) return;
    std::ifstream pk(machine + "/packs/PACKS.TSV"); std::string ln;
    while (std::getline(pk, ln)) {
        std::istringstream in(ln); std::string dir, id; std::getline(in, dir, '\t'); std::getline(in, id, '\t');
        if (dir.empty() || dir[0] == '#') continue;
        std::ifstream p(machine + "/packs/" + dir + "/PRESETS.TSV"); std::string r;
        while (std::getline(p, r)) {
            if (r.empty() || r[0] == '#') continue;
            while (!r.empty() && (r.back() == '\r' || r.back() == '\n')) r.pop_back();
            std::vector<std::string> c; std::istringstream rs(r); std::string f; while (std::getline(rs, f, '\t')) c.push_back(f);
            if (c.size() >= 3 && !c[2].empty()) gCat.push_back({id, c[1], c[2]});
        }
    }
}
static int catFind(const std::string &pack, const std::string &name)
{
    std::lock_guard<std::mutex> l(gCatMtx);
    for (size_t i = 0; i < gCat.size(); i++) if (gCat[i].name == name && (pack.empty() || gCat[i].pack == pack)) return (int)i;
    return -1;
}

class Ensemble : public Plugin
{
public:
    Ensemble() : Plugin(pCount, 0, 1)
    {
        for (int k = 0; k < NB; k++) { param_[k * pPerLane + 0] = 100; param_[k * pPerLane + 1] = 0; param_[k * pPerLane + 2] = 0; param_[k * pPerLane + 3] = 0; }
        param_[pMaster] = 0;
        sh_.S = (bshm *)std::calloc(1, sizeof(bshm));
        bshm *S = sh_.S;
        S->magic = BSHM_MAGIC; S->version = BSHM_VERSION; S->rate = 48000; S->ring_len = BSHM_RING; S->lead = kLead; S->realtime = 0;
        updateLatency();
        if (!isDummyInstance()) start();
    }
    ~Ensemble() override
    {
        if (dumpDir_ && sh_.S && engine_) {   // test: the card's scheduling numbers and Windows' own
            sendLine("stats", 0, 0);
            for (int k = 0; k < 200 && statsLine_.empty(); k++) { sh_.S->grant_until = sh_.S->dac_w + 4800; sh_.S->host_beat++; std::this_thread::sleep_for(std::chrono::milliseconds(5)); }
            char f[600]; std::snprintf(f, sizeof f, "%s/stats-%s.txt", dumpDir_, isProcessingOffline() ? "offline" : "realtime");
            if (FILE *o = std::fopen(f, "w")) { std::fprintf(o, "late %u ontime %u latemax %u underruns %u (after the builds: %llu of %llu blocks)\n%s\n", sh_.S->sched_late, sh_.S->sched_ontime, sh_.S->sched_latemax, sh_.S->underruns, (unsigned long long)dropSong_, (unsigned long long)blocksSong_, statsLine_.c_str()); std::fclose(o); }
        }
        quit_ = true;
        if (worker_.joinable()) worker_.join();
        if (engine_) bs_engine_stop(engine_);
        engine_ = nullptr;
        cleanupTemp();
        for (auto &f : dump_) if (f) std::fclose(f);
        if (trace_) std::fclose(trace_);
        std::free(sh_.S);
    }
    Basilisk16Shared *shared() { return &sh_; }

protected:
    const char *getLabel() const override { return "SNDWAVE1993 Ensemble"; }
    const char *getDescription() const override { return "Ten MIDI channels, ten presets, one Windows 3.11. Every note is played by a real Sound Recorder."; }
    const char *getMaker() const override { return "Algorithmic Industries"; }
    const char *getHomePage() const override { return "https://williamsharkey.com/sndwave2000"; }
    const char *getLicense() const override { return "GPL-2.0-or-later"; }
    uint32_t getVersion() const override { return d_version(1, 5, 0); }

    void initParameter(uint32_t i, Parameter &p) override
    {
        p.hints = kParameterIsAutomatable;
        if (i == pMaster) { p.name = "Master"; p.symbol = "master"; p.unit = "dB"; p.ranges.min = -36; p.ranges.max = 12; p.ranges.def = 0; return; }
        const int k = (int)i / pPerLane, w = (int)i % pPerLane;
        static const char *nm[] = {"Level", "Pan", "Mute", "Solo"};
        char n[32], s[32]; std::snprintf(n, sizeof n, "Ch %d %s", k + 1, nm[w]); std::snprintf(s, sizeof s, "ch%d_%s", k + 1, w == 0 ? "level" : w == 1 ? "pan" : w == 2 ? "mute" : "solo");
        p.name = n; p.symbol = s;
        if (w == 0) { p.ranges.min = 0; p.ranges.max = 127; p.ranges.def = 100; p.hints |= kParameterIsInteger; }
        else if (w == 1) { p.ranges.min = -64; p.ranges.max = 63; p.ranges.def = 0; p.hints |= kParameterIsInteger; }
        else { p.ranges.min = 0; p.ranges.max = 1; p.ranges.def = 0; p.hints |= kParameterIsBoolean | kParameterIsInteger; }
    }
    float getParameterValue(uint32_t i) const override { return i < pCount ? param_[i].load() : 0.f; }
    void setParameterValue(uint32_t i, float v) override
    {
        if (i >= pCount) return;
        param_[i] = v;
        if (i != pMaster) mixDirty_ |= 1u << (i / pPerLane);   // Windows' strip follows
    }

    // the state: each lane's sound (pack, name, DNA) and mix, as text
    void initState(uint32_t, State &st) override { st.key = "ensemble"; st.defaultValue = ""; st.hints = kStateIsOnlyForDSP; }
    String getState(const char *key) const override
    {
        if (std::strcmp(key, "ensemble")) return String();
        std::lock_guard<std::mutex> l(mtx_);
        std::string t = "ensemble 1\n";
        for (int k = 0; k < NB; k++)
            t += "lane " + std::to_string(k) + "\t" + lanes_[k].pack + "\t" + lanes_[k].name + "\t" + lanes_[k].dna + "\n";
        return String(t.c_str());
    }
    void setState(const char *key, const char *value) override
    {
        if (std::strcmp(key, "ensemble") || !value || !*value) return;
        std::istringstream in(value); std::string ln;
        while (std::getline(in, ln)) {
            if (ln.rfind("lane ", 0)) continue;
            std::vector<std::string> c; std::istringstream rs(ln.substr(5)); std::string f; while (std::getline(rs, f, '\t')) c.push_back(f);
            if (c.size() < 4) continue;
            const int k = std::atoi(c[0].c_str());
            if (k >= 0 && k < NB) setLane(k, c[1], c[2], c[3]);
        }
    }

    void sampleRateChanged(double) override { updateLatency(); }
    void bufferSizeChanged(uint32_t) override { updateLatency(); }
    void activate() override { anchor_ = -1; }

    void initAudioPort(bool input, uint32_t index, AudioPort &port) override
    {
        if (input) { Plugin::initAudioPort(input, index, port); return; }
        port.hints = 0;
        if (index < 2) { port.name = index ? "Mix R" : "Mix L"; port.symbol = index ? "mix_r" : "mix_l"; port.groupId = kPortGroupStereo; return; }
        const int k = (int)(index - 2) / 2, r = (int)(index - 2) % 2;
        char n[32], s[32]; std::snprintf(n, sizeof n, "Ch %d %s", k + 1, r ? "R" : "L"); std::snprintf(s, sizeof s, "ch%d_%s", k + 1, r ? "r" : "l");
        port.name = n; port.symbol = s; port.groupId = 100 + k;
    }
    void initPortGroup(uint32_t groupId, PortGroup &g) override
    {
        if (groupId >= 100 && groupId < 100 + NB) { char n[32], s[32]; std::snprintf(n, sizeof n, "Ch %u", groupId - 99); std::snprintf(s, sizeof s, "ch%u", groupId - 99); g.name = n; g.symbol = s; return; }
        Plugin::initPortGroup(groupId, g);
    }

    void run(const float **, float **out, uint32_t frames, const MidiEvent *ev, uint32_t nev) override
    {
        bshm *S = sh_.S;
        S->host_beat++;
        audioAlive_ = nowSec();
        const double sr = getSampleRate(), ratio = 48000.0 / sr;
        const bool offline = isProcessingOffline() && !testLive_;
        if (offline) pumpReplies();
        housekeeping(offline);
        S->offline = offline ? 1 : 0;
        bool waited = false;
        if (engine_ && offline && S->state < BS_RUNNING) {
            for (int k = 0; k < 20000 && S->state < BS_RUNNING && S->state != BS_FAILED && !quit_; k++) {
                S->grant_until = S->dac_w + 48000; S->host_beat++;
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            waited = true;
        }
        for (uint32_t c = 0; c < 2 + 2 * NB; c++) std::memset(out[c], 0, frames * sizeof(float));
        if (S->state < BS_RUNNING || S->state == BS_FAILED) return;
        S->realtime = 1;
        // offline: wait for Windows (the assembly, a lane being built), so renders are exact
        if (offline && (!ready_.load() || building())) {
            for (int k = 0; k < 60000 && (!ready_.load() || building()) && S->state != BS_FAILED && !S->quit && !quit_; k++) {
                S->grant_until = S->dac_w + 48000; S->host_beat++;
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            S->grant_until = 0;
            pumpReplies();
            housekeeping(true);
            waited = true;
        }
        {   // the host's samples on the card's DAC: an integer anchor (as SNDWAVE1993)
            const TimePosition &tp = getTimePosition();
            if (tp.bbt.valid && tp.bbt.beatsPerMinute > 1) bpm_ = tp.bbt.beatsPerMinute;
            const double cur = anchor_ < 0 ? -1 : anchor_ + (double)hcount_ * ratio;
            const bool startT = tp.playing && !wasPlaying_;
            wasPlaying_ = tp.playing;
            if (anchor_ < 0 || startT || ratio != lastRatio_) {
                double a = cur < 0 ? (double)S->dac_w : std::ceil(cur);
                if ((double)S->dac_w > a + kLead) a = (double)S->dac_w - kLead;
                anchor_ = std::floor(a); hcount_ = 0; lastRatio_ = ratio;
            } else if (waited || (double)S->dac_w > cur + kLead + 24000) {
                const double jump = std::ceil((double)S->dac_w - kLead - cur);
                if (jump > 0) anchor_ += jump;
            }
        }
        // auditions from Windows (a click on a strip): C4 for half a second
        MidiEvent kev[16]; uint32_t nk = 0;
        for (uint32_t r = keyR_.load(), w = keyW_.load(std::memory_order_acquire); r != w && nk < 16; r++, nk++) {
            const uint32_t k = keyQ_[r % 64];
            kev[nk].frame = 0; kev[nk].size = 3; kev[nk].data[0] = (uint8_t)(k >> 16); kev[nk].data[1] = (uint8_t)(k >> 8); kev[nk].data[2] = (uint8_t)k;
            keyR_.store(r + 1);
        }
        for (uint32_t i = 0; i < nk + nev; i++) {
            const MidiEvent &e = i < nk ? kev[i] : ev[i - nk];
            const uint8_t *d = e.size > 4 ? e.dataExt : e.data;
            if (e.size < 2) continue;
            const int k = d[0] & 0x0F;
            if (k >= NB) continue;   // channels 11-16: no lane
            const uint64_t at = (uint64_t)std::floor(anchor_ + (double)(hcount_ + e.frame) * ratio) + kLatency48;
            const uint8_t st = d[0] & 0xF0;
            Lane &L = lanes_[k];
            if (!L.audioHas) continue;
            L.host.bpm = bpm_; L.host.capWin = L.host.capRate = L.host.capTape = true;
            char pre[8]; std::snprintf(pre, sizeof pre, "@%d ", k);
            L.host.midi(d[0], d[1], e.size >= 3 ? d[2] : 0, at, [&](const char *line, uint64_t when) {
                char b[192]; std::snprintf(b, sizeof b, "%s%s", pre, line); sendLine(b, ++nextId_, when);
                if (dumpDir_) { if (!trace_) { char f[600]; std::snprintf(f, sizeof f, "%s/lines.txt", dumpDir_); trace_ = std::fopen(f, "w"); }
                                if (trace_) std::fprintf(trace_, "%d %lld %s\n", k, (long long)when - (long long)anchor_, line); }
            });
            if (st == 0x90 && e.size >= 3 && d[2]) { char b[32]; std::snprintf(b, sizeof b, "@%d note %d %d", k, d[1], d[2]); sendLine(b, 0, 0); }
        }
        {
            const uint64_t upTo = (uint64_t)std::floor(anchor_ + (double)(hcount_ + frames) * ratio) + kLatency48;
            for (int k = 0; k < NB; k++) if (lanes_[k].audioHas) {
                char pre[8]; std::snprintf(pre, sizeof pre, "@%d ", k);
                lanes_[k].host.tick(upTo, [&](const char *line, uint64_t when) { char b[192]; std::snprintf(b, sizeof b, "%s%s", pre, line); sendLine(b, ++nextId_, when); });
            }
        }
        const double pos0 = anchor_ + (double)hcount_ * ratio, need = pos0 + frames * ratio + 3;
        for (int k = 0; offline && k < 400 && (double)S->dac_w < need && S->state != BS_FAILED && !S->quit && !quit_; k++) {
            S->grant_until = (uint64_t)std::ceil(need); S->host_beat++;
            std::this_thread::sleep_for(std::chrono::microseconds(500));
        }
        if (!offline) S->grant_until = 0;
        if ((double)S->dac_w < need) {   // a dropout: the machine is behind the host (counted apart once every lane is built)
            S->underruns++;
            if (ready_.load() && !building()) dropSong_++;
        }
        if (ready_.load() && !building()) blocksSong_++;
        // the lanes' buses, from the card: [first, last] DAC samples this block needs (4-point Hermite, as SNDWAVE1993)
        if (readLane_) {
            const int64_t first = (int64_t)std::floor(pos0) - 1, last = (int64_t)std::floor(pos0 + (frames - 1) * ratio) + 2;
            const int n = (int)(last - first + 1);
            if ((int)bus_.size() < n * 2) bus_.resize(n * 2);
            bool solo = false; for (int k = 0; k < NB; k++) if (param_[k * pPerLane + 3].load() >= 0.5f) solo = true;
            const float master = (float)std::pow(10.0, param_[pMaster].load() / 20.0);
            for (int k = 0; k < NB; k++) {
                if (!lanes_[k].audioHas) continue;
                const float lev = param_[k * pPerLane].load() / 100.f, pan = param_[k * pPerLane + 1].load() / 64.f;
                const bool on = param_[k * pPerLane + 2].load() < 0.5f && (!solo || param_[k * pPerLane + 3].load() >= 0.5f);
                const float g = lev * lev * (float)lanes_[k].gain;   // level: 100 = unity, squared (a fader's feel)
                const double th = (std::max(-1.f, std::min(1.f, pan)) + 1.0) * 0.25 * M_PI;   // constant power, centre = unity
                const float gl = g * (float)(std::cos(th) * M_SQRT2), gr = g * (float)(std::sin(th) * M_SQRT2);
                if (first < 0 || readLane_(k, (uint64_t)first, bus_.data(), n) != n) continue;
                float *OL = out[2 + 2 * k], *OR = out[3 + 2 * k];
                for (uint32_t i = 0; i < frames; i++) {
                    const double p = pos0 + (double)i * ratio; const int64_t j = (int64_t)std::floor(p) - first; const float f = (float)(p - std::floor(p));
                    float y[2];
                    for (int c = 0; c < 2; c++) {
                        const float y0 = bus_[(j - 1) * 2 + c], y1 = bus_[j * 2 + c], y2 = bus_[(j + 1) * 2 + c], y3 = bus_[(j + 2) * 2 + c];
                        const float c1 = 0.5f * (y2 - y0), c2 = y0 - 2.5f * y1 + 2.f * y2 - 0.5f * y3, c3 = 0.5f * (y3 - y0) + 1.5f * (y1 - y2);
                        y[c] = ((c3 * f + c2) * f + c1) * f + y1;
                    }
                    OL[i] = y[0] * gl; OR[i] = y[1] * gr;
                    if (on) { out[0][i] += OL[i] * master; out[1][i] += OR[i] * master; }
                }
                if (dumpDir_) {   // test: each lane's own output, raw stereo float, from the first block
                    if (!dump_[k]) { char f[600]; std::snprintf(f, sizeof f, "%s/lane%d.f32", dumpDir_, k); dump_[k] = std::fopen(f, "wb"); }
                    if (dump_[k]) for (uint32_t i = 0; i < frames; i++) { float v[2] = {OL[i], OR[i]}; std::fwrite(v, 4, 2, dump_[k]); }
                }
            }
        }
        hcount_ += frames;
        S->host_r = (uint64_t)std::max(0.0, anchor_ + (double)hcount_ * ratio - 4);
    }

private:
    // the engine keeps kLead DAC samples ahead of the host; notes are stamped kLatency48 ahead (60 ms at 1024).
    // ENSEMBLE_LEAD (test) trades latency for headroom: what a busy Windows needs to stay ahead of the host
    const uint32_t kLead = std::getenv("ENSEMBLE_LEAD") ? (uint32_t)std::max(256, std::atoi(std::getenv("ENSEMBLE_LEAD"))) : 1024u;
    uint32_t kLatency48 = kLead + 1536;
    void updateLatency()
    {
        const uint32_t block48 = (uint32_t)std::ceil(getBufferSize() * 48000.0 / getSampleRate());
        kLatency48 = std::max<uint32_t>(kLead + 1536, block48 + 2 * 672 + kLead);
        setLatency((uint32_t)std::lround(kLatency48 * getSampleRate() / 48000.0));
    }

    struct Lane {
        std::string pack, name, dna;           // what the lane plays (guarded by mtx_)
        bool dirty = false;                    // worker: send it to Windows
        bool building = false;                 // Windows is building it
        int cap = 0;
        // the audio thread's side
        b16v3::NoteHost host; bool audioHas = false; double gain = 1;
        // staged by the worker, adopted by the audio thread (housekeeping)
        bool pend = false; bsynth::Dna eff; bsynth3::Dna3 d3; uint32_t salt = 0;
        std::vector<std::vector<int>> pendLayers; std::vector<int> pendEnds; std::vector<std::pair<int, std::vector<uint32_t>>> pendSegs;
    };
    Lane lanes_[NB];
    mutable std::mutex mtx_;
    std::atomic<float> param_[pCount];
    std::atomic<uint32_t> mixDirty_{0};
    std::atomic<bool> ready_{false};
    bool building() { std::lock_guard<std::mutex> l(mtx_); for (auto &L : lanes_) if (L.building || L.dirty) return true; return false; }

    Basilisk16Shared sh_;
    bs_engine *engine_ = nullptr;
    std::thread worker_;
    std::atomic<bool> quit_{false};
    std::string tmp_, coreCopy_, conf_, recDir_, machine_;
    int (*readLane_)(int, uint64_t, float *, int) = nullptr;
    std::vector<float> bus_;
    double anchor_ = -1, lastRatio_ = 0; uint64_t hcount_ = 0; bool wasPlaying_ = false;
    std::atomic<double> bpm_{120}; std::atomic<double> audioAlive_{0};
    uint32_t nextId_ = 0;
    bool testLive_ = std::getenv("ENSEMBLE_TEST_LIVE") != nullptr;
    const char *dumpDir_ = std::getenv("ENSEMBLE_DUMP_DIR") && *std::getenv("ENSEMBLE_DUMP_DIR") ? std::getenv("ENSEMBLE_DUMP_DIR") : nullptr;
    FILE *dump_[NB] = {};
    std::string statsLine_; FILE *trace_ = nullptr;
    uint64_t dropSong_ = 0, blocksSong_ = 0;   // blocks the machine was behind in, once built; blocks once built
    uint32_t keyQ_[64]; std::atomic<uint32_t> keyR_{0}, keyW_{0};

    // a lane's sound: the cap (its recorders) from what it may play at once, the DNA staged for Windows and the audio
    void setLane(int k, const std::string &pack, const std::string &name, const std::string &dna)
    {
        std::lock_guard<std::mutex> l(mtx_);
        Lane &L = lanes_[k];
        L.pack = pack; L.name = name; L.dna = dna; L.dirty = !dna.empty();
    }
    static int capFor(const bsynth::Dna &d, const bsynth3::Dna3 &d3, const std::string &canon)
    {
        (void)canon;
        if (d3.g.kit()) return 16;   // a kit: every pad may ring at once (and its pads round-robin over all sixteen)
        int need = 0;
        for (auto &L : d.layers) need += std::min(16, 4 * (int)L.harmony.size() * std::max(1, L.unison));
        return std::max<int>((int)d.layers.size(), std::min(16, need));
    }
    void housekeeping(bool block = false)
    {
        if (block) mtx_.lock(); else if (!mtx_.try_lock()) return;
        for (auto &L : lanes_) {
            if (L.pend) {   // built: the new sound, its layers' recorders and segments, all at once
                L.host.adopt(L.eff, L.d3, L.salt); L.gain = std::pow(10.0, L.eff.g.gainDb / 20.0); L.audioHas = true; L.pend = false;
                for (auto &v : L.pendLayers) L.host.layerInfo(v[0], v[1], v[2], v[3], v[4]);
                for (auto &s : L.pendSegs) L.host.segments(s.first, s.second);
                L.pendLayers.clear(); L.pendSegs.clear();
            }
            for (int r : L.pendEnds) L.host.end(r);
            L.pendEnds.clear();
        }
        mtx_.unlock();
    }

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

    void status(const char *s) { std::snprintf(sh_.status, sizeof sh_.status, "%s", s); }
    void start()
    {
        const char *res = getResourcePath(getBundlePath());
        if (!res) { status("SNDWAVE1993 Ensemble: the machine files were not found next to the plugin."); sh_.S->state = BS_FAILED; return; }
        machine_ = std::string(res) + "/machine";
#ifdef _WIN32
        const char *coreName = "dosbox_pure_libretro.dll";
#else
        const char *coreName = "dosbox_pure_libretro.so";
#endif
        tmp_ = tempDir() + "sndwave-ensemble-" + std::to_string(processId()) + "-" + std::to_string(++gInstanceCounter);
#ifdef _WIN32
        CreateDirectoryA(tmp_.c_str(), nullptr);
#else
        mkdir(tmp_.c_str(), 0700);
#endif
        coreCopy_ = tmp_ + "/" + coreName; conf_ = tmp_ + "/w31.conf"; recDir_ = tmp_ + "/rec";
#ifdef _WIN32
        CreateDirectoryA(recDir_.c_str(), nullptr);
#else
        mkdir(recDir_.c_str(), 0700);
#endif
        if (!copyFile(machine_ + "/" + coreName, coreCopy_)) { status("SNDWAVE1993 Ensemble: cannot copy the emulator core."); sh_.S->state = BS_FAILED; return; }
        {
            std::ifstream in(machine_ + "/w31.conf"); std::string s((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
            std::string md = machine_, rd = recDir_;
#ifdef _WIN32
            for (auto &c : md) if (c == '/') c = '\\';
            for (auto &c : rd) if (c == '/') c = '\\';
#endif
            size_t p;
            while ((p = s.find("@MACHINE@")) != std::string::npos) s.replace(p, 9, "\"" + md + "\"");
            while ((p = s.find("@DRIVE@")) != std::string::npos) s.replace(p, 7, "\"" + md + "/drive\"");
            while ((p = s.find("@RECDIR@")) != std::string::npos) s.replace(p, 8, "\"" + rd + "\"");
            while ((p = s.find("@PACKS@")) != std::string::npos) s.replace(p, 7, "\"" + md + "/packs\"");
            if (!writeText(conf_, s)) { status("SNDWAVE1993 Ensemble: cannot write the machine settings."); sh_.S->state = BS_FAILED; return; }
        }
        {   // the library's and the packs' sound names, for the DNA parser (as SNDWAVE1993)
            std::vector<std::string> names; std::string l;
            std::ifstream a(machine_ + "/library.names.txt"); while (std::getline(a, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) names.push_back(l); }
            std::ifstream b(machine_ + "/packs/packs.names.txt"); while (std::getline(b, l)) { while (!l.empty() && (l.back() == '\r' || l.back() == ' ')) l.pop_back(); if (!l.empty()) names.push_back(l); }
            setLibrary(names);
        }
        loadCatalogue(machine_);
        defaultLanes();
        if (const char *lf = std::getenv("ENSEMBLE_LANES")) if (*lf) {   // test: lanes from a file (the state's lines)
            std::ifstream in(lf); std::string t((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
            if (!t.empty()) { for (int k = 0; k < NB; k++) setLane(k, "", "", ""); setState("ensemble", t.c_str()); }
        }
        status("Starting Windows for Workgroups 3.11...");
        const char *logEnv = std::getenv("ENSEMBLE_LOG");
        engine_ = bs_engine_start(sh_.S, coreCopy_.c_str(), conf_.c_str(), (machine_ + "/w31.state").c_str(), nullptr, logEnv && *logEnv ? logEnv : nullptr);
        worker_ = std::thread([this] { work(); });
    }
    void defaultLanes()   // a small band on the first channels, the kit on channel 10 (as General MIDI)
    {
        static const char *def[NB][2] = {{"rainy-loft", "Loft Tine Bright"}, {"rainy-loft", "Rubber Taxi"}, {"rainy-loft", "Couch Fort Lead"},
            {"rainy-loft", "Harbour Reed"}, {"rainy-loft", "Disco Clavinet"}, {"rainy-loft", "Daylight Strings"}, {"rainy-loft", "Vocoder Chorus"},
            {"rainy-loft", "Party Horns"}, {"", ""}, {"rainy-loft", "Couch Disco"}};
        for (int k = 0; k < NB; k++) {
            const int i = def[k][1][0] ? catFind(def[k][0], def[k][1]) : -1;
            if (i >= 0) { std::lock_guard<std::mutex> l(gCatMtx); setLane(k, gCat[i].pack, gCat[i].name, gCat[i].dna); }
        }
    }
    void cleanupTemp()
    {
        if (tmp_.empty()) return;
#ifdef _WIN32
        for (int k = 0; k < 20 && !DeleteFileA(coreCopy_.c_str()) && GetLastError() != ERROR_FILE_NOT_FOUND; k++) Sleep(25);
        RemoveDirectoryA(recDir_.c_str());
#else
        rmdir(recDir_.c_str());
#endif
        std::remove(coreCopy_.c_str()); std::remove(conf_.c_str());
#ifdef _WIN32
        RemoveDirectoryA(tmp_.c_str());
#else
        rmdir(tmp_.c_str());
#endif
    }
    void findLaneReader()
    {
#ifdef _WIN32
        HMODULE h = GetModuleHandleA(coreCopy_.c_str());
        if (h) readLane_ = (int (*)(int, uint64_t, float *, int))GetProcAddress(h, "bsyn_host_read_lane");
#else
        void *h = dlopen(coreCopy_.c_str(), RTLD_NOW | RTLD_NOLOAD);
        if (h) { readLane_ = (int (*)(int, uint64_t, float *, int))dlsym(h, "bsyn_host_read_lane"); dlclose(h); }
#endif
    }

    // the worker: Windows' replies, the lanes' sounds to Windows, the strips' mix both ways
    void work()
    {
        bshm *S = sh_.S;
        bool hello = false;
        while (!quit_) {
            if (nowSec() - audioAlive_.load() > 0.2) { S->realtime = 0; S->host_beat++; }
            if (S->state == BS_FAILED) { status(S->error); std::this_thread::sleep_for(std::chrono::milliseconds(50)); continue; }
            if (!hello && S->state >= BS_RUNNING) {
                hello = true;
                findLaneReader();
                std::string ids; { std::ifstream in(machine_ + "/packs/PACKS.TSV"); std::string l;
                    while (std::getline(in, l)) { const size_t a1 = l.find('\t'), a2 = a1 == std::string::npos ? a1 : l.find('\t', a1 + 1); if (a2 != std::string::npos) ids += (ids.empty() ? "" : ",") + l.substr(a1 + 1, a2 - a1 - 1); } }
                sendLine(("packs " + ids).c_str(), 0, 0);
                for (int k = 0; k < NB; k++) {   // names and mixes first: the assembly shows them
                    std::string nm; { std::lock_guard<std::mutex> l(mtx_); nm = lanes_[k].name; }
                    for (auto &c : nm) if (c == ' ') c = '_';
                    if (!nm.empty()) sendLine(("@" + std::to_string(k) + " name " + nm).c_str(), 0, 0);
                    mixToGuest(k);
                }
                sendLine("go", 0, 0);
            }
            if (hello) {
                const uint32_t md = mixDirty_.exchange(0);
                for (int k = 0; k < NB; k++) if (md >> k & 1) mixToGuest(k);
                for (int k = 0; k < NB; k++) {   // a lane's sound to Windows: one build at a time (Windows queues the rest)
                    std::string dna, name; bool go = false;
                    { std::lock_guard<std::mutex> l(mtx_); if (lanes_[k].dirty && ready_.load()) { go = true; dna = lanes_[k].dna; name = lanes_[k].name; lanes_[k].dirty = false; lanes_[k].building = true; } }
                    if (go) laneToGuest(k, dna, name);
                }
            }
            pumpReplies();
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
    }
    // Windows' replies: read by the worker live, and by the audio thread offline at the start of every block (the
    // machine stands still there), so a render's voice allocation sees each recorder's end at the same emulated time
    std::mutex repMtx_; std::vector<uint16_t> words_; std::string frag_;
    void pumpReplies()
    {
        bshm *S = sh_.S;
        std::lock_guard<std::mutex> g(repMtx_);
        while (S->rep_r != S->rep_w) { words_.push_back((uint16_t)S->rep[S->rep_r % BSHM_REP]); __sync_synchronize(); S->rep_r++; }
        size_t i = 0;
        while (i < words_.size()) {
            const int n = words_[i] & 0xFF ? words_[i] & 0xFF : 1;
            if (i + n > words_.size()) break;
            const int ty = words_[i] >> 8;
            if (ty == 3 || ty == 7) {
                for (int k = 1; k < n; k++) { const char a = (char)(words_[i + k] & 0xFF), b = (char)(words_[i + k] >> 8); if (a) frag_ += a; if (a && b) frag_ += b; }
                if (ty == 3) { onLine(frag_); frag_.clear(); }
            }
            i += n;
        }
        words_.erase(words_.begin(), words_.begin() + i);
    }
    void mixToGuest(int k)
    {
        char b[64]; std::snprintf(b, sizeof b, "@%d mix %d %d %d %d", k, (int)std::lround(param_[k * pPerLane].load()), (int)std::lround(param_[k * pPerLane + 1].load()),
                                  param_[k * pPerLane + 2].load() >= 0.5f, param_[k * pPerLane + 3].load() >= 0.5f);
        sendLine(b, 0, 0);
    }
    void laneToGuest(int k, const std::string &dnaText, const std::string &name)
    {
        const bsynth::Dna written = bsynth::parse(dnaText);
        bsynth::Dna eff = bsynth::applyMacros(written);
        bsynth3::Dna3 d3 = bsynth3::applyMacros3(bsynth3::parse3(written.canonical), written.g.macro);
        const std::string pre = "@" + std::to_string(k) + " ";
        int cap = capFor(eff, d3, written.canonical);
        if (const char *fc = std::getenv("ENSEMBLE_CAP")) if (std::atoi(fc) > 0) cap = std::min(16, std::atoi(fc));   // test: every lane this many
        {   // the budget: every lane's recorders together fit in Windows
            std::lock_guard<std::mutex> l(mtx_);
            int others = 0; for (int j = 0; j < NB; j++) if (j != k) others += lanes_[j].cap ? lanes_[j].cap : (lanes_[j].dna.empty() ? 1 : 8);
            const int budget = std::getenv("ENSEMBLE_BUDGET") ? std::atoi(std::getenv("ENSEMBLE_BUDGET")) : kRecBudget;
            if (others + cap > budget) cap = std::max<int>((int)eff.layers.size(), budget - others);
            lanes_[k].cap = cap;
            lanes_[k].eff = eff; lanes_[k].d3 = d3; lanes_[k].salt = b16v3::salt(written.canonical);
        }
        std::string nm = name; for (auto &c : nm) if (c == ' ') c = '_';
        sendLine((pre + "name " + nm).c_str(), 0, 0);
        sendLine((pre + "cap " + std::to_string(cap)).c_str(), 0, 0);
        sendLine((pre + "dna " + written.canonical).c_str(), 0, 0);
        char b[160]; proto::env(b, sizeof b, eff.g); b[std::strlen(b) - 1] = 0; sendLine((pre + b).c_str(), 0, 0);
        for (int i = 0; i < kMaxLayers; i++) {
            static const Env none;
            const Layer *Ly = i < (int)eff.layers.size() ? &eff.layers[i] : nullptr;
            sendLine((pre + b16v3::lenvLine(i, 'a', Ly ? Ly->envA : none, d3, bpm_.load(), true)).c_str(), 0, 0);
            sendLine((pre + b16v3::lenvLine(i, 'p', Ly ? Ly->envP : none, d3, bpm_.load(), true)).c_str(), 0, 0);
        }
    }
    void onLine(std::string l)
    {
        if (l == "ready") { ready_ = true; status(""); return; }
        if (l.rfind("stats ", 0) == 0) { statsLine_ = l; return; }
        if (l.rfind("mix ", 0) == 0) {   // Windows' strip moved: mix <lane> <level> <pan> <mute> <solo>
            int k, lv, pn, mu, so;
            if (std::sscanf(l.c_str() + 4, "%d %d %d %d %d", &k, &lv, &pn, &mu, &so) == 5 && k >= 0 && k < NB) {
                param_[k * pPerLane] = (float)lv; param_[k * pPerLane + 1] = (float)pn; param_[k * pPerLane + 2] = (float)mu; param_[k * pPerLane + 3] = (float)so;
            }
            return;
        }
        if (l.rfind("pick ", 0) == 0) {   // < or > on a strip: the previous or next preset of the catalogue
            int k = 0, d = 1; std::sscanf(l.c_str() + 5, "%d %d", &k, &d);
            if (k < 0 || k >= NB) return;
            std::string pack, name; { std::lock_guard<std::mutex> lk(mtx_); pack = lanes_[k].pack; name = lanes_[k].name; }
            int i = catFind(pack, name);
            std::lock_guard<std::mutex> g(gCatMtx);
            if (gCat.empty()) return;
            i = i < 0 ? 0 : (int)((i + d + (int)gCat.size()) % (int)gCat.size());
            setLane(k, gCat[i].pack, gCat[i].name, gCat[i].dna);
            return;
        }
        if (l.rfind("audition ", 0) == 0) {   // a click on a strip: its lane plays C4 (on, and off half a second later)
            const int k = std::atoi(l.c_str() + 9);
            if (k < 0 || k >= NB) return;
            const uint32_t w = keyW_.load(); keyQ_[w % 64] = ((0x90u | k) << 16) | (60 << 8) | 100; keyW_.store(w + 1, std::memory_order_release);
            std::thread([this, k] { std::this_thread::sleep_for(std::chrono::milliseconds(500)); const uint32_t w2 = keyW_.load(); keyQ_[w2 % 64] = ((0x80u | k) << 16) | (60 << 8); keyW_.store(w2 + 1, std::memory_order_release); }).detach();
            return;
        }
        if (l.size() < 3 || l[0] != '@') return;
        const int k = std::atoi(l.c_str() + 1);
        const size_t sp = l.find(' ');
        if (k < 0 || k >= NB || sp == std::string::npos) return;
        const std::string r = l.substr(sp + 1);
        std::lock_guard<std::mutex> g(mtx_);
        Lane &L = lanes_[k];
        if (r.rfind("seg ", 0) == 0) { std::istringstream in(r.substr(4)); int Ly = -1; in >> Ly; std::vector<uint32_t> v; uint32_t f; while (in >> f) v.push_back(f); L.pendSegs.push_back({Ly, v}); return; }
        proto::Reply rp = proto::parse(r);
        if (rp.kind == proto::Reply::Layer) L.pendLayers.push_back({rp.layer, rp.first, rp.count, rp.rate, rp.frames});
        else if (rp.kind == proto::Reply::Built) { L.building = false; L.pend = true; }
        else if (rp.kind == proto::Reply::End) L.pendEnds.push_back(rp.rec);
    }

    DISTRHO_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(Ensemble)
};

Plugin *createPlugin() { return new Ensemble(); }

Basilisk16Shared *basilisk16Shared(void *plugin) { return plugin ? static_cast<Ensemble *>(plugin)->shared() : nullptr; }

END_NAMESPACE_DISTRHO
