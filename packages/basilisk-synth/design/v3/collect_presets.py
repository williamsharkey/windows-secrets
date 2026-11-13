"""Collect every real preset DNA for the recipe round-trip test (design/v3/test_recipe.cpp).

    python3 collect_presets.py OUT.txt [--main /path/to/main/checkout] [--aes aesthetic-presets.json] ...

Writes one line per preset: <source> TAB <name> TAB <dna>. Sources (each optional, read-only):
  311-tsv      packages/basilisk-synth-311/presets/*.tsv           (BASILISK 16's programs and overrides)
  311-gen      packages/basilisk-synth-311/plugin/presets_gen.h
  xp-tsv       packages/basilisk-synth/library/presets/*.tsv        (the XP factory presets)
  xp-gen       packages/basilisk-synth/plugin/presets_gen.h
  electromech  packages/basilisk-synth/library/research/electromech-presets.json (instruments and kits)
  targets      packages/basilisk-synth/library/research/preset-targets.json
  aesthetic    design/aesthetic-presets.json (branch design/aesthetic-presets)
  site         site/sndrec/presets.json
"""
import glob
import json
import os
import re
import sys


def tsv(path, tag, out):
    for line in open(path, encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            continue
        f = line.rstrip('\n').split('\t')
        if len(f) >= 3 and f[2].strip():
            out.append((tag, f[0] + ': ' + f[1], f[2].strip()))


def gen(path, tag, out):
    for m in re.finditer(r'\{\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\}', open(path, encoding='utf-8').read()):
        out.append((tag, m.group(1), m.group(2)))


def walk(x, tag, out, name=''):
    if isinstance(x, dict):
        nm = x.get('name') or x.get('id') or name
        for k, v in x.items():
            if k == 'dna' and isinstance(v, str) and v.strip():
                out.append((tag, str(nm), v.strip()))
            else:
                walk(v, tag, out, nm)
    elif isinstance(x, list):
        for v in x:
            walk(v, tag, out, name)


def main():
    a = sys.argv[1:]
    dst = a[0]
    opt = dict(zip(a[1::2], a[2::2]))
    main_ = opt.get('--main', '')
    out = []
    if main_:
        for p in sorted(glob.glob(os.path.join(main_, 'packages/basilisk-synth-311/presets/*.tsv'))):
            tsv(p, '311-tsv', out)
        p = os.path.join(main_, 'packages/basilisk-synth-311/plugin/presets_gen.h')
        if os.path.exists(p):
            gen(p, '311-gen', out)
        for p in sorted(glob.glob(os.path.join(main_, 'packages/basilisk-synth/library/presets/*.tsv'))):
            tsv(p, 'xp-tsv', out)
        p = os.path.join(main_, 'packages/basilisk-synth/plugin/presets_gen.h')
        if os.path.exists(p):
            gen(p, 'xp-gen', out)
        for tag, rel in (('electromech', 'packages/basilisk-synth/library/research/electromech-presets.json'),
                         ('targets', 'packages/basilisk-synth/library/research/preset-targets.json'),
                         ('site', 'site/sndrec/presets.json')):
            p = os.path.join(main_, rel)
            if os.path.exists(p):
                walk(json.load(open(p, encoding='utf-8')), tag, out)
    if '--aes' in opt and os.path.exists(opt['--aes']):
        walk(json.load(open(opt['--aes'], encoding='utf-8')), 'aesthetic', out)
    with open(dst, 'w', encoding='utf-8') as f:
        for t, n, d in out:
            f.write('%s\t%s\t%s\n' % (t, n.replace('\t', ' '), d))
    counts = {}
    for t, _, _ in out:
        counts[t] = counts.get(t, 0) + 1
    print(len(out), 'presets', counts)


if __name__ == '__main__':
    main()
