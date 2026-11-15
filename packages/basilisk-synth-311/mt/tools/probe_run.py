#!/usr/bin/env python3
"""Drive PROBE.EXE (mt/guest/probe.c) in a cold-booted Windows 3.11: launch Sound Recorders until Windows refuses,
with heap censuses along the way.  probe_run.py CONF CORE LOG SCRIPT
SCRIPT: host lines separated by ';' (each waits for its reply), e.g. "census;launch 600 0;census;conv;sel;mem"."""
import os, sys, time, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
from bsdrv import Engine
conf, core, log, script = sys.argv[1:5]
e = Engine(conf, core=core, log=log, name='mtprobe%d' % os.getpid())
e.u32('vid_want', 0)
e.u32('offline', 1); struct.pack_into('<Q', e.m, __import__('bsdrv').OFF['grant_until'], 1 << 62)   # run as fast as it can
t0 = time.time()
try:
    e.wait_text('probe up', 600)
    print('boot %.1f s wall' % (time.time() - t0), flush=True)
    for cmd in script.split(';'):
        cmd = cmd.strip(); n0 = len(e.texts); t = time.time()
        e.line(cmd)
        key = {'launch': ('launched', 'fail'), 'census': ('user free',), 'conv': ('conv',), 'low': ('lowowners',), 'sel': ('sel',), 'mem': ('mem',),
               'strip': ('strip',), 'play': ('played',), 'stop': ('stopped',), 'status': ('status',), 'closeall': ('closed',), 'ping': ('pong',), 'autostrip': ('pong',), 'deleted': ('pong',), 'voices': ('pong',), 'dump': ('pong children',), 'veto': ('pong',)}[cmd.split()[0]]
        while time.time() - t < 3600:
            e.poll()
            if any(any(s.startswith(k) or (' ' + k) in s[:12] for k in key) for s in e.texts[n0:]): break
            time.sleep(0.05)
        print('# %s: %.1f s wall' % (cmd, time.time() - t), flush=True)
finally:
    e.close()
