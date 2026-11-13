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

void FAR PASCAL __loadds __export TimeProc(UINT id, UINT msg, DWORD user, DWORD d1, DWORD d2)
{
    drain();
}

static int nopen(void) { int k, n = 0; for (k = 0; k < MAXI; k++) if (in[k].used) n++; return n; }

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
        if (!timer) timer = timeSetEvent(10, 5, (LPTIMECALLBACK)TimeProc, 0, TIME_PERIODIC);
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
