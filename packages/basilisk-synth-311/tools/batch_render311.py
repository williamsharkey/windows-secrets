#!/usr/bin/env python3
"""Batch rendering for BASILISK 16 (DNA.md 5.6): DNA + notes -> WAV through the real Windows 3.11 machine.

    batch_render311.py JOBS.json --machine DIR [--core FILE] [--render311 EXE] [--parallel K] [--out-dir DIR]

JOBS.json is the same list as packages/basilisk-synth/tools/batch_render.py takes:
    {"dna": "piano_upright_cs4#16T-1;R400",           the sound (DNA.md; library NAMEs from DIR/library.names.txt)
     "score": "0:60:100:1.0,1.2:64:90:0.5",           notes: t:note:velocity:duration (seconds) ...
     "midi": "phrase.mid",                            ... or a standard MIDI file
     "out": "piano_c4.wav",                           relative to --out-dir
     "tail": 2.0}                                     seconds after the last note ends (default 2)

Each job is one render311 process: its own emulator, resumed from the machine's snapshot, Sound Recorder builds the
DNA (no assembly animation), and the notes play through the recorders exactly as the plugin plays them offline.
The emulated card is not paced by a clock here, so a job runs faster than real time (about 7-8x on one core,
plus about 0.5-2 s to resume and build), and K jobs run side by side.

DIR: a machine folder (w31.conf, w31.state, drive.zip, library.zip, library.names.txt): the plugin bundle's
Contents/Resources/machine, or tools/build.sh's WORKDIR/machine. --core: the DOSBox Pure core with the BSYN card
(default: DIR/dosbox_pure_libretro.{dll,so,dylib}). --render311: tools/render311.cpp built for this OS (see README).
Output: 32-bit float stereo WAV at 48 kHz per job, and OUT_DIR/batch.json (seconds, peak, wall time per job).
"""
import argparse, array, concurrent.futures as cf, json, os, subprocess, sys, time


def parse_score(s):
    out = []
    for it in s.split(','):
        t, n, v, du = it.split(':')
        out.append((float(t), int(n), int(v), float(du)))
    return out


def peak_of(path):
    try:
        with open(path, 'rb') as f:
            d = f.read()
        i = d.find(b'data')
        a = array.array('f'); a.frombytes(d[i + 8:i + 8 + (len(d) - i - 8) // 4 * 4])
        return max((abs(x) for x in a), default=0.0)
    except Exception:
        return None


def run_job(i, job, a):
    out = os.path.abspath(os.path.join(a.out_dir, job['out']))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tail = float(job.get('tail', 2.0))
    args = [a.render311, '--machine', a.machine, '--core', a.core, '--dna', job['dna'], '--out', out, '--tail', str(tail), '--bits', '32']
    if job.get('midi'):
        args += ['--midi', job['midi']]; length = None
    else:
        notes = parse_score(job['score'])
        args += ['--score', ','.join('%.4f:%d:%d:%.4f' % n for n in notes)]
        length = max(t + du for t, _, _, du in notes) if notes else 0
    t0 = time.time()
    r = subprocess.run(args, capture_output=True, text=True, timeout=a.timeout)
    wall = time.time() - t0
    ok = r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 44
    secs = None
    if ok:
        with open(out, 'rb') as f:
            d = f.read()
        secs = (len(d) - d.find(b'data') - 8) / 8 / 48000
    return {'out': job['out'], 'ok': ok, 'seconds': round(secs, 2) if secs else (round(length + tail, 2) if length is not None else None),
            'wall': round(wall, 2), 'peak': round(peak_of(out), 4) if ok else None, 'log': r.stderr.strip()[-400:]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jobs')
    ap.add_argument('--machine', required=True)
    ap.add_argument('--core')
    ap.add_argument('--render311', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render311' + ('.exe' if os.name == 'nt' else '')))
    ap.add_argument('--parallel', type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument('--out-dir', default='.')
    ap.add_argument('--timeout', type=float, default=600)
    a = ap.parse_args()
    a.machine = os.path.abspath(a.machine)
    if not a.core:
        for n in ('dosbox_pure_libretro.dll', 'dosbox_pure_libretro.dylib', 'dosbox_pure_libretro.so'):
            if os.path.exists(os.path.join(a.machine, n)) and (n.endswith('.dll') == (os.name == 'nt')):
                a.core = os.path.join(a.machine, n)
        if not a.core: sys.exit('batch_render311: no core for this OS in %s (give --core)' % a.machine)
    jobs = json.load(open(a.jobs))
    base = os.path.dirname(os.path.abspath(a.jobs))
    for j in jobs:
        if j.get('midi') and not os.path.isabs(j['midi']): j['midi'] = os.path.join(base, j['midi'])
    os.makedirs(a.out_dir, exist_ok=True)
    t0 = time.time(); res = []
    with cf.ThreadPoolExecutor(a.parallel) as ex:
        for f in cf.as_completed([ex.submit(run_job, i, j, a) for i, j in enumerate(jobs)]):
            r = f.result(); res.append(r)
            print('%-40s %s  %6.2f s audio  %5.2f s wall  peak %s' % (r['out'], 'ok  ' if r['ok'] else 'FAIL', r['seconds'] or 0, r['wall'], r['peak']), flush=True)
            if not r['ok']: print(r['log'])
    wall = time.time() - t0
    audio = sum(r['seconds'] or 0 for r in res if r['ok'])
    summary = {'jobs': len(jobs), 'ok': sum(r['ok'] for r in res), 'parallel': a.parallel, 'wall_s': round(wall, 2),
               'audio_s': round(audio, 2), 'audio_per_wall': round(audio / wall, 2) if wall else 0, 'results': res}
    json.dump(summary, open(os.path.join(a.out_dir, 'batch.json'), 'w'), indent=1)
    print('%d/%d rendered, %.1f s of audio in %.1f s (%.1fx real time, %d at once)' % (summary['ok'], len(jobs), audio, wall, summary['audio_per_wall'], a.parallel))
    sys.exit(0 if summary['ok'] == len(jobs) else 1)


if __name__ == '__main__':
    main()
