import rig, time, json, numpy as np
e = rig.start(); out = {}
try:
    rig.pr(e, 'hi 2', 'hi', 60)
    rec = rig.Rec(e); time.sleep(0.2)
    for name, r0, nrec, n in (('one', 0, 1, 100), ('sixteen', 0, 16, 320)):
        n0 = len(e.texts)
        s = rig.pr(e, 'pr burst %d %d %d 22050' % (r0, nrec, n), 'pr burst total', timeout=120)
        time.sleep(0.5); e.poll()
        rows = []
        for t in e.texts[n0:]:
            if t.startswith('pr bms'):
                for tok in t.split()[3:]:
                    ms, d = tok.split(':'); rows.append((int(ms), int(d)))
        tot = int(s.split('total ')[1].split()[0])
        ms = np.array([r[0] for r in rows]); dd = np.array([r[1] for r in rows])
        gaps = np.diff(dd) / 48.0
        out[name] = dict(total_ms=tot, n=n, plays_per_s=n / max(tot,1) * 1000, per_play_ms=ms.tolist(), dac=dd.tolist())
        print(name, s, 'plays/s %.1f' % (n / max(tot,1) * 1000), 'per-play ms: median %d p90 %d max %d' % (np.median(ms), np.percentile(ms, 90), ms.max()),
              'DAC gap ms: median %.1f p10 %.1f p90 %.1f max %.1f' % (np.median(gaps), np.percentile(gaps, 10), np.percentile(gaps, 90), gaps.max()))
        rig.pr(e, 'pr stopall', 'pr stopall'); time.sleep(0.5)
    a = rec.stop(); out['base'] = rec.start
    np.save('/home/wm/pe2-311/work/t6.npy', a)
    rig.wav('/home/wm/pe2-evidence/311/t6_burst.wav', a)
    out['logs'] = [t for t in e.texts if t.startswith('log')]
finally: e.close()
json.dump(out, open('/home/wm/pe2-evidence/311/t6_burst.json', 'w'))
