"""My Street (congusbongus, CC0), re-voiced for the Game Port Sound Set: the module's square lead, wave and sine
arpeggios, triangle bass and noise drums, each on a Game Port preset, the noise on the Noise Channel kit."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

module_song(__file__, 'my_street.notes.mid', 144, {
    1: ('square', 1, -12, 67, 91, 1.0),
    4: ('wave', 2, -12, 60, 84, 0.9),
    5: ('sine', 3, -12, 60, 86, 0.85),
    3: ('bass', 4, -12, 36, 57, 1.0),
    6: ('long', 5, -12, 55, 79, 0.9),
    2: ('noise', 10, 'split', [(47, 38), (127, 42)], 1.0),
}, {
    'title': 'My Street',
    'pack': 'game-port',
    'kind': 'chiptune',
    'composer': 'congusbongus',
    'source': 'My Street, a FastTracker 2 module (my street.xm), from OpenGameArt. Its notes are played here; its '
              'samples are not used.',
    'licence': 'The module: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.',
    'proof': 'https://opengameart.org/content/my-street',
    'arranger': 'Algorithmic Industries house band',
    'note': 'The module\'s six instruments on Game Port presets: square lead, wave and sine arpeggios, a long pad, '
            'triangle bass; the noise channel on the Kit Manager 98 Noise Channel kit (snare and hat by pitch).',
}, [
    ('square', 'ch1', 'Midnight Signal', dict(lufs=-20, pan=-8, echo=0.12, verb=0.1)),
    ('wave', 'ch2', 'Lucid Line', dict(lufs=-24, pan=22, echo=0.1)),
    ('sine', 'ch3', 'Second Ray', dict(lufs=-23, pan=-20)),
    ('bass', 'ch4', 'Waxed Line', dict(lufs=-19)),
    ('long', 'ch5', 'Cold Voice', dict(lufs=-25, pan=12, verb=0.25)),
    ('noise', 'ch10', 'kit-manager:Noise Channel Kit', dict(lufs=-19, verb=0.05)),
], master={'loudness': -14, 'ceiling': -1.0}, echo={'time': '3/16', 'feedback': 0.25, 'tone': 4000, 'level': -7},
   reverb={'size': 1.2, 'predelay': 10, 'tone': 6000, 'level': -9}, cut=400)
