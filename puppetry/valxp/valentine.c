/* XP VALENTINE - a valentine assembled from Windows XP's own parts.
 *
 *   valentine.exe <jobfile>      jobfile (UTF-8): line 1 to, line 2 from, rest = message
 *
 * Calculator's keys are lifted out of Calculator and stand in a heart; Notepad holds the
 * letter inside it. Every part is a real window painted by the program that made it.
 * Nothing visible is ever moved: each part is hidden, placed, and only then shown, and the
 * whole screen is repainted and left to settle before the host takes the picture.
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#define PI 3.14159265358979
#define HCY 361     /* the heart's centre line; the picture is cropped around it */
static int SW, SH;
static FILE *lg;
static void say(const char *f, ...)
{
    va_list a;
    if (!lg) lg = fopen("C:\\p\\valentine.log", "w");
    va_start(a, f); vfprintf(lg, f, a); va_end(a);
    fputc('\n', lg); fflush(lg);
}

/* ---- the job --------------------------------------------------------------------------- */
static WCHAR to_[128], from_[128], msg[1024];
static int read_job(const char *path)
{
    FILE *f = fopen(path, "rb");
    char buf[4096];
    int n;
    WCHAR w[4096], *p, *e;
    if (!f) return 0;
    n = (int)fread(buf, 1, sizeof buf - 1, f);
    fclose(f);
    buf[n] = 0;
    n = MultiByteToWideChar(CP_UTF8, 0, buf, -1, w, 4096);
    p = w;
    e = wcschr(p, L'\n'); if (!e) return 0; *e = 0; lstrcpynW(to_, p, 128); p = e + 1;
    e = wcschr(p, L'\n'); if (!e) return 0; *e = 0; lstrcpynW(from_, p, 128); p = e + 1;
    {   /* \n -> \r\n, trim the tail */
        WCHAR *q = msg;
        for (; *p && q < msg + 1000; p++) {
            if (*p == L'\r') continue;
            if (*p == L'\n') *q++ = L'\r';
            *q++ = *p;
        }
        while (q > msg && (q[-1] == L'\r' || q[-1] == L'\n' || q[-1] == L' ')) q--;
        *q = 0;
    }
    return 1;
}

/* ---- window helpers -------------------------------------------------------------------- */
typedef struct { const char *cls; DWORD pid; HWND found; } FT;
static BOOL CALLBACK ft_cb(HWND h, LPARAM lp)
{
    FT *f = (FT *)lp; char c[64]; DWORD pid;
    GetClassNameA(h, c, sizeof c);
    if (strcmp(c, f->cls)) return TRUE;
    GetWindowThreadProcessId(h, &pid);
    if (f->pid && pid != f->pid) return TRUE;
    f->found = h; return FALSE;
}
static HWND wait_top(const char *cls, DWORD pid, int ms)
{
    DWORD end = GetTickCount() + ms;
    do {
        FT f = {cls, pid, NULL};
        EnumWindows(ft_cb, (LPARAM)&f);
        if (f.found) return f.found;
        Sleep(30);
    } while ((LONG)(GetTickCount() - end) < 0);
    return NULL;
}
static DWORD launch(const char *cl0, int show)
{
    STARTUPINFOA si; PROCESS_INFORMATION pi; char cl[256];
    memset(&si, 0, sizeof si); si.cb = sizeof si; si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = (WORD)show;
    lstrcpynA(cl, cl0, sizeof cl);
    if (!CreateProcessA(NULL, cl, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) return 0;
    WaitForInputIdle(pi.hProcess, 6000);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    return pi.dwProcessId;
}
static void reg_dw(HKEY k, const char *n, DWORD v) { RegSetValueExA(k, n, 0, REG_DWORD, (BYTE *)&v, 4); }

typedef struct { int id; HWND found; } FI;
static BOOL CALLBACK fi_cb(HWND h, LPARAM lp) { FI *f = (FI *)lp; if (GetDlgCtrlID(h) == f->id) { f->found = h; return FALSE; } return TRUE; }
static HWND kid_id(HWND p, int id) { FI f = {id, NULL}; EnumChildWindows(p, fi_cb, (LPARAM)&f); return f.found; }
static int overlaps(RECT a, RECT b) { return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom; }

/* ---- the heart ------------------------------------------------------------------------- */
/* classic heart curve, y down; t=0 at the top cleft */
static void heart(double t, double *x, double *y)
{
    double s = sin(t);
    *x = 16 * s * s * s;
    *y = -(13 * cos(t) - 5 * cos(2 * t) - 2 * cos(3 * t) - cos(4 * t));
}
/* n points evenly spaced by arc length, starting at the top cleft, clockwise */
static void heart_points(int n, double cx, double cy, double sx, double sy, POINT *out)
{
    enum { M = 4000 };
    static double px[M + 1], py[M + 1], len[M + 1];
    int i, k = 0;
    for (i = 0; i <= M; i++) {
        heart(2 * PI * i / M, &px[i], &py[i]);
        len[i] = i ? len[i - 1] + hypot(px[i] - px[i - 1], py[i] - py[i - 1]) : 0;
    }
    for (i = 0; i < n; i++) {
        double want = len[M] * i / n;
        while (k < M && len[k + 1] < want) k++;
        out[i].x = (LONG)(cx + px[k] * sx + .5);
        out[i].y = (LONG)(cy + py[k] * sy + .5);
    }
}

/* ---- the keys -------------------------------------------------------------------------- */
static HWND keys[128];
static int nkeys;
static BOOL CALLBACK key_cb(HWND h, LPARAM lp)
{
    char c[32];
    LONG st = GetWindowLongA(h, GWL_STYLE), t = st & 0xF;
    (void)lp;
    GetClassNameA(h, c, sizeof c);
    if (strcmp(c, "Button") || !(st & WS_VISIBLE)) return TRUE;
    if (t != BS_PUSHBUTTON && t != BS_DEFPUSHBUTTON) return TRUE;   /* only push keys: they paint themselves whole */
    {   /* the wide keys (Backspace, CE, C) would crowd the curve */
        RECT r; GetWindowRect(h, &r);
        if (r.right - r.left > 50) return TRUE;
    }
    if (nkeys < 128) keys[nkeys++] = h;
    return TRUE;
}

int WINAPI WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cl, int show)
{
    HKEY k;
    HWND calc, np, ed, tray, lv, paint, palette = NULL;
    int palette_y = 0;
    DWORD pid;
    int i, rose = RGB(196, 72, 104), elem = COLOR_BACKGROUND;
    POINT pts[128];
    WCHAR text[2048], title[256];
    RECT nr;
    (void)hi; (void)hp; (void)show;
    SW = GetSystemMetrics(SM_CXSCREEN); SH = GetSystemMetrics(SM_CYSCREEN);
    if (!read_job(cl)) { say("bad job %s", cl); return 1; }

    /* the room: a rose desktop, no taskbar, no icons, no pointer in the picture */
    SetSysColors(1, &elem, (COLORREF *)&rose);
    tray = FindWindowA("Shell_TrayWnd", NULL);
    if (tray) ShowWindow(tray, SW_HIDE);
    lv = FindWindowExA(FindWindowExA(FindWindowA("Progman", NULL), NULL, "SHELLDLL_DefView", NULL), NULL, "SysListView32", NULL);
    if (lv) ShowWindow(lv, SW_HIDE);
    SetCursorPos(SW - 1, SH - 1);

    /* Notepad's letter font: Times New Roman italic, 16 pt, wrapped */
    if (!RegCreateKeyExA(HKEY_CURRENT_USER, "Software\\Microsoft\\Notepad", 0, NULL, 0, KEY_ALL_ACCESS, NULL, &k, NULL)) {
        RegSetValueExA(k, "lfFaceName", 0, REG_SZ, (const BYTE *)"Times New Roman", 16);
        { int L = lstrlenW(msg); reg_dw(k, "iPointSize", L <= 140 ? 160 : L <= 200 ? 140 : 130); } reg_dw(k, "lfWeight", 400); reg_dw(k, "lfItalic", 1);
        reg_dw(k, "lfCharSet", 0); reg_dw(k, "fWrap", 1); reg_dw(k, "StatusBar", 0);
        RegCloseKey(k);
    }
    WriteProfileStringA("SciCalc", "layout", "0");     /* Calculator opens in Scientific view */

    /* Calculator, kept out of sight; its keys are what we want */
    pid = launch("calc.exe", SW_HIDE);
    calc = wait_top("SciCalc", pid, 8000);
    if (!calc) { say("no calc"); return 1; }
    ShowWindow(calc, SW_HIDE);
    EnumChildWindows(calc, key_cb, 0);
    say("calc keys %d", nkeys);

    /* Notepad, with the letter */
    pid = launch("notepad.exe", SW_HIDE);
    np = wait_top("Notepad", pid, 8000);
    if (!np) { say("no notepad"); return 1; }
    ed = FindWindowExA(np, NULL, "Edit", NULL);
    wsprintfW(text, L"Dear %s,\r\n\r\n%s\r\n\r\n\x2665 %s", to_, msg, from_);
    SendMessageW(ed, WM_SETTEXT, 0, (LPARAM)text);
    wsprintfW(title, L"For %s - Notepad", to_);
    SetWindowTextW(np, title);
    SetWindowLongA(ed, GWL_STYLE, GetWindowLongA(ed, GWL_STYLE) & ~(WS_VSCROLL | WS_HSCROLL));
    nr.left = SW / 2 - 200; nr.right = SW / 2 + 200; nr.top = 270; nr.bottom = 490;
    SetWindowPos(np, HWND_TOP, nr.left, nr.top, nr.right - nr.left, nr.bottom - nr.top, SWP_NOACTIVATE | SWP_FRAMECHANGED);
    SetWindowPos(ed, NULL, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED);
    {   /* height to fit the letter */
        int lines = (int)SendMessageW(ed, EM_GETLINECOUNT, 0, 0), lh = 24, chrome, want;
        RECT wr, cr;
        LRESULT p0 = SendMessageW(ed, EM_POSFROMCHAR, 0, 0), p1;
        if (lines > 1) {
            p1 = SendMessageW(ed, EM_POSFROMCHAR, SendMessageW(ed, EM_LINEINDEX, 1, 0), 0);
            if ((short)HIWORD(p1) > (short)HIWORD(p0)) lh = (short)HIWORD(p1) - (short)HIWORD(p0);
        }
        GetWindowRect(np, &wr); GetClientRect(ed, &cr);
        chrome = (wr.bottom - wr.top) - cr.bottom;
        want = chrome + lines * lh + 10;
        if (want > 330) want = 330;
        nr.top = HCY - 18 - want / 2; if (nr.top < 236) nr.top = 236; nr.bottom = nr.top + want;
        say("letter lines %d lh %d height %d", lines, lh, want);
        SetWindowPos(np, HWND_TOP, nr.left, nr.top, nr.right - nr.left, want, SWP_NOACTIVATE);
    }

    /* Paint's colour box, with red picked, under the letter */
    palette_y = nr.bottom + 10;
    paint = NULL;
    if (palette_y + 51 <= 524) {
        pid = launch("mspaint.exe", SW_SHOWMINNOACTIVE);
        paint = wait_top("MSPaintApp", pid, 8000);
    }
    say("paint %p", paint);
    if (paint && palette_y + 51 <= 524) {      /* only when the letter leaves room for it */
        HWND pal = NULL;
        int tries;
        for (tries = 0; tries < 40 && !pal; tries++) { pal = kid_id(paint, 59416); if (!pal) Sleep(50); }
        ShowWindow(paint, SW_HIDE);
        if (pal) {
            RECT r; int w, hh;
            GetWindowRect(pal, &r);
            w = r.right - r.left; hh = r.bottom - r.top;
            say("palette %dx%d", w, hh);
            ShowWindow(pal, SW_HIDE);
            SetWindowLongA(pal, GWL_STYLE, (GetWindowLongA(pal, GWL_STYLE) & ~WS_CHILD) | WS_POPUP);
            SetParent(pal, NULL);
            SetWindowPos(pal, HWND_TOP, SW / 2 - w / 2, palette_y, w, hh, SWP_NOACTIVATE);
            {   /* pick red: the third swatch of the bottom row */
                LPARAM at = MAKELPARAM(41 + 16 * 2, 16 + 16 * 1);
                PostMessageA(pal, WM_LBUTTONDOWN, MK_LBUTTON, at);
                PostMessageA(pal, WM_LBUTTONUP, 0, at);
            }
            palette = pal;
        }
    }

    /* the heart: keys on the curve, in mirror pairs; a pair is left out where it would touch
       another key or the letter (the cleft and the tip are where the two sides meet) */
    {
        RECT placed[160], keep, core[160];
        int np_ = 0, nc = 0, used = 0, N = nkeys & ~1, kw = 38, kh = 30, cw = 13, ch = 9;
        POINT spot[160];
        heart_points(N, SW / 2, HCY, 23.5, 21.0, pts);
        GetWindowRect(np, &keep);
        InflateRect(&keep, 10, 10);
        placed[np_++] = keep;
        if (palette) { GetWindowRect(palette, &keep); InflateRect(&keep, 4, 4); placed[np_++] = keep; }
        for (i = 0; i <= N / 2; i++) {
            int j = (N - i) % N, pair = (j != i), q, ok = 1;
            RECT ri, rj;
            SetRect(&ri, pts[i].x - kw / 2 - 2, pts[i].y - kh / 2 - 2, pts[i].x + kw / 2 + 2, pts[i].y + kh / 2 + 2);
            SetRect(&rj, pts[j].x - kw / 2 - 2, pts[j].y - kh / 2 - 2, pts[j].x + kw / 2 + 2, pts[j].y + kh / 2 + 2);
            RECT ci, cj;
            if (pair && abs(pts[i].x - pts[j].x) < kw && abs(pts[i].y - pts[j].y) < kh) {
                /* the two sides meet (just above the tip): stand the pair shoulder to shoulder */
                pts[i].x = SW / 2 + (pts[i].x < SW / 2 ? -1 : 1) * (kw / 2);
                pts[j].x = SW / 2 + (pts[j].x < SW / 2 ? -1 : 1) * (kw / 2);
                if (pts[i].x == pts[j].x) pts[j].x = SW - pts[i].x;
                SetRect(&ri, pts[i].x - kw / 2 - 2, pts[i].y - kh / 2 - 2, pts[i].x + kw / 2 + 2, pts[i].y + kh / 2 + 2);
                SetRect(&rj, pts[j].x - kw / 2 - 2, pts[j].y - kh / 2 - 2, pts[j].x + kw / 2 + 2, pts[j].y + kh / 2 + 2);
            }
            SetRect(&ci, pts[i].x - cw, pts[i].y - ch, pts[i].x + cw, pts[i].y + ch);
            SetRect(&cj, pts[j].x - cw, pts[j].y - ch, pts[j].x + cw, pts[j].y + ch);
            if (pair && overlaps(ci, cj)) ok = 0;                 /* the two sides meeting */
            for (q = 0; ok && q < np_; q++) if (overlaps(ri, placed[q]) || (pair && overlaps(rj, placed[q]))) ok = 0;
            for (q = 0; ok && q < nc; q++) if (overlaps(ci, core[q]) || (pair && overlaps(cj, core[q]))) ok = 0;
            if (!ok) continue;
            core[nc++] = ci; spot[used++] = pts[i];
            if (pair) { core[nc++] = cj; spot[used++] = pts[j]; }
        }
        say("spots %d of %d keys", used, nkeys);
        for (i = 0; i < nkeys; i++) {
            HWND h = keys[i];
            RECT r;
            int w, hh;
            GetWindowRect(h, &r);
            w = r.right - r.left; hh = r.bottom - r.top;
            ShowWindow(h, SW_HIDE);
            if (i >= used) continue;          /* a spare key stays hidden */
            EnableWindow(h, TRUE);
            SetWindowLongA(h, GWL_STYLE, (GetWindowLongA(h, GWL_STYLE) & ~WS_CHILD) | WS_POPUP);
            SetParent(h, NULL);
            SetWindowPos(h, HWND_TOP, spot[i].x - w / 2, spot[i].y - hh / 2, w, hh, SWP_NOACTIVATE);
        }
        nkeys = used;
    }

    /* show everything at once, then let it all paint */
    for (i = 0; i < nkeys; i++) ShowWindow(keys[i], SW_SHOWNA);
    if (palette) ShowWindow(palette, SW_SHOWNA);
    ShowWindow(np, SW_SHOWNORMAL);
    SetForegroundWindow(np);
    {   /* Notepad stays the active window, but nothing has the keyboard: no caret in the picture */
        DWORD me = GetCurrentThreadId(), them = GetWindowThreadProcessId(np, NULL);
        AttachThreadInput(me, them, TRUE);
        SetFocus(NULL);
        AttachThreadInput(me, them, FALSE);
    }
    SendMessageW(ed, EM_SETSEL, 0, 0);
    PostMessageW(ed, WM_KILLFOCUS, 0, 0);    /* the edit drops its caret */
    Sleep(300);
    RedrawWindow(NULL, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_FRAME | RDW_UPDATENOW);
    Sleep(1200);
    say("settled");
    return 0;
}
