"""The plain-text files on a pack's disc, written in the maker's own habits.

Every function returns {DISC_NAME: bytes}. Text files use CR LF. Encodings: CP437 for .NFO / FILE_ID.DIZ (DOS art),
Windows-1252 for the rest, Shift-JIS for the Japanese readme."""
import datetime
import textwrap

from PIL import Image, ImageDraw

from . import gfx


def _crlf(s):
    return s.replace('\r\n', '\n').replace('\n', '\r\n')


def enc(s, codec='cp1252'):
    return _crlf(s).encode(codec, errors='replace')


def para(s, width=76, indent=''):
    return textwrap.fill(s, width, initial_indent=indent, subsequent_indent=indent)


def date_of(p):
    return datetime.date.fromisoformat(p['pack']['date'])


def preset_table(data, width=76, dna=True):
    out = []
    cur = None
    for p in data['presets']:
        if p['dfolder'] != cur:
            cur = p['dfolder']
            out.append('')
            out.append('  \\%s' % cur)
        line = '    %-12s  %s' % (p['dfile'], p['name']) if p['dfile'] != p['joliet'] else '    ' + p['dfile']
        out.append(line)
        if dna:
            out.append(textwrap.fill(p['dna'], width, initial_indent=' ' * 18, subsequent_indent=' ' * 18, break_on_hyphens=False))
    return '\n'.join(out)


# ------------------------------------------------------------------------------------------- block-letter logos

def block_logo(word, fontfile='ariblk.ttf', rows=6, shade=True):
    """Renders a word into CP437 half-block art (rows text lines tall). Returns a list of unicode strings."""
    px = rows * 2
    f = gfx.font(fontfile, int(px * 1.25))
    w = int(gfx.text_w(word, f, 1)) + 4
    im = Image.new('1', (w, px + 4), 0)
    d = ImageDraw.Draw(im)
    gfx.text(d, (1, px + 1), word, f, 1, anchor='ls', spacing=1)
    bb = im.getbbox()
    im = im.crop((bb[0], bb[1], bb[2], bb[3]))
    # squash to exactly px pixels high, keep width (terminal cells are 1:2)
    im = im.resize((im.width, px), Image.NEAREST)
    a = [[im.getpixel((x, y)) for x in range(im.width)] for y in range(px)]
    lines = []
    for r in range(rows):
        top, bot = a[2 * r], a[2 * r + 1]
        s = ''
        for x in range(im.width):
            t, b = top[x], bot[x]
            s += '█' if t and b else '▀' if t else '▄' if b else ' '
        lines.append(s)
    if shade:  # a light shadow one cell right and below
        H, W = len(lines), len(lines[0]) + 1
        grid = [list(l + ' ') for l in lines] + [[' '] * W]
        for y in range(H - 1, -1, -1):
            for x in range(W - 2, -1, -1):
                if lines[y][x] != ' ' and grid[y + 1][x + 1] == ' ':
                    grid[y + 1][x + 1] = '░'
        lines = [''.join(r).rstrip() for r in grid]
    return lines


def center(s, width=79):
    return s.center(width).rstrip()


# ------------------------------------------------------------------------------------------- styles

def nfo_style(p, data):
    """BBS group: an .NFO in CP437 with block letters and box drawing, FILE_ID.DIZ, a short README.TXT, GREETS.TXT."""
    T, M, pk = p['text'], p['maker'], p['pack']
    W = 79
    logo = block_logo(T.get('nfo_logo') or pk['title'], rows=6)
    L = []
    L += [''] + [center(l, W) for l in logo] + ['']
    L.append(center('·:·  ' + M['name'].lower() + '  ·  ' + pk['subtitle'] + '  ·:·', W))
    L.append('')
    top = '╔' + '═' * 75 + '╗'
    bot = '╚' + '═' * 75 + '╝'

    def box(title, body):
        L.append('  ' + top)
        L.append('  ║ ' + ('▓▒░ ' + title + ' ░▒▓').center(73) + ' ║')
        L.append('  ╟' + '─' * 75 + '╢')
        for b in body:
            for ln in (textwrap.wrap(b, 71) or ['']):
                L.append('  ║  ' + ln.ljust(73) + '║')
        L.append('  ' + bot)
        L.append('')

    d = date_of(p)
    box('release info', ['title ........ ' + pk['title'], 'group ........ ' + M['name'].lower(),
                         'date ......... ' + d.strftime('%m/%d/%y'), 'type ......... presets for basilisk 16 / basilisk synth',
                         'size ......... %d presets, 1 cd' % len(data['presets']), 'label ........ ' + pk['label']])
    NH = T.get('nfo_heads', {})
    box(NH.get('intro', 'about'), T['intro'])
    box(NH.get('list', 'tracklist'), ['%-2d  %-22s  \\%s\\%s' % (i + 1, x['name'].lower(), x['dfolder'], x['dfile']) for i, x in enumerate(data['presets'])])
    box('how to', T['install'])
    box('members', ['%-16s %s' % (a, b) for a, b in M['people']])
    box('call', M['contact'])
    box('word from the group', T['maker_note'])
    L.append(center('"' + T['nfo_quote'] + '"', W))
    L.append('')
    L.append(center('░▒▓█ ' + M['short'] + ' ' + str(M['year']) + ' █▓▒░', W))
    nfo = '\n'.join(L) + '\n'
    files = {p['files']['nfo']: enc(nfo, 'cp437')}
    previews = {p['files']['nfo']: nfo}
    if p['files'].get('diz'):
        diz = diz_text(p, data)
        files['FILE_ID.DIZ'] = enc(diz, 'cp437')
        previews['FILE_ID.DIZ'] = diz
    rd = ('%s by %s\n\nread %s with a dos viewer or notepad with the terminal font.\n'
          'help: %s    zine: %s\n\n%s\n' % (pk['title'], M['name'].lower(), p['files']['nfo'], p['files']['hlp'],
                                            p['files']['pdf'], '\n'.join(T['install'])))
    files['README.TXT'] = enc(rd)
    previews['README.TXT'] = rd
    g = T['greets_note'] + '\n\n' + '\n'.join('  ' + x for x in T['greets']) + '\n\n-- ' + M['short'].lower() + '\n'
    files['GREETS.TXT'] = enc(g)
    lic = '\n\n'.join(para(x, 70) for x in T['license']) + '\n'
    files[p['files']['license']] = enc(lic)
    return files, previews


def diz_text(p, data):
    """FILE_ID.DIZ: at most 10 lines of at most 45 characters."""
    pk, M = p['pack'], p['maker']
    head = '%s v%s' % (pk['title'][:28], pk['version'])
    if p['text'].get('diz'):
        lines = [l.center(45) if not l.startswith(('▄', '▀', '─', '=', '-')) else l for l in p['text']['diz']]
    else:
        lines = [head.upper(), '-' * 44] + textwrap.wrap(p['text']['blurb'], 44)[:5] + \
                ['SHAREWARE $%.2f  %s' % (p['register']['price'], M['name'].upper())[:44] if p.get('register') else M['name'][:44]]
        lines = lines[:10]
    return '\n'.join(l.rstrip() for l in lines) + '\n'


def shareware_style(p, data):
    T, M, pk, R = p['text'], p['maker'], p['pack'], p['register']
    W = 76
    bar = '=' * W
    title = '%s  Version %s' % (pk['title'].upper(), pk['version'])
    L = [bar, center(title, W), center(pk['subtitle'], W), center('Copyright (C) %d by %s' % (date_of(p).year, M['contact'][0]), W),
         center('All Rights Reserved', W), bar, '', center('*** THIS IS SHAREWARE ***', W),
         center('Please see REGISTER.TXT to register your copy.', W), '']
    sec = lambda t: L.extend(['', t.upper(), '-' * len(t)])
    sec('Introduction')
    L += [para(x, W) + '\n' for x in T['intro']]
    sec('Getting started')
    L += ['  %d. %s' % (i + 1, para(x, W - 6).replace('\n', '\n     ')) for i, x in enumerate(T['install'])]
    sec('What is on this disc')
    files = [('README.TXT', 'This file'), ('REGISTER.TXT', 'How to register (please do!)'), ('ORDER.FRM', 'Order form to print and mail'),
             ('VENDOR.TXT', 'Information for shareware distributors'), ('WHATSNEW.TXT', 'Version history'),
             (p['files']['hlp'], 'Windows Help file'), (p['files']['wri'], 'The manual, for Windows Write'),
             (p['files']['pdf'], 'The manual, for Acrobat Reader'), ('FILE_ID.DIZ', 'Description for BBS sysops'),
             (', '.join(sorted({x['dfolder'] + '\\' for x in data['presets']}))[:16], 'The presets (*.BSP)')]
    L += ['  %-16s %s' % f for f in files]
    sec('The presets')
    L.append(preset_table(data, W, dna=False))
    sec('Shareware')
    L += [para(x, W) + '\n' for x in T['maker_note'][:-1]]
    sec('How to reach me')
    L += ['  ' + c for c in M['contact']]
    L += ['', bar, center('Thank you for supporting SHAREWARE!', W), bar]
    rd = '\n'.join(L) + '\n'
    reg = register_text(p)
    order = order_form(p)
    vendor = '\n'.join(['VENDOR.TXT - %s %s' % (pk['title'].upper(), pk['version']), '=' * 40, ''] + [para(x, W) + '\n' for x in T['vendor']]) + '\n'
    wn = '\n'.join(['WHATSNEW.TXT - %s' % pk['title'].upper(), '=' * 40, ''] +
                   ['Version %-5s %s\n%s\n' % (v, d, para(t, W, '    ')) for v, d, t in T['history']]) + '\n'
    out = {'README.TXT': rd, 'REGISTER.TXT': reg, 'ORDER.FRM': order, 'VENDOR.TXT': vendor, 'WHATSNEW.TXT': wn}
    if p['files'].get('diz'):
        out['FILE_ID.DIZ'] = diz_text(p, data)
    files = {k: enc(v, 'cp437' if k.endswith('.DIZ') else 'cp1252') for k, v in out.items()}
    return files, out


def register_text(p):
    T, M, pk, R = p['text'], p['maker'], p['pack'], p['register']
    W = 76
    L = ['REGISTERING %s' % pk['title'].upper(), '=' * 40, '',
         para('%s is not free software. It is SHAREWARE. You may use it for 30 days to see if it suits you. If you use '
              'it after 30 days, you must register it. Registration costs $%.2f plus $%.2f shipping ($%.2f outside the '
              'USA and Canada).' % (pk['title'], R['price'], R['shipping'], R['foreign_shipping']), W), '',
         'When you register, you get:', '',
         '  * %s' % R['bonus'], '  * free updates by mail for one year', '  * telephone and BBS support', '  * no more "please register" reminders', '',
         para(R['site'], W), '',
         para('%s residents please add %.1f%% sales tax. Send a check or money order in US dollars, drawn on a US bank, '
              'to:' % (R['tax_state'], R['tax_rate'] * 100), W), '']
    L += ['      ' + c for c in M['contact'][:4]] + ['', 'Or print ORDER.FRM, fill it in and mail it with your payment.', '',
                                                     'Thank you!  -- ' + M['contact'][0]]
    return '\n'.join(L) + '\n'


def order_form(p):
    M, pk, R = p['maker'], p['pack'], p['register']
    W = 72
    line = lambda a, b='': '%-46s %s' % (a, b)
    L = ['+' + '-' * (W - 2) + '+', '|' + ('ORDER FORM - %s %s' % (pk['title'].upper(), pk['version'])).center(W - 2) + '|',
         '+' + '-' * (W - 2) + '+', '', 'Remit to:  ' + M['contact'][1]] + ['           ' + c for c in M['contact'][2:4]] + ['',
         line('Name  ______________________________________'), '', line('Address ____________________________________'), '',
         line('City/State/ZIP _____________________________'), '', line('Online service or BBS ID (opt.) ____________'), '',
         line('Where did you get your copy? ______________'), '', '-' * W,
         line('%s registration' % pk['title'], '____ x $%6.2f = $______' % R['price']),
         line('Site license (10 or more computers)', '____ x $  5.00 = $______'),
         line('Shipping (USA/Canada $%.2f, other $%.2f)' % (R['shipping'], R['foreign_shipping']), '               $______'),
         line('%s residents add %.1f%% sales tax' % (R['tax_state'], R['tax_rate'] * 100), '               $______'),
         line('', '         TOTAL $______'), '-' * W, '', 'Disk size:  [ ] 3.5" 1.44MB    [ ] 5.25" 1.2MB    [ ] CD-ROM (+$4.00)', '',
         'Comments: ___________________________________________________________', '',
         '__________________________________________________________________', '']
    return '\n'.join(L) + '\n'


def corporate_style(p, data):
    T, M, pk = p['text'], p['maker'], p['pack']
    W = 76
    L = ['%s %s' % (pk['title'], pk.get('subtitle', '')), pk.get('edition', '') + ', version ' + pk['version'],
         T.get('copyright', ''), '', 'README.TXT', '-' * 76, '',
         'This file contains important information that is not in the User\'s Guide. Please read it before you use the product.', '',
         'CONTENTS', '  1. Introduction', '  2. Getting Started', '  3. Contents of the Disc', '  4. Technical Support', '',
         '1. INTRODUCTION', '']
    L += [para(x, W) + '\n' for x in T['intro']]
    L += ['2. GETTING STARTED', '']
    L += [para('* ' + x, W, '').replace('\n', '\n  ') for x in T['install']]
    L += ['', '3. CONTENTS OF THE DISC', '', preset_table(data, W, dna=False), '',
          '4. TECHNICAL SUPPORT', ''] + ['  ' + c for c in M['contact']] + ['']
    for k, v in p['maker'].items():
        if k == 'distributor':
            L += [v, '']
    L += [T.get('copyright', '')]
    rd = '\n'.join(L) + '\n'
    files = {'README.TXT': enc(rd)}
    prev = {'README.TXT': rd}
    lic = '\n\n'.join(para(x, W) for x in T['license']) + '\n'
    files[p['files']['license']] = enc(lic)
    prev[p['files']['license']] = lic
    if T.get('y2k'):
        y = '\n\n'.join(para(x, W) for x in T['y2k']) + '\n'
        files['Y2K.TXT'] = enc(y)
        prev['Y2K.TXT'] = y
    if p['files'].get('readme_ja'):
        j = [M['name_ja'], T['ja_title'], '=' * 38, ''] + T['intro_ja'] + ['', '■ご使用方法'] + ['  ' + x for x in T['install_ja']] + \
            ['', '■お問い合わせ'] + ['  ' + c for c in M['contact']] + ['', T['copyright']]
        js = '\n'.join(j) + '\n'
        files[p['files']['readme_ja']] = enc(js, 'shift_jis')
        prev[p['files']['readme_ja']] = js
    return files, prev


def german_style(p, data):
    T, M, pk = p['text'], p['maker'], p['pack']
    W = 72
    head = lambda t: ['', t, '~' * len(t)]
    de = ['LIESMICH.TXT', '%s %s, %s' % (pk['title'], pk['subtitle'], pk['edition']), T['copyright'], '']
    de += head('1. Allgemeines') + [para(x, W) + '\n' for x in T['intro_de']]
    de += head('2. Installation') + ['  %d) %s' % (i + 1, para(x, W - 6).replace('\n', '\n     ')) for i, x in enumerate(T['install_de'])]
    de += head('3. Inhalt der CD') + [preset_table(data, W, dna=True)]
    de += head('4. Kontakt') + ['  ' + c for c in M['contact']] + ['', 'Bielefeld, im %s' % ['Januar', 'Februar', 'Maerz', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'][date_of(p).month - 1] + ' %d' % date_of(p).year]
    en = ['README.TXT', '%s %s, %s' % (pk['title'], pk['subtitle'], pk['edition']), T['copyright'], '',
          'The German text is in LIESMICH.TXT. The manual is HANDBUCH.RTF (Write/WordPad) and HANDBUCH.PDF.', '']
    en += head('1. General') + [para(x, W) + '\n' for x in T['intro']]
    en += head('2. Installation') + ['  %d) %s' % (i + 1, para(x, W - 6).replace('\n', '\n     ')) for i, x in enumerate(T['install'])]
    en += head('3. Contents of the CD') + [preset_table(data, W, dna=True)]
    en += head('4. Contact') + ['  ' + c for c in M['contact']]
    lic = '\n\n'.join(para(x, W) for x in T['license']) + '\n'
    out = {'LIESMICH.TXT': '\n'.join(de) + '\n', 'README.TXT': '\n'.join(en) + '\n', p['files']['license']: lic}
    return {k: enc(v) for k, v in out.items()}, out


def academic_style(p, data):
    T, M, pk = p['text'], p['maker'], p['pack']
    W = 72
    d = date_of(p)
    L = ['', center(M['name'].upper(), W), center(M['contact'][2], W), '', center('Technical Report ' + pk['edition'].split()[-1], W),
         center(d.strftime('%B %Y'), W), '', center(pk['title'] + ': ' + pk['subtitle'], W), '',
         center(' and '.join(a for a, _ in M['people'][:2]), W), '', '-' * W, 'README for the ' + pk['label'] + ' disc', '-' * W, '',
         'ABSTRACT', '']
    L += [para(T['abstract'], W, '   '), '', '1. CONTENTS OF THIS DISC', '']
    L += ['   README.TXT     this file', '   INDEX.TXT      one line per preset: folder, file, name, DNA', '   COPYING.TXT    terms of use',
          '   TR9407.PDF     the technical report (letter, 6 pages)', '   DRIFTS.HLP     on-line help version (Windows Help)',
          '   DRONES\\        five drones', '   FIELDS\\        six fields (slowly changing pads)', '',
          '2. USE', ''] + ['   ' + para(x, W - 3).replace('\n', '\n   ') for x in T['install']]
    L += ['', '3. AVAILABILITY', '', '   ' + M['contact'][3], '   ' + M['contact'][4], '',
          '4. ACKNOWLEDGEMENTS', '', '   ' + para(T['maker_note'][0], W - 3).replace('\n', '\n   '), '']
    idx = '\n'.join('%s\t%s\t%s\t%s' % (x['folder'], x['file83'], x['name'], x['dna']) for x in data['presets']) + '\n'
    lic = '\n\n'.join(para(x, W) for x in T['license']) + '\n'
    out = {'README.TXT': '\n'.join(L) + '\n', 'INDEX.TXT': idx, p['files']['license']: lic}
    return {k: enc(v) for k, v in out.items()}, out


def extra_texts(p):
    """text.files: {NAME: [paragraphs]}: any further plain-text file a maker habitually put on its discs.
    A paragraph starting with '|' is kept as one line, unwrapped."""
    out = {}
    for name, paras in p['text'].get('files', {}).items():
        body = '\n\n'.join(x[1:] if x.startswith('|') else para(x, 72) for x in paras) + '\n'
        out[name] = body
    return out


STYLES = {'nfo': nfo_style, 'shareware': shareware_style, 'corporate': corporate_style, 'german': german_style, 'academic': academic_style}


def pack_inf(p, data):
    pk, M = p['pack'], p['maker']
    nx = sum(1 for x in data['presets'] if 'XP' in x.get('ships', ['XP']))
    inf = ('[Pack]\nId=%s\nTitle=%s\nVersion=%s\nAuthor=%s\nLicence=%s\nDate=%s\nPresets=%d\nPresetsXP=%d\nDescription=%s\n'
           % (pk.get('plan_id') or p['id'], pk['title'], pk['version'], M['name'], p['files']['license'], pk['date'], len(data['presets']), nx,
              p['text']['blurb']))
    return inf


def autorun_inf(p):
    return '[autorun]\nlabel=%s\nicon=%s\n' % (p['pack']['label_long'], 'PACK.ICO')
