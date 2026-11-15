"""Offline sample preparation for the Rainy Loft Collection (the album pack): load, trim, filter, saturate, chorus,
room, retune, loop and write 3.11-ready WAVs (22050 Hz, 16-bit, mono, at most 30 s).

This only prepares source recordings before they go into SNDWAVE1993's Sound Recorders; every note of the album is
then played by the recorders themselves.
"""
import math, os, subprocess, wave
import numpy as np
from scipy import signal

SR = 48000
FFMPEG = os.path.expanduser('~/.local/bin/ffmpeg')


def load(path, start=0.0, dur=None, sr=SR):
    cmd = [FFMPEG, '-v', 'error', '-ss', str(start)]
    if dur:
        cmd += ['-t', str(dur)]
    cmd += ['-i', path, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-']
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32).astype(np.float64)
    return x


def raw(data):
    return np.frombuffer(data, dtype=np.float32).astype(np.float64)


def sos(kind, f, order=2, sr=SR):
    return signal.butter(order, f, btype=kind, fs=sr, output='sos')


def hp(x, f, order=2):
    return signal.sosfilt(sos('highpass', f, order), x)


def lp(x, f, order=2):
    return signal.sosfilt(sos('lowpass', f, order), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], btype='bandpass', fs=SR, output='sos'), x)


def peq(x, f, db, q=0.9):
    """a peaking EQ (RBJ)"""
    A = 10 ** (db / 40); w = 2 * math.pi * f / SR; al = math.sin(w) / (2 * q)
    b = [1 + al * A, -2 * math.cos(w), 1 - al * A]; a = [1 + al / A, -2 * math.cos(w), 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def shelf(x, f, db, high=True):
    A = 10 ** (db / 40); w = 2 * math.pi * f / SR; al = math.sin(w) / 2 * math.sqrt(2)
    c = math.cos(w); s = 2 * math.sqrt(A) * al
    if high:
        b = [A * ((A + 1) + (A - 1) * c + s), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - s)]
        a = [(A + 1) - (A - 1) * c + s, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - s]
    else:
        b = [A * ((A + 1) - (A - 1) * c + s), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - s)]
        a = [(A + 1) + (A - 1) * c + s, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - s]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def tape(x, drive=1.6, warm=0.0):
    """soft saturation (tanh), level-matched, with an optional low warmth bump"""
    pk = np.max(np.abs(x)) + 1e-12
    y = np.tanh(drive * x / pk) / math.tanh(drive) * pk
    if warm:
        y = peq(y, 180, warm, 0.7)
    return y


def delay_mod(x, base_ms, depth_ms, rate_hz, phase=0.0):
    n = np.arange(len(x))
    d = (base_ms + depth_ms * np.sin(2 * math.pi * rate_hz * n / SR + phase)) * SR / 1000
    idx = n - d
    i0 = np.floor(idx).astype(int); fr = idx - i0
    i0c = np.clip(i0, 0, len(x) - 1); i1c = np.clip(i0 + 1, 0, len(x) - 1)
    y = x[i0c] * (1 - fr) + x[i1c] * fr
    y[idx < 0] = 0
    return y


def chorus(x, mix=0.45, rates=(0.31, 0.47), depth=2.2, base=11.0):
    """a mono ensemble: two slowly moving delayed copies summed with the dry signal"""
    w = sum(delay_mod(x, base + 3 * k, depth, r, k * 1.7) for k, r in enumerate(rates)) / len(rates)
    return (1 - mix) * x + mix * w


def wow(x, cents=6.0, rate=0.6, flutter=0.0, frate=9.0):
    """tape speed drift: a slowly varying read rate"""
    n = np.arange(len(x)) / SR
    c = cents * np.sin(2 * math.pi * rate * n) + flutter * np.sin(2 * math.pi * frate * n)
    r = 2 ** (c / 1200)
    pos = np.cumsum(r) - r[0]
    pos = pos[pos < len(x) - 1]
    i0 = np.floor(pos).astype(int); fr = pos - i0
    return x[i0] * (1 - fr) + x[i0 + 1] * fr


def room_ir(seconds=1.2, tone=5000, seed=1988, pre_ms=12, density=1.0):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-6.9 * t / seconds) * density
    ir = lp(ir, tone, 1)
    ir = np.concatenate([np.zeros(int(pre_ms * SR / 1000)), ir])
    return ir / np.sqrt(np.sum(ir ** 2))


def room(x, mix=0.25, seconds=1.2, tone=5000, seed=1988):
    w = signal.fftconvolve(x, room_ir(seconds, tone, seed))[:len(x) + int(seconds * SR)]
    y = np.concatenate([x, np.zeros(len(w) - len(x))])
    return (1 - mix) * y + mix * w * (np.max(np.abs(x)) / (np.max(np.abs(w)) + 1e-12))


def gate_start(x, thresh_db=-45):
    """cut silence before the first sound (keeps 2 ms)"""
    th = 10 ** (thresh_db / 20) * (np.max(np.abs(x)) + 1e-12)
    k = np.argmax(np.abs(x) > th)
    return x[max(0, k - int(0.002 * SR)):]


def trim_end(x, thresh_db=-60, hold_ms=40):
    env = np.abs(x)
    th = 10 ** (thresh_db / 20) * (np.max(env) + 1e-12)
    above = np.where(env > th)[0]
    if len(above) == 0:
        return x
    return x[:min(len(x), above[-1] + int(hold_ms * SR / 1000))]


def fades(x, fin_ms=2.0, fout_ms=30.0):
    y = x.copy()
    a = int(fin_ms * SR / 1000); b = int(fout_ms * SR / 1000)
    if a:
        y[:a] *= np.linspace(0, 1, a) ** 2
    if b:
        y[-b:] *= np.linspace(1, 0, b) ** 2
    return y


def loopify(x, xfade_s=1.5):
    """a seamless loop: the end crossfaded (equal power) into the start"""
    n = int(xfade_s * SR)
    if len(x) <= 2 * n:
        return x
    head, body, tail = x[:n], x[n:len(x) - n], x[len(x) - n:]
    t = np.linspace(0, math.pi / 2, n)
    mixed = tail * np.cos(t) + head * np.sin(t)
    return np.concatenate([body, mixed])


def rms_db(x):
    return 20 * math.log10(math.sqrt(np.mean(x ** 2)) + 1e-12)


def norm(x, peak_db=-1.0):
    return x * (10 ** (peak_db / 20) / (np.max(np.abs(x)) + 1e-12))


def norm_rms(x, rms=-20.0, peak_db=-1.0):
    y = x * 10 ** ((rms - rms_db(x)) / 20)
    pk = np.max(np.abs(y))
    if pk > 10 ** (peak_db / 20):
        y = y * 10 ** (peak_db / 20) / pk
    return y


def f0(x, lo=40.0, hi=1500.0, start=0.08, length=0.5):
    """the fundamental of a tonal note (normalised autocorrelation over a steady part)"""
    a = int(start * SR); seg = x[a:a + int(length * SR)]
    seg = seg - np.mean(seg)
    if len(seg) < 2048:
        seg = x[:min(len(x), int(length * SR))]
    seg = seg * np.hanning(len(seg))
    ac = signal.fftconvolve(seg, seg[::-1])[len(seg) - 1:]
    ac /= ac[0] + 1e-12
    kmin, kmax = int(SR / hi), min(len(ac) - 2, int(SR / lo))
    k = kmin + int(np.argmax(ac[kmin:kmax]))
    # prefer the earliest strong peak (no octave error downwards)
    thr = 0.85 * ac[k]
    for j in range(kmin, k):
        if ac[j] > thr and ac[j] >= ac[j - 1] and ac[j] >= ac[j + 1]:
            k = j; break
    if 1 <= k < len(ac) - 1:
        y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
        k = k + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)
    return SR / k


def midi_of(f):
    return 69 + 12 * math.log2(f / 440.0)


def retune(x, f_now, midi_target):
    """resample so the note sounds at exactly midi_target"""
    ratio = (440 * 2 ** ((midi_target - 69) / 12)) / f_now
    n = int(round(len(x) / ratio))
    return signal.resample_poly(x, 1000, int(round(1000 * ratio))) if abs(ratio - 1) > 1e-4 else x


def write311(path, x, seconds=30.0):
    """22050 Hz, 16-bit, mono; at most `seconds`"""
    y = signal.resample_poly(x, 147, 320)   # 48000 -> 22050
    y = y[:int(seconds * 22050)]
    y = np.clip(y, -1, 1)
    d = (y * 32767).astype('<i2').tobytes()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(d)
    return len(y) / 22050


NOTE = ['c', 'cs', 'd', 'ds', 'e', 'f', 'fs', 'g', 'gs', 'a', 'as', 'b']


def note_name(m):
    return f'{NOTE[m % 12]}{m // 12 - 1}'
