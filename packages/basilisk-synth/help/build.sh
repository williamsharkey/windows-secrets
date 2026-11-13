#!/bin/sh
# Builds the two help files from help.txt (Python 3 only; no Microsoft tools).
#   build.sh [OUTDIR]     default: out/
#   BSYNTH.HLP   for Windows XP  (winhlp32.exe), BASILISK SYNTH
#   BASIL16.HLP  for Windows 3.11 (WINHELP.EXE), BASILISK 16
# Also writes bsynth.rtf, basil16.rtf (the topic files), helpmap.txt ([MAP] for hlpc) and helpids.h (for the guests).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$HERE/out}
mkdir -p "$OUT"
# a fixed build date, so the same sources give the same bytes
[ -n "$SOURCE_DATE_EPOCH" ] || SOURCE_DATE_EPOCH=$(git -C "$HERE" log -1 --format=%ct -- . 2>/dev/null)
export SOURCE_DATE_EPOCH
python3 "$HERE/mkrtf.py" "$HERE/help.txt" xp "$HERE/bsynth.rtf" "$HERE/helpmap.txt" "$HERE/helpids.h"
python3 "$HERE/mkrtf.py" "$HERE/help.txt" 311 "$HERE/basil16.rtf"
python3 "$HERE/hlpc.py" "$HERE/bsynth.hpj" -o "$OUT/BSYNTH.HLP"
python3 "$HERE/hlpc.py" "$HERE/basil16.hpj" -o "$OUT/BASIL16.HLP"
