/*  BASILISK.C  -  Claude Code for Windows for Workgroups 3.11
 *
 *  Nothing on screen is drawn by this program.  It borrows:
 *     Terminal    the console: transcript, scrollback, the cable to Claude (COM1)
 *     Clock       the face in the corner
 *     Cardfile    a card for the session's status
 *     Calculator  its display, for the bill
 *  and moves them into one window.  Then it listens on COM2 and does what
 *  Claude asks of this machine: run a DOS command, read a file, write one.
 *
 *  wcl -q -bt=windows -l=windows -ml basilisk.c
 */
#include <windows.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define EOT 4
#define SEP 0x1F

HINSTANCE hInst;
HWND hHost;                    /* our own window: invisible, owns the timer */
HWND hTerm, hText;             /* Terminal and its text pane (DC_Term) */
HWND hClock, hCardfile, hCard, hCardEdit, hCalc, hBill;
int  cid = -1;                 /* COM2 */
char rx[8192];
int  rxn;

/* a tool still running in a DOS window */
HINSTANCE runInst;
DWORD runEnd;
char runId[16];

/* ---------------------------------------------------------------- COM2 */

void Send(char type, LPCSTR a, LPCSTR b, LPCSTR c)
{
    static char sep[2] = { SEP, 0 };
    char t[2];
    if (cid < 0) return;
    t[0] = type; t[1] = 0;
    WriteComm(cid, t, 1);
    if (a) WriteComm(cid, a, lstrlen(a));
    if (b) { WriteComm(cid, sep, 1); WriteComm(cid, b, lstrlen(b)); }
    if (c) { WriteComm(cid, sep, 1); WriteComm(cid, c, lstrlen(c)); }
    t[0] = EOT;
    WriteComm(cid, t, 1);
}

/* ---------------------------------------------------------------- borrowing windows */

void Pump(int ms)
{
    DWORD end = GetTickCount() + ms;
    MSG m;
    while ((long)(GetTickCount() - end) < 0) {
        while (PeekMessage(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessage(&m); }
        Yield();
    }
}

HWND Launch(LPCSTR cmd)                 /* start a program, return its main window */
{
    HINSTANCE hi = WinExec(cmd, SW_SHOWNORMAL);
    DWORD end = GetTickCount() + 9000;
    HWND h;
    if (hi < 32) return NULL;
    while ((long)(GetTickCount() - end) < 0) {
        for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT))
            if ((HINSTANCE)GetWindowWord(h, GWW_HINSTANCE) == hi && IsWindowVisible(h) && !GetWindow(h, GW_OWNER))
                return h;
        Pump(50);
    }
    return NULL;
}

HWND Kid(HWND parent, LPCSTR cls)      /* first child of a class */
{
    HWND h;
    char c[32];
    for (h = GetWindow(parent, GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
        GetClassName(h, c, sizeof c);
        if (!lstrcmpi(c, cls)) return h;
    }
    return NULL;
}

UINT MenuId(HWND w, LPCSTR want)      /* a menu command by its words, e.g. "&Analog" */
{
    HMENU m = GetMenu(w);
    int i, j, n = m ? GetMenuItemCount(m) : 0;
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

HWND Dialog(HWND owner)                /* the dialog a program just opened */
{
    DWORD end = GetTickCount() + 4000;
    HWND h;
    char c[16];
    while ((long)(GetTickCount() - end) < 0) {
        for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
            GetClassName(h, c, sizeof c);
            if (GetWindow(h, GW_OWNER) == owner && IsWindowVisible(h) && !lstrcmp(c, "#32770")) return h;
        }
        Pump(40);
    }
    return NULL;
}

void Type(HWND e, LPCSTR text)        /* keystrokes into a field, as a person would */
{
    SetFocus(e);
    SendMessage(e, EM_SETSEL, 0, MAKELPARAM(0, 32767));
    PostMessage(e, WM_KEYDOWN, VK_DELETE, 0x00530001L);
    for (; *text; text++) { PostMessage(e, WM_CHAR, (BYTE)*text, 1L); Pump(12); }   /* a queue holds 8 */
    PostMessage(e, WM_KEYDOWN, VK_RETURN, 0x001C0001L);
    PostMessage(e, WM_KEYUP, VK_RETURN, 0xC01C0001L);
}

void CardIndex(LPCSTR menu, LPCSTR text)  /* Cardfile: Edit > Index, or Card > Add */
{
    UINT id = MenuId(hCardfile, menu);
    HWND d;
    if (!id) return;
    PostMessage(hCardfile, WM_COMMAND, id, 0L);
    if ((d = Dialog(hCardfile)) == NULL) return;
    Pump(250);
    Type(Kid(d, "Edit"), text);
    { DWORD end = GetTickCount() + 1500; while (IsWindow(d) && (long)(GetTickCount() - end) < 0) Pump(30); }
    if (IsWindow(d)) { PostMessage(d, WM_COMMAND, IDOK, MAKELPARAM(GetDlgItem(d, IDOK), BN_CLICKED)); Pump(300); }
}

void Adopt(HWND child, HWND into, int x, int y, int w, int h, long extra)
{
    long st = GetWindowLong(child, GWL_STYLE);
    st &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX);
    SetWindowLong(child, GWL_STYLE, st | WS_CHILD | WS_VISIBLE | extra);
    SetParent(child, into);
    MoveWindow(child, x, y, w, h, TRUE);
}

#define CARDH 224                     /* Cardfile's card, one more behind it, and its margin */
int PanelX, PanelW, TextW, ClientH, ClockH;

void Layout(void)                      /* Terminal on the left, the borrowed parts on the right */
{
    RECT r;
    GetClientRect(hTerm, &r);
    ClientH = r.bottom;
    TextW = 80 * 8 + GetSystemMetrics(SM_CXVSCROLL) + 4;
    PanelX = TextW + 10;
    PanelW = r.right - PanelX - 10;
    ClockH = ClientH - CARDH - 24 - 40;
    MoveWindow(hText, 0, 0, TextW, ClientH, TRUE);
}

void Assemble(void)
{
    HWND d;
    UINT id;

    hTerm = Launch("TERMINAL.EXE C:\\B3\\B3.TRM");
    hText = Kid(hTerm, "DC_Term");
    SetWindowText(hTerm, "BASILISK 3.11");
    MoveWindow(hTerm, 0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), TRUE);
    SetWindowLong(hTerm, GWL_STYLE, GetWindowLong(hTerm, GWL_STYLE) | WS_CLIPCHILDREN);
    Pump(300);
    Layout();

    hClock = Launch("CLOCK.EXE");
    if ((id = MenuId(hClock, "&Analog")) != 0) PostMessage(hClock, WM_COMMAND, id, 0L);
    Pump(200);
    SetMenu(hClock, NULL);
    Adopt(hClock, hTerm, PanelX, 10, PanelW, ClockH, WS_BORDER);

    hCardfile = Launch("CARDFILE.EXE");
    hCard = Kid(hCardfile, "Card");
    hCardEdit = Kid(hCard, "Edit");
    CardIndex("&Index...", "Esc stop  PgUp/PgDn scroll  /help");   /* the blank first card */
    CardIndex("&Add...", "BASILISK 3.11  -  this session");          /* in front: the status */
    hCardEdit = Kid(hCard, "Edit");                                  /* Cardfile made a new one */
    Adopt(hCard, hTerm, PanelX - 8, ClientH - CARDH - 4, PanelW + 16, CARDH, 0);
    ShowWindow(hCardfile, SW_HIDE);

    hCalc = Launch("CALC.EXE");
    hBill = GetDlgItem(hCalc, 414);
    Adopt(hBill, hTerm, PanelX, ClockH + 20, PanelW, 24, WS_BORDER);
    SetWindowText(hBill, "$0.00000 ");
    ShowWindow(hCalc, SW_HIDE);

    BringWindowToTop(hTerm);
    SetActiveWindow(hTerm);
    InvalidateRect(hTerm, NULL, TRUE);
}

/* ---------------------------------------------------------------- tools */

void FullPath(LPSTR out, LPCSTR p)
{
    if (p[0] && p[1] == ':') lstrcpy(out, p);
    else if (p[0] == '\\') { lstrcpy(out, "C:"); lstrcat(out, p); }
    else { lstrcpy(out, "C:\\B3\\WORK\\"); lstrcat(out, p); }
}

void ReadBack(LPCSTR id, LPCSTR path)  /* send a file's first 3500 bytes */
{
    static char buf[3600];
    OFSTRUCT of;
    HFILE f = OpenFile(path, &of, OF_READ);
    int n;
    if (f == HFILE_ERROR) { Send('O', id, "err", "file not found"); return; }
    n = _lread(f, buf, 3500);
    _lclose(f);
    if (n < 0) n = 0;
    buf[n] = 0;
    { int i; for (i = 0; i < n; i++) if (buf[i] == EOT || buf[i] == 0) buf[i] = ' '; }
    Send('O', id, "ok", buf);
}

void Run(LPCSTR id, LPCSTR cmd)
{
    OFSTRUCT of;
    HFILE f;
    char line[300];
    if (runInst) { Send('O', id, "err", "another command is still running"); return; }
    f = OpenFile("C:\\B3\\CMD.BAT", &of, OF_CREATE | OF_WRITE);
    if (strchr(cmd, '>'))               /* they chose where the output goes */
        wsprintf(line, "@echo off\r\ncd \\B3\\WORK\r\n%s\r\n", cmd);
    else
        wsprintf(line, "@echo off\r\ncd \\B3\\WORK\r\n%s > C:\\B3\\OUT.TXT\r\n", cmd);
    _lwrite(f, line, lstrlen(line));
    _lclose(f);
    OpenFile("C:\\B3\\OUT.TXT", &of, OF_DELETE);
    runInst = WinExec("C:\\B3\\CMD.BAT", SW_SHOWMINNOACTIVE);
    if (runInst < 32) { runInst = 0; Send('O', id, "err", "could not start COMMAND.COM"); return; }
    lstrcpy(runId, id);
    runEnd = GetTickCount() + 60000L;
}

void RunCheck(void)                    /* called on the timer while a command runs */
{
    if (!runInst) return;
    if (GetModuleUsage(runInst) > 0) {
        if ((long)(GetTickCount() - runEnd) < 0) return;
        Send('O', runId, "err", "still running after 60 seconds (left running)");
    } else {
        ReadBack(runId, "C:\\B3\\OUT.TXT");
    }
    runInst = 0;
    BringWindowToTop(hTerm);
}

void Write(LPCSTR id, LPCSTR path, LPCSTR body)
{
    OFSTRUCT of;
    char full[128], msg[64];
    HFILE f;
    FullPath(full, path);
    f = OpenFile(full, &of, OF_CREATE | OF_WRITE);
    if (f == HFILE_ERROR) { Send('O', id, "err", "cannot create that file"); return; }
    _lwrite(f, body, lstrlen(body));
    _lclose(f);
    wsprintf(msg, "wrote %d bytes to %s", lstrlen(body), (LPSTR)full);
    Send('O', id, "ok", msg);
}

/* ---------------------------------------------------------------- messages from the host */

void Scroll(LPSTR how)
{
    int n;
    if (!lstrcmp(how, "P-")) { SendMessage(hText, WM_VSCROLL, SB_PAGEUP, 0L); return; }
    if (!lstrcmp(how, "P+")) { SendMessage(hText, WM_VSCROLL, SB_PAGEDOWN, 0L); return; }
    n = atoi(how);
    while (n < 0) { SendMessage(hText, WM_VSCROLL, SB_LINEUP, 0L); n++; }
    while (n > 0) { SendMessage(hText, WM_VSCROLL, SB_LINEDOWN, 0L); n--; }
}

void Show(HWND w, LPCSTR text)        /* new words, painted now (its owner may be busy) */
{
    SetWindowText(w, text);
    InvalidateRect(w, NULL, TRUE);
    UpdateWindow(w);
}

void CardText(LPCSTR text)            /* the card's body is Cardfile's own edit */
{
    SendMessage(hCardEdit, EM_SETSEL, 0, MAKELPARAM(0, 32767));
    SendMessage(hCardEdit, EM_REPLACESEL, 0, (LPARAM)text);
    InvalidateRect(hCard, NULL, TRUE);
    UpdateWindow(hCard);
    InvalidateRect(hCardEdit, NULL, TRUE);
    UpdateWindow(hCardEdit);
}

void Handle(char type, LPSTR p)
{
    LPSTR a = p, b = NULL, c = NULL;
    if ((b = strchr(a, SEP)) != NULL) { *b++ = 0; if ((c = strchr(b, SEP)) != NULL) *c++ = 0; }
    switch (type) {
    case 'S': CardText(p); break;                          /* status card */
    case 'C': Show(hBill, p); break;                       /* the bill */
    case 'V': Scroll(p); break;                            /* scrollback */
    case 'R': if (b) Run(a, b); break;                     /* id, command */
    case 'G': if (b) { char full[128]; FullPath(full, b); ReadBack(a, full); } break;
    case 'W': if (b && c) Write(a, b, c); break;           /* id, path, text */
    }
}

void Poll(void)
{
    COMSTAT cs;
    int n, i;
    if (cid < 0) return;
    GetCommError(cid, &cs);
    n = ReadComm(cid, rx + rxn, sizeof rx - 1 - rxn);
    if (n < 0) { n = -n; GetCommError(cid, &cs); }
    rxn += n;
    for (;;) {
        for (i = 0; i < rxn && rx[i] != EOT; i++) ;
        if (i >= rxn) break;
        rx[i] = 0;
        Handle(rx[0], rx + 1);
        memmove(rx, rx + i + 1, rxn - i - 1);
        rxn -= i + 1;
    }
    if (rxn >= (int)sizeof rx - 1) rxn = 0;
}

long FAR PASCAL __export HostProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_TIMER) {
        Poll();
        RunCheck();
        if (hText && IsWindow(hText)) {                    /* keep Terminal's pane where we put it */
            RECT r;
            GetWindowRect(hText, &r);
            if (r.right - r.left != TextW) Layout();
        }
        return 0;
    }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProc(h, m, w, l);
}

int PASCAL WinMain(HINSTANCE hi, HINSTANCE prev, LPSTR cmdline, int show)
{
    WNDCLASS wc;
    DCB dcb;
    MSG m;
    hInst = hi;
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = HostProc;
    wc.hInstance = hi;
    wc.lpszClassName = "Basilisk";
    RegisterClass(&wc);
    hHost = CreateWindow("Basilisk", "BASILISK", WS_OVERLAPPED, 0, 0, 0, 0, NULL, NULL, hi, NULL);

    cid = OpenComm("COM2", 8192, 4096);
    if (cid >= 0 && BuildCommDCB("COM2:19200,n,8,1", &dcb) == 0) { dcb.Id = cid; SetCommState(&dcb); }
    Send('H', "basilisk", NULL, NULL);

    Assemble();
    Send('R', "assembled", NULL, NULL);
    SetTimer(hHost, 1, 30, NULL);
    while (GetMessage(&m, NULL, 0, 0)) { TranslateMessage(&m); DispatchMessage(&m); }
    if (cid >= 0) CloseComm(cid);
    return 0;
}
