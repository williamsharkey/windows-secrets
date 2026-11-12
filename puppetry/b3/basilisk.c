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
#include <math.h>

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

/* ==== the suite: tabs, plan, files, usage, tools, settings ==================================
   Borrowed (still drawn by the program that made them): Notepad's edit (transcript), Notepad's
   Find dialog (prompt), Date and Time's tab control (the tabs), its page (clock, calendar),
   Calculator's display (the bill), MessageBox (permission prompts), shell32's copy animation.
   Created here, from the same Windows XP control classes: list views, tree view, status bar,
   trackbar, progress bar, group boxes, check boxes, and the drawn graphs, pie and map. */
typedef struct _TREEITEM *HTI;
typedef struct { HWND from; UINT_PTR id; UINT code; } NMH;
typedef struct { NMH hdr; int item, sub; UINT nst, ost, chg; POINT pt; LPARAM lp; } NMLV;
#define TCM_GETITEMCOUNT 0x1304
#define TCM_SETITEMA 0x1306
#define TCM_INSERTITEMA 0x1307
#define TCM_GETCURSEL 0x130B
#define TCM_SETCURSEL 0x130C
#define TCIF_TEXT 1
typedef struct { UINT mask; DWORD st, stm; LPSTR text; int cch, img; LPARAM lp; } TCI;
#define LVM_GETITEMCOUNT 0x1004
#define LVM_SETITEMA 0x1006
#define LVM_INSERTITEMA 0x1007
#define LVM_DELETEITEM 0x1008
#define LVM_DELETEALLITEMS 0x1009
#define LVM_GETNEXTITEM 0x100C
#define LVM_ENSUREVISIBLE 0x1013
#define LVM_INSERTCOLUMNA 0x101B
#define LVM_SETCOLUMNWIDTH 0x101E
#define LVM_SETITEMSTATE 0x102B
#define LVM_GETITEMSTATE 0x102C
#define LVM_GETITEMTEXTA 0x102D
#define LVM_SETITEMTEXTA 0x102E
#define LVM_SETEXTENDEDLISTVIEWSTYLE 0x1036
#define LVS_REPORT 1
#define LVS_SINGLESEL 4
#define LVS_SHOWSELALWAYS 8
#define LVS_NOCOLUMNHEADER 0x4000
#define LVS_NOSORTHEADER 0x8000
#define LVS_EX_GRIDLINES 1
#define LVS_EX_CHECKBOXES 4
#define LVS_EX_FULLROWSELECT 0x20
#define LVIF_TEXT 1
#define LVIF_STATE 8
#define LVIS_SELECTED 2
#define LVIS_STATEIMAGEMASK 0xF000
#define LVNI_SELECTED 2
#define LVCF_WIDTH 2
#define LVCF_TEXT 4
typedef struct { UINT mask; int item, sub; UINT st, stm; LPSTR text; int cch, img; LPARAM lp; int indent; } LVI;
typedef struct { UINT mask; int fmt, cx; LPSTR text; int cch, sub; } LVC;
#define TVM_INSERTITEMA 0x1100
#define TVM_DELETEITEM 0x1101
#define TVM_EXPAND 0x1102
#define TVM_GETNEXTITEM 0x110A
#define TVM_SELECTITEM 0x110B
#define TVM_GETITEMA 0x110C
#define TVGN_CARET 9
#define TVE_EXPAND 2
#define TVIF_TEXT 1
#define TVIF_PARAM 4
#define TVIF_STATE 8
#define TVIS_BOLD 0x10
#define TVS_HASBUTTONS 1
#define TVS_HASLINES 2
#define TVS_LINESATROOT 4
#define TVS_SHOWSELALWAYS 0x20
#define TVI_ROOT ((HTI)(ULONG_PTR)-0x10000)
#define TVI_LAST ((HTI)(ULONG_PTR)-0xFFFE)
typedef struct { UINT mask; HTI h; UINT st, stm; LPSTR text; int cch, img, simg, kids; LPARAM lp; } TVI;
typedef struct { HTI parent, after; TVI item; } TVINS;
#define SB_SETTEXTA (WM_USER + 1)
#define SB_SETPARTS (WM_USER + 4)
#define CCS_NORESIZE 4
#define CCS_NOPARENTALIGN 8
#define TBM_GETPOS WM_USER
#define TBM_SETPOS (WM_USER + 5)
#define TBM_SETRANGE (WM_USER + 6)
#define TBS_AUTOTICKS 1
#define PBM_SETMARQUEE (WM_USER + 10)
#define PBS_MARQUEE 8
#define ACM_OPENA (WM_USER + 100)
#define ACM_PLAY (WM_USER + 101)
#define ACM_STOP (WM_USER + 102)
#define ACS_CENTER 1
#define ACS_TRANSPARENT 2
#define NM_DBLCLK (-3)
#define TVN_SELCHANGEDA (-402)
#define LVN_ITEMCHANGED (-101)
#ifndef GWL_USERDATA
#define GWL_USERDATA (-21)
#endif

#define SIDE 200          /* the sidebar: meter, context pie, clock and calendar */
#define PAGE_H 360        /* the Date and Time page (Time and Date groups), anchored at the bottom */
#define BAR 40            /* the prompt (Notepad's Find dialog) */
#define TABH 26           /* the tab strip (Date and Time's tab control) */
#define STATH 22          /* the status bar */
#define STRIPH 66         /* the busy strip (shell32's copy animation) while a tool runs */
enum { T_CHAT, T_PLAN, T_FILES, T_USAGE, T_TOOLS, T_SETTINGS, NTABS };
enum { P_PLAN = 1, P_FILES, P_USAGE, P_TOOLS, P_SETTINGS, P_PIE = 10, P_STRIP };
static HWND tabs, status_bar, pie_wnd, strip, strip_anim, strip_prog, strip_label;
static HWND panel[NTABS];
static HWND lv_plan, lv_allow, ck_plan, ck_autoedit, ck_askrun;
static HWND tv_files, ed_preview, lb_path, bt_mention, bt_refresh, bt_savemem;
static HWND bt_analyze, bt_defrag, grp_u[6];
static HWND lv_tools, bt_endproc;
static HWND cb_model, tb_effort, ck_notify, bt_clear, bt_compact, bt_memory;
static HFONT ui_font, ui_bold, mono_font;
static HANDLE actx;
static int cur_tab, strip_on, tool_row = -1, suite_ready;
static DWORD tool_t0, turn_t0;
static char sel_path[MAX_PATH];
/* numbers from the host ('q' events) */
static long st_ctx, st_cache_r, st_cache_w, st_in, st_out, st_calls, st_tools, st_sys = 2600, st_compact = 100000;
static double st_usd, st_cap = 0.60;
static char st_effort[16] = "low", st_model[32] = "Claude Haiku 5.5", st_state[96] = "ready";
static long ctx_hist[64]; static int n_ctx;
static long rate_hist[64]; static int n_rate; static long rate_acc;
static void suite_status(void);
static void suite_show_tab(int t);
static void strip_show(int on, const char *label);
static void tools_add(const char *name, const char *details);
static void tools_done(int ok, int lines);
static void plan_set(const char *lines);
static void settings_sync(const char *kv);
static void files_refresh(void);
static void notify_done(void);
static int ask_permission(const char *name, const char *a1);
static void suite_init(void);
static void suite_create(int W, int H);
static void remote_tab(HWND tab, int idx, const char *text, int insert);
static void set_state(const char *s);
static void layout_main(void);
static HWND tab_ov;                  /* our invisible pane over the borrowed tabs: it takes the clicks */
static RECT tab_rc[NTABS];
static volatile int g_plan, g_autoedit, g_askrun = 1;   /* read by tool threads */
static volatile HWND perm_box;
static char strip_text[256];
static int chat_bottom = 1;      /* was the transcript at its end when Chat was left? */
static int lay_w, lay_h;
static DWORD lay_t;
#define TCM_GETITEMRECT 0x130A
#define CCS_NODIVIDER 0x40
static int syncing;
static void tab_rects(void);
static LRESULT CALLBACK tab_ov_proc(HWND h, UINT m, WPARAM wp, LPARAM lp);
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
static WCHAR spin_custom[128];     /* progress from the host, e.g. "Writing heli.c (9.4 KB)" */
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
    if (interrupted && !timed_out) timed_out = 2;     /* Esc or End Process killed it before the loop could */
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
    if (!raw) {
        char *m = (char *)malloc(strlen(path) + 40);
        *ok = 0;
        sprintf(m, "cannot read %s (no such file?)", path);
        free(path);
        return m;
    }
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

static char *tool_write(const char *p_u8, const char *content, int append, int *ok)
{
    WCHAR *wp = u8_to_w(p_u8, -1);
    char *pa = w_to_cp(wp, CP_ACP), *path = abspath(pa), *data, *msg;
    int n, lines = 0, i;
    FILE *f;
    free(wp); free(pa);
    data = to_dos(content, &n);
    for (i = 0; i < n; i++) if (data[i] == '\n') lines++;
    {   /* make any missing folders on the way (C:\b3\work\heli\game.c) */
        char *q;
        for (q = path + 3; *q; q++) if (*q == '\\') { *q = 0; CreateDirectoryA(path, NULL); *q = '\\'; }
    }
    f = fopen(path, append ? "ab" : "wb");
    msg = (char *)malloc(MAX_PATH * 2 + 64);
    if (!f) { *ok = 0; sprintf(msg, "cannot write %s", path); }
    else {
        fwrite(data, 1, n, f); fclose(f); *ok = 1;
        sprintf(msg, "%s %d lines %s %s", append ? "appended" : "wrote", lines + (n && data[n - 1] != '\n'), append ? "to" : "to", path);
    }
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
    int denied = ask_permission(t->name, t->a1);
    if (denied == 2) res = _strdup("Plan mode is on, so nothing may change. Read and look only, and propose the change as a plan (todo_write).");
    else if (denied) res = _strdup("The person denied this. Do not retry it; ask them, or choose another way.");
    else if (!strcmp(t->name, "run")) res = tool_run(t->a1, &ok);
    else if (!strcmp(t->name, "read_file")) res = tool_read(t->a1, &ok);
    else if (!strcmp(t->name, "write_file")) res = tool_write(t->a1, t->a2 ? t->a2 : "", t->a3 && t->a3[0] == '1', &ok);
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
    {
        int i, ln = 0;
        for (i = 0; res[i]; i++) if (res[i] == '\n') ln++;
        if (*res) ln++;
        tools_done(ok, ln);
        strip_show(0, NULL);
        set_state("working");
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
        set_state("writing");
        spin_off();
        t_block();
        t_putw(L"\x2022 ");
        in_assistant = 1;
        last_block_blank = 0;
        break;
    case 't':                         /* streamed text */
        rate_acc += e->n;
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
        {   /* the Tools tab gets a row; the busy strip says what runs (it shows if the tool takes a while) */
            WCHAR *w = u8_to_w(f[1] ? f[1] : "", -1);
            char *a = w_to_cp(w, CP_ACP);
            free(w);
            tools_add(t->name, f[1] ? f[1] : "");
            lstrcpynA(strip_text, a, sizeof strip_text);
            if (strip_label) SetWindowTextA(strip_label, a);
            free(a);
            set_state("running a tool");
        }
        CloseHandle(CreateThread(NULL, 0, tool_thread, t, 0, NULL));
        spin_word = L"Running";
        spin_on();
        break;
    }
    case 'b':                         /* busy (model working) */
        set_busy(1);
        turn_t0 = GetTickCount();
        set_state("working");
        break;
    case 'd':                         /* turn done */
        set_busy(0);
        t_newline();
        in_assistant = 0;
        set_state("ready");
        notify_done();
        break;
    case 'o':                         /* the plan (todo_write) */
        plan_set(e->data);
        break;
    case 'm':                         /* a setting changed by a slash command */
        settings_sync(e->data);
        break;
    case 'q': {                       /* numbers: ctx cache_r cache_w in out usd cap calls tools effort sys compact|model */
        char *bar = strchr(e->data, '|');
        char ef[16] = "", kv[32];
        if (bar) { *bar = 0; lstrcpynA(st_model, bar + 1, sizeof st_model); }
        sscanf(e->data, "%ld %ld %ld %ld %ld %lf %lf %ld %ld %15s %ld %ld", &st_ctx, &st_cache_r, &st_cache_w, &st_in, &st_out,
               &st_usd, &st_cap, &st_calls, &st_tools, ef, &st_sys, &st_compact);
        if (ef[0]) { lstrcpynA(st_effort, ef, sizeof st_effort); sprintf(kv, "effort=%s", ef); settings_sync(kv); }
        if (n_ctx == 64) { memmove(ctx_hist, ctx_hist + 1, 63 * sizeof ctx_hist[0]); n_ctx--; }
        ctx_hist[n_ctx++] = st_ctx;
        suite_status();
        if (pie_wnd) InvalidateRect(pie_wnd, NULL, FALSE);
        if (cur_tab == T_USAGE) InvalidateRect(panel[T_USAGE], NULL, FALSE);
        break;
    }
    case 'e':                         /* an error line */
        spin_off();
        t_block();
        t_putw(L"  ! ");
        t_put(e->data, e->n, L"    ");
        t_newline();
        last_block_blank = 0;
        if (busy) spin_on();
        break;
    case 'g': {                       /* progress while Claude composes a long tool input */
        WCHAR *w = u8_to_w(e->data, e->n);
        lstrcpynW(spin_custom, w, 127);
        free(w);
        spin_word = spin_custom;
        if (busy) spin_on();
        break;
    }
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
            if (cb_model) {
                syncing = 1;
                SendMessageA(cb_model, CB_SETCURSEL, strstr(a, "sonnet") ? 1 : 0, 0);
                syncing = 0;
            }
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
        if (lv_plan) SendMessageA(lv_plan, LVM_DELETEALLITEMS, 0, 0);
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
        {   /* a menu is open (the visitor right-clicked, or opened File/Edit), or a window is being
               moved or sized: every key belongs to Windows (Esc closes the menu, letters pick items) */
            GTI g;
            memset(&g, 0, sizeof g);
            g.cb = sizeof g;
            if (pGetGUIThreadInfo && pGetGUIThreadInfo(np_tid, &g) && (g.flags & (0x4 | 0x10 | 0x20 | 0x2)))
                return CallNextHookEx(NULL, code, wp, lp);   /* INMENUMODE, POPUPMENUMODE, SYSTEMMENUMODE, INMOVESIZE */
        }
        {   /* the suite's own controls: an editable one (CLAUDE.md in Files, the model list) keeps every key;
               the others (lists, the tree, the trackbar, buttons) keep their navigation keys */
            HWND f = focus_of(np_tid);
            int ours = f && f != fd_edit && f != tab_ov && GetWindowThreadProcessId(f, NULL) == GetCurrentThreadId();
            int typing_here = ours && ((f == ed_preview && !(GetWindowLongA(f, GWL_STYLE) & ES_READONLY)) ||
                                       f == cb_model || GetParent(f) == cb_model);
            int nav = k->vk == VK_LEFT || k->vk == VK_RIGHT || k->vk == VK_UP || k->vk == VK_DOWN || k->vk == VK_HOME ||
                      k->vk == VK_END || k->vk == VK_PRIOR || k->vk == VK_NEXT || k->vk == VK_SPACE || k->vk == VK_DELETE;
            if (k->vk == VK_TAB && ctrl) { PostMessageA(me, WM_KEYCMD, 13 | ((GetAsyncKeyState(VK_SHIFT) < 0) << 8), 0); return 1; }
            if (typing_here || (ours && nav && !ctrl)) return CallNextHookEx(NULL, code, wp, lp);
        }
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
        /* typing while the pointer has put focus elsewhere in BASILISK (the transcript, a button):
           the key goes to the prompt instead, not lost. Ctrl/Alt chords stay where they are
           (Ctrl+C copies a selection in the transcript). Keys we inject ourselves pass through. */
        if (!(k->flags & 0x10) && focus_of(np_tid) != fd_edit && !ctrl && GetAsyncKeyState(VK_MENU) >= 0 &&
            k->vk != VK_SHIFT && k->vk != VK_LSHIFT && k->vk != VK_RSHIFT && k->vk != VK_CAPITAL) {
            PostMessageA(me, WM_KEYCMD, 12 | (k->vk << 8), 0);
            return 1;
        }
    }
    return CallNextHookEx(NULL, code, wp, lp);
}

static void keycmd(int c)
{
    switch (c & 0xFF) {
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
    case 12: {      /* bring the prompt forward, then deliver the key that was typed elsewhere */
        INPUT in[2];
        WORD vk = (WORD)(c >> 8);
        focus_input();
        memset(in, 0, sizeof in);
        in[0].type = INPUT_KEYBOARD; in[0].ki.wVk = vk;
        in[1].type = INPUT_KEYBOARD; in[1].ki.wVk = vk; in[1].ki.dwFlags = KEYEVENTF_KEYUP;
        SendInput(2, in, sizeof(INPUT));
        break;
    }
    case 13:        /* Ctrl+Tab, Ctrl+Shift+Tab */
        suite_show_tab((cur_tab + ((c >> 8) ? NTABS - 1 : 1)) % NTABS);
        break;
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
    int W, H, ex, tw, top = 0, y1;
    GetClientRect(np, &rc);
    W = rc.right; H = rc.bottom;
    if (W == lay_w && H == lay_h) return;
    lay_w = W; lay_h = H;
    lay_t = GetTickCount();
    tw = clk_page ? W - SIDE : W;
    y1 = H - BAR - (status_bar ? STATH : 0);
    layout_main();
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
    if (tabs) {
        SetWindowPos(tabs, NULL, 2, 2, tw - 4, TABH, SWP_NOZORDER | SWP_NOACTIVATE);
        if (tab_ov) SetWindowPos(tab_ov, HWND_TOP, 2, 2, tw - 4, TABH, SWP_NOACTIVATE);
    }
    if (clk_page) {
        /* arrange the page while it is hidden, then show it once: a themed page that is moved
           around while visible leaves stale copies of its controls behind. The page sits at the
           bottom of the sidebar; above it the meter, then the context pie */
        top = y1 - PAGE_H;
        if (top < 34) top = 34;
        part_set(&calc_disp, tw + 10, 4, SIDE - 20, 24);
        if (calc_disp) SetWindowPos(calc_disp, HWND_TOP, tw + 10, 4, SIDE - 20, 24, SWP_SHOWWINDOW | SWP_NOACTIVATE);
        if (pie_wnd) SetWindowPos(pie_wnd, NULL, tw, 34, SIDE, top - 34, SWP_NOZORDER | SWP_NOACTIVATE);
        if (page_ready) {
            page_inner();      /* records the places for the keeper; the children are already there */
            SetWindowPos(clk_page, HWND_TOP, tw, top, SIDE, y1 - top, SWP_NOACTIVATE);
        } else {
            ShowWindow(clk_page, SW_HIDE);
            SetWindowPos(clk_page, HWND_TOP, tw, top, SIDE, y1 - top, SWP_NOACTIVATE);
            page_inner();
            ShowWindow(clk_page, SW_SHOWNA);
        }
        set_title();
    }
    SetWindowPos(fd, HWND_TOP, 0, y1, W, BAR, SWP_SHOWWINDOW);
    if (status_bar) SetWindowPos(status_bar, NULL, 0, H - STATH, W, STATH, SWP_NOZORDER | SWP_NOACTIVATE);
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
        for (i = 0; i < n; i++) if (f[i].h) RedrawWindow(f[i].h, NULL, NULL, RDW_UPDATENOW | RDW_ALLCHILDREN);
        {   /* the other donors still standing repaint what a passing part uncovered (children too) */
            HWND others[4];
            int k;
            others[0] = calc; others[1] = clk_dlg; others[2] = fd; others[3] = tabs;
            for (k = 0; k < 4; k++)
                if (others[k] && IsWindowVisible(others[k]))
                    RedrawWindow(others[k], NULL, NULL, RDW_UPDATENOW | RDW_ALLCHILDREN);
        }
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
    SetWindowLongA(h, GWL_EXSTYLE, GetWindowLongA(h, GWL_EXSTYLE) | WS_EX_TOOLWINDOW);   /* no taskbar button */
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
    DWORD pid, calc_pid;
    WINDOWPLACEMENT wp;
    RECT wa;
    reg_notepad();
    CreateDirectoryA("C:\\b3", NULL);
    CreateDirectoryA(WORKDIR, NULL);
    SystemParametersInfoA(SPI_GETWORKAREA, 0, &wa, 0);
    SetCursorPos(wa.right - 6, wa.bottom - 140);      /* the pointer rests at the edge */

    /* 1. the donors, each as itself: Notepad on the left, Date and Time on the right,
          Calculator below it, Notepad's Find box over Notepad */
    logf_("t %lu start", GetTickCount());
    {   /* all three start at once; each is then found as it appears */
        DWORD dt_pid;
        pid = launch("notepad.exe", SW_SHOWMINNOACTIVE);
        dt_pid = launch("rundll32.exe shell32.dll,Control_RunDLL timedate.cpl", SW_HIDE);
        calc_pid = launch("calc.exe", SW_HIDE);
        (void)dt_pid;
    }
    np = wait_top("Notepad", NULL, pid, 8000);
    if (!np) return 0;
    np_tid = GetWindowThreadProcessId(np, NULL);
    np_edit = FindWindowExA(np, NULL, "Edit", NULL);
    np_font = (HFONT)SendMessageA(np_edit, WM_GETFONT, 0, 0);
    SetWindowLongA(np_edit, GWL_STYLE, GetWindowLongA(np_edit, GWL_STYLE) | WS_CLIPSIBLINGS);
    restore_at(np, 24, 36, 560, 560);

    find_hidden = 1;              /* the next two start hidden and appear already in place */
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
    calc = wait_top("SciCalc", NULL, calc_pid, 8000);
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
    logf_("t %lu donors", GetTickCount());
    Sleep(450);                           /* a moment to see four ordinary programs */

    logf_("t %lu grow", GetTickCount());
    /* 2. Notepad grows to fill the screen, behind the others (they stay on top while they fly) */
    if (clk_dlg) SetWindowPos(clk_dlg, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    if (calc) SetWindowPos(calc, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    SetWindowPos(fd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    {
        Fly f[1];
        RECT r;
        GetWindowRect(np, &r);
        memset(f, 0, sizeof f);
        f[0].h = np; f[0].a = r; f[0].b = wa; f[0].dur = 480;
        fly(f, 1);
    }
    memset(&wp, 0, sizeof wp); wp.length = sizeof wp;
    GetWindowPlacement(np, &wp);
    wp.showCmd = SW_SHOWMAXIMIZED;        /* final geometry now, so every part flies to its true place */
    SetWindowPlacement(np, &wp);
    Sleep(100);

    /* 3. the parts lift out of their programs, one at a time, each moving mostly intact and
          then refining, quickly but one change at a time */
    {
        RECT cr;
        POINT o = {0, 0};
        int W, H, top, tw, ph, ex;
        GetClientRect(np, &cr);
        ClientToScreen(np, &o);
        W = cr.right; H = cr.bottom;
        tw = W - SIDE;
        top = H - BAR - STATH - PAGE_H; if (top < 34) top = 34;
        ph = H - BAR - STATH - top;
        ex = W - 2 * 78 - 12;
        fd_edit = GetDlgItem(fd, 1152);
        fd_send = GetDlgItem(fd, IDOK);
        fd_stop = GetDlgItem(fd, IDCANCEL);
        {   /* the "Find what:" label (its id is -1) */
            HWND c = NULL;
            fd_label = NULL;
            while ((c = FindWindowExA(fd, c, "Static", NULL))) {
                char t[32];
                GetWindowTextA(c, t, sizeof t);
                if (strstr(t, "ind")) { fd_label = c; break; }
            }
        }

        logf_("t %lu find", GetTickCount());
        /* Find: glides down to the bottom of Notepad, still itself */
        {
            Fly f[1];
            RECT r;
            memset(f, 0, sizeof f);
            GetWindowRect(fd, &r);
            f[0].h = fd; f[0].a = r;
            f[0].b = rc_xywh(o.x + 6, o.y + H - STATH - (r.bottom - r.top) - 6, r.right - r.left, r.bottom - r.top);
            f[0].dur = 450;
            fly(f, 1);
        }
        logf_("t %lu f.typed", GetTickCount());
        /* someone types into it */
        {
            const char *q = "find a connection to 2026";
            for (; *q; q++) { PostMessageA(fd_edit, WM_CHAR, (BYTE)*q, 0); Sleep(9); UpdateWindow(fd_edit); }
            Sleep(130);
        }
        logf_("t %lu f.drop", GetTickCount());
        /* what it won't need drops away, one control at a time */
        {
            static const int gone[] = {1041, 1056, 1057, 1072, 1040, 1038};
            int i;
            for (i = 0; i < 6; i++) {
                HWND c = GetDlgItem(fd, gone[i]);
                if (c && IsWindowVisible(c)) { ShowWindow(c, SW_HIDE); UpdateWindow(fd); Sleep(25); }
            }
            if (fd_label) { ShowWindow(fd_label, SW_HIDE); UpdateWindow(fd); Sleep(25); }
        }
        logf_("t %lu f.names", GetTickCount());
        /* its buttons take their new names (and new ids, so Notepad never searches or closes it) */
        SetWindowLongA(fd_send, GWL_ID, 0x7701);
        SetWindowLongA(fd_stop, GWL_ID, 0x7702);
        SetWindowTextA(fd_send, "Send"); UpdateWindow(fd_send); Sleep(80);
        SetWindowTextA(fd_stop, "Stop"); UpdateWindow(fd_stop); Sleep(80);
        logf_("t %lu f.stretch", GetTickCount());
        /* it stretches into the bar: the box and its edit and buttons move together */
        {
            RECT r, e0, s0, t0;
            POINT p0 = {0, 0};
            DWORD t_0 = GetTickCount();
            int dur = 340;
            GetWindowRect(fd, &r);
            ClientToScreen(fd, &p0);
            GetWindowRect(fd_edit, &e0); GetWindowRect(fd_send, &s0); GetWindowRect(fd_stop, &t0);
            OffsetRect(&e0, -p0.x, -p0.y); OffsetRect(&s0, -p0.x, -p0.y); OffsetRect(&t0, -p0.x, -p0.y);
            for (;;) {
                double t = (double)(GetTickCount() - t_0) / dur, e;
                int cw = p0.x - r.left, chh = p0.y - r.top;          /* border + caption */
                RECT fb;
                if (t > 1) t = 1;
                e = ease_io(t);
#define LERP(a, b) ((a) + (int)(((b) - (a)) * e))
                fb = rc_xywh(LERP(r.left, o.x - cw), LERP(r.top, o.y + H - STATH - BAR - chh), LERP(r.right - r.left, W + 2 * cw),
                             LERP(r.bottom - r.top, BAR + chh + cw));
                SetWindowPos(fd, NULL, fb.left, fb.top, fb.right - fb.left, fb.bottom - fb.top, SWP_NOZORDER | SWP_NOACTIVATE);
                MoveWindow(fd_edit, LERP(e0.left, 8), LERP(e0.top, 8), LERP(e0.right - e0.left, ex - 16), LERP(e0.bottom - e0.top, 24), TRUE);
                MoveWindow(fd_send, LERP(s0.left, ex), LERP(s0.top, 7), LERP(s0.right - s0.left, 74), LERP(s0.bottom - s0.top, 26), TRUE);
                MoveWindow(fd_stop, LERP(t0.left, ex + 78), LERP(t0.top, 7), LERP(t0.right - t0.left, 74), LERP(t0.bottom - t0.top, 26), TRUE);
#undef LERP
                UpdateWindow(np); UpdateWindow(np_edit); UpdateWindow(fd);
                if (t >= 1) break;
                Sleep(15);
            }
        }
        logf_("t %lu f.frame", GetTickCount());
        /* its frame goes: it is part of Notepad now; the words it was given clear */
        ShowWindow(fd, SW_HIDE);
        SetWindowPos(fd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
        EnumChildWindows(fd, hide_cb, 0);
        make_child(fd, np);
        SetWindowPos(fd, HWND_TOP, 0, H - STATH - BAR, W, BAR, SWP_NOACTIVATE | SWP_SHOWWINDOW);
        if (np_font) SendMessageA(fd_edit, WM_SETFONT, (WPARAM)np_font, TRUE);
        SendMessageA(fd_edit, EM_LIMITTEXT, 30000, 0);
        EnableWindow(fd_send, TRUE);
        EnableWindow(fd_stop, FALSE);
        UpdateWindow(fd);
        Sleep(100);
        SendMessageA(fd_edit, EM_SETSEL, 0, -1); UpdateWindow(fd_edit); Sleep(110);
        SendMessageA(fd_edit, WM_SETTEXT, 0, (LPARAM)""); UpdateWindow(fd_edit);

        logf_("t %lu page", GetTickCount());
        /* the Date and Time page leaves its dialog, folds into a column (hidden) and flies over */
        if (clk_page) {
            Fly f[1];
            RECT r;
            HWND c = NULL;
            memset(f, 0, sizeof f);
            float_out(clk_page);
            ShowWindow(clk_page, SW_HIDE);
            tabs = FindWindowExA(clk_dlg, NULL, "SysTabControl32", NULL);
            if (tabs) float_out(tabs);        /* its tabs stay standing where they were, with nothing in them */
            ShowWindow(clk_dlg, SW_HIDE);
            GetWindowRect(clk_page, &r);
            /* everything else on the page hides, the time-zone label included: a static moved off its
               themed tab paints a flat grey patch */
            while ((c = FindWindowExA(clk_page, c, NULL, NULL)))
                if (c != clk && c != cal && c != grp_date && c != grp_time) ShowWindow(c, SW_HIDE);
            cost_label = NULL;
            SetWindowPos(clk_page, HWND_TOPMOST, r.left, r.top, SIDE, ph, SWP_NOACTIVATE);
            page_inner();
            ShowWindow(clk_page, SW_SHOWNA);
            logf_("t %lu p.fly", GetTickCount());
            f[0].h = clk_page; f[0].a = rc_xywh(r.left, r.top, SIDE, ph);
            f[0].b = rc_xywh(o.x + tw, o.y + top, SIDE, ph);
            f[0].dur = 560;
            fly(f, 1);
            /* it stays standing, above everything, until Calculator has passed */
        }

        logf_("t %lu tabs", GetTickCount());
        /* Date and Time's tabs: they let go of their empty page, fly up to the top of Notepad, become
           Notepad's, and are renamed one at a time */
        if (tabs) {
            Fly f[1];
            RECT r;
            static const char *names[NTABS] = {"Chat", "Plan", "Files", "Usage", "Tools", "Settings"};
            int i, n;
            LONG st;
            GetWindowRect(tabs, &r);
            SetWindowPos(tabs, NULL, r.left, r.top, r.right - r.left, TABH, SWP_NOZORDER | SWP_NOACTIVATE);
            UpdateWindow(np); UpdateWindow(np_edit); UpdateWindow(tabs);
            Sleep(110);
            memset(f, 0, sizeof f);
            f[0].h = tabs; f[0].a = rc_xywh(r.left, r.top, r.right - r.left, TABH);
            f[0].b = rc_xywh(o.x + 2, o.y + 2, r.right - r.left, TABH);    /* whole: a control stretched in flight smears */
            f[0].dur = 420;
            fly(f, 1);
            st = GetWindowLongA(tabs, GWL_STYLE);
            SetWindowPos(tabs, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
            SetWindowLongA(tabs, GWL_STYLE, ((st & ~WS_POPUP) | WS_CHILD) & ~WS_CLIPSIBLINGS);
            SetParent(tabs, np);
            SetWindowPos(tabs, HWND_TOP, 2, 2, r.right - r.left, TABH, SWP_NOACTIVATE | SWP_SHOWWINDOW);
            UpdateWindow(np); UpdateWindow(np_edit);
            Sleep(60);
            SetWindowPos(tabs, NULL, 2, 2, tw - 4, TABH, SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOCOPYBITS);
            RedrawWindow(tabs, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_UPDATENOW);
            Sleep(70);
            n = (int)SendMessageA(tabs, TCM_GETITEMCOUNT, 0, 0);
            for (i = 0; i < NTABS; i++) {
                remote_tab(tabs, i, names[i], i >= n);
                UpdateWindow(tabs);
                Sleep(45);
            }
            SendMessageA(tabs, TCM_SETCURSEL, 0, 0);
        }

        logf_("t %lu calc", GetTickCount());
        /* Calculator: moves over whole, sheds its keys one by one, then its display slides into place */
        if (calc && calc_disp) {
            Fly f[1];
            RECT r, d;
            HWND kid[160];
            int nk = 0, i, j;
            HWND c = NULL;
            memset(f, 0, sizeof f);
            GetWindowRect(calc, &r);
            GetWindowRect(calc_disp, &d);
            f[0].h = calc; f[0].a = r;
            /* it parks against the right edge, over the sidebar, below where the meter will live */
            f[0].b = rc_xywh(o.x + W - (r.right - r.left) - 4, o.y + 40, r.right - r.left, r.bottom - r.top);
            f[0].dur = 430;
            fly(f, 1);
            logf_("t %lu c.shed", GetTickCount());
            while ((c = FindWindowExA(calc, c, NULL, NULL)) && nk < 160)
                if (c != calc_disp && IsWindowVisible(c)) kid[nk++] = c;
            {   /* bottom-right first, like a page being wiped (each place read once: they live in Calculator) */
                int key[160];
                for (i = 0; i < nk; i++) { RECT a; GetWindowRect(kid[i], &a); key[i] = a.top + a.left; }
                for (i = 0; i < nk; i++)
                    for (j = i + 1; j < nk; j++)
                        if (key[j] > key[i]) {
                            HWND t = kid[i]; int k2 = key[i];
                            kid[i] = kid[j]; kid[j] = t; key[i] = key[j]; key[j] = k2;
                        }
            }
            for (i = 0; i < nk;) {           /* in five sweeps, each one deferred batch (one repaint, not dozens) */
                int end = i + (nk + 4) / 5;
                HDWP dw = BeginDeferWindowPos(end - i);
                for (; i < nk && i < end; i++)
                    if (dw) dw = DeferWindowPos(dw, kid[i], NULL, 0, 0, 0, 0, SWP_HIDEWINDOW | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
                if (dw) EndDeferWindowPos(dw);
                UpdateWindow(calc);
                Sleep(30);
            }
            UpdateWindow(calc);
            Sleep(70);
            logf_("t %lu c.float", GetTickCount());
            float_out(calc_disp);
            ShowWindow(calc, SW_HIDE);
            SendMessageA(calc_disp, EM_SETREADONLY, FALSE, 0);     /* white, like it is inside Calculator */
            SetWindowLongA(calc_disp, GWL_EXSTYLE, GetWindowLongA(calc_disp, GWL_EXSTYLE) | WS_EX_CLIENTEDGE);
            SetWindowPos(calc_disp, NULL, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED | SWP_NOACTIVATE);
            GetWindowRect(calc_disp, &d);
            memset(f, 0, sizeof f);
            f[0].h = calc_disp; f[0].a = d;
            f[0].b = rc_xywh(o.x + tw + 10, o.y + 4, SIDE - 20, 24);
            f[0].dur = 330;
            fly(f, 1);
            {
                LONG st = GetWindowLongA(calc_disp, GWL_STYLE);
                SetWindowPos(calc_disp, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
                SetWindowLongA(calc_disp, GWL_STYLE, (st & ~WS_POPUP) | WS_CHILD);
                SetParent(calc_disp, np);
                SetWindowPos(calc_disp, HWND_TOP, tw + 10, 4, SIDE - 20, 24, SWP_NOACTIVATE);
            }
        }

        logf_("t %lu settle", GetTickCount());
        /* the page settles into Notepad */
        if (clk_page) {
            SetWindowPos(clk_page, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
            make_child(clk_page, np);
            SetWindowPos(clk_page, HWND_TOP, tw, top, SIDE, ph, SWP_NOACTIVATE);
            page_ready = 1;
            /* the calendar and the Date group repaint now (never the clock: XOR hands) */
            if (grp_date) RedrawWindow(grp_date, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_UPDATENOW);
            if (cal) RedrawWindow(cal, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_FRAME | RDW_UPDATENOW);
        }

        logf_("t %lu create", GetTickCount());
        /* the rest is made here, from the same XP control classes: the pages behind the tabs (hidden
           until chosen), the status bar, the context pie */
        suite_create(W, H);
    }

    lay_w = lay_h = -1;
    layout();
    logf_("t %lu laid", GetTickCount());
    UpdateWindow(np); UpdateWindow(np_edit);
    Sleep(60);
    if (status_bar) { ShowWindow(status_bar, SW_SHOWNA); UpdateWindow(status_bar); Sleep(80); }
    if (pie_wnd) { ShowWindow(pie_wnd, SW_SHOWNA); UpdateWindow(pie_wnd); }
    set_title();
    SetWindowTextW(np_edit, L"");
    return 1;
}


/* ==== the suite =========================================================================== */

/* XP's themed (Luna) controls come from comctl32 version 6, which a program gets through a
   manifest; tcc can't link one in, so the client writes it and activates it at run time */
static void suite_init(void)
{
    typedef struct { ULONG cb; DWORD fl; LPCSTR src; USHORT arch; LANGID lang; LPCSTR dir, res, app; HMODULE mod; } ACTX;
    typedef struct { DWORD sz, icc; } ICCX;
    HANDLE (WINAPI *mk_ctx)(ACTX *);
    BOOL (WINAPI *act)(HANDLE, ULONG_PTR *);
    BOOL (WINAPI *init)(ICCX *);
    HMODULE k = GetModuleHandleA("kernel32.dll"), cc;
    FILE *f = fopen("C:\\b3\\basilisk.manifest", "w");
    if (f) {
        fputs("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n"
              "<assembly xmlns=\"urn:schemas-microsoft-com:asm.v1\" manifestVersion=\"1.0\">\n"
              "<dependency><dependentAssembly><assemblyIdentity type=\"win32\" name=\"Microsoft.Windows.Common-Controls\" "
              "version=\"6.0.0.0\" processorArchitecture=\"X86\" publicKeyToken=\"6595b64144ccf1df\" language=\"*\"/>"
              "</dependentAssembly></dependency>\n</assembly>\n", f);
        fclose(f);
    }
    *(FARPROC *)&mk_ctx = GetProcAddress(k, "CreateActCtxA");
    *(FARPROC *)&act = GetProcAddress(k, "ActivateActCtx");
    if (mk_ctx && act) {
        ACTX a;
        ULONG_PTR cookie;
        memset(&a, 0, sizeof a);
        a.cb = sizeof a; a.src = "C:\\b3\\basilisk.manifest";
        actx = mk_ctx(&a);
        if (actx != INVALID_HANDLE_VALUE) act(actx, &cookie);
        else actx = NULL;
    }
    cc = LoadLibraryA("comctl32.dll");
    LoadLibraryA("shell32.dll");       /* loaded now, while nothing is on screen, not in the middle of the show */
    LoadLibraryA("uxtheme.dll");
    *(FARPROC *)&init = GetProcAddress(cc, "InitCommonControlsEx");
    if (init) { ICCX i; i.sz = sizeof i; i.icc = 0x3FFF; init(&i); }
    ui_font = CreateFontA(-11, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Tahoma");
    ui_bold = CreateFontA(-11, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Tahoma");
    mono_font = CreateFontA(-12, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, FIXED_PITCH, "Lucida Console");
}
static void thread_actx(void)          /* tool threads too, so their MessageBox wears Luna */
{
    BOOL (WINAPI *act)(HANDLE, ULONG_PTR *);
    ULONG_PTR cookie;
    *(FARPROC *)&act = GetProcAddress(GetModuleHandleA("kernel32.dll"), "ActivateActCtx");
    if (act && actx) act(actx, &cookie);
}

/* a tab control in another program (Date and Time's): its item text has to live in that program */
static void remote_tab(HWND tab, int idx, const char *text, int insert)
{
    DWORD pid;
    HANDLE ph;
    TCI it, *ri;
    char *rb;
    SIZE_T done;
    int n = (int)strlen(text) + 1;
    GetWindowThreadProcessId(tab, &pid);
    ph = OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE, FALSE, pid);
    if (!ph) return;
    ri = (TCI *)VirtualAllocEx(ph, NULL, sizeof it + n + 16, MEM_COMMIT, PAGE_READWRITE);
    if (ri) {
        rb = (char *)(ri + 1);
        WriteProcessMemory(ph, rb, text, n, &done);
        memset(&it, 0, sizeof it);
        it.mask = TCIF_TEXT; it.text = rb;
        WriteProcessMemory(ph, ri, &it, sizeof it, &done);
        SendMessageA(tab, insert ? TCM_INSERTITEMA : TCM_SETITEMA, idx, (LPARAM)ri);
        VirtualFreeEx(ph, ri, 0, MEM_RELEASE);
    }
    CloseHandle(ph);
}

static HWND mkx(DWORD ex, const char *cls, const char *text, DWORD style, int x, int y, int w, int hh, HWND parent, int id)
{
    HWND c = CreateWindowExA(ex, cls, text, WS_CHILD | WS_VISIBLE | style, x, y, w, hh, parent,
                             (HMENU)(INT_PTR)id, GetModuleHandleA(NULL), NULL);
    SendMessageA(c, WM_SETFONT, (WPARAM)ui_font, FALSE);
    return c;
}
#define mk(cls, text, style, x, y, w, hh, parent, id) mkx(0, cls, text, style, x, y, w, hh, parent, id)

static void lv_col(HWND lv, int i, const char *text, int w)
{
    LVC c;
    memset(&c, 0, sizeof c);
    c.mask = LVCF_TEXT | LVCF_WIDTH; c.text = (LPSTR)text; c.cx = w;
    SendMessageA(lv, LVM_INSERTCOLUMNA, i, (LPARAM)&c);
}
static int lv_add(HWND lv, int at, const char *text, int checked)
{
    LVI it;
    int i;
    memset(&it, 0, sizeof it);
    it.mask = LVIF_TEXT; it.item = at < 0 ? 0x7fffffff : at; it.text = (LPSTR)text;
    i = (int)SendMessageA(lv, LVM_INSERTITEMA, 0, (LPARAM)&it);
    if (checked >= 0) {
        memset(&it, 0, sizeof it);
        it.stm = LVIS_STATEIMAGEMASK; it.st = (checked ? 2 : 1) << 12;
        SendMessageA(lv, LVM_SETITEMSTATE, i, (LPARAM)&it);
    }
    return i;
}
static void lv_text(HWND lv, int i, int sub, const char *text)
{
    LVI it;
    memset(&it, 0, sizeof it);
    it.sub = sub; it.text = (LPSTR)text;
    SendMessageA(lv, LVM_SETITEMTEXTA, i, (LPARAM)&it);
}
static int lv_checked(HWND lv, int i)
{
    return ((SendMessageA(lv, LVM_GETITEMSTATE, i, LVIS_STATEIMAGEMASK) >> 12) & 0xF) == 2;
}
static void lv_get(HWND lv, int i, char *buf, int n)
{
    LVI it;
    memset(&it, 0, sizeof it);
    it.text = buf; it.cch = n;
    buf[0] = 0;
    SendMessageA(lv, LVM_GETITEMTEXTA, i, (LPARAM)&it);
}

/* ---- settings to the host -------------------------------------------------------------- */
static void settings_send(void)
{
    char body[160], *r;
    int e = (int)SendMessageA(tb_effort, TBM_GETPOS, 0, 0);
    static const char *ef[] = {"low", "medium", "high", "xhigh", "max"};
    if (syncing || !suite_ready) return;
    sprintf(body, "model=%s\neffort=%s\nplan=%d\n",
            SendMessageA(cb_model, CB_GETCURSEL, 0, 0) == 1 ? "sonnet" : "haiku", ef[e < 0 ? 0 : e > 4 ? 4 : e],
            SendMessageA(ck_plan, BM_GETCHECK, 0, 0) == BST_CHECKED);
    r = http("POST", "/b3/set", body, (int)strlen(body), NULL, 5000);
    free(r);
}
static void settings_sync(const char *kv)     /* the host says (after a slash command) */
{
    static const char *ef[] = {"low", "medium", "high", "xhigh", "max"};
    int i;
    syncing = 1;
    if (!strncmp(kv, "plan=", 5)) { g_plan = kv[5] == '1'; SendMessageA(ck_plan, BM_SETCHECK, g_plan ? BST_CHECKED : BST_UNCHECKED, 0); }
    if (!strncmp(kv, "effort=", 7))
        for (i = 0; i < 5; i++) if (!strcmp(kv + 7, ef[i])) SendMessageA(tb_effort, TBM_SETPOS, TRUE, i);
    syncing = 0;
}

/* ---- status bar --------------------------------------------------------------------------- */
static void suite_status(void)
{
    char t[160];
    if (!status_bar) return;
    SendMessageA(status_bar, SB_SETTEXTA, 0, (LPARAM)st_model);
    sprintf(t, "effort: %s", st_effort);
    SendMessageA(status_bar, SB_SETTEXTA, 1, (LPARAM)t);
    sprintf(t, "context %ld%%  (%ld of %ld tokens)", st_compact ? st_ctx * 100 / st_compact : 0, st_ctx, st_compact);
    SendMessageA(status_bar, SB_SETTEXTA, 2, (LPARAM)t);
    sprintf(t, "$%.4f of $%.2f", st_usd, st_cap);
    SendMessageA(status_bar, SB_SETTEXTA, 3, (LPARAM)t);
    SendMessageA(status_bar, SB_SETTEXTA, 4, (LPARAM)"C:\\b3\\work");
    SendMessageA(status_bar, SB_SETTEXTA, 5, (LPARAM)st_state);
}
static void set_state(const char *s) { lstrcpynA(st_state, s, sizeof st_state); suite_status(); }

/* ---- the context pie (the drive Properties pie, drawn: the shell's only knows disks) -------- */
static void paint_pie(HWND h, HDC dc)
{
    RECT r;
    int w, cx, x0, y0, pw, ph, d = 12, i;
    double frac = st_compact ? (double)st_ctx / st_compact : 0, a;
    HBRUSH bu = CreateSolidBrush(RGB(0, 0, 255)), bf = CreateSolidBrush(RGB(255, 0, 255));
    HBRUSH bud = CreateSolidBrush(RGB(0, 0, 128)), bfd = CreateSolidBrush(RGB(128, 0, 128));
    HPEN pn = CreatePen(PS_SOLID, 1, RGB(0, 0, 0)), op;
    HFONT of;
    char t[96];
    GetClientRect(h, &r);
    w = r.right;
    if (frac > 1) frac = 1;
    of = (HFONT)SelectObject(dc, ui_bold);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, RGB(0, 0, 0));
    TextOutA(dc, 12, 4, "Context window", 14);
    SelectObject(dc, ui_font);
    pw = w - 60; ph = 56; x0 = 30; y0 = 26; cx = x0 + pw / 2;
    op = (HPEN)SelectObject(dc, pn);
    a = 2 * 3.14159265358979 * frac;
    for (i = d; i >= 0; i--) {           /* the depth first, then the face: the way Windows draws it */
        int yy = y0 + i;
        int ex = cx + (int)(pw / 2 * cos(a)), ey = yy + ph / 2 - (int)(ph / 2 * sin(a));
        SelectObject(dc, i ? GetStockObject(NULL_PEN) : (HGDIOBJ)pn);
        SelectObject(dc, i ? bfd : bf);
        Ellipse(dc, x0, yy, x0 + pw, yy + ph);           /* free, all round; the used slice goes over it */
        SelectObject(dc, i ? bud : bu);
        if (frac > 0.001) {
            if (frac >= 0.999) Ellipse(dc, x0, yy, x0 + pw, yy + ph);
            else Pie(dc, x0, yy, x0 + pw, yy + ph, x0 + pw, yy + ph / 2, ex, ey);
        }
    }
    SelectObject(dc, pn);                /* the outline of the depth: the two sides and the lower rim */
    MoveToEx(dc, x0, y0 + ph / 2, NULL); LineTo(dc, x0, y0 + ph / 2 + d);
    MoveToEx(dc, x0 + pw - 1, y0 + ph / 2, NULL); LineTo(dc, x0 + pw - 1, y0 + ph / 2 + d);
    Arc(dc, x0, y0 + d, x0 + pw, y0 + d + ph, x0, y0 + d + ph / 2, x0 + pw, y0 + d + ph / 2);
    SelectObject(dc, op);
    {
        int ly = y0 + ph + d + 12;
        RECT sq;
        SetRect(&sq, 12, ly + 2, 24, ly + 14); FillRect(dc, &sq, bu); FrameRect(dc, &sq, (HBRUSH)GetStockObject(BLACK_BRUSH));
        sprintf(t, "Used     %ld tokens", st_ctx); TextOutA(dc, 30, ly, t, (int)strlen(t));
        SetRect(&sq, 12, ly + 20, 24, ly + 32); FillRect(dc, &sq, bf); FrameRect(dc, &sq, (HBRUSH)GetStockObject(BLACK_BRUSH));
        sprintf(t, "Free     %ld tokens", st_compact > st_ctx ? st_compact - st_ctx : 0); TextOutA(dc, 30, ly + 18, t, (int)strlen(t));
        sprintf(t, "Capacity %ld, then compact", st_compact); TextOutA(dc, 30, ly + 38, t, (int)strlen(t));
    }
    SelectObject(dc, of);
    DeleteObject(bu); DeleteObject(bf); DeleteObject(bud); DeleteObject(bfd); DeleteObject(pn);
}

/* ---- the Usage tab: Task Manager's meters and graphs, Disk Defragmenter's map ------------- */
static void tm_box(HDC dc, RECT *r)          /* Task Manager's black instrument well */
{
    FillRect(dc, r, (HBRUSH)GetStockObject(BLACK_BRUSH));
}
static void tm_meter(HDC dc, RECT r, double frac, const char *label)
{
    int i, rows = (r.bottom - r.top - 24) / 3, lit = (int)(rows * frac + 0.5);
    HBRUSH on = CreateSolidBrush(RGB(0, 255, 0)), off = CreateSolidBrush(RGB(0, 80, 0));
    tm_box(dc, &r);
    for (i = 0; i < rows; i++) {
        RECT b;
        int y = r.bottom - 22 - i * 3;
        SetRect(&b, r.left + 14, y - 2, (r.left + r.right) / 2 - 1, y);
        FillRect(dc, &b, i < lit ? on : off);
        SetRect(&b, (r.left + r.right) / 2 + 1, y - 2, r.right - 14, y);
        FillRect(dc, &b, i < lit ? on : off);
    }
    SetTextColor(dc, RGB(0, 255, 0));
    SetBkMode(dc, TRANSPARENT);
    {
        RECT t = r;
        t.top = r.bottom - 18;
        DrawTextA(dc, label, -1, &t, DT_CENTER | DT_SINGLELINE);
    }
    DeleteObject(on); DeleteObject(off);
}
static void tm_graph(HDC dc, RECT r, const long *v, int n, long max)
{
    HPEN grid = CreatePen(PS_SOLID, 1, RGB(0, 128, 64)), line = CreatePen(PS_SOLID, 1, RGB(0, 255, 0)), op;
    int x, y, i;
    tm_box(dc, &r);
    op = (HPEN)SelectObject(dc, grid);
    for (y = r.bottom - 12; y > r.top; y -= 12) { MoveToEx(dc, r.left, y, NULL); LineTo(dc, r.right, y); }
    for (x = r.right - 12; x > r.left; x -= 12) { MoveToEx(dc, x, r.top, NULL); LineTo(dc, x, r.bottom); }
    SelectObject(dc, line);
    if (max <= 0) max = 1;
    for (i = 0; i < n; i++) {
        int px = r.right - 2 - (n - 1 - i) * (r.right - r.left - 4) / 63;
        int py = r.bottom - 2 - (int)((double)v[i] * (r.bottom - r.top - 4) / max);
        if (py < r.top + 2) py = r.top + 2;
        if (i == 0) MoveToEx(dc, px, py, NULL); else LineTo(dc, px, py);
    }
    SelectObject(dc, op);
    DeleteObject(grid); DeleteObject(line);
}
static void defrag_band(HDC dc, RECT r, long sys, long cached, long fresh, long cap)
{
    /* Disk Defragmenter's colours: green unmovable (system prompt and tools), blue contiguous (cached),
       red fragmented (new since the cache), white free */
    long parts[3]; COLORREF col[3];
    int x, k, cols = (r.right - r.left - 4) / 3;
    long acc = 0, per = cap / (cols ? cols : 1);
    parts[0] = sys; parts[1] = cached; parts[2] = fresh;
    col[0] = RGB(0, 160, 0); col[1] = RGB(0, 0, 230); col[2] = RGB(230, 0, 0);
    FillRect(dc, &r, (HBRUSH)GetStockObject(WHITE_BRUSH));
    FrameRect(dc, &r, (HBRUSH)GetStockObject(GRAY_BRUSH));
    if (per < 1) per = 1;
    for (k = 0, x = 0; k < 3; k++) {
        long left = parts[k];
        HBRUSH b = CreateSolidBrush(col[k]);
        while (left > 0 && x < cols) {
            RECT s;
            SetRect(&s, r.left + 2 + x * 3, r.top + 2, r.left + 2 + x * 3 + 2, r.bottom - 2);
            FillRect(dc, &s, b);
            left -= per; x++;
        }
        DeleteObject(b);
        acc += parts[k];
    }
    (void)acc;
}
static HANDLE (WINAPI *pOpenTheme)(HWND, LPCWSTR);
static HRESULT (WINAPI *pDrawThemeBg)(HANDLE, HDC, int, int, const RECT *, const RECT *);
static HANDLE th_button;
static void group_box(HDC dc, int x, int y, int w, int hh, const char *label)
{
    RECT r;
    SIZE sz;
    int sv;
    HFONT of = (HFONT)SelectObject(dc, ui_font);
    GetTextExtentPoint32A(dc, label, (int)strlen(label), &sz);
    SetRect(&r, x, y + sz.cy / 2, x + w, y + hh);
    sv = SaveDC(dc);
    ExcludeClipRect(dc, x + 7, y, x + 9 + sz.cx + 2, y + sz.cy);
    if (th_button && pDrawThemeBg) pDrawThemeBg(th_button, dc, 4 /* BP_GROUPBOX */, 1, &r, NULL);
    else DrawEdge(dc, &r, EDGE_ETCHED, BF_RECT);
    RestoreDC(dc, sv);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, th_button ? RGB(0, 70, 213) : RGB(0, 0, 0));
    TextOutA(dc, x + 9, y, label, (int)strlen(label));
    SelectObject(dc, of);
}
static void paint_usage(HWND h, HDC dc)
{
    RECT r, g;
    HFONT of = (HFONT)SelectObject(dc, ui_font);
    char t[200];
    long sys = st_sys, cached = st_cache_r > sys ? st_cache_r - sys : st_cache_r, fresh;
    int pw, i;
    GetClientRect(h, &r);
    pw = r.right;
    fresh = st_ctx - sys - cached; if (fresh < 0) fresh = 0;
    group_box(dc, 10, 8, 114, 146, "Context");
    group_box(dc, 132, 8, pw - 142, 146, "Context, call by call");
    group_box(dc, 10, 158, 114, 146, "Output");
    group_box(dc, 132, 158, pw - 142, 146, "Output tokens per second");
    group_box(dc, 10, 312, 270, 152, "Totals");
    group_box(dc, 288, 312, pw - 298, r.bottom - 320, "Context map");
    sprintf(t, "%ld%%", st_compact ? st_ctx * 100 / st_compact : 0);
    SetRect(&g, 22, 30, 112, 142); tm_meter(dc, g, st_compact ? (double)st_ctx / st_compact : 0, t);
    SetRect(&g, 142, 30, pw - 22, 142); tm_graph(dc, g, ctx_hist, n_ctx, st_compact);
    {
        long rh[64];
        long mx = 40;
        for (i = 0; i < n_rate; i++) { rh[i] = rate_hist[i]; if (rh[i] > mx) mx = rh[i]; }
        sprintf(t, "%ld/s", n_rate ? rate_hist[n_rate - 1] : 0);
        SetRect(&g, 22, 180, 112, 292); tm_meter(dc, g, (double)(n_rate ? rate_hist[n_rate - 1] : 0) / mx, t);
        SetRect(&g, 142, 180, pw - 22, 292); tm_graph(dc, g, rh, n_rate, mx);
    }
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, RGB(0, 0, 0));
    {
        static const char *nm[] = {"Context now", "Cached (reused)", "Input, all calls", "Output, all calls", "API calls", "Tool runs", "Spent"};
        long val[6];
        int y = 336;
        val[0] = st_ctx; val[1] = st_cache_r; val[2] = st_in; val[3] = st_out; val[4] = st_calls; val[5] = st_tools;
        for (i = 0; i < 7; i++, y += 18) {
            TextOutA(dc, 24, y, nm[i], (int)strlen(nm[i]));
            if (i < 6) sprintf(t, "%ld", val[i]); else sprintf(t, "$%.4f of $%.2f", st_usd, st_cap);
            {
                RECT v;
                SetRect(&v, 120, y, 268, y + 16);
                DrawTextA(dc, t, -1, &v, DT_RIGHT | DT_SINGLELINE);
            }
        }
    }
    {
        int x0 = 298, x1 = pw - 22;
        long after = sys + 400;
        TextOutA(dc, x0, 334, "Context now:", 12);
        SetRect(&g, x0, 352, x1, 386); defrag_band(dc, g, sys, cached, fresh, st_compact);
        TextOutA(dc, x0, 394, "After Defragment (estimated):", 29);
        SetRect(&g, x0, 412, x1, 446); defrag_band(dc, g, sys, after - sys, 0, st_compact);
        {
            static const char *lg[] = {"System prompt and tools", "Cached conversation", "New since the cache", "Free"};
            COLORREF lc[4];
            int k, lx = x0, ly = 458;
            lc[0] = RGB(0, 160, 0); lc[1] = RGB(0, 0, 230); lc[2] = RGB(230, 0, 0); lc[3] = RGB(255, 255, 255);
            for (k = 0; k < 4; k++) {
                RECT sq;
                HBRUSH b = CreateSolidBrush(lc[k]);
                SetRect(&sq, lx, ly + 2, lx + 10, ly + 12);
                FillRect(dc, &sq, b); FrameRect(dc, &sq, (HBRUSH)GetStockObject(GRAY_BRUSH));
                DeleteObject(b);
                TextOutA(dc, lx + 14, ly, lg[k], (int)strlen(lg[k]));
                lx += k == 1 ? 150 : 160;
                if (k == 1) { lx = x0; ly += 18; }
            }
        }
        sprintf(t, "Past %ld tokens BASILISK compacts by itself. Defragment does it now: the conversation is", st_compact);
        TextOutA(dc, x0, 500, t, (int)strlen(t));
        sprintf(t, "summarised and continues from the summary. Files in C:\\b3\\work stay.");
        TextOutA(dc, x0, 516, t, (int)strlen(t));
    }
    SelectObject(dc, of);
}

/* ---- the panels -------------------------------------------------------------------------- */
static void suite_command(int id, int code, HWND c);
static void suite_notify(NMH *n);
static LRESULT CALLBACK panel_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    int kind = (int)GetWindowLongA(h, GWL_USERDATA);
    switch (m) {
    case WM_ERASEBKGND: {
        RECT r;
        if (kind == P_USAGE || kind == P_PIE) return 1;     /* painted whole, from a buffer */
        GetClientRect(h, &r);
        FillRect((HDC)wp, &r, (HBRUSH)GetStockObject(WHITE_BRUSH));
        return 1;
    }
    case WM_PRINTCLIENT: {
        RECT r;
        GetClientRect(h, &r);
        FillRect((HDC)wp, &r, (HBRUSH)GetStockObject(WHITE_BRUSH));
        return 0;
    }
    case WM_CTLCOLORSTATIC:
    case WM_CTLCOLORBTN:
        SetBkColor((HDC)wp, RGB(255, 255, 255));
        return (LRESULT)GetStockObject(WHITE_BRUSH);
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(h, &ps);
        if (kind == P_USAGE || kind == P_PIE) {
            RECT r;
            HDC m;
            HBITMAP bm, ob;
            GetClientRect(h, &r);
            m = CreateCompatibleDC(dc);
            bm = CreateCompatibleBitmap(dc, r.right, r.bottom);
            ob = (HBITMAP)SelectObject(m, bm);
            FillRect(m, &r, (HBRUSH)GetStockObject(WHITE_BRUSH));
            if (kind == P_USAGE) paint_usage(h, m); else paint_pie(h, m);
            BitBlt(dc, 0, 0, r.right, r.bottom, m, 0, 0, SRCCOPY);
            SelectObject(m, ob); DeleteObject(bm); DeleteDC(m);
        } else if (kind == P_STRIP) {
            RECT r, l;
            HBRUSH b = CreateSolidBrush(RGB(172, 168, 153));
            GetClientRect(h, &r);
            SetRect(&l, 0, 0, r.right, 1);
            FillRect(dc, &l, b);
            DeleteObject(b);
        }
        EndPaint(h, &ps);
        return 0;
    }
    case WM_COMMAND: suite_command(LOWORD(wp), HIWORD(wp), (HWND)lp); return 0;
    case WM_NOTIFY: suite_notify((NMH *)lp); return 0;
    case WM_HSCROLL: if ((HWND)lp == tb_effort && LOWORD(wp) == 8 /* TB_ENDTRACK */) settings_send(); return 0;
    }
    return DefWindowProcA(h, m, wp, lp);
}
static HWND mk_panel(int kind, int x, int y, int w, int hh, int visible)
{
    /* group boxes paint only their frame: under them the panel itself must paint, so a panel with group
       boxes does not clip its children (the drawn ones, Usage and the pie, have none and do) */
    DWORD clip = (kind == P_USAGE || kind == P_PIE) ? WS_CLIPCHILDREN : 0;
    HWND p = CreateWindowExA(0, "B3Panel", "", WS_CHILD | clip | WS_CLIPSIBLINGS | (visible ? WS_VISIBLE : 0),
                             x, y, w, hh, np, NULL, GetModuleHandleA(NULL), NULL);
    SetWindowLongA(p, GWL_USERDATA, kind);
    return p;
}

/* ---- Plan: the to-do list, modes, and what may run without asking ---------------------- */
static void plan_set(const char *lines)
{
    const char *s = lines;
    int i = 0;
    SendMessageA(lv_plan, LVM_DELETEALLITEMS, 0, 0);
    /* and the same list into the transcript, the way Claude Code shows it (the spinner line goes first,
       or taking it away later would take the list with it) */
    spin_off();
    t_block();
    t_putw(L"\x2022 Update plan");
    t_putw(L"\r\n");
    while (*s) {
        char st[16] = "", text[256], line[300];
        const char *e = strchr(s, '\n'), *tb = strchr(s, '\t');
        int n = e ? (int)(e - s) : (int)strlen(s);
        if (tb && tb < s + n) {
            lstrcpynA(st, s, (int)(tb - s) + 1 > 16 ? 16 : (int)(tb - s) + 1);
            lstrcpynA(text, tb + 1, (int)(s + n - tb) > 255 ? 255 : (int)(s + n - tb));
        } else { lstrcpynA(text, s, n + 1 > 255 ? 255 : n + 1); }
        sprintf(line, "%s%s", !strcmp(st, "in_progress") ? "\xBB " : "", text);
        lv_add(lv_plan, i, line, !strcmp(st, "completed"));
        sprintf(line, "%s %s\n", !strcmp(st, "completed") ? "[x]" : !strcmp(st, "in_progress") ? "[>]" : "[ ]", text);
        {
            char *u = cp_to_u8(line, -1, CP_ACP);
            t_put(u, -1, L"    ");
            free(u);
        }
        i++;
        if (!e) break;
        s = e + 1;
    }
    last_block_blank = 0;
    if (busy) spin_on();
}
static int allowed_cmd(const char *cmd_u8)
{
    char first[MAX_PATH], item[MAX_PATH];
    int i, n = (int)SendMessageA(lv_allow, LVM_GETITEMCOUNT, 0, 0), k = 0;
    while (*cmd_u8 == ' ') cmd_u8++;
    while (cmd_u8[k] && cmd_u8[k] != ' ' && k < MAX_PATH - 1) { first[k] = cmd_u8[k]; k++; }
    first[k] = 0;
    for (i = 0; i < n; i++) {
        if (!lv_checked(lv_allow, i)) continue;
        lv_get(lv_allow, i, item, sizeof item);
        if (!lstrcmpiA(item, first)) return 1;
    }
    return 0;
}
static HHOOK cbt_hook;
static LRESULT CALLBACK cbt_relabel(int code, WPARAM wp, LPARAM lp)
{
    if (code == 5 /* HCBT_ACTIVATE */) {
        HWND d = (HWND)wp;
        perm_box = d;
        SetDlgItemTextA(d, IDYES, "&Allow");
        SetDlgItemTextA(d, IDNO, "Al&ways");
        SetDlgItemTextA(d, IDCANCEL, "&Deny");
    }
    return CallNextHookEx(cbt_hook, code, wp, lp);
}
/* 0 = go ahead, 1 = denied. Runs on the tool's own thread: a real MessageBox, relabelled. */
static int ask_permission(const char *name, const char *a1)
{
    int is_run = !strcmp(name, "run"), is_edit = !strcmp(name, "write_file") || !strcmp(name, "edit_file");
    int plan = g_plan;
    char text[700], *ac;
    WCHAR *w;
    int r;
    if (!is_run && !is_edit) return 0;
    if (plan && !(is_run && allowed_cmd(a1) && !strchr(a1, '>'))) return 2;
    if (is_edit && g_autoedit) return 0;
    if (is_run && (allowed_cmd(a1) || !g_askrun)) return 0;
    w = u8_to_w(a1, -1);
    ac = w_to_cp(w, CP_ACP);
    free(w);
    if (strlen(ac) > 400) ac[400] = 0;
    sprintf(text, is_run ? "Claude wants to run this command in C:\\b3\\work:\n\n    %s\n\n"
                           "Allow = this once.   Always = never ask about this command again.   Deny = don't."
                         : "Claude wants to change this file:\n\n    %s\n\n"
                           "Allow = this once.   Always = accept every edit this session.   Deny = don't.", ac);
    PostMessageA(me, WM_APP + 9, 0, 0);          /* the strip: waiting for you */
    thread_actx();
    cbt_hook = SetWindowsHookExA(5 /* WH_CBT */, cbt_relabel, NULL, GetCurrentThreadId());
    r = MessageBoxA(np, text, "BASILISK - Permission", MB_YESNOCANCEL | MB_ICONQUESTION | MB_SETFOREGROUND | MB_TOPMOST);
    UnhookWindowsHookEx(cbt_hook);
    perm_box = NULL;
    PostMessageA(me, WM_APP + 10, 0, 0);         /* back to running */
    if (r == IDNO) {
        if (is_run) {
            char first[MAX_PATH];
            int k = 0;
            const char *c = ac;
            while (*c == ' ') c++;
            while (c[k] && c[k] != ' ' && k < MAX_PATH - 1) { first[k] = c[k]; k++; }
            first[k] = 0;
            if (first[0]) PostMessageA(me, WM_APP + 11, 0, (LPARAM)_strdup(first));
        } else { g_autoedit = 1; PostMessageA(me, WM_APP + 12, 0, 0); }
    }
    free(ac);
    return r == IDCANCEL ? 1 : 0;
}

/* ---- Files: the work folder, memory, @-mentions ------------------------------------------ */
static void files_add(const char *dir, HTI parent, int depth)
{
    WIN32_FIND_DATAA fd_;
    HANDLE h;
    char pat[MAX_PATH];
    int n = 0;
    sprintf(pat, "%s\\*", dir);
    h = FindFirstFileA(pat, &fd_);
    if (h == INVALID_HANDLE_VALUE) return;
    do {
        TVINS ins;
        char full[MAX_PATH], label[MAX_PATH + 32];
        HTI it;
        if (fd_.cFileName[0] == '.') continue;
        sprintf(full, "%s\\%s", dir, fd_.cFileName);
        if (fd_.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) sprintf(label, "%s", fd_.cFileName);
        else sprintf(label, "%s   (%lu bytes)", fd_.cFileName, (unsigned long)fd_.nFileSizeLow);
        memset(&ins, 0, sizeof ins);
        ins.parent = parent; ins.after = TVI_LAST;
        ins.item.mask = TVIF_TEXT | TVIF_PARAM | TVIF_STATE;
        ins.item.text = label;
        ins.item.lp = (LPARAM)_strdup(full);
        if (!lstrcmpiA(fd_.cFileName, "CLAUDE.md")) { ins.item.st = TVIS_BOLD; ins.item.stm = TVIS_BOLD; }
        it = (HTI)SendMessageA(tv_files, TVM_INSERTITEMA, 0, (LPARAM)&ins);
        if ((fd_.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) && depth < 3) {
            files_add(full, it, depth + 1);
            SendMessageA(tv_files, TVM_EXPAND, TVE_EXPAND, (LPARAM)it);
        }
    } while (FindNextFileA(h, &fd_) && ++n < 400);
    FindClose(h);
}
static void files_refresh(void)
{
    TVINS ins;
    HTI root;
    char label[64];
    FILE *f;
    if (!tv_files) return;
    /* CLAUDE.md is always there to be written in */
    f = fopen("C:\\b3\\work\\CLAUDE.md", "rb");
    if (f) fclose(f);
    else if ((f = fopen("C:\\b3\\work\\CLAUDE.md", "wb"))) {
        fputs("# Memory for BASILISK\r\n\r\nWrite standing instructions for Claude here, then press Save memory.\r\n", f);
        fclose(f);
    }
    SendMessageA(tv_files, WM_SETREDRAW, FALSE, 0);
    SendMessageA(tv_files, TVM_DELETEITEM, 0, (LPARAM)TVI_ROOT);
    memset(&ins, 0, sizeof ins);
    ins.parent = TVI_ROOT; ins.after = TVI_LAST;
    ins.item.mask = TVIF_TEXT | TVIF_PARAM;
    strcpy(label, "C:\\b3\\work");
    ins.item.text = label;
    ins.item.lp = (LPARAM)_strdup("C:\\b3\\work");
    root = (HTI)SendMessageA(tv_files, TVM_INSERTITEMA, 0, (LPARAM)&ins);
    files_add("C:\\b3\\work", root, 0);
    SendMessageA(tv_files, TVM_EXPAND, TVE_EXPAND, (LPARAM)root);
    SendMessageA(tv_files, WM_SETREDRAW, TRUE, 0);
    InvalidateRect(tv_files, NULL, TRUE);
}
static void files_select(void)
{
    HTI it = (HTI)SendMessageA(tv_files, TVM_GETNEXTITEM, TVGN_CARET, 0);
    TVI v;
    int n = 0, is_mem;
    char *raw;
    if (!it) return;
    memset(&v, 0, sizeof v);
    v.mask = TVIF_PARAM; v.h = it;
    SendMessageA(tv_files, TVM_GETITEMA, 0, (LPARAM)&v);
    if (!v.lp) return;
    lstrcpynA(sel_path, (char *)v.lp, sizeof sel_path);
    SetWindowTextA(lb_path, sel_path);
    is_mem = strstr(sel_path, "CLAUDE.md") != NULL;
    raw = read_all(sel_path, &n);
    if (raw) {
        if (n > 60000) raw[60000] = 0;
        SetWindowTextA(ed_preview, raw);
        free(raw);
    } else SetWindowTextA(ed_preview, (GetFileAttributesA(sel_path) & FILE_ATTRIBUTE_DIRECTORY) ? "(a folder)" : "(cannot read)");
    SendMessageA(ed_preview, EM_SETREADONLY, !is_mem, 0);
    EnableWindow(bt_savemem, is_mem);
    EnableWindow(bt_mention, !(GetFileAttributesA(sel_path) & FILE_ATTRIBUTE_DIRECTORY));
}
static void memory_send(void)
{
    int n = 0;
    char *raw = read_all("C:\\b3\\work\\CLAUDE.md", &n), *u8, *r;
    if (!raw) return;
    u8 = cp_to_u8(raw, n, CP_ACP);
    r = http("POST", "/b3/memory", u8, (int)strlen(u8), NULL, 5000);
    free(r); free(u8); free(raw);
}

/* ---- Tools: every tool call, with End Process --------------------------------------------- */
static void tools_add(const char *name, const char *details)
{
    char t[64];
    WCHAR *w = u8_to_w(details, -1);
    char *a = w_to_cp(w, CP_ACP);
    free(w);
    if (strlen(a) > 200) a[200] = 0;
    tool_row = lv_add(lv_tools, (int)SendMessageA(lv_tools, LVM_GETITEMCOUNT, 0, 0), name, -1);
    lv_text(lv_tools, tool_row, 1, a);
    lv_text(lv_tools, tool_row, 2, "running");
    SYSTEMTIME s; GetLocalTime(&s);
    sprintf(t, "%02d:%02d:%02d", s.wHour, s.wMinute, s.wSecond);
    lv_text(lv_tools, tool_row, 3, t);
    SendMessageA(lv_tools, LVM_ENSUREVISIBLE, tool_row, FALSE);
    EnableWindow(bt_endproc, TRUE);
    tool_t0 = GetTickCount();
    free(a);
}
static void tools_done(int ok, int lines)
{
    char t[64];
    if (tool_row < 0) return;
    lv_text(lv_tools, tool_row, 2, ok ? "finished" : interrupted ? "ended" : "failed");
    sprintf(t, "%.1f s", (GetTickCount() - tool_t0) / 1000.0);
    lv_text(lv_tools, tool_row, 4, t);
    sprintf(t, lines == 1 ? "1 line" : "%d lines", lines);
    lv_text(lv_tools, tool_row, 5, t);
    tool_row = -1;
    EnableWindow(bt_endproc, FALSE);
}

/* ---- the busy strip: shell32's own copy animation while a tool runs ---------------------- */
static void strip_show(int on, const char *label)
{
    if (label) SetWindowTextA(strip_label, label);
    if (on == strip_on) return;
    strip_on = on;
    if (on) SendMessageA(strip_anim, ACM_PLAY, (WPARAM)-1, MAKELONG(0, 0xFFFF));
    else SendMessageA(strip_anim, ACM_STOP, 0, 0);
    SendMessageA(strip_prog, PBM_SETMARQUEE, on, 40);
    layout_main();               /* the transcript gives the strip its room */
}

/* ---- the tray: a balloon when a long turn finishes ---------------------------------------- */
typedef struct { DWORD cb; HWND hwnd; UINT id, flags, cbmsg; HICON icon; CHAR tip[128]; DWORD state, statemask;
                 CHAR info[256]; UINT timeout; CHAR infotitle[64]; DWORD infoflags; } NID;
static BOOL (WINAPI *pShellNotify)(DWORD, NID *);
static void tray_init(void)
{
    NID n;
    *(FARPROC *)&pShellNotify = GetProcAddress(LoadLibraryA("shell32.dll"), "Shell_NotifyIconA");
    if (!pShellNotify) return;
    memset(&n, 0, sizeof n);
    n.cb = sizeof n; n.hwnd = me; n.id = 1; n.flags = 2 | 4;
    n.icon = LoadIconA(NULL, (LPCSTR)IDI_INFORMATION);
    strcpy(n.tip, "BASILISK III");
    pShellNotify(0, &n);
}
static void notify_done(void)
{
    NID n;
    if (!pShellNotify || SendMessageA(ck_notify, BM_GETCHECK, 0, 0) != BST_CHECKED) return;
    if (GetTickCount() - turn_t0 < 12000) return;           /* only for turns long enough to look away */
    memset(&n, 0, sizeof n);
    n.cb = sizeof n; n.hwnd = me; n.id = 1; n.flags = 0x10;
    strcpy(n.infotitle, "BASILISK III");
    sprintf(n.info, "Claude finished (%.0f s). %ld tool runs this session.", (GetTickCount() - turn_t0) / 1000.0, st_tools);
    n.timeout = 8000; n.infoflags = 1;
    pShellNotify(1, &n);
}

/* ---- building the suite -------------------------------------------------------------------- */
static void suite_create(int W, int H)
{
    WNDCLASSA wc;
    int y0 = TABH + 4, y1 = H - BAR - STATH, tw = W - SIDE, pw = tw, ph = y1 - y0, i;
    static const char *defaults[] = {"dir", "type", "ver", "echo", "tree", "find", "findstr", "more", "sort", "set",
                                     "systeminfo", "tasklist", "vol", "C:\\tcc\\tcc.exe", "cscript"};
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = panel_proc; wc.hInstance = GetModuleHandleA(NULL); wc.lpszClassName = "B3Panel";
    wc.hCursor = LoadCursorA(NULL, (LPCSTR)IDC_ARROW);
    RegisterClassA(&wc);

    /* status bar along the very bottom */
    status_bar = CreateWindowExA(0, "msctls_statusbar32", "", WS_CHILD | CCS_NORESIZE | CCS_NOPARENTALIGN | CCS_NODIVIDER,
                                 0, H - STATH, W, STATH, np, NULL, GetModuleHandleA(NULL), NULL);
    SendMessageA(status_bar, WM_SETFONT, (WPARAM)ui_font, FALSE);
    {
        int edges[6];
        edges[0] = 130; edges[1] = 220; edges[2] = 470; edges[3] = 600; edges[4] = 700; edges[5] = -1;
        SendMessageA(status_bar, SB_SETPARTS, 6, (LPARAM)edges);
    }
    /* the context pie, in the sidebar between the meter and the clock */
    pie_wnd = mk_panel(P_PIE, tw, 34, SIDE, (y1 - PAGE_H) - 34, 0);
    /* the busy strip (Chat tab, above the prompt) */
    strip = mk_panel(P_STRIP, 0, y1 - STRIPH, tw, STRIPH, 0);
    strip_anim = mk("SysAnimate32", "", ACS_TRANSPARENT | ACS_CENTER, 6, 3, 272, 60, strip, 0);
    SendMessageA(strip_anim, ACM_OPENA, (WPARAM)LoadLibraryA("shell32.dll"), (LPARAM)161);   /* "copying files" */
    strip_label = mk("Static", "", SS_LEFT | SS_NOPREFIX | SS_ENDELLIPSIS, 292, 10, tw - 400, 16, strip, 0);
    SendMessageA(strip_label, WM_SETFONT, (WPARAM)ui_bold, FALSE);
    strip_prog = mk("msctls_progress32", "", PBS_MARQUEE, 292, 32, tw - 400, 14, strip, 0);
    mk("Static", "Esc stops it", SS_RIGHT, tw - 100, 32, 90, 16, strip, 0);

    /* Plan */
    panel[T_PLAN] = mk_panel(P_PLAN, 0, y0, pw, ph, 0);
    mk("Button", "Plan  (Claude's to-do list, updated as it works)", BS_GROUPBOX, 10, 6, pw - 20, ph * 52 / 100, panel[T_PLAN], 0);
    lv_plan = mkx(WS_EX_CLIENTEDGE, "SysListView32", "", LVS_REPORT | LVS_NOCOLUMNHEADER | LVS_SHOWSELALWAYS | LVS_SINGLESEL,
                  22, 28, pw - 44, ph * 52 / 100 - 34, panel[T_PLAN], 0);
    SendMessageA(lv_plan, LVM_SETEXTENDEDLISTVIEWSTYLE, 0, LVS_EX_CHECKBOXES | LVS_EX_FULLROWSELECT);
    lv_col(lv_plan, 0, "Task", pw - 70);
    {
        int gy = ph * 52 / 100 + 14, gh = ph - gy - 8, half = (pw - 30) / 2;
        mk("Button", "Permissions", BS_GROUPBOX, 10, gy, half, gh, panel[T_PLAN], 0);
        ck_plan = mk("Button", "Plan mode: Claude looks and plans, and changes nothing", BS_AUTOCHECKBOX, 24, gy + 26, half - 30, 20, panel[T_PLAN], 201);
        ck_autoedit = mk("Button", "Accept file edits without asking", BS_AUTOCHECKBOX, 24, gy + 50, half - 30, 20, panel[T_PLAN], 202);
        ck_askrun = mk("Button", "Ask before running a command", BS_AUTOCHECKBOX, 24, gy + 74, half - 30, 20, panel[T_PLAN], 203);
        SendMessageA(ck_askrun, BM_SETCHECK, BST_CHECKED, 0);
        mk("Static", "When Claude needs permission, a real Windows message box asks: Allow (once), Always, "
                     "or Deny. Reading files never asks.", SS_LEFT, 24, gy + 104, half - 30, 48, panel[T_PLAN], 0);
        mk("Button", "Always allowed commands  (ticked: runs without asking)", BS_GROUPBOX, 20 + half, gy, half, gh, panel[T_PLAN], 0);
        lv_allow = mkx(WS_EX_CLIENTEDGE, "SysListView32", "", LVS_REPORT | LVS_NOCOLUMNHEADER | LVS_SINGLESEL,
                       32 + half, gy + 22, half - 24, gh - 30, panel[T_PLAN], 0);
        SendMessageA(lv_allow, LVM_SETEXTENDEDLISTVIEWSTYLE, 0, LVS_EX_CHECKBOXES | LVS_EX_FULLROWSELECT);
        lv_col(lv_allow, 0, "Command", half - 50);
        for (i = 0; i < (int)(sizeof defaults / sizeof defaults[0]); i++) lv_add(lv_allow, i, defaults[i], 1);
    }

    /* Files */
    panel[T_FILES] = mk_panel(P_FILES, 0, y0, pw, ph, 0);
    tv_files = mkx(WS_EX_CLIENTEDGE, "SysTreeView32", "", TVS_HASBUTTONS | TVS_HASLINES | TVS_LINESATROOT | TVS_SHOWSELALWAYS,
                   10, 10, 270, ph - 20, panel[T_FILES], 0);
    lb_path = mk("Static", "Choose a file. CLAUDE.md is BASILISK's memory: what you write there, Claude reads.",
                 SS_LEFT | SS_NOPREFIX | SS_PATHELLIPSIS, 292, 12, pw - 302, 16, panel[T_FILES], 0);
    ed_preview = mkx(WS_EX_CLIENTEDGE, "Edit", "", ES_MULTILINE | ES_AUTOVSCROLL | ES_AUTOHSCROLL | WS_VSCROLL | WS_HSCROLL | ES_READONLY,
                     292, 34, pw - 302, ph - 82, panel[T_FILES], 0);
    SendMessageA(ed_preview, WM_SETFONT, (WPARAM)mono_font, FALSE);
    bt_mention = mk("Button", "@ Mention in prompt", BS_PUSHBUTTON, 292, ph - 38, 140, 26, panel[T_FILES], 301);
    bt_refresh = mk("Button", "Refresh", BS_PUSHBUTTON, 440, ph - 38, 80, 26, panel[T_FILES], 302);
    bt_savemem = mk("Button", "Save memory", BS_PUSHBUTTON, 528, ph - 38, 100, 26, panel[T_FILES], 303);
    EnableWindow(bt_savemem, FALSE);

    /* Usage */
    panel[T_USAGE] = mk_panel(P_USAGE, 0, y0, pw, ph, 0);
    {
        HMODULE ux = LoadLibraryA("uxtheme.dll");
        if (ux) {
            *(FARPROC *)&pOpenTheme = GetProcAddress(ux, "OpenThemeData");
            *(FARPROC *)&pDrawThemeBg = GetProcAddress(ux, "DrawThemeBackground");
            if (pOpenTheme) th_button = pOpenTheme(panel[T_USAGE], L"Button");
        }
    }
    bt_analyze = mk("Button", "Analyze", BS_PUSHBUTTON, 12, 476, 90, 26, panel[T_USAGE], 401);
    bt_defrag = mk("Button", "Defragment", BS_PUSHBUTTON, 110, 476, 90, 26, panel[T_USAGE], 402);

    /* Tools */
    panel[T_TOOLS] = mk_panel(P_TOOLS, 0, y0, pw, ph, 0);
    lv_tools = mkx(WS_EX_CLIENTEDGE, "SysListView32", "", LVS_REPORT | LVS_SHOWSELALWAYS | LVS_SINGLESEL,
                   10, 10, pw - 20, ph - 56, panel[T_TOOLS], 0);
    SendMessageA(lv_tools, LVM_SETEXTENDEDLISTVIEWSTYLE, 0, LVS_EX_FULLROWSELECT | LVS_EX_GRIDLINES);
    lv_col(lv_tools, 0, "Tool", 80); lv_col(lv_tools, 1, "What", pw - 20 - 80 - 80 - 70 - 60 - 70 - 24);
    lv_col(lv_tools, 2, "Status", 80); lv_col(lv_tools, 3, "Started", 70); lv_col(lv_tools, 4, "Took", 60);
    lv_col(lv_tools, 5, "Output", 70);
    bt_endproc = mk("Button", "End Process", BS_PUSHBUTTON, pw - 110, ph - 38, 100, 26, panel[T_TOOLS], 501);
    EnableWindow(bt_endproc, FALSE);
    mk("Static", "Every tool Claude runs, in order. End Process stops the one running now (like Esc).",
       SS_LEFT, 12, ph - 34, pw - 140, 18, panel[T_TOOLS], 0);

    /* Settings */
    panel[T_SETTINGS] = mk_panel(P_SETTINGS, 0, y0, pw, ph, 0);
    mk("Button", "Model", BS_GROUPBOX, 10, 8, 360, 70, panel[T_SETTINGS], 0);
    cb_model = mk("ComboBox", "", CBS_DROPDOWNLIST | WS_VSCROLL, 24, 34, 330, 120, panel[T_SETTINGS], 601);
    SendMessageA(cb_model, CB_ADDSTRING, 0, (LPARAM)"Claude Haiku 5.5  (fastest, the default)");
    SendMessageA(cb_model, CB_ADDSTRING, 0, (LPARAM)"Claude Sonnet 5.5  (deeper, slower, dearer)");
    SendMessageA(cb_model, CB_SETCURSEL, 0, 0);
    mk("Button", "Effort  (how hard Claude thinks before it answers)", BS_GROUPBOX, 10, 88, 360, 108, panel[T_SETTINGS], 0);
    tb_effort = mk("msctls_trackbar32", "", TBS_AUTOTICKS, 24, 114, 330, 30, panel[T_SETTINGS], 602);
    SendMessageA(tb_effort, TBM_SETRANGE, TRUE, MAKELONG(0, 4));
    SendMessageA(tb_effort, TBM_SETPOS, TRUE, 0);
    mk("Static", "Low", SS_LEFT, 26, 148, 50, 16, panel[T_SETTINGS], 0);
    mk("Static", "Medium", SS_CENTER, 86, 148, 60, 16, panel[T_SETTINGS], 0);
    mk("Static", "High", SS_CENTER, 162, 148, 50, 16, panel[T_SETTINGS], 0);
    mk("Static", "X-high", SS_CENTER, 228, 148, 50, 16, panel[T_SETTINGS], 0);
    mk("Static", "Max", SS_RIGHT, 300, 148, 50, 16, panel[T_SETTINGS], 0);
    mk("Button", "Notifications", BS_GROUPBOX, 10, 206, 360, 58, panel[T_SETTINGS], 0);
    ck_notify = mk("Button", "A balloon in the tray when a long turn finishes", BS_AUTOCHECKBOX, 24, 230, 330, 20, panel[T_SETTINGS], 603);
    SendMessageA(ck_notify, BM_SETCHECK, BST_CHECKED, 0);
    mk("Button", "Conversation", BS_GROUPBOX, 386, 8, pw - 396, 160, panel[T_SETTINGS], 0);
    bt_clear = mk("Button", "Clear conversation", BS_PUSHBUTTON, 402, 34, 170, 26, panel[T_SETTINGS], 604);
    bt_compact = mk("Button", "Compact now (Defragment)", BS_PUSHBUTTON, 402, 68, 170, 26, panel[T_SETTINGS], 605);
    bt_memory = mk("Button", "Edit memory (CLAUDE.md)...", BS_PUSHBUTTON, 402, 102, 170, 26, panel[T_SETTINGS], 606);
    mk("Static", "Slash commands do the same: /clear, /compact, /model, /effort, /plan, /cost, /help.",
       SS_LEFT, 586, 36, pw - 610, 60, panel[T_SETTINGS], 0);
    {   /* where every part comes from, said plainly */
        static const char *rows[][3] = {
            {"Transcript", "borrowed", "Notepad's own edit control (Lucida Console, word wrap)"},
            {"Prompt bar, Send, Stop", "borrowed", "Notepad's Find dialog: Find what, Find Next, Cancel, relabelled"},
            {"Tabs", "borrowed", "Date and Time Properties' tab control, renamed tab by tab"},
            {"Clock and calendar", "borrowed", "Date and Time Properties' Date & Time page"},
            {"Cost meter", "borrowed", "Calculator's display"},
            {"Permission prompts", "borrowed", "MessageBox, its Yes/No/Cancel renamed Allow/Always/Deny"},
            {"Busy strip animation", "borrowed", "shell32's copying-files animation (the one Explorer plays)"},
            {"Tray balloon", "borrowed", "the notification area (Shell_NotifyIcon)"},
            {"Plan, Tools, Files lists", "created", "XP's list view and tree view controls, made here"},
            {"Status bar, trackbar, check boxes", "created", "XP's common controls, themed (comctl32 v6)"},
            {"Meters, graphs, pie, context map", "drawn", "drawn here in the manner of Task Manager, a drive's Properties, Defrag"},
        };
        HWND lv;
        int k, gy = 330;
        mk("Button", "Where each part comes from", BS_GROUPBOX, 10, gy, pw - 20, ph - gy - 8, panel[T_SETTINGS], 0);
        lv = mkx(WS_EX_CLIENTEDGE, "SysListView32", "", LVS_REPORT | LVS_SINGLESEL | LVS_NOSORTHEADER,
                 22, gy + 22, pw - 44, ph - gy - 40, panel[T_SETTINGS], 0);
        SendMessageA(lv, LVM_SETEXTENDEDLISTVIEWSTYLE, 0, LVS_EX_FULLROWSELECT | LVS_EX_GRIDLINES);
        lv_col(lv, 0, "Part", 200); lv_col(lv, 1, "", 70); lv_col(lv, 2, "From", pw - 44 - 200 - 70 - 24);
        for (k = 0; k < (int)(sizeof rows / sizeof rows[0]); k++) {
            int i = lv_add(lv, k, rows[k][0], -1);
            lv_text(lv, i, 1, rows[k][1]);
            lv_text(lv, i, 2, rows[k][2]);
        }
    }
    {   /* the pane over the tabs */
        WNDCLASSA oc;
        memset(&oc, 0, sizeof oc);
        oc.lpfnWndProc = tab_ov_proc; oc.hInstance = GetModuleHandleA(NULL); oc.lpszClassName = "B3TabPane";
        oc.hCursor = LoadCursorA(NULL, (LPCSTR)IDC_ARROW);
        RegisterClassA(&oc);
        if (tabs) {
            tab_ov = CreateWindowExA(WS_EX_TRANSPARENT, "B3TabPane", "", WS_CHILD | WS_VISIBLE, 2, 2, tw - 4, TABH, np, NULL,
                                     GetModuleHandleA(NULL), NULL);
            SetWindowPos(tab_ov, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
            tab_rects();
        }
    }
    tray_init();
    suite_ready = 1;
    suite_status();
}

/* ---- tabs ------------------------------------------------------------------------------------- */
static void suite_show_tab(int t)
{
    int i, old = cur_tab;
    if (t < 0 || t >= NTABS || !suite_ready) return;
    cur_tab = t;
    if (tabs && (int)SendMessageA(tabs, TCM_GETCURSEL, 0, 0) != t) SendMessageA(tabs, TCM_SETCURSEL, t, 0);
    if (t == old) return;
    /* the new page goes up over the old one first, then the old one hides underneath: no frame of bare background */
    if (t == T_CHAT) {
        layout_main();
        SetWindowPos(np_edit, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE);
        if (chat_bottom) SendMessageW(np_edit, WM_VSCROLL, SB_BOTTOM, 0);   /* what arrived meanwhile, in view */
        if (strip && strip_on) SetWindowPos(strip, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE);
    } else {
        if (t == T_FILES) files_refresh();
        SetWindowPos(panel[t], HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOACTIVATE);
        UpdateWindow(panel[t]);
    }
    if (old == T_CHAT) {
        chat_bottom = t_at_bottom();
        ShowWindow(np_edit, SW_HIDE);
        if (strip) ShowWindow(strip, SW_HIDE);
    }
    for (i = 1; i < NTABS; i++) if (panel[i] && i != t) ShowWindow(panel[i], SW_HIDE);
}

/* ---- the borrowed tabs ----------------------------------------------------------------------
   Date and Time's tab control still reports its clicks to Date and Time's (hidden) property sheet,
   which would answer by swapping in its own pages. So an invisible pane of ours lies over it and takes
   the clicks; the tabs only ever change by TCM_SETCURSEL, which tells nobody. */
static void tab_rects(void)
{
    DWORD pid;
    HANDLE ph;
    RECT *rr;
    SIZE_T done;
    int i, n;
    if (!tabs) return;
    n = (int)SendMessageA(tabs, TCM_GETITEMCOUNT, 0, 0);
    GetWindowThreadProcessId(tabs, &pid);
    ph = OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE, FALSE, pid);
    if (!ph) return;
    rr = (RECT *)VirtualAllocEx(ph, NULL, sizeof(RECT), MEM_COMMIT, PAGE_READWRITE);
    if (rr) {
        for (i = 0; i < n && i < NTABS; i++) {
            SendMessageA(tabs, TCM_GETITEMRECT, i, (LPARAM)rr);
            ReadProcessMemory(ph, rr, &tab_rc[i], sizeof(RECT), &done);
        }
        VirtualFreeEx(ph, rr, 0, MEM_RELEASE);
    }
    CloseHandle(ph);
}
static LRESULT CALLBACK tab_ov_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    switch (m) {
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: { PAINTSTRUCT ps; BeginPaint(h, &ps); EndPaint(h, &ps); return 0; }
    case WM_MOUSEACTIVATE: return MA_NOACTIVATE;
    case WM_LBUTTONDOWN: {
        POINT p;
        int i;
        p.x = (short)LOWORD(lp); p.y = (short)HIWORD(lp);
        if (!tab_rc[1].right) tab_rects();
        for (i = 0; i < NTABS; i++) if (PtInRect(&tab_rc[i], p)) { suite_show_tab(i); break; }
        return 0;
    }
    }
    return DefWindowProcA(h, m, wp, lp);
}
static void layout_main(void)
{
    RECT rc;
    int W, H, y0, y1, tw, strip_vis, bottom;
    if (!np || !np_edit) return;
    GetClientRect(np, &rc);
    W = rc.right; H = rc.bottom;
    y0 = tabs ? TABH + 4 : 0;
    y1 = H - BAR - (status_bar ? STATH : 0);
    tw = clk_page ? W - SIDE : W;
    strip_vis = strip && strip_on && cur_tab == T_CHAT;
    bottom = t_at_bottom();
    SetWindowPos(np_edit, NULL, 0, y0, tw, y1 - y0 - (strip_vis ? STRIPH : 0), SWP_NOZORDER | SWP_NOACTIVATE);
    if (bottom) SendMessageW(np_edit, EM_SCROLLCARET, 0, 0);
    if (strip) {
        if (strip_vis) SetWindowPos(strip, HWND_TOP, 0, y1 - STRIPH, tw, STRIPH, SWP_SHOWWINDOW | SWP_NOACTIVATE);
        else ShowWindow(strip, SW_HIDE);
    }
}

static void suite_command(int id, int code, HWND c)
{
    (void)c;
    switch (id) {
    case 201: if (code == BN_CLICKED) { g_plan = SendMessageA(ck_plan, BM_GETCHECK, 0, 0) == BST_CHECKED; settings_send(); } break;
    case 202: if (code == BN_CLICKED) g_autoedit = SendMessageA(ck_autoedit, BM_GETCHECK, 0, 0) == BST_CHECKED; break;
    case 203: if (code == BN_CLICKED) g_askrun = SendMessageA(ck_askrun, BM_GETCHECK, 0, 0) == BST_CHECKED; break;
    case 301: {                                   /* @ Mention */
        char m[MAX_PATH + 4];
        WCHAR *w;
        const char *rel = sel_path;
        if (!_strnicmp(rel, "C:\\b3\\work\\", 11)) rel += 11;
        sprintf(m, "@%s ", rel);
        w = u8_to_w(m, -1);
        SendMessageW(fd_edit, EM_SETSEL, 32767, 32767);
        SendMessageW(fd_edit, EM_REPLACESEL, TRUE, (LPARAM)w);
        free(w);
        focus_input();
        break;
    }
    case 302: files_refresh(); break;
    case 303: {                                   /* Save memory */
        int n = GetWindowTextLengthA(ed_preview);
        char *b = (char *)malloc(n + 1);
        FILE *f;
        GetWindowTextA(ed_preview, b, n + 1);
        if ((f = fopen("C:\\b3\\work\\CLAUDE.md", "wb"))) { fwrite(b, 1, n, f); fclose(f); }
        free(b);
        memory_send();
        SetWindowTextA(lb_path, "C:\\b3\\work\\CLAUDE.md  (saved: Claude reads it with your next message)");
        break;
    }
    case 401: InvalidateRect(panel[T_USAGE], NULL, FALSE); break;
    case 402: case 605: { char *r = http("POST", "/b3/send", "/compact", 8, NULL, 5000); free(r); break; }
    case 501: PostMessageA(me, WM_KEYCMD, 2, 0); break;   /* End Process = Esc */
    case 601: if (code == CBN_SELCHANGE) settings_send(); break;
    case 604: { char *r = http("POST", "/b3/send", "/clear", 6, NULL, 5000); free(r); break; }
    case 606:
        SendMessageA(tabs, TCM_SETCURSEL, T_FILES, 0);
        suite_show_tab(T_FILES);
        {
            HTI it = (HTI)SendMessageA(tv_files, TVM_GETNEXTITEM, 0 /* TVGN_ROOT */, 0);
            it = it ? (HTI)SendMessageA(tv_files, TVM_GETNEXTITEM, 4 /* TVGN_CHILD */, (LPARAM)it) : NULL;
            while (it) {
                TVI v;
                memset(&v, 0, sizeof v); v.mask = TVIF_PARAM; v.h = it;
                SendMessageA(tv_files, TVM_GETITEMA, 0, (LPARAM)&v);
                if (v.lp && strstr((char *)v.lp, "CLAUDE.md")) { SendMessageA(tv_files, TVM_SELECTITEM, TVGN_CARET, (LPARAM)it); break; }
                it = (HTI)SendMessageA(tv_files, TVM_GETNEXTITEM, 1 /* TVGN_NEXT */, (LPARAM)it);
            }
        }
        break;
    }
}
static void suite_notify(NMH *n)
{
    if (!n) return;
    if (n->from == tv_files && (n->code == (UINT)TVN_SELCHANGEDA || n->code == (UINT)(-451) /* TVN_SELCHANGEDW */)) files_select();
    else if (n->from == tv_files && n->code == (UINT)NM_DBLCLK) suite_command(301, 0, NULL);
}

static void bring_front(HWND w)        /* the permission box: XP lets only the foreground thread hand over */
{
    DWORD my = GetCurrentThreadId(), ft = 0;
    HWND fg = GetForegroundWindow();
    if (fg) ft = GetWindowThreadProcessId(fg, NULL);
    if (ft && ft != my) AttachThreadInput(my, ft, TRUE);
    SetForegroundWindow(w);
    if (ft && ft != my) AttachThreadInput(my, ft, FALSE);
}

static LRESULT CALLBACK me_proc(HWND h, UINT m, WPARAM wp, LPARAM lp)
{
    static int ticks;
    switch (m) {
    case WM_EV: handle_ev((Ev *)lp); return 0;
    case WM_TOOLRES: show_tool_result((char **)lp); return 0;
    case WM_KEYCMD: keycmd((int)wp); return 0;
    case WM_APP + 9:
        set_state("waiting for your permission");
        if (strip_label) SetWindowTextA(strip_label, "Waiting for your permission...");
        return 0;
    case WM_APP + 10:
        set_state("running a tool");
        if (strip_label) SetWindowTextA(strip_label, strip_text);
        return 0;
    case WM_APP + 11: lv_add(lv_allow, -1, (char *)lp, 1); free((void *)lp); return 0;
    case WM_APP + 12: SendMessageA(ck_autoedit, BM_SETCHECK, BST_CHECKED, 0); return 0;
    case WM_TIMER:
        if (wp == 1) {
            if (perm_box && IsWindow(perm_box) && GetForegroundWindow() != perm_box) bring_front(perm_box);
            if (tool_row >= 0 && !strip_on && GetTickCount() - tool_t0 > 700) strip_show(1, NULL);
            if (suite_ready && ++ticks % 4 == 0 && (busy || rate_acc || (n_rate && rate_hist[n_rate - 1]))) {
                if (n_rate == 64) { memmove(rate_hist, rate_hist + 1, 63 * sizeof rate_hist[0]); n_rate--; }
                rate_hist[n_rate++] = rate_acc / 4;          /* about four characters to a token */
                rate_acc = 0;
                if (cur_tab == T_USAGE) InvalidateRect(panel[T_USAGE], NULL, FALSE);
            }
            if (!IsWindow(np)) { PostQuitMessage(0); return 0; }
            /* BASILISK lives maximized: if someone restores it while it is in front, put it back
               (a smaller window would leave the tab strip and sidebar out of place) */
            if (GetForegroundWindow() == np && !IsZoomed(np) && !IsIconic(np)) ShowWindow(np, SW_SHOWMAXIMIZED);
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
            /* (no focus keeping here: the visitor's pointer may be selecting text in the transcript;
               the keyboard hook brings the prompt back when they type) */
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
    suite_init();
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = me_proc; wc.hInstance = hi; wc.lpszClassName = "BasiliskIII";
    RegisterClassA(&wc);
    me = CreateWindowA("BasiliskIII", "BASILISK III", 0, 0, 0, 0, 0, NULL, NULL, hi, NULL);
    if (!assemble()) { MessageBoxA(NULL, "BASILISK could not find its parts.", "BASILISK", MB_ICONERROR); return 1; }

    t_putw(L"\x2022 BASILISK III Suite  \x00B7  a Claude Code client assembled from Windows XP\r\n");
    t_putw(L"  Notepad keeps the transcript, its Find box takes your words, Date and Time lends its\r\n");
    t_putw(L"  tabs, clock and calendar, Calculator keeps the bill. Tools run here, in C:\\b3\\work.\r\n\r\n");
    t_putw(L"  Enter send \x00B7 Esc interrupt \x00B7 Ctrl+Tab tabs \x00B7 PgUp/PgDn scroll \x00B7 Up/Down history \x00B7 /help\r\n");
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
    logf_("t %lu ready", GetTickCount());
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
