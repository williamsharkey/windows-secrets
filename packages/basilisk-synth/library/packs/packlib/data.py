"""Pack data: the presets (and, later, the sounds) that go on a pack's disc.

Order of sources:
1. The library lane's pack output, when it exists: library/builder/out/<id>/PRESETS.TSV (category, name, DNA[, pack])
   and optional LIBRARY.TSV + sound folders. Override the folder with persona["pack"]["data"].
2. Otherwise placeholders from the research lane's preset targets (library/research/preset-targets.json and
   electromech-presets.json), renamed so that no preset name carries a real product or company name.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../library/packs
LIB = os.path.dirname(HERE)                                          # .../library

# Names that would put a real product, company or person on a fictional pack. Applied to placeholder names only.
RENAME = {
    'Rhodes Mk I Suitcase': 'Tine Suitcase EP', 'Wurlitzer 200A': 'Reed Piano 200', 'Clavinet D6 Funk': 'Funk Clav',
    "FM EP 'DX Tine' (90s)": 'FM Tine EP', 'Vaporwave EP (slowed DX)': 'Slowed FM EP', 'Pipe/Church Organ': 'Church Organ',
    "Gospel Organ 'Full'": 'Gospel Organ Full', 'Toy Piano / Celesta': 'Toy Celesta', 'MSN Nudge Boing': 'Nudge Boing',
    'Vista Sparkle Glissando': 'Sparkle Glissando', 'Nokia-style Ringtone Lead': 'Pocket Ringtone Lead',
    'Windows Error Choir': 'Error Choir', 'Flash Intro Whoosh-Hit': 'Intro Whoosh-Hit', 'Eccojam Loop': 'Echo Jam Loop',
    'Slowed + Reverb Chord': 'Slowed and Reverb Chord', '1403 Chorus': 'Line Printer Chorus', 'Ferranti Hoot': 'Mainframe Hoot',
    'CSIRAC Pulse': 'Valve Computer Pulse', 'GPO Alarm Bell': 'Post Alarm Bell', 'Strowger Glock': 'Selector Glock',
    'Swell Pad (Reverse)': 'Reverse Swell Pad', 'Organ Drone (Cathedral)': 'Cathedral Organ Drone',
}
BRANDS = re.compile(r'\b(Rhodes|Wurlitzer|Clavinet|DX7?|Nokia|MSN|Vista|Windows|Microsoft|Yamaha|Roland|Korg|Kurzweil|Ensoniq|'
                    r'E-?mu|Moog|Omnisphere|Serum|Massive|Kontakt|Sylenth|Spire|Nexus|Absynth|Alchemy|Zebra|Ethno|Fairlight|'
                    r'Hammond|Leslie|Mellotron|Flash|Apple|Mac|IBM|AOL|GeoCities|Ferranti|CSIRAC|Strowger|GPO|Vangelis|Zamfir|Proteus|Emulator|'
                    r'Triton|Wavestation|Juno|Jupiter|Prophet|Oberheim|Minimoog|Akai|Casio|TB-?303|TR-?[0-9]{3}|M1|D-?50|JV-?[0-9]+|'
                    r'SC-?55|TX81Z|Synclavier|Lexicon|Nord|Arturia|Spectrasonics|Keyscape|Vital|Pigments|Diva|LABS|Ableton|MPC|SP-?1200|'
                    r'Mirage|MT-?32|Fairlight|Steinway|Bosendorfer|Fender|Gibson|Nokia|Sega|Nintendo|Atari|Commodore|Amiga|SID|NES|Game ?Boy|K2000|K250|FB-?01)\b', re.I)


_REN = {}


def clean_name(n):
    n = _REN.get(n) or RENAME.get(n, n)
    n = n.replace('/', ' ').replace("'", '').replace('"', '')
    n = re.sub(r'\s+', ' ', n).strip()
    if BRANDS.search(n):
        n2 = re.sub(r'\(\s*\)|^-?style\b', '', BRANDS.sub('', n))
        n2 = re.sub(r'\s+', ' ', n2).strip(" -+'")
        print('  renamed %r -> %r (a real name)' % (n, n2))
        n = n2 or 'Preset'
    return n


def _targets():
    return json.load(open(os.path.join(LIB, 'research', 'preset-targets.json')))


def _pick(items, spec):
    """spec '*', '*2' (first 2), '*2:4' (items 2..3), or an exact name."""
    if spec.startswith('*'):
        r = spec[1:]
        if not r:
            return items
        if ':' in r:
            a, b = r.split(':')
            return items[int(a):int(b)]
        return items[:int(r)]
    return [x for x in items if x['name'] == spec]


ROLE_FOLDER = {'bass': 'Bass', 'sub': 'Bass', 'drums': 'Kits', 'pad': 'Pads', 'fx': 'FX', 'keys': 'Keys', 'lead': 'Leads',
               'stab': 'Stabs', 'vocal': 'Vocals', 'texture': 'Texture', 'perc': 'Perc', 'bell': 'Bells', 'strings': 'Strings',
               'drone': 'Drones', 'organ': 'Organs', 'mallet': 'Mallets', 'pluck': 'Plucks', 'chord': 'Chords', 'snare': 'Perc',
               'brass': 'Brass', 'arp': 'Arps'}
AES = os.environ.get('AES_PRESETS', os.path.expanduser('~/ws-aes/packages/basilisk-synth/design/aesthetic-presets.json'))


def _seeds():
    g = json.load(open(os.path.join(LIB, 'research', 'genres.json')))['targets']
    m = json.load(open(os.path.join(LIB, 'research', 'modern-favorites.json')))['targets']
    return g + m


LIBMAP = {'workgrp': 'workgroup-house', 'techsrv': 'techno-server', 'trance2k': 'trance-connectivity', 'breakbt': 'breakbeat-resource',
          'bassent': 'bass-enterprise', 'beatmgmt': 'beat-management', 'retrodsp': 'retro-display', 'screensv': 'screen-saver',
          'diagnost': 'diagnostics', 'leisure': 'leisure', 'gameport': 'game-port', 'workstn': 'workstation-classics',
          'studarch': 'studio-archive', 'heritage': 'w3x-heritage', 'romref': 'rom-reference', 'lifestyl': 'lifestyle-aesthetics',
          'emheritg': 'electromech-heritage'}
BUILDER_OUT = os.path.join(LIB, 'builder', 'out')


def _library(persona):
    """The library lane's presets for this pack (builder/out/library.json), or None."""
    lid = persona['pack'].get('library_id') or LIBMAP.get(persona['id'])
    f = os.path.join(BUILDER_OUT, 'library.json')
    if not lid or not os.path.exists(f):
        return None, None
    rows = [x for x in json.load(open(f, encoding='utf-8')) if x['pack'] == lid]
    return (rows or None), lid


def _builder_folder(persona):
    pk = persona['pack']
    if pk.get('data'):
        return pk['data']
    for name in (pk.get('plan_id'), persona['id']):
        if name:
            for sub in ('out', 'packs'):
                f = os.path.join(LIB, 'builder', sub, name)
                if os.path.exists(os.path.join(f, 'PRESETS.TSV')):
                    return f
    return None


def load(persona):
    """Returns dict: presets [ {category, folder, folder83, name, dna, file83, joliet, disp} ], sounds [], placeholder, source.
    pack.sources (placeholders): {"plan": "<pack id in genres.json / modern-favorites.json>"} | {"heritage": true}
    (every seed with the W3.11 badge) | {"targets": [categories], "extra": ["cat/*a:b"]} (preset-targets.json) |
    {"aesthetic": true} (aesthetic-presets.json) | {"electromech": true}. Optional "limit"."""
    pk = persona['pack']
    _REN.clear()
    _REN.update(pk.get('rename', {}))
    folders = pk.get('folders', {})
    presets = []
    folder = _builder_folder(persona)
    lib, lid = _library(persona)
    if lib:
        for x in lib:
            presets.append({'category': x['category'], 'name': x['name'], 'dna': x['dna'], 'ships': x['ships'],
                            'badge': x.get('badge', ''), 'library': x.get('library', False)})
        src, placeholder, sounds = 'builder/out/library.json, pack %s' % lid, False, []
    elif folder:
        for line in open(os.path.join(folder, 'PRESETS.TSV'), encoding='utf-8'):
            if line.startswith('#') or not line.strip():
                continue
            f = line.rstrip('\n').split('\t')
            presets.append({'category': f[0], 'name': f[1], 'dna': f[2]})
        src, placeholder = os.path.relpath(folder, LIB), False
        sounds = []
        if os.path.exists(os.path.join(folder, 'LIBRARY.TSV')):
            for line in open(os.path.join(folder, 'LIBRARY.TSV'), encoding='utf-8'):
                if line.strip() and not line.startswith('#'):
                    sounds.append(line.rstrip('\n').split('\t'))
    else:
        placeholder, sounds = True, []
        s = pk['sources']
        if s.get('kits'):
            # real kit DNAs (DNA v3 kit pads, PRESET-ENGINE-2.md 15): the kit seeds of the genre and favourites research,
            # and the electromech kits; written in the v3 canonical form (KITCHECK canonicalizes, see kit_canonical)
            for x in _seeds():
                if x.get('pack') == 'kit-manager' and x.get('v3_dna'):
                    presets.append({'category': 'Machine' if 'favorite' in x else 'Genre', 'name': clean_name(x['name']),
                                    'dna': x['v3_dna'], 'ships': ['3.11', 'XP']})
            em = json.load(open(os.path.join(LIB, 'research', 'electromech-presets.json')))
            for x in em['kits']:
                presets.append({'category': 'Electromech', 'name': clean_name(x['name']), 'dna': x['dna'], 'ships': ['XP']})
            presets = kit_canonical(presets)
            src = 'kit seeds (genres.json, modern-favorites.json) + electromech kits, v3 canonical'
        elif s.get('electromech'):
            em = json.load(open(os.path.join(LIB, 'research', 'electromech-presets.json')))
            for x in em['instruments']:
                presets.append({'category': x['category'], 'name': clean_name(x['name']), 'dna': x['dna']})
            src = 'research/electromech-presets.json'
        elif s.get('aesthetic'):
            a = json.load(open(AES))['presets']
            for x in a:
                presets.append({'category': x['section'], 'name': clean_name(x['name']), 'dna': x['dna']})
            src = 'design/aesthetic-presets.json (ws-aes)'
        elif s.get('plan') or s.get('heritage'):
            for x in _seeds():
                if (s.get('plan') and x.get('pack') == s['plan']) or (s.get('heritage') and x.get('edition_badge') == 'w31'):
                    presets.append({'category': x['role'], 'name': clean_name(x['name']), 'dna': x['dna']})
            src = 'research/genres.json + modern-favorites.json seeds'
        else:
            T = _targets()
            for cat in s.get('targets', []):
                items = [x for x in T if x['category'] == cat or cat == '*']
                want = s.get('pick', {}).get(cat)
                if want:
                    items = [x for x in items if x['name'] in want]
                for x in items:
                    presets.append({'category': x['category'] if cat == '*' else cat, 'name': clean_name(x['name']), 'dna': x['dna']})
            for ex in s.get('extra', []):
                cat, spec = ex.split('/', 1)
                for x in _pick([x for x in T if x['category'] == cat], spec):
                    presets.append({'category': cat, 'name': clean_name(x['name']), 'dna': x['dna']})
            src = 'research/preset-targets.json'
        if s.get('limit'):
            presets = presets[:s['limit']]
        if s.get('kits'):
            placeholder = False      # real kit DNAs, checked by the core's v3 parser: not a placeholder
        else:
            src += ' (placeholder until library/builder has this pack)'
    ren = pk.get('rename', {})
    for p in presets:
        p['name'] = ren.get(p['name'], p['name'])
        if BRANDS.search(p['name']):
            p['name'] = clean_name(p['name'])
    seen = set()
    out = []
    for p in presets:
        if p['name'] in seen:
            continue
        seen.add(p['name'])
        cat = p['category']
        p['folder'] = folders.get(cat) or ROLE_FOLDER.get(cat) or folders.get('*') or (cat[:1].upper() + cat[1:]).replace('-', ' ')
        p['folder83'] = re.sub(r'[^A-Z0-9_]', '', p['folder'].upper())[:8] or 'PRESETS'
        out.append(p)
    out.sort(key=lambda x: x['folder'])
    _name_files(out)
    for x in out:
        x['disp'] = disp(persona, x)
        x['dfolder'], x['dfile'] = x['disp'].split('\\')
    return {'presets': out, 'sounds': sounds, 'placeholder': placeholder, 'source': src}


def short83(name, taken, ext):
    base = re.sub(r'[^A-Z0-9]', '', name.upper().replace('&', 'N'))
    words = [re.sub(r'[^A-Z0-9]', '', w.upper()) for w in name.split()]
    words = [w for w in words if w]
    if len(base) > 8 and len(words) > 1:
        # first word cut + initials of the rest, as people did by hand
        cand = (words[0][:8 - min(3, len(words) - 1)] + ''.join(w[0] for w in words[1:4]))[:8]
    else:
        cand = base[:8] or 'PRESET'
    c = cand
    i = 1
    while (c + ext) in taken:
        suf = str(i)
        c = cand[:8 - len(suf)] + suf
        i += 1
    taken.add(c + ext)
    return c + ext


def _name_files(presets):
    taken = {}
    for p in presets:
        t = taken.setdefault(p['folder83'], set())
        p['file83'] = short83(p['name'], t, '.BSP')
        p['joliet'] = re.sub(r'[\\/:*?"<>|]', '', p['name']) + '.bsp'


def disp(persona, p):
    """How the maker's own docs name a preset file: long names for XP-era makers, 8.3 for the rest."""
    if persona['maker']['year'] >= 1998:
        return '%s\\%s' % (p['folder'], p['joliet'])
    return '%s\\%s' % (p['folder83'], p['file83'])


KITCHECK = os.environ.get('KITCHECK', os.path.expanduser('~/packwork/kitcheck/kitcheck'))


def kit_canonical(presets):
    """Runs every kit DNA through the core's v3 parser (core/dna3.cpp, built as KITCHECK): keeps only real kits and
    writes them in the v3 canonical form, except where that would drop library-sound steps. Without the checker the
    DNAs are kept as written."""
    import subprocess
    if not os.path.exists(KITCHECK):
        print('  KITCHECK not built: kit DNAs kept as written')
        return presets
    r = subprocess.run([KITCHECK], input='\n'.join(p['dna'] for p in presets) + '\n', capture_output=True, text=True, check=True)
    out = []
    for p, line in zip(presets, r.stdout.splitlines()):
        pads, kit, same, layers, canon = line.split('\t', 4)
        if kit != '1':
            print('  not a kit, dropped: %s' % p['name'])
            continue
        # library sounds are unknown to the checker (no catalogue), so a canonical form that drops them is not used
        if same != '1' and canon.count('@') + canon.count('I') < p['dna'].count('@') + p['dna'].count('I'):
            pass
        else:
            p['dna'] = canon
        out.append(p)
    return out
