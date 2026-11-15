#!/usr/bin/env python3
"""Pixel art from a picture (the Grok Imagine stills): downscale, quantise, dither, outline, whole-number upscale.

    pixelize.py IN.png OUT.png --width 140 [--palette vga16|win256|adaptive:N|kit] [--dither fs|bayer|none]
                [--outline] [--scale 3] [--crop x0,y0,x1,y1]

- Downscale: area averaging (Pillow's reduce/box) to `width` pixels, a mild unsharp to keep edges.
- Palette: `vga16` (the 16 VGA colours, as Windows 3.1 draws), `win256` (16 VGA + a 6x6x6 cube + greys: an
  8-bit Windows look), `kit` (the SNDWAVE1993 brand colours + VGA16), or `adaptive:N` (median cut, N colours).
- Dither: Floyd-Steinberg error diffusion (`fs`) or an ordered 4x4 Bayer matrix (`bayer`), in linear-ish RGB.
- Outline: a one-pixel dark line where the luminance edge is strong (cleans the silhouette at low resolution).
- Upscale: nearest neighbour by `scale`.
"""
import argparse, json, os
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
VGA16 = ['#000000', '#800000', '#008000', '#808000', '#000080', '#800080', '#008080', '#c0c0c0',
         '#808080', '#ff0000', '#00ff00', '#ffff00', '#0000ff', '#ff00ff', '#00ffff', '#ffffff']


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))


def palette(name, img):
    if name == 'vga16':
        return np.array([hexrgb(c) for c in VGA16], np.float32)
    if name == 'win256':
        cube = [(r, g, b) for r in (0, 51, 102, 153, 204, 255) for g in (0, 51, 102, 153, 204, 255) for b in (0, 51, 102, 153, 204, 255)]
        greys = [(v, v, v) for v in range(8, 256, 12)]
        return np.array([hexrgb(c) for c in VGA16] + cube + greys, np.float32)
    if name == 'kit':
        p = os.path.join(HERE, '..', '..', 'design', 'brand', 'sndwave1993', 'palette', 'palette.json')
        j = json.load(open(p))
        return np.array([hexrgb(c) for c in list(j['brand'].values()) + j['vga16']], np.float32)
    if name.startswith('adaptive'):
        n = int(name.split(':')[1]) if ':' in name else 32
        q = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = np.array(q.getpalette()[:n * 3], np.float32).reshape(-1, 3)
        return pal
    raise ValueError(name)


def nearest(px, pal):
    d = ((px[:, None, :] - pal[None, :, :]) ** 2 * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1)
    return d.argmin(-1)


def quantise(a, pal, dither):
    h, w, _ = a.shape
    if dither == 'fs':
        a = a.copy()
        out = np.zeros((h, w), np.int32)
        for y in range(h):
            row = a[y]
            for x in range(w):
                old = row[x]
                k = nearest(old[None], pal)[0]
                out[y, x] = k
                err = old - pal[k]
                if x + 1 < w: row[x + 1] += err * 7 / 16
                if y + 1 < h:
                    if x > 0: a[y + 1, x - 1] += err * 3 / 16
                    a[y + 1, x] += err * 5 / 16
                    if x + 1 < w: a[y + 1, x + 1] += err * 1 / 16
        return out
    if dither == 'bayer':
        m = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 - 0.5
        t = np.tile(m, (h // 4 + 1, w // 4 + 1))[:h, :w, None]
        spread = 48.0
        return nearest((a + t * spread).reshape(-1, 3), pal).reshape(h, w)
    return nearest(a.reshape(-1, 3), pal).reshape(h, w)


def pixelize(img, width, pal_name='vga16', dither='fs', outline=False, scale=3):
    img = img.convert('RGB')
    h = round(img.height * width / img.width)
    small = img.resize((width, h), Image.BOX).filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    pal = palette(pal_name, small)
    a = np.asarray(small, np.float32)
    idx = quantise(a, pal, dither)
    out = pal[idx]
    if outline:
        lum = (a * [0.3, 0.59, 0.11]).sum(-1)
        gx = np.abs(np.diff(lum, axis=1, prepend=lum[:, :1])); gy = np.abs(np.diff(lum, axis=0, prepend=lum[:1]))
        edge = (np.maximum(gx, gy) > 70)
        dark = pal[np.argmin((pal * [0.3, 0.59, 0.11]).sum(-1))]
        out[edge] = out[edge] * 0.35 + dark * 0.65
        out = pal[nearest(out.reshape(-1, 3), pal)].reshape(out.shape)
    res = Image.fromarray(out.astype(np.uint8))
    return res.resize((res.width * scale, res.height * scale), Image.NEAREST)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--width', type=int, default=140)
    ap.add_argument('--palette', default='vga16')
    ap.add_argument('--dither', default='fs')
    ap.add_argument('--outline', action='store_true')
    ap.add_argument('--scale', type=int, default=3)
    ap.add_argument('--crop')
    a = ap.parse_args()
    im = Image.open(a.src)
    if a.crop: im = im.crop(tuple(int(v) for v in a.crop.split(',')))
    pixelize(im, a.width, a.palette, a.dither, a.outline, a.scale).save(a.out)
