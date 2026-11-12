/* BASILISK III: the build. A blank Notepad, the source dropped in at once, saved to the
   desktop, compiled with tcc in a Command Prompt, started. No theatre beyond the work itself. */

static int b3_find(char names[][64], int n, const char *s)
{
    int i;
    for (i = 0; i < n; i++) if (strstr(names[i], s)) return i;
    return -1;
}

static void scene_b3(void)
{
    static const char *order[] = {"Notepad", "Command Prompt", "tcc", "Calculator", "Date and Time", "basilisk"};
    char names[64][64], *src, path[MAX_PATH];
    int n, i, k, row = 0, len;
    HWND np, ed, d, con;
    POINT ip;
    DWORD pid;

    {   /* the file has Unix line ends; XP's Notepad shows a bare LF as a box, so give it CRLF */
        char *raw = readfile("C:\\p\\basilisk3.c");
        if (!raw) { say("no C:\\p\\basilisk3.c"); return; }
        src = crlf(raw);
        free(raw);
    }
    len = (int)strlen(src);
    GetEnvironmentVariableA("USERPROFILE", path, sizeof path);
    strcat(path, "\\Desktop\\basilisk.c");
    DeleteFileA(path);

    /* the desktop: one tidy column, in the order the work uses them */
    n = desk_items(names, 64);
    for (k = 0; k < 6; k++) { i = b3_find(names, n, order[k]); if (i >= 0) desk_pos(i, 14, 8 + 74 * row++); }
    SetCursorPos(700, 520);
    play(700);

    /* a blank Notepad, from its icon */
    i = b3_find(names, n, "Notepad");
    if (i >= 0) {
        ip = v2_icon(i);
        human_glide(ip.x, ip.y, 520);
        play(120);
        dblclick_at(ip.x, ip.y);
    } else launch("notepad.exe");
    np = wait_top("Notepad", NULL, 0, 8000);
    if (!np) return;
    place(np, 128, 18, 760, 660);
    foreground(np);
    ed = kid_cls(np, "Edit");
    glide(940, 700, 300, 0);
    play(350);

    /* the source, dropped in: forty-odd kilobytes in a few seconds */
    say("dump %d bytes", len);
    {   /* small chunks, ~20 a second: each one scrolls the edit by a few lines, which Windows does by
           copying the pixels already there and drawing only the new lines (no whole-page repaints) */
        int chunks = 70, step = (len + chunks - 1) / chunks, at = 0;
        char *buf = (char *)malloc(step + 1);
        while (at < len) {
            int m = len - at < step ? len - at : step;
            memcpy(buf, src + at, m); buf[m] = 0;
            SendMessageA(ed, EM_SETSEL, 0x7fffffff, 0x7fffffff);
            SendMessageA(ed, EM_REPLACESEL, FALSE, (LPARAM)buf);
            SendMessageA(ed, EM_SCROLLCARET, 0, 0);
            UpdateWindow(ed);
            at += m;
            play(48);
        }
        free(buf);
    }
    say("dumped");
    play(500);

    /* File > Save As..., onto the desktop */
    cmd(np, 4);
    GetWindowThreadProcessId(np, &pid);
    d = wait_top("#32770", "Save As", pid, 20000);
    if (d) {
        HWND fn = kid_cls(kid_id(d, 1148), "Edit");
        char q[MAX_PATH + 4];
        if (!fn) fn = kid_id(d, 1152);
        play(250);
        sprintf(q, "\"%s\"", path);
        settext(fn, "");
        type_into(fn, q, 90);
        play(250);
        SendMessageA(kid_id(d, IDOK), BM_SETSTATE, 1, 0); play(110);
        SendMessageA(kid_id(d, IDOK), BM_SETSTATE, 0, 0);
        PostMessageA(d, WM_COMMAND, MAKEWPARAM(IDOK, BN_CLICKED), (LPARAM)kid_id(d, IDOK));
        for (k = 0; k < 80 && GetFileAttributesA(path) == INVALID_FILE_ATTRIBUTES; k++) play(60);
    }
    say("saved: %d", GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES);
    play(400);
    PostMessageA(np, WM_CLOSE, 0, 0);
    play(500);

    /* Command Prompt, from its icon: compile, start, leave */
    n = desk_items(names, 64);
    i = b3_find(names, n, "Command Prompt");
    if (i >= 0) {
        ip = v2_icon(i);
        human_glide(ip.x, ip.y, 480);
        play(100);
        dblclick_at(ip.x, ip.y);
    } else launch("cmd.exe");
    con = wait_top("ConsoleWindowClass", NULL, 0, 8000);
    if (!con) return;
    SetWindowPos(con, HWND_TOP, 200, 120, 0, 0, SWP_NOSIZE);
    foreground(con);
    glide(940, 700, 300, 0);
    play(500);
    v2_keys("cd Desktop\n", 28);
    play(250);
    v2_keys("C:\\tcc\\tcc.exe basilisk.c -luser32 -lgdi32 -Wl,-subsystem=windows\n", 22);
    path[strlen(path) - 1] = 0;
    strcat(path, "exe");
    for (k = 0; k < 150 && GetFileAttributesA(path) == INVALID_FILE_ATTRIBUTES; k++) play(60);
    say("compiled: %d", GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES);
    play(700);
    v2_keys("dir /b basilisk.*\n", 26);
    play(900);
    v2_keys("start basilisk.exe & exit\n", 26);   /* one line: no keystroke may land after it starts */
    for (k = 0; k < 100 && !FindWindowA("BasiliskIII", NULL); k++) play(60);
    SetCursorPos(1016, 600);        /* the pointer rests out of the way; the visitor types */
    say("b3 started");
    free(src);
}

/* the snapshot holds this, already running: it waits for Ctrl+Alt+Shift+F12, which only the host can
   press (through QMP; visitors' keys never include function keys), then builds. No network involved,
   so a restored snapshot starts building the instant the host asks. */
static void scene_b3wait(void)
{
    MSG m;
    if (!RegisterHotKey(NULL, 0xB3, MOD_CONTROL | MOD_ALT | MOD_SHIFT, VK_F12)) { say("hotkey taken"); return; }
    say("b3 waiting for the hotkey");
    while (GetMessageA(&m, NULL, 0, 0) > 0) {
        if (m.message == WM_HOTKEY && m.wParam == 0xB3) break;
    }
    UnregisterHotKey(NULL, 0xB3);
    say("hotkey: build");
    scene_b3();
}
