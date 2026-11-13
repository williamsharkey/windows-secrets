#!/usr/bin/env python3
"""Make the local (download) edition of BASILISK III from the live sources.

    puppetry/b3/server.py   -> packages/basilisk-xp/app/server_local.py
    puppetry/b3/basilisk.c  -> packages/basilisk-xp/guest/basilisk3.c

Every change is a literal replacement that must match exactly once, so this fails loudly (instead of
quietly producing a broken edition) when the live sources move on. Run it again after updating them.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PKG))
B3 = os.path.join(REPO, 'puppetry', 'b3')


def patch(text, pairs, name):
    for i, (a, b) in enumerate(pairs):
        n = text.count(a)
        if n != 1:
            sys.exit('%s: patch %d matches %d times:\n%s' % (name, i, n, a[:200]))
        text = text.replace(a, b)
    return text


# ----------------------------------------------------------------------------------------------- server

SERVER = [
    # one person, on their own machine: the guest reaches this host at 10.0.2.2:8765 (QEMU user networking),
    # signing in happens in the launcher's terminal; nothing is capped (it is their own account)
    ("    'TERM_GUEST_PORT': '8771',\n    'TERM_PUBLIC_PORT': '8781',",
     "    'TERM_GUEST_PORT': '8765',\n    'TERM_PUBLIC_PORT': '8790',"),
    ("    'TERM_MONTHLY_CAP_USD': '25',\n    'TERM_SESSION_USD': '0.60',        # one driver's session\n"
     "    'TERM_IP_DAY_USD': '1.50',         # one address per day",
     "    'TERM_MONTHLY_CAP_USD': '0',       # local edition: no caps, it is the person's own account\n"
     "    'TERM_SESSION_USD': '0',\n    'TERM_IP_DAY_USD': '0',"),
    # every current model the person may want
    ("    'claude-sonnet-5-5': (2.00, 10.00),\n}\nMODELS = {'haiku': 'claude-haiku-5-5', 'sonnet': 'claude-sonnet-5-5'}",
     "    'claude-sonnet-5-5': (2.00, 10.00),\n    'claude-opus-5-5': (4.00, 20.00),\n    'claude-fable-5-2': (8.00, 40.00),\n}\n"
     "MODELS = {'haiku': 'claude-haiku-5-5', 'sonnet': 'claude-sonnet-5-5', 'opus': 'claude-opus-5-5', 'fable': 'claude-fable-5-2'}\n"
     "MODEL_NAMES = {'claude-haiku-5-5': 'Claude Haiku 5.5', 'claude-sonnet-5-5': 'Claude Sonnet 5.5',\n"
     "               'claude-opus-5-5': 'Claude Opus 5.5', 'claude-fable-5-2': 'Claude Fable 5.2'}"),
    # credentials: the person's own. A pasted key (stored owner-only), ANTHROPIC_API_KEY, or an
    # `ant auth login` profile, which the SDK picks up by itself when no key is given
    ("""def api_client():
    import anthropic
    key = cfg('ANTHROPIC_API_KEY')
    if _client['key'] != key:
        _client['c'] = anthropic.AsyncAnthropic(api_key=key, timeout=60.0, max_retries=2)
        _client['key'] = key
    return _client['c']""",
     """CONFIG_DIR = os.environ.get('BASILISK_CONFIG') or ROOT
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
    \"\"\"which credential will be used: 'key' (pasted), 'env', 'token', 'profile', or ''\"\"\"
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
    \"\"\"Sonnet, Opus and Fable get the server-side refusal fallback (routes a declined request to a
    fallback model by refusal category); Haiku has none\"\"\"
    if 'haiku' in model:
        return api_client().messages.stream(model=model, **kw)
    return api_client().beta.messages.stream(model=model, betas=['server-side-fallback-2026-07-01'],
                                              fallbacks='default', **kw)"""),
    # names in the transcript, title and status bar
    ("""        short = 'Claude Haiku 5.5' if 'haiku' in self.model else 'Claude Sonnet 5.5'""",
     """        short = MODEL_NAMES.get(self.model, self.model)"""),
    ("""            self.ev('x', 'Now using %s (conversation restarted).' % ('Claude Haiku 5.5' if 'haiku' in m else 'Claude Sonnet 5.5'))""",
     """            self.ev('x', 'Now using %s (conversation restarted).' % MODEL_NAMES.get(m, m))
            save_settings(model=m)"""),
    ("""        if e in EFFORTS and e != self.effort:
            self.effort = e""",
     """        if e in EFFORTS and e != self.effort:
            self.effort = e
            save_settings(effort=e)"""),
    ("""                    self.ev('x', 'Models: /model haiku  or  /model sonnet')""",
     """                    self.ev('x', 'Models: /model haiku | sonnet | opus | fable')"""),
    ("""                if m != self.model:
                    self.model = m
                    self.messages = []    # caches and thinking are per model: start the conversation afresh
                    self.ev('x', 'Now using %s (conversation restarted).' % m)
                self.usage_event()""",
     """                if m != self.model:
                    self.model = m
                    self.messages = []    # caches and thinking are per model: start the conversation afresh
                    self.ev('x', 'Now using %s (conversation restarted).' % MODEL_NAMES.get(m, m))
                    save_settings(model=m)
                self.usage_event()"""),
    ("""  /model haiku     Claude Haiku 5.5 (default, fastest)
  /model sonnet    Claude Sonnet 5.5""",
     """  /model haiku     Claude Haiku 5.5 (default, fastest, cheapest)
  /model sonnet    Claude Sonnet 5.5
  /model opus      Claude Opus 5.5
  /model fable     Claude Fable 5.2 (most capable, dearest)"""),
    ("""                self.ev('x', 'This session: %s input tokens, %s output tokens, $%.4f. Month so far: $%.2f of $%.0f.' % (
                    format(self.tok_in, ','), format(self.tok_out, ','), self.usd, BUDGET.spent(), BUDGET.cap()))""",
     """                self.ev('x', 'This session: %s input tokens, %s output tokens, about $%.4f at list prices, billed to '
                        'your own Anthropic account. This month on this computer: about $%.2f.' % (
                    format(self.tok_in, ','), format(self.tok_out, ','), self.usd, BUDGET.spent()))"""),
    # no caps; only credentials can stop a turn
    ("""    def can_spend(self):
        if not cfg('ANTHROPIC_API_KEY'):
            return 'The line to Claude is not connected right now.'""",
     """    def can_spend(self):
        if not has_creds():
            return ('Not signed in to Claude yet. Close this window and start BASILISK again: it asks for an API '
                    'key (or run `ant auth login` first).')
        return None"""),
    ("""                async with api_client().messages.stream(
                        model=self.model, max_tokens=32000,""",
     """                async with open_stream(self.model,
                        max_tokens=32000,"""),
    ("""        self.model = cfg('TERM_MODEL')
        self.messages = []""",
     """        saved = load_settings()
        self.model = saved.get('model') if saved.get('model') in PRICES else cfg('TERM_MODEL')
        self.messages = []"""),
    ("""        self.effort = cfg('TERM_EFFORT') or 'low'""",
     """        self.effort = saved.get('effort') if saved.get('effort') in EFFORTS else (cfg('TERM_EFFORT') or 'low')"""),
    # the clock in XP shows the person's own time
    ("""        end = time.time() + 25
        while True:
            out = [e for e in self.events if e[0] > after]""",
     """        if LOCAL['renumber']:
            # first poll from a client that was resumed from a snapshot: it counts on from its own last event,
            # so number what waits for it from there
            LOCAL['renumber'] = False
            self.events = deque(((after + 1 + i, k, d) for i, (q, k, d) in enumerate(self.events)), maxlen=4000)
            self.seq = after + len(self.events)
        end = time.time() + 25
        while True:
            if LOCAL['dark']:
                return web.Response(body=b'%d z 4\\n2000' % after)
            out = [e for e in self.events if e[0] > after]"""),
    ("""        return web.Response(text=time.strftime('time %Y %m %d %H %M %S', time.gmtime()))""",
     """        return web.Response(text=time.strftime('time %Y %m %d %H %M %S', time.localtime()))"""),
    ("""        if self.agent and self.phase == 'ready':
            self.agent.settings(kv)
            self.touch()""",
     """        if kv.get('app') == 'settings':
            notify('open_settings')
            return web.Response(text='ok')
        if self.agent and self.phase == 'ready':
            self.agent.settings(kv)
            self.touch()"""),
    # Windows has no SIGHUP
    ("""    signal.signal(signal.SIGHUP, lambda *a: (load_env(), log('reloaded .env')))""",
     """    import threading
    if hasattr(signal, 'SIGHUP') and threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGHUP, lambda *a: (load_env(), log('reloaded .env')))"""),
    ("""        if cfg('ANTHROPIC_API_KEY'):
            api_client()""",
     """        if has_creds():
            api_client()"""),
    # no public side at all: QEMU's own window shows the machine. A web page in the person's browser must not
    # be able to talk to the guest port (it would drive Claude on their account): anything a browser marks is refused
    ("""    guest = web.Application(client_max_size=4 * 1024 * 1024)""",
     """    guest = web.Application(middlewares=[guest_only], client_max_size=4 * 1024 * 1024)"""),
    ("""    pub = web.Application(middlewares=[cors], client_max_size=64 * 1024)
    pub.add_routes([web.get('/ws', p_ws), web.get('/vnc', p_vnc), web.get('/vnc2', p_vnc_pumped), web.get('/state', p_state),
                    web.get('/', lambda r: web.Response(text='BASILISK III\\n'))])
    r1, r2 = web.AppRunner(guest, access_log=None), web.AppRunner(pub, access_log=None)
    await r1.setup()
    await r2.setup()
    await web.TCPSite(r1, '127.0.0.1', int(cfg('TERM_GUEST_PORT'))).start()
    await web.TCPSite(r2, '127.0.0.1', int(cfg('TERM_PUBLIC_PORT'))).start()""",
     """    T.runner = web.AppRunner(guest, access_log=None)
    await T.runner.setup()
    await open_door(True)"""),
    ("""    log('guest 127.0.0.1:%s, public 127.0.0.1:%s, model %s, key %s, month $%.4f of $%s' % (
        cfg('TERM_GUEST_PORT'), cfg('TERM_PUBLIC_PORT'), cfg('TERM_MODEL'),
        'present' if cfg('ANTHROPIC_API_KEY') else 'absent', BUDGET.spent(), cfg('TERM_MONTHLY_CAP_USD')))
    await asyncio.gather(T.pusher(), T.watchdog())""",
     """    log('BASILISK XP local: guest 127.0.0.1:%s, credentials: %s' % (
        cfg('TERM_GUEST_PORT'), cred_source() or 'none yet'))
    await asyncio.gather(T.pusher(), local_session())"""),
]

LOCAL_TAIL = r'''

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
'''

# ----------------------------------------------------------------------------------------------- client

CLIENT = [
    ("""    SendMessageA(cb_model, CB_ADDSTRING, 0, (LPARAM)"Claude Haiku 5.5  (fastest, the default)");
    SendMessageA(cb_model, CB_ADDSTRING, 0, (LPARAM)"Claude Sonnet 5.5  (deeper, slower, dearer)");""",
     """    SendMessageA(cb_model, CB_ADDSTRING, 0, (LPARAM)"Claude Haiku 5.5  (fastest, the default)");
    SendMessageA(cb_model, CB_ADDSTRING, 0, (LPARAM)"Claude Sonnet 5.5  (deeper, slower, dearer)");
    SendMessageA(cb_model, CB_ADDSTRING, 0, (LPARAM)"Claude Opus 5.5  (deepest coding and agents)");
    SendMessageA(cb_model, CB_ADDSTRING, 0, (LPARAM)"Claude Fable 5.2  (most capable, dearest)");"""),
    ("""            SendMessageA(cb_model, CB_GETCURSEL, 0, 0) == 1 ? "sonnet" : "haiku", ef[e < 0 ? 0 : e > 4 ? 4 : e],""",
     """            model_key((int)SendMessageA(cb_model, CB_GETCURSEL, 0, 0)), ef[e < 0 ? 0 : e > 4 ? 4 : e],"""),
    ("""static char st_effort[16] = "low", st_model[32] = "Claude Haiku 5.5", st_state[96] = "ready";""",
     """static char st_effort[16] = "low", st_model[32] = "Claude Haiku 5.5", st_state[96] = "ready";
static const char *model_key(int i)
{
    static const char *k[] = {"haiku", "sonnet", "opus", "fable"};
    return k[i < 0 || i > 3 ? 0 : i];
}
static int model_index(const char *a)
{
    return strstr(a, "fable") ? 3 : strstr(a, "opus") ? 2 : strstr(a, "sonnet") ? 1 : 0;
}
static void fmt_cost(char *t)     /* local edition: no cap, the person's own account */
{
    if (st_cap > 0) sprintf(t, "$%.4f of $%.2f", st_usd, st_cap);
    else sprintf(t, "$%.4f (your account)", st_usd);
}"""),
    ("""                SendMessageA(cb_model, CB_SETCURSEL, strstr(a, "sonnet") ? 1 : 0, 0);""",
     """                SendMessageA(cb_model, CB_SETCURSEL, model_index(a), 0);"""),
    ("""    sprintf(t, "$%.4f of $%.2f", st_usd, st_cap);""",
     """    fmt_cost(t);"""),
    ("""            if (i < 6) sprintf(t, "%ld", val[i]); else sprintf(t, "$%.4f of $%.2f", st_usd, st_cap);""",
     """            if (i < 6) sprintf(t, "%ld", val[i]); else fmt_cost(t);"""),
    # the clock is the person's local time (the host sends local time; XP's own zone does not matter)
    ("""            SetSystemTime(&st);
        }
    }
    free(hello);""",
     """            SetLocalTime(&st);
            SetLocalTime(&st);
        }
    }
    free(hello);"""),
    # snapshots: the host can ask the event thread to pause ('z' ms) so the machine is saved with no request
    # in flight, and can set the clock ('T' Y M D h m s, local) after a resume
    ("""                memcpy(e->data, s, len); e->data[len] = 0;
                s += len;""",
     """                memcpy(e->data, s, len); e->data[len] = 0;
                s += len;
                if (kind == 'z') { int ms = atoi(e->data); free(e->data); free(e); Sleep(ms); continue; }"""),
    ("""    case 'x':                         /* a quiet note from the host */""",
     """    case 'T': {                       /* set the clock (after a resume): "Y M D h m s", local time */
        int Y, M, D, h, mi, se;
        if (sscanf(e->data, "%d %d %d %d %d %d", &Y, &M, &D, &h, &mi, &se) == 6) {
            SYSTEMTIME st;
            memset(&st, 0, sizeof st);
            st.wYear = (WORD)Y; st.wMonth = (WORD)M; st.wDay = (WORD)D;
            st.wHour = (WORD)h; st.wMinute = (WORD)mi; st.wSecond = (WORD)se;
            SetLocalTime(&st);
            SetLocalTime(&st);
        }
        break;
    }
    case 'x':                         /* a quiet note from the host */"""),
    # the local edition's own settings (sign-in, intro, display, sound, reset) live in the app around XP
    ("""    SendMessageA(ck_notify, BM_SETCHECK, BST_CHECKED, 0);
""",
     """    SendMessageA(ck_notify, BM_SETCHECK, BST_CHECKED, 0);
    mk("Button", "This computer", BS_GROUPBOX, 10, 270, 360, 54, panel[T_SETTINGS], 0);
    mk("Button", "BASILISK app settings...", BS_PUSHBUTTON, 24, 290, 190, 26, panel[T_SETTINGS], 607);
    mk("Static", "Sign-in, intro, display, sound, reset", SS_LEFT, 222, 296, 140, 26, panel[T_SETTINGS], 0);
"""),
    ("""    case 604: { char *r = http("POST", "/b3/send", "/clear", 6, NULL, 5000); free(r); break; }""",
     """    case 604: { char *r = http("POST", "/b3/send", "/clear", 6, NULL, 5000); free(r); break; }
    case 607: { char *r = http("POST", "/b3/set", "app=settings\\n", 13, NULL, 5000); free(r); break; }"""),
]


def main():
    with open(os.path.join(B3, 'server.py')) as f:
        s = f.read()
    s = patch(s, SERVER, 'server.py')
    i = s.index("\nif __name__ == '__main__':")
    s = s[:i] + LOCAL_TAIL + s[i:]
    s = s.replace('BASILISK III - host side of the Claude Code client', 'BASILISK III, local edition - host side of the Claude Code client', 1)
    with open(os.path.join(PKG, 'app', 'server_local.py'), 'w') as f:
        f.write(s)
    with open(os.path.join(B3, 'basilisk.c')) as f:
        c = f.read()
    c = patch(c, CLIENT, 'basilisk.c')
    with open(os.path.join(PKG, 'guest', 'basilisk3.c'), 'w', newline='\n') as f:
        f.write(c)
    print('wrote app/server_local.py and guest/basilisk3.c')


if __name__ == '__main__':
    main()
