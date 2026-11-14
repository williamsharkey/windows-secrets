#!/usr/bin/env python3
"""The pack discs for SNDWAVE2000's Library tab (PRESET-ENGINE-2 16.3): drive P: of the machine.

    make_packs311.py DISCS_DIR OUT_DIR

DISCS_DIR: the packs lane's final set (packages/basilisk-synth/library/packs/out/discs): DISCS.TSV and one folder per
disc (the same files as its ISO, 8.3 names). Every disc DISCS.TSV lists is copied to OUT_DIR/<DIR>, DIR an 8.3 name
from its label (unique), and OUT_DIR/PACKS.TSV indexes them for Windows:
    dir TAB id TAB label TAB title TAB presets for 3.11
Any number of discs: new packs only add lines to DISCS.TSV. Also writes OUT_DIR/packs.names.txt: the sound NAMEs
the discs' LIBRARY.TSV files add (the host's name table).
"""
import os, re, shutil, sys

src, out = sys.argv[1], sys.argv[2]
shutil.rmtree(out, ignore_errors=True)
os.makedirs(out)
rows, used, names = [], set(), []
for line in open(os.path.join(src, 'DISCS.TSV'), encoding='utf-8', errors='replace'):
    line = line.rstrip('\r\n')
    if not line or line.startswith('#'):
        continue
    f = line.split('\t')
    if len(f) < 6:
        continue
    pid, label, _iso, title, _n, n311 = f[:6]
    folder = os.path.join(src, label)
    if not os.path.isdir(folder):
        print('make_packs311: no folder for %s, skipped' % label)
        continue
    base = re.sub(r'[^A-Z0-9_]', '', label.upper())[:8] or 'PACK'
    d, k = base, 1
    while d in used:
        k += 1; d = base[:8 - len(str(k))] + str(k)
    used.add(d)
    shutil.copytree(folder, os.path.join(out, d))
    rows.append('\t'.join([d, pid, label, title, n311]))
    lib = os.path.join(folder, 'LIBRARY.TSV')
    if os.path.exists(lib):
        for l in open(lib, encoding='cp1252', errors='replace'):
            if l.strip() and not l.startswith('#'):
                names.append(l.split('\t')[0].strip())
open(os.path.join(out, 'PACKS.TSV'), 'wb').write(''.join(r + '\r\n' for r in rows).encode('cp1252', 'replace'))
open(os.path.join(out, 'packs.names.txt'), 'w').write(''.join(n + '\n' for n in names))
print('packs: %d discs, %d sounds -> %s' % (len(rows), len(names), out))
