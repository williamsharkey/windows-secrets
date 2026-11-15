"""RPG Battle Theme (Wolfgang_, CC0), re-voiced for the bass-enterprise pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/RPGBattleTheme-Min.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('horn', 1, 12, 55, 79, 0.95), 2: ('chord', 2, 12, 55, 76, 0.85), 3: ('wobble', 3, 12, 33, 52, 1.0), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'RPG Battle Theme', 'pack': 'bass-enterprise', 'kind': 'chiptune', 'composer': 'Wolfgang_', 'source': 'RPG Battle Theme, a FamiTracker module (RPGBattleTheme-Min.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/RPGBattleTheme.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/8-bit-rpg-battleencounter-theme', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'e5e33b5969a1b02fd90d74a5eed4de32690e407c45f94a1f9b2e3e5598fadc2a', 'note': "Played twice through: the NES module's pulse 1 on the trombone, pulse 2 on a brass section, the triangle on the wobbling speed sub, the noise on Kit Manager 98 (Half-Time Kit)."}
TRACKS = [('horn', 'ch1', 'Lattice Accent', {'lufs': -20, 'pan': 12, 'echo': 0.2}), ('chord', 'ch2', 'Lagoon Section', {'lufs': -22, 'pan': -16, 'verb': 0.2}), ('wobble', 'ch3', 'Wobbly Speed Sub', {'lufs': -19}), ('kit', 'ch10', 'kit-manager:Half-Time Kit', {'lufs': -17, 'verb': 0.05})]
module_song(__file__, 'RPGBattleTheme-Min.notes.mid', 180, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)
