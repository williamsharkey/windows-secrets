#!/usr/bin/env python3
"""Narration with Kokoro-82M (hexgrad/Kokoro-82M, Apache-2.0), run locally on the CPU.

    ~/video/kvenv/bin/python tts.py OUT_DIR [ID ...]      one 24 kHz WAV per line of script.py, and lines.json
"""
import json, os, sys
import numpy as np, soundfile as sf, torch
from kokoro import KPipeline
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, VOICES

torch.set_num_threads(4)
out = sys.argv[1]
only = set(sys.argv[2:])
os.makedirs(out, exist_ok=True)
pipes, packs = {}, {}
meta = json.load(open(os.path.join(out, 'lines.json'))) if os.path.exists(os.path.join(out, 'lines.json')) else {}
for lid, spk, text, cap in LINES:
    if only and lid not in only: continue
    v = VOICES[spk]
    p = pipes.get(v['lang']) or pipes.setdefault(v['lang'], KPipeline(lang_code=v['lang'], repo_id='hexgrad/Kokoro-82M'))
    if spk not in packs:   # a weighted blend of voice packs
        vv = v['voice']
        packs[spk] = sum(p.load_voice(vv[k]) * vv[k + 1] for k in range(0, len(vv), 2))
    audio = np.concatenate([r.audio.numpy() for r in p(text, voice=packs[spk], speed=v['speed'])])
    # trim leading/trailing silence to 30 ms
    nz = np.nonzero(np.abs(audio) > 0.01)[0]
    audio = audio[max(0, nz[0] - 720): nz[-1] + 720]
    sf.write(os.path.join(out, lid + '.wav'), audio, 24000)
    meta[lid] = {'speaker': spk, 'seconds': round(len(audio) / 24000, 3), 'caption': cap or text}
    print(f'{lid:12s} {spk:4s} {len(audio) / 24000:6.2f} s', flush=True)
json.dump(meta, open(os.path.join(out, 'lines.json'), 'w'), indent=1)
print('total', round(sum(m['seconds'] for m in meta.values()), 1), 's')
