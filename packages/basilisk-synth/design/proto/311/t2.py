import rig, time, json, numpy as np
e = rig.start()
log = {}
try:
    rig.pr(e, 'hi 2', 'hi', 60)
    print(rig.pr(e, 'pr load 0 C:\\PE2\\SINE.WAV', 'pr load'))
    rec = rig.Rec(e); time.sleep(0.3)
    at = e.dac_w() + 4800
    s = rig.pr(e, 'pr splay 0 0 22050 1', 'pr splay', id=1, at=at); print(s); log['play'] = (at, s)
    time.sleep(0.3)
    v = rig.pr(e, 'pr voices', 'pr voices'); print(v)
    m = int(v.split()[2], 16); ch = (m & -m).bit_length() - 1; log['ch'] = ch
    sends = []
    def rate(val):
        d = e.dac_w(); s = rig.pr(e, 'pr rate %d %d' % (ch, val), 'pr rate'); sends.append((val, d, int(s.split(' at ')[1]), s))
    time.sleep(0.5); rate(98304)      # 1.5x
    time.sleep(0.5); rate(65536)
    time.sleep(0.5); rate(43691)      # 2/3
    time.sleep(0.5); rate(65536)
    time.sleep(0.4)
    for k in range(10):               # latency samples: alternate small changes
        rate(65536 + (k % 2) * 3277); time.sleep(0.07)
    rate(65536); time.sleep(0.3)
    d = e.dac_w(); g = rig.pr(e, 'pr glide %d 65536 131072 100 10' % ch, 'pr glide done', timeout=10); log['glide'] = (d, g); print(g)
    time.sleep(0.3)
    d = e.dac_w(); g = rig.pr(e, 'pr glide %d 131072 65536 100 10' % ch, 'pr glide done', timeout=10); log['glide2'] = (d, g); print(g)
    time.sleep(0.3)
    rate(0); time.sleep(0.3); rate(65536); time.sleep(0.2)
    rate(4096); time.sleep(0.3); rate(65536); time.sleep(0.2)
    rate(16 * 65536); time.sleep(0.05); rate(65536); time.sleep(0.2)
    log['texts'] = [t for t in e.texts if t.startswith('pr glide step')]
    rig.pr(e, 'pr stopall', 'pr stopall'); time.sleep(0.2)
    a = rec.stop(); log['base'] = rec.start; log['sends'] = sends
    np.save('/home/wm/pe2-311/work/t2.npy', a)
    rig.wav('/home/wm/pe2-evidence/311/t2_setrate_sine441.wav', a)
finally:
    e.close()
json.dump(log, open('/home/wm/pe2-evidence/311/t2_log.json', 'w'), indent=1)
for s in log['sends']: print(s[:3], s[2] - s[1])
