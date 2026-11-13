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
/* envelope time: the performance counter (the emulated ACPI timer, which follows the virtual clock the sound card
   runs on); XP's tick count runs slow when the emulator is short of CPU */
static DWORD cur_rate;
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
/* The fast path streams: XP's waveOutSetVolume on this machine is one volume for the whole card, not per handle
   (measured: one recorder's pan or envelope moved every other voice). So the level, pan and envelope are applied
   to the samples here, 20 ms at a time, four chunks queued (4 x 10 ms starves under the emulator). */
#define NCH 4
#define CH_MS 20
#define CH_MAXF 4096                    /* frames per chunk at up to 204 kHz */
static WAVEHDR chdr[NCH];
static short chbuf[NCH][CH_MAXF * 2];
static int ch_next;                     /* the next chunk to fill, in order */
#define OUT_RATE 48000                  /* the handle's fixed rate: opened once, never reopened for a pitch */
static DWORD src_frames, spos;          /* source frames; the next one (integer part of sp) */
static DWORD sfrac, sstep_i, sstep_f;   /* 16.16: source position fraction, and the step per output frame (pitch) */
static DWORD ofr;                       /* output frames queued for this note */
static int src_ch, src_bits, ended;     /* ended: no more source; the queued chunks play out */
static double g_l, g_r;                 /* the gains the last chunk ended with (ramped across each chunk) */
static DWORD wbytes, chstart[NCH];      /* bytes queued since the stream (re)started; where each chunk begins */
static HANDLE note_ev;

static void done(int op, LONG arg)
{
    if (shm && shm->synth_hwnd) PostMessageA((HWND)shm->synth_hwnd, msg_done, slot, op == SYE_OPEN ? (op | (arg << 8)) : op);
}

/* a v2 breakpoint curve (lenv) at t ms: linear between points, the last one held */
static LONG curve_at(int L, int which, LONG t, LONG dflt)
{
    int n, i;
    if (L < 0 || L >= 8) return dflt;
    n = shm->env[L][which].n;
    if (n <= 0) return dflt;
    if (t <= shm->env[L][which].t[0]) return shm->env[L][which].v[0];
    for (i = 1; i < n; i++) {
        LONG t0_ = shm->env[L][which].t[i - 1], t1 = shm->env[L][which].t[i], v0 = shm->env[L][which].v[i - 1], v1 = shm->env[L][which].v[i];
        if (t <= t1) return t1 > t0_ ? v0 + (LONG)((double)(v1 - v0) * (t - t0_) / (t1 - t0_)) : v1;
    }
    return shm->env[L][which].v[n - 1];
}

/* the envelope at time now, 0..65535 */
static DWORD env_now(void)
{
    static LARGE_INTEGER f;
    LARGE_INTEGER c;
    if (!f.QuadPart && !QueryPerformanceFrequency(&f)) f.QuadPart = -1;
    if (f.QuadPart <= 0 || !QueryPerformanceCounter(&c)) return GetTickCount();
    return (DWORD)(c.QuadPart * 1000 / f.QuadPart);
}
static LONG env_level(DWORD now)
{
    LONG a = shm->env_a, d = shm->env_d, s = shm->env_s * 65535 / 100, t = (LONG)(now - t0), l;
    if (s > 65535) s = 65535;
    if (s < 0) s = 0;
    if (t < a) l = (LONG)((double)t * 65535 / a);
    else if (t < a + d) l = 65535 - (LONG)((double)(t - a) * (65535 - s) / d);
    else l = s;
    if (S->layer >= 0 && S->layer < 8 && shm->env[S->layer][0].n > 0)      /* a drawn envelope replaces A, D and S */
        l = curve_at(S->layer, 0, t, 100) * 65535 / 100;
    if (t_rel) {
        LONG r = (LONG)(now - t_rel);
        l = r >= rel_ms ? 0 : (LONG)((double)lvl_rel * (rel_ms - r) / rel_ms);
    }
    return l;
}

/* the gains for envelope level l (0..65535) at note time t ms: velocity, then pan as a balance */
static void gains(LONG l, LONG t, double *gl, double *gr)
{
    double v = (double)l / 65535 * S->vol / 65535;
    LONG pan = S->pan + (S->layer >= 0 && S->layer < 8 ? curve_at(S->layer, 1, t, 0) : 0);
    if (pan > 100) pan = 100;
    if (pan < -100) pan = -100;
    *gl = pan > 0 ? v * (100 - pan) / 100 : v;
    *gr = pan < 0 ? v * (100 + pan) / 100 : v;
    S->level = l;
}

/* note time of the next chunk: the source frames already queued, at the rate they play */
static DWORD stream_now(void) { return t0 + (DWORD)((double)ofr * 1000 / OUT_RATE); }

/* the source as 16-bit stereo, made once when the sound loads: the inner loop below is integers only (x87 floating
   point is slow under the emulator) */
static short *src16;
static void make_src16(void)
{
    DWORD i;
    free(src16);
    src16 = (short *)malloc((size_t)(src_frames + 2) * 4);
    if (!src16) return;
    for (i = 0; i < src_frames; i++) {
        int l, r;
        if (src_bits == 16) { const short *q = (const short *)pcm + (size_t)i * src_ch; l = q[0]; r = src_ch > 1 ? q[1] : q[0]; }
        else { const unsigned char *b = (const unsigned char *)pcm + (size_t)i * src_ch; l = ((int)b[0] - 128) << 8; r = src_ch > 1 ? ((int)b[1] - 128) << 8 : l; }
        src16[2 * i] = (short)l; src16[2 * i + 1] = (short)r;
    }
    src16[2 * src_frames] = src16[2 * src_frames + 1] = src16[2 * src_frames + 2] = src16[2 * src_frames + 3] = 0;
}

/* fill chunk k with the next 20 ms (levels ramp from the last chunk's to this one's) and queue it; 0 when nothing
   is left to play */
static int fill_chunk(int k)
{
    WAVEHDR *h = &chdr[k];
    DWORD n = OUT_RATE * CH_MS / 1000, i, now;
    double gl, gr, l, r;
    LONG lv;
    short *o = chbuf[k];
    if (n > CH_MAXF) n = CH_MAXF;
    if (n < 16) n = 16;
    if (ended || spos >= src_frames) { ended = 1; return 0; }
    now = stream_now();
    if (!t_rel && (!S->gate || S->cut)) {     /* the note was let go (or cut): the release starts with this chunk */
        lvl_rel = S->level;
        rel_ms = S->cut ? 5 : (shm->env_r > 0 ? shm->env_r : 1);
        t_rel = now;
    }
    lv = env_level(now + CH_MS);
    gains(lv, (LONG)(now + CH_MS - t0), &gl, &gr);
    {
        /* linear interpolation through the source in 16.16 fixed point (the step is the pitch); gains in Q15,
           ramped from the last chunk's to this one's */
        LONG gl0 = (LONG)(g_l * 32768), gr0 = (LONG)(g_r * 32768), gl1 = (LONG)(gl * 32768), gr1 = (LONG)(gr * 32768);
        LONG dgl = (gl1 - gl0) / (LONG)n, dgr = (gr1 - gr0) / (LONG)n, xl = gl0, xr = gr0;
        DWORD idx = spos, frac = sfrac, si = sstep_i, sf = sstep_f;
        for (i = 0; i < n; i++) {
            LONG l = 0, r = 0;
            if (src16 && idx < src_frames) {
                const short *q = src16 + 2 * idx;
                l = q[0] + (((LONG)q[2] - q[0]) * (LONG)(frac >> 1) >> 15);
                r = q[1] + (((LONG)q[3] - q[1]) * (LONG)(frac >> 1) >> 15);
                frac += sf; idx += si + (frac >> 16); frac &= 0xFFFF;
            }
            l = (l * (xl >> 1)) >> 14; r = (r * (xr >> 1)) >> 14;
            o[2 * i] = (short)(l > 32767 ? 32767 : l < -32768 ? -32768 : l);
            o[2 * i + 1] = (short)(r > 32767 ? 32767 : r < -32768 ? -32768 : r);
            xl += dgl; xr += dgr;
        }
        spos = idx > src_frames ? src_frames : idx; sfrac = frac;
    }
    g_l = gl; g_r = gr;
    ofr += n;
    if (t_rel && lv == 0) { ended = 1; spos = src_frames; }        /* released to silence */
    if (h->dwFlags & 2 /* WHDR_PREPARED */) w_unprep(fh, h, sizeof *h);
    memset(h, 0, sizeof *h);
    h->lpData = (char *)o;
    h->dwBufferLength = n * 4;
    chstart[k] = wbytes;
    wbytes += n * 4;
    w_prep(fh, h, sizeof *h);
    w_write(fh, h, sizeof *h);
    return 1;
}

static int chunks_busy(void)
{
    int k, b = 0;
    for (k = 0; k < NCH; k++) if ((chdr[k].dwFlags & 2) && !(chdr[k].dwFlags & WHDR_DONE_)) b++;
    return b;
}

/* stop the stream now: what is queued is faded out in place over 4 ms first (no click), then the card is reset */
static void open_fh(void);
static void stream_stop(void)
{
    int k;
    MMT mt;
    DWORD played, fade = OUT_RATE * 4 / 1000 * 4, lead = OUT_RATE * 3 / 1000 * 4;   /* bytes: 4 ms fade, from 3 ms ahead */
    mt.wType = TIME_BYTES_; mt.u.cb = 0;
    if (!fh) return;
    if (w_pos) w_pos(fh, &mt, sizeof mt);
    played = mt.u.cb + lead;
    if (!chunks_busy()) {        /* nothing playing: nothing to fade */
        for (k = 0; k < NCH; k++) if (chdr[k].dwFlags & 2) w_unprep(fh, &chdr[k], sizeof chdr[k]);
        memset(chdr, 0, sizeof chdr);
        wbytes = 0;
        return;
    }
    for (k = 0; k < NCH; k++) if ((chdr[k].dwFlags & 2) && !(chdr[k].dwFlags & WHDR_DONE_)) {
        /* what is still queued is faded from a little ahead of the play position, then silent */
        DWORD n = chdr[k].dwBufferLength / 4, i;
        for (i = 0; i < n; i++) {
            DWORD o = chstart[k] + i * 4;
            double g = o < played ? 1.0 : o >= played + fade ? 0.0 : 1.0 - (double)(o - played) / fade;
            if (g < 1.0) { chbuf[k][2 * i] = (short)(chbuf[k][2 * i] * g); chbuf[k][2 * i + 1] = (short)(chbuf[k][2 * i + 1] * g); }
        }
    }
    Sleep(8);
    w_reset(fh);
    for (k = 0; k < NCH; k++) if (chdr[k].dwFlags & 2) w_unprep(fh, &chdr[k], sizeof chdr[k]);
    memset(chdr, 0, sizeof chdr);
    wbytes = 0;
}

static DWORD WINAPI env_thread(LPVOID p)
{
    for (;;) {
        Sleep(5);
        EnterCriticalSection(&cs);
        if (cur && !stopping) {
            DWORD now = env_now();
            LONG l;
            if (!t_rel && (!S->gate || S->cut)) {     /* the note was let go (or cut) */
                lvl_rel = S->level;
                rel_ms = S->cut ? 5 : (shm->env_r > 0 ? shm->env_r : 1);
                t_rel = now;
            }
            if (cur == fh && fh) {
                /* the fast path: keep four chunks queued; the note ends when the last one has played */
                int k, guard;
                for (guard = 0; guard < NCH; guard++) {
                    k = ch_next;
                    if ((chdr[k].dwFlags & 2) && !(chdr[k].dwFlags & WHDR_DONE_)) break;   /* still playing */
                    if (!fill_chunk(k)) break;
                    ch_next = (ch_next + 1) % NCH;
                }
                if (ended && !chunks_busy()) {
                    for (k = 0; k < NCH; k++) if (chdr[k].dwFlags & 2) w_unprep(fh, &chdr[k], sizeof chdr[k]);
                    memset(chdr, 0, sizeof chdr);
                    cur = 0; S->playing = 0; S->level = 0;
                    done(SYE_END, 0);
                }
                LeaveCriticalSection(&cs);
                continue;
            }
            l = env_level(now);
            S->level = l;          /* Sound Recorder's own Play (a click in XP): as it is */
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
        cur_rate = S->rate > 0 ? (DWORD)S->rate : f->nSamplesPerSec;
        t0 = env_now();
        t_rel = 0;
        stopping = 0;
        S->t_open = GetTickCount();
        S->opens++;
        S->playing = 1;
        S->level = env_level(t0);
        LeaveCriticalSection(&cs);
        done(SYE_OPEN, (LONG)(S->t_open - S->t_req));
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
    if (fh) { stream_stop(); if (cur == fh) { cur = 0; S->playing = 0; } }
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
            if (pcm_fmt.wFormatTag != 1 || (pcm_fmt.wBitsPerSample != 8 && pcm_fmt.wBitsPerSample != 16) || pcm_fmt.nChannels < 1 || pcm_fmt.nChannels > 2) { free(pcm); pcm = NULL; pcm_len = 0; }
            else { src_ch = pcm_fmt.nChannels; src_bits = pcm_fmt.wBitsPerSample; src_frames = pcm_len / pcm_fmt.nBlockAlign; make_src16(); open_fh(); }
            LeaveCriticalSection(&cs);
            break;
        }
        i += 8 + n + (n & 1);
    }
    free(b);
}

/* the card, stereo 16-bit at a fixed rate, opened once: a note never waits for waveOutOpen */
static void open_fh(void)
{
    WAVEFORMATEX g;
    if (fh) return;
    g.wFormatTag = 1; g.nChannels = 2; g.wBitsPerSample = 16; g.nBlockAlign = 4; g.cbSize = 0;
    g.nSamplesPerSec = OUT_RATE;
    g.nAvgBytesPerSec = OUT_RATE * 4;
    if (real_open(&fh, WAVE_MAPPER, &g, 0, 0, 0)) fh = 0;
    fh_rate = OUT_RATE;
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
        if (fh) {                               /* stop what this recorder was playing (faded, no click) */
            stream_stop();

        }
        if (!fh) open_fh();
        if (fh) {
            cur = fh;
            cur_rate = fh_rate;
            t0 = env_now();
            t_rel = 0;
            stopping = 0;
            S->cut = 0;
            S->t_open = GetTickCount();
            S->opens++;
            S->playing = 1;
            spos = 0; sfrac = 0; ofr = 0; ended = 0; ch_next = 0; wbytes = 0;
            {
                unsigned __int64 st = ((unsigned __int64)rate << 16) / OUT_RATE;
                sstep_i = (DWORD)(st >> 16); sstep_f = (DWORD)(st & 0xFFFF);
            }
            gains(env_level(t0), 0, &g_l, &g_r);
            {
                int k;
                for (k = 0; k < NCH; k++) { if (!fill_chunk(k)) break; ch_next = (k + 1) % NCH; }
            }
        }
        LeaveCriticalSection(&cs);
        if (fh) {
            done(SYE_OPEN, (LONG)(S->t_open - S->t_post));
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
    {
        /* bytes the card has played (stereo 16-bit) -> source frames */
        DWORD f = (DWORD)(((unsigned __int64)(mt.u.cb / 4) * ((sstep_i << 16) | sstep_f)) >> 16);
        pos = src_frames ? (LONG)((double)mx * (f > src_frames ? src_frames : f) / src_frames) : 0;
    }
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


/* ---------------------------------------------------------------- building, visibly */
/* The command runs from Sound Recorder's own menu: it pops up at the strip, the highlight walks down to the item,
   Enter. The command it returns is executed the ordinary way. */
static HMENU g_menu;
static volatile int walk_presses;
static HMENU walk_menu;
#define MN_GETHMENU_ 0x01E1
static DWORD WINAPI walker(LPVOID p)
{
    HWND pop = NULL, w = (HWND)S->hwnd;
    int k, i;
    /* the popup that shows this menu (not one still fading out from before) */
    for (k = 0; k < 100 && !pop; k++) {
        HWND h = NULL;
        while ((h = FindWindowExA(NULL, h, "#32768", NULL))) {
            DWORD pid;
            GetWindowThreadProcessId(h, &pid);
            if (pid == GetCurrentProcessId() && IsWindowVisible(h) && (HMENU)SendMessageA(h, MN_GETHMENU_, 0, 0) == walk_menu) { pop = h; break; }
        }
        if (!pop) Sleep(10);
    }
    if (!pop) { PostMessageA(w, WM_CANCELMODE, 0, 0); return 0; }
    Sleep(60);
    for (i = 0; i < walk_presses; i++) { PostMessageA(pop, WM_KEYDOWN, VK_DOWN, 0); Sleep(45); }
    Sleep(110);
    PostMessageA(pop, WM_KEYDOWN, VK_RETURN, 0);
    for (k = 0; k < 30; k++) {           /* still up: close it; the command runs anyway */
        Sleep(20);
        if (!IsWindowVisible(pop)) return 0;
    }
    PostMessageA(w, WM_CANCELMODE, 0, 0);
    return 0;
}
static void visible_cmd(int id)
{
    HWND w = (HWND)S->hwnd;
    HMENU m = g_menu ? g_menu : GetMenu(w), sub = NULL;
    int i, k, n, presses = 0, got;
    for (i = 0; m && i < GetMenuItemCount(m) && !sub; i++) {
        HMENU sm = GetSubMenu(m, i);
        if (!sm) continue;
        presses = 0;
        n = GetMenuItemCount(sm);
        for (k = 0; k < n; k++) {
            UINT st = GetMenuState(sm, k, MF_BYPOSITION);
            if (!(st & MF_SEPARATOR)) presses++;
            if (GetMenuItemID(sm, k) == (UINT)id) { sub = sm; break; }
        }
    }
    S->answer = 1;
    if (sub) {
        walk_presses = presses;
        walk_menu = sub;
        CloseHandle(CreateThread(NULL, 0, walker, NULL, 0, NULL));
        got = (int)TrackPopupMenu(sub, TPM_RETURNCMD | TPM_LEFTALIGN | TPM_TOPALIGN | TPM_NONOTIFY, S->menu_x, S->menu_y, 0, w, NULL);
        (void)got;
    }
    cmd(id);
    S->answer = 0;
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
    case SYO_NOMENU: g_menu = GetMenu((HWND)S->hwnd); SetMenu((HWND)S->hwnd, NULL); UpdateWindow((HWND)S->hwnd); break;
    case SYO_CMDV: visible_cmd((int)arg); break;
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
