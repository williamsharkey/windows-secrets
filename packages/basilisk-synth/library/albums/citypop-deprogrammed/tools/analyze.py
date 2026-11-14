#!/usr/bin/env python3
"""Objective checks of a rendered song (I cannot listen, so I measure).

    analyze.py OUT_DIR SLUG [--song SONG.song]

For every stem (<slug>.<track>.wav, from songrender --stems): peak, how many samples sit at full scale (clipping in
the emulated card), loudness, the spectral balance (sub / low / mid / presence / air), and whether each bar that
has notes in the MIDI also has sound (a silent layer). For the mix: integrated and short-term loudness over the
song, true-ish peak, stereo correlation and width, and resonances (narrow peaks in the long-term spectrum).
"""
import argparse, math, os, sys, wave
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', '..', '..', '..', 'tools', 'songrender'))
import songrender as sr   # noqa: E402
from smf import Smf   # noqa: E402


def read(path):
    with wave.open(path) as w:
        n, ch, sw, rate = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        b = w.readframes(n)
    if sw == 3:
        a = np.frombuffer(b, np.uint8).reshape(-1, 3)
        x = (a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8) | (a[:, 2].astype(np.int8).astype(np.int32) << 16)) / 2 ** 23
    elif sw == 4:
        x = np.frombuffer(b, '<i4') / 2 ** 31
    else:
        x = np.frombuffer(b, '<i2') / 32768
    return x.reshape(-1, ch).astype(np.float64), rate


BANDS = [(20, 60, 'sub'), (60, 250, 'low'), (250, 2000, 'mid'), (2000, 6000, 'pres'), (6000, 20000, 'air')]


def bands(m, rate):
    f, p = signal.welch(m, rate, nperseg=8192)
    tot = np.sum(p) + 1e-20
    return {n: round(10 * math.log10(np.sum(p[(f >= a) & (f < b)]) / tot + 1e-12), 1) for a, b, n in BANDS}, f, p


def resonances(f, p, lo=150, hi=8000):
    lp = 10 * np.log10(p + 1e-20)
    sm = signal.savgol_filter(lp, 151, 2)
    d = lp - sm
    ok = (f > lo) & (f < hi)
    idx = np.where(ok & (d > 9))[0]
    out = []
    for i in idx:
        if not out or f[i] - out[-1][0] > 40:
            out.append((round(float(f[i])), round(float(d[i]), 1)))
    return out[:8]


def match(m, rate, ex, spb):
    """how much of the stem's pitched energy falls on the pitch classes the MIDI asks for (per 0.5 s window), and
    the same with every possible transposition: a stem in tune scores best at 0"""
    notes, on = [], {}
    for tk, e in sorted(ex.tracks[0], key=lambda z: z[0]):
        st = e[0] & 0xF0
        if st == 0x90 and e[2] > 0:
            on.setdefault(e[1], []).append(tk)
        elif st == 0x80 or (st == 0x90 and e[2] == 0):
            if on.get(e[1]):
                t0 = on[e[1]].pop(0); notes.append((t0 / ex.division * spb, tk / ex.division * spb, e[1]))
    if not notes:
        return ''
    win = 0.5; n = int(len(m) / rate / win)
    want = np.zeros((n, 12))
    for a, b, p in notes:
        for k in range(int(a / win), min(n, int(b / win) + 1)):
            want[k, p % 12] = 1
    tot = np.zeros(12); hit = np.zeros(12); cnt = 0
    N = int(win * rate)
    fr = np.fft.rfftfreq(N, 1 / rate); ok = (fr > 50) & (fr < 4000)
    mid = np.round(69 + 12 * np.log2(fr[ok] / 440)).astype(int) % 12
    for k in range(n):
        if want[k].sum() == 0:
            continue
        seg = m[k * N:(k + 1) * N]
        if len(seg) < N or np.sqrt(np.mean(seg ** 2)) < 1e-4:
            continue
        sp = np.abs(np.fft.rfft(seg * np.hanning(N)))[ok] ** 2
        ch = np.bincount(mid, sp, 12)
        ch /= ch.sum() + 1e-20
        for sh in range(12):
            hit[sh] += np.sum(ch * np.roll(want[k], sh))
        cnt += 1
    if not cnt:
        return ''
    sc = hit / cnt
    best = int(np.argmax(sc))
    flag = '' if best == 0 else f' TRANSPOSED? best at {best if best <= 6 else best - 12:+d}'
    return f'  match {sc[0] * 100:.0f}%{flag}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('slug'); ap.add_argument('--song')
    a = ap.parse_args()
    song = sr.Song(a.song) if a.song else None
    smf = Smf.read(song.midi_path) if song else None
    if song:
        song.bpm = float(song.meta.get('bpm', smf.first_tempo_bpm()))
    spb = 60.0 / song.bpm if song else None
    print(f'== {a.slug}')
    for fn in sorted(os.listdir(a.out)):
        if not (fn.startswith(a.slug + '.') and fn.endswith('.wav')) or fn == a.slug + '.wav':
            continue
        name = fn[len(a.slug) + 1:-4]
        x, rate = read(os.path.join(a.out, fn))
        x = x * 2   # songrender writes stems at half level
        m = x.mean(axis=1)
        pk = np.max(np.abs(x))
        full = int(np.sum(np.abs(x) >= 0.9995 * pk))   # flat tops at the stem's own peak: clipping upstream
        bd, f, p = bands(m, rate)
        msg = ''
        if song:
            t = next((t for t in song.tracks if t.name == name), None)
            if t:
                ex = smf.extract(song.selector(t), t.tr)
                ons = sorted(set(int(tk / ex.division * spb // 2) for tk, e in ex.tracks[0] if e[0] & 0xF0 == 0x90 and e[2] > 0))
                silent = []
                for k in ons:   # 2-second windows that should have sound
                    seg = m[int(k * 2 * rate):int((k * 2 + 2.5) * rate)]
                    if len(seg) and 20 * math.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12) < -60:
                        silent.append(k * 2)
                if silent:
                    msg = f'  SILENT at {silent[:10]}s'
                msg += match(m, rate, ex, spb)
        res = resonances(f, p)
        print(f'  {name:10s} peak {20 * math.log10(pk + 1e-12):6.1f}  clip {full:5d}  rms {20 * math.log10(np.sqrt(np.mean(m ** 2)) + 1e-12):6.1f}  '
              + ' '.join(f'{k}{v:+.0f}' for k, v in bd.items()) + (f'  res {res}' if res else '') + msg)
    mixp = os.path.join(a.out, a.slug + '.wav')
    if os.path.exists(mixp):
        x, rate = read(mixp)
        L, R = x[:, 0], x[:, 1]
        corr = float(np.corrcoef(L, R)[0, 1])
        side = 20 * math.log10(np.sqrt(np.mean(((L - R) / 2) ** 2)) / (np.sqrt(np.mean(((L + R) / 2) ** 2)) + 1e-12) + 1e-12)
        bd, f, p = bands(x.mean(axis=1), rate)
        st = []
        w = int(3 * rate)
        for i in range(0, len(x) - w, w * 5):
            st.append(round(sr.lufs(x[i:i + w]), 1))
        print(f'  MIX  lufs {sr.lufs(x):.1f}  peak {20 * math.log10(np.max(np.abs(x))):.1f}  corr {corr:.2f}  side {side:.1f} dB  '
              + ' '.join(f'{k}{v:+.0f}' for k, v in bd.items()))
        print(f'  short-term (every 15 s): {st}')
        print(f'  resonances: {resonances(f, p)}')


if __name__ == '__main__':
    main()
