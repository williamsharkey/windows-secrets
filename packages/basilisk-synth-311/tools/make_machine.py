#!/usr/bin/env python3
"""Build the machine the plugin resumes: drive.zip (the Windows for Workgroups 3.11 C: drive with BASILISK 16 installed, and the
snapshot of it (sixteen Sound Recorders open, waiting for `go`).

  make_machine.py WFW_DRIVE GUEST_BUILD_DIR CORE_SO OUT_DIR

WFW_DRIVE: an installed WfW 3.11 C: (the one in site/basilisk-31-browser/w31.jsdos, see README).
The snapshot is made with the Linux build of the engine (tools/engine, built by build.sh); it loads on every OS."""
import os, shutil, struct, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bsdrv import Engine

src, gout, core, out = sys.argv[1:5]
folder = '--folder' in sys.argv   # C: as a plain folder instead of drive.zip (for experiments)
drive = os.path.join(out, 'drive')
if os.path.exists(out): shutil.rmtree(out)
shutil.copytree(src, drive)
for d in ('WATCOM', 'B3', '.jsdos'):
    shutil.rmtree(os.path.join(drive, d), ignore_errors=True)
os.makedirs(os.path.join(drive, 'BS'), exist_ok=True)
for f in ('SYNTH.EXE', 'SYNHOOK.DLL'): shutil.copy(os.path.join(gout, f), os.path.join(drive, 'BS', f))
shutil.copy(os.path.join(gout, 'BSYNTH.DRV'), os.path.join(drive, 'WINDOWS', 'SYSTEM', 'BSYNTH.DRV'))

def edit(path, fn):
    b = open(path, 'rb').read(); b2 = fn(b)
    open(path, 'wb').write(b2)
# the wave driver is the BSYN card's; Windows starts BASILISK 16; no system sounds
edit(os.path.join(drive, 'WINDOWS', 'SYSTEM.INI'), lambda b: b.replace(b'Wave=sb16snd.drv\r\n', b'Wave=bsynth.drv\r\n'))
def winini(b):
    import re
    b = re.sub(rb'run=[^\r\n]*', rb'run=C:\\BS\\SYNTH.EXE', b, count=1)
    if b'[sounds]' not in b:
        b = b.rstrip(b'\r\n\x1a') + (b'\r\n\r\n[sounds]\r\nSystemStart=none,Windows Start\r\nSystemExit=none,Windows Exit\r\n'
             b'SystemDefault=none,Default Beep\r\nSystemAsterisk=none,Asterisk\r\nSystemExclamation=none,Exclamation\r\n'
             b'SystemHand=none,Critical Stop\r\nSystemQuestion=none,Question\r\n')
    return b
edit(os.path.join(drive, 'WINDOWS', 'WIN.INI'), winini)

# C: travels as one zip (DOSBox Pure mounts it read-only): plugin hosts scan their folders for .dll files and
# must not find Windows 3.11's 16-bit ones; it also halves the download
import zipfile
if not folder:
  z = zipfile.ZipFile(os.path.join(out, 'drive.zip'), 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
  def add(path, name):   # fixed dates: the same inputs give the same zip on every machine (the snapshots must match it)
    zi = zipfile.ZipInfo(name, date_time=(1993, 11, 8, 3, 11, 0))
    if name.endswith('/'): zi.external_attr = 0o40755 << 16 | 0x10; z.writestr(zi, b'')
    else: zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16; z.writestr(zi, open(path, 'rb').read())
  for root, dirs, files in sorted(os.walk(drive)):
    dirs.sort()
    rel = os.path.relpath(root, drive)
    for d in dirs: add(os.path.join(root, d), (os.path.join(rel, d) if rel != '.' else d).replace(os.sep, '/') + '/')
    for f in sorted(files): add(os.path.join(root, f), (os.path.join(rel, f) if rel != '.' else f).replace(os.sep, '/'))
  z.close()
  shutil.rmtree(drive)

here = os.path.dirname(os.path.abspath(__file__))
conf_name = 'w31-folder.conf.in' if folder else 'w31.conf.in'
conf_in = open(os.path.join(here, '..', 'engine', conf_name)).read()
shutil.copy(os.path.join(here, '..', 'engine', conf_name), os.path.join(out, 'w31.conf'))
run_conf = os.path.join(out, 'make.conf')
open(run_conf, 'w').write(conf_in.replace('@MACHINE@', '"%s"' % os.path.abspath(out)).replace('@DRIVE@', '"%s"' % os.path.abspath(drive)))
state = os.path.join(out, 'w31.state')
log = os.path.join(out, 'make.log')
e = Engine(run_conf, core=core, make_state=state, log=log, name='bs311make')
try:
    e.wait_packet(2, 120)
    t = time.time()
    while time.time() - t < 20 and 'snapshot' not in open(log).read(): time.sleep(0.1)
finally:
    e.close()
os.remove(run_conf)
print('machine:', out, 'snapshot', os.path.getsize(state), 'bytes')
