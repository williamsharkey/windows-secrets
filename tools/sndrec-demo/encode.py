#!/usr/bin/env python3
"""Check and encode the rendered demo phrases for sndrec.html.

    encode.py RENDER_DIR OUT_AUDIO_DIR EDITION [--lufs -16] [--kbps 96]

RENDER_DIR is phrases.py's output after the batch renderer ran (presets.json, mid/, wav/, batch.json).
For each preset:
- checks the 48 kHz float WAV the plugin's renderer wrote: silent? clipped? the right length? each note heard?
- normalizes to about -16 LUFS (ffmpeg ebur128 measure, then gain; a -1 dBFS limiter only if the gain would clip),
  fades the last 0.4 s, and encodes MP3 at 96 kbps, mono when the left and right channels are identical;
- writes OUT_AUDIO_DIR/<slug>.mp3 and RENDER_DIR/manifest.json (preset rows plus a 64-bar waveform, the checks and
  flags), which the page reads.
The sound itself is never changed except by that gain, the limiter (when needed) and the fade.
"""
import argparse, json, os, re, struct, subprocess, sys, wave
import numpy as np

SR = 48000


def read_wav_f32(path):
    d = open(path, 'rb').read()
    i = d.find(b'data')
    ch = struct.unpack_from('<H', d, 22)[0]
    a = np.frombuffer(d[i + 8:i + 8 + (len(d) - i - 8) // 4 * 4], dtype='<f4')
    return a.reshape(-1, ch)


def note_ons(mid):
    d = open(mid, 'rb').read()
    p = d.find(b'MTrk') + 8
    t, out, run = 0, [], 0
    while p < len(d):
        v = 0
        while True:
            c = d[p]; p += 1; v = (v << 7) | (c & 0x7F)
            if not c & 0x80: break
        t += v
        st = d[p]
        if st == 0xFF:
            ln = d[p + 2]; p += 3 + ln; continue
        if st & 0x80: p += 1; run = st
        else: st = run
        a, b = d[p], d[p + 1]; p += 2
        if st & 0xF0 == 0x90 and b: out.append((t / 960.0, a, b))
    return out


def lufs(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    return float(m[-1]) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('render'); ap.add_argument('out'); ap.add_argument('edition')
    ap.add_argument('--lufs', type=float, default=-16.0); ap.add_argument('--kbps', type=int, default=96)
    ap.add_argument('--renderer', default='render311', help='what rendered the plain demos')
    ap.add_argument('--macro-renderer', default='BasiliskHost (VST3, Macro 1 automated)')
    ap.add_argument('--review', help='JSON of listening notes per slug: {"drop": [flag substrings], "note": text}')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = json.load(open(os.path.join(a.render, 'presets.json')))
    batch = {r['out']: r for r in json.load(open(os.path.join(a.render, 'batch.json')))['results']}
    mp = os.path.join(a.render, 'macro.json')
    macro = json.load(open(mp)) if os.path.exists(mp) else {}
    review = json.load(open(a.review)) if a.review else {}
    sp = os.path.join(a.render, 'sources.json')   # demos kept from an earlier release's take, and why
    sources = json.load(open(sp)) if os.path.exists(sp) else {}
    man = []
    for row in rows:
        wavp = os.path.join(a.render, 'wav', row['slug'] + '.wav')
        x = read_wav_f32(wavp).astype(np.float64)
        dur = len(x) / SR
        peak = float(np.abs(x).max()) if len(x) else 0.0
        clips = int((np.abs(x) >= 0.999).sum())
        rms = float(np.sqrt((x ** 2).mean())) if len(x) else 0.0
        mono = bool(np.abs(x[:, 0] - x[:, 1]).max() <= 1e-6 * max(peak, 1e-9)) if x.shape[1] == 2 else True
        m = x.mean(axis=1)
        # each distinct note-on time: is there sound in the 300 ms after it?
        ons = sorted(set(round(t, 3) for t, _, _ in note_ons(os.path.join(a.render, 'mid', row['slug'] + '.mid'))))
        heard = 0
        win = 1.0 if row['kind'] in ('pad', 'drone', 'fx', 'collage') else 0.3   # slow attacks get longer
        for t in ons:
            seg = m[int(t * SR):int((t + win) * SR)]
            if len(seg) and 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12) > -50: heard += 1
        flags = []
        if peak < 0.003: flags.append('silent')
        if clips: flags.append('hot: peaks at %+.1f dBFS (float output, %d samples over full scale)' % (20 * np.log10(peak), clips))
        if abs(dur - row['seconds']) > 0.05: flags.append('length %.2f s, expected %.2f s' % (dur, row['seconds']))
        if ons and heard < len(ons) and 'silent' not in flags: flags.append('%d of %d note onsets silent' % (len(ons) - heard, len(ons)))
        mac = macro.get(row['slug'])
        log = '' if mac else batch.get('wav/%s.wav' % row['slug'], {}).get('log', '')
        late = re.search(r'late notes (\d+) of (\d+)', log)
        if late and int(late.group(1)): flags.append('%s late notes' % late.group(1))
        if 'silent' not in flags and rms > 0:
            I0 = lufs(wavp)
            if I0 is not None and I0 < -36: flags.append('very quiet: %.0f LUFS before normalizing' % I0)
        rv = review.get(row['slug'], {})
        flags = [f for f in flags if not any(d in f for d in rv.get('drop', []))]
        mp3 = os.path.join(a.out, row['slug'] + '.mp3')
        wave_bars, I_before, I_after, gain_db = [0] * 64, None, None, 0.0
        if 'silent' not in flags:
            I_before = lufs(wavp)
            gain_db = a.lufs - I_before if I_before is not None and I_before > -70 else 0.0
            gpeak = 20 * np.log10(peak) + gain_db
            fade = max(0.0, dur - 0.4)
            af = 'volume=%.3fdB' % gain_db
            if gpeak > -1.0: af += ',alimiter=limit=%.4f:attack=1:release=60:level=disabled' % (10 ** (-1.0 / 20))
            af += ',afade=t=out:st=%.3f:d=0.4' % fade
            subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', wavp, '-af', af,
                            '-ac', '1' if mono else '2', '-ar', '48000', '-c:a', 'libmp3lame', '-b:a', '%dk' % a.kbps,
                            '-map_metadata', '-1', '-id3v2_version', '0', '-write_xing', '1', mp3], check=True)
            I_after = lufs(mp3)
            g = 10 ** (gain_db / 20)
            env = np.abs(m) * g
            n = len(env) // 64
            wave_bars = [round(float(min(1.0, env[k * n:(k + 1) * n].max())), 3) for k in range(64)]
        man.append(dict(row, edition=a.edition, renderer=sources.get(row['slug']) or (a.macro_renderer if mac else a.renderer),
                        macro_curve=mac['curve'] if mac else None, file=os.path.basename(mp3) if 'silent' not in flags else None,
                        mono=mono, peak_dbfs=round(20 * np.log10(peak + 1e-12), 1), rms_dbfs=round(20 * np.log10(rms + 1e-12), 1),
                        lufs_render=I_before, lufs_out=I_after, gain_db=round(gain_db, 1), onsets=len(ons), heard=heard,
                        render_seconds=round(dur, 2), flags=flags, note=rv.get('note'), wave=wave_bars,
                        bytes=os.path.getsize(mp3) if os.path.exists(mp3) and 'silent' not in flags else 0))
        print('%-28s %-8s peak %6.1f  I %s -> %s  %s  %s' % (row['slug'][:28], row['kind'], 20 * np.log10(peak + 1e-12),
              I_before, I_after, 'mono' if mono else 'stereo', '; '.join(flags)), flush=True)
    json.dump(man, open(os.path.join(a.render, 'manifest.json'), 'w'), indent=1)
    print('%d presets, %d flagged, %.1f MB' % (len(man), sum(1 for r in man if r['flags']), sum(r['bytes'] for r in man) / 1e6))


if __name__ == '__main__':
    main()
