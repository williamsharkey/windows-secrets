/* CITYPOP.EXE - Program Manager's CITYPOP DEPROGRAMMED item. SYNTH.EXE is already running; this small program asks it
   to open the album's player (SNDWAVE2000 plays the album, every part on Sound Recorder) and ends. */
#include <windows.h>
int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show)
{
    HWND w = FindWindow("Basilisk16", NULL);
    (void)hi; (void)hp; (void)cmd; (void)show;
    if (!w) { MessageBox(NULL, "SNDWAVE2000 is not running.", "CITYPOP DEPROGRAMMED", MB_OK | MB_ICONINFORMATION); return 1; }
    PostMessage(w, WM_USER + 9, (WPARAM)GlobalAddAtom("/citypop"), 0L);
    return 0;
}
