#!/usr/bin/env python3
"""BASILISK 3.11, local edition: Windows for Workgroups 3.11 in its own window, Claude with your own account.

What runs:
  - the engine (DOSBox-X, official build; only its title is changed) boots Windows for Workgroups 3.11 from a folder
    that is its C:. Its two serial ports are null-modem cables to this program over TCP on 127.0.0.1:
      COM1  Windows Terminal  <->  the line editor and transcript (you type into Terminal)
      COM2  B3BOOT.EXE / BASILISK.EXE  <->  the tools (run a DOS command, read and write a file), status, the bill
    D: is a folder on this computer (Documents/BASILISK 3.11), shared both ways.
  - this program: the Claude tool loop (w31_server.py, the same code as williamsharkey.com/basilisk-31.html, with the
    public site's queue, caps and shared key taken out) using YOUR credentials. No window of its own.

First start: Windows builds BASILISK in front of you (Notepad, Save As, Open Watcom) - the intro, about half a minute.
Later starts open straight into the finished program (BASILISK.EXE is Windows' shell); /intro on brings the build back.

Credentials, first that works: a key you gave with /login (read from the clipboard, saved owner-only in the config
folder), then what the Anthropic SDK finds: ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, the `ant auth login` profile.

  basilisk.py [--fresh] [--intro] [--forget-key]
"""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib'))
sys.path.insert(0, HERE)
TOP = os.path.dirname(HERE)
VERSION = open(os.path.join(HERE, 'VERSION')).read().strip() if os.path.exists(os.path.join(HERE, 'VERSION')) else 'dev'
WIN, MAC = sys.platform == 'win32', sys.platform == 'darwin'
DEBUG = bool(os.environ.get('BASILISK_DEBUG'))


def config_dir():
    if os.environ.get('BASILISK311_HOME'):
        return os.environ['BASILISK311_HOME']
    if WIN:
        return os.path.join(os.environ.get('APPDATA') or os.path.expanduser('~'), 'BASILISK311')
    if MAC:
        return os.path.expanduser('~/Library/Application Support/BASILISK311')
    return os.path.join(os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'), 'basilisk311')


def files_dir():
    if os.environ.get('BASILISK311_FILES'):
        return os.environ['BASILISK311_FILES']
    docs = os.path.expanduser('~/Documents')
    return os.path.join(docs if os.path.isdir(docs) else os.path.expanduser('~'), 'BASILISK 3.11')


CONF_DIR = config_dir()
os.makedirs(os.path.join(CONF_DIR, 'data'), exist_ok=True)
CONF = os.path.join(CONF_DIR, 'config.json')
DRIVE = os.path.join(CONF_DIR, 'drive')                 # C:, refreshed each start except C:\B3\WORK and the build
FILES = files_dir()                                     # D:
LOGF = os.path.join(CONF_DIR, 'basilisk.log')
os.environ['W31_ROOT'] = CONF_DIR
_logf = open(LOGF, 'a', encoding='utf-8')
if sys.stdout is None:                                  # pythonw: no console at all
    sys.stdout = sys.stderr = _logf

MODELS = {   # name -> (id, input $/M, output $/M)
    'haiku': ('claude-haiku-5-5', 0.10, 0.50),
    'sonnet': ('claude-sonnet-5-5', 2.00, 10.00),
    'opus': ('claude-opus-5-5', 4.00, 20.00),
    'fable': ('claude-fable-5-2', 8.00, 40.00),
}
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
FALLBACK_MODELS = ('claude-opus-5-5', 'claude-sonnet-5-5', 'claude-fable-5-2')
SIZES = ('auto', '1x', '1.25x', '1.5x', '1.75x', '2x', 'fullscreen')


def log(msg):
    _logf.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg))
    _logf.flush()


def load_conf():
    try:
        with open(CONF) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_conf(c):
    tmp = CONF + '.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)     # owner-only from the start
    with os.fdopen(fd, 'w') as f:
        json.dump(c, f, indent=1)
    os.replace(tmp, CONF)
    try:
        os.chmod(CONF, 0o600)
    except OSError:
        pass


CONFIG = load_conf()
CONFIG.setdefault('model', 'claude-haiku-5-5')
CONFIG.setdefault('effort', 'low')
CONFIG.setdefault('size', 'auto')
CREDS = {'ok': False, 'source': '', 'detail': ''}

import w31_server as S          # noqa: E402  (after W31_ROOT is set)

S.load_env = lambda: None
S._env.clear()
_orig_cfg = S.cfg
OVERRIDE = {'W31_MONTHLY_CAP_USD': '1e12', 'W31_IP_TURNS_HOUR': '1e9', 'W31_IP_USD_DAY': '1e12', 'W31_IP_SESSIONS_HOUR': '1e9'}


def cfg(k):
    if k == 'ANTHROPIC_API_KEY':          # "is there a line to Claude?" - never the key itself
        return '1' if CREDS['ok'] else ''
    if k == 'W31_MODEL':
        return CONFIG['model']
    if k == 'W31_EFFORT':
        return CONFIG['effort']
    return OVERRIDE.get(k) or _orig_cfg(k)


S.cfg = cfg
S.log = log
for _id, _pin, _pout in MODELS.values():
    S.PRICES[_id] = (_pin, _pout)


def extra(model):
    """if a safety classifier declines on these models, the API answers with its default fallback model"""
    if model in FALLBACK_MODELS:
        return {'extra_headers': {'anthropic-beta': 'server-side-fallback-2026-07-01'}, 'extra_body': {'fallbacks': 'default'}}
    return {}


S.EXTRA = extra
_client = {}


def api():
    import anthropic
    key = CONFIG.get('api_key') or ''
    if _client.get('key') != key or 'c' not in _client:
        _client['c'] = (anthropic.AsyncAnthropic(api_key=key, timeout=120.0, max_retries=2) if key else
                        anthropic.AsyncAnthropic(timeout=120.0, max_retries=2))   # env, or `ant auth login`
        _client['key'] = key
    return _client['c']


S.api = api


async def check_creds(key=None):
    """does this credential work? (listing models costs nothing) -> (ok, source, detail)"""
    import anthropic
    try:
        if key:
            c, source = anthropic.AsyncAnthropic(api_key=key, timeout=20.0, max_retries=0), 'your saved key'
        else:
            c = anthropic.AsyncAnthropic(timeout=20.0, max_retries=0)
            source = ('ANTHROPIC_API_KEY' if os.environ.get('ANTHROPIC_API_KEY') else
                      'ANTHROPIC_AUTH_TOKEN' if os.environ.get('ANTHROPIC_AUTH_TOKEN') else 'your ant auth login profile')
        await c.models.list(limit=1)
        return True, source, ''
    except anthropic.AuthenticationError:
        return False, '', 'that key was refused (401)'
    except anthropic.PermissionDeniedError:
        return False, '', 'that key may not use the API (403)'
    except anthropic.APIConnectionError:
        return False, '', 'could not reach api.anthropic.com (are you online?)'
    except Exception as e:        # no credential at all, a half-finished profile, anything else
        if 'auth' in str(e).lower() or 'api_key' in str(e).lower():
            return False, '', 'no API key or sign-in found'
        return False, '', '%s: %s' % (type(e).__name__, str(e)[:160])


def clipboard():
    """the host's clipboard text (for /login), or None"""
    try:
        if WIN:
            import ctypes
            from ctypes import wintypes
            u, k = ctypes.windll.user32, ctypes.windll.kernel32
            u.GetClipboardData.restype = wintypes.HANDLE
            k.GlobalLock.restype = ctypes.c_void_p
            k.GlobalLock.argtypes = [wintypes.HANDLE]
            k.GlobalUnlock.argtypes = [wintypes.HANDLE]
            if not u.OpenClipboard(None):
                return None
            try:
                h = u.GetClipboardData(13)          # CF_UNICODETEXT
                if not h:
                    return None
                p = k.GlobalLock(h)
                try:
                    return ctypes.wstring_at(p)
                finally:
                    k.GlobalUnlock(h)
            finally:
                u.CloseClipboard()
        cmds = [['pbpaste']] if MAC else [['wl-paste', '-n'], ['xclip', '-o', '-selection', 'clipboard'], ['xsel', '-b', '-o']]
        for c in cmds:
            if shutil.which(c[0]):
                r = subprocess.run(c, capture_output=True, timeout=5)
                if r.returncode == 0:
                    return r.stdout.decode('utf-8', 'replace')
    except Exception as e:
        log('clipboard: %r' % e)
    return None


# ------------------------------------------------------------------ the machine, local
class Local:
    ip = 'local'
    rest_until = 0


ME = Local()


class LocalMachine(S.Machine):
    def __init__(self, intro):
        super().__init__()
        self.driver = ME
        # the input line is BASILISK's own edit control now; Terminal only shows the transcript
        self.tui.show_prompt = lambda: None
        self.tui.redraw = lambda: None
        self.tui.hide_prompt = lambda: None
        self.esc = b''
        self.engine = None
        self.intro = intro

    def freeze(self):            # no idle freezing locally: the window is yours
        pass

    def thaw(self):
        pass

    def drop_still(self):
        pass

    # ---- COM1: you type into Terminal; it sends the keys here --------------------
    async def on_com1(self, d):
        if DEBUG:
            log('COM1 rx %r' % d)
        b = self.esc + d
        self.esc = b''
        i = 0
        while i < len(b):
            c = b[i]
            if c == 0x1b:
                rest = b[i + 1:i + 3]
                if rest in (b'[', b'O') and i + 2 == len(b):      # a sequence cut in two: wait for the rest
                    self.esc = b[i:]
                    return
                if rest[:1] in (b'[', b'O') and len(rest) == 2:
                    k = {65: 'ArrowUp', 66: 'ArrowDown', 67: 'ArrowRight', 68: 'ArrowLeft', 72: 'Home', 70: 'End'}.get(rest[1])
                    if k:
                        self.key(ME, k)
                        i += 3
                        continue
                self.key(ME, 'Escape')
                i += 1
                continue
            if c == 0x0d or (c == 0x0a and not (i > 0 and b[i - 1] == 0x0d)):
                self.key(ME, 'Enter')
            elif c in (0x08, 0x7f):
                self.key(ME, 'Backspace')
            elif c == 0x03:
                self.key(ME, 'Escape')
            elif c in (0x01, 0x05, 0x15):
                self.key(ME, {0x01: 'a', 0x05: 'e', 0x15: 'u'}[c], True)
            elif c >= 0x20:
                self.key(ME, bytes([c]).decode('cp1252', 'replace'))
            i += 1

    def key(self, s, k, ctrl=False):
        if self.phase == 'live':
            super().key(s, k, ctrl)

    hist, hi = [], 0

    def line(self, text):
        """a line from BASILISK's input line (Enter)"""
        text = text.strip()
        if DEBUG:
            log('line %r' % text[:80])
        if not text or self.phase != 'live':
            return
        if self.task and not self.task.done():
            self.send2('T', text)                 # one request at a time: give it back to finish later
            return
        if not self.hist or self.hist[-1] != text:
            self.hist.append(text)
        self.hi = len(self.hist)
        self.submit(ME, text)

    # ---- COM2: BASILISK.EXE forwards the keys typed into Terminal's pane ('K') ---------
    kbuf = b''
    KEYNAMES = {'Up': 'ArrowUp', 'Down': 'ArrowDown', 'Left': 'ArrowLeft', 'Right': 'ArrowRight',
                'Home': 'Home', 'End': 'End', 'Del': 'Delete'}

    async def on_com2(self, d):
        buf, rest = self.kbuf + d, b''
        while True:
            i = buf.find(S.EOT)
            if i < 0:
                break
            msg, buf = buf[:i + 1], buf[i + 1:]
            if msg[:1] == b'K':
                self.typed(msg[1:-1].decode('latin-1'))
            elif msg[:1] == b'U':
                self.line(msg[1:-1].decode('cp1252', 'replace'))
            else:
                rest += msg
        self.kbuf = buf
        if rest:
            await super().on_com2(rest)

    def typed(self, k):
        if DEBUG:
            log('key %r' % k)
        if self.phase != 'live':
            return
        if k in ('Up', 'Down'):                  # history for the input line
            h = self.hist
            if h:
                self.hi = max(0, self.hi - 1) if k == 'Up' else min(len(h), self.hi + 1)
                self.send2('T', h[self.hi] if self.hi < len(h) else '')
            return
        if k == 'c27':
            if self.task and not self.task.done():
                self.task.cancel()
            return
        if k in self.KEYNAMES:
            return self.key(ME, self.KEYNAMES[k])
        if not k.startswith('c'):
            return
        c = int(k[1:] or 0)
        if c == 13:
            self.key(ME, 'Enter')
        elif c == 8:
            self.key(ME, 'Backspace')
        elif c in (27, 3):
            self.key(ME, 'Escape')
        elif c in (1, 5, 21):
            self.key(ME, {1: 'a', 5: 'e', 21: 'u'}[c], True)
        elif c >= 32:
            self.key(ME, bytes([c]).decode('cp1252', 'replace'))

    # ---- commands ------------------------------------------------------------------
    def slash(self, text):
        t, B = self.tui, S.BUL + ' '
        parts = text.split()
        cmd, arg = parts[0].lower(), (parts[1].lower() if len(parts) > 1 else '')
        if cmd not in ('/model', '/effort', '/login', '/logout', '/help', '/settings', '/intro', '/size', '/files', '/reset'):
            return super().slash(text)
        t.out('\n')
        if cmd == '/model':
            if arg in MODELS or arg in [v[0] for v in MODELS.values()]:
                setconf(model=MODELS[arg][0] if arg in MODELS else arg)
                t.para('Model is now %s. It counts from your next request.' % CONFIG['model'], B)
                self.status()
            else:
                t.para('Model: %s. Choices, per million tokens in/out: %s. Type /model sonnet, for example.' % (
                    CONFIG['model'], ', '.join('%s $%g/$%g' % (k, v[1], v[2]) for k, v in MODELS.items())), B)
        elif cmd == '/effort':
            if arg in EFFORTS:
                setconf(effort=arg)
                t.para('Effort is now %s. It counts from your next request.' % arg, B)
                self.status()
            else:
                t.para('Effort: %s. Choices: %s. Higher thinks harder and costs more. Type /effort high, for example.' % (
                    CONFIG['effort'], ', '.join(EFFORTS)), B)
        elif cmd == '/login':
            asyncio.get_running_loop().create_task(self.login())
            return
        elif cmd == '/logout':
            CONFIG.pop('api_key', None)
            save_conf(CONFIG)
            CREDS.update(ok=False, source='', detail='signed out')
            asyncio.get_running_loop().create_task(self.login(quiet=True))
            t.para('The saved key is forgotten.', B)
        elif cmd == '/intro':
            if arg in ('on', 'off'):
                setconf(intro=arg == 'on')
                t.para('Next start: %s.' % ('Windows builds BASILISK in front of you (about half a minute)' if arg == 'on'
                                            else 'straight into BASILISK'), B)
            else:
                t.para('Intro is %s. /intro on shows the build (Notepad, Open Watcom) at every start; /intro off opens '
                       'straight into BASILISK.' % ('on' if CONFIG.get('intro') else 'off'), B)
        elif cmd == '/size':
            if arg in SIZES:
                setconf(size=arg)
                t.para('Window size %s from the next start. Alt+Enter switches full screen now.' % arg, B)
            else:
                t.para('Window size: %s. Choices: %s. Alt+Enter switches full screen.' % (CONFIG['size'], ', '.join(SIZES)), B)
        elif cmd == '/files':
            t.para('D: is %s on your computer: anything you or Claude put there is on both sides. C:\\B3\\WORK '
                   'is kept between starts too.' % FILES, B)
        elif cmd == '/reset':
            setconf(reset=True)
            t.para('At the next start C: is fresh again (C:\\B3\\WORK emptied, BASILISK rebuilt). D: is never touched.', B)
        elif cmd == '/settings':
            for line in settings_lines():
                t.para(line, B)
        else:
            t.para('Type a request and press Enter. BASILISK runs DOS commands, reads and writes files, and compiles C '
                   'with Open Watcom. Esc interrupts, Up/Down recall, PgUp/PgDn scroll, Alt+Enter full screen.', B)
            t.para('/model [haiku|sonnet|opus|fable]  /effort [low..max]  /cost  /clear  /login  /logout  /settings  '
                   '/intro [on|off]  /size  /files  /reset', '  ', '  ')

    async def selftest(self, lines):
        for text in lines:
            while self.task and not self.task.done():
                await asyncio.sleep(0.5)
            await asyncio.sleep(1.5)
            log('selftest: %s' % text[:60])
            self.line(text)
            await asyncio.sleep(1.0)
        while self.task and not self.task.done():
            await asyncio.sleep(0.5)
        log('selftest done')

    async def login(self, quiet=False):
        """/login: the key comes from the clipboard (never typed or shown); otherwise ant auth login / env"""
        t, B = self.tui, S.BUL + ' '
        clip = (clipboard() or '').strip()
        key = clip if clip.startswith('sk-ant-') and len(clip) < 400 and ' ' not in clip else ''
        if key:
            ok, source, detail = await check_creds(key)
            if ok:
                CONFIG['api_key'] = key
                save_conf(CONFIG)
                CREDS.update(ok=True, source='your saved key', detail='')
                api()
                self.say('Key accepted and saved on this computer (only your account can read it). You may want to '
                         'clear your clipboard. Ask away.', B)
                return
            self.say('The key on your clipboard did not work: %s.' % detail, B)
            return
        ok, source, detail = await check_creds(None)
        if ok:
            CREDS.update(ok=True, source=source, detail='')
            self.say('Signed in with %s.' % source, B)
        elif not quiet:
            self.say('No key on your clipboard. Copy your Anthropic API key (console.anthropic.com > API keys), then '
                     'type /login again. Or run ant auth login on your computer, then /login.', B)

    def say(self, text, lead=None):
        """a paragraph in the transcript from outside a turn"""
        if self.phase != 'live':
            return
        busy = self.task and not self.task.done()
        t = self.tui
        if not busy:
            t.hide_prompt()
        t.para(text, lead or S.BUL + ' ')
        if not busy:
            t.out('\n')
            t.show_prompt()

    def banner(self):
        super().banner()
        if not CREDS['ok']:
            self.tui.para('Not signed in to Claude yet. Copy your Anthropic API key (console.anthropic.com > API keys), '
                          'then type /login. Every request is billed to your own Anthropic account.', '  ', '  ')
            self.tui.out('\n')

    # ---- start ---------------------------------------------------------------------
    async def run(self, conf_path):
        asyncio.create_task(self.com1.serve())
        asyncio.create_task(self.com2.serve())
        await asyncio.sleep(0.1)
        self.set_phase('booting')
        t0 = time.time()
        self.engine = start_engine(conf_path)
        if not self.intro:
            hide_while_booting(self.engine)        # the intro is the show; a fast start appears when ready
        else:
            reveal_soon(self.engine)
        try:
            await asyncio.wait_for(self.com2.connected.wait(), 60)
            if self.intro:
                await self.wait_event(('H',), 180)                 # B3BOOT
                log('windows up in %.1fs; building' % (time.time() - t0))
                await self.build()
            else:
                await self.wait_event(('H',), 120)                 # BASILISK.EXE itself, as the shell
                await asyncio.wait_for(self.wait_event(('R',), 60), 61)
                self.messages = []
                self.status()
                await asyncio.sleep(0.2)
                self.banner()
                self.tui.show_prompt()
                self.set_phase('live')
            log('ready in %.1fs (%s)' % (time.time() - t0, 'intro' if self.intro else 'fast'))
            reveal(self.engine)
            if os.environ.get('BASILISK_SELFTEST'):         # testing: lines as if typed, one after another
                asyncio.get_running_loop().create_task(self.selftest(os.environ['BASILISK_SELFTEST'].split(';;')))
            if self.intro and os.path.exists(os.path.join(DRIVE, 'B3', 'BASILISK.EXE')):
                keep_build()
                if CONFIG.get('intro') is None:
                    setconf(intro=False)                           # the first start shows the build once
        except Exception as e:
            log('start failed: %r' % e)
            reveal(self.engine)


def settings_lines():
    return ['Model %s, effort %s (/model, /effort).' % (CONFIG['model'], CONFIG['effort']),
            'Signed in: %s (/login, /logout).' % (CREDS['source'] or 'no'),
            'Intro at start: %s (/intro). Window: %s (/size).' % ('on' if CONFIG.get('intro') else 'off', CONFIG['size']),
            'D: = %s. Settings and C: live in %s.' % (FILES, CONF_DIR)]


def setconf(**kw):
    CONFIG.update(kw)
    save_conf(CONFIG)
    log('settings: %r' % {k: v for k, v in kw.items()})


# ------------------------------------------------------------------ C:, D: and the engine
BUILD_KEEP = ('BASILISK.EXE', 'BASILISK.C')


def keep_build():
    os.makedirs(os.path.join(CONF_DIR, 'build'), exist_ok=True)
    for f in BUILD_KEEP:
        p = os.path.join(DRIVE, 'B3', f)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(CONF_DIR, 'build', f))


def refresh_drive(fresh):
    """C: from the shipped copy, then your C:\\B3\\WORK and the BASILISK.EXE Windows built; -> intro needed?"""
    src = os.path.join(TOP, 'drive')
    work = os.path.join(DRIVE, 'B3', 'WORK')
    keep = os.path.join(CONF_DIR, 'work.keep')
    shutil.rmtree(keep, ignore_errors=True)
    if fresh:
        shutil.rmtree(os.path.join(CONF_DIR, 'build'), ignore_errors=True)
    elif os.path.isdir(work):
        shutil.move(work, keep)
    stamp = os.path.join(DRIVE, '.stamp')
    same = (not fresh and os.path.exists(stamp) and os.path.exists(os.path.join(src, '.stamp'))
            and open(stamp).read() == open(os.path.join(src, '.stamp')).read())
    if same:                         # the same C: as last time: put back only what Windows and the build change
        for rel in ('WINDOWS/WIN.INI', 'WINDOWS/SYSTEM.INI', 'WINDOWS/PROGMAN.INI', 'WINDOWS/CONTROL.INI', 'B3'):
            a, b = os.path.join(src, *rel.split('/')), os.path.join(DRIVE, *rel.split('/'))
            if os.path.isdir(a):
                shutil.rmtree(b, ignore_errors=True)
                shutil.copytree(a, b)
            elif os.path.exists(a):
                shutil.copy(a, b)
        shutil.rmtree(os.path.join(DRIVE, 'WINDOWS', 'TEMP'), ignore_errors=True)
        os.makedirs(os.path.join(DRIVE, 'WINDOWS', 'TEMP'), exist_ok=True)
    else:
        shutil.rmtree(DRIVE, ignore_errors=True)
        shutil.copytree(src, DRIVE)
    if os.path.isdir(keep):
        shutil.rmtree(work, ignore_errors=True)
        shutil.move(keep, work)
    os.makedirs(work, exist_ok=True)
    built = all(os.path.exists(os.path.join(CONF_DIR, 'build', f)) for f in BUILD_KEEP)
    intro = not built or bool(CONFIG.get('intro'))
    if built and not intro:
        for f in BUILD_KEEP:
            shutil.copy(os.path.join(CONF_DIR, 'build', f), os.path.join(DRIVE, 'B3', f))
    # fast start: Windows runs the BASILISK.EXE it built last time (it hides Program Manager) - no pour, no compile
    if not intro:
        w = os.path.join(DRIVE, 'WINDOWS', 'WIN.INI')
        s = open(w, 'rb').read()
        assert b'run=C:\\B3\\B3BOOT.EXE' in s
        open(w, 'wb').write(s.replace(b'run=C:\\B3\\B3BOOT.EXE', b'run=C:\\B3\\BASILISK.EXE', 1))
    os.makedirs(FILES, exist_ok=True)
    return intro


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def engine_path():
    if os.environ.get('BASILISK_ENGINE'):
        return os.environ['BASILISK_ENGINE']
    if WIN:
        return os.path.join(TOP, 'engine', 'basilisk-engine.exe')
    if MAC:
        return os.path.join(TOP, 'engine', 'BASILISK 3.11.app', 'Contents', 'MacOS', 'dosbox-x')
    return os.path.join(TOP, 'engine', 'basilisk-engine')


def screen_scale():
    """Windows: a size that fits the screen, in real pixels (the engine is DPI-aware, the shader keeps it sharp)"""
    size = CONFIG.get('size', 'auto')
    if size.endswith('x'):
        return float(size[:-1])
    if not WIN:
        return 1.0
    try:
        import ctypes
        from ctypes import wintypes
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            pass
        r = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)       # SPI_GETWORKAREA
        dpi = ctypes.windll.user32.GetDpiForSystem() if hasattr(ctypes.windll.user32, 'GetDpiForSystem') else 96
        w, h = r.right - r.left, r.bottom - r.top
        s = min(dpi / 96.0, (w * 0.92) / 1024, (h - 60 * dpi / 96.0) / 768)
        return max(1.0, int(s * 4) / 4.0)
    except Exception as e:
        log('screen size: %r' % e)
        return 1.0


def write_conf(p1, p2):
    s = screen_scale()
    full = CONFIG.get('size') == 'fullscreen'
    conf = """[sdl]
fullscreen={full}
fullresolution=desktop
windowresolution={w}x{h}
windowposition=-
output=texture
autolock=false
autolock_feedback=none
mouse_emulation=always
showmenu=false
showbasic=false
showdetails=false
titlebar=
[dosbox]
title=BASILISK 3.11
machine=svga_s3
memsize=64
quit warning=false
startbanner=false
fastbioslogo=true
disable graphical splash=true
dpi aware=true
captures={cap}
[cpu]
cputype=pentium
core=normal
cycles=max
[render]
scaler=none
aspect=false
[mixer]
nosound=true
[speaker]
pcspeaker=false
[serial]
serial1=nullmodem server:127.0.0.1 port:{p1} transparent:1
serial2=nullmodem server:127.0.0.1 port:{p2} transparent:1
[autoexec]
@mount c "{drive}" -q
@mount d "{files}" -nocachedir -q
@c:
@SET TEMP=C:\\WINDOWS\\TEMP
@SET PATH=C:\\WINDOWS;C:\\WATCOM\\BINW
@SET WATCOM=C:\\WATCOM
@SET INCLUDE=C:\\WATCOM\\H;C:\\WATCOM\\H\\WIN
@cd \\WINDOWS
@WIN :
@exit
""".format(full='true' if full else 'false', w=int(1024 * s), h=int(768 * s), p1=p1, p2=p2, drive=DRIVE, files=FILES,
           cap=os.path.join(CONF_DIR, 'captures'))
    path = os.path.join(CONF_DIR, 'engine.conf')
    with open(path, 'w') as f:
        f.write(conf)
    return path


def start_engine(conf_path):
    env = dict(os.environ)
    if sys.platform.startswith('linux'):
        env['LD_LIBRARY_PATH'] = os.path.join(TOP, 'engine', 'lib') + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
        env.setdefault('SDL_VIDEO_X11_WMCLASS', 'basilisk-3.11')
    kw = {}
    if WIN:
        kw['creationflags'] = 0x08000000            # CREATE_NO_WINDOW: no console behind it
    return subprocess.Popen([engine_path(), '-conf', conf_path, '-nopromptfolder', '-nolog'], env=env, cwd=CONF_DIR,
                            stdin=subprocess.DEVNULL, stdout=open(os.path.join(CONF_DIR, 'engine.log'), 'w'),
                            stderr=subprocess.STDOUT, **kw)


def windows_of(pid):
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(h, _):
        p = wintypes.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u.IsWindowVisible(h) or (p.value == pid and u.GetWindowTextLengthW(h) > 0):
            found.append(h)
        return True
    u.EnumWindows(cb, 0)
    return found


def hide_while_booting(proc):
    """Windows: as soon as the engine's window exists, make it invisible (it stays on the taskbar with our icon)
    until BASILISK is assembled; reveal() brings it in"""
    if not WIN:
        return
    import ctypes
    import threading
    u = ctypes.windll.user32

    def watch():
        end = time.time() + 20
        while time.time() < end and proc.poll() is None:
            hs = windows_of(proc.pid)
            if hs:
                for h in hs:
                    u.SetWindowLongW(h, -20, u.GetWindowLongW(h, -20) | 0x80000)      # WS_EX_LAYERED
                    u.SetLayeredWindowAttributes(h, 0, 0, 2)                           # LWA_ALPHA, fully clear
                    set_icon(h)
                return
            time.sleep(0.01)
    threading.Thread(target=watch, daemon=True).start()


def reveal_soon(proc):
    """Windows: our icon on the intro's window as soon as it exists"""
    if not WIN:
        return
    import threading

    def watch():
        end = time.time() + 20
        while time.time() < end and proc.poll() is None:
            hs = windows_of(proc.pid)
            if hs:
                for h in hs:
                    set_icon(h)
                return
            time.sleep(0.02)
    threading.Thread(target=watch, daemon=True).start()


def set_icon(h):
    import ctypes
    u = ctypes.windll.user32
    ico = os.path.join(HERE, 'basilisk.ico')
    big = u.LoadImageW(None, ico, 1, 0, 0, 0x10 | 0x40)          # IMAGE_ICON, LR_LOADFROMFILE|LR_DEFAULTSIZE
    small = u.LoadImageW(None, ico, 1, 16, 16, 0x10)
    if big:
        u.SendMessageW(h, 0x80, 1, big)                         # WM_SETICON ICON_BIG
    if small:
        u.SendMessageW(h, 0x80, 0, small)


def reveal(proc):
    """Windows: the window was parked off-screen while Windows booted; give it our icon and bring it in, centred"""
    if not WIN or not proc:
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        for h in windows_of(proc.pid):
            set_icon(h)
            if u.GetWindowLongW(h, -20) & 0x80000:
                u.SetLayeredWindowAttributes(h, 0, 255, 2)
                u.SetWindowLongW(h, -20, u.GetWindowLongW(h, -20) & ~0x80000)
            if CONFIG.get('size') == 'fullscreen':
                continue
            r = (ctypes.c_long * 4)()
            u.GetWindowRect(h, r)
            w, hgt = r[2] - r[0], r[3] - r[1]
            wa = (ctypes.c_long * 4)()
            u.SystemParametersInfoW(0x30, 0, wa, 0)
            x = wa[0] + max(0, (wa[2] - wa[0] - w) // 2)
            y = wa[1] + max(0, (wa[3] - wa[1] - hgt) // 2)
            u.SetWindowPos(h, 0, x, y, 0, 0, 0x0001 | 0x0004 | 0x0040)   # NOSIZE|NOZORDER|SHOWWINDOW
            u.SetForegroundWindow(h)
    except Exception as e:
        log('reveal: %r' % e)


def single_instance():
    """one BASILISK at a time: a second start just brings the first one forward"""
    s = socket.socket()
    try:
        s.bind(('127.0.0.1', 47311))
        s.listen(4)
        return s
    except OSError:
        try:
            socket.create_connection(('127.0.0.1', 47311), timeout=2).close()
        except OSError:
            pass
        return None


def start_menu_shortcut():
    """Windows: a Start menu entry the first time BASILISK runs from its folder"""
    if not WIN or CONFIG.get('shortcut'):
        return
    exe = os.path.join(TOP, 'BASILISK 3.11.exe')
    if not os.path.exists(exe):
        return
    lnk = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'BASILISK 3.11.lnk')
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');$s.TargetPath='%s';$s.WorkingDirectory='%s';"
          "$s.IconLocation='%s,0';$s.Description='Claude Code on Windows for Workgroups 3.11';$s.Save()") % (
        lnk.replace("'", "''"), exe.replace("'", "''"), TOP.replace("'", "''"), exe.replace("'", "''"))
    try:
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps], timeout=30,
                       creationflags=0x08000000, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        setconf(shortcut=lnk)
    except Exception as e:
        log('shortcut: %r' % e)


async def main():
    args = sys.argv[1:]
    lock = single_instance()
    if not lock:
        log('already running')
        return
    if '--forget-key' in args:
        CONFIG.pop('api_key', None)
        save_conf(CONFIG)
    log('start %s on %s' % (VERSION, sys.platform))
    fresh = '--fresh' in args or CONFIG.pop('reset', False)
    if fresh:
        save_conf(CONFIG)
    t0 = time.time()
    intro = refresh_drive(fresh) or '--intro' in args
    log('C: ready in %.2fs (%s)' % (time.time() - t0, 'intro' if intro else 'fast'))
    m = LocalMachine(intro)
    m.com1.port, m.com2.port = free_port(), free_port()
    conf_path = write_conf(m.com1.port, m.com2.port)

    async def creds():
        await asyncio.sleep(0.5)          # let the engine start first
        ok, source, detail = await check_creds(CONFIG.get('api_key') or None)
        CREDS.update(ok=ok, source=source if ok else '', detail=detail)
        log('credentials: %s' % (source if ok else detail))
    ct = asyncio.create_task(creds())
    loop = asyncio.get_running_loop()

    async def poke():           # a second start: bring the window forward
        while True:
            c, _ = await loop.sock_accept(lock)
            c.close()
            reveal(m.engine)
    lock.setblocking(False)
    asyncio.create_task(poke())
    asyncio.create_task(m.run(conf_path))
    loop.run_in_executor(None, start_menu_shortcut)
    await ct
    while True:                      # the window closed = BASILISK is over
        await asyncio.sleep(0.3)
        if m.engine and m.engine.poll() is not None:
            break
    log('exit; session %s in, %s out, $%.5f' % (m.usage['in'], m.usage['out'], m.usage['usd']))
    _logf.flush()
    os._exit(0)                      # nothing else to wind down; don't wait on sockets


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    os._exit(0)
