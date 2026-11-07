/* scene_v2.h - BASILISK V2: the prophecy is typed by hand into a blank Notepad,
   in Japanese, faster and faster; DEBUG.EXE "compiles" it (choking on every line
   of prophecy until it reaches the tail, which is real 8086 assembly); the
   result, basilisk.com, lands on the desktop where a human hand finds it.
   Needs MS Gothic installed in the guest and C:\p\basilisk.txt (UTF-8). */

static void v2_addfont(void)
{
    int n = AddFontResourceA("C:\\WINDOWS\\Fonts\\msgothic.ttc");
    DWORD_PTR r;
    SendMessageTimeoutA(HWND_BROADCAST, WM_FONTCHANGE, 0, 0, SMTO_ABORTIFHUNG, 2000, &r);
    say("addfont msgothic -> %d", n);
}

/* hand-typed: the delay for every character comes from where it sits in the text */
static double v2_speed = 1.0;   /* "v2 fast" rehearses at 20x */
static void v2_type(HWND edit, const WCHAR *w, int n, int a_end, int b_end)
{
    double due = GetTickCount();
    int i, last_line = n, first_nl = 0;
    while (first_nl < n && w[first_nl] != L'\n') first_nl++;
    for (i = n - 2; i > 0; i--) if (w[i] == L'\n') { last_line = i + 1; break; }
    for (i = 0; i < n; i++) {
        WCHAR c = w[i];
        double d, f, jit = 0.6 + (rand() % 80) / 100.0;
        LONG now;
        if (c == L'\r') continue;
        if (i < first_nl) {                      /* the ===== rule: rattled off */
            d = 6;
        } else if (i < a_end) {                  /* the prophecy: a brisk pace that runs away */
            f = (double)i / a_end;
            d = 2 + 42 * exp(-5.2 * f);
            if (c == L'\n') d *= 4;
            else if (c == L'、' || c == L'。') d *= 3;
        } else if (i < b_end) {                  /* the tail: the machine's own tongue */
            d = (c == L'\n') ? 20 : 4;
        } else if (i < last_line) {              /* the blessing: slowing back down */
            f = (double)(i - b_end) / (last_line - b_end);
            d = 12 + 80 * f * f;
            if (c == L'\n') d *= 5;
            else if (c == L'、' || c == L'。') d *= 3;
        } else {                                 /* おはよう、蛇。 */
            d = 200;
            if (i == last_line) d = 900;
            if (c == L'、') d = 450;
        }
        due += d * jit * v2_speed;
        PostMessageW(edit, WM_CHAR, c == L'\n' ? L'\r' : c, 0);
        now = (LONG)(due - GetTickCount());
        if (now > 0) play(now);
    }
}

/* type into the focused window with real keystrokes (consoles want these) */
static void v2_keys(const char *s, int ms)
{
    for (; *s; s++) {
        SHORT vk = VkKeyScanA(*s);
        int sh = (vk >> 8) & 1;
        if (*s == '\n') vk = VK_RETURN, sh = 0;
        if (sh) key(VK_SHIFT, 0);
        key((BYTE)vk, 0); key((BYTE)vk, 1);
        if (sh) key(VK_SHIFT, 1);
        play(*s == '\n' ? ms * 4 : ms / 2 + rand() % ms);
    }
}

/* a human hand: curved, a little overshoot, a little tremor */
static void human_glide(int x, int y, int ms)
{
    POINT p;
    DWORD t0 = GetTickCount(), t;
    double bx, by, nx, ny, len;
    GetCursorPos(&p);
    nx = -(y - p.y); ny = x - p.x;
    len = sqrt(nx * nx + ny * ny); if (len < 1) len = 1;
    bx = (p.x + x) / 2.0 + nx / len * (rand() % 120 - 60);
    by = (p.y + y) / 2.0 + ny / len * (rand() % 120 - 60);
    do {
        double f, e, u, cx, cy;
        t = GetTickCount() - t0;
        f = ms ? (double)t / ms : 1;
        if (f > 1) f = 1;
        e = 1 - pow(1 - f, 2.4);                       /* fast start, careful landing */
        e += 0.04 * sin(f * 3.14159) * (f > 0.7);      /* overshoot */
        u = 1 - e;
        cx = u * u * p.x + 2 * u * e * bx + e * e * x;
        cy = u * u * p.y + 2 * u * e * by + e * e * y;
        cx += 1.5 * sin(t / 37.0); cy += 1.2 * sin(t / 53.0);
        mouse_abs((int)cx, (int)cy, 0);
        play(12);
    } while (t < (DWORD)ms);
    mouse_abs(x, y, 0);
}

/* where an icon really is (XP snaps them to its own grid): the centre of its
   icon rectangle, asked of explorer through memory allocated inside it */
static POINT v2_icon(int item)
{
    HWND lv = desk_lv();
    DWORD pid;
    HANDLE ph;
    RECT r, *rr;
    POINT p = {0, 0};
    SIZE_T done;
    GetWindowThreadProcessId(lv, &pid);
    ph = OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE, FALSE, pid);
    if (!ph) return p;
    rr = (RECT *)VirtualAllocEx(ph, NULL, sizeof r, MEM_COMMIT, PAGE_READWRITE);
    r.left = LVIR_ICON;
    WriteProcessMemory(ph, rr, &r, sizeof r, &done);
    SendMessageA(lv, LVM_GETITEMRECT, item, (LPARAM)rr);
    ReadProcessMemory(ph, rr, &r, sizeof r, &done);
    VirtualFreeEx(ph, rr, 0, MEM_RELEASE);
    CloseHandle(ph);
    p.x = (r.left + r.right) / 2; p.y = (r.top + r.bottom) / 2;
    ClientToScreen(lv, &p);
    return p;
}

static void scene_v2(void)
{
    char names[64][64], *raw;
    int n, i, row = 0, np_row = -1, wn, a_end = 0, b_end = 0;
    WCHAR *w;
    HWND np, ed, d, con;
    POINT ip;

    v2_addfont();
    raw = readfile("C:\\p\\basilisk.txt");
    if (!raw) { say("no C:\\p\\basilisk.txt"); return; }
    wn = MultiByteToWideChar(CP_UTF8, 0, raw, -1, NULL, 0);
    w = calloc(wn + 1, sizeof(WCHAR));
    MultiByteToWideChar(CP_UTF8, 0, raw, -1, w, wn);
    wn = lstrlenW(w);
    if (w[0] == 0xFEFF) { memmove(w, w + 1, wn * sizeof(WCHAR)); wn--; }
    {   /* part boundaries: the assembly starts at "a 100", ends after the line "q" */
        WCHAR *a = wcsstr(w, L"\na 100"), *q = wcsstr(w, L"\nq\n");
        a_end = a ? (int)(a - w) + 1 : wn;
        b_end = q ? (int)(q - w) + 3 : wn;
    }
    say("v2 text %d chars, asm at %d, blessing at %d", wn, a_end, b_end);

    /* a tidy desktop column */
    n = desk_items(names, 64);
    for (i = 0; i < n; i++) {
        if (strstr(names[i], "Notepad")) np_row = i;
        desk_pos(i, 12, 10 + 76 * row++);
    }
    SetCursorPos(760, 560);
    play(3000);

    /* ---- someone opens Notepad ---- */
    if (np_row >= 0) {
        ip = v2_icon(np_row);
        glide(ip.x, ip.y, 1500, 0);
        play(500);
        say("notepad icon %ld,%ld", ip.x, ip.y);
        dblclick_at(ip.x, ip.y);
    } else launch("notepad.exe");
    np = wait_top("Notepad", NULL, 0, 8000);
    if (!np) return;
    place(np, 130, 16, 880, 700);
    foreground(np);
    play(900);
    glide(600, 400, 900, 0);
    {   /* the Font dialog, already on MS Gothic (set in the registry by v2-setup.bat:
           XP's dialog only maps it when the script is Japanese) */
        DWORD pid;
        HWND fd;
        GetWindowThreadProcessId(np, &pid);
        cmd(np, 33);
        fd = wait_top("#32770", "Font", pid, 4000);
        play(2600);
        if (fd) PostMessageA(kid_id(fd, IDOK), BM_CLICK, 0, 0);
        play(500);
    }
    ed = kid_cls(np, "Edit");
    SetFocus(ed);
    glide(980, 740, 1200, 0);                     /* out of the way */
    play(1200);
    say("typing");
    v2_type(ed, w, wn, a_end, b_end);
    say("typed");
    play(3500);

    /* ---- save it, as UTF-8 ---- */
    cmd(np, 4);                                   /* File > Save As... */
    {
        DWORD pid;
        GetWindowThreadProcessId(np, &pid);
        d = wait_top("#32770", "Save As", pid, 60000);
    }
    if (d) {
        HWND fn = kid_cls(kid_id(d, 1148), "Edit");
        HWND cbs[16];
        int k, nc = kids(d, "ComboBox", cbs, 16);
        if (!fn) fn = kid_id(d, 1152);
        play(900);
        settext(fn, "");
        type_into(fn, "\"C:\\basilisk\\basilisk.ja\"", 12);   /* quoted: no .txt */
        play(700);
        for (k = 0; k < nc; k++) {
            int ix = (int)SendMessageA(cbs[k], CB_FINDSTRINGEXACT, (WPARAM)-1, (LPARAM)"UTF-8");
            if (ix >= 0) {
                SendMessageA(cbs[k], CB_SETCURSEL, ix, 0);
                SendMessageA(GetParent(cbs[k]), WM_COMMAND, MAKEWPARAM(GetDlgCtrlID(cbs[k]), CBN_SELCHANGE), (LPARAM)cbs[k]);
                say("encoding combo %d -> UTF-8", GetDlgCtrlID(cbs[k]));
            }
        }
        play(1100);
        foreground(d);
        SendMessageA(kid_id(d, IDOK), BM_SETSTATE, 1, 0); play(140);
        SendMessageA(kid_id(d, IDOK), BM_SETSTATE, 0, 0);
        PostMessageA(d, WM_COMMAND, MAKEWPARAM(IDOK, BN_CLICKED), (LPARAM)kid_id(d, IDOK));
        for (k = 0; k < 60 && GetFileAttributesA("C:\\basilisk\\basilisk.ja") == INVALID_FILE_ATTRIBUTES; k++) play(100);
        play(1200);
    }
    say("saved: %lu", (unsigned long)GetFileAttributesA("C:\\basilisk\\basilisk.ja"));

    /* ---- the compiler: DEBUG.EXE, which has shipped with every Windows since DOS ---- */
    launch("cmd.exe /k mode con cols=80 lines=44 & title C:\\WINDOWS\\system32\\cmd.exe & cd /d C:\\basilisk");
    con = wait_top("ConsoleWindowClass", NULL, 0, 8000);
    play(800);
    if (!con) return;
    { RECT r = srect(con); SetWindowPos(con, HWND_TOP, 230, 50, 0, 0, SWP_NOSIZE); (void)r; }
    foreground(con);
    play(1500);
    v2_keys("dir /b\n", 140);
    play(1800);
    v2_keys("debug < basilisk.ja\n", 150);
    for (i = 0; i < 200 && GetFileAttributesA("C:\\basilisk\\basilisk.com") == INVALID_FILE_ATTRIBUTES; i++) play(100);
    play(3500);
    v2_keys("dir basilisk.com\n", 110);
    play(2500);
    v2_keys("copy basilisk.com \"%USERPROFILE%\\Desktop\"\n", 70);
    play(2500);
    v2_keys("exit\n", 160);
    play(1500);

    /* the source closes; only the program is left */
    PostMessageA(np, WM_CLOSE, 0, 0);
    play(1500);
    for (i = 0; i < 60 && desk_find("BASILISK") < 0; i++) play(100);
    i = desk_find("BASILISK");
    if (i < 0) { say("no basilisk.com on the desktop"); return; }
    desk_pos(i, 560, 330);
    play(300);
    ip = v2_icon(i);
    say("BASILISK.COM icon at %ld,%ld", ip.x, ip.y);
    play(4000);

    /* ---- a human hand, much later, looking for Minesweeper ---- */
    say("human");
    {
        int ms_row = -1, sol_row = -1;
        n = desk_items(names, 64);
        for (i = 0; i < n; i++) {
            if (strstr(names[i], "Minesweeper")) ms_row = i;
            if (strstr(names[i], "Solitaire")) sol_row = i;
        }
        human_glide(820, 610, 1300);
        play(900);
        human_glide(300, 450, 1700);
        play(600);
        if (sol_row >= 0) { POINT s = v2_icon(sol_row); human_glide(s.x + 6, s.y + 4, 1500); play(1600); }
        human_glide(ip.x + 160, ip.y - 90, 1400);   /* drifting, undecided */
        play(1400);
        human_glide(ip.x + 4, ip.y + 6, 1100);      /* hover: what is this? */
        play(3200);
        human_glide(ip.x + 70, ip.y + 70, 900);     /* no. Minesweeper... */
        play(700);
        if (ms_row >= 0) { POINT m = v2_icon(ms_row); human_glide(m.x + 60, m.y, 1300); }
        play(500);
        human_glide(ip.x - 4, ip.y + 14, 700);      /* ...the hand comes back anyway */
        play(350);
        dblclick_at(ip.x - 4, ip.y + 14);
    }
    say("v2 done");
    play(4000);
    free(w); free(raw);
}
