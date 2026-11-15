#!/usr/bin/env python3
"""The Grok Imagine stills as pixel art, with PixelOE (github.com/KohakuBlueleaf/PixelOE, Apache-2.0; its
contrast-aware downscale and outline pass gave the cleanest faces of the converters tried: see README.md).

    pixel_ai.py GROKDIR        writes GROKDIR/px/<name>.png at their small size (the edit scales them by whole numbers)

Host stills: cropped to the box's shape (420 x 470) and reduced to 140 x 157 (3x in the box). Backdrops: 320 x 180
(6x = 1920 x 1080). 24 colours, k-means.
"""
import os, sys
import cv2
from pixeloe.legacy.pixelize import pixelize

d = sys.argv[1]
os.makedirs(os.path.join(d, 'px'), exist_ok=True)
for name in sorted(os.listdir(d)):
    if not name.endswith('.png'): continue
    img = cv2.imread(os.path.join(d, name))
    h, w = img.shape[:2]
    if name.startswith(('harlan', 'clement')):
        cw = int(h * 420 / 470)
        img = img[:, (w - cw) // 2:(w - cw) // 2 + cw]
        size = (140, 157)
    else:
        size = (320, 180)
    # PixelOE works on a square-ish target size; reduce to the area, then fit the exact size
    out = pixelize(img, mode='contrast', target_size=max(size), patch_size=6, thickness=2, colors=24, no_upscale=True)
    out = cv2.resize(out, size, interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(os.path.join(d, 'px', name), out)
    print(name, out.shape)
