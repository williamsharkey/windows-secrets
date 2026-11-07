#!/usr/bin/env python3
"""Host side of the XP agent.  Serves files from ./www, hands out queued
commands on GET /next, collects output on POST /out.  Control it with
   studio_server.py run "dir C:\\p"     (enqueue, wait, print output)
   studio_server.py serve               (the server, port 8765)
The /claude endpoint forwards a prompt to a relay on 127.0.0.1:8788 if one
is listening (an ssh -R tunnel to a machine running the Claude CLI)."""
import http.server, socketserver, sys, os, time, json, urllib.request, threading

PORT = 8765
Q = '/root/xp/queue'
os.makedirs(Q, exist_ok=True)


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, data, code=200):
        if isinstance(data, str):
            data = data.encode('utf-8', 'replace')
        self.send_response(code)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == '/next':
            jobs = sorted(f for f in os.listdir(Q) if f.endswith('.cmd'))
            if not jobs:
                return self.reply('')
            p = os.path.join(Q, jobs[0])
            cmd = open(p).read()
            os.rename(p, p[:-4] + '.run')
            return self.reply(cmd)
        path = os.path.join('/root/xp/www', self.path.lstrip('/'))
        if os.path.isfile(path):
            return self.reply(open(path, 'rb').read())
        self.reply('not found', 404)

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(n)
        if self.path == '/out':
            runs = sorted(f for f in os.listdir(Q) if f.endswith('.run'))
            if runs:
                p = os.path.join(Q, runs[0])
                open(p[:-4] + '.out', 'wb').write(body)
                os.remove(p)
            return self.reply('ok')
        if self.path == '/claude':
            try:
                req = urllib.request.Request('http://127.0.0.1:8788/', data=body, method='POST')
                ans = urllib.request.urlopen(req, timeout=120).read()
            except Exception as e:
                ans = ('(relay unavailable: %s)' % e).encode()
            return self.reply(ans)
        self.reply('?', 404)


def serve():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('127.0.0.1', PORT), H) as s:
        s.serve_forever()


def run(cmd, timeout=180):
    if not cmd.startswith(('get ', 'spawn ')):
        cmd = '(' + cmd + ')'
    jid = '%016d' % int(time.time() * 1e6)
    open(os.path.join(Q, jid + '.tmp'), 'w').write(cmd)
    os.rename(os.path.join(Q, jid + '.tmp'), os.path.join(Q, jid + '.cmd'))
    out = os.path.join(Q, jid + '.out')
    t = time.time()
    while time.time() - t < timeout:
        if os.path.exists(out):
            time.sleep(0.1)
            sys.stdout.write(open(out, 'rb').read().decode('cp1252', 'replace'))
            os.remove(out)
            return
        time.sleep(0.2)
    print('(timeout)')


if __name__ == '__main__':
    if sys.argv[1] == 'serve':
        serve()
    else:
        run(' '.join(sys.argv[2:]))
