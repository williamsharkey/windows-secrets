#!/usr/bin/env python3
"""menumock - draw a menu resource as a Windows-classic popup (PNG, needs Pillow).

    python3 menumock.py FILE MENUID [--popup "Debug"] [--cascade "Set &Transparency"]
                        [--mark 32756,...] [--caption TEXT] [--font micross.ttf] -o out.png

FILE is any PE/NE/.mui that codehunt.py can parse.  --popup picks a top-level (or
nested, '/'-separated) popup by its text without '&'; without it the first popup is
drawn.  --cascade opens one sub-popup to the right.  --mark draws a red tag next to
item IDs (items the code deletes or hides at runtime).  The drawing is a mock-up from
the resource, not a screenshot.
"""
import argparse
import importlib.util
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("codehunt", os.path.join(HERE, "codehunt.py"))
ch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch)

FACE, LIGHT, SHADOW, DARK, WHITE = (192, 192, 192), (223, 223, 223), (128, 128, 128), (0, 0, 0), (255, 255, 255)


def tree(items):
    """flat (id, text, flags, depth) list -> nested [(id, text, flags, children)]"""
    root, stack = [], [(-1, None)]
    nodes = {}
    for k, (mid, txt, fl, dep) in enumerate(items):
        node = [mid, txt, fl, []]
        while stack[-1][0] >= dep:
            stack.pop()
        (root if stack[-1][1] is None else stack[-1][1][3]).append(node)
        if mid is None:
            stack.append((dep, node))
    return root


def clean(t):
    return t.replace("&&", "\0").replace("&", "").replace("\0", "&")


def find(nodes, path):
    for part in path.split("/"):
        for n in nodes:
            if n[0] is None and clean(n[1] or "") == part:
                nodes = n[3]
                break
        else:
            sys.exit("menumock: popup %r not found" % part)
    return nodes


def draw_popup(img, d, x, y, nodes, font, marks, cascade_text):
    lh, pad = font.size + 8, 4
    def label(n):
        txt = (n[1] or "").split("\t")
        return clean(txt[0]), (txt[1] if len(txt) > 1 else "")
    wl = max([d.textlength(label(n)[0], font=font) for n in nodes] + [40])
    wa = max([d.textlength(label(n)[1], font=font) for n in nodes] + [0])
    w = int(22 + wl + (24 + wa if wa else 0) + 28)
    h = 2 * pad + sum((8 if is_sep(n) else lh) for n in nodes) if nodes else 2 * pad + lh
    d.rectangle([x, y, x + w, y + h], fill=FACE)
    d.line([x, y, x + w - 1, y], fill=LIGHT); d.line([x, y, x, y + h - 1], fill=LIGHT)
    d.line([x + 1, y + 1, x + w - 2, y + 1], fill=WHITE); d.line([x + 1, y + 1, x + 1, y + h - 2], fill=WHITE)
    d.line([x + w, y, x + w, y + h], fill=DARK); d.line([x, y + h, x + w, y + h], fill=DARK)
    d.line([x + w - 1, y + 1, x + w - 1, y + h - 1], fill=SHADOW); d.line([x + 1, y + h - 1, x + w - 1, y + h - 1], fill=SHADOW)
    cy, sub = y + pad, None
    if not nodes:
        d.text((x + 22, cy + 3), "(empty)", font=font, fill=SHADOW)
    for n in nodes:
        if is_sep(n):
            d.line([x + 3, cy + 3, x + w - 4, cy + 3], fill=SHADOW)
            d.line([x + 3, cy + 4, x + w - 4, cy + 4], fill=WHITE)
            cy += 8
            continue
        text, acc = label(n)
        grayed = bool(n[2] & 0x3)
        hot = cascade_text is not None and n[0] is None and text == clean(cascade_text)
        if hot:
            d.rectangle([x + 3, cy, x + w - 3, cy + lh - 1], fill=(0, 0, 128))
        col = WHITE if hot else (SHADOW if grayed else DARK)
        if grayed and not hot:
            d.text((x + 23, cy + 4), text, font=font, fill=WHITE)
        d.text((x + 22, cy + 3), text, font=font, fill=col)
        raw = (n[1] or "").split("\t")[0]
        i = raw.replace("&&", "\0").find("&")
        if 0 <= i < len(raw) - 1:
            pre = clean(raw[:i])
            ux = x + 22 + d.textlength(pre, font=font)
            uw = d.textlength(raw[i + 1], font=font)
            d.line([ux, cy + 3 + font.size + 1, ux + uw, cy + 3 + font.size + 1], fill=col)
        if acc:
            d.text((x + w - 18 - wa, cy + 3), acc, font=font, fill=col)
        if n[2] & 0x8:
            d.text((x + 7, cy + 2), "✓", font=font, fill=col)
        if n[0] is None:
            ay = cy + lh // 2
            d.polygon([(x + w - 12, ay - 4), (x + w - 12, ay + 4), (x + w - 8, ay)], fill=col)
            if hot:
                sub = (x + w - 3, cy - pad, n[3])
        if n[0] in marks:
            d.ellipse([x + w + 6, cy + lh // 2 - 4, x + w + 14, cy + lh // 2 + 4], fill=(200, 0, 0))
        cy += lh
    return (x + w, y + h), sub


def is_sep(n):
    return n[0] == 0 and not n[1] or (n[2] & 0x800)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("menu")
    ap.add_argument("--popup")
    ap.add_argument("--cascade")
    ap.add_argument("--mark", default="")
    ap.add_argument("--caption")
    ap.add_argument("--font", default="/mnt/c/Windows/Fonts/micross.ttf")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    m = ch.Module(a.file)
    want = int(a.menu) if a.menu.isdigit() else a.menu
    res = [r for r in m.res if r.type == 4 and (r.name == want or str(r.name).upper() == str(want).upper())]
    if not res:
        sys.exit("menumock: no MENU %s" % a.menu)
    nodes = tree(ch.parse_menu(res[0], m.wide))
    nodes = find(nodes, a.popup) if a.popup else (nodes[0][3] if nodes and nodes[0][0] is None else nodes)
    try:
        font = ImageFont.truetype(a.font, 13)
    except OSError:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
    marks = {int(v) for v in a.mark.split(",") if v}
    img = Image.new("RGB", (1400, 1000), (0, 128, 128))
    d = ImageDraw.Draw(img)
    cap = a.caption or "%s  MENU %s%s" % (os.path.basename(a.file), a.menu, ("  › " + a.popup) if a.popup else "")
    d.text((10, 8), cap, font=font, fill=WHITE)
    (r, b), sub = draw_popup(img, d, 10, 30, nodes, font, marks, a.cascade)
    if sub:
        (r2, b2), _ = draw_popup(img, d, sub[0], sub[1], sub[2], font, marks, None)
        r, b = max(r, r2), max(b, b2)
    right = max(r + 24, int(d.textlength(cap, font=font)) + 20)
    img.crop((0, 0, right, b + 12)).save(a.out)


if __name__ == "__main__":
    main()
