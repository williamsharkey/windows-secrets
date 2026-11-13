#!/usr/bin/env python3
"""The try-online controls' pixels, taken from Windows for Workgroups 3.11 itself (no look-alikes):
  - the bitmap font MS Sans Serif 8 pt (SSERIFE.FON, the VGA size Windows uses for dialogs) and the System font
    (VGASYS.FON), as glyph atlases the page draws text with, pixel for pixel;
  - Sound Recorder's icon (SOUNDREC.EXE), the slots' desktop icon;
  - Sound Recorder's record-button microphone (SOUNDREC.EXE bitmap 270).
Windows 3.x executables are NE files; their resources are read here directly.

  ui_assets.py W31_JSDOS OUT_DIR    ->  OUT_DIR/ui.png (atlas) + OUT_DIR/ui.json (glyph and sprite rectangles)
"""
import io, json, struct, sys, zipfile
from PIL import Image

RT_ICON, RT_BITMAP, RT_GROUP_ICON, RT_FONT = 0x8003, 0x8002, 0x800E, 0x8008


def ne_resources(b):
    """{(type, id): bytes} of an NE executable (ids: ints, or names for named resources)"""
    ne = struct.unpack_from('<H', b, 0x3C)[0]
    assert b[ne:ne + 2] == b'NE'
    rtab = ne + struct.unpack_from('<H', b, ne + 0x24)[0]
    shift = struct.unpack_from('<H', b, rtab)[0]
    p = rtab + 2; out = {}
    while True:
        t = struct.unpack_from('<H', b, p)[0]
        if t == 0: break
        n = struct.unpack_from('<H', b, p + 2)[0]; p += 8
        for _ in range(n):
            off, ln, flags, rid = struct.unpack_from('<HHHH', b, p); p += 12
            if rid & 0x8000: rid &= 0x7FFF
            else: L = b[rtab + rid]; rid = b[rtab + rid + 1: rtab + rid + 1 + L].decode('latin1')
            out[(t, rid)] = b[off << shift:(off << shift) + (ln << shift)]
    return out


def dib(d, icon=False):
    """a Windows DIB (BITMAPINFOHEADER, 1/4/8 bpp) -> RGBA image (an icon: AND mask made transparent)"""
    hs, w, h, planes, bpp = struct.unpack_from('<IiiHH', d, 0)
    if icon: h //= 2
    ncol = struct.unpack_from('<I', d, 32)[0] or (1 << bpp if bpp <= 8 else 0)
    pal = [tuple(d[hs + 4 * i + k] for k in (2, 1, 0)) for i in range(ncol)]
    stride = ((w * bpp + 31) // 32) * 4
    px0 = hs + 4 * ncol
    im = Image.new('RGBA', (w, h))
    mstride = ((w + 31) // 32) * 4; m0 = px0 + stride * h
    for y in range(h):
        row = px0 + (h - 1 - y) * stride
        for x in range(w):
            if bpp == 1: v = (d[row + x // 8] >> (7 - x % 8)) & 1
            elif bpp == 4: v = (d[row + x // 2] >> (4 if x % 2 == 0 else 0)) & 15
            else: v = d[row + x]
            a = 255
            if icon:
                mb = d[m0 + (h - 1 - y) * mstride + x // 8]
                if (mb >> (7 - x % 8)) & 1: a = 0
            im.putpixel((x, y), pal[v] + (a,))
    return im


def fnt_glyphs(f):
    """a Windows 2.x/3.x .FNT raster font -> (height, ascent, {char: 1-bit image})"""
    ver = struct.unpack_from('<H', f, 0)[0]
    ascent = struct.unpack_from('<H', f, 0x4A)[0]
    height = struct.unpack_from('<H', f, 0x58)[0]
    first, last = f[0x5F], f[0x60]
    tab = 0x76 if ver == 0x200 else 0x94
    ent = 4 if ver == 0x200 else 6
    out = {}
    for i, c in enumerate(range(first, last + 2)):
        if c > 255: break
        w = struct.unpack_from('<H', f, tab + i * ent)[0]
        off = struct.unpack_from('<H' if ver == 0x200 else '<I', f, tab + i * ent + 2)[0]
        im = Image.new('1', (max(w, 1), height), 0)
        for col in range((w + 7) // 8):   # column-major 8-pixel strips
            for y in range(height):
                byte = f[off + col * height + y]
                for bit in range(8):
                    x = col * 8 + bit
                    if x < w and (byte >> (7 - bit)) & 1: im.putpixel((x, y), 1)
        out[c] = (w, im)
    return height, ascent, out


def font_of(fon, points=None):
    r = ne_resources(fon)
    fonts = [v for (t, _), v in r.items() if t == RT_FONT]
    if points is not None:
        fonts = [f for f in fonts if struct.unpack_from('<H', f, 0x44)[0] == points] or fonts
    return fnt_glyphs(min(fonts, key=lambda f: struct.unpack_from('<H', f, 0x58)[0]))


def main():
    jsdos, out = sys.argv[1:3]
    z = zipfile.ZipFile(jsdos)
    sprites, glyph_sets = {}, {}
    sr = ne_resources(z.read('WINDOWS/SOUNDREC.EXE'))
    # the icon: the 32x32 16-colour image of SOUNDREC's first icon group
    icons = [dib(v, icon=True) for (t, _), v in sorted(sr.items(), key=lambda kv: str(kv[0][1])) if t == RT_ICON]
    icon = next((i for i in icons if i.size == (32, 32)), icons[0])
    sprites['icon'] = icon
    for k in (270, 'RECORD'):   # the record button's microphone (bitmap 270, named RECORD in this build)
        if (RT_BITMAP, k) in sr: sprites['mic'] = dib(sr[(RT_BITMAP, k)]); break
    for name, path, pts in (('sans', 'WINDOWS/SYSTEM/SSERIFE.FON', 8), ('system', 'WINDOWS/SYSTEM/VGASYS.FON', None)):
        glyph_sets[name] = font_of(z.read(path), pts)
    # one atlas: sprites first, then each font's glyphs in a row
    W = 1024; y = 0; x = 0; rows_h = 0; items = []
    for n, im in sprites.items(): items.append(('sprite', n, im.convert('RGBA')))
    for fname, (h, asc, gl) in glyph_sets.items():
        for c, (w, im) in gl.items():
            g = Image.new('RGBA', im.size, (0, 0, 0, 0))
            for yy in range(im.size[1]):
                for xx in range(im.size[0]):
                    if im.getpixel((xx, yy)): g.putpixel((xx, yy), (0, 0, 0, 255))
            items.append(('glyph', (fname, c, w), g))
    pos = []
    for kind, key, im in items:
        if x + im.size[0] > W: x = 0; y += rows_h + 1; rows_h = 0
        pos.append((kind, key, x, y, im)); x += im.size[0] + 1; rows_h = max(rows_h, im.size[1])
    atlas = Image.new('RGBA', (W, y + rows_h + 1), (0, 0, 0, 0))
    meta = {'sprites': {}, 'fonts': {n: {'height': h, 'ascent': a, 'glyphs': {}} for n, (h, a, _) in glyph_sets.items()}}
    for kind, key, x, y, im in pos:
        atlas.paste(im, (x, y))
        if kind == 'sprite': meta['sprites'][key] = [x, y, im.size[0], im.size[1]]
        else:
            fname, c, w = key
            meta['fonts'][fname]['glyphs'][c] = [x, y, w]
    atlas.save(out + '/ui.png', optimize=True)
    json.dump(meta, open(out + '/ui.json', 'w'), separators=(',', ':'))
    print('ui.png', atlas.size, 'sprites', {k: v[2:] for k, v in meta['sprites'].items()},
          'fonts', {n: (f['height'], len(f['glyphs'])) for n, f in meta['fonts'].items()})


if __name__ == '__main__':
    main()
