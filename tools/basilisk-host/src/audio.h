// BasiliskHost - WASAPI output (shared mode, event driven) and loopback capture
#pragma once
#include <atomic>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

struct AudioDevice { std::wstring id; std::string name; bool isDefault = false; };
std::vector<AudioDevice> audio_devices();
// the endpoint's master volume (0..1) and mute, or false when it cannot be read
bool endpoint_volume(const std::wstring &deviceId, float &vol, bool &muted);

class AudioOut {
public:
    // render(L, R, n): produce exactly n frames
    using RenderFn = std::function<void(float *, float *, int)>;
    ~AudioOut() { stop(); }
    bool start(const std::wstring &deviceId, int sampleRate, int block, RenderFn fn, std::string &err);
    void stop();
    bool running() const { return run_; }
    // what the device gave us
    int sampleRate = 0, block = 0, bufferFrames = 0, mixRate = 0, mixChannels = 0, mixBits = 0;
    double periodMs = 0, streamLatencyMs = 0;
    std::string deviceName;
    std::atomic<uint64_t> underruns{0}, framesOut{0};
    std::atomic<double> load{0};   // share of real time spent rendering
    float gain = 1.f;
private:
    void thread(std::wstring id, int sr, int blk);
    std::thread th_;
    std::atomic<bool> run_{false}, ready_{false}, failed_{false};
    std::string err_;
    RenderFn fn_;
};

// records what the device plays (all applications), for checking that sound reaches it
class Loopback {
public:
    ~Loopback() { stop(); }
    bool start(const std::wstring &deviceId, std::string &err);
    std::vector<float> stop();   // interleaved stereo at `sampleRate`
    int sampleRate = 0;
private:
    std::thread th_;
    std::atomic<bool> run_{false};
    std::vector<float> data_;
    std::mutex m_;
};
