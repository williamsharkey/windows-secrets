#!/usr/bin/env python3
"""songrender: multitrack song demos for SNDWAVE2000, rendered headlessly through the real Windows 3.11 machine.

    songrender.py SONG.song [SONG.song ...] --out-dir DIR [--render311 EXE] [--machine DIR] [--jobs 6]
                  [--cache DIR] [--stems] [--keep-wav] [--engine render311|host] [--dry]

Each track of a song is its own engine: one render311 run, that is one emulated Windows 3.11 with its 16 Sound
Recorders, playing only that track's notes (a DAW with one plugin instance per track). The stems are then mixed to
stereo: volume, pan, a send to a shared echo and a shared reverb, mute/solo, then a master loudness gain and a
look-ahead peak limiter. Every note is played by Sound Recorder; the mixer only adds, delays and scales the
recorders' own output. Output: DIR/<slug>.wav (48 kHz 24-bit), <slug>.ogg (Opus 64 kbps), <slug>.mp3 (128 kbps)
and <slug>.json (what was rendered, with every DNA).

The song format is in README.md beside this file. Renders are deterministic: the same song, MIDI, machine and
render311 give bit-identical stems, WAV, Opus and MP3.
"""
import argparse, concurrent.futures as cf, hashlib, json, math, os, re, shlex, shutil, subprocess, sys, tempfile, time

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smf import Smf   # noqa: E402

SR = 48000
HOME = os.path.expanduser('~')
DEF_RENDER311 = os.environ.get('SONGRENDER_RENDER311', os.path.join(HOME, 'songs', 'build', 'render311-la'))
DEF_MACHINE = os.environ.get('SONGRENDER_MACHINE', os.path.join(HOME, 'songs', 'machine'))
DEF_CACHE = os.environ.get('SONGRENDER_CACHE', os.path.join(HOME, 'songs', 'cache'))
MAX_JOBS = 6   # the PC is shared: never more engines than this at once


# ------------------------------------------------------------------------------------------------- the song file
class Track:
    def __init__(self):
        self.name = ''; self.src = ''; self.preset = ''; self.dna = ''
        self.vol = 0.0; self.pan = 0.0; self.echo = 0.0; self.verb = 0.0
        self.tr = 0; self.vel = 1.0; self.mute = False; self.solo = False; self.width = 1.0
        self.hp = 0.0; self.lp = 0.0; self.tune = 0.0; self.lufs = None


class Song:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        self.slug = os.path.splitext(os.path.basename(path))[0]
        self.meta = {}
        self.sec = {'master': {}, 'echo': {}, 'reverb': {}}
        self.pinned = {}   # [dna]: "pack:Name" = DNA, recorded when the song was written
        self.tracks = []
        section = None
        for ln, raw in enumerate(open(path, encoding='utf-8'), 1):
            line = raw.rstrip('\n')
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            m = re.match(r'^\[(\w+)\]$', s)
            if m:
                section = m.group(1).lower()
                if section not in ('master', 'echo', 'reverb', 'tracks', 'dna'):
                    raise SystemExit(f'{path}:{ln}: unknown section [{section}]')
                continue
            if section == 'tracks':
                self.tracks.append(self._track(s, path, ln))
                continue
            if section == 'dna':
                m = re.match(r'^"([^"]+)"\s*=\s*(\S+)$', s)
                if not m:
                    raise SystemExit(f'{path}:{ln}: [dna] lines are: "pack:Name" = DNA')
                self.pinned[m.group(1)] = m.group(2)
                continue
            m = re.match(r'^([\w-]+)\s*[=:]\s*(.*)$', s)
            if not m:
                raise SystemExit(f'{path}:{ln}: expected "key = value"')
            k, v = m.group(1).lower(), m.group(2).strip()
            if section is None:
                if k in self.meta and k in ('credit', 'note'):
                    self.meta[k] += '\n' + v
                else:
                    self.meta[k] = v
            else:
                self.sec[section][k] = v
        for k in ('title', 'pack', 'midi'):
            if k not in self.meta:
                raise SystemExit(f'{path}: missing "{k} ="')
        self.midi_path = os.path.join(self.dir, self.meta['midi'])

    @staticmethod
    def _track(s, path, ln):
        try:
            parts = shlex.split(s, comments=True)
        except ValueError as e:
            raise SystemExit(f'{path}:{ln}: {e}')
        if len(parts) < 3:
            raise SystemExit(f'{path}:{ln}: a track is: NAME SOURCE PRESET [key=value ...]')
        t = Track()
        t.name, t.src, p = parts[0], parts[1], parts[2]
        if p.startswith('dna:'):
            t.dna = p[4:]
        else:
            t.preset = p
        for kv in parts[3:]:
            if kv in ('mute', 'solo'):
                setattr(t, kv, True); continue
            if '=' not in kv:
                raise SystemExit(f'{path}:{ln}: "{kv}": expected key=value, mute or solo')
            k, v = kv.split('=', 1)
            if k in ('vol', 'pan', 'echo', 'verb', 'vel', 'width', 'hp', 'lp', 'tune', 'lufs'):
                setattr(t, k, float(v))
            elif k in ('tr', 'transpose'):
                t.tr = int(v)
            else:
                raise SystemExit(f'{path}:{ln}: unknown track key "{k}"')
        if not re.match(r'^((ch\d+|tr\d+)(\+|$))+', t.src) and t.src != 'all':
            raise SystemExit(f'{path}:{ln}: source "{t.src}": chN (MIDI channel 1-16), trN (track 0-), joined by +, or all')
        return t

    def selector(self, t):
        if t.src == 'all':
            return lambda ti, ch: True
        chans, trks = set(), set()
        for part in t.src.split('+'):
            if part.startswith('ch'):
                chans.add(int(part[2:]) - 1)
            else:
                trks.add(int(part[2:]))
        return lambda ti, ch: (not chans or ch in chans) and (not trks or ti in trks)


def num(v, default):
    if v is None:
        return default
    return float(str(v).replace('ms', '').replace('dB', '').strip())


# ------------------------------------------------------------------------------------------------- presets
_presets = None


def presets(machine):
    """pack id -> {preset name: DNA}, from the machine's own pack discs (what the engine can play)"""
    global _presets
    if _presets is None:
        _presets = {}
        root = os.path.join(machine, 'packs')
        for l in open(os.path.join(root, 'PACKS.TSV'), encoding='utf-8'):
            f = l.rstrip('\n').split('\t')
            if len(f) < 2:
                continue
            d, pid = f[0], f[1]
            tsv = os.path.join(root, d, 'PRESETS.TSV')
            if not os.path.exists(tsv):
                continue
            m = _presets.setdefault(pid, {})
            for r in open(tsv, encoding='utf-8', errors='replace'):
                if r.startswith('#'):
                    continue
                c = r.rstrip('\n').split('\t')
                if len(c) >= 3:
                    m.setdefault(c[1], c[2])
                    m.setdefault(f'{c[0]}/{c[1]}', c[2])
    return _presets


def resolve(song, t, machine):
    if t.dna:
        return t.dna, '(DNA)'
    pk, name = song.meta['pack'], t.preset
    if ':' in name:
        pk, name = name.split(':', 1)
    if f'{pk}:{name}' in song.pinned:   # the DNA the song was written with (packs change; the song does not)
        return song.pinned[f'{pk}:{name}'], f'{pk}:{name}'
    P = presets(machine).get(pk)
    if P is None:
        raise SystemExit(f'{song.path}: no pack "{pk}" in {machine}/packs')
    if name not in P:
        close = [n for n in P if name.lower() in n.lower()][:6]
        raise SystemExit(f'{song.path}: track {t.name}: no preset "{name}" in {pk}' + (f' (did you mean {close}?)' if close else ''))
    return P[name], f'{pk}:{name}'


# ------------------------------------------------------------------------------------------------- stems
def file_sha(p, h):
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)


_engine_id = {}


def engine_id(render311, machine):
    k = (render311, machine)
    if k not in _engine_id:
        h = hashlib.sha256()
        for p in (render311, os.path.join(machine, 'w31.state'), os.path.join(machine, 'w31.conf'),
                  os.path.join(machine, 'packs', 'PACKS.TSV'), os.path.join(machine, 'library.names.txt')):
            file_sha(p, h)
        for p in ('drive.zip', 'library.zip', 'dosbox_pure_libretro.so'):
            st = os.stat(os.path.join(machine, p)); h.update(f'{p}{st.st_size}'.encode())
        _engine_id[k] = h.hexdigest()[:16]
    return _engine_id[k]


def read_f32_wav(path):
    with open(path, 'rb') as f:
        d = f.read()
    p = 12
    fmt = None
    while p + 8 <= len(d):
        cid, ln = d[p:p + 4], int.from_bytes(d[p + 4:p + 8], 'little')
        if cid == b'fmt ':
            fmt = int.from_bytes(d[p + 8:p + 10], 'little'), int.from_bytes(d[p + 10:p + 12], 'little'), int.from_bytes(d[p + 22:p + 24], 'little')
        elif cid == b'data':
            body = d[p + 8:p + 8 + ln]
            if fmt[0] == 3:
                a = np.frombuffer(body, '<f4')
            elif fmt[2] == 24:
                b = np.frombuffer(body, np.uint8).reshape(-1, 3).astype(np.int32)
                a = ((b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)) << 8 >> 8) / 8388607.0
            else:
                a = np.frombuffer(body, '<i2') / 32767.0
            return a.astype(np.float32).reshape(-1, fmt[1])
        p += 8 + ln + (ln & 1)
    raise ValueError(f'{path}: no data')


def write_wav24(path, x):
    x = np.clip(x, -1.0, 1.0)
    s = np.round(x * 8388607.0).astype(np.int32).reshape(-1)
    b = np.empty((s.size, 3), np.uint8)
    b[:, 0] = s & 0xFF; b[:, 1] = (s >> 8) & 0xFF; b[:, 2] = (s >> 16) & 0xFF
    data = b.tobytes()
    with open(path, 'wb') as f:
        f.write(b'RIFF' + (36 + len(data)).to_bytes(4, 'little') + b'WAVEfmt ' + (16).to_bytes(4, 'little'))
        f.write((1).to_bytes(2, 'little') + (2).to_bytes(2, 'little') + SR.to_bytes(4, 'little') + (SR * 6).to_bytes(4, 'little'))
        f.write((6).to_bytes(2, 'little') + (24).to_bytes(2, 'little') + b'data' + len(data).to_bytes(4, 'little') + data)


class StemJob:
    def __init__(self, song, track, dna, label, midi_bytes, key, tail, bpm, cache, lookahead=0.0):
        self.song, self.track, self.dna, self.label = song, track, dna, label
        self.midi_bytes, self.key, self.tail, self.bpm = midi_bytes, key, tail, bpm
        self.lookahead = lookahead
        self.path = os.path.join(cache, key[:2], key + '.flac')
        self.log = ''
        self.seconds = 0.0


def render_stem(job, render311, machine, engine, host_args):
    """one engine for one track -> the cache (FLAC, 24-bit: render311's own WAV depth)"""
    if os.path.exists(job.path):
        os.utime(job.path)   # recently used (the cache is pruned oldest first)
        return 'cached'
    os.makedirs(os.path.dirname(job.path), exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='songrender-', dir=os.path.dirname(job.path)) as tmp:
        mid = os.path.join(tmp, 'track.mid')
        with open(mid, 'wb') as f:
            f.write(job.midi_bytes)
        wav = os.path.join(tmp, 'track.wav')
        t0 = time.time()
        if engine == 'render311':
            cmd = ['nice', '-n', '10', render311, '--machine', machine, '--core', os.path.join(machine, 'dosbox_pure_libretro.so'),
                   '--dna', job.dna, '--midi', mid, '--out', wav, '--tail', f'{job.tail:g}', '--bpm', f'{job.bpm:.6f}']
            if job.lookahead:   # each event sent this many ms early, its stamp unchanged: dense chords arm on time
                cmd += ['--lookahead', f'{job.lookahead:g}']
            env = dict(os.environ, TMPDIR=tmp)
            r = subprocess.run(cmd, capture_output=True, text=True, env=env)
            job.log = (r.stderr or '').strip().splitlines()[-1:] and r.stderr.strip().splitlines()[-1]
            if r.returncode or not os.path.exists(wav):
                raise RuntimeError(f'render311 failed for {job.song.slug}/{job.track.name}: {r.stderr[-800:]}')
        else:
            import host_song
            job.log = host_song.render_track(host_args, job.dna, mid, wav, job.tail)
        job.seconds = time.time() - t0
        tmpf = os.path.join(tmp, 'stem.flac')
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', wav, '-c:a', 'flac', '-sample_fmt', 's32',
                        '-bits_per_raw_sample', '24', '-compression_level', '8', '-bitexact', '-map_metadata', '-1', tmpf], check=True)
        os.replace(tmpf, job.path)
    return 'rendered'


def prune_cache(cache, limit_gb):
    """keep the stem cache under limit_gb: the least recently used stems go first"""
    fs = []
    for d, _, names in os.walk(cache):
        for n in names:
            if n.endswith('.flac'):
                p = os.path.join(d, n); st = os.stat(p); fs.append((st.st_mtime, st.st_size, p))
    total = sum(f[1] for f in fs)
    for m, sz, p in sorted(fs):
        if total <= limit_gb * 1e9:
            break
        os.remove(p); total -= sz
    return total


def load_flac(path):
    r = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, '<f4').reshape(-1, 2).astype(np.float64)


# ------------------------------------------------------------------------------------------------- mixing
def pan_gains(p, width=1.0):
    th = (max(-100.0, min(100.0, p)) + 100.0) / 200.0 * math.pi / 2
    return math.sqrt(2) * math.cos(th), math.sqrt(2) * math.sin(th)


def onepole_lp(x, fc):
    if fc <= 0 or fc >= SR / 2:
        return x
    a = math.exp(-2 * math.pi * fc / SR)
    return signal.lfilter([1 - a], [1, -a], x, axis=0)


def echo_ir(sec, bpm):
    t = sec.get('time', '3/16')
    if '/' in t:   # a note value, in whole notes: 3/16 is a dotted eighth
        a, b = t.split('/')
        dsec = 240.0 / bpm * float(a) / float(b)
    else:
        dsec = num(t, 375) / 1000.0
    D = max(1, int(round(dsec * SR)))
    fb = min(0.9, num(sec.get('feedback'), 0.35))
    tone = num(sec.get('tone'), 3500)
    ping = sec.get('pingpong', 'yes').lower() in ('yes', 'on', '1', 'true')
    n = 1
    while fb ** n > 0.001 and n < 64:
        n += 1
    L = n * D + 4096
    h = np.zeros((L, 2))
    imp = np.zeros(4096); imp[0] = 1.0
    for k in range(1, n + 1):
        imp = onepole_lp(imp, tone)
        g = fb ** (k - 1)
        if ping:
            h[k * D:k * D + 4096, (k - 1) % 2] += g * imp
        else:
            h[k * D:k * D + 4096, :] += g * imp[:, None] * 0.7071
    return h


def splitmix_gauss(seed, n):
    """n Gaussian-ish samples, bit-exact anywhere: SplitMix64 from `seed` (state x; each output: x += 0x9E3779B97F4A7C15,
    z = x, z = (z ^ z>>30) * 0xBF58476D1CE4E5B9, z = (z ^ z>>27) * 0x94D049BB133111EB, z ^= z>>31), uniform
    u = (z >> 11) * 2^-53; sample i = (u[4i] + u[4i+1] + u[4i+2] + u[4i+3] - 2) * sqrt(3) (Irwin-Hall of 4)"""
    with np.errstate(over='ignore'):
        k = np.arange(1, 4 * n + 1, dtype=np.uint64)
        z = np.uint64(seed) + k * np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        z = z ^ (z >> np.uint64(31))
    u = (z >> np.uint64(11)).astype(np.float64) * (2.0 ** -53)
    return (u.reshape(n, 4).sum(axis=1) - 2.0) * math.sqrt(3.0)


def reverb_ir(sec):
    rt = num(sec.get('size'), 2.0)        # seconds to -60 dB
    pre = num(sec.get('predelay'), 18) / 1000.0
    tone = num(sec.get('tone'), 5500)
    seed = int(num(sec.get('seed'), 3110))
    L = int((rt * 1.2 + pre) * SR)
    t = np.arange(L) / SR
    h = np.zeros((L, 2))
    P = int(pre * SR)
    for c in range(2):
        nz = splitmix_gauss(seed * 2 + c, L)   # one stream per channel (portable: the Song tab draws the same)
        lo = onepole_lp(onepole_lp(nz, tone), tone)
        hi = nz - onepole_lp(nz, tone)
        env_lo = np.exp(-6.9078 * t / rt)
        env_hi = np.exp(-6.9078 * t / (rt * 0.45))
        x = lo * env_lo + 0.35 * hi * env_hi
        x[:int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))   # soft onset
        h[P:, c] = x[:L - P]
    h /= math.sqrt(np.sum(h ** 2) / 2)
    return h


def conv(x, h):
    out = np.zeros((x.shape[0] + h.shape[0] - 1, 2))
    for c in range(2):
        out[:, c] = signal.fftconvolve(x[:, c] if x.ndim == 2 else x, h[:, c])
    return out


# BS.1770 loudness (K-weighting, 400 ms blocks, gated)
def lufs(x):
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = signal.lfilter(b2, a2, signal.lfilter(b1, a1, x, axis=0), axis=0)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([np.mean(np.sum(y[i:i + blk] ** 2, axis=1)) for i in range(0, max(1, len(y) - blk), hop)])
    if not len(ms):
        return -70.0
    l = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[l > -70]
    if not len(g):
        return -70.0
    rel = -0.691 + 10 * np.log10(np.mean(g)) - 10
    g = ms[(l > -70) & (l > rel)]
    return float(-0.691 + 10 * np.log10(np.mean(g)))


def limiter(x, ceiling_db=-1.0, look_ms=3.0, release_ms=120.0):
    """look-ahead peak limiter on 4x-oversampled peaks: the gain never lets a (true) peak over the ceiling"""
    c = 10 ** (ceiling_db / 20)
    up = signal.resample_poly(x, 4, 1, axis=0)
    pk = np.max(np.abs(up), axis=1).reshape(-1, 4).max(axis=1)[:len(x)]
    pk = np.pad(pk, (0, len(x) - len(pk)))
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    L = max(1, int(look_ms / 1000 * SR))
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    g = minimum_filter1d(need, size=2 * L + 1, mode='nearest')   # look-ahead: the gain is down before the peak
    g = _release(g, math.exp(-1.0 / (release_ms / 1000 * SR)))  # instant attack, exponential release (never above g)
    g = uniform_filter1d(g, size=L + 1, mode='nearest')          # smooth: still <= the needed gain at every sample
    y = x * g[:, None]
    return np.clip(y, -c, c), float(1 - g.min())


def _release(g, a):
    """y[n] = min(g[n], a*y[n-1] + (1-a)*g[n]); walks only the stretches where the gain is reduced"""
    out = g.copy()
    idx = np.flatnonzero(g < 0.999999)
    if not len(idx):
        return out
    n, i, y = len(g), int(idx[0]), 1.0
    gl = g.tolist()
    while i < n:
        if y >= 0.999999 and gl[i] >= 0.999999:
            k = np.searchsorted(idx, i)
            if k >= len(idx):
                break
            i, y = int(idx[k]), 1.0
            continue
        v = a * y + (1 - a) * gl[i]
        y = gl[i] if gl[i] < v else v
        out[i] = y
        i += 1
    return out


def mix(song, jobs, stems_dir=None):
    bpm = song.bpm
    active = [j for j in jobs if not j.track.mute]
    if any(j.track.solo for j in jobs):
        active = [j for j in jobs if j.track.solo]
    n = max([0] + [int(song.length_s * SR)])
    dry = np.zeros((n, 2)); eb = np.zeros((n, 2)); rb = np.zeros((n, 2))
    stats = []
    for j in active:
        x = load_flac(j.path)
        x = x[:n] if len(x) >= n else np.pad(x, ((0, n - len(x)), (0, 0)))
        x = x - np.mean(x, axis=0)   # the card's DC, if any
        t = j.track
        if t.hp > 0:
            x = signal.sosfilt(signal.butter(2, t.hp, 'hp', fs=SR, output='sos'), x, axis=0)
        if t.lp > 0:
            x = signal.sosfilt(signal.butter(2, t.lp, 'lp', fs=SR, output='sos'), x, axis=0)
        if t.width != 1.0:
            m, s = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2 * t.width
            x = np.stack([m + s, m - s], axis=1)
        gl, gr = pan_gains(t.pan)
        g = 10 ** (t.vol / 20)
        own = lufs(x)
        if t.lufs is not None and own > -69:   # brought to a loudness of its own (then vol on top)
            g *= 10 ** ((t.lufs - own) / 20)
        y = x * np.array([gl, gr]) * g
        dry += y
        if t.echo > 0:
            eb += y * t.echo
        if t.verb > 0:
            rb += y * t.verb
        stats.append({'track': t.name, 'peak_db': round(20 * math.log10(np.max(np.abs(x)) + 1e-12), 2), 'lufs': round(own, 1),
                      'gain_db': round(20 * math.log10(g), 1)})
        if stems_dir:
            write_wav24(os.path.join(stems_dir, f'{song.slug}.{t.name}.wav'), y * 0.5)
    out = dry
    if np.any(eb):
        e = conv(eb, echo_ir(song.sec['echo'], bpm))[:n]
        e = onepole_lp(e - onepole_lp(e, num(song.sec['echo'].get('lowcut'), 180)), 20000)
        out = out + e * 10 ** (num(song.sec['echo'].get('level'), 0) / 20)
    if np.any(rb):
        r = conv(rb, reverb_ir(song.sec['reverb']))[:n]
        r = r - onepole_lp(r, num(song.sec['reverb'].get('lowcut'), 150))
        out = out + r * 10 ** (num(song.sec['reverb'].get('level'), -6) / 20)
    out = signal.sosfilt(signal.butter(2, 25, 'hp', fs=SR, output='sos'), out, axis=0)
    # fades at the very ends (the song's own last notes ring out inside the tail)
    fo = int(num(song.sec['master'].get('fadeout'), 1.5) * SR)
    if fo > 0:
        out[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    target = num(song.sec['master'].get('loudness'), -16.0)
    ceiling = num(song.sec['master'].get('ceiling'), -1.0)
    pre = lufs(out)
    gain = 10 ** ((target - pre) / 20) * 10 ** (num(song.sec['master'].get('gain'), 0) / 20)
    y, red = limiter(out * gain, ceiling)
    post = lufs(y)
    if post < target - 0.3:   # the limiter took some: one more pass at the remaining gain
        y, red = limiter(out * gain * 10 ** ((target - post) / 20), ceiling)
        post = lufs(y)
    return y, {'tracks': stats, 'lufs_premaster': round(pre, 2), 'lufs': round(post, 2),
               'master_gain_db': round(20 * math.log10(gain), 2), 'limiter_max_reduction_db': round(-20 * math.log10(max(1e-6, 1 - red)), 2),
               'peak_dbfs': round(20 * math.log10(np.max(np.abs(y)) + 1e-12), 2)}


def encode(wav, base, meta):
    tags = []
    for k, v in (('title', meta.get('title', '')), ('artist', meta.get('artist', 'Algorithmic Industries (SNDWAVE2000)')),
                 ('album', meta.get('album', '')), ('comment', meta.get('comment', ''))):
        if v:
            tags += ['-metadata', f'{k}={v}']
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', wav, '-map_metadata', '-1', '-c:a', 'libopus', '-b:a', '64k',
                    '-vbr', 'on', '-compression_level', '10', '-application', 'audio', '-bitexact', '-fflags', '+bitexact',
                    '-flags:a', '+bitexact'] + tags + [base + '.ogg'], check=True)
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', wav, '-map_metadata', '-1', '-c:a', 'libmp3lame', '-b:a', '128k',
                    '-ar', '44100', '-bitexact', '-fflags', '+bitexact', '-flags:a', '+bitexact', '-id3v2_version', '3'] + tags + [base + '.mp3'], check=True)


# ------------------------------------------------------------------------------------------------- main
def finish_song(s, args):
    """mix one song from its cached stems, write and encode it, its report; returns the summary line"""
    os.nice(5)
    y, st = mix(s, s.jobs, args.out_dir if args.stems else None)
    base = os.path.join(args.out_dir, s.slug)
    write_wav24(base + '.wav', y)
    if not args.no_encode:
        encode(base + '.wav', base, {'title': s.meta['title'], 'album': s.meta.get('album', s.meta['pack']),
                                      'comment': s.meta.get('source', '')})
    rep = {'song': os.path.basename(s.path), 'title': s.meta['title'], 'pack': s.meta['pack'],
           'meta': s.meta, 'seconds': round(len(y) / SR, 2), 'bpm': s.bpm, 'engine': args.engine,
           'tracks': [{'name': j.track.name, 'source': j.track.src, 'preset': j.label, 'dna': j.dna, 'stem': j.key, 'render': j.log or 'cached',
                       'muted': j.track.mute} for j in s.jobs], 'mix': st}
    if not args.no_encode:
        for ext in ('wav', 'ogg', 'mp3'):
            h = hashlib.sha256(); file_sha(base + '.' + ext, h); rep[ext + '_sha256'] = h.hexdigest()
    if args.no_wav:
        os.remove(base + '.wav')
    with open(base + '.json', 'w') as f:
        json.dump(rep, f, indent=1)
    if args.drop_stems:
        for j in s.jobs:
            if os.path.exists(j.path) and j.key not in args.shared_keys:
                os.remove(j.path)
    return f'{s.slug}: {rep["seconds"]} s, {st["lufs"]} LUFS, peak {st["peak_dbfs"]} dBFS, limiter {st["limiter_max_reduction_db"]} dB'



def plan(song, args):
    smf = Smf.read(song.midi_path)
    song.bpm = float(song.meta.get('bpm', smf.first_tempo_bpm()))
    tail = float(song.meta.get('tail', 4))
    song.length_s = smf.seconds(smf.last_tick()) + tail
    eid = engine_id(args.render311, args.machine) if args.engine == 'render311' else 'host:' + args.plugin_id
    jobs = []
    tmpdir = tempfile.mkdtemp(prefix='songplan-')
    try:
        for t in song.tracks:
            dna, label = resolve(song, t, args.machine)
            ex = smf.extract(song.selector(t), t.tr, t.vel)
            if t.tune:   # cents, through the plugin's own pitch bend (the DNA's B range, 2 by default)
                m = re.search(r';[^;]*?B(\d+)', dna)
                rng = float(m.group(1)) if m else 2.0
                if abs(t.tune) > rng * 100:
                    raise SystemExit(f'{song.path}: track {t.name}: tune {t.tune:g} is past the bend range ({rng:g} semitones)')
                v = int(round(8192 + t.tune / (rng * 100) * 8191))
                ex.tracks[0].insert(0, [0, bytes([0xE0, v & 0x7F, v >> 7])])
            if ex.note_count() == 0:
                raise SystemExit(f'{song.path}: track {t.name} ({t.src}) has no notes in {song.meta["midi"]}')
            b = ex.to_bytes_for(os.path.join(tmpdir, 'x.mid'))
            la = getattr(args, 'lookahead', 0.0) if args.engine == 'render311' else 0.0
            key = hashlib.sha256(f'{eid}\n{dna}\n{tail:g}\n{song.bpm:.6f}\n'.encode() + (f'la{la:g}\n'.encode() if la else b'') + b).hexdigest()[:32]
            jobs.append(StemJob(song, t, dna, label, b, key, tail, song.bpm, args.cache, la))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return jobs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('songs', nargs='+')
    ap.add_argument('--out-dir', default=os.path.join(HOME, 'songs', 'out'))
    ap.add_argument('--render311', default=DEF_RENDER311)
    ap.add_argument('--machine', default=DEF_MACHINE)
    ap.add_argument('--cache', default=DEF_CACHE)
    ap.add_argument('--jobs', type=int, default=MAX_JOBS)
    ap.add_argument('--lookahead', type=float, default=150.0,
                    help='render311 --lookahead MS (dense chords arm on time; 0 for a render311 without it)')
    ap.add_argument('--stems', action='store_true', help='also write each track\'s mixed stem')
    ap.add_argument('--keep-wav', action='store_true', help='keep the master WAV (default: kept; --no-wav drops it)')
    ap.add_argument('--no-wav', action='store_true', help='delete the master WAV after encoding')
    ap.add_argument('--no-encode', action='store_true')
    ap.add_argument('--engine', choices=('render311', 'host'), default='render311',
                    help='host: each track through the real plugin in BasiliskHost (host_song.py)')
    ap.add_argument('--host', default='', help='--engine host: BasiliskHost.exe')
    ap.add_argument('--plugin', default='', help='--engine host: the plugin .vst3')
    ap.add_argument('--dry', action='store_true', help='resolve and print the plan only')
    ap.add_argument('--drop-stems', action='store_true', help='delete each song\'s cached stems once it is mixed')
    ap.add_argument('--cache-gb', type=float, default=1.5, help='stem cache limit (least recently used go first)')
    args = ap.parse_args()
    args.jobs = max(1, min(MAX_JOBS, args.jobs))
    args.render311 = os.path.abspath(args.render311); args.machine = os.path.abspath(args.machine)
    args.plugin_id = ''
    host_args = None
    if args.engine == 'host':
        import host_song
        host_args = host_song.HostArgs(args.host, args.plugin)
        args.plugin_id = host_args.ident()
        args.jobs = 1   # the host runs its own engines; one track at a time
    songs = [Song(p) for p in args.songs]
    alljobs = []
    for s in songs:
        s.jobs = plan(s, args)
        alljobs += s.jobs
        print(f'{s.slug}: {len(s.jobs)} tracks, {s.length_s:.1f} s at {s.bpm:.1f} bpm')
        if args.dry:
            for j in s.jobs:
                print(f'   {j.track.name:10s} {j.track.src:8s} {j.label}  {j.dna}')
    if args.dry:
        return
    os.makedirs(args.out_dir, exist_ok=True)
    t0 = time.time()
    # longest first: the pool stays full to the end
    todo = sorted({j.key: j for j in alljobs}.values(), key=lambda j: -j.song.length_s)
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        fut = {ex.submit(render_stem, j, args.render311, args.machine, args.engine, host_args): j for j in todo}
        for f in cf.as_completed(fut):
            j = fut[f]
            r = f.result()
            if r == 'rendered':
                print(f'   {j.song.slug}/{j.track.name}: {j.seconds:.1f} s   {j.log}', flush=True)
    print(f'stems: {time.time() - t0:.1f} s')
    from collections import Counter
    uses = Counter(j.key for s in songs for j in s.jobs)
    args.shared_keys = {k for k, n in uses.items() if n > 1}
    with cf.ProcessPoolExecutor(max_workers=min(4, len(songs))) as ex:   # mixing and encoding: a process per song
        for line in ex.map(finish_song, songs, [args] * len(songs)):
            print(line, flush=True)
    print(f'cache: {prune_cache(args.cache, args.cache_gb) / 1e9:.2f} GB')


if __name__ == '__main__':
    main()
