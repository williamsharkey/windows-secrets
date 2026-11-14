#!/usr/bin/env python3
"""The album's master chain (on songrender's mixed WAV): a gentle glue compressor, a touch of tape, a small tilt
toward air, a little more side, then every track to the same loudness under a true-peak ceiling.

    master.py IN.wav OUT.wav [--lufs -16] [--ceiling -1.0] [--side 1.5] [--air 1.0]
"""
import argparse, math, os, sys, wave
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', '..', '..', '..', 'tools', 'songrender'))
sys.path.insert(0, HERE)
import songrender as sr   # noqa: E402
from analyze import read   # noqa: E402

SR = 48000


def shelf(x, f, db, high=True):
    A = 10 ** (db / 40); w = 2 * math.pi * f / SR; al = math.sin(w) / 2 * math.sqrt(2); c = math.cos(w); s = 2 * math.sqrt(A) * al
    if high:
        b = [A * ((A + 1) + (A - 1) * c + s), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - s)]
        a = [(A + 1) - (A - 1) * c + s, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - s]
    else:
        b = [A * ((A + 1) - (A - 1) * c + s), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - s)]
        a = [(A + 1) + (A - 1) * c + s, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - s]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def glue(x, thresh_db=-22.0, ratio=1.6, att_ms=30.0, rel_ms=350.0):
    """a slow, gentle bus compressor on the summed level (stereo-linked)"""
    lvl = np.sqrt(np.mean(x ** 2, axis=1) + 1e-12)
    a_a, a_r = math.exp(-1 / (att_ms * SR / 1000)), math.exp(-1 / (rel_ms * SR / 1000))
    db = 20 * np.log10(lvl)
    over = np.maximum(0, db - thresh_db)
    target = -over * (1 - 1 / ratio)
    # smooth the gain (attack when reducing more, release when recovering)
    g = np.zeros_like(target)
    cur = 0.0
    for i in range(0, len(target), 64):   # a control rate of 750 Hz is plenty here
        t = target[i:i + 64].min()
        cur = (a_a ** 64) * cur + (1 - a_a ** 64) * t if t < cur else (a_r ** 64) * cur + (1 - a_r ** 64) * t
        g[i:i + 64] = cur
    return x * (10 ** (g / 20))[:, None]


def tape(x, amount=0.15):
    pk = np.max(np.abs(x)) + 1e-12
    y = np.tanh(2.0 * x / pk) / math.tanh(2.0) * pk
    return (1 - amount) * x + amount * y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out')
    ap.add_argument('--lufs', type=float, default=-16.0); ap.add_argument('--ceiling', type=float, default=-1.0)
    ap.add_argument('--side', type=float, default=2.5); ap.add_argument('--air', type=float, default=1.0)
    a = ap.parse_args()
    x, rate = read(a.inp)
    assert rate == SR
    x = glue(x)
    x = tape(x)
    x = shelf(x, 9000, a.air, True)
    x = shelf(x, 90, 0.5, False)
    m, s = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2 * 10 ** (a.side / 20)
    x = np.stack([m + s, m - s], axis=1)
    pre = sr.lufs(x)
    y, red = sr.limiter(x * 10 ** ((a.lufs - pre) / 20), a.ceiling)
    post = sr.lufs(y)
    if post < a.lufs - 0.2:
        y, red = sr.limiter(x * 10 ** ((a.lufs - pre + a.lufs - post) / 20), a.ceiling)
        post = sr.lufs(y)
    sr.write_wav24(a.out, y)
    print(f'{os.path.basename(a.out)}: {post:.2f} LUFS, peak {20 * math.log10(np.max(np.abs(y))):.2f} dBFS')


if __name__ == '__main__':
    main()
