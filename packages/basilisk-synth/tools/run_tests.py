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
            f.write('@echo off\r\ncd /d %s\r\nbsynth-host.exe BasiliskSynth.vst3 %s.wav %s\r\n'
                    % (WIN_DIR, name, ' '.join(args)))
        out = subprocess.run(['cmd.exe', '/c', 'run_%s.bat' % name], capture_output=True, text=True, timeout=timeout, cwd=WSL_DIR).stdout
        path = os.path.join(WSL_DIR, name + '.wav')
    else:
        args = [a.strip('"') for a in args]
        q = ' '.join("'%s'" % a if ' ' in a or ';' in a or '#' in a else a for a in args)
        out = subprocess.run(['ssh', MAC, 'cd %s && ../bsynth-host '
                              'BasiliskSynth.vst3 %s.wav %s' % (MAC_DIR, name, q)], capture_output=True, text=True, timeout=timeout).stdout
        path = '/tmp/bsyn-%s.wav' % name
        subprocess.run(['scp', '-q', '%s:%s/%s.wav' % (MAC, MAC_DIR, name), path])
    if not os.path.exists(path):          # --instances K writes NAME-k.wav instead
        return out, np.zeros((1, 2)), 48000
    sr, x = wavfile.read(path)
    return out, x.astype(np.float64), sr


def qemu_count():
    if MODE == 'win':
        # our QEMUs only: the ones whose command line uses this test folder's machine or a bsynth temp folder
        ps = "(Get-CimInstance Win32_Process -Filter \"name='qemu-system-i386w.exe'\" | Where-Object { $_.CommandLine -like '*bsynth-test*' }).Count"
        o = subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-Command', ps], capture_output=True, text=True).stdout
        return int(o.strip() or 0)
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
    log = open('/mnt/c/Users/willi/AppData/Local/BASILISK SYNTH/plugin.log').read() if MODE == 'win' else subprocess.run(
        ['ssh', MAC, 'cat ~/Library/Caches/BASILISK\\ SYNTH/plugin.log'], capture_output=True, text=True).stdout
    tail = log[-3000:]
    results['sleep_wake'] = {'slept': 'asleep' in tail, 'woke': 'woke' in tail,
                             'peak_after_wake': round(float(np.abs(x[int(14 * sr):]).max()), 3)}
    # 2) a long run of notes; kill QEMU at ~13 s: everything after must be silent
    score = ','.join('%g:%d:100:0.3' % (0.35 * k, 60 + (k % 8)) for k in range(30))
    res = {}

    def killer():
        time.sleep(12 + 6)       # load + warmup + 6 s of notes
        if MODE == 'win':
            # only the QEMU our own bsynth-host started (other programs on this PC may run QEMUs too)
            ps = ("$h = Get-CimInstance Win32_Process -Filter \"name='bsynth-host.exe'\" | ForEach-Object ProcessId; "
                  "Get-CimInstance Win32_Process -Filter \"name='qemu-system-i386w.exe'\" | Where-Object { $h -contains $_.ParentProcessId } | "
                  "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
            subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-Command', ps], capture_output=True)
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


def test_v2():
    """DNA v2 (DNA.md 5): pan, offsets, drawn envelopes, macros, a library sound; one note each"""
    r = {}
    def one(name, dna, score='0:60:100:1.2', warm=12):
        out, x, sr = render(name, ['--dna', '"%s"' % dna, '--score', score, '--warmup', str(warm), '--tail', '2'])
        return x[int(warm * sr):], sr, latency_ms(out) or 100
    xl, sr, lat = one('t_panl', 'ding#16Q-100;R200')
    xr, _, _ = one('t_panr', 'ding#16Q100;R200')
    rms = lambda v: float(np.sqrt((v ** 2).mean()))
    r['pan_left_L_R'] = [round(rms(xl[:, 0]), 4), round(rms(xl[:, 1]), 4)]
    r['pan_right_L_R'] = [round(rms(xr[:, 0]), 4), round(rms(xr[:, 1]), 4)]
    # offsets: layer 2 (right) starts 500 ms after layer 1 (left)
    x, sr, lat = one('t_offset', 'ding#8Q-100/ding#8O500Q100;R100', '0:60:100:1.5')
    on = []
    for ch in (0, 1):          # the first time each side gets loud (each side has one layer)
        env = np.convolve(np.abs(x[:, ch]), np.ones(64) / 64, 'same')
        k = np.nonzero(env[:int(2 * sr)] > 0.2 * env[:int(2 * sr)].max())[0]
        on.append(int(k[0]) if len(k) else None)
    r['offset_ms'] = {'asked': 500, 'measured': round((on[1] - on[0]) / sr * 1000, 1) if None not in on else None}
    # a drawn envelope on a sustained organ: silent start, loudest at 500 ms, gone by 1000 ms
    x, sr, lat = one('t_ja', 'organ_pipe_open_31#16Ja0,0.500,100.1000,0;R100', '0:60:100:2.0')
    e = envelope(x, sr)
    k0 = int(np.argmax(e > e.max() * 0.02))
    r['ja_envelope'] = {'asked': '0 -> 100 % at 500 ms -> 0 at 1000 ms', 'peak_ms_after_onset': int((int(np.argmax(e)) - k0) * 10),
                        'level_at_250ms_rel': round(float(e[k0 + 25] / e.max()), 2), 'level_at_1100ms_rel': round(float(e[min(len(e) - 1, k0 + 110)] / e.max()), 3)}
    # a macro: the same DNA, macro 1 at 0 and at 100, mapped to the layer's level 10..100 %
    x0, _, _ = one('t_m0', 'ding#16;m1=0m10L10,100')
    x1, _, _ = one('t_m1', 'ding#16;m1=100m10L10,100')
    r['macro_level_ratio'] = round(float(np.abs(x0).max() / max(1e-9, np.abs(x1).max())), 3)
    # a sound from the library disc, at its root note
    x, sr, lat = one('t_lib', 'kalimba_c4#16;R300')
    m = x.mean(axis=1)
    env = np.convolve(np.abs(m), np.ones(64) / 64, 'same')
    on = onset(env, 0, int(1.0 * sr), sr)
    r['library_kalimba_c4'] = {'peak': round(float(np.abs(m).max()), 3), 'hz': round(peak_hz(m[on + int(0.05 * sr):], sr), 1) if on is not None else None, 'c4_hz': 261.6}
    results['v2'] = r


def test_host():
    """what a DAW does, in our own host: automation (a macro), a preset change while notes play, state round trip,
    real-time timing on a dummy device; on Windows also the keyboard inside XP (mouse and PC keys) through the editor"""
    r = {}
    def seg_peaks(x, sr, warm, times, w=0.45):
        m = np.abs(x.mean(axis=1))
        return [round(float(m[int((warm + t + 0.08) * sr):int((warm + t + w) * sr)].max()), 3) for t in times]
    # a macro automated mid-score: level 10 % -> 100 %
    times = [0, 1, 2, 3]
    out, x, sr = render('t_auto', ['--dna', '"ding#16;m1=0m10L10,100"', '--score', ','.join('%g:60:100:0.4' % t for t in times),
                                   '--set', '"Macro 1@1.8=100"', '--warmup', '12', '--tail', '1'])
    pk = seg_peaks(x, sr, 12, times)
    r['macro_automation'] = {'peaks': pk, 'after_over_before': round(pk[3] / max(1e-9, pk[0]), 1), 'host': [l for l in out.splitlines() if 'automation' in l]}
    # a preset change while playing: notes every 0.5 s; program 5 at 2.6 s
    times = [0.5 * k for k in range(20)]
    out, x, sr = render('t_prog', ['--score', ','.join('%g:%d:100:0.3' % (t, 60 + k % 5) for k, t in enumerate(times)), '--set', 'program@2.6=5',
                                   '--warmup', '12', '--tail', '2', '--state-roundtrip', '--timing'])
    pk = seg_peaks(x, sr, 12, times, 0.4)
    r['preset_change_while_playing'] = {'peaks': pk, 'silent_notes': sum(p < 0.01 for p in pk),
                                        'host': [l for l in out.splitlines() if 'automation' in l or 'roundtrip' in l]}
    r['state_roundtrip'] = [l for l in out.splitlines() if 'roundtrip' in l]
    r['realtime_timing'] = [l for l in out.splitlines() if l.startswith('timing')]
    if MODE == 'win':
        # the keyboard in Windows, through the editor: "PC keys" on, then the 'a' key (C4), then the mouse on C4
        menu = 19
        ui = ['--ui', '0.3:click:117:%d' % (690 + menu), '--ui', '1.0:key:a', '--ui', '1.8:keyup:a',
              '--ui', '3.0:down:298:%d' % (723 + menu), '--ui', '3.8:up:298:%d' % (723 + menu)]
        out, x, sr = render('t_kbd', ['--editor', '--score', '"7:30:1:0.05"', '--warmup', '14', '--tail', '1'] + ui)
        m = np.abs(x.mean(axis=1))
        blk = [round(float(m[int((14 + t) * sr):int((14 + t + 0.5) * sr)].max()), 3) for t in (0.0, 1.0, 2.2, 3.0)]
        r['xp_keyboard'] = {'peak_quiet_0s': blk[0], 'peak_pc_key_1s': blk[1], 'peak_after_release': blk[2], 'peak_mouse_key_3s': blk[3]}
    results['host'] = r


if __name__ == '__main__':
    only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
    for t in [test_scale, test_steal, test_determinism_and_state, test_offline, test_instances, test_sleep_wake_and_kill, test_v2, test_host]:
        if only and t.__name__ not in only: continue
        try:
            t()
        except Exception as e:
            results[t.__name__] = 'ERROR %r' % e
        print(t.__name__, json.dumps(results, indent=None)[-400:], flush=True)
    results['qemu_left'] = qemu_count()
    print(json.dumps(results, indent=2))
    json.dump(results, open('test-results-%s.json' % MODE, 'w'), indent=2)
