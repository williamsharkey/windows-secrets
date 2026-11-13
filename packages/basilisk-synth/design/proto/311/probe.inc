/* PRESET ENGINE 2 measurement probe for the 3.11 edition: included into a PRIVATE copy of guest/synth.c (answers "pr ..." host lines). Used for T1, set-rate, T6, T8 and the effects questions (spec section 12). Not part of the product. */
static HWND launch(const char *cmd, int show);
static DWORD dacnow(void)
{
    WORD a, b, c, d;
    _disable(); outpw(BS_CMD, BSC_DACNOW); a = bs_get(); b = bs_get(); c = bs_get(); d = bs_get(); _enable();
    (void)c; (void)d;
    return MAKELONG(a, b);
}
static void pr_state(int r, const char *tag)
{
    char p[24], L[24]; int lo, hi; HWND sb = GetDlgItem(rw[r], SR_SCROLL);
    GetScrollRange(sb, SB_CTL, &lo, &hi);
    GetDlgItemText(rw[r], SR_POS, p, sizeof p); GetDlgItemText(rw[r], SR_LEN, L, sizeof L);
    say("pr %s %d lo %d hi %d pos %d P %s L %s", tag, r, lo, hi, GetScrollPos(sb, SB_CTL), p, L);
}
static void pr_seek(int r, int pos)
{
    HWND sb = GetDlgItem(rw[r], SR_SCROLL);
    SendMessage(rw[r], WM_HSCROLL, SB_THUMBPOSITION, MAKELPARAM(pos, sb));
    SendMessage(rw[r], WM_HSCROLL, SB_ENDSCROLL, MAKELPARAM(pos, sb));
}
static HWND hMine;
static void pr_hexdump(WORD sel, WORD off, WORD len)
{
    static char b[260]; static const char hx[] = "0123456789ABCDEF";
    BYTE FAR *p = (BYTE FAR *)MAKELP(sel, 0);
    WORD i, k;
    for (i = 0; i < len; i += 100) {
        int n = len - i > 100 ? 100 : len - i; char *o = b;
        o += sprintf(o, "pr hx %u ", off + i);
        for (k = 0; k < (WORD)n; k++) { BYTE x = p[off + i + k]; *o++ = hx[x >> 4]; *o++ = hx[x & 15]; }
        *o = 0; bs_line(b);
    }
}
static void probe(char *rest)
{
    char cmd[16]; int a = 0, b = 0, c = 0, d = 0; long la = 0, lb = 0; char path[128];
    path[0] = 0; cmd[0] = 0;
    sscanf(rest, "%15s", cmd);
    rest = strchr(rest, ' '); rest = rest ? rest + 1 : "";
    if (!strcmp(cmd, "load")) {          /* load r path */
        sscanf(rest, "%d %127s", &a, path);
        bs_arm(rt[a], 0, 0, 0);
        HookActive(TRUE);
        drop_file(a, path);
        { DWORD t = timeGetTime(); while (timeGetTime() - t < 600) { pump(); if (is_playing(a)) { bs_armstop(rt[a], 0, 1); press(a, SR_STOP); break; } } }
        press(a, SR_REW); pump(); HookActive(FALSE);
        pr_state(a, "load");
    } else if (!strcmp(cmd, "state")) { sscanf(rest, "%d", &a); pr_state(a, "state"); }
    else if (!strcmp(cmd, "menu")) {     /* menu r id */
        sscanf(rest, "%d %d", &a, &b); HookActive(TRUE); menu(a, b); HookActive(FALSE); pump(); pr_state(a, "menu");
    } else if (!strcmp(cmd, "mixfile")) {   /* mixfile r path */
        sscanf(rest, "%d %127s", &a, path); HookActive(TRUE); HookPending(path); menu(a, SR_MIX); HookActive(FALSE); pump(); pr_state(a, "mixfile");
    } else if (!strcmp(cmd, "seek")) { sscanf(rest, "%d %d", &a, &b); pr_seek(a, b); pump(); pr_state(a, "seek"); }
    else if (!strcmp(cmd, "press")) { sscanf(rest, "%d %d", &a, &b); press(a, b); pump(); pr_state(a, "press"); }
    else if (!strcmp(cmd, "splay")) {    /* splay r pos hz [rew]: stop, seek (or rewind), arm with this line's id, Play */
        DWORD d0, d1, d2, t0, t1; int rew = 0;
        sscanf(rest, "%d %d %ld %d", &a, &b, &la, &rew);
        if (rplay[a] || is_playing(a)) { bs_armstop(rt[a], 0, 1); press(a, SR_STOP); }
        if (rew) press(a, SR_REW); else pr_seek(a, b);
        d0 = dacnow(); t0 = timeGetTime();
        bs_arm2(rt[a], curId, (DWORD)la, 65535, 0, -1);
        d1 = dacnow();
        press(a, SR_PLAY);
        d2 = dacnow(); t1 = timeGetTime();
        rplay[a] = TRUE;
        { char p[24]; HWND sb = GetDlgItem(rw[a], SR_SCROLL); GetDlgItemText(rw[a], SR_POS, p, sizeof p);
          say("pr splay %d want %d got %d P %s d0 %lu d1 %lu d2 %lu ms %lu", a, b, GetScrollPos(sb, SB_CTL), p, d0, d1, d2, t1 - t0); }
    } else if (!strcmp(cmd, "voices")) {
        DWORD m = bs_voices(); say("pr voices %lx d %lu", m, dacnow());
    } else if (!strcmp(cmd, "rate")) {   /* rate ch val16.16 */
        DWORD d0;
        sscanf(rest, "%d %ld", &a, &la);
        _disable(); d0 = dacnow(); bs_put((WORD)a); bs_put(LOWORD(la)); bs_put(HIWORD(la)); outpw(BS_CMD, BSC_SETRATE); _enable();
        say("pr rate %d %ld at %lu", a, la, d0);
    } else if (!strcmp(cmd, "glide")) {  /* glide ch from to nsteps step_ms: 16.16 rates, geometric */
        DWORD t0, d0; int k; double f, q;
        sscanf(rest, "%d %ld %ld %d %d", &a, &la, &lb, &b, &c);
        t0 = timeGetTime(); d0 = dacnow();
        q = (double)lb / (double)la;
        for (k = 0; k <= b; k++) {
            DWORD v;
            while (timeGetTime() - t0 < (DWORD)(k * c)) { }
            f = (double)la; { int j; double s = 1.0, r1 = 1.0; for (j = 0; j < 40; j++) {} (void)s; (void)r1; }
            v = (DWORD)(la * exp(log(q) * k / b));
            _disable(); bs_put((WORD)a); bs_put(LOWORD(v)); bs_put(HIWORD(v)); outpw(BS_CMD, BSC_SETRATE); _enable();
            if (k == 0 || k == b) say("pr glide step %d rate %lu dac %lu", k, v, dacnow());
        }
        say("pr glide done d0 %lu d1 %lu", d0, dacnow());
    } else if (!strcmp(cmd, "burst")) {  /* burst r0 nrec n hz: n plays round-robin over recorders r0.., as fast as possible */
        static WORD ms[400]; static DWORD dd[400]; int k; DWORD t0, t1, ta;
        sscanf(rest, "%d %d %d %ld", &a, &b, &c, &la);
        if (c > 400) c = 400;
        ta = timeGetTime();
        for (k = 0; k < c; k++) {
            int r = a + k % b;
            t0 = timeGetTime();
            if (rplay[r] || is_playing(r)) { bs_armstop(rt[r], 0, 2); press(r, SR_STOP); }
            press(r, SR_REW);
            bs_arm2(rt[r], 0, (DWORD)la, 65535, 0, -1);
            dd[k] = dacnow();
            press(r, SR_PLAY);
            t1 = timeGetTime();
            rplay[r] = TRUE;
            ms[k] = (WORD)(t1 - t0);
            pump();
        }
        t1 = timeGetTime();
        say("pr burst total %lu ms n %d", t1 - ta, c);
        { static char bb[260]; char *o; int j;
          for (k = 0; k < c; k += 20) { o = bb; o += sprintf(o, "pr bms %d", k); for (j = k; j < c && j < k + 20; j++) o += sprintf(o, " %u:%lu", ms[j], dd[j]); bs_line(bb); } }
    } else if (!strcmp(cmd, "tburst")) {  /* tburst r0 nrec n hz T_ms: a play every T ms (by the DAC), round-robin */
        static DWORD d0s[400]; static WORD pd[400]; int k; DWORD ta;
        sscanf(rest, "%d %d %d %ld %d", &a, &b, &c, &la, &d);
        if (c > 400) c = 400;
        ta = dacnow();
        for (k = 0; k < c; k++) {
            int r = a + k % b; DWORD d0, d1;
            while (dacnow() - ta < (DWORD)k * d * 48) pump();
            d0 = dacnow();
            if (rplay[r] || is_playing(r)) { bs_armstop(rt[r], 0, 2); press(r, SR_STOP); }
            press(r, SR_REW);
            bs_arm2(rt[r], 0, (DWORD)la, 65535, 0, -1);
            press(r, SR_PLAY);
            d1 = dacnow();
            rplay[r] = TRUE;
            d0s[k] = d0; pd[k] = (WORD)(d1 - d0);
        }
        say("pr tburst total %lu ms n %d", (dacnow() - ta) / 48, c);
        { static char bb[260]; char *o; int j;
          for (k = 0; k < c; k += 16) { o = bb; o += sprintf(o, "pr tb %d", k); for (j = k; j < c && j < k + 16; j++) o += sprintf(o, " %lu:%u", d0s[j], pd[j]); bs_line(bb); } }
    } else if (!strcmp(cmd, "stopall")) { int r; for (r = 0; r < NR; r++) stop_rec(r, 0, 2); say("pr stopall"); }
    /* ---- Minesweeper */
    else if (!strcmp(cmd, "mine")) {
        char sub[16]; sub[0] = 0; sscanf(rest, "%15s %d %d %d", sub, &a, &b, &c);
        if (!strcmp(sub, "start")) {
            hMine = launch("WINMINE.EXE", SW_SHOWNORMAL);
            if (hMine) { char cls[40]; RECT rc; GetClassName(hMine, cls, sizeof cls); GetClientRect(hMine, &rc);
                say("pr mine hwnd %04x inst %04x class %s client %d %d", (WORD)hMine, GetWindowWord(hMine, GWW_HINSTANCE), cls, rc.right, rc.bottom); }
            else say("pr mine failed");
        } else if (!strcmp(sub, "seg")) {
            WORD sel = GetWindowWord(hMine, GWW_HINSTANCE); DWORD gh = GlobalHandle(sel); DWORD sz = GlobalSize((HGLOBAL)LOWORD(gh));
            RECT rc; GetClientRect(hMine, &rc);
            say("pr mine seg %04x handle %08lx size %lu client %d %d", sel, gh, sz, rc.right, rc.bottom);
        } else if (!strcmp(sub, "dump")) {   /* dump off len */
            pr_hexdump(GetWindowWord(hMine, GWW_HINSTANCE), (WORD)a, (WORD)b); say("pr mine dumped");
        } else if (!strcmp(sub, "cmd")) { SendMessage(hMine, WM_COMMAND, a, 0L); pump(); say("pr mine cmd %d", a); }
        else if (!strcmp(sub, "click")) {   /* click x y btn(0 left, 1 right) */
            UINT dn = c ? WM_RBUTTONDOWN : WM_LBUTTONDOWN, up = c ? WM_RBUTTONUP : WM_LBUTTONUP;
            { POINT pt; pt.x = a; pt.y = b; ClientToScreen(hMine, &pt); SetCursorPos(pt.x, pt.y); }
            SendMessage(hMine, WM_MOUSEMOVE, 0, MAKELPARAM(a, b));
            PostMessage(hMine, dn, c ? MK_RBUTTON : MK_LBUTTON, MAKELPARAM(a, b)); pump();
            PostMessage(hMine, up, 0, MAKELPARAM(a, b)); pump();
            say("pr mine click %d %d %d", a, b, c);
        } else if (!strcmp(sub, "c2s")) { POINT pt; pt.x = 0; pt.y = 0; ClientToScreen(hMine, &pt); say("pr mine c2s %d %d", pt.x, pt.y);
        } else if (!strcmp(sub, "shot")) { ShowWindow(hMine, SW_SHOWNORMAL); SetWindowPos(hMine, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE); UpdateWindow(hMine); say("pr mine shown"); }
    }
    else say("pr ? %s", cmd);
}
