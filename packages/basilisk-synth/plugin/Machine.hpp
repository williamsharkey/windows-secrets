// BASILISK SYNTH - the Windows XP machine behind one plugin instance.
//
// Each instance runs its own QEMU (a child process, never a window of its own):
//   - its own throwaway overlay over the shared, read-only machine disk
//   - resumed from the shipped machine state (a migration stream sent over loopback TCP) in 1-2 seconds
//   - XP's AC97 sound card goes to QEMU's "wav" audiodev, whose file is a pipe that this class drains;
//     that stream IS the instrument's sound
//   - COM1 is the guest link (DNA.md section 4)
//   - VNC is the screen and the visitor's mouse and keys
// Everything here runs on its own threads. The audio thread only touches the lock-free rings.
#pragma once
#include "DBusIn.hpp"
#include <atomic>
#include <cstdint>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace bsynth {

// single producer, single consumer
template <typename T> class Spsc {
public:
    explicit Spsc(size_t pow2) : buf_(pow2), mask_(pow2 - 1) {}
    bool push(const T &v)
    {
        size_t w = w_.load(std::memory_order_relaxed);
        if (w - r_.load(std::memory_order_acquire) >= buf_.size()) return false;
        buf_[w & mask_] = v;
        w_.store(w + 1, std::memory_order_release);
        return true;
    }
    bool pop(T &v)
    {
        size_t r = r_.load(std::memory_order_relaxed);
        if (r == w_.load(std::memory_order_acquire)) return false;
        v = buf_[r & mask_];
        r_.store(r + 1, std::memory_order_release);
        return true;
    }
private:
    std::vector<T> buf_;
    size_t mask_;
    std::atomic<size_t> w_{0}, r_{0};
};

struct Line { char s[96]; };

// XP's sound, 96 kHz stereo float, written by the pipe reader, read by the audio thread.
// The writer never waits: if the audio thread falls far behind, the oldest audio is dropped.
class AudioRing {
public:
    static constexpr size_t kSize = 1 << 19;   // ~5.4 s at 96 kHz
    void write(const float *lr, size_t frames)
    {
        uint64_t w = w_.load(std::memory_order_relaxed);
        for (size_t i = 0; i < frames; i++) { l_[(w + i) & (kSize - 1)] = lr[2 * i]; r_[(w + i) & (kSize - 1)] = lr[2 * i + 1]; }
        w_.store(w + frames, std::memory_order_release);
    }
    uint64_t written() const { return w_.load(std::memory_order_acquire); }
    float L(uint64_t i) const { return l_[i & (kSize - 1)]; }
    float R(uint64_t i) const { return r_[i & (kSize - 1)]; }
private:
    std::vector<float> l_ = std::vector<float>(kSize), r_ = std::vector<float>(kSize);
    std::atomic<uint64_t> w_{0};
};

class Machine {
public:
    enum Phase { Off, Fetching, Unpacking, Starting, Resuming, Running, Failed };

    Machine();
    ~Machine();
    void start();            // non-blocking; idempotent
    void stop();             // blocking, quick: QEMU is gone when it returns
    void restart();          // stop, then start a fresh QEMU (the watchdog: a machine that went silent)

    // the guest link: any thread may queue (the audio thread does); the link thread sends
    void send(const char *line);
    // XP under emulation never really idles (its idle loop spins, ~75% of a core per vCPU), so the machine is
    // paused after a few quiet seconds and resumed by the next note: touch() whenever it must stay awake
    // (voices sounding, editor open). Lock-free; the audio thread may call it.
    void touch() { lastTouch_.store(now(), std::memory_order_relaxed); }
    std::atomic<bool> asleep{false};
    std::atomic<bool> keepAwake{false};
    std::atomic<bool> capWin{false}, capRate{false}, capKit{false};   // the guest's DNA v3 caps (hi 3)   // the plugin waits for its sounds to be built: no sleep meanwhile
    void sendLong(const std::string &line);   // a long line (a DNA); not from the audio thread
    // lines from the guest, for the plugin's own thread (not the audio thread)
    bool popReply(std::string &line);

    // the screen (VNC): RGBA, kW x kH
    static constexpr int kW = 1024, kH = 768;
    static constexpr double kSleepAfter = 4.0;   // seconds of quiet before the machine is paused
    bool frame(std::vector<uint8_t> &rgba, int &x0, int &y0, int &x1, int &y1);   // copies if changed
    void pointer(int x, int y, int buttons);
    void key(uint32_t keysym, bool down);

    AudioRing audio;
    DBusIn input;          // the DAW's audio into XP's recording card (RECORDING.md 1.2)
    std::atomic<uint64_t> gapsIn_{0};   // exact-silence runs >= 5 ms in XP's stream that cut a sound off
    size_t zeroRun_ = 0; float lastLevel_ = 0;
    std::atomic<int> phase{Off};
    std::atomic<float> progress{0};       // Fetching/Unpacking: 0..1
    std::atomic<double> resumedAt{0};     // seconds (monotonic) when XP started running
    std::atomic<bool> ready{false};       // the guest said ready (assembled)
    std::atomic<bool> linked{false};      // the guest answered hi
    std::string error() { std::lock_guard<std::mutex> g(mu_); return error_; }
    std::string status() { std::lock_guard<std::mutex> g(mu_); return status_; }
    static double now();
    static void log(const char *fmt, ...);
    static std::string machineDir();
    static std::string cacheDir();

private:
    void run();
    bool ensureMachine();
    bool launch();
    bool resume();
    void linkLoop();
    void audioLoop();
    void vncLoop();
    void blit(int x, int y, int w, int h, const uint8_t *p, uint32_t stride, uint32_t fmt);
    std::atomic<bool> dbusFrames_{false};
    std::atomic<bool> screenWanted_{false};
    unsigned long qpid_ = 0;
public:
    // an editor is open: the screen comes (D-Bus display listener, else VNC); none open: no screen work at all
    void wantScreen(bool w);
private:
    void fail(const std::string &e);
    void setStatus(const std::string &s);
    void kill();

    std::thread main_, audio_, vnc_;
    std::atomic<bool> stopping_{false};
    std::atomic<double> lastTouch_{0}, lastOn_{0};
    double armed_ = 0, lastDump_ = 0;
    const char *dumpDir_ = nullptr;
    bool dbgArrival_ = false;
    std::mutex mu_;
    std::string error_, status_;

    Spsc<Line> out_{1024};
    std::mutex longMu_;
    std::vector<std::string> long_;
    std::mutex inMu_;
    std::vector<std::string> in_;

    // screen
    std::mutex fbMu_;
    std::vector<uint8_t> fb_;
    int dx0_ = kW, dy0_ = kH, dx1_ = 0, dy1_ = 0;
    std::mutex vncSendMu_;
    intptr_t vncSock_ = -1;

    // process and endpoints
    std::string tmp_, overlay_, pipePath_;
    int portQmp_ = 0, portCom_ = 0, portVnc_ = 0, portMig_ = 0;
    intptr_t com_ = -1;
#ifdef _WIN32
    void *proc_ = nullptr, *job_ = nullptr, *pipe_ = nullptr;
#else
    int pid_ = -1, watchdog_ = -1, fifo_ = -1;
#endif
};

}  // namespace bsynth
