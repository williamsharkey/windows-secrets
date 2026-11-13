import json, numpy as np
from scipy.signal import hilbert, butter, sosfiltfilt, sosfilt
a = np.load('/home/wm/pe2-311/work/t2.npy')[:, 0].astype(float)
L = json.load(open('/home/wm/pe2-evidence/311/t2_log.json')); base = L['base']
ph = np.unwrap(np.angle(hilbert(a))); f = np.diff(ph) * 48000 / (2 * np.pi)
sos = butter(6, 3000, 'hp', fs=48000, output='sos'); hp = sosfilt(sos, a)
def db(x): return 20 * np.log10(max(x, 1e-12))
steady = hp[int(0.3*48000) + 0: int(0.3*48000) + 20000]
print('steady HP>3k peak %.1f dBFS rms %.1f' % (db(np.abs(steady).max()), db(np.sqrt(np.mean(steady**2)))))
print('signal peak', np.abs(a).max())
res = []
for val, dh, dg, s in L['sends'][:4] + L['sends'][15:]:
    i = dg - base
    # find where inst freq departs: median freq before/after
    fb = np.median(f[i - 2000:i - 200]); fa = np.median(f[i + 1500:i + 3000]) if val else 0
    # first sample (from i-100) where freq moves > 30% of the way
    seg = f[i - 100:i + 1500]
    sm = np.convolve(seg, np.ones(24) / 24, 'same')
    k = np.nonzero(np.abs(sm - fb) > 0.5 * abs(fa - fb))[0] if val != 65536 or True else []
    chg = (k[0] - 100) if len(k) else None
    w = hp[i - 300:i + 600]
    res.append(dict(rate=val / 65536, host_dac=dh, guest_dac=dg, f_before=round(fb, 1), f_after=round(fa, 1), change_vs_guest_samples=int(chg) if chg is not None else None,
                    hp_peak_dbfs=round(db(np.abs(w).max()), 1)))
    print(res[-1])
# exact: compare to an ideal model at the 1.5x change: phase continuity
val, dh, dg, s = L['sends'][0]; i = dg - base
x = a[i - 4800:i + 4800]
# fit sines separately before and after a candidate boundary b in [i-48, i+96]
def fit(y, fr, t):
    M = np.stack([np.sin(2*np.pi*fr*t), np.cos(2*np.pi*fr*t)], 1); c, *_ = np.linalg.lstsq(M, y, rcond=None); return M @ c, c
best = None
for b in range(-96, 144):
    t1 = np.arange(-4800, b) / 48000; t2 = np.arange(b, 4800) / 48000
    y1, c1 = fit(x[:4800 + b], 441, t1); y2, c2 = fit(x[4800 + b:], 661.5, t2)
    r = np.concatenate([x[:4800 + b] - y1, x[4800 + b:] - y2])
    e = np.sum(r ** 2)
    if best is None or e < best[0]: best = (e, b, r, c1, c2)
e, b, r, c1, c2 = best
# phase continuity check: value of each model at the boundary
tb = b / 48000
v1 = c1[0]*np.sin(2*np.pi*441*tb) + c1[1]*np.cos(2*np.pi*441*tb); v2 = c2[0]*np.sin(2*np.pi*661.5*tb) + c2[1]*np.cos(2*np.pi*661.5*tb)
print('1.5x step: boundary at guest+%d samples (dac %d, mod48=%d); model mismatch at boundary %.2e; residual max %.2e (%.1f dBFS) rms %.1f dBFS; amp before %.4f after %.4f' % (
    b, dg + b, (dg + b) % 48, v1 - v2, np.abs(r).max(), db(np.abs(r).max()), db(np.sqrt(np.mean(r**2))), np.hypot(*c1), np.hypot(*c2)))
json.dump(dict(steps=res, step15=dict(boundary_vs_guest=int(b), resid_max_dbfs=db(np.abs(r).max()))), open('/home/wm/pe2-evidence/311/t2_analysis.json', 'w'), indent=1)
# glide trace
for key in ('glide', 'glide2'):
    d, g = L[key]
    d0 = int(g.split('d0 ')[1].split()[0]); d1 = int(g.split('d1 ')[1]); i0 = d0 - base; i1 = d1 - base
    fr = np.convolve(f, np.ones(48)/48, 'same')
    tr = fr[i0 - 2400:i1 + 2400:480]
    print(key, 'duration %.1f ms' % ((d1 - d0) / 48), 'trace every 10 ms:', np.round(tr).astype(int).tolist())
    np.savetxt('/home/wm/pe2-evidence/311/t2_%s_freqtrace_1ms.txt' % key, np.round(fr[i0 - 2400:i1 + 2400:48], 2), fmt='%.2f', header='inst. freq (Hz) every 1 ms, from 50 ms before the glide start')
    w = hp[i0:i1]; print('   glide HP>3k peak %.1f dBFS' % db(np.abs(w).max()))
    # staircase: ratio of max freq jump per ms
    seg = fr[i0:i1:48]; jumps = np.diff(seg); print('   per-ms freq change max %.2f Hz, steps seen (>2 Hz jumps): %d' % (np.abs(jumps).max(), np.sum(np.abs(jumps) > 2)))
