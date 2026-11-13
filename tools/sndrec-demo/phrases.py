#!/usr/bin/env python3
"""Demo phrases for the sndrec.html preset browser: one short, typical MIDI phrase per factory preset.

    phrases.py PRESETS.H OUT_DIR [--edition b16|xp]

PRESETS.H is a plugin's generated program list (packages/basilisk-synth-311/plugin/presets_gen.h for BASILISK 16,
packages/basilisk-synth/plugin/presets_gen.h for BASILISK SYNTH): {"Category: Name", "DNA"} rows.
Writes OUT_DIR/mid/<slug>.mid (format 0, 960 ticks per second), OUT_DIR/jobs.json (the batch renderers' job list:
dna, midi, out, tail) and OUT_DIR/presets.json (index, category, name, DNA, phrase kind, slug).

Everything is deterministic (no randomness): the same list gives the same MIDI bytes, so demos can be re-rendered.
The phrase follows the sound's job: pads get slow chords, basses a bassline, keys a progression with a melody,
plucks an arpeggio, bells a melody, leads a lead line, FX and drones held notes, percussion a groove, collages
spaced held notes, macro presets pulsing chords (the macro move itself is in the demo videos).
"""
import json, os, re, struct, sys

TPS = 960   # ticks per second: 480 ppq at 120 bpm


# ------------------------------------------------------------------ phrases: lists of (t, note, vel, dur) in seconds
def pad():
    chords = [(48, 55, 60, 64), (45, 52, 57, 60), (41, 48, 53, 57), (43, 50, 55, 59)]
    out = []
    for i, ch in enumerate(chords):
        for k, n in enumerate(ch):
            out.append((i * 2.3, n, 84 - 4 * k, 2.25))
    return out, 2.0


def keys():
    prog = [(48, 55, 64), (45, 52, 60), (41, 48, 57), (43, 50, 59)]
    mel = [(0.0, 72, 1), (0.45, 74, 1), (0.9, 76, 2), (1.8, 76, 1), (2.25, 74, 1), (2.7, 72, 2),
           (3.6, 69, 1), (4.05, 72, 1), (4.5, 77, 2), (5.4, 76, 1), (5.85, 74, 1), (6.3, 71, 1), (6.75, 74, 2)]
    out = []
    for i, ch in enumerate(prog):
        for n in ch:
            out.append((i * 1.8, n, 72, 1.7))
        out.append((i * 1.8 + 0.9, ch[0], 62, 0.8))
    for t, n, l in mel:
        out.append((t, n, 96 if l == 2 else 88, 0.43 * l))
    return out, 1.5


def melody(base=0):
    # bells and mallets: a bright pentatonic tune
    seq = [(0.0, 72, 0.5), (0.5, 76, 0.5), (1.0, 79, 0.5), (1.5, 84, 1.0), (2.5, 81, 0.5), (3.0, 79, 0.5),
           (3.5, 76, 1.0), (4.5, 74, 0.5), (5.0, 76, 0.5), (5.5, 72, 1.5)]
    return [(t, n + base, 100 - (i % 3) * 8, d) for i, (t, n, d) in enumerate(seq)], 2.0


def mono_melody():
    # sounds that stack their own harmony (H) or many unison voices: single notes only
    seq = [(0.0, 60, 0.55), (0.6, 64, 0.55), (1.2, 67, 0.55), (1.8, 65, 1.1), (3.0, 64, 0.55), (3.6, 62, 0.55),
           (4.2, 60, 1.1), (5.4, 62, 0.55), (6.0, 64, 0.55), (6.6, 60, 1.4)]
    return [(t, n, 96 - (i % 2) * 10, d) for i, (t, n, d) in enumerate(seq)], 1.5


def arp():
    chords = [(57, 60, 64, 69), (53, 57, 60, 65), (48, 55, 60, 64), (55, 59, 62, 67)]
    pat = [0, 1, 2, 3, 2, 1, 2, 3]
    out, step, t = [], 0.17, 0.0
    for ch in chords:
        for k, p in enumerate(pat):
            out.append((round(t, 3), ch[p], 104 if k == 0 else 80 + (k % 2) * 8, step * 0.9))
            t += step
    return out, 1.5


def bass():
    line = [45, 45, 57, 45, 43, 43, 55, 43, 41, 41, 53, 41, 43, 43, 47, 50]
    step = 0.36
    return [(round(i * step, 3), n, 110 if i % 4 == 0 else 92, step * (0.9 if i % 4 != 3 else 0.6)) for i, n in enumerate(line)], 1.2


def lead():
    seq = [(0.0, 69, 0.4), (0.45, 72, 0.4), (0.9, 74, 0.9), (1.8, 76, 0.4), (2.25, 74, 0.4), (2.7, 72, 1.3),
           (4.2, 67, 0.4), (4.65, 69, 0.4), (5.1, 72, 0.9), (6.0, 71, 0.4), (6.45, 67, 0.4), (6.9, 69, 1.6)]
    return [(t, n, 100 if d > 0.5 else 90, d) for t, n, d in seq], 1.5


def fx():
    return [(0.0, 60, 100, 4.5), (5.0, 67, 92, 3.0)], 2.0


def drone():
    return [(0.0, 48, 100, 5.0), (0.0, 55, 80, 5.0), (5.4, 53, 96, 3.0)], 2.2


def collage():
    return [(0.0, 60, 100, 2.8), (3.1, 55, 96, 2.8), (6.2, 64, 100, 2.4)], 1.8


def perc():
    # a two-bar groove at 100 bpm in eighth notes, played twice; F (fixed pitch) layers ignore the note, others follow it
    hits = [(0, 48, 120), (2, 60, 100), (3, 48, 70), (4, 55, 110), (6, 60, 96), (7, 64, 76),
            (8, 48, 120), (9, 48, 84), (10, 60, 100), (12, 55, 112), (13, 64, 80), (14, 60, 100), (15, 67, 90)]
    out, step = [], 0.3
    for bar in range(2):
        for s, n, v in hits:
            out.append((round((bar * 16 + s) * step, 3), n, v, 0.14))
    return sorted(out), 1.0


def macro():
    # pulsing chords: two per bar, as you would ride a macro or the mod wheel over
    prog = [(48, 55, 64), (45, 52, 60), (41, 48, 57), (43, 50, 59)]
    out = []
    for i, ch in enumerate(prog):
        for r in range(2):
            for n in ch:
                out.append((round(i * 2.0 + r * 1.0, 3), n, 96 if r == 0 else 80, 0.9))
    return out, 1.8


KINDS = {'pad': pad, 'keys': keys, 'melody': melody, 'mono': mono_melody, 'arp': arp, 'bass': bass, 'lead': lead,
         'fx': fx, 'drone': drone, 'collage': collage, 'perc': perc, 'macro': macro}
LABEL = {'pad': 'slow chords', 'keys': 'chords and melody', 'melody': 'melody', 'mono': 'melody (single notes)',
         'arp': 'arpeggio', 'bass': 'bassline', 'lead': 'lead line', 'fx': 'held notes', 'drone': 'held drone',
         'collage': 'spaced held notes', 'perc': 'groove', 'macro': 'pulsing chords'}

# per-preset choices where the category alone would be wrong (by name)
BY_NAME = {
    'Ding Piano': 'keys', 'Chime Octaves': 'melody', 'Telephone Choir': 'pad', 'Reverse Ding Swell': 'pad',
    'Echo Bells': 'melody', 'Slow Ring Pad': 'pad', 'Fifth Stack': 'mono', 'Major Ding': 'mono',
    'Ding and Chimes': 'melody', 'Chopped Ring': 'arp', 'Insert and Mix': 'fx', 'Triple Echo Reverse': 'fx',
    'Bass Ding': 'bass', 'Detuned Unison': 'lead', 'Ring Out Octaves': 'mono', 'Copy Paste Stutter': 'arp',
    'Glass Piano': 'keys', 'Bowl Swell': 'pad', 'Marimba Echo': 'melody', 'Vibe Wide': 'keys', 'Harp Stereo': 'arp',
    'Upright Piano': 'keys', 'Kalimba Glass': 'arp', 'Choir Pad': 'pad', 'Singing Bowl': 'drone',
    'Thunder Thrush': 'fx', 'Balloon Keys': 'mono', 'Ding Bells': 'melody', 'Shutdown Drone': 'drone',
    'Wind Sweep': 'fx',
}
BY_CAT = {'pads': 'pad', 'bass': 'bass', 'keys': 'keys', 'bells': 'melody', 'plucks': 'arp', 'percussion': 'perc',
          'collage': 'collage', 'fx': 'fx', 'macro': 'macro', 'layers': 'keys', 'leads': 'lead', 'lead': 'lead',
          'arps': 'arp', 'drones': 'drone', 'textures': 'fx', 'brass': 'lead', 'strings': 'pad', 'organ': 'keys'}


def kind_of(cat, name, dna):
    if name in BY_NAME: return BY_NAME[name]
    c = cat.lower().replace('b16 ', '').strip()
    for k, v in BY_CAT.items():
        if c.startswith(k): return v
    return 'keys'


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


# ------------------------------------------------------------------ Standard MIDI File, format 0
def vlq(n):
    b = [n & 0x7F]; n >>= 7
    while n: b.append(0x80 | (n & 0x7F)); n >>= 7
    return bytes(reversed(b))


def write_mid(path, notes):
    ev = []
    for t, n, v, d in notes:
        ev.append((round(t * TPS), 1, bytes([0x90, n, v])))
        ev.append((round((t + d) * TPS), 0, bytes([0x80, n, 0])))
    ev.sort(key=lambda e: (e[0], e[1], e[2][1]))   # at the same tick: offs before ons
    trk, last = bytearray(vlq(0) + b'\xff\x51\x03' + (500000).to_bytes(3, 'big')), 0
    for tick, _, msg in ev:
        trk += vlq(tick - last) + msg; last = tick
    trk += vlq(0) + b'\xff\x2f\x00'
    with open(path, 'wb') as f:
        f.write(b'MThd' + struct.pack('>IHHH', 6, 0, 1, 480) + b'MTrk' + struct.pack('>I', len(trk)) + trk)


def read_presets(h):
    return re.findall(r'\{"((?:[^"\\]|\\.)*)",\s*"((?:[^"\\]|\\.)*)"\}', open(h, encoding='utf-8').read())


def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.join(out, 'mid'), exist_ok=True)
    jobs, index, used = [], [], set()
    for i, (full, dna) in enumerate(read_presets(src)):
        full, dna = full.replace('\\"', '"').replace('\\\\', '\\'), dna.replace('\\"', '"').replace('\\\\', '\\')
        cat, name = full.split(': ', 1)
        k = kind_of(cat, name, dna)
        notes, tail = KINDS[k]()
        s = slug(name)
        if s in used: s = slug(cat + '-' + name)
        used.add(s)
        mid = os.path.join('mid', s + '.mid')
        write_mid(os.path.join(out, mid), notes)
        length = max(t + d for t, _, _, d in notes)
        jobs.append({'dna': dna, 'midi': mid, 'out': 'wav/%s.wav' % s, 'tail': tail})
        index.append({'i': i, 'cat': cat, 'name': name, 'dna': dna, 'kind': k, 'phrase': LABEL[k], 'slug': s,
                      'seconds': round(length + tail, 2)})
    json.dump(jobs, open(os.path.join(out, 'jobs.json'), 'w'), indent=1)
    json.dump(index, open(os.path.join(out, 'presets.json'), 'w'), indent=1)
    print(len(jobs), 'phrases ->', out)


if __name__ == '__main__':
    main()
