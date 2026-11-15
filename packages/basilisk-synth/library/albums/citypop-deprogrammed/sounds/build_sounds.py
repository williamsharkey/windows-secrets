#!/usr/bin/env python3
"""The Rainy Loft Collection's sounds: prepared offline from CC0 / public-domain recordings and from the owner's
own instruments, written as 3.11-ready WAVs (22050 Hz, 16-bit, mono, at most 30 s) with a LIBRARY.TSV and a
provenance file.

    build_sounds.py OUT_DIR [--raw library/sources-raw/citypop] [--garden ~/cpd/garden/cpd_render] [--only NAME,...]

- CC0 / PD sources: the Freesound previews fetched by library/tools/fetch.py (catalog: rainy_loft.json beside this
  script records each one's page, author, licence and proof).
- The owner's instruments: the Bele Dance electric piano and the Cricket bass (midigarden), rendered offline one
  note at a time by a private harness (--garden). Their code stays private; only the rendered audio is used.

Preparation is ordinary studio work done before sampling: trimming, filtering, soft tape saturation, a mono
ensemble, a short room, retuning to the nearest semitone, seamless loops for ambiences.
"""
import argparse, json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsp   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OWNER = 'William Sharkey (rendered from his own instruments, Bele Dance / midigarden); for SNDWAVE1993 packs'


def bele(garden, kind, *args):
    d = subprocess.run([garden, kind] + [str(a) for a in args], capture_output=True, check=True).stdout
    return dsp.raw(d)


def ep(garden, model, tone, char, trem, midi, vel, hold, chorus=0.35, drive=1.3, lpf=9000, roomy=0.12):
    x = bele(garden, 'ep', model, tone, char, trem, midi, vel, hold)
    x = dsp.hp(x, 30)
    if chorus:
        x = dsp.chorus(x, chorus)
    x = dsp.tape(x, drive, warm=1.5)
    x = dsp.lp(x, lpf, 2)
    if roomy:
        x = dsp.room(x, roomy, 0.7, 4500, seed=midi)
    return dsp.fades(dsp.trim_end(x, -62), 0.5, 60)


def bass(garden, model, midi, hold, a=None, b=None, c=None, lpf=3200, drive=1.4):
    D = [(.42, .58, .20), (.22, .78, .12), (.54, .64, .38), (.46, .56, .28), (.72, .68, .44), (.62, .48, .24)][model]
    a, b, c = a if a is not None else D[0], b if b is not None else D[1], c if c is not None else D[2]
    x = bele(garden, 'bass', model, a, b, c, midi, hold)
    x = dsp.hp(x, 28, 2)
    x = dsp.tape(x, drive, warm=1.0)
    x = dsp.lp(x, lpf, 2)
    return dsp.fades(dsp.trim_end(x, -60), 0.3, 40)


def excerpt_steady(x, seconds, hop=0.5):
    """the steadiest window of a recording (least level variation, no sudden events): for ambiences"""
    n = int(seconds * dsp.SR)
    if len(x) <= n:
        return x
    w = int(0.25 * dsp.SR)
    env = np.array([np.sqrt(np.mean(x[i:i + w] ** 2)) + 1e-9 for i in range(0, len(x) - w, w)])
    db = 20 * np.log10(env)
    k = n // w
    best, bs = 0, 1e9
    for i in range(0, len(db) - k, max(1, int(hop / 0.25))):
        seg = db[i:i + k]
        s = np.std(seg) + 0.5 * max(0, np.max(seg) - np.median(seg) - 6)
        if s < bs:
            best, bs = i, s
    return x[best * w: best * w + n]


def hits(x, n=4, min_gap=0.08, max_len=1.2, thresh_db=-30):
    """the n cleanest separate hits of a multi-hit recording"""
    x = np.concatenate([np.zeros(int(0.02 * dsp.SR)), x])
    w = int(0.005 * dsp.SR)
    env = np.array([np.max(np.abs(x[i:i + w])) for i in range(0, len(x) - w, w)])
    db = 20 * np.log10(env / (np.max(env) + 1e-12) + 1e-9)
    on = []
    for i in range(2, len(db)):
        if db[i] > thresh_db and db[i] - db[i - 2] > 12 and (not on or (i - on[-1]) * 0.005 > min_gap):
            on.append(i)
    segs = []
    for j, i in enumerate(on):
        a = max(0, i * w - int(0.003 * dsp.SR))
        b = (on[j + 1] * w - int(0.004 * dsp.SR)) if j + 1 < len(on) else len(x)
        b = min(b, a + int(max_len * dsp.SR))
        s = x[a:b]
        if len(s) < int(0.03 * dsp.SR):
            continue
        # quality: loud, and quiet before the next hit (a clean tail)
        pk = np.max(np.abs(s)); tail = np.max(np.abs(s[-int(0.01 * dsp.SR):])) / (pk + 1e-12)
        segs.append((pk * (1 - tail), dsp.fades(dsp.trim_end(s, -50, 20), 0.3, 15)))
    segs.sort(key=lambda z: -z[0])
    return [s for _, s in segs[:n]]


def tonal(x, target=None, lo=40, hi=1500, start=0.1):
    f = dsp.f0(x, lo, hi, start)
    m = dsp.midi_of(f)
    tgt = int(round(m)) if target is None else target
    return dsp.retune(x, f, tgt), tgt, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--raw', default=os.path.join(LIB, 'sources-raw', 'citypop'))
    ap.add_argument('--garden', default=os.path.expanduser('~/cpd/garden/cpd_render'))
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    only = set(a.only.split(',')) - {''}
    cat = {c['id']: c for c in json.load(open(os.path.join(HERE, 'rainy_loft.json')))} \
        if os.path.exists(os.path.join(HERE, 'rainy_loft.json')) else {}
    out, rows, prov = a.out, [], []
    os.makedirs(out, exist_ok=True)

    def R(fid, start=0.0, dur=None):
        return dsp.load(os.path.join(a.raw, cat[fid]['raw'].split('/', 1)[1]), start, dur)

    def emit(name, category, x, src, note='', loop=False, seconds=30.0, peak=-1.0, rms=None):
        if only and name not in only:
            return
        x = dsp.norm_rms(x, rms, peak) if rms is not None else dsp.norm(x, peak)
        sub = {'keys': 'KEYS', 'bass': 'BASS', 'lead': 'LEAD', 'bell': 'BELL', 'pad': 'PAD', 'pluck': 'PLUCK',
               'kit': 'KIT', 'perc': 'PERC', 'texture': 'TEXTURE'}[category]
        fn = name.upper().replace('RL_', '')[:8] + '.WAV'
        # unique 8.3 names inside each folder
        while any(r[2].endswith('\\' + fn) and r[2].startswith('\\SOUNDS\\' + sub) for r in rows):
            fn = fn[:6] + '%02d' % (len(rows) % 100) + '.WAV'
        path = os.path.join(out, 'SOUNDS', sub, fn)
        secs = dsp.write311(path, x, seconds)
        srcs = src if isinstance(src, list) else [src]
        lic = ' + '.join(sorted(set(('CC0-1.0' if s in cat else 'owner') for s in srcs)))
        rows.append((name, category, f'\\SOUNDS\\{sub}\\{fn}', f'{secs:.2f}',
                     '; '.join(f'{cat[s]["author"]} (Freesound {s[3:]}, CC0)' if s in cat else OWNER for s in srcs)))
        prov.append({'name': name, 'file': f'SOUNDS/{sub}/{fn}', 'seconds': round(secs, 2), 'note': note,
                     'sources': [{k: cat[s].get(k) for k in ('id', 'description', 'author', 'license', 'license_proof_url', 'source_url')}
                                 if s in cat else {'id': s, 'author': 'William Sharkey', 'license': OWNER} for s in srcs]})
        print(f'{name:28s} {secs:5.2f}s  {fn}  {note}')

    G = a.garden
    # ---- keys: the Bele Dance electric piano, five roots, with an ensemble, tape and a small room
    for midi in (36, 48, 60, 72, 84):
        hold = 4.5 if midi <= 60 else 3.5 if midi == 72 else 2.6
        emit(f'rl_ep_loft_{dsp.note_name(midi)}', 'keys', ep(G, 0, .40, .30, .30, midi, .62, hold), 'bele:ep/tine',
             'tine, soft hammer, ensemble, tape')
        emit(f'rl_ep_bright_{dsp.note_name(midi)}', 'keys', ep(G, 0, .56, .58, .22, midi, .90, hold, chorus=.3, drive=1.6, lpf=11000),
             'bele:ep/tine', 'tine, hard hammer: the bark')
    for midi in (48, 60, 72, 84):
        hold = 4.0 if midi <= 60 else 3.0
        emit(f'rl_ep_glass_{dsp.note_name(midi)}', 'keys', ep(G, 1, .62, .50, .18, midi, .72, hold, chorus=.4, lpf=12000, roomy=.18),
             'bele:ep/bell', 'bell model: the glassy FM-like tine')
        emit(f'rl_ep_suitcase_{dsp.note_name(midi)}', 'keys', ep(G, 2, .38, .40, .68, midi, .66, hold, chorus=.25, drive=1.5, lpf=7000),
             'bele:ep/reed', 'reed model with deep tremolo')
    # ---- bass: the Cricket bass (Round for fretless, Pluck for finger, Rubber for the slap-ish one)
    for midi in (24, 36, 48):
        emit(f'rl_bass_round_{dsp.note_name(midi)}', 'bass', bass(G, 1, midi, 2.6, lpf=2400), 'bele:bass/round', 'round, warm, long')
        emit(f'rl_bass_pluck_{dsp.note_name(midi)}', 'bass', bass(G, 0, midi, 1.6, lpf=4200, drive=1.6), 'bele:bass/pluck', 'finger pluck')
        emit(f'rl_bass_rubber_{dsp.note_name(midi)}', 'bass', bass(G, 2, midi, 1.4, lpf=5200, drive=1.8), 'bele:bass/rubber', 'snappy rubber')

    have = lambda *ids: all(i in cat and os.path.exists(os.path.join(a.raw, cat[i]['raw'].split('/', 1)[1])) for i in ids)

    # ---- CC0 recordings
    if have('fs_412144'):
        x = dsp.gate_start(R('fs_412144')); y, m, f = tonal(x[:int(4 * dsp.SR)], lo=35, hi=200)
        emit(f'rl_fretless_{dsp.note_name(m)}', 'bass', dsp.lp(dsp.tape(y, 1.3), 3000), 'fs_412144', f'fretless open string ({f:.1f} Hz)')
    if have('fs_385868'):
        x = dsp.gate_start(R('fs_385868')); y, m, f = tonal(x[:int(3 * dsp.SR)], lo=35, hi=300)
        emit(f'rl_fingerbass_{dsp.note_name(m)}', 'bass', dsp.lp(y, 3500), 'fs_385868', f'clean fingered bass ({f:.1f} Hz)')
    for fid, nm in (('fs_373301', 'flute_vib'), ('fs_373314', 'flute_exp'), ('fs_373287', 'flute_plain'),
                    ('fs_372952', 'clarinet'), ('fs_374060', 'harmon'), ('fs_374142', 'straightmute')):
        if not have(fid):
            continue
        x = dsp.gate_start(R(fid), -40)
        y, m, f = tonal(x, lo=100, hi=1600, start=0.3)
        note = f'{cat[fid]["description"][:50]} ({f:.1f} Hz)'
        if nm == 'clarinet':   # the reed, warmed and pushed: a saxophone-like lead
            y = dsp.peq(dsp.tape(dsp.hp(y, 90), 2.2, warm=2.0), 1500, 4, 0.8)
            y = dsp.lp(dsp.room(dsp.chorus(y, 0.2, depth=1.2), 0.1, 0.5, 5000), 7500)
            emit(f'rl_reed_{dsp.note_name(m)}', 'lead', y, fid, 'clarinet, saturated and voiced up: the saxophone of the pack ' + note)
        emit(f'rl_{nm}_{dsp.note_name(m)}', 'lead', dsp.room(y, 0.08, 0.5), fid, note)
    for fid, nm, lo_, hi_ in (('fs_858114', 'crystal', 100, 1200), ('fs_396423', 'glassbell', 200, 3000),
                              ('fs_398496', 'chime', 300, 4000), ('fs_683038', 'harmonic', 150, 2000), ('fs_683037', 'harmonic2', 80, 2000)):
        if not have(fid):
            continue
        x = dsp.gate_start(R(fid), -40)
        y, m, f = tonal(x[:int(8 * dsp.SR)], lo=lo_, hi=hi_, start=0.15)
        if nm == 'chime':   # heard a quarter-tone sharp of what the autocorrelation says (library lane's 3.11 check)
            y = dsp.retune(y, 440.0, 69 - 0.47)
        emit(f'rl_{nm}_{dsp.note_name(m)}', 'bell', dsp.hp(y, 60), fid, f'{cat[fid]["description"][:50]} ({f:.1f} Hz)')
    for fid, nm in (('fs_340293', 'mutegtr_a'), ('fs_340292', 'mutegtr_b'), ('fs_374531', 'pizz_vln'), ('fs_373056', 'pizz_cb')):
        if not have(fid):
            continue
        x = dsp.gate_start(R(fid), -40)
        y, m, f = tonal(x[:int(2 * dsp.SR)], lo=40, hi=1200, start=0.02)
        emit(f'rl_{nm}', 'pluck', dsp.trim_end(y, -55), fid, f'{cat[fid]["description"][:50]} (root {dsp.note_name(m)}, {f:.1f} Hz)')

    # ---- drums and hand percussion (one hit each, kits are built from them in DNA)
    PERC = [('fs_614387', 'brush_a', 1), ('fs_725845', 'brush_sw', 2), ('fs_44868', 'brush_rim', 1), ('fs_132418', 'rim_a', 1),
            ('fs_82281', 'rim_b', 1), ('fs_493717', 'clap_a', 1), ('fs_154399', 'clap_b', 1), ('fs_421711', 'clap_c', 1),
            ('fs_824675', 'snap', 3), ('fs_319814', 'snap_b', 1), ('fs_547122', 'snap_c', 1), ('fs_199825', 'shaker', 4),
            ('fs_105336', 'shaker_b', 2), ('fs_871621', 'shaker_c', 2), ('fs_792560', 'shaker_d', 1), ('fs_219266', 'tamb', 1),
            ('fs_648735', 'tamb_b', 1), ('fs_349504', 'triangle', 1), ('fs_517646', 'triangle_b', 1), ('fs_350711', 'cowbell', 1),
            ('fs_373411', 'conga', 1), ('fs_375654', 'guiro', 1)]
    for fid, nm, n in PERC:
        if not have(fid):
            continue
        x = R(fid, 0, 60)
        if nm == 'guiro':
            g = dsp.gate_start(x, -40)[:int(1.4 * dsp.SR)]
            emit('rl_guiro', 'perc', dsp.fades(dsp.trim_end(g, -50), 0.5, 80), fid, cat[fid]['description'][:60])
            continue
        hs = hits(x, n, max_len=2.5 if nm.startswith(('triangle', 'guiro', 'brush_sw')) else 0.9)
        for k, h in enumerate(hs):
            emit(f'rl_{nm}{k + 1 if n > 1 else ""}', 'perc', dsp.hp(h, 40), fid, cat[fid]['description'][:60])

    # ---- ambiences: the steadiest 26 s, filtered, looped seamlessly
    AMB = [('fs_243781', 'rain_glass', 26, 90, 9000, -24), ('fs_869851', 'rain_window', 26, 90, 9000, -24),
           ('fs_163690', 'rain_soft', 26, 80, 8000, -24), ('fs_369494', 'rain_puddle', 14, 80, 10000, -24),
           ('fs_75069', 'rain_balcony', 26, 80, 9000, -24),
           ('fs_427841', 'city_hush', 26, 40, 6000, -26), ('fs_197211', 'city_night', 26, 40, 7000, -26),
           ('fs_454822', 'city_far', 26, 40, 7000, -26), ('fs_42211', 'night_autumn', 26, 40, 8000, -26),
           ('fs_723695', 'traffic_wet', 26, 50, 7000, -25), ('fs_365257', 'insects', 26, 200, 9000, -27),
           ('fs_637931', 'vinyl', 26, 150, 9000, -30), ('fs_682193', 'vinyl_b', 26, 150, 9000, -30),
           ('fs_464396', 'vinyl_c', 26, 150, 9000, -30)]
    for fid, nm, secs, hpf, lpf, rms in AMB:
        if not have(fid):
            continue
        x = R(fid)
        y = excerpt_steady(x, secs + 1.5)
        y = dsp.lp(dsp.hp(y, hpf), lpf)
        emit(f'rl_{nm}', 'texture', dsp.loopify(y, 1.5), fid, 'steady excerpt, seamless loop', rms=rms, seconds=29.5)
    EVENTS = [('fs_96906', 'espresso', 0, 26), ('fs_402845', 'espresso_auto', 0, 26), ('fs_333948', 'espresso_wave', 0, 24),
              ('fs_556722', 'needle', 0, 14), ('fs_826353', 'cassette', 0, 4), ('fs_452869', 'lighter', 0, 3),
              ('fs_459462', 'cup_stir', 0, 12), ('fs_545874', 'teacup', 0, 20), ('fs_475501', 'train_far', None, 26),
              ('fs_593082', 'train_pass', 0, 25), ('fs_364806', 'bicycle_bell', 0, 6), ('fs_683102', 'drip', 0, 1.7),
              ('fs_795709', 'foghorn', 0, 26), ('fs_507471', 'foghorn_far', 0, 26)]
    for fid, nm, st, secs in EVENTS:
        if not have(fid):
            continue
        x = R(fid)
        if st is None:
            # the loudest 26 s around the train's pass
            w = int(0.5 * dsp.SR); env = [np.sqrt(np.mean(x[i:i + w] ** 2)) for i in range(0, len(x) - w, w)]
            c = int(np.argmax(env)) * w
            a0 = max(0, c - int(secs * 0.55 * dsp.SR)); y = x[a0:a0 + int(secs * dsp.SR)]
        else:
            y = dsp.gate_start(x[int(st * dsp.SR):int((st + secs) * dsp.SR)], -30 if nm == 'bicycle_bell' else -45)
        y = dsp.hp(y, 40)
        if nm == 'bicycle_bell':   # start on the bell itself, not the hand reaching for it
            k = int(np.argmax(np.abs(y) > 0.5 * np.max(np.abs(y))))
            y = y[max(0, k - int(0.01 * dsp.SR)):]
        emit(f'rl_{nm}', 'texture', dsp.fades(y, 3 if nm == 'bicycle_bell' else 30, 600), fid, cat[fid]['description'][:60], seconds=29.5)

    with open(os.path.join(out, 'LIBRARY.TSV'), 'w', encoding='cp1252', newline='') as f:
        f.write('# name\tcategory\tpath\tseconds\tsource/licence\r\n')
        for r in rows:
            f.write('\t'.join(r) + '\r\n')
    json.dump(prov, open(os.path.join(out, 'provenance.json'), 'w'), indent=1)
    print(len(rows), 'sounds ->', out)


if __name__ == '__main__':
    main()
