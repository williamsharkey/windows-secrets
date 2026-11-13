/*  BASILISK.C - Claude Code for Windows for Workgroups 3.11: the suite
 *
 *  Nothing on screen is drawn by this program except two gauges.  It borrows:
 *    Cardfile      five cards; their index lines are the tabs:  1 Chat  2 Plan  3 Files  4 Usage  5 Settings
 *    Notepad       the transcript (browser) or Terminal (server), and a second Notepad for the plan
 *    Find          Notepad's own Find dialog as the input bar (browser): Find Next = Send, Cancel = Stop
 *    File Manager  its directory window on C:\B3\WORK
 *    Control Panel the Mouse applet's sliders and boxes: effort, answer length, asking, model
 *    Clock         the face in the corner;  Calculator  its display, for the bill
 *  The link to Claude is COM2 (server), two files on C: (js-dos), or the BSYN card's ports (DOSBox Pure in the
 *  browser: the same guest/host packets BASILISK 16 uses), picked at run time.
 *
 *  wcl -q -bt=windows -l=windows -ml -k16384 basilisk.c
 */
#include <windows.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <direct.h>
#include <conio.h>
#include <dos.h>

#define EOT 4
#define SEP 0x1F

HINSTANCE hInst;
HWND hHost, hNote, hText, hFind, hInput, hSend, hStop, hClock, hCardfile, hCard, hCalc, hBill;
HWND hCardBox, hPlanNote, hPlan, hFm, hFmClient, hFmStatus, hCpl, hSet, hUsage;
HWND sEffort, sLength, bAsk, bModel, tEffortWord, gEffort, gLength;
int Browser, Bsyn, Tab = -1, cid = -1;
HINSTANCE runInst;
DWORD runEnd;
char runId[16];
int asking, busy;
char askId[16];

/* ================================================================ the link */

long linkIn;
static char lbuf[8200];
int lbn;

/* the BSYN card (DOSBox Pure web engine): text goes out as report packets of up to 240 bytes (type 7 = more,
   3 = the line ends), and comes in as events (type 8 = more, 4 = the line ends; words 1-2 an id, then bytes);
   an event of type 6 is the host's pointer (x, y), which only the guest can place */
#define BS_ARG 0x2C0
#define BS_CMD 0x2C2
#define BS_MAGIC 0x2C4
static char bsOut[240];
static int bsN;
void BsPacket(int last)
{
    int i, n = (bsN + 1) / 2;
    _disable();
    outpw(BS_ARG, (WORD)(((last ? 3 : 7) << 8) | (n + 1)));
    for (i = 0; i < bsN; i += 2) outpw(BS_ARG, (WORD)((BYTE)bsOut[i] | ((i + 1 < bsN ? (BYTE)bsOut[i + 1] : 0) << 8)));
    outpw(BS_CMD, 22);
    _enable();
    bsN = 0;
}
void BsAdd(LPCSTR t, int n) { while (n--) { if (bsN == sizeof bsOut) BsPacket(0); bsOut[bsN++] = *t++; } }

void LinkPut(char type, LPCSTR a, LPCSTR b, LPCSTR c)
{
    static char sep[2] = { SEP, 0 }, t[2], e[2] = { EOT, 0 };
    t[0] = type;
    if (Bsyn) {
        bsN = 0;
        BsAdd(t, 1);
        if (a) BsAdd(a, lstrlen(a));
        if (b) { BsAdd(sep, 1); BsAdd(b, lstrlen(b)); }
        if (c) { BsAdd(sep, 1); BsAdd(c, lstrlen(c)); }
        BsPacket(1);
    } else if (Browser) {
        OFSTRUCT of;
        HFILE f = OpenFile("C:\\B3\\TOJS.TXT", &of, OF_WRITE | OF_SHARE_DENY_NONE);
        if (f == HFILE_ERROR) f = OpenFile("C:\\B3\\TOJS.TXT", &of, OF_CREATE | OF_WRITE);
        if (f == HFILE_ERROR) return;
        _llseek(f, 0L, 2);
        _lwrite(f, t, 1);
        if (a) _lwrite(f, a, lstrlen(a));
        if (b) { _lwrite(f, sep, 1); _lwrite(f, b, lstrlen(b)); }
        if (c) { _lwrite(f, sep, 1); _lwrite(f, c, lstrlen(c)); }
        _lwrite(f, e, 1);
        _lclose(f);
    } else if (cid >= 0) {
        WriteComm(cid, t, 1);
        if (a) WriteComm(cid, a, lstrlen(a));
        if (b) { WriteComm(cid, sep, 1); WriteComm(cid, b, lstrlen(b)); }
        if (c) { WriteComm(cid, sep, 1); WriteComm(cid, c, lstrlen(c)); }
        WriteComm(cid, e, 1);
    }
}

void LinkPoll(void (*h)(char, LPSTR))
{
    int n, i;
    if (Bsyn) {                          /* events: the bytes join the buffer; a line's end is an EOT */
        WORD w[140];
        int k, j;
        n = 0;
        for (k = 0; k < 64 && lbn + n < (int)sizeof lbuf - 260; k++) {
            int c;
            _disable();
            outpw(BS_CMD, 20);
            c = inpw(BS_ARG);
            for (j = 0; j < c; j++) { WORD x = inpw(BS_ARG); if (j < 140) w[j] = x; }
            _enable();
            if (c <= 0) break;
            if ((w[0] >> 8) == 6 && c >= 3) { SetCursorPos((int)w[1], (int)w[2]); continue; }
            if ((w[0] >> 8) != 4 && (w[0] >> 8) != 8) continue;
            for (j = 3; j < c && j < 140; j++) {
                BYTE lo = (BYTE)w[j], hi = (BYTE)(w[j] >> 8);
                if (lo) lbuf[lbn + n++] = lo;
                if (lo && hi) lbuf[lbn + n++] = hi;
            }
            if ((w[0] >> 8) == 4) lbuf[lbn + n++] = EOT;
        }
    } else if (Browser) {
        OFSTRUCT of;
        HFILE f = OpenFile("C:\\B3\\TOWIN.TXT", &of, OF_READ | OF_SHARE_DENY_NONE);
        if (f == HFILE_ERROR) return;
        _llseek(f, linkIn + lbn, 0);
        n = _lread(f, lbuf + lbn, sizeof lbuf - 1 - lbn);
        _lclose(f);
    } else {
        COMSTAT cs;
        if (cid < 0) return;
        GetCommError(cid, &cs);
        n = ReadComm(cid, lbuf + lbn, sizeof lbuf - 1 - lbn);
        if (n < 0) { n = -n; GetCommError(cid, &cs); }
    }
    if (n <= 0) return;
    lbn += n;
    for (;;) {
        static char msg[8200];
        char t;
        for (i = 0; i < lbn && lbuf[i] != EOT; i++) ;
        if (i >= lbn) break;
        lbuf[i] = 0;
        t = lbuf[0];
        memcpy(msg, lbuf + 1, i);
        memmove(lbuf, lbuf + i + 1, lbn - i - 1);
        lbn -= i + 1;
        linkIn += i + 1;
        h(t, msg);
    }
    if (lbn >= (int)sizeof lbuf - 1) { linkIn += lbn; lbn = 0; }
}

#define Send(t, a, b, c) LinkPut(t, a, b, c)

/* ================================================================ borrowing windows */

void Pump(int ms)
{
    DWORD end = GetTickCount() + ms;
    MSG m;
    do {
        while (PeekMessage(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessage(&m); }
        Yield();
    } while ((long)(GetTickCount() - end) < 0);
}

HWND Launch(LPCSTR cmd, int show)        /* start a program, return its main window */
{
    HINSTANCE hi = WinExec(cmd, show);
    DWORD end = GetTickCount() + 9000;
    HWND h;
    if (hi < 32) return NULL;
    while ((long)(GetTickCount() - end) < 0) {
        for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT))
            if ((HINSTANCE)GetWindowWord(h, GWW_HINSTANCE) == hi && !GetWindow(h, GW_OWNER) &&
                (IsWindowVisible(h) || show == SW_HIDE)) {
                char c[24];
                GetClassName(h, c, sizeof c);
                if (lstrcmp(c, "#32770") || show == SW_HIDE) return h;
            }
        Pump(40);
    }
    return NULL;
}

HWND Kid(HWND parent, LPCSTR cls)
{
    HWND h;
    char c[32];
    for (h = GetWindow(parent, GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
        GetClassName(h, c, sizeof c);
        if (!lstrcmpi(c, cls)) return h;
    }
    return NULL;
}

UINT MenuId(HWND w, LPCSTR want)
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

HWND Dialog(HWND owner, LPCSTR title)    /* a dialog a program just opened */
{
    DWORD end = GetTickCount() + 5000;
    HWND h;
    char c[16], t[40];
    while ((long)(GetTickCount() - end) < 0) {
        for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
            GetClassName(h, c, sizeof c);
            if (lstrcmp(c, "#32770") || !IsWindowVisible(h)) continue;
            GetWindowText(h, t, sizeof t);
            if ((owner && GetWindow(h, GW_OWNER) == owner) || (title && !lstrcmp(t, title))) return h;
        }
        Pump(40);
    }
    return NULL;
}

void Type(HWND e, LPCSTR text)           /* keystrokes into a field, as a person would */
{
    SetFocus(e);
    SendMessage(e, EM_SETSEL, 0, MAKELPARAM(0, 32767));
    PostMessage(e, WM_KEYDOWN, VK_DELETE, 0x00530001L);
    for (; *text; text++) { PostMessage(e, WM_CHAR, (BYTE)*text, 1L); Pump(14); }   /* a queue holds 8 */
    PostMessage(e, WM_KEYDOWN, VK_RETURN, 0x001C0001L);
    PostMessage(e, WM_KEYUP, VK_RETURN, 0xC01C0001L);
}

void Adopt(HWND child, HWND into, int x, int y, int w, int h, long extra)
{
    long st = GetWindowLong(child, GWL_STYLE);
    st &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | DS_MODALFRAME);
    SetWindowLong(child, GWL_STYLE, st | WS_CHILD | extra);
    SetParent(child, into);
    MoveWindow(child, x, y, w - 1, h - 1, FALSE);   /* a real resize, so it re-measures its new client area */
    MoveWindow(child, x, y, w, h, TRUE);
}

/* a top-level window travels to a screen rectangle; everything it uncovers is repainted as it goes */
void Glide(HWND w, int x, int y, int cx, int cy, int ms)
{
    RECT r;
    DWORD t0 = GetTickCount();
    long t;
    GetWindowRect(w, &r);
    if (GetWindowLong(w, GWL_STYLE) & WS_CHILD) {
        POINT a, b;
        a.x = r.left; a.y = r.top; b.x = r.right; b.y = r.bottom;
        ScreenToClient(GetParent(w), &a); ScreenToClient(GetParent(w), &b);
        SetRect(&r, a.x, a.y, b.x, b.y);
    }
    for (;;) {
        int k;
        t = (long)(GetTickCount() - t0);
        if (t > ms) t = ms;
        k = (int)(t * 1000L / ms);
        k = k < 500 ? (int)(2L * k * k / 1000) : 1000 - (int)(2L * (1000 - k) * (1000 - k) / 1000);
        MoveWindow(w, r.left + (int)((long)(x - r.left) * k / 1000), r.top + (int)((long)(y - r.top) * k / 1000),
                   (r.right - r.left) + (int)((long)(cx - (r.right - r.left)) * k / 1000),
                   (r.bottom - r.top) + (int)((long)(cy - (r.bottom - r.top)) * k / 1000), TRUE);
        if (hNote) UpdateWindow(hNote);
        UpdateWindow(GetDesktopWindow());
        UpdateWindow(w);
        if (t >= ms) break;
        Pump(25);
    }
}

void Repaint(HWND w)
{
    RedrawWindow(w, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN | RDW_UPDATENOW);
}

/* ================================================================ geometry */

#define BARH 34
#define CARDH 268
int PaneW, ClientH, ClientW, ColX, ColW, ClockH, FmH;
char Title[120];

void Geometry(void)
{
    RECT r;
    GetClientRect(hNote, &r);
    ClientW = r.right; ClientH = r.bottom;
    PaneW = Browser ? 80 * 8 + 6 : 80 * 8 + GetSystemMetrics(SM_CXVSCROLL) + 6;
    ColX = PaneW + 8;
    ColW = ClientW - ColX - 8;
    ClockH = ClientH - CARDH - 24 - 30;
}

int PaneH(void) { return Browser ? ClientH - BARH : ClientH; }

/* ================================================================ the tabs: Cardfile's cards */

static char *TabName[5] = { "1 Chat", "2 Plan", "3 Files", "4 Usage", "5 Settings" };
static char *TabHead[5] = { "Talking to Claude", "Claude's plan", "Files in C:\\B3\\WORK",
                            "This session", "Settings" };
static char CardBody[5][520];

HWND CardEdit(void) { return Kid(hCard, "Edit"); }

void WriteCards(void)                    /* the five cards, as a Cardfile file (MGC): index lines sorted, then bodies */
{
    OFSTRUCT of;
    HFILE f = OpenFile("C:\\B3\\TABS.CRD", &of, OF_CREATE | OF_WRITE);
    static char e[52];
    long at = 5 + 5 * 52L;
    int i;
    WORD n = 5, z = 0, len;
    if (f == HFILE_ERROR) return;
    _lwrite(f, "MGC", 3);
    _lwrite(f, (LPSTR)&n, 2);
    for (i = 0; i < 5; i++) {
        memset(e, 0, sizeof e);
        *(long *)(e + 6) = at;
        lstrcpy(e + 11, TabName[i]);
        _lwrite(f, e, 52);
        at += 4 + lstrlen(CardBody[i]);
    }
    for (i = 0; i < 5; i++) {
        len = lstrlen(CardBody[i]);
        _lwrite(f, (LPSTR)&z, 2);
        _lwrite(f, (LPSTR)&len, 2);
        _lwrite(f, CardBody[i], len);
    }
    _lclose(f);
}

void CardKey(int vk)                     /* PgUp/PgDn, as Cardfile itself takes them */
{
    long sc = vk == VK_NEXT ? 0x01510001L : 0x01490001L;
    HWND e = CardEdit();
    PostMessage(e ? e : hCard, WM_KEYDOWN, vk, sc);
    PostMessage(e ? e : hCard, WM_KEYUP, vk, sc | 0xC0000000L);
}

int FrontCard(void)                      /* which card is in front: its body starts with its heading */
{
    static char t[60];
    HWND e = CardEdit();
    int i;
    if (!e) return -1;
    t[0] = 0;
    SendMessage(e, WM_GETTEXT, sizeof t, (LPARAM)(LPSTR)t);
    for (i = 0; i < 5; i++) if (!strncmp(t, TabHead[i], lstrlen(TabHead[i]))) return i;
    return -1;
}

void SetCard(int i, LPCSTR body)         /* the body of card i (written now if it is in front) */
{
    wsprintf(CardBody[i], "%s\r\n%s", (LPSTR)TabHead[i], (LPSTR)body);
    if (FrontCard() == i) {
        HWND e = CardEdit();
        SendMessage(e, WM_SETTEXT, 0, (LPARAM)(LPSTR)CardBody[i]);
        SendMessage(e, EM_SETMODIFY, TRUE, 0L);
        InvalidateRect(e, NULL, TRUE);
        UpdateWindow(e);
    }
}

void Keep(void)                          /* the donors re-lay themselves out for frames they no longer have: undo it */
{
    RECT r;
    char t[120];
    if (hFmClient && IsWindow(hFmClient)) {
        GetWindowRect(hFmClient, &r);
        if (r.right - r.left != PaneW || r.bottom - r.top != FmH) {
            HWND c = GetWindow(hFmClient, GW_CHILD);
            MoveWindow(hFmClient, 0, 0, PaneW, FmH, TRUE);
            if (c) SendMessage(hFmClient, WM_MDIMAXIMIZE, (WPARAM)c, 0L);
        }
    }
    if (Title[0]) {                      /* File Manager titles "its" frame after a refresh */
        GetWindowText(hNote, t, sizeof t);
        if (lstrcmp(t, Title)) SetWindowText(hNote, Title);
    }
}

void ShowPane(int t)                     /* the left pane shows tab t's borrowed part */
{
    HWND show[6], hide[8];
    int ns = 0, nh = 0, i;
    if (t == Tab) return;
    if (t == 0) { show[ns++] = hText; if (hFind) show[ns++] = hFind; } else { hide[nh++] = hText; if (hFind) hide[nh++] = hFind; }
    if (t == 1) show[ns++] = hPlan; else hide[nh++] = hPlan;
    if (t == 2) { show[ns++] = hFmClient; show[ns++] = hFmStatus; } else { hide[nh++] = hFmClient; hide[nh++] = hFmStatus; }
    if (t == 3) show[ns++] = hUsage; else hide[nh++] = hUsage;
    if (t == 4) show[ns++] = hSet; else hide[nh++] = hSet;
    for (i = 0; i < nh; i++) if (hide[i]) ShowWindow(hide[i], SW_HIDE);
    for (i = 0; i < ns; i++) if (show[i]) { ShowWindow(show[i], SW_SHOWNA); Repaint(show[i]); }
    Tab = t;
    {   /* the title bar is the status line */
        wsprintf(Title, "BASILISK 3.11  -  %s", (LPSTR)(TabName[t] + 2));
        SetWindowText(hNote, Title);
    }
    if (t == 0 && hInput) SetFocus(hInput);
    Keep();
    Send('J', TabName[t] + 2, NULL, NULL);
}

void GoTab(int t)                        /* bring card t to the front of the file, as PgDn would */
{
    int i, f;
    if (t < 0 || t > 4) return;
    for (i = 0; i < 5 && (f = FrontCard()) != t && f >= 0; i++) {
        CardKey(VK_NEXT);
        Pump(60);
    }
    f = FrontCard();
    if (f >= 0) {
        HWND e = CardEdit();
        if (lstrcmp(CardBody[f], "")) { SendMessage(e, WM_SETTEXT, 0, (LPARAM)(LPSTR)CardBody[f]); SendMessage(e, EM_SETMODIFY, TRUE, 0L); }
        ShowPane(f);
    }
}

/* ================================================================ the transcript (browser: Notepad) */

int Visible(void)
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

void Settle(int toEnd)
{
    int total = (int)SendMessage(hText, EM_GETLINECOUNT, 0, 0L);
    int first = (int)SendMessage(hText, EM_GETFIRSTVISIBLELINE, 0, 0L);
    int want = total - Visible();
    if (want < 0) want = 0;
    if (toEnd || first > want) SendMessage(hText, EM_LINESCROLL, 0, MAKELPARAM(want - first, 0));
}

void Append(LPCSTR text)
{
    int n = (int)SendMessage(hText, WM_GETTEXTLENGTH, 0, 0L);
    if (n > 22000) {
        SendMessage(hText, EM_SETSEL, 0, MAKELPARAM(0, 8000));
        SendMessage(hText, EM_REPLACESEL, 0, (LPARAM)(LPSTR)"[...]\r\n");
        n = (int)SendMessage(hText, WM_GETTEXTLENGTH, 0, 0L);
    }
    SendMessage(hText, EM_SETSEL, 0, MAKELPARAM(n, n));
    SendMessage(hText, EM_REPLACESEL, 0, (LPARAM)text);
    Settle(1);
}

void Back(int k)
{
    int n = (int)SendMessage(hText, WM_GETTEXTLENGTH, 0, 0L);
    if (k > n) k = n;
    SendMessage(hText, EM_SETSEL, 0, MAKELPARAM(n - k, n));
    SendMessage(hText, EM_REPLACESEL, 0, (LPARAM)(LPSTR)"");
}

void Scroll(LPSTR how)
{
    int n, vis;
    if (!Browser) {                      /* Terminal scrolls by its own scrollbar */
        if (!lstrcmp(how, "P-")) { SendMessage(hText, WM_VSCROLL, SB_PAGEUP, 0L); return; }
        if (!lstrcmp(how, "P+")) { SendMessage(hText, WM_VSCROLL, SB_PAGEDOWN, 0L); return; }
        n = atoi(how);
        while (n < 0) { SendMessage(hText, WM_VSCROLL, SB_LINEUP, 0L); n++; }
        while (n > 0) { SendMessage(hText, WM_VSCROLL, SB_LINEDOWN, 0L); n--; }
        return;
    }
    vis = Visible();
    if (!lstrcmp(how, "E")) { Settle(1); return; }
    if (!lstrcmp(how, "P-")) n = -(vis - 1);
    else if (!lstrcmp(how, "P+")) n = vis - 1;
    else n = atoi(how);
    {
        int first = (int)SendMessage(hText, EM_GETFIRSTVISIBLELINE, 0, 0L);
        int max = (int)SendMessage(hText, EM_GETLINECOUNT, 0, 0L) - vis;
        if (max < 0) max = 0;
        if (first + n > max) n = max - first;
        if (first + n < 0) n = -first;
        if (n) SendMessage(hText, EM_LINESCROLL, 0, MAKELPARAM(n, 0));
    }
}

void Show(HWND w, LPCSTR text)
{
    SetWindowText(w, text);
    InvalidateRect(w, NULL, TRUE);
    UpdateWindow(w);
}

void Press(HWND b)
{
    SendMessage(b, BM_SETSTATE, TRUE, 0L);
    UpdateWindow(b);
    Pump(90);
    SendMessage(b, BM_SETSTATE, FALSE, 0L);
    UpdateWindow(b);
}

void Submit(void)
{
    static char t[1100];
    t[0] = 0;
    SendMessage(hInput, WM_GETTEXT, sizeof t, (LPARAM)(LPSTR)t);
    SendMessage(hInput, WM_SETTEXT, 0, (LPARAM)(LPSTR)"");
    Press(hSend);
    Send('U', t, NULL, NULL);
}

/* ================================================================ tools */

void FullPath(LPSTR out, LPCSTR p)
{
    if (p[0] && p[1] == ':') lstrcpy(out, p);
    else if (p[0] == '\\') { lstrcpy(out, "C:"); lstrcat(out, p); }
    else { lstrcpy(out, "C:\\B3\\WORK\\"); lstrcat(out, p); }
}

void ReadBack(LPCSTR id, LPCSTR path)
{
    static char buf[3600];
    OFSTRUCT of;
    HFILE f = OpenFile(path, &of, OF_READ);
    int n, i;
    if (f == HFILE_ERROR) { Send('O', id, "err", "file not found"); return; }
    n = _lread(f, buf, 3500);
    _lclose(f);
    if (n < 0) n = 0;
    buf[n] = 0;
    for (i = 0; i < n; i++) if (buf[i] == EOT || buf[i] == 0 || buf[i] == SEP) buf[i] = ' ';
    Send('O', id, "ok", buf);
}

void Run(LPCSTR id, LPCSTR cmd)
{
    OFSTRUCT of;
    HFILE f;
    static char line[300];
    if (runInst) { Send('O', id, "err", "another command is still running"); return; }
    f = OpenFile("C:\\B3\\CMD.BAT", &of, OF_CREATE | OF_WRITE);
    if (strchr(cmd, '>')) wsprintf(line, "@echo off\r\ncd \\B3\\WORK\r\n%s\r\n", cmd);
    else wsprintf(line, "@echo off\r\ncd \\B3\\WORK\r\n%s > C:\\B3\\OUT.TXT\r\n", cmd);
    _lwrite(f, line, lstrlen(line));
    _lclose(f);
    OpenFile("C:\\B3\\OUT.TXT", &of, OF_DELETE);
    runInst = WinExec("C:\\B3\\CMD.BAT", SW_SHOWMINNOACTIVE);
    if (runInst < 32) { runInst = 0; Send('O', id, "err", "could not start COMMAND.COM"); return; }
    lstrcpy(runId, id);
    runEnd = GetTickCount() + 60000L;
}

void RunCheck(void)
{
    if (!runInst) return;
    if (GetModuleUsage(runInst) > 0) {
        if ((long)(GetTickCount() - runEnd) < 0) return;
        Send('O', runId, "err", "still running after 60 seconds (left running)");
    } else ReadBack(runId, "C:\\B3\\OUT.TXT");
    runInst = 0;
    BringWindowToTop(hNote);
    if (hInput && Tab == 0) SetFocus(hInput);
    if (hFmClient) PostMessage(hFm, WM_KEYDOWN, VK_F5, 0x003F0001L);   /* File Manager: refresh */
}

void Write(LPCSTR id, LPCSTR path, LPCSTR body)
{
    OFSTRUCT of;
    static char full[128], msg[160];
    HFILE f;
    FullPath(full, path);
    f = OpenFile(full, &of, OF_CREATE | OF_WRITE);
    if (f == HFILE_ERROR) { Send('O', id, "err", "cannot create that file"); return; }
    _lwrite(f, body, lstrlen(body));
    _lclose(f);
    wsprintf(msg, "wrote %d bytes to %s", lstrlen(body), (LPSTR)full);
    Send('O', id, "ok", msg);
    if (hFm) PostMessage(hFm, WM_KEYDOWN, VK_F5, 0x003F0001L);
}

#include "parts.c"                       /* plan, permission, files, usage, settings, mouse: PARTS.C */

/* ================================================================ the assembly, shown */

DWORD aT0;
void Step(LPCSTR what)                   /* the host shows the assembly as it goes (and how long each part took) */
{
    static char t[60];
    wsprintf(t, "%s %ld", what, (long)(GetTickCount() - aT0));
    Send('S', t, NULL, NULL);
}

void Assemble(void)
{
    UINT id;
    int sw = GetSystemMetrics(SM_CXSCREEN), sh = GetSystemMetrics(SM_CYSCREEN), i;
    RECT r;
    POINT o;

    /* the host: Notepad (browser) or Terminal (server) opens, then fills the screen */
    aT0 = GetTickCount();
    if (Browser) hNote = Launch("NOTEPAD.EXE", SW_SHOWNORMAL), hText = Kid(hNote, "Edit");
    else hNote = Launch("TERMINAL.EXE C:\\B3\\B3.TRM", SW_SHOWNORMAL), hText = Kid(hNote, "DC_Term");
    SetWindowText(hNote, "BASILISK 3.11");
    Pump(150);
    Glide(hNote, 0, 0, sw, sh, 380);
    ShowWindow(hNote, SW_SHOWMAXIMIZED);
    SetWindowLong(hNote, GWL_STYLE, GetWindowLong(hNote, GWL_STYLE) | WS_CLIPCHILDREN);
    SetClassWord(hNote, GCW_HBRBACKGROUND, (WORD)GetStockObject(LTGRAY_BRUSH));
    if (Browser) {
        SendMessage(hText, WM_SETFONT, (WPARAM)GetStockObject(SYSTEM_FIXED_FONT), 0L);
        SendMessage(hText, EM_LIMITTEXT, 0, 0L);
    }
    if (Browser) ShowScrollBar(hNote, SB_BOTH, FALSE);
    Geometry();
    MoveWindow(hText, 0, 0, PaneW, PaneH(), TRUE);
    o.x = o.y = 0;
    ClientToScreen(hNote, &o);
    hUsage = CreateWindow("B3Usage", "", WS_CHILD | WS_BORDER, 0, 0, PaneW, ClientH, hNote, NULL, hInst, NULL);
    hSet = CreateWindow("B3Pane", "", WS_CHILD | WS_BORDER, 0, 0, PaneW, ClientH, hNote, NULL, hInst, NULL);
    Repaint(hNote);

    Step("find");
    /* the input bar (browser): Notepad's Find dialog sheds what it won't need, one control at a time */
    if (Browser && (id = MenuId(hNote, "&Find...")) != 0) {
        HWND h, nx;
        PostMessage(hNote, WM_COMMAND, id, 0L);
        if ((hFind = Dialog(hNote, NULL)) != NULL) {
            hInput = GetDlgItem(hFind, 1152);
            hSend = GetDlgItem(hFind, IDOK);
            hStop = GetDlgItem(hFind, IDCANCEL);
            Pump(150);
            for (h = GetWindow(hFind, GW_CHILD); h; h = nx) {
                nx = GetWindow(h, GW_HWNDNEXT);
                if (h != hInput && h != hSend && h != hStop && IsWindowVisible(h)) {
                    ShowWindow(h, SW_HIDE); UpdateWindow(hFind); Pump(45);
                }
            }
            SetWindowWord(hSend, GWW_ID, 0x7701);
            SetWindowWord(hStop, GWW_ID, 0x7702);
            Show(hSend, "Send"); Pump(90);
            Show(hStop, "Stop"); Pump(90);
            EnableWindow(hSend, TRUE);
            EnableWindow(hStop, FALSE);
            GetWindowRect(hFind, &r);
            Glide(hFind, o.x, o.y + ClientH - BARH - (GetSystemMetrics(SM_CYCAPTION)), PaneW, BARH + GetSystemMetrics(SM_CYCAPTION), 380);
            SendMessage(hInput, WM_SETFONT, (WPARAM)GetStockObject(SYSTEM_FIXED_FONT), 0L);
            SendMessage(hInput, EM_LIMITTEXT, 1000, 0L);
            Adopt(hFind, hNote, 0, ClientH - BARH, PaneW, BARH, 0);
            MoveWindow(hInput, 6, 6, PaneW - 2 * 64 - 22, 22, TRUE);
            MoveWindow(hSend, PaneW - 2 * 64 - 10, 5, 64, 24, TRUE);
            MoveWindow(hStop, PaneW - 64 - 6, 5, 64, 24, TRUE);
            ShowWindow(hFind, SW_SHOWNA);
            Repaint(hFind);
        }
    }

    Step("clock");
    /* the clock: appears, then glides to the top of the column */
    hClock = Launch("CLOCK.EXE", SW_SHOWNORMAL);
    if ((id = MenuId(hClock, "&Analog")) != 0) PostMessage(hClock, WM_COMMAND, id, 0L);
    Pump(150);
    SetMenu(hClock, NULL);
    Glide(hClock, o.x + ColX, o.y + 8, ColW, ClockH, 380);
    Adopt(hClock, hNote, ColX, 8, ColW, ClockH, WS_BORDER);
    ShowWindow(hClock, SW_SHOWNA);

    Step("calculator");
    /* the bill: Calculator appears, its display leaves it */
    hCalc = Launch("CALC.EXE", SW_SHOWNORMAL);
    hBill = GetDlgItem(hCalc, 414);
    Pump(200);
    GetWindowRect(hBill, &r);
    Adopt(hBill, hNote, r.left - o.x, r.top - o.y, r.right - r.left, r.bottom - r.top, WS_BORDER);
    ShowWindow(hBill, SW_SHOWNA);
    BringWindowToTop(hBill);
    UpdateWindow(hBill);
    Pump(120);
    ShowWindow(hCalc, SW_HIDE);
    UpdateWindow(hNote);
    Pump(100);
    Glide(hBill, ColX, ClockH + 16, ColW, 24, 350);
    SetWindowText(hBill, "$0.00000 ");
    ShowWindow(hBill, SW_SHOWNA);

    Step("cardfile");
    /* the tabs: Cardfile, five cards typed in one after another, then the file slides into the column */
    wsprintf(CardBody[0], "%s\r\n%s", (LPSTR)TabHead[0], (LPSTR)(Browser ?
             "Type in the box below. Enter sends,\r\nEsc stops. Up/Down: earlier lines.\r\nPgUp/PgDn: scroll back.\r\nAlt+1..5 or a click: change card.\r\n/help  /clear  /compact  /cost" :
             "Type and press Enter. Esc stops.\r\nPgUp/PgDn: scroll back.\r\nAlt+1..5 or a click: change card.\r\n/help  /clear  /compact  /cost"));
    wsprintf(CardBody[1], "%s\r\nNothing planned yet.\r\nAsk for something with a few steps.", (LPSTR)TabHead[1]);
    wsprintf(CardBody[2], "%s\r\nC:\\B3\\WORK in File Manager.\r\nPick a file, press Ins: it goes\r\ninto your message as @NAME.\r\nCLAUDE.MD here is read every turn.", (LPSTR)TabHead[2]);
    wsprintf(CardBody[3], "%s\r\nNo questions asked yet.", (LPSTR)TabHead[3]);
    wsprintf(CardBody[4], "%s\r\nEffort low, answers normal.\r\nAsks before running commands.\r\nModel: Claude Haiku 5.5.", (LPSTR)TabHead[4]);
    WriteCards();
    hCardfile = Launch("CARDFILE.EXE C:\\B3\\TABS.CRD", SW_SHOWNORMAL);
    hCard = Kid(hCardfile, "Card");
    MoveWindow(hCardfile, o.x + ColX - 60, o.y + ClientH - CARDH - 120, ColW + 120, CARDH + 120, TRUE);
    UpdateWindow(hCardfile);
    Pump(250);
    {   /* the file glides so its front card lands on the column, then the cards leave Cardfile */
        RECT f;
        GetWindowRect(hCard, &r);
        GetWindowRect(hCardfile, &f);
        Glide(hCardfile, o.x + ColX - 4 - (r.left - f.left), o.y + ClientH - CARDH - (r.top - f.top),
              ColW + 8 + (f.right - f.left) - (r.right - r.left), CARDH + (f.bottom - f.top) - (r.bottom - r.top), 450);
    }
    /* Cardfile's card-flipping scroll bars belong to the card's parent: this box, whose bars hang off the screen */
    hCardBox = CreateWindow("B3Pane", "", WS_CHILD | WS_VISIBLE | WS_CLIPCHILDREN, ColX - 4, ClientH - CARDH,
                            ClientW - ColX + 4 + 40, CARDH + 40, hNote, NULL, hInst, NULL);
    Adopt(hCard, hCardBox, 0, 0, ClientW - ColX + 4 + 40, CARDH, 0);
    ShowWindow(hCard, SW_SHOWNA);
    ShowWindow(hCardfile, SW_HIDE);
    Repaint(hCard);

    Step("plan");
    /* the other tabs' parts arrive and go behind their cards */
    hPlanNote = Launch("NOTEPAD.EXE", SW_SHOWNORMAL);
    hPlan = Kid(hPlanNote, "Edit");
    SetWindowText(hPlanNote, "Plan - Notepad");
    SendMessage(hPlan, WM_SETFONT, (WPARAM)GetStockObject(SYSTEM_FIXED_FONT), 0L);
    SetPlan("");
    Pump(120);
    Glide(hPlanNote, o.x + ColX, o.y + ClientH - CARDH + 20, 60, 30, 300);
    Adopt(hPlan, hNote, 0, 0, PaneW, ClientH, WS_BORDER);
    ShowWindow(hPlan, SW_HIDE);
    ShowWindow(hPlanNote, SW_HIDE);

    chdir("C:\\B3\\WORK");               /* File Manager opens where it is started */
    Step("filemanager");
    hFm = Launch("WINFILE.EXE", SW_SHOWNORMAL);
    chdir("C:\\B3");
    hFmClient = Kid(hFm, "MDIClient");
    hFmStatus = Kid(hFm, "msctls_statusbar");
    Pump(250);
    if (hFmClient && GetWindow(hFmClient, GW_CHILD))
        SendMessage(hFmClient, WM_MDIMAXIMIZE, (WPARAM)GetWindow(hFmClient, GW_CHILD), 0L);
    Glide(hFm, o.x + ColX, o.y + ClientH - CARDH + 40, 60, 30, 300);
    if (hFmClient) {
        RECT sr;
        int sh = 24;
        if (hFmStatus) { GetWindowRect(hFmStatus, &sr); sh = sr.bottom - sr.top; }
        FmH = ClientH - sh;
        Adopt(hFmClient, hNote, 0, 0, PaneW, FmH, 0);
        ShowWindow(hFmClient, SW_HIDE);
    }
    if (hFmStatus) {
        RECT sr;
        GetWindowRect(hFmStatus, &sr);
        Adopt(hFmStatus, hNote, 0, ClientH - (sr.bottom - sr.top), PaneW, sr.bottom - sr.top, 0);
        ShowWindow(hFmStatus, SW_HIDE);
    }
    ShowWindow(hFm, SW_HIDE);

    Step("controlpanel");
    WinExec("CONTROL.EXE MAIN.CPL Mouse", SW_SHOWNORMAL);
    hCpl = Dialog(NULL, "Mouse");
    if (hCpl) {
        Pump(150);
        BuildSettings();
        Glide(hCpl, o.x + ColX, o.y + ClientH - CARDH + 60, 60, 30, 300);
        ShowWindow(hCpl, SW_HIDE);
    }
    ShowWindow(hSet, SW_HIDE);

    Step("done");
    Tab = -1;
    ShowPane(0);
    BringWindowToTop(hNote);
    SetActiveWindow(hNote);
    if (hInput) SetFocus(hInput);
    Repaint(hNote);
    SettingsSend(1);
}

/* ================================================================ messages from the host */

void SetClock(LPSTR p)                   /* "Y M D h m s": a machine resumed from a snapshot has the snapshot's time */
{
    union REGS r;
    int v[6], i;
    for (i = 0; i < 6 && *p; i++) { v[i] = atoi(p); while (*p && *p != ' ') p++; while (*p == ' ') p++; }
    if (i < 6) return;
    r.h.ah = 0x2B; r.x.cx = v[0]; r.h.dh = (BYTE)v[1]; r.h.dl = (BYTE)v[2]; intdos(&r, &r);
    r.h.ah = 0x2D; r.h.ch = (BYTE)v[3]; r.h.cl = (BYTE)v[4]; r.h.dh = (BYTE)v[5]; r.h.dl = 0; intdos(&r, &r);
}

void Handle(char type, LPSTR p)
{
    LPSTR a = p, b = NULL, c = NULL;
    if (type == 'A') { if (Browser) Append(p); return; }
    if ((b = strchr(a, SEP)) != NULL) { *b++ = 0; if ((c = strchr(b, SEP)) != NULL) *c++ = 0; }
    switch (type) {
    case 'B': if (Browser) Back(atoi(p)); break;
    case 'K': if (Browser) SendMessage(hText, WM_SETTEXT, 0, (LPARAM)(LPSTR)""); break;
    case 'S': SetCard(3, p); break;                       /* the session, on the Usage card */
    case 'N': SetUsage(p); break;                         /* the gauges */
    case 'C': Show(hBill, p); break;                      /* the bill */
    case 'L': { char *q; for (q = p; *q; q++) if (*q == '~') *q = '\r'; SetPlan(p); } break;
    case 'V': Scroll(p); break;
    case 'J': GoTab(atoi(p) - 1); break;                  /* Alt+1..5 */
    case 'Z': if (Browser) Submit(); break;
    case 'T': if (hInput) { SendMessage(hInput, WM_SETTEXT, 0, (LPARAM)p); SendMessage(hInput, EM_SETSEL, 0, MAKELPARAM(32767, 32767)); } break;
    case 'P': if (hInput) SendMessage(hInput, EM_REPLACESEL, 0, (LPARAM)p); break;
    case 'Y': if (hStop) EnableWindow(hStop, atoi(p)); break;
    case 'X': if (hStop) Press(hStop); break;
    case 'F': BringWindowToTop(hNote); SetActiveWindow(hNote); if (hInput && Tab == 0) SetFocus(hInput); break;
    case 'M': Mouse(p); break;
    case 'D': SetClock(p); break;
    case 'w': Wheel(atoi(p)); break;
    case 'Q': Spy(); break;
    case '@': Mention(); break;
    case 'I': if (b) Ask(a, b); break;                    /* id, what */
    case '!': Answer(p); break;
    case 'R': if (b) Run(a, b); break;
    case 'G': if (b) { char full[128]; FullPath(full, b); ReadBack(a, full); } break;
    case 'W': if (b && c) Write(a, b, c); break;
    }
}

void Sliders(void)                       /* the web engine presses the real mouse: the borrowed sliders' own
                                            tracking reports to Control Panel's hidden dialog, so drive them here */
{
    static int down;
    static char t[24];
    POINT pt;
    int k = GetAsyncKeyState(VK_LBUTTON), now = (k & 0x8000) != 0;
    GetCursorPos(&pt);
    if ((now || (k & 1)) && !down) {     /* pressed now, or pressed and let go since the last look (a quick click) */
        HWND w = WindowFromPoint(pt);
        if (w == sEffort || w == sLength) {
            wsprintf(t, "%d|%d|1|1", pt.x, pt.y); Mouse(t);
            if (!now && dragW) { wsprintf(t, "%d|%d|1|0", pt.x, pt.y); Mouse(t); }
        }
    } else if (now && dragW) { wsprintf(t, "%d|%d|0|0", pt.x, pt.y); Mouse(t); }
    else if (!now && down && dragW) { wsprintf(t, "%d|%d|1|0", pt.x, pt.y); Mouse(t); }
    down = now;
}

long FAR PASCAL __export HostProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_TIMER) {
        int f;
        if (busy) return 0;
        busy = 1;
        LinkPoll(Handle);
        RunCheck();
        if (hText && IsWindow(hText)) {
            RECT r;
            GetWindowRect(hText, &r);
            if (r.right - r.left != PaneW) MoveWindow(hText, 0, 0, PaneW, PaneH(), TRUE);
        }
        if (Tab >= 0 && (f = FrontCard()) >= 0 && f != Tab) ShowPane(f);   /* a card was clicked */
        Keep();
        if (Browser && (GetWindowLong(hNote, GWL_STYLE) & (WS_VSCROLL | WS_HSCROLL)))
            ShowScrollBar(hNote, SB_BOTH, FALSE);   /* Notepad keeps its bars on its frame; the column covers that edge */
        if (Bsyn && Tab == 4) Sliders();
        busy = 0;
        return 0;
    }
    if (m == WM_DESTROY) { PostQuitMessage(0); return 0; }
    return DefWindowProc(h, m, w, l);
}

int PASCAL WinMain(HINSTANCE hi, HINSTANCE prev, LPSTR cmdline, int show)
{
    WNDCLASS wc;
    MSG m;
    OFSTRUCT of;
    hInst = hi;
    Bsyn = inpw(BS_MAGIC) == 0x5342;
    Browser = Bsyn || OpenFile("C:\\B3\\TOWIN.TXT", &of, OF_EXIST) != HFILE_ERROR;
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = HostProc;
    wc.hInstance = hi;
    wc.lpszClassName = "Basilisk";
    RegisterClass(&wc);
    wc.lpfnWndProc = UsageProc;
    wc.hbrBackground = GetStockObject(LTGRAY_BRUSH);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.lpszClassName = "B3Usage";
    RegisterClass(&wc);
    wc.lpfnWndProc = PaneProc;
    wc.lpszClassName = "B3Pane";
    RegisterClass(&wc);
    hHost = CreateWindow("Basilisk", "BASILISK", WS_OVERLAPPED, 0, 0, 0, 0, NULL, NULL, hi, NULL);
    if (Bsyn) ;
    else if (Browser) {
        HFILE f = OpenFile("C:\\B3\\TOWIN.TXT", &of, OF_READ | OF_SHARE_DENY_NONE);
        if (f != HFILE_ERROR) { linkIn = _llseek(f, 0L, 2); _lclose(f); }
    } else {
        DCB dcb;
        cid = OpenComm("COM2", 8192, 4096);
        if (cid >= 0 && BuildCommDCB("COM2:19200,n,8,1", &dcb) == 0) { dcb.Id = cid; SetCommState(&dcb); }
    }
    Send('H', "basilisk", NULL, NULL);
    Assemble();
    Send('R', "assembled", NULL, NULL);
    SetTimer(hHost, 1, 40, NULL);
    while (GetMessage(&m, NULL, 0, 0)) { TranslateMessage(&m); DispatchMessage(&m); }
    if (cid >= 0) CloseComm(cid);
    return 0;
}
