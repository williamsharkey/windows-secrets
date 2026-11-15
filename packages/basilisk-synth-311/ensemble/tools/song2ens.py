#!/usr/bin/env python3
"""A songs-lane .song -> an Ensemble test: lanes.txt (ENSEMBLE_LANES: each track's pack, preset and DNA on lane k),
ens.mid (every track's events on MIDI channel k+1, as songrender extracts them: transpose, velocity, tune bend), and an
mtrender job with each track's own MIDI (the render311 baseline).
  song2ens.py SONG MACHINE OUTDIR [--lanes 10] [--skip name,name]"""
import os, sys, types, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'tools', 'songrender'))
import songrender as sr
song_path, machine, out = sys.argv[1:4]
opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
NB = int(opt('--lanes', '10')); skip = set(x for x in opt('--skip', '').split(',') if x)
os.makedirs(out, exist_ok=True)
song = sr.Song(song_path)
args = types.SimpleNamespace(render311='x', machine=machine, engine='host', plugin_id='ens', cache=out)
jobs = [j for j in sr.plan(song, args) if j.track.name not in skip]
if len(jobs) > NB: print('note: %d tracks, %d lanes: dropped %s' % (len(jobs), NB, ', '.join(j.track.name for j in jobs[NB:]))); jobs = jobs[:NB]
def vlq(n):
    b = [n & 0x7F]; n >>= 7
    while n: b.insert(0, (n & 0x7F) | 0x80); n >>= 7
    return bytes(b)
def events(mid):   # (tick, bytes) of a type-0/1 file from songrender (one track), with its division and tempo events
    d = open(mid, 'rb').read(); div = struct.unpack('>H', d[12:14])[0]; p = 14; ev = []
    while p < len(d):
        ln = struct.unpack('>I', d[p + 4:p + 8])[0]; q = p + 8; end = q + ln; t = 0; run = 0
        while q < end:
            dt = 0
            while True:
                c = d[q]; q += 1; dt = (dt << 7) | (c & 0x7F)
                if not c & 0x80: break
            t += dt; st = d[q]
            if st & 0x80: q += 1
            else: st = run
            if st == 0xFF:
                ty = d[q]; q += 1; l = 0
                while True:
                    c = d[q]; q += 1; l = (l << 7) | (c & 0x7F)
                    if not c & 0x80: break
                if ty == 0x51: ev.append((t, bytes([0xFF, 0x51, 3]) + d[q:q + 3]))
                q += l
            elif st in (0xF0, 0xF7):
                l = 0
                while True:
                    c = d[q]; q += 1; l = (l << 7) | (c & 0x7F)
                    if not c & 0x80: break
                q += l
            else:
                run = st; n = 1 if st & 0xF0 in (0xC0, 0xD0) else 2
                ev.append((t, bytes([st]) + d[q:q + n])); q += n
        p = end
    return div, ev
allev = []; div0 = None; lanev = []
with open(os.path.join(out, 'lanes.txt'), 'w') as lf, open(os.path.join(out, 'job.txt'), 'w') as jf:
    jf.write('bpm %.6f\ntail %g\n' % (song.bpm, jobs[0].tail))
    for k, j in enumerate(jobs):
        p = os.path.join(out, 'k%02d.mid' % k); open(p, 'wb').write(j.midi_bytes)
        jf.write('lane %s %s\n' % (p, j.dna))
        pk, nm = (j.label.split(':', 1) + [''])[:2] if ':' in j.label else ('', j.label)
        lf.write('lane %d\t%s\t%s\t%s\n' % (k, pk, nm, j.dna))
        div, ev = events(p); div0 = div0 or div
        lanev.append((p, div, ev))
        for t, b in ev:
            if b[0] == 0xFF:
                if k == 0: allev.append((t * div0 // div, 0, b))
            else: allev.append((t * div0 // div, 1, bytes([(b[0] & 0xF0) | k]) + b[1:]))
allev.sort(key=lambda e: (e[0], e[1], 0 if (e[2][0] & 0xF0) == 0x80 or ((e[2][0] & 0xF0) == 0x90 and len(e[2]) > 2 and e[2][2] == 0) else 1))
until = float(opt('--until', '0'))
if until > 0:   # only the first seconds (one tempo assumed): later note-ons dropped, their offs kept at the limit
    lim = int(until * song.bpm / 60 * div0)
    allev = [(min(t, lim), o, b) for t, o, b in allev if t < lim or (b[0] & 0xF0) == 0x80 or ((b[0] & 0xF0) == 0x90 and len(b) > 2 and b[2] == 0)]
    allev.sort(key=lambda e: (e[0], e[1]))
def write(path, evs, div):
    trk = b''; last = 0
    for t, _, b in evs: trk += vlq(t - last) + b; last = t
    trk += b'\x00\xFF\x2F\x00'
    open(path, 'wb').write(b'MThd' + struct.pack('>IHHH', 6, 0, 1, div) + b'MTrk' + struct.pack('>I', len(trk)) + trk)
if '--grid' in sys.argv:
    # every event a quarter-sample after a 48 kHz sample: render311 (floor) and a host (round) give the same sample.
    # One tempo assumed (the song's). Ticks of 1/192000 s: division 480, 2500 us a quarter.
    def regrid(evs, div):
        o = []
        for t, ordk, b in evs:
            if b[0] == 0xFF: continue
            sec = t * 60.0 / (song.bpm * div)
            if until > 0 and sec >= until:
                if not ((b[0] & 0xF0) == 0x80 or ((b[0] & 0xF0) == 0x90 and len(b) > 2 and b[2] == 0)): continue
                sec = until
            o.append((4 * int(round(sec * 48000)) + 1, ordk, b))
        o.sort(key=lambda e: (e[0], 0 if (e[2][0] & 0xF0) == 0x80 or ((e[2][0] & 0xF0) == 0x90 and len(e[2]) > 2 and e[2][2] == 0) else 1))
        return [(0, 0, bytes([0xFF, 0x51, 3, 0x00, 0x09, 0xC4]))] + o
    allev = regrid(allev, div0)
    for p, div, ev in lanev:
        write(p, regrid([(t, 1, b) for t, b in ev], div), 480)
    div0 = 480
write(os.path.join(out, 'ens.mid'), allev, div0)
print('%d lanes: %s; %.1f s, bpm %.1f' % (len(jobs), ', '.join('%d %s' % (k, j.track.name) for k, j in enumerate(jobs)), song.length_s, song.bpm))
