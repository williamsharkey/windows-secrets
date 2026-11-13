/* SYNTH.EXE - BASILISK 16: sixteen Windows 3.11 Sound Recorders assembled into one synthesizer.

   The recorders are real SOUNDREC.EXE instances. Their windows lose their menus and title bars, become children
   of this window, and their controls are lined up into sixteen rows (status, wave display, position, length,
   seek bar, the five transport buttons). Notes from the host (the BASILISK synth plugin) press Play on the
   recorder it picked; the sound is Sound Recorder's own buffer, played through the BSYN card's driver.
   The DNA (packages/basilisk-synth/DNA.md) is built with Sound Recorder's own menu commands.

   Host link: the BSYN card's mailbox (bslink.h), carrying the text lines of DNA.md section 4. */
#include <windows.h>
#include <mmsystem.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
#include <dos.h>
#include "bslink.h"

#define NR 16
#define ROW0 50
#define ROWH 35
#define STRIPX 40
#define STRIPW 924
#define STRIPH 34
#define PANEL 620
#define NL 8
#define NS 64

/* Sound Recorder's control and menu ids (from SOUNDREC.EXE's resources) */
#define SR_STATUS 200
#define SR_POS 201
#define SR_LEN 202
#define SR_WAVE 203
#define SR_SCROLL 204
#define SR_REW 205
#define SR_PLAY 206
#define SR_STOP 207
#define SR_REC 208
#define SR_FWD 209
#define SR_COPY 20
#define SR_PASTE 24
#define SR_PASTEMIX 25
#define SR_INSERT 22
#define SR_MIX 23
#define SR_DELBEFORE 31
#define SR_DELAFTER 32
#define SR_VOLUP 33
#define SR_VOLDN 34
#define SR_FASTER 35
#define SR_SLOWER 36
#define SR_ECHO 37
#define SR_REVERSE 38

HINSTANCE hInst;
HWND hMain, hClock, hDna;
/* One bank of sixteen. (A second, spare bank of sixteen was tried, to build a new DNA out of sight: Windows 3.11
   runs out of GDI resources at about 30 Sound Recorders, 4% free. So a new DNA is built in place, one recorder
   at a time, and notes keep being served between recorders; see build().) */
#define NB 1
#define NALL (NR * NB)
HWND rw[NALL];        /* the recorders' main windows */
HTASK rt[NALL];
BOOL rplay[NALL];     /* we pressed Play and it has not stopped yet */
int rlayer[NALL];
int bank;             /* the active bank */
long recRate[NALL];   /* the sample rate of what each recorder holds now */
long hostRate[NALL];  /* the rate the host believes it holds (its last `layer` reply) */
#define AR(r) (bank * NR + (r))
BOOL assembled, building, titleShown;
char dnaText[1100] = "ding#16;R120";
int envA, envD, envS = 100, envR = 120;
int selLayer;
char line[1200];

static void panel_refresh(void);

/* SYNHOOK.DLL */
void (FAR PASCAL *HookActive)(BOOL);
void (FAR PASCAL *HookPending)(LPCSTR);
BOOL (FAR PASCAL *HookInstall)(BOOL);

static void say(const char *fmt, ...)
{
    static char b[300];
    va_list a; va_start(a, fmt); vsprintf(b, fmt, a); va_end(a);
    bs_line(b);
}
static void logf_(const char *fmt, ...)
{
    static char b[300];
    va_list a; va_start(a, fmt); strcpy(b, "log "); vsprintf(b + 4, fmt, a); va_end(a);
    bs_line(b);
}

/* ================================================================ the DNA, as packages/basilisk-synth/core parses it */
static const char *names[35] = {
    "chimes", "chord", "ding", "notify", "recycle", "ringin", "ringout", "start", "tada",
    "balloon", "batcrit", "batlow", "critstop", "default", "xpding", "error", "exclaim", "hwfail",
    "hwin", "hwout", "infobar", "logoff", "logon", "menu", "minimize", "xpnotify", "popup", "print",
    "xprecycle", "restore", "xpringin", "xpringout", "shutdown", "startup", "xpstart"};
static int sound_index(const char *s, int n)
{
    int i;
    for (i = 0; i < 35; i++) if ((int)strlen(names[i]) == n && !strncmp(names[i], s, n)) return i;
    return -1;
}
static const char *sound_file(int i)   /* Windows 3.11: only these four exist; every other NAME plays ding */
{
    switch (i) {
    case 0: return "C:\\WINDOWS\\CHIMES.WAV";
    case 5: return "C:\\WINDOWS\\RINGIN.WAV";
    case 6: return "C:\\WINDOWS\\RINGOUT.WAV";
    }
    return "C:\\WINDOWS\\DING.WAV";
}
static int sound_cs(int i)   /* lengths in centiseconds, for the 30 s rule */
{
    switch (i) { case 0: return 72; case 5: return 90; case 6: return 47; }
    return 52;
}
static int sound_rate(int i) { return (i == 5 || i == 6) ? 11025 : 22050; }

typedef struct { char op; int arg; int sound; } STEP;
typedef struct { int source; STEP st[NS]; int nst; int pool; int first, count; } LAYER;
LAYER lay[NL];
int nlay;

static int isname(char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'); }
static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }
static int getint(const char **pp, int dflt)
{
    const char *p = *pp; int neg = 0; long v = 0;
    if (*p == '-' || *p == '+') { neg = *p == '-'; p++; }
    if (*p < '0' || *p > '9') return dflt;
    while (*p >= '0' && *p <= '9') { if (v < 100000000L) v = v * 10 + (*p - '0'); p++; }
    *pp = p;
    return (int)(neg ? -v : v);
}

static void dna_parse(const char *t)
{
    const char *p = t;
    int i, k, left = NR, valid[NL], nv = 0, at = 0;
    nlay = 0;
    while (*p && *p != ';') {
        LAYER L; const char *b = p;
        memset(&L, 0, sizeof L);
        while (isname(*p)) p++;
        L.source = sound_index(b, (int)(p - b));
        while (*p && *p != '/' && *p != ';') {
            char c = *p++;
            switch (c) {
            case '+': case '-': case '>': case '<': case 'E': case 'R': case '[': case ']': case 'C': case 'P': case 'X':
                if (L.nst < NS) { L.st[L.nst].op = c; L.nst++; }
                break;
            case '@': { int v = clampi(getint(&p, 0), 0, 99); if (L.nst < NS) { L.st[L.nst].op = '@'; L.st[L.nst].arg = v; L.nst++; } break; }
            case 'I': case 'M': {
                const char *q = p; int si;
                while (isname(*p)) p++;
                si = sound_index(q, (int)(p - q));
                if (si >= 0 && L.nst < NS) { L.st[L.nst].op = c; L.st[L.nst].sound = si; L.nst++; }
                break; }
            case '#': L.pool = clampi(getint(&p, 1), 1, NR); break;
            case 'T': case 'L': getint(&p, 0); break;
            case 'H': do { if (*p == ',') p++; getint(&p, 0); } while (*p == ','); break;
            case 'U': getint(&p, 1); if (*p == '~') { p++; getint(&p, 0); } break;
            default: break;
            }
        }
        if (nlay < NL) lay[nlay++] = L;
        if (*p == '/') p++;
    }
    for (i = 0; i < nlay; i++) { lay[i].first = lay[i].count = 0; if (lay[i].source >= 0) valid[nv++] = i; }
    for (k = 0; k < nv; k++) {
        LAYER *L = &lay[valid[k]]; int later, cap, give, j;
        if (!L->pool) continue;
        later = nv - k - 1;
        for (j = 0; j < k; j++) if (!lay[valid[j]].pool) later++;
        cap = left - later;
        give = L->pool < cap ? L->pool : cap;
        if (give < 1) give = left > 0 ? 1 : 0;
        L->count = give; left -= give;
    }
    {
        int nf = 0, f[NL], each, rem;
        for (k = 0; k < nv; k++) if (!lay[valid[k]].pool) f[nf++] = valid[k];
        if (nf && left > 0) {
            each = left / nf; rem = left % nf;
            for (k = 0; k < nf; k++) lay[f[k]].count = each + (k < rem ? 1 : 0);
        }
    }
    for (i = 0; i < nlay; i++) { lay[i].first = at; at += lay[i].count; }
}

/* ================================================================ driving one Sound Recorder */
typedef struct { int id; int x, y, w, h; } PART;
static PART strip[] = {   /* wave display: Sound Recorder draws it at its own size, so it keeps that width */
    {SR_STATUS, 4, 9, 80, 16}, {SR_WAVE, 88, 1, 133, 32}, {SR_POS, 228, 10, 66, 14}, {SR_LEN, 298, 10, 66, 14},
    {SR_SCROLL, 370, 9, 270, 17}, {SR_REW, 648, 3, 52, 28}, {SR_FWD, 702, 3, 52, 28}, {SR_PLAY, 756, 3, 52, 28},
    {SR_STOP, 810, 3, 52, 28}, {SR_REC, 864, 3, 52, 28}};
#define NPART (sizeof strip / sizeof strip[0])
static int hidden[] = {300, 301, 304, 302, 305};


static void press(int r, int id)
{
    SendMessage(rw[r], WM_COMMAND, id, MAKELPARAM(GetDlgItem(rw[r], id), BN_CLICKED));
}
static void menu(int r, int id) { SendMessage(rw[r], WM_COMMAND, id, 0L); }
static int length_cs(int r)       /* "0.52 sec." -> 52 */
{
    char t[32]; int s = 0, c = 0; char *p;
    GetDlgItemText(rw[r], SR_LEN, t, sizeof t);
    s = atoi(t);
    p = t; while (*p && *p >= '0' && *p <= '9') p++;
    if (*p) { p++; c = atoi(p); }
    return s * 100 + c;
}
static BOOL is_playing(int r)
{
    char t[24];
    GetDlgItemText(rw[r], SR_STATUS, t, sizeof t);
    return t[0] == 'P';
}
static void drop_file(int r, const char *fn)
{
    HGLOBAL h = GlobalAlloc(GMEM_MOVEABLE | GMEM_SHARE | GMEM_ZEROINIT, 160);
    LPSTR p = GlobalLock(h);
    *(WORD FAR *)p = 8; *(int FAR *)(p + 2) = 10; *(int FAR *)(p + 4) = 10; *(int FAR *)(p + 6) = 0;
    lstrcpy(p + 8, fn);
    GlobalUnlock(h);
    SendMessage(rw[r], WM_DROPFILES, (WPARAM)h, 0L);
}
static void seek_pct(int r, int pct)
{
    HWND sb = GetDlgItem(rw[r], SR_SCROLL); int lo, hi, pos;
    GetScrollRange(sb, SB_CTL, &lo, &hi);
    pos = lo + (int)((long)(hi - lo) * pct / 100);
    SendMessage(rw[r], WM_HSCROLL, SB_THUMBPOSITION, MAKELPARAM(pos, sb));
    SendMessage(rw[r], WM_HSCROLL, SB_ENDSCROLL, MAKELPARAM(pos, sb));
}

static void layout_strip(int r)   /* Sound Recorder re-lays its controls when it loads a file: line them up again */
{
    int i;
    if (!assembled) return;
    for (i = 0; i < 5; i++) ShowWindow(GetDlgItem(rw[r], hidden[i]), SW_HIDE);
    for (i = 0; i < NPART; i++)
        SetWindowPos(GetDlgItem(rw[r], strip[i].id), NULL, strip[i].x, strip[i].y, strip[i].w, strip[i].h, SWP_NOZORDER | SWP_NOACTIVATE);
}

static void pump(void)
{
    MSG m;
    while (PeekMessage(&m, 0, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessage(&m); }
}

/* one layer's steps, on one recorder; returns its final length in centiseconds */
static int run_steps(int r, LAYER *L)
{
    int i, len, clip, first_c = -1, needcopy = 0;
    bs_arm(rt[r], 0, 0, 0);            /* Sound Recorder plays a dropped file: that play is silent */
    drop_file(r, sound_file(L->source));
    {   /* it starts playing the dropped file a moment later: stop it as soon as it does */
        DWORD t = timeGetTime();
        while (timeGetTime() - t < 400) {
            pump();
            if (is_playing(r)) { bs_armstop(rt[r], 0, 1); press(r, SR_STOP); break; }
        }
    }
    press(r, SR_REW);
    len = length_cs(r);
    clip = len;
    for (i = 0; i < L->nst; i++) {
        if (L->st[i].op == 'C') { first_c = i; break; }
        if (L->st[i].op == 'P' || L->st[i].op == 'X') { needcopy = 1; break; }
    }
    if (needcopy) menu(r, SR_COPY);
    for (i = 0; i < L->nst; i++) {
        STEP *s = &L->st[i];
        int predict = len;
        switch (s->op) {
        case '<': predict = len * 2; break;
        case 'P': predict = len + clip; break;
        case 'I': predict = len + sound_cs(s->sound); break;
        case 'X': case 'M': predict = len > clip ? len : clip; if (s->op == 'M' && sound_cs(s->sound) > predict) predict = sound_cs(s->sound); break;
        }
        if (predict > 3000) continue;                       /* the 30 s rule: both editions skip it */
        switch (s->op) {
        case '+': menu(r, SR_VOLUP); break;
        case '-': menu(r, SR_VOLDN); break;
        case '>': menu(r, SR_FASTER); break;
        case '<': menu(r, SR_SLOWER); break;
        case 'E': menu(r, SR_ECHO); break;
        case 'R': menu(r, SR_REVERSE); break;
        case '[': menu(r, SR_DELBEFORE); break;
        case ']': menu(r, SR_DELAFTER); break;
        case 'C': menu(r, SR_COPY); clip = len; break;
        case 'P': menu(r, SR_PASTE); break;
        case 'X': menu(r, SR_PASTEMIX); break;
        case 'I': HookPending(sound_file(s->sound)); menu(r, SR_INSERT); break;
        case 'M': HookPending(sound_file(s->sound)); menu(r, SR_MIX); break;
        case '@': seek_pct(r, s->arg); break;
        }
        len = length_cs(r);
    }
    press(r, SR_REW);
    return len;
}

static void stop_rec(int r, DWORD id, int fade_ms);

static char lastSig[1400];
static int layer_len[NL];
static void signature(char *out)    /* what Sound Recorder has to do: sources, steps, pools */
{
    int i, k; char *o = out;
    for (i = 0; i < nlay; i++) {
        o += sprintf(o, "%d:%d:%d:", lay[i].source, lay[i].first, lay[i].count);
        for (k = 0; k < lay[i].nst && o - out < 1300; k++) o += sprintf(o, "%c%d.%d", lay[i].st[k].op, lay[i].st[k].arg, lay[i].st[k].sound);
        *o++ = '|';
    }
    *o = 0;
}
static char pendingDna[1100];
static BOOL assembling;
static int poll_host(void);
static void layer_replies(void)
{
    int i;
    for (i = 0; i < nlay; i++)
        if (lay[i].count) say("layer %d %d %d %d %ld", i, lay[i].first, lay[i].count, sound_rate(lay[i].source), (long)layer_len[i] * sound_rate(lay[i].source) / 100);
        else say("layer %d %d 0 0 0", i, lay[i].first);
}
static void build(const char *dna)
{
    DWORD t0 = timeGetTime();
    int i, r, tb;
    static char sig[1400], next[1100], mine[1100];
    /* during the assembly, or while a build runs (notes are served between its steps), the newest DNA waits */
    if (assembling || building) { lstrcpyn(pendingDna, dna, sizeof pendingDna); return; }
    lstrcpyn(mine, dna, sizeof mine);    /* dna points into the host-line buffer, which notes reuse during the build */
    dna = mine;
    dna_parse(dna);
    signature(sig);
    if (!strcmp(sig, lastSig)) {        /* only voice genes or globals changed: Sound Recorder has nothing to do */
        lstrcpyn(dnaText, dna, sizeof dnaText);
        if (hDna) SetWindowText(hDna, dnaText);
        layer_replies();
        if (selLayer >= nlay) selLayer = 0;
        panel_refresh();
        say("built 0");
        return;
    }
    building = TRUE;
    tb = bank;
    HookActive(TRUE);
    /* in place, one recorder at a time; between recorders the host's notes are served. A note on a recorder
       already rebuilt plays its new sound, at the pitch the host meant (see play_rec), so nothing goes silent */
    for (i = 0; i < nlay; i++) {
        LAYER *L = &lay[i];
        int len = 0;
        for (r = L->first; r < L->first + L->count; r++) {
            int a = tb * NR + r;
            stop_rec(a, 0, 1500);        /* an old note on it rings out (the card fades it over 1.5 s) */
            rlayer[a] = i;
            len = run_steps(a, L);
            recRate[a] = sound_rate(L->source);
            layout_strip(a);
            poll_host();
            pump();
        }
        layer_len[i] = len;
    }
    HookActive(FALSE);
    for (r = 0; r < NALL; r++) hostRate[r] = recRate[r];   /* the host learns the new rates from the replies */
    lstrcpyn(dnaText, dna, sizeof dnaText);
    if (hDna) SetWindowText(hDna, dnaText);
    strcpy(lastSig, sig);
    building = FALSE;
    layer_replies();
    if (hMain) InvalidateRect(hMain, NULL, FALSE);
    if (selLayer >= nlay) selLayer = 0;
    panel_refresh();
    say("built %ld", (long)(timeGetTime() - t0));
    if (pendingDna[0]) { lstrcpy(next, pendingDna); pendingDna[0] = 0; build(next); }
}

/* ================================================================ notes */
static void play_rec(int r, DWORD id, DWORD hz, WORD vol)
{
    if (r < 0 || r >= NR) return;
    r = AR(r);
    if (!rw[r]) return;
    if (hostRate[r] && recRate[r] && hostRate[r] != recRate[r]) hz = hz * recRate[r] / hostRate[r];   /* rebuilt mid-change */
    {
    DWORD t0 = timeGetTime(), t1, t2, t3;
    if (rplay[r] || is_playing(r)) { bs_armstop(rt[r], id, 5); press(r, SR_STOP); }
    t1 = timeGetTime();
    press(r, SR_REW);
    t2 = timeGetTime();
    bs_arm(rt[r], id, hz, vol);
    press(r, SR_PLAY);
    t3 = timeGetTime();
    if (t3 - t0 > 30) logf_("slow play rec %d: stop %ld rew %ld play %ld ms", r, t1 - t0, t2 - t1, t3 - t2);
    }
    rplay[r] = TRUE;
}
static void stop_rec(int r, DWORD id, int fade_ms)   /* r: an absolute recorder (bank * NR + row) */
{
    if (r < 0 || r >= NALL || !rw[r]) return;
    if (rplay[r] || is_playing(r)) {
        bs_armstop(rt[r], id, (WORD)fade_ms);
        press(r, SR_STOP);
    }
    rplay[r] = FALSE;
}
static void watch_ends(void)
{
    static DWORD last; int r;
    if (timeGetTime() - last < 25) return;
    last = timeGetTime();
    for (r = 0; r < NR; r++) if (rplay[AR(r)] && !is_playing(AR(r))) { rplay[AR(r)] = FALSE; say("end %d", r); }
}

/* ================================================================ the clock: the host's time after a resume */
static void set_time(int Y, int M, int D, int h, int m, int s)
{
    union REGS rg;
    rg.h.ah = 0x2B; rg.x.cx = Y; rg.h.dh = (unsigned char)M; rg.h.dl = (unsigned char)D; intdos(&rg, &rg);
    rg.h.ah = 0x2D; rg.h.ch = (unsigned char)h; rg.h.cl = (unsigned char)m; rg.h.dh = (unsigned char)s; rg.h.dl = 0; intdos(&rg, &rg);
}


/* ================================================================ the panel: editing the DNA from Windows */
/* The panel's controls change the DNA text the same way the host's core does (packages/basilisk-synth/core):
   steps are appended to the layer, a gene or a global replaces its last occurrence. Windows rebuilds what it
   must and tells the host with an `edit` line. */
#define ID_SOUND 1100      /* + sound index 0..3 */
#define ID_STEP 1120       /* + effect index */
#define ID_UNDO 1140
#define ID_CLEAR 1141
#define ID_LAYERPREV 1142
#define ID_LAYERNEXT 1143
#define ID_HARM 1144
#define ID_SB 1160         /* + scrollbar index */
#define ID_VAL 1180        /* + value label index */
static const char *panelSounds[4] = {"chimes", "ding", "ringin", "ringout"};
static const char *stepNames[10] = {"Louder", "Softer", "Faster", "Slower", "Echo", "Reverse", "Del <", "Del >", "Copy", "Paste"};
static const char stepOps[10] = {'+', '-', '>', '<', 'E', 'R', '[', ']', 'C', 'P'};
static const char *harmNames[6] = {"Single", "Octave", "Fifth", "Major", "Minor", "Octaves"};
static const char *harmGenes[6] = {"H0", "H0,12", "H0,7", "H0,4,7", "H0,3,7", "H-12,0,12"};
typedef struct { const char *label; char letter; int lo, hi; BOOL global; } SLIDER;
static SLIDER sliders[] = {
    {"Voices", '#', 1, 16, FALSE}, {"Transpose", 'T', -24, 24, FALSE}, {"Unison", 'U', 1, 8, FALSE}, {"Level", 'L', 0, 400, FALSE},
    {"Attack", 'A', 0, 2000, TRUE}, {"Decay", 'D', 0, 2000, TRUE}, {"Sustain", 'S', 0, 100, TRUE}, {"Release", 'R', 0, 3000, TRUE}};
#define NSL (sizeof sliders / sizeof sliders[0])
static HWND hSb[NSL], hVal[NSL], hLayerLbl, hHarm;
static int harmIdx;

/* the span of layer i in dnaText (or of the globals, i = -1) */
static void span(int li, int *b, int *e)
{
    int i = 0, k = 0, n = strlen(dnaText), semi;
    for (semi = 0; semi < n && dnaText[semi] != ';'; semi++) {}
    if (li < 0) { *b = semi < n ? semi + 1 : n; *e = n; return; }
    *b = 0;
    for (k = 0; k < semi && i < li; k++) if (dnaText[k] == '/') { i++; *b = k + 1; }
    if (i < li) { *b = *e = -1; return; }
    for (*e = *b; *e < semi && dnaText[*e] != '/'; (*e)++) {}
}
static void splice(int b, int e, const char *ins)     /* replace dnaText[b..e) */
{
    static char t[1200];
    int n = strlen(dnaText), m = strlen(ins);
    if (n - (e - b) + m >= (int)sizeof dnaText - 1) return;
    memcpy(t, dnaText, b); memcpy(t + b, ins, m); strcpy(t + b + m, dnaText + e);
    strcpy(dnaText, t);
}
/* the next token of a layer (same grammar as the core); returns its kind: 's' step, 'g' gene, 0 = end */
static int token(const char *p, int *len, char *letter)
{
    const char *q = p;
    char c = *q;
    if (!c || c == '/' || c == ';') return 0;
    q++;
    *letter = c;
    switch (c) {
    case '+': case '-': case '>': case '<': case 'E': case 'R': case '[': case ']': case 'C': case 'P': case 'X':
        *len = 1; return 's';
    case '@': getint(&q, 0); *len = (int)(q - p); return 's';
    case 'I': case 'M': while (isname(*q)) q++; *len = (int)(q - p); return 's';
    case '#': case 'T': case 'L': getint(&q, 0); *len = (int)(q - p); return 'g';
    case 'H': do { if (*q == ',') q++; getint(&q, 0); } while (*q == ','); *len = (int)(q - p); return 'g';
    case 'U': getint(&q, 1); if (*q == '~') { q++; getint(&q, 0); } *len = (int)(q - p); return 'g';
    case 'F': *len = 1; return 'g';
    }
    *len = 1; return 'x';
}
static void layer_edit(int li, int what, char letter, const char *ins)   /* what: 0 set gene, 1 undo step, 2 clear steps */
{
    int b, e, p, last = -1, lastLen = 0, len; char L;
    span(li, &b, &e);
    if (b < 0) return;
    p = b; while (isname(dnaText[p])) p++;
    while (p < e) {
        int k = token(dnaText + p, &len, &L);
        if (!k) break;
        if ((what == 0 && k == 'g' && L == letter) || (what == 2 && k == 's')) { splice(p, p + len, ""); e -= len; continue; }
        if (what == 1 && k == 's') { last = p; lastLen = len; }
        p += len;
    }
    if (what == 1 && last >= 0) splice(last, last + lastLen, "");
    if (what == 0 && ins && *ins) { span(li, &b, &e); splice(e, e, ins); }
}
static void global_set(char letter, int v)
{
    int b, e, p; char tok[16];
    if (!strchr(dnaText, ';')) strcat(dnaText, ";");
    span(-1, &b, &e);
    for (p = b; p < e;) {
        if (dnaText[p] == letter) {
            const char *q = dnaText + p + 1; int len;
            getint(&q, 0); len = (int)(q - (dnaText + p));
            splice(p, p + len, ""); e -= len; continue;
        }
        p++;
    }
    sprintf(tok, "%c%d", letter, v);
    span(-1, &b, &e); splice(e, e, tok);
}
static int gene_value(int li, char letter, int dflt)
{
    int b, e, p, len, v = dflt; char L;
    span(li, &b, &e);
    if (b < 0) return dflt;
    p = b; while (isname(dnaText[p])) p++;
    while (p < e) {
        int k = token(dnaText + p, &len, &L);
        if (!k) break;
        if (k == 'g' && L == letter && letter != 'F') { const char *q = dnaText + p + 1; v = getint(&q, dflt); }
        p += len;
    }
    return v;
}
static int global_value(char letter, int dflt)
{
    int b, e, p, v = dflt;
    span(-1, &b, &e);
    for (p = b; p < e; p++) if (dnaText[p] == letter) { const char *q = dnaText + p + 1; v = getint(&q, dflt); }
    return v;
}
static void harmony_from_dna(void)   /* the Harmony button follows the DNA's H gene for the selected layer */
{
    int b, e, p, len, k; char L; static char t[64];
    t[0] = 0; harmIdx = 0;
    span(selLayer, &b, &e);
    if (b < 0) return;
    p = b; while (isname(dnaText[p])) p++;
    while (p < e) {
        int kind = token(dnaText + p, &len, &L);
        if (!kind) break;
        if (kind == 'g' && L == 'H' && len < (int)sizeof t) { memcpy(t, dnaText + p, len); t[len] = 0; }
        p += len;
    }
    for (k = 0; k < 6; k++) if (!strcmp(t, harmGenes[k])) harmIdx = k;
    if (t[0] && !strcmp(t, "H0")) harmIdx = 0;
}
static void panel_refresh(void)
{
    int i; char t[48];
    if (!hSb[0]) return;
    harmony_from_dna();
    if (hHarm) SetWindowText(hHarm, harmNames[harmIdx]);
    if (hDna) SetWindowText(hDna, dnaText);
    for (i = 0; i < (int)NSL; i++) {
        SLIDER *S = &sliders[i];
        int dflt = S->letter == '#' ? (lay[selLayer].count ? lay[selLayer].count : 1) : S->letter == 'U' ? 1 : S->letter == 'L' ? 100 :
                   S->letter == 'S' ? 100 : S->letter == 'R' ? 120 : 0;
        int v = S->global ? global_value(S->letter, dflt) : gene_value(selLayer, S->letter, dflt);
        SetScrollPos(hSb[i], SB_CTL, v, TRUE);
        sprintf(t, "%d", v);
        SetWindowText(hVal[i], t);
    }
    sprintf(t, "Layer %d of %d", selLayer + 1, nlay);
    SetWindowText(hLayerLbl, t);
}
static void edited(BOOL rebuild)
{
    static char line[1200];
    sprintf(line, "edit %s", dnaText);
    bs_line(line);
    if (rebuild) build(dnaText);
    else {
        envA = global_value('A', 0); envD = global_value('D', 0); envS = global_value('S', 100); envR = global_value('R', 120);
        bs_env((WORD)envA, (WORD)envD, (WORD)envS);
    }
    panel_refresh();
}
static void panel_command(int id)
{
    int b, e;
    if (building) return;
    if (id >= ID_SOUND && id < ID_SOUND + 4) {
        span(selLayer, &b, &e);
        if (b >= 0) { int p = b; while (isname(dnaText[p])) p++; splice(b, p, panelSounds[id - ID_SOUND]); edited(TRUE); }
    } else if (id >= ID_STEP && id < ID_STEP + 10) {
        char tok[2]; tok[0] = stepOps[id - ID_STEP]; tok[1] = 0;
        span(selLayer, &b, &e);
        if (b >= 0) { splice(e, e, tok); edited(TRUE); }
    } else if (id == ID_UNDO) { layer_edit(selLayer, 1, 0, NULL); edited(TRUE); }
    else if (id == ID_CLEAR) { layer_edit(selLayer, 2, 0, NULL); edited(TRUE); }
    else if (id == ID_LAYERPREV || id == ID_LAYERNEXT) {
        selLayer += id == ID_LAYERNEXT ? 1 : -1;
        if (selLayer < 0) selLayer = nlay - 1; if (selLayer >= nlay) selLayer = 0;
        InvalidateRect(hMain, NULL, FALSE);
        panel_refresh();
    } else if (id == ID_HARM) {
        harmIdx = (harmIdx + 1) % 6;
        SetWindowText(hHarm, harmNames[harmIdx]);
        layer_edit(selLayer, 0, 'H', harmGenes[harmIdx]);
        edited(FALSE);
    }
}
static void panel_scroll(HWND sb, int code, int pos)
{
    int i, v, lo, hi;
    for (i = 0; i < (int)NSL && hSb[i] != sb; i++) {}
    if (i == (int)NSL || building) return;
    GetScrollRange(sb, SB_CTL, &lo, &hi);
    v = GetScrollPos(sb, SB_CTL);
    switch (code) {
    case SB_LINELEFT: v--; break; case SB_LINERIGHT: v++; break;
    case SB_PAGELEFT: v -= (hi - lo) / 10 ? (hi - lo) / 10 : 1; break; case SB_PAGERIGHT: v += (hi - lo) / 10 ? (hi - lo) / 10 : 1; break;
    case SB_THUMBTRACK: case SB_THUMBPOSITION: v = pos; break;
    case SB_ENDSCROLL: break;
    default: return;
    }
    if (v < lo) v = lo; if (v > hi) v = hi;
    SetScrollPos(sb, SB_CTL, v, TRUE);
    { char t[16]; sprintf(t, "%d", v); SetWindowText(hVal[i], t); }
    if (code == SB_THUMBTRACK) return;                  /* apply when the thumb is let go */
    if (sliders[i].global) global_set(sliders[i].letter, v);
    else {
        char tok[24];
        if (sliders[i].letter == 'U') sprintf(tok, "U%d~%d", v, v > 1 ? 15 : 0);
        else sprintf(tok, "%c%d", sliders[i].letter, v);
        layer_edit(selLayer, 0, sliders[i].letter, tok);
    }
    edited(sliders[i].letter == '#');                    /* pool sizes are Sound Recorder's business; the rest is not */
}

/* the DNA line can be typed into: Enter applies it (Windows rebuilds and tells the host), Esc puts it back */
static WNDPROC oldDnaProc;
long FAR PASCAL __export DnaEditProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_KEYDOWN && w == VK_RETURN) {
        static char t[1100];
        GetWindowText(h, t, sizeof t);
        if (t[0] && !building) { lstrcpyn(dnaText, t, sizeof dnaText); edited(TRUE); }
        return 0;
    }
    if (m == WM_KEYDOWN && w == VK_ESCAPE) { SetWindowText(h, dnaText); return 0; }
    if (m == WM_CHAR && (w == '\r' || w == 27)) return 0;
    return CallWindowProc((FARPROC)oldDnaProc, h, m, w, l);
}

static HFONT panelFont;
static HWND mk(const char *cls, const char *text, DWORD st, int x, int y, int w, int h, int id)
{
    HWND c = CreateWindow(cls, text, WS_CHILD | st, x, y, w, h, hMain, (HMENU)id, hInst, NULL);
    SendMessage(c, WM_SETFONT, (WPARAM)panelFont, 0L);
    return c;
}
/* the panel appears in four groups, one after another */
static void panel_create(int group)
{
    int i, x;
    if (!panelFont) panelFont = CreateFont(14, 0, 0, 0, FW_NORMAL, 0, 0, 0, ANSI_CHARSET, 0, 0, 0, VARIABLE_PITCH | FF_SWISS, "Arial");
    switch (group) {
    case 0:
        mk("STATIC", "DNA", WS_VISIBLE, 8, PANEL + 6, 30, 16, -1);
        hDna = mk("EDIT", dnaText, WS_VISIBLE | WS_BORDER | ES_AUTOHSCROLL, 40, PANEL + 2, 830, 22, 1099);
        SendMessage(hDna, EM_LIMITTEXT, 1024, 0L);
        oldDnaProc = (WNDPROC)GetWindowLong(hDna, GWL_WNDPROC);
        SetWindowLong(hDna, GWL_WNDPROC, (LONG)MakeProcInstance((FARPROC)DnaEditProc, hInst));
        break;
    case 1:
        mk("STATIC", "Sound", WS_VISIBLE, 8, PANEL + 36, 40, 16, -1);
        for (i = 0; i < 4; i++) mk("BUTTON", panelSounds[i], WS_VISIBLE | BS_PUSHBUTTON, 50 + i * 62, PANEL + 32, 60, 24, ID_SOUND + i);
        mk("STATIC", "Effects", WS_VISIBLE, 306, PANEL + 36, 46, 16, -1);
        for (i = 0, x = 354; i < 10; i++, x += 52) mk("BUTTON", stepNames[i], WS_VISIBLE | BS_PUSHBUTTON, x, PANEL + 32, 50, 24, ID_STEP + i);
        break;
    case 2:
        mk("BUTTON", "<", WS_VISIBLE | BS_PUSHBUTTON, 8, PANEL + 62, 22, 24, ID_LAYERPREV);
        hLayerLbl = mk("STATIC", "Layer 1 of 1", WS_VISIBLE | SS_CENTER, 32, PANEL + 66, 86, 16, -1);
        mk("BUTTON", ">", WS_VISIBLE | BS_PUSHBUTTON, 120, PANEL + 62, 22, 24, ID_LAYERNEXT);
        mk("BUTTON", "Undo", WS_VISIBLE | BS_PUSHBUTTON, 150, PANEL + 62, 50, 24, ID_UNDO);
        mk("BUTTON", "Clear", WS_VISIBLE | BS_PUSHBUTTON, 202, PANEL + 62, 50, 24, ID_CLEAR);
        mk("STATIC", "Harmony", WS_VISIBLE, 262, PANEL + 66, 54, 16, -1);
        hHarm = mk("BUTTON", harmNames[harmIdx], WS_VISIBLE | BS_PUSHBUTTON, 318, PANEL + 62, 70, 24, ID_HARM);
        for (i = 0; i < 4; i++) {
            mk("STATIC", sliders[i].label, WS_VISIBLE, 398 + i * 120, PANEL + 60, 70, 14, -1);
            hSb[i] = mk("SCROLLBAR", "", WS_VISIBLE | SBS_HORZ, 398 + i * 120, PANEL + 74, 84, 14, ID_SB + i);
            SetScrollRange(hSb[i], SB_CTL, sliders[i].lo, sliders[i].hi, FALSE);
            hVal[i] = mk("STATIC", "", WS_VISIBLE, 484 + i * 120, PANEL + 74, 32, 14, ID_VAL + i);
        }
        break;
    case 3:
        for (i = 4; i < (int)NSL; i++) {
            int k = i - 4;
            mk("STATIC", sliders[i].label, WS_VISIBLE, 8 + k * 216, PANEL + 96, 60, 14, -1);
            hSb[i] = mk("SCROLLBAR", "", WS_VISIBLE | SBS_HORZ, 66 + k * 216, PANEL + 96, 110, 14, ID_SB + i);
            SetScrollRange(hSb[i], SB_CTL, sliders[i].lo, sliders[i].hi, FALSE);
            hVal[i] = mk("STATIC", "", WS_VISIBLE, 180 + k * 216, PANEL + 96, 36, 14, ID_VAL + i);
        }
        panel_refresh();
        break;
    }
    UpdateWindow(hMain);
}

/* ================================================================ assembly */
typedef struct { RECT win; RECT part[NPART]; int stage; } FLY;
static FLY fly[NR];

static void lerp_rect(RECT *o, const RECT *a, int x, int y, int w, int h, long f)   /* f in 0..1000 */
{
    o->left = a->left + (int)((long)(x - a->left) * f / 1000);
    o->top = a->top + (int)((long)(y - a->top) * f / 1000);
    o->right = (a->right - a->left) + (int)((long)(w - (a->right - a->left)) * f / 1000);
    o->bottom = (a->bottom - a->top) + (int)((long)(h - (a->bottom - a->top)) * f / 1000);
}
static long ease(long f) { /* smoothstep, 0..1000 */ if (f < 0) f = 0; if (f > 1000) f = 1000; return f * f / 1000 * (3000 - 2 * f) / 1000; }

/* stage 1: the menu bar goes; 2: the title bar and frame go, and it becomes part of BASILISK 16;
   3: the frames and captions inside go; 4..: the controls line up and the strip glides into its row */
static void to_child(int r)
{
    RECT c; POINT o = {0, 0};
    LONG st = GetWindowLong(rw[r], GWL_STYLE);
    GetClientRect(rw[r], &c);
    ClientToScreen(rw[r], &o);
    ScreenToClient(hMain, &o);
    ShowWindow(rw[r], SW_HIDE);
    st &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME | WS_OVERLAPPED);
    SetWindowLong(rw[r], GWL_STYLE, st | WS_CHILD | WS_CLIPSIBLINGS);
    SetParent(rw[r], hMain);
    SetWindowPos(rw[r], HWND_TOP, o.x, o.y, c.right, c.bottom, SWP_NOACTIVATE);
    ShowWindow(rw[r], SW_SHOWNA);
    UpdateWindow(rw[r]);
}

static void step_fly(int r, long ms)   /* ms since this recorder's turn began */
{
    FLY *F = &fly[r];
    int i;
    if (F->stage == 0 && ms >= 0) { SetMenu(rw[r], NULL); DrawMenuBar(rw[r]); UpdateWindow(rw[r]); F->stage = 1; }
    if (F->stage == 1 && ms >= 90) { to_child(r); F->stage = 2; }
    if (F->stage == 2 && ms >= 180) {
        for (i = 0; i < 5; i++) ShowWindow(GetDlgItem(rw[r], hidden[i]), SW_HIDE);
        UpdateWindow(rw[r]);
        GetWindowRect(rw[r], &F->win); ScreenToClient(hMain, (POINT *)&F->win.left); ScreenToClient(hMain, (POINT *)&F->win.right);
        for (i = 0; i < NPART; i++) {
            HWND c = GetDlgItem(rw[r], strip[i].id);
            GetWindowRect(c, &F->part[i]);
            ScreenToClient(rw[r], (POINT *)&F->part[i].left); ScreenToClient(rw[r], (POINT *)&F->part[i].right);
        }
        F->stage = 3;
    }
    if (F->stage == 3) {
        /* the controls line up (180..420 ms), then the strip glides into its row (420..700 ms) */
        long f1 = ease((ms - 180) * 1000 / 240), f2 = ease((ms - 420) * 1000 / 280);
        RECT o; int tx = STRIPX, ty = ROW0 + r * ROWH;
        int ww = F->win.right - F->win.left, wh = F->win.bottom - F->win.top;
        /* while lining up, the window is as wide as both layouts need; then it glides and narrows */
        int midw = ww > STRIPW ? ww : STRIPW, midh = wh;
        if (f2 <= 0) {
            HDWP dw;
            if (f1 > 0) {
                SetWindowPos(rw[r], NULL, F->win.left, F->win.top, ww + (int)((long)(midw - ww) * f1 / 1000), midh, SWP_NOZORDER | SWP_NOACTIVATE);
            }
            dw = BeginDeferWindowPos(NPART);
            for (i = 0; i < NPART; i++) {
                lerp_rect(&o, &F->part[i], strip[i].x, strip[i].y, strip[i].w, strip[i].h, f1);
                dw = DeferWindowPos(dw, GetDlgItem(rw[r], strip[i].id), NULL, o.left, o.top, o.right, o.bottom, SWP_NOZORDER | SWP_NOACTIVATE);
            }
            EndDeferWindowPos(dw);
        } else {
            RECT a; a.left = F->win.left; a.top = F->win.top; a.right = F->win.left + midw; a.bottom = F->win.top + midh;
            lerp_rect(&o, &a, tx, ty, STRIPW, STRIPH, f2);
            SetWindowPos(rw[r], NULL, o.left, o.top, o.right, o.bottom, SWP_NOZORDER | SWP_NOACTIVATE);
            for (i = 0; i < NPART; i++)   /* Sound Recorder moves its controls when resized: keep them in line */
                SetWindowPos(GetDlgItem(rw[r], strip[i].id), NULL, strip[i].x, strip[i].y, strip[i].w, strip[i].h, SWP_NOZORDER | SWP_NOACTIVATE);
        }
        UpdateWindow(hMain);
        UpdateWindow(rw[r]);
        if (f2 >= 1000) F->stage = 4;
    }
}

static int poll_host(void);

static void assemble(void)
{
    DWORD t0 = timeGetTime();
    long gap = 185, first_extra = 220;   /* the first recorder is shown slowly; the rest follow */
    int r, done = 0;
    RECT full;
    assembling = TRUE;
    SetRect(&full, 0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN));
    /* BASILISK 16 opens under the recorders, growing from the middle (0..350 ms) */
    {   /* under the lowest recorder (and the clock): they stay on top until their turn */
        HWND x, low = NULL; int k;
        for (x = GetWindow(GetDesktopWindow(), GW_CHILD); x; x = GetWindow(x, GW_HWNDNEXT)) {
            if (x == hClock) low = x;
            for (k = 0; k < NR; k++) if (x == rw[k]) low = x;
        }
        SetWindowPos(hMain, low, full.right / 2 - 40, full.bottom / 2 - 30, 80, 60, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    }
    for (;;) {
        long t = (long)(timeGetTime() - t0);
        long f = ease(t * 1000 / 350);
        int w = 80 + (int)((long)(full.right - 80) * f / 1000), h = 60 + (int)((long)(full.bottom - 60) * f / 1000);
        SetWindowPos(hMain, NULL, (full.right - w) / 2, (full.bottom - h) / 2, w, h, SWP_NOZORDER | SWP_NOACTIVATE);
        UpdateWindow(hMain);
        poll_host();
        if (f >= 1000) break;
    }
    /* the clock joins first: it glides over the recorders to the bottom right, then becomes part of BASILISK 16 */
    if (hClock) {
        RECT c, q, a; LONG st; DWORD t1; POINT o; int k;
        HWND own;
        GetWindowRect(hClock, &c);
        SetRect(&a, c.left, c.top, c.right, c.bottom);
        o.x = 1024 - 140; o.y = PANEL; ClientToScreen(hMain, &o);
        t1 = timeGetTime();
        for (;;) {
            long f = ease((long)(timeGetTime() - t1) * 1000 / 380);
            lerp_rect(&q, &a, o.x, o.y, 132, 124, f);
            SetWindowPos(hClock, HWND_TOPMOST, q.left, q.top, q.right, q.bottom, SWP_NOACTIVATE);   /* above every recorder */
            UpdateWindow(hClock);
            for (k = 0; k < NR; k++) UpdateWindow(rw[k]);
            UpdateWindow(hMain);
            poll_host();
            if (f >= 1000) break;
        }
        st = GetWindowLong(hClock, GWL_STYLE);
        SetWindowPos(hClock, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
        ShowWindow(hClock, SW_HIDE);
        SetMenu(hClock, NULL);
        SetWindowLong(hClock, GWL_STYLE, (st & ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_DLGFRAME)) | WS_CHILD | WS_BORDER);
        SetParent(hClock, hMain);
        SetWindowPos(hClock, HWND_TOP, 1024 - 140, PANEL, 132, 124, SWP_NOACTIVATE | SWP_SHOWWINDOW);
        UpdateWindow(hClock);
        (void)own;
    }
    t0 = timeGetTime();
    for (r = 0; r < NR; r++) fly[r].stage = 0;
    while (done < NR) {
        long t = (long)(timeGetTime() - t0);
        done = 0;
        for (r = 0; r < NR; r++) {
            long start = r == 0 ? 0 : first_extra + r * gap;
            long ms = t - start;
            if (r == 0) ms = ms * 10 / 18;                      /* the first one at half speed: see what happens */
            if (ms >= 0 && fly[r].stage < 4) {
                step_fly(r, ms);
                if (r == 0 && fly[0].stage >= 4 && !titleShown) {   /* the title, once the first recorder has left it */
                    RECT tr; SetRect(&tr, 0, 0, 300, ROW0 - 16); titleShown = TRUE;
                    InvalidateRect(hMain, &tr, TRUE); UpdateWindow(hMain);
                }
            }
            if (fly[r].stage >= 4) done++;
        }
        poll_host();
        pump();
    }
    {   /* the panel: four groups, one after another */
        int g; DWORD t2;
        for (g = 0; g < 4; g++) {
            panel_create(g);
            t2 = timeGetTime();
            while (timeGetTime() - t2 < 45) { poll_host(); pump(); }
        }
    }
    assembled = TRUE;
    assembling = FALSE;
    for (r = 0; r < NR; r++) layout_strip(r);
    for (r = 0; NB > 1 && r < NR; r++) {   /* a spare bank (NB 2) would take the same rows, hidden */
        HWND w = rw[NR + r]; LONG st;
        if (!w) continue;
        SetMenu(w, NULL);
        st = GetWindowLong(w, GWL_STYLE);
        st &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME | WS_OVERLAPPED | WS_VISIBLE);
        SetWindowLong(w, GWL_STYLE, st | WS_CHILD | WS_CLIPSIBLINGS);
        SetParent(w, hMain);
        SetWindowPos(w, HWND_BOTTOM, STRIPX, ROW0 + r * ROWH, STRIPW, STRIPH, SWP_NOACTIVATE | SWP_HIDEWINDOW);
        layout_strip(NR + r);
    }
    InvalidateRect(hMain, NULL, TRUE);
    UpdateWindow(hMain);
    {
        WORD z = 0; bs_report(1, &z, 0);
    }
    say("ready");
    logf_("ready: free resources user %d%% gdi %d%%", GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES));
    if (pendingDna[0]) { static char d[1100]; lstrcpy(d, pendingDna); pendingDna[0] = 0; build(d); }
}

/* ================================================================ host lines */
static DWORD curId;
static void host_line(char *s)
{
    char *a = strchr(s, ' ');
    char *rest = a ? a + 1 : "";
    if (a) *a = 0;
    if (!strcmp(s, "hi")) say("hi 1 311 %s", assembled ? "ready" : "wait");
    else if (!strcmp(s, "go")) { if (!assembled) assemble(); else say("ready"); }
    else if (!strcmp(s, "dna")) build(rest);
    else if (!strcmp(s, "on")) {
        int r = atoi(rest); char *p = strchr(rest, ' ');
        DWORD hz = p ? atol(p + 1) : 0; WORD vol = 65535;
        if (p) { p = strchr(p + 1, ' '); if (p) vol = (WORD)atol(p + 1); }
        play_rec(r, curId, hz, vol);
    }
    else if (!strcmp(s, "off")) { int r = atoi(rest); if (r >= 0 && r < NR) stop_rec(AR(r), curId, envR); }
    else if (!strcmp(s, "cut")) { int r = atoi(rest); if (r >= 0 && r < NR) stop_rec(AR(r), curId, 5); }
    else if (!strcmp(s, "panic")) { int r; for (r = 0; r < NALL; r++) stop_rec(r, 0, 5); }
    else if (!strcmp(s, "env")) {
        sscanf(rest, "%d %d %d %d", &envA, &envD, &envS, &envR);
        bs_env((WORD)envA, (WORD)envD, (WORD)envS);
    }
    else if (!strcmp(s, "sel")) { selLayer = atoi(rest); if (selLayer >= nlay || selLayer < 0) selLayer = 0; if (hMain) InvalidateRect(hMain, NULL, FALSE); panel_refresh(); }
    else if (!strcmp(s, "time")) {
        int Y, M, D, h, m, x;
        if (sscanf(rest, "%d %d %d %d %d %d", &Y, &M, &D, &h, &m, &x) == 6) set_time(Y, M, D, h, m, x);
    }
}

static int poll_host(void)   /* returns how many events it handled */
{
    static WORD e[140];
    static char acc[1200]; static int accn;
    int n, k, handled = 0;
    while ((n = bs_event(e, 140)) > 0) {
        int ty = e[0] >> 8;
        if (ty == 6 && n >= 3) { SetCursorPos(e[1], e[2]); handled++; continue; }   /* the host's pointer */
        if (ty == 4 || ty == 8) {
            for (k = 3; k < n && accn < (int)sizeof acc - 2; k++) { acc[accn++] = (char)(e[k] & 0xFF); acc[accn++] = (char)(e[k] >> 8); }
            if (ty == 4) {
                acc[accn] = 0; accn = 0;
                curId = MAKELONG(e[1], e[2]);
                host_line(acc);
            }
        }
        handled++;
    }
    watch_ends();
    return handled;
}

/* ================================================================ the window */
static const COLORREF layerColor[NL] = {RGB(0, 128, 0), RGB(0, 0, 160), RGB(160, 0, 0), RGB(128, 0, 128),
                                        RGB(0, 128, 128), RGB(160, 96, 0), RGB(64, 64, 64), RGB(96, 0, 48)};

static void paint(HWND h)
{
    PAINTSTRUCT ps; HDC dc = BeginPaint(h, &ps);
    RECT r; int i;
    HFONT big = CreateFont(26, 0, 0, 0, FW_BOLD, 0, 0, 0, ANSI_CHARSET, 0, 0, 0, VARIABLE_PITCH | FF_SWISS, "Arial");
    HFONT sm = CreateFont(14, 0, 0, 0, FW_NORMAL, 0, 0, 0, ANSI_CHARSET, 0, 0, 0, VARIABLE_PITCH | FF_SWISS, "Arial");
    HFONT of;
    GetClientRect(h, &r);
    SetBkMode(dc, TRANSPARENT);
    of = SelectObject(dc, big);
    SetTextColor(dc, RGB(0, 0, 128));
    if (titleShown) TextOut(dc, 12, 10, "BASILISK 16", 11);
    SelectObject(dc, sm);
    SetTextColor(dc, RGB(0, 0, 0));
    if (assembled) {
        static const char *hdr[] = {"Status", "Wave", "Position", "Length", "Seek", "Rewind", "Forward", "Play", "Stop", "Record"};
        int hx[] = {4, 88, 228, 298, 370, 648, 702, 756, 810, 864};
        for (i = 0; i < 10; i++) TextOut(dc, STRIPX + hx[i], ROW0 - 15, hdr[i], strlen(hdr[i]));
    }
    for (i = 0; i < NR; i++) {
        char t[4]; RECT b;
        int y = ROW0 + i * ROWH;
        int l = rlayer[AR(i)];
        SetRect(&b, 6, y + 4, 34, y + 28);
        if (l >= 0) {
            HBRUSH br = CreateSolidBrush(layerColor[l % NL]);
            FillRect(dc, &b, br); DeleteObject(br);
            SetTextColor(dc, RGB(255, 255, 255));
        } else SetTextColor(dc, RGB(0, 0, 0));
        wsprintf(t, "%d", i + 1);
        DrawText(dc, t, -1, &b, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    }
    SetTextColor(dc, RGB(0, 0, 0));

    SelectObject(dc, of);
    DeleteObject(big); DeleteObject(sm);
    EndPaint(h, &ps);
}

long FAR PASCAL __export MainProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    switch (m) {
    case WM_PAINT: paint(h); return 0;
    case WM_HSCROLL: panel_scroll((HWND)HIWORD(l), w, LOWORD(l)); return 0;
    case WM_CTLCOLOR:                  /* the panel's labels sit on the window's grey */
        if (HIWORD(l) == CTLCOLOR_STATIC) {
            static HBRUSH face;
            if (!face) face = CreateSolidBrush(GetSysColor(COLOR_BTNFACE));
            SetBkColor((HDC)w, GetSysColor(COLOR_BTNFACE));
            return (LRESULT)(WORD)face;
        }
        break;
    case WM_COMMAND: {
        int r;
        if (w >= 1100 && w < 1200) { panel_command(w); return 0; }
        /* a reparented recorder's buttons report to us: hand the click to its recorder */
        for (r = 0; r < NALL; r++) if (rw[r] && (HWND)LOWORD(l) && GetParent((HWND)LOWORD(l)) == rw[r]) {
            PostMessage(rw[r], WM_COMMAND, w, l);
            return 0;
        }
        break; }
    case WM_CLOSE: return 0;           /* BASILISK 16 is the machine: it does not close */
    case WM_DESTROY: PostQuitMessage(0); return 0;
    }
    return DefWindowProc(h, m, w, l);
}

/* ================================================================ start */
static HWND window_of(HINSTANCE hi)
{
    HWND x;
    for (x = GetWindow(GetDesktopWindow(), GW_CHILD); x; x = GetWindow(x, GW_HWNDNEXT))
        if (GetWindowWord(x, GWW_HINSTANCE) == (WORD)hi && !GetParent(x) && IsWindowVisible(x)) return x;
    return NULL;
}
static HWND launch(const char *cmd, int show)
{
    HINSTANCE h = WinExec(cmd, show);
    HWND w = NULL; DWORD t = timeGetTime();
    if ((UINT)h < 32) return NULL;
    while (!w && timeGetTime() - t < 8000) { pump(); w = window_of(h); }
    return w;
}

int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show)
{
    WNDCLASS wc; HINSTANCE hk; int r; HWND pm;
    hInst = hi;
    if (!bs_present()) { MessageBox(NULL, "The BASILISK 16 card is not here.", "BASILISK 16", MB_OK); return 1; }
    hk = LoadLibrary("C:\\BS\\SYNHOOK.DLL");
    if ((UINT)hk < 32) { logf_("no SYNHOOK.DLL"); return 1; }
    HookActive = (void (FAR PASCAL *)(BOOL))GetProcAddress(hk, "HOOKACTIVE");
    HookPending = (void (FAR PASCAL *)(LPCSTR))GetProcAddress(hk, "HOOKPENDING");
    HookInstall = (BOOL (FAR PASCAL *)(BOOL))GetProcAddress(hk, "HOOKINSTALL");
    if (!HookActive || !HookPending || !HookInstall) { logf_("SYNHOOK.DLL exports missing"); return 1; }
    HookInstall(TRUE);

    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = MainProc; wc.hInstance = hi; wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1); wc.lpszClassName = "Basilisk16";
    wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
    RegisterClass(&wc);
    hMain = CreateWindow("Basilisk16", "BASILISK 16 - Sound Recorder Synthesizer", WS_POPUP | WS_CAPTION | WS_CLIPCHILDREN,
                         0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), NULL, NULL, hi, NULL);

    /* the desktop as the visitor first sees it: Program Manager out of the way, a clock, sixteen recorders */
    pm = FindWindow("Progman", NULL);
    if (pm) ShowWindow(pm, SW_MINIMIZE);
    hClock = launch("CLOCK.EXE", SW_SHOWNOACTIVATE);
    if (hClock) { SendMessage(hClock, WM_COMMAND, 1, 0L); MoveWindow(hClock, 868, 8, 148, 160, TRUE); }   /* Settings > Analog */
    for (r = 0; r < NR; r++) {
        int c = r % 4, row = r / 4;
        rw[r] = launch("SOUNDREC.EXE C:\\WINDOWS\\DING.WAV", SW_SHOWNOACTIVATE);
        if (!rw[r]) { logf_("recorder %d did not start", r); continue; }
        rt[r] = GetWindowTask(rw[r]);
        rlayer[r] = 0;
        recRate[r] = hostRate[r] = 22050;
        MoveWindow(rw[r], 12 + c * 214 + row * 18, 18 + row * 176 + c * 10, 320, 186, TRUE);
        pump();
    }
    for (r = NR; r < NALL; r++) {        /* the spare bank: the same recorders, out of sight until a DNA needs them */
        rw[r] = launch("SOUNDREC.EXE C:\\WINDOWS\\DING.WAV", SW_SHOWNOACTIVATE);
        if (!rw[r]) { logf_("recorder %d did not start", r); continue; }
        ShowWindow(rw[r], SW_HIDE);
        rt[r] = GetWindowTask(rw[r]);
        rlayer[r] = 0;
        pump();
    }
    dna_parse(dnaText);
    signature(lastSig);
    { int i; for (i = 0; i < nlay; i++) layer_len[i] = 52; }
    logf_("SYNTH up: %d recorders, free resources: user %d%% gdi %d%%", NALL, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES));
    {   /* idle: the engine may freeze the machine here (the snapshot) */
        WORD z = 0; bs_report(2, &z, 0);
    }
    for (;;) {
        MSG m;
        if (PeekMessage(&m, 0, 0, 0, PM_REMOVE)) {
            if (m.message == WM_QUIT) break;
            TranslateMessage(&m); DispatchMessage(&m);
        } else {
            if (!poll_host()) bs_idle();
        }
    }
    HookInstall(FALSE);
    return 0;
}
