#!/usr/bin/env python3
"""The data and media for williamsharkey.com/sndwave1993/ (the SNDWAVE1993 site) and its Sound Pack Explorer.

    sndwave_site.py SITE_DIR [--recipe-cli recipe_cli] [--previews DIR] [--songs DIR] [--discs DISCS.TSV]

SITE_DIR is the staged docroot (it holds sndrec/ and sndwave1993/). Writes:
  sndwave1993/presets.json         sndrec/presets.json for the product page: SNDWAVE1993 names, root-relative audio
  sndwave1993/packs/packs.json     one entry per sound pack: persona (the fictional maker), counts, files, art sizes
  sndwave1993/packs/data/ID.json   the pack's presets by category: DNA, ASCII recipe (recipe_cli), rating, preview
  sndwave1993/packs/ID/            box.png, disc3d.png, front.png, back.png, spine.png, disc.png, icon32/48.png (native size);
                                   half.png and thumb.png (the box at 1/2 and 1/3, for the shelf);
                                   the manual (PDF), the help file (HLP), README.TXT
  sndwave1993/packs/audio/         the preview clips named in --previews DIR/manifest.json (the library lane's renders)

Packs come from packages/basilisk-synth/library/packs/*/persona.json and, where the packs lane has exported one,
packs/out/web/ID/ (pack.json, the art at native size, manual.pdf); their presets from builder/out/library.json (by
the export's pack_id, else the pack's title or plan id), or the disc's own PRESETS.TSV for a pack not in the library
(Kit Manager 98). Only presets that play on Windows 3.11 are listed.
Without --previews, the owner's thirty picks play the demos already on the site (sndrec/audio/lib/), and the rest
show no play button.
"""
import glob, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LIB = os.path.join(REPO, 'packages', 'basilisk-synth', 'library')
ALIAS = {'electromech': 'electromech-heritage', 'heritage': 'w3x-heritage', 'instruments-archive': 'studio-archive'}
PRODUCT = 'SNDWAVE1993'
# known issues in the current release, shown as a note on the preset: slug -> text (none in 1.3.1)
KNOWN = {}


def recipes(cli, dnas):
    sys.path.insert(0, HERE)
    import site_data
    return site_data.recipes(cli, dnas, None)


def pdf_pages(path):
    b = open(path, 'rb').read()
    return len(re.findall(rb'/Type\s*/Page(?![s\w])', b)) or None


def copy(src, dst):
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src) or open(dst, 'rb').read() != open(src, 'rb').read():
        shutil.copyfile(src, dst)


def thumb(src, dst, n):
    """The box at exactly 1/n size (each pixel the mean of an n x n block), shown pixel for pixel like the rest."""
    from PIL import Image
    im = Image.open(src).convert('RGBA')
    w, h = im.size[0] // n, im.size[1] // n
    t = im.crop((0, 0, w * n, h * n)).resize((w, h), Image.BOX)
    t.save(dst, optimize=True)
    return [w, h]


def size(path):
    from PIL import Image
    return list(Image.open(path).size)


def product_presets(site):
    """sndrec/presets.json, renamed for SNDWAVE1993 and with audio under /sndrec/."""
    d = json.load(open(os.path.join(site, 'sndrec', 'presets.json')))
    for ed, E in d['editions'].items():
        E['plugin'] = PRODUCT
        for p in E['presets']:
            if p.get('file'): p['file'] = '/' + p['file']
            p['program'] = p['program'].replace('BASILISK 16', PRODUCT)
    d['editions']['b16']['note'] = ('The 76 factory programs of 1.2.1, released as BASILISK 16, rendered with <code>render311</code>, '
                                    'which gives the same result on every run.')
    d['editions']['lib']['note'] = ('<b>In 1.3.0.</b> The owner\'s favourites from the new library, rated 6.5 to 8.5 of 10 when '
                                    'it held 1,039 presets. Each demo is the file the owner rated, rendered by <code>render311</code> '
                                    'through the real Windows 3.11 machine and checked that every note sounds. Their level is the preset\'s '
                                    'own, so some are a little quieter than the other demos. Every pack is in the <a href="packs/">Sound Pack Explorer</a>.')
    json.dump(d, open(os.path.join(site, 'sndwave1993', 'presets.json'), 'w'), separators=(',', ':'))
    return {p['dna']: p for p in d['editions']['lib']['presets']}


def main():
    a = sys.argv[1:]
    site = a.pop(0)
    opt = lambda k, dflt=None: a[a.index(k) + 1] if k in a else dflt
    cli, prev, songsdir = opt('--recipe-cli'), opt('--previews'), opt('--songs')
    out = os.path.join(site, 'sndwave1993', 'packs')
    os.makedirs(os.path.join(out, 'data'), exist_ok=True)
    picks = product_presets(site)
    lib = json.load(open(os.path.join(LIB, 'builder', 'out', 'library.json')))
    manifest = {}
    if prev:
        mfile = next(f for f in (os.path.join(prev, 'manifest.json'), os.path.join(prev, 'index.json')) if os.path.exists(f))
        m = json.load(open(mfile))
        for r in (m['presets'] if isinstance(m, dict) else m): manifest[r['slug']] = r
        os.makedirs(os.path.join(out, 'audio'), exist_ok=True)
    by_pack = {}
    for x in lib: by_pack.setdefault(x['pack'], []).append(x)
    names = {v[0]['pack_name']: k for k, v in by_pack.items()}
    WEB = os.path.join(LIB, 'packs', 'out', 'web')
    web = {w['id']: w for w in json.load(open(os.path.join(WEB, 'packs.json')))} if os.path.exists(os.path.join(WEB, 'packs.json')) else {}
    # every pack: the packs lane's web export (packs/out/web/ID/pack.json and its art) where there is one, plus the
    # persona (the maker's address, people and notes, the help file and README)
    entries = []
    for pp in sorted(glob.glob(os.path.join(LIB, 'packs', '*', 'persona.json'))):
        P = json.load(open(pp)); pid = P['id']
        W = json.load(open(os.path.join(WEB, pid, 'pack.json'))) if pid in web else None
        plan = P['pack'].get('plan_id')
        lid = (W and W.get('pack_id')) or names.get(P['pack']['title']) or (plan if plan in by_pack else ALIAS.get(plan))
        entries.append((pid, P, W, lid, os.path.dirname(pp)))
    tsv_rows = {}
    for pid, P, W, lid, pdir in entries:
        if lid in by_pack: continue
        t = os.path.join(pdir, 'disc', 'PRESETS.TSV')   # a pack not in library.json (Kit Manager 98): its disc's own list
        if not os.path.exists(t): continue
        rows = []
        for l in open(t, encoding='utf-8', errors='replace'):
            if l.startswith('#') or not l.strip(): continue
            c = l.rstrip('\n').split('\t')
            if len(c) < 5: continue
            rows.append({'slug': lid + '-' + re.sub(r'[^a-z0-9]+', '-', c[1].lower()).strip('-'), 'name': c[1], 'category': c[0], 'dna': c[2],
                         'ships': ['3.11'] if '3.11' in c[4] else ['XP'], 'edition': 'w31', 'phrase': None, 'tags': []})
        tsv_rows[lid] = rows
    alldna = [x['dna'] for x in lib] + [x['dna'] for r in tsv_rows.values() for x in r]
    recs = recipes(cli, alldna) if cli else {}
    songs = json.load(open(os.path.join(songsdir, 'index.json')))['packs'] if songsdir else {}
    index = []
    # the released discs: a pack staged for a later release (Rainy Loft Collection, 1.4) is left out until then;
    # --discs packages/basilisk-synth/library/packs/out/discs-1.4/DISCS.TSV switches the 1.4 set on (disc images from beside it)
    discs = opt('--discs') or os.path.join(LIB, 'packs', 'out', 'discs', 'DISCS.TSV')
    released = {l.split('\t')[0] for l in open(discs) if l.strip() and not l.startswith('#')} if os.path.exists(discs) else None
    for pid, P, W, lid, pdir in entries:
        if released is not None and lid not in released:
            print('skip', pid, '(not on a released disc)'); continue
        rows = by_pack.get(lid) or tsv_rows.get(lid)
        if not rows:
            print('skip', pid, '(no presets)'); continue
        if not W and not os.path.exists(os.path.join(pdir, 'renders', 'box.png')):
            print('skip', pid, '(no art yet)'); continue
        dst = os.path.join(out, pid); os.makedirs(dst, exist_ok=True)
        art = {}
        if W:   # native pixel size, never rescaled: front, back, spine, disc (printed side), box and disc3d renders
            for k in ('box', 'disc3d', 'front', 'back', 'spine', 'disc', 'icon32', 'icon48'):
                f = W['files'].get(k)
                if f and os.path.exists(os.path.join(WEB, pid, f)):
                    copy(os.path.join(WEB, pid, f), os.path.join(dst, k + '.png')); art[k] = size(os.path.join(WEB, pid, f))
            boxsrc = os.path.join(WEB, pid, W['files']['box'])
        else:
            R = os.path.join(pdir, 'renders')
            for f, k in (('box.png', 'box'), ('disc.png', 'disc3d'), ('icon32.png', 'icon32')):
                if os.path.exists(os.path.join(R, f)):
                    copy(os.path.join(R, f), os.path.join(dst, k + '.png')); art[k] = size(os.path.join(R, f))
            boxsrc = os.path.join(R, 'box.png')
        for stale in ('splash.png',):
            if os.path.exists(os.path.join(dst, stale)): os.remove(os.path.join(dst, stale))
        small = W and os.path.join(WEB, pid, W['files'].get('box_small', 'box_small.png'))
        if small and os.path.exists(small):   # the packs lane's own small render: nothing on the site is downscaled
            copy(small, os.path.join(dst, 'thumb.png')); art['thumb'] = size(small)
            if os.path.exists(os.path.join(dst, 'half.png')): os.remove(os.path.join(dst, 'half.png'))
        else:   # until it exists: the box at 1/3 (each pixel the mean of a 3 x 3 block)
            art['thumb'] = thumb(boxsrc, os.path.join(dst, 'thumb.png'), 3)
        files = {}
        fl = P.get('files', {})
        man = W and os.path.join(WEB, pid, W['files'].get('manual', 'manual.pdf'))
        for k, name in (('pdf', fl.get('pdf')), ('hlp', fl.get('hlp')), ('readme', 'README.TXT')):
            src = name and next(iter(glob.glob(os.path.join(pdir, 'build', name)) + glob.glob(os.path.join(pdir, 'disc', name))), None)
            if k == 'pdf' and man and os.path.exists(man): src = man
            if not src: continue
            copy(src, os.path.join(dst, name))
            files[k] = {'name': name, 'kb': max(1, round(os.path.getsize(src) / 1024))}
            if k == 'pdf': files[k]['pages'] = pdf_pages(src); files[k]['size'] = fl.get('pdf_size')
        booklet = None
        if W and W.get('booklet') and os.path.exists(os.path.join(WEB, pid, W['booklet'])):   # one page per category (384 x 288)
            bsrc = os.path.dirname(os.path.join(WEB, pid, W['booklet'])); bdst = os.path.join(dst, 'booklet')
            shutil.rmtree(bdst, ignore_errors=True); os.makedirs(bdst)   # the export as it is now: no stale pages
            for f in os.listdir(bsrc): copy(os.path.join(bsrc, f), os.path.join(bdst, f))
            booklet = 'booklet/' + os.path.basename(W['booklet'])
        iso = W and W.get('iso') and next((f for f in (os.path.join(os.path.dirname(discs), W['iso']), os.path.join(LIB, 'packs', 'out', 'discs', W['iso'])) if os.path.exists(f)), None)
        if iso and os.path.exists(iso):   # the disc image (it also ships inside the release, on drive P:)
            copy(iso, os.path.join(dst, W['iso'])); files['iso'] = {'name': W['iso'], 'kb': max(1, round(os.path.getsize(iso) / 1024))}
        M, T = P['maker'], P.get('text', {})
        presets = []
        for x in rows:
            if '3.11' not in x['ships']: continue   # SNDWAVE1993 is the Windows 3.11 instrument
            rec = recs.get(x['dna']) or {'one': x.get('recipe_one'), 'lines': x.get('recipe')}
            q = {'s': x['slug'], 'n': x['name'], 'c': x['category'], 'd': x['dna'],
                 'r': {k: rec[k] for k in ('one', 'lines', 'kit') if rec.get(k)}, 'ph': x.get('phrase'),
                 'tags': x.get('tags') or [], 'v3': bool(x.get('v3'))}   # (no edition label: SNDWAVE1993 plays them all on 3.11)
            if x.get('favourite'): q['fav'] = 1
            if x.get('rating') not in (None, 5): q['rt'] = x['rating']
            mf = manifest.get(x['slug'])
            if mf:
                for ext in ('mp3', 'ogg'):
                    f = os.path.join(prev, x['slug'] + '.' + ext)
                    if os.path.exists(f): copy(f, os.path.join(out, 'audio', x['slug'] + '.' + ext)); q[ext] = 1
                q['sec'] = mf.get('seconds')
                if mf.get('phrase') and not q.get('ph'): q['ph'] = mf['phrase']   # what the preview plays (kits: from the manifest)
                if mf.get('flags'): q['fl'] = mf['flags']
                if mf.get('ok') is False: q['bad'] = 1
            if x['slug'] in KNOWN: q['fl'] = q.get('fl', []) + [KNOWN[x['slug']]]
            if mf: pass
            elif x['dna'] in picks and picks[x['dna']].get('file'):
                q['a'] = picks[x['dna']]['file']; q['sec'] = picks[x['dna']].get('sec')
            presets.append(q)
        if not presets:
            print('skip', pid, '(no presets for 3.11)'); continue
        presets_only = len(presets)
        cats = {}
        for q in presets: cats[q['c']] = cats.get(q['c'], 0) + 1
        nsongs = 0
        for g in (songs.get(lid) or {}).get('songs', []):   # the pack's song demos (tools/songrender), before its presets
            q = {'k': 'song', 's': 'song-' + g['slug'], 'n': g['title'], 'c': 'Songs', 'sec': g.get('seconds'),
                 'song': {k: g.get(k) for k in ('kind', 'composer', 'arranger', 'source', 'licence', 'proof', 'credits', 'note', 'length', 'bpm', 'presets', 'tracks')}, 'au': {}}
            for ext in ('ogg', 'mp3'):
                if g.get(ext) and os.path.exists(os.path.join(songsdir, g[ext])):
                    d2 = os.path.join(out, 'songs', os.path.dirname(g[ext])); os.makedirs(d2, exist_ok=True)
                    copy(os.path.join(songsdir, g[ext]), os.path.join(out, 'songs', g[ext]))
                    v = ((g.get('sha256') or {}).get(ext) or '')[:8]   # a new file gets a new URL (no stale copy from a cache)
                    q['au'][ext] = 'songs/' + g[ext] + ('?v=' + v if v else '')
            presets.insert(nsongs, q); nsongs += 1
        json.dump({'id': pid, 'presets': presets}, open(os.path.join(out, 'data', pid + '.json'), 'w'), separators=(',', ':'))
        W = W or {}
        index.append({'id': pid, 'lib': lid, 'title': W.get('title') or P['pack']['title'], 'subtitle': W.get('subtitle') or P['pack'].get('subtitle'),
                      'label': W.get('label') or P['pack'].get('label'), 'year': (W.get('date') or P['pack'].get('date') or '')[:4] or M.get('year'),
                      'edition': W.get('edition'), 'package': W.get('package'), 'price': W.get('price'), 'starburst': W.get('starburst'),
                      'credits': W.get('sound_credits') or [],
                      'maker': {k: M.get(k) for k in ('name', 'short', 'kind', 'place', 'contact', 'people')},
                      'blurb': (W.get('blurb') or T.get('blurb') or '').replace('{count}', str(len(presets))) or None,
                      'intro': [s.replace('{count}', str(len(presets))) for s in T.get('intro', [])],
                      'note': T.get('maker_note', []), 'copyright': T.get('copyright'),
                      'accent': P.get('look', {}).get('accent'), 'n': presets_only, 'cats': cats,
                      'fav': sum(1 for q in presets if q.get('fav')), 'picks': sum(1 for q in presets if q.get('rt', 0) >= 6.5),
                      'art': art, 'files': files, 'booklet': booklet, 'songs': nsongs})
        print(pid, lid, len(presets), 'presets', files.get('pdf', {}).get('pages'), 'pages', 'web' if W else 'renders')
    index.sort(key=lambda p: -p['n'])
    json.dump({'packs': index, 'total': sum(p['n'] for p in index), 'previews': bool(prev)},
              open(os.path.join(out, 'packs.json'), 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
