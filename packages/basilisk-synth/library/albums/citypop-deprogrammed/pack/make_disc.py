#!/usr/bin/env python3
"""The Rainy Loft Collection disc (pack id rainy-loft, label RAINYLOFT), in the layout of the other pack discs
(library/builder/INTEGRATION.md): PACK.INF, PACK.TXT, AUTORUN.INF, README.TXT, PRESETS.TSV, LIBRARY.TSV,
<CATEGORY>\\<NAME>.BSP and \\SOUNDS.

    make_disc.py SOUNDS_DIR DISC_DIR [--install MACHINE_PACKS_DIR]

SOUNDS_DIR is build_sounds.py's output. --install also copies the disc into a machine's packs folder as RAINYLOF
and adds (or replaces) its line in PACKS.TSV and its sound names in packs.names.txt.
"""
import argparse, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
PID, LABEL, DIR, TITLE = 'rainy-loft', 'RAINYLOFT', 'RAINYLOF', 'Rainy Loft Collection'
MAKER = 'Harborlight Audio Works Co., Ltd.'
DATE = '1988-06-21'
BLURB = 'Late-evening keys, fretless bass, reeds and the weather outside. For after the club.'

README = """Rainy Loft Collection
Sound Library for Evening Production, version 1.0
(c) 1988 Harborlight Audio Works Co., Ltd. Onomichi Studio.

README.TXT
----------------------------------------------------------------------------

1. INTRODUCTION

The Rainy Loft Collection is a library of sounds for music made after dark.
It contains electric pianos recorded through our ensemble and tape chain,
three basses, two reeds, two muted trumpets, flutes, bells, a brush kit, a
stick kit, a disco kit, hand percussion, and the weather: rain on glass, rain
on a balcony, a quiet city, a train on the far side of the harbour, an
espresso machine and a record player.

The electric pianos and basses are multisampled across the keyboard. Each
zone plays from its own recording. Play them gently. They respond to how
hard you play.

2. GETTING STARTED

Insert the disc. In SNDWAVE2000 open the Library tab, choose RAINYLOFT and
pick a preset. Texture and FX presets play at the pitch they were recorded at,
whatever key you press. Hold a key to hear the weather. Release it to let the
weather go.

3. CONTENTS OF THE DISC

  KEYS\\     electric pianos (Loft Tine, Glass Tine, Suitcase Night ...)
  BASS\\     fretless, pluck, rubber, pizzicato
  LEAD\\     reed, flutes, muted trumpets, clarinet
  BELL\\     crystal, glass, chime, harmonics
  PLUCK\\    muted guitar, pizzicato
  VOCAL\\    PAD\\    choir and strings
  KIT\\      Loft Brushes, Loft Sticks, Couch Disco, Loft Percussion
  TEXTURE\\  FX\\     rain, city, vinyl, espresso, trains, horns
  SOUNDS\\   the recordings themselves (LIBRARY.TSV lists their sources)

The recordings are in the public domain (CC0) or were made by the publisher.
LIBRARY.TSV names the source and the licence of every sound.

4. TECHNICAL SUPPORT

Harborlight Audio Works Co., Ltd.
Onomichi Studio, on the slope above the harbour
Onomichi, Hiroshima, Japan
Letters are answered in the evening.
"""


def bsp_name(name, used):
    b = re.sub(r'[^A-Z0-9]', '', name.upper())[:8] or 'PRESET'
    n, k = b, 1
    while n in used:
        k += 1; n = b[:8 - len(str(k))] + str(k)
    used.add(n)
    return n + '.BSP'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sounds'); ap.add_argument('disc'); ap.add_argument('--install')
    ap.add_argument('--from-packs', default=os.path.expanduser('~/cpd/machine/packs'),
                    help='installed pack discs to copy borrowed sounds from, so this disc stands alone')
    ap.add_argument('--library-names', default=os.path.expanduser('~/cpd/machine/library.names.txt'))
    a = ap.parse_args()
    shutil.rmtree(a.disc, ignore_errors=True)
    os.makedirs(a.disc)
    pres = []
    for l in open(os.path.join(HERE, 'presets.tsv'), encoding='utf-8'):
        if l.startswith('#') or not l.strip():
            continue
        c, n, d = l.rstrip('\n').split('\t')[:3]
        pres.append((c, n, d))
    # the sounds the presets name: our own (rl_), the built-in library disc's, or borrowed from another pack disc
    lib = set(l.strip() for l in open(a.library_names) if l.strip())
    names = set()
    for c, n, d in pres:
        lay = d.split(';')[0]
        for tok in re.findall(r'(?:^|/|I|M)([a-z][a-z0-9_]+)', lay):
            names.add(tok)
    own = [l.rstrip('\r\n').split('\t') for l in open(os.path.join(a.sounds, 'LIBRARY.TSV'), encoding='cp1252') if l.strip() and not l.startswith('#')]
    keep = [r for r in own if r[0] in names]
    os.makedirs(os.path.join(a.disc, 'SOUNDS'), exist_ok=True)
    for r in keep:
        src = os.path.join(a.sounds, *r[2].strip('\\').split('\\'))
        dst = os.path.join(a.disc, *r[2].strip('\\').split('\\'))
        os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
    have = set(r[0] for r in keep) | lib
    borrowed = []
    for nm in sorted(names - have):
        for d in sorted(os.listdir(a.from_packs)):
            lt = os.path.join(a.from_packs, d, 'LIBRARY.TSV')
            if d == DIR or not os.path.exists(lt):
                continue
            row = next((l.rstrip('\r\n').split('\t') for l in open(lt, encoding='cp1252') if l.startswith(nm + '\t')), None)
            if row:
                fn = 'B' + os.path.basename(row[2].replace('\\', '/'))[1:]
                path = f'\\SOUNDS\\BORROWED\\{fn}'
                os.makedirs(os.path.join(a.disc, 'SOUNDS', 'BORROWED'), exist_ok=True)
                shutil.copy(os.path.join(a.from_packs, d, *row[2].strip('\\').split('\\')), os.path.join(a.disc, 'SOUNDS', 'BORROWED', fn))
                borrowed.append([row[0], row[1], path, row[3], row[4]])
                break
        else:
            if nm not in have:
                print('make_disc: WARNING no source for', nm)
    with open(os.path.join(a.disc, 'LIBRARY.TSV'), 'w', encoding='cp1252', newline='') as f:
        f.write('# name\tcategory\tpath\tseconds\tsource/licence\r\n')
        for r in keep + borrowed:
            f.write('\t'.join(r) + '\r\n')
    print(f'sounds: {len(keep)} own, {len(borrowed)} borrowed, {len(own) - len(keep)} unused left off')
    rows, used = [], {}
    for c, n, d in pres:
        folder = c.upper()
        fn = bsp_name(n, used.setdefault(folder, set()))
        os.makedirs(os.path.join(a.disc, folder), exist_ok=True)
        open(os.path.join(a.disc, folder, fn), 'wb').write((d + '\r\n').encode('ascii'))
        rows.append('\t'.join([c, n, d, PID, '3.11', '', '-', f'{folder}\\{fn}']))
    hdr = '# SNDWAVE2000 by Algorithmic Industries presets: category\tname\tDNA\tpack\teditions\trating\tverdict\tfile'
    open(os.path.join(a.disc, 'PRESETS.TSV'), 'wb').write(('\r\n'.join([hdr] + rows) + '\r\n').encode('cp1252'))
    inf = (f'[Pack]\r\nId={PID}\r\nTitle={TITLE}\r\nProduct=SNDWAVE2000 by Algorithmic Industries\r\nVersion=1.0\r\n'
           f'Author={MAKER}\r\nDate={DATE}\r\nPresets={len(rows)}\r\nPresets311={len(rows)}\r\nPresetsXP=0\r\n'
           f'Favourites=0\r\nDescription={BLURB}\r\n')
    open(os.path.join(a.disc, 'PACK.INF'), 'wb').write(inf.encode('cp1252'))
    open(os.path.join(a.disc, 'PACK.TXT'), 'wb').write(inf.replace('[Pack]\r\n', f'{TITLE}\r\n\r\n').encode('cp1252'))
    open(os.path.join(a.disc, 'AUTORUN.INF'), 'wb').write(f'[autorun]\r\nlabel={TITLE}\r\n'.encode('cp1252'))
    open(os.path.join(a.disc, 'README.TXT'), 'wb').write(README.replace('\n', '\r\n').encode('cp1252'))
    print(f'{TITLE}: {len(rows)} presets -> {a.disc}')
    if a.install:
        dst = os.path.join(a.install, DIR)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(a.disc, dst)
        pt = os.path.join(a.install, 'PACKS.TSV')
        lines = [l for l in open(pt, encoding='cp1252').read().split('\r\n') if l and not l.startswith(DIR + '\t')]
        lines.append('\t'.join([DIR, PID, LABEL, TITLE, str(len(rows))]))
        open(pt, 'wb').write(''.join(l + '\r\n' for l in lines).encode('cp1252'))
        names = [l.split('\t')[0] for l in open(os.path.join(a.disc, 'LIBRARY.TSV'), encoding='cp1252') if l.strip() and not l.startswith('#')]
        pn = os.path.join(a.install, 'packs.names.txt')
        old = [l.strip() for l in open(pn) if l.strip() and not l.startswith('rl_')]
        open(pn, 'w').write(''.join(n + '\n' for n in old + names))
        print(f'installed in {dst}')


if __name__ == '__main__':
    main()
