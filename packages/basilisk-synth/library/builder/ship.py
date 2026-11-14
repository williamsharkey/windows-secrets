#!/usr/bin/env python3
"""Ship format: the kept library as each plugin's preset table, plus metadata and .vstpreset files.

    ship.py      data/library.json -> out/

out/w311/<pack>.tsv     BASILISK 16 rows (category <TAB> name <TAB> DNA), the format of presets/b16.tsv and
                        library/presets/*.tsv; every kept preset (v2 and the v3 W/Y ones)
out/xp/<pack>.tsv       BASILISK SYNTH rows (factory.tsv's format); the v2 presets (v3 waits for XP's phase)
out/packs.json          per pack: name, blurb, counts, files
out/library.json        per preset: pack, category, name, DNA, edition badge, library flag, v3, ships, tags, recipe,
                        sources, lineage and research target, scores, render facts
out/vstpreset/<plugin>/<win|mac>/<Pack>/<Category> - <Name>.vstpreset
                        VST3 presets: the component state the DPF plugin writes (its state key and core State text)
                        under the plugin's class id, in Windows (COM GUID) and macOS (byte order) string forms
"""
import json, os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HERE, load_json, dna_names, display_name
from packs import PACKS

OUT = os.path.join(HERE, 'out')


def cconst(s):
    a, b, c, d = (ord(x) for x in s)
    return (a << 24) | (b << 16) | (c << 8) | d


def class_id(unique, brand='Wshk', win=True):
    words = [cconst('DPF '), cconst('clas'), cconst(unique), cconst(brand)]
    raw = b''.join(struct.pack('<I', w) for w in words)
    if not win:
        return raw.hex().upper()
    d1, d2, d3 = struct.unpack_from('<IHH', raw, 0)
    return '%08X%04X%04X%s' % (d1, d2, d3, raw[8:].hex().upper())


def vstpreset(cid, key, value):
    # DPF's state layout as BasiliskHost proved it: NUL-separated fields, ending 0xFE 0x00
    comp = b'__dpf_state_begin__\x00' + key.encode() + b'\x00' + value.encode() + b'\x00' + b'__dpf_state_end__\x00\xfe\x00'
    head = b'VST3' + struct.pack('<i', 1) + cid.encode('ascii')
    off = len(head) + 8
    lst_off = off + len(comp)
    lst = b'List' + struct.pack('<i', 1) + b'Comp' + struct.pack('<qq', off, len(comp))
    return head + struct.pack('<q', lst_off) + comp + lst


PLUGINS = {
    'BASILISK 16': dict(unique='B311', key='state', value=lambda d: 'BASILISK-SYNTH 1\ndna %s\nreference 0\n' % d),
    'BASILISK SYNTH': dict(unique='Bsyn', key='dna', value=lambda d: 'BASILISK-SYNTH 1\ndna %s\nreference 0\nver 1.2.1\n' % d),
}


def fname(s):
    return re.sub(r'[<>:"/\\|?*]+', '-', s).strip()


def main():
    L = load_json(os.environ.get('LIBJSON', 'library.json'))
    import shutil
    shutil.rmtree(os.path.join(OUT, 'vstpreset'), ignore_errors=True)
    os.makedirs(os.path.join(OUT, 'w311'), exist_ok=True); os.makedirs(os.path.join(OUT, 'xp'), exist_ok=True)
    # XP: the presets checked on the XP machine (xpcheck.py) that lose a quarter of their notes or fall silent there
    # ship to BASILISK 16 only; a measured level difference becomes the XP row's own G (peaks kept under -1 dBFS)
    from common import DNA
    for p in L:
        p['xp_dna'] = p['canonical']
        xc = p.get('xp_check')
        if not xc or 'XP' not in p['ships']: continue
        # the coordinator's rule for 1.2.1 (streaming gaps until 1.2.2): only a silent take, missing notes or layers, or the
        # wrong pitch keeps a preset off XP; levels are not changed from an XP 1.2.1 render
        if not xc['ok']:
            p['ships'] = ['3.11']; p['xp_excluded'] = xc['why']
    ch = [p for p in L if p['xp_dna'] != p['canonical']]
    if ch:
        import subprocess
        from common import RECIPE_CLI, MACHINE
        out = subprocess.run([RECIPE_CLI, os.path.join(MACHINE, 'library.names.txt')], input='\n'.join(p['xp_dna'] for p in ch) + '\n',
                             capture_output=True, text=True).stdout.splitlines()
        for p, l in zip(ch, out):
            r = json.loads(l); assert r['ok']; p['xp_dna'] = r['canonical']
    packs_out = []
    meta = []
    for pk in PACKS:
        ps = sorted([p for p in L if p['pack'] == pk['id']], key=lambda p: (p['category'], p['name']))
        if not ps: continue
        files = {}
        for ed, sel in (('w311', ps), ('xp', [p for p in ps if 'XP' in p['ships']])):
            path = os.path.join(OUT, ed, pk['id'] + '.tsv')
            with open(path, 'w', newline='\n', encoding='utf-8') as f:
                f.write('# %s: "%s" (library/builder, DNA.md). category <TAB> name <TAB> DNA\n' % (pk['name'], pk['blurb']))
                for p in sel:
                    f.write('%s\t%s\t%s\n' % (p['category'], p['name'], p['canonical'] if ed == 'w311' else p['xp_dna']))
            files[ed] = os.path.relpath(path, OUT)
        cats = {}
        for p in ps: cats[p['category']] = cats.get(p['category'], 0) + 1
        packs_out.append(dict(id=pk['id'], name=pk['name'], blurb=pk['blurb'], presets=len(ps),
                              xp=sum('XP' in p['ships'] for p in ps), w311_badge=sum(p['edition'] == 'w31' for p in ps),
                              v3=sum(p['v3'] for p in ps), library=sum(p['library'] for p in ps), categories=cats, files=files))
        for p in ps:
            meta.append(dict(pack=pk['id'], pack_name=pk['name'], category=p['category'], name=p['name'], dna=p['canonical'],
                             edition=p['edition'], badge='W3.11' if p['edition'] == 'w31' else 'XP', library=p['library'],
                             v3=p['v3'], ships=p['ships'], tags=p['tags'],
                             sources=sorted(set(display_name(n) for n in dna_names(p['canonical']))), origins=p['origins'],
                             recipe=p.get('recipe'), recipe_one=p.get('recipe_one'), recipe_ok=p.get('recipe_ok'),
                             lineage=p['lineage'], target=p['target'], target_name=p.get('target_name'), research=p['source'],
                             score=p['score'], novelty=p['novelty'], gain_db=p['G'], phrase=p['phrase'],
                             phrase_lufs=p.get('phrase_lufs'), phrase_peak_dbfs=p.get('phrase_peak'),
                             rendered_by='render311 (BASILISK 16, Windows 3.11 machine, main 4bda617)',
                             xp_check=p.get('xp_check'), xp_dna=p['xp_dna'] if 'XP' in p['ships'] else None,
                             xp_excluded=p.get('xp_excluded'), slug=p['slug']))
        # .vstpreset
        for plug, cfg in PLUGINS.items():
            sel = ps if plug == 'BASILISK 16' else [p for p in ps if 'XP' in p['ships']]
            for plat in ('win', 'mac'):
                cid = class_id(cfg['unique'], win=(plat == 'win'))
                d = os.path.join(OUT, 'vstpreset', plug, plat, fname(pk['name']))
                os.makedirs(d, exist_ok=True)
                for p in sel:
                    with open(os.path.join(d, fname('%s - %s' % (p['category'], p['name'])) + '.vstpreset'), 'wb') as f:
                        f.write(vstpreset(cid, cfg['key'], cfg['value'](p['canonical'] if plug == 'BASILISK 16' else p['xp_dna'])))
    # the .vstpreset folders are also zipped per plugin (the zips are what git keeps; the folders are regenerated)
    import shutil, zipfile
    for plug in PLUGINS:
        src = os.path.join(OUT, 'vstpreset', plug)
        zp = os.path.join(OUT, 'vstpreset-%s.zip' % plug.replace(' ', '-'))
        with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, _, fs in sorted(os.walk(src)):
                for f in sorted(fs):
                    full = os.path.join(root, f)
                    zi = zipfile.ZipInfo(os.path.relpath(full, os.path.join(OUT, 'vstpreset')), (2026, 11, 13, 0, 0, 0))
                    z.writestr(zi, open(full, 'rb').read(), zipfile.ZIP_DEFLATED)
    json.dump(packs_out, open(os.path.join(OUT, 'packs.json'), 'w'), indent=1)
    json.dump(meta, open(os.path.join(OUT, 'library.json'), 'w'), indent=1, ensure_ascii=False)
    print('%d presets in %d packs; xp %d; v3 %d' % (len(meta), len(packs_out), sum('XP' in m['ships'] for m in meta), sum(m['v3'] for m in meta)))
    for p in packs_out: print('  %-38s %4d  %s' % (p['name'], p['presets'], p['categories']))


if __name__ == '__main__':
    main()
