#!/usr/bin/env python3
"""A songs-lane .song -> an mtrender job: one lane per track (its DNA and its own MIDI file, exactly what
songrender.py hands render311 for that track's stem).   song2lanes.py SONG MACHINE OUTDIR [--repeat N]
--repeat N: the song's tracks N times over (more lanes from one song, for the lane-count sweep)."""
import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'tools', 'songrender'))
import songrender as sr
song_path, machine, out = sys.argv[1:4]
rep = int(sys.argv[sys.argv.index('--repeat') + 1]) if '--repeat' in sys.argv else 1
os.makedirs(out, exist_ok=True)
song = sr.Song(song_path)
args = types.SimpleNamespace(render311=os.path.join(machine, '..', 'render311'), machine=machine, engine='host', plugin_id='mt', cache=out)
jobs = sr.plan(song, args)
with open(os.path.join(out, 'job.txt'), 'w') as f:
    f.write('bpm %.6f\ntail %g\n' % (song.bpm, jobs[0].tail))
    k = 0
    for r in range(rep):
        for j in jobs:
            p = os.path.join(out, 'k%02d.mid' % k)
            open(p, 'wb').write(j.midi_bytes)
            f.write('lane %s %s\n' % (p, j.dna)); k += 1
print('%d lanes: %s' % (k, ', '.join(j.track.name for j in jobs)), 'bpm %.2f' % song.bpm, 'length %.1f s' % song.length_s)
