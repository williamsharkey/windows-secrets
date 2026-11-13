"""The owner's review page: one card per pack with its renders, icon, README preview and links to the HLP, PDF,
ISO and disc folder. Renders are copied next to the page; the docs are linked in place (file:// paths)."""
import html
import json
import os
import shutil


def winpath(p):
    p = os.path.abspath(p)
    if p.startswith('/mnt/') and len(p) > 6:
        return 'file:///%s:/%s' % (p[5].upper(), p[7:])
    return 'file://' + p


CSS = """
:root{--bg:#e9e7e1;--card:#fbfaf7;--ink:#1d1d1b;--mute:#6b6a64;--line:#d4d1c8;--accent:#1f4f8a}
@media (prefers-color-scheme:dark){:root{--bg:#18191b;--card:#222326;--ink:#ecebe6;--mute:#9b9a94;--line:#34353a;--accent:#8ab4ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,Segoe UI,Arial,sans-serif}
header{padding:28px 24px 10px;max-width:1500px;margin:auto}h1{margin:0 0 4px;font-size:26px}header p{margin:4px 0;color:var(--mute)}
nav{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0 0}nav a{font-size:13px;padding:3px 9px;border:1px solid var(--line);border-radius:12px;color:var(--ink);text-decoration:none;background:var(--card)}
main{max-width:1500px;margin:auto;padding:12px 24px 60px;display:grid;gap:22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:20px}
@media (max-width:900px){.card{grid-template-columns:1fr}}
.shots{display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:end}.shots img{width:100%;height:auto;display:block}
.pix{image-rendering:pixelated}.flat{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.flat a img{height:110px;width:auto;border:1px solid var(--line);background:#fff}
.icons{display:flex;gap:14px;align-items:end;margin:8px 0}.icons figure{margin:0;text-align:center;font-size:11px;color:var(--mute)}
h2{margin:0;font-size:21px}.kind{color:var(--mute);margin:2px 0 10px}.sw{display:inline-block;width:16px;height:16px;border:1px solid #0004;margin-right:2px;vertical-align:middle}
dl{display:grid;grid-template-columns:max-content 1fr;gap:3px 12px;margin:10px 0;font-size:14px}dt{color:var(--mute)}dd{margin:0}
.links a{display:inline-block;margin:0 10px 4px 0;color:var(--accent)}pre{background:#0d0d10;color:#d8d8d0;padding:10px;border-radius:6px;max-height:340px;overflow:auto;font:12px/1.25 Consolas,'Lucida Console',monospace;white-space:pre}
details summary{cursor:pointer;color:var(--accent);margin:6px 0}.files{columns:3 140px;font:12px Consolas,monospace;color:var(--mute)}
.note{font-size:12px;color:var(--mute)}
"""


def write(page, packs_dir, personas):
    page = os.path.abspath(page)
    root = os.path.dirname(page)
    assets = os.path.join(root, 'packs')
    os.makedirs(assets, exist_ok=True)
    cards, nav = [], []
    for p in personas:
        pid = p['id']
        pd = os.path.join(packs_dir, pid)
        rd = os.path.join(pd, 'renders')
        if not os.path.isdir(rd):
            continue
        dst = os.path.join(assets, pid)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(rd):
            shutil.copy2(os.path.join(rd, f), os.path.join(dst, f))
        rel = lambda f: 'packs/%s/%s' % (pid, f)
        has = lambda f: os.path.exists(os.path.join(rd, f))
        pk, M, F, L = p['pack'], p['maker'], p['files'], p['look']
        try:
            prev = json.load(open(os.path.join(pd, 'build', 'previews.json'), encoding='utf-8'))
        except OSError:
            prev = {}
        order = [F.get('nfo'), 'README.TXT'] + list(prev)
        first = next((k for k in order if k and k in prev), None)
        disc = os.path.join(pd, 'disc')
        dfiles = []
        for dp, dn, fn in os.walk(disc):
            for f in fn:
                dfiles.append(os.path.relpath(os.path.join(dp, f), disc).replace('/', '\\'))
        top = sorted(f for f in dfiles if '\\' not in f)
        nbsp = len([f for f in dfiles if f.upper().endswith('.BSP')])
        pal = L['palette'] if isinstance(L['palette'], list) else [L['paper'], L['ink'], L['accent'], L.get('accent2', L['ink'])]
        iso = os.path.join(packs_dir, 'out', pk['label'] + '.ISO')
        links = [('Help (.HLP)', os.path.join(disc, F['hlp'])), ('Manual (PDF)', os.path.join(disc, F['pdf'])),
                 ('Disc folder', disc), ('ISO image', iso), ('persona.json', os.path.join(pd, 'persona.json'))]
        if F.get('wri'):
            links.insert(2, ('Write manual (.WRI)', os.path.join(disc, F['wri'])))
        if F.get('rtf'):
            links.insert(2, ('RTF manual', os.path.join(disc, F['rtf'])))
        e = html.escape
        flat = ''.join('<a href="%s"><img class="pix" src="%s" alt="%s" title="%s"></a>' % (rel(f), rel(f), t, t)
                       for f, t in (('inlay.png', 'jewel-case inlay: front insert and tray card'), ('label.png', 'disc label (printed side)'),
                                    ('splash.png', 'splash .BMP as Windows shows it')) if has(f))
        nav.append('<a href="#%s">%s</a>' % (pid, e(pk['title'])))
        cards.append(f"""
<section class="card" id="{pid}">
 <div>
  <div class="shots">{'<img src="%s" alt="box render">' % rel('box.png') if has('box.png') else '<p class="note">box render pending</p>'}
  {'<img src="%s" alt="disc render">' % rel('disc.png') if has('disc.png') else ''}</div>
  <div class="flat">{flat}</div>
 </div>
 <div>
  <h2>{e(pk['title'])}</h2>
  <div class="kind">{e(M['name'])} &middot; {e(M['kind'])} &middot; {M['year']} &middot; {e(M['place'])}</div>
  <div class="icons">
   <figure><img class="pix" src="{rel('icon32.png')}" width="32" height="32" alt=""><figcaption>32</figcaption></figure>
   <figure><img class="pix" src="{rel('icon48.png')}" width="48" height="48" alt=""><figcaption>48</figcaption></figure>
   <figure><img class="pix" src="{rel('icon32.png')}" width="96" height="96" alt=""><figcaption>32 at 3x</figcaption></figure>
  </div>
  <dl>
   <dt>Plan pack</dt><dd>{e(pk.get('plan_title', pk['title']))}</dd>
   <dt>Tagline</dt><dd>{e(p['text']['tagline'])}</dd>
   <dt>Volume</dt><dd>{e(pk['label'])} &nbsp;/&nbsp; {e(pk['label_long'])} &middot; {e(pk['date'])}</dd>
   <dt>Package</dt><dd>{e(p['box']['type'])}, price sticker "{e(' '.join(p['box']['price']))}"{', starburst "' + e(' '.join(p['box']['burst'])) + '"' if p['box'].get('burst') else ''}</dd>
   <dt>Look</dt><dd>{''.join('<span class="sw" style="background:%s"></span>' % c for c in pal[:16])} {e(str(L['dither']))}{', no anti-aliasing' if not L['aa'] else ''}</dd>
   <dt>Voice</dt><dd>{e(M.get('voice', ''))}</dd>
   <dt>Presets</dt><dd>{nbsp} on the disc (placeholder seeds until the library builder has this pack)</dd>
  </dl>
  <div class="links">{''.join('<a href="%s">%s</a>' % (winpath(u), t) for t, u in links)}</div>
  {'<details open><summary>%s</summary><pre>%s</pre></details>' % (e(first), e(prev[first])) if first else ''}
  <details><summary>Other text files</summary>{''.join('<p><b>%s</b></p><pre>%s</pre>' % (e(k), e(v)) for k, v in prev.items() if k != first)}</details>
  <details><summary>Disc root ({len(dfiles)} files)</summary><div class="files">{'<br>'.join(e(f) for f in top)}</div></details>
 </div>
</section>""")
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sound Packs Review</title><style>{CSS}</style></head><body>
<header><h1>BASILISK sound packs: makers and discs</h1>
<p>{len(cards)} packs, each from its own fictional maker. Every name of a person, company, product, board or domain on these discs is invented; the pictures are public-domain art from the names-page library (credits in each PDF).</p>
<p class="note">Renders: Blender 4.2 Cycles (shrink-wrap film, price sticker, shadow catcher). Flat art is shown at print resolution, never smooth-scaled. Links open the files in place in the repo (packages/basilisk-synth/library/packs/).</p>
<nav>{''.join(nav)}</nav></header><main>{''.join(cards)}</main></body></html>"""
    with open(page, 'w', encoding='utf-8') as f:
        f.write(doc)
    print('gallery:', page)
