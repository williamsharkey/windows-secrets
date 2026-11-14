"""Analysis of one render (48 kHz float stereo from render311) against the score that made it.

Per isolated note: heard, peak, attack, decay, sustain at the end of the hold, release tail, pitch and its error.
Whole render: peak, overs, card clipping (samples at the card's full scale), DC, loudness, tail at the end,
stereo width, onsets heard; and a feature vector (spectrum bands + envelope shape + descriptors) for novelty.
"""
import re
import numpy as np
from audio import read_wav, frames_rms, pitch, spectral, gated_loudness, db, chroma_err

SR = 48000


def gain_of(dna):
    m = re.search(r';[^;]*?G(-?\d+)', dna)
    return int(m.group(1)) if m else 0


def analyze(path, score, tail, kind, dna, singles=None):
    x, rate = read_wav(path)
    assert rate == SR
    L, R = x[:, 0], x[:, 1] if x.shape[1] > 1 else x[:, 0]
    m = 0.5 * (L + R)
    fs = 10 ** (gain_of(dna) / 20)            # the card's full scale after the plugin's G
    peak = float(np.abs(x).max()) if len(x) else 0.0
    res = {'seconds': round(len(m) / SR, 3), 'peak_db': round(float(db(peak)), 2),
           'overs': int((np.abs(x) > 1.0).sum()),
           'card_clip': int((np.abs(x) >= 0.9995 * fs).sum()),
           'dc': round(float(max(abs(L.mean()), abs(R.mean())) / (np.sqrt(np.mean(m ** 2)) + 1e-12)), 4),
           'loud': round(gated_loudness(m, SR), 2), 'peak_rel_fs_db': round(float(db(peak / fs)), 2)}
    side = 0.5 * (L - R)
    res['width'] = round(float(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(m ** 2)) + 1e-12)), 3)
    env = frames_rms(m, SR)                   # 10 ms hop
    emax = float(env.max()) if len(env) else 0.0
    end_rms = float(np.sqrt(np.mean(m[-int(0.25 * SR):] ** 2))) if len(m) > SR // 4 else 0.0
    res['end_rel_db'] = round(float(db(end_rms / (emax + 1e-12))), 1)
    # onsets heard: every distinct note-on, sound within the window after it
    ons = sorted(set(round(n[0], 3) for n in score))
    win = 1.0 if kind in ('pad', 'drone', 'fx') else 0.3
    heard = 0
    for t in ons:
        seg = m[int(t * SR):int((t + win) * SR)]
        if len(seg) and db(np.sqrt(np.mean(seg ** 2))) - db(fs) > -50: heard += 1
    res['onsets'], res['heard'] = len(ons), heard
    if singles is None:
        return res
    notes = []
    for i in singles:
        t, n, v, d = score[i]
        nxt = min([s[0] for s in score if s[0] > t + 1e-6] + [len(m) / SR])
        a, b = int(t * SR), int(min(nxt, len(m) / SR) * SR)
        seg = m[a:b]
        e = frames_rms(seg, SR)
        if not len(e) or e.max() <= 0:
            notes.append({'note': n, 'heard': False}); continue
        pk = int(np.argmax(e)); ep = float(e.max())
        rel = e / ep
        on12 = int(np.argmax(rel > 10 ** (-12 / 20)))
        hold_end = int(d / 0.01)
        sus = float(db(rel[min(hold_end - 3, len(rel) - 1)])) if hold_end > 3 else 0.0
        below20 = np.nonzero(rel[pk:] < 0.1)[0]
        dec20 = float(below20[0] * 0.01) if len(below20) else float((len(rel) - pk) * 0.01)
        after = rel[hold_end:]
        below40 = np.nonzero(after < 0.01)[0]
        relt = float(below40[0] * 0.01) if len(below40) else float(len(after) * 0.01)
        # pitch: from just after the peak, inside the hold
        pa = a + int((pk * 0.01 + 0.03) * SR)
        pb = min(a + int(d * SR), pa + int(0.5 * SR))
        if pb - pa < 4096: pb = pa + 4096
        f0, conf, spk = pitch(m[pa:pb], SR)
        nr = {'note': n, 'heard': bool(db(ep) - db(fs) > -50), 'peak_db': round(float(db(ep)), 1),
              'attack': round(on12 * 0.01, 3), 'peak_t': round(pk * 0.01, 3), 'sus_db': round(sus, 1),
              'dec20': round(dec20, 2), 'rel40': round(relt, 2)}
        if f0 is not None:
            nr.update(f0=round(float(f0), 2), conf=round(conf, 3), err=round(chroma_err(f0, n), 1),
                      spk_err=round(chroma_err(spk, n), 1) if spk is not None else None)
        notes.append(nr)
    res['notes'] = notes
    # features of the middle single note (or the first)
    ref = singles[1] if len(singles) > 1 else singles[0]
    t, n, v, d = score[ref]
    a = int(t * SR)
    seg = m[a:a + int(min(d + 0.5, 2.5) * SR)]
    cen, flat, bands, roll = spectral(seg[int(0.01 * SR):], SR)
    e = frames_rms(seg, SR, hop=0.05, win=0.05)
    e = e / (e.max() + 1e-12)
    shape = [round(float(max(-48.0, db(v))) / 48 + 1, 3) for v in e[:30]] + [0.0] * max(0, 30 - len(e))
    res.update(centroid=round(cen), flatness=round(flat, 4), rolloff=round(roll), bands=[round(b, 1) for b in bands],
               shape=shape[:30])
    return res
