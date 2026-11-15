"""Drawing kit for the CITYPOP night scene: float RGB layers with hard (1-bit) alpha,
small-bbox primitives, glows, and an ordered-dither palette quantiser.
Everything is deterministic: no randomness lives here; callers pass a numpy Generator."""
import numpy as np
from PIL import Image, ImageDraw

F = np.float32
GROUP = [0]   # draw-group counter: later groups are nearer; used for anchor occlusion tests


def C(h, a=None):
    """'#rrggbb' or (r,g,b) 0-255 -> float32 array 0..1"""
    if isinstance(h, str):
        h = h.lstrip('#')
        return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], F) / 255.0
    return np.array(h, F) / (255.0 if max(h) > 1.0 else 1.0)


def mix(a, b, t):
    return a + (b - a) * t


BAYER8 = np.array([
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]], F)
BAYER8 = (BAYER8 + 0.5) / 64.0


def bayer(H, W):
    return np.tile(BAYER8, (H // 8 + 1, W // 8 + 1))[:H, :W]


class Layer:
    def __init__(self, name, W, H):
        self.name, self.W, self.H = name, W, H
        self.rgb = np.zeros((H, W, 3), F)
        self.a = np.zeros((H, W), bool)
        self.lock = None  # optional bool mask of pixels that are "emissive" (exempt from glow/grade)
        self.wid = None   # optional int32 id-buffer: which window still owns each pixel
        self.own = None   # optional int32 buffer: the draw group that last painted each pixel

    # ---- core: paint a local mask with a colour (const, (h,w,3) array, or callable(X,Y)->...)
    def paint(self, x0, y0, mask, col, alpha=True):
        h, w = mask.shape
        X0, Y0 = max(0, x0), max(0, y0)
        X1, Y1 = min(self.W, x0 + w), min(self.H, y0 + h)
        if X1 <= X0 or Y1 <= Y0:
            return
        m = mask[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
        if not m.any():
            return
        if callable(col):
            Y, X = np.mgrid[Y0:Y1, X0:X1].astype(F)
            c = np.asarray(col(X, Y), F)
            if c.ndim == 1:
                c = np.broadcast_to(c, (Y1 - Y0, X1 - X0, 3))
        else:
            c = np.asarray(col, F)
            if c.ndim == 3:
                c = c[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
            else:
                c = np.broadcast_to(c, (Y1 - Y0, X1 - X0, 3))
        reg = self.rgb[Y0:Y1, X0:X1]
        reg[m] = c[m]
        if self.wid is not None:
            self.wid[Y0:Y1, X0:X1][m] = 0
        if self.own is not None:
            self.own[Y0:Y1, X0:X1][m] = GROUP[0]
        if alpha:
            self.a[Y0:Y1, X0:X1][m] = True

    def rect(self, x, y, w, h, col):
        x, y, w, h = int(round(x)), int(round(y)), int(round(w)), int(round(h))
        if w <= 0 or h <= 0:
            return
        self.paint(x, y, np.ones((h, w), bool), col)

    def px(self, x, y, col):
        x, y = int(x), int(y)
        if 0 <= x < self.W and 0 <= y < self.H:
            self.rgb[y, x] = col
            self.a[y, x] = True

    def poly(self, pts, col, outline=None):
        pts = [(float(p[0]), float(p[1])) for p in pts]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        x0, y0 = int(np.floor(min(xs))), int(np.floor(min(ys)))
        x1, y1 = int(np.ceil(max(xs))) + 1, int(np.ceil(max(ys))) + 1
        if x1 < 0 or y1 < 0 or x0 >= self.W or y0 >= self.H:
            return
        # clip huge polys to canvas+margin to keep masks small
        cx0, cy0 = max(x0, -4), max(y0, -4)
        cx1, cy1 = min(x1, self.W + 4), min(y1, self.H + 4)
        im = Image.new('1', (cx1 - cx0, cy1 - cy0), 0)
        d = ImageDraw.Draw(im)
        d.polygon([(px - cx0, py - cy0) for px, py in pts], fill=1, outline=1)
        self.paint(cx0, cy0, np.array(im, bool), col)
        if outline is not None:
            self.lines(pts + [pts[0]], outline)

    def lines(self, pts, col, width=1):
        pts = [(float(p[0]), float(p[1])) for p in pts]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        x0, y0 = int(np.floor(min(xs))) - width, int(np.floor(min(ys))) - width
        x1, y1 = int(np.ceil(max(xs))) + width + 1, int(np.ceil(max(ys))) + width + 1
        if x1 < 0 or y1 < 0 or x0 >= self.W or y0 >= self.H:
            return
        cx0, cy0 = max(x0, -4), max(y0, -4)
        cx1, cy1 = min(x1, self.W + 4), min(y1, self.H + 4)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        im = Image.new('1', (cx1 - cx0, cy1 - cy0), 0)
        d = ImageDraw.Draw(im)
        d.line([(px - cx0, py - cy0) for px, py in pts], fill=1, width=width)
        self.paint(cx0, cy0, np.array(im, bool), col)

    def ellipse(self, cx, cy, rx, ry, col):
        x0, y0 = int(np.floor(cx - rx)), int(np.floor(cy - ry))
        w, h = int(np.ceil(2 * rx)) + 2, int(np.ceil(2 * ry)) + 2
        Y, X = np.mgrid[y0:y0 + h, x0:x0 + w].astype(F)
        m = ((X + 0.5 - cx) / max(rx, 0.5)) ** 2 + ((Y + 0.5 - cy) / max(ry, 0.5)) ** 2 <= 1.0
        self.paint(x0, y0, m, col)

    def catenary(self, x0, y0, x1, y1, sag, col, width=1, n=None):
        n = n or max(4, int(abs(x1 - x0) / 6))
        t = np.linspace(0, 1, n + 1)
        xs = x0 + (x1 - x0) * t
        ys = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        pts = list(zip(xs, ys))
        self.lines(pts, col, width)
        return pts

    # ---- lighting helpers operating on what's already painted
    def glow(self, cx, cy, r, col, k=1.0, falloff=2.0, only_opaque=True, ry=None):
        """additive light pool (screen-ish) around a point"""
        ry = ry or r
        x0, y0 = int(max(0, cx - r)), int(max(0, cy - ry))
        x1, y1 = int(min(self.W, cx + r + 1)), int(min(self.H, cy + ry + 1))
        if x1 <= x0 or y1 <= y0:
            return
        Y, X = np.mgrid[y0:y1, x0:x1].astype(F)
        d = np.sqrt(((X - cx) / r) ** 2 + ((Y - cy) / ry) ** 2)
        g = np.clip(1 - d, 0, 1) ** falloff * k
        reg = self.rgb[y0:y1, x0:x1]
        add = g[..., None] * np.asarray(col, F)
        out = 1 - (1 - reg) * (1 - add)   # screen
        if only_opaque:
            m = self.a[y0:y1, x0:x1]
            if self.lock is not None:
                m = m & ~self.lock[y0:y1, x0:x1]
            reg[m] = out[m]
        else:
            reg[:] = out
            self.a[y0:y1, x0:x1] = True

    def fog(self, mask_or_none, col, t):
        if mask_or_none is None:
            self.rgb[:] = mix(self.rgb, np.asarray(col, F), t)


def mask_from_poly(W, H, pts):
    im = Image.new('1', (W, H), 0)
    ImageDraw.Draw(im).polygon([(float(x), float(y)) for x, y in pts], fill=1, outline=1)
    return np.array(im, bool)


# ------------------------------------------------------------------ value noise (deterministic)
def vnoise(shape, scale, rng, octaves=3, persist=0.5):
    H, W = shape
    out = np.zeros(shape, F)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        sx = max(1, int(W / scale) + 2); sy = max(1, int(H / scale) + 2)
        g = rng.random((sy + 1, sx + 1)).astype(F)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize(
            (int((sx) * scale), int((sy) * scale)), Image.BICUBIC)
        a = np.asarray(im, F)[:H, :W] / 255.0
        if a.shape != shape:
            a = np.pad(a, ((0, H - a.shape[0]), (0, W - a.shape[1])), mode='edge')
        out += a * amp
        tot += amp
        amp *= persist
        scale /= 2.0
        if scale < 1.5:
            break
    return out / tot


# ------------------------------------------------------------------ quantiser
def kmeans_palette(samples, K, iters=18, seed=1, fixed=None):
    rng = np.random.default_rng(seed)
    samples = samples.astype(F)
    # init: k-means++ lite on a subsample
    idx = rng.choice(len(samples), size=min(len(samples), 20000), replace=False)
    sub = samples[idx]
    cents = [sub[0]]
    d2 = ((sub - cents[0]) ** 2).sum(1)
    for _ in range(1, K):
        p = d2 / d2.sum() if d2.sum() > 0 else None
        c = sub[rng.choice(len(sub), p=p)]
        cents.append(c)
        d2 = np.minimum(d2, ((sub - c) ** 2).sum(1))
    cents = np.array(cents, F)
    nf = 0 if fixed is None else len(fixed)
    if nf:
        cents[:nf] = fixed
    for _ in range(iters):
        d = ((samples[:, None, :] - cents[None]) ** 2).sum(2)
        lab = d.argmin(1)
        for k in range(nf, K):
            m = lab == k
            if m.any():
                cents[k] = samples[m].mean(0)
    return cents


def to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4).astype(F)


def quantize(rgb, alpha, K=40, seed=1, fixed=None, penalty=2.0, order=None):
    """ordered-dither 'two nearest along a line' quantiser (Yliluoma-ish).
    returns (index image uint8 with 0 = transparent, palette (K,3) float)"""
    H, W = alpha.shape
    pix = rgb[alpha]
    if len(pix) == 0:
        return np.zeros((H, W), np.uint8), np.zeros((1, 3), F)
    rng = np.random.default_rng(seed)
    # samples: mix of pixels and unique-ish colours (so small bright features keep their colour)
    s1 = pix[rng.choice(len(pix), size=min(len(pix), 120000), replace=False)]
    q = np.unique((np.clip(pix, 0, 1) * 63).astype(np.int32), axis=0).astype(F) / 63.0
    s2 = q[rng.choice(len(q), size=min(len(q), 40000), replace=False)]
    pal = kmeans_palette(np.concatenate([s1, s2]), K, seed=seed, fixed=fixed)
    pal = np.clip(pal, 0, 1)
    # sort palette by luma for tidy files
    luma = pal @ np.array([0.3, 0.55, 0.15], F)
    pal = pal[np.argsort(luma)]
    wts = np.array([0.8, 1.0, 0.6], F)
    P = pal * wts
    th = bayer(H, W)[alpha]
    out = np.zeros(len(pix), np.uint8)
    pw = pix * wts
    D = P[None, :, :] - P[:, None, :]          # c2 - c1   (K1,K2,3)
    DD = (D ** 2).sum(2) + 1e-9
    for s in range(0, len(pix), 60000):
        p = pw[s:s + 60000]
        d1 = ((p[:, None, :] - P[None]) ** 2).sum(2)
        c1 = d1.argmin(1)
        v = p - P[c1]                            # (n,3)
        Dc = D[c1]                               # (n,K,3)
        t = np.clip((v[:, None, :] * Dc).sum(2) / DD[c1], 0, 1)   # (n,K)
        e = ((v[:, None, :] - t[..., None] * Dc) ** 2).sum(2) + penalty * DD[c1] * t * (1 - t) * 0.25
        c2 = e.argmin(1)
        tt = t[np.arange(len(p)), c2]
        pick = np.where(tt > th[s:s + 60000], c2, c1)
        out[s:s + 60000] = pick + 1
    img = np.zeros((H, W), np.uint8)
    img[alpha] = out
    return img, pal


def save_indexed(path, img, pal):
    pl = np.zeros((256, 3), np.uint8)
    pl[1:len(pal) + 1] = np.round(np.clip(pal, 0, 1) * 255).astype(np.uint8)
    pl[0] = (0, 0, 0)
    # unique palette entries are needed so the runtime can map RGB back to an index
    seen = {}
    for i in range(1, len(pal) + 1):
        k = tuple(pl[i])
        while k in seen:
            pl[i][2] = (int(pl[i][2]) + 1) % 256
            k = tuple(pl[i])
        seen[k] = i
    im = Image.fromarray(img, 'P')
    n = len(pal) + 1
    im.putpalette(pl[:n].flatten().tolist())
    im.save(path, format='PNG', optimize=True, transparency=0)
    return pl[1:n].astype(int).tolist()
