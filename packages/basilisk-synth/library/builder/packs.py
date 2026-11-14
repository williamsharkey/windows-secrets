"""The packs (research/pack-plan.md): names, blurbs, groups with their counts, and what the builder fills them with.

Each group: (program-list category, scoring category (catdefs), count for v2/W-Y presets). The plan's v3 counts
for kits, the sequencer, glide/wow and grains are not built yet (data/v3-ideas.json); presets that use only the
v3 W and Y genes (available on 3.11 now) may fill up to the plan's v3 share of a group as 3.11-only programs.
"""

ROLE_CAT = {
    'bass': 'Bass', 'sub': 'Bass', 'wobble': 'Bass', 'growl': 'Bass', 'reese': 'Bass', 'organ bass': 'Bass', 'bass 808': 'Bass',
    'lead': 'Leads', 'pad': 'Pads', 'pad grain': 'Pads', 'keys': 'Keys', 'organ': 'Organ', 'stab': 'Brass/Stabs',
    'chord': 'Brass/Stabs', 'stab hit': 'Brass/Stabs', 'pluck': 'Plucks/Arps', 'arp': 'Plucks/Arps', 'bell': 'Bells/Mallets',
    'mallet': 'Bells/Mallets', 'bell mallet': 'Bells/Mallets', 'strings': 'Strings', 'strings brass': 'Strings',
    'brass strings': 'Strings', 'brass': 'Brass/Stabs', 'vocal': 'Choir/Vox', 'fx': 'FX/Risers', 'glitch fx': 'FX/Risers',
    'texture': 'Textures', 'drone': 'Drones/Ambient', 'perc': 'Perc', 'snare': 'Perc', 'snare tom': 'Perc',
    'perc impact': 'Perc', 'ep': 'EP',
}
# program-list category (pack-plan 1.4) for a group
PROG = {'Wobble': 'Bass', 'Growl': 'Bass', 'Reese': 'Bass', 'Organ bass': 'Bass', 'Bass 808': 'Bass', 'Sub': 'Sub',
        'Pad grain': 'Pad', 'Glitch FX': 'FX', 'Strings brass': 'Strings', 'Brass strings': 'Brass', 'Snare tom': 'Perc',
        'Perc impact': 'Perc', 'Bell mallet': 'Bell', 'Stab hit': 'Stab'}

W31_ONLY = ['chimes', 'chord', 'ding', 'tada', 'ringin', 'ringout']


def G(name, total, v3=0):
    cat = ROLE_CAT[name.lower()]
    return (name, cat, total - v3, v3)


PACKS = [
    dict(id='workgroup-house', name='Workgroup House Edition', blurb='Four-on-the-floor productivity for the whole department.',
         groups=[G('Bass', 14, 3), G('Keys', 10), G('Organ', 6), G('Stab', 18, 4), G('Pad', 8), G('Strings', 4), G('Lead', 6, 2),
                 G('Vocal', 12, 8), G('Pluck', 6), G('FX', 10), G('Perc', 6)],
         prefer=['chord', 'chordxp', 'xpding', 'ringout', 'tada', 'organ_hammond_m100_flute_c', 'epiano_yamaha_vibe', 'crowd_sing_aah_f']),
    dict(id='techno-server', name='Techno Server 4.0', blurb='Mission-critical repetition, now with dub delay.',
         groups=[G('Bass', 12, 4), G('Stab', 16, 6), G('Pad', 10), G('Lead', 6), G('Perc', 16), G('FX', 10), G('Texture', 10)],
         prefer=['xpding', 'menu', 'xpstart', 'start', 'em_relay_click_a', 'ems_relay_pull', 'startup', 'logon', 'em_hum_mains_loop']),
    dict(id='trance-connectivity', name='Trance Connectivity Kit 2000', blurb='Connects your hands to the ceiling.',
         groups=[G('Lead', 16), G('Pad', 14, 6), G('Pluck', 12), G('Bass', 8, 4), G('Chord', 8, 4), G('FX', 8, 2), G('Keys', 4)],
         prefer=['tadaxp', 'tada', 'startup', 'logon', 'print', 'xpringout', 'ringout', 'default']),
    dict(id='breakbeat-resource', name='Breakbeat Resource Kit', blurb='Every break your network will ever need.',
         groups=[G('Bass', 24, 8), G('Vocal', 14, 10), G('Pad', 12), G('Keys', 8), G('Stab', 12), G('Lead', 8, 3), G('FX', 12),
                 G('Perc', 10, 2)],
         prefer=['xpringout', 'ringout', 'recycle', 'critstop', 'chord', 'tadaxp', 'prelinger_office_courtesy', 'nasa_apollo8_go_for_tli']),
    dict(id='bass-enterprise', name='Bass Enterprise Edition', blurb='Low-end infrastructure for medium and large businesses.',
         groups=[G('Wobble', 16), G('Growl', 14, 6), G('Sub', 12, 4), G('Organ bass', 12, 4), G('Reese', 10, 4), G('Stab', 6),
                 G('Vocal', 6, 4), G('FX', 4)],
         prefer=['xpringout', 'ringout', 'batlow', 'error', 'critstop', 'hwfail', 'organ_pedal_25', 'bass_guitar_gs']),
    dict(id='beat-management', name='Beat Management Console', blurb='Centralised administration of the boom and the bap.',
         groups=[G('Keys', 22, 12), G('Bass 808', 18, 10), G('Bell', 10, 2), G('Pluck', 4), G('Lead', 10, 4), G('Pad', 12),
                 G('Vocal', 10, 6), G('Texture', 14), G('Strings brass', 10), G('FX', 10)],
         prefer=['epiano_yamaha_vibe', 'epiano_bell_c3', 'piano_upright_cs4', 'balloon', 'rain_on_window', 'vibraphone_c_low', 'xpding']),
    dict(id='retro-display', name='Retro Display Properties', blurb='Adjust your colour depth to 1985.',
         groups=[G('Pad', 16, 4), G('Keys', 16), G('Lead', 14, 4), G('Bass', 14, 6), G('Brass strings', 10), G('Snare tom', 6),
                 G('FX', 6)],
         prefer=['logon', 'startup', 'default', 'print', 'tadaxp', 'xpding', 'recycle', 'epiano_yamaha_vibe']),
    dict(id='screen-saver', name='Ambient Screen Saver Collection', blurb='Protects your monitor and your nervous system.',
         groups=[G('Pad', 26, 4), G('Drone', 18), G('Bell mallet', 16), G('Texture', 20), G('Lead', 10, 4)],
         prefer=['startup', 'shutdown', 'logon', 'singing_bowl_long', 'crystal_bowl_ab4', 'creek_loop', 'glass_harp', 'wind_chime_single']),
    dict(id='diagnostics', name='Experimental Diagnostics Suite', blurb='Finds errors. Plays them back in time.',
         groups=[G('Glitch FX', 16, 4), G('Perc', 14), G('Bell', 10, 4), G('Lead', 10), G('Pad grain', 10, 6), G('Vocal', 10, 4)],
         prefer=['error', 'critstop', 'hwfail', 'popup', 'menu', 'emh_modem_crush', 'ems_crushed_line_noise', 'tadaxp']),
    dict(id='leisure', name='Leisure Accessories Pack', blurb='For the executive lounge.',
         groups=[G('Mallet', 10), G('Texture', 8), G('Keys', 6), G('Strings', 6), G('Perc', 6), G('Lead', 4)],
         prefer=['vibraphone_c_low', 'marimba_c4', 'bird_american_robin', 'frogs_night_chorus', 'flute_vib_c5', 'harp_c5', 'glass_harp']),
    dict(id='game-port', name='Game Port Sound Set', blurb='Joystick not included.',
         groups=[G('Lead', 14), G('Bass', 8, 4), G('Perc', 8), G('FX', 10)],
         prefer=['ding', 'ringin', 'chimes', 'popup', 'menu', 'balloon', 'ringout', 'xpstart']),
    dict(id='workstation-classics', name='Professional Workstation Classics',
         blurb='The sounds of the leading software, re-engineered for your desktop.',
         groups=[G('Lead', 18, 4), G('Bass', 22, 10), G('Pad', 14, 2), G('Pluck', 12), G('Chord', 10, 4), G('FX', 6)],
         prefer=['tadaxp', 'xpringout', 'ringout', 'print', 'logon', 'default']),
    dict(id='studio-archive', name='Studio Instruments Archive', blurb='Every keyboard in the building, catalogued.',
         groups=[G('Keys', 24), G('Strings', 12, 2), G('Brass', 10), G('Pad', 12, 2), G('Bell mallet', 10), G('Perc impact', 6, 2),
                 G('Bass', 6, 2)],
         prefer=['piano_upright_cs3', 'piano_upright_cs4', 'epiano_yamaha_vibe', 'violin_section_sus_c4', 'cello_section_sus_c3',
                 'trumpet_sus_c4', 'horn_sus_c3', 'vibraphone_c_low', 'organ_hammond_m100_flute_c']),
    dict(id='w3x-heritage', name='Windows 3.x Heritage Edition', blurb='Sixteen bits of history. Eight of them audible.',
         groups=[G('Bell', 10), G('Keys', 8), G('Pad', 10), G('Bass', 8, 2), G('Lead', 8, 2), G('Stab hit', 8), G('Perc', 8)],
         only=W31_ONLY),
    # the three packs from earlier research: one preset per target (its best variant)
    dict(id='rom-reference', name='ROM Reference Library', blurb='The great workstations, archived.', research='preset-targets'),
    dict(id='lifestyle-aesthetics', name='Lifestyle Aesthetics Pack', blurb='Mall. Lobby. Aquarium. Startup.', research='aesthetic'),
    dict(id='electromech-heritage', name='Electromechanical Heritage', blurb='Relays, typewriters, telephones.', research='electromech'),
]
PACK_BY_ID = {p['id']: p for p in PACKS}

# genres.json / modern-favorites.json 'pack' ids -> ours
PLAN_PACK = {'workgroup-house': 'workgroup-house', 'techno-server': 'techno-server', 'trance-connectivity': 'trance-connectivity',
             'breakbeat-resource': 'breakbeat-resource', 'bass-enterprise': 'bass-enterprise', 'beat-management': 'beat-management',
             'retro-display': 'retro-display', 'screen-saver': 'screen-saver', 'diagnostics': 'diagnostics', 'leisure': 'leisure',
             'game-port': 'game-port', 'workstation-classics': 'workstation-classics', 'studio-archive': 'studio-archive',
             'heritage': 'w3x-heritage', 'w3x-heritage': 'w3x-heritage', 'kit-manager': None}


def group_for(pack, role):
    """the pack group a researched role lands in"""
    cat = ROLE_CAT.get(role.lower())
    p = PACK_BY_ID[pack]
    for g in p.get('groups', []):
        if g[0].lower() == role.lower(): return g
    for g in p.get('groups', []):
        if g[1] == cat: return g
    return None
