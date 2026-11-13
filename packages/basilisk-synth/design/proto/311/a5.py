import json, numpy as np
W = '/home/wm/pe2-311/work/'
R = json.load(open('/home/wm/pe2-evidence/311/t5_results.json'))
out = {}
def ld(t): return np.load(W + 't5_%s.npy' % t)
# echo: raw source frames at 48k output = 1 frame per sample
for tag, sr, i0 in (('echo_CLICK', 22050, 220), ('echo_CLICK8', 22050, 220), ('echo_CLICK11', 11025, 110), ('echo2_CLICK', 22050, 220)):
    x = ld(tag); q = 1/128 if '8' in tag or '11' in tag else 1/32768
    pk = np.nonzero(np.abs(x) > 3 * q)[0]
    # group nonzero samples
    groups = []
    for p in pk:
        if groups and p - groups[-1][-1] <= 2: groups[-1].append(p)
        else: groups.append([p])
    rows = [(g[0], g[0] - i0, (g[0] - i0) / sr * 1000, float(x[g].sum()), len(g)) for g in groups]
    base = rows[0][3]
    print(tag, 'echo taps (frame, delay frames, delay ms, amplitude rel. to click):')
    for r in rows[:12]: print('   frame %6d  +%5d  %7.2f ms  %.4f (%+.1f dB)  width %d' % (r[0], r[1], r[2], r[3] / base, 20 * np.log10(abs(r[3] / base) + 1e-12), r[4]))
    out[tag] = [dict(frame=int(r[0]), delay_frames=int(r[1]), delay_ms=r[2], rel=r[3] / base) for r in rows[:20]]
# paste mix / mix file at 50%: where the second click lands
for tag in ('pastemix_at50', 'mixfile_at50'):
    x = ld(tag); pk = np.nonzero(np.abs(x) > 0.05)[0]; print(tag, 'clicks at frames', pk.tolist(), 'values', np.round(x[pk], 3).tolist())
    out[tag] = dict(frames=pk.tolist(), values=x[pk].tolist())
# speed round trips: compare with reference
from scipy.signal import welch, csd
fs = np.load(W + 'steps_f.npy')
srcS = np.load(W + 'STEPS.WAV.npy').astype(float) / 32768; srcN = np.load(W + 'NOISE4.WAV.npy').astype(float) / 32768
def align(x, src):
    n = len(src); x = x[:n + 2000]
    c = np.correlate(x[:20000], src[:15000], 'valid') if len(x) > 20000 else None
    return x[:n]
for kind in ('slow_fast', 'fast_slow', 'ref'):
    x = ld('%s_STEPS' % kind)[:len(srcS)]
    print('==', kind, 'STEPS: max |y - x| = %.4g, exact-equal frames %.3f' % (np.abs(x - srcS).max(), np.mean(np.abs(x - srcS) < 2e-5)))
    seg = int(0.1 * 22050); gap = int(0.02 * 22050); rows = []
    for k, f in enumerate(fs):
        a = k * (seg + gap) + seg // 4; b = a + seg // 2
        X = np.fft.rfft(srcS[a:b] * np.hanning(b - a), 8192); Y = np.fft.rfft(x[a:b] * np.hanning(b - a), 8192)
        fr = np.fft.rfftfreq(8192, 1 / 22050); kf = np.argmin(np.abs(fr - f))
        sl = slice(max(kf - 3, 0), kf + 4)
        g = np.sqrt(np.sum(np.abs(Y[sl]) ** 2) / np.sum(np.abs(X[sl]) ** 2))
        Ym = np.abs(Y).copy(); Ym[max(kf - 6, 0):kf + 7] = 0
        alias_f = fr[np.argmax(Ym)]; alias = Ym.max() / np.abs(X[kf])
        rows.append((f, 20 * np.log10(g + 1e-12), alias_f, 20 * np.log10(alias + 1e-12)))
    out['%s_STEPS' % kind] = rows
    if kind != 'ref':
        for f, g, af, al in rows[::3] + [rows[-1]]: print('   %7.0f Hz: gain %+6.2f dB, largest other component %7.0f Hz at %+6.1f dB' % (f, g, af, al))
        g = np.array([r[1] for r in rows]); F = np.array([r[0] for r in rows])
        def cross(th):
            i = np.nonzero(g < th)[0]; return float(F[i[0]]) if len(i) else None
        print('   -3 dB at ~%s Hz, -10 dB at ~%s Hz (first tone below)' % (cross(-3), cross(-10)))
for kind in ('slow_fast', 'fast_slow', 'ref', 'fast', 'slow'):
    x = ld('%s_NOISE4' % kind)
    if kind in ('fast',): s = srcN; n = len(srcN) // 2
    elif kind == 'slow': s = srcN; n = len(srcN) * 2
    else: s = srcN; n = len(srcN)
    x = x[:n]
    if kind in ('fast', 'slow'):
        print('==', kind, 'NOISE4 length frames', n, 'first 12 out:', np.round(x[:12] * 32768).astype(int).tolist(), 'src:', np.round(s[:12] * 32768).astype(int).tolist()); continue
    f, Pxy = csd(s, x, 22050, nperseg=1024); _, Pxx = welch(s, 22050, nperseg=1024); _, Pyy = welch(x, 22050, nperseg=1024)
    H = np.abs(Pxy) / Pxx; coh = np.abs(Pxy) ** 2 / (Pxx * Pyy)
    noncoh = Pyy * (1 - coh) / Pxx   # output power not explained linearly (alias, distortion), relative to input
    HdB = 20 * np.log10(H + 1e-12)
    def cross(th):
        i = np.nonzero(HdB[1:] < th)[0]; return float(f[1:][i[0]]) if len(i) else None
    print('== %s NOISE4: |H| -3 dB at %s Hz, -10 dB at %s Hz; |H| at 1k %.2f dB, 5k %.2f dB, 8k %.2f dB, 10k %.2f dB; non-coherent (alias/distortion) power rel. input at 2k %.1f dB, 6k %.1f dB, 9k %.1f dB' % (
        kind, cross(-3), cross(-10), *[HdB[np.argmin(np.abs(f - q))] for q in (1000, 5000, 8000, 10000)], *[10 * np.log10(noncoh[np.argmin(np.abs(f - q))] + 1e-12) for q in (2000, 6000, 9000)]))
    print('   max |y - x| = %.4g' % np.abs(x - s).max())
    out['%s_NOISE4' % kind] = dict(f=f.tolist(), H_db=HdB.tolist(), noncoh_db=(10 * np.log10(noncoh + 1e-12)).tolist())
json.dump(out, open('/home/wm/pe2-evidence/311/t5_analysis.json', 'w'))
