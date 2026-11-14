#!/usr/bin/env python3
r"""The web edition's machine files: drive.zip (C:), the same Windows for Workgroups 3.11 drive as the plugin's
(packages/basilisk-synth-311/tools/make_machine.py: the same steps, without the native snapshot, which the web
edition makes with its own engine, make_snapshot.mjs), plus w31.conf.

  make_drive.py W31_JSDOS GUEST_BUILD_DIR PKG_DIR OUT_DIR [--keep LIST.txt] [--xpsounds DIR|DRIVE.zip]

--xpsounds: XP's sounds for C:\XPSOUNDS (BASILISK 16 1.2.1+): a folder made by packages/basilisk-synth-311/tools/
xpsounds311.py, or the plugin's own machine/drive.zip, from which XPSOUNDS\ is taken. Not in git (Microsoft's audio).

--keep: only the files listed (paths relative to C:, one per line, as recorded by a traced session; see README),
plus every file Windows might load on its own (settings, drivers, fonts, sounds: KEEP_EXT), go into the zip, which
makes the download smaller. Directories are always kept."""
import os, re, shutil, sys, zipfile

w31, gout, pkg, out = sys.argv[1:5]
keep = None
if '--keep' in sys.argv:
    keep = set(l.strip().upper() for l in open(sys.argv[sys.argv.index('--keep') + 1]) if l.strip() and not l.startswith('#'))
os.makedirs(out, exist_ok=True)
src = zipfile.ZipFile(w31)
files = {}
for i in src.infolist():
    n = i.filename
    if n.endswith('/') or n.split('/')[0] in ('WATCOM', 'B3', '.jsdos'): continue
    files[n] = src.read(i)
extra = os.path.join(pkg, 'machine-extra')
for f in ('CHORD.WAV', 'TADA.WAV'): files['WINDOWS/' + f] = open(os.path.join(extra, f), 'rb').read()
for f in ('SYNTH.EXE', 'SYNHOOK.DLL'): files['BS/' + f] = open(os.path.join(gout, f), 'rb').read()
files['WINDOWS/SYSTEM/BSYNTH.DRV'] = open(os.path.join(gout, 'BSYNTH.DRV'), 'rb').read()
if '--xpsounds' in sys.argv:
    xp = sys.argv[sys.argv.index('--xpsounds') + 1]
    if xp.lower().endswith('.zip'):
        zx = zipfile.ZipFile(xp)
        for i in zx.infolist():
            if i.filename.upper().startswith('XPSOUNDS/') and i.filename.upper().endswith('.WAV'): files['XPSOUNDS/' + i.filename.split('/')[-1].upper()] = zx.read(i)
        # and, from the plugin's drive, its help: C:\BS\BASIL16.HLP, the BASILISK 16 group and Program Manager's list of
        # groups (F1 in BASILISK 16 opens the help with WINHELP.EXE, which drive-keep.txt keeps)
        for n in ('BS/BASIL16.HLP', 'WINDOWS/BASIL16.GRP', 'WINDOWS/PROGMAN.INI'):
            if n in zx.namelist(): files[n] = zx.read(n)
    else:
        for f in sorted(os.listdir(xp)):
            if f.upper().endswith('.WAV'): files['XPSOUNDS/' + f.upper()] = open(os.path.join(xp, f), 'rb').read()
def key(name):
    for k in files:
        if k.upper() == name.upper(): return k
    raise KeyError(name)
k = key('WINDOWS/SYSTEM.INI'); files[k] = files[k].replace(b'Wave=sb16snd.drv\r\n', b'Wave=bsynth.drv\r\n')
k = key('WINDOWS/WIN.INI'); b = files[k]
b = re.sub(rb'run=[^\r\n]*', rb'run=C:\\BS\\SYNTH.EXE', b, count=1)
# no pointer acceleration: a drag reaches the emulated mouse as relative motion (web_engine.c), which must move
# Windows' pointer by the same distance however fast it goes
if not re.search(rb'(?im)^MouseSpeed=', b): b = re.sub(rb'(?i)\[windows\]\r\n', lambda m: m.group(0) + b'MouseSpeed=0\r\n', b, count=1)
if b'[sounds]' not in b:
    b = b.rstrip(b'\r\n\x1a') + (b'\r\n\r\n[sounds]\r\nSystemStart=none,Windows Start\r\nSystemExit=none,Windows Exit\r\n'
         b'SystemDefault=none,Default Beep\r\nSystemAsterisk=none,Asterisk\r\nSystemExclamation=none,Exclamation\r\n'
         b'SystemHand=none,Critical Stop\r\nSystemQuestion=none,Question\r\n')
files[k] = b
KEEP_EXT = {'INI', 'DRV', '386', 'FON', 'FOT', 'TTF', 'GRP', 'BAT', 'SYS', 'CFG', 'DAT', 'WAV', 'CPL', 'INF', 'REG', 'TXT', 'COM'}
def kept(n):
    if keep is None or n.upper() in keep: return True
    b = n.rsplit('/', 1)[-1]
    return '.' in b and b.rsplit('.', 1)[1].upper() in KEEP_EXT
dirs = set()
for n in files:
    p = n.split('/')
    for i in range(1, len(p)): dirs.add('/'.join(p[:i]) + '/')
z = zipfile.ZipFile(os.path.join(out, 'drive.zip'), 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
nkept = dropped = 0
for n in sorted(dirs | set(files)):
    zi = zipfile.ZipInfo(n, date_time=(1993, 11, 8, 3, 11, 0))
    if n.endswith('/'): zi.external_attr = 0o40755 << 16 | 0x10; z.writestr(zi, b''); continue
    if not kept(n): dropped += 1; continue
    zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16; z.writestr(zi, files[n]); nkept += 1
z.close()
conf = open(os.path.join(pkg, 'engine', 'w31.conf.in')).read()
open(os.path.join(out, 'w31.conf'), 'w').write(conf.replace('@MACHINE@', '/machine'))
print('drive.zip', os.path.getsize(os.path.join(out, 'drive.zip')), 'bytes,', nkept, 'files', '(%d left out)' % dropped if keep else '')
