// BasiliskHost - the Win32 GUI: instances, editors, audio, MIDI, keyboard, parameters, automation, presets
#include "analysis.h"
#include "engine.h"
#include "json.h"
#include "midi.h"
#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <commdlg.h>
#include <shellapi.h>
#include <shlobj.h>
#include <algorithm>
#include <cmath>
#include <deque>
#include <fstream>
#include <map>
#include <set>

#define BH_VERSION "1.0.0"

// ------------------------------------------------------------------ state
namespace {

HINSTANCE g_hi;
HWND hMain, hList, hDev, hRate, hBuf, hAudioBtn, hStatus, hVol, hMidiIn, hAllInst, hOct, hVel, hVelTxt, hSus, hBend,
    hSeqTxt, hTapBtn, hKeys, hLog;
HFONT g_font;
HBRUSH g_bg;   // one background for windows and their labels
Engine g_eng;
MidiIn g_midiIn;
std::vector<AudioDevice> g_devs;
int g_octave = 4;          // the computer keyboard's A key plays C of this octave
int g_vel = 100;
bool g_spaceSus = false;
int g_mouseNote = -1;
std::set<int> g_compKeys;  // notes held from the computer keyboard
std::deque<std::string> g_logLines;
std::mutex g_logm;
std::vector<std::string> g_pendingLog;

const int RATES[] = {44100, 48000, 88200, 96000};
const int BUFS[] = {64, 128, 256, 512, 1024, 2048};

struct Slot;
struct Row { ParamRec p; HWND name, bar, val; };
struct Slot {
    std::shared_ptr<Instance> I;
    HWND editor = NULL, params = NULL, panel = NULL, prog = NULL, rec = NULL, play = NULL, autoTxt = NULL, autoLen = NULL;
    IPtr<IPlugView> view;
    bool resizing = false;
    std::vector<Row> rows;
    int scroll = 0;
    ParamID sel = 0;
    bool hasSel = false;
    // automation
    bool recording = false;
    double recStart = 0;
    AutoLane recLane;
    std::map<ParamID, AutoLane> stored;
    std::set<ParamID> playingLanes;
    std::vector<std::string> presetFiles;   // .vstpreset files listed after the factory programs
    int nFactory = 0;
};
std::vector<std::unique_ptr<Slot>> g_slots;

enum {
    ID_LIST = 100, ID_LOAD, ID_LOADDIR, ID_DUP, ID_REMOVE, ID_EDITOR, ID_PARAMS, ID_DEV, ID_RATE, ID_BUF, ID_AUDIO, ID_VOL,
    ID_MIDIIN, ID_ALLINST, ID_OCTDN, ID_OCTUP, ID_VEL, ID_SUS, ID_BEND, ID_PLAYMID, ID_PATTERN, ID_STOP, ID_PANIC, ID_TAP,
    ID_SAVEMID,
    // params window
    ID_PROG = 300, ID_PREV, ID_NEXT, ID_LOADPRE, ID_SAVEPRE, ID_LOADST, ID_SAVEST, ID_REC, ID_PLAY, ID_SINE, ID_RAMP, ID_CLEAR,
    ID_AUTOLEN,
};

// ------------------------------------------------------------------ helpers
void logline(const std::string &s)
{
    std::lock_guard<std::mutex> g(g_logm);
    g_pendingLog.push_back(s);
}

void flush_log()
{
    std::vector<std::string> v;
    {
        std::lock_guard<std::mutex> g(g_logm);
        v.swap(g_pendingLog);
    }
    if (v.empty() || !hLog) return;
    for (auto &s : v) {
        g_logLines.push_back(s);
        if (g_logLines.size() > 200) g_logLines.pop_front();
    }
    std::string all;
    for (auto &s : g_logLines) all += s + "\r\n";
    SetWindowTextW(hLog, widen(all).c_str());
    SendMessageW(hLog, EM_LINESCROLL, 0, 100000);
}

HWND mk(const wchar_t *cls, const wchar_t *txt, DWORD style, int x, int y, int w, int h, HWND parent, int id, DWORD ex = 0)
{
    HWND c = CreateWindowExW(ex, cls, txt, WS_CHILD | WS_VISIBLE | style, x, y, w, h, parent, (HMENU)(INT_PTR)id, g_hi, NULL);
    SendMessageW(c, WM_SETFONT, (WPARAM)g_font, TRUE);
    return c;
}
HWND label(const wchar_t *t, int x, int y, int w, int h, HWND p) { return mk(L"STATIC", t, SS_LEFT, x, y, w, h, p, -1); }
HWND button(const wchar_t *t, int x, int y, int w, int h, HWND p, int id, DWORD st = BS_PUSHBUTTON) { return mk(L"BUTTON", t, st | WS_TABSTOP, x, y, w, h, p, id); }

void set_text(HWND h, const std::string &s)
{
    wchar_t cur[512];
    GetWindowTextW(h, cur, 512);
    std::wstring w = widen(s);
    if (w != cur) SetWindowTextW(h, w.c_str());
}

std::string note_name(int n)
{
    static const char *nm[] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    return std::string(nm[n % 12]) + std::to_string(n / 12 - 1);
}

Slot *slot_of(Instance *I)
{
    for (auto &s : g_slots) if (s->I.get() == I) return s.get();
    return nullptr;
}

Slot *selected_slot()
{
    int i = (int)SendMessageW(hList, LB_GETCURSEL, 0, 0);
    if (i < 0 || i >= (int)g_slots.size()) return g_slots.empty() ? nullptr : g_slots.back().get();
    return g_slots[i].get();
}

std::string file_dialog(HWND owner, bool save, const wchar_t *filter, const wchar_t *defExt, const std::string &initDir = "",
                        const std::string &initName = "")
{
    wchar_t buf[MAX_PATH] = {};
    if (!initName.empty()) wcsncpy(buf, widen(initName).c_str(), MAX_PATH - 1);
    std::wstring idir = widen(initDir);
    OPENFILENAMEW of = {sizeof of};
    of.hwndOwner = owner;
    of.lpstrFilter = filter;
    of.lpstrFile = buf;
    of.nMaxFile = MAX_PATH;
    of.lpstrDefExt = defExt;
    of.lpstrInitialDir = idir.empty() ? NULL : idir.c_str();
    of.Flags = OFN_EXPLORER | OFN_NOCHANGEDIR | (save ? OFN_OVERWRITEPROMPT : OFN_FILEMUSTEXIST);
    BOOL ok = save ? GetSaveFileNameW(&of) : GetOpenFileNameW(&of);
    return ok ? narrow(buf) : std::string();
}

std::string folder_dialog(HWND owner)
{
    std::string out;
    IFileOpenDialog *d = nullptr;
    if (FAILED(CoCreateInstance(CLSID_FileOpenDialog, NULL, CLSCTX_ALL, IID_IFileOpenDialog, (void **)&d))) return out;
    DWORD o = 0;
    d->GetOptions(&o);
    d->SetOptions(o | FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM);
    d->SetTitle(L"Choose a .vst3 bundle folder");
    if (SUCCEEDED(d->Show(owner))) {
        IShellItem *it = nullptr;
        if (SUCCEEDED(d->GetResult(&it))) {
            PWSTR p = nullptr;
            if (SUCCEEDED(it->GetDisplayName(SIGDN_FILESYSPATH, &p))) { out = narrow(p); CoTaskMemFree(p); }
            it->Release();
        }
    }
    d->Release();
    return out;
}

std::string presets_dir(Instance *I)
{
    wchar_t docs[MAX_PATH] = {};
    SHGetFolderPathW(NULL, CSIDL_PERSONAL, NULL, 0, docs);
    return narrow(docs) + "\\VST3 Presets\\" + I->vendor + "\\" + I->name;
}

void ensure_dir(const std::string &p)
{
    std::wstring w = widen(p);
    for (size_t i = 3; i <= w.size(); i++)
        if (i == w.size() || w[i] == L'\\') CreateDirectoryW(w.substr(0, i).c_str(), NULL);
}

// ------------------------------------------------------------------ instance list
void refresh_list()
{
    int sel = (int)SendMessageW(hList, LB_GETCURSEL, 0, 0);
    SendMessageW(hList, LB_RESETCONTENT, 0, 0);
    for (auto &s : g_slots) {
        uint32_t lat = s->I->latency();
        char b[256];
        snprintf(b, sizeof b, "#%d  %s   latency %u (%.1f ms)%s", s->I->number, s->I->name.c_str(), lat, lat * 1000.0 / g_eng.sr,
                 s->editor ? "  [editor]" : "");
        SendMessageW(hList, LB_ADDSTRING, 0, (LPARAM)widen(b).c_str());
    }
    if (sel >= (int)g_slots.size()) sel = (int)g_slots.size() - 1;
    SendMessageW(hList, LB_SETCURSEL, sel, 0);
}

void open_editor(Slot *s);
void open_params(Slot *s);
void close_editor(Slot *s);
void close_params(Slot *s);

Slot *add_instance(const std::string &path)
{
    std::string err;
    hlog("loading %s ...", path.c_str());
    double t0 = now_s();
    auto I = Instance::create(path, err);
    if (!I) { hlog("load failed: %s", err.c_str()); return nullptr; }
    auto s = std::make_unique<Slot>();
    s->I = I;
    Slot *sp = s.get();
    I->onEdit = [sp](ParamID id, double v) {   // the plugin's editor moved a parameter (UI thread)
        if (sp->recording && sp->hasSel && id == sp->sel) sp->recLane.pts.push_back({now_s() - sp->recStart, v});
    };
    I->onResize = [sp](int w, int h) {
        if (!sp->editor || sp->resizing) return;
        sp->resizing = true;
        RECT r = {0, 0, w, h};
        AdjustWindowRectEx(&r, (DWORD)GetWindowLongW(sp->editor, GWL_STYLE), FALSE, (DWORD)GetWindowLongW(sp->editor, GWL_EXSTYLE));
        SetWindowPos(sp->editor, NULL, 0, 0, r.right - r.left, r.bottom - r.top, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
        sp->resizing = false;
    };
    g_eng.addInstance(I);
    g_slots.push_back(std::move(s));
    hlog("#%d %s (%s) loaded in %.2f s, latency %u samples (%.1f ms)", I->number, I->name.c_str(), I->vendor.c_str(), now_s() - t0,
         I->latency(), I->latency() * 1000.0 / g_eng.sr);
    refresh_list();
    SendMessageW(hList, LB_SETCURSEL, g_slots.size() - 1, 0);
    return sp;
}

void remove_slot(Slot *s)
{
    close_editor(s);
    close_params(s);
    std::shared_ptr<Instance> I = s->I;
    g_eng.removeInstance(I.get());
    for (auto it = g_slots.begin(); it != g_slots.end(); ++it)
        if (it->get() == s) { g_slots.erase(it); break; }
    double t0 = now_s();
    int n = I->number;
    std::string nm = I->name;
    I.reset();
    hlog("#%d %s removed (%.2f s)", n, nm.c_str(), now_s() - t0);
    refresh_list();
}

// ------------------------------------------------------------------ editor window
LRESULT CALLBACK editor_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    Slot *s = (Slot *)GetWindowLongPtrW(h, GWLP_USERDATA);
    switch (m) {
    case WM_SIZE:
        if (s && s->view && !s->resizing && wp != SIZE_MINIMIZED) {
            if (s->view->canResize() == kResultTrue) {
                ViewRect r(0, 0, LOWORD(lp), HIWORD(lp));
                s->view->checkSizeConstraint(&r);
                s->resizing = true;
                s->view->onSize(&r);
                s->resizing = false;
            }
        }
        return 0;
    case WM_CLOSE:
        if (s) close_editor(s);
        else DestroyWindow(h);
        return 0;
    case WM_ERASEBKGND: {
        RECT r;
        GetClientRect(h, &r);
        FillRect((HDC)wp, &r, (HBRUSH)GetStockObject(BLACK_BRUSH));
        return 1;
    }
    }
    return DefWindowProcW(h, m, wp, lp);
}

void open_editor(Slot *s)
{
    if (s->editor) { ShowWindow(s->editor, SW_SHOWNORMAL); SetForegroundWindow(s->editor); return; }
    if (!s->I->ctl) { hlog("#%d has no edit controller", s->I->number); return; }
    s->view = owned(s->I->ctl->createView(ViewType::kEditor));
    if (!s->view) { hlog("#%d %s has no editor", s->I->number, s->I->name.c_str()); return; }
    if (s->view->isPlatformTypeSupported(kPlatformTypeHWND) != kResultTrue) { hlog("editor does not support HWND"); s->view = nullptr; return; }
    ViewRect vr;
    s->view->getSize(&vr);
    int w = std::max(vr.getWidth(), 100), hh = std::max(vr.getHeight(), 60);
    RECT r = {0, 0, w, hh};
    DWORD st = WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN;
    AdjustWindowRectEx(&r, st, FALSE, 0);
    char title[256];
    snprintf(title, sizeof title, "#%d %s - editor", s->I->number, s->I->name.c_str());
    int off = 30 * (int)(s - g_slots.front().get() >= 0 ? 0 : 0);
    (void)off;
    static int cascade = 0;
    int x = 60 + (cascade % 6) * 40, y = 40 + (cascade % 6) * 40;
    cascade++;
    s->editor = CreateWindowExW(0, L"BHEditor", widen(title).c_str(), st, x, y, r.right - r.left, r.bottom - r.top, NULL, NULL, g_hi, NULL);
    SetWindowLongPtrW(s->editor, GWLP_USERDATA, (LONG_PTR)s);
    s->view->setFrame(&s->I->handler);
    s->I->view = s->view;
    ShowWindow(s->editor, SW_SHOWNORMAL);
    if (s->view->attached(s->editor, kPlatformTypeHWND) != kResultOk) {
        hlog("#%d editor attach failed", s->I->number);
        close_editor(s);
        return;
    }
    // some views report their real size only once attached
    ViewRect vr2;
    if (s->view->getSize(&vr2) == kResultOk && (vr2.getWidth() != w || vr2.getHeight() != hh) && s->I->onResize) s->I->onResize(vr2.getWidth(), vr2.getHeight());
    hlog("#%d editor open, %dx%d, %s", s->I->number, vr2.getWidth(), vr2.getHeight(), s->view->canResize() == kResultTrue ? "resizable" : "fixed size");
    refresh_list();
}

void close_editor(Slot *s)
{
    if (s->view) {
        s->view->removed();
        s->view->setFrame(nullptr);
        s->I->view = nullptr;
        s->view = nullptr;
    }
    if (s->editor) {
        HWND e = s->editor;
        s->editor = NULL;
        SetWindowLongPtrW(e, GWLP_USERDATA, 0);
        DestroyWindow(e);
    }
    refresh_list();
}

// ------------------------------------------------------------------ parameters + presets window
const int ROW_H = 26, PANEL_Y = 128;

void set_param(Slot *s, ParamID id, double v, bool fromUser)
{
    if (s->I->ctl) s->I->ctl->setParamNormalized(id, v);
    s->I->queueParam(id, v);
    if (fromUser && s->recording && s->hasSel && id == s->sel) s->recLane.pts.push_back({now_s() - s->recStart, v});
}

void layout_rows(Slot *s)
{
    RECT r;
    GetClientRect(s->panel, &r);
    int y = -s->scroll;
    for (auto &row : s->rows) {
        MoveWindow(row.name, 8, y + 4, 190, 18, FALSE);
        MoveWindow(row.bar, 200, y, std::max(120, (int)r.right - 340), ROW_H - 2, FALSE);
        MoveWindow(row.val, r.right - 134, y + 4, 126, 18, FALSE);
        y += ROW_H;
    }
    SCROLLINFO si = {sizeof si, SIF_RANGE | SIF_PAGE | SIF_POS, 0, (int)s->rows.size() * ROW_H, (UINT)r.bottom, s->scroll};
    SetScrollInfo(s->panel, SB_VERT, &si, TRUE);
    InvalidateRect(s->panel, NULL, TRUE);
}

void update_auto_text(Slot *s)
{
    if (!s->params) return;
    std::string t = "Automation: ";
    if (!s->hasSel) t += "click a parameter's slider to choose it";
    else {
        std::string nm = "?";
        for (auto &r : s->rows) if (r.p.info.id == s->sel) nm = r.p.name;
        t += nm;
        auto it = s->stored.find(s->sel);
        if (s->recording) t += "  (recording...)";
        else if (it != s->stored.end()) {
            char b[96];
            snprintf(b, sizeof b, "  (curve: %zu points, %.1f s%s)", it->second.pts.size(), it->second.length, s->playingLanes.count(s->sel) ? ", playing" : "");
            t += b;
        }
    }
    int lanes = (int)s->playingLanes.size();
    if (lanes) t += "   lanes playing: " + std::to_string(lanes);
    set_text(s->autoTxt, t);
    SendMessageW(s->rec, BM_SETCHECK, s->recording ? BST_CHECKED : BST_UNCHECKED, 0);
    SendMessageW(s->play, BM_SETCHECK, s->hasSel && s->playingLanes.count(s->sel) ? BST_CHECKED : BST_UNCHECKED, 0);
}

void fill_programs(Slot *s)
{
    SendMessageW(s->prog, CB_RESETCONTENT, 0, 0);
    auto pr = s->I->programs();
    s->nFactory = (int)pr.size();
    for (auto &p : pr) SendMessageW(s->prog, CB_ADDSTRING, 0, (LPARAM)widen(p.name).c_str());
    s->presetFiles.clear();
    WIN32_FIND_DATAW fd;
    std::string dir = presets_dir(s->I.get());
    HANDLE f = FindFirstFileW(widen(dir + "\\*.vstpreset").c_str(), &fd);
    if (f != INVALID_HANDLE_VALUE) {
        do {
            s->presetFiles.push_back(dir + "\\" + narrow(fd.cFileName));
            SendMessageW(s->prog, CB_ADDSTRING, 0, (LPARAM)(std::wstring(L"[file] ") + fd.cFileName).c_str());
        } while (FindNextFileW(f, &fd));
        FindClose(f);
    }
    int cur = s->I->currentProgram();
    SendMessageW(s->prog, CB_SETCURSEL, cur, 0);
}

void build_rows(Slot *s)
{
    for (auto &r : s->rows) { DestroyWindow(r.name); DestroyWindow(r.bar); DestroyWindow(r.val); }
    s->rows.clear();
    for (auto &p : s->I->params(false)) {
        if (p.info.flags & ParameterInfo::kIsProgramChange) continue;   // that one is the program list
        Row r;
        r.p = p;
        r.name = label(widen(p.name).c_str(), 0, 0, 10, 10, s->panel);
        r.bar = mk(TRACKBAR_CLASSW, L"", TBS_HORZ | TBS_NOTICKS | WS_TABSTOP, 0, 0, 10, 10, s->panel, (int)s->rows.size());
        int steps = p.info.stepCount > 0 ? p.info.stepCount : 1000;
        SendMessageW(r.bar, TBM_SETRANGE, FALSE, MAKELPARAM(0, steps));
        r.val = label(L"", 0, 0, 10, 10, s->panel);
        s->rows.push_back(r);
    }
    layout_rows(s);
}

void sync_rows(Slot *s)
{
    if (!s->params || !s->I->ctl) return;
    auto lv = s->I->laneValues();
    HWND cap = GetCapture();
    for (auto &r : s->rows) {
        ParamID id = r.p.info.id;
        double v;
        if (s->playingLanes.count(id) && lv.count(id)) {
            v = lv[id];
            s->I->ctl->setParamNormalized(id, v);   // the editor follows the automation
        } else v = s->I->ctl->getParamNormalized(id);
        int steps = r.p.info.stepCount > 0 ? r.p.info.stepCount : 1000;
        if (cap != r.bar) {
            int pos = (int)std::lround(v * steps);
            if (SendMessageW(r.bar, TBM_GETPOS, 0, 0) != pos) SendMessageW(r.bar, TBM_SETPOS, TRUE, pos);
        }
        std::string t = s->I->paramString(id, v);
        if (!r.p.units.empty()) t += " " + r.p.units;
        if (s->playingLanes.count(id)) t = "~ " + t;
        set_text(r.val, t);
        std::string nm = (s->hasSel && s->sel == id ? "> " : "") + r.p.name;
        set_text(r.name, nm);
    }
}

LRESULT CALLBACK panel_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    Slot *s = (Slot *)GetWindowLongPtrW(h, GWLP_USERDATA);
    switch (m) {
    case WM_HSCROLL:
        if (s && lp) {
            int i = GetDlgCtrlID((HWND)lp);
            if (i >= 0 && i < (int)s->rows.size()) {
                Row &r = s->rows[i];
                int steps = r.p.info.stepCount > 0 ? r.p.info.stepCount : 1000;
                double v = SendMessageW(r.bar, TBM_GETPOS, 0, 0) / (double)steps;
                bool newSel = !s->hasSel || s->sel != r.p.info.id;
                s->sel = r.p.info.id;
                s->hasSel = true;
                if (LOWORD(wp) != TB_ENDTRACK) {
                    if (s->playingLanes.count(r.p.info.id) && !s->recording) {   // touching a playing lane stops it
                        s->playingLanes.erase(r.p.info.id);
                        s->I->removeLane(r.p.info.id);
                    }
                    set_param(s, r.p.info.id, v, true);
                }
                if (newSel) update_auto_text(s);
            }
        }
        return 0;
    case WM_VSCROLL: {
        RECT r;
        GetClientRect(h, &r);
        int total = (int)s->rows.size() * ROW_H, mx = std::max(0, total - (int)r.bottom), y = s->scroll;
        switch (LOWORD(wp)) {
        case SB_LINEUP: y -= ROW_H; break;
        case SB_LINEDOWN: y += ROW_H; break;
        case SB_PAGEUP: y -= r.bottom; break;
        case SB_PAGEDOWN: y += r.bottom; break;
        case SB_THUMBTRACK: case SB_THUMBPOSITION: y = HIWORD(wp); break;
        }
        s->scroll = std::max(0, std::min(mx, y));
        layout_rows(s);
        return 0;
    }
    case WM_MOUSEWHEEL:
        SendMessageW(h, WM_VSCROLL, GET_WHEEL_DELTA_WPARAM(wp) > 0 ? SB_LINEUP : SB_LINEDOWN, 0);
        return 0;
    case WM_SIZE:
        if (s) layout_rows(s);
        return 0;
    case WM_CTLCOLORSTATIC:
        SetBkMode((HDC)wp, TRANSPARENT);
        return (LRESULT)GetSysColorBrush(COLOR_WINDOW);
    }
    return DefWindowProcW(h, m, wp, lp);
}

double auto_len(Slot *s)
{
    wchar_t b[32] = {};
    GetWindowTextW(s->autoLen, b, 32);
    double v = _wtof(b);
    return v > 0.1 ? v : 4;
}

void params_command(Slot *s, int id, int code)
{
    Instance *I = s->I.get();
    switch (id) {
    case ID_PROG:
        if (code == CBN_SELCHANGE) {
            int k = (int)SendMessageW(s->prog, CB_GETCURSEL, 0, 0);
            if (k < s->nFactory) {
                if (I->selectProgram(k)) hlog("#%d program %d", I->number, k);
                else hlog("#%d: no program-change parameter", I->number);
            } else if (k - s->nFactory < (int)s->presetFiles.size()) {
                std::string f = s->presetFiles[k - s->nFactory];
                hlog("#%d preset %s: %s", I->number, f.c_str(), I->loadVstPreset(f) ? "loaded" : "FAILED");
            }
        }
        break;
    case ID_PREV: case ID_NEXT: {
        int n = (int)SendMessageW(s->prog, CB_GETCOUNT, 0, 0);
        if (n <= 0) break;
        int k = (int)SendMessageW(s->prog, CB_GETCURSEL, 0, 0);
        k = (k + (id == ID_NEXT ? 1 : n - 1)) % n;
        SendMessageW(s->prog, CB_SETCURSEL, k, 0);
        params_command(s, ID_PROG, CBN_SELCHANGE);
        break;
    }
    case ID_SAVEPRE: {
        std::string dir = presets_dir(I);
        ensure_dir(dir);
        std::string f = file_dialog(s->params, true, L"VST3 preset (*.vstpreset)\0*.vstpreset\0", L"vstpreset", dir);
        if (!f.empty()) { hlog("save %s: %s", f.c_str(), I->saveVstPreset(f) ? "ok" : "FAILED"); fill_programs(s); }
        break;
    }
    case ID_LOADPRE: {
        std::string f = file_dialog(s->params, false, L"VST3 preset (*.vstpreset)\0*.vstpreset\0All files\0*.*\0", L"vstpreset", presets_dir(I));
        if (!f.empty()) hlog("load %s: %s", f.c_str(), I->loadVstPreset(f) ? "ok" : "FAILED");
        break;
    }
    case ID_SAVEST: {
        std::string f = file_dialog(s->params, true, L"BasiliskHost state (*.bhstate)\0*.bhstate\0", L"bhstate");
        if (!f.empty()) hlog("save state %s: %s", f.c_str(), I->saveStateFile(f) ? "ok" : "FAILED");
        break;
    }
    case ID_LOADST: {
        std::string f = file_dialog(s->params, false, L"BasiliskHost state (*.bhstate)\0*.bhstate\0All files\0*.*\0", L"bhstate");
        if (!f.empty()) {
            std::string err;
            bool ok = I->loadStateFile(f, err);
            hlog("load state %s: %s %s", f.c_str(), ok ? "ok" : "FAILED", err.c_str());
        }
        break;
    }
    case ID_REC:
        if (!s->hasSel) { hlog("choose a parameter first (move its slider)"); SendMessageW(s->rec, BM_SETCHECK, BST_UNCHECKED, 0); break; }
        if (!s->recording) {
            s->recording = true;
            s->recStart = now_s();
            s->recLane = AutoLane();
            s->recLane.id = s->sel;
            s->recLane.pts.push_back({0.0, I->ctl ? I->ctl->getParamNormalized(s->sel) : 0.0});
            s->playingLanes.erase(s->sel);
            I->removeLane(s->sel);
        } else {
            s->recording = false;
            s->recLane.length = std::max(now_s() - s->recStart, s->recLane.pts.back().first + 0.01);
            s->recLane.loop = true;
            s->stored[s->sel] = s->recLane;
            hlog("#%d recorded %zu points over %.1f s; press Play to loop it", I->number, s->recLane.pts.size(), s->recLane.length);
        }
        update_auto_text(s);
        break;
    case ID_PLAY:
        if (!s->hasSel || !s->stored.count(s->sel)) { hlog("no curve for this parameter: record one, or press Sine or Ramp"); update_auto_text(s); break; }
        if (s->playingLanes.count(s->sel)) { s->playingLanes.erase(s->sel); I->removeLane(s->sel); }
        else { s->playingLanes.insert(s->sel); I->setLane(s->stored[s->sel]); }
        update_auto_text(s);
        break;
    case ID_SINE: case ID_RAMP: {
        if (!s->hasSel) { hlog("choose a parameter first (move its slider)"); break; }
        AutoLane L;
        L.id = s->sel;
        L.length = auto_len(s);
        L.loop = true;
        for (int k = 0; k <= 64; k++) {
            double t = L.length * k / 64.0, u = k / 64.0;
            L.pts.push_back({t, id == ID_SINE ? 0.5 + 0.4 * std::sin(2 * M_PI * u) : u});
        }
        s->stored[s->sel] = L;
        s->playingLanes.insert(s->sel);
        I->setLane(L);
        update_auto_text(s);
        break;
    }
    case ID_CLEAR:
        if (s->hasSel) { s->stored.erase(s->sel); s->playingLanes.erase(s->sel); I->removeLane(s->sel); }
        update_auto_text(s);
        break;
    }
}

LRESULT CALLBACK params_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    Slot *s = (Slot *)GetWindowLongPtrW(h, GWLP_USERDATA);
    switch (m) {
    case WM_COMMAND:
        if (s) params_command(s, LOWORD(wp), HIWORD(wp));
        return 0;
    case WM_SIZE:
        if (s && s->panel) MoveWindow(s->panel, 0, PANEL_Y, LOWORD(lp), std::max(10, HIWORD(lp) - PANEL_Y), TRUE);
        return 0;
    case WM_CLOSE:
        if (s) close_params(s);
        else DestroyWindow(h);
        return 0;
    case WM_CTLCOLORSTATIC:
        SetBkMode((HDC)wp, TRANSPARENT);
        return (LRESULT)g_bg;
    }
    return DefWindowProcW(h, m, wp, lp);
}

void open_params(Slot *s)
{
    if (s->params) { ShowWindow(s->params, SW_SHOWNORMAL); SetForegroundWindow(s->params); return; }
    char title[256];
    snprintf(title, sizeof title, "#%d %s - parameters and presets", s->I->number, s->I->name.c_str());
    static int cascade = 0;
    s->params = CreateWindowExW(0, L"BHParams", widen(title).c_str(), WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN, 720 + (cascade % 6) * 30,
                                80 + (cascade % 6) * 30, 640, 520, NULL, NULL, g_hi, NULL);
    cascade++;
    SetWindowLongPtrW(s->params, GWLP_USERDATA, (LONG_PTR)s);
    HWND p = s->params;
    label(L"Program", 10, 13, 60, 18, p);
    s->prog = mk(L"COMBOBOX", L"", CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP, 70, 9, 330, 400, p, ID_PROG);
    button(L"<", 406, 9, 26, 24, p, ID_PREV);
    button(L">", 434, 9, 26, 24, p, ID_NEXT);
    button(L"Load .vstpreset...", 10, 40, 120, 26, p, ID_LOADPRE);
    button(L"Save .vstpreset...", 134, 40, 120, 26, p, ID_SAVEPRE);
    button(L"Load state...", 262, 40, 100, 26, p, ID_LOADST);
    button(L"Save state...", 366, 40, 100, 26, p, ID_SAVEST);
    s->autoTxt = label(L"", 10, 74, 610, 18, p);
    s->rec = button(L"Rec", 10, 96, 50, 26, p, ID_REC, BS_AUTOCHECKBOX | BS_PUSHLIKE);
    s->play = button(L"Play", 64, 96, 50, 26, p, ID_PLAY, BS_AUTOCHECKBOX | BS_PUSHLIKE);
    button(L"Sine", 126, 96, 50, 26, p, ID_SINE);
    button(L"Ramp", 180, 96, 50, 26, p, ID_RAMP);
    button(L"Clear", 234, 96, 50, 26, p, ID_CLEAR);
    label(L"curve length (s)", 296, 101, 100, 18, p);
    s->autoLen = mk(L"EDIT", L"4", ES_AUTOHSCROLL | WS_BORDER | WS_TABSTOP, 400, 98, 50, 22, p, ID_AUTOLEN);
    RECT r;
    GetClientRect(p, &r);
    s->panel = CreateWindowExW(WS_EX_CLIENTEDGE, L"BHPanel", L"", WS_CHILD | WS_VISIBLE | WS_VSCROLL | WS_CLIPCHILDREN, 0, PANEL_Y, r.right,
                               r.bottom - PANEL_Y, p, NULL, g_hi, NULL);
    SetWindowLongPtrW(s->panel, GWLP_USERDATA, (LONG_PTR)s);
    fill_programs(s);
    build_rows(s);
    update_auto_text(s);
    ShowWindow(p, SW_SHOWNORMAL);
}

void close_params(Slot *s)
{
    if (s->params) {
        HWND p = s->params;
        s->params = NULL;
        s->rows.clear();
        s->panel = NULL;
        SetWindowLongPtrW(p, GWLP_USERDATA, 0);
        DestroyWindow(p);
    }
}

// ------------------------------------------------------------------ on-screen keyboard
const int KB_LO = 36, KB_HI = 96;   // C2..C7
bool is_black(int n) { int k = n % 12; return k == 1 || k == 3 || k == 6 || k == 8 || k == 10; }

void key_rects(int w, int h, std::vector<RECT> &rc)
{
    rc.assign(128, RECT{0, 0, 0, 0});
    int whites = 0;
    for (int n = KB_LO; n <= KB_HI; n++) if (!is_black(n)) whites++;
    double ww = (double)w / whites;
    int i = 0;
    for (int n = KB_LO; n <= KB_HI; n++) {
        if (!is_black(n)) { rc[n] = {(int)(i * ww), 0, (int)((i + 1) * ww), h}; i++; }
        else {
            int x = (int)(i * ww - ww * 0.32);
            rc[n] = {x, 0, x + (int)(ww * 0.64), (int)(h * 0.62)};
        }
    }
}

int key_at(HWND h, int x, int y, int *vel)
{
    RECT c;
    GetClientRect(h, &c);
    std::vector<RECT> rc;
    key_rects(c.right, c.bottom - 8, rc);
    POINT p = {x, y};
    int found = -1;
    for (int n = KB_LO; n <= KB_HI; n++) if (is_black(n) && PtInRect(&rc[n], p)) found = n;
    if (found < 0) for (int n = KB_LO; n <= KB_HI; n++) if (!is_black(n) && PtInRect(&rc[n], p)) found = n;
    if (found >= 0 && vel) {   // nearer the front of the key plays louder
        double u = (double)y / std::max(1L, rc[found].bottom);
        *vel = std::max(1, std::min(127, (int)(g_vel * (0.55 + 0.45 * u) + 0.5)));
    }
    return found;
}

void note(int n, int vel, bool on)
{
    if (n < 0 || n > 127) return;
    g_eng.midi({0, (uint8_t)(on ? 0x90 : 0x80), (uint8_t)n, (uint8_t)(on ? vel : 0)});
    InvalidateRect(hKeys, NULL, FALSE);
}

LRESULT CALLBACK keys_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    switch (m) {
    case WM_LBUTTONDOWN: {
        SetCapture(h);
        int v = g_vel;
        int n = key_at(h, GET_X_LPARAM(lp), GET_Y_LPARAM(lp), &v);
        if (n >= 0) { g_mouseNote = n; note(n, v, true); }
        return 0;
    }
    case WM_MOUSEMOVE:
        if (GetCapture() == h && g_mouseNote >= 0) {
            int v = g_vel;
            int n = key_at(h, GET_X_LPARAM(lp), GET_Y_LPARAM(lp), &v);
            if (n >= 0 && n != g_mouseNote) { note(g_mouseNote, 0, false); g_mouseNote = n; note(n, v, true); }
        }
        return 0;
    case WM_LBUTTONUP: case WM_CAPTURECHANGED:
        if (g_mouseNote >= 0) { note(g_mouseNote, 0, false); g_mouseNote = -1; }
        if (m == WM_LBUTTONUP) ReleaseCapture();
        return 0;
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(h, &ps);
        RECT c;
        GetClientRect(h, &c);
        HDC md = CreateCompatibleDC(dc);
        HBITMAP bm = CreateCompatibleBitmap(dc, c.right, c.bottom);
        HGDIOBJ ob = SelectObject(md, bm);
        FillRect(md, &c, g_bg);
        std::vector<RECT> rc;
        key_rects(c.right, c.bottom - 8, rc);
        HBRUSH white = CreateSolidBrush(RGB(250, 250, 248)), black = CreateSolidBrush(RGB(30, 30, 34)), lit = CreateSolidBrush(RGB(64, 140, 230)),
               litb = CreateSolidBrush(RGB(40, 100, 200)), range = CreateSolidBrush(RGB(230, 150, 40));
        HPEN pen = CreatePen(PS_SOLID, 1, RGB(120, 120, 120));
        HGDIOBJ op = SelectObject(md, pen);
        SetBkMode(md, TRANSPARENT);
        SelectObject(md, g_font);
        for (int pass = 0; pass < 2; pass++)
            for (int n = KB_LO; n <= KB_HI; n++) {
                if (is_black(n) != (pass == 1)) continue;
                bool on = g_eng.keys[n] > 0 || g_compKeys.count(n) || g_mouseNote == n;
                SelectObject(md, on ? (pass ? litb : lit) : (pass ? black : white));
                Rectangle(md, rc[n].left, rc[n].top, rc[n].right + (pass ? 0 : 1), rc[n].bottom);
                if (!pass && n % 12 == 0) {
                    RECT t = rc[n];
                    t.top = t.bottom - 18;
                    SetTextColor(md, RGB(110, 110, 110));
                    DrawTextW(md, widen(note_name(n)).c_str(), -1, &t, DT_CENTER | DT_SINGLELINE);
                }
            }
        // the range the computer keyboard plays
        int lo = 12 * (g_octave + 1), hi = lo + 17;
        lo = std::max(lo, KB_LO);
        hi = std::min(hi, KB_HI);
        if (lo <= hi) {
            RECT r = {rc[lo].left, c.bottom - 6, rc[hi].right, c.bottom - 1};
            FillRect(md, &r, range);
        }
        BitBlt(dc, 0, 0, c.right, c.bottom, md, 0, 0, SRCCOPY);
        SelectObject(md, op);
        SelectObject(md, ob);
        DeleteObject(pen);
        for (HBRUSH b : {white, black, lit, litb, range}) DeleteObject(b);
        DeleteObject(bm);
        DeleteDC(md);
        EndPaint(h, &ps);
        return 0;
    }
    }
    return DefWindowProcW(h, m, wp, lp);
}

// ------------------------------------------------------------------ computer keyboard
int key_note(WPARAM vk)
{
    // two rows like a piano: A W S E D F T G Y H U J K O L P ; '
    static const struct { int vk, semi; } map[] = {
        {'A', 0}, {'W', 1}, {'S', 2}, {'E', 3}, {'D', 4}, {'F', 5}, {'T', 6}, {'G', 7}, {'Y', 8}, {'H', 9}, {'U', 10}, {'J', 11},
        {'K', 12}, {'O', 13}, {'L', 14}, {'P', 15}, {VK_OEM_1, 16}, {VK_OEM_7, 17}};
    for (auto &k : map) if ((int)vk == k.vk) return 12 * (g_octave + 1) + k.semi;
    return -1;
}

void update_midi_labels()
{
    set_text(hOct, "Octave " + std::to_string(g_octave) + "  (Z/X)");
    set_text(hVelTxt, std::to_string(g_vel) + "  (C/V)");
    SendMessageW(hVel, TBM_SETPOS, TRUE, g_vel);
    InvalidateRect(hKeys, NULL, FALSE);
}

void sustain(bool on)
{
    g_eng.midi({0, 0xB0, 64, (uint8_t)(on ? 127 : 0)});
    SendMessageW(hSus, BM_SETCHECK, on ? BST_CHECKED : BST_UNCHECKED, 0);
}

bool handle_key(const MSG &msg)
{
    if (msg.message != WM_KEYDOWN && msg.message != WM_KEYUP) return false;
    if (!(msg.hwnd == hMain || IsChild(hMain, msg.hwnd))) return false;
    wchar_t cls[32] = {};
    GetClassNameW(msg.hwnd, cls, 32);
    if (!_wcsicmp(cls, L"Edit") || !_wcsicmp(cls, L"ComboBox") || !_wcsicmp(cls, L"ComboLBox")) return false;
    bool down = msg.message == WM_KEYDOWN, repeat = (msg.lParam & (1 << 30)) != 0;
    WPARAM vk = msg.wParam;
    if (vk == VK_SPACE) {
        if (down && !repeat) { g_spaceSus = true; sustain(true); }
        if (!down) { g_spaceSus = false; sustain(false); }
        return true;
    }
    if (down && !repeat) {
        if (vk == 'Z') { g_octave = std::max(-1, g_octave - 1); update_midi_labels(); return true; }
        if (vk == 'X') { g_octave = std::min(8, g_octave + 1); update_midi_labels(); return true; }
        if (vk == 'C') { g_vel = std::max(1, g_vel - 20); update_midi_labels(); return true; }
        if (vk == 'V') { g_vel = std::min(127, g_vel + 20); update_midi_labels(); return true; }
    }
    int n = key_note(vk);
    if (n < 0 || n > 127) return n >= 0;
    if (down && !repeat && !g_compKeys.count(n)) { g_compKeys.insert(n); note(n, g_vel, true); }
    else if (!down && g_compKeys.count(n)) { g_compKeys.erase(n); note(n, 0, false); }
    return true;
}

// ------------------------------------------------------------------ audio + MIDI setup
void start_audio()
{
    int di = (int)SendMessageW(hDev, CB_GETCURSEL, 0, 0), ri = (int)SendMessageW(hRate, CB_GETCURSEL, 0, 0), bi = (int)SendMessageW(hBuf, CB_GETCURSEL, 0, 0);
    std::wstring id = di >= 0 && di < (int)g_devs.size() ? g_devs[di].id : L"";
    std::string err;
    g_eng.out.gain = (float)std::pow(10.0, (SendMessageW(hVol, TBM_GETPOS, 0, 0) - 100) / 20.0 * 0.6);
    if (!g_eng.startAudio(id, RATES[ri < 0 ? 1 : ri], BUFS[bi < 0 ? 3 : bi], err)) hlog("audio: %s", err.c_str());
    else hlog("audio: %s, %d Hz, block %d, WASAPI buffer %d frames, device period %.1f ms", g_eng.out.deviceName.c_str(), g_eng.out.sampleRate,
              g_eng.out.block, g_eng.out.bufferFrames, g_eng.out.periodMs);
    SetWindowTextW(hAudioBtn, g_eng.out.running() ? L"Stop audio" : L"Start audio");
    refresh_list();
}

void open_midi_in()
{
    int k = (int)SendMessageW(hMidiIn, CB_GETCURSEL, 0, 0);
    g_midiIn.close();
    if (k <= 0) return;
    std::string err;
    if (g_midiIn.open(k - 1, [](const MidiMsg &m) { g_eng.midi(m); }, err)) hlog("MIDI in: device %d open", k - 1);
    else hlog("MIDI in: %s", err.c_str());
}

void update_target()
{
    bool all = SendMessageW(hAllInst, BM_GETCHECK, 0, 0) == BST_CHECKED;
    Slot *s = selected_slot();
    g_eng.target = all || !s ? 0 : s->I->number;
}

std::string g_tapPath;   // set by the self test; otherwise asked for
void toggle_tap()
{
    if (!g_eng.tapping()) {
        g_eng.startTap();
        SetWindowTextW(hTapBtn, L"Stop recording");
        hlog("recording the output...");
        return;
    }
    auto v = g_eng.stopTap();
    SetWindowTextW(hTapBtn, L"Record output");
    std::string f = g_tapPath.empty() ? file_dialog(hMain, true, L"WAV (*.wav)\0*.wav\0", L"wav", "", "output.wav") : g_tapPath;
    if (f.empty()) return;
    write_wav(f, v, g_eng.sr);
    Level L = level(v);
    hlog("output recorded: %.1f s, peak %.1f dBFS, rms %.1f dBFS -> %s", v.size() / 2.0 / g_eng.sr, L.peakDb, L.rmsDb, f.c_str());
}

// ------------------------------------------------------------------ main window
void main_command(int id, int code)
{
    switch (id) {
    case ID_LOAD: {
        std::string f = file_dialog(hMain, false, L"VST3 plugin (*.vst3)\0*.vst3\0All files\0*.*\0", L"vst3");
        if (!f.empty()) add_instance(f);
        update_target();
        break;
    }
    case ID_LOADDIR: {
        std::string f = folder_dialog(hMain);
        if (!f.empty()) add_instance(f);
        update_target();
        break;
    }
    case ID_DUP:
        if (Slot *s = selected_slot()) add_instance(s->I->path);
        update_target();
        break;
    case ID_REMOVE:
        if (Slot *s = selected_slot()) remove_slot(s);
        update_target();
        break;
    case ID_EDITOR:
        if (Slot *s = selected_slot()) open_editor(s);
        break;
    case ID_PARAMS:
        if (Slot *s = selected_slot()) open_params(s);
        break;
    case ID_LIST:
        if (code == LBN_SELCHANGE) update_target();
        if (code == LBN_DBLCLK) if (Slot *s = selected_slot()) open_editor(s);
        break;
    case ID_AUDIO:
        if (g_eng.out.running()) { g_eng.stopAudio(); SetWindowTextW(hAudioBtn, L"Start audio"); hlog("audio stopped"); }
        else start_audio();
        break;
    case ID_DEV: case ID_RATE: case ID_BUF:
        if (code == CBN_SELCHANGE && g_eng.out.running()) start_audio();
        break;
    case ID_MIDIIN:
        if (code == CBN_SELCHANGE) open_midi_in();
        break;
    case ID_ALLINST: update_target(); break;
    case ID_OCTDN: g_octave = std::max(-1, g_octave - 1); update_midi_labels(); break;
    case ID_OCTUP: g_octave = std::min(8, g_octave + 1); update_midi_labels(); break;
    case ID_SUS: sustain(SendMessageW(hSus, BM_GETCHECK, 0, 0) == BST_CHECKED); break;
    case ID_PLAYMID: {
        std::string f = file_dialog(hMain, false, L"MIDI file (*.mid;*.midi)\0*.mid;*.midi\0All files\0*.*\0", L"mid");
        if (f.empty()) break;
        Score s;
        std::string err;
        if (!read_midi_file(f, s, err)) { hlog("MIDI file: %s", err.c_str()); break; }
        hlog("playing %s: %zu notes, %.1f s", f.c_str(), s.notes.size(), s.length);
        g_eng.play(s);
        break;
    }
    case ID_SAVEMID: {
        std::string f = file_dialog(hMain, true, L"MIDI file (*.mid)\0*.mid\0", L"mid", "", "basilisk-test-pattern.mid");
        if (!f.empty()) hlog("test pattern written to %s: %s", f.c_str(), write_midi_file(f, test_pattern()) ? "ok" : "FAILED");
        break;
    }
    case ID_PATTERN: {
        Score s = test_pattern();
        hlog("test pattern: scale, chords, fast repeats, sustain, bend (%zu notes, %.1f s)", s.notes.size(), s.length);
        g_eng.play(s);
        break;
    }
    case ID_STOP: g_eng.stopPlay(); break;
    case ID_PANIC: g_eng.panic(); g_compKeys.clear(); InvalidateRect(hKeys, NULL, FALSE); break;
    case ID_TAP: toggle_tap(); break;
    }
}

void main_timer()
{
    flush_log();
    // latency changes, parameter refreshes
    bool relist = false;
    for (auto &s : g_slots) {
        if (s->I->latencyChanged.exchange(false)) { relist = true; hlog("#%d latency now %u samples", s->I->number, s->I->latency()); }
        if (s->I->paramsChanged.exchange(false) && s->params) fill_programs(s.get());
        if (s->params) sync_rows(s.get());
        if (s->recording) update_auto_text(s.get());
    }
    if (relist) refresh_list();
    // status line
    char b[512];
    uint32_t maxLat = 0;
    for (auto &s : g_slots) maxLat = std::max(maxLat, s->I->latency());
    if (g_eng.out.running())
        snprintf(b, sizeof b, "%s | %d Hz, block %d, buffer %d (%.1f ms) | plugin latency %u smp (%.1f ms), output total %.1f ms | DSP %.0f%% | underruns %llu | peak %.1f dB",
                 g_eng.out.deviceName.c_str(), g_eng.out.sampleRate, g_eng.out.block, g_eng.out.bufferFrames,
                 g_eng.out.bufferFrames * 1000.0 / g_eng.out.sampleRate, maxLat, maxLat * 1000.0 / g_eng.sr,
                 (maxLat + g_eng.out.bufferFrames + g_eng.block) * 1000.0 / g_eng.sr, g_eng.out.load * 100,
                 (unsigned long long)g_eng.out.underruns, g_eng.peak > 1e-6 ? 20 * std::log10(g_eng.peak.load()) : -120.0);
    else snprintf(b, sizeof b, "audio stopped | plugin latency %u samples", maxLat);
    set_text(hStatus, b);
    if (g_eng.playing()) snprintf(b, sizeof b, "playing %.1f / %.1f s", g_eng.playPos(), g_eng.playLength());
    else b[0] = 0;
    set_text(hSeqTxt, b);
    static uint8_t lastKeys[128];
    bool changed = false;
    for (int i = 0; i < 128; i++) if (g_eng.keys[i] != lastKeys[i]) { lastKeys[i] = g_eng.keys[i]; changed = true; }
    if (changed) InvalidateRect(hKeys, NULL, FALSE);
}

void selftest_tick();

LRESULT CALLBACK main_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    switch (m) {
    case WM_COMMAND: main_command(LOWORD(wp), HIWORD(wp)); return 0;
    case WM_HSCROLL:
        if ((HWND)lp == hVel) { g_vel = (int)SendMessageW(hVel, TBM_GETPOS, 0, 0); update_midi_labels(); }
        else if ((HWND)lp == hVol) g_eng.out.gain = (float)std::pow(10.0, (SendMessageW(hVol, TBM_GETPOS, 0, 0) - 100) / 20.0 * 0.6);
        else if ((HWND)lp == hBend) {
            int v = (int)SendMessageW(hBend, TBM_GETPOS, 0, 0);
            if (LOWORD(wp) == TB_ENDTRACK) { v = 8192; SendMessageW(hBend, TBM_SETPOS, TRUE, v); }   // springs back
            g_eng.midi({0, 0xE0, (uint8_t)(v & 0x7F), (uint8_t)(v >> 7)});
        }
        SetFocus(hMain);   // keep the computer keyboard playing
        return 0;
    case WM_TIMER:
        if (wp == 1) main_timer();
        if (wp == 2) selftest_tick();
        return 0;
    case WM_DROPFILES: {
        HDROP d = (HDROP)wp;
        UINT n = DragQueryFileW(d, 0xFFFFFFFF, NULL, 0);
        for (UINT i = 0; i < n; i++) {
            wchar_t p[MAX_PATH];
            DragQueryFileW(d, i, p, MAX_PATH);
            add_instance(narrow(p));
        }
        DragFinish(d);
        update_target();
        return 0;
    }
    case WM_CTLCOLORSTATIC:
        if ((HWND)lp == hLog) break;
        SetBkMode((HDC)wp, TRANSPARENT);
        return (LRESULT)g_bg;
    case WM_ACTIVATE:
        if (LOWORD(wp) == WA_INACTIVE && !g_compKeys.empty()) {   // no stuck notes when focus leaves
            for (int n : g_compKeys) note(n, 0, false);
            g_compKeys.clear();
        }
        return 0;
    case WM_CLOSE:
        g_eng.stopPlay();
        g_eng.stopAudio();
        g_midiIn.close();
        while (!g_slots.empty()) remove_slot(g_slots.back().get());
        DestroyWindow(h);
        return 0;
    case WM_DESTROY: PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(h, m, wp, lp);
}

void build_main()
{
    HWND p = hMain;
    int X = 8;
    mk(L"BUTTON", L"Instances", BS_GROUPBOX, X, 4, 300, 262, p, -1);
    hList = mk(L"LISTBOX", L"", LBS_NOTIFY | WS_VSCROLL | WS_BORDER | WS_TABSTOP | LBS_NOINTEGRALHEIGHT, X + 10, 24, 280, 160, p, ID_LIST);
    button(L"Load .vst3...", X + 10, 190, 90, 28, p, ID_LOAD);
    button(L"Load bundle...", X + 104, 190, 90, 28, p, ID_LOADDIR);
    button(L"Duplicate", X + 198, 190, 92, 28, p, ID_DUP);
    button(L"Editor", X + 10, 224, 90, 28, p, ID_EDITOR);
    button(L"Parameters", X + 104, 224, 90, 28, p, ID_PARAMS);
    button(L"Remove", X + 198, 224, 92, 28, p, ID_REMOVE);

    int A = 318, W = 630;
    mk(L"BUTTON", L"Audio output (WASAPI)", BS_GROUPBOX, A, 4, W, 118, p, -1);
    label(L"Device", A + 10, 28, 50, 18, p);
    hDev = mk(L"COMBOBOX", L"", CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP, A + 62, 24, 300, 300, p, ID_DEV);
    label(L"Rate", A + 372, 28, 32, 18, p);
    hRate = mk(L"COMBOBOX", L"", CBS_DROPDOWNLIST | WS_TABSTOP, A + 404, 24, 74, 200, p, ID_RATE);
    label(L"Block", A + 486, 28, 36, 18, p);
    hBuf = mk(L"COMBOBOX", L"", CBS_DROPDOWNLIST | WS_TABSTOP, A + 524, 24, 62, 200, p, ID_BUF);
    hAudioBtn = button(L"Start audio", A + 10, 54, 100, 28, p, ID_AUDIO);
    label(L"Volume", A + 124, 60, 46, 18, p);
    hVol = mk(TRACKBAR_CLASSW, L"", TBS_HORZ | TBS_NOTICKS, A + 170, 56, 150, 26, p, ID_VOL);
    SendMessageW(hVol, TBM_SETRANGE, FALSE, MAKELPARAM(0, 100));
    SendMessageW(hVol, TBM_SETPOS, TRUE, 100);
    hTapBtn = button(L"Record output", A + 330, 54, 110, 28, p, ID_TAP);
    hStatus = label(L"", A + 10, 88, W - 20, 30, p);

    mk(L"BUTTON", L"MIDI", BS_GROUPBOX, A, 126, W, 140, p, -1);
    label(L"MIDI in", A + 10, 150, 50, 18, p);
    hMidiIn = mk(L"COMBOBOX", L"", CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP, A + 62, 146, 260, 300, p, ID_MIDIIN);
    hAllInst = button(L"Play all instances (else the selected one)", A + 334, 146, 280, 24, p, ID_ALLINST, BS_AUTOCHECKBOX);
    button(L"-", A + 10, 176, 26, 26, p, ID_OCTDN);
    hOct = label(L"", A + 40, 181, 100, 18, p);
    button(L"+", A + 140, 176, 26, 26, p, ID_OCTUP);
    label(L"Velocity", A + 178, 181, 50, 18, p);
    hVel = mk(TRACKBAR_CLASSW, L"", TBS_HORZ | TBS_NOTICKS, A + 228, 178, 110, 26, p, ID_VEL);
    SendMessageW(hVel, TBM_SETRANGE, FALSE, MAKELPARAM(1, 127));
    hVelTxt = label(L"", A + 340, 181, 70, 18, p);
    hSus = button(L"Sustain (Space)", A + 412, 178, 110, 24, p, ID_SUS, BS_AUTOCHECKBOX | BS_PUSHLIKE);
    label(L"Bend", A + 530, 181, 32, 18, p);
    hBend = mk(TRACKBAR_CLASSW, L"", TBS_HORZ | TBS_NOTICKS, A + 562, 178, 60, 26, p, ID_BEND);
    SendMessageW(hBend, TBM_SETRANGE, TRUE, MAKELPARAM(0, 16383));
    SendMessageW(hBend, TBM_SETPOS, TRUE, 8192);
    button(L"Play .mid...", A + 10, 210, 86, 28, p, ID_PLAYMID);
    button(L"Test pattern", A + 100, 210, 92, 28, p, ID_PATTERN);
    button(L"Save pattern .mid...", A + 196, 210, 124, 28, p, ID_SAVEMID);
    button(L"Stop", A + 324, 210, 60, 28, p, ID_STOP);
    button(L"Panic", A + 388, 210, 60, 28, p, ID_PANIC);
    hSeqTxt = label(L"", A + 456, 216, 166, 18, p);
    label(L"Keys: A W S E D F T G Y H U J K O L P ; '   Z/X octave   C/V velocity   Space sustain", A + 10, 244, 600, 18, p);

    hKeys = CreateWindowExW(0, L"BHKeys", L"", WS_CHILD | WS_VISIBLE, X, 274, 940, 110, p, NULL, g_hi, NULL);
    hLog = mk(L"EDIT", L"", ES_MULTILINE | ES_READONLY | ES_AUTOVSCROLL | WS_VSCROLL | WS_BORDER, X, 390, 940, 96, p, -1);

    for (int r : RATES) SendMessageW(hRate, CB_ADDSTRING, 0, (LPARAM)std::to_wstring(r).c_str());
    for (int b : BUFS) SendMessageW(hBuf, CB_ADDSTRING, 0, (LPARAM)std::to_wstring(b).c_str());
    SendMessageW(hRate, CB_SETCURSEL, 1, 0);
    SendMessageW(hBuf, CB_SETCURSEL, 3, 0);
    g_devs = audio_devices();
    // the default device first
    std::stable_sort(g_devs.begin(), g_devs.end(), [](const AudioDevice &a, const AudioDevice &b) { return a.isDefault > b.isDefault; });
    g_devs.push_back({L"dummy", "Dummy (no device, real-time clock)", false});
    for (auto &d : g_devs) SendMessageW(hDev, CB_ADDSTRING, 0, (LPARAM)widen(d.name + (d.isDefault ? "  (default)" : "")).c_str());
    SendMessageW(hDev, CB_SETCURSEL, 0, 0);
    SendMessageW(hMidiIn, CB_ADDSTRING, 0, (LPARAM)L"(none)");
    auto mids = midi_in_devices();
    for (auto &d : mids) SendMessageW(hMidiIn, CB_ADDSTRING, 0, (LPARAM)widen(d).c_str());
    SendMessageW(hMidiIn, CB_SETCURSEL, 0, 0);
    SendMessageW(hAllInst, BM_SETCHECK, BST_CHECKED, 0);
    hlog("BasiliskHost %s - %zu audio device(s), %zu MIDI input(s)", BH_VERSION, g_devs.size(), mids.size());
    update_midi_labels();
}

// ------------------------------------------------------------------ GUI self test (--selftest DIR)
struct SelfTest {
    bool on = false;
    std::string dir;
    std::vector<std::string> plugins;
    int step = 0;
    double t0 = 0, stepT = 0;
    Loopback loop;
    bool loopOn = false;
    std::wstring devId;
    J rep = J::obj();
    std::vector<std::pair<std::string, std::pair<int64_t, int64_t>>> phases;   // name -> tap frames
    int64_t tapStart = 0, patternStart = 0;
    double audioT0 = 0;
    std::vector<ProcInfo> children;
    Score pattern;
} T;

int64_t tap_frames() { return g_eng.pos; }


void shots(const char *tag)
{
    J a = J::arr();
    char b[512];
    snprintf(b, sizeof b, "%s\\%s-main.bmp", T.dir.c_str(), tag);
    save_bmp(hMain, b, false);
    a.push(b);
    for (auto &s : g_slots) {
        if (s->editor) {
            snprintf(b, sizeof b, "%s\\%s-editor%d.bmp", T.dir.c_str(), tag, s->I->number);
            save_bmp(s->editor, b, false);
            a.push(b);
        }
        if (s->params) {
            snprintf(b, sizeof b, "%s\\%s-params%d.bmp", T.dir.c_str(), tag, s->I->number);
            save_bmp(s->params, b, false);
            a.push(b);
        }
    }
    T.rep["screenshots"].push(a);
}

void click_key(int n, bool down)
{
    RECT c;
    GetClientRect(hKeys, &c);
    std::vector<RECT> rc;
    key_rects(c.right, c.bottom - 8, rc);
    int x = (rc[n].left + rc[n].right) / 2, y = rc[n].bottom - 12;
    SendMessageW(hKeys, down ? WM_LBUTTONDOWN : WM_LBUTTONUP, down ? MK_LBUTTON : 0, MAKELPARAM(x, y));
}

void type_key(WPARAM vk, bool down)
{
    // through the message loop, as a real key press (the loop's key handler sees it)
    PostMessageW(hMain, down ? WM_KEYDOWN : WM_KEYUP, vk, down ? 1 : (LPARAM)0xC0000001);
}

void phase_begin(const std::string &name)
{
    T.phases.push_back({name, {tap_frames() - T.tapStart, -1}});
    hlog("[selftest %.1f s, audio %.1f s] %s", now_s() - T.t0, (tap_frames() - T.tapStart) / (double)g_eng.sr, name.c_str());
}
void phase_end() { if (!T.phases.empty()) T.phases.back().second.second = tap_frames() - T.tapStart; }

void selftest_finish()
{
    KillTimer(hMain, 2);
    auto tap = g_eng.stopTap();
    std::vector<float> lb;
    if (T.loopOn) lb = T.loop.stop();
    write_wav(T.dir + "\\tap.wav", tap, g_eng.sr);
    J ph = J::arr();
    for (auto &p : T.phases) {
        J o = J::obj();
        o["phase"] = p.first;
        int64_t a = std::max<int64_t>(0, p.second.first), b = p.second.second < 0 ? (int64_t)tap.size() / 2 : p.second.second;
        o["from_s"] = r3(a / (double)g_eng.sr);
        o["to_s"] = r3(b / (double)g_eng.sr);
        Level L = level(tap, (size_t)a, (size_t)b);
        o["tap_peak_dbfs"] = r1(L.peakDb);
        o["tap_rms_dbfs"] = r1(L.rmsDb);
        if (!lb.empty() && T.loop.sampleRate > 0) {
            double k = (double)T.loop.sampleRate / g_eng.sr;
            Level M = level(lb, (size_t)(a * k), (size_t)(b * k));
            o["loopback_peak_dbfs"] = r1(M.peakDb);
            o["loopback_rms_dbfs"] = r1(M.rmsDb);
        }
        ph.push(o);
    }
    T.rep["phases"] = ph;
    Level L = level(tap);
    J t = J::obj();
    t["wav"] = T.dir + "\\tap.wav";
    t["seconds"] = r1(tap.size() / 2.0 / g_eng.sr);
    t["peak_dbfs"] = r1(L.peakDb);
    t["rms_dbfs"] = r1(L.rmsDb);
    T.rep["output_tap"] = t;
    if (!lb.empty()) {
        write_wav(T.dir + "\\loopback.wav", lb, T.loop.sampleRate);
        Level M = level(lb);
        J o = J::obj();
        o["wav"] = T.dir + "\\loopback.wav";
        o["sample_rate"] = T.loop.sampleRate;
        o["seconds"] = r1(lb.size() / 2.0 / std::max(1, T.loop.sampleRate));
        o["peak_dbfs"] = r1(M.peakDb);
        o["rms_dbfs"] = r1(M.rmsDb);
        T.rep["device_loopback"] = o;
    }
    // the test pattern, played live through the GUI path, analysed like the offline harness
    if (T.patternStart > 0) {
        uint32_t lat = 0;
        for (auto &s : g_slots) lat = std::max(lat, s->I->latency());
        NotesSummary sum;
        double startS = (T.patternStart - T.tapStart) / (double)g_eng.sr;
        analyze_notes(tap, g_eng.sr, startS, T.pattern, lat / (double)g_eng.sr, sum);
        J o = J::obj();
        o["notes"] = sum.notes;
        o["heard"] = sum.heard;
        o["note"] = "all instances play at once; onsets are of the mix, against the largest reported latency";
        o["reported_latency_ms"] = r1(lat * 1000.0 / g_eng.sr);
        o["onset_error_median_ms"] = r1(sum.medianErrMs);
        o["onset_error_std_ms"] = r1(sum.stdErrMs);
        o["jitter_spread_ms"] = r1(sum.maxErrMs - sum.minErrMs);
        T.rep["test_pattern_live"] = o;
    }
    J au = J::obj();
    au["device"] = g_eng.out.deviceName;
    au["sample_rate"] = g_eng.out.sampleRate;
    au["block"] = g_eng.out.block;
    au["wasapi_buffer_frames"] = g_eng.out.bufferFrames;
    au["device_period_ms"] = r1(g_eng.out.periodMs);
    au["underruns"] = (unsigned long long)g_eng.out.underruns;
    au["frames_out"] = (unsigned long long)g_eng.out.framesOut;
    au["wall_s_since_audio_start"] = r1(now_s() - T.audioT0);
    au["dsp_load"] = r3(g_eng.out.load);
    {
        float vol = 0;
        bool mu = false;
        int di = (int)SendMessageW(hDev, CB_GETCURSEL, 0, 0);
        if (endpoint_volume(di >= 0 && di < (int)g_devs.size() ? g_devs[di].id : L"", vol, mu)) {
            au["endpoint_volume"] = r3(vol);
            au["endpoint_muted"] = mu;
        }
    }
    T.rep["audio"] = au;
    J inst = J::arr();
    for (auto &s : g_slots) {
        J o = J::obj();
        o["number"] = s->I->number;
        o["name"] = s->I->name;
        o["latency_samples"] = (unsigned)s->I->latency();
        o["programs"] = (unsigned)s->I->programs().size();
        o["parameters"] = (unsigned)s->I->params(false).size();
        uint64_t calls = s->I->procCalls;
        o["process_calls"] = (unsigned long long)calls;
        o["process_mean_ms"] = calls ? r3(s->I->procNsTotal / 1e6 / calls) : 0.0;
        o["process_max_ms"] = r1(s->I->procNsMax / 1e6);
        if (s->view) {
            ViewRect vr;
            s->view->getSize(&vr);
            o["editor_size"] = std::to_string(vr.getWidth()) + "x" + std::to_string(vr.getHeight());
            o["editor_resizable"] = s->view->canResize() == kResultTrue;
        }
        inst.push(o);
    }
    T.rep["instances"] = inst;
    // close everything, then look for leftover child processes
    for (auto &s : g_slots) for (auto &c : descendants(GetCurrentProcessId())) { (void)s; bool seen = false; for (auto &x : T.children) if (x.pid == c.pid) seen = true; if (!seen) T.children.push_back(c); }
    double t0 = now_s();
    g_eng.stopAudio();
    while (!g_slots.empty()) remove_slot(g_slots.back().get());
    unload_modules();
    std::vector<ProcInfo> left;
    for (int i = 0; i < 100; i++) {
        left = descendants(GetCurrentProcessId());
        if (left.empty()) break;
        Sleep(100);
    }
    J o = J::obj(), seen = J::arr(), lf = J::arr();
    for (auto &c : T.children) seen.push(c.exe + " (" + std::to_string(c.pid) + ")");
    for (auto &c : left) lf.push(c.exe + " (" + std::to_string(c.pid) + ")");
    o["child_processes_seen"] = seen;
    o["left_after_unload"] = lf;
    o["unload_s"] = r3(now_s() - t0);
    T.rep["orphans"] = o;
    flush_log();
    J lg = J::arr();
    for (auto &l : g_logLines) lg.push(l);
    T.rep["log"] = lg;
    std::ofstream(T.dir + "\\selftest.json") << T.rep.dump() << "\n";
    PostMessageW(hMain, WM_CLOSE, 0, 0);
}

void selftest_tick()
{
    double t = now_s() - T.stepT;
    auto next = [&]() { T.step++; T.stepT = now_s(); };
    for (auto &c : descendants(GetCurrentProcessId())) {
        bool seen = false;
        for (auto &x : T.children) if (x.pid == c.pid) seen = true;
        if (!seen) T.children.push_back(c);
    }
    switch (T.step) {
    case 0: {   // load one instance of each plugin, plus a second one of the first (two editors of one plugin),
                // 3 s apart as a person would (see README: BASILISK 16 created while BASILISK SYNTH starts QEMU)
        static size_t loaded = 0;
        std::vector<std::string> order = T.plugins;
        if (!order.empty()) order.push_back(order[0]);
        if (loaded < order.size()) {
            if (t >= 3.0 * loaded) {
                if (Slot *s = add_instance(order[loaded])) { open_editor(s); open_params(s); }
                if (loaded == 0) {
                    start_audio();
                    T.audioT0 = now_s();
                    g_eng.startTap();
                    T.tapStart = tap_frames();
                    std::string err;
                    int di = (int)SendMessageW(hDev, CB_GETCURSEL, 0, 0);
                    T.loopOn = T.loop.start(di >= 0 && di < (int)g_devs.size() ? g_devs[di].id : L"", err);
                    if (!T.loopOn) hlog("loopback: %s", err.c_str());
                    phase_begin("startup/assembly");
                }
                loaded++;
            }
            break;
        }
        next();
        break;
    }
    case 1:   // let the machines assemble, then look at them
        if (t > 12) {
            phase_end();
            shots("assembled");
            // resize the first editor, to check the resizable window
            if (!g_slots.empty() && g_slots[0]->editor) {
                RECT r;
                GetWindowRect(g_slots[0]->editor, &r);
                SetWindowPos(g_slots[0]->editor, NULL, 0, 0, (r.right - r.left) * 3 / 4, (r.bottom - r.top) * 3 / 4, SWP_NOMOVE | SWP_NOZORDER);
            }
            SetForegroundWindow(hMain);
            next();
        }
        break;
    case 2:
        if (t > 1.5) {
            shots("resized");
            if (!g_slots.empty() && g_slots[0]->editor) {
                RECT r;
                GetWindowRect(g_slots[0]->editor, &r);
                SetWindowPos(g_slots[0]->editor, NULL, 0, 0, (r.right - r.left) * 4 / 3, (r.bottom - r.top) * 4 / 3, SWP_NOMOVE | SWP_NOZORDER);
            }
            phase_begin("silence");
            next();
        }
        break;
    case 3:   // on-screen keyboard: each instance in turn, C4 E4 G4 clicked
        if (t > 1.5) {
            phase_end();
            phase_begin("on-screen keyboard");
            SendMessageW(hAllInst, BM_SETCHECK, BST_UNCHECKED, 0);
            next();
        }
        break;
    case 4: {
        // 0.5 s per key; per instance 3 keys
        static const int notes[3] = {60, 64, 67};
        int k = (int)(t / 0.5), inst = k / 3, key = k % 3;
        static int lastK = -1;
        if (inst >= (int)g_slots.size()) {
            if (lastK >= 0) { click_key(notes[lastK % 3], false); lastK = -1; }
            if (t > 0.5 * 3 * g_slots.size() + 1.0) { phase_end(); phase_begin("computer keyboard"); SendMessageW(hAllInst, BM_SETCHECK, BST_CHECKED, 0); update_target(); next(); }
            break;
        }
        if (k != lastK) {
            if (lastK >= 0) click_key(notes[lastK % 3], false);
            SendMessageW(hList, LB_SETCURSEL, inst, 0);
            update_target();
            click_key(notes[key], true);
            lastK = k;
        }
        break;
    }
    case 5: {   // computer keyboard: A D G (C E G), then octave up (X) and K (C)
        static int done = 0;
        struct { double at; WPARAM vk; bool down; } seq[] = {
            {0.0, 'A', true}, {0.4, 'A', false}, {0.5, 'D', true}, {0.9, 'D', false}, {1.0, 'G', true}, {1.4, 'G', false},
            {1.5, 'X', true}, {1.55, 'X', false}, {1.6, 'K', true}, {2.0, 'K', false}, {2.05, 'Z', true}, {2.1, 'Z', false},
            // sustain: hold Space, tap A, release Space later
            {2.3, VK_SPACE, true}, {2.4, 'A', true}, {2.5, 'A', false}, {3.3, VK_SPACE, false}};
        int n = sizeof seq / sizeof seq[0];
        SetForegroundWindow(hMain);
        SetFocus(hMain);
        while (done < n && t >= seq[done].at) { type_key(seq[done].vk, seq[done].down); done++; }
        if (done >= n && t > 4.0) { phase_end(); phase_begin("pitch bend"); next(); }
        break;
    }
    case 6: {   // bend the wheel up, play a note, let it spring back
        static int st = 0;
        if (st == 0) { SendMessageW(hBend, TBM_SETPOS, TRUE, 16383); SendMessageW(hMain, WM_HSCROLL, MAKEWPARAM(TB_THUMBTRACK, 0), (LPARAM)hBend); st = 1; }
        else if (st == 1 && t > 0.1) { click_key(60, true); st = 2; }
        else if (st == 2 && t > 0.6) { click_key(60, false); SendMessageW(hMain, WM_HSCROLL, MAKEWPARAM(TB_ENDTRACK, 0), (LPARAM)hBend); st = 3; }
        else if (st == 3 && t > 0.8) { click_key(60, true); st = 4; }
        else if (st == 4 && t > 1.3) { click_key(60, false); st = 5; }
        else if (st == 5 && t > 2.0) {
            phase_end();
            phase_begin("test pattern");
            T.pattern = test_pattern();
            T.patternStart = tap_frames();
            SendMessageW(GetDlgItem(hMain, ID_PATTERN), BM_CLICK, 0, 0);
            next();
        }
        break;
    }
    case 7:   // the test pattern button, with every instance playing
        if (t > 3 && t < 3.5) shots("playing");
        if (t > T.pattern.length + 2.5) {
            phase_end();
            // automation: a sine on the first visible parameter of instance 1, played for 3 s
            if (!g_slots.empty() && g_slots[0]->params && !g_slots[0]->rows.empty()) {
                Slot *s = g_slots[0].get();
                s->sel = s->rows[0].p.info.id;
                s->hasSel = true;
                params_command(s, ID_SINE, 0);
            }
            phase_begin("automation (sine) + held note");
            click_key(67, true);
            next();
        }
        break;
    case 8:
        if (t > 3.0) {
            click_key(67, false);
            if (!g_slots.empty()) {
                Slot *s = g_slots[0].get();
                auto lv = s->I->laneValues();
                J a = J::obj();
                a["parameter"] = s->rows.empty() ? std::string() : s->rows[0].p.name;
                a["lane_value_now"] = lv.empty() ? -1.0 : r3(lv.begin()->second);
                a["controller_value_now"] = s->rows.empty() || !s->I->ctl ? -1.0 : r3(s->I->ctl->getParamNormalized(s->rows[0].p.info.id));
                T.rep["automation"] = a;
                shots("automation");
                params_command(s, ID_CLEAR, 0);
            }
            next();
        }
        break;
    case 9:
        if (t > 1.5) { phase_end(); selftest_finish(); T.step = 99; }
        break;
    }
}

}  // namespace

int run_gui(const std::vector<std::string> &plugins, const std::string &selftestDir, const std::string &device, int sr, int block)
{
    g_hi = GetModuleHandleW(NULL);
    CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
    INITCOMMONCONTROLSEX ic = {sizeof ic, ICC_BAR_CLASSES | ICC_STANDARD_CLASSES | ICC_WIN95_CLASSES};
    InitCommonControlsEx(&ic);
    NONCLIENTMETRICSW ncm = {sizeof ncm};
    SystemParametersInfoW(SPI_GETNONCLIENTMETRICS, sizeof ncm, &ncm, 0);
    g_font = CreateFontIndirectW(&ncm.lfMessageFont);
    g_bg = GetSysColorBrush(COLOR_WINDOW);
    set_log_sink([](const std::string &s) { logline(s); });

    WNDCLASSW wc = {};
    wc.hInstance = g_hi;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hIcon = LoadIconW(g_hi, MAKEINTRESOURCEW(1));
    wc.hbrBackground = g_bg;
    wc.lpfnWndProc = main_proc;
    wc.lpszClassName = L"BHMain";
    RegisterClassW(&wc);
    wc.lpfnWndProc = editor_proc;
    wc.lpszClassName = L"BHEditor";
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    RegisterClassW(&wc);
    wc.lpfnWndProc = params_proc;
    wc.lpszClassName = L"BHParams";
    wc.hbrBackground = g_bg;
    RegisterClassW(&wc);
    wc.lpfnWndProc = panel_proc;
    wc.lpszClassName = L"BHPanel";
    wc.hbrBackground = GetSysColorBrush(COLOR_WINDOW);
    RegisterClassW(&wc);
    wc.lpfnWndProc = keys_proc;
    wc.lpszClassName = L"BHKeys";
    wc.hbrBackground = NULL;
    RegisterClassW(&wc);

    RECT r = {0, 0, 956, 494};
    DWORD st = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_CLIPCHILDREN;
    AdjustWindowRect(&r, st, FALSE);
    hMain = CreateWindowExW(WS_EX_ACCEPTFILES, L"BHMain", L"BasiliskHost " BH_VERSION " - VST3 test host", st, 120, 120, r.right - r.left,
                            r.bottom - r.top, NULL, NULL, g_hi, NULL);
    build_main();
    // command-line choices of device, rate and block
    if (!device.empty())
        for (size_t i = 0; i < g_devs.size(); i++)
            if (g_devs[i].name.find(device) != std::string::npos) { SendMessageW(hDev, CB_SETCURSEL, i, 0); break; }
    for (int i = 0; i < 4; i++) if (RATES[i] == sr) SendMessageW(hRate, CB_SETCURSEL, i, 0);
    for (int i = 0; i < 6; i++) if (BUFS[i] == block) SendMessageW(hBuf, CB_SETCURSEL, i, 0);
    ShowWindow(hMain, SW_SHOW);
    UpdateWindow(hMain);
    SetTimer(hMain, 1, 33, NULL);
    if (!selftestDir.empty()) {
        T.on = true;
        T.dir = selftestDir;
        CreateDirectoryW(widen(T.dir).c_str(), NULL);
        T.plugins = plugins;
        T.stepT = T.t0 = now_s();
        T.rep["host"] = "BasiliskHost " BH_VERSION;
        T.rep["screenshots"] = J::arr();
        g_tapPath = T.dir + "\\tap.wav";
        SendMessageW(hVol, TBM_SETPOS, TRUE, 50);   // quieter on the speakers during the test; the tap is before the gain
        SetTimer(hMain, 2, 20, NULL);
    } else {
        start_audio();
        for (auto &p : plugins) add_instance(p);
        update_target();
        if (!g_slots.empty()) open_editor(g_slots.back().get());
    }
    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0) > 0) {
        if (handle_key(msg)) continue;
        // keyboard navigation in the parameter windows
        HWND top = GetAncestor(msg.hwnd, GA_ROOT);
        wchar_t cls[32] = {};
        if (top) GetClassNameW(top, cls, 32);
        if (top && !wcscmp(cls, L"BHParams") && IsDialogMessageW(top, &msg)) continue;
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    g_midiIn.close();
    unload_modules();
    return 0;
}
