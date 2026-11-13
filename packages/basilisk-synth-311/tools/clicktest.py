"""Test rig (Linux/macOS): CONF = a machine conf with paths filled in; CORE optional (tools/bsdrv.py). See README."""
import sys, time, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsdrv import *
import numpy as np
e = Engine(os.environ['CONF'])
def click(x, y):
    e.mouse(x, y, 0); time.sleep(0.15); e.mouse(x, y, 1); time.sleep(0.12); e.mouse(x, y, 0); time.sleep(0.1)
try:
    e.wait_packet(2, 90)
    e.line('hi 1'); e.line('go'); e.wait_text('ready', 20)
    e.shot('/tmp/c0.png')
    click(587, 684)                 # Effects: Echo
    e.wait_text('built', 20); print([t for t in e.texts if t.startswith('edit')])
    click(268, 684)                 # Sound: ringout
    time.sleep(1.5); e.poll(); print([t for t in e.texts if t.startswith('edit')])
    e.shot('/tmp/c1.png')
finally:
    e.close()
