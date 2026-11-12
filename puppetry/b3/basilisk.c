/* BASILISK III - a Claude Code client assembled from Windows XP's own parts.
 *
 *   transcript   Notepad's edit control (Lucida Console, word wrap, scrollback)
 *   input bar    Notepad's own Find dialog, made a child of Notepad: Find what = the prompt,
 *                Find Next = Send, Cancel = Stop
 *   clock        the analog clock from Date and Time Properties
 *   meter        Calculator's display, showing what the session has cost
 *
 * Every part is a real window owned by the program that made it; this program only moves,
 * reparents, relabels and reads them. The model runs on the host (10.0.2.2:8765); tools
 * (run, read_file, write_file, edit_file) run here, inside Windows XP.
 *
 * Build:  tcc basilisk.c -luser32 -lgdi32 -Wl,-subsystem=windows
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- bits tcc's headers leave out ---------------------------------------------------- */
#ifndef CP_UTF8
#define CP_ACP 0
#define CP_OEMCP 1
#define CP_UTF8 65001
WINBASEAPI int WINAPI MultiByteToWideChar(UINT, DWORD, LPCSTR, int, LPWSTR, int);
WINBASEAPI int WINAPI WideCharToMultiByte(UINT, DWORD, LPCWSTR, int, LPSTR, int, LPCSTR, LPBOOL);
#endif
#ifndef WH_KEYBOARD_LL
#define WH_KEYBOARD_LL 13
#endif
#ifndef EM_SETMARGINS
#define EM_SETMARGINS 0x00D3
#endif
#ifndef EC_LEFTMARGIN
#define EC_LEFTMARGIN 1
#define EC_RIGHTMARGIN 2
#endif
#ifndef EM_GETFIRSTVISIBLELINE
#define EM_GETFIRSTVISIBLELINE 0x00CE
#endif
#ifndef EM_SCROLLCARET
#define EM_SCROLLCARET 0x00B7
#endif
typedef struct { DWORD vk, scan, flags, time; ULONG_PTR extra; } KLL;
typedef struct { DWORD cb, flags; HWND active, focus, capture, menuowner, movesize, caret; RECT rc; } GTI;
typedef BOOL (WINAPI *GetGUIThreadInfo_t)(DWORD, GTI *);
static GetGUIThreadInfo_t pGetGUIThreadInfo;

/* winsock, loaded by hand (tcc ships no ws2_32 import library) */
typedef struct { short family; unsigned short port; unsigned long addr; char zero[8]; } SIN;
typedef struct { WORD v, hv; char d[257], s[129]; unsigned short mx, mu; char *vi; } WSAD;
static int (WINAPI *wStartup)(WORD, WSAD *);
static UINT_PTR (WINAPI *wSocket)(int, int, int);
static int (WINAPI *wConnect)(UINT_PTR, const SIN *, int);
static int (WINAPI *wSend)(UINT_PTR, const char *, int, int);
static int (WINAPI *wRecv)(UINT_PTR, char *, int, int);
static int (WINAPI *wClose)(UINT_PTR);
static int (WINAPI *wSetOpt)(UINT_PTR, int, int, const char *, int);
static unsigned short (WINAPI *wHtons)(unsigned short);
static unsigned long (WINAPI *wAddr)(const char *);

/* registry, also by hand (no advapi32 import library either) */
static LONG (WINAPI *rCreate)(HKEY, LPCSTR, DWORD, LPSTR, DWORD, REGSAM, void *, HKEY *, DWORD *);
static LONG (WINAPI *rSet)(HKEY, LPCSTR, DWORD, DWORD, const BYTE *, DWORD);
static LONG (WINAPI *rClose)(HKEY);

static void load_apis(void)
{
    HMODULE w = LoadLibraryA("ws2_32.dll"), a = LoadLibraryA("advapi32.dll"), u = GetModuleHandleA("user32.dll");
    WSAD d;
    *(FARPROC *)&wStartup = GetProcAddress(w, "WSAStartup");
    *(FARPROC *)&wSocket = GetProcAddress(w, "socket");
    *(FARPROC *)&wConnect = GetProcAddress(w, "connect");
    *(FARPROC *)&wSend = GetProcAddress(w, "send");
    *(FARPROC *)&wRecv = GetProcAddress(w, "recv");
    *(FARPROC *)&wClose = GetProcAddress(w, "closesocket");
    *(FARPROC *)&wSetOpt = GetProcAddress(w, "setsockopt");
    *(FARPROC *)&wHtons = GetProcAddress(w, "htons");
    *(FARPROC *)&wAddr = GetProcAddress(w, "inet_addr");
    *(FARPROC *)&rCreate = GetProcAddress(a, "RegCreateKeyExA");
    *(FARPROC *)&rSet = GetProcAddress(a, "RegSetValueExA");
    *(FARPROC *)&rClose = GetProcAddress(a, "RegCloseKey");
    *(FARPROC *)&pGetGUIThreadInfo = GetProcAddress(u, "GetGUIThreadInfo");
    wStartup(0x0202, &d);
}

/* ---- the parts ------------------------------------------------------------------------- */
static HWND np, np_edit;            /* Notepad and its edit: the transcript */
static HWND fd, fd_edit, fd_send, fd_stop, fd_label;   /* the Find dialog: the input bar */
static HWND clk, cal, clk_page, clk_dlg, grp_time, grp_date, cost_label;   /* Date and Time: clock, calendar, the page holding them */
static HWND calc, calc_disp;       /* Calculator and its display */
static HWND me;                    /* our own message-only window */
static HFONT np_font;              /* Notepad's own font handle (valid inside Notepad) */
static DWORD np_tid;

#define WM_EV      (WM_APP + 1)
#define WM_TOOLRES (WM_APP + 2)
#define WM_SUBMIT  (WM_APP + 3)
#define WM_KEYCMD  (WM_APP + 4)

static void logf_(const char *fmt, ...)
{
    FILE *f = fopen("C:\\b3\\basilisk.log", "a");
    va_list ap;
    if (!f) return;
    va_start(ap, fmt); vfprintf(f, fmt, ap); va_end(ap);
    fputc('\n', f); fclose(f);
}

/* ---- text helpers ---------------------------------------------------------------------- */
static WCHAR *u8_to_w(const char *s, int n)
{
    int k = MultiByteToWideChar(CP_UTF8, 0, s, n, NULL, 0);
    WCHAR *w = (WCHAR *)malloc((k + 1) * sizeof(WCHAR));
    MultiByteToWideChar(CP_UTF8, 0, s, n, w, k);
    w[k] = 0;
    return w;
}
static char *w_to_cp(const WCHAR *w, UINT cp)
{
    int k = WideCharToMultiByte(cp, 0, w, -1, NULL, 0, NULL, NULL);
    char *s = (char *)malloc(k + 1);
    WideCharToMultiByte(cp, 0, w, -1, s, k, NULL, NULL);
    s[k] = 0;
    return s;
}
static char *cp_to_u8(const char *s, int n, UINT cp)
{
    int k = MultiByteToWideChar(cp, 0, s, n, NULL, 0);
    WCHAR *w = (WCHAR *)malloc((k + 1) * sizeof(WCHAR));
    char *r;
    MultiByteToWideChar(cp, 0, s, n, w, k);
    w[k] = 0;
    r = w_to_cp(w, CP_UTF8);
    free(w);
    return r;
}

/* ---- HTTP to the host (one request per connection) -------------------------------------- */
static char *http(const char *method, const char *path, const char *body, int blen, int *outlen, int timeout_ms)
{
    UINT_PTR s = wSocket(2, 1, 6);
    SIN a;
    char hdr[512], *buf = NULL, *p;
    int cap = 0, n = 0, r;
    if (s == (UINT_PTR)~0) return NULL;
    memset(&a, 0, sizeof a);
    a.family = 2; a.port = wHtons(8765); a.addr = wAddr("10.0.2.2");
    wSetOpt(s, 0xffff, 0x1006, (const char *)&timeout_ms, sizeof timeout_ms);   /* SO_RCVTIMEO */
    if (wConnect(s, &a, sizeof a)) { wClose(s); return NULL; }
    sprintf(hdr, "%s %s HTTP/1.0\r\nHost: x\r\nContent-Length: %d\r\n\r\n", method, path, blen);
    wSend(s, hdr, (int)strlen(hdr), 0);
    if (blen) {
        int off = 0;
        while (off < blen) { int k = wSend(s, body + off, blen - off, 0); if (k <= 0) break; off += k; }
    }
    for (;;) {
        if (cap - n < 8192) { cap = cap * 2 + 16384; buf = (char *)realloc(buf, cap + 1); }
        r = wRecv(s, buf + n, cap - n, 0);
        if (r <= 0) break;
        n += r;
    }
    wClose(s);
    if (!buf) return NULL;
    buf[n] = 0;
    p = strstr(buf, "\r\n\r\n");
    if (!p || strncmp(buf + 9, "200", 3)) { free(buf); return NULL; }
    p += 4;
    n -= (int)(p - buf);
    memmove(buf, p, n + 1);
    if (outlen) *outlen = n;
    return buf;
}

/* ---- the transcript --------------------------------------------------------------------- */
static int spin_at = -1;            /* char index of the spinner line, or -1 */
static DWORD spin_t0;
static int spin_i;
static int at_line_start = 1;       /* is the transcript's end at the start of a line? */
static int in_assistant;            /* inside an assistant text block (continuation indent) */

static int t_len(void) { return (int)SendMessageW(np_edit, WM_GETTEXTLENGTH, 0, 0); }

static int t_at_bottom(void)
{
    SCROLLINFO si;
    memset(&si, 0, sizeof si);
    si.cbSize = sizeof si; si.fMask = SIF_ALL;
    if (!GetScrollInfo(np_edit, SB_VERT, &si)) return 1;
    return si.nPos + (int)si.nPage >= si.nMax - 1;
}

/* append raw wide text at the end, keeping the reader's place if they scrolled up */
static void t_raw(const WCHAR *w)
{
    int bottom = t_at_bottom(), first = 0, n = t_len();
    if (!bottom) first = (int)SendMessageW(np_edit, EM_GETFIRSTVISIBLELINE, 0, 0);
    if (n > 150000) {     /* keep the edit light: drop the oldest third */
        int cut = n / 3;
        SendMessageW(np_edit, EM_SETSEL, 0, cut);
        SendMessageW(np_edit, EM_REPLACESEL, 0, (LPARAM)L"[...earlier transcript trimmed...]\r\n");
        n = t_len();
        if (spin_at >= 0) spin_at = -1;
    }
    SendMessageW(np_edit, EM_SETSEL, n, n);
    SendMessageW(np_edit, EM_REPLACESEL, 0, (LPARAM)w);
    if (bottom) {
        SendMessageW(np_edit, EM_SCROLLCARET, 0, 0);
    } else {
        int now = (int)SendMessageW(np_edit, EM_GETFIRSTVISIBLELINE, 0, 0);
        SendMessageW(np_edit, EM_LINESCROLL, 0, first - now);
    }
}

static void spin_off(void)
{
    if (spin_at < 0) return;
    SendMessageW(np_edit, EM_SETSEL, spin_at, t_len());
    SendMessageW(np_edit, EM_REPLACESEL, 0, (LPARAM)L"");
    spin_at = -1;
}
static int busy;
static const WCHAR *spin_word = L"Thinking";
static void spin_on(void)
{
    static const WCHAR *f[] = {L"\x00B7", L"\x2022", L"*", L"\x2022"};
    WCHAR b[160];
    int secs = (int)((GetTickCount() - spin_t0) / 1000);
    if (!busy) return;
    spin_off();
    spin_at = t_len();
    _snwprintf(b, 159, L"%s%s %s\x2026 (%ds \x00B7 esc to interrupt)", at_line_start ? L"" : L"\r\n",
             f[spin_i++ % 4], spin_word, secs);
    t_raw(b);
}

/* append UTF-8 text with Claude Code style indentation and our own word wrap, so wrapped lines
   keep their indent; \n becomes \r\n + indent */
static int cols = 90;               /* characters per transcript line (from layout) */
static int col;                     /* current column at the transcript's end */
static WCHAR word[256];             /* the word being written at the end of the transcript */
static int wlen;
static void t_put(const char *u8, int n, const WCHAR *indent)
{
    WCHAR *w = u8_to_w(u8, n), *o, *q;
    int i, ind = indent ? (int)wcslen(indent) : 0, cap;
    cap = (int)wcslen(w) * 2 + 64 + ind * 8;
    for (i = 0; w[i]; i++) if (w[i] == '\n') cap += ind + 2;
    o = (WCHAR *)malloc(cap * sizeof(WCHAR) + 4096);
    q = o;
#define FLUSH() do { *q = 0; if (*o) t_raw(o); q = o; } while (0)
    for (i = 0; w[i]; i++) {
        WCHAR c = w[i];
        if (c == '\r') continue;
        if (c == '\t') c = ' ';
        if (c == '\n') { *q++ = '\r'; *q++ = '\n'; at_line_start = 1; col = 0; wlen = 0; continue; }
        if (at_line_start && indent) { memcpy(q, indent, ind * sizeof(WCHAR)); q += ind; col = ind; }
        at_line_start = 0;
        if (col >= cols) {
            if (c == ' ') {                  /* the break falls on a space: just break */
                *q++ = '\r'; *q++ = '\n';
                memcpy(q, indent ? indent : L"", ind * sizeof(WCHAR)); q += ind;
                col = ind; wlen = 0;
                continue;
            }
            if (wlen > 0 && wlen < cols - ind - 1) {   /* carry the word to the next line */
                FLUSH();
                {
                    int L = t_len();
                    SendMessageW(np_edit, EM_SETSEL, L - wlen, L);
                    SendMessageW(np_edit, EM_REPLACESEL, 0, (LPARAM)L"");
                }
                *q++ = '\r'; *q++ = '\n';
                memcpy(q, indent ? indent : L"", ind * sizeof(WCHAR)); q += ind;
                memcpy(q, word, wlen * sizeof(WCHAR)); q += wlen;
                col = ind + wlen;
            } else {                         /* a word longer than the line: hard break */
                *q++ = '\r'; *q++ = '\n';
                memcpy(q, indent ? indent : L"", ind * sizeof(WCHAR)); q += ind;
                col = ind; wlen = 0;
            }
        }
        *q++ = c;
        col++;
        if (c == ' ') wlen = 0;
        else if (wlen < 255) word[wlen++] = c;
    }
    FLUSH();
#undef FLUSH
    free(o); free(w);
}
static void t_putw(const WCHAR *w)        /* literal wide pieces (no wrapping), \r\n already in place */
{
    int n = (int)wcslen(w), i;
    if (!n) return;
    t_raw(w);
    at_line_start = w[n - 1] == '\n';
    for (i = 0; i < n; i++) {
        if (w[i] == '\n') { col = 0; wlen = 0; }
        else if (w[i] != '\r') { col++; if (w[i] == ' ') wlen = 0; else if (wlen < 255) word[wlen++] = w[i]; }
    }
}
static void t_newline(void) { if (!at_line_start) t_putw(L"\r\n"); }
static int last_block_blank = 1;
static void t_block(void) { t_newline(); if (!last_block_blank) t_putw(L"\r\n"); last_block_blank = 1; }

/* ---- title and meter ----------------------------------------------------------------- */
static char model_name[64] = "Claude Haiku 5.5";
static char meter[64] = "$0.0000";
static char usage_note[128] = "";
static void set_title(void)
{
    char t[256];
    sprintf(t, "BASILISK III - %s", usage_note[0] ? usage_note : model_name);
    SetWindowTextA(np, t);
    if (calc_disp) {
        char m[96];
        sprintf(m, "session cost  %s ", meter);
        SendMessageA(calc_disp, WM_SETTEXT, 0, (LPARAM)m);
    }
}

/* ---- input history ------------------------------------------------------------------ */
#define NHIST 64
static WCHAR *hist[NHIST];
static int nhist, hist_at;

/* ---- tools (run here, inside XP) --------------------------------------------------- */
typedef struct { char id[64]; char *name, *a1, *a2, *a3; char *buf; } Tool;
static volatile HANDLE tool_proc;
static volatile int interrupted;
static const char *WORKDIR = "C:\\b3\\work";

static char *abspath(const char *p)
{
    char *r = (char *)malloc(MAX_PATH * 2);
    if (p[0] && (p[1] == ':' || (p[0] == '\\' && p[1] == '\\'))) strcpy(r, p);
    else if (p[0] == '\\' || p[0] == '/') sprintf(r, "C:%s", p);
    else sprintf(r, "%s\\%s", WORKDIR, p);
    { char *c; for (c = r; *c; c++) if (*c == '/') *c = '\\'; }
    return r;
}

typedef struct { char *p; int n, cap; } Buf;
static void b_add(Buf *b, const char *s, int n)
{
    if (n < 0) n = (int)strlen(s);
    if (b->n + n + 1 > b->cap) { b->cap = (b->n + n + 1) * 2 + 256; b->p = (char *)realloc(b->p, b->cap); }
    memcpy(b->p + b->n, s, n); b->n += n; b->p[b->n] = 0;
}

static char *tool_run(const char *cmd_u8, int *ok)
{
    SECURITY_ATTRIBUTES sa;
    HANDLE rd, wr;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    WCHAR *wc = u8_to_w(cmd_u8, -1);
    char *cmd = w_to_cp(wc, CP_ACP), *line, *res;
    Buf out = {0};
    DWORD t0 = GetTickCount(), code = 0;
    int timed_out = 0;
    free(wc);
    line = (char *)malloc(strlen(cmd) + 32);
    sprintf(line, "cmd.exe /c %s", cmd);
    memset(&sa, 0, sizeof sa); sa.nLength = sizeof sa; sa.bInheritHandle = TRUE;
    CreatePipe(&rd, &wr, &sa, 0);
    SetHandleInformation(rd, HANDLE_FLAG_INHERIT, 0);
    memset(&si, 0, sizeof si); si.cb = sizeof si;
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    si.hStdOutput = wr; si.hStdError = wr; si.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    CreateDirectoryA(WORKDIR, NULL);
    if (!CreateProcessA(NULL, line, NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, WORKDIR, &si, &pi)) {
        CloseHandle(rd); CloseHandle(wr); free(line); free(cmd);
        *ok = 0;
        return _strdup("could not start cmd.exe");
    }
    CloseHandle(wr);
    tool_proc = pi.hProcess;
    for (;;) {
        DWORD avail = 0, got = 0;
        char tmp[4096];
        if (PeekNamedPipe(rd, NULL, 0, NULL, &avail, NULL) && avail) {
            if (ReadFile(rd, tmp, avail > sizeof tmp ? sizeof tmp : avail, &got, NULL) && got) {
                if (out.n < 200000) b_add(&out, tmp, (int)got);
                continue;
            }
        }
        if (WaitForSingleObject(pi.hProcess, 30) == WAIT_OBJECT_0) {
            while (PeekNamedPipe(rd, NULL, 0, NULL, &avail, NULL) && avail &&
                   ReadFile(rd, tmp, avail > sizeof tmp ? sizeof tmp : avail, &got, NULL) && got)
                if (out.n < 200000) b_add(&out, tmp, (int)got);
            break;
        }
        if (interrupted || GetTickCount() - t0 > 60000) {
            timed_out = interrupted ? 2 : 1;
            TerminateProcess(pi.hProcess, 1);
        }
    }
    GetExitCodeProcess(pi.hProcess, &code);
    tool_proc = NULL;
    CloseHandle(pi.hProcess); CloseHandle(pi.hThread); CloseHandle(rd);
    free(line); free(cmd);
    if (!out.p) b_add(&out, "", 0);
    res = cp_to_u8(out.p, out.n, CP_OEMCP);
    free(out.p);
    {
        Buf r = {0};
        char tail[96];
        b_add(&r, res, -1);
        if (timed_out == 1) b_add(&r, "\n[stopped after 60 s]", -1);
        if (timed_out == 2) b_add(&r, "\n[interrupted by the user]", -1);
        sprintf(tail, "\n[exit code %lu]", (unsigned long)code);
        if (code && !timed_out) b_add(&r, tail, -1);
        free(res);
        res = r.p;
    }
    *ok = !timed_out;
    return res;
}

static char *read_all(const char *path, int *n)
{
    FILE *f = fopen(path, "rb");
    char *b;
    long sz;
    if (!f) return NULL;
    fseek(f, 0, SEEK_END); sz = ftell(f); fseek(f, 0, SEEK_SET);
    if (sz > 2000000) { fclose(f); return NULL; }
    b = (char *)malloc(sz + 1);
    *n = (int)fread(b, 1, sz, f);
    b[*n] = 0;
    fclose(f);
    return b;
}

static char *tool_read(const char *p_u8, int *ok)
{
    WCHAR *wp = u8_to_w(p_u8, -1);
    char *pa = w_to_cp(wp, CP_ACP), *path = abspath(pa), *raw, *u8, *s;
    int n, line = 1;
    Buf out = {0};
    free(wp); free(pa);
    raw = read_all(path, &n);
    if (!raw) { *ok = 0; sprintf(path, "cannot read %s", path); return path; }
    u8 = cp_to_u8(raw, n, CP_ACP);
    free(raw);
    for (s = u8; *s;) {      /* cat -n style */
        char num[16], *e = strchr(s, '\n');
        int len = e ? (int)(e - s) : (int)strlen(s);
        if (len && s[len - 1] == '\r') len--;
        sprintf(num, "%5d\t", line++);
        b_add(&out, num, -1); b_add(&out, s, len); b_add(&out, "\n", 1);
        if (out.n > 120000) { b_add(&out, "[file truncated here]\n", -1); break; }
        if (!e) break;
        s = e + 1;
    }
    if (!out.p) b_add(&out, "(empty file)", -1);
    free(u8); free(path);
    *ok = 1;
    return out.p;
}

/* UTF-8 with \n  ->  ANSI with \r\n, as XP's own tools expect */
static char *to_dos(const char *u8, int *n)
{
    WCHAR *w = u8_to_w(u8, -1);
    char *a = w_to_cp(w, CP_ACP), *o, *q, *s;
    free(w);
    o = (char *)malloc(strlen(a) * 2 + 1);
    for (s = a, q = o; *s; s++) {
        if (*s == '\r') continue;
        if (*s == '\n') *q++ = '\r';
        *q++ = *s;
    }
    *q = 0;
    *n = (int)(q - o);
    free(a);
    return o;
}

static char *tool_write(const char *p_u8, const char *content, int *ok)
{
    WCHAR *wp = u8_to_w(p_u8, -1);
    char *pa = w_to_cp(wp, CP_ACP), *path = abspath(pa), *data, *msg;
    int n, lines = 0, i;
    FILE *f;
    free(wp); free(pa);
    data = to_dos(content, &n);
    for (i = 0; i < n; i++) if (data[i] == '\n') lines++;
    f = fopen(path, "wb");
    msg = (char *)malloc(MAX_PATH * 2 + 64);
    if (!f) { *ok = 0; sprintf(msg, "cannot write %s", path); }
    else { fwrite(data, 1, n, f); fclose(f); *ok = 1; sprintf(msg, "wrote %d lines to %s", lines + (n && data[n - 1] != '\n'), path); }
    free(data); free(path);
    return msg;
}

static char *tool_edit(const char *p_u8, const char *old_u8, const char *new_u8, int *ok)
{
    WCHAR *wp = u8_to_w(p_u8, -1);
    char *pa = w_to_cp(wp, CP_ACP), *path = abspath(pa), *raw, *o, *nw, *hit, *msg;
    int n, on, nn, count = 0;
    FILE *f;
    free(wp); free(pa);
    msg = (char *)malloc(MAX_PATH * 2 + 96);
    raw = read_all(path, &n);
    if (!raw) { *ok = 0; sprintf(msg, "cannot read %s", path); free(path); return msg; }
    o = to_dos(old_u8, &on);
    nw = to_dos(new_u8, &nn);
    if (!strstr(raw, o) && !strstr(raw, "\r\n")) {   /* a file with bare \n line ends */
        free(o); free(nw);
        { WCHAR *w1 = u8_to_w(old_u8, -1), *w2 = u8_to_w(new_u8, -1); o = w_to_cp(w1, CP_ACP); nw = w_to_cp(w2, CP_ACP); free(w1); free(w2); }
        on = (int)strlen(o); nn = (int)strlen(nw);
    }
    for (hit = raw; on && (hit = strstr(hit, o)); hit += on) count++;
    if (count != 1) {
        *ok = 0;
        if (count) sprintf(msg, "old_string occurs %d times in %s; include more context so it is unique", count, path);
        else sprintf(msg, "old_string not found in %s", path);
    } else {
        hit = strstr(raw, o);
        f = fopen(path, "wb");
        if (!f) { *ok = 0; sprintf(msg, "cannot write %s", path); }
        else {
            fwrite(raw, 1, hit - raw, f); fwrite(nw, 1, nn, f); fwrite(hit + on, 1, n - (int)(hit - raw) - on, f);
            fclose(f);
            *ok = 1;
            sprintf(msg, "updated %s", path);
        }
    }
    free(raw); free(o); free(nw); free(path);
    return msg;
}

static DWORD WINAPI tool_thread(LPVOID p)
{
    Tool *t = (Tool *)p;
    int ok = 0, blen;
    char *res, *body, path[128];
    if (!strcmp(t->name, "run")) res = tool_run(t->a1, &ok);
    else if (!strcmp(t->name, "read_file")) res = tool_read(t->a1, &ok);
    else if (!strcmp(t->name, "write_file")) res = tool_write(t->a1, t->a2 ? t->a2 : "", &ok);
    else if (!strcmp(t->name, "edit_file")) res = tool_edit(t->a1, t->a2 ? t->a2 : "", t->a3 ? t->a3 : "", &ok);
    else { res = _strdup("unknown tool"); ok = 0; }
    blen = (int)strlen(res);
    body = (char *)malloc(blen + 4);
    sprintf(body, "%d\n%s", ok, res);
    {   /* draw it first (main thread), then report: the next call must not arrive before this result shows */
        /* posted, not sent: a sent message would be handled in the middle of the main thread's own
           cross-process calls into Notepad and tear the transcript */
        HANDLE done = CreateEventA(NULL, TRUE, FALSE, NULL);
        char **pack = (char **)malloc(4 * sizeof(char *));
        pack[0] = _strdup(t->name); pack[1] = _strdup(res); pack[2] = (char *)(INT_PTR)ok; pack[3] = (char *)done;
        PostMessageA(me, WM_TOOLRES, 0, (LPARAM)pack);
        WaitForSingleObject(done, 5000);
        CloseHandle(done);
    }
    sprintf(path, "/b3/tool?id=%s", t->id);
    {
        char *r = http("POST", path, body, (int)strlen(body), NULL, 20000);
        free(r);
    }
    free(res);
    free(body); free(t->buf); free(t);
    return 0;
}

static void show_tool_result(char **pack)
{
    char *name = pack[0], *res = pack[1];
    int ok = (int)(INT_PTR)pack[2];
    spin_off();
    {   /* drop leading blank lines (keep the first line's own indentation) */
        char *q = res;
        while (*q == ' ' || *q == '\r' || *q == '\n' || *q == '\t') { if (*q == '\n') res = q + 1; q++; }
        if (!*q) res = q;
    }
    {
        int e = (int)strlen(res);
        while (e > 0 && (res[e - 1] == '\r' || res[e - 1] == '\n' || res[e - 1] == ' ')) res[--e] = 0;
    }
    if (!strcmp(name, "run") || !strcmp(name, "read_file")) {
        /* first few lines, then a count, like Claude Code's folded output */
        char *s = res;
        int shown = 0, total = 0, i;
        Buf b = {0};
        for (i = 0; res[i]; i++) if (res[i] == '\n') total++;
        if (i && res[i - 1] != '\n') total++;
        if (!strcmp(name, "read_file")) {
            char m[64];
            sprintf(m, "read %d lines", total);
            b_add(&b, ok ? m : res, -1);
            shown = total;
        } else {
            while (*s && shown < 5) {
                char *e = strchr(s, '\n');
                int len = e ? (int)(e - s) : (int)strlen(s);
                if (len > 150) len = 150;
                if (shown) b_add(&b, "\n", 1);
                b_add(&b, s, len);
                shown++;
                if (!e) break;
                s = e + 1;
            }
            if (!b.p || !*b.p) { b_add(&b, "(no output)", -1); }
        }
        t_newline();
        t_putw(L"  \x2514 ");
        at_line_start = 0;
        t_put(b.p, -1, L"    ");
        if (total > shown) {
            char more[48];
            sprintf(more, "\n\xE2\x80\xA6 +%d lines", total - shown);
            t_put(more, -1, L"    ");
        }
        free(b.p);
    } else {
        t_newline();
        t_putw(L"  \x2514 ");
        at_line_start = 0;
        t_put(res, -1, L"    ");
    }
    t_newline();
    last_block_blank = 0;
    SetEvent((HANDLE)pack[3]);
    free(pack[0]); free(pack[1]); free(pack);
    spin_word = L"Working";
    spin_on();
}

/* ---- events from the host ------------------------------------------------------------- */
typedef struct { char kind; int n; char *data; } Ev;
static volatile LONG last_seq;

static DWORD WINAPI net_thread(LPVOID p)
{
    (void)p;
    for (;;) {
        char path[64];
        int n = 0;
        char *r;
        sprintf(path, "/b3/ev?after=%ld", last_seq);
        r = http("GET", path, NULL, 0, &n, 40000);
        if (!r) { Sleep(400); continue; }
        {   /* frames: "<seq> <kind> <len>\n<payload>" */
            char *s = r, *end = r + n;
            while (s < end) {
                long seq; char kind; int len;
                char *nl = (char *)memchr(s, '\n', end - s);
                Ev *e;
                if (!nl || sscanf(s, "%ld %c %d", &seq, &kind, &len) != 3) break;
                s = nl + 1;
                if (s + len > end) break;
                e = (Ev *)malloc(sizeof *e);
                e->kind = kind; e->n = len;
                e->data = (char *)malloc(len + 1);
                memcpy(e->data, s, len); e->data[len] = 0;
                s += len;
                last_seq = seq;
                PostMessageA(me, WM_EV, 0, (LPARAM)e);
            }
        }
        free(r);
    }
    return 0;
}

static void focus_input(void);
static void set_busy(int b)
{
    busy = b;
    EnableWindow(fd_stop, b);
    if (b) { spin_t0 = GetTickCount(); spin_word = L"Thinking"; spin_on(); }
    else spin_off();
}

static void handle_ev(Ev *e)
{
    switch (e->kind) {
    case 's':                         /* an assistant text block begins */
        spin_off();
        t_block();
        t_putw(L"\x2022 ");
        in_assistant = 1;
        last_block_blank = 0;
        break;
    case 't':                         /* streamed text */
        spin_off();
        t_put(e->data, e->n, L"  ");
        last_block_blank = 0;
        break;
    case 'c': {                       /* a tool call: id \x1f display \x1f name \x1f args... */
        Tool *t = (Tool *)calloc(1, sizeof *t);
        char *f[6] = {0}, *s;
        int k = 0;
        t->buf = e->data; e->data = NULL;
        for (s = t->buf, f[k++] = s; *s && k < 6; s++) if (*s == 0x1f) { *s = 0; f[k++] = s + 1; }
        lstrcpynA(t->id, f[0] ? f[0] : "", sizeof t->id);
        t->name = f[2] ? f[2] : (char *)""; t->a1 = f[3] ? f[3] : (char *)""; t->a2 = f[4]; t->a3 = f[5];
        spin_off();
        t_block();
        t_putw(L"\x2022 ");
        t_put(f[1] ? f[1] : "", -1, L"  ");
        t_newline();
        last_block_blank = 0;
        interrupted = 0;
        CloseHandle(CreateThread(NULL, 0, tool_thread, t, 0, NULL));
        spin_word = L"Running";
        spin_on();
        break;
    }
    case 'b':                         /* busy (model working) */
        set_busy(1);
        break;
    case 'd':                         /* turn done */
        set_busy(0);
        t_newline();
        in_assistant = 0;
        break;
    case 'e':                         /* an error line */
        spin_off();
        t_block();
        t_putw(L"  ! ");
        t_put(e->data, e->n, L"    ");
        t_newline();
        last_block_blank = 0;
        if (busy) spin_on();
        break;
    case 'x':                         /* a quiet note from the host */
        spin_off();
        t_block();
        t_put(e->data, e->n, L"");
        t_newline();
        last_block_blank = 0;
        if (busy) spin_on();
        break;
    case 'u': {                       /* usage: model|title note|meter */
        char *a = e->data, *b2 = strchr(a, '|'), *c = b2 ? strchr(b2 + 1, '|') : NULL;
        if (b2 && c) {
            *b2 = 0; *c = 0;
            lstrcpynA(model_name, a, sizeof model_name);
            lstrcpynA(usage_note, b2 + 1, sizeof usage_note);
            lstrcpynA(meter, c + 1, sizeof meter);
            set_title();
        }
        break;
    }
    case 'p': {                       /* paste into the prompt */
        WCHAR *w = u8_to_w(e->data, e->n), *q;
        for (q = w; *q; q++) if (*q == '\r' || *q == '\n' || *q == '\t') *q = ' ';
        SendMessageW(fd_edit, EM_REPLACESEL, TRUE, (LPARAM)w);
        free(w);
        break;
    }
    case 'w': {                       /* wheel / scroll lines from the page */
        int lines = atoi(e->data);
        SendMessageW(np_edit, EM_LINESCROLL, 0, lines);
        break;
    }
    case 'f':                         /* bring BASILISK back to the front */
        focus_input();
        break;
    case 'k':                         /* clear the transcript */
        spin_off();
        SetWindowTextW(np_edit, L"");
        at_line_start = 1; last_block_blank = 1;
        break;
    }
    free(e->data);
    free(e);
}

/* ---- the prompt ----------------------------------------------------------------------- */
static void submit(void)
{
    int n = (int)SendMessageW(fd_edit, WM_GETTEXTLENGTH, 0, 0);
    WCHAR *w;
    char *u8;
    if (n <= 0) return;
    w = (WCHAR *)malloc((n + 1) * sizeof(WCHAR));
    SendMessageW(fd_edit, WM_GETTEXT, n + 1, (LPARAM)w);
    SendMessageW(fd_edit, WM_SETTEXT, 0, (LPARAM)L"");
    if (nhist == NHIST) { free(hist[0]); memmove(hist, hist + 1, (NHIST - 1) * sizeof hist[0]); nhist--; }
    hist[nhist++] = _wcsdup(w);
    hist_at = nhist;
    /* echo it the way Claude Code does */
    spin_off();
    t_block();
    t_putw(L"> ");
    {
        char *e8 = w_to_cp(w, CP_UTF8);
        t_put(e8, -1, L"  ");
        free(e8);
    }
    t_newline();
    last_block_blank = 0;
    /* the Find Next button visibly presses */
    SendMessageW(fd_send, BM_SETSTATE, TRUE, 0);
    u8 = w_to_cp(w, CP_UTF8);
    {
        char *r = http("POST", "/b3/send", u8, (int)strlen(u8), NULL, 8000);
        if (!r) { t_putw(L"  ! the host did not answer; try again\r\n"); }
        free(r);
    }
    SendMessageW(fd_send, BM_SETSTATE, FALSE, 0);
    if (busy) spin_on();
    free(u8); free(w);
}

static void recall(int dir)
{
    if (!nhist) return;
    hist_at += dir;
    if (hist_at < 0) hist_at = 0;
    if (hist_at >= nhist) { hist_at = nhist; SendMessageW(fd_edit, WM_SETTEXT, 0, (LPARAM)L""); return; }
    SendMessageW(fd_edit, WM_SETTEXT, 0, (LPARAM)hist[hist_at]);
    SendMessageW(fd_edit, EM_SETSEL, 32767, 32767);
}

static void focus_input(void)
{
    /* XP only lets the foreground thread hand the foreground away: borrow its input state */
    DWORD me_tid = GetCurrentThreadId(), fg_tid = 0;
    HWND fg = GetForegroundWindow();
    if (IsIconic(np)) ShowWindow(np, SW_RESTORE);
    if (fg && fg != np) fg_tid = GetWindowThreadProcessId(fg, NULL);
    if (fg_tid && fg_tid != me_tid) AttachThreadInput(me_tid, fg_tid, TRUE);
    AttachThreadInput(me_tid, np_tid, TRUE);
    SetForegroundWindow(np);
    BringWindowToTop(np);
    SetFocus(fd_edit);
    AttachThreadInput(me_tid, np_tid, FALSE);
    if (fg_tid && fg_tid != me_tid) AttachThreadInput(me_tid, fg_tid, FALSE);
}

static HWND focus_of(DWORD tid)
{
    GTI g;
    memset(&g, 0, sizeof g);
    g.cb = sizeof g;
    if (pGetGUIThreadInfo && pGetGUIThreadInfo(tid, &g)) return g.focus;
    return NULL;
}

/* keys: Enter sends, Esc interrupts, PgUp/PgDn and Ctrl+arrows scroll, Up/Down recall */
static LRESULT CALLBACK kbd(int code, WPARAM wp, LPARAM lp)
{
    KLL *k = (KLL *)lp;
    if (code == HC_ACTION && (wp == WM_KEYDOWN || wp == WM_SYSKEYDOWN) && GetForegroundWindow() == np) {
        int ctrl = GetAsyncKeyState(VK_CONTROL) < 0;
        switch (k->vk) {
        case VK_RETURN: PostMessageA(me, WM_KEYCMD, 1, 0); return 1;
        case VK_ESCAPE: PostMessageA(me, WM_KEYCMD, 2, 0); return 1;
        case VK_PRIOR:  PostMessageA(me, WM_KEYCMD, 3, 0); return 1;
        case VK_NEXT:   PostMessageA(me, WM_KEYCMD, 4, 0); return 1;
        case VK_UP:     PostMessageA(me, WM_KEYCMD, ctrl ? 5 : 7, 0); return 1;
        case VK_DOWN:   PostMessageA(me, WM_KEYCMD, ctrl ? 6 : 8, 0); return 1;
        case VK_TAB:    return 1;
        case VK_HOME:   if (ctrl) { PostMessageA(me, WM_KEYCMD, 9, 0); return 1; } break;
        case VK_END:    if (ctrl) { PostMessageA(me, WM_KEYCMD, 10, 0); return 1; } break;
        }
        if (focus_of(np_tid) != fd_edit) PostMessageA(me, WM_KEYCMD, 11, 0);
    }
    return CallNextHookEx(NULL, code, wp, lp);
}

static void keycmd(int c)
{
    switch (c) {
    case 1: submit(); break;
    case 2: {
        char *r;
        interrupted = 1;
        if (tool_proc) TerminateProcess(tool_proc, 1);
        r = http("POST", "/b3/int", "", 0, NULL, 5000);
        free(r);
        SendMessageW(fd_stop, BM_SETSTATE, TRUE, 0);
        Sleep(120);
        SendMessageW(fd_stop, BM_SETSTATE, FALSE, 0);
        break;
    }
    case 3: SendMessageW(np_edit, WM_VSCROLL, SB_PAGEUP, 0); break;
    case 4: SendMessageW(np_edit, WM_VSCROLL, SB_PAGEDOWN, 0); break;
    case 5: SendMessageW(np_edit, EM_LINESCROLL, 0, -3); break;
    case 6: SendMessageW(np_edit, EM_LINESCROLL, 0, 3); break;
    case 7: recall(-1); break;
    case 8: recall(1); break;
    case 9: SendMessageW(np_edit, WM_VSCROLL, SB_TOP, 0); break;
    case 10: SendMessageW(np_edit, WM_VSCROLL, SB_BOTTOM, 0); break;
    case 11: focus_input(); break;
    }
}

/* ---- finding and assembling the parts ---------------------------------------------- */
typedef struct { const char *cls, *title; DWORD pid; HWND found; int any; } FindTop;
static BOOL CALLBACK ft_cb(HWND h, LPARAM lp)
{
    FindTop *f = (FindTop *)lp;
    char c[64], t[256];
    DWORD pid;
    if (!f->any && !IsWindowVisible(h)) return TRUE;
    GetClassNameA(h, c, sizeof c);
    if (f->cls && strcmp(c, f->cls)) return TRUE;
    GetWindowTextA(h, t, sizeof t);
    if (f->title && !strstr(t, f->title)) return TRUE;
    GetWindowThreadProcessId(h, &pid);
    if (f->pid && pid != f->pid) return TRUE;
    f->found = h;
    return FALSE;
}
static int find_hidden;      /* wait_top also accepts hidden windows (donors launched hidden) */
static HWND wait_top(const char *cls, const char *title, DWORD pid, int ms)
{
    DWORD end = GetTickCount() + ms;
    do {
        FindTop f;
        f.cls = cls; f.title = title; f.pid = pid; f.found = NULL; f.any = find_hidden;
        EnumWindows(ft_cb, (LPARAM)&f);
        if (f.found) return f.found;
        Sleep(40);
    } while ((LONG)(GetTickCount() - end) < 0);
    return NULL;
}
static DWORD launch(const char *cmdline, int show)
{
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    char cl[512];
    memset(&si, 0, sizeof si);
    si.cb = sizeof si; si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = (WORD)show;
    lstrcpynA(cl, cmdline, sizeof cl);
    if (!CreateProcessA(NULL, cl, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) return 0;
    WaitForInputIdle(pi.hProcess, 5000);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    return pi.dwProcessId;
}

/* largest roughly-square child: the analog clock in Date and Time */
typedef struct { HWND best; int area; } Big;
static BOOL CALLBACK dump_cb(HWND h, LPARAM lp)
{
    char c[64], t[64];
    RECT r;
    GetClassNameA(h, c, sizeof c); GetWindowTextA(h, t, sizeof t); GetWindowRect(h, &r);
    logf_("  child %p %s '%s' %ld,%ld %ldx%ld vis=%d id=%d", h, c, t, r.left, r.top, r.right - r.left, r.bottom - r.top,
          IsWindowVisible(h), GetDlgCtrlID(h));
    (void)lp;
    return TRUE;
}
static BOOL CALLBACK big_cb(HWND h, LPARAM lp)
{
    Big *b = (Big *)lp;
    char c[64];
    RECT r;
    int w, hh;
    GetClassNameA(h, c, sizeof c);
    if (!IsWindowVisible(h)) return TRUE;
    if (!strcmp(c, "Button") || !strcmp(c, "Static") || !strcmp(c, "Edit") || !strcmp(c, "ComboBox") ||
        !strcmp(c, "#32770") || !strcmp(c, "SysTabControl32")) return TRUE;
    GetWindowRect(h, &r);
    w = r.right - r.left; hh = r.bottom - r.top;
    if (w < 60 || hh < 60 || w > hh * 3 / 2 || hh > w * 3 / 2) return TRUE;
    if (w * hh > b->area) { b->area = w * hh; b->best = h; }
    return TRUE;
}

static void reg_notepad(void)
{
    HKEY k;
    DWORD v;
    if (!rCreate || rCreate(HKEY_CURRENT_USER, "Software\\Microsoft\\Notepad", 0, NULL, 0, KEY_ALL_ACCESS, NULL, &k, NULL)) return;
    rSet(k, "lfFaceName", 0, REG_SZ, (const BYTE *)"Lucida Console", 15);
    v = 100; rSet(k, "iPointSize", 0, REG_DWORD, (BYTE *)&v, 4);
    v = 400; rSet(k, "lfWeight", 0, REG_DWORD, (BYTE *)&v, 4);
    v = 0;   rSet(k, "lfCharSet", 0, REG_DWORD, (BYTE *)&v, 4);
    v = 0;   rSet(k, "lfItalic", 0, REG_DWORD, (BYTE *)&v, 4);
    v = 1;   rSet(k, "fWrap", 0, REG_DWORD, (BYTE *)&v, 4);
    v = 0;   rSet(k, "StatusBar", 0, REG_DWORD, (BYTE *)&v, 4);
    v = 0;   rSet(k, "fSaveWindowPositions", 0, REG_DWORD, (BYTE *)&v, 4);
    rClose(k);
}

static void make_child(HWND h, HWND parent)
{
    LONG st = GetWindowLongA(h, GWL_STYLE);
    st &= ~(WS_POPUP | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | DS_MODALFRAME | WS_DLGFRAME | WS_BORDER);
    st |= WS_CHILD | WS_CLIPSIBLINGS;
    SetWindowLongA(h, GWL_STYLE, st);
    SetWindowLongA(h, GWL_EXSTYLE, GetWindowLongA(h, GWL_EXSTYLE) & ~(WS_EX_DLGMODALFRAME | WS_EX_WINDOWEDGE | WS_EX_APPWINDOW));
    SetParent(h, parent);
}

static int lay_w, lay_h;
static DWORD lay_t;
#define SIDE 200
#define PAGE_H 590
#define BAR 40
typedef struct { HWND *h; int x, y, w, hh; } Part;
static Part parts[8];
static int nparts;
static void part_set(HWND *h, int x, int y, int w, int hh)
{
    int i;
    for (i = 0; i < nparts; i++) if (parts[i].h == h) break;
    if (i == nparts && nparts < 8) nparts++;
    parts[i].h = h; parts[i].x = x; parts[i].y = y; parts[i].w = w; parts[i].hh = hh;
}

/* the Date and Time page rearranges its own children now and then; put ours back, touching
   only what is wrong so nothing flickers */
static void keep_parts(void)
{
    int i;
    for (i = 0; i < nparts; i++) {
        HWND h = *parts[i].h;
        RECT r;
        POINT p;
        if (!h || !IsWindow(h)) continue;
        GetWindowRect(h, &r);
        p.x = r.left; p.y = r.top;
        ScreenToClient(GetParent(h), &p);
        if (!IsWindowVisible(h) || p.x != parts[i].x || p.y != parts[i].y ||
            r.right - r.left != parts[i].w || r.bottom - r.top != parts[i].hh) {
            SetWindowPos(h, HWND_TOP, parts[i].x, parts[i].y, parts[i].w, parts[i].hh, SWP_SHOWWINDOW | SWP_NOACTIVATE);
            logf_("kept part %d", i);
        }
    }
}
static int page_ready;       /* the page was arranged while it flew in: layout must not hide and redo it */
static void page_inner(void) /* the sidebar's inside: Time group with the clock, Date group with the calendar */
{
    int i;
    part_set(&grp_time, 8, 6, SIDE - 16, 176);
    part_set(&clk, (SIDE - 135) / 2, 26, 135, 146);
    part_set(&grp_date, 8, 190, SIDE - 16, 160);
    part_set(&cal, (SIDE - 162) / 2, 212, 162, 130);
    for (i = 0; i < nparts; i++) if (*parts[i].h && *parts[i].h != calc_disp)
        SetWindowPos(*parts[i].h, HWND_TOP, parts[i].x, parts[i].y, parts[i].w, parts[i].hh, SWP_SHOWWINDOW | SWP_NOACTIVATE);
}          /* when the last layout happened; the sidebar gets one settling repaint after it */
static void layout(void)
{
    RECT rc;
    int W, H, ex, tw, top = 0;
    GetClientRect(np, &rc);
    W = rc.right; H = rc.bottom;
    if (W == lay_w && H == lay_h) return;
    lay_w = W; lay_h = H;
    lay_t = GetTickCount();
    tw = clk_page ? W - SIDE : W;
    MoveWindow(np_edit, 0, 0, tw, H - BAR, TRUE);
    SendMessageW(np_edit, EM_SETMARGINS, EC_LEFTMARGIN | EC_RIGHTMARGIN, MAKELONG(10, 10));
    {
        HDC dc = GetDC(NULL);
        HFONT f = CreateFontA(-MulDiv(10, GetDeviceCaps(dc, LOGPIXELSY), 72), 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, FIXED_PITCH, "Lucida Console");
        HFONT old = (HFONT)SelectObject(dc, f);
        TEXTMETRICA tm;
        RECT er;
        GetTextMetricsA(dc, &tm);
        SelectObject(dc, old); DeleteObject(f); ReleaseDC(NULL, dc);
        GetClientRect(np_edit, &er);
        if (tm.tmAveCharWidth > 0) cols = (er.right - 20) / tm.tmAveCharWidth - 1;
        if (cols < 30) cols = 30;
    }
    if (clk_page) {
        /* arrange the page while it is hidden, then show it once: a themed page that is moved
           around while visible leaves stale copies of its controls behind */
        /* the page's themed texture is about 600 px tall and white at its top: anchor the page to
           the bottom and let Notepad's own white fill the strip above, where the meter sits */
        top = H - BAR - PAGE_H;
        if (top < 0) top = 0;
        part_set(&calc_disp, tw + 10, top > 34 ? (top - 24) / 2 : 6, SIDE - 20, 24);
        if (calc_disp)
            SetWindowPos(calc_disp, HWND_TOP, tw + 10, top > 34 ? (top - 24) / 2 : 6, SIDE - 20, 24, SWP_SHOWWINDOW | SWP_NOACTIVATE);
        if (page_ready) {
            page_inner();      /* records the places for the keeper; the children are already there */
            SetWindowPos(clk_page, HWND_TOP, tw, top, SIDE, H - BAR - top, SWP_NOACTIVATE);
        } else {
            ShowWindow(clk_page, SW_HIDE);
            SetWindowPos(clk_page, HWND_TOP, tw, top, SIDE, H - BAR - top, SWP_NOACTIVATE);
            page_inner();
            ShowWindow(clk_page, SW_SHOWNA);
        }
        set_title();
    }
    SetWindowPos(fd, HWND_TOP, 0, H - BAR, W, BAR, SWP_SHOWWINDOW);
    ex = W - 2 * 78 - 12;
    MoveWindow(fd_edit, 8, 8, ex - 16, 24, TRUE);
    MoveWindow(fd_send, ex, 7, 74, 26, TRUE);
    MoveWindow(fd_stop, ex + 78, 7, 74, 26, TRUE);
    /* only the bar: erasing all of Notepad would paint over the sidebar (Notepad does not clip children) */
    RedrawWindow(fd, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW);
}

static BOOL CALLBACK hide_cb(HWND h, LPARAM lp)
{
    if (h != fd_edit && h != fd_send && h != fd_stop) ShowWindow(h, SW_HIDE);
    (void)lp;
    return TRUE;
}

/* ---- the assembly, shown: the parts stand as their own windows, then fly in ------------- */
typedef struct { HWND h; RECT a, b; DWORD start, dur; int done; } Fly;
static double ease_io(double t) { return t < .5 ? 4 * t * t * t : 1 - (-2 * t + 2) * (-2 * t + 2) * (-2 * t + 2) / 2; }

/* move the flights along their paths together; each starts at its own offset */
static void fly(Fly *f, int n)
{
    DWORD t0 = GetTickCount();
    int left = n;
    while (left) {
        DWORD now = GetTickCount() - t0;
        int i;
        left = 0;
        for (i = 0; i < n; i++) {
            double t, e;
            int x, y, w, hh;
            if (f[i].done || !f[i].h) continue;
            left++;
            if (now < f[i].start) continue;
            t = (double)(now - f[i].start) / f[i].dur;
            if (t >= 1) { t = 1; f[i].done = 1; }
            e = ease_io(t);
            x = f[i].a.left + (int)((f[i].b.left - f[i].a.left) * e);
            y = f[i].a.top + (int)((f[i].b.top - f[i].a.top) * e);
            w = (f[i].a.right - f[i].a.left) + (int)(((f[i].b.right - f[i].b.left) - (f[i].a.right - f[i].a.left)) * e);
            hh = (f[i].a.bottom - f[i].a.top) + (int)(((f[i].b.bottom - f[i].b.top) - (f[i].a.bottom - f[i].a.top)) * e);
            SetWindowPos(f[i].h, NULL, x, y, w, hh, SWP_NOZORDER | SWP_NOACTIVATE);
        }
        /* let every window finish painting before the next step: a part moved again before the
           window under it repaints leaves a ghost of itself (UpdateWindow waits for the owner) */
        if (np) { UpdateWindow(np); if (np_edit) UpdateWindow(np_edit); }
        for (i = 0; i < n; i++) if (f[i].h && !f[i].done) UpdateWindow(f[i].h);
        Sleep(15);
    }
}

/* lift a child control out of its program's window: a free-floating top-level window, same spot */
static void float_out(HWND h)
{
    RECT r;
    LONG st = GetWindowLongA(h, GWL_STYLE);
    GetWindowRect(h, &r);
    SetWindowLongA(h, GWL_STYLE, (st & ~WS_CHILD) | WS_POPUP);
    SetParent(h, NULL);
    SetWindowPos(h, HWND_TOPMOST, r.left, r.top, r.right - r.left, r.bottom - r.top, SWP_NOACTIVATE | SWP_SHOWWINDOW);
}

static void restore_at(HWND h, int x, int y, int w, int hh)
{
    WINDOWPLACEMENT wp;
    memset(&wp, 0, sizeof wp); wp.length = sizeof wp;
    GetWindowPlacement(h, &wp);
    if (w < 0) w = wp.rcNormalPosition.right - wp.rcNormalPosition.left;
    if (hh < 0) hh = wp.rcNormalPosition.bottom - wp.rcNormalPosition.top;
    wp.rcNormalPosition.left = x; wp.rcNormalPosition.top = y;
    wp.rcNormalPosition.right = x + w; wp.rcNormalPosition.bottom = y + hh;
    wp.showCmd = SW_SHOWNOACTIVATE; wp.flags = 0;
    SetWindowPlacement(h, &wp);
}

static RECT rc_xywh(int x, int y, int w, int hh) { RECT r; r.left = x; r.top = y; r.right = x + w; r.bottom = y + hh; return r; }

static int assemble(void)
{
    DWORD pid;
    WINDOWPLACEMENT wp;
    RECT wa;
    reg_notepad();
    CreateDirectoryA("C:\\b3", NULL);
    CreateDirectoryA(WORKDIR, NULL);
    SystemParametersInfoA(SPI_GETWORKAREA, 0, &wa, 0);
    SetCursorPos(wa.right - 6, wa.bottom - 140);      /* the pointer rests at the edge */

    /* 1. the donors, each as itself: Notepad on the left, Date and Time on the right,
          Calculator below it, Notepad's Find box over Notepad */
    pid = launch("notepad.exe", SW_SHOWMINNOACTIVE);
    np = wait_top("Notepad", NULL, pid, 8000);
    if (!np) return 0;
    np_tid = GetWindowThreadProcessId(np, NULL);
    np_edit = FindWindowExA(np, NULL, "Edit", NULL);
    np_font = (HFONT)SendMessageA(np_edit, WM_GETFONT, 0, 0);
    SetWindowLongA(np_edit, GWL_STYLE, GetWindowLongA(np_edit, GWL_STYLE) | WS_CLIPSIBLINGS);
    restore_at(np, 24, 36, 560, 560);

    find_hidden = 1;              /* the next two start hidden and appear already in place */
    launch("rundll32.exe shell32.dll,Control_RunDLL timedate.cpl", SW_HIDE);
    clk_dlg = wait_top("#32770", "Date and Time", 0, 8000);
    if (clk_dlg) {
        EnumChildWindows(clk_dlg, dump_cb, 0);
        clk_page = FindWindowExA(clk_dlg, NULL, "#32770", NULL);
        if (clk_page) {
            clk = GetDlgItem(clk_page, 712);
            cal = GetDlgItem(clk_page, 711);
            grp_date = GetDlgItem(clk_page, 103);
            grp_time = GetDlgItem(clk_page, 104);
        }
        restore_at(clk_dlg, 604, 16, -1, -1);
    }
    pid = launch("calc.exe", SW_HIDE);
    calc = wait_top("SciCalc", NULL, pid, 8000);
    find_hidden = 0;
    if (calc) {
        calc_disp = GetDlgItem(calc, 403);
        restore_at(calc, wa.right - 490, wa.bottom - 330, -1, -1);
    }
    PostMessageA(np, WM_COMMAND, 21, 0);
    GetWindowThreadProcessId(np, &pid);
    fd = wait_top("#32770", "Find", pid, 5000);
    if (!fd) return 0;
    {
        RECT r;
        GetWindowRect(fd, &r);
        SetWindowPos(fd, HWND_TOP, 60, 470, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);
        (void)r;
    }
    Sleep(1300);                          /* a moment to see four ordinary programs */

    /* 2. Notepad grows to fill the screen, behind the others (they stay on top while they fly) */
    if (clk_dlg) SetWindowPos(clk_dlg, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    if (calc) SetWindowPos(calc, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    SetWindowPos(fd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    {
        Fly f[1];
        RECT r;
        GetWindowRect(np, &r);
        memset(f, 0, sizeof f);
        f[0].h = np; f[0].a = r; f[0].b = wa; f[0].dur = 1100;
        fly(f, 1);
    }
    memset(&wp, 0, sizeof wp); wp.length = sizeof wp;
    GetWindowPlacement(np, &wp);
    wp.showCmd = SW_SHOWMAXIMIZED;        /* final geometry now, so every part flies to its true place */
    SetWindowPlacement(np, &wp);
    Sleep(200);

    /* 3. the parts lift out of their programs and fly to where they will live */
    {
        RECT cr;
        POINT o = {0, 0};
        int W, H, top, tw, ph, n = 0;
        Fly f[3];
        memset(f, 0, sizeof f);
        GetClientRect(np, &cr);
        ClientToScreen(np, &o);
        W = cr.right; H = cr.bottom;
        tw = W - SIDE;
        top = H - BAR - PAGE_H; if (top < 0) top = 0;
        ph = H - BAR - top;
        {                                                 /* Notepad's own Find box: down to the bottom */
            RECT r;
            GetWindowRect(fd, &r);
            f[n].h = fd; f[n].a = r;
            f[n].b = rc_xywh(o.x + 6, o.y + H - (r.bottom - r.top) - 6, r.right - r.left, r.bottom - r.top);
            f[n].start = 0; f[n].dur = 1500; n++;
        }
        if (clk_page) {      /* the Date and Time page leaves its dialog and folds into a column, hidden */
            RECT r;
            HWND c = NULL;
            float_out(clk_page);
            ShowWindow(clk_page, SW_HIDE);
            ShowWindow(clk_dlg, SW_HIDE);
            GetWindowRect(clk_page, &r);
            /* everything else on the page hides, the time-zone label included: a static moved off its
               themed tab paints a flat grey patch */
            while ((c = FindWindowExA(clk_page, c, NULL, NULL)))
                if (c != clk && c != cal && c != grp_date && c != grp_time) ShowWindow(c, SW_HIDE);
            cost_label = NULL;
            SetWindowPos(clk_page, NULL, r.left, r.top, SIDE, ph, SWP_NOZORDER | SWP_NOACTIVATE);
            page_inner();
            ShowWindow(clk_page, SW_SHOWNA);
            f[n].h = clk_page; f[n].a = rc_xywh(r.left, r.top, SIDE, ph);
            f[n].b = rc_xywh(o.x + tw, o.y + top, SIDE, ph);
            f[n].start = 600; f[n].dur = 1700; n++;
        }
        if (calc_disp) {                                  /* Calculator's display, alone */
            RECT r;
            float_out(calc_disp);
            ShowWindow(calc, SW_HIDE);
            SendMessageA(calc_disp, EM_SETREADONLY, FALSE, 0);     /* white, like it is inside Calculator */
            SetWindowLongA(calc_disp, GWL_EXSTYLE, GetWindowLongA(calc_disp, GWL_EXSTYLE) | WS_EX_CLIENTEDGE);
            SetWindowPos(calc_disp, NULL, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED | SWP_NOACTIVATE);
            GetWindowRect(calc_disp, &r);
            f[n].h = calc_disp; f[n].a = r;
            f[n].b = rc_xywh(o.x + tw + 10, o.y + (top > 34 ? (top - 24) / 2 : 6), SIDE - 20, 24);
            f[n].start = 1300; f[n].dur = 1500; n++;
        }
        fly(f, n);
        Sleep(200);

        /* 4. landing: each part becomes part of Notepad exactly where it already is */
        if (clk_page) {
            SetWindowPos(clk_page, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
            make_child(clk_page, np);
            SetWindowPos(clk_page, HWND_TOP, tw, top, SIDE, ph, SWP_NOACTIVATE);
            page_ready = 1;
            /* the calendar and the Date group repaint now (never the clock: XOR hands) */
            if (grp_date) RedrawWindow(grp_date, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_UPDATENOW);
            if (cal) RedrawWindow(cal, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_UPDATENOW);
        }
        if (calc_disp) {
            LONG st = GetWindowLongA(calc_disp, GWL_STYLE);
            SetWindowPos(calc_disp, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
            SetWindowLongA(calc_disp, GWL_STYLE, (st & ~WS_POPUP) | WS_CHILD);
            SetParent(calc_disp, np);
            SetWindowPos(calc_disp, HWND_TOP, tw + 10, top > 34 ? (top - 24) / 2 : 6, SIDE - 20, 24, SWP_NOACTIVATE);
        }
    }
    fd_edit = GetDlgItem(fd, 1152);
    fd_send = GetDlgItem(fd, IDOK);
    fd_stop = GetDlgItem(fd, IDCANCEL);
    fd_label = GetDlgItem(fd, 0xFFFF);
    {   /* find the "Find what:" label (its id is -1) */
        HWND c = NULL;
        while ((c = FindWindowExA(fd, c, "Static", NULL))) {
            char t[32];
            GetWindowTextA(c, t, sizeof t);
            if (strstr(t, "ind")) { fd_label = c; break; }
        }
    }
    ShowWindow(fd, SW_HIDE);
    SetWindowPos(fd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    EnumChildWindows(fd, hide_cb, 0);
    /* new ids, so Notepad never runs a search or closes the bar when these are pressed */
    SetWindowLongA(fd_send, GWL_ID, 0x7701);
    SetWindowLongA(fd_stop, GWL_ID, 0x7702);
    SetWindowTextA(fd_send, "Send");
    SetWindowTextA(fd_stop, "Stop");
    if (fd_label) ShowWindow(fd_label, SW_HIDE);
    if (np_font) SendMessageA(fd_edit, WM_SETFONT, (WPARAM)np_font, TRUE);
    SendMessageA(fd_edit, EM_LIMITTEXT, 30000, 0);
    EnableWindow(fd_send, TRUE);
    EnableWindow(fd_stop, FALSE);
    make_child(fd, np);

    lay_w = lay_h = -1;
    layout();
    set_title();
    SetWindowTextW(np_edit, L"");
    return 1;
}

static LRESULT CALLBACK me_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    switch (m) {
    case WM_EV: handle_ev((Ev *)lp); return 0;
    case WM_TOOLRES: show_tool_result((char **)lp); return 0;
    case WM_KEYCMD: keycmd((int)wp); return 0;
    case WM_TIMER:
        if (wp == 1) {
            if (!IsWindow(np)) { PostQuitMessage(0); return 0; }
            layout();
            keep_parts();
            if (lay_t && GetTickCount() - lay_t > 700) {   /* the calendar does not repaint itself after a move */
                int i;
                lay_t = 0;
                /* never the clock: it draws its hands with XOR, and a forced repaint between its ticks
                   leaves a frozen ghost of the second hand */
                for (i = 0; i < nparts; i++) if (*parts[i].h && *parts[i].h != clk && *parts[i].h != grp_time)
                    RedrawWindow(*parts[i].h, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_UPDATENOW);
            }
            if (busy) spin_on();
            if (GetForegroundWindow() == np && focus_of(np_tid) != fd_edit) focus_input();
        }
        return 0;
    }
    return DefWindowProcA(h, m, wp, lp);
}

int WINAPI WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cl, int show)
{
    WNDCLASSA wc;
    MSG msg;
    char *hello;
    int n = 0;
    (void)hp; (void)cl; (void)show;
    load_apis();
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = me_proc; wc.hInstance = hi; wc.lpszClassName = "BasiliskIII";
    RegisterClassA(&wc);
    me = CreateWindowA("BasiliskIII", "BASILISK III", 0, 0, 0, 0, 0, NULL, NULL, hi, NULL);
    if (!assemble()) { MessageBoxA(NULL, "BASILISK could not find its parts.", "BASILISK", MB_ICONERROR); return 1; }

    t_putw(L"\x2022 BASILISK III  \x00B7  a Claude Code client assembled from Windows XP\r\n");
    t_putw(L"  Notepad keeps the transcript, its Find box takes your words, Date and Time\r\n");
    t_putw(L"  keeps the clock, Calculator keeps the bill. Tools run here, in C:\\b3\\work.\r\n\r\n");
    t_putw(L"  Enter send \x00B7 Esc interrupt \x00B7 PgUp/PgDn scroll \x00B7 Up/Down history \x00B7 /help\r\n");
    last_block_blank = 0;
    hello = http("GET", "/b3/hello", NULL, 0, &n, 8000);
    if (hello) {     /* "time Y M D h m s" (UTC): a restored snapshot wakes at the hour it was saved */
        int Y, M, D, h, mi, se;
        if (sscanf(hello, "time %d %d %d %d %d %d", &Y, &M, &D, &h, &mi, &se) == 6) {
            SYSTEMTIME st;
            memset(&st, 0, sizeof st);
            st.wYear = (WORD)Y; st.wMonth = (WORD)M; st.wDay = (WORD)D;
            st.wHour = (WORD)h; st.wMinute = (WORD)mi; st.wSecond = (WORD)se;
            SetSystemTime(&st);
        }
    }
    free(hello);
    CloseHandle(CreateThread(NULL, 0, net_thread, NULL, 0, NULL));
    SetWindowsHookExA(WH_KEYBOARD_LL, kbd, hi, 0);
    SetTimer(me, 1, 250, NULL);
    focus_input();
    logf_("assembled np=%p edit=%p find=%p clock=%p calc=%p", np, np_edit, fd, clk, calc_disp);
    {
        int i;
        for (i = 0; i < nparts; i++) {
            HWND h = *parts[i].h;
            RECT r;
            char t[64] = "";
            if (!h) { logf_("part %d null", i); continue; }
            GetWindowRect(h, &r);
            GetWindowTextA(h, t, sizeof t);
            logf_("part %d %p parent=%p vis=%d %ld,%ld %ldx%ld '%s'", i, h, GetParent(h), IsWindowVisible(h),
                  r.left, r.top, r.right - r.left, r.bottom - r.top, t);
        }
        logf_("page %p calc %p", clk_page, calc);
    }
    while (GetMessageA(&msg, NULL, 0, 0) > 0) { TranslateMessage(&msg); DispatchMessageA(&msg); }
    return 0;
}
