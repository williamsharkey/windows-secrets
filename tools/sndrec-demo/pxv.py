#!/usr/bin/env python3
"""pxv: a lossless screen-video format for the sndrec.html canvas player (pixel-exact, no YUV, no smoothing).

    pxv.py encode FRAMES OUT_DIR NAME [--fps 30] [--tile 16] [--poster N] [--reduce K] [--crop X,Y,W,H]
    pxv.py verify OUT_DIR NAME FRAMES          decode in Python and compare every frame with the source, byte for byte

FRAMES: a lossless capture: a video file ffmpeg reads exactly (demo311's FFV1 .mkv), or a folder of numbered
.bmp/.png frames (bsynth-host --shots). Output, in OUT_DIR:
    NAME.pxv            the index (below)
    NAME-0.png ...      atlases: frame 0 whole, then every changed rectangle of every later frame, packed in shelves
    NAME-poster.png     frame --poster, for the player before it loads
--reduce K: the frames show each pixel as K x K screen pixels (an editor at a whole-pixel scale); every frame is
checked to be exact K x K blocks and reduced to one pixel per block (it stops if a block is not uniform).
--crop X,Y,W,H: keep that rectangle (after reducing), e.g. Windows' own screen inside an editor window.
Index, little-endian: "PXV1", u16 width, u16 height, u16 fps, u16 atlases, u32 frames; then per frame a u16 count
and that many rectangles of 7 u16: dst x, dst y, w, h, atlas, src x, src y. Frame n is frame n-1 with its rectangles
drawn over it (frame 0: from nothing). Rectangles are runs of changed tile x tile cells, so every pixel copied is
the new frame's own pixel: decoding is exact. PNGs carry no gAMA/sRGB/iCCP chunk (no colour management), and are
palette PNGs when an atlas has 256 colours or fewer (exact palette, never quantized).
"""
import glob, io, os, struct, subprocess, sys, zlib
import numpy as np
from PIL import Image

AW, AH = 1024, 4096   # atlas size limit


def frames(src):
    if os.path.isdir(src):
        fs = sorted(glob.glob(os.path.join(src, '*.bmp')) + glob.glob(os.path.join(src, '*.png')))
        for f in fs:
            yield np.asarray(Image.open(f).convert('RGB'))
        return
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                            '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip().split(',')
    w, h = int(probe[0]), int(probe[1])
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n = w * h * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def dirty_rects(prev, cur, t):
    h, w = cur.shape[:2]
    th, tw = (h + t - 1) // t, (w + t - 1) // t
    d = np.any(prev != cur, axis=2)
    pad = np.zeros((th * t, tw * t), bool); pad[:h, :w] = d
    cells = pad.reshape(th, t, tw, t).any(axis=(1, 3))
    runs = []   # (row, c0, c1) horizontal runs of changed cells
    for r in range(th):
        c = 0
        while c < tw:
            if cells[r, c]:
                c0 = c
                while c < tw and cells[r, c]: c += 1
                runs.append([r, c0, c, r + 1])
            else: c += 1
    merged = []   # stack runs with the same column span in consecutive rows
    for r, c0, c1, r1 in runs:
        for m in merged:
            if m[1] == c0 and m[2] == c1 and m[3] == r: m[3] = r1; break
        else: merged.append([r, c0, c1, r1])
    out = []
    for r0, c0, c1, r1 in merged:
        x, y = c0 * t, r0 * t
        out.append((x, y, min(c1 * t, w) - x, min(r1 * t, h) - y))
    return out


class Atlases:
    def __init__(self):
        self.sheets = []; self.new()

    def new(self):
        self.sheets.append(np.zeros((AH, AW, 3), np.uint8)); self.x = self.y = self.sh = 0; self.used = 0

    def put(self, px):
        h, w = px.shape[:2]
        if self.x + w > AW: self.y += self.sh; self.x = 0; self.sh = 0
        if self.y + h > AH: self.new()
        a = self.sheets[-1]; sx, sy = self.x, self.y
        a[sy:sy + h, sx:sx + w] = px
        self.x += w; self.sh = max(self.sh, h); self.used = max(self.used, sy + h)
        self.heights = getattr(self, 'heights', {}); self.heights[len(self.sheets) - 1] = self.used
        return len(self.sheets) - 1, sx, sy


def save_png(px, path):
    flat = px.reshape(-1, 3)
    key = (flat[:, 0].astype(np.uint32) << 16) | (flat[:, 1].astype(np.uint32) << 8) | flat[:, 2]
    u, inv = np.unique(key, return_inverse=True)
    if len(u) <= 256:
        im = Image.fromarray(inv.astype(np.uint8).reshape(px.shape[:2]), 'P')
        pal = np.stack([(u >> 16) & 255, (u >> 8) & 255, u & 255], 1).astype(np.uint8).reshape(-1).tolist()
        im.putpalette(pal + [0] * (768 - len(pal)))
    else:
        im = Image.fromarray(px, 'RGB')
    im.save(path, optimize=True, compress_level=9)
    return len(u)


def reduce_exact(f, k, n):
    h, w = f.shape[0] // k * k, f.shape[1] // k * k
    f = f[:h, :w]
    r = f[::k, ::k]
    if not np.array_equal(np.repeat(np.repeat(r, k, 0), k, 1), f):
        sys.exit('frame %d is not made of exact %dx%d blocks' % (n, k, k))
    return r


def encode(src, out, name, fps=30, tile=16, poster=None, reduce=1, crop=None):
    os.makedirs(out, exist_ok=True)
    at = Atlases(); index = []; prev = None; n = 0; post = None
    for f in frames(src):
        if reduce > 1: f = reduce_exact(f, reduce, n)
        if crop: x, y, cw, ch = crop; f = np.ascontiguousarray(f[y:y + ch, x:x + cw])
        h, w = f.shape[:2]
        rects = [(0, 0, w, h)] if prev is None else dirty_rects(prev, f, tile)
        recs = []
        for x, y, rw, rh in rects:
            a, sx, sy = at.put(f[y:y + rh, x:x + rw])
            recs.append((x, y, rw, rh, a, sx, sy))
        index.append(recs)
        if poster is not None and n == poster: post = f.copy()
        prev = f; n += 1
    files = []
    for i, a in enumerate(at.sheets):
        used = at.heights.get(i, 0)
        p = os.path.join(out, '%s-%d.png' % (name, i))
        cols = save_png(a[:max(1, used)], p); files.append((p, cols))
    b = bytearray(b'PXV1' + struct.pack('<HHHHI', w, h, fps, len(at.sheets), n))
    for recs in index:
        b += struct.pack('<H', len(recs))
        for r in recs: b += struct.pack('<7H', *r)
    open(os.path.join(out, name + '.pxv'), 'wb').write(b)
    if post is None: post = prev
    save_png(post, os.path.join(out, name + '-poster.png'))
    total = len(b) + sum(os.path.getsize(p) for p, _ in files)
    print('%s: %d frames %dx%d, %d atlases (%s colours), %d rects, index %d B, total %.0f KB (+ poster %.0f KB)' % (
        name, n, w, h, len(files), '/'.join(str(c) for _, c in files), sum(len(r) for r in index), len(b), total / 1024,
        os.path.getsize(os.path.join(out, name + '-poster.png')) / 1024))


def decode(out, name):
    b = open(os.path.join(out, name + '.pxv'), 'rb').read()
    assert b[:4] == b'PXV1'
    w, h, fps, na, n = struct.unpack_from('<HHHHI', b, 4)
    sheets = [np.asarray(Image.open(os.path.join(out, '%s-%d.png' % (name, i))).convert('RGB')) for i in range(na)]
    o = 16; cur = np.zeros((h, w, 3), np.uint8)
    for _ in range(n):
        k, = struct.unpack_from('<H', b, o); o += 2
        for _ in range(k):
            x, y, rw, rh, a, sx, sy = struct.unpack_from('<7H', b, o); o += 14
            cur[y:y + rh, x:x + rw] = sheets[a][sy:sy + rh, sx:sx + rw]
        yield cur


def main():
    a = sys.argv[1:]
    if a and a[0] == 'encode':
        opt = dict(fps=30, tile=16, poster=None, reduce=1, crop=None)
        rest = []
        i = 1
        while i < len(a):
            if a[i] == '--crop': opt['crop'] = [int(x) for x in a[i + 1].split(',')]; i += 2
            elif a[i].startswith('--'): opt[a[i][2:]] = int(a[i + 1]); i += 2
            else: rest.append(a[i]); i += 1
        encode(rest[0], rest[1], rest[2], **opt)
    elif a and a[0] == 'verify':
        out, name, src = a[1:4]
        bad = n = 0
        for d, s in zip(decode(out, name), frames(src)):
            if not np.array_equal(d, s): bad += 1
            n += 1
        print('%s: %d frames compared, %d differ' % (name, n, bad))
        sys.exit(1 if bad else 0)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
