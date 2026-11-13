#!/usr/bin/env python3
"""mkrtf - turns help.txt (one source for both editions) into the WinHelp topic files bsynth.rtf and basil16.rtf.

    mkrtf.py help.txt xp  bsynth.rtf
    mkrtf.py help.txt 311 basil16.rtf

The RTF it writes is plain WinHelp 3.1 authoring RTF (the kind HC31 reads, and hlpc.py reads), so the .rtf files can
also be opened in a word processor of the period.

Source format, one paragraph per line:
  %topic ID [popup]    a new topic (ID is its context string). popup: a glossary popup (no browse, small heading)
  %title TITLE         its title (Search shows it; also the heading)
  %keys a;b;c          its keywords for Search
  %map N               its help context number (for WinHelp HELP_CONTEXT)
  %col TWIPS           width of the first column of tables in this topic (default 1440)
  ## Text              a subheading
  - Text               a bullet
  + Text               an indented line (lists of links, as in the Contents)
  1. Text              a numbered step
  | left | right       a table row: left column, tab, right column
  > Text               a note, indented
  :xp line / :311 line the line is only in that edition
  ; comment
  anything else        a body paragraph
Inline: `code` (Courier), **bold**, *italic*, [text](ctx) a jump, [text](!ctx) a popup, {NAME} {WIN} ... edition
words (see WORDS), {xp:text|311:text} edition text.
"""
import re
import sys

WORDS = {
    'xp': {'NAME': 'BASILISK SYNTH', 'WIN': 'Windows XP', 'SR': 'sndrec32.exe', 'HLP': 'BSYNTH.HLP',
           'NPRESETS': '39', 'LAT': '100 ms', 'KEYS': '37 keys, C3 to C6', 'PCKEYS': 'PC keys',
           'SYNTHDIR': 'C:\\synth', 'OTHER': 'BASILISK 16, the Windows 3.11 edition',
           'LIBDRIVE': 'the CD drive', 'VIEWER': 'Windows Help (winhlp32.exe)'},
    '311': {'NAME': 'BASILISK 16', 'WIN': 'Windows 3.11', 'SR': 'SOUNDREC.EXE', 'HLP': 'BASIL16.HLP',
            'NPRESETS': '71', 'LAT': '60 ms', 'KEYS': 'five octaves, C2 to C7', 'PCKEYS': 'Keys',
            'SYNTHDIR': 'C:\\BS', 'OTHER': 'BASILISK SYNTH, the Windows XP edition',
            'LIBDRIVE': 'drive L:', 'VIEWER': 'Windows Help (WINHELP.EXE)'},
}

HEAD = r'''{\rtf1\ansi\deff0
{\fonttbl{\f0\fswiss Helv;}{\f1\fmodern Courier;}}
{\colortbl;\red0\green0\blue0;\red0\green0\blue128;}
'''
BODY = r'\pard\sa60\li115\ri175\plain\f0\fs20 '


def esc(s):
    out = []
    for ch in s:
        o = ord(ch)
        if ch in '\\{}':
            out.append('\\' + ch)
        elif o > 126:
            b = ch.encode('cp1252')[0]
            if 0x80 <= b <= 0x9f:
                raise SystemExit('mkrtf: %r is not in the Windows 3.1 character set' % ch)
            out.append("\\'%02x" % b)
        else:
            out.append(ch)
    return ''.join(out)


def words(s, ed):
    s = re.sub(r'\{xp:([^|}]*)\|311:([^}]*)\}', lambda m: m.group(1) if ed == 'xp' else m.group(2), s)
    return re.sub(r'\{([A-Z]+)\}', lambda m: WORDS[ed][m.group(1)], s)


def inline(s, ed, refs):
    s = words(s, ed)
    out, i = [], 0
    pat = re.compile(r'`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*|\[([^\]]+)\]\((!?)([A-Za-z0-9_.]+)\)')
    for m in pat.finditer(s):
        out.append(esc(s[i:m.start()]))
        if m.group(1) is not None:
            out.append(r'{\f1 %s}' % esc(m.group(1)))
        elif m.group(2) is not None:
            out.append(r'{\b %s}' % esc(m.group(2)))
        elif m.group(3) is not None:
            out.append(r'{\i %s}' % esc(m.group(3)))
        else:
            refs.add(m.group(6))
            out.append(r'{\%s %s}{\v %s}' % ('ul' if m.group(5) else 'uldb', esc(m.group(4)), m.group(6)))
        i = m.end()
    out.append(esc(s[i:]))
    return ''.join(out)


def convert(src, ed):
    refs, ctxs, maps = set(), set(), {}
    out = [HEAD]
    topic = None
    col = 1440
    lines = src.split('\n')
    pending = []

    def flush_head():
        nonlocal topic
        if topic is None or topic.get('written'):
            return
        t = topic
        fn = '#{\\footnote %s}' % t['id']
        if t.get('title'):
            fn += '${\\footnote %s}' % esc(t['title'])
            if not t['popup']:
                fn += '+{\\footnote main:%03d}' % t['seq']
        if t.get('keys'):
            fn += 'K{\\footnote %s}' % esc(t['keys'])
        out.append(fn + '\n')
        if t.get('title'):
            if t['popup']:
                out.append(r'\pard\sb60\sa60\li115\ri175\plain\f0\fs20\b %s\par' % esc(t['title']) + '\n')
            else:
                out.append(r'\pard\keepn\sb120\sa120\li115\ri175\plain\f0\fs24\b %s\par' % esc(t['title']) + '\n')
        t['written'] = True

    seq = 0
    for raw in lines:
        line = raw.rstrip()
        m = re.match(r':(xp|311) (.*)', line)
        if m:
            if m.group(1) != ed:
                continue
            line = m.group(2)
        if not line.strip() or line.startswith(';'):
            continue
        line = words(line, ed)
        if line.startswith('%topic '):
            if topic is not None:
                flush_head()
                out.append('\\page\n')
            parts = line.split()
            seq += 10
            topic = {'id': parts[1], 'popup': 'popup' in parts[2:], 'seq': seq}
            if topic['id'] in ctxs:
                raise SystemExit('mkrtf: topic %s twice' % topic['id'])
            ctxs.add(topic['id'])
            col = 1440
            continue
        if line.startswith('%title '):
            topic['title'] = words(line[7:], ed)
            continue
        if line.startswith('%keys '):
            topic['keys'] = words(line[6:], ed)
            continue
        if line.startswith('%map '):
            maps[topic['id']] = int(line[5:])
            continue
        if line.startswith('%col '):
            col = int(line[5:])
            continue
        flush_head()
        li = 115 + col
        if line.startswith('## '):
            out.append(r'\pard\sb115\sa25\li115\ri175\plain\f0\fs20\b %s\par' % inline(line[3:], ed, refs))
        elif line.startswith('+ '):
            out.append(r'\pard\sa30\li395\ri175\plain\f0\fs20 %s\par' % inline(line[2:], ed, refs))
        elif line.startswith('- '):
            out.append(r'\pard\sa40\li395\ri175\fi-275\tx395\plain\f0\fs20 \'b7\tab %s\par' % inline(line[2:], ed, refs))
        elif re.match(r'\d+\. ', line):
            n, rest = line.split('. ', 1)
            out.append(r'\pard\sa40\li395\ri175\fi-275\tx395\plain\f0\fs20 %s\tab %s\par' % (n, inline(rest, ed, refs)))
        elif line.startswith('| '):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            out.append(r'\pard\sa30\li%d\ri175\fi-%d\tx%d\plain\f0\fs20 %s\tab %s\par' % (
                li, col, li, inline(cells[0], ed, refs), inline(cells[1] if len(cells) > 1 else '', ed, refs)))
        elif line.startswith('> '):
            out.append(r'\pard\sb40\sa60\li395\ri175\plain\f0\fs20 %s\par' % inline(line[2:], ed, refs))
        else:
            out.append(BODY + inline(line, ed, refs) + r'\par')
        out.append('\n')
    flush_head()
    out.append('}\n')
    missing = sorted(refs - ctxs)
    if missing:
        raise SystemExit('mkrtf (%s): links to missing topics: %s' % (ed, ', '.join(missing)))
    return ''.join(out), maps


def main():
    src, ed, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    rtf, maps = convert(open(src, encoding='utf-8').read(), ed)
    open(dst, 'w', encoding='cp1252', newline='\r\n').write(rtf)
    items = sorted(maps.items(), key=lambda x: x[1])
    if len(sys.argv) > 4:          # the [MAP] list hlpc reads (context string, number)
        open(sys.argv[4], 'w', newline='\r\n').write(''.join('%s %d\n' % kv for kv in items))
    if len(sys.argv) > 5:          # the same numbers for the guests' C code: WinHelp(w, file, HELP_CONTEXT, HELPID_...)
        open(sys.argv[5], 'w', newline='\n').write(
            '/* generated by help/mkrtf.py from help/help.txt - the help context numbers of BSYNTH.HLP and BASIL16.HLP\n'
            '   (the same in both). Use: WinHelp(hwnd, path, HELP_CONTEXT, HELPID_KEYBOARD); */\n'
            '#ifndef BASILISK_HELPIDS_H\n#define BASILISK_HELPIDS_H\n' +
            ''.join('#define HELPID_%s %d\n' % (k.upper(), v) for k, v in items) + '#endif\n')


if __name__ == '__main__':
    main()
