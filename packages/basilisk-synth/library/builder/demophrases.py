"""Demo phrases for the Sound Pack Explorer previews: chosen per preset by its role (category), its pack's mood and
its envelope, seeded by its id, so every preset gets a short figure that suits it and two neighbours rarely share one.

Every phrase here is original (written for this library); none quotes a song. bele dance's own songs are users'
recordings and generated takes, with no bundled third-party scores, so nothing was taken from them.

phrase_for(preset) -> (notes [(t, note, vel, dur)], tail_s, label, phrase_id)
"""
import hashlib, random

# ------------------------------------------------------------------ moods: key, tempo, progression (degrees), scale
MAJOR, MINOR, DORIAN, MIXO, PENTA, MINPENTA = [0, 2, 4, 5, 7, 9, 11], [0, 2, 3, 5, 7, 8, 10], [0, 2, 3, 5, 7, 9, 10], \
    [0, 2, 4, 5, 7, 9, 10], [0, 2, 4, 7, 9], [0, 3, 5, 7, 10]
MOODS = {   # key root (MIDI, octave 4), bpm, scale, progressions (lists of scale-degree roots), feel
    'house': (57, 122, MINOR, [[0, 5, 3, 4], [0, 3, 5, 4]], 'offbeat'),
    'techno': (55, 130, MINOR, [[0, 0, 5, 6], [0, 6, 0, 3]], 'driving'),
    'trance': (57, 138, MINOR, [[0, 5, 2, 6], [5, 3, 0, 4]], 'driving'),
    'breaks': (53, 172, MINOR, [[0, 3, 5, 4], [0, 6, 5, 3]], 'syncopated'),
    'bass': (52, 140, MINOR, [[0, 0, 5, 6], [0, 3, 0, 4]], 'halftime'),
    'hiphop': (55, 88, DORIAN, [[0, 3, 1, 4], [1, 4, 0, 5]], 'laidback'),
    'retro': (57, 104, MINOR, [[5, 3, 0, 4], [0, 5, 3, 6]], 'straight'),
    'ambient': (60, 70, MAJOR, [[0, 3, 5, 4], [3, 0, 4, 5]], 'slow'),
    'glitch': (61, 126, MINOR, [[0, 1, 5, 6]], 'stutter'),
    'lounge': (65, 108, MAJOR, [[1, 4, 0, 5], [0, 5, 1, 4]], 'swing'),
    'chip': (60, 140, MAJOR, [[0, 5, 3, 4], [0, 3, 4, 0]], 'straight'),
    'classic': (60, 112, MAJOR, [[0, 4, 5, 3], [0, 5, 3, 4]], 'straight'),
    'studio': (62, 92, MAJOR, [[0, 3, 4, 0], [0, 5, 1, 4]], 'flowing'),
    'heritage': (60, 100, MAJOR, [[0, 3, 4, 0], [0, 5, 3, 4]], 'straight'),
    'vapor': (63, 84, MAJOR, [[3, 2, 1, 0], [1, 4, 0, 5]], 'laidback'),
    'pauly': (60, 112, MAJOR, [[0, 3, 4, 0], [0, 4, 5, 3]], 'bouncy'),
    'tape': (62, 96, MAJOR, [[0, 3, 4, 0], [0, 5, 3, 4], [0, 2, 3, 4]], 'flowing'),
    'early': (62, 84, DORIAN, [[0, 6, 0, 4], [0, 3, 6, 0]], 'flowing'),
    'ocean': (50, 56, MINOR, [[0, 5, 3, 0]], 'slow'),
    'office': (57, 118, MIXO, [[0, 0, 6, 3]], 'mechanical'),
    'poly': (57, 116, MINOR, [[0, 5, 3, 4], [5, 3, 0, 6]], 'straight'),
    'electromech': (60, 100, MIXO, [[0, 3, 0, 4]], 'mechanical'),
}
PACK_MOOD = {'workgroup-house': 'house', 'techno-server': 'techno', 'trance-connectivity': 'trance',
             'breakbeat-resource': 'breaks', 'bass-enterprise': 'bass', 'beat-management': 'hiphop', 'retro-display': 'retro',
             'screen-saver': 'ambient', 'diagnostics': 'glitch', 'leisure': 'lounge', 'game-port': 'chip',
             'workstation-classics': 'classic', 'studio-archive': 'studio', 'w3x-heritage': 'heritage', 'rom-reference': 'classic',
             'lifestyle-aesthetics': 'vapor', 'electromech-heritage': 'electromech', 'kit-manager': 'breaks', 'rainy-loft': 'lounge',
             'waulophone': 'pauly', 'paulywaulophone': 'pauly', 'garden-rhythm': 'house', 'tape-parlour': 'tape', 'courtyard-chapel': 'early',
             'listening-post': 'ocean', 'office-machinery': 'office', 'polysynth-showroom': 'poly'}
ROLE = {'Keys': 'keys', 'Organ': 'organ', 'Bass': 'bass', 'Sub': 'bass', 'Pad': 'pad', 'Strings': 'strings', 'Vocal': 'vocal',
        'Stab': 'stab', 'Brass': 'brass', 'Chord': 'stab', 'Lead': 'lead', 'Pluck': 'pluck', 'Arp': 'pluck', 'Bell': 'bell',
        'Mallet': 'mallet', 'FX': 'fx', 'Texture': 'texture', 'Drone': 'drone', 'Perc': 'perc', 'Kit': 'kit'}


def scale_note(root, sc, deg, octave=0):
    o, d = divmod(deg, len(sc))
    return root + sc[d] + 12 * (o + octave)


def triad(root, sc, deg, extra=False):
    out = [scale_note(root, sc, deg), scale_note(root, sc, deg + 2), scale_note(root, sc, deg + 4)]
    if extra: out.append(scale_note(root, sc, deg + 6))
    return out


# ------------------------------------------------------------------ figures (each returns notes, tail)
def f_chords(m, rng, slow, spread=False, comp=False):
    root, bpm, sc, progs, feel = m
    beat = 60 / bpm; prog = rng.choice(progs); bar = 4 * beat
    out = []
    for i, d in enumerate(prog):
        ch = triad(root - 12, sc, d, extra=rng.random() < 0.5)
        t0 = i * bar
        if comp and not slow:          # keys comping: the chord on 1 and the and-of-2, pushed
            hits = [(0, 0.9), (1.5, 0.45), (2.5, 0.4)] if feel != 'offbeat' else [(0.5, 0.4), (1.5, 0.4), (2.5, 0.4), (3.5, 0.4)]
            for b, dur in hits:
                for k, n in enumerate(ch): out.append((t0 + b * beat, n, 84 - 4 * k, dur * beat))
        else:
            for k, n in enumerate(ch):
                off = (k * 0.12 * beat) if spread else 0
                out.append((t0 + off, n, 80 - 5 * k, bar * 0.98 - off))
    return out, (2.5 if slow else 1.2)


def f_melody(m, rng, slow, register=12, rhythm=None):
    root, bpm, sc, progs, feel = m
    beat = 60 / bpm
    rh = rhythm or rng.choice([[1, 0.5, 0.5, 1, 1, 2, 1, 1], [0.5, 0.5, 1, 0.5, 0.5, 1, 2, 1, 1], [1.5, 0.5, 1, 1, 1.5, 0.5, 2],
                               [0.75, 0.75, 0.5, 1, 1, 0.75, 0.75, 0.5, 2]])
    if slow: rh = [r * 2 for r in rh[:5]]
    deg = rng.choice([0, 2, 4]); t = 0.0; out = []
    for i, r in enumerate(rh):
        n = scale_note(root, sc, deg, register // 12)
        out.append((round(t, 3), n, 96 if i % 2 == 0 else 86, r * beat * (0.95 if slow else 0.85)))
        t += r * beat
        deg += rng.choice([-2, -1, 1, 1, 2, -1, 3])
        deg = max(-2, min(9, deg))
    return out, (2.0 if slow else 1.0)


def f_arp(m, rng, slow, up_down=True, octaves=2, step_beats=0.25):
    root, bpm, sc, progs, feel = m
    beat = 60 / bpm; prog = rng.choice(progs); out = []; t = 0.0
    step = step_beats * beat * (2 if slow else 1)
    for d in prog:
        ch = triad(root, sc, d) + [triad(root, sc, d)[0] + 12]
        seq = ch + (ch[-2:0:-1] if up_down else [])
        if octaves > 1 and rng.random() < 0.5: seq = seq + [n + 12 for n in ch]
        for i in range(int(4 * beat / step)):
            n = seq[i % len(seq)]
            out.append((round(t, 3), n, 104 if i % 4 == 0 else 82, step * 0.9)); t += step
    return out, (2.2 if slow else 1.2)


def f_bass(m, rng, slow):
    root, bpm, sc, progs, feel = m
    beat = 60 / bpm; prog = rng.choice(progs); out = []
    pat = {'offbeat': [(0.5, 0.4), (1.5, 0.4), (2.5, 0.4), (3.5, 0.4)], 'driving': [(0, 0.2), (0.5, 0.2), (1, 0.2), (1.5, 0.2), (2, 0.2), (2.5, 0.2), (3, 0.2), (3.5, 0.2)],
           'syncopated': [(0, 0.7), (0.75, 0.25), (1.5, 0.5), (2.5, 0.4), (3.25, 0.5)], 'halftime': [(0, 1.5), (2.5, 0.4), (3, 0.9)],
           'laidback': [(0, 0.9), (1.75, 0.25), (2, 0.9), (3.5, 0.4)], 'swing': [(0, 0.9), (1, 0.9), (2, 0.9), (3, 0.6), (3.66, 0.3)],
           'bouncy': [(0, 0.45), (1, 0.45), (2, 0.45), (2.5, 0.4), (3, 0.45)], 'mechanical': [(0, 0.3), (0.5, 0.3), (1.5, 0.3), (2, 0.3), (3, 0.3)]
           }.get(feel, [(0, 0.9), (1, 0.4), (2, 0.9), (3, 0.4)])
    if slow: pat = [(0, 3.5)]
    for i, d in enumerate(prog):
        r = scale_note(root - 24, sc, d)
        for k, (b, du) in enumerate(pat):
            n = r + (12 if (k == len(pat) - 1 and feel in ('offbeat', 'bouncy', 'swing')) else 0)
            out.append((round(i * 4 * beat + b * beat, 3), n, 112 if k == 0 else 92, du * beat))
    return out, 1.0


def f_stabs(m, rng, slow):
    root, bpm, sc, progs, feel = m
    beat = 60 / bpm; prog = rng.choice(progs); out = []
    hits = [(0, 0.3), (0.75, 0.25), (2.5, 0.3)] if not slow else [(0, 1.5), (2, 1.5)]
    for i, d in enumerate(prog[:3] if bpm > 120 else prog):
        ch = triad(root - 12, sc, d)
        for b, du in hits:
            for k, n in enumerate(ch): out.append((round(i * 4 * beat + b * beat, 3), n, 108 - 4 * k, du * beat))
    return out, 1.2


def f_fx(m, rng, slow):
    root = m[0]
    g = rng.choice(['rise', 'fall', 'hit', 'pair'])
    if g == 'rise': return [(0.0, root - 12, 100, 3.5), (3.8, root, 90, 2.5)], 2.5
    if g == 'fall': return [(0.0, root + 12, 100, 2.5), (2.8, root, 96, 2.5)], 2.5
    if g == 'hit': return [(0.0, root, 110, 1.5), (1.8, root - 5, 96, 1.5), (3.6, root - 12, 104, 2.5)], 2.5
    return [(0.0, root, 100, 2.0), (2.4, root + 7, 92, 3.0)], 2.5


def f_drone(m, rng, slow):
    root, bpm, sc, progs, feel = m
    r = root - 12
    if rng.random() < 0.5: return [(0.0, r, 96, 7.0), (0.0, r + 7, 80, 7.0), (4.0, r + 12, 70, 3.0)], 3.0
    return [(0.0, r, 96, 4.0), (0.0, r + 7, 76, 4.0), (4.2, r + 5, 90, 3.5), (4.2, r + 12, 72, 3.5)], 3.0


def f_texture(m, rng, slow):
    root = m[0]
    return [(0.0, root, 100, 6.0)] + ([(3.0, root + 7, 80, 3.5)] if rng.random() < 0.5 else []), 2.5


def f_perc(m, rng, slow):
    bpm = m[1]; beat = 60 / bpm; out = []
    pat = rng.choice([[0, 1, 1.5, 2, 3, 3.5], [0, 0.75, 1.5, 2, 2.75, 3.5], [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]])
    notes = rng.choice([[60, 60, 72, 60, 48, 67], [48, 60, 60, 72, 60, 64, 55, 60], [60, 67, 60, 72, 64, 60, 55, 48]])
    for bar in range(2):
        for i, b in enumerate(pat):
            out.append((round((bar * 4 + b) * beat, 3), notes[i % len(notes)], 112 if b == 0 else 88, 0.12))
    return out, 1.0


KIT_GROOVES = {   # genre: [(16th step, GM note, velocity)] over one bar
    'house': [(0, 36, 118), (4, 36, 118), (8, 36, 118), (12, 36, 118), (4, 39, 100), (12, 39, 100)] + [(s, 42, 80) for s in (2, 6, 10, 14)] + [(14, 46, 86)],
    'breaks': [(0, 36, 118), (6, 36, 100), (10, 36, 110), (4, 38, 112), (12, 38, 112), (15, 38, 70)] + [(s, 42, 78) for s in range(0, 16, 2)] + [(9, 38, 60)],
    'triphop': [(0, 36, 112), (7, 36, 96), (4, 38, 104), (12, 38, 104), (14, 37, 70)] + [(s, 42, 72) for s in (0, 3, 6, 8, 11, 14)],
    'march': [(0, 36, 110), (8, 36, 104), (4, 38, 96), (6, 38, 80), (12, 38, 100), (13, 38, 76), (14, 38, 84), (15, 38, 96)] + [(s, 49 if s == 0 else 51, 70) for s in (0, 8)],
    'lounge': [(0, 36, 100), (7, 36, 86), (10, 36, 90), (4, 37, 84), (12, 37, 84)] + [(s, 42, 66) for s in range(0, 16, 2)] + [(3, 56, 70), (11, 56, 70)],
    'techno': [(0, 36, 120), (4, 36, 120), (8, 36, 120), (12, 36, 120), (4, 39, 96), (12, 39, 96)] + [(s, 46, 80) for s in (2, 6, 10, 14)] + [(s, 42, 66) for s in (1, 3, 5, 7, 9, 11, 13, 15)],
}


def f_kit(m, rng, pads, mood):
    genre = {'house': 'house', 'techno': 'techno', 'trance': 'techno', 'breaks': 'breaks', 'bass': 'breaks', 'hiphop': 'triphop',
             'retro': 'breaks', 'glitch': 'breaks', 'lounge': 'lounge', 'chip': 'house', 'pauly': 'lounge', 'office': 'march',
             'electromech': 'march', 'heritage': 'march'}.get(mood, rng.choice(list(KIT_GROOVES)))
    bpm = {'house': 122, 'techno': 130, 'breaks': 172 / 2 * 1.0 + 30, 'triphop': 86, 'march': 112, 'lounge': 112}[genre]
    step = 60 / bpm / 4
    have = sorted(pads) if pads else [36, 38, 42, 46, 39, 37]
    def near(n): return n if n in have else min(have, key=lambda p: abs(p - n))
    out = []
    for bar in range(2):
        for s, n, v in KIT_GROOVES[genre]:
            out.append((round((bar * 16 + s) * step, 3), near(n), v, 0.12))
    # every pad of the kit once at the end, so its whole set is heard
    t0 = 32 * step + 0.1
    out += [(round(t0 + 0.14 * i, 3), p, 100, 0.12) for i, p in enumerate(have[:20])]
    return sorted(set(out)), 1.2, genre


# ------------------------------------------------------------------ the choice
def phrase_for(p, pads=None, slow_attack=False):
    """p: a preset row (pack, category, slug, kind); pads: a kit's mapped notes; slow_attack: the patch's A >= 250 ms"""
    seed = int(hashlib.sha1(p['slug'].encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    mood = PACK_MOOD.get(p['pack'], 'classic')
    m = MOODS[mood]
    role = ROLE.get(p['category'], 'keys')
    slow = slow_attack or role in ('pad', 'drone', 'strings') or mood in ('ambient', 'ocean')
    if role == 'kit':
        notes, tail, genre = f_kit(m, rng, pads, mood)
        return notes, tail, 'kit groove: %s' % genre, 'kit-%s' % genre
    table = {
        'keys': [('comp', lambda: f_chords(m, rng, slow, comp=True)), ('melody over chords', None), ('arpeggio', lambda: f_arp(m, rng, slow))],
        'organ': [('held chords', lambda: f_chords(m, rng, slow)), ('comp', lambda: f_chords(m, rng, slow, comp=True))],
        'pad': [('chord swell', lambda: f_chords(m, rng, True, spread=True)), ('progression', lambda: f_chords(m, rng, True))],
        'strings': [('legato chords', lambda: f_chords(m, rng, True, spread=True)), ('melody', lambda: f_melody(m, rng, True))],
        'vocal': [('sung line', lambda: f_melody(m, rng, slow)), ('choir chords', lambda: f_chords(m, rng, True))],
        'stab': [('stabs', lambda: f_stabs(m, rng, slow)), ('comp', lambda: f_chords(m, rng, slow, comp=True))],
        'brass': [('stabs', lambda: f_stabs(m, rng, slow)), ('fanfare line', lambda: f_melody(m, rng, slow, register=0))],
        'lead': [('lead melody', lambda: f_melody(m, rng, slow)), ('lead melody (high)', lambda: f_melody(m, rng, slow, register=12))],
        'pluck': [('arpeggio', lambda: f_arp(m, rng, slow)), ('pattern', lambda: f_arp(m, rng, slow, up_down=False, octaves=1, step_beats=0.5))],
        'bell': [('bell tune', lambda: f_melody(m, rng, slow, register=12)), ('chime arpeggio', lambda: f_arp(m, rng, slow, step_beats=0.5))],
        'mallet': [('mallet tune', lambda: f_melody(m, rng, slow, register=12)), ('mallet arpeggio', lambda: f_arp(m, rng, slow))],
        'bass': [('bass groove', lambda: f_bass(m, rng, slow))],
        'fx': [('gesture', lambda: f_fx(m, rng, slow))],
        'drone': [('drone', lambda: f_drone(m, rng, slow))],
        'texture': [('texture', lambda: f_texture(m, rng, slow))],
        'perc': [('pattern', lambda: f_perc(m, rng, slow))],
    }.get(role)
    label, fn = rng.choice(table)
    if fn is None:   # keys: chords in the left hand and a melody on top
        a, _ = f_chords(m, rng, slow); b, tail = f_melody(m, rng, slow, register=12)
        notes = a + b
    else:
        notes, tail = fn()
    # trim to about 10 s
    notes = [(t, n, v, min(d, 9.6 - t)) for t, n, v, d in notes if t < 9.0]
    return notes, tail, '%s (%s)' % (label, mood), '%s-%s-%s' % (role, label.split()[0], mood)
