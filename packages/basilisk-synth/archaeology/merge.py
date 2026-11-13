#!/usr/bin/env python3
"""merge.py - one deduplicated catalog from the image scans and the prior research list.

    python3 merge.py --prior .../library/research/windows-sounds.json --out catalog.csv xp.csv w311.csv

Rules:
- One row per distinct sound per OS: byte-identical copies (dllcache, driver.cab, ServicePackFiles, the same file
  in two 3.11 trees) collapse into one row. `copies` counts them and `also_at` lists the other places. The row's
  `path` is the copy most likely to be on a user's disk (a loose file before a dllcache copy before a .cab member).
- A scanned sound that the prior list holds (same path, or same container + format + length) keeps the prior
  name, category, root, usefulness and DNA name, and gets status "prior". The rest get status "new".
- Prior entries that are not in our images stay in the catalog with status "prior, not in our images" and the
  prior measurements, so the catalog is the one list of every known Windows sound.
Only metadata: no audio, no Microsoft bytes.
"""
import argparse, csv, json, re, collections

OUT = ["id", "status", "os", "name", "path", "where", "offset", "bytes", "sha1", "kind", "format", "rate", "bits", "ch",
       "duration", "f0", "note", "clarity", "centroid", "attack_ms", "peak", "character", "decodable", "sndrec_xp",
       "sndrec_311", "root_midi", "loop", "copies", "also_at", "found_in", "category", "tonal", "root", "usefulness",
       "synth_class", "dna_name", "prior_character", "prior_os", "notes"]

LESS_LIKELY = ("\\dllcache\\", "\\servicepackfiles\\", "\\$ntuninstall", "\\$ntservicepackuninstall", "\\driver cache\\",
               "\\winsxs\\", "\\i386\\", "|", "\\pchealth\\helpctr\\binaries\\", "\\packagestore\\")


def rank(r):
    p = r["path"].lower()
    return (sum(1 for s in LESS_LIKELY if s in p), len(p))


def norm(p):
    p = (p or "").lower()
    return p[2:] if p[1:2] == ":" else p


def prior_index(prior):
    files, conts = {}, collections.defaultdict(list)
    for s in prior:
        for p in [s.get("path")] + (s.get("also_at") or []):
            if not p:
                continue
            q = norm(p)
            m = re.match(r"(.*?) \((embedded|wave resource) #(\d+)\)$", q)
            if m:
                conts[m.group(1)].append((int(m.group(3)), s))
            elif q not in files or (s.get("present_in_our_images") and not files[q].get("present_in_our_images")):
                files[q] = s   # several versions share a path (XP and Vista chimes.wav): prefer the one in our images
    return files, conts


DTMF = {601: "0", 602: "1", 603: "2", 604: "3", 605: "4", 606: "5", 607: "6", 608: "7", 609: "8", 610: "9", 611: "*",
        612: "#", 613: "A", 614: "B", 615: "C", 616: "D"}
LOW = {1: (697, 1209), 2: (697, 1336), 3: (697, 1477), 4: (770, 1209), 5: (770, 1336), 6: (770, 1477), 7: (852, 1209),
       8: (852, 1336), 9: (852, 1477), 0: (941, 1336)}
# names and notes checked by spectrum (two strongest partials) and envelope of the extracted sound
CURATED = {("tapi3.dll", "res WAVE/%d" % k): ("TAPI DTMF digit %s" % v, "dual tone (DTMF row + column frequencies); "
            "the autocorrelation note is not meaningful") for k, v in DTMF.items()}
CURATED.update({
    ("tapi3.dll", "res WAVE/617"): ("TAPI dial tone", "350 + 440 Hz (North American dial tone), 0.1 s: loop it"),
    ("tapi3.dll", "res WAVE/618"): ("TAPI busy tone", "480 + 620 Hz (busy / reorder), 0.1 s: loop it"),
    ("tapi3.dll", "res WAVE/619"): ("TAPI tone 619", ""),
    ("tapi3.dll", "res WAVE/620"): ("TAPI ringback tone", "440 + 480 Hz (ringback), 0.1 s: loop it"),
    ("tapi3.dll", "res WAVE/621"): ("TAPI tone 621", "1400 + 2060 + 2450 + 2600 Hz cluster, 0.1 s (off-hook / howler-like)"),
    ("tapi3.dll", "res WAVE/622"): ("TAPI tone 622", "0.9 s, partials 1285 / 1624 / 3368 Hz, decaying"),
    ("rtcdll.dll", "res WAVE/616"): ("RTC (Windows Messenger voice) blip", "60 ms, 800 + 2400 Hz"),
    ("rtcdll.dll", "res WAVE/617"): ("RTC (Windows Messenger voice) tone", "1.05 s, 593 / 889 / 1778 Hz (a fifth + octave)"),
    ("rtcdll.dll", "res WAVE/618"): ("RTC (Windows Messenger voice) tone", "0.4 s, 308 / 488 / 554 Hz"),
    ("rtcdll.dll", "res WAVE/619"): ("RTC ringback", "2.0 s, 440 + 480 Hz ringback"),
    ("clock.avi", "file (AVI audio stream: extract to open it)"):
        ("clock.avi alarm beeps", "TrueSpeech; 800 Hz beep once a second for 12 s (the XP clock animation)"),
    ("osk.exe", "res WAVE/179"): ("On-Screen Keyboard click", "57 ms key click"),
    ("osk.exe", "res WAVE/180"): ("On-Screen Keyboard click (short)", "31 ms key click"),
    ("osk.exe", "res WAVE/182"): ("On-Screen Keyboard tone", "0.25 s, harmonic 222 / 445 / 666 Hz (A3)"),
    ("dxdiagn.dll", "res WAVE/7000"): ("DirectX Diagnostic test sound", "dxdiag's DirectSound test, 1.6 s stereo"),
    ("srchui.dll", "res WAVE/101"): ("Search Companion sound", "MS ADPCM, 0.17 s"),
    ("mshearts.exe", "res WAVE/401"): ("Hearts 3.11 sound 401", "WfW 3.11 Hearts (network Hearts) resource"),
    ("mshearts.exe", "res WAVE/402"): ("Hearts 3.11 sound 402", "WfW 3.11 Hearts resource, 1.5 s"),
    ("msmail.exe", "res 1502/1031"): ("Mail 3.x new-mail sound", "WfW 3.11 Microsoft Mail, custom resource type 1502"),
})


def curated(r):
    hit = CURATED.get((r["path"].split("|")[0].split("\\")[-1].lower(), r["where"]))
    if hit:
        if hit[0]:
            r["name"] = hit[0]
        if hit[1]:
            r["notes"] = (hit[1] + "; " + r["notes"]) if r.get("notes") else hit[1]
    p = r["path"].lower()
    if "\\mmtour\\" in p:
        r["notes"] = "XP tour (mmTour) Flash sound: narration unless the character says tone/melody"
    if "msgrcore.cab" in p:
        r["notes"] = "MSN Messenger 6 (MSN 9 installer) version: 8-bit, different from Windows Messenger 4.7's file"
    if "driver.cab|ir_" in p:
        r["notes"] = "infrared file-transfer sound; only inside driver.cab (not installed loose on our image)"


def fmt_key(f):
    f = (f or "").lower().replace("ms-adpcm", "ms adpcm").replace("ima-adpcm", "ima adpcm")
    return re.sub(r"\s+", " ", f).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prior", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("scans", nargs="+")
    a = ap.parse_args()
    prior = json.load(open(a.prior))["sounds"]
    files, conts = prior_index(prior)
    rows = []
    for f in a.scans:
        rows += list(csv.DictReader(open(f)))
    # BASILISK's own working files and Sound Recorder's empty "New Sound" template are not sources
    rows = [r for r in rows if not norm(r["path"]).startswith("\\synth\\")
            and not (norm(r["path"]).endswith("sndrec.wav") and r.get("duration") in ("0.0", "0", ""))]
    # group byte-identical copies per OS
    groups = collections.OrderedDict()
    for r in rows:
        k = (r["source"], r.get("sha1") or r["id"], r["kind"])
        groups.setdefault(k, []).append(r)
    used = set()
    out = []
    for (src, sha, kind), g in groups.items():
        g.sort(key=rank)
        r = dict(g[0])
        r["os"] = src
        r["copies"] = len(g)
        r["also_at"] = " ; ".join(sorted({x["path"] + ("" if x["where"] == "file" else " [" + x["where"] + "]")
                                          for x in g[1:]}))[:600]
        r["found_in"] = ";".join(sorted({y for x in g for y in (x.get("found_in") or "").split(";") if y}))
        # prior match
        hit = None
        for x in g:
            p = norm(x["path"].split("|")[0])
            if x["where"] == "file" and "|" not in x["path"] and p in files:
                hit = files[p]; break
            if p in conts and kind == "wave":
                cands = [s for _, s in conts[p] if id(s) not in used]
                for s in cands:
                    try:
                        same_len = abs(float(s.get("duration") or -9) - float(x.get("duration") or 0)) < 0.02
                    except ValueError:
                        same_len = False
                    if same_len and fmt_key(s.get("format"))[:12] == fmt_key(x.get("format"))[:12]:
                        hit = s; break
                if hit:
                    break
            if kind == "media" and p in files:
                hit = files[p]; break
            if kind == "speech-voice" and p in files:
                hit = files[p]; break
        if kind == "dls-wave":
            r["status"] = "new (single instrument wave inside gm.dls; the prior list holds gm.dls as one entry)"
            m = re.search(r"dls-wave (.*)$", r["where"])
            r["name"] = "gm.dls: " + (m.group(1) if m else "?")
        elif hit is not None:
            used.add(id(hit))
            r["status"] = "prior"
            for k in ("name", "category", "tonal", "root", "usefulness", "synth_class", "dna_name"):
                r[k] = hit.get(k)
            r["prior_character"] = hit.get("character")
            r["prior_os"] = hit.get("os")
        else:
            r["status"] = "new"
            leaf = r["path"].split("\\")[-1]
            r["name"] = leaf + ("" if r["where"] == "file" else " (" + r["where"] + ")")
        if r["status"].startswith("new"):
            curated(r)
        if r.get("decodable") == "True" and not (r.get("sndrec_311") or "").startswith("yes"):
            r["sndrec_311"] = "after extract.py --target 311 (PCM mono, %s Hz to %s Hz)" % (
                r.get("rate") or "?", "11025" if r.get("rate") and int(r["rate"]) <= 11025 else "22050")
        if r.get("decodable") == "True" and not (r.get("sndrec_xp") or "").startswith("yes"):
            r["sndrec_xp"] = "after extract.py (PCM 16-bit)"
        out.append(r)
    # prior entries we did not see in our images
    n_prior_only = 0
    for i, s in enumerate(prior):
        if id(s) in used:
            continue
        if s.get("path", "").lower().endswith("gm.dls") and any(r["kind"] == "dls" for r in out):
            # gm.dls itself is in the scans as one "dls" row
            for r in out:
                if r["kind"] == "dls" and r["status"] != "prior":
                    r["status"] = "prior"; r["name"] = s.get("name"); r["category"] = s.get("category")
                    r["prior_character"] = s.get("character"); r["usefulness"] = s.get("usefulness")
            continue
        f = s.get("format") or ""
        pcm = f.upper().startswith("PCM")
        acm = any(t in f.upper() for t in ("ADPCM", "MP3", "GSM", "TRUESPEECH", "LAW"))
        rate = re.search(r"(\d{4,5}) Hz", f)
        std = rate and int(rate.group(1)) in (11025, 22050, 44100)
        out.append(dict(
            id="prior-%04d" % i, os="other" if not s.get("present_in_our_images") else ",".join(s["present_in_our_images"]),
            status="prior, not in our images" if not s.get("present_in_our_images") else
                   "prior, listed as in our images but not found by this scan",
            name=s.get("name"), path=s.get("path"), where="file", kind="wave" if ".wav" in (s.get("path") or "").lower() else "",
            format=f, duration=s.get("duration"), category=s.get("category"), tonal=s.get("tonal"), root=s.get("root"),
            usefulness=s.get("usefulness"), synth_class=s.get("synth_class"), dna_name=s.get("dna_name"),
            prior_character=s.get("character"), prior_os=s.get("os"),
            decodable="not in our images",
            sndrec_xp="yes" if pcm else "yes (ACM codec)" if acm else "no",
            sndrec_311="yes" if pcm and std and "8-bit" in f or pcm and std and "16-bit" in f else
                       "after conversion to PCM" if pcm or acm else "no",
            notes=s.get("distribution")))
        n_prior_only += 1
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, OUT, extrasaction="ignore"); w.writeheader(); w.writerows(out)
    c = collections.Counter((r["os"], r["kind"], r["status"].split(" (")[0]) for r in out)
    for k, v in sorted(c.items(), key=lambda kv: (str(kv[0]))):
        print("%5d  %s" % (v, " | ".join(map(str, k))))
    print("%d catalog rows (%d prior-only) -> %s" % (len(out), n_prior_only, a.out))


if __name__ == "__main__":
    main()
