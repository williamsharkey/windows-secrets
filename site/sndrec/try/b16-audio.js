// BASILISK 16 in the browser: the audio. It plays the BSYN card's DAC ring (48 kHz stereo float) straight out of
// the machine's shared memory, resampled to the AudioContext's rate with the plugin's 4-point Hermite, and writes
// back how far it has played (host_r) and a beat, which is what paces the emulator (as a DAW's audio thread does).
class B16Out extends AudioWorkletProcessor {
  constructor() {
    super();
    this.pos = -1; this.ratio = 48000 / sampleRate; this.under = 0; this.blocks = 0; this.lastReport = 0; this.gainNow = 1;
    this.port.onmessage = e => {
      const m = e.data;
      if (m.t === 'mem') {
        const b = m.base, L = m.lay;
        this.u32 = new Uint32Array(m.buffer); this.f32 = new Float32Array(m.buffer); this.i32 = new Int32Array(m.buffer);
        this.dacLo = (b + L.dac_w) >> 2; this.hrLo = (b + L.host_r) >> 2; this.beat = (b + L.host_beat) >> 2;
        this.rt = (b + L.realtime) >> 2; this.ring = (b + L.ring) >> 2; this.len = L.ring_len; this.gain = L.gain >> 2;
        this.lead = m.lead || 2048; this.pos = -1;
      } else if (m.t === 'tap') this.tap = m.on ? [] : null;   // tests: capture the output
    };
  }
  process(inputs, outputs) {
    const out = outputs[0], L = out[0], R = out[1] || out[0], n = L.length;
    if (!this.u32) { L.fill(0); if (R !== L) R.fill(0); return true; }
    const u = this.u32, f = this.f32, ring = this.ring, len = this.len;
    const dac = u[this.dacLo] + u[this.dacLo + 1] * 4294967296;
    // start (or jump, after a pause or a stall) a little behind the newest sample
    if (this.pos < 0 || dac - this.pos > this.lead + 24000) this.pos = Math.max(0, dac - this.lead);
    const g = f[this.gain] || 1;
    let missing = 0;
    for (let i = 0; i < n; i++) {
      const p = this.pos, k = Math.floor(p), fr = p - k;
      if (k + 2 >= dac || k < 1) { L[i] = 0; if (R !== L) R[i] = 0; missing++; }
      else {
        const j0 = ((k - 1) % len) * 2, j1 = (k % len) * 2, j2 = ((k + 1) % len) * 2, j3 = ((k + 2) % len) * 2;
        for (let c = 0; c < 2; c++) {
          const y0 = f[ring + j0 + c], y1 = f[ring + j1 + c], y2 = f[ring + j2 + c], y3 = f[ring + j3 + c];
          const c1 = 0.5 * (y2 - y0), c2 = y0 - 2.5 * y1 + 2 * y2 - 0.5 * y3, c3 = 0.5 * (y3 - y0) + 1.5 * (y1 - y2);
          const y = (((c3 * fr + c2) * fr + c1) * fr + y1) * g;
          if (c === 0) L[i] = y; else if (R !== L) R[i] = y;
        }
      }
      this.pos = p + this.ratio;
    }
    const hr = Math.max(0, Math.floor(this.pos) - 4);
    u[this.hrLo] = hr % 4294967296; u[this.hrLo + 1] = Math.floor(hr / 4294967296);
    u[this.rt] = 1;
    Atomics.add(this.i32, this.beat, 1);
    this.blocks++;
    if (missing) this.under++;
    if (this.tap) { this.tap.push(new Float32Array(L), new Float32Array(R)); if (this.tap.length >= 64) { this.port.postMessage({ t: 'tap', d: this.tap }); this.tap = []; } }
    if (currentTime - this.lastReport > 0.5) {
      this.lastReport = currentTime;
      this.port.postMessage({ t: 'a', blocks: this.blocks, under: this.under, pos: this.pos, dac });
      this.blocks = 0; this.under = 0;
    }
    return true;
  }
}
registerProcessor('b16-out', B16Out);
