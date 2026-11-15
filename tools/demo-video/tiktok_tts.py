#!/usr/bin/env python3
"""The opening and closing announcer lines in TikTok's text-to-speech voice (en_us_001), at the owner's request; every
other line is Kokoro. Fetched once through a public proxy of TikTok's TTS (no login), cached, then converted into the
tts folder in place of the Kokoro takes. Only the script lines are sent.

    tiktok_tts.py TTS_DIR CACHE_DIR
"""
import base64, json, os, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES

IDS = ('ann_open', 'ann_tag')
URL = 'https://ottsy.weilbyte.dev/api/generation'   # (tiktok-tts.weilnet.workers.dev redirects here)
tts, cache = sys.argv[1], sys.argv[2]
os.makedirs(cache, exist_ok=True)
meta = json.load(open(os.path.join(tts, 'lines.json')))
for lid, spk, text, cap in LINES:
    if lid not in IDS: continue
    mp3 = os.path.join(cache, lid + '.mp3')
    if not os.path.exists(mp3):
        req = urllib.request.Request(URL, data=json.dumps({'text': text, 'voice': 'en_us_001'}).encode(),
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        if not r.get('success'): sys.exit(f'{lid}: {r.get("error")}')
        open(mp3, 'wb').write(base64.b64decode(r['data']))
        time.sleep(2)
    wav = os.path.join(tts, lid + '.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp3, '-af', 'silenceremove=start_periods=1:start_threshold=-50dB,areverse,'
                    'silenceremove=start_periods=1:start_threshold=-50dB,areverse', '-ac', '1', '-ar', '24000', wav], check=True)
    secs = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', wav],
                                capture_output=True, text=True).stdout)
    meta[lid] = {'speaker': 'ANN', 'seconds': round(secs, 3), 'caption': cap or text, 'voice': 'TikTok TTS en_us_001'}
    print(lid, round(secs, 2), 's')
json.dump(meta, open(os.path.join(tts, 'lines.json'), 'w'), indent=1)
