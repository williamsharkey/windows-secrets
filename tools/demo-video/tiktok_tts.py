#!/usr/bin/env python3
"""The narration in TikTok's text-to-speech voice (en_us_001), at the owner's request: every line of script.py whose
speaker has a 'tiktok' voice. Fetched through a public no-login proxy of TikTok's TTS, politely: one request at a time,
a pause between them, and a cache keyed by the line's text, so only new or changed lines are fetched again. Only the
script's lines are sent. Writes TTS_DIR/<id>.wav (24 kHz mono) and TTS_DIR/lines.json.

    tiktok_tts.py TTS_DIR CACHE_DIR [--delay 2.5]

If the proxy fails, the line is reported and left out; tts.py (Kokoro) is the fallback.
"""
import argparse, base64, hashlib, json, os, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES, VOICES

URL = 'https://ottsy.weilbyte.dev/api/generation'   # (tiktok-tts.weilnet.workers.dev redirects here)
ap = argparse.ArgumentParser()
ap.add_argument('tts'); ap.add_argument('cache'); ap.add_argument('--delay', type=float, default=2.5)
a = ap.parse_args()
os.makedirs(a.tts, exist_ok=True); os.makedirs(a.cache, exist_ok=True)
lj = os.path.join(a.tts, 'lines.json')
meta = json.load(open(lj)) if os.path.exists(lj) else {}
failed = []
for lid, spk, text, cap in LINES:
    voice = VOICES[spk].get('tiktok')
    if not voice: continue
    key = hashlib.sha1(f'{voice}\n{text}'.encode()).hexdigest()[:16]
    mp3 = os.path.join(a.cache, f'{lid}-{key}.mp3')
    if not os.path.exists(mp3):
        req = urllib.request.Request(URL, data=json.dumps({'text': text, 'voice': voice}).encode(),
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            if not r.get('success'): raise RuntimeError(r.get('error'))
            open(mp3, 'wb').write(base64.b64decode(r['data']))
            print('fetched', lid, flush=True)
        except Exception as e:
            print('FAILED', lid, e, flush=True); failed.append(lid); continue
        finally:
            time.sleep(a.delay)
    wav = os.path.join(a.tts, lid + '.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp3, '-af', 'silenceremove=start_periods=1:start_threshold=-50dB,areverse,'
                    'silenceremove=start_periods=1:start_threshold=-50dB,areverse', '-ac', '1', '-ar', '24000', wav], check=True)
    secs = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', wav],
                                capture_output=True, text=True).stdout)
    meta[lid] = {'speaker': spk, 'seconds': round(secs, 3), 'caption': cap or text, 'voice': f'TikTok TTS {voice}'}
ids = {l[0] for l in LINES}
meta = {k: v for k, v in meta.items() if k in ids}
json.dump(meta, open(lj, 'w'), indent=1)
print(len(meta), 'lines,', round(sum(m['seconds'] for m in meta.values()), 1), 's;', 'failed:', failed or 'none')
sys.exit(1 if failed else 0)
