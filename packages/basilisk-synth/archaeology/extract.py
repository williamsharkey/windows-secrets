#!/usr/bin/env python3
"""extract.py - first-use extraction of the cataloged Windows sounds from YOUR OWN image.

No Microsoft audio is in this repository. At first use, this reads the user's XP or Windows 3.11 disk image (qcow2,
raw), drive folder or drive .zip/.jsdos, finds each sound of catalog.csv by path + place + offset, checks its sha1,
decodes it and writes a plain PCM WAV that the target Sound Recorder opens.

    python3 extract.py SOURCE --os xp   --out DIR                # every XP sound, for XP Sound Recorder
    python3 extract.py SOURCE --os w311 --out DIR --target 311   # every 3.11 sound, for 3.11 Sound Recorder
    python3 extract.py SOURCE --os xp   --out DIR --target both  # DIR/xp and DIR/311
    python3 extract.py SOURCE --ids picks.txt --out DIR          # only the ids in picks.txt ("ID [NAME]" lines)

Targets:
    xp   PCM 16-bit, the source rate and channels (XP's Sound Recorder opens any PCM rate).
    311  PCM mono, 8- or 16-bit (--bits, default 16), 11025 Hz for sources at or below 11025 Hz, else 22050 Hz.

Options: --loop-seconds S (DLS loop samples: attack + loop repeated to S s), --max-seconds S (cut long music),
--force (write even when the sha1 differs: another Windows build), --report CSV.
Needs: numpy; dissect.ntfs dissect.fat dissect.hypervisor for disk images; pefile; ffmpeg (WMA, MP3 in Flash,
TrueSpeech); cabextract (driver.cab members); 7z (CHM/MSI members).
"""
import argparse, os, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sound_archaeology as sa

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--catalog", default=os.path.join(HERE, "catalog.csv"))
    ap.add_argument("--os", choices=("xp", "w311"), help="which catalog rows (default: from --target)")
    ap.add_argument("--target", choices=("xp", "311", "both"), default="xp")
    ap.add_argument("--bits", type=int, choices=(8, 16), default=16)
    ap.add_argument("--ids"); ap.add_argument("--out", required=True)
    ap.add_argument("--loop-seconds", type=float, default=0.0); ap.add_argument("--max-seconds", type=float, default=0.0)
    ap.add_argument("--force", action="store_true"); ap.add_argument("--report")
    ap.add_argument("--no-verify", action="store_true", help="skip the header check of the written files")
    a = ap.parse_args()
    targets = ("xp", "311") if a.target == "both" else (a.target,)
    for t in targets:
        out = os.path.join(a.out, t) if len(targets) > 1 else a.out
        ns = types.SimpleNamespace(sources=a.sources, csv=a.catalog, ids=a.ids, out=out, loop_seconds=a.loop_seconds,
                                   native=False, target=t, bits=a.bits if t == "311" else 16,
                                   source=a.os or ("w311" if t == "311" else "xp"), force=a.force,
                                   max_seconds=a.max_seconds, report=(a.report and (a.report if len(targets) == 1
                                                                      else a.report.replace(".csv", "-%s.csv" % t))))
        sa.cmd_extract(ns)
        if not a.no_verify:
            verify(out, t)


def verify(d, target):
    """Check every written WAV against what the target Sound Recorder accepts."""
    import struct
    ok = bad = 0
    for n in sorted(os.listdir(d)):
        if not n.lower().endswith(".wav"):
            continue
        b = open(os.path.join(d, n), "rb").read()
        why = None
        if b[:4] != b"RIFF" or b[8:16] != b"WAVEfmt " or struct.unpack("<I", b[4:8])[0] != len(b) - 8:
            why = "bad RIFF header"
        else:
            tag, ch, rate, avg, align, bits = struct.unpack("<HHIIHH", b[20:36])
            dlen = struct.unpack("<I", b[40:44])[0]
            if b[36:40] != b"data" or 44 + dlen > len(b):
                why = "bad data chunk"
            elif tag != 1:
                why = "not PCM"
            elif avg != rate * align or align != ch * bits // 8:
                why = "inconsistent fmt"
            elif target == "311" and (ch != 1 or bits not in (8, 16) or rate not in (11025, 22050)):
                why = "not 3.11 ready (%d ch, %d-bit, %d Hz)" % (ch, bits, rate)
            elif target == "xp" and (ch not in (1, 2) or bits not in (8, 16)):
                why = "not XP ready"
        if why:
            bad += 1; print("verify: %s: %s" % (n, why), file=sys.stderr)
        else:
            ok += 1
    print("verify %s: %d ok, %d bad" % (target, ok, bad))
    return bad == 0


if __name__ == "__main__":
    main()
