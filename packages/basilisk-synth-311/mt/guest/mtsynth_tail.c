/* ================================================================ lanes */
/* A stripped recorder has no status field: the card says whether its task has the wave device open (Sound Recorder
   opens it on Play and closes it when the sound ends or Stop is pressed) */
static BOOL is_playing(int r)
{
    WORD v;
    if (GetDlgItem(rw[r], SR_STATUS)) return is_playing_text(r);
    _disable(); bs_put((WORD)rt[r]); outpw(BS_CMD, 35); v = bs_get(); _enable();
    return v != 0;
}
/* While a recorder is built, its status, position and length fields exist again for a moment: static controls of
   ours with Sound Recorder's ids, which it writes as it works (SetDlgItemText finds them by id) */
static HWND tmpf[3];
static void temp_fields(int r, BOOL on)
{
    int k;
    for (k = 0; k < 3; k++) {
        if (on) tmpf[k] = GetDlgItem(rw[r], 200 + k) ? NULL : CreateWindow("STATIC", "", WS_CHILD, 0, 0, 1, 1, rw[r], (HMENU)(200 + k), hInst, NULL);
        else if (tmpf[k]) { DestroyWindow(tmpf[k]); tmpf[k] = NULL; }
    }
}
static int layer_len[NL];
static void layer_replies(void)
{
    int i;
    for (i = 0; i < nlay; i++)
        if (lay[i].count) {
            lnFrames[bank][i] = (long)layer_len[i] * sound_rate(lay[i].source) / 100;
            say("@%d layer %d %d %d %d %ld", bank, i, lay[i].first, lay[i].count, sound_rate(lay[i].source), lnFrames[bank][i]);
            if (nSeg[i] > 1) {
                char t[160]; int k, n = sprintf(t, "@%d seg %d", bank, i);
                for (k = 0; k < nSeg[i] && n < 140; k++) n += sprintf(t + n, " %ld", (long)segCs[i][k] * sound_rate(lay[i].source) / 100);
                say("%s", (LPSTR)t);
            }
        }
        else say("@%d layer %d %d 0 0 0", bank, i, lay[i].first);
}
static char sigBuf[1400]; static int buildLog = 1;
static void build(const char *dna)   /* the lane `bank`'s DNA, on its recorders (offline: nothing plays meanwhile) */
{
    DWORD t0 = timeGetTime(); int i, r;
    static char mine[1100];
    lstrcpyn(mine, dna, sizeof mine);
    dna_parse(mine);
    signature(sigBuf);
    if (!_fstrcmp(sigBuf, lnSig[bank])) { layer_replies(); say("@%d built 0", bank); return; }
    building = TRUE;
    HookActive(TRUE);
    for (i = 0; i < nlay; i++) {
        LAYER *Ly = &lay[i];
        for (r = Ly->first; r < Ly->first + Ly->count; r++) {
            int a = bank * NR + r;
            if (!rw[a]) continue;
            stop_rec(a, 0, 1500);
            rlayer[a] = i;
            temp_fields(a, TRUE);
            if (tmpf[2]) { SendMessage(rw[a], WM_COMMAND, SR_REW, 0L); }   /* (it writes its fields as it rewinds) */
            { DWORD tr = timeGetTime(); layer_len[i] = run_steps(a, Ly); if (buildLog) logf_("@%d rec %d layer %d len %d in %ld ms", bank, r, i, layer_len[i], (long)(timeGetTime() - tr)); }
            temp_fields(a, FALSE);
            recRate[a] = sound_rate(Ly->source);
            poll_host(); pump();
        }
    }
    HookActive(FALSE);
    for (r = bank * NR; r < bank * NR + NR; r++) hostRate[r] = recRate[r];
    _fstrcpy(lnSig[bank], sigBuf);
    building = FALSE;
    layer_replies();
    say("@%d built %ld", bank, (long)(timeGetTime() - t0));
}
static void watch_ends(void)
{
    static DWORD last; int r;
    stops_due();
    if (timeGetTime() - last < 25) return;
    last = timeGetTime();
    for (r = 0; r < NALL; r++) if (rplay[r] && !is_playing(r)) { rplay[r] = FALSE; say("@%d end %d", r / NR, r % NR); }
}
static void host_line(char *s)
{
    char *a, *rest;
    if (s[0] == '@') {   /* a lane's line */
        int ln = atoi(s + 1); char *sp = strchr(s, ' ');
        if (ln < 0 || ln >= NB || !sp) return;
        bank = ln; s = sp + 1;
    } else bank = 0;
    a = strchr(s, ' '); rest = a ? a + 1 : "";
    if (a) *a = 0;
    if (!strcmp(s, "hi")) say("hi 3 311 ready win,desk,rate,loop,tape,lanes=%d,recs=%d", NB, laneRecs);
    else if (!strcmp(s, "dna")) build(rest);
    else if (!strcmp(s, "on")) {
        long f[8] = {0, 0, 65535, 0, 0, -1, 0, 0}; int nf = 0; char *p = rest;
        while (*p && nf < 8) { f[nf++] = atol(p); p = strchr(p, ' '); if (!p) break; p++; }
        if (f[0] >= 0 && f[0] < laneRecs) play_rec((int)f[0], curId, (DWORD)f[1], (WORD)f[2], (int)f[3], (int)f[5], f[6]);
    }
    else if (!strcmp(s, "mod")) {
        int f[9] = {-1, 0, 0, 0, 0, 0, 0, 0, 0}, nf = 0, k; char *p = rest;
        while (*p && nf < 9) { f[nf++] = atoi(p); p = strchr(p, ' '); if (!p) break; p++; }
        if (f[0] >= 0 && f[0] < NR) { for (k = 0; k < 8; k++) modArg[f[0]][k] = f[k + 1] < 0 ? 0 : f[k + 1]; modOn[f[0]] = 1; }
    }
    else if (!strcmp(s, "off")) { int r = atoi(rest); if (r >= 0 && r < laneRecs) stop_rec(AR(r), curId, lnRel[bank]); }
    else if (!strcmp(s, "cut")) { int r = atoi(rest); if (r >= 0 && r < laneRecs) stop_rec(AR(r), curId, 5); }
    else if (!strcmp(s, "choke")) {
        int r = atoi(rest), f = strchr(rest, ' ') ? atoi(strchr(rest, ' ') + 1) : 10;
        if (r >= 0 && r < laneRecs) stop_rec(AR(r), curId, f > 0 ? f : 10);
    }
    else if (!strcmp(s, "rate")) {
        long f[4] = {-1, 0, 0, 0}; int nf = 0; char *p = rest;
        while (*p && nf < 4) { f[nf++] = atol(p); p = strchr(p, ' '); if (!p) break; p++; }
        if (f[0] >= 0 && f[0] < laneRecs) rate_rec(AR((int)f[0]), curId, (DWORD)f[1], (int)f[2], (int)f[3]);
    }
    else if (!strcmp(s, "env")) {   /* per lane: the card keeps A, D, S for each */
        int A = 0, D = 0, S = 100, R = 120;
        sscanf(rest, "%d %d %d %d", &A, &D, &S, &R);
        lnRel[bank] = R;
        _disable(); bs_put((WORD)A); bs_put((WORD)D); bs_put((WORD)S); bs_put((WORD)bank); outpw(BS_CMD, 27); _enable();
    }
    else if (!strcmp(s, "lenv")) {
        int L = atoi(rest), kind, n = 0, t[8], l[8], loop = 0; char *p = strchr(rest, ' ');
        if (p && L >= 0 && L < NL) {
            kind = p[1] == 'p'; p = strchr(p + 1, ' ');
            if (p && p[1] != '-') {
                const char *q = p + 1;
                while (*q && n < 8) {
                    t[n] = getint(&q, 0); if (*q == ',') q++; l[n] = getint(&q, 0); n++;
                    if (*q == '.') q++; else break;
                }
            }
            if (p && (p = strchr(p + 1, ' ')) != NULL) loop = atoi(p + 1);
            bs_lenv(bank * NL + L, kind, n, t, l, loop);
        }
    }
    else if (!strcmp(s, "q")) {   /* test aid: a recorder's status, position and length fields */
        int r = AR(atoi(rest)); char a1[24] = "", a2[24] = "", a3[24] = "";
        if (rw[r]) { GetDlgItemText(rw[r], SR_STATUS, a1, 24); GetDlgItemText(rw[r], SR_POS, a2, 24); GetDlgItemText(rw[r], SR_LEN, a3, 24); }
        say("@%d q %d '%s' '%s' '%s' win %d", bank, r % NR, (LPSTR)a1, (LPSTR)a2, (LPSTR)a3, IsWindow(rw[r]));
    }
    else if (!strcmp(s, "packs")) lib_packs(rest);
    else if (!strcmp(s, "panic")) { int r; for (r = 0; r < NALL; r++) stop_rec(r, 0, 5); }
    else if (!strcmp(s, "stats")) {   /* the experiment's numbers */
        say("stats plays %ld slowmax %ld user %d gdi %d free %ld", (long)nPlays, (long)slowMax, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES), GetFreeSpace(0) / 1024);
        slowMax = 0;
    }
    else if (!strcmp(s, "mem")) {   /* every global block, by owner task: who holds the wave buffers */
        GLOBALENTRY g; long sr = 0, all = 0; int nb = 0;
        MEMMANINFO m; m.dwSize = sizeof m; MemManInfo(&m);
        g.dwSize = sizeof g;
        if (GlobalFirst(&g, GLOBAL_ALL)) do {
            TASKENTRY te; MODULEENTRY me; te.dwSize = sizeof te; me.dwSize = sizeof me;
            if (g.wType == GT_FREE) continue;
            all += g.dwBlockSize;
            if ((TaskFindHandle(&te, (HTASK)g.hOwner) && !lstrcmp(te.szModule, "SOUNDREC")) || (ModuleFindHandle(&me, (HMODULE)g.hOwner) && !lstrcmp(me.szModule, "SOUNDREC"))) { sr += g.dwBlockSize; nb++; }
        } while (GlobalNext(&g, GLOBAL_ALL));
        say("mem used %ld KB soundrec %ld KB blocks %d freepages %ld totalpages %ld", all / 1024, sr / 1024, nb, m.dwFreePages, m.dwTotalPages);
    }
}
static int poll_host(void)
{
    static WORD e[140];
    static char acc[1200]; static int accn;
    int n, k, handled = 0;
    while ((n = bs_event(e, 140)) > 0) {
        int ty = e[0] >> 8;
        if (ty == 4 || ty == 8) {
            for (k = 3; k < n && accn < (int)sizeof acc - 2; k++) { acc[accn++] = (char)(e[k] & 0xFF); acc[accn++] = (char)(e[k] >> 8); }
            if (ty == 4) { acc[accn] = 0; accn = 0; curId = MAKELONG(e[1], e[2]); host_line(acc); }
        }
        handled++;
    }
    watch_ends();
    return handled;
}

/* ================================================================ the launcher */
static UINT msgStrip;
static HANDLE __far gh[3000]; static int ngh;
static void gdi_handles(void)
{
    SYSHEAPINFO h; LOCALENTRY e; h.dwSize = sizeof h; ngh = 0;
    if (!SystemHeapInfo(&h)) return;
    e.dwSize = sizeof e;
    if (LocalFirst(&e, h.hGDISegment)) do { if (!(e.wFlags & LF_FREE) && ngh < 3000) gh[ngh++] = e.hHandle; } while (LocalNext(&e));
}
static int gdi_delete_new(void)   /* brushes, fonts, pens and bitmaps a hidden recorder made: it never paints */
{
    SYSHEAPINFO h; LOCALENTRY e; int k, n = 0; h.dwSize = sizeof h;
    if (!SystemHeapInfo(&h)) return 0;
    e.dwSize = sizeof e;
    if (LocalFirst(&e, h.hGDISegment)) do {
        if (e.wFlags & LF_FREE) continue;
        if (e.wType != LT_GDI_BRUSH && e.wType != LT_GDI_BITMAP && e.wType != LT_GDI_FONT && e.wType != LT_GDI_PEN) continue;
        for (k = 0; k < ngh && gh[k] != e.hHandle; k++) {}
        if (k < ngh) continue;
        if (DeleteObject((HGDIOBJ)e.hHandle)) n++;
    } while (LocalNext(&e));
    return n;
}
static HWND window_of(HINSTANCE hi)
{
    HWND x;
    for (x = GetWindow(GetDesktopWindow(), GW_CHILD); x; x = GetWindow(x, GW_HWNDNEXT))
        if (GetWindowWord(x, GWW_HINSTANCE) == (WORD)hi && !GetParent(x)) return x;
    return NULL;
}
#ifndef KEEP_WORK
#define KEEP_WORK 0x8017
#endif
#ifndef OFFSCREEN
#define OFFSCREEN 1
#endif
#ifndef GDIDEL
#define GDIDEL 1
#endif
#define KEEP_WORK_   /* status, position, length, seek bar: what the build and the notes read */
#ifndef KEEP_LEAD
#define KEEP_LEAD 0x801F   /* and the wave display, for a lane's first recorder */
#endif
#define WAVEW 236
#define WAVEH 44
static void lead_place(int k)   /* lane k's first recorder: a child of ours, its wave display in the grid */
{
    int r = k * NR, col = k % 4, row = k / 4; HWND wv;
    LONG st = GetWindowLong(rw[r], GWL_STYLE);
    st &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME);
    SetWindowLong(rw[r], GWL_STYLE, st | WS_CHILD | WS_CLIPSIBLINGS);
    SetParent(rw[r], hMain);
    SetWindowPos(rw[r], HWND_TOP, 8 + col * (WAVEW + 16), 28 + row * (WAVEH + 30), WAVEW, WAVEH, SWP_NOACTIVATE);
    wv = GetDlgItem(rw[r], SR_WAVE);
    if (wv) SetWindowPos(wv, NULL, 0, 0, WAVEW, WAVEH, SWP_NOZORDER | SWP_NOACTIVATE);
    ShowWindow(rw[r], SW_SHOWNA);
}
long FAR PASCAL __export MainProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; HDC dc = BeginPaint(h, &ps); int k; char t[24];
        SetBkMode(dc, TRANSPARENT);
        TextOut(dc, 8, 4, "SNDWAVE2000 multitimbral experiment: one Windows, many lanes", 59);
        for (k = 0; k < NB; k++) { wsprintf(t, "Lane %d", k + 1); TextOut(dc, 8 + k % 4 * (WAVEW + 16), 28 + k / 4 * (WAVEH + 30) + WAVEH + 2, t, lstrlen(t)); }
        EndPaint(h, &ps); return 0;
    }
    return DefWindowProc(h, m, w, l);
}
int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show)
{
    WNDCLASS wc; HINSTANCE hk; int k, j, dels = 0, fails = 0; DWORD t0;
    hInst = hi;
    for (k = 0; k < NB; k++) lnRel[k] = 120;
    if (!bs_present()) return 1;
    hk = LoadLibrary("C:\\BS\\SYNHOOK.DLL");
    if ((UINT)hk < 32) { logf_("no SYNHOOK.DLL"); return 1; }
    HookActive = (void (FAR PASCAL *)(BOOL))GetProcAddress(hk, "HOOKACTIVE");
    HookPending = (void (FAR PASCAL *)(LPCSTR))GetProcAddress(hk, "HOOKPENDING");
    ((BOOL (FAR PASCAL *)(BOOL))GetProcAddress(hk, "HOOKINSTALL"))(TRUE);
    hk = LoadLibrary("C:\\MT\\MTHOOK.DLL");
    if ((UINT)hk >= 32) msgStrip = ((UINT (FAR PASCAL *)(void))GetProcAddress(hk, "MTINSTALL"))();
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = MainProc; wc.hInstance = hi; wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1); wc.lpszClassName = "MtLanes";
    RegisterClass(&wc);
    hMain = CreateWindow("MtLanes", "SNDWAVE2000 Lanes", WS_POPUP | WS_CAPTION | WS_CLIPCHILDREN | WS_VISIBLE,
                         0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), NULL, NULL, hi, NULL);
    { HWND pm = FindWindow("Progman", NULL); if (pm) ShowWindow(pm, SW_MINIMIZE); }
    say("mt up: user %d%% gdi %d%% free %ld KB", GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES), GetFreeSpace(0) / 1024);
    t0 = timeGetTime();
    for (k = 0; k < NB; k++)
        for (j = 0; j < laneRecs; j++) {
            int r = k * NR + j; HINSTANCE h; DWORD tw;
            if (j) gdi_handles();
            h = WinExec("SOUNDREC.EXE C:\\WINDOWS\\DING.WAV", SW_HIDE);
            if ((UINT)h < 32) { if (!fails++) say("launch failed at lane %d rec %d code %u user %d%% gdi %d%%", k, j, (UINT)h, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES)); continue; }
            tw = timeGetTime();
            while (!rw[r] && timeGetTime() - tw < 8000) { pump(); rw[r] = window_of(h); }
            if (!rw[r]) continue;
            rt[r] = GetWindowTask(rw[r]); recRate[r] = hostRate[r] = 22050;
            pump();
            if (msgStrip) PostMessage(rw[r], msgStrip, j ? KEEP_WORK : KEEP_LEAD, 0L);
            pump();
            if (j && GDIDEL) dels += gdi_delete_new();
            if (!j) lead_place(k);
            else if (OFFSCREEN) SetWindowPos(rw[r], HWND_BOTTOM, -3000, -3000, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW);   /* shown, out of sight */
        }
    { int d = 0; for (k = 0; k < NALL; k++) if (rw[k]) d++;
      say("mt ready: %d lanes x %d recorders (%d up) in %ld ms; user %d%% gdi %d%% free %ld KB; gdi objects deleted %d",
          NB, laneRecs, d, (long)(timeGetTime() - t0), GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES), GetFreeSpace(0) / 1024, dels); }
    for (;;) {
        MSG m;
        if (PeekMessage(&m, 0, 0, 0, PM_REMOVE)) { if (m.message == WM_QUIT) break; TranslateMessage(&m); DispatchMessage(&m); }
        else if (!poll_host()) bs_idle();
    }
    return 0;
}
