"""The XP machine: finding QEMU, its command line, QMP control and snapshots. No UI here.

Every BASILISK on every OS runs the same virtual PC (so one shipped snapshot loads anywhere):
i440FX (QEMU 6.2 flavour), 2 x qemu32 CPUs, 512 MB, Cirrus VGA, RTL8139, USB tablet, one IDE disk (no sound card: XP's AC97 driver hangs after a snapshot resume).
QEMU never shows a window of its own: the app reads its screen over VNC (a private local socket).
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

APP = os.path.dirname(os.path.abspath(__file__))
WIN = os.name == 'nt'
MAC = sys.platform == 'darwin'
NOWIN = subprocess.CREATE_NO_WINDOW if WIN else 0


def bundle_root():
    """the folder holding app/, runtime/ and qemu/ (inside BASILISK.app on macOS: Contents/Resources)"""
    return os.environ.get('BASILISK_BUNDLE') or os.path.dirname(APP)


class Qemu:
    """how to run the QEMU we ship (or the system's, on Linux, as a fallback)"""

    def __init__(self):
        root = bundle_root()
        q = os.path.join(root, 'qemu')
        self.env = dict(os.environ)
        self.prefix = []
        self.share = None
        if WIN and os.path.isfile(os.path.join(q, 'qemu-system-i386w.exe')):
            self.exe = os.path.join(q, 'qemu-system-i386w.exe')
            self.img = os.path.join(q, 'qemu-img.exe')
            self.share = os.path.join(q, 'share')
        elif MAC and os.path.isfile(os.path.join(q, 'bin', 'qemu-system-i386')):
            self.exe = os.path.join(q, 'bin', 'qemu-system-i386')
            self.img = os.path.join(q, 'bin', 'qemu-img')
            self.share = os.path.join(q, 'share', 'qemu')
        elif os.path.isfile(os.path.join(q, 'lib', 'ld-linux-x86-64.so.2')):
            # Linux: QEMU with its own C library, run through its own loader, so any distribution will do
            lib = os.path.join(q, 'lib')
            self.prefix = [os.path.join(lib, 'ld-linux-x86-64.so.2'), '--library-path', lib]
            self.exe = os.path.join(q, 'bin', 'qemu-system-i386')
            self.img = os.path.join(q, 'bin', 'qemu-img')
            self.share = os.path.join(q, 'share')
            self.env['QEMU_MODULE_DIR'] = os.path.join(lib, 'modules')
        else:
            self.exe = os.environ.get('BASILISK_QEMU') or shutil.which('qemu-system-i386')
            self.img = shutil.which('qemu-img')
        if not self.exe:
            raise RuntimeError('QEMU is missing from this copy of BASILISK.')

    def cmd(self, *a):
        return self.prefix + [self.exe] + list(a)

    def img_cmd(self, *a):
        return self.prefix + [self.img] + list(a)

    def snapshots(self, disk):
        """names of the internal snapshots in disk (empty if it cannot be read)"""
        try:
            out = subprocess.run(self.img_cmd('info', '-U', '--output=json', disk), capture_output=True, text=True,
                                 env=self.env, creationflags=NOWIN, timeout=60).stdout
            return {s['name'] for s in json.loads(out).get('snapshots', [])}
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError):
            return set()


def kvm_ok():
    return sys.platform.startswith('linux') and os.access('/dev/kvm', os.R_OK | os.W_OK)


def free_port(want=0):
    """want, if it is free (0: any free port); None if want is taken"""
    s = socket.socket()
    try:
        s.bind(('127.0.0.1', want))
        return s.getsockname()[1]
    except OSError:
        return None
    finally:
        s.close()


def sock_dir():
    """short private folder for unix sockets (macOS limits their paths to 104 bytes)"""
    base = '/tmp' if not WIN else tempfile.gettempdir()
    d = os.path.join(base, 'basilisk-%s' % (os.getuid() if hasattr(os, 'getuid') else os.getpid()))
    os.makedirs(d, mode=0o700, exist_ok=True)
    if not WIN:
        os.chmod(d, 0o700)
    return d


class Machine:
    """one running QEMU: start, QMP, snapshots, stop"""

    def __init__(self, qemu, disk, log_path, guest_port, accel='tcg', sound=False, relay_python=None):
        self.q, self.disk, self.log_path = qemu, disk, log_path
        self.guest_port, self.accel, self.sound = guest_port, accel, sound
        rp = os.path.join(bundle_root(), 'runtime', 'python', 'bin', 'python3')
        # never sys.executable: inside BASILISK XP.app that is the app itself, not Python
        self.relay_python = relay_python or (rp if os.path.isfile(rp) else sys.executable)
        self.proc = None
        self.qmp = None
        self.lock = threading.Lock()
        d = sock_dir()
        tag = '%d' % os.getpid()
        if WIN:
            self.vnc = ('tcp', None)
            self.qmp_path = r'\\.\pipe\basilisk-%s-qmp' % tag
        else:
            self.vnc = ('unix', os.path.join(d, 'vnc-%s' % tag))
            self.qmp_path = os.path.join(d, 'qmp-%s' % tag)

    def args(self, paused):
        a = ['-name', 'BASILISK', '-nodefaults', '-no-user-config', '-M', 'pc-i440fx-6.2', '-m', '512',
             '-smp', os.environ.get('BASILISK_SMP', '2'), '-cpu', 'qemu32',
             '-drive', 'file=%s,format=qcow2,if=ide,index=0,cache=writeback' % self.disk.replace(',', ',,'),
             '-vga', 'cirrus', '-device', 'rtl8139,netdev=n0,mac=52:54:00:12:34:56',
             '-usb', '-device', 'usb-tablet', '-rtc', 'base=localtime',
             '-display', 'none', '-boot', 'menu=off']
        # the same firmware on every OS (taken from the QEMU that made the snapshot): option ROM sizes are
        # part of a snapshot, and newer QEMUs ship bigger ones
        fw = os.path.join(APP, 'firmware')
        if os.path.isdir(fw):
            a += ['-L', fw]
        if self.q.share:
            a += ['-L', self.q.share]
        if WIN:
            # Windows QEMU cannot hand a connection to a helper, so XP keeps QEMU's ordinary NAT here
            # (the server answers 10.0.2.2:8765 = this computer's 127.0.0.1:8765)
            a += ['-netdev', 'user,id=n0,net=10.0.2.0/24']
        else:
            relay = "'%s' '%s' %d" % (self.relay_python, os.path.join(APP, 'relay.py'), self.guest_port)
            a += ['-netdev', 'user,id=n0,restrict=on,net=10.0.2.0/24,host=10.0.2.100,'
                  'guestfwd=tcp:10.0.2.2:8765-cmd:%s' % relay.replace(',', ',,')]
        # no sound card: XP's AC97 driver hangs when resumed from a snapshot
        if self.accel == 'kvm':
            a += ['-accel', 'kvm']
        else:
            a += ['-accel', 'tcg,thread=multi,tb-size=256']
        if self.vnc[0] == 'unix':
            a += ['-vnc', 'unix:%s' % self.vnc[1]]
        else:
            port = next(p for p in range(5990, 6200) if free_port(p) == p)
            self.vnc = ('tcp', port)
            a += ['-vnc', '127.0.0.1:%d' % (port - 5900)]
        if WIN:
            a += ['-chardev', 'pipe,id=qmpc,path=%s' % self.qmp_path[len('\\\\.\\pipe\\'):],
                  '-mon', 'chardev=qmpc,mode=control']
        else:
            a += ['-qmp', 'unix:%s,server=on,wait=off' % self.qmp_path]
        if paused:
            a += ['-S']
        return a

    def start(self, paused=True):
        for p in (self.vnc[1], self.qmp_path):
            if p and not WIN and isinstance(p, str) and os.path.exists(p):
                os.remove(p)
        log = open(self.log_path, 'a', encoding='utf-8', errors='replace')
        cmd = self.q.cmd(*self.args(paused))
        log.write('\n==== %s\n%s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), ' '.join(cmd)))
        log.flush()
        self.proc = subprocess.Popen(cmd, env=self.q.env, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, creationflags=NOWIN)
        self.qmp = Qmp(self.qmp_path, self.proc)

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def hmp(self, line, timeout=120):
        with self.lock:
            r = self.qmp.cmd('human-monitor-command', {'command-line': line}, timeout)
        return r if isinstance(r, str) else ''

    def cmd(self, name, args=None, timeout=30):
        with self.lock:
            return self.qmp.cmd(name, args, timeout)

    def loadvm(self, name):
        """True if the snapshot loaded (an error message from QEMU otherwise)"""
        out = self.hmp('loadvm %s' % name, 300).strip()
        return True if not out else out

    def savevm(self, name):
        self.hmp('delvm %s' % name)
        out = self.hmp('savevm %s' % name, 600).strip()
        return True if not out else out

    def quit(self, wait=15):
        if not self.alive():
            return
        try:
            self.cmd('quit', timeout=5)
        except Exception:
            pass
        try:
            self.proc.wait(wait)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def kill(self):
        if self.alive():
            self.proc.kill()


class QmpError(Exception):
    pass


class Qmp:
    """a QMP client over a unix socket (macOS, Linux) or a named pipe (Windows)"""

    def __init__(self, path, proc):
        self.path, self.proc = path, proc
        self.f = None
        self.buf = b''

    def _open(self, timeout=30):
        end = time.time() + timeout
        while True:
            if self.proc.poll() is not None:
                raise QmpError('QEMU stopped (see qemu.log)')
            try:
                if WIN:
                    self.f = open(self.path, 'r+b', buffering=0)
                    self._w, self._r = self.f.write, lambda: self.f.read(65536)
                else:
                    s = socket.socket(socket.AF_UNIX)
                    s.connect(self.path)
                    self.f = s
                    self._w, self._r = s.sendall, lambda: s.recv(65536)
                break
            except OSError:
                if time.time() > end:
                    raise QmpError('cannot reach QEMU')
                time.sleep(0.05)
        self._line()                                    # greeting
        self._send({'execute': 'qmp_capabilities'})
        self._reply()

    def _line(self):
        while b'\n' not in self.buf:
            b = self._r()
            if not b:
                raise QmpError('QEMU closed its control channel')
            self.buf += b
        line, self.buf = self.buf.split(b'\n', 1)
        return json.loads(line)

    def _send(self, obj):
        self._w(json.dumps(obj).encode() + b'\n')

    def _reply(self):
        while True:
            r = self._line()
            if 'return' in r:
                return r['return']
            if 'error' in r:
                raise QmpError(r['error'].get('desc', 'error'))

    def cmd(self, name, args=None, timeout=30):
        if self.f is None:
            self._open()
        if not WIN:
            self.f.settimeout(timeout)
        m = {'execute': name}
        if args:
            m['arguments'] = args
        self._send(m)
        return self._reply()
