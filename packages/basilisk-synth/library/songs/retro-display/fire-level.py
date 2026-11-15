"""Fire Level (Spring Spring, CC0), re-voiced for the retro-display pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/Fire_Level.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 0, 64, 88, 0.95), 2: ('lead2', 2, 0, 60, 84, 0.85), 4: ('arp', 3, 0, 60, 88, 0.8), 5: ('bass', 4, -12, 33, 55, 1.0), 3: ('kit', 10, 'split', [(44, 42), (127, 38)], 0.9)}
HEADER = {'title': 'Fire Level', 'pack': 'retro-display', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'Fire_Level, a Standard MIDI File (Fire_Level.mid) from OpenGameArt (https://opengameart.org/sites/default/files/Fire%20Level.mid). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/fire-level', 'arranger': 'Algorithmic Industries house band', 'source_sha256': 'd2162064a0a20cdcd60d7b1e0d849d91c644c79ad99e1076c0d1f64e3ac162fd', 'note': "The MIDI file's 2A03 and VRC6 lines on the sun-glare lead, a pilot lead, kalimba chords and the basement bass, the noise channel on Kit Manager 98 (Echo Chamber Kit)."}
TRACKS = [('lead', 'ch1', 'Sun Glare Lead', {'lufs': -20, 'pan': 4, 'echo': 0.2, 'verb': 0.25}), ('lead2', 'ch2', 'Field Pilot', {'lufs': -23, 'pan': -16}), ('arp', 'ch3', 'Violet Chords', {'lufs': -24, 'pan': 24, 'echo': 0.3}), ('bass', 'ch4', 'Remote Basement', {'lufs': -19}), ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', {'lufs': -17, 'verb': 0.12})]
module_song(__file__, 'Fire_Level.mid', 140, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=390)
