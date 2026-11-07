/*
 * winprobe - look for hidden UI in *running* Windows programs.
 *
 * The runtime twin of dlgscan.  Where dlgscan reads dialog templates out
 * of files, winprobe asks the live window manager where every control
 * actually ended up, which catches controls that code moves around after
 * the dialog is created.
 *
 *   winprobe list                       top-level windows (hwnd pid class title)
 *   winprobe probe  <win>               every child control, flagged:
 *                                         OUTSIDE   beyond the parent's client area
 *                                         CLIPPED   more than half cut off
 *                                         GHOST     hidden, yet sitting inside the window
 *                                         COVERED   visible but buried under a sibling
 *                                         ZEROSIZE  0 wide or 0 tall
 *   winprobe tab    <win>               walk the Tab order like the keyboard does
 *   winprobe menu   <win>               dump the menu bar with item states
 *   winprobe grow   <win> <w> <h>       force a window to a new size (ignores
 *                                       the fixed border - like dragging an edge
 *                                       that is not supposed to move)
 *   winprobe reveal <win>               grow a window until every child shows
 *   winprobe shot   <win|screen> f.bmp  save a screenshot as BMP
 *   winprobe focus  <child-hwnd>        give keyboard focus to a control
 *   winprobe show   <child-hwnd>        resurrect a ghost: show + enable it
 *   winprobe enable <child-hwnd>        enable a disabled control
 *   winprobe check  <child-hwnd>        tick a checkbox
 *   winprobe click  <child-hwnd>        press a button
 *   winprobe settext <hwnd> <text>      set a window's text
 *   winprobe close  <win>               send WM_CLOSE
 *   winprobe crawl  <outdir> <cmdline>  launch a program and visit every
 *                                       "..." menu item, every property-sheet
 *                                       tab and every ">>" expander, probing
 *                                       and photographing each window
 *
 * <win> is a hex HWND (0x1234), a substring of a window title, or
 * class:NAME for an exact window class.
 *
 * Build: i686-w64-mingw32-gcc -O2 -o winprobe.exe winprobe.c -lgdi32 -luser32
 *
 * Public domain / CC0.  https://github.com/williamsharkey/windows-secrets
 */
#define _WIN32_WINNT 0x0600
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static FILE *out;

static void utf8(const WCHAR *w, char *o, int cap)
{
    int i, n;
    WCHAR tmp[512];
    for (i = 0; w[i] && i < 511; i++) tmp[i] = (w[i] == '\t' || w[i] == '\r' || w[i] == '\n' || w[i] == '"') ? L' ' : w[i];
    tmp[i] = 0;
    n = WideCharToMultiByte(CP_UTF8, 0, tmp, -1, o, cap, NULL, NULL);
    if (n <= 0) o[0] = 0;
}

static void wtext(HWND h, char *o, int cap)
{
    WCHAR w[512];
    DWORD_PTR r;
    w[0] = 0;
    if (!SendMessageTimeoutW(h, WM_GETTEXT, 511, (LPARAM)w, SMTO_ABORTIFHUNG, 500, &r)) w[0] = 0;
    w[511] = 0;
    utf8(w, o, cap);
}

static void wclass(HWND h, char *o, int cap)
{
    WCHAR w[256];
    GetClassNameW(h, w, 256);
    utf8(w, o, cap);
}

/* ---- window lookup ----------------------------------------------------- */

struct find { const char *pat; HWND found; int cls; };

static BOOL CALLBACK find_cb(HWND h, LPARAM lp)
{
    struct find *f = (struct find *)lp;
    char t[512];
    if (!IsWindowVisible(h)) return TRUE;
    if (f->cls) wclass(h, t, sizeof t);
    else wtext(h, t, sizeof t);
    if (f->cls ? !strcmp(t, f->pat) : strstr(t, f->pat) != NULL) { f->found = h; return FALSE; }
    return TRUE;
}

static HWND find_win(const char *s)
{
    struct find f;
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) return (HWND)(UINT_PTR)strtoul(s, NULL, 16);
    f.found = NULL;
    f.cls = !strncmp(s, "class:", 6);
    f.pat = f.cls ? s + 6 : s;
    EnumWindows(find_cb, (LPARAM)&f);
    if (!f.found) { fprintf(stderr, "winprobe: no window matches '%s'\n", s); exit(1); }
    return f.found;
}

/* ---- list -------------------------------------------------------------- */

static BOOL CALLBACK list_cb(HWND h, LPARAM lp)
{
    char t[512], c[256];
    DWORD pid;
    RECT r;
    (void)lp;
    if (!IsWindowVisible(h)) return TRUE;
    wtext(h, t, sizeof t);
    wclass(h, c, sizeof c);
    GetWindowThreadProcessId(h, &pid);
    GetWindowRect(h, &r);
    fprintf(out, "0x%08lx\tpid=%lu\t%s\t%ldx%ld@%ld,%ld\t\"%s\"\n", (unsigned long)(UINT_PTR)h, pid, c,
            r.right - r.left, r.bottom - r.top, r.left, r.top, t);
    return TRUE;
}

/* ---- probe ------------------------------------------------------------- */

static RECT root_client; /* client rect of the top window, screen coords */
static int n_outside, n_ghost, n_disabled, n_covered;

static const char *btn_kind(LONG style)
{
    switch (style & 0xF) {
    case 0: case 1: return "pushbutton";
    case 2: case 3: return "checkbox";
    case 5: case 6: return "3state";
    case 4: case 9: return "radio";
    case 7: return "groupbox";
    case 11: return "ownerdraw";
    default: return "button";
    }
}

/* a visible control whose whole rectangle sits inside a visible, opaque
   sibling that is above it in the z-order cannot be seen */
static int covered(HWND h, RECT *r)
{
    HWND s;
    RECT sr, u;
    char c[64];
    for (s = GetWindow(h, GW_HWNDPREV); s; s = GetWindow(s, GW_HWNDPREV)) {
        if (!IsWindowVisible(s)) continue;
        wclass(s, c, sizeof c);
        if (!strcmp(c, "Static")) continue;
        if (!strcmp(c, "Button") && (GetWindowLongW(s, GWL_STYLE) & 0xF) == 7) continue;
        if (GetWindowLongW(s, GWL_EXSTYLE) & WS_EX_TRANSPARENT) continue;
        GetWindowRect(s, &sr);
        UnionRect(&u, &sr, r);
        if (EqualRect(&u, &sr)) return 1;
    }
    return 0;
}

static void probe_one(HWND h, int depth)
{
    char t[512], c[256];
    RECT r, pr, vis;
    HWND parent = GetParent(h), k;
    LONG style = GetWindowLongW(h, GWL_STYLE);
    const char *flag = "ok";
    POINT p0;
    int visible = IsWindowVisible(h) != 0;
    int pvisible = IsWindowVisible(parent) != 0;
    int enabled = IsWindowEnabled(h) != 0;

    wtext(h, t, sizeof t);
    wclass(h, c, sizeof c);
    GetWindowRect(h, &r);
    GetClientRect(parent, &pr);
    p0.x = 0; p0.y = 0;
    ClientToScreen(parent, &p0);
    OffsetRect(&pr, p0.x, p0.y);

    if (r.right <= r.left || r.bottom <= r.top) flag = "ZEROSIZE";
    else if (!IntersectRect(&vis, &r, &pr)) flag = "OUTSIDE";
    else if (!IntersectRect(&vis, &r, &root_client)) flag = "OUTSIDE";
    else {
        long full = (long)(r.right - r.left) * (r.bottom - r.top);
        long seen = (long)(vis.right - vis.left) * (vis.bottom - vis.top);
        if (seen * 2 < full) flag = "CLIPPED";
        else if (!visible && pvisible) flag = "GHOST";
        else if (visible && covered(h, &r)) flag = "COVERED";
    }
    if (visible && (!strcmp(flag, "OUTSIDE") || !strcmp(flag, "CLIPPED"))) n_outside++;
    if (!strcmp(flag, "GHOST")) n_ghost++;
    if (!strcmp(flag, "COVERED")) n_covered++;
    if (visible && !enabled) n_disabled++;

    fprintf(out, "%s\t%*s0x%08lx\tid=%d\t%s%s%s\t@%ld,%ld %ldx%ld\t%s%s%s\t\"%s\"\n",
            flag, depth * 2, "", (unsigned long)(UINT_PTR)h, GetDlgCtrlID(h), c,
            !strcmp(c, "Button") ? ":" : "", !strcmp(c, "Button") ? btn_kind(style) : "",
            r.left - p0.x, r.top - p0.y, r.right - r.left, r.bottom - r.top,
            visible ? "visible" : "hidden", enabled ? "" : ",disabled", style & WS_TABSTOP ? ",tabstop" : "", t);

    for (k = GetWindow(h, GW_CHILD); k; k = GetWindow(k, GW_HWNDNEXT)) probe_one(k, depth + 1);
}

static void probe(HWND top)
{
    char t[512], c[256];
    RECT wr, cr;
    POINT p0 = {0, 0};
    HWND k;
    wtext(top, t, sizeof t);
    wclass(top, c, sizeof c);
    GetWindowRect(top, &wr);
    GetClientRect(top, &cr);
    ClientToScreen(top, &p0);
    root_client = cr;
    OffsetRect(&root_client, p0.x, p0.y);
    n_outside = n_ghost = n_disabled = n_covered = 0;
    fprintf(out, "WINDOW\t0x%08lx\t%s\twindow=%ldx%ld client=%ldx%ld\t\"%s\"\n", (unsigned long)(UINT_PTR)top, c,
            wr.right - wr.left, wr.bottom - wr.top, cr.right, cr.bottom, t);
    for (k = GetWindow(top, GW_CHILD); k; k = GetWindow(k, GW_HWNDNEXT)) probe_one(k, 1);
    fprintf(out, "SUMMARY\toutside=%d ghost=%d covered=%d disabled=%d\n", n_outside, n_ghost, n_covered, n_disabled);
}

/* ---- tab order --------------------------------------------------------- */

static void tab(HWND top)
{
    HWND first = GetNextDlgTabItem(top, NULL, FALSE), h = first;
    int n = 0;
    RECT cr, r, x;
    POINT p0 = {0, 0};
    GetClientRect(top, &cr);
    ClientToScreen(top, &p0);
    OffsetRect(&cr, p0.x, p0.y);
    while (h && n < 300) {
        char t[512], c[256];
        wtext(h, t, sizeof t);
        wclass(h, c, sizeof c);
        GetWindowRect(h, &r);
        fprintf(out, "TAB %3d\t0x%08lx\tid=%d\t%s\t%s%s\t\"%s\"\n", ++n, (unsigned long)(UINT_PTR)h, GetDlgCtrlID(h), c,
                IntersectRect(&x, &r, &cr) ? "onscreen" : "OFFSCREEN", IsWindowEnabled(h) ? "" : ",disabled", t);
        h = GetNextDlgTabItem(top, h, FALSE);
        if (h == first) break;
    }
}

/* ---- menus ------------------------------------------------------------- */

#define MAXCMD 400
static struct { UINT id; char text[160]; } cmds[MAXCMD];
static int ncmds;

static int ends_with_dots(const char *t)
{
    /* "Print...  Ctrl+P" - the accelerator follows the dots, so look for
       an ellipsis anywhere; "About" boxes break the convention, add them */
    return strstr(t, "...") || strstr(t, "\xE2\x80\xA6") || strstr(t, "About");
}

static int risky(const char *t)
{
    static const char *bad[] = {"Delete", "Format", "Exit", "Uninstall", "Shut", "Restart", "Log off", "Log Off",
                                "Disconnect", "Erase", "Remove", "Open", "Save", "Import", "Export", "Send",
                                "Run", "Insert Object", "Connect", "Dial", "Hang", "Restore", "Backup", "Install", 0};
    int i;
    for (i = 0; bad[i]; i++) if (strstr(t, bad[i])) return 1;
    return 0;
}

static void dump_menu(HMENU m, int depth, int collect)
{
    int i, n = GetMenuItemCount(m);
    for (i = 0; i < n; i++) {
        WCHAR w[256];
        char t[512];
        MENUITEMINFOW mi;
        memset(&mi, 0, sizeof mi);
        mi.cbSize = sizeof mi;
        mi.fMask = MIIM_STATE | MIIM_ID | MIIM_SUBMENU | MIIM_FTYPE | MIIM_STRING;
        mi.dwTypeData = w;
        mi.cch = 255;
        w[0] = 0;
        if (!GetMenuItemInfoW(m, i, TRUE, &mi)) continue;
        utf8(w, t, sizeof t);
        fprintf(out, "MENU\t%*s%s\tid=%u%s%s%s\n", depth * 2, "", mi.fType & MFT_SEPARATOR ? "-----" : t, mi.wID,
                mi.fState & MFS_GRAYED ? " GRAYED" : "", mi.fState & MFS_CHECKED ? " CHECKED" : "",
                mi.fType & MFT_OWNERDRAW ? " OWNERDRAW" : "");
        if (mi.hSubMenu) dump_menu(mi.hSubMenu, depth + 1, collect);
        else if (collect && ncmds < MAXCMD && !(mi.fState & MFS_GRAYED) && ends_with_dots(t) && !risky(t)) {
            cmds[ncmds].id = mi.wID;
            snprintf(cmds[ncmds].text, sizeof cmds[ncmds].text, "%s", t);
            ncmds++;
        }
    }
}

/* ---- resize ------------------------------------------------------------ */

static void grow(HWND h, int w, int ht)
{
    RECT r;
    SetWindowPos(h, NULL, 0, 0, w, ht, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
    GetWindowRect(h, &r);
    fprintf(out, "now %ldx%ld\n", r.right - r.left, r.bottom - r.top);
}

static BOOL CALLBACK extent_cb(HWND h, LPARAM lp)
{
    RECT *u = (RECT *)lp, r;
    if (!IsWindowVisible(h)) return TRUE;
    GetWindowRect(h, &r);
    if (r.right - r.left > 4000 || r.bottom - r.top > 4000) return TRUE;
    UnionRect(u, u, &r);
    return TRUE;
}

static void reveal(HWND h)
{
    RECT wr, u;
    GetWindowRect(h, &wr);
    u = wr;
    EnumChildWindows(h, extent_cb, (LPARAM)&u);
    if (u.right - wr.left > 3000) u.right = wr.left + 3000;
    if (u.bottom - wr.top > 2000) u.bottom = wr.top + 2000;
    grow(h, u.right - wr.left + 16, u.bottom - wr.top + 16);
}

/* ---- screenshot ------------------------------------------------------- */

static int save_bmp(HBITMAP bm, HDC dc, int w, int h, const char *path)
{
    BITMAPINFOHEADER bi;
    BITMAPFILEHEADER fh;
    int stride = ((w * 24 + 31) / 32) * 4;
    unsigned char *px = (unsigned char *)malloc((size_t)stride * h);
    FILE *f;
    memset(&bi, 0, sizeof bi);
    bi.biSize = sizeof bi;
    bi.biWidth = w;
    bi.biHeight = h;
    bi.biPlanes = 1;
    bi.biBitCount = 24;
    GetDIBits(dc, bm, 0, h, px, (BITMAPINFO *)&bi, DIB_RGB_COLORS);
    memset(&fh, 0, sizeof fh);
    fh.bfType = 0x4D42;
    fh.bfOffBits = sizeof fh + sizeof bi;
    fh.bfSize = fh.bfOffBits + stride * h;
    f = fopen(path, "wb");
    if (!f) { free(px); return 0; }
    fwrite(&fh, sizeof fh, 1, f);
    fwrite(&bi, sizeof bi, 1, f);
    fwrite(px, (size_t)stride * h, 1, f);
    fclose(f);
    free(px);
    return 1;
}

static void shot_rect(RECT r, const char *path)
{
    HDC sdc = GetDC(NULL), mdc;
    HBITMAP bm;
    int w = r.right - r.left, h = r.bottom - r.top;
    if (w <= 0 || h <= 0) return;
    mdc = CreateCompatibleDC(sdc);
    bm = CreateCompatibleBitmap(sdc, w, h);
    SelectObject(mdc, bm);
    BitBlt(mdc, 0, 0, w, h, sdc, r.left, r.top, SRCCOPY | CAPTUREBLT);
    fprintf(out, save_bmp(bm, mdc, w, h, path) ? "SHOT\t%s %dx%d\n" : "SHOTFAIL\t%s\n", path, w, h);
    DeleteObject(bm);
    DeleteDC(mdc);
    ReleaseDC(NULL, sdc);
}

static void shot(const char *which, const char *path)
{
    RECT r;
    if (!strcmp(which, "screen")) {
        r.left = GetSystemMetrics(SM_XVIRTUALSCREEN);
        r.top = GetSystemMetrics(SM_YVIRTUALSCREEN);
        r.right = r.left + GetSystemMetrics(SM_CXVIRTUALSCREEN);
        r.bottom = r.top + GetSystemMetrics(SM_CYVIRTUALSCREEN);
    } else
        GetWindowRect(find_win(which), &r);
    shot_rect(r, path);
}

/* ---- crawl ------------------------------------------------------------- */

#define MAXW 512
static HWND before[MAXW];
static int nbefore;

static BOOL CALLBACK snap_cb(HWND h, LPARAM lp)
{
    (void)lp;
    if (nbefore < MAXW && IsWindowVisible(h)) before[nbefore++] = h;
    return TRUE;
}

static void snapshot(void) { nbefore = 0; EnumWindows(snap_cb, 0); }

struct newwin { HWND found; DWORD pid; };

static BOOL CALLBACK new_cb(HWND h, LPARAM lp)
{
    struct newwin *nw = (struct newwin *)lp;
    int i;
    DWORD pid;
    RECT r;
    char c[64];
    if (!IsWindowVisible(h)) return TRUE;
    for (i = 0; i < nbefore; i++) if (before[i] == h) return TRUE;
    GetWindowThreadProcessId(h, &pid);
    if (nw->pid && pid != nw->pid) return TRUE;
    GetWindowRect(h, &r);
    if (r.right - r.left < 60 || r.bottom - r.top < 30) return TRUE;
    wclass(h, c, sizeof c);
    if (!strcmp(c, "tooltips_class32") || !strcmp(c, "#32768") || !strcmp(c, "ConsoleWindowClass")) return TRUE;
    nw->found = h;
    return FALSE;
}

static HWND wait_new(DWORD pid, int ms)
{
    struct newwin nw;
    int t;
    for (t = 0; t < ms; t += 100) {
        nw.found = NULL;
        nw.pid = pid;
        EnumWindows(new_cb, (LPARAM)&nw);
        if (nw.found) { Sleep(400); return nw.found; }
        Sleep(100);
    }
    return NULL;
}

static char outdir[MAX_PATH];
static int seq;
static FILE *summary;

static void record(HWND h, const char *why)
{
    char path[MAX_PATH], t[512];
    RECT r;
    FILE *save = out;
    seq++;
    wtext(h, t, sizeof t);
    sprintf(path, "%s\\%03d.txt", outdir, seq);
    out = fopen(path, "w");
    if (!out) out = save;
    fprintf(out, "VIA\t%s\n", why);
    probe(h);
    tab(h);
    if (GetMenu(h)) dump_menu(GetMenu(h), 0, 0);
    GetWindowRect(h, &r);
    sprintf(path, "%s\\%03d.bmp", outdir, seq);
    SetForegroundWindow(h);
    Sleep(150);
    shot_rect(r, path);
    if (out != save) fclose(out);
    out = save;
    fprintf(summary, "%03d\toutside=%d\tghost=%d\tcovered=%d\tdisabled=%d\t%s\t\"%s\"\n", seq, n_outside, n_ghost,
            n_covered, n_disabled, why, t);
    fflush(summary);
}

static int is_propsheet(HWND h)
{
    HWND tabc = FindWindowExW(h, NULL, L"SysTabControl32", NULL);
    return tabc ? (int)SendMessageW(tabc, 0x1304 /* TCM_GETITEMCOUNT */, 0, 0) : 0;
}

static void visit(HWND h, const char *why, int depth);

static void visit_tabs_and_expanders(HWND h, const char *why, int depth)
{
    int i, n = is_propsheet(h);
    char w2[300];
    HWND k;
    for (i = 1; i < n && i < 30; i++) {
        SendMessageW(h, WM_USER + 101 /* PSM_SETCURSEL */, (WPARAM)i, 0);
        Sleep(500);
        sprintf(w2, "%s > tab %d", why, i);
        record(h, w2);
    }
    if (depth > 1) return;
    /* expander buttons: ">>" style - press them and look again */
    for (k = FindWindowExW(h, NULL, L"Button", NULL); k; k = FindWindowExW(h, k, L"Button", NULL)) {
        char t[256];
        wtext(k, t, sizeof t);
        if (IsWindowVisible(k) && IsWindowEnabled(k) && (strstr(t, ">>") || strstr(t, "<<"))) {
            DWORD pid;
            HWND nw;
            GetWindowThreadProcessId(h, &pid);
            snapshot();
            PostMessageW(k, BM_CLICK, 0, 0);
            Sleep(700);
            sprintf(w2, "%s > pressed [%s]", why, t);
            nw = wait_new(pid, 600);
            if (nw) visit(nw, w2, depth + 1);
            else record(h, w2);
        }
    }
}

static void dismiss(HWND h)
{
    int t;
    PostMessageW(h, WM_COMMAND, IDCANCEL, 0);
    for (t = 0; t < 15 && IsWindow(h) && IsWindowVisible(h); t++) Sleep(100);
    if (IsWindow(h) && IsWindowVisible(h)) PostMessageW(h, WM_CLOSE, 0, 0);
    for (t = 0; t < 15 && IsWindow(h) && IsWindowVisible(h); t++) Sleep(100);
    if (IsWindow(h) && IsWindowVisible(h)) PostMessageW(h, WM_KEYDOWN, VK_ESCAPE, 0);
    for (t = 0; t < 10 && IsWindow(h) && IsWindowVisible(h); t++) Sleep(100);
}

static void visit(HWND h, const char *why, int depth)
{
    record(h, why);
    visit_tabs_and_expanders(h, why, depth);
    if (depth > 0) dismiss(h);
}

static void crawl(const char *dir, const char *cmdline)
{
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    char cl[1024], path[MAX_PATH], w[300];
    HWND main_w;
    DWORD pid;
    int i;

    strncpy(outdir, dir, sizeof outdir - 1);
    CreateDirectoryA(outdir, NULL);
    sprintf(path, "%s\\summary.tsv", outdir);
    summary = fopen(path, "w");
    if (!summary) { fprintf(stderr, "cannot write %s\n", path); exit(1); }

    snapshot();
    memset(&si, 0, sizeof si);
    si.cb = sizeof si;
    snprintf(cl, sizeof cl, "%s", cmdline);
    if (!CreateProcessA(NULL, cl, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        fprintf(summary, "ERROR\tcannot start %s (%lu)\n", cmdline, GetLastError());
        fclose(summary);
        return;
    }
    WaitForInputIdle(pi.hProcess, 8000);
    main_w = wait_new(0, 12000); /* any pid: launchers like control.exe hand off */
    if (!main_w) { fprintf(summary, "ERROR\tno window appeared\n"); fclose(summary); return; }
    GetWindowThreadProcessId(main_w, &pid);
    Sleep(800);
    visit(main_w, "main window", 0);

    ncmds = 0;
    if (GetMenu(main_w)) {
        FILE *save = out;
        sprintf(path, "%s\\menu.txt", outdir);
        out = fopen(path, "w");
        if (!out) out = save;
        dump_menu(GetMenu(main_w), 0, 1);
        if (out != save) fclose(out);
        out = save;
    }
    for (i = 0; i < ncmds; i++) {
        HWND d;
        if (!IsWindow(main_w)) break;
        snapshot();
        PostMessageW(main_w, WM_COMMAND, cmds[i].id, 0);
        d = wait_new(pid, 4000);
        sprintf(w, "menu [%s]", cmds[i].text);
        if (d) visit(d, w, 1);
        else fprintf(summary, "---\tno dialog\t%s\n", w);
        fflush(summary);
    }
    /* close up: politely, then answer "No" to save prompts, then force */
    if (IsWindow(main_w)) {
        HWND d;
        snapshot();
        PostMessageW(main_w, WM_CLOSE, 0, 0);
        d = wait_new(pid, 1500);
        if (d) PostMessageW(d, WM_COMMAND, IDNO, 0);
    }
    if (WaitForSingleObject(pi.hProcess, 3000) == WAIT_TIMEOUT) {
        HANDLE hp = OpenProcess(PROCESS_TERMINATE, FALSE, pid);
        if (hp) { TerminateProcess(hp, 0); CloseHandle(hp); }
        if (pid != pi.dwProcessId) TerminateProcess(pi.hProcess, 0);
    }
    fprintf(summary, "END\t%d windows recorded\n", seq);
    fclose(summary);
}

int main(int argc, char **argv)
{
    const char *cmd = argc > 1 ? argv[1] : "";
    out = stdout;
    {   /* Vista+ only; look it up so the same exe runs on XP */
        FARPROC f = GetProcAddress(GetModuleHandleA("user32.dll"), "SetProcessDPIAware");
        if (f) ((BOOL (WINAPI *)(void))f)();
    }
    if (!strcmp(cmd, "list")) EnumWindows(list_cb, 0);
    else if (!strcmp(cmd, "probe") && argc > 2) probe(find_win(argv[2]));
    else if (!strcmp(cmd, "tab") && argc > 2) tab(find_win(argv[2]));
    else if (!strcmp(cmd, "menu") && argc > 2) {
        HMENU m = GetMenu(find_win(argv[2]));
        if (m) dump_menu(m, 0, 0); else puts("(no menu bar)");
    } else if (!strcmp(cmd, "grow") && argc > 4) grow(find_win(argv[2]), atoi(argv[3]), atoi(argv[4]));
    else if (!strcmp(cmd, "reveal") && argc > 2) reveal(find_win(argv[2]));
    else if (!strcmp(cmd, "shot") && argc > 3) shot(argv[2], argv[3]);
    else if (!strcmp(cmd, "focus") && argc > 2) {
        HWND h = find_win(argv[2]);
        DWORD me = GetCurrentThreadId(), them = GetWindowThreadProcessId(h, NULL);
        AttachThreadInput(me, them, TRUE);
        SetForegroundWindow(GetAncestor(h, GA_ROOT));
        SetFocus(h);
        AttachThreadInput(me, them, FALSE);
    } else if (!strcmp(cmd, "show") && argc > 2) {
        /* resurrect a ghost: make it visible and usable */
        HWND h = find_win(argv[2]);
        ShowWindow(h, SW_SHOWNA);
        EnableWindow(h, TRUE);
        InvalidateRect(GetParent(h), NULL, TRUE);
    } else if (!strcmp(cmd, "enable") && argc > 2) EnableWindow(find_win(argv[2]), TRUE);
    else if (!strcmp(cmd, "check") && argc > 2) SendMessageW(find_win(argv[2]), BM_SETCHECK, BST_CHECKED, 0);
    else if (!strcmp(cmd, "click") && argc > 2) PostMessageW(find_win(argv[2]), BM_CLICK, 0, 0);
    else if (!strcmp(cmd, "settext") && argc > 3) SetWindowTextA(find_win(argv[2]), argv[3]);
    else if (!strcmp(cmd, "close") && argc > 2) PostMessageW(find_win(argv[2]), WM_CLOSE, 0, 0);
    else if (!strcmp(cmd, "crawl") && argc > 3) {
        /* everything after the outdir is the command line */
        char cl[1024] = "";
        int i;
        for (i = 3; i < argc; i++) {
            if (i > 3) strcat(cl, " ");
            if (strchr(argv[i], ' ')) { strcat(cl, "\""); strcat(cl, argv[i]); strcat(cl, "\""); }
            else strcat(cl, argv[i]);
        }
        crawl(argv[2], cl);
    } else {
        fputs("usage: winprobe list | probe <win> | tab <win> | menu <win> | grow <win> <w> <h>\n"
              "                | reveal <win> | shot <win|screen> out.bmp | focus <hwnd> | close <win>\n"
              "                | show|enable|check|click <hwnd> | settext <hwnd> <text>\n"
              "                | crawl <outdir> <command line...>\n"
              "  <win> = 0xHWND, a title substring, or class:NAME\n", stderr);
        return 2;
    }
    return 0;
}
