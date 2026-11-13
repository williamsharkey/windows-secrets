// BasiliskHost - plugin side: loading a VST3 module, one plugin instance, its parameters, programs and state.
#pragma once
// Windows COM headers first: their IConnectionPoint must not meet Steinberg::Vst::IConnectionPoint after the using below
#include <windows.h>
#include <ole2.h>
#include <ocidl.h>
#include <shlobj.h>
#include <mmdeviceapi.h>
#include "public.sdk/source/vst/hosting/module.h"
#include "public.sdk/source/vst/hosting/hostclasses.h"
#include "public.sdk/source/vst/hosting/plugprovider.h"
#include "public.sdk/source/vst/hosting/processdata.h"
#include "public.sdk/source/vst/hosting/eventlist.h"
#include "public.sdk/source/vst/hosting/parameterchanges.h"
#include "pluginterfaces/vst/ivstaudioprocessor.h"
#include "pluginterfaces/vst/ivsteditcontroller.h"
#include "pluginterfaces/vst/ivstprocesscontext.h"
#include "pluginterfaces/vst/ivstunits.h"
#include "pluginterfaces/vst/ivstmidicontrollers.h"
#include "pluginterfaces/gui/iplugview.h"

#include <atomic>
#include <cstdint>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

using namespace Steinberg;
using namespace Steinberg::Vst;

std::string narrow(const std::wstring &w);
std::wstring widen(const std::string &s);
std::string str16(const char16 *s);
double now_s();
void hlog(const char *fmt, ...);               // to the log file / console / GUI log
void set_log_sink(std::function<void(const std::string &)> f);

// one MIDI-ish message with a time (seconds or samples, depending on where it is used)
struct MidiMsg {
    double t = 0;
    uint8_t st = 0, d1 = 0, d2 = 0;
};

// an automation curve for one parameter: (seconds, normalized) points, looped over `length`
struct AutoLane {
    ParamID id = 0;
    std::vector<std::pair<double, double>> pts;
    double length = 0;
    bool loop = true;
    double valueAt(double t) const;
};

class Instance;

// IComponentHandler + IPlugFrame for one instance
class HostHandler : public IComponentHandler, public IPlugFrame {
public:
    Instance *inst = nullptr;
    tresult PLUGIN_API queryInterface(const TUID iid, void **obj) override;
    uint32 PLUGIN_API addRef() override { return 1; }
    uint32 PLUGIN_API release() override { return 1; }
    tresult PLUGIN_API beginEdit(ParamID) override;
    tresult PLUGIN_API performEdit(ParamID id, ParamValue v) override;
    tresult PLUGIN_API endEdit(ParamID) override;
    tresult PLUGIN_API restartComponent(int32 flags) override;
    tresult PLUGIN_API resizeView(IPlugView *view, ViewRect *newSize) override;
};

struct ParamRec {
    ParameterInfo info;
    std::string name, units;
};

struct ProgramRec {
    std::string name;
    int listId = -1, index = 0;
};

class Instance {
public:
    ~Instance();
    // load class `classIndex` (-1: first audio-effect class) of the module at `path`
    static std::shared_ptr<Instance> create(const std::string &path, std::string &err);
    bool setup(double sr, int maxBlock, bool offline);   // setupProcessing + activate + start processing
    void shutdown();                                       // stop processing + deactivate

    // audio thread
    void process(int n, int64_t pos, double sr, bool playing);
    float *outL() { return data.outputs && data.numOutputs ? data.outputs[0].channelBuffers32[0] : silence.data(); }
    float *outR() { return data.outputs && data.numOutputs && data.outputs[0].numChannels > 1 ? data.outputs[0].channelBuffers32[1] : outL(); }

    // any thread: queued for the next process() call
    void queueEvent(const Event &e);
    void queueParam(ParamID id, double v, int32 offset = 0);
    void queueMidi(const MidiMsg &m, int32 offset = 0);   // notes as events, CCs/bend via IMidiMapping
    void allNotesOff();

    uint32 latency();
    std::vector<ParamRec> params(bool includeHidden = false);
    std::vector<ProgramRec> programs();
    bool selectProgram(int index);                         // via the program-change parameter
    int currentProgram();
    std::string paramString(ParamID id, double v);

    // state (UI thread; processing is held while it is applied)
    bool getState(std::vector<char> &comp, std::vector<char> &ctl);
    bool setState(const std::vector<char> &comp, const std::vector<char> &ctl);
    bool saveVstPreset(const std::string &file);
    bool loadVstPreset(const std::string &file);
    bool saveStateFile(const std::string &file);           // our own .bhstate
    bool loadStateFile(const std::string &file, std::string &err);

    // automation lanes, played in process()
    void setLane(const AutoLane &l);
    void removeLane(ParamID id);
    std::vector<AutoLane> lanes();
    std::map<ParamID, double> laneValues();                // last values sent by lanes (for the UI)

    std::string name, vendor, path, classIdStr;
    VST3::Hosting::Module::Ptr module;
    VST3::Hosting::ClassInfo info;
    IPtr<PlugProvider> provider;
    IPtr<IComponent> comp;
    IPtr<IEditController> ctl;
    IPtr<IAudioProcessor> proc;
    HostHandler handler;
    int number = 0;                                        // shown as "#n"
    std::atomic<bool> latencyChanged{false}, paramsChanged{false};
    std::function<void(ParamID, double)> onEdit;           // plugin's editor moved a parameter
    std::function<void(int32)> onRestart;
    std::function<void(int, int)> onResize;                // editor asks for a new size
    IPlugView *view = nullptr;                             // set by the GUI while an editor is open
    std::atomic<int> processing{0};
    std::atomic<uint64_t> procCalls{0}, procNsTotal{0}, procNsMax{0};   // time spent in process()
    std::mutex procLock;                                   // held by process(); taken by state changes
    bool active = false;
    double sr = 48000;
    int maxBlock = 512;
    bool offline = false;

private:
    HostProcessData data;
    EventList events;
    ParameterChanges inParams, outParams;
    ProcessContext ctx{};
    std::vector<float> silence;
    std::mutex qlock;
    std::vector<Event> qEvents;
    std::vector<std::pair<ParamID, std::pair<double, int32>>> qParams;
    std::vector<AutoLane> lanes_;
    std::map<ParamID, double> laneVals_;
    int64_t laneStart_ = -1;
    std::mutex laneLock;
};

// keep modules loaded once per path (instances share them)
VST3::Hosting::Module::Ptr load_module(const std::string &path, std::string &err);
void init_host_context();
void unload_modules();   // after every instance is gone

// child processes of this process (pid, exe) - for the orphan check
struct ProcInfo { uint32_t pid, ppid; std::string exe; };
std::vector<ProcInfo> list_processes();
std::vector<ProcInfo> descendants(uint32_t root);

// a window as a 24-bit BMP (PrintWindow with PW_RENDERFULLCONTENT, so OpenGL content is included)
bool save_bmp(HWND w, const std::string &path, bool client);

void write_wav(const std::string &path, const std::vector<float> &lr, int sr);     // 32-bit float stereo
bool read_wav(const std::string &path, std::vector<float> &lr, int &sr);
