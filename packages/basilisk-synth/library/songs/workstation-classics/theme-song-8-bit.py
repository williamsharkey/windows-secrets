"""Theme Song (8-bit) (nene, CC0), re-voiced for the workstation-classics pack: the notes of a Standard MIDI File from OpenGameArt played on
the pack's own presets (sources/cc0/Theme_Song_8_bit.mid)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {1: ('lead', 1, 0, 60, 84, 0.95), 2: ('lead2', 2, 0, 60, 84, 0.7), 3: ('pluck', 3, 0, 52, 72, 0.8), 5: ('bass', 4, 12, 33, 52, 1.0), 7: ('pad', 5, 0, 55, 76, 0.8), 8: ('saw', 6, -12, 60, 84, 0.8), 6: ('kit', 10, 0, 0, 127, 1.0)}
HEADER = {'title': 'Theme Song (8-bit)', 'pack': 'workstation-classics', 'kind': 'chiptune', 'composer': 'nene', 'source': 'Theme_Song_8_bit, a Standard MIDI File (Theme_Song_8_bit.mid) from OpenGameArt (https://opengameart.org/sites/default/files/Theme%20Song%20%5B8-bit%5D.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/theme-song-8-bit', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '4c7f57cf0212d3a21ace15dd54cdd73769a7519bf4d4bb096d9311bd2f69fbbb', 'note': "The MIDI file's lead and rhythm guitars, bass, strings and sawtooth on workstation leads, a strum, the mono bass, a pad and a call lead, its General MIDI drums on Kit Manager 98 (Punch Kick Kit)."}
TRACKS = [('lead', 'ch1', 'Chrome Pilot', {'lufs': -20, 'pan': 4, 'echo': 0.2}), ('lead2', 'ch2', 'Arctic Signal', {'lufs': -25, 'pan': -16}), ('pluck', 'ch3', 'Orbital Strum', {'lufs': -24, 'pan': 22}), ('bass', 'ch4', 'Ladder Mono Bass', {'lufs': -19}), ('pad', 'ch5', 'Pale Cloud', {'lufs': -26, 'verb': 0.35}), ('saw', 'ch6', 'Remote Call', {'lufs': -24, 'pan': -24, 'echo': 0.2}), ('kit', 'ch10', 'kit-manager:Punch Kick Kit', {'lufs': -17, 'verb': 0.06})]
module_song(__file__, 'Theme_Song_8_bit.mid', 130, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6}, loops=2, cut=370)
