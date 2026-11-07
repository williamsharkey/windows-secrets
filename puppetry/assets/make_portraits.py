#!/usr/bin/env python3
"""Text-art portraits for Notepad (Lucida Console 4pt = 3x5 px cells), inked
with the letter's own characters, in order."""
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw, ImageFont
import sys
COLS, ROWS = 175, 100
letter = open('letter.txt').read()
ink = [c for c in letter if not c.isspace()]

def art(src, crop, name, channel=None, contrast=1.6, gamma=1.0):
    im = Image.open(src).convert('RGB')
    W, H = im.size
    im = im.crop((int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H)))
    im = im.getchannel(channel) if channel else im.convert('L')
    target = (COLS * 3) / (ROWS * 5)
    w, h = im.size
    if w / h > target:
        nw = int(h * target); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target); im = im.crop((0, 0, w, nh))
    im = ImageOps.autocontrast(im, cutoff=1)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=140))
    im = im.resize((COLS, ROWS), Image.LANCZOS)
    px = im.load(); k = 0; lines = []
    for y in range(ROWS):
        row = ''
        for x in range(COLS):
            v = (px[x, y] / 255.0) ** gamma
            if v < 0.30: c = ink[k % len(ink)].upper(); k += 1
            elif v < 0.52: c = ink[k % len(ink)].lower(); k += 1
            elif v < 0.70: c = '.,:;\'-'[k % 6]; k += 1
            else: c = ' '
            row += c
        lines.append(row.rstrip())
    open('portrait-%s.txt' % name, 'w').write('\n'.join(lines))
    pv = Image.new('L', (COLS * 3, ROWS * 5), 255); d = ImageDraw.Draw(pv)
    f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 5)
    for y, l in enumerate(lines): d.text((0, y * 5 - 1), l, fill=0, font=f)
    return pv

pvs = [art('mother.jpg', (0.0, 0.03, 1.0, 0.80), 'mother'),
       art('worker.jpg', (0.36, 0.03, 0.78, 0.95), 'worker', contrast=1.9),
       art('sorrow.jpg', (0.20, 0.02, 0.86, 0.58), 'sorrow', channel='R', contrast=2.1, gamma=0.85)]
W = Image.new('L', (sum(p.width for p in pvs) + 20, pvs[0].height), 255); x = 0
for p in pvs: W.paste(p, (x, 0)); x += p.width + 10
W.save(sys.argv[1] if len(sys.argv) > 1 else 'preview.png')
