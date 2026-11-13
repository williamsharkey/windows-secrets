"""PRESET ENGINE 2: analysis of the xp_swaptest recordings (QEMU wav audiodev, 44.1 kHz stereo s16).

    python3 xp_analyze.py align  REC.wav            B's start error vs A (L/R cross-correlation per trial)
    python3 xp_analyze.py click  REC.wav            HF (>3 kHz) peak around each swap of a sine; level dips
    python3 xp_analyze.py freq   REC.wav [png]      the pitch trace (cents re 440 Hz) and swap glitches
    python3 xp_analyze.py onsets REC.wav            grain onset times and their jitter
    python3 xp_analyze.py window REC.wav LOG        T2: where each [from, to) window of the noise source starts/ends
    python3 xp_analyze.py gaps   REC.wav            T4: dropouts of the 440 Hz reference

The recordings are not in git (the sources are synthetic, but they are large); see the spec's evidence notes.
"""
import sys
import wave
import numpy as np
from scipy import signal

FS = 44100


def load(p):
    w = wave.open(p)
    x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').reshape(-1, 2).astype(np.float64) / 32768
    return x


def segments(active, min_len, gap):
    """runs of True in active, merging gaps shorter than gap samples"""
    idx = np.flatnonzero(active)
    if not len(idx):
        return []
    out, s, p = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - p > gap:
            if p - s >= min_len:
                out.append((s, p))
            s = i
        p = i
    if p - s >= min_len:
        out.append((s, p))
    return out


def env(x, ms=5):
    n = int(FS * ms / 1000)
    return np.sqrt(np.convolve(x * x, np.ones(n) / n, 'same'))


def markers(x):
    """the 2 kHz markers: start and end of the test"""
    m = x.mean(1)
    b, a = signal.butter(4, [1800, 2200], 'band', fs=FS)
    e = env(signal.filtfilt(b, a, m), 5)
    return [s for s, _ in segments(e > 0.3, int(0.015 * FS), int(0.01 * FS))]


def align(x):
    L, R = x[:, 0], x[:, 1]
    eL, eR = env(L), env(R)
    lags = []
    for s, e in segments(eR > 0.02, int(0.1 * FS), int(0.02 * FS)):
        a, b = s + int(0.03 * FS), min(e, s + int(0.2 * FS))
        if eL[a:b].mean() < 0.02:
            continue
        W = 9000
        r, l = R[a:b], L[a - W:b + W]
        c = signal.correlate(l, r, 'valid')          # c[k]: r against l[k:k+len(r)], k=W -> lag 0
        k = int(np.argmax(c))
        # sub-sample: parabola
        if 0 < k < len(c) - 1:
            d = 0.5 * (c[k - 1] - c[k + 1]) / (c[k - 1] - 2 * c[k] + c[k + 1])
        else:
            d = 0
        lag = (W - (k + d)) / FS * 1000      # >0: B (right) plays material A played lag ms earlier = B is late
        # B's onset relative to the time A was asked for its position is not known here; the lag is the error
        lags.append(lag)
        print('trial %2d  B behind A by %7.2f ms  (corr peak %.2f)' % (len(lags) - 1, lag, c[k] / np.sqrt((r * r).sum() * (l[k:k + len(r)] ** 2).sum())))
    lags = np.array(lags)
    print('n %d  mean %.2f ms  sd %.2f  min %.2f  max %.2f' % (len(lags), lags.mean(), lags.std(), lags.min(), lags.max()))


def residual(x):
    """xfade split runs: A (left) ramps down while B (right) ramps up; the L/R lag in the overlap is the swap error"""
    L, R = x[:, 0], x[:, 1]
    eR = env(R)
    lags = []
    for s, e in segments(eR > 0.01, int(0.1 * FS), int(0.02 * FS)):
        a, b = s, s + int(0.08 * FS)
        W = 9000
        r, l = R[a:b], L[a - W:b + W]
        c = signal.correlate(l, r, 'valid')
        k = int(np.argmax(c))
        d = 0.5 * (c[k - 1] - c[k + 1]) / (c[k - 1] - 2 * c[k] + c[k + 1]) if 0 < k < len(c) - 1 else 0
        lags.append((W - (k + d)) / FS * 1000)
    lags = np.array(lags)
    print('residual B-after-A error: n %d  mean %.2f ms  sd %.2f  min %.2f  max %.2f  |err| median %.2f' % (
        len(lags), lags.mean(), lags.std(), lags.min(), lags.max(), np.median(np.abs(lags))))


def choke(x):
    """TK1: each burst of a 440 Hz sine ends with a choke; the HF (>3 kHz) peak in its last 30 ms, in dB re the sine,
    and the fall time from 90 % to 10 % of the level"""
    m = x.mean(1)
    b, a = signal.butter(6, 3000, 'high', fs=FS)
    hf = signal.filtfilt(b, a, m)
    e = env(m, 1)
    res = []
    for s, t in segments(e > 0.02, int(0.2 * FS), int(0.005 * FS)):
        lvl = np.median(e[s:t])
        tail = slice(max(s, t - int(0.03 * FS)), min(len(m), t + int(0.01 * FS)))
        peak = np.abs(hf[tail]).max()
        k90 = t - np.argmax(e[s:t][::-1] > 0.9 * lvl)
        fall = (t - k90) / FS * 1000
        res.append((20 * np.log10(peak / (lvl * np.sqrt(2)) + 1e-12), fall))
    r = np.array(res)
    print('n %d  HF peak at the end: median %.1f dB re the sine (worst %.1f)   fall 90%%->off median %.1f ms' % (len(r), np.median(r[:, 0]), r[:, 0].max(), np.median(r[:, 1])))


def pitch_track(m, hop_ms=2, win_ms=20):
    """instantaneous frequency of a near-sine: analytic-signal phase derivative, smoothed"""
    b, a = signal.butter(2, [150, 2000], 'band', fs=FS)
    y = signal.filtfilt(b, a, m)
    z = signal.hilbert(y)
    ph = np.unwrap(np.angle(z))
    f = np.diff(ph) * FS / (2 * np.pi)
    n = int(FS * win_ms / 1000)
    fs = np.convolve(f, np.ones(n) / n, 'same')
    amp = np.abs(z)
    return fs, amp


def click(x, log=None):
    """per swap region: the HF (>3 kHz) residual peak in dB re the sine, and the level dip during the crossfade"""
    m = x.mean(1)
    b, a = signal.butter(6, 3000, 'high', fs=FS)
    hf = signal.filtfilt(b, a, m)
    e = env(m, 2)
    act = segments(e > 0.05, int(0.3 * FS), int(0.02 * FS))
    res = []
    for s, t in act:
        seg = slice(s + int(0.05 * FS), t - int(0.05 * FS))
        mm, hh, ee = m[seg], hf[seg], e[seg]
        f, amp = pitch_track(mm)
        # the swap: where the frequency changes most, or (ratio 1) where the HF is largest
        lvl = np.median(ee)
        k = int(np.argmax(np.abs(hh)))
        peak = np.abs(hh).max()
        dip = ee[max(0, k - int(0.03 * FS)):k + int(0.03 * FS)].min() / lvl
        hfdb = 20 * np.log10(peak / (lvl * np.sqrt(2)) + 1e-12)
        floor = 20 * np.log10(np.percentile(np.abs(hh), 50) / (lvl * np.sqrt(2)) + 1e-12)
        res.append((hfdb, dip, floor))
        print('swap %2d  HF peak %6.1f dB re sine   HF median %6.1f dB   level dip to %.2f' % (len(res) - 1, hfdb, floor, dip))
    r = np.array(res)
    if len(r):
        print('n %d  HF peak median %.1f dB (worst %.1f)   dip median %.2f (worst %.2f)' % (len(r), np.median(r[:, 0]), r[:, 0].max(), np.median(r[:, 1]), r[:, 1].min()))


def freq(x, png=None):
    m = x.mean(1)
    f, amp = pitch_track(m)
    ok = amp[:-1] > 0.05
    c = np.where(ok, 1200 * np.log2(np.maximum(f, 1) / 440.0), np.nan)
    hop = int(FS * 0.002)
    t = np.arange(0, len(c), hop) / FS
    cs = c[::hop]
    np.savetxt(sys.stdout, np.c_[t, cs][~np.isnan(cs)][:: 25], fmt='%.3f')
    if png:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
        ax[0].plot(t, cs, lw=0.7)
        ax[0].set_ylabel('cents re 440 Hz')
        b, a = signal.butter(6, 3000, 'high', fs=FS)
        hf = signal.filtfilt(b, a, m)
        ax[1].plot(np.arange(len(hf)) / FS, 20 * np.log10(np.abs(hf) + 1e-6), lw=0.3)
        ax[1].set_ylabel('HF >3 kHz, dBFS')
        ax[1].set_ylim(-100, 0)
        ax[1].set_xlabel('s')
        fig.tight_layout()
        fig.savefig(png, dpi=90)


def onsets(x):
    m = x.mean(1)
    e = env(m, 1)
    segs = segments(e > 0.01, int(0.004 * FS), int(0.003 * FS))
    on = np.array([s for s, _ in segs]) / FS * 1000
    d = np.diff(on)
    print('onsets %d' % len(on))
    if len(d) > 2:
        med = np.median(d)
        # the schedule is regular: residuals of a straight-line fit
        k = np.arange(len(on))
        p = np.polyfit(k, on, 1)
        r = on - np.polyval(p, k)
        print('interval median %.2f ms  fit %.3f ms/grain   residual sd %.2f ms  p5..p95 %.2f..%.2f  max |r| %.2f' %
              (med, p[0], r.std(), np.percentile(r, 5), np.percentile(r, 95), np.abs(r).max()))


def window(x, logp):
    """T2: each window of the noise source [from, to) at 22050 Hz -> where it sits in the 44.1 kHz recording"""
    import re
    seed = 12345
    n = 22050 * 12
    src = np.empty(n)
    for i in range(n):
        seed = (seed * 1103515245 + 12345) & 0xFFFFFFFF
        src[i] = (((seed >> 16) & 0x7FFF) - 16384) / 32768
    up = signal.resample_poly(src, 2, 1)
    m = x.mean(1)
    e = env(m, 1)
    segs = segments(e > 0.02, int(0.05 * FS), int(0.005 * FS))
    wins = [tuple(map(int, g)) for g in re.findall(r'window \d+ from (\d+) to (\d+)', open(logp).read())]
    for (s, t), (fr, to) in zip(segs, wins):
        seg = m[s:s + 4410]
        c = signal.correlate(up[2 * fr - 2000:2 * fr + 6410], seg, 'valid')
        k = int(np.argmax(np.abs(c)))
        start_err = (k - 2000) / 2      # in 22.05 kHz source frames
        dur = (t - s) / 2
        print('window from %6d to %6d: starts at source frame %+.1f of from; length %.1f frames (asked %d, error %+.1f)' %
              (fr, to, start_err, dur, to - fr, dur - (to - fr)))


def gaps(x):
    """stream starvation: kmixer fills a starved stream with exactly 10 ms of digital silence"""
    for ch in (0, 1):
        z = np.abs(x[:, ch]) < 1e-4
        d = np.diff(np.r_[0, z.astype(int), 0])
        st, en = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        ln = (en - st) / FS * 1000
        sel = (ln > 0.5) & (ln < 60)
        print('channel %d: %d silent holes of 0.5-60 ms inside the sound (lengths %s ...)' % (ch, sel.sum(), np.round(ln[sel][:8], 1)))


if __name__ == '__main__':
    mode, path = sys.argv[1], sys.argv[2]
    x = load(path)
    mk = markers(x)
    if len(mk) >= 2:
        x = x[mk[0] + int(0.05 * FS):mk[-1]]
    {'align': lambda: align(x), 'residual': lambda: residual(x), 'choke': lambda: choke(x), 'click': lambda: click(x), 'freq': lambda: freq(x, sys.argv[3] if len(sys.argv) > 3 else None),
     'onsets': lambda: onsets(x), 'window': lambda: window(x, sys.argv[3]), 'gaps': lambda: gaps(x)}[mode]()
