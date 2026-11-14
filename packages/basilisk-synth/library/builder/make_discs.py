#!/usr/bin/env python3
"""The packs as disc images for SNDWAVE2000's Library tab (the 3.11 synth, formerly BASILISK 16) (PRESET-ENGINE-2.md section 16.3: packs as real discs
in File Manager), with the owner's ratings attached.

    PYTHONPATH=<pycdlib> make_discs.py [--edition 311|xp]     out/library.json + ratings/*.json -> out/discs<ed>/

Per pack: out/discs311/<LABEL>/ (the disc's files) and out/discs311/<LABEL>.ISO (ISO 9660 level 1, 8.3 names, for
DOSBox Pure's imgmount; plus Joliet long names). Disc root, as DNA.md 5.5 and PE2 16.1:

  PACK.INF       [Pack] Id, Title, Version, Author, Date, Presets, PresetsXP, Favourites, Description
  PACK.TXT       the same as text, for Notepad (3.11 has no property page)
  AUTORUN.INF    [autorun] label
  PRESETS.TSV    category <TAB> name <TAB> DNA <TAB> pack <TAB> editions <TAB> rating <TAB> verdict <TAB> file
                 (the first three columns are the plugins' preset tables; rating 0-10 and verdict keep/reject/- are the
                 owner's, from builder/ratings; file is the .BSP path on the disc)
  LIBRARY.TSV    the disc's own sounds: none (every preset uses the built-in sounds and drive L:), header only
  <CATEGORY>\\<NAME>.BSP   one line, the DNA, CRLF; File > Associate links .BSP to SYNTH.EXE
  FAVORITE\\<NAME>.BSP     the owner's favourites again (verdict keep, or rated 6.5 or more), so File Manager shows them

out/discs311/DISCS.TSV indexes the discs: id, label, ISO, title, presets, favourites. Identity (pack id, volume label,
title, author, date) follows the packs lane's personas (library/packs/*/persona.json), so these discs and the packs
lane's retail discs (library/packs/out/*.ISO, with manuals and art) are the same packs.
"""
import argparse, glob, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HERE, LIB, load_json
from packs import PACKS

FOLDER = {'workgroup-house': 'workgrp', 'techno-server': 'techsrv', 'trance-connectivity': 'trance2k',
          'breakbeat-resource': 'breakbt', 'bass-enterprise': 'bassent', 'beat-management': 'beatmgmt',
          'retro-display': 'retrodsp', 'screen-saver': 'screensv', 'diagnostics': 'diagnost', 'leisure': 'leisure',
          'game-port': 'gameport', 'workstation-classics': 'workstn', 'studio-archive': 'studarch',
          'w3x-heritage': 'heritage', 'rom-reference': 'romref', 'lifestyle-aesthetics': 'lifestyl',
          'electromech-heritage': 'emheritg', 'kit-manager': 'kitmgr', 'paulywaulophone': 'paulyw', 'garden-rhythm': 'gardenrw'}
FAV_RATING = 6.5
# the product strings (design/brand/sndwave2000/COPY.md when the names lane commits it)
PRODUCT = os.environ.get('SNDWAVE_PRODUCT', 'SNDWAVE2000')
MAKER = os.environ.get('SNDWAVE_MAKER', 'Algorithmic Industries')


def ratings():
    """slug -> {rating, verdict} from the owner's exports (the newest export wins per preset)"""
    out = {}
    for f in sorted(glob.glob(os.path.join(HERE, 'ratings', '*.json'))):
        d = json.load(open(f))
        for slug, v in d.get('presets', {}).items():
            out[slug] = {'rating': v.get('rating'), 'verdict': v.get('verdict'), 'export': os.path.basename(f)}
    return out


def persona(pid):
    f = os.path.join(LIB, 'packs', FOLDER.get(pid, ''), 'persona.json')
    p = json.load(open(f)) if os.path.exists(f) else {}
    pk = dict(p.get('pack', {}))
    if isinstance(p.get('maker'), dict): pk.setdefault('maker', p['maker'].get('name'))
    inf = os.path.join(LIB, 'packs', FOLDER.get(pid, ''), 'disc', 'PACK.INF')
    kv = {}
    if os.path.exists(inf):
        for l in open(inf, encoding='latin-1'):
            if '=' in l: k, v = l.rstrip('\r\n').split('=', 1); kv[k] = v
    return pk, kv


PACK_CATEGORIES = ('garden', 'pauly')          # catalog categories that ship on pack discs, not on L:


def stock_names():
    """the NAMEs of the stock library disc (L:): every catalog sound outside the pack-disc categories"""
    return {i for i, e in catalog().items() if e['category'] not in PACK_CATEGORIES}


def catalog():
    out = {}
    for f in glob.glob(os.path.join(LIB, 'catalog', '*.json')):
        for e in json.load(open(f)): out[e['id']] = e
    return out


def short83(name, taken, ext):
    base = re.sub(r'[^A-Z0-9]', '', name.upper().replace('&', 'N'))
    words = [w for w in (re.sub(r'[^A-Z0-9]', '', w.upper()) for w in name.split()) if w]
    if len(base) > 8 and len(words) > 1:
        cand = (words[0][:8 - min(3, len(words) - 1)] + ''.join(w[0] for w in words[1:4]))[:8]
    else:
        cand = base[:8] or 'PRESET'
    c, i = cand, 1
    while (c + ext) in taken:
        suf = str(i); c = cand[:8 - len(suf)] + suf; i += 1
    taken.add(c + ext)
    return c + ext


def folder83(cat):
    return re.sub(r'[^A-Z0-9]', '', cat.upper())[:8] or 'PRESETS'


def label_of(pid, pp):
    lab = (pp.get('label') or pid).upper()
    return re.sub(r'[^A-Z0-9_]', '_', lab)[:32]


def crlf(s):
    return s.replace('\r\n', '\n').replace('\n', '\r\n').encode('latin-1', 'replace')


def kit_manager():
    """Kit Manager 98: the packs lane's 39 kits (library/packs/kitmgr/KITS.TSV) as they are, with their
    editions (the 12 electromech kits are XP-only: their Insert File steps name library-disc sounds)"""
    f = os.path.join(LIB, 'packs', 'kitmgr', 'KITS.TSV')           # the packs lane's stable list (not the disc copy)
    out = []
    if not os.path.exists(f): return None, out
    for l in open(f, encoding='utf-8'):
        if l.startswith('#') or l.count('\t') < 4: continue
        c, n, d, pid, eds = l.rstrip('\r\n').split('\t')[:5]
        out.append(dict(pack='kit-manager', category=c, name=n, canonical=d, dna=d, xp_dna=d, ships=eds.split(),
                        slug='kit-manager-' + re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-'), kit=True))
    pk = dict(id='kit-manager', name='Kit Manager 98', blurb='Map any drum to any key. Restart not required.')
    return pk, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edition', default='311', choices=['311', 'xp'])
    a = ap.parse_args()
    import pycdlib
    # the shipped table (ship.py): its 'ships' already holds the XP check's verdict
    L = json.load(open(os.path.join(HERE, 'out', 'library.json')))
    for p in L: p['canonical'] = p['dna']
    R = ratings()
    kpk, kits = kit_manager()
    L = L + kits
    packs = list(PACKS) + ([kpk] if kpk else [])
    outdir = os.path.join(HERE, 'out', 'discs' + a.edition)
    os.makedirs(outdir, exist_ok=True)
    index = []
    for pk in packs:
        ps = [p for p in L if p['pack'] == pk['id']]
        if a.edition == 'xp': ps = [p for p in ps if 'XP' in p['ships']]
        if not ps: continue
        pp, kv = persona(pk['id'])
        label = label_of(pk['id'], pp)
        title = pp.get('title') or kv.get('Title') or pk['name']
        files = {}
        rows, favs = [], []
        taken = {}
        for p in sorted(ps, key=lambda p: (p['category'], p['name'])):
            r = R.get(p['slug'], {})
            rating = r.get('rating'); verdict = r.get('verdict')
            fd = folder83(p['category'])
            fn = short83(p['name'], taken.setdefault(fd, set()), '.BSP')
            dna = p['canonical'] if a.edition == '311' else p.get('xp_dna') or p['canonical']
            files['%s/%s' % (fd, fn)] = (crlf(dna + '\n'), '%s/%s.bsp' % (p['category'], re.sub(r'[\\/:*?"<>|]', '', p['name'])))
            eds = ' '.join(e for e in ('3.11', 'XP') if e in p['ships'])
            rows.append('\t'.join([p['category'], p['name'], dna, pk['id'], eds,
                                   '' if rating is None else ('%g' % rating), verdict or '-', '%s\\%s' % (fd, fn)]))
            if verdict == 'keep' or (rating is not None and rating >= FAV_RATING):
                favs.append((p, fd, fn, dna, rating, verdict))
        ftaken = set()
        for p, fd, fn, dna, rating, verdict in sorted(favs, key=lambda f: (-(f[4] or 0), f[0]['name'])):
            ff = short83(p['name'], ftaken, '.BSP')
            files['FAVORITE/%s' % ff] = (crlf(dna + '\n'), 'Favourites/%s.bsp' % re.sub(r'[\\/:*?"<>|]', '', p['name']))
        # a pack's own sounds (the gardens packs): the NAMEs its presets use that the stock library disc lacks
        lib_lines, credits = [], set()
        if pk.get('new'):
            from common import dna_names, BUILTIN
            stock = stock_names()
            cat = catalog()
            used = sorted({n for p in ps for n in dna_names(p['canonical']) if n not in BUILTIN and n not in stock})
            staken = set()
            for n in used:
                e = cat.get(n)
                src = e and os.path.join(LIB, 'sources', e['category'], n + '.wav')
                if not src or not os.path.exists(src): raise SystemExit('missing sound %s for %s' % (n, pk['id']))
                fn = short83(n.replace('gd_', '').replace('pw_', 'pw'), staken, '.WAV')
                data = open(src, 'rb').read()
                files['SOUNDS/' + fn] = (data, 'Sounds/%s.wav' % n)
                secs = (len(data) - 44) / 2 / 22050
                lib_lines.append('%s\t%s\t\\SOUNDS\\%s\t%.2f\t%s' % (n, e['category'], fn, secs, e.get('license', '') if e.get('author', '') in e.get('license', '') else '%s, %s' % (e.get('author', ''), e.get('license', ''))))
                credits.add(e.get('author', ''))
        nxp = sum('XP' in p['ships'] for p in ps)
        n311 = sum('3.11' in p['ships'] for p in ps)
        info = [('Id', pk['id']), ('Title', title), ('Product', '%s by %s' % (PRODUCT, MAKER)), ('Version', pp.get('version') or kv.get('Version') or '1.0'),
                ('Author', kv.get('Author') or pp.get('maker') or ''), ('Date', pp.get('date') or kv.get('Date', '')), ('Presets', str(len(ps))),
                ('Presets311', str(n311)), ('PresetsXP', str(nxp)), ('Favourites', str(len(favs))), ('Description', pk['blurb'])]
        files['PACK.INF'] = (crlf('[Pack]\n' + ''.join('%s=%s\n' % kv_ for kv_ in info)), 'PACK.INF')
        txt = '%s\n%s\n\nA sound pack for %s by %s (Windows 3.11).\n\n' % (title, '=' * len(title), PRODUCT, MAKER) + ''.join('%s: %s\n' % kv_ for kv_ in info)
        if pk.get('new'):
            txt += '\nSounds on this disc (SOUNDS\\, listed in LIBRARY.TSV):\n' + ''.join('  %s\n' % c for c in sorted(credits) if c)
            txt += '  Rendered from William Sharkey\'s own instruments in midigarden / Bele Dance and ghosts.garden.\n'
            if any('Paul Chauncy' in c for c in credits):
                txt += '  Sounds by Paul Chauncy (Uncle Homunculus / Paulywauly): permission from the author, via the owner, 2026-11-14.\n'
        txt += '\nFavourites (the owner\'s picks): FAVORITE\\\n' + ''.join('  %s (%s)\n' % (f[0]['name'], f[0]['category']) for f in favs)
        files['PACK.TXT'] = (crlf(txt), 'PACK.TXT')
        files['AUTORUN.INF'] = (crlf('[autorun]\nlabel=%s\n' % title[:32]), 'AUTORUN.INF')
        files['PRESETS.TSV'] = (crlf('# %s by %s presets: category\tname\tDNA\tpack\teditions\trating\tverdict\tfile\n' % (PRODUCT, MAKER) + '\n'.join(rows) + '\n'), 'PRESETS.TSV')
        files['LIBRARY.TSV'] = (crlf('# name\tcategory\tpath\tseconds\tsource/licence\n' + ''.join(l + '\n' for l in lib_lines)), 'LIBRARY.TSV')
        # the folder copy and the ISO
        root = os.path.join(outdir, label)
        for path, (data, _) in files.items():
            fp = os.path.join(root, *path.split('/'))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, 'wb').write(data)
        iso = pycdlib.PyCdlib()
        iso.new(interchange_level=1, joliet=3, vol_ident=label[:32], sys_ident='BASILISK',
                app_ident_str='BASILISK PRESET LIBRARY')
        dirs = sorted({p.split('/')[0] for p in files if '/' in p})
        for d in dirs:
            jl = next(j for p, (_, j) in files.items() if p.startswith(d + '/')).split('/')[0]
            iso.add_directory('/' + d, joliet_path='/' + jl)
        for path, (data, jpath) in sorted(files.items()):
            iso.add_fp(io.BytesIO(data), len(data), '/' + path + ';1', joliet_path='/' + jpath)
        isop = os.path.join(outdir, label + '.ISO')
        iso.write(isop); iso.close()
        index.append('\t'.join([pk['id'], label, label + '.ISO', title, str(len(ps)), str(n311), str(nxp), str(len(favs))]))
        print('%-22s %-12s %4d presets, %3d favourites, %6d bytes' % (pk['id'], label, len(ps), len(favs), os.path.getsize(isop)))
    open(os.path.join(outdir, 'DISCS.TSV'), 'w', newline='\r\n').write(
        '# %s by %s sound pack discs: id\tlabel\tiso\ttitle\tpresets\tpresets_311\tpresets_xp\tfavourites\n' % (PRODUCT, MAKER) + '\n'.join(index) + '\n')


if __name__ == '__main__':
    main()
