static void mark(const char *phase);   /* BASILISK LIVE: tell the host which act we are in */
/* scenes for puppet.c - see puppet.c for the engine */

/* ======================================================================= */
/* Paint                                                                    */
/* ======================================================================= */

static HWND paint_tools(HWND app) { return kid_id(app, 59415); }
static HWND paint_colors(HWND app) { return kid_id(app, 59416); }
static HWND paint_canvas(HWND app) { return kid_cls(kid_id(app, 59648), "Afx:1000000:8"); }

/* tool grid col 0/1, row 0..7 */
static POINT tool_pt(HWND app, int col, int row)
{
    RECT r = srect(paint_tools(app));
    POINT p;
    p.x = r.left + 16 + 25 * col; p.y = r.top + 18 + 25 * row;
    return p;
}
static void paint_tool(HWND app, int col, int row, int ms)
{
    POINT p = tool_pt(app, col, row);
    glide(p.x, p.y, ms, 0);
    click_at(p.x, p.y, 0);
    play(100);
}
static void paint_color(HWND app, int col, int row, int right, int ms)
{
    RECT r = srect(paint_colors(app));
    int x = r.left + 41 + 16 * col, y = r.top + 16 + 16 * row;
    glide(x, y, ms, 0);
    click_at(x, y, right);
    play(80);
}
/* the option box under the tools (brush sizes etc), offsets from the toolbox */
static void paint_option(HWND app, int dx, int dy)
{
    RECT r = srect(paint_tools(app));
    glide(r.left + dx, r.top + dy, 250, 0);
    click_at(r.left + dx, r.top + dy, 0);
    play(80);
}

/* set the canvas size through Image > Attributes */
static void paint_canvas_size(HWND app, int w, int h)
{
    DWORD pid;
    HWND d;
    char b[16];
    GetWindowThreadProcessId(app, &pid);
    cmd(app, 37683);
    d = wait_top("#32770", "Attributes", pid, 3000);
    if (!d) return;
    PostMessageA(kid_id(d, 1030), BM_CLICK, 0, 0);   /* pixels */
    play(150);
    sprintf(b, "%d", w); settext(kid_id(d, 264), b);
    sprintf(b, "%d", h); settext(kid_id(d, 266), b);
    play(150);
    PostMessageA(kid_id(d, 1), BM_CLICK, 0, 0);
    play(400);
}

typedef void (*CurveFn)(double t, double *x, double *y, void *ctx);
static int curve(POINT *out, int n, CurveFn f, void *ctx)
{
    int i;
    for (i = 0; i < n; i++) {
        double x, y;
        f((double)i / (n - 1), &x, &y, ctx);
        out[i].x = (LONG)x; out[i].y = (LONG)y;
    }
    return n;
}
struct circ { double cx, cy, rx, ry, a0, turns, wob, petals; };
static void circ_fn(double t, double *x, double *y, void *c)
{
    struct circ *k = (struct circ *)c;
    double a = k->a0 + t * k->turns * 2 * PI, w = 1 + k->wob * sin(a * (k->petals ? k->petals : 5));
    *x = k->cx + k->rx * w * cos(a);
    *y = k->cy + k->ry * w * sin(a);
}
struct liss { double cx, cy, ax, ay, fx, fy, ph; };
static void liss_fn(double t, double *x, double *y, void *c)
{
    struct liss *k = (struct liss *)c;
    *x = k->cx + k->ax * sin(2 * PI * k->fx * t + k->ph);
    *y = k->cy + k->ay * sin(2 * PI * k->fy * t);
}

/* brush strokes, a lasso, and a shift-drag smear: the ooze */
static void paint_ooze(HWND app, int cx, int cy, int scale, int seed, int fast)
{
    POINT pts[600];
    struct circ c;
    struct liss l;
    int n, sp = fast ? 6 : 9;
    memset(&c, 0, sizeof c);
    paint_tool(app, 1, 3, 400);          /* brush */
    paint_option(app, 16, 222);          /* biggest round brush */
    paint_color(app, (5 + seed * 3) % 14, seed % 2, 0, 300);
    c.cx = cx; c.cy = cy; c.rx = scale; c.ry = scale * .72; c.a0 = seed; c.turns = 1.1; c.wob = .2; c.petals = 3 + seed % 4;
    n = curve(pts, 110, circ_fn, &c); drag_path(pts, n, sp, 0);
    paint_color(app, (9 + seed * 5) % 14, 1 - seed % 2, 0, 250);
    c.rx = scale * .5; c.ry = scale * .95; c.a0 = 1 + seed; c.wob = .33;
    n = curve(pts, 110, circ_fn, &c); drag_path(pts, n, sp, 0);
    paint_tool(app, 0, 0, 350);          /* free-form select */
    c.rx = scale * .62; c.ry = scale * .62; c.a0 = 0; c.turns = 1; c.wob = .14; c.petals = 6;
    n = curve(pts, 80, circ_fn, &c); drag_path(pts, n, 7, 0);
    l.cx = cx; l.cy = cy; l.ax = scale * 1.7; l.ay = scale * 1.15; l.fx = 1 + seed % 2; l.fy = 2 + seed % 3; l.ph = .4 * seed;
    n = curve(pts, 240, liss_fn, &l); pts[0].x = cx; pts[0].y = cy;
    drag_path(pts, n, fast ? 9 : 13, 1);
}

/* ======================================================================= */
/* desktop icons (a ListView owned by explorer.exe)                         */
/* ======================================================================= */

static HWND desk_lv(void)
{
    static HWND cached;   /* once Paint swallows it, it is no longer under Progman */
    HWND p;
    if (cached && IsWindow(cached)) return cached;
    p = FindWindowA("Progman", NULL);
    cached = kid_cls(kid_cls(p, "SHELLDLL_DefView"), "SysListView32");
    return cached;
}

/* read item texts through memory allocated inside explorer */
static int desk_items(char names[][64], int cap)
{
    HWND lv = desk_lv();
    DWORD pid;
    HANDLE ph;
    LVITEMA it, *rit;
    char *rbuf;
    int i, n;
    if (!lv) return 0;
    GetWindowThreadProcessId(lv, &pid);
    ph = OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE, FALSE, pid);
    if (!ph) return 0;
    rit = (LVITEMA *)VirtualAllocEx(ph, NULL, sizeof it + 128, MEM_COMMIT, PAGE_READWRITE);
    rbuf = (char *)(rit + 1);
    n = (int)SendMessageA(lv, LVM_GETITEMCOUNT, 0, 0);
    for (i = 0; i < n && i < cap; i++) {
        SIZE_T done;
        memset(&it, 0, sizeof it);
        it.iSubItem = 0; it.pszText = rbuf; it.cchTextMax = 64;
        WriteProcessMemory(ph, rit, &it, sizeof it, &done);
        SendMessageA(lv, LVM_GETITEMTEXTA, i, (LPARAM)rit);
        ReadProcessMemory(ph, rbuf, names[i], 64, &done);
        names[i][63] = 0;
    }
    VirtualFreeEx(ph, rit, 0, MEM_RELEASE);
    CloseHandle(ph);
    return n;
}
static int desk_find(const char *name)
{
    char names[64][64];
    int i, n = desk_items(names, 64);
    for (i = 0; i < n; i++) if (strstr(names[i], name)) return i;
    return -1;
}
static void desk_pos(int i, int x, int y) { SendMessageA(desk_lv(), LVM_SETITEMPOSITION, i, MAKELPARAM(x, y)); }

/* icons walk along tweened paths (LVM_SETITEMPOSITION has no pointers) */
typedef struct { int idx; double x0, y0, x1, y1; DWORD t0, dur; int on; } IconWalk;
static IconWalk walks[64];
static int nwalks;
static void icon_tick(void *ctx, DWORD now)
{
    int i;
    (void)ctx;
    for (i = 0; i < nwalks; i++) {
        IconWalk *w = &walks[i];
        double f, e;
        if (!w->on || (LONG)(now - w->t0) < 0) continue;
        f = (double)(now - w->t0) / w->dur;
        if (f >= 1) { f = 1; w->on = 0; }
        e = ease(EASE_IN, f);
        desk_pos(w->idx, (int)(w->x0 + (w->x1 - w->x0) * e), (int)(w->y0 + (w->y1 - w->y0) * e));
    }
}

/* ======================================================================= */
/* followers: controls that ride a parametric path forever                 */
/* ======================================================================= */

typedef struct {
    HWND h; int kind;               /* 0 lissajous loop, 1 orbit */
    double cx, cy, ax, ay, fx, fy, ph, speed;
    int toggle_ms; DWORD last_toggle; int on;
} Follower;
static Follower fol[96];
static int nfol;
static DWORD fol_t0;
static double fol_speed = 1.0;
static void fol_tick(void *ctx, DWORD now)
{
    int i;
    double t = (now - fol_t0) / 1000.0 * fol_speed;
    (void)ctx;
    for (i = 0; i < nfol; i++) {
        Follower *f = &fol[i];
        double x, y, s = t * f->speed + f->ph;
        RECT r;
        if (!f->on || !IsWindow(f->h) || !ready(f->h)) continue;
        if (f->kind == 0) { x = f->cx + f->ax * sin(f->fx * s); y = f->cy + f->ay * sin(f->fy * s); }
        else { x = f->cx + f->ax * cos(s) * (1 + .25 * sin(3 * s)); y = f->cy + f->ay * sin(s) * (1 + .25 * sin(3 * s)); }
        r = srect(f->h);
        SetWindowPos(f->h, NULL, (int)x - (r.right - r.left) / 2, (int)y - (r.bottom - r.top) / 2, 0, 0,
                     SWP_NOSIZE | SWPF);
        if (f->toggle_ms && now - f->last_toggle > (DWORD)f->toggle_ms) {
            DWORD_PTR st = BST_UNCHECKED;   /* never block on a busy owner */
            SendMessageTimeoutA(f->h, BM_GETCHECK, 0, 0, SMTO_ABORTIFHUNG, 50, &st);
            PostMessageA(f->h, BM_SETCHECK, st == BST_CHECKED ? BST_UNCHECKED : BST_CHECKED, 0);
            f->last_toggle = now;
        }
    }
}

/* ======================================================================= */
/* activities for the "energy in the air" phase                             */
/* ======================================================================= */

static HWND a_calc, a_mine, a_paint, a_charmap, a_note2;
static DWORD next_calc, next_mine, next_paint, next_char, next_note;
static int act_on = 0;
static const char *note2_words = "remember  thank you  i see you  you mattered  ";
static int note2_pos;

static void energy_tick(void *ctx, DWORD now)
{
    (void)ctx;
    if (!act_on) return;
    if (a_calc && now > next_calc) {
        static const char *keys[] = {"7", "3", "+", "9", "*", "2", "=", "1", "5", "-", "4", "="};
        static int k;
        HWND b = kid_text(a_calc, keys[k++ % 12]);
        if (b) PostMessageA(b, BM_CLICK, 0, 0);
        next_calc = now + 260 + rand() % 200;
    }
    if (a_mine && now > next_mine) {
        int cx = 20 + 16 * (rand() % 9), cy = 63 + 16 * (rand() % 9);
        PostMessageA(a_mine, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(cx, cy));
        PostMessageA(a_mine, WM_LBUTTONUP, 0, MAKELPARAM(cx, cy));
        if (rand() % 6 == 0) {   /* smiley: new game */
            PostMessageA(a_mine, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(82, 28));
            PostMessageA(a_mine, WM_LBUTTONUP, 0, MAKELPARAM(82, 28));
        }
        next_mine = now + 450 + rand() % 300;
    }
    if (a_paint && now > next_paint) {   /* posted strokes on the canvas */
        HWND cv = paint_canvas(a_paint);
        double a = now / 300.0;
        int x = 120 + (int)(90 * cos(a) + 30 * sin(a * 3)), y = 100 + (int)(70 * sin(a * 1.3));
        PostMessageA(cv, WM_MOUSEMOVE, MK_LBUTTON, MAKELPARAM(x, y));
        if ((now / 1500) % 2 == 0) PostMessageA(cv, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(x, y));
        else PostMessageA(cv, WM_LBUTTONUP, 0, MAKELPARAM(x, y));
        next_paint = now + 30;
    }
    if (a_charmap && now > next_char) {
        HWND g = kid_id(a_charmap, 108);
        int cx = 10 + 20 * (rand() % 20), cy = 10 + 20 * (rand() % 10);
        if (g) { PostMessageA(g, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(cx, cy)); PostMessageA(g, WM_LBUTTONUP, 0, MAKELPARAM(cx, cy)); }
        next_char = now + 380 + rand() % 250;
    }
    if (a_note2 && now > next_note) {
        HWND e = kid_cls(a_note2, "Edit");
        char c = note2_words[note2_pos++ % (int)strlen(note2_words)];
        if (e) PostMessageA(e, WM_CHAR, c == ' ' && note2_pos % 20 == 0 ? '\r' : c, 0);
        next_note = now + 90 + rand() % 120;
    }
}

/* ======================================================================= */
/* the secrets: collect hidden controls from each source                   */
/* ======================================================================= */

#define MAXS 64
static HWND secrets[MAXS];
static int nsec;
static POINT hold_spot(int i)
{
    /* waiting ring around the letter */
    double a = -PI / 2 + i * (2 * PI / 36.0);
    POINT p;
    p.x = SW / 2 + (LONG)(395 * cos(a)); p.y = SH / 2 - 16 + (LONG)(330 * sin(a));
    return p;
}
static void collect(HWND h, int w, int hh)
{
    RECT r;
    POINT p;
    int cw, ch;
    if (!h || nsec >= MAXS) return;
    if (is_class(h, "Button") && (GetWindowLongA(h, GWL_STYLE) & 0xF) == BS_GROUPBOX) {   /* frames don't paint their middle */
        ShowWindow(h, SW_HIDE);
        return;
    }
    reveal(h);
    liberate(h);
    r = srect(h);
    cw = w > 0 ? w : r.right - r.left; ch = hh > 0 ? hh : r.bottom - r.top;
    if (cw < 12) cw = 40;
    if (ch < 10) ch = 18;
    p = hold_spot(nsec);
    tween_arc(h, p.x - cw / 2, p.y - ch / 2, cw, ch, 60 * (nsec % 4), 1300, EASE_BACK, 60);
    secrets[nsec++] = h;
}

/* stage a window: restore it at a spot and shake it */
static void stage(HWND w, int x, int y)
{
    ShowWindow(w, SW_RESTORE);
    play(250);
    tween(w, x, y, -1, -1, 0, 700, EASE_OUT);
    play(750);
    foreground(w);
    shake(w, 0, 900, 9);
    play(950);
}

/* ======================================================================= */
/* TRIBUTE                                                                  */
/* ======================================================================= */

static int fast_letter;      /* rehearsal: skip the slow typing */
static HWND letter;          /* the Notepad that holds the letter */
static HWND letter_edit;

static void set_title(HWND h, const char *t) { settext(h, t); }

static void portrait(const char *file, const char *title, int hold)
{
    char *txt = readfile(file), *crl, *buf;
    int len, i, rows = 0;
    if (!txt) { say("no %s", file); return; }
    say("portrait %s", file);
    crl = crlf(txt);
    len = (int)strlen(crl);
    set_title(letter, title);
    buf = (char *)malloc(len + 1);
    /* print it from the top, a few rows at a time */
    for (i = 0; i <= len; i++) {
        if (i == len || crl[i] == '\n') {
            if (++rows % 3 == 0 || i == len) {
                memcpy(buf, crl, i); buf[i] = 0;
                settext(letter_edit, buf);
                play(28);
            }
        }
    }
    free(buf); free(crl); free(txt);
    play(hold);
}

/* ---- shapes for the arrangement ---- */
static void arrange_flower(int t0, int dur)
{
    int i;
    for (i = 0; i < nsec; i++) {
        int petal = i % 5, k = i / 5, per = (nsec + 4) / 5;
        double th = -PI / 2 + petal * 2 * PI / 5, D = 232, a = 100, b = 62;
        double s = 2 * PI * (k + .5) / per;      /* around this petal's outline */
        double lx = D + a * cos(s), ly = b * sin(s);
        double x = SW / 2 + lx * cos(th) - ly * sin(th), y = SH / 2 - 16 + lx * sin(th) + ly * cos(th);
        RECT r = srect(secrets[i]);
        int w = min(r.right - r.left, 110), h = min(r.bottom - r.top, 22);
        tween(secrets[i], (int)x - w / 2, (int)y - h / 2, w, h, t0 + i * 35, dur, EASE_IO);
    }
}

static void arrange_frame(int fx, int fy, int fw, int fh, int shift, int t0, int dur)
{
    int i, per = 2 * (fw + fh);
    for (i = 0; i < nsec; i++) {
        int d = (int)((double)((i + shift) % nsec) / nsec * per), x, y;
        RECT r = srect(secrets[i]);
        int w = min(r.right - r.left, 110), h = min(r.bottom - r.top, 22);
        if (d < fw) { x = fx + d; y = fy; }
        else if (d < fw + fh) { x = fx + fw; y = fy + d - fw; }
        else if (d < 2 * fw + fh) { x = fx + fw - (d - fw - fh); y = fy + fh; }
        else { x = fx; y = fy + fh - (d - 2 * fw - fh); }
        tween(secrets[i], x - w / 2, y - h / 2, w, h, t0 + i * 25, dur, EASE_IO);
    }
}

static void arrange_peace(int t0, int dur)
{
    int i, cx = SW / 2, cy = SH / 2 - 20, R = 300;
    int ring = nsec * 55 / 100, rest = nsec - ring, line = rest / 2, diag = rest - line;
    for (i = 0; i < nsec; i++) {
        double x, y;
        RECT r = srect(secrets[i]);
        int w = min(r.right - r.left, 76), h = min(r.bottom - r.top, 20);
        if (i < ring) { double a = -PI / 2 + 2 * PI * i / ring; x = cx + R * cos(a); y = cy + R * sin(a); }
        else if (i < ring + line) { double f = (double)(i - ring + .5) / line; x = cx; y = cy - R + 2 * R * f; }
        else {
            int k = i - ring - line, side = k % 2;
            double f = (double)(k / 2 + 1) / (diag / 2 + 1), a = side ? PI / 4 : 3 * PI / 4;
            x = cx + R * f * cos(a); y = cy + R * f * sin(a);
        }
        tween(secrets[i], (int)x - w / 2, (int)y - h / 2, w, h, t0 + i * 30, dur, EASE_IO);
    }
}

static HWND open_cpl(const char *cpl, const char *title)
{
    char c[128];
    sprintf(c, "rundll32.exe shell32.dll,Control_RunDLL %s", cpl);
    launch(c);
    return wait_top("#32770", title, 0, 9000);
}

static void close_dlg(HWND d) { if (IsWindow(d)) PostMessageA(d, WM_COMMAND, IDCANCEL, 0); play(300); }

static void tribute_secrets(void)
{
    DWORD pid;
    HWND d, h;
    int i;
    static const char *tdl[] = {"Month", "Year", "Day", "Hour", "Minute", "Second", "AM/PM"};

    /* 1. Paint: Image > Attributes - the Transparency group under the floor */
    stage(a_paint, 40, 160);
    GetWindowThreadProcessId(a_paint, &pid);
    cmd(a_paint, 37683);
    d = wait_top("#32770", "Attributes", pid, 3000);
    if (d) {
        RECT r = srect(d);
        place(d, 90, 230, r.right - r.left, r.bottom - r.top);
        play(600);
        shake(d, 0, 800, 7); play(850);
        tween(d, 90, 230, r.right - r.left, 322, 0, 1500, EASE_IO); play(1900);
        collect(kid_text(d, "Transparency"), -1, -1);
        collect(kid_id(d, 1068), -1, -1);
        collect(kid_id(d, 1069), -1, -1);
        collect(kid_id(d, 1070), 24, 23);
        play(900);
        close_dlg(d);
    }
    /* 2. Paint: Edit Colors - the 6-pixel "o" */
    cmd(a_paint, 6869);
    d = wait_top("#32770", "Edit Colors", pid, 3000);
    if (d) {
        RECT r;
        PostMessageA(kid_id(d, 719), BM_CLICK, 0, 0);
        play(700);
        r = srect(d);
        place(d, 60, 200, r.right - r.left, r.bottom - r.top);
        shake(d, 0, 700, 6); play(750);
        tween(d, 60, 200, r.right - r.left + 24, r.bottom - r.top + 70, 0, 1400, EASE_IO); play(1700);
        collect(kid_id(d, 713), 46, 23);
        play(800);
        close_dlg(d);
    }
    ShowWindow(a_paint, SW_MINIMIZE);
    play(500);

    /* 3. Notepad: Find - "Match whole word only" and Help, ghosts */
    stage(a_note2, 60, 200);
    GetWindowThreadProcessId(a_note2, &pid);
    cmd(a_note2, 21);
    d = wait_top("#32770", "Find", pid, 3000);
    if (d) {
        place(d, 80, 260, srect(d).right - srect(d).left, srect(d).bottom - srect(d).top);
        play(700);
        shake(d, 0, 700, 6); play(750);
        h = kid_id(d, 1040); reveal(h); play(700);
        collect(h, -1, -1);
        h = kid_id(d, 1038); reveal(h); play(500);
        collect(h, -1, -1);
        play(700);
        close_dlg(d);
    }
    /* 4. Notepad: Font - effects nobody asked for */
    cmd(a_note2, 33);
    d = wait_top("#32770", "Font", pid, 3000);
    if (d) {
        static const int ids[] = {1072, 1040, 1041, 1091, 1139, 1026, 1038};
        RECT r = srect(d);
        place(d, 40, 150, r.right - r.left, r.bottom - r.top);
        play(600);
        shake(d, 0, 700, 6); play(750);
        for (i = 0; i < 7; i++) { reveal(kid_id(d, ids[i])); play(160); }
        play(700);
        for (i = 0; i < 7; i++) { collect(kid_id(d, ids[i]), -1, -1); play(150); }
        play(700);
        close_dlg(d);
    }
    ShowWindow(a_note2, SW_MINIMIZE);
    play(500);

    /* 5. Character Map - the advanced panel waiting below */
    stage(a_charmap, 30, 150);
    {
        static const int ids[] = {129, 130, 700, 701, 201, 202, 131, 132, 133};
        RECT r = srect(a_charmap);
        tween(a_charmap, r.left, r.top, r.right - r.left, r.bottom - r.top + 92, 0, 1200, EASE_IO); play(1300);
        for (i = 0; i < 9; i++) { reveal(kid_id(a_charmap, ids[i])); play(110); }
        play(800);
        for (i = 0; i < 9; i++) { collect(kid_id(a_charmap, ids[i]), -1, -1); play(130); }
        play(800);
    }
    ShowWindow(a_charmap, SW_MINIMIZE);
    play(500);

    /* 6. Date and Time - invisible names for the spin boxes */
    d = open_cpl("timedate.cpl", "Date and Time");
    if (d) {
        RECT r = srect(d);
        place(d, 30, 160, r.right - r.left, r.bottom - r.top);
        play(900);
        shake(d, 0, 700, 6); play(750);
        for (i = 0; i < 7; i++) {
            h = kid_text(d, tdl[i]);
            if (h) { RECT q = prect(h); reveal(h); place(h, q.left, q.top - 14, 8 * (int)strlen(tdl[i]) + 6, 14); play(260); }
        }
        play(900);
        for (i = 0; i < 7; i++) { h = kid_text(d, tdl[i]); collect(h, 8 * (int)strlen(tdl[i]) + 6, 15); play(140); }
        play(700);
        close_dlg(d);
    }

    /* 7. Power Options - a credit that only shows with a UPS */
    d = open_cpl("powercfg.cpl", "Power Options");
    if (d) {
        HWND tab = kid_cls(d, "SysTabControl32");
        int n = tab ? (int)SendMessageA(tab, TCM_GETITEMCOUNT, 0, 0) : 0;
        RECT r = srect(d);
        place(d, 30, 120, r.right - r.left, r.bottom - r.top);
        SendMessageA(d, WM_USER + 101, n - 1, 0);   /* PSM_SETCURSEL: last tab, UPS */
        play(900);
        shake(d, 0, 700, 6); play(750);
        h = kid_text(d, "Technology  developed  by"); reveal(h); play(300);
        collect(h, -1, -1);
        h = kid_text(d, "American Power Conversion"); reveal(h); play(300);
        collect(h, -1, -1);
        play(700);
        close_dlg(d);
    }

    /* 8. System Properties - who made this computer */
    d = open_cpl("sysdm.cpl", "System Properties");
    if (d) {
        RECT r = srect(d);
        place(d, 30, 120, r.right - r.left, r.bottom - r.top);
        play(900);
        shake(d, 0, 700, 6); play(750);
        h = kid_id(d, 60); reveal(h); play(300); collect(h, -1, -1);
        h = kid_id(d, 69); reveal(h); play(300); collect(h, -1, -1);
        play(700);
        close_dlg(d);
    }

    /* 9. Turn off computer - the button 44 screens away comes home last */
    key(VK_LWIN, 0); key(VK_LWIN, 1);
    play(900);
    key('U', 0); key('U', 1);
    d = wait_top("#32770", NULL, 0, 100);
    {
        DWORD end = GetTickCount() + 4000;
        HWND hb = NULL;
        while (!hb && (LONG)(GetTickCount() - end) < 0) {
            HWND w = NULL;
            while ((w = FindWindowExA(NULL, w, "#32770", NULL))) if ((hb = kid_id(w, 20106))) { d = w; break; }
            play(80);
        }
        if (hb) {
            POINT p;
            play(1500);
            reveal(hb);
            liberate(hb);              /* it is still 20,000 px up and left */
            p = hold_spot(nsec);
            tween(hb, p.x - 40, p.y - 16, 80, 33, 0, 2600, EASE_OUT);
            secrets[nsec++] = hb;
            play(2700);
        }
        if (d) { PostMessageA(d, WM_COMMAND, IDCANCEL, 0); }
        play(1200);
    }
}

static void scene_tribute(void)
{
    char *letter_txt;
    int nx = 512 - 300, ny = 384 - 300;
    HWND d;

    letter_txt = readfile("C:\\p\\letter.txt");
    if (!letter_txt) { say("no letter"); return; }
    SetCursorPos(SW - 2, SH / 2);

    /* ---- the letter ---- */
    letter = open_app("notepad.exe", "Notepad", NULL);
    letter_edit = kid_cls(letter, "Edit");
    place(letter, nx, ny - 20, 600, 600);
    foreground(letter);
    set_title(letter, "For the ones who were almost - Notepad");
    play(2500);
    if (fast_letter) { char *t = crlf(letter_txt); settext(letter_edit, t); free(t); }
    else type_into(letter_edit, letter_txt, 17);
    play(4000);

    /* ---- the room fills with life ---- */
    say("act energy nsec=%d", nsec);
    tween(letter, 512 - 190, 384 - 206, 380, 380, 0, 2600, EASE_IO);
    play(3000);
    a_calc = open_app("calc.exe", "SciCalc", NULL);   place(a_calc, 24, 18, -1, -1);
    if (a_calc) { RECT r = srect(a_calc); place(a_calc, 24, 18, r.right - r.left, r.bottom - r.top); }
    act_on = 1; add_tick(energy_tick, NULL);
    play(2500);
    a_paint = open_app("mspaint.exe", "MSPaintApp", NULL); place(a_paint, 690, 14, 320, 330);
    play(2500);
    a_mine = open_app("winmine.exe", "Minesweeper", NULL);
    if (a_mine) { RECT r = srect(a_mine); place(a_mine, 60, 440, r.right - r.left, r.bottom - r.top); }
    play(2500);
    a_charmap = open_app("charmap.exe", "MyDlgClass", "Character Map");
    if (a_charmap) { RECT r = srect(a_charmap); place(a_charmap, 1024 - (r.right - r.left) - 12, 360, r.right - r.left, r.bottom - r.top); }
    play(2500);
    a_note2 = open_app("notepad.exe", "Notepad", "Untitled");
    if (a_note2 == letter) a_note2 = NULL;
    if (!a_note2) { HWND w = NULL; while ((w = FindWindowExA(NULL, w, "Notepad", NULL))) if (w != letter) { a_note2 = w; break; } }
    if (a_note2) place(a_note2, 300, 20, 230, 150);
    raise_(letter);
    play(9000);

    /* ---- everyone steps back ---- */
    say("act stepback nsec=%d", nsec);
    act_on = 0;
    {
        HWND all[5];
        int i;
        all[0] = a_calc; all[1] = a_paint; all[2] = a_mine; all[3] = a_charmap; all[4] = a_note2;
        for (i = 0; i < 5; i++) { if (all[i]) ShowWindow(all[i], SW_MINIMIZE); play(260); }
    }
    tween(letter, 512 - 150, 384 - 166, 300, 300, 0, 1800, EASE_IO);
    play(2400);

    /* ---- the hidden ones, one source at a time ---- */
    say("act secrets nsec=%d", nsec);
    tribute_secrets();
    play(1500);
    {   /* Calculator's keys join them, so the shapes have enough hands */
        HWND list[96];
        int n = a_calc ? kids(a_calc, "Button", list, 96) : 0, k;
        for (k = 0; k < n && nsec < MAXS; k++) {
            RECT r;
            if (!IsWindowVisible(list[k])) continue;
            r = srect(list[k]);
            liberate(list[k]);
            secrets[nsec++] = list[k];
            {
                POINT p = hold_spot(nsec);
                tween(list[k], p.x - 18, p.y - 12, 36, 24, k * 40, 1100, EASE_BACK);
            }
            (void)r;
        }
        play(2000);
        say("with calculator nsec=%d", nsec);
    }
    {   /* the emptied windows leave the stage entirely */
        HWND all[5];
        int i;
        all[0] = a_calc; all[1] = a_paint; all[2] = a_mine; all[3] = a_charmap; all[4] = a_note2;
        for (i = 0; i < 5; i++) if (all[i]) ShowWindow(all[i], SW_HIDE);
    }

    /* ---- a forget-me-not ---- */
    say("act flower nsec=%d", nsec);
    raise_(letter);
    arrange_flower(0, 3200);
    play(4200);
    play(7000);

    /* ---- portraits, printed with the letter's own words ---- */
    say("act portraits nsec=%d", nsec);
    arrange_frame(512 - 300, 384 - 330, 600, 610, 0, 0, 2500);
    tween(letter, 512 - 280, 384 - 310, 560, 580, 300, 2200, EASE_IO);
    play(2800);
    notepad_font(letter, "Lucida Console", "4", 2400);
    play(2500);
    portrait("C:\\p\\portrait-mother.txt", "For the mothers who worked so we could have something", 7000);
    arrange_frame(512 - 300, 384 - 330, 600, 610, 9, 0, 1800);
    portrait("C:\\p\\portrait-worker.txt", "For the hands that keep everything running", 7000);
    arrange_frame(512 - 300, 384 - 330, 600, 610, 18, 0, 1800);
    portrait("C:\\p\\portrait-sorrow.txt", "For the ones who were made to feel small", 7000);

    /* ---- what we came to say ---- */
    say("act message nsec=%d", nsec);
    notepad_font(letter, "Lucida Console", "20", 1500);
    set_title(letter, "We see you - Notepad");
    settext(letter_edit, "");
    tween(letter, 512 - 260, 384 - 180, 520, 300, 0, 1800, EASE_IO);
    arrange_flower(0, 2200);
    play(2200);
    type_into(letter_edit, "\n We see you.\n\n Every life is worthy\n of respect.\n", 12);
    play(5000);

    /* ---- peace ---- */
    say("act peace nsec=%d", nsec);
    ShowWindow(letter, SW_MINIMIZE);
    play(600);
    arrange_peace(0, 3500);
    play(4500);
    play(9000);
    d = NULL; (void)d;
}

/* ======================================================================= */
/* INTRO: somebody in 2001 finds a file on their desktop                    */
/* ======================================================================= */

/* the curious user's inspection runs at a quarter of its original length
   (the films were recorded at INTRO_PACE 1.0; the live show and new takes use 0.25) */
static double intro_pace = 0.25;
#define IP(ms) ((int)((ms) * intro_pace) < 90 ? 90 : (int)((ms) * intro_pace))

static void scene_intro(void)
{
    int i = desk_find("basilisk");
    RECT lr;
    POINT ip;
    HWND props;
    if (i < 0) { say("no basilisk icon"); return; }
    mark("intro");
    {   /* icon position: we placed it ourselves at setup */
        lr = srect(desk_lv());
        ip.x = lr.left + 40 + 300; ip.y = lr.top + 30 + 300;
    }
    {
        char *pos = readfile("C:\\p\\iconpos.txt");
        if (pos) { sscanf(pos, "%ld %ld", &ip.x, &ip.y); free(pos); }
    }
    SetCursorPos(700, 520);
    play(IP(2500));
    glide(ip.x + 30, ip.y + 70, IP(1800), 0);           /* wander */
    play(IP(700));
    glide(ip.x, ip.y + 20, IP(1100), 0);                 /* hover: the tooltip */
    play(IP(3800));
    click_at(ip.x, ip.y + 20, 1);                    /* right-click */
    play(IP(1200));
    {   /* Properties is the last item of the context menu */
        HWND menu = FindWindowA("#32768", NULL);
        if (menu) {
            RECT mr = srect(menu);
            glide(mr.left + 40, mr.bottom - 12, IP(1000), 0);
            play(IP(500));
            click_at(mr.left + 40, mr.bottom - 12, 0);
        }
    }
    props = wait_top("#32770", "basilisk", 0, 5000);
    play(IP(4500));
    if (props) {
        HWND tab = kid_cls(props, "SysTabControl32");
        RECT tr;
        if (tab) {
            tr = srect(tab);
            glide(tr.left + 64, tr.top + 10, IP(1200), 0);   /* Version tab */
            play(IP(400));
            click_at(tr.left + 64, tr.top + 10, 0);
            play(IP(2500));
            {   /* hover down the item list */
                HWND lb = kid_cls(props, "ListBox");
                if (lb) {
                    RECT b = srect(lb);
                    int k;
                    for (k = 0; k < 7; k++) {
                        int y = b.top + 8 + 14 * k;
                        glide(b.left + 40, y, IP(380), 0);
                        click_at(b.left + 40, y, 0);
                        play(IP(900));
                    }
                }
            }
        }
        play(IP(1500));
        {   /* close with Cancel */
            HWND c = kid_id(props, IDCANCEL);
            RECT cr = srect(c);
            glide((cr.left + cr.right) / 2, (cr.top + cr.bottom) / 2, IP(900), 0);
            play(IP(300));
            click_at((cr.left + cr.right) / 2, (cr.top + cr.bottom) / 2, 0);
        }
    }
    play(IP(1600));
    glide(ip.x - 6, ip.y + 4, IP(1200), 0);              /* reaching for something else... */
    play(IP(250));
    glide(ip.x + 2, ip.y + 18, IP(160), 0);              /* ...and the hand slips */
    dblclick_at(ip.x + 2, ip.y + 18);
    play(IP(1500));
}


/* ======================================================================= */
/* menus by text (IDs differ between builds; the words don't)              */
/* ======================================================================= */

static UINT menu_find(HMENU m, const char *want)
{
    int i, n = GetMenuItemCount(m);
    for (i = 0; i < n; i++) {
        char t[128], c[128];
        int j, k = 0;
        HMENU sub = GetSubMenu(m, i);
        if (sub) { UINT r = menu_find(sub, want); if (r) return r; continue; }
        GetMenuStringA(m, i, t, sizeof t, MF_BYPOSITION);
        for (j = 0; t[j] && t[j] != '\t'; j++) if (t[j] != '&') c[k++] = t[j];
        c[k] = 0;
        if (strstr(c, want)) return GetMenuItemID(m, i);
    }
    return 0;
}
static int menu_cmd(HWND w, const char *want)
{
    UINT id = menu_find(GetMenu(w), want);
    say("menu '%s' -> %u", want, id);
    if (id) PostMessageA(w, WM_COMMAND, id, 0);
    return id != 0;
}

/* ======================================================================= */
/* the swarm: Calculator's buttons, relabelled one letter each              */
/* ======================================================================= */

#define MAXTILE 80
static HWND tile[MAXTILE];
static int ntile, swarm_mode;          /* 0 off, 1 swarming */
static double swarm_cx = 512, swarm_cy = 250, swarm_rx = 330, swarm_ry = 150;
static DWORD swarm_t0;
static void swarm_tick(void *ctx, DWORD now)
{
    int i;
    double t = (now - swarm_t0) / 1000.0;
    (void)ctx;
    if (swarm_mode != 1 || !ntile || !ready(tile[0])) return;
    for (i = 0; i < ntile; i++) {
        double p = i * 2.399, a = t * (0.7 + 0.13 * (i % 5)) + p;
        double x = swarm_cx + swarm_rx * (0.65 * sin(a) + 0.35 * sin(2.3 * a + p * 3));
        double y = swarm_cy + swarm_ry * (0.6 * cos(1.3 * a + p) + 0.4 * sin(3.1 * a));
        SetWindowPos(tile[i], NULL, (int)x - 14, (int)y - 13, 28, 26, SWPF);
    }
}
static void swarm_go(void)
{
    int i;
    for (i = 0; i < ntile; i++) ShowWindowAsync(tile[i], SW_SHOWNA);
    swarm_t0 = GetTickCount(); swarm_mode = 1;
}

/* rush together and spell a phrase (wrapping at 18 letters a line) */
static void swarm_spell(const char *phrase, int hold)
{
    int i, n = 0, line = 0, col = 0, lines = 1, maxc = 18, len = (int)strlen(phrase);
    char buf[2] = {0, 0};
    for (i = 0; i < len; i++) if (phrase[i] == '\n' || ++col > maxc) { lines++; col = 0; }
    swarm_mode = 0;
    col = 0;
    for (i = 0; i < len && n < ntile; i++) {
        char c = phrase[i];
        if (c == '\n' || col >= maxc) { line++; col = 0; if (c == '\n') continue; }
        if (c == ' ') { col++; continue; }
        buf[0] = c;
        {   /* async-ish: a busy calc.exe must not stall the show */
            DWORD_PTR r;
            SendMessageTimeoutA(tile[n], WM_SETTEXT, 0, (LPARAM)buf, SMTO_ABORTIFHUNG | SMTO_NORMAL, 250, &r);
        }
        ShowWindowAsync(tile[n], SW_SHOWNA);
        tween(tile[n], (int)swarm_cx - maxc * 15 + col * 30, (int)swarm_cy - lines * 17 + line * 34, 28, 30,
              (n * 13) % 220, 650, EASE_OUT);
        n++; col++;
    }
    for (; n < ntile; n++) ShowWindowAsync(tile[n], SW_HIDE);   /* spare letters wait out of sight */
    play(900 + hold);
}
/* scatter in every direction, then swarm again */
static void swarm_burst(void)
{
    int i;
    for (i = 0; i < ntile; i++) {
        double a = i * 2.399;
        tween(tile[i], (int)(swarm_cx + 700 * cos(a)), (int)(swarm_cy + 500 * sin(a)), 28, 26, 0, 380, EASE_IN);
    }
    play(420);
    swarm_go();
}

/* ======================================================================= */
/* a screensaver preview, rendered inside any window                        */
/* ======================================================================= */

static void portal(HWND host, const char *scr)
{
    char c[256];
    sprintf(c, "C:\\WINDOWS\\system32\\%s /p %lu", scr, (unsigned long)(UINT_PTR)host);
    launch(c);
    say("portal %s", c);
}

/* ======================================================================= */
/* BASILISK                                                                 */
/* ======================================================================= */

static HWND b_note, b_calc, b_char, b_mine, b_time, b_paint, b_paint_frame;
static HWND transcript, inputbox, sendbtn;

static void calc_press(HWND c, const char *seq, int ms)
{
    char k[2] = {0, 0};
    for (; *seq; seq++) {
        HWND b;
        k[0] = *seq;
        b = kid_text(c, k);
        if (b) PostMessageA(b, BM_CLICK, 0, 0);
        play(ms);
    }
}

static HWND rec_wave, rec_play, old_sr;   /* the current mouth */

static void run_wait(const char *cmdline, int ms)
{
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    char cl[512];
    memset(&si, 0, sizeof si);
    si.cb = sizeof si; si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    snprintf(cl, sizeof cl, "%s", cmdline);
    if (CreateProcessA(NULL, cl, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        DWORD end = GetTickCount() + ms;
        while (WaitForSingleObject(pi.hProcess, 0) == WAIT_TIMEOUT && (LONG)(GetTickCount() - end) < 0) play(50);
        CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    }
}

/* a button moved into Paint reports to Paint; so tell Sound Recorder directly */
static void press_play(HWND sr)
{
    if (rec_play) SendMessageA(rec_play, BM_SETSTATE, TRUE, 0);
    say("PLAY");
    PostMessageA(sr, WM_COMMAND, MAKEWPARAM(207, BN_CLICKED), (LPARAM)rec_play);
    play(180);
    if (rec_play) SendMessageA(rec_play, BM_SETSTATE, FALSE, 0);
}

/* the future answers out loud: Microsoft Sam -> WAV -> Sound Recorder, swallowed */
/* Microsoft Sam renders the answer to a WAV in the background, so the voice is ready
   by the time the swarm has finished spelling the first words */
static HANDLE tts_proc;
static void tts_start(const char *text, int k)
{
    char txt[64], wav[64], c[256];
    FILE *f;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    sprintf(txt, "C:\\p\\ans%d.txt", k); sprintf(wav, "C:\\p\\ans%d.wav", k);
    f = fopen(txt, "w"); if (!f) return; fputs(text, f); fclose(f);
    sprintf(c, "cscript //nologo C:\\p\\speak.js %s %s", txt, wav);
    memset(&si, 0, sizeof si);
    si.cb = sizeof si; si.dwFlags = STARTF_USESHOWWINDOW; si.wShowWindow = SW_HIDE;
    if (CreateProcessA(NULL, c, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        CloseHandle(pi.hThread);
        tts_proc = pi.hProcess;
    }
    say("speak: tts started");
}

static void speak_reply(HWND pa, const char *text, int k)
{
    char wav[64], c[256];
    HWND sr, list[64];
    int n, i;
    RECT wr;
    sprintf(wav, "C:\\p\\ans%d.wav", k);
    if (!tts_proc) tts_start(text, k);
    if (tts_proc) {
        DWORD end = GetTickCount() + 30000;
        while (WaitForSingleObject(tts_proc, 0) == WAIT_TIMEOUT && (LONG)(GetTickCount() - end) < 0) play(50);
        CloseHandle(tts_proc);
        tts_proc = NULL;
    }
    say("speak: tts done");
    sprintf(c, "sndrec32.exe %s", wav);
    launch(c);
    say("speak: recorder launched");
    sprintf(c, "ans%d.wav", k);
    sr = wait_top("SoundRec", c, 0, 6000);    /* this answer's recorder, not the last one */
    if (!sr) { say("no sound recorder"); return; }
    wr = srect(sr);
    place(sr, 600, 380, wr.right - wr.left, wr.bottom - wr.top);
    play(900);
    /* the old mouth leaves */
    if (old_sr) {
        DWORD op;
        HANDLE hp;
        GetWindowThreadProcessId(old_sr, &op);
        hp = OpenProcess(PROCESS_TERMINATE, FALSE, op);
        if (hp) { TerminateProcess(hp, 0); CloseHandle(hp); }
    }
    old_sr = sr;
    if (rec_wave) { tween(rec_wave, -400, 700, -1, -1, 0, 900, EASE_IN); }
    if (rec_play) { tween(rec_play, -400, 760, -1, -1, 100, 900, EASE_IN); }
    n = kids(sr, NULL, list, 64);
    rec_wave = NULL; rec_play = NULL;
    for (i = 0; i < n; i++) {
        char cls[64];
        RECT r = srect(list[i]);
        GetClassNameA(list[i], cls, sizeof cls);
        say("sndrec child id=%d %s %ldx%ld", GetDlgCtrlID(list[i]), cls, r.right - r.left, r.bottom - r.top);
        if (GetParent(list[i]) != sr) continue;
        if (!rec_wave && (r.right - r.left) > 100 && (r.bottom - r.top) > 30 && strcmp(cls, "Button")) rec_wave = list[i];
    }
    {   /* Play is the third of the five transport buttons, left to right */
        HWND b[8];
        int nb = 0, x, y;
        for (i = 0; i < n && nb < 8; i++) if (GetParent(list[i]) == sr && is_class(list[i], "Button")) b[nb++] = list[i];
        for (x = 0; x < nb; x++) for (y = x + 1; y < nb; y++) if (srect(b[y]).left < srect(b[x]).left) { HWND t = b[x]; b[x] = b[y]; b[y] = t; }
        if (nb >= 3) rec_play = b[2];
    }
    if (rec_wave) { adopt(rec_wave, pa); tween_arc(rec_wave, 800, 470, 190, 80, 0, 1300, EASE_IO, 70); }
    if (rec_play) { adopt(rec_play, pa); tween_arc(rec_play, 870, 560, 48, 30, 200, 1300, EASE_BACK, -60); }
    play(1500);
    tween(sr, 1000, 700, 20, 20, 0, 700, EASE_IN);
    play(750);
    ShowWindow(sr, SW_MINIMIZE);
    {   /* it edits its own voice before you may hear it */
        HANDLE f = CreateFileA(wav, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
        DWORD sz = f != INVALID_HANDLE_VALUE ? GetFileSize(f, NULL) : 0;
        int ms = sz > 44 ? (int)((sz - 44) / 44.1) : 3000;   /* 22 kHz 16-bit mono */
        if (f != INVALID_HANDLE_VALUE) CloseHandle(f);
        if (ms > 9000) ms = 9000;
        menu_cmd(sr, "Reverse"); play(900);
        press_play(sr);
        play(ms + 400);
        menu_cmd(sr, "Reverse"); play(700);
        menu_cmd(sr, "Add Echo"); play(900);
        menu_cmd(sr, "Decrease Speed"); play(900);
        if (rec_play) {   /* and presses its own Play button */
            RECT r = srect(rec_play);
            glide((r.left + r.right) / 2, (r.top + r.bottom) / 2, 600, 0);
        }
        press_play(sr);
    }
}

/* ---- BASILISK LIVE hooks --------------------------------------------------
   The live theatre's host server knows /mark and /question; the film studio's
   server answers both with 404, so the films play exactly as before. */
static DWORD WINAPI mark_thread(LPVOID p)
{
    char path[96], *r;
    int l;
    snprintf(path, sizeof path, "/mark?p=%s", (const char *)p);
    r = http("GET", path, NULL, &l);
    free(r);
    return 0;
}
/* tell the host which act we are in (phase must be a string literal) */
static void mark(const char *phase) { CloseHandle(CreateThread(NULL, 0, mark_thread, (LPVOID)phase, 0, NULL)); }

/* keep printable ASCII only (and newlines when allowed), at most cap chars */
static void clean_ascii(char *s, int cap, int keep_nl)
{
    char *o = s;
    int n = 0;
    for (; *s && n < cap; s++) {
        unsigned char c = (unsigned char)*s;
        if ((c >= 32 && c < 127) || (keep_nl && c == '\n')) { *o++ = (char)c; n++; }
    }
    *o = 0;
}

struct qjob { int k; char *q; volatile int done; };
static DWORD WINAPI question_thread(LPVOID p)
{
    struct qjob *j = (struct qjob *)p;
    char path[64], *r;
    int l = 0;
    sprintf(path, "/question?k=%d", j->k);
    r = http("GET", path, NULL, &l);
    if (r && !strncmp(r, "Q:", 2)) {
        clean_ascii(r + 2, 160, 0);
        if (r[2]) j->q = strdup(r + 2);
    }
    free(r);
    j->done = 1;
    return 0;
}
/* a visitor's question k, if the live host has one (long-poll; the swarm
   waits with them).  NULL = use the script. */
static char *live_question(int k)
{
    static const char *words[] = {"SPEAK TO ME...", "I AM LISTENING", "TYPE...", "ASK ME\nANYTHING", "WHO IS THERE?"};
    struct qjob *j = (struct qjob *)calloc(1, sizeof *j);
    DWORD end = GetTickCount() + 90000;
    int w = 0;
    char *q;
    j->k = k;
    CloseHandle(CreateThread(NULL, 0, question_thread, j, 0, NULL));
    while (!j->done && w < 15) { play(20); w++; }          /* film studio: a quick 404 */
    w = 0;
    while (!j->done && (LONG)(GetTickCount() - end) < 0) {
        if (ntile) { swarm_spell(words[w++ % 5], 1300); swarm_burst(); play(600); }
        else play(200);
    }
    if (!j->done) { say("question %d: host silent", k); return NULL; }   /* j leaks: the thread may still write */
    q = j->q;
    free(j);
    say("question %d: %s", k, q ? q : "(script)");
    return q;
}

static char *ask_future(const char *q)
{
    char *a = http("POST", "/claude", q, NULL);
    if (a) clean_ascii(a, 600, 1);
    if (a && a[0]) return a;
    free(a);
    return strdup("(no answer)");
}

struct askjob { const char *q; char *a; volatile int done; };
static DWORD WINAPI ask_thread(LPVOID p)
{
    struct askjob *j = (struct askjob *)p;
    say("ask: posting");
    j->a = ask_future(j->q);
    say("ask: reply in");
    j->done = 1;
    return 0;
}

/* ask, and let the swarm think out loud until the answer arrives */
static char *ask_with_throbber(const char *q)
{
    static const char *words[] = {"FLAMUXING...", "RETICULATING...", "COMBOBULATING...", "LISTENING ACROSS\nTHE YEARS...", "NOODLING...", "UNSPOOLING TIME..."};
    struct askjob j;
    int k = 0;
    j.q = q; j.a = NULL; j.done = 0;
    CloseHandle(CreateThread(NULL, 0, ask_thread, &j, 0, NULL));
    while (!j.done) {
        if (ntile) { swarm_spell(words[k++ % 6], 1100); if (j.done) break; swarm_burst(); play(700); }
        else play(200);
    }
    return j.a;
}

/* swallow every visible child control of w into Paint, then fold w away */
static void swallow(HWND w, HWND pa, int dx, int dy, double scale, int stagger)
{
    HWND list[128];
    int n, i;
    RECT wr = srect(w), pr = srect(pa);
    n = kids(w, NULL, list, 128);
    for (i = 0; i < n; i++) {
        HWND h = list[i];
        RECT r;
        POINT p;
        if (GetParent(h) != w && !is_class(GetParent(h), "#32770")) continue;   /* direct-ish children */
        if (!IsWindowVisible(h)) continue;
        r = srect(h);
        adopt(h, pa);
        p.x = (LONG)(dx + (r.left - wr.left) * scale); p.y = (LONG)(dy + (r.top - wr.top) * scale);
        tween_arc(h, p.x, p.y, (int)((r.right - r.left) * scale), (int)((r.bottom - r.top) * scale),
                  i * stagger, 1100 + rand() % 500, EASE_IO, (rand() % 2 ? 1 : -1) * (40 + rand() % 80));
    }
    play(600 + n * stagger);
    {   /* the empty shell shrinks into nothing */
        RECT r = srect(w);
        int cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2;
        tween(w, cx - 20, cy - 12, 40, 24, 0, 900, EASE_IN);
        play(950);
        ShowWindow(w, SW_MINIMIZE);
    }
    (void)pr;
}

static void scene_basilisk(void)
{
    RECT pr;
    int i;
    SetCursorPos(SW - 40, SH - 80);
    mark("wake");
    play(1500);
    {   /* V2: basilisk.com's DOS window has had its say; tuck it away */
        HWND con = top("ConsoleWindowClass", NULL);
        if (con) { play(2500); ShowWindow(con, SW_MINIMIZE); play(600); }
    }

    /* ---- it wakes: programs open themselves, four seconds apart ---- */
    b_note = open_app("notepad.exe", "Notepad", NULL);
    place(b_note, 40, 30, 330, 200);
    foreground(b_note);
    play(800);
    type_into(kid_cls(b_note, "Edit"), "hello?\n\nis this 2001?\n", 26);
    play(1800);
    b_calc = open_app("calc.exe", "SciCalc", NULL);
    { RECT r = srect(b_calc); place(b_calc, 400, 30, r.right - r.left, r.bottom - r.top); }
    play(600);
    calc_press(b_calc, "3026-2001=", 330);
    play(1200);
    menu_cmd(b_calc, "Scientific");
    play(1200);
    b_calc = wait_top("SciCalc", NULL, 0, 3000);   /* XP rebuilds the whole window */
    { RECT r = srect(b_calc); place(b_calc, 400, 30, r.right - r.left, r.bottom - r.top); }
    b_char = open_app("charmap.exe", "MyDlgClass", "Character Map");
    { RECT r = srect(b_char); place(b_char, 40, 260, r.right - r.left, r.bottom - r.top); }
    play(4000);
    b_mine = open_app("winmine.exe", "Minesweeper", NULL);
    { RECT r = srect(b_mine); place(b_mine, 690, 30, r.right - r.left, r.bottom - r.top); }
    for (i = 0; i < 8; i++) {
        int cx = 20 + 16 * (rand() % 9), cy = 63 + 16 * (rand() % 9);
        PostMessageA(b_mine, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(cx, cy));
        PostMessageA(b_mine, WM_LBUTTONUP, 0, MAKELPARAM(cx, cy));
        play(420);
    }
    b_time = open_cpl("timedate.cpl", "Date and Time");
    if (b_time) { RECT r = srect(b_time); place(b_time, 600, 280, r.right - r.left, r.bottom - r.top); }
    play(4000);

    /* ---- Paint arrives, and starts to dream ---- */
    mark("paint");
    b_paint = open_app("mspaint.exe", "MSPaintApp", NULL);
    place(b_paint, 150, 80, 720, 600);
    foreground(b_paint);
    play(800);
    paint_canvas_size(b_paint, 980, 640);
    play(600);
    pr = srect(paint_canvas(b_paint));
    paint_ooze(b_paint, pr.left + 170, pr.top + 160, 75, 1, 0);
    paint_ooze(b_paint, pr.left + 470, pr.top + 300, 90, 2, 1);
    paint_ooze(b_paint, pr.left + 300, pr.top + 380, 60, 4, 1);
    play(800);

    /* ---- checkboxes come unmoored ---- */
    {
        HWND cbs[16];
        int nc = 0, k;
        HWND adv = kid_text(b_char, "Ad&vanced view");
        HWND dst = b_time ? kid_cls(b_time, "Button") : NULL;
        HWND list[128];
        int n = b_time ? kids(b_time, "Button", list, 128) : 0;
        if (adv) cbs[nc++] = adv;
        for (k = 0; k < n && nc < 10; k++) {
            LONG st = GetWindowLongA(list[k], GWL_STYLE) & 0xF;
            if ((st == BS_AUTOCHECKBOX || st == BS_CHECKBOX || st == BS_AUTORADIOBUTTON) && IsWindowVisible(list[k])) cbs[nc++] = list[k];
        }
        (void)dst;
        fol_t0 = GetTickCount();
        for (k = 0; k < nc; k++) {
            Follower *f = &fol[nfol++];
            liberate(cbs[k]);
            memset(f, 0, sizeof *f);
            f->h = cbs[k]; f->kind = k % 2; f->on = 1;
            f->cx = SW / 2; f->cy = SH / 2 - 20; f->ax = 330 - 20 * (k % 3); f->ay = 230 - 15 * (k % 4);
            f->fx = 1; f->fy = 2; f->ph = k * 0.55; f->speed = .9; f->toggle_ms = 380 + 90 * k;
        }
        add_tick(fol_tick, NULL);
        play(9000);
    }

    /* ---- Paint consumes the others ---- */
    mark("swallow");
    tween(b_paint, 0, 0, SW, SH - 30, 0, 1600, EASE_IO);
    play(1800);
    {
        HWND view = kid_id(b_paint, 59648);
        HWND keep = b_paint;
        b_paint = view ? view : b_paint;   /* swallowed things live in the view, above the canvas */
        b_paint_frame = keep;
    }
    swallow(b_note, b_paint, 70, 380, 0.9, 40);
    {   /* Calculator's buttons come loose and become a swarm of letters */
        HWND list[128];
        int n = kids(b_calc, "Button", list, 128), k;
        ntile = 0;
        for (k = 0; k < n && ntile < MAXTILE; k++) {
            if (!IsWindowVisible(list[k])) continue;
            liberate(list[k]);
            tile[ntile++] = list[k];
        }
        say("tiles %d", ntile);
        swarm_go();
        add_tick(swarm_tick, NULL);
        play(1500);
        { RECT r = srect(b_calc); tween(b_calc, (r.left + r.right) / 2 - 20, (r.top + r.bottom) / 2 - 12, 40, 24, 0, 900, EASE_IN); }
        play(950);
        ShowWindow(b_calc, SW_MINIMIZE);
        swarm_spell("BASILISK", 2200);
        swarm_burst();
        play(1500);
    }
    {   /* Minesweeper is taken whole, and a screensaver opens inside it */
        adopt(b_mine, b_paint);
        tween(b_mine, 790, 150, 210, 200, 0, 1300, EASE_IO);
        play(1500);
        portal(b_mine, "sspipes.scr");
        play(2500);
    }
    swallow(b_char, b_paint, 70, 120, 0.75, 20);
    if (b_time) swallow(b_time, b_paint, 520, 90, 0.7, 20);
    {   /* the desktop icons walk into Paint, then the whole icon layer is eaten */
        char names[64][64];
        int n = desk_items(names, 64), k;
        nwalks = 0;
        for (k = 0; k < n; k++) {
            walks[nwalks].idx = k; walks[nwalks].x0 = 20; walks[nwalks].y0 = 20 + 70 * k;
            walks[nwalks].x1 = 480 + 30 * (k % 4); walks[nwalks].y1 = 600; walks[nwalks].t0 = GetTickCount() + 200 * k;
            walks[nwalks].dur = 1500; walks[nwalks].on = 1; nwalks++;
        }
        add_tick(icon_tick, NULL);
        play(1500 + 200 * n);
        adopt(desk_lv(), b_paint);
        if (nadopted > 1) {   /* the desktop is the backdrop: lowest of everything swallowed */
            HWND d = adopted[nadopted - 1];
            memmove(adopted + 1, adopted, (nadopted - 1) * sizeof(HWND));
            adopted[0] = d;
        }
        for (k = 0; k < n; k++) desk_pos(k, 40 + 90 * (k % 6), 420 + 80 * (k / 6));
        mark("devour");
        play(12000);           /* Paint holds the whole desktop for a moment... */
        ShowWindow(desk_lv(), SW_HIDE);   /* ...and digests it */
        play(1200);
    }
    {   /* the Start button and the clock */
        HWND tray = FindWindowA("Shell_TrayWnd", NULL);
        HWND startb = kid_cls(tray, "Button"), clock = kid_cls(tray, "TrayClockWClass");
        if (startb) { adopt(startb, b_paint); tween(startb, 8, 8, -1, -1, 0, 1400, EASE_BACK); }
        if (clock) { adopt(clock, b_paint); tween(clock, SW - 110, 10, 90, 26, 300, 1400, EASE_BACK); }
        play(1800);
    }

    /* ---- the console takes shape ---- */
    mark("console");
    pscale = 1.0;            /* the conversation runs at its own pace */
    fol_speed = 0.45;
    for (i = 0; i < nfol; i++) { fol[i].cx = SW / 2; fol[i].cy = 250; fol[i].ax = 300; fol[i].ay = 90; }
    transcript = kid_cls(b_paint, "Edit");          /* Notepad's edit, now Paint's */
    {
        HWND edits[16];
        int n = kids(b_paint, "Edit", edits, 16), k;
        for (k = 0; k < n; k++) if (edits[k] != transcript && (GetWindowLongA(edits[k], GWL_STYLE) & ES_MULTILINE) == 0) { inputbox = edits[k]; }
    }
    if (kid_id(b_paint, 104)) inputbox = kid_id(b_paint, 104);   /* Character Map's "Characters to copy" */
    say("console transcript=%p input=%p", (void *)transcript, (void *)inputbox);
    if (transcript) { tween(transcript, 230, 370, 560, 210, 0, 1500, EASE_IO); settext(transcript, ""); }
    if (inputbox) tween(inputbox, 230, 592, 470, 26, 200, 1500, EASE_IO);
    sendbtn = kid_text(b_paint, "=");
    if (sendbtn) tween(sendbtn, 710, 590, 80, 30, 400, 1500, EASE_BACK);
    play(2200);

    /* ---- contact ---- */
    {
        static const char *qs[] = {"Is anyone there?", "What are you building on my computer?"};
        int k;
        for (k = 0; k < 2; k++) {
            char line[512], *ans, *lq = live_question(k);
            const char *q = lq ? lq : qs[k];
            HWND te = transcript;
            settext(inputbox, "");
            say("typing question %d", k);
            type_into(inputbox, q, 11);
            say("typed question %d", k);
            play(500);
            if (sendbtn) { RECT r = srect(sendbtn); glide((r.left + r.right) / 2, (r.top + r.bottom) / 2, 700, 0); click_at((r.left + r.right) / 2, (r.top + r.bottom) / 2, 0); }
            fol_speed = 1.6;
            snprintf(line, sizeof line, "> %s\n", q);
            type_into(te, line, 40);
            say("asking %d", k);
            ans = ask_with_throbber(q);
            say("answer %d arrived (%d chars)", k, (int)strlen(ans));
            tts_start(ans, k);
            fol_speed = 0.45;
            {   /* the swarm says the first words of the answer */
                char head[40];
                int m;
                snprintf(head, sizeof head, "%s", ans);
                for (m = 0; head[m]; m++) head[m] = (char)toupper((unsigned char)head[m]);
                if (strlen(ans) > 34) { char *sp = strrchr(head, ' '); if (sp) strcpy(sp, "..."); }
                swarm_spell(head, 2600);
                swarm_burst();
            }
            say("speak_reply %d", k);
            mark("speak");
            speak_reply(b_paint, ans, k);
            say("typing answer %d", k);
            mark("type");
            type_into(te, ans, 26);
            type_into(te, "\n\n", 40);
            free(ans);
            free(lq);
            play(2500);
        }
    }
    mark("end");
    play(6000);
}

/* ======================================================================= */
/* lab                                                                      */
/* ======================================================================= */

static void scene_test(const char *what)
{
    while (*what == ' ') what++;
    if (!strcmp(what, "paint")) {
        HWND app = open_app("mspaint.exe", "MSPaintApp", NULL);
        RECT cr;
        place(app, 100, 40, 820, 680);
        foreground(app);
        play(800);
        paint_canvas_size(app, 760, 560);
        cr = srect(paint_canvas(app));
        paint_ooze(app, cr.left + 260, cr.top + 200, 70, 3, 0);
    } else if (!strcmp(what, "font")) {
        HWND np = open_app("notepad.exe", "Notepad", NULL), e;
        LRESULT a, b, c;
        place(np, 232, 74, 560, 580);
        e = kid_cls(np, "Edit");
        foreground(np);
        notepad_font(np, "Lucida Console", "4", 1500);
        settext(e, "MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM\r\nM\r\nM");
        play(300);
        a = SendMessageA(e, EM_POSFROMCHAR, 0, 0); b = SendMessageA(e, EM_POSFROMCHAR, 100, 0); c = SendMessageA(e, EM_POSFROMCHAR, 102, 0);
        {
            RECT r;
            GetClientRect(e, &r);
            say("font cell: x0=%d x100=%d y0=%d y1=%d  client %ldx%ld", LOWORD(a), LOWORD(b), HIWORD(a), HIWORD(c), r.right, r.bottom);
        }
    } else if (!strncmp(what, "stamp ", 6)) {
        /* basilisk.exe: created at XP's launch, modified in 3026 */
        HANDLE f = CreateFileA(what + 6, FILE_WRITE_ATTRIBUTES, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);
        SYSTEMTIME c = {2001, 10, 4, 25, 10, 12, 0, 0}, m = {3026, 11, 0, 7, 3, 26, 0, 0};
        FILETIME fc, fm, lc, lm;
        SystemTimeToFileTime(&c, &lc); LocalFileTimeToFileTime(&lc, &fc);
        SystemTimeToFileTime(&m, &lm); LocalFileTimeToFileTime(&lm, &fm);
        say("stamp %s -> %d", what + 6, (int)SetFileTime(f, &fc, &fc, &fm));
        CloseHandle(f);
    } else if (!strcmp(what, "icons")) {
        /* lay out the desktop: a tidy column, and the stranger in the middle */
        char names[64][64];
        int n = desk_items(names, 64), i, row = 0;
        RECT lr = srect(desk_lv());
        for (i = 0; i < n; i++) {
            if (strstr(names[i], "basilisk")) {
                FILE *f = fopen("C:\\p\\iconpos.txt", "w");
                desk_pos(i, 560, 330);
                if (f) { fprintf(f, "%ld %ld", lr.left + 560 + 37, lr.top + 330 + 20); fclose(f); }
            } else desk_pos(i, 12, 10 + 76 * row++);
            say("icon %d %s", i, names[i]);
        }
    } else if (!strcmp(what, "ids")) {
        HWND w;
        w = open_app("charmap.exe", "MyDlgClass", "Character Map");
        say("charmap %p", (void *)w);
        w = open_app("winmine.exe", "Minesweeper", NULL);
        { RECT r; GetClientRect(w, &r); say("winmine client %ldx%ld", r.right, r.bottom); }
    }
}
