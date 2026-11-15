"""CITYPOP DEPROGRAMMED: Onomichi after the rain, 2 a.m.
A deterministic procedural night scene, rendered at device-pixel resolution in five layers.
usage: python3 scene.py [desktop|portrait|all] [--preview DIR]
"""
import json, math, os, sys, zlib, time
import numpy as np
import kit
from kit import Layer, C, mix, vnoise, quantize, save_indexed, bayer, F

SEED = 20261114
PENDING = []
DBG = []
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_IMG = os.path.normpath(os.path.join(HERE, '..', 'img'))
OUT_JSON = os.path.normpath(os.path.join(HERE, '..', '..', 'art', 'scene2.json'))

VARIANTS = {
    'hd': dict(W=1920, H=1080, hy=270, f=1125, cam=18.0, slope=0.15, Zs=110.0, cx=1125,
               lane0=0.7, moon=(1420, 150, 36), towers=(0.32, 0.72), bridge=(-120, 1035),
               pagoda=(1567, 80.0), island_end=1237, shipyard=(135, 480), unit=1.0, focus=[0.6, 0.5]),
    'desktop': dict(W=2560, H=1440, hy=360, f=1500, cam=18.0, slope=0.15, Zs=110.0, cx=1500,
                    lane0=0.7, moon=(1870, 190, 44), towers=(0.32, 0.72), bridge=(-160, 1380),
                    pagoda=(2090, 80.0), island_end=1650, shipyard=(180, 640), unit=1.0),
    'portrait': dict(W=1170, H=2532, hy=900, f=1100, cam=24.0, slope=0.15, Zs=110.0, cx=640,
                     lane0=0.5, moon=(850, 560, 40), towers=(0.3, 0.7), bridge=(-140, 640),
                     pagoda=(960, 80.0), island_end=820, shipyard=(-200, 120), unit=1.0, focus=[0.55, 0.45]),
}

# ------------------------------------------------------------------ colours
K = dict(
    sky0=C('#04051a'), sky1=C('#0b0d33'), sky2=C('#191a4c'), sky3=C('#2e2163'), sky4=C('#4a2670'), sky5=C('#6a2c76'),
    haze=C('#1d1a48'), hazeW=C('#3b2a68'),
    moon=C('#f4f0fb'), moonM=C('#cdc5e6'), halo=C('#a89cd8'), halo2=C('#c06a9a'),
    star=C('#e8e6ff'), starW=C('#ffe6c8'), starB=C('#b8c8ff'),
    navy0=C('#06071a'), navy1=C('#0c0f2e'), navy2=C('#161a44'), ind=C('#22215a'),
    plum=C('#33226a'), purp=C('#4a2470'), mag=C('#6a2a74'), mag2=C('#8c3478'), pink=C('#b0507e'),
    brn0=C('#1e1418'), brn1=C('#2c1c1e'), brn2=C('#402a26'), brn3=C('#5a3a2c'),
    tile=C('#1b1d3c'), tileH=C('#3a3a70'), tileR=C('#2a2148'), tin=C('#2c2234'),
    plaster=C('#2a2442'), plaster2=C('#322a48'), conc=C('#22253e'), mortar=C('#30283a'),
    stone=C('#211f36'), stoneH=C('#3a3656'), moss=C('#1c3236'), moss2=C('#2a4640'), leaf=C('#0d1a24'), leafH=C('#20383e'),
    warm=C('#ffd08a'), warm2=C('#e8a860'), warm3=C('#b87848'), amber=C('#ffb860'), cream=C('#f6e2b4'),
    tv=C('#8cb0f0'), tv2=C('#5a78c8'), cool=C('#dff2ff'), fluo=C('#c8f0e8'), pinkL=C('#ff9ac8'),
    red=C('#a8283a'), red2=C('#d03848'), redL=C('#ff4a50'), green=C('#3a8a5a'),
    glass=C('#0d1034'), glass2=C('#1e1e50'), frame=C('#0a0a1c'),
    water0=C('#0a0c2a'), water1=C('#181a48'), water2=C('#2c2262'),
)


def rng_for(name, variant):
    return np.random.default_rng([SEED, zlib.crc32(name.encode()), zlib.crc32(variant.encode())])


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


class Cam:
    def __init__(s, V):
        s.__dict__.update(V)
        s.Esea = -s.slope * s.Zs - 2.0

    def g(s, Z):
        return -s.slope * min(Z, s.Zs)

    def P(s, X, Z, E):
        return (s.cx + s.f * X / Z, s.hy + s.f * (s.cam - E) / Z)

    def Xat(s, x, Z):
        return (x - s.cx) * Z / s.f

    def Zat_ground(s, y):
        # ground y = hy + f*slope + f*cam/Z
        d = y - s.hy - s.f * s.slope
        return s.f * s.cam / d if d > 0 else 1e9

    def lane(s, Z):
        return s.lane0 + 0.9 * math.sin(Z / 23.0 + 0.6) + 0.5 * math.sin(Z / 9.5)


def fogt(Z):
    return clamp(1 - math.exp(-Z / 260.0)) * 0.75


def fz(col, Z, extra=0.0):
    return mix(np.asarray(col, F), K['haze'], clamp(fogt(Z) + extra))


# ------------------------------------------------------------------ anchors
class GList(list):
    def append(self, x):
        if isinstance(x, dict) and 'layer' in x:
            x['_g'] = kit.GROUP[0]
        super().append(x)


class GDict(dict):
    def __setitem__(self, k, v):
        if isinstance(v, list) and not isinstance(v, GList) and k not in ('windows', 'far', 'windowsFields'):
            v = GList(v)
        if isinstance(v, dict) and 'layer' in v and not isinstance(v, GDict):
            v['_g'] = kit.GROUP[0]
        super().__setitem__(k, v)


class Anchors:
    def __init__(s):
        s.d = GDict()
        s.d.update(dict(windows=[], lamps=[], puddles=[], water=[], stars=dict(regions=[], points=[]), moon=None,
                   bridge=dict(lights=[], towers=[], cables=[], deck=None), train=None, boats=[], ferry=None,
                   far=[], drips=[], cat=None, vending=None, shrine=None, mailbox=None, bikes=[], wires=[],
                   vents=[], laundry=[], signs=[], stairs=[], paths=[], ac=[], eaves=[], bench=None, shop=None,
                   crossing=None, regions=dict(sky=None, haze=[], motes=[]), plants=[], poles=[], trees=[]))
        for k, v in list(s.d.items()):
            if isinstance(v, list) and k not in ('windows', 'far'):
                dict.__setitem__(s.d, k, GList(v))

    def win(s, x, y, w, h, lit, baked, hue, curtain, room, layer, dark):
        s.d['windows'].append([int(x), int(y), int(w), int(h), int(lit), int(baked), hue, int(curtain), room,
                               layer, [int(v * 255) for v in dark]])
        return len(s.d['windows'])


HUES = ['warm', 'cool', 'tv', 'pink']
ROOMS = ['plain', 'tv', 'desk']


# ================================================================== SKY
def draw_sky(L, cam, A, rng, V):
    W, H, hy = L.W, L.H, cam.hy
    mx, my, mr = V['moon']
    Y, X = np.mgrid[0:H, 0:W].astype(F)
    t = np.clip(Y / hy, 0, 1.2)
    stops = [(0.0, K['sky0']), (0.28, K['sky1']), (0.55, K['sky2']), (0.78, K['sky3']), (0.93, K['sky4']), (1.02, K['sky5']), (1.2, K['sky5'])]
    rgb = np.zeros((H, W, 3), F)
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        m = (t >= a) & (t < b)
        u = ((t[m] - a) / (b - a))[:, None]
        rgb[m] = ca + (cb - ca) * u
    rgb[t >= 1.2] = K['sky5']
    # moon's glow: a wide magenta bloom and a cool inner halo, squashed by the moist air
    d = np.sqrt(((X - mx) / 1.0) ** 2 + ((Y - my) / 0.85) ** 2)
    bloom = np.clip(1 - d / (W * 0.42), 0, 1) ** 2.2
    rgb = 1 - (1 - rgb) * (1 - bloom[..., None] * K['mag2'] * 0.55)
    inner = np.clip(1 - d / (mr * 6.5), 0, 1) ** 2.0
    rgb = 1 - (1 - rgb) * (1 - inner[..., None] * K['halo'] * 0.55)
    # a 22-degree ring in the wet air
    ring = np.exp(-((d - mr * 4.6) / (mr * 0.35)) ** 2) * 0.10
    rgb = 1 - (1 - rgb) * (1 - ring[..., None] * K['halo'])
    # horizon glow: the town's light in the haze (warm-magenta, low)
    hg = np.exp(-((Y - hy) / (hy * 0.16)) ** 2) * 0.22
    rgb = 1 - (1 - rgb) * (1 - hg[..., None] * K['pink'])
    # cloud wisps: anisotropic noise, lit near the moon
    n = vnoise((H // 3 + 2, W // 14 + 2), 22, rng, octaves=4)
    from PIL import Image
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), F) / 255.0
    n2 = vnoise((H, W), 90, rng, octaves=3)
    band = smooth(0.12, 0.35, t) * (1 - smooth(0.80, 0.98, t))
    cloud = smooth(0.50, 0.78, n * 0.75 + n2 * 0.35) * band
    moonlit = np.clip(1 - d / (W * 0.30), 0, 1) ** 1.3
    ccol = mix(K['navy1'], K['plum'], 0.5)[None, None] + (K['halo'] - K['navy1'])[None, None] * (moonlit[..., None] * 0.55)
    # silver lining: the cloud edge (where density changes) catches moonlight
    edge = np.clip(cloud - np.roll(cloud, 6, axis=0), 0, 1) * moonlit * 1.8
    rgb = mix(rgb, ccol, (cloud * 0.72)[..., None])
    rgb = 1 - (1 - rgb) * (1 - np.clip(edge, 0, 0.6)[..., None] * K['halo'])
    # high thin streaks
    st = smooth(0.62, 0.9, n2) * smooth(0.0, 0.2, t) * (1 - smooth(0.4, 0.6, t)) * 0.25
    rgb = mix(rgb, K['sky2'], st[..., None])
    L.rgb[:] = rgb
    L.a[:] = True
    # moon disc
    dd = np.sqrt((X - mx) ** 2 + (Y - my) ** 2)
    disc = dd <= mr
    mn = vnoise((H, W), mr * 0.45, rng, octaves=3)
    maria = smooth(0.52, 0.66, mn)
    limb = 1 - 0.18 * (dd / mr) ** 3
    mc = mix(K['moon'], K['moonM'], maria[..., None] * 0.75) * limb[..., None]
    L.rgb[disc] = mc[disc]
    # stars: faint baked field, bright ones are life's (anchors)
    cl = cloud
    skyy = int(hy * 0.92)
    A.d['stars']['regions'] = [[0, 0, W, int(hy * 0.55)], [0, int(hy * 0.55), W, skyy - int(hy * 0.55)]]
    nbg = int(W * hy / 1100)
    for i in range(nbg):
        x, y = int(rng.random() * W), int((rng.random() ** 1.35) * skyy)
        if cl[y, x] > 0.35 or dd[y, x] < mr * 3:
            continue
        fade = (1 - y / skyy) * clamp(dd[y, x] / (mr * 10))
        b = (0.12 + 0.35 * rng.random() ** 2) * fade
        sc = [K['star'], K['starW'], K['starB']][int(rng.random() * 3)]
        L.rgb[y, x] = mix(L.rgb[y, x], sc, b)
    pts = []
    tries = 0
    while len(pts) < int(W * hy / 9000) and tries < 20000:
        tries += 1
        x, y = int(rng.random() * W), int((rng.random() ** 1.5) * skyy * 0.9)
        if cl[y, x] > 0.25 or dd[y, x] < mr * 4.5:
            continue
        mag = round(float(0.35 + 0.65 * rng.random() ** 2.2) * clamp(1.15 - y / skyy), 3)
        hue = ['white', 'warm', 'blue'][int(rng.random() * 3)]
        pts.append([x, y, mag, hue])
        L.rgb[y, x] = mix(L.rgb[y, x], K['star'], mag * 0.25)
    A.d['stars']['points'] = pts
    A.d['moon'] = dict(x=mx, y=my, r=mr, halo=int(mr * 4.6))
    A.d['regions']['sky'] = [0, 0, W, hy]
    A.d['regions']['haze'] = [[int(hy * 0.85), int(hy * 1.25)], [int(hy * 0.2), int(hy * 0.6)]]


# ================================================================== FAR: islands, strait, bridge, shore, rail
def ridge(W, rng, base, amp, scale, oct=4):
    n = vnoise((4, W + 8), scale, rng, octaves=oct)[1, :W]
    n = (n - n.min()) / (n.max() - n.min() + 1e-6)
    return base - amp * n


def draw_far(L, cam, A, rng, V):
    W, H, hy = L.W, L.H, cam.hy
    mx, my, mr = V['moon']
    Esea = cam.Esea
    Xs = np.arange(W, dtype=F)
    # ---- far ridges (behind the strait)
    Zi = cam.Zs + 220.0
    yis = cam.P(0, Zi, Esea + 1)[1]       # the island's shore line
    r0 = ridge(W, rng, hy - 6, 60, 300)
    r1 = ridge(W, rng, hy + 2, 120, 200)
    iend = V['island_end']
    shape = np.clip(1 - (Xs - iend + 200) / 460.0, 0, 1) ** 1.3
    r2 = yis - (yis - (hy + 20 - 70 * vnoise((4, W + 8), 180, rng, 4)[1, :W] * 1.6)) * np.minimum(1, shape * 1.2)
    r2 = np.where(Xs > iend + 260, yis + 4, r2)
    fr = [(r0, mix(K['sky4'], K['haze'], 0.45), 3200), (r1, mix(K['plum'], K['navy2'], 0.55), 1800), (r2, K['navy1'], 600)]
    for ri, (r, col, Zr) in enumerate(fr):
        x0 = 0
        for x in range(W):
            top = int(r[x])
            bot = int(yis + 6)
            if bot > top:
                L.rgb[top:bot, x] = col
                L.a[top:bot, x] = True
        # rim light on the crest from the moon
        for x in range(W):
            top = int(r[x])
            k = clamp(1 - abs(x - mx) / (W * 0.45)) * (0.35 if ri < 2 else 0.5)
            if k > 0.02 and 0 <= top < H:
                L.rgb[top, x] = mix(L.rgb[top, x], K['halo'], k)
        # a mottle of forest on the near island, a nearer spur, and a band of mist low on the slopes
        if ri == 2:
            r3 = np.maximum(r2, yis - (yis - r2) * 0.55 + 18 * vnoise((4, W + 8), 60, rng, 3)[1, :W])
            for x in range(W):
                t3 = int(r3[x])
                if t3 < yis + 6:
                    L.rgb[t3:int(yis + 6), x] = mix(K['navy0'], K['navy1'], 0.5)
                    if 0 <= t3 < H:
                        L.rgb[t3, x] = mix(L.rgb[t3, x], K['plum'], 0.5)
            mist = np.exp(-((np.arange(H)[:, None] - (yis - (yis - r2[None, :]) * 0.62)) / 9.0) ** 2) * 0.35
            mm = L.a & (np.arange(H)[:, None] < yis + 6)
            L.rgb[mm] = mix(L.rgb[mm], K['plum'], mist[mm][:, None])
            nn = vnoise((H, W), 5, rng, octaves=2)
            m = L.a & (np.arange(H)[:, None] >= r2[None, :]) & (np.arange(H)[:, None] < yis + 6)
            L.rgb[m] = mix(L.rgb[m], K['navy2'], (smooth(0.45, 0.7, nn[m]) * 0.3)[:, None])
    # far ridge lights: scattered towns
    farl = []
    for ri, (r, col, Zr) in enumerate(fr):
        n = int(W / (10 if ri == 2 else 22))
        for i in range(n):
            x = int(rng.random() * W)
            if ri == 2 and x > iend + 200:
                continue
            top = r[x]
            depth = (rng.random() ** (2.2 if ri == 2 else 1.4))
            y = int(yis - 2 - depth * (yis - top - 3)) if ri == 2 else int(top + 2 + rng.random() * 6)
            if not (top + 1 < y < yis + 3):
                continue
            c = [K['warm'], K['cream'], K['cool'], K['amber']][int(rng.random() * 4)]
            b = 0.85 if ri == 2 else 0.4
            L.rgb[y, x] = mix(L.rgb[y, x], c, b)
            if ri == 2 and rng.random() < 0.3 and x + 1 < W:
                L.rgb[y, x + 1] = mix(L.rgb[y, x + 1], c, b * 0.6)
            farl.append([x, y])
    # the island's shore road: a string of streetlights
    for x in range(int(rng.random() * 14), min(W, iend + 120), 14 + int(rng.random() * 3)):
        y = int(yis + 1)
        L.rgb[y, x] = K['amber']
        farl.append([x, y])
    A.d['far'] = farl
    # ---- shipyard: gantry cranes and a ship (left)
    sx0, sx1 = V['shipyard']
    if sx1 > 0:
        gx = sx0 + 60
        for k, (cxp, ht, wd) in enumerate([(gx, 150, 120), (gx + 230, 118, 96)]):
            yb = int(yis + 2)
            col = mix(K['navy2'], K['ind'], 0.4)
            for lx in (cxp, cxp + wd):
                L.rect(lx, yb - ht, 4, ht, col)
                L.lines([(lx + 2, yb), (lx + 2 + (12 if lx == cxp else -12), yb - ht * 0.5)], col)
            L.rect(cxp - 20, yb - ht - 10, wd + 44, 10, col)
            for i in range(0, wd + 40, 6):
                L.px(cxp - 20 + i, yb - ht - 6, mix(col, K['halo'], 0.25))
            L.rect(cxp + int(wd * 0.4), yb - ht - 2, 14, 12, mix(col, K['navy1'], 0.5))
            for tx in (cxp - 20, cxp + wd + 23):
                L.px(tx, yb - ht - 11, K['redL'])
                A.d['bridge']['towers'].append(dict(x=tx, y=yb - ht - 11, kind='crane'))
        for k in range(3):
            jx = sx1 - 140 + k * 70
            yb = int(yis + 2)
            L.rect(jx, yb - 70, 3, 70, K['navy2'])
            L.lines([(jx + 1, yb - 68), (jx - 40 + k * 10, yb - 92 - k * 6)], K['navy2'], 2)
            L.px(jx - 40 + k * 10, yb - 93 - k * 6, K['redL'])
        # ship: long hull, white superstructure
        hx, hw_ = sx0 + 20, 420
        yb = int(yis + 4)
        L.poly([(hx, yb - 18), (hx + hw_, yb - 18), (hx + hw_ - 24, yb + 2), (hx + 10, yb + 2)], mix(K['navy1'], K['brn1'], 0.4))
        L.rect(hx + hw_ - 110, yb - 44, 70, 26, mix(K['conc'], K['halo'], 0.25))
        for i in range(6):
            L.rect(hx + hw_ - 104 + i * 11, yb - 38, 6, 3, K['warm'] if rng.random() < 0.6 else K['glass'])
        for i in range(0, hw_ - 40, 9):
            L.px(hx + 14 + i, yb - 20, K['cream'] if rng.random() < 0.5 else K['amber'])
    # ---- the strait
    ytop = int(min(r2.min(), hy) - 2)
    wy0 = hy
    Y = np.arange(H, dtype=F)[:, None]
    base_t = np.clip((Y - wy0) / (H * 0.45), 0, 1)
    wcol = mix(K['water2'], K['water0'], base_t[..., None] ** 0.6) * np.ones((1, W, 1), F)
    rip = vnoise((H // 2 + 2, W // 24 + 2), 6, rng, octaves=3)
    from PIL import Image
    rip = np.asarray(Image.fromarray((rip * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), F) / 255.0
    # sky reflection: lighter plum where the moon's bloom falls
    dx = np.abs(Xs[None, :] - mx)
    refl = np.clip(1 - dx / (W * 0.35), 0, 1) ** 2 * np.clip(1 - (Y - wy0) / (H * 0.5), 0, 1)
    wcol = 1 - (1 - wcol) * (1 - refl[..., None] * K['mag'] * 0.6)
    wcol = mix(wcol, K['water1'], (smooth(0.55, 0.8, rip) * 0.45)[..., None])
    wcol = mix(wcol, K['navy0'], (smooth(0.35, 0.15, rip) * 0.35)[..., None])
    water = np.zeros((H, W), bool)
    water[wy0:, :] = True
    # water only where no land is drawn (the island is in front of its reflection)
    land = L.a.copy()
    wm = water & ~land
    L.rgb[wm] = wcol[wm]
    L.a[wm] = True
    # island reflection: a darker band under the island shore, broken by ripples
    for x in range(0, min(W, iend + 260)):
        h_ = int((yis - r2[x]) * 0.35)
        y0 = int(yis + 6)
        for y in range(y0, min(H, y0 + h_)):
            if rip[y, x] < 0.62:
                L.rgb[y, x] = mix(L.rgb[y, x], K['navy0'], 0.55)
    # moon glitter: broken dashes in a widening column
    gl = []
    for y in range(int(hy + 1), H):
        depth = (y - hy) / (H - hy)
        wd = 6 + depth * 260
        if land[y, int(clamp(mx, 0, W - 1))] and y < yis + 6:
            continue
        nseg = 1 + int(depth * 7)
        for s in range(nseg):
            if rng.random() < 0.45 + depth * 0.2:
                cxp = mx + (rng.random() - 0.5) * 2 * wd * (0.3 + 0.7 * rng.random())
                ln = int(2 + rng.random() * (4 + depth * 26))
                b = clamp((1 - abs(cxp - mx) / (wd + 1)) * (1.05 - depth * 0.7))
                if b < 0.1:
                    continue
                x0 = int(cxp - ln / 2)
                for x in range(max(0, x0), min(W, x0 + ln)):
                    if not land[y, x]:
                        L.rgb[y, x] = mix(L.rgb[y, x], K['moon'] if b > 0.6 else K['halo'], b)
        if y % 4 == 0:
            gl.append(y)
    A.d['water'].append(dict(x=0, y=int(hy), w=W, h=int(H - hy), moonPath=dict(x=int(mx), y0=int(hy), y1=H, w0=6, w1=266)))
    # light columns under the island lights
    for (x, y) in farl[::2]:
        if y > yis - 30:
            for k in range(int(4 + rng.random() * 18)):
                yy = int(yis + 7 + k * 2 + rng.random() * 2)
                if yy < H and rip[yy, x] > 0.45:
                    L.rgb[yy, x] = mix(L.rgb[yy, x], K['amber'], 0.45 * (1 - k / 22))
    # ---- the bridge (cable-stayed, two towers), crossing the strait from our shore to the island
    xa_s, xb_s = V['bridge']
    ZA, ZB = cam.Zs + 25.0, Zi - 5.0
    XA, XB = cam.Xat(xa_s, ZA), cam.Xat(xb_s, ZB)
    Ed = Esea + 28.0
    bcol = mix(K['navy1'], K['ind'], 0.35)
    bhi = mix(K['ind'], K['halo'], 0.4)
    ax_, az_ = XA, ZA
    Lb = math.hypot(XB - XA, ZB - ZA)
    ux, uz = (XB - XA) / Lb, (ZB - ZA) / Lb          # along the deck
    nx, nz = -uz, ux                                   # across

    def BP(t, off=0.0, e=0.0):
        X = XA + ux * t + nx * off
        Z = ZA + uz * t + nz * off
        return cam.P(X, Z, Ed + e)

    def BPs(t, off=0.0, e=0.0):
        X = XA + ux * t + nx * off
        Z = ZA + uz * t + nz * off
        return cam.P(X, Z, Esea + e)
    # piers first (they stand in the water)
    for t in np.arange(30.0, Lb, 55.0):
        (x0, y0) = BP(t, 0, -1.5)
        (_, y1) = BPs(t, 0, 0)
        Z = ZA + uz * t
        w = max(2, cam.f * 3.0 / Z)
        L.rect(x0 - w / 2, y0, w, y1 - y0, bcol)
        L.rect(x0 + w / 2 - 1, y0, 1, y1 - y0, bhi)
        for k in range(int((y1 - y0) * 0.6)):
            yy = int(y1 + 2 + k)
            if yy < H and rng.random() < 0.6:
                L.px(x0 + math.sin(k * 0.5) * 2, yy, mix(K['navy0'], K['water1'], 0.3))
    # the deck: a ribbon with a girder edge and a moonlit rail
    for t in np.arange(0.0, Lb, 0.25):
        (x0, yt) = BP(t, 0, 0.0)
        (_, yb) = BP(t, 0, -2.6)
        (_, yr) = BP(t, 0, 1.2)
        L.rect(x0, yr, 1.2, yb - yr + 1, bcol)
        L.px(x0, yr, bhi)
        L.px(x0, yb, mix(bcol, K['navy0'], 0.5))
    towers = []
    for tf in V['towers']:
        t = tf * Lb
        Z = ZA + uz * t
        top_e = 62.0
        legs = []
        for side in (-1, 1):
            (x0, y0) = BPs(t, side * 9.0, 0)
            (x1, y1) = BP(t, side * 1.2, top_e - 28.0)
            legs.append(((x0, y0), (x1, y1)))
            lw = max(2, cam.f * 1.8 / Z)
            L.poly([(x0 - lw / 2, y0), (x0 + lw / 2, y0), (x1 + lw / 3, y1), (x1 - lw / 3, y1)], bcol)
            L.lines([(x0 + lw / 2, y0), (x1 + lw / 3, y1)], bhi)
        (cx0, cy0) = BP(t, 0, top_e - 28.0)
        (cx1, cy1) = BP(t, 0, top_e)
        lw = max(2, cam.f * 2.0 / Z)
        L.rect(cx1 - lw / 2, cy1, lw, cy0 - cy1, bcol)
        L.rect(cx1 + lw / 2 - 1, cy1, 1, cy0 - cy1, bhi)
        # cross beam below the deck
        (b0x, b0y) = BP(t, -8.0, -4.0)
        (b1x, b1y) = BP(t, 8.0, -4.0)
        L.lines([(b0x, b0y), (b1x, b1y)], bcol, width=max(1, int(lw / 2)))
        L.px(cx1, cy1 - 1, mix(K['red'], K['navy1'], 0.3))
        A.d['bridge']['towers'].append(dict(x=int(cx1), y=int(cy1) - 1, kind='tower'))
        towers.append((t, Z))
    # stay cables: two fans per tower, both planes of cables
    ccol = mix(K['navy2'], K['halo'], 0.22)
    for (t, Z) in towers:
        for side in (-1, 1):
            for i in range(1, 9):
                d = side * (8 + i * 11.0)
                if not (0 < t + d < Lb):
                    continue
                e_top = 60.0 - 2.0 - i * 2.2
                p0 = BP(t, 0, e_top)
                p1 = BP(t + d, 0, 0.8)
                # cables are thin: draw them as a sparse dotted line so they shimmer, not cage
                n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1])))
                for k in range(0, n, 1):
                    if (k + i) % 3 == 0:
                        continue
                    L.px(p0[0] + (p1[0] - p0[0]) * k / n, p0[1] + (p1[1] - p0[1]) * k / n, ccol)
                A.d['bridge']['cables'].append([int(p0[0]), int(p0[1]), int(p1[0]), int(p1[1])])
    # deck lights along both rails (fixtures dim; bright bulbs are the life lane's)
    bl = []
    for t in np.arange(4.0, Lb, 16.0):
        for side in (-1,):
            (x, y) = BP(t, side * 7.5, 1.6)
            L.px(int(x), int(y), mix(K['amber'], K['navy1'], 0.2))
            bl.append([int(x), int(y)])
            (_, ys) = BPs(t, side * 7.5, 0)
            Z = ZA + uz * t
            n = int(cam.f * 9 / Z)
            for k in range(n):
                yy = int(ys + 2 + k * 1.5 + rng.random() * 2)
                if 0 <= yy < H and 0 <= int(x) < W and rip[yy, int(x)] > 0.45:
                    L.rgb[yy, int(x)] = mix(L.rgb[yy, int(x)], K['amber'], 0.4 * (1 - k / n))
    A.d['bridge']['lights'] = bl
    (dax, day), (dbx, dby) = BP(0), BP(Lb)
    A.d['bridge']['deck'] = [int(dax), int(day), int(dbx), int(dby)]
    # a far second bridge: a faint string of lights at the horizon right
    for i in range(0, 220, 5):
        x = iend + 380 + i
        if x < W:
            L.px(x, int(hy + 2 - i * 0.01), mix(K['amber'], K['sky4'], 0.5))
    # ---- boats on the water
    boats = []
    for i in range(4 if W > 2000 else 2):
        bx_ = int(W * (0.25 + 0.7 * rng.random()))
        Zb = 230 + rng.random() * 200
        x0, y0 = cam.P(cam.Xat(bx_, Zb), Zb, Esea)
        s = 260 / Zb
        if land[int(y0), int(clamp(x0, 0, W - 1))]:
            continue
        wb = int(30 * s)
        L.poly([(x0 - wb, y0 - 4 * s), (x0 + wb, y0 - 4 * s), (x0 + wb - 4, y0 + 1), (x0 - wb + 3, y0 + 1)], K['navy0'])
        L.rect(x0 - wb * 0.2, y0 - 10 * s, wb * 0.6, 6 * s, mix(K['conc'], K['halo'], 0.2))
        L.px(int(x0 + wb * 0.1), int(y0 - 8 * s), K['warm'])
        L.lines([(x0 - wb * 0.5, y0 - 4 * s), (x0 - wb * 0.5, y0 - 26 * s)], K['navy1'])
        L.px(int(x0 - wb * 0.5), int(y0 - 27 * s), K['cream'])
        for k in range(14):
            yy = int(y0 + 4 + k * 2)
            if yy < H:
                L.px(int(x0 + wb * 0.1), yy, mix(L.rgb[yy, int(x0 + wb * 0.1)], K['warm'], 0.4 * (1 - k / 14)))
        boats.append(dict(x=int(x0), y=int(y0), w=int(wb * 2), path=[[int(x0 - 400), int(y0)], [int(x0 + 400), int(y0)]]))
    A.d['boats'] = boats
    # oyster rafts: dark lattices low on the water, a marker light at a corner
    for i in range(7 if W > 2000 else 4):
        Zr = cam.Zs + 40 + rng.random() * 150
        Xc = cam.Xat(rng.random() * W, Zr)
        wX, wZ = 14 + rng.random() * 14, 8 + rng.random() * 8
        c0 = cam.P(Xc, Zr, Esea + 0.3)
        if not (0 <= c0[0] < W) or land[int(min(H - 1, c0[1])), int(c0[0])] or abs(c0[0] - mx) < 160:
            continue
        rc = mix(K['navy0'], K['brn0'], 0.4)
        for k in range(7):
            z = Zr + wZ * k / 6
            L.lines([cam.P(Xc, z, Esea + 0.3), cam.P(Xc + wX, z, Esea + 0.3)], rc)
        for k in range(9):
            x = Xc + wX * k / 8
            L.lines([cam.P(x, Zr, Esea + 0.3), cam.P(x, Zr + wZ, Esea + 0.3)], rc)
        (lx, ly) = cam.P(Xc + wX, Zr, Esea + 1.2)
        L.px(lx, ly, mix(K['amber'], K['red2'], 0.3))
        A.d['far'].append([int(lx), int(ly)])
    # squid boats far out to the right: hard white-green lamps on the horizon, and their long reflections
    for i in range(3 if W > 2000 else 2):
        x = int(min(W - 20, V['island_end'] + 140 + rng.random() * (W - V['island_end'])))
        y = int(hy + 3 + rng.random() * 6)
        if x >= W - 10:
            continue
        L.rect(x - 6, y, 13, 2, K['navy0'])
        for k in range(5):
            L.px(x - 5 + k * 3, y - 2, K['fluo'])
        for k in range(30):
            yy = y + 3 + k * 2
            if yy < H:
                L.px(x + int(math.sin(k) * 2), yy, mix(L.rgb[yy, x], K['fluo'], 0.5 * (1 - k / 30)))
        boats.append(dict(x=x, y=y, w=13, kind='squid', path=[[x, y], [x + 30, y]]))
    # ferry path: from our shore pier to the island
    return yis, land


def draw_shore(L, cam, A, rng, V, lights):
    """quay, shore road, pier, shore buildings, the railway (all in the far layer: the train runs behind the town)."""
    W, H, hy = L.W, L.H, cam.hy
    Zq = cam.Zs
    Eq = cam.g(Zq)
    Esea = cam.Esea
    Xl, Xr = cam.Xat(-40, Zq), cam.Xat(W + 40, Zq)
    # quay face
    for Z, E0, E1, col in [(Zq + 2, Esea, Eq, mix(K['stone'], K['haze'], 0.35))]:
        x0, y0 = cam.P(Xl, Z, E1)
        x1, y1 = cam.P(Xr, Z, E0)
        L.rect(-2, y0, W + 4, y1 - y0 + 1, col)
        L.rect(-2, y0, W + 4, 1, mix(K['stoneH'], K['halo'], 0.2))
    # road surface (wet: reflective)
    yq = cam.P(0, Zq + 2, Eq)[1]
    yb = cam.P(0, 128, cam.g(128))[1]
    L.rect(-2, int(yq), W + 4, int(H - yq), mix(K['navy1'], K['plum'], 0.25))
    # ferry pier and moored boats near the quay
    px_ = int(cam.cx - 140 if W > 2000 else W * 0.28)
    pz = Zq + 14
    Xp = cam.Xat(px_, Zq)
    pp = [cam.P(Xp, Zq + 2, Eq - 0.6), cam.P(Xp + 3, Zq + 2, Eq - 0.6), cam.P(Xp + 3, pz, Eq - 0.6), cam.P(Xp, pz, Eq - 0.6)]
    L.poly(pp, mix(K['navy1'], K['stone'], 0.5))
    L.lines([pp[1], pp[2]], mix(K['stoneH'], K['halo'], 0.2))
    for k in range(1, 4):
        bx_, by_ = cam.P(Xp + 3, Zq + 2 + k * 3, Eq - 0.4)
        L.px(bx_, by_ - 1, mix(K['stoneH'], K['halo'], 0.4))
    # pier pylons in the water
    for k in range(4):
        bx_, by_ = cam.P(Xp + 1.5, Zq + 3 + k * 3.5, Eq - 0.6)
        L.rect(bx_, by_ + 1, 1, 4, K['navy0'])
    fx, fy = pp[2]
    fy = int(fy) + 1
    # moored ferry
    fw = 46
    L.poly([(fx - 8, fy - 7), (fx + fw, fy - 7), (fx + fw - 6, fy + 2), (fx - 4, fy + 2)], mix(K['navy0'], K['brn1'], 0.3))
    L.rect(fx, fy - 14, fw - 14, 7, mix(K['conc'], K['halo'], 0.3))
    for i in range(5):
        L.rect(fx + 2 + i * 6, fy - 12, 4, 3, K['warm'] if i != 2 else K['cool'])
    L.px(int(fx + fw - 18), int(fy - 17), K['cream'])
    A.d['ferry'] = dict(dock=[int(fx), int(fy)], path=[[int(fx), int(fy)], [int(fx + 120), int(fy - 60)], [int(fx + 260), int(cam.hy + 60)]])
    # pier lamp
    lights.append(dict(x=fx - 6, y=fy - 24, r=26, col=K['amber'], k=0.35, layer='far', kind='pier'))
    L.rect(fx - 7, fy - 24, 1, 22, K['navy0'])
    L.px(int(fx - 6), int(fy - 25), K['warm'])
    # fishing boats against the quay
    for i in range(int(W / 220)):
        x = int(rng.random() * W)
        y = int(cam.P(0, Zq + 6, Esea)[1])
        if abs(x - px_) < 90:
            continue
        L.poly([(x, y - 3), (x + 16, y - 3), (x + 13, y + 1), (x + 2, y + 1)], K['navy0'])
        L.rect(x + 9, y - 7, 4, 4, mix(K['conc'], K['haze'], 0.3))
        L.lines([(x + 4, y - 3), (x + 4, y - 15)], K['navy1'])
        if rng.random() < 0.3:
            L.px(x + 10, y - 6, K['warm'])
    # shore road streetlights (tall, cool and warm)
    for i, x in enumerate(range(int(rng.random() * 60), W, 110)):
        y0 = cam.P(0, Zq - 1, Eq)[1]
        h = 26
        L.rect(x, int(y0 - h), 1, h, K['navy0'])
        L.rect(x, int(y0 - h), 4, 1, K['navy0'])
        L.px(x + 4, int(y0 - h + 1), K['cream'])
        lights.append(dict(x=x + 4, y=y0 - h + 1, r=30, col=K['amber'] if i % 3 else K['fluo'], k=0.30, layer='far', kind='street', pool=(x + 4, y0)))
    # shore buildings between road and rail: low warehouses, the arcade, a lit shop
    zrow = Zq - 3
    x = -30
    shop_done = False
    while x < W + 30:
        w = int(30 + rng.random() * 70)
        h = int(14 + rng.random() * 26)
        Z = zrow - rng.random() * 3
        y0 = cam.P(0, Z, cam.g(Z))[1]
        kind = rng.random()
        col = fz([K['conc'], K['plaster'], K['brn2'], K['mortar']][int(rng.random() * 4)], Z)
        if kind < 0.18 and x > W * 0.1:
            # arcade roof: a long low vault with a lit seam
            ln = int(200 + rng.random() * 200)
            L.rect(x, int(y0 - 12), ln, 12, mix(K['navy2'], K['haze'], 0.2))
            L.rect(x, int(y0 - 13), ln, 1, mix(K['halo'], K['haze'], 0.5))
            for k in range(x, x + ln, 7):
                L.px(k, int(y0 - 7), mix(K['navy2'], K['halo'], 0.25))
            L.rect(x, int(y0 - 2), ln, 2, mix(K['warm2'], K['navy1'], 0.3))
            lights.append(dict(x=x + ln / 2, y=y0 - 1, r=ln * 0.6, ry=12, col=K['warm2'], k=0.25, layer='far', kind='arcade'))
            x += ln + 6
            continue
        L.rect(x, int(y0 - h), w, h, col)
        L.rect(x - 1, int(y0 - h - 2), w + 2, 2, mix(col, K['navy0'], 0.5))
        # rows of tiny windows
        for wy in range(int(y0 - h + 4), int(y0 - 4), 7):
            for wx in range(x + 3, x + w - 4, 7):
                if rng.random() < 0.25:
                    c = [K['warm'], K['cream'], K['tv']][int(rng.random() * 3)]
                    L.rect(wx, wy, 3, 3, c)
                    wi = A.win(wx, wy, 3, 3, 1, 1, 'warm', 0, 'plain', 'far', K['glass'])
                    if L.wid is not None and wx >= 0 and wy >= 0:
                        L.wid[wy:wy + 3, wx:wx + 3] = wi
                elif rng.random() < 0.4:
                    L.rect(wx, wy, 3, 3, K['glass'])
        if not shop_done and abs(x - cam.cx) < 500 and x > cam.cx - 420:
            # a small lit shop, no brand: a band of cool white with shelves
            sw = 40
            L.rect(x + 4, int(y0 - 11), sw, 9, K['cool'])
            for k in range(3):
                L.rect(x + 6 + k * 13, int(y0 - 9), 9, 1, mix(K['cool'], K['tv2'], 0.6))
            L.rect(x + 4, int(y0 - 14), sw, 3, mix(K['green'], K['cool'], 0.3))
            A.d['shop'] = dict(x=x + 4, y=int(y0 - 14), w=sw, h=12, layer='far')
            lights.append(dict(x=x + 24, y=y0 - 2, r=60, ry=20, col=K['cool'], k=0.35, layer='far', kind='shop'))
            shop_done = True
        elif rng.random() < 0.3:
            # vertical sign
            sx = x + w - 6
            sh = 14
            sc = [K['pinkL'], K['cream'], K['warm']][int(rng.random() * 3)]
            L.rect(sx, int(y0 - h - 2), 4, sh, sc)
            for k in range(3):
                L.px(sx + 1 + (k % 2), int(y0 - h + k * 4), mix(sc, K['navy0'], 0.7))
            A.d['signs'].append(dict(x=sx, y=int(y0 - h - 2), w=4, h=sh, layer='far', neon=sc is K['pinkL']))
        x += w + int(rng.random() * 12)
    # the railway at the foot of the hill
    Zr = cam.Zs - 7.0
    Er = cam.g(Zr)
    yr = cam.P(0, Zr, Er)[1]
    yr2 = cam.P(0, Zr - 3, cam.g(Zr - 3))[1]
    L.rect(-2, int(yr) - 1, W + 4, int(yr2 - yr) + 4, mix(K['stone'], K['navy1'], 0.4))
    for x in range(0, W, 3):
        L.px(x, int(yr) + 1, mix(K['stoneH'], K['halo'], 0.15))
    L.rect(-2, int(yr) + 1, W + 4, 1, mix(K['halo'], K['stone'], 0.35))
    L.rect(-2, int(yr) + 3, W + 4, 1, mix(K['halo'], K['stone'], 0.45))
    # catenary poles and the wire
    pts = []
    for x in range(int(rng.random() * 40), W + 60, 90):
        L.rect(x, int(yr - 30), 2, 31, mix(K['navy1'], K['ind'], 0.3))
        L.rect(x - 2, int(yr - 28), 12, 1, mix(K['navy1'], K['ind'], 0.3))
        pts.append((x + 9, yr - 27))
    L.lines([(-4, yr - 25)] + [(p[0], p[1] + 2) for p in pts], mix(K['ind'], K['halo'], 0.25))
    A.d['train'] = dict(path=[[-200, int(yr)], [W + 200, int(yr)]], y=int(yr), car=int(64 * L.W / 2560 + 30), h=10, layer='far')
    A.d['wires'].append(dict(pts=[[int(p[0]), int(p[1] + 2)] for p in pts], layer='far', kind='catenary'))
    return yr


# ================================================================== houses (mid + near)
def tile_roof_col(q, Z, rows, cols, base, hi, shade):
    """colour function for a roof quad: q = (eaveL, eaveR, ridgeR, ridgeL) screen pts"""
    (exl, ey), (exr, _), (rxr, ry), (rxl, _) = q

    def f(X, Y):
        v = np.clip((ey - Y) / max(1e-3, ey - ry), 0, 1)       # 0 at eave, 1 at ridge
        xl = exl + (rxl - exl) * v
        xr = exr + (rxr - exr) * v
        u = np.clip((X - xl) / np.maximum(1e-3, xr - xl), 0, 1)
        cu = (u * cols) % 1.0
        rv = (v * rows) % 1.0
        ch = 0.45 + 0.55 * np.sin(cu * math.pi)            # rounded tile channels
        rowline = (rv < 1.0 / max(2, (ey - ry) / rows)) * 1.0
        c = base * (shade * (0.75 + 0.35 * ch))[..., None]
        c = mix(c, hi, (v ** 3 * 0.35 * ch)[..., None])     # wet sheen near the ridge
        c = mix(c, K['navy0'], (rowline * 0.7)[..., None])
        return fz(c, Z) if True else c
    return f


class Town:
    def __init__(s, cam, A, rng, V, lights):
        s.cam, s.A, s.rng, s.V, s.lights = cam, A, rng, V, lights
        s.ops = []   # (Z, layer, fn)

    def add(s, Z, layer, fn):
        s.ops.append((Z, layer, fn))

    # -------------------------------------------- a window
    def window(s, L, x, y, w, h, Z, layer, lit_p=0.4, kind=None):
        rng = s.rng
        x, y, w, h = int(round(x)), int(round(y)), max(2, int(round(w))), max(2, int(round(h)))
        if x + w < 0 or x >= L.W or y + h < 0 or y >= L.H:
            return
        fr = fz(K['frame'], Z)
        lit = rng.random() < lit_p
        baked = lit and rng.random() < 0.7
        hue = 'warm'
        r = rng.random()
        if r < 0.12:
            hue = 'tv'
        elif r < 0.2:
            hue = 'cool'
        elif r < 0.24:
            hue = 'pink'
        curtain = rng.random() < 0.45
        room = ROOMS[int(rng.random() * 3)] if hue != 'tv' else 'tv'
        dark = fz(mix(K['glass'], K['glass2'], rng.random() * 0.5), Z)
        if w >= 4 and h >= 4:
            L.rect(x - 1, y - 1, w + 2, h + 2, fr)
        if baked:
            base = {'warm': K['warm'], 'tv': K['tv'], 'cool': K['cool'], 'pink': K['pinkL']}[hue]
            inner = mix(base, K['warm3'] if hue == 'warm' else K['tv2'], 0.45)
            dim = 0.55 + 0.45 * rng.random()

            def col(X, Y, base=base, inner=inner, dim=dim):
                v = (Y - y) / max(1, h)
                c = mix(base, inner, np.clip(v * 0.9, 0, 1)[..., None]) * dim
                return c
            L.rect(x, y, w, h, col)
            if L.lock is not None:
                L.lock[max(0, y):max(0, y + h), max(0, x):max(0, x + w)] = True
            # interior stories, depending on size
            if w >= 6 and h >= 6:
                st = rng.random()
                cc = mix(K['cream'], K['warm2'], rng.random()) * dim
                if curtain:
                    pw = max(1, int(w * (0.25 + 0.2 * rng.random())))
                    for side in ([0, 1] if rng.random() < 0.6 else [int(rng.random() * 2)]):
                        cx0 = x if side == 0 else x + w - pw
                        for k in range(pw):
                            fold = 0.8 + 0.2 * ((k % 3) == 0)
                            L.rect(cx0 + k, y, 1, h, cc * fold)
                if st < 0.2 and h >= 8:
                    # shoji lattice
                    gc = mix(base, K['brn2'], 0.6) * dim
                    for gx in range(x + w // 3, x + w, max(3, w // 3)):
                        L.rect(gx, y, 1, h, gc)
                    for gy in range(y + h // 4, y + h, max(3, h // 4)):
                        L.rect(x, gy, w, 1, gc)
                elif st < 0.35:
                    # blinds
                    for gy in range(y + 1, y + h, 2):
                        L.rect(x, gy, w, 1, mix(inner, K['brn2'], 0.3) * dim)
                elif st < 0.55:
                    # a plant on the sill
                    pw = max(3, w // 3)
                    px0 = x + int(rng.random() * (w - pw))
                    ph = max(2, h // 3)
                    for k in range(pw * ph):
                        dx_, dy_ = k % pw, k // pw
                        if rng.random() < 0.7 - dy_ / ph * 0.3:
                            L.px(px0 + dx_, y + h - 1 - dy_, mix(K['leaf'], K['moss'], rng.random() * 0.5))
                elif st < 0.62 and h >= 10:
                    # someone's silhouette
                    sx = x + int(w * (0.3 + 0.4 * rng.random()))
                    hr = max(1, h // 8)
                    L.ellipse(sx, y + h * 0.45, hr, hr * 1.2, mix(inner, K['navy0'], 0.75))
                    L.rect(sx - hr * 2, int(y + h * 0.45 + hr), hr * 4, int(h * 0.55 - hr), mix(inner, K['navy0'], 0.75))
                elif st < 0.7:
                    # a hanging lamp
                    L.rect(x + w // 2, y, 1, h // 3, mix(inner, K['navy0'], 0.6))
                    L.rect(x + w // 2 - 1, y + h // 3, 3, 2, K['cream'])
            # mullions
            if w >= 5:
                L.rect(x + w // 2, y, 1, h, fr)
            if h >= 10 and rng.random() < 0.5:
                L.rect(x, y + h // 2, w, 1, fr)
            # light spill on the sill and the wall below
            s.lights.append(dict(x=x + w / 2, y=y + h, r=max(4, w * 1.1), ry=max(3, h * 0.8), col=base * 0.6, k=0.18, layer=layer, kind='spill', air=False))
        else:
            def col(X, Y, dark=dark):
                v = (X - x + (Y - y) * 0.6) / max(1, w + h)
                streak = (np.abs(((v * 3) % 1.0) - 0.5) < 0.08) * 0.25
                return mix(dark, K['halo'] * 0.5, streak[..., None])
            L.rect(x, y, w, h, col)
            if w >= 5:
                L.rect(x + w // 2, y, 1, h, fr)
        wid = s.A.win(x, y, w, h, 1 if lit else 0, 1 if baked else 0, hue, curtain, room, layer, dark)
        if L.wid is not None:
            L.wid[max(0, y):max(0, y + h), max(0, x):max(0, x + w)] = wid

    # -------------------------------------------- a house
    def house(s, L, X0, X1, Z, D, hw, roof, layer, wall=None, rkind='tile'):
        cam, rng = s.cam, s.rng
        Zf, Zb, Zm = Z, Z + D, Z + D / 2
        Xl_ = cam.lane(Zf)
        dl = min(abs(X0 - Xl_), abs(X1 - Xl_)) if not (X0 < Xl_ < X1) else 0.0
        Eg = cam.g(Zf) - min(5.0, 0.22 * max(0.0, dl - 2.5)) * clamp(1.2 - Zf / 90.0)
        P = cam.P
        wall = wall if wall is not None else [K['plaster'], K['plaster2'], K['conc'], K['brn1'], K['brn2'], K['mortar']][int(rng.random() * 6)]
        wallc = fz(wall, Z)
        unit = cam.f / Zf               # px per metre at the front face
        # side walls first (seen from the lane / the eye)
        hr = {'gable': 1.6 + rng.random() * 0.8, 'hip': 1.4 + rng.random() * 0.6, 'flat': 0.0, 'shed': 0.8}[roof]
        o = 0.45
        side_col = fz(mix(wall, K['navy0'], 0.35), Z)
        lit_side = fz(mix(wall, K['halo'], 0.12), Z)
        if X1 < 0:      # we see the right side
            q = [P(X1, Zf, Eg), P(X1, Zb, Eg), P(X1, Zb, Eg + hw), P(X1, Zf, Eg + hw)]
            L.poly(q, lit_side)
            if roof == 'gable':
                L.poly([P(X1, Zf, Eg + hw), P(X1, Zb, Eg + hw), P(X1, Zm, Eg + hw + hr)], lit_side)
        if X0 > 0:
            q = [P(X0, Zf, Eg), P(X0, Zb, Eg), P(X0, Zb, Eg + hw), P(X0, Zf, Eg + hw)]
            L.poly(q, side_col)
            if roof == 'gable':
                L.poly([P(X0, Zf, Eg + hw), P(X0, Zb, Eg + hw), P(X0, Zm, Eg + hw + hr)], side_col)
        # windows on the visible side wall, in perspective
        Xs_ = X1 if X1 < 0 else (X0 if X0 > 0 else None)
        if Xs_ is not None and unit > 6:
            nfl = max(1, int(hw / 2.7))
            for fl in range(nfl):
                Ew = Eg + fl * (hw / nfl) + 0.9
                for k in range(max(1, int(D / 3.2))):
                    if rng.random() < 0.35:
                        continue
                    Zc = Zf + (k + 0.5) * D / max(1, int(D / 3.2))
                    q = [P(Xs_, Zc - 0.4, Ew + 1.0), P(Xs_, Zc + 0.4, Ew + 1.0), P(Xs_, Zc + 0.4, Ew), P(Xs_, Zc - 0.4, Ew)]
                    lit = rng.random() < 0.4
                    col = mix(K['warm'], K['warm3'], rng.random() * 0.5) * (0.6 + 0.3 * rng.random()) if lit else fz(K['glass'], Z)
                    L.poly(q, col)
                    L.lines([q[0], q[1], q[2], q[3], q[0]], fz(K['frame'], Z))
                    xs_ = [p_[0] for p_ in q]; ys_ = [p_[1] for p_ in q]
                    if lit:
                        L.lock[int(max(0, min(ys_))):int(max(0, max(ys_))), int(max(0, min(xs_))):int(max(0, max(xs_)))] = True
        # front wall
        (x0, yb), (x1, yt) = P(X0, Zf, Eg), P(X1, Zf, Eg + hw)
        grime = s.rng.random() * 0.4

        def wcol(X, Y, wallc=wallc, x0=x0, yt=yt, yb=yb):
            v = np.clip((Y - yt) / max(1, yb - yt), 0, 1)
            streak = np.sin(X * 0.9 + np.sin(X * 0.13) * 3) * 0.5 + 0.5
            c = wallc * (0.85 + 0.25 * (1 - v))[..., None]
            c = mix(c, K['navy0'], (streak * grime * v * 0.5)[..., None])
            return c
        L.rect(x0, yt, x1 - x0, yb - yt, wcol)
        # wood-board texture for old houses
        if wall is K['brn1'] or wall is K['brn2']:
            step = max(2, int(unit * 0.18))
            for yy in range(int(yt) + step, int(yb), step):
                L.rect(x0, yy, x1 - x0, 1, fz(mix(wall, K['navy0'], 0.45), Z))
        # floors & windows
        floors = max(1, int(hw / 2.7))
        fh = hw / floors
        ww = (0.8 + rng.random() * 0.6)
        whh = 0.9 + rng.random() * 0.3
        nwin = max(1, int((X1 - X0) / 1.7))
        lit_p = 0.5
        for fl in range(floors):
            Ewin = Eg + fl * fh + fh * 0.35
            for i in range(nwin):
                if rng.random() < 0.18:
                    continue
                Xc = X0 + (i + 0.5) * (X1 - X0) / nwin + (rng.random() - 0.5) * 0.3
                (wx, wy) = P(Xc - ww / 2, Zf, Ewin + whh)
                (wx2, wy2) = P(Xc + ww / 2, Zf, Ewin)
                s.window(L, wx, wy, wx2 - wx, wy2 - wy, Zf, layer, lit_p)
                # balcony / laundry pole on upper floors
                if fl >= 1 and rng.random() < 0.12 and unit > 9:
                    (bx0, by0) = P(Xc - ww, Zf, Ewin - 0.05)
                    (bx1, by1) = P(Xc + ww, Zf, Ewin - 0.05)
                    L.rect(bx0, by0, bx1 - bx0, max(1, unit * 0.06), fz(K['conc'], Z, 0.1))
                    # laundry pole above the window
                    (lx0, ly) = P(Xc - ww * 1.2, Zf - 0.4, Ewin + whh + 0.25)
                    (lx1, _) = P(Xc + ww * 1.2, Zf - 0.4, Ewin + whh + 0.25)
                    L.rect(lx0, ly, lx1 - lx0, 1, fz(mix(K['conc'], K['halo'], 0.3), Z))
                    s.A.d['laundry'].append(dict(x=int(lx0), y=int(ly), w=int(lx1 - lx0), h=int(unit * 0.6), layer=layer))
                    n = int(rng.random() * 4)
                    for k in range(n):
                        cxp = lx0 + (k + 0.5) * (lx1 - lx0) / max(1, n)
                        cw = max(2, unit * (0.25 + rng.random() * 0.3))
                        chh = max(2, unit * (0.3 + rng.random() * 0.4))
                        cc = fz([K['cream'], K['pink'], K['tv2'], K['halo'], K['mag']][int(rng.random() * 5)] * 0.6, Z)
                        L.rect(cxp - cw / 2, ly + 1, cw, chh, cc)
                # AC unit beside the window
                if rng.random() < 0.18 and unit > 7:
                    (ax_, ay_) = P(Xc + ww / 2 + 0.25, Zf - 0.25, Ewin + 0.55)
                    aw, ah = unit * 0.75, unit * 0.55
                    if ax_ + aw < x1:
                        L.rect(ax_, ay_, aw, ah, fz(mix(K['conc'], K['halo'], 0.25), Z))
                        L.rect(ax_, ay_ + ah - 1, aw, 1, fz(K['navy0'], Z))
                        if aw > 6:
                            L.ellipse(ax_ + aw * 0.62, ay_ + ah * 0.5, aw * 0.25, ah * 0.32, fz(K['navy1'], Z))
                            for k in range(1, int(aw * 0.35), 2):
                                L.px(ax_ + 1 + k, ay_ + ah * 0.5, fz(K['navy1'], Z))
                        L.lines([(ax_ + aw * 0.1, ay_ + ah), (ax_ + aw * 0.1, ay_ + ah + unit * 0.5)], fz(K['navy0'], Z))
                        s.A.d['ac'].append(dict(x=int(ax_ + aw * 0.1), y=int(ay_ + ah + unit * 0.5), layer=layer))
        # small facade clutter: downpipe, meter box, vents, a sudare blind, a sign
        if unit > 7:
            pc = fz(mix(K['conc'], K['navy0'], 0.3), Z)
            if rng.random() < 0.7:
                Xp_ = X0 + 0.15 if rng.random() < 0.5 else X1 - 0.25
                (gx, gy0) = P(Xp_, Zf - 0.1, Eg + hw)
                (_, gy1) = P(Xp_, Zf - 0.1, Eg)
                L.rect(gx, gy0, max(1, unit * 0.08), gy1 - gy0, pc)
                L.rect(gx - 1, gy1 - max(1, unit * 0.1), max(2, unit * 0.2), max(1, unit * 0.1), pc)
            if rng.random() < 0.5:
                Xm = X0 + (X1 - X0) * rng.random()
                (mx0, my0) = P(Xm, Zf - 0.05, Eg + 1.6)
                L.rect(mx0, my0, max(2, unit * 0.3), max(2, unit * 0.4), fz(mix(K['conc'], K['halo'], 0.3), Z))
                L.px(mx0 + max(1, unit * 0.1), my0 + max(1, unit * 0.15), fz(K['navy0'], Z))
            if rng.random() < 0.4:
                Xv = X0 + (X1 - X0) * rng.random()
                (vx, vy) = P(Xv, Zf - 0.05, Eg + hw - 0.5)
                vr = max(1, unit * 0.13)
                L.ellipse(vx, vy, vr, vr, fz(K['navy0'], Z))
                L.ellipse(vx, vy, vr * 0.5, vr * 0.5, fz(K['conc'], Z))
                s.A.d['vents'].append(dict(x=int(vx), y=int(vy), kind='fan', layer=layer))
            if rng.random() < 0.2 and unit > 12:
                # a reed blind leaning against the wall
                Xs_ = X0 + (X1 - X0) * (0.1 + 0.6 * rng.random())
                (sx0, sy0) = P(Xs_, Zf - 0.2, Eg + 1.8)
                (sx1, sy1) = P(Xs_ + 1.0, Zf - 0.2, Eg)
                for k in range(int(sy0), int(sy1)):
                    L.rect(sx0 + (k - sy0) * 0.1, k, sx1 - sx0, 1, fz(mix(K['brn3'], K['brn1'], (k % 2) * 0.6), Z))
            if rng.random() < 0.08 and unit > 10:
                # a small shop sign, unreadable glyphs
                (sx0, sy0) = P(X0 + 0.3, Zf - 0.15, Eg + hw - 0.3)
                sw, sh = unit * 0.45, unit * 1.3
                sc = [K['cream'], K['pinkL'], K['amber']][int(rng.random() * 3)]
                L.rect(sx0, sy0, sw, sh, mix(sc, K['navy0'], 0.15))
                for k in range(4):
                    gy = sy0 + 2 + k * (sh - 3) / 4
                    L.rect(sx0 + sw * 0.25 + (k % 2), gy, sw * 0.5, max(1, sh * 0.08), mix(sc, K['navy0'], 0.7))
                L.lock[int(max(0, sy0)):int(max(0, sy0 + sh)), int(max(0, sx0)):int(max(0, sx0 + sw))] = True
                s.lights.append(dict(x=sx0 + sw / 2, y=sy0 + sh / 2, r=unit * 1.6, col=sc, k=0.25, layer=layer, kind='sign'))
                s.A.d['signs'].append(dict(x=int(sx0), y=int(sy0), w=int(sw), h=int(sh), layer=layer, neon=sc is K['pinkL']))
        # entrance: a door with a little porch light
        if rng.random() < 0.55 and unit > 6:
            Xd = X0 + (X1 - X0) * (0.2 + rng.random() * 0.6)
            (dx0, dy0) = P(Xd - 0.45, Zf, Eg + 2.0)
            (dx1, dy1) = P(Xd + 0.45, Zf, Eg)
            frosted = rng.random() < 0.5
            dc = fz(mix(K['warm2'], K['cream'], 0.4), Z) * 0.6 if frosted else fz(K['brn0'], Z)
            L.rect(dx0, dy0, dx1 - dx0, dy1 - dy0, dc)
            if frosted and (dx1 - dx0) > 5:
                for k in range(int(dx0) + 2, int(dx1), max(2, int((dx1 - dx0) / 4))):
                    L.rect(k, dy0, 1, dy1 - dy0, fz(K['brn1'], Z))
            (lx_, ly_) = P(Xd + 0.7, Zf - 0.1, Eg + 2.1)
            if rng.random() < 0.6:
                L.rect(lx_, ly_, max(1, unit * 0.12), max(1, unit * 0.16), K['cream'])
                s.lights.append(dict(x=lx_, y=ly_, r=unit * 1.6, ry=unit * 1.0, col=K['amber'], k=0.26, layer=layer, kind='porch'))
                s.A.d['lamps'].append(dict(x=int(lx_), y=int(ly_), r=int(unit * 2.2), kind='porch', layer=layer, bulb=[int(lx_), int(ly_), max(1, int(unit * 0.12)), max(1, int(unit * 0.16))]))
            # a potted plant or two by the door
            for k in range(int(rng.random() * 3)):
                s.plant(L, Xd + (0.8 + k * 0.5) * (1 if rng.random() < 0.5 else -1), Zf - 0.4, Eg, Z, layer, size=0.5 + rng.random() * 0.4)
        # gutter edge (drips)
        (ex0, ey0), (ex1, _) = P(X0 - o, Zf - o, Eg + hw), P(X1 + o, Zf - o, Eg + hw)
        s.A.d['eaves'].append(dict(x0=int(ex0), x1=int(ex1), y=int(ey0), layer=layer))
        # roof
        top_col = fz(K['tile'], Z)
        if roof == 'flat':
            q = [P(X0, Zf, Eg + hw), P(X1, Zf, Eg + hw), P(X1, Zb, Eg + hw), P(X0, Zb, Eg + hw)]
            rc0 = fz(mix(K['conc'], K['navy1'], 0.35), Z)

            def flatf(X, Y, rc0=rc0):
                st = (np.sin(X * 0.07 + Y * 0.31) + np.sin(X * 0.023 - Y * 0.11)) * 0.5
                pud = smooth(0.55, 0.75, st)
                c = mix(rc0, fz(K['navy0'], Z), (smooth(0.0, -0.6, st) * 0.4)[..., None])
                return mix(c, fz(mix(K['sky3'], K['halo'], 0.2), Z), (pud * 0.5)[..., None])
            L.poly(q, flatf)
            # parapet
            L.rect(q[0][0], q[0][1] - max(1, unit * 0.15), q[1][0] - q[0][0], max(1, unit * 0.15), fz(mix(K['conc'], K['halo'], 0.25), Z))
            # water tank on legs or a satellite dish
            if rng.random() < 0.6:
                Xt = X0 + (X1 - X0) * (0.2 + 0.6 * rng.random())
                (tx0, ty0) = P(Xt - 0.6, Zm, Eg + hw + 2.0)
                (tx1, ty1) = P(Xt + 0.6, Zm, Eg + hw + 0.8)
                L.rect(tx0, ty0, tx1 - tx0, ty1 - ty0, fz(mix(K['conc'], K['halo'], 0.3), Z))
                L.rect(tx0, ty0, tx1 - tx0, 1, fz(K['halo'], Z, 0.1))
                (lx0_, lb) = P(Xt - 0.5, Zm, Eg + hw)
                (lx1_, _) = P(Xt + 0.5, Zm, Eg + hw)
                L.lines([(lx0_, ty1), (lx0_, lb)], fz(K['navy0'], Z))
                L.lines([(lx1_, ty1), (lx1_, lb)], fz(K['navy0'], Z))
            if rng.random() < 0.5:
                Xt = X0 + (X1 - X0) * rng.random()
                (dx_, dy_) = P(Xt, Zb - 0.6, Eg + hw + 0.9)
                rr = max(2, unit * 0.4)
                L.ellipse(dx_, dy_, rr, rr * 1.15, fz(mix(K['conc'], K['halo'], 0.4), Z))
                L.lines([(dx_, dy_), (dx_ + rr * 0.8, dy_ - rr * 0.3)], fz(K['navy0'], Z))
            if rng.random() < 0.4:
                # rooftop laundry rack
                (rx0, ry0) = P(X0 + 0.5, Zm, Eg + hw + 1.5)
                (rx1, ry1) = P(X0 + 2.5, Zm, Eg + hw)
                L.rect(rx0, ry0, rx1 - rx0, 1, fz(K['conc'], Z, 0.1))
                L.lines([(rx0, ry0), (rx0, ry1)], fz(K['navy0'], Z))
                L.lines([(rx1, ry0), (rx1, ry1)], fz(K['navy0'], Z))
            return
        if roof == 'shed':
            q = [P(X0 - o, Zf - o, Eg + hw), P(X1 + o, Zf - o, Eg + hw), P(X1 + o, Zb, Eg + hw + hr), P(X0 - o, Zb, Eg + hw + hr)]
            cols = max(2, int((X1 - X0) * 3))
            base = [K['tin'], K['brn2'], K['tileR']][int(rng.random() * 3)]

            def tinf(X, Y, q=q, base=base):
                (exl, ey) = q[0]; (exr, _) = q[1]; (rxl, ry) = q[3]
                v = np.clip((ey - Y) / max(1e-3, ey - ry), 0, 1)
                u = (X - exl) / max(1, exr - exl)
                rib = ((u * cols * 3) % 1.0) < 0.3
                c = base * (0.8 + 0.3 * v)[..., None]
                c = mix(c, K['halo'] * 0.6, (rib * 0.18)[..., None])
                return fz(c, Z)
            L.poly(q, tinf)
            L.lines([q[3], q[2]], fz(mix(base, K['halo'], 0.4), Z))
            return
        # gable/hip, ridge along X
        ridgeL, ridgeR = (X0 - o, X1 + o) if roof == 'gable' else (X0 + D / 2, X1 - D / 2)
        if ridgeR <= ridgeL:
            ridgeL = ridgeR = (X0 + X1) / 2
        rtype = rng.random()
        base = K['tile'] if rtype < 0.5 else (C('#141428') if rtype < 0.65 else (C('#3a2024') if rtype < 0.8 else (K['tileR'] if rtype < 0.93 else (C('#1c3034') if rtype < 0.97 else K['brn2']))))
        base = base * (0.88 + 0.24 * rng.random())
        rows = max(2, int(D * 1.6))
        colsN = max(2, int((X1 - X0) * 3.2))
        # far slope (lit by the moon, beyond the ridge)
        qf = [P(X0 - o, Zb + o, Eg + hw - 0.15), P(X1 + o, Zb + o, Eg + hw - 0.15), P(ridgeR, Zm, Eg + hw + hr), P(ridgeL, Zm, Eg + hw + hr)]
        L.poly(qf, fz(mix(base, K['halo'], 0.22), Z))
        # hip side triangles
        if roof == 'hip':
            L.poly([P(X0 - o, Zf - o, Eg + hw - 0.15), P(X0 - o, Zb + o, Eg + hw - 0.15), P(ridgeL, Zm, Eg + hw + hr)], fz(mix(base, K['navy0'], 0.2), Z))
            L.poly([P(X1 + o, Zf - o, Eg + hw - 0.15), P(X1 + o, Zb + o, Eg + hw - 0.15), P(ridgeR, Zm, Eg + hw + hr)], fz(mix(base, K['halo'], 0.1), Z))
        qn = [P(X0 - o, Zf - o, Eg + hw - 0.15), P(X1 + o, Zf - o, Eg + hw - 0.15), P(ridgeR, Zm, Eg + hw + hr), P(ridgeL, Zm, Eg + hw + hr)]
        if unit > 6:
            L.poly(qn, tile_roof_col(qn, Z, rows, colsN, base, mix(K['halo'], K['pink'], 0.3), 0.9))
        else:
            L.poly(qn, fz(mix(base, K['navy0'], 0.1), Z))
        # ridge cap with a moonlit edge, onigawara bumps at the ends
        (r0x, r0y), (r1x, r1y) = P(ridgeL, Zm, Eg + hw + hr), P(ridgeR, Zm, Eg + hw + hr)
        cap = max(1, int(unit * 0.22))
        L.rect(r0x, r0y - cap, r1x - r0x, cap, fz(mix(base, K['navy0'], 0.3), Z))
        L.rect(r0x, r0y - cap, r1x - r0x, 1, fz(mix(K['halo'], K['pink'], 0.2), Z, -0.1))
        if roof == 'gable' and unit > 5:
            for ex in (r0x, r1x):
                L.rect(ex - cap * 0.6, r0y - cap * 1.8, cap * 1.2, cap * 1.8, fz(mix(base, K['navy0'], 0.2), Z))
        # eave line (dark shadow under the eave)
        (e0x, e0y), (e1x, _) = qn[0], qn[1]
        L.rect(e0x, e0y, e1x - e0x, max(1, unit * 0.12), fz(K['navy0'], Z))
        # TV antenna, solar water heater, vent pipe
        if rng.random() < 0.28 and unit > 4:
            Xa = X0 + (X1 - X0) * rng.random()
            (ax_, ay0) = P(Xa, Zm, Eg + hw + hr)
            (_, ay1) = P(Xa, Zm, Eg + hw + hr + 2.2)
            ac = fz(mix(K['navy1'], K['halo'], 0.25), Z)
            L.lines([(ax_, ay0), (ax_, ay1)], ac)
            el = max(2, unit * 0.9)
            for k in range(3):
                yy = ay1 + k * max(1, unit * 0.18)
                L.lines([(ax_ - el * (0.6 - k * 0.12), yy), (ax_ + el * (0.6 - k * 0.12), yy)], ac)
        if rng.random() < 0.12 and unit > 6:
            Xa = X0 + (X1 - X0) * (0.15 + 0.5 * rng.random())
            q2 = [P(Xa, Zf + 0.3, Eg + hw + 0.25), P(Xa + 2.0, Zf + 0.3, Eg + hw + 0.25), P(Xa + 2.0, Zm - 0.3, Eg + hw + hr - 0.1), P(Xa, Zm - 0.3, Eg + hw + hr - 0.1)]
            L.poly(q2, fz(mix(K['tv2'], K['navy1'], 0.78), Z))
            for k in range(1, 4):
                xa = q2[0][0] + (q2[1][0] - q2[0][0]) * k / 4
                L.lines([(xa, q2[0][1]), (xa, q2[3][1])], fz(K['navy0'], Z))
            (tx_, ty_) = P(Xa + 0.3, Zm, Eg + hw + hr + 0.6)
            L.rect(tx_, ty_, max(3, unit * 1.6), max(2, unit * 0.4), fz(mix(K['conc'], K['halo'], 0.2), Z))
        # lichen and moss on old tiles
        if rng.random() < 0.35 and unit > 5:
            for k in range(int(4 + unit * 1.5)):
                u, v = rng.random(), rng.random() * 0.8
                lx = qn[0][0] + (qn[1][0] - qn[0][0]) * u
                ly = qn[0][1] + (qn[3][1] - qn[0][1]) * v
                L.ellipse(lx, ly, max(0.6, unit * 0.06), max(0.5, unit * 0.035), fz(mix(K['tile'], K['moss2'], 0.35 + 0.3 * rng.random()), Z))
        # a monohoshi: the wooden drying deck on the roof, with someone's washing
        if rng.random() < 0.13 and unit > 9 and X1 - X0 > 4:
            Xa = X0 + (X1 - X0) * (0.1 + 0.4 * rng.random())
            Xb = Xa + 2.6
            Ed_ = Eg + hw + hr + 0.4
            wc = fz(mix(K['brn2'], K['halo'], 0.12), Z)
            deck = [P(Xa, Zf + 0.6, Ed_), P(Xb, Zf + 0.6, Ed_), P(Xb, Zm, Ed_), P(Xa, Zm, Ed_)]
            for (xx, Zz) in ((Xa, Zf + 0.6), (Xb, Zf + 0.6)):
                (px0, py0) = P(xx, Zz, Ed_)
                (_, py1) = P(xx, Zz, Eg + hw + 0.6)
                L.rect(px0, py0, max(1, unit * 0.08), py1 - py0, wc)
            L.poly(deck, fz(mix(K['brn1'], K['halo'], 0.1), Z))
            for k in range(1, 6):
                xx = deck[0][0] + (deck[1][0] - deck[0][0]) * k / 6
                L.lines([(xx, deck[0][1]), (xx, deck[3][1])], fz(K['navy0'], Z))
            (r0x, r0y) = P(Xa, Zf + 0.6, Ed_ + 1.0)
            (r1x, _) = P(Xb, Zf + 0.6, Ed_ + 1.0)
            L.rect(r0x, r0y, r1x - r0x, 1, wc)
            (p0x, p0y) = P(Xa + 0.2, Zf + 1.4, Ed_ + 1.5)
            (p1x, _) = P(Xb - 0.2, Zf + 1.4, Ed_ + 1.5)
            L.rect(p0x, p0y, p1x - p0x, 1, fz(mix(K['conc'], K['halo'], 0.3), Z))
            for k in range(int(rng.random() * 5)):
                cxp = p0x + (k + 0.5) * (p1x - p0x) / 5
                cc = fz([K['cream'], K['pink'], K['tv2'], K['halo']][int(rng.random() * 4)] * 0.55, Z)
                L.rect(cxp, p0y + 1, max(2, unit * 0.3), max(2, unit * (0.35 + rng.random() * 0.4)), cc)
            s.A.d['laundry'].append(dict(x=int(p0x), y=int(p0y), w=int(p1x - p0x), h=int(unit * 0.7), layer=layer))

    def plant(s, L, X, Z, Eg, Zs_, layer, size=0.6):
        cam, rng = s.cam, s.rng
        (px_, py_) = cam.P(X, Z, Eg)
        unit = cam.f / Z
        pw = max(2, unit * 0.35 * size)
        ph = max(2, unit * 0.32 * size)
        pc = fz(mix(K['brn3'], K['red'], 0.25), Z) * 0.8
        L.poly([(px_ - pw / 2, py_ - ph), (px_ + pw / 2, py_ - ph), (px_ + pw * 0.38, py_), (px_ - pw * 0.38, py_)], pc)
        L.rect(px_ - pw / 2, py_ - ph, pw, 1, fz(mix(pc, K['halo'], 0.3), Z))
        # leaves: a cluster of small blobs
        n = int(4 + size * 10 + unit * size * 0.4)
        lr = max(1, unit * 0.12 * size)
        for k in range(min(n, 60)):
            a = rng.random() * math.pi
            rr = rng.random() * unit * 0.45 * size
            lx = px_ + math.cos(a) * rr * 1.2
            ly = py_ - ph - math.sin(a) * rr - lr
            lc = fz(mix(K['leaf'], [K['moss2'], K['leafH'], K['green'] * 0.5][int(rng.random() * 3)], rng.random() * 0.8), Z)
            L.ellipse(lx, ly, lr * (0.8 + rng.random() * 0.6), lr * (0.6 + rng.random() * 0.4), lc)
        if rng.random() < 0.15 and unit > 15:
            L.ellipse(px_ + lr, py_ - ph - unit * 0.3 * size, max(1, lr * 0.6), max(1, lr * 0.6), fz(K['pink'], Z))
        s.A.d['plants'].append(dict(x=int(px_), y=int(py_ - ph), layer=layer))

    def tree(s, L, X, Z, Eg, layer, h=4.0, kind='round'):
        cam, rng = s.cam, s.rng
        (bx_, by_) = cam.P(X, Z, Eg)
        (_, ty_) = cam.P(X, Z, Eg + h)
        unit = cam.f / Z
        tc = fz(K['brn0'], Z)
        dark = fz(mix(K['leaf'], K['navy0'], 0.35), Z)
        mid_ = fz(K['leaf'], Z)
        lit = fz(mix(K['leafH'], K['moss2'], 0.4), Z)
        rim = fz(mix(K['leafH'], K['halo'], 0.35), Z)
        lr = max(1.0, unit * 0.16)
        if kind == 'pine':
            # a leaning trunk and flat cloud-pads of needles, the Japanese garden pine
            lean = (rng.random() - 0.5) * unit * 1.2
            pts = [(bx_ + lean * t * t, by_ - (by_ - ty_) * t) for t in np.linspace(0, 1, 8)]
            L.lines(pts, tc, width=max(1, int(unit * 0.22)))
            npad = 3 + int(rng.random() * 3)
            for k in range(npad):
                t = 0.45 + 0.55 * k / max(1, npad - 1)
                px0, py0 = pts[int(t * 7)]
                side = (-1) ** k
                pxc = px0 + side * unit * (0.4 + rng.random() * 0.9)
                pw, ph = unit * (0.9 + rng.random() * 0.7) * (1.25 - t * 0.5), unit * 0.32
                L.lines([(px0, py0), (pxc, py0 - ph * 0.2)], tc, width=max(1, int(unit * 0.08)))
                for j in range(int(10 + pw * ph / (lr * lr) * 0.9)):
                    a = rng.random() * 2 * math.pi
                    d = rng.random() ** 0.5
                    lx = pxc + math.cos(a) * d * pw
                    ly = py0 - ph * 0.3 + math.sin(a) * d * ph
                    L.ellipse(lx, ly, lr * 1.4, lr * 0.7, dark if ly > py0 - ph * 0.2 else mid_)
                for j in range(int(pw / max(1, lr))):
                    lx = pxc - pw * 0.8 + rng.random() * pw * 1.6
                    ly = py0 - ph * 0.9 - rng.random() * ph * 0.3
                    L.ellipse(lx, ly, lr * 1.2, max(0.6, lr * 0.45), lit)
                    if rng.random() < 0.3:
                        L.px(lx, ly - lr * 0.4, rim)
        else:
            L.lines([(bx_, by_), (bx_ + unit * 0.1, ty_ + (by_ - ty_) * 0.4)], tc, width=max(1, int(unit * 0.16)))
            rr = unit * h * 0.30
            cy_ = ty_ + rr * 0.85
            # clumps: several sub-crowns, each shaded dark below and lit above
            for c in range(3 + int(rng.random() * 4)):
                cx2 = bx_ + (rng.random() - 0.5) * rr * 1.2
                cy2 = cy_ + (rng.random() - 0.6) * rr * 0.8
                cr = rr * (0.45 + rng.random() * 0.35)
                n = int(min(140, 8 + (cr / lr) ** 2 * 1.4))
                for j in range(n):
                    a = rng.random() * 2 * math.pi
                    d = rng.random() ** 0.6 * cr
                    lx = cx2 + math.cos(a) * d
                    ly = cy2 + math.sin(a) * d * 0.8
                    up = (cy2 - ly) / max(1, cr)
                    col = lit if up > 0.35 else (mid_ if up > -0.2 else dark)
                    L.ellipse(lx, ly, lr * (0.8 + rng.random() * 0.6), lr * (0.6 + rng.random() * 0.4), col)
                    if up > 0.6 and rng.random() < 0.25:
                        L.px(lx, ly - lr * 0.5, rim)
            rr = rr
        s.A.d['trees'].append(dict(x=int(bx_), y=int(ty_), r=int(unit * h * 0.3), layer=layer))

    def pole(s, L, X, Z, Eg, layer, h=9.0, trans=True):
        cam, rng = s.cam, s.rng
        (bx_, by_) = cam.P(X, Z, Eg)
        (_, ty_) = cam.P(X, Z, Eg + h)
        unit = cam.f / Z
        pw = max(1, unit * 0.28)
        pc = fz(mix(K['conc'], K['navy1'], 0.3), Z)
        L.rect(bx_ - pw / 2, ty_, pw, by_ - ty_, pc)
        L.rect(bx_ + pw / 2 - max(1, pw * 0.3), ty_, max(1, pw * 0.3), by_ - ty_, fz(mix(K['conc'], K['halo'], 0.25), Z))
        # crossarms
        arms = []
        for k in range(2):
            ay_ = ty_ + unit * (0.35 + k * 0.7)
            aw = unit * (1.6 - k * 0.3)
            L.rect(bx_ - aw / 2, ay_, aw, max(1, unit * 0.1), fz(K['navy0'], Z))
            for j in (-1, 0, 1):
                L.rect(bx_ + j * aw * 0.42 - max(1, unit * 0.04), ay_ - max(1, unit * 0.12), max(1, unit * 0.08), max(1, unit * 0.12), fz(mix(K['conc'], K['halo'], 0.4), Z))
                arms.append((bx_ + j * aw * 0.42, ay_ - max(1, unit * 0.12)))
        if trans and unit > 3:
            tw = max(2, unit * 0.45)
            th = max(3, unit * 0.75)
            tx_ = bx_ + pw / 2
            tyy = ty_ + unit * 1.8
            L.rect(tx_, tyy, tw, th, fz(mix(K['conc'], K['tv2'], 0.2), Z))
            L.rect(tx_, tyy, tw, max(1, unit * 0.06), fz(K['halo'], Z, 0.1))
            L.rect(tx_ + tw * 0.3, tyy - max(1, unit * 0.1), max(1, tw * 0.15), max(1, unit * 0.1), fz(K['navy0'], Z))
            # a small sign plate (unreadable)
            (sx_, sy_) = cam.P(X, Z - 0.2, Eg + 2.2)
            if unit > 12:
                L.rect(sx_ - unit * 0.12, sy_, unit * 0.24, unit * 0.6, fz(mix(K['cream'], K['halo'], 0.4), Z, 0.15))
                for k in range(3):
                    L.px(sx_, sy_ + 2 + k * max(1, unit * 0.15), fz(K['navy0'], Z))
        s.A.d['poles'].append(dict(x=int(bx_), y=int(ty_), layer=layer, arms=[[int(a[0]), int(a[1])] for a in arms]))
        return arms


def draw_town(Ls, cam, A, rng, V, lights):
    """mid and near layers: hillside houses in rows, the pagoda and temple, the stair lane and its life."""
    T = Town(cam, A, rng, V, lights)
    W, H = Ls['mid'].W, Ls['mid'].H
    Zfar, Znear = cam.Zs - 30.0, cam.Zat_ground(H + 30)
    Zlane = cam.Zs - 9.0
    Zcut = 52.0          # mid / near split
    # ---------------- ground fill for each layer (dark hillside, terraced)
    for name, z0, z1 in (('mid', Zcut - 4, cam.Zs - 8.5), ('near', Znear - 10, Zcut + 2)):
        L = Ls[name]
        yA = cam.P(0, z1, cam.g(z1))[1]
        gn = vnoise((H, W), 14, rng, octaves=3)

        def gcol(X, Y, yA=yA):
            v = np.clip((Y - yA) / max(1, H - yA), 0, 1)
            n = gn[int(Y[0, 0]):int(Y[-1, 0]) + 1, int(X[0, 0]):int(X[0, -1]) + 1]
            c = mix(K['navy1'], K['brn1'], (n * 0.5)[..., None])
            c = mix(c, K['moss'], (smooth(0.62, 0.75, n) * 0.6)[..., None])
            return c * (0.8 + 0.25 * v)[..., None]
        L.rect(-2, yA, W + 4, H - yA + 2, gcol)
    # ---------------- reserved plots along the lane (the shrine's path, the vending recess)
    SP = dict(cat=Znear + 10, vend=Znear + 14, mail=Znear + 21, torii=Znear + 33, neon=Znear + 50)
    T.spots = SP
    lt, lv = cam.lane(SP['torii']), cam.lane(SP['vend'])
    reserved = [(lt - 1.6 - 7.0, lt - 1.6 + 0.2, SP['torii'] - 2.5, SP['torii'] + 8.0),
                (lv + 1.6 - 0.2, lv + 1.6 + 3.6, SP['vend'] - 1.5, SP['vend'] + 1.5)]
    # keep the line of sight to the lane's inhabitants clear: nothing tall nearer than them beside the lane
    for key, side in (('cat', -1), ('mail', -1), ('torii', -1), ('vend', 1)):
        Zk = SP[key]
        lk = cam.lane(Zk)
        edge = lk + side * 1.6
        reserved.append((min(edge, edge + side * 5.0), max(edge, edge + side * 5.0), Zk - 10.0, Zk + 0.5))
    T.reserved = reserved
    # ---------------- rows of houses
    zs = []
    Z = Zfar
    while Z > Znear - 9:
        zs.append(Z)
        Z -= 6.5 + rng.random() * 3.0 * (Z / 60)
    for Zr in zs:
        layer = 'mid' if Zr >= Zcut else 'near'
        L = Ls[layer]
        Xmin, Xmax = cam.Xat(-60, Zr + 8), cam.Xat(W + 60, Zr + 8)
        Xlane = cam.lane(Zr)
        lane_half = 1.6
        xs = []
        X = Xmin
        while X < Xmax:
            w = 4.5 + rng.random() * 3.5 * (1 + Zr / 120)
            gap = rng.random() * 1.8 if rng.random() < 0.6 else 1.0 + rng.random() * 4
            xs.append((X, X + w))
            X += w + gap
        # don't build on the lane; leave a garden/terrace margin
        blocks = []
        for (a, b) in xs:
            if b > Xlane - lane_half - 1.0 and a < Xlane + lane_half + 1.0:
                # trim to the lane's walls
                if a < Xlane - lane_half - 1.0 - 2.2:
                    blocks.append((a, Xlane - lane_half - 1.2))
                if b > Xlane + lane_half + 1.0 + 2.2:
                    blocks.append((Xlane + lane_half + 1.2, b))
                continue
            blocks.append((a, b))
        # avoid the pagoda's terrace
        pgx, pgz = V['pagoda']
        PX = cam.Xat(pgx, pgz)
        for (a, b) in blocks:
            if abs(Zr - pgz) < 14 and b > PX - 12 and a < PX + 12:
                continue
            # rail-side strip: leave the first row sparse so the train shows
            if Zr > Zfar - 3 and rng.random() < 0.55:
                continue
            D = 5 + rng.random() * 4
            hw = (2.6 if rng.random() < (0.55 if Zr > 45 else 0.8) else 5.4) + rng.random() * 0.8
            if rng.random() < 0.08 and Zr > 45:
                hw = 8.4 + rng.random()        # a small apartment block
            r = rng.random()
            roof = 'gable' if r < 0.55 else ('hip' if r < 0.8 else ('flat' if r < 0.9 else 'shed'))
            if hw > 8:
                roof = 'flat'
            Zh = Zr + rng.random() * 1.5
            if any(b > ra and a < rb and Zh + D > za and Zh < zb for (ra, rb, za, zb) in reserved):
                continue
            key = Zh
            T.add(key, layer, (lambda L=L, a=a, b=b, Zh=Zh, D=D, hw=hw, roof=roof, layer=layer: T.house(L, a, b, Zh, D, hw, roof, layer)))
            # gardens: trees in some gaps
        for i in range(len(blocks) - 1):
            g0, g1 = blocks[i][1], blocks[i + 1][0]
            if g0 < Xlane + lane_half + 1.5 and g1 > Xlane - lane_half - 1.5:
                continue
            if g1 - g0 > 2.0 and rng.random() < 0.75:
                Xt = (g0 + g1) / 2
                Zt = Zr + 2 + rng.random() * 3
                if any(ra - 2 < Xt < rb + 2 and za - 3 < Zt < zb for (ra, rb, za, zb) in reserved):
                    continue
                kind = 'pine' if rng.random() < 0.3 else 'round'
                T.add(Zt, layer, (lambda L=L, Xt=Xt, Zt=Zt, kind=kind, layer=layer: T.tree(L, Xt, Zt, cam.g(Zt), layer, h=3 + rng.random() * 4, kind=kind)))
        # utility poles along each row, wires between them
        if rng.random() < 0.7:
            for k in range(int(1 + (Xmax - Xmin) / 70)):
                Xp = Xmin + rng.random() * (Xmax - Xmin)
                if abs(Xp - Xlane) < 3 or any(ra - 1 < Xp < rb + 1 and za - 2 < Zr < zb for (ra, rb, za, zb) in reserved):
                    continue
                Zp = Zr - 0.5
                T.add(Zp - 0.01, layer, (lambda L=L, Xp=Xp, Zp=Zp, layer=layer: T.pole(L, Xp, Zp, cam.g(Zp), layer)))
    # ---------------- retaining walls (ishigaki) at the front of each row, drawn before the houses of that row
    for Zr in zs:
        layer = 'mid' if Zr >= Zcut else 'near'
        L = Ls[layer]

        def wallf(L=L, Zr=Zr):
            E1 = cam.g(Zr)
            E0 = cam.g(Zr - 3)
            (x0, y0) = cam.P(cam.Xat(-40, Zr), Zr, E1)
            (_, y1) = cam.P(0, Zr, E0 + 0.0)
            unit = cam.f / Zr
            hgt = max(1, (cam.slope * 3) * unit)
            sc = fz(K['stone'], Zr)

            def stonef(X, Y, y0=y0, unit=unit, Zr=Zr):
                bw, bh = max(3, unit * 0.55), max(2, unit * 0.3)
                rr = np.floor((Y - y0) / bh)
                xx = (X + (rr % 2) * bw * 0.5) % bw
                yy = (Y - y0) % bh
                joint = (xx < 1) | (yy < 1)
                c = mix(sc, fz(K['stoneH'], Zr), (0.25 + 0.2 * np.sin(rr * 7.1 + np.floor((X + (rr % 2) * bw * 0.5) / bw) * 3.3))[..., None])
                c = mix(c, fz(K['moss2'], Zr), (((np.sin(X * 0.21) + np.sin(Y * 0.9 + X * 0.05)) > 1.4) * 0.6)[..., None])
                return np.where(joint[..., None], fz(K['navy0'], Zr), c)
            L.rect(-2, y0, W + 4, hgt, stonef)
            L.rect(-2, y0, W + 4, 1, fz(mix(K['stoneH'], K['halo'], 0.3), Zr))
        T.add(Zr + 0.02, layer, wallf)
    # ---------------- the pagoda (three storeys) and a temple hall on a terrace
    pgx, pgz = V['pagoda']
    PX = cam.Xat(pgx, pgz)
    T.add(pgz - 0.5, 'mid', lambda: draw_pagoda(T, Ls['mid'], PX, pgz))
    # ---------------- the lane: steps, side walls, handrail, lamps, and its inhabitants
    draw_lane(T, Ls, Znear, Zlane, Zcut)
    draw_lowstreet(T, Ls['mid'], Zfar, cam.Zs - 8.0)
    # ---------------- run everything far to near
    T.ops.sort(key=lambda o: -o[0])
    for Z, layer, fn in T.ops:
        kit.GROUP[0] += 1
        fn()
    return T


def draw_lowstreet(T, L, Z0, Z1):
    """the flat strip at the foot of the hill: a back road, parked cars, sheds, the crossing at the lane's foot."""
    cam, rng, A = T.cam, T.rng, T.A
    P = cam.P
    W, H = L.W, L.H
    Zroad0, Zroad1 = Z1 - 6.5, Z1 - 1.5
    def road(L=L):
        E = cam.g(Zroad0)
        (_, y0) = P(0, Zroad1, cam.g(Zroad1))
        (_, y1) = P(0, Zroad0, E)
        rc = fz(mix(K['navy1'], K['plum'], 0.2), Zroad0)
        def f(X, Y):
            n = np.sin(X * 0.05 + Y * 0.9) * np.sin(X * 0.013 + 1.7)
            return mix(rc, fz(K['sky3'], Zroad0), (smooth(0.4, 0.9, n) * 0.35)[..., None])
        L.rect(-2, y0, W + 4, y1 - y0, f)
        L.rect(-2, y1 - 1, W + 4, 1, fz(K['stoneH'], Zroad0))
        L.rect(-2, y0, W + 4, 1, fz(K['stoneH'], Zroad1))
        (_, ym) = P(0, (Zroad0 + Zroad1) / 2, E)
        for x in range(0, W, 26):
            L.rect(x, ym, 12, 1, fz(mix(K['cream'], K['halo'], 0.5), Zroad0, 0.1))
        A.d['paths'].append(dict(pts=[[-60, int(ym) - 1], [W + 60, int(ym) - 1]], layer='mid', kind='road'))
        A.d['paths'].append(dict(pts=[[W + 60, int(ym) + 2], [-60, int(ym) + 2]], layer='mid', kind='road'))
    T.add(Zroad1 + 0.1, 'mid', road)
    # street lamps on the road's near kerb
    X = cam.Xat(-40, Zroad0)
    i = 0
    while cam.P(X, Zroad0, 0)[0] < W + 40:
        def sl(X=X, i=i):
            Z = Zroad0 - 0.3
            E = cam.g(Z)
            unit = cam.f / Z
            (x0, y0) = P(X, Z, E)
            (_, y1) = P(X, Z, E + 5.5)
            pc = fz(K['navy0'], Z)
            L.rect(x0, y1, max(1, unit * 0.12), y0 - y1, pc)
            (hx, hy_) = P(X + 1.2, Z + 1.0, E + 5.4)
            L.lines([(x0, y1), (hx, hy_)], pc)
            L.rect(hx - 2, hy_, 4, 1, K['cream'] if i % 3 else K['fluo'])
            col = K['amber'] if i % 3 else K['fluo']
            T.lights.append(dict(x=hx, y=hy_ + 1, r=unit * 4, ry=unit * 2.5, col=col, k=0.28, layer='mid', kind='street', air=True, pool=(hx, P(X + 1.2, Z + 1.0, E)[1])))
            A.d['lamps'].append(dict(x=int(hx), y=int(hy_ + 1), r=int(unit * 4), kind='street', layer='mid', bulb=[int(hx - 2), int(hy_), 4, 1]))
        T.add(Zroad0 - 0.3, 'mid', sl)
        X += 28 + rng.random() * 14
        i += 1
    # parked cars along the road
    for k in range(int(W / 260)):
        x = rng.random() * W
        Xc = cam.Xat(x, Zroad1)
        if abs(Xc - cam.lane(Zroad1)) < 6:
            continue
        def car(Xc=Xc):
            Z = Zroad1 - 1.2
            E = cam.g(Z)
            unit = cam.f / Z
            (x0, y0) = P(Xc, Z, E + 1.45)
            (x1, y1) = P(Xc + 4.0, Z, E)
            bc = fz([K['conc'], K['red'], K['tv2'], K['cream'] * 0.5, K['navy2']][int(rng.random() * 5)], Z)
            L.poly([(x0, y1 - (y1 - y0) * 0.5), (x0 + (x1 - x0) * 0.08, y1 - (y1 - y0) * 0.62), (x1 - (x1 - x0) * 0.05, y1 - (y1 - y0) * 0.62), (x1, y1 - (y1 - y0) * 0.45), (x1, y1 - 2), (x0, y1 - 2)], bc)
            L.poly([(x0 + (x1 - x0) * 0.25, y1 - (y1 - y0) * 0.6), (x0 + (x1 - x0) * 0.35, y0), (x1 - (x1 - x0) * 0.25, y0), (x1 - (x1 - x0) * 0.15, y1 - (y1 - y0) * 0.6)], mix(bc, K['navy0'], 0.3))
            L.rect(x0 + (x1 - x0) * 0.36, y0 + 2, (x1 - x0) * 0.36, (y1 - y0) * 0.25, fz(mix(K['glass'], K['halo'], 0.25), Z))
            L.rect(x0, y1 - (y1 - y0) * 0.5, (x1 - x0), 1, fz(mix(bc, K['halo'], 0.5), Z))
            for wx in (x0 + (x1 - x0) * 0.2, x1 - (x1 - x0) * 0.2):
                L.ellipse(wx, y1 - 2, unit * 0.32, unit * 0.32, K['navy0'])
            L.px(x1 - 1, y1 - (y1 - y0) * 0.4, mix(K['red'], K['navy0'], 0.3))
            L.px(x0, y1 - (y1 - y0) * 0.4, mix(K['cream'], K['navy0'], 0.5))
        T.add(Zroad1 - 1.2, 'mid', car)
    # sheds and low garden walls between road and the first row of houses
    X = cam.Xat(-60, Z0 + 8)
    while cam.P(X, Z0 + 8, 0)[0] < W + 60:
        w = 2.5 + rng.random() * 5
        Zh = Z0 + 3 + rng.random() * (Zroad0 - Z0 - 8)
        Xl = cam.lane(Zh)
        if abs(X + w / 2 - Xl) > w / 2 + 3:
            r = rng.random()
            if r < 0.35:
                T.add(Zh, 'mid', (lambda X=X, w=w, Zh=Zh: T.house(L, X, X + w, Zh, 3.0, 2.3, 'shed', 'mid')))
            elif r < 0.55:
                T.add(Zh + 1, 'mid', (lambda X=X, w=w, Zh=Zh: T.tree(L, X + w / 2, Zh + 1, cam.g(Zh + 1), 'mid', h=3 + rng.random() * 3)))
            elif r < 0.75:
                def gw(X=X, w=w, Zh=Zh):
                    E = cam.g(Zh)
                    (x0, y0) = P(X, Zh, E + 1.2)
                    (x1, y1) = P(X + w, Zh, E)
                    L.rect(x0, y0, x1 - x0, y1 - y0, fz(K['stone'], Zh))
                    L.rect(x0, y0, x1 - x0, 1, fz(K['stoneH'], Zh))
                    for k in range(int(x0), int(x1), 3):
                        if rng.random() < 0.4:
                            L.px(k, y0 - 1 - rng.random() * 2, fz(K['moss2'], Zh))
                T.add(Zh, 'mid', gw)
        X += w + rng.random() * 4
    # crossing at the foot of the lane: a railway crossing signal and a pedestrian light
    def crossing():
        Z = Z1 - 0.3
        E = cam.g(Z)
        Xc = cam.lane(Z) + 2.4
        unit = cam.f / Z
        (x0, y0) = P(Xc, Z, E)
        (_, y1) = P(Xc, Z, E + 3.2)
        pc = fz(mix(K['conc'], K['halo'], 0.2), Z)
        L.rect(x0, y1, max(1, unit * 0.1), y0 - y1, pc)
        # the X sign
        a = unit * 0.5
        L.lines([(x0 - a, y1 - a * 0.6), (x0 + a, y1 + a * 0.6)], fz(mix(K['amber'], K['navy0'], 0.3), Z))
        L.lines([(x0 - a, y1 + a * 0.6), (x0 + a, y1 - a * 0.6)], fz(mix(K['amber'], K['navy0'], 0.3), Z))
        lamps = []
        for d in (-1, 1):
            lx, ly = x0 + d * unit * 0.35, y1 + unit * 0.9
            L.ellipse(lx, ly, max(1, unit * 0.13), max(1, unit * 0.13), mix(K['red'], K['navy0'], 0.5))
            lamps.append([int(lx), int(ly)])
        A.d['crossing'] = dict(x=int(x0), y=int(y1), kind='rail', lamps=lamps, layer='mid')
        # pedestrian light across the road
        Zp = Zroad0 - 0.4
        (px0, py0) = P(cam.lane(Zp) - 2.4, Zp, cam.g(Zp))
        (_, py1) = P(0, Zp, cam.g(Zp) + 2.6)
        up = cam.f / Zp
        L.rect(px0, py1, max(1, up * 0.1), py0 - py1, pc)
        L.rect(px0 - up * 0.15, py1, up * 0.3, up * 0.6, fz(K['navy0'], Zp))
        L.rect(px0 - up * 0.08, py1 + up * 0.08, up * 0.16, up * 0.16, mix(K['red'], K['navy0'], 0.4))
        L.rect(px0 - up * 0.08, py1 + up * 0.34, up * 0.16, up * 0.16, mix(K['green'], K['navy0'], 0.5))
        A.d['ped'] = dict(x=int(px0), y=int(py1), red=[int(px0 - up * 0.08), int(py1 + up * 0.08), max(1, int(up * 0.16)), max(1, int(up * 0.16))],
                          green=[int(px0 - up * 0.08), int(py1 + up * 0.34), max(1, int(up * 0.16)), max(1, int(up * 0.16))], layer='mid')
    T.add(Z1 - 0.35, 'mid', crossing)


def draw_pagoda(T, L, PX, Z):
    cam, rng = T.cam, T.rng
    Eg = cam.g(Z) + 6.0
    P = cam.P
    unit = cam.f / Z
    # terrace: stone wall
    (tx0, ty0) = P(PX - 9, Z - 4, Eg)
    (tx1, ty1) = P(PX + 9, Z - 4, Eg - 6)
    L.rect(tx0, ty0, tx1 - tx0, ty1 - ty0, fz(K['stone'], Z))
    for yy in range(int(ty0), int(ty1), max(2, int(unit * 0.4))):
        L.rect(tx0, yy, tx1 - tx0, 1, fz(K['navy0'], Z))
    L.rect(tx0, ty0, tx1 - tx0, 1, fz(K['stoneH'], Z))
    # temple hall behind/right: a big hip-and-gable roof
    T.house(L, PX + 4, PX + 16, Z + 2, 10, 3.4, 'hip', 'mid', wall=K['brn1'])
    col = fz(mix(K['navy0'], K['brn0'], 0.3), Z)
    edge = fz(mix(K['halo'], K['pink'], 0.35), Z, -0.1)
    wallc = fz(K['brn1'], Z)
    E = Eg
    sizes = [(3.4, 3.2), (2.8, 2.7), (2.3, 2.5)]
    for i, (half, h) in enumerate(sizes):
        # body
        (bx0, by0) = P(PX - half * 0.55, Z, E + h)
        (bx1, by1) = P(PX + half * 0.55, Z, E)
        L.rect(bx0, by0, bx1 - bx0, by1 - by0, wallc)
        # lattice doors, warm because a lamp is lit inside at the bottom storey
        if i == 0:
            (dx0, dy0) = P(PX - 0.6, Z - 0.01, E + 1.8)
            (dx1, dy1) = P(PX + 0.6, Z - 0.01, E)
            L.rect(dx0, dy0, dx1 - dx0, dy1 - dy0, fz(K['warm3'], Z) * 0.8)
            for k in range(int(dx0), int(dx1), 2):
                L.px(k, (dy0 + dy1) / 2, fz(K['brn0'], Z))
            T.lights.append(dict(x=(dx0 + dx1) / 2, y=dy1, r=unit * 3, col=K['amber'], k=0.4, layer='mid', kind='lantern'))
        else:
            for k in range(int(bx0) + 2, int(bx1) - 1, 3):
                L.rect(k, by0 + 2, 1, by1 - by0 - 3, fz(K['brn0'], Z))
        # roof: wide, with upturned eaves
        E += h
        (rx0, ry0) = P(PX - half * 1.25, Z - 1, E - 0.2)
        (rx1, _) = P(PX + half * 1.25, Z - 1, E - 0.2)
        (cx0, cy0) = P(PX - half * 0.45, Z, E + 0.9)
        (cx1, _) = P(PX + half * 0.45, Z, E + 0.9)
        curl = unit * 0.5
        pts = [(rx0 - 1, ry0 - curl), (rx0 + unit * 0.4, ry0), (rx1 - unit * 0.4, ry0), (rx1 + 1, ry0 - curl), (cx1, cy0), (cx0, cy0)]
        L.poly(pts, col)
        L.lines([(rx0 - 1, ry0 - curl), (rx0 + unit * 0.4, ry0), (rx1 - unit * 0.4, ry0), (rx1 + 1, ry0 - curl)], edge)
        L.lines([(rx1 + 1, ry0 - curl), (cx1, cy0)], fz(mix(K['halo'], K['pink'], 0.2), Z))
        # bracket shadow line
        L.rect(rx0 + unit * 0.4, ry0 + 1, rx1 - rx0 - unit * 0.8, max(1, unit * 0.15), fz(K['navy0'], Z))
        # wind bells at the eave corners
        for bxp in (rx0 - 1, rx1 + 1):
            L.px(bxp, ry0 - curl + 1, fz(K['brn3'], Z))
            L.px(bxp, ry0 - curl + 2, fz(K['brn3'], Z))
            T.A.d['vents'].append(dict(x=int(bxp), y=int(ry0 - curl + 2), kind='windbell', layer='mid'))
        E += 0.9
    # sorin finial with rings
    (fx_, fy0) = P(PX, Z, E)
    (_, fy1) = P(PX, Z, E + 5.5)
    L.rect(fx_ - max(1, unit * 0.1), fy1, max(2, unit * 0.2), fy0 - fy1, col)
    for k in range(9):
        yy = fy0 - (fy0 - fy1) * (0.15 + k * 0.07)
        L.rect(fx_ - unit * 0.3, yy, unit * 0.6, 1, edge if k % 2 == 0 else col)
    L.ellipse(fx_, fy1, max(1.5, unit * 0.25), max(1.5, unit * 0.25), edge)
    # stone lanterns and a pine
    for dxp in (-5.5, 5.5):
        (lx_, ly_) = P(PX + dxp, Z - 3, Eg)
        L.rect(lx_ - unit * 0.25, ly_ - unit * 1.6, unit * 0.5, unit * 1.6, fz(K['stone'], Z))
        L.rect(lx_ - unit * 0.45, ly_ - unit * 1.8, unit * 0.9, unit * 0.25, fz(K['stoneH'], Z))
        L.rect(lx_ - unit * 0.15, ly_ - unit * 1.25, unit * 0.3, unit * 0.3, K['warm'])
        T.lights.append(dict(x=lx_, y=ly_ - unit * 1.1, r=unit * 2.5, col=K['amber'], k=0.4, layer='mid', kind='lantern'))
        T.A.d['lamps'].append(dict(x=int(lx_), y=int(ly_ - unit * 1.1), r=int(unit * 2.5), kind='lantern', layer='mid', bulb=[int(lx_ - unit * 0.15), int(ly_ - unit * 1.25), max(1, int(unit * 0.3)), max(1, int(unit * 0.3))]))
    T.tree(L, PX - 9, Z + 1, Eg, 'mid', h=7, kind='pine')
    T.A.d['shrine_pagoda'] = dict(x=int(fx_), y=int(fy1), base=int(P(PX, Z, Eg)[1]))


def draw_lane(T, Ls, Znear, Zfar, Zcut):
    cam, rng, A = T.cam, T.rng, T.A
    W, H = Ls['near'].W, Ls['near'].H
    P = cam.P
    half = 1.6
    rise = 0.16
    run = rise / cam.slope
    steps = []
    Z = Znear - 1
    centre = []
    k = 0
    while Z < Zfar - 2:
        Z1 = Z + run
        # landings now and then
        if k % 14 == 13:
            Z1 = Z + run * 3
        steps.append((Z, Z1))
        Z = Z1
        k += 1
    puddle_n = 0
    for i, (Za, Zb) in enumerate(steps):
        layer = 'mid' if Za >= Zcut else 'near'
        L = Ls[layer]
        E = cam.g(Za)
        Xa, Xb = cam.lane(Za), cam.lane(Zb)

        def tread(L=L, Za=Za, Zb=Zb, E=E, Xa=Xa, Xb=Xb, i=i, layer=layer):
            unit = cam.f / Za
            q = [P(Xa - half, Za, E), P(Xa + half, Za, E), P(Xb + half, Zb, E), P(Xb - half, Zb, E)]
            sc = fz(mix(K['stone'], K['plum'], 0.25), Za)
            hi = fz(mix(K['stoneH'], K['halo'], 0.25), Za)
            seed = i * 7.31

            def f(X, Y, q=q):
                (x0, y0), (x1, _), (x2, y2), (x3, _) = q
                v = np.clip((y0 - Y) / max(1e-3, y0 - y2), 0, 1)
                xl = x0 + (x3 - x0) * v
                xr = x1 + (x2 - x1) * v
                u = (X - xl) / np.maximum(1, xr - xl)
                slab = np.floor(u * 4 + (i % 2) * 0.5)
                jn = (np.abs((u * 4 + (i % 2) * 0.5) % 1.0) < 0.03)
                c = mix(sc, hi, (0.15 + 0.15 * np.sin(slab * 3.7 + seed))[..., None])
                c = mix(c, hi, ((1 - v) ** 6 * 0.6)[..., None])       # the wet nosing catches light
                c = np.where(jn[..., None], fz(K['navy0'], Za), c)
                return c
            L.poly(q, f)
            # the drop shadow beyond the nosing (the next step down)
            L.lines([q[3], q[2]], fz(K['navy0'], Za))
            # moss in the joints at the lane edges
            if unit > 8:
                for side in (0, 1):
                    xe, ye = q[side]
                    for m in range(int(unit * 0.25)):
                        if rng.random() < 0.5:
                            L.px(xe + (1 if side == 0 else -2) * (m % 3) + (rng.random() - 0.5) * 2, ye - 1 - rng.random() * (ye - q[3][1]), fz(mix(K['moss2'], K['green'], 0.3), Za))
        T.add(Za + run * 0.5, layer, tread)
        centre.append(P(Xa, Za, E))
        # puddles on some treads
        if rng.random() < 0.13 and Za < Zfar - 20:
            def pud(L=L, Za=Za, Zb=Zb, E=E, Xa=Xa, layer=layer):
                unit = cam.f / Za
                Xp = Xa + (rng.random() - 0.5) * 2 * (half - 0.6)
                (px_, py_) = P(Xp, (Za + Zb) / 2, E)
                rw = unit * (0.35 + rng.random() * 0.55)
                rh = max(1.0, (P(0, Za, E)[1] - P(0, Zb, E)[1]) * 0.32)
                def pc(X, Y):
                    v = (Y - (py_ - rh)) / (2 * rh)
                    c = mix(fz(K['sky4'], 60), fz(K['sky2'], 60), np.clip(v, 0, 1)[..., None])
                    sp = (np.abs(X - px_ - rw * 0.2) < max(1, rw * 0.06)) * 0.6
                    return mix(c, K['halo'], sp[..., None])
                L.ellipse(px_, py_, rw, rh, pc)
                src = [[int(px_), int(py_ - unit * 4.5)]]
                A.d['puddles'].append(dict(x=int(px_ - rw), y=int(py_ - rh), w=int(2 * rw), h=int(2 * rh), src=src, layer=layer))
            T.add(Za + run * 0.5 - 0.001, layer, pud)
    A.d['stairs'].append(dict(pts=[[int(x), int(y)] for x, y in centre[::2]], w=int(2 * half * cam.f / Znear), layer='near'))
    # ---------------- side walls along the lane (stone, ~1.1 m), stepping with the treads
    for i, (Za, Zb) in enumerate(steps):
        layer = 'mid' if Za >= Zcut else 'near'
        L = Ls[layer]
        E = cam.g(Za)
        for side in (-1, 1):
            if side == 1 and T.spots['vend'] - 1.6 < Za < T.spots['vend'] + 1.2:
                continue
            def sw(L=L, Za=Za, Zb=Zb, E=E, side=side, i=i):
                Xa, Xb = cam.lane(Za) + side * half, cam.lane(Zb) + side * half
                hgt = 1.1 if (i // 9) % 3 else 2.4
                q = [P(Xa, Za, E), P(Xb, Zb, E), P(Xb, Zb, E + hgt), P(Xa, Za, E + hgt)]
                c0 = fz(mix(K['stone'], K['navy0'], 0.25 if side < 0 else 0.0), Za)
                unit = cam.f / Za

                def f(X, Y, q=q):
                    bh = max(2, unit * 0.28)
                    rr = np.floor(Y / bh)
                    jn = (Y % bh) < 1
                    c = mix(c0, fz(K['stoneH'], Za), (0.18 + 0.12 * np.sin(rr * 5.3 + i))[..., None])
                    return np.where(jn[..., None], fz(K['navy0'], Za), c)
                L.poly(q, f)
                L.lines([q[3], q[2]], fz(mix(K['stoneH'], K['halo'], 0.35), Za))
                # cap stones on top
                if hgt < 2:
                    L.lines([(q[3][0], q[3][1] - 1), (q[2][0], q[2][1] - 1)], fz(K['stoneH'], Za))
            T.add(Za + run * 0.4, layer, sw)
    # ---------------- handrail down the middle
    for i in range(0, len(steps), 3):
        Za = steps[i][0]
        layer = 'mid' if Za >= Zcut else 'near'
        L = Ls[layer]
        def post(L=L, Za=Za, i=i):
            X = cam.lane(Za) + 0.0
            E = cam.g(Za)
            (x0, y0) = P(X, Za, E)
            (_, y1) = P(X, Za, E + 0.9)
            unit = cam.f / Za
            pc = fz(mix(K['conc'], K['halo'], 0.25), Za)
            L.rect(x0 - max(1, unit * 0.03), y1, max(1, unit * 0.06), y0 - y1, pc)
            if i + 3 < len(steps):
                Zb = steps[i + 3][0]
                (x2, y2) = P(cam.lane(Zb), Zb, cam.g(Zb) + 0.9)
                L.lines([(x0, y1), (x2, y2)], pc, width=max(1, int(unit * 0.05)))
                L.lines([(x0, y1 - 1), (x2, y2 - 1)], fz(mix(K['halo'], K['cream'], 0.3), Za))
        T.add(Za - 0.05, layer, post)
    # ---------------- street lamps along the lane
    li = 0
    Z = Znear + 3
    while Z < Zfar - 6:
        side = 1 if li % 2 == 0 else -1
        layer = 'mid' if Z >= Zcut else 'near'
        L = Ls[layer]
        kind = 'street'
        coolp = (li % 4 == 3)
        def lamp(L=L, Z=Z, side=side, layer=layer, coolp=coolp):
            X = cam.lane(Z) + side * (half + 0.15)
            E = cam.g(Z)
            unit = cam.f / Z
            (x0, y0) = P(X, Z, E)
            (_, y1) = P(X, Z, E + 4.4)
            pc = fz(mix(K['navy0'], K['ind'], 0.3), Z)
            L.rect(x0 - max(1, unit * 0.05), y1, max(1, unit * 0.1), y0 - y1, pc)
            (hx, hy_) = P(X - side * 0.7, Z, E + 4.3)
            L.lines([(x0, y1), (x0 - side * unit * 0.3, y1 - unit * 0.12), (hx, hy_)], pc, width=max(1, int(unit * 0.06)))
            hw_ = max(2, unit * 0.32)
            L.poly([(hx - hw_, hy_ + 1), (hx + hw_, hy_ + 1), (hx + hw_ * 0.5, hy_ - hw_ * 0.5), (hx - hw_ * 0.5, hy_ - hw_ * 0.5)], pc)
            bc = K['fluo'] if coolp else K['cream']
            L.rect(hx - hw_ * 0.6, hy_ + 1, hw_ * 1.2, max(1, unit * 0.07), bc)
            col = K['fluo'] if coolp else K['amber']
            T.lights.append(dict(x=hx, y=hy_ + 1, r=unit * 3.2, ry=unit * 2.2, col=col, k=0.32, layer=layer, kind='street', air=True, pool=(hx, P(X - side * 0.7, Z, E)[1])))
            A.d['lamps'].append(dict(x=int(hx), y=int(hy_ + 1), r=int(unit * 4.5), kind='street', layer=layer, cool=bool(coolp),
                                     bulb=[int(hx - hw_ * 0.6), int(hy_ + 1), max(1, int(hw_ * 1.2)), max(1, int(unit * 0.07))]))
            # moths' region
            A.d['regions']['motes'].append([int(hx - unit * 1.2), int(hy_ - unit * 0.8), int(unit * 2.4), int(unit * 1.6)])
        T.add(Z - 0.2, layer, lamp)
        Z += 9 + li * 0.8
        li += 1
    # ---------------- inhabitants of the lane (near layer)
    near = Ls['near']
    Zc = T.spots['cat']
    # the sleeping cat on the left wall cap
    def cat(L=near, Z=Zc):
        X = cam.lane(Z) - half
        E = cam.g(Z) + 1.1
        unit = cam.f / Z
        (cx_, cy_) = P(X, Z, E)
        bw, bh = unit * 0.42, unit * 0.2
        fur = K['brn1'] * 1.1
        rim = mix(K['amber'], K['cream'], 0.4)
        L.ellipse(cx_, cy_ - bh, bw, bh, fur)
        L.ellipse(cx_ + bw * 0.75, cy_ - bh * 1.05, bh * 0.85, bh * 0.75, fur)
        for e in (-1, 1):
            ex = cx_ + bw * 0.75 + e * bh * 0.4
            L.poly([(ex - bh * 0.25, cy_ - bh * 1.6), (ex + bh * 0.25, cy_ - bh * 1.6), (ex, cy_ - bh * 2.15)], fur)
        # tail curled round the front
        L.lines([(cx_ - bw * 0.9, cy_ - bh * 0.4), (cx_ - bw * 0.3, cy_ + 1), (cx_ + bw * 0.5, cy_)], fur, width=max(1, int(bh * 0.35)))
        # rim light from the lamp along the top of the back
        for k in range(int(bw * 1.6)):
            xx = cx_ - bw * 0.8 + k
            yy = cy_ - bh - bh * math.sqrt(max(0, 1 - ((xx - cx_) / bw) ** 2))
            L.px(xx, yy, rim)
        # closed eye
        L.px(cx_ + bw * 0.85, cy_ - bh * 1.05, K['navy0'])
        L.px(cx_ + bw * 0.85 + 1, cy_ - bh * 1.05, K['navy0'])
        A.d['cat'] = dict(x=int(cx_ - bw), y=int(cy_ - bh * 2.2), w=int(bw * 2 + bh * 1.6), h=int(bh * 2.2), layer='near', head=[int(cx_ + bw * 0.75), int(cy_ - bh * 1.05)], tail=[int(cx_ - bw * 0.9), int(cy_ - bh * 0.4)])
    T.add(Zc - 0.3, 'near', cat)
    # vending machine in a recess on the right
    Zv = T.spots['vend']
    def vend(L=near, Z=Zv):
        X = cam.lane(Z) + half + 0.2
        E = cam.g(Z)
        unit = cam.f / Z
        (x0, y0) = P(X, Z, E + 1.85)
        (x1, y1) = P(X + 1.0, Z, E)
        w, h = x1 - x0, y1 - y0
        # side (seen in perspective) and the body
        sq = [P(X, Z, E), P(X, Z + 0.75, E), P(X, Z + 0.75, E + 1.85), P(X, Z, E + 1.85)]
        L.poly(sq, mix(K['conc'], K['cool'], 0.25))
        L.rect(x0, y0, w, h, mix(K['conc'], K['cool'], 0.45))
        L.rect(x0 + 2, y0 + 2, w - 4, h * 0.45, K['cool'])
        # product rows: little bottles in invented colours
        rows = 3
        cols = max(4, int(w / 5))
        for r in range(rows):
            ry_ = y0 + 4 + r * (h * 0.42 / rows)
            for c in range(cols):
                cx_ = x0 + 4 + c * (w - 8) / cols
                bc = [K['red2'], K['tv'], K['green'], K['amber'], K['pinkL'], K['cream'], K['tv2']][int(rng.random() * 7)]
                bw_ = max(1, (w - 8) / cols - 2)
                L.rect(cx_, ry_ + 2, bw_, h * 0.42 / rows - 5, bc * 0.85)
                L.rect(cx_, ry_ + 1, bw_, 1, mix(bc, K['cool'], 0.5))
                # price tag with button
                L.rect(cx_, ry_ + h * 0.42 / rows - 3, bw_, 1, K['navy1'])
                L.px(cx_ + bw_ / 2, ry_ + h * 0.42 / rows - 2, K['redL'] if rng.random() < 0.4 else K['green'] * 1.5)
        # panel below: coin slot, a tiny display, the pickup bay
        L.rect(x0 + w * 0.7, y0 + h * 0.55, w * 0.15, h * 0.12, mix(K['conc'], K['navy1'], 0.5))
        L.rect(x0 + w * 0.72, y0 + h * 0.57, w * 0.1, 2, K['green'] * 1.6)
        L.rect(x0 + w * 0.1, y0 + h * 0.8, w * 0.8, h * 0.12, K['navy0'])
        L.rect(x0 + w * 0.12, y0 + h * 0.6, w * 0.45, h * 0.14, mix(K['cool'], K['tv'], 0.4))
        for k in range(3):
            L.rect(x0 + w * 0.15 + k * w * 0.13, y0 + h * 0.64, w * 0.08, h * 0.05, K['navy1'])
        L.rect(x0, y0, w, 2, mix(K['cool'], K['halo'], 0.2))
        T.lights.append(dict(x=x0 + w / 2, y=y0 + h * 0.4, r=unit * 3.5, ry=unit * 2.4, col=K['cool'], k=0.32, layer='near', kind='vending', air=True, pool=(x0 + w / 2, y1)))
        L.lock[int(y0):int(y1), int(x0):int(x1)] = True
        A.d['vending'] = dict(x=int(x0), y=int(y0), w=int(w), h=int(h), layer='near', panel=[int(x0 + 2), int(y0 + 2), int(w - 4), int(h * 0.45)])
        A.d['lamps'].append(dict(x=int(x0 + w / 2), y=int(y0 + h * 0.4), r=int(unit * 5.5), kind='vending', layer='near', bulb=[int(x0 + 2), int(y0 + 2), int(w - 4), int(h * 0.45)]))
        # a bench beside it
        (bx0, by0) = P(X + 1.25, Z - 0.1, E + 0.45)
        (bx1, by1) = P(X + 2.6, Z - 0.1, E)
        L.rect(bx0, by0, bx1 - bx0, max(2, unit * 0.08), fz(K['brn2'], Z))
        L.rect(bx0 + 2, by0, max(1, unit * 0.06), by1 - by0, fz(K['navy0'], Z))
        L.rect(bx1 - 3, by0, max(1, unit * 0.06), by1 - by0, fz(K['navy0'], Z))
        A.d['bench'] = dict(x=int(bx0), y=int(by0), w=int(bx1 - bx0), h=int(by1 - by0), layer='near')
        # a can on the bench
        L.rect(bx0 + (bx1 - bx0) * 0.7, by0 - unit * 0.12, max(1, unit * 0.06), unit * 0.12, K['red2'])
    T.add(Zv - 0.4, 'near', vend)
    # the mailbox (red cylinder) on the left, further down
    Zm = T.spots['mail']
    def mailbox(L=near, Z=Zm):
        X = cam.lane(Z) - half - 0.5
        E = cam.g(Z)
        unit = cam.f / Z
        (x0, y0) = P(X - 0.25, Z - 0.6, E + 1.3)
        (x1, y1) = P(X + 0.25, Z - 0.6, E)
        w = x1 - x0
        def mc(Xg, Yg):
            u = (Xg - x0) / max(1, w)
            sh = 0.6 + 0.5 * np.sin(np.clip(u, 0, 1) * math.pi * 0.9 + 0.3)
            return K['red'] * sh[..., None]
        L.rect(x0, y0 + w * 0.3, w, y1 - y0 - w * 0.3, mc)
        L.ellipse(x0 + w / 2, y0 + w * 0.3, w / 2, w * 0.3, mix(K['red2'], K['halo'], 0.2))
        L.rect(x0 + w * 0.2, y0 + (y1 - y0) * 0.3, w * 0.6, max(1, unit * 0.05), K['navy0'])
        L.rect(x0 + w * 0.3, y0 + (y1 - y0) * 0.5, w * 0.4, max(1, unit * 0.15), mix(K['cream'], K['red'], 0.4))
        L.rect(x0 - 1, y1 - max(2, unit * 0.1), w + 2, max(2, unit * 0.1), K['navy0'])
        A.d['mailbox'] = dict(x=int(x0), y=int(y0), w=int(w), h=int(y1 - y0), layer='near')
    T.add(Zm - 0.7, 'near', mailbox)
    # bicycles leaning on walls
    for (Zb, side) in ((Znear + 13, 1), (Znear + 22, -1), (Znear + 41, 1)):
        layer = 'mid' if Zb >= Zcut else 'near'
        def bike(L=Ls[layer], Z=Zb, side=side, layer=layer):
            X = cam.lane(Z) + side * (half - 0.15)
            E = cam.g(Z)
            unit = cam.f / Z
            (cx0, cy0) = P(X, Z - 0.6, E + 0.33)
            (cx1, cy1) = P(X, Z + 0.6, E + 0.33)
            r0 = unit * 0.33 * (Z / (Z - 0.6))
            r1 = unit * 0.33 * (Z / (Z + 0.6))
            fc = [K['tv2'], K['red'], K['conc'], K['green']][int(rng.random() * 4)]
            fc = mix(fc, K['halo'], 0.2)
            for (cx_, cy_, rr) in ((cx0, cy0, r0), (cx1, cy1, r1)):
                n = max(12, int(rr * 6))
                pts = [(cx_ + rr * 0.35 * math.cos(a), cy_ + rr * math.sin(a)) for a in np.linspace(0, 2 * math.pi, n)]
                L.lines(pts, fz(mix(K['navy0'], K['halo'], 0.25), Z))
            (sx_, sy_) = P(X, Z - 0.1, E + 0.85)
            (hx_, hy2) = P(X, Z + 0.45, E + 1.0)
            L.lines([(cx0, cy0), (sx_, sy_), (cx1, cy1), ((cx0 + cx1) / 2, (cy0 + cy1) / 2 + 1), (cx0, cy0)], fz(fc, Z))
            L.lines([(hx_, hy2), (cx1, cy1)], fz(fc, Z))
            L.lines([(hx_ - unit * 0.1, hy2), (hx_ + unit * 0.1, hy2)], fz(K['navy0'], Z), width=max(1, int(unit * 0.04)))
            L.rect(sx_ - unit * 0.06, sy_ - unit * 0.04, unit * 0.14, max(1, unit * 0.05), fz(K['navy0'], Z))
            # a basket on the front
            L.rect(hx_ - unit * 0.12, hy2 + 1, unit * 0.24, unit * 0.16, fz(mix(K['conc'], K['halo'], 0.2), Z))
            A.d['bikes'].append(dict(x=int(min(cx0, cx1) - r0 * 0.4), y=int(hy2), w=int(abs(cx1 - cx0) + r0), h=int(cy0 + r0 - hy2), layer=layer))
        T.add(Zb - 0.3, layer, bike)
    # the shrine gate on a side path to the left, with its lantern
    Zt = T.spots['torii']
    def torii(L=Ls['near' if Zt < Zcut else 'mid'], Z=Zt):
        X = cam.lane(Z) - half - 3.8
        E = cam.g(Z) + 0.6
        unit = cam.f / Z
        tc = mix(K['red'], K['navy0'], 0.25)
        th = mix(K['red2'], K['halo'], 0.15)
        for dxp in (-1.0, 1.0):
            (x0, y0) = P(X + dxp, Z, E)
            (_, y1) = P(X + dxp, Z, E + 3.0)
            pw = max(2, unit * 0.18)
            L.rect(x0 - pw / 2, y1, pw, y0 - y1, tc)
            L.rect(x0 + pw / 2 - 1, y1, 1, y0 - y1, th)
        (a0, ay) = P(X - 1.6, Z, E + 3.15)
        (a1, _) = P(X + 1.6, Z, E + 3.15)
        L.poly([(a0 - unit * 0.15, ay - unit * 0.22), (a1 + unit * 0.15, ay - unit * 0.22), (a1, ay + unit * 0.05), (a0, ay + unit * 0.05)], K['navy0'])
        L.rect(a0, ay + unit * 0.05, a1 - a0, unit * 0.12, tc)
        (b0, by_) = P(X - 1.3, Z, E + 2.6)
        (b1, _) = P(X + 1.3, Z, E + 2.6)
        L.rect(b0, by_, b1 - b0, max(1, unit * 0.12), tc)
        (pl_x, pl_y) = P(X, Z, E + 2.75)
        L.rect(pl_x - unit * 0.12, pl_y, unit * 0.24, unit * 0.32, mix(K['navy0'], K['brn2'], 0.4))
        # small shrine roof behind and a hanging lantern
        T.house(L, X - 1.2, X + 1.2, Z + 4, 2.0, 1.2, 'gable', 'near', wall=K['brn1'])
        (lx_, ly_) = P(X + 1.6, Z - 0.3, E + 1.5)
        L.lines([(lx_, ly_ - unit * 0.5), (lx_, ly_)], K['navy0'])
        # the lantern itself is the life lane's (it sways); only its hook and cord are baked
        L.rect(lx_ - 1, ly_ - unit * 0.5, 3, 1, K['navy0'])
        T.lights.append(dict(x=lx_, y=ly_ + unit * 0.22, r=unit * 2.4, col=mix(K['red2'], K['amber'], 0.5), k=0.5, layer='near', kind='lantern', air=True))
        A.d['shrine'] = dict(x=int(P(X - 1.6, Z, E)[0]), y=int(ay - unit * 0.22), w=int(a1 - a0 + unit * 0.3), h=int(P(X, Z, E)[1] - ay), layer='near',
                             lantern=[int(lx_), int(ly_ + unit * 0.22)], hang=[int(lx_), int(ly_ - unit * 0.5)])
        A.d['lamps'].append(dict(x=int(lx_), y=int(ly_ + unit * 0.22), r=int(unit * 2.4), kind='lantern', layer='near', bulb=[int(lx_ - unit * 0.1), int(ly_), max(1, int(unit * 0.2)), max(1, int(unit * 0.4))]))
    T.add(Zt - 0.3, 'near', torii)
    # potted plants lining the lane edges
    for k in range(60):
        Zp = Znear + 1 + (rng.random() ** 1.6) * (Zfar - Znear - 30)
        side = -1 if rng.random() < 0.5 else 1
        if any(abs(Zp - T.spots[n]) < 2.5 for n in ('cat', 'mail', 'vend', 'torii')):
            continue
        layer = 'mid' if Zp >= Zcut else 'near'
        T.add(Zp - 0.05, layer, (lambda L=Ls[layer], Zp=Zp, side=side, layer=layer: T.plant(L, cam.lane(Zp) + side * (half - 0.25), Zp, cam.g(Zp), Zp, layer, size=0.5 + rng.random() * 0.6)))
    # a little neon sign of a snack bar at the bottom of the lane
    Zn = T.spots['neon']
    def neon(L=Ls['near' if Zn < Zcut else 'mid'], Z=Zn):
        X = cam.lane(Z) + half + 0.05
        E = cam.g(Z)
        unit = cam.f / Z
        (x0, y0) = P(X, Z, E + 2.8)
        sw, sh = max(4, unit * 0.35), max(10, unit * 1.3)
        L.rect(x0, y0, sw, sh, mix(K['navy0'], K['mag'], 0.3))
        L.rect(x0, y0, sw, 1, K['pinkL'])
        L.rect(x0, y0 + sh - 1, sw, 1, K['pinkL'])
        L.rect(x0, y0, 1, sh, K['pinkL'])
        L.rect(x0 + sw - 1, y0, 1, sh, K['pinkL'])
        # unreadable glyphs
        for k in range(4):
            gy = y0 + 2 + k * (sh - 4) / 4
            L.rect(x0 + 1 + (k % 2), gy, sw - 3, 1, mix(K['pinkL'], K['cream'], 0.4))
            L.px(x0 + sw / 2, gy + 1, K['pinkL'])
        T.lights.append(dict(x=x0 + sw / 2, y=y0 + sh / 2, r=unit * 2.2, col=K['pinkL'], k=0.45, layer=L.name, kind='neon', air=True))
        A.d['signs'].append(dict(x=int(x0), y=int(y0), w=int(sw), h=int(sh), layer=L.name, neon=True))
    T.add(Zn - 0.3, 'near' if Zn < Zcut else 'mid', neon)
    # paths for walkers: the lane centre line from bottom to rail
    A.d['paths'].append(dict(pts=[[int(x), int(y)] for x, y in centre[::3]], layer='near', kind='lane'))


# ================================================================== FG: pole, wires, dripping leaves
def draw_fg(L, cam, A, rng, V):
    W, H = L.W, L.H
    # a big utility pole at the right, off the top, with a transformer and wires across the sky
    px_ = int(W * 0.935) if W > 1500 else int(W * 0.94)
    pw = 34 if W > 2000 else 30
    pc = mix(K['navy0'], K['conc'], 0.25)
    L.rect(px_, -10, pw, H + 20, pc)
    L.rect(px_ + pw - 6, -10, 4, H + 20, mix(K['conc'], K['halo'], 0.3))
    L.rect(px_ + 4, -10, 2, H + 20, mix(K['navy0'], K['conc'], 0.4))
    # rungs (step bolts)
    for y in range(int(H * 0.35), H, 46):
        L.rect(px_ - 10, y, 12, 3, pc)
        L.rect(px_ + pw - 2, y + 23, 12, 3, pc)
    # crossarms and insulators
    arms = []
    for k, y in enumerate((int(H * 0.07), int(H * 0.14))):
        L.rect(px_ - 150, y, pw + 300, 10, pc)
        L.rect(px_ - 150, y, pw + 300, 2, mix(K['conc'], K['halo'], 0.35))
        for j in range(-2, 3):
            ix = px_ + pw // 2 + j * 66
            L.rect(ix - 4, y - 14, 9, 14, mix(K['conc'], K['halo'], 0.45))
            for r in range(3):
                L.rect(ix - 6, y - 12 + r * 4, 13, 2, mix(K['cream'], K['halo'], 0.5))
            arms.append((ix, y - 14))
    # transformer can
    ty = int(H * 0.2)
    L.rect(px_ - 64, ty, 56, 96, mix(K['conc'], K['tv2'], 0.2))
    L.rect(px_ - 64, ty, 6, 96, mix(K['conc'], K['halo'], 0.4))
    L.rect(px_ - 64, ty, 56, 6, mix(K['conc'], K['halo'], 0.3))
    for r in range(4):
        L.rect(px_ - 58, ty + 18 + r * 18, 50, 2, mix(K['navy0'], K['conc'], 0.3))
    L.rect(px_ - 8, ty + 20, 8, 8, pc)
    L.rect(px_ - 8, ty + 70, 8, 8, pc)
    L.rect(px_ - 50, ty + 40, 22, 14, mix(K['cream'], K['halo'], 0.5))       # a plate: unreadable marks
    for k in range(4):
        L.rect(px_ - 47, ty + 43 + k * 3, 6 + (k * 5) % 13, 1, K['navy1'])
    # a street lamp on the pole, its bulb low warm
    ly = int(H * 0.48)
    L.lines([(px_, ly), (px_ - 70, ly - 18), (px_ - 110, ly - 12)], pc, width=5)
    L.poly([(px_ - 132, ly - 8), (px_ - 88, ly - 8), (px_ - 98, ly - 20), (px_ - 122, ly - 20)], pc)
    L.rect(px_ - 126, ly - 8, 32, 3, K['cream'])
    A.d['lamps'].append(dict(x=px_ - 110, y=ly - 6, r=260, kind='street', layer='fg', bulb=[px_ - 126, ly - 8, 32, 3]))
    # wires: from the insulators out of frame and down to the town
    wires = []
    for j, (ix, iy) in enumerate(arms[:5]):
        tx = int(W * (0.60 + 0.045 * j))
        ty_ = int(H * (0.66 + 0.02 * j))
        sag = 30 + 15 * (j % 3)
        pts = L.catenary(ix, iy, tx, ty_, sag, mix(K['navy0'], K['navy1'], 0.5), width=2 if j < 5 else 1)
        wires.append(dict(pts=[[int(x), int(y)] for x, y in pts[::4]], layer='fg', kind='power'))
    # service drops toward the right edge
    for j in range(3):
        ix, iy = arms[j * 3]
        pts = L.catenary(ix, iy, W + 30, int(H * (0.25 + 0.1 * j)), 30, mix(K['navy0'], K['navy1'], 0.5), width=2)
        wires.append(dict(pts=[[int(x), int(y)] for x, y in pts[::4]], layer='fg', kind='power'))
    A.d['wires'] += wires
    # raindrops beaded on the lower wires (a few highlights)
    for w_ in wires[:6]:
        for (x, y) in w_['pts'][2::3]:
            if 0 <= x < W and 0 <= y < H and rng.random() < 0.5:
                L.px(x, y + 2, mix(K['halo'], K['moon'], 0.5))
    # ---- dripping leaves: a camellia branch top-right, a maple top-left
    drips = []
    def branch(x0, y0, x1, y1, n, scale, maple=False, flip=1):
        pts = [(x0 + (x1 - x0) * t + math.sin(t * 5) * 10, y0 + (y1 - y0) * t + math.sin(t * 3) * 14) for t in np.linspace(0, 1, 20)]
        L.lines(pts, mix(K['brn0'], K['navy0'], 0.3), width=int(6 * scale))
        for k in range(n):
            t = rng.random()
            bx_, by_ = pts[int(t * 19)]
            a = rng.random() * math.pi * 2
            ln = (18 + rng.random() * 30) * scale
            lx, ly = bx_ + math.cos(a) * ln, by_ + abs(math.sin(a)) * ln * 0.8 + 6
            L.lines([(bx_, by_), (lx, ly)], mix(K['brn0'], K['navy0'], 0.3), width=max(1, int(2 * scale)))
            leaf(lx, ly, a, scale * (0.8 + rng.random() * 0.6), maple)

    def leaf(cx_, cy_, a, s, maple):
        ln, wd = 34 * s, 14 * s
        ang = a * 0.3 + math.pi / 2 * 0.85 + (rng.random() - 0.5) * 0.9
        ca, sa = math.cos(ang), math.sin(ang)
        if maple:
            pts = []
            for i in range(10):
                t = i / 10 * 2 * math.pi
                r = ln * 0.55 * (0.55 + 0.45 * abs(math.cos(t * 2.5)))
                pts.append((cx_ + math.cos(t) * r, cy_ + math.sin(t) * r))
        else:
            pts = []
            for i in range(14):
                t = i / 14 * 2 * math.pi
                px0 = math.cos(t) * ln * 0.5
                py0 = math.sin(t) * wd * 0.5
                pts.append((cx_ + px0 * ca - py0 * sa, cy_ + px0 * sa + py0 * ca))
        lc = mix(K['leaf'], K['navy0'], rng.random() * 0.4)
        L.poly(pts, lc)
        # wet sheen: a moonlit edge on the upper side, a vein
        top = sorted(pts, key=lambda p: p[1])[:4]
        L.lines(top[:2], mix(K['leafH'], K['halo'], 0.4))
        if not maple:
            L.lines([(cx_ - ca * ln * 0.45, cy_ - sa * ln * 0.45), (cx_ + ca * ln * 0.45, cy_ + sa * ln * 0.45)], mix(K['leaf'], K['leafH'], 0.6))
        tip = max(pts, key=lambda p: p[1])
        if rng.random() < 0.45:
            # a hanging drop at the lowest point
            L.ellipse(tip[0], tip[1] + 2.5 * s, 1.8 * s, 2.4 * s, mix(K['halo'], K['navy1'], 0.3))
            L.px(tip[0] - 0.5 * s, tip[1] + 1.6 * s, K['moon'])
            drips.append(dict(x=int(tip[0]), y=int(tip[1] + 2.5 * s), layer='fg'))
        if not maple and rng.random() < 0.08:
            # a camellia flower, deep pink
            L.ellipse(cx_ + 8 * s, cy_ - 6 * s, 9 * s, 7 * s, mix(K['red'], K['mag'], 0.5))
            L.ellipse(cx_ + 8 * s, cy_ - 7 * s, 3 * s, 2.5 * s, mix(K['amber'], K['red2'], 0.4))
    S = 1.0 if W > 2000 else 0.9
    branch(W + 30, -20, W * 0.86, H * 0.10, 50, S)
    branch(W + 20, H * 0.06, W * 0.90, H * 0.24, 34, S * 0.9)
    branch(-30, -30, W * 0.18, H * 0.09, 55, S, maple=True)
    A.d['drips'] = drips
    # bottom-left corner: the near railing of the viewpoint and a big hydrangea
    ry = H - int(H * 0.06)
    rc = mix(K['navy0'], K['conc'], 0.3)
    L.rect(-4, ry, int(W * 0.24), 8, rc)
    L.rect(-4, ry, int(W * 0.24), 2, mix(K['conc'], K['halo'], 0.4))
    for x in range(10, int(W * 0.24), 70):
        L.rect(x, ry, 8, H - ry, rc)
    for k in range(40):
        cx_ = rng.random() * W * 0.14
        cy_ = H - rng.random() * H * 0.12
        r = 10 + rng.random() * 22
        L.ellipse(cx_, cy_, r * 1.3, r, mix(K['leaf'], K['navy0'], rng.random() * 0.5))
    for k in range(9):
        cx_ = rng.random() * W * 0.12
        cy_ = H - H * 0.06 - rng.random() * H * 0.05
        r = 14 + rng.random() * 10
        L.ellipse(cx_, cy_, r, r * 0.85, mix(K['tv2'], K['purp'], rng.random()) * 0.55)
        for j in range(18):
            a = rng.random() * 6.28
            d = rng.random() * r
            L.px(cx_ + math.cos(a) * d, cy_ + math.sin(a) * d * 0.85, mix(K['tv'], K['halo'], 0.4) * 0.7)


# ================================================================== lights
def apply_lights(Ls, lights, order):
    """light pools on surfaces (own layer) and halos in the moist air (own + behind)."""
    for lt in lights:
        li = order.index(lt['layer'])
        L = Ls[lt['layer']]
        r = lt['r']
        ry = lt.get('ry', r)
        col = np.asarray(lt['col'], F)
        L.glow(lt['x'], lt['y'], r, ry=ry, col=col, k=lt['k'], falloff=1.6)
        if 'pool' in lt:
            px_, py_ = lt['pool']
            L.glow(px_, py_, r * 1.0, ry=r * 0.3, col=col, k=lt['k'] * 0.7, falloff=1.5)
            # the wet-stone streak: reflection straight down from the lamp
            L.glow(px_, py_ + r * 0.15, max(2, r * 0.06), ry=r * 0.4, col=col, k=lt['k'] * 0.6, falloff=1.2)
        if lt.get('air'):
            for name in order[:li + 1]:
                Ls[name].glow(lt['x'], lt['y'], r * 0.8, ry=r * 0.8, col=col, k=lt['k'] * 0.22, falloff=2.6)


# ================================================================== output
def cull_hidden(Ls, order, margin):
    from scipy.ndimage import binary_erosion
    cover = np.zeros_like(Ls[order[-1]].a)
    for name in reversed(order):
        L = Ls[name]
        if cover.any():
            hidden = binary_erosion(cover, iterations=margin, border_value=1)
            L.a &= ~hidden
        cover |= Ls[name].a


def mood_palettes(pal, L, img, name, hyf=0.3):
    """four time-of-night palettes per layer: rain, deep (as drawn), predawn, dawn.
    roles are measured from the pixels that use each entry: mean height, emissive share."""
    H, W = img.shape
    yy = np.repeat(np.arange(H)[:, None], W, 1)
    n = len(pal)
    meany = np.zeros(n); emis = np.zeros(n)
    flat = img.ravel()
    cnt = np.bincount(flat, minlength=n + 1)[1:] + 1e-6
    meany = np.bincount(flat, weights=yy.ravel(), minlength=n + 1)[1:] / cnt / H
    lk = L.lock if L.lock is not None else np.zeros_like(L.a)
    emis = np.bincount(flat, weights=lk.ravel().astype(float), minlength=n + 1)[1:] / cnt
    out = {}
    lum = pal @ np.array([0.3, 0.55, 0.15])
    sat = pal.max(1) - pal.min(1)
    warm = np.clip((pal[:, 0] - pal[:, 2]) * 2, 0, 1)
    light = np.clip(np.maximum(emis, smooth(0.45, 0.75, lum) * (warm * 0.7 + 0.3)), 0, 1)
    def skygrad(y):
        stops = [(0.0, C('#24306a')), (0.35, C('#4c5694')), (0.62, C('#8a84b8')), (0.8, C('#d0949e')), (0.95, C('#f4b88e')), (1.2, C('#f8c8a0'))]
        out_ = np.zeros((len(y), 3))
        for i, yy in enumerate(y):
            for (a_, ca), (b_, cb) in zip(stops, stops[1:]):
                if yy <= b_:
                    out_[i] = mix(ca, cb, clamp((yy - a_) / (b_ - a_)))
                    break
            else:
                out_[i] = stops[-1][1]
        return out_
    mlum = (lum * cnt).sum() / cnt.sum()
    def grade(lift, tint, light_k, sky_dawn=0.0, desat=0.0):
        p = pal.copy()
        g = p.mean(1, keepdims=True)
        p = mix(p, g, desat * (1 - light[:, None]))
        p = p * (1 + lift * 2.2 * (1 - light[:, None])) + (1 - light[:, None]) * (np.asarray(tint) * lift)
        p = mix(p, p * light_k, light[:, None])
        if sky_dawn and name == 'sky':
            d = skygrad(meany / hyf)
            keep = smooth(0.5, 0.7, lum)[:, None]           # the moon and the stars keep their own light
            tgt = d * np.clip(0.85 + 0.9 * (lum[:, None] - mlum), 0.55, 1.3)
            p = mix(p, tgt, sky_dawn * (1 - keep))
        return np.clip(p, 0, 1)
    out['rain'] = grade(0.03, (0.30, 0.08, 0.40), 1.05, desat=-0.08)
    out['deep'] = pal.copy()
    out['predawn'] = grade(0.05, (0.02, 0.08, 0.30), 0.75, sky_dawn=0.45, desat=0.25)
    out['dawn'] = grade(0.14, (0.05, 0.09, 0.22), 0.4, sky_dawn=0.95, desat=0.3)
    return {k: (np.round(v * 255).astype(int)).tolist() for k, v in out.items()}


def build(variant, preview_dir=None):
    t0 = time.time()
    V = VARIANTS[variant]
    W, H = V['W'], V['H']
    cam = Cam(V)
    A = Anchors()
    order = ['sky', 'far', 'mid', 'near', 'fg']
    Ls = {n: Layer(n, W, H) for n in order}
    for n in order:
        Ls[n].lock = np.zeros((H, W), bool)
        Ls[n].wid = np.zeros((H, W), np.int32)
        Ls[n].own = np.zeros((H, W), np.int32)
    kit.GROUP[0] = 1
    lights = []
    draw_sky(Ls['sky'], cam, A, rng_for('sky', variant), V)
    print(variant, 'sky', round(time.time() - t0, 1)); sys.stdout.flush()
    draw_far(Ls['far'], cam, A, rng_for('far', variant), V)
    draw_shore(Ls['far'], cam, A, rng_for('shore', variant), V, lights)
    print(variant, 'far', round(time.time() - t0, 1)); sys.stdout.flush()
    draw_town(Ls, cam, A, rng_for('town', variant), V, lights)
    print(variant, 'town', round(time.time() - t0, 1)); sys.stdout.flush()
    kit.GROUP[0] += 1
    draw_fg(Ls['fg'], cam, A, rng_for('fg', variant), V)
    apply_lights(Ls, lights, order)
    print(variant, 'lights', round(time.time() - t0, 1)); sys.stdout.flush()
    # keep only windows that still show >= 90% of their own pixels in the final stack
    upper = {}
    acc = np.zeros((H, W), bool)
    for name in reversed(order):
        upper[name] = acc.copy()
        acc |= Ls[name].a
    kept, dropped = [], 0
    for i, w_ in enumerate(A.d['windows']):
        x, y, ww, hh, ln = w_[0], w_[1], w_[2], w_[3], w_[9]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + ww), min(H, y + hh)
        if x1 <= x0 or y1 <= y0:
            dropped += 1
            continue
        own = (Ls[ln].wid[y0:y1, x0:x1] == i + 1) & ~upper[ln][y0:y1, x0:x1]
        if os.environ.get('SCENE_DEBUG'):
            o1 = float((Ls[ln].wid[y0:y1, x0:x1] == i + 1).mean()); o2 = float(upper[ln][y0:y1, x0:x1].mean())
            DBG.append((ln, o1, o2, x, y, ww, hh))
        if own.sum() >= 0.9 * ww * hh:
            kept.append(w_)
        else:
            dropped += 1
    A.d['windows'] = kept
    print(variant, 'windows kept', len(kept), 'dropped', dropped)
    # every other anchor: visible only if nothing drawn later (same layer) or nearer (upper layers) covers it
    def vis(ln, g, x0, y0, x1, y1):
        x0, y0 = int(max(0, x0)), int(max(0, y0))
        x1, y1 = int(min(W, max(x1, x0 + 1))), int(min(H, max(y1, y0 + 1)))
        if x1 <= x0 or y1 <= y0:
            return 0.0
        ok = (Ls[ln].own[y0:y1, x0:x1] <= g) & ~upper[ln][y0:y1, x0:x1]
        return float(ok.mean())

    def test(a):
        if not isinstance(a, dict) or '_g' not in a or a.get('layer') not in Ls:
            return True
        ln, g = a['layer'], a.pop('_g')
        if 'arms' in a:
            a['arms'] = [p for p in a['arms'] if vis(ln, g, p[0] - 1, p[1] - 1, p[0] + 2, p[1] + 2) >= 0.9]
        if 'bulb' in a:
            b_ = a['bulb']
            return vis(ln, g, b_[0], b_[1], b_[0] + b_[2], b_[1] + b_[3]) >= 0.9
        if 'w' in a and 'h' in a and 'x' in a:
            return vis(ln, g, a['x'], a['y'], a['x'] + a['w'], a['y'] + a['h']) >= 0.9
        if 'x0' in a:
            return vis(ln, g, a['x0'], a['y'] - 1, a['x1'], a['y'] + 1) >= 0.9
        if 'pts' in a:
            return True
        if 'x' in a:
            return vis(ln, g, a['x'] - 1, a['y'] - 1, a['x'] + 2, a['y'] + 2) >= 0.9
        return True
    stats = {}
    for k in list(A.d.keys()):
        v = A.d[k]
        if isinstance(v, list) and k not in ('windows', 'far'):
            keep = [a for a in v if test(a)]
            stats[k] = (len(keep), len(v))
            dict.__setitem__(A.d, k, list(keep))
        elif isinstance(v, dict) and '_g' in v:
            if not test(v):
                v['visible'] = 0
                stats[k] = 'hidden'
            dict.__setitem__(A.d, k, dict(v))
    print(variant, 'anchor visibility', stats)
    for n in order:
        Ls[n].wid = None
        Ls[n].own = None
    cull_hidden(Ls, order, margin=14)
    os.makedirs(OUT_IMG, exist_ok=True)
    Kq = dict(sky=40, far=48, mid=56, near=64, fg=32)
    layers = {}
    depth = dict(sky=0.0, far=0.12, mid=0.3, near=0.55, fg=1.0)
    flat = np.zeros((H, W, 3), np.uint8)
    total = 0
    for z, n in enumerate(order):
        L = Ls[n]
        img, pal = quantize(L.rgb, L.a, K=Kq[n], seed=7 + z)
        fn = f'{variant}-{n}.png'
        path = os.path.join(OUT_IMG, fn)
        plist = save_indexed(path + '.tmp', img, pal)
        PENDING.append((path + '.tmp', path))
        palq = np.array(plist, float) / 255.0
        sz = os.path.getsize(path + '.tmp')
        total += sz
        moods = mood_palettes(palq, L, img, n, cam.hy / H)
        moods['deep'] = plist
        layers[n] = dict(src=f'scene/img/{fn}', depth=depth[n], z=z, bytes=sz, palette=plist, moods=moods)
        pl = np.array([[0, 0, 0]] + plist, np.uint8)
        m = img > 0
        flat[m] = pl[img[m]]
        print(variant, n, 'colours', len(pal), 'bytes', sz, round(time.time() - t0, 1)); sys.stdout.flush()
    print(variant, 'total bytes', total)
    if preview_dir:
        from PIL import Image
        Image.fromarray(flat).save(os.path.join(preview_dir, f'{variant}-flat.png'))
    d = A.d
    d['windowsFields'] = ['x', 'y', 'w', 'h', 'lit', 'baked', 'hue', 'curtain', 'room', 'layer', 'dark']
    return dict(w=W, h=H, pad=16, focus=V.get('focus', [0.62, 0.47]), layers=layers, order=order, anchors=d,
                camera=dict(hy=cam.hy, f=cam.f, cx=cam.cx)), total


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    pdir = None
    if '--preview' in sys.argv:
        pdir = sys.argv[sys.argv.index('--preview') + 1]
    vs = ['desktop', 'hd', 'portrait'] if which == 'all' else [which]
    doc = dict(version=2, seed=SEED, moods=['rain', 'deep', 'predawn', 'dawn'],
               moodTimes=dict(rain=19.5, deep=24.5, predawn=27.8, dawn=29.5), variants={})
    if os.path.exists(OUT_JSON):
        try:
            old = json.load(open(OUT_JSON))
            doc['variants'].update(old.get('variants', {}))
        except Exception:
            pass
    for v in vs:
        doc['variants'][v], _ = build(v, pdir)
    # images first, the anchors last, each by rename: a page never pairs new anchors with old art
    for tmp, final in PENDING:
        os.replace(tmp, final)
    with open(OUT_JSON + '.tmp', 'w') as fh:
        json.dump(doc, fh, separators=(',', ':'))
    os.replace(OUT_JSON + '.tmp', OUT_JSON)
    print('wrote', OUT_JSON, os.path.getsize(OUT_JSON))


if __name__ == '__main__':
    main()
