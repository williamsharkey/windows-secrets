#!/usr/bin/env python3
"""latprobe.py - keystroke-to-pixels latency of BASILISK 3.11, measured on the host:
inject one character as the driver (admin/type), time until x11vnc ships a framebuffer update
that touches the Terminal pane.  Usage: latprobe.py N"""
import socket, struct, sys, time, subprocess, threading, select

def rfb():
    s = socket.create_connection(('127.0.0.1', 5931))
    s.recv(12); s.sendall(b'RFB 003.008\n')
    n = s.recv(1)[0]; types = s.recv(n)
    s.sendall(b'\x01'); s.recv(4)            # None security, result
    s.sendall(b'\x01')                        # shared
    hdr = recvn(s, 24); w, h = struct.unpack('>HH', hdr[:4]); nl = struct.unpack('>I', hdr[20:24])[0]; recvn(s, nl)
    s.sendall(struct.pack('>BBH', 2, 0, 1) + struct.pack('>i', 0))   # raw only
    # 32bpp pixel format default; request full once
    s.sendall(struct.pack('>BBHHHH', 3, 0, 0, 0, w, h))
    return s, w, h

def recvn(s, n):
    b = b''
    while len(b) < n:
        d = s.recv(n - len(b))
        if not d: raise EOFError
        b += d
    return b

def read_update(s, bpp=4):
    t = recvn(s, 1)[0]
    if t != 0:
        raise RuntimeError('msg %d' % t)
    recvn(s, 1); nr = struct.unpack('>H', recvn(s, 2))[0]
    rects = []
    for _ in range(nr):
        x, y, w, h, enc = struct.unpack('>HHHHi', recvn(s, 12))
        if enc == 0:
            recvn(s, w * h * bpp)
        rects.append((x, y, w, h))
    return rects

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    s, W, H = rfb()
    read_update(s)
    token = open('/root/w31/data/admin.token').read().strip()
    res = []
    for i in range(n):
        # drain: ask incremental, wait for quiet
        s.sendall(struct.pack('>BBHHHH', 3, 1, 0, 0, W, H))
        while True:
            r, _, _ = select.select([s], [], [], 0.25)
            if not r: break
            read_update(s); s.sendall(struct.pack('>BBHHHH', 3, 1, 0, 0, W, H))
        ch = 'abcdefghij'[i % 10]
        t0 = time.time()
        subprocess.Popen(['curl', '-s', '-XPOST', 'http://127.0.0.1:8782/admin/type?token=' + token, '--data-binary', ch],
                         stdout=subprocess.DEVNULL)
        while True:
            r, _, _ = select.select([s], [], [], 3)
            if not r:
                res.append(None); break
            rects = read_update(s)
            if any(x < 660 for x, y, w, h in rects):
                res.append(time.time() - t0); break
            s.sendall(struct.pack('>BBHHHH', 3, 1, 0, 0, W, H))
        time.sleep(0.3)
    ok = sorted(r for r in res if r)
    print('samples', len(ok), 'of', n, 'ms:', [round(x * 1000) for x in ok])
    if ok:
        print('median %.0f ms  p90 %.0f ms' % (ok[len(ok) // 2] * 1000, ok[int(len(ok) * 0.9) - 1] * 1000))
    # clean the line
    subprocess.run(['curl', '-s', '-XPOST', 'http://127.0.0.1:8782/admin/type?token=' + token, '--data-binary', '\x08' * n], stdout=subprocess.DEVNULL)

main()
