from PIL import Image, ImageDraw
import numpy as np
def plot(path, series, title='', W=1200, H=400, ylim=None, xlim=None, vlines=()):
    im = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(im)
    xs = np.concatenate([s[0] for s in series]); ys = np.concatenate([s[1] for s in series])
    x0, x1 = xlim or (xs.min(), xs.max()); y0, y1 = ylim or (ys.min(), ys.max())
    if y1 == y0: y1 = y0 + 1
    L, R, T, B = 60, W - 10, 25, H - 25
    X = lambda x: L + (x - x0) / (x1 - x0) * (R - L); Y = lambda y: B - (y - y0) / (y1 - y0) * (B - T)
    d.rectangle([L, T, R, B], outline='black')
    for v in vlines: d.line([X(v), T, X(v), B], fill=(255, 160, 160))
    cols = [(0, 0, 200), (200, 0, 0), (0, 140, 0), (120, 0, 120)]
    for k, (x, y, *style) in enumerate(series):
        m = (x >= x0) & (x <= x1); x, y = x[m], np.clip(y[m], y0, y1)
        pts = list(zip(X(x), Y(y)))
        if style and style[0] == 'dot':
            for p in pts: d.point(p, fill=cols[k % 4])
        elif len(pts) > 1: d.line(pts, fill=cols[k % 4], width=1)
    d.text((L, 5), title, fill='black')
    for k in range(5):
        yv = y0 + (y1 - y0) * k / 4; d.text((2, Y(yv) - 6), '%.4g' % yv, fill='black')
        xv = x0 + (x1 - x0) * k / 4; d.text((X(xv) - 15, B + 5), '%.4g' % xv, fill='black')
    im.save(path)
