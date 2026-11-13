"""Test driver: plays the plugin's role against the engine through the shared-memory block (Linux)."""
import os, struct, subprocess, threading, time
from multiprocessing import shared_memory
HERE = os.path.dirname(os.path.abspath(__file__))
OFF = dict(l.split('=') for l in subprocess.run([os.environ.get('BS311_OFFS', os.path.join(HERE, 'offs'))], capture_output=True, text=True).stdout.split())
OFF = {k: int(v) for k, v in OFF.items()}
RING, EVN, REPN, W, H = 65536, 1024, 32768, 1024, 768

class Engine:
    def __init__(self, conf, state='-', core=None, name='bs311t', lead=2048, make_state=None, log='/tmp/bs311-engine.log'):
        self.name = name
        try: shared_memory.SharedMemory(name=name).unlink()
        except Exception: pass
        self.shm = shared_memory.SharedMemory(name=name, create=True, size=OFF['size'])
        self.m = self.shm.buf
        self.m[:OFF['size']] = bytes(OFF['size'])
        self.u32('magic', 0x4D485342); self.u32('version', 1); self.u32('rate', 48000); self.u32('ring_len', RING)
        self.u32('lead', lead); self.u32('vid_want', 1); self.u32('realtime', 0)
        args = [os.environ.get('BS311_ENGINE', os.path.join(HERE, 'engine')), '/' + name, core or os.environ['CORE'],
                conf, state, str(os.getpid())]
        if make_state: args += ['--make-state', make_state]
        env = dict(os.environ, BS311_LOG=log)
        self.t0 = time.time()
        self.p = subprocess.Popen(args, env=env)
        self.alive = True
        self.texts = []; self.packets = []
        threading.Thread(target=self._beat, daemon=True).start()

    def u32(self, k, v=None, off=0):
        o = OFF[k] + off
        if v is None: return struct.unpack_from('<I', self.m, o)[0]
        struct.pack_into('<I', self.m, o, v)
    def u64(self, k, v=None):
        if v is None: return struct.unpack_from('<Q', self.m, OFF[k])[0]
        struct.pack_into('<Q', self.m, OFF[k], v)
    def _beat(self):
        while self.alive:
            self.u64('host_beat', self.u64('host_beat') + 1); time.sleep(0.1)
    def state(self): return self.u32('state')
    def event(self, typ, words, id=0, at=0):
        w = self.u32('ev_w'); slot = OFF['ev'] + (w % EVN) * OFF['evsize']
        words = [((typ << 8) | (len(words) + 1))] + list(words)
        struct.pack_into('<IIQ', self.m, slot, len(words), id, at)
        struct.pack_into('<%dH' % len(words), self.m, slot + 16, *[x & 0xFFFF for x in words])
        assert len(words) <= 24 or True
        self.u32('ev_w', w + 1)
    def poll(self):
        r, w = self.u32('rep_r'), self.u32('rep_w')
        words = [struct.unpack_from('<H', self.m, OFF['rep'] + ((r + i) % REPN) * 2)[0] for i in range(w - r)]
        self.u32('rep_r', w)
        self.buf = getattr(self, 'buf', []) + words
        while self.buf:
            n = self.buf[0] & 0xFF or 1
            if len(self.buf) < n: break
            pk, self.buf = self.buf[:n], self.buf[n:]
            typ = pk[0] >> 8
            if typ in (3, 7):
                s = b''.join(struct.pack('<H', x) for x in pk[1:]).split(b'\0')[0].decode('latin1')
                self.frag = getattr(self, 'frag', '') + s
                if typ == 3:
                    self.texts.append(self.frag); print('  guest:', self.frag[:300]); self.frag = ''
            self.packets.append((typ, pk[1:]))
        return self.packets
    def wait_text(self, sub, timeout=30):
        t = time.time()
        while time.time() - t < timeout:
            self.poll()
            for s in self.texts:
                if sub in s: return s
            time.sleep(0.02)
        raise TimeoutError(sub)
    def wait_packet(self, typ, timeout=30):
        t = time.time()
        while time.time() - t < timeout:
            for p in self.poll():
                if p[0] == typ: self.packets.remove(p); return p
            time.sleep(0.01)
        raise TimeoutError(typ)
    def dac_w(self): return self.u64('dac_w')
    def read(self, start, n):
        import numpy as np
        a = np.frombuffer(self.m, dtype=np.float32, count=RING * 2, offset=OFF['ring']).reshape(RING, 2)
        idx = (np.arange(start, start + n) % RING)
        return a[idx].copy()
    def shot(self, path):
        from PIL import Image
        for _ in range(100):
            s = self.u32('vid_seq')
            if s & 1: time.sleep(0.002); continue
            w, h = self.u32('vid_w'), self.u32('vid_h')
            px = bytes(self.m[OFF['vid']:OFF['vid'] + w * h * 4])
            if self.u32('vid_seq') == s: break
        Image.frombuffer('RGBX', (w, h), px, 'raw', 'BGRX').convert('RGB').save(path)
    def record(self, seconds):
        """capture the DAC for `seconds` from now (engine paced by its own clock)"""
        start = self.dac_w(); out = []; pos = start; end = start + int(seconds * 48000)
        while pos < end:
            w = self.dac_w()
            if w > pos: n = min(w, end) - pos; out.append(self.read(pos, n)); pos += n
            time.sleep(0.01)
        import numpy as np
        return start, np.concatenate(out)
    def line(self, text, id=0, at=0):
        b = text.encode('latin1')
        chunks = [b[i:i + 240] for i in range(0, len(b), 240)] or [b'']
        for k, c in enumerate(chunks):
            if len(c) % 2: c += b'\0'
            words = [id & 0xFFFF, id >> 16] + list(struct.unpack('<%dH' % (len(c) // 2), c))
            self.event(4 if k == len(chunks) - 1 else 8, words, id if k == len(chunks) - 1 else 0, at)
    KEYS = {'enter': 13, 'esc': 27, 'backspace': 8, 'tab': 9, 'home': 278, 'end': 279, 'lshift': 304, 'left': 276, 'right': 275, 'delete': 127}
    SHIFTED = {'>': '.', '<': ',', '#': '3', '@': '2', '~': '`', ':': ';', '+': '='}
    def key(self, code, down):
        w = self.u32('key_w')
        struct.pack_into('<I', self.m, OFF['keys'] + (w % 64) * 4, (0x80000000 if down else 0) | code)
        self.u32('key_w', w + 1)
    def tap(self, name_or_code, dt=0.04):
        code = self.KEYS.get(name_or_code, name_or_code) if isinstance(name_or_code, str) else name_or_code
        if isinstance(code, str): code = ord(code)
        self.key(code, True); time.sleep(dt); self.key(code, False); time.sleep(dt)
    def type(self, text, dt=0.04):
        for ch in text:
            if ch in self.SHIFTED or ch.isupper():
                base = self.SHIFTED.get(ch, ch.lower())
                self.key(304, True); time.sleep(dt); self.tap(ord(base), dt); self.key(304, False); time.sleep(dt)
            else:
                self.tap(ord(ch), dt)
    def mouse(self, x, y, btn=0):
        struct.pack_into('<iiI', self.m, OFF['mouse_x'], x, y, btn); self.u32('mouse_seq', self.u32('mouse_seq') + 1)
    def close(self):
        self.u32('quit', 1)
        try: self.p.wait(5)
        except subprocess.TimeoutExpired: self.p.kill()
        self.alive = False
        self.m = None
        self.shm.close(); self.shm.unlink()

def wav(path, a, rate=48000):
    import wave
    import numpy as np
    x = (np.clip(a, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(rate); f.writeframes(x.tobytes())
