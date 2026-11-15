"""A Basin Away: an original deep-ocean ambient piece, 60 bpm, D minor, from hydrophone recordings. The bloop and an
iceberg in the dark, then fin-whale and blue-whale drones in slow chords, a humpback singing a line, the upsweep,
a ship passing overhead, and the tremor."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *
chord_cap(8)   # rendered before render311 --lookahead: chords thinned to 8 recorders an instant (_lib.cap_chords)

S = Score(bpm=60, seed=1997)
fin = S.part('fin', 1)
blue = S.part('blue', 2)
bowl = S.part('bowl', 3)
hump = S.part('humpback', 4)
bloop = S.part('bloop', 5)
ice = S.part('iceberg', 6)
sweep = S.part('upsweep', 7)
ship = S.part('ship', 8)
tremor = S.part('tremor', 9)
nets = S.part('nets', 11)
murmur = S.part('murmur', 12)
dive = S.part('dive', 13)

EVERY = 12


def drone_chord(at, beats, fin_note, blue_note, bowl_note=None, vel=72):
    hold(fin, at, fin_note, beats, vel, EVERY)
    hold(blue, at + 2, blue_note, beats - 2, vel - 6, EVERY)
    if bowl_note:
        hold(bowl, at + 4, bowl_note, beats - 4, vel - 10, EVERY)


t = 0.0
# 1. the dark (24 s): bloop, iceberg, a far ship
bloop.note(0, 19, 6, 90); bloop.note(10, 17, 6, 84)
ice.note(4, 17, 8, 86)
hold(murmur, 0, 60, 24, 60)
nets.note(16, 30, 6, 76)
t = 24
# 2. the drones gather (32 s): Dm, then Bb
drone_chord(t, 16, 50, 62, 74)
drone_chord(t + 16, 16, 46, 58, 77)
sweep.note(t + 6, 60, 4, 80); sweep.note(t + 22, 63, 4, 76)
bloop.note(t + 12, 19, 6, 80)
t += 32
# 3. the humpback (48 s): a slow line over F, C, Dm, Bb, Gm, A
prog = [(53, 65, 72), (48, 60, 79), (50, 62, 77), (46, 58, 74), (43, 55, 74), (45, 57, 73)]
for i, (f, b, w) in enumerate(prog):
    drone_chord(t + 8 * i, 8, f, b, w, 70)
hump.mel('h. A4 q C5 | w D5 | h C5 A4 | w G4 | h. F4 q G4 | w A4 | h Bb4 A4 | w F4 | '
         'h. G4 q Bb4 | w A4 | h G4 E4 | w C#4', at=t, vel=84)
sweep.note(t + 18, 60, 4, 76); dive.note(t + 30, 60, 5, 70)
ice.note(t + 40, 17, 8, 80)
t += 48
# 4. the ship overhead (24 s): everything, the tremor under it
ship.note(t, 33, 14, 88); tremor.note(t + 8, 41, 8, 90)
drone_chord(t, 12, 50, 62, 74, 78)
drone_chord(t + 12, 12, 46, 58, 70, 76)
hump.mel('h. D5 q F5 | w E5 | h D5 C5 | w D5 | h. Bb4 q A4 | w A4', at=t, vel=86)
sweep.note(t + 4, 65, 4, 80); sweep.note(t + 14, 60, 4, 74)
t += 24
# 5. back down (20 s): one D drone, the bloop, the nets
drone_chord(t, 16, 50, 62, None, 66)
bloop.note(t + 4, 19, 6, 78); nets.note(t + 10, 30, 6, 70)
hold(murmur, t, 60, 18, 56)
t += 20

finish(__file__, S, {
    'title': 'A Basin Away',
    'pack': 'listening-post',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement); the hydrophone recordings are NOAA PMEL\'s (public domain)',
    'note': 'Deep-ocean ambient in D minor, 60 bpm: the bloop and an iceberg calving, fin-whale and blue-whale drones '
            'in slow chords with a singing bowl, a humpback singing a line, the upsweep, a ship overhead and a tremor.',
    'tail': 8,
}, [
    ('fin', 'ch1', 'Dial Depth', dict(lufs=-23, pan=-14, verb=0.4)),
    ('blue', 'ch2', 'Lattice Dormant', dict(lufs=-24, pan=14, verb=0.4)),
    ('bowl', 'ch3', 'Saffron Dormant', dict(lufs=-28, verb=0.5)),
    ('humpback', 'ch4', 'Ocean Shoreline', dict(lufs=-21, pan=4, echo=0.25, verb=0.5)),
    ('bloop', 'ch5', 'Cedar Murmur', dict(lufs=-23, verb=0.4)),
    ('iceberg', 'ch6', 'Swift Room', dict(lufs=-24, pan=-24, verb=0.5)),
    ('upsweep', 'ch7', 'Lattice Dive', dict(lufs=-25, pan=22, echo=0.4, verb=0.5)),
    ('ship', 'ch8', 'Second Launch', dict(lufs=-23, width=1.4, verb=0.3)),
    ('tremor', 'ch9', 'Still Lift', dict(lufs=-24, verb=0.3)),
    ('nets', 'ch11', 'White Shoreline', dict(lufs=-26, pan=30, verb=0.5)),
    ('murmur', 'ch12', 'Broadcast Murmur', dict(lufs=-31, width=1.4)),
    ('dive', 'ch13', 'Tropic Sweep', dict(lufs=-26, pan=-30, echo=0.4, verb=0.5)),
], master={'loudness': -18, 'ceiling': -1.0, 'fadeout': 4},
   echo={'time': '1/2', 'feedback': 0.45, 'tone': 2000, 'level': -5},
   reverb={'size': 6.0, 'predelay': 40, 'tone': 3500, 'level': -2})
