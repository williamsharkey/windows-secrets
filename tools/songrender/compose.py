"""compose: a small toolkit for writing the song demos' MIDI in Python (used by library/songs/*/*.py).

    S = Score(bpm=100)
    lead = S.part('lead', ch=1)
    lead.mel('q C5 D5 e E5 F5 | h G5 r', at=0)          # durations: w h q e s (+ '.' dotted, 't' triplet), r rest,
                                                         # ~ ties to the previous note, C4+E4+G4 a chord, !C5 accent,
                                                         # ?C5 soft, C5/1.5 an explicit length in beats, C5* staccato, > octave up, < down
    S.part('pad', ch=2).chords('Am F C G', at=0, beats=4, style='pad')
    S.part('drums', ch=10).drums({36: 'x...x...', 38: '....x...'}, at=0, bars=4)
    S.write('song.mid')

Times are in beats (quarter notes) from the start. All randomness (humanize) is seeded, so a script always writes
the same file.
"""
import os, random, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smf import Smf   # noqa: E402

NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
QUAL = {
    '': [0, 4, 7], 'maj': [0, 4, 7], 'm': [0, 3, 7], 'min': [0, 3, 7], '7': [0, 4, 7, 10], 'maj7': [0, 4, 7, 11],
    'M7': [0, 4, 7, 11], 'm7': [0, 3, 7, 10], 'dim': [0, 3, 6], 'dim7': [0, 3, 6, 9], 'm7b5': [0, 3, 6, 10],
    'aug': [0, 4, 8], '+': [0, 4, 8], 'sus2': [0, 2, 7], 'sus4': [0, 5, 7], 'sus': [0, 5, 7], '6': [0, 4, 7, 9],
    'm6': [0, 3, 7, 9], 'add9': [0, 4, 7, 14], 'madd9': [0, 3, 7, 14], '9': [0, 4, 7, 10, 14], 'm9': [0, 3, 7, 10, 14],
    'maj9': [0, 4, 7, 11, 14], '5': [0, 7], '7sus4': [0, 5, 7, 10], 'm11': [0, 3, 7, 10, 17], '13': [0, 4, 10, 21],
}
DUR = {'w': 4.0, 'h': 2.0, 'q': 1.0, 'e': 0.5, 's': 0.25, 'z': 0.125}


def pitch(name):
    """'C4' -> 60, 'F#3', 'Bb5', or a number"""
    if isinstance(name, int):
        return name
    m = re.match(r'^([A-G])([#b]*)(-?\d+)$', name)
    if not m:
        raise ValueError(f'bad note {name!r}')
    return 12 * (int(m.group(3)) + 1) + NAMES[m.group(1)] + m.group(2).count('#') - m.group(2).count('b')


def chord(sym, octave=4):
    """'Am7' -> pitches from the root in the given octave; 'C/G' puts G under it"""
    bass = None
    if '/' in sym:
        sym, b = sym.split('/')
        bass = b
    m = re.match(r'^([A-G][#b]?)(.*)$', sym)
    root = pitch(m.group(1) + str(octave))
    q = m.group(2)
    if q not in QUAL:
        raise ValueError(f'bad chord quality {sym!r}')
    ns = [root + i for i in QUAL[q]]
    if bass:
        bp = pitch(bass + str(octave - 1))
        while bp >= ns[0]:
            bp -= 12
        ns = [bp] + ns
    return ns


def root_of(sym, octave=2):
    sym = sym.split('/')[1] if '/' in sym else sym
    m = re.match(r'^([A-G][#b]?)', sym)
    return pitch(m.group(1) + str(octave))


def voice_lead(prev, ns, lo=52, hi=72):
    """a voicing of chord ns (pitch classes) close to prev, within lo..hi"""
    pcs = sorted(set(n % 12 for n in ns))
    if not prev:
        base = [n for n in ns]
        while min(base) < lo:
            base = [n + 12 for n in base]
        while max(base) > hi + 5:
            base = [n - 12 for n in base]
        return sorted(base)
    c = sum(prev) / len(prev)
    out = []
    for pc in pcs:
        cands = [pc + 12 * k for k in range(2, 9) if lo <= pc + 12 * k <= hi]
        if not cands:
            cands = [pc + 12 * k for k in range(2, 9)]
        out.append(min(cands, key=lambda n: abs(n - c)))
    return sorted(set(out))


class Part:
    def __init__(self, score, name, ch):
        self.score, self.name, self.ch = score, name, ch
        self.notes = []          # (beat, pitch, dur, vel)
        self.ccs = []            # (beat, cc, value) / ('bend', value)
        self.oct = 0

    def note(self, at, p, dur, vel=90):
        p = pitch(p) if isinstance(p, str) else p
        if 0 <= p <= 127 and dur > 0:
            self.notes.append((float(at), int(p), float(dur), int(max(1, min(127, vel)))))
        return at + dur

    def mel(self, text, at=0.0, vel=90, gate=0.92, tr=0, step=None):
        """the melody notation (module doc); returns the beat after the last token"""
        t, d = float(at), step or 1.0
        last = None
        for tok in text.replace('|', ' ').split():
            m = re.match(r'^([whqesz])(\.?)(t?)$', tok)
            if m:
                d = DUR[m.group(1)] * (1.5 if m.group(2) else 1) * (2 / 3 if m.group(3) else 1)
                continue
            if tok in ('>', '<'):
                tr += 12 if tok == '>' else -12; continue
            if tok == '~':
                if last:
                    for i in last:
                        b, p, du, v = self.notes[i]
                        self.notes[i] = (b, p, du + d, v)
                t += d; continue
            mm = re.match(r'^([!?]?)([A-Gr][#b]*-?\d*(?:\+[A-G][#b]*-?\d+)*)(?:/([\d.]+))?(\*?)$', tok)
            if not mm:
                raise ValueError(f'{self.name}: bad token {tok!r}')
            acc, body, ln, stac = mm.groups()
            dd = float(ln) if ln else d
            v = vel + (18 if acc == '!' else -22 if acc == '?' else 0)
            g = 0.5 if stac else gate
            if body == 'r':
                last = None
            else:
                ps = body.split('+')
                last = []
                for p in ps:
                    last.append(len(self.notes))
                    self.note(t, pitch(p) + tr, dd * g, v)
            t += dd
        return t

    def chords(self, prog, at=0.0, beats=4.0, style='pad', vel=72, lo=52, hi=72, octave=4, rhythm=None, gate=0.98):
        """chord symbols, one per `beats` (or 'Am:2' for its own length); styles: pad (held), block (rhythm hits),
        arp (up), arpud (up-down), broken (root then the rest); rhythm: offsets in beats within each chord"""
        t, prev = float(at), None
        for sym in prog.split():
            b = beats
            if ':' in sym:
                sym, b = sym.split(':'); b = float(b)
            if sym in ('-', 'r', 'N.C.'):
                t += b; continue
            ns = voice_lead(prev, chord(sym, octave), lo, hi); prev = ns
            if style == 'pad':
                for n in ns:
                    self.note(t, n, b * gate, vel)
            elif style == 'block':
                for off, du in (rhythm or [(0, 0.9), (1.5, 0.4), (2, 0.9), (3.5, 0.4)]):
                    if off < b:
                        for n in ns:
                            self.note(t + off, n, min(du, b - off), vel)
            elif style in ('arp', 'arpud', 'broken'):
                st = rhythm or 0.5
                seq = ns + [ns[0] + 12] if style == 'arp' else ns + [ns[0] + 12] + ns[-1:0:-1] if style == 'arpud' else ns
                k = 0
                while k * st < b - 1e-6:
                    self.note(t + k * st, seq[k % len(seq)], st * 1.6, vel - (0 if k % 2 == 0 else 8))
                    k += 1
            t += b
        return t

    def bass(self, prog, at=0.0, beats=4.0, pattern=None, vel=96, octave=2):
        """a bass line: pattern = [(offset, interval-or-'5'/'8', length)] per chord; default root on 1 and 3"""
        pattern = pattern or [(0, 0, 1.8), (2, 0, 1.8)]
        t = float(at)
        for sym in prog.split():
            b = beats
            if ':' in sym:
                sym, b = sym.split(':'); b = float(b)
            if sym in ('-', 'r'):
                t += b; continue
            r = root_of(sym, octave)
            cq = chord(sym.split('/')[0], octave)
            third = cq[1] - cq[0]
            for off, iv, du in pattern:
                if off >= b:
                    continue
                iv = {'5': 7, '8': 12, '3': third, '-1': -1, '7': 10, '6': 9}.get(str(iv), iv)
                self.note(t + off, r + iv, min(du, b - off), vel - (0 if off == 0 else 10))
            t += b
        return t

    def drums(self, pads, at=0.0, bars=1, step=0.25, beats_per_bar=4, vel=None, swing=0.0):
        """pads: {note: 'x.o.X...'}; x normal, X accent, o ghost, . rest; repeats for `bars` bars"""
        vel = vel or {'x': 96, 'X': 118, 'o': 58, 'g': 40}
        steps = int(round(beats_per_bar / step))
        for n, pat in pads.items():
            pat = pat.replace(' ', '').replace('|', '')
            for k in range(bars * steps):   # a pattern longer than a bar runs on over the next bars
                c = pat[k % len(pat)]
                if c in vel:
                    b = at + k * step + (swing * step if k % 2 else 0)
                    self.note(b, n, step * 0.9, vel[c])
        return at + bars * beats_per_bar

    def cc(self, at, num, val):
        self.ccs.append((float(at), num, val))

    def bend(self, at, val):
        """val -1..1 of the bend range"""
        self.ccs.append((float(at), 'bend', val))

    def end(self):
        return max([b + d for b, p, d, v in self.notes] + [0])


class Score:
    def __init__(self, bpm=120, ppq=480, seed=1):
        self.ppq = ppq
        self.tempos = [(0.0, bpm)]
        self.parts = []
        self.rng = random.Random(seed)

    def tempo(self, at, bpm):
        self.tempos.append((float(at), bpm))

    def part(self, name, ch):
        p = Part(self, name, ch)
        self.parts.append(p)
        return p

    def humanize(self, ms=6, vel=6, parts=None):
        """deterministic small timing and velocity changes (a beat is 60/bpm s at the first tempo)"""
        spb = 60.0 / self.tempos[0][1]
        for p in self.parts:
            if parts and p.name not in parts:
                continue
            out = []
            for b, n, d, v in p.notes:
                dt = self.rng.uniform(-ms, ms) / 1000.0 / spb
                out.append((max(0.0, b + dt), n, d, int(max(1, min(127, v + self.rng.randint(-vel, vel))))))
            p.notes = out

    def end(self):
        return max([p.end() for p in self.parts] + [0])

    def write(self, path):
        m = Smf(self.ppq)
        tr0 = []
        for b, bpm in sorted(self.tempos):
            us = int(round(60e6 / bpm))
            tr0.append([int(round(b * self.ppq)), b'\xff\x51\x03' + us.to_bytes(3, 'big')])
        tr0.append([0, b'\xff\x58\x04\x04\x02\x18\x08'])
        m.tracks.append(tr0)
        for p in self.parts:
            ch = (p.ch - 1) & 15
            evs = [[0, b'\xff\x03' + bytes([len(p.name)]) + p.name.encode()]]
            offs, ons = [], []
            for b, n, d, v in p.notes:
                t0 = int(round(b * self.ppq)); t1 = max(t0 + 1, int(round((b + d) * self.ppq)))
                ons.append([t0, bytes([0x90 | ch, n, v])])
                offs.append([t1, bytes([0x80 | ch, n, 0])])
            for b, k, v in p.ccs:
                t = int(round(b * self.ppq))
                if k == 'bend':
                    x = int(max(0, min(16383, round(8192 + v * 8191))))
                    evs.append([t, bytes([0xE0 | ch, x & 0x7F, x >> 7])])
                else:
                    evs.append([t, bytes([0xB0 | ch, k, int(v)])])
            # at one tick, note-offs come before note-ons (a repeated note is retriggered, not cut)
            allev = sorted(evs + offs + ons, key=lambda e: (e[0], 0 if e[1][0] == 0xFF else 1 if e[1][0] & 0xF0 == 0x80 else 2 if e[1][0] & 0xF0 != 0x90 else 3))
            m.tracks.append(allev)
        m.write(path)
        return path


def write_song(path, header, tracks, master=None, echo=None, reverb=None, pinned=None):
    """the .song file: header {key: value}, tracks [(name, source, preset, {key: value})]"""
    L = [f'# {header.get("title", "")}: a SNDWAVE1993 song demo (tools/songrender/README.md has the format)', '']
    for k, v in header.items():
        for line in str(v).split('\n'):
            L.append(f'{k:9s}= {line}')
    for sec, d in (('master', master), ('echo', echo), ('reverb', reverb)):
        if d:
            L += ['', f'[{sec}]'] + [f'{k:9s}= {v}' for k, v in d.items()]
    L += ['', '[tracks]', '# name      source  preset                                  mix']
    for name, src, preset, kv in tracks:
        p = f'"{preset}"' if not preset.startswith('dna:') else f"'{preset}'"
        mixs = ' '.join(k if v is True else f'{k}={v:g}' if isinstance(v, (int, float)) else f'{k}={v}' for k, v in kv.items())
        L.append(f'{name:11s} {src:7s} {p:40s} {mixs}')
    if pinned:
        L += ['', '[dna]', '# the presets\' DNA when this song was written (used before the pack discs\' own)']
        L += [f'"{k}" = {v}' for k, v in sorted(pinned.items())]
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L) + '\n')
