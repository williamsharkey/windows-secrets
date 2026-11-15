"""Showcase 2 (Spring Spring, CC0), re-voiced for the trance-connectivity pack: the notes of a 0CC-FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/Coding_Pirates_Showcase_OST_2_FDS.notes.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {6: ('lead', 1, 0, 64, 88, 0.95), 7: ('pluck', 2, 12, 60, 84, 0.85), 8: ('saw', 3, 0, 55, 79, 0.85), 2: ('arp', 4, 12, 60, 84, 0.8), 1: ('bass', 5, 12, 36, 55, 1.0), 3: ('pad', 6, 0, 55, 72, 0.8), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'Showcase 2', 'pack': 'trance-connectivity', 'kind': 'chiptune', 'composer': 'Spring Spring', 'source': 'Test, a 0CC-FamiTracker module (Coding_Pirates_Showcase_OST_2_FDS.0cc) from OpenGameArt (https://opengameart.org/sites/default/files/Coding%20Pirates%20Showcase%20OST%202%20FDS.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/fdsnamco-pwm-demonstation', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '76cf086c2afa31f872eac88adad781a2e7b29efad9ffe733e23c36c7e332051f', 'note': "Played twice through as trance: the module's VRC6 and FDS-style lines on a lead, plucks, a saw line and a harp arpeggio, pulse 1 on the bass, the triangle on a pad, the noise on Kit Manager 98 (Punch Kick Kit)."}
TRACKS = [('lead', 'ch1', 'Velvet Solo', {'lufs': -20, 'pan': 4, 'echo': 0.25, 'verb': 0.3}), ('pluck', 'ch2', 'Woven Snap', {'lufs': -23, 'pan': -18, 'echo': 0.3}), ('saw', 'ch3', 'Bakelite Line', {'lufs': -23, 'pan': 16, 'verb': 0.2}), ('arp', 'ch4', 'Rainy Harp', {'lufs': -25, 'pan': -26, 'echo': 0.3}), ('bass', 'ch5', 'Rainy Groove', {'lufs': -19}), ('pad', 'ch6', 'Paper Halo', {'lufs': -25, 'verb': 0.4, 'width': 1.3}), ('kit', 'ch10', 'kit-manager:Punch Kick Kit', {'lufs': -17, 'verb': 0.05})]
module_song(__file__, 'Coding_Pirates_Showcase_OST_2_FDS.notes.mid', 140, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2)
