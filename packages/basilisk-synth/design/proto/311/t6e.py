import rig, time, json, numpy as np
e = rig.start(); out = {}
try:
    rig.pr(e, 'hi 2', 'hi', 60); rig.pr(e, 'go', 'ready', 60); time.sleep(1)
    for r in range(16): rig.pr(e, 'pr load %d C:\\PE2\\CLICK.WAV' % r, 'pr load')
    rec = rig.Rec(e); time.sleep(0.3)
    nid = 1000
    for nrec in (1, 16):
        for B in (2560, 1280):
            for rate in (25, 50, 100, 150, 200, 300):
                t0 = time.time(); k = 0; ats = []
                while time.time() - t0 < 1.5:
                    at = e.dac_w() + B; e.line('on %d 48000 65535' % (k % nrec), id=nid, at=at); ats.append(at); nid += 1; k += 1
                    nxt = t0 + k / rate
                    while time.time() < nxt: e.poll(); time.sleep(0.0005)
                time.sleep(0.5); e.poll()
                out['%d_%d_%d' % (nrec, B, rate)] = ats
                e.line('panic'); time.sleep(0.5)
    a = rec.stop(); base = rec.start
    np.save('/home/wm/pe2-311/work/t6e.npy', a[:, 0])
finally: e.close()
x = a[:, 0]; pk = np.nonzero((x[1:-1] > 0.3) & (x[1:-1] >= x[:-2]) & (x[1:-1] > x[2:]))[0] + 1 + base - 220
res = {}
for key, ats in out.items():
    nrec, B, rate = map(int, key.split('_')); ats = np.array(ats)
    lat = []
    for i, at in enumerate(ats):
        nxt = ats[i + nrec] if i + nrec < len(ats) else at + 96000
        c = pk[(pk >= at - 2) & (pk < max(nxt, at) + 96000)]
        lat.append((c[0] - at) / 48 if len(c) else np.nan)
    lat = np.array(lat); ok = ~np.isnan(lat)
    exact = np.sum(np.abs(lat[ok]) < 0.05)
    res[key] = dict(nrec=nrec, budget_ms=B / 48, rate=rate, sent=len(ats), heard=int(ok.sum()), exact=int(exact), late_ms_p50=float(np.nanmedian(lat)), late_ms_p90=float(np.nanpercentile(lat, 90)), late_ms_max=float(np.nanmax(lat)))
    r = res[key]
    print('nrec %2d budget %.1f ms rate %3d/s: sent %d heard %d sample-exact %d; onset-at ms p50 %.2f p90 %.2f max %.2f' % (nrec, B / 48, rate, len(ats), ok.sum(), exact, r['late_ms_p50'], r['late_ms_p90'], r['late_ms_max']))
json.dump(res, open('/home/wm/pe2-evidence/311/t6_hostpath_assembled.json', 'w'), indent=1)
