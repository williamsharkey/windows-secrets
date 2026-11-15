/* ================================================================ SNDWAVE2000 Ensemble: lanes */
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

static BOOL lnVoiced[NB];          /* the lane has a sound of its own (an empty lane shows "no voice") */
static BOOL lnNamed[NB];           /* the host named a preset for it: its recorder's sound shows until the preset is built */
static void run_pending(void);
static void grid_dirty(void);
/* ---------------------------------------------------------------- the launcher: recorders on demand */
static UINT msgStrip;
static HANDLE __far gh[3000]; static int ngh;
static int nLaneRecs[NB];          /* recorders launched for each lane */
static int recsUp, recFail;
static void gdi_handles(void)
{
    SYSHEAPINFO h; LOCALENTRY e; h.dwSize = sizeof h; ngh = 0;
    if (!SystemHeapInfo(&h)) return;
    e.dwSize = sizeof e;
    if (LocalFirst(&e, h.hGDISegment)) do { if (!(e.wFlags & LF_FREE) && ngh < 3000) gh[ngh++] = e.hHandle; } while (LocalNext(&e));
}
static int gdi_delete_new(void)   /* brushes, fonts, pens and bitmaps a stripped recorder made: it never paints */
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
        if (GetWindowWord(x, GWW_HINSTANCE) == (WORD)hi && !GetParent(x)) {
            char c[16]; GetClassName(x, c, sizeof c);
            if (!lstrcmp(c, "SoundRec")) return x;   /* (not its OLE server window, SrvrWndClass) */
        }
    return NULL;
}
#define KEEP_WORK 0x8000   /* a worker keeps no control (the card and our own fields stand in) */
#define KEEP_LEAD 0x8008   /* a lane's first recorder keeps its wave display (the assembly shows it) */
static void hide_srvr(void)   /* Sound Recorder's OLE server windows (SrvrWndClass), out of sight as soon as they exist */
{
    HWND x;
    for (x = GetWindow(GetDesktopWindow(), GW_CHILD); x; x = GetWindow(x, GW_HWNDNEXT))
        if (IsWindowVisible(x)) { char c[16]; GetClassName(x, c, sizeof c); if (!lstrcmp(c, "SrvrWndClass")) SetWindowPos(x, NULL, -3000, -3000, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_HIDEWINDOW); }
}
static BOOL launch_rec(int k, int j)
{
    int r = k * NR + j; HINSTANCE h; DWORD tw;
    if (rw[r]) return TRUE;
    if (j) gdi_handles();
    h = WinExec("SOUNDREC.EXE C:\\WINDOWS\\DING.WAV", SW_SHOWNOACTIVATE);
    if ((UINT)h < 32) { if (!recFail++) logf_("launch failed at lane %d rec %d code %u user %d%% gdi %d%%", k, j, (UINT)h, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES)); return FALSE; }
    tw = timeGetTime();
    while (!rw[r] && timeGetTime() - tw < 8000) { pump(); rw[r] = window_of(h); }
    if (!rw[r]) return FALSE;
    rt[r] = GetWindowTask(rw[r]); recRate[r] = hostRate[r] = 22050;
    {   /* its OLE server window (SrvrWndClass) out of sight too: SW_SHOWNOACTIVATE shows it at 0, 0 */
        HWND x;
        for (x = GetWindow(GetDesktopWindow(), GW_CHILD); x; x = GetWindow(x, GW_HWNDNEXT))
            if (GetWindowWord(x, GWW_HINSTANCE) == (WORD)h && x != rw[r]) SetWindowPos(x, HWND_BOTTOM, -3000, -3000, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE | SWP_HIDEWINDOW);
    }
    SetWindowPos(rw[r], HWND_BOTTOM, -3000, -3000, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);   /* shown, out of sight */
    pump();
    if (msgStrip) PostMessage(rw[r], msgStrip, j ? KEEP_WORK : KEEP_LEAD, 0L);
    pump();
    if (j) gdi_delete_new();
    hide_srvr();
    recsUp++;
    return TRUE;
}
static void ensure_recs(int k, int n)   /* lane k gets at least n recorders (launched now if it has fewer) */
{
    int j;
    for (j = 0; j < n && j < LANE_RECS; j++) if (!rw[k * NR + j] && !launch_rec(k, j)) break;
    if (j > nLaneRecs[k]) nLaneRecs[k] = j;
}

/* ---------------------------------------------------------------- the build */
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
static void wave_dirty(int k);
static void show_recs(int k);
static char sigBuf[1400];
static void build(const char *dna)   /* the lane `bank`'s DNA, on its recorders, in place (notes are served in between) */
{
    DWORD t0 = timeGetTime(); int i, r;
    static char mine[1100];
    lstrcpyn(mine, dna, sizeof mine);
    ensure_recs(bank, laneRecs);
    if (nLaneRecs[bank] < laneRecs) laneRecs = nLaneRecs[bank] ? nLaneRecs[bank] : 1;
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
            hide_srvr();
            rlayer[a] = i;
            temp_fields(a, TRUE);
            if (tmpf[2]) { SendMessage(rw[a], WM_COMMAND, SR_REW, 0L); }   /* (it writes its fields as it rewinds) */
            layer_len[i] = run_steps(a, Ly);
            temp_fields(a, FALSE);
            recRate[a] = sound_rate(Ly->source);
            { int b = bank, lr = laneRecs; poll_host(); pump(); bank = b; laneRecs = lr; }   /* (notes of any lane are served meanwhile) */
        }
    }
    HookActive(FALSE);
    for (r = bank * NR; r < bank * NR + NR; r++) hostRate[r] = recRate[r];
    _fstrcpy(lnSig[bank], sigBuf);
    building = FALSE;
    lnVoiced[bank] = TRUE;
    layer_replies();
    {   /* the lane's waveform: its first recorder plays its new sound once, silently, so the card sees the buffer */
        int a = bank * NR + (nlay ? lay[0].first : 0);
        if (rw[a] && !rplay[a]) { bs_arm2(rt[a], 0, 0, 0, 0, bank * NL); press(a, SR_PLAY); }
    }
    wave_dirty(bank); show_recs(bank);
    grid_dirty();
    say("@%d built %ld", bank, (long)(timeGetTime() - t0));
    run_pending();
}

/* ================================================================ the mixer window */
#define STRIPW 100
#define SX(k) (12 + (k) * STRIPW)
#define WAVEX 6        /* the vertical waveform, in the strip */
#define WAVEY 108
#define WAVEW 46
#define WAVEH 236
#define LEVX 62
#define ID_CH 1600     /* + lane */
#define ID_PREV 1620
#define ID_NEXT 1640
#define ID_LEV 1660
#define ID_PAN 1680
#define ID_MUTE 1700
#define ID_SOLO 1720
static HWND hCh[NB], hName[NB], hPrev[NB], hNext[NB], hWave[NB], hLev[NB], hLevVal[NB], hPan[NB], hPanVal[NB], hMute[NB], hSolo[NB], hInfo[NB], hGrid, hStatus;
static int lnLevel[NB], lnPan[NB], lnMute[NB], lnSolo[NB], lnChan[NB], lnSeq[NB], lnPos[NB];
static char lnName[NB][40];
static int waveAngle[NB] = {900, 900, 900, 900, 900, 900, 900, 900, 900, 900};   /* tenths of a degree: 0 horizontal (as Sound Recorder), 900 vertical */
static signed char __far lnPk[NB][64][2];
static BOOL lnPkDirty[NB];
static BOOL assembling;
static HFONT hSmall;
static HBRUSH hBlack;
static HPEN hGreen, hGrey, hYellow;

static void wave_dirty(int k) { if (k >= 0 && k < NB) lnPkDirty[k] = TRUE; }
static void show_recs(int k) { char t[32]; if (hInfo[k]) { wsprintf(t, "%d rec", nLaneRecs[k]); SetWindowText(hInfo[k], t); } }
/* the lane's waveform from the card: 64 min/max pairs of the buffer its recorder last played, and where it plays */
static BOOL peaks_read(int k)
{
    WORD w[66]; int i, n = 64; WORD seq, pos;
    _disable(); bs_put((WORD)k); bs_put((WORD)n); outpw(BS_CMD, 36); seq = bs_get(); pos = bs_get();
    for (i = 0; i < n; i++) w[i] = bs_get();
    _enable();
    if (seq == (WORD)lnSeq[k] && (int)pos == lnPos[k]) return FALSE;
    lnSeq[k] = seq; lnPos[k] = pos;
    for (i = 0; i < n; i++) { lnPk[k][i][0] = (signed char)(w[i] & 0xFF); lnPk[k][i][1] = (signed char)(w[i] >> 8); }
    return TRUE;
}
/* a waveform drawn the way Sound Recorder draws one (green on black, the silence line), turned by `deci` tenths of a
   degree about its centre: u runs along the sound, v across it; 0 is Sound Recorder's own horizontal display */
static long isin(int deci)   /* sin in 1/16384, by table: no floating point on the emulated CPU */
{
    static const int q[91] = {0,286,572,857,1143,1428,1713,1997,2280,2563,2845,3126,3406,3686,3964,4240,4516,4790,5063,5334,5604,
        5872,6138,6402,6664,6924,7182,7438,7692,7943,8192,8438,8682,8923,9162,9397,9630,9860,10087,10311,10531,10749,10963,11174,
        11381,11585,11786,11982,12176,12365,12551,12733,12911,13085,13255,13421,13583,13741,13894,14044,14189,14330,14466,14598,
        14726,14849,14968,15082,15191,15296,15396,15491,15582,15668,15749,15826,15897,15964,16026,16083,16135,16182,16225,16262,
        16294,16322,16344,16362,16374,16382,16384};
    int d = ((deci % 3600) + 3600) % 3600, s = 1, a;
    if (d >= 1800) { d -= 1800; s = -1; }
    if (d > 900) d = 1800 - d;
    a = d / 10;
    if (a >= 90) return s * 16384L;
    return s * (q[a] + (long)(q[a + 1] - q[a]) * (d % 10) / 10);
}
static long icos(int deci) { return isin(deci + 900); }
static void wave_paint(HDC dc, int k, int cw, int ch)
{
    RECT rc; int i, len, amp; long s = isin(waveAngle[k]), c = icos(waveAngle[k]); int cx = cw / 2, cy = ch / 2;
    SetRect(&rc, 0, 0, cw, ch); FillRect(dc, &rc, hBlack);
    if (!lnVoiced[k] && !lnNamed[k]) {   /* no sound on this lane: the silence line, and "no voice" */
        SelectObject(dc, hGrey);
        MoveTo(dc, cx - (int)(icos(waveAngle[k]) * (cw > ch ? cw : ch) / 2 / 16384), cy - (int)(isin(waveAngle[k]) * (cw > ch ? cw : ch) / 2 / 16384));
        LineTo(dc, cx + (int)(icos(waveAngle[k]) * (cw > ch ? cw : ch) / 2 / 16384), cy + (int)(isin(waveAngle[k]) * (cw > ch ? cw : ch) / 2 / 16384));
        if (assembled && waveAngle[k] == 900) {
            HFONT of = SelectObject(dc, hSmall); SetTextColor(dc, RGB(0, 128, 0)); SetBkMode(dc, TRANSPARENT);
            TextOut(dc, 3, ch / 2 - 20, "no", 2); TextOut(dc, 3, ch / 2 - 6, "voice", 5); SelectObject(dc, of);
        }
        return;
    }
    /* the sound's length and height: the longer side runs along it */
    len = (int)((labs(c) * cw + labs(s) * ch) / 16384); amp = (int)((labs(s) * cw + labs(c) * ch) / 16384) / 2 - 1;
    if (len < 8) len = 8; if (amp < 2) amp = 2;
    SelectObject(dc, hGrey);   /* the silence line */
    MoveTo(dc, cx + (int)(-(long)len / 2 * c / 16384), cy + (int)(-(long)len / 2 * s / 16384));
    LineTo(dc, cx + (int)((long)len / 2 * c / 16384), cy + (int)((long)len / 2 * s / 16384));
    SelectObject(dc, hGreen);
    for (i = 0; i < 64; i++) {
        long u = (long)len * i / 64 - len / 2, v0 = (long)lnPk[k][i][0] * amp / 128, v1 = (long)lnPk[k][i][1] * amp / 128;
        MoveTo(dc, cx + (int)((u * c - v0 * s) / 16384), cy + (int)((u * s + v0 * c) / 16384));
        LineTo(dc, cx + (int)((u * c - v1 * s) / 16384), cy + (int)((u * s + v1 * c) / 16384) + 1);
    }
    if (lnPos[k] >= 0 && lnPos[k] <= 1000) {   /* where the newest note plays */
        long u = (long)len * lnPos[k] / 1000 - len / 2;
        SelectObject(dc, hYellow);
        MoveTo(dc, cx + (int)((u * c + (long)amp * s) / 16384), cy + (int)((u * s - (long)amp * c) / 16384));
        LineTo(dc, cx + (int)((u * c - (long)amp * s) / 16384), cy + (int)((u * s + (long)amp * c) / 16384));
    }
}
long FAR PASCAL __export WaveProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; RECT rc; HDC dc = BeginPaint(h, &ps); int k = GetWindowWord(h, 0);
        GetClientRect(h, &rc);
        if (k >= 0 && k < NB) wave_paint(dc, k, rc.right, rc.bottom);
        EndPaint(h, &ps); return 0;
    }
    if (m == WM_ERASEBKGND) return 1;
    if (m == WM_LBUTTONDOWN) { say("audition %d", GetWindowWord(h, 0)); return 0; }   /* a click plays the lane's root */
    return DefWindowProc(h, m, w, l);
}

/* the track view (bottom): every lane's notes as they play, a row each, scrolling left like a sequencer's track
   screen; within a row the height is the pitch. The names column on the left stays. */
#define GRIDX 12
#define GRIDY 520
#define GRIDW 1000
#define GRIDH 200
#define GRIDL 96        /* the names column */
#define GSTEP 2         /* pixels a tick (50 ms) */
#define NGN 64
static int gnLane[NGN], gnNote[NGN], gnVel[NGN], gnN;   /* notes since the last tick */
static void grid_dirty(void) { if (hGrid) InvalidateRect(hGrid, NULL, FALSE); }
static void grid_note(int lane, int note, int vel) { if (gnN < NGN) { gnLane[gnN] = lane; gnNote[gnN] = note; gnVel[gnN] = vel; gnN++; } }
static void grid_names(HDC dc)
{
    RECT rc; int k; char t[24]; HFONT of = SelectObject(dc, hSmall);
    SetRect(&rc, 0, 0, GRIDL, GRIDH); FillRect(dc, &rc, (HBRUSH)GetStockObject(BLACK_BRUSH));
    SetBkMode(dc, TRANSPARENT);
    for (k = 0; k < NB; k++) {
        SetTextColor(dc, lnVoiced[k] ? RGB(0, 255, 0) : RGB(0, 96, 0));
        wsprintf(t, "%2d %.12s", k + 1, (LPSTR)lnName[k]);
        TextOut(dc, 3, k * GRIDH / NB + 3, t, lstrlen(t));
    }
    SelectObject(dc, hGrey);
    for (k = 0; k <= NB; k++) { MoveTo(dc, 0, k * GRIDH / NB); LineTo(dc, GRIDW, k * GRIDH / NB); }
    MoveTo(dc, GRIDL - 1, 0); LineTo(dc, GRIDL - 1, GRIDH);
    SelectObject(dc, of);
}
long FAR PASCAL __export GridProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; RECT rc; HDC dc = BeginPaint(h, &ps);
        GetClientRect(h, &rc); FillRect(dc, &rc, hBlack);
        grid_names(dc);
        EndPaint(h, &ps); return 0;
    }
    return DefWindowProc(h, m, w, l);
}
static void grid_tick(void)   /* every 50 ms: the notes move a step left; the new ones appear at the right edge */
{
    static int col; HDC dc; RECT rc, sc; int k, i;
    if (!hGrid || !assembled) return;
    dc = GetDC(hGrid);
    SetRect(&sc, GRIDL, 0, GRIDW, GRIDH);
    ScrollDC(dc, -GSTEP, 0, &sc, &sc, NULL, NULL);
    SetRect(&rc, GRIDW - GSTEP, 0, GRIDW, GRIDH); FillRect(dc, &rc, hBlack);
    SelectObject(dc, hGrey);
    for (k = 0; k <= NB; k++) { MoveTo(dc, GRIDW - GSTEP, k * GRIDH / NB); LineTo(dc, GRIDW, k * GRIDH / NB); }
    if (++col % 20 == 0) { MoveTo(dc, GRIDW - 1, 0); LineTo(dc, GRIDW - 1, GRIDH); }   /* a beat line every second */
    for (i = 0; i < gnN; i++) {   /* a note: a mark at its pitch in its lane's row, brighter when louder */
        int y0 = gnLane[i] * GRIDH / NB + 1, hh = GRIDH / NB - 3, n = gnNote[i] < 24 ? 24 : gnNote[i] > 107 ? 107 : gnNote[i];
        int y = y0 + hh - (n - 24) * hh / 84;
        SetRect(&rc, GRIDW - GSTEP, y - 1, GRIDW, y + 2);
        FillRect(dc, &rc, (HBRUSH)GetStockObject(gnVel[i] > 90 ? WHITE_BRUSH : LTGRAY_BRUSH));
    }
    gnN = 0;
    ReleaseDC(hGrid, dc);
}

static void mix_show(int k)   /* the controls show the lane's mix */
{
    char t[16];
    SetScrollPos(hLev[k], SB_CTL, 127 - lnLevel[k], TRUE);
    wsprintf(t, "%d", lnLevel[k]); SetWindowText(hLevVal[k], t);
    SetScrollPos(hPan[k], SB_CTL, lnPan[k] + 64, TRUE);
    if (lnPan[k] == 0) lstrcpy(t, "C"); else wsprintf(t, "%c%d", lnPan[k] < 0 ? 'L' : 'R', lnPan[k] < 0 ? -lnPan[k] : lnPan[k]);
    SetWindowText(hPanVal[k], t);
    SendMessage(hMute[k], BM_SETCHECK, lnMute[k], 0L);
    SendMessage(hSolo[k], BM_SETCHECK, lnSolo[k], 0L);
}
static void mix_send(int k) { say("mix %d %d %d %d %d", k, lnLevel[k], lnPan[k], lnMute[k], lnSolo[k]); }
static HWND mk(const char *cls, const char *text, DWORD st, int x, int y, int w, int h, int id)
{
    HWND c = CreateWindow(cls, text, WS_CHILD | WS_CLIPSIBLINGS | st, x, y, w, h, hMain, (HMENU)id, hInst, NULL);   /* (siblings overlap while they fly) */
    if (c && hSmall && lstrcmp(cls, "EnsWave")) SendMessage(c, WM_SETFONT, (WPARAM)hSmall, 0L);
    return c;
}
/* the final place of each of a strip's controls (x, y, w, h), in the strip */
typedef struct { int x, y, w, h; } PL;
static const PL plCh = {4, 30, 92, 22}, plName = {4, 54, 92, 28}, plPrev = {4, 84, 45, 20}, plNext = {51, 84, 45, 20},
    plWave = {WAVEX, WAVEY, WAVEW, WAVEH}, plLev = {LEVX, WAVEY, 17, WAVEH}, plLevVal = {58, WAVEY + WAVEH + 2, 36, 14},
    plPan = {4, 372, 92, 17}, plPanVal = {4, 390, 92, 14}, plMute = {4, 410, 46, 20}, plSolo = {52, 410, 44, 20},
    plInfo = {4, 434, 92, 14};
static void place(HWND c, int k, const PL *p) { SetWindowPos(c, NULL, SX(k) + p->x, p->y, p->w, p->h, SWP_NOZORDER | SWP_NOACTIVATE); }
static void strips_create(void)
{
    int k; char t[16];
    for (k = 0; k < NB; k++) {
        wsprintf(t, "Ch %d", lnChan[k]);
        hCh[k] = mk("BUTTON", t, BS_PUSHBUTTON, 0, 0, 1, 1, ID_CH + k);
        hName[k] = mk("STATIC", lnName[k], SS_CENTER, 0, 0, 1, 1, -1);
        hPrev[k] = mk("BUTTON", "<", BS_PUSHBUTTON, 0, 0, 1, 1, ID_PREV + k);
        hNext[k] = mk("BUTTON", ">", BS_PUSHBUTTON, 0, 0, 1, 1, ID_NEXT + k);
        hWave[k] = mk("EnsWave", "", 0, 0, 0, 1, 1, -1); SetWindowWord(hWave[k], 0, (WORD)k);
        hLev[k] = mk("SCROLLBAR", "", SBS_VERT, 0, 0, 1, 1, ID_LEV + k); SetScrollRange(hLev[k], SB_CTL, 0, 127, FALSE);
        hLevVal[k] = mk("STATIC", "", SS_CENTER, 0, 0, 1, 1, -1);
        hPan[k] = mk("SCROLLBAR", "", SBS_HORZ, 0, 0, 1, 1, ID_PAN + k); SetScrollRange(hPan[k], SB_CTL, 0, 127, FALSE);
        hPanVal[k] = mk("STATIC", "", SS_CENTER, 0, 0, 1, 1, -1);
        hMute[k] = mk("BUTTON", "Mute", BS_AUTOCHECKBOX, 0, 0, 1, 1, ID_MUTE + k);
        hSolo[k] = mk("BUTTON", "Solo", BS_AUTOCHECKBOX, 0, 0, 1, 1, ID_SOLO + k);
        hInfo[k] = mk("STATIC", "", SS_CENTER, 0, 0, 1, 1, -1);
        mix_show(k); show_recs(k);
    }
    hGrid = mk("EnsGrid", "", 0, GRIDX, GRIDY, GRIDW, GRIDH, -1);
    hStatus = mk("STATIC", "", SS_LEFT, GRIDX, GRIDY + GRIDH + 8, GRIDW, 16, -1);
}
static void strips_final(void)
{
    int k;
    for (k = 0; k < NB; k++) {
        place(hCh[k], k, &plCh); place(hName[k], k, &plName); place(hPrev[k], k, &plPrev); place(hNext[k], k, &plNext);
        place(hWave[k], k, &plWave); place(hLev[k], k, &plLev); place(hLevVal[k], k, &plLevVal); place(hPan[k], k, &plPan);
        place(hPanVal[k], k, &plPanVal); place(hMute[k], k, &plMute); place(hSolo[k], k, &plSolo); place(hInfo[k], k, &plInfo);
        waveAngle[k] = 900;
    }
}
static void strips_show(int k, int on)
{
    HWND *c[12]; int i;
    c[0] = &hCh[k]; c[1] = &hName[k]; c[2] = &hPrev[k]; c[3] = &hNext[k]; c[4] = &hWave[k]; c[5] = &hLev[k]; c[6] = &hLevVal[k];
    c[7] = &hPan[k]; c[8] = &hPanVal[k]; c[9] = &hMute[k]; c[10] = &hSolo[k]; c[11] = &hInfo[k];
    for (i = 0; i < 12; i++) ShowWindow(*c[i], on ? SW_SHOWNA : SW_HIDE);
}

/* ---------------------------------------------------------------- the assembly
   The lanes start as Sound Recorder's own horizontal wave displays (each lane's first recorder, as SNDWAVE2000 shows
   its strips), stacked down the left. Then, lane by lane, the waveform leaves its recorder: it turns from horizontal to
   vertical while it flies to its strip, and the strip's controls fly in after it. */
static long ease(long f) { if (f < 0) f = 0; if (f > 1000) f = 1000; return f * f / 1000 * (3000 - 2 * f) / 1000; }
static int lerp(int a, int b, long f) { return a + (int)((long)(b - a) * f / 1000); }
static DWORD animFrames, animMs;
#define ROWX(k) ((k) < 5 ? 40 : 540)   /* the stack: two columns of five, where the track view will be */
#define ROWY(k) (520 + ((k) % 5) * 44)
static void lead_show(int k, BOOL on)   /* the lane's first recorder: its own wave display, in the stack */
{
    int r = k * NR;
    if (!rw[r]) return;
    if (on) {
        LONG st = GetWindowLong(rw[r], GWL_STYLE);
        st &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_BORDER | WS_DLGFRAME);
        SetWindowLong(rw[r], GWL_STYLE, st | WS_CHILD | WS_CLIPSIBLINGS);
        SetParent(rw[r], hMain);
        SetWindowPos(rw[r], HWND_BOTTOM, ROWX(k), ROWY(k), 133, 35, SWP_NOACTIVATE);
        { HWND wv = GetDlgItem(rw[r], SR_WAVE); if (wv) SetWindowPos(wv, NULL, 0, 0, 133, 35, SWP_NOZORDER | SWP_NOACTIVATE); }
        ShowWindow(rw[r], SW_SHOWNA);
    } else SetWindowPos(rw[r], HWND_BOTTOM, -3000 + 0 * k, -3000, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);
}
static void fly(HWND c, int k, const PL *p, int fx, int fy, long f)
{
    long e = ease(f);
    SetWindowPos(c, NULL, lerp(fx, SX(k) + p->x, e), lerp(fy, p->y, e), p->w, p->h, SWP_NOZORDER | SWP_NOACTIVATE);
}
static void assemble(void)
{
    DWORD t0 = timeGetTime(), t; int k, done = 0;
    const DWORD per = 140, flyMs = 900;   /* a lane starts every 140 ms; its flight takes 900 ms */
    assembling = TRUE;
    for (k = 0; k < NB; k++) {   /* each lane's recorder plays its sound once, silently: the card has its waveform */
        int r = k * NR;
        if (rw[r] && (lnVoiced[k] || lnNamed[k])) { bs_arm2(rt[r], 0, 0, 0, 0, k * NL); press(r, SR_PLAY); }   /* (it plays out, silent: a Stop pressed at once hangs a stripped recorder) */
        lead_show(k, TRUE);
    }
    pump();
    for (k = 0; k < NB; k++) peaks_read(k);
    UpdateWindow(hMain);
    { DWORD tw = timeGetTime(); while (timeGetTime() - tw < 600) { pump(); poll_host(); } }   /* the recorders, as they are */
    t0 = timeGetTime();
    while (!done) {
        t = timeGetTime() - t0; done = 1;
        for (k = 0; k < NB; k++) {
            long f = t < k * per ? -1 : (long)(t - k * per) * 1000 / flyMs;
            if (f < 0) { done = 0; continue; }
            if (f > 1000) f = 1000;
            if (f < 1000) done = 0;
            if (!IsWindowVisible(hWave[k])) {   /* the waveform takes over from the recorder's own display, in place */
                waveAngle[k] = 0;
                SetWindowPos(hWave[k], HWND_TOP, ROWX(k), ROWY(k), 133, 35, SWP_NOACTIVATE);
                strips_show(k, TRUE);
                lead_show(k, FALSE);
            }
            {   /* the waveform: from 133 x 35 at angle 0 to WAVEW x WAVEH at 90 degrees, along a curve */
                long e = ease(f);
                int x = lerp(ROWX(k), SX(k) + WAVEX, e), y = lerp(ROWY(k), WAVEY, e), w = lerp(133, WAVEW, e), h = lerp(35, WAVEH, e);
                waveAngle[k] = (int)(900L * e / 1000);
                SetWindowPos(hWave[k], NULL, x, y, w, h, SWP_NOZORDER | SWP_NOACTIVATE);
                InvalidateRect(hWave[k], NULL, FALSE);
            }
            fly(hCh[k], k, &plCh, SX(k) + 4, -40, f); fly(hName[k], k, &plName, SX(k) + 4, -40, f);
            fly(hPrev[k], k, &plPrev, -60, 84, f); fly(hNext[k], k, &plNext, 1100, 84, f);
            fly(hLev[k], k, &plLev, SX(k) + LEVX, 800, f); fly(hLevVal[k], k, &plLevVal, SX(k) + 58, 800, f);
            fly(hPan[k], k, &plPan, SX(k) + 4, 800, f); fly(hPanVal[k], k, &plPanVal, SX(k) + 4, 800, f);
            fly(hMute[k], k, &plMute, -60, 410, f); fly(hSolo[k], k, &plSolo, 1100, 410, f);
            fly(hInfo[k], k, &plInfo, SX(k) + 4, 800, f);
        }
        RedrawWindow(hMain, NULL, NULL, RDW_UPDATENOW | RDW_ALLCHILDREN);
        animFrames++;
        pump(); poll_host();
    }
    strips_final();
    ShowWindow(hGrid, SW_SHOWNA); ShowWindow(hStatus, SW_SHOWNA);
    assembling = FALSE; assembled = TRUE;
    RedrawWindow(hMain, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_UPDATENOW);
    animMs = timeGetTime() - t0;
    logf_("assembled in %ld ms, %ld frames (%ld ms a frame)", (long)animMs, (long)animFrames, animFrames ? (long)(animMs / animFrames) : 0L);
    say("ready");
    { WORD z = 0; bs_report(1, &z, 0); }   /* the engine: BS_READY */
}

/* ---------------------------------------------------------------- rotbench: rotating Sound Recorder's own pixels
   The other way to turn a waveform: copy the pixels Sound Recorder painted (its wave display, 133 x 35) and map them
   through a rotation, nearest neighbour, on the emulated CPU. rotbench <lane> <deci> <n>: n rotations, timed; the last
   one stays on screen at (600, 40). */
static void rotbench(int k, int deci, int n)
{
    int r = k * NR, i, x, y, S2 = 140; HWND wv; HDC sdc, mdc, odc; HBITMAP src, dst, os, od; BITMAP bm;
    BYTE __huge *sb; BYTE __huge *db; long sbytes, dbytes; long s = isin(deci), c = icos(deci); DWORD t0, tc;
    if (!rw[r] || !(wv = GetDlgItem(rw[r], SR_WAVE))) { say("rotbench none"); return; }
    lead_show(k, TRUE); UpdateWindow(rw[r]);
    sdc = GetDC(wv); mdc = CreateCompatibleDC(sdc); odc = CreateCompatibleDC(sdc);
    src = CreateCompatibleBitmap(sdc, 133, 35); dst = CreateCompatibleBitmap(sdc, S2, S2);
    os = SelectObject(mdc, src); od = SelectObject(odc, dst);
    t0 = timeGetTime();
    BitBlt(mdc, 0, 0, 133, 35, sdc, 0, 0, SRCCOPY);   /* what Sound Recorder painted */
    tc = timeGetTime() - t0;
    GetObject(src, sizeof bm, &bm);
    sbytes = (long)bm.bmWidthBytes * bm.bmHeight * bm.bmPlanes;
    { BITMAP b2; GetObject(dst, sizeof b2, &b2); dbytes = (long)b2.bmWidthBytes * b2.bmHeight * b2.bmPlanes; }
    sb = (BYTE __huge *)GlobalLock(GlobalAlloc(GMEM_MOVEABLE, sbytes)); db = (BYTE __huge *)GlobalLock(GlobalAlloc(GMEM_MOVEABLE, dbytes));
    SelectObject(mdc, os);
    GetBitmapBits(src, sbytes, (LPSTR)sb);
    t0 = timeGetTime();
    if ((bm.bmBitsPixel == 8 || bm.bmBitsPixel == 16) && bm.bmPlanes == 1) for (i = 0; i < n; i++) {
        long dw = dbytes / S2; int px = bm.bmBitsPixel / 8;
        for (y = 0; y < S2; y++) {   /* inverse map: the source pixel under each destination pixel, nearest neighbour */
            long dy = y - S2 / 2, ax = (-(long)(S2 / 2)) * c + dy * s, ay = -(-(long)(S2 / 2)) * s + dy * c;   /* (incremental along the row) */
            BYTE __huge *o = db + y * dw;
            for (x = 0; x < S2; x++, ax += c, ay -= s) {
                int sx = (int)(ax / 16384) + 66, sy = (int)(ay / 16384) + 17;
                if (sx >= 0 && sx < 133 && sy >= 0 && sy < 35) {
                    BYTE __huge *q = sb + (long)sy * bm.bmWidthBytes + (long)sx * px;
                    o[x * px] = q[0]; if (px == 2) o[x * px + 1] = q[1];
                } else { o[x * px] = 0; if (px == 2) o[x * px + 1] = 0; }
            }
        }
    }
    t0 = timeGetTime() - t0;
    SetBitmapBits(dst, dbytes, (LPSTR)db);
    { HDC wdc = GetDC(hMain); BitBlt(wdc, 600, 40, S2, S2, odc, 0, 0, SRCCOPY); ReleaseDC(hMain, wdc); }
    say("rotbench bpp %d planes %d: capture %ld ms, %d rotations of %dx%d in %ld ms (%ld.%ld ms each)", bm.bmBitsPixel, bm.bmPlanes,
        (long)tc, n, S2, S2, (long)t0, n ? (long)(t0 / n) : 0L, n ? (long)(t0 * 10 / n % 10) : 0L);
    SelectObject(odc, od); DeleteDC(mdc); DeleteDC(odc); ReleaseDC(wv, sdc); DeleteObject(src); DeleteObject(dst);
    GlobalFree(GlobalHandle(SELECTOROF(sb))); GlobalFree(GlobalHandle(SELECTOROF(db)));
}

/* ---------------------------------------------------------------- ends, idle, the status line */
static void watch_ends(void)
{
    static DWORD last; int r;
    stops_due();
    if (timeGetTime() - last < 25) return;
    last = timeGetTime();
    for (r = 0; r < NALL; r++) if (rplay[r] && !is_playing(r)) { rplay[r] = FALSE; say("@%d end %d", r / NR, r % NR); }
}
static DWORD uiMax, uiSlow;   /* the longest idle drawing, ms; how often it took over 10 ms */
static void idle_ui2(void);
static void idle_ui(void)
{
    DWORD t0 = timeGetTime(), d;
    idle_ui2();
    d = timeGetTime() - t0;
    if (d > uiMax) uiMax = d;
    if (d > 10) uiSlow++;
}
static void idle_ui2(void)   /* when Windows has nothing else to do: waveforms, the track view, the status line */
{
    static DWORD lastWave, lastGrid, lastStat; static int next; DWORD t = timeGetTime(); int k;
    if (!assembled) return;
    if (t - lastWave > 60) {   /* one lane's waveform at a time */
        lastWave = t;
        for (k = 0; k < NB; k++) { int j = (next + k) % NB; if (peaks_read(j) || lnPkDirty[j]) { lnPkDirty[j] = FALSE; InvalidateRect(hWave[j], NULL, FALSE); UpdateWindow(hWave[j]); next = j + 1; break; } }
    }
    if (t - lastGrid >= 50) { lastGrid = t; grid_tick(); }
    if (t - lastStat > 1000) {
        char s[160]; int n = 0;
        lastStat = t;
        hide_srvr();
        for (k = 0; k < NB; k++) n += nLaneRecs[k];
        wsprintf(s, "%d lanes, %d Sound Recorders. Free resources: user %d%%, gdi %d%%. Free memory %ld KB.", NB, n,
                 GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES), GetFreeSpace(0) / 1024);
        SetWindowText(hStatus, s);
    }
}

/* ---------------------------------------------------------------- the host's lines */
/* A lane's sound is built one recorder at a time, and notes are served in between (poll_host); a line that would
   change a lane's sound or settings meanwhile waits here, in order, and goes after the build */
#define NPEND 40
static char __far pendLine[NPEND][1100]; static int pendN;
static BOOL deferred(const char *s)
{
    const char *c = s;
    if (*c == '@') { c = strchr(c, ' '); if (!c) return FALSE; c++; }
    return !strncmp(c, "dna ", 4);   /* (the rest touch only their own lane's tables, the card or the strip: at once) */
}
static void host_line(char *s);
static void run_pending(void)
{
    static char ln[1100];
    while (pendN && !building) {
        int i;
        _fstrcpy(ln, pendLine[0]);
        for (i = 1; i < pendN; i++) _fstrcpy(pendLine[i - 1], pendLine[i]);
        pendN--;
        host_line(ln);
    }
}
static void host_line(char *s)
{
    char *a, *rest;
    if (building && deferred(s)) { if (pendN < NPEND) _fstrcpy(pendLine[pendN++], s); return; }
    if (s[0] == '@') {   /* a lane's line */
        int ln = atoi(s + 1); char *sp = strchr(s, ' ');
        if (ln < 0 || ln >= NB || !sp) return;
        bank = ln; s = sp + 1;
    } else bank = 0;
    laneRecs = lnCap[bank] ? lnCap[bank] : LANE_RECS;   /* the lane's own recorder count (cap) */
    a = strchr(s, ' '); rest = a ? a + 1 : "";
    if (a) *a = 0;
    if (!strcmp(s, "hi")) say("hi 3 311 %s win,desk,rate,loop,tape,lanes=%d,recs=%d", assembled ? "ready" : "wait", NB, LANE_RECS);
    else if (!strcmp(s, "go")) { if (!assembled && !assembling) assemble(); else say("ready"); }
    else if (!strcmp(s, "dna")) build(rest);
    else if (!strcmp(s, "cap")) { int c = atoi(rest); lnCap[bank] = c >= 1 && c <= LANE_RECS ? c : 0; laneRecs = lnCap[bank] ? lnCap[bank] : LANE_RECS; }
    else if (!strcmp(s, "on")) {
        long f[8] = {0, 0, 65535, 0, 0, -1, 0, 0}; int nf = 0; char *p = rest;
        while (*p && nf < 8) { f[nf++] = atol(p); p = strchr(p, ' '); if (!p) break; p++; }
        if (f[0] >= 0 && f[0] < laneRecs) { play_rec((int)f[0], curId, (DWORD)f[1], (WORD)f[2], (int)f[3], (int)f[5], f[6]); }
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
    else if (!strcmp(s, "note")) { int n = 60, v = 100; sscanf(rest, "%d %d", &n, &v); grid_note(bank, n, v); }   /* the host: a note-on, for the track view */
    else if (!strcmp(s, "name")) {   /* the lane's preset, as the strip shows it */
        lstrcpyn(lnName[bank], rest, sizeof lnName[0]);
        lnNamed[bank] = rest[0] != 0;
        { char *c; for (c = lnName[bank]; *c; c++) if (*c == '_') *c = ' '; }
        if (hName[bank]) SetWindowText(hName[bank], lnName[bank]);
        if (hGrid) InvalidateRect(hGrid, NULL, FALSE);
    }
    else if (!strcmp(s, "mix")) {   /* mix <level> <pan> <mute> <solo>: the host's values */
        sscanf(rest, "%d %d %d %d", &lnLevel[bank], &lnPan[bank], &lnMute[bank], &lnSolo[bank]);
        if (hLev[bank]) mix_show(bank);
    }
    else if (!strcmp(s, "chan")) { char t[16]; lnChan[bank] = atoi(rest); wsprintf(t, "Ch %d", lnChan[bank]); if (hCh[bank]) SetWindowText(hCh[bank], t); }
    else if (!strcmp(s, "who")) {   /* who <x> <y>: the window under a screen point (a test aid) */
        POINT pt; HWND w; char cls[32], txt[32], pc[32];
        pt.x = atoi(rest); pt.y = atoi(strchr(rest, ' ') ? strchr(rest, ' ') + 1 : "0");
        w = WindowFromPoint(pt); cls[0] = txt[0] = pc[0] = 0;
        if (w) { GetClassName(w, cls, sizeof cls); GetWindowText(w, txt, sizeof txt); if (GetParent(w)) GetClassName(GetParent(w), pc, sizeof pc); }
        say("who %d %d %04x %s id %d '%s' parent %04x %s task %04x", pt.x, pt.y, (WORD)w, (LPSTR)cls, w ? GetDlgCtrlID(w) : 0, (LPSTR)txt, w ? (WORD)GetParent(w) : 0, (LPSTR)pc, w ? (WORD)GetWindowTask(w) : 0);
    }
    else if (!strcmp(s, "sb")) { int k = atoi(rest), lo, hi; GetScrollRange(hPan[k], SB_CTL, &lo, &hi); say("sb %d pan %d..%d pos %d en %d style %08lx", k, lo, hi, GetScrollPos(hPan[k], SB_CTL), IsWindowEnabled(hPan[k]), GetWindowLong(hPan[k], GWL_STYLE)); }
    else if (!strcmp(s, "dbg")) { DWORD v = bs_voices(); WORD dacl, dach; DWORD hi, lo = bs_dacnow_lo(&hi); say("dbg voices %08lx dac %lu playing0 %d", v, lo, is_playing(0));
        { WORD w[9]; int i; _disable(); bs_put(0); outpw(BS_CMD, 37); for (i = 0; i < 9; i++) w[i] = bs_get(); _enable();
          say("dbg v0 srate %u rate %u arm %u master %u pos %u q %u paused %u mod %u frames %u", w[0], w[1], w[2], w[3], w[4], w[5], w[6], w[7], w[8]); } }
    else if (!strcmp(s, "packs")) lib_packs(rest);
    else if (!strcmp(s, "panic")) { int r; for (r = 0; r < NALL; r++) stop_rec(r, 0, 5); }
    else if (!strcmp(s, "rotbench")) { int k = 0, d = 450, n = 10; sscanf(rest, "%d %d %d", &k, &d, &n); rotbench(k, d, n); }
    else if (!strcmp(s, "stats")) {
        int n = 0, k; for (k = 0; k < NB; k++) n += nLaneRecs[k];
        say("stats recorders %d plays %ld slowmax %ld uimax %ld uislow %ld user %d gdi %d free %ld anim %ld ms %ld frames", n, (long)nPlays, (long)slowMax, (long)uiMax, (long)uiSlow,
            GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES), GetFreeSpace(0) / 1024, (long)animMs, (long)animFrames);
        slowMax = 0;
    }
}
/* the host's pointer: BSYNTH.DRV moves it at interrupt time (BsPointer), as in SYNTH.EXE (its periodic timer also keeps
   the multimedia timer running across the snapshot) */
static void pointer_feed(void)
{
    BOOL (FAR PASCAL *f)(BOOL, WORD, WORD); HMODULE m = GetModuleHandle("BSYNTH");
    f = m ? (BOOL (FAR PASCAL *)(BOOL, WORD, WORD))GetProcAddress(m, "BSPOINTER") : NULL;
    logf_("pointer feed %s", f && f(TRUE, (WORD)GetSystemMetrics(SM_CXSCREEN), (WORD)GetSystemMetrics(SM_CYSCREEN)) ? "on" : "missing");
}
static int poll_host(void)
{
    static WORD e[140];
    static char acc[1200]; static int accn;
    int n, k, handled = 0;
    while ((n = bs_event(e, 140)) > 0) {
        int ty = e[0] >> 8;
        if (ty == 6 && n >= 3) { SetCursorPos(e[1], e[2]); handled++; continue; }   /* the host's pointer (until the feed runs) */
        if (ty == 4 || ty == 8) {
            for (k = 3; k < n && accn < (int)sizeof acc - 2; k++) { acc[accn++] = (char)(e[k] & 0xFF); acc[accn++] = (char)(e[k] >> 8); }
            if (ty == 4) { acc[accn] = 0; accn = 0; curId = MAKELONG(e[1], e[2]); host_line(acc); }
        }
        handled++;
    }
    watch_ends();
    return handled;
}

/* ================================================================ the window */
static void scroll_lane(HWND sb, int code, int pos)
{
    int id = GetDlgCtrlID(sb), k, lev = id >= ID_LEV && id < ID_LEV + NB, v, lo = 0, hi = 127;
    k = lev ? id - ID_LEV : id - ID_PAN;
    if (k < 0 || k >= NB) return;
    v = GetScrollPos(sb, SB_CTL);
    switch (code) {
    case SB_LINEUP: v--; break; case SB_LINEDOWN: v++; break; case SB_PAGEUP: v -= 8; break; case SB_PAGEDOWN: v += 8; break;
    case SB_THUMBTRACK: case SB_THUMBPOSITION: v = pos; break; case SB_TOP: v = lo; break; case SB_BOTTOM: v = hi; break;
    default: return;
    }
    if (v < lo) v = lo; if (v > hi) v = hi;
    if (lev) lnLevel[k] = 127 - v; else lnPan[k] = v - 64;
    mix_show(k); mix_send(k);
}
long FAR PASCAL __export MainProc(HWND h, UINT m, WPARAM w, LPARAM l)
{
    if (m == WM_PAINT) {
        PAINTSTRUCT ps; HDC dc = BeginPaint(h, &ps); HFONT of = hSmall ? SelectObject(dc, hSmall) : NULL;
        SetBkMode(dc, TRANSPARENT);
        TextOut(dc, 12, 8, " SNDWAVE2000 Ensemble", 21);
        if (assembled) TextOut(dc, GRIDX, GRIDY - 18, " Track view", 11);
        if (of) SelectObject(dc, of);
        EndPaint(h, &ps); return 0;
    }
    if (m == WM_VSCROLL || m == WM_HSCROLL) { scroll_lane((HWND)HIWORD(l), (int)w, (int)LOWORD(l)); return 0; }
    if (m == WM_COMMAND) {
        int id = (int)w;
        if (id >= ID_PREV && id < ID_PREV + NB) say("pick %d -1", id - ID_PREV);
        else if (id >= ID_NEXT && id < ID_NEXT + NB) say("pick %d 1", id - ID_NEXT);
        else if (id >= ID_CH && id < ID_CH + NB) say("audition %d", id - ID_CH);
        else if (id >= ID_MUTE && id < ID_MUTE + NB) { int k = id - ID_MUTE; lnMute[k] = (int)SendMessage(hMute[k], BM_GETCHECK, 0, 0L); mix_send(k); }
        else if (id >= ID_SOLO && id < ID_SOLO + NB) { int k = id - ID_SOLO; lnSolo[k] = (int)SendMessage(hSolo[k], BM_GETCHECK, 0, 0L); mix_send(k); }
        return 0;
    }
    return DefWindowProc(h, m, w, l);
}
int PASCAL WinMain(HINSTANCE hi, HINSTANCE hp, LPSTR cmd, int show)
{
    WNDCLASS wc; HINSTANCE hk; int k;
    hInst = hi;
    for (k = 0; k < NB; k++) { lnRel[k] = 120; lnLevel[k] = 100; lnPan[k] = 0; lnChan[k] = k + 1; lstrcpy(lnName[k], "(empty)"); lnPos[k] = -1; }
    if (!bs_present()) return 1;
    hk = LoadLibrary("C:\\BS\\SYNHOOK.DLL");
    if ((UINT)hk < 32) { logf_("no SYNHOOK.DLL"); return 1; }
    HookActive = (void (FAR PASCAL *)(BOOL))GetProcAddress(hk, "HOOKACTIVE");
    HookPending = (void (FAR PASCAL *)(LPCSTR))GetProcAddress(hk, "HOOKPENDING");
    ((BOOL (FAR PASCAL *)(BOOL))GetProcAddress(hk, "HOOKINSTALL"))(TRUE);
    hk = LoadLibrary("C:\\BS\\MTHOOK.DLL");
    if ((UINT)hk >= 32) msgStrip = ((UINT (FAR PASCAL *)(void))GetProcAddress(hk, "MTINSTALL"))();
    hSmall = CreateFont(-11, 0, 0, 0, FW_NORMAL, 0, 0, 0, ANSI_CHARSET, 0, 0, 0, VARIABLE_PITCH | FF_SWISS, "MS Sans Serif");
    hBlack = (HBRUSH)GetStockObject(BLACK_BRUSH);
    hGreen = CreatePen(PS_SOLID, 1, RGB(0, 255, 0)); hGrey = CreatePen(PS_SOLID, 1, RGB(0, 96, 0)); hYellow = CreatePen(PS_SOLID, 1, RGB(255, 255, 0));
    memset(&wc, 0, sizeof wc);
    wc.lpfnWndProc = MainProc; wc.hInstance = hi; wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1); wc.lpszClassName = "EnsMain";
    wc.hIcon = ExtractIcon(hi, "C:\\WINDOWS\\SOUNDREC.EXE", 0);
    RegisterClass(&wc);
    wc.lpfnWndProc = WaveProc; wc.lpszClassName = "EnsWave"; wc.cbWndExtra = 2; wc.hbrBackground = NULL; wc.hIcon = NULL; RegisterClass(&wc);
    wc.lpfnWndProc = GridProc; wc.lpszClassName = "EnsGrid"; wc.cbWndExtra = 0; RegisterClass(&wc);
    hMain = CreateWindow("EnsMain", "SNDWAVE2000 Ensemble", WS_POPUP | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_CLIPCHILDREN | WS_VISIBLE,
                         0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN), NULL, NULL, hi, NULL);
    { HWND pm = FindWindow("Progman", NULL); if (pm) ShowWindow(pm, SW_MINIMIZE); }
    for (k = 0; k < NB; k++) ensure_recs(k, 1);   /* each lane's first recorder; the rest come with the lane's sound */
    strips_create();
    pointer_feed();
    logf_("ENSEMBLE up: %d lanes, %d recorders, free resources: user %d%% gdi %d%%", NB, recsUp, GetFreeSystemResources(GFSR_USERRESOURCES), GetFreeSystemResources(GFSR_GDIRESOURCES));
    /* (the snapshot waits 1.5 s: taken at once after the timers start, a resumed machine never returned a played buffer) */
    { DWORD tw = timeGetTime(); while (timeGetTime() - tw < 1500UL) { pump(); poll_host(); bs_idle(); } }
    { WORD z = 0; bs_report(2, &z, 0); }   /* idle: the machine may be frozen here (the snapshot); `go` assembles */
    for (;;) {
        MSG m;
        if (PeekMessage(&m, 0, 0, 0, PM_REMOVE)) { if (m.message == WM_QUIT) break; TranslateMessage(&m); DispatchMessage(&m); }
        else if (!poll_host()) { idle_ui(); bs_idle(); }
    }
    return 0;
}
