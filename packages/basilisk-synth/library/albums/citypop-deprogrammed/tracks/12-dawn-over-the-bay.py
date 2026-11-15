"""12. Finale: Dawn over the Bay. E-flat, then F major, 96 bpm. The theme comes home with the night's
variations around it: the inversion as a high counter-line, the motto traded as in the espresso bar, the caprice
figure as a hinge into F, the pushes of the taxi ride, the party's fast version. The first
track ended on the IV. This one ends on the I, as the birds start and the rain stops."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 3                        # E-flat; later F
BPM = 96
S = Score(bpm=BPM, seed=1212)
ep = S.part('ep', 1); bass = S.part('bass', 2); reed = S.part('reed', 3); trumpet = S.part('trumpet', 4)
strings = S.part('strings', 5); choir = S.part('choir', 6); glass = S.part('glass', 7); flute = S.part('flute', 8)
brass = S.part('brass', 9); kit = S.part('kit', 10); perc = S.part('perc', 11); bell = S.part('bell', 12)
rain = S.part('rain', 13); dawn = S.part('dawn', 14); harbour = S.part('harbour', 15); syn = S.part('synth', 16)
rng = random.Random(1212)


def band(ch, t, bars, kv=0.82, groove='citypop', ep_style='citypop', bstyle='citypop', perc_on=True):
    comp(ep, ch, style=ep_style, vel=60, lo=53, hi=74, rng=rng, var=0.12)
    bassline(bass, ch, style=bstyle, vel=94, rng=rng, var=0.18)
    drums(kit, groove, t, bars, vel=kv)
    if perc_on:
        drums(perc, {SHAKER: 'xox.xoxoxox.xoxo', TAMB: '....x.......x...'}, t, bars, vel=0.5)


def push(notes, amt=0.25):
    return [(b - amt, p, d + amt) if d >= 1.0 and abs(b - round(b)) < 1e-6 and b > 0 else (b, p, d) for b, p, d in notes]


A = tprog(CHORDS_A, K)
B = tprog(CHORDS_B, K)
t = 0.0
# ---- before dawn (4): the last of the rain, the far horn, the piano on the first four chords
ch = prog(tprog('Fmaj7 | Em7 A7 | Dm9 | G13', K), at=t)
comp(ep, ch, style='ballad', vel=54, lo=51, hi=72, push=False)
for s, d, sym in ch:
    ep.note(s, root(sym, 2) + 12, d * 0.95, 48)
harbour.note(2.0, 60, 10, 80)
t += 16

# ---- A: the reed has the theme as it was at the start; the inversion floats over it on the glass piano
ch = prog(A, at=t)
band(ch, t, 8, kv=0.74, groove='brush', ep_style='citypop2', bstyle='fretless')
play(reed, grace(mel(THEME_A, K - 12)), at=t, vel=86, legato=True)
inv = invert(mel(THEME_A, 0), 'E5')
play(glass, [(b, p + K + 12, d) for b, p, d in inv if b >= 16], at=t, vel=52)
sustain(strings, ch, vel=40, lo=55, hi=79, n=3)
fill(kit, t + 32, 'snare', 0.75)
t += 32

# ---- A: the strings sing it; the vibes-and-piano question and answer from the espresso bar, on glass and flute
ch = prog(A, at=t)
band(ch, t, 8, kv=0.8)
play(strings, mel(THEME_A, K), at=t, vel=78, legato=True)
head_inv = [(b, p + K, d) for b, p, d in invert(mel(HEAD, 0), 'E5')]
for k in (0, 16):
    play(glass, shift(mel(HEAD, K + 12), t + k + 2), vel=66)
    play(flute, shift(head_inv, t + k + 6.5), vel=64)
kit.note(t, CRASH, 2, 84)
fill(kit, t + 32, 'toms', 0.8)
t += 32

# ---- B: everyone, the choir under it
ch = prog(B, at=t)
band(ch, t, 8, kv=0.84, ep_style='citypop2')
play(reed, grace(mel(THEME_B, K - 12)), at=t, vel=88, legato=True)
sustain(choir, ch, vel=52, lo=55, hi=79, n=4)
sustain(strings, ch, vel=48, lo=58, hi=84, n=3)
t += 32

# ---- the piano's chorus (8): bright, the party's fast theme answering on the polysynth in its last bars
ch = prog(A, at=t)
KEY = [(x + K) % 12 for x in C_MAJOR]
line = improvise(ch, KEY, seed=1200, lo=63, hi=86, density=0.85, motif=shift(mel(HEAD, K), t))
for b, n, d in line:
    if b < t + 24:
        ep.note(b, n, d * 0.88, 78 + rng.randint(-8, 6))
comp(ep, ch, style='halves', vel=46, lo=48, hi=62, n=3)
play(syn, [(b + 24, p, d) for b, p, d in augment(mel(THEME_A, K), 0.5) if b < 8], at=t, vel=74)
bassline(bass, ch, style='citypop', vel=92, rng=rng, var=0.2)
drums(kit, 'citypop2', t, 8, vel=0.84)
drums(perc, {SHAKER: 'xxxxxxxxxxxxxxxx'}, t, 8, vel=0.5)
t += 32

# ---- half-time (8): the glass piano and the bell trade the motto over the night's chords, the bass long
ch = prog(tprog('Dm9 | G13 | Em7 | A7#9 | Dm9 | G13 | Bbmaj7 | A7sus4 A7', K), at=t)
comp(ep, ch, style='ballad', vel=52, lo=53, hi=74, push=False)
bassline(bass, ch, style='ballad', vel=86, rng=rng)
drums(kit, 'halftime', t, 8, vel=0.7)
for k in range(4):
    play(glass if k % 2 == 0 else bell, shift(mel(HEAD, K + 12), t + 8 * k + 4), vel=66)
sustain(choir, ch, vel=40, lo=55, hi=79, n=3)
t += 32

# ---- the hinge (4): the caprice figure, then G7sus4 G7 into F major
ch = prog(tprog('Am9 | E7b9 | Gm9 | C7sus4 C7b9', 0), at=t)
play(strings, shift(mel(CAPRICE, 0), t), vel=80, tr=12 - 12, shape=False)
play(bass, shift(mel(CAPRICE, -24), t + 4), vel=94, shape=False)
comp(ep, ch, style='stabs', vel=60, lo=55, hi=74)
drums(kit, 'citypop', t, 4, vel=0.82)
for s, d, sym in ch[2:]:
    bass.note(s, root(sym, 2), d * 0.9, 92)
fill(kit, t + 16, 'roll', 0.9)
t += 16

# ---- A in F: reed and trumpet in octaves, everything pushed a sixteenth early, the brass on the pushes
K2 = 5
A2, B2 = tprog(CHORDS_A, K2), tprog(CHORDS_B, K2)
ch = prog(A2, at=t)
band(ch, t, 8, kv=0.9, groove='citypop2')
play(reed, push(mel(THEME_A, K2 - 12)), at=t, vel=90, legato=True)
play(trumpet, push(mel(THEME_A, K2)), at=t, vel=84, legato=True)
sustain(strings, ch, vel=52, lo=60, hi=84, n=3)
sustain(choir, ch, vel=46, lo=55, hi=79, n=3)
comp(brass, ch, style=[(3.5, 0.3, 1.0)], vel=82, lo=60, hi=79, push=False)
kit.note(t, CRASH, 2, 100)
fill(kit, t + 32, 'toms', 0.9)
t += 32

# ---- the reed's chorus in F (8)
ch = prog(A2, at=t)
KEY2 = [(x + K2) % 12 for x in C_MAJOR]
line = improvise(ch, KEY2, seed=1201, lo=55, hi=80, density=0.9)
for b, n, d in line:
    reed.note(b, n, d * 0.95, 86 + rng.randint(-8, 6))
band(ch, t, 8, kv=0.86, groove='citypop2')
sustain(strings, ch, vel=40, lo=60, hi=84, n=3)
t += 32

# ---- B in F: the trumpet and the flute share it; strings and choir
ch = prog(B2, at=t)
band(ch, t, 8, kv=0.86)
play(trumpet, mel(THEME_B[:14], K2 - 12), at=t, vel=80, legato=True)
play(flute, mel(THEME_B[14:], K2), at=t, vel=80, legato=True)
sustain(choir, ch, vel=54, lo=55, hi=79, n=4)
sustain(strings, ch, vel=50, lo=60, hi=84, n=3)
kit.note(t, CRASH, 2, 90)
t += 32

# ---- the last A: everyone; the inversion on top this time, on the glass piano, an octave up
ch = prog(A2, at=t)
band(ch, t, 8, kv=0.9, groove='citypop2')
play(reed, mel(THEME_A, K2 - 12), at=t, vel=92, legato=True)
play(trumpet, mel(THEME_A, K2), at=t, vel=86, legato=True)
play(strings, mel(THEME_A, K2), at=t, vel=74, legato=True)
play(glass, [(b, p + K2 + 12, d) for b, p, d in inv], at=t, vel=56)
sustain(choir, ch, vel=56, lo=55, hi=82, n=4)
comp(brass, ch, style=[(3.5, 0.3, 1.0), (1.75, 0.25, 0.9)], vel=84, lo=60, hi=79, push=False)
kit.note(t, CRASH, 2, 104)
t += 32

# ---- dawn (12): the motto, slow, on the crystal bell over the first chords; the band falls away; the I at last
ch = prog(tprog('Fmaj7 | Em7 A7 | Dm9 | G13 | Fmaj7 | Em7 A7 | Dm9 | G13sus4 G13', K2), at=t)
comp(ep, ch, style='ballad', vel=54, lo=53, hi=74, push=False)
bassline(bass, ch, style='ballad', vel=80, rng=rng)
sustain(strings, ch, vel=42, lo=60, hi=84, n=3)
drums(kit, 'brush', t, 4, vel=0.55)
play(bell, augment(mel(HEAD, K2 + 12), 2.0), at=t, vel=70, shape=False)
play(bell, augment(mel(HEAD, K2 + 12), 2.0), at=t + 16, vel=60, shape=False)
S.tempo(t + 24, 90); S.tempo(t + 28, 84)
t += 32
for s, d, sym in prog('Fmaj9:10', at=t):
    for j, n in enumerate(voice(tones(sym, 5), None, 53, 79)):
        ep.note(s + j * 0.08, n, 9, 58); strings.note(s, n, 9.5, 46); choir.note(s, n, 9.5, 44)
    bass.note(s, root(sym, 1) + 12, 9, 80)
    play(glass, shift(mel(HEAD, K2 + 12), s + 3), vel=52)
t += 14

texture(rain, 0, t - 60, note=60, vel=80, bpm=BPM, seconds=26)
fade(rain, t - 120, t - 60, 1.0, 0.4)
texture(dawn, t - 72, 72, note=60, vel=78, bpm=BPM, seconds=26)
harbour.note(t - 30, 60, 10, 70)

F = Feel(12012)
for p, lay, jit in ((reed, 14, 9), (trumpet, 14, 9), (flute, 14, 8), (strings, 12, 6), (glass, 8, 8), (ep, 4, 6),
                    (bass, 4, 5), (syn, 4, 5), (brass, 4, 6)):
    F.apply(S, p, lay_ms=lay, jit_ms=jit, vel=4)
F.apply(S, kit, jit_ms=3, vel=4)
F.apply(S, perc, jit_ms=6, vel=6)
for b in range(0, int(t), 4):
    ep.cc(b, 64, 0); ep.cc(b + 0.05, 64, 127)

finish(__file__, S, {
    'title': 'Finale: Dawn over the Bay',
    'track': 12,
    'note': 'The theme comes home in E-flat with the night around it (the inversion as a counter-line, the motto '
            'traded, the fast version), the caprice figure as a hinge into F, everything pushed and full, then the '
            'motto slowly on the bell; the first track ended on the IV, this one on the I, as the birds start.',
}, [
    ('rain', 'ch13', 'Rain on Glass', dict(lufs=-32)),
    ('dawn', 'ch14', 'Dawn Chorus', dict(lufs=-32, hp=300, pan=-10, verb=0.2)),
    ('harbour', 'ch15', 'Harbour Horn', dict(lufs=-34, pan=40, verb=0.4, lp=3000)),
    ('ep', 'ch1', 'Loft Tine', dict(lufs=-20, pan=-16, verb=0.22, echo=0.05)),
    ('bass', 'ch2', 'Fretless Harbour', dict(lufs=-20)),
    ('reed', 'ch3', 'Harbour Reed', dict(lufs=-18, pan=8, verb=0.28, echo=0.12)),
    ('trumpet', 'ch4', 'Harmon Glow', dict(lufs=-21, pan=-8, verb=0.3, echo=0.1)),
    ('strings', 'ch5', 'Humid Strings', dict(lufs=-23, pan=-36, verb=0.45)),
    ('choir', 'ch6', 'Mist Choir', dict(lufs=-27, pan=22, verb=0.55)),
    ('glass', 'ch7', 'Glass Tine', dict(lufs=-24, pan=36, verb=0.35, echo=0.18)),
    ('flute', 'ch8', 'Night Flute', dict(lufs=-22, pan=-24, verb=0.35, echo=0.12)),
    ('brass', 'ch9', 'Rooftop Brass', dict(lufs=-25, pan=26, verb=0.2)),
    ('synth', 'ch16', 'Couch Fort Lead', dict(lufs=-24, pan=10, verb=0.25, echo=0.15)),
    ('bell', 'ch12', 'Crystal Bb', dict(lufs=-22, pan=-20, verb=0.5, echo=0.25)),
    ('kit', 'ch10', 'Loft Sticks', dict(lufs=-20, verb=0.1)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-28, pan=30, verb=0.12)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 5.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 2800, 'pingpong': 'yes', 'level': -7, 'lowcut': 220},
   reverb={'size': 2.6, 'predelay': 22, 'tone': 5200, 'level': -5, 'seed': 3122})
