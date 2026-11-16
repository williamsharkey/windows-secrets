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
    'minimise': 12.6, 'sr_menu': 29.4, 'about': 33.2,
    'lib': 14.6, 'granite': 22.6, 'tremolo': 38.4, 'shaded': 54.0, 'afterhours': 69.8, 'misty': 86.0,
    'rounded': 22.0, 'opal': 38.0, 'neon': 54.0, 'crystal': 70.0, 'loft': 86.0,
    'vibe': float(os.environ.get('VIBE', 25.8)), 'kit': 25.0, 'mines': 23.3, 'steps': 25.8, 'rec': 25.0, 'rec_play': 36.0,
    'song_open': 15.0, 'song_render': 26.0, 'song_done': 118.0, 'song_play': float(os.environ.get('SONG_PLAY', 130.0)), 'song_start': 130.528,   # where the song's first sample lands in the capture
    'citypop': 27.6, 'citypop_track': 33.781,   # (the live capture; track 1 starts here)
}

SCR_X, SCR_Y = 88, 92   # compose.py's wide layout

PLACES = {   # x, y, scale of the narrator's phone (324 x 598 at scale 1)
    'side': (1430, 120, 1.0),
    'corner': (1722, 610, 0.55),
    'corner_hi': (1722, 40, 0.55),
    'center': (798, 200, 1.0),
    'big': (720, 60, 1.4),
    'right': (1520, 300, 0.8),
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

    F = lambda text, sub=None, y=120, t=(0.2, 99), x=60, size=34: {'k': 'super', 'text': text, 'sub': sub, 'x': x, 'y': y, 't': t, 'size': size}
    # 1. cold open: her dad's old tape: the desk in 1993 (Blender, scene1993.py), the camera pushing into the CRT
    ln, d = said('t_intro', 't_desk', lead=0.6)
    shot(max(7.0, d), {'k': 'seq', 'dir': 'blender/day_px', 'speed': 210 / (30 * max(7.0, d))}, ln, host='side', swoop=0.8,
         over=[{'k': 'osd', 'text': 'PLAY \u25b6', 't': (0, 2.6)}], gest=[(0.3, 'wave', 1.4), (d - 2.4, 'eyeroll', 1.4)])
    shot(2.6 if spot else 3.4, cap('cold_rt', SRC['asm'] + 7.0, WIDE), host='side', tr=('dissolve', 0.5), mute=True,
         over=[F('Windows for Workgroups 3.11 (1993), running inside the plugin', 'sixteen copies of Microsoft Sound Recorder line up into one synthesizer', y=790, x=60, size=30)])
    # 2. her title slide
    shot(2.4 if spot else 3.0, {'k': 'card', 'title': "My Family's Technology", 'sub': 'Computers Project \u00b7 Period 4 \u00b7 by Kayleigh',
                                'foot': 'SNDWAVE1993 \u00b7 a music plugin my dad made'}, host=None, tr=('star', 0.8))
    # 3. what it is, over Ding Piano; a shout-out
    ids = ['t_dad', 't_what', 't_what2', 't_maddie', 't_anyway1']
    ln, d = said(*ids)
    shot(d + 0.2, cap('cold', SRC['ding'], WIDE), ln, host='side', tr=('wipe', 0.5), gain=0.8,
         gest=[(ln[1][1] + 1.0, 'eyeroll', 1.3), (ln[3][1], 'phone', 2.4)],
         over=[{'k': 'super', 'text': 'Ding Piano', 'sub': "SNDWAVE1993's first program: C:\\WINDOWS\\DING.WAV", 'x': 1180, 'y': 800,
                't': (ln[3][1] - 0.5, d + 0.2), 'size': 34}])
    # 4. it is really Windows: Program Manager, Accessories, Sound Recorder; she reads the wrong parts of the About box
    ln, d = said('t_real')
    shot(max(d, 6.2), cap('proof', SRC['minimise'], WIDE, speed=2.0), ln, host='side', tr=('page', 0.6), mute=True,
         over=[{'k': 'chapter', 'text': 'SLIDE 2 \u00b7 IT REALLY IS WINDOWS', 't': (0.2, 3.6)},
               {'k': 'osd', 'text': '\u25b6\u25b6 x2', 't': (0, 99)},
               F('Program Manager \u2192 Accessories \u2192 Sound Recorder (SOUNDREC.EXE)', y=790, size=30, t=(2.0, 99))])
    shot(3.0 if spot else 3.6, cap('proof', SRC['sr_menu'], Z(320, 250, 3)), host='corner', mute=True)
    ids = ['t_about', 't_free', 't_license', 't_year', 't_note1', 't_note1b', 't_ok']
    ln, d = said(*ids, pad=0.5)
    t_free = ln[1][1]
    over = [{'k': 'panel', 'title': 'C:\\WINDOWS\\SOUNDREC.EXE (its version resource)', 'x': 1290, 'y': 60, 'w': 610, 'col': 190, 'size': 23,
             'rows': [('Description', 'Sound Recorder accessory'), ('File version', '3.1'),
                      ('Copyright', 'Copyright \u00a9 Microsoft Corp. 1991'), ('Product', 'Microsoft Windows 3.1'),
                      ('File date', '11/08/1993  3:11 AM'), ('Size', '51,305 bytes')], 't': (0.4, d + 0.2)},
            {'k': 'box', 'r': zrect(470, 370, 3, (266, 454, 458, 470)), 't': (t_free, t_free + 2.5)}]
    if not spot:
        over.append({'k': 'box', 'r': zrect(470, 370, 3, (266, 355, 458, 400)), 't': (ln[2][1], ln[2][1] + 2.5)})
    i1 = [x[0] for x in ln].index('t_note1')
    over.append({'k': 'note', 'title': 'what to say (from Dad)', 'text': 'It is a real Windows 3.11, running inside the plugin. Every note is played by the real Sound Recorder, from 1993.',
                 't': (ln[i1][1] + 0.6, ln[i1 + 2][1] + 0.4)})
    over[0]['t'] = (0.4, ln[i1][1])
    shot(d + 0.2, cap('proof', SRC['about'], Z(470, 370, 3), hold=SRC['about'] + 5.0), ln, host='corner', mute=True,
         gest=[(ln[1][1] + 1.0, 'eyeroll', 1.2), (ln[i1][1], 'phone', 1.2), (ln[i1 + 2][1], 'eyeroll', 1.0)], over=over)
    if False:
        ln, d = said('t_play')
        shot(d + 0.5, cap('cold', SRC['ding'] + 2.0, WIDE), ln, host='side', tr=('iris', 0.6),
             over=[F('Each note: Windows presses Play on one of the sixteen Sound Recorders', y=790, size=30)])
    # 5. sound packs
    ln, d = said('t_packs')
    shot(max(d + 0.3, 5.5), cap('packs1', SRC['lib'], Z(512, 560)), ln, host='corner_hi', tr=('blinds', 0.6),
         over=[{'k': 'chapter', 'text': 'SLIDE 3 \u00b7 SOUNDS', 't': (0.2, 3.6)},
               F('Library tab: 26 sound pack discs, 1,437 presets', 'pick a disc, pick a preset, Load preset', y=120, x=600, size=34)])
    ln, d = said('t_granite')
    shot(max(d, 3.6), cap('packs1', SRC['granite'], WIDE), ln, host='side', gest=[(0.4, 'phone', 1.8)],
         over=[{'k': 'super', 'text': 'Granite Cloud', 'sub': "Workgroup House Edition \u00b7 Pad \u00b7 a flute, slowed, with XP's Ringout", 'x': 1180, 'y': 790, 'size': 34}])
    if not spot:
        ln, d = said('t_shaded')
        shot(max(d, 4.2), cap('packs1', SRC['shaded'], WIDE), ln, host='side',
             over=[{'k': 'super', 'text': 'Shaded End', 'sub': "Workgroup House Edition \u00b7 Bass", 'x': 1180, 'y': 790}])
        ln, d = said('t_rounded')
        if False: shot(max(d, 3.2), cap('packs2', SRC['rounded'], WIDE), ln, host='side', gest=[(0.5, 'eyeroll', 1.3)],
             over=[{'k': 'super', 'text': 'Rounded Corner Chord', 'sub': "Lifestyle Aesthetics Pack \u00b7 XP's Notify as a major seventh", 'x': 1180, 'y': 790, 'size': 34}])
        if False: shot(3.0, cap('packs2', SRC['loft'], WIDE), host='side',
             over=[{'k': 'super', 'text': 'Loft Tine', 'sub': 'Rainy Loft Collection \u00b7 Keys \u00b7 new in 1.4', 'x': 1180, 'y': 790}])
    # 6. in your DAW, and the vibe
    from phrases import phrase
    notes = phrase('keys', 0.0)
    ln, d = said('t_note2', 't_idk')
    shot(max(d + 0.4, 6.0), {'k': 'daw', 'scene': 'packs1', 'src': SRC['afterhours'] - 0.2, 'notes': notes, 'notes_len': 8.0,
                   'clip0': SRC['afterhours']}, ln, host='corner_hi', tr=('page', 0.6),
         over=[{'k': 'chapter', 'text': 'SLIDE 4 \u00b7 IN A DAW', 't': (0.2, 3.6)},
               F('VST3 \u00b7 Audio Unit \u00b7 CLAP \u2014 Windows and macOS', 'works in Ableton Live and other DAWs', y=760, size=34, t=(ln[1][1], 99)),
               {'k': 'note', 'title': 'Dad, part 2', 'text': 'It works in Ableton and other DAWs, as a VST3, AU or CLAP, on Windows and Mac.', 't': (0.6, ln[1][1] + 0.2)}],
         gest=[(ln[1][1], 'eyeroll', 1.3)])
    ln, d = said('t_vibe')
    shot(max(d + 0.5, 6.4 if spot else 8.0), cap('vibe', SRC['vibe'], [(0, 3, 300, 640), (3.6, 1, 512, 384)]), ln, host='corner',
         over=[F('For vaporwave and Frutiger Aero: slow chords, a long release,', 'and Wow and Flutter on the Playback tab (tape wobble, in cents)', y=120, size=32)])
    # 7. the Song tab
    ln, d = said('t_song')
    a = min(d, 9.0)
    shot(a, cap('song', SRC['song_open'], Z(480, 300)), ln, host='corner', tr=('star', 0.7),
         over=[{'k': 'chapter', 'text': 'SLIDE 5 \u00b7 THE SONG TAB', 't': (0.2, 3.6)},
               F('Song tab (new in 1.4): import MIDI, a preset per track, Render', 'every track plays in its own Windows 3.11, on its own sixteen Sound Recorders; then they are mixed', y=760, size=30)])
    rs = (SRC['song_done'] + 1 - SRC['song_render']) / 30.0
    rd = max(2.5 if spot else rs, d - a + 0.3)
    sp = (SRC['song_done'] + 1 - SRC['song_render']) / rd
    shot(rd, cap('song', SRC['song_render'], Z(480, 470), speed=sp), host='corner',
         over=[{'k': 'osd', 'text': '\u25b6\u25b6 x%d' % round(sp), 't': (0, 99)}], mute=True)
    ln, d = ([], 0) if spot else said('t_export', lead=1.2)
    shot(max(d, 4.2 if spot else 7.0), cap('song', SRC['song_play'] + 0.3, WIDE), ln, host='side', mute=True, mark='songplay',
         over=[{'k': 'super', 'text': 'Aquarium (Level 3)', 'sub': 'a demo song \u00b7 11 tracks \u00b7 rendered on the Song tab \u00b7 then Export WAV...',
                'x': 1180, 'y': 780, 'size': 32}])
    # 8. kits, the Steps tab, recording
    ln, d = said('t_kits', lead=0.2) if spot else said('t_kits', 't_maddie2', lead=0.2)
    shot(d + 0.5, cap('kits', SRC['kit'], Z(700, 420, 3)), ln, host='corner', tr=('wipe', 0.5), gest=[(ln[-1][1], 'phone', 2.0)] if not spot else [],
         over=[{'k': 'chapter', 'text': 'SLIDE 6 \u00b7 MORE STUFF', 't': (0.2, 3.0)},
               F('Kits: Kit Manager 98\u2019s Echo Chamber Kit, with the pad calculator', y=880, size=30)])
    ln, d = said('t_steps', lead=0.2)
    shot(d + 0.6, cap('steps', SRC['steps'], Z(670, 250, 2), onsets=True, nodeclick=True), ln, host='corner', gest=[(0.3, 'eyeroll', 1.3)],
         over=[F('Steps tab (1.5): a step sequencer drawn like Minesweeper', 'numbers are notes of the scale \u00b7 accents \u00b7 octave shifts \u00b7 follows the DAW', y=760, size=30)])
    ln, d = said('t_rec', lead=0.2)
    shot(max(d + 0.4, 3.0), cap('rec', SRC['rec'], Z(340, 200, 3)), ln, host='corner',
         over=[F('Recorder: records the DAW input or the synth into Sound Recorder', y=880, size=30)])
    if not spot:
        shot(3.5, cap('rec', SRC['rec_play'], Z(340, 200, 3)), host='corner', over=[F('the take, played back', y=880, size=30)])
    # 9. free: the web edition, then the box
    ln, d = said('t_note3', 't_web2')
    dw = max(3.6, ln[1][1] + 0.3)
    shot(dw, {'k': 'seq', 'dir': 'web/frames', 'start': WEB0}, ln, mark='free', host='corner', tr=('star', 0.8),
         over=[{'k': 'super', 'text': 'Try it in your browser', 'sub': 'williamsharkey.com/sndwave1993/play', 'x': 60, 'y': 820, 'size': 36},
               {'k': 'note', 'title': 'Dad, part 3', 'text': "It's free, at williamsharkey.com/sndwave1993. You can also try it in your browser.", 't': (0.5, 99)}])
    shot(max(2.5, d - dw + 0.6), {'k': 'art', 'items': [{'path': 'box-3d-render.png', 'x': 560, 'y': 470, 'scale': 2, 'pixel': True}],
                   'text': [{'s': 'FREE', 'x': 1080, 'y': 250, 'size': 120, 'fill': (255, 230, 80), 'stroke': 4},
                            {'s': 'VST3 \u00b7 AU \u00b7 CLAP', 'x': 1086, 'y': 400, 'size': 48},
                            {'s': 'Windows and macOS', 'x': 1086, 'y': 470, 'size': 48},
                            {'s': 'williamsharkey.com/sndwave1993', 'x': 1086, 'y': 570, 'size': 40, 'fill': (180, 240, 255)}]},
         host='corner', tr=('wipe', 0.5))
    # 10. CITYPOP1993: the one part she likes
    ln, d = said('t_citypop') if spot else said('t_citypop', 't_citypop2')
    D = max(d + 1.2, 7.5)
    shot(3.5, cap('citypop', SRC['citypop'], WIDE), ln, host='side', tr=('iris', 0.7), mute=True, gest=[(0.6, 'smile', D - 0.8)],
         over=[{'k': 'box', 'r': (SCR_X + 314, SCR_Y + 212, SCR_X + 362, SCR_Y + 262), 't': (0.3, 2.2)}])
    shot(D - 3.5, cap('citypop', SRC['citypop'] + 3.5, Z(515, 330)), host='right', mute=True, swoop=0.8,
         over=[{'k': 'super', 'text': 'CITYPOP1993', 'sub': 'an album made on it \u00b7 williamsharkey.com/citypop1993', 'x': 60, 'y': 120, 'size': 40},
               {'k': 'super', 'text': 'CITYPOP1993.EXE', 'sub': "the album plays on the plugin's own Windows desktop (new in 1.5)", 'x': 60, 'y': 250, 'size': 28, 't': (0.6, 99)}])
    # 11. sign-off over the night desk, then the end card
    ln, d = said('t_anyway', 't_bye', pad=0.6)
    shot(max(d + 0.8, 4.5), {'k': 'seq', 'dir': 'blender/night_px', 'mark': 1, 'speed': 210 / (30 * max(d + 0.8, 4.5))}, ln, host='side', tr=('page', 0.7),
         gest=[(ln[1][1] + 1.5, 'peace', 2.0)])
    ln, d = said('t_tag', lead=0.4)
    shot(d + 1.2, {'k': 'card', 'title': 'williamsharkey.com/sndwave1993', 'sub': None,
                   'logo': 'title-640.png', 'logo_scale': 2, 'logo_y': 30, 'band_y': 840}, ln, host='corner', tr=('star', 0.7), gest=[(d - 1.5, 'eyeroll', 1.4)])
    music = []
    total = sum(s['dur'] for s in S)
    at = lambda i: sum(x['dur'] for x in S[:i])
    i_free = next(i for i, x in enumerate(S) if x.get('mark') == 'free')
    i_city = next(i for i, x in enumerate(S) if x['v'].get('scene') == 'citypop')
    i_bye = next(i for i, x in enumerate(S) if x['v'].get('mark'))
    # the Song tab's Play: its picture is the capture; its sound is the same song rendered offline by render311 --song
    # (tools/songrender), which matches the tab's mix sample for sample (correlation 0.999), without the playback
    # thread's 512-sample underruns that an editor capture records
    # CITYPOP1993.EXE: the picture is the live capture (the album player plays only on a live host); the sound is the
    # album's master of track 1, which the player plays sample for sample (correlation 0.998), placed where it starts
    music.append({'file': 'citypop-01.mp3', 'at': at(i_city) + SRC['citypop_track'] - SRC['citypop'], 'src': 0.0,
                  'len': at(i_bye) - at(i_city) - (SRC['citypop_track'] - SRC['citypop']), 'gain': 1.0, 'fin': 0.02, 'fout': 0.6, 'lufs': -20})
    i_sp = next(i for i, x in enumerate(S) if x.get('mark') == 'songplay')
    music.append({'file': 'aquarium-level-three.mp3', 'at': at(i_sp), 'src': SRC['song_play'] + 0.3 - SRC['song_start'],
                  'len': S[i_sp]['dur'], 'gain': 1.0, 'fin': 0.05, 'fout': 0.4, 'lufs': -20})
    music.append({'file': 'atrium-level-b2.mp3', 'at': 0.0, 'src': 0.0, 'len': 12.5, 'gain': 0.45, 'fin': 0.5, 'fout': 1.5})
    music.append({'file': 'atrium-level-b2.mp3', 'at': at(i_free), 'src': 30.0, 'len': at(i_city) - at(i_free) + 0.6, 'gain': 0.5})
    music.append({'file': 'citypop-12.mp3', 'at': at(i_bye), 'src': 0.0, 'len': total - at(i_bye), 'gain': 0.5, 'fin': 0.6, 'fout': 2.0})
    t_proof = next(sum(x['dur'] for x in S[:k]) for k, x in enumerate(S) if x['v'].get('scene') == 'proof')
    t_after = next(sum(x['dur'] for x in S[:k]) for k, x in enumerate(S) if k and S[k - 1]['v'].get('scene') == 'proof' and x['v'].get('scene') != 'proof')
    music.append({'file': 'fax-machine-fanfare.mp3', 'at': t_proof, 'src': 2.0, 'len': t_after - t_proof, 'gain': 0.4, 'fin': 0.8, 'fout': 1.0})
    return {'shots': S, 'music': music, 'places': PLACES}
