"""Volcano View Cha-Cha: an original lounge cha-cha, 118 bpm, F major. Claves and bongo taps on the cha-cha-cha,
a vibes-bells tune, tiki piano montuno, cello bass, a granite lead in the bridge, strings, a gong and the robin."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=118, seed=1958)
bells = S.part('bells', 1)
piano = S.part('piano', 2)
cello = S.part('cello', 3)
strings = S.part('strings', 4)
lead = S.part('lead', 5)
marimba = S.part('marimba', 6)
claves = S.part('claves', 7)
bongo = S.part('bongo', 8)
guiro = S.part('guiro', 9)
gong = S.part('gong', 11)
bird = S.part('bird', 12)

A = 'Fmaj7 Gm7 C7 Fmaj7 Fmaj7 Gm7 C7 F6'
B = 'Bbmaj7 Bbm6 Am7 D7 Gm7 C7 Fmaj7 C7'
AMEL = 'q. A5 e G5 q F5 e. E5 s F5 | h G5 h r | q. Bb5 e A5 q G5 e. F5 s G5 | h A5 h r | q C6 A5 q. F5 e G5 | q A5 G5 h E5 | q D5 E5 F5 G5 | w F5'
BMEL = 'h D6 q C6 Bb5 | h Db6 q Bb5 G5 | h C6 q A5 F5 | h F#5 q A5 C6 | h Bb5 q G5 D5 | h E5 q G5 Bb5 | w A5 | h G5 r'


def chacha(at, bars):
    claves.drums({60: 'x..x..x...x.x...'}, at=at, bars=bars, vel={'x': 78})
    bongo.drums({60: '..o.x.o.o.o.x.xx'}, at=at, bars=bars, vel={'x': 76, 'o': 50})
    guiro.drums({60: 'x...x...x...x.x.'}, at=at, bars=bars, vel={'x': 56})


def montuno(at, prog, vel=62):
    prev = None
    for k, sy in enumerate(prog.split()):
        ns = voice_lead(prev, chord(sy, 4), 57, 72); prev = ns
        r = root_of(sy, 2)
        cello.note(at + 4 * k, r + 12, 1.4, 86); cello.note(at + 4 * k + 1.5, r + 19 if r + 19 <= 52 else r + 7, 0.9, 76)
        cello.note(at + 4 * k + 3, r + 12, 0.5, 78); cello.note(at + 4 * k + 3.5, r + 12, 0.5, 74)
        for off in (0.5, 1.5, 2, 3, 3.5):
            for n in ns:
                piano.note(at + 4 * k + off, n, 0.35, vel)


t = 0.0
gong.note(0, 55, 6, 84); bird.note(3, 60, 2, 74)
marimba.chords('Fmaj7:4 C7:4', at=4, style='arp', vel=60, lo=60, hi=81, rhythm=0.25)
t = 12
chacha(t, 8); montuno(t, A); bells.mel(AMEL, at=t, vel=88)
t += 32
chacha(t, 8); montuno(t, A, 58); marimba.mel(AMEL, at=t, vel=78); strings.chords(A, at=t, beats=4, style='pad', vel=56, lo=55, hi=72)
t += 32
chacha(t, 8); montuno(t, B, 60); lead.mel(BMEL, at=t, vel=88, tr=-12); strings.chords(B, at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
bird.note(t + 30, 62, 2, 70)
t += 32
chacha(t, 8); montuno(t, A, 62); bells.mel(AMEL, at=t, vel=90); marimba.mel(AMEL, at=t, vel=64, tr=-12)
strings.chords(A, at=t, beats=4, style='pad', vel=56, lo=55, hi=72)
t += 32
# the bridge again on the marimba, then the tune for everyone
chacha(t, 8); montuno(t, B, 58); marimba.mel(BMEL, at=t, vel=84); bells.mel(BMEL, at=t + 16, vel=70, tr=12)
t += 32
chacha(t, 8); montuno(t, A, 64); bells.mel(AMEL, at=t, vel=92); lead.mel(AMEL, at=t, vel=74, tr=-12)
strings.chords(A, at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
t += 32
claves.mel('q C5 C5 e C5 C5 q r', at=t, vel=80); bells.mel('q A5 G5 e F5 F5 q r', at=t, vel=88)
piano.chords('F6:4', at=t + 4, style='pad', vel=70, lo=57, hi=74); cello.note(t + 4, pitch('F2') + 12, 4, 88)
gong.note(t + 4, 55, 6, 76)

S.humanize(ms=6, vel=4)
finish(__file__, S, {
    'title': 'Volcano View Cha-Cha',
    'pack': 'leisure',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A lounge cha-cha in F, 118 bpm: claves, bongo taps and a scrape on the cha-cha-cha, vibes-bells and '
            'marimba on the tune, the tiki piano montuno, cello bass, strings, a lead in the bridge, a gong and a robin.',
}, [
    ('bells', 'ch1', 'Soft Bells', dict(lufs=-20, pan=8, echo=0.2, verb=0.4)),
    ('piano', 'ch2', 'Tiki Lounge Piano', dict(lufs=-24, pan=-16, verb=0.3)),
    ('cello', 'ch3', 'Opal Section', dict(lufs=-21, verb=0.15)),
    ('strings', 'ch4', 'White Cellos', dict(lufs=-26, pan=14, verb=0.4, width=1.3)),
    ('lead', 'ch5', 'Granite Lead', dict(lufs=-21, pan=-6, echo=0.15, verb=0.35)),
    ('marimba', 'ch6', 'Mint Ballad', dict(lufs=-23, pan=-24, verb=0.3)),
    ('claves', 'ch7', 'Steel Block', dict(lufs=-26, pan=-32)),
    ('bongo', 'ch8', 'Twilight Tap', dict(lufs=-26, pan=30)),
    ('guiro', 'ch9', 'Grey Clack', dict(lufs=-29, pan=18)),
    ('gong', 'ch11', 'Cedar Gong', dict(lufs=-25, verb=0.5)),
    ('bird', 'ch12', 'Half-Speed Mockingbird', dict(lufs=-28, pan=38, verb=0.4)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '3/8', 'feedback': 0.3, 'tone': 2800, 'level': -6},
   reverb={'size': 2.4, 'predelay': 22, 'tone': 5000, 'level': -4})
