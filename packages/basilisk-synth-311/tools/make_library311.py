#!/usr/bin/env python3
"""The library disc for Windows 3.11 (DNA.md 5.5): library.zip, mounted as drive L: next to C:.

  make_library311.py OUT.zip [--sources packages/basilisk-synth/library/sources]
                             [--presets ONE.tsv] [--max-seconds 30]

Sounds: every SOURCES/<category>/*.wav; names follow the XP disc (packages/basilisk-synth/tools/make_library.py):
[a-z0-9_]+ with '#' -> 's', built-in NAMEs are never taken, so a DNA plays the same sound in both editions.
Also writes OUT.names.txt (the plugin's catalogue for bsynth::setLibrary).

Windows 3.11 only knows 8.3 file names, so every category gets an 8-character folder and every sound an
8-character file (the DNA keeps the sound's real name: LIBRARY.TSV maps it). The WAVs stay what the library
builder made (PCM 16-bit, 22050 Hz, mono): Sound Recorder 3.1 opens those as they are. Anything else (other rates,
float, 24-bit, stereo) is converted to that. Dates are fixed, so the same inputs give the same zip on every machine
(the snapshot is made with this drive mounted).

LIBRARY.TSV: name TAB category TAB \\FOLDER\\FILE.WAV TAB seconds TAB source/licence
PRESETS.TSV: category TAB name TAB DNA (make_presets311.py: presets/b16.tsv, then the shared library/presets)
"""
import argparse, glob, io, json, os, re, sys, wave, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SYNTH = os.path.join(HERE, '..', '..', 'basilisk-synth')
DATE = (1993, 11, 8, 3, 11, 0)


def short(word, used, n=8):
    base = re.sub(r'[^A-Z0-9]', '', word.upper())[:n] or 'X'
    cand, k = base, 1
    while cand in used:
        suf = str(k); cand = base[:n - len(suf)] + suf; k += 1
    used.add(cand)
    return cand


def to_311(path):
    """PCM 16-bit mono 22050 Hz bytes of a WAV (resampled/converted if needed), and its length in seconds"""
    with wave.open(path) as w:
        ch, sw, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2: x = np.frombuffer(raw, '<i2').astype(np.float64) / 32768
    elif sw == 1: x = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128) / 128
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16); v = np.where(v >= 1 << 23, v - (1 << 24), v); x = v / float(1 << 23)
    elif sw == 4: x = np.frombuffer(raw, '<i4').astype(np.float64) / 2 ** 31
    else: raise ValueError('sample width %d' % sw)
    x = x.reshape(-1, ch).mean(axis=1)
    if rate != 22050:
        t = np.arange(int(len(x) * 22050 / rate)) * rate / 22050
        x = np.interp(t, np.arange(len(x)), x)
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    out = io.BytesIO()
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(pcm)
    return out.getvalue(), len(x) / 22050


def dna_name(stem):
    """the XP lane's rule (packages/basilisk-synth/tools/make_library.py): [a-z0-9_]+, '#' becomes 's'"""
    s = stem.lower().replace('#', 's')
    s = re.sub(r'[^a-z0-9_]', '_', s)
    return re.sub(r'_+', '_', s).strip('_')


def builtins():
    core = os.path.join(SYNTH, 'core', 'dna.cpp')
    return set(re.findall(r'"([a-z0-9]+)"', open(core).read().split('kSoundNames', 1)[1].split('};', 1)[0]))


def licences(manifest):
    out = {}
    paths = glob.glob(os.path.join(SYNTH, 'library', 'catalog', '*.json')) + ([manifest] if os.path.exists(manifest) else [])
    for p in paths:
        try: data = json.load(open(p))
        except Exception: continue
        items = data if isinstance(data, list) else data.get('files', data.get('sounds', []))
        for e in items:
            if not isinstance(e, dict): continue
            k = e.get('id') or os.path.splitext(os.path.basename(e.get('file', '')))[0]
            if k: out[dna_name(k)] = '%s, %s' % (e.get('author', '?'), e.get('license', '?'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--sources', default=os.path.join(SYNTH, 'library', 'sources'))
    ap.add_argument('--presets', help='one .tsv instead of the programs of make_presets311.py')
    ap.add_argument('--max-seconds', type=float, default=30)
    a = ap.parse_args()
    lic = licences(os.path.join(a.sources, 'manifest.json'))
    taken = builtins()
    used_dirs, lines, names, ncat = set(), [], [], 0
    z = zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
    def put(name, data):
        zi = zipfile.ZipInfo(name, date_time=DATE); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
        z.writestr(zi, data)
    for cdir in sorted(glob.glob(os.path.join(a.sources, '*'))) if os.path.isdir(a.sources) else []:
        files = sorted(glob.glob(os.path.join(cdir, '*.wav'))) if os.path.isdir(cdir) else []
        if not files: continue
        cat = dna_name(os.path.basename(cdir)); dname = short(cat, used_dirs); used_files = set(); made = 0
        for f in files:
            nm = dna_name(os.path.splitext(os.path.basename(f))[0])
            if not nm or nm in taken: print('skip (name taken): %s' % f, file=sys.stderr); continue
            try: data, sec = to_311(f)
            except Exception as ex: print('skip %s: %s' % (f, ex), file=sys.stderr); continue
            if sec > a.max_seconds: print('skip %s: %.1f s' % (f, sec), file=sys.stderr); continue
            if not made:
                zi = zipfile.ZipInfo(dname + '/', date_time=DATE); zi.external_attr = 0o40755 << 16 | 0x10; z.writestr(zi, b'')
            made += 1; taken.add(nm); names.append(nm)
            fn = short(nm, used_files) + '.WAV'
            put('%s/%s' % (dname, fn), data)
            lines.append('%s\t%s\t\\%s\\%s\t%.2f\t%s' % (nm, cat, dname, fn, sec, lic.get(nm, 'see LICENSES').replace('\t', ' ')))
        ncat += made > 0
    put('LIBRARY.TSV', ''.join(l + '\r\n' for l in lines).encode('cp1252', 'replace'))
    import make_presets311   # the same rows, in the same order, as the plugin's program list
    pre = ['\t'.join(r) for r in make_presets311.rows([a.presets] if a.presets else None)]
    put('PRESETS.TSV', ''.join(r + '\r\n' for r in pre).encode('cp1252', 'replace'))
    z.close()
    # the plugin's catalogue (bsynth::setLibrary): the names a DNA may use besides the built-in ones
    with open(os.path.splitext(a.out)[0] + '.names.txt', 'w') as f: f.write(''.join(n + '\n' for n in sorted(names)))
    print('library: %d sounds in %d categories, %d presets -> %s (%d bytes)' % (len(lines), ncat, len(pre), a.out, os.path.getsize(a.out)))


if __name__ == '__main__':
    main()
