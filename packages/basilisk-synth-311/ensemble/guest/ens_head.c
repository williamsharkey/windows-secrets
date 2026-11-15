/* ENSEMBLE.EXE - SNDWAVE2000 Ensemble (design/ENSEMBLE.md), from the multitimbral experiment (design/MULTITIMBRAL-EXPERIMENT.md): one Windows 3.11, NB lanes.
   A lane is one MIDI channel with its own DNA built on its own LANE_RECS Sound Recorders, exactly as SYNTH.EXE builds
   and plays one (the recorder code is copied from guest/synth.c by mt/tools/make_mtsynth.py). No assembly, no strips:
   every recorder is hidden and stripped of what it does not need (MTHOOK.DLL, in its own task); a lane's first
   recorder keeps its wave display, shown in a grid (the Song tab's one waveform per lane).
   Host lines may carry a lane: "@<lane> <line>". Replies about a lane carry it the same way. */
#include <windows.h>
#include <mmsystem.h>
#include <toolhelp.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdarg.h>
#include <dos.h>
#include <shellapi.h>
#include "../../guest/bslink.h"

#ifndef NB_LANES
#define NB_LANES 10
#endif
#ifndef LANE_RECS
#define LANE_RECS 16   /* at most; a lane launches what its cap asks for */
#endif
#define NR 16                 /* recorders a lane may use at most (the DNA's pools); LANE_RECS of them exist */
#define NB NB_LANES
#define NALL (NR * NB)
#define NL 8
#define NS 64
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
#define SR_OPEN 12
#define SR_SAVEAS 14
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
HWND hMain;
HWND rw[NALL];
HTASK rt[NALL];
BOOL rplay[NALL];
int rlayer[NALL];
int bank;                     /* the lane a line is for */
int laneRecs = LANE_RECS;
long recRate[NALL], hostRate[NALL];
#define AR(r) (bank * NR + (r))
#define CARDLAYER(r, L) ((r) / NR * NL + (L))   /* the card keeps envelopes for every lane's layers */
BOOL assembled = FALSE, building;
int envN[8], envT[8][8], envL[8][8];
static long __far lnFrames[NB][NL];
static char __far lnSig[NB][1400];
static DWORD slowMax, nPlays;
static DWORD curId;
static int lnRel[NB_LANES];
static int lnCap[NB_LANES];   /* recorders a lane builds and plays (0: all LANE_RECS) */   /* each lane's release (env R), ms */
void (FAR PASCAL *HookActive)(BOOL);
void (FAR PASCAL *HookPending)(LPCSTR);
static int poll_host(void);
static BOOL is_playing(int r);
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
static int segCs[NL][10], nSeg[NL];
