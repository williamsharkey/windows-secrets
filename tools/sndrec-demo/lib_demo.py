#!/usr/bin/env python3
"""The owner's picks from the library (coming in BASILISK 16 1.3.0) for sndrec.html.

    lib_demo.py RATINGS.json LIBRARY.json MP3_DIR AUDIO_OUT RENDER_DIR [--min 6.5]

RATINGS.json: the owner's review export (packages/basilisk-synth/library/builder/ratings/...). LIBRARY.json: the
builder's out/library.json (DNA, category, pack, phrase, how it was rendered). MP3_DIR: the library build's demo
phrases ($LIBBUILD/mp3), the very files the owner listened to and rated: rendered by render311 through the real
Windows 3.11 machine (main 4bda617), each phrase checked by the builder's finalize step (every note onset heard, not
clipped, not silent, ends in its tail). They are copied as they are (no second lossy encode): AUDIO_OUT/<slug>.mp3.
Their level is the preset's own (its G gene), about -16 to -19 LUFS, so they are not re-levelled.
Writes RENDER_DIR/manifest.json, the rows site_data.py reads (rating, pack, waveform from the decoded MP3).
"""
import argparse, json, os, shutil, subprocess
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('ratings'); ap.add_argument('library'); ap.add_argument('mp3'); ap.add_argument('audio'); ap.add_argument('render')
ap.add_argument('--min', type=float, default=6.5)
a = ap.parse_args()
R = json.load(open(a.ratings))['presets']
L = {e['slug']: e for e in json.load(open(a.library))}
top = sorted([(v['rating'], k) for k, v in R.items() if (v.get('rating') or 0) >= a.min and k in L], key=lambda x: (-x[0], L[x[1]]['name']))
os.makedirs(a.audio, exist_ok=True); os.makedirs(a.render, exist_ok=True)
rows = []
for n, (rating, slug) in enumerate(top):
    e = L[slug]; src = os.path.join(a.mp3, slug + '.mp3'); dst = os.path.join(a.audio, slug + '.mp3')
    shutil.copy(src, dst)
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-f', 'f32le', '-ac', '1', '-ar', '48000', '-'], capture_output=True).stdout
    m = np.abs(np.frombuffer(pcm, '<f4'))
    k = len(m) // 64
    wave = [round(float(min(1.0, m[i * k:(i + 1) * k].max())), 3) for i in range(64)]
    v3 = e.get('v3')
    rows.append({'i': n, 'cat': e['category'], 'name': e['name'], 'dna': e['dna'], 'kind': e.get('phrase'), 'phrase': e.get('phrase'),
                 'slug': slug, 'render_seconds': round(len(m) / 48000, 2), 'wave': wave, 'flags': [], 'file': slug + '.mp3',
                 'note': 'Uses DNA v3 (W/Y genes): BASILISK 16 1.3.0 only.' if v3 else None,
                 'renderer': e.get('rendered_by'), 'macro_curve': None, 'rating': rating, 'pack_name': e.get('pack_name'),
                 'ships': e.get('ships'), 'v3': v3})
json.dump(rows, open(os.path.join(a.render, 'manifest.json'), 'w'), indent=1)
print(len(rows), 'picks;', sum(os.path.getsize(os.path.join(a.audio, r['file'])) for r in rows) // 1024, 'KB')
