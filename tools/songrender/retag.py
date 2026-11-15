#!/usr/bin/env python3
"""retag: rewrite the artist tag of published song files without re-encoding them.

    retag.py SITE_SONGS_DIR [--artist "Algorithmic Industries (SNDWAVE1993)"] [--dry]

For every <pack>/<slug>.ogg and .mp3 under the directory (make_index.py's --dest), ffmpeg stream-copies the audio
(-c copy) and rewrites only the tags: the Opus comment header (a stream tag) or the MP3's ID3v2.3. Each file is
checked before it replaces the old one: the audio packets (ffmpeg -f md5 of the copied stream) must be identical,
and the new artist must read back. index.json's sha256 for each file is then updated.
"""
import argparse, hashlib, json, os, subprocess, sys


def packets_md5(path):
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', path, '-map', '0:a', '-c', 'copy', '-f', 'md5', '-'],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def artist_of(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format_tags=artist:stream_tags=artist', '-of',
                        'default=nw=1:nk=1', path], capture_output=True, text=True, check=True)
    return [l for l in r.stdout.split('\n') if l]


def retag(path, artist):
    tmp = path + '.retag' + os.path.splitext(path)[1]
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', path, '-map', '0', '-c', 'copy', '-map_metadata', '0',
           '-fflags', '+bitexact', '-flags', '+bitexact']
    if path.endswith('.ogg'):   # Opus keeps its tags in the stream's comment header
        cmd += ['-map_metadata:s:a', '0:s:a', '-metadata:s:a', f'artist={artist}']
    else:
        cmd += ['-metadata', f'artist={artist}', '-id3v2_version', '3']
    subprocess.run(cmd + [tmp], check=True)
    if packets_md5(tmp) != packets_md5(path):
        os.remove(tmp)
        raise SystemExit(f'{path}: the audio changed in the copy; left as it was')
    if artist not in artist_of(tmp):
        os.remove(tmp)
        raise SystemExit(f'{path}: the new artist did not read back')
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--artist', default='Algorithmic Industries (SNDWAVE1993)')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    ix = os.path.join(a.dir, 'index.json')
    I = json.load(open(ix))
    n = 0
    for pk, p in I['packs'].items():
        for s in p['songs']:
            for ext in ('ogg', 'mp3'):
                f = os.path.join(a.dir, pk, f"{s['slug']}.{ext}")
                if a.artist in artist_of(f):
                    pass
                elif a.dry:
                    print('would retag', f)
                    continue
                else:
                    retag(f, a.artist)
                s['sha256'][ext] = hashlib.sha256(open(f, 'rb').read()).hexdigest()
                n += 1
    if not a.dry:
        json.dump(I, open(ix, 'w'), indent=1, ensure_ascii=False)
    print(n, 'files', '(dry run)' if a.dry else 'retagged and hashed ->', ix)


if __name__ == '__main__':
    sys.exit(main())
