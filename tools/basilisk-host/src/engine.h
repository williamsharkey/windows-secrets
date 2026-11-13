// BasiliskHost - the real-time engine: instances, MIDI routing, sequencer, mixing, output tap
#pragma once
#include "audio.h"
#include "host.h"
#include "midi.h"

class Engine {
public:
    ~Engine();
    bool startAudio(const std::wstring &device, int sr, int block, std::string &err);
    void stopAudio();
    void addInstance(std::shared_ptr<Instance> I);   // set up for the current rate/block, then mixed
    void removeInstance(Instance *I);
    std::vector<std::shared_ptr<Instance>> list();

    // MIDI from anywhere (UI thread, winmm thread): to instance `target` (number), or to all when target == 0
    void midi(const MidiMsg &m);
    std::atomic<int> target{0};
    // the sequencer (MIDI files, test pattern)
    void play(const Score &s);
    void stopPlay();
    bool playing() const { return seqOn_; }
    double playPos() const { return seqT_; }
    double playLength() const { return seqLen_; }
    void panic();

    std::atomic<uint8_t> keys[128] = {};   // notes sounding (for the on-screen keyboard)

    // output tap: everything the host sends to the device, before the output gain
    void startTap();
    std::vector<float> stopTap();
    bool tapping() const { return tap_; }

    void render(float *L, float *R, int n);
    AudioOut out;
    int sr = 48000, block = 512;
    int64_t pos = 0;
    std::atomic<float> peak{0};

private:
    void route(const MidiMsg &m, int32 offset);
    std::mutex mx_;
    std::vector<std::shared_ptr<Instance>> ins_;
    std::mutex seqm_;
    Score seq_;
    size_t seqIdx_ = 0;
    std::atomic<bool> seqOn_{false};
    std::atomic<double> seqT_{0}, seqLen_{0};
    std::mutex tapm_;
    std::atomic<bool> tap_{false};
    std::vector<float> tapData_;
};
