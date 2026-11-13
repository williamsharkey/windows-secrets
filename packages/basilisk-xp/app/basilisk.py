"""BASILISK - Claude Code in Windows XP, as one program on your computer.

The window is ours: XP's screen arrives over a private local VNC socket from a QEMU that never shows itself,
keys go in as PC scancodes, the pointer as an absolute tablet. The host side of the client (the Claude tool
loop) runs in this same process. XP comes up from a snapshot taken after BASILISK built itself, so it is
ready in a second or two; the build is still there to watch ("Intro" in settings).
"""
import hashlib
import json
import lzma
import os
import ssl
import subprocess
import sys
import threading
import time
import traceback
import urllib.request

APP = os.path.dirname(os.path.abspath(__file__))
WIN = os.name == 'nt'
MAC = sys.platform == 'darwin'
VERSION = '1.0'

MACHINE_NAME = 'basilisk-xp-machine-1.qcow2.xz'
MACHINE_URL = 'https://github.com/williamsharkey/windows-secrets/releases/download/basilisk-xp-v1.0.0/' + MACHINE_NAME
MACHINE_SHA256 = ''          # filled in by tools/build_bundles.py
MACHINE_XZ_SIZE = 0
MACHINE_SIZE = 0


# ----------------------------------------------------------------------------------------------- places

def places():
    home = os.path.expanduser('~')
    if WIN:
        cfg = os.path.join(os.environ.get('APPDATA') or home, 'BASILISK XP')
        data = os.path.join(os.environ.get('LOCALAPPDATA') or home, 'BASILISK XP')
    elif MAC:
        cfg = data = os.path.join(home, 'Library', 'Application Support', 'BASILISK XP')
    else:
        cfg = os.path.join(os.environ.get('XDG_CONFIG_HOME') or os.path.join(home, '.config'), 'basilisk-xp')
        data = os.path.join(os.environ.get('XDG_DATA_HOME') or os.path.join(home, '.local', 'share'), 'basilisk-xp')
    cfg = os.environ.get('BASILISK_CONFIG_DIR') or cfg
    data = os.environ.get('BASILISK_DATA_DIR') or data
    for d in (cfg, data, os.path.join(data, 'logs')):
        os.makedirs(d, exist_ok=True)
    if not WIN:
        os.chmod(cfg, 0o700)
    return cfg, data


CONFIG, DATA = places()
LOGS = os.path.join(DATA, 'logs')
MACHINE = os.path.join(DATA, 'machine.qcow2')
SESSION = os.path.join(DATA, 'session.json')
PREFS_FILE = os.path.join(CONFIG, 'app.json')
DEFAULT_PREFS = {'intro': False, 'scale': 'fit', 'on_quit': 'ask', 'fullscreen': False,
                 'session': False, 'size': None}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


class Prefs(dict):
    def __init__(self):
        super().__init__(DEFAULT_PREFS)
        try:
            with open(PREFS_FILE) as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass

    def set(self, **kv):
        self.update(kv)
        tmp = PREFS_FILE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(dict(self), f, indent=1)
        os.replace(tmp, PREFS_FILE)


def single_instance():
    """True if no other BASILISK runs (the lock is held for the life of the process)"""
    global _lockf
    _lockf = open(os.path.join(DATA, 'running.lock'), 'a+')
    try:
        if WIN:
            import msvcrt
            msvcrt.locking(_lockf.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_lockf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


# ----------------------------------------------------------------------------------------------- setup

def setup_env():
    import machine
    if WIN:
        port = 8765          # NAT on Windows: XP's 10.0.2.2:8765 is this computer's 127.0.0.1:8765
        if machine.free_port(port) is None:
            raise RuntimeError('Another program on this computer is using port 8765, which BASILISK needs. '
                               'Close it (or another BASILISK) and start again.')
    else:
        port = machine.free_port(8765) or machine.free_port(0)
    os.environ.update({'TERM_ROOT': DATA, 'BASILISK_CONFIG': CONFIG, 'TERM_GUEST_PORT': str(port)})
    return port


def find_local_xz():
    """a machine image shipped next to the app (offline installs, tests)"""
    import machine
    d = os.path.join(machine.bundle_root(), 'disk')
    for n in (MACHINE_NAME,):
        p = os.path.join(d, n)
        if os.path.isfile(p):
            return p
    return None


class Boot:
    """everything between double-click and a ready BASILISK, in a thread; the window shows its progress"""

    def __init__(self, app):
        self.app = app
        self.text, self.sub, self.frac = 'Starting', '', None
        self.error = None
        self.m = None
        self.intro = False
        self.speed_note = ''

    def say(self, text, sub='', frac=None):
        self.text, self.sub, self.frac = text, sub, frac
        self.app.wake()

    def run(self):
        try:
            self._run()
        except Exception as e:
            traceback.print_exc()
            self.error = str(e) or type(e).__name__
            self.app.wake()

    def _run(self):
        import machine
        app = self.app
        if app.guest_port is None:
            app.guest_port = setup_env()
        if not os.path.exists(MACHINE):
            self.fetch()
        # the server (and its imports) come up while QEMU loads the machine
        server = threading.Thread(target=app.start_server, daemon=True)
        server.start()
        q = machine.Qemu()
        # the machine always holds 'ready'; 'session' when the person kept it (asking qemu-img costs seconds)
        target = 'session' if app.prefs['session'] and os.path.exists(SESSION) else 'ready'
        intro = app.prefs['intro'] or app.prefs.get('ready_broken')
        state = None
        if target == 'session':
            try:
                with open(SESSION) as f:
                    state = json.load(f)
            except (OSError, ValueError):
                state = None
        # KVM where there is one, except to resume the shipped snapshot: it was taken under TCG, and a TCG
        # snapshot does not run under KVM. A machine saved here resumes under whatever saved it.
        kvm = machine.kvm_ok() and not app.prefs.get('kvm_bad')
        if intro:
            accel = 'kvm' if kvm else 'tcg'
        elif target == 'session':
            accel = app.prefs.get('session_accel') or 'tcg'
            accel = accel if accel != 'kvm' or kvm else 'tcg'
        else:
            accel = 'tcg'
        app.accel = accel
        while True:
            self.say('Starting Windows XP', 'Building BASILISK in front of you' if intro else '')
            m = machine.Machine(q, MACHINE, os.path.join(LOGS, 'qemu.log'), app.guest_port, accel=accel,
)
            m.start(paused=True)
            if intro:
                break
            t0 = time.time()
            r = m.loadvm(target)
            log('loadvm %s (%s): %s in %.1fs' % (target, accel, r, time.time() - t0))
            if r is True:
                break
            m.quit()
            if target == 'session':
                target, state = 'ready', None
                continue
            app.prefs.set(ready_broken=True)
            intro = True
        self.m, self.intro = m, intro
        if accel == 'kvm':
            self.speed_note = 'Running with hardware acceleration (KVM).'
        elif kvm:
            self.speed_note = ('Resumed from a snapshot, so XP is emulated (TCG) this time. Keep the machine when '
                               'you quit and it will resume with KVM next time.')
        else:
            self.speed_note = ('This computer cannot run an x86 guest with hardware acceleration, so XP is emulated '
                               '(TCG): quick enough for BASILISK, a little slower than a real PC.')
        server.join()
        import server_local as S
        if not intro:
            S.call(S.restored(state))
            if target == 'session':
                app.prefs.set(session=False)       # a saved machine is used once; quitting saves it again
        m.cmd('cont')
        self.say('Connecting the screen')
        app.connect_screen(m)
        app.ready(m, intro)

    def fetch(self):
        """first run: the machine image, downloaded once, unpacked once"""
        xz = find_local_xz()
        tmp = os.path.join(DATA, MACHINE_NAME + '.part')
        if not xz:
            xz = os.path.join(DATA, MACHINE_NAME)
            if not os.path.exists(xz):
                self.download(tmp)
                os.replace(tmp, xz)
        self.say('Unpacking Windows XP', 'Once only', 0.0)
        out = MACHINE + '.part'
        d = lzma.LZMADecompressor()
        total = os.path.getsize(xz)
        done = 0
        t0 = time.time()
        with open(xz, 'rb') as f, open(out, 'wb') as o:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                done += len(b)
                o.write(d.decompress(b))
                self.say('Unpacking Windows XP', 'Once only', done / total)
        os.replace(out, MACHINE)
        log('unpacked in %.0fs' % (time.time() - t0))
        if xz.startswith(DATA):
            os.remove(xz)

    def download(self, tmp):
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        h = hashlib.sha256()
        got = 0
        t0 = time.time()
        self.say('Downloading Windows XP', 'Once only: %d MB' % (MACHINE_XZ_SIZE >> 20), 0.0)
        req = urllib.request.Request(MACHINE_URL, headers={'User-Agent': 'BASILISK/' + VERSION})
        with urllib.request.urlopen(req, context=ctx, timeout=60) as r, open(tmp, 'wb') as f:
            total = int(r.headers.get('Content-Length') or MACHINE_XZ_SIZE or 1)
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
                h.update(b)
                got += len(b)
                rate = got / max(0.1, time.time() - t0)
                self.say('Downloading Windows XP', '%d of %d MB  ·  %.1f MB/s  ·  once only' % (
                    got >> 20, total >> 20, rate / 2 ** 20), got / total)
        if MACHINE_SHA256 and h.hexdigest() != MACHINE_SHA256:
            os.remove(tmp)
            raise RuntimeError('The download was damaged on the way (checksum mismatch). Start BASILISK again '
                               'to retry.')
        log('downloaded %d bytes in %.0fs' % (got, time.time() - t0))


def start_menu_shortcut():
    """Windows: a Start menu entry for this copy of BASILISK.exe (made once; delete it like any shortcut)"""
    import machine
    exe = os.path.join(machine.bundle_root(), 'BASILISK XP.exe')
    lnk = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'BASILISK XP.lnk')
    if not WIN or not os.path.isfile(exe) or os.path.exists(lnk):
        return
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s'); $s.TargetPath='%s'; "
          "$s.WorkingDirectory='%s'; $s.IconLocation='%s,0'; $s.Description='Claude Code in Windows XP'; $s.Save()"
          % (lnk.replace("'", "''"), exe.replace("'", "''"), os.path.dirname(exe).replace("'", "''"),
             exe.replace("'", "''")))
    try:
        subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], timeout=30,
                       creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True)
        log('Start menu shortcut:', os.path.exists(lnk))
    except (OSError, subprocess.TimeoutExpired) as e:
        log('Start menu shortcut failed: %r' % e)


# ----------------------------------------------------------------------------------------------- the app

def main():
    sys.path.insert(0, APP)
    logf = open(os.path.join(LOGS, 'basilisk.log'), 'a', encoding='utf-8', errors='replace', buffering=1)
    if not (sys.stdout and sys.stdout.isatty()):
        sys.stdout = sys.stderr = logf
    log('==== BASILISK XP %s on %s (%s)' % (VERSION, sys.platform, os.environ.get('BASILISK_BUNDLE', APP)))
    if not single_instance():
        log('another BASILISK is running')
        return
    threading.Thread(target=start_menu_shortcut, daemon=True).start()
    import ui
    ui.App(Boot, sys.modules[__name__]).run()


if __name__ == '__main__':
    main()
