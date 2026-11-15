#!/usr/bin/env python3
"""Ensemble debugging: resume, go, then host lines from argv (each `;`-separated), printing everything Windows says."""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
from bsdrv import Engine
machine, core, out, script = sys.argv[1:5]
os.makedirs(out + '/rec', exist_ok=True)
s = open(os.path.join(machine, 'w31.conf')).read().replace('@MACHINE@', '"%s"' % machine).replace('@DRIVE@', '"%s/drive"' % machine).replace('@RECDIR@', '"%s/rec"' % out).replace('@PACKS@', '"%s/packs"' % machine)
open(out + '/w31.conf', 'w').write(s)
e = Engine(out + '/w31.conf', state=os.path.join(machine, 'w31.state') if not os.environ.get('ENS_COLD') else '-', core=core, log=out + '/engine.log', name='ensdbg%d' % os.getpid())
try:
    t0 = time.time()
    while e.state() < 2 and time.time() - t0 < 60: time.sleep(0.05)
    if os.environ.get('ENS_COLD'):
        while not any('ENSEMBLE up' in x for x in e.texts) and time.time() - t0 < 120: e.poll(); time.sleep(0.05)
    for cmd in script.split(';'):
        cmd = cmd.strip()
        if cmd.startswith('sleep '): t = time.time(); d = float(cmd[6:]);
        if cmd.startswith('sleep '):
            while time.time() - t < d: e.poll(); time.sleep(0.05)
            continue
        if cmd.startswith('shot '): e.shot(os.path.join(out, cmd[5:])); continue
        if cmd.startswith('wait '):
            t = time.time(); w = cmd[5:]
            while time.time() - t < 60 and not any(w in x for x in e.texts): e.poll(); time.sleep(0.05)
            print('# waited %.1f s for %s' % (time.time() - t, w), flush=True); continue
        e.line(cmd)
    e.poll()
finally:
    e.close()
