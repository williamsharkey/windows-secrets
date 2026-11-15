"""Battle Loop (Wolfgang_, CC0), re-voiced for the kit-manager pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/BattleTheme.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('calculator', 1, 24, 72, 84, 0.95), 2: ('typingpool', 2, 12, 72, 84, 0.9), 3: ('relayroom', 3, 12, 60, 72, 1.0), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'Battle Loop', 'pack': 'kit-manager', 'kind': 'chiptune', 'composer': 'Wolfgang_', 'source': 'Battle Loop, a FamiTracker module (BattleTheme.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/BattleLoop.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/8-bit-battle-loop', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'e1c26821ab1a95919ee160da81b7d098fa2b09ae5af63f0bf324e4b68a1644f2', 'note': "Played four times through on Kit Manager 98: the NES module's pulses on Calculator Bureau and Typing Pool's tuned keys, the triangle on Relay Room's, the noise on the Twelve-Bit Crate Kit."}
TRACKS = [('calculator', 'ch1', 'Calculator Bureau', {'lufs': -20, 'pan': -6, 'echo': 0.2, 'verb': 0.3}), ('typingpool', 'ch2', 'Typing Pool', {'lufs': -21, 'pan': 24, 'echo': 0.15}), ('relayroom', 'ch3', 'Relay Room', {'lufs': -21, 'verb': 0.15}), ('kit', 'ch10', 'Twelve-Bit Crate Kit', {'lufs': -18, 'verb': 0.06})]
module_song(__file__, 'BattleTheme.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=4)
