// (--post-js: runs in the worker and in every engine thread.) The JS side of fs.cpp's library disc.
// WasmFS asks wasmFS$backends[id] for a JS-implemented file's size and data; ours is the only such backend, and
// its pieces come from b16_lazy_chunk (kept in shared memory). A missing piece is fetched with a synchronous
// ranged request on the worker's own thread: an engine thread asks for it over a BroadcastChannel, and waits.
var b16LazyChannel = null;
function b16LazyXhr(dst, a, e) {
  let url = '', p = _b16_lazy_url();
  while (HEAPU8[p]) url += String.fromCharCode(HEAPU8[p++]);
  for (let tries = 0; tries < 3; tries++) {
    try {
      const x = new XMLHttpRequest();
      x.open('GET', url, false);
      x.responseType = 'arraybuffer';
      x.setRequestHeader('Range', 'bytes=' + a + '-' + e);
      x.send(null);
      if (x.status !== 206 && x.status !== 200) continue;
      let d = new Uint8Array(x.response);
      if (x.status === 200) d = d.subarray(a, e + 1);   // (no ranges: the whole file came)
      HEAPU8.set(d, dst);
      return d.length;
    } catch (err) {}
  }
  return -1;
}
function b16LazyListen() {
  const token = (Math.random() * 4294967295) >>> 0 || 1;
  b16LazyChannel = new BroadcastChannel('b16lazy-' + token);
  b16LazyChannel.onmessage = ev => {
    const m = ev.data, f = new Int32Array(wasmMemory.buffer);
    Atomics.add(HEAPU32, (_b16_lazy_vars() >> 2) + 6, 1);
    const n = b16LazyXhr(m.dst, m.a, m.e);
    Atomics.store(f, (m.flag >> 2) + 1, n); Atomics.store(f, m.flag >> 2, 1); Atomics.notify(f, m.flag >> 2);
  };
  return token;
}
function b16LazyFetch(dst, a, e, flag) {
  if (b16LazyChannel) return b16LazyXhr(dst, a, e);   // the worker's own thread
  const f = new Int32Array(wasmMemory.buffer), token = HEAPU32[(_b16_lazy_vars() >> 2) + 4];
  Atomics.store(f, flag >> 2, 0);
  const ch = new BroadcastChannel('b16lazy-' + token);
  Atomics.add(HEAPU32, (_b16_lazy_vars() >> 2) + 5, 1);
  ch.postMessage({ dst, a, e, flag });
  ch.close();
  while (Atomics.load(f, flag >> 2) === 0) Atomics.wait(f, flag >> 2, 0, 30000);
  return Atomics.load(f, (flag >> 2) + 1);
}
(function () {
  if (typeof wasmFS$backends === 'undefined') return;
  const V = () => _b16_lazy_vars() >> 2;   // [size, chunk, pieces fetched, bytes fetched, token]
  const impl = {
    allocFile() {}, freeFile() {},
    getSize() { return HEAPU32[V()]; },
    write() { return -1; },
    read(file, buffer, length, offset) {
      const size = HEAPU32[V()], csz = HEAPU32[V() + 1];
      if (offset >= size) return 0;
      length = Math.min(length, size - offset);
      const lenp = _malloc(4);
      let done = 0;
      while (done < length) {
        const at = offset + done, i = Math.floor(at / csz), o = at - i * csz;
        const p = _b16_lazy_chunk(i, lenp);
        if (!p) break;
        const n = Math.min(length - done, HEAPU32[lenp >> 2] - o);
        if (n <= 0) break;
        HEAPU8.copyWithin(buffer + done, p + o, p + o + n);
        done += n;
      }
      _free(lenp);
      return done || (length ? -5 : 0);
    }
  };
  const real = wasmFS$backends;
  wasmFS$backends = new Proxy(real, { get: (t, k) => t[k] || impl });
})();
