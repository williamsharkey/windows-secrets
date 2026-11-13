"""A small, fast RFB (VNC) client for QEMU's display: raw pixels over a private local socket, QEMU's
extended key events (PC scancodes, so every key reaches XP exactly), absolute pointer."""
import socket
import struct
import threading

# SDL scancode (USB HID usage) -> PC/XT scancode in QEMU's numbering (0x80 set = an E0-prefixed key)
SDL_TO_XT = {
    4: 0x1E, 5: 0x30, 6: 0x2E, 7: 0x20, 8: 0x12, 9: 0x21, 10: 0x22, 11: 0x23, 12: 0x17, 13: 0x24, 14: 0x25,
    15: 0x26, 16: 0x32, 17: 0x31, 18: 0x18, 19: 0x19, 20: 0x10, 21: 0x13, 22: 0x1F, 23: 0x14, 24: 0x16,
    25: 0x2F, 26: 0x11, 27: 0x2D, 28: 0x15, 29: 0x2C,
    30: 0x02, 31: 0x03, 32: 0x04, 33: 0x05, 34: 0x06, 35: 0x07, 36: 0x08, 37: 0x09, 38: 0x0A, 39: 0x0B,
    40: 0x1C, 41: 0x01, 42: 0x0E, 43: 0x0F, 44: 0x39, 45: 0x0C, 46: 0x0D, 47: 0x1A, 48: 0x1B, 49: 0x2B,
    50: 0x2B, 51: 0x27, 52: 0x28, 53: 0x29, 54: 0x33, 55: 0x34, 56: 0x35, 57: 0x3A,
    58: 0x3B, 59: 0x3C, 60: 0x3D, 61: 0x3E, 62: 0x3F, 63: 0x40, 64: 0x41, 65: 0x42, 66: 0x43, 67: 0x44,
    68: 0x57, 69: 0x58, 70: 0xB7, 71: 0x46, 73: 0xD2, 74: 0xC7, 75: 0xC9, 76: 0xD3, 77: 0xCF, 78: 0xD1,
    79: 0xCD, 80: 0xCB, 81: 0xD0, 82: 0xC8, 83: 0x45, 84: 0xB5, 85: 0x37, 86: 0x4A, 87: 0x4E, 88: 0x9C,
    89: 0x4F, 90: 0x50, 91: 0x51, 92: 0x4B, 93: 0x4C, 94: 0x4D, 95: 0x47, 96: 0x48, 97: 0x49, 98: 0x52,
    99: 0x53, 100: 0x56, 101: 0xDD,
    224: 0x1D, 225: 0x2A, 226: 0x38, 227: 0xDB, 228: 0x9D, 229: 0x36, 230: 0xB8, 231: 0xDC,
}


class VncError(Exception):
    pass


class Vnc:
    """Reads QEMU's screen into self.fb (RGBX bytes, self.w x self.h) in a thread of its own.
    on_change() is called (from that thread) after each update; keep it cheap."""

    def __init__(self, addr, on_change):
        self.addr, self.on_change = addr, on_change
        self.s = None
        self.w = self.h = 0
        self.fb = bytearray()
        self.lock = threading.Lock()
        self.size_gen = 0          # bumps when the screen changes size
        self.alive = False
        self.wlock = threading.Lock()

    def connect(self):
        kind, where = self.addr
        if kind == 'unix':
            s = socket.socket(socket.AF_UNIX)
            s.connect(where)
        else:
            s = socket.create_connection(('127.0.0.1', where), 5)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) if kind != 'unix' else None
        s.settimeout(None)
        self.s = s
        ver = self._n(12)
        if not ver.startswith(b'RFB '):
            raise VncError('not a VNC server')
        s.sendall(b'RFB 003.008\n')
        n = self._n(1)[0]
        types = self._n(n)
        if 1 not in types:
            raise VncError('the display wants a password')
        s.sendall(b'\x01')
        if struct.unpack('>I', self._n(4))[0] != 0:
            raise VncError('the display refused us')
        s.sendall(b'\x01')                                    # shared
        w, h = struct.unpack('>HH', self._n(4))
        self._n(16)
        self._n(struct.unpack('>I', self._n(4))[0])
        self._resize(w, h)
        # 32 bits per pixel, bytes R G B X: what the texture wants, no conversion anywhere
        pf = struct.pack('>BBBBHHHBBB3x', 32, 24, 0, 1, 255, 255, 255, 0, 8, 16)
        s.sendall(b'\x00\x00\x00\x00' + pf)
        enc = [0, -223, -258]                                 # raw, desktop size, QEMU extended key events
        s.sendall(struct.pack('>BxH', 2, len(enc)) + b''.join(struct.pack('>i', e) for e in enc))
        self.alive = True
        self._request(False)
        threading.Thread(target=self._run, daemon=True, name='vnc').start()

    def _n(self, n):
        buf = bytearray(n)
        mv = memoryview(buf)
        got = 0
        while got < n:
            k = self.s.recv_into(mv[got:], n - got)
            if not k:
                raise VncError('the display closed')
            got += k
        return bytes(buf)

    def _into(self, mv):
        got, n = 0, len(mv)
        while got < n:
            k = self.s.recv_into(mv[got:], n - got)
            if not k:
                raise VncError('the display closed')
            got += k

    def _resize(self, w, h):
        with self.lock:
            self.w, self.h = w, h
            self.fb = bytearray(w * h * 4)
            self.size_gen += 1

    def _request(self, incremental=True):
        with self.wlock:
            self.s.sendall(struct.pack('>BBHHHH', 3, 1 if incremental else 0, 0, 0, self.w, self.h))

    def _run(self):
        try:
            row = bytearray()
            while True:
                t = self._n(1)[0]
                if t == 0:
                    n = struct.unpack('>xH', self._n(3))[0]
                    for _ in range(n):
                        x, y, w, h, e = struct.unpack('>HHHHi', self._n(12))
                        if e == 0:
                            need = w * h * 4
                            if len(row) < need:
                                row = bytearray(need)
                            mv = memoryview(row)[:need]
                            self._into(mv)
                            with self.lock:
                                if x + w <= self.w and y + h <= self.h:
                                    fb, W, rw = self.fb, self.w * 4, w * 4
                                    if x == 0 and w == self.w:
                                        fb[y * W:(y + h) * W] = mv
                                    else:
                                        o = y * W + x * 4
                                        for r in range(h):
                                            fb[o:o + rw] = mv[r * rw:(r + 1) * rw]
                                            o += W
                        elif e == -223:
                            self._resize(w, h)
                        elif e == -258:
                            pass
                        else:
                            raise VncError('unexpected encoding %d' % e)
                    self.on_change()
                    self._request(True)
                elif t == 2:
                    pass                                              # bell
                elif t == 3:
                    self._n(3)
                    self._n(struct.unpack('>I', self._n(4))[0])
                elif t == 1:
                    self._n(1)
                    k = struct.unpack('>HH', self._n(4))[1]
                    self._n(6 * k)
                else:
                    raise VncError('unexpected message %d' % t)
        except (OSError, VncError, struct.error):
            self.alive = False
            self.on_change()

    def key(self, sdl_scancode, down):
        xt = SDL_TO_XT.get(sdl_scancode)
        if xt is None or not self.alive:
            return
        try:
            with self.wlock:
                self.s.sendall(struct.pack('>BBHII', 255, 0, 1 if down else 0, 0, xt))
        except OSError:
            pass

    def pointer(self, x, y, buttons):
        if not self.alive:
            return
        x = max(0, min(self.w - 1, int(x)))
        y = max(0, min(self.h - 1, int(y)))
        try:
            with self.wlock:
                self.s.sendall(struct.pack('>BBHH', 5, buttons & 0xFF, x, y))
        except OSError:
            pass

    def close(self):
        self.alive = False
        try:
            self.s.close()
        except (OSError, AttributeError):
            pass
