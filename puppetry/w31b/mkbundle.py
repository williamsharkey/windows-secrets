#!/usr/bin/env python3
"""mkbundle.py W : the js-dos bundle (zip) for BASILISK 3.11 in the browser: the WfW 3.11 C: tree + dosbox-x conf"""
import os, sys, zipfile
W = sys.argv[1]
CONF = r"""[sdl]
autolock=false
output=surface
showmenu=false
[dosbox]
machine=svga_s3
memsize=64
quit warning=false
startbanner=false
[cpu]
cputype=pentium
core=normal
cycles=max
[render]
scaler=none
[mixer]
nosound=true
[speaker]
pcspeaker=false
[serial]
serial1=disabled
serial2=disabled
[autoexec]
mount c .
c:
SET TEMP=C:\WINDOWS\TEMP
SET PATH=C:\WINDOWS;C:\WATCOM\BINW
SET WATCOM=C:\WATCOM
SET INCLUDE=C:\WATCOM\H;C:\WATCOM\H\WIN
cd \WINDOWS
WIN.COM
"""
out = os.path.join(W, 'www', 'w31.jsdos')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    root = os.path.join(W, 'c')
    z.writestr('.jsdos/', '')
    for dp, dn, fn in os.walk(root):
        for d in dn:      # libzip extraction needs the directories as entries of their own
            z.writestr(os.path.relpath(os.path.join(dp, d), root) + '/', '')
        for f in fn:
            full = os.path.join(dp, f)
            z.write(full, os.path.relpath(full, root))
    z.writestr('.jsdos/dosbox.conf', CONF)
    z.writestr('.jsdos/jsdos.json', '{"version":"8"}')
print(out, os.path.getsize(out))
