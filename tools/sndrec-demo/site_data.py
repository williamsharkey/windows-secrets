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


def sound_table_311(machine, names, cat, research):
    tab = {}
    drive = zipfile.ZipFile(os.path.join(machine, 'drive.zip'))
    libz = zipfile.ZipFile(os.path.join(machine, 'library.zip'))
    tsv = {}
    for line in libz.read('LIBRARY.TSV').decode('latin1').splitlines():
        p = line.split('\t')
        if len(p) >= 5 and not line.startswith('#'): tsv[p[0]] = p
    for n in names:
        if n in W311:
            f, o = W311[n]
            dur, fmt = wav_facts(drive.read('WINDOWS/' + f))
            r = find_research(research, f, 'Workgroups') if o == '311' else find_research(research, f, '3.1 /')
            if n in ('ringin', 'ringout'): r = find_research(research, n + '.wav', 'XP')   # the same 11 kHz files
            tab[n] = {'o': o, 'file': f, 'path': 'C:\\WINDOWS\\' + f, 'dur': dur, 'fmt': fmt, 'root': r and r.get('root'),
                      'what': (r or {}).get('character'),
                      'from': 'Windows for Workgroups 3.11' if o == '311' else 'Windows 3.1 (added to C:\\WINDOWS; WfW 3.11 had dropped it)'}
        elif n in XP_NAMES:
            dur, fmt = wav_facts(drive.read('WINDOWS/DING.WAV'))
            tab[n] = {'o': 'fb', 'file': 'DING.WAV', 'path': 'C:\\WINDOWS\\DING.WAV', 'dur': dur, 'fmt': fmt, 'root': 'G5',
                      'xp': XP_NAMES[n], 'from': 'Windows XP name: Windows 3.11 has no such file, so DING.WAV plays instead'}
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
        rec = {'one': x['one'], 'lines': x['lines']}
        env = x['lines'][-1] if x['lines'] and x['lines'][-1].startswith('env ') else None
        if env and ' · pad ' in ' · ' + env.split(None, 1)[1]:
            # a kit: the converter writes each pad as a "pad ..." phrase in the env line; list them one per line
            parts = [p for p in env.split(None, 1)[1].split(' · ')]
            pads = [p for p in parts if p.startswith('pad ')]
            rest = [p for p in parts if not p.startswith('pad ')]
            nums = set()
            for pd in pads:
                m = re.match(r'pad (\d+)(?:\u2013(\d+))?', pd)
                if m: nums.add(int(m.group(1)))   # a pad, or a pitched range of keys, by its first key
            rec['kit'] = {'pads': pads, 'n': len(nums), 'layers': x['lines'][:-1], 'env': 'env     ' + ' · '.join(rest) if rest else None}
        out[x['dna']] = rec
    return out


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
        sounds = sound_table_311(machine, names, cat, research) if ed == 'b16' and machine else {}
        recs = recipes(cli, [r['dna'] for r in rows], os.path.join(machine, 'library.names.txt') if machine else None) if cli else {}
        out['editions'][ed] = {'plugin': PLUGIN.get(ed, ed), 'sounds': sounds, 'presets': [{
            'n': r['i'], 'cat': r['cat'].replace('B16 ', '') if r['cat'] != 'BASILISK 16' else 'Classic', 'program': r['cat'] + ': ' + r['name'],
            'pack': pack(ed, r['cat']), 'name': r['name'], 'dna': r['dna'], 'phrase': r['phrase'], 'src': dna_names(r['dna']), 'rec': recs.get(r['dna']),
            'file': ('sndrec/audio/%s/%s' % (ed, r['file'])) if r['file'] else None, 'sec': r['render_seconds'],
            'wave': [round(x * 100) for x in r['wave']], 'flags': [f for f in r['flags'] if not f.startswith('hot')],
            'hot': next((f for f in r['flags'] if f.startswith('hot')), None), 'note': r.get('note'),
            'macro': r.get('macro_curve') is not None} for r in rows]}
        from collections import Counter
        print(ed, len(rows), 'presets,', len(sounds), 'sounds', dict(Counter(s['o'] for s in sounds.values())))
    json.dump(out, open(sys.argv[1], 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
