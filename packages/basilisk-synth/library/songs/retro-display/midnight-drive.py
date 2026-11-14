"""Midnight Drive (congusbongus, CC0), re-voiced for the retro-display pack: the notes of a FastTracker 2 module from OpenGameArt played on
the pack's own presets (sources/cc0/midnight_drive.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {4: ('lead', 1, -12, 64, 88, 0.95), 7: ('arp', 2, 0, 60, 86, 0.8), 5: ('bass', 3, -24, 33, 52, 1.0), 6: ('brass', 4, -12, 55, 79, 0.9), 1: ('kit', 10, 'pad', 36, 1.0), 2: ('kit', 10, 'pad', 38, 1.0), 3: ('kit', 10, 'pad', 42, 0.8), 9: ('kit', 10, 'pad', 49, 0.9), 8: ('kit', 10, 'pad', 46, 0.7)}
HEADER = {'title': 'Midnight Drive', 'pack': 'retro-display', 'kind': 'chiptune', 'composer': 'congusbongus', 'source': 'Midnight Drive, a FastTracker 2 module (midnight_drive.xm) from OpenGameArt (https://opengameart.org/sites/default/files/midnight_drive_0.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/midnight-drive', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '10c01f72019b649f0a1fc5af04e357dfaf59ee3083d9b57534d5e8d3da8aad13', 'note': "Synthwave at 80 bpm: the module's lead synth on the chrome lead, its arpeggio on kalimba chords, its TB-303 line on the rumble bass, its second synth on a brass lead, its drums on Kit Manager 98 (Echo Chamber Kit)."}
TRACKS = [('lead', 'ch1', 'Chrome Brass Lead', {'lufs': -20, 'pan': 4, 'echo': 0.25, 'verb': 0.3}), ('arp', 'ch2', 'Violet Chords', {'lufs': -24, 'pan': 22, 'echo': 0.3, 'verb': 0.2}), ('bass', 'ch3', 'Saffron Rumble', {'lufs': -19}), ('brass', 'ch4', 'Brass Signal', {'lufs': -22, 'pan': -14, 'verb': 0.3}), ('kit', 'ch10', 'kit-manager:Echo Chamber Kit', {'lufs': -17, 'verb': 0.12})]
module_song(__file__, 'midnight_drive.notes.mid', 80, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, cut=226)
