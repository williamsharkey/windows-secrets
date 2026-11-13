/* PRESET ENGINE 2, measurement T3 on XP: the handle swap with SOFTWARE gain (design/PRESET-ENGINE-2.md 5.3).

   Found first (xp_swaptest tone): on this XP, waveOutSetVolume is one device-wide Wave volume, shared by every
   handle of every process. So a crossfade cannot ramp two handles' volumes. This program streams each voice's PCM
   to its own stereo handle in 10 ms chunks (a ring of 4) and applies gain and pan to the samples it copies, as srhook
   would. A swap is then exact in frames: A's stream ramps down from the first frame it has not queued yet (F), and B
   starts S = F - rateB * (dt - Lb) frames earlier at gain 0, so that B reaches F when A does. dt: the time until A
   plays F (from waveOutGetPosition); Lb: B's start latency (calibrated with mode align).

   Build: i686-w64-mingw32-gcc -O2 -o xp_stream.exe xp_stream.c -lwinmm -static
   Modes: align N            | xfade N semis fadeMs split(0/1) LbMs   | glide N semis ms steps fadeMs LbMs
          wow secs depth hz stepMs q cache fadeMs LbMs                | bend secs depth hz stepMs q cache fadeMs LbMs */
#include <windows.h>
#include <mmsystem.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define SR 22050
#define SECS 14
#ifndef NQ
#define NQ 4
#endif
#ifndef CHUNK_MS
#define CHUNK_MS 10
#endif
static short sine[SR * SECS], noise[SR * SECS];
static LARGE_INTEGER qf, q0;
static double now(void) { LARGE_INTEGER t; QueryPerformanceCounter(&t); return (t.QuadPart - q0.QuadPart) * 1000.0 / qf.QuadPart; }
static CRITICAL_SECTION cs;

typedef struct {
    HWAVEOUT h; int rate; double used;
    int active;                 /* streaming */
    const short *src; int pos, end, base;   /* next source frame to queue; frame of the stream's first sample */
    double g, gStep; int rampLeft, zeroLeft, holdLeft, stopAfter;   /* gain now, per-frame step, frames left in the ramp */
    double panL, panR;
    WAVEHDR hdr[NQ]; short *buf[NQ]; int chunk;
} V;
#define MAXV 48
static V vc[MAXV];
static int nv = 4;

static HWAVEOUT openh(int rate, double *ms)
{
    WAVEFORMATEX f; HWAVEOUT h = 0; double t = now();
    memset(&f, 0, sizeof f);
    f.wFormatTag = WAVE_FORMAT_PCM; f.nChannels = 2; f.nSamplesPerSec = rate; f.wBitsPerSample = 16;
    f.nBlockAlign = 4; f.nAvgBytesPerSec = rate * 4;
    if (waveOutOpen(&h, 0, &f, 0, 0, CALLBACK_NULL) != MMSYSERR_NOERROR) h = 0;
    if (ms) *ms = now() - t;
    return h;
}
static void vstop(V *v)
{
    int i;
    v->active = 0;
    if (!v->h) return;
    waveOutReset(v->h);
    for (i = 0; i < NQ; i++) if (v->hdr[i].dwFlags & WHDR_PREPARED) waveOutUnprepareHeader(v->h, &v->hdr[i], sizeof(WAVEHDR));
}
static V *cached(int rate, V *keep, double *openMs)
{
    int i, pick = -1;
    *openMs = 0;
    for (i = 0; i < nv; i++) if (vc[i].h && vc[i].rate == rate) { vc[i].used = now(); return &vc[i]; }
    for (i = 0; i < nv; i++) if (!vc[i].h) { pick = i; break; }
    if (pick < 0) {
        for (i = 0; i < nv; i++) if (&vc[i] != keep && !vc[i].active && (pick < 0 || vc[i].used < vc[pick].used)) pick = i;
        if (pick < 0) return NULL;
        vstop(&vc[pick]); waveOutClose(vc[pick].h); vc[pick].h = 0;
    }
    vc[pick].h = openh(rate, openMs); vc[pick].rate = rate; vc[pick].used = now();
    vc[pick].chunk = rate * CHUNK_MS / 1000;
    for (i = 0; i < NQ; i++) { if (!vc[pick].buf[i]) vc[pick].buf[i] = (short *)malloc(SR * 4 * 2 / 10); memset(&vc[pick].hdr[i], 0, sizeof(WAVEHDR)); }
    return &vc[pick];
}
/* fill one chunk: gain ramps and pan applied per sample */
static int fill(V *v, int i)
{
    int k, n = v->chunk;
    short *o = v->buf[i];
    if (v->pos >= v->end || (v->stopAfter && v->rampLeft <= 0 && v->g <= 0)) return 0;
    if (n > v->end - v->pos) n = v->end - v->pos;
    for (k = 0; k < n; k++) {
        double s;
        if (v->zeroLeft > 0) { v->zeroLeft--; s = 0; }
        else {
            if (v->holdLeft > 0) v->holdLeft--;
            else if (v->rampLeft > 0) {
                v->g += v->gStep; v->rampLeft--;
                if (v->g < 0) v->g = 0;
                if (v->g > 1) v->g = 1;
                if (!v->rampLeft) v->g = v->stopAfter ? 0 : 1;
            }
            s = v->src[v->pos] * v->g;
        }
        o[2 * k] = (short)(s * v->panL); o[2 * k + 1] = (short)(s * v->panR);
        v->pos++;
    }
    if (v->hdr[i].dwFlags & WHDR_PREPARED) waveOutUnprepareHeader(v->h, &v->hdr[i], sizeof(WAVEHDR));
    memset(&v->hdr[i], 0, sizeof(WAVEHDR));
    v->hdr[i].lpData = (LPSTR)o; v->hdr[i].dwBufferLength = n * 4;
    waveOutPrepareHeader(v->h, &v->hdr[i], sizeof(WAVEHDR));
    waveOutWrite(v->h, &v->hdr[i], sizeof(WAVEHDR));
    return 1;
}
static void pump1(V *v)
{
    int i;
    if (!v->active) return;
    for (i = 0; i < NQ; i++) {
        WAVEHDR *h = &v->hdr[i];
        if (!(h->dwFlags & WHDR_PREPARED) || (h->dwFlags & WHDR_DONE)) if (!fill(v, i)) break;
    }
}
static DWORD WINAPI pump(LPVOID p)
{
    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_TIME_CRITICAL);
    for (;;) {
        int i;
        EnterCriticalSection(&cs);
        for (i = 0; i < nv; i++) pump1(&vc[i]);
        LeaveCriticalSection(&cs);
        Sleep(1);
    }
    return 0;
}
/* start v at source frame `from`: zero frames of silence-gain first, then a ramp of fade frames to 1 (0: at once) */
static void vstart(V *v, const short *src, int from, int zero, int fade, double pl, double pr)
{
    int i;
    vstop(v);
    v->src = src; v->pos = v->base = from < 0 ? 0 : from; v->end = SR * SECS;
    v->panL = pl; v->panR = pr; v->stopAfter = 0; v->holdLeft = 0;
    v->zeroLeft = zero > 0 ? zero : 0;                  /* frames played at gain 0 before the ramp starts */
    if (fade > 0) { v->g = 0; v->rampLeft = fade; v->gStep = 1.0 / fade; }
    else { v->g = 1; v->rampLeft = 0; }
    v->active = 1;
    for (i = 0; i < NQ; i++) fill(v, i);
}
static int played(V *v) { MMTIME t; t.wType = TIME_SAMPLES; waveOutGetPosition(v->h, &t, sizeof t); return v->base + (int)t.u.sample; }

/* the swap: returns B. fadeMs: crossfade length; LbMs: B's start latency */
static V *swapTo(V *a, V *b, int fadeMs, double LbMs, double pl, double pr, double *callMs, int *slack)
{
    double t = now(), dt;
    int F, S, zero, fadeA, fadeB, p, hold;
    EnterCriticalSection(&cs);
    p = played(a);
    F = a->pos;                                    /* A's first unqueued frame: A's ramp can start there at the earliest */
    hold = (int)(p + LbMs * a->rate / 1000.0 + 0.5) - F;   /* B cannot sound before Lb: A holds until then */
    if (hold < 0) hold = 0;
    F += hold;
    dt = (F - p) * 1000.0 / a->rate;               /* ms until A plays F (>= Lb) */
    fadeA = a->rate * fadeMs / 1000; fadeB = b->rate * fadeMs / 1000;
    zero = (int)((dt - LbMs) * b->rate / 1000.0 + 0.5);   /* B: gain 0 from Lb until dt */
    S = F - zero;                                  /* so that B plays frame F at dt */
    *slack = (int)(dt - LbMs);
    a->holdLeft = hold; a->rampLeft = fadeA > 0 ? fadeA : 1; a->gStep = -a->g / (fadeA > 0 ? fadeA : 1); a->stopAfter = 1;
    vstart(b, a->src, S, zero, fadeB, pl, pr);
    LeaveCriticalSection(&cs);
    *callMs = now() - t;
    return b;
}
static double cents(double c) { return pow(2.0, c / 1200.0); }

static HWAVEOUT keep; static WAVEHDR keepHdr; static short keepBuf[SR * 2];
static void keepalive(void)
{
    keep = openh(SR, NULL);
    memset(&keepHdr, 0, sizeof keepHdr);
    keepHdr.lpData = (LPSTR)keepBuf; keepHdr.dwBufferLength = sizeof keepBuf;
    keepHdr.dwFlags = WHDR_BEGINLOOP | WHDR_ENDLOOP; keepHdr.dwLoops = 0x7FFFFFFF;
    waveOutPrepareHeader(keep, &keepHdr, sizeof keepHdr);
    waveOutWrite(keep, &keepHdr, sizeof keepHdr);
}
static short mark[SR * 3 / 100];
static void marker(void)
{
    double o; int i, n = SR * 3 / 100;
    V *m = &vc[MAXV - 1];
    for (i = 0; i < n; i++) mark[i] = (short)(30000 * sin(2 * 3.14159265358979 * 2000.0 * i / SR));
    if (!m->h) { m->h = openh(SR, &o); m->rate = SR; m->chunk = SR * CHUNK_MS / 1000; for (i = 0; i < NQ; i++) m->buf[i] = (short *)malloc(SR * 4 * 2 / 10); }
    EnterCriticalSection(&cs);
    vstart(m, mark, 0, 0, 0, 1, 1); m->end = n;
    LeaveCriticalSection(&cs);
    printf("%.1f marker\n", now());
    Sleep(400);
    EnterCriticalSection(&cs); vstop(m); LeaveCriticalSection(&cs);
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "align";
    int i, n = argc > 2 ? atoi(argv[2]) : 10, slack;
    unsigned seed = 12345;
    double o, callMs;
    QueryPerformanceFrequency(&qf); QueryPerformanceCounter(&q0);
    timeBeginPeriod(1);
    InitializeCriticalSection(&cs);
    for (i = 0; i < SR * SECS; i++) {
        sine[i] = (short)(16000 * sin(2 * 3.14159265358979 * 440.0 * i / SR));
        seed = seed * 1103515245u + 12345u;
        noise[i] = (short)((int)((seed >> 16) & 0x7FFF) - 16384);
    }
    keepalive();
    waveOutSetVolume(keep, 0xFFFFFFFF);   /* the Wave volume is device-wide and persists: set it to full */
    CreateThread(NULL, 0, pump, NULL, 0, NULL);
    Sleep(300);
    marker();
    if (!strcmp(mode, "align")) {
        /* A: noise, left only. B: hard start from A's played position (no lead), right only. */
        nv = 2;
        for (i = 0; i < n; i++) {
            V *a = cached(SR, NULL, &o), *b = cached(SR + 1, a, &o);   /* +1 Hz: a second handle (same pitch to 0.08 cents) */
            int p;
            EnterCriticalSection(&cs); vstart(a, noise, SR * (i % 4), 0, 0, 1, 0); LeaveCriticalSection(&cs);
            Sleep(250 + (i * 37) % 200);
            EnterCriticalSection(&cs);
            p = played(a);
            vstart(b, noise, p, 0, 0, 0, 1);
            LeaveCriticalSection(&cs);
            printf("%.1f align trial %d pos %d queuedA %d\n", now(), i, p, a->pos - p);
            Sleep(300);
            EnterCriticalSection(&cs); vstop(a); vstop(b); LeaveCriticalSection(&cs);
            Sleep(300);
        }
    } else if (!strcmp(mode, "xfade")) {
        double semis = argc > 3 ? atof(argv[3]) : 0, Lb = argc > 6 ? atof(argv[6]) : 0;
        int fadeMs = argc > 4 ? atoi(argv[4]) : 10, split = argc > 5 ? atoi(argv[5]) : 0;
        const short *src = split ? noise : sine;
        nv = 4;
        for (i = 0; i < n; i++) {
            V *a = cached(SR, NULL, &o), *b = cached((int)(SR * pow(2.0, semis / 12.0) + 0.5) + (semis == 0), a, &o);
            EnterCriticalSection(&cs); vstart(a, src, 0, 0, 0, 1, split ? 0 : 1); LeaveCriticalSection(&cs);
            Sleep(500 + (i * 13) % 40);
            b = swapTo(a, b, fadeMs, Lb, split ? 0 : 1, 1, &callMs, &slack);
            printf("%.1f swap trial %d call %.2f ms slack %d ms semis %.2f fade %d\n", now(), i, callMs, slack, semis, fadeMs);
            Sleep(500);
            EnterCriticalSection(&cs); vstop(b); vstop(a); LeaveCriticalSection(&cs);
            Sleep(300);
        }
    } else if (!strcmp(mode, "glide")) {
        double semis = argc > 3 ? atof(argv[3]) : 7, ms = argc > 4 ? atof(argv[4]) : 100, Lb = argc > 7 ? atof(argv[7]) : 0;
        int steps = argc > 5 ? atoi(argv[5]) : 4, fadeMs = argc > 6 ? atoi(argv[6]) : 10, s;
        nv = 8;
        for (i = 0; i < n; i++) {
            V *a = cached(SR, NULL, &o), *b;
            for (s = 1; s <= steps; s++) cached((int)(SR * pow(2.0, semis * s / steps / 12.0) + 0.5), a, &o);
            EnterCriticalSection(&cs); vstart(a, sine, 0, 0, 0, 1, 1); LeaveCriticalSection(&cs);
            Sleep(500);
            printf("%.1f glide start trial %d\n", now(), i);
            for (s = 1; s <= steps; s++) {
                double t = now();
                b = cached((int)(SR * pow(2.0, semis * s / steps / 12.0) + 0.5), a, &o);
                a = swapTo(a, b, fadeMs, Lb, 1, 1, &callMs, &slack);
                printf("%.1f glide step %d call %.2f slack %d\n", now(), s, callMs, slack);
                if (s < steps) { double w = ms / steps - (now() - t); if (w > 0) Sleep((DWORD)w); }
            }
            Sleep(600);
            EnterCriticalSection(&cs); for (s = 0; s < nv; s++) vstop(&vc[s]); LeaveCriticalSection(&cs);
            Sleep(300);
        }
    } else if (!strcmp(mode, "wow") || !strcmp(mode, "bend")) {
        int isBend = !strcmp(mode, "bend"), opens = 0, swaps = 0, lastRate = SR;
        double depth = argc > 3 ? atof(argv[3]) : 6, hz = argc > 4 ? atof(argv[4]) : 0.6, stepMs = argc > 5 ? atof(argv[5]) : 40;
        double q = argc > 6 ? atof(argv[6]) : 1, Lb = argc > 9 ? atof(argv[9]) : 0, t0, maxOpen = 0, sumOpen = 0;
        int fadeMs = argc > 8 ? atoi(argv[8]) : 10;
        V *a, *b;
        nv = argc > 7 ? atoi(argv[7]) : 4;
        a = cached(SR, NULL, &o);
        EnterCriticalSection(&cs); vstart(a, sine, 0, 0, 0, 1, 1); LeaveCriticalSection(&cs);
        Sleep(300);
        t0 = now();
        printf("%.1f %s start\n", t0, mode);
        while (now() - t0 < n * 1000.0) {
            double t = now(), ph = (t - t0) / 1000.0 * hz, c;
            int rate;
            if (isBend) { double f = ph - floor(ph); c = depth * (f < 0.5 ? 4 * f - 1 : 3 - 4 * f); }
            else c = depth * sin(2 * 3.14159265358979 * ph);
            c = q * floor(c / q + 0.5);
            rate = (int)(SR * cents(c) + 0.5);
            if (rate != lastRate) {
                b = cached(rate, a, &o);
                if (!b) { printf("cache full\n"); break; }
                if (o > 0) { opens++; sumOpen += o; if (o > maxOpen) maxOpen = o; }
                a = swapTo(a, b, fadeMs, Lb, 1, 1, &callMs, &slack);
                swaps++; lastRate = rate;
                printf("%.1f step cents %.1f rate %d open %.2f call %.2f slack %d\n", now(), c, rate, o, callMs, slack);
            }
            { double w = stepMs - (now() - t); if (w > 0) Sleep((DWORD)w); }
        }
        printf("%.1f %s end swaps %d opens %d open mean %.2f max %.2f\n", now(), mode, swaps, opens, opens ? sumOpen / opens : 0, maxOpen);
        Sleep(300);
        EnterCriticalSection(&cs); for (i = 0; i < nv; i++) vstop(&vc[i]); LeaveCriticalSection(&cs);
    }
    marker();
    fflush(stdout);
    timeEndPeriod(1);
    ExitProcess(0);
    return 0;
}
