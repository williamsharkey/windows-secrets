"""Booklet pages: one page per category ("group") of a pack, in that pack's own style, for the site's media player.

    out/web/<id>/booklet/<NN>-<category>.png   384 x 288 pixels, native, dithered to the pack's palette
    out/web/<id>/booklet/cover.png             the booklet's cover
    out/web/<id>/booklet/booklet.json          {category: page, credits, listing?, rows (the preset rectangles)}

A page is one of three kinds:
    listing   a typeset list of the category's presets (a 90s CD-ROM insert), with a spot picture
    art       a full-bleed picture for what the category sounds like, the category name, a signature or a line
    mixed     picture and a short list (or a pull-quote) side by side
Which kind a page gets depends on the maker (persona booklet.mode or its kind) and on the category (pads, drones and
textures lean to pictures; kits, perc and bass to lists). Pictures come from the public-domain / CC0 art library
(synth-names/art/*/manifest.json), chosen by the category's subject words; a few pages are procedural (Chladni
figures, waveforms, rings). Every page's picture is credited in booklet.json."""
import hashlib
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw

from . import artwork, gfx

W, H = 384, 288
LANES = ('aero', 'books', 'global', 'classic', 'newage')
OWN_LANES = ('paulywaulyton',)   # one pack's own pictures: only a pack that names the lane (booklet.lanes / only_lanes) uses them

SUBJECT = {   # what a category sounds like, in picture words (manifest tags and titles)
    'pad': ['ocean', 'sea', 'beach', 'clouds', 'sky', 'aurora', 'wave', 'horizon', 'mist', 'underwater'],
    'drone': ['aurora', 'earth', 'space', 'night sky', 'cosmos', 'glacier', 'ice', 'deep'],
    'texture': ['microscopy', 'coral', 'crystal', 'pattern', 'textile', 'moss', 'fern', 'reef', 'macro'],
    'bass': ['whale', 'deep', 'underwater', 'earth', 'architecture', 'machine', 'shuttle'],
    'sub': ['whale', 'deep', 'underwater', 'earth'],
    'keys': ['piano', 'instrument', 'keyboard', 'music', 'phonograph', 'parlour', 'interior'],
    'organ': ['architecture', 'atrium', 'chapel', 'cathedral', 'pipe', 'interior', 'music'],
    'lead': ['comet', 'rocket', 'lightning', 'star', 'launch', 'flight', 'bird'],
    'bell': ['bell', 'crystal', 'glass', 'snowflake', 'iridescent', 'sun', 'chime'],
    'mallet': ['wood', 'crystal', 'shell', 'marimba', 'glass', 'snowflake'],
    'pluck': ['harp', 'shell', 'butterfly', 'leaf', 'fern', 'instrument'],
    'strings': ['harp', 'instrument', 'music', 'classical', 'ornament', 'art-nouveau'],
    'brass': ['horn', 'poster', 'deco', 'expo', 'launch', 'travel'],
    'vocal': ['choir', 'body', 'aura', 'figure', 'portrait', 'thought-form', 'theosophy'],
    'fx': ['lightning', 'storm', 'satellite', 'hurricane', 'explosion', 'weather', 'cgi'],
    'perc': ['machine', 'engraving', 'apparatus', 'patent', 'gear', 'diagram'],
    'kit': ['machine', 'apparatus', 'patent', 'computer', 'lab', 'diagram'],
    'stab': ['lightning', 'poster', 'deco', 'star', 'bolt'],
    'chord': ['mandala', 'geometry', 'polyhedra', 'sacred geometry', 'symmetry'],
    'arp': ['geometry', 'grid', 'wireframe', 'cgi', 'pattern', 'spiral'],
    'genre': ['machine', 'computer', 'expo'], 'machine': ['computer', 'machine', 'lab'], 'electromech': ['patent', 'apparatus', 'telegraph'],
}
LINES = {     # deadpan period copy, one per category (persona booklet.quotes overrides)
    'pad': 'Hold the key. Let the room do the rest.', 'drone': 'The note that stays.', 'texture': 'Surfaces you can hear.',
    'bass': 'Felt before it is heard.', 'sub': 'Below the floor.', 'keys': 'Every key, voiced by hand.',
    'organ': 'Air through pipes and wires.', 'lead': 'Out in front, where it belongs.', 'bell': 'Struck once, heard twice.',
    'mallet': 'Wood, metal and a soft hammer.', 'pluck': 'Short and bright.', 'strings': 'Bowed, plucked and patient.',
    'brass': 'Announcing itself.', 'vocal': 'Voices from the next room.', 'fx': 'For the moment between moments.',
    'perc': 'Time, kept.', 'kit': 'Every drum on the right key.', 'stab': 'One hit. Then silence.',
    'chord': 'Three notes at once, on purpose.', 'arp': 'Up, down and around.'}
ART_FIRST = {'pad', 'drone', 'texture', 'strings', 'vocal', 'fx', 'mall', 'aqua', 'glass', 'startup', 'utopia', 'slush', 'late night', 'signal'}
LIST_FIRST = {'kit', 'perc', 'bass', 'sub', 'keys', 'genre', 'machine', 'electromech', 'stab'}

_INDEX = None
GLOBAL_WORDS = set()
GLOBAL_USED = {}          # picture -> how many booklets already use it (built in one run, so packs differ)
_TITLEW = {}
_STOP = {'noaa', 'nasa', 'image', 'photo', 'plate', 'from', 'with', 'view', 'over', 'the', 'and', 'of', 'in', 'a', 'flickr',
         'library', 'public', 'domain', 'national', 'marine', 'sanctuary', 'hihwnms', 'fgbnms', 'usfws'}


def _TEXTY(e):
    """Pictures that carry printed titles or lettering (covers, posters, title pages, maps): kept off the pages."""
    w = e['words'] + ' ' + e['path'].lower()
    if any(t in w for t in ('chamberlin', 'mellotron', 'hammond', 'rca ', 'edison', 'olson', 'wurlitzer', 'moog', 'yamaha', 'bell labs')):
        return True
    return any(t in w for t in ('cover', 'poster', 'typography', 'magazine', 'title', 'ephemera', 'map-', ' map', 'label',
                                'advert', 'printing trade', 'layout', 'stamp', 'coin', 'wpa'))


def _words(e):
    return {w for w in ''.join(c if c.isalpha() else ' ' for c in e['title'].lower()).split() if len(w) > 3 and w not in _STOP}


def art_index():
    global _INDEX
    if _INDEX is None:
        _INDEX = []
        for lane in LANES + OWN_LANES:
            f = os.path.join(gfx.ART_ROOT, lane, 'manifest.json')
            if not os.path.exists(f):
                continue
            for e in json.load(open(f, encoding='utf-8')):
                tags = [t.lower() for t in (e.get('tags') or e.get('theme') or [])]
                words = (' '.join(tags) + ' ' + e.get('title', '').lower())
                _INDEX.append({'path': lane + '/' + e['file'], 'lane': lane, 'kind': e.get('kind', 'background'), 'words': words,
                               'title': e.get('title', ''), 'author': (e.get('author') or '').split(';')[0][:120],
                               'license': e.get('license', ''), 'source': e.get('source_url', '')})
    return _INDEX


def _rng(*k):
    return random.Random(int(hashlib.md5('|'.join(map(str, k)).encode()).hexdigest()[:8], 16))


def pick(p, cat, used, kind=('background',), extra=()):
    """The best public-domain picture for a category in this pack: subject words, the pack's own art lanes, unused."""
    B = p.get('booklet', {})
    if cat in B.get('images', {}):
        for e in art_index():
            if e['path'] == B['images'][cat]:
                used.add(e['path'])
                return e
    keys = list(B.get('subjects', {}).get(cat, [])) + SUBJECT.get(cat.lower(), []) + list(extra) + [cat.lower()]
    lanes = {v.split('/')[0] for v in p['look']['art'].values() if isinstance(v, str) and '/' in v}
    lanes |= set(B.get('lanes', []))
    r = _rng(p['id'], cat)
    best, bs = None, -1e9
    seen_words = {w for u in used for w in _TITLEW.get(u, ())}
    only = set(B.get('only_lanes', ()))
    for e in art_index():
        if e['kind'] not in kind or e['path'] in used or _TEXTY(e):
            continue
        if (only and e['lane'] not in only) or (e['lane'] in OWN_LANES and e['lane'] not in lanes):
            continue
        s = sum(3 for k in keys if k in e['words']) + sum(2 for k in B.get('theme', []) if k in e['words']) \
            + (2 if e['lane'] in lanes else 0) + r.random() * 2
        s -= 4 * GLOBAL_USED.get(e['path'], 0)                         # another pack already shows it
        s -= 3 * len(seen_words & _words(e))                          # no two turtles in one booklet
        s -= 1.5 * len(GLOBAL_WORDS & _words(e))                      # and few across the set
        if s > bs:
            best, bs = e, s
    if best:
        used.add(best['path'])
        _TITLEW[best['path']] = _words(best)
        GLOBAL_USED[best['path']] = GLOBAL_USED.get(best['path'], 0) + 1
        GLOBAL_WORDS.update(_words(best))
    return best


# ------------------------------------------------------------------------------------------------ style

def style(p):
    L, B = p['look'], p.get('booklet', {})
    pal = L['palette']
    st = {'ink': L.get('back_ink', L['ink']), 'paper': L.get('back_bg', L['paper']), 'accent': L['accent'], 'accent2': L.get('accent2', L['accent']),
          'band': L.get('spine_bg', L['accent']), 'band_ink': L.get('spine_ink', '#ffffff'), 'aa': L['aa'], 'dither': L['dither'],
          'pixel': 2 if L.get('pixel', 1) > 1 and B.get('chunky', True) else 1, 'pal': pal,
          'display': L['fonts'].get('black') or L['fonts']['display'], 'body': L['fonts']['body'], 'mono': L['fonts'].get('mono', 'cour.ttf'),
          'italic': L['fonts'].get('italic', L['fonts']['body']), 'script': B.get('script_font', 'segoesc.ttf')}
    st.update(B.get('style', {}))
    return st


def dither_pic(p, st, img):
    pal = st['pal']
    if isinstance(pal, str) and pal.startswith('adaptive'):
        pal = gfx.adaptive(img.convert('RGB'), int(pal[8:]), p['look'].get('quant'))
    k = st['pixel']
    if k > 1:
        img = img.resize((img.width // k, img.height // k), Image.LANCZOS)   # the source picture, before dithering
    d = gfx.dither(img, pal, st['dither'] if st['dither'] != 'none' else 'fs')
    return gfx.zoom(d, k) if k > 1 else d


def picture(p, st, e, size, tint=None):
    w, h = size
    if e['kind'] == 'background':
        im = gfx.art(e['path'], (w, h))
    else:
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        o = gfx.art_fit(e['path'], (int(w * .92), int(h * .92)))
        im.alpha_composite(o, ((w - o.width) // 2, (h - o.height) // 2))
    if tint:
        im = gfx.tint(im, *tint)
    return dither_pic(p, st, im)


def procedural(p, st, kind, size, seed):
    """Abstract pages that need no picture: Chladni figures, stacked waveforms, rings."""
    w, h = size
    im = Image.new('RGB', (w, h), st['paper'])
    d = ImageDraw.Draw(im)
    r = random.Random(seed)
    if kind == 'chladni':
        a, b = r.randint(2, 5), r.randint(1, 4)
        ys, xs = np.mgrid[0:h, 0:w]
        u, v = xs / w * math.pi, ys / h * math.pi
        z = np.cos(a * u) * np.cos(b * v) - np.cos(b * u) * np.cos(a * v)
        m = np.abs(z) < .09
        arr = np.array(im)
        arr[m] = gfx.hexrgb(st['ink'])
        im = Image.fromarray(arr)
    elif kind == 'waves':
        n = r.randint(9, 15)
        for i in range(n):
            y0 = h * (i + 1) / (n + 1)
            f = r.uniform(1, 6)
            amp = h / (n + 3) * r.uniform(.4, 1.1)
            col = [st['ink'], st['accent'], st['accent2']][i % 3]
            pts = [(x, y0 + amp * math.sin(x / w * f * 2 * math.pi + i) * math.sin(x / w * math.pi)) for x in range(0, w, 2)]
            d.line(pts, fill=col, width=1)
    else:   # rings
        cx, cy = w * r.uniform(.3, .7), h * r.uniform(.3, .7)
        for i in range(30, 0, -1):
            rr = i * max(w, h) / 30
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=[st['accent'], st['ink'], st['accent2']][i % 3])
    return dither_pic(p, st, im.convert('RGBA'))


# ------------------------------------------------------------------------------------------------ pages

def _sp(s, f):
    """Small bitmap-style type can render a space one pixel wide: make every space at least 3 pixels."""
    return s.replace(' ', '  ') if f.getlength(' ') < 3 else s


def _font(st, key, size):
    f = st[key]
    try:
        return gfx.font(f, size)
    except Exception:
        return gfx.font('arial.ttf', size)


def _head(p, st, d, cat, y=0, h=26):
    d.rectangle((0, y, W, y + h), fill=st['band'])
    f = gfx.fit_font(st['display'], cat.upper(), W - 120, 16)
    gfx.text(d, (10, y + h // 2), cat.upper(), f, st['band_ink'], anchor='lm', aa=st['aa'])
    f2 = gfx.fit_font(st['body'], p['pack']['title'], 110, 10)
    gfx.text(d, (W - 8, y + h // 2), _sp(p['pack']['title'], f2), f2, st['band_ink'], anchor='rm', aa=st['aa'])


def _foot(p, st, d, n):
    f = _font(st, 'body', 9)
    gfx.text(d, (8, H - 5), _sp(p['maker']['name'], f), f, st['ink'], anchor='lb', aa=st['aa'])
    gfx.text(d, (W - 8, H - 5), str(n), f, st['ink'], anchor='rb', aa=st['aa'])


def _list(st, d, presets, box, rows, max_rows=None):
    """Writes the presets' full names in columns inside box (never cut: the face gets smaller, then a long name wraps
    onto a second line) and records each preset's rectangle for the player's highlight. Returns how many it showed."""
    x0, y0, x1, y1 = box
    names = [x['name'] for x in presets]
    if max_rows:
        names = names[:max_rows]
    n = max(1, len(names))
    for cols in (1, 2, 3):
        cw = (x1 - x0) // cols
        per_col = math.ceil(n / cols)
        lh = max(10, min(20, (y1 - y0) // per_col))
        size = max(8, min(15 if cols == 1 else 11, lh - 3))
        while size > 8:
            f = _font(st, 'body', size)
            nw = int(f.getlength('00')) + 6
            if max(f.getlength(_sp(s, f)) for s in names) <= cw - nw - 4:
                break
            size -= 1
        f = _font(st, 'body', size)
        nw = int(f.getlength('00')) + 6
        fits = max(f.getlength(_sp(s, f)) for s in names) <= cw - nw - 4
        if per_col * max(lh, size + 2) <= (y1 - y0) and (fits or cols == 3):
            break
    lh = max(size + 2, min(20, (y1 - y0) // per_col))
    x, y, c = x0, y0, 0
    shown = 0
    for i, s in enumerate(names):
        lines = [_sp(s, f)]
        if f.getlength(lines[0]) > cw - nw - 4:            # wrap a long name onto two lines
            lines = [_sp(l, f) for l in gfx.wrap(s, f, cw - nw - 4)[:2]]
        need = lh * len(lines)
        if y + need > y1:
            c += 1
            if c >= cols:
                break
            x, y = x0 + c * cw, y0
        gfx.text(d, (x, y), '%2d' % (i + 1), f, st['accent'], aa=st['aa'])
        for k, l in enumerate(lines):
            gfx.text(d, (x + nw, y + k * lh), l, f, st['ink'], aa=st['aa'])
        rows.append({'name': s, 'rect': [x, y - 1, cw - 2, need]})
        y += need
        shown += 1
    return shown


def page_listing(p, st, cat, presets, n, used, e=None):
    im = Image.new('RGB', (W, H), st['paper'])
    d = ImageDraw.Draw(im)
    _head(p, st, d, cat)
    rows = []
    credit = None
    spot = e or pick(p, cat, used, kind=('object', 'mark'))
    lx1 = W - 10
    if spot and len(presets) <= 30:
        pic = picture(p, st, spot, (110, 110))
        im.paste(pic.convert('RGB'), (W - 120, 38), pic)
        credit = spot
        lx1 = W - 128
    gfx.text(d, (12, 36), '%d preset%s' % (len(presets), 's' if len(presets) != 1 else ''), _font(st, 'italic', 10), st['accent'], aa=st['aa'])
    d.line((12, 50, lx1, 50), fill=st['ink'])
    _list(st, d, presets, (12, 56, lx1, H - 22), rows)
    _foot(p, st, d, n)
    return im, rows, credit


def page_art(p, st, cat, presets, n, used, proc=None):
    credit = None
    if proc:
        pic = procedural(p, st, proc, (W, H), hash(p['id'] + cat))
    else:
        e = pick(p, cat, used)
        pic = picture(p, st, e, (W, H)) if e else procedural(p, st, 'waves', (W, H), 1)
        credit = e
    im = pic.convert('RGB')
    d = ImageDraw.Draw(im)
    B = p.get('booklet', {})
    r = _rng(p['id'], cat, 'art')
    # the category name in a solid label, top or bottom
    f = gfx.fit_font(st['display'], cat.upper(), W - 40, 22)
    tw = int(gfx.text_w(cat.upper(), f)) + 20
    y = 10 if r.random() < .5 else H - 40
    d.rectangle((10, y, 10 + tw, y + 30), fill=st['band'])
    gfx.text(d, (20, y + 15), cat.upper(), f, st['band_ink'], anchor='lm', aa=st['aa'])
    line = B.get('quotes', {}).get(cat) or LINES.get(cat.lower(), '')
    sig = B.get('signature') or (p['maker']['people'][0][0] if p['maker'].get('people') else p['maker']['name'])
    fy = 14 if y > H / 2 else H - 30
    if line:
        fq = _font(st, 'italic', 11)
        tw2 = int(gfx.text_w(line, fq)) + 12
        d.rectangle((W - tw2 - 10, fy - 2, W - 10, fy + 14), fill=st['paper'])
        gfx.text(d, (W - 16, fy + 6), line, fq, st['ink'], anchor='rm', aa=st['aa'])
    fs = _font(st, 'script', 15)
    sy = fy + 26 if fy < H / 2 else fy - 26
    gfx.text(d, (W - 16, sy), sig, fs, st['band_ink'] if st['band_ink'] else '#ffffff', anchor='rm', aa=True,
             stroke=1, stroke_fill=st['band'])
    return im, [], credit


def page_mixed(p, st, cat, presets, n, used):
    im = Image.new('RGB', (W, H), st['paper'])
    d = ImageDraw.Draw(im)
    e = pick(p, cat, used)
    left = r_left = _rng(p['id'], cat, 'mix').random() < .5
    pw = W // 2
    pic = picture(p, st, e, (pw, H)) if e else procedural(p, st, 'rings', (pw, H), 2)
    im.paste(pic.convert('RGB'), (0 if left else W - pw, 0))
    x0 = (pw + 12) if left else 12
    x1 = (W - 10) if left else (W - pw - 10)
    f = gfx.fit_font(st['display'], cat.upper(), x1 - x0, 20)
    gfx.text(d, (x0, 14), cat.upper(), f, st['accent'], aa=st['aa'])
    d.line((x0, 40, x1, 40), fill=st['ink'])
    rows = []
    B = p.get('booklet', {})
    line = B.get('quotes', {}).get(cat) or LINES.get(cat.lower(), '')
    if line:
        fq = _font(st, 'italic', 11)
        yy = 46
        for ln in gfx.wrap(line, fq, x1 - x0):
            gfx.text(d, (x0, yy), ln, fq, st['ink'], aa=st['aa'])
            yy += 13
    else:
        yy = 46
    shown = _list(st, d, presets, (x0, yy + 6, x1, H - 30), rows, max_rows=(H - 36 - yy) // 11)
    shown = len(rows)
    if shown < len(presets):
        gfx.text(d, (x0, H - 26), 'and %d more on the disc' % (len(presets) - shown), _font(st, 'italic', 9), st['accent'], aa=st['aa'])
    _foot(p, st, d, n)
    return im, rows, e


def page_cover(p, st, used):
    e = pick(p, 'cover', used, extra=SUBJECT.get('pad', []))
    pic = picture(p, st, e, (W, H)) if e else procedural(p, st, 'rings', (W, H), 3)
    im = pic.convert('RGB')
    d = ImageDraw.Draw(im)
    d.rectangle((0, H - 70, W, H), fill=st['band'])
    f = gfx.fit_font(st['display'], p['pack']['title'], W - 30, 26)
    gfx.text(d, (14, H - 54 if p.get('booklet', {}).get('cover_credit') else H - 50), p['pack']['title'], f, st['band_ink'], anchor='lm', aa=st['aa'])
    by = H - 30 if p.get('booklet', {}).get('cover_credit') else H - 22
    gfx.text(d, (14, by), 'Booklet  -  ' + p['maker']['name'], _font(st, 'body', 11), st['band_ink'], anchor='lm', aa=st['aa'])
    cc = p.get('booklet', {}).get('cover_credit')     # a sound credit that must show in the booklet (e.g. Paul Chauncy's)
    if cc:
        fc = _font(st, 'italic', 9)
        gfx.text(d, (W - 10, H - 8), _sp(cc, fc), fc, st['band_ink'], anchor='rb', aa=st['aa'])
    return im, [], e


def plan(p, cats):
    """Page kind per category: the maker's mix (booklet.mode: art / list / mixed / varied), leaning by category."""
    B = p.get('booklet', {})
    mode = B.get('mode', 'varied')
    out = {}
    r = _rng(p['id'], 'plan')
    kinds = ['art', 'mixed', 'listing']
    for i, c in enumerate(cats):
        k = c.lower()
        if c in B.get('pages', {}):
            out[c] = B['pages'][c]
            continue
        if mode == 'list':
            out[c] = 'art' if (k in ART_FIRST and i % 3 == 1) else ('mixed' if i % 4 == 3 else 'listing')
        elif mode == 'art':
            out[c] = 'listing' if (k in LIST_FIRST and i % 2) else ('mixed' if i % 3 == 2 else 'art')
        elif mode == 'mixed':
            out[c] = 'art' if k in ART_FIRST and i % 2 == 0 else ('listing' if k in LIST_FIRST and i % 2 else 'mixed')
        else:
            if k in ART_FIRST:
                out[c] = r.choice(['art', 'art', 'mixed'])
            elif k in LIST_FIRST:
                out[c] = r.choice(['listing', 'listing', 'mixed'])
            else:
                out[c] = kinds[(i + r.randrange(3)) % 3]
    if len(set(out.values())) == 1 and len(out) > 2:      # never all one kind
        c = cats[len(cats) // 2]
        out[c] = 'art' if out[c] != 'art' else 'listing'
    return out


def build(p, data, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    st = style(p)
    cats = []
    by = {}
    for x in data['presets']:
        c = x['category']
        if c not in by:
            by[c] = []
            cats.append(c)
        by[c].append(x)
    kinds = plan(p, cats)
    used = set()
    pages = []
    im, rows, e = page_cover(p, st, used)
    im.save(os.path.join(out_dir, 'cover.png'))
    pages.append({'category': None, 'file': 'cover.png', 'kind': 'cover', 'listing': False, 'rows': [], 'credit': _cred(e)})
    procs = p.get('booklet', {}).get('procedural', {})
    for i, c in enumerate(cats):
        k = kinds[c]
        if k == 'listing':
            im, rows, e = page_listing(p, st, c, by[c], i + 2, used)
        elif k == 'art':
            im, rows, e = page_art(p, st, c, by[c], i + 2, used, proc=procs.get(c))
        else:
            im, rows, e = page_mixed(p, st, c, by[c], i + 2, used)
        fn = '%02d-%s.png' % (i + 1, ''.join(ch for ch in c.lower() if ch.isalnum()) or 'group')
        im.convert('RGB').save(os.path.join(out_dir, fn))
        pages.append({'category': c, 'file': fn, 'kind': k, 'listing': bool(rows), 'presets': len(by[c]), 'rows': rows, 'credit': _cred(e)})
    j = {'pack': p['id'], 'title': p['pack']['title'], 'size': [W, H], 'pages': pages,
         'by_category': {pg['category']: pg['file'] for pg in pages if pg['category']}}
    with open(os.path.join(out_dir, 'booklet.json'), 'w', encoding='utf-8') as f:
        json.dump(j, f, ensure_ascii=False, indent=1)
    return j


def _cred(e):
    if not e:
        return {'title': 'procedural', 'license': 'drawn by the generator'}
    return {'title': e['title'], 'author': e['author'], 'license': e['license'], 'source': e['source'], 'file': e['path']}
