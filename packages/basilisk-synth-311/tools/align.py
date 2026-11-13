import numpy as np, wave, sys
def src(path):
    w = wave.open(path); n = w.getnframes(); b = np.frombuffer(w.readframes(n), np.uint8)
    return (b.astype(float) - 128) / 128, w.getframerate()
def expected(path, hz, n=48000):
    x, r = src(path)
    step = hz / 48000.0
    t = np.arange(n) * step
    t = t[t < len(x) - 1]
    return np.interp(t, np.arange(len(x)), x)
def lag(rec, exp, maxlag=3000):
    best = None
    L = min(len(exp), 12000)
    e = exp[:L]
    for d in range(-maxlag, maxlag):
        if d < 0 or d + L > len(rec): continue
        c = np.dot(rec[d:d + L], e) / (np.linalg.norm(e) ** 2 + 1e-12)   # unnormalized: the silence before the onset counts
        if best is None or c > best[1]: best = (d, c)
    return best
