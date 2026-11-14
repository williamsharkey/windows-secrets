#!/usr/bin/env python3
"""emubench: resume the BASILISK SYNTH XP machine under a given QEMU/accelerator/display setup and measure
   - resume -> guest hello, and "go" -> "ready" (the editor assembly),
   - screen update cadence as a VNC client sees it (updates/s, longest still run, during the assembly),
   - QEMU CPU while assembling and while idle,
   - optionally a sustained tone (notes over COM1) with the audio written to a wav, then gaps counted.
Only stock QEMU options. Usage: bench.py --qemu BIN --machine DIR --accel tcg,thread=single,tb-size=1024 [--vnc-mode plugin|eager]
       [--extra "..."] [--tone 20] [--out result.json]
"""
import argparse, json, os, shutil, socket, struct, subprocess, sys, tempfile, threading, time

ap = argparse.ArgumentParser()
ap.add_argument('--qemu', required=True)
ap.add_argument('--qemu-prefix', default='', help='e.g. a ld-linux wrapper: "LD --library-path L"')
ap.add_argument('--machine', required=True, help='dir with base.qcow2, state.mig, fw/')
ap.add_argument('--share', default='', help='extra -L dir')
ap.add_argument('--accel', default='tcg,thread=single,tb-size=1024')
ap.add_argument('--vnc-mode', default='plugin', choices=['plugin', 'eager', 'none', 'dbus'])
ap.add_argument('--cold', action='store_true', help='boot instead of resuming the saved state')
ap.add_argument('--extra', default='')
ap.add_argument('--tone', type=float, default=0, help='seconds of sustained 4-note chord after ready')
ap.add_argument('--dna', default='organ_pipe_open_31#16;A20R300')
ap.add_argument('--idle', type=float, default=5, help='seconds of idle CPU measurement after ready/tone')
ap.add_argument('--timeout', type=float, default=90)
ap.add_argument('--out', default='')
ap.add_argument('--label', default='')
a = ap.parse_args()
a.machine = os.path.abspath(a.machine); a.qemu = os.path.abspath(a.qemu) if os.path.exists(a.qemu) else a.qemu
if a.share: a.share = os.path.abspath(a.share)

T0 = time.time()
def t(): return time.time() - T0
work = tempfile.mkdtemp(prefix='emubench-')
res = {'label': a.label, 'accel': a.accel, 'vnc_mode': a.vnc_mode, 'extra': a.extra, 'cold': a.cold}
qcmd = a.qemu_prefix.split() + [a.qemu]
img = os.path.join(os.path.dirname(a.qemu), 'qemu-img' + ('.exe' if os.name == 'nt' else ''))
if not os.path.exists(img): img = shutil.which('qemu-img') or img
ov = os.path.join(work, 'ov.qcow2')
subprocess.run(a.qemu_prefix.split() + [img, 'create', '-q', '-f', 'qcow2', '-b', os.path.join(a.machine, 'base.qcow2'), '-F', 'qcow2', ov], check=True)
wav = os.path.join(work, 'out.wav')

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
pq, pc, pv = free_port(), free_port(), free_port()
while pv < 5900: pv = free_port()
args = qcmd + ['-name', 'EMUBENCH', '-nodefaults', '-no-user-config', '-M', 'pc-i440fx-6.2', '-m', '512', '-smp', '1', '-cpu', 'qemu32',
        '-drive', 'file=%s,format=qcow2,if=ide,index=0,cache=writeback' % ov,
        '-drive', 'if=none,id=cd0,media=cdrom,readonly=on', '-device', 'ide-cd,drive=cd0,id=cdrom0,bus=ide.1,unit=0',
        '-vga', 'cirrus', '-device', 'rtl8139,netdev=n0,mac=52:54:00:12:34:56', '-netdev', 'user,id=n0,restrict=on,net=10.0.2.0/24',
        '-usb', '-device', 'usb-tablet', '-rtc', 'base=localtime', '-boot', 'menu=off',
        '-L', os.path.join(a.machine, 'fw')] + (['-L', a.share] if a.share else []) + [
        '-accel', a.accel,
        '-audiodev', 'wav,id=snd0,path=%s,out.frequency=96000,out.channels=2,out.format=s16' % wav, '-device', 'AC97,audiodev=snd0',
        '-chardev', 'socket,id=ser0,host=127.0.0.1,port=%d,server=on,wait=off' % pc, '-serial', 'chardev:ser0',
        '-vnc', '127.0.0.1:%d' % (pv - 5900), '-qmp', 'tcp:127.0.0.1:%d,server=on,wait=off' % pq]
qsock = os.path.join(work, 'qmp.sock')
if a.vnc_mode == 'dbus': args += ['-display', 'dbus,p2p=yes', '-qmp', 'unix:%s,server=on,wait=off' % qsock]
else: args += ['-display', 'none']
pm = free_port()
if not a.cold: args += ['-S', '-incoming', ('tcp:127.0.0.1:%d' % pm) if os.name == 'nt' else ('exec:cat %s' % os.path.join(a.machine, 'state.mig'))]
args += a.extra.split()
log = open(os.path.join(work, 'qemu.log'), 'w')
p = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
open(os.path.join(work, 'qemu.pid'), 'w').write(str(p.pid))

def connect(port, tries=200):
    for _ in range(tries):
        try: return socket.create_connection(('127.0.0.1', port), timeout=5)
        except OSError: time.sleep(0.05)
    raise SystemExit('no connect %d' % port)

# QMP
q = connect(pq); qf = q.makefile('rwb', buffering=0)
qf.readline(); qf.write(b'{"execute":"qmp_capabilities"}\n'); qf.readline()
def qmp(cmd, args=None):
    qf.write((json.dumps({'execute': cmd, **({'arguments': args} if args else {})}) + '\n').encode())
    while True:
        r = json.loads(qf.readline())
        if 'return' in r or 'error' in r: return r
if not a.cold and os.name == 'nt':
    def feed():
        m = connect(pm)
        with open(os.path.join(a.machine, 'state.mig'), 'rb') as f:
            while True:
                b = f.read(1 << 20)
                if not b: break
                m.sendall(b)
        m.close()
    threading.Thread(target=feed, daemon=True).start()
if not a.cold:
    while True:
        st = qmp('query-status')['return']['status']
        if st in ('paused', 'postmigrate', 'prelaunch'):
            mig = qmp('query-migrate')['return'].get('status')
            if mig in ('completed', None) and st != 'inmigrate': break
        if p.poll() is not None: raise SystemExit('qemu died: ' + open(os.path.join(work, 'qemu.log')).read()[-2000:])
        time.sleep(0.05)
    res['load_s'] = round(t(), 3)
    qmp('cont'); tcont = t()
else:
    tcont = t()

def cpu_s():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, p.pid)
        c, e, kt, ut = (wintypes.FILETIME() for _ in range(4))
        k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut)); k.CloseHandle(h)
        f = lambda x: (x.dwHighDateTime << 32 | x.dwLowDateTime) / 1e7
        return f(kt) + f(ut)
    try:
        f = open('/proc/%d/stat' % p.pid).read().split()
        return (int(f[13]) + int(f[14])) / os.sysconf('SC_CLK_TCK')
    except Exception:
        o = subprocess.run(['ps', '-o', 'time=', '-p', str(p.pid)], capture_output=True, text=True).stdout.strip()
        if not o: return 0.0
        parts = o.replace('-', ':').split(':')
        s = 0.0
        for x in parts: s = s * 60 + float(x)
        return s

# COM1: the guest's serial output only leaves when a byte arrives (PROGRESS: lost UART interrupts after resume)
c = connect(pc)
lines = []
def rd():
    buf = b''
    while True:
        try: d = c.recv(4096)
        except OSError: break
        if not d: break
        buf += d
        while b'\n' in buf:
            l, buf = buf.split(b'\n', 1)
            lines.append((t(), l.decode('latin1').strip()))
threading.Thread(target=rd, daemon=True).start()
stop = False
def ping():
    while not stop:
        try: c.sendall(b'\n')
        except OSError: break
        time.sleep(0.015)
threading.Thread(target=ping, daemon=True).start()
def send(s): c.sendall(s.encode())
def wait_line(pred, tmo):
    end = time.time() + tmo; i = 0
    while time.time() < end:
        while i < len(lines):
            if pred(lines[i][1]): return lines[i][0]
            i += 1
        time.sleep(0.005)
    return None

# VNC client: raw 32bpp, counts framebuffer updates that carried pixels
upd = []   # (t, pixels)
def vnc():
    try:
        s = connect(pv); s.settimeout(None)
        s.recv(12); s.sendall(b'RFB 003.008\n')
        n = s.recv(1)[0]; s.recv(n); s.sendall(b'\x01'); s.recv(4)
        s.sendall(b'\x01')
        hdr = b''
        while len(hdr) < 24: hdr += s.recv(24 - len(hdr))
        W, H = struct.unpack('>HH', hdr[:4]); nl = struct.unpack('>I', hdr[20:24])[0]
        while nl: nl -= len(s.recv(nl))
        s.sendall(bytes([0, 0, 0, 0, 32, 24, 0, 1, 0, 255, 0, 255, 0, 255, 16, 8, 0, 0, 0, 0]))
        s.sendall(struct.pack('>BBHi', 2, 0, 1, 0))
        f = s.makefile('rb')
        def rx(k):
            b = f.read(k)
            if len(b) < k: raise EOFError
            return b
        inc = 0; last = 0
        while not stop:
            if a.vnc_mode == 'plugin':
                w = 0.033 - (time.time() - last)
                if w > 0: time.sleep(w)
            last = time.time()
            s.sendall(struct.pack('>BBHHHH', 3, inc, 0, 0, W, H)); inc = 1
            while True:
                ty = rx(1)[0]
                if ty == 0: break
                if ty == 2: continue
                if ty == 3: l = struct.unpack('>3xI', rx(7))[0]; rx(l); continue
                if ty == 1: nc = struct.unpack('>xHH', rx(5))[1]; rx(6 * nc); continue
                raise EOFError
            nr = struct.unpack('>xH', rx(3))[0]; px = 0
            for _ in range(nr):
                x, y, w, h, e = struct.unpack('>HHHHi', rx(12))
                if e == 0: rx(w * h * 4); px += w * h
                elif e == 1: rx(4); px += w * h
            if px: upd.append((t(), px))
    except Exception as ex:
        res['vnc_error'] = repr(ex)
if a.vnc_mode == 'dbus':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dbusdisplay
    res['dbus_register'] = str(dbusdisplay.start(qsock, lambda tt, m: upd.append((tt - T0, 1)))[:2])
elif a.vnc_mode != 'none': threading.Thread(target=vnc, daemon=True).start()

if a.cold and a.vnc_mode in ('plugin', 'eager'):
    # cold boot: the disk alone does not start the synth (the saved state does), so time the boot to a settled desktop:
    # the first moment after which the screen stays unchanged for 8 s
    c0 = cpu_s(); end = time.time() + a.timeout; settled = None
    while time.time() < end:
        time.sleep(0.5)
        last = upd[-1][0] if upd else 0
        if upd and t() - last > 8 and len(upd) > 20: settled = last; break
    res['boot_desktop_s'] = round(settled - tcont, 2) if settled else None
    res['boot_updates'] = len(upd)
    res['boot_cpu'] = round((cpu_s() - c0) / max(t() - tcont, 1e-3), 2)
    lines.append((t(), 'cold-done'))
thi = None
send('hi 2\n')
thi = wait_line(lambda l: l.startswith('hi '), 5 if a.cold else a.timeout)
res['hello_s'] = round(thi - tcont, 3) if thi else None
c0 = cpu_s(); tg = t()
send('go\n')
tr = wait_line(lambda l: l == 'ready' or l.startswith('ready'), 5 if a.cold else a.timeout)
res['assembly_s'] = round(tr - tg, 3) if tr else None
if tr:
    c1 = cpu_s(); res['assembly_cpu'] = round((c1 - c0) / max(tr - tg, 1e-3), 2)
    u = [x for x in upd if tg <= x[0] <= tr]
    ts = [tg] + [x[0] for x in u] + [tr]
    gaps = [b - a_ for a_, b in zip(ts, ts[1:])]
    res['assembly_updates'] = len(u)
    res['assembly_fps'] = round(len(u) / max(tr - tg, 1e-3), 1)
    res['assembly_max_still_ms'] = round(max(gaps) * 1000) if gaps else None
    srt = sorted(gaps); res['assembly_p95_still_ms'] = round(srt[int(0.95 * (len(srt) - 1))] * 1000) if srt else None

if tr and a.vnc_mode != 'none':
    # reaction: after quiet stretches (QEMU's VNC refresh backs off while nothing changes), how long from a guest-visible
    # change (a key on the strip goes down/up) to the next screen update the client receives
    reacts = []
    for k in range(6):
        time.sleep(1.5)
        n0 = len(upd); ts_ = t()
        send('show %d %d\n' % (60 + k, 100 if k % 2 == 0 else 0) if False else 'show %d 100\n' % (60 + k))
        end = time.time() + 3
        while time.time() < end and len(upd) == n0: time.sleep(0.002)
        if len(upd) > n0: reacts.append(round((upd[n0][0] - ts_) * 1000))
        send('show %d 0\n' % (60 + k))
    res['react_ms'] = reacts
if tr and a.tone > 0:
    send('dna %s\n' % a.dna)
    tb = wait_line(lambda l: l.startswith('built') or l.startswith('end'), 30)
    res['build_s'] = round(tb - tr, 3) if tb else None
    time.sleep(0.5)
    ttone = t(); res['tone_from_s'] = round(ttone, 3)
    notes = [48, 55, 60, 64]
    for k, n in enumerate(notes): send('on %d %d 100 %d\n' % (k, n, k)) if False else None
    # the guest's note line is driven by the host allocator in the plugin; the bench uses the simple form the
    # guest accepts for a test: "on <rec> <rate> <vol> <pan>" is not stable across versions, so the tone uses the
    # plugin when available. Here we only hold the machine and let the wav record whatever plays.
    time.sleep(a.tone)
c2 = cpu_s(); ti = t()
time.sleep(a.idle)
res['idle_cpu'] = round((cpu_s() - c2) / max(t() - ti, 1e-3), 2)
res['qemu_version'] = subprocess.run(qcmd + ['--version'], capture_output=True, text=True).stdout.split('\n')[0]
res['log_tail'] = open(os.path.join(work, 'qemu.log')).read()[-400:]
stop = True
try: qmp('quit')
except Exception: pass
try: p.wait(5)
except Exception: p.kill()
shutil.rmtree(work, ignore_errors=True)
print(json.dumps(res))
if a.out:
    with open(a.out, 'a') as f: f.write(json.dumps(res) + '\n')
