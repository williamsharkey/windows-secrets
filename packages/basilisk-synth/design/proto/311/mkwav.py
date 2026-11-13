import numpy as np, wave, sys
D='/home/wm/pe2-311/m/drive/PE2/'
def w(name, x, rate=22050):
    x = np.clip(np.round(x * 32767), -32768, 32767).astype('<i2')
    with wave.open(D + name, 'wb') as f: f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate); f.writeframes(x.tobytes())
    np.save('/home/wm/pe2-311/work/' + name + '.npy', x)
R=22050
rng = np.random.default_rng(1)
w('NOIS1.WAV', rng.uniform(-.5, .5, R))
w('NOIS8.WAV', rng.uniform(-.5, .5, 8 * R))
t = np.arange(8 * R) / R
w('SINE.WAV', 0.5 * np.sin(2 * np.pi * 441 * t))
c = np.zeros(2 * R); c[220] = 0.9; w('CLICK.WAV', c)
w('NOISE4.WAV', rng.uniform(-.5, .5, 4 * R))
# stepped sines: 48 log-spaced tones 100..10900 Hz, 100 ms each, 20 ms gaps
fs = np.geomspace(100, 10900, 48); seg = []
for f in fs:
    n = int(0.1 * R); tt = np.arange(n) / R; win = np.hanning(n)
    seg.append(0.5 * np.sin(2 * np.pi * f * tt) * np.minimum(1, 8 * win)); seg.append(np.zeros(int(0.02 * R)))
w('STEPS.WAV', np.concatenate(seg)); np.save('/home/wm/pe2-311/work/steps_f.npy', fs)
