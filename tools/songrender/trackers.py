#!/usr/bin/env python3
"""trackers: FastTracker 2 (.xm) and Impulse Tracker (.it) modules -> Standard MIDI Files, for re-voicing on
SNDWAVE1993 (the notes and timing only; the module's samples are never used).

    trackers.py MODULE.xm|.it OUT.mid [--by instrument|channel] [--info]

- Order list followed once, with pattern breaks (D/C) and position jumps (B); a jump backwards ends the song.
- Speed and tempo (F in XM; A and T in IT) give each row's length: 2.5 / BPM seconds a tick.
- Note delay (EDx / SDx) and note cut (ECx / SCx), key off (XM 97; IT 255, 254 cut, 253 fade).
- Volume: the volume column (and the instrument's default) sets the note's velocity.
- Every (instrument or channel) becomes its own MIDI track (track 1 is the first instrument), with a track name
  such as "ins 3 Lead", and a MIDI channel in order of first use (10 skipped; past 15 they repeat, so pick by trN).
"""
import argparse, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smf import Smf   # noqa: E402


class Row:
    __slots__ = ('note', 'ins', 'vol', 'fx', 'param')

    def __init__(self, note=0, ins=0, vol=-1, fx=0, param=0):
        self.note, self.ins, self.vol, self.fx, self.param = note, ins, vol, fx, param


class Module:
    def __init__(self):
        self.title = ''; self.channels = 0; self.orders = []; self.patterns = []
        self.speed = 6; self.bpm = 125; self.ins_names = {}; self.ins_vol = {}; self.ins_shift = {}
        self.kind = ''


def read_xm(path):
    d = open(path, 'rb').read()
    if not d.startswith(b'Extended Module: '):
        raise ValueError('not an XM')
    m = Module(); m.kind = 'xm'
    m.title = d[17:37].rstrip(b'\0 ').decode('latin-1')
    hs = struct.unpack('<I', d[60:64])[0]
    songlen, restart, nch, npat, nins, flags, speed, bpm = struct.unpack('<HHHHHHHH', d[64:80])
    m.channels, m.speed, m.bpm = nch, speed or 6, bpm or 125
    m.orders = list(d[80:80 + songlen])
    p = 60 + hs
    for _ in range(npat):
        phl = struct.unpack('<I', d[p:p + 4])[0]
        rows = struct.unpack('<H', d[p + 5:p + 7])[0]
        psize = struct.unpack('<H', d[p + 7:p + 9])[0]
        q, end = p + phl, p + phl + psize
        pat = []
        for r in range(rows):
            row = []
            for c in range(nch):
                if psize == 0:
                    row.append(Row()); continue
                b = d[q]
                if b & 0x80:
                    q += 1
                    note = d[q] if b & 1 else 0; q += 1 if b & 1 else 0
                    ins = d[q] if b & 2 else 0; q += 1 if b & 2 else 0
                    vol = d[q] if b & 4 else 0; q += 1 if b & 4 else 0
                    fx = d[q] if b & 8 else 0; q += 1 if b & 8 else 0
                    prm = d[q] if b & 16 else 0; q += 1 if b & 16 else 0
                else:
                    note, ins, vol, fx, prm = d[q:q + 5]; q += 5
                v = vol - 0x10 if 0x10 <= vol <= 0x50 else -1
                row.append(Row(note, ins, v, fx, prm))
            pat.append(row)
        m.patterns.append(pat)
        p = end
    for i in range(1, nins + 1):   # instrument names and their first sample's volume
        ihs = struct.unpack('<I', d[p:p + 4])[0]
        m.ins_names[i] = d[p + 4:p + 26].rstrip(b'\0 ').decode('latin-1', 'replace')
        ns = struct.unpack('<H', d[p + 27:p + 29])[0]
        if ns:
            shs = struct.unpack('<I', d[p + 29:p + 33])[0]
            q = p + ihs
            tot = 0
            for s in range(ns):
                ln = struct.unpack('<I', d[q:q + 4])[0]
                if s == 0:
                    m.ins_vol[i] = d[q + 12]
                    fine = struct.unpack('<b', d[q + 13:q + 14])[0]
                    rel = struct.unpack('<b', d[q + 16:q + 17])[0]
                    m.ins_shift[i] = rel + fine / 128.0   # semitones the sample is played off the written note
                tot += ln
                q += shs
            p = q + tot
        else:
            p += ihs
    return m


def read_it(path):
    d = open(path, 'rb').read()
    if d[:4] != b'IMPM':
        raise ValueError('not an IT')
    m = Module(); m.kind = 'it'
    m.title = d[4:30].rstrip(b'\0 ').decode('latin-1')
    ordnum, insnum, smpnum, patnum, cwt, cmwt, flags, special = struct.unpack('<HHHHHHHH', d[32:48])
    gv, mv, speed, tempo = d[48], d[49], d[50], d[51]
    m.speed, m.bpm = speed or 6, tempo or 125
    p = 0xC0
    m.orders = [o for o in d[p:p + ordnum] if o != 254]
    if 255 in m.orders:
        m.orders = m.orders[:m.orders.index(255)]
    p += ordnum
    insp = struct.unpack('<%dI' % insnum, d[p:p + 4 * insnum]); p += 4 * insnum
    smpp = struct.unpack('<%dI' % smpnum, d[p:p + 4 * smpnum]); p += 4 * smpnum
    patp = struct.unpack('<%dI' % patnum, d[p:p + 4 * patnum])
    use_ins = bool(flags & 4)
    names = insp if use_ins else smpp
    for i, o in enumerate(names, 1):
        if o:
            off = 0x20 if use_ins else 0x14
            m.ins_names[i] = d[o + off:o + off + 26].rstrip(b'\0 ').decode('latin-1', 'replace')
    import math
    smp_shift = {}
    for i, o in enumerate(smpp, 1):
        if o:
            m.ins_vol[i] = d[o + 0x13]   # the sample's default volume (0-64)
            c5 = struct.unpack('<I', d[o + 0x3C:o + 0x40])[0]
            smp_shift[i] = 12 * math.log2(c5 / 8363.0) if c5 else 0.0
    if use_ins:   # an instrument plays the sample its note table names for C-5
        vol = dict(m.ins_vol); m.ins_vol = {}
        for i, o in enumerate(insp, 1):
            if o:
                smp = d[o + 0x40 + 2 * 60 + 1]
                m.ins_shift[i] = smp_shift.get(smp, 0.0) + (d[o + 0x40 + 2 * 60] - 60)
                m.ins_vol[i] = vol.get(smp, 64)
    else:
        m.ins_shift = smp_shift
    nch = 0
    for o in patp:
        if not o:
            m.patterns.append([[Row() for _ in range(64)] for _ in range(64)]); continue
        ln, rows = struct.unpack('<HH', d[o:o + 4])
        q, end = o + 8, o + 8 + ln
        last = {}
        pat = [[Row() for _ in range(64)] for _ in range(rows)]
        r = 0
        while r < rows and q < end:
            cv = d[q]; q += 1
            if cv == 0:
                r += 1; continue
            ch = (cv - 1) & 63
            nch = max(nch, ch + 1)
            if cv & 128:
                last.setdefault(ch, {})['mask'] = d[q]; q += 1
            L = last.setdefault(ch, {'mask': 0})
            mask = L.get('mask', 0)
            row = pat[r][ch]
            if mask & 1:
                L['note'] = d[q]; q += 1
            if mask & 2:
                L['ins'] = d[q]; q += 1
            if mask & 4:
                L['vol'] = d[q]; q += 1
            if mask & 8:
                L['fx'], L['param'] = d[q], d[q + 1]; q += 2
            if mask & (1 | 16):
                n = L.get('note', 0)
                row.note = n + 1 if n < 120 else {255: 97, 254: 98, 253: 97}.get(n, 0)   # 1 = C-0 (IT C-5 is note 61 here)
            if mask & (2 | 32):
                row.ins = L.get('ins', 0)
            if mask & (4 | 64):
                v = L.get('vol', 255)
                row.vol = v if v <= 64 else -1
            if mask & (8 | 128):
                row.fx, row.param = L.get('fx', 0), L.get('param', 0)
        m.patterns.append(pat)
    m.channels = nch
    return m


def to_events(m):
    """-> [(seconds, channel, instrument, note, velocity, length seconds)] and the song length"""
    out = []
    t = 0.0
    speed, bpm = m.speed, m.bpm
    playing = {}   # channel -> [start, ins, note, vel]
    last_ins = {}
    oi, row0 = 0, 0
    visited = set()

    def end_note(ch, at):
        if ch in playing:
            s, ins, n, v = playing.pop(ch)
            if at > s:
                out.append((s, ch, ins, n, v, at - s))
    while 0 <= oi < len(m.orders):
        pi = m.orders[oi]
        if pi >= len(m.patterns):
            oi += 1; continue
        if (oi, row0) in visited:
            break
        visited.add((oi, row0))
        pat = m.patterns[pi]
        nxt_o, nxt_r = oi + 1, 0
        r = row0
        jumped = False
        while r < len(pat):
            row = pat[r]
            # tempo effects first (they change this row's length)
            for c in row[:m.channels]:
                if m.kind == 'xm' and c.fx == 0x0F and c.param:
                    if c.param < 32:
                        speed = c.param
                    else:
                        bpm = c.param
                if m.kind == 'it' and c.fx == 1 and c.param:
                    speed = c.param
                if m.kind == 'it' and c.fx == 20 and c.param >= 32:
                    bpm = c.param
            tick = 2.5 / bpm
            rowlen = speed * tick
            for ch, c in enumerate(row[:m.channels]):
                delay, cut = 0.0, None
                if (m.kind == 'xm' and c.fx == 0x0E) or (m.kind == 'it' and c.fx == 19):
                    hi, lo = c.param >> 4, c.param & 15
                    if hi == 0xD:
                        delay = min(lo, speed - 1) * tick
                    if hi == 0xC:
                        cut = lo * tick
                at = t + delay
                if c.note == 97 or c.note == 98:
                    end_note(ch, at)
                elif 1 <= c.note <= 96 or (m.kind == 'it' and 1 <= c.note <= 120):
                    end_note(ch, at)
                    ins = c.ins or last_ins.get(ch, 0)
                    last_ins[ch] = ins
                    vol = c.vol if c.vol >= 0 else m.ins_vol.get(ins, 64)
                    vel = max(1, min(127, int(round(vol / 64 * 127))))
                    # module C-4 (XM note 49; IT C-5) -> MIDI 60 (the written note is the pitch meant: a sample's
                    # relative note / C5 speed exist to make it so)
                    n = c.note - 1 + 12 - (12 if m.kind == 'it' else 0)
                    playing[ch] = [at, ins, n, vel]
                elif c.vol == 0 and ch in playing:
                    end_note(ch, at)
                if cut is not None and ch in playing:
                    end_note(ch, t + cut)
            # flow control
            brk = None
            for c in row[:m.channels]:
                if (m.kind == 'xm' and c.fx == 0x0B) or (m.kind == 'it' and c.fx == 2):
                    nxt_o, nxt_r, brk = c.param, 0, True
                if (m.kind == 'xm' and c.fx == 0x0D) or (m.kind == 'it' and c.fx == 3):
                    rr = (c.param >> 4) * 10 + (c.param & 15) if m.kind == 'xm' else c.param
                    if not brk:
                        nxt_o = oi + 1
                    nxt_r, brk = rr, True
            t += rowlen
            if brk:
                jumped = True
                break
            r += 1
        if jumped and nxt_o <= oi and not (nxt_o == oi and nxt_r > row0):
            break   # a loop back: the song is over
        oi, row0 = nxt_o, nxt_r
    for ch in list(playing):
        end_note(ch, t)
    return sorted(out), t


def key_check(events):
    """instruments whose pitch classes fit the rest of the module better transposed: {ins: (shift, gain)}"""
    import math
    h = {}
    for st, c, ins, n, v, du in events:
        h.setdefault(ins, [0.0] * 12)[n % 12] += min(du, 2.0)
    mel = {i: x for i, x in h.items() if sum(1 for y in x if y > 0) >= 4}
    out = {}
    for i, x in mel.items():
        ref = [sum(mel[j][k] for j in mel if j != i) for k in range(12)]
        if not any(ref):
            continue
        def corr(s):
            a = [x[(k - s) % 12] for k in range(12)]
            ma, mb = sum(a) / 12, sum(ref) / 12
            num = sum((p - ma) * (q - mb) for p, q in zip(a, ref))
            den = math.sqrt(sum((p - ma) ** 2 for p in a) * sum((q - mb) ** 2 for q in ref)) or 1
            return num / den
        best = max(range(-6, 6), key=corr)
        if best != 0 and corr(best) > corr(0) + 0.25:
            out[i] = (best, round(corr(0), 2), round(corr(best), 2))
    return out


def write_midi(m, events, path, by='instrument', length=None):
    keys = []
    for ev in events:
        k = ev[2] if by == 'instrument' else ev[1]
        if k not in keys:
            keys.append(k)
    chans = [c for c in range(16) if c != 9]
    cmap = {k: chans[i % len(chans)] for i, k in enumerate(keys)}   # past 15, channels repeat: pick those by track (trN)
    s = Smf(480)
    s.tracks.append([[0, b'\xff\x51\x03' + (500000).to_bytes(3, 'big')]])   # 120 bpm: 960 ticks a second
    tps = 960.0
    for k in keys:
        name = (f'ins {k} {m.ins_names.get(k, "")}' if by == 'instrument' else f'chan {k}').strip().encode('latin-1', 'replace')[:60]
        ch = cmap[k]
        evs = [[0, b'\xff\x03' + bytes([len(name)]) + name]]
        for st, c, ins, n, v, du in events:
            if (ins if by == 'instrument' else c) != k or not (0 <= n <= 127):
                continue
            a, b = int(round(st * tps)), max(int(round(st * tps)) + 1, int(round((st + du) * tps)))
            evs.append([a, bytes([0x90 | ch, n, v])])
            evs.append([b, bytes([0x80 | ch, n, 0])])
        evs.sort(key=lambda e: (e[0], 0 if e[1][0] == 0xFF else 1 if e[1][0] & 0xF0 == 0x80 else 2))
        s.tracks.append(evs)
    s.write(path)
    return cmap


FTM_CH = ['Pulse 1', 'Pulse 2', 'Triangle', 'Noise', 'DPCM', 'VRC6 Pulse 1', 'VRC6 Pulse 2', 'VRC6 Saw']


def read_ftm(path, track=0):
    """FamiTracker 0.4 (file 0x440) -> a Module with events precomputed (instrument = channel + 1)"""
    d = open(path, 'rb').read()
    if not d.startswith(b'FamiTracker Module'):
        raise ValueError('not a FamiTracker module')
    blocks, p = {}, 22
    while p + 24 <= len(d) and d[p:p + 3] != b'END':
        bid = d[p:p + 16].rstrip(b'\0').decode('latin-1')
        ver, size = struct.unpack('<II', d[p + 16:p + 24])
        blocks[bid] = (ver, d[p + 24:p + 24 + size])
        p += 24 + size
    pv, pd = blocks['PARAMS']
    ext = pd[0]
    nch, machine, eng, vib, h1, h2 = struct.unpack('<6i', pd[1:25])
    split = struct.unpack('<i', pd[25:29])[0] if len(pd) >= 29 else 32
    hv, hd = blocks['HEADER']
    ntracks = hd[0] + 1
    q, names = 1, []
    for _ in range(ntracks):
        e = hd.index(b'\0', q); names.append(hd[q:e].decode('latin-1')); q = e + 1
    ch_types, fxcols = [], []
    for c in range(nch):
        ch_types.append(hd[q]); q += 1
        fxcols.append(list(hd[q:q + ntracks])); q += ntracks
    fv, fd = blocks['FRAMES']
    q, tracks = 0, []
    for t in range(ntracks):
        nfr, speed, tempo, rows = struct.unpack('<4i', fd[q:q + 16]); q += 16
        frames = [list(fd[q + f * nch:q + (f + 1) * nch]) for f in range(nfr)]; q += nfr * nch
        tracks.append((speed, tempo, rows, frames))
    patv, patd = blocks['PATTERNS']
    pats = {}
    q = 0
    while q + 16 <= len(patd):
        tr, ch, pat, items = struct.unpack('<4i', patd[q:q + 16]); q += 16
        cells = {}
        for _ in range(items):
            row = struct.unpack('<i', patd[q:q + 4])[0]; q += 4
            note, octv, ins, vol = patd[q], patd[q + 1], patd[q + 2], patd[q + 3]; q += 4
            fx = []
            for _ in range(fxcols[ch][tr] + 1):
                fx.append((patd[q], patd[q + 1])); q += 2
            cells[row] = (note, octv, ins, vol, fx)
        pats[(tr, ch, pat)] = cells
    speed, tempo, rows, frames = tracks[track]
    m = Module(); m.kind = 'ftm'; m.title = names[track]; m.channels = nch
    m.ins_names = {c + 1: FTM_CH[c] if c < len(FTM_CH) else f'ch {c}' for c in range(nch)}
    m.speed, m.bpm = speed, tempo
    out, t, playing, lastvol = [], 0.0, {}, {}

    def end_note(c, at):
        if c in playing:
            s0, n, v = playing.pop(c)
            if at > s0:
                out.append((s0, c, c + 1, n, v, at - s0))
    fi, r0, seen = 0, 0, set()
    while fi < len(frames):
        if (fi, r0) in seen:
            break
        seen.add((fi, r0))
        nf, nr, jumped = fi + 1, 0, False
        r = r0
        while r < rows:
            cells = [pats.get((track, c, frames[fi][c]), {}).get(r) for c in range(nch)]
            for cell in cells:
                if cell:
                    for fx, prm in cell[4]:
                        if fx == 1 and prm:
                            if prm < split:
                                speed = prm
                            else:
                                tempo = prm
            rowlen = 2.5 * speed / tempo
            brk = False
            for c, cell in enumerate(cells):
                if not cell:
                    continue
                note, octv, ins, vol, fxs = cell
                if vol < 16:
                    lastvol[c] = vol
                delay = 0.0
                for fx, prm in fxs:
                    if fx == 14 and prm:
                        delay = min(prm, speed - 1) * 2.5 / tempo
                    if fx == 2:
                        nf, nr, brk = prm, 0, True
                    if fx == 3:
                        nf, nr, brk = (fi + 1 if not brk else nf), prm, True
                at = t + delay
                if note in (13, 14):
                    end_note(c, at)
                elif 1 <= note <= 12:
                    end_note(c, at)
                    v = lastvol.get(c, 15)
                    vel = max(1, int(round((v if vol >= 16 else vol) / 15 * 127)))
                    if c == 3:      # noise: its 16 pitches -> a snare (low) or a hat (high)
                        n = 42 if ((octv * 12 + note - 1) % 16) >= 8 else 38
                    elif c == 4:    # DPCM samples: kicks
                        n = 36
                    else:
                        n = 12 * (octv + 1) + note - 1
                    playing[c] = (at, n, vel)
                    if c in (3, 4):
                        end_note(c, at + min(rowlen, 0.12))
                elif vol == 0:
                    end_note(c, at)
            t += rowlen
            if brk:
                jumped = True
                break
            r += 1
        if jumped and nf <= fi:
            break
        fi, r0 = nf, nr
    for c in list(playing):
        end_note(c, t)
    m.events, m.length = sorted(out), t
    return m


def load(path):
    if path.lower().endswith('.ftm'):
        return read_ftm(path)
    return read_xm(path) if path.lower().endswith('.xm') else read_it(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('module')
    ap.add_argument('out', nargs='?')
    ap.add_argument('--by', choices=('instrument', 'channel'), default='instrument')
    ap.add_argument('--info', action='store_true')
    a = ap.parse_args()
    m = load(a.module)
    ev, length = (m.events, m.length) if m.kind == 'ftm' else to_events(m)
    if a.info or not a.out:
        from collections import Counter
        c = Counter(e[2] for e in ev)
        print(f'{os.path.basename(a.module)}: "{m.title}" {m.kind} {m.channels} ch, {len(m.orders)} orders, '
              f'speed {m.speed} bpm {m.bpm}, {len(ev)} notes, {length:.1f} s')
        for i, n in sorted(c.items()):
            ns = [e[3] for e in ev if e[2] == i]
            print(f'   ins {i:3d} {m.ins_names.get(i, ""):24s} {n:5d} notes  {min(ns)}-{max(ns)}')
        kc = key_check(ev)
        if kc:
            print('   key check, a hint only; chromatic or swing tunes fool it, so check intervals against the bass (shift, corr now, corr shifted):', kc)
    if a.out:
        cm = write_midi(m, ev, a.out, a.by)
        print('->', a.out, {k: v + 1 for k, v in cm.items()})


if __name__ == '__main__':
    main()
