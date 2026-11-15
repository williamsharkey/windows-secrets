/* PROBE.EXE - the multitimbral experiment's limit probe (design/MULTITIMBRAL-EXPERIMENT.md).
   Started by Windows instead of SYNTH.EXE; driven by host lines through the BSYN card's mailbox:
     launch <n> <show> [<file>]   start n more Sound Recorders (show: 0 SW_HIDE, 7 SW_SHOWMINNOACTIVE, 4 SW_SHOWNOACTIVATE)
     census                       walk the GDI and USER heaps (ToolHelp): free bytes and objects by type
     conv | sel | mem             free conventional memory (GlobalDosAlloc), free LDT selectors, MemManInfo
     strip <mask>                 on every recorder: 1 destroy its child controls but the wave display, 2 its menu,
                                  4 the wave display too
     play <i> | stop <i>          press Play / Stop on recorder i
     closeall                     close every recorder
   Replies are text lines (bs_line). */
#include <windows.h>
#include <mmsystem.h>
#include <toolhelp.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include "../../guest/bslink.h"

#define MAXR 640
static HWND rw[MAXR]; static HINSTANCE rh[MAXR]; static int nr;
static void say(const char *fmt, ...) { static char b[300]; va_list a; va_start(a, fmt); vsprintf(b, fmt, a); va_end(a); bs_line(b); }
static void pump(void) { MSG m; while (PeekMessage(&m, 0, 0, 0, PM_REMOVE)) { TranslateMessage(&m); DispatchMessage(&m); } }
static HWND window_of(HINSTANCE hi)
{
    HWND x;
    for (x = GetWindow(GetDesktopWindow(), GW_CHILD); x; x = GetWindow(x, GW_HWNDNEXT))
        if (GetWindowWord(x, GWW_HINSTANCE) == (WORD)hi && !GetParent(x)) return x;
    return NULL;
}
static void heap_walk(HGLOBAL seg, const char *name)
{
    LOCALENTRY e; long freeb = 0, used = 0; int cnt[33], n = 0, k; char b[260]; int at;
    memset(cnt, 0, sizeof cnt);
    e.dwSize = sizeof e;
    if (LocalFirst(&e, seg)) do {
        if (e.wFlags & LF_FREE) freeb += e.wSize; else { used += e.wSize; cnt[e.wType < 33 ? e.wType : 32]++; }
        n++;
    } while (LocalNext(&e));
    at = sprintf(b, "%s free %ld used %ld blocks %d types", name, freeb, used, n);
    for (k = 0; k < 33; k++) if (cnt[k]) at += sprintf(b + at, " %d:%d", k, cnt[k]);
    bs_line(b);
}
static void census(void)
{
    SYSHEAPINFO h; h.dwSize = sizeof h;
    if (!SystemHeapInfo(&h)) { say("census none"); return; }
    say("census n %d user %d%% gdi %d%% tasks %d", nr, h.wUserFreePercent, h.wGDIFreePercent, GetNumTasks());
    heap_walk(h.hGDISegment, "gdi");
    heap_walk(h.hUserSegment, "user");
}
static void conv(void)
{
    static DWORD hd[700]; int n = 0, i;
    while (n < 700) { DWORD d = GlobalDosAlloc(1024); if (!d) break; hd[n++] = d; }
    for (i = 0; i < n; i++) GlobalDosFree(LOWORD(hd[i]));
    say("conv %d KB", n);
}
static void sel(void)
{
    static UINT s[8200]; int n = 0, i;
    while (n < 8200) { UINT x = AllocSelector(0); if (!x) break; s[n++] = x; }
    for (i = 0; i < n; i++) FreeSelector(s[i]);
    say("sel %d free", n);
}
static void mem(void)
{
    MEMMANINFO m; m.dwSize = sizeof m;
    MemManInfo(&m);
    say("mem largest %ld KB freepages %ld totalpages %ld freelinear %ld swap %ld freespace %ld KB", m.dwLargestFreeBlock / 1024,
        m.dwFreePages, m.dwTotalPages, m.dwFreeLinearSpace, m.dwSwapFilePages, GetFreeSpace(0) / 1024);
}
static void low(void)   /* the global heap below 1 MB: used bytes by block type, and the biggest owners */
{
    GLOBALENTRY g; long by[16], fr = 0, all = 0; int k, nb = 0; char b[300]; int at;
    static WORD own[64]; static long ob[64]; int no = 0;
    memset(by, 0, sizeof by);
    g.dwSize = sizeof g;
    if (GlobalFirst(&g, GLOBAL_ALL)) do {
        if (g.dwAddress >= 0x100000L) continue;
        if (g.wType == GT_FREE) { fr += g.dwBlockSize; continue; }
        all += g.dwBlockSize; by[g.wType < 16 ? g.wType : 15] += g.dwBlockSize; nb++;
        for (k = 0; k < no && own[k] != (WORD)g.hOwner; k++) {}
        if (k == no && no < 64) { own[no] = (WORD)g.hOwner; ob[no] = 0; no++; }
        if (k < 64) ob[k] += g.dwBlockSize;
    } while (GlobalNext(&g, GLOBAL_ALL));
    at = sprintf(b, "low used %ld free %ld blocks %d bytype", all, fr, nb);
    for (k = 0; k < 16; k++) if (by[k]) at += sprintf(b + at, " %d:%ld", k, by[k]);
    bs_line(b);
    at = sprintf(b, "lowowners");
    for (k = 0; k < no && at < 260; k++) {
        MODULEENTRY me; TASKENTRY te; char nm[12] = "?";
        me.dwSize = sizeof me; te.dwSize = sizeof te;
        if (ModuleFindHandle(&me, (HMODULE)own[k])) lstrcpyn(nm, me.szModule, 9);
        else if (TaskFindHandle(&te, (HTASK)own[k])) { lstrcpyn(nm, te.szModule, 7); lstrcat(nm, "/t"); }
        if (ob[k] >= 2048) at += sprintf(b + at, " %s:%ld", nm, ob[k]);
    }
    bs_line(b);
}
static UINT msgStrip; static void (FAR PASCAL *MtVeto)(WORD); static int (FAR PASCAL *MtCount)(int);
static int autostrip;   /* strip mask applied to each new recorder as it starts (8: delete the brushes and bitmaps it made) */
static HANDLE gh[3000]; static int ngh;
static void gdi_handles(HANDLE *out, int *n, int max)
{
    SYSHEAPINFO h; LOCALENTRY e; h.dwSize = sizeof h; *n = 0;
    if (!SystemHeapInfo(&h)) return;
    e.dwSize = sizeof e;
    if (LocalFirst(&e, h.hGDISegment)) do { if (!(e.wFlags & LF_FREE) && *n < max) out[(*n)++] = (HANDLE)((WORD)e.hHandle | (e.wType << 0) * 0); } while (LocalNext(&e));
}
static int deleted, kept;
static void strip_one(int i, int mask);
static void gdi_delete_new(void)
{
    SYSHEAPINFO h; LOCALENTRY e; int k; h.dwSize = sizeof h;
    if (!SystemHeapInfo(&h)) return;
    e.dwSize = sizeof e;
    if (LocalFirst(&e, h.hGDISegment)) do {
        if (e.wFlags & LF_FREE) continue;
        if (e.wType != LT_GDI_BRUSH && e.wType != LT_GDI_BITMAP && e.wType != LT_GDI_FONT && e.wType != LT_GDI_PEN) continue;
        for (k = 0; k < ngh && gh[k] != e.hHandle; k++) {}
        if (k < ngh) continue;
        if (DeleteObject((HGDIOBJ)e.hHandle)) deleted++; else kept++;
    } while (LocalNext(&e));
}
static void launch(int n, int show, const char *file)
{
    char cmd[128]; int i; DWORD t0 = timeGetTime();
    wsprintf(cmd, "SOUNDREC.EXE %s", (LPSTR)file);
    for (i = 0; i < n && nr < MAXR; i++) {
        DWORD t = timeGetTime(), tw;
        HINSTANCE h;
        if (autostrip & (autostrip & 0x8000 ? 0x4000 : 8)) gdi_handles(gh, &ngh, 3000);
        h = WinExec(cmd, show);
        if ((UINT)h < 32) { say("fail %d code %u user %d%% gdi %d%% tasks %d", nr, (UINT)h, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES), GetNumTasks()); return; }
        rh[nr] = h; rw[nr] = NULL; tw = timeGetTime();
        while (!rw[nr] && timeGetTime() - tw < 8000) { pump(); rw[nr] = window_of(h); }
        if (!rw[nr]) { say("fail %d nowindow user %d%% gdi %d%%", nr, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES)); nr++; return; }
        nr++;
        if (autostrip) { pump(); strip_one(nr - 1, autostrip); if (autostrip & (autostrip & 0x8000 ? 0x4000 : 8)) gdi_delete_new(); }
        say("pr %d user %d gdi %d free %ld ms %ld", nr, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES), GetFreeSpace(0) / 1024, (long)(timeGetTime() - t));
    }
    say("launched %d in %ld ms", nr, (long)(timeGetTime() - t0));
}
static void strip_one(int i, int mask)
{
    if (!rw[i] || !IsWindow(rw[i]) || !msgStrip) return;
    PostMessage(rw[i], msgStrip, (WPARAM)mask, 0L);
}
static void strip(int mask)
{
    int i;
    for (i = 0; i < nr; i++) strip_one(i, mask);
    { DWORD t = timeGetTime(); while (timeGetTime() - t < 200) pump(); }
    say("strip %d done user %d gdi %d", mask, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES));
}
static void host_line(char *s)
{
    char *a = strchr(s, ' '), *rest = a ? a + 1 : "";
    if (a) *a = 0;
    if (!strcmp(s, "launch")) { int n = atoi(rest), sh = 0; char f[80] = "C:\\WINDOWS\\DING.WAV"; char *p = strchr(rest, ' ');
        if (p) { sh = atoi(p + 1); p = strchr(p + 1, ' '); if (p) lstrcpyn(f, p + 1, sizeof f); } launch(n, sh, f); }
    else if (!strcmp(s, "census")) census();
    else if (!strcmp(s, "conv")) conv();
    else if (!strcmp(s, "low")) low();
    else if (!strcmp(s, "sel")) sel();
    else if (!strcmp(s, "mem")) mem();
    else if (!strcmp(s, "strip")) strip(atoi(rest));
    else if (!strcmp(s, "play")) { int i = atoi(rest); if (i >= 0 && i < nr) SendMessage(rw[i], WM_COMMAND, 206, MAKELPARAM(GetDlgItem(rw[i], 206), BN_CLICKED)); say("played %d", i); }
    else if (!strcmp(s, "stop")) { int i = atoi(rest); if (i >= 0 && i < nr) SendMessage(rw[i], WM_COMMAND, 207, MAKELPARAM(GetDlgItem(rw[i], 207), BN_CLICKED)); say("stopped %d", i); }
    else if (!strcmp(s, "status")) { int i = atoi(rest); char t[40] = ""; if (i >= 0 && i < nr) GetDlgItemText(rw[i], 200, t, sizeof t); say("status %d %s", i, (LPSTR)t); }
    else if (!strcmp(s, "closeall")) { int i; for (i = 0; i < nr; i++) if (rw[i] && IsWindow(rw[i])) PostMessage(rw[i], WM_CLOSE, 0, 0L); nr = 0; say("closed"); }
    else if (!strcmp(s, "autostrip")) { autostrip = atoi(rest); say("pong autostrip %d", autostrip); }
    else if (!strcmp(s, "deleted")) say("pong deleted %d kept %d destroyed %d vetoed %d", deleted, kept, MtCount ? MtCount(0) : -1, MtCount ? MtCount(1) : -1);
    else if (!strcmp(s, "veto")) { if (MtVeto) MtVeto((WORD)atoi(rest)); say("pong veto %d", atoi(rest)); }
    else if (!strcmp(s, "voices")) { DWORD v = bs_voices(); say("pong voices %08lx", v); }
    else if (!strcmp(s, "dump")) { int i = atoi(rest); HWND c; char cl[32], t[32]; int n = 0;
        if (i < 0 || i >= nr) return;
        GetClassName(rw[i], cl, sizeof cl); GetWindowText(rw[i], t, sizeof t);
        say("pong-w %04x %s '%s' menu %04x vis %d", (WORD)rw[i], (LPSTR)cl, (LPSTR)t, (WORD)GetMenu(rw[i]), IsWindowVisible(rw[i]));
        for (c = GetWindow(rw[i], GW_CHILD); c; c = GetWindow(c, GW_HWNDNEXT)) { GetClassName(c, cl, sizeof cl); say("pong-c %d %s", GetDlgCtrlID(c), (LPSTR)cl); n++; }
        say("pong children %d", n); }
    else if (!strcmp(s, "ping")) say("pong %d", nr);
}
int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show)
{
    static WORD e[140]; static char acc[1200]; int accn = 0;
    if (!bs_present()) return 1;
    {   HINSTANCE hk = LoadLibrary("C:\\MT\\MTHOOK.DLL");
        if ((UINT)hk >= 32) { UINT (FAR PASCAL *inst)(void) = (UINT (FAR PASCAL *)(void))GetProcAddress(hk, "MTINSTALL");
            MtVeto = (void (FAR PASCAL *)(WORD))GetProcAddress(hk, "MTVETO"); MtCount = (int (FAR PASCAL *)(int))GetProcAddress(hk, "MTCOUNT");
            if (inst) msgStrip = inst(); }
        say("hook %u", msgStrip); }
    say("probe up: user %d%% gdi %d%% tasks %d free %ld KB", GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES), GetNumTasks(), GetFreeSpace(0) / 1024);
    for (;;) {
        MSG m; int n, k;
        if (PeekMessage(&m, 0, 0, 0, PM_REMOVE)) { if (m.message == WM_QUIT) break; TranslateMessage(&m); DispatchMessage(&m); continue; }
        n = bs_event(e, 140);
        if (n <= 0) { bs_idle(); continue; }
        if ((e[0] >> 8) == 4 || (e[0] >> 8) == 8) {
            for (k = 3; k < n && accn < (int)sizeof acc - 2; k++) { acc[accn++] = (char)(e[k] & 0xFF); acc[accn++] = (char)(e[k] >> 8); }
            if ((e[0] >> 8) == 4) { acc[accn] = 0; accn = 0; host_line(acc); }
        }
    }
    return 0;
}
