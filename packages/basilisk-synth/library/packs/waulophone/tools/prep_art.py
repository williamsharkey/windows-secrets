# Builds the 'paulywaulyton' art lane (owner's own art: ghosts.garden captures, midigarden instrument faces, WAULOPHONE panel)
import os, glob, json
from PIL import Image, ImageOps, ImageEnhance
ART = '/mnt/c/Users/willi/Desktop/synth-names/art/paulywaulyton'
os.makedirs(ART + '/objects', exist_ok=True)
SH = os.path.expanduser('~/packwork/ggcap/shots2')
BS = os.path.expanduser('~/gardens/midigarden/midigarden/BeleSamples')
AUTH = 'William Sharkey (ghosts.garden, Paulywaulyton)'
LIC = "The owner's own artwork, used by the owner"
man = []
def shot(n): return sorted(glob.glob(f'{SH}/{n}-*.png'))[0]
SCENES = [   # frame, file, title, tags
 ('018', 'village-gate', 'The gate of Paulywaulyton, toadstool homes either side', ['village', 'toadstool', 'gate', 'night', 'vocal', 'choir']),
 ('046', 'paulywauly-big-ears', 'Paulywauly, big ears, at the fairy ring', ['paulywauly', 'ears', 'listen', 'vocal', 'night', 'fairy']),
 ('076', 'fairy-ring', 'The fairy ring under the bluebell lamps', ['fairy', 'ring', 'bell', 'bluebell', 'night', 'pad']),
 ('006', 'giant-snail', 'The giant snail through the toadstool grove', ['snail', 'toadstool', 'wood', 'bass', 'slow']),
 ('064', 'snail-house', 'The house on the snail', ['snail', 'house', 'toadstool', 'keys', 'wood']),
 ('044', 'dandelion-clock', 'The dandelion clock over the treetops at evening', ['dandelion', 'evening', 'sky', 'pad', 'lead']),
 ('030', 'root-tortoise', 'The spirit tortoise in the root tunnel, glowing mushrooms', ['tortoise', 'root', 'tunnel', 'mushroom', 'bass', 'kit']),
 ('000', 'front-room', "Paul's front room: the bookshelf, the synths, the long rug", ['room', 'books', 'keys', 'home']),
 ('040', 'leaf-boat', 'The leaf boat down the stream', ['boat', 'leaf', 'stream', 'lead', 'pad']),
 ('024', 'narrowboat', 'The narrowboat on the canal at night', ['canal', 'boat', 'night', 'bass']),
 ('050', 'otolith', 'OTOLITH, the little listening café', ['cafe', 'listening', 'keys', 'kit']),
 ('028', 'old-oak', 'The old oak in the back garden, the fairy door in its root', ['oak', 'tree', 'door', 'fairy', 'bell']),
 ('020', 'cargo-bike', 'The cargo bike through the flower market', ['bike', 'market', 'street', 'kit']),
]
CROP = {'paulywauly-big-ears': (110, 190, 414, 560)}
for fr, name, title, tags in SCENES:
    im = Image.open(shot(fr)).convert('RGB').crop(CROP.get(name, (0, 108, 414, 588)))
    im = ImageOps.autocontrast(im, cutoff=1, preserve_tone=True); im = ImageEnhance.Color(im).enhance(1.2); im = ImageEnhance.Brightness(im).enhance(1.06)
    im.save(f'{ART}/{name}.png')
    man.append({'file': f'{name}.png', 'title': title, 'tags': tags + ['paulywaulyton'], 'kind': 'background', 'author': AUTH, 'license': LIC,
                'source_url': 'https://ghosts.garden/'})
def cut(src, box=None, thresh=18):
    im = Image.open(src).convert('RGBA')
    if box: im = im.crop(box)
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if r < thresh and g < thresh and b < thresh: px[x, y] = (0, 0, 0, 0)
    bb = im.getbbox(); return im.crop(bb) if bb else im
OBJ = [
 ('bele-object-preset-waul-doo.png', 'paulywauly', 'Paulywauly (Doo), pixel portrait', ['paulywauly', 'doo', 'vocal', 'portrait']),
 ('bele-object-preset-waul-barry.png', 'barry', 'Barry, the golden crooner', ['barry', 'crooner', 'bass', 'vocal']),
 ('bele-object-preset-waul-boop.png', 'boop', 'Boop, the honey bear with the round singing mouth', ['boop', 'bear', 'vocal']),
 ('bele-object-preset-waul-glock.png', 'glock', 'The glock: bird-song bells', ['glock', 'bell', 'bird']),
 ('bele-object-preset-waul-harp.png', 'harp', 'The willow harp', ['harp', 'pluck', 'keys']),
 ('bele-object-preset-r-homunculus-choir.png', 'homunculus-choir', 'The homunculus choir: three honey-wood dolls', ['choir', 'homunculus', 'vocal']),
 ('bele-object-preset-p-fairy-dust.png', 'fairy-dust', 'Fairy dust, a mobile of crystals', ['fairy', 'crystal', 'bell', 'pad']),
 ('bele-object-preset-r-fairy-door-pad.png', 'fairy-door-chimes', 'The fairy door chimes', ['fairy', 'door', 'chimes', 'pad']),
 ('bele-object-pauly.png', 'ear-horn', 'The brass ear horn', ['horn', 'ear', 'listen', 'lead']),
 ('bele-object-preset-waul-nylon.png', 'nylon', 'The nylon guitar', ['guitar', 'pluck', 'keys']),
]
for src, name, title, tags in OBJ:
    cut(f'{BS}/{src}').save(f'{ART}/objects/{name}.png')
    man.append({'file': f'objects/{name}.png', 'title': title, 'tags': tags + ['paulywaulyton', 'cutout'], 'kind': 'object', 'author': 'William Sharkey (midigarden / Bele Dance)', 'license': LIC, 'source_url': ''})
panel = f'{BS}/bele-panel-waulotron.png'
Image.open(panel).convert('RGB').save(f'{ART}/panel.png')
man.append({'file': 'panel.png', 'title': 'The WAULOPHONE, Paulywaulyton Works model PW-36', 'tags': ['waulophone', 'panel', 'machine', 'paulywaulyton'], 'kind': 'background', 'author': AUTH, 'license': LIC, 'source_url': 'https://ghosts.garden/'})
P = Image.open(panel).convert('RGBA')
P.crop((6, 4, 100, 102)).save(f'{ART}/objects/fairy-door.png')
P.crop((718, 8, 796, 100)).save(f'{ART}/objects/carved-ear.png')
man += [{'file': 'objects/fairy-door.png', 'title': 'The fairy door of the WAULOPHONE', 'tags': ['fairy', 'door', 'paulywaulyton'], 'kind': 'object', 'author': AUTH, 'license': LIC, 'source_url': ''},
        {'file': 'objects/carved-ear.png', 'title': 'The carved ear (LISTEN)', 'tags': ['ear', 'listen', 'paulywaulyton'], 'kind': 'object', 'author': AUTH, 'license': LIC, 'source_url': ''}]
json.dump(man, open(f'{ART}/manifest.json', 'w'), indent=1)
print(len(man))
# shaped cut-outs from the panel: the ear (an oval) and the fairy door (round-topped)
from PIL import ImageDraw
def shaped(path, shape):
    im = Image.open(path).convert('RGBA'); w, h = im.size
    m = Image.new('L', (w, h), 0); d = ImageDraw.Draw(m)
    if shape == 'oval': d.ellipse((2, 0, w - 3, h - 12), fill=255)
    else: d.rounded_rectangle((0, 0, w - 1, h - 1), radius=w // 2, fill=255); d.rectangle((0, h // 2, w - 1, h - 1), fill=255)
    im.putalpha(m); im.save(path)
shaped(f'{ART}/objects/carved-ear.png', 'oval')
shaped(f'{ART}/objects/fairy-door.png', 'arch')
