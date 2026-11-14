#!/usr/bin/env python3
"""Synthesized source sounds for the `electromech` library category (BASILISK SYNTH / BASILISK 16).

The plugin never synthesizes a note: Sound Recorder plays every sound. So the synthesis happens here, offline,
and the results are library *sources* like any recording. Everything is deterministic: each sound has its own
seed (crc32 of its id), and the same numpy version gives the same bytes.

  python3 -I synth_sources.py [--only ID[,ID...]] [--list]

Writes  library/sources-raw/electromech/synth/<id>.wav   (PCM 16-bit, 44100 Hz mono; build_library.py then
        converts it like every other raw file: 22050 Hz, trimmed, normalized)
and merges one catalog entry per sound into library/catalog/electromech.json with "origin": "synth"
(hybrids: "origin": "synth+recording", plus "parents"). Entries for recordings are left alone.

Methods (see research/electromech.md, section "Synthesized sources"):
  solenoid  - mass/spring/bounce plunger model: magnetic pull ~ 1/(gap)^2 with coil rise/decay, preloaded return
              spring, restitution at both stops; every impact excites a modal bank (front stop, back stop, frame)
  modal     - sums of exponentially decaying partials (bars, bells, frames), struck by band-limited clicks
  ks        - Karplus-Strong (block-vectorized delay line with a two-point average and loss)
  fm        - two-operator FM with a decaying index
  additive  - harmonic / inharmonic partial stacks (motor and drum whines)
  noise     - shaped noise bursts (paper, air, brushes), FFT-domain filters
  fsk       - phase-continuous FSK (Bell 103, Bell 202, 45.45-baud RTTY with ITA2 framing), call-progress tones
  line      - mains hum, crackle, band-limited hiss, dropouts, crosstalk murmur
  ringmod / bitcrush - ring modulation and sample-and-hold + bit reduction
  phrase    - event sequences built from the models (message received, stored, displayed)
  hybrid    - a recording from sources/electromech plus a synthesized layer
"""
import argparse, json, os, sys, wave, zlib
import numpy as np

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.dirname(HERE)
RAWDIR = os.path.join(LIB, "sources-raw", "electromech", "synth")
CONV = os.path.join(LIB, "sources", "electromech")
CATALOG = os.path.join(LIB, "catalog", "electromech.json")
TOOL_URL = "packages/basilisk-synth/library/tools/synth_sources.py"
REG = []


def sound(id, desc, method, tonal=False, root=None, kind="oneshot", parents=None, tags=()):
    def deco(fn):
        REG.append(dict(id=id, fn=fn, desc=desc, method=method, tonal=tonal, root=root, kind=kind,
                        parents=parents or [], tags=list(tags)))
        return fn
    return deco


# ----------------------------------------------------------------------------------------------- primitives
def N(d):
    return int(round(d * SR))


def tt(d):
    return np.arange(N(d)) / SR


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def place(buf, x, t0, g=1.0):
    i = N(t0)
    if i < 0:
        x, i = x[-i:], 0
    if i >= len(buf):
        return buf
    n = min(len(x), len(buf) - i)
    buf[i:i + n] += g * x[:n]
    return buf


def specf(x, lo=None, hi=None, peaks=(), tilt=0.0, order=4):
    """Zero-phase FFT-domain filter: high-pass lo, low-pass hi (Butterworth-like magnitude), resonant peaks
    (f, bandwidth Hz, gain), spectral tilt in dB/octave around 1 kHz."""
    n = len(x)
    if n == 0:
        return x
    m = 1 << int(np.ceil(np.log2(n + 1)))
    X = np.fft.rfft(x, m)
    f = np.fft.rfftfreq(m, 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** (2 * order))
    if hi:
        g *= 1 / np.sqrt(1 + (f / hi) ** (2 * order))
    for (pf, bw, pg) in peaks:
        g *= 1 + (pg - 1) / (1 + ((f - pf) / (bw / 2)) ** 2)
    if tilt:
        g *= (np.maximum(f, 20) / 1000.0) ** (tilt / 6.02)
    return np.fft.irfft(X * g, m)[:n]


def expenv(n, t60):
    return 10 ** (-3 * np.arange(n) / SR / max(t60, 1e-4))


def adsr(n, a, r, hold=None):
    e = np.ones(n)
    na, nr = min(n, N(a)), min(n, N(r))
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def modes(freqs, t60s, amps, dur, rng, bright=1.0):
    """Impulse response of a bank of decaying partials. bright<1 damps the upper partials (soft strike)."""
    t = tt(dur)
    y = np.zeros(len(t))
    f0 = min(freqs)
    for f, d, a in zip(freqs, t60s, amps):
        if f >= SR / 2 * 0.95:
            continue
        w = a * bright ** np.log2(f / f0) if bright != 1.0 else a
        y += w * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) * expenv(len(t), d)
    return y


def click(rng, dur=0.004, lo=300, hi=9000, decay=0.0012):
    x = rng.standard_normal(N(dur)) * expenv(N(dur), decay * 6.9)
    return specf(x, lo, hi)


def strike(rng, bank, vel=1.0, dur=None, exc_ms=1.0, bright=None, click_g=0.5, jitter=0.0):
    """One impact on a modal bank: a short excitation convolved with the bank, plus the contact click."""
    fr, d, a = bank
    if jitter:
        fr = [f * (1 + rng.uniform(-jitter, jitter)) for f in fr]
    dur = dur or min(2.5, max(d) * 1.2 + 0.01)
    b = bright if bright is not None else 0.6 + 0.4 * vel
    ir = modes(fr, d, a, dur, rng, b)
    ne = max(8, N(exc_ms / 1000))
    exc = np.hanning(ne * 2)[ne:] * (1 + 0.3 * rng.standard_normal(ne))
    y = np.convolve(ir, exc)[:len(ir)] / ne
    c = click(rng, 0.003, 800, 12000 * b + 2000)
    y[:len(c)] += click_g * c * np.abs(y).max() / (np.abs(c).max() + 1e-9)
    return vel * y


def noise(rng, d, lo=None, hi=None, peaks=(), tilt=0.0):
    return specf(rng.standard_normal(N(d)), lo, hi, peaks, tilt)


def norm(x, peak=0.9):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def lin_interp_resample(x, sr_in):
    if sr_in == SR:
        return x
    t_out = np.arange(int(len(x) * SR / sr_in)) / SR
    return np.interp(t_out, np.arange(len(x)) / sr_in, x)


def load_conv(id):
    p = os.path.join(CONV, id + ".wav")
    with wave.open(p) as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    x = (np.frombuffer(raw, np.uint8).astype(float) - 128) / 128 if sw == 1 else \
        np.frombuffer(raw, "<i2").astype(float) / 32768
    x = x.reshape(-1, ch).mean(axis=1)
    return lin_interp_resample(x, sr)


# ------------------------------------------------------------------------------------------- modal banks
# (frequencies Hz, T60 s, amplitudes). Values are chosen by ear-memory of the machines and by the usual
# plate/bar/shell ratios; they are models, not measurements.
B_RELAY_FRONT = ([2150, 3420, 5230, 7610, 980], [0.035, 0.025, 0.018, 0.012, 0.05], [1, .7, .5, .3, .4])
B_RELAY_BACK = ([3050, 4700, 6900, 9100], [0.02, 0.015, 0.01, 0.008], [1, .6, .4, .2])
B_RELAY_FRAME = ([640, 1310, 2480], [0.06, 0.04, 0.03], [1, .6, .4])
B_CONTACTOR = ([185, 430, 1160, 2290, 3810], [0.14, 0.11, 0.07, 0.045, 0.03], [1, .8, .6, .4, .3])
B_CONTACTOR_BACK = ([260, 690, 1720, 3100], [0.1, 0.07, 0.04, 0.03], [1, .7, .5, .3])
B_HAMMER = ([1830, 3120, 4640, 6280, 8100], [0.03, 0.022, 0.016, 0.012, 0.008], [1, .8, .6, .5, .3])
B_TYPEBAR = ([1210, 2380, 3730, 5600], [0.045, 0.03, 0.02, 0.012], [1, .7, .5, .3])
B_PLATEN = ([140, 330, 760], [0.05, 0.04, 0.03], [1, .5, .3])
B_STEPPER = ([510, 1240, 2760, 4410, 6020], [0.09, 0.06, 0.04, 0.025, 0.015], [1, .9, .7, .4, .3])
B_STEPPER_FRAME = ([95, 240, 570], [0.18, 0.12, 0.08], [1, .6, .4])
B_PUNCH = ([310, 870, 1940, 3650], [0.05, 0.035, 0.025, 0.015], [1, .7, .5, .3])
B_CABINET = ([72, 150, 290, 520], [0.25, 0.18, 0.12, 0.08], [1, .7, .5, .3])
B_FLAP = ([2400, 3900, 5600], [0.012, 0.009, 0.006], [1, .6, .4])
B_FLIPDOT = ([3300, 5100, 7300], [0.01, 0.008, 0.006], [1, .7, .4])
B_SOUNDER_DOWN = ([620, 1480, 2950, 4300], [0.07, 0.05, 0.03, 0.02], [1, .8, .5, .3])
B_SOUNDER_UP = ([940, 2210, 3880, 5900], [0.05, 0.035, 0.02, 0.012], [1, .8, .6, .3])

SHELL = [1.0, 2.61, 4.86, 7.68, 10.9]                    # thin hemispherical shell (desk, typewriter bells)
CHURCH = [0.5, 1.0, 1.183, 1.506, 2.0, 2.514, 2.662, 3.011, 4.166]   # hum, prime, tierce, quint, nominal ...
BAR_FREE = [1.0, 2.756, 5.404, 8.933]                     # free-free uniform bar
BAR_TUNED = [1.0, 3.99, 9.85]                             # undercut marimba-style bar


def bell_bank(f0, ratios, t60_base, amps=None, t60_pow=0.8):
    amps = amps or [1.0 / (1 + 0.4 * i) for i in range(len(ratios))]
    return ([f0 * r for r in ratios], [t60_base / r ** t60_pow for r in ratios], amps)


# --------------------------------------------------------------------------------------- solenoid model
def solenoid_sim(rng, on=0.06, pull=2.1e5, g0=0.3, preload=4.0e4, k=2.0e4, damp=60.0, e_front=0.35,
                 e_back=0.45, tau_on=0.0015, tau_off=0.002, total=None, vmin=40.0):
    """Plunger/armature in mm and s: gap 1 mm, back stop at 0, front stop (pole face) at 1.
    a = pull * coil(t) / (1 - x + g0)^2 - preload - k x - damp v.  Returns impacts [(t, speed mm/s, 'f'|'b')].
    coil(t) rises with tau_on while energized and decays with tau_off after `on` seconds (the release delay
    of a real coil). Restitution e at each stop gives the bounce train; a hold below vmin sticks."""
    total = total or on + 0.08
    dt = 1.0 / SR
    x = v = 0.0
    coil = 0.0
    out = []
    for i in range(int(total * SR)):
        t = i * dt
        target = 1.0 if t < on else 0.0
        tau = tau_on if t < on else tau_off
        coil += (target - coil) * dt / tau
        a = pull * coil / (1.0 - x + g0) ** 2 - preload - k * x - damp * v
        v += a * dt
        x += v * dt
        if x >= 1.0:
            x = 1.0
            if v > vmin:
                out.append((t, v, "f"))
                v = -e_front * v
            else:
                v = 0.0
        elif x <= 0.0:
            x = 0.0
            if v < -vmin:
                out.append((t, -v, "b"))
                v = -e_back * v
            else:
                v = 0.0
    return out


def render_solenoid(rng, impacts, front, back, frame=None, dur=None, frame_g=0.4, thump=0.0, vref=None):
    dur = dur or (impacts[-1][0] + 0.25 if impacts else 0.3)
    y = np.zeros(N(dur))
    vref = vref or max([s for _, s, _ in impacts] + [1])
    for t, s, side in impacts:
        vel = min(1.0, s / vref)
        bank = front if side == "f" else back
        place(y, strike(rng, bank, vel, jitter=0.01), t)
        if frame is not None:
            place(y, frame_g * strike(rng, frame, vel * 0.8, click_g=0.0), t)
    if thump and impacts:
        th = np.sin(2 * np.pi * 90 * tt(0.06)) * expenv(N(0.06), 0.05) * thump
        place(y, th, impacts[0][0])
    return y


def solenoid(rng, front=B_RELAY_FRONT, back=B_RELAY_BACK, frame=B_RELAY_FRAME, part="both", **kw):
    imp = solenoid_sim(rng, **kw)
    if part == "pull":
        imp = [i for i in imp if i[2] == "f"]
    elif part == "release":
        imp = [i for i in imp if i[2] == "b" and i[0] > kw.get("on", 0.06)]
        t0 = imp[0][0] - 0.002 if imp else 0
        imp = [(t - t0, s, sd) for t, s, sd in imp]
    elif part == "pull_only_first":
        imp = imp[:1]
    if part == "pull" and imp:
        t0 = imp[0][0] - 0.002
        imp = [(t - t0, s, sd) for t, s, sd in imp]
    return render_solenoid(rng, imp, front, back, frame)


# ---------------------------------------------------------------------------------------- signal sources
def fsk(bits, f_mark, f_space, baud, amp=0.5, lead=0.0):
    n_bit = SR / baud
    total = int(len(bits) * n_bit + lead * SR)
    f = np.full(total, f_mark, float)
    for i, b in enumerate(bits):
        a = int(lead * SR + i * n_bit)
        f[a:int(lead * SR + (i + 1) * n_bit)] = f_mark if b else f_space
    ph = 2 * np.pi * np.cumsum(f) / SR
    return amp * np.sin(ph)


ITA2 = {c: i for i, c in enumerate("\0E\nA SIU\rDRJNFCKTZLWHYPQOBG\x0fMXV\x0e")}   # letters shift


def ita2_bits(text, stop=1.5):
    """Start bit (space, 0), 5 data bits LSB first, 1.5 stop bits (mark, 1). Returns a list at a half-bit grid
    expressed as whole bits: we double the rate, so 1.5 stops = 3 half bits."""
    out = []
    for ch in text.upper():
        code = ITA2.get(ch, 4)
        half = [0, 0] + sum([[b, b] for b in [(code >> i) & 1 for i in range(5)]], []) + [1] * int(stop * 2)
        out += half
    return out


def tones(freqs, d, amp=0.3):
    t = tt(d)
    return amp * sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)


def cadence(sig_fn, on, off, cycles):
    seg = np.concatenate([sig_fn(on), np.zeros(N(off))])
    return np.tile(seg, cycles)


def line_band(x):
    """Telephone channel: 300-3400 Hz, a little mid boost."""
    return specf(x, 300, 3400, peaks=[(1800, 1500, 1.3)], order=3)


def hum(d, f=60.0, rng=None, odd=True, amps=None):
    t = tt(d)
    amps = amps or [1, .45, .5, .2, .3, .1, .15]
    y = np.zeros(len(t))
    for i, a in enumerate(amps):
        h = i + 1
        y += a * np.sin(2 * np.pi * f * h * t + (rng.uniform(0, 6.28) if rng is not None else 0))
    return y


def crackle(rng, d, rate=40.0, bright=4000):
    y = np.zeros(N(d))
    n = rng.poisson(rate * d)
    for _ in range(n):
        c = click(rng, 0.002, 200, bright * rng.uniform(0.5, 1.5), 0.0004) * rng.pareto(2.5)
        place(y, c, rng.uniform(0, d))
    return y


def murmur(rng, d, f0=120.0):
    """Crosstalk: a speech-like buzz (glottal pulse train with a wandering pitch) through moving formants."""
    n = N(d)
    t = np.arange(n) / SR
    pitch = f0 * (1 + 0.15 * np.sin(2 * np.pi * 0.7 * t) + 0.08 * np.sin(2 * np.pi * 2.3 * t + 1))
    ph = np.cumsum(pitch) / SR
    src = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    src = specf(src, 80, 4000)
    syl = 0.5 + 0.5 * np.sin(2 * np.pi * 4.0 * t + 2 * np.sin(2 * np.pi * 0.9 * t))
    out = np.zeros(n)
    blk = N(0.05)
    for a in range(0, n, blk):
        f1 = 500 + 250 * np.sin(a / SR * 5.1)
        f2 = 1500 + 600 * np.sin(a / SR * 3.3 + 1)
        seg = src[a:a + blk + 256]
        seg = specf(seg, None, None, peaks=[(f1, 120, 12), (f2, 200, 8), (2600, 300, 4)])
        out[a:a + blk] += seg[:min(blk, n - a)]
    return line_band(out * syl)


def crush(x, bits=4, hold=4):
    y = np.repeat(x[::hold], hold)[:len(x)]
    q = 2 ** (bits - 1)
    return np.round(y * q) / q


def ks(rng, f, d, loss=0.996, bright=0.5, pick=0.13):
    """Karplus-Strong, vectorized per delay block."""
    L = int(round(SR / f))
    n = N(d)
    y = np.zeros(n + L + 1)
    exc = rng.uniform(-1, 1, L)
    exc = bright * exc + (1 - bright) * specf(np.tile(exc, 3), None, 800 + 6000 * bright)[L:2 * L] * 1.5
    # pick position comb
    p = max(1, int(pick * L))
    exc = exc - np.roll(exc, p) * 0.7
    y[:L] = exc
    for a in range(L, n + L, L):
        b = min(a + L, n + L + 1)
        prev = y[a - L:b - L]
        prev1 = y[a - L - 1:b - L - 1] if a - L - 1 >= 0 else np.concatenate([[0], y[a - L:b - L - 1]])
        y[a:b] = loss * 0.5 * (prev + prev1[:len(prev)])
    return y[:n]


def fm(f, d, ratio=1.4, index=6.0, idx_t60=0.6, amp_t60=2.5, rng=None):
    t = tt(d)
    I = index * expenv(len(t), idx_t60)
    return np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * ratio * t)) * expenv(len(t), amp_t60)


def motor(rng, d, f_rot=30.0, f_elec=120.0, whine=None, rough=0.2, spin_up=0.0, spin_down=0.0):
    """Motor: electrical hum (2x mains), shaft rotation partials, a whine, bearing noise; optional ramps."""
    n = N(d)
    t = np.arange(n) / SR
    sp = np.ones(n)
    if spin_up:
        k = min(n, N(spin_up))
        sp[:k] = np.linspace(0.05, 1, k) ** 0.7
    if spin_down:
        k = min(n, N(spin_down))
        sp[-k:] *= np.linspace(1, 0.05, k) ** 1.3
    ph_r = 2 * np.pi * np.cumsum(f_rot * sp) / SR
    y = 0.5 * np.sin(2 * np.pi * f_elec * t) + 0.2 * np.sin(4 * np.pi * f_elec * t)
    for h, a in [(1, .5), (2, .35), (3, .2), (5, .12), (8, .08)]:
        y += a * np.sin(h * ph_r + rng.uniform(0, 6)) * (1 + 0.2 * np.sin(ph_r))
    if whine:
        ph_w = 2 * np.pi * np.cumsum(whine * sp) / SR
        y += 0.15 * np.sin(ph_w) + 0.05 * np.sin(2 * ph_w)
    y += rough * noise(rng, d, 150, 5000, peaks=[(900, 600, 3)]) * (0.6 + 0.4 * np.sin(ph_r))
    return y * sp


# ------------------------------------------------------------------------------- machine-level helpers
def tty_char(rng, y, t, printing=True, baud=110.0, vel=1.0):
    """One teletype character cycle (Model 33 style): selector magnet clicks on the code's transitions, then the
    print cycle: typewheel positioning whirr and the hammer/print strike against platen."""
    code = rng.integers(1, 127)
    bits = [0] + [(code >> i) & 1 for i in range(8)] + [1, 1]
    tb = 1.0 / baud
    prev = 1
    for i, b in enumerate(bits):
        if b != prev:
            place(y, 0.18 * vel * strike(rng, B_RELAY_BACK if b else B_RELAY_FRONT, 0.5, click_g=0.3), t + i * tb)
        prev = b
    tp = t + 11 * tb * 0.6
    place(y, 0.25 * vel * noise(rng, 0.02, 600, 4000) * expenv(N(0.02), 0.02), tp)
    if printing:
        place(y, vel * strike(rng, B_HAMMER, rng.uniform(0.75, 1.0), jitter=0.02), tp + 0.022)
        place(y, 0.5 * vel * strike(rng, B_PLATEN, 0.8, click_g=0.0), tp + 0.022)


def carriage_return(rng, d=0.45, slam=1.0):
    y = noise(rng, d, 200, 3000, peaks=[(700, 300, 4)]) * np.linspace(0.3, 1, N(d)) * 0.25
    y *= adsr(len(y), 0.02, 0.02)
    out = np.zeros(N(d + 0.3))
    out[:len(y)] += y
    place(out, slam * strike(rng, B_CONTACTOR, 1.0, dur=0.3), d)
    place(out, 0.6 * slam * strike(rng, B_TYPEBAR, 0.9), d + 0.002)
    return out


def line_feed(rng):
    y = np.zeros(N(0.15))
    place(y, strike(rng, B_STEPPER, 0.7, dur=0.12), 0.0)
    place(y, 0.5 * strike(rng, B_RELAY_BACK, 0.6), 0.018)
    return y


def tty_motor(rng, d):
    return 0.18 * motor(rng, d, f_rot=30.0, f_elec=120.0, whine=840.0, rough=0.35)


# ======================================================================================== the sounds
# ---- 1. actuators: physically modelled solenoids and relays (attack / release pairs, chatter, bounce)
@sound("ems_relay_pull", "Telephone-type relay pulling in: modelled armature hits the pole face and bounces",
       "solenoid", tags=["actuator", "attack"])
def _(rng):
    return solenoid(rng, part="pull", on=0.08)


@sound("ems_relay_release", "Telephone-type relay releasing: armature returns to the back stop, small bounce",
       "solenoid", tags=["actuator", "release"])
def _(rng):
    return solenoid(rng, part="release", on=0.05)


@sound("ems_relay_pair", "Relay pull-in then release 120 ms later (one complete operate/release cycle)",
       "solenoid", tags=["actuator"])
def _(rng):
    return solenoid(rng, on=0.12)


@sound("ems_relay_bouncy", "Relay with a soft pole face: long contact bounce train (restitution 0.6)",
       "solenoid", tags=["actuator", "bounce"])
def _(rng):
    return solenoid(rng, part="pull", on=0.1, e_front=0.62, pull=1.4e5)


@sound("ems_relay_tiny", "Miniature (reed-like) relay tick, pull and release", "solenoid", tags=["actuator"])
def _(rng):
    fr = ([f * 1.9 for f in B_RELAY_FRONT[0]], B_RELAY_FRONT[1], B_RELAY_FRONT[2])
    bk = ([f * 1.7 for f in B_RELAY_BACK[0]], B_RELAY_BACK[1], B_RELAY_BACK[2])
    return 0.6 * solenoid(rng, fr, bk, None, on=0.04, pull=3.2e5, preload=6e4)


@sound("ems_contactor_pull", "Large AC contactor closing: heavy armature, low frame boom", "solenoid",
       tags=["actuator", "attack"])
def _(rng):
    y = solenoid(rng, B_CONTACTOR, B_CONTACTOR_BACK, B_CABINET, part="pull", on=0.2, pull=1.1e5,
                 preload=2.5e4, e_front=0.25, tau_on=0.006)
    return y + 0.15 * hum(len(y) / SR, 60.0, rng) * expenv(len(y), 0.4)


@sound("ems_contactor_release", "Large contactor dropping out", "solenoid", tags=["actuator", "release"])
def _(rng):
    return solenoid(rng, B_CONTACTOR, B_CONTACTOR_BACK, B_CABINET, part="release", on=0.1, pull=1.1e5,
                    preload=2.5e4, tau_off=0.008)


@sound("ems_relay_buzz_ac", "AC relay chattering on a weak supply: armature hammers at 120 Hz (loop)",
       "solenoid", kind="loop", tags=["actuator", "chatter", "line"])
def _(rng):
    d = 1.6
    y = np.zeros(N(d))
    for i in range(int(d * 120)):
        t = i / 120 + rng.normal(0, 0.0003)
        place(y, strike(rng, B_RELAY_FRONT, rng.uniform(0.3, 0.6), dur=0.03, click_g=0.6), t)
    return y + 0.3 * hum(d, 60, rng) * 0.3


@sound("ems_relay_rack_chatter", "A rack of relays operating in a sequence (marker / register burst)",
       "solenoid", kind="loop", tags=["actuator", "chatter", "switching"])
def _(rng):
    d = 2.4
    y = np.zeros(N(d))
    t = 0.02
    while t < d - 0.2:
        sc = rng.uniform(0.8, 1.4)
        fr = ([f * sc for f in B_RELAY_FRONT[0]], B_RELAY_FRONT[1], B_RELAY_FRONT[2])
        bk = ([f * sc for f in B_RELAY_BACK[0]], B_RELAY_BACK[1], B_RELAY_BACK[2])
        imp = solenoid_sim(rng, on=rng.uniform(0.03, 0.25))
        place(y, rng.uniform(0.3, 1.0) * render_solenoid(rng, imp, fr, bk, None), t)
        t += rng.exponential(0.06)
    return y


@sound("ems_print_hammer", "Print hammer fired against ribbon and paper (line printer, single hammer)",
       "solenoid", tags=["actuator", "printer"])
def _(rng):
    y = solenoid(rng, B_HAMMER, B_RELAY_BACK, B_PLATEN, part="pull_only_first", on=0.004, pull=5e5,
                 preload=2e4)
    return y + 0.2 * noise(rng, len(y) / SR, 1500, 9000) * expenv(len(y), 0.01)


@sound("ems_punch_magnet", "Card/tape punch magnet: punch die through card stock (thud + paper shear)",
       "solenoid", tags=["actuator", "punch", "store"])
def _(rng):
    y = render_solenoid(rng, solenoid_sim(rng, on=0.03, pull=3e5), B_PUNCH, B_RELAY_BACK, B_CABINET,
                        thump=0.4)
    sh = noise(rng, 0.03, 1200, 8000, peaks=[(3500, 2000, 2)]) * expenv(N(0.03), 0.012)
    return place(y, 0.5 * sh, 0.004)


@sound("ems_clutch_trip", "Single-revolution clutch trip: latch magnet click, pawl drop, drive engages",
       "solenoid", tags=["actuator", "clutch"])
def _(rng):
    y = np.zeros(N(0.35))
    place(y, 0.6 * strike(rng, B_RELAY_FRONT, 0.6), 0.0)
    place(y, strike(rng, B_STEPPER, 1.0), 0.012)
    m = 0.3 * motor(rng, 0.3, 30, 120, 600, 0.3) * np.linspace(0.2, 1, N(0.3)) * adsr(N(0.3), 0.01, 0.05)
    place(y, m, 0.02)
    place(y, 0.7 * strike(rng, B_STEPPER, 0.7), 0.31)
    return y


@sound("ems_escapement", "Escapement tick-tock: pallet against escape wheel, pair of unequal clicks",
       "modal", tags=["actuator", "escapement"])
def _(rng):
    y = np.zeros(N(0.5))
    place(y, strike(rng, B_RELAY_BACK, 0.9, jitter=0.02), 0.0)
    place(y, 0.7 * strike(rng, B_RELAY_FRONT, 0.6, jitter=0.02), 0.25)
    return y


@sound("ems_selector_magnet", "Teletype selector magnet stepping through one 5-unit code (110 baud clicks)",
       "solenoid", tags=["actuator", "teletype", "receive"])
def _(rng):
    y = np.zeros(N(0.16))
    bits = [0, 1, 0, 1, 1, 0, 1, 1, 1]
    prev = 1
    for i, b in enumerate(bits):
        if b != prev:
            place(y, strike(rng, B_RELAY_FRONT if not b else B_RELAY_BACK, 0.8, click_g=0.4), i / 110)
        prev = b
    return y


@sound("ems_stepper_step", "Strowger-type stepping switch: one step (pawl drives the wipers one contact)",
       "solenoid", tags=["actuator", "switching", "strowger"])
def _(rng):
    imp = solenoid_sim(rng, on=0.035, pull=1.6e5, e_front=0.3)
    return render_solenoid(rng, imp, B_STEPPER, B_RELAY_BACK, B_STEPPER_FRAME, frame_g=0.6)


@sound("ems_stepper_vertical", "Strowger selector: 7 vertical steps at 10 pulses/s from a dial", "solenoid",
       kind="phrase", tags=["switching", "strowger", "dial"])
def _(rng):
    y = np.zeros(N(1.0))
    for i in range(7):
        imp = solenoid_sim(rng, on=0.06, pull=1.6e5, e_front=0.3)
        place(y, render_solenoid(rng, imp, B_STEPPER, B_RELAY_BACK, B_STEPPER_FRAME, frame_g=0.6), i * 0.1)
    return y


@sound("ems_stepper_rotary_hunt", "Strowger selector hunting rotary: fast self-interrupted steps, then cut in",
       "solenoid", kind="phrase", tags=["switching", "strowger"])
def _(rng):
    y = np.zeros(N(0.9))
    t, step = 0.0, 0.03
    for i in range(14):
        place(y, 0.8 * strike(rng, B_STEPPER, rng.uniform(0.6, 0.85), jitter=0.01), t)
        place(y, 0.3 * strike(rng, B_RELAY_BACK, 0.5), t + 0.012)
        t += step
    place(y, solenoid(rng, part="pull", on=0.1), t + 0.03)
    return y


@sound("ems_stepper_release", "Strowger switch release: wipers spin home and drop (whirr, clatter, thunk)",
       "solenoid", kind="phrase", tags=["switching", "strowger", "release"])
def _(rng):
    y = np.zeros(N(0.6))
    place(y, solenoid(rng, part="pull", on=0.2), 0.0)
    w = noise(rng, 0.18, 300, 4000, peaks=[(1400, 600, 3)]) * np.linspace(1, 0.4, N(0.18)) * 0.25
    place(y, w, 0.03)
    for i in range(6):
        place(y, 0.3 * strike(rng, B_RELAY_BACK, 0.5), 0.04 + i * 0.022)
    place(y, strike(rng, B_STEPPER_FRAME, 1.0, dur=0.3, click_g=0.6), 0.22)
    place(y, 0.7 * strike(rng, B_STEPPER, 0.9), 0.222)
    return y


@sound("ems_crossbar_select", "Crossbar switch: select magnet rocks the bar, hold magnet closes the crosspoint",
       "solenoid", kind="phrase", tags=["switching", "crossbar"])
def _(rng):
    y = np.zeros(N(0.5))
    place(y, solenoid(rng, B_CONTACTOR, B_CONTACTOR_BACK, None, part="pull", on=0.2, pull=1.3e5,
                      preload=3e4), 0.0)
    place(y, 0.9 * solenoid(rng, B_STEPPER, B_RELAY_BACK, B_STEPPER_FRAME, part="pull", on=0.2), 0.06)
    return y


@sound("ems_crossbar_release", "Crossbar hold magnet releases: the fingers spring back (clatter + bar)",
       "solenoid", tags=["switching", "crossbar", "release"])
def _(rng):
    y = solenoid(rng, B_STEPPER, B_RELAY_BACK, B_STEPPER_FRAME, part="release", on=0.05)
    for i in range(5):
        place(y, 0.25 * strike(rng, B_RELAY_BACK, 0.5, jitter=0.05), 0.004 + i * rng.uniform(0.002, 0.006))
    return y


@sound("ems_flipdot", "Flip-disc display: one disc flipping (magnetic snap onto its stop)", "solenoid",
       tags=["display", "actuator"])
def _(rng):
    return render_solenoid(rng, solenoid_sim(rng, on=0.01, pull=4e5, e_front=0.5), B_FLIPDOT, B_FLIPDOT,
                           None)


@sound("ems_flipdot_wipe", "Flip-disc display: a column-by-column wipe (cascade of disc snaps)", "solenoid",
       kind="phrase", tags=["display", "message"])
def _(rng):
    y = np.zeros(N(1.4))
    for col in range(28):
        for r in range(rng.integers(2, 7)):
            sc = rng.uniform(0.9, 1.1)
            bank = ([f * sc for f in B_FLIPDOT[0]], B_FLIPDOT[1], B_FLIPDOT[2])
            place(y, rng.uniform(0.3, 0.8) * strike(rng, bank, 0.8), col * 0.04 + rng.uniform(0, 0.012))
    return y


@sound("ems_splitflap", "Split-flap display: one unit flipping through 9 flaps and stopping", "modal",
       kind="phrase", tags=["display", "message"])
def _(rng):
    y = np.zeros(N(0.7))
    t = 0.0
    for i in range(9):
        place(y, strike(rng, B_FLAP, rng.uniform(0.6, 1.0), jitter=0.04), t)
        place(y, 0.3 * noise(rng, 0.01, 2000, 9000) * expenv(N(0.01), 0.008), t + 0.003)
        t += 0.045 + 0.01 * i / 9
    place(y, 0.6 * strike(rng, B_RELAY_FRONT, 0.6), t + 0.02)
    return y


@sound("ems_splitflap_board", "Split-flap departure board updating: many units flapping, then settling", "modal",
       kind="phrase", tags=["display", "message"])
def _(rng):
    y = np.zeros(N(2.6))
    for u in range(24):
        t = rng.uniform(0, 0.15)
        stop = rng.uniform(0.5, 2.2)
        while t < stop:
            place(y, rng.uniform(0.2, 0.6) * strike(rng, B_FLAP, 0.8, jitter=0.06), t)
            t += rng.uniform(0.038, 0.06)
    return y


# ---- 2. line noise and signalling
@sound("ems_fsk_bell103_orig", "Bell 103 modem, originate side: 300 baud FSK 1070/1270 Hz (random data, loop)",
       "fsk", kind="loop", tags=["line", "modem"])
def _(rng):
    return line_band(fsk(list(rng.integers(0, 2, 600)), 1270, 1070, 300))


@sound("ems_fsk_bell103_ans", "Bell 103 answer side: 2225/2025 Hz FSK, 300 baud (loop)", "fsk", kind="loop",
       tags=["line", "modem"])
def _(rng):
    return line_band(fsk(list(rng.integers(0, 2, 600)), 2225, 2025, 300))


@sound("ems_fsk_bell202", "Bell 202 FSK at 1200 baud, 1200/2200 Hz (caller-ID style burst)", "fsk",
       tags=["line", "modem"])
def _(rng):
    return line_band(fsk([1] * 120 + list(rng.integers(0, 2, 1200)), 1200, 2200, 1200))


@sound("ems_rtty_baudot", "RTTY: ITA2 Baudot at 45.45 baud, 170 Hz shift (2125/2295), text 'RYRYRY CQ'",
       "fsk", kind="loop", tags=["line", "teletype", "radio"])
def _(rng):
    bits = ita2_bits("RYRYRY CQ CQ DE BSYN RYRY ")
    return fsk(bits, 2125, 2295, 45.45 * 2, lead=0.1)


@sound("ems_rtty_idle", "RTTY steady mark carrier with a slight drift (tonal, ~2125 Hz)", "fsk", tonal=True,
       root=None, tags=["line", "radio"])
def _(rng):
    t = tt(2.5)
    f = 2125 + 3 * np.sin(2 * np.pi * 0.3 * t)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * adsr(len(t), 0.01, 0.05)


@sound("ems_modem_answer_tone", "Modem answer tone 2100 Hz with 450 ms phase reversals (V.25/V.8 ANSam style)",
       "fsk", tags=["line", "modem"])
def _(rng):
    t = tt(2.7)
    ph = np.pi * (np.floor(t / 0.45) % 2)
    am = 1 + 0.2 * np.sin(2 * np.pi * 15 * t)
    return line_band(np.sin(2 * np.pi * 2100 * t + ph) * am)


@sound("ems_modem_handshake", "Modem handshake sketch: dial tone, DTMF, ring-back, answer tone, FSK, scrambled "
       "training noise", "fsk", kind="phrase", tags=["line", "modem", "message"])
def _(rng):
    parts = [tones([350, 440], 0.6)]
    dt = {"1": (697, 1209), "5": (770, 1336), "5b": (770, 1336), "2": (697, 1336), "0": (941, 1336)}
    for k in ["5", "5b", "5", "1", "2", "0", "2"]:
        parts += [tones(dt[k], 0.07), np.zeros(N(0.05))]
    parts += [np.zeros(N(0.25)), tones([440, 480], 0.5), np.zeros(N(0.3))]
    t = tt(1.0)
    parts += [np.sin(2 * np.pi * 2100 * t + np.pi * (np.floor(t / 0.45) % 2))]
    parts += [fsk(list(rng.integers(0, 2, 150)), 1270, 1070, 300), fsk(list(rng.integers(0, 2, 150)), 2225, 2025, 300)]
    tr = noise(rng, 1.2, 600, 3200, peaks=[(1800, 900, 3)]) * 0.5
    tr += 0.4 * np.sin(2 * np.pi * 1800 * tt(1.2) + 6 * np.sin(2 * np.pi * 37 * tt(1.2)))
    parts += [tr]
    return line_band(np.concatenate(parts))


@sound("ems_acoustic_coupler", "Acoustic coupler: FSK heard through a carbon mic and rubber cups (muffled, "
       "with room hiss)", "fsk", kind="loop", tags=["line", "modem"])
def _(rng):
    x = fsk(list(rng.integers(0, 2, 500)), 1270, 1070, 300) + fsk(list(rng.integers(0, 2, 500)), 2225, 2025, 300) * 0.5
    x = specf(x, 400, 2400, peaks=[(1000, 400, 2.5)])
    x = np.tanh(2.5 * x)
    return line_band(x) + 0.05 * noise(rng, len(x) / SR, 200, 6000)


@sound("ems_dial_tone", "North American precise dial tone 350+440 Hz (tonal pad source; root labelled A4 = 440)",
       "additive", tonal=True, root=69, tags=["line", "callprogress"])
def _(rng):
    return line_band(tones([350, 440], 3.0)) + 0.01 * noise(rng, 3.0, 300, 3400)


@sound("ems_ringback", "Ring-back tone 440+480 Hz, 2 s on / 4 s off (one cycle)", "additive", kind="loop",
       tags=["line", "callprogress"])
def _(rng):
    return line_band(cadence(lambda d: tones([440, 480], d) * adsr(N(d), 0.01, 0.01), 2.0, 1.0, 1))


@sound("ems_busy", "Busy signal 480+620 Hz, 0.5 s on / 0.5 s off (loop)", "additive", kind="loop",
       tags=["line", "callprogress"])
def _(rng):
    return line_band(cadence(lambda d: tones([480, 620], d) * adsr(N(d), 0.005, 0.005), 0.5, 0.5, 3))


@sound("ems_reorder", "Reorder (fast busy) 480+620 Hz, 0.25 s on / 0.25 s off", "additive", kind="loop",
       tags=["line", "callprogress"])
def _(rng):
    return line_band(cadence(lambda d: tones([480, 620], d) * adsr(N(d), 0.005, 0.005), 0.25, 0.25, 6))


@sound("ems_sit_tones", "Special information tones (913.8, 1370.6, 1776.7 Hz rising triplet)", "additive",
       tags=["line", "callprogress"])
def _(rng):
    return line_band(np.concatenate([tones([f], 0.33) * adsr(N(0.33), 0.005, 0.01)
                                     for f in (913.8, 1370.6, 1776.7)]))


@sound("ems_pulse_dial_digit", "Pulse dialing heard on the line: digit 7 (7 breaks at 10 pps, 61/39 break/make)",
       "line", kind="phrase", tags=["line", "dial"])
def _(rng):
    y = 0.04 * line_band(noise(rng, 1.1))
    for i in range(7):
        t = 0.1 + i * 0.1
        y[N(t):N(t + 0.061)] *= 0.15
        place(y, line_band(click(rng, 0.006, 100, 6000, 0.0015)), t)
        place(y, 0.6 * line_band(click(rng, 0.006, 100, 6000, 0.0015)), t + 0.061)
    return y


@sound("ems_rotary_dial", "Rotary dial mechanism: wind-up ratchet, then governed run-down with 10 pps contact "
       "clicks", "modal", kind="phrase", tags=["dial", "actuator"])
def _(rng):
    y = np.zeros(N(1.6))
    for i in range(12):
        place(y, 0.5 * strike(rng, B_RELAY_BACK, 0.5, jitter=0.03), 0.02 + i * 0.035)
    place(y, strike(rng, B_TYPEBAR, 0.7), 0.46)
    gov = noise(rng, 0.85, 400, 3500, peaks=[(1650, 300, 6)]) * 0.15
    gov *= 1 + 0.5 * np.sin(2 * np.pi * 10 * tt(0.85))
    place(y, gov, 0.5)
    for i in range(8):
        place(y, 0.6 * strike(rng, B_RELAY_FRONT, 0.6), 0.52 + i * 0.1)
    place(y, 0.8 * strike(rng, B_TYPEBAR, 0.9), 1.36)
    return y


@sound("ems_mains_hum", "Mains hum on a long line: 60 Hz series with strong odd harmonics (tonal, ~60 Hz)",
       "line", tonal=True, tags=["line", "noise"])
def _(rng):
    d = 3.0
    y = hum(d, 60.0, rng, amps=[1, .3, .6, .15, .4, .1, .25, .05, .15])
    return y * (1 + 0.05 * np.sin(2 * np.pi * 0.5 * tt(d))) + 0.03 * noise(rng, d, 300, 3400)


@sound("ems_hum_buzz_50", "50 Hz transformer buzz with magnetostriction harmonics (European exchange room)",
       "line", tonal=True, tags=["line", "noise"])
def _(rng):
    d = 3.0
    y = hum(d, 50.0, rng, amps=[.3, 1, .5, .7, .3, .4, .2, .25, .15, .1, .08])
    return np.tanh(1.5 * y)


@sound("ems_line_hiss", "Long-distance line: band-limited hiss with slow level wander (loop)", "line",
       kind="loop", tags=["line", "noise"])
def _(rng):
    d = 3.0
    w = 1 + 0.3 * specf(rng.standard_normal(N(d)), None, 2)
    return line_band(noise(rng, d)) * w


@sound("ems_line_crackle", "Noisy subscriber loop: crackle from a corroded joint, plus faint hum (loop)", "line",
       kind="loop", tags=["line", "noise"])
def _(rng):
    d = 3.0
    return line_band(crackle(rng, d, 60)) + 0.1 * hum(d, 60, rng) * 0.3 + 0.02 * line_band(noise(rng, d))


@sound("ems_line_dropout", "Line with dropouts: hiss and hum cut out and return with clicks", "line",
       kind="loop", tags=["line", "noise"])
def _(rng):
    d = 3.0
    y = 0.4 * line_band(noise(rng, d)) + 0.3 * hum(d, 60, rng) * 0.3
    g = np.ones(len(y))
    t = 0.3
    while t < d - 0.2:
        a, b = N(t), N(t + rng.uniform(0.05, 0.35))
        g[a:b] = 0.02
        place(y, line_band(click(rng, 0.004, 100, 8000)), t)
        place(y, line_band(click(rng, 0.004, 100, 8000)), b / SR)
        t = b / SR + rng.uniform(0.2, 0.7)
    return y * g


@sound("ems_crosstalk", "Crosstalk: someone else's conversation leaking in, unintelligible, under hiss",
       "line", kind="loop", tags=["line", "noise"])
def _(rng):
    d = 3.5
    return 0.6 * murmur(rng, d) + 0.25 * line_band(noise(rng, d))


@sound("ems_line_hit", "Line hit: a burst of impulse noise (lightning, a nearby switch operating)", "line",
       tags=["line", "noise"])
def _(rng):
    y = np.zeros(N(0.5))
    for i in range(18):
        place(y, rng.pareto(2) * line_band(click(rng, 0.004, 100, 8000)), rng.exponential(0.08))
    return y


@sound("ems_telegraph_sounder", "Telegraph sounder: down-stroke 'click' and up-stroke 'clack' (one dot)",
       "solenoid", tags=["telegraph", "actuator"])
def _(rng):
    y = np.zeros(N(0.3))
    place(y, strike(rng, B_SOUNDER_DOWN, 1.0, dur=0.15), 0.0)
    place(y, 0.8 * strike(rng, B_SOUNDER_UP, 0.9, dur=0.15), 0.09)
    return y


@sound("ems_telegraph_message", "Telegraph sounder spelling 'CQ' in American Morse timing (phrase)", "solenoid",
       kind="phrase", tags=["telegraph", "message"])
def _(rng):
    code = "-.-. --.-"
    u = 0.07
    y = np.zeros(N(2.2))
    t = 0.02
    for c in code:
        if c == " ":
            t += 3 * u
            continue
        dur = u if c == "." else 3 * u
        place(y, strike(rng, B_SOUNDER_DOWN, rng.uniform(0.85, 1.0), dur=0.12), t)
        place(y, 0.8 * strike(rng, B_SOUNDER_UP, rng.uniform(0.8, 0.95), dur=0.12), t + dur)
        t += dur + u
    return y


@sound("ems_morse_cw", "CW Morse on a 700 Hz tone, keyed with soft clicks ('BSYN')", "fsk", kind="phrase",
       tags=["telegraph", "radio"])
def _(rng):
    code = "-... ... -.-- -."
    u = 0.06
    out = []
    for c in code:
        if c == " ":
            out.append(np.zeros(N(2 * u)))
            continue
        d = u if c == "." else 3 * u
        out += [np.sin(2 * np.pi * 700 * tt(d)) * adsr(N(d), 0.004, 0.004), np.zeros(N(u))]
    return np.concatenate(out)


# ---- 3. teletypes, printers, punches: message events
@sound("ems_tty_char", "Teletype: one printed character (selector clicks, typewheel, hammer on platen)",
       "solenoid", tags=["teletype", "printer"])
def _(rng):
    y = np.zeros(N(0.25))
    tty_char(rng, y, 0.0)
    return y


@sound("ems_tty_burst", "Teletype printing a line at 10 chars/s over motor hum (loop)", "phrase", kind="loop",
       tags=["teletype", "printer", "message"])
def _(rng):
    d = 3.0
    y = tty_motor(rng, d)
    for i in range(int(d * 10)):
        tty_char(rng, y, i * 0.1, printing=rng.random() > 0.15)
    return y


@sound("ems_tty_motor", "Teletype motor idling: 1800 rpm shaft, gear whine, hum (loop / drone)", "additive",
       kind="loop", tags=["teletype", "motor"])
def _(rng):
    return tty_motor(rng, 3.0)


@sound("ems_tty_motor_start", "Teletype motor start: relay pull-in and spin-up to speed", "additive",
       kind="phrase", tags=["teletype", "motor", "message"])
def _(rng):
    y = np.zeros(N(1.6))
    place(y, solenoid(rng, B_CONTACTOR, B_CONTACTOR_BACK, None, part="pull", on=0.2, pull=1.1e5, preload=2.5e4), 0)
    place(y, 0.2 * motor(rng, 1.5, 30, 120, 840, 0.35, spin_up=0.9) / 0.18 * 0.18, 0.03)
    return y


@sound("ems_tty_motor_stop", "Teletype motor stop: spin-down after the line goes idle", "additive",
       kind="phrase", tags=["teletype", "motor"])
def _(rng):
    return 0.2 * motor(rng, 1.4, 30, 120, 840, 0.35, spin_down=1.2) + 0.0


@sound("ems_tty_cr", "Teletype carriage return (whirr, slam into the left margin)", "phrase",
       tags=["teletype", "carriage"])
def _(rng):
    return carriage_return(rng, 0.25, 1.0)


@sound("ems_tty_lf", "Teletype line feed: platen ratchet advance", "modal", tags=["teletype", "carriage"])
def _(rng):
    return line_feed(rng)


@sound("ems_tty_bell", "Teletype signal bell (BEL, ^G): small gong struck once", "modal", tonal=True, root=None,
       tags=["teletype", "bell", "message"])
def _(rng):
    return strike(rng, bell_bank(1480, SHELL, 1.6), 1.0, dur=2.2, click_g=0.3)


@sound("ems_tty_message_received", "Message received on a teletype: bell, motor start, two printed lines with "
       "CR/LF, motor runs on", "phrase", kind="phrase", tags=["teletype", "message", "receive"])
def _(rng):
    d = 7.5
    y = np.zeros(N(d))
    place(y, strike(rng, bell_bank(1480, SHELL, 1.6), 1.0, dur=1.5, click_g=0.3), 0.0)
    place(y, solenoid(rng, B_CONTACTOR, B_CONTACTOR_BACK, None, part="pull", on=0.2, pull=1.1e5, preload=2.5e4), 0.5)
    m = tty_motor(rng, d - 0.55) * np.minimum(1, np.arange(N(d - 0.55)) / N(0.6))
    place(y, m, 0.55)
    t = 1.3
    for line in range(2):
        for i in range(int(rng.integers(22, 32))):
            tty_char(rng, y, t, printing=rng.random() > 0.17)
            t += 0.1
        place(y, carriage_return(rng, 0.2, 0.9), t)
        place(y, line_feed(rng), t + 0.22)
        t += 0.5
    return y


@sound("ems_tape_punch_burst", "Paper-tape punch (high-speed, ~50 rows/s): stored message burst with feed",
       "phrase", kind="loop", tags=["punch", "store"])
def _(rng):
    d = 2.0
    y = 0.15 * motor(rng, d, 25, 120, 1100, 0.4)
    for i in range(int(d * 50)):
        holes = rng.integers(1, 6)
        place(y, (0.4 + 0.1 * holes) * strike(rng, B_PUNCH, 0.7, dur=0.04, jitter=0.03), i * 0.02)
        place(y, 0.15 * noise(rng, 0.008, 2000, 9000), i * 0.02 + 0.002)
    return y


@sound("ems_tape_reader", "Paper-tape reader: sprocket feed clicks at 30 rows/s and tape rustle (loop)",
       "phrase", kind="loop", tags=["tape", "read"])
def _(rng):
    d = 2.0
    y = 0.15 * noise(rng, d, 1500, 9000) * (1 + 0.3 * np.sin(2 * np.pi * 30 * tt(d)))
    for i in range(int(d * 30)):
        place(y, 0.6 * strike(rng, B_RELAY_BACK, 0.5, dur=0.02), i / 30)
    return y


@sound("ems_card_punch_col", "Keypunch: one column punched (punch bail and dies, card advances one column)",
       "solenoid", tags=["punch", "card", "store"])
def _(rng):
    y = np.zeros(N(0.2))
    place(y, strike(rng, B_PUNCH, 1.0), 0.0)
    place(y, 0.5 * strike(rng, B_RELAY_FRONT, 0.7), 0.025)
    place(y, 0.3 * noise(rng, 0.02, 2500, 9000) * expenv(N(0.02), 0.01), 0.002)
    return y


@sound("ems_card_punch_dup", "Keypunch duplicating a card: 80 columns at ~20 columns/s (loop)", "phrase",
       kind="loop", tags=["punch", "card", "store"])
def _(rng):
    d = 3.2
    y = 0.08 * motor(rng, d, 20, 120, 0, 0.3)
    for i in range(int(d * 20)):
        hit = rng.random() > 0.25
        if hit:
            place(y, rng.uniform(0.6, 1.0) * strike(rng, B_PUNCH, 0.9, dur=0.06, jitter=0.02), i * 0.05)
        place(y, 0.3 * strike(rng, B_RELAY_FRONT, 0.6, dur=0.02), i * 0.05 + 0.02)
    return y


@sound("ems_card_feed", "Card feed and register: picker knife, rollers, card hits the stop", "phrase",
       tags=["card"])
def _(rng):
    y = np.zeros(N(0.45))
    w = noise(rng, 0.12, 300, 6000, peaks=[(2500, 1500, 2)]) * adsr(N(0.12), 0.01, 0.06) * 0.4
    place(y, w, 0.0)
    place(y, strike(rng, B_STEPPER, 0.8), 0.13)
    place(y, 0.6 * strike(rng, B_PUNCH, 0.6), 0.16)
    return y


@sound("ems_card_stack", "Card release into the stacker: flap and thump", "phrase", tags=["card"])
def _(rng):
    y = np.zeros(N(0.35))
    place(y, 0.5 * noise(rng, 0.06, 800, 7000) * adsr(N(0.06), 0.005, 0.04), 0)
    place(y, strike(rng, B_CABINET, 0.8, dur=0.3, click_g=0.3), 0.06)
    return y


@sound("ems_sorter_run", "Card sorter at 1000 cards/min: feed rhythm, brush, pocket chute clicks (loop)",
       "phrase", kind="loop", tags=["card", "rhythm"])
def _(rng):
    d = 3.0
    y = 0.2 * motor(rng, d, 16.7, 120, 520, 0.5)
    for i in range(int(d * 16.67)):
        t = i / 16.67
        place(y, 0.5 * strike(rng, B_STEPPER, 0.6, dur=0.05), t)
        place(y, 0.2 * noise(rng, 0.02, 2000, 8000), t + 0.01)
        place(y, 0.35 * strike(rng, B_FLAP, 0.7, jitter=0.1), t + 0.03)
    return y


@sound("ems_tabulator_cycle", "Tabulator (407-style) at 150 cycles/min: a print-and-add cycle, the "
       "machine's bar (one cycle, 0.4 s)", "phrase", kind="loop", tags=["card", "rhythm", "tabulator"])
def _(rng):
    d = 0.4
    y = 0.15 * motor(rng, d, 2.5 * 6, 120, 300, 0.4)
    place(y, strike(rng, B_CABINET, 1.0, dur=0.25, click_g=0.4), 0.0)
    place(y, 0.6 * strike(rng, B_STEPPER, 0.8), 0.1)
    for k in range(int(rng.integers(10, 30))):
        place(y, 0.25 * strike(rng, B_HAMMER, 0.7, jitter=0.1, dur=0.03), 0.2 + rng.uniform(0, 0.03))
    place(y, 0.4 * strike(rng, B_PUNCH, 0.7), 0.3)
    return y


@sound("ems_tabulator_run", "Tabulator running a report: 8 cycles at 150/min with accumulator clatter (loop)",
       "phrase", kind="loop", tags=["card", "rhythm", "tabulator"])
def _(rng):
    d = 3.2
    y = 0.15 * motor(rng, d, 15, 120, 300, 0.4)
    for c in range(8):
        t0 = c * 0.4
        place(y, strike(rng, B_CABINET, 1.0, dur=0.25, click_g=0.4), t0)
        place(y, 0.6 * strike(rng, B_STEPPER, 0.8), t0 + 0.1)
        for k in range(int(rng.integers(8, 30))):
            place(y, 0.25 * strike(rng, B_HAMMER, 0.7, jitter=0.1, dur=0.03), t0 + 0.2 + rng.uniform(0, 0.03))
        for k in range(int(rng.integers(3, 9))):
            place(y, 0.2 * strike(rng, B_RELAY_FRONT, 0.5), t0 + 0.05 + rng.uniform(0, 0.3))
    return y


@sound("ems_lineprinter_line", "Chain line printer: one 132-column line (hammer volley) then a paper space",
       "phrase", tags=["printer", "display", "message"])
def _(rng):
    y = np.zeros(N(0.25))
    for i in range(132):
        if rng.random() > 0.3:
            place(y, 0.25 * strike(rng, B_HAMMER, rng.uniform(0.5, 1.0), dur=0.03, jitter=0.03, click_g=0.6),
                  rng.uniform(0, 0.055))
    place(y, 0.6 * strike(rng, B_STEPPER, 0.8), 0.075)
    place(y, 0.2 * noise(rng, 0.05, 400, 5000) * adsr(N(0.05), 0.005, 0.03), 0.08)
    return y


@sound("ems_lineprinter_page", "Chain line printer at 1100 lines/min, then a form-feed slew (loop)", "phrase",
       kind="loop", tags=["printer", "rhythm"])
def _(rng):
    d = 3.0
    y = 0.12 * motor(rng, d, 20, 120, 2000, 0.3)
    t = 0.0
    while t < d - 0.6:
        for i in range(132):
            if rng.random() > 0.35:
                place(y, 0.2 * strike(rng, B_HAMMER, rng.uniform(0.5, 1.0), dur=0.025, jitter=0.03),
                      t + rng.uniform(0, 0.04))
        place(y, 0.4 * strike(rng, B_STEPPER, 0.7, dur=0.05), t + 0.045)
        t += 0.0545
    sl = noise(rng, 0.5, 300, 5000, peaks=[(1200, 800, 3)]) * adsr(N(0.5), 0.02, 0.1) * 0.5
    place(y, sl, d - 0.55)
    return y


@sound("ems_lineprinter_tone_a3", "Line-printer 'music': hammers fired in a pattern so the volley repeats at "
       "220 Hz (pitched source, A3)", "phrase", tonal=True, root=57, tags=["printer", "tonal", "lead"])
def _(rng):
    d = 2.5
    y = np.zeros(N(d))
    per = 1 / 220.0
    hit = strike(rng, B_HAMMER, 0.9, dur=0.02, click_g=0.6)
    n = int(d / per)
    for i in range(n):
        place(y, (0.8 + 0.2 * rng.random()) * hit, i * per + rng.normal(0, per * 0.01))
    y += 0.1 * motor(rng, d, 20, 120, 0, 0.2)
    return y * adsr(len(y), 0.01, 0.2)


@sound("ems_selectric_char", "Selectric-style golf-ball element: tilt/rotate whirr then the strike", "phrase",
       tags=["typewriter", "printer"])
def _(rng):
    y = np.zeros(N(0.2))
    place(y, 0.3 * noise(rng, 0.015, 800, 5000, peaks=[(2300, 800, 3)]) * adsr(N(0.015), 0.002, 0.01), 0)
    place(y, 0.3 * strike(rng, B_RELAY_FRONT, 0.6), 0.004)
    place(y, strike(rng, B_TYPEBAR, 1.0), 0.019)
    place(y, 0.5 * strike(rng, B_PLATEN, 0.9, click_g=0), 0.019)
    return y


@sound("ems_typebar", "Manual typewriter: typebar strike on the platen (one key)", "solenoid",
       tags=["typewriter"])
def _(rng):
    y = np.zeros(N(0.2))
    place(y, strike(rng, B_TYPEBAR, 1.0, jitter=0.02), 0)
    place(y, 0.5 * strike(rng, B_PLATEN, 0.9, click_g=0), 0)
    place(y, 0.3 * strike(rng, B_RELAY_BACK, 0.4), 0.05)
    return y


@sound("ems_typewriter_bell", "Typewriter margin bell: small shell bell, struck by a lever (tonal)", "modal",
       tonal=True, tags=["typewriter", "bell", "tonal"])
def _(rng):
    return strike(rng, bell_bank(hz(91), SHELL, 1.2), 1.0, dur=1.8, click_g=0.2)


@sound("ems_drum_memory", "Magnetic drum memory: drum whine near 208 Hz (12,500 rpm), bearing hiss, head "
       "select relays", "additive", tonal=True, tags=["memory", "motor", "drone"])
def _(rng):
    d = 3.0
    t = tt(d)
    f = 208.3
    y = sum(a * np.sin(2 * np.pi * f * h * t + rng.uniform(0, 6)) for h, a in
            [(1, 1), (2, .4), (3, .35), (4, .1), (6, .15), (12, .05)])
    y *= 1 + 0.05 * np.sin(2 * np.pi * 3.5 * t)
    y += 0.2 * noise(rng, d, 2000, 9000)
    for k in range(5):
        place(y, 0.5 * strike(rng, B_RELAY_FRONT, 0.5), rng.uniform(0.2, 2.8))
    return y


@sound("ems_drum_write", "Drum memory storing a word: write current hiss bursts in sync with the drum turning",
       "noise", kind="phrase", tags=["memory", "store"])
def _(rng):
    d = 1.0
    t = tt(d)
    y = 0.3 * np.sin(2 * np.pi * 208.3 * t)
    for k in range(int(d * 208.3 / 4)):
        if rng.random() > 0.5:
            place(y, 0.3 * noise(rng, 0.0045, 3000, 10000), k * 4 / 208.3)
    return y


@sound("ems_tape_drive_shuttle", "Vacuum-column tape drive: reels jerk start/stop (block reads), vacuum hiss "
       "(loop)", "noise", kind="loop", tags=["memory", "tape", "motor"])
def _(rng):
    d = 3.0
    y = 0.25 * noise(rng, d, 500, 8000, peaks=[(3000, 2000, 1.5)])
    t = 0.05
    while t < d - 0.2:
        L = rng.uniform(0.05, 0.25)
        m = motor(rng, L, 40, 120, rng.uniform(300, 700), 0.4) * adsr(N(L), 0.005, 0.02)
        place(y, 0.5 * m, t)
        place(y, 0.4 * strike(rng, B_RELAY_FRONT, 0.5), t)
        t += L + rng.uniform(0.03, 0.2)
    return y


@sound("ems_ticker", "Stock ticker: typewheel stepping, print strikes and tape feed (loop)", "phrase", kind="loop",
       tags=["teletype", "printer", "message"])
def _(rng):
    d = 3.0
    y = np.zeros(N(d))
    t = 0.0
    while t < d - 0.1:
        for s in range(int(rng.integers(2, 8))):
            place(y, 0.3 * strike(rng, B_RELAY_BACK, 0.5, dur=0.02), t)
            t += 0.012
        place(y, strike(rng, B_TYPEBAR, 0.8, jitter=0.05), t)
        t += rng.uniform(0.05, 0.12)
    return y + 0.05 * noise(rng, d, 1500, 7000)


@sound("ems_adding_machine_pull", "Adding machine handle pull: ratchet rack, accumulator cycle, print strike",
       "phrase", tags=["calculator"])
def _(rng):
    y = np.zeros(N(0.6))
    for i in range(10):
        place(y, 0.4 * strike(rng, B_STEPPER, 0.5, jitter=0.03, dur=0.04), 0.02 + i * 0.022)
    place(y, strike(rng, B_TYPEBAR, 1.0), 0.27)
    place(y, 0.6 * strike(rng, B_PLATEN, 1.0, click_g=0), 0.27)
    for i in range(6):
        place(y, 0.3 * strike(rng, B_STEPPER, 0.4, dur=0.03), 0.33 + i * 0.03)
    place(y, 0.7 * strike(rng, B_CONTACTOR_BACK, 0.7), 0.52)
    return y


@sound("ems_calculator_division", "Motor-driven desk calculator dividing: repeated subtract cycles and "
       "carriage shifts (loop)", "phrase", kind="loop", tags=["calculator", "rhythm"])
def _(rng):
    d = 3.0
    y = 0.15 * motor(rng, d, 12, 120, 460, 0.4)
    t = 0.0
    while t < d - 0.1:
        n = int(rng.integers(2, 9))
        for i in range(n):
            place(y, 0.6 * strike(rng, B_STEPPER, 0.7, dur=0.05, jitter=0.02), t)
            place(y, 0.25 * strike(rng, B_RELAY_FRONT, 0.4), t + 0.03)
            t += 0.083
        place(y, strike(rng, B_CONTACTOR_BACK, 0.8, dur=0.15), t)
        t += 0.12
    return y


@sound("ems_cash_register", "Cash register: keys, crank cycle, drawer bell and drawer slide", "phrase",
       kind="phrase", tags=["register", "bell", "message"])
def _(rng):
    y = np.zeros(N(2.2))
    for i in range(3):
        place(y, 0.6 * strike(rng, B_TYPEBAR, 0.8, jitter=0.05), 0.05 + i * 0.18)
    for i in range(8):
        place(y, 0.4 * strike(rng, B_STEPPER, 0.6, dur=0.05), 0.65 + i * 0.03)
    place(y, strike(rng, bell_bank(hz(86), SHELL, 1.4), 1.0, dur=1.4, click_g=0.2), 0.95)
    sl = noise(rng, 0.3, 200, 3000, peaks=[(500, 300, 3)]) * adsr(N(0.3), 0.01, 0.05) * 0.5
    place(y, sl, 0.97)
    place(y, strike(rng, B_CABINET, 1.0, dur=0.3), 1.27)
    return y


@sound("ems_punch_clock", "Time recorder: card in, solenoid stamp, bell", "phrase", tags=["register", "bell"])
def _(rng):
    y = np.zeros(N(1.3))
    place(y, 0.4 * noise(rng, 0.1, 500, 6000) * adsr(N(0.1), 0.01, 0.05), 0)
    place(y, render_solenoid(rng, solenoid_sim(rng, on=0.05, pull=3e5), B_CONTACTOR, B_CONTACTOR_BACK,
                             B_CABINET), 0.15)
    place(y, 0.6 * strike(rng, bell_bank(hz(84), SHELL, 1.0), 1.0, dur=1.0), 0.25)
    return y


# ---- 4. pitched sources for instruments (modal, KS, FM, additive, ring mod, bitcrush)
@sound("ems_relay_mallet_c5", "Relay-struck steel bar: a relay armature as the mallet on a tuned free-free bar "
       "(C5)", "modal", tonal=True, root=72, tags=["tonal", "mallet"])
def _(rng):
    f = hz(72)
    bar = strike(rng, ([f * r for r in BAR_FREE], [1.8, 0.9, 0.5, 0.3], [1, .45, .25, .12]), 1.0, dur=2.5,
                 click_g=0.2, bright=0.8)
    y = np.zeros(len(bar))
    place(y, 0.4 * solenoid(rng, part="pull", on=0.05), 0)
    return y + bar


@sound("ems_relay_marimba_c4", "Relay-struck undercut wooden-ish bar (marimba ratios 1:4:10), C4", "modal",
       tonal=True, root=60, tags=["tonal", "mallet"])
def _(rng):
    f = hz(60)
    bar = strike(rng, ([f * r for r in BAR_TUNED] + [f * 0.5 * 1.01], [1.1, 0.4, 0.15, 0.6], [1, .35, .12, .2]),
                 1.0, dur=2.0, click_g=0.15, bright=0.6)
    y = np.zeros(len(bar))
    place(y, 0.25 * solenoid(rng, part="pull", on=0.05), 0)
    return y + bar


@sound("ems_ttybell_g5", "Teletype-bell keyboard source: shell bell tuned to G5, medium strike", "modal",
       tonal=True, root=79, tags=["tonal", "bell"])
def _(rng):
    return strike(rng, bell_bank(hz(79), SHELL, 2.0, amps=[1, .5, .3, .2, .1]), 1.0, dur=2.8, click_g=0.15)


@sound("ems_exchange_bell_c4", "Telephone ringer gong (subscriber set), single stroke, C4 church-like partials",
       "modal", tonal=True, root=60, tags=["tonal", "bell", "phone"])
def _(rng):
    return strike(rng, bell_bank(hz(60) * 2, CHURCH, 3.0, amps=[.4, 1, .6, .4, .7, .3, .2, .2, .1]), 1.0,
                  dur=3.5, click_g=0.2)


@sound("ems_phone_ring_trill", "Twin-gong telephone ringer: clapper trills at 20 Hz between two gongs (one ring)",
       "modal", kind="phrase", tags=["bell", "phone", "message"])
def _(rng):
    d = 2.0
    y = np.zeros(N(d + 1.0))
    g1, g2 = bell_bank(hz(84), SHELL, 1.2), bell_bank(hz(86.5), SHELL, 1.2)
    for i in range(int(d * 20)):
        place(y, 0.6 * strike(rng, g1 if i % 2 else g2, rng.uniform(0.6, 0.9), dur=0.8, click_g=0.3), i / 20)
    return y


@sound("ems_ks_spring_g3", "Karplus-Strong: a relay contact spring plucked (G3)", "ks", tonal=True, root=55,
       tags=["tonal", "pluck"])
def _(rng):
    y = ks(rng, hz(55), 2.5, loss=0.997, bright=0.7)
    return y + 0.3 * np.pad(click(rng), (0, len(y) - N(0.004)))


@sound("ems_ks_wire_c3", "Karplus-Strong: a long dial-governor spring, dark and buzzy (C3)", "ks", tonal=True,
       root=48, tags=["tonal", "pluck"])
def _(rng):
    y = ks(rng, hz(48), 3.0, loss=0.998, bright=0.3, pick=0.07)
    return np.tanh(2 * y)


@sound("ems_fm_register_bell_c6", "FM bell (1:1.4, decaying index): a cash-register drawer bell, C6", "fm",
       tonal=True, root=84, tags=["tonal", "bell"])
def _(rng):
    return fm(hz(84), 2.5, ratio=1.4, index=5.0, idx_t60=0.5, amp_t60=2.0)


@sound("ems_fm_sounder_c4", "FM: a hollow, clicking telegraph-sounder tone (1:3.5 ratio), C4", "fm", tonal=True,
       root=60, tags=["tonal"])
def _(rng):
    y = fm(hz(60), 2.0, ratio=3.5, index=3.0, idx_t60=0.15, amp_t60=1.2)
    y[:N(0.004)] += click(rng)[:N(0.004)] * 2
    return y


@sound("ems_fm_bell103_lead", "FM lead built on the Bell 103 mark/space pair (1070:1270 as carrier:modulator), "
       "root ~C6", "fm", tonal=True, root=None, tags=["tonal", "modem", "lead"])
def _(rng):
    t = tt(2.5)
    y = np.sin(2 * np.pi * 1070 * t + 1.5 * np.sin(2 * np.pi * 1270 * t)) * adsr(len(t), 0.01, 0.3)
    return line_band(y)


@sound("ems_motor_drone_c3", "Additive motor drone: 2x-mains hum plus rotation partials, tuned to C3", "additive",
       tonal=True, root=48, tags=["tonal", "motor", "drone"])
def _(rng):
    d = 4.0
    f = hz(48)
    return motor(rng, d, f / 4, f, f * 7, 0.15) * adsr(N(d), 0.2, 0.3)


@sound("ems_motor_whine_a4", "Additive high gear whine (tape and drum motors), A4 with slow speed hunting",
       "additive", tonal=True, root=69, tags=["tonal", "motor", "drone"])
def _(rng):
    d = 4.0
    t = tt(d)
    f = 440 * (1 + 0.004 * np.sin(2 * np.pi * 0.4 * t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph) + 0.1 * np.sin(0.25 * ph)
    return y * adsr(len(t), 0.3, 0.3) + 0.05 * noise(rng, d, 2000, 8000)


@sound("ems_ringmod_relay_bell", "Ring modulation: relay chatter multiplied by a 660 Hz carrier (metallic, "
       "clangorous)", "ringmod", tags=["ringmod"])
def _(rng):
    d = 1.5
    y = np.zeros(N(d))
    for i in range(10):
        place(y, strike(rng, B_RELAY_FRONT, rng.uniform(0.4, 1)), rng.uniform(0, 1.0))
    y += 0.3 * strike(rng, bell_bank(500, SHELL, 1.0), 1.0, dur=d)[:len(y)]
    return y * np.sin(2 * np.pi * 660 * tt(d))


@sound("ems_ringmod_dial_tone", "Ring modulation: dial tone x 30 Hz teletype shaft partial (warbling pad)",
       "ringmod", tonal=True, root=69, tags=["ringmod", "line", "tonal"])
def _(rng):
    d = 3.0
    return tones([350, 440], d) * (0.6 + 0.4 * np.sin(2 * np.pi * 30 * tt(d))) * \
        np.sin(2 * np.pi * 7.5 * tt(d))


@sound("ems_ferranti_hoot_c4", "Ferranti Mark 1 style 'hoot': square pulses with periods quantized to the "
       "machine's 240 us beat (nearest C4 is 16 beats, 260.4 Hz)", "bitcrush", tonal=True, root=60,
       tags=["tonal", "computer-music"])
def _(rng):
    d = 2.5
    per = 16 * 240e-6
    t = tt(d)
    y = np.where((t % per) < per * 0.5, 1.0, -1.0)
    y = specf(y, 80, 6000)
    return y * adsr(len(t), 0.005, 0.05)


@sound("ems_csirac_pulse_e4", "CSIRAC-style speaker pulses: one-sample clicks from a timing loop, crushed to "
       "4 bits (E4)", "bitcrush", tonal=True, root=64, tags=["tonal", "computer-music"])
def _(rng):
    d = 2.5
    y = np.zeros(N(d))
    per = 1 / hz(64)
    for i in range(int(d / per)):
        y[N(i * per)] = 1.0
    y = specf(y, 60, 5000, peaks=[(900, 600, 3)])
    return crush(norm(y), 4, 3)


@sound("ems_704_vowel_a3", "1961-style vocal-tract synthesis: buzz source through 'ah' formants (a nod to the "
       "IBM 7094 'Daisy Bell'), A3", "additive", tonal=True, root=57, tags=["tonal", "computer-music", "voice"])
def _(rng):
    d = 2.5
    t = tt(d)
    f = hz(57) * (1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.5))
    ph = np.cumsum(f) / SR
    src = 2 * (ph % 1) - 1
    y = specf(src, 60, None, peaks=[(730, 90, 20), (1090, 110, 10), (2440, 160, 5)])
    return crush(norm(y), 6, 2) * adsr(len(t), 0.06, 0.2)


@sound("ems_crushed_tty_bell", "Bitcrushed teletype bell (5 bits, sample-and-hold x6)", "bitcrush", tonal=True,
       tags=["bitcrush", "bell"])
def _(rng):
    return crush(norm(strike(rng, bell_bank(1480, SHELL, 1.6), 1.0, dur=2.0)), 5, 6)


@sound("ems_crushed_line_noise", "Bitcrushed line noise: hiss and hum through 3 bits (digital-trunk grit, loop)",
       "bitcrush", kind="loop", tags=["bitcrush", "line", "noise"])
def _(rng):
    d = 2.5
    return crush(norm(line_band(noise(rng, d)) + 0.5 * hum(d, 60, rng) * 0.3), 3, 5)


# ---- 5. hybrids: a recording plus a synthesized layer (need sources/electromech/em_*.wav built first)
def hybrid(rec_id, syn, rec_gain=1.0, syn_gain=1.0, offset=0.0):
    x = norm(load_conv(rec_id))
    n = max(len(x), N(offset) + len(syn))
    y = np.zeros(n)
    y[:len(x)] += rec_gain * x
    place(y, syn_gain * norm(syn), offset)
    return y


@sound("emh_relay_ping_e5", "Hybrid: a recorded relay click plus a tuned resonator ping (E5 steel bar)",
       "hybrid", tonal=True, root=76, parents=["em_relay_click_a"], tags=["tonal", "mallet", "hybrid"])
def _(rng):
    f = hz(76)
    return hybrid("em_relay_click_a", strike(rng, ([f * r for r in BAR_FREE], [1.5, .7, .4, .2], [1, .4, .2, .1]),
                                             1.0, dur=2.0, click_g=0.0), 1.0, 0.8, 0.001)


@sound("emh_crossbar_gong_c3", "Hybrid: recorded crossbar operation plus a struck-gong body at C3", "hybrid",
       tonal=True, root=48, parents=["em_crossbar_kissoff"], tags=["tonal", "hybrid"])
def _(rng):
    return hybrid("em_crossbar_kissoff", strike(rng, bell_bank(hz(48) * 2, CHURCH, 4.0), 1.0, dur=3.5,
                                                click_g=0.0), 1.0, 0.7)


@sound("emh_tty_bell_fm", "Hybrid: recorded teletype run under an FM bell (message alert)", "hybrid",
       parents=["em_tty_machine_loop"], tags=["hybrid", "message", "bell"])
def _(rng):
    return hybrid("em_tty_machine_loop", fm(hz(83), 2.0, 1.4, 4.0, 0.4, 1.5), 0.6, 0.8)


@sound("emh_typewriter_ks", "Hybrid: recorded typewriter key strike plus a plucked-spring KS tail (D4)",
       "hybrid", tonal=True, root=62, parents=["em_typewriter_key_a"], tags=["hybrid", "tonal", "pluck"])
def _(rng):
    return hybrid("em_typewriter_key_a", ks(rng, hz(62), 1.8, 0.996, 0.6), 1.0, 0.6, 0.003)


@sound("emh_dial_ring_mod", "Hybrid: recorded rotary dial ring-modulated with 220 Hz", "hybrid",
       parents=["em_rotary_dial_a"], tags=["hybrid", "ringmod", "dial"])
def _(rng):
    x = norm(load_conv("em_rotary_dial_a"))
    return x * np.sin(2 * np.pi * 220 * np.arange(len(x)) / SR) + 0.3 * x


@sound("emh_modem_crush", "Hybrid: recorded dial-up modem bitcrushed to 4 bits and mixed with mains hum",
       "hybrid", parents=["em_modem_dialup"], tags=["hybrid", "bitcrush", "line"])
def _(rng):
    x = norm(load_conv("em_modem_dialup"))
    return crush(x, 4, 4) + 0.15 * hum(len(x) / SR, 60, rng) * 0.3


@sound("emh_cardpunch_thump", "Hybrid: a recorded mechanical stamp on paper reinforced by the modelled punch-magnet "
       "thud (a card-punch stand-in)", "hybrid", parents=["em_stamp_a"], tags=["hybrid", "punch"])
def _(rng):
    y = render_solenoid(rng, solenoid_sim(rng, on=0.03, pull=3e5), B_PUNCH, B_RELAY_BACK, B_CABINET, thump=0.6)
    return hybrid("em_stamp_a", y, 0.8, 1.0)


@sound("emh_switchroom_drone", "Hybrid: recorded switchboard relays over an additive 50 Hz exchange-room drone",
       "hybrid", kind="loop", parents=["em_switchboard_relays"], tags=["hybrid", "drone", "switching"])
def _(rng):
    x = norm(load_conv("em_switchboard_relays"))
    d = len(x) / SR
    return x + 0.4 * norm(np.tanh(1.5 * hum(d, 50.0, rng, amps=[.3, 1, .5, .7, .3, .4, .2])))


# ------------------------------------------------------------------------------------------------- main
def seed_for(id):
    return zlib.crc32(id.encode()) & 0xFFFFFFFF


def write_wav(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    x = norm(specf(x - x.mean(), 25, None, order=2), 0.89)
    fo = min(len(x) // 4, N(0.01))
    if fo:
        x[-fo:] *= np.linspace(1, 0, fo)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.clip(np.round(x * 32767), -32768, 32767).astype("<i2").tobytes())


def entry(s, path):
    hyb = s["method"] == "hybrid"
    e = dict(id=s["id"], raw="electromech/synth/" + s["id"] + ".wav", category="electromech",
             description=s["desc"], tonal=bool(s["tonal"]), start=0, dur=None,
             origin="synth+recording" if hyb else "synth", synth_method=s["method"], seed=seed_for(s["id"]),
             kind=s["kind"], tags=s["tags"],
             source_url=TOOL_URL, author="BASILISK SYNTH library (synth_sources.py)",
             license=("CC0-1.0 (synthesized; parents are CC0/PD recordings)" if hyb else "CC0-1.0"),
             license_proof_url=TOOL_URL)
    if s["parents"]:
        e["parents"] = s["parents"]
    if s["root"] is not None:
        e["labelled_note"] = s["root"]
    if s["kind"] != "oneshot" and not s["tonal"]:
        e["no_trim"] = s["kind"] == "loop"
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None
    if a.list:
        for s in REG:
            print(f"{s['id']:30s} {s['method']:9s} {s['kind']:7s} {s['desc'][:70]}")
        return
    made = []
    for s in REG:
        if only and s["id"] not in only:
            continue
        miss = [p for p in s["parents"] if not os.path.exists(os.path.join(CONV, p + ".wav"))]
        if miss:
            print(f"skip {s['id']}: parent not built yet: {miss}", file=sys.stderr)
            continue
        rng = np.random.default_rng(seed_for(s["id"]))
        x = np.asarray(s["fn"](rng), float)
        p = os.path.join(RAWDIR, s["id"] + ".wav")
        write_wav(p, x)
        made.append(entry(s, p))
        print(f"ok  {s['id']:30s} {len(x) / SR:6.2f}s")
    cat = json.load(open(CATALOG)) if os.path.exists(CATALOG) else []
    ids = {e["id"] for e in made}
    cat = [e for e in cat if e["id"] not in ids] + made
    cat.sort(key=lambda e: (e.get("origin", "recording") != "recording", e["id"]))
    with open(CATALOG, "w") as f:
        json.dump(cat, f, indent=1, ensure_ascii=False)
    print(f"{len(made)} synthesized, catalog now {len(cat)} entries")


if __name__ == "__main__":
    main()
