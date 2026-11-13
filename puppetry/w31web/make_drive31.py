r"""C: for BASILISK 3.11 on the DOSBox Pure web engine, as the worker unpacks it: one gzip stream of records
([u16 name length][name][u32 size][bytes]; folders end in /).

  make_drive31.py W31_JSDOS BASILISK.EXE SUITE_DIR OUT/drive.bin.gz

From the in-browser edition's C: (the js-dos bundle site/basilisk-31-browser/w31.jsdos at its last js-dos version):
the mailbox files go (the BSYN card is the link here), BASILISK.EXE goes in already built (from SUITE_DIR's sources,
which go in too, as BASILISK.C and PARTS.C), and Windows starts it. make_snapshot31.cjs boots that, lets the suite
assemble, and writes the drive again as Windows left it, so the snapshot and C: always match."""
import gzip, os, re, struct, sys, zipfile
w31, exe, suite, out = sys.argv[1:5]
src = zipfile.ZipFile(w31)
files, dirs = {}, set()
for i in src.infolist():
    n = i.filename
    if n.startswith('.jsdos'): continue
    if n.endswith('/'): dirs.add(n); continue      # empty folders too (C:\B3\WORK starts empty)
    files[n] = src.read(i)
for n in list(files):
    if n.upper() in ('B3/TOWIN.TXT', 'B3/TOJS.TXT', 'B3/B3BOOT.EXE', 'B3/BASILISK.SRC', 'B3/PARTS.SRC', 'B3/LINK.H'): del files[n]
files['B3/BASILISK.EXE'] = open(exe, 'rb').read()
for a, b in (('basilisk.c', 'BASILISK.C'), ('parts.c', 'PARTS.C')):
    files['B3/' + b] = open(os.path.join(suite, a), 'rb').read().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
k = [n for n in files if n.upper() == 'WINDOWS/WIN.INI'][0]
b = re.sub(rb'run=[^\r\n]*', rb'run=C:\\B3\\BASILISK.EXE', files[k], count=1)
if not re.search(rb'(?im)^MouseSpeed=', b): b = re.sub(rb'(?i)\[windows\]\r\n', lambda m: m.group(0) + b'MouseSpeed=0\r\n', b, count=1)
files[k] = b
for n in files:
    p = n.split('/')
    for i in range(1, len(p)): dirs.add('/'.join(p[:i]) + '/')
raw = bytearray()
for n in sorted(dirs) + sorted(files):
    data = b'' if n.endswith('/') else files[n]
    nb = n.encode('latin1')
    raw += struct.pack('<H', len(nb)) + nb + struct.pack('<I', len(data)) + data
open(out, 'wb').write(gzip.compress(bytes(raw), 9))
print(out, len(files), 'files,', len(raw), 'bytes ->', os.path.getsize(out))
