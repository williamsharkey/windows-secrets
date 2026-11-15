"""Victory Loop (Wolfgang_, CC0), re-voiced for the w3x-heritage pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/victoryloop.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 12, 64, 88, 0.95), 2: ('chords', 2, 12, 55, 76, 0.8), 3: ('bass', 3, 12, 40, 58, 1.0), 4: ('snare', 4, 'pad', 60, 0.8)}
HEADER = {'title': 'Victory Loop', 'pack': 'w3x-heritage', 'kind': 'chiptune', 'composer': 'Wolfgang_', 'source': 'Victory Loop, a FamiTracker module (victoryloop.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/victory.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/8-bit-victory-loop', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '3b062cf67d63f066b35a1604328f58bcebce857083fd357103cda387f6d84dae', 'note': "Played twice through on the six Windows 3.1 sounds: the NES module's pulses on the ding piano and ding chords, the triangle on the ding bass, the noise on a ding snare."}
TRACKS = [('lead', 'ch1', 'Still Upright', {'lufs': -19, 'pan': 6, 'verb': 0.25}), ('chords', 'ch2', 'Sonic Chords', {'lufs': -23, 'pan': -16, 'verb': 0.2}), ('bass', 'ch3', 'Field Bass', {'lufs': -20}), ('snare', 'ch4', 'Basement Snare', {'lufs': -27, 'pan': 10})]
module_song(__file__, 'victoryloop.notes.mid', 180, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)
