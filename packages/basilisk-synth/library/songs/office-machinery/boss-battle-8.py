"""Boss Battle 8 (nene, CC0), re-voiced for the office-machinery pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/boss_battle_08.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('bugle', 1, 0, 60, 84, 0.95), 2: ('beep', 2, 12, 60, 84, 0.8), 3: ('lowbugle', 3, 12, 52, 72, 0.8), 4: ('drives', 4, 12, 33, 52, 1.0), 6: ('beep2', 5, 0, 64, 88, 0.8), 7: ('inductor', 6, 0, 45, 67, 0.8), 5: ('kit', 10, 0, 0, 127, 1.0)}
HEADER = {'title': 'Boss Battle 8', 'pack': 'office-machinery', 'kind': 'chiptune', 'composer': 'nene', 'source': 'boss_battle_08, a Standard MIDI File (boss_battle_08.mid) from OpenGameArt (https://opengameart.org/sites/default/files/boss_battle_08.mid). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/boss-battle-8-retro', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '52da0aa33ad0a76eaa47b2135f6de4cd5da9c4dbd4b9d1b4b80a568f52b365d1', 'note': "Played twice through on office machinery: the MIDI file's lead on the civil-defence bugle, its rhythm lines on PC-speaker beeps and the low bugle, its bass on twelve drives, its strings on a hard-disk inductor, its General MIDI drums on the spacebar kit."}
TRACKS = [('bugle', 'ch1', 'Signal Uplink', {'lufs': -20, 'pan': -4, 'verb': 0.3}), ('beep', 'ch2', 'Cedar Hat', {'lufs': -24, 'pan': 16}), ('lowbugle', 'ch3', 'White Dive', {'lufs': -23, 'pan': -18, 'verb': 0.3}), ('drives', 'ch4', 'Ocean Crowd', {'lufs': -19}), ('beep2', 'ch5', 'Harbor Snare', {'lufs': -26, 'pan': 24}), ('inductor', 'ch6', 'Steady Texture', {'lufs': -26, 'pan': -24}), ('kit', 'ch10', 'Rubber Canopy', {'lufs': -17, 'verb': 0.06})]
module_song(__file__, 'boss_battle_08.mid', 140, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)
