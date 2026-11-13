import os, sys, time, shutil
os.environ['BS311_ENGINE'] = '/home/wm/pe2-311/bin/engine'; os.environ['BS311_OFFS'] = '/home/wm/pe2-311/bin/offs'
sys.path.insert(0, '/home/wm/pe2-311/src')
import bsdrv
from bsdrv import Engine, wav
import numpy as np
M = '/home/wm/pe2-311/m'; CORE = '/home/wm/pe2-311/bin/dosbox_pure_libretro.so'
def conf():
    c = open('/home/wm/pe2-311/src/w31-folder.conf.in').read().replace('@MACHINE@', '"%s"' % M).replace('@DRIVE@', '"%s/drive"' % M)
    p = M + '/run.conf'; open(p, 'w').write(c); return p
def start(state=M + '/w31.state', make=None, name='pe2t311', log=M + '/engine.log'):
    e = Engine(conf(), state=state if not make else '-', core=CORE, name=name, make_state=make, log=log)
    open('/home/wm/pe2-311/engine.pid', 'a').write('%d\n' % e.p.pid)
    return e
def install():
    g = '/home/wm/pe2-311/gout'; d = M + '/drive'
    for f in ('SYNTH.EXE', 'SYNHOOK.DLL'): shutil.copy(g + '/' + f, d + '/BS/' + f)
    shutil.copy(g + '/BSYNTH.DRV', d + '/WINDOWS/SYSTEM/BSYNTH.DRV')
def make():
    install()
    st = M + '/w31.state'
    if os.path.exists(st): os.remove(st)
    e = start(make=st, name='pe2m311', log=M + '/make.log')
    try:
        e.wait_packet(2, 180)
        t = time.time()
        while time.time() - t < 20 and 'snapshot' not in open(M + '/make.log').read(): time.sleep(0.1)
    finally: e.close()
    print('state', os.path.getsize(st))
class Rec:
    """continuous DAC capture in a thread"""
    def __init__(s, e):
        import threading
        s.e = e; s.start = e.dac_w(); s.pos = s.start; s.buf = []; s.on = True
        s.t = threading.Thread(target=s.run, daemon=True); s.t.start()
    def run(s):
        while s.on:
            w = s.e.dac_w()
            if w > s.pos:
                if w - s.pos > 60000: print('CAPTURE OVERRUN', w - s.pos)
                s.buf.append(s.e.read(s.pos, w - s.pos)); s.pos = w
            time.sleep(0.005)
    def stop(s):
        s.on = False; s.t.join(); return np.concatenate(s.buf) if s.buf else np.zeros((0, 2))
def pr(e, text, want, timeout=30, id=0, at=0):
    n0 = len(e.texts); e.line(text, id=id, at=at)
    t = time.time()
    while time.time() - t < timeout:
        e.poll()
        for s in e.texts[n0:]:
            if s.startswith(want): return s
        time.sleep(0.005)
    raise TimeoutError(text)
