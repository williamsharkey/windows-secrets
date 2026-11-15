#!/usr/bin/env python3
"""Harlan Pettibone, the tour's host: an original character drawn from code (no photo, no reference person).
A retired gentleman in a cardigan and bow tie, with big glasses, a bald crown and white side hair, clean-shaven.

    from presenter import Presenter
    P = Presenter(); img = P.draw(mouth=0.6, shape='a', blink=0, brow=0.3, gesture='point', g=1.0, t=12.3)

`draw` returns an RGBA image of the inner picture (W x H). It is drawn at SS x the size and reduced, for smooth edges.
    python3 presenter.py sheet OUT.png      a contact sheet of mouths, blinks and gestures
"""
import math, sys
from PIL import Image, ImageDraw, ImageFilter

W, H = 420, 470
SS = 3

SKIN = (240, 196, 160)
SKIN_D = (214, 160, 124)
CHEEK = (236, 150, 140)
HAIR = (236, 236, 232)
HAIR_D = (196, 196, 192)
CARD = (122, 46, 58)          # cardigan
CARD_D = (92, 32, 44)
SHIRT = (214, 228, 242)
BOW = (32, 66, 132)
FRAME = (70, 48, 34)          # glasses
BG_TOP = (36, 84, 140)
BG_BOT = (12, 34, 70)


def _bg():
    """The studio: a blue sweep, a soft spotlight, a bookshelf line and a potted plant (all invented)."""
    im = Image.new('RGB', (W * SS, H * SS))
    d = ImageDraw.Draw(im)
    for y in range(H * SS):
        u = y / (H * SS)
        c = tuple(int(BG_TOP[k] * (1 - u) + BG_BOT[k] * u) for k in range(3))
        d.line([(0, y), (W * SS, y)], fill=c)
    glow = Image.new('L', (W * SS, H * SS), 0)
    ImageDraw.Draw(glow).ellipse([W * SS * 0.12, H * SS * 0.05, W * SS * 0.88, H * SS * 0.85], fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(40 * SS))
    im = Image.composite(Image.new('RGB', im.size, (120, 170, 220)), im, glow)
    d = ImageDraw.Draw(im)
    s = SS
    # shelf on the left with three book spines
    d.rectangle([0, 150 * s, 70 * s, 156 * s], fill=(70, 50, 40))
    for i, (bw, bh, c) in enumerate([(14, 46, (150, 60, 50)), (11, 40, (60, 110, 80)), (16, 50, (200, 170, 90))]):
        x = 8 * s + sum(b[0] + 3 for b in [(14,), (11,), (16,)][:i]) * s
        d.rectangle([x, (150 - bh) * s, x + bw * s, 150 * s], fill=c)
    # a plant on the right
    d.rectangle([352 * s, 210 * s, 392 * s, 250 * s], fill=(176, 92, 60))
    for a in range(-60, 61, 24):
        r = math.radians(a - 90)
        x0, y0 = 372 * s, 212 * s
        d.ellipse([x0 + math.cos(r) * 46 * s - 12 * s, y0 + math.sin(r) * 50 * s - 22 * s,
                   x0 + math.cos(r) * 46 * s + 12 * s, y0 + math.sin(r) * 50 * s + 22 * s], fill=(52, 128, 76))
    return im


class Presenter:
    def __init__(self):
        self.bg = _bg()

    def draw(self, mouth=0.0, shape='a', blink=0.0, brow=0.0, gesture='none', g=0.0, t=0.0, tilt=0.0):
        s = SS
        im = self.bg.copy()
        d = ImageDraw.Draw(im)
        # gentle idle sway and a breath
        sway = math.sin(t * 0.9) * 3 + tilt
        breath = math.sin(t * 1.7) * 1.5
        cx = W / 2 + sway * 0.5
        hx, hy = W / 2 + sway, 196 + breath * 0.5          # head centre
        P = lambda pts: [(x * s, y * s) for x, y in pts]
        # --- body: cardigan over a shirt, bow tie
        top = 336 + breath
        d.polygon(P([(cx - 150, H + 5), (cx - 138, top + 40), (cx - 96, top + 2), (cx - 34, top - 6), (cx + 34, top - 6),
                     (cx + 96, top + 2), (cx + 138, top + 40), (cx + 150, H + 5)]), fill=CARD)
        d.polygon(P([(cx - 36, top - 6), (cx + 36, top - 6), (cx, top + 110)]), fill=SHIRT)            # shirt V
        d.polygon(P([(cx - 36, top - 6), (cx - 6, top + 112), (cx - 18, top + 116), (cx - 52, top + 4)]), fill=CARD_D)
        d.polygon(P([(cx + 36, top - 6), (cx + 6, top + 112), (cx + 18, top + 116), (cx + 52, top + 4)]), fill=CARD_D)
        for k in range(3):
            by = top + 132 + k * 34
            d.ellipse(P([(cx - 5, by - 5), (cx + 5, by + 5)]), fill=(230, 214, 170))
        d.polygon(P([(cx - 30, top - 10), (cx - 6, top + 8), (cx - 30, top + 22)]), fill=SHIRT, outline=(170, 180, 196))   # collar
        d.polygon(P([(cx + 30, top - 10), (cx + 6, top + 8), (cx + 30, top + 22)]), fill=SHIRT, outline=(170, 180, 196))
        # neck
        d.rounded_rectangle(P([(hx - 32, hy + 60), (hx + 32, top + 4)]), radius=10 * s, fill=SKIN_D)
        # bow tie
        bty = top + 10
        d.polygon(P([(cx - 30, bty - 13), (cx - 4, bty - 3), (cx - 4, bty + 3), (cx - 30, bty + 13)]), fill=BOW)
        d.polygon(P([(cx + 30, bty - 13), (cx + 4, bty - 3), (cx + 4, bty + 3), (cx + 30, bty + 13)]), fill=BOW)
        d.ellipse(P([(cx - 7, bty - 7), (cx + 7, bty + 7)]), fill=(52, 92, 168))
        for k in (-18, 18):
            d.ellipse(P([(cx + k - 2, bty - 2), (cx + k + 2, bty + 2)]), fill=(220, 220, 240))     # polka dots
        # --- head
        d.ellipse(P([(hx - 92, hy - 6), (hx - 66, hy + 40)]), fill=SKIN_D)        # ears
        d.ellipse(P([(hx + 66, hy - 6), (hx + 92, hy + 40)]), fill=SKIN_D)
        d.ellipse(P([(hx - 80, hy - 100), (hx + 80, hy + 96)]), fill=SKIN)
        # side hair, white, tufted
        for side in (-1, 1):
            for k in range(5):
                ox = side * (70 + (k % 2) * 6)
                oy = -40 + k * 16
                d.ellipse(P([(hx + ox - 16, hy + oy - 13), (hx + ox + 16, hy + oy + 13)]), fill=HAIR if k % 2 else HAIR_D)
        d.arc(P([(hx - 40, hy - 104), (hx + 30, hy - 60)]), 200, 330, fill=HAIR_D, width=2 * s)      # a last few strands
        d.arc(P([(hx - 28, hy - 102), (hx + 44, hy - 62)]), 210, 320, fill=HAIR_D, width=2 * s)
        d.ellipse(P([(hx - 30, hy - 86), (hx + 6, hy - 70)]), fill=(250, 220, 196))                     # shine on the crown
        # cheeks
        for side in (-1, 1):
            c = Image.new('L', im.size, 0)
            ImageDraw.Draw(c).ellipse(P([(hx + side * 50 - 18, hy + 28), (hx + side * 50 + 18, hy + 50)]), fill=110)
            c = c.filter(ImageFilter.GaussianBlur(6 * s))
            im.paste(Image.new('RGB', im.size, CHEEK), (0, 0), c)
        d = ImageDraw.Draw(im)
        # eyebrows (white, bushy), raised by `brow`
        by = hy - 30 - brow * 8
        for side in (-1, 1):
            x0 = hx + side * 34
            d.polygon(P([(x0 - 22, by + 4 - side * 0), (x0 - 8, by - 6), (x0 + 12, by - 5), (x0 + 24, by + 3), (x0 + 8, by + 1), (x0 - 10, by + 2)]),
                      fill=HAIR)
        # eyes behind the glasses
        ey = hy + 2
        for side in (-1, 1):
            ex = hx + side * 34
            if blink > 0.5:
                d.arc(P([(ex - 10, ey - 6), (ex + 10, ey + 6)]), 20, 160, fill=(60, 40, 30), width=3 * s)
            else:
                d.ellipse(P([(ex - 11, ey - 9), (ex + 11, ey + 9)]), fill=(250, 250, 248))
                d.ellipse(P([(ex - 6 + sway * 0.3, ey - 6), (ex + 6 + sway * 0.3, ey + 6)]), fill=(70, 96, 120))
                d.ellipse(P([(ex - 3 + sway * 0.3, ey - 3), (ex + 3 + sway * 0.3, ey + 3)]), fill=(20, 20, 24))
                d.ellipse(P([(ex + 1, ey - 5), (ex + 4, ey - 2)]), fill=(255, 255, 255))
        # glasses: big rounded rectangles, a bridge, temples
        for side in (-1, 1):
            ex = hx + side * 36
            d.rounded_rectangle(P([(ex - 30, ey - 24), (ex + 30, ey + 22)]), radius=14 * s, outline=FRAME, width=5 * s)
            lens = Image.new('L', im.size, 0)
            ImageDraw.Draw(lens).polygon(P([(ex - 22, ey - 20), (ex - 8, ey - 20), (ex - 22, ey + 2)]), fill=70)
            im.paste(Image.new('RGB', im.size, (255, 255, 255)), (0, 0), lens)
            d = ImageDraw.Draw(im)
            d.line(P([(hx + side * 66, ey - 12), (hx + side * 80, ey - 6)]), fill=FRAME, width=4 * s)
        d.arc(P([(hx - 10, ey - 18), (hx + 10, ey - 2)]), 200, 340, fill=FRAME, width=4 * s)
        # nose
        d.ellipse(P([(hx - 13, hy + 22), (hx + 13, hy + 46)]), fill=SKIN_D)
        d.ellipse(P([(hx - 10, hy + 20), (hx + 9, hy + 40)]), fill=(246, 206, 172))
        # mouth: visemes from openness and shape
        my = hy + 66
        m = max(0.0, min(1.0, mouth))
        wide = {'a': 26, 'e': 32, 'o': 15, 'm': 26}[shape]
        if m < 0.08 or shape == 'm':
            d.arc(P([(hx - 26, my - 14), (hx + 26, my + 8)]), 20, 160, fill=(120, 50, 50), width=4 * s)   # a closed smile
        else:
            hgt = 4 + m * (22 if shape in 'ao' else 12)
            d.rounded_rectangle(P([(hx - wide, my - hgt * 0.45), (hx + wide, my + hgt * 0.75)]), radius=int(min(hgt, wide) * 0.5 * s),
                                fill=(90, 24, 30), outline=(150, 70, 70), width=2 * s)
            if hgt > 9:
                d.ellipse(P([(hx - wide * 0.55, my + hgt * 0.2), (hx + wide * 0.55, my + hgt * 0.75)]), fill=(200, 90, 100))   # tongue
                d.rectangle(P([(hx - wide * 0.7, my - hgt * 0.45 + 1), (hx + wide * 0.7, my - hgt * 0.45 + 5)]), fill=(246, 244, 236))  # teeth
        # --- the right hand (his left on screen): gestures
        if gesture != 'none' and g > 0:
            e = g * g * (3 - 2 * g)
            if gesture == 'point':      # index finger up and towards the screen (to his right = image left)
                hx2, hy2 = W * 0.18 + (1 - e) * 40, H - 40 - e * 150
                self._hand(d, hx2, hy2, 'point', s)
                d.line(P([(cx - 120, H), (hx2 + 10, hy2 + 40)]), fill=CARD, width=40 * s)
                self._hand(d, hx2, hy2, 'point', s)
            elif gesture == 'disk':     # holds up a 3.5-inch diskette (blank label)
                hx2, hy2 = W * 0.80 - (1 - e) * 30, H - 30 - e * 170
                d.line(P([(cx + 120, H), (hx2 - 6, hy2 + 50)]), fill=CARD, width=40 * s)
                d.rectangle(P([(hx2 - 40, hy2 - 50), (hx2 + 40, hy2 + 30)]), fill=(40, 40, 46))
                d.rectangle(P([(hx2 - 22, hy2 - 50), (hx2 + 18, hy2 - 22)]), fill=(180, 184, 190))
                d.rectangle(P([(hx2 - 8, hy2 - 46), (hx2 + 4, hy2 - 26)]), fill=(40, 40, 46))
                d.rectangle(P([(hx2 - 30, hy2 - 12), (hx2 + 30, hy2 + 26)]), fill=(240, 236, 220))
                for k in range(3):
                    d.line(P([(hx2 - 24, hy2 - 2 + k * 9), (hx2 + 24, hy2 - 2 + k * 9)]), fill=(150, 160, 200), width=s)
                self._hand(d, hx2 + 6, hy2 + 34, 'grip', s)
            elif gesture == 'wave':
                hx2, hy2 = W * 0.80, H - 40 - e * 160
                d.line(P([(cx + 120, H), (hx2, hy2 + 40)]), fill=CARD, width=40 * s)
                self._hand(d, hx2 + math.sin(t * 9) * 8 * e, hy2, 'open', s)
            elif gesture == 'thumb':
                hx2, hy2 = W * 0.80, H - 40 - e * 140
                d.line(P([(cx + 120, H), (hx2, hy2 + 40)]), fill=CARD, width=40 * s)
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
        Pz = Presenter()
        states = [dict(), dict(mouth=0.4), dict(mouth=1.0), dict(mouth=0.8, shape='o'), dict(mouth=0.7, shape='e'),
                  dict(blink=1), dict(brow=1, mouth=0.5), dict(gesture='point', g=1), dict(gesture='disk', g=1),
                  dict(gesture='wave', g=1, t=0.2), dict(gesture='thumb', g=1, mouth=0.3)]
        sheet = Image.new('RGB', (W * 4, H * 3), 'black')
        for i, st in enumerate(states):
            sheet.paste(Pz.draw(**st), ((i % 4) * W, (i // 4) * H))
        sheet.save(sys.argv[2])
