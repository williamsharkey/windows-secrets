"""Original preset names: at most three words, no brand, product, artist, label or song (pack-plan 6.8).

Researched targets keep their research name when it is original (genres, favorites, aesthetic, electromech);
the ROM Reference targets name real instruments and products, so every preset gets a new name here. Names are
deterministic (seeded by the preset's DNA) and unique across the whole library.
"""
import hashlib, re

BANNED = re.compile(r'\b(roland|korg|yamaha|emu|e-mu|ensoniq|kurzweil|moog|arp|oberheim|sequential|prophet|juno|jupiter|'
                    r'd-50|d50|m1|dx7|dx|tx81z|sy|wavestation|fairlight|emulator|mellotron|rhodes|wurlitzer|wurli|hammond|'
                    r'leslie|clavinet|serum|vital|massive|sylenth|spire|nexus|omnisphere|keyscape|kontakt|labs|arturia|'
                    r'ableton|pigments|diva|reese|zamfir|vangelis|kraftwerk|daft|microsoft|windows|xp|intel|apple|mac|'
                    r'nintendo|sega|atari|commodore|amiga|sony|casio|akai|mpc|tr-808|808|909|303|minimoog|vocoder|'
                    r'steinway|bosendorfer|fender|gibson|marimba lumina|melodica|stylophone|omnichord|ebow|autotune)\b', re.I)

ADJ = """Amber Arctic Azure Bakelite Ballroom Basement Blue Brass Bright Broadcast Brushed Cable Cathode Cedar Chrome Civic
Clear Cobalt Coded Cold Copper Coral Corner Crystal Daylight Delta Dial Digital Distant Dusk Dusty Early Echo Electric
Elevated Ember Empty Faded Federal Felt Field Flat Floor Foggy Folded Frosted Gentle Glass Global Golden Granite Grey
Harbor Hazy Hollow Honey Hotel Humid Indigo Inland Ivory Jade Kinetic Lagoon Laser Late Lattice Lobby Long Lucid Lunar
Marble Matte Meadow Metro Midnight Mild Mint Misty Modular Molten Neon Night Noble Northern Ocean Office Opal Open
Orbital Pale Paper Pastel Pearl Pewter Plaza Polar Polished Quiet Radiant Rainy Rapid Remote Rose Rubber Rural Rusty
Saffron Satin Second Shaded Signal Silent Silver Slate Slow Soft Solar Sonic Spare Static Steady Steel Still Stone
Sunday Sunlit Swift Tidal Tinted Topaz Tropic Twilight Ultra Upper Urban Velvet Vinyl Violet Warm Washed Waxed Western
White Wide Winter Wired Woven Yellow Zinc""".split()

NOUN = {
 'Keys': 'Keys Piano Upright Parlour Hammers Ivories Chords Study Recital Felt Practice Lounge Salon Etude Ballad'.split(),
 'EP': 'Tines Tine Bars Suitcase Reed Glow Comping Electric Keys Satin Lounge Vibe Chorus Phaser'.split(),
 'Organ': 'Organ Drawbars Chapel Console Pipes Bark Choir Loft Stops Manual Cathedral Rink Revival Wheel'.split(),
 'Bass': 'Bass Sub Floor Low End Foundation Bottom Pulse Thump Rumble Line Groove Basement Cellar Weight Anchor'.split(),
 'Pads': 'Pad Wash Haze Bloom Canopy Horizon Cloud Atrium Field Mist Aurora Drift Veil Tide Glow Halo'.split(),
 'Strings': 'Strings Section Ensemble Bows Quartet Orchestra Cellos Violins Swell Legato Tremolo Chamber'.split(),
 'Choir/Vox': 'Choir Voices Vox Chant Hymn Ahh Chorus Singers Vowel Chop Breath Murmur Cantor'.split(),
 'Brass/Stabs': 'Stab Hit Brass Fanfare Horns Section Blast Punch Chord Accent Herald Salute'.split(),
 'Leads': 'Lead Line Whistle Solo Signal Beam Ray Voice Wire Song Call Spark Pilot'.split(),
 'Plucks/Arps': 'Pluck Pick Harp Strum Pizz Ticks Arp Steps Ladder Plink Snap Flick Spool'.split(),
 'Bells/Mallets': 'Bells Chimes Mallets Bell Carillon Glock Vibes Gong Peal Toll Tower Steeple Ring'.split(),
 'World': 'Zither Strings Drum Reed Flute Harp Bowl Temple Market Caravan Lute Gamelan Kettle'.split(),
 'FX/Risers': 'Riser Sweep Swoosh Lift Dive Launch Warp Uplink Ascent Descent Wake Surge Burst'.split(),
 'Drones/Ambient': 'Drone Hum Expanse Depth Monolith Dormant Continuum Vault Reservoir Hangar Sanctum'.split(),
 'Textures': 'Texture Ambience Room Weather Grain Murmur Static Traffic Rain Current Crowd Shoreline'.split(),
 'Lo-fi/Vaporwave': 'Tape Cassette Mall Escalator Fountain Food Court Plaza Arcade Memory Rerun Loop'.split(),
 'Frutiger Aero': 'Aqua Bubble Glass Dew Droplet Lagoon Aquarium Breeze Orb Gloss Ripple Prism'.split(),
 'Y2K/Corporate': 'Logon Portal Synergy Memo Intranet Lobby Dialup Hold Kiosk Webinar Bulletin Cubicle'.split(),
 'Electromech': 'Relay Teletype Exchange Switchboard Typebar Ticker Dynamo Dial Solenoid Crossbar Punch'.split(),
 'Perc': 'Click Tick Snap Knock Rim Shaker Clap Tap Block Clack Hat Snare'.split(),
}


def _h(s, k=0):
    return int(hashlib.sha1(('%s|%d' % (s, k)).encode()).hexdigest(), 16)


def ok_name(n):
    return n and not BANNED.search(n) and len(n.split()) <= 3 and len(n) <= 28


class Namer:
    def __init__(self):
        self.used = set()

    def take(self, n):
        k = n.lower()
        if k in self.used: return False
        self.used.add(k); return True

    def keep_or_make(self, name, cat, key):
        if name and ok_name(name) and self.take(name): return name
        return self.make(cat, key)

    def make(self, cat, key):
        nouns = NOUN.get(cat, NOUN['Pads'])
        for k in range(400):
            h = _h(key, k)
            n = '%s %s' % (ADJ[h % len(ADJ)], nouns[(h // 997) % len(nouns)])
            if k > 60:
                n = '%s %s %s' % (ADJ[h % len(ADJ)], ADJ[(h // 7) % len(ADJ)], nouns[(h // 997) % len(nouns)])
            if ok_name(n) and self.take(n): return n
        raise RuntimeError('no name for ' + key)
