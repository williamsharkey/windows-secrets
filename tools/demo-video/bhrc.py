#!/usr/bin/env python3
"""Read a BasiliskHost `rec` capture (.bhrc): the editor's frames with their wall-clock times.

    bhrc.py info FILE.bhrc
    bhrc.py png FILE.bhrc T OUT.png          the frame on screen at audio time T (seconds into the render's WAV)

Format (tools/basilisk-host/src/harness.cpp, EditorRun::recStart): "BHRC", render start (f64), W, H (i32); then
per frame: time (f64), x, y, w, h (i32) and w*h BGRX pixels of the rectangle that changed since the frame before.
"""
import struct, sys
import numpy as np


class Capture:
    def __init__(self, path):
        self.f = open(path, 'rb')
        d = self.f.read(20)
        assert d[:4] == b'BHRC', path
        self.start, = struct.unpack('<d', d[4:12])
        self.W, self.H = struct.unpack('<ii', d[12:20])
        self.idx = []           # (audio time, offset of the rect header)
        pos = 20
        while True:
            self.f.seek(pos)
            h = self.f.read(24)
            if len(h) < 24: break
            t, x, y, w, hh = struct.unpack('<diiii', h)
            self.idx.append((t - self.start, pos))
            pos += 24 + w * hh * 4
        self.times = np.array([t for t, _ in self.idx])
        self._k = -1
        self._ck = {}
        self._img = np.zeros((self.H, self.W, 3), np.uint8)

    def _apply(self, k):
        self.f.seek(self.idx[k][1])
        t, x, y, w, h = struct.unpack('<diiii', self.f.read(24))
        if w:
            px = np.frombuffer(self.f.read(w * h * 4), np.uint8).reshape(h, w, 4)
            self._img[y:y + h, x:x + w] = px[:, :, 2::-1]

    def frame(self, t):
        """RGB uint8 (H, W, 3) on screen at audio time t (the latest frame captured at or before t)."""
        k = max(0, int(np.searchsorted(self.times, t, 'right')) - 1)
        if k < self._k:     # back to the nearest checkpoint at or before k
            c = max([j for j in self._ck if j <= k], default=-1)
            if c < 0: self._k = -1; self._img[:] = 0
            else: self._k = c; self._img[:] = self._ck[c]
        while self._k < k:
            self._k += 1; self._apply(self._k)
            if self._k % 150 == 0 and self._k not in self._ck: self._ck[self._k] = self._img.copy()
        return self._img

    @property
    def first(self): return float(self.times[0]) if len(self.times) else 0.0

    @property
    def last(self): return float(self.times[-1]) if len(self.times) else 0.0


if __name__ == '__main__':
    c = Capture(sys.argv[2])
    if sys.argv[1] == 'info':
        dt = np.diff(c.times)
        print(f'{c.W}x{c.H}, {len(c.idx)} frames, {c.first:.2f}..{c.last:.2f} s, interval median {np.median(dt)*1000:.1f} ms max {dt.max()*1000:.0f} ms')
    elif sys.argv[1] == 'png':
        from PIL import Image
        Image.fromarray(c.frame(float(sys.argv[3]))).save(sys.argv[4])
