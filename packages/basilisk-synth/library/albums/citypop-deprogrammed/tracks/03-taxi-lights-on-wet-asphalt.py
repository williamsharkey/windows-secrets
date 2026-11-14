"""3. Var. II: Taxi Lights on Wet Asphalt. G major, 104 bpm: the bright one. Slap bass, a clean plucked
"guitar" in sixteenths, synth brass, the reed doubled by a polysynth an octave up. Every long note of the theme is
pushed a sixteenth early, the way the band leans into the next bar on a fast road. The last two choruses step up a
semitone, into A-flat."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 7                       # G
BPM = 104
S = Score(bpm=BPM, seed=303)
ep = S.part('ep', 1); bass = S.part('bass', 2); sax = S.part('sax', 3); syn = S.part('synlead', 4)
brass = S.part('brass', 5); strings = S.part('strings', 6); gtr = S.part('gtr', 7); glass = S.part('glass', 8)
kit = S.part('kit', 10); perc = S.part('perc', 11); street = S.part('street', 13)
rng = random.Random(33)


def push(notes, amt=0.25):
    """anticipate: notes of a beat or longer that start on a beat move a sixteenth earlier"""
    out = []
    for b, p, d in notes:
        if d >= 1.0 and abs(b - round(b)) < 1e-6 and b > 0:
            out.append((b - amt, p, d + amt))
        else:
            out.append((b, p, d))
    return out


def guitar(ch, vel=60, pat='x.xxx.x.x.xxx.x.'):
    """a clean plucked guitar cutting sixteenths on the upper chord tones"""
    for s, d, sym in ch:
        ns = voice(tones(sym, 3), None, 62, 76)
        k = 0
        while k * 0.25 < d - 1e-6:
            c = pat[int(round((s + k * 0.25) / 0.25)) % 16]
            if c == 'x':
                n = ns[(k // 2) % len(ns)] if k % 4 != 2 else ns[-1]
                gtr.note(s + k * 0.25, n, 0.2, vel + (8 if k % 4 == 0 else 0))
            k += 1


def stabs(ch, rhythm=((3.5, 0.3), (1.75, 0.25)), vel=86, lo=60, hi=79):
    """brass hits: on the pushes"""
    prev = None
    for s, d, sym in ch:
        ns = voice(tones(sym, 4), prev, lo, hi); prev = ns
        for off, ln in rhythm:
            if off < d:
                for n in ns:
                    brass.note(s + off, n, ln, vel)


def section(ch, t, bars, groove='citypop2', kv=0.85, gt=True, st=True, ep_style='citypop', bstyle='slap'):
    comp(ep, ch, style=ep_style, vel=62, lo=55, hi=76, rng=rng, var=0.1)
    bassline(bass, ch, style=bstyle, vel=98, rng=rng, var=0.15)
    drums(kit, groove, t, bars, vel=kv)
    drums(perc, {TAMB: '..x...x...x...x.', SHAKER: 'xxxxxxxxxxxxxxxx', CLAP: '....x.......x...'}, t, bars, vel=0.5)
    if gt:
        guitar(ch)
    if st:
        sustain(strings, ch, vel=46, lo=60, hi=84, n=3)


def lead(notes, at, vel=88):
    play(sax, grace(push(notes), every=2), at=at, vel=vel, legato=True)
    play(syn, push(notes), at=at, vel=vel - 22, tr=12, gate=0.85)


A = tprog(CHORDS_A, K)
B = tprog(CHORDS_B, K)
TA, TB = mel(THEME_A, K - 12), mel(THEME_B, K - 12)
t = 0.0
# ---- intro (8): the brass and the slap bass on a two-chord riff; the band falls in at bar 5
RIFF = tprog('Fmaj7 | Em7 A7 | Fmaj7 | Em7 A7 | Fmaj7 | Em7 A7 | Dm9 | G13sus4 G13', K)
ch = prog(RIFF, at=t)
bassline(bass, ch, style='slap', vel=98, rng=rng, var=0.1)
stabs(ch[:4], vel=80)
drums(kit, {CHH: 'x.x.x.x.x.x.x.x.'}, t, 4, vel=0.7)
section(ch[4:], t + 16, 4, gt=True, st=False)
stabs(ch[4:], vel=88)
fill(kit, t + 32, 'toms', 0.9)
street.note(0, 60, 8, 80)
t += 32

# ---- A, A: the reed and its polysynth shadow; brass answers the second time
for k in range(2):
    ch = prog(A, at=t)
    section(ch, t, 8, kv=0.82 + 0.04 * k)
    lead(TA, t, vel=86 + 2 * k)
    if k:
        for b0 in (3.25, 11.25, 19.25, 27.25):
            sym = next(s for s0, d0, s in ch if s0 <= t + b0 < s0 + d0)
            for n in voice(tones(sym, 3), None, 64, 78):
                brass.note(t + b0, n, 0.35, 82)
    kit.note(t, CRASH, 2, 92)
    fill(kit, t + 32, 'snare', 0.85)
    t += 32

# ---- B: strings take the lead line, the reed answers in thirds
ch = prog(B, at=t)
section(ch, t, 8, kv=0.8, gt=False, st=False, ep_style='citypop2')
play(strings, push(mel(THEME_B, K)), at=t, vel=74, legato=True)
thirds = [(b, p - 4 if (p - 4) % 12 in [(x + K) % 12 for x in C_MAJOR] else p - 3, d) for b, p, d in TB]
play(sax, push(thirds), at=t, vel=74, legato=True)
guitar(ch, vel=54, pat='..x...x...x...x.')
kit.note(t, CRASH, 2, 88)
fill(kit, t + 32, 'roll', 0.85)
t += 32

# ---- the motto as a riff: brass and glass in unison over the A changes, the bass doubling the pick-up
ch = prog(A, at=t)
section(ch, t, 8, kv=0.88)
for k in range(4):
    h = shift(mel(HEAD, K), t + 8 * k)
    play(glass, h, vel=80); play(brass, h, vel=84, tr=-12)
    play(glass, shift(mel([(0.0, 'D5', 0.5), (0.5, 'C5', 0.5), (1.0, 'A4', 1.0)], K), t + 8 * k + 5), vel=70)
fill(kit, t + 32, 'toms', 0.9)
t += 32

# ---- two choruses: the reed (sixteenths and all), then the bright piano
KEY = [(x + K) % 12 for x in C_MAJOR]
for k, (who, lo_, hi_, cells) in enumerate(((sax, 55, 79, None), (ep, 64, 88, None))):
    ch = prog(A, at=t)
    line = improvise(ch, KEY, seed=300 + k, lo=lo_, hi=hi_, density=0.9, cells=cells)
    for b, n, d in line:
        who.note(b, n, d * (0.95 if who is sax else 0.85), 84 + rng.randint(-8, 6))
    comp(ep if k == 0 else strings, ch, style='citypop' if k == 0 else 'halves', vel=58 if k == 0 else 44,
         lo=55 if k == 0 else 60, hi=74 if k == 0 else 82, rng=rng, var=0.15)
    bassline(bass, ch, style='slap', vel=96, rng=rng, var=0.2)
    drums(kit, 'citypop2', t, 8, vel=0.84)
    drums(perc, {TAMB: '..x...x...x...x.', SHAKER: 'xxxxxxxxxxxxxxxx'}, t, 8, vel=0.5)
    guitar(ch, vel=56)
    if k == 1:
        stabs(ch, rhythm=((3.5, 0.3),), vel=78)
    t += 32
fill(kit, t, 'snare', 0.9)

# ---- half-time breakdown (8): wet asphalt; the glass piano alone on the motto, the bass on long notes
ch = prog(tprog('Dm9 | G13 | Em7 | A7#9 | Dm9 | G13 | Bbmaj7 | A7sus4 A7', K), at=t)
comp(glass, ch, style='ballad', vel=60, lo=60, hi=80, push=False)
bassline(bass, ch, style='ballad', vel=88, rng=rng)
drums(kit, 'halftime', t, 8, vel=0.72)
for k in (0, 16):
    play(glass, shift(mel(HEAD, K), t + k + 4), vel=74, tr=12)
sustain(strings, ch, vel=40, lo=60, hi=84, n=3)
street.note(t, 60, 32, 90)
fill(kit, t + 32, 'toms', 0.95)
t += 32

# ---- B, then A twice a semitone up (A-flat): everyone
ch = prog(B, at=t)
section(ch, t, 8, kv=0.86)
lead(TB, t, vel=90)
stabs(ch, rhythm=((3.5, 0.3),), vel=80)
kit.note(t, CRASH, 2, 96)
fill(kit, t + 32, 'roll', 0.95)
t += 32
K2 = K + 1
A2 = tprog(CHORDS_A, K2)
for k in range(2):
    ch = prog(A2, at=t)
    section(ch, t, 8, kv=0.9)
    lead(mel(THEME_A, K2 - 12), t, vel=92)
    stabs(ch, rhythm=((3.5, 0.3), (1.75, 0.25)) if k == 0 else ((3.5, 0.3),), vel=84)
    play(strings, mel(THEME_A, K2), at=t, vel=58, legato=True)
    kit.note(t, CRASH, 2, 98)
    if k == 1:
        fade(ep, t + 16, t + 32, 1.0, 0.6); fade(kit, t + 16, t + 32, 1.0, 0.6)
        fade(perc, t + 16, t + 32, 1.0, 0.5); fade(gtr, t + 16, t + 32, 1.0, 0.5)
    t += 32
# the last chord, held; a horn somewhere outside
for s, d, sym in prog(tprog('Fmaj9:8', K2), at=t):
    for j, n in enumerate(voice(tones(sym, 5), None, 55, 79)):
        ep.note(s + j * 0.03, n, 7, 70); brass.note(s, n, 1.5, 76)
    bass.note(s, root(sym, 1) + 12, 6, 96)
    kit.note(s, KICK, 0.5, 100); kit.note(s, CRASH, 3, 96)
t += 10
texture(street, t - 40, 40, note=60, vel=80, bpm=BPM, seconds=24)

F = Feel(3033)
F.apply(S, sax, lay_ms=10, jit_ms=8, vel=4)
F.apply(S, syn, lay_ms=12, jit_ms=8, vel=4)
F.apply(S, ep, lay_ms=2, jit_ms=5, vel=5)
F.apply(S, bass, lay_ms=-3, jit_ms=4, vel=5)
F.apply(S, gtr, lay_ms=4, jit_ms=4, vel=6)
F.apply(S, brass, lay_ms=4, jit_ms=6, vel=4)
F.apply(S, kit, jit_ms=3, vel=4)
F.apply(S, perc, jit_ms=5, vel=6)

finish(__file__, S, {
    'title': 'Var. II: Taxi Lights on Wet Asphalt',
    'track': 3,
    'note': 'The theme in G at 104 bpm, every long note pushed a sixteenth early: slap bass, a plucked guitar in '
            'sixteenths, synth brass, the reed with a polysynth an octave above; two choruses; up to A-flat at the end.',
}, [
    ('street', 'ch13', 'Wet Traffic', dict(lufs=-34)),
    ('ep', 'ch1', 'Loft Tine Bright', dict(lufs=-21, pan=-22, verb=0.18, echo=0.04)),
    ('bass', 'ch2', 'Rubber Taxi', dict(lufs=-19)),
    ('sax', 'ch3', 'Harbour Reed', dict(lufs=-18, pan=6, verb=0.25, echo=0.12)),
    ('synlead', 'ch4', 'polysynth-showroom:Tropic Signal', dict(lufs=-28, pan=-10, verb=0.25, echo=0.2)),
    ('brass', 'ch5', 'polysynth-showroom:Signal Stab', dict(lufs=-24, pan=26, verb=0.2)),
    ('strings', 'ch6', 'studio-archive:Daylight Bows', dict(lufs=-26, pan=-40, verb=0.4)),
    ('gtr', 'ch7', 'courtyard-chapel:Kinetic Harp', dict(lufs=-26, pan=42, verb=0.12, echo=0.08)),
    ('glass', 'ch8', 'Glass Tine', dict(lufs=-24, pan=34, verb=0.3, echo=0.18)),
    ('kit', 'ch10', 'Loft Sticks', dict(lufs=-19, verb=0.08)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-28, pan=-30, verb=0.1)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3200, 'pingpong': 'yes', 'level': -7, 'lowcut': 250},
   reverb={'size': 1.6, 'predelay': 14, 'tone': 6000, 'level': -7, 'seed': 3113})
