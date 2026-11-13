/* pxfit: show Windows screenshots and screen captures with every Windows pixel as exactly k x k device pixels.

   Every element with data-px="WIDTHxHEIGHT" is a <canvas> whose backing store is in device pixels:
     k = floor(available CSS width x devicePixelRatio / native width)
     k >= 1: the source is drawn at k x its size with nearest-neighbour scaling (exact for an integer k);
     k < 1:  the largest reduction 1/n that fits (nearest pixel), and the element's data-px-note says so.
   The canvas's CSS size is its backing size / devicePixelRatio, so the browser maps it 1:1 onto the screen. Layout
   works in 1/64 CSS px, so some device sizes have no exact CSS size (at 3x, only multiples of 3 device px do): the
   backing store is then padded by a pixel or two on the right and bottom (filled with the box's background) to the
   next size that has one. Its position is set the same way: left and top margins, in 1/64 px steps, put both edges
   on whole device pixels (a canvas at x = 49.5 device px would be resampled). Nothing is ever resampled.
   An <img data-px> is replaced by such a canvas (role="img", its alt as the label). A canvas gets its picture from
   el.pxSource (an image or a native-size canvas); call pxfit.draw(el) after changing it.
   Recomputed on resize, zoom and devicePixelRatio changes. */
(function () {
  'use strict';
  function exactSize(dev, dpr) {   // smallest device size >= dev whose CSS size is a whole number of 1/64 px
    for (var p = dev; p < dev + 64; p++) { var c = p / dpr * 64; if (Math.abs(c - Math.round(c)) < 1e-6) return p; }
    return dev;
  }
  function draw(el) {
    var src = el.pxSource, s = el._pxs;
    if (!s) return;
    var ctx = el.getContext('2d', {alpha: false});
    if (el.width !== s.P || el.height !== s.Q) { el.width = s.P; el.height = s.Q; }
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = s.bg; ctx.fillRect(0, 0, s.P, s.Q);
    if (src && (src.naturalWidth || src.width)) ctx.drawImage(src, 0, 0, s.nw, s.nh, 0, 0, s.dw, s.dh);
  }
  function fit(el) {
    var m = /^(\d+)x(\d+)$/.exec(el.getAttribute('data-px') || ''); if (!m) return;
    if (el.tagName === 'IMG') el = fromImg(el);
    var nw = +m[1], nh = +m[2], dpr = window.devicePixelRatio || 1;
    var box = el.parentNode, cs = getComputedStyle(box);
    var avail = box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    var k = Math.floor(avail * dpr / nw + 1e-6), dw, dh, note = '', scale;
    if (k >= 1) { dw = nw * k; dh = nh * k; scale = String(k); }
    else {
      var n = 2; while (Math.floor(nw / n) > avail * dpr) n++;
      dw = Math.floor(nw / n); dh = Math.floor(nh / n); scale = '1/' + n;
      note = 'Shown at 1/' + n + ' size to fit this screen; widen the window to see every pixel.';
    }
    var P = exactSize(dw, dpr), Q = exactSize(dh, dpr);
    var bg = 'rgb(255, 255, 255)';   // padding pixels: the first background behind the picture
    for (var a = box; a && a.nodeType === 1; a = a.parentNode) { var c = getComputedStyle(a).backgroundColor; if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') { bg = c; break; } }
    el._pxs = {nw: nw, nh: nh, dw: dw, dh: dh, P: P, Q: Q, k: k, bg: bg};
    el.style.width = (P / dpr) + 'px'; el.style.height = (Q / dpr) + 'px';
    el.setAttribute('data-px-scale', scale);
    place(el, box, cs, dpr, avail * dpr, P);
    draw(el);
    var nid = el.getAttribute('data-px-note'), ne = nid && document.getElementById(nid);
    if (ne) { ne.textContent = note; ne.hidden = !note; }
  }
  function frac(x) { return Math.abs(x - Math.round(x)); }
  function place(el, box, cs, dpr, availDev, P) {   // centre it, with its left and top edges on whole device pixels
    el.style.marginLeft = '0px'; el.style.marginTop = '0px';
    var r = el.getBoundingClientRect(), x0 = r.left * dpr, y0 = (r.top + window.scrollY) * dpr;
    var want = Math.max(0, (availDev - P) / 2), best = 0, bm = 1e9;
    for (var m = Math.max(0, Math.floor(want * 64 / dpr) - 256); m <= Math.floor(want * 64 / dpr) + 256; m++) {   // a whole device pixel recurs within 256 layout units
      var o = m * dpr / 64, e = frac(x0 + o) * 1000 + Math.abs(o - want);
      if (frac(x0 + o) < 1e-3 && e < bm) { bm = e; best = m; }
    }
    var mt = 0;
    for (var n = 0; n < 64 * 4; n++) { if (frac(y0 + n * dpr / 64) < 1e-3) { mt = n; break; } }
    el.style.marginLeft = (best / 64) + 'px'; el.style.marginTop = (mt / 64) + 'px';
  }
  function fromImg(img) {   // an exact canvas in place of the <img>; the image loads when it nears the screen
    var c = document.createElement('canvas');
    ['data-px', 'data-px-note', 'id'].forEach(function (a) { if (img.getAttribute(a)) c.setAttribute(a, img.getAttribute(a)); });
    c.setAttribute('role', 'img'); c.setAttribute('aria-label', img.alt || '');
    c.pxSrc = img.getAttribute('src');
    img.parentNode.replaceChild(c, img);
    load(c);
    return c;
  }
  var io = window.IntersectionObserver ? new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { io.unobserve(e.target); start(e.target); } });
  }, {rootMargin: '400px'}) : null;
  function load(c) { if (io) io.observe(c); else start(c); }
  function start(c) {
    var url = c.pxSrc; if (!url) return;
    var im = new Image();
    im.onload = function () { if (c.pxSrc === url) { c.pxSource = im; draw(c); } };
    im.src = url;
  }
  function setImage(c, url, size, label) {   // show another picture in an exact canvas (the help gallery)
    c.setAttribute('data-px', size); c.setAttribute('aria-label', label || '');
    c.pxSrc = url; c.pxSource = null; fit(c); start(c);
  }
  function all() { [].forEach.call(document.querySelectorAll('[data-px]'), fit); }
  var t = 0;
  function soon() { cancelAnimationFrame(t); t = requestAnimationFrame(all); }
  window.addEventListener('resize', soon);
  var mq;
  function watchDpr() {   // fires when the window moves to another screen, or on zoom
    if (mq && mq.removeEventListener) mq.removeEventListener('change', onDpr);
    mq = window.matchMedia('(resolution: ' + (window.devicePixelRatio || 1) + 'dppx)');
    if (mq.addEventListener) mq.addEventListener('change', onDpr); else if (mq.addListener) mq.addListener(onDpr);
  }
  function onDpr() { watchDpr(); soon(); }
  watchDpr();
  // anything above changing height moves the pictures: place them again (size only changes with width)
  if (window.ResizeObserver) new ResizeObserver(soon).observe(document.body || document.documentElement);
  window.pxfit = {all: all, fit: fit, draw: draw, setImage: setImage};
  if (document.readyState !== 'loading') all(); else document.addEventListener('DOMContentLoaded', all);
})();
