import rig, time, json, numpy as np
e = rig.start(); log = {}
try:
    rig.pr(e, 'hi 2', 'hi', 60)
    rig.pr(e, 'pr load 0 C:\\PE2\\SINE.WAV', 'pr load')
    rec = rig.Rec(e); time.sleep(0.2)
    rig.pr(e, 'pr splay 0 0 22050 1', 'pr splay', id=1, at=e.dac_w() + 4800); time.sleep(0.3)
    v = rig.pr(e, 'pr voices', 'pr voices'); m = int(v.split()[2], 16); ch = (m & -m).bit_length() - 1
    sends = []
    for val, hold in ((16 * 65536, 0.1), (65536, 0.2), (int(10.9 * 65536), 0.1), (65536, 0.2), (40 * 65536, 0.03), (65536, 0.2), (1, 0.2), (65536, 0.2), (0xFFFFFFFF, 0.02), (65536, 0.2)):
        s = rig.pr(e, 'pr rate %d %d' % (ch, val), 'pr rate'); sends.append((val, int(s.split(' at ')[1]))); time.sleep(hold)
    rig.pr(e, 'pr stopall', 'pr stopall'); time.sleep(0.1)
    a = rec.stop(); base = rec.start
    rig.wav('/home/wm/pe2-evidence/311/t2b_rate_limits.wav', a)
finally: e.close()
x = a[:, 0].astype(float)
for k, (val, d) in enumerate(sends):
    i = d - base + 96; j = (sends[k + 1][1] - base) if k + 1 < len(sends) else len(x)
    seg = x[i:j - 48]
    if len(seg) < 64: print(val, 'short'); continue
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))); fr = np.fft.rfftfreq(len(seg), 1 / 48000)
    print('rate %.6g: dur %d samples, peak %.0f Hz (expect %.0f), rms %.3f' % (val / 65536, len(seg), fr[np.argmax(sp)], 441 * val / 65536, np.sqrt(np.mean(seg ** 2))))
