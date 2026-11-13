"""BASILISK's window: XP's screen, our loading screen, settings and the quit card. pygame-ce (SDL2) with
GPU textures; nothing of QEMU is ever shown."""
import os
import subprocess
import sys
import threading
import time

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
os.environ.setdefault('SDL_WINDOWS_NO_CLOSE_ON_ALT_F4', '1')    # Alt+F4 belongs to XP
os.environ.setdefault('SDL_MOUSE_FOCUS_CLICKTHROUGH', '1')
os.environ.setdefault('SDL_VIDEO_X11_WMCLASS', 'basilisk-xp')
import pygame                                                    # noqa: E402
from pygame._sdl2 import video                                   # noqa: E402

APP = os.path.dirname(os.path.abspath(__file__))
WIN = os.name == 'nt'
MAC = sys.platform == 'darwin'

BG = (12, 13, 16)
PANEL = (24, 26, 31)
CARD = (32, 35, 41)
LINE = (52, 56, 64)
INK = (236, 234, 229)
DIM = (150, 154, 162)
ACCENT = (76, 195, 138)          # basilisk green
ACCENT_INK = (10, 24, 17)
WARN = (240, 160, 90)
EV_WAKE = pygame.USEREVENT + 1
EV_SETTINGS = pygame.USEREVENT + 2
MODELS = [('haiku', 'Haiku 5.5'), ('sonnet', 'Sonnet 5.5'), ('opus', 'Opus 5.5'), ('fable', 'Fable 5.2')]
EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']
MOD_HOST = pygame.KMOD_META if MAC else 0


FONT_DIR = os.path.join(APP, 'fonts')


class Fonts:
    def __init__(self):
        self.cache = {}
        reg = os.path.join(FONT_DIR, 'Inter-Regular.ttf')
        bold = os.path.join(FONT_DIR, 'Inter-SemiBold.ttf')
        self.paths = {False: reg if os.path.exists(reg) else None, True: bold if os.path.exists(bold) else None}

    def get(self, px, bold=False):
        k = (int(px), bold)
        if k not in self.cache:
            path = self.paths[bold]
            f = pygame.font.Font(path, max(6, int(px)))
            if bold and not path:
                f.set_bold(True)
            self.cache[k] = f
        return self.cache[k]


class Painter:
    """immediate-mode drawing and hit-testing, in points (scaled by k to pixels)"""

    def __init__(self, surf, k, fonts, mouse, click):
        self.s, self.k, self.f = surf, k, fonts
        self.mouse, self.click = mouse, click
        self.hot = False

    def r(self, x, y, w, h):
        k = self.k
        return pygame.Rect(round(x * k), round(y * k), round(w * k), round(h * k))

    def box(self, x, y, w, h, color, radius=8, border=None):
        rc = self.r(x, y, w, h)
        pygame.draw.rect(self.s, color, rc, border_radius=round(radius * self.k))
        if border:
            pygame.draw.rect(self.s, border, rc, width=max(1, round(self.k)), border_radius=round(radius * self.k))
        return rc

    def text(self, x, y, t, size=14, color=INK, bold=False, center=False, right=False, maxw=None):
        f = self.f.get(size * self.k, bold)
        if maxw:
            while t and f.size(t)[0] > maxw * self.k:
                t = t[:-2] + '…'
        img = f.render(t, True, color)
        px, py = round(x * self.k), round(y * self.k)
        if center:
            px -= img.get_width() // 2
        elif right:
            px -= img.get_width()
        self.s.blit(img, (px, py))
        return img.get_width() / self.k

    def wrap(self, x, y, w, t, size=13, color=DIM, lh=1.45):
        f = self.f.get(size * self.k)
        words, line, yy = t.split(' '), '', y
        for wd in words:
            test = (line + ' ' + wd).strip()
            if f.size(test)[0] > w * self.k and line:
                self.text(x, yy, line, size, color)
                yy += size * lh
                line = wd
            else:
                line = test
        if line:
            self.text(x, yy, line, size, color)
            yy += size * lh
        return yy

    def hit(self, rc):
        inside = rc.collidepoint(self.mouse)
        if inside:
            self.hot = True
        return inside and self.click

    def button(self, x, y, w, h, label, primary=False, on=False, size=13):
        rc = self.r(x, y, w, h)
        over = rc.collidepoint(self.mouse)
        if primary or on:
            col = ACCENT if not over else (96, 215, 158)
            ink = ACCENT_INK
        else:
            col = CARD if not over else (44, 48, 56)
            ink = INK
        pygame.draw.rect(self.s, col, rc, border_radius=round(6 * self.k))
        if not (primary or on):
            pygame.draw.rect(self.s, LINE, rc, width=max(1, round(self.k)), border_radius=round(6 * self.k))
        self.text(x + w / 2, y + (h - size * 1.25) / 2, label, size, ink, bold=primary or on, center=True)
        return self.hit(rc)

    def segmented(self, x, y, w, h, options, value, size=13):
        """options [(value, label)]: returns the clicked value or None"""
        n = len(options)
        seg = w / n
        out = None
        self.box(x, y, w, h, CARD, 7, LINE)
        for i, (v, lab) in enumerate(options):
            rc = self.r(x + i * seg + 2, y + 2, seg - 4, h - 4)
            if v == value:
                pygame.draw.rect(self.s, ACCENT, rc, border_radius=round(5 * self.k))
            elif rc.collidepoint(self.mouse):
                pygame.draw.rect(self.s, (44, 48, 56), rc, border_radius=round(5 * self.k))
            self.text(x + i * seg + seg / 2, y + (h - size * 1.25) / 2, lab, size,
                      ACCENT_INK if v == value else INK, bold=v == value, center=True)
            if self.hit(rc):
                out = v
        return out

    def toggle(self, x, y, on):
        rc = self.r(x, y, 38, 22)
        pygame.draw.rect(self.s, ACCENT if on else LINE, rc, border_radius=round(11 * self.k))
        cx = x + (27 if on else 11)
        pygame.draw.circle(self.s, (250, 250, 248), (round(cx * self.k), round((y + 11) * self.k)), round(8 * self.k))
        return self.hit(rc)


class App:
    def __init__(self, Boot, core):
        self.core = core
        self.prefs = core.Prefs()
        self.boot = Boot(self)
        self.guest_port = None
        self.m = None
        self.vnc = None
        self.tex = None
        self.tex_gen = -1
        self.tex_mode = None
        self.dirty = True
        self.mode = 'loading'          # loading | running | error | quitting
        self.overlay = None            # None | 'settings' | 'quit'
        self.held = set()
        self.buttons = 0
        self.key_text = ''
        self.key_focus = False
        self.key_msg = ''
        self.reset_armed = 0
        self.dont_ask = False
        self.server_started = False
        self.first_frame = False
        self.intro = False
        self.quit_text = ''
        self.lock = threading.Lock()
        self.quit_thread = None
        self.fb_dirty = True
        self.accel = 'tcg'

    # ---- called from the boot thread
    def wake(self):
        try:
            pygame.event.post(pygame.event.Event(EV_WAKE))
        except pygame.error:
            pass

    def start_server(self):
        if self.server_started:
            return
        import server_local as S
        ready = threading.Event()
        S.LOCAL['listeners'].append(self.on_server)
        threading.Thread(target=S.serve, args=(ready.set,), daemon=True, name='server').start()
        ready.wait(10)
        time.sleep(0.2)
        self.server_started = True

    def on_server(self, kind, kv):
        if kind == 'open_settings':
            pygame.event.post(pygame.event.Event(EV_SETTINGS))
        self.wake()

    def connect_screen(self, m):
        import vnc
        end = time.time() + 30
        while True:
            try:
                v = vnc.Vnc(m.vnc, self.on_frame)
                v.connect()
                break
            except (OSError, vnc.VncError):
                if time.time() > end or not m.alive():
                    raise RuntimeError('Could not reach the XP screen (see logs/qemu.log).')
                time.sleep(0.05)
        self.vnc = v

    def on_frame(self):
        self.fb_dirty = True
        if not self.dirty:
            self.dirty = True
            self.wake()

    def ready(self, m, intro):
        self.m, self.intro = m, intro
        self.mode = 'running'
        import server_local as S
        if not S.has_creds():
            pygame.event.post(pygame.event.Event(EV_SETTINGS))
        self.wake()

    # ---- window
    def make_window(self):
        pygame.init()
        pygame.key.stop_text_input()
        info = pygame.display.get_desktop_sizes()[0] if pygame.display.get_desktop_sizes() else (1600, 1000)
        w, h = self.prefs.get('size') or (1024, 768)
        if w > info[0] * 0.92 or h > info[1] * 0.88:
            s = min(info[0] * 0.92 / w, info[1] * 0.88 / h)
            w, h = int(w * s), int(h * s)
        self.win = video.Window('BASILISK XP', size=(w, h), resizable=True, allow_high_dpi=True)
        self.win.minimum_size = (640, 480)
        icon = os.path.join(APP, 'icon.png')
        if os.path.exists(icon):
            self.win.set_icon(pygame.image.load(icon))
        self.ren = video.Renderer(self.win, vsync=True)
        self.fonts = Fonts()
        if self.prefs.get('fullscreen'):
            self.win.set_fullscreen(True)
        self.ui_tex = None

    def scale_k(self):
        vw = self.ren.get_viewport().w
        return max(1.0, vw / max(1, self.win.size[0]))

    def run(self):
        self.make_window()
        threading.Thread(target=self.boot.run, daemon=True, name='boot').start()
        if os.environ.get('BASILISK_TEST_DIR'):
            threading.Thread(target=self.test_hook, daemon=True, name='test').start()
        last_draw = 0
        while True:
            evs = [pygame.event.wait(16 if self.dirty else 500)] + pygame.event.get()
            for e in evs:
                if not self.handle(e):
                    return self.shutdown()
            if self.mode == 'quitting' and not self.quit_thread:
                return self.shutdown()
            now = time.time()
            if now - last_draw > 0.004 or self.dirty:
                self.draw()
                last_draw = now

    # ---- testing: BASILISK_TEST_DIR/cmd holds lines the app acts on as if a person did them
    def test_hook(self):
        d = os.environ['BASILISK_TEST_DIR']
        cmdf = os.path.join(d, 'cmd')
        while True:
            time.sleep(0.25)
            try:
                with open(cmdf) as f:
                    lines = f.read().splitlines()
                os.remove(cmdf)
            except OSError:
                continue
            for line in lines:
                op, _, arg = line.partition(' ')
                log('test: %s %s' % (op, '(hidden)' if op == 'key' else arg[:60]))
                if op == 'shot':
                    self.shot_to = os.path.join(d, arg)
                    self.dirty = True
                    self.wake()
                elif op == 'type':
                    for ch in arg.replace('\\n', '\n'):
                        for sc, down in keys_for(ch):
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP,
                                                                 scancode=sc, key=0, mod=0, unicode=''))
                        time.sleep(0.03)
                elif op == 'settings':
                    pygame.event.post(pygame.event.Event(EV_SETTINGS))
                elif op == 'esc':
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, scancode=41, key=pygame.K_ESCAPE, mod=0,
                                                         unicode=''))
                elif op == 'click':
                    x, y = (float(v) for v in arg.split())
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=1))
                elif op == 'guestclick':
                    x, y = (int(v) for v in arg.split())
                    if self.vnc:
                        self.vnc.pointer(x, y, 0)
                        time.sleep(0.05)
                        self.vnc.pointer(x, y, 1)
                        time.sleep(0.08)
                        self.vnc.pointer(x, y, 0)
                elif op == 'quit':
                    if arg in ('keep', 'fresh') and self.mode == 'running':
                        self.do_quit(arg == 'keep')
                    else:
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                elif op == 'model':
                    import server_local as S
                    S.set_model_effort(model=arg)
                elif op == 'effort':
                    import server_local as S
                    S.set_model_effort(effort=arg)
                elif op == 'key':
                    import server_local as S
                    S.store_key(arg)
                    S.credentials_changed()
            self.wake()

    # ---- input
    def host_shortcut(self, e):
        mods = e.mod
        if MAC:
            if mods & pygame.KMOD_META and e.key == pygame.K_COMMA:
                return 'settings'
            if mods & pygame.KMOD_META and mods & pygame.KMOD_CTRL and e.key == pygame.K_f:
                return 'fullscreen'
            if mods & pygame.KMOD_META and e.key == pygame.K_q:
                return 'quit'
            if mods & pygame.KMOD_META:
                return 'swallow'
        else:
            if mods & pygame.KMOD_CTRL and mods & pygame.KMOD_ALT and e.key == pygame.K_s:
                return 'settings'
            if e.key == pygame.K_F11:
                return 'fullscreen'
        return None

    def release_all(self):
        if self.vnc:
            for sc in list(self.held):
                self.vnc.key(sc, False)
            if self.buttons:
                self.buttons = 0
        self.held.clear()

    def vm_rect(self):
        """where XP's screen sits in the window, in pixels"""
        vw, vh = self.ren.get_viewport().size
        w, h = (self.vnc.w, self.vnc.h) if self.vnc and self.vnc.w else (1024, 768)
        if self.prefs['scale'] == 'sharp':
            s = min(vw // w, vh // h)
            if s >= 1:
                return pygame.Rect((vw - w * s) // 2, (vh - h * s) // 2, w * s, h * s)
        s = min(vw / w, vh / h)
        return pygame.Rect(round((vw - w * s) / 2), round((vh - h * s) / 2), round(w * s), round(h * s))

    def to_guest(self, pos):
        k = self.scale_k()
        r = self.vm_rect()
        x = (pos[0] * k - r.x) * self.vnc.w / r.w
        y = (pos[1] * k - r.y) * self.vnc.h / r.h
        return x, y, r.collidepoint(pos[0] * k, pos[1] * k)

    def handle(self, e):
        t = e.type
        if t == pygame.QUIT or (t == pygame.WINDOWCLOSE):
            return self.ask_quit()
        if t == EV_SETTINGS:
            if self.mode == 'running':
                self.open_overlay('settings')
            return True
        if t == pygame.WINDOWFOCUSLOST:
            self.release_all()
            return True
        if t in (pygame.WINDOWRESIZED, pygame.WINDOWSIZECHANGED):
            self.dirty = True
            if not self.win_fullscreen():
                self.prefs['size'] = list(self.win.size)
            return True
        if t == pygame.KEYDOWN:
            sc = self.host_shortcut(e)
            if sc == 'settings':
                self.release_all()
                self.open_overlay(None if self.overlay == 'settings' else 'settings')
                return True
            if sc == 'fullscreen':
                self.release_all()
                self.toggle_fullscreen()
                return True
            if sc == 'quit':
                self.release_all()
                return self.ask_quit()
            if sc == 'swallow':
                return True
            if self.overlay:
                return self.overlay_key(e)
            if self.mode == 'running' and self.vnc:
                if MAC and e.scancode in (227, 231):
                    return True
                self.held.add(e.scancode)
                self.vnc.key(e.scancode, True)
            return True
        if t == pygame.KEYUP:
            if e.scancode in self.held:
                self.held.discard(e.scancode)
                self.vnc.key(e.scancode, False)
            return True
        if t == pygame.TEXTINPUT and self.overlay == 'settings' and self.key_focus:
            self.key_text += e.text
            self.dirty = True
            return True
        if t in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):
            return self.mouse(e)
        return True

    def mouse(self, e):
        t = e.type
        if self.overlay or self.mode != 'running' or not self.vnc or not self.vnc.w:
            pygame.mouse.set_visible(True)
            if t in (pygame.MOUSEBUTTONUP,) and e.button == 1:
                self.click_at = e.pos
                self.dirty = True
            if t == pygame.MOUSEMOTION:
                self.dirty = True
            return True
        if t == pygame.MOUSEWHEEL:
            x, y, inside = self.to_guest(pygame.mouse.get_pos())
            b = 8 if e.y > 0 else 16
            for _ in range(min(5, abs(int(e.y)) or 1)):
                self.vnc.pointer(x, y, self.buttons | b)
                self.vnc.pointer(x, y, self.buttons)
            return True
        x, y, inside = self.to_guest(e.pos)
        pygame.mouse.set_visible(not inside)
        if t == pygame.MOUSEBUTTONDOWN or t == pygame.MOUSEBUTTONUP:
            bit = {1: 1, 2: 2, 3: 4}.get(e.button, 0)
            if t == pygame.MOUSEBUTTONDOWN:
                self.buttons |= bit
            else:
                self.buttons &= ~bit
        self.vnc.pointer(x, y, self.buttons)
        return True

    def win_fullscreen(self):
        return bool(self.prefs.get('fullscreen'))

    def toggle_fullscreen(self):
        on = not self.prefs.get('fullscreen')
        if on:
            self.win.set_fullscreen(True)
        else:
            self.win.set_windowed()
        self.prefs.set(fullscreen=on)
        self.dirty = True

    def open_overlay(self, which):
        self.overlay = which
        self.key_focus = False
        self.reset_armed = 0
        pygame.key.stop_text_input()
        pygame.mouse.set_visible(True)
        self.dirty = True

    def overlay_key(self, e):
        if e.key == pygame.K_ESCAPE:
            if self.overlay == 'quit' and self.mode == 'quitting':
                return True
            self.open_overlay(None)
            return True
        if self.overlay == 'settings' and self.key_focus:
            paste = (e.mod & (pygame.KMOD_META if MAC else pygame.KMOD_CTRL)) and e.key == pygame.K_v
            if paste:
                try:
                    txt = pygame.scrap.get_text() if hasattr(pygame.scrap, 'get_text') else ''
                except pygame.error:
                    txt = ''
                self.key_text += (txt or '').strip()
            elif e.key == pygame.K_BACKSPACE:
                self.key_text = self.key_text[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.save_key()
            self.dirty = True
        return True

    # ---- settings actions
    def save_key(self):
        key = self.key_text.strip()
        if not key:
            return
        self.key_msg = 'Checking the key with Anthropic…'

        def work():
            import server_local as S
            ok = check_key(key)
            if ok is True:
                S.store_key(key)
                S.credentials_changed()
                self.key_text = ''
                self.key_focus = False
                self.key_msg = 'Saved. Signed in with this key.'
            else:
                self.key_msg = ok
            self.wake()
        threading.Thread(target=work, daemon=True).start()

    def reset_machine(self):
        self.open_overlay(None)
        self.mode = 'loading'
        self.boot.say('Resetting the machine')

        def work():
            import server_local as S
            if self.accel == 'kvm':        # the shipped snapshot runs under TCG: start the machine again
                self.prefs.set(session=False)
                S.call(S.go_dark())
                if self.vnc:
                    self.vnc.close()
                self.m.quit()
                self.vnc = self.m = None
                self.tex = None
                S.call(S.open_door())
                self.boot.run()
                return
            try:
                S.call(S.go_dark())
                self.m.cmd('stop')
                r = self.m.loadvm('ready')
                log('reset: loadvm ready: %s' % r)
                S.call(S.open_door())
                S.call(S.restored(None))
                self.m.cmd('cont')
                self.prefs.set(session=False)
            except Exception as ex:
                log('reset failed: %r' % ex)
            self.mode = 'running'
            self.wake()
        threading.Thread(target=work, daemon=True).start()

    def ask_quit(self):
        if self.mode == 'quitting':
            return True
        if self.mode != 'running' or not self.m:
            return False
        choice = self.prefs['on_quit']
        if choice == 'ask':
            self.open_overlay('quit')
            return True
        self.do_quit(choice == 'keep')
        return True

    def do_quit(self, keep):
        self.quit_thread = True
        self.mode = 'quitting'
        self.overlay = 'quit'
        self.quit_text = 'Saving the machine for next time…' if keep else 'Closing…'
        self.release_all()
        self.dirty = True

        def work():
            import server_local as S
            try:
                if keep:
                    S.call(S.go_dark())
                    state = S.agent_state(S.T.agent) if S.T and S.T.agent else None
                    with open(self.core.SESSION, 'w') as f:
                        import json
                        json.dump(state, f)
                    self.m.cmd('stop')
                    r = self.m.savevm('session')
                    log('savevm session: %s' % r)
                    self.prefs.set(session=r is True, session_accel=self.accel)
                else:
                    self.prefs.set(session=False)
            except Exception as ex:
                log('quit: %r' % ex)
            self.quit_thread = None
            self.wake()
        self.quit_thread = threading.Thread(target=work, daemon=True)
        self.quit_thread.start()

    def shutdown(self):
        if self.vnc:
            self.vnc.close()
        if self.m:
            self.m.quit()
        try:
            self.prefs.set()
        except OSError:
            pass
        pygame.quit()

    # ---- drawing
    def draw(self):
        self.dirty = False
        ren = self.ren
        ren.draw_color = BG
        ren.clear()
        k = self.scale_k()
        if self.mode in ('running', 'quitting') and self.vnc and self.vnc.w and self.showable():
            self.draw_vm()
        else:
            self.draw_loading(k)
        if self.overlay:
            self.draw_overlay(k)
        if getattr(self, 'shot_to', None):
            try:
                pygame.image.save(ren.to_surface(), self.shot_to)
            except Exception as ex:
                log('shot: %r' % ex)
            self.shot_to = None
        ren.present()

    def showable(self):
        """in the intro, hide the PC's text-mode start (BIOS): show XP from its own boot screen on"""
        if not self.intro or self.first_frame:
            return True
        if self.vnc.w >= 640 and self.vnc.h >= 480 and self.vnc.w != 720:
            self.first_frame = True
        return self.first_frame

    def draw_vm(self):
        v = self.vnc
        sharp = self.prefs['scale'] == 'sharp'
        if self.tex is None or self.tex_gen != v.size_gen or self.tex_mode != sharp:
            os.environ['SDL_RENDER_SCALE_QUALITY'] = 'nearest' if sharp else 'linear'
            with v.lock:
                self.tex = video.Texture(self.ren, (v.w, v.h), streaming=True)
                self.tex_gen, self.tex_mode = v.size_gen, sharp
                self.fb_dirty = True
        if self.fb_dirty:
            self.fb_dirty = False
            with v.lock:
                surf = pygame.image.frombuffer(v.fb, (v.w, v.h), 'RGBX')
                self.tex.update(surf)
        self.tex.draw(dstrect=self.vm_rect())

    def surface(self):
        vw, vh = self.ren.get_viewport().size
        s = pygame.Surface((vw, vh), pygame.SRCALPHA)
        return s

    def blit_surface(self, s):
        t = video.Texture.from_surface(self.ren, s)
        t.blend_mode = 1
        t.draw(dstrect=(0, 0, s.get_width(), s.get_height()))

    def draw_loading(self, k):
        s = self.surface()
        W, H = s.get_width() / k, s.get_height() / k
        p = Painter(s, k, self.fonts, (0, 0), False)
        cy = H / 2 - 40
        b = self.boot
        if b.error:
            p.text(W / 2, cy - 30, 'BASILISK', 34, INK, bold=True, center=True)
            p.text(W / 2, cy + 22, 'Something went wrong', 16, WARN, center=True)
            yy = cy + 52
            p.wrap(W / 2 - 260, yy, 520, b.error, 13, DIM)
            p.text(W / 2, H - 40, 'Logs: %s' % self.core.LOGS, 11, DIM, center=True)
        else:
            p.text(W / 2, cy - 30, 'B A S I L I S K   X P', 34, INK, bold=True, center=True)
            p.text(W / 2, cy + 18, 'Claude Code, in Windows XP', 14, DIM, center=True)
            p.text(W / 2, cy + 62, b.text, 14, INK, center=True)
            if b.sub:
                p.text(W / 2, cy + 84, b.sub, 12, DIM, center=True)
            bw = 260
            p.box(W / 2 - bw / 2, cy + 110, bw, 4, LINE, 2)
            if b.frac is not None:
                p.box(W / 2 - bw / 2, cy + 110, max(4, bw * b.frac), 4, ACCENT, 2)
            else:
                ph = (time.time() * 0.8) % 1.0
                p.box(W / 2 - bw / 2 + (bw - 60) * (0.5 - 0.5 * __import__('math').cos(ph * 6.283)), cy + 110, 60, 4,
                      ACCENT, 2)
                self.dirty = True
        self.blit_surface(s)

    def draw_overlay(self, k):
        s = self.surface()
        s.fill((6, 7, 9, 170))
        W, H = s.get_width() / k, s.get_height() / k
        click = getattr(self, 'click_at', None)
        self.click_at = None
        mpos = pygame.mouse.get_pos()
        p = Painter(s, k, self.fonts, (mpos[0] * k, mpos[1] * k), bool(click))
        if click:
            p.mouse = (click[0] * k, click[1] * k)
        if self.overlay == 'settings':
            self.draw_settings(p, W, H)
        elif self.overlay == 'quit':
            self.draw_quit(p, W, H)
        self.blit_surface(s)

    def draw_quit(self, p, W, H):
        w, h = 440, 210
        x, y = (W - w) / 2, (H - h) / 2
        p.box(x, y, w, h, PANEL, 12, LINE)
        p.text(x + 24, y + 22, 'Quit BASILISK XP', 18, INK, bold=True)
        if self.mode == 'quitting':
            p.text(x + 24, y + 64, self.quit_text, 14, DIM)
            self.dirty = True
            return
        p.wrap(x + 24, y + 56, w - 48, 'Keep this machine as it is (open windows, files in C:\\b3\\work and the '
                                          'conversation) for next time, or start fresh?', 13, DIM)
        if p.toggle(x + 24, y + 116, self.dont_ask):
            self.dont_ask = not self.dont_ask
        p.text(x + 72, y + 118, "Don't ask again (change it in settings)", 12, DIM)
        if p.button(x + 24, y + 156, 150, 34, 'Keep and quit', primary=True):
            if self.dont_ask:
                self.prefs.set(on_quit='keep')
            self.do_quit(True)
        if p.button(x + 184, y + 156, 120, 34, 'Start fresh'):
            if self.dont_ask:
                self.prefs.set(on_quit='fresh')
            self.do_quit(False)
        if p.button(x + w - 104, y + 156, 80, 34, 'Cancel'):
            self.open_overlay(None)

    def draw_settings(self, p, W, H):
        import server_local as S
        st = S.status()
        w, h = 620, min(H - 40, 610)
        x, y = (W - w) / 2, max(20, (H - h) / 2)
        p.box(x, y, w, h, PANEL, 14, LINE)
        p.text(x + 28, y + 22, 'BASILISK XP settings', 18, INK, bold=True)
        p.text(x + w - 28, y + 26, ('⌘,' if MAC else 'Ctrl+Alt+S') + '  ·  Esc to close', 11, DIM, right=True)
        cx, yy, cw = x + 28, y + 62, w - 56

        # account
        src = {'key': 'Signed in with your saved API key', 'env': 'Signed in with ANTHROPIC_API_KEY',
               'token': 'Signed in with ANTHROPIC_AUTH_TOKEN', 'profile': 'Signed in with your `ant` profile'}
        creds = st['creds']
        p.text(cx, yy, 'Claude account', 13, DIM, bold=True)
        pygame.draw.circle(p.s, ACCENT if creds else WARN, (round((cx + 6) * p.k), round((yy + 31) * p.k)),
                           round(5 * p.k))
        p.text(cx + 18, yy + 23, src.get(creds, 'Not signed in yet'), 14, INK)
        yy += 50
        fr = p.box(cx, yy, cw - 200, 34, CARD, 7, ACCENT if self.key_focus else LINE)
        shown = self.key_text
        if shown:
            shown = shown[:7] + '•' * max(0, min(24, len(shown) - 11)) + shown[-4:] if len(shown) > 12 else '•' * len(shown)
        p.text(cx + 12, yy + 9, shown or 'Paste an Anthropic API key', 13, INK if shown else DIM, maxw=cw - 230)
        if p.hit(fr):
            self.key_focus = True
            pygame.key.start_text_input()
        if p.button(cx + cw - 190, yy, 90, 34, 'Paste'):
            try:
                txt = pygame.scrap.get_text() if hasattr(pygame.scrap, 'get_text') else ''
            except pygame.error:
                txt = ''
            self.key_text = (txt or '').strip()
            self.key_focus = True
        if p.button(cx + cw - 92, yy, 92, 34, 'Save key', primary=bool(self.key_text)):
            self.save_key()
        yy += 42
        msg = self.key_msg or ('The key is checked with one tiny request and kept only on this computer, readable by '
                               'you alone. Or run `ant auth login` in a terminal. Every turn is billed to your Anthropic '
                               'account at API prices.')
        yy = p.wrap(cx, yy, cw - (110 if creds == 'key' else 0), msg, 12, DIM)
        if creds == 'key' and p.button(cx + cw - 100, yy - 34, 100, 28, 'Forget key', size=12):
            S.store_key('')
            S.credentials_changed()
            self.key_msg = 'Forgotten.'
        yy += 14

        # model & effort
        p.text(cx, yy, 'Model', 13, DIM, bold=True)
        cur = next((short for short, full in S.MODELS.items() if full == st['model']), 'haiku')
        v = p.segmented(cx, yy + 20, cw, 32, MODELS, cur)
        if v and v != cur:
            S.set_model_effort(model=v)
        yy += 62
        p.text(cx, yy, 'Effort', 13, DIM, bold=True)
        v = p.segmented(cx, yy + 20, cw, 32, [(e, e) for e in EFFORTS], st['effort'])
        if v and v != st['effort']:
            S.set_model_effort(effort=v)
        yy += 60
        p.text(cx, yy, 'This conversation about $%.4f  ·  this month on this computer about $%.2f  ·  estimates; '
                       'Anthropic bills your account' % (st['usd'], st['month_usd']), 11, DIM, maxw=cw)
        yy += 30

        # app
        rows = [('Intro', 'Watch BASILISK build itself each start (slower)', 'intro')]
        for lab, sub, key in rows:
            p.text(cx, yy + 2, lab, 14, INK)
            p.text(cx + 90, yy + 4, sub, 12, DIM)
            if p.toggle(cx + cw - 38, yy, self.prefs[key]):
                self.prefs.set(**{key: not self.prefs[key]})
            yy += 34
        p.text(cx, yy + 6, 'Display', 14, INK)
        v = p.segmented(cx + 90, yy, 220, 30, [('fit', 'Fit window'), ('sharp', 'Sharp pixels')], self.prefs['scale'])
        if v:
            self.prefs.set(scale=v)
        if p.button(cx + cw - 130, yy, 130, 30, 'Exit full screen' if self.prefs.get('fullscreen') else 'Full screen',
                    size=12):
            self.toggle_fullscreen()
        yy += 40
        p.text(cx, yy + 6, 'On quit', 14, INK)
        v = p.segmented(cx + 90, yy, 300, 30, [('ask', 'Ask'), ('keep', 'Keep machine'), ('fresh', 'Start fresh')],
                        self.prefs['on_quit'])
        if v:
            self.prefs.set(on_quit=v)
        yy += 44
        armed = time.time() - self.reset_armed < 4
        if p.button(cx, yy, 170, 30, 'Click again to reset' if armed else 'Reset machine', size=12):
            if armed:
                self.reset_machine()
                return
            self.reset_armed = time.time()
        if armed:
            self.dirty = True
        if p.button(cx + 180, yy, 150, 30, 'Show my files', size=12):
            open_folder(self.core.DATA)
        p.text(cx + 342, yy + 8, self.core.DATA, 11, DIM, maxw=cw - 342)
        yy += 42
        p.wrap(cx, yy, cw, self.boot.speed_note, 11, DIM)


US = {**{c: (4 + i) for i, c in enumerate('abcdefghijklmnopqrstuvwxyz')},
      **{c: (30 + i) for i, c in enumerate('1234567890')},
      '\n': 40, ' ': 44, '-': 45, '=': 46, '[': 47, ']': 48, '\\': 49, ';': 51, "'": 52, '`': 53, ',': 54, '.': 55,
      '/': 56}
SHIFT = {'!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
         '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';', '"': "'", '~': '`', '<': ',', '>': '.', '?': '/'}


def keys_for(ch):
    """(SDL scancode, down) presses that type ch on a US keyboard"""
    shift = ch.isupper() or ch in SHIFT
    base = SHIFT.get(ch, ch.lower())
    sc = US.get(base)
    if sc is None:
        return []
    seq = [(sc, True), (sc, False)]
    return [(225, True)] + seq + [(225, False)] if shift else seq


def open_folder(path):
    try:
        if WIN:
            os.startfile(path)
        elif MAC:
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
    except OSError:
        pass


def check_key(key):
    try:
        import anthropic
    except ImportError:
        return True
    try:
        anthropic.Anthropic(api_key=key, timeout=30.0, max_retries=1).messages.create(
            model='claude-haiku-5-5', max_tokens=8, messages=[{'role': 'user', 'content': 'hi'}])
        return True
    except anthropic.AuthenticationError:
        return 'Anthropic did not accept that key.'
    except anthropic.APIError as e:
        return 'Could not check the key (%s). Try again.' % type(e).__name__


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)
