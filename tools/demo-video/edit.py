"""The edit list: shots in order, each with its picture, its narration, the host's place and its overlays.

build('spot') is the two-minute X spot; build('long') the home page cut (about three minutes). Times inside a shot
are seconds from its start; `src` is seconds into a capture's audio (shoot.py's `at` times).
"""
import json, os

ROOT = os.environ.get('DEMO_ROOT', '.')
WEB0 = int(os.environ.get('WEB0', 0))   # the web capture's frame where the keys play

# where things happen in the captures (shoot.py's scripts)
SRC = {
    'asm': 0.2, 'ding': 14.3,
    'minimise': 12.6, 'sr_menu': 25.0, 'about': 28.6,
    'lib': 14.6, 'granite': 22.6, 'tremolo': 38.4, 'shaded': 54.0, 'afterhours': 69.8, 'misty': 86.0,
    'rounded': 22.0, 'opal': 38.0, 'neon': 54.0, 'crystal': 70.0, 'loft': 86.0,
    'vibe': float(os.environ.get('VIBE', 25.8)), 'kit': 25.0, 'mines': 23.3, 'rec': 25.0, 'rec_play': 36.0,
    'song_open': 15.0, 'song_render': 26.0, 'song_done': 118.0, 'song_play': float(os.environ.get('SONG_PLAY', 130.0)),
    'citypop': 20.0,
}

SCR_X, SCR_Y = 88, 92   # compose.py's wide layout

PLACES = {   # x, y, scale of the host's box (428 x 574 at scale 1)
    'side': (1356, 150, 1.0),
    'corner': (1648, 640, 0.56),
    'corner_hi': (1648, 60, 0.56),
    'center': (746, 180, 1.0),
    'big': (660, 96, 1.4),
}


def L(lid):
    return json.load(open(os.path.join(ROOT, 'tts', 'lines.json')))[lid]['seconds']


def cap(scene, src, view=None, speed=1.0, **kw):
    v = {'k': 'cap', 'scene': scene, 'src': src, 'speed': speed}
    if view: v['view'] = view
    v.update(kw)
    return v


WIDE = [(0, 1, 512, 384)]
Z = lambda cx, cy, k=2: [(0, k, cx, cy)]


def zrect(cx, cy, k, r, pad=6):
    """A screen rectangle (x0, y0, x1, y1) in frame coordinates under a k-times zoom centred on cx, cy."""
    cw, ch = 1920 // k, 1080 // k
    x0 = min(max(cx - cw / 2, 0), 1024 - cw); y0 = min(max(cy - ch / 2, 0), 768 - ch)
    return ((r[0] - x0) * k - pad, (r[1] - y0) * k - pad, (r[2] - x0) * k + pad, (r[3] - y0) * k + pad)


PAD = [0.35]


def said(*ids, pad=None, lead=0.3):
    """Lines one after another from `lead`; returns (lines, total seconds)."""
    out, t = [], lead
    pad = PAD[0] if pad is None else pad
    for i in ids:
        out.append((i, t)); t += L(i) + pad
    return out, t


def build(cut):
    spot = cut == 'spot'
    PAD[0] = 0.25 if spot else 0.35
    S = []

    def shot(dur, v, lines=(), host='side', tr=None, over=(), gest=(), **kw):
        s = {'dur': dur, 'v': v, 'lines': list(lines), 'host': host, 'over': list(over), 'gest': list(gest)}
        if tr: s['tr'] = tr
        s.update(kw)
        S.append(s)

    # 1. cold open: the desk in 1993 (Blender, scene1993.py), the camera pushing into the CRT, which shows the real
    #    capture of the machine resuming; through the glass into the capture itself
    shot(7.0, {'k': 'seq', 'dir': 'blender/day_px'}, [('ann_open', 1.0)], host=None,
         over=[{'k': 'osd', 'text': 'PLAY \u25b6', 't': (0, 2.6)}])
    shot(3.4, cap('cold', SRC['asm'] + 7.0, WIDE), host=None, tr=('dissolve', 0.5))
    # 2. title card
    shot(2.4 if spot else 3.0, {'k': 'card', 'title': 'Getting Started with SNDWAVE1993', 'sub': 'Home Learning Series \u00b7 Tape 1 \u00b7 1993 technology, revisited',
               'logo': 'title-640.png', 'logo_scale': 2, 'logo_y': 30, 'band_y': 840}, host=None, tr=('star', 0.8))
    # 3. the host arrives over Ding Piano
    ln, d = said('h_hello', 's_what' if spot else 'h_what', 'h_1993')
    shot(d + 0.2, cap('cold', SRC['ding'], WIDE), ln, host='side', tr=('wipe', 0.5), gest=[(0.3, 'wave', 1.6), (d - 3.6, 'thumb', 2.6)],
         gain=0.8, over=[{'k': 'super', 'text': 'Ding Piano', 'sub': "SNDWAVE1993's first program: C:\\WINDOWS\\DING.WAV", 'x': 1180, 'y': 800,
                         't': (3.0, 9.0), 'size': 34}])
    # 4. it is really Windows: Program Manager, Accessories, Sound Recorder (sped up twice)
    ln, d = said('h_real')
    shot(max(d, 6.2), cap('proof', SRC['minimise'], WIDE, speed=2.0), ln, host='side', tr=('page', 0.6),
         over=[{'k': 'chapter', 'text': 'LESSON 1 \u00b7 IT REALLY IS WINDOWS', 't': (0.2, 3.6)},
               {'k': 'osd', 'text': '\u25b6\u25b6 x2', 't': (0, 99)}])
    shot(3.0 if spot else 3.6, cap('proof', SRC['sr_menu'], Z(320, 250, 3)), host='corner')
    ln, d = said('s_ver' if spot else 'h_ver', 'h_res', pad=0.5)
    t_res = ln[1][1]
    shot(d + 0.2, cap('proof', SRC['about'], Z(470, 370, 3), hold=SRC['about'] + 5.0), ln, host='corner', gest=[(0.5, 'point', 3.0)],
         over=[{'k': 'panel', 'title': 'C:\\WINDOWS\\SOUNDREC.EXE (its version resource)', 'x': 1290, 'y': 60, 'w': 610, 'col': 190, 'size': 23,
                'rows': [('Description', 'Sound Recorder accessory'), ('File version', '3.1'),
                         ('Copyright', 'Copyright \u00a9 Microsoft Corp. 1991'), ('Product', 'Microsoft Windows 3.1'),
                         ('File date', '11/08/1993  3:11 AM'), ('Size', '51,305 bytes')], 't': (0.4, t_res - 0.2)},
               {'k': 'box', 'r': zrect(470, 370, 3, (266, 454, 458, 470)), 't': (t_res, d + 0.2)}])
    if not spot:
        ln, d = said('h_play')
        shot(d + 0.5, cap('cold', SRC['ding'] + 2.0, WIDE), ln, host='side', tr=('iris', 0.6))
    # 5. sound packs
    ln, d = said('h_packs')
    shot(d + 0.3, cap('packs1', SRC['lib'], Z(512, 560)), ln, host='corner_hi', tr=('blinds', 0.6),
         over=[{'k': 'chapter', 'text': 'LESSON 2 \u00b7 SOUND PACKS', 't': (0.2, 3.6)}])
    ln, d = said('h_granite')
    shot(max(d, 3.6), cap('packs1', SRC['granite'], WIDE), ln, host='side',
         over=[{'k': 'super', 'text': 'Granite Cloud', 'sub': "Workgroup House Edition \u00b7 Pad \u00b7 owner's pick", 'x': 1180, 'y': 790}])
    if not spot:
        shot(3.2, cap('packs1', SRC['tremolo'], WIDE), host='side',
             over=[{'k': 'super', 'text': 'Shaded Tremolo', 'sub': "Workgroup House Edition \u00b7 Strings \u00b7 owner's pick", 'x': 1180, 'y': 790}])
    ln, d = said('h_shaded')
    shot(max(d, 4.2), cap('packs1', SRC['shaded'], WIDE), ln, host='side',
         over=[{'k': 'super', 'text': 'Shaded End', 'sub': "Workgroup House Edition \u00b7 Bass \u00b7 owner's pick", 'x': 1180, 'y': 790}])
    if not spot:
      ln, d = said('h_rounded')
      shot(max(d, 3.2), cap('packs2', SRC['rounded'], WIDE), ln, host='side',
         over=[{'k': 'super', 'text': 'Rounded Corner Chord', 'sub': 'Lifestyle Aesthetics Pack \u00b7 Bell', 'x': 1180, 'y': 790}])
    if not spot:
        shot(3.0, cap('packs2', SRC['opal'], WIDE), host='side',
             over=[{'k': 'super', 'text': 'Opal Rain', 'sub': 'Techno Server 4.0 \u00b7 Texture', 'x': 1180, 'y': 790}])
        shot(3.0, cap('packs2', SRC['neon'], WIDE), host='side',
             over=[{'k': 'super', 'text': 'Neon Pad', 'sub': 'ROM Reference Library \u00b7 Pad', 'x': 1180, 'y': 790}])
    if not spot:
      shot(3.0, cap('packs2', SRC['loft'], WIDE), host='side',
         over=[{'k': 'super', 'text': 'Loft Tine', 'sub': 'Rainy Loft Collection \u00b7 Keys \u00b7 new in 1.4', 'x': 1180, 'y': 790}])
    # 6. in your DAW, and the vibe
    from phrases import phrase
    notes = phrase('keys', 0.0)
    ln, d = said('h_daw')
    shot(d + 0.4, {'k': 'daw', 'scene': 'packs1', 'src': SRC['afterhours'] - 0.2, 'notes': notes, 'notes_len': 8.0,
                   'clip0': SRC['afterhours']}, ln, host='corner_hi', tr=('page', 0.6),
         over=[{'k': 'chapter', 'text': 'LESSON 3 \u00b7 IN YOUR DAW', 't': (0.2, 3.6)},
               {'k': 'super', 'text': 'Afterhours Tine', 'sub': 'Workgroup House Edition \u00b7 Keys', 'x': 60, 'y': 760, 't': (3.8, 99)}])
    ln, d = said('h_vibe')
    shot(max(d + 0.5, 6.4 if spot else 8.0), cap('vibe', SRC['vibe'], [(0, 3, 300, 640), (3.6, 1, 512, 384)]), ln, host='corner',
         over=[{'k': 'super', 'text': 'Playback tab: Wow, Flutter', 'sub': 'tape wobble, in cents, on every recorder', 'x': 60, 'y': 120, 't': (0.2, 3.5)}])
    # 7. the Song tab
    ln, d = said('s_song' if spot else 'h_song')
    a = min(d, 9.0)
    shot(a, cap('song', SRC['song_open'], Z(480, 300)), ln, host='corner', tr=('star', 0.7),
         over=[{'k': 'chapter', 'text': 'LESSON 4 \u00b7 THE SONG TAB', 't': (0.2, 3.6)}])
    rs = (SRC['song_done'] + 1 - SRC['song_render']) / 30.0
    shot(max(rs, d - a + 0.3), cap('song', SRC['song_render'], Z(480, 470), speed=30.0), host='corner',
         over=[{'k': 'osd', 'text': '\u25b6\u25b6 x30', 't': (0, 99)}], mute=True)
    ln, d = ([], 0) if spot else said('h_export', lead=1.2)
    shot(max(d, 4.8 if spot else 7.0), cap('song', SRC['song_play'] + 0.3, WIDE), ln, host='side', gain=1.1,
         over=[{'k': 'super', 'text': 'Aquarium (Level 3)', 'sub': 'Lifestyle Aesthetics Pack demo song \u00b7 11 tracks \u00b7 rendered on the Song tab',
                'x': 1180, 'y': 780, 'size': 34}] + ([{'k': 'super', 'text': 'Then: Export WAV...', 'x': 60, 'y': 120, 't': (3.0, 99), 'size': 32}] if spot else []))
    # 8. kits, the mine grid, recording
    if spot:
        ln, d = said('s_more', lead=0.2)
        k1 = ln[0][1] + 2.9
        shot(k1, cap('kits', SRC['kit'], Z(700, 420, 3)), ln, host='corner', tr=('wipe', 0.5),
             over=[{'k': 'chapter', 'text': 'LESSON 5 \u00b7 MORE FEATURES', 't': (0.2, 3.0)}])
        shot(4.8, cap('mines', SRC['mines'], Z(548, 450, 3)), host='corner', gest=[(0.3, 'point', 2.5)])
        shot(max(2.6, d - k1 - 4.8 + 0.4), cap('rec', SRC['rec'], Z(340, 200, 3)), host='corner')
    else:
        ln, d = said('h_kits', lead=0.2)
        shot(d + 0.6, cap('kits', SRC['kit'], Z(700, 420, 3)), ln, host='corner', tr=('wipe', 0.5),
             over=[{'k': 'chapter', 'text': 'LESSON 5 \u00b7 MORE FEATURES', 't': (0.2, 3.0)},
                   {'k': 'super', 'text': 'Echo Chamber Kit', 'sub': 'Kit Manager 98', 'x': 60, 'y': 120, 't': (0.5, 99)}])
        ln, d = said('h_mines', lead=0.2)
        shot(d + 1.0, cap('mines', SRC['mines'], Z(548, 450, 3)), ln, host='corner', gest=[(0.3, 'point', 2.5)],
             over=[{'k': 'super', 'text': 'Bedroom Tape Kit', 'sub': 'Kit Manager 98 \u00b7 played by the board', 'x': 60, 'y': 120}])
        ln, d = said('h_rec', lead=0.2)
        shot(max(d, 3.5), cap('rec', SRC['rec'], Z(340, 200, 3)), ln, host='corner')
        shot(4.0, cap('rec', SRC['rec_play'], Z(340, 200, 3)), host='corner',
             over=[{'k': 'super', 'text': 'The take, played back', 'x': 60, 'y': 120}])
    # 9. free: the web edition, then the box
    ln, d = said('h_free')
    shot(3.6, {'k': 'seq', 'dir': 'web/frames', 'start': WEB0}, ln, mark='free', host='corner', tr=('star', 0.8),
         over=[{'k': 'super', 'text': 'Try it in your browser', 'sub': 'williamsharkey.com/sndwave1993/play', 'x': 60, 'y': 820, 'size': 36}])
    shot(max(2.5, d - 3.6 + 0.6), {'k': 'art', 'items': [{'path': 'box-3d-render.png', 'x': 560, 'y': 470, 'scale': 2, 'pixel': True}],
                   'text': [{'s': 'FREE', 'x': 1080, 'y': 250, 'size': 120, 'fill': (255, 230, 80), 'stroke': 4},
                            {'s': 'VST3 \u00b7 AU \u00b7 CLAP', 'x': 1086, 'y': 400, 'size': 48},
                            {'s': 'Windows and macOS', 'x': 1086, 'y': 470, 'size': 48},
                            {'s': 'williamsharkey.com/sndwave1993', 'x': 1086, 'y': 570, 'size': 40, 'fill': (180, 240, 255)}]},
         host='corner', tr=('wipe', 0.5), gest=[(0.2, 'disk', 2.5)])
    # 10. CITYPOP1993: Program Manager, the icon, the player (wide), then up close as it plays
    ln, d = said('h_citypop') if spot else said('h_citypop', 'h_citypop2')
    D = max(d + 1.2, 7.5)
    shot(3.5, cap('citypop', SRC['citypop'], WIDE), ln, host='side', tr=('iris', 0.7),
         over=[{'k': 'box', 'r': (SCR_X + 104, SCR_Y + 208, SCR_X + 150, SCR_Y + 256), 't': (0.3, 2.2)}])
    shot(D - 3.5, cap('citypop', SRC['citypop'] + 3.5, Z(515, 330)), host='corner', gain=1.0,
         over=[{'k': 'super', 'text': 'CITYPOP1993', 'sub': 'an album made on it \u00b7 williamsharkey.com/citypop1993', 'x': 60, 'y': 120, 'size': 40},
               {'k': 'super', 'text': 'CITYPOP1993.EXE: coming in 1.5', 'sub': "the album, on the plugin's own desktop (test build shown)", 'x': 60, 'y': 250, 'size': 28, 't': (0.6, 99)}])
    # 11. sign-off: the host up close, then the end card
    ln, d = said('h_bye')
    shot(max(d + 0.8, 4.5), {'k': 'seq', 'dir': 'blender/night_px', 'mark': 1, 'speed': 210 / (30 * max(d + 0.8, 4.5))}, ln, host='side', tr=('page', 0.7),
         gest=[(0.3, 'wave', 2.2)])
    ln, d = said('ann_tag', lead=0.4)
    shot(d + 1.2, {'k': 'card', 'title': 'williamsharkey.com/sndwave1993', 'sub': None,
                   'logo': 'title-640.png', 'logo_scale': 2, 'logo_y': 30, 'band_y': 840}, ln, host=None, tr=('star', 0.7), swoop=0.6)
    music = []
    total = sum(s['dur'] for s in S)
    at = lambda i: sum(x['dur'] for x in S[:i])
    i_free = next(i for i, x in enumerate(S) if x.get('mark') == 'free')
    i_city = next(i for i, x in enumerate(S) if x['v'].get('scene') == 'citypop')
    i_bye = next(i for i, x in enumerate(S) if x['v'].get('mark'))
    music.append({'file': 'atrium-level-b2.mp3', 'at': 0.0, 'src': 0.0, 'len': 12.5, 'gain': 0.45, 'fin': 0.5, 'fout': 1.5})
    music.append({'file': 'atrium-level-b2.mp3', 'at': at(i_free), 'src': 30.0, 'len': at(i_city) - at(i_free) + 0.6, 'gain': 0.5})
    music.append({'file': 'citypop-12.mp3', 'at': at(i_bye), 'src': 0.0, 'len': total - at(i_bye), 'gain': 0.5, 'fin': 0.6, 'fout': 2.0})
    t_proof = next(sum(x['dur'] for x in S[:k]) for k, x in enumerate(S) if x['v'].get('scene') == 'proof')
    t_after = next(sum(x['dur'] for x in S[:k]) for k, x in enumerate(S) if k and S[k - 1]['v'].get('scene') == 'proof' and x['v'].get('scene') != 'proof')
    music.append({'file': 'fax-machine-fanfare.mp3', 'at': t_proof, 'src': 2.0, 'len': t_after - t_proof, 'gain': 0.4, 'fin': 0.8, 'fout': 1.0})
    return {'shots': S, 'music': music, 'places': PLACES}
