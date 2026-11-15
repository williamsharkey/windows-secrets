#!/usr/bin/env python3
"""Stage /citypop-ens/ for upload: the page (site/citypop-ens), the worklet, the worker and the machine's files.
   stage.py OUT_WEB SITE_DIR STAGE_DIR
OUT_WEB: link.sh's output plus prep_data.py's (ens-worker.js/.wasm, ens.state, drive.zip, library.zip, packs.zip,
album.ens, w31.conf, names.txt, schedule.json). Every URL carries its file's md5 (cache key)."""
import os, sys, json, shutil, hashlib
web, site, out = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(out, 'm'), exist_ok=True)
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()[:10]
def put(src, name):
    d = os.path.join(out, name); shutil.copyfile(src, d); return d
files = []
for name, src in [('ens.wasm', 'ens-worker.wasm'), ('ens.state', 'ens.state'), ('drive.zip', 'drive.zip'), ('library.zip', 'library.zip'), ('album.ens', 'album.ens')]:
    d = put(os.path.join(web, src), 'm/' + name)
    files.append(dict(name=name, url=name, size=os.path.getsize(d), v=md5(d)))
for n in ['w31.conf', 'names.txt', 'schedule.json']: put(os.path.join(web, n), 'm/' + n)
disc = put(os.path.join(web, 'packs.zip'), 'm/packs.zip')
# the worker: the Emscripten output looks for its .wasm beside it (unused: the page hands it the bytes) - keep it beside too
put(os.path.join(web, 'ens-worker.js'), 'ens-worker.js')
put(os.path.join(here, 'audio-worklet.js'), 'audio-worklet.js')
put(os.path.join(here, 'htaccess'), '.htaccess')
shutil.copyfile(os.path.join(out, '.htaccess'), os.path.join(out, 'm', '.htaccess'))
for n in ['ens.css', 'ens-page.js', 'still.png', 'still-loft.png']:
    if os.path.exists(os.path.join(site, n)): put(os.path.join(site, n), n)
tracks = []
for l in open(os.path.join(web, 'album.ens'), encoding='utf-8'):
    if l.startswith('T '):
        f = l.rstrip('\n').split(' ', 4); tracks.append(dict(i=int(f[1]), start=float(f[2]), end=float(f[3]), title=f[4]))
bpm = []
try: bpm = [t.get('bpm', 100) for t in json.load(open(os.path.join(site, '..', 'citypop', 'album.json')))['tracks']]
except Exception: pass
code = md5(os.path.join(out, 'ens-worker.js')) + md5(os.path.join(out, 'audio-worklet.js'))[:4]
man = dict(v=code, ui='20261114j', base='m/', files=files, disc=dict(url='packs.zip', size=os.path.getsize(disc), v=md5(disc)),
           tracks=tracks, bpm=bpm, lead=96000, leadMax=288000, master=0.7)
html = open(os.path.join(site, 'index.html'), encoding='utf-8').read()
html = html.replace('@MANIFEST@', json.dumps(man, separators=(',', ':'))).replace('ens.css?v=@V@', 'ens.css?v=' + md5(os.path.join(out, 'ens.css'))) \
           .replace('ens-page.js?v=@V@', 'ens-page.js?v=' + md5(os.path.join(out, 'ens-page.js')))
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(html)
tot = sum(f['size'] for f in files) + man['disc']['size']
print('staged %s: %d tracks, %.1f MB of machine (%.1f MB of it the pack disc, in pieces)' % (out, len(tracks), tot / 1e6, man['disc']['size'] / 1e6))
