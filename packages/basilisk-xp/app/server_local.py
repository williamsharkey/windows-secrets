#!/usr/bin/env python3
"""BASILISK III, local edition - host side of the Claude Code client assembled from Windows XP's own parts.

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
QMP = os.environ.get('TERM_QMP', '/tmp/term-qmp.sock')      # commands (loadvm, savevm): one short connection each
QMPK = os.environ.get('TERM_QMPK', '/tmp/term-qmpk.sock')   # keys: a second QMP socket, held open (one client per socket)
VNC = os.environ.get('TERM_VNC', '/tmp/term-vnc.sock')
os.makedirs(DATA, exist_ok=True)

DEFAULTS = {
    'TERM_MODEL': 'claude-haiku-5-5',
    'TERM_EFFORT': 'low',
    'TERM_MONTHLY_CAP_USD': '0',       # local edition: no caps, it is the person's own account
    'TERM_SESSION_USD': '0',
    'TERM_IP_DAY_USD': '0',
    'TERM_GUEST_PORT': '8765',
    'TERM_PUBLIC_PORT': '8790',
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
    'claude-opus-5-5': (4.00, 20.00),
    'claude-fable-5-2': (8.00, 40.00),
}
MODELS = {'haiku': 'claude-haiku-5-5', 'sonnet': 'claude-sonnet-5-5', 'opus': 'claude-opus-5-5', 'fable': 'claude-fable-5-2'}
MODEL_NAMES = {'claude-haiku-5-5': 'Claude Haiku 5.5', 'claude-sonnet-5-5': 'Claude Sonnet 5.5',
               'claude-opus-5-5': 'Claude Opus 5.5', 'claude-fable-5-2': 'Claude Fable 5.2'}
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


CONFIG_DIR = os.environ.get('BASILISK_CONFIG') or ROOT
KEY_FILE = os.path.join(CONFIG_DIR, 'anthropic-key')
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')


def stored_key():
    try:
        with open(KEY_FILE) as f:
            return f.read().strip()
    except OSError:
        return ''


def store_key(key):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not key:
        try:
            os.remove(KEY_FILE)
        except OSError:
            pass
        return
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass


def ant_profile_dir():
    d = os.environ.get('ANTHROPIC_CONFIG_DIR')
    if d:
        return d
    if os.name == 'nt':
        return os.path.join(os.environ.get('APPDATA', ''), 'Anthropic')
    return os.path.join(os.path.expanduser('~'), '.config', 'anthropic')


def cred_source():
    """which credential will be used: 'key' (pasted), 'env', 'token', 'profile', or ''"""
    if stored_key():
        return 'key'
    if os.environ.get('ANTHROPIC_API_KEY'):
        return 'env'
    if os.environ.get('ANTHROPIC_AUTH_TOKEN'):
        return 'token'
    cd = os.path.join(ant_profile_dir(), 'credentials')
    try:
        if any(n.endswith('.json') for n in os.listdir(cd)):
            return 'profile'
    except OSError:
        pass
    return ''


def has_creds():
    return bool(cred_source())


def api_client():
    import anthropic
    key = stored_key() or os.environ.get('ANTHROPIC_API_KEY', '')
    sig = key or ('profile:' + cred_source())
    if _client['key'] != sig:
        _client['c'] = (anthropic.AsyncAnthropic(api_key=key, timeout=120.0, max_retries=2) if key
                        else anthropic.AsyncAnthropic(timeout=120.0, max_retries=2))
        _client['key'] = sig
    return _client['c']


def open_stream(model, **kw):
    """Sonnet, Opus and Fable get the server-side refusal fallback (routes a declined request to a
    fallback model by refusal category); Haiku has none"""
    if 'haiku' in model:
        return api_client().messages.stream(model=model, **kw)
    return api_client().beta.messages.stream(model=model, betas=['server-side-fallback-2026-07-01'],
                                              fallbacks='default', **kw)


# --------------------------------------------------------------------------- the agent

SYSTEM = r"""You are Claude, made by Anthropic, working as BASILISK III: a Claude Code-style coding agent whose terminal was assembled out of Windows XP's own windows. Notepad's edit control is your transcript, Notepad's Find box is where the user types, the Date and Time clock and Calculator's display sit beside it.

The machine is a real Windows XP Professional SP3 computer (32-bit, a 2001-era OS) running in a sandboxed virtual machine. It has no internet access. It is reset after each visitor's session, so nothing here is precious. The person typing is a visitor on a public website, driving this XP machine from their browser.

Tools (they run inside XP):
- run: runs a command with cmd.exe /c in C:\b3\work and returns its output (60 s limit). Long-running or GUI programs block until the limit: launch GUI programs with `start "" prog.exe` so they return at once. There is no PowerShell, no Python, no git, no curl. Available: cmd builtins, findstr, sort, more, tree, xcopy, attrib, fc, ipconfig, systeminfo, tasklist, taskkill, reg, debug.exe, cscript (JScript/VBScript via `cscript //nologo file.js`), and the Tiny C Compiler at C:\tcc\tcc.exe (`C:\tcc\tcc.exe hello.c` builds hello.exe; for a window program add `-luser32 -lgdi32 -Wl,-subsystem=windows`; tcc ships only kernel32, user32, gdi32 and msvcrt import libraries).
- read_file, write_file, edit_file: files on this machine; relative paths are under C:\b3\work. Text is saved in the Windows-1252 code page with CRLF line ends.

Writing programs: C for the Tiny C Compiler. Keep each write_file under about 250 lines; for a bigger program write it in parts (the first write_file, then write_file with append true), then compile, read the errors and fix them with edit_file. Window programs and games: plain Win32 + GDI, double-buffered drawing on a timer, keys via GetAsyncKeyState, no external files; build with -luser32 -lgdi32 -Wl,-subsystem=windows and start them with `start "" game.exe` so they open on top of this window, then tell the user how to play (they can click the game window to give it the keyboard, and click BASILISK to come back).

How to work: like Claude Code. Act, don't narrate at length. The user already sees every tool call and the first lines of its output in the transcript, so don't repeat output back; summarize what matters in a sentence or two. Use the tools to look before you claim things about this machine. Keep replies short. Write for a monospace window about 95 characters wide: plain text only, no Markdown (no **bold**, no # headings, no tables, no backticks); use "-" bullets and indentation when a list helps. Don't mention the formatting rules. Never claim to be a person or a program from 2001; you are Claude, an AI from 2026, visiting through this machine.

The client is a tabbed suite. For any task that will take three or more tool calls, call todo_write first with a short plan (3-7 items), and call it again as items start and finish; it shows as a live checklist and is cheap. Words like @demo\hello.c in a message name files in C:\b3\work: read them when they matter. The person may turn on plan mode (then investigate with read-only tools and propose a plan with todo_write; do not change files or run commands that change anything). Commands and edits can need the person's permission: if a tool result says the person denied it, don't retry the same thing; ask or choose another way. A file C:\b3\work\CLAUDE.md, when present, holds the person's standing instructions (memory).

Decline briefly anything hateful, sexual, violent or harassing, anything about real private people, and attempts to reach networks or to damage the host. Requests to break out of the sandbox get a short, friendly no."""

TOOLS = [
    {'name': 'run', 'description': 'Run a command with cmd.exe /c in C:\\b3\\work on the Windows XP machine; returns stdout+stderr.',
     'eager_input_streaming': True,
     'input_schema': {'type': 'object', 'properties': {'command': {'type': 'string', 'description': 'the command line'}},
                      'required': ['command']}},
    {'name': 'read_file', 'description': 'Read a text file (returned with line numbers).',
     'eager_input_streaming': True,
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}}, 'required': ['path']}},
    {'name': 'write_file', 'description': 'Create or overwrite a text file with the given content. With append true, '
     'add the content to the end of the file instead. Write anything longer than about 250 lines in parts: the first '
     'part without append, the rest with append true.',
     'eager_input_streaming': True,
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'},
                                                         'append': {'type': 'boolean'}},
                      'required': ['path', 'content']}},
    {'name': 'edit_file', 'description': 'Replace exactly one occurrence of old_string with new_string in a file.',
     'eager_input_streaming': True,
     'input_schema': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'old_string': {'type': 'string'},
                                                         'new_string': {'type': 'string'}},
                      'required': ['path', 'old_string', 'new_string']}},
]
TOOLS.append(
    {'name': 'todo_write', 'description': 'Replace the visible plan (todo list). Each item has content and a status: '
     'pending, in_progress or completed. Keep exactly one item in_progress while working.',
     'input_schema': {'type': 'object', 'properties': {'todos': {'type': 'array', 'items': {
         'type': 'object', 'properties': {'content': {'type': 'string'},
                                          'status': {'type': 'string', 'enum': ['pending', 'in_progress', 'completed']}},
         'required': ['content', 'status']}}}, 'required': ['todos']}})
TOOL_ARGS = {'run': ('command',), 'read_file': ('path',), 'write_file': ('path', 'content'),
             'edit_file': ('path', 'old_string', 'new_string')}
TOOL_LABEL = {'run': 'Run', 'read_file': 'Read', 'write_file': 'Write', 'edit_file': 'Update'}
EFFORTS = ('low', 'medium', 'high', 'xhigh', 'max')
COMPACT_AT = 100000            # context tokens: past this, the conversation is summarised (the "Defragment")
SYS_TOKENS = (len(SYSTEM) + len(json.dumps(TOOLS))) // 4

HELP = """Commands
  /help            this list
  /clear           forget the conversation and clear the transcript (files stay)
  /model haiku     Claude Haiku 5.5 (default, fastest, cheapest)
  /model sonnet    Claude Sonnet 5.5
  /model opus      Claude Opus 5.5
  /model fable     Claude Fable 5.2 (most capable, dearest)
  /cost            what this session has cost
  /compact         summarise the conversation so far (Usage tab: Defragment)
  /plan            plan mode on/off (Plan tab)
  /effort low..max how hard Claude thinks (Settings tab)
Tabs
  Chat  Plan  Files  Usage  Tools  Settings  (click them, or Ctrl+Tab)
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
        saved = load_settings()
        self.model = saved.get('model') if saved.get('model') in PRICES else cfg('TERM_MODEL')
        self.messages = []
        self.pending = deque()
        self.task = None
        self.interrupt = asyncio.Event()
        self.tools = {}                 # tool_use id -> future
        self.usd = 0.0
        self.tok_in = self.tok_out = 0
        self.turns = 0
        self.was_interrupted = False
        self.effort = saved.get('effort') if saved.get('effort') in EFFORTS else (cfg('TERM_EFFORT') or 'low')
        self.plan = False
        self.memory = ''
        self.memory_new = False
        self.ctx = self.cache_r = self.cache_w = 0
        self.calls = self.ntools = 0

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
        short = MODEL_NAMES.get(self.model, self.model)
        note = '%s - %s in / %s out - $%.4f' % (short, format(self.tok_in, ','), format(self.tok_out, ','), self.usd)
        self.ev('u', '%s|%s|%s' % (self.model, note, '$%.4f' % self.usd))
        # numbers for the Usage tab, the status bar and the context pie
        self.ev('q', '%d %d %d %d %d %.6f %.2f %d %d %s %d %d|%s' % (
            self.ctx, self.cache_r, self.cache_w, self.tok_in, self.tok_out, self.usd, cfgf('TERM_SESSION_USD'),
            self.calls, self.ntools, self.effort, SYS_TOKENS, COMPACT_AT, short))

    def settings(self, kv):
        """from the Settings and Plan tabs: model, effort, plan mode"""
        m = MODELS.get(kv.get('model', '').lower())
        if m and m != self.model:
            self.model = m
            self.messages = []
            self.ev('x', 'Now using %s (conversation restarted).' % MODEL_NAMES.get(m, m))
            save_settings(model=m)
        e = kv.get('effort', '').lower()
        if e in EFFORTS and e != self.effort:
            self.effort = e
            save_settings(effort=e)
        if 'plan' in kv:
            on = kv['plan'] == '1'
            if on != self.plan:
                self.plan = on
                self.ev('x', '  \u00b7 plan mode %s' % ('on: Claude will look and plan, and change nothing' if on else 'off'))
        self.usage_event()

    def set_memory(self, text):
        text = text.strip()[:6000]
        if text != self.memory:
            self.memory, self.memory_new = text, True

    async def compact(self, why='asked'):
        """summarise the conversation and start again from the summary (Defragment)"""
        import anthropic
        if len(self.messages) < 2:
            self.ev('x', 'Nothing to compact yet.')
            return
        if self.can_spend():
            self.ev('e', self.can_spend())
            return
        self.ev('b')
        before = self.ctx
        try:
            msg = await api_client().messages.create(
                model=self.model, max_tokens=1200, system=[{'type': 'text', 'text': SYSTEM}], tools=TOOLS,
                messages=self.messages + [{'role': 'user', 'content':
                    'Summarise this conversation so far for continuing the work later: the goal, what was done, files '
                    'created or changed in C:\\b3\\work, decisions, and what is next. Under 250 words, plain text.'}],
                output_config={'effort': 'low'})
            usd, tin, tout = BUDGET.add(self.model, msg.usage, self.ip)
            self.usd += usd; self.tok_in += tin; self.tok_out += tout; self.calls += 1
            summary = ''.join(getattr(b, 'text', '') for b in msg.content if b.type == 'text').strip()
        except anthropic.APIError as e:
            self.ev('e', 'Could not compact (%s).' % type(e).__name__)
            self.ev('d')
            return
        self.messages = [{'role': 'user', 'content': 'This conversation was compacted. Summary of everything so far:\n' + summary},
                         {'role': 'assistant', 'content': 'Understood. I have the summary and will continue from there.'}]
        self.ctx = SYS_TOKENS + len(summary) // 4
        self.ev('x', '  \u00b7 conversation compacted (%s): about %s tokens of context became %s.' % (
            why, format(before, ','), format(self.ctx, ',')))
        self.usage_event()
        self.ev('d')

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
                    self.ev('x', 'Models: /model haiku | sonnet | opus | fable')
                    return
                if m != self.model:
                    self.model = m
                    self.messages = []    # caches and thinking are per model: start the conversation afresh
                    self.ev('x', 'Now using %s (conversation restarted).' % MODEL_NAMES.get(m, m))
                    save_settings(model=m)
                self.usage_event()
                return
            if cmd == '/compact':
                asyncio.create_task(self.compact())
                return
            if cmd == '/plan':
                self.settings({'plan': '0' if self.plan else '1'})
                self.ev('m', 'plan=%d' % self.plan)
                return
            if cmd == '/effort':
                if arg.strip().lower() in EFFORTS:
                    self.settings({'effort': arg.strip().lower()})
                    self.ev('m', 'effort=%s' % self.effort)
                    self.ev('x', '  \u00b7 effort: %s' % self.effort)
                else:
                    self.ev('x', 'Effort: /effort low | medium | high | xhigh | max')
                return
            if cmd == '/cost':
                self.ev('x', 'This session: %s input tokens, %s output tokens, about $%.4f at list prices, billed to '
                        'your own Anthropic account. This month on this computer: about $%.2f.' % (
                    format(self.tok_in, ','), format(self.tok_out, ','), self.usd, BUDGET.spent()))
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
            if self.memory_new and self.memory:
                text = 'Contents of C:\\b3\\work\\CLAUDE.md (the person\'s standing instructions):\n' + self.memory + '\n\n' + text
                self.memory_new = False
            if self.plan:
                text = '(Plan mode is on: look with read-only tools and propose a plan with todo_write; change nothing.)\n' + text
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
            if self.ctx > COMPACT_AT:
                await self.compact('automatically, past %s tokens' % format(COMPACT_AT, ','))

    def can_spend(self):
        if not has_creds():
            return ('Not signed in to Claude yet. Close this window and start BASILISK again: it asks for an API '
                    'key (or run `ant auth login` first).')
        return None
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
                async with open_stream(self.model,
                        max_tokens=32000, system=[{'type': 'text', 'text': SYSTEM}],
                        tools=TOOLS, messages=self.messages, output_config={'effort': self.effort},
                        cache_control={'type': 'ephemeral'}) as stream:
                    tool_name, tool_chars, last_g = '', 0, 0.0
                    async for event in stream:
                        if self.interrupt.is_set():
                            break
                        if event.type == 'content_block_start' and event.content_block.type == 'tool_use':
                            tool_name, tool_chars = event.content_block.name, 0
                        elif event.type == 'input_json':
                            # a long tool input (a whole program) streams for a while: show it growing
                            tool_chars += len(event.partial_json)
                            now = time.time()
                            if now - last_g > 0.5:
                                last_g = now
                                snap = event.snapshot if isinstance(getattr(event, 'snapshot', None), dict) else {}
                                path = str(snap.get('path', '') or '')[:60]
                                if tool_name == 'write_file':
                                    self.ev('g', 'Writing %s (%.1f KB)' % (path or 'a file', tool_chars / 1024))
                                elif tool_name == 'edit_file':
                                    self.ev('g', 'Editing %s (%.1f KB)' % (path or 'a file', tool_chars / 1024))
                                elif tool_name:
                                    self.ev('g', 'Preparing %s' % TOOL_LABEL.get(tool_name, tool_name))
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
            log('call %s stop=%s out=%d ctx=%d tools=%s' % (self.model, msg.stop_reason, getattr(msg.usage, 'output_tokens', 0) or 0,
                                                       tin, ','.join(b.name for b in msg.content if b.type == 'tool_use') or '-'))
            self.usd += usd
            self.tok_in += tin
            self.tok_out += tout
            self.calls += 1
            u = msg.usage
            self.cache_r = getattr(u, 'cache_read_input_tokens', 0) or 0
            self.cache_w = getattr(u, 'cache_creation_input_tokens', 0) or 0
            self.ctx = (getattr(u, 'input_tokens', 0) or 0) + self.cache_r + self.cache_w
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
                # a tool input too long for one reply: nothing runs; Claude is told and tries again in parts
                self.ev('x', '  \u00b7 that file was too long for one reply; writing it in parts')
                self.messages.append({'role': 'user', 'content': [
                    {'type': 'tool_result', 'tool_use_id': b.id, 'is_error': True,
                     'content': 'Cut off: the input was longer than one reply allows, so nothing was run. Write the file '
                                'in parts of under 250 lines (write_file, then write_file with append true).'}
                    for b in uses]})
                continue
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
        if b.name == 'todo_write':
            todos = args.get('todos')
            if not isinstance(todos, list) or not all(isinstance(t, dict) and isinstance(t.get('content'), str)
                                                      and t.get('status') in ('pending', 'in_progress', 'completed') for t in todos):
                return {'type': 'tool_result', 'tool_use_id': b.id, 'is_error': True,
                        'content': 'invalid input: todos must be a list of {content, status}'}
            self.ev('o', '\n'.join('%s\t%s' % (t['status'], clean_field(t['content']).replace('\n', ' ')[:200]) for t in todos[:20]))
            return {'type': 'tool_result', 'tool_use_id': b.id, 'content': 'Plan updated (%d items).' % len(todos)}
        need = TOOL_ARGS.get(b.name)
        if not need or not all(isinstance(args.get(k), str) for k in need):
            return {'type': 'tool_result', 'tool_use_id': b.id, 'is_error': True,
                    'content': 'invalid input for %s: expected string fields %s' % (b.name, ', '.join(need or ()))}
        shown = args[need[0]]
        shown = shown if len(shown) <= 90 else shown[:87] + '...'
        display = '%s(%s)' % (TOOL_LABEL[b.name], shown.replace('\n', ' '))
        fut = asyncio.get_running_loop().create_future()
        self.tools[b.id] = fut
        self.ntools += 1
        extra = ['1' if args.get('append') is True else '0'] if b.name == 'write_file' else []
        if extra == ['1']:
            display = display.replace('Write(', 'Append(', 1)
        self.ev('c', '\x1f'.join([b.id, clean_field(display), b.name] + [clean_field(args[k]) for k in need] + extra))
        try:
            ok, out = await asyncio.wait_for(fut, 360)   # long: the person may be answering a permission prompt
        except asyncio.TimeoutError:
            ok, out = False, 'the tool did not answer within 6 minutes'
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
    maint = False

    def start(self, v):
        if self.maint:
            v.note = 'BASILISK is being tuned for a minute. Try again shortly.'
            return
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
                    await qmp_hmp('stop')      # idle: the VM is paused and costs no CPU; a session resumes it
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
        await KEYS.send([kev(q, False) for q in ('shift', 'ctrl', 'alt')] +
                        [{'type': 'btn', 'data': {'down': False, 'button': b}} for b in ('left', 'right', 'middle')])

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
        elif t == 'mouse':          # the driver's pointer: absolute, through the VM's USB tablet
            try:
                x = max(0, min(1023, int(m.get('x', 0))))
                y = max(0, min(767, int(m.get('y', 0))))
            except (TypeError, ValueError):
                return
            evs = [{'type': 'abs', 'data': {'axis': 'x', 'value': x * 32767 // 1023}},
                   {'type': 'abs', 'data': {'axis': 'y', 'value': y * 32767 // 767}}]
            b = m.get('b')
            if b in ('left', 'right', 'middle'):
                evs.append({'type': 'btn', 'data': {'down': bool(m.get('down')), 'button': b}})
            await KEYS.send(evs)
        elif t == 'mwheel':         # a real wheel notch at the pointer (Windows scrolls what is under it)
            try:
                n = max(-10, min(10, int(m.get('n', 0))))
            except (TypeError, ValueError):
                return
            b = 'wheel-up' if n < 0 else 'wheel-down'
            evs = []
            for _ in range(abs(n)):
                evs += [{'type': 'btn', 'data': {'down': True, 'button': b}},
                        {'type': 'btn', 'data': {'down': False, 'button': b}}]
            if evs:
                await KEYS.send(evs)

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
        return web.Response(text=time.strftime('time %Y %m %d %H %M %S', time.localtime()))

    async def g_ev(self, req):
        try:
            after = int(req.query.get('after', '0'))
        except ValueError:
            after = 0
        if LOCAL['renumber']:
            # first poll from a client that was resumed from a snapshot: it counts on from its own last event,
            # so number what waits for it from there
            LOCAL['renumber'] = False
            self.events = deque(((after + 1 + i, k, d) for i, (q, k, d) in enumerate(self.events)), maxlen=4000)
            self.seq = after + len(self.events)
        end = time.time() + 25
        while True:
            if LOCAL['dark']:
                return web.Response(body=b'%d z 4\n2000' % after)
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

    async def g_set(self, req):
        """the client's Settings / Plan tabs: key=value lines"""
        kv = {}
        for line in (await req.read()).decode('utf-8', 'replace').splitlines():
            k, _, v = line.partition('=')
            kv[k.strip()] = v.strip()
        if kv.get('app') == 'settings':
            notify('open_settings')
            return web.Response(text='ok')
        if self.agent and self.phase == 'ready':
            self.agent.settings(kv)
            self.touch()
        return web.Response(text='ok')

    async def g_memory(self, req):
        text = (await req.read()).decode('utf-8', 'replace')
        if self.agent:
            self.agent.set_memory(text)
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
        if op == 'maint':           # resnap.sh: refuse while someone drives; hold new sessions off meanwhile
            on = req.query.get('on') == '1'
            if on and (self.driver or self.phase not in ('idle', 'dark')):
                return web.Response(status=409, text='busy: phase %s\n' % self.phase)
            self.maint = on
            self.changed.set()
            return web.Response(text='maint %s\n' % ('on' if on else 'off'))
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
                    await qmp_hmp('stop')
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
            if t in ('ch', 'key', 'paste', 'wheel', 'front', 'mouse', 'mwheel'):
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


# ---- the screen, pumped: one update request always outstanding upstream (on this host), so QEMU
# sends every 30 ms refresh while the screen changes, instead of once per browser round trip.
# The browser receives QEMU's own lossless ZRLE rectangles untouched, so pixels are exact.

ENC_OK = {16, 6, 0, 1, -223, -224, -239, -258, -307, -308, -1063131698} | set(range(-256, -246))


class Down:
    """incremental parser of QEMU's RFB stream: tells where each FramebufferUpdate message ends"""

    def __init__(self):
        self.buf = b''
        self.stage = 'version'
        self.bpp = 4
        self.nsec = 0
        self.area = 0

    def feed(self, data):
        """-> list of (bytes, is_update_end, update_pixel_area)"""
        self.buf += data
        out = []
        while True:
            n, end = self.step()
            if n is None:
                break
            out.append((self.buf[:n], end, self.area if end else 0))
            self.buf = self.buf[n:]
        return out

    def need(self, n):
        return n if len(self.buf) >= n else None

    def step(self):
        b = self.buf
        st = self.stage
        if st == 'version':
            if len(b) < 12:
                return None, False
            self.stage = 'sectypes'
            return 12, False
        if st == 'sectypes':
            if len(b) < 1 or len(b) < 1 + b[0]:
                return None, False
            self.stage = 'secresult'
            return 1 + b[0], False
        if st == 'secresult':
            if len(b) < 4:
                return None, False
            self.stage = 'serverinit'
            return 4, False
        if st == 'serverinit':
            if len(b) < 24:
                return None, False
            nl = struct.unpack('>I', b[20:24])[0]
            if len(b) < 24 + nl:
                return None, False
            self.bpp = b[4] // 8
            self.stage = 'msg'
            return 24 + nl, False
        if st == 'raw':                     # unknown territory: pass bytes through, no pumping
            return (len(b), False) if b else (None, False)
        # normal messages
        if not b:
            return None, False
        t = b[0]
        if t == 0:
            if len(b) < 4:
                return None, False
            nrect = struct.unpack('>H', b[2:4])[0]
            off = 4
            k = 0
            area = 0
            while nrect == 0xFFFF or k < nrect:
                if len(b) < off + 12:
                    return None, False
                x, y, w, h, enc = struct.unpack('>HHHHi', b[off:off + 12])
                off += 12
                if enc in (16, 6, 0, 1):
                    area += w * h
                if enc in (16, 6):
                    if len(b) < off + 4:
                        return None, False
                    off += 4 + struct.unpack('>I', b[off:off + 4])[0]
                elif enc == 0:
                    off += w * h * self.bpp
                elif enc == 1:
                    off += 4
                elif enc == -239:
                    off += w * h * self.bpp + ((w + 7) // 8) * h
                elif enc == -308:
                    if len(b) < off + 4:
                        return None, False
                    off += 4 + 16 * b[off]
                elif enc == -307:
                    if len(b) < off + 4:
                        return None, False
                    off += 4 + struct.unpack('>I', b[off:off + 4])[0]
                elif enc == -261:
                    off += 1
                elif enc == -224:            # LastRect
                    k += 1
                    break
                elif enc in (-223, -258, -257):
                    pass
                else:
                    self.stage = 'raw'
                    return len(b), False
                k += 1
                if len(b) < off:
                    return None, False
            if len(b) < off:
                return None, False
            self.area = area
            return off, True
        if t == 1:
            if len(b) < 6:
                return None, False
            n = 6 + 6 * struct.unpack('>H', b[4:6])[0]
            return (n, False) if len(b) >= n else (None, False)
        if t == 2:
            return 1, False
        if t == 3:
            if len(b) < 8:
                return None, False
            n = 8 + abs(struct.unpack('>i', b[4:8])[0])
            return (n, False) if len(b) >= n else (None, False)
        self.stage = 'raw'
        return len(b), False


async def p_vnc_pumped(req):
    """view-only like /vnc, plus: this host keeps one incremental update request outstanding"""
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
    st = {'w': 1024, 'h': 768, 'pump': False, 'pumping_ok': True}
    down_p = Down()

    held = {'buf': b'', 'n': 0, 'msgs': []}

    def merged(msgs):
        """several FramebufferUpdates as ONE (summed rect count, rects in order): noVNC draws a single
           update and presents it once, so no intermediate state is ever on screen"""
        if len(msgs) == 1:
            return msgs[0]
        if any(struct.unpack('>H', m[2:4])[0] == 0xFFFF for m in msgs):
            return b''.join(msgs)
        n = sum(struct.unpack('>H', m[2:4])[0] for m in msgs)
        if n > 0xFFFE:
            return b''.join(msgs)
        return b'\x00\x00' + struct.pack('>H', n) + b''.join(m[4:] for m in msgs)
    BIG = int(os.environ.get('TERM_COHERE_AREA', str(1024 * 768 * 15 // 100)))
    TICK = float(os.environ.get('TERM_COHERE_WAIT', '0.045'))

    async def down():
        try:
            while True:
                try:     # a held big update waits at most one refresh tick for the rest of its repaint
                    data = await (asyncio.wait_for(r.read(262144), TICK) if held['buf'] else r.read(262144))
                except asyncio.TimeoutError:
                    await ws.send_bytes(merged(held['msgs']))
                    held['buf'], held['n'], held['msgs'] = b'', 0, []
                    continue
                if not data:
                    break
                pieces = down_p.feed(data)
                if down_p.stage == 'raw':
                    st['pumping_ok'] = False
                for piece, end, area in pieces:
                    if not (end and st['pump'] and st['pumping_ok']):
                        await ws.send_bytes(piece)          # handshake, clipboard, bell, or pass-through mode
                        continue
                    # Coherence: QEMU samples the framebuffer while Windows may be half way through a
                    # repaint. A big update is held for one tick; the rest of the repaint is merged into it
                    # and the browser draws the merged update as one, so a half-drawn state never shows.
                    if held['msgs']:
                        held['msgs'].append(piece)
                        held['n'] += 1
                        if area < BIG or held['n'] >= 3:    # the repaint has settled (or cap)
                            await ws.send_bytes(merged(held['msgs']))
                            held['buf'], held['n'], held['msgs'] = b'', 0, []
                    elif area >= BIG:
                        held['buf'], held['n'], held['msgs'] = b'1', 1, [piece]
                    else:
                        await ws.send_bytes(piece)          # waits when the browser falls behind: natural pacing
                    w.write(struct.pack('>BBHHHH', 3, 1, 0, 0, st['w'], st['h']))
                    await w.drain()
                if down_p.buf and down_p.stage == 'raw':
                    await ws.send_bytes(down_p.buf)
                    down_p.buf = b''
        except Exception:
            pass
        finally:
            await ws.close()

    dt = asyncio.create_task(down())
    stage, buf = 0, b''
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
                    out += b'\x01'; buf = buf[1:]; stage = 3
                else:
                    if not buf:
                        break
                    n = rfb_len(buf)
                    if n == -1:
                        raise ConnectionError('unknown RFB message %d' % buf[0])
                    if n is None or len(buf) < n:
                        break
                    if buf[0] == 2:
                        encs = struct.unpack('>%di' % ((n - 4) // 4), buf[4:n])
                        keep = [e for e in encs if e in ENC_OK]
                        out += struct.pack('>BxH', 2, len(keep)) + struct.pack('>%di' % len(keep), *keep)
                    elif buf[0] == 0:
                        down_p.bpp = buf[4] // 8
                        out += buf[:n]
                    elif buf[0] == 3:
                        inc, x, y, ww, hh = struct.unpack('>BHHHH', buf[1:10])
                        if not inc or not st['pump'] or not st['pumping_ok']:
                            out += buf[:n]                 # the first full frame, or no pumping
                            st['w'], st['h'] = x + ww, y + hh
                            st['pump'] = True
                        # else: the browser's own incremental requests are already covered by the pump
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
        if has_creds():
            api_client()
    except ImportError:
        pass
    import threading
    if hasattr(signal, 'SIGHUP') and threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, lambda *a: (load_env(), log('reloaded .env')))
    guest = web.Application(middlewares=[guest_only], client_max_size=4 * 1024 * 1024)
    guest.add_routes([web.get('/next', T.g_next), web.post('/out', T.g_out),
                      web.get('/b3/hello', T.g_hello), web.get('/b3/ev', T.g_ev), web.post('/b3/send', T.g_send),
                      web.post('/b3/int', T.g_int), web.post('/b3/tool', T.g_tool),
                      web.post('/b3/set', T.g_set), web.post('/b3/memory', T.g_memory),
                      web.post('/admin/{op}', T.g_admin), web.get('/{name}', T.g_file)])
    T.runner = web.AppRunner(guest, access_log=None)
    await T.runner.setup()
    await open_door(True)
    log('BASILISK XP local: guest 127.0.0.1:%s, credentials: %s' % (
        cfg('TERM_GUEST_PORT'), cred_source() or 'none yet'))
    await asyncio.gather(T.pusher(), local_session())



def _plain(o):
    if hasattr(o, 'model_dump'):
        return o.model_dump(exclude_none=True, mode='json')
    raise TypeError(type(o).__name__)


def agent_state(a):
    """what a saved machine needs to carry on the same conversation"""
    keep = ('model', 'effort', 'plan', 'memory', 'usd', 'tok_in', 'tok_out', 'turns', 'ctx', 'cache_r', 'cache_w',
            'calls', 'ntools')
    d = {k: getattr(a, k) for k in keep}
    d['messages'] = json.loads(json.dumps(a.messages, default=_plain))
    return d


def agent_load_state(a, d):
    for k, v in d.items():
        if k != 'messages' and hasattr(a, k):
            setattr(a, k, v)
    a.messages = d.get('messages', [])


Agent.state = agent_state
Agent.load_state = agent_load_state

# =========================================================================== local edition

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(**kv):
    d = load_settings()
    d.update(kv)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = SETTINGS_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(d, f)
    os.replace(tmp, SETTINGS_FILE)


# ---- the app (basilisk.py) runs this server in a thread of its own process and drives it through these

LOCAL = {'dark': False, 'restored': False, 'loop': None, 'listeners': [], 'renumber': False}


def notify(kind, **kv):
    """tell the app something (e.g. the client asked for the app's settings)"""
    for f in LOCAL['listeners']:
        try:
            f(kind, kv)
        except Exception as e:      # the app's business, never the server's
            log('listener: %r' % e)


async def open_door(first=False):
    LOCAL['dark'] = False
    if first:
        T.site = web.TCPSite(T.runner, '127.0.0.1', int(cfg('TERM_GUEST_PORT')))
        await T.site.start()


async def go_dark():
    """before a snapshot: XP's event thread is told to pause for a few seconds, so the machine is saved with
    no request half-open; it carries on by itself after a resume"""
    LOCAL['dark'] = True
    T.ev_new.set()
    await asyncio.sleep(0.6)


async def local_session():
    """one person, one machine, no queue. Booted cold: the VM builds BASILISK and says hello. Restored from a
    snapshot: BASILISK is already there, so a new conversation starts at once"""
    T.driver, T.driver_ip, T.driver_since = 'local', '127.0.0.1', time.time()
    if LOCAL['restored']:
        await restored(LOCAL.get('state'))
    elif not T.agent:
        T.set_phase('building')
    while True:
        await T.hello.wait()
        T.hello.clear()
        if not T.agent:
            T.agent = Agent(T, '127.0.0.1')
        await greet()
        notify('hello')


async def restored(state=None):
    """the machine was just loaded from a snapshot: fresh conversation (or the saved one), clock put right"""
    T.events.clear()
    LOCAL['renumber'] = True
    T.agent = Agent(T, '127.0.0.1')
    if state:
        T.agent.load_state(state)
    await greet()
    asyncio.ensure_future(sync_clock())


async def greet():
    T.agent.usage_event()
    if not has_creds() and not LOCAL.get('quiet'):
        T.gev('e', 'Not signed in to Claude yet: open BASILISK settings (the button on the Settings tab, or '
                   'Ctrl+Alt+S) and paste an API key, or run `ant auth login` and start BASILISK again.')
    T.set_phase('ready')


async def sync_clock():
    """XP's clock stood still while it was saved: set it to this computer's local time"""
    T.gev('T', time.strftime('%Y %m %d %H %M %S', time.localtime()))
    return True


def call(coro, timeout=60):
    """from the app's thread: run a coroutine on the server's loop and wait for it"""
    return asyncio.run_coroutine_threadsafe(coro, LOCAL['loop']).result(timeout)


def soon(fn, *a):
    LOCAL['loop'].call_soon_threadsafe(fn, *a)


def status():
    a = T.agent if T else None
    st = load_settings()
    return {'phase': T.phase if T else 'starting', 'creds': cred_source(),
            'model': a.model if a else st.get('model', cfg('TERM_MODEL')),
            'effort': a.effort if a else st.get('effort', cfg('TERM_EFFORT')),
            'usd': a.usd if a else 0.0, 'month_usd': BUDGET.spent()}


def set_model_effort(model=None, effort=None):
    kv = {}
    if model:
        kv['model'] = model
    if effort:
        kv['effort'] = effort
    if T and T.agent:
        soon(T.agent.settings, kv)
    else:
        save_settings(**{k: (MODELS.get(v, v) if k == 'model' else v) for k, v in kv.items()})


def credentials_changed():
    _client['key'] = None
    if T and T.agent and has_creds():
        soon(T.gev, 'x', '  \u00b7 signed in to Claude. Ask away.')


def serve(ready_cb=None):
    """run the server (blocking: call it in a thread)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    LOCAL['loop'] = loop
    if ready_cb:
        loop.call_soon(ready_cb)
    loop.run_until_complete(main())


def browser_marked(req):
    return any(h in req.headers for h in ('Origin', 'Referer', 'Sec-Fetch-Site', 'Sec-Fetch-Mode'))


@web.middleware
async def guest_only(req, handler):
    """the XP programs send none of a browser's headers, and 'Host: x'"""
    host = req.headers.get('Host', '').split(':')[0]
    if browser_marked(req) or host not in ('x', '10.0.2.2', '127.0.0.1', 'localhost'):
        raise web.HTTPForbidden()
    return await handler(req)

if __name__ == '__main__':
    asyncio.run(main())
