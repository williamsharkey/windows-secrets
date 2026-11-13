/* wavrec.exe DEV SECONDS OUT.WAV : record from waveIn device DEV (-1 = mapper) at 44.1 kHz s16 stereo through XP's
   own waveIn / kmixer / driver path, and write a WAV. "wavrec list" prints the waveIn devices. (RECORDING.md TR1) */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
typedef UINT MMRESULT;
typedef HANDLE HWAVEIN;
#pragma pack(push,1)
typedef struct { WORD wFormatTag, nChannels; DWORD nSamplesPerSec, nAvgBytesPerSec; WORD nBlockAlign, wBitsPerSample, cbSize; } WFX;
#pragma pack(pop)
typedef struct whdr { LPSTR lpData; DWORD dwBufferLength, dwBytesRecorded; DWORD_PTR dwUser; DWORD dwFlags, dwLoops; struct whdr *lpNext; DWORD_PTR reserved; } WHDR;
typedef struct { WORD wMid, wPid; UINT vDriverVersion; CHAR szPname[32]; DWORD dwFormats; WORD wChannels, wReserved1; } WICAPS;
typedef UINT (WINAPI *P_NUM)(void);
typedef MMRESULT (WINAPI *P_CAPS)(UINT, WICAPS *, UINT);
typedef MMRESULT (WINAPI *P_OPEN)(HWAVEIN *, UINT, const WFX *, DWORD_PTR, DWORD_PTR, DWORD);
typedef MMRESULT (WINAPI *P_HDR)(HWAVEIN, WHDR *, UINT);
typedef MMRESULT (WINAPI *P_H)(HWAVEIN);
#define NB 8
#define CHUNK (44100 * 4 / 10)
int main(int argc, char **argv)
{
    HMODULE m = LoadLibraryA("winmm.dll");
    P_NUM num = (P_NUM)GetProcAddress(m, "waveInGetNumDevs");
    P_CAPS caps = (P_CAPS)GetProcAddress(m, "waveInGetDevCapsA");
    P_OPEN op = (P_OPEN)GetProcAddress(m, "waveInOpen");
    P_HDR prep = (P_HDR)GetProcAddress(m, "waveInPrepareHeader"), add = (P_HDR)GetProcAddress(m, "waveInAddBuffer"), unprep = (P_HDR)GetProcAddress(m, "waveInUnprepareHeader");
    P_H start = (P_H)GetProcAddress(m, "waveInStart"), stop = (P_H)GetProcAddress(m, "waveInStop"), reset = (P_H)GetProcAddress(m, "waveInReset"), cls = (P_H)GetProcAddress(m, "waveInClose");
    UINT i, n = num();
    if (argc >= 3 && !strcmp(argv[1], "stat")) {
        /* a 1 kHz test tone's quality: frequency by zero crossings, glitches (jumps no sine of this level makes),
           silent runs (dropouts), peak and noise between clicks */
        FILE *fi = fopen(argv[2], "rb");
        long sz, k, n, zc = 0, glitch = 0, runs = 0, run = 0, first = -1, last = -1;
        short *d; int pk = 0;
        if (!fi) { printf("no file\n"); return 1; }
        fseek(fi, 0, SEEK_END); sz = ftell(fi); fseek(fi, 44, SEEK_SET);
        d = (short *)malloc(sz); n = (long)fread(d, 1, sz - 44, fi) / 4; fclose(fi);
        for (k = 1; k < n; k++) {
            int a = d[2 * k], b = d[2 * k - 2], dd = a - b;
            if (a > pk) pk = a;
            if (b < 0 && a >= 0) { zc++; if (first < 0) first = k; last = k; }
            if (dd > 4000 || dd < -4000) glitch++;
            if (a > -50 && a < 50) run++; else { if (run > 20) runs++; run = 0; }
        }
        printf("frames %ld, peak %d, rising zero crossings %ld -> %.3f Hz, glitches %ld, silent runs %ld\n",
               n, pk, zc, zc > 1 ? (double)(zc - 1) * 44100.0 / (last - first) : 0.0, glitch, runs);
        return 0;
    }
    if (argc < 2 || !strcmp(argv[1], "list")) {
        for (i = 0; i < n; i++) { WICAPS c; caps(i, &c, sizeof c); printf("waveIn %u: %s\n", i, c.szPname); }
        return 0;
    }
    {
        int dev = atoi(argv[1]);
        double secs = atof(argv[2]);
        DWORD want = (DWORD)(secs * 44100) * 4, got = 0, t0, first = 0;
        char *all = (char *)malloc(want + 4);
        static char bufs[NB][CHUNK];
        WHDR h[NB];
        WFX f = {1, 2, 44100, 44100 * 4, 4, 16, 0};
        HWAVEIN w;
        HANDLE ev = CreateEventA(NULL, FALSE, FALSE, NULL);
        FILE *o;
        MMRESULT r = op(&w, dev < 0 ? (UINT)-1 : (UINT)dev, &f, (DWORD_PTR)ev, 0, 0x50000 /* CALLBACK_EVENT */);
        if (r) { printf("waveInOpen failed %u\n", r); return 1; }
        for (i = 0; i < NB; i++) { memset(&h[i], 0, sizeof h[i]); h[i].lpData = bufs[i]; h[i].dwBufferLength = CHUNK; prep(w, &h[i], sizeof h[i]); add(w, &h[i], sizeof h[i]); }
        t0 = GetTickCount();
        start(w);
        while (got < want && GetTickCount() - t0 < (DWORD)(secs * 1000) + 5000) {
            WaitForSingleObject(ev, 200);
            for (i = 0; i < NB; i++) if (h[i].dwFlags & 1 /* DONE */) {
                DWORD k = h[i].dwBytesRecorded;
                if (!first && k) first = GetTickCount() - t0;
                if (got + k > want) k = want - got;
                memcpy(all + got, h[i].lpData, k); got += k;
                unprep(w, &h[i], sizeof h[i]); h[i].dwFlags = 0; h[i].dwBytesRecorded = 0;
                prep(w, &h[i], sizeof h[i]); add(w, &h[i], sizeof h[i]);
            }
        }
        stop(w); reset(w);
        for (i = 0; i < NB; i++) unprep(w, &h[i], sizeof h[i]);
        cls(w);
        o = fopen(argv[3], "wb");
        {
            DWORD hdr[11] = {0x46464952, 36 + got, 0x45564157, 0x20746d66, 16, 0x00020001, 44100, 44100 * 4, 0x00100004, 0x61746164, got};
            fwrite(hdr, 4, 11, o); fwrite(all, 1, got, o); fclose(o);
        }
        printf("recorded %lu bytes in %lu ms (first data after %lu ms)\n", got, GetTickCount() - t0, first);
    }
    return 0;
}
