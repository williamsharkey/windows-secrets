/*
 * puppet - choreography for real Windows XP controls.
 *
 * Moves, resizes, reparents, shakes and drives the controls of ordinary
 * running programs (Notepad, Paint, Calculator, ...) from a separate process.
 * Nothing is drawn by puppet itself: every pixel on screen belongs to the
 * original programs.  Scenes:
 *
 *   puppet tribute     "For the ones who were almost"
 *   puppet basilisk    the BASILISK console (also runs when started with no args,
 *                      so a copy named basilisk.exe can be double-clicked)
 *   puppet intro       the curious user: hover, Properties, accidental double-click
 *   puppet test <x>    lab experiments
 *
 * Build: i686-w64-mingw32-gcc -O2 -o puppet.exe puppet.c puppet.res -lgdi32 -luser32 -lws2_32 -lshell32 -lcomctl32
 * Public domain / CC0.  https://github.com/williamsharkey/windows-secrets
 */
#define _WIN32_WINNT 0x0501
#define _WIN32_IE 0x0600
#include <winsock2.h>
#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>

#define PI 3.14159265358979
static int SW = 1024, SH = 768;
static FILE *plog;
static void say(const char *fmt, ...)
{
    va_list a;
    va_start(a, fmt);
    if (plog) { fprintf(plog, "%7.1f ", GetTickCount() / 1000.0); vfprintf(plog, fmt, a); fputc('\n', plog); fflush(plog); }
    va_end(a);
}

/* ===================================================================== */
/* window helpers                                                          */
/* ===================================================================== */

static void gettext_(HWND h, char *o, int cap)
{
    DWORD_PTR r;
    o[0] = 0;
    SendMessageTimeoutA(h, WM_GETTEXT, cap, (LPARAM)o, SMTO_ABORTIFHUNG, 400, &r);
}

static int is_class(HWND h, const char *c)
{
    char b[128];
    GetClassNameA(h, b, sizeof b);
    return !strcmp(b, c);
}

struct fw { const char *cls, *title; DWORD pid; HWND found; int visible; };
static BOOL CALLBACK fw_cb(HWND h, LPARAM lp)
{
    struct fw *f = (struct fw *)lp;
    char t[256];
    DWORD pid;
    if (f->visible && !IsWindowVisible(h)) return TRUE;
    if (f->cls && !is_class(h, f->cls)) return TRUE;
    if (f->pid) { GetWindowThreadProcessId(h, &pid); if (pid != f->pid) return TRUE; }
    if (f->title) { gettext_(h, t, sizeof t); if (!strstr(t, f->title)) return TRUE; }
    f->found = h;
    return FALSE;
}
static HWND top(const char *cls, const char *title)
{
    struct fw f = {cls, title, 0, NULL, 1};
    EnumWindows(fw_cb, (LPARAM)&f);
    return f.found;
}
static HWND top_pid(const char *cls, const char *title, DWORD pid)
{
    struct fw f = {cls, title, pid, NULL, 1};
    EnumWindows(fw_cb, (LPARAM)&f);
    return f.found;
}

struct fc { int id; const char *text, *cls; HWND found; };
static BOOL CALLBACK fc_cb(HWND h, LPARAM lp)
{
    struct fc *f = (struct fc *)lp;
    char t[256];
    if (f->cls && !is_class(h, f->cls)) return TRUE;
    if (f->text) { gettext_(h, t, sizeof t); if (strcmp(t, f->text)) return TRUE; }
    else if (f->id && GetDlgCtrlID(h) != f->id) return TRUE;
    f->found = h;
    return FALSE;
}
static HWND kid_id(HWND p, int id) { struct fc f = {id, NULL, NULL, NULL}; if (p) EnumChildWindows(p, fc_cb, (LPARAM)&f); return f.found; }
static HWND kid_text(HWND p, const char *t) { struct fc f = {0, t, NULL, NULL}; if (p) EnumChildWindows(p, fc_cb, (LPARAM)&f); return f.found; }
static HWND kid_cls(HWND p, const char *c) { struct fc f = {0, NULL, c, NULL}; if (p) EnumChildWindows(p, fc_cb, (LPARAM)&f); return f.found; }

/* every child with a given class, in z order */
struct fa { const char *cls; HWND *out; int n, cap; };
static BOOL CALLBACK fa_cb(HWND h, LPARAM lp)
{
    struct fa *f = (struct fa *)lp;
    if ((!f->cls || is_class(h, f->cls)) && f->n < f->cap) f->out[f->n++] = h;
    return TRUE;
}
static int kids(HWND p, const char *cls, HWND *out, int cap)
{
    struct fa f = {cls, out, 0, cap};
    if (p) EnumChildWindows(p, fa_cb, (LPARAM)&f);
    return f.n;
}

static RECT srect(HWND h) { RECT r; GetWindowRect(h, &r); return r; }

/* position of h in its parent's client coordinates (screen for top-levels) */
static RECT prect(HWND h)
{
    RECT r = srect(h);
    HWND p = (GetWindowLongA(h, GWL_STYLE) & WS_CHILD) ? GetParent(h) : NULL;
    if (p) { MapWindowPoints(NULL, p, (POINT *)&r, 2); }
    return r;
}

/* SWP_ASYNCWINDOWPOS: a hung program can't freeze the show */
#define SWPF (SWP_NOZORDER | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS)
static void place(HWND h, int x, int y, int w, int hh)
{
    SetWindowPos(h, NULL, x, y, w, hh, SWPF);
}

static void raise_(HWND h) { SetWindowPos(h, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE); }

static void cmd(HWND h, int id) { PostMessageA(h, WM_COMMAND, id, 0); }

static void settext(HWND h, const char *t) { DWORD_PTR r; SendMessageTimeoutA(h, WM_SETTEXT, 0, (LPARAM)t, SMTO_ABORTIFHUNG, 2000, &r); }

static void foreground(HWND h)
{
    DWORD me = GetCurrentThreadId(), them = GetWindowThreadProcessId(h, NULL);
    AttachThreadInput(me, them, TRUE);
    SetForegroundWindow(h);
    BringWindowToTop(h);
    AttachThreadInput(me, them, FALSE);
}

/* float a child control free on the desktop (it keeps its owner process) */
static void liberate(HWND h)
{
    RECT r = srect(h);
    LONG st = GetWindowLongA(h, GWL_STYLE);
    SetWindowLongA(h, GWL_STYLE, (st & ~WS_CHILD) | WS_POPUP);
    SetWindowLongA(h, GWL_EXSTYLE, GetWindowLongA(h, GWL_EXSTYLE) | WS_EX_TOOLWINDOW);   /* no taskbar button */
    SetParent(h, NULL);
    SetWindowPos(h, HWND_TOPMOST, r.left, r.top, r.right - r.left, r.bottom - r.top,
                 SWP_SHOWWINDOW | SWP_NOACTIVATE | SWP_FRAMECHANGED);
}

/* adopted controls are kept on top of their new parent's own children */
static HWND adopted[256];
static int nadopted;
static void raise_adopted(void)
{
    int i;
    for (i = 0; i < nadopted; i++)
        if (IsWindow(adopted[i])) SetWindowPos(adopted[i], HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS);
}

/* move a control (or a liberated one) into another window, keeping its screen spot */
static void adopt(HWND h, HWND np)
{
    if (nadopted < 256) adopted[nadopted++] = h;
    RECT r = srect(h);
    LONG st = GetWindowLongA(h, GWL_STYLE);
    SetWindowLongA(h, GWL_STYLE, (st & ~WS_POPUP) | WS_CHILD);
    SetParent(h, np);
    MapWindowPoints(NULL, np, (POINT *)&r, 2);
    SetWindowPos(h, HWND_TOP, r.left, r.top, r.right - r.left, r.bottom - r.top,
                 SWP_SHOWWINDOW | SWP_NOACTIVATE | SWP_FRAMECHANGED);
}

static void reveal(HWND h) { ShowWindow(h, SW_SHOWNA); EnableWindow(h, TRUE); }

/* ===================================================================== */
/* the animation engine                                                    */
/* ===================================================================== */

enum { EASE_IO, EASE_OUT, EASE_IN, EASE_LIN, EASE_BACK, EASE_ELASTIC };
typedef struct {
    HWND h;
    int pending;                 /* capture start rect when it begins */
    double x0, y0, w0, h0, x1, y1, w1, h1;
    DWORD start, dur;
    int ease, active, keep_size;
    double shake;                /* amplitude in px (shake tweens) */
    double arc;                  /* sideways bow, px */
} Tween;
#define MAXT 2048
static Tween tw[MAXT];
static int ntw;

typedef void (*TickFn)(void *ctx, DWORD now);
typedef struct { TickFn fn; void *ctx; int on; } Tick;
#define MAXK 64
static Tick ticks[MAXK];
static int nticks;

static double ease(int e, double f)
{
    switch (e) {
    case EASE_OUT: return 1 - (1 - f) * (1 - f) * (1 - f);
    case EASE_IN: return f * f * f;
    case EASE_LIN: return f;
    case EASE_BACK: { double c = 1.70158, c3 = c + 1; return 1 + c3 * pow(f - 1, 3) + c * pow(f - 1, 2); }
    case EASE_ELASTIC: return f <= 0 ? 0 : f >= 1 ? 1 : pow(2, -10 * f) * sin((f * 10 - 0.75) * (2 * PI / 3)) + 1;
    default: return f < .5 ? 4 * f * f * f : 1 - pow(-2 * f + 2, 3) / 2;
    }
}

static void cancel_tweens(HWND h)
{
    int i;
    for (i = 0; i < ntw; i++) if (tw[i].h == h) tw[i].active = 0;
}

/* tween h to x,y,w,h (parent coords) starting after delay ms, lasting dur ms.
   w or h < 0 keeps the current size. */
static Tween *tween(HWND h, int x, int y, int w, int hh, int delay, int dur, int e)
{
    Tween *t;
    int i;
    for (i = 0; i < ntw && tw[i].active; i++) ;
    if (i == ntw) { if (ntw >= MAXT) return NULL; ntw++; }
    t = &tw[i];
    memset(t, 0, sizeof *t);
    t->h = h; t->pending = 1; t->active = 1;
    t->x1 = x; t->y1 = y; t->w1 = w; t->h1 = hh;
    t->keep_size = w < 0 || hh < 0;
    t->start = GetTickCount() + delay; t->dur = dur > 0 ? dur : 1; t->ease = e;
    return t;
}

static void tween_arc(HWND h, int x, int y, int w, int hh, int delay, int dur, int e, double arc)
{
    Tween *t = tween(h, x, y, w, hh, delay, dur, e);
    if (t) t->arc = arc;
}

static void shake(HWND h, int delay, int dur, double amp)
{
    int i;
    for (i = 0; i < ntw && tw[i].active; i++) ;
    if (i == ntw) { if (ntw >= MAXT) return; ntw++; }
    memset(&tw[i], 0, sizeof tw[i]);
    tw[i].h = h; tw[i].pending = 1; tw[i].active = 1; tw[i].shake = amp;
    tw[i].start = GetTickCount() + delay; tw[i].dur = dur;
}

static void add_tick(TickFn fn, void *ctx)
{
    if (nticks < MAXK) { ticks[nticks].fn = fn; ticks[nticks].ctx = ctx; ticks[nticks].on = 1; nticks++; }
}
static void stop_ticks(void) { nticks = 0; }

static void frame(void)
{
    DWORD now = GetTickCount();
    static DWORD last_raise;
    int i;
    if (now - last_raise > 400) { raise_adopted(); last_raise = now; }
    for (i = 0; i < nticks; i++) if (ticks[i].on) ticks[i].fn(ticks[i].ctx, now);
    for (i = 0; i < ntw; i++) {
        Tween *t = &tw[i];
        double f, e, x, y, w, hh;
        if (!t->active || (LONG)(now - t->start) < 0) continue;
        if (!IsWindow(t->h)) { t->active = 0; continue; }
        if (t->pending) {
            RECT r = prect(t->h);
            t->x0 = r.left; t->y0 = r.top; t->w0 = r.right - r.left; t->h0 = r.bottom - r.top;
            if (t->keep_size || t->shake) { t->w1 = t->w0; t->h1 = t->h0; }
            t->pending = 0;
        }
        f = (double)(now - t->start) / t->dur;
        if (f >= 1) { f = 1; t->active = 0; }
        if (t->shake) {
            double a = t->shake * (1 - f);
            x = t->x0 + (f < 1 ? a * sin(now * 0.09) * (((now / 31) % 2) ? 1 : -1) : 0);
            y = t->y0 + (f < 1 ? a * 0.6 * cos(now * 0.13) : 0);
            SetWindowPos(t->h, NULL, (int)x, (int)y, 0, 0, SWP_NOSIZE | SWPF);
            continue;
        }
        e = ease(t->ease, f);
        x = t->x0 + (t->x1 - t->x0) * e;
        y = t->y0 + (t->y1 - t->y0) * e;
        if (t->arc) {   /* bow perpendicular to the path */
            double dx = t->x1 - t->x0, dy = t->y1 - t->y0, L = sqrt(dx * dx + dy * dy) + 1e-9, b = sin(PI * e) * t->arc;
            x += -dy / L * b; y += dx / L * b;
        }
        w = t->w0 + (t->w1 - t->w0) * e;
        hh = t->h0 + (t->h1 - t->h0) * e;
        SetWindowPos(t->h, NULL, (int)x, (int)y, (int)w, (int)hh, SWPF);
    }
}

/* run the world for ms milliseconds */
static void play(int ms)
{
    DWORD end = GetTickCount() + ms;
    MSG m;
    while ((LONG)(GetTickCount() - end) < 0) {
        frame();
        while (PeekMessageA(&m, NULL, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessageA(&m); }
        Sleep(14);
    }
}

static int tweens_running(void)
{
    int i;
    for (i = 0; i < ntw; i++) if (tw[i].active) return 1;
    return 0;
}
static void settle(int maxms) { DWORD end = GetTickCount() + maxms; while (tweens_running() && (LONG)(GetTickCount() - end) < 0) play(30); }

/* ===================================================================== */
/* input: a ghost hand on the real mouse and keyboard                      */
/* ===================================================================== */

static void mouse_abs(int x, int y, DWORD flags)
{
    INPUT in;
    memset(&in, 0, sizeof in);
    in.type = INPUT_MOUSE;
    in.mi.dx = (LONG)((x * 65535.0) / (SW - 1));
    in.mi.dy = (LONG)((y * 65535.0) / (SH - 1));
    in.mi.dwFlags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE | flags;
    SendInput(1, &in, sizeof in);
}

/* glide the pointer to x,y over ms, letting the world animate meanwhile */
static void glide(int x, int y, int ms, int drag)
{
    POINT p;
    DWORD t0 = GetTickCount(), t;
    GetCursorPos(&p);
    do {
        double f, e;
        t = GetTickCount() - t0;
        f = ms ? (double)t / ms : 1;
        if (f > 1) f = 1;
        e = ease(EASE_IO, f);
        mouse_abs((int)(p.x + (x - p.x) * e), (int)(p.y + (y - p.y) * e), 0);
        (void)drag;
        play(12);
    } while (t < (DWORD)ms);
}

static void click_at(int x, int y, int right)
{
    mouse_abs(x, y, right ? MOUSEEVENTF_RIGHTDOWN : MOUSEEVENTF_LEFTDOWN);
    play(60);
    mouse_abs(x, y, right ? MOUSEEVENTF_RIGHTUP : MOUSEEVENTF_LEFTUP);
}

static void dblclick_at(int x, int y)
{
    click_at(x, y, 0);
    play(90);
    click_at(x, y, 0);
}

static void key(BYTE vk, int up)
{
    INPUT in;
    memset(&in, 0, sizeof in);
    in.type = INPUT_KEYBOARD;
    in.ki.wVk = vk;
    in.ki.dwFlags = up ? KEYEVENTF_KEYUP : 0;
    SendInput(1, &in, sizeof in);
}

/* drag along a path of points (screen coords) with the left button held */
static void drag_path(const POINT *pts, int n, int ms_per_pt, int shift)
{
    int i;
    mouse_abs(pts[0].x, pts[0].y, 0);
    play(40);
    if (shift) key(VK_SHIFT, 0);
    mouse_abs(pts[0].x, pts[0].y, MOUSEEVENTF_LEFTDOWN);
    for (i = 1; i < n; i++) { mouse_abs(pts[i].x, pts[i].y, 0); play(ms_per_pt); }
    mouse_abs(pts[n - 1].x, pts[n - 1].y, MOUSEEVENTF_LEFTUP);
    if (shift) key(VK_SHIFT, 1);
    play(60);
}

/* type into an edit control with WM_CHAR at a human-ish pace */
static void type_into(HWND edit, const char *s, int cps)
{
    int base = 1000 / (cps > 0 ? cps : 20);
    for (; *s; s++) {
        char c = *s;
        if (c == '\n') { PostMessageA(edit, WM_CHAR, '\r', 0); play(base * 7); continue; }
        PostMessageA(edit, WM_CHAR, (BYTE)c, 0);
        if (c == '.' || c == ',') play(base * 6);
        else if (c == ' ') play(base + rand() % base);
        else play(base / 2 + rand() % base);
    }
}

/* ===================================================================== */
/* launching programs                                                     */
/* ===================================================================== */

static DWORD launch(const char *cmdline)
{
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    char cl[512];
    memset(&si, 0, sizeof si);
    si.cb = sizeof si;
    snprintf(cl, sizeof cl, "%s", cmdline);
    if (!CreateProcessA(NULL, cl, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) { say("launch failed %s", cmdline); return 0; }
    WaitForInputIdle(pi.hProcess, 5000);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    return pi.dwProcessId;
}

static HWND wait_top(const char *cls, const char *title, DWORD pid, int ms)
{
    DWORD end = GetTickCount() + ms;
    HWND h;
    do {
        h = pid ? top_pid(cls, title, pid) : top(cls, title);
        if (h) return h;
        play(60);
    } while ((LONG)(GetTickCount() - end) < 0);
    say("timeout waiting for %s/%s", cls ? cls : "-", title ? title : "-");
    return NULL;
}

static HWND open_app(const char *exe, const char *cls, const char *title)
{
    say("open_app %s", exe);
    DWORD pid = launch(exe);
    return wait_top(cls, title, 0, 8000);
    (void)pid;
}

/* ===================================================================== */
/* HTTP to the host (10.0.2.2) - files and the Claude relay               */
/* ===================================================================== */

static char *http(const char *method, const char *path, const char *body, int *outlen)
{
    SOCKET s;
    struct sockaddr_in a;
    char hdr[512], *buf = NULL, *p;
    int cap = 0, n = 0, r, blen = body ? (int)strlen(body) : 0;
    s = socket(AF_INET, SOCK_STREAM, 0);
    memset(&a, 0, sizeof a);
    a.sin_family = AF_INET;
    a.sin_port = htons(8765);
    a.sin_addr.s_addr = inet_addr("10.0.2.2");
    if (connect(s, (struct sockaddr *)&a, sizeof a)) { closesocket(s); return NULL; }
    sprintf(hdr, "%s %s HTTP/1.0\r\nHost: x\r\nContent-Length: %d\r\n\r\n", method, path, blen);
    send(s, hdr, (int)strlen(hdr), 0);
    if (blen) send(s, body, blen, 0);
    for (;;) {
        if (n + 8192 > cap) { cap = cap * 2 + 8192; buf = (char *)realloc(buf, cap + 1); }
        r = recv(s, buf + n, cap - n, 0);
        if (r <= 0) break;
        n += r;
    }
    closesocket(s);
    if (!buf) return NULL;
    buf[n] = 0;
    p = strstr(buf, "\r\n\r\n");
    if (!p) { free(buf); return NULL; }
    p += 4;
    if (outlen) *outlen = n - (int)(p - buf);
    memmove(buf, p, strlen(p) + 1);
    return buf;
}

static char *readfile(const char *path)
{
    FILE *f = fopen(path, "rb");
    long n;
    char *b;
    if (!f) return NULL;
    fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
    b = (char *)malloc(n + 1);
    n = (long)fread(b, 1, n, f);
    b[n] = 0;
    fclose(f);
    return b;
}

/* convert \n to \r\n for edit controls */
static char *crlf(const char *s)
{
    char *o = (char *)malloc(strlen(s) * 2 + 1), *q = o;
    for (; *s; s++) { if (*s == '\r') continue; if (*s == '\n') *q++ = '\r'; *q++ = *s; }
    *q = 0;
    return o;
}

/* ===================================================================== */
/* Notepad                                                                 */
/* ===================================================================== */

/* change Notepad's font through its own Font dialog */
static void notepad_font(HWND np, const char *face, const char *size, int show_ms)
{
    DWORD pid;
    HWND d, e;
    GetWindowThreadProcessId(np, &pid);
    cmd(np, 33);
    d = wait_top("#32770", "Font", pid, 4000);
    if (!d) return;
    play(show_ms / 3);
    e = kid_cls(kid_id(d, 1136), "Edit");
    if (e) settext(e, face);
    SendMessageA(d, WM_COMMAND, MAKEWPARAM(1136, CBN_EDITCHANGE), (LPARAM)kid_id(d, 1136));
    play(show_ms / 3);
    e = kid_cls(kid_id(d, 1138), "Edit");
    if (e) settext(e, size);
    SendMessageA(d, WM_COMMAND, MAKEWPARAM(1138, CBN_EDITCHANGE), (LPARAM)kid_id(d, 1138));
    play(show_ms / 3);
    PostMessageA(kid_id(d, 1), BM_CLICK, 0, 0);
    play(400);
}

#include "scenes.h"
#include "scene_v2.h"

int WINAPI WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cl, int show)
{
    WSADATA w;
    char *scene;
    (void)hi; (void)hp; (void)show;
    WSAStartup(MAKEWORD(2, 0), &w);
    InitCommonControls();
    SW = GetSystemMetrics(SM_CXSCREEN);
    SH = GetSystemMetrics(SM_CYSCREEN);
    CreateDirectoryA("C:\\p", NULL);
    plog = fopen("C:\\p\\puppet.log", "a");
    srand(1999);
    while (*cl == ' ') cl++;
    scene = cl;
    say("puppet start: '%s' %dx%d", scene, SW, SH);
    if (!*scene || !strncmp(scene, "basilisk", 8)) scene_basilisk();
    else if (!strncmp(scene, "tribute", 7)) { fast_letter = strstr(scene, "fast") != NULL; scene_tribute(); }
    else if (!strncmp(scene, "intro", 5)) scene_intro();
    else if (!strncmp(scene, "v2", 2)) { if (strstr(scene, "fast")) v2_speed = 0.05; scene_v2(); }
    else if (!strncmp(scene, "test", 4)) scene_test(scene + 4);
    say("puppet end");
    return 0;
}
