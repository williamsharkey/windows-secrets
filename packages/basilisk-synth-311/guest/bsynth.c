/* BSYNTH.DRV - Windows 3.11 wave-output driver for the BSYN multi-voice card (BASILISK 16).
   One card voice per waveOutOpen, so any number of programs (up to 32 voices) play at once.
   Built with Open Watcom: see build.sh. */
#include <windows.h>
#include <mmsystem.h>
#include <conio.h>
#include <i86.h>
#include <string.h>
#include "bsynth.h"

/* ---- from the Windows 3.1 DDK (mmddk.h), which Open Watcom does not ship ---- */
#define DRV_LOAD 0x0001
#define DRV_ENABLE 0x0002
#define DRV_OPEN 0x0003
#define DRV_CLOSE 0x0004
#define DRV_DISABLE 0x0005
#define DRV_FREE 0x0006
#define DRV_CONFIGURE 0x0007
#define DRV_QUERYCONFIGURE 0x0008
#define DRV_INSTALL 0x0009
#define DRV_REMOVE 0x000A
#define DRVCNF_RESTART 0x0002
#define WODM_GETNUMDEVS 3
#define WODM_GETDEVCAPS 4
#define WODM_OPEN 5
#define WODM_CLOSE 6
#define WODM_PREPARE 7
#define WODM_UNPREPARE 8
#define WODM_WRITE 9
#define WODM_PAUSE 10
#define WODM_RESTART 11
#define WODM_RESET 12
#define WODM_GETPOS 13
#define WODM_GETPITCH 14
#define WODM_SETPITCH 15
#define WODM_GETVOLUME 16
#define WODM_SETVOLUME 17
#define WODM_GETPLAYBACKRATE 18
#define WODM_SETPLAYBACKRATE 19
#define WODM_BREAKLOOP 20
#define WIDM_GETNUMDEVS 50
#define WIDM_GETDEVCAPS 51
#define WIDM_OPEN 52
#define WIDM_CLOSE 53
#define WIDM_PREPARE 54
#define WIDM_UNPREPARE 55
#define WIDM_ADDBUFFER 56
#define WIDM_START 57
#define WIDM_STOP 58
#define WIDM_RESET 59
#define WIDM_GETPOS 60
typedef struct { HWAVE hWave; const WAVEFORMAT FAR *lpFormat; DWORD dwCallback; DWORD dwInstance; } WAVEOPENDESC;
typedef WAVEOPENDESC FAR *LPWAVEOPENDESC;
#define DCB_TYPEMASK 0x0007
BOOL WINAPI DriverCallback(DWORD dwCallback, UINT uFlags, HANDLE hDevice, UINT uMessage, DWORD dwUser, DWORD dwParam1, DWORD dwParam2);
DWORD WINAPI GetSelectorBase(UINT sel);

#define MAXI 32
typedef struct { BOOL used; HWAVE hWave; DWORD cb, inst; DWORD flags; int ch; WORD align; } INST;
static INST in[MAXI];
static UINT timer;
static BOOL card;
/* the wave input (RECORDING.md 1.3): the card's one ADC, one open at a time */
static INST win;   /* .used, .hWave, .cb, .inst, .flags, .align */
static void ensure_timer(void);

static void put(WORD w) { outpw(BS_ARG, w); }
static void put32(DWORD d) { outpw(BS_ARG, LOWORD(d)); outpw(BS_ARG, HIWORD(d)); }
static WORD get(void) { return inpw(BS_ARG); }

static void notify(INST *p, UINT msg, DWORD p1)
{
    BOOL r = DriverCallback(p->cb, HIWORD(p->flags), (HANDLE)p->hWave, msg, p->inst, p1, 0L);
#ifdef BSDEBUG
    _disable();
    outpw(BS_ARG, (5 << 8) | 8); outpw(BS_ARG, msg); outpw(BS_ARG, LOWORD(p->cb)); outpw(BS_ARG, HIWORD(p->cb));
    outpw(BS_ARG, p->flags); outpw(BS_ARG, HIWORD(p1)); outpw(BS_ARG, (WORD)p->hWave); outpw(BS_ARG, r);
    outpw(BS_CMD, BSC_REPORT);
    _enable();
#endif
}

/* hand back every finished buffer (called from the timer, at interrupt time, and after a reset) */
static void drain(void)
{
    WORD n, i, ch; DWORD ck; LPWAVEHDR h; int k;
    for (;;) {
        _disable();
        outpw(BS_CMD, BSC_POLLDONE);
        n = get();
        if (!n) { _enable(); return; }
        {
            static WORD buf[60];
            for (i = 0; i < n * 3 && i < 60; i++) buf[i] = get();
            _enable();
            for (i = 0; i < n; i++) {
                ch = buf[i * 3]; ck = MAKELONG(buf[i * 3 + 1], buf[i * 3 + 2]);
                h = (LPWAVEHDR)ck;
                h->dwFlags &= ~WHDR_INQUEUE;
                h->dwFlags |= WHDR_DONE;
                for (k = 0; k < MAXI; k++) if (in[k].used && in[k].ch == (int)ch) { notify(&in[k], WOM_DONE, ck); break; }
            }
        }
    }
}

/* hand back every filled input buffer (WIM_DATA) */
static void drain_in(void)
{
    WORD n, i; DWORD ck, nb; LPWAVEHDR h;
    if (!win.used) return;
    for (;;) {
        static WORD buf[60];
        _disable();
        outpw(BS_CMD, BSC_INPOLL);
        n = get();
        for (i = 0; i < n * 4 && i < 60; i++) buf[i] = get();
        _enable();
        if (!n) return;
        for (i = 0; i < n; i++) {
            ck = MAKELONG(buf[i * 4], buf[i * 4 + 1]); nb = MAKELONG(buf[i * 4 + 2], buf[i * 4 + 3]);
            h = (LPWAVEHDR)ck;
            h->dwBytesRecorded = nb;
            h->dwFlags &= ~WHDR_INQUEUE;
            h->dwFlags |= WHDR_DONE;
            notify(&win, WIM_DATA, ck);
        }
    }
}

void FAR PASCAL __loadds __export TimeProc(UINT id, UINT msg, DWORD user, DWORD d1, DWORD d2)
{
    drain();
    drain_in();
}

/* The host's pointer (BsPointer): every 10 ms at interrupt time, a new position from the card becomes real mouse
   input through USER's mouse_event (USER.299, the entry the mouse driver itself calls at interrupt time; registers
   AX flags, BX x, CX y, DX buttons, SI:DI extra). SetCursorPos in the synth program cannot do this: it makes no
   input, and it does not run while a scroll bar's tracking loop (a modal loop) holds the program. */
static FARPROC mouseEvent;
static UINT ptrTimer;
static WORD ptrSeq, scrW = 1024, scrH = 768;
void mev_call(WORD ax, WORD bx, WORD cx, WORD dx, FARPROC f);
#pragma aux mev_call = \
    "push bp" \
    "push es" \
    "push di" \
    "mov bp, sp" \
    "xor si, si" \
    "xor di, di" \
    "call dword ptr ss:[bp]" \
    "add sp, 4" \
    "pop bp" \
    parm [ax] [bx] [cx] [dx] [es di] \
    modify [ax bx cx dx si di es];
void FAR PASCAL __loadds __export PtrProc(UINT id, UINT msg, DWORD user, DWORD d1, DWORD d2)
{
    WORD seq, x, y;
    _disable(); outpw(BS_CMD, 32); seq = get(); x = get(); y = get(); _enable();
    if (seq == ptrSeq) return;
    ptrSeq = seq;
    mev_call(0x8001, (WORD)(((DWORD)x * 65535UL + (scrW - 1) / 2) / (scrW - 1)), (WORD)(((DWORD)y * 65535UL + (scrH - 1) / 2) / (scrH - 1)), 2, mouseEvent);
}
/* the synth program turns the pointer feed on (TRUE) once, with the screen size; FALSE stops it */
BOOL FAR PASCAL __loadds __export BsPointer(BOOL on, WORD w, WORD h)
{
    if (!card) return FALSE;
    if (!on) { if (ptrTimer) timeKillEvent(ptrTimer); ptrTimer = 0; return TRUE; }
    if (ptrTimer) return TRUE;
    if (!mouseEvent) mouseEvent = GetProcAddress(GetModuleHandle("USER"), MAKEINTRESOURCE(299));
    if (!mouseEvent || w < 2 || h < 2) return FALSE;
    scrW = w; scrH = h;
    _disable(); outpw(BS_CMD, 32); ptrSeq = get(); get(); get(); _enable();
    ptrTimer = timeSetEvent(10, 10, (LPTIMECALLBACK)PtrProc, 0L, TIME_PERIODIC);   /* resolution 10: a 1 ms one reprograms the PIT to 1 kHz and slows the whole machine */
    return ptrTimer != 0;
}

static int nopen(void) { int k, n = win.used ? 1 : 0; for (k = 0; k < MAXI; k++) if (in[k].used) n++; return n; }
static void ensure_timer(void) { if (!timer) timer = timeSetEvent(10, 5, (LPTIMECALLBACK)TimeProc, 0, TIME_PERIODIC); }

DWORD FAR PASCAL __loadds __export widMessage(UINT dev, UINT msg, DWORD user, DWORD p1, DWORD p2)
{
    switch (msg) {
    case WIDM_GETNUMDEVS:
        return card ? 1 : 0;
    case WIDM_GETDEVCAPS: {
        WAVEINCAPS FAR *c = (WAVEINCAPS FAR *)p1;
        WAVEINCAPS w;
        w.wMid = 1; w.wPid = 0xB6; w.vDriverVersion = 0x0100;
        lstrcpy(w.szPname, "BASILISK 16 Input");
        w.dwFormats = 0xFFF; w.wChannels = 2;
        _fmemcpy(c, &w, (UINT)p2 < sizeof w ? (UINT)p2 : sizeof w);
        return 0; }
    case WIDM_OPEN: {
        LPWAVEOPENDESC d = (LPWAVEOPENDESC)p1;
        const PCMWAVEFORMAT FAR *f = (const PCMWAVEFORMAT FAR *)d->lpFormat;
        WORD ok;
        if (!card) return MMSYSERR_NOTENABLED;
        if (f->wf.wFormatTag != WAVE_FORMAT_PCM || (f->wf.nChannels != 1 && f->wf.nChannels != 2) ||
            (f->wBitsPerSample != 8 && f->wBitsPerSample != 16) || f->wf.nSamplesPerSec < 4000 || f->wf.nSamplesPerSec > 48000)
            return WAVERR_BADFORMAT;
        if (LOWORD(p2) & WAVE_FORMAT_QUERY) return 0;
        if (win.used) return MMSYSERR_ALLOCATED;
        _disable();
        put32(f->wf.nSamplesPerSec); put(f->wBitsPerSample); put(f->wf.nChannels);
        outpw(BS_CMD, BSC_INOPEN);
        ok = get();
        _enable();
        if (!ok) return MMSYSERR_ALLOCATED;
        win.used = TRUE; win.hWave = d->hWave; win.cb = d->dwCallback; win.inst = d->dwInstance;
        win.flags = p2; win.align = f->wf.nBlockAlign;
        *(DWORD FAR *)user = 1;
        ensure_timer();
        notify(&win, WIM_OPEN, 0);
        return 0; }
    }
    if (!win.used) return MMSYSERR_INVALHANDLE;
    switch (msg) {
    case WIDM_CLOSE:
        _disable(); outpw(BS_CMD, BSC_INRESET); _enable();
        drain_in();
        _disable(); outpw(BS_CMD, BSC_INCLOSE); _enable();
        notify(&win, WIM_CLOSE, 0);
        win.used = FALSE;
        if (!nopen() && timer) { timeKillEvent(timer); timer = 0; }
        return 0;
    case WIDM_ADDBUFFER: {
        LPWAVEHDR h = (LPWAVEHDR)p1; DWORD lin;
        if (!(h->dwFlags & WHDR_PREPARED)) return WAVERR_UNPREPARED;
        h->dwFlags &= ~WHDR_DONE; h->dwFlags |= WHDR_INQUEUE; h->dwBytesRecorded = 0;
        lin = GetSelectorBase(SELECTOROF(h->lpData)) + OFFSETOF(h->lpData);
        _disable(); put32(lin); put32(h->dwBufferLength); put32((DWORD)h); outpw(BS_CMD, BSC_INADD); _enable();
        return 0; }
    case WIDM_START: _disable(); outpw(BS_CMD, BSC_INSTART); _enable(); return 0;
    case WIDM_STOP: _disable(); outpw(BS_CMD, BSC_INSTOP); _enable(); drain_in(); return 0;
    case WIDM_RESET: _disable(); outpw(BS_CMD, BSC_INRESET); _enable(); drain_in(); return 0;
    case WIDM_GETPOS: {
        LPMMTIME t = (LPMMTIME)p1; DWORD b;
        _disable(); outpw(BS_CMD, BSC_INGETPOS); b = get(); b |= (DWORD)get() << 16; _enable();
        if (t->wType == TIME_SAMPLES && win.align) t->u.sample = b / win.align;
        else { t->wType = TIME_BYTES; t->u.cb = b; }
        return 0; }
    case WIDM_PREPARE: case WIDM_UNPREPARE:
        return MMSYSERR_NOTSUPPORTED;
    }
    return MMSYSERR_NOTSUPPORTED;
}

DWORD FAR PASCAL __loadds __export wodMessage(UINT dev, UINT msg, DWORD user, DWORD p1, DWORD p2)
{
    INST *p = (user && (WORD)user <= MAXI) ? &in[(WORD)user - 1] : NULL;
    switch (msg) {
    case WODM_GETNUMDEVS:
        return card ? 1 : 0;
    case WODM_GETDEVCAPS: {
        WAVEOUTCAPS FAR *c = (WAVEOUTCAPS FAR *)p1;
        WAVEOUTCAPS w;
        w.wMid = 1; w.wPid = 0xB5; w.vDriverVersion = 0x0100;
        lstrcpy(w.szPname, "BASILISK 16 Wave");
        w.dwFormats = 0xFFF; w.wChannels = 2;
        w.dwSupport = WAVECAPS_VOLUME | WAVECAPS_LRVOLUME | WAVECAPS_PLAYBACKRATE;
        _fmemcpy(c, &w, (UINT)p2 < sizeof w ? (UINT)p2 : sizeof w);
        return 0; }
    case WODM_OPEN: {
        LPWAVEOPENDESC d = (LPWAVEOPENDESC)p1;
        const PCMWAVEFORMAT FAR *f = (const PCMWAVEFORMAT FAR *)d->lpFormat;
        int k; WORD ch;
        if (!card) return MMSYSERR_NOTENABLED;
        if (f->wf.wFormatTag != WAVE_FORMAT_PCM || (f->wf.nChannels != 1 && f->wf.nChannels != 2) ||
            (f->wBitsPerSample != 8 && f->wBitsPerSample != 16) || f->wf.nSamplesPerSec < 2000 || f->wf.nSamplesPerSec > 96000)
            return WAVERR_BADFORMAT;
        if (LOWORD(p2) & WAVE_FORMAT_QUERY) return 0;
        for (k = 0; k < MAXI && in[k].used; k++) {}
        if (k == MAXI) return MMSYSERR_ALLOCATED;
        _disable();
        put((WORD)GetCurrentTask()); put(f->wf.nChannels); put(f->wBitsPerSample); put32(f->wf.nSamplesPerSec);
        outpw(BS_CMD, BSC_OPEN);
        ch = get();
        _enable();
        if (ch == 0xFFFF) return MMSYSERR_ALLOCATED;
        in[k].used = TRUE; in[k].hWave = d->hWave; in[k].cb = d->dwCallback; in[k].inst = d->dwInstance;
        in[k].flags = p2; in[k].ch = ch; in[k].align = f->wf.nBlockAlign;
        *(DWORD FAR *)user = k + 1;
        ensure_timer();
        notify(&in[k], WOM_OPEN, 0);
        return 0; }
    }
    if (!p) return MMSYSERR_INVALHANDLE;
    switch (msg) {
    case WODM_CLOSE:
        drain();
        _disable(); put(p->ch); outpw(BS_CMD, BSC_CLOSE); _enable();
        drain();
        notify(p, WOM_CLOSE, 0);
        p->used = FALSE;
        if (!nopen() && timer) { timeKillEvent(timer); timer = 0; }
        return 0;
    case WODM_WRITE: {
        LPWAVEHDR h = (LPWAVEHDR)p1; WORD ok;
        DWORD lin;
        if (!(h->dwFlags & WHDR_PREPARED)) return WAVERR_UNPREPARED;
        h->dwFlags &= ~WHDR_DONE; h->dwFlags |= WHDR_INQUEUE;
        lin = GetSelectorBase(SELECTOROF(h->lpData)) + OFFSETOF(h->lpData);
        _disable();
        put(p->ch); put32(lin); put32(h->dwBufferLength); put32((DWORD)h);
        outpw(BS_CMD, BSC_WRITE);
        ok = get();
        _enable();
        if (!ok) { h->dwFlags &= ~WHDR_INQUEUE; h->dwFlags |= WHDR_DONE; notify(p, WOM_DONE, p1); }
        return 0; }
    case WODM_PAUSE: _disable(); put(p->ch); outpw(BS_CMD, BSC_PAUSE); _enable(); return 0;
    case WODM_RESTART: _disable(); put(p->ch); outpw(BS_CMD, BSC_RESTART); _enable(); return 0;
    case WODM_RESET:
        _disable(); put(p->ch); outpw(BS_CMD, BSC_RESET); _enable();
        drain();
        return 0;
    case WODM_BREAKLOOP: return 0;
    case WODM_GETPOS: {
        LPMMTIME t = (LPMMTIME)p1; DWORD fr;
        drain();
        _disable(); put(p->ch); outpw(BS_CMD, BSC_GETPOS); fr = get(); fr |= (DWORD)get() << 16; _enable();
        if (t->wType == TIME_SAMPLES) t->u.sample = fr;
        else { t->wType = TIME_BYTES; t->u.cb = fr * p->align; }
        return 0; }
    case WODM_SETVOLUME:
        _disable(); put(p->ch); put(LOWORD(p1)); put(HIWORD(p1)); outpw(BS_CMD, BSC_SETVOL); _enable(); return 0;
    case WODM_GETVOLUME: {
        DWORD v;
        _disable(); put(p->ch); outpw(BS_CMD, BSC_GETVOL); v = get(); v |= (DWORD)get() << 16; _enable();
        *(DWORD FAR *)p1 = v; return 0; }
    case WODM_SETPLAYBACKRATE:
        _disable(); put(p->ch); put32(p1); outpw(BS_CMD, BSC_SETRATE); _enable(); return 0;
    case WODM_GETPLAYBACKRATE: {
        DWORD v;
        _disable(); put(p->ch); outpw(BS_CMD, BSC_GETRATE); v = get(); v |= (DWORD)get() << 16; _enable();
        *(DWORD FAR *)p1 = v; return 0; }
    case WODM_PREPARE: case WODM_UNPREPARE:
        return MMSYSERR_NOTSUPPORTED;
    }
    return MMSYSERR_NOTSUPPORTED;
}

LRESULT FAR PASCAL __loadds __export DriverProc(DWORD id, HANDLE hd, UINT msg, LPARAM l1, LPARAM l2)
{
    switch (msg) {
    case DRV_LOAD: card = (inpw(BS_MAGIC) == 0x5342); return 1L;
    case DRV_FREE: case DRV_OPEN: case DRV_CLOSE: case DRV_ENABLE: case DRV_DISABLE: return 1L;
    case DRV_QUERYCONFIGURE: return 0L;
    case DRV_INSTALL: case DRV_REMOVE: return DRVCNF_RESTART;
    }
    return DefDriverProc(id, hd, msg, l1, l2);
}

int FAR PASCAL LibMain(HINSTANCE hi, WORD ds, WORD heap, LPSTR cmd) { return 1; }
int FAR PASCAL __export WEP(int x) { return 1; }
