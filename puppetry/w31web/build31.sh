#!/bin/bash
# build31.sh WORKDIR : BASILISK 3.11 on the DOSBox Pure web engine, from source, into site/basilisk-31-browser/web.
#   1 BASILISK.EXE from puppetry/w31suite (Open Watcom; OW=dir, or on sharkey-server with SSH=host)
#   2 the engine: link.sh (needs emsdk and libdbp.a from tools/basilisk16-web/core.mk: LIBDBP=dir)
#   3 C: from the last js-dos bundle's tree (git: site/basilisk-31-browser/w31.jsdos at JSDOS_REV)
#   4 the snapshot (make_snapshot31.cjs, node 22+), then stage31.py
set -e
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../.." && pwd)
W=${1:?workdir}; mkdir -p "$W/out"; W=$(cd "$W" && pwd)
LIBDBP=${LIBDBP:-$HOME/b16web/obj}; NODE=${NODE:-node}; JSDOS_REV=${JSDOS_REV:-5b29743}
if [ -n "$OW" ]; then
  (cd "$REPO/puppetry/w31suite" && WATCOM=$OW PATH=$OW/binl64:$PATH INCLUDE=$OW/h:$OW/h/win wcl -q -bt=windows -l=windows -ml -k16384 -fe="$W/BASILISK.EXE" basilisk.c)
else
  H=${SSH:-root@165.227.95.55}
  scp -q "$REPO/puppetry/w31suite/basilisk.c" "$REPO/puppetry/w31suite/parts.c" $H:/root/w31/labboot/
  ssh -n $H 'cd /root/w31/labboot && export WATCOM=/root/w31/dl/ow PATH=/root/w31/dl/ow/binl64:$PATH INCLUDE=/root/w31/dl/ow/h:/root/w31/dl/ow/h/win && rm -f basilisk.exe && wcl -q -bt=windows -l=windows -ml -k16384 basilisk.c >/dev/null && ls basilisk.exe >/dev/null'
  scp -q $H:/root/w31/labboot/basilisk.exe "$W/BASILISK.EXE"
fi
source "${EMSDK:-$HOME/emsdk}/emsdk_env.sh" >/dev/null 2>&1
[ -f "$W/out/b31-worker.wasm" -a -z "$RELINK" ] || bash "$HERE/link.sh" "$REPO" "$LIBDBP" "$W/out" >/dev/null
git -C "$REPO" show "$JSDOS_REV:site/basilisk-31-browser/w31.jsdos" > "$W/w31.jsdos"
python3 "$HERE/make_drive31.py" "$W/w31.jsdos" "$W/BASILISK.EXE" "$REPO/puppetry/w31suite" "$W/drive0.bin.gz"
"$NODE" "$HERE/make_snapshot31.cjs" "$W/out" "$W/drive0.bin.gz" "$HERE/w31.conf" | tail -1
python3 "$HERE/stage31.py" "$W/out" "$REPO/site"
