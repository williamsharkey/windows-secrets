#!/usr/bin/env python3
"""Build the library disc (DNA.md 5.6): an ISO 9660 + Joliet image that the plugin puts in XP's CD drive.

    make_library.py OUT.iso [--sources library/sources] [--presets library/presets]

Layout on the disc:
    \\LIBRARY.TSV                 name <TAB> category <TAB> path <TAB> seconds <TAB> source/licence  (CRLF)
    \\PRESETS.TSV                 category <TAB> name <TAB> DNA                                       (CRLF)
    \\<category>\\<name>.wav

Sounds are every library/sources/<category>/*.wav (PCM). Names are made DNA-safe ([a-z0-9_]+: '#' becomes 's',
anything else '_'); the licence column comes from library/sources/manifest.json or library/catalog/*.json when
there is an entry for the file. Also writes OUT.names.txt (one name per line) for the plugin's catalogue.
"""
import argparse, glob, io, json, os, re, sys, wave

import pycdlib

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def dna_name(stem):
    s = stem.lower().replace('#', 's')
    s = re.sub(r'[^a-z0-9_]', '_', s)
    return re.sub(r'_+', '_', s).strip('_')


def licences():
    out = {}
    paths = glob.glob(os.path.join(PKG, 'library', 'catalog', '*.json'))
    man = os.path.join(PKG, 'library', 'sources', 'manifest.json')
    if os.path.exists(man):
        paths.append(man)
    for p in paths:
        try:
            data = json.load(open(p))
        except Exception:
            continue
        items = data if isinstance(data, list) else data.get('sounds', data.get('entries', []))
        for e in items:
            if not isinstance(e, dict):
                continue
            k = e.get('id') or os.path.splitext(os.path.basename(e.get('file', '')))[0]
            if k:
                out[dna_name(k)] = '%s, %s' % (e.get('author', '?'), e.get('license', '?'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--sources', default=os.path.join(PKG, 'library', 'sources'))
    ap.add_argument('--presets', default=os.path.join(PKG, 'library', 'presets'))
    a = ap.parse_args()
    lic = licences()
    builtin = set()
    core = os.path.join(PKG, 'core', 'dna.cpp')
    for m in re.finditer(r'"([a-z0-9]+)"', open(core).read().split('kSoundNames', 1)[1].split('};', 1)[0]):
        builtin.add(m.group(1))

    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, joliet=3, vol_ident='BSYNTH_LIBRARY')
    rows, names, ncat = [], set(), {}
    total = 0
    for cdir in sorted(glob.glob(os.path.join(a.sources, '*'))):
        if not os.path.isdir(cdir):
            continue
        cat = dna_name(os.path.basename(cdir))
        files = sorted(glob.glob(os.path.join(cdir, '*.wav')))
        if not files:
            continue
        ci = len(ncat)
        ncat[cat] = 0
        iso.add_directory('/C%02d' % ci, joliet_path='/' + cat)
        for f in files:
            nm = dna_name(os.path.splitext(os.path.basename(f))[0])
            if not nm or nm in names or nm in builtin:
                print('skip (name taken): %s' % f, file=sys.stderr)
                continue
            try:
                w = wave.open(f)
                secs = w.getnframes() / float(w.getframerate())
                w.close()
            except Exception as e:
                print('skip (not PCM wav): %s %s' % (f, e), file=sys.stderr)
                continue
            names.add(nm)
            data = open(f, 'rb').read()
            total += len(data)
            k = ncat[cat]
            ncat[cat] += 1
            iso.add_fp(io.BytesIO(data), len(data), '/C%02d/S%05d.WAV;1' % (ci, k), joliet_path='/%s/%s.wav' % (cat, nm))
            rows.append('\t'.join([nm, cat, '\\%s\\%s.wav' % (cat, nm), '%.3f' % secs, lic.get(nm, 'see LICENSES')]))

    def add_text(iso_name, joliet, text):
        b = text.encode('cp1252', 'replace')
        iso.add_fp(io.BytesIO(b), len(b), '/' + iso_name + ';1', joliet_path='/' + joliet)

    add_text('LIBRARY.TSV', 'LIBRARY.TSV', ''.join(r + '\r\n' for r in rows))
    pre = []
    for p in sorted(glob.glob(os.path.join(a.presets, '*.tsv'))):
        for ln in open(p, encoding='utf-8'):
            ln = ln.rstrip('\r\n')
            if ln and not ln.startswith('#') and ln.count('\t') >= 2:
                pre.append(ln)
    add_text('PRESETS.TSV', 'PRESETS.TSV', ''.join(r + '\r\n' for r in pre))
    iso.write(a.out)
    iso.close()
    with open(a.out + '.names.txt', 'w') as f:
        f.write(''.join(n + '\n' for n in sorted(names)))
    print('%s: %d sounds in %d categories (%.1f MB of audio), %d presets' % (a.out, len(rows), len(ncat), total / 1e6, len(pre)))


if __name__ == '__main__':
    main()
