#!/usr/bin/env python3
"""BASILISK III - host side of the Claude Code client assembled from Windows XP's own parts.

Two faces, like the BASILISK LIVE theatre server (puppetry/live/server.py), which this borrows from:
  guest side  127.0.0.1:8771  <- the term VM's only network path (guestfwd 10.0.2.2:8765)
      /next /out          agent.exe command queue (spawns the build puppet)
      /b3/hello           the client finished assembling itself
      /b3/ev?after=N      long-poll: transcript events (text, tool calls, usage, notes)
      /b3/send /b3/int    the visitor's words / Esc
      /b3/tool?id=        a tool's result, run inside XP
  public side 127.0.0.1:8781  <- Caddy, live.williamsharkey.com/term/*
      /ws                 control: state, start, keys, paste, scroll
      /vnc                the screen: QEMU's VNC, proxied VIEW-ONLY (client key/pointer/clipboard dropped)
      /state

One driver at a time. Their keys go to the VM through QMP input-send-event; everyone else watches.
The Claude tool loop runs here; the four tools run inside XP and report back.
"""
import asyncio
import json
import os
import re
import secrets
import signal
import struct
import time
from collections import deque

from aiohttp import web, WSMsgType

ROOT = os.environ.get('TERM_ROOT', '/root/term')
ENVFILE = os.path.join(ROOT, '.env')
DATA = os.path.join(ROOT, 'data')
WWW = os.path.join(ROOT, 'www')
QMP = '/tmp/term-qmp.sock'          # commands (loadvm, savevm): one short connection each
QMPK = '/tmp/term-qmpk.sock'        # keys: a second QMP socket, held open (QMP serves one client per socket)
VNC = '/tmp/term-vnc.sock'
os.makedirs(DATA, exist_ok=True)

DEFAULTS = {
    'TERM_MODEL': 'claude-haiku-5-5',
    'TERM_EFFORT': 'low',
    'TERM_MONTHLY_CAP_USD': '25',
    'TERM_SESSION_USD': '0.60',        # one driver's session
    'TERM_IP_DAY_USD': '1.50',         # one address per day
    'TERM_GUEST_PORT': '8771',
    'TERM_PUBLIC_PORT': '8781',
    'TERM_TRUSTED_PROXY': '127.0.0.1',
    'TERM_ORIGINS': 'https://williamsharkey.com,https://www.williamsharkey.com,https://live.williamsharkey.com,'
                    'http://localhost:8000,http://127.0.0.1:8000',
    'TERM_LEASE': '600',               # seconds a driver keeps the wheel while others wait
    'TERM_IDLE': '240',                # seconds without a key or a reply before the session ends
    'TERM_GRACE': '45',                # a driver who reloads the page gets the wheel back
    'TERM_QUEUE_MAX': '30',
    'TERM_VIEWERS_MAX': '60',
    'TERM_SNAPSHOT': 'term-desk',
}
PRICES = {   # USD per million tokens: input, output (cache write 1.25x input, cache read 0.1x input)
    'claude-haiku-5-5': (0.10, 0.50),
    'claude-sonnet-5-5': (2.00, 10.00),
}
MODELS = {'haiku': 'claude-haiku-5-5', 'sonnet': 'claude-sonnet-5-5'}
_env = {}


def load_env():
    env = {}
    try:
        with open(ENVFILE) as f:
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


# --------------------------------------------------------------------------- spend

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

    def cap(self):
        return cfgf('TERM_MONTHLY_CAP_USD')

    def ip_today(self, ip):
        return self.d.get('ip', {}).get(time.strftime('%Y-%m-%d', time.gmtime()), {}).get(ip, 0.0)

    def add(self, model, usage, ip):
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
        day = time.strftime('%Y-%m-%d', time.gmtime())
        ipd = self.d.setdefault('ip', {})
        for k in list(ipd):
            if k != day:
                del ipd[k]
        ipd.setdefault(day, {})[ip] = round(ipd.get(day, {}).get(ip, 0.0) + usd, 6)
        tmp = self.path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(self.d, f, indent=1)
        os.replace(tmp, self.path)
        return usd, inp + cw + cr, out


BUDGET = Budget()

_client = {'key': None, 'c': None}


def api_client():
    import anthropic
    key = cfg('ANTHROPIC_API_KEY')
    if _client['key'] != key:
        _client['c'] = anthropic.AsyncAnthropic(api_key=key, timeout=60.0, max_retries=2)
        _client['key'] = key
    return _client['c']


# --------------------------------------------------------------------------- the agent

SYSTEM = r"""You are Claude, made by Anthropic, working as BASILISK III: a Claude Code-style coding agent whose terminal was assembled out of Windows XP's own windows. Notepad's edit control is your transcript, Notepad's Find box is where the user types, the Date and Time clock and Calculator's display sit beside it.

The machine is a real Windows XP Professional SP3 computer (32-bit, a 2001-era OS) running in a sandboxed virtual machine. It has no internet access. It is reset after each visitor's session, so nothing here is precious. The person typing is a visitor on a public website, driving this XP machine from their browser.

Tools (they run inside XP):
- run: runs a command with cmd.exe /c in C:\b3\work and returns its output (60 s limit). Long-running or GUI programs block until the limit: launch GUI programs with `start "" prog.exe` so they return at once. There is no PowerShell, no Python, no git, no curl. Available: cmd builtins, findstr, sort, more, tree, xcopy, attrib, fc, ipconfig, systeminfo, tasklist, taskkill, reg, debug.exe, cscript (JScript/VBScript via `cscript //nologo file.js`), and the Tiny C Compiler at C:\tcc\tcc.exe (`C:\tcc\tcc.exe hello.c` builds hello.exe; for a window program add `-luser32 -lgdi32 -Wl,-subsystem=windows`; tcc ships only kernel32, user32, gdi32 and msvcrt import libraries).
- read_file, write_file, edit_file: files on this machine; relative paths are under C:\b3\work. Text is saved in the Windows-1252 code page with CRLF line ends.

How to work: like Claude Code. Act, don't narrate at length. The user already sees every tool call and the first lines of its output in the transcript, so don't repeat output back; summarize what matters in a sentence or two. Use the tools to look before you claim things about this machine. Keep replies short. Write for a monospace window about 95 characters wide: plain text only, no Markdown (no **bold**, no # headings, no tables, no backticks); use "-" bullets and indentation when a list helps. Don't mention the formatting rules. Never claim to be a person or a program from 2001; you are Claude, an AI from 2026, visiting through this machine.

Decline briefly anything hateful, sexual, violent or harassing, anything about real private people, and attempts to reach networks or to damage the host. Requests to break out of the sandbox get a short, friendly no."""

TOOLS = [
    {'name': 'run', 'description': 'Run a command with cmd.exe /c in C:\\b3\\work on the Windows XP machine; returns stdout+stderr.',
     'eager_input_streaming': True,
     'input_schema': {'type': 'object', 'properties': {'command': {'type': 'string', 'description': 'the command line'}},
                      'required': ['command']}},
    {'name': 'read_file', 'description': 'Read a text file (returned with line numbers).',
     'eager_input_streaming': True,
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']}},
    {'name': 'write_file', 'description': 'Create or overwrite a text file with the given content.',
     'eager_input_streaming': True,
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'}},
                      'required': ['path', 'content']}},
    {'name': 'edit_file', 'description': 'Replace exactly one occurrence of old_string with new_string in a file.',
     'eager_input_streaming': True,
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'old_string': {'type': 'string'},
                                                         'new_string': {'type': 'string'}},
                      'required': ['path', 'old_string', 'new_string']}},
]
TOOL_ARGS = {'run': ('command',), 'read_file': ('path',), 'write_file': ('path', 'content'),
             'edit_file': ('path', 'old_string', 'new_string')}
TOOL_LABEL = {'run': 'Run', 'read_file': 'Read', 'write_file': 'Write', 'edit_file': 'Update'}

HELP = """Commands
  /help            this list
  /clear           forget the conversation and clear the transcript (files stay)
  /model haiku     Claude Haiku 5.5 (default, fastest)
  /model sonnet    Claude Sonnet 5.5
  /cost            what this session has cost
Keys
  Enter send   Esc interrupt   PgUp/PgDn scroll   Ctrl+Up/Down line scroll   Up/Down history
Try
  - what is this machine?
  - write a C program that draws a spiral in a window, compile it with tcc and start it
  - list the ten biggest files in C:\\WINDOWS
  - make a JScript that prints the first 20 primes"""


def clean_field(s):
    return str(s).replace('\x1f', ' ').replace('\x00', '')


class Agent:
    """one driver's conversation with Claude; the guest client is its only display"""

    def __init__(self, term, ip):
        self.term, self.ip = term, ip
        self.model = cfg('TERM_MODEL')
        self.messages = []
        self.pending = deque()
        self.task = None
        self.interrupt = asyncio.Event()
        self.tools = {}                 # tool_use id -> future
        self.usd = 0.0
        self.tok_in = self.tok_out = 0
        self.turns = 0
        self.was_interrupted = False

    hold = ''

    def plain(self, t):
        """the transcript is plain text: drop Markdown's backticks and bold markers as they stream"""
        t = (self.hold + t).replace('`', '').replace('**', '')
        self.hold = ''
        if t.endswith('*'):
            self.hold, t = '*', t[:-1]
        return t

    def ev(self, kind, data=''):
        self.term.gev(kind, data)

    def usage_event(self):
        short = 'Claude Haiku 5.5' if 'haiku' in self.model else 'Claude Sonnet 5.5'
        note = '%s - %s in / %s out - $%.4f' % (short, format(self.tok_in, ','), format(self.tok_out, ','), self.usd)
        self.ev('u', '%s|%s|%s' % (self.model, note, '$%.4f' % self.usd))

    def send(self, text):
        text = text.strip()[:8000]
        if not text:
            return
        self.term.touch()
        if text.startswith('/'):
            cmd, _, arg = text.partition(' ')
            cmd = cmd.lower()
            if cmd == '/help':
                self.ev('x', HELP)
                return
            if cmd == '/clear':
                self.messages = []
                self.pending.clear()
                self.ev('k')
                self.ev('x', 'Conversation cleared. Files in C:\\b3\\work are still there.')
                return
            if cmd == '/model':
                m = MODELS.get(arg.strip().lower())
                if not m:
                    self.ev('x', 'Models: /model haiku  or  /model sonnet')
                    return
                if m != self.model:
                    self.model = m
                    self.messages = []    # caches and thinking are per model: start the conversation afresh
                    self.ev('x', 'Now using %s (conversation restarted).' % m)
                self.usage_event()
                return
            if cmd == '/cost':
                self.ev('x', 'This session: %s input tokens, %s output tokens, $%.4f. Month so far: $%.2f of $%.0f.' % (
                    format(self.tok_in, ','), format(self.tok_out, ','), self.usd, BUDGET.spent(), BUDGET.cap()))
                return
        self.pending.append(text)
        if not self.task or self.task.done():
            self.task = asyncio.create_task(self.run_turns())

    def stop(self):
        self.interrupt.set()
        for f in self.tools.values():
            if not f.done():
                f.set_result((False, '[interrupted by the user]'))

    async def run_turns(self):
        while self.pending:
            text = self.pending.popleft()
            if self.was_interrupted:
                text = '(The previous response was interrupted by the user.)\n' + text
                self.was_interrupted = False
            self.messages.append({'role': 'user', 'content': text})
            self.interrupt.clear()
            self.ev('b')
            try:
                await self.loop()
            except Exception as e:      # never leave the client spinning
                log('turn failed: %r' % e)
                self.ev('e', 'Something went wrong talking to Claude (%s). Try again.' % type(e).__name__)
            self.ev('d')
            self.term.touch()

    def can_spend(self):
        if not cfg('ANTHROPIC_API_KEY'):
            return 'The line to Claude is not connected right now.'
        if BUDGET.spent() >= BUDGET.cap():
            return 'BASILISK has used its budget for this month. It will be back on the 1st.'
        if self.usd >= cfgf('TERM_SESSION_USD'):
            return 'This session has used its share. Start a new session to keep going.'
        if BUDGET.ip_today(self.ip) >= cfgf('TERM_IP_DAY_USD'):
            return "You've used today's share. Come back tomorrow (UTC)."
        return None

    async def loop(self):
        import anthropic
        for step in range(30):
            why = self.can_spend()
            if why:
                self.ev('e', why)
                if self.messages and self.messages[-1]['role'] == 'user':
                    self.messages.pop()
                return
            started_text = False
            parts = []
            try:
                async with api_client().messages.stream(
                        model=self.model, max_tokens=8000, system=[{'type': 'text', 'text': SYSTEM}],
                        tools=TOOLS, messages=self.messages, output_config={'effort': cfg('TERM_EFFORT')},
                        cache_control={'type': 'ephemeral'}) as stream:
                    async for event in stream:
                        if self.interrupt.is_set():
                            break
                        if event.type == 'content_block_start' and event.content_block.type == 'text':
                            started_text = False
                        elif event.type == 'text':
                            if not started_text:
                                self.ev('s')
                                started_text = True
                            parts.append(event.text)
                            shown = self.plain(event.text)
                            if shown:
                                self.ev('t', shown)
                        elif event.type == 'content_block_stop' and self.hold:
                            self.ev('t', self.hold)
                            self.hold = ''
                    if self.interrupt.is_set():
                        if ''.join(parts).strip():
                            self.messages.append({'role': 'assistant', 'content': ''.join(parts)})
                        self.was_interrupted = True
                        self.ev('x', '  [interrupted]')
                        return
                    msg = await stream.get_final_message()
            except ValueError:     # tool input JSON the SDK could not parse at all: re-issue the step
                continue
            except anthropic.RateLimitError:
                self.ev('e', 'Claude is busy right now; try again in a moment.')
                return
            except anthropic.APIStatusError as e:
                log('api status %s' % e.status_code)
                self.ev('e', 'Claude returned an error (%s).' % e.status_code)
                if self.messages and self.messages[-1]['role'] == 'user':
                    self.messages.pop()
                return
            except anthropic.APIConnectionError:
                self.ev('e', 'Could not reach Claude. Try again.')
                return
            usd, tin, tout = BUDGET.add(self.model, msg.usage, self.ip)
            self.usd += usd
            self.tok_in += tin
            self.tok_out += tout
            self.usage_event()
            self.messages.append({'role': 'assistant', 'content': msg.content})
            if msg.stop_reason == 'refusal':
                self.ev('e', 'Claude declined that request.')
                self.messages.pop()
                self.messages.pop()
                return
            uses = [b for b in msg.content if b.type == 'tool_use']
            if not uses:
                return
            if msg.stop_reason == 'max_tokens':
                self.ev('e', 'That reply ran past the length limit; ask for something smaller.')
                self.messages.append({'role': 'user', 'content': [
                    {'type': 'tool_result', 'tool_use_id': b.id, 'is_error': True,
                     'content': 'cut off at max_tokens; not run'} for b in uses]})
                return
            results = []
            for b in uses:          # in order, one at a time: a compile must not race the write before it
                results.append(await self.call_tool(b) if not self.interrupt.is_set() else
                               {'type': 'tool_result', 'tool_use_id': b.id, 'is_error': True, 'content': '[interrupted by the user]'})
            self.messages.append({'role': 'user', 'content': results})
            if self.interrupt.is_set():
                self.was_interrupted = True
                return
            if sum(len(json.dumps(m, default=str)) for m in self.messages[-6:]) > 400000:
                self.ev('e', 'The conversation is very long; use /clear to start fresh.')
                return

    async def call_tool(self, b):
        args = b.input if isinstance(b.input, dict) else {}
        need = TOOL_ARGS.get(b.name)
        if not need or not all(isinstance(args.get(k), str) for k in need):
            return {'type': 'tool_result', 'tool_use_id': b.id, 'is_error': True,
                    'content': 'invalid input for %s: expected string fields %s' % (b.name, ', '.join(need or ()))}
        shown = args[need[0]]
        shown = shown if len(shown) <= 90 else shown[:87] + '...'
        display = '%s(%s)' % (TOOL_LABEL[b.name], shown.replace('\n', ' '))
        fut = asyncio.get_running_loop().create_future()
        self.tools[b.id] = fut
        self.ev('c', '\x1f'.join([b.id, clean_field(display), b.name] + [clean_field(args[k]) for k in need]))
        try:
            ok, out = await asyncio.wait_for(fut, 120)
        except asyncio.TimeoutError:
            ok, out = False, 'the tool did not answer within 120 s'
        finally:
            self.tools.pop(b.id, None)
        self.term.touch()
        if len(out) > 30000:
            out = out[:15000] + '\n[... %d characters omitted ...]\n' % (len(out) - 30000) + out[-15000:]
        return {'type': 'tool_result', 'tool_use_id': b.id, 'is_error': not ok, 'content': out or '(no output)'}


# --------------------------------------------------------------------------- keys -> QMP

US_SHIFT = {')': '0', '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9',
            '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.', '?': '/', '~': '`'}
US_KEY = {'-': 'minus', '=': 'equal', '[': 'bracket_left', ']': 'bracket_right', '\\': 'backslash', ';': 'semicolon',
          "'": 'apostrophe', ',': 'comma', '.': 'dot', '/': 'slash', '`': 'grave_accent', ' ': 'spc'}
NAMED = {'Enter': 'ret', 'Backspace': 'backspace', 'Delete': 'delete', 'ArrowLeft': 'left', 'ArrowRight': 'right',
         'ArrowUp': 'up', 'ArrowDown': 'down', 'Home': 'home', 'End': 'end', 'PageUp': 'pgup', 'PageDown': 'pgdn',
         'Escape': 'esc', 'Tab': 'tab', 'Insert': 'insert'}
CTRL_OK = set('acxzy') | {'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End', 'Backspace', 'Delete'}


def char_keys(c):
    """-> (qcode, shift) for one printable ASCII character on a US layout, or None"""
    if 'a' <= c <= 'z' or '0' <= c <= '9':
        return c, False
    if 'A' <= c <= 'Z':
        return c.lower(), True
    if c in US_SHIFT:
        base = US_SHIFT[c]
        return (base if base.isdigit() else US_KEY[base]), True
    if c in US_KEY:
        return US_KEY[c], False
    return None


def kev(q, down):
    return {'type': 'key', 'data': {'down': down, 'key': {'type': 'qcode', 'data': q}}}


class QMPKeys:
    """one persistent QMP connection for key injection (microseconds per key)"""

    def __init__(self):
        self.r = self.w = None
        self.lock = asyncio.Lock()

    async def _open(self):
        self.r, self.w = await asyncio.wait_for(asyncio.open_unix_connection(QMPK), 3)
        await self.r.readline()
        self.w.write(b'{"execute":"qmp_capabilities"}\n')
        await self.w.drain()
        await self.r.readline()
        asyncio.create_task(self._drain(self.r))

    async def _drain(self, r):
        try:
            while await r.readline():
                pass
        except Exception:
            pass

    async def send(self, events):
        async with self.lock:
            for attempt in (0, 1):
                try:
                    if not self.w or self.w.is_closing():
                        await self._open()
                    self.w.write(json.dumps({'execute': 'input-send-event', 'arguments': {'events': events}}).encode() + b'\n')
                    await self.w.drain()
                    return
                except Exception as e:
                    self.w = None
                    if attempt:
                        log('qmp keys: %r' % e)


KEYS = QMPKeys()


async def qmp_hmp(command, timeout=60):
    r, w = await asyncio.wait_for(asyncio.open_unix_connection(QMP), 5)
    try:
        await asyncio.wait_for(r.readline(), 5)
        w.write(b'{"execute":"qmp_capabilities"}\n')
        await w.drain()
        await asyncio.wait_for(r.readline(), 5)
        w.write(json.dumps({'execute': 'human-monitor-command', 'arguments': {'command-line': command}}).encode() + b'\n')
        await w.drain()
        while True:
            line = json.loads(await asyncio.wait_for(r.readline(), timeout))
            if 'return' in line or 'error' in line:
                return line
    finally:
        w.close()


# --------------------------------------------------------------------------- the terminal (sessions, queue, guest)

class Viewer:
    def __init__(self, ws, ip, tok):
        self.ws, self.ip, self.tok = ws, ip, tok
        self.note = ''


class Term:
    def __init__(self):
        self.phase = 'idle'           # idle | building | ready | ending | dark
        self.phase_t = time.time()
        self.viewers = set()
        self.queue = []               # tokens waiting
        self.tok_ip = {}
        self.driver = None            # token
        self.driver_ip = None
        self.driver_since = 0
        self.driver_gone = 0          # when the driver's last socket closed
        self.last_touch = time.time()
        self.agent = None
        self.events = deque(maxlen=4000)
        self.seq = 0
        self.ev_new = asyncio.Event()
        self.hello = asyncio.Event()
        self.agent_q = deque()
        self.agent_out = asyncio.Queue()
        self.agent_lock = asyncio.Lock()
        self.changed = asyncio.Event()
        self.runner = None
        self.sessions_today = {}
        tok = os.path.join(DATA, 'admin.token')
        if not os.path.exists(tok):
            with open(tok, 'w') as f:
                f.write(secrets.token_hex(16))
            os.chmod(tok, 0o600)
        self.admin_token = open(tok).read().strip()
        self.vnc_viewers = 0

    # ---- state
    def set_phase(self, p):
        if p != self.phase:
            log('phase %s -> %s' % (self.phase, p))
            self.phase, self.phase_t = p, time.time()
            self.changed.set()

    def touch(self):
        self.last_touch = time.time()

    def public(self, v=None):
        now = time.time()
        st = {'t': 'state', 'phase': self.phase, 'since': self.phase_t, 'now': now,
              'viewers': len(self.viewers), 'queue': len(self.queue),
              'driving': bool(self.driver), 'line': 'live' if cfg('ANTHROPIC_API_KEY') and BUDGET.spent() < BUDGET.cap() else 'quiet'}
        if self.driver:
            lease_end = self.driver_since + cfgf('TERM_LEASE') if self.queue else 0
            idle_end = self.last_touch + cfgf('TERM_IDLE')
            st['ends'] = min(x for x in (lease_end, idle_end) if x)
        if v is not None:
            st['you'] = 'driver' if v.tok == self.driver else ('queued' if v.tok in self.queue else 'watcher')
            if v.tok in self.queue:
                st['pos'] = self.queue.index(v.tok) + 1
            st['note'] = v.note
        return st

    async def broadcast(self):
        for v in list(self.viewers):
            try:
                await v.ws.send_json(self.public(v))
            except Exception:
                self.viewers.discard(v)

    # ---- guest events
    def gev(self, kind, data=''):
        self.seq += 1
        self.events.append((self.seq, kind, data.encode('utf-8', 'replace') if isinstance(data, str) else data))
        self.ev_new.set()

    # ---- visitors
    def start(self, v):
        if self.phase == 'dark':
            v.note = 'The machine is resting. Try again in a few minutes.'
            return
        if v.tok == self.driver or v.tok in self.queue:
            return
        if any(self.tok_ip.get(t) == v.ip for t in self.queue) or (self.driver and self.driver_ip == v.ip):
            v.note = 'You already have a turn coming.'
            return
        day = time.strftime('%Y-%m-%d')
        n = self.sessions_today.get((day, v.ip), 0)
        if n >= 12:
            v.note = "That's a lot of sessions today. Watch a while; the wheel frees up tomorrow."
            return
        if len(self.queue) >= cfgf('TERM_QUEUE_MAX'):
            v.note = 'The line is long right now. Watch a while and try again.'
            return
        if BUDGET.ip_today(v.ip) >= cfgf('TERM_IP_DAY_USD'):
            v.note = "You've used today's share of Claude. Come back tomorrow (UTC)."
            return
        self.tok_ip[v.tok] = v.ip
        self.queue.append(v.tok)
        v.note = ''
        self.changed.set()
        if not self.runner or self.runner.done():
            self.runner = asyncio.create_task(self.run_queue())

    def leave(self, v):
        if v.tok in self.queue:
            self.queue.remove(v.tok)
        if v.tok == self.driver:
            self.driver_gone = 1 - time.time()     # ends now (negative marks a deliberate leave)
        self.changed.set()

    def present(self, tok):
        return any(v.tok == tok for v in self.viewers)

    # ---- the session loop
    async def run_queue(self):
        while self.queue:
            tok = self.queue.pop(0)
            if not self.present(tok):
                continue
            try:
                await self.session(tok)
            except Exception as e:
                log('session failed: %r' % e)
            self.driver = self.driver_ip = None
            if self.agent:
                self.agent.stop()
                self.agent = None
            await self.release_keys()
            if not self.queue:
                try:
                    self.set_phase('ending')
                    await self.reset()
                    self.set_phase('idle')
                except Exception as e:
                    log('reset failed: %r' % e)
                    self.set_phase('dark')

    async def reset(self):
        t = time.time()
        res = await qmp_hmp('loadvm ' + cfg('TERM_SNAPSHOT'))
        ret = res.get('return', '')
        if 'error' in res or (isinstance(ret, str) and 'rror' in ret):
            raise RuntimeError('loadvm: %r' % res)
        await qmp_hmp('cont')
        self.agent_q.clear()
        log('reset in %.2fs' % (time.time() - t))

    async def agent_run(self, cmd, timeout=20):
        async with self.agent_lock:
            while not self.agent_out.empty():
                self.agent_out.get_nowait()
            self.agent_q.append(cmd)
            try:
                return await asyncio.wait_for(self.agent_out.get(), timeout)
            finally:
                self.agent_q.clear()

    async def session(self, tok):
        ip = self.tok_ip.get(tok, '?')
        day = time.strftime('%Y-%m-%d')
        self.sessions_today = {k: v for k, v in self.sessions_today.items() if k[0] == day}
        self.sessions_today[(day, ip)] = self.sessions_today.get((day, ip), 0) + 1
        self.driver, self.driver_ip, self.driver_since = tok, ip, time.time()
        self.driver_gone = 0
        self.touch()
        self.set_phase('building')
        built = False
        for attempt in range(2):
            await self.reset()
            await asyncio.sleep(0.4)
            self.events.clear()
            self.seq = 0
            self.hello.clear()
            try:
                # the snapshot holds the build puppet waiting for Ctrl+Alt+Shift+F12: press it through QMP
                # (no network, so nothing stranded by the restore can delay it)
                await KEYS.send([kev('ctrl', True), kev('alt', True), kev('shift', True), kev('f12', True),
                                 kev('f12', False), kev('shift', False), kev('alt', False), kev('ctrl', False)])
                if attempt:      # second try: the old way, through the agent
                    out = await self.agent_run(r'spawn C:\p\puppet.exe b3', 40)
                    if 'spawned' not in out:
                        raise RuntimeError(out)
                await asyncio.wait_for(self.hello.wait(), 75)
                built = True
                break
            except Exception as e:
                log('build attempt %d failed: %r' % (attempt, e))
        if not built:
            self.set_phase('dark')
            await asyncio.sleep(30)
            return
        self.agent = Agent(self, ip)
        self.agent.usage_event()
        self.touch()
        self.set_phase('ready')
        warned = False
        while True:
            await asyncio.sleep(1)
            now = time.time()
            if self.driver_gone < 0:
                log('driver left')
                break
            if self.driver_gone and not self.present(tok) and now - self.driver_gone > cfgf('TERM_GRACE'):
                log('driver gone')
                break
            if self.present(tok):
                self.driver_gone = 0
            elif not self.driver_gone:
                self.driver_gone = now
            busy = self.agent.task and not self.agent.task.done()
            if busy:
                self.touch()
            idle_left = self.last_touch + cfgf('TERM_IDLE') - now
            lease_left = (self.driver_since + cfgf('TERM_LEASE') - now) if self.queue else 1e9
            left = min(idle_left, lease_left)
            if left < 45 and not warned:
                self.gev('x', '  \u00b7 this session ends in %d seconds%s' % (
                    int(left), ' (someone is waiting)' if lease_left < idle_left else ' unless you type something'))
                warned = True
            if left > 60:
                warned = False
            if left <= 0:
                log('session over (%s)' % ('lease' if lease_left <= idle_left else 'idle'))
                self.gev('x', '  \u00b7 session over. Thank you for visiting.')
                await asyncio.sleep(2.5)
                break

    async def release_keys(self):
        await KEYS.send([kev(q, False) for q in ('shift', 'ctrl', 'alt')])

    # ---- driver input
    async def key(self, v, m):
        if v.tok != self.driver or self.phase != 'ready':
            return
        self.touch()
        t = m.get('t')
        if t == 'ch':
            c = str(m.get('c', ''))[:1]
            if not c:
                return
            k = char_keys(c)
            if k is None:                    # anything a US keyboard can't type goes in by paste
                if ord(c) >= 32:
                    self.gev('p', c)
                return
            q, shift = k
            evs = ([kev('shift', True)] if shift else []) + [kev(q, True), kev(q, False)] + ([kev('shift', False)] if shift else [])
            await KEYS.send(evs)
        elif t == 'key':
            name = str(m.get('k', ''))
            ctrl, shift = bool(m.get('ctrl')), bool(m.get('shift'))
            if name in NAMED:
                q = NAMED[name]
                if ctrl and name not in CTRL_OK:
                    return
            elif ctrl and len(name) == 1 and name.lower() in CTRL_OK:
                q = name.lower()
            else:
                return
            evs = []
            if ctrl:
                evs.append(kev('ctrl', True))
            if shift:
                evs.append(kev('shift', True))
            evs += [kev(q, True), kev(q, False)]
            if shift:
                evs.append(kev('shift', False))
            if ctrl:
                evs.append(kev('ctrl', False))
            await KEYS.send(evs)
        elif t == 'paste':
            text = str(m.get('text', ''))[:4000]
            if text:
                self.gev('p', text)
        elif t == 'wheel':
            try:
                n = max(-30, min(30, int(m.get('n', 0))))
            except (TypeError, ValueError):
                return
            if n:
                self.gev('w', str(n))
        elif t == 'front':
            self.gev('f')

    # ---- guest endpoints
    async def g_next(self, req):
        if self.agent_q:
            return web.Response(text=self.agent_q.popleft())
        return web.Response(text='')

    async def g_out(self, req):
        self.agent_out.put_nowait((await req.read()).decode('cp1252', 'replace'))
        return web.Response(text='ok')

    async def g_hello(self, req):
        self.events.clear()
        self.seq = 0
        self.hello.set()
        log('client assembled')
        return web.Response(text=time.strftime('time %Y %m %d %H %M %S', time.gmtime()))

    async def g_ev(self, req):
        try:
            after = int(req.query.get('after', '0'))
        except ValueError:
            after = 0
        end = time.time() + 25
        while True:
            out = [e for e in self.events if e[0] > after]
            if out:
                break
            self.ev_new.clear()
            try:
                await asyncio.wait_for(self.ev_new.wait(), max(0.1, end - time.time()))
            except asyncio.TimeoutError:
                return web.Response(body=b'')
        body = b''.join(b'%d %s %d\n' % (s, k.encode(), len(d)) + d for s, k, d in out[:400])
        return web.Response(body=body)

    async def g_send(self, req):
        text = (await req.read()).decode('utf-8', 'replace')
        if self.agent and self.phase == 'ready':
            self.agent.send(text)
        return web.Response(text='ok')

    async def g_int(self, req):
        if self.agent:
            self.agent.stop()
        self.touch()
        return web.Response(text='ok')

    async def g_tool(self, req):
        tid = req.query.get('id', '')
        body = (await req.read()).decode('utf-8', 'replace')
        ok, _, out = body.partition('\n')
        if self.agent and tid in self.agent.tools and not self.agent.tools[tid].done():
            self.agent.tools[tid].set_result((ok.strip() == '1', out))
        return web.Response(text='ok')

    async def g_file(self, req):
        name = os.path.basename(req.match_info.get('name', ''))
        path = os.path.join(WWW, name)
        if name and os.path.isfile(path):
            return web.FileResponse(path)
        return web.Response(status=404, text='not found')

    async def g_admin(self, req):
        if req.query.get('token') != self.admin_token:
            raise web.HTTPForbidden()
        op = req.match_info['op']
        if op == 'run':
            cmd = (await req.read()).decode()
            if not cmd.startswith(('get ', 'spawn ')):
                cmd = '(' + cmd + ')'
            try:
                return web.Response(text=await self.agent_run(cmd, float(req.query.get('timeout', '60'))))
            except asyncio.TimeoutError:
                return web.Response(text='(timeout)\n')
        if op == 'hmp':
            res = await qmp_hmp((await req.read()).decode())
            return web.Response(text=str(res.get('return', res)) + '\n')
        if op == 'testdrive':       # maintenance: talk to the client without a visitor session
            self.agent = Agent(self, 'admin')
            self.set_phase('ready')
            self.agent.usage_event()
            return web.Response(text='ok\n')
        if op == 'status':
            return web.json_response({'phase': self.phase, 'viewers': len(self.viewers), 'vnc': self.vnc_viewers,
                                      'queue': len(self.queue), 'spent': BUDGET.spent(), 'cap': BUDGET.cap()})
        raise web.HTTPNotFound()

    async def watchdog(self):
        """a dark machine tries to come back by itself"""
        while True:
            await asyncio.sleep(60)
            if self.phase == 'dark' and not self.driver:
                try:
                    await self.reset()
                    self.set_phase('idle')
                    if self.queue and (not self.runner or self.runner.done()):
                        self.runner = asyncio.create_task(self.run_queue())
                except Exception as e:
                    log('still dark: %r' % e)

    async def pusher(self):
        while True:
            try:
                await asyncio.wait_for(self.changed.wait(), 5)
            except asyncio.TimeoutError:
                pass
            self.changed.clear()
            await self.broadcast()
            await asyncio.sleep(0.2)


T = None


# --------------------------------------------------------------------------- public side

def client_ip(req):
    peer = req.remote or ''
    if peer == cfg('TERM_TRUSTED_PROXY'):
        xff = req.headers.get('X-Forwarded-For', '')
        if xff:
            return xff.split(',')[-1].strip()[:64] or peer
    return peer


def origin_ok(req):
    o = req.headers.get('Origin')
    return not o or o in [x.strip() for x in cfg('TERM_ORIGINS').split(',')]


async def p_ws(req):
    if not origin_ok(req):
        raise web.HTTPForbidden()
    ws = web.WebSocketResponse(heartbeat=25, max_msg_size=16384)
    await ws.prepare(req)
    ip = client_ip(req)
    if sum(1 for v in T.viewers if v.ip == ip) >= 8:
        await ws.close(code=4008, message=b'too many')
        return ws
    tok = re.sub(r'[^a-zA-Z0-9]', '', req.query.get('tok', ''))[:32] or secrets.token_hex(8)
    v = Viewer(ws, ip, tok)
    T.viewers.add(v)
    T.changed.set()
    stamps = deque()
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            now = time.time()
            stamps.append(now)
            while stamps and stamps[0] < now - 1:
                stamps.popleft()
            if len(stamps) > 200:         # far beyond typing speed: a runaway script, not a person
                continue
            try:
                m = json.loads(msg.data)
            except ValueError:
                continue
            t = m.get('t')
            if t in ('ch', 'key', 'paste', 'wheel', 'front'):
                await T.key(v, m)
            elif t == 'start':
                T.start(v)
                T.changed.set()
            elif t == 'leave':
                T.leave(v)
            elif t == 'ping':
                await ws.send_json(T.public(v))
    finally:
        T.viewers.discard(v)
        T.changed.set()
    return ws


# RFB client->server messages: (type) -> fixed length, or a function of the buffer
def rfb_len(buf):
    t = buf[0]
    if t == 0:
        return 20
    if t == 2:
        return 4 + 4 * struct.unpack('>H', buf[2:4])[0] if len(buf) >= 4 else None
    if t == 3:
        return 10
    if t == 4:
        return 8
    if t == 5:
        return 6
    if t == 6:      # ClientCutText; a negative length is the extended-clipboard form, |length| bytes follow
        return 8 + abs(struct.unpack('>i', buf[4:8])[0]) if len(buf) >= 8 else None
    if t == 255:
        if len(buf) < 2:
            return None
        if buf[1] == 0:
            return 12
        if buf[1] == 1:
            if len(buf) < 4:
                return None
            return 10 if struct.unpack('>H', buf[2:4])[0] == 2 else 4
    return -1


PASS = {0, 2, 3}      # SetPixelFormat, SetEncodings, FramebufferUpdateRequest; everything else is dropped


async def p_vnc(req):
    """the screen, view-only: client keys, pointer and clipboard never reach QEMU"""
    if not origin_ok(req):
        raise web.HTTPForbidden()
    if T.vnc_viewers >= cfgf('TERM_VIEWERS_MAX'):
        raise web.HTTPServiceUnavailable()
    ws = web.WebSocketResponse(protocols=('binary',), max_msg_size=1 << 16, heartbeat=30)
    await ws.prepare(req)
    try:
        r, w = await asyncio.open_unix_connection(VNC)
    except OSError:
        await ws.close()
        return ws
    T.vnc_viewers += 1

    async def down():
        try:
            while True:
                b = await r.read(65536)
                if not b:
                    break
                await ws.send_bytes(b)
        except Exception:
            pass
        finally:
            await ws.close()

    dt = asyncio.create_task(down())
    stage = 0          # 0 version (12), 1 security choice (1), 2 ClientInit (1), 3 messages
    buf = b''
    try:
        async for msg in ws:
            if msg.type != WSMsgType.BINARY:
                continue
            buf += msg.data
            out = b''
            while True:
                if stage == 0:
                    if len(buf) < 12:
                        break
                    out += buf[:12]; buf = buf[12:]; stage = 1
                elif stage == 1:
                    if len(buf) < 1:
                        break
                    out += buf[:1]; buf = buf[1:]; stage = 2
                elif stage == 2:
                    if len(buf) < 1:
                        break
                    out += b'\x01'; buf = buf[1:]; stage = 3        # always a shared session
                else:
                    if not buf:
                        break
                    n = rfb_len(buf)
                    if n == -1:
                        raise ConnectionError('unknown RFB message %d' % buf[0])
                    if n is None or len(buf) < n:
                        break
                    if buf[0] == 2:      # SetEncodings: lossless only (crisp text), no Tight/JPEG
                        encs = struct.unpack('>%di' % ((n - 4) // 4), buf[4:n])
                        keep = [e for e in encs if e not in (7, -260) and not (-32 <= e <= -23)]
                        if os.environ.get('TERM_RFB_DEBUG'):
                            log('rfb encodings asked %s kept %s' % (list(encs), keep))
                        out += struct.pack('>BxH', 2, len(keep)) + struct.pack('>%di' % len(keep), *keep)
                    elif buf[0] in PASS:
                        out += buf[:n]
                    if os.environ.get('TERM_RFB_DEBUG'):
                        log('rfb client msg %d len %d %s' % (buf[0], n, 'pass' if buf[0] in PASS else 'drop'))
                    buf = buf[n:]
            if len(buf) > 1 << 20:
                break
            if out:
                w.write(out)
                await w.drain()
    except Exception:
        pass
    finally:
        T.vnc_viewers -= 1
        dt.cancel()
        w.close()
    return ws


async def p_state(req):
    return web.json_response(T.public())


@web.middleware
async def cors(req, handler):
    resp = await handler(req)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    return resp


async def main():
    global T
    T = Term()
    try:
        import anthropic  # noqa: F401
        if cfg('ANTHROPIC_API_KEY'):
            api_client()
    except ImportError:
        pass
    signal.signal(signal.SIGHUP, lambda *a: (load_env(), log('reloaded .env')))
    guest = web.Application(client_max_size=4 * 1024 * 1024)
    guest.add_routes([web.get('/next', T.g_next), web.post('/out', T.g_out),
                      web.get('/b3/hello', T.g_hello), web.get('/b3/ev', T.g_ev), web.post('/b3/send', T.g_send),
                      web.post('/b3/int', T.g_int), web.post('/b3/tool', T.g_tool),
                      web.post('/admin/{op}', T.g_admin), web.get('/{name}', T.g_file)])
    pub = web.Application(middlewares=[cors], client_max_size=64 * 1024)
    pub.add_routes([web.get('/ws', p_ws), web.get('/vnc', p_vnc), web.get('/state', p_state),
                    web.get('/', lambda r: web.Response(text='BASILISK III\n'))])
    r1, r2 = web.AppRunner(guest, access_log=None), web.AppRunner(pub, access_log=None)
    await r1.setup()
    await r2.setup()
    await web.TCPSite(r1, '127.0.0.1', int(cfg('TERM_GUEST_PORT'))).start()
    await web.TCPSite(r2, '127.0.0.1', int(cfg('TERM_PUBLIC_PORT'))).start()
    log('guest 127.0.0.1:%s, public 127.0.0.1:%s, model %s, key %s, month $%.4f of $%s' % (
        cfg('TERM_GUEST_PORT'), cfg('TERM_PUBLIC_PORT'), cfg('TERM_MODEL'),
        'present' if cfg('ANTHROPIC_API_KEY') else 'absent', BUDGET.spent(), cfg('TERM_MONTHLY_CAP_USD')))
    await asyncio.gather(T.pusher(), T.watchdog())


if __name__ == '__main__':
    asyncio.run(main())
