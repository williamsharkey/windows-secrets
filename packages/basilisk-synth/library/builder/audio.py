"""Audio measurement for the builder: WAV reading, pitch (harmonic-sum spectrum), envelopes, spectral descriptors,
loudness (ffmpeg's EBU R128 when asked; a fast gated-RMS estimate otherwise)."""
import io, re, struct, subprocess, wave
import numpy as np

SR = 48000


def read_wav(path_or_bytes):
    """-> (float64 array [n, ch], rate). PCM 8/16/24 bit or 32-bit float."""
    d = open(path_or_bytes, 'rb').read() if isinstance(path_or_bytes, str) else path_or_bytes
    fmt = d.find(b'fmt ')
    tag, ch, rate = struct.unpack_from('<HHI', d, fmt + 8)
    bits = struct.unpack_from('<H', d, fmt + 22)[0]
    i = d.find(b'data')
    n = struct.unpack_from('<I', d, i + 4)[0]
    raw = d[i + 8:i + 8 + n]
    if tag == 3 or (tag == 0xFFFE and bits == 32 and False):
        a = np.frombuffer(raw[:len(raw) // 4 * 4], dtype='<f4').astype(np.float64)
    elif bits == 8:
        a = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128) / 128
    elif bits == 16:
        a = np.frombuffer(raw[:len(raw) // 2 * 2], dtype='<i2').astype(np.float64) / 32768
    elif bits == 32 and tag == 0xFFFE:
        a = np.frombuffer(raw[:len(raw) // 4 * 4], dtype='<f4').astype(np.float64)
    else:
        raise ValueError('unsupported wav %d/%d' % (tag, bits))
    a = a[:len(a) // ch * ch].reshape(-1, ch)
    return a, rate


def db(x):
    return 20 * np.log10(np.maximum(x, 1e-12))


def frames_rms(m, rate, hop=0.01, win=0.02):
    h, w = max(1, int(hop * rate)), max(2, int(win * rate))
    n = max(1, (len(m) - w) // h + 1)
    if len(m) < w: return np.array([np.sqrt(np.mean(m ** 2)) if len(m) else 0.0])
    idx = np.arange(n)[:, None] * h + np.arange(w)[None, :]
    return np.sqrt(np.mean(m[idx] ** 2, axis=1))


# ------------------------------------------------------------------ pitch
_GRID = 440 * 2 ** ((np.arange(24 * 100, 108 * 100, 5) / 100 - 69) / 12)   # MIDI 24..108 in 5-cent steps


def pitch(seg, rate, fmin=40.0, fmax=2500.0):
    """harmonic-sum f0 of a segment -> (midi float, confidence 0..1, spectral peak midi)"""
    if len(seg) < 256: return None, 0.0, None
    seg = seg[:int(rate * 0.8)] if len(seg) > rate * 0.8 else seg
    nfft = 1 << int(np.ceil(np.log2(max(len(seg) * 4, 16384))))
    X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), nfft))
    if X.max() <= 0: return None, 0.0, None
    X = X / X.max()
    fr = rate / nfft
    grid = _GRID[(_GRID >= fmin) & (_GRID <= fmax)]
    S = np.zeros(len(grid))
    for h in range(1, 9):
        f = grid * h
        ok = f < rate / 2 - 50
        b = np.round(f[ok] / fr).astype(int)
        # max over +-1 bin (the 5-cent grid is finer than the bins at low f)
        v = np.maximum(np.maximum(X[b], X[np.maximum(b - 1, 0)]), X[np.minimum(b + 1, len(X) - 1)])
        S[ok] += (0.82 ** (h - 1)) * v ** 0.6
    k = int(np.argmax(S))
    f0 = grid[k]
    # prefer the lower octave when it explains almost as much (missing-fundamental sounds)
    lo = np.argmin(np.abs(grid - f0 / 2))
    if abs(grid[lo] * 2 / f0 - 1) < 0.01 and S[lo] > 0.93 * S[k]: f0 = grid[lo]; k = lo
    conf = float((S[k] - np.median(S)) / (S[k] + 1e-9))
    pk = int(np.argmax(X[int(fmin / fr):]) + int(fmin / fr))
    return 69 + 12 * np.log2(f0 / 440), conf, (69 + 12 * np.log2(pk * fr / 440) if pk > 0 else None)


def chroma_err(measured_midi, expected_midi):
    """cents from the expected pitch class (folded to -600..600)"""
    c = (measured_midi - expected_midi) * 100
    return float((c + 600) % 1200 - 600)


# ------------------------------------------------------------------ descriptors
def spectral(seg, rate):
    """-> centroid Hz, flatness 0..1, 16 log band energies (dB, relative), rolloff85 Hz"""
    if len(seg) < 512:
        return 0.0, 0.0, [0.0] * 16, 0.0
    n = min(len(seg), int(rate * 1.0))
    seg = seg[:n]
    nfft = 1 << int(np.ceil(np.log2(n)))
    P = np.abs(np.fft.rfft(seg * np.hanning(n), nfft)) ** 2
    f = np.fft.rfftfreq(nfft, 1 / rate)
    tot = P.sum() + 1e-18
    cen = float((P * f).sum() / tot)
    band = P[(f > 50) & (f < 16000)] + 1e-18
    flat = float(np.exp(np.mean(np.log(band))) / np.mean(band))
    edges = np.geomspace(60, 16000, 17)
    bands = []
    for a, b in zip(edges[:-1], edges[1:]):
        bands.append(float(10 * np.log10(P[(f >= a) & (f < b)].sum() / tot + 1e-12)))
    c = np.cumsum(P); roll = float(f[min(len(f) - 1, np.searchsorted(c, 0.85 * c[-1]))])
    return cen, flat, bands, roll


def gated_loudness(m, rate):
    """a fast LUFS-like number: RMS of 400 ms blocks above -70 dB and above (mean - 10 dB), in dB (+ -0.7 offset)"""
    b = int(0.4 * rate); h = int(0.1 * rate)
    if len(m) < b: return float(db(np.sqrt(np.mean(m ** 2) + 1e-20)))
    e = np.array([np.mean(m[i:i + b] ** 2) for i in range(0, len(m) - b, h)])
    e = e[e > 1e-7]
    if not len(e): return -99.0
    rel = np.mean(e) * 0.1
    e = e[e > rel]
    return float(10 * np.log10(np.mean(e)) - 0.7)


def ebur128(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    return float(m[-1]) if m else None
