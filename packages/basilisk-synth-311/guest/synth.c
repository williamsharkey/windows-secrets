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
#include <shellapi.h>
#include "bslink.h"

#define NR 16
#define ROW0 66      /* the header above: title, envelope, presets, library, pan, offset, envelope points */
#define ROWH 30
#define STRIPX 44   /* left of the strips: a layer-colour bar (0..2) and the Calculator digit key (4..42) */
#define STRIPW 924
#define STRIPH 30   /* (a strip shorter than its row leaves gaps that make every repaint of the window slow) */
#define PANEL 550
#define KBY 684      /* the keyboard strip: mod wheel, pitch bend, Hold, Keys, five octaves */
#define ENVX 262
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
HWND hEnvRec;          /* a seventeenth Sound Recorder: its green wave display draws the envelope */
int envN[8], envT[8][8], envL[8][8];   /* the layers' amplitude envelopes as the host last sent them */
static void show_envelope(void);
static DWORD envWant;   /* the envelope view is redrawn when Windows is idle, 120 ms after the last change */
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
/* the built-in NAMEs, in core order (packages/basilisk-synth/core/dna.cpp kSoundNames, DNA.md 2.4: one name, one file) */
#define NSND 39
static const char *names[NSND] = {
    "chimes", "chord", "ding", "notify", "recycle", "ringin", "ringout", "start", "tada", "balloon",
    "batcrit", "batlow", "critstop", "default", "xpding", "error", "exclaim", "hwfail", "hwin", "hwout",
    "infobar", "logoff", "logon", "menu", "minimize", "xpnotify", "popup", "print", "xprecycle", "restore",
    "xpringin", "xpringout", "shutdown", "startup", "xpstart", "chimesxp", "chordxp", "dingxp", "tadaxp"};
static int sound_index(const char *s, int n)
{
    int i;
    for (i = 0; i < NSND; i++) if ((int)strlen(names[i]) == n && !strncmp(names[i], s, n)) return i;
    return -1;
}
/* DNA v2 library sounds (DNA.md 5.5): the library drive L: holds \LIBRARY.TSV (name, category, path, seconds,
   source) and the WAVs. A name found there gets an index from 1000 on, into this small table for the build. */
#define NLIB 32
static char libPath[NLIB][72], libName[NLIB][33];
static long libCs[NLIB], libRate[NLIB];
static int nlib;
static int lib_index(const char *name, int n)
{
    static char buf[1024]; static char line[400];
    HFILE f; OFSTRUCT of; int got, ln = 0, k;
    if (n > 32) return -1;
    for (k = 0; k < nlib; k++) if ((int)strlen(libName[k]) == n && !strncmp(libName[k], name, n)) return 1000 + k;   /* this build's */
    if (nlib >= NLIB) return -1;
    f = OpenFile("L:\\LIBRARY.TSV", &of, OF_READ);
    if (f == HFILE_ERROR) return -1;
    while ((got = _lread(f, buf, sizeof buf)) > 0) {
        int i;
        for (i = 0; i < got; i++) {
            char ch = buf[i];
            if (ch == '\n' || ln >= (int)sizeof line - 1) {
                line[ln] = 0; ln = 0;
                if (!strncmp(line, name, n) && line[n] == '\t') {   /* name TAB category TAB path TAB seconds */
                    char *c = strchr(line + n + 1, '\t'), *pth, *sec;
                    if (!c) continue;
                    pth = c + 1; sec = strchr(pth, '\t');
                    if (sec) *sec++ = 0;
                    k = nlib++;
                    strcpy(libPath[k], "L:"); strncat(libPath[k], pth, 60);
                    { char *cr = strchr(libPath[k], '\r'); if (cr) *cr = 0; }
                    libCs[k] = sec ? (long)(atof(sec) * 100) : 100;
                    libRate[k] = 22050;
                    {   /* the rate from the WAV header */
                        HFILE w = OpenFile(libPath[k], &of, OF_READ); BYTE h[64];
                        if (w != HFILE_ERROR) { if (_lread(w, h, 64) == 64) libRate[k] = *(long *)(h + 24); _lclose(w); }
                    }
                    memcpy(libName[k], name, n); libName[k][n] = 0;
                    _lclose(f);
                    return 1000 + k;
                }
            } else if (ch != '\r') line[ln++] = ch;
        }
    }
    _lclose(f);
    return -1;
}
/* C:\WINDOWS holds the 3.x recordings (chimes, chord, ding, tada, ringin, ringout); every XP file is in C:\XPSOUNDS
   as X<index>.WAV, converted to PCM that Sound Recorder opens (core kSoundFiles311) */
static const char *sound_file(int i)
{
    static char path[32];
    if (i >= 1000) return libPath[i - 1000];
    switch (i) {
    case 0: return "C:\\WINDOWS\\CHIMES.WAV";
    case 1: return "C:\\WINDOWS\\CHORD.WAV";
    case 2: return "C:\\WINDOWS\\DING.WAV";
    case 5: return "C:\\WINDOWS\\RINGIN.WAV";
    case 6: return "C:\\WINDOWS\\RINGOUT.WAV";
    case 8: return "C:\\WINDOWS\\TADA.WAV";
    }
    if (i < 0 || i >= NSND) return "C:\\WINDOWS\\DING.WAV";
    sprintf(path, "C:\\XPSOUNDS\\X%02d.WAV", i);
    return path;
}
/* rate and length (centiseconds, for the 30 s rule) from the file's own header, read once */
static long sndRate[NSND], sndCs[NSND];
static void sound_info(int i)
{
    OFSTRUCT of; HFILE f; BYTE h[44];
    if (i < 0 || i >= NSND || sndRate[i]) return;
    sndRate[i] = 22050; sndCs[i] = 100;
    f = OpenFile(sound_file(i), &of, OF_READ);
    if (f == HFILE_ERROR) return;
    if (_lread(f, h, 44) == 44) {
        long rate = *(long *)(h + 24), bps = *(long *)(h + 28), data = *(long *)(h + 40);
        if (rate > 0) sndRate[i] = rate;
        if (bps > 0) sndCs[i] = data * 100 / bps;
    }
    _lclose(f);
}
static int sound_cs(int i)   /* lengths in centiseconds, for the 30 s rule */
{
    if (i >= 1000) return (int)libCs[i - 1000];
    sound_info(i);
    return i >= 0 && i < NSND ? (int)sndCs[i] : 52;
}
static int sound_rate(int i)
{
    if (i >= 1000) return (int)libRate[i - 1000];
    sound_info(i);
    return i >= 0 && i < NSND ? (int)sndRate[i] : 22050;
}
static int sound_lookup(const char *s, int n)   /* the built-in table first, then the library (DNA.md 5.2) */
{
    int i = sound_index(s, n);
    return i >= 0 ? i : lib_index(s, n);
}

typedef struct { char op; int arg; int sound; } STEP;
typedef struct { int source; STEP st[NS]; int nst; int pool; int first, count; } LAYER;
LAYER lay[NL];
int nlay;

static int isname(char c) { return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_'; }
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

/* DNA v2 macros (DNA.md 5.3): only N (repeat count of a layer's last step) changes what Sound Recorder builds;
   the host does every other macro. Globals: mK=V sets macro K; mKLNmin,max maps it onto layer L's N (L 0 = all). */
static void macro_repeats(const char *g)
{
    int mv[5] = {0, 0, 0, 0, 0}, i, L;
    float nsum[NL]; int nmapped[NL];
    const char *p;
    for (i = 0; i < NL; i++) { nsum[i] = 0; nmapped[i] = 0; }
    if (*g != ';') return;
    for (p = g; *p; p++) if (p[0] == 'm' && p[1] >= '1' && p[1] <= '4' && p[2] == '=') { const char *q = p + 3; mv[p[1] - '0'] = clampi(getint(&q, 0), 0, 100); }
    for (p = g; *p; p++) {
        if (p[0] == 'm' && p[1] >= '1' && p[1] <= '4' && p[2] >= '0' && p[2] <= '8' && p[3] == 'N') {
            const char *q = p + 4; int lo = getint(&q, 0), hi = lo, K = p[1] - '0';
            if (*q == ',') { q++; hi = getint(&q, lo); }
            L = p[2] - '0';
            for (i = 0; i < nlay; i++) if (L == 0 || L - 1 == i) {
                float v = lo + (hi - lo) * mv[K] / 100.f;
                nsum[i] += nmapped[i] ? v - lo : v; nmapped[i]++;
            }
        }
    }
    for (i = 0; i < nlay; i++) if (nmapped[i] && lay[i].nst > 0) {   /* the last step, N times in all (0 = none) */
        int n = clampi((int)(nsum[i] + 0.5f), 0, 8), k;
        STEP last = lay[i].st[lay[i].nst - 1];
        lay[i].nst--;
        for (k = 0; k < n && lay[i].nst < NS; k++) lay[i].st[lay[i].nst++] = last;
    }
}
static void dna_parse(const char *t)
{
    const char *p = t;
    int i, k, left = NR, valid[NL], nv = 0, at = 0;
    nlay = 0; nlib = 0;
    for (i = 0; i < NL; i++) envN[i] = 0;
    while (*p && *p != ';') {
        LAYER L; const char *b = p;
        memset(&L, 0, sizeof L);
        while (isname(*p)) p++;
        L.source = sound_lookup(b, (int)(p - b));
        while (*p && *p != '/' && *p != ';') {
            char c = *p++;
            switch (c) {
            case '+': case '-': case '>': case '<': case 'E': case 'R': case '[': case ']': case 'C': case 'P': case 'X':
                if (L.nst < NS) { L.st[L.nst].op = c; L.nst++; }
                break;
            case '@':
                if (*p == 't') { int v; p++; v = clampi(getint(&p, 0), 0, 30000); if (L.nst < NS) { L.st[L.nst].op = 't'; L.st[L.nst].arg = v; L.nst++; } }
                else { int v = clampi(getint(&p, 0), 0, 99); if (L.nst < NS) { L.st[L.nst].op = '@'; L.st[L.nst].arg = v; L.nst++; } }
                break;
            case 'I': case 'M': {
                const char *q = p; int si;
                while (isname(*p)) p++;
                si = sound_lookup(q, (int)(p - q));
                if (si >= 0 && L.nst < NS) { L.st[L.nst].op = c; L.st[L.nst].sound = si; L.nst++; }
                break; }
            case '#': L.pool = clampi(getint(&p, 1), 1, NR); break;
            case 'T': case 'L': getint(&p, 0); break;
            case 'H': do { if (*p == ',') p++; getint(&p, 0); } while (*p == ','); break;
            case 'U': getint(&p, 1); if (*p == '~') { p++; getint(&p, 0); } break;
            case 'O': case 'Q': getint(&p, 0); break;                          /* v2: offset, pan (the host's) */
            case 'J': {                                                        /* v2: drawn envelope points */
                int amp = *p != 'p', n = 0;
                if (*p == 'a' || *p == 'p') p++;
                while (n < 8 && ((*p >= '0' && *p <= '9') || *p == '-')) {
                    int tt = getint(&p, 0), ll = 0;
                    if (*p == ',') { p++; ll = getint(&p, 0); }
                    if (amp && nlay < NL) { envT[nlay][n] = tt; envL[nlay][n] = ll; }
                    n++;
                    if (*p == '.') p++; else break;
                }
                while ((*p >= '0' && *p <= '9') || *p == ',' || *p == '.' || *p == '-') p++;
                if (amp && nlay < NL) envN[nlay] = n;
                break; }
            default: break;
            }
        }
        if (nlay < NL) lay[nlay++] = L;
        if (*p == '/') p++;
    }
    macro_repeats(p);
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
    /* Sound Recorder draws the wave display's centre line 18 rows down, from the control's native 35-row height,
       whatever its size: so it keeps that height, 4 rows above the strip; the strip shows rows 4..33 of it, and a
       1-row cover on the strip's last row (layout_strip) leaves 29 rows with the line exactly in the middle (row 14) */
    {SR_STATUS, 4, 7, 80, 16}, {SR_WAVE, 88, -4, 133, 35}, {SR_POS, 228, 8, 66, 14}, {SR_LEN, 298, 8, 66, 14},
    {SR_SCROLL, 370, 6, 270, 17}, {SR_REW, 648, 1, 52, 28}, {SR_FWD, 702, 1, 52, 28}, {SR_PLAY, 756, 1, 52, 28},
    {SR_STOP, 810, 1, 52, 28}, {SR_REC, 864, 1, 52, 28}};
#define NPART (sizeof strip / sizeof strip[0])
static int hidden[] = {300, 301, 304, 302, 305};


static void press(int r, int id)
{
    SendMessage(rw[r], WM_COMMAND, id, MAKELPARAM(GetDlgItem(rw[r], id), BN_CLICKED));
}
static void menu(int r, int id) { SendMessage(rw[r], WM_COMMAND, id, 0L); }
static int field_cs(int r, int id)   /* "0.52 sec." -> 52 */
{
    char t[32]; int s = 0, c = 0; char *p;
    GetDlgItemText(rw[r], id, t, sizeof t);
    s = atoi(t);
    p = t; while (*p && *p >= '0' && *p <= '9') p++;
    if (*p) { p++; c = atoi(p); }
    return s * 100 + c;
}
static int length_cs(int r) { return field_cs(r, SR_LEN); }
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
    {   /* the cover: a blank static of ours in the recorder's window, above its wave display, on the strip's last row */
        static HWND cover[NALL];
        HWND wv = GetDlgItem(rw[r], SR_WAVE);
        SetWindowLong(wv, GWL_STYLE, GetWindowLong(wv, GWL_STYLE) | WS_CLIPSIBLINGS);   /* never paints over it */
        if (!cover[r]) cover[r] = CreateWindow("STATIC", "", WS_CHILD | WS_VISIBLE, 88, STRIPH - 1, 133, 1, rw[r], (HMENU)-1, hInst, NULL);
        SetWindowPos(cover[r], HWND_TOP, 88, STRIPH - 1, 133, 1, SWP_NOACTIVATE);
    }
}

/* v3: the position slider to num/den of the length. Sound Recorder's scroll range is 0..10000 for every length and
   playback starts within half a frame of round(pos * N / 10000) (design/PRESET-ENGINE-2.md T1) */
static void seek_frac(int r, long num, long den)
{
    HWND sb = GetDlgItem(rw[r], SR_SCROLL); int lo, hi, pos;
    if (den <= 0) return;
    if (num < 0) num = 0;
    if (num > den) num = den;
    GetScrollRange(sb, SB_CTL, &lo, &hi);
    pos = lo + (int)(((long)(hi - lo) * num + den / 2) / den);
    SendMessage(rw[r], WM_HSCROLL, SB_THUMBPOSITION, MAKELPARAM(pos, sb));
    SendMessage(rw[r], WM_HSCROLL, SB_ENDSCROLL, MAKELPARAM(pos, sb));
}
static void seek_ms(int r, int ms, int len_cs)   /* v2: the position slider to ms (clamped to the length) */
{
    HWND sb = GetDlgItem(rw[r], SR_SCROLL); int lo, hi, pos;
    long len_ms = (long)len_cs * 10;
    GetScrollRange(sb, SB_CTL, &lo, &hi);
    if (len_ms <= 0) return;
    if (ms > len_ms) ms = (int)len_ms;
    pos = lo + (int)((long)(hi - lo) * ms / len_ms);
    SendMessage(rw[r], WM_HSCROLL, SB_THUMBPOSITION, MAKELPARAM(pos, sb));
    SendMessage(rw[r], WM_HSCROLL, SB_ENDSCROLL, MAKELPARAM(pos, sb));
}

static void pump(void)
{
    MSG m;
    while (PeekMessage(&m, 0, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessage(&m); }
}

/* what Sound Recorder is doing, in its own status field (it shows the menu command being carried out) */
static void op_label(int r, const char *t)
{
    HWND st = GetDlgItem(rw[r], SR_STATUS);
    if (st) { SetWindowText(st, t); UpdateWindow(st); }
}
static const char *op_name(STEP *s, char *buf)
{
    switch (s->op) {
    case '+': return "Louder"; case '-': return "Softer"; case '>': return "Faster"; case '<': return "Slower";
    case 'E': return "Echo"; case 'R': return "Reverse"; case '[': return "Delete <"; case ']': return "Delete >";
    case 'C': return "Copy"; case 'P': return "Paste"; case 'X': return "Paste mix";
    case 'I': sprintf(buf, "Insert %.9s", s->sound >= 1000 ? libName[s->sound - 1000] : names[s->sound]); return buf;
    case 'M': sprintf(buf, "Mix %.12s", s->sound >= 1000 ? libName[s->sound - 1000] : names[s->sound]); return buf;
    case '@': sprintf(buf, "Seek %d%%", s->arg); return buf;
    case 't': sprintf(buf, "Seek %d ms", s->arg); return buf;
    }
    return "";
}
int buildRow = -1;     /* the recorder being rebuilt (its number lights up) */
static void light_row(int r)
{
    RECT b; int old = buildRow;
    buildRow = r;
    if (!hMain) return;
    if (old >= 0) { SetRect(&b, 4, ROW0 + old * ROWH + 2, 36, ROW0 + old * ROWH + 30); InvalidateRect(hMain, &b, FALSE); }
    if (r >= 0) { SetRect(&b, 4, ROW0 + r * ROWH + 2, 36, ROW0 + r * ROWH + 30); InvalidateRect(hMain, &b, FALSE); }
    UpdateWindow(hMain);
}

/* one layer's steps, on one recorder; returns its final length in centiseconds */
static int run_steps(int r, LAYER *L)
{
    int i, len, clip, first_c = -1, needcopy = 0;
    char lbl[32];
    if (assembled) { sprintf(lbl, "Open %.10s", L->source >= 1000 ? libName[L->source - 1000] : names[L->source]); op_label(r, lbl); }
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
        if (assembled) op_label(r, op_name(s, lbl));
        switch (s->op) {
        case '+': menu(r, SR_VOLUP); break;
        case '-': menu(r, SR_VOLDN); break;
        case '>': menu(r, SR_FASTER); break;
        case '<': menu(r, SR_SLOWER); break;
        case 'E': menu(r, SR_ECHO); break;
        case 'R': menu(r, SR_REVERSE); break;
        case '[': menu(r, SR_DELBEFORE); break;
        case ']': if (field_cs(r, SR_POS) > 0) menu(r, SR_DELAFTER); break;   /* at the start it would delete the whole
                                                                                  sound: refused, like [ at the start (DNA.md 2.1) */
        case 'C': menu(r, SR_COPY); clip = len; break;
        case 'P': menu(r, SR_PASTE); break;
        case 'X': menu(r, SR_PASTEMIX); break;
        case 'I': HookPending(sound_file(s->sound)); menu(r, SR_INSERT); break;
        case 'M': HookPending(sound_file(s->sound)); menu(r, SR_MIX); break;
        case '@': seek_pct(r, s->arg); break;
        case 't': seek_ms(r, s->arg, len); break;
        }
        len = length_cs(r);
    }
    press(r, SR_REW);
    if (assembled) op_label(r, "Stopped");
    return len;
}

static void stop_rec(int r, DWORD id, int fade_ms);

static char lastSig[1400];
static int layer_len[NL];
static long layerFrames[NL];   /* each layer's length in frames, as told to the host (v3 windows are in these frames) */
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
static void dig_watch(void);
static void layer_replies(void)
{
    int i;
    for (i = 0; i < nlay; i++)
        if (lay[i].count) { layerFrames[i] = (long)layer_len[i] * sound_rate(lay[i].source) / 100; say("layer %d %d %d %d %ld", i, lay[i].first, lay[i].count, sound_rate(lay[i].source), layerFrames[i]); }
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
    /* idle recorders first; a recorder still sounding a note goes last, and gets up to 1.5 s to finish it (notes are
       served meanwhile), because loading the new sound stops whatever it plays */
    {
        int pass, done[NR];
        for (r = 0; r < NR; r++) done[r] = 0;
        for (pass = 0; pass < 2; pass++)
            for (i = 0; i < nlay; i++) {
                LAYER *L = &lay[i];
                for (r = L->first; r < L->first + L->count; r++) {
                    int a = tb * NR + r;
                    if (done[r] || (pass == 0 && rplay[a])) continue;
                    if (pass == 1) { DWORD tw = timeGetTime(); while (rplay[a] && timeGetTime() - tw < 1500) { if (!poll_host()) bs_idle(); pump(); } }
                    stop_rec(a, 0, 1500);        /* an old note on it rings out (the card fades it over 1.5 s) */
                    rlayer[a] = i;
                    light_row(r);
                    layer_len[i] = run_steps(a, L);
                    recRate[a] = sound_rate(L->source);
                    layout_strip(a);
                    done[r] = 1;
                    poll_host();
                    pump();
                }
            }
    }
    HookActive(FALSE);
    light_row(-1);
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
static BOOL regated[NALL];   /* a regate (v3 continue) keeps this recorder's ghost sounding after Sound Recorder stopped */
static void play_rec(int r, DWORD id, DWORD hz, WORD vol, int pan, int layer, long from)
{
    if (r < 0 || r >= NR) return;
    r = AR(r);
    if (!rw[r]) return;
    if (hostRate[r] && recRate[r] && hostRate[r] != recRate[r]) hz = hz * recRate[r] / hostRate[r];   /* rebuilt mid-change */
    {
    DWORD t0 = timeGetTime(), t1, t2, t3;
    if (rplay[r] || is_playing(r)) { bs_armstop(rt[r], id, 5); press(r, SR_STOP); }
    if (regated[r]) { bs_stoptask(rt[r], id, 5); regated[r] = FALSE; }
    t1 = timeGetTime();
    {   /* v3 window: start at frame `from` of the layer's buffer (the host ends it with a stamped cut) */
        int L = layer >= 0 && layer < NL ? layer : rlayer[r];
        if (from > 0 && L >= 0 && L < NL && layerFrames[L] > 0) seek_frac(r, from, layerFrames[L]);
        else press(r, SR_REW);
    }
    t2 = timeGetTime();
    bs_arm2(rt[r], id, hz, vol, pan, layer < 0 ? rlayer[r] : layer);
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
    if (regated[r]) { bs_stoptask(rt[r], id, (WORD)fade_ms); regated[r] = FALSE; }
    rplay[r] = FALSE;
}
/* v3: the recorder's sounding voice (and its release) changes to hz at the event's sample, gliding over glide_ms */
static void rate_rec(int r, DWORD id, DWORD hz, int glide_ms, int regate)
{
    if (r < 0 || r >= NALL || !rw[r] || !hz) return;
    if (hostRate[r] && recRate[r] && hostRate[r] != recRate[r]) hz = hz * recRate[r] / hostRate[r];
    bs_rate(rt[r], id, hz, (WORD)(glide_ms < 0 ? 0 : glide_ms), (WORD)(regate != 0));
    if (regate) regated[r] = TRUE;   /* the next stop or play also ends the ghost it kept */
}
/* Recording (RECORDING.md 1.3, 4.3): the card has one ADC, so while a recorder records every other Record button
   is grey; the host hears `rec start <rec>` / `rec stop <rec> <ms>` (it keeps its notes off that recorder) */
static int recording = -1; static DWORD recT0;
static void watch_rec(void)
{
    int r, now = -1; char t[24];
    for (r = 0; r < NR && now < 0; r++) { GetDlgItemText(rw[AR(r)], SR_STATUS, t, sizeof t); if (t[0] == 'R' && t[2] == 'c') now = r; }
    if (now != recording) {
        if (recording >= 0) say("rec stop %d %ld", recording, (long)(timeGetTime() - recT0));
        if (now >= 0) { say("rec start %d", now); recT0 = timeGetTime(); }
        recording = now;
        if (now < 0) for (r = 0; r < NR; r++) EnableWindow(GetDlgItem(rw[AR(r)], SR_REC), TRUE);
    }
    if (recording >= 0)   /* Sound Recorder enables its own button again on its state changes: keep the others grey */
        for (r = 0; r < NR; r++) if (r != recording && IsWindowEnabled(GetDlgItem(rw[AR(r)], SR_REC))) EnableWindow(GetDlgItem(rw[AR(r)], SR_REC), FALSE);
}
static void watch_ends(void)
{
    static DWORD last; int r;
    if (timeGetTime() - last < 25) return;
    last = timeGetTime();
    watch_rec();
    dig_watch();
    for (r = 0; r < NR; r++) if (rplay[AR(r)] && !is_playing(AR(r))) { rplay[AR(r)] = FALSE; say("end %d", r); }
}

/* ================================================================ the clock: the host's time after a resume */
static void set_time(int Y, int M, int D, int h, int m, int s)
{
    union REGS rg;
    rg.h.ah = 0x2B; rg.x.cx = Y; rg.h.dh = (unsigned char)M; rg.h.dl = (unsigned char)D; intdos(&rg, &rg);
    rg.h.ah = 0x2D; rg.h.ch = (unsigned char)h; rg.h.cl = (unsigned char)m; rg.h.dh = (unsigned char)s; rg.h.dl = 0; intdos(&rg, &rg);
}


static int mkGroup = -1, grpN[7];
static BOOL listsWanted;
static HWND grpWin[7][72];
static void show_group(int g)
{
    int i;
    for (i = 0; i < grpN[g]; i++) ShowWindow(grpWin[g][i], SW_SHOWNA);
    UpdateWindow(hMain);
}

/* ================================================================ the keyboard strip (DNA.md 5.4) */
/* Five octaves of keys along the bottom, a pitch bend and a mod wheel, Hold and Keys: Windows 3.11's own controls.
   White keys are push buttons (pressed = the button's own pushed-in look), black keys are black-rectangle statics
   (pressed = grey). The mouse and the computer keyboard play through the host (`key`), and the host shows what it
   plays (`show`), so the keys go down for MIDI notes too. */
#define KLO 36          /* C2 */
#define KHI 96          /* C7 */
#define KX0 138
#define KWW 24          /* white key width */
#define KWH 58          /* white key height */
#define KBW 14
#define KBH 35
#define ID_HOLD 1151
#define ID_KEYS 1152
static HWND hKey[128], hBend, hMod, hHold, hKeysChk, hOctLbl;
static BYTE hostDown[128], kbdDown[128], latched[128];
static int mouseNote = -1, holdOn, keysOn, octBase = 60, modVal, bendVal;
static WNDPROC oldBtnProc, oldStaticProc;
static int is_black(int n) { int k = n % 12; return k == 1 || k == 3 || k == 6 || k == 8 || k == 10; }
static int white_index(int n) { static const int w[12] = {0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6}; return (n / 12 - KLO / 12) * 7 + w[n % 12]; }
static void key_rect(int n, RECT *r)
{
    if (is_black(n)) { int x = KX0 + (white_index(n) + 1) * KWW - KBW / 2; SetRect(r, x, KBY, x + KBW, KBY + KBH); }
    else { int x = KX0 + white_index(n) * KWW; SetRect(r, x, KBY, x + KWW + 1, KBY + KWH); }
}
static void key_visual(int n)
{
    int down;
    if (n < KLO || n > KHI || !hKey[n]) return;
    down = hostDown[n] || kbdDown[n] || latched[n] || mouseNote == n;
    if (is_black(n)) {
        LONG st = GetWindowLong(hKey[n], GWL_STYLE), want = (st & ~0x1FL) | (down ? SS_GRAYRECT : SS_BLACKRECT);
        if (st != want) { SetWindowLong(hKey[n], GWL_STYLE, want); InvalidateRect(hKey[n], NULL, TRUE); }
    } else {   /* pushed in, with a dot on it */
        SendMessage(hKey[n], BM_SETSTATE, down ? TRUE : FALSE, 0L);
        SetWindowText(hKey[n], down ? "\x95" : "");
    }
}
static void note_on(int n, int vel) { if (n < 0 || n > 127) return; latched[n] = 0; say("key %d %d", n, vel); }
static void note_off(int n)
{
    if (n < 0 || n > 127) return;
    if (holdOn) latched[n] = 1;          /* Hold: the note stays down until Hold is let go */
    else say("key %d 0", n);
}
static int note_at(int x, int y, int *vel)
{
    int n;
    if (y < KBY || y >= KBY + KWH || x < KX0) return -1;
    *vel = 40 + 87 * (y - KBY) / KWH;   /* nearer the front of the key, louder */
    if (y < KBY + KBH)
        for (n = KLO; n <= KHI; n++) if (is_black(n)) { RECT r; key_rect(n, &r); if (x >= r.left && x < r.right) return n; }
    for (n = KLO; n <= KHI; n++) if (!is_black(n)) { RECT r; key_rect(n, &r); if (x >= r.left && x < r.right - 1) return n; }
    return -1;
}
static void kb_mouse(HWND h, LPARAM l, int up)
{
    POINT p; int n, vel = 100, old = mouseNote;
    p.x = (short)LOWORD(l); p.y = (short)HIWORD(l);
    ClientToScreen(h, &p); ScreenToClient(hMain, &p);
    n = up ? -1 : note_at(p.x, p.y, &vel);
    if (n == old) return;
    mouseNote = n;
    if (old >= 0) { if (!kbdDown[old]) note_off(old); key_visual(old); }
    if (n >= 0) { note_on(n, vel); key_visual(n); }
}
long FAR PASCAL __export KeyProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    switch (m) {
    case WM_NCHITTEST: return HTCLIENT;
    case WM_LBUTTONDOWN: case WM_LBUTTONDBLCLK: SetCapture(h); kb_mouse(h, l, 0); return 0;
    case WM_MOUSEMOVE: if (GetCapture() == h) kb_mouse(h, l, 0); return 0;
    case WM_LBUTTONUP: if (GetCapture() == h) { ReleaseCapture(); kb_mouse(h, l, 1); } return 0;
    }
    return CallWindowProc((FARPROC)((GetWindowWord(h, GWW_ID) & 0x200) ? oldStaticProc : oldBtnProc), h, m, w, l);
}
static void hold_set(int on)
{
    int n;
    holdOn = on;
    if (on) return;
    for (n = 0; n < 128; n++) if (latched[n]) { latched[n] = 0; if (!kbdDown[n] && mouseNote != n) say("key %d 0", n); key_visual(n); }
}
static void oct_label(void)
{
    static const char *nm[12] = {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"};
    char t[32];
    sprintf(t, "z x: %s%d", nm[octBase % 12], octBase / 12 - 1);
    if (hOctLbl) SetWindowText(hOctLbl, t);
}
static int computer_key(WPARAM vk, LPARAM l, int down)   /* a w s e d f t g y h u j k: C..C; z x: octave */
{
    static const char map[] = "AWSEDFTGYHUJK";
    const char *p;
    if (!keysOn) return 0;
    if (down && (l & 0x40000000L)) return 1;            /* auto-repeat */
    if (vk == 'Z' || vk == 'X') { if (down) { octBase += vk == 'Z' ? -12 : 12; if (octBase < 24) octBase = 24; if (octBase > 96) octBase = 96; oct_label(); } return 1; }
    p = vk < 128 ? strchr(map, (int)vk) : NULL;
    if (!p || !*p) return 0;
    {
        int n = octBase + (int)(p - map);
        if (n > 127) return 1;
        if (down && !kbdDown[n]) { kbdDown[n] = 1; note_on(n, 100); }
        else if (!down && kbdDown[n]) { kbdDown[n] = 0; if (mouseNote != n) note_off(n); }
        key_visual(n);
    }
    return 1;
}
static void kb_scroll(HWND sb, int code, int pos)
{
    int lo, hi, v;
    if (sb != hBend && sb != hMod) return;
    GetScrollRange(sb, SB_CTL, &lo, &hi);
    v = GetScrollPos(sb, SB_CTL);
    switch (code) {
    case SB_LINEUP: v -= sb == hBend ? 512 : 4; break; case SB_LINEDOWN: v += sb == hBend ? 512 : 4; break;
    case SB_PAGEUP: v -= sb == hBend ? 2048 : 16; break; case SB_PAGEDOWN: v += sb == hBend ? 2048 : 16; break;
    case SB_THUMBTRACK: case SB_THUMBPOSITION: v = pos; break;
    case SB_ENDSCROLL:
        if (sb == hBend) { v = 0; break; }                /* the bend springs back */
        return;
    default: return;
    }
    if (v < lo) v = lo; if (v > hi) v = hi;
    SetScrollPos(sb, SB_CTL, v, TRUE);
    if (sb == hBend) { if (-v != bendVal) { bendVal = -v; say("bend %d", bendVal); } }   /* up = higher */
    else if (127 - v != modVal) { modVal = 127 - v; say("cc 1 %d", modVal); }
}
static void kb_show(const char *what, const char *rest)    /* the host: incoming MIDI, for the eye only */
{
    if (!strcmp(what, "show")) {
        int n = 0, v = 0;
        sscanf(rest, "%d %d", &n, &v);
        if (n >= 0 && n < 128) { hostDown[n] = v > 0; key_visual(n); }
    } else if (!strcmp(what, "cc")) {
        int c = 0, v = 0;
        sscanf(rest, "%d %d", &c, &v);
        if (c == 1 && hMod && GetCapture() != hMod) { modVal = v; SetScrollPos(hMod, SB_CTL, 127 - v, TRUE); }
    } else if (!strcmp(what, "bend")) {
        bendVal = atoi(rest);
        if (hBend && GetCapture() != hBend) SetScrollPos(hBend, SB_CTL, -bendVal, TRUE);
    }
}
static HWND mk(const char *cls, const char *text, DWORD st, int x, int y, int w, int h, int id);
static void keyboard_create(void)   /* at boot, hidden */
{
    int n, g = mkGroup;
    hBend = mk("SCROLLBAR", "", WS_VISIBLE | SBS_VERT, 4, KBY, 17, KWH, 1153);     /* the two wheels, full height */
    SetScrollRange(hBend, SB_CTL, -8191, 8192, FALSE); SetScrollPos(hBend, SB_CTL, 0, TRUE);
    hMod = mk("SCROLLBAR", "", WS_VISIBLE | SBS_VERT, 24, KBY, 17, KWH, 1154);
    SetScrollRange(hMod, SB_CTL, 0, 127, FALSE); SetScrollPos(hMod, SB_CTL, 127, TRUE);
    mk("STATIC", "Bend Mod", WS_VISIBLE, 46, KBY, 88, 14, -1);
    hHold = mk("BUTTON", "Hold", WS_VISIBLE | BS_AUTOCHECKBOX, 46, KBY + 14, 80, 15, ID_HOLD);
    hKeysChk = mk("BUTTON", "Keys", WS_VISIBLE | BS_AUTOCHECKBOX, 46, KBY + 29, 80, 15, ID_KEYS);
    hOctLbl = mk("STATIC", "", WS_VISIBLE, 46, KBY + 44, 88, 14, -1);
    oct_label();
    mkGroup = -1;                      /* the keys are shown by keyboard_show's sweep */
    for (n = KLO; n <= KHI; n++) {     /* whites, then blacks on top of them */
        RECT r; int b = is_black(n);
        key_rect(n, &r);
        if (b) continue;
        hKey[n] = mk("BUTTON", "", WS_CLIPSIBLINGS | BS_PUSHBUTTON, r.left, r.top, r.right - r.left, r.bottom - r.top, 0x100 | n);
        {   /* the dot of a pressed key: big, low on the key (the text sits in the middle of the button) */
            static HFONT dot;
            if (!dot) dot = CreateFont(40, 0, 0, 0, FW_BOLD, 0, 0, 0, ANSI_CHARSET, 0, 0, 0, VARIABLE_PITCH | FF_SWISS, "Arial");
            SendMessage(hKey[n], WM_SETFONT, (WPARAM)dot, 0L);
        }
        if (!oldBtnProc) oldBtnProc = (WNDPROC)GetWindowLong(hKey[n], GWL_WNDPROC);
        SetWindowLong(hKey[n], GWL_WNDPROC, (LONG)MakeProcInstance((FARPROC)KeyProc, hInst));
    }
    for (n = KLO; n <= KHI; n++) if (is_black(n)) {
        RECT r; key_rect(n, &r);
        hKey[n] = mk("STATIC", "", WS_CLIPSIBLINGS | SS_BLACKRECT, r.left, r.top, r.right - r.left, r.bottom - r.top, 0x300 | n);
        if (!oldStaticProc) oldStaticProc = (WNDPROC)GetWindowLong(hKey[n], GWL_WNDPROC);
        SetWindowLong(hKey[n], GWL_WNDPROC, (LONG)MakeProcInstance((FARPROC)KeyProc, hInst));
        SetWindowPos(hKey[n], HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    }
    mkGroup = g;
}
static void keyboard_show(void)     /* part of the assembly: wheels and switches, then the keys left to right */
{
    int n, failed = 0, late = 0;
    show_group(6);
    for (n = KLO; n <= KHI; n += 12) {   /* an octave at a time, left to right: one batch each (whites, then blacks on top) */
        int k, pass;
        for (pass = 0; pass < 2; pass++) {   /* the whites painted before the blacks arrive on them */
            HDWP dw = BeginDeferWindowPos(7);
            for (k = n; k < n + 12 && k <= KHI; k++)
                if (is_black(k) == pass) dw = DeferWindowPos(dw, hKey[k], pass ? HWND_TOP : NULL, 0, 0, 0, 0,
                                                             SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW | (pass ? 0 : SWP_NOZORDER));
            if (!dw || !EndDeferWindowPos(dw)) { failed++;   /* (a batch can fail): one by one instead */
                for (k = n; k < n + 12 && k <= KHI; k++) if (is_black(k) == pass) ShowWindow(hKey[k], SW_SHOWNA);
            }
            for (k = n; k < n + 12 && k <= KHI; k++) if (is_black(k) == pass) UpdateWindow(hKey[k]);
        }
        poll_host();
    }
    for (n = KLO; n <= KHI; n++) if (!IsWindowVisible(hKey[n])) { ShowWindow(hKey[n], SW_SHOWNA); late++; }
    if (failed || late) logf_("keyboard: %d batches failed, %d keys shown late", failed, late);
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
#define ID_PRESET 1145     /* the preset browser (L:\\PRESETS.TSV) */
#define ID_LIBRARY 1146    /* every sound: the four of C:\\WINDOWS and the library disc (L:\\LIBRARY.TSV) */
#define ID_ENVPREV 1147    /* the drawn envelope's points: < > + - */
#define ID_ENVNEXT 1148
#define ID_ENVADD 1149
#define ID_ENVDEL 1150
#define ID_FILTER 1157     /* + 0 All, 1 W3.11, 2 XP: which presets the browser lists */
#define ID_PRESETPREV 1155
#define ID_PRESETNEXT 1156
static const char *panelSounds[4] = {"chimes", "ding", "ringin", "ringout"};
static const char *stepNames[10] = {"Louder", "Softer", "Faster", "Slower", "Echo", "Reverse", "Del <", "Del >", "Copy", "Paste"};
static const char stepOps[10] = {'+', '-', '>', '<', 'E', 'R', '[', ']', 'C', 'P'};
static const char *harmNames[6] = {"Single", "Octave", "Fifth", "Major", "Minor", "Octaves"};
static const char *harmGenes[6] = {"H0", "H0,12", "H0,7", "H0,4,7", "H0,3,7", "H-12,0,12"};
typedef struct { const char *label; char letter; int lo, hi; BOOL global; } SLIDER;
static SLIDER sliders[] = {
    {"Voices", '#', 1, 16, FALSE}, {"Transpose", 'T', -24, 24, FALSE}, {"Unison", 'U', 1, 8, FALSE}, {"Level", 'L', 0, 400, FALSE},
    {"Attack", 'A', 0, 2000, TRUE}, {"Decay", 'D', 0, 2000, TRUE}, {"Sustain", 'S', 0, 100, TRUE}, {"Release", 'R', 0, 3000, TRUE},
    /* v2 (DNA.md 5): the layer's pan and start offset; the selected envelope point's time and level; the four macros */
    {"Pan", 'Q', -100, 100, FALSE}, {"Offset", 'O', 0, 4000, FALSE}, {"ms", 'e', 0, 4000, FALSE}, {"%", 'l', 0, 100, FALSE},
    {"Macro 1", '1', 0, 100, TRUE}, {"Macro 2", '2', 0, 100, TRUE}, {"Macro 3", '3', 0, 100, TRUE}, {"Macro 4", '4', 0, 100, TRUE}};
#define SL_PAN 8
#define SL_ETIME 10
#define SL_ELEVEL 11
#define SL_MACRO 12
#define NSL (sizeof sliders / sizeof sliders[0])
static HWND hSb[NSL], hVal[NSL], hLayerLbl, hHarm, hPreset, hLibrary, hEnvLbl, hFilter[3];
static int presetFilter;   /* 0 All, 1 W3.11 (no XP file), 2 XP (uses one) */
static int harmIdx, envPt;

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
    case '@': if (*q == 't') q++; getint(&q, 0); *len = (int)(q - p); return 's';
    case 'I': case 'M': while (isname(*q)) q++; *len = (int)(q - p); return 's';
    case '#': case 'T': case 'L': getint(&q, 0); *len = (int)(q - p); return 'g';
    case 'H': do { if (*q == ',') q++; getint(&q, 0); } while (*q == ','); *len = (int)(q - p); return 'g';
    case 'U': getint(&q, 1); if (*q == '~') { q++; getint(&q, 0); } *len = (int)(q - p); return 'g';
    case 'F': *len = 1; return 'g';
    case 'O': case 'Q': getint(&q, 0); *len = (int)(q - p); return 'g';
    case 'J':                     /* v2 drawn envelope: Ja (letter 'J') and Jp (letter 'j') are separate genes */
        if (*q == 'p') *letter = 'j';
        if (*q == 'a' || *q == 'p') q++;
        while ((*q >= '0' && *q <= '9') || *q == ',' || *q == '.' || *q == '-') q++;
        *len = (int)(q - p); return 'g';
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
/* v2 macros: mK=V among the globals */
static int macro_value(int k)
{
    int b, e, p, v = 0;
    span(-1, &b, &e);
    for (p = b; p + 2 < e; p++) if (dnaText[p] == 'm' && dnaText[p + 1] == '0' + k && dnaText[p + 2] == '=') { const char *q = dnaText + p + 3; v = getint(&q, 0); }
    return v;
}
static void macro_set(int k, int v)
{
    int b, e, p; char tok[16];
    if (!strchr(dnaText, ';')) strcat(dnaText, ";");
    span(-1, &b, &e);
    for (p = b; p + 2 < e;) {
        if (dnaText[p] == 'm' && dnaText[p + 1] == '0' + k && dnaText[p + 2] == '=') {
            const char *q = dnaText + p + 3; int len;
            getint(&q, 0); len = (int)(q - (dnaText + p));
            splice(p, p + len, ""); e -= len; continue;
        }
        p++;
    }
    sprintf(tok, "m%d=%d", k, v);
    span(-1, &b, &e); splice(e, e, tok);
}
/* v2 drawn envelope (Ja) of layer li as written in the DNA: n points of (ms, level %) */
static int env_get(int li, int *t, int *l)
{
    int b, e, p, len, n = 0; char L;
    span(li, &b, &e);
    if (b < 0) return 0;
    p = b; while (isname(dnaText[p])) p++;
    while (p < e) {
        int k = token(dnaText + p, &len, &L);
        if (!k) break;
        if (k == 'g' && L == 'J') {
            const char *q = dnaText + p + 2;
            n = 0;
            while (n < 8 && ((*q >= '0' && *q <= '9') || *q == '-')) {
                t[n] = getint(&q, 0); l[n] = 0;
                if (*q == ',') { q++; l[n] = getint(&q, 0); }
                n++;
                if (*q == '.') q++; else break;
            }
        }
        p += len;
    }
    return n;
}
static void env_put(int li, int n, const int *t, const int *l)
{
    char tok[120], *o = tok; int k;
    if (n > 0) {
        o += sprintf(o, "Ja");
        for (k = 0; k < n; k++) o += sprintf(o, "%s%d,%d", k ? "." : "", t[k], l[k]);
    }
    *o = 0;
    layer_edit(li, 0, 'J', tok);
}
/* a layer with no drawn envelope gets one shaped like A/D/S, so there is something to move */
static int env_seed(int *t, int *l)
{
    int a = envA > 10 ? envA : 10, d = envD > 200 ? envD : 200;
    t[0] = 0; l[0] = 0; t[1] = a; l[1] = 100; t[2] = a + d; l[2] = envS; t[3] = a + d + 600; l[3] = envS;
    return 4;
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
    {
        int et[8], el[8], en = env_get(selLayer, et, el);
        if (envPt >= en) envPt = en ? en - 1 : 0;
        for (i = 0; i < (int)NSL; i++) {
            SLIDER *S = &sliders[i];
            int dflt = S->letter == '#' ? (lay[selLayer].count ? lay[selLayer].count : 1) : S->letter == 'U' ? 1 : S->letter == 'L' ? 100 :
                       S->letter == 'S' ? 100 : S->letter == 'R' ? 120 : 0;
            int v;
            if (!hSb[i]) continue;
            if (S->letter >= '1' && S->letter <= '4') v = macro_value(S->letter - '0');
            else if (S->letter == 'e') v = en ? et[envPt] : 0;
            else if (S->letter == 'l') v = en ? el[envPt] : 0;
            else v = S->global ? global_value(S->letter, dflt) : gene_value(selLayer, S->letter, dflt);
            SetScrollPos(hSb[i], SB_CTL, v, TRUE);
            sprintf(t, "%d", v);
            if (hVal[i]) SetWindowText(hVal[i], t);
        }
        if (hEnvLbl) {
            if (en) sprintf(t, "%d/%d %dms %d%%", envPt + 1, en, et[envPt], el[envPt]); else strcpy(t, "A/D/S");
            SetWindowText(hEnvLbl, t);
        }
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
        {
            int i, t[8], l[8];
            for (i = 0; i < nlay && i < NL; i++) {
                int n = env_get(i, t, l), k;
                envN[i] = n;
                for (k = 0; k < n; k++) { envT[i][k] = t[k]; envL[i][k] = l[k]; }
                bs_lenv(i, 0, n, t, l, 0);
            }
        }
        show_envelope();
    }
    panel_refresh();
}
static void read_lines(const char *path, void (*fn)(char *line, long off))   /* a text file on a disc, line by line */
{
    OFSTRUCT of; HFILE f;
    static char buf[512], ln[1100]; static int busy; int n, i, m = 0; long off = 0, start = 0;
    if (busy) return;                    /* (it pumps messages: a click must not start a second read) */
    f = OpenFile(path, &of, OF_READ);
    if (f == HFILE_ERROR) return;
    busy = 1;
    while ((n = _lread(f, buf, sizeof buf)) > 0) {
        poll_host();                     /* notes are served, and windows painted, while a long list is read */
        pump();
        for (i = 0; i < n; i++, off++) {
            char c = buf[i];
            if (c == '\n') { ln[m] = 0; if (m && ln[m - 1] == '\r') ln[m - 1] = 0; fn(ln, start); m = 0; start = off + 1; }
            else if (m < (int)sizeof ln - 1) ln[m++] = c;
        }
    }
    if (m) { ln[m] = 0; fn(ln, start); }
    _lclose(f);
    busy = 0;
}
/* does a DNA use an XP file? (its sources and its I/M sounds; DNA.md 2.4: everything but the six 3.x files) */
static int uses_xp(const char *d)
{
    const char *p = d; int start = 1;
    while (*p && *p != ';') {
        if (start || ((*p == 'I' || *p == 'M') && isname(p[1]))) {
            const char *q = start ? p : p + 1, *e = q; int i;
            while (isname(*e)) e++;
            i = sound_index(q, (int)(e - q));
            if (i == 3 || i == 4 || i == 7 || i >= 9) return 1;
            p = e; start = 0; continue;
        }
        if (*p == '/') start = 1;
        p++;
    }
    return 0;
}
static void add_preset(char *ln, long off)    /* category TAB name TAB DNA -> "Category: Name" (its DNA is re-read when picked) */
{
    char *a = strchr(ln, '\t'), *b, t[80]; int i;
    if (!a || ln[0] == '#') return;
    *a = 0; b = strchr(a + 1, '\t'); if (!b) return; *b = 0;
    if (presetFilter && uses_xp(b + 1) != (presetFilter == 2)) return;
    sprintf(t, "%.30s: %.44s", ln, a + 1);
    i = (int)SendMessage(hPreset, CB_ADDSTRING, 0, (LPARAM)(LPSTR)t);
    if (i >= 0) SendMessage(hPreset, CB_SETITEMDATA, i, off);
}
static long wantOff; static char pickedDna[1100];
static void pick_preset(char *ln, long off)
{
    char *a, *b;
    if (off != wantOff) return;
    a = strchr(ln, '\t'); b = a ? strchr(a + 1, '\t') : NULL;
    if (b) lstrcpyn(pickedDna, b + 1, sizeof pickedDna);
}
static void add_sound(char *ln, long off)     /* name TAB category ... -> "category: name" */
{
    char *a = strchr(ln, '\t'), *b, t[80];
    (void)off;
    if (!a) return;
    *a = 0; b = strchr(a + 1, '\t'); if (b) *b = 0;
    sprintf(t, "%.20s: %.40s", a + 1, ln);
    SendMessage(hLibrary, CB_ADDSTRING, 0, (LPARAM)(LPSTR)t);
}
static void preset_list(void)
{
    int i;
    SendMessage(hPreset, CB_RESETCONTENT, 0, 0L);
    read_lines("L:\\PRESETS.TSV", add_preset);
    for (i = 0; i < 3; i++) if (hFilter[i]) SendMessage(hFilter[i], BM_SETSTATE, i == presetFilter, 0L);   /* pushed in */
}
static void panel_lists(void)
{
    int i; char t[48];
    preset_list();
    SendMessage(hLibrary, CB_RESETCONTENT, 0, 0L);
    read_lines("L:\\LIBRARY.TSV", add_sound);
    {   /* C:\\WINDOWS: WfW 3.11's four and 3.1's CHORD and TADA */
        static const char *w[6] = {"chimes", "chord", "ding", "ringin", "ringout", "tada"};
        for (i = 0; i < 6; i++) { sprintf(t, "windows: %s", w[i]); SendMessage(hLibrary, CB_ADDSTRING, 0, (LPARAM)(LPSTR)t); }
    }
}
static void combo_pick(int id)
{
    HWND cb = id == ID_PRESET ? hPreset : hLibrary;
    int i = (int)SendMessage(cb, CB_GETCURSEL, 0, 0L), b, e;
    char t[80], *nm;
    if (i < 0 || building) return;
    if (id == ID_PRESET) {
        wantOff = SendMessage(cb, CB_GETITEMDATA, i, 0L); pickedDna[0] = 0;
        read_lines("L:\\PRESETS.TSV", pick_preset);
        if (pickedDna[0]) { lstrcpyn(dnaText, pickedDna, sizeof dnaText); selLayer = 0; envPt = 0; edited(TRUE); }
        return;
    }
    SendMessage(cb, CB_GETLBTEXT, i, (LPARAM)(LPSTR)t);
    nm = strstr(t, ": "); if (!nm) return; nm += 2;
    span(selLayer, &b, &e);
    if (b >= 0) { int p = b; while (isname(dnaText[p])) p++; splice(b, p, nm); edited(TRUE); }
}
static void panel_command(int id, int code)
{
    int b, e;
    if (id == ID_HOLD || id == ID_KEYS) {
        int on = (int)SendMessage(id == ID_HOLD ? hHold : hKeysChk, BM_GETCHECK, 0, 0L);
        if (id == ID_HOLD) hold_set(on);
        else { keysOn = on; if (on) SetFocus(hMain); }
        return;
    }
    if (id == ID_PRESET || id == ID_LIBRARY) {   /* a pick: when the list closes, or with the keys while it is shut */
        HWND cb = id == ID_PRESET ? hPreset : hLibrary;
        if (code == CBN_CLOSEUP || (code == CBN_SELCHANGE && !SendMessage(cb, CB_GETDROPPEDSTATE, 0, 0L))) {
            static int last[2] = {-2, -2};
            int i = (int)SendMessage(cb, CB_GETCURSEL, 0, 0L);
            if (i != last[id - ID_PRESET] || code == CBN_SELCHANGE) { last[id - ID_PRESET] = i; combo_pick(id); }
        }
        return;
    }
    if (id >= ID_FILTER && id < ID_FILTER + 3) { presetFilter = id - ID_FILTER; preset_list(); return; }
    if (building) return;
    if (id == ID_PRESETPREV || id == ID_PRESETNEXT) {
        int n = (int)SendMessage(hPreset, CB_GETCOUNT, 0, 0L), i = (int)SendMessage(hPreset, CB_GETCURSEL, 0, 0L);
        if (n <= 0) return;
        i = i < 0 ? 0 : (i + (id == ID_PRESETNEXT ? 1 : n - 1)) % n;
        SendMessage(hPreset, CB_SETCURSEL, i, 0L);
        combo_pick(ID_PRESET);
        return;
    }
    if (id >= ID_ENVPREV && id <= ID_ENVDEL) {
        int t[8], l[8], n = env_get(selLayer, t, l), k;
        if (id == ID_ENVPREV) { if (n) envPt = (envPt + n - 1) % n; panel_refresh(); return; }
        if (id == ID_ENVNEXT) { if (n) envPt = (envPt + 1) % n; panel_refresh(); return; }
        if (id == ID_ENVADD) {
            if (!n) { n = env_seed(t, l); envPt = 1; }
            else if (n < 8) {
                for (k = n; k > envPt + 1; k--) { t[k] = t[k - 1]; l[k] = l[k - 1]; }
                t[envPt + 1] = envPt + 2 <= n ? (t[envPt] + t[envPt + 2]) / 2 : t[envPt] + 200;
                l[envPt + 1] = l[envPt];
                n++; envPt++;
            }
        } else {   /* delete the point (the last one deleted: back to A/D/S) */
            if (!n) return;
            for (k = envPt; k < n - 1; k++) { t[k] = t[k + 1]; l[k] = l[k + 1]; }
            n--; if (envPt >= n && envPt) envPt--;
        }
        env_put(selLayer, n, t, l);
        edited(FALSE);
        return;
    }
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
        envPt = 0;
        InvalidateRect(hMain, NULL, FALSE);
        panel_refresh();
        show_envelope();
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
    if (hVal[i]) { char t[16]; sprintf(t, "%d", v); SetWindowText(hVal[i], t); }
    if (code == SB_THUMBTRACK) return;                  /* apply when the thumb is let go */
    if (sliders[i].letter >= '1' && sliders[i].letter <= '4') {   /* a macro: N mappings make Sound Recorder rebuild */
        macro_set(sliders[i].letter - '0', v);
        edited(TRUE);
        return;
    }
    if (sliders[i].letter == 'e' || sliders[i].letter == 'l') {   /* the selected point of the drawn envelope */
        int t[8], l[8], n = env_get(selLayer, t, l);
        if (!n) { n = env_seed(t, l); envPt = 1; }
        if (sliders[i].letter == 'l') l[envPt] = v;
        else {   /* points stay in time order */
            int lo2 = envPt ? t[envPt - 1] : 0, hi2 = envPt + 1 < n ? t[envPt + 1] : 30000;
            t[envPt] = v < lo2 ? lo2 : v > hi2 ? hi2 : v;
        }
        env_put(selLayer, n, t, l);
        edited(FALSE);
        return;
    }
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
/* (Making the controls at boot, hidden, was tried: 140 hidden siblings slow every recorder's flight by a third.) */
static HWND mk(const char *cls, const char *text, DWORD st, int x, int y, int w, int h, int id)
{
    HWND c;
    if (mkGroup >= 0) st &= ~WS_VISIBLE;
    c = CreateWindow(cls, text, WS_CHILD | st, x, y, w, h, hMain, (HMENU)id, hInst, NULL);
    SendMessage(c, WM_SETFONT, (WPARAM)panelFont, 0L);
    if (mkGroup >= 0 && grpN[mkGroup] < 72) grpWin[mkGroup][grpN[mkGroup]++] = c;
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
    case 4:   /* the header: preset browser and every sound; pan, offset and the drawn envelope's points */
        hFilter[0] = mk("BUTTON", "All", WS_VISIBLE | BS_PUSHBUTTON, 406, 3, 26, 21, ID_FILTER);       /* the preset browser's */
        hFilter[1] = mk("BUTTON", "W3.11", WS_VISIBLE | BS_PUSHBUTTON, 433, 3, 44, 21, ID_FILTER + 1);  /* filter: Windows 3.x */
        hFilter[2] = mk("BUTTON", "XP", WS_VISIBLE | BS_PUSHBUTTON, 478, 3, 24, 21, ID_FILTER + 2);     /* sounds only, or XP's */
        hPreset = mk("COMBOBOX", "", WS_VISIBLE | WS_VSCROLL | CBS_DROPDOWNLIST, 504, 3, 162, 320, ID_PRESET);
        mk("BUTTON", "<", WS_VISIBLE | BS_PUSHBUTTON, 669, 3, 17, 21, ID_PRESETPREV);   /* the previous / next program */
        mk("BUTTON", ">", WS_VISIBLE | BS_PUSHBUTTON, 687, 3, 17, 21, ID_PRESETNEXT);
        mk("STATIC", "Sound", WS_VISIBLE, 716, 7, 38, 14, -1);
        hLibrary = mk("COMBOBOX", "", WS_VISIBLE | WS_VSCROLL | CBS_DROPDOWNLIST, 756, 3, 262, 320, ID_LIBRARY);   /* (LIBRARY.TSV is in order) */
        listsWanted = TRUE;    /* filled at the first idle moment after the assembly */
        for (i = SL_PAN; i < SL_PAN + 2; i++) {
            int k = i - SL_PAN, x = 410 + k * 132, lw = k ? 40 : 26;
            mk("STATIC", sliders[i].label, WS_VISIBLE, x, 31, lw, 14, -1);
            hSb[i] = mk("SCROLLBAR", "", WS_VISIBLE | SBS_HORZ, x + lw + 2, 31, 64, 14, ID_SB + i);
            SetScrollRange(hSb[i], SB_CTL, sliders[i].lo, sliders[i].hi, FALSE);
            hVal[i] = mk("STATIC", "", WS_VISIBLE, x + lw + 70, 31, 32, 14, ID_VAL + i);
        }
        mk("STATIC", "Env", WS_VISIBLE, 684, 31, 24, 14, -1);
        mk("BUTTON", "<", WS_VISIBLE | BS_PUSHBUTTON, 708, 28, 17, 20, ID_ENVPREV);
        mk("BUTTON", ">", WS_VISIBLE | BS_PUSHBUTTON, 726, 28, 17, 20, ID_ENVNEXT);
        mk("BUTTON", "+", WS_VISIBLE | BS_PUSHBUTTON, 744, 28, 17, 20, ID_ENVADD);
        mk("BUTTON", "-", WS_VISIBLE | BS_PUSHBUTTON, 762, 28, 17, 20, ID_ENVDEL);
        hEnvLbl = mk("STATIC", "A/D/S", WS_VISIBLE, 783, 31, 86, 14, -1);
        for (i = SL_ETIME; i <= SL_ELEVEL; i++) {   /* the point's time and level */
            hSb[i] = mk("SCROLLBAR", "", WS_VISIBLE | SBS_HORZ, i == SL_ETIME ? 870 : 946, 31, 72, 14, ID_SB + i);
            SetScrollRange(hSb[i], SB_CTL, sliders[i].lo, sliders[i].hi, FALSE);
        }
        panel_refresh();
        break;
    case 5:   /* the four macros (automatable in the host; DNA.md 5.3) */
        for (i = SL_MACRO; i < SL_MACRO + 4; i++) {
            int k = i - SL_MACRO;
            mk("STATIC", sliders[i].label, WS_VISIBLE, 8 + k * 216, PANEL + 116, 56, 14, -1);
            hSb[i] = mk("SCROLLBAR", "", WS_VISIBLE | SBS_HORZ, 66 + k * 216, PANEL + 116, 110, 14, ID_SB + i);
            SetScrollRange(hSb[i], SB_CTL, sliders[i].lo, sliders[i].hi, FALSE);
            hVal[i] = mk("STATIC", "", WS_VISIBLE, 180 + k * 216, PANEL + 116, 36, 14, ID_VAL + i);
        }
        panel_refresh();
        break;
    case 3:
        for (i = 4; i < 8; i++) {
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

/* ================================================================ the strip numbers: Calculator's digit keys
   The recorders are 0..F (DNA.md numbers them 0..15). Windows 3.1's Calculator paints its keys itself (they are not
   windows), so its keys are taken as pictures: at startup a real Calculator is opened in Scientific view and Hex,
   and each key 0-F is copied from the screen as Calculator drew it. Calculator has no pressed look (a real press
   changes only its display), so the pressed key is the same picture with its two colours swapped (the key's colour
   fills it, the digit is white). In the assembly the keys fly from Calculator to the strips, and Calculator closes.
   Each is then an owner-drawn button: pressed while held (an audition: the recorder plays at its root rate) and
   while its recorder sounds. */
#define NDIG 16
#define DIGW 39
#define DIGH 28
#define DIGX 4
#define ID_DIG 1300
#define CALCX 272
#define CALCY 214
static HWND hCalc, hDig[NDIG];
static HBITMAP digUp[NDIG], digDn[NDIG], digMask;
static BOOL digShown[NDIG], digHeld[NDIG];
static const int digKX[NDIG] = {221, 221, 264, 307, 221, 264, 307, 221, 264, 307, 221, 264, 307, 350, 393, 436};   /* Calculator's client */
static const int digKY[NDIG] = {216, 180, 180, 180, 144, 144, 144, 108, 108, 108, 252, 252, 252, 252, 252, 252};
static HWND launch(const char *cmd, int show);

static void wait_ms(DWORD ms) { DWORD t = timeGetTime(); while (timeGetTime() - t < ms) pump(); }
static void calc_prepare(void)
{
    HDC sdc, mdc, kdc; POINT o = {0, 0}; int i; COLORREF bg;
    hCalc = launch("CALC.EXE", SW_SHOWNOACTIVATE);
    if (!hCalc) { logf_("no Calculator: plain numbers"); return; }
    SendMessage(hCalc, WM_COMMAND, 305, 0L);                                                 /* View > Scientific */
    SendMessage(hCalc, WM_COMMAND, 124, MAKELPARAM(GetDlgItem(hCalc, 124), BN_CLICKED));      /* Hex */
    SetWindowPos(hCalc, HWND_TOP, CALCX, CALCY, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);
    UpdateWindow(hCalc); pump();
    ClientToScreen(hCalc, &o);
    sdc = GetDC(NULL); mdc = CreateCompatibleDC(sdc); kdc = CreateCompatibleDC(sdc);
    for (i = 0; i < NDIG; i++) {
        int x = o.x + digKX[i], y = o.y + digKY[i], px, py;
        COLORREF ink = RGB(0, 0, 255);
        digUp[i] = CreateCompatibleBitmap(sdc, DIGW, DIGH); digDn[i] = CreateCompatibleBitmap(sdc, DIGW, DIGH);
        SelectObject(mdc, digUp[i]); BitBlt(mdc, 0, 0, DIGW, DIGH, sdc, x, y, SRCCOPY);
        SelectObject(kdc, digDn[i]); BitBlt(kdc, 0, 0, DIGW, DIGH, mdc, 0, 0, SRCCOPY);
        ink = GetPixel(mdc, DIGW / 2, 0);   /* the key's outline colour */
        for (py = 1; py < DIGH - 1; py++) for (px = 1; px < DIGW - 1; px++) {
            COLORREF c = GetPixel(mdc, px, py);
            if (c == RGB(255, 255, 255)) SetPixel(kdc, px, py, ink);
            else if (c == ink) {   /* inside the outline: the digit's pixels (the outline itself stays) */
                BOOL inside = GetPixel(mdc, px - 1, py) == RGB(255, 255, 255) || GetPixel(mdc, px + 1, py) == RGB(255, 255, 255) ||
                              GetPixel(mdc, px, py - 1) == RGB(255, 255, 255) || GetPixel(mdc, px, py + 1) == RGB(255, 255, 255);
                if (inside && px > 3 && px < DIGW - 4 && py > 2 && py < DIGH - 3) SetPixel(kdc, px, py, RGB(255, 255, 255));
            }
        }
    }
    UpdateWindow(hCalc);
    ShowWindow(hCalc, SW_HIDE);   /* until its turn in the assembly (it would only be in the way of the recorders) */
    /* the mask: 1 where Calculator's background shows (outside the rounded key), from the corner's colour */
    SelectObject(mdc, digUp[0]); bg = GetPixel(mdc, 0, 0);
    digMask = CreateBitmap(DIGW, DIGH, 1, 1, NULL);
    SelectObject(kdc, digMask); SetBkColor(mdc, bg); BitBlt(kdc, 0, 0, DIGW, DIGH, mdc, 0, 0, SRCCOPY);
    for (i = 0; i < NDIG; i++) {   /* the pictures with that background black, for SRCAND + SRCPAINT */
        SelectObject(mdc, digUp[i]); BitBlt(mdc, 0, 0, DIGW, DIGH, kdc, 0, 0, 0x00220326L);
        SelectObject(mdc, digDn[i]); BitBlt(mdc, 0, 0, DIGW, DIGH, kdc, 0, 0, 0x00220326L);
    }
    DeleteDC(kdc); DeleteDC(mdc); ReleaseDC(NULL, sdc);
    logf_("Calculator keys taken");
}
static void dig_draw(HDC dc, int i, BOOL down, int x, int y)
{
    HDC mdc = CreateCompatibleDC(dc);
    RECT b; HBRUSH face = CreateSolidBrush(GetSysColor(COLOR_BTNFACE));
    SetRect(&b, x, y, x + DIGW, y + DIGH); FillRect(dc, &b, face); DeleteObject(face);
    if (digMask) {
        COLORREF tc = SetTextColor(dc, RGB(0, 0, 0)), bc = SetBkColor(dc, RGB(255, 255, 255));
        HBITMAP ob = SelectObject(mdc, digMask);
        BitBlt(dc, x, y, DIGW, DIGH, mdc, 0, 0, SRCAND);
        SelectObject(mdc, down ? digDn[i] : digUp[i]); BitBlt(dc, x, y, DIGW, DIGH, mdc, 0, 0, SRCPAINT);
        SelectObject(mdc, ob);
        SetTextColor(dc, tc); SetBkColor(dc, bc);
    } else {   /* no Calculator: the digit as text */
        char t[2]; t[0] = "0123456789ABCDEF"[i]; t[1] = 0;
        SetBkMode(dc, TRANSPARENT);
        DrawText(dc, t, 1, &b, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    }
    DeleteDC(mdc);
}
static void dig_drawitem(const DRAWITEMSTRUCT FAR *d)
{
    int i = d->CtlID - ID_DIG;
    BOOL sel = (d->itemState & ODS_SELECTED) != 0;
    if (i < 0 || i >= NDIG) return;
    if (sel != digHeld[i] && assembled) {   /* held: an audition of this recorder at its root rate */
        digHeld[i] = sel;
        if (sel) play_rec(i, 0, (DWORD)recRate[AR(i)], 65535, 0, -1, 0);
        else stop_rec(AR(i), 0, envR);
    }
    dig_draw(d->hDC, i, sel || rplay[AR(i)], d->rcItem.left, d->rcItem.top);
}
static void dig_watch(void)   /* down while its recorder sounds */
{
    int i;
    for (i = 0; i < NDIG; i++) if (hDig[i] && digShown[i] != (rplay[AR(i)] != 0)) { digShown[i] = rplay[AR(i)] != 0; InvalidateRect(hDig[i], NULL, FALSE); }
}
/* the keys leave Calculator one by one and fly to their strips (drawn on the screen with save-under: nothing else
   paints meanwhile); then they become buttons of BASILISK 16 and Calculator closes */
static void calc_fly(void)
{
    POINT o = {0, 0}; DWORD t0; int i, done = 0;
    HDC sdc, mdc, sav; HBITMAP under[NDIG]; POINT at[NDIG]; BOOL shown[NDIG];
    if (hCalc && digMask) {
        SetWindowPos(hCalc, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW);   /* Calculator's turn */
        UpdateWindow(hCalc);
        { DWORD t1 = timeGetTime(); while (timeGetTime() - t1 < 120) poll_host(); }
        ClientToScreen(hCalc, &o);
        sdc = GetDC(NULL); mdc = CreateCompatibleDC(sdc); sav = CreateCompatibleDC(sdc);
        for (i = 0; i < NDIG; i++) { under[i] = CreateCompatibleBitmap(sdc, DIGW, DIGH); shown[i] = FALSE; }
        t0 = timeGetTime();
        while (done < NDIG) {
            long t = (long)(timeGetTime() - t0);
            done = 0;
            for (i = NDIG - 1; i >= 0; i--)   /* last drawn first undone: what each saved is under the later ones */
                if (shown[i]) { SelectObject(sav, under[i]); BitBlt(sdc, at[i].x, at[i].y, DIGW, DIGH, sav, 0, 0, SRCCOPY); shown[i] = FALSE; }
            for (i = 0; i < NDIG; i++) {
                long f = ease((t - i * 10) * 1000 / 170);
                POINT d; RECT a, q;
                d.x = DIGX; d.y = ROW0 + i * ROWH + 1; ClientToScreen(hMain, &d);
                SetRect(&a, o.x + digKX[i], o.y + digKY[i], o.x + digKX[i] + DIGW, o.y + digKY[i] + DIGH);
                lerp_rect(&q, &a, d.x, d.y, DIGW, DIGH, f);
                if (f >= 1000) { done++; if (!hDig[i]) hDig[i] = CreateWindow("BUTTON", "", WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, DIGX, ROW0 + i * ROWH + 1, DIGW, DIGH, hMain, (HMENU)(ID_DIG + i), hInst, NULL); continue; }
                at[i].x = q.left; at[i].y = q.top;
                SelectObject(sav, under[i]); BitBlt(sav, 0, 0, DIGW, DIGH, sdc, q.left, q.top, SRCCOPY);
                {   /* the key over what is there: mask, then picture */
                    COLORREF tc = SetTextColor(sdc, RGB(0, 0, 0)), bc = SetBkColor(sdc, RGB(255, 255, 255));
                    SelectObject(mdc, digMask); BitBlt(sdc, q.left, q.top, DIGW, DIGH, mdc, 0, 0, SRCAND);
                    SelectObject(mdc, digUp[i]); BitBlt(sdc, q.left, q.top, DIGW, DIGH, mdc, 0, 0, SRCPAINT);
                    SetTextColor(sdc, tc); SetBkColor(sdc, bc);
                }
                shown[i] = TRUE;
            }
            if (hDig[NDIG - 1]) break;
            poll_host();
        }
        for (i = 0; i < NDIG; i++) if (shown[i]) { SelectObject(sav, under[i]); BitBlt(sdc, at[i].x, at[i].y, DIGW, DIGH, sav, 0, 0, SRCCOPY); }
        DeleteDC(sav); DeleteDC(mdc); ReleaseDC(NULL, sdc);
        for (i = 0; i < NDIG; i++) DeleteObject(under[i]);
        PostMessage(hCalc, WM_CLOSE, 0, 0L);
        hCalc = NULL;
    }
    for (i = 0; i < NDIG; i++) if (!hDig[i])
        hDig[i] = CreateWindow("BUTTON", "", WS_CHILD | WS_VISIBLE | BS_OWNERDRAW, DIGX, ROW0 + i * ROWH + 1, DIGW, DIGH, hMain, (HMENU)(ID_DIG + i), hInst, NULL);
}

static void assemble(void)
{
    DWORD t0 = timeGetTime(), tStart = t0; long stage[6];
    long gap = 140, first_extra = 200;   /* the first recorder is shown slowly; the rest follow (140: room for the Calculator keys in 6 s) */
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
        long f = ease(t * 1000 / 300);
        int w = 80 + (int)((long)(full.right - 80) * f / 1000), h = 60 + (int)((long)(full.bottom - 60) * f / 1000);
        SetWindowPos(hMain, NULL, (full.right - w) / 2, (full.bottom - h) / 2, w, h, SWP_NOZORDER | SWP_NOACTIVATE);
        UpdateWindow(hMain);
        poll_host();
        if (f >= 1000) break;
    }
    stage[0] = timeGetTime() - tStart;
    /* the clock joins first: it glides over the recorders to the bottom right, then becomes part of BASILISK 16 */
    if (hClock) {
        RECT c, q, a; LONG st; DWORD t1; POINT o; int k;
        HWND own;
        GetWindowRect(hClock, &c);
        SetRect(&a, c.left, c.top, c.right, c.bottom);
        o.x = 1024 - 140; o.y = PANEL; ClientToScreen(hMain, &o);
        t1 = timeGetTime();
        for (;;) {
            long f = ease((long)(timeGetTime() - t1) * 1000 / 300);
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
    stage[1] = timeGetTime() - tStart;
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
    stage[2] = timeGetTime() - tStart;
    if (hEnvRec) {   /* the seventeenth recorder: everything but its wave display goes, and it glides to the header */
        RECT c, q, a2; DWORD t1; POINT o; LONG st; HWND ch;
        SetMenu(hEnvRec, NULL); DrawMenuBar(hEnvRec);
        for (ch = GetWindow(hEnvRec, GW_CHILD); ch; ch = GetWindow(ch, GW_HWNDNEXT))
            if (GetDlgCtrlID(ch) != SR_WAVE) ShowWindow(ch, SW_HIDE);
        UpdateWindow(hEnvRec);
        {   /* the wave display alone, at the window's corner */
            HWND wv = GetDlgItem(hEnvRec, SR_WAVE);
            SetWindowPos(wv, NULL, 0, 0, 133, 35, SWP_NOZORDER | SWP_NOACTIVATE);   /* native height: centred line */
        }
        GetWindowRect(hEnvRec, &c);
        st = GetWindowLong(hEnvRec, GWL_STYLE);
        SetWindowLong(hEnvRec, GWL_STYLE, (st & ~(WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_DLGFRAME | WS_BORDER)) | WS_POPUP);
        SetWindowPos(hEnvRec, HWND_TOPMOST, c.left, c.top, 133, 35, SWP_NOACTIVATE | SWP_FRAMECHANGED);
        SetRect(&a2, c.left, c.top, c.left + 133, c.top + 35);
        o.x = ENVX; o.y = 2; ClientToScreen(hMain, &o);
        t1 = timeGetTime();
        for (;;) {
            long f = ease((long)(timeGetTime() - t1) * 1000 / 220);
            lerp_rect(&q, &a2, o.x, o.y, 133, 35, f);
            SetWindowPos(hEnvRec, HWND_TOPMOST, q.left, q.top, q.right, q.bottom, SWP_NOACTIVATE);
            UpdateWindow(hEnvRec); UpdateWindow(hMain);
            poll_host();
            if (f >= 1000) break;
        }
        SetWindowPos(hEnvRec, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
        ShowWindow(hEnvRec, SW_HIDE);
        st = GetWindowLong(hEnvRec, GWL_STYLE);
        SetWindowLong(hEnvRec, GWL_STYLE, (st & ~WS_POPUP) | WS_CHILD);
        SetParent(hEnvRec, hMain);
        SetWindowPos(hEnvRec, HWND_TOP, ENVX, 2, 133, 35, SWP_NOACTIVATE | SWP_SHOWWINDOW);
        UpdateWindow(hEnvRec);
    }
    stage[3] = timeGetTime() - tStart;
    {   /* the panel: four groups, one after another */
        int g; DWORD t2;
        for (g = 0; g < 6; g++) {
            panel_create(g);
            t2 = timeGetTime();
            while (timeGetTime() - t2 < 10) { poll_host(); pump(); }
        }
        stage[4] = timeGetTime() - tStart;
        mkGroup = 6; keyboard_create(); mkGroup = -1;
        stage[5] = timeGetTime() - tStart;
        keyboard_show();
    }
    calc_fly();
    stage[5] = timeGetTime() - tStart;   /* (keys made: now with the Calculator's) */
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
    show_envelope();
    logf_("stages: grow %ld clock %ld recorders %ld envelope %ld panel %ld keys made %ld", stage[0], stage[1], stage[2], stage[3], stage[4], stage[5]);
    logf_("ready: assembled in %ld ms (Windows' clock); free resources user %d%% gdi %d%%", (long)(timeGetTime() - tStart), GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES));
    if (pendingDna[0]) { static char d[1100]; lstrcpy(d, pendingDna); pendingDna[0] = 0; build(d); }
}

/* ================================================================ the envelope, drawn by Sound Recorder */
/* The selected layer's amplitude envelope (its drawn Ja, or else the global A/D/S/R) becomes a sound: a buzz whose
   loudness follows the envelope, pasted into the seventeenth Sound Recorder, whose own wave display draws it. */
static void show_envelope(void) { envWant = timeGetTime() | 1; }
static void draw_envelope(void)
{
    static int busy;
    int L = selLayer, n, k, t[12], l[12], total, N = 129;   /* Sound Recorder draws one sample per pixel: the whole envelope fits the 131-pixel view */
    HGLOBAL h; BYTE FAR *w;
    if (!hEnvRec || busy || building || !assembled) return;   /* headless renders: nobody is watching */
    busy = 1;
    if (L >= 0 && L < NL && envN[L] > 0) {
        n = envN[L];
        for (k = 0; k < n; k++) { t[k] = envT[L][k]; l[k] = envL[L][k]; }
        if (t[0] > 0) { for (k = n; k > 0; k--) { t[k] = t[k - 1]; l[k] = l[k - 1]; } t[0] = 0; l[0] = 0; n++; }
    } else {   /* A, D, S */
        n = 0; t[n] = 0; l[n++] = envA ? 0 : 100; t[n] = envA; l[n++] = 100; t[n] = envA + envD; l[n++] = envS;
    }
    t[n] = t[n - 1] + (t[n - 1] / 3 > 150 ? t[n - 1] / 3 : 150); l[n] = l[n - 1]; n++;      /* held */
    t[n] = t[n - 1] + envR; l[n] = 0; n++;                                                   /* release */
    total = t[n - 1] > 0 ? t[n - 1] : 1;
    h = GlobalAlloc(GMEM_MOVEABLE | GMEM_DDESHARE, 44 + N);
    w = (BYTE FAR *)GlobalLock(h);
    _fmemcpy(w, "RIFF", 4); *(DWORD FAR *)(w + 4) = 36 + N; _fmemcpy(w + 8, "WAVEfmt ", 8);
    *(DWORD FAR *)(w + 16) = 16; *(WORD FAR *)(w + 20) = 1; *(WORD FAR *)(w + 22) = 1;
    *(DWORD FAR *)(w + 24) = 22050; *(DWORD FAR *)(w + 28) = 22050; *(WORD FAR *)(w + 32) = 1; *(WORD FAR *)(w + 34) = 8;
    _fmemcpy(w + 36, "data", 4); *(DWORD FAR *)(w + 40) = N;
    for (k = 0; k < N; k++) {
        long ms = (long)k * total / N; int j = 0, a;
        while (j < n - 2 && ms >= t[j + 1]) j++;
        a = t[j + 1] > t[j] ? l[j] + (int)((long)(l[j + 1] - l[j]) * (ms - t[j]) / (t[j + 1] - t[j])) : l[j + 1];
        a = a * 120 / 100;
        w[44 + k] = (BYTE)(128 + ((k & 1) ? a : -a));
    }
    GlobalUnlock(h);
    if (OpenClipboard(hMain)) {
        EmptyClipboard();
        SetClipboardData(CF_WAVE, h);
        CloseClipboard();
        HookActive(TRUE);
        SendMessage(hEnvRec, WM_COMMAND, SR_REW, MAKELPARAM(GetDlgItem(hEnvRec, SR_REW), BN_CLICKED));
        SendMessage(hEnvRec, WM_COMMAND, SR_DELAFTER, 0L);     /* empty it (Sound Recorder asks; the hook says yes) */
        SendMessage(hEnvRec, WM_COMMAND, SR_PASTE, 0L);        /* Paste Insert: the envelope */
        SendMessage(hEnvRec, WM_COMMAND, SR_REW, MAKELPARAM(GetDlgItem(hEnvRec, SR_REW), BN_CLICKED));
        HookActive(FALSE);
    } else GlobalFree(h);
    busy = 0;
}

/* ================================================================ host lines */
static DWORD curId;

static void host_line(char *s)
{
    char *a = strchr(s, ' ');
    char *rest = a ? a + 1 : "";
    if (a) *a = 0;
    if (!strcmp(s, "hi")) {
        int v = atoi(rest); v = v >= 3 ? 3 : v >= 2 ? 2 : 1;
        if (v == 3) say("hi 3 311 %s win,desk,rate,loop,rec", assembled ? "ready" : "wait");   /* the v3 features this guest has */
        else say("hi %d 311 %s", v, assembled ? "ready" : "wait");
    }
    else if (!strcmp(s, "desk")) { if (hMain && assembled) ShowWindow(hMain, atoi(rest) ? SW_MINIMIZE : SW_RESTORE); }
    else if (!strcmp(s, "go")) { if (!assembled) assemble(); else say("ready"); }
    else if (!strcmp(s, "dna")) build(rest);
    else if (!strcmp(s, "on")) {
        /* on <rec> <rate> <vol> [<pan> [<delay_ms> [<layer> [<from> <to>]]]]: the host waits out delays and sends 0;
           v3: the window [from, to) in frames of the layer's buffer (0 0: all) */
        long f[8] = {0, 0, 65535, 0, 0, -1, 0, 0}; int nf = 0; char *p = rest;
        while (*p && nf < 8) { f[nf++] = atol(p); p = strchr(p, ' '); if (!p) break; p++; }
        play_rec((int)f[0], curId, (DWORD)f[1], (WORD)f[2], (int)f[3], (int)f[5], f[6]);
    }
    else if (!strcmp(s, "off")) { int r = atoi(rest); if (r >= 0 && r < NR) stop_rec(AR(r), curId, envR); }
    else if (!strcmp(s, "cut")) { int r = atoi(rest); if (r >= 0 && r < NR) stop_rec(AR(r), curId, 5); }
    else if (!strcmp(s, "rate")) {   /* rate <rec> <hz> [<glide_ms> [<regate>]] (v3) */
        long f[4] = {-1, 0, 0, 0}; int nf = 0; char *p = rest;
        while (*p && nf < 4) { f[nf++] = atol(p); p = strchr(p, ' '); if (!p) break; p++; }
        if (f[0] >= 0 && f[0] < NR) rate_rec(AR((int)f[0]), curId, (DWORD)f[1], (int)f[2], (int)f[3]);
    }
    else if (!strcmp(s, "who")) {   /* who <x> <y>: the window under a screen point (a test aid) */
        POINT pt; HWND w; char cls[32], txt[32];
        pt.x = atoi(rest); pt.y = atoi(strchr(rest, ' ') ? strchr(rest, ' ') + 1 : "0");
        w = WindowFromPoint(pt); cls[0] = txt[0] = 0;
        if (w) { GetClassName(w, cls, sizeof cls); GetWindowText(w, txt, sizeof txt); }
        say("who %d %d %04x %s id %d en %d '%s' parent %04x", pt.x, pt.y, (WORD)w, cls, w ? GetDlgCtrlID(w) : 0, w ? IsWindowEnabled(w) : 0, txt, w ? (WORD)GetParent(w) : 0);
    }
    else if (!strcmp(s, "calcshow")) {   /* test aid: a Calculator in Scientific + Hex where the donor one was */
        HWND c = launch("CALC.EXE", SW_SHOWNOACTIVATE);
        if (c) { SendMessage(c, WM_COMMAND, 305, 0L); SendMessage(c, WM_COMMAND, 124, MAKELPARAM(GetDlgItem(c, 124), BN_CLICKED));
                 SetWindowPos(c, HWND_TOPMOST, CALCX, CALCY, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE); UpdateWindow(c); }
        say("calcshow %d", c != NULL);
    }
    else if (!strcmp(s, "panic")) { int r; for (r = 0; r < NALL; r++) stop_rec(r, 0, 5); }
    else if (!strcmp(s, "env")) {
        sscanf(rest, "%d %d %d %d", &envA, &envD, &envS, &envR);
        bs_env((WORD)envA, (WORD)envD, (WORD)envS);
        show_envelope();
    }
    else if (!strcmp(s, "lenv")) {   /* lenv <layer> <a|p> <t,l.t,l...|-> [<loop>] (v3: the last <loop> points repeat while held) */
        int L = atoi(rest), kind, n = 0, t[8], l[8], loop = 0; char *p = strchr(rest, ' ');
        if (p && L >= 0 && L < NL) {
            kind = p[1] == 'p'; p = strchr(p + 1, ' ');
            if (p && p[1] != '-') {
                const char *q = p + 1;
                while (*q && n < 8) {
                    t[n] = getint(&q, 0); if (*q == ',') q++; l[n] = getint(&q, 0); n++;
                    if (*q == '.') q++; else break;
                }
            }
            if (p && (p = strchr(p + 1, ' ')) != NULL) loop = atoi(p + 1);
            bs_lenv(L, kind, n, t, l, loop);
            if (!kind) { envN[L] = n; memcpy(envT[L], t, sizeof t); memcpy(envL[L], l, sizeof l); show_envelope(); }
        }
    }
    else if (!strcmp(s, "show") || !strcmp(s, "cc") || !strcmp(s, "bend")) kb_show(s, rest);
    else if (!strcmp(s, "sel")) { selLayer = atoi(rest); if (selLayer >= nlay || selLayer < 0) selLayer = 0; if (hMain) InvalidateRect(hMain, NULL, FALSE); panel_refresh(); }
    else if (!strcmp(s, "time")) {
        int Y, M, D, h, m, x;
        if (sscanf(rest, "%d %d %d %d %d %d", &Y, &M, &D, &h, &m, &x) == 6) set_time(Y, M, D, h, m, x);
    }
}

/* The host's pointer. BSYNTH.DRV moves it at interrupt time with USER's mouse_event (BsPointer), so a held scroll
   bar thumb follows a drag; until that runs (or without it) the pointer events come here and SetCursorPos places
   the arrow, which makes no mouse input. */
static void pointer_feed(void)
{
    static BOOL done;
    BOOL (FAR PASCAL *f)(BOOL, WORD, WORD); HMODULE m;
    if (done) return;
    done = TRUE;
    m = GetModuleHandle("BSYNTH");
    f = m ? (BOOL (FAR PASCAL *)(BOOL, WORD, WORD))GetProcAddress(m, "BSPOINTER") : NULL;
    logf_("pointer feed %s", f && f(TRUE, (WORD)GetSystemMetrics(SM_CXSCREEN), (WORD)GetSystemMetrics(SM_CYSCREEN)) ? "on" : "missing: SetCursorPos only");
}
static void host_pointer(int x, int y) { SetCursorPos(x, y); }

static int poll_host(void)   /* returns how many events it handled */
{
    static WORD e[140];
    static char acc[1200]; static int accn;
    int n, k, handled = 0;
    while ((n = bs_event(e, 140)) > 0) {
        int ty = e[0] >> 8;
        if (ty == 6 && n >= 3) { host_pointer(e[1], e[2]); handled++; continue; }   /* the host's pointer */
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
    if (assembled) TextOut(dc, ENVX - 58, 12, "Envelope", 8);
    SelectObject(dc, big);
    SelectObject(dc, sm);
    SetTextColor(dc, RGB(0, 0, 0));
    if (assembled) {
        static const char *hdr[] = {"Status", "Wave", "Position", "Length", "Seek", "Rewind", "Forward", "Play", "Stop", "Record"};
        int hx[] = {4, 88, 228, 298, 370, 648, 702, 756, 810, 864};
        /* each drawn after a space, the space's width to the left: Windows 3.1 cuts off what a glyph draws left of
           where the string starts, and Arial's W reaches one pixel left of its cell */
        for (i = 0; i < 10; i++) {
            char t[16]; DWORD e = GetTextExtent(dc, " ", 1);
            t[0] = ' '; lstrcpy(t + 1, hdr[i]);
            TextOut(dc, STRIPX + hx[i] - LOWORD(e), ROW0 - 15, t, lstrlen(t));
        }
    }
    for (i = 0; i < NR; i++) {   /* left of each Calculator key: its layer's colour (yellow while it is built) */
        RECT b;
        int y = ROW0 + i * ROWH;
        int l = rlayer[AR(i)];
        SetRect(&b, 0, y + 3, 3, y + 27);
        if (i == buildRow || l >= 0) {
            HBRUSH br = CreateSolidBrush(i == buildRow ? RGB(255, 255, 0) : layerColor[l % NL]);
            FillRect(dc, &b, br); DeleteObject(br);
        }
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
    case WM_DRAWITEM: if (w >= ID_DIG && w < ID_DIG + NDIG) { dig_drawitem((const DRAWITEMSTRUCT FAR *)l); return TRUE; } break;
    case WM_HSCROLL: panel_scroll((HWND)HIWORD(l), w, LOWORD(l)); return 0;
    case WM_VSCROLL: kb_scroll((HWND)HIWORD(l), w, LOWORD(l)); return 0;
    case WM_KEYDOWN: case WM_KEYUP: if (computer_key(w, l, m == WM_KEYDOWN)) return 0; break;
    case WM_CTLCOLOR:                  /* the panel's labels sit on the window's grey */
        if (HIWORD(l) == CTLCOLOR_STATIC || HIWORD(l) == CTLCOLOR_BTN) {   /* (and the Hold / Keys boxes) */
            static HBRUSH face;
            if (!face) face = CreateSolidBrush(GetSysColor(COLOR_BTNFACE));
            SetBkColor((HDC)w, GetSysColor(COLOR_BTNFACE));
            return (LRESULT)(WORD)face;
        }
        break;
    case WM_COMMAND: {
        int r;
        if (w >= 1100 && w < 1200) { panel_command(w, HIWORD(l)); return 0; }
        /* a reparented recorder's buttons report to us: hand the click to its recorder */
        for (r = 0; r < NALL; r++) if (rw[r] && (HWND)LOWORD(l) && GetParent((HWND)LOWORD(l)) == rw[r]) {
            PostMessage(rw[r], WM_COMMAND, w, l);
            return 0;
        }
        break; }
    case WM_SIZE:                      /* desktop mode (PRESET-ENGINE-2 section 10): the host hears it */
        if (assembled) {
            static int iconic;
            if (w == SIZE_MINIMIZED && !iconic) { iconic = 1; say("desk 1"); }
            else if (w != SIZE_MINIMIZED && iconic) { int r; iconic = 0; for (r = 0; r < NR; r++) layout_strip(r); say("desk 0"); }
        }
        break;
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
    wc.hIcon = ExtractIcon(hi, "C:\\WINDOWS\\SOUNDREC.EXE", 0);   /* minimized, BASILISK 16 is Sound Recorder's icon */
    if ((UINT)wc.hIcon <= 1) wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
    RegisterClass(&wc);
    hMain = CreateWindow("Basilisk16", "BASILISK 16 - Sound Recorder Synthesizer", WS_POPUP | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_CLIPCHILDREN,
                         0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), NULL, NULL, hi, NULL);

    /* the desktop as the visitor first sees it: Program Manager out of the way, a clock, sixteen recorders */
    pm = FindWindow("Progman", NULL);
    if (pm) ShowWindow(pm, SW_MINIMIZE);
    calc_prepare();   /* first, while nothing covers it: its keys' pictures (the recorders open over it) */
    hClock = launch("CLOCK.EXE", SW_SHOWNOACTIVATE);
    hEnvRec = launch("SOUNDREC.EXE C:\\WINDOWS\\DING.WAV", SW_SHOWNOACTIVATE);
    if (hEnvRec) MoveWindow(hEnvRec, 700, 560, 320, 186, TRUE);
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
    pointer_feed();
    logf_("SYNTH up: %d recorders, free resources: user %d%% gdi %d%%", NALL, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES));
    {   /* idle: the engine may freeze the machine here (the snapshot) */
        WORD z = 0; bs_report(2, &z, 0);
    }
    for (;;) {
        MSG m;
        if (PeekMessage(&m, 0, 0, 0, PM_REMOVE)) {
            if (m.message == WM_QUIT) break;
            if (m.message == WM_KEYDOWN && m.wParam == VK_F1) { WinHelp(hMain, "C:\\BS\\BASIL16.HLP", HELP_CONTENTS, 0L); continue; }
            TranslateMessage(&m); DispatchMessage(&m);
        } else {
            if (!poll_host()) {
                if (listsWanted && assembled && !building) { DWORD tl = timeGetTime(); listsWanted = FALSE; panel_lists(); logf_("lists in %ld ms", (long)(timeGetTime() - tl)); }
                else if (envWant && timeGetTime() - envWant > 120 && !building) { envWant = 0; draw_envelope(); }
                else bs_idle();
            }
        }
    }
    HookInstall(FALSE);
    return 0;
}
