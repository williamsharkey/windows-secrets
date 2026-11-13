#!/bin/sh
# Build the Windows 3.11 side with Open Watcom v2 (host cross-compile). Usage: build.sh OWDIR OUTDIR
set -e
OW=$1; OUT=$2; HERE=$(cd "$(dirname "$0")" && pwd)
export WATCOM=$OW PATH=$OW/binl64:$PATH INCLUDE=$OW/h:$OW/h/win
mkdir -p "$OUT"; cd "$OUT"
wcc -q $CFLAGS16 -bt=windows -bd -ml -zu -s -ox -zW -fo=bsynth.obj "$HERE/bsynth.c"
cat > bsynth.lnk <<LNK
system windows_dll
name BSYNTH.DRV
file bsynth.obj
library mmsystem.lib
option description 'wave:BASILISK 16 Wave (32 voices)'
option modname=BSYNTH
option quiet
segment type code fixed
segment type data fixed
export wodMessage, widMessage, DriverProc, BsPointer, WEP.1 resident
LNK
wlink @bsynth.lnk
wcc -q $CFLAGS16 -bt=windows -bd -ml -zu -s -ox -zW -fo=synhook.obj "$HERE/synhook.c"
cat > synhook.lnk <<LNK
system windows_dll
name SYNHOOK.DLL
file synhook.obj
option modname=SYNHOOK
option quiet
segment type code fixed
segment type data fixed
LNK
wlink @synhook.lnk
wcl -q $CFLAGS16 -bt=windows -l=windows -ml -k16384 -fe=SYNTH.EXE "$HERE/synth.c" mmsystem.lib shell.lib
