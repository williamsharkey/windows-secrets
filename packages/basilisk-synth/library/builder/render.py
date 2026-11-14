"""Render DNA + score through the real Windows 3.11 machine (render311, BASILISK 16 1.2.1), analyse each render
right away, and cache the analysis by (DNA, score, tail).

- Local: render311 under `nice -n 10`, K jobs at once (default 8 of this PC's 16 cores).
- Remote (optional, LIBBUILD_REMOTE=root@host): the same machine folder on sharkey-server, at most 4 jobs, niced.
- Every render311 we start is written to $LIBBUILD/run/render.pids (and removed when it exits), so our processes
  can be told apart from other lanes'.

A job: {"dna", "score": [(t, note, vel, dur)...], "tail", "kind", "keep": bool (keep the WAV), "tag"}.
"""
import concurrent.futures as cf, hashlib, json, os, subprocess, threading, time
import numpy as np
from common import WORK, MACHINE, RENDER311
import analyze

CACHE = os.path.join(WORK, 'feat')
WAVS = os.path.join(WORK, 'wav')
TMP = os.path.join(WORK, 'tmp')
RUN = os.path.join(WORK, 'run')
for d in (CACHE, WAVS, TMP, RUN): os.makedirs(d, exist_ok=True)
_pidlock = threading.Lock()
STATS = {'renders': 0, 'cached': 0, 'audio_s': 0.0, 'wall_s': 0.0, 'fail': 0}


def score_text(score):
    return ','.join('%.4f:%d:%d:%.4f' % tuple(n) for n in score)


def key_of(dna, score, tail, bpm=None):
    b = '|bpm%g' % bpm if bpm else ''
    return hashlib.sha1(('%s|%s|%.3f|v1%s' % (dna, score_text(score), tail, b)).encode()).hexdigest()[:20]


def _pids(add=None, rm=None):
    with _pidlock:
        p = os.path.join(RUN, 'render.pids')
        s = set(open(p).read().split()) if os.path.exists(p) else set()
        if add: s.add(str(add))
        if rm: s.discard(str(rm))
        open(p, 'w').write('\n'.join(sorted(s)) + '\n')


def run_render(dna, score, tail, out, bpm=None):
    args = ['nice', '-n', '10', RENDER311, '--machine', MACHINE, '--core', os.path.join(MACHINE, 'dosbox_pure_libretro.so'),
            '--dna', dna, '--score', score_text(score), '--out', out, '--tail', '%.3f' % tail, '--bits', '32'] + (['--bpm', '%g' % bpm] if bpm else [])
    t0 = time.time()
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _pids(add=p.pid)
    try:
        so, se = p.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        p.kill(); so, se = p.communicate()
    finally:
        _pids(rm=p.pid)
    return p.returncode, se.strip()[-300:], time.time() - t0


def job(j):
    k = key_of(j['dna'], j['score'], j['tail'], j.get('bpm'))
    cp = os.path.join(CACHE, k + '.json')
    wav = os.path.join(WAVS, k + '.wav')
    if os.path.exists(cp) and (not j.get('keep') or os.path.exists(wav)):
        r = json.load(open(cp)); r['cached'] = True; return r
    out = wav if j.get('keep') else os.path.join(TMP, k + '.wav')
    rc, log, wall = run_render(j['dna'], j['score'], j['tail'], out, j.get('bpm'))
    r = {'key': k, 'dna': j['dna'], 'kind': j.get('kind'), 'wall': round(wall, 2), 'log': log}
    if rc != 0 or not os.path.exists(out):
        r['ok'] = False
    else:
        try:
            r.update(analyze.analyze(out, j['score'], j['tail'], j.get('kind', 'keys'), j['dna'], j.get('singles')))
            r['ok'] = True
        except Exception as e:
            r['ok'] = False; r['err'] = repr(e)
        if not j.get('keep'):
            os.remove(out)
    if 'late notes' in log:
        try: r['late'] = int(log.split('late notes ')[1].split(' ')[0])
        except Exception: pass
    json.dump(r, open(cp, 'w'))
    r['cached'] = False
    return r


def render_all(jobs, parallel=8, progress=None):
    """-> results in job order"""
    res = [None] * len(jobs)
    t0 = time.time()
    with cf.ThreadPoolExecutor(parallel) as ex:
        futs = {ex.submit(job, j): i for i, j in enumerate(jobs)}
        done = 0
        for f in cf.as_completed(futs):
            i = futs[f]
            try:
                r = f.result()
            except Exception as e:
                r = {'ok': False, 'err': repr(e), 'dna': jobs[i]['dna']}
            res[i] = r
            done += 1
            if r.get('cached'): STATS['cached'] += 1
            else:
                STATS['renders'] += 1; STATS['audio_s'] += r.get('seconds', 0) or 0
                if not r.get('ok'): STATS['fail'] += 1
            if progress and done % 50 == 0:
                print('  %d/%d  %.0f s' % (done, len(jobs), time.time() - t0), flush=True)
    STATS['wall_s'] += time.time() - t0
    return res


def wav_path(dna, score, tail, bpm=None):
    return os.path.join(WAVS, key_of(dna, score, tail, bpm) + '.wav')
