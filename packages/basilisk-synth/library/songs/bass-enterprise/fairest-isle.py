"""Fairest Isle (Henry Purcell, King Arthur, 1691), arranged for the Bass Enterprise Edition as UK garage in a 6/8
shuffle: the air on a trombone hook, the inner voices on the organ chord, the bass voice on the 2-step organ
bass and a sub, a skipping kit; a speed-garage turn on the wobbling sub for the second time through."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'FairestIsle.mid'))
S = Score(bpm=132, seed=1691)
kit = S.part('kit', 10)
horn = S.part('horn', 1)
chordp = S.part('chord', 2)
obass = S.part('organbass', 3)
sub = S.part('sub', 4)
wob = S.part('wobble', 5)
vowel = S.part('vowel', 6)
fx = S.part('fx', 7)
doom = S.part('doom', 8)
gtr = S.part('bassgtr', 9)
stab = S.part('stab', 11)

L = src.bars() * 3.0
sop, alt, ten, bas = src.tracks


def shuffle(at, beats_len, four=False):
    for k in range(int(beats_len // 6)):
        b = at + 6 * k
        if four:
            kit.drums({KICK: 'x.....x.....', SNARE: '...x.....x..', CHH: 'x.xx.xx.xx.x', OHH: '..x.....x...'}, at=b, bars=1,
                      step=0.5, beats_per_bar=6.0)
        else:
            kit.drums({KICK: 'x....x..x...', SNARE: '...x.....x..', CHH: '.x.xx..x.xx.', RIM: '..o.....o..o'}, at=b, bars=1,
                      step=0.5, beats_per_bar=6.0, vel={'x': 96, 'o': 56})


def voices(at, lead=horn, bassp=obass, vel=92):
    put(lead, beats(sop, 0, L, at), vel=vel, lo=60, hi=81)
    for b, p, d, v in beats(alt + ten, 0, L, at):
        chordp.note(b, p, min(d, 1.4), 64)
    for b, p, d, v in beats(bas, 0, L, at):
        n = p
        while n > 50:
            n -= 12
        bassp.note(b, n, min(d, 1.0), 98)
        sub.note(b, n - 12 if n - 12 >= 28 else n, d, 84)


t = 0.0
vowel.chords(' '.join(chords_of(src.all, 0, 24, 6.0)), at=0, beats=6, style='pad', vel=60, lo=53, hi=67)
fx.note(16, 60, 8, 84)
kit.drums({CHH: '.x.xx..x.xx.'}, at=12, bars=2, step=0.5, beats_per_bar=6.0)
t = 24
doom.note(t, 24, 3, 100)
shuffle(t, L); voices(t)
t += L
# breakdown: the vowel and the bass guitar on the bass voice, the stab on the downbeats
vowel.chords(' '.join(chords_of(src.all, 0, 48, 6.0)), at=t, beats=6, style='pad', vel=62, lo=53, hi=67)
put(gtr, beats(bas, 0, 48, t), vel=94, lo=36, hi=55)
for k in range(8):
    stab.note(t + 6 * k, 62, 0.3, 80)
fx.note(t + 40, 60, 8, 86)
kit.drums({SNARE: '...x.....x..', CHH: 'x.x.x.x.x.x.'}, at=t, bars=8, step=0.5, beats_per_bar=6.0)
t += 48
# second time: four to the floor, the wobble
doom.note(t, 24, 3, 104); kit.note(t, CRASH, 2, 110)
shuffle(t, L, four=True); voices(t, bassp=wob, vel=96)
t += L
horn.note(t, pitch('Bb4'), 3, 92); chordp.chords('Bb:6', at=t, style='pad', vel=66, lo=55, hi=70)
obass.note(t, pitch('Bb2'), 3, 98); kit.note(t, KICK, 1, 104); doom.note(t, 24, 3, 92)

S.humanize(ms=3, vel=4, parts=['horn', 'chord', 'bassgtr'])
finish(__file__, S, {
    'title': 'Fairest Isle',
    'pack': 'bass-enterprise',
    'kind': 'world',
    'composer': 'Henry Purcell (1659-1695)',
    'source': 'Fairest Isle, from King Arthur (1691), as a four-part setting. Score: The Mutopia Project.',
    'licence': 'The work: public domain (17th century). The edition used: public domain (Mutopia). This arrangement: '
               'CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=268',
    'arranger': 'Algorithmic Industries house band',
    'note': 'UK garage at 132 bpm in a 6/8 shuffle: the air on a trombone hook, inner voices on the organ chord, the '
            'bass voice on the 2-step organ bass and a sub, a bass-guitar breakdown, then four to the floor on the '
            'wobbling sub. Drums: Kit Manager 98 (Half-Time Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Half-Time Kit', dict(lufs=-17, verb=0.05)),
    ('horn', 'ch1', 'Lattice Accent', dict(lufs=-20, pan=12, echo=0.2, verb=0.2)),
    ('chord', 'ch2', 'Golden Chord', dict(lufs=-24, pan=-16, verb=0.25)),
    ('organbass', 'ch3', 'Organ Bass 2-Step', dict(lufs=-19)),
    ('sub', 'ch4', 'Floor Rumble', dict(lufs=-25)),
    ('wobble', 'ch5', 'Wobbly Speed Sub', dict(lufs=-19)),
    ('vowel', 'ch6', 'Marble Vowel', dict(lufs=-25, verb=0.4, width=1.3)),
    ('fx', 'ch7', 'Cedar Ascent', dict(lufs=-26, verb=0.4)),
    ('doom', 'ch8', 'Impact Doom', dict(lufs=-24, verb=0.3)),
    ('bassgtr', 'ch9', 'Ocean Bass', dict(lufs=-20)),
    ('stab', 'ch11', 'Federal Punch', dict(lufs=-25, pan=-10, echo=0.25)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3000, 'level': -4},
   reverb={'size': 1.6, 'predelay': 12, 'tone': 5500, 'level': -7})
