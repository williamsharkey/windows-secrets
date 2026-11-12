/* VAL.EXE - a valentine assembled from Windows for Workgroups 3.11's own parts.
 *
 *   the message     a real Cardfile card (Cardfile's index line and card text)
 *   the heart       twenty-six hearts from Solitaire's CARDS.DLL, dealt along a heart curve
 *   the time        a real Clock window, ticking
 *
 * It waits on COM1 for jobs from the host:   JOB id / T:to / M:message / F:from / S:style / END
 * then sets the card, repaints everything, and answers READY id; the host takes the picture.
 *
 * Build (host):  wcl -q -bt=windows -l=windows -ml val.c
 */
#include <windows.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define SW 1024
#define SH 768
#define CARD_X (SW / 2 - 210)
#define CARD_Y 214
#define CARD_W 420
#define CARD_H 272

typedef BOOL (FAR PASCAL *CDTINIT)(int FAR *, int FAR *);
typedef BOOL (FAR PASCAL *CDTDRAW)(HDC, int, int, int, int, DWORD);
static CDTINIT cdtInit;
static CDTDRAW cdtDraw;
static int cardW = 71, cardH = 96;

static HWND hBack, hCard, hCardEdit, hClock;
static HINSTANCE hInst;
static int comm = -1;
static char rx[2048];
static int nrx;

/* the job being composed */
static char jobId[40], jTo[64], jMsg[600], jFrom[64];
static int jStyle;
static int collecting;
void on_line(const char FAR *l);

/* ---------------------------------------------------------------- helpers */
static void pump(DWORD ms)
{
    DWORD end = GetTickCount() + ms;
    MSG m;
    do {
        while (PeekMessage(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessage(&m); }
        Yield();
    } while (GetTickCount() < end);
}

static void say(const char *s)
{
    if (comm >= 0) WriteComm(comm, s, strlen(s));
}

typedef struct { HINSTANCE inst; const char *prefix; HWND found; } FINDW;
static FINDW fw;
BOOL FAR PASCAL __export FindProc(HWND h, LPARAM lp)
{
    char t[80];
    (void)lp;
    if (fw.inst && (HINSTANCE)GetWindowWord(h, GWW_HINSTANCE) != fw.inst) return TRUE;
    if (GetParent(h)) return TRUE;
    if (!IsWindowVisible(h)) return TRUE;
    GetWindowText(h, t, sizeof t);
    if (fw.prefix && _fstrncmp(t, fw.prefix, strlen(fw.prefix))) return TRUE;
    fw.found = h;
    return FALSE;
}
static HWND find_top(HINSTANCE inst, const char *prefix, DWORD ms)
{
    FARPROC p = MakeProcInstance((FARPROC)FindProc, hInst);
    DWORD end = GetTickCount() + ms;
    fw.found = NULL;
    do {
        fw.inst = inst; fw.prefix = prefix; fw.found = NULL;
        EnumWindows((WNDENUMPROC)p, 0);
        if (fw.found) break;
        pump(50);
    } while (GetTickCount() < end);
    FreeProcInstance(p);
    return fw.found;
}

/* a menu command by its text, e.g. ("Edit", "Index") */
static UINT menu_id(HWND h, const char *top, const char *item)
{
    HMENU m = GetMenu(h), sub;
    char t[64];
    int i, j, n, k;
    if (!m) return 0;
    n = GetMenuItemCount(m);
    for (i = 0; i < n; i++) {
        GetMenuString(m, i, t, sizeof t, MF_BYPOSITION);
        if (!strstr(t, top)) continue;
        sub = GetSubMenu(m, i);
        k = GetMenuItemCount(sub);
        for (j = 0; j < k; j++) {
            GetMenuString(sub, j, t, sizeof t, MF_BYPOSITION);
            if (strstr(t, item)) return GetMenuItemID(sub, j);
        }
    }
    return 0;
}

static HWND first_child(HWND h, const char *cls)
{
    HWND c = GetWindow(h, GW_CHILD), d;
    char t[32];
    while (c) {
        GetClassName(c, t, sizeof t);
        if (!lstrcmpi(t, cls)) return c;
        if ((d = first_child(c, cls)) != NULL) return d;
        c = GetWindow(c, GW_HWNDNEXT);
    }
    return NULL;
}

/* ---------------------------------------------------------------- the heart */
typedef struct { int x, y; } PT;
static PT pts[40];
static int npts;
static int rank_of[40];

static void heart_xy(double t, double *x, double *y)
{
    double s = sin(t);
    *x = 16.0 * s * s * s;
    *y = -(13.0 * cos(t) - 5.0 * cos(2 * t) - 2.0 * cos(3 * t) - cos(4 * t));
}

/* 13 points down the right half by equal arc length, mirrored to the left */
static void heart_points(int cx, int cy, double sx, double sc)
{
    double len[401], total, x0, y0, x, y;
    int i, k;
    heart_xy(0, &x0, &y0);
    len[0] = 0;
    for (i = 1; i <= 400; i++) {
        heart_xy(3.14159265 * i / 400, &x, &y);
        len[i] = len[i - 1] + sqrt((x - x0) * (x - x0) + (y - y0) * (y - y0));
        x0 = x; y0 = y;
    }
    total = len[400];
    /* 2..Queen down each side, the Ace at the cusp, the King at the tip */
    npts = 0;
    for (k = 0; k < 11; k++) {
        double want = total * (k + 1) / 12.0;
        for (i = 1; i < 400 && len[i] < want; i++) ;
        heart_xy(3.14159265 * i / 400, &x, &y);
        pts[npts].x = cx + (int)(x * sx); pts[npts].y = cy + (int)(y * sc); rank_of[npts] = k + 1; npts++;
    }
    for (k = 0; k < 11; k++) {
        pts[npts].x = 2 * cx - pts[k].x; pts[npts].y = pts[k].y; rank_of[npts] = k + 1; npts++;
    }
    pts[npts].x = cx; pts[npts].y = cy - (int)(5.0 * sc) - 40; rank_of[npts] = 0; npts++;   /* clear of Cardfile's top edge */
    heart_xy(3.14159265, &x, &y);
    pts[npts].x = cx; pts[npts].y = cy + (int)(y * sc); rank_of[npts] = 12; npts++;
}

static COLORREF bgTop[3] = {RGB(92, 10, 40), RGB(0, 96, 96), RGB(16, 16, 56)};
static COLORREF bgBot[3] = {RGB(170, 40, 80), RGB(0, 150, 140), RGB(70, 30, 110)};

static void paint_back(HDC dc)
{
    int i, bands = 96;
    RECT r;
    HBRUSH b;
    COLORREF a = bgTop[jStyle], z = bgBot[jStyle];
    for (i = 0; i < bands; i++) {
        int rr = (int)((long)GetRValue(a) + ((long)GetRValue(z) - GetRValue(a)) * i / (bands - 1));
        int gg = (int)((long)GetGValue(a) + ((long)GetGValue(z) - GetGValue(a)) * i / (bands - 1));
        int bb = (int)((long)GetBValue(a) + ((long)GetBValue(z) - GetBValue(a)) * i / (bands - 1));
        SetRect(&r, 0, (int)((long)SH * i / bands), SW, (int)((long)SH * (i + 1) / bands));
        b = CreateSolidBrush(RGB(rr, gg, bb));
        FillRect(dc, &r, b);
        DeleteObject(b);
    }
    if (cdtDraw) {
        /* deal the hearts: Ace to King down each side, the lower cards on top */
        int order[40], i2, j, k;
        for (i2 = 0; i2 < npts; i2++) order[i2] = i2;
        for (i2 = 0; i2 < npts; i2++) for (j = i2 + 1; j < npts; j++)
            if (pts[order[j]].y < pts[order[i2]].y) { k = order[i2]; order[i2] = order[j]; order[j] = k; }
        for (i2 = 0; i2 < npts; i2++) {
            int n = order[i2], rank = rank_of[n];
            RECT c, w, x;
            SetRect(&c, pts[n].x - cardW / 2, pts[n].y - cardH / 2, pts[n].x + cardW / 2, pts[n].y + cardH / 2);
            SetRect(&w, CARD_X - 4, CARD_Y - 4, CARD_X + CARD_W + 4, CARD_Y + CARD_H + 4);
            /* the heart runs behind Cardfile: a card that would touch the window is not dealt at all,
               so every card on screen is whole and the gap is the same on both sides */
            if (IntersectRect(&x, &c, &w)) continue;
            cdtDraw(dc, c.left, c.top, rank * 4 + 2, 0, 0);
        }
    }
    {   /* a quiet credit line, in the system font */
        static const char *credit = "Assembled in Windows for Workgroups 3.11 from Cardfile, Clock and Solitaire's own cards";
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, RGB(255, 220, 230));
        SetRect(&r, 0, SH - 30, SW, SH - 8);
        DrawText(dc, credit, -1, &r, DT_CENTER | DT_SINGLELINE | DT_VCENTER);
    }
}

LRESULT FAR PASCAL __export BackProc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    switch (m) {
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(h, &ps);
        paint_back(dc);
        EndPaint(h, &ps);
        return 0;
    }
    case WM_ERASEBKGND: return 1;
    case WM_TIMER: {
        int n, err;
        COMSTAT cs;
        if (comm < 0) return 0;
        err = GetCommError(comm, &cs);
        (void)err;
        n = ReadComm(comm, rx + nrx, sizeof rx - 1 - nrx);
        if (n < 0) n = -n;
        nrx += n;
        rx[nrx] = 0;
        {
            char *nl;
            while ((nl = strchr(rx, '\n')) != NULL) {
                char line[700];
                int len = (int)(nl - rx);
                if (len > (int)sizeof line - 1) len = sizeof line - 1;
                memcpy(line, rx, len); line[len] = 0;
                if (len && line[len - 1] == '\r') line[len - 1] = 0;
                memmove(rx, nl + 1, nrx - (int)(nl - rx) - 1 + 1);
                nrx -= (int)(nl - rx) + 1;
                if (nrx < 0) nrx = 0;
                PostMessage(h, WM_USER + 1, 0, (LPARAM)(LPSTR)strdup(line));
            }
            if (nrx >= (int)sizeof rx - 2) nrx = 0;
        }
        return 0;
    }
    case WM_USER + 1: {
        char FAR *line = (char FAR *)lp;
        on_line(line);
        free(line);
        return 0;
    }
    }
    return DefWindowProc(h, m, wp, lp);
}

/* ---------------------------------------------------------------- the parts */
static void dbg(const char *fmt, int a, int b)
{
    char t[120];
    sprintf(t, "DBG ");
    sprintf(t + 4, fmt, a, b);
    strcat(t, "\r\n");
    say(t);
}
static void dump_tree(HWND h, int depth)
{
    HWND c = GetWindow(h, GW_CHILD);
    char t[40], line[160], tx[40];
    RECT r;
    while (c) {
        GetClassName(c, t, sizeof t);
        GetWindowText(c, tx, sizeof tx);
        GetWindowRect(c, &r);
        sprintf(line, "DBG %d %u %s vis=%d %d,%d %dx%d id=%d '%s'\r\n", depth, (unsigned)c, t, IsWindowVisible(c),
                r.left, r.top, r.right - r.left, r.bottom - r.top, GetDlgCtrlID(c), tx);
        say(line);
        pump(30);
        dump_tree(c, depth + 1);
        c = GetWindow(c, GW_HWNDNEXT);
    }
}
/* type into a control the way a person would: one WM_CHAR at a time */
static void type_into(HWND e, const char *t)
{
    for (; *t; t++) {
        if (*t == '\n') continue;
        /* SendMessage, not PostMessage: a Windows 3.1 queue holds only 8 messages */
        SendMessage(e, WM_CHAR, (WPARAM)(unsigned char)*t, 1L);
    }
    pump(80);
}
static void clear_edit(HWND e)
{
    SendMessage(e, EM_SETSEL, 0, MAKELPARAM(0, 32767));
    SendMessage(e, WM_CLEAR, 0, 0);
}
static void set_index(const char *text)
{
    UINT id = menu_id(hCard, "Edit", "Index");
    HWND dlg, e;
    DWORD end;
    if (!id) return;
    PostMessage(hCard, WM_COMMAND, id, 0);
    end = GetTickCount() + 3000;
    dlg = NULL;
    while (!dlg && GetTickCount() < end) {
        HWND a;
        pump(40);
        a = GetActiveWindow();
        if (a && a != hCard && GetWindow(a, GW_OWNER) == hCard) dlg = a;
    }
    dbg("index id=%u dlg=%u", (int)id, (int)dlg);
    if (!dlg) return;
    e = first_child(dlg, "Edit");
    if (e) {
        SetWindowLong(e, GWL_STYLE, GetWindowLong(e, GWL_STYLE) | ES_AUTOHSCROLL);   /* a long name may scroll */
        SetFocus(e); clear_edit(e); type_into(e, text);
    }
    PostMessage(dlg, WM_COMMAND, IDOK, 0);
    pump(300);
}

static void place_parts(void)
{
    /* Cardfile in the middle of the heart, Clock at the cusp */
    if (hCard) SetWindowPos(hCard, NULL, CARD_X, CARD_Y, CARD_W, CARD_H, SWP_NOZORDER | SWP_NOACTIVATE);
    /* wide enough for Clock's own caption, "Clock - mm/dd/yy", beside its buttons */
    if (hClock) SetWindowPos(hClock, NULL, SW - 236, SH - 276, 212, 232, SWP_NOZORDER | SWP_NOACTIVATE);
}

static void settle_and_report(void)
{
    char out[64];
    SetCursorPos(SW - 1, SH - 1);
    RedrawWindow(GetDesktopWindow(), NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_ALLCHILDREN | RDW_UPDATENOW);
    pump(600);
    if (hCard) UpdateWindow(hCard);
    if (hClock) UpdateWindow(hClock);
    pump(400);
    sprintf(out, "READY %s\r\n", jobId);
    say(out);
}

static void compose(void)
{
    char idx[64], body[700];
    InvalidateRect(hBack, NULL, FALSE);
    if (jTo[0]) sprintf(idx, "To %s", jTo); else strcpy(idx, "To you");
    set_index(idx);
    strcpy(body, jMsg);
    if (jFrom[0]) { strcat(body, "\r\n\r\n                      - "); strcat(body, jFrom); }
    dbg("card=%u edit=%u", (int)hCard, (int)hCardEdit);
    if (hCardEdit) { SetFocus(hCardEdit); clear_edit(hCardEdit); type_into(hCardEdit, body); }

    if (hCard) {
        char t[80];
        sprintf(t, "Cardfile - VALENTIN.CRD");
        SetWindowText(hCard, t);
        SetActiveWindow(hCard);
        SetFocus(hCard);
    }
    if (hCardEdit) SendMessage(hCardEdit, EM_SETSEL, 0, MAKELPARAM(0, 0));
    /* no keyboard focus anywhere, so no caret in the picture; Cardfile still draws itself active */
    SetFocus(NULL);
    if (hCard) SendMessage(hCard, WM_NCACTIVATE, TRUE, 0L);
    place_parts();
    settle_and_report();
}

void on_line(const char FAR *l)
{
    if (!_fstrncmp(l, "JOB ", 4)) {
        _fstrncpy(jobId, l + 4, sizeof jobId - 1); jobId[sizeof jobId - 1] = 0;
        jTo[0] = jMsg[0] = jFrom[0] = 0; jStyle = 0; collecting = 1;
    } else if (collecting && !_fstrncmp(l, "T:", 2)) {
        _fstrncpy(jTo, l + 2, sizeof jTo - 1); jTo[sizeof jTo - 1] = 0;
    } else if (collecting && !_fstrncmp(l, "M:", 2)) {
        char *q;
        _fstrncpy(jMsg, l + 2, sizeof jMsg - 1); jMsg[sizeof jMsg - 1] = 0;
        /* \x01 marks a line break; the card wants CR LF */
        {
            char tmp[700], *p, *o = tmp;
            for (p = jMsg; *p && o < tmp + sizeof tmp - 3; p++) {
                if (*p == 1) { *o++ = '\r'; *o++ = '\n'; } else *o++ = *p;
            }
            *o = 0;
            strcpy(jMsg, tmp);
        }
        (void)q;
    } else if (collecting && !_fstrncmp(l, "F:", 2)) {
        _fstrncpy(jFrom, l + 2, sizeof jFrom - 1); jFrom[sizeof jFrom - 1] = 0;
    } else if (collecting && !_fstrncmp(l, "S:", 2)) {
        jStyle = (l[2] - '0') % 3;
        if (jStyle < 0) jStyle = 0;
    } else if (collecting && !_fstrcmp(l, "END")) {
        collecting = 0;
        compose();
    } else if (!_fstrcmp(l, "PING")) {
        say("PONG\r\n");
    }
}

int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cl, int show)
{
    WNDCLASS wc;
    MSG m;
    HINSTANCE ci, ki;
    DCB dcb;
    HINSTANCE lib;
    (void)hp; (void)cl; (void)show;
    hInst = hi;

    lib = LoadLibrary("CARDS.DLL");
    if ((UINT)lib > 32) {
        cdtInit = (CDTINIT)GetProcAddress(lib, "cdtInit");
        cdtDraw = (CDTDRAW)GetProcAddress(lib, "cdtDraw");
        if (cdtInit) cdtInit(&cardW, &cardH);
    }
    heart_points(SW / 2, 296, 23.0, 19.5);

    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = BackProc;
    wc.hInstance = hi;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.lpszClassName = "ValBack";
    RegisterClass(&wc);
    hBack = CreateWindow("ValBack", "Valentine", WS_POPUP | WS_VISIBLE, 0, 0, SW, SH, NULL, NULL, hi, NULL);
    SetWindowPos(hBack, HWND_BOTTOM, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    UpdateWindow(hBack);

    /* Program Manager steps out of the way */
    {
        HWND pm = FindWindow("Progman", NULL);
        if (pm) ShowWindow(pm, SW_HIDE);
    }
    ci = WinExec("CARDFILE.EXE", SW_SHOWNORMAL);
    hCard = find_top(ci, "Cardfile", 8000);
    if (hCard) hCardEdit = first_child(hCard, "Edit");
    ki = WinExec("CLOCK.EXE", SW_SHOWNOACTIVATE);
    hClock = find_top(ki, "Clock", 8000);
    if (hClock) {
        UINT id = menu_id(hClock, "Settings", "Analog");
        if (id) PostMessage(hClock, WM_COMMAND, id, 0);
    }
    place_parts();
    SetCursorPos(SW - 1, SH - 1);

    comm = OpenComm("COM1", 4096, 1024);
    if (comm >= 0) {
        BuildCommDCB("COM1:9600,n,8,1", &dcb);
        SetCommState(&dcb);
        say("HELLO\r\n");
    }
    SetTimer(hBack, 1, 100, NULL);

    while (GetMessage(&m, NULL, 0, 0)) { TranslateMessage(&m); DispatchMessage(&m); }
    if (comm >= 0) CloseComm(comm);
    return 0;
}
