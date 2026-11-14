"""Thermocline: an original deep-ocean piece, 56 bpm, E minor. A slow descent: the ship overhead fades, the
drones settle a fifth lower each section, the humpback sings a falling line, airguns pulse in the distance, ice
and the bloop at the bottom."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

S = Score(bpm=56, seed=2026)
fin = S.part('fin', 1)
blue = S.part('blue', 2)
bowl = S.part('bowl', 3)
hump = S.part('humpback', 4)
ship = S.part('ship', 5)
airgun = S.part('airgun', 6)
bloop = S.part('bloop', 7)
ice = S.part('ice', 8)
sweep = S.part('upsweep', 9)
murmur = S.part('murmur', 11)
shelf = S.part('shoreline', 12)

t = 0.0
# 1. near the surface: a ship passes, a high drone
ship.note(0, 33, 14, 86)
hold(blue, 2, 64, 22, 70, 12); hold(bowl, 6, 76, 18, 58, 12)
sweep.note(12, 64, 4, 74)
t = 24
# 2. the first layer: E minor drones, the humpback's line, distant airguns every 6 beats
for i, (f, b) in enumerate(((52, 64), (48, 60), (50, 62), (47, 59))):
    hold(fin, t + 8 * i, f, 8, 72, 8); hold(blue, t + 8 * i + 1, b, 7, 64, 8)
hump.mel('h. B4 q A4 | w G4 | h E4 G4 | w F#4 | h. B4 q C5 | w B4 | h A4 F#4 | w E4', at=t, vel=84)
for k in range(5):
    airgun.note(t + 3 + 6 * k, 38, 1, 64 - 3 * k)
t += 32
# 3. deeper: the drones a fifth lower, the humpback lower too, the white shoreline
for i, (f, b) in enumerate(((45, 57), (41, 53), (43, 55), (40, 52))):
    hold(fin, t + 8 * i, f, 8, 74, 8); hold(blue, t + 8 * i + 1, b, 7, 66, 8)
hump.mel('h. E4 q D4 | w C4 | h A3 C4 | w B3 | h. E4 q F#4 | w E4 | h D4 B3 | w B3', at=t, vel=86)
shelf.note(t + 4, 30, 6, 74); sweep.note(t + 20, 60, 4, 70)
hold(murmur, t, 60, 32, 56, 16)
t += 32
# 4. the bottom: one drone, the bloop, ice
hold(fin, t, 40, 24, 70, 8); hold(bowl, t + 4, 64, 18, 52, 12)
bloop.note(t + 2, 19, 6, 84); ice.note(t + 9, 17, 8, 84); bloop.note(t + 16, 17, 6, 76)
hump.mel('w r | h. E4 q D4 | w B3 | w r', at=t + 4, vel=78)
t += 24

finish(__file__, S, {
    'title': 'Thermocline',
    'pack': 'listening-post',
    'kind': 'original',
    'composer': 'Algorithmic Industries house band (an original for SNDWAVE2000)',
    'licence': 'CC0-1.0 (the composition and this arrangement); the hydrophone recordings are NOAA PMEL\'s (public domain)',
    'note': 'A slow descent in E minor, 56 bpm: a ship overhead, blue-whale and fin-whale drones settling a fifth '
            'lower each section, a humpback line, distant airguns, the white shoreline, the bloop and ice at the bottom.',
    'tail': 8,
}, [
    ('fin', 'ch1', 'Dial Depth', dict(lufs=-23, pan=-12, verb=0.45)),
    ('blue', 'ch2', 'Lattice Dormant', dict(lufs=-24, pan=12, verb=0.45)),
    ('bowl', 'ch3', 'Saffron Dormant', dict(lufs=-28, verb=0.5)),
    ('humpback', 'ch4', 'Ocean Shoreline', dict(lufs=-20, pan=4, echo=0.25, verb=0.5)),
    ('ship', 'ch5', 'Second Launch', dict(lufs=-23, width=1.4, verb=0.3)),
    ('airgun', 'ch6', 'Waxed Murmur', dict(lufs=-27, pan=-30, echo=0.4, verb=0.5)),
    ('bloop', 'ch7', 'Cedar Murmur', dict(lufs=-23, verb=0.4)),
    ('ice', 'ch8', 'Swift Room', dict(lufs=-24, pan=24, verb=0.5)),
    ('upsweep', 'ch9', 'Lattice Dive', dict(lufs=-26, pan=22, echo=0.4, verb=0.5)),
    ('murmur', 'ch11', 'Broadcast Murmur', dict(lufs=-31, width=1.4)),
    ('shoreline', 'ch12', 'White Shoreline', dict(lufs=-26, pan=-20, verb=0.5)),
], master={'loudness': -18, 'ceiling': -1.0, 'fadeout': 4},
   echo={'time': '1/2', 'feedback': 0.45, 'tone': 2000, 'level': -5},
   reverb={'size': 6.0, 'predelay': 40, 'tone': 3500, 'level': -2})
