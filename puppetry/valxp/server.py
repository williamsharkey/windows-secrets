#!/usr/bin/env python3
"""XP VALENTINE - the server.

Guest side (127.0.0.1:8773, reached by the VM as 10.0.2.2:8765):
    GET /next, POST /out      the in-guest agent.exe command channel
    GET /<file>               files from www/ (job.txt, valentine.exe)
Public side (127.0.0.1:8783, behind Caddy at live.williamsharkey.com/valxp/):
    POST /make                {to, from, msg} -> {id} or {error}
    GET  /job/<id>            {state: queued|rendering|done|error, pos, error}
    GET  /img/<id>.png        the finished valentine (private: the id is the key)
    GET  /state               queue length

One VM renders one valentine at a time: loadvm val-ready, hand the job to valentine.exe,
wait for it to say the screen has settled, take a QMP screendump, crop, save a PNG.
"""
import asyncio, json, os, re, secrets, time, unicodedata
from collections import deque
from aiohttp import web
from PIL import Image

ROOT = os.environ.get('VALXP_ROOT', '/root/valxp')
WWW = os.path.join(ROOT, 'www')
JOBS = os.path.join(ROOT, 'jobs')
QMP = '/tmp/valxp-qmp.sock'
GUEST_PORT, PUBLIC_PORT = 8773, 8783
SNAPSHOT = 'val-ready'
CROP = (80, 64, 944, 768)          # the heart and a margin of rose around it
KEEP_S = 24 * 3600
PER_HOUR, PER_DAY, QUEUE_MAX = 6, 20, 30
ORIGINS = {'https://williamsharkey.com', 'https://www.williamsharkey.com', 'https://live.williamsharkey.com',
           'http://localhost:8000', 'http://127.0.0.1:8000'}
os.makedirs(JOBS, exist_ok=True)


def log(m):
    print(time.strftime('%H:%M:%S'), m, flush=True)


# --------------------------------------------------------------------------- words in

HEARTS = set('\u2764\u2665\u2661\U0001F495\U0001F496\U0001F497\U0001F498\U0001F499\U0001F49A\U0001F49B\U0001F49C'
             '\U0001F49D\U0001F49E\U0001F49F\U0001F493\U0001F48C\U0001F48B\U0001F60D\U0001F618\U0001F970\U0001F339'
             '\u2763\U0001F5A4\U0001F90D\U0001F90E\U0001F9E1')
# a short list, matched on whole words; the point is a kind no, not a lecture
BLOCK = re.compile(r'\b(' + '|'.join([
    'nigg\\w*', 'fagg?\\w*', 'kike\\w*', 'spic', 'chink\\w*', 'tranny\\w*', 'retard\\w*', 'cunt\\w*',
    'whore\\w*', 'slut\\w*', 'rape\\w*', 'raping', 'porn\\w*', 'cock\\w*', 'dick', 'pussy', 'blowjob\\w*',
    'kill yourself', 'kys', 'nazi\\w*', 'hitler',
]) + r')\b', re.I)


def renderable(ch):
    """keep what Times New Roman on XP can draw: Latin, Greek, Cyrillic, common punctuation, the heart"""
    o = ord(ch)
    if ch in HEARTS:
        return '\u2665'
    if o < 32 or 0x7f <= o < 0xa0:
        return ''
    if o < 0x250 or 0x370 <= o < 0x530 or 0x2010 <= o <= 0x2027 or 0x2030 <= o <= 0x203a or o in (0x20ac, 0x2122, 0x2665):
        return ch
    if unicodedata.category(ch).startswith('Z'):
        return ' '
    return ''


def clean(s, limit, multiline=False):
    s = unicodedata.normalize('NFC', str(s or ''))
    out = []
    for ch in s:
        if ch == '\n' and multiline:
            out.append('\n')
            continue
        if ch in '\r\t\n':
            out.append(' ')
            continue
        out.append(renderable(ch))
    s = ''.join(out)
    s = re.sub(r'[ ]{2,}', ' ', s)
    if multiline:
        s = re.sub(r'\n{3,}', '\n\n', s)
        s = '\n'.join(line.strip() for line in s.split('\n'))
    s = s.strip()
    return s[:limit]


# --------------------------------------------------------------------------- the line

class Job:
    def __init__(self, ip, to, frm, msg):
        self.id = secrets.token_urlsafe(18)
        self.ip, self.to, self.frm, self.msg = ip, to, frm, msg
        self.state, self.error, self.t = 'queued', '', time.time()


class Studio:
    def __init__(self):
        self.jobs = {}
        self.line = deque()
        self.wake = asyncio.Event()
        self.agent_q = deque()
        self.agent_out = asyncio.Queue()
        self.agent_lock = asyncio.Lock()
        self.per_ip = {}
        self.current = None
        self.made = 0

    # -- limits ---------------------------------------------------------------
    def check(self, ip):
        now = time.time()
        dq = self.per_ip.setdefault(ip, deque())
        while dq and dq[0] < now - 86400:
            dq.popleft()
        hour = [t for t in dq if t > now - 3600]
        if len(dq) >= PER_DAY:
            return dq[0] + 86400
        if len(hour) >= PER_HOUR:
            return hour[0] + 3600
        return 0

    def position(self, job):
        if job.state != 'queued':
            return 0
        try:
            return list(self.line).index(job) + 1 + (1 if self.current else 0)
        except ValueError:
            return 0

    # -- the VM ---------------------------------------------------------------
    async def qmp(self, command):
        r, w = await asyncio.wait_for(asyncio.open_unix_connection(QMP), 5)
        try:
            await asyncio.wait_for(r.readline(), 5)
            w.write(b'{"execute":"qmp_capabilities"}\n')
            await w.drain()
            await asyncio.wait_for(r.readline(), 5)
            w.write(json.dumps({'execute': 'human-monitor-command', 'arguments': {'command-line': command}}).encode() + b'\n')
            await w.drain()
            while True:
                line = json.loads(await asyncio.wait_for(r.readline(), 60))
                if 'return' in line or 'error' in line:
                    return line
        finally:
            w.close()

    async def agent_run(self, cmd, timeout=20):
        async with self.agent_lock:
            while not self.agent_out.empty():
                self.agent_out.get_nowait()
            self.agent_q.append(cmd)
            try:
                return await asyncio.wait_for(self.agent_out.get(), timeout)
            finally:
                self.agent_q.clear()

    async def render(self, job):
        t0 = time.time()
        res = await self.qmp('loadvm ' + SNAPSHOT)
        if 'error' in res or 'rror' in str(res.get('return', '')):
            raise RuntimeError('loadvm: %r' % res)
        await self.qmp('cont')
        with open(os.path.join(WWW, 'job.txt'), 'w', encoding='utf-8') as f:
            f.write('%s\n%s\n%s\n' % (job.to, job.frm, job.msg))
        out = None
        for attempt in range(4):        # a fresh loadvm can strand the agent's first poll
            try:
                out = await self.agent_run(r'get /job.txt C:\p\job.txt', 8)
                break
            except asyncio.TimeoutError:
                log('agent slow after loadvm (%d)' % attempt)
        if not out or 'saved' not in out:
            raise RuntimeError('job not delivered: %r' % out)
        out = await self.agent_run(r'C:\p\valentine.exe C:\p\job.txt & type C:\p\valentine.log', 60)
        if 'settled' not in out:
            raise RuntimeError('valentine.exe: %r' % out[-300:])
        shot = '/dev/shm/valxp-%s.ppm' % job.id
        await self.qmp('screendump ' + shot)
        for _ in range(50):
            if os.path.exists(shot) and os.path.getsize(shot) > 1000:
                break
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.15)
        img = Image.open(shot).convert('RGB').crop(CROP)
        img.save(os.path.join(JOBS, job.id + '.png'), optimize=True)
        os.remove(shot)
        log('rendered %s in %.1fs' % (job.id[:6], time.time() - t0))

    async def worker(self):
        while True:
            while not self.line:
                self.wake.clear()
                await self.wake.wait()
            job = self.line.popleft()
            self.current = job
            job.state = 'rendering'
            try:
                await self.render(job)
                job.state = 'done'
                self.made += 1
            except Exception as e:
                log('render failed: %r' % e)
                try:            # one more go after a clean reset
                    await self.render(job)
                    job.state = 'done'
                    self.made += 1
                except Exception as e2:
                    log('render failed again: %r' % e2)
                    job.state, job.error = 'error', 'The valentine machine stumbled. Please try again in a minute.'
            self.current = None

    async def sweeper(self):
        while True:
            now = time.time()
            for jid, job in list(self.jobs.items()):
                if now - job.t > KEEP_S:
                    self.jobs.pop(jid, None)
                    try:
                        os.remove(os.path.join(JOBS, jid + '.png'))
                    except OSError:
                        pass
            for name in os.listdir(JOBS):      # files left by an earlier run of the server
                p = os.path.join(JOBS, name)
                if now - os.path.getmtime(p) > KEEP_S:
                    os.remove(p)
            await asyncio.sleep(600)

    # -- guest side -----------------------------------------------------------
    async def g_next(self, req):
        return web.Response(text=self.agent_q.popleft() if self.agent_q else '')

    async def g_out(self, req):
        self.agent_out.put_nowait((await req.read()).decode('cp1252', 'replace'))
        return web.Response(text='ok')

    async def g_file(self, req):
        name = os.path.basename(req.match_info.get('name', ''))
        path = os.path.join(WWW, name)
        if name and os.path.isfile(path):
            return web.FileResponse(path)
        return web.Response(status=404, text='not found')

    # -- public side ----------------------------------------------------------
    async def p_make(self, req):
        ip = client_ip(req)
        try:
            body = json.loads(await req.text())
            assert isinstance(body, dict)
        except Exception:
            return web.json_response({'error': 'That did not arrive in one piece. Try again?'}, status=400)
        to = clean(body.get('to'), 40)
        frm = clean(body.get('from'), 40)
        msg = clean(body.get('msg'), 240, multiline=True)
        if not to:
            return web.json_response({'error': 'Who is it for? Add a name.'}, status=400)
        if not msg:
            return web.json_response({'error': 'Write a few words for the inside.'}, status=400)
        if BLOCK.search(' '.join((to, frm, msg))):
            return web.json_response({'error': 'This machine only makes kind valentines. Try different words?'}, status=400)
        until = self.check(ip)
        if until:
            return web.json_response({'error': "You've made a lot of valentines. The machine is resting; you can make "
                                      "another at %s UTC." % time.strftime('%H:%M', time.gmtime(until)),
                                      'until': until}, status=429)
        if len(self.line) >= QUEUE_MAX:
            return web.json_response({'error': 'A long line of valentines is waiting. Try again in a few minutes.'}, status=503)
        self.per_ip.setdefault(ip, deque()).append(time.time())
        job = Job(ip, to, frm, msg)
        self.jobs[job.id] = job
        self.line.append(job)
        self.wake.set()
        log('job %s queued (%d waiting)' % (job.id[:6], len(self.line)))
        return web.json_response({'id': job.id, 'pos': self.position(job), 'to': to, 'from': frm, 'msg': msg})

    async def p_job(self, req):
        job = self.jobs.get(req.match_info['id'])
        if not job:
            return web.json_response({'state': 'gone'}, status=404)
        return web.json_response({'state': job.state, 'pos': self.position(job), 'error': job.error})

    async def p_img(self, req):
        jid = req.match_info['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]{20,40}', jid):
            raise web.HTTPNotFound()
        path = os.path.join(JOBS, jid + '.png')
        if not os.path.isfile(path):
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={'Cache-Control': 'private, max-age=86400'})

    async def p_state(self, req):
        return web.json_response({'waiting': len(self.line) + (1 if self.current else 0), 'made': self.made})


def client_ip(req):
    peer = req.remote or ''
    if peer == '127.0.0.1':
        xff = req.headers.get('X-Forwarded-For', '')
        if xff:
            return xff.split(',')[-1].strip()[:64] or peer
    return peer


@web.middleware
async def cors(req, handler):
    origin = req.headers.get('Origin')
    if req.method == 'OPTIONS':
        resp = web.Response()
    else:
        if origin and origin not in ORIGINS and req.method == 'POST':
            raise web.HTTPForbidden()
        resp = await handler(req)
    if origin in ORIGINS:
        resp.headers['Access-Control-Allow-Origin'] = origin
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        resp.headers['Vary'] = 'Origin'
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    return resp


async def main():
    S = Studio()
    guest = web.Application(client_max_size=64 * 1024)
    guest.add_routes([web.get('/next', S.g_next), web.post('/out', S.g_out), web.get('/{name}', S.g_file)])
    pub = web.Application(middlewares=[cors], client_max_size=8 * 1024)
    pub.add_routes([web.post('/make', S.p_make), web.get('/job/{id}', S.p_job), web.get('/img/{id}.png', S.p_img),
                    web.get('/state', S.p_state), web.route('OPTIONS', '/{tail:.*}', lambda r: web.Response()),
                    web.get('/', lambda r: web.Response(text='XP VALENTINE\n'))])
    r1, r2 = web.AppRunner(guest, access_log=None), web.AppRunner(pub, access_log=None)
    await r1.setup()
    await r2.setup()
    await web.TCPSite(r1, '127.0.0.1', GUEST_PORT).start()
    await web.TCPSite(r2, '127.0.0.1', PUBLIC_PORT).start()
    log('guest 127.0.0.1:%d, public 127.0.0.1:%d' % (GUEST_PORT, PUBLIC_PORT))
    await asyncio.gather(S.worker(), S.sweeper())


if __name__ == '__main__':
    asyncio.run(main())
