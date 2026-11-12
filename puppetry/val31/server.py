#!/usr/bin/env python3
"""VALENTINE 3.11 - the host side.

A visitor's message becomes a job; VAL.EXE inside Windows for Workgroups 3.11 (DOSBox-X, COM1 = a
null-modem to 127.0.0.1:8774, served here) types it onto a real Cardfile card inside a heart of
Solitaire's hearts, repaints, and answers READY; we photograph the screen (Xvfb :41) and keep the
PNG for 24 hours under an unguessable id.

  public  127.0.0.1:8784   POST /make  GET /job/<id>  GET /img/<id>.png  GET /state
  guest   127.0.0.1:8774   the COM1 line (DOSBox-X connects to us once, at its start)
"""
import asyncio, json, os, re, secrets, subprocess, textwrap, time, unicodedata
from collections import deque
from aiohttp import web

ROOT = '/root/val31'
DATA = os.path.join(ROOT, 'data')
RES = os.path.join(DATA, 'results')
os.makedirs(RES, exist_ok=True)
DISPLAY = ':41'
SERIAL_PORT = 8774
PUBLIC_PORT = 8784
KEEP_S = 24 * 3600
ORIGINS = {'https://williamsharkey.com', 'https://www.williamsharkey.com', 'https://live.williamsharkey.com',
           'http://localhost:8000', 'http://127.0.0.1:8000'}
COLS, BODY_LINES = 39, 9          # Cardfile's card: 40 x 11; two lines go to the signature

# a short list of words a valentine won't carry (kind refusal; not exhaustive)
BLOCK = re.compile(r'\b(n[i1]gg(?:er|a)s?|f[a@]gg?ots?|k[i1]kes?|sp[i1]cs?|ch[i1]nks?|tr[a@]nn(?:y|ies)|retards?|'
                   r'kill\s+(?:your|ur)self|kys)\b', re.I)


def log(m):
    print(time.strftime('%H:%M:%S'), m, flush=True)


# ------------------------------------------------------------------ text for a 1993 machine

# Cardfile's card font has the Latin-1 letters but not cp1252's typographic extras
TYPO = {'\u2013': '-', '\u2014': '--', '\u2018': "'", '\u2019': "'", '\u201a': ',', '\u201c': '"', '\u201d': '"',
        '\u201e': '"', '\u2026': '...', '\u2022': '*', '\u2020': '+', '\u2122': '(TM)', '\u20ac': 'EUR',
        '\u2039': '<', '\u203a': '>', '\u02c6': '^', '\u02dc': '~', '\u0152': 'OE', '\u0153': 'oe',
        '\u0160': 'S', '\u0161': 's', '\u017d': 'Z', '\u017e': 'z', '\u0178': 'Y', '\u0192': 'f', '\u2030': '%o',
        '\u00a0': ' ', '\u2665': '<3', '\u2764': '<3', '\u0141': 'L', '\u0142': 'l', '\u0110': 'D', '\u0111': 'd',
        '\u0131': 'i', '\u00df': '\u00df'}


def to_ansi(s):
    """-> (text Cardfile can draw, list of characters it could not)"""
    s = ''.join(TYPO.get(c, c) for c in s)
    out, bad = [], []
    for ch in s:
        if ord(ch) < 0x80 or 0xa0 <= ord(ch) <= 0xff:
            out.append(ch)
            continue
        alt = ''.join(c for c in unicodedata.normalize('NFKD', ch) if not unicodedata.combining(c))
        if alt and all(ord(c) < 0x80 or 0xa0 <= ord(c) <= 0xff for c in alt):
            out.append(alt)
            continue
        bad.append(ch)
    return ''.join(out), bad


def name_width(s):
    """rough width of a name in the System font the Index dialog uses, in units where 'W' is 1.5"""
    w = 0.0
    for c in s:
        if c in 'WM':
            w += 1.5
        elif c in 'mw':
            w += 1.3
        elif c in " iljtf.,;:'!|I":
            w += 0.5
        elif c.isupper():
            w += 1.15
        else:
            w += 0.9
    return w


def clean_field(s, n):
    s = ''.join(c for c in (s or '') if c == '\n' or (ord(c) >= 32 and ord(c) != 127))
    s = s.replace('\r', '')
    return s[:n]


def wrap_card(msg):
    lines = []
    for para in msg.split('\n'):
        para = para.rstrip()
        if not para:
            lines.append('')
            continue
        lines.extend(textwrap.wrap(para, COLS, break_long_words=True, break_on_hyphens=True) or [''])
    while lines and not lines[-1]:
        lines.pop()
    while lines and not lines[0]:
        lines.pop(0)
    return lines


def check(body):
    """-> (job dict, None) or (None, kind message)"""
    to = clean_field(body.get('to'), 60).replace('\n', ' ').strip()
    frm = clean_field(body.get('from'), 60).replace('\n', ' ').strip()
    msg = clean_field(body.get('msg'), 600).strip()
    style = body.get('style', 0)
    style = style if style in (0, 1, 2) else 0
    if not msg:
        return None, 'Write a few words for the card first.'
    if len(msg) > 240:
        return None, 'Cardfile cards are small: keep it under 240 characters.'
    if len(to) > 24 or len(frm) > 30:
        return None, 'Names fit best under 24 characters.'
    if BLOCK.search(' '.join((to, msg, frm))):
        return None, "This card only carries kind words. Try saying it another way."
    if re.search(r'https?://|www\.', msg, re.I):
        return None, 'No links on a Cardfile card - just words.'
    parts = []
    for f in (to, msg, frm):
        t, bad = to_ansi(f)
        if bad:
            shown = ' '.join(sorted(set(bad))[:6])
            return None, 'Windows 3.11 has no glyphs for %s. Try plain letters (accents are fine).' % shown
        parts.append(t)
    to, msg, frm = parts
    if name_width('To ' + to) > 34:
        return None, "That name is a little wide for Cardfile's index line. Try a shorter one."
    lines = wrap_card(msg)
    if len(lines) > BODY_LINES:
        return None, 'That needs %d lines and the card holds %d. Shorten it a little.' % (len(lines), BODY_LINES)
    return {'to': to, 'lines': lines, 'from': frm, 'style': style}, None


# ------------------------------------------------------------------ limits

class Limits:
    def __init__(self):
        self.d = {}

    def ok(self, ip):
        dq = self.d.setdefault(ip, deque())
        now = time.time()
        while dq and dq[0] < now - 86400:
            dq.popleft()
        hour = [t for t in dq if t > now - 3600]
        if len(dq) >= 20:
            return False, dq[0] + 86400
        if len(hour) >= 6:
            return False, hour[0] + 3600
        return True, 0

    def note(self, ip):
        self.d.setdefault(ip, deque()).append(time.time())


LIMITS = Limits()

# ------------------------------------------------------------------ the line to Windows


class Line:
    def __init__(self):
        self.w = None
        self.hello = asyncio.Event()
        self.ready = {}            # job id -> Event
        self.pong = asyncio.Event()
        self.last_seen = 0

    async def on_connect(self, r, w):
        log('COM1 connected')
        if self.w:
            try:
                self.w.close()
            except Exception:
                pass
        self.w = w
        buf = b''
        try:
            while True:
                d = await r.read(1024)
                if not d:
                    break
                self.last_seen = time.time()
                buf += d
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    line = line.strip(b'\r').decode('cp1252', 'replace')
                    if line == 'HELLO':
                        self.hello.set()
                    elif line == 'PONG':
                        self.pong.set()
                    elif line.startswith('READY '):
                        ev = self.ready.get(line[6:].strip())
                        if ev:
                            ev.set()
                    elif line.startswith('DBG '):
                        log(line)
        finally:
            log('COM1 closed')
            if self.w is w:
                self.w = None
                self.hello.clear()

    async def send(self, text):
        if not self.w:
            raise RuntimeError('no line')
        self.w.write(text.encode('cp1252'))
        await self.w.drain()


LINE = Line()


def dbx(cmd):
    subprocess.run([os.path.join(ROOT, 'dbx.sh'), cmd], timeout=30)


async def capture(path):
    proc = await asyncio.create_subprocess_exec(
        'import', '-display', DISPLAY, '-window', 'root', '-depth', '8', 'png:' + path,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    _, err = await asyncio.wait_for(proc.communicate(), 20)
    if proc.returncode:
        raise RuntimeError('capture: %s' % err.decode()[:200])


# ------------------------------------------------------------------ jobs

JOBS = {}            # id -> dict(state, pos, t, err, ip)
QUEUE = deque()
WAKE = asyncio.Event()


def job_lines(jid, job):
    body = '\x01'.join(job['lines'])
    if job['from']:
        body += '\x01\x01' + ('- ' + job['from']).rjust(COLS)
    return ('JOB %s\r\nT:%s\r\nM:%s\r\nF:\r\nS:%d\r\nEND\r\n' % (jid, job['to'], body, job['style']))


async def worker():
    while True:
        while not QUEUE:
            WAKE.clear()
            await WAKE.wait()
        jid = QUEUE[0]
        j = JOBS.get(jid)
        if not j:
            QUEUE.popleft()
            continue
        j['state'] = 'working'
        t0 = time.time()
        try:
            for attempt in range(2):
                try:
                    if not LINE.hello.is_set():
                        await asyncio.wait_for(LINE.hello.wait(), 60)
                    ev = LINE.ready[jid] = asyncio.Event()
                    await LINE.send(job_lines(jid, j['job']))
                    await asyncio.wait_for(ev.wait(), 40)
                    await asyncio.sleep(0.5)        # let the last paint reach the framebuffer
                    path = os.path.join(RES, jid + '.png')
                    await capture(path)
                    j['state'] = 'done'
                    j['secs'] = round(time.time() - t0, 1)
                    log('job %s done in %.1fs' % (jid[:6], time.time() - t0))
                    break
                except (asyncio.TimeoutError, RuntimeError, OSError) as e:
                    log('job %s attempt %d failed: %r; restarting Windows' % (jid[:6], attempt, e))
                    LINE.hello.clear()
                    await asyncio.get_running_loop().run_in_executor(None, dbx, 'restart')
            else:
                j['state'] = 'error'
        finally:
            LINE.ready.pop(jid, None)
            QUEUE.popleft()
            j.pop('job', None)


async def line_watch():
    """DOSBox-X dials COM1 only once, at its start: if the line has been down a while, restart Windows"""
    down_since = time.time()
    while True:
        await asyncio.sleep(5)
        if LINE.hello.is_set():
            down_since = None
            continue
        if down_since is None:
            down_since = time.time()
        busy = bool(QUEUE) and JOBS.get(QUEUE[0], {}).get('state') == 'working'
        if not busy and time.time() - down_since > 20:
            log('COM1 silent for 20 s; restarting Windows')
            await asyncio.get_running_loop().run_in_executor(None, dbx, 'restart')
            down_since = time.time() + 40      # give it time to boot before trying again


async def janitor():
    while True:
        now = time.time()
        for jid, j in list(JOBS.items()):
            if now - j['t'] > KEEP_S:
                JOBS.pop(jid, None)
                try:
                    os.remove(os.path.join(RES, jid + '.png'))
                except OSError:
                    pass
        for f in os.listdir(RES):
            p = os.path.join(RES, f)
            if now - os.path.getmtime(p) > KEEP_S:
                os.remove(p)
        await asyncio.sleep(600)


# ------------------------------------------------------------------ public side

def client_ip(req):
    peer = req.remote or ''
    if peer == '127.0.0.1':
        xff = req.headers.get('X-Forwarded-For', '')
        if xff:
            return xff.split(',')[-1].strip()[:64] or peer
    return peer


@web.middleware
async def cors(req, handler):
    if req.method == 'OPTIONS':
        resp = web.Response()
    else:
        resp = await handler(req)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    return resp


async def p_make(req):
    o = req.headers.get('Origin')
    if o and o not in ORIGINS:
        raise web.HTTPForbidden()
    try:
        body = await req.json()
    except (ValueError, UnicodeDecodeError):
        return web.json_response({'ok': False, 'msg': 'That did not arrive in one piece. Try again.'})
    if not isinstance(body, dict):
        return web.json_response({'ok': False, 'msg': 'That did not arrive in one piece. Try again.'})
    job, why = check(body)
    if not job:
        return web.json_response({'ok': False, 'msg': why})
    ip = client_ip(req)
    local = req.remote == '127.0.0.1' and not req.headers.get('X-Forwarded-For')   # host-side tests; Caddy always sets XFF
    ok, until = (True, 0) if local else LIMITS.ok(ip)
    if not ok:
        return web.json_response({'ok': False, 'rest_until': until,
                                  'msg': 'Windows has made several valentines for you already. It can make more at %s UTC.'
                                         % time.strftime('%H:%M', time.gmtime(until))})
    if len(QUEUE) >= 30:
        return web.json_response({'ok': False, 'msg': 'A lot of valentines are in line. Try again in a minute.'})
    if not local:
        LIMITS.note(ip)
    jid = secrets.token_urlsafe(16)
    JOBS[jid] = {'state': 'queued', 't': time.time(), 'job': job}
    QUEUE.append(jid)
    WAKE.set()
    return web.json_response({'ok': True, 'id': jid, 'pos': len(QUEUE)})


async def p_job(req):
    jid = req.match_info['id']
    j = JOBS.get(jid)
    if not j:
        raise web.HTTPNotFound()
    out = {'state': j['state']}
    if j['state'] == 'queued':
        try:
            out['pos'] = list(QUEUE).index(jid)
        except ValueError:
            out['pos'] = 0
    if j['state'] == 'done':
        out['img'] = 'img/%s.png' % jid
        out['secs'] = j.get('secs')
    return web.json_response(out, headers={'Cache-Control': 'no-store'})


async def p_img(req):
    jid = req.match_info['id']
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,40}', jid):
        raise web.HTTPNotFound()
    path = os.path.join(RES, jid + '.png')
    if not os.path.isfile(path):
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers={'Cache-Control': 'private, max-age=86400'})


async def p_state(req):
    return web.json_response({'up': LINE.hello.is_set(), 'queue': len(QUEUE)})


async def main():
    srv = await asyncio.start_server(LINE.on_connect, '127.0.0.1', SERIAL_PORT)
    app = web.Application(middlewares=[cors], client_max_size=8 * 1024)
    app.add_routes([web.post('/make', p_make), web.route('OPTIONS', '/make', p_make),
                    web.get('/job/{id}', p_job), web.get('/img/{id}.png', p_img),
                    web.get('/state', p_state), web.get('/', lambda r: web.Response(text='VALENTINE 3.11\n'))])
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, '127.0.0.1', PUBLIC_PORT).start()
    log('COM1 line on 127.0.0.1:%d, public on 127.0.0.1:%d' % (SERIAL_PORT, PUBLIC_PORT))
    async with srv:
        await asyncio.gather(worker(), janitor(), line_watch())


if __name__ == '__main__':
    asyncio.run(main())
