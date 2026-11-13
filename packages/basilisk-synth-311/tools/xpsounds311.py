#!/usr/bin/env python3
"""XP's sounds for BASILISK 16 (DNA.md 2.4: one name, one file): every XP file of core kSoundFiles311, converted to PCM
that Windows 3.11's Sound Recorder opens, named X<index>.WAV for C:\\XPSOUNDS.

    xpsounds311.py XP_IMAGE OUT_DIR --extractor PATH/TO/archaeology/extract.py

No Microsoft audio is in git: the sounds come from the user's own XP image (BASILISK SYNTH's base.qcow2), through the
sound-archaeology extractor (packages/basilisk-synth/archaeology, branch feat/sound-archaeology), which checks each
file's sha1 against its catalog. make_machine.py --xpsounds OUT_DIR puts them on the drive.
"""
import argparse, csv, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(HERE, '..', '..', 'basilisk-synth', 'core', 'dna.cpp')


def table(name):
    src = open(CORE).read()
    return re.findall(r'"([^"]+)"', src.split(name + '[kSoundCount] = {', 1)[1].split('};', 1)[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image'); ap.add_argument('out'); ap.add_argument('--extractor', required=True)
    a = ap.parse_args()
    xp, f311 = table('kSoundFilesXP'), table('kSoundFiles311')
    cat = list(csv.DictReader(open(os.path.join(os.path.dirname(a.extractor), 'catalog.csv'))))
    picks = []
    for i, (f, t) in enumerate(zip(xp, f311)):
        if 'XPSOUNDS' not in t:
            continue
        hit = [r for r in cat if r['os'] == 'xp' and r['where'] == 'file' and r['path'].lower().endswith('\\media\\' + f.lower())]
        if not hit:
            sys.exit('xpsounds311: %s is not in the catalog' % f)
        picks.append('%s X%02d' % (hit[0]['id'], i))
    os.makedirs(a.out, exist_ok=True)
    pf = os.path.join(a.out, 'picks.txt')
    open(pf, 'w').write('\n'.join(picks) + '\n')
    subprocess.run([sys.executable, a.extractor, a.image, '--os', 'xp', '--target', '311', '--ids', pf, '--out', a.out], check=True)
    os.remove(pf)
    print('%d XP sounds -> %s' % (len(picks), a.out))


if __name__ == '__main__':
    main()
