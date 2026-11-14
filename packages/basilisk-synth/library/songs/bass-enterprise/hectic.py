"""Hectic (Phillip Miller (redactionary), CC0), re-voiced for the bass-enterprise pack: the notes of a FamiTracker module from OpenGameArt played on
the pack's own presets (sources/cc0/nes_05-hectic.notes.mid, converted by tools/songrender/trackers.py)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from _lib import *

PLAN = {2: ('organbass', 2, 0, 36, 55, 1.0), 8: ('wobble', 3, -12, 33, 52, 1.0), 3: ('horn', 1, -12, 55, 76, 0.95), 6: ('chord', 4, 0, 55, 74, 0.85), 1: ('section', 5, 0, 55, 79, 0.9), 7: ('punch', 6, 0, 48, 64, 0.85), 5: ('kit', 10, 'pad', 36, 1.0), 4: ('kit', 10, 'split', [(38, 38), (127, 42)], 0.9)}
HEADER = {'title': 'Hectic', 'pack': 'bass-enterprise', 'kind': 'chiptune', 'composer': 'Phillip Miller (redactionary)', 'source': 'hectic song, a FamiTracker module (nes_05-hectic.ftm) from OpenGameArt (https://opengameart.org/sites/default/files/Free_NES_Music_Pack.zip). Its notes are played here; its samples or chip voices are not used.', 'licence': 'The music: CC0-1.0 (public-domain dedication on the OpenGameArt page). This arrangement: CC0-1.0.', 'proof': 'https://opengameart.org/content/free-nes-music-pack', 'arranger': 'Algorithmic Industries house band', 'source_sha256': '678f3481bd0af420c5ca5d4cf6a807c5e767f2890bd6b4165f965fa11c0546f2', 'note': 'A NES module (2A03 + VRC6) re-voiced as garage: pulse 2 on the 2-step organ bass, the VRC6 saw on the wobbling sub, the triangle on the trombone hook, the VRC6 pulses and pulse 1 on organ chords, a brass section and a punch; DPCM and noise on Kit Manager 98 (Half-Time Kit).'}
TRACKS = [('organbass', 'ch2', 'Organ Bass 2-Step', {'lufs': -19}), ('wobble', 'ch3', 'Wobbly Speed Sub', {'lufs': -21}), ('horn', 'ch1', 'Lattice Accent', {'lufs': -20, 'pan': 12, 'echo': 0.2, 'verb': 0.2}), ('chord', 'ch4', 'Golden Chord', {'lufs': -24, 'pan': -16, 'verb': 0.2}), ('section', 'ch5', 'Lagoon Section', {'lufs': -23, 'pan': 20, 'verb': 0.2}), ('punch', 'ch6', 'Federal Punch', {'lufs': -26, 'pan': -24}), ('kit', 'ch10', 'kit-manager:Half-Time Kit', {'lufs': -17, 'verb': 0.05})]
module_song(__file__, 'nes_05-hectic.notes.mid', 150, PLAN, HEADER, TRACKS, master={'loudness': -15, 'ceiling': -1.0},
            echo={'time': '3/16', 'feedback': 0.3, 'tone': 3500, 'level': -6},
            reverb={'size': 2.0, 'predelay': 16, 'tone': 5500, 'level': -6})
