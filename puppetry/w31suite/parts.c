/*  PARTS.C - the other four cards of BASILISK 3.11, and the mouse.  Included by BASILISK.C
 *  (Notepad holds about 45 KB, so the program is poured in as two files.)
 */

/* ================================================================ plan, permission, files */

void SetPlan(LPSTR items)                /* items: lines "[x] done" "[>] doing" "[ ] to do" */
{
    static char t[2600];
    wsprintf(t, "CLAUDE'S PLAN\r\n=============\r\n\r\n%s\r\n\r\n\r\n"
                "Permissions\r\n-----------\r\n"
                "Settings > \"Ask before running commands\" decides whether Claude asks.\r\n"
                "When it asks: Yes = run it this once, No = always allow that command,\r\n"
                "Cancel = don't run it.  DIR, TYPE, VER, MEM and SET never need asking.\r\n",
             items[0] ? items : (LPSTR)"(no plan yet: Claude writes one for bigger tasks)");
    SendMessage(hPlan, WM_SETTEXT, 0, (LPARAM)(LPSTR)t);
    SetCard(1, items[0] ? items : (LPSTR)"Nothing planned yet.\r\nAsk for something with a few steps.");
}

void Ask(LPSTR id, LPSTR what)           /* a real message box asks the visitor */
{
    static char t[400];
    int r;
    if (asking) { Send('I', id, "deny", NULL); return; }
    asking = 1;
    lstrcpy(askId, id);
    Send('I', id, "asking", NULL);
    wsprintf(t, "Claude wants to run:\n\n    %s\n\nYes\t= run it this once\nNo\t= always allow this command\n"
                "Cancel\t= don't run it", what);
    busy = 0;                            /* the link keeps flowing while the box waits (the host may answer it) */
    r = MessageBox(hNote, t, "BASILISK 3.11 - may Claude do this?", MB_YESNOCANCEL | MB_ICONQUESTION);
    asking = 0;
    busy = 1;
    Send('I', askId, r == IDYES ? "once" : r == IDNO ? "always" : "deny", NULL);
    if (hInput && Tab == 0) SetFocus(hInput);
}

void Answer(LPSTR how)                   /* the host answers the message box for the visitor */
{
    HWND h;
    char c[16];
    for (h = GetWindow(GetDesktopWindow(), GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
        GetClassName(h, c, sizeof c);
        if (!lstrcmp(c, "#32770") && GetWindow(h, GW_OWNER) == hNote && IsWindowVisible(h)) {
            int id = !lstrcmp(how, "once") ? IDYES : !lstrcmp(how, "always") ? IDNO : IDCANCEL;
            Press(GetDlgItem(h, id));
            PostMessage(h, WM_COMMAND, id, MAKELPARAM(GetDlgItem(h, id), BN_CLICKED));
            return;
        }
    }
}

void Mention(void)                       /* File Manager's selection, via its own Copy dialog's "From" */
{
    UINT id = MenuId(hFm, "&Copy...");
    HWND d, e;
    static char t[160], out[200];
    if (!id) return;
    PostMessage(hFm, WM_COMMAND, id, 0L);
    if ((d = Dialog(hFm, NULL)) == NULL) return;
    Pump(200);
    e = GetDlgItem(d, 102);              /* "From:" holds the selection */
    t[0] = 0;
    if (e) SendMessage(e, WM_GETTEXT, sizeof t, (LPARAM)(LPSTR)t);
    PostMessage(d, WM_COMMAND, IDCANCEL, 0L);
    Pump(150);
    if (!t[0]) return;
    {   /* first file name only, upper case, relative to C:\B3\WORK */
        char *p = t, *s;
        while (*p == ' ') p++;
        if ((s = strchr(p, ' ')) != NULL) *s = 0;
        if (!strnicmp(p, "C:\\B3\\WORK\\", 11)) p += 11;
        wsprintf(out, "@%s ", (LPSTR)p);
    }
    if (Browser) { SendMessage(hInput, EM_REPLACESEL, 0, (LPARAM)(LPSTR)out); GoTab(0); }
    Send('@', out, NULL, NULL);
}

/* ================================================================ Usage: gauges, drawn as Setup draws its own */

static long G[6];                        /* context used, context max, day $, day cap, month $, month cap (x1e5) */
static char UsageText[800];

void Gauge(HDC dc, int x, int y, int w, int h, long num, long den)
{
    RECT r, f;
    static char pc[8];
    int fill = den > 0 ? (int)((long)w * (num > den ? den : num) / den) : 0;
    HBRUSH blue = CreateSolidBrush(RGB(0, 0, 128));
    SetRect(&r, x, y, x + w, y + h);
    FrameRect(dc, &r, GetStockObject(BLACK_BRUSH));
    InflateRect(&r, -1, -1);
    FillRect(dc, &r, GetStockObject(WHITE_BRUSH));
    SetRect(&f, r.left, r.top, r.left + fill, r.bottom);
    FillRect(dc, &f, blue);
    DeleteObject(blue);
    {   /* tenths below 10%, as Setup never needed to */
        long k = den > 0 ? (long)((double)num * 1000.0 / den) : 0;
        if (k < 100) wsprintf(pc, "%ld.%ld%%", k / 10, k % 10);
        else wsprintf(pc, "%ld%%", k / 10);
    }
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, RGB(0, 0, 128));
    DrawText(dc, pc, -1, &r, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    SaveDC(dc);
    IntersectClipRect(dc, f.left, f.top, f.right, f.bottom);
    SetTextColor(dc, RGB(255, 255, 255));
    DrawText(dc, pc, -1, &r, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    RestoreDC(dc, -1);
}

long FAR PASCAL __export UsageProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(h, &ps);
        RECT r;
        static char t[120];
        int i, gw;
        static char *lab[3] = { "Context window (Claude's working memory)", "Your share of Claude today",
                                "Everyone's share this month" };
        GetClientRect(h, &r);
        gw = r.right - 80;
        SetBkMode(dc, TRANSPARENT);
        SelectObject(dc, GetStockObject(SYSTEM_FONT));
        for (i = 0; i < 3; i++) {
            int y = 30 + i * 110;
            SetTextColor(dc, RGB(0, 0, 0));
            TextOut(dc, 40, y, lab[i], lstrlen(lab[i]));
            Gauge(dc, 40, y + 24, gw, 26, G[i * 2], G[i * 2 + 1]);
            SetTextColor(dc, RGB(0, 0, 0));
            if (i == 0) wsprintf(t, "%ld of %ld tokens", G[0], G[1]);
            else wsprintf(t, "$%ld.%05ld of $%ld.%02ld", G[i * 2] / 100000L, G[i * 2] % 100000L,
                          G[i * 2 + 1] / 100000L, (G[i * 2 + 1] % 100000L) / 1000);
            TextOut(dc, 40, y + 56, t, lstrlen(t));
        }
        SetRect(&r, 40, 360, r.right - 40, r.bottom - 10);
        DrawText(dc, UsageText, -1, &r, DT_LEFT | DT_WORDBREAK | DT_EXPANDTABS);
        EndPaint(h, &ps);
        return 0;
    }
    return DefWindowProc(h, m, w, l);
}

void SetUsage(LPSTR p)                   /* "ctx|ctxmax|day|daycap|month|monthcap|text" ($ in 1e-5) */
{
    int i;
    char *q = p, *s;
    for (i = 0; i < 6 && q; i++) { G[i] = atol(q); s = strchr(q, '|'); q = s ? s + 1 : NULL; }
    lstrcpyn(UsageText, q ? q : "", sizeof UsageText);
    { char *c; for (c = UsageText; *c; c++) if (*c == '~') *c = '\n'; }
    InvalidateRect(hUsage, NULL, TRUE);
    UpdateWindow(hUsage);
}

/* ================================================================ Settings: the Mouse applet's controls */

static char *Effort[5] = { "low", "medium", "high", "xhigh", "max" };
static char *Length[3] = { "brief", "normal", "full" };
static char SetNow[60];

void Retitle(HWND g, LPCSTR t)           /* a group box draws its title over its parent: clear that first */
{
    RECT r;
    POINT a;
    GetWindowRect(g, &r);
    a.x = r.left; a.y = r.top;
    ScreenToClient(GetParent(g), &a);
    SetWindowText(g, t);
    SetRect(&r, a.x, a.y, a.x + (r.right - r.left), a.y + 18);
    InvalidateRect(GetParent(g), &r, TRUE);
    InvalidateRect(g, NULL, TRUE);
    UpdateWindow(GetParent(g));
}

void SettingsSend(int force)
{
    static char t[60];
    int e = GetScrollPos(sEffort, SB_CTL), n = GetScrollPos(sLength, SB_CTL);
    wsprintf(t, "%s|%s|%s|%s", (LPSTR)Effort[e], (LPSTR)Length[n],
             (LPSTR)(SendMessage(bAsk, BM_GETCHECK, 0, 0L) ? "ask" : "auto"),
             (LPSTR)(SendMessage(bModel, BM_GETCHECK, 0, 0L) ? "sonnet" : "haiku"));
    if (!force && !lstrcmp(t, SetNow)) return;
    lstrcpy(SetNow, t);
    {
        static char g[60];
        wsprintf(g, "&Effort:  %s", (LPSTR)Effort[e]);
        Retitle(gEffort, g);
        wsprintf(g, "&Answers:  %s", (LPSTR)Length[n]);
        Retitle(gLength, g);
    }
    Send('E', t, NULL, NULL);
    {
        static char b[200];
        wsprintf(b, "Effort %s, answers %s.\r\n%s before running commands.\r\nModel: Claude %s.",
                 (LPSTR)Effort[e], (LPSTR)Length[n],
                 (LPSTR)(SendMessage(bAsk, BM_GETCHECK, 0, 0L) ? "Asks" : "Doesn't ask"),
                 (LPSTR)(SendMessage(bModel, BM_GETCHECK, 0, 0L) ? "Sonnet 5.5" : "Haiku 5.5"));
        SetCard(4, b);
    }
}

long FAR PASCAL __export PaneProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_HSCROLL) {               /* the sliders report to us now, not to Control Panel */
        HWND sb = (HWND)HIWORD(l);
        int lo, hi, p;
        if (!sb || (sb != sEffort && sb != sLength)) return 0;
        p = GetScrollPos(sb, SB_CTL);
        GetScrollRange(sb, SB_CTL, &lo, &hi);
        switch (w) {
        case SB_LINEUP: case SB_PAGEUP: p--; break;
        case SB_LINEDOWN: case SB_PAGEDOWN: p++; break;
        case SB_THUMBPOSITION: case SB_THUMBTRACK: p = LOWORD(l); break;
        case SB_TOP: p = lo; break;
        case SB_BOTTOM: p = hi; break;
        }
        if (p < lo) p = lo;
        if (p > hi) p = hi;
        SetScrollPos(sb, SB_CTL, p, TRUE);
        SettingsSend(0);
        return 0;
    }
    if (m == WM_COMMAND) {               /* the check boxes too */
        HWND b = (HWND)LOWORD(l);
        if ((b == bAsk || b == bModel) && HIWORD(l) == BN_CLICKED) SettingsSend(0);   /* they check themselves */
        return 0;
    }
    if (m == WM_CTLCOLOR) {
        SetBkColor((HDC)w, GetSysColor(COLOR_BTNFACE));
        return (long)(WORD)GetStockObject(LTGRAY_BRUSH);
    }
    return DefWindowProc(h, m, w, l);
}

void Relabel(HWND d, HWND into, int id, LPCSTR text, int x, int y, int w, int h)
{
    HWND c = GetDlgItem(d, id);
    if (!c) return;
    if (text) SetWindowText(c, text);
    SetParent(c, into);
    MoveWindow(c, x, y, w, h, TRUE);
    ShowWindow(c, SW_SHOWNA);
}

HWND KidText(HWND d, LPCSTR text)        /* a dialog control by its words (statics have id -1) */
{
    HWND h;
    char t[40];
    for (h = GetWindow(d, GW_CHILD); h; h = GetWindow(h, GW_HWNDNEXT)) {
        GetWindowText(h, t, sizeof t);
        if (!lstrcmp(t, text)) return h;
    }
    return NULL;
}

void Move(HWND c, HWND into, LPCSTR text, int x, int y, int w, int h)
{
    if (!c) return;
    if (text) SetWindowText(c, text);
    SetParent(c, into);
    MoveWindow(c, x, y, w, h, TRUE);
    ShowWindow(c, SW_SHOWNA);
}

void BuildSettings(void)                 /* Control Panel's Mouse dialog, its parts moved onto our pane */
{
    HWND g1, g2, s1, f1, s2, f2, test;
    int x = 40, y = 30, w = 420;
    g1 = KidText(hCpl, "&Mouse Tracking Speed");
    g2 = KidText(hCpl, "&Double Click Speed");
    s1 = KidText(hCpl, "Slow"); f1 = KidText(hCpl, "Fast");
    sEffort = GetDlgItem(hCpl, 532);
    Move(g1, hSet, "&Effort  (how hard Claude thinks)", x, y, w, 96);
    Move(s1, hSet, "low", x + 12, y + 22, 60, 16);
    Move(f1, hSet, "max", x + w - 52, y + 22, 40, 16);
    Move(sEffort, hSet, NULL, x + 12, y + 40, w - 24, 20);
    s2 = KidText(hCpl, "Slow"); f2 = KidText(hCpl, "Fast");
    sLength = GetDlgItem(hCpl, 531);
    test = KidText(hCpl, "TEST");
    tEffortWord = GetDlgItem(hCpl, 529);
    Move(g2, hSet, "&Answers  (how much Claude writes)", x, y + 120, w, 96);
    Move(s2, hSet, "brief", x + 12, y + 142, 60, 16);
    Move(f2, hSet, "full", x + w - 52, y + 142, 40, 16);
    Move(sLength, hSet, NULL, x + 12, y + 160, w - 24, 20);
    if (test) ShowWindow(test, SW_HIDE);
    if (tEffortWord) ShowWindow(tEffortWord, SW_HIDE);
    gEffort = g1; gLength = g2;
    bAsk = GetDlgItem(hCpl, 500);
    bModel = GetDlgItem(hCpl, 509);
    Move(bAsk, hSet, "&Ask before running commands", x, y + 246, w, 22);
    EnableWindow(bModel, TRUE);
    Move(bModel, hSet, "Use Claude &Sonnet 5.5  (smarter, slower, dearer)", x, y + 276, w + 120, 22);
    SetScrollRange(sEffort, SB_CTL, 0, 4, FALSE);
    SetScrollPos(sEffort, SB_CTL, 0, TRUE);
    SetScrollRange(sLength, SB_CTL, 0, 2, FALSE);
    SetScrollPos(sLength, SB_CTL, 1, TRUE);
    SetWindowLong(bAsk, GWL_STYLE, (GetWindowLong(bAsk, GWL_STYLE) & ~0x0FL) | BS_AUTOCHECKBOX);   /* Swap was a plain check box */
    SetWindowLong(bModel, GWL_STYLE, (GetWindowLong(bModel, GWL_STYLE) & ~0x0FL) | BS_AUTOCHECKBOX);
    SendMessage(bAsk, BM_SETCHECK, 1, 0L);
    SendMessage(bModel, BM_SETCHECK, 0, 0L);
}

/* ================================================================ the mouse (server version: sent over the link) */

static HWND capW, dragW;
static int dragBar, dragLo, dragLen;
static DWORD lastDn;
static int lastX, lastY;

/* a scroll bar is driven by its messages, not by a posted click (its tracking loop polls the real button) */
void ScrollMsg(HWND w, int bar, int code, int pos)
{
    HWND to = bar == SB_CTL ? GetParent(w) : w;
    int vert = bar == SB_CTL ? (int)(GetWindowLong(w, GWL_STYLE) & SBS_VERT) : bar == SB_VERT;
    UINT m = vert ? WM_VSCROLL : WM_HSCROLL;
    SendMessage(to, m, code, MAKELPARAM(pos, bar == SB_CTL ? w : 0));
    if (code != SB_THUMBTRACK) SendMessage(to, m, SB_ENDSCROLL, MAKELPARAM(0, bar == SB_CTL ? w : 0));
}

int ScrollPos(int at)                    /* where along the dragged bar the pointer is, in its range */
{
    int lo, hi;
    GetScrollRange(dragW, dragBar, &lo, &hi);
    if (dragLen <= 0) return lo;
    if (at < 0) at = 0;
    if (at > dragLen) at = dragLen;
    return lo + (int)(((long)(hi - lo) * at + dragLen / 2) / dragLen);
}

void ScrollClick(HWND w, int bar, int x, int y)
{
    RECT r;
    int vert, a, from, to, at, lo, hi, pos, len, thumb, tpos;
    if (bar == SB_CTL) { GetWindowRect(w, &r); vert = (int)(GetWindowLong(w, GWL_STYLE) & SBS_VERT); }
    else {
        POINT o;
        GetClientRect(w, &r);
        o.x = o.y = 0;
        ClientToScreen(w, &o);
        OffsetRect(&r, o.x, o.y);
        vert = bar == SB_VERT;
    }
    a = vert ? GetSystemMetrics(SM_CYVSCROLL) : GetSystemMetrics(SM_CXHSCROLL);
    from = vert ? r.top : r.left;
    to = vert ? r.bottom : r.right;
    at = vert ? y : x;
    GetScrollRange(w, bar, &lo, &hi);
    pos = GetScrollPos(w, bar);
    thumb = a;
    len = to - from - 2 * a - thumb;
    tpos = from + a + (hi > lo ? (int)((long)len * (pos - lo) / (hi - lo)) : 0);
    if (at < from + a) ScrollMsg(w, bar, SB_LINEUP, 0);
    else if (at >= to - a) ScrollMsg(w, bar, SB_LINEDOWN, 0);
    else if (at < tpos) ScrollMsg(w, bar, SB_PAGEUP, 0);
    else if (at >= tpos + thumb) ScrollMsg(w, bar, SB_PAGEDOWN, 0);
    else { dragW = w; dragBar = bar; dragLo = from + a + (at - tpos); dragLen = len; }
}

void Mouse(LPSTR p)                      /* "x|y|b|down"  b: 0 move, 1 left, 2 right */
{
    int x = atoi(p), y, b, down, ht;
    char *q = strchr(p, '|'), cls[16];
    POINT pt, c;
    HWND w;
    if (!q) return;
    y = atoi(++q); q = strchr(q, '|'); b = q ? atoi(++q) : 0; q = q ? strchr(q, '|') : NULL; down = q ? atoi(++q) : 0;
    SetCursorPos(x, y);
    pt.x = x; pt.y = y;
    if (dragW) {                         /* a scroll box being dragged */
        int v = (dragBar == SB_VERT || (dragBar == SB_CTL && (GetWindowLong(dragW, GWL_STYLE) & SBS_VERT))) ? y : x;
        int at = ScrollPos(v - dragLo);
        if (b == 1 && !down) { ScrollMsg(dragW, dragBar, SB_THUMBPOSITION, at); dragW = NULL; }
        else ScrollMsg(dragW, dragBar, SB_THUMBTRACK, at);
        return;
    }
    if (b && down) capW = NULL;          /* a new press starts afresh, whatever became of the last release */
    w = capW ? capW : WindowFromPoint(pt);
    if (b && !down) capW = NULL;
    if (!w) return;
    c = pt;
    ScreenToClient(w, &c);
    if (b == 0) { PostMessage(w, WM_MOUSEMOVE, capW ? MK_LBUTTON : 0, MAKELPARAM(c.x, c.y)); return; }
    if (!capW && !Browser && w == hText) return;   /* Terminal would start a selection nobody can use */
    ht = (int)SendMessage(w, WM_NCHITTEST, 0, MAKELPARAM(x, y));
    GetClassName(w, cls, sizeof cls);
    if (!capW && b == 1 && down && !lstrcmpi(cls, "ScrollBar")) { ScrollClick(w, SB_CTL, x, y); return; }
    if (!capW && b == 1 && down && (ht == HTVSCROLL || ht == HTHSCROLL)) {
        ScrollClick(w, ht == HTVSCROLL ? SB_VERT : SB_HORZ, x, y);
        return;
    }
    if (ht == HTCLIENT || (b == 1 && !down)) {
        UINT msg;
        if (b == 1 && down) {
            int dbl = (long)(GetTickCount() - lastDn) < 500 && abs(x - lastX) < 4 && abs(y - lastY) < 4 &&
                      (GetClassWord(w, GCW_STYLE) & CS_DBLCLKS);
            lastDn = dbl ? 0 : GetTickCount(); lastX = x; lastY = y;
            msg = dbl ? WM_LBUTTONDBLCLK : WM_LBUTTONDOWN;
            capW = w;
        } else if (b == 1) msg = WM_LBUTTONUP;
        else msg = down ? WM_RBUTTONDOWN : WM_RBUTTONUP;
        PostMessage(w, msg, (b == 1 && down) ? MK_LBUTTON : 0, MAKELPARAM(c.x, c.y));
    }
}

void Wheel(int n)                        /* the wheel scrolls whatever is under the pointer */
{
    POINT pt;
    HWND w;
    GetCursorPos(&pt);
    w = WindowFromPoint(pt);
    if (Tab == 0 || !w) { static char t[8]; wsprintf(t, "%d", n * 3); Scroll(t); return; }
    for (; n; n += n < 0 ? 1 : -1) {
        int i;
        for (i = 0; i < 3; i++) SendMessage(w, WM_VSCROLL, n < 0 ? SB_LINEUP : SB_LINEDOWN, 0L);
    }
    SendMessage(w, WM_VSCROLL, SB_ENDSCROLL, 0L);
}

/* ================================================================ diagnostics: the window tree, to C:\B3\SPY.TXT */

HFILE spyF;
void SpyTree(HWND w, int depth)
{
    static char line[200], c[32], t[40];
    RECT r;
    for (; w; w = GetWindow(w, GW_HWNDNEXT)) {
        GetClassName(w, c, sizeof c);
        GetWindowText(w, t, sizeof t);
        GetWindowRect(w, &r);
        wsprintf(line, "%s%04X %s \"%s\" id=%d st=%08lX vis=%d %d,%d-%d,%d\r\n", (LPSTR)("        " + 8 - depth * 2), (WORD)w,
                 (LPSTR)c, (LPSTR)t, GetWindowWord(w, GWW_ID), GetWindowLong(w, GWL_STYLE), IsWindowVisible(w),
                 r.left, r.top, r.right, r.bottom);
        _lwrite(spyF, line, lstrlen(line));
        if (depth < 3) SpyTree(GetWindow(w, GW_CHILD), depth + 1);
    }
}

void Spy(void)
{
    OFSTRUCT of;
    spyF = OpenFile("C:\\B3\\SPY.TXT", &of, OF_CREATE | OF_WRITE);
    if (spyF == HFILE_ERROR) return;
    SpyTree(GetWindow(GetDesktopWindow(), GW_CHILD), 0);
    _lclose(spyF);
}

