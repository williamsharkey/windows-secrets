#!/usr/bin/env python3
"""Sound Pack Explorer previews on the release build: one clip per preset, its demo phrase chosen per preset
(demophrases.py: role, pack mood, envelope; seeded by id), levelled to -16 LUFS, MP3 48 kbps + Opus 24 kbps.

    LIBBUILD_V3=<release build> previews.py [--out ~/libbuild/previews] [--parallel 4] [--only slug ...]   data/library.json
Writes OUT/<slug>.{mp3,ogg}, OUT/manifest.json and OUT/index.json (the same list).
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json
import demophrases, phrases, render
from recheck import encode
from make_discs import ratings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser('~/libbuild/previews')); ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--build', default=os.environ.get('SNDWAVE_BUILD', '?'))
    ap.add_argument('--only', nargs='+', help='re-render just these slugs and merge them into OUT/manifest.json')
    a = ap.parse_args()
    L = load_json('library.json'); R = ratings()
    if a.only: L = [p for p in L if p['slug'] in set(a.only)]
    os.makedirs(a.out, exist_ok=True)
    jobs, meta = [], []
    for p in L:
        dna = p['dna_final']
        pads = phrases.kit_pads(dna) if p['category'] == 'Kit' else None
        m = re.search(r';[^;]*?A(\d+)', dna)
        notes, tail, label, pid = demophrases.phrase_for(p, pads, bool(m and int(m.group(1)) >= 250))
        jobs.append(dict(dna=dna, score=notes, tail=tail, kind=p['kind'], keep=True)); meta.append((p, label, pid))
    res = render.render_all(jobs, a.parallel, progress=True)
    index = []
    for (p, label, pid), j, r in zip(meta, jobs, res):
        wav = render.wav_path(j['dna'], j['score'], j['tail'])
        if not r.get('ok') or not os.path.exists(wav):
            print('no render:', p['slug']); continue
        I, dur, pk = encode(wav, os.path.join(a.out, p['slug']))
        os.remove(wav)
        rat = R.get(p['slug'], {})
        c = p.get('check311') or {}
        index.append({'slug': p['slug'], 'pack': p['pack'], 'pack_name': p['pack_name'], 'category': p['category'], 'name': p['name'],
                      'dna': p.get('canonical') or p['dna_final'], 'recipe_one': p.get('recipe_one'), 'recipe': p.get('recipe'),
                      'mp3': p['slug'] + '.mp3', 'ogg': p['slug'] + '.ogg', 'seconds': dur, 'peak_dbfs': pk, 'lufs': I,
                      'phrase': label, 'phrase_id': pid, 'heard': r.get('heard'), 'onsets': r.get('onsets'),
                      'ok': c.get('ok', True), 'flags': c.get('why', []), 'rating': rat.get('rating'), 'verdict': rat.get('verdict'),
                      'edition': p['edition'], 'v3': p['v3'], 'tags': p.get('tags', [])})
    doc = {'build': a.build, 'renderer': 'render311 (%s)' % a.build, 'lufs_target': -16, 'mp3': '48 kHz mono 48 kbps',
           'ogg': 'Opus mono 24 kbps', 'fade_s': 0.2, 'phrases': 'demophrases.py (original phrases, per role, pack mood and envelope)',
           'presets': index}
    if a.only:
        old = json.load(open(os.path.join(a.out, 'manifest.json')))
        new = {e['slug']: e for e in index}
        doc['presets'] = [new.pop(e['slug'], e) for e in old['presets']] + list(new.values())
        index = doc['presets']
    for f in ('manifest.json', 'index.json'):
        json.dump(doc, open(os.path.join(a.out, f), 'w'), indent=1)
    tot = sum(os.path.getsize(os.path.join(a.out, f)) for f in os.listdir(a.out))
    print('previews: %d of %d presets, %.1f MB -> %s' % (len(index), len(L), tot / 1e6, a.out))


if __name__ == '__main__':
    main()
