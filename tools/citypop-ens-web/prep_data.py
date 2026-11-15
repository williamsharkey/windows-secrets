#!/usr/bin/env python3
"""The album page's data: the slim discs, the machine's settings, the album and what to fetch ahead.
   prep_data.py ALBUM.ens MACHINE_DIR OUT_DIR
MACHINE_DIR is the Ensemble machine (ensemble/machine via make_machine.py: drive.zip, library.zip, packs/).
Writes OUT_DIR/:
  library.zip  the library disc (L:) with only the sounds the album uses, and its LIBRARY.TSV lines
  packs.zip    the pack disc (P:): PACKS.TSV and RAINYLOF with only the album's sounds (stored, read in pieces)
  names.txt    every sound name the DNAs may use (the host's parser)
  w31.conf     the machine's settings for the browser (/machine)
  album.ens    the schedule (copied)
  schedule.json  per track, the byte ranges of packs.zip its sounds sit in (fetched ahead of the track)"""
import os, re, sys, json, zipfile, shutil
ens, machine, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
segs, tracks = [], []
for l in open(ens):
    if l.startswith('S '):
        f = l.rstrip('\n').split(' ', 10); rest = f[10].split('\t')
        segs.append(dict(track=int(f[3]), dna=rest[2]))
    elif l.startswith('T '): tracks.append(l)
def names_of(dna):
    return set(re.findall(r'(?:^|/|I|M)([a-z][a-z0-9_]+)', dna.split(';')[0]))
need = set(); per = {}
for s in segs: n = names_of(s['dna']); need |= n; per.setdefault(s['track'], set()).update(n)
# the pack disc
pk = os.path.join(machine, 'packs')
packs_line = next(l for l in open(os.path.join(pk, 'PACKS.TSV'), encoding='latin1') if l.split('\t')[0] == 'RAINYLOF')
lib_lines, pack_files = [], {}
for l in open(os.path.join(pk, 'RAINYLOF', 'LIBRARY.TSV'), encoding='latin1'):
    f = l.rstrip('\r\n').split('\t')
    if l.startswith('#') or (len(f) > 2 and f[0] in need):
        lib_lines.append(l if l.endswith('\n') else l + '\n')
        if len(f) > 2 and not l.startswith('#'): pack_files[f[0]] = f[2].replace('\\', '/').lstrip('/')
zp = os.path.join(out, 'packs.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_STORED) as z:
    z.writestr('PACKS.TSV', packs_line.replace('\r\n', '\n').replace('\n', '\r\n'))
    z.writestr('RAINYLOF/LIBRARY.TSV', ''.join(lib_lines).replace('\r\n', '\n').replace('\n', '\r\n'))
    for n, p in sorted(pack_files.items()): z.write(os.path.join(pk, 'RAINYLOF', p), 'RAINYLOF/' + p.upper())
ranges = {}
with zipfile.ZipFile(zp) as z:
    for info in z.infolist():
        ranges[info.filename] = [info.header_offset, info.header_offset + 30 + len(info.filename) + info.file_size + 64]
    cd = [min(r[0] for r in ranges.values()), os.path.getsize(zp)]
sched = {'ranges': []}
for t in range(len(tracks)):
    r = [[0, 4096], [cd[1] - 65536 if cd[1] > 65536 else 0, cd[1]], ranges['PACKS.TSV'], ranges['RAINYLOF/LIBRARY.TSV']]
    for n in sorted(per.get(t, ())):
        if n in pack_files: r.append(ranges['RAINYLOF/' + pack_files[n].upper()])
    sched['ranges'].append(r)
json.dump(sched, open(os.path.join(out, 'schedule.json'), 'w'))
# the library disc: only what the album uses
src = zipfile.ZipFile(os.path.join(machine, 'library.zip'))
tsv = src.read('LIBRARY.TSV').decode('latin1').splitlines(True)
keep, files = [], []
for l in tsv:
    f = l.rstrip('\r\n').split('\t')
    if l.startswith('#'): keep.append(l)
    elif len(f) > 2 and f[0] in need: keep.append(l); files.append(f[2].replace('\\', '/').lstrip('/'))
with zipfile.ZipFile(os.path.join(out, 'library.zip'), 'w', zipfile.ZIP_STORED) as z:
    z.writestr('LIBRARY.TSV', ''.join(keep))
    for name in src.namelist():
        if name.upper() == 'PRESETS.TSV': z.writestr(name, '')
    for p in files:
        try: z.writestr(p, src.read(p))
        except KeyError:
            try: z.writestr(p.upper(), src.read(p.upper()))
            except KeyError: print('missing in library.zip:', p)
# names (the host's DNA parser)
names = open(os.path.join(machine, 'library.names.txt')).read().split() + open(os.path.join(pk, 'packs.names.txt')).read().split()
open(os.path.join(out, 'names.txt'), 'w').write('\n'.join(names) + '\n')
# the settings: everything under /machine (the worker writes the files there)
conf = open(os.path.join(machine, 'w31.conf')).read()
conf = conf.replace('mount d @MACHINE@', 'mount d /machine').replace('mount r @RECDIR@', 'mount r /machine/rec').replace('mount p @PACKS@', 'imgmount p d:\\packs.zip -t zip')
open(os.path.join(out, 'w31.conf'), 'w').write(conf)
shutil.copy(ens, os.path.join(out, 'album.ens'))
print('packs.zip %.1f MB (%d sounds), library.zip %.1f MB (%d sounds), %d tracks' % (os.path.getsize(zp) / 1e6, len(pack_files),
      os.path.getsize(os.path.join(out, 'library.zip')) / 1e6, len(files), len(tracks)))
