"""dbusdisplay.py: listen to QEMU's p2p D-Bus display (console 0) and time-stamp each screen Update it pushes.
Unix only (QMP fd passing over SCM_RIGHTS). Standard library; the wire code is dbuswire.py (from the X0 audio peer)."""
import os, socket, struct, threading, time
from dbuswire import W, message, parse_header, send_with_fds, readline, qmp, METHOD_CALL, METHOD_RETURN

def start(qmp_path, on_update, log=None):
    a1, b1 = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    r1 = qmp(qmp_path, 'getfd', {'fdname': 'dbusdisp'}, fd=a1.fileno()); a1.close()
    r2 = qmp(qmp_path, 'add_client', {'protocol': '@dbus-display', 'fdname': 'dbusdisp'})
    s = b1
    s.sendall(b'\0' + ('AUTH EXTERNAL %s\r\n' % str(os.getuid()).encode().hex()).encode()); readline(s)
    s.sendall(b'NEGOTIATE_UNIX_FD\r\n'); readline(s); s.sendall(b'BEGIN\r\n')
    c, d = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    body = W(); body.u(0)
    m = message(METHOD_CALL, 1, {1: ('o', '/org/qemu/Display1/Console_0'), 2: ('s', 'org.qemu.Display1.Console'),
                                3: ('s', 'RegisterListener'), 9: ('u', 1)}, bytes(body.b), 'h')
    def serve():
        d.sendall(b'\0' + ('AUTH EXTERNAL %s\r\n' % str(os.getuid()).encode().hex()).encode()); readline(d)
        d.sendall(b'BEGIN\r\n')
        buf = b''; ser = 5000
        while True:
            x = d.recv(1 << 20)
            if not x: return
            buf += x
            while True:
                h = parse_header(buf)
                if not h: break
                total, mtype, flags, sr, fields, boff = h
                buf = buf[total:]
                if mtype != METHOD_CALL: continue
                member, iface = fields.get(3), fields.get(2)
                if member in ('Update', 'UpdateMap', 'Scanout', 'ScanoutMap', 'UpdateDMABUF', 'ScanoutDMABUF'):
                    on_update(time.time(), member)
                out = W(); osig = ''
                if iface == 'org.freedesktop.DBus.Properties' and member == 'Get':
                    out.g('as'); out.u(0); osig = 'v'
                elif iface == 'org.freedesktop.DBus.Properties' and member == 'GetAll':
                    out.u(0); osig = 'a{sv}'
                if flags & 1: continue
                ser += 1
                fo = {}
                if fields.get(7): fo[6] = ('s', fields[7])
                d.sendall(message(METHOD_RETURN, ser, fo, bytes(out.b), osig, reply_serial=sr))
    threading.Thread(target=serve, daemon=True).start()
    send_with_fds(s, m, [c.fileno()]); c.close()
    s.settimeout(5)
    buf = b''
    while True:
        buf += s.recv(65536)
        h = parse_header(buf)
        if h: return {2: 'ok', 3: 'error'}.get(h[1], h[1]), h[4].get(4, ''), r1, r2, s
