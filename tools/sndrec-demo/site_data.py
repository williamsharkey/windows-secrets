#!/usr/bin/env python3
"""Merge encode.py's manifest.json files into the page's preset list, with the source sounds of every preset.

    site_data.py OUT.json EDITION=RENDER_DIR[@MACHINE_DIR] [...] [--recipe-cli recipe_cli]

--recipe-cli: recipe_cli.cpp built against the recipe converter (design/v3/recipe.{h,cpp}, PRESET-ENGINE-2.md 17);
each preset then gets `rec`: the one-line and multi-line recipes, exactly as the converter writes them, checked to
round-trip. A kit (pads in the globals) also gets its pads one per line, for the page's summary and disclosure.

MACHINE_DIR (BASILISK 16: the release bundle's Contents/Resources/machine) supplies drive.zip, to measure the
C:\\WINDOWS sounds, and library.zip's LIBRARY.TSV, the library disc as it ships (path, seconds, credit).

Each preset gets `src`: one entry per distinct sound its DNA names (every layer's SOURCE and every I/M file), in DNA
order. A name is resolved as the plugin does (DNA.md 2.4, 5.2): the edition's built-in table first, then the library
disc. On 3.11 the XP-only built-in names play DING.WAV (DNA.md appendix), and are marked as that fallback. Sound
facts come from packages/basilisk-synth/library: catalog/*.json (author, licence, source, description, how a
synthesized sound was made) and research/windows-sounds.json (root notes of the Windows files).
"""
import glob, io, json, os, re, struct, sys, zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
LIB = os.path.join(REPO, 'packages', 'basilisk-synth', 'library')
PLUGIN = {'b16': 'BASILISK 16', 'xp': 'BASILISK SYNTH'}

# DNA.md 2.4: NAME -> XP file (C:\WINDOWS\Media)
XP_NAMES = {'chimes': 'chimes.wav', 'chord': 'chord.wav', 'ding': 'ding.wav', 'notify': 'notify.wav', 'recycle': 'recycle.wav',
            'ringin': 'ringin.wav', 'ringout': 'ringout.wav', 'start': 'start.wav', 'tada': 'tada.wav'}
for n, f in {'balloon': 'Balloon', 'batcrit': 'Battery Critical', 'batlow': 'Battery Low', 'critstop': 'Critical Stop',
             'default': 'Default', 'xpding': 'Ding', 'error': 'Error', 'exclaim': 'Exclamation', 'hwfail': 'Hardware Fail',
             'hwin': 'Hardware Insert', 'hwout': 'Hardware Remove', 'infobar': 'Information Bar', 'logoff': 'Logoff Sound',
             'logon': 'Logon Sound', 'menu': 'Menu Command', 'minimize': 'Minimize', 'xpnotify': 'Notify',
             'popup': 'Pop-up Blocked', 'print': 'Print complete', 'xprecycle': 'Recycle', 'restore': 'Restore',
             'xpringin': 'Ringin', 'xpringout': 'Ringout', 'shutdown': 'Shutdown', 'startup': 'Startup', 'xpstart': 'Start'}.items():
    XP_NAMES[n] = 'Windows XP %s.wav' % f
# BASILISK 16 (README 1.2.0): C:\WINDOWS holds WfW 3.11's four, plus Windows 3.1's CHORD and TADA (machine-extra/)
W311 = {'chimes': ('CHIMES.WAV', '311'), 'ding': ('DING.WAV', '311'), 'ringin': ('RINGIN.WAV', '311'),
        'ringout': ('RINGOUT.WAV', '311'), 'chord': ('CHORD.WAV', '31'), 'tada': ('TADA.WAV', '31')}


def wav_facts(b):
    i = b.find(b'fmt ')
    fmt, ch, sr, br, ba, bits = struct.unpack('<HHIIHH', b[i + 8:i + 24])
    j = b.find(b'data')
    n = struct.unpack('<I', b[j + 4:j + 8])[0]
    return round(n / br, 2), 'PCM %d Hz %d-bit %s' % (sr, bits, 'mono' if ch == 1 else 'stereo')


def research_roots():
    d = json.load(open(os.path.join(LIB, 'research', 'windows-sounds.json')))
    roots = {}
    for s in d['sounds']:
        key = (s['os'], s['name'].lower())
        roots[key] = s
    return d['sounds']


def find_research(sounds, filename, os_hint):
    for s in sounds:
        if s['name'].lower() == filename.lower() and os_hint in s['os']:
            return s
    for s in sounds:
        if s['name'].lower() == filename.lower():
            return s
    return None


def catalog():
    cat = {}
    for f in glob.glob(os.path.join(LIB, 'catalog', '*.json')):
        for e in json.load(open(f)):
            cat[e['id'].replace('#', 's')] = e   # disc names write '#' as 's' (make_library.py)
    return cat


def root_of(name, e):
    if e.get('labelled_note'): return e['labelled_note']
    if not e.get('tonal'): return None
    m = re.search(r'_([a-g])(s?)(\d)$', name)
    return (m.group(1).upper() + ('#' if m.group(2) else '') + m.group(3)) if m else None


def dna_names(dna):
    out = []
    for layer in dna.split(';', 1)[0].split('/'):
        m = re.match(r'[a-z0-9_]+', layer)
        if m: out.append(m.group(0))
        for m in re.finditer(r'[IM]([a-z0-9_]+)', layer[m.end() if m else 0:]):
            out.append(m.group(1))
    seen, res = set(), []
    for n in out:
        if n not in seen: seen.add(n); res.append(n)
    return res


def core_tables(src=os.path.join(REPO, 'packages', 'basilisk-synth', 'core', 'dna.cpp')):
    """kSoundNames, kSoundFilesXP and kSoundFiles311 from core/dna.cpp (DNA.md 2.4: one name, one file)"""
    c = open(src).read()
    def arr(name):
        body = re.search(r'%s\[kSoundCount\] = \{(.*?)\};' % name, c, re.S).group(1)
        return [x.encode().decode('unicode_escape') for x in re.findall(r'"((?:[^"\\]|\\.)*)"', body)]
    return arr('kSoundNames'), arr('kSoundFilesXP'), arr('kSoundFiles311')


def display_name(n):   # core::displayName: chimesxp chordxp dingxp tadaxp are written chimes-xp ... in recipes and here
    return n[:-2] + '-xp' if n in ('chimesxp', 'chordxp', 'dingxp', 'tadaxp') else n


def sound_table_311(machine, names, cat, research):
    tab = {}
    drive = zipfile.ZipFile(os.path.join(machine, 'drive.zip'))
    libz = zipfile.ZipFile(os.path.join(machine, 'library.zip'))
    knames, kxp, k311 = core_tables()
    tsv = {}
    for line in libz.read('LIBRARY.TSV').decode('latin1').splitlines():
        p = line.split('\t')
        if len(p) >= 5 and not line.startswith('#'): tsv[p[0]] = p
    for n in names:
        if n in knames:
            i = knames.index(n); path = k311[i]
            dur, fmt = wav_facts(drive.read(path[3:].replace('\\', '/')))
            xpfile = kxp[i].split('\\')[-1]
            if i in (0, 2):     # chimes ding: Windows for Workgroups 3.11's own
                r = find_research(research, path.split('\\')[-1], 'Workgroups') or {}
                o, frm = '311', 'Windows for Workgroups 3.11'
            elif i in (1, 8):   # chord tada: Windows 3.1's (3.11's disks dropped them)
                r = find_research(research, path.split('\\')[-1], '3.1 /') or {}
                o, frm = '31', 'Windows 3.1 (added to C:\\WINDOWS; WfW 3.11 had dropped it)'
            elif i in (5, 6):   # ringin ringout: the same bytes in 3.11 and XP
                r = find_research(research, xpfile, 'XP') or {}
                o, frm = 'both', 'Windows for Workgroups 3.11, byte-identical to Windows XP\'s copy'
            else:               # an XP file, converted to PCM that SOUNDREC opens
                r = find_research(research, xpfile, 'XP') or {}
                o, frm = 'xp', 'Windows XP (%s), converted to PCM that Sound Recorder 3.1 opens%s' % (
                    xpfile, ('; XP\'s own %s' % r['format']) if r.get('format') else '')
            tab[n] = {'o': o, 'd': display_name(n), 'file': path.split('\\')[-1], 'path': path, 'dur': dur, 'fmt': fmt,
                      'root': r.get('root'), 'what': r.get('character'), 'from': frm}
        elif n in tsv:
            p = tsv[n]; e = cat.get(n, {})
            lic = e.get('license', p[4].split(', ')[-1])
            syn = bool(e.get('synth_method'))
            tab[n] = {'o': 'syn' if syn else ('cc0' if 'CC0' in lic else 'pd'), 'file': p[2].split('\\')[-1],
                      'path': 'L:' + p[2], 'dur': float(p[3]), 'fmt': 'PCM 22050 Hz 16-bit mono (converted for Sound Recorder 3.1)',
                      'root': root_of(n, e), 'what': e.get('description'), 'author': e.get('author', p[4].rsplit(', ', 1)[0]),
                      'lic': lic, 'url': e.get('source_url'), 'how': e.get('synth_method'),
                      'from': 'Library disc (%s)' % p[1]}
        else:
            tab[n] = {'o': 'unk', 'from': 'Unknown name: the layer is silent'}
    return tab


def recipes(cli, dnas, names_file):
    import subprocess
    r = subprocess.run([cli] + ([names_file] if names_file else []), input='\n'.join(dnas) + '\n', capture_output=True, text=True, check=True)
    out = {}
    for line in r.stdout.splitlines():
        x = json.loads(line)
        if not x['ok']: sys.exit('recipe does not round-trip: ' + x['dna'])
        # ASCII (toRecipe: what is copied and typed) and pretty (prettify: what is shown), PRESET-ENGINE-2.md 17.1b
        rec = {'one': x['one'], 'lines': x['lines'], 'pone': x['pone'], 'plines': x['plines']}
        env, penv = (x['lines'][-1], x['plines'][-1]) if x['lines'] and x['lines'][-1].startswith('env ') else (None, None)
        if env and re.search(r'(^|  )pad \d', env.split(None, 1)[1]):
            # a kit: the converter writes each pad as a "pad ..." phrase in the env line (ASCII: two spaces between
            # phrases, pretty: " · "); list them one per line, in both forms
            parts = list(zip(env.split(None, 1)[1].split('  '), penv.split(None, 1)[1].split(' \u00b7 ')))
            if any(len(a.split('  ')) != 1 for a, _ in parts) or len(env.split(None, 1)[1].split('  ')) != len(penv.split(None, 1)[1].split(' \u00b7 ')):
                sys.exit('kit phrases do not line up: ' + x['dna'])
            pads = [pp for pp in parts if pp[0].startswith('pad ')]
            rest = [pp for pp in parts if not pp[0].startswith('pad ')]
            nums = set()
            for pd, _ in pads:
                m = re.match(r'pad (\d+)', pd)
                if m: nums.add(int(m.group(1)))   # a pad, or a pitched range of keys, by its first key
            rec['kit'] = {'n': len(nums), 'pads': [a for a, _ in pads], 'ppads': [b for _, b in pads],
                          'layers': x['lines'][:-1], 'players': x['plines'][:-1],
                          'env': ('env      ' + '  '.join(a for a, _ in rest)) if rest else None,
                          'penv': ('env      ' + ' \u00b7 '.join(b for _, b in rest)) if rest else None}
        out[x['dna']] = rec
    return out


class Iso:
    """just enough ISO 9660 + Joliet to read files by their real names (the XP library disc)"""
    def __init__(self, path):
        self.f = open(path, 'rb'); self.root = None
        for sec in range(16, 32):
            self.f.seek(sec * 2048); vd = self.f.read(2048)
            if vd[0] == 2 and vd[88:91] in (b'%/@', b'%/C', b'%/E'):   # Joliet supplementary descriptor
                self.root = (struct.unpack('<I', vd[158:162])[0], struct.unpack('<I', vd[166:170])[0])
            if vd[0] == 255: break

    def entries(self, ext, size):
        self.f.seek(ext * 2048); d = self.f.read(size); p = 0; out = {}
        while p < len(d):
            l = d[p]
            if l == 0: p = (p // 2048 + 1) * 2048; continue
            nl = d[p + 32]; raw = d[p + 33:p + 33 + nl]
            if raw not in (b'\x00', b'\x01'):
                out[raw.decode('utf-16-be').split(';')[0].lower()] = (struct.unpack('<I', d[p + 2:p + 6])[0], struct.unpack('<I', d[p + 10:p + 14])[0])
            p += l
        return out

    def read(self, path):
        ext, size = self.root
        for part in [x for x in path.replace('\\', '/').split('/') if x]:
            ext, size = self.entries(ext, size)[part.lower()]
        self.f.seek(ext * 2048); return self.f.read(size)


def sound_table_xp(machine, names, cat, research):
    tab = {}
    iso = Iso(os.path.join(machine, 'library.iso'))
    tsv = {}
    for line in iso.read('LIBRARY.TSV').decode('utf-8', 'replace').splitlines():
        p = line.split('\t')
        if len(p) >= 5 and not line.startswith('#'): tsv[p[0]] = p
    for n in names:
        if n in XP_NAMES:
            f = XP_NAMES[n]; r = find_research(research, f, 'XP') or {}
            tab[n] = {'o': 'xp', 'file': f, 'path': 'C:\\WINDOWS\\Media\\' + f, 'dur': r.get('duration'), 'fmt': r.get('format'),
                      'root': r.get('root'), 'what': r.get('character'), 'from': 'Windows XP'}
        elif n in tsv:
            p = tsv[n]; e = cat.get(n, {})
            lic = e.get('license', p[4].split(', ')[-1]); syn = bool(e.get('synth_method'))
            try: dur, fmt = wav_facts(iso.read(p[2]))
            except Exception: dur, fmt = float(p[3]), None
            tab[n] = {'o': 'syn' if syn else ('cc0' if 'CC0' in lic else 'pd'), 'file': p[2].split('\\')[-1],
                      'path': 'library disc ' + p[2], 'dur': dur, 'fmt': fmt, 'root': root_of(n, e), 'what': e.get('description'),
                      'author': e.get('author', p[4].rsplit(', ', 1)[0]), 'lic': lic, 'url': e.get('source_url'),
                      'how': e.get('synth_method'), 'from': 'Library disc (%s)' % p[1]}
        else:
            tab[n] = {'o': 'unk', 'from': 'Unknown name: the layer is silent'}
    return tab


def pack(ed, cat):
    if ed == 'b16':
        if cat == 'BASILISK 16': return '3.11 originals'
        if cat.startswith('B16 '): return 'Library disc'
    if cat == 'Library': return 'Library disc'
    return 'Factory'


def main():
    out = {'editions': {}}
    cat, research = catalog(), research_roots()
    args = sys.argv[2:]
    cli = None
    if '--recipe-cli' in args:
        i = args.index('--recipe-cli'); cli = args[i + 1]; del args[i:i + 2]
    for arg in args:
        ed, rest = arg.split('=', 1)
        d, _, machine = rest.partition('@')
        rows = json.load(open(d + '/manifest.json'))
        names = []
        for r in rows: names += [n for n in dna_names(r['dna']) if n not in names]
        sounds = {} if not machine else sound_table_311(machine, names, cat, research) if ed == 'b16' else sound_table_xp(machine, names, cat, research)
        names_file = None
        if machine and os.path.exists(os.path.join(machine, 'library.names.txt')): names_file = os.path.join(machine, 'library.names.txt')
        elif machine and ed == 'xp':   # the XP disc's names, for the recipe converter
            names_file = os.path.join(d, 'library.names.txt')
            open(names_file, 'w').write('\n'.join(l.split('\t')[0] for l in Iso(os.path.join(machine, 'library.iso')).read('LIBRARY.TSV').decode('utf-8', 'replace').splitlines() if l and not l.startswith('#')) + '\n')
        recs = recipes(cli, [r['dna'] for r in rows], names_file) if cli else {}
        out['editions'][ed] = {'plugin': PLUGIN.get(ed, ed), 'sounds': sounds, 'presets': [{
            'n': r['i'], 'cat': r['cat'].replace('B16 ', '') if r['cat'] != 'BASILISK 16' else 'Classic', 'program': r['cat'] + ': ' + r['name'],
            'pack': pack(ed, r['cat']), 'name': r['name'], 'dna': r['dna'], 'phrase': r['phrase'], 'src': dna_names(r['dna']), 'rec': recs.get(r['dna']),
            'file': ('sndrec/audio/%s/%s' % (ed, r['file'])) if r['file'] else None, 'sec': r['render_seconds'],
            'wave': [round(x * 100) for x in r['wave']], 'flags': [f for f in r['flags'] if not f.startswith('hot')],
            'hot': next((f for f in r['flags'] if f.startswith('hot')), None), 'note': r.get('note'),
            'macro': r.get('macro_curve') is not None,
            # DNA.md 2.4: a DNA's edition is xp when it uses any XP file, else w31 (library sounds do not count)
            'ed': 'xp' if any(sounds.get(n, {}).get('o') == 'xp' for n in dna_names(r['dna'])) else 'w31'} for r in rows]}
        from collections import Counter
        print(ed, len(rows), 'presets,', len(sounds), 'sounds', dict(Counter(s['o'] for s in sounds.values())))
    json.dump(out, open(sys.argv[1], 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
