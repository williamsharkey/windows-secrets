"""Word-processor manuals: Windows Write 3.x (.WRI) and RTF (WordPad / Word 6).

A manual is a list of blocks: ('h1', text) ('h2', text) ('p', text) ('mono', text) ('center', text) ('bullet', text).
"""
import struct


# ------------------------------------------------------------------------------------------------ Write 3.x

def _fkp(fc_first, fods, props):
    """One 128-byte formatting page. fods: [(fcLim, prop_index or None)], props: list of bytes (cch-prefixed later)."""
    page = bytearray(128)
    struct.pack_into('<I', page, 0, fc_first)
    # properties packed from the end (before the cfod byte), FODs from the front
    end = 127
    offs = []
    for pr in props:
        blob = bytes([len(pr)]) + pr
        end -= len(blob)
        page[end:end + len(blob)] = blob
        offs.append(end - 4)
    pos = 4
    for fclim, pi in fods:
        struct.pack_into('<IH', page, pos, fclim, 0xFFFF if pi is None else offs[pi])
        pos += 6
    assert pos <= end, 'FKP overflow'
    page[127] = len(fods)
    return bytes(page)


def write_wri(path, blocks, fonts=('Times New Roman', 'Arial', 'Courier New')):
    """Windows Write (3.0/3.1) file. Fonts: 0 body (roman), 1 headings (swiss), 2 mono (modern)."""
    runs = []  # (text bytes, chp bytes, pap bytes)

    def chp(ftc=0, hps=24, bold=False, italic=False):
        # byte0 = 1 (reserved), byte1 = bold | italic<<1 | ftc<<2, byte2 = hps, byte3 = 0 (underline etc.)
        return bytes([1, (1 if bold else 0) | (2 if italic else 0) | ((ftc & 63) << 2), hps])

    def pap(jc=0, left=0, first=0, before=0, after=0):
        b = bytearray(17)
        b[0] = 61           # reserved, 61 as Write writes it
        b[1] = jc
        struct.pack_into('<h', b, 4, 0)        # dxaRight
        struct.pack_into('<h', b, 6, left)     # dxaLeft
        struct.pack_into('<h', b, 8, first)    # dxaLeft1
        struct.pack_into('<h', b, 10, 240)     # dyaLine
        # bytes 12-15 are reserved in Write (it has no space before/after); blank lines give the spacing
        b[16] = 0           # rhc: normal text
        return bytes(b)

    for kind, s in blocks:
        t = s.encode('cp1252', errors='replace') + b'\r\n'
        if kind == 'h1':
            runs.append((t, chp(1, 36, bold=True), pap(1, before=0, after=240)))
        elif kind == 'h2':
            runs.append((t, chp(1, 24, bold=True), pap(0, before=240, after=120)))
        elif kind == 'center':
            runs.append((t, chp(0, 24, italic=True), pap(1, after=120)))
        elif kind == 'mono':
            runs.append((t, chp(2, 20), pap(0, left=720)))
        elif kind == 'bullet':
            runs.append((b'\x95\t' + t, chp(0, 24), pap(0, left=720, first=-360, after=60)))
        else:
            runs.append((t, chp(0, 24), pap(0, after=120)))
        if kind in ('h1', 'p', 'center'):
            runs.append((b'\r\n', chp(0, 24), pap(0)))
        if kind == 'h2':
            pass

    text = b''.join(r[0] for r in runs)
    fc_mac = 128 + len(text)
    pn_char = (fc_mac + 127) // 128

    def pages(kind):
        """Groups runs into formatting pages; one FOD per run, identical properties shared within a page."""
        out = []
        fc = 128
        first, fods, props = 128, [], []
        for t, c, pp in runs:
            prop = c if kind == 'c' else pp
            lim = fc + len(t)
            new_props = props if prop in props else props + [prop]
            need = 4 + 6 * (len(fods) + 1) + sum(len(x) + 1 for x in new_props) + 1
            if need > 128:
                out.append(_fkp(first, fods, props))
                first, fods, new_props = fc, [], [prop]
            props = new_props
            fods.append((lim, props.index(prop)))
            fc = lim
        out.append(_fkp(first, fods, props))
        return out

    char_pages = pages('c')
    para_pages = pages('p')
    pn_para = pn_char + len(char_pages)
    pn_ffntb = pn_para + len(para_pages)
    fam = {0: 1, 1: 2, 2: 3}   # FF_ROMAN=1, FF_SWISS=2, FF_MODERN=3 (ffid = family)
    ff = struct.pack('<H', len(fonts))
    for i, name in enumerate(fonts):
        nm = name.encode('cp1252') + b'\0'
        ff += struct.pack('<HB', 1 + len(nm), fam[i] << 4) + nm
    ff += struct.pack('<H', 0)
    ff += b'\0' * ((-len(ff)) % 128)
    pn_mac = pn_ffntb + len(ff) // 128

    hdr = bytearray(128)
    struct.pack_into('<HHH', hdr, 0, 0o137061, 0, 0o125400)
    struct.pack_into('<I', hdr, 14, fc_mac)
    # pnPara, pnFntb, pnSep, pnSetb, pnPgtb, pnFfntb (no footnotes, sections or page table)
    struct.pack_into('<HHHHHH', hdr, 18, pn_para, pn_ffntb, pn_ffntb, pn_ffntb, pn_ffntb, pn_ffntb)
    struct.pack_into('<H', hdr, 96, pn_mac)
    body = bytes(hdr) + text
    body += b'\0' * (pn_char * 128 - len(body))
    data = body + b''.join(char_pages) + b''.join(para_pages) + ff
    with open(path, 'wb') as f:
        f.write(data)


# ------------------------------------------------------------------------------------------------ RTF

def _resc(s):
    out = []
    for ch in s:
        if ch in '\\{}':
            out.append('\\' + ch)
        elif ord(ch) > 126:
            try:
                out.append("\\'%02x" % ch.encode('cp1252')[0])
            except UnicodeEncodeError:
                out.append('?')
        else:
            out.append(ch)
    return ''.join(out)


def write_rtf(path, blocks, body_font='Arial', head_font='Arial', mono_font='Courier New', accent='#000000', title=''):
    a = accent.lstrip('#')
    r, g, b = (int(a[i:i + 2], 16) for i in (0, 2, 4))
    L = ['{\\rtf1\\ansi\\ansicpg1252\\deff0',
         '{\\fonttbl{\\f0\\fswiss\\fcharset0 %s;}{\\f1\\fswiss\\fcharset0 %s;}{\\f2\\fmodern\\fcharset0 %s;}}' % (body_font, head_font, mono_font),
         '{\\colortbl;\\red0\\green0\\blue0;\\red%d\\green%d\\blue%d;}' % (r, g, b),
         '{\\info{\\title %s}}' % _resc(title), '\\paperw11906\\paperh16838\\margl1134\\margr1134\\margt1134\\margb1134', '']
    for kind, s in blocks:
        t = _resc(s)
        if kind == 'h1':
            L.append('\\pard\\qc\\sa240\\plain\\f1\\fs36\\b\\cf2 %s\\par' % t)
        elif kind == 'h2':
            L.append('\\pard\\sb240\\sa120\\plain\\f1\\fs24\\b\\cf2 %s\\par' % t)
        elif kind == 'center':
            L.append('\\pard\\qc\\sa120\\plain\\f0\\fs20\\i %s\\par' % t)
        elif kind == 'mono':
            L.append('\\pard\\li567\\plain\\f2\\fs18 %s\\par' % t)
        elif kind == 'bullet':
            L.append('\\pard\\li567\\fi-284\\sa60\\plain\\f0\\fs20 \\bullet\\tab %s\\par' % t)
        elif kind == 'page':
            L.append('\\page')
        else:
            L.append('\\pard\\sa120\\plain\\f0\\fs20 %s\\par' % t)
    L.append('}')
    with open(path, 'wb') as f:
        f.write('\r\n'.join(L).encode('ascii'))
