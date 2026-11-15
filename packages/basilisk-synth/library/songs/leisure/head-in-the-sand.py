"""Head in the Sand (congusbongus, CC0), re-voiced for the leisure pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/headinthesand.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {3: ('marimba', 1, 12, 55, 81, 0.9), 1: ('flute', 2, 0, 60, 84, 0.95), 2: ('bells', 3, 12, 64, 88, 0.85), 4: ('bongo', 4, 'pad', 60, 0.8)}
HEADER = {'title': 'Head in the Sand', 'pack': 'leisure', 'kind': 'chiptune', 'composer': 'congusbongus', 'source': 'Head in the Sand, a FamiTracker module (headinthesand.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/headinthesand.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/head-in-the-sand-seamless-loop', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'e775a237c9830e416380ce0bae63a167faa2d782164d4060171adcb4a56c2ec1', 'note': "Played three times through as exotica: the NES module's triangle on the marimba, pulse 1 on the lounge flute, pulse 2 on the vibes-bells, the noise on a bongo tap."}
TRACKS = [('marimba', 'ch1', 'Island Marimba', {'lufs': -20, 'pan': -12, 'verb': 0.3}), ('flute', 'ch2', 'Polished Call', {'lufs': -20, 'pan': 6, 'echo': 0.15, 'verb': 0.35}), ('bells', 'ch3', 'Soft Bells', {'lufs': -23, 'pan': 22, 'echo': 0.2, 'verb': 0.4}), ('bongo', 'ch4', 'Twilight Tap', {'lufs': -26, 'pan': 30})]
module_song(__file__, 'headinthesand.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=3)
