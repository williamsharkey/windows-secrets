/* srhook.dll - lives inside each of BASILISK SYNTH's sixteen Sound Recorders (synth.exe loads it there with a
   WH_GETMESSAGE hook). Sound Recorder still does all the work - opening, effects, playing, its displays - and
   this only:
     - opens the sound card at the note's rate: XP's AC97 driver has no waveOutSetPlaybackRate, but kmixer will
       resample any PCM rate, so asking waveOutOpen for 2x the file's rate plays the same samples an octave up
     - shapes each note with the per-handle waveOut volume (attack, decay, sustain, release)
     - answers the file dialogs and message boxes when synth.exe drives the menus (no dialog ever shows)
     - runs synth.exe's requests on Sound Recorder's own thread, so the program never sees anything unusual
   Build (in XP): tcc -shared -o srhook.dll srhook.c -luser32 */
#include <windows.h>
#include "mm.h"
#include "synthshm.h"

#define WAVE_FORMAT_QUERY 1
#define TBM_GETPOS (WM_USER)
#define TBM_GETRANGEMAX (WM_USER + 2)
#define TBM_SETPOS (WM_USER + 5)
#define TB_THUMBPOSITION 4
#define TB_ENDTRACK 8

typedef struct {
    DWORD lStructSize; HWND hwndOwner; HINSTANCE hInstance; LPCWSTR lpstrFilter; LPWSTR lpstrCustomFilter;
    DWORD nMaxCustFilter, nFilterIndex; LPWSTR lpstrFile; DWORD nMaxFile; LPWSTR lpstrFileTitle; DWORD nMaxFileTitle;
    LPCWSTR lpstrInitialDir, lpstrTitle; DWORD Flags; WORD nFileOffset, nFileExtension;
} OFNW;

typedef MMRESULT (WINAPI *P_OPEN)(LPHWAVEOUT, UINT, LPCWAVEFORMATEX, DWORD_PTR, DWORD_PTR, DWORD);
typedef MMRESULT (WINAPI *P_CLOSE)(HWAVEOUT);
typedef MMRESULT (WINAPI *P_SETVOL)(HWAVEOUT, DWORD);
typedef BOOL (WINAPI *P_OFN)(OFNW *);
typedef int (WINAPI *P_MB)(HWND, LPCWSTR, LPCWSTR, UINT);

static HINSTANCE me;
static int is_rec, slot = -1;
static SyShm *shm;
static SySlot *S;
static UINT msg_op, msg_done;
static P_OPEN real_open;
static P_CLOSE real_close;
static P_SETVOL setvol;
static P_OFN real_ofn, real_sfn;
static P_MB real_mb;
static CRITICAL_SECTION cs;
static HWAVEOUT cur;          /* the open sound card handle, while playing */
static DWORD t0, t_rel;       /* note start; release start (0 while held) */
static LONG lvl_rel;          /* level when the release began */
static int rel_ms, stopping;
static volatile int cut, pending;

static void done(int op, LONG arg)
{
    if (shm && shm->synth_hwnd) PostMessageA((HWND)shm->synth_hwnd, msg_done, slot, op == SYE_OPEN ? (op | (arg << 8)) : op);
}

/* the envelope at time now, 0..65535 */
static LONG env_level(DWORD now)
{
    LONG a = shm->env_a, d = shm->env_d, s = shm->env_s * 65535 / 100, t = (LONG)(now - t0), l;
    if (s > 65535) s = 65535;
    if (s < 0) s = 0;
    if (t < a) l = (LONG)((double)t * 65535 / a);
    else if (t < a + d) l = 65535 - (LONG)((double)(t - a) * (65535 - s) / d);
    else l = s;
    if (t_rel) {
        LONG r = (LONG)(now - t_rel);
        l = r >= rel_ms ? 0 : (LONG)((double)lvl_rel * (rel_ms - r) / rel_ms);
    }
    return l;
}

static void apply_vol(LONG l)
{
    DWORD v = (DWORD)((double)l * S->vol / 65535);
    if (v > 65535) v = 65535;
    S->level = l;
    if (cur && setvol) setvol(cur, v | (v << 16));
}

static DWORD WINAPI env_thread(LPVOID p)
{
    for (;;) {
        Sleep(5);
        EnterCriticalSection(&cs);
        if (cur && !stopping) {
            DWORD now = GetTickCount();
            LONG l;
            if (!t_rel && (!S->gate || cut)) {     /* the note was let go (or cut) */
                lvl_rel = S->level;
                rel_ms = cut ? 5 : (shm->env_r > 0 ? shm->env_r : 1);
                t_rel = now;
            }
            l = env_level(now);
            apply_vol(l);
            if (t_rel && l == 0) {
                stopping = 1;
                PostMessageW((HWND)S->hwnd, WM_COMMAND, MAKEWPARAM(SR_STOP, BN_CLICKED),
                             (LPARAM)GetDlgItem((HWND)S->hwnd, SR_STOP));
            }
        }
        LeaveCriticalSection(&cs);
    }
    return 0;
}

static MMRESULT WINAPI my_open(LPHWAVEOUT ph, UINT dev, LPCWAVEFORMATEX f, DWORD_PTR cb, DWORD_PTR inst, DWORD fl)
{
    WAVEFORMATEX g;
    MMRESULT r;
    if (!f || (fl & WAVE_FORMAT_QUERY) || !S || f->wFormatTag != 1)
        return real_open(ph, dev, f, cb, inst, fl);
    if (!pending) { S->rate = 0; S->vol = 65535; S->gate = 1; }    /* someone clicked Play in XP: as it is, to the end */
    pending = 0;
    if (S->rate <= 0) {
        r = real_open(ph, dev, f, cb, inst, fl);
        goto opened;
    }
    g = *f;
    g.cbSize = 0;
    g.nSamplesPerSec = S->rate;
    g.nAvgBytesPerSec = S->rate * g.nBlockAlign;
    r = real_open(ph, dev, &g, cb, inst, fl);
    if (r) r = real_open(ph, dev, f, cb, inst, fl);   /* a rate the card refuses: play it as it is */
opened:
    if (!r) {
        EnterCriticalSection(&cs);
        cur = *ph;
        t0 = GetTickCount();
        t_rel = 0;
        stopping = 0;
        S->t_open = t0;
        S->opens++;
        S->playing = 1;
        apply_vol(env_level(t0));
        LeaveCriticalSection(&cs);
        done(SYE_OPEN, (LONG)(t0 - S->t_req));
    }
    return r;
}

static MMRESULT WINAPI my_close(HWAVEOUT h)
{
    int was;
    EnterCriticalSection(&cs);
    was = cur == h;
    if (was) { cur = 0; S->playing = 0; S->level = 0; }
    LeaveCriticalSection(&cs);
    if (was) done(SYE_END, 0);
    return real_close(h);
}

/* the file dialogs: when synth.exe has named a file, answer at once with it and show nothing */
static BOOL answer_file(OFNW *o)
{
    int n, i;
    if (!S || !S->file[0] || !o->lpstrFile) return -1;
    n = lstrlenW(S->file);
    if ((DWORD)n >= o->nMaxFile) return -1;
    lstrcpyW(o->lpstrFile, S->file);
    S->file[0] = 0;
    for (i = n; i > 0 && o->lpstrFile[i - 1] != '\\'; i--);
    o->nFileOffset = (WORD)i;
    for (i = n; i > 0 && o->lpstrFile[i - 1] != '.'; i--);
    o->nFileExtension = (WORD)(i > 0 ? i : n);
    if (o->lpstrFileTitle && o->nMaxFileTitle > (DWORD)(n - o->nFileOffset)) lstrcpyW(o->lpstrFileTitle, o->lpstrFile + o->nFileOffset);
    return TRUE;
}
static BOOL WINAPI my_ofn(OFNW *o) { BOOL r = answer_file(o); return r == -1 ? real_ofn(o) : r; }
static BOOL WINAPI my_sfn(OFNW *o) { BOOL r = answer_file(o); return r == -1 ? real_sfn(o) : r; }

static int WINAPI my_mb(HWND h, LPCWSTR text, LPCWSTR cap, UINT type)
{
    if (S && S->answer) {
        switch (type & 0xF) {
        case MB_YESNOCANCEL: return IDNO;      /* "save changes?" - never: the next file replaces it */
        case MB_YESNO: return IDYES;           /* "delete before/after the position?" */
        case MB_OKCANCEL: return IDOK;
        default: return IDOK;                  /* a refusal ("cannot ...") just ends that step */
        }
    }
    return real_mb(h, text, cap, type);
}

static void patch(const char *dll, const char *fn, void *nf, void **orig)
{
    BYTE *b = (BYTE *)GetModuleHandleA(NULL);
    IMAGE_NT_HEADERS *nt = (IMAGE_NT_HEADERS *)(b + ((IMAGE_DOS_HEADER *)b)->e_lfanew);
    IMAGE_DATA_DIRECTORY *dd = &nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
    IMAGE_IMPORT_DESCRIPTOR *d = (IMAGE_IMPORT_DESCRIPTOR *)(b + dd->VirtualAddress);
    HMODULE m = GetModuleHandleA(dll);
    FARPROC want = m ? GetProcAddress(m, fn) : NULL;
    if (!want) return;
    for (; d->Name; d++) {
        IMAGE_THUNK_DATA *t;
        if (lstrcmpiA((char *)(b + d->Name), dll)) continue;
        for (t = (IMAGE_THUNK_DATA *)(b + d->FirstThunk); t->u1.Function; t++) {
            if ((FARPROC)t->u1.Function == want) {
                DWORD o;
                VirtualProtect(&t->u1.Function, sizeof(DWORD), PAGE_READWRITE, &o);
                *orig = (void *)t->u1.Function;
                t->u1.Function = (DWORD)nf;
                VirtualProtect(&t->u1.Function, sizeof(DWORD), o, &o);
            }
        }
    }
}


/* ---------------------------------------------------------------- the assembly, done from inside: each Sound
   Recorder moves its own window and parts on its own thread, so sixteen of them animate side by side */
static const int kid_ids[] = {SR_PLAY, SR_STOP, -1, 302, SR_POS, SR_WAVE, 304, 305, SR_LEN, SR_TRACK, SR_REW, SR_FWD, SR_REC};
#define NK 13
static HWND kid[NK];
static RECT k0[NK], w0, w1;
static DWORD a_t0, d_t0;
static int a_dur;
#define T_FLY 0xB51
#define T_DROP 0xB52

static void find_kids(void)
{
    HWND w = (HWND)S->hwnd, c = NULL;
    int k;
    for (k = 0; k < NK; k++) {
        if (kid_ids[k] == -1) {
            while ((c = FindWindowExA(w, c, "shadowframe", NULL))) if (GetDlgCtrlID(c) != 304) { kid[k] = c; break; }
        } else kid[k] = GetDlgItem(w, kid_ids[k]);
    }
}
static RECT in_parent(HWND h)
{
    RECT r;
    POINT a, b;
    GetWindowRect(h, &r);
    a.x = r.left; a.y = r.top; b.x = r.right; b.y = r.bottom;
    ScreenToClient(GetParent(h), &a); ScreenToClient(GetParent(h), &b);
    SetRect(&r, a.x, a.y, b.x, b.y);
    return r;
}
static double ease(double x) { return x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) * (-2 * x + 2) * (-2 * x + 2) / 2; }
static int lerp(int a, int b, double x) { return a + (int)((b - a) * x + (b > a ? 0.5 : -0.5)); }

static void CALLBACK fly_tick(HWND w, UINT m, UINT_PTR id, DWORD now)
{
    double x = ease((double)(GetTickCount() - a_t0) / a_dur);
    HDWP dw;
    int k;
    SetWindowPos(w, NULL, lerp(w0.left, w1.left, x), lerp(w0.top, w1.top, x), lerp(w0.right - w0.left, w1.right - w1.left, x),
                 lerp(w0.bottom - w0.top, w1.bottom - w1.top, x), SWP_NOZORDER | SWP_NOACTIVATE);
    dw = BeginDeferWindowPos(10);
    for (k = 0; k < 10; k++) {
        /* the parts lag the panel a little, one after another, so the row assembles left to right */
        double y = ease(((double)(GetTickCount() - a_t0) - k * 22) / (a_dur - 10 * 22));
        RECT *b = &shm->kid_final[k];
        if (kid[k]) dw = DeferWindowPos(dw, kid[k], NULL, lerp(k0[k].left, b->left, y), lerp(k0[k].top, b->top, y),
                                        lerp(k0[k].right - k0[k].left, b->right - b->left, y), lerp(k0[k].bottom - k0[k].top, b->bottom - b->top, y),
                                        SWP_NOZORDER | SWP_NOACTIVATE);
    }
    EndDeferWindowPos(dw);
    RedrawWindow(w, NULL, NULL, RDW_UPDATENOW | RDW_ALLCHILDREN);   /* every part painted before the next step */
    if (x >= 1) {
        KillTimer(w, T_FLY);
        /* landed: every part painted once more, whole (a label moved mid-repaint can be left blank) */
        RedrawWindow(w, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW);
        done(SYO_FLY, 0);
    }
}

static void CALLBACK drop_tick(HWND w, UINT m, UINT_PTR id, DWORD now)
{
    int k, all = 1;
    for (k = 10; k < 13; k++) {
        double y = (double)(GetTickCount() - d_t0 - (12 - k) * 70) / 170;   /* Record first, then >>, then << */
        if (!kid[k] || !IsWindowVisible(kid[k])) continue;
        all = 0;
        if (y < 0) continue;
        if (y >= 1) { ShowWindow(kid[k], SW_HIDE); continue; }
        SetWindowPos(kid[k], NULL, k0[k].left, k0[k].top + (int)(y * y * 46), 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
    }
    UpdateWindow(w);
    if (all) { KillTimer(w, T_DROP); done(SYO_DROP, 0); }
}

static void strip(void)
{
    HWND w = (HWND)S->hwnd, p = (HWND)shm->synth_hwnd;
    RECT cr;
    POINT c = {0, 0};
    LONG st = GetWindowLongW(w, GWL_STYLE);
    GetClientRect(w, &cr);
    ClientToScreen(w, &c);
    st &= ~(WS_POPUP | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME);
    st |= WS_CHILD | WS_CLIPSIBLINGS;
    SetWindowLongW(w, GWL_STYLE, st);
    SetWindowLongW(w, GWL_EXSTYLE, GetWindowLongW(w, GWL_EXSTYLE) & ~(WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE | WS_EX_APPWINDOW | WS_EX_CLIENTEDGE));
    SetParent(w, p);
    ScreenToClient(p, &c);
    SetWindowPos(w, HWND_TOP, c.x, c.y, cr.right, cr.bottom, SWP_NOACTIVATE | SWP_FRAMECHANGED);
    UpdateWindow(w);
}

static void seek(LONG permille)
{
    HWND w = (HWND)S->hwnd, tb = GetDlgItem(w, SR_TRACK);
    LONG mx = (LONG)SendMessageW(tb, TBM_GETRANGEMAX, 0, 0), p = (LONG)((double)mx * permille / 1000);
    SendMessageW(tb, TBM_SETPOS, TRUE, p);
    SendMessageW(w, WM_HSCROLL, MAKEWPARAM(TB_THUMBPOSITION, p), (LPARAM)tb);
    SendMessageW(w, WM_HSCROLL, MAKEWPARAM(TB_ENDTRACK, 0), (LPARAM)tb);
}

static void cmd(int id)
{
    HWND w = (HWND)S->hwnd;
    SendMessageW(w, WM_COMMAND, MAKEWPARAM(id, BN_CLICKED), (LPARAM)GetDlgItem(w, id));
}

static void run_op(int op, LONG arg)
{
    switch (op) {
    case SYO_PLAY:
        cut = 0;
        if (S->playing) { stopping = 1; cmd(SR_STOP); }
        cmd(SR_REW);
        S->t_req = GetTickCount();
        pending = 1;          /* srhook's waveOutOpen takes the note's rate and volume (and clears this) */
        cmd(SR_PLAY);
        break;
    case SYO_OFF: break;                  /* gate is already 0: the envelope thread releases */
    case SYO_CUT: cut = 1; break;
    case SYO_STOP: if (S->playing) cmd(SR_STOP); break;
    case SYO_CMD:
        S->answer = 1;
        cmd((int)arg);
        S->answer = 0;
        break;
    case SYO_SEEK: seek(arg); break;
    case SYO_NOMENU: SetMenu((HWND)S->hwnd, NULL); UpdateWindow((HWND)S->hwnd); break;
    case SYO_STRIP: strip(); break;
    case SYO_DROP: {
        int k;
        if (!kid[0]) find_kids();
        for (k = 10; k < 13; k++) if (kid[k]) k0[k] = in_parent(kid[k]);
        d_t0 = GetTickCount();
        SetTimer((HWND)S->hwnd, T_DROP, 25, drop_tick);
        return;
    }
    case SYO_FLY: {
        int k;
        if (!kid[0]) find_kids();
        for (k = 0; k < 10; k++) if (kid[k]) k0[k] = in_parent(kid[k]);
        w0 = in_parent((HWND)S->hwnd);
        SetRect(&w1, S->fly[0], S->fly[1], S->fly[0] + S->fly[2], S->fly[1] + S->fly[3]);
        a_dur = arg > 50 ? arg : 50;
        a_t0 = GetTickCount();
        SetTimer((HWND)S->hwnd, T_FLY, 25, fly_tick);   /* ~40 fps asked; each frame drawn whole */
        return;
    }
    }
    if (op != SYO_PLAY && op != SYO_OFF && op != SYO_CUT) done(op, 0);
}

__declspec(dllexport) LRESULT CALLBACK GetMsgProc(int code, WPARAM wp, LPARAM lp)
{
    MSG *m = (MSG *)lp;
    if (code == HC_ACTION && wp == PM_REMOVE && S && m->message == msg_op) {
        int op = (int)m->wParam;
        LONG arg = (LONG)m->lParam;
        m->message = WM_NULL;
        run_op(op, arg);
    }
    return CallNextHookEx(NULL, code, wp, lp);
}

static void attach(void)
{
    char path[MAX_PATH];
    HANDLE map;
    int i;
    GetModuleFileNameA(NULL, path, sizeof path);
    CharLowerA(path);
    if (!strstr(path, "sndrec32")) return;
    map = OpenFileMappingA(FILE_MAP_ALL_ACCESS, FALSE, SY_SHM);
    if (!map) return;
    shm = (SyShm *)MapViewOfFile(map, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SyShm));
    if (!shm || shm->magic != SY_MAGIC) return;
    for (i = 0; i < SY_NREC; i++) if ((DWORD)shm->s[i].pid == GetCurrentProcessId()) slot = i;
    if (slot < 0) return;
    S = &shm->s[slot];
    msg_op = RegisterWindowMessageA(SY_MSG);
    msg_done = RegisterWindowMessageA(SY_DONE);
    InitializeCriticalSection(&cs);
    LoadLibraryA("winmm.dll");
    LoadLibraryA("comdlg32.dll");
    setvol = (P_SETVOL)GetProcAddress(GetModuleHandleA("winmm.dll"), "waveOutSetVolume");
    patch("winmm.dll", "waveOutOpen", (void *)my_open, (void **)&real_open);
    patch("winmm.dll", "waveOutClose", (void *)my_close, (void **)&real_close);
    patch("comdlg32.dll", "GetOpenFileNameW", (void *)my_ofn, (void **)&real_ofn);
    patch("comdlg32.dll", "GetSaveFileNameW", (void *)my_sfn, (void **)&real_sfn);
    patch("user32.dll", "MessageBoxW", (void *)my_mb, (void **)&real_mb);
    is_rec = 1;
    CreateThread(NULL, 0, env_thread, NULL, 0, NULL);
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD why, LPVOID r)
{
    if (why == DLL_PROCESS_ATTACH) {
        me = h;
        DisableThreadLibraryCalls(h);
        attach();
    }
    return TRUE;
}
