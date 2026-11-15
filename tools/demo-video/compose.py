#!/usr/bin/env python3
"""The tour's editor: an edit list (edit.py) -> 1920x1080 frames, a mixed soundtrack, captions (.srt) -> MP4.

    compose.py ROOT OUT.mp4 [--cut spot|long] [--jobs 8] [--from S --to S] [--frames T1,T2,.. --sheet OUT.png]

ROOT holds cap/<scene>/{cap.bhrc,editor.wav} (shoot.py), tts/<id>.wav + lines.json (tts.py), music/*.mp3, art/*,
fonts/*. Everything on screen is drawn here: the Windows screen is copied pixel for pixel (whole-number scales,
nearest neighbour); the host comes from presenter.py; cards, bars, wipes and the motion trail are drawn from code.
"""
import argparse, json, math, os, subprocess, sys, tempfile
from collections import OrderedDict
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bhrc import Capture
from presenter import Presenter, W as PW, H as PH

FPS = 30
W, H = 1920, 1080
SR = 48000
SCR_X, SCR_Y = 88, 92                       # the Windows screen at 1x in the wide layout
ROOT = '.'
STYLE = os.environ.get('HOST_STYLE', 'drawn')   # 'drawn' (presenter.py) or 'ai' (the Grok Imagine stills in grok/)


def font(name, size):
    return ImageFont.truetype(os.path.join(ROOT, 'fonts', name), size)


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


# ------------------------------------------------------------------ backgrounds and frames
_cache = {}


def background():
    if 'bg' in _cache: return _cache['bg']
    if STYLE == 'ai':
        im = Image.open(os.path.join(ROOT, 'grok', 'px', 'bg_grid.png')).convert('RGB')   # pixel art (pixel_ai.py): 6x
        im = im.resize((im.width * (W // im.width), im.height * (W // im.width)), Image.NEAREST).crop((0, 0, W, H))
        _cache['bg'] = np.asarray(im).copy()
        return _cache['bg']
    y = np.linspace(0, 1, H)[:, None, None]
    x = np.linspace(0, 1, W)[None, :, None]
    top = np.array([18, 70, 112]); bot = np.array([52, 24, 86])
    img = top * (1 - y) + bot * y + np.array([20, -10, 10]) * x
    # a faint perspective grid in the lower third (the late-90s screensaver floor)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im, 'RGBA')
    hz = 700
    for k in range(-20, 21):
        d.line([(W / 2 + k * 40, hz), (W / 2 + k * 260, H)], fill=(120, 220, 255, 28), width=2)
    for k in range(10):
        yy = hz + (H - hz) * (k / 10) ** 1.8
        d.line([(0, yy), (W, yy)], fill=(120, 220, 255, 24), width=2)
    _cache['bg'] = np.asarray(im).copy()
    return _cache['bg']


def bezel(img, x, y, w, h):
    """A beige monitor bezel around a w x h screen at x, y (drawn into img, a PIL image)."""
    d = ImageDraw.Draw(img)
    b = 26
    d.rounded_rectangle([x - b - 6, y - b - 6, x + w + b + 6, y + h + b + 6], radius=18, fill=(70, 66, 60))
    d.rounded_rectangle([x - b, y - b, x + w + b, y + h + b], radius=14, fill=(214, 206, 186))
    d.rectangle([x - 6, y - 6, x + w + 5, y + h + 5], fill=(120, 114, 100))
    d.rectangle([x - 3, y - 3, x + w + 2, y + h + 2], fill=(20, 20, 20))
    # a little power light
    d.ellipse([x + w + b - 18, y + h + 8, x + w + b - 8, y + h + 18], fill=(80, 230, 110))


def wide_base():
    if 'wide' in _cache: return _cache['wide']
    im = Image.fromarray(background())
    bezel(im, SCR_X, SCR_Y, 1024, 768)
    _cache['wide'] = np.asarray(im).copy()
    return _cache['wide']


# ------------------------------------------------------------------ the generic host ("YOUR DAW HERE")
def daw_base(notes, length):
    key = 'daw'
    if key in _cache: return _cache[key]
    im = Image.fromarray(background())
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 40, 40, W - 40, 900
    d.rectangle([x0, y0, x1, y1], fill=(46, 48, 54), outline=(10, 10, 12), width=2)
    d.rectangle([x0, y0, x1, y0 + 44], fill=(30, 32, 36))
    f = font('DejaVuSans-Bold.ttf', 22)
    d.text((x0 + 18, y0 + 10), 'YOUR DAW HERE', font=f, fill=(230, 230, 230))
    d.text((x0 + 280, y0 + 12), '(any VST3, AU or CLAP host)', font=font('DejaVuSans.ttf', 18), fill=(150, 150, 160))
    # transport
    d.polygon([(x0 + 700, y0 + 12), (x0 + 700, y0 + 34), (x0 + 720, y0 + 23)], fill=(110, 220, 120))
    d.rectangle([x0 + 736, y0 + 13, x0 + 756, y0 + 33], fill=(200, 200, 200))
    d.text((x0 + 780, y0 + 12), '120.00 BPM   4/4', font=font('DejaVuSansMono-Bold.ttf', 20), fill=(240, 200, 90))
    # track list and the MIDI clip lane
    d.rectangle([x0, y0 + 44, x0 + 260, y1], fill=(38, 40, 46))
    for k, (nm, c) in enumerate([('1  SNDWAVE1993', (255, 170, 60)), ('2  Audio', (120, 160, 220)), ('3  Return A', (150, 150, 150))]):
        yy = y0 + 60 + k * 96
        d.rectangle([x0 + 8, yy, x0 + 252, yy + 86], fill=(56, 58, 66))
        d.rectangle([x0 + 8, yy, x0 + 16, yy + 86], fill=c)
        d.text((x0 + 26, yy + 10), nm, font=font('DejaVuSans-Bold.ttf', 18), fill=(230, 230, 230))
    lx0, ly0, lx1, ly1 = x0 + 270, y0 + 60, x1 - 10, y0 + 146
    d.rectangle([lx0, ly0, lx1, ly1], fill=(120, 76, 28))
    lo = min(n for _, n, _, _ in notes); hi = max(n for _, n, _, _ in notes)
    for t, n, v, du in notes:
        xa = lx0 + (lx1 - lx0) * t / length; xb = lx0 + (lx1 - lx0) * (t + du) / length
        yy = ly1 - 6 - (ly1 - ly0 - 12) * (n - lo) / max(1, hi - lo)
        d.rectangle([xa, yy - 2, max(xa + 2, xb), yy + 2], fill=(255, 220, 160))
    _cache[key] = (np.asarray(im).copy(), (lx0, ly0, lx1, ly1))
    return _cache[key]


# ------------------------------------------------------------------ the host's box
class HostBox:
    TITLE = 'Your Instructor'

    def __init__(self):
        self.P = Presenter()
        self.cache = OrderedDict()
        f1, f2 = font('DejaVuSans-Bold.ttf', 30), font('DejaVuSans.ttf', 19)
        # the frame: a Windows 3.1-style window with a name plate
        bw = PW + 8
        bh = PH + 26 + 8 + 70
        fr = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
        d = ImageDraw.Draw(fr)
        d.rectangle([0, 0, bw - 1, bh - 1], fill=(192, 192, 192), outline=(0, 0, 0))
        d.rectangle([3, 3, bw - 4, 28], fill=(0, 0, 128))
        d.text((bw // 2, 16), self.TITLE, font=font('DejaVuSans-Bold.ttf', 17), fill=(255, 255, 255), anchor='mm')
        d.rectangle([4, 30, bw - 5, 30 + PH + 1], outline=(128, 128, 128))
        ny = 34 + PH
        d.rectangle([4, ny, bw - 5, bh - 5], fill=(255, 255, 224), outline=(128, 128, 128))
        d.text((16, ny + 6), 'HARLAN PETTIBONE', font=f1, fill=(20, 20, 80))
        d.text((18, ny + 40), 'Home computing instructor (retired)', font=f2, fill=(60, 60, 60))
        self.frame = fr
        self.size = (bw, bh)

    def image(self, st):
        key = (round(st['mouth'] * 6), st['shape'], st['blink'] > 0.5, round(st['brow'] * 3), st['gesture'], round(st['g'] * 8),
               round(st['t'] * 6) % 48 if True else 0)
        if STYLE == 'ai':   # the AI stills: one per gesture, a small bob while he talks (no lip movement)
            name = {'point': 'harlan_point.png', 'disk': 'harlan_disk.png'}.get(st['gesture'] if st['g'] > 0.5 else 'none', 'harlan_ref.png')
            bob = int(round(st['mouth'] * 3))
            key = ('ai', name, bob)
            im = self.cache.get(key)
            if im is None:
                src = Image.open(os.path.join(ROOT, 'grok', 'px', name)).convert('RGB')   # 140 x 157 pixel art: 3x
                crop = src.resize((src.width * 3, src.height * 3), Image.NEAREST).crop((0, 0, PW, PH))
                pic = Image.new('RGB', (PW, PH)); pic.paste(crop, (0, -bob))
                im = self.frame.copy(); im.paste(pic, (4, 31)); self.cache[key] = im
            return im
        im = self.cache.get(key)
        if im is None:
            pic = self.P.draw(mouth=key[0] / 6, shape=key[1], blink=1.0 if key[2] else 0.0, brow=key[3] / 3,
                              gesture=key[4], g=key[5] / 8, t=key[6] / 6)
            im = self.frame.copy()
            im.paste(pic, (4, 31))
            self.cache[key] = im
            if len(self.cache) > 600: self.cache.popitem(last=False)
        return im


# ------------------------------------------------------------------ text helpers
def text_bar(img, text, sub, x, y, u, colours=((0, 120, 170), (150, 40, 150)), size=40):
    """A tinted lower-third bar sliding in from the left (u: 0..1 in, 1 shown)."""
    f1, f2 = font('DejaVuSans-Bold.ttf', size), font('DejaVuSans.ttf', int(size * 0.55))
    d0 = ImageDraw.Draw(img)
    tw = max(d0.textlength(text, font=f1), d0.textlength(sub or '', font=f2)) + 60
    bh = int(size * 1.35 + (size * 0.75 if sub else 0) + 16)
    off = int((1 - ease(u)) * -(tw + x + 40))
    bar = Image.new('RGBA', (int(tw), bh))
    gx = np.linspace(0, 1, int(tw))[None, :, None]
    c0, c1 = np.array(colours[0]), np.array(colours[1])
    arr = np.concatenate([np.broadcast_to(c0 * (1 - gx) + c1 * gx, (bh, int(tw), 3)), np.full((bh, int(tw), 1), 225)], 2).astype(np.uint8)
    bar = Image.fromarray(arr, 'RGBA')
    d = ImageDraw.Draw(bar)
    d.rectangle([0, 0, 8, bh], fill=(255, 230, 90, 255))
    d.text((26, 8), text, font=f1, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    if sub: d.text((28, 12 + size * 1.25), sub, font=f2, fill=(255, 250, 220))
    img.paste(bar, (x + off, y), bar)


def wrap(text, f, width, d):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= width: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def caption(img, text):
    f = font('DejaVuSans-Bold.ttf', 40)
    d = ImageDraw.Draw(img, 'RGBA')
    lines = wrap(text, f, 1560, d)
    lh = 52
    y = H - 34 - lh * len(lines)
    wmax = max(d.textlength(l, font=f) for l in lines)
    d.rounded_rectangle([W / 2 - wmax / 2 - 22, y - 12, W / 2 + wmax / 2 + 22, H - 26], radius=10, fill=(0, 0, 40, 170))
    for k, l in enumerate(lines):
        d.text((W / 2, y + k * lh), l, font=f, fill=(255, 255, 255), anchor='ma', stroke_width=3, stroke_fill=(0, 0, 0))


# ------------------------------------------------------------------ transitions
def tmask(kind, p, seed=0):
    """Mask (H, W) float 0..1 of the incoming picture at progress p."""
    if kind == 'dissolve': return np.full((H, W), p, np.float32)
    s = 4
    m = Image.new('L', (W // s, H // s), 0)
    d = ImageDraw.Draw(m)
    w, h = W // s, H // s
    if kind == 'wipe':
        if int(w * p * 1.1) - 6 >= 0: d.rectangle([0, 0, int(w * p * 1.1) - 6, h], fill=255)
    elif kind == 'iris':
        r = max(0.5, p * math.hypot(w, h) / 2 * 1.05)
        d.ellipse([w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r], fill=255)
    elif kind == 'star':
        r = p * math.hypot(w, h) * 0.75
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5 + p * 1.2
            rr = r if k % 2 == 0 else r * 0.45
            pts.append((w / 2 + rr * math.cos(a), h / 2 + rr * math.sin(a)))
        d.polygon(pts, fill=255)
    elif kind == 'blinds':
        n = 12
        for k in range(n):
            y0 = k * h / n
            if p > 0: d.rectangle([0, y0, w, y0 + h / n * p], fill=255)
    elif kind == 'page':   # a diagonal page turn from the bottom right, with a lighter turning edge
        yy, xx = np.mgrid[0:h, 0:w]
        c = (1 - p) * (w + h + 30)
        a = np.where(xx + yy >= c, 255, np.where(xx + yy >= c - 24, 150, 0)).astype(np.uint8)
        m = Image.fromarray(a, 'L')
    return np.asarray(m.resize((W, H), Image.BILINEAR), np.float32) / 255.0


# ------------------------------------------------------------------ the edit
class Edit:
    def __init__(self, cut):
        import edit
        self.spec = edit.build(cut)
        self.shots = self.spec['shots']
        t = 0.0
        for s in self.shots:
            s['t0'] = t
            t += s['dur']
            s['t1'] = t
        self.length = t
        self.lines = json.load(open(os.path.join(ROOT, 'tts', 'lines.json')))
        # narration placements (global times)
        self.say = []
        for s in self.shots:
            for lid, off in s.get('lines', []):
                self.say.append((s['t0'] + off, lid))
        self.say.sort()

    def shot_at(self, t):
        for k, s in enumerate(self.shots):
            if t < s['t1']: return k
        return len(self.shots) - 1


# ------------------------------------------------------------------ audio
def load_audio(path, sr=SR):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(sr), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<f4').reshape(-1, 2).copy()


def lufs_gain(x, target):
    """A rough loudness match (RMS of the louder half of 400 ms blocks) to target dBFS RMS."""
    b = 19200
    n = len(x) // b
    if n == 0: return 1.0
    r = np.sqrt((x[:n * b].reshape(n, b, 2) ** 2).mean((1, 2)))
    r = np.sort(r[r > 1e-4])
    if not len(r): return 1.0
    ref = np.sqrt((r[len(r) // 2:] ** 2).mean())
    return 10 ** (target / 20) / ref


def mix(E, out_wav):
    N = int(E.length * SR) + SR
    bed = np.zeros((N, 2), np.float32)      # everything that ducks under the voice
    voice = np.zeros((N, 2), np.float32)
    host_env = np.zeros(N, np.float32)      # the host's voice alone (for his mouth)
    caps = {}
    for s in E.shots:
        v = s['v']
        if v.get('k') in ('cap', 'daw') and not s.get('mute'):
            sc = v['scene']
            if sc not in caps:
                a = load_audio(os.path.join(ROOT, 'cap', sc, 'editor.wav'))
                caps[sc] = a * lufs_gain(a, -20)
            a = caps[sc]
            sp = v.get('speed', 1.0)
            n = int(s['dur'] * SR)
            if sp == 1.0:
                i0 = int(v['src'] * SR)
                seg = a[i0:i0 + n]
            else:
                seg = np.zeros((n, 2), np.float32)   # sped-up footage is silent
            g = s.get('gain', 1.0)
            j = int(s['t0'] * SR)
            seg = seg * g
            fade = min(len(seg) // 2, int(0.08 * SR))
            if fade:
                ramp = np.linspace(0, 1, fade)[:, None]
                seg[:fade] *= ramp; seg[-fade:] *= ramp[::-1]
            bed[j:j + len(seg)] += seg
    for m in E.spec.get('music', []):
        a = load_audio(os.path.join(ROOT, 'music', m['file']))
        i0 = int(m.get('src', 0) * SR)
        n = int(m['len'] * SR)
        seg = a[i0:i0 + n] * lufs_gain(a, -20) * m.get('gain', 0.5)
        fi, fo = int(m.get('fin', 1.0) * SR), int(m.get('fout', 1.5) * SR)
        if fi: seg[:fi] *= np.linspace(0, 1, fi)[:, None]
        if fo: seg[-fo:] *= np.linspace(1, 0, fo)[:, None]
        j = int(m['at'] * SR)
        bed[j:j + len(seg)] += seg[:N - j]
    for t, lid in E.say:
        a = load_audio(os.path.join(ROOT, 'tts', lid + '.wav'))
        a = a * lufs_gain(a, -17)
        j = int(t * SR)
        voice[j:j + len(a)] += a[:N - j]
        if E.lines[lid]['speaker'] == 'HOST':
            host_env[j:j + len(a)] += a[:N - j, 0]
    # ducking: the bed drops ~11 dB under the voice, with a 60 ms attack and 400 ms release
    env = np.abs(voice[:, 0])
    k = int(SR * 0.02)
    env = np.convolve(env, np.ones(k) / k, 'same')
    act = (env > 0.01).astype(np.float32)
    g = np.empty_like(act)
    cur = 0.0
    a_att, a_rel = 1 / (0.06 * SR), 1 / (0.4 * SR)
    for i in range(0, len(act), 240):          # control rate 200 Hz
        tgt = act[i:i + 240].max()
        step = 240 * (a_att if tgt > cur else a_rel)
        cur = min(tgt, cur + step) if tgt > cur else max(tgt, cur - step)
        g[i:i + 240] = cur
    duck = 1 - 0.72 * g
    out = bed * duck[:, None] + voice
    out = out[:int(E.length * SR)]
    import soundfile as sf
    sf.write(out_wav, out, SR, subtype='FLOAT')
    # the host's mouth: RMS and zero crossings per video frame
    fr = SR // FPS
    nf = int(E.length * FPS) + 1
    he = np.zeros(nf); zc = np.zeros(nf)
    for i in range(nf):
        x = host_env[i * fr:(i + 1) * fr]
        if len(x):
            he[i] = np.sqrt((x ** 2).mean())
            zc[i] = (np.abs(np.diff(np.sign(x))) > 0).mean() if len(x) > 1 else 0
    return he, zc


# ------------------------------------------------------------------ the host's track
def host_track(E, he, zc):
    """Per frame: the box's position/scale (with swoops), and the presenter's state."""
    nf = int(E.length * FPS)
    rng = np.random.default_rng(311)
    places = E.spec['places']
    pos = []
    # keyframes from shots: each shot names where the host is ('side', 'corner', 'center', None = off-screen)
    keys = []
    for s in E.shots:
        keys.append((s['t0'], s.get('host', 'side'), s.get('swoop', 0.7)))
    blinks = set()
    t = 1.0
    while t < E.length:
        t += rng.uniform(2.5, 5.0)
        for k in range(4): blinks.add(int(t * FPS) + k)
    gest = []
    for s in E.shots:
        for (gt, kind, dur) in s.get('gest', []):
            gest.append((s['t0'] + gt, kind, dur))
    states = []
    for i in range(nf):
        t = i / FPS
        # where
        cur = None; prev = None; t_change = 0; sw = 0.7
        for kt, place, swd in keys:
            if kt <= t:
                if place != cur:
                    prev, cur, t_change, sw = cur, place, kt, swd
            else: break
        def at(pl):
            if pl is None: return None
            return places[pl]
        A, B = at(prev), at(cur)
        u = (t - t_change) / sw if sw > 0 else 1.0
        if B is None and A is None: pos_ = None
        else:
            if A is None: A = (B[0], H + 60, B[2]) if B[1] > H / 2 else (B[0], -700, B[2])
            if B is None: B = (A[0], H + 60, A[2])
            e = ease(u)
            # an arc: the box flies over a curve, not a straight line
            mx, my = (A[0] + B[0]) / 2, min(A[1], B[1]) - 260
            x = (1 - e) ** 2 * A[0] + 2 * (1 - e) * e * mx + e * e * B[0]
            y = (1 - e) ** 2 * A[1] + 2 * (1 - e) * e * my + e * e * B[1]
            sc = A[2] + (B[2] - A[2]) * e
            pos_ = (x, y, sc, u)
        # mouth
        m = min(1.0, he[i] / 0.06) if i < len(he) else 0
        shape = 'm' if m < 0.08 else ('e' if zc[i] > 0.12 else ('o' if zc[i] < 0.05 and m > 0.5 else 'a'))
        g_kind, g = 'none', 0.0
        for gt, kind, dur in gest:
            if gt <= t < gt + dur:
                g_kind = kind
                g = min(1.0, (t - gt) / 0.35, (gt + dur - t) / 0.35)
        brow = 0.0
        for st, lid in E.say:
            if 0 <= t - st < 0.6 and E.lines[lid]['speaker'] == 'HOST': brow = 1 - (t - st) / 0.6
        states.append({'pos': pos_, 'mouth': m, 'shape': shape, 'blink': 1.0 if i in blinks else 0.0, 'brow': brow,
                       'gesture': g_kind, 'g': g, 't': t})
    return states


TRAIL = 16


def draw_host(img, box, states, i):
    """The box, and its motion trail: every frame of a swoop leaves a copy behind; the trail keeps the last 16
    copies, so on each new frame the 17th-oldest is cleared, and after landing the trail empties oldest first."""
    st = states[i]
    if st['pos'] is None: return
    for k in range(max(0, i - TRAIL), i):
        p = states[k]['pos']
        if p is not None and p[3] < 1.0:
            _paste_box(img, box, states[k])
    _paste_box(img, box, st)


def _paste_box(img, box, st, dim=0.0):
    x, y, sc, u = st['pos']
    im = box.image(st)
    if abs(sc - 1.0) > 0.01:
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
    # a hard drop shadow (the cheap kind)
    sh = Image.new('RGBA', im.size, (0, 0, 0, 110))
    img.paste(sh, (int(x) + 8, int(y) + 8), im)
    img.paste(im, (int(x), int(y)), im)


# ------------------------------------------------------------------ pictures
class Pictures:
    def __init__(self, E):
        self.E = E
        self.caps = {}
        self.imgs = {}

    def cap(self, sc):
        if sc not in self.caps: self.caps[sc] = Capture(os.path.join(ROOT, 'cap', sc, 'cap.bhrc'))
        return self.caps[sc]

    def image(self, path):
        if path not in self.imgs: self.imgs[path] = Image.open(os.path.join(ROOT, 'art', path)).convert('RGBA')
        return self.imgs[path]

    def shot(self, s, lt):
        """The shot's own picture at local time lt (RGB uint8, H x W x 3)."""
        v = s['v']
        k = v['k']
        if k in ('cap', 'daw'):
            c = self.cap(v['scene'])
            src = min(v['src'] + lt * v.get('speed', 1.0), v.get('hold', 1e9))
            scr = c.frame(src)
            view = v.get('view', [(0, 1, 512, 384)])
            # the current view keyframe, with a pan to the next one at the same scale
            j = 0
            while j + 1 < len(view) and view[j + 1][0] <= lt: j += 1
            _, scale, cx, cy = view[j]
            if j + 1 < len(view) and view[j + 1][1] == scale and view[j].__len__() >= 4:
                t0, t1 = view[j][0], view[j + 1][0]
                pan = v.get('pan', 1.2)
                u = ease((lt - (t1 - pan)) / pan) if lt > t1 - pan else 0.0
                cx += (view[j + 1][2] - cx) * u; cy += (view[j + 1][3] - cy) * u
            if k == 'daw':
                base, lane = daw_base(v['notes'], v['notes_len'])
                out = base.copy()
                px, py = 760, 120
                out[py:py + 768, px:px + 1024] = scr
                # the plugin window's title
                im = Image.fromarray(out)
                d = ImageDraw.Draw(im)
                d.rectangle([px - 2, py - 30, px + 1025, py - 1], fill=(30, 32, 36))
                d.text((px + 10, py - 26), 'SNDWAVE1993 (VST3)  -  Track 1', font=font('DejaVuSans-Bold.ttf', 18), fill=(230, 230, 230))
                # the playhead over the clip
                lx0, ly0, lx1, ly1 = lane
                ph = (src - v.get('clip0', v['src'])) / v['notes_len']
                if 0 <= ph <= 1:
                    xx = lx0 + (lx1 - lx0) * ph
                    d.line([(xx, ly0 - 6), (xx, ly1 + 6)], fill=(255, 255, 255), width=3)
                return np.asarray(im)
            if scale == 1:
                out = wide_base().copy()
                out[SCR_Y:SCR_Y + 768, SCR_X:SCR_X + 1024] = scr
                return out
            # whole-number zoom of a region, filling the frame
            cw, ch = W // scale, H // scale
            x0 = int(round(min(max(cx - cw / 2, 0), 1024 - cw))) if cw <= 1024 else None
            y0 = int(round(min(max(cy - ch / 2, 0), 768 - ch))) if ch <= 768 else None
            if x0 is None or y0 is None:   # region larger than the screen: centre it on the background
                out = background().copy()
                cw2, ch2 = min(cw, 1024), min(ch, 768)
                xa = 0 if x0 is None else x0; ya = 0 if y0 is None else y0
                crop = scr[ya:ya + ch2, xa:xa + cw2]
                big = crop.repeat(scale, 0).repeat(scale, 1)
                oy, ox = (H - big.shape[0]) // 2, (W - big.shape[1]) // 2
                out[oy:oy + big.shape[0], ox:ox + big.shape[1]] = big
                return out
            crop = scr[y0:y0 + ch, x0:x0 + cw]
            return crop.repeat(scale, 0).repeat(scale, 1)
        if k == 'card':
            return self.card(v, lt, s['dur'])
        if k == 'seq':      # a folder of 1920x1080 PNG frames at 30 fps (the Blender shots, the web capture)
            d = os.path.join(ROOT, v['dir'])
            files = self.imgs.get(d)
            if files is None: files = self.imgs[d] = sorted(f for f in os.listdir(d) if f.endswith('.png'))
            n = min(len(files) - 1, max(0, int(v.get('start', 0) + lt * FPS * v.get('speed', 1.0))))
            im = Image.open(os.path.join(d, files[n])).convert('RGB')
            if im.size != (W, H): im = im.resize((W, H), Image.NEAREST)
            return np.asarray(im)
        if k == 'art':
            out = Image.fromarray(background())
            for it in v['items']:
                im = self.image(it['path'])
                sc = it.get('scale', 1.0) * (1 + it.get('zoom', 0.0) * lt / max(1e-3, s['dur']))
                im2 = im.resize((int(im.width * sc), int(im.height * sc)), Image.NEAREST if it.get('pixel') else Image.LANCZOS)
                out.paste(im2, (int(it['x'] - im2.width / 2), int(it['y'] - im2.height / 2)), im2)
            d = ImageDraw.Draw(out)
            for tx in v.get('text', []):
                d.text((tx['x'], tx['y']), tx['s'], font=font(tx.get('font', 'DejaVuSans-Bold.ttf'), tx.get('size', 48)),
                       fill=tuple(tx.get('fill', (255, 255, 255))), anchor=tx.get('anchor', 'la'), stroke_width=tx.get('stroke', 0),
                       stroke_fill=(0, 0, 0))
            return np.asarray(out.convert('RGB'))
        raise ValueError(k)

    def card(self, v, lt, dur):
        out = Image.fromarray(background())
        d = ImageDraw.Draw(out)
        y0 = 380
        if v.get('logo'):    # pixel art: whole-number scale, nearest neighbour
            lg = self.image(v['logo'])
            k = v.get('logo_scale', 1)
            lg = lg.resize((lg.width * k, lg.height * k), Image.NEAREST)
            out.paste(lg, (W // 2 - lg.width // 2, v.get('logo_y', 40)), lg)
            y0 = v.get('band_y', 830)
        bh = 320 if not v.get('logo') else 210
        d.rectangle([0, y0, W, y0 + bh], fill=(0, 0, 90))
        d.rectangle([0, y0 - 8, W, y0], fill=(255, 220, 60)); d.rectangle([0, y0 + bh, W, y0 + bh + 8], fill=(255, 220, 60))
        ty = y0 + (90 if not v.get('logo') else 60)
        d.text((W / 2, ty), v['title'], font=font('DejaVuSans-Bold.ttf', 72 if not v.get('logo') else 60), fill=(255, 255, 255), anchor='mm',
               stroke_width=3, stroke_fill=(0, 0, 0))
        if v.get('sub'):
            d.text((W / 2, ty + 100 if not v.get('logo') else ty + 80), v['sub'], font=font('DejaVuSans.ttf', 40 if not v.get('logo') else 34),
                   fill=(255, 240, 180), anchor='mm')
        if v.get('foot'):
            d.text((W / 2, y0 + bh + 50), v['foot'], font=font('DejaVuSans.ttf', 30), fill=(220, 220, 240), anchor='mm')
        return np.asarray(out)


# ------------------------------------------------------------------ one frame
class Renderer:
    def __init__(self, E, states):
        self.E, self.states = E, states
        self.pics = Pictures(E)
        self.box = HostBox()
        self.frozen = {}
        self.capts = self.caption_chunks()

    def caption_chunks(self):
        """Burned-in captions: each line split into chunks of at most ~2 caption lines, timed by length."""
        out = []
        for t, lid in self.E.say:
            L = self.E.lines[lid]
            text, dur = L['caption'], L['seconds']
            words = text.split()
            chunks, cur = [], ''
            for w in words:
                if len(cur) + len(w) + 1 > 84 and cur:
                    chunks.append(cur); cur = w
                else: cur = (cur + ' ' + w).strip()
                if cur.endswith(('.', ':', '?')) and len(cur) > 40: chunks.append(cur); cur = ''
            if cur: chunks.append(cur)
            total = sum(len(c) for c in chunks)
            tt = t
            for c in chunks:
                d = dur * len(c) / total
                out.append((tt, tt + d + (0.25 if c is chunks[-1] else 0), c))
                tt += d
        return out

    def frame(self, i):
        E = self.E
        t = i / FPS
        k = E.shot_at(t)
        s = E.shots[k]
        lt = t - s['t0']
        img = self.pics.shot(s, lt)
        tr = s.get('tr')
        if tr and k > 0 and lt < tr[1]:
            if (k - 1) not in self.frozen:
                p = E.shots[k - 1]
                self.frozen = {k - 1: self.pics.shot(p, p['dur'] - 1 / FPS)}
            prev = self.frozen[k - 1]
            m = tmask(tr[0], ease(lt / tr[1]))[:, :, None]
            img = (img * m + prev * (1 - m)).astype(np.uint8)
        im = Image.fromarray(img).convert('RGBA')
        # overlays of the shot: supers, chapter bars, cards over the picture
        for ov in s.get('over', []):
            a, b = ov.get('t', (0, s['dur']))
            if not (a <= lt < b): continue
            u = min(1.0, (lt - a) / 0.35, (b - lt) / 0.35)
            if ov['k'] == 'super':
                text_bar(im, ov['text'], ov.get('sub'), ov.get('x', 60), ov.get('y', 770), u, size=ov.get('size', 40))
            elif ov['k'] == 'chapter':
                text_bar(im, ov['text'], None, 0, 24, u, colours=((200, 40, 120), (240, 140, 30)), size=34)
            elif ov['k'] == 'panel':
                self.panel(im, ov, u)
            elif ov['k'] == 'box':      # a highlight rectangle (frame coordinates)
                d = ImageDraw.Draw(im)
                x0, y0, x1, y1 = ov['r']
                for w_ in range(4): d.rectangle([x0 - w_, y0 - w_, x1 + w_, y1 + w_], outline=(255, 40, 40))
            elif ov['k'] == 'osd':
                d = ImageDraw.Draw(im)
                d.text((70, 60), ov['text'], font=font('DejaVuSansMono-Bold.ttf', 54), fill=(80, 255, 120), stroke_width=3, stroke_fill=(0, 40, 0))
        draw_host(im, self.box, self.states, i)
        for a, b, c in self.capts:
            if a <= t < b:
                caption(im, c)
                break
        return np.asarray(im.convert('RGB'))

    def panel(self, im, ov, u):
        """A Windows 3.1-style information panel (title bar, grey body, rows of text)."""
        x, y, w = ov['x'], ov['y'], ov['w']
        rows = ov['rows']
        fs = ov.get('size', 28)
        f = font('DejaVuSans.ttf', fs); fb = font('DejaVuSans-Bold.ttf', fs)
        h = 70 + int(fs * 1.6) * len(rows) + 20
        off = int((1 - ease(u)) * (W - x + 40))
        pn = Image.new('RGBA', (w, h), (192, 192, 192, 255))
        d = ImageDraw.Draw(pn)
        d.rectangle([0, 0, w - 1, h - 1], outline=(0, 0, 0))
        d.rectangle([3, 3, w - 4, 40], fill=(0, 0, 128))
        d.text((w // 2, 22), ov['title'], font=font('DejaVuSans-Bold.ttf', 18), fill=(255, 255, 255), anchor='mm')
        for k, (a, b) in enumerate(rows):
            d.text((20, 62 + k * int(fs * 1.6)), a, font=fb, fill=(0, 0, 0))
            d.text((ov.get('col', 260), 62 + k * int(fs * 1.6)), b, font=f, fill=(0, 0, 0))
        im.paste(pn, (x + off, y), pn)


# ------------------------------------------------------------------ main
def render_range(args):
    root, cut, a, b, out, states_path = args
    global ROOT
    ROOT = root
    E = Edit(cut)
    states = np.load(states_path, allow_pickle=True)['s'].tolist()
    R = Renderer(E, states)
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p',
                           '-threads', '2', out], stdin=subprocess.PIPE)
    for i in range(a, b):
        ff.stdin.write(R.frame(i).tobytes())
    ff.stdin.close()
    ff.wait()
    return out


def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument('root'); ap.add_argument('out')
    ap.add_argument('--cut', default='spot')
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--frames'); ap.add_argument('--sheet')
    ap.add_argument('--from', dest='t_from', type=float, default=0); ap.add_argument('--to', dest='t_to', type=float)
    a = ap.parse_args()
    ROOT = os.path.abspath(a.root)
    sys.path.insert(0, HERE)
    E = Edit(a.cut)
    work = os.path.join(ROOT, 'work', a.cut)
    os.makedirs(work, exist_ok=True)
    print(f'{a.cut}: {len(E.shots)} shots, {E.length:.2f} s', flush=True)
    wav = os.path.join(work, 'mix.wav')
    he, zc = mix(E, wav)
    states = host_track(E, he, zc)
    sp = os.path.join(work, 'states.npz')
    np.savez(sp, s=np.array(states, dtype=object))
    # captions file
    R0 = Renderer(E, states)
    def ts(x):
        return f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round(x * 1000)) % 1000:03d}'
    with open(os.path.splitext(a.out)[0] + '.srt', 'w') as f:
        for n, (s0, s1, c) in enumerate(R0.capts, 1):
            f.write(f'{n}\n{ts(s0)} --> {ts(s1)}\n{c}\n\n')
    if a.frames:
        tl = [float(x) for x in a.frames.split(',')]
        cols = 4; rows = (len(tl) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 480, rows * 290), 'black')
        for n, t in enumerate(tl):
            fr = Image.fromarray(R0.frame(int(t * FPS))).resize((480, 270))
            sheet.paste(fr, ((n % cols) * 480, (n // cols) * 290))
            ImageDraw.Draw(sheet).text(((n % cols) * 480 + 4, (n // cols) * 290 + 272), f'{t:.1f}s', fill='yellow')
        sheet.save(a.sheet)
        return
    nf = int(E.length * FPS)
    f0 = int(a.t_from * FPS); f1 = int((a.t_to or E.length) * FPS)
    from multiprocessing import Pool
    step = (f1 - f0 + a.jobs - 1) // a.jobs
    parts = [(ROOT, a.cut, f0 + k * step, min(f1, f0 + (k + 1) * step), os.path.join(work, f'part{k:02d}.mp4'), sp)
             for k in range(a.jobs) if f0 + k * step < f1]
    with Pool(len(parts)) as P:
        outs = P.map(render_range, parts)
    lst = os.path.join(work, 'parts.txt')
    open(lst, 'w').write(''.join(f"file '{o}'\n" for o in outs))
    # the mix: loudness for social video (-14 LUFS integrated, -1 dBTP), AAC
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-ss', f'{a.t_from}', '-t', f'{(f1 - f0) / FPS}', '-i', wav,
                    '-af', 'loudnorm=I=-14:TP=-1.0:LRA=11', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-movflags', '+faststart', '-shortest', a.out], check=True)
    for o in outs: os.remove(o)
    print('wrote', a.out, flush=True)


if __name__ == '__main__':
    main()
