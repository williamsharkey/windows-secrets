# Writes waulophone/persona.json (the WAULOPHONE identity: Paulywaulyton Works, 1993).
import json
F = '/mnt/c/Users/willi/github/williamsharkey/windows-secrets/packages/basilisk-synth/library/packs/waulophone/persona.json'
p = json.load(open(F))
p['id'] = 'waulophone'
A = 'paulywaulyton/'
INK, BARK, PINE, PINE2, PINE3, CREAM = '#3a200c', '#2e1e12', '#e2b36c', '#bf8038', '#9c6127', '#fff4e4'
CAP, MOSS, MOSS2, BELL, BELL2, LAMP, GLOW, NIGHT = '#c8301e', '#2e4c20', '#62883a', '#3e44a8', '#8a96f0', '#ffc870', '#5ee8b0', '#1a1830'
CREDIT = 'Sounds by Paul Chauncy (Uncle Homunculus / Paulywauly)'
p['category'] = 'WAULOPHONE (library lane; was Paulywaulophone)'
p['pack'].update({'plan_id': 'waulophone', 'library_id': 'waulophone', 'aliases': ['paulywaulophone', 'paulyw', 'PAULYWAULO'], 'title': 'WAULOPHONE', 'subtitle': 'Sounds from Paulywaulyton',
                  'edition': 'Model PW-62', 'version': '1.0', 'date': '1993-10-31', 'label': 'WAULOPHONE', 'label_long': 'WAULOPHONE PW-62', 'author_is_maker': True})
p['maker'] = {
    'name': 'Paulywaulyton Works', 'short': 'Paulywaulyton Works', 'kind': 'instrument workshop', 'year': 1993, 'place': 'Paulywaulyton',
    'contact': ['Paulywaulyton Works', 'The Old Oak, lower root (the small door)', 'Paulywaulyton PW1', 'Knock on the ear and wait.', 'Orders by post. No callers after dusk.'],
    'people': [['Paul Chauncy', 'sounds (Uncle Homunculus / Paulywauly)'], ['Paulywauly', 'keeps the patches']],
    'voice': 'deadpan small workshop; everything by ear; fairies treated as a practical matter'}
L = p['look']
L.update({
    'palette': 'adaptive16',
    'dither': 'bayer4', 'quant': 'octree', 'pixel': 2, 'aa': False, 'ink': INK, 'paper': PINE, 'accent': CAP, 'accent2': MOSS2,
    'fonts': {'display': 'palab.ttf', 'body': 'pala.ttf', 'italic': 'palai.ttf', 'mono': 'cour.ttf', 'hand': 'segoepr.ttf', 'black': 'palab.ttf', 'type': 'cour.ttf'},
    'art': {'bg': A + 'pine.png', 'scene': A + 'village-gate.png', 'back': A + 'giant-snail.png', 'mark': A + 'objects/carved-ear.png',
            'object': A + 'objects/paulywauly.png', 'door': A + 'objects/fairy-door.png', 'ear': A + 'objects/carved-ear.png',
            'ring': A + 'dandelion-clock.png', 'ears': A + 'paulywauly-big-ears.png', 'snail': A + 'giant-snail.png'},
    'focus': {'scene': [.5, .5], 'back': [.5, .62]},
    'title': {'style': 'shadow', 'colors': [INK, PINE3], 'font': 'display', 'spacing': 6},
    'front': [
        {'t': 'pic', 'key': 'bg', 'box': [0, 0, 1, 1]},
        {'t': 'pic', 'key': 'door', 'box': [.035, .025, .195, .2], 'fit': 'contain'},
        {'t': 'pic', 'key': 'ear', 'box': [.825, .03, .965, .2], 'fit': 'contain'},
        {'t': 'word', 'pos': [.51, .095], 'size': .11, 'maxw': .6},
        {'t': 'text', 's': '{subtitle}', 'font': 'italic', 'size': .036, 'pos': [.51, .185], 'anchor': 'mm', 'c': INK, 'maxw': .6},
        {'t': 'rect', 'box': [.065, .235, .935, .785], 'c': BARK},
        {'t': 'rect', 'box': [.075, .245, .925, .775], 'c': PINE3},
        {'t': 'pic', 'key': 'scene', 'box': [.085, .255, .915, .765]},
        {'t': 'pic', 'key': 'object', 'box': [.73, .52, .91, .76], 'fit': 'contain'},
        {'t': 'text', 's': 'PLAY IT BY EAR', 'font': 'display', 'size': .045, 'pos': [.085, .835], 'anchor': 'lm', 'c': INK, 'spacing': 3},
        {'t': 'text', 's': '{edition}  -  {count} presets', 'font': 'body', 'size': .03, 'pos': [.085, .885], 'anchor': 'lm', 'c': INK},
        {'t': 'text', 's': CREDIT, 'font': 'italic', 'size': .027, 'pos': [.5, .955], 'anchor': 'mm', 'c': INK, 'maxw': .9}],
    'spine_bg': PINE3, 'spine_ink': CREAM, 'spine_title': '#f0cc8a',
    'back_bg': PINE, 'back_ink': INK, 'back_head': CAP, 'back_tint': None, 'bullet': '- ',
    'compat': {'pos': [.97, .905], 'anchor': 'rb', 'size': .12},
    'req_head': 'WHAT YOU NEED', 'req': ['{sw} (Windows 3.11)', 'CD-ROM drive (the plugin provides one)']})
p['box'] = {'type': 'jewel', 'price': ['7/6', 'post free'], 'sticker': {'bg': CREAM, 'ink': INK, 'shape': 'round', 'pos': [.86, .3]},
            'burst': None,
            'features': ['{count} presets, each set by ear at the workshop bench', 'The Doo, the Hmm, Boop, Barry, the bird glock and the bee organ',
                         CREDIT, 'A booklet of the stop tabs, and how to listen to them'],
            'barcode': True}
p['disc'] = {'style': 'silk', 'base': '#d8d8d8', 'label': 'full',
             'front': [{'t': 'pic', 'key': 'bg', 'box': [0, 0, 1, 1]},
                       {'t': 'pic', 'key': 'ring', 'box': [.0, .5, 1, 1], 'focus': [.5, .55]},
                       {'t': 'rect', 'box': [0, .495, 1, .505], 'c': BARK},
                       {'t': 'word', 'pos': [.5, .2], 'size': .1, 'maxw': .62},
                       {'t': 'text', 's': '{edition}', 'font': 'italic', 'size': .04, 'pos': [.5, .285], 'anchor': 'mm', 'c': INK},
                       {'t': 'pic', 'key': 'ear', 'box': [.13, .22, .25, .36], 'fit': 'contain'},
                       {'t': 'pic', 'key': 'door', 'box': [.75, .22, .87, .36], 'fit': 'contain'},
                       {'t': 'text', 's': 'PAULYWAULYTON WORKS', 'font': 'display', 'size': .03, 'pos': [.5, .33], 'anchor': 'mm', 'c': INK, 'spacing': 2}],
             'ring': 'PAULYWAULYTON WORKS  *  WAULOPHONE PW-62  *  SOUNDS BY PAUL CHAUNCY  *  PLAY IT BY EAR  *', 'ring_ink': CREAM}
p['icon'] = {'motif': 'ear', 'colors': [PINE, INK, '#d39a4e', PINE3]}
p['files'].update({'readme': 'corporate', 'readme_txt': True, 'license': 'LICENCE.TXT', 'hlp': 'WAULOPHN.HLP', 'pdf': 'WAULOPHN.PDF', 'pdf_size': 'A5',
                   'pdf_style': 'corporate', 'splash': 'WAULOPHN.BMP', 'splash_bpp': 8, 'splash_size': [640, 480]})
p['pdf'] = {'band': PINE3, 'band2': PINE, 'accent': CAP, 'ink': INK, 'line1': "Owner's Book  -  Paulywaulyton Works",
            'heads': {'Introduction': 'From the Workshop', 'Getting Started': 'Listening', 'The Presets': 'The Stop Tabs', 'License': 'Licence'}}
p['hlp'] = {'font': 'Palatino', 'family': 'roman', 'title_color': CAP}
p['text'] = {
    'tagline': 'Play it by ear.',
    'credit': CREDIT,
    'blurb': 'The WAULOPHONE is made in Paulywaulyton, behind the small door in the root of the old oak. This disc carries {count} of its presets: the Doo, the Hmm, Boop, Barry on the bottom line, the glock that sings like a bird, the bee organ and the tuning fork. ' + CREDIT + '.',
    'intro': [
        'The WAULOPHONE is made in Paulywaulyton, a village of toadstool houses behind a small door in the root of an old oak. This disc carries {count} of its presets for {sw}.',
        CREDIT + '. The Doo, Hmm, Boop, bass, sax, glock, flutecorder, flute, tuning fork, guitar pad and bee organ are his recordings, used with his permission. The pianos, tines, voices and kits around them are listed with their own credits in CREDITS.TXT.',
        'No preset on this disc was set by eye. They were tuned at the bench in the evening, with the lamp off and the door shut. Please use them the same way.'],
    'install': [
        'Insert the disc. In the Library tab it appears as WAULOPHONE.',
        'Open a folder and double-click a preset. Listen to it before you play it.',
        'If a preset is too bright, turn the tone down until it is not. You will hear when.',
        'The booklet of stop tabs is WAULOPHN.PDF. The help file is WAULOPHN.HLP.'],
    'maker_note': [
        'Every preset here was chosen by ear, in the evening. Where two settings sounded the same we kept the one that was easier to play.',
        'If you hear something we did not, write and tell us. Letters are read aloud at the Thursday listening.',
        'Paulywaulyton Works'],
    'license': [
        'PAULYWAULYTON WORKS LICENCE',
        'You may use the presets on one computer, and use what you play with them in your own music, anywhere, for as long as you like.',
        'The source recordings by Paul Chauncy (Uncle Homunculus / Paulywauly) are used with his permission. They may not be extracted, sold or given away as a sound collection.',
        'This disc is guaranteed against faults in manufacture for ninety days from the date of purchase. The guarantee does not cover damp, fairies, or a disc left on a radiator.'],
    'copyright': '(c) 1993 Paulywaulyton Works. ' + CREDIT + '.',
    'files': {
        'CARE.TXT': ['|CARE OF YOUR WAULOPHONE DISC\n----------------------------',
                     'Keep the disc in its case, upright, away from the kettle.',
                     'Clean it from the middle outward with a soft dry cloth. Never in circles.',
                     'Honey pine moves with the weather. If the case swells in a wet spring, leave it on a dry shelf for a week. Do not put it near a radiator.',
                     'If the disc sounds wrong, check your ears first. Then check the disc.',
                     '|Paulywaulyton Works'],
        'ORDER.TXT': ['|PAULYWAULYTON WORKS - ORDER FORM\n--------------------------------',
                      'Fill in, fold twice and leave under the small door. Orders are collected at dusk.',
                      '|  [ ] WAULOPHONE PW-62 disc (this disc) ............ 7/6\n  [ ] WAULOPHONE PW-36, the honey-pine box ......... ask\n  [ ] GNOME-16, pages of toadstools ................ ask\n  [ ] Spare carved ear (LISTEN), walnut ............ 2/-\n  [ ] Fairy lights, one string, warm ............... 1/6',
                      '|  Name ______________________________________________\n\n  Address ___________________________________________\n\n  Which ear do you listen with?   [ ] left  [ ] right  [ ] both',
                      'Allow one cycle of the moon for delivery.']}}
p['booklet'] = {
    'mode': 'varied', 'signature': 'Paulywauly', 'only_lanes': ['paulywaulyton'], 'lanes': ['paulywaulyton'],
    'quotes': {'Vocal': 'Doo. Hmm. Boop. Paulywauly keeps the patches.', 'Keys': 'The front room, the long rug, the lamp off.',
               'Pad': 'Through the small door, and out the other side.', 'Bass': 'Barry sings the bottom line.',
               'Bell': 'Leave the window open for the glock.', 'Kit': 'Pages of toadstools.', 'Lead': 'Steer by ear.'},
    'images': {'Vocal': A + 'paulywauly-big-ears.png', 'Pad': A + 'fairy-ring.png', 'Bass': A + 'giant-snail.png', 'Bell': A + 'old-oak.png',
               'Keys': A + 'front-room.png', 'Kit': A + 'root-tortoise.png', 'Lead': A + 'dandelion-clock.png'},
    'subjects': {}, 'theme': ['paulywaulyton', 'fairy', 'toadstool'], 'script_font': 'segoepr.ttf'}
json.dump(p, open(F, 'w'), indent=2, ensure_ascii=False)
print('ok')
