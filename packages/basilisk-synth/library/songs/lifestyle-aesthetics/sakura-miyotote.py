"""Sakura-Miyotote (a cherry-blossom song), Japanese traditional, as printed for koto in Osaka in 1895, arranged for the Lifestyle
Aesthetics Pack: the tune on kalimba and glass keyboard in an atrium, then over a slow city-pop groove with tines,
nylon guitar, a faraway choir and fountain coins, and back to the kalimba alone."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'JPM037-Sakura-Miyotote.mid'))
S = Score(bpm=110, seed=1895)
kalimba = S.part('kalimba', 1)
glass = S.part('glasskeys', 2)
tines = S.part('tines', 3)
nylon = S.part('nylon', 4)
bass = S.part('bass', 5)
choir = S.part('choir', 6)
pad = S.part('pad', 7)
coins = S.part('coins', 8)
kit = S.part('kit', 10)
marimba = S.part('marimba', 11)
pool = S.part('pool', 12)

L = src.bars() * src.bar
tune = src.tracks[0]
TR = 1   # E (the koto's tuning as printed) up to F for the band


def harmony(at, part, vel, lo=52, hi=67, step=4.0, style='pad'):
    syms = chords_of(beats(tune, 0, L, 0), 0, L, step)
    prev = None
    for i, sy in enumerate(syms):
        ns = voice_lead(prev, [n + TR for n in chord(sy, 4)], lo, hi); prev = ns
        if style == 'pad':
            for n in ns:
                part.note(at + i * step, n, step * 0.97, vel)
        else:
            for k in range(int(step * 2)):
                part.note(at + i * step + k * 0.5, ns[k % len(ns)] + (12 if k % 4 == 3 else 0), 0.45, vel)


def groove_bars(at, bars):
    for k in range(bars):
        kit.drums({KICK: 'x.......x.x.....', SNARE: '....x.......x...', CHH: 'x.x.x.x.x.x.x.x.'}, at=at + 4 * k, bars=1, swing=0.15)


t = 0.0
# 1: the tune alone on kalimba, glass keys an octave above on the long notes, the pool room
hold(pool, 0, 60, 8, 64)
put(kalimba, beats(tune, 0, L / 2, 4), tr=TR, vel=84)
for b, p, d, v in skyline(beats(tune, 0, L / 2, 4)):
    if d >= 1.0:
        glass.note(b, p + TR + 12, d, 56)
harmony(4, pad, 50)
t = 4 + L / 2
# 2: the band: tines on the tune, nylon arpeggios, bass, a slow groove
groove_bars(t, int(L // 4))
put(tines, skyline(beats(tune, 0, L, t)), tr=TR, vel=88)
harmony(t, nylon, 56, 55, 72, style='arp')
for i, sy in enumerate(chords_of(beats(tune, 0, L, 0), 0, L, 4.0)):
    r = root_of(sy, 2) + TR
    bass.note(t + 4 * i, r, 1.8, 92); bass.note(t + 4 * i + 2.5, r + 7, 1.0, 80)
coins.note(t + L - 3, 84, 2, 66)
t += L
# 3: everyone; the choir holds the chords, marimba doubles the tune an octave down
groove_bars(t, int(L // 4))
put(tines, skyline(beats(tune, 0, L, t)), tr=TR, vel=90); put(marimba, skyline(beats(tune, 0, L, t)), tr=TR - 12, vel=66)
harmony(t, nylon, 54, 55, 72, style='arp'); harmony(t, choir, 60, 55, 69)
for i, sy in enumerate(chords_of(beats(tune, 0, L, 0), 0, L, 4.0)):
    r = root_of(sy, 2) + TR
    bass.note(t + 4 * i, r, 1.8, 94); bass.note(t + 4 * i + 2.5, r + 7, 1.0, 82)
t += L
# end: the kalimba's last phrase, the fountain
put(kalimba, beats(tune, L - 8, L, t), tr=TR, vel=74)
coins.note(t + 2, 84, 2, 60)
hold(pool, t, 60, 12, 60)
t += 8
glass.note(t, pitch('F6'), 4, 60); kalimba.note(t, pitch('F4'), 4, 70)

S.humanize(ms=6, vel=4)
finish(__file__, S, {
    'title': 'Sakura-Miyotote',
    'pack': 'lifestyle-aesthetics',
    'kind': 'world',
    'composer': 'Japanese traditional',
    'source': 'Sakura-Miyotote, as printed for koto in Nagai and Obata, "Seiyo gakufu Nihon zokkyokushu" (Osaka: '
              'Miki Shoten, 1895). Score: The Mutopia Project.',
    'licence': 'The work: traditional, public domain. The edition used: public domain (Mutopia; the source was '
               'printed in 1895). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1971',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Kalimba and glass keyboard alone, then a slow city-pop groove with tines, nylon arpeggios, bass, choir and '
            'marimba, then the last phrase on kalimba. Moved up a semitone from the 1895 print. Drums: Kit Manager 98 '
            '(Echo Chamber Kit).',
}, [
    ('kalimba', 'ch1', 'Hydro Kalimba', dict(lufs=-20, pan=-8, echo=0.25, verb=0.35)),
    ('glasskeys', 'ch2', 'Glass Keyboard', dict(lufs=-25, pan=24, echo=0.3, verb=0.45)),
    ('tines', 'ch3', 'Atrium Keys', dict(lufs=-20, pan=6, echo=0.15, verb=0.3)),
    ('nylon', 'ch4', 'Food Court Nylon', dict(lufs=-24, pan=-22, verb=0.25)),
    ('bass', 'ch5', 'Slow Jam Bass', dict(lufs=-20)),
    ('choir', 'ch6', 'Faraway Choir', dict(lufs=-25, verb=0.5, width=1.3)),
    ('pad', 'ch7', 'Weather Map Pad', dict(lufs=-27, verb=0.4, width=1.3)),
    ('coins', 'ch8', 'Fountain Coins', dict(lufs=-26, pan=32, echo=0.3, verb=0.5)),
    ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', dict(lufs=-19, verb=0.1)),
    ('marimba', 'ch11', 'Droplet Marimba', dict(lufs=-25, pan=-30, echo=0.2, verb=0.3)),
    ('pool', 'ch12', 'Liminal Pool Room', dict(lufs=-29, width=1.3)),
], master={'loudness': -16, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.35, 'tone': 3200, 'level': -5},
   reverb={'size': 2.8, 'predelay': 24, 'tone': 5500, 'level': -4})
