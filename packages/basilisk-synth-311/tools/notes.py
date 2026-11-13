"""Test rig (Linux/macOS): CONF = a machine conf with paths filled in; CORE optional (tools/bsdrv.py). See README."""
import sys, time, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsdrv import *
import numpy as np
from align import expected, lag
e = Engine(os.environ['CONF'])
def peakhz(x, rate=48000):
    x = x[:, 0] * np.hanning(len(x)); n = 1 << 20
    s = np.abs(np.fft.rfft(x, n)); f = np.argmax(s[100:]) + 100
    return f * rate / n
try:
    e.wait_packet(2, 90)
    e.line('hi 1'); e.wait_text('hi 1 311', 10)
    e.line('go'); e.wait_text('ready', 20)
    t = time.time(); e.line('dna ding#16;R120'); e.wait_text('built', 60); print('build took', time.time() - t)
    e.line('env 0 0 100 120')
    # three notes 0.5 s apart, scheduled 150 ms ahead
    base = e.dac_w() + 7200
    plan = [(0, 22050, base), (1, 44100, base + 24000), (2, 11025, base + 48000)]
    for i, (rec, hz, at) in enumerate(plan):
        e.line('on %d %d 65535' % (rec, hz), id=100 + i, at=at)
    start, a = e.record(2.5)
    e.poll()
    wav('/tmp/notes.wav', a)
    for rec, hz, at in plan:
        i0 = at - start
        exp = expected(os.environ['DING_WAV'], hz)
        d, c = lag(a[i0 - 3000:i0 + 20000, 0], exp)
        print('rec', rec, 'hz', hz, 'timing error', d - 3000, 'samples, corr', round(c, 4), 'peak', round(peakhz(a[i0:i0 + 10000]), 1))
    e.shot('/tmp/notes.png')
finally:
    e.close()
