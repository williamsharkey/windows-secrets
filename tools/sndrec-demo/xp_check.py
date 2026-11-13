#!/usr/bin/env python3
"""Frame timing and audio continuity of an XP editor capture (xp_video.py, bsynth-host --editor --shots).

    xp_check.py WORKDIR CLIP [--start S]

Needs WORKDIR/CLIP/shots.csv, written by a bsynth-host built with the shot log (the sndrec-demo build: one line per
shot: index, audio seconds, wall seconds before and after the grab), the BMP frames, and WORKDIR/CLIP.wav.
Reports, from --start on:
- audio clock: every shot must be within one frame (1/30 s) of index/30 (the host takes it at the first block
  boundary past it);
- wall clock: each grab's lag behind its own audio time (wall time of the grab minus the shot's audio time; the
  host plays in real time). The picture is even when that lag varies by less than a frame: a frame grabbed more
  than one frame later than the median shows the screen too late (as if repeated/dropped). Counted, with the spread;
- picture: how often consecutive frames differ (the editor shows XP as QEMU's VNC updates arrive);
- audio: dropouts: exact-zero runs of 5 ms or more that cut a sound off (the 10 ms before the run still above
  -40 dBFS), as a gap in XP's stream does; a note that decays to silence is not counted.
Exit status 1 if any frame is off by more than one frame on either clock, or any audio gap is found.
"""
import argparse, glob, os, sys
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('clip'); ap.add_argument('--start', type=float, default=0.0)
a = ap.parse_args()
d = os.path.join(a.work, a.clip)
rows = [list(map(float, l.split(','))) for l in open(os.path.join(d, 'shots.csv')) if l.strip()]
rows = [r for r in rows if r[1] >= a.start - 1e-9]
fr = 1 / 30.0
audio_err = max(abs(r[1] - r[0] * fr) for r in rows)
gaps = np.diff([r[2] for r in rows])
lag = np.array([r[2] - r[1] for r in rows]); med = np.median(lag)
late = int((lag - med > fr).sum()); bunched = int((med - lag > fr).sum())
grab = max(r[3] - r[2] for r in rows)
# picture
fs = sorted(glob.glob(os.path.join(d, '*.bmp')))[int(round(a.start * 30)):]
prev = None; same = 0; runs = []; run = 0
for f in fs:
    g = np.asarray(Image.open(f).convert('RGB'))
    if prev is not None:
        if np.array_equal(g, prev): same += 1; run += 1
        else:
            if run: runs.append(run)
            run = 0
    prev = g
# audio
raw = open(os.path.join(a.work, a.clip + '.wav'), 'rb').read(); i = raw.find(b'data')
x = np.frombuffer(raw[i + 8:], '<f4').reshape(-1, 2)[int(a.start * 48000):]
m = np.abs(x).max(axis=1)
env = np.convolve(m, np.ones(4800) / 4800, mode='same')   # 100 ms envelope: is something sounding here?
zero = m == 0
gaps_a = []; k = 0; n = len(m)
while k < n:
    if zero[k]:
        j = k
        while j < n and zero[j]: j += 1
        before = x[max(0, k - 480):k]
        if j - k >= 240 and k > 0 and len(before) and 20 * np.log10(np.sqrt((before ** 2).mean()) + 1e-12) > -40:
            gaps_a.append((k / 48000 + a.start, (j - k) / 48));
        k = j
    else: k += 1
print('%s: %d shots; audio clock: worst %.1f ms from index/30 | grab lag behind audio: %.1f..%.1f ms (spread %.1f), '
      '%d over a frame late, %d over a frame early; grabs take up to %.1f ms' % (
      a.clip, len(rows), audio_err * 1000, lag.min() * 1000, lag.max() * 1000, (lag.max() - lag.min()) * 1000, late, bunched, grab * 1000))
print('   picture: %d of %d frames identical to the one before; longest still run %d frames' % (same, len(fs) - 1, max(runs or [0])))
print('   audio: %d dropouts (sound cut off by >= 5 ms of exact silence)%s' % (len(gaps_a), (': ' + ', '.join('%.2f s (%.0f ms)' % g for g in gaps_a[:6])) if gaps_a else ''))
sys.exit(1 if audio_err > fr or late or bunched or gaps_a else 0)
