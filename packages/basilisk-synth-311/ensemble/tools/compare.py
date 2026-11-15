#!/usr/bin/env python3
"""The plugin's render against the per-track render311 stems: align (cross-correlation), then compare the mix and
report the residual.   compare.py PLUGIN.wav STEMDIR NLANES [--from S --to S] [--warmup S]"""
import sys, struct, numpy as np
def rd(p):
    d = open(p, 'rb').read(); i = 12; fmt = None
    while i < len(d):
        cid, ln = d[i:i + 4], struct.unpack('<I', d[i + 4:i + 8])[0]
        if cid == b'fmt ': fmt = struct.unpack('<HHIIHH', d[i + 8:i + 24])
        if cid == b'data':
            b = d[i + 8:i + 8 + ln]
            a = np.frombuffer(b, '<f4') if fmt[0] == 3 else np.frombuffer(b, '<i2') / 32768.0
            return a.reshape(-1, fmt[1]).astype(np.float64)
        i += 8 + ln + (ln & 1)
if __name__ == "__main__":
    wav, stems, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    opt = lambda k, d: float(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
    t0, t1, warm = opt('--from', 0.5), opt('--to', 29.0), opt('--warmup', 20.0)
    p = rd(wav)
    ref = None
    for k in range(n):
        s = rd('%s/lane%d.wav' % (stems, k))
        ref = s if ref is None else (ref[:min(len(ref), len(s))] + s[:min(len(ref), len(s))]) if len(s) != len(ref) else ref + s
    sr = 48000; a0, a1 = int(t0 * sr), int(t1 * sr)
    r = ref[a0:a1, 0]
    best, bo = -1, 0
    base = int(warm * sr)
    for off in range(base - 4000, base + 4000):   # the plugin's file starts with the warm-up (and maybe its latency)
        seg = p[off + a0: off + a1, 0]
        if len(seg) < len(r): continue
        c = float(np.dot(seg[:48000], r[:48000]))
        if c > best: best, bo = c, off
    q = p[bo + a0: bo + a1]; R = ref[a0:a1]
    d = q - R
    print('offset %d samples (%.4f s after the warm-up); %.1f s compared' % (bo, (bo - base) / sr, (a1 - a0) / sr))
    print('identical samples %.3f%%; max diff %.3g; residual %.1f dB under the mix (rms); mix rms %.1f dBFS' % (
        100 * np.mean(np.all(d == 0, axis=1)), np.abs(d).max(), 20 * np.log10(np.sqrt((d ** 2).mean()) / np.sqrt((R ** 2).mean()) + 1e-30), 20 * np.log10(np.sqrt((R ** 2).mean()))))
    
