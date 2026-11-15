# Read-only capture of a ghosts.garden room journey from a local build (pattern of tools/test-ride-time.mjs):
# GETs of /api and /blobs go to the live site, every POST is answered here (204), every other host is blocked.
import sys, os, time, threading, urllib.request, http.server, socketserver, json
from playwright.sync_api import sync_playwright

WEB = os.path.expanduser('~/packwork/ggcap/web'); LIVE = 'https://ghosts.garden'
OUT = sys.argv[1]; ROOM = sys.argv[2] if len(sys.argv) > 2 else 'pauly'
SECS = float(os.environ.get('SECS', '90')); EVERY = float(os.environ.get('EVERY', '1.5'))
os.makedirs(OUT, exist_ok=True)

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=WEB, **k)
    def log_message(s, *a): pass
    def do_POST(s):
        n = int(s.headers.get('content-length') or 0); s.rfile.read(n); s.send_response(204); s.end_headers()
    do_PUT = do_DELETE = do_POST
    def do_GET(s):
        if s.path.startswith('/api/') or s.path.startswith('/blobs/'):
            try:
                with urllib.request.urlopen(LIVE + s.path, timeout=30) as r:
                    b = r.read(); s.send_response(r.status); s.send_header('Content-Type', r.headers.get('content-type') or ''); s.end_headers(); s.wfile.write(b)
            except Exception as e:
                s.send_response(502); s.end_headers()
            return
        return super().do_GET()

class TS(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
srv = TS(('127.0.0.1', 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{port}/'

with sync_playwright() as pw:
    b = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    ctx = b.new_context(viewport={'width': 414, 'height': 736}, device_scale_factor=1, is_mobile=True, has_touch=True)
    p = ctx.new_page()
    p.route('**/*', lambda r: r.continue_() if r.request.url.startswith(base) else r.abort())
    p.goto(base, wait_until='load'); time.sleep(2.5)
    p.evaluate("() => document.querySelector('[data-tab=chat]').click()")
    for i in range(30):
        time.sleep(0.5)
        if p.evaluate("() => { const G = window.__gg.garden; return !!(G.roomsView && G.roomsView._show && G.roomsApi); }"): break
    p.evaluate("async (room) => { const G = window.__gg.garden; await G.roomsApi().join(room); G.roomsView._show(room); }", ROOM)
    ok = False
    for i in range(60):
        time.sleep(0.5)
        ok = p.evaluate("(room) => { const s = window.__gg.garden.roomScenes[room]; if (!s || !s._debug) return false; const d = s._debug(); return d && d.ready > 2; }", ROOM)
        if ok: break
    print("ready", ok)
    HIDE = "(room) => { window.__gg.garden.roomScenes[room]._people(false); }"
    if os.environ.get('NOPPL'): p.evaluate(HIDE, ROOM)
    time.sleep(2)
    p.screenshot(path=f'{OUT}/000-present.png')
    p.keyboard.down('ArrowUp'); t0 = time.time(); n = 1
    while time.time() - t0 < SECS:
        time.sleep(EVERY)
        if os.environ.get('NOPPL'):
            try: p.evaluate(HIDE, ROOM)
            except Exception: pass
        try: dbg = p.evaluate("(room) => { const d = window.__gg.garden.roomScenes[room]._debug(); return d.p; }", ROOM)
        except Exception: dbg = '?'
        p.screenshot(path=f'{OUT}/{n:03d}-p{dbg}.png'); n += 1
    p.keyboard.up('ArrowUp')
    b.close()
srv.shutdown()
