#!/usr/bin/env python3
"""Convert library/sources-raw/** into Sound-Recorder-friendly WAVs in library/sources/<category>/
and write library/sources/manifest.json.

Input: every library/catalog/<category>.json (a JSON list of entries made from fetch.py stubs):
  id, raw, category, description, tonal, start (s), dur (s or null), source_url, author, license,
  license_proof_url, optional: rate (22050|11025), channels (1|2), gain_db, no_trim, fade_out

Output format: PCM 16-bit, 22050 Hz (default) mono (default). Leading/trailing silence trimmed,
peak normalised to -1 dBFS, 10 ms fades. Max length: 15 s tonal, 30 s otherwise.
Tonal files get a root-note estimate (YIN over the steadiest part after the attack).

  python3 -I build_library.py [--only category] [--force]
"""
import argparse, glob, json, math, os, re, subprocess, sys, wave
import numpy as np

LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(LIB, "sources-raw")
OUT = os.path.join(LIB, "sources")
FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def decode(path, rate, ch, start, dur):
    cmd = [FFMPEG, "-v", "error"]
    if start:
        cmd += ["-ss", str(start)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-i", path, "-vn", "-ac", str(ch), "-ar", str(rate), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype="<f4").astype(np.float64)
    return x.reshape(-1, ch)


def trim_silence(x, rate, thresh_db=-50):
    env = np.abs(x).max(axis=1)
    peak = env.max() if len(env) else 0
    if peak <= 0:
        return x
    thr = peak * 10 ** (thresh_db / 20)
    idx = np.nonzero(env > thr)[0]
    a = max(0, idx[0] - int(0.002 * rate))
    b = min(len(x), idx[-1] + int(0.05 * rate))
    return x[a:b]


def yin_f0(x, rate, fmin=30.0, fmax=2000.0):
    """Median YIN f0 over frames from the sustain part; returns (hz, confidence) or (None, 0)."""
    mono = x.mean(axis=1)
    n = len(mono)
    if n < rate * 0.05:
        return None, 0.0
    env = np.abs(mono)
    pk = int(np.argmax(env))
    a = pk + int(0.04 * rate)                       # skip the attack transient
    seg = mono[a:a + int(1.5 * rate)]
    if len(seg) < 2048:
        seg = mono[:min(n, int(1.5 * rate))]
    W = 2048 if fmin >= 40 else 4096
    tmax = min(int(rate / fmin), W // 2)
    tmin = max(2, int(rate / fmax))
    est = []
    for s in range(0, max(1, len(seg) - W - tmax), W // 2):
        fr = seg[s:s + W + tmax]
        if len(fr) < W + tmax or np.sqrt(np.mean(fr ** 2)) < 1e-3:
            continue
        d = np.array([np.sum((fr[:W] - fr[t:t + W]) ** 2) for t in range(tmax)])
        cmnd = np.ones_like(d)
        cs = np.cumsum(d[1:])
        cmnd[1:] = d[1:] * np.arange(1, tmax) / np.maximum(cs, 1e-12)
        cand = np.nonzero(cmnd[tmin:] < 0.15)[0]
        if len(cand) == 0:
            continue
        t = cand[0] + tmin
        while t + 1 < tmax and cmnd[t + 1] < cmnd[t]:
            t += 1
        if 1 <= t < tmax - 1:                       # parabolic interpolation
            y0, y1, y2 = cmnd[t - 1], cmnd[t], cmnd[t + 1]
            den = y0 - 2 * y1 + y2
            tt = t + (0.5 * (y0 - y2) / den if den != 0 else 0)
        else:
            tt = t
        est.append((rate / tt, 1 - cmnd[t]))
    if not est:
        return None, 0.0
    est = [e for e in est if np.isfinite(e[0]) and fmin * 0.9 < e[0] < fmax * 1.1]
    if not est:
        return None, 0.0
    f = np.array([e[0] for e in est])
    midi = 69 + 12 * np.log2(f / 440.0)
    med = np.median(midi)
    if not np.isfinite(med):
        return None, 0.0
    good = np.abs(midi - med) < 0.5
    if not good.any():                              # no frame near the median (a spread of octaves): no estimate
        return None, 0.0
    cs_ = np.array([e[1] for e in est], dtype=float)
    cs_ = cs_[np.isfinite(cs_)]
    conf = float(good.mean() * cs_.mean()) if len(cs_) else 0.0
    hz = float(440.0 * 2 ** ((np.median(midi[good]) - 69) / 12))
    if not (math.isfinite(hz) and math.isfinite(conf)):
        return None, 0.0
    return hz, conf


def fft_peak(x, rate, fmin=60.0, fmax=6000.0):
    """Strongest spectral peak in the 250 ms after the loudest sample; returns (hz, prominence)."""
    mono = x.mean(axis=1)
    i = int(np.argmax(np.abs(mono)))
    seg = mono[i:i + int(0.25 * rate)]
    if len(seg) < 512:
        seg = mono[:4096]
    if len(seg) < 256:
        return None, 0.0
    n = 1 << 16
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    f = np.fft.rfftfreq(n, 1 / rate)
    band = (f > fmin) & (f < fmax)
    k = int(np.argmax(S * band))
    prom = float(S[k] / (np.median(S[band]) + 1e-12))
    if not math.isfinite(prom):
        return None, 0.0
    return (float(f[k]), prom) if prom > 20 else (None, prom)


def note_name(hz):
    m = 69 + 12 * math.log2(hz / 440.0)
    r = int(round(m))
    return f"{NOTES[r % 12]}{r // 12 - 1}", r, round((m - r) * 100, 1)


def write_wav(path, x, rate, bits):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if bits == 8:
        data = np.clip(np.round(x * 127 + 128), 0, 255).astype(np.uint8).tobytes()
    else:
        data = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(x.shape[1])
        w.setsampwidth(bits // 8)
        w.setframerate(rate)
        w.writeframes(data)


def build(e):
    rate = int(e.get("rate", 22050))
    ch = int(e.get("channels", 1))
    bits = int(e.get("bits", 16))
    maxlen = 15.0 if e.get("tonal") else 30.0
    dur = e.get("dur")
    dur = min(dur, maxlen) if dur else maxlen + 5
    x = decode(os.path.join(RAW, e["raw"]), rate, ch, e.get("start") or 0, dur)
    if not e.get("no_trim"):
        x = trim_silence(x, rate)
    if len(x) > maxlen * rate:
        x = x[:int(maxlen * rate)]
    x = x - x.mean(axis=0)                          # DC
    pk = np.abs(x).max()
    if pk > 0:
        x = x / pk * 10 ** ((-1 + e.get("gain_db", 0)) / 20)
    fi = min(len(x) // 4, int(0.003 * rate))
    fo = min(len(x) // 4, int(e.get("fade_out", 0.01) * rate))
    if fi:
        x[:fi] *= np.linspace(0, 1, fi)[:, None]
    if fo:
        x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    rel = os.path.join(e["category"], e["id"] + ".wav")
    write_wav(os.path.join(OUT, rel), x, rate, bits)
    m = dict(file=rel, category=e["category"], description=e.get("description", ""),
             tonal=bool(e.get("tonal")), est_root_note=None, duration=round(len(x) / rate, 3),
             source_url=e["source_url"], author=e.get("author", "unknown"), license=e["license"],
             license_proof_url=e["license_proof_url"])
    if e.get("tonal"):
        hz, conf = yin_f0(x, rate)
        if hz and math.isfinite(hz) and hz > 0:
            nm, midi, cents = note_name(hz)
            m.update(est_root_note=nm, est_root_midi=midi, est_root_hz=round(hz, 2),
                     est_root_cents=cents, pitch_confidence=round(conf, 2), pitch_method="yin")
        else:
            hz, prom = fft_peak(x, rate)            # short/gliding sounds (drips, taps): spectral peak
            if hz and math.isfinite(hz) and hz > 0:
                nm, midi, cents = note_name(hz)
                m.update(est_root_note=nm, est_root_midi=midi, est_root_hz=round(hz, 2),
                         est_root_cents=cents, pitch_confidence=round(min(1.0, prom / 500), 2),
                         pitch_method="fft_peak")
        if e.get("labelled_note"):
            m["labelled_note"] = e["labelled_note"]
    for k in [k for k, v in m.items() if isinstance(v, float) and not math.isfinite(v)]:
        m[k] = None                                 # never write NaN/inf into the manifest (JSON has no NaN)
    m.update(sample_rate=rate, bits=bits, channels=ch, bytes=os.path.getsize(os.path.join(OUT, rel)),
             raw_file="sources-raw/" + e["raw"], raw_sha256=e.get("raw_sha256"),
             download_url=e.get("download_url"))
    for k in ("note", "excerpt_start", "excerpt_dur", "license_url", "origin", "kind", "tags", "parents",
              "synth_method", "seed"):
        if e.get(k) is not None:
            m[k] = e[k]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--no-manifest", action="store_true", help="convert only; leave manifest.json alone")
    a = ap.parse_args()
    entries = []
    for p in sorted(glob.glob(os.path.join(LIB, "catalog", "*.json"))):
        with open(p) as f:
            entries += json.load(f)
    if a.only:
        entries = [e for e in entries if e["category"] == a.only]
    ids = {}
    for e in entries:
        k = (e["category"], e["id"])
        if k in ids:
            sys.exit(f"duplicate id {k}")
        if not re.fullmatch(r"[a-z0-9_]+", e["id"]):
            # a DNA NAME is [a-z0-9_]+ (DNA.md 5.2): '#' is the pool gene, so c# is written cs (piano_upright_cs4)
            sys.exit(f"id {e['id']!r} is not DNA-safe: use [a-z0-9_] only (write sharps as s: c# -> cs)")
        ids[k] = 1
    mpath = os.path.join(OUT, "manifest.json")
    old = []
    if a.only and os.path.exists(mpath):
        old = [m for m in json.load(open(mpath))["files"] if m["category"] != a.only]
    out = []
    for e in entries:
        try:
            out.append(build(e))
            m = out[-1]
            print(f"ok  {m['file']:60s} {m['duration']:6.2f}s {m.get('est_root_note') or ''}")
        except Exception as ex:
            print(f"ERR {e.get('category')}/{e.get('id')}: {ex}", file=sys.stderr)
    if a.no_manifest:
        return
    files = sorted(old + out, key=lambda m: m["file"])
    cats = {}
    for m in files:
        c = cats.setdefault(m["category"], dict(count=0, bytes=0, seconds=0.0))
        c["count"] += 1; c["bytes"] += m["bytes"]; c["seconds"] = round(c["seconds"] + m["duration"], 2)
    lic = {}
    for m in files:
        lic[m["license"]] = lic.get(m["license"], 0) + 1
    with open(mpath, "w") as f:
        json.dump(dict(version=1, format="PCM WAV, 16-bit, 22050 Hz unless noted per file",
                       totals=dict(files=len(files), bytes=sum(m["bytes"] for m in files)),
                       categories=cats, licenses=lic, files=files), f, indent=1, ensure_ascii=False)
    print(json.dumps(dict(categories=cats, licenses=lic), indent=1))


if __name__ == "__main__":
    main()
