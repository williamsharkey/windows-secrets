// BasiliskHost - real-time engine (see engine.h)
#include "engine.h"
#include <algorithm>
#include <cmath>
#include <cstring>

Engine::~Engine() { stopAudio(); }

bool Engine::startAudio(const std::wstring &device, int rate, int blk, std::string &err)
{
    stopAudio();
    sr = rate;
    block = blk;
    {
        std::lock_guard<std::mutex> g(mx_);
        for (auto &I : ins_) I->setup(sr, block, false);
    }
    pos = 0;
    return out.start(device, sr, block, [this](float *L, float *R, int n) { render(L, R, n); }, err);
}

void Engine::stopAudio() { out.stop(); }

void Engine::addInstance(std::shared_ptr<Instance> I)
{
    I->setup(sr, block, false);
    std::lock_guard<std::mutex> g(mx_);
    ins_.push_back(I);
}

void Engine::removeInstance(Instance *I)
{
    std::shared_ptr<Instance> keep;
    {
        std::lock_guard<std::mutex> g(mx_);
        for (auto it = ins_.begin(); it != ins_.end(); ++it)
            if (it->get() == I) { keep = *it; ins_.erase(it); break; }
    }
    if (keep) keep->shutdown();
    // `keep` goes here: the plugin is released on the caller's (UI) thread
}

std::vector<std::shared_ptr<Instance>> Engine::list()
{
    std::lock_guard<std::mutex> g(mx_);
    return ins_;
}

void Engine::route(const MidiMsg &m, int32 offset)
{
    int ty = m.st & 0xF0;
    if (ty == 0x90 && m.d2 > 0) keys[m.d1]++;
    else if ((ty == 0x80 || ty == 0x90) && keys[m.d1] > 0) keys[m.d1]--;
    int t = target;
    for (auto &I : ins_)
        if (t == 0 || I->number == t) I->queueMidi(m, offset);
}

void Engine::midi(const MidiMsg &m)
{
    std::lock_guard<std::mutex> g(mx_);
    route(m, 0);
}

void Engine::play(const Score &s)
{
    std::lock_guard<std::mutex> g(seqm_);
    seq_ = s;
    seqIdx_ = 0;
    seqT_ = 0;
    seqLen_ = s.length;
    seqOn_ = true;
}

void Engine::stopPlay()
{
    {
        std::lock_guard<std::mutex> g(seqm_);
        seqOn_ = false;
    }
    panic();
}

void Engine::panic()
{
    std::lock_guard<std::mutex> g(mx_);
    for (auto &I : ins_) {
        I->queueMidi({0, 0xB0, 64, 0});
        I->allNotesOff();
    }
    for (auto &k : keys) k = 0;
}

void Engine::startTap()
{
    std::lock_guard<std::mutex> g(tapm_);
    tapData_.clear();
    tapData_.reserve((size_t)sr * 2 * 120);
    tap_ = true;
}

std::vector<float> Engine::stopTap()
{
    std::lock_guard<std::mutex> g(tapm_);
    tap_ = false;
    std::vector<float> v;
    v.swap(tapData_);
    return v;
}

void Engine::render(float *L, float *R, int n)
{
    memset(L, 0, sizeof(float) * n);
    memset(R, 0, sizeof(float) * n);
    std::lock_guard<std::mutex> g(mx_);
    {   // sequencer events falling in this block
        std::unique_lock<std::mutex> s(seqm_, std::try_to_lock);
        if (s.owns_lock() && seqOn_) {
            double t0 = seqT_, t1 = t0 + (double)n / sr;
            while (seqIdx_ < seq_.msgs.size() && seq_.msgs[seqIdx_].t < t1) {
                const MidiMsg &m = seq_.msgs[seqIdx_++];
                int32 off = (int32)std::max(0.0, std::floor((m.t - t0) * sr));
                route(m, std::min(off, n - 1));
            }
            seqT_ = t1;
            if (seqIdx_ >= seq_.msgs.size() && t1 > seq_.length + 0.5) seqOn_ = false;
        }
    }
    for (auto &I : ins_) {
        I->process(n, pos, sr, true);
        float *a = I->outL(), *b = I->outR();
        for (int i = 0; i < n; i++) { L[i] += a[i]; R[i] += b[i]; }
    }
    pos += n;
    float pk = 0;
    for (int i = 0; i < n; i++) pk = std::max(pk, std::max(std::fabs(L[i]), std::fabs(R[i])));
    peak = std::max(peak.load() * 0.9f, pk);
    if (tap_) {
        std::lock_guard<std::mutex> t(tapm_);
        for (int i = 0; i < n; i++) { tapData_.push_back(L[i]); tapData_.push_back(R[i]); }
    }
}
