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


# ------------------------------------------------------------------ packs from the owner's gardens (2026-11-14)
# Each group's sounds come only from its list (GROUP_ONLY); kit groups are built by gen.kit_dna from KITS2.
ROLE_CAT.update({'kit': 'Kit', 'vocal': 'Choir/Vox', 'rave': 'Brass/Stabs', 'mallet': 'Bells/Mallets'})
EP = ['gd_ep_%s_%s' % (m, n) for m in ('tine', 'bell', 'reed') for n in ('c2', 'c3', 'c4', 'c5', 'c6')] + \
     ['gd_ep_%s_hard_%s' % (m, n) for m in ('tine', 'bell', 'reed') for n in ('c3', 'c4', 'c5')]
PIANO = ['gd_piano_a%d' % i for i in range(1, 6)]
BASS = ['gd_bass%d_c%d' % (p, n) for p in range(6) for n in (1, 2, 3)]
WORLDS = ['gd_%s_%s' % (w, n) for w in ('stalactite_grotto', 'conch_horizon', 'fog_temple', 'bamboo_mist', 'crystal_fantasia',
                                       'aurora_veil') for n in ('c2', 'c4', 'c6')]
RAVE = ['gd_rave_%s_%s' % (w, n) for w in ('hoover', 'chord', 'scream', 'piano', 'organ', 'reese') for n in ('c2', 'c4', 'c6')]
VOICE = ['gd_voice_%s_%s' % (v, w) for v in ('lpc', 'klatt', 'sam') for w in
         ('aah', 'ooh', 'boop', 'bele', 'dance', 'hello', 'lala', 'meow', 'goose', 'robot')]
MALLET = ['gd_marimba_%s' % p for p in ('bass', 'fifth', 'root', 'third', 'fifthhi', 'octave', 'sixth')] + \
         ['gd_steelpan_%s' % p for p in ('basspan', 'lowfifth', 'tenor', 'third', 'fifth', 'octave', 'tenth')] + \
         ['gd_timpani_%s' % p for p in ('c3', 'd3', 'e3', 'g3', 'a3', 'c4')]
PAUL = ['pw_doo', 'pw_doo_held', 'pw_bass', 'pw_bass_held', 'pw_boop', 'pw_glock', 'pw_flutecorder', 'pw_fork',
        'pw_guitar_pad', 'pw_bee_organ', 'pw_hmm', 'pw_hmm_held', 'pw_flute', 'pw_sax']
SHIM = ['dingxp', 'chimesxp', 'print', 'default', 'ding']   # a Windows sound may sparkle on top

PACKS2 = [
    dict(id='paulywaulophone', name='Paulywaulophone', blurb='Uncle Homunculus plays the office piano. Everyone sings along.',
         new=True, groups=[G('Keys', 14), G('Pad', 10), G('Vocal', 10), G('Lead', 6), G('Bass', 8), G('Bell', 8), G('Kit', 6)]),
    dict(id='garden-rhythm', name='Garden Rhythm Works', blurb='Drums, rave stabs and talking machines from the garden shed.',
         new=True, groups=[G('Kit', 14), G('Stab', 10), G('Pad', 10), G('Vocal', 8), G('Perc', 8), G('Mallet', 8)]),
]
GROUP_ONLY = {
    ('paulywaulophone', 'Keys'): EP + PIANO + ['pw_guitar_pad', 'pw_glock', 'pw_bee_organ'] + SHIM,
    ('paulywaulophone', 'Pad'): ['pw_hmm_held', 'pw_doo_held', 'pw_bee_organ', 'pw_flute', 'pw_fork'] + WORLDS[:9] + EP[:5],
    ('paulywaulophone', 'Vocal'): ['pw_doo', 'pw_doo_held', 'pw_hmm', 'pw_hmm_held', 'pw_boop'] + VOICE[:12],
    ('paulywaulophone', 'Lead'): ['pw_flutecorder', 'pw_flute', 'pw_sax', 'pw_bee_organ', 'pw_glock'] + EP[10:15],
    ('paulywaulophone', 'Bass'): ['pw_bass', 'pw_bass_held', 'pw_boop'] + BASS,
    ('paulywaulophone', 'Bell'): ['pw_glock', 'pw_fork'] + EP[5:10] + MALLET[:14] + SHIM,
    ('garden-rhythm', 'Stab'): RAVE,
    ('garden-rhythm', 'Pad'): WORLDS + RAVE[12:15],
    ('garden-rhythm', 'Vocal'): VOICE,
    ('garden-rhythm', 'Perc'): ['gd_%s_%s' % (k, p) for k, ps in (('taiko', ('odaiko', 'shime', 'nagado', 'okedo', 'ka')),
                                ('tabla', ('ge', 'na', 'ke', 'tin', 'tun', 'te', 'ra')), ('glitch', ('kick', 'snap', 'grit', 'zap', 'tick', 'fuzz', 'blip', 'err')))
                                for p in ps],
    ('garden-rhythm', 'Mallet'): MALLET,
}
GM = {'rosewood': {'kick': 36, 'lowkick': 35, 'snare': 38, 'rim': 37, 'clap': 39, 'hat': 42, 'tighthat': 44, 'openhat': 46,
                   'bell': 56, 'tamb': 54, 'hitom': 50, 'midtom': 47, 'lotom': 45, 'cabasa': 52, 'crash': 49, 'conga': 48,
                   'loconga': 43, 'loclap': 40, 'lorim': 41, 'ride': 51},
      'mouth': {'bkick': 36, 'lowkick': 35, 'ksnare': 38, 'pfsnare': 40, 'tshat': 42, 'that': 44, 'tchhat': 53, 'opents': 46,
                'psh': 49, 'kh': 51, 'dum': 45, 'dom': 47, 'dumm': 43, 'click': 37, 'hum': 50, 'tightkick': 41, 'kesnare': 39,
                'pfrim': 48, 'double': 52, 'wub': 55}}
HANDS = ['tumba', 'conga', 'slap', 'mute', 'cajon', 'bongohi', 'bongolo', 'slap2', 'talking', 'frame', 'blockhi', 'blockmid',
         'blocklo', 'claves', 'agogohi', 'agogolo', 'triangle', 'mutetri', 'shaker', 'back']
KITS2 = {
    'garden-rhythm': [('studio', 'rosewood'), ('tape', 'rosewood'), ('chip', 'rosewood'), ('latin', 'rosewood'),
                      ('mouth', 'mouth'), ('radio', 'mouth'), ('hands', 'hands'), ('temple', 'hands'),
                      ('taiko', 'modal'), ('tabla', 'modal'), ('glitch', 'modal'), ('timpani', 'modal')],
    'paulywaulophone': [('pauly', 'pauly'), ('studio', 'rosewood'), ('tape', 'rosewood'), ('mouth', 'mouth')],
}
PACKS.extend(PACKS2)
PACK_BY_ID.update({p['id']: p for p in PACKS2})

# the tape-replay pack: sustained PD/CC0 (and the owner's) notes given tape character in the DNA (gen.tapeify)
PACKS2.append(dict(id='tape-parlour', name='Tape Parlour Ensemble', blurb='Eight seconds of tape behind every key.',
                   new=True, tape=True, groups=[G('Strings', 10), G('Lead', 8), G('Vocal', 8), G('Brass', 6), G('Organ', 6), G('Keys', 4)]))
PACK_BY_ID['tape-parlour'] = PACKS2[-1]; PACKS.append(PACKS2[-1])
GROUP_ONLY.update({
    ('tape-parlour', 'Strings'): ['violin_section_sus_c4', 'cello_section_sus_c3', 'cello_section_sus_g1', 'contrabass_sus_d1', 'erhu_d3'],
    ('tape-parlour', 'Lead'): ['flute_vib_c5', 'pw_flute', 'organ_hammond_m100_flute_c', 'pw_flutecorder'],
    ('tape-parlour', 'Vocal'): ['choir_aah', 'crowd_sing_aah_f', 'ems_704_vowel_a3', 'pw_hmm_held', 'gd_voice_klatt_aah', 'gd_voice_klatt_ooh'],
    ('tape-parlour', 'Brass'): ['horn_sus_c3', 'trumpet_sus_c4', 'trombone_sus_c3', 'tuba_sus_f1', 'pw_sax'],
    ('tape-parlour', 'Organ'): ['organ_pipe_open_13', 'organ_pipe_open_31', 'organ_pipe_open_49', 'organ_hammond_m100_flute_c', 'pw_bee_organ'],
    ('tape-parlour', 'Keys'): ['vibraphone_c_low', 'gd_piano_a3', 'gd_piano_a4', 'gd_ep_tine_c4', 'gd_ep_reed_c4'],
})
