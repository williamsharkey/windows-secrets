"""In the Hall of the Mountain King (Edvard Grieg, Peer Gynt, 1875), arranged for the Game Port Sound Set as a
chiptune: the theme creeps in on a pulse bass, climbs through square leads and chord arpeggios, speeds up all the
way, and ends with the coin."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
src = Source(os.path.join(HERE, '..', 'sources', 'Dans_l_antre_du_roi_de_la_montagne.mid'))
S = Score(bpm=96, seed=1875)
lead = S.part('lead', 1)
lead2 = S.part('lead2', 2)
arp = S.part('arp', 3)
bass = S.part('bass', 4)
kick = S.part('kick', 5)
snare = S.part('snare', 6)
hat = S.part('hat', 7)
coin = S.part('coin', 8)
boot = S.part('boot', 9)
riser = S.part('riser', 11)

N = src.bars()
# the tempo climbs: 96 to 200 bpm over the piece, a bar at a time, as the orchestra does
for k in range(N):
    S.tempo(k * 4.0, 96 + (200 - 96) * (k / (N - 1)) ** 1.6)
boot.note(0, 41, 6, 90)
for k in range(N):
    a, b = k * 4.0, k * 4.0 + 4
    rh = beats(src.tracks[0], a, b, a); lhn = beats(src.tracks[1], a, b, a)
    top = skyline(rh)
    if k < 16:            # the theme low, on the bass alone
        put(bass, floor(lhn or rh), vel=100, lo=36, hi=55)
    elif k < 32:          # the square lead takes it, the bass keeps time
        put(lead2, top, vel=88, lo=55, hi=79); put(bass, floor(lhn), vel=100, lo=36, hi=55)
    else:                 # everyone, the lead an octave up, chord arpeggios
        put(lead, top, vel=96, lo=67, hi=91); put(lead2, top, vel=74, lo=55, hi=79)
        put(bass, floor(lhn), vel=104, lo=36, hi=55)
        sy = chords_of(rh + lhn, a, b, 2.0)
        for i, s in enumerate(sy):
            ns = chord(s, 5)
            for j in range(8):
                arp.note(a + 2 * i + j * 0.25, ns[j % len(ns)] + (12 if j >= 4 else 0), 0.2, 62)
    if k >= 8:
        kick.drums({48: 'x...x...x...x...'}, at=a, bars=1, vel={'x': 100})
    if k >= 24:
        snare.drums({60: '....x.......x...' if k < 56 else '....x..x....x.xx'}, at=a, bars=1, vel={'x': 90})
    if k >= 16:
        hat.drums({60: 'x.x.x.x.x.x.x.x.' if k < 48 else 'xxxxxxxxxxxxxxxx'}, at=a, bars=1, vel={'x': 58})
riser.note((N - 8) * 4.0, 60, 32, 86)
t = N * 4.0
lead.mel('q B5 r B4 r | w B3', at=t, vel=100); bass.note(t, pitch('B1') + 12, 6, 104)
kick.note(t, 48, 0.5, 110); snare.note(t, 60, 0.5, 100); coin.note(t + 4, 72, 1, 90)

finish(__file__, S, {
    'title': 'In the Hall of the Mountain King',
    'pack': 'game-port',
    'kind': 'world',
    'composer': 'Edvard Grieg (1843-1907)',
    'source': 'In the Hall of the Mountain King, Peer Gynt Suite No. 1, Op. 46 No. 4 (1875), piano version. Score: '
              'The Mutopia Project, from The University Society (1918).',
    'licence': 'The work: public domain (composed 1875; the composer died 1907). The edition used: public domain '
               '(Mutopia). This arrangement: CC0-1.0.',
    'proof': 'https://www.mutopiaproject.org/cgibin/piece-info.cgi?id=1888',
    'arranger': 'Algorithmic Industries house band',
    'note': 'A chiptune: the theme on a pulse bass, then square leads and chord arpeggios over noise drums, the tempo '
            'climbing from 96 to 200 bpm, a 286 boot at the start and a coin at the end.',
}, [
    ('lead', 'ch1', 'Midnight Signal', dict(lufs=-20, pan=-6, echo=0.12, verb=0.1)),
    ('lead2', 'ch2', 'Second Ray', dict(lufs=-21, pan=20, echo=0.12)),
    ('arp', 'ch3', 'Lucid Line', dict(lufs=-26, pan=-24)),
    ('bass', 'ch4', 'Waxed Line', dict(lufs=-19)),
    ('kick', 'ch5', 'Silver Block', dict(lufs=-21)),
    ('snare', 'ch6', 'Chrome Snap', dict(lufs=-23)),
    ('hat', 'ch7', 'Slate Tick', dict(lufs=-29, pan=18)),
    ('coin', 'ch8', 'Coin Jingle', dict(lufs=-24, echo=0.2)),
    ('boot', 'ch9', 'Digital Sweep', dict(lufs=-24, verb=0.2)),
    ('riser', 'ch11', 'Kinetic Riser', dict(lufs=-27, verb=0.3)),
], master={'loudness': -14, 'ceiling': -1.0},
   echo={'time': '1/8', 'feedback': 0.25, 'tone': 4000, 'level': -7},
   reverb={'size': 1.2, 'predelay': 10, 'tone': 6000, 'level': -9})
