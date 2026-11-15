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
    dict(id='waulophone', name='WAULOPHONE', aliases=['paulywaulophone'],
         blurb='The WAULOPHONE is made in Paulywaulyton, behind the small door in the root of the old oak. Play it by ear.',
         new=True, groups=[G('Keys', 14), G('Pad', 10), G('Vocal', 10), G('Lead', 6), G('Bass', 8), G('Bell', 8), G('Kit', 6)]),
    dict(id='garden-rhythm', name='Garden Rhythm Works', blurb='Drums, rave stabs and talking machines from the garden shed.',
         new=True, groups=[G('Kit', 14), G('Stab', 10), G('Pad', 10), G('Vocal', 8), G('Perc', 8), G('Mallet', 8)]),
]
GROUP_ONLY = {
    ('waulophone', 'Keys'): EP + PIANO + ['pw_guitar_pad', 'pw_glock', 'pw_bee_organ'] + SHIM,
    ('waulophone', 'Pad'): ['pw_hmm_held', 'pw_doo_held', 'pw_bee_organ', 'pw_flute', 'pw_fork'] + WORLDS[:9] + EP[:5],
    ('waulophone', 'Vocal'): ['pw_doo', 'pw_doo_held', 'pw_hmm', 'pw_hmm_held', 'pw_boop'] + VOICE[:12],
    ('waulophone', 'Lead'): ['pw_flutecorder', 'pw_flute', 'pw_sax', 'pw_bee_organ', 'pw_glock'] + EP[10:15],
    ('waulophone', 'Bass'): ['pw_bass', 'pw_bass_held', 'pw_boop'] + BASS,
    ('waulophone', 'Bell'): ['pw_glock', 'pw_fork'] + EP[5:10] + MALLET[:14] + SHIM,
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
    'waulophone': [('pauly', 'pauly'), ('studio', 'rosewood'), ('tape', 'rosewood'), ('mouth', 'mouth')],
}
PACKS.extend(PACKS2)
PACK_BY_ID.update({p['id']: p for p in PACKS2})
# old pack ids still resolve (saved projects, .song files, ratings): the owner's renames
PACK_ALIASES = {a: p['id'] for p in PACKS2 for a in p.get('aliases', [])}
PACK_BY_ID.update({a: PACK_BY_ID[i] for a, i in PACK_ALIASES.items()})

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

# Tape Parlour Ensemble, rebuilt on the research lane's tape set: one family (or two, as two tracks) per preset,
# every sample in its own key zone (gen.tape_zone_dna)
F = lambda *names: [(n, None, None) for n in names]
TAPE_SPECS = {
    'Strings': [F('tape_cellos'), F('tape_violins'), F('tape_violins_trem'), F('tape_violas'), F('tape_violin_solo'),
                F('tape_contrabass'), F('tape_cellos', 'tape_violins'), F('tape_violas', 'tape_violins'),
                F('tape_psaltery_bowed'), F('tape_contrabass', 'tape_cellos'), F('tape_violins_trem', 'tape_cellos')],
    'Lead': [F('tape_flute_vib'), F('tape_flute_plain'), F('tape_piccolo'), F('tape_recorder_alto'), F('tape_recorder_tenor'),
             F('tape_recorder_soprano'), F('tape_recorder_bass'), F('tape_ocarina'), F('tape_oboe'), F('tape_clarinet'),
             F('tape_flute_vib', 'tape_clarinet')],
    'Vocal': [F('choir_breathing_pad_c4'), F('choir_full_octave_first_note'), F('choir_drone_practice'),
              F('voice_man_singing_note'), F('voice_low_note'), F('choir_marching_drone'), F('choir_aah'),
              F('crowd_sing_aah_f'), F('pw_hmm_held')],
    'Brass': [F('tape_trumpet'), F('tape_trumpet_harmon'), F('tape_trombone'), F('tape_horn'), F('tape_tuba'),
              F('tape_saxello'), F('tape_bassoon'), F('tape_trumpet', 'tape_trombone')],
    'Organ': [F('tape_organ_8ft'), F('tape_organ_full'), F('tape_organ_quiet'), F('tape_harmonica'),
              F('tape_organ_8ft', 'tape_recorder_bass'), F('pw_bee_organ')],
    'Keys': [F('gd_piano'), F('gd_ep_tine'), F('gd_ep_reed'), F('tape_vibes_bowed')],
}

# ------------------------------------------------------------------ packs from the research lane's round 2 (PD/CC0)
OCEAN = ['pmel_airguns', 'pmel_ak_whale_52', 'pmel_atlantic_blue', 'pmel_atlantic_fin', 'pmel_atlantic_minke', 'pmel_bloop',
         'pmel_blue_ne_pacific', 'pmel_blue_south_pacific', 'pmel_blue_w_pacific', 'pmel_blue_whale_nets', 'pmel_challenger_deep_modem',
         'pmel_damselfish', 'pmel_earthquake_pioneer', 'pmel_harmonic_tremor', 'pmel_humpback_ship_samoa', 'pmel_humpback_ship_sbnms',
         'pmel_iceberg_calving', 'pmel_noise_97139', 'pmel_ron_brown_arrival', 'pmel_ship_overhead', 'pmel_small_ship',
         'pmel_sound_source', 'pmel_tremor', 'pmel_upsweep', 'pmel_whistle']
PCFX = ['pc_crt_degauss', 'pc_crt_tv_on_off_static', 'pc_floppy_eject', 'pc_floppy_insert_latch', 'pc_hdd_spin_up',
        'pc_hdd_spin_up_down', 'pc_tape_deck_startup', 'pc_pc_speaker_gsm_buzz', 'pc_cd_seek_mouse', 'pc_crt_tv_uhf_scan',
        'pc_hdd_head_align', 'pc_floppy_read_a', 'pc_floppy_read_b', 'civil_defense_siren_waver'] + \
       ['bugle_adjutants_call', 'bugle_assembly', 'bugle_attention', 'bugle_drill_call', 'bugle_mail_call', 'bugle_officers_call', 'bugle_recall']
PCTEX = ['pc_server_rack_fans', 'pc_vhs_tape_hiss', 'pc_vhs_ntsc_hum', 'pc_crt_tv_hum', 'pc_fan_coil_whine', 'pc_hdd_7200_idle',
         'pc_hdd_maxtor_10k', 'pc_hdd_inductor_mic', 'pc_cassette_squeaky', 'pc_computer_12_drives', 'pc_cdrom_pickup_coil']
PCPERC = ['pc_floppy_access', 'pc_floppy_insert', 'pc_opl3_elec_snare', 'pc_pc_speaker_error_beep', 'floppy_seek_clunk',
          'key_mechanical_hard', 'key_spacebar', 'mouse_click', 'light_switch_on', 'relay_click', 'dtmf_digits', 'key_press_down']
PACKS2 += [
    dict(id='courtyard-chapel', name='Courtyard & Chapel', blurb='Harpsichords in the hall, bells in the tower, harps in the garden.',
         new=True, groups=[G('Keys', 8), G('Pluck', 10), G('Mallet', 8), G('Bell', 8), G('FX', 4), G('Drone', 2)]),
    dict(id='listening-post', name='Listening Post', blurb='Three thousand metres down, something is singing.',
         new=True, groups=[G('Drone', 10), G('Texture', 10), G('FX', 8)]),
    dict(id='office-machinery', name='Office Machinery', blurb='Every drive, fan and speaker in the building, on cue.',
         new=True, groups=[G('Kit', 4), G('Perc', 8), G('FX', 10), G('Texture', 6)]),
]
for p in PACKS2[-3:]:
    PACKS.append(p); PACK_BY_ID[p['id']] = p
ZONE_SPECS = {
    ('courtyard-chapel', 'Keys'): [F('harpsichord_flemish'), F('harpsichord_flemish_hi'), F('upright_yamaha'),
                                   F('harpsichord_flemish', 'harpsichord_flemish_hi'), F('upright_yamaha', 'harpsichord_flemish')],
    ('courtyard-chapel', 'Pluck'): [F('folk_harp'), F('dan_tranh'), F('dan_tranh_vib'), F('dan_tranh_trem'), F('psaltery_pluck'),
                                    F('strumstick'), F('nyunga'), F('mbira_mavembe'), F('kalimba_tanzania'), F('kalimba_kenya')],
    ('courtyard-chapel', 'Mallet'): [F('balafon'), F('vibes_soft'), F('vibes_hard'), F('tubular_glock'), F('kalimba_tanzania', 'balafon')],
    ('courtyard-chapel', 'Bell'): [F('tubular_bell'), F('hand_chime'), F('tubular_glock'), F('hand_chime', 'tubular_bell')],
}
GROUP_ONLY.update({
    ('courtyard-chapel', 'Bell'): ['nepalese_bell_a', 'nepalese_bell_b', 'gong_mf', 'bell_tree_stroke', 'vibraslap_ring'],
    ('courtyard-chapel', 'FX'): ['glock_gliss_down_penta', 'glock_gliss_up', 'mark_tree_down', 'mark_tree_slow_up', 'flexatone_long',
                                 'toy_train_whistle_fall', 'siren_whistle_b', 'gong_scrape', 'cymbal_bowed', 'dan_tranh_gliss_up', 'dan_tranh_gliss_down'],
    ('courtyard-chapel', 'Drone'): ['didgeridoo_sus_a', 'didgeridoo_phrase', 'organ_blower', 'cymbal_bowed', 'gong_mf'],
    ('listening-post', 'Drone'): OCEAN + ['choir_aah', 'singing_bowl_long', 'gd_fog_temple_c4', 'tape_cellos_c1'],
    ('listening-post', 'Texture'): OCEAN,
    ('listening-post', 'FX'): OCEAN,
    ('office-machinery', 'Perc'): PCPERC,
    ('office-machinery', 'FX'): PCFX,
    ('office-machinery', 'Texture'): PCTEX,
})
KITS2['office-machinery'] = [('office', 'office'), ('office2', 'office'), ('pcspeaker', 'office'), ('typing', 'office')]

# the polysynth / FM pack (research round 2, brand-neutral IDs; models are credited in the catalog only)
PACKS2.append(dict(id='polysynth-showroom', name='Polysynth Showroom', blurb='Every keyboard on the shop floor, plugged in at once.',
                   new=True, groups=[G('Keys', 8), G('Pad', 10), G('Strings', 6), G('Vocal', 6), G('Brass', 6), G('Bass', 8), G('Lead', 8)]))
PACKS.append(PACKS2[-1]); PACK_BY_ID['polysynth-showroom'] = PACKS2[-1]
ZONE_SPECS.update({
    ('polysynth-showroom', 'Keys'): [F('fm87_epiano'), F('fm87_piano'), F('fm87_clav'), F('fm87_epiano', 'fm87_clav')],
    ('polysynth-showroom', 'Strings'): [F('poly83_on_off_strings'), F('vocoder_strings'), F('vocoder_strings', 'poly83_on_off_strings')],
    ('polysynth-showroom', 'Vocal'): [F('vocoder_choir_male'), F('vocoder_choir_female'), F('vocoder_choir_male_ens'),
                                      F('vocoder_choir_female_ens'), F('vocoder_choir_male', 'vocoder_choir_female')],
})
GROUP_ONLY.update({
    ('polysynth-showroom', 'Keys'): ['poly78_roger_piano_c3', 'mono77_bargain_piano_b2', 'poly82_rich_pluck_c4', 'poly84_simpleton_c3'],
    ('polysynth-showroom', 'Pad'): ['poly78_saxons_pad_c2', 'poly78_vikings_pad_2_osc_c2', 'poly78_vikings_pad_2_osc_c3', 'poly82_open_pad_c2',
                                    'poly82_open_pad_c3', 'poly85_dark_pad_chorus_c2', 'poly85_dark_pad_chorus_c3', 'poly85_mod_pad_c2',
                                    'poly83_slowone_c2', 'poly78_thick_swishy_c2', 'poly78_shimmer_c3', 'poly83_gasflowers_c1', 'poly78_sad_wow_c3'],
    ('polysynth-showroom', 'Brass'): ['poly83_brassy_f1', 'poly85_thin_brassy_c2', 'poly83_wobble_brass_c2', 'poly83_big_c2', 'poly85_synthetic_c3'],
    ('polysynth-showroom', 'Bass'): ['poly83_snapbass_c2', 'poly85_slow_bass_d3', 'mono79_filter_vel_bass_c3', 'mono77_cream_b0',
                                     'mono77_fm_rings_ds1', 'mono77_iee_yah_f1', 'poly83_big_c2'],
    ('polysynth-showroom', 'Lead'): ['poly85_buzzy_lead_c3', 'mono77_curious_lead_c3', 'poly85_sensitive_square_c3', 'mono77_pulse_2_g2',
                                     'poly78_pwm_lady_c4', 'mono79_noisy_sqr_filter_vel_c3', 'poly83_cease_ds5', 'poly78_res_organ_d4'],
})
