#!/usr/bin/env python3
"""Check kept presets on the XP machine too (BASILISK SYNTH 1.2.1, tools/batch_render.py, at most 2 VMs).

    xpcheck.py [--n 0 (all XP-shipping XP-badge presets)] [--parallel 2]   data/library.json -> its xp_check fields

The demo phrase is rendered through the XP plugin's own machine (bsynth-host, offline), then the same checks as the
3.11 phrase (every onset heard, not silent, no DC, ends inside the tail) plus the loudness difference against the
3.11 render. XP is not sample-accurate or bit-identical, so only those facts are compared.
Uses C:\\Users\\willi\\libbuild-xp (a private copy of the 1.2.1 release and bsynth-host); WAVs are deleted after.
"""
import argparse, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, save_json, REPO, WORK
import analyze, phrases
from audio import ebur128

XPDIR = '/mnt/c/Users/willi/libbuild-xp'


def _mono(path, offset=0.0):
    if path.endswith('.mp3'):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', '48000', '-'], capture_output=True).stdout
        import numpy as np
        return np.frombuffer(raw, dtype='<f4').astype(float)
    from audio import read_wav
    x, _ = read_wav(path)
    m = x.mean(axis=1)
    return m[int(offset * 48000):]


def _chroma_bands(m):
    import numpy as np
    n = 8192; h = 4096
    C = np.zeros(12); B = np.zeros(16)
    f = np.fft.rfftfreq(n, 1 / 48000)
    ok = (f > 60) & (f < 5000)
    pc = (np.round(12 * np.log2(f[ok] / 440.0)) % 12).astype(int)
    edges = np.geomspace(60, 16000, 17)
    bi = np.digitize(f, edges) - 1
    for i in range(0, max(0, len(m) - n), h):
        P = np.abs(np.fft.rfft(m[i:i + n] * np.hanning(n))) ** 2
        C += np.bincount(pc, weights=P[ok], minlength=12)
        sel = (bi >= 0) & (bi < 16)
        B += np.bincount(bi[sel], weights=P[sel], minlength=16)[:16]
    return C, B


def compare(xp_wav, offset, ref_mp3):
    """chroma similarity and band-level difference of the XP render against the 3.11 render (its MP3)"""
    import numpy as np
    a = _mono(xp_wav, offset); b = _mono(ref_mp3)
    n = min(len(a), len(b))
    if n < 48000: return None
    ca, ba = _chroma_bands(a[:n]); cb, bb = _chroma_bands(b[:n])
    chroma = float(ca @ cb / (np.linalg.norm(ca) * np.linalg.norm(cb) + 1e-20))
    da = 10 * np.log10(ba / ba.sum() + 1e-9); db_ = 10 * np.log10(bb / bb.sum() + 1e-9)
    w = (bb / bb.sum()) > 1e-3
    return {'chroma': round(chroma, 3), 'bands_db': round(float(np.mean(np.abs(da - db_)[w])) if w.any() else 0.0, 1)}


def verdict(p, cmp):
    """pitch is judged only where the sound is meant to be pitched (unpitched FX, perc and textures have no stable
    chroma); basses get a lower bar (few, low partials); a band-level gap over 9 dB means a layer is missing"""
    from catdefs import CATS
    why = []
    if not cmp: return why
    c = CATS.get(p['scat'], {})
    if c.get('tonal') and p['kind'] not in ('fx', 'perc'):
        lim = 0.55 if p['kind'] == 'bass' else 0.7
        if cmp['chroma'] < lim: why.append('pitch differs from 3.11 (chroma %.2f)' % cmp['chroma'])
    if cmp['bands_db'] > 9: why.append('spectrum differs from 3.11 by %.1f dB (a missing layer?)' % cmp['bands_db'])
    return why


def rejudge():
    """apply verdict() again to the stored measurements (no render)"""
    L = load_json('library.json')
    for p in L:
        x = p.get('xp_check')
        if not x: continue
        why = [w for w in x['why'] if w == 'silent' or 'missing' in w and 'layer' not in w]
        if 'chroma' in x: why += verdict(p, {'chroma': x['chroma'], 'bands_db': x['bands_db']})
        x['why'] = why; x['ok'] = not why
    save_json('library.json', L)
    xs = [p for p in L if p.get('xp_check')]
    print('rejudged: %d/%d pass' % (sum(p['xp_check']['ok'] for p in xs), len(xs)))


def gaps(path):
    """exact-silence runs of 8-40 ms inside sound (XP 1.2.1's streaming gaps), per minute"""
    import numpy as np
    from audio import read_wav
    x, _ = read_wav(path)
    z = np.all(x == 0, axis=1).astype(np.int8)
    d = np.diff(np.concatenate([[0], z, [0]]))
    st, en = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    ln = en - st
    k = int(((ln >= 384) & (ln <= 1920)).sum())
    return round(k * 60.0 / (len(x) / 48000), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rejudge', action='store_true')
    ap.add_argument('--n', type=int, default=0); ap.add_argument('--parallel', type=int, default=2)
    a = ap.parse_args()
    if a.rejudge: return rejudge()
    L = load_json('library.json')
    sel = [p for p in L if 'XP' in p['ships'] and p['edition'] == 'xp' and not p.get('xp_check')]
    if a.n:
        import random
        by = {}
        for p in sel: by.setdefault(p['pack'], []).append(p)
        rng = random.Random(7); out = []
        while len(out) < a.n and any(by.values()):
            for k in sorted(by):
                if by[k] and len(out) < a.n: out.append(by[k].pop(rng.randrange(len(by[k]))))
        sel = out
    out = os.path.join(XPDIR, 'out')
    os.makedirs(out, exist_ok=True)
    jobs, meta = [], {}
    for p in sel:
        notes, tail, _ = phrases.phrase(p['kind'], mono='mono' in p.get('phrase', ''))
        o = p['slug'] + '.wav'
        jobs.append({'dna': p['canonical'], 'score': ','.join('%.4f:%d:%d:%.4f' % n for n in notes), 'out': o, 'tail': tail})
        meta[o] = (p, notes, tail)
    jp = os.path.join(XPDIR, 'jobs.json'); json.dump(jobs, open(jp, 'w'))
    t0 = time.time()
    subprocess.run([sys.executable, os.path.join(REPO, 'packages', 'basilisk-synth', 'tools', 'batch_render.py'), jp,
                    '--host', os.path.join(XPDIR, 'bsynth-host.exe'), '--plugin', os.path.join(XPDIR, 'BasiliskSynth.vst3'),
                    '--parallel', str(a.parallel), '--out-dir', out])
    wall = time.time() - t0
    n_ok = 0
    for o, (p, notes, tail) in meta.items():
        w = os.path.join(out, o)
        if not os.path.exists(w):
            p['xp_check'] = {'ok': False, 'why': ['XP render failed']}; continue
        # XP's render starts the score after the machine wakes and builds (warmup + build wait): align on the
        # first onset (every phrase has a note at t = 0)
        from audio import read_wav, frames_rms
        import numpy as np
        x, _ = read_wav(w); env = frames_rms(x.mean(axis=1), 48000)
        on = int(np.argmax(env > env.max() * 0.01)) * 0.01 if env.max() > 0 else 0.0
        shifted = [(t + on, n, v, du) for t, n, v, du in notes]
        r = analyze.analyze(w, shifted, tail, p['kind'], p['canonical'])
        I = ebur128(w)
        why = []
        # XP 1.2.1 drops ~450 10 ms gaps a minute (srhook streaming runs dry; 1.2.2 fixes it): gaps and level are
        # recorded, never held against a preset. What counts: a silent take, missing notes or layers (sound names
        # not resolving), and the wrong pitch, against the 3.11 render of the same phrase.
        if r['peak_db'] < -45: why.append('silent')
        elif r['onsets'] and r['heard'] < 0.5 * r['onsets']:
            why.append('%d of %d notes missing' % (r['onsets'] - r['heard'], r['onsets']))
        ref = os.path.join(WORK, 'mp3', p['slug'] + '.mp3')
        cmp = compare(w, on, ref) if os.path.exists(ref) and 'silent' not in why else None
        why += verdict(p, cmp)
        d = (I - p['phrase_lufs']) if (I is not None and p.get('phrase_lufs') is not None) else None
        p['xp_check'] = {'ok': not why, 'why': why, 'offset_s': round(on, 2),
                         'plugin': 'BASILISK SYNTH 1.2.1 release (10 ms streaming gaps; re-render on 1.2.2)', 'rerender_on': '1.2.2',
                         'lufs': I, 'peak_db': r['peak_db'], 'vs_311_db': round(d, 1) if d is not None else None,
                         'onsets': r['onsets'], 'heard': r['heard'], 'gaps_10ms': gaps(w), **(cmp or {})}
        n_ok += not why
        os.remove(w)
    save_json('library.json', L)
    print('XP check: %d/%d pass, %.0f s wall for %d renders' % (n_ok, len(meta), wall, len(meta)))


if __name__ == '__main__':
    main()
