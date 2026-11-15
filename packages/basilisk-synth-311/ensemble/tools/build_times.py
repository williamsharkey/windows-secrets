#!/usr/bin/env python3
"""How long Windows takes to build each preset of an album (album.json from album_parts.py), on lane 0 of the Ensemble
machine, in Windows' own milliseconds.   build_times.py MACHINE CORE ALBUM.json OUT.json"""
import os, sys, time, json, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import bsdrv
from bsdrv import Engine
machine, core, album, outp = sys.argv[1:5]
a = json.load(open(album))
dnas = []
for t in a:
    for p in t['parts']:
        if p['dna'] not in [d for d, _ in dnas]: dnas.append((p['dna'], p['label']))
out = os.path.dirname(os.path.abspath(outp)) + '/bt'; os.makedirs(out + '/rec', exist_ok=True)
s = open(os.path.join(machine, 'w31.conf')).read().replace('@MACHINE@', '"%s"' % machine).replace('@DRIVE@', '"%s/drive"' % machine).replace('@RECDIR@', '"%s/rec"' % out).replace('@PACKS@', '"%s/packs"' % machine)
open(out + '/w31.conf', 'w').write(s)
e = Engine(out + '/w31.conf', state=os.path.join(machine, 'w31.state'), core=core, log=out + '/engine.log', name='ensbt%d' % os.getpid())
e.u32('vid_want', 0); e.u32('offline', 1)
def run(sec): struct.pack_into('<Q', e.m, bsdrv.OFF['grant_until'], e.dac_w() + int(sec * 48000))
res = {}
try:
    while e.state() < 2: time.sleep(0.05)
    ids = []
    for l in open(os.path.join(machine, 'packs', 'PACKS.TSV')):
        f = l.split('\t')
        if len(f) > 2: ids.append(f[1])
    e.line('packs ' + ','.join(ids)); e.line('go')
    while not any(x == 'ready' for x in e.texts): run(1); e.poll(); time.sleep(0.01)
    for i, (d, lab) in enumerate(dnas):
        kit = ';' in d and any(tok.startswith('k') and tok[1:2].isdigit() for tok in d.split(';')[1].replace('k', ' k').split())
        cap = 16 if kit else 8
        n0 = len(e.texts); t0 = time.time()
        e.line('@0 cap %d' % cap); e.line('@0 dna ' + d)
        while not any(x.startswith('@0 built') for x in e.texts[n0:]):
            run(0.5); e.poll(); time.sleep(0.005)
            if time.time() - t0 > 300: break
        b = [x for x in e.texts[n0:] if x.startswith('@0 built')]
        ms = int(b[0].split()[2]) if b else -1
        res[d] = dict(label=lab, cap=cap, ms=ms, wall=round(time.time() - t0, 2))
        print('%2d %-38s cap %2d %6d ms (Windows) %5.1f s wall' % (i, lab[:38], cap, ms, time.time() - t0), flush=True)
finally:
    e.close()
json.dump(res, open(outp, 'w'), indent=1)
