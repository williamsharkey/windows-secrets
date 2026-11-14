#!/usr/bin/env python3
"""New library sounds from the owner's own instruments in midigarden / Bele Dance and ghosts.garden.

    garden_sources.py [--gardens ~/gardens] [--renders ~/gardens-render/wav]

Everything here is made by William Sharkey's own synth code, or is public domain:
- the Bele Dance electric piano (tine, bell, reed) and bass DSP, rendered offline by a private harness into
  --renders (one note each, 48 kHz);
- ghosts.garden's drum kits, modal percussion, ROM patches and speech voices, as already rendered offline by the
  owner's tools into midigarden's BeleSamples (dry, one note or one hit each);
- the soft piano: Salamander Grand Piano V3 by Alexander Holm (public-domain dedication; CC-BY 3.0 credited).
- Paul Chauncy's own sounds (his WAULOPHONE packs Avuncular and Waulotone), by permission from the author via the
  owner (2026-11-14), credited "Sounds by Paul Chauncy (Uncle Homunculus / Paulywauly)"; they are not PD/CC0.
Not used: the GENKI pack (third-party material inside it).

Writes library/sources-raw/garden/*.wav (gitignored) and library/catalog/garden.json; tools/build_library.py
--only garden then converts them like every other library sound.
"""
import argparse, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LIB

CREDIT = 'William Sharkey'
EP_URL = 'https://github.com/williamsharkey/midigarden (private): Bele Dance electric piano, rendered offline'
GG_URL = 'https://github.com/williamsharkey/ghosts-garden (private): ghosts.garden synths, rendered offline'
ROWSEWOOD = {0: 'studio', 5: 'latin', 6: 'chip', 7: 'tape', 8: 'hands', 9: 'temple', 10: 'mouth', 11: 'radio'}
PADS = {  # pad index -> our pad name (the kits' own pad order)
    'rosewood': ['kick', 'lowkick', 'snare', 'rim', 'clap', 'hat', 'tighthat', 'openhat', 'bell', 'tamb', 'hitom',
                 'midtom', 'lotom', 'cabasa', 'crash', 'conga', 'loconga', 'loclap', 'lorim', 'ride'],
    'hands': ['tumba', 'conga', 'slap', 'mute', 'cajon', 'bongohi', 'bongolo', 'slap2', 'talking', 'frame', 'blockhi',
              'blockmid', 'blocklo', 'claves', 'agogohi', 'agogolo', 'triangle', 'mutetri', 'shaker', 'back'],
    'mouth': ['bkick', 'lowkick', 'ksnare', 'pfsnare', 'tshat', 'that', 'tchhat', 'opents', 'psh', 'kh', 'dum', 'dom',
              'dumm', 'click', 'hum', 'tightkick', 'kesnare', 'pfrim', 'double', 'wub'],
}
MODAL = {'marimba': ['bass', 'fifth', 'root', 'third', 'fifthhi', 'octave', 'sixth', 'frame'],
         'steel-pan': ['basspan', 'lowfifth', 'tenor', 'third', 'fifth', 'octave', 'tenth', 'iron'],
         'timpani': ['c3', 'd3', 'e3', 'g3', 'a3', 'c4', 'd4', 'e4'],
         'taiko': ['odaiko', 'shime', 'nagadolo', 'nagado', 'okedo', 'atarigane', 'chappa', 'ka'],
         'tabla': ['ge', 'na', 'ke', 'tin', 'tun', 'te', 'gheglide', 'ra'],
         'glitch': ['kick', 'snap', 'grit', 'zap', 'tick', 'fuzz', 'blip', 'err']}
ROM = ['worlds-stalactite-grotto', 'worlds-conch-horizon', 'worlds-fog-temple', 'worlds-bamboo-mist',
       'worlds-crystal-fantasia', 'worlds-aurora-veil', 'rave-stabs-belgian-stab', 'rave-stabs-detroit-stab',
       'rave-stabs-mentasm', 'rave-keys-piano-16', 'rave-keys-organ-two', 'rave-keys-reese']
ROMNAME = {'rave-stabs-belgian-stab': 'rave_hoover', 'rave-stabs-detroit-stab': 'rave_chord', 'rave-stabs-mentasm': 'rave_scream',
           'rave-keys-piano-16': 'rave_piano', 'rave-keys-organ-two': 'rave_organ', 'rave-keys-reese': 'rave_reese'}
PAUL = {  # BeleSamples file -> our NAME, for Paul's own sounds (Avuncular, Waulotone); never GENKI
    'doo': 'pw_doo', 'doo-held': 'pw_doo_held', 'barry': 'pw_bass', 'barry-held': 'pw_bass_held', 'boop': 'pw_boop',
    'glock': 'pw_glock', 'flutecorder': 'pw_flutecorder', 'fork': 'pw_fork', 'mguitar': 'pw_guitar_pad',
    'beeorgan': 'pw_bee_organ', 'hmm': 'pw_hmm', 'hmm-held': 'pw_hmm_held', 'saphron': 'pw_flute', 'plaintive': 'pw_sax'}
PAUL_DESC = {'pw_doo': 'Doo, a sung syllable', 'pw_doo_held': 'Doo, held (looped)', 'pw_bass': 'Bass, tuned to C',
             'pw_bass_held': 'Bass, held (looped)', 'pw_boop': 'Boop, low', 'pw_glock': 'Glockenspiel, C',
             'pw_flutecorder': 'Wooden flutecorder', 'pw_fork': 'Tuning fork, C', 'pw_guitar_pad': 'Guitar with pad, C',
             'pw_bee_organ': 'Bee organ', 'pw_hmm': 'Hmm, a hummed voice', 'pw_hmm_held': 'Hmm, held (looped)',
             'pw_flute': 'Flute', 'pw_sax': 'Saxophone phrase'}
PAUL_CREDIT = 'Sounds by Paul Chauncy (Uncle Homunculus / Paulywauly)'
PAUL_LICENCE = 'Permission from the author, via the owner, 2026-11-14 (not PD/CC0): BASILISK packs, credited "%s"' % PAUL_CREDIT
SPEECH = ['aah', 'ooh', 'boop', 'bele', 'dance', 'hello', 'lala', 'meow', 'goose', 'robot']
NOTE = {36: 'c2', 60: 'c4', 84: 'c6'}


def entry(i, raw, desc, tonal, url, kind):
    return {'id': i, 'raw': 'garden/' + raw, 'category': 'garden', 'description': desc, 'tonal': tonal,
            'start': 0, 'dur': None, 'source_url': url, 'download_url': None, 'author': CREDIT,
            'license': 'William Sharkey (rendered from his own instruments); for BASILISK packs',
            'license_proof_url': url, 'origin': 'rendered', 'kind': kind}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gardens', default=os.path.expanduser('~/gardens'))
    ap.add_argument('--renders', default=os.path.expanduser('~/gardens-render/wav'))
    a = ap.parse_args()
    bs = os.path.join(a.gardens, 'midigarden', 'midigarden', 'BeleSamples')
    raw = os.path.join(LIB, 'sources-raw', 'garden')
    os.makedirs(raw, exist_ok=True)
    cat = []

    def copy(src, dst):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-c:a', 'pcm_s16le', os.path.join(raw, dst)], check=True)

    # Bele Dance electric piano and bass (the private harness's renders)
    for f in sorted(os.listdir(a.renders)):
        m = re.match(r'bele_ep_(tine|bell|reed)(_hard)?_(c[2-6])\.wav$', f)
        if m:
            if m.group(2) and m.group(3) in ('c2', 'c6'): continue
            i = 'gd_ep_%s%s_%s' % (m.group(1), m.group(2) or '', m.group(3))
            copy(os.path.join(a.renders, f), i + '.wav')
            cat.append(entry(i, i + '.wav', 'Electric piano, %s model, %s touch, %s (Bele Dance EP, rendered)'
                             % (m.group(1), 'hard' if m.group(2) else 'soft', m.group(3).upper()), True, EP_URL, 'note'))
        m = re.match(r'bele_bass(\d)_(c[1-3])\.wav$', f)
        if m:
            i = 'gd_bass%s_%s' % (m.group(1), m.group(2))
            copy(os.path.join(a.renders, f), i + '.wav')
            cat.append(entry(i, i + '.wav', 'Synth bass preset %s, %s (Bele Dance bass, rendered)' % (m.group(1), m.group(2).upper()), True, EP_URL, 'note'))
    # the soft piano (Salamander Grand, public domain): the loudest soft layer at A1..A5
    pz = json.load(open(os.path.join(bs, 'bele-piano-soft.json')))
    for z in pz['zones']:
        if z['layer'] == 2 and z['root'] in (33, 45, 57, 69, 81):
            nm = {33: 'a1', 45: 'a2', 57: 'a3', 69: 'a4', 81: 'a5'}[z['root']]
            i = 'gd_piano_' + nm
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', '%.6f' % (z['firstFrame'] / 24000), '-t', '%.6f' % (min(z['frames'], 8 * 24000) / 24000),
                            '-i', os.path.join(bs, 'bele-piano-soft.caf'), '-c:a', 'pcm_s16le', os.path.join(raw, i + '.wav')], check=True)
            e = entry(i, i + '.wav', 'Soft grand piano, %s (Salamander Grand Piano V3, Alexander Holm; Bele Dance soft layer)' % nm.upper(),
                      True, 'https://github.com/sfzinstruments/SalamanderGrandPiano/tree/%s' % pz['sourceRevision'], 'note')
            # the exact recordings rendered from: sfzinstruments/SalamanderGrandPiano (V3) at this revision; the author
            # dedicated Salamander Grand Piano to the public domain on 2022-03-04, and V3 was first released CC-BY 3.0
            e.update(author='Alexander Holm (Salamander Grand Piano V3); soft layer by William Sharkey',
                     license='Public domain (author\'s dedication 2022-03-04) for Salamander Grand Piano V3, '
                             'sfzinstruments/SalamanderGrandPiano revision %s; first released CC-BY-3.0 (credited)' % pz['sourceRevision'],
                     license_proof_url='https://rytmenpinne.wordpress.com/sounds-and-such/salamander-grandpiano/')
            cat.append(e)
    # ghosts.garden drum kits (dry one-shots)
    for k, kit in ROWSEWOOD.items():
        pads = PADS['hands'] if kit in ('hands', 'temple') else PADS['mouth'] if kit in ('mouth', 'radio') else PADS['rosewood']
        for p, pn in enumerate(pads):
            src = os.path.join(bs, 'gg-exp-drum-%d-%d.wav' % (k, p))
            if not os.path.exists(src): continue
            i = 'gd_kit_%s_%s' % (kit, pn)
            copy(src, i + '.wav')
            cat.append(entry(i, i + '.wav', 'Drum kit "%s", pad %s (ghosts.garden drums, rendered)' % (kit, pn), False, GG_URL, 'oneshot'))
    # modal percussion (marimba, steel pan, timpani, taiko, tabla) and the glitch kit
    for kit, pads in MODAL.items():
        for p, pn in enumerate(pads):
            src = os.path.join(bs, 'gg-orchestra-%s-%d.wav' % (kit, p))
            if not os.path.exists(src): continue
            i = 'gd_%s_%s' % (kit.replace('-', ''), pn)
            copy(src, i + '.wav')
            cat.append(entry(i, i + '.wav', '%s, %s (ghosts.garden modal synthesis, rendered)' % (kit.replace('-', ' ').title(), pn),
                             kit in ('marimba', 'steel-pan', 'timpani'), GG_URL, 'oneshot'))
    # ROM patches at C2, C4, C6
    for r in ROM:
        for n, nm in NOTE.items():
            src = os.path.join(bs, 'gg-rom-%s-%d.wav' % (r, n))
            if not os.path.exists(src): continue
            base = ROMNAME.get(r, r.split('-', 1)[1].replace('-', '_'))
            i = 'gd_%s_%s' % (base, nm)
            copy(src, i + '.wav')
            cat.append(entry(i, i + '.wav', 'Synth patch "%s", %s (ghosts.garden ROM synth, rendered)' % (base.replace('_', ' '), nm.upper()), True, GG_URL, 'note'))
    # speech voices: LPC, Klatt and a SAM-style formant voice, ten words each, at C4
    for v in ('lpc', 'klatt', 'sam'):
        for w in SPEECH:
            src = os.path.join(bs, 'gg-speech-%s-%s.wav' % (v, w))
            if not os.path.exists(src): continue
            i = 'gd_voice_%s_%s' % (v, w)
            copy(src, i + '.wav')
            cat.append(entry(i, i + '.wav', 'Speech synth (%s) saying "%s", C4 (ghosts.garden speech, rendered)' % (v.upper(), w), True, GG_URL, 'oneshot'))
    # Paul Chauncy's own sounds (permission via the owner): category 'pauly'
    for f, i in PAUL.items():
        src = os.path.join(bs, f + '.wav')
        if not os.path.exists(src): continue
        copy(src, i + '.wav')
        e = entry(i, i + '.wav', '%s (%s)' % (PAUL_DESC[i], PAUL_CREDIT), i not in ('pw_boop',), 'https://github.com/williamsharkey/ghosts-garden (private): WAULOPHONE packs', 'note')
        e.update(raw='garden/' + i + '.wav', category='pauly', author=PAUL_CREDIT, license=PAUL_LICENCE,
                 license_proof_url='permission recorded in packages/basilisk-synth/library/builder/PROGRESS.md (2026-11-14)', origin='recording')
        cat.append(e)
    for e in cat:
        assert re.fullmatch(r'[a-z0-9_]+', e['id']), e['id']
    json.dump(cat, open(os.path.join(LIB, 'catalog', 'garden.json'), 'w'), indent=1)
    print(len(cat), 'sounds ->', raw)


if __name__ == '__main__':
    main()
