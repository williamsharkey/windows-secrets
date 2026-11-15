#!/usr/bin/env python3
"""Smoke test of MTSYNTH.EXE: boot, build a DNA on two lanes, play a note on each, measure the DAC."""
import os, sys, time, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import bsdrv
from bsdrv import Engine
import numpy as np
conf, core = sys.argv[1:3]
e = Engine(conf, core=core, log=os.path.expanduser('~/mtw/smoke.log'), name='mtsmoke%d' % os.getpid())
e.u32('vid_want', 1); e.u32('offline', 1)
def grant(n):   # run n more DAC samples
    struct.pack_into('<Q', e.m, bsdrv.OFF['grant_until'], e.dac_w() + n)
def run(sec):
    tgt = e.dac_w() + int(sec * 48000); grant(int(sec * 48000))
    while e.dac_w() < tgt: e.poll(); time.sleep(0.002)
try:
    t0 = time.time()
    while not any('mt ready' in s for s in e.texts):
        grant(48000); time.sleep(0.01); e.poll()
        if time.time() - t0 > 60: e.shot(os.path.expanduser('~/mtw/stall.png')); print('stalled; dac %.1f s' % (e.dac_w() / 48000)); raise SystemExit(1)
    print('ready %.1f s wall' % (time.time() - t0))
    e.line('@0 q 0'); run(0.1)
    dnas = sys.argv[3].split('|') if len(sys.argv) > 3 else ['chimes', 'tada#4/ding']
    for ln, dna in enumerate(dnas):
        e.line('@%d dna %s' % (ln, dna)); tb = time.time()
        while not any(s.startswith('@%d built' % ln) for s in e.texts):
            run(0.2)
            if time.time() - tb > 30: e.shot(os.path.expanduser('~/mtw/stall.png')); raise SystemExit('build stalled')
        e.line('@%d q 0' % ln); run(0.1)
    e.line('@0 env 0 0 100 120'); e.line('@1 env 0 0 100 120')
    run(0.1)
    d0 = e.dac_w()
    e.line('@0 on 0 22050 65535', id=1, at=d0 + 9600)
    e.line('@1 on 0 22050 65535', id=2, at=d0 + 48000)
    run(2.0)
    a = e.read(d0, 2 * 48000)
    for k in range(8): print('  %.2f s rms %.4f' % (k * 0.25, np.sqrt((a[k * 12000:(k + 1) * 12000] ** 2).mean())))
    e.line('stats'); e.line('mem'); run(0.3)
    e.shot(os.path.expanduser('~/mtw/smoke.png'))
finally:
    e.close()
