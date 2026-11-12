/* spy.c - dump the window tree of Windows 3.1 to C:\B3\SPY.TXT (diagnostic, host-built) */
#include <windows.h>
#include <stdio.h>
static FILE *f;
static int depth;
BOOL FAR PASCAL __export Kid(HWND h, LPARAM lp);
static void dump(HWND h)
{
    char cls[64], txt[80], mod[64];
    RECT r;
    HINSTANCE hi = (HINSTANCE)GetWindowWord(h, GWW_HINSTANCE);
    GetClassName(h, cls, sizeof cls);
    GetWindowText(h, txt, sizeof txt);
    GetWindowRect(h, &r);
    mod[0] = 0; GetModuleFileName(hi, mod, sizeof mod);
    fprintf(f, "%*s%04X id=%d cls=%s txt=\"%s\" r=%d,%d,%d,%d st=%08lX vis=%d mod=%s\n", depth * 2, "",
            (unsigned)h, GetWindowWord(h, GWW_ID), cls, txt, r.left, r.top, r.right, r.bottom,
            GetWindowLong(h, GWL_STYLE), IsWindowVisible(h), mod);
}
BOOL FAR PASCAL __export Kid(HWND h, LPARAM lp)
{
    if (GetParent(h) != (HWND)LOWORD(lp)) return TRUE;   /* direct children only */
    dump(h);
    depth++;
    { FARPROC p = MakeProcInstance((FARPROC)Kid, (HINSTANCE)HIWORD(lp)); EnumChildWindows(h, (WNDENUMPROC)p, MAKELPARAM(h, HIWORD(lp))); FreeProcInstance(p); }
    depth--;
    return TRUE;
}
int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cl, int show)
{
    HWND h;
    FARPROC p;
    f = fopen("C:\\B3\\SPY.TXT", "w");
    if (!f) return 1;
    p = MakeProcInstance((FARPROC)Kid, hi);
    for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
        if (!IsWindowVisible(h)) continue;
        dump(h);
        depth = 1;
        EnumChildWindows(h, (WNDENUMPROC)p, MAKELPARAM(h, hi));
        depth = 0;
    }
    FreeProcInstance(p);
    fclose(f);
    return 0;
}
