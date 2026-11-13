"""PRESET ENGINE 2: analysis of `sr_probe.exe fx` (XP Sound Recorder): the files come back base64 in its log.

    python3 sr_analyze.py fx.log [outdir]

Prints: Add Echo's taps (delay, gain) from the impulse runs; lengths before/after (from the log lines); and the
magnitude response and alias level of the speed round trips on white noise (<>, ><, <<>>, >><<) against the source.
"""
import base64
import io
import re
import sys
import wave
import numpy as np


def files(log):
    out, cur, buf = {}, None, []
    for line in open(log, encoding='latin-1'):
        line = line.strip()
        if line.startswith('FILE '):
            cur, buf = line.split()[1].split('\\')[-1], []
        elif line == 'END' and cur:
            out[cur] = base64.b64decode(''.join(buf))
            cur = None
        elif cur:
            buf.append(line)
    return out


def pcm(b):
    w = wave.open(io.BytesIO(b))
    return np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768, w.getframerate()


def taps(x, fs):
    k0 = int(np.argmax(np.abs(x)))
    a0 = x[k0]
    t = []
    for k in np.flatnonzero(np.abs(x) > abs(a0) * 0.01):
        if k != k0:
            t.append(((k - k0) / fs * 1000, x[k] / a0))
    return k0, t


def response(src, y, fs):
    """|Y/X| in octave-ish bands, from long-term spectra (Welch); and the alias share above fs/4"""
    from scipy import signal
    n = min(len(src), len(y))
    f, pxx = signal.welch(src[:n], fs, nperseg=2048)
    _, pyy = signal.welch(y[:n], fs, nperseg=2048)
    _, pxy = signal.csd(src[:n], y[:n], fs, nperseg=2048)
    h = np.abs(pxy) / pxx                      # the part of y that is coherent with x (the filter)
    coh = np.abs(pxy) ** 2 / (pxx * pyy)       # 1 - coh: noise and aliasing share
    return f, h, coh


if __name__ == '__main__':
    log = sys.argv[1]
    fl = files(log)
    for line in open(log, encoding='latin-1'):
        if line.startswith('ops '):
            print(line.strip())
    for name in ('e1.wav', 'e2.wav'):
        if name in fl:
            x, fs = pcm(fl[name])
            k0, t = taps(x, fs)
            print('%s (%d Hz, %d frames): impulse at %d; taps: %s' % (name, fs, len(x), k0, ', '.join('%+.1f ms x%.3f' % (d, g) for d, g in t[:8])))
    if 'noise.wav' in fl:
        src, fs = pcm(fl['noise.wav'])
        for name in ('du.wav', 'ud.wav', 'dduu.wav', 'uudd.wav'):
            if name not in fl:
                continue
            y, _ = pcm(fl[name])
            same = len(y) == len(src) and np.array_equal(y, src)
            f, h, coh = response(src, y, fs)
            pts = []
            for fr in (500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000):
                i = int(np.argmin(np.abs(f - fr)))
                pts.append('%d:%+.1f dB (coh %.2f)' % (fr, 20 * np.log10(h[i] + 1e-9), coh[i]))
            print('%s: %d frames (source %d)%s\n   %s' % (name, len(y), len(src), '  BIT-IDENTICAL to the source' if same else '', '  '.join(pts)))
