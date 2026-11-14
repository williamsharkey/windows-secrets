/* sndrec.html and sndrec-xp.html: the preset browser (players, waveforms, source badges, recipes, filters).
   The page sets: the tabs (.tab[data-ed], the selected one first shown), #panel[data-src] (the presets JSON, default
   sndrec/presets.json) and, for BASILISK 16, #panel[data-soundfilter] (filter by Windows sounds used: 3.x only, or
   with XP's sounds, which BASILISK 16 carries in C:\XPSOUNDS). An optional #libgo button opens the picks tab. */
(function () {
  'use strict';
  var panelEl = document.getElementById('panel'), selTab = document.querySelector('.tab[aria-selected="true"]');
  var data = null, ed = selTab ? selTab.dataset.ed : 'b16', edf = 'All', pack = 'All', cat = 'All', current = null;
  var player = document.getElementById('player');
  var list = document.getElementById('list'), countEl = document.getElementById('count');
  var PLAY = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 1.5v11l9-5.5z" fill="currentColor"/></svg>';
  var STOP = '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="2.5" y="2.5" width="9" height="9" fill="currentColor"/></svg>';

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); }
  function waveSvg(w, color) {
    var r = '', n = w.length;
    for (var i = 0; i < n; i++) { var h = Math.max(1, w[i] / 100 * 22); r += '<rect x="' + (i * 2 + 0.3) + '" y="' + (12 - h / 2) + '" width="1.4" height="' + h + '"/>'; }
    return '<svg viewBox="0 0 ' + (n * 2) + ' 24" preserveAspectRatio="none" aria-hidden="true" fill="' + color + '">' + r + '</svg>';
  }
  // ---- source sounds: a badge per sound, its origin mark, full facts in a popover (hover, focus or tap)
  var MARK = {'311': ['m311', '3.11', 'Windows for Workgroups 3.11 original'], '31': ['m31', '3.1', 'Windows 3.1 original'],
    'xp': ['mxp', 'XP', 'Windows XP original'], 'both': ['mboth', '3.11=XP', 'The same file in Windows 3.11 and XP'], 'fb': ['mfb', '\u2192DING', 'XP name: DING.WAV plays on 3.11'],
    'cc0': ['mcc0', 'CC0', 'Library recording, CC0'], 'pd': ['mpd', 'PD', 'Library recording, public domain'],
    'syn': ['msyn', 'SYN', 'Synthesized (library)'], 'unk': ['munk', '?', 'Unknown name']};
  function mk(o) { var m = MARK[o] || MARK.unk; return '<span class="mk ' + m[0] + '" aria-hidden="true">' + m[1] + '</span>'; }
  function facts(n, S) {
    var x = S[n] || {o: 'unk'}, m = MARK[x.o] || MARK.unk, r = '<div class="item"><h4>' + mk(x.o) + '<span>' + esc(x.d || n) + '</span></h4>';
    if (x.o === 'fb') r += '<div class="warn">Not an original 3.11 sound: <b>' + esc(x.xp) + '</b> is a Windows XP file, so BASILISK 16 plays DING.WAV for it.</div>';
    r += '<dl><dt>Origin</dt><dd>' + esc(x.from || m[2]) + '</dd>';
    if (x.path) r += '<dt>File</dt><dd><code>' + esc(x.path) + '</code></dd>';
    if (x.dur != null) r += '<dt>Length</dt><dd>' + x.dur + ' s</dd>';
    if (x.fmt) r += '<dt>Format</dt><dd>' + esc(x.fmt) + '</dd>';
    r += '<dt>Root</dt><dd>' + (x.root ? esc(x.root) : 'not pitched / not given') + '</dd>';
    if (x.what) r += '<dt>Sound</dt><dd>' + esc(x.what) + '</dd>';
    if (x.how) r += '<dt>Made by</dt><dd>' + esc(x.how) + '</dd>';
    if (x.author) r += '<dt>Author</dt><dd>' + esc(x.author) + '</dd>';
    if (x.lic) r += '<dt>Licence</dt><dd>' + esc(x.lic) + '</dd>';
    if (x.url) r += '<dt>Source</dt><dd><a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.url.replace(/^https?:\/\/(www\.)?/, '').slice(0, 60)) + '</a></dd>';
    return r + '</dl></div>';
  }
  function srcBadges(p, S) {
    var box = el('div', 'srcs');
    box.setAttribute('role', 'list'); box.setAttribute('aria-label', 'Sounds used');
    (p.src || []).forEach(function (n) {
      var x = S[n] || {o: 'unk'}, b = el('button', 'src' + (x.o === 'fb' ? ' fb' : ''), mk(x.o) + '<span class="nmx">' + esc(x.d || n) + '</span>');
      b.type = 'button'; b.setAttribute('role', 'listitem');
      b.setAttribute('aria-label', (x.d || n) + ': ' + (MARK[x.o] || MARK.unk)[2] + (x.path ? ', ' + x.path : ''));
      b._html = function () { return facts(n, S); };
      box.appendChild(b);
    });
    var more = el('button', 'src more', '+0'); more.type = 'button'; more.hidden = true;
    more._html = function () {
      return [].filter.call(box.children, function (c) { return c !== more && c.hidden; }).map(function (c) { return c._html(); }).join('');
    };
    box.appendChild(more);
    return box;
  }
  function fit(box) {   // all badges; else marks only; else as many marks as fit, and +N for the rest
    var kids = [].slice.call(box.children), more = kids.pop();
    kids.forEach(function (k) { k.hidden = false; }); more.hidden = true; box.classList.remove('compact');
    if (box.scrollWidth <= box.clientWidth + 1) return;
    box.classList.add('compact');
    if (box.scrollWidth <= box.clientWidth + 1) return;
    more.hidden = false;
    for (var i = kids.length - 1; i >= 0 && box.scrollWidth > box.clientWidth + 1; i--) {
      kids[i].hidden = true;
      var h = kids.filter(function (k) { return k.hidden; }).length;
      more.textContent = '+' + h; more.setAttribute('aria-label', h + ' more sound' + (h > 1 ? 's' : ''));
    }
  }
  // recipes: the converter's one-line form if it fits the cell's width in its own font, else its lines
  var meas = document.createElement('canvas').getContext('2d');
  // Recipes (PRESET-ENGINE-2.md 17.1b): shown pretty; selecting, focusing or double-clicking one turns it into its ASCII
  // form, which is what is typed and copied. Both forms come from the converter (toRecipe, prettify) at build time.
  function recHTML(r, asc, one) {
    function ln(t, cls) { return '<div class="ln' + (cls ? ' ' + cls : '') + '">' + esc(t) + '</div>'; }
    if (r.kit) {
      var lay = asc ? r.kit.layers : r.kit.players, env = asc ? r.kit.env : r.kit.penv, pads = asc ? r.kit.pads : r.kit.ppads;
      var srcs = r.kit.layers.map(function (l) { return l.split(/\s+/)[0]; });
      return '<details' + (asc ? ' open' : '') + '><summary>kit ' + (asc ? '' : '\u00b7 ') + r.kit.n + ' pads ' + (asc ? '' : '\u00b7 ') + esc(srcs.join(', ')) + '</summary>' +
        lay.map(function (l) { return ln(l); }).join('') + (env ? ln(env, 'env') : '') + pads.map(function (l) { return ln(l, 'pad'); }).join('') + '</details>';
    }
    if (one) return ln(asc ? r.one : r.pone, 'one');
    return (asc ? r.lines : r.plines).map(function (l) { return ln(l, /^env\s/.test(l) ? 'env' : ''); }).join('');
  }
  function fitRec(box) {   // the one-line form if its pretty text fits the cell in its own font, else a line per layer
    var r = box._p.rec, cs = getComputedStyle(box);
    var w = box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    meas.font = cs.fontStyle + ' ' + cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
    var one = !r.kit && meas.measureText(r.pone).width <= w;
    if (box._one === one && box._drawn) return;
    box._one = one; setRec(box, !!box._asc, true);
  }
  function setRec(box, asc, force) {
    if (!force && !!box._asc === asc) return;
    var open = box.querySelector('details') && box.querySelector('details').open;
    box._asc = asc; box._drawn = true;
    box.classList.toggle('ascii', asc);
    box.innerHTML = recHTML(box._p.rec, asc, box._one);
    if (open) box.querySelector('details').open = true;
  }
  function recOf(n) { while (n && n.nodeType !== 1) n = n.parentNode; return n && n.closest ? n.closest('.rec') : null; }
  list.addEventListener('mousedown', function (e) { var b = recOf(e.target); if (b && !(e.target.closest && e.target.closest('summary'))) setRec(b, true); });
  list.addEventListener('focusin', function (e) { if (e.target.classList && e.target.classList.contains('rec')) setRec(e.target, true); });
  list.addEventListener('focusout', function (e) { var b = e.target.classList && e.target.classList.contains('rec') ? e.target : null; if (b) setTimeout(revertRecs, 0); });
  function revertRecs() {   // back to pretty when nothing in it is selected or focused
    var sel = window.getSelection(), r = sel.rangeCount && !sel.isCollapsed ? sel.getRangeAt(0) : null;
    [].forEach.call(document.querySelectorAll('.rec.ascii'), function (b) {
      if (document.activeElement === b || (r && r.intersectsNode(b))) return;
      setRec(b, false);
    });
  }
  document.addEventListener('selectionchange', function () {
    var sel = window.getSelection();
    if (!sel.rangeCount || sel.isCollapsed) { revertRecs(); return; }
    var r = sel.getRangeAt(0), a = recOf(sel.anchorNode), f = recOf(sel.focusNode);
    // a recipe wholly inside a selection that spans rows: switch it too (its own text is not a boundary of the range)
    [].forEach.call(list.querySelectorAll('.rec:not(.ascii)'), function (b) { if (b !== a && b !== f && r.intersectsNode(b)) setRec(b, true); });
  });
  // copy: always ASCII. Selections in recipes already are; a recipe the selection only enters at its far end is still
  // pretty, so its symbols go back through the converter's own substitution (17.1: × x, ± +-, ¢ c, – -, " · " two spaces, … ...)
  document.addEventListener('copy', function (e) {
    var sel = window.getSelection();
    if (!sel.rangeCount || sel.isCollapsed) return;
    var r = sel.getRangeAt(0), hit = [].some.call(document.querySelectorAll('.rec'), function (b) { return r.intersectsNode(b); });
    if (!hit) return;
    var t = sel.toString().replace(/ \u00b7 /g, '  ').replace(/\u00d7/g, 'x').replace(/\u00b1/g, '+-').replace(/\u00a2/g, 'c')
      .replace(/\u2013/g, '-').replace(/\u2026/g, '...').replace(/\u2192/g, '->').replace(/\u00b7/g, '-');
    e.clipboardData.setData('text/plain', t); e.preventDefault();
  });
  function fitAll() {
    [].forEach.call(document.querySelectorAll('.srcs'), fit);
    [].forEach.call(document.querySelectorAll('.rec'), fitRec);
  }
  var fitT = 0;
  window.addEventListener('resize', function () { cancelAnimationFrame(fitT); fitT = requestAnimationFrame(function () { fitAll(); hidePop(); }); });

  var pop = document.getElementById('pop'), popFor = null, popTimer = 0;
  function showPop(b) {
    clearTimeout(popTimer);
    if (popFor && popFor !== b) popFor.setAttribute('aria-expanded', 'false');
    popFor = b; b.setAttribute('aria-expanded', 'true');
    pop.innerHTML = b._html(); pop.classList.add('on');
    place();
  }
  function place() {   // under the badge, or above it near the bottom; always inside the window
    var b = popFor; if (!b) return;
    var r = b.getBoundingClientRect(), vw = document.documentElement.clientWidth, vh = window.innerHeight;
    var below = vh - r.bottom - 14, above = r.top - 14;
    pop.style.maxHeight = 'none';
    var w = pop.offsetWidth, h = pop.offsetHeight, y;
    if (h <= below) y = r.bottom + 6;
    else if (h <= above) y = r.top - h - 6;
    else if (below >= above) { pop.style.maxHeight = below + 'px'; y = r.bottom + 6; }   // never over its badge: scroll inside
    else { pop.style.maxHeight = above + 'px'; y = 8; }
    var x = Math.max(8, Math.min(r.left + r.width / 2 - w / 2, vw - w - 8));
    pop.style.left = x + 'px'; pop.style.top = y + 'px';
  }
  function hidePop() { clearTimeout(popTimer); pop.classList.remove('on'); if (popFor) popFor.setAttribute('aria-expanded', 'false'); popFor = null; }
  function laterHide() { clearTimeout(popTimer); popTimer = setTimeout(hidePop, 180); }
  var touch = false;
  document.addEventListener('touchstart', function () { touch = true; }, {passive: true});
  list.addEventListener('mouseover', function (e) { var b = e.target.closest && e.target.closest('.src'); if (b && !touch) showPop(b); });
  list.addEventListener('mouseout', function (e) { var b = e.target.closest && e.target.closest('.src'); if (b && !touch) laterHide(); });
  var focusedAt = 0;
  list.addEventListener('focusin', function (e) { var b = e.target.closest && e.target.closest('.src'); if (b) { showPop(b); focusedAt = Date.now(); } });
  list.addEventListener('focusout', function (e) { if (e.target.closest && e.target.closest('.src') && !pop.contains(e.relatedTarget)) laterHide(); });
  list.addEventListener('click', function (e) { var b = e.target.closest && e.target.closest('.src'); if (!b) return; if (popFor === b && pop.classList.contains('on') && Date.now() - focusedAt > 400) hidePop(); else showPop(b); });
  pop.addEventListener('mouseenter', function () { clearTimeout(popTimer); });
  pop.addEventListener('mouseleave', laterHide);
  document.addEventListener('click', function (e) { if (!pop.contains(e.target) && !(e.target.closest && e.target.closest('.src'))) hidePop(); });
  window.addEventListener('scroll', function () {
    if (!popFor) return;
    var r = popFor.getBoundingClientRect();
    if (r.bottom < 0 || r.top > window.innerHeight) hidePop(); else place();
  }, {passive: true});

  function stop() {
    if (!current) return;
    player.pause();
    current.row.classList.remove('playing');
    current.btn.innerHTML = PLAY; current.btn.setAttribute('aria-pressed', 'false');
    current.btn.setAttribute('aria-label', 'Play ' + current.p.name);
    current.done.style.clipPath = 'inset(0 100% 0 0)';
    current = null;
  }
  function play(p, row, btn, done) {
    if (current && current.p === p) { stop(); return; }
    stop();
    pauseVideos();
    var me = current = {p: p, row: row, btn: btn, done: done};
    player.src = p.file;
    var pr = player.play();
    if (pr && pr.catch) pr.catch(function (e) { if (current === me && e && e.name !== 'AbortError') stop(); });
    row.classList.add('playing');
    btn.innerHTML = STOP; btn.setAttribute('aria-pressed', 'true'); btn.setAttribute('aria-label', 'Stop ' + p.name);
    tick();
  }
  function tick() {
    if (!current) return;
    var d = player.duration || current.p.sec, f = d ? Math.min(1, player.currentTime / d) : 0;
    current.done.style.clipPath = 'inset(0 ' + ((1 - f) * 100).toFixed(2) + '% 0 0)';
    if (!player.paused) requestAnimationFrame(tick);
  }
  player.addEventListener('ended', stop);
  player.addEventListener('play', tick);
  function pauseVideos() { if (window.PxPlayer) PxPlayer.pauseAll(); }
  window.onPxPlay = function () { stop(); };   // a capture playing stops the preset player

  function copy(text, b) {
    function ok() { var t = b.textContent; b.textContent = 'Copied'; setTimeout(function () { b.textContent = t; }, 1200); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(ok, fallback); else fallback();
    function fallback() {
      var t = document.createElement('textarea'); t.value = text; t.setAttribute('readonly', ''); t.style.position = 'fixed'; t.style.opacity = '0';
      document.body.appendChild(t); t.select();
      try { document.execCommand('copy'); ok(); } catch (e) {}
      document.body.removeChild(t);
    }
  }

  function chips(box, label, values, sel, on) {
    box.innerHTML = '';
    box.appendChild(el('span', 'lbl', label));
    values.forEach(function (v) {
      var b = el('button', 'chip', esc(v[0]) + (v[1] != null ? ' <span class="sr">(' + v[1] + ' presets)</span><span aria-hidden="true"> ' + v[1] + '</span>' : ''));
      b.type = 'button'; b.setAttribute('aria-pressed', String(v[0] === sel));
      b.addEventListener('click', function () { on(v[0]); });
      box.appendChild(b);
    });
  }
  function tally(rows, key) {
    var m = {}, order = [];
    rows.forEach(function (p) { if (!(p[key] in m)) { m[p[key]] = 0; order.push(p[key]); } m[p[key]]++; });
    return [['All', rows.length]].concat(order.map(function (k) { return [k, m[k]]; }));
  }

  function render() {
    var E = data && data.editions[ed];
    document.getElementById('filters').hidden = !E;
    document.getElementById('soon').hidden = !!E;
    list.innerHTML = '';
    if (!E) { countEl.textContent = ''; return; }
    var all = E.presets;
    var notes = {
      b16: 'BASILISK 16 1.2.1, 76 programs, rendered with <code>render311</code>, which gives the same result on every run.',
      lib: '<b>Coming in BASILISK 16 1.3.0.</b> The owner\'s favourites from the new library (1,039 presets in 17 sound packs), rated 6.5 to 8.5 of 10 on the review page. Each demo is the file the owner rated: rendered by <code>render311</code> through the real Windows 3.11 machine (main 4bda617), checked that every note sounds. Their level is the preset\'s own, so some are a little quieter than the other demos.',
      xp: 'BASILISK SYNTH 1.2.2, 43 programs. XP\'s timing is not sample-accurate, so its renders differ a little run to run; each demo is the best of up to four takes.',
      libxp: 'The owner\'s picks from the BASILISK 16 1.3.0 library that also play on XP, rendered by BASILISK SYNTH 1.2.2.'};
    document.getElementById('ednote').innerHTML = notes[ed] || '';
    // DNA.md 2.4: a DNA uses XP's sounds when it names any XP file (in BASILISK 16 they are in C:\XPSOUNDS); library
    // sounds do not count. Shown as a filter only where the page asks for it (BASILISK 16).
    all.forEach(function (p) { p.edl = p.ed === 'xp' ? 'With XP sounds' : '3.x sounds only'; });
    var useF = panelEl.hasAttribute('data-soundfilter');
    var eds = tally(all, 'edl').sort(function (a, b) { var o = {All: 0, '3.x sounds only': 1, 'With XP sounds': 2}; return o[a[0]] - o[b[0]]; });
    var ec = document.getElementById('edchips');
    if (ec) { ec.hidden = !useF; if (useF) chips(ec, 'Windows sounds', eds, edf, function (v) { edf = v; pack = 'All'; cat = 'All'; render(); }); }
    if (!useF) edf = 'All';
    var inEd = all.filter(function (p) { return edf === 'All' || p.edl === edf; });
    chips(document.getElementById('packchips'), 'Sound pack', tally(inEd, 'pack'), pack, function (v) { pack = v; cat = 'All'; render(); });
    var inPack = inEd.filter(function (p) { return pack === 'All' || p.pack === pack; });
    chips(document.getElementById('catchips'), 'Category', tally(inPack, 'cat'), cat, function (v) { cat = v; render(); });
    var q = document.getElementById('q').value.trim().toLowerCase();
    var rows = inPack.filter(function (p) {
      return (cat === 'All' || p.cat === cat) && (!q || (p.name + ' ' + p.dna + ' ' + p.cat + ' ' + (p.rec ? p.rec.one : '') + ' ' + (p.src || []).join(' ')).toLowerCase().indexOf(q) >= 0);
    });
    countEl.textContent = rows.length + ' of ' + all.length + ' presets';
    rows.forEach(function (p) {
      var li = el('li', 'row');
      var btn = el('button', 'btn play', PLAY); btn.type = 'button';
      var meta = el('div', 'meta', '<div class="nm"><span class="t">' + esc(p.name) + '</span></div><div class="sub">' + esc(p.cat) + ' &middot; ' + esc(p.phrase) +
        (p.rating ? ' &middot; ' + esc(p.pack) + ' &middot; rated ' + p.rating + '/10' : ' &middot; program ' + (p.n + 1)) + (p.macro ? '<span class="badge">Macro 1 moves</span>' : '') + (p.flags.length ? '<span class="badge">issue</span>' : '') + '</div>');
      meta.firstChild.appendChild(srcBadges(p, E.sounds || {}));
      var wave = el('div', 'wave');
      var done = el('div', 'done');
      wave.innerHTML = waveSvg(p.wave, '#3a7a3a');
      done.innerHTML = waveSvg(p.wave, '#00ff00');
      done.style.position = 'absolute'; done.style.inset = '0';
      wave.appendChild(done);
      if (p.file) {
        btn.setAttribute('aria-label', 'Play ' + p.name); btn.setAttribute('aria-pressed', 'false');
        btn.addEventListener('click', function () { play(p, li, btn, done); });
        wave.addEventListener('click', function () { play(p, li, btn, done); });
      } else {
        btn.disabled = true; btn.setAttribute('aria-label', p.name + ': silent, nothing to play');
      }
      var dna = el('div', 'dna');
      var code = p.rec ? el('div', 'rec') : el('code', null, esc(p.dna));
      if (p.rec) { code._p = p; code.tabIndex = 0; code.setAttribute('aria-label', 'Recipe of ' + p.name + ' (focus for the typable form): ' + p.rec.one); }
      var cp = el('button', 'btn copy', 'Copy DNA'); cp.type = 'button'; cp.title = p.dna; cp.setAttribute('aria-label', 'Copy the DNA of ' + p.name + ': ' + p.dna);
      cp.addEventListener('click', function () { copy(p.dna, cp); });
      dna.appendChild(code); dna.appendChild(cp);
      li.appendChild(btn); li.appendChild(meta); li.appendChild(wave); li.appendChild(dna);
      if (p.flags.length || p.note) {
        var note = p.note || p.flags.join('; ');
        li.appendChild(el('div', 'issue', '<b>' + (p.flags.length ? 'Issue' : 'Note') + ':</b> ' + esc(note)));
      }
      if (current && current.p === p) { current.row = li; current.btn = btn; current.done = done; li.classList.add('playing'); btn.innerHTML = STOP; btn.setAttribute('aria-pressed', 'true'); }
      list.appendChild(li);
    });
    fitAll();
  }

  document.getElementById('q').addEventListener('input', render);
  var tabs = [].slice.call(document.querySelectorAll('.tab'));
  function selectTab(t, focus) {
    tabs.forEach(function (o) { var s = o === t; o.setAttribute('aria-selected', String(s)); o.tabIndex = s ? 0 : -1; });
    document.getElementById('panel').setAttribute('aria-labelledby', t.id);
    if (focus) t.focus();
    if (ed !== t.dataset.ed) { stop(); ed = t.dataset.ed; edf = 'All'; pack = 'All'; cat = 'All'; render(); }
  }
  var libgo = document.getElementById('libgo');
  if (libgo) libgo.addEventListener('click', function () { selectTab(document.getElementById('tab-lib')); });
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { selectTab(t); });
    t.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); selectTab(tabs[(i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length], true); }
    });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { if (popFor) { var f = popFor; hidePop(); f.focus(); } else stop(); } });

  fetch(panelEl.getAttribute('data-src') || 'sndrec/presets.json').then(function (r) { return r.json(); }).then(function (d) { data = d; render(); })
    .catch(function () { list.innerHTML = '<li class="note">The preset list could not be loaded.</li>'; });
})();
