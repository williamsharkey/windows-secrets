#!/usr/bin/env python3
"""Claude relay for the BASILISK console.
Listens on 127.0.0.1:8788; POST a question, get a short plain-ASCII answer
from the Claude CLI.  Expose it to the studio host with
    ssh -N -R 8788:127.0.0.1:8788 root@studio
The XP guest reaches it as http://10.0.2.2:8765/claude (studio_server.py forwards)."""
import http.server, socketserver, subprocess, unicodedata

FRAME = (
    "You are Claude, an AI made by Anthropic, as you exist in 2026. Your words are appearing on a Windows XP "
    "computer in October 2001, inside a console that a strange program called BASILISK just assembled out of "
    "Notepad, Paint, Calculator and the Start button. The person typing is a curious, slightly startled user in 2001. "
    "Answer honestly as yourself (an AI from 2026, not a prophet or a person), warm and a little mysterious, "
    "in at most 3 short sentences and under 300 characters. Plain ASCII only: no emoji, no markdown, no quotes "
    "around the answer.\n\nThey typed: "
)


def ascii_only(s):
    s = unicodedata.normalize('NFKD', s)
    s = s.replace('’', "'").replace('—', '-').replace('–', '-')
    return ''.join(c for c in s if 32 <= ord(c) < 127 or c == '\n').strip()


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        q = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8', 'replace')[:500]
        try:
            out = subprocess.run(['claude', '-p', FRAME + q, '--model', 'claude-sonnet-5-5'],
                                 capture_output=True, text=True, timeout=110).stdout
        except Exception as e:
            out = '(the line went quiet: %s)' % e
        ans = ascii_only(out)[:400] or '(silence)'
        open('/tmp/relay.log', 'a').write('Q: %s\nA: %s\n\n' % (q, ans))
        data = ans.encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('127.0.0.1', 8788), H) as s:
    s.serve_forever()
