"""Pixels: palettes, dithering, crisp (non anti-aliased) text, PD art loading, and the period file writers
(.ICO with 4-bit and 8-bit images, 4-bit and 8-bit .BMP).

Nothing here smooth-scales a finished picture. Source art is resampled once, to the working size, before it is
dithered; after that, only whole-number nearest-neighbour scaling is used (`zoom`)."""
import os
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIRS = ['/mnt/c/Windows/Fonts', '/usr/share/fonts/truetype/dejavu']
ART_ROOT = os.environ.get('PACK_ART', '/mnt/c/Users/willi/Desktop/synth-names/art')

# --------------------------------------------------------------------------------------------- palettes

VGA16 = ['#000000', '#800000', '#008000', '#808000', '#000080', '#800080', '#008080', '#c0c0c0',
         '#808080', '#ff0000', '#00ff00', '#ffff00', '#0000ff', '#ff00ff', '#00ffff', '#ffffff']
WEB216 = ['#%02x%02x%02x' % (r, g, b) for r in range(0, 256, 51) for g in range(0, 256, 51) for b in range(0, 256, 51)]
GRAY4 = ['#000000', '#555555', '#aaaaaa', '#ffffff']


def hexrgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def palette(spec):
    """spec: 'vga16' | 'web216' | 'gray4' | list of hex colours."""
    if isinstance(spec, str):
        spec = {'vga16': VGA16, 'web216': WEB216, 'gray4': GRAY4}[spec]
    return np.array([hexrgb(c) for c in spec], dtype=np.float32)


def adaptive(img, n):
    """An n-colour palette from the picture (median cut), as hex strings."""
    q = img.convert('RGB').quantize(n, method=Image.Quantize.MEDIANCUT)
    p = q.getpalette()[:n * 3]
    return ['#%02x%02x%02x' % tuple(p[i:i + 3]) for i in range(0, len(p), 3)]


# --------------------------------------------------------------------------------------------- dithering

def _bayer(n):
    if n == 1:
        return np.zeros((1, 1))
    m = _bayer(n // 2)
    return np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])


def _nearest(px, P):
    # weighted RGB distance (as the names page): 3,4,2
    w = np.array([3, 4, 2], dtype=np.float32)
    d = (((px[:, None, :] - P[None, :, :]) ** 2) * w).sum(-1)
    return d.argmin(1)


def dither(img, pal, mode='fs'):
    """img: PIL RGB/RGBA. pal: palette spec. mode: none|posterize|bayer2|bayer4|bayer8|fs|atkinson.
    Returns an RGBA image whose opaque pixels are all palette colours (alpha is cut at 128)."""
    img = img.convert('RGBA')
    a = np.asarray(img).astype(np.float32)
    rgb, alpha = a[..., :3].copy(), a[..., 3]
    h, w = alpha.shape
    if mode in ('none', 'smooth'):
        out = rgb
    else:
        P = palette(pal)
        n = len(P)
        if mode == 'posterize':
            out = P[_nearest(rgb.reshape(-1, 3), P)].reshape(h, w, 3)
        elif mode.startswith('bayer'):
            N = int(mode[5:])
            M = _bayer(N)
            sp = 150 if n <= 4 else 90 if n <= 16 else 52 if n > 100 else 76
            t = ((M + .5) / (N * N) - .5) * sp
            tt = np.tile(t, (h // N + 1, w // N + 1))[:h, :w]
            out = P[_nearest((rgb + tt[..., None]).reshape(-1, 3), P)].reshape(h, w, 3)
        else:
            # error diffusion: Pillow's C Floyd-Steinberg against the fixed palette ('atkinson' maps here too;
            # a Python Atkinson loop was too slow for box-size textures)
            pimg = Image.new('P', (1, 1))
            flat = [int(v) for c in P[:256] for v in c]
            flat += flat[-3:] * (256 - min(n, 256))
            pimg.putpalette(flat)
            q = Image.fromarray(rgb.clip(0, 255).astype(np.uint8), 'RGB').quantize(palette=pimg, dither=Image.Dither.FLOYDSTEINBERG)
            out = np.asarray(q.convert('RGB')).astype(np.float32)
    res = np.dstack([out.clip(0, 255), np.where(alpha < 128, 0, 255)]).astype(np.uint8)
    return Image.fromarray(res, 'RGBA')


def zoom(img, k):
    """Whole-number nearest-neighbour enlargement (keeps the pixels square and sharp)."""
    k = int(k)
    return img if k == 1 else img.resize((img.width * k, img.height * k), Image.NEAREST)


# --------------------------------------------------------------------------------------------- fonts and text

_font_cache = {}


def font(name, size):
    key = (name, size)
    if key not in _font_cache:
        path = name if os.path.isabs(name) else None
        if not path:
            for d in FONT_DIRS:
                p = os.path.join(d, name)
                if os.path.exists(p):
                    path = p
                    break
        if not path:
            raise FileNotFoundError('font ' + name)
        idx = 0
        _font_cache[key] = ImageFont.truetype(path, size, index=idx)
    return _font_cache[key]


def text(draw, xy, s, fnt, fill, anchor='la', aa=False, spacing=0, stroke=0, stroke_fill=None):
    draw.fontmode = 'L' if aa else '1'
    if spacing:
        x, y = xy
        if anchor[0] in 'mr':
            tw = text_w(s, fnt, spacing)
            x -= tw if anchor[0] == 'r' else tw / 2
        for ch in s:
            draw.text((x, y), ch, font=fnt, fill=fill, anchor='l' + anchor[1], stroke_width=stroke, stroke_fill=stroke_fill)
            x += fnt.getlength(ch) + spacing
        return
    draw.text(xy, s, font=fnt, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


def text_w(s, fnt, spacing=0):
    return fnt.getlength(s) + spacing * max(0, len(s) - 1)


def fit_font(name, s, maxw, start, minsize=6, spacing=0):
    sz = start
    while sz > minsize and text_w(s, font(name, sz), spacing) > maxw:
        sz -= 1
    return font(name, sz)


def wrap(s, fnt, maxw):
    out, line = [], ''
    for word in s.split():
        t = (line + ' ' + word).strip()
        if fnt.getlength(t) <= maxw or not line:
            line = t
        else:
            out.append(line)
            line = word
    if line:
        out.append(line)
    return out


# --------------------------------------------------------------------------------------------- art

def art(path, size, crop=None, focus=(.5, .5)):
    """Loads a public-domain picture from the names page's art library and covers `size` (w, h) with it.
    crop: optional (x, y, w, h) in 0..1 of the source first."""
    im = Image.open(os.path.join(ART_ROOT, path))
    im = im.convert('RGBA') if im.mode in ('RGBA', 'LA', 'P') else im.convert('RGB')
    if crop:
        W, H = im.size
        im = im.crop((int(crop[0] * W), int(crop[1] * H), int((crop[0] + crop[2]) * W), int((crop[1] + crop[3]) * H)))
    w, h = size
    s = max(w / im.width, h / im.height)
    nw, nh = max(w, round(im.width * s)), max(h, round(im.height * s))
    im = im.resize((nw, nh), Image.LANCZOS)
    x = int((nw - w) * focus[0])
    y = int((nh - h) * focus[1])
    return im.crop((x, y, x + w, y + h))


def art_fit(path, box, crop=None):
    """Fits (contain) a picture with alpha into box (w, h)."""
    im = Image.open(os.path.join(ART_ROOT, path)).convert('RGBA')
    if crop:
        W, H = im.size
        im = im.crop((int(crop[0] * W), int(crop[1] * H), int((crop[0] + crop[2]) * W), int((crop[1] + crop[3]) * H)))
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    s = min(box[0] / im.width, box[1] / im.height)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def tint(img, ink, paper=None):
    """Maps luminance to a two-colour ramp (an engraving printed in one ink)."""
    g = np.asarray(img.convert('L')).astype(np.float32) / 255
    a = np.asarray(img.convert('RGBA'))[..., 3]
    i = np.array(hexrgb(ink), np.float32)
    p = np.array(hexrgb(paper), np.float32) if paper else None
    if p is None:
        rgb = np.broadcast_to(i, g.shape + (3,))
        al = ((1 - g) * a).astype(np.uint8)
    else:
        rgb = i * (1 - g[..., None]) + p * g[..., None]
        al = a
    return Image.fromarray(np.dstack([rgb, al]).astype(np.uint8), 'RGBA')


def gradient(size, stops, vertical=True):
    w, h = size
    n = h if vertical else w
    cols = [np.array(hexrgb(c), np.float32) for c in stops]
    t = np.linspace(0, 1, n)
    seg = np.minimum((t * (len(cols) - 1)).astype(int), len(cols) - 2)
    f = t * (len(cols) - 1) - seg
    line = np.array([cols[s] * (1 - ff) + cols[s + 1] * ff for s, ff in zip(seg, f)])
    arr = np.repeat(line[:, None, :], w, 1) if vertical else np.repeat(line[None, :, :], h, 0)
    return Image.fromarray(arr.astype(np.uint8), 'RGB')


def starburst(size, fill, ink, lines, fontname, points=16, rot=0, outline='#000000', aa=False):
    """An edition starburst: a spiky star with up to three lines of text, drawn without anti-aliasing."""
    import math
    w = h = size
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy, R, r = w / 2, h / 2, w / 2 - 1, w / 2 * .78
    pts = []
    for i in range(points * 2):
        a = math.pi * i / points + math.radians(rot)
        rr = R if i % 2 == 0 else r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill, outline=outline)
    inner = r * 1.5
    n = len(lines)
    sizes = [fit_font(fontname, ln, inner * (.86 if j in (0, n - 1) and n > 2 else 1), int(size * (.22 if n < 3 else .18))) for j, ln in enumerate(lines)]
    tot = sum(f.size for f in sizes) * 1.05
    y = cy - tot / 2
    for ln, f in zip(lines, sizes):
        text(d, (cx, y + f.size / 2), ln, f, ink, anchor='mm', aa=aa)
        y += f.size * 1.05
    return im


# --------------------------------------------------------------------------------------------- .ICO / .BMP

def _vga16_index(img):
    P = palette(VGA16)
    rgb = np.asarray(img.convert('RGB')).astype(np.float32)
    return _nearest(rgb.reshape(-1, 3), P).reshape(rgb.shape[:2]).astype(np.uint8)


def _dib(img, bpp, pal_rgb, idx):
    """A BITMAPINFOHEADER + palette + XOR bits + AND mask, as an .ICO image entry (height doubled)."""
    w, h = img.size
    alpha = np.asarray(img.convert('RGBA'))[..., 3]
    hdr = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, bpp, 0, 0, 0, 0, 0, 0)
    pal = b''.join(struct.pack('BBBB', b, g, r, 0) for r, g, b in pal_rgb)
    pal += b'\0' * (4 * (2 ** bpp) - len(pal))
    rows = []
    for y in range(h - 1, -1, -1):
        r = idx[y]
        if bpp == 4:
            bs = bytes(((int(r[x]) << 4) | (int(r[x + 1]) if x + 1 < w else 0)) for x in range(0, w, 2))
        else:
            bs = bytes(int(v) for v in r)
        bs += b'\0' * ((-len(bs)) % 4)
        rows.append(bs)
    xor = b''.join(rows)
    mrows = []
    for y in range(h - 1, -1, -1):
        bits = 0
        out = bytearray()
        for x in range(w):
            bits = (bits << 1) | (1 if alpha[y, x] < 128 else 0)
            if x % 8 == 7:
                out.append(bits)
                bits = 0
        if w % 8:
            out.append(bits << (8 - w % 8))
        out += b'\0' * ((-len(out)) % 4)
        mrows.append(bytes(out))
    return hdr + pal + xor + b''.join(mrows)


def write_ico(path, images):
    """images: list of (PIL RGBA image, bpp) with bpp 4 (standard VGA 16 colours) or 8 (adaptive 256).
    Transparent pixels are written black in the XOR bits, with the AND mask set (as the 1990s icon editors did)."""
    entries = []
    for img, bpp in images:
        img = img.convert('RGBA')
        a = np.asarray(img)[..., 3]
        if bpp == 4:
            idx = _vga16_index(img)
            pal = [hexrgb(c) for c in VGA16]
        else:
            rgb = img.convert('RGB')
            q = rgb.quantize(255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            p = q.getpalette()[:255 * 3]
            pal = [(0, 0, 0)] + [tuple(p[i:i + 3]) for i in range(0, len(p), 3)]
            idx = (np.asarray(q).astype(np.uint16) + 1).astype(np.uint8)
        idx = np.where(a < 128, 0, idx)
        if bpp == 4:
            idx = np.where(a < 128, 0, idx)
        entries.append((img.size, bpp, _dib(img, bpp, pal, idx)))
    out = struct.pack('<HHH', 0, 1, len(entries))
    off = 6 + 16 * len(entries)
    blobs = b''
    for (w, h), bpp, blob in entries:
        out += struct.pack('<BBBBHHII', w % 256, h % 256, 16 if bpp == 4 else 0, 0, 1, bpp, len(blob), off + len(blobs))
        blobs += blob
    with open(path, 'wb') as f:
        f.write(out + blobs)


def write_bmp(path, img, bpp, pal=None):
    """A Windows 3.0 DIB .BMP, 4 bpp (VGA 16) or 8 bpp (the given palette or adaptive 256), uncompressed."""
    img = img.convert('RGB')
    w, h = img.size
    if bpp == 4:
        pal_rgb = [hexrgb(c) for c in VGA16]
        idx = _vga16_index(img)
    else:
        if pal:
            P = palette(pal)
            idx = _nearest(np.asarray(img).astype(np.float32).reshape(-1, 3), P).reshape(h, w)
            pal_rgb = [tuple(int(v) for v in c) for c in P]
        else:
            q = img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            p = q.getpalette()[:768]
            pal_rgb = [tuple(p[i:i + 3]) for i in range(0, len(p), 3)]
            idx = np.asarray(q)
    ncol = 2 ** bpp
    palb = b''.join(struct.pack('BBBB', b, g, r, 0) for r, g, b in pal_rgb)
    palb += b'\0' * (4 * ncol - len(palb))
    rows = []
    for y in range(h - 1, -1, -1):
        r = idx[y]
        if bpp == 4:
            bs = bytes(((int(r[x]) << 4) | (int(r[x + 1]) if x + 1 < w else 0)) for x in range(0, w, 2))
        else:
            bs = bytes(int(v) for v in r)
        bs += b'\0' * ((-len(bs)) % 4)
        rows.append(bs)
    bits = b''.join(rows)
    off = 14 + 40 + len(palb)
    with open(path, 'wb') as f:
        f.write(b'BM' + struct.pack('<IHHI', off + len(bits), 0, 0, off))
        f.write(struct.pack('<IiiHHIIiiII', 40, w, h, 1, bpp, 0, len(bits), 3780, 3780, 0, 0))
        f.write(palb + bits)
    # what Windows will show: the quantized picture
    return Image.fromarray(np.array(pal_rgb, np.uint8)[np.asarray(idx).astype(int)], 'RGB')
