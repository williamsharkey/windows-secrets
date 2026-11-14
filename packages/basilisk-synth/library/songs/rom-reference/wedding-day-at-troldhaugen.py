"""Wedding Day at Troldhaugen (Edvard Grieg, Lyric Pieces Op. 65 No. 6, 1896), arranged for the ROM Reference
Library as late-80s workstation pop: the procession on brass stabs and a soaring lead, the left hand on a slap
bass line and piano, string swells, gamelan and harp runs, a vocal pad, then the procession's return."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'troldhaugen.mid'))
S = Score(bpm=116, seed=1896)
lead = S.part('lead', 1)
brass = S.part('brass', 2)
piano = S.part('piano', 3)
bass = S.part('bass', 4)
strings = S.part('strings', 5)
gamelan = S.part('gamelan', 6)
harp = S.part('harp', 7)
vox = S.part('vox', 8)
organ = S.part('organ', 9)
kit = S.part('kit', 10)

CUT = 48
rh = beats(src.tracks[0], 0, CUT * 4, 0); lhn = beats(src.tracks[1], 0, CUT * 4, 0)
top = skyline(rh)
put(lead, top, vel=92, lo=60, hi=86)
put(brass, [n for n in rh if n not in top], vel=74, lo=55, hi=76)
low = floor(lhn)
put(bass, low, vel=94, lo=33, hi=52)
put(piano, [n for n in lhn if n not in low], vel=62, lo=48, hi=72)
arrange(src, 16 * 4, CUT * 4, 16 * 4, pad=strings, rh_track=0, lh_track=1, pad_range=(55, 72), vel=56)
arrange(src, 0, 16 * 4, 0, pad=vox, rh_track=0, lh_track=1, pad_range=(55, 70), vel=52)
syms = chords_of(rh + lhn, 0, CUT * 4, 4.0)
for i, sy in enumerate(syms):
    if 24 <= i < 40:
        gamelan.chords(sy + ':4', at=4 * i, style='arp', vel=52, lo=64, hi=84, rhythm=0.5)
    if i % 8 == 7:
        harp.chords(sy + ':4', at=4 * i, style='arp', vel=60, lo=60, hi=86, rhythm=0.25)
groove(kit, 'synthpop', 8 * 4, 39, extra={OHH: '..............x.'})
groove(kit, 'synthpop', 47 * 4, 1, fill=True)
# the return: the last eight bars of the piece
end = src.bars() * 4.0
t = CUT * 4
arrange(src, end - 32, end, t, lead=lead, inner=brass, lh=piano, bass=bass, pad=strings, rh_track=0, lh_track=1,
        lead_range=(60, 86), inner_range=(55, 76), lh_range=(48, 72), bass_range=(33, 52), pad_range=(55, 72), vel=60)
groove(kit, 'synthpop', t, 7); kit.note(t, CRASH, 2, 108)
organ.chords('D:8', at=t + 24, style='pad', vel=60, lo=55, hi=72)
kit.note(t + 32, KICK, 1, 104)

S.humanize(ms=4, vel=4, parts=['lead', 'piano', 'brass'])
finish(__file__, S, {
    'title': 'Wedding Day at Troldhaugen',
    'pack': 'rom-reference',
    'kind': 'world',
    'composer': 'Edvard Grieg (1843-1907)',
    'source': 'Wedding Day at Troldhaugen, Lyric Pieces Op. 65 No. 6 (1896): bars 1-48 and the last eight bars. '
              'Score: The Mutopia Project, from Schirmer (1903).',
    'licence': 'The work: public domain (published 1896; the composer died 1907). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=781',
    'arranger': 'Algorithmic Industries house band',
    'note': 'Late-80s workstation pop at 116 bpm: the tune on a lead over brass stabs, the left hand on bass and '
            'piano, a vocal pad then string swells, gamelan and harp runs, an organ on the last chord. Drums: Kit '
            'Manager 98 (Breaker Box Kit).',
}, [
    ('lead', 'ch1', 'Cathode Lead', dict(lufs=-19, pan=4, echo=0.2, verb=0.35)),
    ('brass', 'ch2', 'Lunar Brass', dict(lufs=-23, pan=16, verb=0.25)),
    ('piano', 'ch3', 'Lagoon Piano', dict(lufs=-23, pan=-18, verb=0.3)),
    ('bass', 'ch4', 'Neon Basement', dict(lufs=-20)),
    ('strings', 'ch5', 'Blue Swell', dict(lufs=-24, pan=-10, verb=0.4, width=1.3)),
    ('gamelan', 'ch6', 'Hazy Gamelan', dict(lufs=-26, pan=-26, echo=0.3, verb=0.3)),
    ('harp', 'ch7', 'Copper Harp', dict(lufs=-26, pan=30, echo=0.2, verb=0.35)),
    ('vox', 'ch8', 'Slate Vox', dict(lufs=-26, verb=0.45, width=1.3)),
    ('organ', 'ch9', 'Pastel Bark', dict(lufs=-26, pan=24, verb=0.2)),
    ('kit', 'ch10', 'kit-manager:Breaker Box Kit', dict(lufs=-18, verb=0.12)),
], master={'loudness': -15, 'ceiling': -1.0},
   echo={'time': '3/16', 'feedback': 0.32, 'tone': 3500, 'level': -5},
   reverb={'size': 2.6, 'predelay': 20, 'tone': 6000, 'level': -4})
