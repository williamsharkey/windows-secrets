"""Standard MIDI Files: a small reader and writer (format 0 and 1, PPQ timing), no dependencies.

Events are kept as (tick, order, bytes) so a split or a rewrite keeps the file's own timing exactly.
"""
import struct


def _prio(e):
    if e[0] == 0xFF:
        return 0
    st = e[0] & 0xF0
    if st == 0x80 or (st == 0x90 and len(e) > 2 and e[2] == 0):
        return 1
    return 3 if st == 0x90 else 2


class Smf:
    def __init__(self, division=480):
        self.division = division
        self.tracks = []          # each a list of [tick, bytes]; bytes is the full event (status first), meta as FF type len data

    # ---- reading
    @classmethod
    def read(cls, path):
        with open(path, 'rb') as f:
            d = f.read()
        if d[:4] != b'MThd':
            raise ValueError(f'{path}: not a MIDI file')
        hl = struct.unpack('>I', d[4:8])[0]
        fmt, ntrk, div = struct.unpack('>HHH', d[8:14])
        if div & 0x8000:
            raise ValueError(f'{path}: SMPTE timing is not supported')
        m = cls(div)
        p = 8 + hl
        for _ in range(ntrk):
            if d[p:p + 4] != b'MTrk':
                raise ValueError(f'{path}: bad track chunk')
            ln = struct.unpack('>I', d[p + 4:p + 8])[0]
            end = p + 8 + ln
            p += 8
            tick, run, evs = 0, 0, []

            def vlq():
                nonlocal p
                v = 0
                while True:
                    c = d[p]; p += 1
                    v = (v << 7) | (c & 0x7F)
                    if not c & 0x80:
                        return v
            while p < end:
                tick += vlq()
                st = d[p]
                if st & 0x80:
                    p += 1
                else:
                    st = run
                if st == 0xFF:
                    ty = d[p]; p += 1
                    q = p; ln2 = vlq()
                    evs.append([tick, bytes([0xFF, ty]) + d[q:p] + d[p:p + ln2]])
                    p += ln2
                elif st in (0xF0, 0xF7):
                    q = p; ln2 = vlq()
                    evs.append([tick, bytes([st]) + d[q:p] + d[p:p + ln2]])
                    p += ln2
                else:
                    run = st
                    n = 1 if st & 0xF0 in (0xC0, 0xD0) else 2
                    evs.append([tick, bytes([st]) + d[p:p + n]])
                    p += n
            m.tracks.append(evs)
            p = end
        return m

    # ---- writing (format 1, or 0 with one track)
    def write(self, path):
        def vlq(v):
            out = [v & 0x7F]
            v >>= 7
            while v:
                out.insert(0, 0x80 | (v & 0x7F)); v >>= 7
            return bytes(out)
        chunks = []
        for evs in self.tracks:
            evs = sorted(evs, key=lambda e: e[0])   # stable: same-tick order kept
            body, last = bytearray(), 0
            for tick, ev in evs:
                if ev[:2] == b'\xff\x2f':
                    continue
                body += vlq(tick - last) + ev; last = tick
            end_tick = max([e[0] for e in evs] + [0])
            body += vlq(end_tick - last) + b'\xff\x2f\x00'
            chunks.append(b'MTrk' + struct.pack('>I', len(body)) + bytes(body))
        fmt = 0 if len(self.tracks) == 1 else 1
        with open(path, 'wb') as f:
            f.write(b'MThd' + struct.pack('>IHHH', 6, fmt, len(self.tracks), self.division) + b''.join(chunks))

    def to_bytes_for(self, path):
        self.write(path)
        with open(path, 'rb') as f:
            return f.read()

    # ---- queries
    def tempo_events(self):
        return [[t, e] for evs in self.tracks for t, e in evs if e[:2] == b'\xff\x51']

    def channels(self):
        s = set()
        for evs in self.tracks:
            for _, e in evs:
                if e[0] < 0xF0:
                    s.add(e[0] & 0x0F)
        return sorted(s)

    def seconds(self, tick):
        """tick -> seconds through the tempo map (120 bpm before the first tempo event)"""
        tm = sorted((t, struct.unpack('>I', b'\x00' + e[3:6])[0]) for t, e in self.tempo_events())
        sec, last, uspq = 0.0, 0, 500000
        for t, u in tm:
            if t >= tick:
                break
            sec += (t - last) * uspq / 1e6 / self.division; last, uspq = t, u
        return sec + (tick - last) * uspq / 1e6 / self.division

    def last_tick(self):
        return max([t for evs in self.tracks for t, _ in evs] + [0])

    def first_tempo_bpm(self):
        tm = sorted(self.tempo_events(), key=lambda x: x[0])
        if not tm:
            return 120.0
        return 60e6 / struct.unpack('>I', b'\x00' + tm[0][1][3:6])[0]

    def extract(self, sel, transpose=0, vel_scale=1.0):
        """a format-0 file with the tempo map and the events selected by sel(track_index, channel), moved to
        channel 1, notes transposed, velocities scaled (note-ons stay >= 1)"""
        out = Smf(self.division)
        evs = []
        for ti, tr in enumerate(self.tracks):
            for t, e in tr:
                if e[:2] == b'\xff\x51':
                    evs.append([t, e]); continue
                if e[0] >= 0xF0 or not sel(ti, e[0] & 0x0F):
                    continue
                st = e[0] & 0xF0
                b = bytearray(e); b[0] = st
                if st in (0x80, 0x90, 0xA0):
                    n = b[1] + transpose
                    if n < 0 or n > 127:
                        continue
                    b[1] = n
                    if st == 0x90 and b[2] > 0 and vel_scale != 1.0:
                        b[2] = max(1, min(127, int(round(b[2] * vel_scale))))
                evs.append([t, bytes(b)])
        evs.sort(key=lambda x: (x[0], _prio(x[1])))   # at one tick: tempo, then note-offs, then the rest, then note-ons
        out.tracks = [evs]
        return out

    def note_count(self):
        return sum(1 for tr in self.tracks for _, e in tr if e[0] & 0xF0 == 0x90 and len(e) > 2 and e[2] > 0)
