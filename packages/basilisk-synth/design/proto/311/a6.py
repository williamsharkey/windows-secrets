import json, numpy as np
d = json.load(open('/home/wm/pe2-evidence/311/t6_rates.json')); a = np.load('/home/wm/pe2-311/work/t6c.npy'); base = d['base']
pk = np.nonzero((a[1:-1] > 0.3) & (a[1:-1] >= a[:-2]) & (a[1:-1] > a[2:]))[0] + 1
print('impulses', len(pk), 'max', a.max())
summ = {}
for key, r in d['tb'].items():
    rows = r['rows']; d0 = np.array([x[0] for x in rows]) - base; pd = np.array([x[1] for x in rows]) / 48
    T = r['T']; nrec = r['nrec']
    lo, hi = d0[0], d0[-1] + 48000
    P = pk[(pk >= lo) & (pk < hi)] - 220
    used = np.zeros(len(P), bool); lat = []
    for i, x in enumerate(d0):
        nxt = d0[i + nrec] if i + nrec < len(d0) else x + 48000   # the same recorder's next play stops this one
        c = np.nonzero(~used & (P >= x) & (P < nxt))[0]
        if len(c): used[c[0]] = True; lat.append((P[c[0]] - x) / 48)
        else: lat.append(np.nan)
    lat = np.array(lat); ok = ~np.isnan(lat)
    span = (d0[-1] - d0[0]) / 48 / (len(d0) - 1)
    summ[key] = dict(nrec=nrec, T_ms=T, plays=len(d0), sounded=int(ok.sum()), actual_interval_ms=round(span, 2), plays_per_s=round(1000 / span, 1),
                     press_ms_med=float(np.median(pd)), press_ms_max=float(pd.max()),
                     play_to_sound_ms=dict(min=float(np.nanmin(lat)) if ok.any() else None, med=float(np.nanmedian(lat)) if ok.any() else None, p90=float(np.nanpercentile(lat, 90)) if ok.any() else None, max=float(np.nanmax(lat)) if ok.any() else None))
    s = summ[key]; q = s['play_to_sound_ms']
    print('%2d rec T %3d ms: %d plays, %d sounded, actual interval %.1f ms (%.0f/s); press %.1f/%.1f ms (med/max); Play->sound ms min %s med %s p90 %s max %s' % (
        nrec, T, len(d0), ok.sum(), span, 1000 / span, s['press_ms_med'], s['press_ms_max'], *[('%.1f' % q[k]) if q[k] is not None else '-' for k in ('min', 'med', 'p90', 'max')]))
json.dump(summ, open('/home/wm/pe2-evidence/311/t6_tburst_summary.json', 'w'), indent=1)
