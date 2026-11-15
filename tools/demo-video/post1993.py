#!/usr/bin/env python3
"""The establishing shot's period look: one 64-colour palette for the whole sequence (median cut over sample frames),
a 4x4 ordered (Bayer) dither, then a whole-number upscale (nearest neighbour) to 1920x1080.

    post1993.py IN_DIR OUT_DIR [--colors 64] [--scale 3]
"""
import argparse, os
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--colors', type=int, default=64); ap.add_argument('--scale', type=int, default=3)
a = ap.parse_args()
files = sorted(f for f in os.listdir(a.src) if f.endswith('.png'))
os.makedirs(a.out, exist_ok=True)
sample = [Image.open(os.path.join(a.src, f)).convert('RGB') for f in files[::max(1, len(files) // 8)]]
w, h = sample[0].size
mont = Image.new('RGB', (w, h * len(sample)))
for k, im in enumerate(sample): mont.paste(im, (0, k * h))
pal = np.array(mont.quantize(a.colors, method=Image.Quantize.MEDIANCUT).getpalette()[:a.colors * 3], np.float32).reshape(-1, 3)
bayer = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 - 0.5)
thr = np.tile(bayer, (h // 4 + 1, w // 4 + 1))[:h, :w, None] * 40.0
for f in files:
    px = np.asarray(Image.open(os.path.join(a.src, f)).convert('RGB'), np.float32) + thr
    flat = px.reshape(-1, 3)
    best = np.zeros(len(flat), np.int32); bd = np.full(len(flat), 1e12, np.float32)
    for k, c in enumerate(pal):
        d = ((flat - c) ** 2 * (0.3, 0.59, 0.11)).sum(1)
        m = d < bd; bd[m] = d[m]; best[m] = k
    q = Image.fromarray(pal[best].reshape(h, w, 3).astype(np.uint8))
    q.resize((w * a.scale, h * a.scale), Image.NEAREST).save(os.path.join(a.out, f))
print(len(files), 'frames,', a.colors, 'colours')
