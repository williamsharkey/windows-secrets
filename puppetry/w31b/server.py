#!/usr/bin/env python3
"""BASILISK 3.11 in the browser - the server half: only the conversation with Claude.

Windows for Workgroups 3.11 runs in the visitor's browser (js-dos / DOSBox-X in WebAssembly); everything
on screen and every keystroke stays there. This server holds each visitor's conversation, runs the Claude
tool loop, and asks the page to run the tools (the page hands them to BASILISK.EXE inside Windows and
sends the results back). No emulator here, so an idle server costs nothing.

  127.0.0.1:8785   /ws  (Caddy: live.williamsharkey.com/w31b/*)

page -> server   {t:'turn', text} {t:'result', id, status, text} {t:'int'} {t:'clear'} {t:'compact'}
                 {t:'settings', effort, length, ask, model} {t:'perm', id, answer: once|always|deny}
server -> page   {t:'begin'} {t:'text', d} {t:'end'} {t:'tool', id, name, input, title, quiet?}
                 {t:'usage', tin, tout, usd, ctx, ctxmax, day, daycap, month, monthcap, model, turns, cached}
                 {t:'plan', items:[{text, status}]} {t:'ask', id, title} {t:'note', text} {t:'done'}
The suite (puppetry/w31suite): five Cardfile cards - Chat, Plan (todo_write + permission prompts), Files
(CLAUDE.MD is read before each turn), Usage, Settings (effort, answer length, asking, model).
The API key is read from /root/stage/.env and never printed.
"""
import asyncio
import json
import os
import secrets
import time
from collections import deque

from aiohttp import web, WSMsgType

ROOT = '/root/w31b'
DATA = os.path.join(ROOT, 'data')
os.makedirs(DATA, exist_ok=True)

DEFAULTS = {
    'W31B_MODEL': 'claude-haiku-5-5',
    'W31B_EFFORT': 'low',
    'W31B_MONTHLY_CAP_USD': '10',
    'W31B_PORT': '8785',
    'W31B_TRUSTED_PROXY': '127.0.0.1',
    'W31B_ORIGINS': 'https://williamsharkey.com,https://www.williamsharkey.com,https://live.williamsharkey.com,'
                    'http://localhost:8077,http://127.0.0.1:8077',
    'W31B_IP_TURNS_HOUR': '60',
    'W31B_IP_USD_DAY': '1.00',
    'W31B_IP_SOCKETS': '4',
    'W31B_MODELS': 'claude-haiku-5-5,claude-sonnet-5-5',
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
    for path in ('/root/stage/.env', os.path.join(ROOT, '.env')):
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
        return self.spent() >= cfgf('W31B_MONTHLY_CAP_USD')

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
        self.turns, self.usd = {}, {}

    @staticmethod
    def _trim(dq, horizon):
        now = time.time()
        while dq and dq[0][0] < now - horizon:
            dq.popleft()
        return dq

    def turn_ok(self, ip):
        """-> 0 if fine, else epoch when they may ask again"""
        dq = self._trim(self.turns.setdefault(ip, deque()), 3600)
        if len(dq) >= cfgf('W31B_IP_TURNS_HOUR'):
            return dq[0][0] + 3600
        du = self._trim(self.usd.setdefault(ip, deque()), 86400)
        if sum(x for _, x in du) >= cfgf('W31B_IP_USD_DAY'):
            return du[0][0] + 86400
        return 0

    def turn_note(self, ip):
        self.turns.setdefault(ip, deque()).append((time.time(), 1))

    def usd_note(self, ip, usd):
        self.usd.setdefault(ip, deque()).append((time.time(), usd))

    def usd_today(self, ip):
        return sum(x for _, x in self._trim(self.usd.setdefault(ip, deque()), 86400))


LIMITS = Limits()

SYSTEM = """You are BASILISK 3.11: Claude, working as a coding agent (like Claude Code) on a Windows for \
Workgroups 3.11 machine. It is running right now inside the visitor's own web browser (an emulated 486 with \
64 MB, DOSBox-X compiled to WebAssembly), with no network and no internet. The visitor types into Notepad's \
Find box; your words appear in Notepad (80 columns, Fixedsys). BASILISK.EXE, a 16-bit program compiled on this \
machine a minute ago by Open Watcom from a Notepad file, runs your tools.

The machine:
- Drive C: is the only drive. Your working directory is C:\\B3\\WORK (put new files there). DOS 8.3 file names only.
- run_command runs one line through COMMAND.COM in a background DOS window with stdout captured (stderr is not; \
DOS can't redirect it). DIR, TYPE, TREE, FIND, MEM, VER, SET, COPY, MD, DEL, REN, ECHO and .BAT files work. One \
command per call: no &, && or ;, so run steps as separate calls, and each call starts again in C:\\B3\\WORK (a CD \
does not carry over; use paths). There is no MOVE: use COPY then DEL. wcl writes its .EXE to C:\\B3\\WORK unless \
you add -fe=DIR\\NAME.EXE. Never run interactive or full-screen programs (EDIT, QBASIC, MORE without input): they \
hang until the 60 s timeout. Windows programs can't be started from run_command.
- Open Watcom C is installed: compile DOS programs with   wcl -q -bt=dos -ms PROG.C   and Windows 3.1 programs with \
  wcl -q -bt=windows -l=windows -ml PROG.C   (WATCOM, PATH and INCLUDE are set). DOS .EXE output can be run and its \
output captured; a Windows .EXE can be built but not launched by you. Compiling in the browser takes a few seconds.
- Everything resets when the visitor reloads the page.

The screen is a tabbed suite made of real Windows 3.1 programs; the tabs are Cardfile cards: 1 Chat (this transcript), 2 Plan (a Notepad showing your plan: keep it with todo_write for any task of three or more steps, marking one item in_progress at a time and items done as you finish them), 3 Files (File Manager on C:\\B3\\WORK; the visitor can mention a file as @NAME; C:\\B3\\WORK\\CLAUDE.MD, if it exists, holds standing instructions and is given to you when it changes), 4 Usage, 5 Settings. The visitor may set Windows to ask before your commands run and may say no; if a tool result says the visitor declined, don't retry it, ask what they'd like instead.

How to answer: plain text only. No markdown: no headings, no bold or italics, no tables, no code fences (show code \
by writing it to a file, then mention the file). Short paragraphs, lines that read well at 80 columns, '-' for \
bullets. Be brief and do the work with tools rather than describing it. ASCII only. When the visitor just chats, \
chat back briefly and warmly; you can be playful about being Claude (from 2026) living inside 1993 software that \
is itself running inside a web page, but stay accurate about what you can do here. Decline briefly anything \
hateful, sexual, violent or harassing, or about real private people."""

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
        if len(c) > 120:
            return 'command is longer than DOS allows (keep it under 120 characters)'
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


def ascii7(s):
    s = (s.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
         .replace('\u2014', '--').replace('\u2013', '-').replace('\u2026', '...').replace('\u2022', '*')
         .replace('\u2192', '->').replace('\u2190', '<-'))
    return s.encode('cp1252', 'replace').decode('cp1252')


class Visitor:
    def __init__(self, ws, ip):
        self.ws, self.ip = ws, ip
        self.messages = []
        self.task = None
        self.results = {}
        self.asks = {}
        self.usage = {'in': 0, 'out': 0, 'usd': 0.0, 'ctx': 0, 'cached': 0, 'turns': 0}
        self.set = {'effort': cfg('W31B_EFFORT'), 'length': 'normal', 'ask': True, 'model': cfg('W31B_MODEL')}
        self.allowed = set()           # first words of commands the visitor said to always allow
        self.allow_writes = False
        self.claude_md = None          # the CLAUDE.MD text last given to Claude

    async def send(self, **m):
        try:
            await self.ws.send_json(m)
        except Exception:
            pass

    def settings(self, m):
        e = str(m.get('effort', ''))
        if e in EFFORTS:
            self.set['effort'] = e
        if str(m.get('length', '')) in LENGTHS:
            self.set['length'] = str(m['length'])
        self.set['ask'] = str(m.get('ask', 'ask')) != 'auto'
        allowed = [x.strip() for x in cfg('W31B_MODELS').split(',')]
        want = 'claude-sonnet-5-5' if str(m.get('model', '')) == 'sonnet' else cfg('W31B_MODEL')
        self.set['model'] = want if want in allowed else cfg('W31B_MODEL')

    async def report(self):
        model = self.set['model']
        await self.send(t='usage', tin=self.usage['in'], tout=self.usage['out'], usd=round(self.usage['usd'], 6),
                        ctx=self.usage['ctx'], ctxmax=CONTEXT.get(model, 1000000),
                        day=round(LIMITS.usd_today(self.ip), 6), daycap=cfgf('W31B_IP_USD_DAY'),
                        month=round(BUDGET.spent(), 6), monthcap=cfgf('W31B_MONTHLY_CAP_USD'),
                        model=model, effort=self.set['effort'], turns=self.usage['turns'], cached=self.usage['cached'])

    def bill(self, model, usage):
        usd, tin, tout = BUDGET.add(model, usage)
        LIMITS.usd_note(self.ip, usd)
        self.usage['in'] += tin
        self.usage['out'] += tout
        self.usage['usd'] += usd
        self.usage['cached'] += getattr(usage, 'cache_read_input_tokens', 0) or 0
        return usd, tin, tout

    async def windows(self, name, inp, quiet=False, wait=90):
        """ask the page (and BASILISK.EXE) to do something; -> (status, text)"""
        tid = secrets.token_hex(3)
        fut = asyncio.get_running_loop().create_future()
        self.results[tid] = fut
        await self.send(t='tool', id=tid, name=name, input={k: ascii7(v) for k, v in inp.items()},
                        title=ascii7(tool_title(name, inp)), quiet=quiet)
        try:
            return await asyncio.wait_for(fut, wait)
        except asyncio.TimeoutError:
            return 'err', 'no answer from BASILISK.EXE in time'
        finally:
            self.results.pop(tid, None)

    async def memory(self):
        """CLAUDE.MD in C:\\B3\\WORK, read through Windows; -> text to add to the turn when it changed"""
        st, text = await self.windows('read_file', {'path': 'CLAUDE.MD'}, quiet=True, wait=8)
        text = (text or '').strip() if st == 'ok' else ''
        if text == (self.claude_md or ''):
            return ''
        first = self.claude_md is None
        self.claude_md = text
        if not text:
            return '' if first else '[C:\\B3\\WORK\\CLAUDE.MD was removed.]\n\n'
        return '[Standing instructions from C:\\B3\\WORK\\CLAUDE.MD:]\n%s\n[end of CLAUDE.MD]\n\n' % text[:3000]

    async def turn(self, text):
        pending = None
        inflight = None
        model = self.set['model']
        try:
            mem = await self.memory()
            note = LENGTHS.get(self.set['length'], '')
            self.messages.append({'role': 'user', 'content': mem + text + ('\n\n(' + note + ')' if note else '')})
            self.usage['turns'] += 1
            for step in range(16):
                streamed = False
                async with api().messages.stream(
                        model=model, max_tokens=8000, system=SYSTEM, tools=TOOLS,
                        messages=self.messages, cache_control={'type': 'ephemeral'},
                        output_config={'effort': self.set['effort']}) as st:
                    t0 = time.time()
                    inflight = {'in': len(json.dumps(self.messages, default=str)) // 4 + 1500, 'out': 0}
                    async for ev in st:
                        if ev.type == 'text':
                            if not streamed:
                                await self.send(t='begin')
                                streamed = True
                            await self.send(t='text', d=ascii7(ev.text))
                            inflight['out'] += max(1, len(ev.text) // 4)
                        elif ev.type == 'input_json':
                            inflight['out'] += max(1, len(ev.partial_json) // 4)
                    msg = await st.get_final_message()
                inflight = None
                if streamed:
                    await self.send(t='end')
                usd, tin, tout = self.bill(model, msg.usage)
                self.usage['ctx'] = tin + tout
                await self.report()
                log('api %s %.1fs in=%d out=%d $%.5f stop=%s' % (model, time.time() - t0, tin, tout, usd, msg.stop_reason))
                self.messages.append({'role': 'assistant', 'content': msg.content})
                uses = [b for b in msg.content if b.type == 'tool_use']
                if msg.stop_reason == 'refusal':
                    await self.send(t='note', text='(Claude declined that one.)')
                    break
                if not uses:
                    break
                pending = uses
                if msg.stop_reason == 'max_tokens':
                    raise RuntimeError('a tool call was cut off')
                results = []
                for u in uses:
                    results.append(await self.run_tool(u))
                pending = None
                self.messages.append({'role': 'user', 'content': results})
            else:
                await self.send(t='note', text='(Stopping here: that was a lot of steps for one request.)')
        except asyncio.CancelledError:
            if inflight:      # an interrupted stream reports no usage: bill a conservative estimate
                class U:
                    input_tokens, output_tokens = inflight['in'], inflight['out'] + 50
                    cache_creation_input_tokens = cache_read_input_tokens = 0
                self.bill(model, U)
                await self.report()
            await self.send(t='note', text='Interrupted.')
            self.close_out(pending, 'interrupted by the user')
        except Exception as e:
            log('turn error: %r' % e)
            await self.send(t='note', text='Something went wrong on the line (%s). Try again.' % type(e).__name__)
            self.close_out(pending, 'not run')
        finally:
            for f in list(self.asks.values()):
                if not f.done():
                    f.set_result('deny')
            await self.send(t='done')

    def close_out(self, pending, why):
        """leave the history valid: every tool_use answered, and no dangling user turn"""
        if pending:
            self.messages.append({'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': u.id, 'content': why, 'is_error': True} for u in pending]})
        elif self.messages and self.messages[-1]['role'] == 'user':
            self.messages.append({'role': 'assistant', 'content': '(%s)' % why})

    async def permitted(self, name, inp):
        """-> None if it may run, else the reason it may not (the visitor said no)"""
        if not self.set['ask']:
            return None
        if name == 'run_command':
            word = inp.get('command', '').strip().split()[0].upper() if inp.get('command', '').strip() else ''
            if word in SAFE or word in self.allowed:
                return None
            what = inp['command']
        elif name == 'write_file':
            if self.allow_writes:
                return None
            what = 'write the file %s (%d characters)' % (inp.get('path', ''), len(inp.get('content', '')))
        else:
            return None
        aid = secrets.token_hex(3)
        fut = asyncio.get_running_loop().create_future()
        self.asks[aid] = fut
        await self.send(t='ask', id=aid, title=ascii7(what)[:200])
        try:
            answer = await asyncio.wait_for(fut, 300)
        except asyncio.TimeoutError:
            answer = 'deny'
        finally:
            self.asks.pop(aid, None)
        if answer == 'always':
            if name == 'run_command':
                self.allowed.add(word)
            else:
                self.allow_writes = True
        if answer in ('once', 'always'):
            return None
        return 'The visitor declined this (Windows asked them first).'

    async def run_tool(self, u):
        inp = u.input if isinstance(u.input, dict) else {}
        bad = valid(u.name, u.input)
        if bad:
            await self.send(t='tool', id='', name=u.name, input={}, title=tool_title(u.name, inp), error=bad)
            return {'type': 'tool_result', 'tool_use_id': u.id, 'content': bad, 'is_error': True}
        if u.name == 'todo_write':
            items = [{'text': ascii7(it['text'])[:70], 'status': it['status']} for it in inp['items']]
            await self.send(t='plan', items=items)
            return {'type': 'tool_result', 'tool_use_id': u.id, 'content': 'The plan card now shows %d items.' % len(items)}
        no = await self.permitted(u.name, inp)
        if no:
            await self.send(t='tool', id='', name=u.name, input={}, title=ascii7(tool_title(u.name, inp)), error='declined')
            return {'type': 'tool_result', 'tool_use_id': u.id, 'content': no, 'is_error': True}
        status, text = await self.windows(u.name, inp)
        return {'type': 'tool_result', 'tool_use_id': u.id, 'content': (text or '')[:3500] or '(no output)',
                'is_error': status != 'ok'}

    async def compact(self):
        """/compact: Claude summarizes the conversation so far, and the summary replaces it"""
        model = self.set['model']
        try:
            if len(self.messages) < 2:
                await self.send(t='note', text='Nothing to compact yet.')
                return
            ask = self.messages + [{'role': 'user', 'content':
                'Summarize this conversation for yourself so it can continue from the summary alone: what the '
                'visitor wants, what was done (files written, commands run, results), the current plan, and any '
                'open questions. Plain text, at most 200 words. No tools.'}]
            async with api().messages.stream(model=model, max_tokens=2000, system=SYSTEM, tools=TOOLS,
                                              messages=ask, output_config={'effort': 'low'}) as st:
                msg = await st.get_final_message()
            self.bill(model, msg.usage)
            summary = ''.join(b.text for b in msg.content if b.type == 'text').strip()
            if not summary:
                raise RuntimeError('empty summary')
            before = self.usage['ctx']
            self.messages = [{'role': 'user', 'content': '[Summary of the conversation so far]\n' + summary},
                             {'role': 'assistant', 'content': 'Understood; continuing from that summary.'}]
            self.usage['ctx'] = len(SYSTEM + summary) // 4 + 900
            await self.report()
            await self.send(t='note', text='Compacted: the conversation (%s tokens) is now a summary of about %d '
                                           'words. Claude keeps going from there.' % (format(before, ','), len(summary.split())))
        except asyncio.CancelledError:
            await self.send(t='note', text='Interrupted.')
        except Exception as e:
            log('compact error: %r' % e)
            await self.send(t='note', text='Could not compact just now (%s).' % type(e).__name__)
        finally:
            await self.send(t='done')


VISITORS = set()


def client_ip(req):
    peer = req.remote or ''
    if peer == cfg('W31B_TRUSTED_PROXY'):
        xff = req.headers.get('X-Forwarded-For', '')
        if xff:
            return xff.split(',')[-1].strip()[:64] or peer
    return peer


def origin_ok(req):
    o = req.headers.get('Origin')
    return not o or o in [x.strip() for x in cfg('W31B_ORIGINS').split(',')]


async def p_ws(req):
    if not origin_ok(req):
        raise web.HTTPForbidden()
    ws = web.WebSocketResponse(heartbeat=25, max_msg_size=16384)
    await ws.prepare(req)
    ip = client_ip(req)
    if sum(1 for v in VISITORS if v.ip == ip) >= cfgf('W31B_IP_SOCKETS'):
        await ws.close(code=4008, message=b'too many')
        return ws
    v = Visitor(ws, ip)
    VISITORS.add(v)
    await v.send(t='hello', model=cfg('W31B_MODEL'), live=bool(cfg('ANTHROPIC_API_KEY')) and not BUDGET.over())
    await v.report()
    rate = deque()
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            now = time.time()
            rate.append(now)
            while rate and rate[0] < now - 10:
                rate.popleft()
            if len(rate) > 100:
                continue
            try:
                m = json.loads(msg.data)
            except ValueError:
                continue
            t = m.get('t')
            if t == 'turn':
                text = str(m.get('text', ''))[:1000].strip()
                if not text or (v.task and not v.task.done()):
                    continue
                until = LIMITS.turn_ok(ip)
                if until:
                    await v.send(t='note', text='You have asked a lot in a short time, so BASILISK is resting for '
                                              'you. You can ask again at %s UTC.' % time.strftime('%H:%M', time.gmtime(until)))
                    await v.send(t='done')
                    continue
                if BUDGET.over() or not cfg('ANTHROPIC_API_KEY'):
                    await v.send(t='note', text='The line to Claude is quiet for the rest of the month (its budget '
                                              'is spent). Windows still works; come back next month to talk.')
                    await v.send(t='done')
                    continue
                LIMITS.turn_note(ip)
                v.task = asyncio.create_task(v.turn(text))
            elif t == 'result':
                fut = v.results.get(str(m.get('id', '')))
                if fut and not fut.done():
                    fut.set_result((str(m.get('status', 'err')), str(m.get('text', ''))[:4000]))
            elif t == 'int':
                if v.task and not v.task.done():
                    v.task.cancel()
            elif t == 'clear':
                if not (v.task and not v.task.done()):
                    v.messages = []
                    v.usage['ctx'] = 0
                    v.claude_md = None
                    await v.report()
            elif t == 'compact':
                if not (v.task and not v.task.done()) and not BUDGET.over() and not LIMITS.turn_ok(ip):
                    LIMITS.turn_note(ip)
                    v.task = asyncio.create_task(v.compact())
                else:
                    await v.send(t='done')
            elif t == 'settings':
                v.settings(m)
                await v.report()
            elif t == 'perm':
                fut = v.asks.get(str(m.get('id', '')))
                if fut and not fut.done():
                    a = str(m.get('answer', 'deny'))
                    fut.set_result(a if a in ('once', 'always', 'deny') else 'deny')
    finally:
        VISITORS.discard(v)
        if v.task and not v.task.done():
            v.task.cancel()
    return ws


@web.middleware
async def cors(req, handler):
    resp = await handler(req)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    return resp


async def p_state(req):
    return web.json_response({'visitors': len(VISITORS), 'live': bool(cfg('ANTHROPIC_API_KEY')) and not BUDGET.over()})


async def main():
    try:
        import anthropic  # noqa: F401
        if cfg('ANTHROPIC_API_KEY'):
            api()
    except ImportError:
        pass
    app = web.Application(middlewares=[cors], client_max_size=64 * 1024)
    app.add_routes([web.get('/ws', p_ws), web.get('/state', p_state),
                    web.get('/', lambda r: web.Response(text='BASILISK 3.11 (browser)\n'))])
    r = web.AppRunner(app, access_log=None)
    await r.setup()
    await web.TCPSite(r, '127.0.0.1', int(cfg('W31B_PORT'))).start()
    log('BASILISK 3.11 browser server on 127.0.0.1:%s, model %s, key %s, month $%.4f of $%s' % (
        cfg('W31B_PORT'), cfg('W31B_MODEL'), 'present' if cfg('ANTHROPIC_API_KEY') else 'absent',
        BUDGET.spent(), cfg('W31B_MONTHLY_CAP_USD')))
    await asyncio.Event().wait()


if __name__ == '__main__':
    asyncio.run(main())
