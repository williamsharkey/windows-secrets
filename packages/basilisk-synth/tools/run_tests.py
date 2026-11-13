#!/usr/bin/env python3
"""BASILISK SYNTH end-to-end tests through a real VST3 host (tools/testhost/bsynth-host).

    run_tests.py win  [--dir C:\\...synthtest]      (from WSL: renders run on Windows through cmd.exe)
    run_tests.py mac  [--ssh primary-mac]           (renders run on the Mac over ssh)

Every render loads the plugin, which resumes its own Windows XP; the notes are played by sndrec32.exe in there.
Checks: pitch (FFT, cents), onset timing against the reported latency, clicks on voice steals, the same DNA giving
the same sound twice, state save -> load giving the same sound, offline render, two instances at once, the machine
pausing when quiet and waking for a note, killing QEMU silencing the output (the sound is XP's), and no QEMU left.
"""
import json
import os
import subprocess
import sys
import threading
import time

import numpy as np
from scipy.io import wavfile

MODE = sys.argv[1] if len(sys.argv) > 1 else 'win'
WIN_DIR = r'C:\Users\willi\bsynth-test'
WSL_DIR = '/mnt/c/Users/willi/bsynth-test'
MAC = 'primary-mac'
MAC_DIR = '~/bsynth/test'
results = {}


def render(name, args, timeout=300):
    """render to NAME.wav; returns (stdout, wav array, sr)"""
    if MODE == 'win':
        # through a .bat: quotes in arguments do not survive WSL -> cmd.exe intact
        bat = os.path.join(WSL_DIR, 'run_%s.bat' % name)
        with open(bat, 'w') as f:
            f.write('@echo off\r\ncd /d %s\r\nset BSYNTH_MACHINE_DIR=%s\\machine-2\r\nbsynth-host.exe BasiliskSynth.vst3 %s.wav %s\r\n'
                    % (WIN_DIR, WIN_DIR, name, ' '.join(args)))
        out = subprocess.run(['cmd.exe', '/c', 'run_%s.bat' % name], capture_output=True, text=True, timeout=timeout, cwd=WSL_DIR).stdout
        path = os.path.join(WSL_DIR, name + '.wav')
    else:
        args = [a.strip('"') for a in args]
        q = ' '.join("'%s'" % a if ' ' in a or ';' in a or '#' in a else a for a in args)
        out = subprocess.run(['ssh', MAC, 'cd %s && BSYNTH_MACHINE_DIR=$HOME/bsynth/test/machine-2 ../bsynth-host '
                              'BasiliskSynth.vst3 %s.wav %s' % (MAC_DIR, name, q)], capture_output=True, text=True, timeout=timeout).stdout
        path = '/tmp/bsyn-%s.wav' % name
        subprocess.run(['scp', '-q', '%s:%s/%s.wav' % (MAC, MAC_DIR, name), path])
    if not os.path.exists(path):          # --instances K writes NAME-k.wav instead
        return out, np.zeros((1, 2)), 48000
    sr, x = wavfile.read(path)
    return out, x.astype(np.float64), sr


def qemu_count():
    if MODE == 'win':
        o = subprocess.run(['/mnt/c/Windows/System32/tasklist.exe'], capture_output=True, text=True).stdout
        return o.lower().count('qemu-system-i386')
    o = subprocess.run(['ssh', MAC, 'pgrep -f qemu-system-i386 | wc -l'], capture_output=True, text=True).stdout
    return int(o.strip() or 0)


def latency_ms(out):
    for l in out.splitlines():
        if 'latency' in l and 'ms' in l:
            return float(l.split('(')[1].split(' ')[0])
    return None


def onset(env, a, b, sr):
    seg = env[a:b]
    if len(seg) < 600:
        return None
    d = seg[240:] - seg[:-240]
    if d.max() < 2e-3:
        return None
    k = int(np.argmax(d)); pk = seg[k + 240]
    while k > 0 and seg[k] > 0.1 * pk:
        k -= 1
    return a + k


def peak_hz(x, sr):
    w = x[:8192]
    f = np.abs(np.fft.rfft(w * np.hanning(len(w)), 65536)); k = int(np.argmax(f[20:])) + 20
    al, be, ga = np.log(f[k - 1] + 1e-12), np.log(f[k] + 1e-12), np.log(f[k + 1] + 1e-12)
    return (k + 0.5 * (al - ga) / (al - 2 * be + ga)) * sr / 65536


def notes_analysis(x, sr, warm, times, notes, lat):
    m = x.mean(axis=1)
    env = np.convolve(np.abs(m), np.ones(64) / 64, 'same')
    rows = []
    for t, n in zip(times, notes):
        exp = warm + t + lat / 1000
        on = onset(env, int((exp - 0.2) * sr), int((exp + 0.5) * sr), sr)
        if on is None:
            rows.append((n, t, None, None)); continue
        rows.append((n, t, (on / sr - exp) * 1000, peak_hz(m[on + int(0.01 * sr):], sr)))
    return rows


def test_scale():
    times = [0.6 * k for k in range(10)]
    notes = [60, 62, 64, 65, 67, 69, 71, 72, 48, 84]
    score = ','.join('%g:%d:100:0.4' % (t, n) for t, n in zip(times, notes))
    out, x, sr = render('t_scale', ['--dna', '"ding#16;R200"', '--score', score, '--warmup', '10', '--tail', '2'])
    lat = latency_ms(out)
    rows = notes_analysis(x, sr, 10, times, notes, lat)
    base = rows[0]
    cents = [1200 * np.log2((hz / base[3]) / 2 ** ((n - base[0]) / 12)) for n, t, e, hz in rows if hz]
    errs = [e for n, t, e, hz in rows if e is not None]
    results['pitch'] = {'notes': len(rows), 'heard': len(errs), 'max_cents_off': round(float(np.max(np.abs(cents))), 1),
                        'cents': [round(c, 1) for c in cents]}
    results['timing'] = {'reported_latency_ms': lat, 'per_note_ms': [round(e, 1) for e in errs], 'onset_error_median_ms': round(float(np.median(errs)), 1),
                         'onset_error_spread_ms': round(float(np.max(errs) - np.min(errs)), 1),
                         'onset_error_std_ms': round(float(np.std(errs)), 1)}


def test_steal():
    # two recorders, notes faster than the sound: every note steals one; look for clicks (sample jumps) at the steals
    times = [0.15 * k for k in range(20)]
    score = ','.join('%g:%d:110:0.6' % (t, 60 + (k % 5) * 2) for k, t in enumerate(times))
    out, x, sr = render('t_steal', ['--dna', '"tada#2;R60"', '--score', score, '--warmup', '10', '--tail', '2'])
    m = x.mean(axis=1)
    d = np.abs(np.diff(m))
    # a click: a jump much bigger than the signal's own local slope
    loc = np.convolve(d, np.ones(480) / 480, 'same') + 1e-4
    ratio = d / loc
    clicks = int((ratio > 40).sum())
    results['steal_clicks'] = {'notes': len(times), 'recorders': 2, 'sample_jumps_over_40x_local': clicks,
                               'max_ratio': round(float(ratio.max()), 1), 'peak': round(float(np.abs(m).max()), 3)}


def envelope(x, sr):
    m = np.abs(x.mean(axis=1))
    hop = sr // 100
    return np.array([m[i:i + hop].mean() for i in range(0, len(m) - hop, hop)])


def similarity(a, b):
    """best correlation of two loudness envelopes over a +-300 ms shift"""
    best = 0
    for s in range(-30, 31):
        if s >= 0: u, v = a[s:], b[:len(b) - s]
        else: u, v = a[:len(a) + s], b[-s:]
        n = min(len(u), len(v)); u, v = u[:n], v[:n]
        if u.std() > 0 and v.std() > 0:
            best = max(best, float(np.corrcoef(u, v)[0, 1]))
    return best


def test_determinism_and_state():
    dna = '"tada<E@30[I ding R#8;A5R300"'.replace(' ', '')
    score = '0:60:100:1.5,2:67:100:1.5'
    out1, a, sr = render('t_det1', ['--dna', dna, '--score', score, '--warmup', '12', '--tail', '2',
                                    '--save-state', 't_state.bin'])
    out2, b, _ = render('t_det2', ['--dna', dna, '--score', score, '--warmup', '12', '--tail', '2'])
    out3, c, _ = render('t_state', ['--load-state', 't_state.bin', '--score', score, '--warmup', '12', '--tail', '2'])
    ea, eb, ec = envelope(a, sr), envelope(b, sr), envelope(c, sr)
    st = open(os.path.join(WSL_DIR, 't_state.bin'), 'rb').read() if MODE == 'win' else subprocess.run(
        ['ssh', MAC, 'cat %s/t_state.bin' % MAC_DIR], capture_output=True).stdout
    results['determinism'] = {'same_dna_twice_envelope_corr': round(similarity(ea, eb), 3),
                              'peaks': [round(float(np.abs(a).max()), 3), round(float(np.abs(b).max()), 3)]}
    results['state'] = {'state_bytes': len(st), 'state_has_dna': b'tada' in st,
                        'reloaded_vs_original_envelope_corr': round(similarity(ea, ec), 3)}


def test_offline():
    score = ','.join('%g:%d:100:0.3' % (0.4 * k, 60 + k) for k in range(8))
    t0 = time.time()
    out, x, sr = render('t_offline', ['--offline', '--dna', '"ding#16;R150"', '--score', score, '--warmup', '10', '--tail', '2'])
    took = time.time() - t0
    rend = [l for l in out.splitlines() if l.startswith('rendered')]
    results['offline'] = {'host_line': rend[0] if rend else out[-200:], 'wall_s': round(took, 1),
                          'peak': round(float(np.abs(x).max()), 3)}


def test_instances():
    if MODE != 'win' and os.path.exists('/tmp/bsyn-t_inst.wav'): os.remove('/tmp/bsyn-t_inst.wav')
    counts = []
    stop = threading.Event()

    def watch():
        while not stop.is_set():
            counts.append(qemu_count()); time.sleep(2)
    th = threading.Thread(target=watch); th.start()
    score = ','.join('%g:%d:100:0.4' % (0.5 * k, 60 + 2 * k) for k in range(6))
    out, x, sr = render('t_inst', ['--instances', '2', '--score', score, '--warmup', '12', '--tail', '2'])
    stop.set(); th.join()
    peaks = []
    for k in range(2):
        p = os.path.join(WSL_DIR, 't_inst-%d.wav' % k) if MODE == 'win' else '/tmp/bsyn-i%d.wav' % k
        if MODE != 'win':
            subprocess.run(['scp', '-q', '%s:%s/t_inst-%d.wav' % (MAC, MAC_DIR, k), p], check=True)
        sr2, y = wavfile.read(p); peaks.append(round(float(np.abs(y).max()), 3))
    time.sleep(1)
    results['instances'] = {'peaks': peaks, 'max_qemu_during': max(counts) if counts else None, 'qemu_after': qemu_count()}


def test_sleep_wake_and_kill():
    # 1) quiet for 14 s (the machine pauses after 4 s), then notes: they must still sound (it wakes)
    score = '0:60:100:0.5,1:64:100:0.5'
    out, x, sr = render('t_wake', ['--dna', '"ding#16;R150"', '--score', score, '--warmup', '14', '--tail', '2'])
    log = open(os.path.join(WSL_DIR, 'machine-2', 'plugin.log')).read() if MODE == 'win' else subprocess.run(
        ['ssh', MAC, 'cat %s/machine-2/plugin.log' % MAC_DIR], capture_output=True, text=True).stdout
    tail = log[-3000:]
    results['sleep_wake'] = {'slept': 'asleep' in tail, 'woke': 'woke' in tail,
                             'peak_after_wake': round(float(np.abs(x[int(14 * sr):]).max()), 3)}
    # 2) a long run of notes; kill QEMU at ~13 s: everything after must be silent
    score = ','.join('%g:%d:100:0.3' % (0.35 * k, 60 + (k % 8)) for k in range(30))
    res = {}

    def killer():
        time.sleep(12 + 6)       # load + warmup + 6 s of notes
        if MODE == 'win':
            subprocess.run(['/mnt/c/Windows/System32/taskkill.exe', '/f', '/im', 'qemu-system-i386w.exe'], capture_output=True)
        else:
            subprocess.run(['ssh', MAC, 'pkill -9 -f "[q]emu-system-i386"'])
        res['killed_at'] = time.time()
    t0 = time.time()
    th = threading.Thread(target=killer); th.start()
    out, x, sr = render('t_kill', ['--dna', '"ding#16;R150"', '--score', score, '--warmup', '12', '--tail', '2'])
    th.join()
    m = np.abs(x.mean(axis=1))
    hop = sr // 4
    blocks = [float(m[i:i + hop].max()) for i in range(0, len(m) - hop, hop)]
    loud = [i * 0.25 for i, v in enumerate(blocks) if v > 0.01]
    results['kill_qemu'] = {'audible_seconds': [loud[0], loud[-1]] if loud else None,
                            'render_seconds': round(len(m) / sr, 1),
                            'note': 'notes were scheduled until %.1f s; QEMU was killed about 6 s into them' % (12 + 0.35 * 30)}


if __name__ == '__main__':
    only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    for t in [test_scale, test_steal, test_determinism_and_state, test_offline, test_instances, test_sleep_wake_and_kill]:
        if only and t.__name__ not in only: continue
        try:
            t()
        except Exception as e:
            results[t.__name__] = 'ERROR %r' % e
        print(t.__name__, json.dumps(results, indent=None)[-400:], flush=True)
    results['qemu_left'] = qemu_count()
    print(json.dumps(results, indent=2))
    json.dump(results, open('test-results-%s.json' % MODE, 'w'), indent=2)
