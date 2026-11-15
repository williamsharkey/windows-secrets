"""Toccata and Fugue in D minor, BWV 565 (attributed to J. S. Bach), arranged for the Polysynth Showroom: the
toccata on big poly brass and an FM piano over a cream mono pedal bass, then the fugue's opening with drums, the
vocoder choir and string swells, ending on the toccata's last chord."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'ToccataFugue.mid'))
S = Score(bpm=76, seed=565)
brass = S.part('brass', 1)
fm = S.part('fmpiano', 2)
lh = S.part('lefthand', 3)
pedal = S.part('pedal', 4)
choir = S.part('vchoir', 5)
strings = S.part('vstrings', 6)
lead = S.part('lead', 7)
kit = S.part('kit', 10)
hit = S.part('hit', 11)

TOC, FUG = 30, 44   # bars: the toccata, then the fugue's first fourteen bars
rh_, lh_, ped_ = src.tracks[0], src.tracks[1], src.tracks[2]

# the toccata
put(brass, beats(rh_, 0, TOC * 4, 0), vel=96, lo=48, hi=88)
put(fm, beats(rh_, 0, TOC * 4, 0), tr=12, vel=70, lo=60, hi=96)
put(lh, beats(lh_, 0, TOC * 4, 0), vel=84, lo=38, hi=72)
put(pedal, beats(ped_, 0, TOC * 4, 0), vel=100, lo=26, hi=50)
for b, p, d, v in beats(ped_, 0, TOC * 4, 0):   # the big chords get a brass hit
    if d >= 2:
        hit.note(b, p + 24, 0.6, 96)
arrange(src, 32, TOC * 4, 32, pad=strings, rh_track=0, lh_track=1, pad_range=(50, 67), vel=56)
# the fugue: the lead takes the subject, drums, the choir
a, b = TOC * 4, FUG * 4
put(lead, beats(rh_, a, b, a), vel=94, lo=55, hi=84)
put(fm, beats(rh_, a, b, a), vel=64, lo=60, hi=88)
put(lh, beats(lh_, a, b, a), vel=82, lo=40, hi=72)
put(pedal, beats(ped_, a, b, a), vel=100, lo=26, hi=50)
arrange(src, a, b, a, pad=choir, rh_track=0, lh_track=1, pad_range=(53, 69), vel=60)
groove(kit, 'synthpop', a + 16, 9, extra={CLAP: '....x.......x...'})
groove(kit, 'synthpop', a + 52, 1, fill=True)
kit.note(a + 16, CRASH, 2, 108)
# the last chord: D minor, held, with the toccata's opening turn on top
t = b
lead.mel('z A5 G5 h. A5', at=t, vel=96)
for p, lo, hi, v in ((brass, 50, 74, 100), (strings, 50, 69, 70), (choir, 53, 69, 66)):
    p.chords('Dm:8', at=t, style='pad', vel=v, lo=lo, hi=hi)
pedal.note(t, pitch('D2'), 8, 104); kit.note(t, KICK, 1, 110); kit.note(t, CRASH, 3, 110); hit.note(t, pitch('D5'), 1, 100)

finish(__file__, S, {
    'title': 'Toccata in D Minor',
    'pack': 'polysynth-showroom',
    'kind': 'world',
    'composer': 'Johann Sebastian Bach (1685-1750), attributed',
    'source': 'Toccata and Fugue in D minor, BWV 565: the toccata and the fugue\'s first fourteen bars. Score: The '
              'Mutopia Project, from the Bach-Gesellschaft Ausgabe (1867).',
    'licence': 'The work: public domain (18th century). The edition used: public domain (Mutopia). This arrangement: '
               'CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1780',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The toccata on poly brass and FM piano over a mono pedal bass with brass hits, string swells; the '
            'fugue\'s opening with a PWM lead, drums and the vocoder choir; the last D minor chord. Drums: Kit '
            'Manager 98 (Breaker Box Kit).',
    'tail': 5,
}, [
    ('brass', 'ch1', 'Radiant Salute', dict(lufs=-19, pan=-8, verb=0.35, width=1.2)),
    ('fmpiano', 'ch2', 'Stone Parlour', dict(lufs=-24, pan=18, echo=0.1, verb=0.3)),
    ('lefthand', 'ch3', 'Lucid Herald', dict(lufs=-22, pan=-18, verb=0.3)),
    ('pedal', 'ch4', 'Ivory Low', dict(lufs=-20, verb=0.15)),
    ('vchoir', 'ch5', 'Static Chorus', dict(lufs=-25, verb=0.5, width=1.3)),
    ('vstrings', 'ch6', 'Upper Ensemble', dict(lufs=-25, pan=10, verb=0.45, width=1.3)),
    ('lead', 'ch7', 'Silent Ray', dict(lufs=-20, pan=4, echo=0.2, verb=0.3)),
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-18, verb=0.15)),
    ('hit', 'ch11', 'Lucid Herald', dict(lufs=-24, verb=0.4)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
   reverb={'size': 3.2, 'predelay': 25, 'tone': 5500, 'level': -3})
