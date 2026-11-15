#!/usr/bin/env python3
"""A whole album for one SNDWAVE1993 Ensemble instance: which part plays on which lane in every track, when each lane
switches preset, and every note, on one timeline.   album_ens.py TRACKS_DIR MACHINE MIXDIR BUILDTIMES.json OUT.ens [--lanes 10] [--gap 1.5]
- Up to 10 lanes a track: parts that never overlap share a lane; then, while there are too many, the quietest ambience
  goes (one ambience stays), then the doublings, then the hand percussion, then the quietest part.
- A lane keeps its preset when the next track uses the same one; otherwise the part goes to the lane that falls silent
  earliest, so the switch has the longest gap. A switch is built as soon as its lane's previous part has rung out.
- Output (text, one record a line):
    T <i> <start> <end> <title>
    S <id> <lane> <track> <tBuild> <tFirst> <tEnd> <cap> <level> <pan> <pack>\\t<name>\\t<dna>
    N <t> <seg> <status> <d1> <d2>
"""
import os, sys, json, types, glob, re, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'tools', 'songrender'))
import songrender as sr
tdir, machine, mixdir, btp, outp = sys.argv[1:6]
opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
NB = int(opt('--lanes', '10')); GAP = float(opt('--gap', '1.5')); TAIL = 3.0
bt = json.load(open(btp))
AMB = ['room', 'vinyl', 'rain', 'lobby', 'night', 'street', 'static', 'dawn', 'harbour', 'phone', 'glasses', 'cafe', 'spoon', 'wand', 'train', 'crossing', 'chime']
DOUBLE = {'09': ['synth'], '03': ['synlead'], '01': ['pad'], '08': ['choir'], '10': ['choir'], '12': ['choir']}
SHARE = {'05': [('phone', 'bell')], '12': [('synth', 'bell')], '02': [('cafe', 'spoon')], '07': [('crossing', 'train')]}
QUIET = ('pad', 'choir', 'bell', 'chime', 'box', 'cloud', 'glass')   # (the album lane: pads, choir and bells 2 dB down, no reverb here)

def notes_of(midi):   # (seconds, status, d1, d2) of a one-track SMF, tempo map applied
    d = midi; div = struct.unpack('>H', d[12:14])[0]; p = 14; raw = []
    while p + 8 <= len(d):
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
                if ty == 0x51: raw.append((t, 0, ('tempo', (d[q] << 16) | (d[q + 1] << 8) | d[q + 2])))
                q += l
            elif st in (0xF0, 0xF7):
                l = 0
                while True:
                    c = d[q]; q += 1; l = (l << 7) | (c & 0x7F)
                    if not c & 0x80: break
                q += l
            else:
                run = st; n = 1 if st & 0xF0 in (0xC0, 0xD0) else 2
                raw.append((t, 1, (st, d[q], d[q + 1] if n == 2 else 0))); q += n
        p = end
    raw.sort(key=lambda e: (e[0], e[1]))
    sec, last, spt, out = 0.0, 0, 0.5 / div, []
    for t, k, v in raw:
        sec += (t - last) * spt; last = t
        if k == 0: spt = v[1] / 1e6 / div; continue
        out.append((sec, v[0] & 0xF0, v[1], v[2]))
    return out

def cap_of(dna, evs):
    g = dna.split(';', 1)[1] if ';' in dna else ''
    if re.search(r'(^|[^a-z])k\d', g): return 16
    m = re.search(r'R(\d+)', g); rel = (int(m.group(1)) if m else 120) / 1000.0 + 0.05
    on, edges = {}, []
    for t, st, a, b in evs:
        if st == 0x90 and b: on.setdefault(a, []).append(t)
        elif st in (0x80, 0x90) and on.get(a): edges += [(on[a].pop(0), 1), (t + rel, -1)]
    for a in on:
        for t in on[a]: edges.append((t, 1))
    edges.sort(); cur = peak = 0
    for t, d in edges: cur += d; peak = max(peak, cur)
    layers = [l for l in dna.split(';')[0].split('/') if l]
    per = 0
    for l in layers:
        h = re.search(r'H([0-9,\-]+)', l); u = re.search(r'U(\d+)', l)
        per += (len(h.group(1).split(',')) if h else 1) * (int(u.group(1)) if u else 1)
    return max(len(layers), min(16, max(1, peak) * max(1, per)))

MAXCAP = int(opt('--maxcap', '16'))
KIT_RING = 1.2   # seconds a drum-kit hit is counted as sounding (one-shots: no note-off)
def exact_pools(dna, evs):
    """Each layer's pool cut to what this part plays at most at once (its keys, chords x unison, the pedal, the release
    tail), never above the pool the preset gives it: (dna with every layer's #N written out, total recorders)."""
    head, _, g = dna.partition(';')
    layers = head.split('/')
    if any(re.search(r'B\d', l) for l in layers) or len(layers) > 8: return dna, cap_of(dna, evs)
    m = re.search(r'R(\d+)', g); rel = (int(m.group(1)) if m else 120) / 1000.0 + 0.05
    kit = bool(re.search(r'(^|[^a-z])k\d', g))
    # the preset's own pools (as the guest's dna_parse gives them out of 16)
    pools = [int(re.search(r'#(\d+)', l).group(1)) if re.search(r'#(\d+)', l) else 0 for l in layers]
    left = 16; cnt = [0] * len(layers); nv = len(layers)
    for k, pl in enumerate(pools):
        if not pl: continue
        later = (nv - k - 1) + sum(1 for j in range(k) if not pools[j])
        give = min(pl, left - later); give = give if give >= 1 else (1 if left > 0 else 0); cnt[k] = give; left -= give
    free = [k for k in range(nv) if not pools[k]]
    for i, k in enumerate(free):
        if left > 0: cnt[k] = left // len(free) + (1 if i < left % len(free) else 0)
    # the notes' spans, the pedal holding key-ups
    spans, on, ped, held = [], {}, False, []
    for t, st, a, b in evs:
        if st == 0xB0 and a == 64:
            down = b >= 64
            if ped and not down:
                for (n, t0) in held: spans.append((n, t0, t))
                held = []
            ped = down
        elif st == 0x90 and b: on.setdefault(a, []).append(t)
        elif st in (0x80, 0x90) and on.get(a):
            t0 = on[a].pop(0)
            if ped: held.append((a, t0))
            else: spans.append((a, t0, t))
    end = evs[-1][0] if evs else 0
    for a in on:
        for t0 in on[a]: spans.append((a, t0, end))
    for (n, t0) in held: spans.append((n, t0, end))
    out, total = [], 0
    for k, l in enumerate(layers):
        z = re.search(r'Z(\d+),(\d+)', l); lo, hi = (int(z.group(1)), int(z.group(2))) if z else (0, 127)
        h = re.search(r'H([0-9,\-]+)', l); u = re.search(r'U(\d+)', l)
        per = (len([x for x in h.group(1).split(',') if x != '']) if h else 1) * (int(u.group(1)) if u else 1)
        ed = []
        for (n, t0, t1) in spans:
            if lo <= n <= hi: ed += [(t0, per), ((t0 + max(rel, KIT_RING)) if kit else (t1 + rel), -per)]
        ed.sort(key=lambda e: (e[0], e[1])); c = pk = 0
        for _, d in ed: c += d; pk = max(pk, c)
        want = max(1, min(cnt[k] or 1, pk))
        l2 = re.sub(r'#\d+', '#%d' % want, l) if '#' in l else l + '#%d' % want
        out.append(l2); total += want
    # at most MAXCAP recorders a part (USER's heap holds them all): the biggest pools give, one recorder at a time
    pools2 = [int(re.search(r'#(\d+)', l).group(1)) for l in out]
    while sum(pools2) > MAXCAP:
        i = max(range(len(pools2)), key=lambda j: pools2[j])
        if pools2[i] <= 1: break
        pools2[i] -= 1
    out = [re.sub(r'#\d+', '#%d' % pools2[k], l) for k, l in enumerate(out)]
    return '/'.join(out) + (';' + g if _ else ''), sum(pools2)

tracks = []
for sp in sorted(glob.glob(os.path.join(tdir, '[0-9]*.song'))):
    song = sr.Song(sp); num = os.path.basename(sp)[:2]
    args = types.SimpleNamespace(render311='x', machine=machine, engine='host', plugin_id='p', cache='/tmp')
    jobs = sr.plan(song, args)
    mix = {}
    mj = glob.glob(os.path.join(mixdir, num + '-*.json'))
    if mj: mix = {m['track']: m for m in json.load(open(mj[0]))['mix']['tracks']}
    parts = []
    for j in jobs:
        evs = notes_of(j.midi_bytes)
        ons = [e[0] for e in evs if e[1] == 0x90 and e[3]]
        if not ons: continue
        g = mix.get(j.track.name, {}).get('gain_db', 0.0) - (2.0 if j.track.name in QUIET or j.track.name.startswith(QUIET) else 0.0)
        pk, nm = j.label.split(':', 1) if ':' in j.label else ('', j.label)
        dna, cap = (j.dna, cap_of(j.dna, evs)) if '--full-pools' in sys.argv else exact_pools(j.dna, evs)
        parts.append(dict(name=j.track.name, pack=pk, label=nm, dna=dna, evs=evs, first=min(ons), last=max(e[0] for e in evs),
                          cap=cap, gain=g, pan=getattr(j.track, 'pan', 0) or 0, lufs=mix.get(j.track.name, {}).get('lufs', -30)))
    # parts that share a lane (never at once)
    groups = [[p] for p in parts]
    for a, b in SHARE.get(num, []):
        ga = next((g for g in groups if g[0]['name'] == a), None); gb = next((g for g in groups if g[0]['name'] == b), None)
        if ga and gb and ga is not gb: ga += gb; groups.remove(gb)
    dropped = []
    def drop(pred, keep_one=False):
        c = [g for g in groups if pred(g[0])]
        c.sort(key=lambda g: g[0]['lufs'])
        while len(groups) > NB and len(c) > (1 if keep_one else 0):
            g = c.pop(0); groups.remove(g); dropped.append(g[0]['name'])
    drop(lambda p: p['name'] in AMB, keep_one=True)
    drop(lambda p: p['name'] in DOUBLE.get(num, []))
    drop(lambda p: p['name'] == 'perc')
    drop(lambda p: True)
    tracks.append(dict(num=num, title=song.meta.get('title', num), groups=groups, dropped=dropped, end=max(p['last'] for g in groups for p in g) + TAIL))
    print('%s %-34s %2d parts -> %2d lanes; dropped %s' % (num, tracks[-1]['title'][:34], len(parts), len(groups), ', '.join(dropped) or '-'))

# the timeline and the lanes
t0 = 0.0; lanes = [dict(dna=None, free=0.0, name=None) for _ in range(NB)]
segs, notes, out = [], [], []
def rel_of(dna):
    m = re.search(r';[^;]*?R(\d+)', dna); return (int(m.group(1)) if m else 120) / 1000.0 + 0.1
for ti, tr in enumerate(tracks):
    start = t0; end = t0 + tr['end']
    out.append('T %d %.6f %.6f %s' % (ti, start, end, tr['title']))
    used = set()
    # first: groups whose preset a lane already holds; then by first note, each to the lane that has been silent longest
    order = sorted(tr['groups'], key=lambda g: g[0]['first'])
    assign = {}
    for g in order:
        for k in range(NB):
            if k not in used and lanes[k]['dna'] == g[0]['dna']: assign[id(g)] = k; used.add(k); break
    for g in order:
        if id(g) in assign: continue
        free = [k for k in range(NB) if k not in used]
        same = [k for k in free if lanes[k]['name'] == g[0]['name']]   # a part of the same role keeps its lane
        k = same[0] if same else min(free, key=lambda k: lanes[k]['free'])
        assign[id(g)] = k; used.add(k)
    for g in tr['groups']:
        k = assign[id(g)]
        for p in sorted(g, key=lambda p: p['first']):
            sid = len(segs)
            tFirst = start + p['first']; tEnd = start + p['last'] + rel_of(p['dna'])
            tBuild = lanes[k]['free']   # (the same preset as before: no build, the switch is only the mix and the name)
            lvl = max(0, min(127, round(100 * 10 ** (p['gain'] / 40.0))))
            pan = max(-64, min(63, round(p['pan'] * 64 / 100)))
            segs.append(dict(id=sid, lane=k, track=ti, tBuild=tBuild, tFirst=tFirst, tEnd=tEnd, cap=p['cap'],
                             level=lvl, pan=pan, pack=p['pack'], name=p['label'], dna=p['dna'], part=p['name']))
            for t, st, a, b in p['evs']: notes.append((start + t, sid, st, a, b))
            lanes[k].update(dna=p['dna'], free=tEnd, name=p['name'])
    t0 = end + GAP
for s in segs:
    out.append('S %d %d %d %.6f %.6f %.6f %d %d %d %s\t%s\t%s' % (s['id'], s['lane'], s['track'], s['tBuild'], s['tFirst'], s['tEnd'], s['cap'], s['level'], s['pan'], s['pack'], s['name'], s['dna']))
notes.sort(key=lambda n: (n[0], 0 if n[2] == 0x80 or (n[2] == 0x90 and n[4] == 0) else 1))
for t, sid, st, a, b in notes: out.append('N %.6f %d %d %d %d' % (t, sid, st, a, b))
open(outp, 'w').write('\n'.join(out) + '\n')
# the plan's own estimate: builds in one queue (Windows builds one lane at a time), at the measured speeds
q = 0.0; late = 0; rows = {}
prevdna = {}
for s in sorted(segs, key=lambda s: s['tBuild']):
    same = prevdna.get(s['lane']) == s['dna']; prevdna[s['lane']] = s['dna']
    if same: continue
    b = bt.get(s['dna'], {}).get('ms', 500) / 1000.0 * max(1, s['cap']) / max(1, bt.get(s['dna'], {}).get('cap', 8))
    st = max(q, s['tBuild']); q = st + b
    n = sum(1 for t, sid, stt, a, v in notes if sid == s['id'] and stt == 0x90 and v and t < q)
    r = rows.setdefault(s['track'], [0, 0]); r[0] += 1; r[1] += n
print('album %.1f s, %d segments, %d notes' % (t0, len(segs), sum(1 for n in notes if n[2] == 0x90 and n[4])))
for ti, tr in enumerate(tracks): print('  %s switches %2d, notes before their build (estimate) %d' % (tr['num'], rows.get(ti, [0, 0])[0], rows.get(ti, [0, 0])[1]))
