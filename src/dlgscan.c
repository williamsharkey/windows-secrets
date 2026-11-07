/*
 * dlgscan - find dialog controls that live outside their own dialog.
 *
 * Reads DIALOG (and optionally MENU) resources straight out of Windows
 * executables - no Windows required.  Understands:
 *   - PE32 / PE32+ files (.exe .dll .cpl .ocx .scr .mui) - Win95 .. Win11
 *   - NE files (16-bit Windows 3.x .exe .dll .drv .cpl)
 *   - DLGTEMPLATE, DLGTEMPLATEEX and the Win16 dialog template format
 *
 * For every dialog it compares each control's rectangle (dialog units)
 * with the dialog's own width/height and reports controls that are:
 *   OUTSIDE   entirely beyond the right/bottom edge or at negative coords
 *   PARTIAL   more than half of the control is clipped by an edge
 *   ZEROSIZE  zero width or height, but has text or a tab stop
 * and with -x also controls that sit inside the dialog but are switched off
 * in the template itself (code may switch them on later - or never):
 *   HIDDEN    no WS_VISIBLE, has text
 *   DISABLED  visible but WS_DISABLED, has text
 *
 * Usage: dlgscan [-a] [-m] [-j] file...
 *   -a  dump every dialog/control, not only suspicious ones
 *   -m  also dump menus
 *   -j  JSON-lines output instead of tab-separated text
 *   -x  also report HIDDEN and DISABLED controls inside the dialog
 *
 * Build: cc -O2 -o dlgscan dlgscan.c       (Linux / macOS)
 *        x86_64-w64-mingw32-gcc -O2 -o dlgscan.exe dlgscan.c
 *
 * Public domain / CC0.  https://github.com/williamsharkey/windows-secrets
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

static u8 *buf;
static size_t blen;
static const char *fname;   /* escaped copy of the current path */
static char fname_buf[1024];
static int opt_all, opt_menu, opt_json, opt_ext;

#define RT_MENU_ 4
#define RT_DIALOG_ 5

#define WS_VISIBLE_ 0x10000000u
#define WS_DISABLED_ 0x08000000u
#define WS_TABSTOP_ 0x00010000u
#define WS_GROUP_ 0x00020000u
#define DS_SETFONT_ 0x40u

static int ok(size_t off, size_t n) { return off <= blen && n <= blen - off; }
static u16 rd16(size_t o) { return ok(o, 2) ? (u16)(buf[o] | buf[o + 1] << 8) : 0; }
static u32 rd32(size_t o) { return ok(o, 4) ? (u32)rd16(o) | (u32)rd16(o + 2) << 16 : 0; }
static short rds16(size_t o) { return (short)rd16(o); }

/* ---- small string helpers ------------------------------------------- */

/* append one code point as UTF-8, escaping for TSV/JSON */
static void put_cp(char *out, size_t *n, size_t cap, u32 c)
{
    char tmp[8];
    int k = 0, i;
    if (c == '&') return; /* drop mnemonic markers for readability */
    if (c == '\\' || c == '"') { tmp[k++] = '\\'; tmp[k++] = (char)c; }
    else if (c == '\t') { tmp[k++] = '\\'; tmp[k++] = 't'; }
    else if (c == '\n') { tmp[k++] = '\\'; tmp[k++] = 'n'; }
    else if (c == '\r') { tmp[k++] = '\\'; tmp[k++] = 'r'; }
    else if (c < 0x20) { k = sprintf(tmp, "\\u%04x", (unsigned)c); }
    else if (c < 0x80) tmp[k++] = (char)c;
    else if (c < 0x800) { tmp[k++] = (char)(0xC0 | c >> 6); tmp[k++] = (char)(0x80 | (c & 63)); }
    else { tmp[k++] = (char)(0xE0 | c >> 12); tmp[k++] = (char)(0x80 | (c >> 6 & 63)); tmp[k++] = (char)(0x80 | (c & 63)); }
    for (i = 0; i < k && *n + 1 < cap; i++) out[(*n)++] = tmp[i];
    out[*n] = 0;
}

/* Windows-1252 high half -> Unicode (for Win16 ANSI strings) */
static const u16 cp1252[32] = {
    0x20AC,0x81,0x201A,0x192,0x201E,0x2026,0x2020,0x2021,0x2C6,0x2030,0x160,0x2039,0x152,0x8D,0x17D,0x8F,
    0x90,0x2018,0x2019,0x201C,0x201D,0x2022,0x2013,0x2014,0x2DC,0x2122,0x161,0x203A,0x153,0x9D,0x17E,0x178};

/* read sz_Or_Ord (wide).  returns offset after it. */
static size_t wsz_or_ord(size_t o, char *out, size_t cap)
{
    size_t n = 0;
    u16 c;
    out[0] = 0;
    if (!ok(o, 2)) return blen;
    if (rd16(o) == 0xFFFF) { sprintf(out, "#%u", rd16(o + 2)); return o + 4; }
    while (ok(o, 2) && (c = rd16(o)) != 0) { put_cp(out, &n, cap, c); o += 2; }
    return o + 2;
}

/* Win16 string or ordinal (0xFF + WORD) */
static size_t asz_or_ord(size_t o, char *out, size_t cap)
{
    size_t n = 0;
    u8 c;
    out[0] = 0;
    if (!ok(o, 1)) return blen;
    if (buf[o] == 0xFF) { sprintf(out, "#%u", rd16(o + 1)); return o + 3; }
    while (ok(o, 1) && (c = buf[o]) != 0) { put_cp(out, &n, cap, c >= 0x80 && c < 0xA0 ? cp1252[c - 0x80] : c); o++; }
    return o + 1;
}

static const char *atom_class(const char *cls)
{
    static const char *names[] = {"Button", "Edit", "Static", "ListBox", "ScrollBar", "ComboBox"};
    int a;
    if (cls[0] == '#') { a = atoi(cls + 1); if (a >= 0x80 && a <= 0x85) return names[a - 0x80]; }
    return cls;
}

/* human readable control kind - checkbox vs pushbutton etc. */
static const char *kind_of(const char *cls, u32 style)
{
    if (!strcmp(cls, "Button")) {
        switch (style & 0xF) {
        case 0: case 1: return "pushbutton";
        case 2: case 3: return "checkbox";
        case 5: case 6: return "3state";
        case 4: case 9: return "radio";
        case 7: return "groupbox";
        case 11: return "ownerdraw-button";
        default: return "button";
        }
    }
    return cls;
}

/* ---- reporting ------------------------------------------------------- */

static char cur_res[128];
static int cur_lang;

struct dlg {
    int x, y, cx, cy;
    u32 style;
    char caption[512];
    int nitems;
};

static void emit_dialog(struct dlg *d)
{
    if (!opt_all) return;
    if (opt_json)
        printf("{\"file\":\"%s\",\"kind\":\"dialog\",\"res\":\"%s\",\"lang\":%d,\"x\":%d,\"y\":%d,\"cx\":%d,\"cy\":%d,\"style\":\"0x%08x\",\"items\":%d,\"caption\":\"%s\"}\n",
               fname, cur_res, cur_lang, d->x, d->y, d->cx, d->cy, d->style, d->nitems, d->caption);
    else
        printf("%s\tDIALOG\t%s\tlang=%d\t%dx%d\t\"%s\"\t%d items\n", fname, cur_res, cur_lang, d->cx, d->cy, d->caption, d->nitems);
}

static void emit_item(struct dlg *d, int x, int y, int cx, int cy, u32 id, u32 style, const char *cls, const char *text)
{
    const char *flag = "";
    int right = x + cx, bottom = y + cy;
    int visx, visy;
    const char *k = kind_of(cls, style);
    int tab = (style & WS_TABSTOP_) != 0;

    /* a combobox template height includes its drop-down list; only the
       edit/button part (~14 DLU) is really on the dialog face */
    if (!strcmp(cls, "ComboBox") && cy > 14) { cy = 14; bottom = y + cy; }

    if (cx > 0 && cy > 0) {
        if (x >= d->cx || y >= d->cy || right <= 0 || bottom <= 0)
            flag = "OUTSIDE";
        else {
            visx = (right < d->cx ? right : d->cx) - (x > 0 ? x : 0);
            visy = (bottom < d->cy ? bottom : d->cy) - (y > 0 ? y : 0);
            if ((long)visx * visy * 2 < (long)cx * cy) flag = "PARTIAL";
        }
    } else if ((text[0] && text[0] != '#') || tab) {
        flag = "ZEROSIZE";
    }
    if (!*flag && opt_ext && text[0] && text[0] != '#') {
        if (!(style & WS_VISIBLE_)) flag = "HIDDEN";
        else if (style & WS_DISABLED_) flag = "DISABLED";
    }
    if (!*flag && !opt_all) return;

    if (opt_json)
        printf("{\"file\":\"%s\",\"kind\":\"control\",\"flag\":\"%s\",\"res\":\"%s\",\"lang\":%d,\"dialog\":\"%s\",\"dlg_cx\":%d,\"dlg_cy\":%d,"
               "\"id\":%d,\"class\":\"%s\",\"type\":\"%s\",\"x\":%d,\"y\":%d,\"cx\":%d,\"cy\":%d,\"style\":\"0x%08x\","
               "\"visible\":%s,\"disabled\":%s,\"tabstop\":%s,\"text\":\"%s\"}\n",
               fname, *flag ? flag : "ok", cur_res, cur_lang, d->caption, d->cx, d->cy, (int)(short)id, cls, k,
               x, y, cx, cy, style, style & WS_VISIBLE_ ? "true" : "false", style & WS_DISABLED_ ? "true" : "false",
               tab ? "true" : "false", text);
    else
        printf("%s\t%s\t%s\tlang=%d\tdlg=%dx%d \"%s\"\tid=%d\t%s\t@%d,%d %dx%d\t%s%s%s\t\"%s\"\n",
               fname, *flag ? flag : "ok", cur_res, cur_lang, d->cx, d->cy, d->caption, (int)(short)id, k,
               x, y, cx, cy, style & WS_VISIBLE_ ? "visible" : "hidden", style & WS_DISABLED_ ? ",disabled" : "",
               tab ? ",tabstop" : "", text);
}

/* ---- dialog template parsers ---------------------------------------- */

static void parse_dlg_pe(size_t o, size_t size)
{
    struct dlg d;
    size_t end = o + size, p;
    int ex, i;
    char tmp[512], cls[256], text[512];

    if (!ok(o, 18)) return;
    memset(&d, 0, sizeof d);
    ex = rd16(o) == 1 && rd16(o + 2) == 0xFFFF;
    if (ex) {
        d.style = rd32(o + 12);
        d.nitems = rd16(o + 16);
        d.x = rds16(o + 18); d.y = rds16(o + 20); d.cx = rds16(o + 22); d.cy = rds16(o + 24);
        p = o + 26;
    } else {
        d.style = rd32(o);
        d.nitems = rd16(o + 8);
        d.x = rds16(o + 10); d.y = rds16(o + 12); d.cx = rds16(o + 14); d.cy = rds16(o + 16);
        p = o + 18;
    }
    p = wsz_or_ord(p, tmp, sizeof tmp);          /* menu */
    p = wsz_or_ord(p, tmp, sizeof tmp);          /* class */
    p = wsz_or_ord(p, d.caption, sizeof d.caption);
    if (d.style & DS_SETFONT_) {
        p += ex ? 6 : 2;
        p = wsz_or_ord(p, tmp, sizeof tmp);
    }
    emit_dialog(&d);
    for (i = 0; i < d.nitems && p < end; i++) {
        u32 style, id;
        int x, y, cx, cy;
        u16 extra;
        p = (p - o + 3) / 4 * 4 + o;
        if (!ok(p, 24)) return;
        if (ex) {
            style = rd32(p + 8);
            x = rds16(p + 12); y = rds16(p + 14); cx = rds16(p + 16); cy = rds16(p + 18);
            id = rd32(p + 20);
            p += 24;
        } else {
            style = rd32(p);
            x = rds16(p + 8); y = rds16(p + 10); cx = rds16(p + 12); cy = rds16(p + 14);
            id = rd16(p + 16);
            p += 18;
        }
        p = wsz_or_ord(p, cls, sizeof cls);
        p = wsz_or_ord(p, text, sizeof text);
        extra = rd16(p);
        p += 2 + extra;
        emit_item(&d, x, y, cx, cy, id, style, atom_class(cls), text);
    }
}

static void parse_dlg_ne(size_t o, size_t size)
{
    struct dlg d;
    size_t end = o + size, p;
    int i;
    char tmp[512], cls[256], text[512];

    if (!ok(o, 13)) return;
    memset(&d, 0, sizeof d);
    d.style = rd32(o);
    d.nitems = buf[o + 4];
    d.x = rds16(o + 5); d.y = rds16(o + 7); d.cx = rds16(o + 9); d.cy = rds16(o + 11);
    p = o + 13;
    p = asz_or_ord(p, tmp, sizeof tmp); /* menu */
    p = asz_or_ord(p, tmp, sizeof tmp); /* class */
    p = asz_or_ord(p, d.caption, sizeof d.caption);
    if (d.style & DS_SETFONT_) { p += 2; p = asz_or_ord(p, tmp, sizeof tmp); }
    emit_dialog(&d);
    for (i = 0; i < d.nitems && p < end; i++) {
        int x, y, cx, cy;
        u32 style;
        u16 id;
        if (!ok(p, 14)) return;
        x = rds16(p); y = rds16(p + 2); cx = rds16(p + 4); cy = rds16(p + 6);
        id = rd16(p + 8);
        style = rd32(p + 10);
        p += 14;
        if (ok(p, 1) && (buf[p] & 0x80)) { sprintf(cls, "#%u", buf[p]); p++; }
        else p = asz_or_ord(p, cls, sizeof cls);
        p = asz_or_ord(p, text, sizeof text);
        if (ok(p, 1)) p += 1 + buf[p];
        emit_item(&d, x, y, cx, cy, id, style, atom_class(cls), text);
    }
}

/* ---- menu parsers ----------------------------------------------------- */

static void menu_line(int depth, u32 id, u32 flags, const char *text)
{
    if (opt_json)
        printf("{\"file\":\"%s\",\"kind\":\"menu\",\"res\":\"%s\",\"lang\":%d,\"depth\":%d,\"id\":%u,\"flags\":\"0x%x\",\"text\":\"%s\"}\n",
               fname, cur_res, cur_lang, depth, id, flags, text);
    else
        printf("%s\tMENU\t%s\tlang=%d\t%*s%s\tid=%u\tflags=0x%x\n", fname, cur_res, cur_lang, depth * 2, "", text, id, flags);
}

static size_t parse_menu_items(size_t p, size_t end, int depth, int wide)
{
    char text[512];
    while (p < end && ok(p, 2)) {
        u16 flags = rd16(p);
        u16 id = 0;
        p += 2;
        if (!(flags & 0x10)) { id = rd16(p); p += 2; }
        if (wide) p = wsz_or_ord(p, text, sizeof text);
        else p = asz_or_ord(p, text, sizeof text);
        menu_line(depth, id, flags, text);
        if (flags & 0x10) p = parse_menu_items(p, end, depth + 1, wide);
        if (flags & 0x80) break;
    }
    return p;
}

static size_t parse_menuex_items(size_t base, size_t p, size_t end, int depth)
{
    char text[512];
    while (p < end && ok(p, 14)) {
        u32 type = rd32(p), state = rd32(p + 4), id = rd32(p + 8);
        u16 res = rd16(p + 12);
        p = wsz_or_ord(p + 14, text, sizeof text);
        p = (p - base + 3) / 4 * 4 + base;
        menu_line(depth, id, type | state << 16, text);
        if (res & 1) { p += 4; p = parse_menuex_items(base, p, end, depth + 1); }
        if (res & 0x80) break;
    }
    return p;
}

static void parse_menu(size_t o, size_t size, int wide)
{
    if (!ok(o, 4)) return;
    if (wide && rd16(o) == 1)
        parse_menuex_items(o, o + 4 + rd16(o + 2), o + size, 0);
    else
        parse_menu_items(o + 4 + rd16(o + 2), o + size, 0, wide);
}

/* ---- PE resource walking -------------------------------------------- */

static u32 nsec, sectab;

static size_t rva2off(u32 rva)
{
    u32 i;
    for (i = 0; i < nsec; i++) {
        size_t s = sectab + i * 40;
        u32 va = rd32(s + 12), vsz = rd32(s + 8), raw = rd32(s + 20), rsz = rd32(s + 16);
        if (vsz < rsz) vsz = rsz;
        if (rva >= va && rva < va + vsz) return (size_t)rva - va + raw;
    }
    return (size_t)-1;
}

static void res_name(size_t rsrc, u32 name, char *out, size_t cap)
{
    if (name & 0x80000000u) {
        size_t o = rsrc + (name & 0x7FFFFFFF), n = 0;
        u16 len = rd16(o), i;
        out[0] = 0;
        for (i = 0; i < len && i < 120; i++) put_cp(out, &n, cap, rd16(o + 2 + i * 2));
    } else
        sprintf(out, "%u", name);
}

static void walk_pe(void)
{
    u32 pe = rd32(0x3C), opt, rsrc_rva;
    u16 magic, nt, i;
    size_t rsrc;

    nsec = rd16(pe + 6);
    opt = pe + 24;
    sectab = opt + rd16(pe + 20);
    magic = rd16(opt);
    rsrc_rva = rd32(opt + (magic == 0x20b ? 112 : 96) + 2 * 8);
    if (!rsrc_rva) return;
    rsrc = rva2off(rsrc_rva);
    if (rsrc == (size_t)-1) return;

    nt = rd16(rsrc + 12) + rd16(rsrc + 14);
    for (i = 0; i < nt && i < 4096; i++) {
        size_t te = rsrc + 16 + i * 8;
        u32 type = rd32(te), tdir = rd32(te + 4);
        size_t nd;
        u16 nn, j;
        if (type & 0x80000000u) continue;
        if (type != RT_DIALOG_ && !(opt_menu && type == RT_MENU_)) continue;
        if (!(tdir & 0x80000000u)) continue;
        nd = rsrc + (tdir & 0x7FFFFFFF);
        nn = rd16(nd + 12) + rd16(nd + 14);
        for (j = 0; j < nn && j < 65535; j++) {
            size_t ne = nd + 16 + j * 8, ld;
            u32 ndir = rd32(ne + 4);
            u16 nl, k;
            if (!(ndir & 0x80000000u)) continue;
            ld = rsrc + (ndir & 0x7FFFFFFF);
            nl = rd16(ld + 12) + rd16(ld + 14);
            for (k = 0; k < nl && k < 256; k++) {
                size_t le = ld + 16 + k * 8, de, off;
                u32 drva, dsz;
                if (rd32(le + 4) & 0x80000000u) continue;
                de = rsrc + rd32(le + 4);
                drva = rd32(de); dsz = rd32(de + 4);
                off = rva2off(drva);
                if (off == (size_t)-1 || !ok(off, dsz)) continue;
                res_name(rsrc, rd32(ne), cur_res, sizeof cur_res);
                cur_lang = (int)rd32(le);
                if (type == RT_DIALOG_) parse_dlg_pe(off, dsz);
                else parse_menu(off, dsz, 1);
            }
        }
    }
}

/* ---- NE resource walking -------------------------------------------- */

static void walk_ne(size_t ne)
{
    size_t rt = ne + rd16(ne + 0x24), p;
    u16 shift = rd16(rt);
    p = rt + 2;
    cur_lang = 0;
    while (ok(p, 8)) {
        u16 tid = rd16(p), cnt = rd16(p + 2), i;
        if (!tid) break;
        p += 8;
        for (i = 0; i < cnt; i++, p += 12) {
            size_t off = (size_t)rd16(p) << shift, len = (size_t)rd16(p + 2) << shift;
            u16 rid = rd16(p + 6);
            int t = tid & 0x8000 ? tid & 0x7FFF : -1;
            if (t != RT_DIALOG_ && !(opt_menu && t == RT_MENU_)) continue;
            if (rid & 0x8000) sprintf(cur_res, "%u", rid & 0x7FFF);
            else {
                size_t s = rt + rid, n = 0;
                u8 l = buf[s], c;
                cur_res[0] = 0;
                for (c = 0; c < l && ok(s + 1 + c, 1); c++) put_cp(cur_res, &n, sizeof cur_res, buf[s + 1 + c]);
            }
            if (!ok(off, len)) continue;
            if (t == RT_DIALOG_) parse_dlg_ne(off, len);
            else parse_menu(off, len, 0);
        }
    }
}

static void scan(const char *path)
{
    FILE *f = fopen(path, "rb");
    long n;
    u32 pe;
    if (!f) { fprintf(stderr, "dlgscan: cannot open %s\n", path); return; }
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n < 64) { fclose(f); return; }
    buf = (u8 *)malloc((size_t)n);
    if (!buf) { fclose(f); return; }
    blen = fread(buf, 1, (size_t)n, f);
    fclose(f);
    {   /* escape backslashes and quotes so the path is valid in JSON */
        size_t n = 0; const char *c;
        for (c = path; *c && n + 2 < sizeof fname_buf; c++) {
            if (*c == '\\' || *c == '"') fname_buf[n++] = '\\';
            fname_buf[n++] = *c;
        }
        fname_buf[n] = 0;
        fname = opt_json ? fname_buf : path;
    }
    if (buf[0] == 'M' && buf[1] == 'Z') {
        pe = rd32(0x3C);
        if (ok(pe, 4) && !memcmp(buf + pe, "PE\0\0", 4)) walk_pe();
        else if (ok(pe, 64) && buf[pe] == 'N' && buf[pe + 1] == 'E') walk_ne(pe);
    }
    free(buf);
    buf = NULL;
}

int main(int argc, char **argv)
{
    int i, files = 0;
    for (i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-a")) opt_all = 1;
        else if (!strcmp(argv[i], "-m")) opt_menu = 1;
        else if (!strcmp(argv[i], "-j")) opt_json = 1;
        else if (!strcmp(argv[i], "-x")) opt_ext = 1;
        else { scan(argv[i]); files++; }
    }
    if (!files) {
        fprintf(stderr, "usage: dlgscan [-a] [-m] [-j] [-x] file.exe|.dll|.mui ...\n"
                        "Finds dialog controls positioned outside their dialog (PE and 16-bit NE).\n");
        return 2;
    }
    return 0;
}
