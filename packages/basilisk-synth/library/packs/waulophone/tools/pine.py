# honey-pine board (wavy grain, knots, varnish sheen) for the WAULOPHONE pack's art lane
import numpy as np, json
from PIL import Image
W, H = 1200, 1600
rng = np.random.default_rng(36)
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
warp = 18 * np.sin(x / 210 + 1.3) + 9 * np.sin(x / 77 + 4) + 4 * np.sin(x / 23)
knots = [(310, 420, 46), (880, 1130, 38), (640, 260, 22)]
v = y + warp
for kx, ky, kr in knots:
    d = np.sqrt((x - kx) ** 2 * .35 + (y - ky) ** 2) + 1
    v += kr * 9 * np.exp(-d / (kr * 2.6)) * np.tanh((y - ky) / kr)
g = .55 + .16 * np.sin(v / 9.5) + .09 * np.sin(v / 2.7 + 1) + .14 * np.sin(v / 47) + .06 * np.sin(v / 1.3 + x / 400)
g += rng.normal(0, .05, (H, W))
for kx, ky, kr in knots:
    d = np.sqrt((x - kx) ** 2 * .9 + (y - ky) ** 2 * 1.6)
    g -= .9 * np.exp(-(d / kr) ** 2)
g = np.clip(g, 0, 1)
P = np.array([[0x9c, 0x61, 0x27], [0xbf, 0x80, 0x38], [0xd3, 0x9a, 0x4e], [0xe2, 0xb3, 0x6c], [0xf0, 0xcc, 0x8a]], np.float32)
t = g * (len(P) - 1); i = np.clip(t.astype(int), 0, len(P) - 2); f = (t - i)[..., None]
rgb = P[i] * (1 - f) + P[i + 1] * f
sheen = .1 * np.exp(-((y - H * .18) / (H * .2)) ** 2)
rgb = np.clip(rgb * (1 + sheen[..., None]), 0, 255)
ART = '/mnt/c/Users/willi/Desktop/synth-names/art/paulywaulyton'
Image.fromarray(rgb.astype(np.uint8)).save(ART + '/pine.png')
m = json.load(open(ART + '/manifest.json'))
m = [e for e in m if e['file'] != 'pine.png'] + [{'file': 'pine.png', 'title': 'Honey pine', 'tags': ['pine', 'wood', 'texture'], 'kind': 'texture',
     'author': 'drawn for this disc', 'license': 'packs lane', 'source_url': ''}]
json.dump(m, open(ART + '/manifest.json', 'w'), indent=1)
