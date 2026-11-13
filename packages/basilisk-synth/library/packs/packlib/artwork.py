"""Flat artwork for a pack, from its persona: box faces (the textures for the 3D render), the jewel-case inlay,
the disc label, the price sticker, the splash .BMP and the pixel icons.

The front of every package is described in the persona (look.front), as a list of layout elements drawn in order;
see FRONT ELEMENTS below. Coordinates are fractions of the face (x of width, y of height); sizes are fractions of
the face height. Text may use {title} {subtitle} {edition} {maker} {short} {tagline} {year} {label} {version}
{count} {place}.

The pictures come from the public-domain art library of the names page (synth-names/art). A picture is resampled
once to the working size, dithered to the persona's palette, and then only enlarged by whole numbers (nearest
neighbour). Text is drawn without anti-aliasing unless the persona's era had it (look.aa)."""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import gfx

PX_PER_MM = 5          # texture resolution: 5 px per mm (127 dpi), enough for a 640 px render
BOX_MM = {             # w, h, d in mm (front width, front height, depth)
    'bigbox': (190, 235, 60), 'bigbox_landscape': (250, 190, 60), 'jewel': (142, 125, 10), 'dvd': (135, 190, 14),
    'mailer': (150, 150, 9)}


def pal_of(p, img=None):
    pal = p['look']['palette']
    if isinstance(pal, str) and pal.startswith('adaptive'):
        return gfx.adaptive(img, int(pal[8:])) if img is not None else gfx.VGA16
    return pal


def credits_for(p):
    """Picture credits (title, author, licence, source) for the art this pack uses."""
    out = []
    for key, path in p['look']['art'].items():
        if not isinstance(path, str) or '/' not in path:
            continue
        lane, f = path.split('/', 1)
        try:
            man = json.load(open(os.path.join(gfx.ART_ROOT, lane, 'manifest.json')))
        except OSError:
            continue
        for e in man:
            if e['file'] == f:
                out.append('%s. %s. %s. %s' % (e['title'], e.get('author', '').split(';')[0][:90], e.get('license', ''), e.get('source_url', '')))
    return out


def words(p, data=None):
    pk, M, T = p['pack'], p['maker'], p['text']
    return {'title': pk['title'], 'subtitle': pk.get('subtitle', ''), 'edition': pk.get('edition', ''), 'maker': M['name'],
            'short': M['short'], 'tagline': T['tagline'], 'year': str(M['year']), 'label': pk['label'], 'version': pk['version'],
            'count': str(p.get('_count', '')), 'place': M['place'], 'blurb': T['blurb']}


def fmt(p, s):
    try:
        return s.format(**words(p))
    except (KeyError, IndexError):
        return s


def fontfile(p, name):
    return p['look']['fonts'].get(name, name)


# ------------------------------------------------------------------------------------------------ picture layers

def picture(p, key, size, focus=None, mode=None, pal=None, tint=None, fit='cover'):
    """A dithered picture layer of `size` (output px), worked at size/pixel and enlarged by `pixel`."""
    L = p['look']
    k = L.get('pixel', 1)
    ws = (max(1, size[0] // k), max(1, size[1] // k))
    path = L['art'][key]
    cutout = path.endswith('.png') and ('/objects/' in path or '/marks/' in path)
    if cutout or fit == 'contain':
        src = Image.new('RGBA', ws, (0, 0, 0, 0))
        im = gfx.art_fit(path, ws)
        src.paste(im, ((ws[0] - im.width) // 2, (ws[1] - im.height) // 2), im)
    else:
        src = gfx.art(path, ws, focus=focus or L.get('focus', {}).get(key) or (.5, .5))
    if tint:
        src = gfx.tint(src, *tint)
    pal = pal or pal_of(p, src.convert('RGB'))
    d = gfx.dither(src, pal, mode or L['dither'])
    return gfx.zoom(d, k).crop((0, 0, size[0], size[1])) if k > 1 else d


def wordmark(s, fontname, size, style, colors, aa=False, spacing=0, maxw=None):
    """A product name as an RGBA image. style: chrome | gloss | flat | extrude | gold | outline | rainbow | shadow."""
    f = gfx.font(fontname, size)
    if maxw:
        f = gfx.fit_font(fontname, s, maxw, size, spacing=spacing)
    tw = int(gfx.text_w(s, f, spacing)) + 24
    th = int(f.size * 1.5) + 24
    mask = Image.new('L', (tw, th), 0)
    d = ImageDraw.Draw(mask)
    gfx.text(d, (10, 10 + f.size * .1), s, f, 255, anchor='la', aa=aa, spacing=spacing)
    bb = mask.getbbox() or (0, 0, tw, th)
    out = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    hard = (lambda m: m.point(lambda v: 255 if v > 0 else 0)) if not aa else (lambda m: m)
    if style in ('chrome', 'gold', 'gloss', 'rainbow'):
        y0, y1 = bb[1], bb[3]
        stops = colors[:-1] if style != 'gloss' else colors
        if style == 'rainbow':
            g = gfx.gradient((max(2, bb[2] - bb[0]), th), stops, vertical=False)
            fill = Image.new('RGB', (tw, th), stops[0])
            fill.paste(g, (bb[0], 0))
        else:
            g = gfx.gradient((tw, max(2, y1 - y0)), stops)
            fill = Image.new('RGB', (tw, th), stops[0])
            fill.paste(g, (0, y0))
        if style == 'gloss':
            hl = Image.new('L', (tw, th), 0)
            ImageDraw.Draw(hl).rectangle((0, y0, tw, y0 + (y1 - y0) * .45), fill=110)
            fill = Image.composite(Image.new('RGB', (tw, th), '#ffffff'), fill, hl)
        edge = hard(mask.filter(ImageFilter.MaxFilter(5 if size > 40 else 3)))
        out.paste(Image.new('RGBA', (tw, th), colors[-1] if style != 'gloss' else '#ffffff'), (0, 0), edge)
        out.paste(fill.convert('RGBA'), (0, 0), mask)
    elif style == 'extrude':
        depth = max(2, size // 12)
        for i in range(depth, 0, -1):
            out.paste(Image.new('RGBA', (tw, th), colors[1]), (i, i), mask)
        out.paste(Image.new('RGBA', (tw, th), colors[0]), (0, 0), mask)
    elif style == 'shadow':
        o = max(2, size // 16)
        out.paste(Image.new('RGBA', (tw, th), colors[1]), (o, o), mask)
        out.paste(Image.new('RGBA', (tw, th), colors[0]), (0, 0), mask)
    elif style == 'outline':
        edge = hard(mask.filter(ImageFilter.MaxFilter(5 if size > 40 else 3)))
        out.paste(Image.new('RGBA', (tw, th), colors[1]), (0, 0), edge)
        out.paste(Image.new('RGBA', (tw, th), colors[0]), (0, 0), mask)
    else:
        out.paste(Image.new('RGBA', (tw, th), colors[0]), (0, 0), mask)
    bb = out.getbbox()
    return out.crop(bb) if bb else out


def paste(dst, src, x, y, anchor='lt'):
    if anchor[0] == 'm':
        x -= src.width // 2
    elif anchor[0] == 'r':
        x -= src.width
    if anchor[1] == 'm':
        y -= src.height // 2
    elif anchor[1] == 'b':
        y -= src.height
    dst.alpha_composite(src.convert('RGBA'), (int(x), int(y)))


def barcode(w, h, seed):
    r = random.Random(seed)
    im = Image.new('RGBA', (w, h), '#ffffff')
    d = ImageDraw.Draw(im)
    x = 6
    while x < w - 8:
        bw = r.choice((1, 1, 2, 3))
        if r.random() < .55:
            d.rectangle((x, 4, x + bw - 1, h - 14), fill='#000000')
        x += bw
    digits = ''.join(str(r.randrange(10)) for _ in range(12))
    gfx.text(d, (w // 2, h - 2), digits[0] + ' ' + digits[1:7] + ' ' + digits[7:], gfx.font('cour.ttf', max(8, h // 7)), '#000000', anchor='mb')
    return im


def title_art(p, maxw, size):
    t = p['look']['title']
    return wordmark(fmt(p, t.get('text', '{title}')), fontfile(p, t.get('font', 'display')), size, t['style'], t['colors'],
                    p['look']['aa'] if t['style'] not in ('gloss', 'gold') else True, t.get('spacing', 0), maxw)


# ------------------------------------------------------------------------------------------------ FRONT ELEMENTS

def _box(e, w, h):
    b = e.get('box', [0, 0, 1, 1])
    return [int(b[0] * w), int(b[1] * h), int(b[2] * w), int(b[3] * h)]


def _pattern(im, kind, box, cols, seed=3):
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    r = random.Random(seed)
    if kind == 'stars':
        for _ in range((x1 - x0) * (y1 - y0) // 900):
            x, y = r.randrange(x0, x1), r.randrange(y0, y1)
            c = r.choice(cols)
            if r.random() < .15:
                d.line((x - 3, y, x + 3, y), fill=c)
                d.line((x, y - 3, x, y + 3), fill=c)
            d.point((x, y), fill=c)
    elif kind == 'grid':          # a perspective floor grid
        hy = y0
        cx = (x0 + x1) / 2
        for i in range(-16, 17):
            d.line((cx + i * (x1 - x0) / 60, hy, cx + i * (x1 - x0) / 5, y1), fill=cols[0], width=1)
        k = 1.0
        y = hy
        while y < y1:
            d.line((x0, int(y), x1, int(y)), fill=cols[0])
            y += 3 * k
            k *= 1.35
    elif kind == 'scanlines':
        for y in range(y0, y1, 3):
            d.line((x0, y, x1, y), fill=cols[0])
    elif kind == 'checker':
        s = max(4, (x1 - x0) // 16)
        for yy in range(y0, y1, s):
            for xx in range(x0, x1, s):
                if ((xx - x0) // s + (yy - y0) // s) % 2:
                    d.rectangle((xx, yy, xx + s - 1, yy + s - 1), fill=cols[0])
    elif kind == 'bubbles':
        ov = Image.new('RGBA', im.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for _ in range(26):
            cx, cy, rr = r.randrange(x0, x1), r.randrange(y0, y1), r.randrange(4, max(5, (x1 - x0) // 12))
            od.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 255, 255, 170), width=2)
            od.ellipse((cx - rr * .5, cy - rr * .6, cx - rr * .1, cy - rr * .25), fill=(255, 255, 255, 150))
        im.alpha_composite(ov)
    elif kind == 'stripes':       # sunset sun stripes
        n = len(cols)
        hh = (y1 - y0) / max(1, n)
        for i, c in enumerate(cols):
            d.rectangle((x0, int(y0 + i * hh), x1, int(y0 + (i + 1) * hh)), fill=c)
    elif kind == 'sun':
        side = min(x1 - x0, y1 - y0)       # always round, whatever the face's shape
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        x0, x1, y0, y1 = cx - side // 2, cx + side // 2, cy - side // 2, cy + side // 2
        g = gfx.gradient((x1 - x0, y1 - y0), cols[:2])
        m = Image.new('L', (x1 - x0, y1 - y0), 0)
        md = ImageDraw.Draw(m)
        md.ellipse((0, 0, x1 - x0 - 1, y1 - y0 - 1), fill=255)
        for i in range(5):
            yy = int((y1 - y0) * (.55 + i * .09))
            md.rectangle((0, yy, x1 - x0, yy + 2 + i), fill=0)
        im.paste(g, (x0, y0), m)
    elif kind == 'rays':
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        R = max(x1 - x0, y1 - y0)
        for i in range(0, 24, 2):
            a0, a1 = 2 * math.pi * i / 24, 2 * math.pi * (i + 1) / 24
            d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)), (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=cols[0])
    elif kind == 'tape':          # strips of sticky tape (magazine cover-disc)
        for (tx, ty, ang) in ((x0, y0, -20), (x1, y0, 20)):
            t = Image.new('RGBA', ((x1 - x0) // 4, (x1 - x0) // 14), (240, 230, 190, 170))
            t = t.rotate(ang, expand=True, resample=Image.NEAREST)
            paste(im, t, tx, ty, 'mm')


def _window(im, box, title, p, body=None):
    """A Windows-style window frame (3.1 or 98 look: title bar colour from look.window)."""
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    wc = p['look'].get('window', {'bar': '#000080', 'bar2': '#1084d0', 'face': '#c0c0c0'})
    d.rectangle(box, fill=wc['face'], outline='#000000')
    d.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill='#ffffff')
    d.line((x0 + 1, y0 + 1, x0 + 1, y1 - 1), fill='#ffffff')
    bh = max(12, (y1 - y0) // 9)
    g = gfx.gradient((x1 - x0 - 6, bh), [wc['bar'], wc.get('bar2', wc['bar'])], vertical=False)
    im.paste(g, (x0 + 3, y0 + 3))
    gfx.text(d, (x0 + 8, y0 + 3 + bh // 2), fmt(p, title), gfx.font('tahomabd.ttf' if p['maker']['year'] >= 1995 else 'arialbd.ttf', int(bh * .62)),
             '#ffffff', anchor='lm', aa=p['look']['aa'])
    for i in range(3):
        bx = x1 - 6 - (i + 1) * (bh - 2)
        d.rectangle((bx, y0 + 5, bx + bh - 6, y0 + bh - 1), fill=wc['face'], outline='#000000')
    return (x0 + 6, y0 + bh + 8, x1 - 6, y1 - 6)


def compose(p, w, h, elements):
    L = p['look']
    im = Image.new('RGBA', (w, h), L['paper'])
    for e in elements:
        t = e['t']
        d = ImageDraw.Draw(im)
        aa = e.get('aa', L['aa'])
        if t == 'fill':
            d.rectangle((0, 0, w, h), fill=e['c'])
        elif t == 'grad':
            b = _box(e, w, h)
            g = gfx.gradient((b[2] - b[0], b[3] - b[1]), e['stops'], vertical=e.get('dir', 'v') == 'v')
            im.paste(g, (b[0], b[1]))
        elif t == 'rect':
            b = _box(e, w, h)
            d.rectangle(b, fill=e.get('c'), outline=e.get('outline'), width=e.get('w', 1))
        elif t == 'pattern':
            _pattern(im, e['kind'], _box(e, w, h), e.get('cols', ['#ffffff']), e.get('seed', 3))
        elif t == 'pic':
            b = _box(e, w, h)
            pic = picture(p, e['key'], (b[2] - b[0], b[3] - b[1]), focus=e.get('focus'), tint=e.get('tint'), fit=e.get('fit', 'cover'),
                          mode=e.get('dither'), pal=e.get('pal'))
            fr = e.get('frame')
            if fr == 'polaroid':
                pad = max(4, pic.width // 20)
                f2 = Image.new('RGBA', (pic.width + 2 * pad, pic.height + pad * 5), '#f4f1f4')
                f2.alpha_composite(pic, (pad, pad))
                if e.get('caption'):
                    gfx.text(ImageDraw.Draw(f2), (f2.width // 2, f2.height - pad), fmt(p, e['caption']),
                             gfx.font(fontfile(p, 'hand'), int(pad * 1.7)), '#3d1a5c', anchor='mb')
                pic = f2
            elif fr == 'bevel':
                f2 = Image.new('RGBA', (pic.width + 8, pic.height + 8), '#808080')
                ImageDraw.Draw(f2).rectangle((0, 0, pic.width + 3, 3), fill='#ffffff')
                ImageDraw.Draw(f2).rectangle((0, 0, 3, pic.height + 3), fill='#ffffff')
                f2.alpha_composite(pic, (4, 4))
                pic = f2
            elif fr == 'line':
                ImageDraw.Draw(pic).rectangle((0, 0, pic.width - 1, pic.height - 1), outline=e.get('c', '#000000'), width=2)
            if e.get('rot'):
                pic = pic.rotate(e['rot'], expand=True, resample=Image.NEAREST)
            paste(im, pic, b[0], b[1])
        elif t == 'window':
            inner = _window(im, _box(e, w, h), e.get('title', '{title}'), p)
            if e.get('key'):
                pic = picture(p, e['key'], (inner[2] - inner[0], inner[3] - inner[1]), tint=e.get('tint'))
                paste(im, pic, inner[0], inner[1])
            for i, ln in enumerate(e.get('lines', [])):
                f = gfx.font(fontfile(p, e.get('font', 'body')), max(8, int(h * e.get('size', .025))))
                gfx.text(d, (inner[0] + 4, inner[1] + 4 + i * int(f.size * 1.35)), fmt(p, ln), f, e.get('c', '#000000'), aa=aa)
        elif t in ('text', 'lines'):
            items = [e['s']] if t == 'text' else (p['box']['features'] if e.get('src') == 'features' else e['items'])
            f = gfx.font(fontfile(p, e.get('font', 'body')), max(7, int(h * e['size'])))
            x, y = e['pos'][0] * w, e['pos'][1] * h
            for ln in items:
                s = fmt(p, (e.get('bullet', '') + ln) if t == 'lines' else ln)
                if e.get('upper'):
                    s = s.upper()
                if e.get('lower'):
                    s = s.lower()
                ff = f
                if e.get('maxw'):
                    ff = gfx.fit_font(fontfile(p, e.get('font', 'body')), s, e['maxw'] * w, f.size, spacing=e.get('spacing', 0))
                st = e.get('stroke')
                if e.get('vertical'):
                    for ch in s:
                        gfx.text(d, (x, y), ch, ff, e['c'], anchor='mt', aa=aa)
                        y += ff.size * 1.02
                    continue
                gfx.text(d, (x, y), s, ff, e['c'], anchor=e.get('anchor', 'la'), aa=aa, spacing=e.get('spacing', 0),
                         stroke=st[0] if st else 0, stroke_fill=st[1] if st else None)
                y += ff.size * e.get('step', 1.3)
        elif t == 'word':
            tw = title_art(p, int(w * e.get('maxw', .9)), int(h * e['size']))
            paste(im, tw, e['pos'][0] * w, e['pos'][1] * h, e.get('anchor', 'mm'))
        elif t == 'burst' and p['box'].get('burst'):
            B = p['box']
            bs = int(min(w, h) * e.get('size', .28))
            sb = gfx.starburst(bs, B['burst_fill'], B['burst_ink'], B['burst'], fontfile(p, e.get('font', 'black' if 'black' in L['fonts'] else 'display')),
                               points=e.get('points', 14), rot=8, aa=aa)
            sb = sb.rotate(e.get('rot', 12), expand=True, resample=Image.NEAREST)
            paste(im, sb, e['pos'][0] * w, e['pos'][1] * h, 'mm')
        elif t == 'stamp':
            sw, sh = int(w * e.get('w', .5)), int(h * e.get('h', .1))
            st = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
            sd = ImageDraw.Draw(st)
            sd.rectangle((0, 0, sw - 1, sh - 1), outline=e.get('c', '#b00000'), width=3)
            gfx.text(sd, (sw // 2, sh // 2), fmt(p, e['s']), gfx.fit_font(fontfile(p, e.get('font', 'timesbd.ttf')), fmt(p, e['s']), sw * .85, int(sh * .7)),
                     e.get('c', '#b00000'), anchor='mm')
            st = st.rotate(e.get('rot', 14), expand=True, resample=Image.NEAREST)
            paste(im, st, e['pos'][0] * w, e['pos'][1] * h, 'mm')
        elif t == 'pill':
            f = gfx.font(fontfile(p, e.get('font', 'display')), int(h * e['size']))
            s = fmt(p, e['s'])
            tw = int(gfx.text_w(s, f)) + f.size
            ph = int(f.size * 1.5)
            x, y = int(e['pos'][0] * w), int(e['pos'][1] * h)
            d.rounded_rectangle((x - tw // 2, y - ph // 2, x + tw // 2, y + ph // 2), radius=ph // 2, fill=e['bg'], outline=e.get('outline', '#000000'))
            gfx.text(d, (x, y), s, f, e['c'], anchor='mm', aa=aa)
    return im


def final(p, im):
    """Puts a finished face through the persona's palette once more (keeps type and art on one palette)."""
    L = p['look']
    if L.get('posterize_final'):
        pal = L['palette'] if not (isinstance(L['palette'], str) and L['palette'].startswith('adaptive')) else 'web216'
        return gfx.dither(im.convert('RGB'), pal, 'posterize').convert('RGB')
    return im.convert('RGB')


def front(p, w, h):
    return final(p, compose(p, w, h, p['look']['front']))


def back(p, w, h):
    L, pk, M, B, T = p['look'], p['pack'], p['maker'], p['box'], p['text']
    F, aa = L['fonts'], L['aa']
    ink = L.get('back_ink', '#111111')
    im = Image.new('RGBA', (w, h), L.get('back_bg', L['paper']))
    d = ImageDraw.Draw(im)
    bt = L.get('back_tint')
    pic = picture(p, 'back', (w, int(h * .32)), tint=tuple(bt) if bt else None)
    paste(im, pic, 0, 0)
    y = int(h * .35)
    fb = gfx.font(F['body'], max(11, h // 46))
    fh = gfx.font(F.get('black') or F['display'], max(14, h // 26))
    fh = gfx.fit_font(F.get('black') or F['display'], pk['title'], w * .88, fh.size)
    gfx.text(d, (int(w * .06), y), pk['title'], fh, L.get('back_head', L['accent']), aa=aa)
    y += int(fh.size * 1.4)
    for blurb, col in ((T.get('blurb_de'), ink), (T['blurb'], ink if not T.get('blurb_de') else '#4a4a4a')):
        if not blurb:
            continue
        for ln in gfx.wrap(blurb, fb, w * .88):
            gfx.text(d, (int(w * .06), y), ln, fb, col, aa=aa)
            y += int(fb.size * 1.3)
        y += fb.size // 2
    y += fb.size // 2
    for ft in B['features']:
        gfx.text(d, (int(w * .08), y), L.get('bullet', '* ') + ft, fb, ink, aa=aa)
        y += int(fb.size * 1.4)
    y += fb.size
    req = [L.get('req_head', 'SYSTEM REQUIREMENTS'), 'BASILISK 16 (the 16-bit edition) or', 'BASILISK SYNTH (the 32-bit edition)',
           'CD-ROM drive (the plugin provides one)']
    bh = int(len(req) * fb.size * 1.35 + 12)
    d.rectangle((int(w * .06), y, int(w * .94), y + bh), outline=ink, width=1)
    for i, ln in enumerate(req):
        gfx.text(d, (int(w * .08), y + 6 + i * int(fb.size * 1.35)), ln, fb, ink, aa=aa)
    y += bh + fb.size
    fs = gfx.font(F['body'], max(9, h // 64))
    for ln in M['contact'][:5]:
        if y > h * .86:
            break
        gfx.text(d, (int(w * .06), y), ln, fs, ink, aa=aa)
        y += int(fs.size * 1.3)
    cp = T.get('copyright') or '(c) %d %s' % (M['year'], M['name'])
    cp = cp.encode('cp1252', 'ignore').decode('cp1252').strip()
    gfx.text(d, (int(w * .06), h - int(h * .03)), cp, fs, ink, anchor='ls', aa=aa)
    if B.get('barcode'):
        bc = barcode(int(w * .3), int(h * .09), p['id'])
        paste(im, bc, int(w * .94), int(h * .94), 'rb')
    return final(p, im)


def spine(p, w, h):
    """A spine (w x h with h the long side). Text runs bottom-to-top as on US/EU boxes."""
    L, pk, M = p['look'], p['pack'], p['maker']
    F, aa = L['fonts'], L['aa']
    im = Image.new('RGBA', (h, w), L['spine_bg'])
    d = ImageDraw.Draw(im)
    f = gfx.fit_font(F.get('black') or F['display'], pk['title'], h * .55, int(w * .55))
    gfx.text(d, (int(h * .05), w // 2), pk['title'], f, L.get('spine_title', L['spine_ink']), anchor='lm', aa=aa)
    f2 = gfx.fit_font(F['body'], M['name'], h * .3, int(w * .32))
    gfx.text(d, (h - int(h * .04), w // 2), M['name'], f2, L['spine_ink'], anchor='rm', aa=aa)
    return final(p, im.rotate(90, expand=True))


def plain(p, w, h):
    return Image.new('RGB', (w, h), p['look']['spine_bg'])


def obi(p, w, h):
    """A Japanese obi strip (spine card): vertical title, price, maker."""
    O, F = p['box']['obi'], p['look']['fonts']
    im = Image.new('RGBA', (w, h), '#ffffff')
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, int(h * .2)), fill=O['top'])
    d.rectangle((0, int(h * .85), w, h), fill=O['bottom'])
    fj = gfx.font(F['ja'], int(min(w * .5, h * .6 / max(1, len(O['title'])))))
    y = int(h * .23)
    for ch in O['title']:
        gfx.text(d, (w // 2, y + fj.size // 2), '|' if ch == 'ー' else ch, fj, O['ink'], anchor='mm', aa=True)
        y += int(fj.size * 1.02)
    fs = gfx.font(F['ja'], int(w * .32))
    for i, ch in enumerate(O['head']):
        gfx.text(d, (w // 2, int(h * .03) + i * int(fs.size * 1.1) + fs.size // 2), ch, fs, '#ffffff', anchor='mm', aa=True)
    a, b = p['box']['price']
    gfx.text(d, (w // 2, int(h * .9)), a, gfx.font(F['display'], int(w * .26)), '#ffffff', anchor='mm', aa=True)
    gfx.text(d, (w // 2, int(h * .95)), b, gfx.font(F['ja'], int(w * .22)), '#ffffff', anchor='mm', aa=True)
    return im.convert('RGB')


def sticker(p, w=200):
    """The price sticker, in the shop's own style (box.sticker: bg, ink, shape round|rect, small)."""
    B = p['box']
    S = B.get('sticker', {})
    h = int(w * .55)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col, ink = S.get('bg', '#ffeb3b'), S.get('ink', '#000000')
    if S.get('shape') == 'round':
        d.ellipse((0, 0, w - 1, h - 1), fill=col, outline='#555555')
    else:
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 5, fill=col, outline='#888888')
    a, b = B['price']
    fn = S.get('font', 'arialbd.ttf')
    fn = p['look']['fonts'].get(fn, fn)
    gfx.text(d, (w // 2, int(h * .36)), a, gfx.fit_font(fn, a, w * .82, int(h * .4)), ink, anchor='mm', aa=True)
    gfx.text(d, (w // 2, int(h * .72)), b, gfx.fit_font(fn, b, w * .82, int(h * .3)), ink, anchor='mm', aa=True)
    return im


# ------------------------------------------------------------------------------------------------ inlay and disc

def inlay(p):
    """Jewel-case inlay: the front insert (120 x 120 mm) and the tray card (151 x 118 mm, two 6.5 mm spines)."""
    s = PX_PER_MM
    fr = front(p, 120 * s, 120 * s)
    tw, th, sp = 151 * s, 118 * s, int(6.5 * s)
    tray = Image.new('RGB', (tw, th), '#ffffff')
    tray.paste(back(p, tw - 2 * sp, th), (sp, 0))
    sp_img = spine(p, sp, th)
    tray.paste(sp_img, (0, 0))
    tray.paste(sp_img.rotate(180), (tw - sp, 0))
    return fr, tray


def disc_label(p, D=None):
    """The printed side of the disc as RGBA (D x D). Transparent = bare disc (silver or CD-R dye).
    disc.label: full (the front art, full colour) | silk (one or two inks) | sticker (a hand-written paper label)."""
    s = PX_PER_MM
    D = D or 120 * s
    L, pk, M, DS = p['look'], p['pack'], p['maker'], p['disc']
    F = L['fonts']
    c = D / 2
    im = Image.new('RGBA', (D, D), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    R_out, R_in = 58 * s, 11.5 * s
    if DS['label'] == 'full':
        art = compose(p, D, D, DS['front']) if DS.get('front') else front(p, D, D).convert('RGBA')
        art = final(p, art).convert('RGBA')
        m = Image.new('L', (D, D), 0)
        ImageDraw.Draw(m).ellipse((c - R_out, c - R_out, c + R_out, c + R_out), fill=255)
        ImageDraw.Draw(m).ellipse((c - R_in * 1.45, c - R_in * 1.45, c + R_in * 1.45, c + R_in * 1.45), fill=0)
        im.paste(art, (0, 0), m)
    elif DS['label'] == 'sticker':
        m = Image.new('L', (D, D), 0)
        md = ImageDraw.Draw(m)
        md.ellipse((c - 52 * s, c - 52 * s, c + 52 * s, c + 52 * s), fill=255)
        md.ellipse((c - 19 * s, c - 19 * s, c + 19 * s, c + 19 * s), fill=0)
        paper = Image.new('RGBA', (D, D), DS.get('paper', '#f7f3ea'))
        pic = picture(p, DS.get('pic', 'bg'), (int(70 * s), int(36 * s)))
        paper.alpha_composite(pic, (int(c - 35 * s), int(c - 49 * s)))
        pd = ImageDraw.Draw(paper)
        hand = fontfile(p, 'hand') if 'hand' in F else 'comic.ttf'
        lines = DS.get('lines', ['{title}', '{maker} {year}'])
        cols = DS.get('inks', ['#202060', '#d00000'])
        for i, ln in enumerate(lines):
            s1 = fmt(p, ln)
            f = gfx.fit_font(hand, s1, 76 * s, int((8 if i == 0 else 5) * s))
            gfx.text(pd, (c, c + (25 + i * 9) * s), s1, f, cols[min(i, len(cols) - 1)], anchor='mm', aa=False)
        for i, ln in enumerate(DS.get('side', [])):
            gfx.text(pd, (c + 31 * s, c + (-4 + 5 * i) * s), ln, gfx.font(hand, int(3.6 * s)), '#d00000', anchor='mm')
        im.paste(paper, (0, 0), m)
    else:
        ink = DS.get('ink', '#141414')
        ink2 = DS.get('ink2', ink)
        ft = gfx.fit_font(F.get('black') or F['display'], pk['title'], 76 * s, int(11 * s))
        gfx.text(d, (c, c - 26 * s), pk['title'], ft, ink, anchor='mm', aa=True)
        gfx.text(d, (c, c - 16 * s), pk.get('edition') or pk['subtitle'], gfx.fit_font(F['body'], pk.get('edition') or pk['subtitle'], 80 * s, int(4.5 * s)), ink, anchor='mm', aa=True)
        if ink2 != ink:
            d.rectangle((c - 50 * s, c + 20 * s, c + 50 * s, c + 25 * s), fill=ink2)
        mk = picture(p, 'mark', (int(26 * s), int(26 * s)), tint=(ink, None) if DS.get('tint_mark', True) else None)
        paste(im, mk, c - 40 * s, c, 'mm')
        gfx.text(d, (c, c + 33 * s), M['name'], gfx.fit_font(F['body'], M['name'], 80 * s, int(4.2 * s)), ink, anchor='mm', aa=True)
        gfx.text(d, (c + 40 * s, c), DS.get('mark_text', 'CD-ROM'), gfx.font(F['display'], int(5 * s)), ink, anchor='mm', aa=True)
    ring = DS.get('ring')
    if ring:
        fr = gfx.font(F['body'], int(3.2 * s))
        col = DS.get('ring_ink', '#141414')
        rr = (54.5 if DS['label'] != 'sticker' else 56) * s
        n = len(ring)
        span = min(2 * math.pi * .9, n * fr.size * .62 / rr)
        for i, ch in enumerate(ring):
            a = -math.pi / 2 - span / 2 + span * i / max(1, n - 1)
            g = Image.new('RGBA', (fr.size * 2, fr.size * 2), (0, 0, 0, 0))
            gfx.text(ImageDraw.Draw(g), (fr.size, fr.size), ch, fr, col, anchor='mm', aa=True)
            g = g.rotate(-math.degrees(a) - 90, resample=Image.BICUBIC)
            paste(im, g, c + rr * math.cos(a), c + rr * math.sin(a), 'mm')
    hole = Image.new('L', (D, D), 255)
    ImageDraw.Draw(hole).ellipse((c - 7.5 * s, c - 7.5 * s, c + 7.5 * s, c + 7.5 * s), fill=0)
    a = Image.fromarray(np.minimum(np.asarray(im)[..., 3], np.asarray(hole)), 'L')
    im.putalpha(a)
    return im


# ------------------------------------------------------------------------------------------------ splash and icons

def splash(p, size):
    w, h = size
    L, pk, M = p['look'], p['pack'], p['maker']
    base = Image.new('RGBA', (w, h), L['paper'])
    bt = L.get('back_tint')
    base.alpha_composite(picture(p, 'back', (w, h), tint=tuple(bt) if bt else None))
    fr = front(p, int(h * .8 * .8), int(h * .8)).convert('RGBA')
    paste(base, Image.new('RGBA', (fr.width + 8, fr.height + 8), (0, 0, 0, 160)), w // 2 + 6, h // 2 + 6, 'mm')
    paste(base, fr, w // 2, h // 2, 'mm')
    d = ImageDraw.Draw(base)
    gfx.text(d, (w - 8, h - 8), '%s %s  -  %s' % (pk['title'], pk['version'], M['name']), gfx.font(L['fonts']['body'], 12), '#ffffff',
             anchor='rb', aa=False, stroke=1, stroke_fill='#000000')
    return base.convert('RGB')


def icon(p, n):
    """The pack icon at n x n (16, 32 or 48), drawn as pixel art on a 32-unit grid (no anti-aliasing)."""
    m = p['icon']['motif']
    C = p['icon']['colors']
    im = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = n / 32
    S = lambda *v: tuple(int(round(x * k)) for x in v)
    W1 = max(1, int(k))
    if m == 'sun':
        d.rectangle(S(0, 0, 31, 31), fill=C[3])
        d.ellipse(S(5, 3, 26, 24), fill=C[0])
        d.pieslice(S(5, 3, 26, 24), 180, 360, fill=C[1])
        for y in (15, 18, 21):
            d.rectangle(S(4, y, 27, y + 1), fill=C[3])
        d.rectangle(S(0, 23, 31, 31), fill=C[3])
        for x in (0, 6, 12, 18, 24, 30):
            d.line(S(16, 23, x * 2 - 16, 31), fill=C[2])
        d.line(S(0, 26, 31, 26), fill=C[2])
        d.line(S(0, 23, 31, 23), fill=C[2])
    elif m == 'droplet':
        pts = [(16, 2), (24, 15), (26, 21), (23, 27), (16, 30), (9, 27), (6, 21), (8, 15)]
        d.polygon([S(*q) for q in pts], fill=C[0])
        d.ellipse(S(11, 20, 23, 29), fill=C[1])
        d.polygon([S(*q) for q in pts], outline=C[3])
        d.ellipse(S(10, 14, 14, 21), fill=C[2])
    elif m == 'relay':
        d.rectangle(S(3, 6, 28, 27), fill=C[2], outline=C[1])
        d.rectangle(S(3, 6, 28, 10), fill=C[0], outline=C[1])
        d.rectangle(S(7, 13, 14, 24), fill=C[0], outline=C[1])
        for y in range(14, 24, 2 if n >= 32 else 3):
            d.line(S(7, y, 14, y), fill=C[1])
        d.line(S(17, 14, 25, 12), fill=C[1], width=W1)
        d.rectangle(S(17, 19, 25, 21), fill=C[3], outline=C[1])
        d.rectangle(S(6, 27, 8, 30), fill=C[1])
        d.rectangle(S(23, 27, 25, 30), fill=C[1])
    elif m == 'keys':
        d.rectangle(S(1, 8, 30, 27), fill=C[0], outline=C[1])
        for x in range(1, 30, 4):
            d.line(S(x, 8, x, 27), fill=C[1])
        for x in (4, 8, 16, 20, 24):
            d.rectangle(S(x, 8, x + 2, 19), fill=C[1])
        d.rectangle(S(1, 4, 30, 8), fill=C[2], outline=C[1])
    elif m == 'chladni':
        d.rectangle(S(2, 2, 29, 29), fill=C[1], outline=C[0])
        for y in range(2, 30):
            for x in range(2, 30):
                u, v = (x - 15.5) / 14, (y - 15.5) / 14
                z = math.cos(3 * math.pi * u) * math.cos(2 * math.pi * v) - math.cos(2 * math.pi * u) * math.cos(3 * math.pi * v)
                if abs(z) < .22:
                    d.rectangle(S(x, y, x, y), fill=C[0])
    elif m == 'globe':
        d.ellipse(S(4, 4, 27, 27), fill=C[0], outline=C[3])
        d.arc(S(9, 4, 22, 27), 0, 360, fill=C[2])
        d.line(S(4, 15, 27, 15), fill=C[2])
        d.arc(S(4, 9, 27, 21), 0, 180, fill=C[2])
        d.arc(S(0, 10, 31, 30), 200, 340, fill=C[1], width=max(1, int(2 * k)))
        d.arc(S(0, 1, 31, 21), 20, 160, fill=C[1], width=max(1, int(2 * k)))
    elif m == 'speaker':     # a speaker cabinet with a big cone
        d.rectangle(S(6, 1, 25, 30), fill=C[3], outline=C[1])
        d.ellipse(S(9, 3, 22, 10), fill=C[2], outline=C[1])
        d.ellipse(S(7, 12, 24, 29), fill=C[0], outline=C[1])
        d.ellipse(S(12, 17, 19, 24), fill=C[2], outline=C[1])
    elif m == 'server':      # a tower case with LEDs and a drive bay
        d.rectangle(S(8, 1, 23, 30), fill=C[2], outline=C[1])
        for y in (4, 8):
            d.rectangle(S(10, y, 21, y + 2), fill=C[3], outline=C[1])
        d.rectangle(S(11, 13, 13, 14), fill=C[0])
        d.rectangle(S(15, 13, 17, 14), fill='#00ff00')
        for y in range(18, 28, 2):
            d.line(S(10, y, 21, y), fill=C[1])
    elif m == 'star':        # a 4-point sparkle over a gradient square
        d.rectangle(S(2, 2, 29, 29), fill=C[3], outline=C[1])
        d.polygon([S(16, 3), S(19, 13), S(29, 16), S(19, 19), S(16, 29), S(13, 19), S(3, 16), S(13, 13)], fill=C[0], outline=C[2])
        d.rectangle(S(15, 15, 16, 16), fill=C[2])
    elif m == 'record':      # a vinyl record with a label
        d.ellipse(S(1, 1, 30, 30), fill=C[1])
        for r in (12, 10, 8):
            d.arc(S(16 - r, 16 - r, 15 + r, 15 + r), 200, 300, fill=C[2])
        d.ellipse(S(10, 10, 21, 21), fill=C[0])
        d.rectangle(S(15, 15, 16, 16), fill=C[3])
    elif m == 'faders':      # a mixing console
        d.rectangle(S(1, 4, 30, 27), fill=C[2], outline=C[1])
        for i, y in enumerate((18, 10, 14, 8, 20)):
            x = 4 + i * 6
            d.line(S(x + 1, 7, x + 1, 24), fill=C[1])
            d.rectangle(S(x - 1, y, x + 3, y + 2), fill=C[0], outline=C[1])
    elif m == 'monitor':     # a CRT with a starfield screensaver
        d.rectangle(S(2, 2, 29, 23), fill=C[2], outline=C[1])
        d.rectangle(S(5, 5, 26, 20), fill=C[3])
        for x, y in ((8, 8), (20, 7), (14, 12), (23, 16), (10, 17), (17, 18)):
            d.rectangle(S(x, y, x, y), fill=C[0])
        d.rectangle(S(10, 24, 21, 26), fill=C[2], outline=C[1])
        d.rectangle(S(6, 27, 25, 29), fill=C[2], outline=C[1])
    elif m == 'scope':       # an oscilloscope trace with a glitch
        d.rectangle(S(1, 3, 30, 28), fill=C[3], outline=C[1])
        for x in range(4, 29, 6):
            d.line(S(x, 5, x, 26), fill=C[2])
        pts = [S(3 + i, 15 + 7 * math.sin(i / 3.0) * (1 if 12 < i < 17 or i < 10 or i > 20 else -1)) for i in range(26)]
        d.line(pts, fill=C[0], width=W1)
    elif m == 'palm':
        d.rectangle(S(0, 0, 31, 31), fill=C[3])
        d.ellipse(S(18, 4, 28, 14), fill=C[2])
        d.rectangle(S(0, 25, 31, 31), fill=C[1])
        d.line([S(12, 26), S(13, 18), S(15, 10)], fill='#6a4a2a', width=max(1, int(2 * k)))
        for dx, dy in ((-8, 2), (8, 1), (-6, -4), (6, -5), (0, -7)):
            d.line([S(15, 10), S(15 + dx // 2, 10 + dy - 2), S(15 + dx, 10 + dy + 3)], fill=C[0], width=W1)
    elif m == 'joystick':
        d.rectangle(S(4, 20, 27, 29), fill=C[2], outline=C[1])
        d.line(S(15, 21, 13, 7), fill=C[1], width=max(1, int(2 * k)))
        d.ellipse(S(9, 2, 17, 10), fill=C[0], outline=C[1])
        d.ellipse(S(20, 22, 24, 26), fill=C[0], outline=C[1])
    elif m == 'drum':
        d.ellipse(S(3, 6, 28, 14), fill=C[2], outline=C[1])
        d.rectangle(S(3, 10, 28, 24), fill=C[0], outline=None)
        d.line(S(3, 10, 3, 24), fill=C[1])
        d.line(S(28, 10, 28, 24), fill=C[1])
        d.arc(S(3, 18, 28, 28), 0, 180, fill=C[1])
        for x in (6, 12, 19, 25):
            d.line(S(x, 14, x + 2, 25), fill=C[3])
        d.ellipse(S(3, 6, 28, 14), outline=C[1])
        d.line(S(18, 1, 24, 8), fill=C[1], width=W1)
    elif m == 'workstation':  # a keyboard under a screen
        d.rectangle(S(6, 1, 25, 14), fill=C[2], outline=C[1])
        d.rectangle(S(8, 3, 23, 12), fill=C[3])
        d.line(S(9, 10, 12, 5), fill=C[0])
        d.line(S(12, 5, 15, 10), fill=C[0])
        d.line(S(15, 10, 22, 4), fill=C[0])
        d.rectangle(S(1, 18, 30, 29), fill='#ffffff', outline=C[1])
        for x in range(1, 30, 3):
            d.line(S(x, 18, x, 29), fill=C[1])
        for x in (3, 6, 12, 15, 18, 24, 27):
            d.rectangle(S(x, 18, x + 1, 24), fill=C[1])
    elif m == 'book':
        d.rectangle(S(5, 2, 26, 29), fill=C[0], outline=C[1])
        d.rectangle(S(5, 2, 8, 29), fill=C[3], outline=C[1])
        d.rectangle(S(11, 7, 23, 12), fill=C[2], outline=C[1])
        d.line(S(26, 4, 28, 6), fill=C[1])
        d.rectangle(S(9, 29, 26, 30), fill='#ffffff')
    elif m == 'floppy':
        d.rectangle(S(3, 3, 28, 28), fill=C[3], outline=C[1])
        d.rectangle(S(9, 3, 22, 11), fill=C[2], outline=C[1])
        d.rectangle(S(17, 4, 20, 10), fill=C[3])
        d.rectangle(S(7, 15, 24, 28), fill='#ffffff', outline=C[1])
        for y in (18, 21, 24):
            d.line(S(9, y, 22, y), fill=C[0])
    elif m == 'chip':
        d.rectangle(S(7, 7, 24, 24), fill=C[3], outline=C[1])
        for i in range(8, 24, 3):
            for a, b in ((i, 3), (i, 25)):
                d.rectangle(S(a, b, a + 1, b + 3), fill=C[2])
                d.rectangle(S(b, a, b + 3, a + 1), fill=C[2])
        d.ellipse(S(9, 9, 11, 11), fill=C[0])
        d.text(S(11, 13), '', fill=C[0])
    return im


def save_icons(p, ico_path):
    """PACK.ICO: 32x32 and 16x16 in 16 colours (Windows 3.1) and 256 colours; 48x48 256 colours for XP-era makers."""
    imgs = {n: icon(p, n) for n in (16, 32, 48)}
    entries = [(imgs[32], 4), (imgs[16], 4), (imgs[32], 8), (imgs[16], 8)]
    if p['maker']['year'] >= 1998:
        entries.append((imgs[48], 8))
    gfx.write_ico(ico_path, entries)
    return imgs


def floppy(p):
    """A 3.5-inch diskette (90 x 94 mm) seen from the label side: plastic, metal shutter, the maker's label."""
    s = PX_PER_MM
    w, h = 90 * s, 94 * s
    L, pk, M = p['look'], p['pack'], p['maker']
    col = p['box'].get('floppy_color', '#20304a')
    im = Image.new('RGBA', (w, h), col)
    d = ImageDraw.Draw(im)
    d.rectangle((int(22 * s), 0, int(70 * s), int(29 * s)), fill='#b8bcc2', outline='#7a7e84')
    d.rectangle((int(48 * s), int(4 * s), int(60 * s), int(25 * s)), fill='#5a5e64')
    d.rectangle((int(3 * s), int(3 * s), int(7 * s), int(7 * s)), fill='#101010')
    lab = (int(5 * s), int(36 * s), int(85 * s), int(91 * s))
    d.rectangle(lab, fill='#ffffff')
    d.rectangle((lab[0], lab[1], lab[2], lab[1] + int(6 * s)), fill=L.get('spine_bg', L['ink']))
    gfx.text(d, ((lab[0] + lab[2]) // 2, lab[1] + int(3 * s)), M['name'].upper(), gfx.fit_font(L['fonts']['body'], M['name'].upper(), 74 * s, int(4 * s)),
             L.get('spine_ink', '#ffffff'), anchor='mm', aa=L['aa'])
    f = gfx.font(L['fonts'].get('type', L['fonts']['mono']), int(4.6 * s))
    lines = [pk['title'], pk.get('edition', ''), 'Disk 1 of 1  -  Registered', '', '(c) %d %s' % (M['year'], M['name'])]
    for i, ln in enumerate(lines):
        gfx.text(d, (lab[0] + int(3 * s), lab[1] + int((10 + i * 7) * s)), ln, gfx.fit_font(L['fonts'].get('type', L['fonts']['mono']), ln, 74 * s, f.size) if ln else f,
                 '#101010', aa=L['aa'])
    return im.convert('RGB')
