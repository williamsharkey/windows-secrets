/*  BASILISK.C  -  Claude Code for Windows for Workgroups 3.11, running in your browser
 *
 *  Nothing on screen is drawn by this program.  It borrows:
 *     Notepad     the transcript (its edit control, in Fixedsys, with its own scrollbar)
 *     Find        Notepad's own Find dialog, made into the input bar: Find What = your words,
 *                 Find Next = Send, Cancel = Stop
 *     Clock       the face in the corner
 *     Cardfile    a card for the session's status
 *     Calculator  its display, for the bill
 *  and moves them into one window.  Then it does what Claude asks of this machine: run a DOS
 *  command, read a file, write one.  The page talks to it through two files (link.h).
 *
 *  wcl -q -bt=windows -l=windows -ml basilisk.c
 */
#include <windows.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "link.h"

HINSTANCE hInst;
HWND hHost;                    /* our own window: invisible, owns the timer */
HWND hNote, hText;             /* Notepad and its edit: the transcript */
HWND hFind, hInput, hSend, hStop;
HWND hClock, hCardfile, hCard, hCardEdit, hCalc, hBill;

/* a tool still running in a DOS window */
HINSTANCE runInst;
DWORD runEnd;
char runId[16];

#define Send(t, a, b, c) LinkPut(t, a, b, c)

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
    st &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | DS_MODALFRAME);
    SetWindowLong(child, GWL_STYLE, st | WS_CHILD | WS_VISIBLE | extra);
    SetParent(child, into);
    MoveWindow(child, x, y, w, h, TRUE);
}

#define CARDH 224                     /* Cardfile's card, one more behind it, and its margin */
#define BARH 34                       /* the input bar (Notepad's Find dialog) */
int PanelX, PanelW, TextW, ClientH, ClockH;

void Layout(void)                      /* transcript and input bar on the left, borrowed parts on the right */
{
    RECT r;
    int bw;
    GetClientRect(hNote, &r);
    ClientH = r.bottom;
    TextW = 80 * 8 + GetSystemMetrics(SM_CXVSCROLL) + 6;
    PanelX = TextW + 10;
    PanelW = r.right - PanelX - 10;
    ClockH = ClientH - CARDH - 24 - 40;
    MoveWindow(hText, 0, 0, TextW, ClientH - BARH, TRUE);
    if (hFind) {
        MoveWindow(hFind, 0, ClientH - BARH, TextW, BARH, TRUE);
        bw = 64;
        MoveWindow(hInput, 6, 6, TextW - 2 * bw - 22, 22, TRUE);
        MoveWindow(hSend, TextW - 2 * bw - 10, 5, bw, 24, TRUE);
        MoveWindow(hStop, TextW - bw - 6, 5, bw, 24, TRUE);
    }
}

void FindBar(void)                     /* Notepad's own Find dialog, made into a strip along the bottom */
{
    UINT id = MenuId(hNote, "&Find...");
    HWND h;
    if (!id) return;
    PostMessage(hNote, WM_COMMAND, id, 0L);
    if ((hFind = Dialog(hNote)) == NULL) return;
    hInput = GetDlgItem(hFind, 1152);
    hSend = GetDlgItem(hFind, IDOK);
    hStop = GetDlgItem(hFind, IDCANCEL);
    for (h = GetWindow(hFind, GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT))
        if (h != hInput && h != hSend && h != hStop) ShowWindow(h, SW_HIDE);
    /* new ids: pressing them must never start a search or close the bar */
    SetWindowWord(hSend, GWW_ID, 0x7701);
    SetWindowWord(hStop, GWW_ID, 0x7702);
    SetWindowText(hSend, "Send");
    SetWindowText(hStop, "Stop");
    EnableWindow(hSend, TRUE);
    EnableWindow(hStop, FALSE);
    SendMessage(hInput, WM_SETFONT, (WPARAM)GetStockObject(SYSTEM_FIXED_FONT), 0L);
    SendMessage(hInput, EM_LIMITTEXT, 1000, 0L);
    SendMessage(hInput, WM_SETTEXT, 0, (LPARAM)(LPSTR)"");
    Adopt(hFind, hNote, 0, 0, 10, 10, 0);
}

void Assemble(void)
{
    UINT id;

    hNote = Launch("NOTEPAD.EXE");
    hText = Kid(hNote, "Edit");
    SetWindowText(hNote, "BASILISK 3.11");
    ShowWindow(hNote, SW_SHOWMAXIMIZED);
    SetWindowLong(hNote, GWL_STYLE, GetWindowLong(hNote, GWL_STYLE) | WS_CLIPCHILDREN);
    /* Notepad's frame has no background brush (its edit always covered it); now that the edit is
       narrower, give it one, or the old scrollbars stay painted where the edit used to be */
    SetClassWord(hNote, GCW_HBRBACKGROUND, (WORD)GetStockObject(WHITE_BRUSH));
    SendMessage(hText, WM_SETFONT, (WPARAM)GetStockObject(SYSTEM_FIXED_FONT), 0L);
    SendMessage(hText, EM_LIMITTEXT, 0, 0L);
    Pump(300);
    FindBar();
    Layout();

    hClock = Launch("CLOCK.EXE");
    if ((id = MenuId(hClock, "&Analog")) != 0) PostMessage(hClock, WM_COMMAND, id, 0L);
    Pump(200);
    SetMenu(hClock, NULL);
    Adopt(hClock, hNote, PanelX, 10, PanelW, ClockH, WS_BORDER);

    hCardfile = Launch("CARDFILE.EXE");
    hCard = Kid(hCardfile, "Card");
    hCardEdit = Kid(hCard, "Edit");
    CardIndex("&Index...", "Enter send  Esc stop  /help");   /* the blank first card */
    CardIndex("&Add...", "BASILISK 3.11  -  this session");  /* in front: the status */
    hCardEdit = Kid(hCard, "Edit");                          /* Cardfile made a new one */
    Adopt(hCard, hNote, PanelX - 8, ClientH - CARDH - 4, PanelW + 16, CARDH, 0);
    ShowWindow(hCardfile, SW_HIDE);

    hCalc = Launch("CALC.EXE");
    hBill = GetDlgItem(hCalc, 414);
    Adopt(hBill, hNote, PanelX, ClockH + 20, PanelW, 24, WS_BORDER);
    SetWindowText(hBill, "$0.00000 ");
    ShowWindow(hCalc, SW_HIDE);

    BringWindowToTop(hNote);
    SetActiveWindow(hNote);
    if (hInput) SetFocus(hInput);
    RedrawWindow(hNote, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN | RDW_UPDATENOW);
}

/* ---------------------------------------------------------------- the transcript */

int Visible(void)                      /* lines the transcript shows at once */
{
    static int lh;
    RECT r;
    if (!lh) {
        HDC dc = GetDC(hText);
        TEXTMETRIC tm;
        HFONT old = SelectObject(dc, GetStockObject(SYSTEM_FIXED_FONT));
        GetTextMetrics(dc, &tm);
        SelectObject(dc, old);
        ReleaseDC(hText, dc);
        lh = tm.tmHeight + tm.tmExternalLeading;
        if (lh < 8) lh = 15;
    }
    GetClientRect(hText, &r);
    return r.bottom / lh;
}

/* Windows 3.1's edit control will scroll past its last line; keep the text where a reader expects it:
   never past the end, and after new text, the newest line at the bottom */
void Settle(int toEnd)
{
    int total = (int)SendMessage(hText, EM_GETLINECOUNT, 0, 0L);
    int first = (int)SendMessage(hText, EM_GETFIRSTVISIBLELINE, 0, 0L);
    int vis = Visible(), want;
    want = total - vis;
    if (want < 0) want = 0;
    if (toEnd || first > want) SendMessage(hText, EM_LINESCROLL, 0, MAKELPARAM(want - first, 0));
}

void Append(LPCSTR text)               /* add to the end of Notepad's text, keeping it light */
{
    int n = (int)SendMessage(hText, WM_GETTEXTLENGTH, 0, 0L);
    if (n > 22000) {                   /* a 16-bit edit control holds about 30 KB: drop the oldest third */
        SendMessage(hText, EM_SETSEL, 0, MAKELPARAM(0, 8000));
        SendMessage(hText, EM_REPLACESEL, 0, (LPARAM)(LPSTR)"[...]\r\n");
        n = (int)SendMessage(hText, WM_GETTEXTLENGTH, 0, 0L);
    }
    SendMessage(hText, EM_SETSEL, 0, MAKELPARAM(n, n));
    SendMessage(hText, EM_REPLACESEL, 0, (LPARAM)text);
    Settle(1);
}

void Back(int k)                       /* take back the last k characters (a word moving to the next line) */
{
    int n = (int)SendMessage(hText, WM_GETTEXTLENGTH, 0, 0L);
    if (k > n) k = n;
    SendMessage(hText, EM_SETSEL, 0, MAKELPARAM(n - k, n));
    SendMessage(hText, EM_REPLACESEL, 0, (LPARAM)(LPSTR)"");
}

void Scroll(LPSTR how)
{
    int n, vis = Visible();
    if (!lstrcmp(how, "E")) { Settle(1); return; }
    if (!lstrcmp(how, "P-")) n = -(vis - 1);
    else if (!lstrcmp(how, "P+")) n = vis - 1;
    else n = atoi(how);
    {
        int first = (int)SendMessage(hText, EM_GETFIRSTVISIBLELINE, 0, 0L);
        int total = (int)SendMessage(hText, EM_GETLINECOUNT, 0, 0L);
        int max = total - vis;
        if (max < 0) max = 0;
        if (first + n > max) n = max - first;
        if (first + n < 0) n = -first;
        if (n) SendMessage(hText, EM_LINESCROLL, 0, MAKELPARAM(n, 0));
    }
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

void Press(HWND b)                     /* the button visibly goes down and up */
{
    SendMessage(b, BM_SETSTATE, TRUE, 0L);
    UpdateWindow(b);
    Pump(90);
    SendMessage(b, BM_SETSTATE, FALSE, 0L);
    UpdateWindow(b);
}

void Submit(void)                      /* Enter: your words leave the Find box */
{
    static char t[1100];
    /* GetWindowText can't read another program's edit control (it returns the window caption, here
       empty); asking the edit itself does */
    t[0] = 0;
    SendMessage(hInput, WM_GETTEXT, sizeof t, (LPARAM)(LPSTR)t);
    SendMessage(hInput, WM_SETTEXT, 0, (LPARAM)(LPSTR)"");
    Press(hSend);
    Send('U', t, NULL, NULL);
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
    { int i; for (i = 0; i < n; i++) if (buf[i] == EOT || buf[i] == 0 || buf[i] == SEP) buf[i] = ' '; }
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
    BringWindowToTop(hNote);
    if (hInput) SetFocus(hInput);
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

/* ---------------------------------------------------------------- messages from the page */

void Handle(char type, LPSTR p)
{
    LPSTR a = p, b = NULL, c = NULL;
    if (type == 'A') { Append(p); return; }                /* transcript text (may hold \x1f) */
    if ((b = strchr(a, SEP)) != NULL) { *b++ = 0; if ((c = strchr(b, SEP)) != NULL) *c++ = 0; }
    switch (type) {
    case 'B': Back(atoi(p)); break;                        /* take back characters */
    case 'K': SendMessage(hText, WM_SETTEXT, 0, (LPARAM)(LPSTR)""); break;   /* clear the transcript */
    case 'S': CardText(p); break;                          /* status card */
    case 'C': Show(hBill, p); break;                       /* the bill */
    case 'V': Scroll(p); break;                            /* scrollback */
    case 'Z': Submit(); break;                             /* Enter */
    case 'Q': {                                            /* diagnostics: who holds the words? */
        static char d[300], ft[120], fc[32];
        HWND f = GetFocus();
        ft[0] = fc[0] = 0;
        if (f) { GetWindowText(f, ft, sizeof ft); GetClassName(f, fc, sizeof fc); }
        wsprintf(d, "input=%04X id=%d len=%d parent=%04X focus=%04X class=%s id=%d text=%s",
                 (UINT)hInput, hInput ? GetDlgCtrlID(hInput) : -1,
                 hInput ? (int)SendMessage(hInput, WM_GETTEXTLENGTH, 0, 0L) : -1,
                 (UINT)GetParent(hInput), (UINT)f, (LPSTR)fc, f ? GetDlgCtrlID(f) : -1, (LPSTR)ft);
        Send('L', d, NULL, NULL);
        break;
    }
    case 'T': SendMessage(hInput, WM_SETTEXT, 0, (LPARAM)p);   /* history recall */
              SendMessage(hInput, EM_SETSEL, 0, MAKELPARAM(32767, 32767)); break;
    case 'P': SendMessage(hInput, EM_REPLACESEL, 0, (LPARAM)p); break;   /* paste */
    case 'Y': EnableWindow(hStop, atoi(p)); break;         /* busy: Stop lights up */
    case 'X': Press(hStop); break;                         /* Esc */
    case 'F': BringWindowToTop(hNote); SetActiveWindow(hNote); if (hInput) SetFocus(hInput); break;
    case 'R': if (b) Run(a, b); break;                     /* id, command */
    case 'G': if (b) { char full[128]; FullPath(full, b); ReadBack(a, full); } break;
    case 'W': if (b && c) Write(a, b, c); break;           /* id, path, text */
    }
}

long FAR PASCAL __export HostProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_TIMER) {
        LinkPoll(Handle);
        RunCheck();
        if (hText && IsWindow(hText)) {                    /* keep Notepad's edit where we put it */
            RECT r;
            GetWindowRect(hText, &r);
            if (r.right - r.left != TextW || r.bottom - r.top != ClientH - BARH) Layout();
        }
        return 0;
    }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProc(h, m, w, l);
}

int PASCAL WinMain(HINSTANCE hi, HINSTANCE prev, LPSTR cmdline, int show)
{
    WNDCLASS wc;
    MSG m;
    hInst = hi;
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = HostProc;
    wc.hInstance = hi;
    wc.lpszClassName = "Basilisk";
    RegisterClass(&wc);
    hHost = CreateWindow("Basilisk", "BASILISK", WS_OVERLAPPED, 0, 0, 0, 0, NULL, NULL, hi, NULL);
    {   /* start reading the page's file where it ends now: old messages were for B3BOOT */
        OFSTRUCT of;
        HFILE f = OpenFile("C:\\B3\\TOWIN.TXT", &of, OF_READ | OF_SHARE_DENY_NONE);
        if (f != HFILE_ERROR) { linkIn = _llseek(f, 0L, 2); _lclose(f); }
    }
    Send('H', "basilisk", NULL, NULL);
    Assemble();
    Send('R', "assembled", NULL, NULL);
    SetTimer(hHost, 1, 40, NULL);
    while (GetMessage(&m, NULL, 0, 0)) { TranslateMessage(&m); DispatchMessage(&m); }
    return 0;
}
