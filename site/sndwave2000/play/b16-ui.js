// BASILISK 16 "Try it online": the controls under the screen, drawn with Windows for Workgroups 3.11's own pixels.
// Text is set in the bitmap fonts taken from the image (MS Sans Serif 8 and System, ui_assets.py), and the icons are
// Sound Recorder's own. Every widget is one canvas whose pixels are exactly k x k device pixels
// (k = max(1, round(devicePixelRatio))), drawn nearest-neighbour: nothing is smoothed.
(function () {
  'use strict';
  var UI = window.B16UI = {}, atlas = null, meta = null, ready = null;
  var C = { face: '#c0c0c0', hi: '#ffffff', lo: '#808080', ink: '#000000', sel: '#000080', selInk: '#ffffff', win: '#ffffff', title: '#000080', gray: '#808080' };
  UI.C = C;
  UI.load = function (base, v) {
    if (ready) return ready;
    ready = Promise.all([
      new Promise(function (res, rej) { var im = new Image(); im.onload = function () { res(im); }; im.onerror = rej; im.src = base + 'ui.png?v=' + v; }),
      fetch(base + 'ui.json?v=' + v).then(function (r) { return r.json(); })
    ]).then(function (r) { atlas = r[0]; meta = r[1]; return UI; });
    return ready;
  };
  UI.k = function () { return Math.max(1, Math.round(window.devicePixelRatio || 1)); };
  UI.measure = function (s, font) {
    var f = meta.fonts[font || 'sans'], w = 0;
    for (var i = 0; i < s.length; i++) { var g = f.glyphs[s.charCodeAt(i)] || f.glyphs[63]; w += g ? g[2] : 0; }
    return w;
  };
  UI.fontHeight = function (font) { return meta.fonts[font || 'sans'].height; };
  // text into a 2D context at (x, y) (top left), in native pixels, coloured
  var tint = {};
  function tinted(color) {
    if (tint[color]) return tint[color];
    var c = document.createElement('canvas'); c.width = atlas.width; c.height = atlas.height;
    var x = c.getContext('2d'); x.drawImage(atlas, 0, 0); x.globalCompositeOperation = 'source-in'; x.fillStyle = color; x.fillRect(0, 0, c.width, c.height);
    return (tint[color] = c);
  }
  UI.text = function (ctx, s, x, y, font, color) {
    var f = meta.fonts[font || 'sans'], src = tinted(color || C.ink), h = f.height;
    for (var i = 0; i < s.length; i++) {
      var g = f.glyphs[s.charCodeAt(i)] || f.glyphs[63]; if (!g) continue;
      ctx.drawImage(src, g[0], g[1], g[2], h, x, y, g[2], h); x += g[2];
    }
    return x;
  };
  UI.sprite = function (ctx, name, x, y) { var s = meta.sprites[name]; ctx.drawImage(atlas, s[0], s[1], s[2], s[3], x, y, s[2], s[3]); };
  UI.spriteSize = function (name) { var s = meta.sprites[name]; return [s[2], s[3]]; };
  // the dotted focus rectangle Windows 3.1 draws (every other pixel)
  UI.focusRect = function (ctx, x, y, w, h) {
    ctx.fillStyle = C.ink;
    for (var i = 0; i < w; i += 2) { ctx.fillRect(x + i, y, 1, 1); ctx.fillRect(x + i, y + h - 1, 1, 1); }
    for (var j = 0; j < h; j += 2) { ctx.fillRect(x, y + j, 1, 1); ctx.fillRect(x + w - 1, y + j, 1, 1); }
  };
  // a canvas of W x H native pixels, shown at exactly k x k device pixels each; draw(ctx) paints it in native pixels
  UI.canvas = function (el, W, H, draw) {
    var k = UI.k(), dpr = window.devicePixelRatio || 1;
    if (el.width !== W * k || el.height !== H * k) { el.width = W * k; el.height = H * k; }
    el.style.width = (W * k / dpr) + 'px'; el.style.height = (H * k / dpr) + 'px';
    var ctx = el.getContext('2d'); ctx.imageSmoothingEnabled = false;
    ctx.setTransform(k, 0, 0, k, 0, 0); ctx.clearRect(0, 0, W, H);
    draw(ctx);
    return el;
  };
  // a Windows 3.1 push button: black frame with its corners cut, white highlight, two-pixel shadow; pressed, default,
  // focused (dotted rectangle round the label) and disabled (grey label) as 3.1 draws them
  UI.drawButton = function (ctx, W, H, o) {
    ctx.fillStyle = C.face; ctx.fillRect(1, 1, W - 2, H - 2);
    ctx.fillStyle = C.ink;
    var b = o.isDefault ? 2 : 1;
    for (var t = 0; t < b; t++) { ctx.fillRect(1 + t, t, W - 2 - 2 * t, 1); ctx.fillRect(1 + t, H - 1 - t, W - 2 - 2 * t, 1); ctx.fillRect(t, 1 + t, 1, H - 2 - 2 * t); ctx.fillRect(W - 1 - t, 1 + t, 1, H - 2 - 2 * t); }
    var x0 = b, y0 = b, x1 = W - 1 - b, y1 = H - 1 - b;
    if (o.pressed) { ctx.fillStyle = C.lo; ctx.fillRect(x0, y0, x1 - x0 + 1, 1); ctx.fillRect(x0, y0, 1, y1 - y0 + 1); }
    else {
      ctx.fillStyle = C.hi; ctx.fillRect(x0, y0, x1 - x0, 1); ctx.fillRect(x0, y0, 1, y1 - y0);
      ctx.fillStyle = C.lo; ctx.fillRect(x0, y1, x1 - x0 + 1, 1); ctx.fillRect(x1, y0, 1, y1 - y0 + 1);
      ctx.fillRect(x0 + 1, y1 - 1, x1 - x0 - 1, 1); ctx.fillRect(x1 - 1, y0 + 1, 1, y1 - y0 - 1);
    }
    var d = o.pressed ? 1 : 0, cw = 0, chh = 0, lx, ly;
    if (o.sprite) { var sz = UI.spriteSize(o.sprite); cw = sz[0]; chh = sz[1]; lx = ((W - cw) >> 1) + d; ly = ((H - chh) >> 1) + d; UI.sprite(ctx, o.sprite, lx, ly); }
    if (o.label) {
      var tw = UI.measure(o.label, 'system'), th = UI.fontHeight('system');
      lx = ((W - tw) >> 1) + d + (o.sprite ? 0 : 0); ly = ((H - th) >> 1) + d; cw = tw; chh = th;
      if (o.disabled) { UI.text(ctx, o.label, lx + 1, ly + 1, 'system', C.hi); UI.text(ctx, o.label, lx, ly, 'system', C.gray); }
      else UI.text(ctx, o.label, lx, ly, 'system', C.ink);
    }
    if (o.focused && !o.disabled) UI.focusRect(ctx, lx - 2, ly - 1, cw + 4, chh + 2);
  };
  // a real <button> whose face is a canvas: keyboard, focus and screen readers as usual, pixels as 3.1
  UI.button = function (label, o) {
    o = o || {};
    var b = document.createElement('button'); b.type = 'button'; b.className = 'b16b';
    b.setAttribute('aria-label', o.aria || label || '');
    var cv = document.createElement('canvas'); b.appendChild(cv);
    var st = { label: label, sprite: o.sprite, isDefault: !!o.isDefault, pressed: false, focused: false, toggled: false };
    var W = o.width || Math.max(56, (label ? UI.measure(label, 'system') : 17) + 18), H = o.height || 23;
    function paint() { UI.canvas(cv, W, H, function (ctx) { UI.drawButton(ctx, W, H, { label: st.label, sprite: st.sprite, isDefault: st.isDefault, pressed: st.pressed || st.toggled, focused: st.focused, disabled: b.disabled }); }); }
    b.addEventListener('pointerdown', function () { if (!b.disabled) { st.pressed = true; paint(); } });
    ['pointerup', 'pointerleave', 'pointercancel'].forEach(function (e) { b.addEventListener(e, function () { if (st.pressed) { st.pressed = false; paint(); } }); });
    b.addEventListener('keydown', function (e) { if ((e.key === ' ' || e.key === 'Enter') && !b.disabled) { st.pressed = true; paint(); } });
    b.addEventListener('keyup', function () { if (st.pressed) { st.pressed = false; paint(); } });
    b.addEventListener('focus', function () { st.focused = b.matches(':focus-visible'); paint(); });
    b.addEventListener('blur', function () { st.focused = false; paint(); });
    b.repaint = paint;
    b.setToggled = function (t) { st.toggled = !!t; b.setAttribute('aria-pressed', String(!!t)); paint(); };
    b.setLabel = function (l) { st.label = l; b.setAttribute('aria-label', o.aria || l); paint(); };
    b.setDisabled = function (d) { b.disabled = !!d; paint(); };
    paint();
    return b;
  };
  // a desktop icon (Program Manager / File Manager): the 32x32 icon, its title below in MS Sans Serif; selected:
  // the title on the selection colour; focused: the dotted rectangle round the title
  UI.icon = function (label, o) {
    o = o || {};
    var b = document.createElement('button'); b.type = 'button'; b.className = 'b16icon'; b.setAttribute('role', 'option');
    b.setAttribute('aria-label', o.aria || label);
    var cv = document.createElement('canvas'); b.appendChild(cv);
    var st = { selected: false, focused: false };
    var W = Math.max(64, UI.measure(label, 'sans') + 8), H = 52;
    function paint() {
      UI.canvas(cv, W, H, function (ctx) {
        ctx.fillStyle = C.win; ctx.fillRect(0, 0, W, H);
        UI.sprite(ctx, o.sprite || 'icon', (W - 32) >> 1, 1);
        var tw = UI.measure(label, 'sans'), th = UI.fontHeight('sans'), tx = (W - tw) >> 1, ty = 35;
        if (st.selected) { ctx.fillStyle = C.sel; ctx.fillRect(tx - 1, ty, tw + 2, th); }
        ctx.save(); ctx.beginPath(); ctx.rect(2, ty, W - 4, th); ctx.clip();
        UI.text(ctx, label, tx, ty, 'sans', st.selected ? C.selInk : C.ink); ctx.restore();
        if (st.focused) UI.focusRect(ctx, tx - 2, ty - 1, tw + 4, th + 2);
      });
    }
    b.addEventListener('focus', function () { st.focused = true; paint(); });
    b.addEventListener('blur', function () { st.focused = false; paint(); });
    b.setSelected = function (s) { st.selected = !!s; b.setAttribute('aria-selected', String(!!s)); paint(); };
    b.repaint = paint;
    paint();
    return b;
  };
  // a line of bitmap text as an element (status lines, labels)
  UI.label = function (text, o) {
    o = o || {};
    var cv = document.createElement('canvas'); cv.className = 'b16label'; cv.setAttribute('role', 'status');
    cv.set = function (t, color) {
      text = t; cv.setAttribute('aria-label', t);
      var W = Math.max(1, Math.min(o.max || 600, UI.measure(t, o.font || 'sans'))), H = UI.fontHeight(o.font || 'sans');
      UI.canvas(cv, W, H, function (ctx) { if (o.bg) { ctx.fillStyle = o.bg; ctx.fillRect(0, 0, W, H); } UI.text(ctx, t, 0, 0, o.font || 'sans', color || o.color || C.ink); });
    };
    cv.set(text || '');
    return cv;
  };
  // a 3.1 dialog (frame, title bar, a prompt, an edit field, OK and Cancel) over `host`; resolves the text or null.
  // The edit field is a real <input> (typing, selection, IME), drawn in the bitmap font on a canvas over it.
  UI.dialog = function (host, o) {
    return new Promise(function (resolve) {
      var wrap = document.createElement('div'); wrap.className = 'b16dlg'; wrap.setAttribute('role', 'dialog'); wrap.setAttribute('aria-label', o.title);
      var W = 248, H = o.edit === false ? 92 : 112, TH = 18;
      var frame = document.createElement('canvas'); frame.className = 'b16dlgframe';
      wrap.appendChild(frame);
      var inp = null, field = null, val = o.value || '', caretOn = true;
      function paintFrame() {
        UI.canvas(frame, W, H, function (ctx) {
          // 3.1 dialog frame: black outline, a thick border in the face colour, the title bar
          ctx.fillStyle = C.ink; ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = C.face; ctx.fillRect(1, 1, W - 2, H - 2);
          ctx.fillStyle = C.hi; ctx.fillRect(1, 1, W - 3, 1); ctx.fillRect(1, 1, 1, H - 3);
          ctx.fillStyle = C.lo; ctx.fillRect(1, H - 2, W - 2, 1); ctx.fillRect(W - 2, 1, 1, H - 2);
          ctx.fillStyle = C.ink; ctx.fillRect(4, 4, W - 8, 1); ctx.fillRect(4, 4, 1, H - 8); ctx.fillRect(W - 5, 4, 1, H - 8); ctx.fillRect(4, H - 5, W - 8, 1);
          ctx.fillStyle = C.title; ctx.fillRect(5, 5, W - 10, TH);
          ctx.fillStyle = C.ink; ctx.fillRect(5, 5 + TH, W - 10, 1);
          var tw = UI.measure(o.title, 'system'); UI.text(ctx, o.title, (W - tw) >> 1, 6, 'system', C.selInk);
          ctx.fillStyle = C.face; ctx.fillRect(5, 6 + TH, W - 10, H - 11 - TH);
          UI.text(ctx, o.prompt || '', 14, 6 + TH + 8, 'sans', C.ink);
          if (o.edit !== false) {
            // the edit field: sunken, white
            var fx = 14, fy = 6 + TH + 26, fw = W - 28, fh = 18;
            ctx.fillStyle = C.lo; ctx.fillRect(fx, fy, fw, 1); ctx.fillRect(fx, fy, 1, fh);
            ctx.fillStyle = C.ink; ctx.fillRect(fx + 1, fy + 1, fw - 2, 1); ctx.fillRect(fx + 1, fy + 1, 1, fh - 2);
            ctx.fillStyle = C.hi; ctx.fillRect(fx, fy + fh - 1, fw, 1); ctx.fillRect(fx + fw - 1, fy, 1, fh);
            ctx.fillStyle = C.win; ctx.fillRect(fx + 2, fy + 2, fw - 3, fh - 3);
            var s0 = inp ? inp.selectionStart : val.length, s1 = inp ? inp.selectionEnd : val.length;
            var tx = fx + 4, ty = fy + 3, a = UI.measure(val.slice(0, s0), 'sans'), bsel = UI.measure(val.slice(0, s1), 'sans');
            if (s1 > s0) { ctx.fillStyle = C.sel; ctx.fillRect(tx + a, ty, bsel - a, UI.fontHeight('sans')); }
            UI.text(ctx, val.slice(0, s0), tx, ty, 'sans', C.ink);
            UI.text(ctx, val.slice(s0, s1), tx + a, ty, 'sans', C.selInk);
            UI.text(ctx, val.slice(s1), tx + bsel, ty, 'sans', C.ink);
            if (caretOn && s1 === s0 && document.activeElement === inp) { ctx.fillStyle = C.ink; ctx.fillRect(tx + a, ty, 1, UI.fontHeight('sans')); }
          }
        });
      }
      if (o.edit !== false) {
        inp = document.createElement('input'); inp.className = 'b16dlginput'; inp.value = val; inp.maxLength = o.maxLength || 8;
        inp.setAttribute('aria-label', o.prompt || o.title); inp.autocomplete = 'off'; inp.spellcheck = false;
        ['input', 'keyup', 'select', 'click', 'focus', 'blur'].forEach(function (e) { inp.addEventListener(e, function () {
          if (o.filter) { var f = o.filter(inp.value); if (f !== inp.value) { var p = inp.selectionStart; inp.value = f; inp.setSelectionRange(p, p); } }
          val = inp.value; caretOn = true; paintFrame(); }); });
        wrap.appendChild(inp);
      }
      var btns = document.createElement('div'); btns.className = 'b16dlgbtns';
      var ok = UI.button(o.ok || 'OK', { isDefault: true, width: 72 }), cancel = UI.button('Cancel', { width: 72 });
      btns.appendChild(ok); btns.appendChild(cancel); wrap.appendChild(btns);
      host.appendChild(wrap);
      var k = UI.k(), dpr = window.devicePixelRatio || 1, u = k / dpr;
      // centred over the screen, on whole device pixels
      wrap.style.left = (Math.round((host.clientWidth - W * u) / 2 * dpr) / dpr) + 'px';
      wrap.style.top = (Math.round(Math.max(0, (host.clientHeight - H * u) / 2) * dpr) / dpr) + 'px';
      // the field and the buttons at their places in the frame (native pixels x k / dpr)
      if (inp) { inp.style.left = (14 * u) + 'px'; inp.style.top = ((6 + TH + 26) * u) + 'px'; inp.style.width = ((W - 28) * u) + 'px'; inp.style.height = (18 * u) + 'px'; }
      btns.style.left = ((W - 72 * 2 - 10) / 2 * u) + 'px'; btns.style.top = ((H - 33) * u) + 'px'; btns.style.gap = (10 * u) + 'px';
      paintFrame();
      var blink = setInterval(function () { caretOn = !caretOn; paintFrame(); }, 530);
      function done(v) { clearInterval(blink); wrap.remove(); resolve(v); }
      ok.addEventListener('click', function () { done(inp ? inp.value : true); });
      cancel.addEventListener('click', function () { done(null); });
      wrap.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { e.preventDefault(); done(null); }
        else if (e.key === 'Enter' && e.target !== cancel) { e.preventDefault(); done(inp ? inp.value : true); }
        e.stopPropagation();
      });
      setTimeout(function () { (inp || ok).focus(); if (inp) inp.select(); }, 0);
    });
  };
  // a 3.1 message box over `host` (one OK): for "not a state file" and the like
  UI.message = function (host, title, text) { return UI.dialog(host, { title: title, prompt: text, edit: false }); };
})();
