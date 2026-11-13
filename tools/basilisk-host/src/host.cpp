// BasiliskHost - plugin side (see host.h)
#include "host.h"
#include "public.sdk/source/common/memorystream.h"
#include "public.sdk/source/vst/vstpresetfile.h"
#include "public.sdk/source/vst/utility/stringconvert.h"
#include "base/source/fstring.h"

#include <windows.h>
#include <tlhelp32.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <fstream>

namespace Steinberg {
DEF_CLASS_IID(IPlugFrame)
DEF_CLASS_IID(IPlugView)
}

// ------------------------------------------------------------------ small helpers
std::string narrow(const std::wstring &w)
{
    if (w.empty()) return {};
    int n = WideCharToMultiByte(CP_UTF8, 0, w.data(), (int)w.size(), NULL, 0, NULL, NULL);
    std::string s(n, 0);
    WideCharToMultiByte(CP_UTF8, 0, w.data(), (int)w.size(), &s[0], n, NULL, NULL);
    return s;
}
std::wstring widen(const std::string &s)
{
    if (s.empty()) return {};
    int n = MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), NULL, 0);
    std::wstring w(n, 0);
    MultiByteToWideChar(CP_UTF8, 0, s.data(), (int)s.size(), &w[0], n);
    return w;
}
std::string str16(const char16 *s) { return StringConvert::convert(s); }
double now_s() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }

static std::function<void(const std::string &)> g_sink;
static std::mutex g_logLock;
void set_log_sink(std::function<void(const std::string &)> f) { std::lock_guard<std::mutex> g(g_logLock); g_sink = std::move(f); }
void hlog(const char *fmt, ...)
{
    char b[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    std::lock_guard<std::mutex> g(g_logLock);
    if (g_sink) g_sink(b);
}

double AutoLane::valueAt(double t) const
{
    if (pts.empty()) return 0;
    if (loop && length > 0) t = std::fmod(t, length);
    if (t <= pts.front().first) return pts.front().second;
    if (t >= pts.back().first) return pts.back().second;
    auto it = std::upper_bound(pts.begin(), pts.end(), std::make_pair(t, -1e9));
    auto a = *(it - 1), b = *it;
    double u = b.first > a.first ? (t - a.first) / (b.first - a.first) : 0;
    return a.second + (b.second - a.second) * u;
}

// ------------------------------------------------------------------ host context
namespace {
class BHHostApp : public HostApplication {
public:
    tresult PLUGIN_API getName(String128 name) override
    {
        const char16 n[] = u"BasiliskHost";
        memcpy(name, n, sizeof n);
        return kResultOk;
    }
};
BHHostApp *g_app = nullptr;
std::mutex g_modLock;
std::map<std::string, VST3::Hosting::Module::Ptr> g_modules;
}

void init_host_context()
{
    if (g_app) return;
    g_app = new BHHostApp();
    PluginContextFactory::instance().setPluginContext(g_app);
}

void unload_modules()
{
    std::lock_guard<std::mutex> g(g_modLock);
    g_modules.clear();
}

VST3::Hosting::Module::Ptr load_module(const std::string &path, std::string &err)
{
    std::lock_guard<std::mutex> g(g_modLock);
    auto it = g_modules.find(path);
    if (it != g_modules.end()) return it->second;
    // never a modal "can't load DLL" box: the error goes to the log instead
    UINT old = SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOOPENFILEERRORBOX | SEM_NOGPFAULTERRORBOX);
    auto m = VST3::Hosting::Module::create(path, err);
    SetErrorMode(old | SEM_FAILCRITICALERRORS | SEM_NOOPENFILEERRORBOX);
    if (!m) {
        DWORD le = GetLastError();
        if (err.empty()) err = "module load failed";
        err += " (GetLastError " + std::to_string(le) + ")";
        return nullptr;
    }
    g_modules[path] = m;
    return m;
}

// ------------------------------------------------------------------ handler
tresult PLUGIN_API HostHandler::queryInterface(const TUID iid, void **obj)
{
    if (FUnknownPrivate::iidEqual(iid, IComponentHandler::iid) || FUnknownPrivate::iidEqual(iid, FUnknown::iid)) {
        *obj = static_cast<IComponentHandler *>(this);
        return kResultOk;
    }
    if (FUnknownPrivate::iidEqual(iid, IPlugFrame::iid)) {
        *obj = static_cast<IPlugFrame *>(this);
        return kResultOk;
    }
    *obj = nullptr;
    return kNoInterface;
}
tresult PLUGIN_API HostHandler::beginEdit(ParamID) { return kResultOk; }
tresult PLUGIN_API HostHandler::endEdit(ParamID) { return kResultOk; }
tresult PLUGIN_API HostHandler::performEdit(ParamID id, ParamValue v)
{
    if (!inst) return kResultFalse;
    inst->queueParam(id, v);   // the controller has it already; the processor gets it with the next block
    if (inst->onEdit) inst->onEdit(id, v);
    return kResultOk;
}
tresult PLUGIN_API HostHandler::restartComponent(int32 flags)
{
    if (!inst) return kResultFalse;
    if (flags & kLatencyChanged) inst->latencyChanged = true;
    if (flags & (kParamValuesChanged | kParamTitlesChanged)) inst->paramsChanged = true;
    if (inst->onRestart) inst->onRestart(flags);
    return kResultOk;
}
tresult PLUGIN_API HostHandler::resizeView(IPlugView *view, ViewRect *r)
{
    if (!inst || !r) return kInvalidArgument;
    if (inst->onResize) inst->onResize(r->getWidth(), r->getHeight());
    if (view) view->onSize(r);
    return kResultOk;
}

// ------------------------------------------------------------------ instance
static int g_instanceCounter = 0;

std::shared_ptr<Instance> Instance::create(const std::string &path, std::string &err)
{
    init_host_context();
    auto mod = load_module(path, err);
    if (!mod) return nullptr;
    auto factory = mod->getFactory();
    auto I = std::make_shared<Instance>();
    bool found = false;
    for (auto &ci : factory.classInfos())
        if (ci.category() == kVstAudioEffectClass) { I->info = ci; found = true; break; }
    if (!found) { err = "no audio processor class in " + path; return nullptr; }
    I->module = mod;
    I->path = path;
    I->name = I->info.name();
    I->vendor = I->info.vendor();
    I->classIdStr = I->info.ID().toString();
    I->handler.inst = I.get();
    I->provider = owned(new PlugProvider(factory, I->info, true));
    if (!I->provider->initialize()) { err = "the plugin failed to initialize"; I->provider = nullptr; return nullptr; }
    I->comp = I->provider->getComponentPtr();
    I->ctl = I->provider->getControllerPtr();
    I->proc = U::cast<IAudioProcessor>(I->comp);
    if (!I->proc) { err = "no IAudioProcessor"; I->provider = nullptr; return nullptr; }
    if (I->ctl) {
        I->ctl->setComponentHandler(&I->handler);
        // as a DAW does after creation: hand the component's state to the controller
        MemoryStream ms;
        if (I->comp->getState(&ms) == kResultOk) {
            ms.seek(0, IBStream::kIBSeekSet, nullptr);
            I->ctl->setComponentState(&ms);
        }
    }
    // main buses on; instrument: event in, audio out
    int nOut = I->comp->getBusCount(kAudio, kOutput), nEvIn = I->comp->getBusCount(kEvent, kInput);
    if (nOut > 0) I->comp->activateBus(kAudio, kOutput, 0, true);
    if (I->comp->getBusCount(kAudio, kInput) > 0) I->comp->activateBus(kAudio, kInput, 0, true);
    if (nEvIn > 0) I->comp->activateBus(kEvent, kInput, 0, true);
    I->number = ++g_instanceCounter;
    int np = I->ctl ? I->ctl->getParameterCount() : 0;
    I->inParams.setMaxParameters(np + 64);
    I->outParams.setMaxParameters(np + 64);
    I->events.setMaxSize(1024);
    return I;
}

Instance::~Instance()
{
    shutdown();
    if (ctl) ctl->setComponentHandler(nullptr);
    proc = nullptr;
    ctl = nullptr;
    comp = nullptr;
    provider = nullptr;   // terminates and releases both parts
}

bool Instance::setup(double rate, int block, bool off)
{
    shutdown();
    std::lock_guard<std::mutex> g(procLock);
    sr = rate;
    maxBlock = block;
    offline = off;
    ProcessSetup ps{off ? kOffline : kRealtime, kSample32, block, rate};
    if (proc->setupProcessing(ps) != kResultOk) hlog("%s: setupProcessing returned an error", name.c_str());
    if (comp->setActive(true) != kResultOk) { hlog("%s: setActive failed", name.c_str()); return false; }
    data.unprepare();
    data.prepare(*comp, block, kSample32);
    data.inputEvents = &events;
    data.inputParameterChanges = &inParams;
    data.outputParameterChanges = &outParams;
    silence.assign(block, 0.f);
    ctx = {};
    ctx.sampleRate = rate;
    ctx.tempo = 120;
    ctx.timeSigNumerator = 4;
    ctx.timeSigDenominator = 4;
    proc->setProcessing(true);
    active = true;
    return true;
}

void Instance::shutdown()
{
    std::lock_guard<std::mutex> g(procLock);
    if (!active) return;
    proc->setProcessing(false);
    comp->setActive(false);
    active = false;
}

void Instance::queueEvent(const Event &e)
{
    std::lock_guard<std::mutex> g(qlock);
    qEvents.push_back(e);
}
void Instance::queueParam(ParamID id, double v, int32 offset)
{
    std::lock_guard<std::mutex> g(qlock);
    qParams.push_back({id, {v, offset}});
}

void Instance::queueMidi(const MidiMsg &m, int32 offset)
{
    int type = m.st & 0xF0, ch = m.st & 0x0F;
    Event ev = {};
    ev.busIndex = 0;
    ev.sampleOffset = offset;
    if (type == 0x90 && m.d2 > 0) {
        ev.type = Event::kNoteOnEvent;
        ev.noteOn.channel = (int16)ch;
        ev.noteOn.pitch = m.d1;
        ev.noteOn.velocity = m.d2 / 127.f;
        ev.noteOn.noteId = -1;
        queueEvent(ev);
    } else if (type == 0x80 || (type == 0x90 && m.d2 == 0)) {
        ev.type = Event::kNoteOffEvent;
        ev.noteOff.channel = (int16)ch;
        ev.noteOff.pitch = m.d1;
        ev.noteOff.velocity = m.d2 / 127.f;
        ev.noteOff.noteId = -1;
        queueEvent(ev);
    } else if (type == 0xB0 || type == 0xE0 || type == 0xD0) {
        // CCs, pitch bend and aftertouch reach a VST3 plugin as parameters it maps itself
        CtrlNumber cc = type == 0xB0 ? (CtrlNumber)m.d1 : type == 0xE0 ? (CtrlNumber)kPitchBend : (CtrlNumber)kAfterTouch;
        double v = type == 0xB0 ? m.d2 / 127.0 : type == 0xE0 ? ((m.d2 << 7) | m.d1) / 16383.0 : m.d1 / 127.0;
        FUnknownPtr<IMidiMapping> mm(ctl);
        ParamID id;
        if (mm && mm->getMidiControllerAssignment(0, (int16)ch, cc, id) == kResultTrue) {
            queueParam(id, v, offset);
            if (ctl) ctl->setParamNormalized(id, v);
        } else if (type == 0xB0 && (m.d1 == 123 || m.d1 == 120)) {
            allNotesOff();
        }
    }
}

void Instance::allNotesOff()
{
    for (int n = 0; n < 128; n++) {
        Event ev = {};
        ev.type = Event::kNoteOffEvent;
        ev.noteOff.pitch = (int16)n;
        ev.noteOff.noteId = -1;
        queueEvent(ev);
    }
}

void Instance::process(int n, int64_t pos, double rate, bool playing)
{
    std::unique_lock<std::mutex> g(procLock, std::try_to_lock);
    if (!g.owns_lock() || !active) {   // a state change is being applied: this block is silent
        if ((int)silence.size() < n) silence.assign(n, 0.f);
        if (data.outputs && data.numOutputs)
            for (int c = 0; c < data.outputs[0].numChannels; c++) memset(data.outputs[0].channelBuffers32[c], 0, sizeof(float) * std::min(n, maxBlock));
        return;
    }
    events.clear();
    inParams.clearQueue();
    outParams.clearQueue();
    {
        std::lock_guard<std::mutex> q(qlock);
        std::stable_sort(qEvents.begin(), qEvents.end(), [](const Event &a, const Event &b) { return a.sampleOffset < b.sampleOffset; });
        for (auto &e : qEvents) { e.sampleOffset = std::min(std::max(e.sampleOffset, 0), n - 1); events.addEvent(e); }
        qEvents.clear();
        for (auto &p : qParams) {
            int32 idx;
            IParamValueQueue *q2 = inParams.addParameterData(p.first, idx);
            if (q2) q2->addPoint(std::min(std::max(p.second.second, 0), n - 1), p.second.first, idx);
        }
        qParams.clear();
    }
    {
        std::lock_guard<std::mutex> l(laneLock);
        if (!lanes_.empty()) {
            if (laneStart_ < 0) laneStart_ = pos;
            for (auto &L : lanes_) {
                double t = (pos - laneStart_) / rate;
                if (!L.loop && t > L.length + 0.5) continue;
                double v = L.valueAt(t);
                int32 idx;
                IParamValueQueue *q2 = inParams.addParameterData(L.id, idx);
                if (q2) q2->addPoint(0, v, idx);
                laneVals_[L.id] = v;
            }
        } else laneStart_ = -1;
    }
    ctx.sampleRate = rate;
    ctx.projectTimeSamples = pos;
    ctx.continousTimeSamples = pos;
    ctx.projectTimeMusic = pos / rate * 2.0;   // 120 bpm
    ctx.systemTime = (int64)(now_s() * 1e9);
    ctx.state = ProcessContext::kTempoValid | ProcessContext::kTimeSigValid | ProcessContext::kContTimeValid |
                ProcessContext::kProjectTimeMusicValid | ProcessContext::kSystemTimeValid | (playing ? ProcessContext::kPlaying : 0);
    data.processContext = &ctx;
    data.numSamples = n;
    data.processMode = offline ? kOffline : kRealtime;
    processing++;
    double t0 = now_s();
    proc->process(data);
    uint64_t ns = (uint64_t)((now_s() - t0) * 1e9);
    processing--;
    procCalls++;
    procNsTotal += ns;
    if (ns > procNsMax) procNsMax = ns;
}

uint32 Instance::latency() { return proc ? proc->getLatencySamples() : 0; }

std::vector<ParamRec> Instance::params(bool includeHidden)
{
    std::vector<ParamRec> v;
    if (!ctl) return v;
    int n = ctl->getParameterCount();
    for (int i = 0; i < n; i++) {
        ParamRec r;
        if (ctl->getParameterInfo(i, r.info) != kResultOk) continue;
        if (!includeHidden && (r.info.flags & ParameterInfo::kIsHidden)) continue;
        r.name = str16(r.info.title);
        r.units = str16(r.info.units);
        v.push_back(r);
    }
    return v;
}

std::string Instance::paramString(ParamID id, double v)
{
    String128 s = {};
    if (ctl && ctl->getParamStringByValue(id, v, s) == kResultOk) return str16(s);
    char b[32];
    snprintf(b, sizeof b, "%.3f", v);
    return b;
}

static bool program_param(IEditController *ctl, ParameterInfo &out)
{
    if (!ctl) return false;
    int n = ctl->getParameterCount();
    for (int i = 0; i < n; i++) {
        ParameterInfo pi;
        if (ctl->getParameterInfo(i, pi) == kResultOk && (pi.flags & ParameterInfo::kIsProgramChange)) { out = pi; return true; }
    }
    return false;
}

std::vector<ProgramRec> Instance::programs()
{
    std::vector<ProgramRec> v;
    FUnknownPtr<IUnitInfo> ui(ctl);
    if (ui && ui->getProgramListCount() > 0) {
        ProgramListInfo li;
        if (ui->getProgramListInfo(0, li) == kResultOk)
            for (int i = 0; i < li.programCount; i++) {
                String128 s = {};
                ui->getProgramName(li.id, i, s);
                v.push_back({str16(s), li.id, i});
            }
        if (!v.empty()) return v;
    }
    ParameterInfo pi;
    if (program_param(ctl, pi) && pi.stepCount > 0)
        for (int i = 0; i <= pi.stepCount; i++) {
            String128 s = {};
            ctl->getParamStringByValue(pi.id, (double)i / pi.stepCount, s);
            v.push_back({str16(s), -1, i});
        }
    return v;
}

bool Instance::selectProgram(int index)
{
    ParameterInfo pi;
    if (!program_param(ctl, pi) || pi.stepCount <= 0) return false;
    double v = (double)index / pi.stepCount;
    ctl->setParamNormalized(pi.id, v);
    queueParam(pi.id, v);
    return true;
}

int Instance::currentProgram()
{
    ParameterInfo pi;
    if (!program_param(ctl, pi) || pi.stepCount <= 0) return -1;
    return (int)std::lround(ctl->getParamNormalized(pi.id) * pi.stepCount);
}

bool Instance::getState(std::vector<char> &c, std::vector<char> &e)
{
    MemoryStream a, b;
    if (comp->getState(&a) != kResultOk) return false;
    c.assign(a.getData(), a.getData() + a.getSize());
    e.clear();
    if (ctl && ctl->getState(&b) == kResultOk) e.assign(b.getData(), b.getData() + b.getSize());
    return true;
}

bool Instance::setState(const std::vector<char> &c, const std::vector<char> &e)
{
    std::lock_guard<std::mutex> g(procLock);
    MemoryStream a;
    int32 w = 0;
    a.write((void *)c.data(), (int32)c.size(), &w);
    a.seek(0, IBStream::kIBSeekSet, nullptr);
    tresult r = comp->setState(&a);
    if (ctl) {
        a.seek(0, IBStream::kIBSeekSet, nullptr);
        ctl->setComponentState(&a);
        if (!e.empty()) {
            MemoryStream b;
            b.write((void *)e.data(), (int32)e.size(), &w);
            b.seek(0, IBStream::kIBSeekSet, nullptr);
            ctl->setState(&b);
        }
    }
    paramsChanged = true;
    return r == kResultOk;
}

bool Instance::saveVstPreset(const std::string &file)
{
    IBStream *s = FileStream::open(file.c_str(), "wb");
    if (!s) return false;
    bool ok = PresetFile::savePreset(s, FUID::fromTUID(info.ID().data()), comp, ctl);
    s->release();
    return ok;
}

bool Instance::loadVstPreset(const std::string &file)
{
    IBStream *s = FileStream::open(file.c_str(), "rb");
    if (!s) return false;
    bool ok;
    {
        std::lock_guard<std::mutex> g(procLock);
        ok = PresetFile::loadPreset(s, FUID::fromTUID(info.ID().data()), comp, ctl);
    }
    s->release();
    paramsChanged = true;
    return ok;
}

// .bhstate: "BHSTATE1\n" class-id "\n" name "\n" then u32 len + component state, u32 len + controller state
bool Instance::saveStateFile(const std::string &file)
{
    std::vector<char> c, e;
    if (!getState(c, e)) return false;
    std::ofstream f(file, std::ios::binary);
    if (!f) return false;
    f << "BHSTATE1\n" << classIdStr << "\n" << name << "\n";
    uint32_t n = (uint32_t)c.size();
    f.write((char *)&n, 4);
    f.write(c.data(), n);
    n = (uint32_t)e.size();
    f.write((char *)&n, 4);
    f.write(e.data(), n);
    return (bool)f;
}

bool Instance::loadStateFile(const std::string &file, std::string &err)
{
    std::ifstream f(file, std::ios::binary);
    if (!f) { err = "cannot open " + file; return false; }
    std::string magic, cid, nm;
    std::getline(f, magic);
    std::getline(f, cid);
    std::getline(f, nm);
    if (magic != "BHSTATE1") { err = "not a BasiliskHost state file"; return false; }
    if (cid != classIdStr) { err = "state is for " + nm + " (" + cid + "), not " + name; return false; }
    uint32_t n = 0;
    std::vector<char> c, e;
    f.read((char *)&n, 4);
    c.resize(n);
    f.read(c.data(), n);
    n = 0;
    if (f.read((char *)&n, 4)) { e.resize(n); f.read(e.data(), n); }
    if (!f && !f.eof()) { err = "truncated state file"; return false; }
    return setState(c, e);
}

void Instance::setLane(const AutoLane &l)
{
    std::lock_guard<std::mutex> g(laneLock);
    for (auto &x : lanes_) if (x.id == l.id) { x = l; return; }
    lanes_.push_back(l);
}
void Instance::removeLane(ParamID id)
{
    std::lock_guard<std::mutex> g(laneLock);
    lanes_.erase(std::remove_if(lanes_.begin(), lanes_.end(), [&](const AutoLane &x) { return x.id == id; }), lanes_.end());
    laneVals_.erase(id);
}
std::vector<AutoLane> Instance::lanes() { std::lock_guard<std::mutex> g(laneLock); return lanes_; }
std::map<ParamID, double> Instance::laneValues() { std::lock_guard<std::mutex> g(laneLock); return laneVals_; }

// ------------------------------------------------------------------ processes
std::vector<ProcInfo> list_processes()
{
    std::vector<ProcInfo> v;
    HANDLE s = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (s == INVALID_HANDLE_VALUE) return v;
    PROCESSENTRY32W pe = {sizeof pe};
    if (Process32FirstW(s, &pe))
        do v.push_back({pe.th32ProcessID, pe.th32ParentProcessID, narrow(pe.szExeFile)});
        while (Process32NextW(s, &pe));
    CloseHandle(s);
    return v;
}

std::vector<ProcInfo> descendants(uint32_t root)
{
    auto all = list_processes();
    std::vector<ProcInfo> out;
    std::vector<uint32_t> frontier{root};
    while (!frontier.empty()) {
        uint32_t p = frontier.back();
        frontier.pop_back();
        for (auto &x : all)
            if (x.ppid == p && x.pid != p && x.pid != root) {
                bool seen = false;
                for (auto &o : out) if (o.pid == x.pid) seen = true;
                if (!seen) { out.push_back(x); frontier.push_back(x.pid); }
            }
    }
    return out;
}

// ------------------------------------------------------------------ screenshots
bool save_bmp(HWND w, const std::string &path, bool client)
{
    RECT r;
    if (client) GetClientRect(w, &r);
    else GetWindowRect(w, &r);
    int W = r.right - r.left, H = r.bottom - r.top;
    if (W <= 0 || H <= 0) return false;
    HDC wdc = GetDC(NULL), md = CreateCompatibleDC(wdc);
    HBITMAP bm = CreateCompatibleBitmap(wdc, W, H);
    HGDIOBJ ob = SelectObject(md, bm);
    // PW_RENDERFULLCONTENT (2) also captures OpenGL/DirectX content
    BOOL ok = PrintWindow(w, md, client ? (PW_CLIENTONLY | 2) : 2);
    if (!ok) {
        POINT o = {0, 0};
        if (client) ClientToScreen(w, &o);
        else { o.x = r.left; o.y = r.top; }
        BitBlt(md, 0, 0, W, H, wdc, o.x, o.y, SRCCOPY);
    }
    BITMAPINFOHEADER bi = {sizeof bi, W, -H, 1, 24, BI_RGB};
    int stride = (W * 3 + 3) & ~3;
    std::vector<char> px((size_t)stride * H);
    GetDIBits(md, bm, 0, H, px.data(), (BITMAPINFO *)&bi, DIB_RGB_COLORS);
    std::ofstream f(path, std::ios::binary);
    BITMAPFILEHEADER fh = {0x4D42, (DWORD)(sizeof fh + sizeof bi + px.size()), 0, 0, (DWORD)(sizeof fh + sizeof bi)};
    f.write((char *)&fh, sizeof fh);
    f.write((char *)&bi, sizeof bi);
    f.write(px.data(), px.size());
    SelectObject(md, ob);
    DeleteObject(bm);
    DeleteDC(md);
    ReleaseDC(NULL, wdc);
    return true;
}

// ------------------------------------------------------------------ wav
void write_wav(const std::string &path, const std::vector<float> &lr, int sr)
{
    std::ofstream f(path, std::ios::binary);
    uint32_t n = (uint32_t)lr.size() * 4;
    auto u32 = [&](uint32_t v) { f.write((const char *)&v, 4); };
    auto u16 = [&](uint16_t v) { f.write((const char *)&v, 2); };
    f.write("RIFF", 4); u32(36 + n); f.write("WAVEfmt ", 8); u32(16); u16(3); u16(2); u32(sr); u32(sr * 8); u16(8); u16(32);
    f.write("data", 4); u32(n);
    f.write((const char *)lr.data(), n);
}

bool read_wav(const std::string &path, std::vector<float> &lr, int &sr)
{
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    char id[4];
    uint32_t sz;
    f.read(id, 4); f.read((char *)&sz, 4); f.read(id, 4);
    uint16_t fmt = 0, ch = 0, bits = 0;
    while (f.read(id, 4) && f.read((char *)&sz, 4)) {
        if (!memcmp(id, "fmt ", 4)) {
            std::vector<char> b(sz);
            f.read(b.data(), sz);
            memcpy(&fmt, &b[0], 2); memcpy(&ch, &b[2], 2); memcpy(&sr, &b[4], 4); memcpy(&bits, &b[14], 2);
        } else if (!memcmp(id, "data", 4)) {
            std::vector<char> b(sz);
            f.read(b.data(), sz);
            size_t frames = sz / (ch * bits / 8);
            lr.resize(frames * 2);
            for (size_t i = 0; i < frames; i++)
                for (int c = 0; c < 2; c++) {
                    int cc = std::min<int>(c, ch - 1);
                    const char *p = &b[(i * ch + cc) * (bits / 8)];
                    float v = 0;
                    if (fmt == 3 && bits == 32) memcpy(&v, p, 4);
                    else if (bits == 16) { int16_t s; memcpy(&s, p, 2); v = s / 32768.f; }
                    lr[i * 2 + c] = v;
                }
            return true;
        } else f.seekg(sz, std::ios::cur);
    }
    return false;
}
