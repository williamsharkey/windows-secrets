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
#include <stdlib.h>
#include "mm.h"
#include "synthshm.h"

#define WAVE_FORMAT_QUERY 1
#define WHDR_DONE_ 1
#define TIME_BYTES_ 4
#define TBM_GETPOS (WM_USER)
#define TBM_GETRANGEMAX (WM_USER + 2)
#define TBM_SETPOS (WM_USER + 5)
#define TB_THUMBPOSITION 4
#define TB_ENDTRACK 8
#define TB_THUMBTRACK 5

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
static volatile int pending;

/* the fast play path: this Sound Recorder's own sound (the file it opened, which it saved itself) on a card handle it
   keeps open, started the instant synth.exe signals - Sound Recorder's Play takes 30-300 ms before it opens the card */
typedef MMRESULT (WINAPI *P_HDR)(HWAVEOUT, LPWAVEHDR, UINT);
typedef MMRESULT (WINAPI *P_RESET)(HWAVEOUT);
typedef struct { UINT wType; union { DWORD ms, sample, cb, ticks; } u; DWORD pad[2]; } MMT;
typedef MMRESULT (WINAPI *P_POS)(HWAVEOUT, MMT *, UINT);
static P_HDR w_prep, w_unprep, w_write;
static P_RESET w_reset;
static P_POS w_pos;
static char *pcm;
static DWORD pcm_len;
static WAVEFORMATEX pcm_fmt;
static HWAVEOUT fh;           /* the fast path's handle, kept open between notes */
static DWORD fh_rate;
static WAVEHDR fhdr;
static HANDLE note_ev;

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
            if (!t_rel && (!S->gate || S->cut)) {     /* the note was let go (or cut) */
                lvl_rel = S->level;
                rel_ms = S->cut ? 5 : (shm->env_r > 0 ? shm->env_r : 1);
                t_rel = now;
            }
            l = env_level(now);
            apply_vol(l);
            if (cur == fh && fh && (fhdr.dwFlags & WHDR_DONE_)) {        /* the fast path's sound ran out */
                cur = 0; S->playing = 0; S->level = 0;
                done(SYE_END, 0);
            } else if (t_rel && l == 0) {
                stopping = 1;
                if (cur == fh && fh) { w_reset(fh); cur = 0; S->playing = 0; S->level = 0; done(SYE_END, 0); }
                else PostMessageW((HWND)S->hwnd, WM_COMMAND, MAKEWPARAM(SR_STOP, BN_CLICKED),
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

static int glide_only;      /* SYO_GLIDE: the window moves whole; its parts stay put inside it */
static int morphing;        /* a SYO_MORPH is still under way */
static void finish_morph(HWND w)
{
    int k;
    SetWindowPos(w, NULL, w1.left, w1.top, w1.right - w1.left, w1.bottom - w1.top, SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOREDRAW);
    for (k = 0; k < 10; k++) {
        RECT *b = &shm->kid_final[k];
        if (kid[k]) SetWindowPos(kid[k], NULL, b->left, b->top, b->right - b->left, b->bottom - b->top, SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOREDRAW);
    }
    RedrawWindow(w, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW);
    morphing = 0;
}
static void CALLBACK fly_tick(HWND w, UINT m, UINT_PTR id, DWORD now)
{
    double x = ease((double)(GetTickCount() - a_t0) / a_dur);
    HDWP dw;
    int k;
    if (glide_only) {
        /* a pure move: Windows carries the strip's painted pixels along, so no frame is ever half drawn */
        SetWindowPos(w, NULL, lerp(w0.left, w1.left, x), lerp(w0.top, w1.top, x), 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
    } else {
        SetWindowPos(w, NULL, lerp(w0.left, w1.left, x), lerp(w0.top, w1.top, x), lerp(w0.right - w0.left, w1.right - w1.left, x),
                     lerp(w0.bottom - w0.top, w1.bottom - w1.top, x), SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOREDRAW);
        dw = BeginDeferWindowPos(10);
        for (k = 0; k < 10; k++) {
            /* the parts lag one another a little, so the row assembles left to right */
            double y = ease(((double)(GetTickCount() - a_t0) - k * 18) / (a_dur - 10 * 18));
            RECT *b = &shm->kid_final[k];
            if (kid[k]) dw = DeferWindowPos(dw, kid[k], NULL, lerp(k0[k].left, b->left, y), lerp(k0[k].top, b->top, y),
                                            lerp(k0[k].right - k0[k].left, b->right - b->left, y), lerp(k0[k].bottom - k0[k].top, b->bottom - b->top, y),
                                            SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOREDRAW);
        }
        EndDeferWindowPos(dw);
        /* everything moved without drawing; now one complete repaint */
        RedrawWindow(w, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW);
        if (GetParent(w)) RedrawWindow(GetParent(w), NULL, NULL, RDW_UPDATENOW);
    }
    if (x >= 1) {
        KillTimer(w, T_FLY);
        if (!glide_only) morphing = 0;
        RedrawWindow(w, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW);
        done(glide_only ? SYO_GLIDE : SYO_MORPH, 0);
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


/* ---------------------------------------------------------------- the fast play path */
static void load_pcm(void)
{
    HANDLE f = CreateFileW(S->pcmfile, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
    DWORD sz, got, i;
    char *b;
    EnterCriticalSection(&cs);
    if (fh) { w_reset(fh); w_unprep(fh, &fhdr, sizeof fhdr); real_close(fh); fh = 0; if (cur == fh) cur = 0; }
    free(pcm); pcm = NULL; pcm_len = 0;
    LeaveCriticalSection(&cs);
    if (f == INVALID_HANDLE_VALUE) return;
    sz = GetFileSize(f, NULL);
    b = (char *)malloc(sz + 8);
    ReadFile(f, b, sz, &got, NULL);
    CloseHandle(f);
    /* RIFF: the fmt and data chunks; plain PCM only (what Sound Recorder saves) */
    if (got < 44 || memcmp(b, "RIFF", 4)) { free(b); return; }
    for (i = 12; i + 8 <= got;) {
        DWORD n = *(DWORD *)(b + i + 4);
        if (!memcmp(b + i, "fmt ", 4) && n >= 16) { memcpy(&pcm_fmt, b + i + 8, 16); pcm_fmt.cbSize = 0; }
        if (!memcmp(b + i, "data", 4)) {
            if (n > got - i - 8) n = got - i - 8;
            EnterCriticalSection(&cs);
            pcm = (char *)malloc(n + 4);
            memcpy(pcm, b + i + 8, n);
            pcm_len = n - n % (pcm_fmt.nBlockAlign ? pcm_fmt.nBlockAlign : 1);
            if (pcm_fmt.wFormatTag != 1) { free(pcm); pcm = NULL; pcm_len = 0; }
            LeaveCriticalSection(&cs);
            break;
        }
        i += 8 + n + (n & 1);
    }
    free(b);
}

static DWORD WINAPI note_thread(LPVOID p)
{
    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_TIME_CRITICAL);
    for (;;) {
        DWORD rate;
        WaitForSingleObject(note_ev, INFINITE);
        rate = S->rate > 0 ? (DWORD)S->rate : 0;
        EnterCriticalSection(&cs);
        if (!pcm) {      /* nothing loaded: let Sound Recorder play it the ordinary way */
            LeaveCriticalSection(&cs);
            PostMessageA((HWND)S->hwnd, msg_op, SYO_PLAY, 0);
            continue;
        }
        if (!rate) rate = pcm_fmt.nSamplesPerSec;
        if (fh) {                               /* stop what this recorder was playing */
            w_reset(fh);
            w_unprep(fh, &fhdr, sizeof fhdr);
            if (fh_rate != rate) { real_close(fh); fh = 0; }
        }
        if (!fh) {                              /* the card, at the note's rate: kmixer resamples */
            WAVEFORMATEX g = pcm_fmt;
            g.nSamplesPerSec = rate;
            g.nAvgBytesPerSec = rate * g.nBlockAlign;
            if (real_open(&fh, WAVE_MAPPER, &g, 0, 0, 0)) fh = 0;
            fh_rate = rate;
        }
        if (fh) {
            cur = fh;
            t0 = GetTickCount();
            t_rel = 0;
            stopping = 0;
            S->cut = 0;
            S->t_open = t0;
            S->opens++;
            S->playing = 1;
            apply_vol(env_level(t0));
            memset(&fhdr, 0, sizeof fhdr);
            fhdr.lpData = pcm;
            fhdr.dwBufferLength = pcm_len;
            w_prep(fh, &fhdr, sizeof fhdr);
            w_write(fh, &fhdr, sizeof fhdr);
        }
        LeaveCriticalSection(&cs);
        if (fh) {
            done(SYE_OPEN, (LONG)(t0 - S->t_post));
            PostMessageA((HWND)S->hwnd, msg_op, SYO_VISUAL, 0);
        }
    }
    return 0;
}

/* the strip shows the note as Sound Recorder would: Play held down, the slider, position and green wave following */
#define T_VIS 0xB53
static void CALLBACK vis_tick(HWND w, UINT m, UINT_PTR id, DWORD now)
{
    HWND play = GetDlgItem(w, SR_PLAY), tb = GetDlgItem(w, SR_TRACK);
    MMT mt;
    LONG mx, pos;
    int on;
    EnterCriticalSection(&cs);
    on = cur == fh && fh && S->playing;
    mt.wType = TIME_BYTES_;
    mt.u.cb = 0;
    if (on) w_pos(fh, &mt, sizeof mt);
    LeaveCriticalSection(&cs);
    mx = (LONG)SendMessageW(tb, TBM_GETRANGEMAX, 0, 0);
    pos = pcm_len ? (LONG)((double)mx * (mt.u.cb > pcm_len ? pcm_len : mt.u.cb) / pcm_len) : 0;
    if (on) {
        SendMessageW(tb, TBM_SETPOS, TRUE, pos);
        SendMessageW(w, WM_HSCROLL, MAKEWPARAM(TB_THUMBTRACK, pos), (LPARAM)tb);
    } else {
        SendMessageW(play, BM_SETSTATE, FALSE, 0);
        SendMessageW(w, WM_HSCROLL, MAKEWPARAM(TB_ENDTRACK, 0), (LPARAM)tb);
        KillTimer(w, T_VIS);
    }
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
        S->cut = 0;
        if (S->playing) { stopping = 1; cmd(SR_STOP); }
        cmd(SR_REW);
        S->t_req = GetTickCount();
        pending = 1;          /* srhook's waveOutOpen takes the note's rate and volume (and clears this) */
        cmd(SR_PLAY);
        break;
    case SYO_OFF: break;                  /* gate is already 0: the envelope thread releases */
    case SYO_CUT: S->cut = 1; break;
    case SYO_STOP: if (S->playing) cmd(SR_STOP); break;
    case SYO_CMD:
        S->answer = 1;
        cmd((int)arg);
        S->answer = 0;
        break;
    case SYO_SEEK: seek(arg); break;
    case SYO_NOMENU: SetMenu((HWND)S->hwnd, NULL); UpdateWindow((HWND)S->hwnd); break;
    case SYO_STRIP: strip(); break;
    case SYO_LOADPCM: load_pcm(); break;
    case SYO_SNAP: {
        int k;
        HWND w = (HWND)S->hwnd;
        if (!kid[0]) find_kids();
        KillTimer(w, T_FLY);
        morphing = 0;
        SetWindowPos(w, NULL, S->fly[0], S->fly[1], S->fly[2], S->fly[3], SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOREDRAW);
        for (k = 0; k < 10; k++) {
            RECT *b = &shm->kid_final[k];
            if (kid[k]) SetWindowPos(kid[k], NULL, b->left, b->top, b->right - b->left, b->bottom - b->top, SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOREDRAW);
        }
        for (k = 10; k < 13; k++) if (kid[k]) ShowWindow(kid[k], SW_HIDE);
        RedrawWindow(w, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW);
        break;
    }
    case SYO_VISUAL: {
        HWND w = (HWND)S->hwnd;
        SendMessageW(GetDlgItem(w, SR_PLAY), BM_SETSTATE, TRUE, 0);
        SetTimer(w, T_VIS, 50, vis_tick);
        return;
    }
    case SYO_DROP: {
        int k;
        if (!kid[0]) find_kids();
        for (k = 10; k < 13; k++) if (kid[k]) k0[k] = in_parent(kid[k]);
        d_t0 = GetTickCount();
        SetTimer((HWND)S->hwnd, T_DROP, 25, drop_tick);
        return;
    }
    case SYO_FLY:
    case SYO_MORPH:
    case SYO_GLIDE: {
        int k;
        if (!kid[0]) find_kids();
        if (op == SYO_GLIDE && morphing) { KillTimer((HWND)S->hwnd, T_FLY); finish_morph((HWND)S->hwnd); }   /* a slow machine */
        for (k = 0; k < 10; k++) if (kid[k]) k0[k] = in_parent(kid[k]);
        w0 = in_parent((HWND)S->hwnd);
        glide_only = op == SYO_GLIDE;
        morphing = op != SYO_GLIDE;
        if (op == SYO_MORPH) SetRect(&w1, w0.left, w0.top, w0.left + S->fly[2], w0.top + S->fly[3]);
        else if (op == SYO_GLIDE) SetRect(&w1, S->fly[0], S->fly[1], S->fly[0] + (w0.right - w0.left), S->fly[1] + (w0.bottom - w0.top));
        else SetRect(&w1, S->fly[0], S->fly[1], S->fly[0] + S->fly[2], S->fly[1] + S->fly[3]);
        a_dur = arg > 50 ? arg : 50;
        a_t0 = GetTickCount();
        SetTimer((HWND)S->hwnd, T_FLY, 20, fly_tick);
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
    w_prep = (P_HDR)GetProcAddress(GetModuleHandleA("winmm.dll"), "waveOutPrepareHeader");
    w_unprep = (P_HDR)GetProcAddress(GetModuleHandleA("winmm.dll"), "waveOutUnprepareHeader");
    w_write = (P_HDR)GetProcAddress(GetModuleHandleA("winmm.dll"), "waveOutWrite");
    w_reset = (P_RESET)GetProcAddress(GetModuleHandleA("winmm.dll"), "waveOutReset");
    w_pos = (P_POS)GetProcAddress(GetModuleHandleA("winmm.dll"), "waveOutGetPosition");
    {
        typedef UINT (WINAPI *TBP)(UINT);
        TBP tbp = (TBP)GetProcAddress(GetModuleHandleA("winmm.dll"), "timeBeginPeriod");
        char evn[64];
        if (tbp) tbp(1);                       /* 1 ms Sleep for the envelope */
        wsprintfA(evn, SY_NOTE_EV, slot);
        note_ev = OpenEventA(SYNCHRONIZE | EVENT_MODIFY_STATE, FALSE, evn);
    }
    patch("winmm.dll", "waveOutOpen", (void *)my_open, (void **)&real_open);
    patch("winmm.dll", "waveOutClose", (void *)my_close, (void **)&real_close);
    patch("comdlg32.dll", "GetOpenFileNameW", (void *)my_ofn, (void **)&real_ofn);
    patch("comdlg32.dll", "GetSaveFileNameW", (void *)my_sfn, (void **)&real_sfn);
    patch("user32.dll", "MessageBoxW", (void *)my_mb, (void **)&real_mb);
    is_rec = 1;
    CreateThread(NULL, 0, env_thread, NULL, 0, NULL);
    if (note_ev) CreateThread(NULL, 0, note_thread, NULL, 0, NULL);
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
