#!/usr/bin/env python3
"""The baseline: every lane of an mtrender job rendered by its own emulator (render311, the Song tab's 1.4 design),
K at a time; then each lane's stem compared with mtrender's.
  sep_render.py JOB RENDER311 MACHINE OUTDIR [--parallel K] [--compare MTDIR] [--lookahead MS]"""
import os, sys, subprocess, time, resource, concurrent.futures as cf
import numpy as np
job, r311, machine, out = sys.argv[1:5]
opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
K = int(opt('--parallel', 4)); cmpdir = opt('--compare', None); look = opt('--lookahead', '150')
os.makedirs(out, exist_ok=True)
bpm, tail, lanes = 120.0, 3.0, []
for l in open(job):
    if l.startswith('bpm '): bpm = float(l[4:])
    elif l.startswith('tail '): tail = float(l[5:])
    elif l.startswith('lane '):
        mid, dna = l[5:].rstrip('\n').split(' ', 1); lanes.append((mid, dna))
def run(k):
    mid, dna = lanes[k]; t = time.time()
    r = subprocess.run(['nice', '-n', '10', r311, '--machine', machine, '--core', os.path.join(machine, 'dosbox_pure_libretro.so'), '--dna', dna,
                        '--midi', mid, '--out', os.path.join(out, 'lane%d.wav' % k), '--bits', '32', '--bpm', '%.6f' % bpm, '--tail', '%g' % tail,
                        '--lookahead', look], capture_output=True, text=True)
    return k, time.time() - t, (r.stderr.strip().splitlines() or ['?'])[-1]
t0 = time.time()
with cf.ThreadPoolExecutor(K) as ex:
    for k, w, msg in ex.map(run, range(len(lanes))): print('lane %d: %.1f s wall: %s' % (k, w, msg), flush=True)
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
print('separate: %d lanes, %d at once: %.1f s wall, %.1f s cpu (user %.1f sys %.1f), max RSS of one %d MB' % (
    len(lanes), K, time.time() - t0, ru.ru_utime + ru.ru_stime, ru.ru_utime, ru.ru_stime, ru.ru_maxrss // 1024))
def rd(p):
    d = open(p, 'rb').read(); return np.frombuffer(d[44:], '<f4').reshape(-1, 2)
if cmpdir:
    for k in range(len(lanes)):
        a, b = rd(os.path.join(out, 'lane%d.wav' % k)), rd(os.path.join(cmpdir, 'lane%d.wav' % k))
        n = min(len(a), len(b)); d = np.abs(a[:n] - b[:n]); rms = np.sqrt((a[:n] ** 2).mean()) + 1e-12
        same = int((a[:n] == b[:n]).all(axis=1).sum())
        print('lane %d: %d vs %d frames; identical frames %.4f%%; max diff %.3g (%.1f dBFS); diff rms / signal rms %.2e; first diff at %s' % (
            k, len(a), len(b), 100.0 * same / n, d.max(), 20 * np.log10(d.max() + 1e-12), np.sqrt((d ** 2).mean()) / rms,
            ('%.4f s' % (np.argmax(d.max(axis=1) > 0) / 48000)) if d.max() > 0 else '-'))
