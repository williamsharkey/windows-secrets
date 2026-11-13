/* the guest side of the BSYN card's host link (used by the synth program) */
#include <conio.h>
#include <i86.h>
#include "bsynth.h"
static void bs_put(WORD w) { outpw(BS_ARG, w); }
static WORD bs_get(void) { return inpw(BS_ARG); }
static BOOL bs_present(void) { return inpw(BS_MAGIC) == 0x5342; }
/* one report packet: type, then words */
static void bs_report(int type, const WORD *w, int n)
{
    int i;
    _disable();
    bs_put((WORD)((type << 8) | (n + 1)));
    for (i = 0; i < n; i++) bs_put(w[i]);
    outpw(BS_CMD, BSC_REPORT);
    _enable();
}
/* a text line to the host: packets of up to 240 characters, type 7 = more follows, type 3 = the line ends */
static void bs_text(const char FAR *s)
{
    static WORD w[130];
    int len = lstrlen(s), at = 0;
    do {
        int n = 0, i, m = len - at > 240 ? 240 : len - at;
        for (i = 0; i < m; i += 2) w[n++] = (WORD)((BYTE)s[at + i] | ((i + 1 < m ? (BYTE)s[at + i + 1] : 0) << 8));
        at += m;
        bs_report(at < len ? 7 : 3, w, n);
    } while (at < len);
}
/* next host event into w (max words); returns its word count, 0 = none */
static int bs_event(WORD *w, int max)
{
    int n, i; WORD x;
    _disable();
    outpw(BS_CMD, BSC_EVPOLL);
    n = bs_get();
    for (i = 0; i < n; i++) { x = bs_get(); if (i < max) w[i] = x; }
    _enable();
    return n;
}
static void bs_arm(HTASK task, DWORD id, DWORD hz, WORD gain)
{
    _disable();
    bs_put((WORD)task); bs_put(LOWORD(id)); bs_put(HIWORD(id)); bs_put(LOWORD(hz)); bs_put(HIWORD(hz)); bs_put(gain);
    outpw(BS_CMD, BSC_ARM);
    _enable();
}
static void bs_armstop(HTASK task, DWORD id, WORD fade_ms)
{
    _disable();
    bs_put((WORD)task); bs_put(LOWORD(id)); bs_put(HIWORD(id)); bs_put(fade_ms);
    outpw(BS_CMD, BSC_ARMSTOP);
    _enable();
}
static DWORD bs_voices(void)
{
    DWORD m;
    _disable();
    outpw(BS_CMD, BSC_VOICES); m = bs_get(); m |= (DWORD)bs_get() << 16; bs_get();
    _enable();
    return m;
}
static void bs_env(WORD a, WORD d, WORD s)
{
    _disable(); bs_put(a); bs_put(d); bs_put(s); outpw(BS_CMD, 27); _enable();
}
/* a text line to the host (DNA.md section 4), at most 250 characters */
static void bs_line(const char *s) { bs_text(s); }
