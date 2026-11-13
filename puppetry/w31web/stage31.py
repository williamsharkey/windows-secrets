r"""Put the web engine's files where the page loads them, and tell the page their sizes and the machine's conf.
  stage31.py OUT_DIR SITE_DIR      (OUT_DIR: link.sh's and make_snapshot31.cjs's output)
-> SITE_DIR/basilisk-31-browser/web/{b31-worker.js, b31.wasm, w31web.state, drive.bin.gz, poster.png, .htaccess}
   and SITE_DIR/basilisk-31-browser.html's FILES, CONF and V."""
import hashlib, json, os, re, shutil, struct, sys
from PIL import Image
out, site = sys.argv[1:3]
here = os.path.dirname(os.path.abspath(__file__))
web = os.path.join(site, 'basilisk-31-browser', 'web'); os.makedirs(web, exist_ok=True)
pairs = [('b31-worker.js', 'b31-worker.js'), ('b31-worker.wasm', 'b31.wasm'), ('w31web.state', 'w31web.state'), ('drive.bin.gz', 'drive.bin.gz')]
for a, b in pairs: shutil.copyfile(os.path.join(out, a), os.path.join(web, b))
raw = open(os.path.join(out, 'frame.rgba'), 'rb').read(); w, h = struct.unpack('<II', raw[:8])
Image.frombytes('RGBA', (w, h), raw[8:8 + w * h * 4]).convert('RGB').save(os.path.join(web, 'poster.png'), optimize=True)
shutil.copyfile(os.path.join(here, 'htaccess'), os.path.join(web, '.htaccess'))
h = hashlib.sha1()
for a, b in pairs: h.update(open(os.path.join(web, b), 'rb').read())
v = '311w-' + h.hexdigest()[:8]
files = [{'name': b, 'size': os.path.getsize(os.path.join(web, b))} for a, b in pairs if b != 'b31-worker.js']
conf = open(os.path.join(here, 'w31.conf')).read()
p = os.path.join(site, 'basilisk-31-browser.html'); s = open(p).read()
s = re.sub(r"V = '[^']*';", "V = '%s';" % v, s, count=1)
s = re.sub(r"const FILES = \[.*?\];", 'const FILES = ' + json.dumps(files).replace('"name"', 'name').replace('"size"', 'size').replace('"', "'") + ';', s, count=1)
s = re.sub(r"const CONF = '.*?';", lambda m: 'const CONF = ' + json.dumps(conf).replace("'", "\\'").replace('"', "'", 1)[:-1] + "';", s, count=1)
open(p, 'w').write(s)
print(v, files)
