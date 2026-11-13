// bsynth-host - a small VST3 host for testing BASILISK SYNTH the way a DAW drives it, without a DAW.
//
//   bsynth-host PLUGIN.vst3 OUT.wav [options]
//     --score "t:note:vel:dur,..."   notes (seconds); default: a C major scale, then a chord
//     --warmup S          seconds of silent processing before the score (the machine wakes meanwhile)
//     --tail S            seconds after the last note
//     --offline           process as fast as the plugin allows, with processMode kOffline
//     --instances K       K instances side by side (each renders OUT-k.wav)
//     --save-state F      write the component state after rendering
//     --load-state F      set the component state before rendering
//     --dna TEXT          set the state to this DNA before rendering
//     --sr HZ --block N
// It prints the reported latency, timing and peak levels. Output: 32-bit float stereo WAV.
#include "public.sdk/source/vst/hosting/module.h"
#include "public.sdk/source/vst/hosting/hostclasses.h"
#include "public.sdk/source/vst/hosting/plugprovider.h"
#include "public.sdk/source/vst/hosting/processdata.h"
#include "public.sdk/source/vst/hosting/eventlist.h"
#include "public.sdk/source/vst/hosting/parameterchanges.h"
#include "public.sdk/source/vst/utility/stringconvert.h"
#include "public.sdk/source/common/memorystream.h"
#include "pluginterfaces/vst/ivstaudioprocessor.h"
#include "pluginterfaces/vst/ivsteditcontroller.h"
#include "pluginterfaces/vst/ivstprocesscontext.h"

#ifdef _WIN32
#include <windows.h>
#endif
#include "pluginterfaces/gui/iplugview.h"
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <memory>
#include <string>
#include <thread>
#include <vector>

using namespace Steinberg;
using namespace Steinberg::Vst;

static double now() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

struct Note { double t, dur; int note, vel; };

static void write_wav(const std::string &path, const std::vector<float> &lr, int sr)
{
    std::ofstream f(path, std::ios::binary);
    uint32_t n = (uint32_t)lr.size() * 4;
    auto u32 = [&](uint32_t v) { f.write((const char *)&v, 4); };
    auto u16 = [&](uint16_t v) { f.write((const char *)&v, 2); };
    f.write("RIFF", 4); u32(36 + n); f.write("WAVEfmt ", 8); u32(16); u16(3); u16(2); u32(sr); u32(sr * 8); u16(8); u16(32);
    f.write("data", 4); u32(n);
    f.write((const char *)lr.data(), n);
}

struct Instance {
    IPtr<PlugProvider> provider;
    IComponent *comp = nullptr;
    IEditController *ctl = nullptr;
    FUnknownPtr<IAudioProcessor> proc;
    HostProcessData data;
    EventList events;
    ParameterChanges outParams;
    std::vector<float> out;
};

int main(int argc, char **argv)
{
    if (argc < 3) { fprintf(stderr, "usage: bsynth-host PLUGIN.vst3 OUT.wav [options]\n"); return 2; }
    std::string plugin = argv[1], outPath = argv[2], score, saveState, loadState, dna;
    double warmup = 8, tail = 2, sr = 48000;
    int block = 512, ninst = 1;
    bool offline = false;
    double shotEvery = 0;       // --shots S: with --editor, a screenshot of the editor every S seconds
    std::string shotDir;
    bool editor = false;
    for (int i = 3; i < argc; i++) {
        std::string a = argv[i];
        auto next = [&]() { return i + 1 < argc ? std::string(argv[++i]) : std::string(); };
        if (a == "--score") score = next();
        else if (a == "--warmup") warmup = atof(next().c_str());
        else if (a == "--tail") tail = atof(next().c_str());
        else if (a == "--offline") offline = true;
        else if (a == "--instances") ninst = atoi(next().c_str());
        else if (a == "--save-state") saveState = next();
        else if (a == "--load-state") loadState = next();
        else if (a == "--dna") dna = next();
        else if (a == "--sr") sr = atof(next().c_str());
        else if (a == "--block") block = atoi(next().c_str());
        else if (a == "--editor") editor = true;
        else if (a == "--shots") { shotEvery = atof(next().c_str()); shotDir = next(); }
    }
    std::vector<Note> notes;
    if (score.empty()) {
        int sc[] = {60, 62, 64, 65, 67, 69, 71, 72};
        for (int k = 0; k < 8; k++) notes.push_back({0.5 * k, 0.4, sc[k], 100});
        notes.push_back({4.5, 1.5, 60, 100}); notes.push_back({4.5, 1.5, 64, 100}); notes.push_back({4.5, 1.5, 67, 100});
    } else {
        size_t p = 0;
        while (p < score.size()) {
            size_t q = score.find(',', p);
            std::string it = score.substr(p, q == std::string::npos ? std::string::npos : q - p);
            Note n{};
            if (sscanf(it.c_str(), "%lf:%d:%d:%lf", &n.t, &n.note, &n.vel, &n.dur) == 4) notes.push_back(n);
            if (q == std::string::npos) break;
            p = q + 1;
        }
    }
    double last = 0;
    for (auto &n : notes) last = std::max(last, n.t + n.dur);

    std::string err;
    auto module = VST3::Hosting::Module::create(plugin, err);
    if (!module) { fprintf(stderr, "load failed: %s\n", err.c_str()); return 1; }
    HostApplication hostApp;
    PluginContextFactory::instance().setPluginContext(&hostApp);
    auto factory = module->getFactory();
    VST3::Hosting::ClassInfo info;
    bool found = false;
    for (auto &ci : factory.classInfos()) if (ci.category() == kVstAudioEffectClass) { info = ci; found = true; break; }
    if (!found) { fprintf(stderr, "no audio class\n"); return 1; }
    printf("plugin: %s (%s)\n", info.name().c_str(), info.vendor().c_str());

    std::vector<std::unique_ptr<Instance>> ins;
    double t0 = now();
    for (int k = 0; k < ninst; k++) {
        auto I = std::make_unique<Instance>();
        I->provider = owned(new PlugProvider(factory, info, true));
        if (!I->provider->initialize()) { fprintf(stderr, "initialize failed\n"); return 1; }
        I->comp = I->provider->getComponentPtr();
        I->ctl = I->provider->getControllerPtr();
        I->proc = FUnknownPtr<IAudioProcessor>(I->comp);
        ProcessSetup setup{offline ? kOffline : kRealtime, kSample32, block, sr};
        I->proc->setupProcessing(setup);
        I->comp->activateBus(kAudio, kOutput, 0, true);
        I->comp->activateBus(kEvent, kInput, 0, true);
        if (!loadState.empty() || !dna.empty()) {
            std::vector<char> st;
            if (!loadState.empty()) { std::ifstream f(loadState, std::ios::binary); st.assign(std::istreambuf_iterator<char>(f), {}); }
            else {
                // DPF's VST3 state: NUL-separated sections, ending in 0xfe
                std::string s = std::string("__dpf_state_begin__") + '\0' + "dna" + '\0' + dna + '\0' + "__dpf_state_end__" + '\0' + '\xfe';
                st.assign(s.begin(), s.end());
            }
            MemoryStream ms;
            int32 w = 0;
            ms.write(st.data(), (int32)st.size(), &w);
            ms.seek(0, IBStream::kIBSeekSet, nullptr);
            tresult r = I->comp->setState(&ms);
            ms.seek(0, IBStream::kIBSeekSet, nullptr);
            if (I->ctl) I->ctl->setComponentState(&ms);
            printf("instance %d: setState %s (%d bytes)\n", k, r == kResultOk ? "ok" : "FAILED", (int)st.size());
        }
        I->comp->setActive(true);
        I->proc->setProcessing(true);
        I->data.prepare(*I->comp, block, kSample32);
        I->data.inputEvents = &I->events;
        I->data.outputParameterChanges = &I->outParams;
        printf("instance %d: latency %u samples (%.1f ms)\n", k, I->proc->getLatencySamples(), I->proc->getLatencySamples() * 1000.0 / sr);
        ins.push_back(std::move(I));
    }
    printf("loaded %d instance(s) in %.2f s\n", ninst, now() - t0);


#ifdef _WIN32
    // the editor, in a plain window of our own, as a DAW would host it
    HWND win = NULL;
    IPtr<IPlugView> view;
    if (editor && ins[0]->ctl) {
        view = owned(ins[0]->ctl->createView(ViewType::kEditor));
        if (view) {
            ViewRect vr;
            view->getSize(&vr);
            WNDCLASSA wc = {};
            wc.lpfnWndProc = DefWindowProcA; wc.hInstance = GetModuleHandleA(NULL); wc.lpszClassName = "bsynthhost";
            wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
            RegisterClassA(&wc);
            RECT r = {0, 0, vr.getWidth(), vr.getHeight()};
            AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
            win = CreateWindowA("bsynthhost", "bsynth-host", WS_OVERLAPPEDWINDOW | WS_VISIBLE, 40, 40, r.right - r.left, r.bottom - r.top, NULL, NULL, wc.hInstance, NULL);
            SetWindowPos(win, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE);
            tresult ar = view->attached(win, kPlatformTypeHWND);
            printf("editor %dx%d attached: %s\n", vr.getWidth(), vr.getHeight(), ar == kResultOk ? "ok" : "FAILED");
        }
    }
    auto pump = [&]() { MSG m; while (PeekMessageA(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessageA(&m); } };
    int shotN = 0;
    auto shot = [&](double t) {
        if (!win || shotDir.empty()) return;
        RECT cr; GetClientRect(win, &cr);
        POINT o = {0, 0}; ClientToScreen(win, &o);
        int w = cr.right, h = cr.bottom;
        HDC sdc = GetDC(NULL), mdc = CreateCompatibleDC(sdc);
        HBITMAP bm = CreateCompatibleBitmap(sdc, w, h);
        SelectObject(mdc, bm);
        BitBlt(mdc, 0, 0, w, h, sdc, o.x, o.y, SRCCOPY);
        BITMAPINFOHEADER bi = {sizeof bi, w, -h, 1, 24, BI_RGB};
        int stride = (w * 3 + 3) & ~3;
        std::vector<char> px((size_t)stride * h);
        GetDIBits(mdc, bm, 0, h, px.data(), (BITMAPINFO *)&bi, DIB_RGB_COLORS);
        char name[512];
        snprintf(name, sizeof name, "%s\\%06d.bmp", shotDir.c_str(), (int)(t * 1000));
        std::ofstream f(name, std::ios::binary);
        BITMAPFILEHEADER fh = {0x4D42, (DWORD)(sizeof fh + sizeof bi + px.size()), 0, 0, (DWORD)(sizeof fh + sizeof bi)};
        bi.biHeight = -h;
        f.write((char *)&fh, sizeof fh); f.write((char *)&bi, sizeof bi); f.write(px.data(), px.size());
        DeleteObject(bm); DeleteDC(mdc); ReleaseDC(NULL, sdc);
        shotN++;
    };
#else
    auto pump = []() {};
    auto shot = [](double) {};
#endif
    double nextShot = 0;
    const int64_t total = (int64_t)((warmup + last + tail) * sr), w0 = (int64_t)(warmup * sr);
    int64_t pos = 0;
    double start = now(), maxLate = 0;
    ProcessContext ctx = {};
    ctx.sampleRate = sr;
    while (pos < total) {
        for (size_t k = 0; k < ins.size(); k++) {
            Instance &I = *ins[k];
            I.events.clear();
            for (auto &n : notes) {
                int64_t on = w0 + (int64_t)(n.t * sr), off = w0 + (int64_t)((n.t + n.dur) * sr);
                for (int e = 0; e < 2; e++) {
                    int64_t at = e ? off : on;
                    if (at >= pos && at < pos + block) {
                        Event ev = {};
                        ev.sampleOffset = (int32)(at - pos);
                        if (!e) { ev.type = Event::kNoteOnEvent; ev.noteOn.pitch = (int16)n.note; ev.noteOn.velocity = n.vel / 127.f; ev.noteOn.noteId = -1; }
                        else { ev.type = Event::kNoteOffEvent; ev.noteOff.pitch = (int16)n.note; ev.noteOff.velocity = 0; ev.noteOff.noteId = -1; }
                        I.events.addEvent(ev);
                    }
                }
            }
            ctx.projectTimeSamples = pos;
            // the transport "plays" from one second before the first note, as when a DAW starts a bar early
            ctx.state = (pos >= w0 - (int64_t)sr ? ProcessContext::kPlaying : 0);
            I.data.processContext = &ctx;
            I.data.numSamples = block;
            I.outParams.clearQueue();
            I.proc->process(I.data);
            float *L = I.data.outputs[0].channelBuffers32[0], *R = I.data.outputs[0].channelBuffers32[1];
            for (int i = 0; i < block; i++) { I.out.push_back(L[i]); I.out.push_back(R[i]); }
        }
        pos += block;
        pump();
        if (shotEvery > 0 && pos / sr >= nextShot) { shot(pos / sr); nextShot += shotEvery; }
        if (!offline) {   // real time: one block per block-length of wall clock
            double due = start + pos / sr, n = now();
            if (due > n) std::this_thread::sleep_for(std::chrono::duration<double>(due - n));
            else maxLate = std::max(maxLate, n - due);
        }
    }
    double took = now() - start;
    printf("rendered %.1f s of audio in %.1f s%s\n", total / sr, took, offline ? " (offline)" : "");
    for (size_t k = 0; k < ins.size(); k++) {
        Instance &I = *ins[k];
        float pk = 0;
        for (float v : I.out) pk = std::max(pk, std::fabs(v));
        std::string p = outPath;
        if (ins.size() > 1) { size_t d = p.rfind('.'); p = p.substr(0, d) + "-" + std::to_string(k) + p.substr(d); }
        write_wav(p, I.out, (int)sr);
        printf("instance %zu: peak %.3f -> %s\n", k, pk, p.c_str());
        if (!saveState.empty() && k == 0) {
            MemoryStream ms;
            I.comp->getState(&ms);
            std::ofstream f(saveState, std::ios::binary);
            f.write(ms.getData(), ms.getSize());
            printf("state saved: %lld bytes\n", (long long)ms.getSize());
        }
    }
#ifdef _WIN32
    if (view) { view->removed(); view = nullptr; }
    if (win) DestroyWindow(win);
#endif
    t0 = now();
    for (auto &I : ins) {
        I->proc->setProcessing(false);
        I->comp->setActive(false);
        I->provider = nullptr;
    }
    ins.clear();
    printf("unloaded in %.2f s\n", now() - t0);
    return 0;
}
