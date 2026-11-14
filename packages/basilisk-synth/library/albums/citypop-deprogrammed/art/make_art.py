#!/usr/bin/env python3
"""CITYPOP DEPROGRAMMED: the pixel art. One night scene, drawn from code (no photographs): a stone stair lane on the
slope of a harbour town, after the rain, at about two in the morning. Houses step down on both sides, a pagoda on the
hill, wires across the sky, a lamp halfway down, puddles on the landings, the strait below with islands and a long
bridge, the moon in the haze.

    make_art.py OUT_DIR

Writes (16 colours, ordered dither, no smoothing):
  scene.png      320 x 200, the page's backdrop (the page animates stars, haze, ripples, windows and a train on top)
  scene.json     where the animated things are: stars, windows, puddles, the moon, the shore line, the haze band
  cover.png      320 x 320, the album cover (the same place, square, with the title)
  cover-640.png  the cover at 2x, for players and link previews
  icon-32.png    the window icon
"""
import json, math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PAL = ['#07081a', '#0d1030', '#171a46', '#23215a', '#33226a', '#4a2470', '#6a2a74', '#8c3478', '#b0507e',
       '#2a1a1c', '#3e2824', '#5a3a2c', '#c89058', '#f0d6a0', '#d8d0f0', '#9a90c8']
SKY = [0, 1, 2, 3, 4, 5, 6, 7, 8]      # the sky's ramp, dark to light
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 + 1 / 32


def rgb(i):
    h = PAL[i]
    return tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))


def dither_ramp(v, ramp, x, y):
    """v in 0..1 along ramp, ordered-dithered at pixel (x, y)"""
    f = v * (len(ramp) - 1)
    lo = int(math.floor(f)); fr = f - lo
    if lo >= len(ramp) - 1:
        return ramp[-1]
    return ramp[lo + 1] if fr > BAYER[y % 4, x % 4] else ramp[lo]


def noise1(n, seed, octaves=4):
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    for o in range(octaves):
        k = 2 ** (o + 2)
        pts = rng.random(k + 2)
        xs = np.linspace(0, k, n)
        i = np.floor(xs).astype(int); f = xs - i
        f = f * f * (3 - 2 * f)
        out += (pts[i] * (1 - f) + pts[i + 1] * f) / 2 ** o
    return out / out.max()


def scene(W, H, seed=1988, cover=False):
    rng = random.Random(seed)
    img = np.zeros((H, W), dtype=np.uint8)
    meta = {'w': W, 'h': H, 'windows': [], 'puddles': [], 'stars': [], 'lamps': []}
    horizon = int(H * (0.50 if not cover else 0.47))
    mx, my = int(W * (0.68 if not cover else 0.76)), int(H * (0.17 if not cover else 0.31))
    mr = max(5, int(min(W, H) * 0.045))
    meta['moon'] = [mx, my, mr]
    # ---- sky: navy at the top, through indigo and plum, to a magenta haze over the water; the moon's glow
    for y in range(horizon + 2):
        for x in range(W):
            v = (y / horizon) ** 1.35 * 0.86
            d = math.hypot(x - mx, (y - my) * 1.15)
            v += 0.42 * math.exp(-(d / (mr * 5.5)) ** 2) + 0.12 * math.exp(-(d / (mr * 14)) ** 2)
            img[y, x] = dither_ramp(min(0.999, v), SKY, x, y)
    # the moon: a pale disc, its haze ring
    for y in range(my - mr - 2, my + mr + 3):
        for x in range(mx - mr - 2, mx + mr + 3):
            d = math.hypot(x - mx, y - my)
            if d <= mr - 0.3:
                img[y, x] = 14 if (x - mx + y - my) < mr * 0.9 or BAYER[y % 4, x % 4] > 0.35 else 15
            elif d <= mr + 1.2 and BAYER[y % 4, x % 4] > 0.5:
                img[y, x] = 15
    # stars where the sky is dark enough
    for _ in range(int(W * H / 900)):
        x, y = rng.randrange(W), rng.randrange(int(horizon * 0.62))
        if math.hypot(x - mx, y - my) > mr * 4 and img[y, x] <= 3:
            meta['stars'].append([x, y, round(rng.random(), 3)])
    # ---- the islands across the strait and the long bridge
    hills = noise1(W, seed + 1)
    for x in range(W):
        top = horizon - int(3 + hills[x] * H * 0.07)
        for y in range(top, horizon + 1):
            img[y, x] = dither_ramp(0.25 + 0.15 * (y - top) / max(1, horizon - top), [2, 3, 4], x, y)
    bx0, bx1 = int(W * 0.06), int(W * 0.52)
    deck = horizon - int(H * 0.035)
    t1, t2 = bx0 + (bx1 - bx0) // 4, bx0 + 3 * (bx1 - bx0) // 4
    tower_h = int(H * 0.07)
    for x in range(bx0, bx1):
        img[deck, x] = 1
        if x % 7 == 0:
            meta['lamps'].append([x, deck - 1])
    for tx in (t1, t2):
        for y in range(deck - tower_h, deck + 4):
            img[y, tx] = 1; img[y, tx + 1] = 1
    for x in range(bx0, bx1):   # the main cable: a catenary between the towers, down to the deck at the ends
        if x < t1:
            yy = deck - tower_h + (tower_h - 1) * (t1 - x) / (t1 - bx0) * 0.0 + (tower_h - 1) * ((x - bx0) / (t1 - bx0)) * 0
            yy = deck - (x - bx0) / (t1 - bx0) * tower_h
        elif x > t2:
            yy = deck - (bx1 - x) / (bx1 - t2) * tower_h
        else:
            u = (x - t1) / (t2 - t1)
            yy = deck - tower_h + 4 * tower_h * 0.75 * u * (1 - u)
        img[int(yy), x] = 1
        if x % 4 == 0 and int(yy) < deck:
            for y in range(int(yy) + 1, deck):
                if y % 2 == 0:
                    img[y, x] = 2
    # ---- the water: dark bands, the moon's broken path, the bridge lamps reflected
    shore = horizon + int(H * 0.13)
    meta['water'] = [horizon + 1, shore]
    for y in range(horizon + 1, shore):
        for x in range(W):
            band = 0.18 + 0.12 * ((y - horizon) / (shore - horizon)) + 0.06 * math.sin(x * 0.31 + y * 1.7)
            img[y, x] = dither_ramp(min(0.999, band), [1, 2, 3, 4], x, y)
        w = int(mr * (0.6 + 0.9 * (y - horizon) / (shore - horizon)))
        for x in range(mx - w, mx + w):
            if 0 <= x < W and rng.random() < 0.42 and (y % 2 == 0):
                img[y, x] = 15 if rng.random() < 0.7 else 14
    for lx, ly in meta['lamps']:
        for y in range(horizon + 2, min(shore, horizon + 9), 2):
            if rng.random() < 0.6:
                img[y, lx] = 12
    meta['shore'] = shore
    # the waterfront road and the railway along it (the page runs a night train here)
    for y in range(shore, shore + 3):
        for x in range(W):
            img[y, x] = 1 if y == shore else 10 if y == shore + 1 else 9
    meta['rail'] = shore - 1
    # ---- the slope: houses step down on both sides of a stone stair lane
    lane_top_x0, lane_top_x1 = int(W * 0.44), int(W * 0.56)
    base_y = H
    meta['lane'] = [lane_top_x0, lane_top_x1, shore + 3]

    def house(x0, x1, y_eave, y_floor, roof_h, tone, lit_p=0.5, gable=False):
        x0, x1 = max(0, x0), min(W, x1)
        if x1 <= x0:
            return
        ramp = [0, 9, 10, 11] if tone else [0, 0, 9, 10]
        for y in range(max(0, y_eave), min(H, y_floor)):
            for x in range(x0, x1):
                img[y, x] = dither_ramp(0.3 + 0.35 * ((x - x0) / max(1, x1 - x0)) - 0.15 * ((y - y_eave) / max(1, y_floor - y_eave)), ramp, x, y)
        if gable:   # a tiled gable: a triangle with the eaves turned up a little
            mid = (x0 + x1) / 2; half = (x1 - x0) / 2 + 2
            for k in range(int(half * 0.6) + 1):
                y = y_eave - 1 - k
                a, b = int(mid - half + k / 0.6), int(mid + half - k / 0.6)
                for x in range(max(0, a), min(W, b)):
                    if 0 <= y < H:
                        img[y, x] = 0 if (k == 0 or (x - a) % 2 == 0) else 1
            if 0 <= y_eave - 2 < H:
                for x in (int(mid - half) - 1, int(mid + half)):
                    if 0 <= x < W:
                        img[y_eave - 2, x] = 0
        else:       # a hipped roof: a dark trapezoid with tile lines
            for k in range(roof_h):
                y = y_eave - 1 - k
                if y < 0:
                    continue
                a, b = x0 - 2 + k, x1 + 2 - k
                for x in range(max(0, a), min(W, b)):
                    img[y, x] = 0 if k == 0 or (x + k) % 3 == 0 else 1
        for wy in range(y_eave + 3, y_floor - 3, 6 + rng.randrange(0, 2)):
            for wx in range(x0 + 2 + rng.randrange(0, 2), x1 - 3, 5 + rng.randrange(0, 4)):
                if rng.random() < 0.45:
                    lit = rng.random() < lit_p
                    ww = 3 if rng.random() < 0.5 else 2
                    for yy in range(wy, min(H, wy + 2)):
                        for xx in range(wx, min(W, wx + ww)):
                            img[yy, xx] = (13 if rng.random() < 0.2 else 12) if lit else 1
                    meta['windows'].append([wx, wy, ww, 2, 1 if lit else 0])

    def tree(cx, cy, r):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r - 2, cx + r + 3):
                if 0 <= x < W and 0 <= y < H and ((x - cx) / (r + 2)) ** 2 + ((y - cy) / r) ** 2 <= 1 + 0.35 * math.sin(x * 1.3 + y):
                    img[y, x] = 1 if BAYER[y % 4, x % 4] < 0.7 else 2

    def sign(x, y, h):
        for yy in range(y, min(H, y + h)):
            for xx in (x, x + 1, x + 2):
                if 0 <= xx < W:
                    img[yy, xx] = 7 if (yy - y) % 3 else 8
        meta.setdefault('signs', []).append([x, y, 3, h])

    # left side, back to front (higher up the slope = further back = smaller)
    rows = 7
    for side in (0, 1):
        for r in range(rows):
            u = r / (rows - 1)
            y_floor = int(shore + 3 + u * (H - shore - 3)) + 4
            lane_x = int((lane_top_x0 if side == 0 else lane_top_x1) + (-1 if side == 0 else 1) * u * W * 0.14)
            x = lane_x
            n = 0
            while (x > -10 if side == 0 else x < W + 10) and n < 12:
                wdt = int(9 + u * 22 + rng.randrange(0, 10))
                tall = int(6 + u * 16 + rng.randrange(0, int(4 + u * 14)))
                x0, x1 = (x - wdt, x) if side == 0 else (x, x + wdt)
                if rng.random() < 0.12 and r < rows - 1:
                    tree((x0 + x1) // 2, y_floor - tall // 2, max(2, tall // 3))
                else:
                    house(x0, x1, y_floor - tall, y_floor, 2 + int(u * 3), (r + n) % 2, lit_p=0.3,
                          gable=rng.random() < 0.45)
                    if rng.random() < 0.07 and tall > 12:
                        sign(x1 - 4 if side == 0 else x0 + 1, y_floor - tall + 3, min(tall - 5, 6 + int(u * 8)))
                gap = rng.randrange(0, 2 + int(u * 3))
                x = x0 - gap if side == 0 else x1 + gap
                n += 1
    # a pagoda on the hill above the left roofs
    px, py = int(W * 0.14), shore - 2
    for tier in range(3):
        wd = 13 - tier * 3; hy = py - tier * 7
        for y in range(hy - 5, hy):
            for x in range(px - wd // 3, px + wd // 3):
                if 0 <= x < W and 0 <= y < H:
                    img[y, x] = 9
        for k in range(3):
            for x in range(px - wd + k * 2, px + wd - k * 2):
                if 0 <= x < W:
                    img[hy - 5 - k, x] = 0
    for y in range(py - 30, py - 20):
        img[y, px] = 0
    # the stair lane: stone steps widening toward us, wet: each step's nose catches the sky
    for y in range(shore + 3, H):
        u = (y - shore - 3) / max(1, H - shore - 4)
        a = int(lane_top_x0 - u * W * 0.14); b = int(lane_top_x1 + u * W * 0.14)
        step = int(3 + u * 6)
        k = (y - shore) % step
        for x in range(max(0, a), min(W, b)):
            if k == 0:
                img[y, x] = 0
            elif k == 1:
                img[y, x] = dither_ramp(0.55 + 0.2 * math.sin(x * 0.21 + y), [2, 3, 4, 15], x, y)
            else:
                img[y, x] = dither_ramp(0.3 + 0.2 * u + 0.08 * math.sin(x * 0.7), [1, 2, 9, 10], x, y)
        # a handrail down the middle, posts every few steps
        cxr = (a + b) // 2
        if 0 <= cxr < W:
            img[y, cxr] = 0 if k else 15
    for k in range(4):
        u = 0.25 + k * 0.22
        cy = int(shore + 3 + u * (H - shore - 3))
        cx = int(W * 0.5 + (-0.08 if k % 2 else 0.07) * W * (0.6 + u))
        rx, ry = int(5 + u * 18), max(1, int(1 + u * 3.5))
        meta['puddles'].append([cx, cy, rx, ry])
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1 and 0 <= x < W and 0 <= y < H:
                    v = 0.55 - 0.3 * (y - cy + ry) / (2 * ry + 1)
                    img[y, x] = dither_ramp(v, [2, 4, 5, 6, 15], x, y)
        # the moon, small, in the puddle
        mxp = cx + int(rx * 0.35)
        for y in range(cy - 1, cy + 1):
            for x in range(mxp - 1, mxp + 2):
                if 0 <= x < W and 0 <= y < H and ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                    img[y, x] = 14
    # the lamp halfway down, at the lane's edge, its glow and its pool of light on the steps
    u = 0.38
    ly = int(shore + 3 + u * (H - shore - 3))
    lx = int(lane_top_x1 + u * W * 0.14) + 2
    ph = int(14 + u * 18)
    for y in range(ly - ph, ly):
        if 0 <= lx < W:
            img[y, lx] = 0
    for x in range(lx - 4, lx + 1):
        if 0 <= x < W:
            img[ly - ph, x] = 0
    meta['streetlamp'] = [lx - 3, ly - ph + 1]
    gx, gy = lx - 3, ly - ph + 1
    for y in range(gy - 9, gy + 10):
        for x in range(gx - 10, gx + 11):
            if 0 <= x < W and 0 <= y < H:
                d = math.hypot(x - gx, (y - gy) * 1.2)
                if d < 1.5:
                    img[y, x] = 13
                elif d < 10 and BAYER[y % 4, x % 4] < 0.42 * (1 - d / 10) ** 1.2:
                    img[y, x] = 12 if d < 4 else 11
    for y in range(ly - 3, min(H, ly + 6)):
        for x in range(lx - 22, lx + 3):
            if 0 <= x < W and img[y, x] in (1, 2, 9, 10) and BAYER[y % 4, x % 4] < 0.4 - abs(x - lx + 9) / 34:
                img[y, x] = 11
    # wires across the sky from pole to pole
    for (x0, y0, x1, y1) in ((0, int(H * 0.3), W, int(H * 0.36)), (0, int(H * 0.33), W, int(H * 0.41))):
        for x in range(W):
            u = x / W
            y = int(y0 + (y1 - y0) * u + 6 * math.sin(math.pi * u))
            if img[y, x] in SKY:
                img[y, x] = 0
    meta['haze'] = [int(horizon * 0.55), shore]
    return img, meta


def save(img, path, scale=1):
    im = Image.fromarray(img, 'P')
    flat = []
    for i in range(16):
        flat += list(rgb(i))
    im.putpalette(flat + [0] * (768 - len(flat)))
    if scale > 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path, optimize=True)


def text1bit(draw_img, xy, text, size, fill, font='DejaVuSans-Bold.ttf', spacing=1):
    """text drawn crisp: rendered once, thresholded, every pixel a palette index"""
    f = ImageFont.truetype(f'/usr/share/fonts/truetype/dejavu/{font}', size)
    l, t, r, b = f.getbbox(text)
    m = Image.new('L', (r - l + 4 + spacing * len(text), b - t + 4), 0)
    d = ImageDraw.Draw(m)
    x = 2
    for ch in text:
        d.text((x - l, 2 - t), ch, font=f, fill=255)
        x += f.getlength(ch) + spacing
    a = np.array(m) > 110
    h, w = a.shape
    X, Y = xy
    for yy in range(h):
        for xx in range(w):
            if a[yy, xx] and 0 <= Y + yy < draw_img.shape[0] and 0 <= X + xx < draw_img.shape[1]:
                draw_img[Y + yy, X + xx] = fill
    return w, h


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    img, meta = scene(320, 200)
    save(img, os.path.join(out, 'scene.png'))
    json.dump(meta, open(os.path.join(out, 'scene.json'), 'w'), separators=(',', ':'))
    c, cm = scene(320, 320, seed=1989, cover=True)
    # the title: light, soft, on the sky; the subtitle under it
    w, h = text1bit(np.zeros((40, 400), np.uint8), (0, 0), 'CITYPOP', 30, 1)
    text1bit(c, ((320 - w) // 2 + 1, 23), 'CITYPOP', 30, 1)
    text1bit(c, ((320 - w) // 2, 22), 'CITYPOP', 30, 14)
    w2, _ = text1bit(np.zeros((40, 400), np.uint8), (0, 0), 'DEPROGRAMMED', 19, 1, spacing=2)
    text1bit(c, ((320 - w2) // 2 + 1, 57), 'DEPROGRAMMED', 19, 1, spacing=2)
    text1bit(c, ((320 - w2) // 2, 56), 'DEPROGRAMMED', 19, 15, spacing=2)
    w3, _ = text1bit(np.zeros((40, 400), np.uint8), (0, 0), 'performed on SNDWAVE2000', 9, 1, font='DejaVuSans.ttf')
    text1bit(c, ((320 - w3) // 2, 300), 'performed on SNDWAVE2000', 9, 15, font='DejaVuSans.ttf')
    save(c, os.path.join(out, 'cover.png'))
    save(c, os.path.join(out, 'cover-640.png'), 2)
    ic = Image.open(os.path.join(out, 'cover.png')).crop((150, 20, 214, 84)).resize((32, 32), Image.NEAREST)
    ic.save(os.path.join(out, 'icon-32.png'))
    print('art ->', out, len(meta['windows']), 'windows', len(meta['stars']), 'stars')


if __name__ == '__main__':
    main()
