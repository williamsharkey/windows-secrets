/* B3BOOT.EXE - the build of BASILISK 3.11, on Windows for Workgroups 3.11 itself (host-built with Open Watcom).
   Started by WIN.INI run=.  One program for both stages; the link is picked at run time:
     server   COM2 (DOSBox-X nullmodem -> TCP)                       C:\B3\TOWIN.TXT absent
     browser  two files on C: (js-dos): TOWIN.TXT in, TOJS.TXT out    C:\B3\TOWIN.TXT present
   host -> Windows   G  the build: Notepad, pour in each source file, Save As, compile, run BASILISK.EXE
                     Y  dump the window tree to C:\B3\SPY.TXT          X cmdline  WinExec it
   Windows -> host   H boot | S <step> | D done | E <error> | O ...
   The source is two files (Notepad holds about 45 KB): BASILISK.SRC -> BASILISK.C, PARTS.SRC -> PARTS.C. */
#include <windows.h>
#include <stdio.h>
#include <string.h>

#define EOT 4
static HINSTANCE hInst;
static HWND hMain;
static int cid = -1, browser;
static char rx[4096];
static int rxn;
static long linkIn;

static void put(char type, const char *s)
{
    char b[300];
    int n = 0;
    b[n++] = type;
    while (*s && n < 296) b[n++] = *s++;
    b[n++] = EOT;
    if (browser) {
        OFSTRUCT of;
        HFILE f = OpenFile("C:\\B3\\TOJS.TXT", &of, OF_WRITE | OF_SHARE_DENY_NONE);
        if (f == HFILE_ERROR) f = OpenFile("C:\\B3\\TOJS.TXT", &of, OF_CREATE | OF_WRITE);
        if (f == HFILE_ERROR) return;
        _llseek(f, 0L, 2);
        _lwrite(f, b, n);
        _lclose(f);
    } else if (cid >= 0) WriteComm(cid, b, n);
}

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

static HWND win_of(HINSTANCE hi, int ms)  /* top-level window of an instance */
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

static HWND dlg_of(HWND w, int ms)       /* a dialog owned by w */
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

static UINT menu_id(HWND w, const char *want)
{
    HMENU m = GetMenu(w);
    int i, j, n = GetMenuItemCount(m);
    char t[64], *tab;
    for (i = 0; i < n; i++) {
        HMENU s = GetSubMenu(m, i);
        int k = s ? GetMenuItemCount(s) : 0;
        for (j = 0; j < k; j++) {
            GetMenuString(s, j, t, sizeof t, MF_BYPOSITION);
            if ((tab = strchr(t, '\t')) != NULL) *tab = 0;
            if (!lstrcmpi(t, want)) return GetMenuItemID(s, j);
        }
    }
    return 0;
}

/* ---- the window-tree dump (diagnostics) ---- */
static FILE *sf;
static void dump(HWND h, int depth)
{
    char cls[64], txt[80];
    RECT r;
    for (; h; h = GetWindow(h, GW_HWNDNEXT)) {
        GetClassName(h, cls, sizeof cls);
        GetWindowText(h, txt, sizeof txt);
        GetWindowRect(h, &r);
        fprintf(sf, "%*s%04X id=%d cls=%s txt=\"%s\" r=%d,%d,%d,%d st=%08lX vis=%d\n", depth * 2, "",
                (unsigned)h, GetWindowWord(h, GWW_ID), cls, txt, r.left, r.top, r.right, r.bottom,
                GetWindowLong(h, GWL_STYLE), IsWindowVisible(h));
        if (depth < 3) dump(GetWindow(h, GW_CHILD), depth + 1);
    }
}
static void spy(void)
{
    if ((sf = fopen("C:\\B3\\SPY.TXT", "w")) == NULL) return;
    dump(GetWindow(GetDesktopWindow(), GW_CHILD), 0);
    fclose(sf);
}

/* ---- the build ---- */
static int pour(HWND np, const char *srcName, const char *cName)   /* one file into Notepad, then Save As */
{
    HWND ed = GetWindow(np, GW_CHILD), d;
    HFILE f;
    long len, off;
    char huge *src;
    HGLOBAL g;
    static char chunk[1201];
    OFSTRUCT of;
    UINT id;

    f = OpenFile(srcName, &of, OF_READ);
    if (f == HFILE_ERROR) { put('E', "no source"); return 0; }
    len = _llseek(f, 0, 2);
    _llseek(f, 0, 0);
    g = GlobalAlloc(GMEM_MOVEABLE, len + 16);
    src = (char huge *)GlobalLock(g);
    _hread(f, src, len);
    _lclose(f);
    for (off = 0; off < len; ) {         /* a screenful at a time */
        int n = 0;
        while (n < 1200 && off < len) chunk[n++] = src[off++];
        chunk[n] = 0;
        SendMessage(ed, EM_SETSEL, 0, MAKELPARAM(32767, 32767));
        SendMessage(ed, EM_REPLACESEL, 0, (LPARAM)(LPSTR)chunk);
        pump(100);
    }
    GlobalUnlock(g);
    GlobalFree(g);
    pump(500);

    id = menu_id(np, "Save &As...");
    PostMessage(np, WM_COMMAND, id, 0L);
    d = dlg_of(np, 6000);
    if (!d) { put('E', "no save dialog"); return 0; }
    pump(400);
    {   /* type the name the way a person would: the dialog's own loop does the rest */
        HWND e = GetDlgItem(d, 1152);
        int k;
        OpenFile(cName, &of, OF_DELETE);
        SetFocus(e);
        SendMessage(e, EM_SETSEL, 0, MAKELPARAM(0, 32767));
        PostMessage(e, WM_KEYDOWN, VK_DELETE, 0x00530001L);
        PostMessage(e, WM_KEYUP, VK_DELETE, 0xC0530001L);
        pump(60);
        for (k = 0; cName[k]; k++) { PostMessage(e, WM_CHAR, (BYTE)cName[k], 1L); pump(25); }
        pump(200);
        PostMessage(e, WM_KEYDOWN, VK_RETURN, 0x001C0001L);
        PostMessage(e, WM_KEYUP, VK_RETURN, 0xC01C0001L);
    }
    {
        DWORD end = GetTickCount() + 5000;
        while (OpenFile(cName, &of, OF_EXIST) == HFILE_ERROR && (long)(GetTickCount() - end) < 0) pump(100);
    }
    pump(300);
    return 1;
}

static void build(void)
{
    HINSTANCE ni, bi;
    HWND np;
    OFSTRUCT of;

    put('S', "notepad");
    ni = WinExec("NOTEPAD.EXE", SW_SHOWNORMAL);
    np = win_of(ni, 8000);
    if (!np) { put('E', "notepad did not open"); return; }
    MoveWindow(np, 70, 40, 884, 660, TRUE);
    pump(400);
    put('S', "typing");
    if (!pour(np, "C:\\B3\\BASILISK.SRC", "C:\\B3\\BASILISK.C")) return;
    if (OpenFile("C:\\B3\\PARTS.SRC", &of, OF_EXIST) != HFILE_ERROR) {
        PostMessage(np, WM_COMMAND, menu_id(np, "&New"), 0L);
        pump(500);
        if (!pour(np, "C:\\B3\\PARTS.SRC", "C:\\B3\\PARTS.C")) return;
    }
    PostMessage(np, WM_CLOSE, 0, 0L);
    pump(400);

    put('S', "compiling");
    OpenFile("C:\\B3\\BASILISK.EXE", &of, OF_DELETE);
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
    if (cid >= 0) { CloseComm(cid); cid = -1; }   /* BASILISK.EXE opens COM2 itself */
    WinExec("C:\\B3\\BASILISK.EXE", SW_SHOWNORMAL);
    PostQuitMessage(0);
}

static int building;
static void handle(char t, char *p)
{
    char b[64];
    if (t == 'X') {
        HINSTANCE h = WinExec(p, SW_SHOWNORMAL);
        sprintf(b, "x\x1f%u", (unsigned)h);
        put('O', b);
    } else if (t == 'Y') {
        spy();
        put('O', "y\x1fok");
    } else if (t == 'G' && !building) {
        building = 1;
        build();
    } else if (t == 'Q') {
        put('O', "q\x1fbye");
        PostQuitMessage(0);
    }
}

static void poll(void)
{
    int n, i;
    if (browser) {
        OFSTRUCT of;
        HFILE f = OpenFile("C:\\B3\\TOWIN.TXT", &of, OF_READ | OF_SHARE_DENY_NONE);
        if (f == HFILE_ERROR) return;
        _llseek(f, linkIn + rxn, 0);
        n = _lread(f, rx + rxn, sizeof rx - 1 - rxn);
        _lclose(f);
        if (n <= 0) return;
    } else {
        COMSTAT cs;
        if (cid < 0) return;
        GetCommError(cid, &cs);
        n = ReadComm(cid, rx + rxn, sizeof rx - 1 - rxn);
        if (n < 0) n = -n;
    }
    rxn += n;
    for (;;) {
        static char msg[4096];
        char t;
        for (i = 0; i < rxn && rx[i] != EOT; i++) ;
        if (i >= rxn) break;
        rx[i] = 0;
        t = rx[0];
        memcpy(msg, rx + 1, i);
        memmove(rx, rx + i + 1, rxn - i - 1);
        rxn -= i + 1;
        linkIn += i + 1;
        handle(t, msg);
        if (!browser && cid < 0) return;
    }
    if (rxn >= (int)sizeof rx - 1) { linkIn += rxn; rxn = 0; }
}

long FAR PASCAL __export WndProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_TIMER) { poll(); return 0; }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProc(h, m, w, l);
}

int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cl, int show)
{
    WNDCLASS wc;
    MSG m;
    OFSTRUCT of;
    hInst = hi;
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hi;
    wc.lpszClassName = "B3Boot";
    RegisterClass(&wc);
    hMain = CreateWindow("B3Boot", "B3BOOT", WS_OVERLAPPED, 0, 0, 10, 10, NULL, NULL, hi, NULL);
    browser = OpenFile("C:\\B3\\TOWIN.TXT", &of, OF_EXIST) != HFILE_ERROR;
    if (browser) {
        HFILE f = OpenFile("C:\\B3\\TOWIN.TXT", &of, OF_READ | OF_SHARE_DENY_NONE);
        if (f != HFILE_ERROR) { linkIn = _llseek(f, 0L, 2); _lclose(f); }
    } else {
        DCB dcb;
        cid = OpenComm("COM2", 4096, 1024);
        if (cid < 0) return 1;
        if (BuildCommDCB("COM2:19200,n,8,1", &dcb) == 0) { dcb.Id = cid; SetCommState(&dcb); }
    }
    put('H', "boot");
    SetTimer(hMain, 1, 40, NULL);
    while (GetMessage(&m, NULL, 0, 0)) { TranslateMessage(&m); DispatchMessage(&m); }
    if (cid >= 0) CloseComm(cid);
    return 0;
}
