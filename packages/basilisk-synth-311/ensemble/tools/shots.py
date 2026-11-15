#!/usr/bin/env python3
"""Screenshots of the Ensemble machine: resume the snapshot, assemble (`go`), shoot the animation, then voice a few
lanes and play notes.   shots.py MACHINE CORE OUTDIR [--dnas "DNA|DNA|..."] [--every 0.15]"""
import os, sys, time, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import bsdrv
from bsdrv import Engine
machine, core, out = sys.argv[1:4]
opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
every = float(opt('--every', '0.15'))
os.makedirs(out, exist_ok=True)
rec = os.path.join(out, 'rec'); os.makedirs(rec, exist_ok=True)
conf = os.path.join(out, 'w31.conf')
s = open(os.path.join(machine, 'w31.conf')).read()
s = s.replace('@MACHINE@', '"%s"' % machine).replace('@DRIVE@', '"%s/drive"' % machine).replace('@RECDIR@', '"%s"' % rec).replace('@PACKS@', '"%s/packs"' % machine)
open(conf, 'w').write(s)
e = Engine(conf, state=os.path.join(machine, 'w31.state'), core=core, log=os.path.join(out, 'engine.log'), name='ensshot%d' % os.getpid())
try:
    t0 = time.time()
    while e.state() < 2 and time.time() - t0 < 60: time.sleep(0.05)
    time.sleep(0.5)
    e.shot(os.path.join(out, 'a00-resumed.png'))
    e.line('go')
    k = 1; t1 = time.time()
    while time.time() - t1 < 12:
        e.poll()
        if any(x.startswith('ready') for x in e.texts): break
        e.shot(os.path.join(out, 'a%02d.png' % k)); k += 1
        time.sleep(every)
    e.shot(os.path.join(out, 'b-assembled.png'))
    dnas = opt('--dnas', '').split('|') if '--dnas' in sys.argv else []
    for i, d in enumerate(dnas):
        if not d: continue
        e.line('@%d name %s' % (i, d.split(';')[0][:24]))
        e.line('@%d cap 8' % i); e.line('@%d dna %s' % (i, d)); e.line('@%d env 0 0 100 300' % i)
    t2 = time.time()
    while time.time() - t2 < 60 and sum(1 for x in e.texts if ' built ' in x) < len([d for d in dnas if d]): e.poll(); time.sleep(0.1)
    for n in range(12):   # notes on every voiced lane
        for i, d in enumerate(dnas):
            if d: e.line('@%d on %d 22050 40000 0' % (i, n % 8), id=0, at=0)
        time.sleep(0.25)
        if n in (2, 6): e.shot(os.path.join(out, 'c%02d-playing.png' % n))
    e.line('stats'); time.sleep(0.5); e.poll()
    e.shot(os.path.join(out, 'd-end.png'))
    for x in e.texts: print(' ', x[:200])
finally:
    e.close()
