#!/usr/bin/env python3
"""BASILISK SYNTH batch renders -> the same framing as render311's: from the score's start, latency removed.

    xp_trim.py BATCH_OUT_DIR RENDER_DIR [--warmup 1] [--latency 4800]

packages/basilisk-synth/tools/batch_render.py writes each WAV with its --warmup seconds of silence first and the
plugin's reported latency (4800 samples at 48 kHz in 1.2.0) still in it. This cuts both and keeps the phrase length
from RENDER_DIR/presets.json, writing RENDER_DIR/wav/<slug>.wav (float stereo 48 kHz) and RENDER_DIR/batch.json.
"""
import argparse, json, os, shutil, struct

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--warmup', type=float, default=1.0); ap.add_argument('--latency', type=int, default=4800)
a = ap.parse_args()
os.makedirs(os.path.join(a.dst, 'wav'), exist_ok=True)
for row in json.load(open(os.path.join(a.dst, 'presets.json'))):
    d = open(os.path.join(a.src, 'wav', row['slug'] + '.wav'), 'rb').read()
    i = d.find(b'data'); x = d[i + 8:]
    start = (int(round(a.warmup * 48000)) + a.latency) * 8
    x = x[start:start + int(round(row['seconds'] * 48000)) * 8]
    x += b'\0' * (int(round(row['seconds'] * 48000)) * 8 - len(x))
    hdr = b'RIFF' + struct.pack('<I', 36 + len(x)) + b'WAVEfmt ' + struct.pack('<IHHIIHH', 16, 3, 2, 48000, 384000, 8, 32) + b'data' + struct.pack('<I', len(x))
    open(os.path.join(a.dst, 'wav', row['slug'] + '.wav'), 'wb').write(hdr + x)
shutil.copy(os.path.join(a.src, 'batch.json'), os.path.join(a.dst, 'batch.json'))
print('trimmed', len(json.load(open(os.path.join(a.dst, 'presets.json')))), 'renders')
