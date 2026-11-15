"""Demo Mode, Aisle 7: an original 1985 power ballad, 76 bpm, A-flat major. FM piano verses, the vocoder choir,
gasflower pads, a big brass chorus with gated drums, a buzzy lead solo and a key change for the last chorus."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=76, seed=1985)
kit = S.part('kit', 10)
piano = S.part('fmpiano', 1)
bass = S.part('bass', 2)
pad = S.part('pad', 3)
vchoir = S.part('vchoir', 4)
brass = S.part('brass', 5)
lead = S.part('lead', 6)
solo = S.part('solo', 7)
strings = S.part('strings', 8)
bells = S.part('bells', 9)

V = 'Ab Eb/G Fm Db Ab Eb Db Eb'
C = 'Db Eb Cm Fm Db Eb Ab Ab'
VMEL = 'q. C5 e Bb4 q Ab4 Eb4 | h. G4 q Ab4 | q. C5 e Db5 q C5 Ab4 | w F4 | q. C5 e Bb4 q Ab4 C5 | h. Eb5 q C5 | q Db5 C5 Bb4 Ab4 | w Bb4'
CMEL = 'h F5 q Eb5 Db5 | h G5 q F5 Eb5 | h Eb5 q C5 Bb4 | w C5 | h F5 q Eb5 Db5 | h Bb5 q Ab5 G5 | w Ab5 | h. r q r'


def band(at, prog, tr=0, drums=True, vel=96):
    p = ' '.join(prog.split())
    bass.bass(p, at=at, beats=4, pattern=[(0, 0, 1.8), (2, 0, 0.9), (3, '5', 0.9)], vel=vel)
    if drums:
        for k in range(8):
            kit.drums({KICK: 'x.......x.x.....', SNARE: '....x.......x...' if k != 7 else '....x.......xxxx', CHH: 'x.x.x.x.x.x.x.x.'},
                      at=at + 4 * k, bars=1)


def tr_prog(prog, n):
    names = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
    out = []
    for sy in prog.split():
        def mv(s):
            m = re.match(r'^([A-G][b#]?)(.*)$', s)
            return names[(pitch(m.group(1) + '4') + n) % 12] + m.group(2)
        out.append('/'.join(mv(x) for x in sy.split('/')))
    return ' '.join(out)


t = 0.0
piano.chords('Ab Db Ab Eb', at=0, beats=4, style='arp', vel=60, lo=56, hi=80, rhythm=0.5)
bells.note(12, pitch('Eb6'), 3, 64)
t = 16
band(t, V, drums=False); piano.chords(V, at=t, beats=4, style='block', vel=62, lo=55, hi=72, rhythm=[(0, 1.8), (2, 1.8)])
vchoir.mel(VMEL, at=t, vel=86); pad.chords(V, at=t, beats=4, style='pad', vel=52, lo=53, hi=70)
t += 32
kit.note(t, CRASH, 2, 108)
band(t, C); brass.chords(C, at=t, beats=4, style='pad', vel=76, lo=55, hi=72); lead.mel(CMEL, at=t, vel=94)
strings.chords(C, at=t, beats=4, style='pad', vel=58, lo=55, hi=72)
t += 32
band(t, V); piano.chords(V, at=t, beats=4, style='block', vel=62, lo=55, hi=72, rhythm=[(0, 1.8), (2, 1.8)])
solo.mel('e C5 Eb5 Ab5 C6 q Bb5 Ab5 | h. G5 q Eb5 | e F5 Ab5 C6 Db6 q C6 Ab5 | h F5 q r e F5 G5 | '
         'e Ab5 G5 Ab5 C6 q Eb6 C6 | h. Bb5 q G5 | q Ab5 Bb5 C6 Db6 | w Eb6', at=t, vel=92)
pad.chords(V, at=t, beats=4, style='pad', vel=54, lo=53, hi=70)
t += 32
# last chorus up a tone
C2 = tr_prog(C, 2)
kit.note(t, CRASH, 2, 112)
band(t, C2, vel=100); brass.chords(C2, at=t, beats=4, style='pad', vel=80, lo=57, hi=74); lead.mel(CMEL, at=t, vel=98, tr=2)
vchoir.mel(CMEL, at=t, vel=78, tr=-10); strings.chords(C2, at=t, beats=4, style='pad', vel=60, lo=57, hi=74)
t += 32
for p, lo, hi, v in ((brass, 57, 74, 84), (strings, 57, 74, 64), (pad, 55, 72, 56), (piano, 55, 79, 66)):
    p.chords('Bb:8', at=t, style='pad', vel=v, lo=lo, hi=hi)
bass.note(t, pitch('Bb1') + 12, 8, 96); kit.note(t, CRASH, 3, 108); bells.note(t + 2, pitch('F6'), 4, 66)

S.humanize(ms=4, vel=4, parts=['fmpiano', 'vchoir', 'lead', 'solo'])
finish(__file__, S, {
    'title': 'Demo Mode, Aisle 7',
    'pack': 'polysynth-showroom',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement)',
    'note': 'A 1985 power ballad in A-flat, 76 bpm: FM piano verses, the female vocoder on the verse, gasflower pads, '
            'big poly brass and a lead on the chorus, string swells, a buzzy solo, the last chorus up a tone. Drums: '
            'Kit Manager 98 (Breaker Box Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-17, verb=0.2)),
    ('fmpiano', 'ch1', 'Mild Chords', dict(lufs=-21, pan=-14, verb=0.3)),
    ('bass', 'ch2', 'Inland Floor', dict(lufs=-20)),
    ('pad', 'ch3', 'Ultra Pad', dict(lufs=-26, verb=0.4, width=1.3)),
    ('vchoir', 'ch4', 'Rose Breath', dict(lufs=-20, pan=4, verb=0.4)),
    ('brass', 'ch5', 'Azure Horns', dict(lufs=-22, pan=10, verb=0.3, width=1.2)),
    ('lead', 'ch6', 'Molten Ray', dict(lufs=-20, pan=-4, echo=0.2, verb=0.3)),
    ('solo', 'ch7', 'Electric Pilot', dict(lufs=-20, pan=6, echo=0.25, verb=0.3)),
    ('strings', 'ch8', 'Upper Ensemble', dict(lufs=-25, pan=-16, verb=0.4, width=1.3)),
    ('bells', 'ch9', 'Mild Lounge', dict(lufs=-26, pan=28, echo=0.3, verb=0.4)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.32, 'tone': 3200, 'level': -5},
   reverb={'size': 2.8, 'predelay': 22, 'tone': 5500, 'level': -3})
