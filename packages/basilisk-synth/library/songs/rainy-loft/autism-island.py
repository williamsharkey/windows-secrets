"""Autism Island (Spring Spring, CC0), re-voiced for the rainy-loft pack: the notes of a 0CC-FamiTracker module from
OpenGameArt played on the pack's own presets (sources/cc0/autism_island.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 0, 60, 88, 1.0), 2: ('clav', 2, 0, 50, 79, 0.85), 3: ('bass', 4, -12, 33, 55, 1.0),
        4: ('kit', 10, 'split', [(38, 36), (40, 40), (127, 42)], 0.9)}
HEADER = {'title': 'Autism Island', 'pack': 'rainy-loft', 'kind': 'chiptune', 'composer': 'Spring Spring',
          'source': 'Autism Island, a 0CC-FamiTracker module (autism_island.0cc) from OpenGameArt (https://opengameart.org/sites/default/files/autism%20island.zip). Its notes are played here; its chip voices are not used.',
          'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.',
          'proof': 'https://opengameart.org/content/autism-island', 'arranger': 'Algorithmic Industries house band',
          'note': 'A NES module (2A03) re-voiced as city pop: pulse 1 on the neon sign lead, pulse 2 on the disco clavinet, '
                  'the triangle on the rubber taxi bass, the noise channel on the pack\'s Couch Disco kit.'}
TRACKS = [('lead', 'ch1', 'Neon Sign Lead', {'lufs': -19, 'pan': -6, 'echo': 0.2, 'verb': 0.2}),
          ('clav', 'ch2', 'Disco Clavinet', {'lufs': -22, 'pan': 18, 'verb': 0.15}),
          ('bass', 'ch4', 'Rubber Taxi', {'lufs': -19}),
          ('kit', 'ch10', 'Couch Disco', {'lufs': -19, 'verb': 0.08})]
module_song(__file__, 'autism_island.notes.mid', 150, PLAN, HEADER, TRACKS,
            master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 1.8, 'predelay': 14, 'tone': 5500, 'level': -7})
