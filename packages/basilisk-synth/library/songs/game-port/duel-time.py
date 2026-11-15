"""Duel Time (Wolfgang_, CC0), re-voiced for the game-port pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/DuelTime.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 12, 64, 88, 0.95), 2: ('lead2', 2, 12, 60, 84, 0.85), 3: ('bass', 3, 0, 36, 55, 1.0), 6: ('arp', 4, 12, 55, 79, 0.8), 7: ('vrc', 5, 12, 52, 76, 0.8), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'Duel Time', 'pack': 'game-port', 'kind': 'chiptune', 'composer': 'Wolfgang_', 'source': 'Duel Time, a FamiTracker module (DuelTime.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/DuelTime.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/8-bit-duel-theme', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'ebe917f826746dea7b5015ef1a56318254ee248283101b5d295bdcbbe1ae7bfa', 'note': "Played three times through: the NES module's pulses on two Game Port leads, the VRC6 pulses on an arpeggio and a warm lead, the triangle on the sub, the noise on Kit Manager 98 (Noise Channel Kit)."}
TRACKS = [('lead', 'ch1', 'Lucid Line', {'lufs': -20, 'pan': -8, 'echo': 0.12}), ('lead2', 'ch2', 'Harbor Whistle', {'lufs': -23, 'pan': 20}), ('bass', 'ch3', 'Saffron Sub', {'lufs': -19}), ('arp', 'ch4', 'Zinc Ray', {'lufs': -25, 'pan': -24}), ('vrc', 'ch5', 'Warm Lead', {'lufs': -24, 'pan': 24}), ('kit', 'ch10', 'kit-manager:Noise Channel Kit', {'lufs': -19, 'verb': 0.05})]
module_song(__file__, 'DuelTime.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=3)
