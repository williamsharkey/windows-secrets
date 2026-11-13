/* vizproto - a throwaway prototype for design/VISUALIZERS.md. Not part of the product.

   Runs inside the BASILISK SYNTH XP machine, beside synth.exe. Three stages, each a real Windows part:
     vizproto bars  X Y W H     16 vertical progress bars (msctls_progress32), one per Sound Recorder; height = the
                                 recorder's envelope level, read from synth.exe's shared memory (no audio work at all)
     vizproto wmp   X Y W H [effect] [preset]
                                 a Windows Media Player visualization (IWMPEffects, from WMP's own registry list)
                                 rendered into our window with TimedLevel data made from the same 16 levels. WMP does
                                 not play anything.
     vizproto saver X Y W H scr  a screen saver in preview mode (scr /p <hwnd>) inside our window
     vizproto list               write the registered WMP effects to C:\vizproto.txt
     vizproto bigwave X Y W H    move strip 1 to the rect and stretch its wave control (does the wave scale?)
   The process runs at IDLE_PRIORITY_CLASS. A governor reads the system idle time twice a second: below 25 % idle
   it halves the frame rate, below 10 % it stops drawing (saver: suspends the saver's thread) until idle is back.

   Build (Linux): i686-w64-mingw32-gcc -O2 -o vizproto.exe vizproto.c -mwindows -lole32 -loleaut32 -lcomctl32 -luuid
*/
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <ole2.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

/* --------------------------------------------------------------- synth.exe's shared memory (guest/synthshm.h) */
#define SY_NREC 16
typedef struct {
    volatile LONG pid, hwnd, rate, vol, gate, level, playing, answer, t_req, t_open, opens, fly[4], t_post, cut;
    WCHAR pcmfile[260], file[260];
} SySlot;
typedef struct {
    LONG magic, synth_hwnd;
    volatile LONG env_a, env_d, env_s, env_r;
    volatile LONG pad[10];
    RECT kid_final[16];
    SySlot s[SY_NREC];
} SyShm;
static SyShm *shm;

/* --------------------------------------------------------------- WMP effects (effects.h, WMP 9 SDK) */
typedef struct {
    unsigned char frequency[2][1024];
    unsigned char waveform[2][1024];
    LONG state;          /* 0 stop, 1 pause, 2 play */
    LONGLONG timeStamp;  /* 100 ns units */
} TimedLevel;
typedef struct IWMPEffects IWMPEffects;
typedef struct {
    HRESULT (STDMETHODCALLTYPE *QueryInterface)(IWMPEffects *, REFIID, void **);
    ULONG (STDMETHODCALLTYPE *AddRef)(IWMPEffects *);
    ULONG (STDMETHODCALLTYPE *Release)(IWMPEffects *);
    HRESULT (STDMETHODCALLTYPE *Render)(IWMPEffects *, TimedLevel *, HDC, RECT *);
    HRESULT (STDMETHODCALLTYPE *MediaInfo)(IWMPEffects *, LONG, LONG, BSTR);
    HRESULT (STDMETHODCALLTYPE *GetCapabilities)(IWMPEffects *, DWORD *);
    HRESULT (STDMETHODCALLTYPE *GetTitle)(IWMPEffects *, BSTR *);
    HRESULT (STDMETHODCALLTYPE *GetPresetTitle)(IWMPEffects *, LONG, BSTR *);
    HRESULT (STDMETHODCALLTYPE *GetPresetCount)(IWMPEffects *, LONG *);
    HRESULT (STDMETHODCALLTYPE *SetCurrentPreset)(IWMPEffects *, LONG);
    HRESULT (STDMETHODCALLTYPE *GetCurrentPreset)(IWMPEffects *, LONG *);
    HRESULT (STDMETHODCALLTYPE *DisplayPropertyPage)(IWMPEffects *, HWND);
    HRESULT (STDMETHODCALLTYPE *GoFullscreen)(IWMPEffects *, BOOL);
    HRESULT (STDMETHODCALLTYPE *RenderFullScreen)(IWMPEffects *, TimedLevel *);
} IWMPEffectsVtbl;
struct IWMPEffects { IWMPEffectsVtbl *v; };
static const IID IID_IWMPEffects_ = {0xD3984C13, 0xC3CB, 0x48e2, {0x8B, 0xE5, 0x51, 0x68, 0x34, 0x0B, 0x4F, 0x35}};

#define EFFKEY "Software\\Microsoft\\MediaPlayer\\Objects\\Effects"
static int effect_clsid(int want, char *name, int nlen, CLSID *out)
{
    HKEY k, p;
    char sub[128], path[300], cls[64];
    WCHAR w[64];
    DWORD n, i, cb;
    if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, EFFKEY, 0, KEY_READ, &k)) return 0;
    for (i = 0; n = sizeof sub, RegEnumKeyExA(k, i, sub, &n, 0, 0, 0, 0) == 0; i++) {
        sprintf(path, EFFKEY "\\%s\\Properties", sub);
        if (RegOpenKeyExA(HKEY_LOCAL_MACHINE, path, 0, KEY_READ, &p)) continue;
        cb = sizeof cls;
        if (RegQueryValueExA(p, "classid", 0, 0, (BYTE *)cls, &cb) == 0 && (int)i == want) {
            lstrcpynA(name, sub, nlen);
            MultiByteToWideChar(CP_ACP, 0, cls, -1, w, 64);
            RegCloseKey(p); RegCloseKey(k);
            return CLSIDFromString(w, out) == S_OK;
        }
        RegCloseKey(p);
    }
    RegCloseKey(k);
    return 0;
}

/* --------------------------------------------------------------- state */
static HWND win, bars[SY_NREC];
static int mode, frame_ms = 50, paused;
static IWMPEffects *fx;
static TimedLevel tl;
static HBITMAP back;
static HDC back_dc;
static RECT area;
static DWORD saver_tid;
static LONGLONG t_start;
static FILE *vlog;

static double level_of(int i) { return shm && shm->magic ? shm->s[i].level / 65535.0 : 0; }

static void make_timed_level(void)
{
    /* the prototype's stand-in for the host analysis: each recorder's envelope level drives a band of the
       spectrum and the amplitude of a waveform. The product computes these from the real audio, host side. */
    int ch, i;
    double sum = 0, ph = (GetTickCount() % 100000) / 1000.0;
    for (i = 0; i < SY_NREC; i++) sum += level_of(i);
    if (sum > 1) sum = 1;
    for (ch = 0; ch < 2; ch++)
        for (i = 0; i < 1024; i++) {
            int band = i * SY_NREC / 1024;
            double f = level_of(band) * (1.0 - i / 1400.0) * 255.0;
            double wv = sum * sin(i * 0.05 + ph * 9 + ch) * (0.6 + 0.4 * sin(i * 0.007 + ph));
            tl.frequency[ch][i] = (unsigned char)(f < 0 ? 0 : f > 255 ? 255 : f);
            tl.waveform[ch][i] = (unsigned char)(128 + 127 * wv);
        }
    tl.state = 2;
    tl.timeStamp = (LONGLONG)(GetTickCount() - (DWORD)t_start) * 10000;
}

/* --------------------------------------------------------------- the governor */
typedef BOOL (WINAPI *GST)(FILETIME *, FILETIME *, FILETIME *);
static GST get_sys_times;
static ULONGLONG ft(FILETIME f) { return ((ULONGLONG)f.dwHighDateTime << 32) | f.dwLowDateTime; }
static void CALLBACK governor(HWND h, UINT m, UINT_PTR id, DWORD now)
{
    static ULONGLONG li, lk, lu;
    FILETIME a, b, c;
    ULONGLONG i, k, u, tot;
    int idle, want;
    if (!get_sys_times || !get_sys_times(&a, &b, &c)) return;
    i = ft(a); k = ft(b); u = ft(c);          /* kernel time includes idle time */
    tot = (k - lk) + (u - lu);
    idle = tot ? (int)(100 * (i - li) / tot) : 100;
    li = i; lk = k; lu = u;
    want = idle < 10 ? 2 : idle < 25 ? 1 : 0;   /* 0 full rate, 1 half rate, 2 stopped */
    if (mode == 3 && saver_tid) {                /* a screen saver: suspend its thread, resume it later */
        HANDLE t = OpenThread(THREAD_SUSPEND_RESUME, FALSE, saver_tid);
        if (t) {
            if (want == 2 && !paused) SuspendThread(t);
            if (want < 2 && paused) ResumeThread(t);
            CloseHandle(t);
        }
    }
    paused = want == 2;
    frame_ms = want == 1 ? 100 : 50;
    if (vlog) { fprintf(vlog, "%lu idle %d%% level %d\n", now, idle, want); fflush(vlog); }
}

/* --------------------------------------------------------------- drawing */
static void CALLBACK frame(HWND h, UINT m, UINT_PTR id, DWORD now)
{
    static DWORD last;
    int i;
    if (paused || now - last < (DWORD)frame_ms - 5) return;
    last = now;
    if (mode == 1) {
        for (i = 0; i < SY_NREC; i++) SendMessageA(bars[i], PBM_SETPOS, (WPARAM)(level_of(i) * 100), 0);
    } else if (mode == 2 && fx) {
        HDC dc = GetDC(win);
        make_timed_level();
        fx->v->Render(fx, &tl, back_dc, &area);
        BitBlt(dc, 0, 0, area.right, area.bottom, back_dc, 0, 0, SRCCOPY);
        ReleaseDC(win, dc);
    }
}

static LRESULT CALLBACK wnd(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_DESTROY) PostQuitMessage(0);
    if (m == WM_ERASEBKGND && mode == 2) return 1;
    return DefWindowProcA(h, m, wp, lp);
}

int WINAPI WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show)
{
    char m[16] = "", arg5[260] = "";
    int x = 0, y = 0, w = 400, hh = 300, preset = 0, i;
    WNDCLASSA wc;
    MSG msg;
    HANDLE map;
    INITCOMMONCONTROLSEX icc = {sizeof icc, ICC_PROGRESS_CLASS};
    sscanf(cmd, "%15s %d %d %d %d %259s %d", m, &x, &y, &w, &hh, arg5, &preset);
    mode = !strcmp(m, "bars") ? 1 : !strcmp(m, "wmp") ? 2 : !strcmp(m, "saver") ? 3 : !strcmp(m, "list") ? 4 : !strcmp(m, "bigwave") ? 5 : 0;
    SetPriorityClass(GetCurrentProcess(), IDLE_PRIORITY_CLASS);
    vlog = fopen("C:\\vizproto.txt", "a");
    get_sys_times = (GST)GetProcAddress(GetModuleHandleA("kernel32.dll"), "GetSystemTimes");
    InitCommonControlsEx(&icc);
    CoInitialize(NULL);
    map = OpenFileMappingA(FILE_MAP_READ, FALSE, "BasiliskSynthShm1");
    if (map) shm = (SyShm *)MapViewOfFile(map, FILE_MAP_READ, 0, 0, 0);
    if (vlog) fprintf(vlog, "start %s shm=%p\n", cmd, (void *)shm);
    if (mode == 4) {
        char name[128];
        CLSID c;
        for (i = 0; i < 32; i++) if (effect_clsid(i, name, sizeof name, &c) && vlog) fprintf(vlog, "effect %d %s\n", i, name);
        return 0;
    }
    if (mode == 5) {
        HWND top = FindWindowA("BasiliskSynth", NULL), wave = NULL, strip;
        HWND c = NULL;
        while (top && (c = FindWindowExA(top, c, NULL, NULL)))
            if ((wave = GetDlgItem(c, 203))) break;
        if (!wave) { if (vlog) fprintf(vlog, "bigwave: no wave\n"); return 1; }
        strip = GetParent(wave);
        SetWindowPos(strip, HWND_TOP, x, y, w, hh, SWP_NOACTIVATE);
        SetWindowPos(wave, NULL, 4, 4, w - 8, hh - 8, SWP_NOZORDER | SWP_NOACTIVATE);
        InvalidateRect(strip, NULL, TRUE);
        if (vlog) fprintf(vlog, "bigwave: strip %p wave %p\n", (void *)strip, (void *)wave);
        return 0;
    }
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = wnd; wc.hInstance = hi; wc.lpszClassName = "VizProto";
    wc.hbrBackground = GetSysColorBrush(COLOR_BTNFACE); wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    RegisterClassA(&wc);
    win = CreateWindowExA(WS_EX_TOOLWINDOW | WS_EX_TOPMOST, "VizProto", "vizproto", WS_POPUP | WS_BORDER | WS_VISIBLE,
                          x, y, w, hh, NULL, NULL, hi, NULL);
    GetClientRect(win, &area);
    t_start = GetTickCount();
    if (mode == 1) {
        int bw = area.right / SY_NREC;
        for (i = 0; i < SY_NREC; i++) {
            bars[i] = CreateWindowExA(0, PROGRESS_CLASSA, "", WS_CHILD | WS_VISIBLE | PBS_VERTICAL,
                                      i * bw + 2, 2, bw - 4, area.bottom - 4, win, NULL, hi, NULL);
            SendMessageA(bars[i], PBM_SETRANGE32, 0, 100);
        }
    } else if (mode == 2) {
        CLSID c;
        char name[128] = "?";
        HDC dc = GetDC(win);
        back_dc = CreateCompatibleDC(dc);
        back = CreateCompatibleBitmap(dc, area.right, area.bottom);
        SelectObject(back_dc, back);
        ReleaseDC(win, dc);
        if (effect_clsid(atoi(arg5), name, sizeof name, &c) &&
            CoCreateInstance(&c, NULL, CLSCTX_INPROC_SERVER, &IID_IWMPEffects_, (void **)&fx) == S_OK) {
            LONG n = 0;
            fx->v->GetPresetCount(fx, &n);
            if (preset < n) fx->v->SetCurrentPreset(fx, preset);
            if (vlog) fprintf(vlog, "effect %s presets %ld\n", name, n);
        } else if (vlog) fprintf(vlog, "effect %s: no IWMPEffects\n", arg5);
    } else if (mode == 3) {
        char cl[400];
        STARTUPINFOA si;
        PROCESS_INFORMATION pi;
        memset(&si, 0, sizeof si); si.cb = sizeof si;
        sprintf(cl, "%s /p %lu", arg5, (unsigned long)(UINT_PTR)win);
        if (CreateProcessA(NULL, cl, NULL, NULL, FALSE, IDLE_PRIORITY_CLASS, NULL, NULL, &si, &pi)) {
            saver_tid = pi.dwThreadId;
            CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
        }
    }
    SetTimer(win, 1, 25, frame);
    SetTimer(win, 2, 500, governor);
    while (GetMessageA(&msg, NULL, 0, 0) > 0) { TranslateMessage(&msg); DispatchMessageA(&msg); }
    if (fx) fx->v->Release(fx);
    return 0;
}
