"""On Again Off Again (Chance de la Soul, CC0), re-voiced for the techno-server pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/On_Again_Off_Again.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 12, 60, 84, 0.9), 2: ('stab', 2, 0, 55, 72, 0.85), 6: ('morse', 3, 12, 60, 84, 0.8), 7: ('chords', 4, 12, 55, 72, 0.8), 8: ('sub', 5, 12, 36, 52, 1.0), 3: ('tick', 6, 'pad', 67, 0.8), 5: ('kit', 10, 'pad', 36, 1.0), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'On Again Off Again', 'pack': 'techno-server', 'kind': 'chiptune', 'composer': 'Chance de la Soul', 'source': 'On Again Off Again, a FamiTracker module (On_Again_Off_Again.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/on_again_off_again_nsf_ftm.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/nes-on-again-off-again', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '41e4465d5fc5f7337a2df1dd0af0bad05f9b03e017621a8419c01976d80e6123', 'note': "Played twice through as techno: the NES module's pulses and VRC6 lines on a CSIRAC-pulse lead, a hit, morse blips and horns, the VRC6 saw on the sub, its triangle on relay ticks, DPCM and noise on Kit Manager 98 (Long Boom Kit)."}
TRACKS = [('lead', 'ch1', 'Folded Call', {'lufs': -21, 'pan': 6, 'echo': 0.3}), ('stab', 'ch2', 'Lattice Hit', {'lufs': -24, 'pan': -12, 'echo': 0.4}), ('morse', 'ch3', 'Granite Line', {'lufs': -24, 'pan': -20, 'echo': 0.35}), ('chords', 'ch4', 'Waxed Horns', {'lufs': -25, 'pan': 18, 'verb': 0.25}), ('sub', 'ch5', 'Felt Sub', {'lufs': -19}), ('tick', 'ch6', 'Rural Tick', {'lufs': -29, 'pan': 28}), ('kit', 'ch10', 'kit-manager:Long Boom Kit', {'lufs': -17, 'verb': 0.04})]
module_song(__file__, 'On_Again_Off_Again.notes.mid', 125, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)
