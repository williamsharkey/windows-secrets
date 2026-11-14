#!/usr/bin/env python3
"""make_packs.py - builds every preset pack's disc, docs and renders from <pack>/persona.json + the pack data.

    make_packs.py [PACK_ID ...] [--no-render] [--render-only] [--no-iso] [--web] [--booklet] [--gallery PAGE]

Content: when the library lane's disc folder exists (library/builder/out/discs311/<LABEL>/, make_discs.py), its files
are copied as built (PRESETS.TSV, PACK.INF, LIBRARY.TSV, category folders, FAVORITE) and this lane adds the identity.
The final set is out/discs/ (<LABEL>/, <LABEL>.ISO, DISCS.TSV); --web writes out/web/ for the site (packlib/webexport.py).

For each pack folder (one with a persona.json):
  disc/        the disc's files: AUTORUN.INF, PACK.ICO, PACK.INF, PACK.TXT, PRESETS.TSV, LIBRARY.TSV, the preset
               folders (*.BSP, one line of DNA each), README / NFO / DIZ / licence files, the WinHelp .HLP (hlpc.py),
               the PDF manual, a .WRI or .RTF manual if the maker wrote one, and a splash .BMP
  renders/     box.png (Blender, shrink-wrapped), disc.png (Blender: disc on its inlay), icon32/48.png,
               inlay.png (front insert + tray card), label.png (the disc's printed side), splash.png
  build/       intermediate textures and help sources (not committed)
and ../packs/out/<LABEL>.ISO: ISO 9660 level 1 (8.3, for Windows 3.11) + Joliet (for XP).

Needs: Python 3 with Pillow, numpy, reportlab, pycdlib (PYTHONPATH=~/packwork/pylib here); the Windows fonts
(/mnt/c/Windows/Fonts); the public-domain art library (PACK_ART, default the names page's art/ folder); hlpc.py
(HLPC, default ../../help/hlpc.py); Blender 4.2 for the renders (BLENDER, default ~/packwork/blender-4.2.3-linux-x64/blender).
"""
import datetime
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from packlib import artwork, brand, data as pdata, docs, gfx, hlp, iso, pdf, texts  # noqa: E402

BLENDER = os.environ.get('BLENDER', os.path.expanduser('~/packwork/blender-4.2.3-linux-x64/blender'))


def personas(ids):
    out = []
    for d in sorted(os.listdir(HERE)):
        f = os.path.join(HERE, d, 'persona.json')
        if os.path.exists(f) and (not ids or d in ids):
            out.append(json.load(open(f, encoding='utf-8')))
    return out


def manual_blocks(p, data):
    T, M, pk = p['text'], p['maker'], p['pack']
    B = [('h1', '%s %s' % (pk['title'], pk.get('edition', ''))), ('center', T['tagline']), ('h2', 'Introduction')]
    B += [('p', x) for x in T.get('intro_de', [])] + [('p', x) for x in T['intro']]
    B += [('h2', 'Getting Started')] + [('bullet', x) for x in T['install']]
    B += [('h2', 'The Presets')]
    cur = None
    for x in data['presets']:
        if x['folder'] != cur:
            cur = x['folder']
            B.append(('p', '\\%s' % cur))
        B.append(('mono', '%-12s %s' % (x['file83'], x['name'])))
    B += [('h2', 'A Note from the Author' if p.get('register') else 'A Note from %s' % M['short'])] + [('p', x) for x in T['maker_note']]
    if p.get('register'):
        R = p['register']
        B += [('h2', 'How to Register'), ('p', 'Registration is $%.2f plus $%.2f shipping. You get %s.' % (R['price'], R['shipping'], R['bonus']))]
        B += [('mono', c) for c in M['contact'][:4]]
    if T.get('license'):
        B += [('h2', 'License')] + [('p', x) for x in T['license']]
    B += [('h2', 'Contact')] + [('mono', c) for c in M['contact']]
    return B


def with_counts(p, data):
    """Fills {count} (presets on the disc), {count_xp} (those that ship to XP) and {ncat} (folders) everywhere."""
    n = len(data['presets'])
    nx = sum(1 for x in data['presets'] if 'XP' in x.get('ships', ['XP']))
    nc = len({x['folder'] for x in data['presets']})
    def sub(v):
        if isinstance(v, str):
            return v.replace('{count}', str(n)).replace('{count_xp}', str(nx)).replace('{ncat}', str(nc))
        if isinstance(v, list):
            return [sub(x) for x in v]
        if isinstance(v, dict):
            return {k: sub(x) for k, x in v.items()}
        return v
    q = sub(p)
    q['_count'] = n
    return q


def build_pack(p, opt):
    pid = p['id']
    root = os.path.join(HERE, pid)
    disc, rend, build = (os.path.join(root, x) for x in ('disc', 'renders', 'build'))
    if opt.get('render_only'):
        if not os.path.isdir(os.path.join(root, 'build', 'tex')):
            print('[%s] no textures yet (build it first): skipped' % pid, flush=True)
            return None
        return render_pack(p, opt)
    if not pdata.content_dir(p) and p['pack'].get('sources', {}).get('plan') and p['pack'].get('library_id') and not opt.get('force'):
        print('[%s] waiting for the library lane\'s disc content (%s): skipped' % (pid, p['pack']['library_id']), flush=True)
        return None
    for d in (disc, build):
        shutil.rmtree(d, ignore_errors=True)
    for d in (disc, rend, build):
        os.makedirs(d, exist_ok=True)
    data = pdata.load(p)
    p = with_counts(p, data)
    files = {}          # disc path (8.3, '/' separated) -> bytes
    joliet = {}         # disc path -> Joliet path (when it differs)
    pk, F = p['pack'], p['files']
    date = datetime.date.fromisoformat(pk['date'])
    print('[%s] %d presets (%s)' % (pid, len(data['presets']), data['source']), flush=True)

    # ---- art
    s = artwork.PX_PER_MM
    bt = p['box']['type']
    shape = 'bigbox_landscape' if bt == 'bigbox' and p['box'].get('shape') == 'landscape' else bt
    bw, bh, bd = artwork.BOX_MM[shape]
    tex = os.path.join(build, 'tex')
    os.makedirs(tex, exist_ok=True)
    fr = artwork.front(p, bw * s, bh * s)
    fr.save(os.path.join(tex, 'front.png'))
    artwork.back(p, bw * s, bh * s).save(os.path.join(tex, 'back.png'))
    artwork.spine(p, bd * s, bh * s).save(os.path.join(tex, 'spine.png'))
    artwork.spine(p, bd * s, bh * s).save(os.path.join(tex, 'spine2.png'))
    artwork.plain(p, bw * s, bd * s).save(os.path.join(tex, 'top.png'))
    if p['box'].get('obi'):
        artwork.obi(p, 26 * s, bh * s).save(os.path.join(tex, 'obi.png'))
    artwork.sticker(p, 200).save(os.path.join(tex, 'sticker.png'))
    if bt == 'mailer':
        artwork.floppy(p).save(os.path.join(tex, 'floppy.png'))
    inl_front, inl_tray = artwork.inlay(p)
    inl_front.save(os.path.join(tex, 'inlay_front.png'))
    inl_tray.save(os.path.join(tex, 'inlay_tray.png'))
    lab = artwork.disc_label(p)
    lab.save(os.path.join(tex, 'label.png'))
    # flat renders for the site: inlay pair and label, at half texture size (2:1 nearest would lose pixels, so
    # these are the textures as printed, 5 px/mm, cropped into one sheet)
    sheet = gfx.Image.new('RGB', (inl_front.width + inl_tray.width + 30, max(inl_front.height, inl_tray.height) + 20), '#d8d8d8')
    sheet.paste(inl_front, (10, 10))
    sheet.paste(inl_tray, (inl_front.width + 20, 10))
    sheet.save(os.path.join(rend, 'inlay.png'))
    lb = gfx.Image.new('RGBA', lab.size, (0, 0, 0, 0))
    _bare_disc(lb, p)
    lb.alpha_composite(lab)
    lb.save(os.path.join(rend, 'label.png'))
    icons = artwork.save_icons(p, os.path.join(build, 'PACK.ICO'))
    icons[32].save(os.path.join(rend, 'icon32.png'))
    icons[48].save(os.path.join(rend, 'icon48.png'))
    # the cover for the PDF: the front, RGB (no alpha, so the PDF stays 1.3)
    cover = os.path.join(build, 'cover.png')
    fr.convert('RGB').save(cover)

    # ---- disc files
    files['PACK.ICO'] = open(os.path.join(build, 'PACK.ICO'), 'rb').read()
    files['AUTORUN.INF'] = texts.enc(texts.autorun_inf(p))
    if data.get('content_dir'):
        # the library lane owns the content: copy its disc folder as built (PRESETS.TSV, PACK.INF, LIBRARY.TSV, the
        # category folders, FAVORITE); this lane adds the identity (AUTORUN, icon, PACK.TXT, docs, help, art)
        cd_ = data['content_dir']
        listed = {('%s/%s' % (x['folder83'], x['file83'])).upper() for x in data['presets']}
        lib_tsv = os.path.join(cd_, 'LIBRARY.TSV')
        sounds = set()
        if os.path.exists(lib_tsv):
            for l in open(lib_tsv, encoding='utf-8', errors='replace'):
                f_ = l.rstrip('\n').split('\t')
                if len(f_) > 2 and not l.startswith('#'):
                    sounds.add(f_[2].strip('\\').replace('\\', '/').upper())
        for root_, dirs_, fns in os.walk(cd_):
            for fn in fns:
                rel = os.path.relpath(os.path.join(root_, fn), cd_).replace(os.sep, '/')
                if rel in ('AUTORUN.INF', 'PACK.TXT'):
                    continue
                if rel.upper().startswith('SOUNDS/') and sounds and rel.upper() not in sounds:
                    print('  [%s] skipped %s: not in the content LIBRARY.TSV (stale)' % (pid, rel))
                    continue
                if rel.upper().endswith('.BSP') and not rel.upper().startswith('FAVORITE/') and rel.upper() not in listed:
                    print('  [%s] skipped %s: not in the content PRESETS.TSV (stale)' % (pid, rel))
                    continue
                files[rel] = open(os.path.join(root_, fn), 'rb').read()
        ptxt = os.path.join(cd_, 'PACK.TXT')
        if os.path.exists(ptxt):     # the content's PACK.TXT, with this maker filled in where the content left it blank
            t = open(ptxt, encoding='cp1252', errors='replace').read().replace('\r\n', '\n')
            t = t.replace('Author: \n', 'Author: %s\n' % p['maker']['name']).replace('Date: \n', 'Date: %s\n' % pk['date'])
        else:
            inf = open(os.path.join(cd_, 'PACK.INF'), encoding='cp1252', errors='replace').read().replace('\r\n', '\n')
            t = inf.replace('[Pack]\n', '%s\n%s\n\nfor %s and %s\n\n' % (pk['title'], '=' * len(pk['title']), brand.SW, brand.XP))
        files['PACK.TXT'] = texts.enc(t)
        if data.get('credits'):
            files['CREDITS.TXT'] = texts.enc('%s - SOUND CREDITS\n\n%s\n\nAll other material on this disc (c) %d %s.\n'
                                             % (pk['title'].upper(), '\n'.join('  ' + c for c in data['credits']), p['maker']['year'], p['maker']['name']))
        for x in data['presets']:
            joliet['%s/%s' % (x['folder83'], x['file83'])] = '%s/%s' % (x['folder'], x['joliet'])
    else:
        inf = texts.pack_inf(p, data)
        files['PACK.INF'] = texts.enc(inf)
        files['PACK.TXT'] = texts.enc(inf.replace('[Pack]\n', '%s\n%s\n\n' % (pk['title'], '=' * len(pk['title']))))
        files['PRESETS.TSV'] = texts.enc('# category\tname\tDNA\tpack\teditions (3.11 = SNDWAVE2000, XP = BASILISK SYNTH)\n' + ''.join(
            '%s\t%s\t%s\t%s\t%s\n' % (x['category'], x['name'], x['dna'], pk.get('plan_id') or pid, ' '.join(x.get('ships', ['3.11', 'XP'])))
            for x in data['presets']), 'utf-8')
        lid = pdata.LIBMAP.get(pid)
        for ed, disc_name in (('xp', 'XP.TSV'), ('w311', 'W311.TSV')):   # the library lane's per-edition lists, as built
            src = os.path.join(pdata.BUILDER_OUT, ed, '%s.tsv' % lid) if lid else None
            if src and os.path.exists(src) and not data['placeholder']:
                files[disc_name] = texts.enc(open(src, encoding='utf-8').read(), 'utf-8')
        files['LIBRARY.TSV'] = texts.enc('# name\tcategory\tpath\tseconds\tsource/licence\n' + ''.join(
            '%s\t%s\t%s\t%s\t%s\n' % tuple(x) for x in data['sounds']), 'utf-8')
        for x in data['presets']:
            path = '%s/%s' % (x['folder83'], x['file83'])
            files[path] = (x['dna'] + '\r\n').encode('ascii')
            joliet[path] = '%s/%s' % (x['folder'], x['joliet'])
    tf, previews = texts.STYLES[F['readme']](p, data)
    files.update(tf)
    for k, v in texts.extra_texts(p).items():
        files[k] = texts.enc(v, 'cp437' if k.endswith(('.NFO', '.DIZ', '.ANS')) else 'cp1252')
        previews[k] = v
    # help
    files[F['hlp']] = None
    hlp.build(p, data, os.path.join(build, 'help'), os.path.join(build, F['hlp']))
    files[F['hlp']] = open(os.path.join(build, F['hlp']), 'rb').read()
    # manuals
    credits = artwork.credits_for(p)
    pdf.build(p, data, cover, credits, os.path.join(build, F['pdf']))
    files[F['pdf']] = open(os.path.join(build, F['pdf']), 'rb').read()
    blocks = manual_blocks(p, data)
    if F.get('wri'):
        docs.write_wri(os.path.join(build, F['wri']), blocks)
        files[F['wri']] = open(os.path.join(build, F['wri']), 'rb').read()
    if F.get('rtf'):
        H = p['hlp']
        docs.write_rtf(os.path.join(build, F['rtf']), blocks, H['font'], H['font'], 'Courier New', p['look']['accent'], pk['title'])
        files[F['rtf']] = open(os.path.join(build, F['rtf']), 'rb').read()
    # splash
    sp = artwork.splash(p, tuple(F['splash_size']))
    shown = gfx.write_bmp(os.path.join(build, F['splash']), sp, F['splash_bpp'])
    files[F['splash']] = open(os.path.join(build, F['splash']), 'rb').read()
    shown.save(os.path.join(rend, 'splash.png'))

    for path, b in files.items():
        fp = os.path.join(disc, *path.split('/'))
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, 'wb') as f:
            f.write(b)
        os.utime(fp, (datetime.datetime(date.year, date.month, date.day, 12).timestamp(),) * 2)
    with open(os.path.join(build, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump({'source': data['source'], 'placeholder': data['placeholder'], 'presets': len(data['presets']),
                   'presets_xp': sum(1 for x in data['presets'] if 'XP' in x.get('ships', ['XP'])),
                   'credits': data.get('credits', []), 'favourites': len(data.get('favourites', []))}, f)
    with open(os.path.join(build, 'previews.json'), 'w', encoding='utf-8') as f:
        json.dump(previews, f, ensure_ascii=False, indent=1)

    # ---- ISO
    if not opt.get('no_iso'):
        out = os.path.join(HERE, 'out', 'discs')          # the final disc set: <LABEL>/ folders, <LABEL>.ISO, DISCS.TSV
        os.makedirs(out, exist_ok=True)
        ents = [('/' + k, '/' + joliet.get(k, k), v) for k, v in files.items()]
        iso.build(os.path.join(out, pk['label'] + '.ISO'), pk['label'], pk['label_long'], ents, date)
        shutil.rmtree(os.path.join(out, pk['label']), ignore_errors=True)
        shutil.copytree(disc, os.path.join(out, pk['label']))

    if not opt.get('no_render'):
        render_pack(p, opt)
    return {'persona': p, 'data': data, 'files': sorted(files), 'previews': previews}


def render_pack(p, opt):
    """Blender renders from the textures in build/tex (made by a normal or --no-render run)."""
    pid = p['id']
    root = os.path.join(HERE, pid)
    rend, build = os.path.join(root, 'renders'), os.path.join(root, 'build')
    tex = os.path.join(build, 'tex')
    bt = p['box']['type']
    shape = 'bigbox_landscape' if bt == 'bigbox' and p['box'].get('shape') == 'landscape' else bt
    bw, bh, bd = artwork.BOX_MM[shape]
    if True:
        job = {'type': bt, 'shape': shape, 'mm': [bw, bh, bd], 'tex': tex, 'id': pid,
               'out_box': os.path.join(build, 'box_raw.png'), 'out_disc': os.path.join(build, 'disc_raw.png'),
               'disc_base': p['disc']['base'], 'disc_style': p['disc']['style'], 'obi': bool(p['box'].get('obi')),
               'sticker_pos': p['box'].get('sticker', {}).get('pos')}
        small = os.environ.get('PACK_ONLY') == 'small'
        if small:   # box_small.png: the box rendered at about 240 px on its long side
            job['out_box'] = os.path.join(build, 'box_small_raw.png')
        jp = os.path.join(build, 'job.json')
        json.dump(job, open(jp, 'w'))
        benv = dict(os.environ, PACK_ONLY='box', PACK_LONG=os.environ.get('PACK_LONG', '240')) if small else None
        r = subprocess.CompletedProcess([], 0) if os.environ.get('PACK_ONLY') == 'post' else subprocess.run(env=benv, args=[BLENDER, '-b', '--factory-startup', '-t', os.environ.get('BLENDER_THREADS', '4'), '-P', os.path.join(HERE, 'packlib', 'render_blender.py'), '--', jp],
                           capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit('blender failed for ' + pid)
        post = p['look'].get('render_post')
        outs = ((job['out_box'], 'box_small.png'),) if small else ((job['out_box'], 'box.png'), (job['out_disc'], 'disc.png'))
        for raw, name in outs:
            if not os.path.exists(raw):
                continue
            im = gfx.Image.open(raw).convert('RGBA')
            if post:   # period colours, alpha kept (shadow becomes a hard-edged, dithered grey)
                a = im.getchannel('A')
                bg = gfx.Image.new('RGBA', im.size, '#ffffff')
                bg.alpha_composite(im)
                im = gfx.dither(bg.convert('RGB'), post, 'bayer4' if post == 'vga16' else 'fs').convert('RGB')
                im.putalpha(a.point(lambda v: 255 if v >= 96 else 0))
            bb = im.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox()
            if bb:   # crop to the object and its shadow, with a margin (no scaling)
                mg = 6 if name == 'box_small.png' else 16
                im = im.crop((max(0, bb[0] - mg), max(0, bb[1] - mg), min(im.width, bb[2] + mg), min(im.height, bb[3] + mg)))
            im.save(os.path.join(rend, name), optimize=True)
        print('[%s] rendered' % pid, flush=True)


def _bare_disc(im, p):
    """Paints the unprinted disc (silver, or CD-R dye) under a label, for the flat label render."""
    from PIL import ImageDraw
    D = im.width
    c = D / 2
    s = artwork.PX_PER_MM
    d = ImageDraw.Draw(im)
    base = p['disc']['base']
    d.ellipse((0, 0, D - 1, D - 1), fill=base)
    for r in range(int(58 * s), int(17 * s), -int(3 * s)):
        tone = 18 if (r // int(3 * s)) % 2 else -10
        rgb = tuple(max(0, min(255, v + tone)) for v in gfx.hexrgb(base))
        d.ellipse((c - r, c - r, c + r, c + r), outline=rgb)
    d.ellipse((c - 17 * s, c - 17 * s, c + 17 * s, c + 17 * s), fill='#e4e4e4')
    d.ellipse((c - 11 * s, c - 11 * s, c + 11 * s, c + 11 * s), fill='#cfcfcf', outline='#b0b0b0')
    d.ellipse((c - 7.5 * s, c - 7.5 * s, c + 7.5 * s, c + 7.5 * s), fill=(0, 0, 0, 0))


def write_index(out):
    """out/discs/DISCS.TSV: the library lane's index rows, with this lane's volume labels and ISO names, listing only
    the discs that exist in out/discs/ (so the 3.11 lane never meets a missing folder). XP-ONLY.TSV is copied."""
    src = os.path.join(pdata.CONTENT, 'DISCS.TSV')
    if not os.path.exists(src) or not os.path.isdir(out):
        return
    labels = {}
    for p in personas([]):
        lid = p['pack'].get('library_id') or pdata.LIBMAP.get(p['id']) or ('kit-manager' if p['id'] == 'kitmgr' else p['pack'].get('plan_id'))
        labels[lid] = p['pack']['label']
    rows = []
    for line in open(src, encoding='utf-8'):
        if line.startswith('#') or not line.strip():
            rows.append(line.rstrip('\n'))
            continue
        f = line.rstrip('\n').split('\t')
        lab = labels.get(f[0], f[1])
        if not os.path.exists(os.path.join(out, lab + '.ISO')):
            continue
        f[1], f[2] = lab, lab + '.ISO'
        rows.append('\t'.join(f))
    with open(os.path.join(out, 'DISCS.TSV'), 'w', encoding='utf-8', newline='\n') as fo:
        fo.write('\n'.join(rows) + '\n')
    x = os.path.join(pdata.CONTENT, 'XP-ONLY.TSV')
    if os.path.exists(x):
        shutil.copy2(x, os.path.join(out, 'XP-ONLY.TSV'))


def main():
    a = sys.argv[1:]
    opt = {'no_render': '--no-render' in a, 'no_iso': '--no-iso' in a, 'render_only': '--render-only' in a}
    gal = None
    web = '--web' in a
    book = '--booklet' in a
    if '--gallery' in a:
        gal = a[a.index('--gallery') + 1]
        a.remove(gal)
    ids = [x for x in a if not x.startswith('--')]
    results = []
    for p in personas(ids):
        results.append(build_pack(p, opt))
    if not opt.get('no_iso') and not opt.get('render_only'):
        out = os.path.join(HERE, 'out', 'discs')
        write_index(out)
    if book:   # booklet pages for the site's player (packlib/booklet.py), one per category, from the content as built
        from packlib import booklet
        for p in personas([]):
            d = pdata.load(p)
            if d['presets'] and not d['placeholder']:
                booklet.build(with_counts(p, d), d, os.path.join(HERE, 'out', 'web', p['id'], 'booklet'))
    if web:
        from packlib import webexport
        webexport.export(HERE, [p for p in personas([])])
    if gal:
        from packlib import gallery
        gallery.write(gal, HERE, [p for p in personas([])])


if __name__ == '__main__':
    main()
