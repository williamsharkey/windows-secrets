#!/usr/bin/env python3
"""BASILISK 3.11 - Claude Code on Windows for Workgroups 3.11, a suite assembled from Terminal, Cardfile, Clock,
Calculator, Notepad, File Manager and Control Panel (puppetry/w31suite: five Cardfile cards are the tabs -
Chat, Plan, Files, Usage, Settings).

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

ROOT = os.environ.get('W31_ROOT', '/root/w31')
DATA = os.path.join(ROOT, 'data')
SNAPC = os.environ.get('W31_SNAPC', '/root/snap/dosbox-x/common/w31')
RUN = os.path.join(SNAPC, 'run')
GOLDEN = os.path.join(ROOT, 'golden')
DBX = os.environ.get('W31_DBX', os.path.join(ROOT, 'dbx.sh'))
XDISPLAY = os.environ.get('W31_DISPLAY', ':31')
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
    'W31_MODELS': 'claude-haiku-5-5,claude-sonnet-5-5',
}
CONTEXT = {'claude-haiku-5-5': 1000000, 'claude-sonnet-5-5': 1000000}
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
LENGTHS = {'brief': 'Keep this answer very short: one to three sentences unless a tool result must be shown.',
           'normal': '',
           'full': 'Be thorough in this answer: explain your reasoning and what you did.'}
SAFE = ('DIR', 'TYPE', 'VER', 'MEM', 'SET', 'TREE', 'FIND', 'ECHO')
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

    def usd_today(self, ip):
        return sum(x for _, x in self._trim(self.usd.setdefault(ip, deque()), 86400))

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
        self.on_lost = None

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
                if self.on_lost:
                    self.on_lost()
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

The screen is a tabbed suite made of real Windows 3.1 programs; the tabs are Cardfile cards: 1 Chat (this \
Terminal), 2 Plan (a Notepad showing your plan: keep it with todo_write for any task of three or more steps, \
marking one item in_progress at a time and items done as you finish them), 3 Files (File Manager on C:\\B3\\WORK; \
the visitor can mention a file as @NAME; C:\\B3\\WORK\\CLAUDE.MD, if it exists, holds standing instructions and \
is given to you when it changes), 4 Usage, 5 Settings. The visitor may set Windows to ask before your commands \
run and may say no; if a tool result says the visitor declined, don't retry it, ask what they'd like instead.

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
    {'name': 'todo_write', 'eager_input_streaming': True,
     'description': 'Replace your plan (shown on the Plan card in Windows) with this list. Use it for tasks with '
                    'three or more steps; keep exactly one item in_progress while working.',
     'input_schema': {'type': 'object', 'properties': {'items': {'type': 'array', 'maxItems': 12, 'items': {
         'type': 'object', 'properties': {'text': {'type': 'string'},
                                          'status': {'type': 'string', 'enum': ['pending', 'in_progress', 'done']}},
         'required': ['text', 'status'], 'additionalProperties': False}}},
                      'required': ['items'], 'additionalProperties': False}},
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
    elif name == 'todo_write':
        items = inp.get('items')
        if not isinstance(items, list) or len(items) > 12:
            return 'items must be a list of at most 12'
        for it in items:
            if not isinstance(it, dict) or not isinstance(it.get('text'), str) or \
                    it.get('status') not in ('pending', 'in_progress', 'done'):
                return 'each item needs text and a status of pending, in_progress or done'
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
    if name == 'todo_write':
        return 'Plan(%d items)' % len(inp.get('items') or [])
    return 'Write(%s)' % inp.get('path', '')


# --------------------------------------------------------------------------- the machine

PHASES = ('dark', 'booting', 'ready', 'building', 'live', 'ending')


class Session:
    def __init__(self, ws, ip):
        self.ws, self.ip = ws, ip
        self.sid = secrets.token_hex(5)
        self.note = ''
        self.rest_until = 0


def dosbox_pids():
    out = subprocess.run(['pgrep', '-f', 'dosbox-x -defaultdir ' + SNAPC], capture_output=True, text=True).stdout
    return [int(x) for x in out.split()]


def freeze(stop):
    """idle costs nothing: the emulator is paused (SIGSTOP) while nobody drives; Xvfb keeps its last frame"""
    for pid in dosbox_pids():
        try:
            os.kill(pid, signal.SIGSTOP if stop else signal.SIGCONT)
        except ProcessLookupError:
            pass


class Machine:
    def __init__(self):
        self.phase = 'dark'
        self.phase_t = time.time()
        self.com1 = Line('COM1', int(cfg('W31_COM1')), self.on_com1)
        self.com2 = Line('COM2', int(cfg('W31_COM2')), self.on_com2)
        self.com2.on_lost = self.lost
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
        self.fresh()
        self.changed = asyncio.Event()
        self.step = ''
        self.build_t = 0
        self.lat = deque(maxlen=50)
        self.boot_lock = asyncio.Lock()
        self.frozen = False
        tok = os.path.join(DATA, 'admin.token')
        if not os.path.exists(tok):
            with open(tok, 'w') as f:
                f.write(secrets.token_hex(16))
            os.chmod(tok, 0o600)
        self.admin_token = open(tok).read().strip()

    def fresh(self):
        """a new visitor: a new conversation, default settings, nothing allowed yet"""
        self.messages = []
        self.usage = {'in': 0, 'out': 0, 'usd': 0.0, 'ctx': 0, 'cached': 0, 'turns': 0}
        self.set = {'effort': cfg('W31_EFFORT'), 'length': 'normal', 'ask': True, 'model': cfg('W31_MODEL')}
        self.allowed, self.allow_writes = set(), False
        self.claude_md = None
        self.asks = {}
        self.tab = 'Chat'
        self.mention = ''

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
            elif t in 'JI@' or (t == 'E' and '|' in p):
                self.on_client(t, p)
            else:
                if t == 'S':
                    self.step = p
                    self.changed.set()
                log('COM2 %s %s' % (t, p[:120]))
                self.events.put_nowait((t, p))

    def on_client(self, t, p):
        """what BASILISK.EXE reports while live: the card in front, settings, permission answers, a mention"""
        if t == 'J':
            self.tab = p or 'Chat'
            self.changed.set()
        elif t == 'E':
            effort, length, ask, model = (p.split('|') + ['', '', '', ''])[:4]
            old = dict(self.set)
            if effort in EFFORTS:
                self.set['effort'] = effort
            if length in LENGTHS:
                self.set['length'] = length
            self.set['ask'] = ask != 'auto'
            want = 'claude-sonnet-5-5' if model == 'sonnet' else cfg('W31_MODEL')
            self.set['model'] = want if want in [x.strip() for x in cfg('W31_MODELS').split(',')] else cfg('W31_MODEL')
            if self.phase == 'live' and old != self.set:
                self.usage_card()
        elif t == 'I':
            aid, _, answer = p.partition('\x1f')
            fut = self.asks.get(aid)
            if fut and not fut.done() and answer in ('once', 'always', 'deny'):
                fut.set_result(answer)
        elif t == '@' and self.phase == 'live':
            self.tui.prompt_on = not (self.task and not self.task.done())
            self.tui.paste(p)
            self.send2('J', '1')

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
            freeze(False)                          # a paused process ignores SIGTERM
            self.frozen = False
            self.drop_still()
            for attempt in range(3):
                await self.sh(DBX, 'stop')
                for _ in range(50):                # the old emulator's cables must be unplugged first
                    if not self.com1.connected.is_set() and not self.com2.connected.is_set():
                        break
                    await asyncio.sleep(0.1)
                self.com1.flush_pending()
                self.com2.flush_pending()
                if os.path.isdir(GOLDEN) and attempt == 0:
                    await self.sh('rsync', '-a', '--delete', GOLDEN + '/', RUN + '/')
                while not self.events.empty():
                    self.events.get_nowait()
                self.rx2 = b''
                await self.sh(DBX, 'start')
                try:      # the snap launcher can stall on a loaded host: retry rather than wait forever
                    await asyncio.wait_for(self.com2.connected.wait(), 45)
                    break
                except asyncio.TimeoutError:
                    log('DOSBox-X did not connect (attempt %d); restarting it' % (attempt + 1))
            try:
                if not self.com2.connected.is_set():
                    raise asyncio.TimeoutError()
                await self.wait_event(('H',), 150)
                self.set_phase('ready')
                await asyncio.sleep(8)             # let Windows settle (and paint the frame watchers will see)
                if self.phase == 'ready' and not self.driver and not self.queue:
                    self.freeze()
                return True
            except asyncio.TimeoutError:
                log('boot timed out')
                self.set_phase('dark')
                return False

    def lost(self):
        """the emulator vanished outside a reboot: say so, and let the scheduler boot a fresh one"""
        if self.boot_lock.locked() or self.phase in ('booting', 'dark'):
            return
        log('DOSBox-X went away during %s' % self.phase)
        if self.task and not self.task.done():
            self.task.cancel()
        if self.driver:
            self.note(self.driver, 'The machine stopped unexpectedly; it is restarting.')
            self.driver = None
        self.frozen = False
        self.drop_still()
        self.set_phase('dark')

    STILL = os.path.join(DATA, 'still.png')

    def freeze(self):
        """pause the emulator; a still of the last frame stands in front of it (a paused window
        can't repaint, so X would show black after the next expose)"""
        if self.frozen:
            return
        env = dict(os.environ, DISPLAY=XDISPLAY)
        try:
            subprocess.run(['import', '-window', 'root', self.STILL], env=env, timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.still = subprocess.Popen(['display', '-immutable', '-geometry', '+0+0', '-title', 'w31-still',
                                           self.STILL], env=env, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL)
            time.sleep(0.4)                      # mapped before the emulator stops answering exposes
        except (OSError, subprocess.SubprocessError) as e:
            log('still frame: %r' % e)
            self.still = None
        freeze(True)
        self.frozen = True
        log('emulator paused (idle)')

    def drop_still(self):
        st = getattr(self, 'still', None)
        if st and st.poll() is None:
            st.terminate()
        self.still = None

    def thaw(self):
        if self.frozen:
            freeze(False)
            self.frozen = False
            log('emulator resumed')
        self.drop_still()

    @staticmethod
    async def sh(*args):
        p = await asyncio.create_subprocess_exec(*args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await p.wait()

    async def build(self):
        """B3BOOT pours the source into Notepad, saves it, compiles it; BASILISK.EXE comes up"""
        self.set_phase('building')
        self.build_t = time.time()
        self.thaw()
        await asyncio.sleep(1.5)                  # a just-resumed DOSBox-X can drop the first bytes it gets
        for attempt in range(4):
            self.send2('G')
            try:
                await self.wait_event(('S',), 5)     # B3BOOT's first step: it heard us
                break
            except asyncio.TimeoutError:
                log('no answer to G (attempt %d)' % (attempt + 1))
        else:
            raise RuntimeError('B3BOOT did not answer')
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
        keep = dict(self.set)
        self.fresh()
        self.set = keep                      # the Settings card already reported itself
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
        t.out('  Assembled just now from Terminal, Cardfile, Clock, Calculator, Notepad,\n')
        t.out('  File Manager and Control Panel; compiled by Open Watcom from Notepad files.\n')
        t.out('  model: %s    cwd: C:\\B3\\WORK\n' % self.NAMES.get(self.set['model'], self.set['model']))
        t.out('\n')
        t.out('  Cards: 1 Chat  2 Plan  3 Files  4 Usage  5 Settings  (Alt+1..5, or click one)\n')
        t.out('  Enter sends.  Esc interrupts.  Up/Down recalls.  PgUp/PgDn scroll.  /help\n')
        t.out('\n')

    NAMES = {'claude-haiku-5-5': 'Claude Haiku 5.5', 'claude-sonnet-5-5': 'Claude Sonnet 5.5'}

    def status(self, doing=None):
        """the Usage card's words, its gauges, and Calculator's bill"""
        if doing is not None:
            self.doing = doing
        u, st = self.usage, self.set
        name = self.NAMES.get(st['model'], st['model'])
        now = getattr(self, 'doing', '') or 'ready'
        lines = [name, 'effort %s, turn %d' % (st['effort'], u['turns']),
                 '%s tokens in, %s out' % (f"{u['in']:,}", f"{u['out']:,}"),
                 '$%.5f (see Calculator)' % u['usd'], '', 'now: ' + now]
        left = ''
        if self.driver and self.queue:
            left = '%d:%02d left (someone waits)' % divmod(max(0, int(self.lease_start + cfgf('W31_LEASE') - time.time())), 60)
            lines.append(left)
        self.send2('S', '\r\n'.join(lines))
        ip = self.driver.ip if self.driver else ''
        e5 = lambda x: str(int(round((x or 0) * 1e5)))
        text = ('Model: %s, effort %s~This session: %d turns, %s tokens in (%s read from cache), %s out, $%.5f~'
                'Caps: $%.2f a day for you, $%.2f a month for everyone.~/compact shrinks the context; /clear empties it.~~'
                'Now: %s%s') % (name, st['effort'], u['turns'], f"{u['in']:,}", f"{u['cached']:,}", f"{u['out']:,}", u['usd'],
                                cfgf('W31_IP_USD_DAY'), cfgf('W31_MONTHLY_CAP_USD'), now, ('~' + left) if left else '')
        self.send2('N', '|'.join([str(u['ctx']), str(CONTEXT.get(st['model'], 1000000)), e5(LIMITS.usd_today(ip)),
                                  e5(cfgf('W31_IP_USD_DAY')), e5(BUDGET.spent()), e5(cfgf('W31_MONTHLY_CAP_USD')), text]))
        self.send2('C', '$%.5f ' % u['usd'])

    def usage_card(self):
        self.status()

    # ---- sessions --------------------------------------------------------------------
    def public(self, s=None):
        st = {'t': 'state', 'phase': self.phase, 'since': self.phase_t, 'now': time.time(),
              'viewers': len(self.sessions), 'queue': len(self.queue), 'step': self.step,
              'busy': bool(self.task and not self.task.done()), 'model': self.set['model'], 'tab': self.tab,
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
                for attempt in (1, 2):               # one quiet retry on a fresh boot before giving up
                    try:
                        await self.build()
                        break
                    except Exception as e:
                        log('build failed (attempt %d): %r' % (attempt, e))
                        if attempt == 1 and s in self.sessions:
                            await self.boot()
                            continue
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
        if k in ('Alt1', 'Alt2', 'Alt3', 'Alt4', 'Alt5'):
            self.send2('J', k[3])
            return
        if k == 'Insert':
            if self.tab == 'Files':
                self.send2('@')
            return
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
            self.send2('w', ('%+d' % max(-30, min(30, int(n)))))

    def mouse(self, s, x, y, b, d):
        """the driver's pointer: BASILISK.EXE moves Windows' own cursor and clicks there"""
        if s is self.driver and self.phase == 'live':
            self.last_key = time.time()
            self.send2('M', '%d|%d|%d|%d' % (max(0, min(1023, int(x))), max(0, min(767, int(y))), int(b) % 3, 1 if d else 0))

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
        if text.split()[0].lower() == '/compact' and cfg('ANTHROPIC_API_KEY') and not BUDGET.over():
            t.out('\n')
            t.para('Compacting: Claude is summarizing the conversation so far...', BUL + ' ')
            self.status('compacting')
            self.task = asyncio.create_task(self.compact(s))
            return
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
                   'PgUp/PgDn scroll the Terminal buffer, Ctrl+U clears the line, Alt+1..5 (or a click on a card) '
                   'changes card: 1 Chat, 2 Plan, 3 Files (Ins mentions the selected file), 4 Usage, 5 Settings. '
                   'The mouse works in Windows. Commands: /help, /clear (forget the conversation), /compact '
                   '(Claude summarizes it, to save context), /cost, /plan, /files, /usage, /settings.', BUL + ' ')
        elif cmd in ('/plan', '/files', '/usage', '/settings'):
            self.send2('J', {'/plan': '2', '/files': '3', '/usage': '4', '/settings': '5'}[cmd])
        elif cmd == '/clear':
            self.messages = []
            self.usage['ctx'] = 0
            self.claude_md = None
            self.send2('L', '')
            self.status()
            t.out('\x1b[2J\x1b[H')
            self.banner()
            t.para('Conversation cleared.', BUL + ' ')
        elif cmd == '/cost':
            u = self.usage
            t.para('This session: %s tokens in, %s out, $%.5f.' % (f"{u['in']:,}", f"{u['out']:,}", u['usd']),
                   BUL + ' ')
        else:
            t.para('Unknown command. Try /help.', BUL + ' ')

    def bill(self, s, model, usage):
        usd, tin, tout = BUDGET.add(model, usage)
        LIMITS.usd_note(s.ip, usd)
        self.usage['in'] += tin
        self.usage['out'] += tout
        self.usage['usd'] += usd
        self.usage['cached'] += getattr(usage, 'cache_read_input_tokens', 0) or 0
        return usd, tin, tout

    async def memory(self):
        """C:\\B3\\WORK\\CLAUDE.MD, read through BASILISK.EXE; -> words to put before the turn when it changed"""
        try:
            res = await self.call2('G', secrets.token_hex(3), 'CLAUDE.MD', 8)
        except asyncio.TimeoutError:
            return ''
        st, _, text = res.partition('\x1f')
        text = text.strip() if st == 'ok' else ''
        if text == (self.claude_md or ''):
            return ''
        first = self.claude_md is None
        self.claude_md = text
        if not text:
            return '' if first else '[C:\\B3\\WORK\\CLAUDE.MD was removed.]\n\n'
        self.tui.para('(CLAUDE.MD read: %d lines of standing instructions)' % (text.count('\n') + 1), BUL + ' ')
        return '[Standing instructions from C:\\B3\\WORK\\CLAUDE.MD:]\n%s\n[end of CLAUDE.MD]\n\n' % text[:3000]

    async def compact(self, s):
        """/compact: Claude summarizes the conversation so far, and the summary replaces it"""
        t = self.tui
        model = self.set['model']
        try:
            if len(self.messages) < 2:
                t.para('Nothing to compact yet.', BUL + ' ')
                return
            ask = self.messages + [{'role': 'user', 'content':
                'Summarize this conversation for yourself so it can continue from the summary alone: what the '
                'visitor wants, what was done (files written, commands run, results), the current plan, and any '
                'open questions. Plain text, at most 200 words. No tools.'}]
            async with api().messages.stream(model=model, max_tokens=2000, system=SYSTEM, tools=TOOLS,
                                              messages=ask, output_config={'effort': 'low'}) as st:
                msg = await st.get_final_message()
            self.bill(s, model, msg.usage)
            summary = ''.join(b.text for b in msg.content if b.type == 'text').strip()
            if not summary:
                raise RuntimeError('empty summary')
            before = self.usage['ctx']
            self.messages = [{'role': 'user', 'content': '[Summary of the conversation so far]\n' + summary},
                             {'role': 'assistant', 'content': 'Understood; continuing from that summary.'}]
            self.usage['ctx'] = len(SYSTEM + summary) // 4 + 900
            t.para('Compacted: the conversation (%s tokens) is now a summary of about %d words. Claude keeps '
                   'going from there.' % (f"{before:,}", len(summary.split())), BUL + ' ')
        except asyncio.CancelledError:
            t.para('Interrupted.', '  ')
        except Exception as e:
            log('compact error: %r' % e)
            t.para('Could not compact just now (%s).' % type(e).__name__, BUL + ' ')
        finally:
            self.last_key = time.time()
            self.status('ready')
            if self.phase == 'live':
                t.out('\n')
                t.show_prompt()
            self.changed.set()

    async def turn(self, s, text):
        t = self.tui
        model = self.set['model']
        pending_tools = None
        try:
            mem = await self.memory()
            note = LENGTHS.get(self.set['length'], '')
            self.messages.append({'role': 'user', 'content': mem + text + ('\n\n(' + note + ')' if note else '')})
            self.usage['turns'] += 1
            for step in range(16):
                t.stream_start_pending = True
                streamed = False
                async with api().messages.stream(
                        model=model, max_tokens=8000, system=SYSTEM, tools=TOOLS,
                        messages=self.messages, cache_control={'type': 'ephemeral'},
                        output_config={'effort': self.set['effort']}) as st:
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
                usd, tin, tout = self.bill(s, model, msg.usage)
                self.usage['ctx'] = tin + tout
                self.status()
                log(model + ' api %.1fs in=%d out=%d $%.5f stop=%s' % (time.time() - t0, tin, tout, usd, msg.stop_reason))
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
                self.bill(s, model, U)
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
            for f in list(self.asks.values()):
                if not f.done():
                    f.set_result('deny')
            self.last_key = time.time()
            self.status('ready')
            if self.phase == 'live':
                t.out('\n')
                t.show_prompt()
            self.changed.set()

    MARK = {'done': '[x] ', 'in_progress': '[>] ', 'pending': '[ ] '}

    async def permitted(self, name, inp):
        """-> None if it may run, else why not: Windows asks the visitor in a real message box"""
        if not self.set['ask']:
            return None
        if name == 'run_command':
            word = inp['command'].strip().split()[0].upper()
            if word in SAFE or word in self.allowed:
                return None
            what = inp['command']
        elif name == 'write_file':
            if self.allow_writes:
                return None
            what = 'write the file %s (%d characters)' % (inp['path'], len(inp['content']))
        else:
            return None
        aid = secrets.token_hex(3)
        fut = asyncio.get_running_loop().create_future()
        self.asks[aid] = fut
        self.status('asking you')
        self.send2('J', '1')
        self.send2('I', aid + '\x1f' + what[:200])
        try:
            answer = await asyncio.wait_for(fut, 300)
        except asyncio.TimeoutError:
            answer = 'deny'
        finally:
            self.asks.pop(aid, None)
        self.tui.out('  \xa6 %s\n' % {'once': 'yes, this once', 'always': 'yes, and from now on', 'deny': 'no'}[answer])
        if answer == 'always':
            if name == 'run_command':
                self.allowed.add(word)
            else:
                self.allow_writes = True
        return None if answer in ('once', 'always') else 'The visitor declined this (Windows asked them first).'

    async def run_tool(self, u):
        t = self.tui
        inp = u.input
        bad = valid(u.name, inp)
        t.para(tool_title(u.name, inp if isinstance(inp, dict) else {}), BUL + ' ', '    ')
        if bad:
            t.out('  \xa6 ' + bad + '\n')
            return {'type': 'tool_result', 'tool_use_id': u.id, 'content': bad, 'is_error': True}
        if u.name == 'todo_write':
            items = inp['items']
            self.send2('L', '\r\n'.join(self.MARK[it['status']] + it['text'][:70] for it in items))
            doing = [it['text'] for it in items if it['status'] == 'in_progress']
            t.out('  \xa6 %d of %d done%s (card 2)\n' % (sum(it['status'] == 'done' for it in items), len(items),
                                                         ('; now ' + doing[0][:40]) if doing else ''))
            return {'type': 'tool_result', 'tool_use_id': u.id, 'content': 'The plan card now shows %d items.' % len(items)}
        no = await self.permitted(u.name, inp)
        if no:
            return {'type': 'tool_result', 'tool_use_id': u.id, 'content': no, 'is_error': True}
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
        """keep the Cardfile status card's countdown honest while someone waits; re-pause an idle machine"""
        while True:
            await asyncio.sleep(15)
            if (self.phase == 'ready' and not self.driver and not self.queue and not self.frozen
                    and time.time() - self.phase_t > 10):
                self.freeze()
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
            elif t == 'm':
                try:
                    M.mouse(s, int(m.get('x', 0)), int(m.get('y', 0)), int(m.get('b', 0)), bool(m.get('d')))
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
                    # signed: noVNC announces Extended Clipboard with a negative length
                    need = 8 + abs(struct.unpack('>i', buf[4:8])[0])
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
    except Exception as e:
        log('vnc proxy closed: %r' % e)
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
    if op in ('x', 'y', 'send2', 'out1', 'type', 'live'):
        M.thaw()
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
                                  'vnc': len(VNC_CLIENTS), 'frozen': M.frozen})
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
