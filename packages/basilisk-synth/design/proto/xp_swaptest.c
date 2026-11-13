/* PRESET ENGINE 2, measurements T2-T5 on XP (design/PRESET-ENGINE-2.md section 12).
   A stand-alone waveOut test. It does what srhook would do for a window, a handle swap, a glide, wow, live bend and
   grains, on synthetic sources it makes itself (no Microsoft audio). QEMU's wav audiodev records the result; the host
   script design/proto/xp_analyze.py measures it.

   Build: i686-w64-mingw32-gcc -O2 -o xp_swaptest.exe xp_swaptest.c -lwinmm
   Run (in XP):  xp_swaptest <mode> [args]   (modes below; every mode logs one line per event to stdout)

   Every mode keeps a silent looping stream open (as synth.exe does), so the wav audiodev writes continuously and
   time in the recording is the guest's audio clock. Each test starts with a 30 ms full-scale 2 kHz marker on its
   own handle, so the analysis can find it. */
#include <windows.h>
#include <mmsystem.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define SR 22050
#define SECS 12
static short sine[SR * SECS], noise[SR * SECS];
static LARGE_INTEGER qf, q0;
static double now(void) { LARGE_INTEGER t; QueryPerformanceCounter(&t); return (t.QuadPart - q0.QuadPart) * 1000.0 / qf.QuadPart; }

typedef struct { HWAVEOUT h; int rate; WAVEHDR hdr[2]; int nhdr; int base; double used; short *tmp; } V;
#define MAXV 64
static V vc[MAXV];
static int nv;

static HWAVEOUT openh(int rate, int ch, double *ms)
{
    WAVEFORMATEX f;
    HWAVEOUT h = 0;
    double t = now();
    memset(&f, 0, sizeof f);
    f.wFormatTag = WAVE_FORMAT_PCM; f.nChannels = (WORD)ch; f.nSamplesPerSec = rate; f.wBitsPerSample = 16;
    f.nBlockAlign = (WORD)(2 * ch); f.nAvgBytesPerSec = rate * f.nBlockAlign;
    if (waveOutOpen(&h, 0, &f, 0, 0, CALLBACK_NULL) != MMSYSERR_NOERROR) h = 0;
    if (ms) *ms = now() - t;
    return h;
}
static void unprep(V *v)
{
    int i;
    for (i = 0; i < v->nhdr; i++) waveOutUnprepareHeader(v->h, &v->hdr[i], sizeof(WAVEHDR));
    v->nhdr = 0;
}
static void vstop(V *v) { waveOutReset(v->h); unprep(v); }
/* write src[from, to) to v; fadeFrames > 0: the first frames get a baked linear fade-in (a copy) */
static void vplay(V *v, const short *src, int from, int to, int fadeFrames)
{
    int k = 0;
    vstop(v);
    v->base = from;
    if (fadeFrames > 0) {
        int i, n = fadeFrames < to - from ? fadeFrames : to - from;
        if (!v->tmp) v->tmp = (short *)malloc(SR * 2);
        for (i = 0; i < n; i++) v->tmp[i] = (short)(src[from + i] * (i + 0.5) / n);
        memset(&v->hdr[0], 0, sizeof(WAVEHDR));
        v->hdr[0].lpData = (LPSTR)v->tmp; v->hdr[0].dwBufferLength = n * 2;
        waveOutPrepareHeader(v->h, &v->hdr[0], sizeof(WAVEHDR));
        waveOutWrite(v->h, &v->hdr[0], sizeof(WAVEHDR));
        from += n; k = 1;
    }
    if (to > from) {
        memset(&v->hdr[k], 0, sizeof(WAVEHDR));
        v->hdr[k].lpData = (LPSTR)(src + from); v->hdr[k].dwBufferLength = (to - from) * 2;
        waveOutPrepareHeader(v->h, &v->hdr[k], sizeof(WAVEHDR));
        waveOutWrite(v->h, &v->hdr[k], sizeof(WAVEHDR));
        k++;
    }
    v->nhdr = k;
}
static V *cached(int rate, double *openMs)   /* a handle at this rate: from the cache, or opened (LRU, max nv) */
{
    int i, lru = -1;
    *openMs = 0;
    for (i = 0; i < nv; i++) if (vc[i].h && vc[i].rate == rate) { vc[i].used = now(); return &vc[i]; }
    for (i = 0; i < nv; i++) if (!vc[i].h) { lru = i; break; }
    if (lru < 0) return NULL;
    vc[lru].h = openh(rate, 1, openMs); vc[lru].rate = rate; vc[lru].nhdr = 0; vc[lru].used = now();
    return &vc[lru];
}
static V *cachedLru(int rate, V *keep, double *openMs)
{
    int i, lru = -1;
    V *v = cached(rate, openMs);
    if (v) return v;
    for (i = 0; i < nv; i++) if (&vc[i] != keep && (lru < 0 || vc[i].used < vc[lru].used)) lru = i;
    vstop(&vc[lru]); waveOutClose(vc[lru].h); vc[lru].h = 0;
    return cached(rate, openMs);
}
static void vol(V *v, int l, int r) { waveOutSetVolume(v->h, (DWORD)((r << 16) | l)); }
static int posOf(V *v)
{
    MMTIME t;
    t.wType = TIME_SAMPLES;
    waveOutGetPosition(v->h, &t, sizeof t);
    return v->base + (int)t.u.sample;
}

/* the swap of design 5.3. method: 0 hard (write B, reset A), 1 two 5 ms volume steps, 2 baked 10 ms fade-in on B
   plus A's two volume steps, 3 four 5 ms steps (20 ms). Returns B. */
static double leadMs = 0;
static V *swapTo(V *a, V *b, const short *src, int method, double *callMs, int *fromOut)
{
    double t = now();
    int p = posOf(a);
    int from = p + (int)(leadMs * a->rate / 1000.0 + 0.5);
    int steps = method == 3 ? 4 : method == 0 ? 0 : 2, i;
    if (from >= SR * SECS - SR / 10) from = SR * SECS - SR / 10;
    if (steps) vol(b, 0, 0); else vol(b, 0xFFFF, 0xFFFF);
    vplay(b, src, from, SR * SECS, method == 2 ? SR / 100 : 0);
    if (method == 2) vol(b, 0xFFFF, 0xFFFF);
    for (i = 1; i <= steps; i++) {
        int g = 0xFFFF * i / steps;
        if (method != 2) vol(b, g, g);
        vol(a, 0xFFFF - g, 0xFFFF - g);
        if (i < steps) Sleep(5);
    }
    vstop(a);
    vol(a, 0xFFFF, 0xFFFF);
    *callMs = now() - t;
    *fromOut = from;
    return b;
}
static double cents(double c) { return pow(2.0, c / 1200.0); }

static HWAVEOUT keep;
static WAVEHDR keepHdr;
static short keepBuf[SR];
static void keepalive(void)
{
    keep = openh(SR, 1, NULL);
    memset(&keepHdr, 0, sizeof keepHdr);
    keepHdr.lpData = (LPSTR)keepBuf; keepHdr.dwBufferLength = sizeof keepBuf;
    keepHdr.dwFlags = WHDR_BEGINLOOP | WHDR_ENDLOOP; keepHdr.dwLoops = 0x7FFFFFFF;
    waveOutPrepareHeader(keep, &keepHdr, sizeof keepHdr);
    waveOutWrite(keep, &keepHdr, sizeof keepHdr);
}
static short mark[SR * 3 / 100];
static void marker(void)
{
    static V m;
    int i, n = SR * 3 / 100;
    for (i = 0; i < n; i++) mark[i] = (short)(30000 * sin(2 * 3.14159265358979 * 2000.0 * i / SR));
    if (!m.h) m.h = openh(SR, 1, NULL);
    vplay(&m, mark, 0, n, 0);
    printf("%.1f marker\n", now());
    Sleep(400);
}

int main(int argc, char **argv)
{
    const char *mode = argc > 1 ? argv[1] : "open";
    int i, n = argc > 2 ? atoi(argv[2]) : 10;
    unsigned seed = 12345;
    QueryPerformanceFrequency(&qf); QueryPerformanceCounter(&q0);
    timeBeginPeriod(1);
    SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_TIME_CRITICAL);
    for (i = 0; i < SR * SECS; i++) {
        sine[i] = (short)(16000 * sin(2 * 3.14159265358979 * 440.0 * i / SR));
        seed = seed * 1103515245u + 12345u;
        noise[i] = (short)((int)((seed >> 16) & 0x7FFF) - 16384);
    }
    if (strcmp(mode, "tone")) { keepalive(); Sleep(300); marker(); }
    nv = MAXV;
    if (!strcmp(mode, "open")) {
        /* open times: cold, warm (same rate again), and with k handles already open */
        int rates[] = {22050, 23361, 24750, 26222, 33037, 44100, 11025, 16000, 21400, 29433};
        double ms;
        HWAVEOUT h[48];
        for (i = 0; i < 10; i++) { HWAVEOUT x = openh(rates[i], 1, &ms); printf("open %d cold %.2f ms\n", rates[i], ms); waveOutClose(x); }
        for (i = 0; i < 10; i++) { HWAVEOUT x = openh(rates[i], 1, &ms); printf("open %d again %.2f ms\n", rates[i], ms); waveOutClose(x); }
        for (i = 0; i < 48; i++) { h[i] = openh(22050 + 37 * i, 1, &ms); printf("open with %d open %.2f ms %s\n", i, ms, h[i] ? "" : "FAILED"); }
        for (i = 0; i < 48; i++) if (h[i]) waveOutClose(h[i]);
    } else if (!strcmp(mode, "align")) {
        /* n trials: A plays noise on the left only; B starts at A's position (+ lead) on the right only. The analysis
           cross-correlates L and R: the lag is B's start error. */
        double callMs; int from;
        leadMs = argc > 3 ? atof(argv[3]) : 0;
        nv = 2;
        for (i = 0; i < n; i++) {
            double o; V *a = cached(SR, &o), *b;
            vc[1].h = vc[1].h ? vc[1].h : openh(SR, 1, &o); vc[1].rate = SR; b = &vc[1];
            vol(a, 0xFFFF, 0); vplay(a, noise, SR * (i % 4), SR * SECS, 0);
            Sleep(250 + (i * 37) % 200);
            {   /* hard start of B, full volume, the other channel */
                double t = now();
                int p = posOf(a);
                from = p + (int)(leadMs * a->rate / 1000.0 + 0.5);
                vol(b, 0, 0xFFFF);
                vplay(b, noise, from, SR * SECS, 0);
                callMs = now() - t;
            }
            printf("%.1f align trial %d pos %d from %d call %.2f ms\n", now(), i, from - (int)(leadMs * SR / 1000.0 + 0.5), from, callMs);
            Sleep(300);
            vstop(a); vstop(b);
            Sleep(300);
        }
    } else if (!strcmp(mode, "xfade")) {
        /* sine 440: A plays 500 ms, swaps to B at ratio r with method m, B plays 500 ms */
        int method = argc > 3 ? atoi(argv[3]) : 1;
        double semis = argc > 4 ? atof(argv[4]) : 0;
        double callMs; int from;
        leadMs = argc > 5 ? atof(argv[5]) : 0;
        nv = 4;
        for (i = 0; i < n; i++) {
            double o; V *a = cached(SR, &o), *b = cached((int)(SR * pow(2.0, semis / 12.0) + 0.5), &o);
            vol(a, 0xFFFF, 0xFFFF); vplay(a, sine, 0, SR * SECS, 0);
            Sleep(500 + (i * 13) % 40);
            printf("%.1f swap start trial %d\n", now(), i);
            b = swapTo(a, b, sine, method, &callMs, &from);
            printf("%.1f swap done trial %d from %d call %.2f ms method %d semis %.2f\n", now(), i, from, callMs, method, semis);
            Sleep(500);
            vstop(b);
            Sleep(300);
        }
    } else if (!strcmp(mode, "glide")) {
        /* a staircase glide: semis over ms in steps; n trials */
        double semis = argc > 3 ? atof(argv[3]) : 7, ms = argc > 4 ? atof(argv[4]) : 100;
        int steps = argc > 5 ? atoi(argv[5]) : 4, method = argc > 6 ? atoi(argv[6]) : 1, s;
        double callMs; int from;
        leadMs = argc > 7 ? atof(argv[7]) : 0;
        nv = 8;
        for (i = 0; i < n; i++) {
            double o; V *a = cached(SR, &o), *b;
            for (s = 1; s <= steps; s++) cached((int)(SR * pow(2.0, semis * s / steps / 12.0) + 0.5), &o);   /* warm the cache */
            vol(a, 0xFFFF, 0xFFFF); vplay(a, sine, 0, SR * SECS, 0);
            Sleep(500);
            printf("%.1f glide start trial %d\n", now(), i);
            for (s = 1; s <= steps; s++) {
                double t = now();
                b = cached((int)(SR * pow(2.0, semis * s / steps / 12.0) + 0.5), &o);
                a = swapTo(a, b, sine, method, &callMs, &from);
                printf("%.1f glide step %d call %.2f ms\n", now(), s, callMs);
                if (s < steps) { double w = ms / steps - (now() - t); if (w > 0) Sleep((DWORD)w); }
            }
            Sleep(600);
            vstop(a);
            Sleep(300);
        }
    } else if (!strcmp(mode, "wow") || !strcmp(mode, "bend")) {
        /* wow: depth cents at rate Hz, one swap every stepMs, quantized to q cents, LRU cache of nv handles.
           bend: a triangle of +-depth cents at rate Hz (a live pitch bend), the same mechanism. */
        int isBend = !strcmp(mode, "bend");
        double depth = argc > 3 ? atof(argv[3]) : 6, hz = argc > 4 ? atof(argv[4]) : 0.6, stepMs = argc > 5 ? atof(argv[5]) : 40;
        double q = argc > 6 ? atof(argv[6]) : 1, secs = n;
        double callMs, o, t0, maxOpen = 0, sumOpen = 0; int from, opens = 0, swaps = 0, lastRate = SR;
        V *a, *b;
        leadMs = argc > 8 ? atof(argv[8]) : 0;
        nv = argc > 7 ? atoi(argv[7]) : 4;
        a = cached(SR, &o);
        vol(a, 0xFFFF, 0xFFFF); vplay(a, sine, 0, SR * SECS, 0);
        Sleep(300);
        t0 = now();
        printf("%.1f %s start\n", t0, mode);
        while (now() - t0 < secs * 1000) {
            double t = now(), ph = (t - t0) / 1000.0 * hz, c;
            if (isBend) { double f = ph - floor(ph); c = depth * (f < 0.5 ? 4 * f - 1 : 3 - 4 * f); }
            else c = depth * sin(2 * 3.14159265358979 * ph);
            c = q * floor(c / q + 0.5);
            {
                int rate = (int)(SR * cents(c) + 0.5);
                if (rate != lastRate) {
                    b = cachedLru(rate, a, &o);
                    if (o > 0) { opens++; sumOpen += o; if (o > maxOpen) maxOpen = o; }
                    a = swapTo(a, b, sine, 1, &callMs, &from);
                    swaps++; lastRate = rate;
                    printf("%.1f step cents %.1f rate %d open %.2f call %.2f\n", now(), c, rate, o, callMs);
                }
            }
            { double w = stepMs - (now() - t); if (w > 0) Sleep((DWORD)w); }
        }
        printf("%.1f %s end swaps %d opens %d open mean %.2f max %.2f\n", now(), mode, swaps, opens, opens ? sumOpen / opens : 0, maxOpen);
        Sleep(300);
        vstop(a);
    } else if (!strcmp(mode, "grain")) {
        /* T5: n grains, one every intervalMs, sizeMs long (baked Hann window), round-robin over streams handles,
           rates from a set of 4 (pitch spread). The guest logs the write time vs the target. */
        double interval = argc > 3 ? atof(argv[3]) : 50, size = argc > 4 ? atof(argv[4]) : 30;
        int streams = argc > 5 ? atoi(argv[5]) : 4, k, len = (int)(size * SR / 1000);
        static short g[SR];
        double t0, o, worst = 0, sum = 0, sum2 = 0;
        for (k = 0; k < len; k++) g[k] = (short)(sine[k] * 0.5 * (1 - cos(2 * 3.14159265358979 * k / (len - 1))));
        nv = streams;
        for (k = 0; k < streams; k++) cached(SR + 1000 * (k % 4), &o);
        t0 = now() + 50;
        for (i = 0; i < n; i++) {
            double target = t0 + i * interval, late;
            V *v = &vc[i % streams];
            while (now() < target) Sleep(1);
            late = now() - target;
            vplay(v, g, 0, len, 0);
            sum += late; sum2 += late * late; if (late > worst) worst = late;
            printf("%.2f grain %d late %.2f\n", now(), i, late);
        }
        printf("grain write lateness mean %.2f sd %.2f max %.2f ms\n", sum / n, sqrt(sum2 / n - (sum / n) * (sum / n)), worst);
        Sleep(300);
    } else if (!strcmp(mode, "mix")) {
        /* T4: k handles playing (looped quiet sines at different rates) for n seconds; the guest's idle share and
           the process times. A reference 440 Hz stays on one handle so the analysis can look for dropouts. */
        int k, cnt = argc > 3 ? atoi(argv[3]) : 16;
        static V ref;
        FILETIME i0, k0, u0, i1, k1, u1;
        ULONGLONG di, dk, du;
        double o;
        nv = 64;
        for (k = 0; k < cnt; k++) {
            V *v = &vc[k];
            v->h = openh(SR + 211 * k, 1, &o); v->rate = SR + 211 * k;
            if (!v->h) { printf("open %d failed\n", k); continue; }
            vol(v, 0x0400, 0x0400);
            memset(&v->hdr[0], 0, sizeof(WAVEHDR));
            v->hdr[0].lpData = (LPSTR)(sine); v->hdr[0].dwBufferLength = SR * 2;
            v->hdr[0].dwFlags = WHDR_BEGINLOOP | WHDR_ENDLOOP; v->hdr[0].dwLoops = 1000;
            waveOutPrepareHeader(v->h, &v->hdr[0], sizeof(WAVEHDR));
            waveOutWrite(v->h, &v->hdr[0], sizeof(WAVEHDR));
            v->nhdr = 1;
        }
        ref.h = openh(SR, 1, &o); vplay(&ref, sine, 0, SR * SECS, 0);
        Sleep(500);
        GetSystemTimes(&i0, &k0, &u0);
        Sleep(n * 1000);
        GetSystemTimes(&i1, &k1, &u1);
#define FT(x) (((ULONGLONG)(x).dwHighDateTime << 32) | (x).dwLowDateTime)
        di = FT(i1) - FT(i0); dk = FT(k1) - FT(k0); du = FT(u1) - FT(u0);
        printf("mix %d handles: idle %.1f %% kernel(incl idle) %.1f %% user %.1f %%\n", cnt, 100.0 * di / (dk + du), 100.0 * dk / (dk + du), 100.0 * du / (dk + du));
        vstop(&ref);
        for (k = 0; k < cnt; k++) if (vc[k].h) { vstop(&vc[k]); waveOutClose(vc[k].h); }
    } else if (!strcmp(mode, "tone")) {
        /* volume scope: tone <secs> <hz> <l> <r> <delay_ms> [setLaterMs l2 r2]: one handle, its volume set, a sine */
        static short t[SR * SECS];
        double hz = argc > 3 ? atof(argv[3]) : 440;
        int l = argc > 4 ? atoi(argv[4]) : 0xFFFF, r = argc > 5 ? atoi(argv[5]) : 0xFFFF, d = argc > 6 ? atoi(argv[6]) : 0;
        int later = argc > 7 ? atoi(argv[7]) : -1, l2 = argc > 8 ? atoi(argv[8]) : 0, r2 = argc > 9 ? atoi(argv[9]) : 0;
        double o; V *a;
        nv = 1;
        for (i = 0; i < SR * SECS; i++) t[i] = (short)(12000 * sin(2 * 3.14159265358979 * hz * i / SR));
        Sleep(d);
        a = cached(SR, &o);
        vol(a, l, r);
        { DWORD v = 0; waveOutGetVolume(a->h, &v); printf("%.1f tone %g Hz vol set %04x %04x read %08lx\n", now(), hz, l, r, (unsigned long)v); }
        vplay(a, t, 0, SR * n, 0);
        if (later >= 0) { Sleep(later); vol(a, l2, r2); printf("%.1f tone vol now %04x %04x\n", now(), l2, r2); }
        Sleep(n * 1000 - (later > 0 ? later : 0));
        vstop(a);
    } else if (!strcmp(mode, "window")) {
        /* T2: n windows of the noise source: [from, to) frames; the analysis finds them in the recording */
        nv = 1;
        for (i = 0; i < n; i++) {
            double o; V *a = cached(SR, &o);
            int from = 1000 + 7919 * i % (SR * 4), to = from + SR / 10 + 3301 * i % SR;
            vol(a, 0xFFFF, 0xFFFF);
            vplay(a, noise, from, to, 0);
            printf("%.1f window %d from %d to %d\n", now(), i, from, to);
            Sleep(1300);
            vstop(a);
            Sleep(200);
        }
    }
    if (strcmp(mode, "tone")) marker();
    fflush(stdout);
    timeEndPeriod(1);
    return 0;
}
