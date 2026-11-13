#!/usr/bin/env python3
"""hlpc - a small Windows Help (.HLP) compiler, written for BASILISK SYNTH.

    hlpc.py PROJECT.HPJ [-o OUT.HLP]
    hlpc.py --dump FILE.HLP            print the topics of a .HLP as plain text (a self-check)

It reads a help project (.HPJ) and the Rich Text Format topic files it names, in the WinHelp conventions that
Microsoft's HC31 reads, and writes a Windows 3.1 help file (format version 1.21, LZ77-compressed topic blocks, no
phrase table). WINHELP.EXE on Windows 3.1/3.11 and WINHLP32.EXE on Windows 95 to XP open it.

The file format follows "Windows Help File Format" by M. Winterhoff (helpfile.txt in helpdeco, GPL) and was checked
against the help files of Windows for Workgroups 3.11. No Microsoft tool is used.

Supported RTF (what the topic files use):
  \\page ends a topic.  Footnotes: # context string(s), $ title, K keywords (separated by ;), + browse sequence,
  ! macros run when the topic opens.  {\\uldb text}{\\v context} is a jump; {\\ul text}{\\v context} is a popup;
  {\\strike ...} is also a jump.  \\keepn paragraphs at the top of a topic form its non-scrolling region.
  \\par \\line \\tab \\pard \\plain \\b \\i \\f \\fs \\cf \\li \\ri \\fi \\sb \\sa \\sl \\qc \\qr \\ql \\tx \\tqr \\tqc,
  \\'hh, \\~, \\-, \\{ \\} \\\\, \\fonttbl and \\colortbl.  Everything else is ignored.
Supported HPJ: [OPTIONS] TITLE, COPYRIGHT, CONTENTS; [FILES]; [CONFIG] (one macro per line).
"""
import os
import re
import struct
import sys
import time

# ------------------------------------------------------------------------------------------------ LZ77

def lz77_compress(data):
    """WinHelp's LZ77: a flag byte (LSB first), then per bit a literal byte (0) or a 16-bit back-reference (1) whose
    low 12 bits are distance-1 and high 4 bits are length-3 (lengths 3..18, distances 1..4096)."""
    out = bytearray()
    n = len(data)
    i = 0
    heads = {}
    while i < n:
        flag_at = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len, best_dist = 0, 0
            if i + 3 <= n:
                key = data[i:i + 3]
                for j in reversed(heads.get(key, ())):
                    d = i - j
                    if d > 4096:
                        break
                    ln = 3
                    while ln < 18 and i + ln < n and data[j + ln] == data[i + ln]:
                        ln += 1
                    if ln > best_len:
                        best_len, best_dist = ln, d
                        if ln == 18:
                            break
            step = best_len if best_len >= 3 else 1
            if best_len >= 3:
                flags |= 1 << bit
                out += struct.pack('<H', ((best_len - 3) << 12) | (best_dist - 1))
            else:
                out.append(data[i])
            for k in range(i, i + step):
                if k + 3 <= n:
                    lst = heads.setdefault(data[k:k + 3], [])
                    lst.append(k)
                    if len(lst) > 64:
                        del lst[:32]
            i += step
        out[flag_at] = flags
    return bytes(out)


def lz77_expand(b):
    out = bytearray()
    i = 0
    while i < len(b):
        bits = b[i]
        i += 1
        for k in range(8):
            if i >= len(b):
                break
            if bits & (1 << k):
                w = b[i] | b[i + 1] << 8
                i += 2
                s = len(out) - (w & 0xfff) - 1
                for _ in range((w >> 12) + 3):
                    out.append(out[s])
                    s += 1
            else:
                out.append(b[i])
                i += 1
    return bytes(out)

# ------------------------------------------------------------------------------------------------ small encodings

def c_ushort(v):          # compressed unsigned short
    return bytes([v * 2]) if v < 128 else bytes([((v & 127) << 1) | 1, v >> 7])


def c_short(v):           # compressed signed short
    if -64 <= v < 64:
        return bytes([(v + 64) * 2])
    x = v + 16384
    return bytes([((x & 127) << 1) | 1, x >> 7])


def c_long(v):            # compressed signed long
    if -16384 <= v < 16384:
        return struct.pack('<H', (v + 16384) * 2)
    return struct.pack('<L', ((v + 67108864) * 2 + 1) & 0xffffffff)


_HASH = bytes.fromhex(
    '00d1d2d3d4d5d6d7d8d9dadbdcdddedf' 'e0e1e2e3e4e5e6e7e8e9eaebecedeeef'
    'f00bf2f3f4f5f6f7f8f9fafbfcfd0cff' '0a0102030405060708090a0b0c0d0e0f'
    '101112131415161718191a1b1c1d1e1f' '202122232425262728292a0b0c0d0e0d'
    '101112131415161718191a1b1c1d1e1f' '202122232425262728292a2b2c2d2e2f'
    '505152535455565758595a5b5c5d5e5f' '606162636465666768696a6b6c6d6e6f'
    '707172737475767778797a7b7c7d7e7f' '808182830b85868788898a8b8c8d8e8f'
    '909192939495969798999a9b9c9d9e9f' 'a0a1a2a3a4a5a6a7a8a9aaabacadaeaf'
    'b0b1b2b3b4b5b6b7b8b9babbbcbdbebf' 'c0c1c2c3c4c5c6c7c8c9cacbcccdcecf')


def ctx_hash(name):
    h = 0
    for ch in name.encode('latin1'):
        t = _HASH[ch]
        if t >= 128:
            t -= 256
        h = (h * 43 + t) & 0xffffffff
    if h >= 1 << 31:
        h -= 1 << 32
    return h

# ------------------------------------------------------------------------------------------------ B+ trees and the file

def btree(structure, leaves, page_size=2048, flags=0x0002):
    """leaves: sorted list of (index_key_bytes, leaf_entry_bytes). Builds a one- or two-level B+ tree."""
    pages, firsts = [], []
    cur, cur_first = [], None
    room = page_size - 8
    for key, ent in leaves:
        if cur and sum(map(len, cur)) + len(ent) > room:
            pages.append(cur); firsts.append(cur_first)
            cur, cur_first = [], None
        if not cur:
            cur_first = key
        cur.append(ent)
    if cur or not pages:
        pages.append(cur); firsts.append(cur_first)
    npages = len(pages)
    out = []
    for i, ents in enumerate(pages):
        body = b''.join(ents)
        out.append(struct.pack('<Hhhh', page_size - 8 - len(body), len(ents), i - 1 if i else -1,
                               i + 1 if i + 1 < npages else -1) + body + bytes(page_size - 8 - len(body)))
    if npages == 1:
        root, levels = 0, 1
    else:
        idx = b''.join(firsts[i] + struct.pack('<h', i) for i in range(1, npages))
        if len(idx) + 6 > page_size:
            raise SystemExit('hlpc: B+ tree too large for two levels')
        out.append(struct.pack('<Hhh', page_size - 6 - len(idx), npages - 1, 0) + idx + bytes(page_size - 6 - len(idx)))
        root, levels = npages, 2
    st = structure.encode().ljust(16, b'\0')
    hdr = struct.pack('<HHH', 0x293B, flags, page_size) + st + struct.pack('<hhhhhhl', 0, 0, root, -1, len(out), levels,
                                                                           len(leaves))
    return hdr + b''.join(out), [firsts[i] for i in range(npages)]


def write_hlp(path, internal):
    """internal: {name: bytes}. Writes the help file: header, internal files, directory B+ tree."""
    body = bytearray(16)
    offs = {}
    for name in sorted(internal, key=lambda s: s.encode('latin1')):
        data = internal[name]
        offs[name] = len(body)
        body += struct.pack('<llB', len(data) + 9, len(data), 4) + data
    leaves = [(n.encode('latin1') + b'\0', n.encode('latin1') + b'\0' + struct.pack('<l', offs[n]))
              for n in sorted(internal, key=lambda s: s.encode('latin1'))]
    tree, _ = btree('z4', leaves, page_size=1024, flags=0x0402)
    dirstart = len(body)
    body += struct.pack('<llB', len(tree) + 9, len(tree), 4) + tree
    struct.pack_into('<llll', body, 0, 0x00035F3F, dirstart, -1, len(body))
    with open(path, 'wb') as f:
        f.write(body)

# ------------------------------------------------------------------------------------------------ RTF reading

class CharProps:
    __slots__ = ('f', 'fs', 'b', 'i', 'ul', 'uldb', 'strike', 'v', 'cf', 'up')

    def __init__(self):
        self.f, self.fs, self.b, self.i = 0, 24, False, False
        self.ul = self.uldb = self.strike = self.v = False
        self.cf, self.up = 0, False

    def copy(self):
        c = CharProps()
        for k in self.__slots__:
            setattr(c, k, getattr(self, k))
        return c


class ParaProps:
    __slots__ = ('li', 'ri', 'fi', 'sb', 'sa', 'sl', 'align', 'keepn', 'tabs', 'tabkind')

    def __init__(self):
        self.li = self.ri = self.fi = self.sb = self.sa = self.sl = 0
        self.align, self.keepn, self.tabs, self.tabkind = 0, False, [], 0

    def copy(self):
        p = ParaProps()
        for k in self.__slots__:
            setattr(p, k, getattr(self, k))
        p.tabs = list(self.tabs)
        return p


class Topic:
    def __init__(self):
        self.ctx, self.title, self.keywords, self.browse, self.macros = [], None, [], None, []
        self.paras = []            # [(ParaProps, items)] items: ('t', text, fontkey) | ('line',) | ('tab',) | hotspots


def tokenize(src):
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c in '{}':
            yield (c,)
            i += 1
        elif c == '\\':
            m = re.compile(r"\\([a-zA-Z]+)(-?\d+)? ?").match(src, i)
            if m:
                yield ('cw', m.group(1), int(m.group(2)) if m.group(2) is not None else None)
                i = m.end()
            elif src.startswith("\\'", i):
                yield ('text', chr(int(src[i + 2:i + 4], 16)))
                i += 4
            else:
                yield ('sym', src[i + 1])
                i += 2
        elif c in '\r\n':
            i += 1
        else:
            j = i
            while j < n and src[j] not in '{}\\\r\n':
                j += 1
            yield ('text', src[i:j])
            i = j


FAMILY = {'fnil': 3, 'froman': 2, 'fswiss': 3, 'fmodern': 1, 'fscript': 4, 'fdecor': 5, 'ftech': 3}


def parse_rtf(src, fonts, colors):
    """Returns a list of Topic. fonts: {num: (face, family)} filled from \\fonttbl; colors: list of RGB."""
    topics = [Topic()]
    cp, pp = CharProps(), ParaProps()
    stack = []
    dest = None                 # None, 'fonttbl', 'colortbl', 'footnote', 'skip'
    dest_depth = 0
    depth = 0
    items = []                  # items of the paragraph being built
    foot = []
    ft_num, ft_fam, ft_name = 0, 3, ''
    col = [0, 0, 0]
    pending_hot = []            # indexes in items of the run that may become a hotspot
    hot_kind = None
    hidden = ''
    foot_mark = None

    def fontkey():
        return (cp.f, cp.fs, cp.b, cp.i, cp.cf)

    def flush_hidden():
        nonlocal hidden, pending_hot, hot_kind
        if hidden and pending_hot:
            target = hidden.strip()
            kind = 'popup' if hot_kind == 'ul' else 'jump'
            first = pending_hot[0]
            items.insert(first, ('hot', kind, target))
            items.append(('endhot',))
        hidden = ''
        pending_hot, hot_kind = [], None

    def end_para():
        flush_hidden()
        topics[-1].paras.append((pp.copy(), list(items)))
        items.clear()

    def emit(text):
        nonlocal hot_kind, pending_hot
        if cp.v:
            nonlocal hidden
            hidden += text
            return
        if hidden:
            flush_hidden()
        kind = 'uldb' if (cp.uldb or cp.strike) else 'ul' if cp.ul else None
        if kind:
            if hot_kind not in (None, kind):
                pending_hot = []
            hot_kind = kind
            pending_hot.append(len(items))
        else:
            pending_hot, hot_kind = [], None
        items.append(('t', text, fontkey()))

    for tok in tokenize(src):
        if tok[0] == '{':
            stack.append((cp.copy(), pp.copy(), dest))
            depth += 1
            continue
        if tok[0] == '}':
            if dest == 'fonttbl' and ft_name.strip():
                fonts[ft_num] = (ft_name.strip().rstrip(';').strip(), ft_fam)
                ft_name = ''
            if dest == 'footnote' and depth == dest_depth:
                txt = ''.join(foot).strip()
                foot.clear()
                if txt:
                    if foot_mark and txt[0] != foot_mark:
                        txt = foot_mark + ' ' + txt
                    mark, val = txt[0], txt[1:].strip()
                    t = topics[-1]
                    if mark == '#':
                        t.ctx += [x.strip() for x in val.split(';') if x.strip()]
                    elif mark == '$':
                        t.title = val
                    elif mark == 'K':
                        t.keywords += [x.strip() for x in val.split(';') if x.strip()]
                    elif mark == '+':
                        t.browse = val or 'auto'
                    elif mark == '!':
                        t.macros += [x.strip() for x in val.split(';') if x.strip()]
            cp, pp, dest = stack.pop()
            depth -= 1
            continue
        kind = tok[0]
        if dest == 'skip':
            continue
        if kind == 'cw':
            w, a = tok[1], tok[2]
            if dest == 'fonttbl':
                if w == 'f':
                    if ft_name.strip():
                        fonts[ft_num] = (ft_name.strip().rstrip(';').strip(), ft_fam)
                    ft_num, ft_name, ft_fam = a, '', 3
                elif w in FAMILY:
                    ft_fam = FAMILY[w]
                continue
            if dest == 'colortbl':
                if w in ('red', 'green', 'blue'):
                    col[('red', 'green', 'blue').index(w)] = a
                continue
            if w == 'fonttbl':
                dest, dest_depth = 'fonttbl', depth
            elif w == 'colortbl':
                dest, dest_depth = 'colortbl', depth
            elif w in ('stylesheet', 'info', 'header', 'footer', 'pict', 'object'):
                dest = 'skip'
            elif w == 'footnote':
                # the footnote mark was written just before as text, or as {\up #}: drop it from the topic text
                foot_mark = None
                if items and items[-1][0] == 't' and items[-1][1][-1:] in '#$K+!':
                    foot_mark = items[-1][1][-1]
                    t = items[-1][1][:-1]
                    if t:
                        items[-1] = ('t', t, items[-1][2])
                    else:
                        items.pop()
                dest, dest_depth = 'footnote', depth
            elif dest == 'footnote':
                if w in ('par', 'line'):
                    foot.append(' ')
                continue
            elif w == 'par':
                end_para()
            elif w == 'page':
                if items:
                    end_para()
                topics.append(Topic())
            elif w == 'line':
                flush_hidden()
                items.append(('line',))
            elif w == 'tab':
                flush_hidden()
                items.append(('tab',))
            elif w == 'pard':
                pp = ParaProps()
            elif w == 'plain':
                cp = CharProps()
            elif w in ('b', 'i', 'ul', 'uldb', 'strike', 'v'):
                if cp.v and w == 'v' and a == 0:
                    pass
                setattr(cp, w, a != 0)
                if w == 'v' and a == 0:
                    pass
            elif w == 'ulnone':
                cp.ul = cp.uldb = False
            elif w == 'up':
                cp.up = (a != 0)
            elif w == 'f':
                cp.f = a
            elif w == 'fs':
                cp.fs = a
            elif w == 'cf':
                cp.cf = a
            elif w in ('li', 'ri', 'fi', 'sb', 'sa', 'sl'):
                setattr(pp, w, a)
            elif w == 'qc':
                pp.align = 0x800
            elif w == 'qr':
                pp.align = 0x400
            elif w == 'ql':
                pp.align = 0
            elif w == 'keepn':
                pp.keepn = True
            elif w == 'tqr':
                pp.tabkind = 1
            elif w == 'tqc':
                pp.tabkind = 2
            elif w == 'tx':
                pp.tabs.append((a, pp.tabkind))
                pp.tabkind = 0
            continue
        if kind == 'sym':
            s = tok[1]
            ch = {'~': '\xa0', '-': '', '_': '-', '{': '{', '}': '}', '\\': '\\'}.get(s)
            if s == '*':
                dest = 'skip' if dest is None else dest
                continue
            if ch is None:
                continue
            tok = ('text', ch)
        if kind in ('text', 'sym'):
            text = tok[1]
            if dest == 'fonttbl':
                ft_name += text
            elif dest == 'colortbl':
                for _ in range(text.count(';')):
                    colors.append(tuple(col))
                    col = [0, 0, 0]
            elif dest == 'footnote':
                foot.append(text)
            elif dest is None and text:
                emit(text)
    if items:
        end_para()
    return [t for t in topics if t.paras or t.ctx or t.title]

# ------------------------------------------------------------------------------------------------ compiling

class Compiler:
    def __init__(self):
        self.fonts = {}           # rtf font number -> (face, family)
        self.colors = []
        self.desc = []            # font descriptors: (attr, halfpoints, family, faceidx, rgb)
        self.desc_ix = {}
        self.faces = []

    def font_index(self, key):
        f, fs, b, it, cf = key
        face, fam = self.fonts.get(f, ('Helv', 3))
        if face not in self.faces:
            self.faces.append(face)
        rgb = self.colors[cf] if 0 <= cf < len(self.colors) else (0, 0, 0)
        d = ((1 if b else 0) | (2 if it else 0), fs, fam, self.faces.index(face), rgb)
        if d not in self.desc_ix:
            self.desc_ix[d] = len(self.desc)
            self.desc.append(d)
        return self.desc_ix[d]

    def para_record(self, pp, items):
        """One TOPICLINK of type 0x20: (LinkData1, LinkData2, TopicLength)."""
        bits = 0
        vals = b''
        if pp.sb:
            bits |= 0x02; vals += c_short(pp.sb // 10)
        if pp.sa:
            bits |= 0x04; vals += c_short(pp.sa // 10)
        if pp.sl:
            bits |= 0x08; vals += c_short(int(pp.sl / 10))
        if pp.li:
            bits |= 0x10; vals += c_short(pp.li // 10)
        if pp.ri:
            bits |= 0x20; vals += c_short(pp.ri // 10)
        if pp.fi:
            bits |= 0x40; vals += c_short(pp.fi // 10)
        if pp.tabs:
            bits |= 0x200
            vals += c_short(len(pp.tabs))
            for pos, k in pp.tabs:
                p = (pos // 10) & 0x3fff
                vals += c_ushort(p | 0x4000) + c_ushort(k) if k else c_ushort(p)
        bits |= pp.align
        fmt = bytes([0x00, 0x80, 0x00, 0x00]) + struct.pack('<H', bits) + vals
        strings, cur, cur_font = [], '', None
        for it in items:
            if it[0] == 't':
                fi = self.font_index(it[2])
                if fi != cur_font:
                    strings.append(cur); cur = ''
                    fmt += bytes([0x80]) + struct.pack('<H', fi)
                    cur_font = fi
                cur += it[1]
            elif it[0] == 'line':
                strings.append(cur); cur = ''; fmt += b'\x81'
            elif it[0] == 'tab':
                strings.append(cur); cur = ''; fmt += b'\x83'
            elif it[0] == 'hot':
                strings.append(cur); cur = ''
                h = ctx_hash(it[2])
                self.refs.add(it[2].lower())
                fmt += bytes([0xE2 if it[1] == 'popup' else 0xE3]) + struct.pack('<l', h)
            elif it[0] == 'endhot':
                strings.append(cur); cur = ''; fmt += b'\x89'
        if cur_font is None:                  # an empty paragraph still needs a font
            fmt += bytes([0x80]) + struct.pack('<H', self.font_index((0, 20, False, False, 0)))
            strings.append('')
        strings.append(cur); fmt += b'\x82'
        strings.append(''); fmt += b'\xff'
        text = b''.join(s.encode('cp1252', 'replace') + b'\0' for s in strings)
        tlen = len(text)
        rest = c_ushort(tlen) + fmt
        size_field = c_long(len(rest) - len(c_ushort(tlen)))
        return size_field + rest, text, tlen

    def compile(self, hpj_path, out_path):
        base = os.path.dirname(os.path.abspath(hpj_path))
        sec, opts, files, config = None, {}, [], []
        for line in open(hpj_path, encoding='cp1252'):
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            if sec != 'CONFIG':
                line = line.split(';', 1)[0].strip()
            if not line:
                continue
            if line.startswith('['):
                sec = line.strip('[]').upper()
                continue
            if sec == 'OPTIONS' and '=' in line:
                k, v = line.split('=', 1)
                opts[k.strip().upper()] = v.strip()
            elif sec == 'FILES':
                files.append(line)
            elif sec == 'CONFIG':
                config.append(line)
        topics = []
        for fn in files:
            src = open(os.path.join(base, fn), encoding='cp1252').read()
            topics += parse_rtf(src, self.fonts, self.colors)
        self.refs = set()
        # every topic: header record + paragraph records
        recs = []                 # (topic_index or None, type, L1 (may be patched), L2, tlen, para_keepn)
        for ti, t in enumerate(topics):
            recs.append([ti, 2, None, (t.title or '').encode('cp1252', 'replace') +
                         b''.join(b'\0' + m.encode('cp1252') for m in t.macros), 0, False])
            for pp, items in t.paras:
                l1, l2, tl = self.para_record(pp, items)
                recs.append([ti, 0x20, l1, l2, tl, pp.keepn])
        recs.append([None, 2, None, b'', 0, False])       # the closing empty topic header, as HC31 writes it
        HDR_L1 = 28

        def link_len(r):
            return 21 + (HDR_L1 if r[1] == 2 else len(r[2])) + len(r[3])

        # lay out: links never cross a topic block; a block holds at most LIMIT decompressed bytes and 4084 compressed
        LIMIT = 12000
        layout = []               # per rec: (block, offset in block)
        blocks = [[]]
        used = 0
        for ri, r in enumerate(recs):
            ln = link_len(r)
            if used and used + ln > LIMIT:
                blocks.append([]); used = 0
            layout.append((len(blocks) - 1, used))
            blocks[-1].append(ri)
            used += ln

        def build(layout):
            pos = [12 + b * 0x4000 + o for b, o in layout]
            # TOPICOFFSET of each record: block*0x8000 + characters before it in its block
            toff, cnt, lastb = [], 0, -1
            for ri, r in enumerate(recs):
                b = layout[ri][0]
                if b != lastb:
                    cnt, lastb = 0, b
                toff.append(b * 0x8000 + cnt)
                cnt += r[4]
            heads = [ri for ri, r in enumerate(recs) if r[1] == 2]
            topic_off = {recs[ri][0]: toff[ri] for ri in heads if recs[ri][0] is not None}
            # browse sequences
            bck, fwd = {}, {}
            seqs = {}
            for ti, t in enumerate(topics):
                if t.browse:
                    name, _, key = t.browse.rpartition(':') if ':' in t.browse else ('', '', t.browse)
                    seqs.setdefault(name, []).append((key, ti))
            for name, lst in seqs.items():
                lst = [ti for key, ti in sorted(lst, key=lambda x: (x[0] == 'auto', x[0]))] if any(
                    k != 'auto' for k, _ in lst) else [ti for _, ti in lst]
                for a, b in zip(lst, lst[1:]):
                    fwd[a], bck[b] = topic_off[b], topic_off[a]
            data = []
            for ri, r in enumerate(recs):
                prev = pos[ri - 1] if ri else -1
                nxt = pos[ri + 1] if ri + 1 < len(recs) else -1
                if r[1] == 2:
                    if r[0] is None:
                        l1 = struct.pack('<lllllll', 0, -1, -1, len(topics), -1, -1, -1)
                    else:
                        hi = heads.index(ri)
                        nh = heads[hi + 1]
                        first = ri + 1
                        ns = [k for k in range(first, nh) if recs[k][5]]
                        nonscroll = pos[first] if ns and ns[0] == first else -1
                        scroll_i = first
                        while scroll_i < nh and recs[scroll_i][5] and nonscroll != -1:
                            scroll_i += 1
                        scroll = pos[scroll_i] if scroll_i < nh else pos[nh]
                        l1 = struct.pack('<lllllll', pos[nh] - pos[ri], bck.get(r[0], -1), fwd.get(r[0], -1), r[0],
                                         nonscroll, scroll, pos[nh])
                    nxt = nxt if r[0] is not None else -1
                else:
                    l1 = r[2]
                link = struct.pack('<lllllB', 21 + len(l1) + len(r[3]), len(r[3]), prev, nxt, 21 + len(l1), r[1]) + l1 + r[3]
                data.append(link)
            out = bytearray()
            for bi, blk in enumerate(blocks):
                raw = b''.join(data[ri] for ri in blk)
                last_prev = pos[blocks[bi - 1][-1]] if bi else -1
                lth = [ri for ri in heads if layout[ri][0] < bi or (layout[ri][0] == bi and ri <= blk[0])]
                last_head = pos[lth[-1]] if bi and lth else 0
                comp = lz77_compress(raw)
                if len(comp) > 4096 - 12:
                    return None, None
                blockbytes = struct.pack('<lll', last_prev, pos[blk[0]], last_head) + comp
                if bi + 1 < len(blocks):
                    blockbytes += bytes(4096 - len(blockbytes))
                out += blockbytes
            return bytes(out), topic_off

        while True:
            topic_bytes, topic_off = build(layout)
            if topic_bytes is not None:
                break
            LIMIT -= 1500
            if LIMIT < 2000:
                raise SystemExit('hlpc: a paragraph is too large for one topic block')
            layout, blocks, used = [], [[]], 0
            for ri, r in enumerate(recs):
                ln = link_len(r)
                if used and used + ln > LIMIT:
                    blocks.append([]); used = 0
                layout.append((len(blocks) - 1, used))
                blocks[-1].append(ri)
                used += ln

        internal = {'|TOPIC': topic_bytes}
        # |CONTEXT: hash -> TOPICOFFSET, sorted by signed hash
        ctx, seen = [], {}
        for ti, t in enumerate(topics):
            for c in t.ctx:
                if not re.fullmatch(r'[A-Za-z0-9_.]+', c):
                    raise SystemExit('hlpc: context string %r has characters WinHelp 3.1 does not allow' % c)
                h = ctx_hash(c)
                if h in seen and seen[h] != c.lower():
                    raise SystemExit('hlpc: context strings %r and %r have the same hash' % (seen[h], c))
                if h in seen:
                    raise SystemExit('hlpc: context string %r is defined twice' % c)
                seen[h] = c.lower()
                ctx.append((h, topic_off[ti]))
        ctx.sort()
        internal['|CONTEXT'], _ = btree('L4', [(struct.pack('<l', h), struct.pack('<ll', h, o)) for h, o in ctx])
        missing = sorted(r for r in self.refs if ctx_hash(r) not in seen)
        if missing:
            raise SystemExit('hlpc: jumps to undefined context strings: %s' % ', '.join(missing))
        # |TTLBTREE: TOPICOFFSET -> title
        ttl = [(topic_off[ti], (t.title or '').encode('cp1252', 'replace')) for ti, t in enumerate(topics)]
        internal['|TTLBTREE'], _ = btree('Lz', [(struct.pack('<l', o), struct.pack('<l', o) + s + b'\0') for o, s in ttl])
        # keywords
        kw = {}
        for ti, t in enumerate(topics):
            for k in t.keywords:
                kw.setdefault(k, [])
                if topic_off[ti] not in kw[k]:
                    kw[k].append(topic_off[ti])
        merged = {}
        for k in kw:                                          # keywords are case-insensitive: merge spellings
            merged.setdefault(k.lower(), [k, []])
            merged[k.lower()][1] += [o for o in kw[k] if o not in merged[k.lower()][1]]
        keys = sorted(merged.values(), key=lambda x: x[0].lower())
        kwdata, leaves = bytearray(), []
        for k, offs in keys:
            kb = k.encode('cp1252', 'replace') + b'\0'
            leaves.append((kb, kb + struct.pack('<hl', len(offs), len(kwdata))))
            kwdata += b''.join(struct.pack('<l', o) for o in sorted(offs))
        if keys:
            tree, firsts = btree('i24', leaves)
            internal['|KWBTREE'] = tree
            internal['|KWDATA'] = bytes(kwdata)
            # |KWMAP: for each leaf page, the number of its first keyword
            npages = struct.unpack_from('<h', tree, 32)[0]
            nleaf = npages - 1 if struct.unpack_from('<h', tree, 34)[0] == 2 else npages
            m, k = b'', 0
            for p in range(nleaf):
                m += struct.pack('<lH', k, p)
                k += struct.unpack_from('<h', tree, 38 + p * 2048 + 2)[0]
            internal['|KWMAP'] = struct.pack('<h', nleaf) + m
        internal['|CTXOMAP'] = struct.pack('<h', 0)
        # |FONT
        faces = b''.join(f.encode('cp1252')[:19].ljust(20, b'\0') for f in self.faces)
        descs = b''.join(struct.pack('<BBBH', a, hp, fam, fi) + bytes(rgb) + bytes(3)
                         for a, hp, fam, fi, rgb in self.desc)
        internal['|FONT'] = struct.pack('<HHHH', len(self.faces), len(self.desc), 8, 8 + len(faces)) + faces + descs
        # |SYSTEM
        sysrec = b''

        def rec(t, data):
            return struct.pack('<HH', t, len(data)) + data
        sysrec += rec(1, opts.get('TITLE', 'Help').encode('cp1252') + b'\0')
        sysrec += rec(2, opts.get('COPYRIGHT', '').encode('cp1252') + b'\0')
        cti = 0
        if 'CONTENTS' in opts:
            want = ctx_hash(opts['CONTENTS'])
            cti = [ti for ti, t in enumerate(topics) if any(ctx_hash(c) == want for c in t.ctx)][0]
        sysrec += rec(3, struct.pack('<l', topic_off[cti]))
        for m in config:
            sysrec += rec(4, m.encode('cp1252') + b'\0')
        gendate = max(0, int(os.environ.get('SOURCE_DATE_EPOCH') or time.time()) - 315532800)
        internal['|SYSTEM'] = struct.pack('<HHHlH', 0x036C, 21, 1, gendate, 4) + sysrec
        write_hlp(out_path, internal)
        return topics

# ------------------------------------------------------------------------------------------------ dump (self-check)

def read_internal(d):
    ds = struct.unpack_from('<l', d, 4)[0]
    hdr = ds + 9
    ps = struct.unpack_from('<H', d, hdr + 4)[0]
    root, _, _, nlev = struct.unpack_from('<hhhh', d, hdr + 26)
    pages = hdr + 38
    p = root
    for _ in range(nlev - 1):
        p = struct.unpack_from('<h', d, pages + p * ps + 4)[0]
    res = {}
    while p != -1:
        o = pages + p * ps
        _, n, _, nxt = struct.unpack_from('<Hhhh', d, o)
        o += 8
        for _ in range(n):
            e = d.index(b'\0', o)
            name = d[o:e].decode('latin1')
            o = e + 1
            off = struct.unpack_from('<l', d, o)[0]
            o += 4
            _, used, _ = struct.unpack_from('<llB', d, off)
            res[name] = d[off + 9:off + 9 + used]
        p = nxt
    return res


def dump(path):
    files = read_internal(open(path, 'rb').read())
    print('internal files:', ', '.join(sorted(files)))
    t = files['|TOPIC']
    blocks = [lz77_expand(t[i + 12:i + 4096]) for i in range(0, len(t), 4096)]
    pos, n = 12, 0
    while pos not in (0, -1) and n < 100000:
        b, o = (pos - 12) // 0x4000, (pos - 12) % 0x4000
        buf = blocks[b]
        bs, dl2, prev, nxt, dl1, rt = struct.unpack_from('<lllllB', buf, o)
        l1, l2 = buf[o + 21:o + dl1], buf[o + dl1:o + bs]
        if rt == 2:
            print('\n=== %s' % l2.split(b'\0')[0].decode('cp1252'))
        elif rt == 0x20:
            strs = l2.split(b'\0')
            # walk the format commands just enough to show text, jumps and breaks
            i = 2 + (1 if l1[2] % 2 == 0 else 2) + 4
            bits = struct.unpack_from('<H', l1, i)[0]
            i += 2
            for flag in (0x1, 0x2, 0x4, 0x8, 0x10, 0x20, 0x40):
                if bits & flag:
                    i += 4 if flag == 1 else (1 if l1[i] % 2 == 0 else 2)
            if bits & 0x200:
                nt = (l1[i] // 2 - 64) if l1[i] % 2 == 0 else None
                i += 1
                for _ in range(nt):
                    v = l1[i] // 2 if l1[i] % 2 == 0 else (l1[i] >> 1) + 128 * l1[i + 1]
                    i += 1 if l1[i] % 2 == 0 else 2
                    if v & 0x4000:
                        i += 1
            line, si = '', 0
            while i < len(l1):
                line += strs[si].decode('cp1252') if si < len(strs) else ''
                si += 1
                c = l1[i]
                if c == 0xff:
                    break
                if c == 0x80:
                    i += 3
                elif c in (0x81, 0x82):
                    line += '\n' if c == 0x81 else ''
                    i += 1
                elif c == 0x83:
                    line += '\t'
                    i += 1
                elif c in (0xE2, 0xE3):
                    line += '[' + ('popup' if c == 0xE2 else 'jump') + ':'
                    i += 5
                elif c == 0x89:
                    line += ']'
                    i += 1
                else:
                    line += '<%02x>' % c
                    break
            print(line)
        pos, n = nxt, n + 1


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == '--dump':
        dump(a[1])
        sys.exit(0)
    out = a[a.index('-o') + 1] if '-o' in a else os.path.splitext(a[0])[0] + '.hlp'
    tops = Compiler().compile(a[0], out)
    print('%s: %d topics, %d bytes' % (out, len(tops), os.path.getsize(out)))
