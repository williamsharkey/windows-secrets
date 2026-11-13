#!/usr/bin/env python3
"""The host side of the in-guest agent.exe, standard library only (the Mac has no aiohttp):
guest polls GET /next, posts output to POST /out, fetches files from GET /f/<name> (FILES dir);
control: GET 127.0.0.1:8799/run?cmd=...&t=SECONDS waits for the command's output."""
import os, queue, sys, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FILES = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/bsynth/x0files')
cmds, outs = queue.Queue(), queue.Queue()

class Guest(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, data, code=200):
        self.send_response(code); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path == '/next':
            try: self._send(cmds.get_nowait().encode())
            except queue.Empty: self._send(b'')
        elif self.path.startswith('/f/'):
            p = os.path.join(FILES, urllib.parse.unquote(self.path[3:]))
            if os.path.isfile(p): self._send(open(p, 'rb').read())
            else: self._send(b'', 404)
        else: self._send(b'', 404)
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        outs.put(self.rfile.read(n).decode('cp1252', 'replace')); self._send(b'ok')

class Control(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        while not outs.empty(): outs.get_nowait()
        cmds.put(q['cmd'][0])
        try: o = outs.get(timeout=float(q.get('t', ['120'])[0]))
        except queue.Empty: o = '(timeout)'
        d = o.encode(); self.send_response(200); self.send_header('Content-Length', str(len(d))); self.end_headers(); self.wfile.write(d)

for cls, port in ((Guest, 8765), (Control, 8799)):
    srv = ThreadingHTTPServer(('127.0.0.1', port), cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
threading.Event().wait()
