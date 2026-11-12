/* B3BOOT.EXE - BASILISK 3.11 in the browser: the build, on Windows for Workgroups 3.11 in js-dos.
   Started by WIN.INI run=. Talks to the page through two files (link.h) instead of COM2:
     page -> Windows  G   the build: Notepad, pour in the source, Save As, compile with Open Watcom,
                          start BASILISK.EXE
     Windows -> page  H boot | S <step> | D done | E <error>
   Adapted from puppetry/w31/b3boot.c (the server version). */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include "link.h"

static HINSTANCE hInst;
static HWND hMain;

static void put(char type, const char *s) { LinkPut(type, s, NULL, NULL); }

static void pump(int ms)
{
    DWORD end = GetTickCount() + ms;
    MSG m;
    do {
        while (PeekMessage(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessage(&m); }
        if ((long)(GetTickCount() - end) >= 0) break;
        Yield();
    } while (1);
}

/* top-level window owned by an instance */
static HWND win_of(HINSTANCE hi, int ms)
{
    DWORD end = GetTickCount() + ms;
    do {
        HWND h;
        for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT))
            if ((HINSTANCE)GetWindowWord(h, GWW_HINSTANCE) == hi && IsWindowVisible(h) && !GetWindow(h, GW_OWNER))
                return h;
        pump(50);
    } while ((long)(GetTickCount() - end) < 0);
    return NULL;
}

/* a dialog owned by w */
static HWND dlg_of(HWND w, int ms)
{
    DWORD end = GetTickCount() + ms;
    do {
        HWND h;
        char c[32];
        for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
            GetClassName(h, c, sizeof c);
            if (GetWindow(h, GW_OWNER) == w && IsWindowVisible(h) && !strcmp(c, "#32770")) return h;
        }
        pump(40);
    } while ((long)(GetTickCount() - end) < 0);
    return NULL;
}

/* menu command id by its text (e.g. "Save &As...") anywhere in a menu bar */
static UINT menu_id(HWND w, const char *want)
{
    HMENU m = GetMenu(w);
    int i, j, n = GetMenuItemCount(m);
    char t[64];
    for (i = 0; i < n; i++) {
        HMENU s = GetSubMenu(m, i);
        int k = s ? GetMenuItemCount(s) : 0;
        for (j = 0; j < k; j++) {
            GetMenuString(s, j, t, sizeof t, MF_BYPOSITION);
            if (!lstrcmpi(t, want)) return GetMenuItemID(s, j);
        }
    }
    return 0;
}

/* ---- the window-tree dump (diagnostics) ---- */
static FILE *sf;
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
    mod[0] = 0;
    GetModuleFileName(hi, mod, sizeof mod);
    fprintf(sf, "%*s%04X id=%d cls=%s txt=\"%s\" r=%d,%d,%d,%d st=%08lX vis=%d mod=%s\n", depth * 2, "",
            (unsigned)h, GetWindowWord(h, GWW_ID), cls, txt, r.left, r.top, r.right, r.bottom,
            GetWindowLong(h, GWL_STYLE), IsWindowVisible(h), mod);
}
BOOL FAR PASCAL __export Kid(HWND h, LPARAM lp)
{
    FARPROC p;
    if (GetParent(h) != (HWND)LOWORD(lp)) return TRUE;
    dump(h);
    depth++;
    p = MakeProcInstance((FARPROC)Kid, hInst);
    EnumChildWindows(h, (WNDENUMPROC)p, MAKELPARAM(h, 0));
    FreeProcInstance(p);
    depth--;
    return TRUE;
}
static void spy(void)
{
    HWND h;
    FARPROC p;
    sf = fopen("C:\\B3\\SPY.TXT", "w");
    if (!sf) return;
    p = MakeProcInstance((FARPROC)Kid, hInst);
    for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
        if (!IsWindowVisible(h)) continue;
        depth = 0;
        dump(h);
        depth = 1;
        EnumChildWindows(h, (WNDENUMPROC)p, MAKELPARAM(h, 0));
    }
    FreeProcInstance(p);
    fclose(sf);
}

/* ---- the build ---- */
static void build(void)
{
    HINSTANCE ni, bi;
    HWND np, ed, d;
    HFILE f;
    long len;
    char huge *src;
    static char chunk[1201];
    long off;
    UINT id;
    OFSTRUCT of;

    put('S', "notepad");
    ni = WinExec("NOTEPAD.EXE", SW_SHOWNORMAL);
    np = win_of(ni, 8000);
    if (!np) { put('E', "notepad did not open"); return; }
    MoveWindow(np, 70, 40, 884, 660, TRUE);
    ed = GetWindow(np, GW_CHILD);
    pump(500);

    f = OpenFile("C:\\B3\\BASILISK.SRC", &of, OF_READ);
    if (f == HFILE_ERROR) { put('E', "no source"); return; }
    len = _llseek(f, 0, 2);
    _llseek(f, 0, 0);
    src = (char huge *)GlobalLock(GlobalAlloc(GMEM_MOVEABLE, len + 16));
    _hread(f, src, len);
    _lclose(f);
    put('S', "typing");
    /* pour it in, a screenful at a time: about three seconds */
    for (off = 0; off < len; ) {
        int n = 0;
        while (n < 1200 && off < len) chunk[n++] = src[off++];
        chunk[n] = 0;
        SendMessage(ed, EM_SETSEL, 0, MAKELPARAM(32767, 32767));
        SendMessage(ed, EM_REPLACESEL, 0, (LPARAM)(LPSTR)chunk);
        pump(110);
    }
    pump(700);

    put('S', "saving");
    id = menu_id(np, "Save &As...");
    PostMessage(np, WM_COMMAND, id, 0L);
    d = dlg_of(np, 6000);
    if (!d) { put('E', "no save dialog"); return; }
    pump(600);
    {   /* type the name the way a person would: the dialog's own loop does the rest */
        static const char name[] = "C:\\B3\\BASILISK.C";
        HWND e = GetDlgItem(d, 1152);
        int k;
        SetFocus(e);
        SendMessage(e, EM_SETSEL, 0, MAKELPARAM(0, 32767));
        PostMessage(e, WM_KEYDOWN, VK_DELETE, 0x00530001L);
        PostMessage(e, WM_KEYUP, VK_DELETE, 0xC0530001L);
        pump(60);
        for (k = 0; name[k]; k++) { PostMessage(e, WM_CHAR, (BYTE)name[k], 1L); pump(25); }
        pump(250);
        PostMessage(e, WM_KEYDOWN, VK_RETURN, 0x001C0001L);
        PostMessage(e, WM_KEYUP, VK_RETURN, 0xC01C0001L);
    }
    {
        OFSTRUCT o2;
        DWORD end = GetTickCount() + 5000;
        while (OpenFile("C:\\B3\\BASILISK.C", &o2, OF_EXIST) == HFILE_ERROR && (long)(GetTickCount() - end) < 0) pump(100);
    }
    pump(300);
    PostMessage(np, WM_CLOSE, 0, 0L);
    pump(500);

    put('S', "compiling");
    bi = WinExec("C:\\B3\\BUILD.BAT", SW_SHOWNORMAL);
    if (bi < 32) { put('E', "build did not start"); return; }
    {
        DWORD end = GetTickCount() + 120000L;
        pump(300);
        while (GetModuleUsage(bi) > 0 && (long)(GetTickCount() - end) < 0) pump(200);
    }
    if (OpenFile("C:\\B3\\BASILISK.EXE", &of, OF_EXIST) == HFILE_ERROR) { put('E', "compile failed"); return; }
    put('S', "running");
    put('D', "built");
    pump(200);
    WinExec("C:\\B3\\BASILISK.EXE", SW_SHOWNORMAL);
    PostQuitMessage(0);
}

static int building;
static void handle(char t, LPSTR p)
{
    (void)p;
    if (t == 'G' && !building) { building = 1; build(); }
}

long FAR PASCAL __export WndProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_TIMER) { LinkPoll(handle); return 0; }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProc(h, m, w, l);
}

int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cl, int show)
{
    WNDCLASS wc;
    MSG m;
    hInst = hi;
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hi;
    wc.lpszClassName = "B3Boot";
    RegisterClass(&wc);
    hMain = CreateWindow("B3Boot", "B3BOOT", WS_OVERLAPPED, 0, 0, 10, 10, NULL, NULL, hi, NULL);
    put('H', "boot");
    SetTimer(hMain, 1, 40, NULL);
    while (GetMessage(&m, NULL, 0, 0)) { TranslateMessage(&m); DispatchMessage(&m); }
    return 0;
}
