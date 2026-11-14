"""1. Theme: Rain on the Loft Window. Eb major, 84 bpm, brushes. The whole theme is stated once, plainly: A, A
(with the vibraphone answering), B, A on muted trumpet. Then the electric piano takes sixteen bars of its own, B
returns, and the last A ends on the IV chord. The rain is there before the band and stays after it."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 3                       # Eb
BPM = 84
S = Score(bpm=BPM, seed=101)
ep = S.part('ep', 1); bass = S.part('bass', 2); lead = S.part('lead', 3); vibes = S.part('vibes', 4)
strings = S.part('strings', 5); pad = S.part('pad', 6); bell = S.part('bell', 7); horn = S.part('horn', 8)
kit = S.part('kit', 10); perc = S.part('perc', 11); rain = S.part('rain', 13); vinyl = S.part('vinyl', 14)
rng = random.Random(11)

A = tprog(CHORDS_A, K)
B = tprog(CHORDS_B, K)
A_END = tprog('Fmaj7 | Em7 A7 | Dm9 | G13 | Fmaj7 | E7#9 | Am9 D9 | Dm9 G13 | Fmaj9 | Fmaj9', K)
TA = mel(THEME_A, K - 12)   # the lead: Bb3..Eb5
TB = mel(THEME_B, K - 12)

bar = 4.0
t = 0.0
# ---- intro (4 bars): rain, vinyl, the piano alone on the first four chords, the motto on the bell
INTRO = 4 * bar
pad_in = prog(tprog('Fmaj7 | Em7 A7 | Dm9 | G13', K), at=t)
comp(ep, pad_in, style='ballad', vel=58, lo=51, hi=72, n=4, push=False)
for s, d, sym in pad_in:
    ep.note(s, root(sym, 2) + 12, d * 0.95, 50)      # left hand root
play(bell, shift(mel(HEAD, K), 8.0), vel=58)
t = INTRO

# ---- A1: the reed states the theme; brushes, fretless, shaker
ch = prog(A, at=t)
comp(ep, ch, style='citypop2', vel=60, lo=51, hi=72, rng=rng, var=0.15)
bassline(bass, ch, style='fretless', vel=88, rng=rng, var=0.3)
play(lead, grace(TA), at=t, vel=84, legato=True)
drums(kit, 'brush', t, 8, vel=0.75, swing=0.12)
drums(perc, {SHAKER: 'x.o.x.o.x.o.x.o.'}, t, 8, vel=0.55, swing=0.12)
sustain(pad, ch, vel=40, lo=56, hi=80)
fill(kit, t + 32, 'snare', 0.7)
t += 32

# ---- A2: sticks on the hats now; the vibraphone answers each phrase of the reed; strings come in
ch = prog(A, at=t)
comp(ep, ch, style='citypop', vel=62, lo=51, hi=72, rng=rng, var=0.1)
bassline(bass, ch, style='citypop', vel=92, rng=rng, var=0.2)
play(lead, grace(TA, every=2), at=t, vel=86, legato=True)
answers = [(3.0, ['G5', 'F5', 'Eb5', 'C5']), (11.0, ['Bb5', 'G5', 'F5']), (19.0, ['C6', 'Bb5', 'G5', 'Eb5']),
           (27.5, ['F5', 'G5', 'Bb5'])]
for b0, ns in answers:
    for i, n in enumerate(ns):
        vibes.note(t + b0 + i * 0.5, pitch(n), 0.9, 70 - i * 3)
drums(kit, 'citypop', t, 8, vel=0.72, swing=0.1)
drums(perc, {SHAKER: 'xox.xoxoxox.xoxo', TAMB: '....x.......x...'}, t, 8, vel=0.55, swing=0.1)
sustain(strings, ch, vel=48, lo=55, hi=79, n=3)
kit.note(t, CRASH, 2, 70)
fill(kit, t + 32, 'toms', 0.7)
t += 32

# ---- B: the bridge on the reed, strings carry it, the piano opens out
ch = prog(B, at=t)
comp(ep, ch, style='halves', vel=58, lo=51, hi=72, rng=rng)
bassline(bass, ch, style='fretless', vel=88, rng=rng, var=0.25)
play(lead, grace(TB), at=t, vel=88, legato=True)
sustain(strings, ch, vel=56, lo=55, hi=82, n=4)
sustain(pad, ch, vel=42, lo=56, hi=80)
drums(kit, 'brush', t, 7, vel=0.8, swing=0.12)
fill(kit, t + 32, 'roll', 0.75)
drums(perc, {SHAKER: 'x.o.x.o.x.o.x.o.'}, t, 8, vel=0.5, swing=0.12)
t += 32

# ---- A3: the muted trumpet has the theme, the reed sings a sixth below in the second half
ch = prog(A, at=t)
comp(ep, ch, style='citypop', vel=62, lo=51, hi=72, rng=rng, var=0.1)
bassline(bass, ch, style='citypop', vel=94, rng=rng, var=0.15)
play(horn, mel(THEME_A, K), at=t, vel=82, legato=True)
sixth = [(b, p - 9 if (p - 9) % 12 in [(x + K) % 12 for x in C_MAJOR] else p - 8, d) for b, p, d in mel(THEME_A[21:], K)]
play(lead, sixth, at=t, vel=70, legato=True)
drums(kit, 'citypop', t, 8, vel=0.78, swing=0.1)
drums(perc, {SHAKER: 'xox.xoxoxox.xoxo', TAMB: '....x.......x...', SNAP: '....x.......x...'}, t, 8, vel=0.55, swing=0.1)
sustain(strings, ch, vel=46, lo=55, hi=79, n=3)
kit.note(t, CRASH, 2, 78)
fill(kit, t + 32, 'snare', 0.75)
t += 32

# ---- solo: sixteen bars of electric piano over the A changes; the band thins to hats and bass
for k in range(2):
    ch = prog(A, at=t)
    line = improvise(ch, [(x + K) % 12 for x in C_MAJOR], seed=40 + k, lo=63, hi=84, density=0.8,
                     motif=shift(mel(HEAD, K), t) if k == 0 else None)
    for b, n, d in line:
        ep.note(b, n, d * 0.92, 72 + rng.randint(-8, 6))
    comp(ep, ch, style='halves', vel=50, lo=48, hi=63, n=3)
    bassline(bass, ch, style='citypop', vel=90, rng=rng, var=0.25)
    drums(kit, 'citypop', t, 8, vel=0.68 + 0.08 * k, swing=0.1, drop=(SNARE2,) if k == 0 else ())
    drums(perc, {SHAKER: 'xox.xoxoxox.xoxo'}, t, 8, vel=0.5, swing=0.1)
    sustain(pad, ch, vel=36 + 6 * k, lo=56, hi=80)
    t += 32
fill(kit, t, 'toms', 0.8)

# ---- B again, everyone
ch = prog(B, at=t)
comp(ep, ch, style='citypop2', vel=60, lo=51, hi=72, rng=rng)
bassline(bass, ch, style='fretless', vel=90, rng=rng, var=0.2)
play(lead, grace(TB), at=t, vel=90, legato=True)
play(vibes, mel(THEME_B, K), at=t, vel=52, gate=0.8)
sustain(strings, ch, vel=58, lo=55, hi=82, n=4)
drums(kit, 'citypop', t, 8, vel=0.76, swing=0.1)
drums(perc, {SHAKER: 'xox.xoxoxox.xoxo', TAMB: '....x.......x...'}, t, 8, vel=0.55, swing=0.1)
kit.note(t, CRASH, 2, 74)
t += 32

# ---- last A, ending on Fmaj9 (the IV: the evening is not over)
ch = prog(A_END, at=t)
comp(ep, ch[:-2], style='citypop', vel=58, lo=51, hi=72, rng=rng, var=0.15)
bassline(bass, ch[:-2], style='fretless', vel=86, rng=rng, var=0.3)
play(lead, grace(TA), at=t, vel=82, legato=True)
sustain(strings, ch, vel=50, lo=55, hi=79, n=3)
sustain(pad, ch, vel=40, lo=56, hi=80)
drums(kit, 'brush', t, 8, vel=0.7, swing=0.12)
drums(perc, {SHAKER: 'x.o.x.o.x.o.x.o.'}, t, 8, vel=0.45, swing=0.12)
end = t + 32
last = prog(tprog('Fmaj9:8', K), at=end)
for s, d, sym in last:
    ns = voice(tones(sym, 5), None, 51, 76)
    for j, n in enumerate(ns):
        ep.note(s + j * 0.06, n, 7.5, 56 - j * 2)
    bass.note(s, root(sym, 1) + 12, 7.5, 80)
    play(bell, shift(mel(HEAD, K), s + 2), vel=50)
    vibes.note(s + 4, pitch('G5'), 3, 44)
kit.note(end, RIDE, 2, 50)
t = end + 8 + 8               # the rain carries on for two more bars

total = t
texture(rain, 0, total, note=60, vel=92, bpm=BPM, seconds=26)
texture(vinyl, 0, total - 4, note=60, vel=70, bpm=BPM, seconds=26)
fade(rain, total - 8, total, 1.0, 0.6)

F = Feel(1011)
F.apply(S, lead, lay_ms=18, jit_ms=10, vel=4)
F.apply(S, horn, lay_ms=14, jit_ms=9, vel=4)
F.apply(S, ep, lay_ms=4, jit_ms=7, vel=5)
F.apply(S, bass, lay_ms=6, jit_ms=5, vel=4)
F.apply(S, kit, jit_ms=4, vel=4)
F.apply(S, perc, jit_ms=6, vel=6)
F.apply(S, vibes, lay_ms=8, jit_ms=8, vel=5)
for p in (ep,):
    for b in range(0, int(total), 4):
        p.cc(b, 64, 0); p.cc(b + 0.05, 64, 127)    # the sustain pedal, changed with each bar

finish(__file__, S, {
    'title': 'Theme: Rain on the Loft Window',
    'track': 1,
    'note': 'The theme, stated plainly in E-flat: A, A, B, A, an electric piano chorus, B, A, ending on the IV. '
            'Brushes, fretless, reed lead, muted trumpet, vibraphone answers, the rain before and after.',
}, [
    ('rain', 'ch13', 'Rain on Glass', dict(lufs=-30, width=1.0)),
    ('vinyl', 'ch14', 'Vinyl Bed', dict(lufs=-38, hp=120)),
    ('ep', 'ch1', 'Loft Tine', dict(lufs=-21, pan=-18, verb=0.24, echo=0.05)),
    ('bass', 'ch2', 'Fretless Harbour', dict(lufs=-20)),
    ('lead', 'ch3', 'Harbour Reed', dict(lufs=-18, pan=8, verb=0.3, echo=0.14)),
    ('vibes', 'ch4', 'courtyard-chapel:Delta Tower', dict(lufs=-24, pan=48, verb=0.32, echo=0.15)),
    ('strings', 'ch5', 'studio-archive:Humid Swell', dict(lufs=-26, pan=-42, verb=0.45)),
    ('pad', 'ch6', 'polysynth-showroom:Hotel Wash', dict(lufs=-29, pan=38, verb=0.4)),
    ('bell', 'ch7', 'Crystal Bb', dict(lufs=-26, pan=-50, verb=0.45, echo=0.25)),
    ('horn', 'ch8', 'Harmon Glow', dict(lufs=-19, pan=-10, verb=0.3, echo=0.12)),
    ('kit', 'ch10', 'Loft Brushes', dict(lufs=-21, verb=0.12)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-28, pan=34, verb=0.15)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 3.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 2800, 'pingpong': 'yes', 'level': -6, 'lowcut': 200},
   reverb={'size': 2.4, 'predelay': 22, 'tone': 5200, 'level': -5, 'seed': 3110})
