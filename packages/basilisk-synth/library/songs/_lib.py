"""shared by the song scripts: the compose toolkit (tools/songrender/compose.py) and one call that writes a song's
.mid and .song beside its script"""
import json, os, re, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'songrender'))
from compose import *   # noqa: F401,F403,E402
import compose as _c   # noqa: E402


MAX_LOAD = 8   # recorders one instant may start on one engine: more and Windows arms some notes late (measured)


def cap_chords(S, tracks, pack):
    """thin each tuned track's chords so notes-at-once x recorders-per-note stays within MAX_LOAD: the top and
    bottom notes are kept first, then the inner ones from the top"""
    import songrender as _sr, voices as _v
    P = _sr.presets(_sr.DEF_MACHINE)
    bych = {p.ch: p for p in S.parts}
    for name, src, preset, kv in tracks:
        m = re.match(r'^ch(\d+)$', src)
        if not m or preset.startswith('dna:') or int(m.group(1)) not in bych:
            continue
        pk, nm = (preset.split(':', 1) if ':' in preset else (pack, preset))
        dna = P.get(pk, {}).get(nm)
        if not dna or re.search(r';.*?(?<![a-z])k\d', dna):   # kits keep every pad
            continue
        k = max(1, MAX_LOAD // _v.per_note(dna))
        part = bych[int(m.group(1))]
        groups = {}
        for n in part.notes:
            groups.setdefault(round(n[0] * 64), []).append(n)
        keep = []
        for g in groups.values():
            if len(g) <= k:
                keep += g; continue
            g = sorted(g, key=lambda n: n[1])
            order = [g[-1], g[0]] + g[-2:0:-1]
            keep += order[:k]
        part.notes = sorted(keep)


def finish(script, S, header, tracks, master=None, echo=None, reverb=None):
    base = os.path.splitext(os.path.abspath(script))[0]
    cap_chords(S, tracks, header['pack'])
    S.write(base + '.mid')
    header = dict(header)
    # the measured tuning of each preset (tuning.json, from tools/songrender/make_tuning.py), unless the song sets one
    tj = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tuning.json')
    tuning = json.load(open(tj)) if os.path.exists(tj) else {}
    fixed = []
    for name, src, preset, kv in tracks:
        if 'tune' not in kv and not preset.startswith('dna:'):
            key = preset if ':' in preset else header['pack'] + ':' + preset
            if key in tuning:
                kv['tune'] = tuning[key]
        fixed.append((name, src, preset, kv))
    tracks = fixed
    header['midi'] = os.path.basename(base) + '.mid'
    header.setdefault('script', os.path.basename(script))
    import songrender as _sr
    P = _sr.presets(_sr.DEF_MACHINE)
    pinned = {}
    for name, src, preset, kv in tracks:
        if preset.startswith('dna:'):
            continue
        pk, nm = preset.split(':', 1) if ':' in preset else (header['pack'], preset)
        if nm in P.get(pk, {}):
            pinned[f'{pk}:{nm}'] = P[pk][nm]
    _c.write_song(base + '.song', header, tracks, master, echo, reverb, pinned)
    print(base + '.song')


# General MIDI drum keys (Kit Manager 98 and the pack kits map their pads this way)
KICK, RIM, SNARE, CLAP, SNARE2, LTOM, CHH, LTOM2, PHH, MTOM, OHH, MTOM2, HTOM, CRASH, HTOM2, RIDE = \
    36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51

GROOVES = {   # 16 steps a bar (sixteenths); x hit, X accent, o ghost
    'house':    {KICK: 'x...x...x...x...', CLAP: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.', OHH: '..x...x...x...x.'},
    'house_lite': {KICK: 'x...x...x...x...', CHH: '..x...x...x...x.'},
    'techno':   {KICK: 'X...x...x...x...', CHH: '..x...x...x...x.', CLAP: '....x.......x...', RIM: '...x..x....x..x.'},
    'trance':   {KICK: 'X...x...x...x...', OHH: '..x...x...x...x.', CLAP: '....x.......x...', CHH: 'xxxxxxxxxxxxxxxx'},
    'breaks':   {KICK: 'x.........x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.xx', SNARE2: '.......o.o....o.'},
    'jungle':   {KICK: 'x.........x.....', SNARE: '....x..o.o..x...', CHH: 'x.xxx.x.x.xxx.x.', RIDE: 'x...x...x...x...'},
    'boombap':  {KICK: 'x......x..x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.'},
    '2step':    {KICK: 'x......x..x.....', SNARE: '....x.......x...', CHH: '..x...x...x.x.x.', RIM: '.o....o..o....o.'},
    'synthpop': {KICK: 'x.......x.x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.'},
    'disco':    {KICK: 'x...x...x...x...', SNARE: '....x.......x...', OHH: '..x...x...x...x.', CHH: 'x.x.x.x.x.x.x.x.'},
    'march':    {KICK: 'x.......x.......', SNARE: 'x.ox....x.oxo.o.', CRASH: 'x...............'},
    'halftime': {KICK: 'x.........x.....', SNARE: '........x.......', CHH: 'x.x.x.x.x.x.x.x.'},
}


def groove(part, name, at, bars, swing=0.0, vel=None, drop=(), extra=None, fill=False):
    """a groove from GROOVES for `bars` bars (4/4); drop: pads to leave out; extra: more pads; fill: the last bar
    ends with a snare/tom fill"""
    pads = {k: v for k, v in GROOVES[name].items() if k not in drop}
    if extra:
        pads.update(extra)
    if fill and bars > 0:
        if bars > 1:
            part.drums(pads, at=at, bars=bars - 1, swing=swing, vel=vel)
        last = at + 4 * (bars - 1)
        part.drums({k: v[:8] + '........' for k, v in pads.items() if k in (KICK, CHH, OHH)}, at=last, bars=1, swing=swing, vel=vel)
        part.drums({SNARE: '........x.xxxxXX'}, at=last, bars=1, vel=vel)
    else:
        part.drums(pads, at=at, bars=bars, swing=swing, vel=vel)
    return at + 4 * bars


def prog_len(prog, beats=4.0):
    t = 0.0
    for sym in prog.split():
        t += float(sym.split(':')[1]) if ':' in sym else beats
    return t


def hold(part, at, note, beats, vel=80, every=16.0):
    """a long held sound as notes of at most `every` beats, back to back (a sample may be shorter than the hold;
    the release covers the join)"""
    t, end = float(at), float(at) + beats
    while t < end - 1e-6:
        d = min(every, end - t)
        part.note(t, note, d, vel)
        t += d
    return end


# ---- arranging from a public-domain score's MIDI (the notes only: tempo, voicing and parts are the arrangement's)
from smf import Smf as _Smf   # noqa: E402

_TEMPLATES = {'': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10], 'maj7': [0, 4, 7, 11],
              'dim': [0, 3, 6], 'sus4': [0, 5, 7], 'aug': [0, 4, 8]}
_PCN = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


class Source:
    """a score's MIDI: notes per track in beats (quarter notes), its time signature"""
    def __init__(self, path):
        m = _Smf.read(path)
        self.path, self.div = path, m.division
        self.bar = 4.0
        for tr in m.tracks:
            for t, e in tr:
                if e[:2] == b'\xff\x58':
                    nn, dd = e[3], 2 ** e[4]
                    self.bar = nn * 4.0 / dd
                    break
        self.tracks = []
        for tr in m.tracks:
            on, notes = {}, []
            for t, e in sorted(tr, key=lambda x: x[0]):
                st = e[0] & 0xF0
                if st == 0x90 and e[2] > 0:
                    on.setdefault(e[1], []).append((t, e[2]))
                elif st == 0x80 or (st == 0x90 and e[2] == 0):
                    if on.get(e[1]):
                        t0, v = on[e[1]].pop(0)
                        notes.append((t0 / self.div, e[1], (t - t0) / self.div, v))
            if notes:
                self.tracks.append(sorted(notes))
        self.all = sorted(n for tr in self.tracks for n in tr)

    def bars(self):
        return int(max(b + d for b, p, d, v in self.all) // self.bar) + 1

    def span(self, notes, bar0, bar1, shift_to=0.0):
        """the notes starting in bars [bar0, bar1) (0-based), moved to start at shift_to"""
        a, b = bar0 * self.bar, bar1 * self.bar
        return [(x - a + shift_to, p, min(d, b - x), v) for x, p, d, v in notes if a <= x < b - 1e-6]


def skyline(notes, min_gap=0.05):
    """the top voice: at each onset the highest note (a melody from a piano part)"""
    by = {}
    for b, p, d, v in notes:
        k = round(b, 3)
        if k not in by or p > by[k][1]:
            by[k] = (b, p, d, v)
    out = sorted(by.values())
    res = []
    for i, (b, p, d, v) in enumerate(out):
        nxt = out[i + 1][0] if i + 1 < len(out) else b + d
        res.append((b, p, max(min_gap, min(d, nxt - b)), v))
    return res


def floor(notes):
    """the lowest voice: at each onset the lowest note"""
    by = {}
    for b, p, d, v in notes:
        k = round(b, 3)
        if k not in by or p < by[k][1]:
            by[k] = (b, p, d, v)
    return sorted(by.values())


def chords_of(notes, start, end, step):
    """a chord symbol for each `step` beats from the notes sounding (duration-weighted pitch classes)"""
    out, t = [], start
    while t < end - 1e-6:
        w = [0.0] * 12
        lo = None
        for b, p, d, v in notes:
            ov = min(b + d, t + step) - max(b, t)
            if ov > 0:
                w[p % 12] += ov
                if lo is None or p < lo[0]:
                    lo = (p, ov)
        best, bs = None, -1e9
        for r in range(12):
            for q, iv in _TEMPLATES.items():
                s = sum(w[(r + i) % 12] for i in iv) - 0.6 * sum(w[k] for k in range(12) if (k - r) % 12 not in iv)
                s += 0.3 * (lo is not None and lo[0] % 12 == r) * max(w)
                if len(iv) == 4:
                    s -= 0.15 * max(w)
                if s > bs:
                    best, bs = _PCN[r] + q, s
        out.append(best if sum(w) > 0 else (out[-1] if out else 'C'))
        t += step
    return out


def put(part, notes, tr=0, vel=None, vscale=1.0, gate=1.0, lo=None, hi=None):
    """place source notes (beats) on a part, octave-folded into lo..hi when given"""
    for b, p, d, v in notes:
        n = p + tr
        if lo is not None:
            while n < lo:
                n += 12
        if hi is not None:
            while n > hi:
                n -= 12
        part.note(b, n, d * gate, vel if vel is not None else int(v * vscale))


_MAJ = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MIN = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def key_of(notes):
    """Krumhansl-Schmuckler key: (tonic pitch class, 'major'|'minor')"""
    w = [0.0] * 12
    for b, p, d, v in notes:
        w[p % 12] += d
    best = None
    for r in range(12):
        for mode, prof in (('major', _MAJ), ('minor', _MIN)):
            a = [w[(r + i) % 12] for i in range(12)]
            ma, mb = sum(a) / 12, sum(prof) / 12
            c = sum((x - ma) * (y - mb) for x, y in zip(a, prof))
            if best is None or c > best[0]:
                best = (c, r, mode)
    return best[1], best[2]


def cadences(src, tonic):
    """bars (0-based) whose downbeat has the tonic in the bass and a melody note of a beat or more: phrase ends"""
    out = []
    lows, tops = floor(src.all), skyline(src.all)
    for k in range(1, src.bars()):
        t = k * src.bar
        bl = [p for b, p, d, v in lows if abs(b - t) < 0.02]
        tp = [d for b, p, d, v in tops if abs(b - t) < 0.02]
        if bl and bl[0] % 12 == tonic and tp and tp[0] >= min(1.0, src.bar * 0.5):
            out.append(k)
    return out


def beats(notes, a, b, at=0.0):
    """the notes starting in source beats [a, b), moved so that a lands on `at`, cut at b"""
    return [(x - a + at, p, max(0.05, min(d, b - x)), v) for x, p, d, v in notes if a - 1e-6 <= x < b - 1e-6]


def arrange(src, a, b, at, lead=None, inner=None, lh=None, bass=None, pad=None, rh_track=0, lh_track=1,
            lead_range=(60, 84), inner_range=(52, 76), lh_range=(40, 64), bass_range=(28, 52), pad_range=(52, 70),
            pad_step=None, vel=None, lead_vel=None, tr=0, gate=1.0):
    """a stretch of a piano score onto parts: lead = the right hand's top voice, inner = the rest of the right hand,
    lh = the left hand, bass = the left hand's lowest voice, pad = a held chord per pad_step beats (default a bar)"""
    rh = beats(src.tracks[rh_track], a, b, at)
    lhn = beats(src.tracks[lh_track], a, b, at) if lh_track is not None and lh_track < len(src.tracks) else []
    top = skyline(rh)
    tops = {(round(x, 3), p) for x, p, d, v in top}
    if lead:
        put(lead, top, tr, lead_vel, lo=lead_range[0], hi=lead_range[1], gate=gate)
    if inner:
        put(inner, [n for n in rh if (round(n[0], 3), n[1]) not in tops], tr, vel, lo=inner_range[0], hi=inner_range[1], gate=gate)
    if lh:
        put(lh, lhn, tr, vel, lo=lh_range[0], hi=lh_range[1], gate=gate)
    if bass:
        put(bass, floor(lhn or rh), tr, vel, lo=bass_range[0], hi=bass_range[1], gate=gate)
    if pad:
        step = pad_step or src.bar
        syms = chords_of(rh + lhn, at, at + (b - a), step)
        prev = None
        for i, s in enumerate(syms):
            ns = voice_lead(prev, [n + tr for n in chord(s, 4)], pad_range[0], pad_range[1]); prev = ns
            for n in ns:
                pad.note(at + i * step, n, step * 0.98, 60 if vel is None else vel)
    return at + (b - a)


# ---- re-voicing a CC0 module (tools/songrender/trackers.py made the notes MIDI; one track per instrument)
def module_tracks(path, bpm):
    """[(track name, [(beat, pitch, dur, vel)])] at `bpm` (the notes MIDI runs at 120 bpm: a beat there is 0.5 s)"""
    m = _Smf.read(path)
    k = bpm / 120.0
    out = []
    for tr in m.tracks:
        name = ''
        on, notes = {}, []
        for t, e in sorted(tr, key=lambda x: x[0]):
            if e[:2] == b'\xff\x03':
                name = e[3:3 + e[2]].decode('latin-1')
            st = e[0] & 0xF0
            if st == 0x90 and e[2] > 0:
                on.setdefault(e[1], []).append((t, e[2]))
            elif st == 0x80 or (st == 0x90 and e[2] == 0):
                if on.get(e[1]):
                    t0, v = on[e[1]].pop(0)
                    notes.append((t0 / m.division * k, e[1], (t - t0) / m.division * k, v))
        if notes:
            if not name.startswith(('ins ', 'chan ')):
                name = f'ins {len(out) + 1} {name}'.strip()   # a plain MIDI file: its tracks in order
            out.append((name, sorted(notes)))
    return out


def module_song(script, src_name, bpm, plan, header, tracks, master=None, echo=None, reverb=None, cut=None,
                loops=1, intro=0.0, seed=1, stretch=1.0):
    """plan: {instrument number: (part name, ch, tr, lo, hi, vel_scale)} for tuned parts, or
    {instrument number: (part name, ch, 'pad', GM note, vel_scale)} for a percussion instrument onto one kit pad, or
    {instrument number: (part name, ch, 'split', [(highest source pitch, pad), ...], vel_scale)} across pads.
    cut: stop at this beat (a fade covers it); loops: play the module this many times (a short game loop);
    stretch: 2.0 plays it at half speed (the beat grid stays at `bpm`)."""
    here = os.path.dirname(os.path.abspath(script))
    path = os.path.join(here, '..', 'sources', 'cc0', src_name)
    mt = [(n, [(b * stretch, p, d * stretch, v) for b, p, d, v in ns]) for n, ns in module_tracks(path, bpm)]
    S = Score(bpm=bpm, seed=seed)
    parts = {}
    length = max(b + d for _, ns in mt for b, p, d, v in ns)
    for name, notes in mt:
        num = int(name.split()[1]) if name.startswith(('ins ', 'chan ')) else None
        if num not in plan:
            continue
        spec = plan[num]
        pname, ch = spec[0], spec[1]
        if pname not in parts:
            parts[pname] = S.part(pname, ch)
        part = parts[pname]
        for L in range(loops):
            off = intro + L * length
            for b, p, d, v in notes:
                b2 = b + off
                if cut is not None and b2 >= cut:
                    continue
                if cut is not None:
                    d = min(d, cut - b2)
                if spec[2] == 'pad':
                    part.note(b2, spec[3], min(d, 0.25), int(max(1, min(127, v * spec[4]))))
                elif spec[2] == 'split':   # [(highest source pitch, pad), ...]: one noise channel onto several pads
                    pad = next((pd for hi_, pd in spec[3] if p <= hi_), spec[3][-1][1])
                    part.note(b2, pad, min(d, 0.25), int(max(1, min(127, v * spec[4]))))
                else:
                    tr, lo, hi, vs = spec[2], spec[3], spec[4], spec[5]
                    n = p + tr
                    while n < lo:
                        n += 12
                    while n > hi:
                        n -= 12
                    part.note(b2, n, d, int(max(1, min(127, v * vs))))
    finish(script, S, header, tracks, master, echo, reverb)
    return S
