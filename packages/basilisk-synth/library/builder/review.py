#!/usr/bin/env python3
"""The local listening page: every kept preset by pack, with its MP3 (the demo phrase rendered by the real
machine), recipe, badges, a 0-10 rating (starts at 5), keep/reject, and Export (JSON to Downloads).

    review.py [--out /mnt/c/Users/willi/Desktop/sndrec-library]     data/library.json -> OUT/review.html, OUT/audio/
"""
import argparse, html, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import WORK, load_json, display_name
from packs import PACKS

CSS = r"""
:root{--desk1:#0b6f86;--desk2:#2aa6a6;--desk3:#ff9ad5;--panel:#c0c0c0;--hi:#fff;--lo:#808080;--dk:#000;--shade:#dfdfdf;
--ink:#000;--muted:#2c2c2c;--field:#fff;--fieldInk:#000;--title1:#000080;--title2:#1084d0;--accent:#000080;--accentInk:#fff;
--rowAlt:#ececec;--keep:#c9f2c9;--rej:#f6caca;--btn:#c0c0c0;--btnInk:#000;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--desk1:#0d0520;--desk2:#26103f;--desk3:#5a1a52;--panel:#2b2838;
--hi:#615c80;--lo:#16131f;--dk:#000;--shade:#3b3752;--ink:#eeeaf8;--muted:#bcb6d0;--field:#1b1826;--fieldInk:#eeeaf8;
--title1:#3d0f63;--title2:#b5307a;--accent:#ff8ad8;--accentInk:#1a0a20;--rowAlt:#25222f;--keep:#1d3b22;--rej:#47201f;--btn:#3a3650;--btnInk:#eeeaf8;color-scheme:dark}}
:root[data-theme="dark"]{--desk1:#0d0520;--desk2:#26103f;--desk3:#5a1a52;--panel:#2b2838;--hi:#615c80;--lo:#16131f;--dk:#000;--shade:#3b3752;
--ink:#eeeaf8;--muted:#bcb6d0;--field:#1b1826;--fieldInk:#eeeaf8;--title1:#3d0f63;--title2:#b5307a;--accent:#ff8ad8;--accentInk:#1a0a20;
--rowAlt:#25222f;--keep:#1d3b22;--rej:#47201f;--btn:#3a3650;--btnInk:#eeeaf8;color-scheme:dark}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--desk1);background:linear-gradient(180deg,var(--desk1) 0%,var(--desk2) 45%,var(--desk3) 100%) fixed;
font-family:Tahoma,"MS Sans Serif",Verdana,"DejaVu Sans",sans-serif;font-size:13px;color:var(--ink);padding:18px 16px 60px;overflow-x:hidden}
.win{background:var(--panel);border:2px solid;border-color:var(--hi) var(--dk) var(--dk) var(--hi);box-shadow:inset -1px -1px var(--lo),inset 1px 1px var(--shade);max-width:1180px;margin:0 auto 18px;min-width:0}
.bar{background:linear-gradient(90deg,var(--title1),var(--title2));color:#fff;font-weight:bold;padding:3px 6px;display:flex;justify-content:space-between;align-items:center;gap:8px}
.bar b{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.bar .n{font-weight:normal;font-size:11px;flex:none}
.body{padding:10px 12px;min-width:0}
h1{font-family:"Trebuchet MS",Tahoma,sans-serif;font-size:22px;margin:0 0 4px}
p{margin:0 0 8px;line-height:1.45}.lede{color:var(--muted);max-width:860px}.small{font-size:11px;color:var(--muted)}
button{font:12px Tahoma,"DejaVu Sans",sans-serif;color:var(--btnInk);padding:3px 10px;background:var(--btn);border:2px solid;border-color:var(--hi) var(--dk) var(--dk) var(--hi);box-shadow:inset -1px -1px var(--lo);cursor:pointer;min-height:24px}
button:active{border-color:var(--dk) var(--hi) var(--hi) var(--dk)}
button.on{background:var(--accent);color:var(--accentInk);font-weight:bold}
button:focus-visible,input:focus-visible,select:focus-visible{outline:2px dotted var(--accent);outline-offset:1px}
input[type=text],select{font:12px Tahoma,"DejaVu Sans",sans-serif;color:var(--fieldInk);background:var(--field);border:2px solid;border-color:var(--lo) var(--hi) var(--hi) var(--lo);padding:3px;max-width:100%}
.toolbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0}
.blurb{font-style:italic;color:var(--muted);margin:0 0 8px}
.row{display:grid;grid-template-columns:34px minmax(0,1fr) 150px 120px;gap:4px 10px;align-items:center;padding:6px 4px;border-top:1px solid var(--lo)}
.row:nth-child(even){background:var(--rowAlt)}.row.keep{background:var(--keep)}.row.rej{background:var(--rej)}
.play{width:30px;height:28px;padding:0;font-size:13px}
.nm{font-weight:bold}.cat{color:var(--muted);font-size:11px;margin-left:6px}
.badges{display:inline-flex;flex-wrap:wrap;gap:3px;margin-left:6px;vertical-align:middle}
.bd{font-size:10px;padding:0 4px;border:1px solid var(--lo);background:var(--field);color:var(--fieldInk);white-space:nowrap}
.bd.w31{background:#008080;color:#fff}.bd.xp{background:#245edb;color:#fff}.bd.lib{background:#8a5a00;color:#fff}.bd.v3{background:#7a0080;color:#fff}
.tags{font-size:11px;color:var(--muted);margin-top:2px;overflow-wrap:anywhere}
details{margin-top:3px}summary{cursor:pointer;font-size:11px;color:var(--muted)}
pre{margin:4px 0 0;font:11px/1.35 "Courier New",monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--field);color:var(--fieldInk);padding:4px;border:1px solid var(--lo)}
.rate{display:flex;align-items:center;gap:6px}.rate output{width:28px;text-align:right;font-weight:bold}
input[type=range]{width:100%;min-width:0;accent-color:var(--title2)}
.kr{display:flex;gap:4px}.kr button{flex:1;padding:3px 4px}
.wave{display:flex;align-items:flex-end;gap:1px;height:16px;margin-top:3px}.wave i{flex:1;background:var(--title2);min-height:1px;opacity:.75}
textarea{width:100%;font:11px/1.35 "Courier New",monospace;color:var(--fieldInk);background:var(--field)}
@media (max-width:760px){.row{grid-template-columns:34px minmax(0,1fr)}.row .rate,.row .kr{grid-column:2}}
"""

JS = r"""
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const KEY='sndrec-library-review-v1';
let ST={};try{ST=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){ST={}}
function save(){try{localStorage.setItem(KEY,JSON.stringify(ST))}catch(e){}}
const audio=new Audio();let playing=null;
function play(btn,src){if(playing===btn){audio.pause();btn.textContent='▶';playing=null;return}
 if(playing)playing.textContent='▶';audio.src=src;audio.play().catch(()=>{});btn.textContent='■';playing=btn}
audio.addEventListener('ended',()=>{if(playing){playing.textContent='▶';playing=null}});
function rowState(id){return ST[id]||(ST[id]={r:5,k:''})}
function paint(row){const s=rowState(row.dataset.id);row.classList.toggle('keep',s.k==='keep');row.classList.toggle('rej',s.k==='reject');
 row.querySelector('input[type=range]').value=s.r;row.querySelector('output').textContent=(+s.r).toFixed(1);
 row.querySelectorAll('.kr button').forEach(b=>b.classList.toggle('on',b.dataset.k===s.k))}
function init(){
 $$('.row').forEach(row=>{paint(row);
  row.querySelector('.play').onclick=e=>play(e.currentTarget,row.dataset.src);
  const r=row.querySelector('input[type=range]');r.oninput=()=>{rowState(row.dataset.id).r=+r.value;save();paint(row);count()};
  row.querySelectorAll('.kr button').forEach(b=>b.onclick=()=>{const s=rowState(row.dataset.id);s.k=s.k===b.dataset.k?'':b.dataset.k;save();paint(row);count()})});
 $('#q').oninput=filter;$('#ed').onchange=filter;$('#pk').onchange=filter;$('#st').onchange=filter;
 $$('.bExport').forEach(b=>b.onclick=()=>doExport(true));count()}
function filter(){const q=$('#q').value.toLowerCase(),ed=$('#ed').value,pk=$('#pk').value,st=$('#st').value;
 $$('.row').forEach(row=>{const d=row.dataset;const s=rowState(d.id);let ok=(!q||d.text.includes(q))&&(!pk||d.pack===pk);
  if(ed==='w31')ok=ok&&d.ed==='w31';if(ed==='xp')ok=ok&&d.ed==='xp';if(ed==='lib')ok=ok&&d.lib==='1';if(ed==='v3')ok=ok&&d.v3==='1';
  if(st==='keep')ok=ok&&s.k==='keep';if(st==='reject')ok=ok&&s.k==='reject';if(st==='open')ok=ok&&!s.k;if(st==='rated')ok=ok&&s.r!=5;
  row.style.display=ok?'':'none'});
 $$('.pack').forEach(p=>{p.style.display=[...p.querySelectorAll('.row')].some(r=>r.style.display!=='none')?'':'none'})}
function count(){let k=0,r=0,n=0;$$('.row').forEach(row=>{const s=rowState(row.dataset.id);if(s.k==='keep')k++;if(s.k==='reject')r++;if(s.r!=5)n++});
 $('#cnt').textContent=`${k} kept, ${r} rejected, ${n} rated of ${$$('.row').length}`}
function stamp(){const d=new Date(),p=n=>String(n).padStart(2,'0');return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`}
function doExport(dl){const out={page:'sndrec-library-review',exported:new Date().toISOString(),presets:{}};
 $$('.row').forEach(row=>{const s=rowState(row.dataset.id);out.presets[row.dataset.id]={rating:s.r,verdict:s.k||null,pack:row.dataset.pack,name:row.dataset.name,dna:row.dataset.dna}});
 const txt=JSON.stringify(out,null,1);$('#exportText').value=txt;
 if(dl){try{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([txt],{type:'application/json'}));a.download=`sndrec-library-review-${stamp()}.json`;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500);$('#msg').textContent='Saved to Downloads. Tell Claude "exported".'}catch(e){$('#msg').textContent='Download blocked: copy the JSON below.'}}}
document.addEventListener('DOMContentLoaded',init);
"""


def esc(s): return html.escape(str(s), quote=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/mnt/c/Users/willi/Desktop/sndrec-library')
    ap.add_argument('--lib', default='library.json')
    a = ap.parse_args()
    L = load_json(a.lib)
    os.makedirs(os.path.join(a.out, 'audio'), exist_ok=True)
    for p in L:
        src = os.path.join(WORK, 'mp3', p['slug'] + '.mp3')
        dst = os.path.join(a.out, 'audio', p['slug'] + '.mp3')
        if os.path.exists(src) and (not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src)):
            shutil.copyfile(src, dst)
    order = [pk['id'] for pk in PACKS]
    by = {}
    for p in L: by.setdefault(p['pack'], []).append(p)
    parts = []
    nw = sum(p['edition'] == 'w31' for p in L)
    parts.append('<div class="win"><div class="bar"><b>BASILISK Preset Library: review</b><span class="n">%d presets</span></div><div class="body">' % len(L))
    parts.append('<h1>Preset library, round 1</h1><p class="lede">Every preset here was built from Sound Recorder commands, '
                 'rendered through the real Windows 3.11 machine (BASILISK 16, render311) with a short phrase for its role, and passed the '
                 'automatic checks (every note heard, in tune, no clipping or DC, level set by the G gene). Play each one, move its rating '
                 '(0-10, starts at 5), mark Keep or Reject, then press <b>Export</b>: a JSON file lands in Downloads. Ratings are kept in this '
                 'browser. Badges: <span class="bd w31">W3.11</span> uses only the 3.x sounds, <span class="bd xp">XP</span> uses XP sounds, '
                 '<span class="bd lib">LIB</span> uses library-disc sounds, <span class="bd v3">v3</span> uses DNA v3 genes (3.11 only for now).</p>')
    parts.append('<div class="toolbar"><input type="text" id="q" placeholder="Search names, tags, DNA" aria-label="Search">'
                 '<select id="pk" aria-label="Pack"><option value="">All packs</option>%s</select>'
                 '<select id="ed" aria-label="Edition"><option value="">All editions</option><option value="w31">W3.11</option><option value="xp">XP</option><option value="lib">Library</option><option value="v3">v3</option></select>'
                 '<select id="st" aria-label="Status"><option value="">Any status</option><option value="open">Not marked</option><option value="keep">Kept</option><option value="reject">Rejected</option><option value="rated">Rated</option></select>'
                 '<button type="button" class="bExport"><b>Export...</b></button><span class="small" id="cnt"></span></div><p class="small" id="msg">%d W3.11, %d XP.</p></div></div>'
                 % (''.join('<option value="%s">%s</option>' % (esc(k), esc(next(x['name'] for x in PACKS if x['id'] == k))) for k in order if k in by), nw, len(L) - nw))
    for pid in order:
        ps = by.get(pid)
        if not ps: continue
        pk = next(x for x in PACKS if x['id'] == pid)
        parts.append('<div class="win pack"><div class="bar"><b>%s</b><span class="n">%d presets</span></div><div class="body"><p class="blurb">"%s"</p>'
                     % (esc(pk['name']), len(ps), esc(pk['blurb'])))
        ps.sort(key=lambda p: (p['category'], p['name']))
        for p in ps:
            bd = '<span class="bd %s">%s</span>' % ('w31' if p['edition'] == 'w31' else 'xp', 'W3.11' if p['edition'] == 'w31' else 'XP')
            if p['library']: bd += '<span class="bd lib">LIB</span>'
            if p['v3']: bd += '<span class="bd v3">v3</span>'
            xc = p.get('xp_check')
            if xc and xc.get('xpver') == '1.2.2':   # 1.2.2's regression: its results say nothing; 1.2.1's do
                xc = next((h for h in p.get('xp_check_history') or [] if h.get('xpver', '1.2.1') == '1.2.1'), None)
            if xc:
                bad = not xc['ok']
                bd += '<span class="bd" title="%s">%s</span>' % (esc('; '.join(xc['why']) or 'checked on the XP machine'),
                                                                 'XP check: 3.11 only' if bad else 'XP checked')
            bd += '<span class="bd">%s</span>' % esc(p['lineage'])
            srcs = ', '.join(sorted(set(display_name(n) for n in __import__('common').dna_names(p['dna_final']))))
            text = ' '.join([p['name'], p['category'], ' '.join(p['tags']), p['dna_final'], srcs, p.get('target_name') or '']).lower()
            wave = ''.join('<i style="height:%d%%"></i>' % max(4, int(v * 100)) for v in p.get('wave', []))
            parts.append(
                '<div class="row" data-id="%s" data-src="audio/%s.mp3" data-pack="%s" data-name="%s" data-dna="%s" data-ed="%s" data-lib="%d" data-v3="%d" data-text="%s">'
                '<button type="button" class="play" aria-label="Play %s">&#9654;</button>'
                '<div><span class="nm">%s</span><span class="cat">%s &middot; %s</span><span class="badges">%s</span>'
                '<div class="tags">%s &middot; sources: %s &middot; score %.0f &middot; peak %.1f dBFS</div><div class="wave">%s</div>'
                '<details><summary>Recipe and DNA</summary><pre>%s</pre><pre>%s</pre><div class="small">%s%s</div></details></div>'
                '<div class="rate"><input type="range" min="0" max="10" step="0.5" value="5" aria-label="Rating for %s"><output>5.0</output></div>'
                '<div class="kr"><button type="button" data-k="keep">Keep</button><button type="button" data-k="reject">Reject</button></div></div>'
                % (esc(p['slug']), esc(p['slug']), esc(pid), esc(p['name']), esc(p['dna_final']), p['edition'], p['library'], p['v3'], esc(text),
                   esc(p['name']), esc(p['name']), esc(p['category']), esc(p['phrase']), bd, esc(', '.join(p['tags'])), esc(srcs),
                   p['score'], p.get('phrase_peak', 0), wave, esc('\n'.join(p.get('recipe', []))), esc(p['dna_final']),
                   esc('From: %s (%s). ' % (p['target_name'], p['source']) if p.get('target_name') else 'Composed from the %s pools. ' % p['scat']),
                   esc(p.get('character', '')), esc(p['name'])))
        parts.append('</div></div>')
    parts.append('<div class="win"><div class="bar"><b>Export</b></div><div class="body"><p>Writes <kbd>sndrec-library-review-YYYYMMDD-HHMM.json</kbd> '
                 '(rating, verdict, pack, name and DNA of every preset) to Downloads, and shows it below.</p>'
                 '<button type="button" class="bExport"><b>Export ratings</b></button><textarea id="exportText" rows="8" readonly></textarea></div></div>')
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Preset Library Review</title><style>%s</style><script>%s</script></head><body>%s</body></html>' % (CSS, JS, '\n'.join(parts)))
    open(os.path.join(a.out, 'review.html'), 'w', encoding='utf-8').write(page)
    print('wrote', os.path.join(a.out, 'review.html'), len(L), 'presets')


if __name__ == '__main__':
    main()
