"""Boss Battle 6 (nene, CC0), re-voiced for the breakbeat-resource pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/Boss_Battle_6.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 0, 60, 86, 0.95), 3: ('gtr', 2, 0, 48, 72, 0.85), 4: ('gtr2', 3, 0, 48, 72, 0.8), 5: ('bass', 4, 12, 33, 52, 1.0), 6: ('pad', 5, 0, 55, 72, 0.8), 7: ('hit', 6, 0, 60, 84, 0.8), 8: ('signal', 7, 0, 60, 86, 0.75), 2: ('kit', 10, 0, 0, 127, 1.0)}
HEADER = {'title': 'Boss Battle 6', 'pack': 'breakbeat-resource', 'kind': 'chiptune', 'composer': 'nene', 'source': 'Boss_Battle_6, a Standard MIDI File (Boss_Battle_6.mid) from OpenGameArt (https://opengameart.org/sites/default/files/Boss%20Battle%206.mid). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/boss-battle-6-8-bit', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '059a90730a4ebcb73662d4827564c47bc80581579dbc0e70f903840eb51a4c74', 'note': 'A CC0 boss theme as breakbeat: its lead guitar on a lead, the two rhythm guitars on trombone stabs, its bass on the reese, strings on a pad, two synth lines on horns and a ray, its General MIDI drums on Kit Manager 98 (Breaker Box Kit).'}
TRACKS = [('lead', 'ch1', 'Velvet Pilot', {'lufs': -20, 'pan': 4, 'echo': 0.2}), ('gtr', 'ch2', 'Rainy Chord', {'lufs': -24, 'pan': -24}), ('gtr2', 'ch3', 'Blue Accent', {'lufs': -24, 'pan': 24}), ('bass', 'ch4', 'Neuro Growl', {'lufs': -19}), ('pad', 'ch5', 'Granite Pad', {'lufs': -26, 'verb': 0.4}), ('hit', 'ch6', 'Northern Hit', {'lufs': -24, 'verb': 0.3}), ('signal', 'ch7', 'Steady Ray', {'lufs': -25, 'pan': -14, 'echo': 0.2}), ('kit', 'ch10', 'kit-manager:Breaker Box Kit', {'lufs': -16.5, 'verb': 0.06})]
module_song(__file__, 'Boss_Battle_6.mid', 160, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=260)
