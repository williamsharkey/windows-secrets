/* probe.c - lab only: start the donor programs, then dump the window tree to C:\B3\SPY.TXT */
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
    fprintf(f, "%*s%04X id=%d cls=%s txt=\"%s\" r=%d,%d,%d,%d st=%08lX vis=%d mod=%s own=%04X\n", depth * 2, "",
            (unsigned)h, GetWindowWord(h, GWW_ID), cls, txt, r.left, r.top, r.right, r.bottom,
            GetWindowLong(h, GWL_STYLE), IsWindowVisible(h), mod, (unsigned)GetWindow(h, GW_OWNER));
}
BOOL FAR PASCAL __export Kid(HWND h, LPARAM lp)
{
    if (GetParent(h) != (HWND)LOWORD(lp)) return TRUE;
    dump(h);
    depth++;
    { FARPROC p = MakeProcInstance((FARPROC)Kid, (HINSTANCE)HIWORD(lp)); EnumChildWindows(h, (WNDENUMPROC)p, MAKELPARAM(h, HIWORD(lp))); FreeProcInstance(p); }
    depth--;
    return TRUE;
}
void Pump(int ms)
{
    DWORD end = GetTickCount() + ms;
    MSG m;
    while ((long)(GetTickCount() - end) < 0) {
        while (PeekMessage(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessage(&m); }
        Yield();
    }
}
int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cl, int show)
{
    HWND h;
    FARPROC p;
    UINT r1, r2;
    r1 = WinExec("WINFILE.EXE", SW_SHOWNORMAL);
    Pump(3000);
    r2 = WinExec("CONTROL.EXE MAIN.CPL Mouse", SW_SHOWNORMAL);
    Pump(4000);
    f = fopen("C:\\B3\\SPY.TXT", "w");
    if (!f) return 1;
    fprintf(f, "winexec winfile=%u control=%u\n", r1, r2);
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
