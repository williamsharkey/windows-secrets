import rig, time, json, numpy as np
e = rig.start(); res = {}; nid = [5000]
def st(s):
    L = float(s.split(' L ')[1].split()[0]); P = s.split(' P ')[1].split(' L ')[0]; return L, P, s
def cap(r, secs, tag):
    rec = rig.Rec(e); time.sleep(0.1)
    at = e.dac_w() + 4800
    rig.pr(e, 'pr splay %d 0 48000 1' % r, 'pr splay', id=nid[0], at=at); nid[0] += 1
    time.sleep(secs + 0.4); a = rec.stop()
    x = a[at - rec.start:, 0].astype(np.float64)
    np.save('/home/wm/pe2-311/work/t5_%s.npy' % tag, x[:int(secs * 48000) + 4800])
    rig.wav('/home/wm/pe2-evidence/311/t5_%s_raw48k.wav' % tag, a[at - rec.start:])
    return x
def load(r, f): return st(rig.pr(e, 'pr load %d C:\\PE2\\%s.WAV' % (r, f), 'pr load'))
def menu(r, m): return st(rig.pr(e, 'pr menu %d %d' % (r, m), 'pr menu', timeout=60))
try:
    rig.pr(e, 'hi 2', 'hi', 60)
    # (a) echo
    for f, sr in (('CLICK', 22050), ('CLICK8', 22050), ('CLICK11', 11025)):
        L0 = load(0, f); L1 = menu(0, 37)
        x = cap(0, L1[0] * sr / 48000 + 0.1, 'echo_' + f)
        res['echo_' + f] = dict(before=L0, after=L1, sr=sr)
        print(f, 'len', L0[0], '->', L1[0])
    L0 = load(0, 'CLICK'); menu(0, 37); L2 = menu(0, 37); cap(0, L2[0] * 22050 / 48000 + 0.1, 'echo2_CLICK'); res['echo2_CLICK'] = dict(before=L0, after=L2, sr=22050)
    print('EE len', L2[0])
    # (b) lengths
    L0 = load(0, 'CLICK'); rig.pr(e, 'pr menu 0 20', 'pr menu'); s = st(rig.pr(e, 'pr seek 0 5000', 'pr seek')); L1 = menu(0, 25)
    cap(0, L1[0] * 22050 / 48000 + 0.1, 'pastemix_at50'); res['pastemix_at50'] = dict(before=L0, seek=s, after=L1, sr=22050); print('paste mix at 50%:', L0[0], '->', L1[0], s[1])
    L0 = load(0, 'CLICK'); rig.pr(e, 'pr menu 0 20', 'pr menu'); L1 = menu(0, 25)
    res['pastemix_at0'] = dict(before=L0, after=L1); print('paste mix at 0:', L0[0], '->', L1[0])
    L0 = load(0, 'CLICK'); s = st(rig.pr(e, 'pr seek 0 5000', 'pr seek')); L1 = st(rig.pr(e, 'pr mixfile 0 C:\\PE2\\CLICK.WAV', 'pr mixfile', timeout=60))
    cap(0, L1[0] * 22050 / 48000 + 0.1, 'mixfile_at50'); res['mixfile_at50'] = dict(before=L0, seek=s, after=L1, sr=22050); print('mix file at 50%:', L0[0], '->', L1[0])
    L0 = load(0, 'CLICK'); L1 = st(rig.pr(e, 'pr mixfile 0 C:\\PE2\\NOIS8.WAV', 'pr mixfile', timeout=60))
    res['mixfile_longer_at0'] = dict(before=L0, after=L1); print('mix 8 s file into 2 s at 0:', L0[0], '->', L1[0])
    L0 = load(0, 'NOIS8'); L1 = st(rig.pr(e, 'pr mixfile 0 C:\\PE2\\CLICK.WAV', 'pr mixfile', timeout=60))
    res['mixfile_shorter_at0'] = dict(before=L0, after=L1); print('mix 2 s file into 8 s at 0:', L0[0], '->', L1[0])
    # (c) speed round trips
    for f in ('STEPS', 'NOISE4'):
        L0 = load(0, f); cap(0, L0[0] * 22050 / 48000 + 0.1, 'ref_' + f)
        for order, ms in (('slow_fast', (36, 35)), ('fast_slow', (35, 36))):
            L0 = load(0, f); La = menu(0, ms[0]); Lb = menu(0, ms[1])
            cap(0, Lb[0] * 22050 / 48000 + 0.1, '%s_%s' % (order, f))
            res['%s_%s' % (order, f)] = dict(before=L0, mid=La, after=Lb); print(f, order, L0[0], La[0], Lb[0])
        L0 = load(0, f); La = menu(0, 35); cap(0, La[0] * 22050 / 48000 + 0.1, 'fast_' + f); res['fast_' + f] = dict(before=L0, after=La)
        L0 = load(0, f); La = menu(0, 36); cap(0, La[0] * 22050 / 48000 + 0.1, 'slow_' + f); res['slow_' + f] = dict(before=L0, after=La)
finally: e.close()
json.dump(res, open('/home/wm/pe2-evidence/311/t5_results.json', 'w'), indent=1)
