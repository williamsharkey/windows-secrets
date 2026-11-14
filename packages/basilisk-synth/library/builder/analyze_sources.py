#!/usr/bin/env python3
"""Measure every source a DNA can name, from the machine's own files (3.11 machine: drive.zip for C:\\WINDOWS and
C:\\XPSOUNDS, library.zip for drive L:). Writes data/sources.json: per NAME its origin, rate, length, lead-in,
loudness, root (MIDI float) and pitch confidence, decay, brightness, noisiness, and a coarse role.

    analyze_sources.py
"""
import json, os, re, sys, zipfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BUILTIN, MACHINE, origin, save_json
from audio import read_wav, frames_rms, pitch, spectral, db

NOTE = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}


def name_root(n):
    """a root written in a library name: marimba_c4 -> 60, piano_upright_cs4 -> 61, crystal_bell_bb5 -> 82"""
    m = re.search(r'_([a-g])(s|b)?(\d)$', n)
    if not m: return None
    v = NOTE[m.group(1)] + (1 if m.group(2) == 's' else -1 if m.group(2) == 'b' else 0)
    return 12 * (int(m.group(3)) + 1) + v


def segments(m, rate, env):
    """note segments by onset (spectral flux on 10 ms frames): [[start_s, end_s, root, conf, peak_db], ...]"""
    h = int(0.01 * rate); w = 2 * h
    n = (len(m) - w) // h
    if n < 8: return []
    idx = np.arange(n)[:, None] * h + np.arange(w)[None, :]
    S = np.abs(np.fft.rfft(m[idx] * np.hanning(w), axis=1))
    S = np.log1p(S * 50)
    flux = np.maximum(S[1:] - S[:-1], 0).sum(axis=1)
    flux = np.concatenate([[0], flux])
    thr = np.median(flux) + 2.5 * (np.percentile(flux, 90) - np.median(flux) + 1e-9)
    emax = env.max()
    ons = [0]
    for i in range(2, n - 2):
        if flux[i] > thr and flux[i] == flux[i - 2:i + 3].max() and i - ons[-1] >= 8 and env[min(i, len(env) - 1)] > emax * 0.05:
            ons.append(i)
    out = []
    for k, a in enumerate(ons[:8]):
        b = ons[k + 1] if k + 1 < len(ons) else n
        seg = m[a * h:b * h]
        if len(seg) < int(0.06 * rate): continue
        e = env[a:b]
        pk = int(np.argmax(e)) if len(e) else 0
        r, c, _ = pitch(seg[int((pk * 0.01 + 0.02) * rate):][:int(0.5 * rate)], rate) if len(seg) > 1500 else (None, 0, None)
        out.append([round(a * 0.01, 3), round(b * 0.01, 3), round(float(r), 2) if r is not None else None, round(c, 3),
                    round(float(db(e.max() if len(e) else 0)), 1)])
    return out


def analyze(data):
    x, rate = read_wav(data)
    m = x.mean(axis=1)
    dur = len(m) / rate
    peak = float(np.abs(m).max()) if len(m) else 0
    env = frames_rms(m, rate)
    emax = env.max() if len(env) else 0
    t = np.arange(len(env)) * 0.01
    on = int(np.argmax(env > emax * 10 ** (-30 / 20))) if emax > 0 else 0
    pk = int(np.argmax(env))
    after = env[pk:]
    dec30 = float(np.argmax(after < emax * 10 ** (-30 / 20)) * 0.01) if (after < emax * 10 ** (-30 / 20)).any() else float(len(after) * 0.01)
    last = np.nonzero(env > emax * 10 ** (-45 / 20))[0]
    tail = float(last[-1] * 0.01) if len(last) else 0.0
    # pitch over the body: from 30 ms after the peak, up to 0.6 s
    a = int((pk * 0.01 + 0.03) * rate); seg = m[a:a + int(0.6 * rate)]
    if len(seg) < 2048: seg = m[max(0, a - 2048):a + 4096]
    root, conf, spk = pitch(seg, rate)
    cen, flat, bands, roll = spectral(m[int(pk * 0.01 * rate):], rate)
    att = float((pk - on) * 0.01)
    segs = segments(m, rate, env)
    return dict(segs=segs, rate=rate, ch=x.shape[1], seconds=round(dur, 3), leadin=round(on * 0.01, 3), attack=round(att, 3),
                peak_db=round(float(db(peak)), 1), rms_db=round(float(db(np.sqrt(np.mean(m ** 2)))), 1),
                decay30=round(dec30, 3), tail=round(tail, 3),
                root=round(float(root), 2) if root is not None else None, pitch_conf=round(conf, 3),
                spec_peak=round(float(spk), 2) if spk is not None else None,
                centroid=round(cen), flatness=round(flat, 4), rolloff=round(roll))


def main():
    out = {}
    dz = zipfile.ZipFile(os.path.join(MACHINE, 'drive.zip'))
    files = {'chimes': 'WINDOWS/CHIMES.WAV', 'chord': 'WINDOWS/CHORD.WAV', 'ding': 'WINDOWS/DING.WAV',
             'tada': 'WINDOWS/TADA.WAV', 'ringin': 'WINDOWS/RINGIN.WAV', 'ringout': 'WINDOWS/RINGOUT.WAV'}
    for i, n in enumerate(BUILTIN):
        f = files.get(n, 'XPSOUNDS/X%02d.WAV' % i)
        r = analyze(dz.read(f)); r.update(name=n, origin=origin(n), category='windows', file311=f)
        out[n] = r
    lz = zipfile.ZipFile(os.path.join(MACHINE, 'library.zip'))
    for line in lz.read('LIBRARY.TSV').decode('utf-8', 'replace').splitlines():
        p = line.split('\t')
        if len(p) < 5: continue
        n, cat, path = p[0], p[1], p[2].lstrip('\\').replace('\\', '/')
        try:
            r = analyze(lz.read(path))
        except Exception as e:
            print('skip', n, e); continue
        r.update(name=n, origin='library', category=cat, file311=path, licence=p[4])
        nr = name_root(n)
        if nr is not None: r['name_root'] = nr
        out[n] = r
    # roles: tonal when the pitch is confident and the sound is not noise
    for n, r in out.items():
        tonal = r['pitch_conf'] > 0.55 and r['flatness'] < 0.12
        if 'name_root' in r: tonal = True
        r['tonal'] = bool(tonal)
        if 'name_root' in r and r['root'] is not None:
            # trust the name's pitch class; keep the measured fine tuning when it agrees within 60 cents
            d = (r['root'] - r['name_root'] + 6) % 12 - 6
            r['root_used'] = round(r['name_root'] + (d if abs(d) < 0.6 else 0), 2)
        else:
            r['root_used'] = r['root']
        r['role'] = ('click' if r['seconds'] < 0.12 else
                     'noise' if r['flatness'] > 0.2 else
                     'long' if r['seconds'] > 4 else
                     'tonal' if tonal else 'texture')
    save_json('sources.json', out)
    print(len(out), 'sources;', sum(r['tonal'] for r in out.values()), 'tonal')


if __name__ == '__main__':
    main()
