import rig, time, json, numpy as np
exec(open('t5.py').read().split("try:")[0])
try:
    rig.pr(e, 'hi 2', 'hi', 60)
    L0 = load(0, 'CLICK'); rig.pr(e, 'pr menu 0 20', 'pr menu'); L1 = menu(0, 25)
    x = cap(0, L1[0] * 22050 / 48000 + 0.1, 'pastemix_at0'); print('paste mix at 0: click value', x[218:223].round(4), 'len', L1[0])
    L0 = load(0, 'SINE'); rig.pr(e, 'pr menu 0 20', 'pr menu'); L1 = menu(0, 25)
    x = cap(0, 1.0, 'pastemix_sine_at0'); print('sine 0.5 paste-mixed onto itself: peak', np.abs(x[:40000]).max().round(4))
    L0 = load(0, 'SINE'); L1 = st(rig.pr(e, 'pr mixfile 0 C:\\PE2\\SINE.WAV', 'pr mixfile', timeout=60))
    x = cap(0, 1.0, 'mixfile_sine_at0'); print('sine 0.5 mixed with file of itself: peak', np.abs(x[:40000]).max().round(4))
    L0 = load(0, 'SINE'); L1 = menu(0, 37)
    x = cap(0, 8 * 22050 / 48000 + 0.1, 'echo_SINE'); s = np.load('/home/wm/pe2-311/work/SINE.WAV.npy') / 32768
    print('echo sine: len', L0[0], L1[0], 'peak', np.abs(x[:170000]).max().round(4), 'last 100 frames vs source ratio', (np.abs(x[176300:176400]).max() / np.abs(s[176300:176400]).max()).round(3))
finally: e.close()
