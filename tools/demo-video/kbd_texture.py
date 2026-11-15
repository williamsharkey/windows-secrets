#!/usr/bin/env python3
"""The keyboard's top-down texture for scene1993.py: every keycap of keyboard101.py drawn at P pixels per key unit,
beige caps, darker modifiers, black legends (DejaVu Sans, the Helvetica-like caps of the period), no logo.

    kbd_texture.py FONTDIR OUT.png [P]
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyboard101 import keys, WIDTH, DEPTH

fd, out = sys.argv[1], sys.argv[2]
P = int(sys.argv[3]) if len(sys.argv) > 3 else 64
im = Image.new('RGB', (int(WIDTH * P), int(DEPTH * P)), (150, 142, 120))
d = ImageDraw.Draw(im)
big = ImageFont.truetype(os.path.join(fd, 'DejaVuSans-Bold.ttf'), int(P * 0.44))
mid = ImageFont.truetype(os.path.join(fd, 'DejaVuSans-Bold.ttf'), int(P * 0.31))
small = ImageFont.truetype(os.path.join(fd, 'DejaVuSans-Bold.ttf'), int(P * 0.2))
for x, y, w, h, leg, dark in keys():
    x0, y0, x1, y1 = x * P + 3, y * P + 3, (x + w) * P - 3, (y + h) * P - 3
    cap = (150, 146, 130) if dark else (206, 200, 180)
    d.rounded_rectangle([x0, y0, x1, y1], radius=int(P * 0.12), fill=cap, outline=(110, 104, 90), width=2)
    d.rounded_rectangle([x0 + P * 0.1, y0 + P * 0.08, x1 - P * 0.1, y1 - P * 0.16], radius=int(P * 0.1), fill=tuple(min(255, c + 10) for c in cap))
    ink = (8, 8, 8)
    lines = leg.split('\n')
    if len(lines) == 2:   # shifted symbol above, base below
        f = mid if all(len(l) <= 2 for l in lines) else small
        d.text((x0 + P * 0.16, y0 + P * 0.1), lines[0], font=f, fill=ink)
        d.text((x0 + P * 0.16, y0 + P * 0.48), lines[1], font=f, fill=ink)
    elif leg:
        f = big if len(leg) <= 2 else (mid if len(leg) <= 3 else small)
        d.text((x0 + P * 0.16, y0 + P * 0.1), leg, font=f, fill=ink)
im.save(out)
print(im.size, len(keys()), 'keys')
