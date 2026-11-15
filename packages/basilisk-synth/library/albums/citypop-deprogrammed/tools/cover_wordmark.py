"""cover_wordmark.py OUTDIR: the CITYPOP1993 cover. The scene comes from art/make_art.py (seed 1989, the cover framing),
and the title is the brand kit's wordmark (design/brand/sndwave1993/album/citypop1993-wordmark-192.png). Its 1-bit
mask is drawn in the scene's own light palette index over a one-pixel dark shadow, so every pixel stays a palette colour.
Writes cover.png (320), cover-640.png (2x, nearest) and icon-32.png (the moon, cropped). Leaves make_art.py untouched."""
import os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '../../../../../..'))
sys.path.insert(0, os.path.join(HERE, '..', 'art'))
import make_art as M   # noqa: E402

LIGHT, SHADOW = 14, 1   # make_art's palette: #d8d0f0 on #0d1030


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    c, cm = M.scene(320, 320, seed=1989, cover=True)
    wm = np.array(Image.open(os.path.join(REPO, 'design/brand/sndwave1993/album/citypop1993-wordmark-192.png')).convert('RGBA'))
    mask = wm[:, :, 3] > 127
    h, w = mask.shape
    x0, y0 = (320 - w) // 2, 26
    ys, xs = np.nonzero(mask)
    c[ys + y0 + 1, xs + x0 + 1] = SHADOW
    c[ys + y0, xs + x0] = LIGHT
    w3, _ = M.text1bit(np.zeros((40, 400), np.uint8), (0, 0), 'performed on SNDWAVE1993', 9, 1, font='DejaVuSans.ttf')
    M.text1bit(c, ((320 - w3) // 2, 300), 'performed on SNDWAVE1993', 9, 15, font='DejaVuSans.ttf')
    M.save(c, os.path.join(out, 'cover.png'))
    M.save(c, os.path.join(out, 'cover-640.png'), 2)
    mx, my, _ = cm.get('moon', [180, 100, 10])
    x, y = int(np.clip(mx - 32, 0, 256)), int(np.clip(my - 32, 0, 256))
    Image.open(os.path.join(out, 'cover.png')).crop((x, y, x + 64, y + 64)).resize((32, 32), Image.NEAREST).save(os.path.join(out, 'icon-32.png'))
    print('cover ->', out)


if __name__ == '__main__':
    main()
