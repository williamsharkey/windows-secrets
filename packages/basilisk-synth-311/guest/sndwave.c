/* SNDWAVE.EXE - what Program Manager's SNDWAVE2000 items and a double-clicked .BSP start. SYNTH.EXE is already
   running (it is the machine) and Windows 3.1 cannot start it twice (it has more than one data segment), so this
   small program hands its command line to it (/recorders, /voices, /setup, or a preset file) and ends. */
#include <windows.h>
int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show)
{
    HWND w = FindWindow("Basilisk16", NULL);
    (void)hi; (void)hp; (void)show;
    if (!w) { MessageBox(NULL, "SNDWAVE2000 is not running.", "SNDWAVE2000", MB_OK | MB_ICONINFORMATION); return 1; }
    PostMessage(w, WM_USER + 9, (WPARAM)GlobalAddAtom(cmd && *cmd ? cmd : "/show"), 0L);
    return 0;
}
