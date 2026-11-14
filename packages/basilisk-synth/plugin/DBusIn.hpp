// BASILISK SYNTH - recording input (RECORDING.md 1.2): the DAW's audio into XP's second, input-only AC97.
//
// QEMU backs that card with `-audiodev dbus` and exports it on its peer-to-peer D-Bus display connection. We are
// the peer: we register an org.qemu.Display1.AudioInListener, and QEMU calls our Read on its own clock. Read is
// answered from a ring the plugin's process() fills (resampled to the card's rate, drift-corrected by the fill
// level). Nothing touches the host's sound devices. Proven in X0 (tools/x0/dbuspeer.py) on macOS and Windows.
#pragma once
#include <atomic>
#include <functional>
#include <cstdint>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace bsynth {

// a single-producer (process()) single-consumer (Read) ring of interleaved s16 stereo frames
class InputRing {
public:
    explicit InputRing(size_t frames = 48000 * 2) : buf_(frames * 2) {}
    void write(const int16_t *lr, size_t frames);        // audio thread
    size_t read(int16_t *lr, size_t frames);             // D-Bus thread; returns the frames copied (only those in hand)
    size_t fill() const { return w_.load() - r_.load(); }
    void clear() { r_.store(w_.load()); primed_ = false; }
    size_t cushion_ = 48000 * 40 / 1000;               // 40 ms in hand before the reader starts
    uint64_t underruns() const { return under_.load(); }
private:
    std::vector<int16_t> buf_;
    std::atomic<size_t> w_{0}, r_{0};
    std::atomic<uint64_t> under_{0};
    bool primed_ = false;   // (reader thread only)
};

class DBusIn {
public:
    // qmp: a function sending one QMP command (JSON) and returning the reply line; fdname is registered first
    // Unix: qmpUnixPath is a Unix-socket QMP (fd passing needs SCM_RIGHTS). Windows: qemuPid for WSADuplicateSocket.
    bool start(const std::string &qmpUnixPath, int qmpTcpPort, unsigned long qemuPid);
    void stop();
    bool connected() const { return connected_.load(); }
    unsigned rate() const { return rate_.load(); }      // the card's input rate from Init (0 until then)
    bool enabled() const { return enabled_.load(); }    // XP has a recording open
    uint64_t reads() const { return reads_.load(); }
    InputRing ring;
    std::string error;

    // the screen (EMULATOR-TUNING.md 5): a display listener on the same connection. QEMU pushes every change as it
    // happens (Scanout/Update, or ScanoutMap/UpdateMap over shared memory on macOS), so nothing polls and an idle
    // screen costs nothing. fn gets each changed rectangle in QEMU's pixman format.
    using RectFn = std::function<void(int x, int y, int w, int h, const uint8_t *p, uint32_t stride, uint32_t fmt)>;
    bool startDisplay(RectFn fn, unsigned long qemuPid);
    bool displayOn() const { return displayOn_.load(); }
    uint64_t displayUpdates() const { return updates_.load(); }
    bool displayMapped() const { return mapped_.load(); }
    std::string displayError;
private:
    void serve(intptr_t s);
    void serveDisplay(intptr_t s);
    RectFn rect_;
    std::thread dth_;
    intptr_t dlistener_ = -1;
    std::string connBuf_;
    std::atomic<bool> displayOn_{false}, mapped_{false};
    std::atomic<uint64_t> updates_{0};
    std::thread th_;
    intptr_t conn_ = -1, listener_ = -1;
    std::atomic<bool> stop_{false}, connected_{false}, enabled_{false};
    std::atomic<unsigned> rate_{0};
    std::atomic<uint64_t> reads_{0};
};

}  // namespace bsynth
