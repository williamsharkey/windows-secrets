#!/bin/bash
# Build BASILISK 16's web edition ("Try it online" on sndrec.html) from source, on Linux/WSL with Emscripten.
#   XPSOUNDS=DIR|drive.zip tools/basilisk16-web/build.sh WORKDIR [LIBRARY_DIR]
# WORKDIR gets the sources (a git archive of HEAD), DOSBox Pure + BSYN as WebAssembly, the guest (Open Watcom),
# the slim C: drive, the snapshot (made by the web engine itself, under node) and the site files in WORKDIR/site.
# LIBRARY_DIR: library.zip and library.names.txt as in the BASILISK 16 release (packages/basilisk-synth-311/tools/
# make_library311.py makes them); default WORKDIR. XPSOUNDS: XP's sounds for C:\XPSOUNDS (see make_drive.py): the
# folder from packages/basilisk-synth-311/tools/xpsounds311.py, or the plugin's machine/drive.zip. Needs: emsdk (~/emsdk), node 22, python3 with Pillow, git, gh.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
W=${1:?workdir}; mkdir -p "$W"; W=$(cd "$W" && pwd)
LIB=${2:-$W}
NODE=${NODE:-node}
source "${EMSDK:-$HOME/emsdk}/emsdk_env.sh" >/dev/null 2>&1

# --- sources: this repository at HEAD, DOSBox Pure at the plugin's commit with the plugin's patch and card
rm -rf "$W/src"; mkdir -p "$W/src"
git -C "$REPO" archive HEAD packages/basilisk-synth-311 packages/basilisk-synth/core | tar -x -C "$W/src"
git -C "$REPO" rev-parse HEAD > "$W/srcrev.txt"
P=$W/src/packages/basilisk-synth-311
[ -d "$W/dbp" ] || { git clone -q https://codeberg.org/schelling/dosbox-pure.git "$W/dbp"; (cd "$W/dbp" && git checkout -q "$(cat "$P/dosbox-pure/UPSTREAM.txt")" && git apply "$P/dosbox-pure/dosbox-pure.patch"); }
cp "$P/dosbox-pure/bsynth.cpp" "$W/dbp/src/hardware/bsynth.cpp"
[ -d "${OW:=$W/ow}" ] || { mkdir -p "$OW"; (cd "$OW" && gh release download Current-build -R open-watcom/open-watcom-v2 -p ow-snapshot.tar.xz && tar xf ow-snapshot.tar.xz && rm ow-snapshot.tar.xz); }

# --- the guest, the C: drive (only what Windows uses: drive-keep.txt), the engine
sh "$P/guest/build.sh" "$OW" "$W/gout" 2>&1 | grep -iv "already been exported" | grep -i "error" || true
git -C "$REPO" show HEAD:site/basilisk-31-browser/w31.jsdos > "$W/w31.jsdos"
python3 "$HERE/make_drive.py" "$W/w31.jsdos" "$W/gout" "$P" "$W/machine" --keep "$HERE/drive-keep.txt" ${XPSOUNDS:+--xpsounds "$XPSOUNDS"}
make -s -f "$HERE/core.mk" DBP="$W/dbp" OUT="$W/obj" -j"$(nproc)"
bash "$HERE/link.sh" "$W/src" "$W/obj" "$W/out" 2>&1 | grep -v "pthread + ALLOW_MEMORY_GROWTH" || true

# --- the snapshot: boot, assemble, build the default DNA, freeze (and the screen at that moment: the poster)
"$NODE" "$HERE/make_snapshot.cjs" "$W/out" "$W/machine" "$LIB/library.zip" "$LIB/library.names.txt" | tail -2
python3 "$HERE/stage.py" "$W" "$LIB" "$W/site"
