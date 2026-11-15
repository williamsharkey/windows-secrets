#!/usr/bin/env python3
"""Each lane the plugin dumped (ENSEMBLE_DUMP_DIR: laneK.f32) against render311's stem of the same track: aligned by
cross-correlation, compared over [from, to] seconds of the score.   cmplanes.py DUMPDIR STEMDIR N [--to 28]"""
import sys, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from compare import rd
dd, sd, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
to = float(sys.argv[sys.argv.index('--to') + 1]) if '--to' in sys.argv else 28.0
sr = 48000
for k in range(n):
    p = np.fromfile('%s/lane%d.f32' % (dd, k), '<f4').reshape(-1, 2).astype(np.float64)
    r = rd('%s/lane%d.wav' % (sd, k))[: int(to * sr)]
    if not np.any(r): print('lane %d: silent stem' % k); continue
    m = 1 << int(np.ceil(np.log2(len(p) + len(r))))
    c = np.fft.irfft(np.fft.rfft(p[:, 0], m) * np.conj(np.fft.rfft(r[:, 0], m)), m)
    off = int(np.argmax(c[: len(p)]))
    q = p[off: off + len(r)]
    if len(q) < len(r): r = r[: len(q)]
    d = q - r; rr = np.sqrt((r ** 2).mean())
    print('lane %d: offset %d (%.3f s); identical %.2f%%; max diff %.3g; residual %.1f dB; first diff at %s' % (
        k, off, off / sr, 100 * np.mean(np.all(d == 0, axis=1)), np.abs(d).max(), 20 * np.log10(np.sqrt((d ** 2).mean()) / rr + 1e-30),
        ('%.3f s' % (np.argmax(np.abs(d).max(axis=1) > 1e-6) / sr)) if np.abs(d).max() > 1e-6 else '-'))
