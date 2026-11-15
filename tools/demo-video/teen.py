#!/usr/bin/env python3
"""Kayleigh, the tour's narrator: an original teenage character (not based on any real person), filmed like a selfie
on a phone for her "My Family's Technology" project. Drawn from code: a vertical 9:16 picture in a generic phone frame
(no app logos), a little hand-held shake, a ring-light catchlight in her eyes, mouth shapes from the narration,
bored half-lidded eyes, an eye-roll, a glance down at her phone, and one real smile.

    from teen import TeenBox
    box = TeenBox(fontdir); im = box.image(state)     # state: mouth, shape, blink, gesture, g, t (as compose.py's)
    python3 teen.py sheet OUT.png [FONTDIR]
"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

PW, PH = 300, 534          # the picture (9:16)
BEZ = 12                    # the phone's frame
SS = 3
SKIN = (241, 205, 180)
SKIN_D = (214, 168, 140)
HAIR = (58, 40, 32)
HAIR_L = (92, 66, 50)
HOOD = (168, 170, 178)      # an oversized grey hoodie
HOOD_D = (134, 136, 146)


def _font(fd, size, bold=True):
    try:
        return ImageFont.truetype(os.path.join(fd, 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), size)
    except OSError:
        return ImageFont.load_default()


def _room():
    """Her bedroom wall: pastel paint, a string of fairy lights, a poster of a city at night (generic)."""
    s = SS
    im = Image.new('RGB', (PW * s, PH * s), (214, 196, 222))
    d = ImageDraw.Draw(im)
    for y in range(PH * s):
        u = y / (PH * s)
        d.line([(0, y), (PW * s, y)], fill=(int(220 - 30 * u), int(200 - 40 * u), int(228 - 20 * u)))
    # the poster: a night skyline under a pink-to-violet sky (city pop, obviously)
    px0, py0, px1, py1 = 168 * s, 40 * s, 286 * s, 196 * s
    for y in range(py0, py1):
        u = (y - py0) / (py1 - py0)
        d.line([(px0, y), (px1, y)], fill=(int(250 - 140 * u), int(140 - 90 * u), int(190 - 60 * u)))
    d.ellipse([214 * s, 92 * s, 254 * s, 132 * s], fill=(255, 220, 150))
    for k, (bx, bw, bh) in enumerate([(170, 18, 50), (190, 14, 74), (206, 20, 40), (228, 12, 88), (242, 22, 60), (266, 18, 46)]):
        d.rectangle([bx * s, (196 - bh) * s, (bx + bw) * s, 196 * s], fill=(40, 30, 70))
        for w in range(3, bh - 6, 9):
            if (w + k) % 2: d.rectangle([(bx + 4) * s, (196 - bh + w) * s, (bx + 7) * s, (196 - bh + w + 3) * s], fill=(255, 230, 140))
    d.rectangle([px0, py0, px1, py1], outline=(250, 250, 250), width=3 * s)
    # fairy lights along the top
    for k in range(12):
        x = 10 + k * 26; y = 16 + 8 * math.sin(k * 0.9)
        d.line([((x - 13) * s, (16 + 8 * math.sin((k - 1) * 0.9)) * s), (x * s, y * s)], fill=(90, 80, 70), width=s)
        glow = Image.new('L', im.size, 0)
        ImageDraw.Draw(glow).ellipse([(x - 6) * s, (y - 3) * s, (x + 6) * s, (y + 9) * s], fill=160)
        glow = glow.filter(ImageFilter.GaussianBlur(4 * s))
        im.paste(Image.new('RGB', im.size, (255, 226, 160)), (0, 0), glow)
        d = ImageDraw.Draw(im)
        d.ellipse([(x - 2.5) * s, y * s, (x + 2.5) * s, (y + 6) * s], fill=(255, 244, 200))
    return im


class Teen:
    def __init__(self):
        self.room = _room()

    def draw(self, mouth=0.0, shape='a', blink=0.0, gesture='none', g=0.0, t=0.0):
        s = SS
        im = self.room.copy()
        d = ImageDraw.Draw(im)
        P = lambda pts: [(x * s, y * s) for x, y in pts]
        e = g * g * (3 - 2 * g) if gesture != 'none' else 0.0
        smile = e if gesture == 'smile' else 0.0
        roll = e if gesture == 'eyeroll' else 0.0
        glance = e if gesture == 'phone' else 0.0
        tilt = math.sin(t * 0.6) * 3 + glance * 6
        hx, hy = PW / 2 - 10 + tilt, 250 + glance * 10
        # hair behind (long, past the shoulders)
        d.rounded_rectangle(P([(hx - 92, hy - 80), (hx + 92, hy + 210)]), radius=60 * s, fill=HAIR)
        # hoodie and shoulders
        d.polygon(P([(hx - 150, PH + 5), (hx - 120, hy + 140), (hx - 50, hy + 112), (hx + 50, hy + 112), (hx + 120, hy + 140), (hx + 150, PH + 5)]), fill=HOOD)
        d.ellipse(P([(hx - 62, hy + 100), (hx + 62, hy + 150)]), fill=HOOD_D)                      # the hood's neckline
        d.line(P([(hx - 22, hy + 146), (hx - 26, hy + 210)]), fill=(230, 230, 236), width=3 * s)     # drawstrings
        d.line(P([(hx + 22, hy + 146), (hx + 26, hy + 210)]), fill=(230, 230, 236), width=3 * s)
        d.rounded_rectangle(P([(hx - 24, hy + 70), (hx + 24, hy + 118)]), radius=10 * s, fill=SKIN_D)   # neck
        # face
        d.ellipse(P([(hx - 70, hy - 88), (hx + 70, hy + 96)]), fill=SKIN)
        # hair front: a centre part, curtain bangs
        d.chord(P([(hx - 78, hy - 104), (hx + 78, hy + 10)]), 180, 360, fill=HAIR)
        d.polygon(P([(hx - 4, hy - 96), (hx - 74, hy - 28), (hx - 78, hy + 40), (hx - 60, hy - 30)]), fill=HAIR)
        d.polygon(P([(hx + 4, hy - 96), (hx + 74, hy - 28), (hx + 78, hy + 40), (hx + 60, hy - 30)]), fill=HAIR)
        d.line(P([(hx, hy - 100), (hx + 2, hy - 64)]), fill=HAIR_L, width=2 * s)
        # small hoop earrings
        for side in (-1, 1):
            d.ellipse(P([(hx + side * 68 - 6, hy + 30), (hx + side * 68 + 6, hy + 44)]), outline=(230, 200, 110), width=2 * s)
        # brows: flat (bored), a little lifted when smiling
        by = hy - 26 - smile * 4
        for side in (-1, 1):
            d.line(P([(hx + side * 16, by), (hx + side * 44, by - 2)]), fill=HAIR, width=4 * s)
        # eyes: half-lidded, pupils up for the roll, down-right at the phone; a ring-light catchlight
        ey = hy + 2
        for side in (-1, 1):
            ex = hx + side * 30
            if blink > 0.5:
                d.arc(P([(ex - 13, ey - 4), (ex + 13, ey + 8)]), 200, 340, fill=(40, 26, 20), width=3 * s)
                continue
            if smile > 0.5:   # eyes that smile
                d.arc(P([(ex - 13, ey - 6), (ex + 13, ey + 10)]), 200, 340, fill=(40, 26, 20), width=4 * s)
                continue
            d.ellipse(P([(ex - 13, ey - 9), (ex + 13, ey + 9)]), fill=(252, 250, 250))
            pdx = glance * 5 + side * 0
            pdy = -roll * 7 + glance * 4
            d.ellipse(P([(ex - 7 + pdx, ey - 7 + pdy), (ex + 7 + pdx, ey + 7 + pdy)]), fill=(96, 64, 44))
            d.ellipse(P([(ex - 3 + pdx, ey - 3 + pdy), (ex + 3 + pdx, ey + 3 + pdy)]), fill=(14, 10, 10))
            d.arc(P([(ex - 4 + pdx, ey - 5 + pdy), (ex + 4 + pdx, ey + 3 + pdy)]), 200, 340, fill=(255, 255, 255), width=2 * s)  # ring light
            lid = 0.45 - roll * 0.25 - smile * 0.4      # how far the upper lid comes down (bored by default)
            d.chord(P([(ex - 14, ey - 11), (ex + 14, ey + 11)]), 180, 180 + 180, fill=SKIN) if False else None
            d.rectangle(P([(ex - 14, ey - 11), (ex + 14, ey - 11 + 22 * lid)]), fill=SKIN)
            d.line(P([(ex - 13, ey - 11 + 22 * lid), (ex + 13, ey - 11 + 22 * lid)]), fill=(40, 26, 20), width=3 * s)   # lash line
            d.line(P([(ex + side * 13, ey - 11 + 22 * lid), (ex + side * 18, ey - 14 + 22 * lid)]), fill=(40, 26, 20), width=2 * s)
        # nose, blush
        d.line(P([(hx + 2, hy + 14), (hx - 3, hy + 32), (hx + 4, hy + 34)]), fill=SKIN_D, width=2 * s)
        for side in (-1, 1):
            b = Image.new('L', im.size, 0)
            ImageDraw.Draw(b).ellipse(P([(hx + side * 44 - 14, hy + 28), (hx + side * 44 + 14, hy + 44)]), fill=70 + int(smile * 60))
            im.paste(Image.new('RGB', im.size, (240, 150, 150)), (0, 0), b.filter(ImageFilter.GaussianBlur(5 * s)))
        d = ImageDraw.Draw(im)
        # mouth: glossy lips; visemes; a real smile for city pop
        my = hy + 56
        m = max(0.0, min(1.0, mouth))
        LIP = (206, 110, 116)
        if smile > 0.5 and m < 0.3:
            d.chord(P([(hx - 22, my - 12), (hx + 22, my + 12)]), 0, 180, fill=(250, 246, 240), outline=LIP, width=3 * s)
        elif m < 0.08 or shape == 'm':
            d.line(P([(hx - 15, my), (hx + 15, my)]), fill=LIP, width=5 * s)
            d.line(P([(hx - 8, my + 4), (hx + 8, my + 4)]), fill=(232, 160, 160), width=2 * s)   # gloss
        else:
            wide = {'a': 16, 'e': 20, 'o': 10, 'm': 16}[shape]
            hgt = 3 + m * (14 if shape in 'ao' else 8)
            d.rounded_rectangle(P([(hx - wide, my - hgt * 0.4), (hx + wide, my + hgt * 0.7)]), radius=int(min(hgt, wide) * 0.5 * s),
                                fill=(110, 40, 46), outline=LIP, width=3 * s)
            if hgt > 7:
                d.rectangle(P([(hx - wide * 0.6, my - hgt * 0.4 + 2), (hx + wide * 0.6, my - hgt * 0.4 + 5)]), fill=(248, 244, 236))
        # the phone she glances at: its corner rises into frame
        if glance > 0:
            yb = PH - glance * 70
            d.rounded_rectangle(P([(200, yb), (290, yb + 160)]), radius=12 * s, fill=(30, 30, 34))
            d.rounded_rectangle(P([(206, yb + 8), (284, yb + 150)]), radius=8 * s, fill=(120, 170, 220))
            d.rounded_rectangle(P([(188, yb + 30), (214, yb + 90)]), radius=10 * s, fill=SKIN)   # her thumb
        if gesture == 'wave' and e > 0:
            x2, y2 = 236 + math.sin(t * 8) * 6 * e, PH - e * 170
            d.rounded_rectangle(P([(x2 - 22, y2), (x2 + 22, y2 + 44)]), radius=14 * s, fill=SKIN)
            for k in range(4):
                d.rounded_rectangle(P([(x2 - 20 + k * 11, y2 - 26 + abs(k - 1.5) * 4), (x2 - 11 + k * 11, y2 + 6)]), radius=5 * s, fill=SKIN)
            d.rectangle(P([(x2 - 26, min(PH, y2 + 40)), (x2 + 26, PH)]), fill=HOOD)
        if gesture == 'peace' and e > 0:
            x2, y2 = 70, PH - e * 160
            d.rounded_rectangle(P([(x2 - 20, y2), (x2 + 20, y2 + 40)]), radius=12 * s, fill=SKIN)
            d.rounded_rectangle(P([(x2 - 16, y2 - 40), (x2 - 4, y2 + 6)]), radius=6 * s, fill=SKIN)
            d.rounded_rectangle(P([(x2 + 2, y2 - 38), (x2 + 14, y2 + 6)]), radius=6 * s, fill=SKIN)
            d.rectangle(P([(x2 - 24, min(PH, y2 + 36)), (x2 + 24, PH)]), fill=HOOD)
        return im.resize((PW, PH), Image.LANCZOS)


class TeenBox:
    """The phone: a generic black frame around the picture, a status bar, a recording dot and timer, a hand-held shake."""
    def __init__(self, fontdir):
        self.T = Teen()
        self.fd = fontdir
        self.size = (PW + 2 * BEZ, PH + 2 * BEZ + 40)
        self.cache = {}

    def image(self, st):
        key = (round(st['mouth'] * 6), st['shape'], st['blink'] > 0.5, st['gesture'], round(st['g'] * 8), round(st['t'] * 6) % 60)
        pic = self.cache.get(key)
        if pic is None:
            pic = self.T.draw(mouth=key[0] / 6, shape=key[1], blink=1.0 if key[2] else 0.0, gesture=key[3], g=key[4] / 8, t=key[5] / 6)
            if len(self.cache) > 600: self.cache.clear()
            self.cache[key] = pic
        w, h = self.size
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, w - 1, PH + 2 * BEZ - 1], radius=34, fill=(16, 16, 18, 255), outline=(70, 70, 76, 255), width=2)
        # hand-held: a small drift (whole pixels, inside the frame)
        t = st['t']
        dx = int(round(2.2 * math.sin(t * 2.3) + 1.2 * math.sin(t * 5.1)))
        dy = int(round(2.0 * math.sin(t * 1.9 + 1) + 1.0 * math.sin(t * 4.3)))
        win = Image.new('RGBA', (PW, PH))
        win.paste(pic.crop((max(0, dx), max(0, dy), PW + min(0, dx), PH + min(0, dy))), (max(0, -dx), max(0, -dy)))
        mask = Image.new('L', (PW, PH), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, PW - 1, PH - 1], radius=24, fill=255)
        im.paste(win, (BEZ, BEZ), mask)
        # status bar and the recording indicator (generic)
        f = _font(self.fd, 14); fb = _font(self.fd, 13)
        d.text((BEZ + 22, BEZ + 8), '4:12', font=f, fill=(255, 255, 255))
        for k in range(4):
            d.rectangle([w - BEZ - 70 + k * 6, BEZ + 18 - k * 3, w - BEZ - 66 + k * 6, BEZ + 21], fill=(255, 255, 255))
        d.rounded_rectangle([w - BEZ - 40, BEZ + 9, w - BEZ - 18, BEZ + 20], radius=3, outline=(255, 255, 255), width=1)
        d.rectangle([w - BEZ - 38, BEZ + 11, w - BEZ - 26, BEZ + 18], fill=(255, 255, 255))
        secs = int(t)
        if int(t * 2) % 2 == 0: d.ellipse([w // 2 - 34, PH + BEZ - 32, w // 2 - 24, PH + BEZ - 22], fill=(235, 40, 40))
        d.text((w // 2 - 18, PH + BEZ - 34), f'{secs // 60:02d}:{secs % 60:02d}', font=fb, fill=(255, 255, 255))
        # the name sticker under the phone, school-project style
        d.rounded_rectangle([18, PH + 2 * BEZ + 4, w - 18, h - 2], radius=8, fill=(255, 236, 120, 255), outline=(40, 40, 40, 255), width=2)
        d.text((w // 2, PH + 2 * BEZ + 20), 'KAYLEIGH · PERIOD 4', font=_font(self.fd, 16), fill=(30, 30, 30), anchor='mm')
        return im


if __name__ == '__main__':
    if sys.argv[1] == 'sheet':
        fd = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'design', 'brand', 'sndwave1993', 'fonts')
        B = TeenBox(fd)
        base = dict(mouth=0.0, shape='a', blink=0.0, gesture='none', g=0.0, t=1.0)
        states = [{}, dict(mouth=0.5), dict(mouth=1.0), dict(mouth=0.8, shape='o'), dict(blink=1),
                  dict(gesture='eyeroll', g=1), dict(gesture='phone', g=1), dict(gesture='smile', g=1),
                  dict(gesture='smile', g=1, mouth=0.6), dict(gesture='wave', g=1, t=0.3), dict(gesture='peace', g=1)]
        w, h = B.size
        sheet = Image.new('RGB', (w * 6, h * 2), (60, 60, 70))
        for i, st in enumerate(states):
            ss = dict(base); ss.update(st)
            im = B.image(ss)
            sheet.paste(im, ((i % 6) * w, (i // 6) * h), im)
        sheet.save(sys.argv[2])
