#!/usr/bin/env python3
"""Dropout check for a plugin capture or a finished video's soundtrack.

    dropouts.py FILE [FILE ...] [--from S --to S]

Counts, per file:
- gaps: runs of exact digital silence (|x| < 1e-6) of 5 to 80 ms where the sound just before and just after has a
  similar level (a buffer underrun cutting a sustained sound; rests between hits and notes are not counted);
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
    total += len(gaps) + len(clicks)
    print(f'{f}: {len(gaps)} gaps, {len(clicks)} clicks' + (f'; gaps at {[round(g[0], 3) for g in gaps[:8]]}' if gaps else '')
          + (f'; clicks at {[round(c, 3) for c in clicks[:8]]}' if clicks else ''))
sys.exit(1 if total else 0)
