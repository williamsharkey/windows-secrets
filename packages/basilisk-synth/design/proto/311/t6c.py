import rig, time, json, numpy as np
e = rig.start(); out = {'tb': {}, 'host': {}}
def stats(): return e.u32('sched_ontime'), e.u32('sched_late'), e.u32('sched_latemax')
try:
    rig.pr(e, 'hi 2', 'hi', 60)
    for r in range(16): rig.pr(e, 'pr load %d C:\\PE2\\CLICK.WAV' % r, 'pr load')
    rec = rig.Rec(e); time.sleep(0.3)
    runs = [(1, T, 30) for T in (100, 50, 30, 20, 15, 10, 7, 5, 3)] + [(16, T, 64) for T in (50, 20, 10, 7, 5, 3, 1)]
    for nrec, T, n in runs:
        n0 = len(e.texts)
        s = rig.pr(e, 'pr tburst 0 %d %d 48000 %d' % (nrec, n, T), 'pr tburst total', timeout=120); time.sleep(0.3); e.poll()
        rows = [tuple(map(int, tok.split(':'))) for t in e.texts[n0:] if t.startswith('pr tb ') for tok in t.split()[3:]]
        out['tb']['%d_%d' % (nrec, T)] = dict(n=n, T=T, nrec=nrec, total=s, rows=rows)
        rig.pr(e, 'pr stopall', 'pr stopall'); time.sleep(2.2)
    nid = 1000
    for nrec in (1, 16):
        for B in (2560, 1280):
            for rate in (10, 25, 50, 100, 200):
                s0 = stats(); n0 = len(e.texts); t0 = time.time(); k = 0
                while time.time() - t0 < 2.0:
                    e.line('on %d 22050 40000' % (k % nrec), id=nid, at=e.dac_w() + B); nid += 1; k += 1
                    nxt = t0 + k / rate
                    while time.time() < nxt: e.poll(); time.sleep(0.001)
                time.sleep(0.4); e.poll(); s1 = stats()
                slow = [t for t in e.texts[n0:] if 'slow play' in t]
                d = dict(sent=k, ontime=s1[0] - s0[0], late=s1[1] - s0[1], latemax_cum=s1[2], slow_logs=len(slow), slow=slow[:4])
                out['host']['%d_%d_%d' % (nrec, B, rate)] = d
                print('host nrec %2d budget %.1f ms rate %3d/s: sent %d ontime %d late %d latemax(cum) %.1f ms slow %d' % (nrec, B / 48, rate, k, d['ontime'], d['late'], s1[2] / 48, len(slow)), slow[:2])
                e.line('panic'); time.sleep(0.6)
    a = rec.stop(); out['base'] = rec.start
    np.save('/home/wm/pe2-311/work/t6c.npy', a[:, 0])
finally: e.close()
json.dump(out, open('/home/wm/pe2-evidence/311/t6_rates.json', 'w'))
