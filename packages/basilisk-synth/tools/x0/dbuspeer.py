#!/usr/bin/env python3
"""X0 (RECORDING.md TR1): a minimal D-Bus peer for QEMU's dbus audio input, Unix (macOS/Linux) side.

    dbuspeer.py QMP_SOCKET [--tone HZ] [--clicks] [--seconds S] [--log FILE]

Connects to QEMU's p2p D-Bus display (QMP getfd + add_client), registers an AudioInListener over a second
socketpair, and answers QEMU's Read calls with a 1 kHz sine (or a click track) as s16 at the format Init gives.
Counts reads, bytes, underruns, and logs the Init format. Standard library only.
"""
import argparse, array, math, os, socket, struct, sys, threading, time, json

# ------------------------------------------------------------------ marshalling (little endian)
class W:
    def __init__(self): self.b = bytearray()
    def pad(self, n):
        while len(self.b) % n: self.b.append(0)
    def y(self, v): self.b.append(v & 255)
    def b_(self, v): self.pad(4); self.b += struct.pack('<I', 1 if v else 0)
    def u(self, v): self.pad(4); self.b += struct.pack('<I', v)
    def t(self, v): self.pad(8); self.b += struct.pack('<Q', v)
    def s(self, v):
        e = v.encode(); self.u(len(e)); self.b += e + b'\0'
    def o(self, v): self.s(v)
    def g(self, v):
        e = v.encode(); self.b.append(len(e)); self.b += e + b'\0'
    def ay(self, data):
        self.u(len(data)); self.b += data

class R:
    def __init__(self, b, p=0): self.b, self.p = b, p
    def pad(self, n):
        while self.p % n: self.p += 1
    def y(self): v = self.b[self.p]; self.p += 1; return v
    def u(self): self.pad(4); v = struct.unpack_from('<I', self.b, self.p)[0]; self.p += 4; return v
    def t(self): self.pad(8); v = struct.unpack_from('<Q', self.b, self.p)[0]; self.p += 8; return v
    def b_(self): return self.u() != 0
    def s(self):
        n = self.u(); v = self.b[self.p:self.p + n].decode(); self.p += n + 1; return v
    def g(self):
        n = self.b[self.p]; self.p += 1; v = self.b[self.p:self.p + n].decode(); self.p += n + 1; return v
    def ay(self):
        n = self.u(); v = bytes(self.b[self.p:self.p + n]); self.p += n; return v
    def variant(self):
        sig = self.g()
        return sig, self.value(sig)
    def value(self, sig):
        c = sig[0]
        if c == 'y': return self.y()
        if c == 'b': return self.b_()
        if c == 'u' or c == 'h': return self.u()
        if c == 't': return self.t()
        if c in 'so': return self.s()
        if c == 'g': return self.g()
        raise ValueError('sig ' + sig)

METHOD_CALL, METHOD_RETURN, ERROR, SIGNAL = 1, 2, 3, 4

def message(mtype, serial, fields, body=b'', sig='', flags=0, reply_serial=None):
    h = W()
    h.y(ord('l')); h.y(mtype); h.y(flags); h.y(1)
    h.u(len(body)); h.u(serial)
    f = W()
    items = []
    for code, (vs, val) in fields.items(): items.append((code, vs, val))
    if sig: items.append((8, 'g', sig))
    if reply_serial is not None: items.append((5, 'u', reply_serial))
    # header fields array: offset from message start matters for alignment, so build in place
    arr = W(); arr.b = bytearray(h.b)  # continue in the same buffer for correct alignment
    arr.u(0)  # length placeholder
    start = len(arr.b)
    for code, vs, val in items:
        arr.pad(8); arr.y(code); arr.g(vs)
        {'s': arr.s, 'o': arr.o, 'g': arr.g, 'u': arr.u}[vs](val)
    struct.pack_into('<I', arr.b, start - 4, len(arr.b) - start)
    arr.pad(8)
    return bytes(arr.b) + body

def parse_header(buf):
    """-> (total_len, mtype, flags, serial, fields, body_offset) or None if incomplete"""
    if len(buf) < 16: return None
    blen, serial, flen = struct.unpack_from('<III', buf, 4)
    hdr_end = 16 + flen
    body_off = hdr_end + ((8 - hdr_end % 8) % 8)
    total = body_off + blen
    if len(buf) < total: return None
    r = R(buf, 16); fields = {}
    while r.p < hdr_end:
        r.pad(8)
        if r.p >= hdr_end: break
        code = r.y(); vs, val = r.variant(); fields[code] = val
    return total, buf[1], buf[2], serial, fields, body_off

# ------------------------------------------------------------------ transport with fd passing
def send_with_fds(sock, data, fds=()):
    if fds:
        sock.sendmsg([data], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', fds))])
    else:
        sock.sendall(data)

def readline(sock):
    b = b''
    while not b.endswith(b'\r\n'):
        c = sock.recv(1)
        if not c: raise EOFError
        b += c
    return b.decode().strip()

def auth_line():
    if sys.platform == 'win32':
        # QEMU's p2p server on Windows rejects EXTERNAL from a duplicated socket; it offers ANONYMOUS
        return b'AUTH ANONYMOUS 627363796e7468\r\n'
    return ('AUTH EXTERNAL %s\r\n' % str(os.getuid()).encode().hex()).encode()

# ------------------------------------------------------------------ QMP
WIN = sys.platform == 'win32'

def qmp(path, cmd, args=None, fd=None):
    if ':' in path and not path.startswith('/'):
        h, p = path.rsplit(':', 1); s = socket.create_connection((h, int(p)))
    else:
        s = socket.socket(socket.AF_UNIX); s.connect(path)
    f = s.makefile('rb')
    f.readline()
    s.sendall(b'{"execute":"qmp_capabilities"}\n'); f.readline()
    msg = json.dumps({'execute': cmd, 'arguments': args or {}}).encode() + b'\n'
    if fd is not None: send_with_fds(s, msg, [fd])
    else: s.sendall(msg)
    while True:
        l = json.loads(f.readline())
        if 'return' in l or 'error' in l: s.close(); return l

# ------------------------------------------------------------------ the peer
class Stats:
    reads = 0; bytes = 0; fmt = None; enabled = None; t0 = None; log = []

def serve_listener(sock, gen, st):
    # QEMU authenticates as the server on this connection too: we are the SASL client, then we serve its calls
    sock.sendall(b'\0' + auth_line())
    st.log.append(('auth', time.time(), readline(sock)))
    sock.sendall(b'BEGIN\r\n')
    buf = b''; serial = 1000
    while True:
        d = sock.recv(65536)
        if not d: return
        buf += d
        while True:
            h = parse_header(buf)
            if not h: break
            total, mtype, flags, ser, fields, boff = h
            body = buf[boff:total]; buf = buf[total:]
            if mtype != METHOD_CALL: continue
            member, iface, sig = fields.get(3), fields.get(2), fields.get(8, '')
            r = R(body + b'', 0)
            # body alignment is relative to the body start, which is 8-aligned in the message
            out = W(); osig = ''
            if member == 'Init':
                i = r.t(); bits = r.y(); sg = r.b_(); fl = r.b_(); freq = r.u(); nch = r.y(); bpf = r.u(); bps = r.u(); be = r.b_()
                st.fmt = dict(bits=bits, signed=sg, float=fl, freq=freq, nch=nch, bpf=bpf, bps=bps, be=be)
                st.log.append(('Init', time.time(), st.fmt))
            elif member == 'SetEnabled':
                i = r.t(); st.enabled = r.b_(); st.log.append(('SetEnabled', time.time(), st.enabled))
                if st.enabled and st.t0 is None: st.t0 = time.time()
            elif member == 'Read':
                i = r.t(); size = r.t()
                data = gen(size, st.fmt)
                st.reads += 1; st.bytes += len(data)
                out.ay(data); osig = 'ay'
            elif member in ('Fini', 'SetVolume'):
                st.log.append((member, time.time(), None))
            elif iface == 'org.freedesktop.DBus.Properties' and member == 'Get':
                # Interfaces: an empty string array
                out.g('as'); out.u(0); osig = 'v'
            elif iface == 'org.freedesktop.DBus.Properties' and member == 'GetAll':
                out.u(0); osig = 'a{sv}'
            if flags & 1:   # NO_REPLY_EXPECTED
                continue
            serial += 1
            fields_out = {}
            if fields.get(7): fields_out[6] = ('s', fields[7])   # DESTINATION <- SENDER
            sock.sendall(message(METHOD_RETURN, serial, fields_out, bytes(out.b), osig, reply_serial=ser))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('qmp')
    ap.add_argument('--tone', type=float, default=1000.0)
    ap.add_argument('--clicks', action='store_true')
    ap.add_argument('--seconds', type=float, default=90)
    ap.add_argument('--pid', type=int, default=0, help='Windows: QEMU process id (socket duplication)')
    a = ap.parse_args()
    st = Stats()
    phase = [0.0]; pos = [0]

    cache = {}
    def gen(size, fmt):
        # one precomputed second of the signal, sliced cyclically (Python is too slow per sample on Windows)
        fmt = fmt or dict(bits=16, nch=2, freq=44100, bpf=4)
        sr, nch = fmt['freq'], fmt['nch']
        key = (sr, nch)
        if key not in cache:
            out = array.array('h')
            for k in range(sr):
                v = (20000 if k < 24 else 0) if a.clicks else int(16000 * math.sin(2 * math.pi * a.tone * k / sr))
                for c in range(nch): out.append(v)
            cache[key] = out.tobytes() * 2
        buf = cache[key]; one = len(buf) // 2
        n = (size // fmt['bpf']) * fmt['bpf']
        res = bytearray()
        while len(res) < n:
            k = min(n - len(res), one)
            res += buf[pos[0]:pos[0] + k]; pos[0] = (pos[0] + k) % one
        return bytes(res)

    # 1. the p2p D-Bus connection to QEMU
    if WIN:
        import base64
        a1, b1 = socket.socketpair()
        for x in (a1, b1): x.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        info = a1.share(a.pid)            # WSAPROTOCOL_INFOW for QEMU's process
        print('get-win32-socket', qmp(a.qmp, 'get-win32-socket', {'info': base64.b64encode(info).decode(), 'fdname': 'dbus1'}))
    else:
        a1, b1 = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        print('getfd', qmp(a.qmp, 'getfd', {'fdname': 'dbus1'}, fd=a1.fileno()))
    a1.close()
    print('add_client', qmp(a.qmp, 'add_client', {'protocol': '@dbus-display', 'fdname': 'dbus1'}))
    s = b1
    s.sendall(b'\0' + auth_line())
    print('auth:', readline(s))
    if not WIN:
        s.sendall(b'NEGOTIATE_UNIX_FD\r\n'); print('fd:', readline(s))
    s.sendall(b'BEGIN\r\n')
    # 2. RegisterInListener: the other socketpair end goes to QEMU (an fd on Unix, WSAPROTOCOL_INFOW bytes on Windows)
    if WIN:
        c, d = socket.socketpair()
        for x in (c, d): x.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)   # loopback TCP: no Nagle stalls
        body = W(); body.ay(c.share(a.pid))
        m = message(METHOD_CALL, 1, {1: ('o', '/org/qemu/Display1/Audio'), 2: ('s', 'org.qemu.Display1.Audio'),
                                    3: ('s', 'RegisterInListener')}, bytes(body.b), 'ay')
    else:
        c, d = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        body = W(); body.u(0)
        m = message(METHOD_CALL, 1, {1: ('o', '/org/qemu/Display1/Audio'), 2: ('s', 'org.qemu.Display1.Audio'),
                                    3: ('s', 'RegisterInListener'), 9: ('u', 1)}, bytes(body.b), 'h')
    th = threading.Thread(target=serve_listener, args=(d, gen, st), daemon=True); th.start()
    if WIN: s.sendall(m)
    else: send_with_fds(s, m, [c.fileno()])
    c.close()
    s.settimeout(5)
    buf = b''
    try:
        while True:
            buf += s.recv(65536)
            h = parse_header(buf)
            if h:
                print('RegisterInListener ->', {2: 'return', 3: 'ERROR'}.get(h[1], h[1]), h[4].get(4, '')); break
    except socket.timeout:
        print('no reply to RegisterInListener')
    t_end = time.time() + a.seconds
    while time.time() < t_end:
        time.sleep(2)
        el = time.time() - st.t0 if st.t0 else 0
        rate = st.bytes / (st.fmt['bpf'] if st.fmt else 4) / el if el > 0 else 0
        print('reads %d, frames/s %.1f, fmt %s, enabled %s' % (st.reads, rate, st.fmt, st.enabled), flush=True)

if __name__ == '__main__':
    main()
