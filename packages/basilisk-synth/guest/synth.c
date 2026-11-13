/* BASILISK SYNTH - inside Windows XP: sixteen real Sound Recorders become one instrument.

   At startup (before the machine is saved for the plugin):
     - sixteen sndrec32.exe open, tiled over the desktop
     - srhook.dll is placed inside each one (see srhook.c)
     - Date and Time and Task Manager open too
     - the default DNA is built
     - then it waits on COM1
   On "go" from the plugin, the recorders come apart and line up, one visible change at a time, into one window:
   sixteen tape strips (Play, Stop, Position, the green wave, Length, the slider), plus the clock and the CPU graph
   beside them.

   The plugin plays notes over COM1 (protocol: ../DNA.md section 4). Each note is a real Sound Recorder playing its
   buffer, at the note's rate.

   Build (in XP): tcc -o synth.exe synth.c -luser32 -lgdi32 -Wl,-subsystem=windows */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mm.h"
#include "synthshm.h"

/* tcc's windows.h has no NLS declarations */
#ifndef CP_ACP
#define CP_ACP 0
WINBASEAPI int WINAPI MultiByteToWideChar(UINT, DWORD, LPCSTR, int, LPWSTR, int);
#endif

#define VERSION "1.0"
#define ROW_H 41
#define STRIP_X 30
#define STRIP_Y 6
#define STRIP_W 562
#define SIDE_X (STRIP_X + STRIP_W + 14)
#define SIDE_W (1016 - SIDE_X)
#define NSND 35
#define MAXL 8
#define MAXSTEP 64
#define MAXLEN_MS 30000
#define WM_LINE (WM_APP + 1)
#define WM_BUILT (WM_APP + 2)

/* ---------------------------------------------------------------- the sounds (DNA.md 2.4) */
static const char *snd_name[NSND] = {
    "chimes", "chord", "ding", "notify", "recycle", "ringin", "ringout", "start", "tada",
    "balloon", "batcrit", "batlow", "critstop", "default", "xpding", "error", "exclaim", "hwfail", "hwin", "hwout",
    "infobar", "logoff", "logon", "menu", "minimize", "xpnotify", "popup", "print", "xprecycle", "restore",
    "xpringin", "xpringout", "shutdown", "startup", "xpstart"};
static const char *snd_file[NSND] = {
    "chimes.wav", "chord.wav", "ding.wav", "notify.wav", "recycle.wav", "ringin.wav", "ringout.wav", "start.wav", "tada.wav",
    "Windows XP Balloon.wav", "Windows XP Battery Critical.wav", "Windows XP Battery Low.wav", "Windows XP Critical Stop.wav",
    "Windows XP Default.wav", "Windows XP Ding.wav", "Windows XP Error.wav", "Windows XP Exclamation.wav",
    "Windows XP Hardware Fail.wav", "Windows XP Hardware Insert.wav", "Windows XP Hardware Remove.wav",
    "Windows XP Information Bar.wav", "Windows XP Logoff Sound.wav", "Windows XP Logon Sound.wav",
    "Windows XP Menu Command.wav", "Windows XP Minimize.wav", "Windows XP Notify.wav", "Windows XP Pop-up Blocked.wav",
    "Windows XP Print complete.wav", "Windows XP Recycle.wav", "Windows XP Restore.wav", "Windows XP Ringin.wav",
    "Windows XP Ringout.wav", "Windows XP Shutdown.wav", "Windows XP Startup.wav", "Windows XP Start.wav"};
static int snd_ms[NSND];    /* lengths, read from the files once */

static const char *DEFAULT_DNA = "chord#10/ding>>E#6;A2D300S70R250";

/* ---------------------------------------------------------------- state */
static SyShm *shm;
static UINT msg_op, msg_done;
static HWND win;                       /* the synth window (hidden until "go") */
static HINSTANCE inst;
static HANDLE com = INVALID_HANDLE_VALUE;
static CRITICAL_SECTION com_cs;
static HANDLE ev_done[SY_NREC];
static volatile LONG building, assembled, sel_layer;
static FILE *logf;

typedef struct {
    HWND w;            /* the Sound Recorder's main window */
    DWORD pid, tid;
    HWND kid[16];      /* its controls, by index into kid_id[] */
    RECT r0;           /* where it sat on the desktop (screen) */
    int layer;         /* which layer's pool it is in (-1: none) */
} Rec;
static Rec rec[SY_NREC];
/* the controls a strip keeps, in this order; the shadow frame around Position has no id (-1) */
static const int kid_id[] = {SR_PLAY, SR_STOP, -1, 302, SR_POS, SR_WAVE, 304, 305, SR_LEN, SR_TRACK, SR_REW, SR_FWD, SR_REC};
#define NKID 13
#define K_PLAY 0
#define K_STOP 1
#define K_PFRAME 2
#define K_PLABEL 3
#define K_POS 4
#define K_WAVE 5
#define K_LFRAME 6
#define K_LLABEL 7
#define K_LEN 8
#define K_TRACK 9
#define K_REW 10
#define K_FWD 11
#define K_REC 12

/* ---------------------------------------------------------------- log, COM1 */
static void logf_(const char *fmt, ...)
{
    va_list a;
    if (!logf) logf = fopen("C:\\synth\\synth.log", "a");
    if (!logf) return;
    va_start(a, fmt);
    fprintf(logf, "%8lu ", GetTickCount());
    vfprintf(logf, fmt, a);
    fputc('\n', logf);
    fflush(logf);
    va_end(a);
}

/* lines to the plugin go through a queue and a writer thread: after a resume the UART's transmit interrupt is lost
   and XP's serial driver sends only when the plugin's pings come in, so a write may wait; nothing else ever does */
static char txq[16384];
static int txn;
static HANDLE tx_ev;
static void send_line(const char *fmt, ...)
{
    char b[1400];
    va_list a;
    int n;
    va_start(a, fmt);
    _vsnprintf(b, sizeof b - 2, fmt, a);
    va_end(a);
    b[sizeof b - 3] = 0;
    strcat(b, "\n");
    n = (int)strlen(b);
    EnterCriticalSection(&com_cs);
    if (txn + n <= (int)sizeof txq) { memcpy(txq + txn, b, n); txn += n; }
    LeaveCriticalSection(&com_cs);
    if (tx_ev) SetEvent(tx_ev);
}
static DWORD WINAPI tx_thread(LPVOID p)
{
    /* writes time out after 40 ms and continue with what is left: a synchronous COM handle serializes its reads and
       writes, so a write that waited forever would also stop the reads that unstick it */
    static char b[32768];
    int n = 0, off = 0;
    for (;;) {
        DWORD w = 0;
        if (off >= n) {
            WaitForSingleObject(tx_ev, 500);
            n = off = 0;
        }
        EnterCriticalSection(&com_cs);
        if (txn && n + txn <= (int)sizeof b) { memcpy(b + n, txq, txn); n += txn; txn = 0; }
        LeaveCriticalSection(&com_cs);
        if (off < n && com != INVALID_HANDLE_VALUE) {
            static OVERLAPPED ov;
            if (!ov.hEvent) ov.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);
            ResetEvent(ov.hEvent);
            if (!WriteFile(com, b + off, n - off, &w, &ov) && GetLastError() == ERROR_IO_PENDING)
                GetOverlappedResult(com, &ov, &w, TRUE);
            off += (int)w;
            if (!w) Sleep(5);
        }
        if (off >= n) { n = off = 0; }
    }
    return 0;
}

static void open_com(void)
{
    DCB d;
    COMMTIMEOUTS t;
    /* overlapped: reads and writes run side by side (a synchronous handle serializes them, and a stalled write then
       starves the reads that would unstick it) */
    com = CreateFileA("\\\\.\\COM1", GENERIC_READ | GENERIC_WRITE, 0, NULL, OPEN_EXISTING, FILE_FLAG_OVERLAPPED, NULL);
    if (com == INVALID_HANDLE_VALUE) { logf_("no COM1 (%lu)", GetLastError()); return; }
    memset(&d, 0, sizeof d);
    d.DCBlength = sizeof d;
    GetCommState(com, &d);
    d.BaudRate = 115200; d.ByteSize = 8; d.Parity = NOPARITY; d.StopBits = ONESTOPBIT;
    d.fBinary = 1; d.fOutxCtsFlow = 0; d.fOutxDsrFlow = 0; d.fDtrControl = DTR_CONTROL_ENABLE;
    d.fRtsControl = RTS_CONTROL_ENABLE; d.fOutX = 0; d.fInX = 0;
    SetCommState(com, &d);
    SetupComm(com, 8192, 8192);
    memset(&t, 0, sizeof t);
    t.ReadIntervalTimeout = MAXDWORD;      /* return what is there ... */
    t.ReadTotalTimeoutMultiplier = MAXDWORD;
    t.ReadTotalTimeoutConstant = 200;      /* ... or wait up to 200 ms for the first byte */
    t.WriteTotalTimeoutConstant = 40;      /* the writer thread retries what did not go */
    SetCommTimeouts(com, &t);
}

/* ---------------------------------------------------------------- DNA */
typedef struct { char op; int arg; } Step;
typedef struct {
    int src;                 /* -1: unknown name, the layer is empty */
    Step step[MAXSTEP];
    int nstep;
    int pool;                /* #N, 0 = not given */
    int first, count;        /* recorders, after pool sizing */
    char key[600];           /* source + steps: what the buffer depends on */
    int rate, frames;        /* of the built file */
} Layer;
typedef struct {
    Layer l[MAXL];
    int n;
    int a, d, s, r;
} Dna;
static Dna dna, built_dna;
static char dna_text[1100] = "";
static char built_text[1100] = "";

static int snd_find(const char *p, int *len)
{
    int n = 0, i;
    while ((p[n] >= 'a' && p[n] <= 'z') || (p[n] >= '0' && p[n] <= '9')) n++;
    *len = n;
    for (i = 0; i < NSND; i++) if ((int)strlen(snd_name[i]) == n && !strncmp(p, snd_name[i], n)) return i;
    return -1;
}

static int read_int(const char **pp)
{
    const char *p = *pp;
    int sg = 1, v = 0;
    if (*p == '-' || *p == '+') { if (*p == '-') sg = -1; p++; }
    while (*p >= '0' && *p <= '9') { v = v * 10 + (*p - '0'); if (v > 100000) v = 100000; p++; }
    *pp = p;
    return sg * v;
}

static void dna_parse(const char *text, Dna *D)
{
    const char *p = text;
    int i, avail, nfree, k;
    memset(D, 0, sizeof *D);
    D->s = 100; D->r = 120;
    while (*p && *p != ';' && D->n < MAXL) {
        Layer *L = &D->l[D->n++];
        int len;
        char *kp;
        L->src = snd_find(p, &len);
        p += len;
        while (*p && *p != '/' && *p != ';') {
            char c = *p++;
            Step st;
            st.op = c; st.arg = 0;
            switch (c) {
            case '+': case '-': case '>': case '<': case 'E': case 'R': case '[': case ']': case 'C': case 'P': case 'X':
                if (L->nstep < MAXSTEP) L->step[L->nstep++] = st;
                break;
            case '@':
                st.arg = read_int(&p);
                if (st.arg < 0) st.arg = 0;
                if (st.arg > 99) st.arg = 99;
                if (L->nstep < MAXSTEP) L->step[L->nstep++] = st;
                break;
            case 'I': case 'M':
                st.arg = snd_find(p, &len);
                p += len;
                if (st.arg >= 0 && L->nstep < MAXSTEP) L->step[L->nstep++] = st;
                break;
            case '#': L->pool = read_int(&p); if (L->pool < 1) L->pool = 1; if (L->pool > 16) L->pool = 16; break;
            case 'T': case 'L': read_int(&p); break;
            case 'H': read_int(&p); while (*p == ',') { p++; read_int(&p); } break;
            case 'U': read_int(&p); if (*p == '~') { p++; read_int(&p); } break;
            case 'F': break;
            default: break;
            }
        }
        if (*p == '/') p++;
        /* the key the buffer depends on */
        kp = L->key;
        kp += sprintf(kp, "%d:", L->src);
        for (i = 0; i < L->nstep && kp - L->key < (int)sizeof L->key - 8; i++)
            kp += sprintf(kp, "%c%d", L->step[i].op, L->step[i].arg);
    }
    while (*p && *p != ';') p++;
    if (*p == ';') {
        p++;
        while (*p) {
            char c = *p++;
            int v;
            if (c == 'A' || c == 'D' || c == 'S' || c == 'R' || c == 'B' || c == 'V' || c == 'K' || c == 'G') {
                v = read_int(&p);
                if (c == 'A') D->a = v < 0 ? 0 : v;
                if (c == 'D') D->d = v < 0 ? 0 : v;
                if (c == 'S') D->s = v < 0 ? 0 : v > 100 ? 100 : v;
                if (c == 'R') D->r = v < 0 ? 0 : v;
            }
        }
    }
    /* pools (DNA.md 2.5): fixed sizes first, in layer order, always leaving one for each later non-empty layer;
       then the rest share what is left; pools are contiguous in layer order */
    avail = SY_NREC;
    for (i = 0; i < D->n; i++) {
        int later = 0;
        if (D->l[i].src < 0 || !D->l[i].pool) continue;
        for (k = i + 1; k < D->n; k++) if (D->l[k].src >= 0) later++;
        for (k = 0; k < i; k++) if (D->l[k].src >= 0 && !D->l[k].pool) later++;
        D->l[i].count = D->l[i].pool;
        if (D->l[i].count > avail - later) D->l[i].count = avail - later;
        if (D->l[i].count < 1) D->l[i].count = 1;
        avail -= D->l[i].count;
    }
    nfree = 0;
    for (i = 0; i < D->n; i++) if (D->l[i].src >= 0 && !D->l[i].pool) nfree++;
    k = 0;
    for (i = 0; i < D->n; i++) {
        if (D->l[i].src < 0 || D->l[i].pool) continue;
        D->l[i].count = avail / nfree + (k < avail % nfree ? 1 : 0);
        k++;
    }
    k = 0;
    for (i = 0; i < D->n; i++) { D->l[i].first = k; k += D->l[i].count; }
}

/* ---------------------------------------------------------------- driving a recorder */
static int rec_op(int r, int op, LONG arg, int wait_ms)
{
    ResetEvent(ev_done[r]);
    PostMessageA(rec[r].w, msg_op, op, arg);
    if (!wait_ms) return 1;
    return WaitForSingleObject(ev_done[r], wait_ms) == WAIT_OBJECT_0;
}

static void rec_file(int r, const char *path)
{
    MultiByteToWideChar(CP_ACP, 0, path, -1, shm->s[r].file, 260);
}

static int read_ms(int r, int id)   /* "1.93 sec." -> 1930 */
{
    char t[64];
    double v = 0;
    GetDlgItemTextA(rec[r].w, id, t, sizeof t);
    sscanf(t, "%lf", &v);
    return (int)(v * 1000 + 0.5);
}

static int wav_info(const char *path, int *rate, int *frames)
{
    unsigned char h[64];
    FILE *f = fopen(path, "rb");
    long sz;
    int n, align;
    if (!f) return 0;
    n = (int)fread(h, 1, 44, f);
    fseek(f, 0, SEEK_END);
    sz = ftell(f);
    fclose(f);
    if (n < 44 || memcmp(h, "RIFF", 4)) return 0;
    *rate = h[24] | h[25] << 8 | h[26] << 16 | h[27] << 24;
    align = h[32] | h[33] << 8;
    *frames = align ? (int)((sz - 44) / align) : 0;
    return 1;
}

static void media_path(char *out, int i) { sprintf(out, "C:\\WINDOWS\\Media\\%s", snd_file[i]); }

/* one layer, on its first recorder, with Sound Recorder's own commands */
static void build_layer(int li, Layer *L)
{
    int r = L->first, i, len_ms, clip_ms;
    char path[MAX_PATH];
    DWORD t0 = GetTickCount();
    media_path(path, L->src);
    rec_file(r, path);
    rec_op(r, SYO_CMD, SR_OPEN, 8000);
    rec_op(r, SYO_CMD, SR_COPY, 8000);           /* the clipboard starts as the source (DNA.md 2.1) */
    len_ms = clip_ms = read_ms(r, SR_LEN);
    for (i = 0; i < L->nstep; i++) {
        Step *s = &L->step[i];
        int id = 0, grow = 0, pos;
        switch (s->op) {
        case '+': id = SR_VOL_UP; break;
        case '-': id = SR_VOL_DOWN; break;
        case '>': id = SR_SPEED_UP; break;
        case '<': id = SR_SPEED_DOWN; grow = len_ms; break;
        case 'E': id = SR_ECHO; break;
        case 'R': id = SR_REVERSE; break;
        case '[': id = SR_DEL_BEFORE; break;
        case ']': id = SR_DEL_AFTER; break;
        case 'C': id = SR_COPY; break;
        case 'P': id = SR_PASTE_INS; grow = clip_ms; break;
        case 'X': id = SR_PASTE_MIX; pos = read_ms(r, SR_POS); grow = pos + clip_ms > len_ms ? pos + clip_ms - len_ms : 0; break;
        case 'I': id = SR_INSFILE; grow = snd_ms[s->arg]; break;
        case 'M': id = SR_MIXFILE; pos = read_ms(r, SR_POS); grow = pos + snd_ms[s->arg] > len_ms ? pos + snd_ms[s->arg] - len_ms : 0; break;
        case '@': rec_op(r, SYO_SEEK, s->arg * 10, 4000); continue;
        }
        if (!id) continue;
        if (len_ms + grow > MAXLEN_MS) { logf_("layer %d step %d skipped (length)", li, i); continue; }
        if (s->op == 'I' || s->op == 'M') { media_path(path, s->arg); rec_file(r, path); }
        rec_op(r, SYO_CMD, id, 15000);
        len_ms = read_ms(r, SR_LEN);
        if (s->op == 'C') clip_ms = len_ms;
    }
    sprintf(path, "C:\\synth\\layer%d.wav", li);
    DeleteFileA(path);
    rec_file(r, path);
    rec_op(r, SYO_CMD, SR_SAVEAS, 15000);
    if (!wav_info(path, &L->rate, &L->frames)) { L->rate = 22050; L->frames = 0; }
    logf_("layer %d built on rec %d: %d steps, %d ms, rate %d, %lu ms work", li, r, L->nstep, len_ms, L->rate, GetTickCount() - t0);
}

static void load_pool(int li, Layer *L)
{
    int r;
    char path[MAX_PATH];
    sprintf(path, "C:\\synth\\layer%d.wav", li);
    for (r = L->first + 1; r < L->first + L->count; r++) {
        rec_file(r, path);
        rec_op(r, SYO_CMD, SR_OPEN, 0);
    }
    for (r = L->first + 1; r < L->first + L->count; r++) { int ok = WaitForSingleObject(ev_done[r], 8000) == WAIT_OBJECT_0; logf_("  pool %d loaded %d", r, ok); }
}

/* apply dna_text: rebuild what changed */
static DWORD WINAPI build_thread(LPVOID p)
{
    Dna D;
    char text[1100];
    int i, r;
    DWORD t0 = GetTickCount();
    lstrcpynA(text, dna_text, sizeof text);
    dna_parse(text, &D);
    for (r = 0; r < SY_NREC; r++) {           /* everything stops while the tapes change */
        shm->s[r].gate = 0;
        if (shm->s[r].playing) rec_op(r, SYO_STOP, 0, 0);
    }
    for (i = 0; i < D.n; i++) {
        Layer *L = &D.l[i], *O = i < built_dna.n ? &built_dna.l[i] : NULL;
        if (L->src < 0 || !L->count) continue;
        if (O && !strcmp(O->key, L->key) && O->first == L->first && O->count == L->count && O->frames) {
            L->rate = O->rate; L->frames = O->frames;
            continue;
        }
        if (O && !strcmp(O->key, L->key) && O->frames) {   /* same sound, other recorders: reload only */
            char path[MAX_PATH];
            sprintf(path, "C:\\synth\\layer%d.wav", i);
            rec_file(L->first, path);
            rec_op(L->first, SYO_CMD, SR_OPEN, 8000);
            L->rate = O->rate; L->frames = O->frames;
        } else build_layer(i, L);
        load_pool(i, L);
    }
    for (r = 0; r < SY_NREC; r++) rec[r].layer = -1;
    for (i = 0; i < D.n; i++) for (r = D.l[i].first; r < D.l[i].first + D.l[i].count; r++) rec[r].layer = i;
    for (r = 0; r < SY_NREC; r++) if (rec[r].layer < 0) {     /* unused recorders: an empty tape */
        rec_op(r, SYO_CMD, SR_NEW, 4000);
    }
    /* each recorder's own file, read by its fast play path (the same bytes Sound Recorder holds); only where the
       recorder's sound changed */
    {
        static char loaded[SY_NREC][620];
        int posted[SY_NREC];
        for (r = 0; r < SY_NREC; r++) {
            char path[MAX_PATH], key[620];
            posted[r] = 0;
            if (rec[r].layer >= 0) sprintf(path, "C:\\synth\\layer%d.wav", rec[r].layer);
            else path[0] = 0;
            sprintf(key, "%s|%s", path, rec[r].layer >= 0 ? D.l[rec[r].layer].key : "");
            if (!strcmp(key, loaded[r])) continue;
            strcpy(loaded[r], key);
            MultiByteToWideChar(CP_ACP, 0, path, -1, shm->s[r].pcmfile, 260);
            rec_op(r, SYO_LOADPCM, 0, 0);
            posted[r] = 1;
        }
        for (r = 0; r < SY_NREC; r++) if (posted[r]) WaitForSingleObject(ev_done[r], 4000);
    }
    shm->env_a = D.a; shm->env_d = D.d; shm->env_s = D.s; shm->env_r = D.r;
    built_dna = D;
    lstrcpynA(built_text, text, sizeof built_text);
    for (i = 0; i < D.n; i++)
        send_line("layer %d %d %d %d %d", i, D.l[i].first, D.l[i].count, D.l[i].src < 0 ? 0 : D.l[i].rate, D.l[i].src < 0 ? 0 : D.l[i].frames);
    send_line("built %lu", GetTickCount() - t0);
    logf_("built '%s' in %lu ms", text, GetTickCount() - t0);
    InterlockedExchange(&building, 0);
    PostMessageA(win, WM_BUILT, (WPARAM)p, 0);
    return 0;
}

static void start_build(const char *text, int from_edit)
{
    if (win && assembled) { RECT st = {0, 690, SIDE_X - 4, 768}; InvalidateRect(win, &st, TRUE); }
    if (InterlockedExchange(&building, 1)) {
        /* a build is running: take the newest DNA when it ends */
        lstrcpynA(dna_text, text, sizeof dna_text);
        return;
    }
    lstrcpynA(dna_text, text, sizeof dna_text);
    CloseHandle(CreateThread(NULL, 0, build_thread, (LPVOID)(INT_PTR)from_edit, 0, NULL));
}

/* ---------------------------------------------------------------- the lines from the plugin */
static HANDLE note_ev[SY_NREC];
/* notes go straight to each Sound Recorder's note thread (srhook.c): an event, no window message */
static void note_line(char *l)
{
    int r, rate, vol;
    if (sscanf(l, "on %d %d %d", &r, &rate, &vol) == 3) {
        if (r < 0 || r >= SY_NREC || building) return;
        shm->s[r].rate = rate;
        shm->s[r].vol = vol < 0 ? 0 : vol > 65535 ? 65535 : vol;
        shm->s[r].gate = 1;
        shm->s[r].cut = 0;
        shm->s[r].t_post = GetTickCount();
        SetEvent(note_ev[r]);
    } else if (sscanf(l, "off %d", &r) == 1) {
        if (r < 0 || r >= SY_NREC) return;
        shm->s[r].gate = 0;
    } else if (sscanf(l, "cut %d", &r) == 1) {
        if (r < 0 || r >= SY_NREC) return;
        shm->s[r].gate = 0;
        shm->s[r].cut = 1;
    } else if (!strncmp(l, "panic", 5)) {
        for (r = 0; r < SY_NREC; r++) { shm->s[r].gate = 0; shm->s[r].cut = 1; }
    }
}

static DWORD WINAPI com_thread(LPVOID p)
{
    char buf[2048], line[1400];
    int n = 0;
    DWORD got, i;
    for (;;) {
        if (com == INVALID_HANDLE_VALUE) { Sleep(1000); continue; }
        {
            static OVERLAPPED ov;
            if (!ov.hEvent) ov.hEvent = CreateEventA(NULL, TRUE, FALSE, NULL);
            ResetEvent(ov.hEvent);
            got = 0;
            if (!ReadFile(com, buf, sizeof buf, &got, &ov)) {
                if (GetLastError() != ERROR_IO_PENDING) { Sleep(50); continue; }
                if (!GetOverlappedResult(com, &ov, &got, TRUE)) { Sleep(50); continue; }
            }
        }
        for (i = 0; i < got; i++) {
            char c = buf[i];
            if (c == '\r') continue;
            if (c != '\n') { if (n < (int)sizeof line - 1) line[n++] = c; continue; }
            line[n] = 0;
            n = 0;
            /* notes are handled right here, on this thread: nothing on the window's thread can delay them */
            if (!strncmp(line, "on ", 3) || !strncmp(line, "off ", 4) || !strncmp(line, "cut ", 4) || !strncmp(line, "panic", 5))
                note_line(line);
            else
                PostMessageA(win, WM_LINE, 0, (LPARAM)_strdup(line));
        }
    }
    return 0;
}

/* ---------------------------------------------------------------- keep the sound card running */
/* a silent stream that never ends: kmixer and the AC97 never stop, so the plugin hears one steady stream and a
   note starts on a card that is already running */
static void keepalive(void)
{
    typedef MMRESULT (WINAPI *OP)(LPHWAVEOUT, UINT, LPCWAVEFORMATEX, DWORD_PTR, DWORD_PTR, DWORD);
    typedef MMRESULT (WINAPI *PH)(HWAVEOUT, LPWAVEHDR, UINT);
    HMODULE m = LoadLibraryA("winmm.dll");
    OP op = (OP)GetProcAddress(m, "waveOutOpen");
    PH ph = (PH)GetProcAddress(m, "waveOutPrepareHeader"), wr = (PH)GetProcAddress(m, "waveOutWrite");
    static WAVEHDR hd;
    static short zero[4410 * 2];
    WAVEFORMATEX f;
    HWAVEOUT h;
    f.wFormatTag = 1; f.nChannels = 2; f.nSamplesPerSec = 44100; f.wBitsPerSample = 16;
    f.nBlockAlign = 4; f.nAvgBytesPerSec = 44100 * 4; f.cbSize = 0;
    if (op(&h, WAVE_MAPPER, &f, 0, 0, 0)) { logf_("keepalive: no card"); return; }
    memset(&hd, 0, sizeof hd);
    hd.lpData = (char *)zero; hd.dwBufferLength = sizeof zero;
    hd.dwFlags = 0x4 | 0x8;               /* WHDR_BEGINLOOP | WHDR_ENDLOOP */
    hd.dwLoops = 0xFFFFFFFF;
    ph(h, &hd, sizeof hd);
    hd.dwFlags |= 0x4 | 0x8;
    hd.dwLoops = 0xFFFFFFFF;
    wr(h, &hd, sizeof hd);
}

/* ---------------------------------------------------------------- windows */
typedef struct { const char *cls, *title; DWORD pid; HWND found; } FindTop;
static BOOL CALLBACK ft_cb(HWND h, LPARAM lp)
{
    FindTop *f = (FindTop *)lp;
    char c[64], t[256];
    DWORD pid;
    GetClassNameA(h, c, sizeof c);
    if (f->cls && strcmp(c, f->cls)) return TRUE;
    GetWindowTextA(h, t, sizeof t);
    if (f->title && !strstr(t, f->title)) return TRUE;
    GetWindowThreadProcessId(h, &pid);
    if (f->pid && pid != f->pid) return TRUE;
    f->found = h;
    return FALSE;
}
static HWND wait_top(const char *cls, const char *title, DWORD pid, int ms)
{
    DWORD end = GetTickCount() + ms;
    do {
        FindTop f;
        f.cls = cls; f.title = title; f.pid = pid; f.found = NULL;
        EnumWindows(ft_cb, (LPARAM)&f);
        if (f.found) return f.found;
        Sleep(30);
    } while ((LONG)(GetTickCount() - end) < 0);
    return NULL;
}
static DWORD launch(const char *cmdline, int show)
{
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    char cl[512];
    memset(&si, 0, sizeof si);
    si.cb = sizeof si; si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = (WORD)show;
    lstrcpynA(cl, cmdline, sizeof cl);
    if (!CreateProcessA(NULL, cl, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) return 0;
    WaitForInputIdle(pi.hProcess, 8000);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    return pi.dwProcessId;
}

/* rect of a window in its parent's client coordinates */
static RECT rel_rect(HWND h)
{
    RECT r;
    POINT a, b;
    GetWindowRect(h, &r);
    a.x = r.left; a.y = r.top; b.x = r.right; b.y = r.bottom;
    if (GetParent(h) && (GetWindowLongA(h, GWL_STYLE) & WS_CHILD)) { ScreenToClient(GetParent(h), &a); ScreenToClient(GetParent(h), &b); }
    r.left = a.x; r.top = a.y; r.right = b.x; r.bottom = b.y;
    return r;
}

/* ---------------------------------------------------------------- layout (the synth window is the whole 1024x768 screen) */
static RECT kid_final[NKID];
static void final_kids(void)
{
    SetRect(&kid_final[K_PLAY], 4, 8, 4 + 48, 8 + 24);
    SetRect(&kid_final[K_STOP], 54, 8, 54 + 48, 8 + 24);
    SetRect(&kid_final[K_PFRAME], 110, 2, 110 + 60, 2 + 37);
    SetRect(&kid_final[K_PLABEL], 113, 6, 113 + 54, 6 + 16);
    SetRect(&kid_final[K_POS], 113, 23, 113 + 54, 23 + 13);
    SetRect(&kid_final[K_WAVE], 176, 2, 176 + 114, 2 + 37);
    SetRect(&kid_final[K_LFRAME], 296, 2, 296 + 60, 2 + 37);
    SetRect(&kid_final[K_LLABEL], 299, 6, 299 + 54, 6 + 16);
    SetRect(&kid_final[K_LEN], 299, 23, 299 + 54, 23 + 13);
    SetRect(&kid_final[K_TRACK], 362, 8, 362 + 196, 8 + 26);
}
static RECT strip_rect(int r)
{
    RECT x;
    SetRect(&x, STRIP_X, STRIP_Y + r * ROW_H, STRIP_X + STRIP_W, STRIP_Y + r * ROW_H + ROW_H - 1);
    return x;
}
/* the right-hand column: frames drawn by the synth window, contents placed inside */
static RECT fr_dna = {SIDE_X, 2, 1016, 94}, fr_lay = {SIDE_X, 98, 1016, 182}, fr_snd = {SIDE_X, 186, 1016, 302},
            fr_cpu = {SIDE_X, 306, 1016, 506}, fr_clk = {SIDE_X, 510, 1016, 742};

/* ---------------------------------------------------------------- the borrowed extras */
/* Task Manager's Performance page and Date and Time's Date & Time page move in whole (their drawing stays their
   own programs' work: owner-drawn graphs, an XOR-drawn clock) and show through a window onto the part we want */
static HWND tm_dlg, tm_page, dt_dlg, dt_page, port_cpu, port_clk;
static POINT off_cpu = {12, 8}, off_clk = {6, 3};       /* the wanted part's corner inside each page */
static SIZE sz_cpu = {354, 182}, sz_clk = {362, 203};
static LRESULT CALLBACK port_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_ERASEBKGND) { RECT r; GetClientRect(h, &r); FillRect((HDC)wp, &r, GetSysColorBrush(COLOR_BTNFACE)); return 1; }
    return DefWindowProcA(h, m, wp, lp);
}
static HWND page_of(HWND dlg)          /* the visible child dialog: the page */
{
    HWND c = NULL;
    while ((c = FindWindowExA(dlg, c, "#32770", NULL))) if (IsWindowVisible(c)) return c;
    return NULL;
}

/* ---------------------------------------------------------------- the synth window's own controls */
#define ID_DNA 3001
#define ID_APPLY 3002
#define ID_MUTATE 3003
#define ID_UNDO 3004
#define ID_LAYERS 3005
#define ID_SOUNDS 3006
#define ID_TITLE 3007
#define IDM_SRC 4000         /* + sound: the selected layer's source */
#define IDM_INS 4100         /* + sound: Insert File */
#define IDM_MIX 4200         /* + sound: Mix with File */
#define IDM_TUP 4301
#define IDM_TDN 4302
#define IDM_H 4310           /* + preset */
#define IDM_U 4320           /* + n */
#define IDM_POOLUP 4331
#define IDM_POOLDN 4332
#define IDM_ADDL 4341
#define IDM_DELL 4342
#define IDM_SEL 4350         /* + layer */
#define IDM_AT 4400          /* + 0..9: position 0%,10%..90% */
#define IDM_ABOUT 4500
static HWND w_dna, w_apply, w_mutate, w_undo, w_layers, w_sounds, w_lbl[SY_NREC];
static HFONT font, font_b, font_mono, font_big;
static int panel_frames;
static DWORD status_ms;
static char undo_text[1100];
static const char *h_presets[] = {"H0", "H0,12", "H0,-12", "H0,12,-12", "H0,7", "H0,4,7", "H0,3,7", "H0,7,12,19"};
static const char *h_names[] = {"Single note", "Note + octave up", "Note + octave down", "Octaves both ways", "Fifth",
                                "Major triad", "Minor triad", "Power stack"};
static COLORREF layer_col[MAXL] = {RGB(0, 84, 227), RGB(204, 51, 0), RGB(0, 140, 70), RGB(150, 60, 170),
                                   RGB(200, 140, 0), RGB(0, 150, 160), RGB(120, 120, 120), RGB(230, 60, 120)};

static HMENU make_menu(void)
{
    HMENU bar = CreateMenu(), m, sub, sub2, sub3;
    int i;
    m = CreatePopupMenu();
    AppendMenuA(m, MF_STRING, ID_APPLY, "&Apply DNA\tEnter");
    AppendMenuA(m, MF_STRING, ID_MUTATE, "&Mutate");
    AppendMenuA(m, MF_STRING, ID_UNDO, "&Undo");
    AppendMenuA(bar, MF_POPUP, (UINT_PTR)m, "&File");
    m = CreatePopupMenu();
    AppendMenuA(m, MF_STRING, SR_COPY, "&Copy");
    AppendMenuA(m, MF_STRING, SR_PASTE_INS, "&Paste Insert");
    AppendMenuA(m, MF_STRING, SR_PASTE_MIX, "Paste Mi&x");
    AppendMenuA(m, MF_SEPARATOR, 0, NULL);
    sub = CreatePopupMenu(); sub2 = CreatePopupMenu(); sub3 = CreatePopupMenu();
    for (i = 0; i < NSND; i++) {
        AppendMenuA(sub, MF_STRING | (i && i % 18 == 0 ? MF_MENUBARBREAK : 0), IDM_INS + i, snd_file[i]);
        AppendMenuA(sub2, MF_STRING | (i && i % 18 == 0 ? MF_MENUBARBREAK : 0), IDM_MIX + i, snd_file[i]);
    }
    AppendMenuA(m, MF_POPUP, (UINT_PTR)sub, "&Insert File");
    AppendMenuA(m, MF_POPUP, (UINT_PTR)sub2, "&Mix with File");
    AppendMenuA(m, MF_SEPARATOR, 0, NULL);
    for (i = 0; i < 10; i++) { char t[32]; sprintf(t, "%d%%", i * 10); AppendMenuA(sub3, MF_STRING, IDM_AT + i, t); }
    AppendMenuA(m, MF_POPUP, (UINT_PTR)sub3, "Move &Position To");
    AppendMenuA(m, MF_STRING, SR_DEL_BEFORE, "Delete &Before Current Position");
    AppendMenuA(m, MF_STRING, SR_DEL_AFTER, "Delete &After Current Position");
    AppendMenuA(bar, MF_POPUP, (UINT_PTR)m, "&Edit");
    m = CreatePopupMenu();
    AppendMenuA(m, MF_STRING, SR_VOL_UP, "&Increase Volume (by 25%)");
    AppendMenuA(m, MF_STRING, SR_VOL_DOWN, "&Decrease Volume");
    AppendMenuA(m, MF_SEPARATOR, 0, NULL);
    AppendMenuA(m, MF_STRING, SR_SPEED_UP, "I&ncrease Speed (by 100%)");
    AppendMenuA(m, MF_STRING, SR_SPEED_DOWN, "D&ecrease Speed");
    AppendMenuA(m, MF_SEPARATOR, 0, NULL);
    AppendMenuA(m, MF_STRING, SR_ECHO, "&Add Echo");
    AppendMenuA(m, MF_STRING, SR_REVERSE, "&Reverse");
    AppendMenuA(bar, MF_POPUP, (UINT_PTR)m, "Effect&s");
    m = CreatePopupMenu();
    AppendMenuA(m, MF_STRING, IDM_TUP, "Transpose &Up an Octave");
    AppendMenuA(m, MF_STRING, IDM_TDN, "Transpose &Down an Octave");
    AppendMenuA(m, MF_SEPARATOR, 0, NULL);
    for (i = 0; i < 8; i++) AppendMenuA(m, MF_STRING, IDM_H + i, h_names[i]);
    AppendMenuA(m, MF_SEPARATOR, 0, NULL);
    AppendMenuA(m, MF_STRING, IDM_U + 1, "Unison: 1 voice");
    AppendMenuA(m, MF_STRING, IDM_U + 2, "Unison: 2 voices");
    AppendMenuA(m, MF_STRING, IDM_U + 3, "Unison: 3 voices");
    AppendMenuA(m, MF_SEPARATOR, 0, NULL);
    AppendMenuA(m, MF_STRING, IDM_POOLUP, "More Recorders");
    AppendMenuA(m, MF_STRING, IDM_POOLDN, "Fewer Recorders");
    AppendMenuA(bar, MF_POPUP, (UINT_PTR)m, "&Voices");
    m = CreatePopupMenu();
    AppendMenuA(m, MF_STRING, IDM_ADDL, "&Add Layer");
    AppendMenuA(m, MF_STRING, IDM_DELL, "&Remove Layer");
    AppendMenuA(bar, MF_POPUP, (UINT_PTR)m, "&Layers");
    m = CreatePopupMenu();
    AppendMenuA(m, MF_STRING, IDM_ABOUT, "&About BASILISK SYNTH");
    AppendMenuA(bar, MF_POPUP, (UINT_PTR)m, "&Help");
    return bar;
}

/* ---------------------------------------------------------------- editing the DNA from XP */
/* layer i of t: [*b, *e) */
static int layer_span(const char *t, int li, int *b, int *e)
{
    int i = 0, k = 0, n = (int)strlen(t), semi;
    const char *sc = strchr(t, ';');
    semi = sc ? (int)(sc - t) : n;
    *b = 0;
    for (; k <= semi; k++) {
        if (k == semi || t[k] == '/') {
            if (i == li) { *e = k; return 1; }
            i++;
            *b = k + 1;
        }
    }
    return 0;
}
static int layer_count(const char *t)
{
    int n = 1;
    for (; *t && *t != ';'; t++) if (*t == '/') n++;
    return n;
}
static void str_insert(char *t, int at, const char *s)
{
    int n = (int)strlen(t), m = (int)strlen(s);
    if (n + m >= 1023) return;
    memmove(t + at + m, t + at, n - at + 1);
    memcpy(t + at, s, m);
}
static void str_cut(char *t, int a, int b) { memmove(t + a, t + b, strlen(t + b) + 1); }

/* drop every gene of kind g from layer li */
static void drop_gene(char *t, int li, char g)
{
    int b, e, k;
    if (!layer_span(t, li, &b, &e)) return;
    for (k = b; k < e; k++) {
        if (t[k] == g && !((g == 'T' || g == 'L' || g == 'H' || g == 'U' || g == 'F' || g == '#') && 0)) {
            int j = k + 1;
            if (t[k] == 'I' || t[k] == 'M') continue;
            while (j < e && ((t[j] >= '0' && t[j] <= '9') || t[j] == '-' || t[j] == ',' || t[j] == '~')) j++;
            str_cut(t, k, j);
            e -= j - k;
            k--;
        }
    }
}
static int gene_val(const char *t, int li, char g, int def)
{
    int b, e, k, v = def;
    const char *p;
    if (!layer_span(t, li, &b, &e)) return def;
    for (k = b; k < e; k++) if (t[k] == g) { p = t + k + 1; v = read_int(&p); }
    return v;
}
static void set_gene(char *t, int li, const char *gene)
{
    int b, e;
    drop_gene(t, li, gene[0]);
    if (layer_span(t, li, &b, &e)) str_insert(t, e, gene);
}
static void add_step(char *t, int li, const char *step)
{
    int b, e;
    if (layer_span(t, li, &b, &e)) str_insert(t, e, step);
}
static void set_source(char *t, int li, int s)
{
    int b, e, n = 0;
    if (!layer_span(t, li, &b, &e)) return;
    while (b + n < e && ((t[b + n] >= 'a' && t[b + n] <= 'z') || (t[b + n] >= '0' && t[b + n] <= '9'))) n++;
    str_cut(t, b, b + n);
    str_insert(t, b, snd_name[s]);
}

static void refresh_panel(void);
static void edit_dna(const char *t)
{
    lstrcpynA(undo_text, built_text, sizeof undo_text);
    SetWindowTextA(w_dna, t);
    start_build(t, 1);
    refresh_panel();
}

static void mutate(char *t)
{
    static const char ops[] = "+-><ER[]CPX";
    int nl = layer_count(t), li = rand() % nl, k = rand() % 6;
    char s[16];
    if (k <= 2) { s[0] = ops[rand() % (sizeof ops - 1)]; s[1] = 0; if (s[0] == '<' && rand() % 2) strcpy(s, "@50"); add_step(t, li, s); }
    else if (k == 3) set_source(t, li, rand() % NSND);
    else if (k == 4) { sprintf(s, "%s", h_presets[rand() % 8]); set_gene(t, li, s); }
    else { sprintf(s, "M%s", snd_name[rand() % NSND]); add_step(t, li, s); }
}

static void on_menu(int id)
{
    char t[1100];
    char s[64];
    int li = sel_layer;
    GetWindowTextA(w_dna, t, sizeof t);
    if (li >= layer_count(t)) li = 0;
    switch (id) {
    case ID_APPLY: edit_dna(t); return;
    case ID_UNDO: if (undo_text[0]) { lstrcpynA(t, undo_text, sizeof t); edit_dna(t); } return;
    case ID_MUTATE: mutate(t); edit_dna(t); return;
    case SR_VOL_UP: add_step(t, li, "+"); break;
    case SR_VOL_DOWN: add_step(t, li, "-"); break;
    case SR_SPEED_UP: add_step(t, li, ">"); break;
    case SR_SPEED_DOWN: add_step(t, li, "<"); break;
    case SR_ECHO: add_step(t, li, "E"); break;
    case SR_REVERSE: add_step(t, li, "R"); break;
    case SR_COPY: add_step(t, li, "C"); break;
    case SR_PASTE_INS: add_step(t, li, "P"); break;
    case SR_PASTE_MIX: add_step(t, li, "X"); break;
    case SR_DEL_BEFORE: add_step(t, li, "["); break;
    case SR_DEL_AFTER: add_step(t, li, "]"); break;
    case IDM_TUP: case IDM_TDN:
        sprintf(s, "T%d", gene_val(t, li, 'T', 0) + (id == IDM_TUP ? 12 : -12));
        set_gene(t, li, s);
        break;
    case IDM_POOLUP: case IDM_POOLDN: {
        int c = li < built_dna.n ? built_dna.l[li].count : 4;
        c += id == IDM_POOLUP ? 1 : -1;
        if (c < 1) c = 1;
        if (c > 16) c = 16;
        sprintf(s, "#%d", c);
        set_gene(t, li, s);
        break;
    }
    case IDM_ADDL:
        if (layer_count(t) < MAXL) { int b, e; layer_span(t, layer_count(t) - 1, &b, &e); str_insert(t, e, "/xpding"); li = layer_count(t) - 1; sel_layer = li; }
        break;
    case IDM_DELL:
        if (layer_count(t) > 1) { int b, e; layer_span(t, li, &b, &e); if (b > 0) str_cut(t, b - 1, e); else str_cut(t, b, e + 1); sel_layer = 0; }
        break;
    case IDM_ABOUT:
        MessageBoxA(win, "BASILISK SYNTH " VERSION "\n\nSixteen Windows XP Sound Recorders, played from your DAW.\n"
                    "Every note is a real sndrec32.exe; every effect is its own Effects menu.\n\nwilliamsharkey.com", "About BASILISK SYNTH", MB_OK);
        return;
    default:
        if (id >= IDM_SRC && id < IDM_SRC + NSND) set_source(t, li, id - IDM_SRC);
        else if (id >= IDM_INS && id < IDM_INS + NSND) { sprintf(s, "I%s", snd_name[id - IDM_INS]); add_step(t, li, s); }
        else if (id >= IDM_MIX && id < IDM_MIX + NSND) { sprintf(s, "M%s", snd_name[id - IDM_MIX]); add_step(t, li, s); }
        else if (id >= IDM_H && id < IDM_H + 8) set_gene(t, li, h_presets[id - IDM_H]);
        else if (id >= IDM_U + 1 && id <= IDM_U + 3) { sprintf(s, "U%d~%d", id - IDM_U, id == IDM_U + 1 ? 0 : 10); set_gene(t, li, s); }
        else if (id >= IDM_AT && id < IDM_AT + 10) { sprintf(s, "@%d", (id - IDM_AT) * 10); add_step(t, li, s); }
        else return;
    }
    edit_dna(t);
}

static void refresh_panel(void)
{
    int i, r;
    char t[1100], line[160];
    GetWindowTextA(w_dna, t, sizeof t);
    SendMessageA(w_layers, LB_RESETCONTENT, 0, 0);
    for (i = 0; i < layer_count(t); i++) {
        int b, e;
        layer_span(t, i, &b, &e);
        sprintf(line, "Layer %d:  ", i + 1);
        lstrcpynA(line + strlen(line), t + b, e - b + 1 < 120 ? e - b + 1 : 120);
        SendMessageA(w_layers, LB_ADDSTRING, 0, (LPARAM)line);
    }
    SendMessageA(w_layers, LB_SETCURSEL, sel_layer, 0);
    for (r = 0; r < SY_NREC; r++) if (w_lbl[r]) InvalidateRect(w_lbl[r], NULL, TRUE);
}

/* ---------------------------------------------------------------- the window */
static LRESULT CALLBACK lbl_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(h, &ps);
        RECT rc;
        int r = GetDlgCtrlID(h) - 100, l = rec[r].layer;
        char t[8];
        HBRUSH b;
        GetClientRect(h, &rc);
        b = CreateSolidBrush(l >= 0 ? layer_col[l % MAXL] : RGB(160, 160, 160));
        FillRect(dc, &rc, b);
        DeleteObject(b);
        if (l == sel_layer) { RECT x = rc; x.left = x.right - 3; FillRect(dc, &x, (HBRUSH)GetStockObject(WHITE_BRUSH)); }
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, RGB(255, 255, 255));
        SelectObject(dc, font_b);
        sprintf(t, "%d", r + 1);
        DrawTextA(dc, t, -1, &rc, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
        EndPaint(h, &ps);
        return 0;
    }
    if (m == WM_LBUTTONDOWN) {
        int r = GetDlgCtrlID(h) - 100;
        if (rec[r].layer >= 0) { sel_layer = rec[r].layer; refresh_panel(); }
        return 0;
    }
    return DefWindowProcA(h, m, wp, lp);
}

static WNDPROC old_edit;
static LRESULT CALLBACK dna_edit_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_CHAR && wp == '\r') { on_menu(ID_APPLY); return 0; }
    if (m == WM_GETDLGCODE) return DLGC_WANTALLKEYS | CallWindowProcA(old_edit, h, m, wp, lp);
    return CallWindowProcA(old_edit, h, m, wp, lp);
}

static LRESULT CALLBACK wnd_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == msg_done) {
        int r = (int)wp, op = (int)(lp & 255);
        if (r >= 0 && r < SY_NREC) {
            if (op == SYE_END) { if (assembled) send_line("end %d", r); }
            else if (op == SYE_OPEN) send_line("log open %d %ld", r, (LONG)(lp >> 8));   /* ms from the line to the card */
            else if (op != SYE_OPEN) { SetEvent(ev_done[r]); if (building) logf_("  done %d op %d", r, op); }
        }
        return 0;
    }
    switch (m) {
    case WM_LINE: {
        char *l = (char *)lp;
        if (!strncmp(l, "hi", 2)) send_line("hi 1 xp %s", assembled ? "ready" : "wait");
        else if (!strncmp(l, "dna ", 4)) { SetWindowTextA(w_dna, l + 4); refresh_panel(); start_build(l + 4, 0); }
        else if (!strncmp(l, "env ", 4)) {
            int a, d, s, r;
            if (sscanf(l + 4, "%d %d %d %d", &a, &d, &s, &r) == 4) { shm->env_a = a; shm->env_d = d; shm->env_s = s; shm->env_r = r; }
        } else if (!strncmp(l, "sel ", 4)) { sel_layer = atoi(l + 4); refresh_panel(); }
        else if (!strncmp(l, "time ", 5)) {
            SYSTEMTIME st;
            int y, mo, d, hh, mi, s;
            if (sscanf(l + 5, "%d %d %d %d %d %d", &y, &mo, &d, &hh, &mi, &s) == 6) {
                /* SetLocalTime needs SeSystemtimePrivilege switched on (advapi32 through GetProcAddress: tcc has no import lib) */
                typedef BOOL (WINAPI *OPT)(HANDLE, DWORD, PHANDLE);
                typedef BOOL (WINAPI *LPV)(LPCSTR, LPCSTR, PLUID);
                typedef BOOL (WINAPI *ATP)(HANDLE, BOOL, PTOKEN_PRIVILEGES, DWORD, PTOKEN_PRIVILEGES, PDWORD);
                HMODULE adv = LoadLibraryA("advapi32.dll");
                OPT opt = (OPT)GetProcAddress(adv, "OpenProcessToken");
                LPV lpv = (LPV)GetProcAddress(adv, "LookupPrivilegeValueA");
                ATP atp = (ATP)GetProcAddress(adv, "AdjustTokenPrivileges");
                HANDLE tok;
                TOKEN_PRIVILEGES tp;
                if (opt && lpv && atp && opt(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, &tok)) {
                    tp.PrivilegeCount = 1;
                    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;
                    if (lpv(NULL, "SeSystemtimePrivilege", &tp.Privileges[0].Luid)) atp(tok, FALSE, &tp, 0, NULL, NULL);
                    CloseHandle(tok);
                }
                memset(&st, 0, sizeof st);
                st.wYear = y; st.wMonth = mo; st.wDay = d; st.wHour = hh; st.wMinute = mi; st.wSecond = s;
                SetLocalTime(&st);
            }
        } else if (!strncmp(l, "go", 2)) PostMessageA(h, WM_APP + 9, 0, 0);
        free(l);
        return 0;
    }
    case WM_BUILT:
        { RECT st = {0, 690, SIDE_X - 4, 768}; InvalidateRect(h, &st, TRUE); }
        if (wp) send_line("edit %s", built_text);
        if (strcmp(dna_text, built_text)) start_build(dna_text, (int)wp);   /* a newer one came in meanwhile */
        refresh_panel();
        return 0;
    case WM_COMMAND: {
        int id = LOWORD(wp), code = HIWORD(wp), r;
        /* a strip's own buttons and slider were reparented here, so their clicks arrive here: hand them back */
        for (r = 0; r < SY_NREC; r++) {
            if (lp && (HWND)lp == rec[r].kid[K_PLAY]) { shm->s[r].rate = 0; shm->s[r].vol = 65535; shm->s[r].gate = 1; PostMessageA(rec[r].w, msg_op, SYO_PLAY, 0); return 0; }
            if (lp && (HWND)lp == rec[r].kid[K_STOP]) { shm->s[r].gate = 0; PostMessageA(rec[r].w, msg_op, SYO_CUT, 0); return 0; }
        }
        if (id == ID_LAYERS && code == LBN_SELCHANGE) { sel_layer = (int)SendMessageA(w_layers, LB_GETCURSEL, 0, 0); refresh_panel(); return 0; }
        if (id == ID_SOUNDS && code == LBN_DBLCLK) { on_menu(IDM_SRC + (int)SendMessageA(w_sounds, LB_GETCURSEL, 0, 0)); return 0; }
        if (code == 0 || code == BN_CLICKED) on_menu(id);
        return 0;
    }
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(h, &ps);
        RECT fr[5] = {fr_dna, fr_lay, fr_snd, fr_cpu, fr_clk}, rc;
        const char *ttl[5] = {"DNA", "Layers", "Sounds - double-click to make one the layer's source", "This machine (Task Manager)", "Date and Time"};
        int i;
        char st[200];
        SetBkMode(dc, TRANSPARENT);
        SelectObject(dc, font);
        if (panel_frames) for (i = 0; i < 5; i++) {
            RECT e = fr[i];
            SIZE tz;
            e.top += 6;
            DrawEdge(dc, &e, EDGE_ETCHED, BF_RECT);
            GetTextExtentPoint32A(dc, ttl[i], (int)strlen(ttl[i]), &tz);
            rc.left = e.left + 6; rc.top = fr[i].top; rc.right = rc.left + tz.cx + 6; rc.bottom = rc.top + 14;
            FillRect(dc, &rc, GetSysColorBrush(COLOR_BTNFACE));
            SetTextColor(dc, RGB(0, 70, 213));
            TextOutA(dc, rc.left + 3, rc.top, ttl[i], (int)strlen(ttl[i]));
        }
        /* the maker's plate, under the strips */
        SetTextColor(dc, RGB(0, 51, 153));
        SelectObject(dc, font_big);
        TextOutA(dc, STRIP_X + 2, 668, "BASILISK SYNTH", 14);
        SelectObject(dc, font);
        SetTextColor(dc, RGB(80, 80, 80));
        sprintf(st, "Sixteen Sound Recorders, one instrument.   %s", assembled ? (building ? "Changing tapes..." : "Ready.") : "");
        TextOutA(dc, STRIP_X + 4, 700, st, (int)strlen(st));
        if (assembled && status_ms) {
            sprintf(st, "Assembled in %.1f s.   Every note is a real sndrec32.exe; every effect is its own Effects menu.", status_ms / 1000.0);
            TextOutA(dc, STRIP_X + 4, 716, st, (int)strlen(st));
        }
        EndPaint(h, &ps);
        return 0;
    }
    case WM_CTLCOLORSTATIC:
        SetBkMode((HDC)wp, TRANSPARENT);
        return (LRESULT)GetSysColorBrush(COLOR_BTNFACE);
    case WM_APP + 9: {
        extern void assemble(void);
        assemble();
        return 0;
    }
    case WM_CLOSE: return 0;        /* the synth is the machine: it does not close */
    }
    return DefWindowProcA(h, m, wp, lp);
}

static HWND mk(const char *cls, const char *text, DWORD st, int x, int y, int w, int h, int id, HFONT f)
{
    HWND c = CreateWindowExA(!strcmp(cls, "EDIT") || !strcmp(cls, "LISTBOX") ? WS_EX_CLIENTEDGE : 0, cls, text,
                             WS_CHILD | st, x, y, w, h, win, (HMENU)(INT_PTR)id, inst, NULL);
    SendMessageA(c, WM_SETFONT, (WPARAM)(f ? f : font), TRUE);
    return c;
}

static void make_window(void)
{
    WNDCLASSA wc;
    int i, x = SIDE_X + 8, W = SIDE_W - 16;
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = wnd_proc; wc.hInstance = inst; wc.lpszClassName = "BasiliskSynth";
    wc.hbrBackground = GetSysColorBrush(COLOR_BTNFACE); wc.hCursor = LoadCursorA(NULL, IDC_ARROW);
    RegisterClassA(&wc);
    wc.lpfnWndProc = lbl_proc; wc.lpszClassName = "BasiliskRow"; wc.hbrBackground = NULL;
    RegisterClassA(&wc);
    wc.lpfnWndProc = port_proc; wc.lpszClassName = "BasiliskPort"; wc.hbrBackground = NULL;
    RegisterClassA(&wc);
    font = CreateFontA(-11, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Tahoma");
    font_b = CreateFontA(-11, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Tahoma");
    font_mono = CreateFontA(-12, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Lucida Console");
    font_big = CreateFontA(-26, 0, 0, 0, 700, 1, 0, 0, 0, 0, 0, 0, 0, "Trebuchet MS");
    win = CreateWindowExA(0, "BasiliskSynth", "BASILISK SYNTH", WS_POPUP | WS_CLIPCHILDREN,
                          0, 0, 1024, 768, NULL, make_menu(), inst, NULL);
    for (i = 0; i < SY_NREC; i++) {
        RECT s = strip_rect(i);
        w_lbl[i] = CreateWindowExA(0, "BasiliskRow", "", WS_CHILD, 6, s.top + 2, 22, ROW_H - 5, win, (HMENU)(INT_PTR)(100 + i), inst, NULL);
    }
    w_dna = mk("EDIT", DEFAULT_DNA, ES_MULTILINE | ES_AUTOVSCROLL | WS_VSCROLL | WS_TABSTOP, x, fr_dna.top + 16, W, 42, ID_DNA, font_mono);
    old_edit = (WNDPROC)SetWindowLongA(w_dna, GWL_WNDPROC, (LONG)dna_edit_proc);
    w_apply = mk("BUTTON", "&Apply", BS_PUSHBUTTON | WS_TABSTOP, x, fr_dna.top + 63, 75, 23, ID_APPLY, NULL);
    w_mutate = mk("BUTTON", "&Mutate", BS_PUSHBUTTON | WS_TABSTOP, x + 80, fr_dna.top + 63, 75, 23, ID_MUTATE, NULL);
    w_undo = mk("BUTTON", "&Undo", BS_PUSHBUTTON | WS_TABSTOP, x + 160, fr_dna.top + 63, 75, 23, ID_UNDO, NULL);
    w_layers = mk("LISTBOX", "", LBS_NOTIFY | WS_VSCROLL | WS_TABSTOP | LBS_NOINTEGRALHEIGHT, x, fr_lay.top + 16, W, fr_lay.bottom - fr_lay.top - 24, ID_LAYERS, NULL);
    w_sounds = mk("LISTBOX", "", LBS_NOTIFY | WS_HSCROLL | WS_TABSTOP | LBS_NOINTEGRALHEIGHT | LBS_MULTICOLUMN, x, fr_snd.top + 16, W, fr_snd.bottom - fr_snd.top - 24, ID_SOUNDS, NULL);
    SendMessageA(w_sounds, LB_SETCOLUMNWIDTH, (W - 4) / 2, 0);
    for (i = 0; i < NSND; i++) SendMessageA(w_sounds, LB_ADDSTRING, 0, (LPARAM)snd_file[i]);
    port_cpu = CreateWindowExA(0, "BasiliskPort", "", WS_CHILD | WS_CLIPCHILDREN, SIDE_X + (SIDE_W - sz_cpu.cx) / 2, fr_cpu.top + 14, sz_cpu.cx, sz_cpu.cy, win, NULL, inst, NULL);
    port_clk = CreateWindowExA(0, "BasiliskPort", "", WS_CHILD | WS_CLIPCHILDREN, SIDE_X + (SIDE_W - sz_clk.cx) / 2, fr_clk.top + 16, sz_clk.cx, sz_clk.cy, win, NULL, inst, NULL);
}

/* ---------------------------------------------------------------- assembly */
/* one visible change at a time, per recorder; recorders start 120 ms apart, so many move at once */
typedef struct { int t, kind, r, done; } Ev;
#define EV_NOMENU 1
#define EV_STRIP 2
#define EV_DROP 3
#define EV_FLY 4
#define EV_LBL 5
#define EV_PANEL 6
#define EV_PORT 7       /* r: 0 Task Manager, 1 Date and Time: the page moves into its port */
#define EV_PORTFLY 8
#define EV_TRAY 9
#define EV_MORPH 10
#define EV_GLIDE 11
#define MORPH_MS 100
#define GLIDE_MS 120
#define STEP_MS 70
static Ev ev[160];
static int nev;
static void add_ev(int t, int kind, int r) { ev[nev].t = t; ev[nev].kind = kind; ev[nev].r = r; ev[nev].done = 0; nev++; }
static double ease(double x) { return x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) * (-2 * x + 2) * (-2 * x + 2) / 2; }

typedef struct { HWND h; RECT a, b; int t0, dur, on; } Glide;
static Glide gl[2];
#define FLY_MS 520

/* the page goes into its port, which sits exactly where that part of the page is on screen now */
static void page_to_port(int which)
{
    HWND dlg = which ? dt_dlg : tm_dlg, page = which ? dt_page : tm_page, port = which ? port_clk : port_cpu;
    POINT off = which ? off_clk : off_cpu, pc;
    SIZE sz = which ? sz_clk : sz_cpu;
    RECT pr;
    if (!page) return;
    GetWindowRect(page, &pr);
    pc.x = pr.left + off.x; pc.y = pr.top + off.y;
    ScreenToClient(win, &pc);
    gl[which].h = port;
    SetRect(&gl[which].a, pc.x, pc.y, pc.x + sz.cx, pc.y + sz.cy);
    gl[which].b = which ? (RECT){SIDE_X + (SIDE_W - sz_clk.cx) / 2, fr_clk.top + 16, 0, 0} : (RECT){SIDE_X + (SIDE_W - sz_cpu.cx) / 2, fr_cpu.top + 14, 0, 0};
    gl[which].b.right = gl[which].b.left + sz.cx; gl[which].b.bottom = gl[which].b.top + sz.cy;
    SetWindowPos(port, HWND_TOP, pc.x, pc.y, sz.cx, sz.cy, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    SetWindowLongA(page, GWL_STYLE, (GetWindowLongA(page, GWL_STYLE) & ~WS_POPUP) | WS_CHILD);
    SetParent(page, port);
    SetWindowPos(page, NULL, -off.x, -off.y, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
    ShowWindow(dlg, SW_HIDE);
    /* painted in full, by its own program, before it moves at all */
    RedrawWindow(page, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_FRAME | RDW_UPDATENOW);
    UpdateWindow(port);
}

static void run_ev(Ev *e)
{
    int r = e->r;
    switch (e->kind) {
    case EV_TRAY: ShowWindow(FindWindowA("Shell_TrayWnd", NULL), SW_HIDE); break;
    case EV_NOMENU: rec_op(r, SYO_NOMENU, 0, 0); break;
    case EV_STRIP: rec_op(r, SYO_STRIP, 0, 0); break;
    case EV_DROP: rec_op(r, SYO_DROP, 0, 0); break;
    case EV_FLY: {
        RECT s = strip_rect(r);
        shm->s[r].fly[0] = s.left; shm->s[r].fly[1] = s.top; shm->s[r].fly[2] = s.right - s.left; shm->s[r].fly[3] = s.bottom - s.top;
        rec_op(r, SYO_FLY, FLY_MS, 0);
        break;
    }
    case EV_MORPH: {
        RECT st = strip_rect(r);
        shm->s[r].fly[0] = st.left; shm->s[r].fly[1] = st.top; shm->s[r].fly[2] = st.right - st.left; shm->s[r].fly[3] = st.bottom - st.top;
        rec_op(r, SYO_MORPH, MORPH_MS, 0);
        break;
    }
    case EV_GLIDE: rec_op(r, SYO_GLIDE, GLIDE_MS, 0); break;
    case EV_LBL: ShowWindow(w_lbl[r], SW_SHOWNA); UpdateWindow(w_lbl[r]); break;
    case EV_PANEL: {
        HWND p[] = {w_dna, w_apply, w_mutate, w_undo, w_layers, w_sounds};
        if (r < 6) { ShowWindow(p[r], SW_SHOWNA); UpdateWindow(p[r]); }
        if (r == 0) { panel_frames = 1; InvalidateRect(win, NULL, FALSE); }
        break;
    }
    case EV_PORT: page_to_port(r); break;
    case EV_PORTFLY: gl[r].dur = 420; gl[r].on = 1; break;
    }
}

/* wait for an event on the window's own thread, still handling messages (the "done" replies come as messages) */
static void wait_pump(HANDLE h, DWORD ms)
{
    DWORD end = GetTickCount() + ms;
    for (;;) {
        MSG m;
        LONG left = (LONG)(end - GetTickCount());
        if (left <= 0) return;
        if (MsgWaitForMultipleObjects(1, &h, FALSE, (DWORD)left, QS_ALLINPUT) == WAIT_OBJECT_0) return;
        while (PeekMessageA(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessageA(&m); }
    }
}

void assemble(void)
{
    DWORD t0;
    int r, t, end, i;
    if (assembled) { send_line("ready"); return; }
    logf_("go");
    nev = 0;
    final_kids();
    memcpy(shm->kid_final, kid_final, sizeof kid_final[0] * 10);
    add_ev(0, EV_TRAY, 0);
    for (r = 0; r < SY_NREC; r++) {
        /* a wave across the desktop: each loses its menu bar, then its frame, then the buttons it won't need ... */
        int a = 30 + r * 28;
        add_ev(a, EV_NOMENU, r);
        add_ev(a + 50, EV_STRIP, r);
        add_ev(a + 100, EV_DROP, r);
        /* ... then one at a time (only one strip ever moves while the next one reshapes, so every window has the
           time to repaint what a moving one uncovers): its parts slide into a row where it stands, and the finished
           strip glides to its place */
        add_ev(620 + r * STEP_MS, EV_MORPH, r);
        add_ev(620 + r * STEP_MS + MORPH_MS + 10, EV_GLIDE, r);
    }
    end = 0x7fffffff;
    /* the synth window comes up under everything: an empty case, the same colour as the parts */
    SetWindowPos(win, HWND_BOTTOM, 0, 0, 1024, 768, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    UpdateWindow(win);
    /* the conductor paints the case: it must never fall behind sixteen recorders busy moving themselves */
    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_ABOVE_NORMAL);
    t0 = GetTickCount();
    {
        int flying[SY_NREC], landed = 0, phase_b = 0, last_sweep = -1;
        memset(flying, 0, sizeof flying);
        for (;;) {
            MSG m;
            t = (int)(GetTickCount() - t0);
            for (i = 0; i < nev; i++) if (!ev[i].done && t >= ev[i].t) {
                ev[i].done = 1;
                run_ev(&ev[i]);
                if (ev[i].kind == EV_GLIDE) flying[ev[i].r] = 1;
                if (ev[i].kind == EV_PORTFLY) gl[ev[i].r].t0 = t;
            }
            for (r = 0; r < SY_NREC; r++) if (flying[r] == 1 && WaitForSingleObject(ev_done[r], 0) == WAIT_OBJECT_0) {
                flying[r] = 2; landed++;
                ShowWindow(w_lbl[r], SW_SHOWNA); UpdateWindow(w_lbl[r]);
            }
            /* the borrowed pages move in once every strip has landed: nothing flies over them after that */
            /* the borrowed pages move in as the last strip leaves their side of the screen */
            if (!phase_b && (landed >= SY_NREC - 1 || t > 6000)) {
                phase_b = 1;
                add_ev(t, EV_PORT, 0); add_ev(t + 30, EV_PORTFLY, 0);
                add_ev(t + 90, EV_PORT, 1); add_ev(t + 120, EV_PORTFLY, 1);
                for (i = 0; i < 6; i++) add_ev(t + 240 + i * 35, EV_PANEL, i);
                end = t + 560;
            }
            for (i = 0; i < 2; i++) if (gl[i].on && gl[i].h) {
                double x = ease((double)(t - gl[i].t0) / gl[i].dur);
                SetWindowPos(gl[i].h, NULL, gl[i].a.left + (int)((gl[i].b.left - gl[i].a.left) * x), gl[i].a.top + (int)((gl[i].b.top - gl[i].a.top) * x),
                             0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
                UpdateWindow(win);
                if (x >= 1) {
                    HWND pg = i ? dt_page : tm_page;
                    gl[i].on = 0;
                    if (pg) RedrawWindow(pg, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_FRAME | RDW_UPDATENOW);
                }
            }
            while (PeekMessageA(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessageA(&m); }
            /* the case under the parts is repainted every tenth of a second whether or not Windows thinks it must:
               a recorder that stops being a top-level window does not always hand back the pixels it covered */
            if (t / 100 != last_sweep) { last_sweep = t / 100; InvalidateRect(win, NULL, TRUE); }
            UpdateWindow(win);
            if (t >= end && !gl[0].on && !gl[1].on) break;
            Sleep(10);
        }
    }
    for (r = 0; r < SY_NREC; r++) wait_pump(ev_done[r], 1500);    /* the last flights */
    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_NORMAL);
    /* every strip exactly in place (a recorder that missed a step on a slow machine is put right), painted whole */
    for (r = 0; r < SY_NREC; r++) {
        RECT st = strip_rect(r);
        shm->s[r].fly[0] = st.left; shm->s[r].fly[1] = st.top; shm->s[r].fly[2] = st.right - st.left; shm->s[r].fly[3] = st.bottom - st.top;
        rec_op(r, SYO_SNAP, 0, 0);
    }
    for (r = 0; r < SY_NREC; r++) wait_pump(ev_done[r], 1500);
    /* one settling repaint of the borrowed pages (their group boxes are transparent and missed some erases) */
    SetForegroundWindow(win);
    SetFocus(w_dna);
    assembled = 1;
    send_line("ready");
    status_ms = GetTickCount() - t0;
    logf_("assembled in %lu ms", GetTickCount() - t0);
    refresh_panel();
    InvalidateRect(win, NULL, FALSE);
}

/* ---------------------------------------------------------------- startup */
static void hook_rec(int r, HMODULE dll, HOOKPROC hp)
{
    shm->s[r].pid = rec[r].pid;
    shm->s[r].hwnd = (LONG)rec[r].w;
    SetWindowsHookExA(WH_GETMESSAGE, hp, dll, rec[r].tid);
    PostMessageA(rec[r].w, WM_NULL, 0, 0);
}

int WINAPI WinMain(HINSTANCE hi, HINSTANCE hp_, LPSTR cmd, int show)
{
    HANDLE map;
    HMODULE dll;
    HOOKPROC hp;
    int r, i;
    MSG m;
    char path[MAX_PATH];
    inst = hi;
    logf_("synth %s starting", VERSION);
    InitializeCriticalSection(&com_cs);
    map = CreateFileMappingA(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0, sizeof(SyShm), SY_SHM);
    shm = (SyShm *)MapViewOfFile(map, FILE_MAP_ALL_ACCESS, 0, 0, sizeof(SyShm));
    memset(shm, 0, sizeof *shm);
    shm->magic = SY_MAGIC;
    shm->env_s = 100; shm->env_r = 120;
    msg_op = RegisterWindowMessageA(SY_MSG);
    msg_done = RegisterWindowMessageA(SY_DONE);
    for (r = 0; r < SY_NREC; r++) {
        char n[64];
        ev_done[r] = CreateEventA(NULL, TRUE, FALSE, NULL);
        sprintf(n, SY_NOTE_EV, r);
        note_ev[r] = CreateEventA(NULL, FALSE, FALSE, n);
    }
    for (i = 0; i < NSND; i++) { int rate, fr; media_path(path, i); snd_ms[i] = wav_info(path, &rate, &fr) && rate ? (int)((double)fr * 1000 / rate) : 1000; }
    make_window();
    shm->synth_hwnd = (LONG)win;
    keepalive();
    open_com();
    tx_ev = CreateEventA(NULL, FALSE, FALSE, NULL);
    CloseHandle(CreateThread(NULL, 0, com_thread, NULL, 0, NULL));
    CloseHandle(CreateThread(NULL, 0, tx_thread, NULL, 0, NULL));

    /* the donors of the extras first, low on the desktop, under where the recorders will be */
    {
        DWORD pid = launch("rundll32.exe shell32.dll,Control_RunDLL timedate.cpl", SW_SHOWNOACTIVATE);
        dt_dlg = wait_top("#32770", "Date and Time", 0, 20000);
        if (dt_dlg) { SetWindowPos(dt_dlg, HWND_BOTTOM, 24, 404, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE); Sleep(300); dt_page = page_of(dt_dlg); }
        logf_("date and time %p page %p (pid %lu)", dt_dlg, dt_page, pid);
    }
    {
        HWND tab;
        launch("taskmgr.exe", SW_SHOWNOACTIVATE);
        tm_dlg = wait_top("#32770", "Windows Task Manager", 0, 20000);
        if (tm_dlg) {
            tab = GetDlgItem(tm_dlg, 1000);
            SendMessageA(tab, 0x1300 + 48, 2, 0);          /* TCM_SETCURFOCUS: the Performance tab */
            Sleep(400);
            SetWindowPos(tm_dlg, HWND_BOTTOM, 600, 300, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);
            tm_page = page_of(tm_dlg);
        }
        logf_("task manager %p page %p", tm_dlg, tm_page);
    }

    /* sixteen Sound Recorders, tiled over the desktop */
    dll = LoadLibraryA("C:\\synth\\srhook.dll");
    hp = (HOOKPROC)GetProcAddress(dll, "GetMsgProc");
    if (!hp) hp = (HOOKPROC)GetProcAddress(dll, "_GetMsgProc@12");
    for (r = 0; r < SY_NREC; r++) {
        char cl[300];
        sprintf(cl, "sndrec32.exe \"C:\\WINDOWS\\Media\\%s\"", snd_file[r % 2 ? 2 : 1]);
        rec[r].pid = launch(cl, SW_SHOWNOACTIVATE);
        rec[r].w = wait_top("SoundRec", NULL, rec[r].pid, 10000);
        rec[r].tid = GetWindowThreadProcessId(rec[r].w, NULL);
        rec[r].layer = -1;
        SetWindowPos(rec[r].w, HWND_TOP, 14 + (r % 4) * 246, 10 + (r / 4) * 148, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);
        hook_rec(r, dll, hp);
        logf_("rec %d pid %lu hwnd %p", r, rec[r].pid, rec[r].w);
    }
    Sleep(300);
    start_build(DEFAULT_DNA, 0);
    while (GetMessageA(&m, NULL, 0, 0) > 0) {
        if (!IsDialogMessageA(win, &m)) { TranslateMessage(&m); DispatchMessageA(&m); }
    }
    return 0;
}
