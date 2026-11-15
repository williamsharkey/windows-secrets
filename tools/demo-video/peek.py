#!/usr/bin/env python3
"""Look at a capture: a contact sheet of frames at the given audio times, and the audio's loudness per second.

    peek.py CAPDIR OUT.png T1 T2 ... [--env]
"""
import os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bhrc import Capture

d, out = sys.argv[1], sys.argv[2]
ts = [float(x) for x in sys.argv[3:] if not x.startswith('--')]
c = Capture(os.path.join(d, 'cap.bhrc'))
n = len(ts); cols = min(4, n); rows = (n + cols - 1) // cols
sheet = Image.new('RGB', (cols * 512, rows * 400), 'black')
from PIL import ImageDraw
for i, t in enumerate(ts):
    im = Image.fromarray(c.frame(t)).resize((512, 384))
    sheet.paste(im, ((i % cols) * 512, (i // cols) * 400))
    ImageDraw.Draw(sheet).text(((i % cols) * 512 + 4, (i // cols) * 400 + 386), f'{t:.1f}s', fill='yellow')
sheet.save(out)
if '--env' in sys.argv:
    import soundfile as sf
    a, sr = sf.read(os.path.join(d, 'editor.wav'))
    m = np.abs(a).max(1)
    print(' '.join(f'{s}:{m[s * sr:(s + 1) * sr].max():.2f}' for s in range(len(m) // sr)))
print(f'{len(c.times)} frames {c.first:.1f}..{c.last:.1f}')
