"""Web assets for the site's Sound Pack Explorer (williamsharkey.com/sndwave2000), per pack, at native pixel size:

    out/web/<id>/front.png   the box (or sleeve, insert, mailer label) front as printed, 5 px per mm
    out/web/<id>/spine.png   the spine, upright
    out/web/<id>/back.png    the back
    out/web/<id>/disc.png    the disc's printed side, with the bare disc around it (RGBA)
    out/web/<id>/box.png     the shrink-wrapped 3D render (RGBA)
    out/web/<id>/disc3d.png  the disc on its inlay, 3D render (RGBA)
    out/web/<id>/icon32.png, icon48.png
    out/web/<id>/manual.pdf  the pack's PDF manual
    out/web/<id>/pack.json   who made it, what is on it, the file names above
    out/web/packs.json       the list of packs (the same objects)

Nothing is rescaled. Images are copied from build/tex and renders/ as the generator wrote them."""
import json
import os
import shutil

from . import brand, data as pdata


def export(here, personas, out=None):
    out = out or os.path.join(here, 'out', 'web')
    os.makedirs(out, exist_ok=True)
    allp = []
    for p in personas:
        pid = p['id']
        root = os.path.join(here, pid)
        tex, rend, disc, build = (os.path.join(root, x) for x in ('build/tex', 'renders', 'disc', 'build'))
        if not os.path.isdir(tex):
            continue
        dst = os.path.join(out, pid)
        os.makedirs(dst, exist_ok=True)
        files = {}
        for src, name in ((os.path.join(tex, 'front.png'), 'front.png'), (os.path.join(tex, 'spine.png'), 'spine.png'),
                          (os.path.join(tex, 'back.png'), 'back.png'), (os.path.join(rend, 'label.png'), 'disc.png'),
                          (os.path.join(rend, 'box.png'), 'box.png'), (os.path.join(rend, 'box_small.png'), 'box_small.png'), (os.path.join(rend, 'disc.png'), 'disc3d.png'),
                          (os.path.join(rend, 'icon32.png'), 'icon32.png'), (os.path.join(rend, 'icon48.png'), 'icon48.png'),
                          (os.path.join(disc, p['files']['pdf']), 'manual.pdf')):
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dst, name))
                files[name.split('.')[0]] = name
        try:
            meta = json.load(open(os.path.join(build, 'meta.json')))
        except OSError:
            meta = {}
        pk, M, T, B = p['pack'], p['maker'], p['text'], p['box']
        lid = pk.get('library_id') or pdata.LIBMAP.get(pid) or ('kit-manager' if pid == 'kitmgr' else pk.get('plan_id') or pid)
        j = {'id': pid, 'pack_id': lid, 'title': pk['title'], 'subtitle': pk.get('subtitle', ''),
             'edition': pk.get('edition', ''), 'version': pk['version'], 'date': pk['date'], 'label': pk['label'],
             'iso': pk['label'] + '.ISO', 'maker': {'name': M['name'], 'kind': M['kind'], 'year': M['year'], 'place': M['place']},
             'tagline': T['tagline'], 'blurb': T['blurb'], 'package': B['type'],
             'price': ' '.join(B['price']), 'starburst': ' '.join(B['burst']) if B.get('burst') else None,
             'presets': meta.get('presets'), 'presets_xp': meta.get('presets_xp'), 'for': [brand.SW, brand.XP],
             'favourites': meta.get('favourites'), 'sound_credits': meta.get('credits') or ([T['credit']] if T.get('credit') else []),
             'files': files}
        with open(os.path.join(dst, 'pack.json'), 'w', encoding='utf-8') as f:
            json.dump(j, f, ensure_ascii=False, indent=1)
        allp.append(j)
    with open(os.path.join(out, 'packs.json'), 'w', encoding='utf-8') as f:
        json.dump(allp, f, ensure_ascii=False, indent=1)
    print('web export:', out, len(allp), 'packs')
    return out
