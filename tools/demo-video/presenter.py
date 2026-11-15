#!/usr/bin/env python3
"""Clement Ashby, host of the (fictional) public-access show "Computing at Your Pace": an original character drawn
from code, not based on any real person. A gentle man in his sixties: salt-and-pepper hair with a careful side part,
thin wire glasses, a mustard cardigan and a red bow tie. Beside him a ficus; in front of him a mug that says
WORLD'S OKAYEST USER.

    from presenter import Presenter
    P = Presenter(); img = P.draw(mouth=0.6, shape='a', blink=0, brow=0.3, gesture='point', g=1.0, t=12.3)

`draw` returns an RGBA image of the inner picture (W x H), drawn at SS x the size and reduced, for smooth edges.
    python3 presenter.py sheet OUT.png FONTDIR      a contact sheet of mouths, blinks and gestures
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 420, 470
SS = 3
FONTDIR = os.environ.get('PRESENTER_FONTS', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'design', 'brand', 'sndwave1993', 'fonts'))

SKIN = (236, 192, 158)
SKIN_D = (206, 152, 118)
HAIR = (128, 120, 112)        # salt and pepper
HAIR_L = (178, 172, 164)
CARD = (184, 140, 52)         # mustard cardigan
CARD_D = (146, 106, 34)
SHIRT = (236, 232, 220)
BOW = (168, 30, 40)
WIRE = (150, 140, 110)        # wire glasses
BG_TOP = (52, 86, 92)         # a public-access studio: a teal curtain
BG_BOT = (20, 40, 46)


def _font(size, bold=True):
    try:
        return ImageFont.truetype(os.path.join(FONTDIR, 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), size)
    except OSError:
        return ImageFont.load_default()


def _bg():
    """The set: a teal curtain with soft folds, a spotlight, a ficus on the right (all invented)."""
    s = SS
    im = Image.new('RGB', (W * s, H * s))
    d = ImageDraw.Draw(im)
    for y in range(H * s):
        u = y / (H * s)
        d.line([(0, y), (W * s, y)], fill=tuple(int(BG_TOP[k] * (1 - u) + BG_BOT[k] * u) for k in range(3)))
    for k in range(9):   # curtain folds
        x = (k + 0.5) * W * s / 9
        fold = Image.new('L', im.size, 0)
        ImageDraw.Draw(fold).rectangle([x - 6 * s, 0, x + 6 * s, H * s], fill=40)
        fold = fold.filter(ImageFilter.GaussianBlur(8 * s))
        im.paste(Image.new('RGB', im.size, (10, 24, 28)), (0, 0), fold)
    glow = Image.new('L', im.size, 0)
    ImageDraw.Draw(glow).ellipse([W * s * 0.15, H * s * 0.02, W * s * 0.85, H * s * 0.8], fill=80)
    glow = glow.filter(ImageFilter.GaussianBlur(40 * s))
    im = Image.composite(Image.new('RGB', im.size, (120, 170, 168)), im, glow)
    d = ImageDraw.Draw(im)
    # the ficus: a tall stem with small oval leaves, in a white pot
    d.rectangle([326 * s, 404 * s, 420 * s, 412 * s], fill=(90, 62, 40))   # a shelf
    d.polygon([(338 * s, 352 * s), (398 * s, 352 * s), (390 * s, 404 * s), (346 * s, 404 * s)], fill=(226, 222, 212))
    d.line([(368 * s, 352 * s), (366 * s, 120 * s)], fill=(96, 70, 44), width=4 * s)
    for k in range(26):
        a = k * 2.399
        r = 18 + (k % 5) * 9
        cx = 366 + math.cos(a) * r * 0.9
        cy = 112 + k * 8.5 + math.sin(a) * 12
        col = (44, 108, 58) if k % 3 else (64, 132, 70)
        d.ellipse([(cx - 8) * s, (cy - 5) * s, (cx + 8) * s, (cy + 5) * s], fill=col)
    return im


def _mug():
    """The mug, drawn once: white, a handle, two lines of text."""
    s = SS
    m = Image.new('RGBA', (110 * s, 96 * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    d.ellipse([78 * s, 24 * s, 106 * s, 64 * s], outline=(236, 236, 230), width=7 * s)       # handle
    d.rounded_rectangle([4 * s, 8 * s, 86 * s, 92 * s], radius=8 * s, fill=(242, 240, 232), outline=(180, 176, 166), width=2 * s)
    d.ellipse([4 * s, 2 * s, 86 * s, 16 * s], fill=(90, 56, 36), outline=(180, 176, 166), width=2 * s)   # coffee
    f1, f2 = _font(13 * s), _font(10 * s)
    d.text((45 * s, 34 * s), "WORLD'S", font=f2, fill=(30, 50, 120), anchor='mm')
    d.text((45 * s, 52 * s), 'OKAYEST', font=f1, fill=(168, 30, 40), anchor='mm')
    d.text((45 * s, 70 * s), 'USER', font=f1, fill=(30, 50, 120), anchor='mm')
    return m


class Presenter:
    def __init__(self):
        self.bg = _bg()
        self.mug = _mug()

    def draw(self, mouth=0.0, shape='a', blink=0.0, brow=0.0, gesture='none', g=0.0, t=0.0, tilt=0.0):
        s = SS
        im = self.bg.copy()
        d = ImageDraw.Draw(im)
        sway = math.sin(t * 0.7) * 2.5 + tilt
        breath = math.sin(t * 1.5) * 1.5
        cx = W / 2 - 20 + sway * 0.5
        hx, hy = W / 2 - 20 + sway, 190 + breath * 0.5
        P = lambda pts: [(x * s, y * s) for x, y in pts]
        # --- body: mustard cardigan, white shirt, red bow tie
        top = 334 + breath
        d.polygon(P([(cx - 146, H + 5), (cx - 134, top + 40), (cx - 92, top + 2), (cx - 32, top - 6), (cx + 32, top - 6),
                     (cx + 92, top + 2), (cx + 134, top + 40), (cx + 146, H + 5)]), fill=CARD)
        for k in range(12, 280, 9):   # the knit: faint ribbing
            d.line(P([(cx - 140 + k, top + 44), (cx - 142 + k, H)]), fill=(174, 130, 46), width=s)
        d.polygon(P([(cx - 34, top - 6), (cx + 34, top - 6), (cx, top + 104)]), fill=SHIRT)
        d.polygon(P([(cx - 34, top - 6), (cx - 5, top + 106), (cx - 16, top + 112), (cx - 50, top + 4)]), fill=CARD_D)
        d.polygon(P([(cx + 34, top - 6), (cx + 5, top + 106), (cx + 16, top + 112), (cx + 50, top + 4)]), fill=CARD_D)
        for k in range(3):
            by = top + 128 + k * 32
            d.ellipse(P([(cx - 5, by - 5), (cx + 5, by + 5)]), fill=(110, 76, 40))
        d.polygon(P([(cx - 30, top - 10), (cx - 6, top + 8), (cx - 28, top + 24)]), fill=SHIRT, outline=(190, 186, 176))
        d.polygon(P([(cx + 30, top - 10), (cx + 6, top + 8), (cx + 28, top + 24)]), fill=SHIRT, outline=(190, 186, 176))
        d.rounded_rectangle(P([(hx - 30, hy + 62), (hx + 30, top + 4)]), radius=10 * s, fill=SKIN_D)   # neck
        bty = top + 10
        d.polygon(P([(cx - 32, bty - 12), (cx - 4, bty - 3), (cx - 4, bty + 3), (cx - 32, bty + 12)]), fill=BOW)
        d.polygon(P([(cx + 32, bty - 12), (cx + 4, bty - 3), (cx + 4, bty + 3), (cx + 32, bty + 12)]), fill=BOW)
        d.ellipse(P([(cx - 7, bty - 7), (cx + 7, bty + 7)]), fill=(196, 50, 60))
        # --- head: a longish face
        d.ellipse(P([(hx - 84, hy - 4), (hx - 62, hy + 40)]), fill=SKIN_D)          # ears
        d.ellipse(P([(hx + 62, hy - 4), (hx + 84, hy + 40)]), fill=SKIN_D)
        d.ellipse(P([(hx - 72, hy - 96), (hx + 72, hy + 100)]), fill=SKIN)
        # hair: a careful side part on his left, grey at the temples
        d.chord(P([(hx - 76, hy - 104), (hx + 76, hy + 20)]), 180, 360, fill=HAIR)
        d.polygon(P([(hx - 76, hy - 42), (hx - 64, hy - 10), (hx - 58, hy - 44)]), fill=HAIR_L)   # temples
        d.polygon(P([(hx + 76, hy - 42), (hx + 64, hy - 10), (hx + 58, hy - 44)]), fill=HAIR_L)
        d.ellipse(P([(hx - 62, hy - 70), (hx + 66, hy - 18)]), fill=SKIN)           # forehead below the hairline
        d.line(P([(hx - 30, hy - 100), (hx - 26, hy - 62)]), fill=HAIR_L, width=3 * s)   # the parting
        for k in range(5):
            d.arc(P([(hx - 24 + k * 16, hy - 98), (hx + 30 + k * 16, hy - 40)]), 200, 260, fill=(150, 142, 134), width=2 * s)
        # forehead lines (a lifetime of mild surprise)
        for k in range(2):
            d.arc(P([(hx - 34, hy - 58 + k * 9), (hx + 34, hy - 30 + k * 9)]), 200, 340, fill=SKIN_D, width=2 * s)
        # eyebrows, raised by `brow` (and a little worried by default)
        by = hy - 26 - brow * 8
        for side in (-1, 1):
            x0 = hx + side * 30
            d.line(P([(x0 - 16, by + 3 + side * 2), (x0 + 16, by - 1 - side * 2)]) if side < 0 else
                   P([(x0 - 16, by - 1 + 2), (x0 + 16, by + 3 + 2)]), fill=HAIR, width=5 * s)
        # eyes
        ey = hy + 2
        for side in (-1, 1):
            ex = hx + side * 30
            if blink > 0.5:
                d.arc(P([(ex - 9, ey - 5), (ex + 9, ey + 5)]), 20, 160, fill=(60, 40, 30), width=3 * s)
            else:
                d.ellipse(P([(ex - 9, ey - 7), (ex + 9, ey + 7)]), fill=(250, 250, 248))
                d.ellipse(P([(ex - 5 + sway * 0.3, ey - 5), (ex + 5 + sway * 0.3, ey + 5)]), fill=(92, 70, 46))
                d.ellipse(P([(ex - 2 + sway * 0.3, ey - 2), (ex + 2 + sway * 0.3, ey + 2)]), fill=(16, 16, 18))
                d.ellipse(P([(ex + 1, ey - 4), (ex + 3, ey - 2)]), fill=(255, 255, 255))
            d.arc(P([(ex - 13, ey + 2), (ex + 13, ey + 14)]), 20, 160, fill=SKIN_D, width=2 * s)   # tired lids below
        # thin wire glasses: small oval lenses
        for side in (-1, 1):
            ex = hx + side * 31
            d.ellipse(P([(ex - 21, ey - 15), (ex + 21, ey + 15)]), outline=WIRE, width=3 * s)
            d.line(P([(hx + side * 52, ey - 4), (hx + side * 72, ey - 8)]), fill=WIRE, width=2 * s)
        d.arc(P([(hx - 10, ey - 12), (hx + 10, ey + 2)]), 200, 340, fill=WIRE, width=2 * s)
        # nose: long and kind
        d.polygon(P([(hx - 2, hy + 4), (hx - 12, hy + 40), (hx + 10, hy + 42)]), fill=SKIN_D)
        d.ellipse(P([(hx - 13, hy + 32), (hx + 11, hy + 46)]), fill=(226, 176, 142))
        # mouth: visemes
        my = hy + 66
        m = max(0.0, min(1.0, mouth))
        wide = {'a': 22, 'e': 28, 'o': 13, 'm': 22}[shape]
        if m < 0.08 or shape == 'm':
            d.line(P([(hx - 22, my), (hx + 22, my - 1)]), fill=(130, 60, 56), width=3 * s)   # a polite, flat smile
            d.arc(P([(hx - 26, my - 6), (hx - 18, my + 4)]), 90, 200, fill=(130, 60, 56), width=2 * s)
        else:
            hgt = 3 + m * (20 if shape in 'ao' else 11)
            d.rounded_rectangle(P([(hx - wide, my - hgt * 0.45), (hx + wide, my + hgt * 0.75)]), radius=int(min(hgt, wide) * 0.5 * s),
                                fill=(84, 26, 30), outline=(150, 74, 70), width=2 * s)
            if hgt > 9:
                d.ellipse(P([(hx - wide * 0.55, my + hgt * 0.2), (hx + wide * 0.55, my + hgt * 0.75)]), fill=(196, 92, 100))
                d.rectangle(P([(hx - wide * 0.7, my - hgt * 0.45 + 1), (hx + wide * 0.7, my - hgt * 0.45 + 5)]), fill=(244, 240, 228))
        # laugh lines
        d.arc(P([(hx - 48, hy + 36), (hx - 24, hy + 82)]), 100, 200, fill=SKIN_D, width=2 * s)
        d.arc(P([(hx + 24, hy + 36), (hx + 48, hy + 82)]), 340, 80, fill=SKIN_D, width=2 * s)
        # the mug, on the desk edge in front of him (bottom left)
        im.paste(self.mug, (int(18 * s), int((H - 100) * s)), self.mug)
        d = ImageDraw.Draw(im)
        # --- gestures
        if gesture != 'none' and g > 0:
            e = g * g * (3 - 2 * g)
            if gesture == 'point':
                hx2, hy2 = W * 0.16 + (1 - e) * 40, H - 60 - e * 150
                d.line(P([(cx - 110, H), (hx2 + 10, hy2 + 40)]), fill=CARD, width=40 * s)
                self._hand(d, hx2, hy2, 'point', s)
            elif gesture == 'disk':
                hx2, hy2 = W * 0.70 - (1 - e) * 30, H - 30 - e * 170
                d.line(P([(cx + 110, H), (hx2 - 6, hy2 + 50)]), fill=CARD, width=40 * s)
                d.rectangle(P([(hx2 - 40, hy2 - 50), (hx2 + 40, hy2 + 30)]), fill=(40, 40, 46))
                d.rectangle(P([(hx2 - 22, hy2 - 50), (hx2 + 18, hy2 - 22)]), fill=(180, 184, 190))
                d.rectangle(P([(hx2 - 8, hy2 - 46), (hx2 + 4, hy2 - 26)]), fill=(40, 40, 46))
                d.rectangle(P([(hx2 - 30, hy2 - 12), (hx2 + 30, hy2 + 26)]), fill=(240, 236, 220))
                for k in range(3):
                    d.line(P([(hx2 - 24, hy2 - 2 + k * 9), (hx2 + 24, hy2 - 2 + k * 9)]), fill=(150, 160, 200), width=s)
                self._hand(d, hx2 + 6, hy2 + 34, 'grip', s)
            elif gesture == 'wave':
                hx2, hy2 = W * 0.70, H - 60 - e * 150
                d.line(P([(cx + 110, H), (hx2, hy2 + 40)]), fill=CARD, width=40 * s)
                self._hand(d, hx2 + math.sin(t * 7) * 7 * e, hy2, 'open', s)
            elif gesture == 'thumb':
                hx2, hy2 = W * 0.70, H - 60 - e * 130
                d.line(P([(cx + 110, H), (hx2, hy2 + 40)]), fill=CARD, width=40 * s)
                self._hand(d, hx2, hy2, 'thumb', s)
        return im.resize((W, H), Image.LANCZOS).convert('RGBA')

    @staticmethod
    def _hand(d, x, y, kind, s):
        P = lambda pts: [(px * s, py * s) for px, py in pts]
        d.rounded_rectangle(P([(x - 24, y), (x + 24, y + 44)]), radius=14 * s, fill=SKIN, outline=SKIN_D, width=2 * s)
        if kind == 'point':
            d.rounded_rectangle(P([(x - 20, y - 40), (x - 6, y + 6)]), radius=7 * s, fill=SKIN, outline=SKIN_D, width=2 * s)
        elif kind == 'open':
            for k in range(4):
                d.rounded_rectangle(P([(x - 22 + k * 12, y - 30 + abs(k - 1.5) * 4), (x - 12 + k * 12, y + 6)]), radius=5 * s,
                                    fill=SKIN, outline=SKIN_D, width=2 * s)
        elif kind == 'thumb':
            d.rounded_rectangle(P([(x - 8, y - 36), (x + 8, y + 6)]), radius=7 * s, fill=SKIN, outline=SKIN_D, width=2 * s)
        for k in range(3):
            d.line(P([(x - 14, y + 12 + k * 9), (x + 16, y + 12 + k * 9)]), fill=SKIN_D, width=2 * s)
        d.rectangle(P([(x - 22, y + 40), (x + 22, y + 52)]), fill=SHIRT)   # cuff


if __name__ == '__main__':
    if sys.argv[1] == 'sheet':
        if len(sys.argv) > 3: FONTDIR = sys.argv[3]
        Pz = Presenter()
        states = [dict(), dict(mouth=0.4), dict(mouth=1.0), dict(mouth=0.8, shape='o'), dict(mouth=0.7, shape='e'),
                  dict(blink=1), dict(brow=1, mouth=0.5), dict(gesture='point', g=1), dict(gesture='disk', g=1),
                  dict(gesture='wave', g=1, t=0.2), dict(gesture='thumb', g=1, mouth=0.3)]
        sheet = Image.new('RGB', (W * 4, H * 3), 'black')
        for i, st in enumerate(states):
            sheet.paste(Pz.draw(**st), ((i % 4) * W, (i // 4) * H))
        sheet.save(sys.argv[2])
