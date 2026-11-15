#!/usr/bin/env python3
"""Put the album's rendered tracks on the page: encode, export the event lists, write album.json.

    build_site.py RENDER_DIR SITE_DIR [--tracks 01,02] [--master]

RENDER_DIR holds songrender's output (<slug>.wav, <slug>.json, run with --keep-wav). For each track this writes:
  SITE_DIR/audio/<nn>.opus   Opus 112 kbps (the page's first choice)
  SITE_DIR/audio/<nn>.mp3    MP3 192 kbps (for browsers without Opus)
  SITE_DIR/data/<nn>.json    the MIDI events the Event List window shows: {"parts": [...], "ev": [[ms, part, note, vel, len_ms], ...]}
and SITE_DIR/album.json with every track's title, length, key, tempo, notes and presets.
--master runs master.py on the WAV first (the album's gentle master chain and loudness match).
"""
import argparse, glob, hashlib, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALB = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(ALB, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'songrender'))
import songrender as sr   # noqa: E402
from smf import Smf   # noqa: E402

FFMPEG = os.path.expanduser('~/.local/bin/ffmpeg')
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def tempo_map(m):
    tm = []
    for tr in m.tracks:
        for t, e in tr:
            if e[:2] == b'\xff\x51':
                tm.append((t, int.from_bytes(e[3:6], 'big')))
    tm = sorted(tm) or [(0, 500000)]
    if tm[0][0] != 0:
        tm.insert(0, (0, 500000))

    def sec(tick):
        s, last_t, us = 0.0, 0, tm[0][1]
        for t, u in tm:
            if t > tick:
                break
            s += (t - last_t) * us / 1e6 / m.division
            last_t, us = t, u
        return s + (tick - last_t) * us / 1e6 / m.division
    return sec


def events(song):
    m = Smf.read(song.midi_path)
    sec = tempo_map(m)
    parts, ev = [], []
    for ti, t in enumerate(song.tracks):
        if t.mute:
            continue
        ex = m.extract(song.selector(t), t.tr)
        on = {}
        pi = len(parts); parts.append(t.name)
        for tick, e in sorted(ex.tracks[0], key=lambda z: z[0]):
            st = e[0] & 0xF0
            if st == 0x90 and e[2] > 0:
                on.setdefault(e[1], []).append((tick, e[2]))
            elif st == 0x80 or (st == 0x90 and e[2] == 0):
                if on.get(e[1]):
                    t0, v = on[e[1]].pop(0)
                    a = sec(t0)
                    ev.append([int(round(a * 1000)), pi, e[1], v, int(round((sec(tick) - a) * 1000))])
    ev.sort()
    return {'parts': parts, 'ev': ev}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('render'); ap.add_argument('site')
    ap.add_argument('--tracks', default='')
    ap.add_argument('--master', action='store_true')
    a = ap.parse_args()
    os.makedirs(os.path.join(a.site, 'audio'), exist_ok=True)
    os.makedirs(os.path.join(a.site, 'data'), exist_ok=True)
    want = set(x for x in a.tracks.split(',') if x)
    aj = os.path.join(a.site, 'album.json')
    album = json.load(open(aj)) if os.path.exists(aj) else {'tracks': []}
    by = {t['n']: t for t in album['tracks']}
    for songf in sorted(glob.glob(os.path.join(ALB, 'tracks', '[0-9][0-9]-*.song'))):
        slug = os.path.splitext(os.path.basename(songf))[0]
        nn = slug[:2]
        if want and nn not in want:
            continue
        rep = os.path.join(a.render, slug + '.json')
        wav = os.path.join(a.render, slug + '.wav')
        if not os.path.exists(rep) or not os.path.exists(wav):
            if int(nn) not in by or by[int(nn)].get('pending'):
                song = sr.Song(songf)
                m = Smf.read(song.midi_path); sec = tempo_map(m)
                end = max(t for tr in m.tracks for t, e in tr)
                by[int(nn)] = {'n': int(nn), 'title': song.meta['title'], 'seconds': round(sec(end) + 3, 1),
                               'note': song.meta.get('note', ''), 'pending': True}
            print('not rendered (listed as pending):', slug); continue
        r = json.load(open(rep))
        src = wav
        if a.master:
            src = os.path.join(a.render, slug + '.master.wav')
            subprocess.run([sys.executable, os.path.join(HERE, 'master.py'), wav, src], check=True)
        op, mp = os.path.join(a.site, 'audio', nn + '.opus'), os.path.join(a.site, 'audio', nn + '.mp3')
        meta = ['-metadata', f'title={r["title"]}', '-metadata', 'album=CITYPOP DEPROGRAMMED', '-metadata', f'track={int(nn)}',
                '-metadata', 'artist=Algorithmic Industries', '-metadata', 'comment=Performed on SNDWAVE2000']
        subprocess.run([FFMPEG, '-y', '-v', 'error', '-i', src, '-c:a', 'libopus', '-b:a', '112k', '-vbr', 'on',
                        '-ar', '48000'] + meta + [op], check=True)
        subprocess.run([FFMPEG, '-y', '-v', 'error', '-i', src, '-c:a', 'libmp3lame', '-b:a', '192k', '-ar', '44100']
                       + meta + [mp], check=True)
        song = sr.Song(songf)
        ev = events(song)
        json.dump(ev, open(os.path.join(a.site, 'data', nn + '.json'), 'w'), separators=(',', ':'))
        mm = song.meta
        pres = [{'part': t['track'] if 'track' in t else t.get('name'), 'preset': t.get('label') or t.get('preset')}
                for t in r.get('tracks', [])]
        h = hashlib.sha256(open(op, 'rb').read()).hexdigest()[:10]
        by[int(nn)] = {'n': int(nn), 'title': r['title'], 'seconds': r['seconds'], 'note': mm.get('note', ''),
                       'bpm': round(r['bpm'], 1), 'opus': f'audio/{nn}.opus?v={h}', 'mp3': f'audio/{nn}.mp3?v={h}',
                       'events': f'data/{nn}.json?v={h}', 'presets': pres, 'lufs': r['mix']['lufs']}
        print(f'{nn} {r["title"]}: {r["seconds"]:.1f} s, {len(ev["ev"])} events')
    album['tracks'] = [by[k] for k in sorted(by)]
    album['title'] = 'CITYPOP DEPROGRAMMED'
    json.dump(album, open(aj, 'w'), indent=1, ensure_ascii=False)
    sources_txt(os.path.join(a.site, 'SOURCES.TXT'))


def sources_txt(path):
    """SOURCES.TXT: every recording the album's own library uses, with its author, licence and page"""
    cat = json.load(open(os.path.join(ALB, 'sounds', 'rainy_loft.json')))
    L = ['CITYPOP DEPROGRAMMED: SOURCES', '', 'Every note was played by SNDWAVE2000 (Windows 3.11 Sound Recorders in DOSBox Pure).',
         'The album\'s sound library, the Rainy Loft Collection, was prepared from these recordings:', '',
         'Recordings dedicated to the public domain (CC0 1.0), from Freesound:', '']
    for c in sorted(cat, key=lambda c: c['author'].lower()):
        L.append(f'  {c["description"][:70]}')
        L.append(f'    by {c["author"]}, {c["license"]}, {c["source_url"]}')
    L += ['', 'Electric piano and bass: the Bele Dance instruments (midigarden) by William Sharkey, rendered offline.',
          'Sounds by Paul Chauncy (Uncle Homunculus / Paulywauly), from the Paulywaulophone pack.',
          'Other SNDWAVE2000 pack discs used: Tape Parlour, Polysynth Showroom, Courtyard Chapel, Studio Archive,',
          '  Garden Rhythm Works and the library disc. Their own LIBRARY.TSV files list their sources (CC0 / public domain).',
          'Paganini, Caprice No. 24 in A minor (published 1820): public domain; one bar is quoted in Var. VI.',
          'Windows for Workgroups 3.11 and Sound Recorder (c) Microsoft Corporation. DOSBox Pure: GPL-2.0-or-later.',
          '', 'The compositions, arrangements and recordings of CITYPOP DEPROGRAMMED: CC0 1.0.']
    open(path, 'w', newline='\r\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
