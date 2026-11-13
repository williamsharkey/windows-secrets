/* pxplayer: plays tools/sndrec-demo/pxv.py captures pixel for pixel on a <canvas>, following its audio track's clock.
   The capture: BASE.pxv (index), BASE-0.png ... (atlases of changed rectangles), BASE-poster.png, BASE.m4a (audio).
   Decoding copies rectangles 1:1 from the atlas PNGs with drawImage (no scaling, smoothing off) into an offscreen
   canvas of the native size, which then holds exactly the emulator's pixels (player.src); pxfit.js blits it onto the
   visible canvas at k x k device pixels per pixel, nearest-neighbour.
   Nothing is fetched but the poster until Play is pressed. Frame shown = floor(audio.currentTime x fps).

   new PxPlayer(root, clips): root holds .pxbox > canvas[data-px], .pxctl (play, time, seek, loop, clip buttons).
   clips: [{base, title, caption}]. */
(function () {
  'use strict';
  function el(t, c, h) { var e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; }
  function fmt(s) { s = Math.max(0, s); var m = Math.floor(s / 60), r = Math.floor(s % 60); return m + ':' + (r < 10 ? '0' : '') + r; }
  function loadImage(url) {
    // the PNGs have no colour chunks; ask for no conversion anyway where the browser lets us
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url); return r.blob(); }).then(function (b) {
      if (window.createImageBitmap) {
        return createImageBitmap(b, {colorSpaceConversion: 'none', premultiplyAlpha: 'none'}).catch(function () { return createImageBitmap(b); });
      }
      return new Promise(function (ok, bad) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = bad; i.src = URL.createObjectURL(b); });
    });
  }
  function parse(buf) {
    var d = new DataView(buf), o = 16;
    if (d.getUint32(0, false) !== 0x50585631) throw new Error('not a PXV1 file');
    var v = {w: d.getUint16(4, true), h: d.getUint16(6, true), fps: d.getUint16(8, true), atlases: d.getUint16(10, true), n: d.getUint32(12, true), frames: []};
    for (var f = 0; f < v.n; f++) {
      var k = d.getUint16(o, true); o += 2;
      v.frames.push(new Uint16Array(buf.slice(o, o + k * 14)));   // 7 u16 per rectangle (little-endian hosts)
      o += k * 14;
    }
    return v;
  }
  var LE = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;

  function PxPlayer(root, clips) {
    var self = this;
    this.root = root; this.clips = clips; this.canvas = root.querySelector('canvas');
    this.src = document.createElement('canvas');
    var nat = (this.canvas.getAttribute('data-px') || '1024x768').split('x');   // native size (the canvas itself is in device pixels)
    this.src.width = +nat[0]; this.src.height = +nat[1];
    this.ctx = this.src.getContext('2d', {alpha: false});
    this.ctx.imageSmoothingEnabled = false;
    this.canvas.pxSource = this.src;
    this.audio = new Audio(); this.audio.preload = 'none';
    var ctl = root.querySelector('.pxctl');
    this.btn = ctl.querySelector('.pxplay'); this.seek = ctl.querySelector('.pxseek'); this.time = ctl.querySelector('.pxtime');
    this.loop = ctl.querySelector('.pxloop input'); this.status = root.querySelector('.pxstatus');
    this.cap = root.querySelector('.pxcap');
    this.btn.addEventListener('click', function () { self.toggle(); });
    root.querySelector('.pxbig').addEventListener('click', function () { self.toggle(); });
    this.seek.addEventListener('input', function () { self.seekTo(+self.seek.value); });
    this.loop.addEventListener('change', function () { self.audio.loop = self.loop.checked; });
    this.audio.addEventListener('ended', function () { self.setPlaying(false); });
    this.audio.addEventListener('pause', function () { self.setPlaying(false); });
    this.audio.addEventListener('play', function () { self.setPlaying(true); });
    [].forEach.call(root.querySelectorAll('.pxclip'), function (b, i) { b.addEventListener('click', function () { self.select(i); }); });
    this.canvas.addEventListener('keydown', function (e) { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); self.toggle(); } });
    PxPlayer.all.push(this);
    this.select(0, true);
  }
  PxPlayer.all = [];
  PxPlayer.pauseAll = function (except) { PxPlayer.all.forEach(function (p) { if (p !== except) p.pause(); }); };
  PxPlayer.prototype.select = function (i, first) {
    var self = this, c = this.clips[i];
    this.pause(); this.ci = i; this.v = null; this.loading = null; this.cur = -1;
    [].forEach.call(this.root.querySelectorAll('.pxclip'), function (b, j) { b.setAttribute('aria-pressed', String(j === i)); });
    if (this.cap) this.cap.innerHTML = c.caption;
    this.canvas.setAttribute('aria-label', c.title);
    this.audio.removeAttribute('src'); this.audio.load();
    this.seek.value = 0; this.seek.max = c.seconds || 1; this.time.textContent = '0:00 / ' + fmt(c.seconds || 0);
    this.root.classList.remove('pxloaded');
    loadImage(c.base + '-poster.png').then(function (im) {
      if (self.ci !== i || self.cur >= 0) return;
      self.ctx.drawImage(im, 0, 0); self.show();
    }).catch(function () {});
    if (!first) this.canvas.focus({preventScroll: true});
  };
  PxPlayer.prototype.ensure = function () {
    var self = this, c = this.clips[this.ci], i = this.ci;
    if (this.v) return Promise.resolve(this.v);
    if (this.loading) return this.loading;
    this.say('Loading...');
    this.loading = fetch(c.base + '.pxv').then(function (r) { if (!r.ok) throw new Error('index'); return r.arrayBuffer(); }).then(function (buf) {
      var v = parse(buf);
      if (!LE) throw new Error('big-endian host');
      var ps = []; for (var a = 0; a < v.atlases; a++) ps.push(loadImage(c.base + '-' + a + '.png'));
      return Promise.all(ps).then(function (ims) { v.ims = ims; return v; });
    }).then(function (v) {
      if (self.ci !== i) return null;
      self.v = v; self.audio.src = c.base + '.m4a'; self.audio.loop = self.loop.checked;
      self.seek.max = v.n / v.fps; self.say('');
      self.root.classList.add('pxloaded');
      return v;
    }).catch(function (e) { self.say('Could not load this capture (' + e.message + ').'); self.loading = null; throw e; });
    return this.loading;
  };
  PxPlayer.prototype.show = function () { if (window.pxfit) pxfit.draw(this.canvas); };
  PxPlayer.prototype.say = function (t) { if (this.status) { this.status.textContent = t; this.status.hidden = !t; } };
  PxPlayer.prototype.draw = function (f) {   // bring the canvas to frame f (replaying from frame 0 when going back)
    var v = this.v, ctx = this.ctx;
    if (!v) return;
    f = Math.max(0, Math.min(v.n - 1, f));
    if (f < this.cur) this.cur = -1;
    var drew = this.cur < f;
    for (var n = this.cur + 1; n <= f; n++) {
      var r = v.frames[n];
      for (var j = 0; j < r.length; j += 7) ctx.drawImage(v.ims[r[j + 4]], r[j + 5], r[j + 6], r[j + 2], r[j + 3], r[j], r[j + 1], r[j + 2], r[j + 3]);
    }
    this.cur = f;
    if (drew) this.show();
  };
  PxPlayer.prototype.tick = function () {
    var self = this;
    if (!this.playing || !this.v) return;
    var t = this.audio.currentTime;
    this.draw(Math.floor(t * this.v.fps + 1e-6));
    this.seek.value = t; this.time.textContent = fmt(t) + ' / ' + fmt(this.v.n / this.v.fps);
    requestAnimationFrame(function () { self.tick(); });
  };
  PxPlayer.prototype.setPlaying = function (on) {
    this.playing = on;
    this.btn.textContent = on ? 'Pause' : 'Play'; this.btn.setAttribute('aria-pressed', String(on));
    this.root.classList.toggle('pxon', on);
    if (on) this.tick();
  };
  PxPlayer.prototype.toggle = function () { if (this.playing) this.pause(); else this.play(); };
  PxPlayer.prototype.play = function () {
    var self = this;
    PxPlayer.pauseAll(this);
    if (window.onPxPlay) window.onPxPlay(this);
    this.ensure().then(function (v) {
      if (!v) return;
      if (self.audio.ended || self.cur >= v.n - 1) { self.audio.currentTime = 0; }
      var p = self.audio.play(); if (p && p.catch) p.catch(function () {});
    }).catch(function () {});
  };
  PxPlayer.prototype.pause = function () { if (!this.audio.paused) this.audio.pause(); this.playing = false; this.root.classList.remove('pxon'); if (this.btn) { this.btn.textContent = 'Play'; this.btn.setAttribute('aria-pressed', 'false'); } };
  PxPlayer.prototype.seekTo = function (t) {
    var self = this;
    this.ensure().then(function (v) {
      if (!v) return;
      self.audio.currentTime = t; self.draw(Math.floor(t * v.fps + 1e-6));
      self.time.textContent = fmt(t) + ' / ' + fmt(v.n / v.fps);
    }).catch(function () {});
  };
  window.PxPlayer = PxPlayer;
})();
