"""A pack's own WinHelp file: writes WinHelp authoring RTF + an .HPJ and compiles them with the help lane's hlpc.py
(packages/basilisk-synth/help/hlpc.py, branch feat/help-and-site). Topics: Contents, About this pack, the preset list
(each preset a popup with its file and DNA), Using the presets, the maker's note, the licence or registration, Credits.
The font, heading colour and wording come from the persona."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [os.environ.get('HLPC', ''), os.path.join(HERE, '..', '..', 'help', 'hlpc.py'),
              os.path.expanduser('~/ws-help/packages/basilisk-synth/help/hlpc.py')]


def hlpc_path():
    for c in CANDIDATES:
        if c and os.path.exists(c):
            return os.path.abspath(c)
    raise SystemExit('hlpc.py not found: set HLPC=/path/to/hlpc.py (branch feat/help-and-site, packages/basilisk-synth/help/)')


def esc(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch in '\\{}':
            out.append('\\' + ch)
        elif o > 126:
            try:
                b = ch.encode('cp1252')[0]
            except UnicodeEncodeError:
                b = ord('?')
            out.append("\\'%02x" % b)
        else:
            out.append(ch)
    return ''.join(out)


def rgb(h):
    h = h.lstrip('#')
    return '\\red%d\\green%d\\blue%d;' % tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Doc:
    def __init__(self, face, family, title_color):
        self.parts = ['{\\rtf1\\ansi\\deff0\n{\\fonttbl{\\f0\\f%s %s;}{\\f1\\fmodern Courier New;}}\n'
                      '{\\colortbl;\\red0\\green0\\blue0;%s\\red128\\green128\\blue128;}\n' % (family, face, rgb(title_color))]

    def topic(self, ctx, title, keys=None, browse=None, popup=False):
        fn = '#{\\footnote %s}${\\footnote %s}' % (ctx, esc(title))
        if browse:
            fn += '+{\\footnote %s}' % browse
        if keys:
            fn += 'K{\\footnote %s}' % esc(';'.join(keys))
        self.parts.append(fn + '\n')
        if popup:
            self.parts.append('\\pard\\sa60\\li115\\ri175\\plain\\f0\\fs20\\b\\cf2 %s\\par\n' % esc(title))
        else:
            self.parts.append('\\pard\\keepn\\sb120\\sa120\\li115\\ri175\\plain\\f0\\fs26\\b\\cf2 %s\\par\n' % esc(title))

    def p(self, s, raw=False, fs=20, extra=''):
        self.parts.append('\\pard\\sa80\\li115\\ri175%s\\plain\\f0\\fs%d %s\\par\n' % (extra, fs, s if raw else esc(s)))

    def mono(self, s):
        self.parts.append('\\pard\\sa40\\li395\\ri175\\plain\\f1\\fs18 %s\\par\n' % esc(s))

    def head(self, s):
        self.parts.append('\\pard\\sb115\\sa40\\li115\\ri175\\plain\\f0\\fs20\\b %s\\par\n' % esc(s))

    def link(self, text, ctx, popup=False, indent=395):
        u = 'ul' if popup else 'uldb'
        self.parts.append('\\pard\\sa30\\li%d\\ri175\\plain\\f0\\fs20 {\\%s %s}{\\v %s}\\par\n' % (indent, u, esc(text), ctx))

    def row(self, left_rtf, right):
        self.parts.append('\\pard\\sa30\\li2275\\ri175\\fi-1880\\tx2275\\plain\\f0\\fs20 %s\\tab %s\\par\n' % (left_rtf, esc(right)))

    def end(self):
        self.parts.append('\\page\n')

    def text(self):
        return ''.join(self.parts) + '}\n'


def build(p, data, workdir, out_path):
    """Writes <id>.rtf and <id>.hpj in workdir and compiles out_path. Returns the RTF text."""
    T, M, pk, H = p['text'], p['maker'], p['pack'], p['hlp']
    d = Doc(H['font'], H['family'], H['title_color'])
    lic_name = p['files']['license']
    shareware = lic_name == 'REGISTER.TXT'

    d.topic('contents', '%s Help Contents' % pk['title'], ['contents', pk['title']], 'main:010')
    d.p('{\\b %s}%s' % (esc(pk['title']), (' ' + esc(pk.get('edition', ''))) if pk.get('edition') else ''), raw=True, fs=24)
    d.p(T['tagline'], extra='\\qc' if M['kind'].startswith('BBS') else '')
    d.p('by %s, %s' % (M['name'], M['place']))
    d.head('Contents')
    d.link('About This Pack', 'about')
    d.link('The Presets', 'presets')
    d.link('Using the Presets', 'using')
    d.link("A Note from %s" % M['short'] if not M['kind'].startswith('BBS') else 'word from the group', 'note')
    d.link('How to Register' if shareware else 'License', 'license')
    d.link('Credits and Contact', 'credits')
    if H.get('link_note'):
        d.p(H['link_note'])
    d.end()

    d.topic('about', 'About This Pack', ['about', pk['title']], 'main:020')
    for x in T['intro']:
        d.p(x)
    if T.get('abstract'):
        d.head('Abstract')
        d.p(T['abstract'])
    for x in T.get('intro_de', []):
        d.p('{\\i %s}' % esc(x), raw=True)
    d.head('On this disc')
    d.row('{\\b %s}' % esc(pk['label']), 'volume label (%s)' % pk['label_long'])
    nx = sum(1 for x in data['presets'] if 'XP' in x.get('ships', ['XP']))
    d.row('{\\b %d}' % len(data['presets']), 'presets in %d folders (%d also play on BASILISK SYNTH)' % (len({x['folder'] for x in data['presets']}), nx))
    d.row('{\\b %s}' % esc(p['files']['pdf']), 'the printed manual, as a PDF')
    d.end()

    d.topic('presets', 'The Presets', ['presets', 'DNA'], 'main:030')
    d.p('Click a name to see its file and its DNA. Double-click the file in the Library tab to load it.')
    cur = None
    for i, x in enumerate(data['presets']):
        if x['folder'] != cur:
            cur = x['folder']
            d.head('\\%s' % cur)
        d.link(x['name'], 'p%03d' % i, popup=True)
    if data['placeholder']:
        d.p('{\\i Preview disc: the presets are placeholders until the library is built.}', raw=True)
    d.end()

    d.topic('using', 'Using the Presets', ['install', 'using', 'Library tab'], 'main:040')
    for i, x in enumerate(T['install']):
        d.p('%d.  %s' % (i + 1, x), extra='\\fi-280\\li395')
    d.end()

    d.topic('note', 'A Note from %s' % M['name'], ['note', M['short']], 'main:050')
    for x in T['maker_note']:
        d.p(x)
    d.end()

    d.topic('license', 'How to Register' if shareware else 'License', ['license', 'register', 'copying'], 'main:060')
    if shareware:
        R = p['register']
        d.p('%s is SHAREWARE. Try it for 30 days. If you keep using it, please register: $%.2f plus $%.2f shipping.'
            % (pk['title'], R['price'], R['shipping']))
        d.p('Registered users get %s, and free updates by mail.' % R['bonus'])
        d.head('Send your check or money order to')
        for c in M['contact'][:4]:
            d.mono(c)
        d.p('Or print ORDER.FRM from the disc and mail it.')
    else:
        for x in T['license']:
            d.p(x)
    d.end()

    d.topic('credits', 'Credits and Contact', ['credits', 'contact', 'support'], 'main:070')
    for a, b in M['people']:
        d.row('{\\b %s}' % esc(a), b)
    d.head('Contact')
    for c in M['contact']:
        d.mono(c)
    d.p('Pictures: public-domain engravings and photographs (see CREDITS in the manual).', fs=16)
    d.p('All names in this pack are fictional.', fs=16)
    d.end()

    for i, x in enumerate(data['presets']):
        d.topic('p%03d' % i, x['name'], popup=True)
        d.p('File: \\\\%s' % x['disp'].replace('\\', '\\\\'), raw=True, fs=18)
        d.mono(x['dna'])
        sh = x.get('ships', ['3.11', 'XP'])
        d.p('Plays on: %s' % ('BASILISK 16 and BASILISK SYNTH' if 'XP' in sh and '3.11' in sh else
                              'BASILISK 16 only' if '3.11' in sh else 'BASILISK SYNTH (library disc sounds)'), fs=16)
        d.end()

    rtf = d.text()
    os.makedirs(workdir, exist_ok=True)
    stem = p['id']
    with open(os.path.join(workdir, stem + '.rtf'), 'w', encoding='latin-1', newline='\r\n') as f:
        f.write(rtf)
    hpj = ('[OPTIONS]\nTITLE=%s Help\nCOPYRIGHT=%s\nCONTENTS=contents\n\n[FILES]\n%s.rtf\n\n[CONFIG]\nBrowseButtons()\n'
           % (pk['title'], T.get('copyright') or ('%s %d' % (M['name'], M['year'])), stem))
    hpj = hpj.encode('cp1252', 'ignore').decode('cp1252').replace('  ', ' ')
    with open(os.path.join(workdir, stem + '.hpj'), 'w', encoding='cp1252', newline='\r\n') as f:
        f.write(hpj)
    import calendar, datetime
    epoch = calendar.timegm(datetime.date.fromisoformat(pk['date']).timetuple()) + 12 * 3600
    env = dict(os.environ, SOURCE_DATE_EPOCH=str(epoch))
    r = subprocess.run([sys.executable, hlpc_path(), os.path.join(workdir, stem + '.hpj'), '-o', out_path],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        raise SystemExit('hlpc failed for %s:\n%s%s' % (p['id'], r.stdout, r.stderr))
    return rtf
