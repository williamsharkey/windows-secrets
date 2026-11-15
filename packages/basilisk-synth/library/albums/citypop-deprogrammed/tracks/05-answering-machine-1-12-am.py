"""5. Var. IV: Answering Machine, 1:12 a.m. C minor, 72 bpm, lo-fi. The phone rings twice and the machine takes it.
The theme in the minor, on a worn electric piano with the tape slowing and speeding under it. The drums lean back
on a swung sixteenth. Nobody leaves a message."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 0
BPM = 72
SW = 0.28
S = Score(bpm=BPM, seed=505)
ep = S.part('ep', 1); bass = S.part('bass', 2); trumpet = S.part('trumpet', 3); flute = S.part('flute', 4)
pad = S.part('pad', 5); bell = S.part('bell', 6); phone = S.part('phone', 7)
kit = S.part('kit', 10); perc = S.part('perc', 11); rain = S.part('rain', 13); vinyl = S.part('vinyl', 14)
rng = random.Random(55)

MA = 'Abmaj7 | Fm9 Bb7#9 | Dm7b5 | Gm9 | Abmaj7 | Fm9 | Cm9 D7b9 | Dm7b5 G7alt'
TM = modal(mel(THEME_A, K), TO_MINOR)          # the theme in C minor (E, A, B flattened)
KEYM = [0, 2, 3, 5, 7, 8, 10]


def band(ch, t, bars, kv=0.78, ep_style='lofi', ev=60, bass_style='lofi'):
    comp(ep, ch, style=ep_style, vel=ev, lo=51, hi=70, rng=rng, var=0.2)
    bassline(bass, ch, style=bass_style, vel=90, rng=rng, var=0.2)
    drums(kit, 'lofi', t, bars, vel=kv, swing=SW)
    drums(perc, {SHAKER: '..x...x...x...x.', SNAP: '....x.......x...'}, t, bars, vel=0.42, swing=SW)


t = 0.0
# ---- the call (4): two rings, the click, the beep; the piano under it
phone.note(0.0, 60, 2.6, 90)                  # ring
phone.note(4.2, 60, 2.6, 90)                  # ring
bell.note(10.4, pitch('B5'), 1.2, 70)         # the machine's beep (a sine-ish bell, held)
ch = prog(MA.split('|')[0] + '|' + MA.split('|')[1] + '|' + MA.split('|')[2] + '|' + MA.split('|')[3], at=t)
comp(ep, ch, style='ballad', vel=50, lo=51, hi=70, push=False)
t += 16

# ---- A in the minor, on the piano itself (a right hand over its own left)
ch = prog(MA, at=t)
band(ch, t, 8, ep_style='halves', ev=50)
play(ep, grace(TM), at=t, vel=78)
sustain(pad, ch, vel=36, lo=55, hi=79, n=3)
fill(kit, t + 32, 'flam', 0.7)
t += 32

# ---- A again: the muted trumpet, very close; the flute answers far off
ch = prog(MA, at=t)
band(ch, t, 8)
play(trumpet, grace(TM, every=2), at=t, vel=84, tr=-12, legato=True)
for b0, ns in ((3.0, ['G5', 'F5', 'Eb5']), (11.0, ['C6', 'Bb5', 'Ab5']), (19.0, ['G5', 'Ab5', 'Bb5']), (27.0, ['D5', 'Eb5', 'G5'])):
    for i, n in enumerate(ns):
        flute.note(t + b0 + i * 0.5, pitch(n), 0.9, 58)
sustain(pad, ch, vel=34, lo=55, hi=79, n=3)
t += 32

# ---- the tape runs on (4): drums, bass, the rain, nothing else
ch = prog('Abmaj7 | Gm9 | Fm9 | G7alt', at=t)
bassline(bass, ch, style='lofi', vel=92, rng=rng)
drums(kit, 'lofi', t, 4, vel=0.8, swing=SW)
fill(kit, t + 16, 'snare', 0.7)
t += 16

# ---- the piano's chorus (8), the motto in the left hand of its first bar
ch = prog(MA, at=t)
line = improvise(ch, KEYM, seed=505, lo=60, hi=82, density=0.75, motif=shift(modal(mel(HEAD, K), TO_MINOR), t))
for b, n, d in line:
    ep.note(b, n, d * 0.9, 72 + rng.randint(-8, 6))
comp(ep, ch, style='halves', vel=46, lo=48, hi=63, n=3)
bassline(bass, ch, style='lofi', vel=88, rng=rng, var=0.25)
drums(kit, 'lofi', t, 8, vel=0.76, swing=SW)
drums(perc, {SHAKER: '..x...x...x...x.'}, t, 8, vel=0.4, swing=SW)
t += 32

# ---- B, darkened (8): the trumpet on the bridge, a minor third lower than it was written
MB = 'Dbmaj7 | Cm7 F7 | Bbm9 | Eb13 | Bmaj7 | Bb7sus4 Bb7 | Ebmaj9 | G7alt'
ch = prog(MB, at=t)
band(ch, t, 8, kv=0.74, ev=54)
play(trumpet, grace(mel(THEME_B, K + 3 - 12)), at=t, vel=80, legato=True)
sustain(pad, ch, vel=38, lo=55, hi=79, n=3)
t += 32

# ---- the flute's chorus (8), over the minor A
ch = prog(MA, at=t)
band(ch, t, 8, kv=0.76)
line = improvise(ch, KEYM, seed=506, lo=67, hi=88, density=0.7)
for b, n, d in line:
    flute.note(b, n, d * 0.95, 66 + rng.randint(-6, 4))
t += 32

# ---- A on the flute an octave up, the trumpet a sixth below; pad and bell
ch = prog(MA, at=t)
band(ch, t, 8, kv=0.8)
play(flute, TM, at=t, vel=78, tr=12, legato=True)
low = [(b, p - 9 if (p - 9) % 12 in KEYM else p - 8, d) for b, p, d in TM]
play(trumpet, low, at=t, vel=68, legato=True)
sustain(pad, ch, vel=40, lo=55, hi=82, n=4)
play(bell, shift(modal(mel(HEAD, K), TO_MINOR), t + 28), vel=56, tr=12)
t += 32

# ---- the last A, halved: the piano alone with the drums, slowing (a little ritardando)
ch = prog(MA, at=t)
band(ch[:5], t, 4, kv=0.7, ev=52)
play(ep, [(b, p, d) for b, p, d in TM if b < 16], at=t, vel=74)
S.tempo(t + 12, 66); S.tempo(t + 14, 60)
t += 16
for s, d, sym in prog('Cm9:8', at=t):
    for j, n in enumerate(voice(tones(sym, 5), None, 51, 75)):
        ep.note(s + j * 0.12, n, 7, 54)
    bass.note(s, root(sym, 1) + 12, 6, 80)
bell.note(t + 4, pitch('B5'), 1.0, 56)   # the machine stops recording
t += 10

texture(rain, 0, t, note=60, vel=80, bpm=BPM, seconds=26)
texture(vinyl, 0, t, note=60, vel=88, bpm=BPM, seconds=26)

F = Feel(5055)
F.apply(S, ep, lay_ms=12, jit_ms=10, vel=6)
F.apply(S, trumpet, lay_ms=20, jit_ms=10, vel=4)
F.apply(S, flute, lay_ms=16, jit_ms=9, vel=4)
F.apply(S, bass, lay_ms=10, jit_ms=6, vel=4)
F.apply(S, kit, lay_ms=6, jit_ms=7, vel=5)
F.apply(S, perc, jit_ms=8, vel=6)

finish(__file__, S, {
    'title': 'Var. IV: Answering Machine, 1:12 a.m.',
    'track': 5,
    'note': 'The theme in C minor at 72 bpm, lo-fi: a worn tape electric piano, a close muted trumpet, a far flute, '
            'swung drums, vinyl and rain; the phone rings twice, the machine answers, nobody speaks.',
}, [
    ('rain', 'ch13', 'Soft Rain', dict(lufs=-33)),
    ('vinyl', 'ch14', 'Vinyl Bed', dict(lufs=-33, hp=200)),
    ('phone', 'ch7', 'Telephone, Two Rings', dict(lufs=-30, pan=-40, lp=3500, hp=300, verb=0.3)),
    ('ep', 'ch1', 'Tape Loft Tine', dict(lufs=-18, pan=-10, verb=0.22, lp=7000)),
    ('bass', 'ch2', 'Fretless Harbour', dict(lufs=-20, lp=1800)),
    ('trumpet', 'ch3', 'Harmon Glow', dict(lufs=-20, pan=12, verb=0.25, echo=0.12, lp=6000)),
    ('flute', 'ch4', 'Late Flute', dict(lufs=-24, pan=-34, verb=0.45, echo=0.2)),
    ('pad', 'ch5', 'Mist Choir', dict(lufs=-30, pan=26, verb=0.5)),
    ('bell', 'ch6', 'Machine Beep', dict(lufs=-30, pan=30, verb=0.3, lp=4000)),
    ('kit', 'ch10', 'Loft Sticks', dict(lufs=-21, lp=6500, verb=0.08)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-30, pan=24, lp=7000)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 2400, 'pingpong': 'yes', 'level': -6, 'lowcut': 250},
   reverb={'size': 2.6, 'predelay': 24, 'tone': 4500, 'level': -6, 'seed': 3115})
