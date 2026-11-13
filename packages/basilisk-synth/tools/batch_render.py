#!/usr/bin/env python3
"""Batch rendering (DNA.md 5.7): DNA + notes -> WAV, through the real machine.

    batch_render.py JOBS.json --host HOST --plugin BUNDLE [--parallel K] [--machine-dir DIR] [--out-dir DIR]

JOBS.json is a list of jobs:
    {"dna": "chord#10/ding>>E#6;A2D300S70R250",       the sound (DNA.md)
     "score": "0:60:100:1.0,1.2:64:90:0.5",           notes: t:note:velocity:duration (seconds) ...
     "midi": "phrase.mid",                            ... or a standard MIDI file (all tracks, all channels)
     "out": "chord_c4.wav",                           relative to --out-dir
     "tail": 2.0}                                     seconds after the last note ends (default 2)

HOST is tools/testhost's bsynth-host (bsynth-host.exe on Windows; from WSL it is run through cmd.exe). Every job
is its own host process with its own plugin instance, so its own QEMU and its own Windows XP: K jobs run side by
side. The machine renders in real time (the emulated sound card runs on the virtual clock). Jobs are rendered with the host
in offline mode: the plugin then waits for its machine to wake and for the sound to be built before the score
starts, so a job takes about 2-6 s plus its length; throughput is up to K times real time. The builds are not shown (BSYNTH_VISIBLE_BUILD=0), which is the
only difference from a DAW.

Output: 32-bit float stereo WAV at 48 kHz, one per job; a summary (seconds, peak, wall time) at the end, and
OUT_DIR/batch.json with the same.
"""
import argparse, concurrent.futures as cf, json, os, shutil, struct, subprocess, sys, time

WSL = 'microsoft' in open('/proc/version').read().lower() if os.path.exists('/proc/version') else False


def midi_score(path):
    """a standard MIDI file -> [(t, note, vel, dur)] in seconds (tempo map honoured, all tracks merged)"""
    d = open(path, 'rb').read()
    if d[:4] != b'MThd':
        raise ValueError('%s: not a MIDI file' % path)
    _, ntrk, div = struct.unpack('>HHH', d[8:14])
    p = 8 + struct.unpack('>I', d[4:8])[0]
    events = []                                     # (tick, kind, a, b)
    for _ in range(ntrk):
        ln = struct.unpack('>I', d[p + 4:p + 8])[0]
        q, end, tick, run = p + 8, p + 8 + ln, 0, 0
        p = end
        while q < end:
            v = 0
            while True:
                c = d[q]; q += 1
                v = (v << 7) | (c & 0x7f)
                if not c & 0x80:
                    break
            tick += v
            st = d[q]
            if st & 0x80:
                q += 1
                run = st if st < 0xf0 else run
            else:
                st = run
            if st == 0xff:
                typ = d[q]; q += 1
                n = 0
                while True:
                    c = d[q]; q += 1
                    n = (n << 7) | (c & 0x7f)
                    if not c & 0x80:
                        break
                if typ == 0x51:
                    events.append((tick, 'tempo', int.from_bytes(d[q:q + 3], 'big'), 0))
                q += n
            elif st in (0xf0, 0xf7):
                n = 0
                while True:
                    c = d[q]; q += 1
                    n = (n << 7) | (c & 0x7f)
                    if not c & 0x80:
                        break
                q += n
            else:
                hi = st & 0xf0
                if hi in (0xc0, 0xd0):
                    q += 1
                else:
                    a, b = d[q], d[q + 1]
                    q += 2
                    if hi == 0x90 and b:
                        events.append((tick, 'on', a, b))
                    elif hi == 0x80 or (hi == 0x90 and not b):
                        events.append((tick, 'off', a, 0))
    events.sort(key=lambda e: (e[0], e[1] != 'tempo', e[1] != 'off'))
    tempo, last_tick, t, held, notes = 500000, 0, 0.0, {}, []
    for tick, kind, a, b in events:
        t += (tick - last_tick) * tempo / 1e6 / div
        last_tick = tick
        if kind == 'tempo':
            tempo = a
        elif kind == 'on':
            held.setdefault(a, []).append((t, b))
        elif held.get(a):
            t0, vel = held[a].pop(0)
            notes.append((t0, a, vel, max(0.01, t - t0)))
    return sorted(notes)


def parse_score(s):
    out = []
    for it in s.split(','):
        t, n, v, du = it.split(':')
        out.append((float(t), int(n), int(v), float(du)))
    return out


def winpath(p):
    return subprocess.run(['wslpath', '-w', p], capture_output=True, text=True).stdout.strip() if WSL else p


def run_job(i, job, a):
    notes = midi_score(job['midi']) if job.get('midi') else parse_score(job['score'])
    score = ','.join('%.4f:%d:%d:%.4f' % n for n in notes)
    length = max(t + du for t, _, _, du in notes) if notes else 0
    tail = float(job.get('tail', 2.0))
    out = os.path.abspath(os.path.join(a.out_dir, job['out']))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    args = [a.plugin, out, '--offline', '--dna', job['dna'], '--score', score, '--warmup', str(a.warmup), '--tail', str(tail)]
    t0 = time.time()
    if WSL and a.host.lower().endswith('.exe'):
        # through a .bat: arguments with ';' and '#' do not survive WSL -> cmd.exe otherwise
        work = os.path.join(a.out_dir, '.batch')
        os.makedirs(work, exist_ok=True)
        bat = os.path.join(work, 'job%d.bat' % i)
        q = lambda s: '"%s"' % s
        with open(bat, 'w') as f:
            f.write('@echo off\r\nset BSYNTH_VISIBLE_BUILD=0\r\n')
            if a.machine_dir:
                f.write('set BSYNTH_MACHINE_DIR=%s\r\n' % winpath(a.machine_dir) if a.machine_dir.startswith('/') else 'set BSYNTH_MACHINE_DIR=%s\r\n' % a.machine_dir)
            f.write('%s %s %s %s\r\n' % (q(winpath(a.host)), q(winpath(a.plugin) if a.plugin.startswith('/') else a.plugin), q(winpath(out)),
                                          ' '.join(q(x.replace('%', '%%')) for x in args[2:])))
        r = subprocess.run(['cmd.exe', '/c', winpath(bat)], capture_output=True, text=True, cwd=work, timeout=a.timeout)
    else:
        env = dict(os.environ, BSYNTH_VISIBLE_BUILD='0')
        if a.machine_dir:
            env['BSYNTH_MACHINE_DIR'] = a.machine_dir
        r = subprocess.run([a.host] + args, capture_output=True, text=True, env=env, timeout=a.timeout)
    wall = time.time() - t0
    ok = os.path.exists(out) and os.path.getsize(out) > 44
    peak = None
    for ln in r.stdout.splitlines():
        if 'peak' in ln.lower():
            peak = ln.strip()
    return {'out': job['out'], 'ok': ok, 'notes': len(notes), 'seconds': round(length + tail, 2), 'wall': round(wall, 1),
            'peak': peak, 'log': r.stdout[-400:] if not ok else ''}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jobs')
    ap.add_argument('--host', required=True, help='bsynth-host (tools/testhost)')
    ap.add_argument('--plugin', required=True, help='BasiliskSynth.vst3')
    ap.add_argument('--parallel', type=int, default=max(1, min(6, (os.cpu_count() or 2) // 2)))
    ap.add_argument('--machine-dir', help='BSYNTH_MACHINE_DIR (default: the plugin\'s own)')
    ap.add_argument('--out-dir', default='.')
    ap.add_argument('--warmup', type=float, default=1, help='seconds of silence before the score (default 1; the render waits for the machine and the build by itself)')
    ap.add_argument('--timeout', type=float, default=900)
    a = ap.parse_args()
    jobs = json.load(open(a.jobs))
    base = os.path.dirname(os.path.abspath(a.jobs))
    for j in jobs:
        if j.get('midi') and not os.path.isabs(j['midi']):
            j['midi'] = os.path.join(base, j['midi'])
    os.makedirs(a.out_dir, exist_ok=True)
    t0 = time.time()
    res = []
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(run_job, i, j, a): j for i, j in enumerate(jobs)}
        for f in cf.as_completed(futs):
            r = f.result()
            res.append(r)
            print('%-40s %s  %5.1f s audio  %5.1f s wall' % (r['out'], 'ok  ' if r['ok'] else 'FAIL', r['seconds'], r['wall']), flush=True)
            if not r['ok']:
                print(r['log'])
    wall = time.time() - t0
    audio = sum(r['seconds'] for r in res if r['ok'])
    summary = {'jobs': len(jobs), 'ok': sum(r['ok'] for r in res), 'parallel': a.parallel, 'wall_s': round(wall, 1),
               'audio_s': round(audio, 1), 'audio_per_wall': round(audio / wall, 2) if wall else 0, 'results': res}
    json.dump(summary, open(os.path.join(a.out_dir, 'batch.json'), 'w'), indent=1)
    shutil.rmtree(os.path.join(a.out_dir, '.batch'), ignore_errors=True)
    print('%d/%d rendered, %.1f s of audio in %.1f s (%.2fx real time, %d VMs)' % (summary['ok'], len(jobs), audio, wall, summary['audio_per_wall'], a.parallel))
    sys.exit(0 if summary['ok'] == len(jobs) else 1)


if __name__ == '__main__':
    main()
