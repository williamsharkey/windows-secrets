// BasiliskHost - the command-line test harness: renders, comparisons and a JSON report (no GUI)
#include "analysis.h"
#include "host.h"
#include "json.h"
#include "midi.h"
#include <windows.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <set>
#include <thread>

#define BH_VERSION "1.0.0"

namespace {

struct Opts {
    std::string plugin, outDir, report, midiFile, pattern = "all", score;
    double sr = 48000, warmup = 8, tail = 2, timeout = -1;
    int block = 512, repeat = 2, instances = 2, program = -1, stateProgram = -1;
    std::string loadState;
    std::vector<int> multiPrograms;
    double changeAt = -1;
    int changeProgram = -1;
    std::vector<std::string> editorScript;
    std::string stateContains;
    std::set<std::string> tests;
    std::vector<std::string> automate;
    bool killOrphans = false, keepWavs = true;
};

struct RenderSpec {
    bool offline = true;
    int instances = 1;
    std::vector<int> programs;            // per instance (-1: leave)
    std::vector<char> stateC, stateE;     // applied before activation when not empty
    std::string vstpreset;                // loaded before activation when set
    std::vector<AutoLane> lanes;
    std::string saveStateTo, savePresetTo;
    double changeAt = -1;                 // score seconds: switch every instance to changeProgram here
    int changeProgram = -1;
    std::vector<std::string> editorScript; // open instance 0's editor and run these steps (see README)
};

struct RenderOut {
    bool ok = false;
    std::string err;
    std::vector<std::vector<float>> out;
    uint32_t latency = 0;
    double loadS = 0, renderS = 0, unloadS = 0, maxLateMs = 0;
    bool timedOut = false;
    std::vector<char> savedC, savedE;
    std::vector<ProcInfo> children;       // child processes seen while loaded
    std::vector<ProcInfo> leftover;       // still there after unload (+ a grace period)
    int programCount = 0;
    std::vector<std::string> programNames;
    J editor = J::obj();
};

Opts O;
int g_timeouts = 0;
Score S;
FILE *g_logf = nullptr;

void say(const char *fmt, ...)
{
    char b[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(b, sizeof b, fmt, ap);
    va_end(ap);
    fputs(b, stdout);
    fputs("\n", stdout);
    fflush(stdout);
    if (g_logf) { fputs(b, g_logf); fputs("\n", g_logf); fflush(g_logf); }
}

std::string join(const std::string &dir, const std::string &f) { return dir.empty() ? f : dir + "\\" + f; }

void merge_children(std::vector<ProcInfo> &into, const std::vector<ProcInfo> &v)
{
    for (auto &p : v) {
        bool seen = false;
        for (auto &q : into) if (q.pid == p.pid) seen = true;
        if (!seen) into.push_back(p);
    }
}


// ------------------------------------------------------------------ the editor, driven by a script
LRESULT CALLBACK test_editor_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_CLOSE) return 0;   // only the harness closes it
    return DefWindowProcW(h, m, wp, lp);
}

struct EditorRun {
    HWND win = NULL;
    IPtr<IPlugView> view;
    Instance *I = nullptr;
    std::vector<std::string> steps;
    size_t next = 0;
    double due = 0;
    J log = J::arr(), shots = J::arr();
    double t0 = 0;
    // messages are posted with real timing: an emulated machine samples its mouse and keys once a frame, so a
    // press and release in the same instant would be lost
    struct Post { double at; HWND h; UINT m; WPARAM wp; LPARAM lp; };
    std::vector<Post> q;
    double qEnd = 0;   // when the last queued message goes out
    static constexpr double HOLD = 0.05, GAP = 0.04;
    void post(double after, HWND h, UINT m, WPARAM wp, LPARAM lp)
    {
        double at = std::max(now_s(), qEnd) + after;
        q.push_back({at, h, m, wp, lp});
        qEnd = at;
    }

    bool open(Instance *inst)
    {
        I = inst;
        if (!I->ctl) return false;
        view = owned(I->ctl->createView(ViewType::kEditor));
        if (!view) return false;
        static bool reg = false;
        if (!reg) {
            WNDCLASSW wc = {};
            wc.lpfnWndProc = test_editor_proc;
            wc.hInstance = GetModuleHandleW(NULL);
            wc.lpszClassName = L"BHTestEditor";
            wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
            wc.hCursor = LoadCursor(NULL, IDC_ARROW);
            RegisterClassW(&wc);
            reg = true;
        }
        ViewRect vr;
        view->getSize(&vr);
        RECT r = {0, 0, vr.getWidth(), vr.getHeight()};
        AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
        win = CreateWindowW(L"BHTestEditor", widen("BasiliskHost test - " + I->name).c_str(), WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN, 40, 40,
                            r.right - r.left, r.bottom - r.top, NULL, NULL, GetModuleHandleW(NULL), NULL);
        I->onResize = [this](int w, int h) {
            RECT rr = {0, 0, w, h};
            AdjustWindowRect(&rr, WS_OVERLAPPEDWINDOW, FALSE);
            SetWindowPos(win, NULL, 0, 0, rr.right - rr.left, rr.bottom - rr.top, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
        };
        view->setFrame(&I->handler);
        ShowWindow(win, SW_SHOWNOACTIVATE);
        if (view->attached(win, kPlatformTypeHWND) != kResultOk) { DestroyWindow(win); win = NULL; view = nullptr; return false; }
        t0 = due = now_s();
        return true;
    }

    void close()
    {
        if (view) { view->removed(); view->setFrame(nullptr); view = nullptr; }
        if (win) { DestroyWindow(win); win = NULL; }
        if (I) I->onResize = nullptr;
    }

    // the plugin's own window under a point of the editor's client area, and the point in its coordinates
    HWND target(POINT &p)
    {
        HWND h = win;
        for (;;) {
            HWND c = ChildWindowFromPointEx(h, p, CWP_SKIPINVISIBLE | CWP_SKIPTRANSPARENT);
            if (!c || c == h) return h;
            MapWindowPoints(h, c, &p, 1);
            h = c;
        }
    }
    HWND focus_target()
    {
        HWND h = win, c;
        while ((c = GetWindow(h, GW_CHILD)) != NULL) h = c;
        return h;
    }

    void mouse(const char *what, int x, int y)
    {
        POINT p = {x, y};
        HWND h = target(p);
        LPARAM lp = MAKELPARAM(p.x, p.y);
        std::string w = what;
        post(0, h, WM_MOUSEMOVE, 0, lp);
        if (w == "move") return;
        UINT dn = w == "rclick" ? WM_RBUTTONDOWN : WM_LBUTTONDOWN, up = w == "rclick" ? WM_RBUTTONUP : WM_LBUTTONUP;
        WPARAM mk = w == "rclick" ? MK_RBUTTON : MK_LBUTTON;
        post(GAP, h, dn, mk, lp);
        post(HOLD, h, up, 0, lp);
        if (w == "dblclick") { post(GAP, h, WM_LBUTTONDBLCLK, MK_LBUTTON, lp); post(HOLD, h, WM_LBUTTONUP, 0, lp); }
        qEnd += GAP;
    }

    void key(UINT vk, wchar_t ch, bool ctrl, bool shift, bool alt)
    {
        HWND h = focus_target();
        SetFocus(h);
        // lParam as a keyboard sends it: repeat count, scan code (pugl tells left/right Shift by it), extended bit
        auto klp = [](UINT v, bool up) -> LPARAM {
            UINT sc = MapVirtualKeyW(v, MAPVK_VK_TO_VSC);
            bool ext = v == VK_LEFT || v == VK_RIGHT || v == VK_UP || v == VK_DOWN || v == VK_HOME || v == VK_END ||
                       v == VK_PRIOR || v == VK_NEXT || v == VK_INSERT || v == VK_DELETE;
            return (LPARAM)(1 | (sc << 16) | (ext ? 1u << 24 : 0) | (up ? 0xC0000000u : 0));
        };
        // a modifier is both a message and this thread's key state (the plugin window is ours; it may ask GetKeyState)
        auto mod = [&](UINT v, bool down) {
            post(down ? 0 : 0.01, NULL, 0, v, down);
            post(0, h, down ? WM_KEYDOWN : WM_KEYUP, v, klp(v, !down));
        };
        if (ctrl) mod(VK_CONTROL, true);
        if (shift) mod(VK_SHIFT, true);
        if (alt) mod(VK_MENU, true);
        post(0.01, h, WM_KEYDOWN, vk, klp(vk, false));
        if (ch && !ctrl && !alt) post(0, h, WM_CHAR, ch, klp(vk, false));
        post(HOLD, h, WM_KEYUP, vk, klp(vk, true));
        if (alt) mod(VK_MENU, false);
        if (shift) mod(VK_SHIFT, false);
        if (ctrl) mod(VK_CONTROL, false);
        qEnd += GAP;
    }

    void step(const std::string &line)
    {
        std::string cmd, rest;
        size_t sp = line.find(' ');
        cmd = line.substr(0, sp);
        rest = sp == std::string::npos ? "" : line.substr(sp + 1);
        J e = J::obj();
        e["t"] = r3(now_s() - t0);
        e["step"] = line;
        int x = 0, y = 0, x2 = 0, y2 = 0;
        if (cmd == "wait") due = std::max(now_s(), qEnd) + atof(rest.c_str());
        else if (cmd == "shot") {
            std::string f = join(O.outDir, (rest.empty() ? "editor" : rest) + ".bmp");
            bool ok = save_bmp(win, f, true);
            e["file"] = f;
            e["ok"] = ok;
            shots.push(f);
        } else if (cmd == "click" || cmd == "dblclick" || cmd == "rclick" || cmd == "move") {
            if (sscanf(rest.c_str(), "%d %d", &x, &y) == 2) mouse(cmd.c_str(), x, y);
        } else if (cmd == "drag") {
            if (sscanf(rest.c_str(), "%d %d %d %d", &x, &y, &x2, &y2) == 4) {
                POINT p = {x, y};
                HWND h = target(p);
                post(0, h, WM_MOUSEMOVE, 0, MAKELPARAM(p.x, p.y));
                post(GAP, h, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(p.x, p.y));
                for (int k = 1; k <= 8; k++) {
                    POINT pt = {x + (x2 - x) * k / 8, y + (y2 - y) * k / 8};
                    MapWindowPoints(win, h, &pt, 1);
                    post(0.03, h, WM_MOUSEMOVE, MK_LBUTTON, MAKELPARAM(pt.x, pt.y));
                }
                POINT pt = {x2, y2};
                MapWindowPoints(win, h, &pt, 1);
                post(HOLD, h, WM_LBUTTONUP, 0, MAKELPARAM(pt.x, pt.y));
                qEnd += GAP;
            }
        } else if (cmd == "type") {
            for (wchar_t c : widen(rest)) {
                SHORT v = VkKeyScanW(c);
                key(v == -1 ? 0 : (v & 0xFF), c, false, v != -1 && (v & 0x100), false);
            }
        } else if (cmd == "key") {
            std::string k = rest;
            bool ctrl = false, shift = false, alt = false;
            for (;;) {
                if (k.rfind("ctrl+", 0) == 0) { ctrl = true; k = k.substr(5); }
                else if (k.rfind("shift+", 0) == 0) { shift = true; k = k.substr(6); }
                else if (k.rfind("alt+", 0) == 0) { alt = true; k = k.substr(4); }
                else break;
            }
            static const struct { const char *n; UINT vk; wchar_t ch; } names[] = {
                {"enter", VK_RETURN, L'\r'}, {"esc", VK_ESCAPE, 27}, {"tab", VK_TAB, L'\t'}, {"backspace", VK_BACK, 8}, {"delete", VK_DELETE, 0},
                {"left", VK_LEFT, 0}, {"right", VK_RIGHT, 0}, {"up", VK_UP, 0}, {"down", VK_DOWN, 0}, {"home", VK_HOME, 0}, {"end", VK_END, 0},
                {"space", VK_SPACE, L' '}, {"f1", VK_F1, 0}, {"f2", VK_F2, 0}, {"f10", VK_F10, 0}};
            bool done = false;
            for (auto &n : names) if (k == n.n) { key(n.vk, n.ch, ctrl, shift, alt); done = true; }
            if (!done && k.size() == 1) {
                SHORT v = VkKeyScanA(k[0]);
                key(v & 0xFF, (wchar_t)k[0], ctrl, shift || (v & 0x100), alt);
            }
        } else if (cmd == "program") {
            e["ok"] = I->selectProgram(atoi(rest.c_str()));
        } else if (cmd == "resize") {
            if (sscanf(rest.c_str(), "%d %d", &x, &y) == 2) {
                RECT rr = {0, 0, x, y};
                AdjustWindowRect(&rr, WS_OVERLAPPEDWINDOW, FALSE);
                SetWindowPos(win, NULL, 0, 0, rr.right - rr.left, rr.bottom - rr.top, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
                if (view->canResize() == kResultTrue) { ViewRect v(0, 0, x, y); view->checkSizeConstraint(&v); view->onSize(&v); }
            }
        } else if (cmd == "state") {
            std::vector<char> c, ed;
            I->getState(c, ed);
            e["component_state_bytes"] = (unsigned)c.size();
            std::string txt;
            for (char ch : c) txt += (ch >= 32 && ch < 127) ? ch : '.';
            e["state_text"] = txt.substr(0, 400);
        } else e["error"] = "unknown step";
        log.push(e);
    }

    void tick()
    {
        MSG m;
        while (PeekMessageW(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessageW(&m); }
        double t = now_s();
        size_t k = 0;
        for (; k < q.size() && q[k].at <= t; k++) {
            if (q[k].m == 0) {   // set a modifier's key state
                BYTE ks[256];
                GetKeyboardState(ks);
                BYTE v = q[k].lp ? 0x80 : 0;
                ks[q[k].wp] = v;
                if (q[k].wp == VK_SHIFT) ks[VK_LSHIFT] = v;
                if (q[k].wp == VK_CONTROL) ks[VK_LCONTROL] = v;
                if (q[k].wp == VK_MENU) ks[VK_LMENU] = v;
                SetKeyboardState(ks);
            } else PostMessageW(q[k].h, q[k].m, q[k].wp, q[k].lp);
        }
        q.erase(q.begin(), q.begin() + k);
        // a step runs once the previous one's input is out
        while (win && next < steps.size() && now_s() >= due && q.empty()) step(steps[next++]);
    }
};

RenderOut render(const RenderSpec &spec, const char *tag)
{
    RenderOut R;
    std::vector<std::shared_ptr<Instance>> ins;
    double t0 = now_s();
    for (int k = 0; k < spec.instances; k++) {
        std::string err;
        auto I = Instance::create(O.plugin, err);
        if (!I) { R.err = err; say("[%s] load failed: %s", tag, err.c_str()); return R; }
        if (!spec.stateC.empty() && !I->setState(spec.stateC, spec.stateE)) say("[%s] setState returned an error", tag);
        if (!spec.vstpreset.empty() && !I->loadVstPreset(spec.vstpreset)) say("[%s] loading %s failed", tag, spec.vstpreset.c_str());
        if (!I->setup(O.sr, O.block, spec.offline)) { R.err = "setup failed"; return R; }
        if (k < (int)spec.programs.size() && spec.programs[k] >= 0) I->selectProgram(spec.programs[k]);
        for (auto &L : spec.lanes) I->setLane(L);
        if (k == 0) {
            auto pr = I->programs();
            R.programCount = (int)pr.size();
            for (auto &p : pr) R.programNames.push_back(p.name);
        }
        ins.push_back(I);
    }
    R.loadS = now_s() - t0;
    R.latency = ins[0]->latency();
    EditorRun ed;
    if (!spec.editorScript.empty()) {
        ed.steps = spec.editorScript;
        bool ok = ed.open(ins[0].get());
        R.editor["opened"] = ok;
        if (ok) {
            ViewRect vr;
            ed.view->getSize(&vr);
            R.editor["size"] = std::to_string(vr.getWidth()) + "x" + std::to_string(vr.getHeight());
            R.editor["resizable"] = ed.view->canResize() == kResultTrue;
        }
    }
    bool changed = false;
    R.out.resize(ins.size());
    const int64_t total = (int64_t)((O.warmup + S.length + O.tail) * O.sr), w0 = (int64_t)(O.warmup * O.sr);
    for (auto &o : R.out) o.reserve((size_t)total * 2 + O.block * 2);
    size_t mi = 0;
    int64_t pos = 0;
    double start = now_s(), lastPoll = 0;
    while (pos < total) {
        // the score's messages in this block, at their sample offsets
        while (mi < S.msgs.size()) {
            int64_t at = w0 + (int64_t)std::llround(S.msgs[mi].t * O.sr);
            if (at >= pos + O.block) break;
            for (auto &I : ins) I->queueMidi(S.msgs[mi], (int32)std::max<int64_t>(0, at - pos));
            mi++;
        }
        if (spec.changeAt >= 0 && !changed && pos >= w0 + (int64_t)(spec.changeAt * O.sr)) {
            for (auto &I : ins) I->selectProgram(spec.changeProgram);
            changed = true;
        }
        for (size_t k = 0; k < ins.size(); k++) {
            ins[k]->process(O.block, pos, O.sr, pos >= w0 - (int64_t)O.sr);   // transport "plays" from 1 s before the score
            float *L = ins[k]->outL(), *Rr = ins[k]->outR();
            auto &o = R.out[k];
            for (int i = 0; i < O.block; i++) { o.push_back(L[i]); o.push_back(Rr[i]); }
        }
        pos += O.block;
        ed.tick();
        // a plugin that stops producing (a hung emulator) must not hang the harness
        double limit = O.timeout > 0 ? O.timeout : 4 * (O.warmup + S.length + O.tail) + 120;
        if (now_s() - start > limit) {
            R.timedOut = true;
            say("[%s] render timed out after %.0f s at %.1f of %.1f s of audio", tag, now_s() - start, pos / O.sr, total / O.sr);
            for (auto &o : R.out) o.resize((size_t)total * 2, 0.f);
            break;
        }
        if (now_s() - lastPoll > 1) { merge_children(R.children, descendants(GetCurrentProcessId())); lastPoll = now_s(); }
        if (!spec.offline) {   // real time: one block per block-length of wall clock
            double due = start + pos / O.sr, n = now_s();
            if (due > n) std::this_thread::sleep_for(std::chrono::duration<double>(due - n));
            else R.maxLateMs = std::max(R.maxLateMs, (n - due) * 1000);
        }
    }
    R.renderS = now_s() - start;
    if (R.timedOut) g_timeouts++;
    if (ed.win) {   // steps not reached yet (a script longer than the render) run now, then the editor closes
        while (ed.next < ed.steps.size() || !ed.q.empty()) { ed.tick(); Sleep(5); }
        for (int k = 0; k < 20; k++) { ed.tick(); Sleep(10); }
        R.editor["steps"] = ed.log;
        R.editor["screenshots"] = ed.shots;
        ed.close();
    }
    merge_children(R.children, descendants(GetCurrentProcessId()));
    if (!ins[0]->getState(R.savedC, R.savedE)) say("[%s] getState failed", tag);
    if (!spec.saveStateTo.empty()) ins[0]->saveStateFile(spec.saveStateTo);
    if (!spec.savePresetTo.empty() && !ins[0]->saveVstPreset(spec.savePresetTo)) say("[%s] saving %s failed", tag, spec.savePresetTo.c_str());
    t0 = now_s();
    ins.clear();   // shutdown + terminate + release
    R.unloadS = now_s() - t0;
    // children should be gone at once; allow a grace period of 10 s
    for (int i = 0; i < 100; i++) {
        R.leftover = descendants(GetCurrentProcessId());
        if (R.leftover.empty()) break;
        Sleep(100);
    }
    R.ok = true;
    return R;
}

J level_json(const std::vector<float> &lr)
{
    Level L = level(lr);
    J j = J::obj();
    j["peak"] = r3(L.peak);
    j["peak_dbfs"] = r1(L.peakDb);
    j["rms_dbfs"] = r1(L.rmsDb);
    return j;
}

J notes_json(const std::vector<float> &lr, uint32_t lat, bool withNotes)
{
    NotesSummary sum;
    auto rows = analyze_notes(lr, (int)O.sr, O.warmup, S, lat / O.sr, sum);
    J j = J::obj();
    J t = J::obj();
    t["notes"] = sum.notes;
    t["heard"] = sum.heard;
    t["reported_latency_ms"] = r1(lat * 1000.0 / O.sr);
    t["onset_error_median_ms"] = r1(sum.medianErrMs);
    t["onset_error_mean_ms"] = r1(sum.meanErrMs);
    t["onset_error_std_ms"] = r1(sum.stdErrMs);
    t["onset_error_min_ms"] = r1(sum.minErrMs);
    t["onset_error_max_ms"] = r1(sum.maxErrMs);
    t["jitter_spread_ms"] = r1(sum.maxErrMs - sum.minErrMs);
    j["timing"] = t;
    J p = J::obj();
    p["reference_note"] = sum.refNote;
    p["notes_measured"] = sum.pitched;
    p["max_abs_cents_off"] = r1(sum.maxAbsCents);
    p["mean_abs_cents_off"] = r1(sum.meanAbsCents);
    j["pitch"] = p;
    if (withNotes) {
        J a = J::arr();
        for (auto &r : rows) {
            J n = J::obj();
            n["t"] = r3(r.n.t);
            n["note"] = r.n.note;
            n["section"] = r.n.section;
            n["heard"] = r.heard;
            if (r.heard) {
                n["onset_raw_ms"] = r1(r.onsetRawMs);
                n["onset_error_ms"] = r1(r.onsetErrMs);
                n["peak"] = r3(r.peak);
            }
            if (r.pitched) {
                n["fft_peak_hz"] = r1(r.hz);
                n["interval_cents"] = r1(r.intervalCents);
                n["cents_off"] = r1(r.centsOff);
            }
            a.push(n);
        }
        j["notes"] = a;
    }
    return j;
}

J compare_json(const Compare &c)
{
    J j = J::obj();
    j["bit_identical"] = c.identical;
    j["max_abs_diff"] = c.maxAbsDiff < 1e-4 ? c.maxAbsDiff : r3(c.maxAbsDiff * 1000) / 1000;
    j["diff_rms_dbfs"] = r1(c.diffRmsDb);
    j["sample_corr"] = r3(c.sampleCorr);
    j["envelope_corr"] = r3(c.envCorr);
    j["envelope_shift_ms"] = c.envShiftMs;
    return j;
}

J procs_json(const std::vector<ProcInfo> &v)
{
    J a = J::arr();
    for (auto &p : v) {
        J o = J::obj();
        o["pid"] = (unsigned)p.pid;
        o["exe"] = p.exe;
        a.push(o);
    }
    return a;
}

J render_json(const RenderOut &R, const char *wav, size_t k = 0)
{
    J j = J::obj();
    j["wav"] = wav;
    if (R.timedOut) j["timed_out"] = true;
    j["seconds"] = r3(R.out[k].size() / 2 / O.sr);
    j["load_s"] = r3(R.loadS);
    j["render_s"] = r3(R.renderS);
    j["unload_s"] = r3(R.unloadS);
    j["latency_samples"] = (unsigned)R.latency;
    j["latency_ms"] = r1(R.latency * 1000.0 / O.sr);
    j["level"] = level_json(R.out[k]);
    J n = notes_json(R.out[k], R.latency, true);
    j["timing"] = n["timing"];
    j["pitch"] = n["pitch"];
    j["notes"] = n["notes"];
    return j;
}

std::vector<AutoLane> parse_automation(const std::string &pluginPath)
{
    std::vector<AutoLane> lanes;
    if (O.automate.empty()) return lanes;
    std::string err;
    auto I = Instance::create(pluginPath, err);
    if (!I) return lanes;
    auto ps = I->params(true);
    for (auto &spec : O.automate) {
        // NAME_OR_ID:t=v;t=v;...  (seconds from the start of the render, normalized values)
        size_t c = spec.find(':');
        if (c == std::string::npos) continue;
        std::string who = spec.substr(0, c), pts = spec.substr(c + 1);
        AutoLane L;
        bool found = false;
        for (auto &p : ps)
            if (p.name == who || std::to_string(p.info.id) == who) { L.id = p.info.id; found = true; break; }
        if (!found) { say("automation: no parameter '%s'", who.c_str()); continue; }
        size_t p = 0;
        while (p < pts.size()) {
            size_t q = pts.find(';', p);
            std::string it = pts.substr(p, q == std::string::npos ? std::string::npos : q - p);
            double t, v;
            if (sscanf(it.c_str(), "%lf=%lf", &t, &v) == 2) L.pts.push_back({t, v});
            if (q == std::string::npos) break;
            p = q + 1;
        }
        std::sort(L.pts.begin(), L.pts.end());
        L.loop = false;
        L.length = L.pts.empty() ? 0 : L.pts.back().first;
        lanes.push_back(L);
    }
    return lanes;
}

bool want(const char *t) { return O.tests.count(t) > 0; }

}  // namespace

int run_harness(const std::vector<std::string> &args)
{
    O.tests = {"offline", "realtime", "repeat", "state", "preset", "progchange", "multi", "orphans"};
    for (size_t i = 0; i < args.size(); i++) {
        const std::string &a = args[i];
        auto next = [&]() { return i + 1 < args.size() ? args[++i] : std::string(); };
        if (a == "--test") O.plugin = next();
        else if (a == "--report") O.report = next();
        else if (a == "--out-dir") O.outDir = next();
        else if (a == "--midi") O.midiFile = next();
        else if (a == "--pattern") O.pattern = next();
        else if (a == "--score") O.score = next();
        else if (a == "--sr") O.sr = atof(next().c_str());
        else if (a == "--block") O.block = atoi(next().c_str());
        else if (a == "--render-timeout") O.timeout = atof(next().c_str());
        else if (a == "--warmup") O.warmup = atof(next().c_str());
        else if (a == "--tail") O.tail = atof(next().c_str());
        else if (a == "--repeat") O.repeat = atoi(next().c_str());
        else if (a == "--instances") O.instances = atoi(next().c_str());
        else if (a == "--program") O.program = atoi(next().c_str());
        else if (a == "--state-program") O.stateProgram = atoi(next().c_str());
        else if (a == "--load-state") O.loadState = next();
        else if (a == "--automate") O.automate.push_back(next());
        else if (a == "--kill-orphans") O.killOrphans = true;
        else if (a == "--change-at") O.changeAt = atof(next().c_str());
        else if (a == "--change-program") O.changeProgram = atoi(next().c_str());
        else if (a == "--state-contains") O.stateContains = next();
        else if (a == "--editor-script" || a == "--editor-script-file") {
            std::string v = next(), all;
            if (a == "--editor-script-file") { std::ifstream f(v); all.assign(std::istreambuf_iterator<char>(f), {}); }
            else all = v;
            char sep = a == "--editor-script" ? '|' : '\n';
            size_t p = 0;
            while (p <= all.size()) {
                size_t q = all.find(sep, p);
                std::string st = all.substr(p, q == std::string::npos ? std::string::npos : q - p);
                while (!st.empty() && (st.back() == '\r' || st.back() == ' ')) st.pop_back();
                while (!st.empty() && st.front() == ' ') st.erase(0, 1);
                if (!st.empty() && st[0] != '#') O.editorScript.push_back(st);
                if (q == std::string::npos) break;
                p = q + 1;
            }
        }
        else if (a == "--multi-programs") {
            std::string l = next();
            for (size_t p = 0; p < l.size();) {
                O.multiPrograms.push_back(atoi(l.c_str() + p));
                size_t q = l.find(',', p);
                if (q == std::string::npos) break;
                p = q + 1;
            }
        }
        else if (a == "--tests") {
            O.tests.clear();
            std::string l = next();
            size_t p = 0;
            while (p <= l.size()) {
                size_t q = l.find(',', p);
                O.tests.insert(l.substr(p, q == std::string::npos ? std::string::npos : q - p));
                if (q == std::string::npos) break;
                p = q + 1;
            }
        }
    }
    if (O.plugin.empty()) { say("--test needs a plugin path"); return 2; }
    O.block = std::max(16, std::min(O.block, 8192));
    if (O.outDir.empty()) {
        SYSTEMTIME st;
        GetLocalTime(&st);
        char b[64];
        snprintf(b, sizeof b, "bhtest-%04d%02d%02d-%02d%02d%02d", st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
        O.outDir = b;
    }
    CreateDirectoryW(widen(O.outDir).c_str(), NULL);
    if (O.report.empty()) O.report = join(O.outDir, "report.json");
    g_logf = _wfopen(widen(join(O.outDir, "harness.log")).c_str(), L"w");
    set_log_sink([](const std::string &s) { say("%s", s.c_str()); });

    std::string scoreSrc;
    if (!O.midiFile.empty()) {
        std::string err;
        if (!read_midi_file(O.midiFile, S, err)) { say("MIDI file: %s", err.c_str()); return 2; }
        scoreSrc = "midi file " + O.midiFile;
    } else if (!O.score.empty()) {
        S = parse_score(O.score);
        scoreSrc = "score";
    } else {
        S = test_pattern(O.pattern);
        scoreSrc = "test pattern: " + O.pattern;
    }
    say("BasiliskHost %s harness: %s", BH_VERSION, O.plugin.c_str());
    say("score: %s, %zu notes, %.1f s; warmup %.1f s, tail %.1f s, %.0f Hz, block %d", scoreSrc.c_str(), S.notes.size(), S.length,
        O.warmup, O.tail, O.sr, O.block);

    J rep = J::obj();
    rep["host"] = "BasiliskHost " BH_VERSION;
    {
        SYSTEMTIME st;
        GetLocalTime(&st);
        char b[64];
        snprintf(b, sizeof b, "%04d-%02d-%02dT%02d:%02d:%02d", st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute, st.wSecond);
        rep["date"] = b;
    }
    J settings = J::obj();
    settings["sample_rate"] = O.sr;
    settings["block"] = O.block;
    settings["warmup_s"] = O.warmup;
    settings["tail_s"] = O.tail;
    settings["score"] = scoreSrc;
    settings["score_notes"] = (unsigned)S.notes.size();
    settings["score_length_s"] = r3(S.length);
    rep["settings"] = settings;

    // plugin facts, from a short-lived instance
    std::vector<AutoLane> lanes;
    int nProg = 0;
    {
        std::string err;
        double t0 = now_s();
        auto I = Instance::create(O.plugin, err);
        if (!I) {
            say("load failed: %s", err.c_str());
            rep["error"] = "load failed: " + err;
            std::ofstream(O.report) << rep.dump() << "\n";
            return 1;
        }
        J p = J::obj();
        p["path"] = O.plugin;
        p["name"] = I->name;
        p["vendor"] = I->vendor;
        p["class_id"] = I->classIdStr;
        p["sdk"] = I->info.sdkVersion();
        p["version"] = I->info.version();
        p["create_s"] = r3(now_s() - t0);
        I->setup(O.sr, O.block, true);
        p["latency_samples"] = (unsigned)I->latency();
        J pa = J::arr();
        auto ps = I->params(false);
        for (auto &x : ps) {
            J o = J::obj();
            o["id"] = (unsigned)x.info.id;
            o["name"] = x.name;
            o["default"] = r3(x.info.defaultNormalizedValue);
            o["steps"] = x.info.stepCount;
            o["automatable"] = (x.info.flags & ParameterInfo::kCanAutomate) != 0;
            pa.push(o);
        }
        p["parameters"] = pa;
        p["parameters_total_incl_hidden"] = (unsigned)I->params(true).size();
        J pr = J::arr();
        auto progs = I->programs();
        nProg = (int)progs.size();
        for (auto &x : progs) pr.push(x.name);
        p["programs"] = pr;
        rep["plugin"] = p;
        say("plugin: %s (%s), %zu parameters, %d programs, latency %u", I->name.c_str(), I->vendor.c_str(), ps.size(), nProg, I->latency());
    }
    lanes = parse_automation(O.plugin);

    J renders = J::obj(), pass = J::obj();
    std::vector<ProcInfo> allChildren, allLeftover;
    auto track = [&](const RenderOut &R) { merge_children(allChildren, R.children); merge_children(allLeftover, R.leftover); };
    RenderSpec base;
    base.programs = {O.program};
    base.lanes = lanes;
    if (!O.loadState.empty()) {
        if (O.loadState.size() > 10 && O.loadState.substr(O.loadState.size() - 10) == ".vstpreset") base.vstpreset = O.loadState;
        else {
            std::ifstream f(O.loadState, std::ios::binary);
            std::string magic;
            std::getline(f, magic);
            if (magic == "BHSTATE1") {   // our file: component + controller blobs after three lines
                std::string l;
                std::getline(f, l);
                std::getline(f, l);
                uint32_t n = 0;
                f.read((char *)&n, 4);
                base.stateC.resize(n);
                f.read(base.stateC.data(), n);
                if (f.read((char *)&n, 4)) { base.stateE.resize(n); f.read(base.stateE.data(), n); }
            } else {   // a raw component state
                f.seekg(0);
                base.stateC.assign(std::istreambuf_iterator<char>(f), {});
            }
        }
    }

    // 1. offline render (+ repeats for determinism)
    RenderOut off;
    std::vector<std::vector<float>> reps;
    if (want("offline") || want("repeat") || want("state") || want("preset")) {
        say("offline render...");
        off = render(base, "offline");
        track(off);
        if (!off.ok) { rep["error"] = off.err; std::ofstream(O.report) << rep.dump() << "\n"; return 1; }
        write_wav(join(O.outDir, "offline.wav"), off.out[0], (int)O.sr);
        renders["offline"] = render_json(off, "offline.wav");
        Level L = level(off.out[0]);
        pass["sound"] = L.peak > 1e-3;
        J t = renders["offline"]["timing"];
        say("  peak %.3f, latency %u, render %.1f s", L.peak, off.latency, off.renderS);
    }
    if (want("repeat") && O.repeat > 0) {
        J d = J::obj(), pairs = J::arr();
        bool allId = true;
        double minEnv = 1;
        for (int k = 0; k < O.repeat; k++) {
            say("offline repeat %d/%d...", k + 1, O.repeat);
            RenderOut r = render(base, "repeat");
            track(r);
            if (!r.ok) break;
            char nm[64];
            snprintf(nm, sizeof nm, "offline-repeat%d.wav", k + 1);
            write_wav(join(O.outDir, nm), r.out[0], (int)O.sr);
            Compare c = compare(off.out[0], r.out[0], (int)O.sr);
            J cj = compare_json(c);
            cj["wav"] = nm;
            pairs.push(cj);
            allId = allId && c.identical;
            minEnv = std::min(minEnv, c.envCorr);
            say("  vs first: identical %s, max diff %.2g, envelope corr %.3f", c.identical ? "yes" : "no", c.maxAbsDiff, c.envCorr);
        }
        d["renders_compared"] = (int)pairs.size();
        d["all_bit_identical"] = allId;
        d["min_envelope_corr"] = r3(minEnv);
        d["vs_first"] = pairs;
        rep["determinism"] = d;
        pass["determinism"] = minEnv >= 0.95;
    }

    // 2. real-time-paced render
    if (want("realtime")) {
        say("real-time render (%.0f s)...", O.warmup + S.length + O.tail);
        RenderSpec rs = base;
        rs.offline = false;
        RenderOut rt = render(rs, "realtime");
        track(rt);
        if (rt.ok) {
            write_wav(join(O.outDir, "realtime.wav"), rt.out[0], (int)O.sr);
            J j = render_json(rt, "realtime.wav");
            j["max_block_late_ms"] = r1(rt.maxLateMs);
            if (off.ok) j["vs_offline"] = compare_json(compare(off.out[0], rt.out[0], (int)O.sr));
            renders["realtime"] = j;
            Level L = level(rt.out[0]);
            pass["realtime_sound"] = L.peak > 1e-3;
            say("  peak %.3f", L.peak);
        }
    }
    rep["renders"] = renders;

    // 3. state: render with a non-default program, save the state, reload into a fresh instance, render, compare
    int sp = O.stateProgram >= 0 ? O.stateProgram : (nProg > 3 ? 3 : nProg > 1 ? 1 : -1);
    auto roundtrip = [&](bool preset) {
        J j = J::obj();
        RenderSpec a = base;
        if (sp >= 0) a.programs = {sp};
        std::string sf = join(O.outDir, preset ? "saved.vstpreset" : "saved.bhstate");
        if (preset) a.savePresetTo = sf;
        else a.saveStateTo = sf;
        say("%s round trip: render with program %d and save...", preset ? "vstpreset" : "state", sp);
        RenderOut A = render(a, "state-a");
        track(A);
        if (!A.ok) return j;
        write_wav(join(O.outDir, preset ? "preset-original.wav" : "state-original.wav"), A.out[0], (int)O.sr);
        RenderSpec b = base;
        b.programs = {-1};
        if (preset) b.vstpreset = sf;
        else { b.stateC = A.savedC; b.stateE = A.savedE; }
        // our own file is checked by reading it back
        if (!preset) {
            std::ifstream f(sf, std::ios::binary);
            j["state_file_bytes"] = (long long)(f.seekg(0, std::ios::end).tellg());
        } else {
            std::ifstream f(sf, std::ios::binary);
            j["vstpreset_bytes"] = (long long)(f.seekg(0, std::ios::end).tellg());
        }
        say("  reload into a fresh instance and render...");
        RenderOut B = render(b, "state-b");
        track(B);
        if (!B.ok) return j;
        write_wav(join(O.outDir, preset ? "preset-reloaded.wav" : "state-reloaded.wav"), B.out[0], (int)O.sr);
        j["program"] = sp;
        j["program_name"] = sp >= 0 && sp < (int)A.programNames.size() ? A.programNames[sp] : "";
        j["component_state_bytes"] = (unsigned)A.savedC.size();
        j["controller_state_bytes"] = (unsigned)A.savedE.size();
        j["reloaded_state_equals_saved"] = B.savedC == A.savedC;
        Compare c = compare(A.out[0], B.out[0], (int)O.sr);
        j["reloaded_vs_original"] = compare_json(c);
        if (off.ok) j["original_vs_default_program"] = compare_json(compare(off.out[0], A.out[0], (int)O.sr));
        say("  reloaded vs original: identical %s, envelope corr %.3f", c.identical ? "yes" : "no", c.envCorr);
        if (preset) pass["vstpreset_reload"] = c.envCorr >= 0.95;
        else pass["state_reload"] = c.envCorr >= 0.95;
        return j;
    };
    if (want("state")) rep["state_roundtrip"] = roundtrip(false);
    if (want("preset")) rep["vstpreset_roundtrip"] = roundtrip(true);

    // 3b. a program change while the score plays, in real time: which notes were dropped
    if (want("progchange") && nProg > 1) {
        RenderSpec pc = base;
        pc.offline = false;
        pc.changeAt = O.changeAt >= 0 ? O.changeAt : std::floor(S.length / 2);
        pc.changeProgram = O.changeProgram >= 0 ? O.changeProgram : (nProg > 3 ? 3 : 1);
        say("program change to %d at %.1f s while playing (real time)...", pc.changeProgram, pc.changeAt);
        RenderOut P = render(pc, "progchange");
        track(P);
        if (P.ok) {
            write_wav(join(O.outDir, "progchange.wav"), P.out[0], (int)O.sr);
            NotesSummary sum;
            auto rows = analyze_notes(P.out[0], (int)O.sr, O.warmup, S, P.latency / O.sr, sum);
            J j = J::obj(), dropped = J::arr();
            int nearChange = 0, before = 0, after = 0;
            for (auto &r : rows) {
                if (r.heard) continue;
                J d = J::obj();
                d["t"] = r3(r.n.t);
                d["note"] = r.n.note;
                d["section"] = r.n.section;
                dropped.push(d);
                if (r.n.t >= pc.changeAt - 0.25 && r.n.t <= pc.changeAt + 3) nearChange++;
                if (r.n.t < pc.changeAt) before++; else after++;
            }
            j["wav"] = "progchange.wav";
            j["change_at_s"] = pc.changeAt;
            j["program"] = pc.changeProgram;
            j["program_name"] = pc.changeProgram < (int)P.programNames.size() ? P.programNames[pc.changeProgram] : "";
            j["notes"] = sum.notes;
            j["heard"] = sum.heard;
            j["notes_dropped"] = sum.notes - sum.heard;
            j["dropped_before_change"] = before;
            j["dropped_after_change"] = after;
            j["dropped_within_3s_of_change"] = nearChange;
            j["dropped"] = dropped;
            j["timing"] = notes_json(P.out[0], P.latency, false)["timing"];
            j["max_block_late_ms"] = r1(P.maxLateMs);
            rep["program_change"] = j;
            pass["program_change_no_drops_near_change"] = nearChange == 0;
            say("  %d of %d notes heard; %d dropped within 3 s of the change", sum.heard, sum.notes, nearChange);
        }
    }

    // 3c. the editor: open it, send it mouse and keys from a script, screenshot it, check the state
    if (want("editor")) {
        RenderSpec e = base;
        e.offline = false;
        e.editorScript = O.editorScript.empty() ? std::vector<std::string>{"wait 8", "shot editor-1", "wait 2", "shot editor-2", "state"} : O.editorScript;
        say("editor: %zu steps (real time render)...", e.editorScript.size());
        RenderOut E = render(e, "editor");
        track(E);
        if (E.ok) {
            write_wav(join(O.outDir, "editor.wav"), E.out[0], (int)O.sr);
            J j = E.editor;
            j["wav"] = "editor.wav";
            j["level"] = level_json(E.out[0]);
            std::string st(E.savedC.begin(), E.savedC.end());
            j["final_state_bytes"] = (unsigned)E.savedC.size();
            if (!O.stateContains.empty()) {
                bool has = st.find(O.stateContains) != std::string::npos;
                j["state_contains"] = O.stateContains;
                j["state_contains_found"] = has;
                pass["editor_state_contains"] = has;
                say("  final state %s \"%s\"", has ? "contains" : "does NOT contain", O.stateContains.c_str());
            }
            rep["editor"] = j;
            pass["editor_opened"] = E.editor.dump().find("\"opened\": true") != std::string::npos;
        }
    }

    // 4. several instances at once, each with its own program
    if (want("multi") && O.instances > 1) {
        RenderSpec m = base;
        m.instances = O.instances;
        m.offline = false;
        m.programs.clear();
        for (int k = 0; k < O.instances; k++)
            m.programs.push_back(k < (int)O.multiPrograms.size() ? O.multiPrograms[k] : nProg > 1 ? k % nProg : -1);
        say("%d instances at once (real time)...", O.instances);
        RenderOut M = render(m, "multi");
        track(M);
        if (M.ok) {
            J j = J::obj(), a = J::arr();
            bool allSound = true;
            for (size_t k = 0; k < M.out.size(); k++) {
                char nm[64];
                snprintf(nm, sizeof nm, "multi-%zu.wav", k);
                write_wav(join(O.outDir, nm), M.out[k], (int)O.sr);
                J one = J::obj();
                one["wav"] = nm;
                one["program"] = m.programs[k];
                one["level"] = level_json(M.out[k]);
                J n = notes_json(M.out[k], M.latency, false);
                one["timing"] = n["timing"];
                one["pitch"] = n["pitch"];
                a.push(one);
                Level L = level(M.out[k]);
                allSound = allSound && L.peak > 1e-3;
                say("  instance %zu: peak %.3f", k, L.peak);
            }
            j["instances"] = a;
            j["child_processes_while_loaded"] = procs_json(M.children);
            if (M.out.size() > 1) j["instance0_vs_instance1"] = compare_json(compare(M.out[0], M.out[1], (int)O.sr));
            j["load_s"] = r3(M.loadS);
            j["unload_s"] = r3(M.unloadS);
            rep["multi_instance"] = j;
            pass["multi_instance_sound"] = allSound;
        }
    }

    // 5. orphans: child processes left after every unload
    if (want("orphans")) {
        unload_modules();
        Sleep(500);
        auto left = descendants(GetCurrentProcessId());
        merge_children(allLeftover, left);
        J j = J::obj();
        j["child_processes_seen"] = procs_json(allChildren);
        j["left_after_unload"] = procs_json(allLeftover);
        j["left_now"] = procs_json(left);
        if (O.killOrphans)
            for (auto &p : left) {   // only our own children, by pid
                HANDLE h = OpenProcess(PROCESS_TERMINATE, FALSE, p.pid);
                if (h) { TerminateProcess(h, 1); CloseHandle(h); }
            }
        rep["orphans"] = j;
        pass["no_orphans"] = allLeftover.empty();
        say("child processes seen: %zu, left after unload: %zu", allChildren.size(), allLeftover.size());
    }

    if (g_timeouts) pass["no_render_timeouts"] = false;
    rep["render_timeouts"] = g_timeouts;
    rep["pass"] = pass;
    bool all = pass.dump().find("false") == std::string::npos;   // every check we ran
    rep["all_pass"] = all;
    std::ofstream(O.report) << rep.dump() << "\n";
    say("report: %s (%s)", O.report.c_str(), all ? "all pass" : "SOME CHECKS FAILED");
    if (g_logf) fclose(g_logf);
    set_log_sink(nullptr);
    return all ? 0 : 1;
}
