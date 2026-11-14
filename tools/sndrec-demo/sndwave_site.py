#!/usr/bin/env python3
"""The data and media for williamsharkey.com/sndwave2000/ (the SNDWAVE2000 site) and its Sound Pack Explorer.

    sndwave_site.py SITE_DIR [--recipe-cli recipe_cli] [--previews DIR] [--presets sndrec/presets.json]

SITE_DIR is the staged docroot (it holds sndrec/ and sndwave2000/). Writes:
  sndwave2000/presets.json         sndrec/presets.json for the product page: SNDWAVE2000 names, root-relative audio
  sndwave2000/packs/packs.json     one entry per sound pack: persona (the fictional maker), counts, files, art sizes
  sndwave2000/packs/data/ID.json   the pack's presets by category: DNA, ASCII recipe (recipe_cli), rating, preview
  sndwave2000/packs/ID/            box.png, half.png and thumb.png (the box at 1/2 and 1/3 size), disc.png, splash.png, icon32.png,
                                   the manual (PDF), the help file (HLP), README.TXT
  sndwave2000/packs/audio/         the preview clips named in --previews DIR/manifest.json (the library lane's renders)

Packs come from packages/basilisk-synth/library/packs/*/persona.json; their presets from builder/out/library.json
(matched by the pack's title, else its plan id). A pack with no presets there (Kit Manager 98: XP kits) is left out.
Without --previews, the owner's thirty picks play the demos already on the site (sndrec/audio/lib/), and the rest
show no play button.
"""
import glob, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LIB = os.path.join(REPO, 'packages', 'basilisk-synth', 'library')
ALIAS = {'electromech': 'electromech-heritage', 'heritage': 'w3x-heritage', 'instruments-archive': 'studio-archive'}
PRODUCT = 'SNDWAVE2000'


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
    """sndrec/presets.json, renamed for SNDWAVE2000 and with audio under /sndrec/."""
    d = json.load(open(os.path.join(site, 'sndrec', 'presets.json')))
    for ed, E in d['editions'].items():
        E['plugin'] = PRODUCT
        for p in E['presets']:
            if p.get('file'): p['file'] = '/' + p['file']
            p['program'] = p['program'].replace('BASILISK 16', PRODUCT)
    d['editions']['b16']['note'] = ('The 76 factory programs of 1.2.1, released as BASILISK 16, rendered with <code>render311</code>, '
                                    'which gives the same result on every run.')
    d['editions']['lib']['note'] = ('<b>Coming in 1.3.0.</b> The owner\'s favourites from the new library (1,039 presets in 17 sound '
                                    'packs), rated 6.5 to 8.5 of 10. Each demo is the file the owner rated, rendered by <code>render311</code> '
                                    'through the real Windows 3.11 machine and checked that every note sounds. Their level is the preset\'s '
                                    'own, so some are a little quieter than the other demos. All 1,039 are in the <a href="packs/">Sound Pack Explorer</a>.')
    json.dump(d, open(os.path.join(site, 'sndwave2000', 'presets.json'), 'w'), separators=(',', ':'))
    return {p['dna']: p for p in d['editions']['lib']['presets']}


def main():
    a = sys.argv[1:]
    site = a.pop(0)
    opt = lambda k, dflt=None: a[a.index(k) + 1] if k in a else dflt
    cli, prev = opt('--recipe-cli'), opt('--previews')
    out = os.path.join(site, 'sndwave2000', 'packs')
    os.makedirs(os.path.join(out, 'data'), exist_ok=True)
    picks = product_presets(site)
    lib = json.load(open(os.path.join(LIB, 'builder', 'out', 'library.json')))
    manifest = {}
    if prev:
        m = json.load(open(os.path.join(prev, 'manifest.json')))
        for r in (m['presets'] if isinstance(m, dict) else m): manifest[r['slug']] = r
        os.makedirs(os.path.join(out, 'audio'), exist_ok=True)
    by_pack = {}
    for x in lib: by_pack.setdefault(x['pack'], []).append(x)
    names = {v[0]['pack_name']: k for k, v in by_pack.items()}
    recs = recipes(cli, [x['dna'] for x in lib]) if cli else {}
    index = []
    for pp in sorted(glob.glob(os.path.join(LIB, 'packs', '*', 'persona.json'))):
        P = json.load(open(pp)); pid = P['id']; pdir = os.path.dirname(pp)
        plan = P['pack'].get('plan_id')
        lid = names.get(P['pack']['title']) or (plan if plan in by_pack else ALIAS.get(plan))
        rows = by_pack.get(lid)
        if not rows:
            print('skip', pid, '(no presets in library.json)'); continue
        dst = os.path.join(out, pid); os.makedirs(dst, exist_ok=True)
        R = os.path.join(pdir, 'renders')
        art = {}
        for f in ('box.png', 'disc.png', 'splash.png', 'icon32.png'):
            if os.path.exists(os.path.join(R, f)):
                copy(os.path.join(R, f), os.path.join(dst, f)); art[f[:-4]] = size(os.path.join(R, f))
        art['half'] = thumb(os.path.join(R, 'box.png'), os.path.join(dst, 'half.png'), 2)
        art['thumb'] = thumb(os.path.join(R, 'box.png'), os.path.join(dst, 'thumb.png'), 3)
        files = {}
        fl = P.get('files', {})
        for k, name in (('pdf', fl.get('pdf')), ('hlp', fl.get('hlp')), ('readme', 'README.TXT')):
            src = name and next(iter(glob.glob(os.path.join(pdir, 'build', name)) + glob.glob(os.path.join(pdir, 'disc', name))), None)
            if not src: continue
            copy(src, os.path.join(dst, name))
            files[k] = {'name': name, 'kb': max(1, round(os.path.getsize(src) / 1024))}
            if k == 'pdf': files[k]['pages'] = pdf_pages(src); files[k]['size'] = fl.get('pdf_size')
        M, T = P['maker'], P.get('text', {})
        presets = []
        for x in rows:
            if '3.11' not in x['ships']: continue   # SNDWAVE2000 is the Windows 3.11 instrument
            rec = recs.get(x['dna']) or {'one': x.get('recipe_one'), 'lines': x.get('recipe')}
            q = {'s': x['slug'], 'n': x['name'], 'c': x['category'], 'd': x['dna'],
                 'r': {k: rec[k] for k in ('one', 'lines', 'kit') if rec.get(k)}, 'ph': x.get('phrase'),
                 'tags': x.get('tags') or [], 'xp': x['edition'] == 'xp', 'v3': bool(x.get('v3'))}
            if x.get('favourite'): q['fav'] = 1
            if x.get('rating') not in (None, 5): q['rt'] = x['rating']
            mf = manifest.get(x['slug'])
            if mf:
                for ext in ('mp3', 'ogg'):
                    f = os.path.join(prev, x['slug'] + '.' + ext)
                    if os.path.exists(f): copy(f, os.path.join(out, 'audio', x['slug'] + '.' + ext)); q[ext] = 1
                q['sec'] = mf.get('seconds')
                if mf.get('flags'): q['fl'] = mf['flags']
                if mf.get('ok') is False: q['bad'] = 1
            elif x['dna'] in picks and picks[x['dna']].get('file'):
                q['a'] = picks[x['dna']]['file']; q['sec'] = picks[x['dna']].get('sec')
            presets.append(q)
        cats = {}
        for q in presets: cats[q['c']] = cats.get(q['c'], 0) + 1
        json.dump({'id': pid, 'presets': presets}, open(os.path.join(out, 'data', pid + '.json'), 'w'), separators=(',', ':'))
        index.append({'id': pid, 'lib': lid, 'title': P['pack']['title'], 'subtitle': P['pack'].get('subtitle'),
                      'label': P['pack'].get('label'), 'year': (P['pack'].get('date') or '')[:4] or M.get('year'),
                      'maker': {k: M.get(k) for k in ('name', 'short', 'kind', 'place', 'contact', 'people')},
                      'blurb': (T.get('blurb') or '').replace('{count}', str(len(presets))) or None, 'intro': [s.replace('{count}', str(len(presets))) for s in T.get('intro', [])],
                      'note': T.get('maker_note', []), 'copyright': T.get('copyright'),
                      'accent': P.get('look', {}).get('accent'), 'n': len(presets), 'cats': cats,
                      'fav': sum(1 for q in presets if q.get('fav')), 'picks': sum(1 for q in presets if q.get('rt', 0) >= 6.5),
                      'art': art, 'files': files})
        print(pid, lid, len(presets), 'presets', files.get('pdf', {}).get('pages'), 'pages')
    index.sort(key=lambda p: -p['n'])
    json.dump({'packs': index, 'total': sum(p['n'] for p in index), 'previews': bool(prev)},
              open(os.path.join(out, 'packs.json'), 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
