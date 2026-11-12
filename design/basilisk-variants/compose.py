#!/usr/bin/env python3
"""Compose the BASILISK variant mockups from real Windows XP / 3.11 captures.

Every chrome element (title bars, menus, tabs, list views, buttons, meters, dialogs) is cut from a
screendump of a real XP machine (the studio VM) or an existing capture in site/windows-secrets/.
Text that a real build would put into those controls is drawn with the real XP fonts (Lucida
Console, Tahoma, Trebuchet MS from C:\\Windows\\Fonts) without anti-aliasing, as XP drew them.
Run:  python3 compose.py <captures dir>   -> img/v01.png ... img/v12.png
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'captures')
SITE = os.path.join(HERE, '..', '..', 'site', 'windows-secrets')
OUT = os.path.join(HERE, 'img')
os.makedirs(OUT, exist_ok=True)
FONTS = '/mnt/c/Windows/Fonts/'


def F(name, size):
    return ImageFont.truetype(FONTS + name, size)


LUC = F('lucon.ttf', 13)          # Lucida Console 10 pt @ 96 dpi
TAH = F('tahoma.ttf', 11)         # Tahoma 8 pt (dialogs, menus)
TAHB = F('tahomabd.ttf', 11)
TITLE = F('trebucbd.ttf', 13)     # Trebuchet MS bold 10 pt (Luna title bars)

WHITE, FACE, INK = (255, 255, 255), (236, 233, 216), (0, 0, 0)
BLUE, GREY, GREEN, RED = (0, 70, 160), (110, 110, 110), (0, 110, 0), (170, 0, 0)
TEAL = (0, 130, 132)


def cap(name):
    return Image.open(os.path.join(CAP, name + '.png')).convert('RGB')


def win(name, box):
    x, y, w, h = box
    return cap(name).crop((x, y, x + w, y + h))


# windows as captured (screen rects from place.exe)
W = {
    'wordpad': win('wordpad', (10, 10, 760, 420)),
    'taskperf': win('taskmgr_perf', (600, 10, 410, 470)),
    'taskproc': win('taskmgr_proc', (600, 10, 410, 470)),
    'explorer': win('explorer', (10, 10, 640, 460)),
    'components': win('components', (10, 10, 503, 392)),
    'cleanup': win('cleanup', (10, 10, 379, 450)),
    'display': win('display', (520, 20, 404, 455)),
    'driveprops': win('driveprops', (20, 20, 367, 455)),
    'mouse': win('mouse', (10, 10, 404, 455)),
    'volume': win('volume', (10, 10, 456, 300)),
    'copy': win('copy1', (300, 200, 381, 169)),
    'run': win('run', (20, 500, 347, 186)),
    'perm': win('perm', (300, 450, 411, 159)),
    'defrag': win('defrag2', (10, 10, 700, 560)),
    'notepad': win('st0', (130, 16, 876, 700)),
}
SCREEN = cap('defrag2')          # its taskbar has one button; the desktop is teal


# ------------------------------------------------------------------ slicing helpers

def hstretch(img, left, right, width):
    """keep `left` and `right` columns, stretch the middle to make `width`"""
    w, h = img.size
    out = Image.new('RGB', (width, h))
    out.paste(img.crop((0, 0, left, h)), (0, 0))
    mid = img.crop((left, 0, left + 1, h)).resize((width - left - right, h))
    out.paste(mid, (left, 0))
    out.paste(img.crop((w - right, 0, w, h)), (width - right, 0))
    return out


def vstretch(img, top, bottom, height):
    w, h = img.size
    out = Image.new('RGB', (w, height))
    out.paste(img.crop((0, 0, w, top)), (0, 0))
    mid = img.crop((0, top, w, top + 1)).resize((w, height - top - bottom))
    out.paste(mid, (0, top))
    out.paste(img.crop((0, h - bottom, w, h)), (0, height - bottom))
    return out


def stretch2(img, l, r, t, b, width, height):
    return vstretch(hstretch(img, l, r, width), t, b, height)


def text(d, xy, s, font=TAH, fill=INK):
    d.text(xy, s, font=font, fill=fill)


def drawer(im):
    d = ImageDraw.Draw(im)
    d.fontmode = '1'              # no anti-aliasing: XP's 8-10 pt text is aliased
    return d


# ------------------------------------------------------------------ chrome

def title_bar(width, caption, src='notepad'):
    """a maximized Luna title bar: icon from the source window, caption redrawn, buttons kept"""
    t = W[src].crop((0, 0, W[src].width, 30))
    # wipe the old caption with a clean slice of the bar, keep the icon (0..26) and buttons (last 84)
    clean = t.crop((200, 0, 201, 30)).resize((t.width - 26 - 84, 30))
    t.paste(clean, (26, 0))
    bar = hstretch(t, 26, 84, width)
    d = drawer(bar)
    d.text((31, 8), caption, font=TITLE, fill=(10, 24, 131))     # shadow
    d.text((30, 7), caption, font=TITLE, fill=WHITE)
    return bar


def menu_bar(width, items=('File', 'Edit', 'Format', 'View', 'Help')):
    m = Image.new('RGB', (width, 19), FACE)
    d = drawer(m)
    x = 6
    for it in items:
        d.text((x, 3), it, font=TAH, fill=INK)
        x += d.textlength(it, font=TAH) + 14
    return m


def status_bar(width, cells):
    """WordPad's real status bar, stretched, with our cells' text"""
    s = W['wordpad'].crop((4, 398, 756, 418))
    sb = hstretch(s, 6, 20, width)
    d = drawer(sb)
    # erase the old text
    d.rectangle((2, 3, width - 22, 17), fill=FACE)
    x = 4
    for i, (label, w) in enumerate(cells):
        if i:
            d.line((x - 4, 3, x - 4, 17), fill=(172, 168, 153))
            d.line((x - 3, 3, x - 3, 17), fill=WHITE)
        d.text((x, 4), label, font=TAH, fill=INK)
        x += w
    return sb


def taskbar(buttons=('BASILISK III',)):
    tb = SCREEN.crop((0, 738, 1024, 768))
    band = tb.crop((600, 0, 601, 30)).resize((930 - 98, 30))
    tb.paste(band, (98, 0))
    # one real taskbar button (from the capture), relabelled
    btn = SCREEN.crop((106, 738, 266, 768))
    x = 106
    for b in buttons:
        tb.paste(btn, (x, 0))
        d = drawer(tb)
        d.rectangle((x + 6, 6, x + 156, 24), fill=btn.getpixel((140, 15)))
        tb.paste(W['notepad'].crop((5, 7, 21, 23)), (x + 8, 7))
        d.text((x + 28, 9), b, font=TAH, fill=WHITE)
        x += 162
    return tb


def screen():
    s = Image.new('RGB', (1024, 768), TEAL)
    s.paste(taskbar(), (0, 738))
    return s


def xp_button(label, w=75, h=23, default=False):
    """a real Luna push button (from Disk Defragmenter's 'Analyze'), resized and relabelled"""
    src = W['defrag'].crop((21, 448, 106, 473))
    b = hstretch(src, 5, 5, w).resize((w, h)) if h != src.height else hstretch(src, 5, 5, w)
    d = drawer(b)
    d.rectangle((5, 5, w - 6, h - 6), fill=b.getpixel((w // 2, 4)))
    tw = d.textlength(label, font=TAH)
    d.text(((w - tw) // 2, (h - 12) // 2), label, font=TAH, fill=INK)
    if default:
        d.rectangle((1, 1, w - 2, h - 2), outline=(60, 80, 220))
    return b


def edit_box(w, h, content='', font=LUC, caret=True):
    e = Image.new('RGB', (w, h), WHITE)
    d = drawer(e)
    d.rectangle((0, 0, w - 1, h - 1), outline=(127, 157, 185))
    if content:
        d.text((5, (h - 13) // 2), content, font=font, fill=INK)
    if caret:
        cx = 5 + int(d.textlength(content, font=font)) + 1
        d.line((cx, 4, cx, h - 5), fill=INK)
    return e


def group_box(w, h, label, bg=FACE):
    g = Image.new('RGB', (w, h), bg)
    d = drawer(g)
    d.rounded_rectangle((0, 6, w - 1, h - 1), radius=3, outline=(208, 208, 191))
    tw = d.textlength(label, font=TAH)
    d.rectangle((7, 0, 7 + tw + 4, 12), fill=bg)
    d.text((9, 0), label, font=TAH, fill=(0, 70, 213))
    return g


# ------------------------------------------------------------------ the transcript (Claude Code style)

T_BASIC = [
    [('\u2022 ', INK), ('BASILISK III', INK), ('  \u00b7  Claude Code assembled from Windows XP', GREY)],
    [],
    [('> ', INK), ('make spiral.c draw a red spiral in a window, compile it and start it', INK)],
    [],
    [('\u2022 ', INK), ('Read', BLUE), ('(spiral.c)', INK)],
    [('  \u2514 ', GREY), ('Read 41 lines', GREY)],
    [],
    [('\u2022 ', INK), ('Update', BLUE), ('(spiral.c)', INK)],
    [('  \u2514 ', GREY), ('Updated spiral.c with 2 additions and 1 removal', GREY)],
    [],
    [('\u2022 ', INK), ('Run', BLUE), ('(C:\\tcc\\tcc.exe spiral.c -luser32 -lgdi32 && start spiral.exe)', INK)],
    [('  \u2514 ', GREY), ('(no output)', GREY)],
    [],
    [('\u2022 ', INK), ('The spiral now winds outward from the centre in red; spiral.exe is', INK)],
    [('  ', INK), ('open on the desktop. Want it to animate?', INK)],
    [],
    [('> ', INK), ('yes, rotate it slowly', INK)],
    [],
    [('* ', (205, 90, 40)), ('Compiling\u2026 ', (205, 90, 40)), ('(6s \u00b7 \u2193 1.2k tokens \u00b7 esc to interrupt)', GREY)],
]

T_DIFF = [
    [('\u2022 ', INK), ('Update', BLUE), ('(spiral.c)', INK)],
    [('  \u2514 ', GREY), ('Updated spiral.c with 2 additions and 1 removal', GREY)],
    ('diff', '   12      int n = 9;', None),
    ('diff', '   13 -    for (i = 0; i < n * n; i++) {', 'del'),
    ('diff', '   13 +    double a = 0.0;', 'add'),
    ('diff', '   14 +    for (i = 0; i < 720; i++, a += 0.05) {', 'add'),
    ('diff', '   15          LineTo(dc, cx + (int)(a * 6 * cos(a)),', None),
]


def transcript(d, x, y, lines, width=None, lh=14):
    for ln in lines:
        if isinstance(ln, tuple) and ln and ln[0] == 'diff':
            _, s, kind = ln
            if kind:
                bg = (250, 220, 220) if kind == 'del' else (220, 245, 220)
                d.rectangle((x + 14, y - 1, x + (width or 600), y + lh - 2), fill=bg)
            d.text((x, y), s, font=LUC, fill=RED if kind == 'del' else GREEN if kind == 'add' else INK)
            y += lh
            continue
        cx = x
        for s, col in ln:
            d.text((cx, y), s, font=LUC, fill=col)
            cx += d.textlength(s, font=LUC)
        y += lh
    return y


def scrollbar_v(h):
    """Notepad's real vertical scroll bar, stretched to height h"""
    sb = W['notepad'].crop((857, 51, 874, 674))
    return vstretch(sb, 18, 18, h)


def notepad_pane(w, h, lines=T_BASIC, top_pad=6):
    p = Image.new('RGB', (w, h), WHITE)
    d = drawer(p)
    d.rectangle((0, 0, w - 1, h - 1), outline=(123, 158, 189))
    p.paste(scrollbar_v(h - 2), (w - 18, 1))
    transcript(d, 10, top_pad, lines, width=w - 30)
    return p


def find_bar(w, prompt='', send='Send', stop='Stop', h=40):
    """Notepad's own Find dialog, made into a strip (as in BASILISK III today)"""
    b = Image.new('RGB', (w, h), FACE)
    ex = w - 2 * 78 - 12
    b.paste(edit_box(ex - 16, 24, prompt), (8, 8))
    b.paste(xp_button(send, 74, 26), (ex, 7))
    b.paste(xp_button(stop, 74, 26), (ex + 78, 7))
    return b


def label(im, xy, s, font=TAH, fill=INK, bg=None):
    d = drawer(im)
    if bg:
        tw = d.textlength(s, font=font)
        d.rectangle((xy[0] - 1, xy[1], xy[0] + tw + 1, xy[1] + 12), fill=bg)
    d.text(xy, s, font=font, fill=fill)


def mock_badge(im, s='MOCKUP \u00b7 real XP parts, illustrative contents'):
    d = ImageDraw.Draw(im)
    f = F('tahomabd.ttf', 10)
    tw = d.textlength(s, font=f)
    x0 = 900 - tw - 12
    d.rectangle((x0, 744, x0 + tw + 12, 762), fill=(255, 251, 214), outline=(200, 170, 80))
    d.text((x0 + 6, 747), s, font=f, fill=(120, 80, 0))


# ------------------------------------------------------------------ reusable real parts

def part(name, box):
    x, y, w, h = box
    return W[name].crop((x, y, x + w, y + h))


def _no_wordpad_caret():
    """WordPad's caret was blinking at the start of the document when captured"""
    d = ImageDraw.Draw(W['wordpad'])
    for x in range(10, 22):
        for y in range(141, 160):
            r, g, b = W['wordpad'].getpixel((x, y))
            if r < 60 and g < 60 and b < 60:
                d.point((x, y), fill=WHITE)


_no_wordpad_caret()


def clock_face():
    """the analog clock from Date and Time (real capture in site/)"""
    dt = Image.open(os.path.join(SITE, 'xp-datetime.png')).convert('RGB')
    return dt


def ctx_pie(pct_used=0.41):
    """the drive Properties pie, recoloured for the context window (we draw it ourselves in a real
       build: the shell draws its pie from disk numbers we can't feed it)"""
    pie = part('driveprops', (100, 255, 160, 70)).copy()
    return pie


# ================================================================== the variants

TOP = 49            # below a 30 px title bar and a 19 px menu bar
BOT = 738           # taskbar


def frame(caption, menu=('File', 'Edit', 'Format', 'View', 'Help'), src='notepad'):
    s = screen()
    s.paste(title_bar(1024, caption, src), (0, 0))
    if menu:
        s.paste(menu_bar(1024, menu), (0, 30))
    return s


def time_group():
    dt = Image.open(os.path.join(SITE, 'xp-datetime.png')).convert('RGB')
    g = dt.crop((214, 60, 388, 232)).copy()          # the real "Time" group with the analog clock
    d = ImageDraw.Draw(g)
    d.rectangle((40, 160, 140, 171), fill=g.getpixel((20, 150)))   # the top edge of the time field below
    return g


def calendar():
    dt = Image.open(os.path.join(SITE, 'xp-datetime.png')).convert('RGB')
    return dt.crop((30, 120, 196, 242))


def checkbox(state):
    """real list-view checkboxes from the Windows Components wizard"""
    c = W['components']
    if state == 'on':
        return c.crop((49, 175, 62, 188))
    return c.crop((49, 193, 62, 206))


def todo_list(w, items, title=None):
    """a list view with checkboxes (Windows Components wizard), as Claude Code's to-do list"""
    h = 18 * len(items) + 6
    lv = Image.new('RGB', (w, h), WHITE)
    d = drawer(lv)
    d.rectangle((0, 0, w - 1, h - 1), outline=(127, 157, 185))
    y = 3
    for state, s in items:
        if state == 'doing':
            d.rectangle((2, y - 1, w - 3, y + 15), fill=(49, 106, 197))
            lv.paste(checkbox('off'), (5, y + 1))
            d.rectangle((8, y + 4, 14, y + 10), fill=(120, 140, 170))     # the 'partly installed' shade
            d.text((24, y + 1), s, font=TAH, fill=WHITE)
        else:
            lv.paste(checkbox('on' if state == 'done' else 'off'), (5, y + 1))
            d.text((24, y + 1), s, font=TAH, fill=GREY if state == 'done' else INK)
        y += 18
    return lv


def xpcheck(on, bg=FACE):
    """a themed XP check box: the checked one is real (Mouse Properties); unchecked drawn to match"""
    if on:
        return part('mouse', (76, 145, 13, 13))
    c = Image.new('RGB', (13, 13), (244, 244, 240))
    ImageDraw.Draw(c).rectangle((0, 0, 12, 12), outline=(28, 81, 128))
    return c


def check_row(img, xy, on, lab, bg=FACE):
    img.paste(xpcheck(on), xy)
    d = drawer(img)
    d.text((xy[0] + 19, xy[1]), lab, font=TAH, fill=INK)


TODO = [('done', 'Read spiral.c'), ('done', 'Draw the spiral with GDI'), ('doing', 'Rotate it on a timer'),
        ('todo', 'Recompile with tcc and start'), ('todo', 'Check it runs without flicker')]


def v01():
    """Notepad, refined: today's BASILISK III plus a status line, context gauge and to-do list"""
    s = frame('BASILISK III - Claude Haiku 5.5')
    side = 220
    tx_h = BOT - 22 - 40 - TOP
    s.paste(notepad_pane(1024 - side, tx_h), (0, TOP))
    col = Image.new('RGB', (side, tx_h), FACE)
    col.paste(time_group(), (23, 6))
    g = group_box(side - 16, 118, 'Context')
    pie = part('driveprops', (104, 252, 140, 60))
    g.paste(pie, (32, 14))
    d = drawer(g)
    d.rectangle((10, 78, 20, 88), fill=(0, 0, 255)); d.text((26, 77), 'Used    82,140 tokens', font=TAH, fill=INK)
    d.rectangle((10, 94, 20, 104), fill=(255, 0, 255)); d.text((26, 93), 'Free   117,860 tokens', font=TAH, fill=INK)
    col.paste(g, (8, 186))
    t = group_box(side - 16, 18 * len(TODO) + 30, 'To do')
    t.paste(todo_list(side - 36, TODO), (10, 18))
    col.paste(t, (8, 312))
    s.paste(col, (1024 - side, TOP))
    s.paste(find_bar(1024, 'yes, rotate it slowly'), (0, BOT - 22 - 40))
    s.paste(status_bar(1024, [('Claude Haiku 5.5', 150), ('effort: low', 100), ('context 41%', 110),
                              ('$0.0021 this session', 160), ('C:\\b3\\work', 200)]), (0, BOT - 22))
    mock_badge(s)
    return s


def tab_strip(labels, selected=0, src='display'):
    """a real Luna tab row (Display Properties), relabelled"""
    if src == 'display':
        strip = W['display'].crop((7, 37, 314, 59))
        edges = [0, 55, 104, 183, 251, 306]
    else:
        strip = W['taskperf'].crop((10, 54, 320, 76))
        edges = [0, 69, 129, 205, 268, 309]
    d = drawer(strip)
    # the pointer was over a tab when captured: drop the orange hover line from every unselected tab
    sel_x = (edges[selected], edges[selected + 1])
    ref = edges[3] + 10                       # a tab with no hover, as the row reference
    for x in range(strip.width):
        if sel_x[0] <= x < sel_x[1]:
            continue
        for y in range(0, 10):
            r, g, b = strip.getpixel((x, y))
            if r > 220 and b < 200 and g < 235:
                strip.putpixel((x, y), strip.getpixel((ref, y)))
    for i, lab in enumerate(labels[:5]):
        x0, x1 = edges[i] + 3, edges[i + 1] - 3
        for y in range(4, 19):
            d.line((x0, y, x1, y), fill=strip.getpixel((x0, y)))
        tw = d.textlength(lab, font=TAH)
        d.text(((x0 + x1 - tw) // 2, 6), lab, font=TAH, fill=INK)
    return strip


def page_body(w, h):
    """the Luna tab-page body (white fading to the dialog face), from Display Properties"""
    body = W['display'].crop((8, 59, 396, 415))
    return stretch2(body, 4, 4, 4, 4, w, h)


def v02():
    """Property-sheet tabs: Chat | Tasks | Files | Usage | Settings"""
    s = frame('BASILISK III', menu=None, src='notepad')
    s.paste(Image.new('RGB', (1024, BOT - 30), FACE), (0, 30))
    s.paste(tab_strip(['Chat', 'Tasks', 'Files', 'Usage', 'Settings'], 0), (7, 37))
    body = page_body(1010, BOT - 30 - 29 - 44)
    body.paste(notepad_pane(990, body.height - 58), (10, 10))
    body.paste(find_bar(990, '/review spiral.c', send='Send', stop='Stop'), (10, body.height - 46))
    s.paste(body, (7, 59))
    bx = 1024 - 3 * 81 - 4
    for i, (lab, dflt) in enumerate([('OK', True), ('Cancel', False), ('Help', False)]):
        pass
    by = BOT - 36
    for i, lab in enumerate(['Clear', 'Model\u2026', 'Help']):
        s.paste(xp_button(lab, 75, 23), (1024 - 3 * 81 + i * 81 - 8, by))
    label(s, (12, by + 5), 'Claude Haiku 5.5  \u00b7  context 41%  \u00b7  $0.0021', bg=FACE)
    mock_badge(s)
    return s


def tm_group(name, box, title, values):
    g = part('taskperf', box).copy()
    d = drawer(g)
    # wipe numbers and labels, keep the frame and title position
    d.rectangle((6, 16, g.width - 7, g.height - 5), fill=FACE)
    d.rectangle((8, 0, g.width - 10, 12), fill=FACE)
    d.text((9, 0), title, font=TAH, fill=(0, 70, 213))
    y = 18
    for k, v in values:
        d.text((10, y), k, font=TAH, fill=INK)
        tw = d.textlength(v, font=TAH)
        d.text((g.width - 12 - tw, y), v, font=TAH, fill=INK)
        y += 13
    return g


def tile_h(img, width):
    out = Image.new('RGB', (width, img.height))
    for x in range(0, width, img.width):
        out.paste(img, (x, 0))
    return out


def graph(w, h, series, color=(0, 255, 0)):
    """Task Manager's history graph: its real black/green grid, tiled to size, with our line"""
    g = Image.new('RGB', (w, h), (0, 0, 0))                  # taskmgr owner-draws: black, green grid every 12 px
    d = ImageDraw.Draw(g)
    for x in range(0, w, 12):
        d.line((x, 0, x, h), fill=(0, 128, 64))
    for y in range(0, h, 12):
        d.line((0, y, w, y), fill=(0, 128, 64))
    pts = [(int(i * (w - 1) / (len(series) - 1)), int(h - 2 - v * (h - 4))) for i, v in enumerate(series)]
    d.line(pts, fill=color, width=1)
    return g


def meter(w, h, frac, text_s):
    """Task Manager's usage meter, drawn the way taskmgr draws it (it is owner-drawn): a sunken black
       well, green LED rows, the value underneath"""
    m = Image.new('RGB', (w, h), (0, 0, 0))
    d = ImageDraw.Draw(m)
    d.line((0, 0, w - 1, 0), fill=(128, 128, 128)); d.line((0, 0, 0, h - 1), fill=(128, 128, 128))
    d.line((w - 1, 0, w - 1, h - 1), fill=WHITE); d.line((0, h - 1, w - 1, h - 1), fill=WHITE)
    rows = (h - 26) // 3
    lit = int(rows * frac + 0.5)
    for r in range(rows):
        y = h - 22 - r * 3
        on = r < lit
        for x0 in (w // 2 - 26, w // 2 + 2):
            d.line((x0, y, x0 + 24, y), fill=(0, 255, 0) if on else (0, 100, 0))
    f = F('tahoma.ttf', 10)
    tw = d.textlength(text_s, font=f)
    d.text(((w - tw) // 2, h - 16), text_s, font=f, fill=(0, 255, 0))
    return m


def v03():
    """Task Manager tabs, Usage tab shown: context meter, token rate, spend, tool totals"""
    s = frame('BASILISK III - Task Manager', menu=('File', 'Options', 'View', 'Shut Down', 'Help'))
    s.paste(Image.new('RGB', (1024, BOT - 49), FACE), (0, 49))
    s.paste(tab_strip(['Chat', 'Tools', 'Usage', 'Model', 'Sessions'], 2, src='task'), (6, 53))
    pane = Image.new('RGB', (1012, BOT - 22 - 77 - 6), FACE)
    d = drawer(pane)
    d.rectangle((0, 0, pane.width - 1, pane.height - 1), outline=(145, 155, 156))
    import math
    tok = [0.15 + 0.6 * abs(math.sin(i / 7.0)) * (1 if (i // 15) % 2 else 0.3) for i in range(80)]
    ctx = [min(1, 0.05 + i / 160.0) for i in range(80)]
    cost = [0.0001 * i for i in range(80)]
    def grp(x, y, w, h, title):
        g = group_box(w, h, title)
        pane.paste(g, (x, y))
    grp(12, 10, 150, 160, 'Context used'); pane.paste(meter(110, 128, 0.41, '41 %'), (32, 30))
    grp(174, 10, 822, 160, 'Context history (this session)'); pane.paste(graph(800, 128, ctx), (186, 30))
    grp(12, 180, 150, 160, 'Tokens / second'); pane.paste(meter(110, 128, 0.62, '86 t/s'), (32, 200))
    grp(174, 180, 822, 160, 'Output rate'); pane.paste(graph(800, 128, tok, (255, 255, 0)), (186, 200))
    def kv(x, y, w, title, rows):
        g = group_box(w, 26 + 13 * len(rows), title)
        dd = drawer(g)
        yy = 18
        for k, v in rows:
            dd.text((10, yy), k, font=TAH, fill=INK)
            tw = dd.textlength(v, font=TAH)
            dd.text((w - 12 - tw, yy), v, font=TAH, fill=INK)
            yy += 13
        pane.paste(g, (x, y))
    kv(12, 352, 240, 'Tokens (K)', [('Input', '8.2'), ('Cached', '73.9'), ('Output', '2.1')])
    kv(264, 352, 240, 'Context window (K)', [('Total', '200.0'), ('Used', '82.1'), ('Free', '117.9')])
    kv(516, 352, 240, 'Spend', [('This session', '$0.0021'), ('Today', '$0.0140'), ('Month cap', '$25.00')])
    kv(768, 352, 228, 'Tools', [('Runs', '14'), ('Errors', '1'), ('Time in tools', '0:41')])
    s.paste(pane, (6, 76))
    s.paste(status_bar(1024, [('Tools running: 1', 160), ('Context: 41%', 140), ('Spend: $0.0021 / $25', 220)]), (0, BOT - 22))
    mock_badge(s)
    return s


def defrag_panel(width, fills):
    """Disk Defragmenter's analysis panel, widened, its map showing the context window"""
    p = part('defrag', (0, 280, 700, 245)).copy()
    d = drawer(p)
    d.rectangle((480, 90, 560, 125), fill=FACE)                         # the captured mouse pointer
    p = hstretch(p, 480, 18, width)
    d = drawer(p)
    d.rectangle((0, 0, 4, p.height), fill=FACE)
    d.rectangle((width - 5, 0, width, p.height), fill=FACE)
    d.rectangle((14, 0, 620, 26), fill=FACE)
    d.text((20, 10), 'Context window (200,000 tokens), as of the last reply:', font=TAH, fill=INK)
    d.rectangle((14, 76, 620, 106), fill=FACE)
    d.text((20, 90), 'After /compact (estimate):', font=TAH, fill=INK)
    def bar(y0, y1, parts):
        x = 21
        total = width - 21 - 21
        d.rectangle((21, y0, width - 21, y1), fill=WHITE)
        for frac, col in parts:
            w = int(total * frac)
            for k in range(x, x + w, 6):        # defrag draws in vertical slivers
                d.rectangle((k, y0, min(k + 4, x + w), y1), fill=col)
            x += w
    G, B, R = (0, 220, 0), (0, 0, 255), (255, 0, 0)
    bar(30, 71, fills)
    bar(110, 151, [(0.06, G), (0.09, B)])
    for i, lab in enumerate(['/context', '/compact', 'Pause', 'Stop', '/cost']):
        x0 = [21, 111, 201, 291, 381][i]
        d.rectangle((x0 + 4, 172, x0 + 78, 188), fill=p.getpixel((x0 + 3, 180)))
        tw = d.textlength(lab, font=TAH)
        d.text((x0 + (82 - tw) // 2, 174), lab, font=TAH, fill=INK if i in (0, 1, 4) else GREY)
    d.rectangle((34, 220, 700, 236), fill=FACE)
    for x, lab in [(36, 'New this turn'), (146, 'Cached history'), (255, 'System prompt + tools'), (390, 'Free')]:
        d.text((x, 223), lab, font=TAH, fill=INK)
    for x, col in [(21, R), (131, B), (240, G), (375, WHITE)]:
        d.rectangle((x, 222, x + 10, 232), fill=col, outline=INK)
    return p


def v04():
    """Defrag map of the context window under the transcript; Defragment = /compact"""
    s = frame('BASILISK III - Claude Haiku 5.5')
    G, B, R = (0, 220, 0), (0, 0, 255), (255, 0, 0)
    panel = defrag_panel(1024, [(0.06, G), (0.31, B), (0.04, R)])
    ph = panel.height
    tx_h = BOT - TOP - ph - 40
    s.paste(notepad_pane(1024, tx_h), (0, TOP))
    s.paste(panel, (0, TOP + tx_h))
    s.paste(find_bar(1024, '/compact keep the spiral work'), (0, BOT - 40))
    mock_badge(s)
    return s


def tree_pane(w, h, items):
    """Explorer's real folder tree (header, + boxes, folder icons), our folder"""
    t = part('explorer', (0, 117, 216, 323)).copy()
    t = stretch2(t, 4, 20, 22, 20, w, h)
    d = drawer(t)
    d.rectangle((2, 22, w - 3, h - 3), fill=WHITE)
    d.line((w - 2, 20, w - 2, h - 2), fill=(172, 168, 153))
    fold = part('explorer', (84, 159, 17, 15))
    file_ic = part('explorer', (209, 171, 16, 16))       # a .gif icon from the file list
    y = 26
    for depth, kind, name in items:
        x = 8 + depth * 18
        t.paste(fold if kind == 'dir' else file_ic, (x, y))
        d.text((x + 22, y + 2), name, font=TAH, fill=INK)
        y += 17
    return t


def v05():
    """Explorer workspace: folder tree = files you can @-mention, Address bar = the prompt"""
    s = screen()
    ex = W['explorer']
    top = ex.crop((0, 0, 640, 117))
    top = hstretch(top, 420, 64, 1024)
    d = drawer(top)
    d.rectangle((26, 3, 600, 27), fill=top.getpixel((700, 14)))
    d.text((31, 8), 'BASILISK III - C:\\b3\\work', font=TITLE, fill=(10, 24, 131))
    d.text((30, 7), 'BASILISK III - C:\\b3\\work', font=TITLE, fill=WHITE)
    # Address -> Ask; its edit shows the prompt being typed with an @-mention
    d.rectangle((2, 98, 50, 112), fill=top.getpixel((5, 105)))
    d.text((8, 100), 'Ask', font=TAH, fill=INK)
    d.rectangle((55, 98, 930, 112), fill=WHITE)
    d.text((58, 99), '@spiral.c make it rotate slowly, then rebuild it', font=TAH, fill=INK)
    d.line((58 + int(d.textlength('@spiral.c make it rotate slowly, then rebuild it', font=TAH)) + 1, 99, 58 + int(d.textlength('@spiral.c make it rotate slowly, then rebuild it', font=TAH)) + 1, 111), fill=INK)
    d.rectangle((987, 96, 1022, 114), fill=top.getpixel((1015, 80)))
    d.text((989, 100), 'Send', font=TAH, fill=INK)
    s.paste(top, (0, 0))
    h = BOT - 22 - 117
    s.paste(tree_pane(230, h, [(0, 'dir', 'work'), (1, 'dir', 'notes'), (1, 'file', 'spiral.c'),
                               (1, 'file', 'spiral.exe'), (1, 'file', 'primes.js'), (1, 'file', 'CLAUDE.md'),
                               (0, 'dir', 'tcc'), (0, 'dir', 'sessions')]), (0, 117))
    s.paste(notepad_pane(1024 - 232, h, T_BASIC[2:]), (232, 117))
    s.paste(status_bar(1024, [('6 objects', 120), ('Claude Haiku 5.5', 150), ('context 41%', 110), ('$0.0021', 100)]), (0, BOT - 22))
    mock_badge(s)
    return s


def v06():
    """Permissions and plan: to-do list, allowed commands, and the real MessageBox asking"""
    s = frame('BASILISK III - Claude Haiku 5.5')
    side = 300
    tx_h = BOT - TOP - 40 - 22
    s.paste(notepad_pane(1024 - side, tx_h), (0, TOP))
    col = Image.new('RGB', (side, tx_h), FACE)
    t = group_box(side - 16, 18 * len(TODO) + 30, 'Plan (to do)')
    t.paste(todo_list(side - 36, TODO), (10, 18))
    col.paste(t, (8, 6))
    al = group_box(side - 16, 130, 'Always allowed (Disk Cleanup\'s checklist)')
    lv = Image.new('RGB', (side - 36, 100), WHITE)
    dl = drawer(lv)
    dl.rectangle((0, 0, lv.width - 1, lv.height - 1), outline=(127, 157, 185))
    gchk = part('cleanup', (31, 151, 13, 13))            # the real green-tick list check box
    rows = [('dir, type, findstr', 'read'), ('C:\\tcc\\tcc.exe *', 'build'), ('start *.exe', 'run'),
            ('edit files in C:\\b3\\work', 'edit'), ('del *', 'ask first')]
    for i, (name, kind) in enumerate(rows):
        y = 4 + 19 * i
        if i < 4:
            lv.paste(gchk, (5, y))
        else:
            lv.paste(xpcheck(False), (5, y))
        dl.text((24, y), name, font=TAH, fill=INK)
        tw = dl.textlength(kind, font=TAH)
        dl.text((lv.width - 8 - tw, y), kind, font=TAH, fill=GREY)
    al.paste(lv, (10, 20))
    col.paste(al, (8, 158))
    check_row(col, (16, 300), False, 'Plan mode (Shift+Tab)')
    check_row(col, (16, 322), True, 'Auto-accept edits in C:\\b3\\work')
    g = group_box(side - 16, 118, 'Context')
    g.paste(part('driveprops', (104, 252, 140, 60)), (70, 14))
    dg = drawer(g)
    dg.rectangle((10, 78, 20, 88), fill=(0, 0, 255)); dg.text((26, 77), 'Used    86,410 tokens  (43%)', font=TAH, fill=INK)
    dg.rectangle((10, 94, 20, 104), fill=(255, 0, 255)); dg.text((26, 93), 'Free   113,590 tokens', font=TAH, fill=INK)
    col.paste(g, (8, 352))
    s.paste(col, (1024 - side, TOP))
    s.paste(find_bar(1024, ''), (0, BOT - 62))
    s.paste(status_bar(1024, [('Waiting for your permission', 220), ('context 43%', 110), ('$0.0024', 100)]), (0, BOT - 22))
    s.paste(W['perm'], (180, 300))
    mock_badge(s)
    return s


def v07():
    """WordPad as the transcript: real colour, bold tool names, diffs; the Run box as the prompt"""
    s = frame('BASILISK III - WordPad', menu=('File', 'Edit', 'View', 'Insert', 'Format', 'Help'), src='wordpad')
    s.paste(Image.new('RGB', (1024, BOT - TOP), WHITE), (0, TOP))
    rich = part('wordpad', (12, 141, 726, 180))         # the real RichEdit rendering of the diff
    s.paste(rich, (0, TOP + 4))
    d = drawer(s)
    y = transcript(d, 8, TOP + 196, [
        [], [('> ', INK), ('now make it rotate slowly', INK)], [],
        [('\u2022 ', INK), ('Update', BLUE), ('(spiral.c)', INK)],
        ('diff', '   22 +    SetTimer(w, 1, 40, NULL);', 'add'),
        ('diff', '   31 +    case WM_TIMER: angle += 0.02; InvalidateRect(w, 0, 0); break;', 'add'),
        [], [('* ', (205, 90, 40)), ('Building\u2026 ', (205, 90, 40)), ('(3s \u00b7 esc to interrupt)', GREY)]], width=900)
    sb = scrollbar_v(BOT - TOP - 22 - 120)
    s.paste(sb, (1024 - 17, TOP))
    run = W['run']
    combo = run.crop((54, 85, 330, 112))
    combo = hstretch(combo, 8, 22, 860)
    dd = drawer(combo)
    dd.rectangle((4, 4, 834, 22), fill=WHITE)
    dd.text((6, 6), '/co', font=TAH, fill=INK)
    dd.line((24, 5, 24, 21), fill=INK)
    bar = Image.new('RGB', (1024, 98), FACE)
    bar.paste(combo, (60, 6))
    drawer(bar).text((12, 12), 'Ask:', font=TAH, fill=INK)
    bar.paste(xp_button('Send', 75, 23, True), (936, 8))
    lst = Image.new('RGB', (860, 62), WHITE)
    dl = drawer(lst)
    dl.rectangle((0, 0, 859, 61), outline=INK)
    for i, (c, desc) in enumerate([('/compact', 'summarize the conversation to free context'),
                                   ('/context', 'show what fills the context window'), ('/cost', 'what this session has cost')]):
        if i == 0:
            dl.rectangle((1, 1, 858, 19), fill=(49, 106, 197))
        dl.text((6, 3 + 20 * i), c, font=TAH, fill=WHITE if i == 0 else INK)
        dl.text((110, 3 + 20 * i), desc, font=TAH, fill=WHITE if i == 0 else GREY)
    bar.paste(lst, (60, 33))
    s.paste(bar, (0, BOT - 22 - 98))
    s.paste(status_bar(1024, [('For Help, press F1', 200), ('Claude Haiku 5.5', 150), ('context 38%', 110), ('$0.0019', 100)]), (0, BOT - 22))
    mock_badge(s)
    return s


def mixer_column(title, check_label, checked, lo, hi):
    """one real Volume Control column (the Wave column), relabelled"""
    c = part('volume', (140, 52, 105, 222)).copy()
    d = drawer(c)
    d.rectangle((2, 4, 100, 98), fill=FACE)            # title, the Balance row and "Volume:" go
    d.text((8, 12), title, font=TAHB, fill=INK)
    d.text((8, 30), hi, font=TAH, fill=GREY)
    d.rectangle((2, 192, 100, 216), fill=FACE)
    if checked:
        c.paste(checkbox('on'), (8, 199))
    else:
        c.paste(checkbox('off'), (8, 199))
    d.text((26, 199), check_label, font=TAH, fill=INK)
    d.text((8, 178), lo, font=TAH, fill=GREY)
    return c


def v08():
    """Volume Control as the controls mixer: effort, output length, thinking; check boxes = modes"""
    s = frame('BASILISK III - Claude Haiku 5.5')
    side = 348
    tx_h = BOT - TOP - 40 - 22
    s.paste(notepad_pane(1024 - side, tx_h), (0, TOP))
    col = Image.new('RGB', (side, tx_h), FACE)
    g = group_box(side - 12, 250, 'Controls')
    for i, (t, chk, on, lo, hi) in enumerate([('Effort', 'Plan', True, 'low', 'max'),
                                               ('Output', 'Auto-ok', False, 'short', 'long'),
                                               ('Thinking', 'Show', False, 'none', 'deep')]):
        g.paste(mixer_column(t, chk, on, lo, hi), (8 + i * 108, 18))
    col.paste(g, (6, 6))
    col.paste(time_group(), (86, 272))
    s.paste(col, (1024 - side, TOP))
    s.paste(find_bar(1024, 'think harder about the flicker'), (0, BOT - 62))
    s.paste(status_bar(1024, [('effort: high', 110), ('plan mode', 100), ('context 41%', 110), ('$0.0021', 100)]), (0, BOT - 22))
    mock_badge(s)
    return s


def v09():
    """The busy strip: the shell's flying-papers copy animation as the spinner, with progress"""
    s = frame('BASILISK III - Claude Haiku 5.5')
    cp = W['copy']
    body = cp.crop((4, 30, 377, 120)).copy()
    d = drawer(body)
    d.rectangle((6, 60, 370, 90), fill=FACE)
    d.text((8, 63), 'Running  C:\\tcc\\tcc.exe spiral.c -luser32 -lgdi32', font=TAH, fill=INK)
    d.text((8, 77), "From 'C:\\b3\\work' to 'spiral.exe'   \u00b7   6 s   \u00b7   esc to stop", font=TAH, fill=INK)
    prog = cp.crop((4, 120, 377, 160)).copy()
    strip = Image.new('RGB', (1024, 132), FACE)
    strip.paste(body, (10, 2))
    strip.paste(prog, (10, 92))
    dd = drawer(strip)
    dd.line((0, 0, 1024, 0), fill=(172, 168, 153))
    dd.text((420, 20), 'Tool output so far:', font=TAH, fill=GREY)
    out = edit_box(590, 86, '', caret=False)
    do = drawer(out)
    for i, l in enumerate(['tcc: compiling spiral.c', 'tcc: linking user32, gdi32', 'spiral.exe 4,096 bytes']):
        do.text((6, 6 + 15 * i), l, font=LUC, fill=GREY)
    strip.paste(out, (420, 36))
    tx_h = BOT - TOP - 132 - 40
    s.paste(notepad_pane(1024, tx_h, T_BASIC[:12]), (0, TOP))
    s.paste(strip, (0, TOP + tx_h))
    s.paste(find_bar(1024, ''), (0, BOT - 40))
    mock_badge(s)
    return s


FIX = None


def v10():
    """Windows for Workgroups 3.11: Terminal transcript, Clock, Calculator bill, a Cardfile to-do card,
       and 3.11's own Find dialog as the prompt"""
    fixed = F('tahomabd.ttf', 12)     # stands in for 3.11's System font (PIL cannot draw .fon bitmaps)
    system = F('tahomabd.ttf', 12)
    pub = Image.open(os.path.join(CAP, 'w31-pub4.png')).convert('RGB')
    shot = pub.crop((134, 48, 1150, 780))                # the real BASILISK 3.11 window as it runs today
    s = Image.new('RGB', (1024, 768), (192, 192, 192))
    # title bar: the control-menu box and the min/max arrows are real; the caption between is 3.11's
    tb = shot.crop((0, 0, 1016, 22))
    bar = Image.new('RGB', (1024, 22), tb.getpixel((200, 10)))
    bar.paste(tb.crop((0, 0, 24, 22)), (0, 0))
    bar.paste(tb.crop((1016 - 40, 0, 1016, 22)), (1024 - 40, 0))
    db = drawer(bar)
    db.line((0, 21, 1024, 21), fill=INK)
    tw = db.textlength('BASILISK 3.11', font=system)
    db.text(((1024 - tw) // 2, 4), 'BASILISK 3.11', font=system, fill=INK)
    s.paste(bar, (0, 0))
    menu = shot.crop((0, 22, 1016, 42))
    s.paste(hstretch(menu, 400, 6, 1024), (0, 22))
    term = shot.crop((0, 42, 652, 626)).copy()           # Terminal's transcript, untouched
    drawer(term).rectangle((498, 326, 514, 352), fill=WHITE)   # the captured I-beam pointer
    s.paste(term, (0, 42))
    col = Image.new('RGB', (1024 - 660, 768 - 42), (192, 192, 192))
    clock = Image.open(os.path.join(SITE, 'heritage', 'w311-clock-analog.png')).convert('RGB')
    col.paste(clock, ((col.width - clock.width) // 2, 8))
    calc = Image.open(os.path.join(SITE, 'heritage', 'w311-calc-1252.png')).convert('RGB')
    disp = calc.crop((40, 42, 252, 78)).copy()
    dd = drawer(disp)
    dd.rectangle((8, 6, 202, 30), fill=WHITE)
    dd.text((70, 10), 'session  $0.00061', font=system, fill=INK)
    col.paste(disp, ((col.width - disp.width) // 2, 244))
    # a Cardfile card, drawn the way Cardfile draws one: white, black frame, the index line on top
    card = Image.new('RGB', (330, 190), WHITE)
    dc = drawer(card)
    dc.rectangle((0, 0, 329, 189), outline=INK)
    dc.line((0, 20, 329, 20), fill=INK)
    dc.line((0, 22, 329, 22), fill=INK)
    dc.text((6, 3), 'TO DO - HI.C', font=fixed, fill=INK)
    for i, (mark, t) in enumerate([('x', 'write HI.C'), ('x', 'compile with wcl'), ('>', 'print the cat'),
                                    (' ', 'add a second cat'), (' ', 'check it fits 80 cols')]):
        dc.text((8, 30 + 22 * i), '[%s] %s' % (mark, t), font=fixed, fill=INK)
    back = Image.new('RGB', (330, 190), WHITE)
    db = drawer(back)
    db.rectangle((0, 0, 329, 189), outline=INK)
    db.line((0, 20, 329, 20), fill=INK)
    db.line((0, 22, 329, 22), fill=INK)
    db.text((6, 3), 'SESSION', font=fixed, fill=INK)
    col.paste(back, (24, 292))
    col.paste(card, (14, 312))
    s.paste(col, (660, 42))
    find = Image.open(os.path.join(SITE, 'w311-cardfile-tab0.png')).convert('RGB')   # 3.11's own Find dialog
    f2 = find.copy()
    df = drawer(f2)
    df.rectangle((24, 7, 400, 21), fill=f2.getpixel((30, 14)))
    tw = df.textlength('Ask Claude', font=system)
    df.text(((425 - tw) // 2, 7), 'Ask Claude', font=system, fill=INK)
    df.rectangle((90, 39, 309, 54), fill=WHITE)
    df.text((92, 39), 'add a second cat', font=system, fill=INK)
    df.rectangle((10, 39, 86, 54), fill=f2.getpixel((30, 60)))
    df.text((44, 40), 'Ask:', font=system, fill=INK)
    df.rectangle((330, 40, 408, 52), fill=f2.getpixel((333, 46)))
    df.text((352, 40), 'Send', font=system, fill=INK)
    df.rectangle((330, 69, 408, 81), fill=f2.getpixel((333, 75)))
    df.text((352, 69), 'Stop', font=system, fill=INK)
    df.rectangle((10, 86, 180, 110), fill=f2.getpixel((100, 120)))
    df.rectangle((195, 70, 305, 82), fill=f2.getpixel((100, 120)))
    df.text((202, 71), 'History', font=system, fill=INK)
    s.paste(f2, (4, 632))
    return s


def v11():
    """Settings as a property page (/config): Mouse Properties' slider and check boxes"""
    s = v01()
    page = W['mouse'].copy()
    d = drawer(page)
    d.rectangle((4, 3, 300, 27), fill=page.getpixel((340, 14)))
    d.text((7, 8), 'BASILISK Settings', font=TITLE, fill=(10, 24, 131))
    d.text((6, 7), 'BASILISK Settings', font=TITLE, fill=WHITE)
    tabs = tab_strip(['Effort', 'Model', 'Permissions', 'Memory', 'Display'], 0)
    drawer(page).rectangle((5, 32, 398, 40), fill=page.getpixel((200, 33)))   # the Mouse page's own taller selected tab
    page.paste(tabs.crop((0, 0, 300, 22)), (7, 37))
    d.rectangle((20, 66, 395, 410), fill=page.getpixel((200, 420)))
    page.paste(group_box(370, 92, 'Thinking effort', bg=page.getpixel((200, 420))), (12, 66))
    trk = part('mouse', (106, 108, 116, 30))
    page.paste(trk, (62, 92))
    d.text((24, 98), 'Low', font=TAH, fill=INK)
    d.text((196, 98), 'Max', font=TAH, fill=INK)
    d.text((24, 130), 'medium: thinks when it helps; Esc always interrupts', font=TAH, fill=GREY)
    y = 175
    for lab, on in [('Plan mode: propose before editing (Shift+Tab)', False), ('Auto-accept file edits', True),
                    ('Show thinking summaries', False), ('Notify me with a balloon when a turn finishes', True)]:
        check_row(page, (32, y), on, lab)
        y += 26
    d.text((24, 290), 'Model:', font=TAH, fill=INK)
    combo = part('display', (20, 128, 190, 21)).copy()
    dc = drawer(combo)
    dc.rectangle((2, 2, 172, 18), fill=WHITE)
    dc.text((5, 4), 'Claude Haiku 5.5', font=TAH, fill=INK)
    page.paste(combo, (70, 286))
    s.paste(page, (300, 150))
    return s


def v12():
    """The suite: tabs, WordPad-quality diffs, defrag context strip, to-do, status line"""
    s = frame('BASILISK III', menu=None)
    s.paste(Image.new('RGB', (1024, BOT - 30), FACE), (0, 30))
    s.paste(tab_strip(['Chat', 'Plan', 'Files', 'Usage', 'Settings'], 0), (7, 37))
    body = page_body(1010, BOT - 30 - 29 - 26)
    side = 230
    tx = Image.new('RGB', (1010 - side - 20, body.height - 150), WHITE)
    dt = drawer(tx)
    dt.rectangle((0, 0, tx.width - 1, tx.height - 1), outline=(123, 158, 189))
    tx.paste(part('wordpad', (12, 141, 692, 180)), (2, 4))
    transcript(dt, 10, 196, [[], [('> ', INK), ('now make it rotate slowly', INK)], [],
                             [('* ', (205, 90, 40)), ('Building\u2026 ', (205, 90, 40)), ('(3s \u00b7 esc to interrupt)', GREY)]])
    tx.paste(scrollbar_v(tx.height - 2), (tx.width - 18, 1))
    body.paste(tx, (10, 10))
    t = group_box(side, 18 * len(TODO) + 30, 'Plan', bg=body.getpixel((900, 40)))
    t.paste(todo_list(side - 20, TODO), (10, 18))
    body.paste(t, (1010 - side - 10, 10))
    body.paste(time_group(), (1010 - side + 18, 160))
    mini = defrag_panel(990, [(0.06, (0, 220, 0)), (0.31, (0, 0, 255)), (0.04, (255, 0, 0))]).crop((0, 0, 990, 76))
    body.paste(mini, (10, body.height - 136))
    body.paste(find_bar(990, ''), (10, body.height - 56))
    s.paste(body, (7, 59))
    s.paste(status_bar(1024, [('Claude Haiku 5.5', 150), ('effort: low', 100), ('context 41%', 110), ('$0.0021', 100), ('C:\\b3\\work', 200)]), (0, BOT - 22))
    mock_badge(s)
    return s


if __name__ == '__main__':
    for i, fn in enumerate([v01, v02, v03, v04, v05, v06, v07, v08, v09, v10, v11, v12], 1):
        try:
            im = fn()
            im.save(os.path.join(OUT, 'v%02d.png' % i))
            print('v%02d ok %s' % (i, im.size))
        except Exception as e:
            import traceback
            traceback.print_exc()
            print('v%02d FAILED %r' % (i, e))
