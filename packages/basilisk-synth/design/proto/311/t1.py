import rig, time, json, numpy as np
e = rig.start()
res = {}
try:
    rig.pr(e, 'hi 2', 'hi', 60)
    nid = 100
    for f, N in (('NOIS1', 22050), ('NOIS8', 8 * 22050)):
        src = np.load('/home/wm/pe2-311/work/%s.WAV.npy' % f).astype(np.float64) / 32768
        print(rig.pr(e, 'pr load 0 C:\\PE2\\%s.WAV' % f, 'pr load'))
        rng = np.random.default_rng(7)
        poss = [0, 1, 2, 3, 5, 7, 10, 13, 50, 100, 101, 1234, 2500, 3333, 5000, 6789, 7500, 9000, 9876, 9990] + list(rng.integers(0, 9950, 20))
        rec = rig.Rec(e); time.sleep(0.2)
        plays = []
        for p in poss:
            at = e.dac_w() + 4800
            s = rig.pr(e, 'pr splay 0 %d 48000' % p, 'pr splay', id=nid, at=at); nid += 1
            plays.append((int(p), at, s)); time.sleep(0.25)
        rig.pr(e, 'pr stopall', 'pr stopall'); time.sleep(0.2)
        a = rec.stop(); base = rec.start
        rig.wav('/home/wm/pe2-evidence/311/t1_%s_seekplay.wav' % f, a)
        out = []
        for p, at, s in plays:
            i = at - base; seg = a[i:i + 256, 0].astype(np.float64)
            pre = a[i - 50:i, 0]
            # find offset: exact match search
            c = np.correlate(src, seg, 'valid'); off = int(np.argmax(c))
            err = np.max(np.abs(src[off:off + 256] - seg))
            want = p / 10000 * N
            gotpos = int(s.split(' got ')[1].split()[0]); ptxt = s.split(' P ')[1].split(' d0')[0]
            # onset: first nonzero sample around at
            nz = np.nonzero(np.abs(a[i - 2000:i + 4800, 0]) > 1e-6)[0]
            onset = (nz[0] - 2000) if len(nz) else None
            out.append(dict(pos=p, scrollpos=gotpos, ptxt=ptxt, want_frames=want, got_frame=off, err_frames=off - want,
                            err_ms=(off - want) / 22.05, match=float(err), onset_vs_at=int(onset) if onset is not None else None, line=s))
            print(p, gotpos, ptxt, round(want, 1), off, round((off - want) / 22.05, 3), 'match %.2g' % err, 'onset', onset)
        res[f] = out
finally:
    e.close()
json.dump(res, open('/home/wm/pe2-evidence/311/t1_results.json', 'w'), indent=1)
