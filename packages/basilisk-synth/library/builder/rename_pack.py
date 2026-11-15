#!/usr/bin/env python3
"""Rename a pack (the owner's decisions), keeping the old ids and names as aliases.

    rename_pack.py OLD_ID NEW_ID NEW_NAME [--renames packs/<folder>/RENAMES.TSV]   data/library.json -> the same

Each preset of the pack gets pack NEW_ID, pack_name NEW_NAME, its new name from RENAMES.TSV (category, old name,
new name) and a new slug; the old slug, name and pack id go into `aliases` (slugs, names, packs), so saved
projects, ratings and previews still resolve. The DNA does not change.
"""
import argparse, csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LIB, load_json, save_json
from finalize import slug


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('old'); ap.add_argument('new'); ap.add_argument('name'); ap.add_argument('--renames')
    a = ap.parse_args()
    ren = {}
    if a.renames:
        for l in open(os.path.join(LIB, a.renames), encoding='utf-8'):
            if l.startswith('#') or l.count('\t') < 2: continue
            c, o, n = l.rstrip('\r\n').split('\t')[:3]
            ren[(c, o)] = n
    L = load_json('library.json')
    taken = {p['name'].lower() for p in L if p['pack'] != a.old}
    done = 0
    for p in L:
        if p['pack'] != a.old: continue
        al = p.setdefault('aliases', {'slugs': [], 'names': [], 'packs': []})
        for k, v in (('slugs', p['slug']), ('names', p['name']), ('packs', p['pack'])):
            if v not in al[k]: al[k].append(v)
        new = ren.get((p['category'], p['name']), p['name'])
        if new.lower() in taken: sys.exit('name clash: %s' % new)
        p['pack'], p['pack_name'], p['name'] = a.new, a.name, new
        p['slug'] = slug(a.new + '-' + new)
        done += 1
    missing = set(ren) - {(p['category'], p['aliases']['names'][0]) for p in L if p['pack'] == a.new}
    if missing: sys.exit('renames with no preset: %s' % sorted(missing))
    save_json('library.json', L)
    print('%d presets: %s -> %s (%s)' % (done, a.old, a.new, a.name))


if __name__ == '__main__':
    main()
