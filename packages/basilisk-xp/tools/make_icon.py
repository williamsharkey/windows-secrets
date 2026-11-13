#!/usr/bin/env python3
"""Draw BASILISK's icon (a basilisk's eye: emerald iris, slit pupil) and write icon.png, .ico and .icns.

    make_icon.py OUT_DIR
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

S = 1024


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def icon():
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    # squircle tile, charcoal with a faint top light
    tile = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    m = Image.new('L', (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle((40, 40, S - 40, S - 40), radius=210, fill=255)
    grad = Image.new('RGBA', (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        gd.line((0, y, S, y), fill=lerp((38, 42, 48, 255), (14, 15, 18, 255), y / S))
    tile.paste(grad, (0, 0), m)
    im = Image.alpha_composite(im, tile)
    cx, cy = S / 2, S / 2 + 6
    # almond eye shape
    eye = Image.new('L', (S, S), 0)
    ed = ImageDraw.Draw(eye)
    w, h = 380, 230
    pts = []
    for i in range(181):
        a = math.pi * i / 180
        pts.append((cx - w * math.cos(a), cy - h * math.sin(a) ** 1.25))
    for i in range(181):
        a = math.pi * i / 180
        pts.append((cx + w * math.cos(a), cy + h * math.sin(a) ** 1.25))
    ed.polygon(pts, fill=255)
    # iris: radial emerald to gold
    iris = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    idr = ImageDraw.Draw(iris)
    R = 220
    for r in range(R, 0, -2):
        t = r / R
        col = lerp((236, 214, 92, 255), (36, 168, 104, 255), t ** 0.7) if t < 0.95 else (18, 92, 58, 255)
        idr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    # fine radial fibres
    for i in range(90):
        a = i * math.tau / 90
        idr.line((cx + 70 * math.cos(a), cy + 70 * math.sin(a), cx + 205 * math.cos(a), cy + 205 * math.sin(a)),
                 fill=(20, 110, 70, 70), width=4)
    # slit pupil
    pd = ImageDraw.Draw(iris)
    pd.ellipse((cx - 46, cy - 205, cx + 46, cy + 205), fill=(8, 10, 9, 255))
    eye_rgba = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    eye_rgba.paste(iris, (0, 0), eye)
    # rim
    rim = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(rim).polygon(pts, outline=(10, 12, 12, 255), width=14)
    im = Image.alpha_composite(im, eye_rgba)
    im = Image.alpha_composite(im, rim)
    # highlight
    hl = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse((cx + 70, cy - 150, cx + 140, cy - 80), fill=(255, 255, 255, 210))
    hl = hl.filter(ImageFilter.GaussianBlur(3))
    return Image.alpha_composite(im, hl)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    im = icon()
    im.save(os.path.join(out, 'icon.png'))
    im.resize((256, 256), Image.LANCZOS).save(os.path.join(out, 'icon-256.png'))
    im.save(os.path.join(out, 'basilisk.ico'), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128),
                                                      (256, 256)])
    im.save(os.path.join(out, 'basilisk.icns'))
    print('icons in', out)


if __name__ == '__main__':
    main()
