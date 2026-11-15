/* GENEPOOL.EXE - Program Manager's Gene Pool item. SYNTH.EXE is already running; this small program asks it to open
   the card table where sounds are dealt, kept, discarded and bred (every sound plays on Sound Recorder) and ends. */
#include <windows.h>
int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show)
{
    HWND w = FindWindow("Basilisk16", NULL);
    (void)hi; (void)hp; (void)cmd; (void)show;
    if (!w) { MessageBox(NULL, "SNDWAVE1993 is not running.", "Gene Pool", MB_OK | MB_ICONINFORMATION); return 1; }
    PostMessage(w, WM_USER + 9, (WPARAM)GlobalAddAtom("/genepool"), 0L);
    return 0;
}
