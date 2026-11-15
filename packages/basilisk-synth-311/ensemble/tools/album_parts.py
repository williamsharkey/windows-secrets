#!/usr/bin/env python3
"""Every part of every track of an album: preset, DNA, its notes' span, count and peak polyphony.
   album_parts.py ALBUM_TRACKS_DIR MACHINE OUT.json"""
import os, sys, json, types, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'tools', 'songrender'))
import songrender as sr
tdir, machine, out = sys.argv[1:4]
res = []
for sp in sorted(glob.glob(os.path.join(tdir, '[0-9]*.song'))):
    song = sr.Song(sp)
    args = types.SimpleNamespace(render311='x', machine=machine, engine='host', plugin_id='p', cache='/tmp')
    jobs = sr.plan(song, args)
    smf = sr.Smf.read(song.midi_path)
    parts = []
    for j in jobs:
        ex = smf.extract(song.selector(j.track), j.track.tr, j.track.vel)
        on = {}; spans = []; first = None; last = 0; n = 0; cur = 0; peak = 0
        evs = []
        for tr in ex.tracks:
            for tick, b in tr:
                if len(b) >= 3 and (b[0] & 0xF0) in (0x80, 0x90): evs.append((ex.seconds(tick), b[0] & 0xF0, b[1], b[2]))
        evs.sort(key=lambda e: (e[0], 0 if e[1] == 0x80 or e[3] == 0 else 1))
        for t, st, k, v in evs:
            if st == 0x90 and v: n += 1; cur += 1; peak = max(peak, cur); first = t if first is None else first; on[k] = on.get(k, 0) + 1
            elif on.get(k, 0): on[k] -= 1; cur -= 1; last = max(last, t)
        parts.append(dict(name=j.track.name, label=j.label, dna=j.dna, src=j.track.src, notes=n, first=first, last=last, poly=peak,
                          lufs=getattr(j.track, 'lufs', None), pan=getattr(j.track, 'pan', None), tune=getattr(j.track, 'tune', None)))
    res.append(dict(song=os.path.basename(sp), title=song.meta.get('title'), bpm=song.bpm, length=song.length_s, parts=parts))
    print('%-40s %5.1f s %2d parts: %s' % (os.path.basename(sp), song.length_s, len(parts), ', '.join('%s(%d,%.0f-%.0f)' % (p['name'], p['notes'], p['first'] or 0, p['last']) for p in parts)))
json.dump(res, open(out, 'w'), indent=1)
