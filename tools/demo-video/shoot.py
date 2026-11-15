#!/usr/bin/env python3
"""The tour's footage: scripted runs of the real SNDWAVE2000 1.4.0 VST3 in BasiliskHost (Windows), each one a
real-time render with the editor open, driven by window messages, captured with the harness's `rec` step
(tools/basilisk-host, a .bhrc file of the editor's frames) and the plugin's own output (editor.wav).

    shoot.py SCENE [SCENE ...] [--sw C:/Users/willi/video-sw] [--dry]

Offline (--editor-offline): the plugin renders offline, paced to the wall clock, so its audio has no dropouts
whatever the PC's load, and the frames carry their audio time. SW holds BasiliskHost.exe and the plugin bundle (--bundle; the SNDWAVE1993 test build from the 3.11 lane); each scene writes SW/cap/SCENE/.
Times in the scripts below are seconds of the render's audio (the `at` step); the score starts at WARMUP.
"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phrases import phrase, write_smf

WARMUP = 14.0   # the plugin blocks process() for seconds while Windows resumes; the harness then
#                 catches up block by block, and notes in that stretch are lost. After it, wall clock = audio time.
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PACKS = None   # set from SW in main

# the editor's controls (1024x768 editor, 1.4.0)
TAB = {'main': (310, 583), 'voices': (351, 583), 'playback': (402, 583), 'scales': (453, 583), 'rec': (491, 583),
       'mines': (528, 583), 'library': (571, 583), 'song': (615, 583)}
DISC_LIST = (125, 609)        # first row of the Library tab's disc list
PRESET_LIST = (330, 627)      # first row of its preset list
LOAD_PRESET = (632, 638)
DISCS = ['WORKHOUS', 'TECHSRV4', 'TRANCEKI', 'CSC007_B', 'LFS012CD', 'CRCD14', 'RETRODSP', 'AMBIENT2', 'WCCM_TR9',
         'LEISURE3', 'GAMEPORT', 'PWCLASSI', 'STUDARCH', 'HERITAGE', 'HAA_CD00', 'LIFESTYL', 'KL_EM_V2', 'PAULYWAU',
         'GARDENRW', 'TAPEPARL', 'COURTYAR', 'LISTENPO', 'OFFICEMA', 'POLYSHOW', 'KITMGR98', 'RAINYLOF']


def items(disc):
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(PACKS, disc, 'PRESETS.TSV'), encoding='latin1') if not l.startswith('#')]
    return [f'{r[0]}: {r[1]}' for r in rows]


def list_keys(labels, i):
    """Keys that move a Windows 3.1 list box from its first item to item i (home, a letter, then arrows)."""
    best = ['home'] + ['down'] * i
    up = ['end'] + ['up'] * (len(labels) - 1 - i)
    if len(up) < len(best): best = up
    c = labels[i][0].lower()
    if labels[0][0].lower() != c:
        first = next(k for k, l in enumerate(labels) if l[0].lower() == c)
        if first <= i and 2 + i - first < len(best): best = ['home', c] + ['down'] * (i - first)
    return best


def go(x, y, s=0.45):
    return [f'glide {x} {y} {s}', f'click {x} {y}']


def pick_preset(disc_index, name, current_disc=None):
    """Steps: select disc (if needed) and the preset named NAME, then Load preset."""
    disc = DISCS[disc_index]
    labels = items(disc)
    i = next(k for k, l in enumerate(labels) if l.split(': ', 1)[1] == name)
    st = []
    if current_disc != disc_index:
        st += go(*DISC_LIST) + ['key home'] + ['key down'] * disc_index if disc_index < 13 else \
              go(*DISC_LIST) + ['key end'] + ['key up'] * (len(DISCS) - 1 - disc_index)
        st += ['wait 0.6']
    st += go(*PRESET_LIST) + [f'key {k}' for k in list_keys(labels, i)] + ['wait 0.5'] + go(*LOAD_PRESET)
    return st


class Scene:
    def __init__(self, name, steps, notes=(), program=None, env=(), fps=30, end=None, bundle=''):
        self.bundle = bundle
        self.name, self.steps, self.notes, self.program, self.env, self.fps = name, steps, list(notes), program, list(env), fps
        self.end = end


def slots(picks, first=16.0, every=16.0, lead=6.0):
    """Preset slots: at `first + k*every` load pick k, its phrase `lead` seconds later. picks: (disc, name, kind)."""
    steps, notes, cur = [], [], None
    for k, (disc, name, kind) in enumerate(picks):
        t = first + k * every
        steps += [f'at {t}'] + pick_preset(disc, name, cur)
        cur = disc
        notes += phrase(kind, t + lead - WARMUP)
    return steps, notes, first + len(picks) * every


def scenes():
    S = {}
    # 1. cold open: Windows resumes, the recorders assemble, Ding Piano plays (factory program 0)
    S['cold'] = Scene('cold', ['rec cap.bhrc 30', 'at 24', 'rec off'], phrase('ding', 0.5), program=0, end=24)
    # 2. it is real: minimise the synth, Program Manager, Accessories, Sound Recorder, Help > About
    S['proof'] = Scene('proof', ['rec cap.bhrc 30', 'at 12', 'glide 600 300 0.6',
        *go(1010, 9, 0.8), 'wait 1.2', *go(38, 715, 0.8), 'wait 0.7', *go(63, 563, 0.3), 'wait 1.8',
        *go(71, 556, 0.7), 'click 71 556', 'wait 1.8', *go(447, 95, 0.6), 'wait 1.4',
        *go(885, 80, 0.8), 'click 885 80', 'wait 2.2', 'key alt+h', 'wait 1.2', 'key a', 'wait 6',
        *go(534, 245, 0.6), 'wait 1.5', 'rec off'], [(30.0, 60, 1, 0.1)], program=0, end=46)
    # 3. sound packs: Workgroup House Edition, the owner's top-rated
    st, nt, end = slots([(0, 'Granite Cloud', 'chords'), (0, 'Shaded Tremolo', 'chords'), (0, 'Shaded End', 'bass'),
                         (0, 'Afterhours Tine', 'keys'), (0, 'Misty Warp', 'fx')])
    S['packs1'] = Scene('packs1', ['rec cap.bhrc 30', 'at 14.5', *go(*TAB['library'])] + st + [f'at {end}', 'rec off'], nt, program=0, end=end)
    # 4. more discs
    st, nt, end = slots([(15, 'Rounded Corner Chord', 'stabs'), (1, 'Opal Rain', 'fx'), (14, 'Neon Pad', 'chords'),
                         (9, 'Crystal Recital', 'melody'), (25, 'Loft Tine', 'keys')])
    S['packs2'] = Scene('packs2', ['rec cap.bhrc 30', 'at 14.5', *go(*TAB['library'])] + st + [f'at {end}', 'rec off'], nt, program=0, end=end)
    # 5. the vibe: Granite Cloud with wow and flutter from the Playback tab
    S['vibe'] = Scene('vibe', ['rec cap.bhrc 30', 'at 14.5', *go(*TAB['library']), 'at 16'] + pick_preset(0, 'Granite Cloud') +
                      ['at 26', *go(*TAB['playback']), 'wait 0.5', *go(149, 643)] + ['click 149 643'] * 3 + [*go(420, 643)] + ['click 420 643'] * 2 +
                      ['wait 0.5', 'shot v1', 'at 41', 'rec off'], phrase('chords', 31 - WARMUP), program=0, end=41)
    # 6. kits: Kit Manager 98's Echo Chamber Kit, the pad calculator
    S['kits'] = Scene('kits', ['rec cap.bhrc 30', 'at 14.5', *go(*TAB['library']), 'at 16'] + pick_preset(24, 'Echo Chamber Kit') +
                      ['at 23', *go(*TAB['main']), *go(115, 738), 'wait 1.5', 'shot c1', 'at 36', 'shot c2', 'rec off'],
                      phrase('drums', 26 - WARMUP), program=0, end=36)
    # 7. the mine grid: Lucid Strum, a new board, cells dug, a flag
    cell = lambda c, r: (492 + 16 * c, 422 + 16 * r)
    S['mines'] = Scene('mines', ['rec cap.bhrc 30', 'at 14.5', *go(*TAB['library']), 'at 16'] + pick_preset(24, 'Bedroom Tape Kit') +
                       ['at 23', *go(*TAB['mines']), 'wait 1', *go(547, 386), 'wait 1', 'shot m1', *go(*cell(1, 1)), *go(*cell(6, 2)),
                        *go(*cell(3, 6)), 'glide %d %d 0.4' % cell(5, 5), 'rclick %d %d' % cell(5, 5), 'wait 1', 'shot m2',
                        'at 34', *go(547, 386), 'wait 1', *go(*cell(2, 3)), *go(*cell(7, 7)), 'at 44', 'shot m3', 'rec off'],
                       [(25 - WARMUP, 48, 100, 19.0)], program=0, end=44)
    # 8. recording: the synth's own output into the Recorder, then To all 16
    S['rec'] = Scene('rec', ['rec cap.bhrc 30', 'at 14.5', *go(*TAB['library']), 'at 16'] + pick_preset(0, 'Afterhours Tine') +
                     ['at 22', *go(*TAB['rec']), 'wait 0.5', *go(125, 663), 'wait 0.8', *go(*TAB['main']), 'at 25.3', *go(311, 57),
                      'at 34.6', *go(346, 57), 'wait 1', 'shot r1', 'at 36', *go(381, 57), 'at 44', 'shot r2', 'rec off'],
                     phrase('keys', 26 - WARMUP), program=0, end=44)
    # 9. the Song tab: open a song (the host's file dialog answered by BASILISK16_TEST_SONG_OPEN), a preset list, Render, Play
    S['song'] = Scene('song', ['rec cap.bhrc 15', 'at 14.5', *go(*TAB['song']), 'wait 1', *go(727, 87), 'wait 3', 'shot s1',
                               *go(200, 167), 'wait 1', *go(735, 369), 'wait 2.5', 'shot s2', 'key esc', 'wait 1', *go(31, 613),
                               'at 60', 'shot s3', 'at 120', 'shot s4', 'at 130', *go(73, 613),
                               'at 175', 'shot s7', 'rec off'], [(165.0 - WARMUP, 60, 1, 0.1)], program=0, end=175,
                      env=[r'BASILISK16_TEST_SONG_OPEN=C:\Users\willi\video-sw\songs\aquarium-level-three.song'])
    # 10. CITYPOP.EXE on the plugin's desktop (the 1.5 test build: SW15)
    S['citypop'] = Scene('citypop', ['rec cap.bhrc 30', 'at 16', *go(8, 10), 'key n', 'wait 1.5', *go(37, 715), 'key r', 'wait 2',
                                     *go(126, 232, 0.7), 'key enter', 'wait 3', 'shot c1', *go(308, 421, 0.6), 'at 60', 'shot c2', 'rec off'],
                         [(55.0 - WARMUP, 60, 1, 0.1)], program=0, end=60,
                         env=[r'BASILISK16_MYREC=C:\Users\willi\video-sw15\myrec'])
    # explorations (screenshots only)
    S['xkit'] = Scene('xkit', ['at 14.5', *go(*TAB['library']), 'at 16'] + pick_preset(24, 'Echo Chamber Kit') +
                      ['wait 8', 'shot k1', *go(*TAB['main']), 'wait 1.5', 'shot k2', *go(*TAB['voices']), 'wait 1.5', 'shot k3',
                       *go(*TAB['mines']), 'wait 2', 'shot k4', 'at 40'], [(30.0, 60, 1, 0.1)], program=0, end=40)
    return S


def main():
    global PACKS
    ap = argparse.ArgumentParser()
    ap.add_argument('scene', nargs='+')
    ap.add_argument('--sw', default='/mnt/c/Users/willi/video-sw93')
    ap.add_argument('--bundle', default='SNDWAVE1993.vst3')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    PACKS = os.path.join(a.sw, a.bundle, 'Contents/Resources/machine/packs')
    all_ = scenes()
    winsw = subprocess.run(['wslpath', '-w', a.sw], capture_output=True, text=True).stdout.strip()
    for name in a.scene:
        sc = all_[name]
        out = os.path.join(a.sw, 'cap', name)
        os.makedirs(out, exist_ok=True)
        notes = sc.notes or [(0.0, 60, 1, 0.1)]
        mid = os.path.join(out, 'score.mid')
        write_smf(mid, notes)
        json.dump(sorted({round(WARMUP + t, 4) for t, n, v, d in notes} | {round(WARMUP + t + d, 4) for t, n, v, d in notes}),
                  open(os.path.join(out, 'notes.json'), 'w'))   # note on/off times in the WAV (dropouts.py)
        score_len = max(t + d for t, _, _, d in notes)
        tail = max(2.0, (sc.end or 0) + 3 - WARMUP - score_len)
        open(os.path.join(out, 'script.txt'), 'w').write('\n'.join(sc.steps) + '\n')
        cmd = [os.path.join(a.sw, 'BasiliskHost.exe'), '--test', winsw + '\\' + a.bundle, '--tests', 'editor',
               '--midi', winsw + f'\\cap\\{name}\\score.mid', '--tail', f'{tail:.1f}', '--warmup', str(WARMUP),
               '--editor-script-file', winsw + f'\\cap\\{name}\\script.txt', '--out-dir', winsw + f'\\cap\\{name}', '--editor-offline']
        if sc.program is not None: cmd += ['--program', str(sc.program)]
        for e in sc.env: cmd += ['--env', e]
        print(name, ':', len(sc.steps), 'steps,', len(notes), 'notes, render', round(WARMUP + score_len + tail, 1), 's', flush=True)
        if a.dry:
            print('\n'.join(sc.steps)); continue
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(r.stdout[-600:], r.stderr[-300:], flush=True)


if __name__ == '__main__':
    main()
