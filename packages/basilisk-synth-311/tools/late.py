"""Test rig (Linux/macOS): CONF = a machine conf with paths filled in; CORE optional (tools/bsdrv.py). See README."""
import sys, time, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsdrv import *
e = Engine(os.environ['CONF'], lead=1024)
def stats(): return [e.u32(k) for k in ('sched_ontime', 'sched_late', 'sched_latemax')]
try:
    e.wait_packet(2, 90)
    e.line('hi 1'); e.line('go'); e.wait_text('ready', 20)
    e.line('dna ding#16H0,12;R120'); e.wait_text('built', 20)
    nid = 1
    for trial in range(8):
        for ahead in (1536,):
            base = e.dac_w() + ahead
            n = 6 if trial % 2 == 0 else 2
            for k in range(n):
                e.line('on %d %d 40000' % (k + (trial % 2) * 8, 22050), id=nid, at=base); nid += 1
            time.sleep(0.6)
            for k in range(n):
                e.line('off %d' % (k + (trial % 2) * 8), id=nid, at=e.dac_w() + ahead); nid += 1
            time.sleep(0.4)
        print('trial', trial, 'n', n, 'ontime/late/latemax', stats())
finally:
    e.close()
