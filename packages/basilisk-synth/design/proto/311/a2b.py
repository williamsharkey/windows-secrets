import json, numpy as np
from plot import plot
a = np.load('/home/wm/pe2-311/work/t2.npy')[:, 0].astype(float)
L = json.load(open('/home/wm/pe2-evidence/311/t2_log.json')); base = L['base']
# zero crossings (rising), linear interp
s = np.sign(a); idx = np.nonzero((s[:-1] <= 0) & (s[1:] > 0))[0]
tz = idx + (-a[idx]) / (a[idx + 1] - a[idx] + 1e-30)
per = np.diff(tz); fz = 48000 / per; tm = tz[1:]
env = np.sqrt(np.convolve(a**2, np.ones(480)/480, 'same'))
print('signal active until sample', np.nonzero(env > 0.1)[0][-1], 'of', len(a))
for key in ('glide', 'glide2'):
    d, g = L[key]; d0 = int(g.split('d0 ')[1].split()[0]); d1 = int(g.split('d1 ')[1]); i0 = d0 - base; i1 = d1 - base
    m = (tm > i0 - 2400) & (tm < i1 + 2400)
    T, F = tm[m], fz[m]
    # detect step edges: per-period freq jumps
    np.savetxt('/home/wm/pe2-evidence/311/t2_%s_zc.txt' % key, np.stack([(T - i0) / 48, F], 1), fmt='%.3f', header='ms from glide start, freq Hz per period (zero crossings)')
    jumps = np.abs(np.diff(F)); within = np.median(jumps)
    print(key, 'periods', len(F), 'median per-period change %.3f Hz, max %.2f Hz; first/last freq %.1f %.1f' % (within, jumps.max(), F[:5].mean(), F[-5:].mean()))
    print('  env during glide min/max', env[i0:i1].min().round(3), env[i0:i1].max().round(3))

plot('/home/wm/pe2-evidence/311/t2_setrate.png', [(tm / 48000, fz, 'dot')], 'BSC_SETRATE on a sounding 441 Hz voice: Hz per period vs s (red: guest SETRATE writes)', ylim=(0, 1000), vlines=[(x[2] - base) / 48000 for x in L['sends']])
val, dh, dg, s_ = L['sends'][0]; i = dg - base
plot('/home/wm/pe2-evidence/311/t2_step15_zoom.png', [(np.arange(-480, 480) / 48.0, a[i - 480:i + 480])], '1.5x SETRATE at 0 ms (the guest write): DAC samples vs ms', vlines=[0])
d, g = L['glide']; d0 = int(g.split('d0 ')[1].split()[0]); i0 = d0 - base
m = (tm > i0 - 2400) & (tm < i0 + 48000 + 2400)
plot('/home/wm/pe2-evidence/311/t2_glide.png', [((tm[m] - i0) / 48, fz[m], 'dot')], 'glide 441 -> 882 Hz, 100 SETRATE steps of 10 ms: Hz per period vs ms')
