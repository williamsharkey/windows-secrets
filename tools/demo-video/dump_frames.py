#!/usr/bin/env python3
"""PNG frames of a capture, one per video frame (for the CRT in scene1993.py).
    dump_frames.py CAP.bhrc OUTDIR START SECONDS [--fps 30]"""
import os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bhrc import Capture
c = Capture(sys.argv[1]); out = sys.argv[2]; t0 = float(sys.argv[3]); n = int(float(sys.argv[4]) * 30)
os.makedirs(out, exist_ok=True)
for i in range(n):
    Image.fromarray(c.frame(t0 + i / 30)).save(os.path.join(out, f'{i + 1:04d}.png'))
