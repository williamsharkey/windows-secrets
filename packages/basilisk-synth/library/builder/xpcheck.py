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


REVIEW_AUDIO = os.environ.get('REVIEW_AUDIO', '/mnt/c/Users/willi/Desktop/sndrec-library/audio')
XPVER = os.environ.get('XPVER', '1.2.2')
XPDIR = os.environ.get('XPDIR', '/mnt/c/Users/willi/libbuild-xp122')
PAUSE = os.path.join(WORK, 'xp-pause')          # touch it to pause between chunks (a synth lane's timing window)


PARFILE = os.path.join(WORK, 'xp-parallel')     # the VM count for the next chunk (the coordinator's 3-4 rule)


def lower_priority():
    """our QEMU and host processes (by their folder) to Below Normal, so other lanes keep their timing; returns the
    Windows CPU load in % (or None)"""
    tag = os.path.basename(XPDIR)
    r = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*%s*' -and $_.Name -ne 'powershell.exe' } | "
                        "ForEach-Object { try { (Get-Process -Id $_.ProcessId).PriorityClass = 'BelowNormal' } catch {} }; "
                        "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average" % tag],
                       capture_output=True, text=True, timeout=60)
    try: return float(r.stdout.strip().splitlines()[-1])
    except Exception: return None


def render_chunk(sel, a):
    import threading
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
    log = open(os.path.join(WORK, 'xp-batch.log'), 'a')
    pr = subprocess.Popen(['nice', '-n', '10', sys.executable, os.path.join(REPO, 'packages', 'basilisk-synth', 'tools', 'batch_render.py'), jp,
                           '--host', os.path.join(XPDIR, 'bsynth-host.exe'), '--plugin', os.path.join(XPDIR, 'BasiliskSynth.vst3'),
                           '--parallel', str(a.parallel), '--out-dir', out], stdout=log, stderr=subprocess.STDOUT, text=True)
    open(os.path.join(WORK, 'run', 'xpcheck-batch.pid'), 'w').write(str(pr.pid))
    cpu = []
    while pr.poll() is None:
        try:
            c = lower_priority()
            if c is not None: cpu.append(c)
        except Exception: pass
        time.sleep(15)
    wall = time.time() - t0
    a.cpu = sum(cpu) / len(cpu) if cpu else None
    n_ok = 0
    for o, (p, notes, tail) in meta.items():
        w = os.path.join(out, o)
        if not os.path.exists(w):
            prev = p.get('xp_check')
            if prev and prev.get('xpver') != XPVER: p.setdefault('xp_check_history', []).append(prev)
            p['xp_check'] = {'ok': False, 'why': ['XP render failed'], 'xpver': XPVER, 'plugin': 'BASILISK SYNTH %s release' % XPVER}; continue
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
        if not os.path.exists(ref): ref = os.path.join(REVIEW_AUDIO, p['slug'] + '.mp3')
        cmp = compare(w, on, ref) if os.path.exists(ref) and 'silent' not in why else None
        why += verdict(p, cmp)
        d = (I - p['phrase_lufs']) if (I is not None and p.get('phrase_lufs') is not None) else None
        prev = p.get('xp_check')
        if prev and prev.get('xpver') != XPVER: p.setdefault('xp_check_history', []).append(prev)
        p['xp_check'] = {'ok': not why, 'why': why, 'offset_s': round(on, 2),
                         'plugin': 'BASILISK SYNTH %s release' % XPVER, 'xpver': XPVER,
                         'lufs': I, 'peak_db': r['peak_db'], 'vs_311_db': round(d, 1) if d is not None else None,
                         'onsets': r['onsets'], 'heard': r['heard'], 'gaps_10ms': gaps(w), **(cmp or {})}
        n_ok += not why
        if getattr(a, 'keep', None):
            import shutil; os.makedirs(a.keep, exist_ok=True); shutil.move(w, os.path.join(a.keep, '%s-%s.wav' % (p['slug'], XPVER)))
        else:
            os.remove(w)
    return n_ok, len(meta), wall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rejudge', action='store_true')
    ap.add_argument('--all', action='store_true', help='every preset that ships to XP (v2), checked again on XPVER')
    ap.add_argument('--chunk', type=int, default=60)
    ap.add_argument('--names', help='only these preset names (comma-separated)')
    ap.add_argument('--keep', help='keep the WAVs in this folder')
    ap.add_argument('--n', type=int, default=0); ap.add_argument('--parallel', type=int, default=2)
    a = ap.parse_args()
    if a.rejudge: return rejudge()
    L = load_json('library.json')
    done = lambda p: p.get('xp_check') and p['xp_check'].get('xpver') == XPVER
    if a.all: sel = [p for p in L if not p['v3'] and not done(p)]
    else: sel = [p for p in L if 'XP' in p['ships'] and p['edition'] == 'xp' and not p.get('xp_check')]
    if a.names:
        want = [n.strip() for n in a.names.split(',')]
        sel = [p for p in L if p['name'] in want]
    if a.n: sel = sel[:a.n]
    by_slug = {p['slug']: p for p in L}
    tot_ok = tot = 0; t0 = time.time()
    for k in range(0, len(sel), a.chunk):
        while os.path.exists(PAUSE): time.sleep(20)
        part = [by_slug[p['slug']] for p in sel[k:k + a.chunk]]
        try: a.parallel = max(1, min(4, int(open(PARFILE).read().strip())))
        except Exception: pass
        ok, n, wall = render_chunk(part, a)
        if a.cpu is not None and a.cpu > 85 and a.parallel > 3:
            open(PARFILE, 'w').write('3\n')          # Windows stayed busy: back to 3 VMs
        print('  chunk with %d VMs, Windows CPU %s%%' % (a.parallel, '%.0f' % a.cpu if a.cpu is not None else '?'), flush=True)
        tot_ok += ok; tot += n
        save_json('library.json', L)
        print('chunk %d: %d/%d pass (%.0f s); total %d/%d of %d, %.0f s' % (k // a.chunk, ok, n, wall, tot_ok, tot, len(sel), time.time() - t0), flush=True)
    print('XP check (%s): %d/%d pass, %.0f s' % (XPVER, tot_ok, tot, time.time() - t0))


if __name__ == '__main__':
    main()
