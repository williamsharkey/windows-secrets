#!/usr/bin/env python3
"""Dropout check for a plugin capture or a finished video's soundtrack.

    dropouts.py FILE [FILE ...] [--from S --to S]

Counts, per file:
- gaps: runs of exact digital silence (|x| < 1e-6) of 5 to 80 ms where the sound just before and just after has a
  similar level (a buffer underrun cutting a sustained sound; rests between hits and notes are not counted);
- pops: second-derivative spikes anywhere (edit points, fades, gain steps, sample starts) over 0.01 and 20x the
  local level; with --notes, those within 80 ms after a note are counted apart as attacks;
- ticks: broadband bursts above ~5 kHz (an 8-bit sample starting or stopping off zero), at any point;
- clicks: sample-to-sample jumps larger than 0.25 and 12x the local (10 ms) RMS of the differences, out of sound
  (a jump out of near-silence is a note's attack).
Reports each with its time. The target is 0 of each.
"""
import json, subprocess, sys
import numpy as np

def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', '48000', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<f4')

import argparse
ap = argparse.ArgumentParser(); ap.add_argument('files', nargs='+'); ap.add_argument('--from', dest='t0', type=float, default=0)
ap.add_argument('--to', dest='t1', type=float)
ap.add_argument('--notes', help='JSON list of note on/off times (s) in the file: jumps up to 80 ms after them are attacks')
ap.add_argument('--latency', type=float, default=0.06)
A = ap.parse_args(); args, t0, t1 = A.files, A.t0, A.t1
total = 0
for f in args:
    x = load(f).astype(np.float64)
    sr = 48000
    a = int(t0 * sr); b = int(t1 * sr) if t1 else len(x)
    x = x[a:b]
    z = np.abs(x) < 1e-6
    gaps = []
    d = np.diff(np.concatenate([[0], z.astype(np.int8), [0]]))
    starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    w = int(0.03 * sr)
    for s0, e0 in zip(starts, ends):
        if not int(0.005 * sr) <= e0 - s0 <= int(0.08 * sr): continue   # an underrun is short; longer silences are rests
        # an underrun cuts a sustained sound and resumes it: similar level just before and just after
        k10 = int(0.01 * sr)
        before = x[max(0, s0 - k10):s0]; after = x[e0:e0 + k10]
        if len(before) < k10 or len(after) < k10: continue
        rb, ra = np.sqrt((before ** 2).mean()), np.sqrt((after ** 2).mean())
        if rb > 0.01 and ra > 0.01 and 0.4 < ra / rb < 2.5:
            gaps.append((s0 / sr + t0, (e0 - s0) / sr * 1000))
    dx = np.abs(np.diff(x))
    k = int(0.01 * sr)
    loc = np.sqrt(np.convolve(dx ** 2, np.ones(k) / k, 'same')) + 1e-9
    cl = np.nonzero((dx > 0.25) & (dx > 12 * loc))[0]
    pre = int(0.003 * sr)   # a jump out of near-silence is a note's attack, not a click
    cl = [i for i in cl if i > pre and np.sqrt((x[i - pre:i] ** 2).mean()) > 0.02]
    if A.notes:
        ev = np.array(json.load(open(A.notes))) + A.latency
        cl = [i for i in cl if not ((i / sr + t0 - ev >= -0.005) & (i / sr + t0 - ev < 0.08)).any()]   # a layer's attack can land a little after the note
    clicks = []
    for i in cl:
        if not clicks or i / sr + t0 - clicks[-1] > 0.05: clicks.append(i / sr + t0)
    # pops: second-derivative spikes anywhere (edit points, fades, gain steps, sample starts), against a robust local
    # level (the largest 5 ms block median within 20 ms); listed with their size
    d2 = np.abs(np.diff(x, 2))
    nb = len(d2) // 240
    blk = np.array([np.median(d2[i * 240:(i + 1) * 240]) for i in range(nb)])
    locm = np.repeat(np.maximum.reduce([np.roll(blk, k) for k in range(-4, 5)]), 240) + 1e-5
    dd = d2[:len(locm)]
    pk = np.nonzero((dd > 0.01) & (dd > 20 * locm))[0]
    pops = []
    for i in pk:
        if not pops or i / sr + t0 - pops[-1][0] > 0.02: pops.append((i / sr + t0, float(dd[i])))
    if A.notes:
        ev = np.array(json.load(open(A.notes))) + A.latency
        attacks = [p for p in pops if ((p[0] - ev >= -0.005) & (p[0] - ev < 0.08)).any()]
        pops = [p for p in pops if p not in attacks]
    else:
        attacks = []
    # broadband ticks: bursts above ~5 kHz (x minus its 9-tap moving average) over 0.03 and 8x their 20 ms RMS:
    # how an 8-bit sample that starts or stops off zero sounds; speech hardly triggers it
    hp = x - np.convolve(x, np.ones(9) / 9, 'same')
    lh = np.sqrt(np.convolve(hp ** 2, np.ones(960) / 960, 'same')) + 1e-5
    tk = np.nonzero((np.abs(hp) > 0.03) & (np.abs(hp) > 8 * lh))[0]
    ticks = []
    for i in tk:
        if not ticks or i / sr + t0 - ticks[-1][0] > 0.02: ticks.append((i / sr + t0, float(abs(hp[i]))))
    total += len(gaps) + len(clicks) + len(pops) + len(ticks)
    print(f'{f}: {len(gaps)} gaps, {len(clicks)} clicks, {len(pops)} pops ({len(attacks)} more at note attacks), {len(ticks)} ticks'
          + (f'; gaps at {[round(g[0], 3) for g in gaps[:8]]}' if gaps else '')
          + (f'; clicks at {[round(c, 3) for c in clicks[:8]]}' if clicks else '')
          + (f'; pops at {[(round(p[0], 3), round(p[1], 3)) for p in pops[:40]]}' if pops else '')
          + (f'; ticks at {[(round(p[0], 3), round(p[1], 3)) for p in ticks[:40]]}' if ticks else ''))
sys.exit(1 if total else 0)
