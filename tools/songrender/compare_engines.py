#!/usr/bin/env python3
"""compare_engines: a song's stems from render311 against the same stems through the real plugin in BasiliskHost.

    compare_engines.py SONG.song --host BasiliskHost.exe --plugin SNDWAVE2000.vst3 [--machine DIR] [--tracks a,b]

Each track is rendered both ways (songrender's stem cache keeps them apart: the engine id is part of the key), then
compared: the best alignment within +-50 ms, the largest sample difference, the RMS of the difference against the
stem's own RMS (dB), and the correlation.
"""
import argparse, os, sys, types
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import songrender as sr   # noqa: E402


def stems(song_path, engine, a):
    args = types.SimpleNamespace(render311=os.path.abspath(a.render311), machine=os.path.abspath(a.machine), cache=a.cache,
                                 engine=engine, plugin_id='')
    ha = None
    if engine == 'host':
        import host_song
        ha = host_song.HostArgs(a.host, a.plugin)
        args.plugin_id = ha.ident()
    s = sr.Song(song_path)
    jobs = sr.plan(s, args)
    if a.tracks:
        jobs = [j for j in jobs if j.track.name in a.tracks.split(',')]
    for j in jobs:
        r = sr.render_stem(j, args.render311, args.machine, engine, ha)
        print(f'   {engine:9s} {j.track.name:12s} {r} {j.log}', flush=True)
    return {j.track.name: j.path for j in jobs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('song')
    ap.add_argument('--host', required=True)
    ap.add_argument('--plugin', required=True)
    ap.add_argument('--render311', default=sr.DEF_RENDER311)
    ap.add_argument('--machine', default=sr.DEF_MACHINE)
    ap.add_argument('--cache', default=sr.DEF_CACHE)
    ap.add_argument('--tracks', default='')
    a = ap.parse_args()
    A = stems(a.song, 'render311', a)
    B = stems(a.song, 'host', a)
    print(f'{"track":12s} {"lag ms":>7s} {"max diff":>9s} {"diff/rms dB":>11s} {"corr":>7s} {"identical":>9s}')
    for name in A:
        x, y = sr.load_flac(A[name]), sr.load_flac(B[name])
        n = min(len(x), len(y))
        x, y = x[:n].mean(axis=1), y[:n].mean(axis=1)
        best, lag = -2, 0
        for L in range(-2400, 2401, 48):
            if L >= 0:
                c = np.corrcoef(x[L:], y[:n - L])[0, 1] if n - L > 1000 else 0
            else:
                c = np.corrcoef(x[:n + L], y[-L:])[0, 1]
            if c > best:
                best, lag = c, L
        for L in range(lag - 48, lag + 49):
            xx, yy = (x[L:], y[:n - L]) if L >= 0 else (x[:n + L], y[-L:])
            c = np.corrcoef(xx, yy)[0, 1]
            if c > best:
                best, lag = c, L
        xx, yy = (x[lag:], y[:n - lag]) if lag >= 0 else (x[:n + lag], y[-lag:])
        d = xx - yy
        rel = 20 * np.log10(np.sqrt(np.mean(d ** 2)) / (np.sqrt(np.mean(xx ** 2)) + 1e-12) + 1e-12)
        print(f'{name:12s} {lag / 48:7.2f} {np.max(np.abs(d)):9.6f} {rel:11.1f} {best:7.4f} {str(bool(np.max(np.abs(d)) == 0)):>9s}')


if __name__ == '__main__':
    main()
