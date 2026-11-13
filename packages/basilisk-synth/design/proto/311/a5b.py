import json, numpy as np
W = '/home/wm/pe2-311/work/'
fs = np.load(W + 'steps_f.npy'); src = np.load(W + 'STEPS.WAV.npy').astype(float) / 32768
out = {}
for kind in ('ref', 'slow_fast', 'fast_slow'):
    x = np.load(W + 't5_%s_STEPS.npy' % kind)[:len(src)]
    seg = int(0.1 * 22050); gap = int(0.02 * 22050); rows = []
    for k, f in enumerate(fs):
        a = k * (seg + gap) + seg // 8; b = a + 3 * seg // 4; n = b - a; t = np.arange(n) / 22050
        def amp(y, fq):
            M = np.stack([np.sin(2 * np.pi * fq * t), np.cos(2 * np.pi * fq * t)], 1); c, *_ = np.linalg.lstsq(M, y, rcond=None); return np.hypot(*c), M @ c
        ax, _ = amp(src[a:b], f); ay, fit = amp(x[a:b], f); fi = 11025 - f; ai, fit2 = amp(x[a:b], fi)
        resid = x[a:b] - fit - fit2
        rows.append(dict(f=float(f), gain_db=20 * np.log10(ay / ax), mirror_f=float(fi), mirror_db=20 * np.log10(ai / ax + 1e-9), resid_db=20 * np.log10(np.sqrt(np.mean(resid ** 2)) / (ax / np.sqrt(2)) + 1e-9)))
    out[kind] = rows
    print('==', kind)
    for r in rows[::2] + [rows[-1]]: print('  %7.0f Hz  gain %+7.2f dB | at %7.0f Hz (11025-f) %+7.1f dB | rest %+6.1f dB' % (r['f'], r['gain_db'], r['mirror_f'], r['mirror_db'], r['resid_db']))
    g = np.array([r['gain_db'] for r in rows])
    for th in (-1, -3, -6, -10, -20):
        i = np.nonzero(g < th)[0]
        if len(i):
            j = i[0]; f0, f1, g0, g1 = fs[j - 1], fs[j], g[j - 1], g[j]; fx = f0 + (th - g0) / (g1 - g0) * (f1 - f0)
            print('   %d dB at %.0f Hz' % (th, fx)); out.setdefault(kind + '_points', {})[str(th)] = float(fx)
json.dump(out, open('/home/wm/pe2-evidence/311/t5_steps_analysis.json', 'w'), indent=1)
# theory for fast_slow: decimate by 2 then linear interpolation x2: H(f) = (1 + cos(2 pi f / 22050)) / 2 for the direct path
for f in (1000, 2000, 3000, 4000, 5000, 6000, 8000):
    print('theory linear-interp passband gain at %d Hz: %.2f dB' % (f, 20 * np.log10((1 + np.cos(2 * np.pi * f / 22050)) / 2)))
