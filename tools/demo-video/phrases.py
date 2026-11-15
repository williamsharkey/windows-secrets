#!/usr/bin/env python3
"""MIDI phrases for the tour's captures: one progression (Fmaj7 Em7 Dm7 Cmaj7, the slow descending kind that
vaporwave is built on) played the way each kind of preset wants it. Every phrase is 8 seconds long.

    from phrases import phrase, write_smf
    write_smf('x.mid', [(t, note, vel, dur), ...])
"""
import struct

CHORDS = [  # (bass root, voicing)
    (41, [57, 60, 64, 69]),   # Fmaj7: F2 | A3 C4 E4 A4
    (40, [55, 59, 62, 67]),   # Em7:   E2 | G3 B3 D4 G4
    (38, [57, 60, 62, 65]),   # Dm7:   D2 | A3 C4 D4 F4
    (36, [55, 59, 64, 67]),   # Cmaj7: C2 | G3 B3 E4 G4
]
BAR = 2.0   # one chord every two seconds (a bar of 4/4 at 120, or two beats at 60: slow either way)


def phrase(kind, t0=0.0):
    """Notes (t, note, vel, dur) of an 8-second phrase starting at t0."""
    ev = []
    for i, (root, v) in enumerate(CHORDS):
        t = t0 + i * BAR
        if kind == 'chords':          # pads, strings: held chords
            ev += [(t, n, 88, BAR - 0.08) for n in v]
        elif kind == 'stabs':         # stabs, bells: two hits a bar
            ev += [(t + o, n, 96, 0.5) for o in (0, 1.0) for n in v]
        elif kind == 'bass':          # a bassline: root, octave, a pickup
            ev += [(t, root, 104, 0.6), (t + 0.75, root + 12, 92, 0.25), (t + 1.0, root, 100, 0.45),
                   (t + 1.5, root + 7, 90, 0.4)]
        elif kind == 'arp':           # keys, plucks: an arpeggio in eighths
            seq = v + [v[2], v[1]] + [v[3] + 12, v[3]]
            ev += [(t + k * 0.25, n, 86 + (8 if k % 4 == 0 else 0), 0.3) for k, n in enumerate(seq)]
        elif kind == 'keys':          # electric piano: chord on the beat, a top note answer
            ev += [(t, n, 90, 0.9) for n in v] + [(t + 1.25, v[-1] + 5 if i % 2 else v[-1] + 3, 84, 0.6)]
        elif kind == 'melody':        # bells, leads: a slow tune over the chords
            tune = [(0, 76, 1.0), (1.0, 74, 1.0)] if i % 2 == 0 else [(0, 72, 0.5), (0.5, 74, 0.5), (1.0, 69, 1.0)]
            ev += [(t + o, n, 92, d * 0.95) for o, n, d in tune] + [(t, v[0] - 12, 70, BAR - 0.1)]
        elif kind == 'fx':            # textures: two long notes
            if i in (0, 2):
                ev += [(t, 60 if i == 0 else 67, 96, 2 * BAR - 0.1)]
        elif kind == 'drums':         # General MIDI drum keys (as Kit Manager 98 maps its pads): a boom-bap bar
            pat = {36: 'x......x..x.....', 38: '....x.......x...', 42: 'x.x.x.x.x.x.x.x.', 46: '..............x.'}
            for n, p in pat.items():
                ev += [(t + k * BAR / 16, n, 110 if n == 36 else 92, 0.1) for k, c in enumerate(p) if c == 'x']
        elif kind == 'ding':          # Ding Piano for the cold open: block chords and a top line
            ev += [(t, n, 84, 1.4) for n in v] + [(t + 1.0, v[-1] + 2 if i < 3 else v[-1] + 5, 90, 0.9)]
        else:
            raise ValueError(kind)
    return ev


def _vlq(n):
    b = [n & 0x7F]
    n >>= 7
    while n:
        b.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(b))


def write_smf(path, notes, ppq=480, bpm=120.0):
    """A type 0 Standard MIDI File: notes (t seconds, note, velocity, duration seconds) on channel 1."""
    tick = lambda s: int(round(s * ppq * bpm / 60))
    evs = []
    for t, n, v, d in notes:
        evs.append((tick(t), 1, bytes([0x90, n, v])))
        evs.append((tick(t + d), 0, bytes([0x80, n, 0])))
    evs.sort(key=lambda e: (e[0], e[1]))
    tr = bytearray(b'\x00\xff\x51\x03' + struct.pack('>I', int(60e6 / bpm))[1:])
    last = 0
    for tk, _, m in evs:
        tr += _vlq(tk - last) + m
        last = tk
    tr += b'\x00\xff\x2f\x00'
    with open(path, 'wb') as f:
        f.write(b'MThd' + struct.pack('>IHHH', 6, 0, 1, ppq) + b'MTrk' + struct.pack('>I', len(tr)) + bytes(tr))
