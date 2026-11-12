#!/usr/bin/env python3
"""BASILISK 3.11 - Claude Code on Windows for Workgroups 3.11, assembled from Terminal, Clock and Cardfile.

The machine: DOSBox-X (snap) running WfW 3.11 on a private Xvfb :31, its C: drive a directory that is
restored from a golden copy before every session.  Two null-modem serial lines come back here over TCP:
  COM1 (127.0.0.1:8772)  Windows Terminal  <->  this server's terminal UI (line editor, transcript, the agent)
  COM2 (127.0.0.1:8792)  B3BOOT.EXE / BASILISK.EXE  <->  tools (run a DOS command, read/write a file), scroll, status
Visitors watch through x11vnc (view-only) proxied at /vnc with every client input message dropped; the driver's
keystrokes arrive on /ws and go straight into the terminal UI (the remote echo comes back through Terminal).
Public side 127.0.0.1:8782 (Caddy: live.williamsharkey.com/w31/*).  Never prints the API key.
"""
import asyncio
import json
import os
import re
import secrets
import signal
import struct
import subprocess
import time
from collections import deque

from aiohttp import web, WSMsgType

ROOT = '/root/w31'
DATA = os.path.join(ROOT, 'data')
SNAPC = '/root/snap/dosbox-x/common/w31'
RUN = os.path.join(SNAPC, 'run')
GOLDEN = os.path.join(ROOT, 'golden')
DBX = os.path.join(ROOT, 'dbx.sh')
os.makedirs(DATA, exist_ok=True)

DEFAULTS = {
    'W31_MODEL': 'claude-haiku-5-5',
    'W31_EFFORT': 'low',
    'W31_MONTHLY_CAP_USD': '10',
    'W31_COM1': '8772', 'W31_COM2': '8792', 'W31_PUBLIC': '8782', 'W31_VNC': '5931',
    'W31_TRUSTED_PROXY': '127.0.0.1',
    'W31_ORIGINS': 'https://williamsharkey.com,https://www.williamsharkey.com,https://live.williamsharkey.com,'
                   'http://localhost:8000,http://127.0.0.1:8000',
    'W31_LEASE': '600',          # seconds a driver keeps the machine when someone is waiting
    'W31_IDLE': '180',           # no keys and no work for this long ends a session
    'W31_IP_SESSIONS_HOUR': '4',
    'W31_IP_TURNS_HOUR': '60',
    'W31_IP_USD_DAY': '1.00',
    'W31_QUEUE_MAX': '20',
    'W31_ONE_PER_IP': '1',       # one place (driving or in line) per address
}
PRICES = {'claude-haiku-5-5': (0.10, 0.50), 'claude-sonnet-5-5': (2.00, 10.00)}
_env = {}


def load_env():
    env = {}
    for path in ('/root/stage/.env', os.path.join(ROOT, '.env')):   # the key lives in the stage's .env
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env[k.strip()] = v.strip().strip('"').strip("'")
        except OSError:
            pass
    _env.clear()
    _env.update(env)


def cfg(k):
    return _env.get(k) or os.environ.get(k) or DEFAULTS.get(k, '')


def cfgf(k):
    try:
        return float(cfg(k))
    except ValueError:
        return float(DEFAULTS[k])


load_env()


def log(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


# --------------------------------------------------------------------------- budget and limits

class Budget:
    path = os.path.join(DATA, 'spend.json')

    def __init__(self):
        try:
            with open(self.path) as f:
                self.d = json.load(f)
        except (OSError, ValueError):
            self.d = {}

    def month(self):
        return time.strftime('%Y-%m', time.gmtime())

    def spent(self):
        return self.d.get(self.month(), {}).get('usd', 0.0)

    def over(self):
        return self.spent() >= cfgf('W31_MONTHLY_CAP_USD')

    def add(self, model, usage):
        pin, pout = PRICES.get(model, PRICES['claude-sonnet-5-5'])
        inp = getattr(usage, 'input_tokens', 0) or 0
        cw = getattr(usage, 'cache_creation_input_tokens', 0) or 0
        cr = getattr(usage, 'cache_read_input_tokens', 0) or 0
        out = getattr(usage, 'output_tokens', 0) or 0
        usd = (inp * pin + cw * pin * 1.25 + cr * pin * 0.1 + out * pout) / 1e6
        m = self.d.setdefault(self.month(), {'usd': 0.0, 'calls': 0, 'in': 0, 'out': 0, 'cache_read': 0})
        m['usd'] = round(m['usd'] + usd, 6)
        m['calls'] += 1
        m['in'] += inp + cw
        m['out'] += out
        m['cache_read'] += cr
        tmp = self.path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.d, f, indent=1)
        os.replace(tmp, self.path)
        return usd, inp + cw + cr, out


BUDGET = Budget()


class Limits:
    def __init__(self):
        self.sessions, self.turns, self.usd = {}, {}, {}

    @staticmethod
    def _trim(dq, horizon):
        now = time.time()
        while dq and dq[0][0] < now - horizon:
            dq.popleft()
        return dq

    def session_ok(self, ip):
        dq = self._trim(self.sessions.setdefault(ip, deque()), 3600)
        if len(dq) >= cfgf('W31_IP_SESSIONS_HOUR'):
            return dq[0][0] + 3600
        return 0

    def session_note(self, ip):
        self.sessions.setdefault(ip, deque()).append((time.time(), 1))

    def turn_ok(self, ip):
        """-> 0 if fine, else epoch when they may type again"""
        dq = self._trim(self.turns.setdefault(ip, deque()), 3600)
        if len(dq) >= cfgf('W31_IP_TURNS_HOUR'):
            return dq[0][0] + 3600
        du = self._trim(self.usd.setdefault(ip, deque()), 86400)
        if sum(x for _, x in du) >= cfgf('W31_IP_USD_DAY'):
            return du[0][0] + 86400
        return 0

    def turn_note(self, ip):
        self.turns.setdefault(ip, deque()).append((time.time(), 1))

    def usd_note(self, ip, usd):
        self.usd.setdefault(ip, deque()).append((time.time(), usd))


LIMITS = Limits()

# --------------------------------------------------------------------------- serial lines

EOT = b'\x04'


class Line:
    """one DOSBox-X null-modem port; DOSBox connects to us once, at its start"""

    def __init__(self, name, port, on_data):
        self.name, self.port, self.on_data = name, port, on_data
        self.w = None
        self.connected = asyncio.Event()
        self.q = asyncio.Queue()
        self.cps = 1800          # 19200 baud: pace writes so the UART never overruns

    async def serve(self):
        srv = await asyncio.start_server(self._conn, '127.0.0.1', self.port)
        asyncio.create_task(self._writer())
        await srv.serve_forever()

    async def _conn(self, r, w):
        if self.w:
            try:
                self.w.close()
            except Exception:
                pass
        self.w = w
        self.connected.set()
        log('%s connected' % self.name)
        try:
            while True:
                d = await r.read(4096)
                if not d:
                    break
                await self.on_data(d)
        except (ConnectionError, OSError):
            pass
        finally:
            if self.w is w:
                self.w = None
                self.connected.clear()
                while not self.q.empty():
                    self.q.get_nowait()
            log('%s closed' % self.name)

    def send(self, b):
        if self.w and b:
            self.q.put_nowait(b)

    def flush_pending(self):
        while not self.q.empty():
            self.q.get_nowait()

    async def _writer(self):
        while True:
            b = await self.q.get()
            # merge whatever else is queued, then pace by the line rate
            while not self.q.empty() and len(b) < 512:
                b += self.q.get_nowait()
            w = self.w
            if not w:
                continue
            i = 0
            while i < len(b):
                part = b[i:i + 64]
                i += len(part)
                try:
                    w.write(part)
                    await w.drain()
                except (ConnectionError, OSError):
                    break
                await asyncio.sleep(len(part) / self.cps)


def cp(s):
    """text for a 1993 ANSI terminal font"""
    s = s.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    s = s.replace('\u2014', '--').replace('\u2013', '-').replace('\u2026', '...').replace('\u2022', '\x95')
    s = s.replace('\u2192', '->').replace('\u2190', '<-').replace('\t', '    ')
    return s.encode('cp1252', 'replace')


# --------------------------------------------------------------------------- terminal UI on COM1

W = 80
BUL = '*'             # Fixedsys in Terminal has no bullet (0x95 shows as '?')


class Tui:
    def __init__(self, m):
        self.m = m
        self.buf, self.cur = [], 0
        self.hist, self.hi = [], 0
        self.col = 0
        self.prompt_on = False
        self.view = 0                  # first char of the input shown (long lines scroll)

    def out(self, s):
        self.m.com1.send(cp(s.replace('\r\n', '\n').replace('\n', '\r\n')))

    # ---- transcript text -------------------------------------------------
    def nl(self):
        self.out('\n')
        self.col = 0

    def para(self, text, first='', rest='  '):
        """word-wrapped paragraph(s) with a first-line marker and a hanging indent"""
        for li, line in enumerate(text.split('\n')):
            lead = first if li == 0 else rest
            self.wrap_line(line, lead, rest)

    def wrap_line(self, line, lead, rest):
        width = W - 1
        cur = lead
        words = re.split(r'(\s+)', line)
        for wd in words:
            if not wd:
                continue
            if len(cur) + len(wd) > width and cur.strip():
                self.out(cur.rstrip() + '\n')
                cur = rest + (wd.lstrip() if wd.isspace() is False else '')
                if wd.isspace():
                    cur = rest
                continue
            while len(rest) + len(wd) > width:      # a very long word: hard split
                room = width - len(cur)
                self.out(cur + wd[:room] + '\n')
                wd = wd[room:]
                cur = rest
            cur += wd
        self.out(cur.rstrip() + '\n')

    # ---- streaming assistant text ----------------------------------------
    def stream_start(self):
        self.sline = BUL + ' '
        self.sword = ''
        self.out(self.sline)
        self.scol = len(self.sline)
        self.sbuf = ''

    def stream(self, t):
        for ch in t:
            if ch == '\n':
                self.out('\n  ')
                self.scol = 2
                continue
            if self.scol >= W - 1:
                if ch == ' ':
                    self.out('\n  ')
                    self.scol = 2
                    continue
                # move the partial word down with us
                tail = self.sbuf.split(' ')[-1] if ' ' in self.sbuf else ''
                if tail and len(tail) < 30:
                    self.out('\b' * len(tail) + '\x1b[K' + '\n  ' + tail)
                    self.scol = 2 + len(tail)
                else:
                    self.out('\n  ')
                    self.scol = 2
            self.out(ch)
            self.sbuf = (self.sbuf + ch)[-80:]
            self.scol += 1

    def stream_end(self):
        self.out('\n')

    # ---- the prompt / line editor -----------------------------------------
    def show_prompt(self):
        self.prompt_on = True
        self.redraw()

    def hide_prompt(self):
        if self.prompt_on:
            self.out('\r\x1b[K')
        self.prompt_on = False

    def redraw(self):
        if not self.prompt_on:
            return
        room = W - 4
        if self.cur < self.view:
            self.view = self.cur
        if self.cur > self.view + room:
            self.view = self.cur - room
        if len(self.buf) <= room:
            self.view = 0
        shown = ''.join(self.buf[self.view:self.view + room])
        back = len(shown) - (self.cur - self.view)
        self.out('\r\x1b[K> ' + shown + ('\x1b[%dD' % back if back > 0 else ''))

    def key(self, k, ctrl=False):
        b, c = self.buf, self.cur
        simple_end = c == len(b) and len(b) < W - 5
        if len(k) == 1 and not ctrl:
            b.insert(c, k)
            self.cur += 1
            if simple_end and self.prompt_on:
                self.out(k)
            else:
                self.redraw()
            return None
        if ctrl and k.lower() == 'u':
            del b[:c]
            self.cur = 0
        elif ctrl and k.lower() == 'a':
            self.cur = 0
        elif ctrl and k.lower() == 'e':
            self.cur = len(b)
        elif k == 'Backspace':
            if c > 0:
                del b[c - 1]
                self.cur -= 1
                if simple_end and self.prompt_on:
                    self.out('\b \b')
                    return None
        elif k == 'Delete':
            if c < len(b):
                del b[c]
        elif k == 'ArrowLeft':
            self.cur = max(0, c - 1)
        elif k == 'ArrowRight':
            self.cur = min(len(b), c + 1)
        elif k == 'Home':
            self.cur = 0
        elif k == 'End':
            self.cur = len(b)
        elif k in ('ArrowUp', 'ArrowDown'):
            if not self.hist:
                return None
            self.hi = max(0, self.hi - 1) if k == 'ArrowUp' else min(len(self.hist), self.hi + 1)
            self.buf = list(self.hist[self.hi]) if self.hi < len(self.hist) else []
            self.cur = len(self.buf)
        elif k == 'Enter':
            text = ''.join(b).strip()
            self.buf, self.cur, self.view = [], 0, 0
            if text:
                if not self.hist or self.hist[-1] != text:
                    self.hist.append(text)
                self.hi = len(self.hist)
            return text
        else:
            return None
        self.redraw()
        return None

    def paste(self, text):
        text = re.sub(r'[\r\n\t]+', ' ', text)[:2000]
        for ch in text:
            if ' ' <= ch:
                self.buf.insert(self.cur, ch)
                self.cur += 1
        self.redraw()


# --------------------------------------------------------------------------- the agent

SYSTEM = """You are BASILISK 3.11: Claude, working as a coding agent (like Claude Code) on a real Windows for \
Workgroups 3.11 machine running on MS-DOS (an emulated 486, 64 MB, no network, no internet). The person types to \
you through Windows Terminal (80 columns, Fixedsys, VT-100) over a null-modem cable. BASILISK.EXE, a 16-bit \
program compiled on this machine a minute ago from a Notepad file, runs your tools.

The machine:
- Drive C: is the only drive. Your working directory is C:\\B3\\WORK (put new files there). DOS 8.3 file names only.
- run_command runs one line through COMMAND.COM in a background DOS window with stdout captured (stderr is not; \
DOS can't redirect it). Things like DIR, TYPE, TREE, FIND, MEM, VER, SET, COPY, MD, DEL, REN, ECHO, and .BAT files \
work. One command per call: this COMMAND.COM has no &, && or ;, so run steps as separate calls, and each call starts again in C:\\B3\\WORK (a CD does not carry over; use paths instead). There is no MOVE: use COPY then DEL. wcl writes its .EXE to C:\\B3\\WORK unless you add -fe=DIR\\NAME.EXE. Never run interactive or full-screen programs (EDIT, QBASIC, MORE without input), they would hang until the 60 s \
timeout. Windows programs can't be started from run_command.
- Open Watcom C is installed: compile DOS programs with   wcl -q -bt=dos -ms PROG.C   and Windows 3.1 programs with \
  wcl -q -bt=windows -l=windows -ml PROG.C   (WATCOM, PATH and INCLUDE are set). DOS .EXE output can be run and its \
output captured; a Windows .EXE can be built but not launched by you.
- The machine is reset for every visitor, so nothing you do persists.

How to answer: this is a terminal, so plain text only. No markdown: no headings, no bold or italics, no tables, no \
code fences (show code by writing it to a file, then mention the file). Short paragraphs, lines that read well at \
80 columns, '-' for bullets. Be brief and do the work with tools rather than describing it. ASCII only. When the \
visitor just chats, chat back briefly and warmly; you can be playful about being Claude (from 2026) living inside \
1993 software, but stay accurate about what you can do here."""

TOOLS = [
    {'name': 'run_command', 'eager_input_streaming': True,
     'description': 'Run one DOS command line through COMMAND.COM in C:\\B3\\WORK and return its stdout '
                    '(first 3500 characters). 60 second limit.',
     'input_schema': {'type': 'object', 'properties': {'command': {'type': 'string'}},
                      'required': ['command'], 'additionalProperties': False}},
    {'name': 'read_file', 'eager_input_streaming': True,
     'description': 'Read a text file (first 3500 characters). Relative paths are under C:\\B3\\WORK.',
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}},
                      'required': ['path'], 'additionalProperties': False}},
    {'name': 'write_file', 'eager_input_streaming': True,
     'description': 'Create or overwrite a text file (up to 6000 characters, DOS line endings are added). '
                    'Relative paths are under C:\\B3\\WORK.',
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'}},
                      'required': ['path', 'content'], 'additionalProperties': False}},
]

_client = {}


def api():
    import anthropic
    key = cfg('ANTHROPIC_API_KEY')
    if _client.get('key') != key:
        _client['c'] = anthropic.AsyncAnthropic(api_key=key, timeout=60.0, max_retries=1)
        _client['key'] = key
    return _client['c']


def valid(name, inp):
    if not isinstance(inp, dict):
        return 'input is not an object'
    if name == 'run_command':
        c = inp.get('command')
        if not isinstance(c, str) or not c.strip():
            return 'command must be a non-empty string'
        if len(c) > 200:
            return 'command is longer than DOS allows (keep it under 127 characters)'
    elif name == 'read_file':
        if not isinstance(inp.get('path'), str) or not inp['path'].strip():
            return 'path must be a non-empty string'
    elif name == 'write_file':
        if not isinstance(inp.get('path'), str) or not inp['path'].strip() or not isinstance(inp.get('content'), str):
            return 'path and content must be strings'
        if len(inp['content']) > 6000:
            return 'content is over 6000 characters; split it into smaller files'
    else:
        return 'unknown tool'
    return None


def tool_title(name, inp):
    if name == 'run_command':
        return 'Run(%s)' % inp.get('command', '')
    if name == 'read_file':
        return 'Read(%s)' % inp.get('path', '')
    return 'Write(%s)' % inp.get('path', '')


# --------------------------------------------------------------------------- the machine

PHASES = ('dark', 'booting', 'ready', 'building', 'live', 'ending')


class Session:
    def __init__(self, ws, ip):
        self.ws, self.ip = ws, ip
        self.sid = secrets.token_hex(5)
        self.note = ''
        self.rest_until = 0


class Machine:
    def __init__(self):
        self.phase = 'dark'
        self.phase_t = time.time()
        self.com1 = Line('COM1', int(cfg('W31_COM1')), self.on_com1)
        self.com2 = Line('COM2', int(cfg('W31_COM2')), self.on_com2)
        self.rx2 = b''
        self.waiters = {}          # tool id -> future
        self.events = asyncio.Queue()   # (type, payload) from COM2
        self.tui = Tui(self)
        self.sessions = set()
        self.queue = []
        self.driver = None
        self.lease_start = 0
        self.last_key = 0
        self.task = None           # current agent turn
        self.messages = []
        self.usage = {'in': 0, 'out': 0, 'usd': 0.0}
        self.changed = asyncio.Event()
        self.step = ''
        self.build_t = 0
        self.lat = deque(maxlen=50)
        self.boot_lock = asyncio.Lock()
        tok = os.path.join(DATA, 'admin.token')
        if not os.path.exists(tok):
            with open(tok, 'w') as f:
                f.write(secrets.token_hex(16))
            os.chmod(tok, 0o600)
        self.admin_token = open(tok).read().strip()

    def set_phase(self, p):
        if p != self.phase:
            log('phase %s -> %s' % (self.phase, p))
            self.phase, self.phase_t = p, time.time()
            self.changed.set()

    # ---- COM1: what Terminal sends (a visitor never types into Windows directly) ----
    async def on_com1(self, d):
        pass

    # ---- COM2 -------------------------------------------------------------------------
    async def on_com2(self, d):
        self.rx2 += d
        while EOT in self.rx2:
            msg, self.rx2 = self.rx2.split(EOT, 1)
            if not msg:
                continue
            t, p = chr(msg[0]), msg[1:].decode('cp1252', 'replace')
            if t == 'O':
                tid, _, rest = p.partition('\x1f')
                fut = self.waiters.pop(tid, None)
                if fut and not fut.done():
                    fut.set_result(rest)
                else:
                    self.events.put_nowait(('O', p))
            else:
                if t == 'S':
                    self.step = p
                    self.changed.set()
                log('COM2 %s %s' % (t, p[:120]))
                self.events.put_nowait((t, p))

    def send2(self, t, payload=''):
        b = t.encode() + cp(payload).replace(EOT, b'?') + EOT
        self.com2.send(b)

    async def call2(self, t, tid, payload, timeout):
        fut = asyncio.get_running_loop().create_future()
        self.waiters[tid] = fut
        self.send2(t, tid + '\x1f' + payload)
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self.waiters.pop(tid, None)

    async def wait_event(self, types, timeout):
        end = time.time() + timeout
        while True:
            left = end - time.time()
            if left <= 0:
                raise asyncio.TimeoutError()
            t, p = await asyncio.wait_for(self.events.get(), left)
            if t in types:
                return t, p

    # ---- lifecycle -------------------------------------------------------------------
    async def boot(self):
        """fresh C: from the golden copy, start DOSBox-X, wait for B3BOOT to say hello"""
        async with self.boot_lock:
            self.set_phase('booting')
            self.step = ''
            await self.sh(DBX, 'stop')
            self.com1.flush_pending()
            self.com2.flush_pending()
            if os.path.isdir(GOLDEN):
                await self.sh('rsync', '-a', '--delete', GOLDEN + '/', RUN + '/')
            while not self.events.empty():
                self.events.get_nowait()
            self.rx2 = b''
            await self.sh(DBX, 'start')
            try:
                await asyncio.wait_for(self.com2.connected.wait(), 20)
                await self.wait_event(('H',), 90)
                self.set_phase('ready')
                return True
            except asyncio.TimeoutError:
                log('boot timed out')
                self.set_phase('dark')
                return False

    @staticmethod
    async def sh(*args):
        p = await asyncio.create_subprocess_exec(*args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await p.wait()

    async def build(self):
        """B3BOOT pours the source into Notepad, saves it, compiles it; BASILISK.EXE comes up"""
        self.set_phase('building')
        self.build_t = time.time()
        self.send2('G')
        try:
            t, p = await self.wait_event(('D', 'E'), 150)
            if t == 'E':
                raise RuntimeError('build: ' + p)
            t, p = await self.wait_event(('H', 'E'), 40)        # BASILISK.EXE on COM2
            if t == 'E':
                raise RuntimeError('basilisk: ' + p)
            await asyncio.wait_for(self.wait_event(('R',), 30), 31)   # it has assembled its window
        except asyncio.TimeoutError:
            raise RuntimeError('build timed out at %s' % self.step)
        log('built in %.1fs' % (time.time() - self.build_t))
        self.messages = []
        self.usage = {'in': 0, 'out': 0, 'usd': 0.0}
        self.status()
        await asyncio.sleep(0.3)
        self.banner()
        self.tui.show_prompt()
        self.set_phase('live')

    def banner(self):
        t = self.tui
        t.out('\x1b[2J\x1b[H')
        t.out('\x1b[7m' + ' BASILISK 3.11 '.ljust(W - 1) + '\x1b[0m\n')
        t.out('\n')
        t.out('  Claude Code, for Windows for Workgroups 3.11.\n')
        t.out('  Assembled just now from Terminal, Clock, Cardfile and Calculator,\n')
        t.out('  compiled by Open Watcom from a Notepad file.\n')
        t.out('  model: %s    cwd: C:\\B3\\WORK\n' % cfg('W31_MODEL'))
        t.out('\n')
        t.out('  Ask it to look around, write a file, or write and compile a C program.\n')
        t.out('  Enter sends.  Esc interrupts.  Up/Down recalls.  PgUp/PgDn scroll.  /help\n')
        t.out('\n')

    def status(self, doing=None):
        if doing is not None:
            self.doing = doing
        u = self.usage
        lines = ['model   %s' % cfg('W31_MODEL'),
                 'tokens  %s in, %s out' % (f"{u['in']:,}", f"{u['out']:,}"),
                 'cost    $%.5f  (see Calculator)' % u['usd'],
                 'cwd     C:\\B3\\WORK', '',
                 'now     ' + (getattr(self, 'doing', '') or 'ready')]
        if self.driver and self.queue:
            left = max(0, int(self.lease_start + cfgf('W31_LEASE') - time.time()))
            lines.append('time    %d:%02d left (someone waits)' % divmod(left, 60))
        self.send2('S', '\r\n'.join(lines))
        self.send2('C', '$%.5f ' % u['usd'])

    # ---- sessions --------------------------------------------------------------------
    def public(self, s=None):
        st = {'t': 'state', 'phase': self.phase, 'since': self.phase_t, 'now': time.time(),
              'viewers': len(self.sessions), 'queue': len(self.queue), 'step': self.step,
              'busy': bool(self.task and not self.task.done()), 'model': cfg('W31_MODEL'),
              'quiet': BUDGET.over() or not cfg('ANTHROPIC_API_KEY')}
        if self.driver and self.queue:
            st['lease_left'] = max(0, int(self.lease_start + cfgf('W31_LEASE') - time.time()))
        if s is not None:
            st['you'] = 'driver' if s is self.driver else ('queued' if s in self.queue else 'watcher')
            if s in self.queue:
                st['pos'] = self.queue.index(s) + 1
            st['note'] = s.note if time.time() - getattr(s, 'note_t', 0) < 10 else ''
            st['rest_until'] = s.rest_until if s.rest_until > time.time() else 0
        return st

    async def broadcast(self):
        for s in list(self.sessions):
            try:
                await s.ws.send_json(self.public(s))
            except Exception:
                self.drop(s)

    def note(self, s, text):
        s.note, s.note_t = text, time.time()
        self.changed.set()

    def drop(self, s):
        self.sessions.discard(s)
        if s in self.queue:
            self.queue.remove(s)
        self.changed.set()

    def join(self, s):
        if s is self.driver or s in self.queue:
            return
        if cfg('W31_ONE_PER_IP') == '1' and (any(q.ip == s.ip for q in self.queue) or
                                             (self.driver and self.driver.ip == s.ip)):
            self.note(s, 'Someone at your address already has a place.')
            return
        until = LIMITS.session_ok(s.ip)
        if until:
            s.rest_until = until
            s.note = ''
            return
        if len(self.queue) >= cfgf('W31_QUEUE_MAX'):
            self.note(s, 'The line is long. Watch a while and try again.')
            return
        s.note = ''
        self.queue.append(s)
        self.changed.set()

    async def scheduler(self):
        """one driver at a time; reboots the machine between drivers"""
        while True:
            await asyncio.sleep(0.5)
            if self.phase == 'dark':
                await self.boot()
                continue
            if self.driver:
                d = self.driver
                gone = d not in self.sessions
                idle = (time.time() - self.last_key > cfgf('W31_IDLE')) and not (self.task and not self.task.done())
                lease = self.queue and time.time() - self.lease_start > cfgf('W31_LEASE')
                if gone or idle or lease:
                    why = 'left' if gone else ('idle' if idle else 'time')
                    await self.end_session(why)
                continue
            if self.phase == 'ready' and self.queue:
                s = self.queue.pop(0)
                if s not in self.sessions:
                    continue
                LIMITS.session_note(s.ip)
                self.driver, self.lease_start, self.last_key = s, time.time(), time.time()
                self.changed.set()
                try:
                    await self.build()
                except Exception as e:
                    log('build failed: %r' % e)
                    self.driver = None
                    self.note(s, 'The build failed on this machine; it is rebooting. Try again in a minute.')
                    await self.boot()
                self.changed.set()

    async def end_session(self, why):
        log('session ends (%s)' % why)
        if self.task and not self.task.done():
            self.task.cancel()
        self.tui.hide_prompt()
        self.tui.out('\n\x1b[7m %s \x1b[0m\n' % {
            'left': 'The visitor left. Rebooting for the next one...',
            'idle': 'Quiet for a while, so this session is over. Rebooting...',
            'time': 'Time is up: someone else is waiting. Thank you! Rebooting...'}[why])
        self.set_phase('ending')
        self.driver = None
        self.changed.set()
        await asyncio.sleep(3)
        await self.boot()

    # ---- the driver's keys -------------------------------------------------------------
    def key(self, s, k, ctrl=False):
        if s is not self.driver or self.phase != 'live':
            return
        self.last_key = time.time()
        if k == 'Escape':
            if self.task and not self.task.done():
                self.task.cancel()
            return
        if k in ('PageUp', 'PageDown'):
            self.send2('V', 'P-' if k == 'PageUp' else 'P+')
            return
        busy = self.task and not self.task.done()
        if busy:
            if k == 'Enter':
                return      # one request at a time; the line keeps what they typed
            # typing ahead while Claude works: kept, shown when the prompt returns
            self.tui.prompt_on = False
            self.tui.key(k, ctrl)
            return
        text = self.tui.key(k, ctrl)
        if text is not None:
            self.submit(s, text)

    def scroll(self, s, n):
        if s is self.driver and self.phase == 'live':
            self.last_key = time.time()
            self.send2('V', ('%+d' % max(-30, min(30, int(n)))))

    def paste(self, s, text):
        if s is self.driver and self.phase == 'live' and isinstance(text, str):
            self.last_key = time.time()
            if self.task and not self.task.done():
                self.tui.prompt_on = False
            self.tui.paste(text)

    def submit(self, s, text):
        t = self.tui
        t.prompt_on = False
        t.out('\r\x1b[K> ')
        t.para(text, '', '  ')           # the request stays in the transcript, wrapped
        if text.startswith('/'):
            self.slash(text)
            t.out('\n')
            t.show_prompt()
            return
        until = LIMITS.turn_ok(s.ip)
        if until:
            t.out('\n')
            t.para('You have asked a lot in a short time, so BASILISK is resting for you. You can type '
                   'again at %s UTC.' % time.strftime('%H:%M', time.gmtime(until)), BUL + ' ')
            t.out('\n')
            t.show_prompt()
            return
        if BUDGET.over() or not cfg('ANTHROPIC_API_KEY'):
            t.out('\n')
            t.para('The line to Claude is quiet for the rest of the month (its budget is spent). '
                   'The machine still works; come back next month to talk.', BUL + ' ')
            t.out('\n')
            t.show_prompt()
            return
        LIMITS.turn_note(s.ip)
        t.out('\n')
        self.status('thinking')
        self.task = asyncio.create_task(self.turn(s, text))

    def slash(self, text):
        t = self.tui
        cmd = text.split()[0].lower()
        t.out('\n')
        if cmd == '/help':
            t.para('Type a request and press Enter. BASILISK can run DOS commands, read and write files, '
                   'and compile C with Open Watcom. Keys: Esc interrupts, Up/Down recall earlier lines, '
                   'PgUp/PgDn scroll the Terminal buffer, Ctrl+U clears the line. Commands: /help, /clear '
                   '(forget the conversation), /cost.', BUL + ' ')
        elif cmd == '/clear':
            self.messages = []
            t.out('\x1b[2J\x1b[H')
            self.banner()
            t.para('Conversation cleared.', BUL + ' ')
        elif cmd == '/cost':
            u = self.usage
            t.para('This session: %s tokens in, %s out, $%.5f.' % (f"{u['in']:,}", f"{u['out']:,}", u['usd']),
                   BUL + ' ')
        else:
            t.para('Unknown command. Try /help.', BUL + ' ')

    async def turn(self, s, text):
        t = self.tui
        self.messages.append({'role': 'user', 'content': text})
        pending_tools = None
        try:
            for step in range(16):
                t.stream_start_pending = True
                streamed = False
                async with api().messages.stream(
                        model=cfg('W31_MODEL'), max_tokens=4000, system=SYSTEM, tools=TOOLS,
                        messages=self.messages, cache_control={'type': 'ephemeral'},
                        output_config={'effort': cfg('W31_EFFORT')}) as st:
                    t0 = time.time()
                    self.inflight = {'in': len(json.dumps(self.messages, default=str)) // 4 + 1200, 'out': 0}
                    async for ev in st:
                        if ev.type == 'text':
                            if not streamed:
                                t.stream_start()
                                streamed = True
                            t.stream(ev.text)
                            self.inflight['out'] += max(1, len(ev.text) // 4)
                        elif ev.type == 'input_json':
                            self.inflight['out'] += max(1, len(ev.partial_json) // 4)
                    msg = await st.get_final_message()
                self.inflight = None
                if streamed:
                    t.stream_end()
                usd, tin, tout = BUDGET.add(cfg('W31_MODEL'), msg.usage)
                LIMITS.usd_note(s.ip, usd)
                self.usage['in'] += tin
                self.usage['out'] += tout
                self.usage['usd'] += usd
                self.status()
                log('api %.1fs in=%d out=%d $%.5f stop=%s' % (time.time() - t0, tin, tout, usd, msg.stop_reason))
                self.messages.append({'role': 'assistant', 'content': msg.content})
                uses = [b for b in msg.content if b.type == 'tool_use']
                if msg.stop_reason == 'refusal':
                    t.para('(Claude declined that one.)', BUL + ' ')
                    break
                if not uses:
                    break
                if msg.stop_reason == 'max_tokens':
                    pending_tools = uses
                    raise RuntimeError('a tool call was cut off')
                pending_tools = uses
                results = []
                for u in uses:
                    results.append(await self.run_tool(u))
                pending_tools = None
                self.status('thinking')
                self.messages.append({'role': 'user', 'content': results})
            else:
                t.para('(Stopping here: that was a lot of steps for one request.)', BUL + ' ')
        except asyncio.CancelledError:
            fl = getattr(self, 'inflight', None)
            if fl:      # an interrupted stream reports no usage: bill a conservative estimate
                class U:
                    input_tokens, output_tokens = fl['in'], fl['out'] + 50
                    cache_creation_input_tokens = cache_read_input_tokens = 0
                usd, tin, tout = BUDGET.add(cfg('W31_MODEL'), U)
                LIMITS.usd_note(s.ip, usd)
                self.usage['in'] += tin
                self.usage['out'] += tout
                self.usage['usd'] += usd
                self.inflight = None
            t.out('\x1b[0m\n')
            t.para('Interrupted.', '  ')
            if pending_tools:
                self.messages.append({'role': 'user', 'content': [
                    {'type': 'tool_result', 'tool_use_id': u.id, 'content': 'interrupted by the user',
                     'is_error': True} for u in pending_tools]})
            elif self.messages and self.messages[-1]['role'] == 'user' and isinstance(self.messages[-1]['content'], str):
                self.messages.append({'role': 'assistant', 'content': '(interrupted)'})
        except Exception as e:
            log('turn error: %r' % e)
            t.out('\n')
            t.para('Something went wrong on the line (%s). Try again.' % type(e).__name__, BUL + ' ')
            if pending_tools:
                self.messages.append({'role': 'user', 'content': [
                    {'type': 'tool_result', 'tool_use_id': u.id, 'content': 'not run', 'is_error': True}
                    for u in pending_tools]})
            elif self.messages and self.messages[-1]['role'] == 'user':
                self.messages.append({'role': 'assistant', 'content': '(error)'})
        finally:
            self.last_key = time.time()
            self.status('ready')
            if self.phase == 'live':
                t.out('\n')
                t.show_prompt()
            self.changed.set()

    async def run_tool(self, u):
        t = self.tui
        inp = u.input
        bad = valid(u.name, inp)
        t.para(tool_title(u.name, inp if isinstance(inp, dict) else {}), BUL + ' ', '    ')
        if bad:
            t.out('  \xa6 ' + bad + '\n')
            return {'type': 'tool_result', 'tool_use_id': u.id, 'content': bad, 'is_error': True}
        tid = secrets.token_hex(3)
        self.status(tool_title(u.name, inp)[:30])
        try:
            if u.name == 'run_command':
                res = await self.call2('R', tid, inp['command'], 75)
            elif u.name == 'read_file':
                res = await self.call2('G', tid, inp['path'], 30)
            else:
                body = inp['content'].replace('\r\n', '\n').replace('\n', '\r\n')
                res = await self.call2('W', tid, inp['path'] + '\x1f' + body, 60)
        except asyncio.TimeoutError:
            res = 'err\x1fno answer from BASILISK.EXE in time'
        status, _, text = res.partition('\x1f')
        text = text.replace('\r\n', '\n').rstrip('\n\x1a')
        lines = [ln for ln in text.split('\n')]
        if u.name == 'write_file' and status == 'ok':
            shown = ['wrote %d lines' % (inp['content'].count('\n') + 1)]
        else:
            shown = [ln for ln in lines if ln.strip()][:5]
        for ln in shown:
            t.out('  \xa6 ' + ln[:W - 6].rstrip() + '\n')
        extra = len([ln for ln in lines if ln.strip()]) - len(shown)
        if extra > 0 and u.name != 'write_file':
            t.out('  \xa6 ... (+%d lines)\n' % extra)
        if not text.strip():
            t.out('  \xa6 (no output)\n')
        return {'type': 'tool_result', 'tool_use_id': u.id, 'content': text[:3500] or '(no output)',
                'is_error': status != 'ok'}

    # ---- loops -----------------------------------------------------------------------
    async def pusher(self):
        while True:
            try:
                await asyncio.wait_for(self.changed.wait(), 5)
            except asyncio.TimeoutError:
                pass
            self.changed.clear()
            await self.broadcast()
            await asyncio.sleep(0.15)

    async def ticker(self):
        """keep the Cardfile status card's countdown honest while someone waits"""
        while True:
            await asyncio.sleep(15)
            if self.phase == 'live' and self.driver and self.queue:
                self.status()


M = None

# --------------------------------------------------------------------------- public side


def client_ip(req):
    peer = req.remote or ''
    if peer == cfg('W31_TRUSTED_PROXY'):
        xff = req.headers.get('X-Forwarded-For', '')
        if xff:
            return xff.split(',')[-1].strip()[:64] or peer
    return peer


def origin_ok(req):
    o = req.headers.get('Origin')
    return not o or o in [x.strip() for x in cfg('W31_ORIGINS').split(',')]


@web.middleware
async def cors(req, handler):
    resp = await handler(req)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    return resp


async def p_state(req):
    return web.json_response(M.public())


async def p_ws(req):
    if not origin_ok(req):
        raise web.HTTPForbidden()
    ws = web.WebSocketResponse(heartbeat=25, max_msg_size=8192)
    await ws.prepare(req)
    ip = client_ip(req)
    if sum(1 for s in M.sessions if s.ip == ip) >= 8:
        await ws.close(code=4008, message=b'too many')
        return ws
    s = Session(ws, ip)
    M.sessions.add(s)
    M.changed.set()
    rate = deque()
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            now = time.time()
            rate.append(now)
            while rate and rate[0] < now - 1:
                rate.popleft()
            if len(rate) > 60:          # 60 messages a second is faster than anyone types
                continue
            try:
                m = json.loads(msg.data)
            except ValueError:
                continue
            t = m.get('t')
            if t == 'k':
                k = m.get('k')
                if isinstance(k, str) and 0 < len(k) <= 12:
                    M.key(s, k, bool(m.get('c')))
                    if m.get('n') is not None and s is M.driver:     # latency probe echo
                        await ws.send_json({'t': 'ka', 'n': m.get('n')})
            elif t == 'paste':
                M.paste(s, m.get('text', ''))
            elif t == 'wheel':
                try:
                    M.scroll(s, int(m.get('n', 0)))
                except (TypeError, ValueError):
                    pass
            elif t == 'start':
                M.join(s)
                M.changed.set()
            elif t == 'leave':
                if s is M.driver:
                    asyncio.create_task(M.end_session('left'))
                elif s in M.queue:
                    M.queue.remove(s)
                M.changed.set()
            elif t == 'ping':
                await ws.send_json(M.public(s))
    finally:
        M.drop(s)
    return ws


async def p_vnc(req):
    """the screen, view-only: an RFB proxy to x11vnc that drops every client input message"""
    if not origin_ok(req):
        raise web.HTTPForbidden()
    if sum(1 for _ in VNC_CLIENTS) >= 40:
        raise web.HTTPServiceUnavailable()
    ws = web.WebSocketResponse(protocols=('binary',), heartbeat=30, max_msg_size=1 << 16)
    await ws.prepare(req)
    try:
        r, w = await asyncio.wait_for(asyncio.open_connection('127.0.0.1', int(cfg('W31_VNC'))), 5)
    except Exception:
        await ws.close()
        return ws
    VNC_CLIENTS.add(ws)

    async def down():
        try:
            while True:
                d = await r.read(65536)
                if not d:
                    break
                await ws.send_bytes(d)
        except Exception:
            pass
        finally:
            await ws.close()

    dt = asyncio.create_task(down())
    buf = b''
    hs = 0             # bytes of handshake still to pass: version (12) + security choice (1) + ClientInit (1)
    try:
        async for msg in ws:
            if msg.type != WSMsgType.BINARY:
                continue
            buf += msg.data
            outb = b''
            while buf:
                if hs < 14:
                    n = min(14 - hs, len(buf))
                    outb += buf[:n]
                    buf = buf[n:]
                    hs += n
                    continue
                t = buf[0]
                need = {0: 20, 3: 10, 4: 8, 5: 6}.get(t)
                if t == 2:
                    if len(buf) < 4:
                        break
                    need = 4 + 4 * struct.unpack('>H', buf[2:4])[0]
                elif t == 6:
                    if len(buf) < 8:
                        break
                    need = 8 + struct.unpack('>I', buf[4:8])[0]
                    if need > 1 << 16:
                        raise ValueError('cut text too long')
                elif need is None:
                    raise ValueError('unknown RFB message %d' % t)
                if len(buf) < need:
                    break
                if t in (0, 2, 3):
                    outb += buf[:need]            # pixel format, encodings, update requests pass
                buf = buf[need:]                  # key, pointer, clipboard: dropped
            if outb:
                w.write(outb)
                await w.drain()
    except Exception:
        pass
    finally:
        VNC_CLIENTS.discard(ws)
        dt.cancel()
        try:
            w.close()
        except Exception:
            pass
    return ws


VNC_CLIENTS = set()


async def p_admin(req):
    if req.remote != '127.0.0.1' or req.query.get('token') != M.admin_token:
        raise web.HTTPForbidden()
    op = req.match_info['op']
    body = (await req.read()).decode('utf-8', 'replace')
    if op == 'x':          # B3BOOT: WinExec
        tid = 'x'
        M.send2('X', body)
        try:
            t, p = await M.wait_event(('O',), 10)
            return web.Response(text=p + '\n')
        except asyncio.TimeoutError:
            return web.Response(text='(timeout)\n')
    if op == 'y':          # B3BOOT: dump windows to C:\B3\SPY.TXT
        M.send2('Y')
        try:
            await M.wait_event(('O',), 10)
        except asyncio.TimeoutError:
            pass
        try:
            return web.Response(text=open(os.path.join(RUN, 'B3', 'SPY.TXT'), errors='replace').read())
        except OSError:
            return web.Response(text='(no spy)\n')
    if op == 'live':       # test: pretend a driver arrived (build + banner)
        async def go():
            class _Quiet:                       # a test driver with no browser behind it
                async def send_json(self, *a):
                    pass
            M.driver = Session(_Quiet(), '127.0.0.1')
            M.sessions.add(M.driver)
            M.last_key = time.time()
            await M.build()
        asyncio.create_task(go())
        return web.Response(text='building\n')
    if op == 'type':       # test: keystrokes as the driver
        for ch in body:
            M.key(M.driver, {'\n': 'Enter', '\x1b': 'Escape', '\x08': 'Backspace'}.get(ch, ch))
            await asyncio.sleep(0.02)
        return web.Response(text='typed\n')
    if op == 'boot':
        asyncio.create_task(M.boot())
        return web.Response(text='booting\n')
    if op == 'send2':      # raw COM2 message: first char is the type
        M.send2(body[:1], body[1:])
        return web.Response(text='sent\n')
    if op == 'out1':
        M.tui.out(body)
        return web.Response(text='sent\n')
    if op == 'status':
        return web.json_response({'phase': M.phase, 'step': M.step, 'spent': BUDGET.spent(),
                                  'driver': bool(M.driver), 'queue': len(M.queue), 'viewers': len(M.sessions),
                                  'vnc': len(VNC_CLIENTS)})
    raise web.HTTPNotFound()


async def main():
    global M
    M = Machine()
    try:
        import anthropic  # noqa: F401
        if cfg('ANTHROPIC_API_KEY'):
            api()
    except ImportError:
        pass
    signal.signal(signal.SIGHUP, lambda *a: (load_env(), log('reloaded env')))
    app = web.Application(middlewares=[cors], client_max_size=64 * 1024)
    app.add_routes([web.get('/state', p_state), web.get('/ws', p_ws), web.get('/vnc', p_vnc),
                    web.post('/admin/{op}', p_admin),
                    web.get('/', lambda r: web.Response(text='BASILISK 3.11\n'))])
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, '127.0.0.1', int(cfg('W31_PUBLIC'))).start()
    log('public 127.0.0.1:%s, COM1 %s, COM2 %s, model %s, key %s, month $%.4f of $%s' % (
        cfg('W31_PUBLIC'), cfg('W31_COM1'), cfg('W31_COM2'), cfg('W31_MODEL'),
        'present' if cfg('ANTHROPIC_API_KEY') else 'absent', BUDGET.spent(), cfg('W31_MONTHLY_CAP_USD')))
    tasks = [M.com1.serve(), M.com2.serve(), M.pusher(), M.ticker()]
    if os.environ.get('W31_NO_SCHED') != '1':
        tasks.append(M.scheduler())
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
