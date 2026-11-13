#!/usr/bin/env python3
"""Put the web edition's files together for the site (site/sndrec/try/ on the server).
  stage.py WORKDIR LIBRARY_DIR SITE_OUT
The page script (b16-try.js) gets the files' sizes and a version (a hash of every file) for cache busting."""
import gzip, hashlib, json, os, re, shutil, struct, sys
from PIL import Image
W, LIB, OUT = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
cp = lambda a, b: shutil.copyfile(a, os.path.join(OUT, b))
cp(os.path.join(W, 'out', 'b16-worker.js'), 'b16-worker.js')
cp(os.path.join(W, 'out', 'b16-worker.wasm'), 'b16.wasm')
cp(os.path.join(W, 'out', 'w31web.state'), 'w31web.state')
cp(os.path.join(W, 'machine', 'drive.zip'), 'drive.zip')
cp(os.path.join(HERE, 'audio-worklet.js'), 'b16-audio.js')
cp(os.path.join(HERE, 'htaccess'), '.htaccess')
lib = os.path.join(OUT, 'library.zip')
if not os.path.exists(lib) or os.path.getsize(lib) != os.path.getsize(os.path.join(LIB, 'library.zip')): cp(os.path.join(LIB, 'library.zip'), 'library.zip')
# the poster: Windows' screen at the snapshot
b = open(os.path.join(W, 'out', 'frame.rgba'), 'rb').read(); w, h = struct.unpack('<II', b[:8])
Image.frombytes('RGBA', (w, h), b[8:8 + w * h * 4]).convert('RGB').save(os.path.join(OUT, 'poster.png'), optimize=True)   # lossless
# the plugin's program list (the same as Windows' Preset drop-down)
src = open(os.path.join(W, 'src', 'packages', 'basilisk-synth-311', 'plugin', 'presets_gen.h')).read()
presets = re.findall(r'\{"((?:[^"\\]|\\.)*)", "((?:[^"\\]|\\.)*)"\}', src)
state = json.load(open(os.path.join(W, 'out', 'state.json')))
data = {'conf': open(os.path.join(W, 'machine', 'w31.conf')).read(), 'layers': state['layers'],
        'libraryNames': open(os.path.join(LIB, 'library.names.txt')).read(), 'presets': presets,
        'librarySize': os.path.getsize(os.path.join(LIB, 'library.zip')),
        # a card with PTRGET (BSYNTH.DRV moves the pointer itself at interrupt time, with mouse_event) needs no
        # relative-motion help for drags (web_engine.c); older cards do
        'relDrag': 'PTRGET' not in open(os.path.join(W, 'src', 'packages', 'basilisk-synth-311', 'dosbox-pure', 'bsynth.cpp')).read()}
open(os.path.join(OUT, 'b16-data.json'), 'w').write(json.dumps(data, separators=(',', ':')))
files = []
for n in ('b16.wasm', 'w31web.state', 'drive.zip'):
    d = open(os.path.join(OUT, n), 'rb').read()
    files.append({'name': n, 'size': len(d), 'gz': len(d) if n.endswith('.zip') else len(gzip.compress(d, 6))})
hsh = hashlib.sha1()
for n in sorted(os.listdir(OUT)):
    if n != 'library.zip' and n != 'b16-try.js' and os.path.isfile(os.path.join(OUT, n)): hsh.update(open(os.path.join(OUT, n), 'rb').read())
hsh.update(open(os.path.join(HERE, 'b16-try.js'), 'rb').read())   # (the page script itself, before its config goes in)
cfg = {'v': hsh.hexdigest()[:10], 'files': files, 'lead': 2048}
js = open(os.path.join(HERE, 'b16-try.js')).read()
js = re.sub(r'/\*CONFIG\*/.*?/\*END\*/', '/*CONFIG*/' + json.dumps(cfg, separators=(',', ':')) + '/*END*/', js, flags=re.S)
open(os.path.join(OUT, 'b16-try.js'), 'w').write(js)
tot = sum(f['gz'] for f in files)
print('staged', OUT, 'version', cfg['v'], '- download on click:', ', '.join('%s %.2f MB' % (f['name'], f['gz'] / 1048576) for f in files), '= %.2f MB' % (tot / 1048576))
