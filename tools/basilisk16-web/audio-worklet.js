// BASILISK 16 in the browser: the audio. It plays the BSYN card's DAC ring (48 kHz stereo float) straight out of
// the machine's shared memory (no messages per block), resampled to the AudioContext's rate with the plugin's
// 4-point Hermite, and writes back how far it has played (host_r) and a beat, which is what paces the emulator (as a
// DAW's audio thread does).
//
// When the ring runs dry (the emulator fell behind) it does not skip ahead: it holds its place, fades out over a
// few milliseconds instead of dropping to zero, and fades back in when the samples arrive. Each such gap raises the
// emulator's lead (how far ahead of the play position it keeps the ring filled), up to a hard cap.
const FADE = 96;   // frames of fade out / in at a gap (2 ms)
class B16Out extends AudioWorkletProcessor {
  constructor() {
    super();
    this.pos = -1; this.ratio = 48000 / sampleRate; this.under = 0; this.blocks = 0; this.lastReport = 0;
    this.gaps = 0; this.short = 0; this.starved = false; this.fade = 1; this.lastL = 0; this.lastR = 0; this.raised = 0;
    this.port.onmessage = e => {
      const m = e.data;
      if (m.t === 'mem') {
        const b = m.base, L = m.lay;
        this.u32 = new Uint32Array(m.buffer); this.f32 = new Float32Array(m.buffer); this.i32 = new Int32Array(m.buffer);
        this.dacLo = (b + L.dac_w) >> 2; this.hrLo = (b + L.host_r) >> 2; this.beat = (b + L.host_beat) >> 2;
        this.rt = (b + L.realtime) >> 2; this.ring = (b + L.ring) >> 2; this.len = L.ring_len; this.gain = L.gain >> 2;
        this.leadIdx = L.lead !== undefined ? (b + L.lead) >> 2 : -1;
        this.lead = this.lead0 = m.lead || 2048; this.leadMax = m.leadMax || 3584; this.pos = -1;
        if (this.leadIdx >= 0) this.u32[this.leadIdx] = this.lead;
      } else if (m.t === 'tap') this.tap = m.on ? [] : null;   // tests: capture the output
    };
  }
  process(inputs, outputs) {
    const out = outputs[0], L = out[0], R = out[1] || out[0], n = L.length;
    if (!this.u32) { L.fill(0); if (R !== L) R.fill(0); return true; }
    const u = this.u32, f = this.f32, ring = this.ring, len = this.len;
    const dac = u[this.dacLo] + u[this.dacLo + 1] * 4294967296;
    // start (or jump, after a pause or a long stall) a little behind the newest sample
    if (this.pos < 0 || dac - this.pos > this.lead + 24000) { this.pos = Math.max(2, dac - this.lead);   // (never below 2: the Hermite reads k-1)
      this.fade = 0; this.starved = true; }
    const g = f[this.gain] || 1;
    let missing = 0;
    for (let i = 0; i < n; i++) {
      const p = this.pos, k = Math.floor(p), fr = p - k;
      if (k + 2 >= dac) {   // dry: hold the place, fade the last sample out (held, it must still be able to move on:
                            // the emulator runs to host_r + lead, so a hold below `lead` would wait forever)
        if (!this.starved) { this.starved = true; this.gaps++; this.gapLen = 0; }
        this.gapLen++;
        missing++;
        this.fade = Math.max(0, this.fade - 1 / FADE);
        L[i] = this.lastL * this.fade; if (R !== L) R[i] = this.lastR * this.fade;
        continue;
      }
      if (this.starved && k + 2 + FADE < dac) {   // enough again: fade back in
        this.starved = false;
        // a short gap is jitter: keep more in hand from now on (a long one is a stall nothing in hand would cover)
        if (this.gapLen && this.gapLen < 2400 && this.leadIdx >= 0 && this.lead < this.leadMax) { this.lead = Math.min(this.leadMax, this.lead + 256); this.u32[this.leadIdx] = this.lead; }
        this.gapLen = 0;
      }
      if (!this.starved || this.fade < 1) this.fade = Math.min(1, this.fade + 1 / FADE);
      const j0 = ((k - 1) % len) * 2, j1 = (k % len) * 2, j2 = ((k + 1) % len) * 2, j3 = ((k + 2) % len) * 2;
      for (let c = 0; c < 2; c++) {
        const y0 = f[ring + j0 + c], y1 = f[ring + j1 + c], y2 = f[ring + j2 + c], y3 = f[ring + j3 + c];
        const c1 = 0.5 * (y2 - y0), c2 = y0 - 2.5 * y1 + 2 * y2 - 0.5 * y3, c3 = 0.5 * (y3 - y0) + 1.5 * (y1 - y2);
        const y = (((c3 * fr + c2) * fr + c1) * fr + y1) * g;
        if (c === 0) { this.lastL = y; L[i] = y * this.fade; } else { this.lastR = y; if (R !== L) R[i] = y * this.fade; }
      }
      if (R === L) this.lastR = this.lastL;
      this.pos = p + this.ratio;
    }
    const hr = Math.max(0, Math.floor(this.pos) - 4);
    u[this.hrLo] = hr % 4294967296; u[this.hrLo + 1] = Math.floor(hr / 4294967296);
    u[this.rt] = 1;
    Atomics.add(this.i32, this.beat, 1);
    // after 20 s without a gap, give some of the lead back (latency), never below where it started
    if (!missing && !this.starved) {
      if (currentTime - (this.lastGapT || 0) > 20 && this.leadIdx >= 0 && this.lead > this.lead0 && currentTime - (this.shrunk || 0) > 20) {
        this.lead = Math.max(this.lead0, this.lead - 256); this.u32[this.leadIdx] = this.lead; this.shrunk = currentTime;
      }
    } else this.lastGapT = currentTime;
    this.blocks++; this.short += missing;
    if (missing) this.under++;
    if (this.tap) { this.tap.push(new Float32Array(L), new Float32Array(R)); if (this.tap.length >= 64) { this.port.postMessage({ t: 'tap', d: this.tap }); this.tap = []; } }
    if (currentTime - this.lastReport > 0.5) {
      this.lastReport = currentTime;
      this.port.postMessage({ t: 'a', blocks: this.blocks, under: this.under, pos: this.pos, dac, gaps: this.gaps, short: this.short, lead: this.lead });
      this.blocks = 0; this.under = 0;
    }
    return true;
  }
}
registerProcessor('b16-out', B16Out);

// the microphone, for Sound Recorder's Record (the card's ADC): 48 kHz stereo blocks of 1024 frames to the page,
// which hands them to the emulator stamped on its DAC clock; and the input level for the meter
class B16Mic extends AudioWorkletProcessor {
  constructor() { super(); this.buf = new Float32Array(2048); this.n = 0; this.ratio = sampleRate / 48000; this.ph = 0; this.prev = 0; this.peak = 0; }
  process(inputs) {
    const inp = inputs[0], L = inp && inp[0];
    if (!L) return true;
    const R = inp[1] || L;
    for (let i = 0; i < L.length; i++) {
      const x = 0.5 * (L[i] + R[i]);
      this.peak = Math.max(this.peak, Math.abs(x));
      // to 48 kHz (linear between the input's samples; exact when the context runs at 48 kHz)
      while (this.ph < 1) {
        const y = this.prev + (x - this.prev) * this.ph;
        this.buf[this.n * 2] = y; this.buf[this.n * 2 + 1] = y; this.n++;
        if (this.n === 1024) { this.port.postMessage({ t: 'mic', d: this.buf, peak: this.peak }, [this.buf.buffer]); this.buf = new Float32Array(2048); this.n = 0; this.peak = 0; }
        this.ph += this.ratio;
      }
      this.ph -= 1; this.prev = x;
    }
    return true;
  }
}
registerProcessor('b16-mic', B16Mic);
