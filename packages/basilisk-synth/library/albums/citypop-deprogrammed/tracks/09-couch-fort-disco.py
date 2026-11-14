"""9. Var. VIII: Couch Fort Disco. E major, 118 bpm, four on the floor: the party in the loft. The theme in diminution
(twice as fast), so all eight bars fit in four and the polysynth plays them twice. Octave bass, clavinet sixteenths,
string runs, claps, a wordless vocoder choir, then the theme at its own speed on the reed. It fades out the way
disco records do."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _album import *

K = 4                        # E
BPM = 118
S = Score(bpm=BPM, seed=909)
ep = S.part('ep', 1); bass = S.part('bass', 2); syn = S.part('synth', 3); sax = S.part('sax', 4); clav = S.part('clav', 5)
strings = S.part('strings', 6); vox = S.part('vox', 7); brass = S.part('brass', 8); kit = S.part('kit', 10)
perc = S.part('perc', 11); crowd = S.part('room', 13)
rng = random.Random(99)

A = tprog(CHORDS_A, K)
B = tprog(CHORDS_B, K)
DIM = augment(mel(THEME_A, K), 0.5)                       # 8 bars of theme in 4


def clav16(ch, vel=62):
    """a funky clavinet: muted sixteenths on two chord tones, accents on the e and the a"""
    pat = 'x.xx.x.xx.x.x.xx'
    for s, d, sym in ch:
        ns = voice(tones(sym, 2), None, 60, 72)
        for k in range(int(round(d / 0.25))):
            tt = s + k * 0.25
            if pat[int(round(tt / 0.25)) % 16] == 'x':
                for n in ns:
                    clav.note(tt, n, 0.12, vel + (10 if k % 4 in (1, 3) else 0))


def runs(t, up=True, vel=70):
    """a string run into the next bar: a scale over the last beat"""
    sc = [(x + K) % 12 for x in C_MAJOR]
    ns = [n for n in range(67, 92) if n % 12 in sc]
    seq = ns[-8:] if up else ns[:8][::-1]
    seq = seq if up else seq
    for i, n in enumerate(seq if up else seq):
        strings.note(t - 1 + i * 0.125, n, 0.15, vel - 10 + i * 2)


def disco(ch, t, bars, kv=0.86, clav_on=True, ep_on=True):
    bassline(bass, ch, style='disco', vel=98, rng=rng, var=0.05)
    drums(kit, 'disco', t, bars, vel=kv)
    drums(perc, {TAMB: 'x.x.x.x.x.x.x.x.', SHAKER: '.x.x.x.x.x.x.x.x', CONGA_HI: '......x.......x.', CONGA_LO: '...x.......x..x.'}, t, bars, vel=0.5)
    if clav_on:
        clav16(ch)
    if ep_on:
        comp(ep, ch, style='disco', vel=56, lo=56, hi=74, rng=rng)


t = 0.0
# ---- intro (8): the kit and the bass; the strings rise into bar 5; the room fills
ch = prog(A, at=t)
bassline(bass, ch[:5], style='disco', vel=96, rng=rng)
drums(kit, 'disco', t, 4, vel=0.8, drop=(CLAP,))
runs(t + 16)
disco(prog(A, at=t)[5:], t + 16, 4)
crowd.note(0, 60, 40, 70)
t += 32

# ---- A, twice as fast: the polysynth plays the whole theme twice
ch = prog(A, at=t)
disco(ch, t, 8)
play(syn, DIM, at=t, vel=86); play(syn, DIM, at=t + 16, vel=90)
kit.note(t, CRASH, 2, 96)
runs(t + 32)
t += 32

# ---- A at its own speed: the reed; strings answer with the fast version an octave up
ch = prog(A, at=t)
disco(ch, t, 8)
play(sax, grace(mel(THEME_A, K - 12)), at=t, vel=88, legato=True)
play(strings, [(b, p, d) for b, p, d in DIM if b >= 8], at=t + 8, vel=64, tr=12)
for b0 in (3.5, 11.5, 19.5, 27.5):
    sym = next(s for s0, d0, s in ch if s0 <= t + b0 < s0 + d0)
    for n in voice(tones(sym, 4), None, 60, 79):
        brass.note(t + b0, n, 0.3, 86)
t += 32

# ---- B: the vocoder choir has it, the strings under them
ch = prog(B, at=t)
disco(ch, t, 8, clav_on=False)
play(vox, mel(THEME_B, K), at=t, vel=84, legato=True)
sustain(strings, ch, vel=52, lo=60, hi=84, n=3)
runs(t + 32)
t += 32

# ---- the fast A again, with brass on the pushes
ch = prog(A, at=t)
disco(ch, t, 8)
play(syn, DIM, at=t, vel=88); play(syn, DIM, at=t + 16, vel=92)
comp(brass, ch, style=[(3.5, 0.3, 1.0)], vel=84, lo=60, hi=79, push=False)
kit.note(t, CRASH, 2, 96)
t += 32

# ---- breakdown (8): bass, claps and congas; the motto chopped on the clavinet
ch = prog(tprog('Dm9 | Dm9 | G13 | G13 | Em7 | A7 | Dm9 | G13sus4 G13', K), at=t)
bassline(bass, ch, style='disco', vel=96, rng=rng)
drums(kit, {KICK: 'x...x...x...x...', CLAP: '....x.......x...'}, t, 8, vel=0.84)
drums(perc, {CONGA_HI: '..x...x...x.x.x.', CONGA_LO: 'x..x..x..x..x...', SHAKER: 'xxxxxxxxxxxxxxxx'}, t, 8, vel=0.6)
for k in range(4):
    play(clav, shift(mel(HEAD, K), t + 8 * k + 4), vel=76)
runs(t + 32)
t += 32

# ---- choruses: the polysynth, then the clavinet's turn on the motto
KEY = [(x + K) % 12 for x in C_MAJOR]
for k in range(2):
    ch = prog(A, at=t)
    disco(ch, t, 8, clav_on=(k == 0))
    who = syn if k == 0 else clav
    line = improvise(ch, KEY, seed=900 + k, lo=64, hi=88, density=0.9, cells=RHYTHMS[2:6])
    for b, n, d in line:
        who.note(b, n, d * 0.85, 86 + rng.randint(-8, 6))
    if k == 1:
        sustain(vox, ch, vel=50, lo=60, hi=79, n=3)
    t += 32

# ---- B again: the reed and the vocoder choir together, string runs between the phrases
ch = prog(B, at=t)
disco(ch, t, 8)
play(sax, mel(THEME_B, K - 12), at=t, vel=88, legato=True)
sustain(vox, ch, vel=54, lo=60, hi=79, n=3)
for k in range(1, 4):
    runs(t + 8 * k, up=(k % 2 == 1), vel=60)
kit.note(t, CRASH, 2, 96)
t += 32

# ---- A for everyone; then A again, fading
for k in range(2):
    ch = prog(A, at=t)
    disco(ch, t, 8, kv=0.9)
    play(sax, mel(THEME_A, K - 12), at=t, vel=90, legato=True)
    play(syn, DIM, at=t, vel=72, tr=12); play(syn, DIM, at=t + 16, vel=72, tr=12)
    sustain(vox, ch, vel=48, lo=60, hi=79, n=3)
    comp(brass, ch, style=[(3.5, 0.3, 1.0)], vel=80, lo=60, hi=79, push=False)
    if k == 1:
        for p in (ep, bass, syn, sax, clav, strings, vox, brass, kit, perc):
            fade(p, t, t + 32, 1.0, 0.25)
    else:
        kit.note(t, CRASH, 2, 100)
    t += 32
crowd.note(t - 40, 60, 46, 76)
t += 4

F = Feel(9099)
F.apply(S, sax, lay_ms=8, jit_ms=8, vel=4)
F.apply(S, syn, lay_ms=4, jit_ms=5, vel=4)
F.apply(S, clav, lay_ms=0, jit_ms=4, vel=6)
F.apply(S, bass, lay_ms=0, jit_ms=3, vel=4)
F.apply(S, ep, lay_ms=4, jit_ms=5, vel=5)
F.apply(S, kit, jit_ms=2, vel=4)
F.apply(S, perc, jit_ms=4, vel=6)

finish(__file__, S, {
    'title': 'Var. VIII: Couch Fort Disco',
    'track': 9,
    'note': 'Four on the floor in E at 118: the theme in diminution (eight bars in four) on polysynth, then at its own '
            'speed on the reed; octave bass, clavinet, string runs, claps, congas, a wordless vocoder choir; it fades.',
}, [
    ('room', 'ch13', 'City at Night', dict(lufs=-36)),
    ('ep', 'ch1', 'Loft Tine Bright', dict(lufs=-24, pan=-20, verb=0.15)),
    ('bass', 'ch2', 'Rubber Taxi', dict(lufs=-18)),
    ('synth', 'ch3', 'polysynth-showroom:Violet Pilot', dict(lufs=-20, pan=6, verb=0.25, echo=0.15)),
    ('sax', 'ch4', 'Harbour Reed', dict(lufs=-19, pan=-6, verb=0.25, echo=0.1)),
    ('clav', 'ch5', 'polysynth-showroom:Distant Parlour', dict(lufs=-24, pan=36, verb=0.1)),
    ('strings', 'ch6', 'studio-archive:Daylight Bows', dict(lufs=-24, pan=-38, verb=0.35)),
    ('vox', 'ch7', 'polysynth-showroom:Broadcast Vox', dict(lufs=-24, pan=20, verb=0.45)),
    ('brass', 'ch8', 'polysynth-showroom:Noble Hit', dict(lufs=-24, pan=28, verb=0.2)),
    ('kit', 'ch10', 'Couch Disco', dict(lufs=-18, verb=0.08)),
    ('perc', 'ch11', 'Loft Percussion', dict(lufs=-26, pan=-26, verb=0.1)),
], master={'loudness': -16, 'ceiling': -1.0, 'fadeout': 4.0},
   echo={'time': '1/8', 'feedback': 0.3, 'tone': 3200, 'pingpong': 'yes', 'level': -8, 'lowcut': 250},
   reverb={'size': 1.6, 'predelay': 14, 'tone': 6000, 'level': -7, 'seed': 3119})
