#!/usr/bin/env python3
"""Editor captures of BASILISK SYNTH (XP) for sndrec.html, through bsynth-host --editor --shots (Windows, from WSL).

    xp_video.py RENDER_DIR WORKDIR --host bsynth-host.exe --plugin BasiliskSynth.vst3 [CLIP ...]

bsynth-host opens the plugin's real editor in a window, plays in real time and saves the window's pixels every 1/30 s
on the same clock as its WAV, from the moment the plugin loads (so the assembly is in it). The window must stay
visible and uncovered on screen while it records. Frames: WORKDIR/<clip>/NNNNNN.bmp, audio WORKDIR/<clip>.wav.
Then: pxv.py encode WORKDIR/<clip> ... --start <frame> (the clip's 'start' seconds x 30) and the audio from the same
second, so picture and sound stay together.

Clips (RENDER_DIR is phrases.py's XP output; scores come from its MIDI files):
  assembly  Chord Organ from plugin load: XP wakes, the sixteen Sound Recorders assemble, the phrase plays
  play      Wide Chimes (three layers, panned): a melody, keys going down in XP
  change    Kalimba Glass arpeggios, then the program changes to Choir Pad while it plays: XP rebuilds in view
  macro     Macro Swell, Macro 1 stepped 35, 70, 100, 20 % (XP's DNA box and Macros panel follow each step)
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'packages', 'basilisk-synth', 'tools'))
import batch_render

WARM = 10.0


def score(mid, at=0.0):
    return [(t + at, n, v, d) for t, n, v, d in batch_render.midi_score(mid)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('render'); ap.add_argument('work'); ap.add_argument('clips', nargs='*')
    ap.add_argument('--host', required=True); ap.add_argument('--plugin', required=True)
    a = ap.parse_args()
    rows = {r['name']: r for r in json.load(open(os.path.join(a.render, 'presets.json')))}
    mid = lambda name: os.path.join(a.render, 'mid', rows[name]['slug'] + '.mid')
    clips = {
        'assembly': dict(program=rows['Chord Organ']['i'], dna=rows['Chord Organ']['dna'], notes=score(mid('Chord Organ'), 0.5), tail=2, start=0),
        'play': dict(program=rows['Wide Chimes']['i'], dna=rows['Wide Chimes']['dna'], notes=score(mid('Wide Chimes'), 0.5), tail=2.5, start=WARM - 0.5),
        'change': dict(program=rows['Kalimba Glass']['i'], dna=rows['Kalimba Glass']['dna'], notes=score(mid('Kalimba Glass'), 0.5) + score(mid('Choir Pad'), 6.5),
                       sets=[('program', 5.6, rows['Choir Pad']['i'])], tail=2.5, start=WARM - 0.5),
        'macro': dict(program=rows['Macro Swell']['i'], dna=rows['Macro Swell']['dna'], notes=score(mid('Macro Swell'), 0.5), tail=2,
                      # held steps, not a ramp: the plugin tells Windows the new DNA 300 ms after the last change, so the
                      # DNA box and the Macros panel in XP follow each step (the sound follows at once either way)
                      sets=[('Macro 1', 1.5, 35), ('Macro 1', 3.5, 70), ('Macro 1', 5.5, 100), ('Macro 1', 7.5, 20)],
                      start=WARM - 0.5),
    }
    win = lambda p: subprocess.run(['wslpath', '-w', p], capture_output=True, text=True).stdout.strip()
    meta = {}
    for name in a.clips or list(clips):
        c = clips[name]
        d = os.path.join(a.work, name); os.makedirs(d, exist_ok=True)
        for f in os.listdir(d): os.remove(os.path.join(d, f))
        sc = ','.join('%.4f:%d:%d:%.4f' % n for n in sorted(c['notes']))
        args = ['--editor', '--shots', '0.0333333', win(d), '--warmup', str(WARM), '--tail', str(c['tail']), '--score', sc,
                '--dna', c['dna']]   # the starting sound is in the state before the plugin loads, so the assembly builds it
        for p, t, v in c.get('sets', []): args += ['--set', '%s@%.3f=%.2f' % (p, t, v)]
        bat = os.path.join(a.work, name + '.bat')
        with open(bat, 'w') as f:
            f.write('@echo off\r\n"%s" "%s" "%s" %s\r\n' % (win(a.host), win(a.plugin), win(os.path.join(a.work, name + '.wav')),
                                                         ' '.join('"%s"' % x for x in args)))
        r = subprocess.run(['cmd.exe', '/c', win(bat)], capture_output=True, text=True, cwd=a.work, timeout=900)
        n = len([f for f in os.listdir(d) if f.endswith('.bmp')])
        meta[name] = {'program': c['program'], 'start': c['start'], 'frames': n, 'log': r.stdout.strip()[-300:]}
        print(name, n, 'frames;', r.stdout.strip().splitlines()[-4:] if r.stdout.strip() else r.stderr[-200:], flush=True)
    json.dump(meta, open(os.path.join(a.work, 'clips.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
