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

#define VERSION "1.2"
#define ROW_H 34
#define STRIP_X 30
#define STRIP_Y 6
#define STRIP_W 562
#define SIDE_X (STRIP_X + STRIP_W + 14)
#define SIDE_W (1016 - SIDE_X)
#define NSND 35
#define MAXSND 2048
#define MAXL 8
#define MAXSTEP 64
#define MAXLEN_MS 30000
#define WM_LINE (WM_APP + 1)
#define WM_BUILT (WM_APP + 2)

/* ---------------------------------------------------------------- the sounds (DNA.md 2.4) */
static const char *snd_name[MAXSND] = {
    "chimes", "chord", "ding", "notify", "recycle", "ringin", "ringout", "start", "tada",
    "balloon", "batcrit", "batlow", "critstop", "default", "xpding", "error", "exclaim", "hwfail", "hwin", "hwout",
    "infobar", "logoff", "logon", "menu", "minimize", "xpnotify", "popup", "print", "xprecycle", "restore",
    "xpringin", "xpringout", "shutdown", "startup", "xpstart"};
static const char *snd_file[MAXSND] = {
    "chimes.wav", "chord.wav", "ding.wav", "notify.wav", "recycle.wav", "ringin.wav", "ringout.wav", "start.wav", "tada.wav",
    "Windows XP Balloon.wav", "Windows XP Battery Critical.wav", "Windows XP Battery Low.wav", "Windows XP Critical Stop.wav",
    "Windows XP Default.wav", "Windows XP Ding.wav", "Windows XP Error.wav", "Windows XP Exclamation.wav",
    "Windows XP Hardware Fail.wav", "Windows XP Hardware Insert.wav", "Windows XP Hardware Remove.wav",
    "Windows XP Information Bar.wav", "Windows XP Logoff Sound.wav", "Windows XP Logon Sound.wav",
    "Windows XP Menu Command.wav", "Windows XP Minimize.wav", "Windows XP Notify.wav", "Windows XP Pop-up Blocked.wav",
    "Windows XP Print complete.wav", "Windows XP Recycle.wav", "Windows XP Restore.wav", "Windows XP Ringin.wav",
    "Windows XP Ringout.wav", "Windows XP Shutdown.wav", "Windows XP Startup.wav", "Windows XP Start.wav"};
static int snd_ms[MAXSND];    /* lengths, read from the files once */
/* v2: the library disc (DNA.md 5.6) extends the table: names after the built-in ones, paths on the disc */
static int nsnd = NSND;
static const char *snd_cat[MAXSND];
static char lib_root[8];

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
static RECT plate_rc = {176, 551, SIDE_X - 52, 566};   /* the maker's plate, on the envelope editor's edge */

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
    while ((p[n] >= 'a' && p[n] <= 'z') || (p[n] >= '0' && p[n] <= '9') || p[n] == '_') n++;
    *len = n;
    for (i = 0; i < nsnd; i++) if ((int)strlen(snd_name[i]) == n && !strncmp(p, snd_name[i], n)) return i;
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
                if (*p == 't') { p++; st.op = 't'; st.arg = read_int(&p); if (st.arg < 0) st.arg = 0; if (st.arg > MAXLEN_MS) st.arg = MAXLEN_MS; }
                else {
                    st.arg = read_int(&p);
                    if (st.arg < 0) st.arg = 0;
                    if (st.arg > 99) st.arg = 99;
                }
                if (L->nstep < MAXSTEP) L->step[L->nstep++] = st;
                break;
            case 'I': case 'M':
                st.arg = snd_find(p, &len);
                p += len;
                if (st.arg >= 0 && L->nstep < MAXSTEP) L->step[L->nstep++] = st;
                break;
            case '#': L->pool = read_int(&p); if (L->pool < 1) L->pool = 1; if (L->pool > 16) L->pool = 16; break;
            case 'T': case 'L': case 'O': case 'Q': read_int(&p); break;
            case 'J': if (*p == 'a' || *p == 'p') { p++; while ((*p >= '0' && *p <= '9') || *p == ',' || *p == '.' || *p == '-') p++; } break;
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

static void media_path(char *out, int i)
{
    if (i >= NSND) sprintf(out, "%s%s", lib_root, snd_file[i]);
    else sprintf(out, "C:\\WINDOWS\\Media\\%s", snd_file[i]);
}

/* the library disc's catalogue: name, category, path, seconds, source (DNA.md 5.6) */
static void lib_load(const char *root)
{
    char path[MAX_PATH], ln[1024];
    FILE *f;
    int n = 0;
    sprintf(path, "%sLIBRARY.TSV", root);
    if (!(f = fopen(path, "r"))) return;
    lstrcpynA(lib_root, root, sizeof lib_root);
    nsnd = NSND;
    while (fgets(ln, sizeof ln, f) && nsnd < MAXSND) {
        char *nm = strtok(ln, "\t\r\n"), *cat = strtok(NULL, "\t\r\n"), *pa = strtok(NULL, "\t\r\n"), *sec = strtok(NULL, "\t\r\n");
        int dup = 0, i;
        if (!nm || !cat || !pa || nm[0] == '#') continue;
        for (i = 0; i < nsnd; i++) if (!strcmp(snd_name[i], nm)) dup = 1;
        if (dup) continue;
        if (*pa == '\\') pa++;
        snd_name[nsnd] = _strdup(nm);
        snd_cat[nsnd] = _strdup(cat);
        snd_file[nsnd] = _strdup(pa);
        snd_ms[nsnd] = sec ? (int)(atof(sec) * 1000) : 1000;
        nsnd++; n++;
    }
    fclose(f);
    logf_("library %s: %d sounds", root, n);
}

static void lib_find(void)
{
    char root[8];
    int d;
    for (d = 'D'; d <= 'Z'; d++) {
        sprintf(root, "%c:\\", d);
        if (GetDriveTypeA(root) != DRIVE_CDROM) continue;
        sprintf(root, "%c:\\", d);
        { char p[MAX_PATH]; sprintf(p, "%sLIBRARY.TSV", root); if (GetFileAttributesA(p) == INVALID_FILE_ATTRIBUTES) continue; }
        lib_load(root);
        return;
    }
}

/* a command from the recorder's own menu: after assembly it is shown (the menu pops up on the strip and walks to
   the item, SYO_CMDV), unless the plugin asked for fast builds ("vis 0", batch renders) */
static volatile LONG visible_build = 0;   /* the plugin says "vis 1" while its editor is open */
static void rec_cmd(int r, int id, int wait_ms)
{
    if (visible_build && assembled) {
        shm->s[r].menu_x = STRIP_X + 40;
        shm->s[r].menu_y = STRIP_Y + r * ROW_H + ROW_H - 4;
        rec_op(r, SYO_CMDV, id, wait_ms + 3000);
    } else rec_op(r, SYO_CMD, id, wait_ms);
}

/* one layer, on its first recorder, with Sound Recorder's own commands */
static void build_layer(int li, Layer *L)
{
    int r = L->first, i, len_ms, clip_ms;
    char path[MAX_PATH];
    DWORD t0 = GetTickCount();
    media_path(path, L->src);
    rec_file(r, path);
    rec_cmd(r, SR_OPEN, 8000);
    rec_cmd(r, SR_COPY, 8000);           /* the clipboard starts as the source (DNA.md 2.1) */
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
        case 't': rec_op(r, SYO_SEEK, len_ms > 0 ? (s->arg >= len_ms ? 1000 : s->arg * 1000 / len_ms) : 0, 4000); continue;
        }
        if (!id) continue;
        if (len_ms + grow > MAXLEN_MS) { logf_("layer %d step %d skipped (length)", li, i); continue; }
        if (s->op == 'I' || s->op == 'M') { media_path(path, s->arg); rec_file(r, path); }
        rec_cmd(r, id, 15000);
        len_ms = read_ms(r, SR_LEN);
        if (s->op == 'C') clip_ms = len_ms;
    }
    sprintf(path, "C:\\synth\\layer%d.wav", li);
    DeleteFileA(path);
    rec_file(r, path);
    rec_cmd(r, SR_SAVEAS, 15000);
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
    if (win && assembled) InvalidateRect(win, &plate_rc, TRUE);
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
    int r, rate, vol, pan = 0, delay = 0, layer = -1, k;
    char w, pts[200];
    if ((k = sscanf(l, "on %d %d %d %d %d %d", &r, &rate, &vol, &pan, &delay, &layer)) >= 3) {
        if (r < 0 || r >= SY_NREC || building) return;
        if (k < 6) layer = -1;
        shm->s[r].pan = pan < -100 ? -100 : pan > 100 ? 100 : pan;
        shm->s[r].layer = layer >= 0 && layer < 8 ? layer : -1;
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
    } else if (sscanf(l, "lenv %d %c %199s", &layer, &w, pts) == 3) {
        /* a drawn envelope (DNA.md 5.3): "t,l.t,l...", or "-" for none */
        int which = w == 'p' ? 1 : 0, n = 0;
        const char *p = pts;
        if (layer < 0 || layer >= 8) return;
        shm->env[layer][which].n = 0;
        while (*p && *p != '-' && n < 8) {
            int t = read_int(&p), v = 0;
            if (*p == ',') { p++; v = read_int(&p); }
            shm->env[layer][which].t[n] = t;
            shm->env[layer][which].v[n] = v;
            n++;
            if (*p == '.') p++; else break;
        }
        if (*pts == '-' && pts[1] == 0) n = 0;
        shm->env[layer][which].n = n;
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
            if (!strncmp(line, "on ", 3) || !strncmp(line, "off ", 4) || !strncmp(line, "cut ", 4) || !strncmp(line, "panic", 5) || !strncmp(line, "lenv ", 5))
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
    {
        /* the card's Wave volume is one setting for every handle on this machine: full, once; the recorders apply
           their own level, pan and envelope to their samples (srhook.c) */
        typedef MMRESULT (WINAPI *SV)(HWAVEOUT, DWORD);
        SV sv = (SV)GetProcAddress(m, "waveOutSetVolume");
        if (sv) sv((HWAVEOUT)0, 0xFFFFFFFF);
    }
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
    /* rows are 34 px: room under the strips for the envelope editor and the keyboard */
    SetRect(&kid_final[K_PLAY], 4, 5, 4 + 48, 5 + 23);
    SetRect(&kid_final[K_STOP], 54, 5, 54 + 48, 5 + 23);
    SetRect(&kid_final[K_PFRAME], 110, 1, 110 + 60, 1 + 31);
    SetRect(&kid_final[K_PLABEL], 113, 3, 113 + 54, 3 + 14);
    SetRect(&kid_final[K_POS], 113, 17, 113 + 54, 17 + 13);
    SetRect(&kid_final[K_WAVE], 176, 1, 176 + 114, 1 + 31);
    SetRect(&kid_final[K_LFRAME], 296, 1, 296 + 60, 1 + 31);
    SetRect(&kid_final[K_LLABEL], 299, 3, 299 + 54, 3 + 14);
    SetRect(&kid_final[K_LEN], 299, 17, 299 + 54, 17 + 13);
    SetRect(&kid_final[K_TRACK], 362, 4, 362 + 196, 4 + 26);
}
static RECT strip_rect(int r)
{
    RECT x;
    SetRect(&x, STRIP_X, STRIP_Y + r * ROW_H, STRIP_X + STRIP_W, STRIP_Y + r * ROW_H + ROW_H - 1);
    return x;
}
/* the right-hand column: frames drawn by the synth window, contents placed inside */
static RECT fr_dna = {SIDE_X, 2, 1016, 94}, fr_lay = {SIDE_X, 98, 1016, 182}, fr_snd = {SIDE_X, 186, 1016, 302},
            fr_cpu = {SIDE_X, 306, 1016, 506}, fr_mac = {SIDE_X, 510, 834, 742}, fr_clk = {838, 510, 1016, 742};

/* ---------------------------------------------------------------- the borrowed extras */
/* Task Manager's Performance page and Date and Time's Date & Time page move in whole (their drawing stays their
   own programs' work: owner-drawn graphs, an XOR-drawn clock) and show through a window onto the part we want */
static HWND tm_dlg, tm_page, dt_dlg, dt_page, port_cpu, port_clk;
static POINT off_cpu = {12, 8}, off_clk = {198, 3};   /* clock: only the Time half of the page */       /* the wanted part's corner inside each page */
static SIZE sz_cpu = {354, 182}, sz_clk = {168, 203};
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
static HWND w_dna, w_apply, w_mutate, w_undo, w_layers, w_sounds, w_lbl[SY_NREC], w_cat;
#define ID_CAT 3007
/* the browser (DNA.md 5.6): the XP sounds, the library disc's categories, and its presets by category */
#define MAXPRE 256
static char *pre_cat[MAXPRE], *pre_name[MAXPRE], *pre_dna[MAXPRE];
static int npre;
static char cats[48][40];
static int ncat;            /* cats[0] = Windows XP sounds; then library categories; then "Presets: X" */
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
    while (b + n < e && ((t[b + n] >= 'a' && t[b + n] <= 'z') || (t[b + n] >= '0' && t[b + n] <= '9') || t[b + n] == '_')) n++;
    str_cut(t, b, b + n);
    str_insert(t, b, snd_name[s]);
}

static void refresh_panel(void);
static void env_refresh(void);
static void mac_refresh(const char *t);
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
    env_refresh();
    mac_refresh(t);
}


/* ---------------------------------------------------------------- the browser */
static void pre_load(void)
{
    char path[MAX_PATH], ln[1400];
    FILE *f;
    if (!lib_root[0]) return;
    sprintf(path, "%sPRESETS.TSV", lib_root);
    if (!(f = fopen(path, "r"))) return;
    npre = 0;
    while (fgets(ln, sizeof ln, f) && npre < MAXPRE) {
        char *c = strtok(ln, "\t\r\n"), *n = strtok(NULL, "\t\r\n"), *d = strtok(NULL, "\t\r\n");
        if (!c || !n || !d || c[0] == '#') continue;
        pre_cat[npre] = _strdup(c); pre_name[npre] = _strdup(n); pre_dna[npre] = _strdup(d);
        npre++;
    }
    fclose(f);
}
static void add_cat(const char *c)
{
    int i;
    for (i = 0; i < ncat; i++) if (!strcmp(cats[i], c)) return;
    if (ncat < 48) lstrcpynA(cats[ncat++], c, 40);
}
static void browser_list(void)
{
    int k = (int)SendMessageA(w_cat, CB_GETCURSEL, 0, 0), i, at;
    char item[200];
    if (k < 0) k = 0;
    SendMessageA(w_sounds, WM_SETREDRAW, FALSE, 0);
    SendMessageA(w_sounds, LB_RESETCONTENT, 0, 0);
    if (!strncmp(cats[k], "Presets: ", 9)) {
        for (i = 0; i < npre; i++) if (!strcmp(pre_cat[i], cats[k] + 9)) {
            at = (int)SendMessageA(w_sounds, LB_ADDSTRING, 0, (LPARAM)pre_name[i]);
            SendMessageA(w_sounds, LB_SETITEMDATA, at, 10000 + i);
        }
    } else {
        for (i = 0; i < nsnd; i++) {
            if (k == 0 ? i >= NSND : (i < NSND || strcmp(snd_cat[i], cats[k]))) continue;
            if (i < NSND) lstrcpynA(item, snd_file[i], sizeof item);
            else sprintf(item, "%s  (%.1f s)", snd_name[i], snd_ms[i] / 1000.0);
            at = (int)SendMessageA(w_sounds, LB_ADDSTRING, 0, (LPARAM)item);
            SendMessageA(w_sounds, LB_SETITEMDATA, at, i);
        }
    }
    SendMessageA(w_sounds, WM_SETREDRAW, TRUE, 0);
    InvalidateRect(w_sounds, NULL, TRUE);
}
static void browser_fill(void)
{
    int i;
    char t[64];
    if (!w_cat) return;
    pre_load();
    ncat = 0;
    add_cat("Windows XP sounds");
    for (i = NSND; i < nsnd; i++) add_cat(snd_cat[i]);
    for (i = 0; i < npre; i++) { sprintf(t, "Presets: %s", pre_cat[i]); add_cat(t); }
    SendMessageA(w_cat, CB_RESETCONTENT, 0, 0);
    for (i = 0; i < ncat; i++) {
        if (i == 0 || !strncmp(cats[i], "Presets: ", 9)) lstrcpynA(t, cats[i], sizeof t);
        else sprintf(t, "Library: %s", cats[i]);
        SendMessageA(w_cat, CB_ADDSTRING, 0, (LPARAM)t);
    }
    SendMessageA(w_cat, CB_SETCURSEL, 0, 0);
    browser_list();
}
static void browser_pick(void)
{
    int at = (int)SendMessageA(w_sounds, LB_GETCURSEL, 0, 0), d;
    char t[1100];
    if (at < 0) return;
    d = (int)SendMessageA(w_sounds, LB_GETITEMDATA, at, 0);
    if (d >= 10000) { lstrcpynA(t, pre_dna[d - 10000], sizeof t); sel_layer = 0; edit_dna(t); return; }
    {
        int li = sel_layer;
        GetWindowTextA(w_dna, t, sizeof t);
        if (li >= layer_count(t)) li = 0;
        set_source(t, li, d);
        edit_dna(t);
    }
}

static HWND mk(const char *cls, const char *text, DWORD st, int x, int y, int w, int h, int id, HFONT f);
static int lib_tries;
static void lib_ready(void)
{
    browser_fill();
    send_line("lib %d %s", nsnd - NSND, lib_root);
    if (dna_text[0]) start_build(dna_text, 0);    /* layers that named library sounds get built now (assembled or not) */
}

/* ---------------------------------------------------------------- the envelope editor (DNA.md 5.3) */
/* Under the strips: Volume Control's own sliders. Eight upright trackbars are the selected layer's amplitude
   envelope (Ja) at eight times; three level ones are its length, its offset (O) and its pan (Q). The graph is drawn
   the way Task Manager draws its history. Letting go of a slider writes the DNA, which goes to the plugin like any
   other edit. */
#define TRACKBAR_CLASS_ "msctls_trackbar32"
#define TBM_GETPOS_ (WM_USER)
#define TBM_SETPOS_ (WM_USER + 5)
#define TBM_SETRANGE_ (WM_USER + 6)
#define TBM_SETTICFREQ_ (WM_USER + 20)
#define TBS_AUTOTICKS_ 0x1
#define TBS_VERT_ 0x2
#define TBS_BOTH_ 0x8
#define TBS_NOTICKS_ 0x10
#define TB_ENDTRACK_ 8
#define ENV_N 8
#define ID_ENV 3100            /* + 0..7 the levels, 8 length, 9 offset, 10 pan */
static const int env_grid[ENV_N] = {0, 40, 120, 300, 600, 1000, 1800, 3000};
static HWND w_env[ENV_N + 3], w_envval[3], w_envlbl[ENV_N + 3], w_graph, w_envclr;
static int env_lv[ENV_N], env_scale = 100, env_has;
static RECT fr_env = {6, 551, SIDE_X - 8, 634};
static RECT fr_kbd = {6, 636, SIDE_X - 8, 746};

static int env_parse(const char *t, int li, int *tt, int *ll)    /* the layer's Ja points */
{
    int b, e, k, n = 0;
    const char *p;
    if (!layer_span(t, li, &b, &e)) return 0;
    for (k = b; k + 1 < e; k++) if (t[k] == 'J' && t[k + 1] == 'a') {
        p = t + k + 2;
        while (n < ENV_N && *p >= '0' && *p <= '9') {
            tt[n] = read_int(&p); ll[n] = 0;
            if (*p == ',') { p++; ll[n] = read_int(&p); }
            n++;
            if (*p == '.') p++; else break;
        }
        break;
    }
    return n;
}
static void drop_env(char *t, int li, char which)
{
    int b, e, k, j;
    if (!layer_span(t, li, &b, &e)) return;
    for (k = b; k + 1 < e; k++) if (t[k] == 'J' && t[k + 1] == which) {
        j = k + 2;
        while (j < e && ((t[j] >= '0' && t[j] <= '9') || t[j] == ',' || t[j] == '.' || t[j] == '-')) j++;
        str_cut(t, k, j);
        return;
    }
}
static int curve_val(const int *tt, const int *ll, int n, int t)
{
    int i;
    if (n <= 0) return 100;
    if (t <= tt[0]) return ll[0];
    for (i = 1; i < n; i++) if (t <= tt[i]) return tt[i] > tt[i - 1] ? ll[i - 1] + (ll[i] - ll[i - 1]) * (t - tt[i - 1]) / (tt[i] - tt[i - 1]) : ll[i];
    return ll[n - 1];
}
static void env_show_vals(void)
{
    char v[32];
    sprintf(v, "%d %%", env_scale); SetWindowTextA(w_envval[0], v);
    sprintf(v, "%d ms", (int)SendMessageA(w_env[ENV_N + 1], TBM_GETPOS_, 0, 0) * 20); SetWindowTextA(w_envval[1], v);
    { int q = (int)SendMessageA(w_env[ENV_N + 2], TBM_GETPOS_, 0, 0) - 100; if (q) sprintf(v, "%c %d", q < 0 ? 'L' : 'R', q < 0 ? -q : q); else strcpy(v, "centre"); }
    SetWindowTextA(w_envval[2], v);
}
static void env_refresh(void)       /* the sliders follow the DNA */
{
    char t[1100], lbl[48];
    int tt[ENV_N], ll[ENV_N], n, i, li = sel_layer;
    if (!w_graph) return;
    GetWindowTextA(w_dna, t, sizeof t);
    if (li >= layer_count(t)) li = 0;
    n = env_parse(t, li, tt, ll);
    env_has = n > 0;
    if (n) {
        env_scale = tt[n - 1] > 0 ? tt[n - 1] * 100 / env_grid[ENV_N - 1] : 100;
        if (env_scale < 25) env_scale = 25;
        if (env_scale > 400) env_scale = 400;
        for (i = 0; i < ENV_N; i++) env_lv[i] = curve_val(tt, ll, n, env_grid[i] * env_scale / 100);
    } else {
        /* no drawn envelope: show the global A, D, S */
        Dna D;
        dna_parse(t, &D);
        env_scale = 100;
        for (i = 0; i < ENV_N; i++) {
            int g = env_grid[i];
            env_lv[i] = g < D.a ? g * 100 / (D.a ? D.a : 1) : g < D.a + D.d ? 100 - (100 - D.s) * (g - D.a) / (D.d ? D.d : 1) : D.s;
        }
    }
    for (i = 0; i < ENV_N; i++) SendMessageA(w_env[i], TBM_SETPOS_, TRUE, 100 - env_lv[i]);
    SendMessageA(w_env[ENV_N], TBM_SETPOS_, TRUE, env_scale);
    SendMessageA(w_env[ENV_N + 1], TBM_SETPOS_, TRUE, gene_val(t, li, 'O', 0) / 20);
    SendMessageA(w_env[ENV_N + 2], TBM_SETPOS_, TRUE, gene_val(t, li, 'Q', 0) + 100);
    sprintf(lbl, "Layer %d envelope%s", li + 1, env_has ? "" : "  (A D S)");
    SetWindowTextA(w_envlbl[ENV_N], lbl);
    env_show_vals();
    InvalidateRect(w_graph, NULL, FALSE);
}
static void env_commit(int which)  /* a slider was let go: write the DNA */
{
    char t[1100], g[200];
    int li = sel_layer, i, k;
    GetWindowTextA(w_dna, t, sizeof t);
    if (li >= layer_count(t)) li = 0;
    if (which < ENV_N + 1) {
        drop_env(t, li, 'a');
        k = sprintf(g, "Ja");
        for (i = 0; i < ENV_N; i++) k += sprintf(g + k, "%s%d,%d", i ? "." : "", env_grid[i] * env_scale / 100, env_lv[i]);
        { int b, e; if (layer_span(t, li, &b, &e)) str_insert(t, e, g); }
    } else if (which == ENV_N + 1) {
        int o = (int)SendMessageA(w_env[which], TBM_GETPOS_, 0, 0) * 20;
        drop_gene(t, li, 'O');
        if (o) { sprintf(g, "O%d", o); set_gene(t, li, g); }
    } else {
        int q = (int)SendMessageA(w_env[which], TBM_GETPOS_, 0, 0) - 100;
        drop_gene(t, li, 'Q');
        if (q) { sprintf(g, "Q%d", q); set_gene(t, li, g); }
    }
    edit_dna(t);
}
static void env_clear(void)
{
    char t[1100];
    int li = sel_layer;
    GetWindowTextA(w_dna, t, sizeof t);
    if (li >= layer_count(t)) li = 0;
    drop_env(t, li, 'a');
    edit_dna(t);
}
static void env_scroll(HWND c, int code)
{
    int i;
    for (i = 0; i < ENV_N + 3; i++) if (c == w_env[i]) break;
    if (i >= ENV_N + 3) return;
    if (i < ENV_N) env_lv[i] = 100 - (int)SendMessageA(c, TBM_GETPOS_, 0, 0);
    if (i == ENV_N) env_scale = (int)SendMessageA(c, TBM_GETPOS_, 0, 0);
    env_show_vals();
    InvalidateRect(w_graph, NULL, FALSE);
    if (code == TB_ENDTRACK_) env_commit(i);
}
static LRESULT CALLBACK graph_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(h, &ps);
        RECT rc;
        HPEN grid = CreatePen(PS_SOLID, 1, RGB(0, 128, 64)), line = CreatePen(PS_SOLID, 1, RGB(0, 255, 0)), old;
        int W, H, x, y, i, tot = env_grid[ENV_N - 1] * env_scale / 100 * 5 / 4;
        GetClientRect(h, &rc);
        W = rc.right; H = rc.bottom;
        FillRect(dc, &rc, (HBRUSH)GetStockObject(BLACK_BRUSH));
        old = (HPEN)SelectObject(dc, grid);
        for (x = 0; x < W; x += 12) { MoveToEx(dc, x, 0, NULL); LineTo(dc, x, H); }
        for (y = H - 1; y > 0; y -= 12) { MoveToEx(dc, 0, y, NULL); LineTo(dc, W, y); }
        SelectObject(dc, line);
        for (i = 0; i < ENV_N; i++) {
            x = (int)((double)env_grid[i] * env_scale / 100 * (W - 3) / (tot ? tot : 1)) + 1;
            y = H - 2 - env_lv[i] * (H - 4) / 100;
            if (i) LineTo(dc, x, y); else MoveToEx(dc, x, y, NULL);
        }
        LineTo(dc, W, y);
        SelectObject(dc, old);
        DeleteObject(grid); DeleteObject(line);
        EndPaint(h, &ps);
        return 0;
    }
    return DefWindowProcA(h, m, wp, lp);
}
static void env_make(void)
{
    typedef void (WINAPI *ICC)(void);
    WNDCLASSA wc;
    HMODULE cc = LoadLibraryA("comctl32.dll");
    ICC icc = (ICC)GetProcAddress(cc, "InitCommonControls");
    int i, x0 = fr_env.left + 156, y0 = fr_env.top + 17;
    static const char *nm[3] = {"Length", "Offset", "Pan"};
    char tl[16];
    if (icc) icc();
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = graph_proc; wc.hInstance = inst; wc.lpszClassName = "BasiliskGraph";
    RegisterClassA(&wc);
    w_graph = CreateWindowExA(WS_EX_CLIENTEDGE, "BasiliskGraph", "", WS_CHILD, fr_env.left + 8, y0 + 2, 140, 60, win, NULL, inst, NULL);
    w_envlbl[ENV_N] = mk("STATIC", "Layer 1 envelope", SS_LEFT, fr_env.left + 10, fr_env.top, 150, 14, 0, font);
    for (i = 0; i < ENV_N; i++) {
        w_env[i] = CreateWindowExA(0, TRACKBAR_CLASS_, "", WS_CHILD | TBS_VERT_ | TBS_BOTH_ | TBS_AUTOTICKS_,
                                   x0 + i * 25, y0, 24, 50, win, (HMENU)(INT_PTR)(ID_ENV + i), inst, NULL);
        SendMessageA(w_env[i], TBM_SETRANGE_, TRUE, MAKELONG(0, 100));
        SendMessageA(w_env[i], TBM_SETTICFREQ_, 25, 0);
        sprintf(tl, env_grid[i] >= 1000 ? "%d.%ds" : "%d", env_grid[i] >= 1000 ? env_grid[i] / 1000 : env_grid[i], env_grid[i] % 1000 / 100);
        w_envlbl[i] = mk("STATIC", tl, SS_CENTER, x0 + i * 25 - 2, y0 + 50, 28, 13, 0, font);
    }
    x0 += ENV_N * 25 + 8;
    for (i = 0; i < 3; i++) {
        int y = y0 + i * 21 - 1;
        mk("STATIC", nm[i], SS_LEFT, x0, y + 3, 40, 14, 0, font);
        w_env[ENV_N + i] = CreateWindowExA(0, TRACKBAR_CLASS_, "", WS_CHILD | TBS_NOTICKS_,
                                           x0 + 40, y, 110, 21, win, (HMENU)(INT_PTR)(ID_ENV + ENV_N + i), inst, NULL);
        w_envval[i] = mk("STATIC", "", SS_LEFT, x0 + 152, y + 3, 52, 14, 0, font);
    }
    SendMessageA(w_env[ENV_N], TBM_SETRANGE_, TRUE, MAKELONG(25, 400));
    SendMessageA(w_env[ENV_N + 1], TBM_SETRANGE_, TRUE, MAKELONG(0, 100));    /* x 20 ms */
    SendMessageA(w_env[ENV_N + 2], TBM_SETRANGE_, TRUE, MAKELONG(0, 200));
    w_envclr = mk("BUTTON", "A D S", BS_PUSHBUTTON, fr_env.right - 44, fr_env.top, 38, 15, ID_ENV + 20, font);
}
static void env_show(void)
{
    HWND kids[64];
    int n = 0, i;
    HWND c = NULL;
    while ((c = FindWindowExA(win, c, NULL, NULL))) {
        RECT r;
        POINT p;
        GetWindowRect(c, &r);
        p.x = r.left; p.y = r.top;
        ScreenToClient(win, &p);
        if (PtInRect(&fr_env, p) && n < 64) kids[n++] = c;
    }
    for (i = 0; i < n; i++) ShowWindow(kids[i], SW_SHOWNA);
    env_refresh();
    UpdateWindow(win);
}


/* ---------------------------------------------------------------- the keyboard (DNA.md 5.4) */
/* Three octaves of push buttons (the BUTTON class, owner-drawn as white and black keys), Volume Control's upright
   sliders as the pitch bend and mod wheel, and push-like check boxes for Hold and the computer keyboard. A key goes
   down with BM_SETSTATE: for a note from the DAW ("show"), the mouse, or the computer keyboard. The mouse and the
   keys play through the host ("key", "cc 1", "bend"), like MIDI. */
#define KB_KEYS 37
#define ID_KEY 3200            /* + key */
#define ID_BEND 3260
#define ID_MOD 3261
#define ID_HOLD 3262
#define ID_QWERTY 3263
#define ID_OCTDN 3264
#define ID_OCTUP 3265
static HWND w_key[KB_KEYS], w_bend, w_mod, w_hold, w_qwerty, w_octdn, w_octup, w_kbinfo, w_kbttl[4];
static int kb_lo = 48;                 /* the lowest key: C3 */
static int kb_oct = 0;                 /* the computer keyboard's octave, relative to kb_lo + 12 */
static int kb_vel = 100;
static unsigned char kb_host[128], kb_mine[128], kb_latched[128];
static int kb_mouse = -1;              /* the note under the held mouse button */
static int kbd_frame;
static WNDPROC old_key;
static const int kb_black[12] = {0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0};

static void key_show(int note)
{
    int k = note - kb_lo;
    if (k < 0 || k >= KB_KEYS || !w_key[k]) return;
    SendMessageA(w_key[k], BM_SETSTATE, kb_host[note] || kb_mine[note] || kb_latched[note], 0);
}
static void kb_note(int note, int vel)       /* the visitor played or let go of a key */
{
    if (note < 0 || note > 127) return;
    if (vel > 0) {
        if (kb_latched[note]) { kb_latched[note] = 0; send_line("key %d 0", note); }
        kb_mine[note] = 1;
        send_line("key %d %d", note, vel);
    } else {
        if (!kb_mine[note]) return;
        kb_mine[note] = 0;
        if (SendMessageA(w_hold, BM_GETCHECK, 0, 0) == BST_CHECKED) kb_latched[note] = 1;   /* Hold: the note-off waits */
        else send_line("key %d 0", note);
    }
    key_show(note);
}
static void kb_release_hold(void)
{
    int n;
    for (n = 0; n < 128; n++) if (kb_latched[n]) { kb_latched[n] = 0; send_line("key %d 0", n); key_show(n); }
}
static void kb_info(void)
{
    char t[64];
    sprintf(t, "C%d  vel %d", (kb_lo + 12 + kb_oct * 12) / 12 - 1, kb_vel);
    SetWindowTextA(w_kbinfo, t);
}
static int key_at(POINT sp)                  /* the key under a screen point (black keys are on top) */
{
    int k;
    for (k = 0; k < KB_KEYS; k++) if (kb_black[(kb_lo + k) % 12]) { RECT r; GetWindowRect(w_key[k], &r); if (PtInRect(&r, sp)) return kb_lo + k; }
    for (k = 0; k < KB_KEYS; k++) if (!kb_black[(kb_lo + k) % 12]) { RECT r; GetWindowRect(w_key[k], &r); if (PtInRect(&r, sp)) return kb_lo + k; }
    return -1;
}
static int key_vel(HWND h, int y)
{
    RECT r;
    GetClientRect(h, &r);
    return 30 + 97 * (y < 0 ? 0 : y > r.bottom ? r.bottom : y) / (r.bottom ? r.bottom : 1);   /* lower on the key: louder */
}
static LRESULT CALLBACK key_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    POINT p;
    int n;
    switch (m) {
    case WM_LBUTTONDOWN: case WM_LBUTTONDBLCLK:
        SetCapture(h);
        kb_mouse = GetDlgCtrlID(h) - ID_KEY + kb_lo;
        kb_note(kb_mouse, key_vel(h, (short)HIWORD(lp)));
        return 0;
    case WM_MOUSEMOVE:
        if (GetCapture() != h || kb_mouse < 0) return 0;
        p.x = (short)LOWORD(lp); p.y = (short)HIWORD(lp);
        ClientToScreen(h, &p);
        n = key_at(p);
        if (n != kb_mouse) {                   /* a glide: the old key up, the new one down */
            kb_note(kb_mouse, 0);
            kb_mouse = n;
            if (n >= 0) { HWND k = w_key[n - kb_lo]; ScreenToClient(k, &p); kb_note(n, key_vel(k, p.y)); }
        }
        return 0;
    case WM_LBUTTONUP: case WM_CAPTURECHANGED:
        if (kb_mouse >= 0) kb_note(kb_mouse, 0);
        kb_mouse = -1;
        if (m == WM_LBUTTONUP && GetCapture() == h) ReleaseCapture();
        return 0;
    case WM_SETFOCUS: case WM_KEYDOWN: case WM_KEYUP: case WM_CHAR:
        return 0;                              /* the keys never take the focus or the keyboard */
    }
    return CallWindowProcA(old_key, h, m, wp, lp);
}
static void key_draw(DRAWITEMSTRUCT *d)
{
    int k = (int)d->CtlID - ID_KEY, note = kb_lo + k, black = kb_black[note % 12], down = (d->itemState & ODS_SELECTED) != 0;
    RECT r = d->rcItem;
    HBRUSH b;
    if (black) {
        b = CreateSolidBrush(down ? RGB(40, 80, 200) : RGB(28, 28, 28));
        FillRect(d->hDC, &r, b);
        DeleteObject(b);
        DrawEdge(d->hDC, &r, down ? BDR_SUNKENOUTER : BDR_RAISEDINNER, BF_RECT);
        if (!down) { RECT g = r; InflateRect(&g, -3, 0); g.top = g.bottom - 7; b = CreateSolidBrush(RGB(70, 70, 70)); FillRect(d->hDC, &g, b); DeleteObject(b); }
    } else {
        DrawFrameControl(d->hDC, &r, DFC_BUTTON, DFCS_BUTTONPUSH | (down ? DFCS_PUSHED : 0));
        if (down) { RECT g = r; InflateRect(&g, -2, -2); g.top += 1; b = CreateSolidBrush(RGB(150, 185, 245)); FillRect(d->hDC, &g, b); DeleteObject(b); }
        if (note % 12 == 0) {
            char t[8];
            sprintf(t, "C%d", note / 12 - 1);
            SetBkMode(d->hDC, TRANSPARENT);
            SetTextColor(d->hDC, RGB(90, 90, 90));
            SelectObject(d->hDC, font);
            r.bottom -= 3;
            DrawTextA(d->hDC, t, -1, &r, DT_CENTER | DT_BOTTOM | DT_SINGLELINE);
        }
    }
}
static void kb_make(void)
{
    int k, x0 = fr_kbd.left + 150, y0 = fr_kbd.top + 17, wk = 19, nw = 0, hw = 80, hb = 50;
    old_key = NULL;
    w_kbttl[0] = mk("STATIC", "Keyboard", SS_LEFT, fr_kbd.left + 10, fr_kbd.top, 50, 14, 0, font);
    for (k = 0; k < KB_KEYS; k++) {
        int note = kb_lo + k, x;
        if (kb_black[note % 12]) continue;
        x = x0 + nw * wk;
        w_key[k] = CreateWindowExA(0, "BUTTON", "", WS_CHILD | WS_CLIPSIBLINGS | BS_OWNERDRAW, x, y0, wk + 1, hw, win, (HMENU)(INT_PTR)(ID_KEY + k), inst, NULL);
        nw++;
    }
    nw = 0;
    for (k = 0; k < KB_KEYS; k++) {
        int note = kb_lo + k;
        if (!kb_black[note % 12]) { nw++; continue; }
        w_key[k] = CreateWindowExA(0, "BUTTON", "", WS_CHILD | WS_CLIPSIBLINGS | BS_OWNERDRAW, x0 + nw * wk - 6, y0, 13, hb, win, (HMENU)(INT_PTR)(ID_KEY + k), inst, NULL);
        SetWindowPos(w_key[k], HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    }
    for (k = 0; k < KB_KEYS; k++) {
        WNDPROC o = (WNDPROC)SetWindowLongA(w_key[k], GWL_WNDPROC, (LONG)key_proc);
        if (!old_key) old_key = o;
    }
    /* the wheels: Volume Control's sliders */
    w_bend = CreateWindowExA(0, TRACKBAR_CLASS_, "", WS_CHILD | TBS_VERT_ | TBS_BOTH_ | TBS_AUTOTICKS_, fr_kbd.left + 8, y0, 30, 72, win, (HMENU)ID_BEND, inst, NULL);
    SendMessageA(w_bend, TBM_SETRANGE_, TRUE, MAKELONG(0, 128));
    SendMessageA(w_bend, TBM_SETTICFREQ_, 64, 0);
    SendMessageA(w_bend, TBM_SETPOS_, TRUE, 64);
    w_mod = CreateWindowExA(0, TRACKBAR_CLASS_, "", WS_CHILD | TBS_VERT_ | TBS_BOTH_ | TBS_AUTOTICKS_, fr_kbd.left + 42, y0, 30, 72, win, (HMENU)ID_MOD, inst, NULL);
    SendMessageA(w_mod, TBM_SETRANGE_, TRUE, MAKELONG(0, 127));
    SendMessageA(w_mod, TBM_SETTICFREQ_, 32, 0);
    SendMessageA(w_mod, TBM_SETPOS_, TRUE, 127);
    w_kbttl[1] = mk("STATIC", "Bend", SS_CENTER, fr_kbd.left + 6, y0 + 73, 34, 13, 0, font);
    w_kbttl[2] = mk("STATIC", "Mod", SS_CENTER, fr_kbd.left + 40, y0 + 73, 34, 13, 0, font);
    w_hold = mk("BUTTON", "Hold", BS_AUTOCHECKBOX | BS_PUSHLIKE, fr_kbd.left + 80, y0 + 1, 62, 22, ID_HOLD, font);
    w_qwerty = mk("BUTTON", "PC keys", BS_AUTOCHECKBOX | BS_PUSHLIKE, fr_kbd.left + 80, y0 + 26, 62, 22, ID_QWERTY, font);
    w_octdn = mk("BUTTON", "<", BS_PUSHBUTTON, fr_kbd.left + 80, y0 + 51, 30, 20, ID_OCTDN, font);
    w_octup = mk("BUTTON", ">", BS_PUSHBUTTON, fr_kbd.left + 112, y0 + 51, 30, 20, ID_OCTUP, font);
    w_kbinfo = mk("STATIC", "", SS_LEFT, fr_kbd.left + 78, y0 + 74, 70, 13, 0, font);
    (void)hb;
    kb_info();
}
static int kb_wheel_scroll(HWND c, int code)
{
    static int last_bend = 0, last_mod = -1;
    if (c == w_bend) {
        int v = (64 - (int)SendMessageA(c, TBM_GETPOS_, 0, 0)) * 128;
        if (code == TB_ENDTRACK_ || code == 4 /* TB_THUMBPOSITION */) { SendMessageA(c, TBM_SETPOS_, TRUE, 64); v = 0; }   /* it springs back */
        if (v > 8191) v = 8191;
        if (v != last_bend) { send_line("bend %d", v); last_bend = v; }
        return 1;
    }
    if (c == w_mod) {
        int v = 127 - (int)SendMessageA(c, TBM_GETPOS_, 0, 0);
        if (v != last_mod) { send_line("cc 1 %d", v); last_mod = v; }
        return 1;
    }
    return 0;
}
static void kb_line(const char *l)             /* display lines from the host */
{
    int a, b;
    if (sscanf(l, "show %d %d", &a, &b) == 2 && a >= 0 && a < 128) { kb_host[a] = b > 0; key_show(a); }
    else if (sscanf(l, "cc %d %d", &a, &b) == 2 && a == 1) { if (GetCapture() != w_mod) SendMessageA(w_mod, TBM_SETPOS_, TRUE, 127 - b); }
    else if (sscanf(l, "bend %d", &a) == 1) { if (GetCapture() != w_bend) SendMessageA(w_bend, TBM_SETPOS_, TRUE, 64 - a / 128); }
}
/* the computer keyboard: a w s e d f t g y h u j k = C..C, z x octave, c v velocity */
static int kb_pc(MSG *m)
{
    static const char map[] = "AWSEDFTGYHUJK";
    const char *q;
    int vk = (int)m->wParam, n;
    if (!w_qwerty || SendMessageA(w_qwerty, BM_GETCHECK, 0, 0) != BST_CHECKED) return 0;
    if (m->message != WM_KEYDOWN && m->message != WM_KEYUP) return 0;
    if (GetFocus() == w_dna) return 0;
    if (vk >= 'A' && vk <= 'Z' && (q = strchr(map, vk))) {
        n = kb_lo + 12 + kb_oct * 12 + (int)(q - map);
        if (m->message == WM_KEYDOWN) { if (!(m->lParam & 0x40000000)) kb_note(n, kb_vel); }
        else kb_note(n, 0);
        return 1;
    }
    if (m->message == WM_KEYDOWN && (vk == 'Z' || vk == 'X')) { kb_oct += vk == 'Z' ? -1 : 1; if (kb_oct < -3) kb_oct = -3; if (kb_oct > 4) kb_oct = 4; kb_info(); return 1; }
    if (m->message == WM_KEYDOWN && (vk == 'C' || vk == 'V')) { kb_vel += vk == 'C' ? -20 : 20; if (kb_vel < 7) kb_vel = 7; if (kb_vel > 127) kb_vel = 127; kb_info(); return 1; }
    return vk == 'Z' || vk == 'X' || vk == 'C' || vk == 'V';
}


/* ---------------------------------------------------------------- the macros (DNA.md 5.3) */
/* Four of Volume Control's upright sliders: Macro 1..4 (the DAW's "Macro K" parameters). Letting go writes mK=V into
   the DNA, which goes to the plugin like any edit. The mod wheel adds to macro 1 in the plugin. */
#define ID_MAC 3280
static HWND w_mac[4], w_macval[4], w_macname[4];
static const char *mac_names[4] = {"1 Tone", "2 Body", "3 Time", "4 Motion"};
static void mac_make(void)
{
    int k, cw = (fr_mac.right - fr_mac.left - 12) / 4;
    for (k = 0; k < 4; k++) {
        int x = fr_mac.left + 6 + k * cw;
        w_mac[k] = CreateWindowExA(0, TRACKBAR_CLASS_, "", WS_CHILD | TBS_VERT_ | TBS_BOTH_ | TBS_AUTOTICKS_, x + (cw - 32) / 2, fr_mac.top + 22, 32, 160, win, (HMENU)(INT_PTR)(ID_MAC + k), inst, NULL);
        SendMessageA(w_mac[k], TBM_SETRANGE_, TRUE, MAKELONG(0, 100));
        SendMessageA(w_mac[k], TBM_SETTICFREQ_, 10, 0);
        SendMessageA(w_mac[k], TBM_SETPOS_, TRUE, 100);
        w_macname[k] = mk("STATIC", mac_names[k], SS_CENTER, x, fr_mac.top + 186, cw, 14, 0, font_b);
        w_macval[k] = mk("STATIC", "0 %", SS_CENTER, x, fr_mac.top + 202, cw, 14, 0, font);
    }
}
static void mac_refresh(const char *t)          /* the sliders follow the DNA's mK=V */
{
    const char *g = strchr(t, ';');
    int k, v[4] = {0, 0, 0, 0}, a, b;
    char val[16];
    if (!w_mac[0]) return;
    if (g) for (; *g; g++) if (g[0] == 'm' && sscanf(g, "m%d=%d", &a, &b) == 2 && a >= 1 && a <= 4) v[a - 1] = b;
    for (k = 0; k < 4; k++) {
        if (GetCapture() != w_mac[k]) SendMessageA(w_mac[k], TBM_SETPOS_, TRUE, 100 - v[k]);
        sprintf(val, "%d %%", v[k]);
        SetWindowTextA(w_macval[k], val);
    }
}
static int mac_scroll(HWND c, int code)
{
    int k;
    char t[1100], tok[16], val[16];
    for (k = 0; k < 4; k++) if (c == w_mac[k]) break;
    if (k == 4) return 0;
    sprintf(val, "%d %%", 100 - (int)SendMessageA(c, TBM_GETPOS_, 0, 0));
    SetWindowTextA(w_macval[k], val);
    if (code != TB_ENDTRACK_) return 1;
    GetWindowTextA(w_dna, t, sizeof t);
    {
        /* replace (or add) mK=V among the globals */
        char *g = strchr(t, ';'), *q;
        int v = 100 - (int)SendMessageA(c, TBM_GETPOS_, 0, 0);
        if (!g) { g = t + strlen(t); strcat(t, ";"); }
        sprintf(tok, "m%d=", k + 1);
        if ((q = strstr(g, tok))) {
            char *e = q + strlen(tok);
            while (*e >= '0' && *e <= '9') e++;
            str_cut(t, (int)(q - t), (int)(e - t));
            sprintf(tok, "m%d=%d", k + 1, v);
            str_insert(t, (int)(q - t), tok);
        } else { sprintf(tok, "m%d=%d", k + 1, v); str_insert(t, (int)(g - t) + 1, tok); }
    }
    edit_dna(t);
    return 1;
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
        else if (!strncmp(l, "vis ", 4)) visible_build = atoi(l + 4);
        else if (!strncmp(l, "show ", 5) || !strncmp(l, "cc ", 3) || !strncmp(l, "bend ", 5)) kb_line(l);
        else if (!strncmp(l, "lib", 3)) {
            const char *q = l + 3;
            while (*q == ' ') q++;
            if (*q) { char root[8]; lstrcpynA(root, q, 4); if (root[2] != '\\') { root[2] = '\\'; root[3] = 0; } lib_load(root); }
            else lib_find();
            if (!lib_root[0]) { lib_tries = 0; SetTimer(h, 77, 500, NULL); }   /* XP has not seen the disc yet */
            else lib_ready();
        }
        free(l);
        return 0;
    }
    case WM_BUILT:
        InvalidateRect(h, &plate_rc, TRUE);
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
        if (id == ID_SOUNDS && code == LBN_DBLCLK) { browser_pick(); return 0; }
        if (id == ID_CAT && code == CBN_SELCHANGE) { browser_list(); return 0; }
        if (id == ID_ENV + 20 && code == BN_CLICKED) { env_clear(); return 0; }
        if (id == ID_HOLD) { if (SendMessageA(w_hold, BM_GETCHECK, 0, 0) != BST_CHECKED) kb_release_hold(); SetFocus(win); return 0; }
        if (id == ID_QWERTY) { SetFocus(win); return 0; }
        if (id == ID_OCTDN || id == ID_OCTUP) { kb_oct += id == ID_OCTDN ? -1 : 1; if (kb_oct < -3) kb_oct = -3; if (kb_oct > 4) kb_oct = 4; kb_info(); SetFocus(win); return 0; }
        if (id >= ID_KEY && id < ID_KEY + KB_KEYS) return 0;
        if (code == 0 || code == BN_CLICKED) on_menu(id);
        return 0;
    }
    case WM_TIMER:
        if (wp == 77) {
            lib_find();
            if (lib_root[0] || ++lib_tries > 30) { KillTimer(h, 77); if (lib_root[0]) lib_ready(); else logf_("no library disc"); }
        }
        return 0;
    case WM_VSCROLL: case WM_HSCROLL:
        if (lp && kb_wheel_scroll((HWND)lp, LOWORD(wp))) return 0;
        if (lp && mac_scroll((HWND)lp, LOWORD(wp))) return 0;
        if (lp) env_scroll((HWND)lp, LOWORD(wp));
        return 0;
    case WM_DRAWITEM:
        if (wp >= ID_KEY && wp < ID_KEY + KB_KEYS) { key_draw((DRAWITEMSTRUCT *)lp); return TRUE; }
        break;
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(h, &ps);
        RECT fr[6] = {fr_dna, fr_lay, fr_snd, fr_cpu, fr_clk, fr_mac}, rc;
        const char *ttl[6] = {"DNA", "Layers", "Library - double-click: a sound becomes the layer's source", "This machine (Task Manager)", "Time", "Macros"};
        int i;
        char st[200];
        SetBkMode(dc, TRANSPARENT);
        SelectObject(dc, font);
        if (panel_frames) for (i = 0; i < 6; i++) {
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
        if (panel_frames) { RECT e = fr_env; e.top += 6; DrawEdge(dc, &e, EDGE_ETCHED, BF_RECT); }
        if (kbd_frame) { RECT e = fr_kbd; e.top += 6; DrawEdge(dc, &e, EDGE_ETCHED, BF_RECT); }
        /* the maker's plate, on the editor's top edge */
        if (panel_frames) {
            SIZE z;
            int x = plate_rc.left + 6;
            FillRect(dc, &plate_rc, GetSysColorBrush(COLOR_BTNFACE));
            SetTextColor(dc, RGB(0, 51, 153));
            SelectObject(dc, font_b);
            TextOutA(dc, x, plate_rc.top, "BASILISK SYNTH " VERSION, (int)strlen("BASILISK SYNTH " VERSION));
            GetTextExtentPoint32A(dc, "BASILISK SYNTH " VERSION, (int)strlen("BASILISK SYNTH " VERSION), &z);
            SelectObject(dc, font);
            SetTextColor(dc, RGB(80, 80, 80));
            if (assembled && status_ms) sprintf(st, "%s  Assembled in %.1f s.", building ? "Changing tapes..." : "Ready.", status_ms / 1000.0);
            else sprintf(st, "Sixteen Sound Recorders, one instrument.");
            TextOutA(dc, x + z.cx + 10, plate_rc.top, st, (int)strlen(st));
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
    w_sounds = mk("LISTBOX", "", LBS_NOTIFY | WS_HSCROLL | WS_TABSTOP | LBS_NOINTEGRALHEIGHT | LBS_MULTICOLUMN, x, fr_snd.top + 39, W, fr_snd.bottom - fr_snd.top - 47, ID_SOUNDS, NULL);
    SendMessageA(w_sounds, LB_SETCOLUMNWIDTH, (W - 4) / 2, 0);
    w_cat = mk("COMBOBOX", "", CBS_DROPDOWNLIST | WS_VSCROLL | WS_TABSTOP, x, fr_snd.top + 15, W, 300, ID_CAT, NULL);
    browser_fill();
    port_cpu = CreateWindowExA(0, "BasiliskPort", "", WS_CHILD | WS_CLIPCHILDREN, SIDE_X + (SIDE_W - sz_cpu.cx) / 2, fr_cpu.top + 14, sz_cpu.cx, sz_cpu.cy, win, NULL, inst, NULL);
    env_make();
    kb_make();
    mac_make();
    port_clk = CreateWindowExA(0, "BasiliskPort", "", WS_CHILD | WS_CLIPCHILDREN, fr_clk.left + (fr_clk.right - fr_clk.left - sz_clk.cx) / 2, fr_clk.top + 16, sz_clk.cx, sz_clk.cy, win, NULL, inst, NULL);
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
#define EV_KBD 12        /* r: a key appears (0..36); 100: the wheels and buttons */
#define MORPH_MS 100
#define GLIDE_MS 120
#define STEP_MS 70
static Ev ev[256];
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
    gl[which].b = which ? (RECT){fr_clk.left + (fr_clk.right - fr_clk.left - sz_clk.cx) / 2, fr_clk.top + 16, 0, 0} : (RECT){SIDE_X + (SIDE_W - sz_cpu.cx) / 2, fr_cpu.top + 14, 0, 0};
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
    case EV_KBD:
        if (r == 0) { kbd_frame = 1; { RECT e = fr_kbd; InvalidateRect(win, &e, TRUE); } ShowWindow(w_kbttl[0], SW_SHOWNA); }
        if (r < KB_KEYS) { ShowWindow(w_key[r], SW_SHOWNA); UpdateWindow(w_key[r]); }
        else {
            HWND c[] = {w_bend, w_mod, w_hold, w_qwerty, w_octdn, w_octup, w_kbinfo, w_kbttl[1], w_kbttl[2]};
            int i;
            for (i = 0; i < 9; i++) ShowWindow(c[i], SW_SHOWNA);
            UpdateWindow(win);
        }
        break;
    case EV_LBL: ShowWindow(w_lbl[r], SW_SHOWNA); UpdateWindow(w_lbl[r]); break;
    case EV_PANEL: {
        HWND p[] = {w_dna, w_apply, w_mutate, w_undo, w_layers, w_sounds};
        if (r < 6) { ShowWindow(p[r], SW_SHOWNA); UpdateWindow(p[r]); }
        if (r == 5) { ShowWindow(w_cat, SW_SHOWNA); UpdateWindow(w_cat); }
        if (r == 6) { int k; env_show(); for (k = 0; k < 4; k++) { ShowWindow(w_mac[k], SW_SHOWNA); ShowWindow(w_macname[k], SW_SHOWNA); ShowWindow(w_macval[k], SW_SHOWNA); } }
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
        if (r == 0) {          /* the keyboard lays itself out, key by key, while the strips morph */
            int k;
            for (k = 0; k < KB_KEYS; k++) add_ev(700 + k * 14, EV_KBD, k);
            add_ev(700 + KB_KEYS * 14 + 30, EV_KBD, 100);
        }
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
                for (i = 0; i < 7; i++) add_ev(t + 240 + i * 35, EV_PANEL, i);
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
    /* menus open and close at once: the building is shown one menu after another */
    SystemParametersInfoA(0x1003 /* SPI_SETMENUANIMATION */, 0, (PVOID)FALSE, 0);
    SystemParametersInfoA(0x1013 /* SPI_SETMENUFADE */, 0, (PVOID)FALSE, 0);
    SystemParametersInfoA(0x1015 /* SPI_SETSELECTIONFADE */, 0, (PVOID)FALSE, 0);
    lib_find();
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
        if (kb_pc(&m)) continue;
        if (!IsDialogMessageA(win, &m)) { TranslateMessage(&m); DispatchMessageA(&m); }
    }
    return 0;
}
