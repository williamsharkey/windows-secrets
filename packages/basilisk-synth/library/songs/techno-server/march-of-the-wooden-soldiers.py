"""March of the Wooden Soldiers (P. I. Tchaikovsky, Album for the Young, Op. 39 No. 5, 1878), arranged for Techno
Server 4.0: the march three times over a four-to-the-floor kit, first as morse-code blips and dub chords, then on
the motor-whine lead with Detroit strings, then everything with the relay ticks."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', '05MarchOfTheWoodenSoldiers.mid'))
S = Score(bpm=126, seed=1878)
kit = S.part('kit', 10)
morse = S.part('morse', 1)
lead = S.part('lead', 2)
dub = S.part('dub', 3)
strings = S.part('strings', 4)
sub = S.part('sub', 5)
tick = S.part('tick', 6)
hat = S.part('hat', 7)
clap = S.part('clap', 8)
voice = S.part('voice', 9)
hum = S.part('hum', 11)

L = src.bars() * src.bar     # 96 beats
syms = chords_of(src.all, 0, L, 4.0)


def harmony(at, part=None, dubs=False, subs=True, vel=62):
    prev = None
    for i, sy in enumerate(syms):
        b = at + 4 * i
        if part:
            ns = voice_lead(prev, chord(sy, 4), 55, 70); prev = ns
            for n in ns:
                part.note(b, n, 3.9, vel)
        if dubs:
            r = root_of(sy, 4)
            for off in (0.5, 2.25):
                dub.note(b + off, r, 0.3, 84)
        if subs:
            r = root_of(sy, 2) + 12
            for k in range(4):
                sub.note(b + k + 0.5, r, 0.42, 98)


def beat(at, bars, full=True):
    groove(kit, 'techno', at, bars, drop=() if full else (CLAP, RIM))
    hat.drums({60: '..x...x...x...x.'}, at=at, bars=bars, vel={'x': 76})


t = 0.0
hold(hum, 0, 54, 32, 74)
beat(16, 4, full=False)
t = 32
# pass 1: morse blips on the tune, dub chords
beat(t, int(L // 4)); harmony(t, dubs=True)
put(morse, skyline(beats(src.tracks[0], 0, L, t)), vel=86, lo=62, hi=84)
t += L
# pass 2: the motor-whine lead, strings, claps
voice.note(t - 6, 60, 6, 90)
beat(t, int(L // 4)); harmony(t, part=strings, dubs=True)
put(lead, skyline(beats(src.tracks[0], 0, L, t)), vel=92, lo=62, hi=84)
clap.drums({60: '....x.......x...'}, at=t, bars=int(L // 4), vel={'x': 80})
t += L
# break: strings and the hum, the dub chord alone
for i, sy in enumerate(syms[-4:]):
    strings.chords(sy + ':4', at=t + 4 * i, style='pad', vel=68, lo=55, hi=70)
    dub.note(t + 4 * i + 0.5, root_of(sy, 4), 0.3, 84)
hold(hum, t, 54, 16, 70)
put(morse, skyline(beats(src.tracks[0], L - 16, L, t)), vel=70, lo=62, hi=84)
t += 16
# pass 3: everything, ticks, the lead an octave up on the second half
kit.note(t, CRASH, 2, 110)
beat(t, int(L // 4)); harmony(t, part=strings, dubs=True)
put(lead, skyline(beats(src.tracks[0], 0, L, t)), vel=94, lo=62, hi=84)
put(morse, skyline(beats(src.tracks[0], L / 2, L, t + L / 2)), tr=12, vel=72, lo=74, hi=96)
tick.drums({67: '..o...x...o..x.o'}, at=t, bars=int(L // 4), vel={'x': 72, 'o': 50})
clap.drums({60: '....x.......x...'}, at=t, bars=int(L // 4), vel={'x': 84})
t += L
beat(t, 4, full=False); hold(hum, t, 54, 20, 68)
dub.note(t + 16, pitch('D4'), 0.4, 86); kit.note(t + 16, KICK, 1, 104)

finish(__file__, S, {
    'title': 'March of the Wooden Soldiers',
    'pack': 'techno-server',
    'kind': 'world',
    'composer': 'Pyotr Ilyich Tchaikovsky (1840-1893)',
    'source': 'March of the Wooden Soldiers, Album for the Young, Op. 39 No. 5 (1878). Score: The Mutopia Project, '
              'from Schirmer (1904).',
    'licence': 'The work: public domain (published 1878; the composer died 1893). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1806',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Techno at 126 bpm: the march three times, on morse blips with dub chords, then the motor-whine lead with '
            'Detroit strings, then everything with relay ticks; a transmission before the second pass. Drums: Kit '
            'Manager 98 (Long Boom Kit).',
}, [
    ('kit', 'ch10', 'kit-manager:Long Boom Kit', dict(lufs=-16.5, verb=0.04)),
    ('morse', 'ch1', 'Granite Line', dict(lufs=-21, pan=-12, echo=0.4, verb=0.15)),
    ('lead', 'ch2', 'Soft Pilot', dict(lufs=-20, pan=8, echo=0.3, verb=0.2)),
    ('dub', 'ch3', 'One-Finger Dub Chord', dict(lufs=-22, pan=-6, echo=0.55, verb=0.25)),
    ('strings', 'ch4', 'Motor City Strings', dict(lufs=-24, pan=14, verb=0.35, width=1.3)),
    ('sub', 'ch5', 'Dot Sub', dict(lufs=-19)),
    ('tick', 'ch6', 'Relay Wood Tick', dict(lufs=-28, pan=30, echo=0.25)),
    ('hat', 'ch7', 'Copper Hat', dict(lufs=-28, pan=18)),
    ('clap', 'ch8', 'Indigo Clap', dict(lufs=-26, pan=-6, verb=0.2)),
    ('voice', 'ch9', 'Transmission Voice', dict(lufs=-22, echo=0.3, verb=0.3)),
    ('hum', 'ch11', 'Dusk Texture', dict(lufs=-30, verb=0.2)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.5, 'tone': 2400, 'level': -3, 'lowcut': 250},
   reverb={'size': 2.2, 'predelay': 20, 'tone': 4500, 'level': -6})
