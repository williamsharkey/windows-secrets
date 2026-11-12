"""draw the BASILISK 3.11 icon (pixel art, 1993 palette) -> assets/basilisk.png/.ico/.icns
   needs Pillow: python3 mkicon.py"""
import os
from PIL import Image

G = """
................
.KKKKKKKKKKKKKK.
.KWWWWWWWWWWWWK.
.KBBBBBBBBBBBBK.
.KTTTTTTTTTTTTK.
.KTTTTGGGGGTTTK.
.KTTTGGGGKGGRRK.
.KTTGGTTTGGGTTK.
.KTTGGTTTTTTTTK.
.KTTTGGGGGGTTTK.
.KTTTTTTTTGGTTK.
.KTTTTTTTTGGTTK.
.KTTGGGGGGGTTTK.
.KTTTTTTTTTTTTK.
.KKKKKKKKKKKKKK.
................
"""
PAL = {'.': (0, 0, 0, 0), 'K': (0, 0, 0, 255), 'W': (255, 255, 255, 255), 'B': (0, 0, 128, 255),
       'T': (0, 128, 128, 255), 'G': (0, 160, 0, 255), 'L': (128, 255, 128, 255), 'Y': (255, 255, 0, 255),
       'R': (192, 0, 0, 255)}
rows = [r for r in G.strip().splitlines()]
base = Image.new('RGBA', (16, 16))
for y, r in enumerate(rows):
    for x, c in enumerate(r):
        base.putpixel((x, y), PAL[c])
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
big = base.resize((1024, 1024), Image.NEAREST)
big.resize((512, 512), Image.NEAREST).save(os.path.join(out, 'basilisk.png'))
big.save(os.path.join(out, 'basilisk.ico'), sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
big.save(os.path.join(out, 'basilisk.icns'))
print('ok')
