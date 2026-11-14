#!/usr/bin/env python3
"""make_index: the site's song list (index.json) from songrender's reports.

    make_index.py OUT_DIR [OUT_DIR ...] --dest DIR [--base-url URL]

Copies each song's .ogg and .mp3 into DIR/<pack>/ and writes DIR/index.json:
  {"generated": ..., "packs": {"<pack id>": {"title": ..., "songs": [{title, kind, source, composer, licence,
   proof, credits, seconds, length, presets, ogg, mp3, sha256}]}}}
"""
import argparse, hashlib, json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DISCS = os.path.join(HERE, '..', '..', 'packages', 'basilisk-synth', 'library', 'packs', 'out', 'discs', 'DISCS.TSV')
KIND_ORDER = {'original': 0, 'world': 1, 'classical': 1, 'chiptune': 2}


def pack_titles():
    t = {}
    for l in open(DISCS, encoding='utf-8'):
        if l.startswith('#'):
            continue
        f = l.rstrip('\n').split('\t')
        if len(f) > 3:
            t[f[0]] = f[3]
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dirs', nargs='+')
    ap.add_argument('--dest', required=True)
    ap.add_argument('--base-url', default='')
    a = ap.parse_args()
    titles = pack_titles()
    packs = {}
    for d in a.dirs:
        for f in sorted(os.listdir(d)):
            if not f.endswith('.json') or f == 'index.json':
                continue
            r = json.load(open(os.path.join(d, f)))
            if 'meta' not in r:
                continue
            m, slug, pk = r['meta'], f[:-5], r['pack']
            os.makedirs(os.path.join(a.dest, pk), exist_ok=True)
            files = {}
            for ext in ('ogg', 'mp3'):
                src = os.path.join(d, f'{slug}.{ext}')
                shutil.copy2(src, os.path.join(a.dest, pk, f'{slug}.{ext}'))
                files[ext] = f'{a.base_url}{pk}/{slug}.{ext}'
            presets = []
            for t in r['tracks']:
                if not t.get('muted') and t['preset'] not in presets:
                    presets.append(t['preset'])
            s = r['seconds']
            song = {
                'slug': slug, 'title': r['title'], 'kind': m.get('kind', 'original'),
                'source': m.get('source', ''), 'composer': m.get('composer', ''), 'arranger': m.get('arranger', ''),
                'licence': m.get('licence', ''), 'proof': m.get('proof', ''), 'credits': m.get('credit', ''),
                'note': m.get('note', ''), 'seconds': s, 'length': f'{int(s // 60)}:{int(s % 60):02d}',
                'bpm': round(r.get('bpm', 0), 1), 'presets': presets,
                'tracks': len([t for t in r['tracks'] if not t.get('muted')]),
                'ogg': files['ogg'], 'mp3': files['mp3'],
                'sha256': {'ogg': r.get('ogg_sha256'), 'mp3': r.get('mp3_sha256')},
            }
            p = packs.setdefault(pk, {'title': titles.get(pk, pk), 'songs': []})
            p['songs'] = [x for x in p['songs'] if x['slug'] != slug] + [song]
    for p in packs.values():
        p['songs'].sort(key=lambda x: (KIND_ORDER.get(x['kind'], 9), x['title']))
    out = {'format': 'sndwave2000-songs 1', 'renderer': 'tools/songrender (render311, SNDWAVE2000 1.3.0 machine)',
           'packs': dict(sorted(packs.items()))}
    json.dump(out, open(os.path.join(a.dest, 'index.json'), 'w'), indent=1, ensure_ascii=False)
    print(sum(len(p['songs']) for p in packs.values()), 'songs in', len(packs), 'packs ->', os.path.join(a.dest, 'index.json'))


if __name__ == '__main__':
    main()
