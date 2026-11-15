#!/bin/sh
# Link the Ensemble album player for the web: DOSBox Pure + the lane card (core.mk, OBJ), the plugin's engine thread
# (web_engine.c), the shared core and the album player (ens_host.cpp).   link.sh REPO OBJ OUT
#   REPO: a tree with packages/basilisk-synth-311 (its ensemble/ folder) and packages/basilisk-synth/core
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${1:?repo}; OBJ=${2:?obj}; OUT=${3:?out}
mkdir -p "$OUT"
P=$SRC/packages/basilisk-synth-311; C=$SRC/packages/basilisk-synth/core
# a DAC ring of 10.9 s (the plugin's is 1.37 s): the music is known ahead, so the emulator runs seconds ahead of the audio
RING=-DBSHM_RING=524288
CF="-O3 -pthread -fwasm-exceptions $RING -I$P/engine -I$C -I$P/plugin -I$P/ensemble/player"
emcc $CF -c "$HERE/web_engine.c" -o "$OBJ/web_engine.o"
em++ $CF -std=c++17 -c "$HERE/ens_host.cpp" -o "$OBJ/ens_host.o"
CORE=""
for u in SharedCore SharedCore3Dna SharedCore3Engine SharedCore3Recipe SharedCore3Scales SharedUserstore; do
  [ -f "$P/plugin/$u.cpp" ] || continue
  em++ $CF -std=c++17 -c "$P/plugin/$u.cpp" -o "$OBJ/$u.o"; CORE="$CORE $OBJ/$u.o"
done
em++ $CF -std=c++17 -c "$HERE/fs.cpp" -o "$OBJ/fs.o"
em++ -O3 -pthread -fwasm-exceptions -sWASMFS -sFORCE_FILESYSTEM \
  -sMODULARIZE -sEXPORT_NAME=EnsModule -sENVIRONMENT=worker,node \
  -sPTHREAD_POOL_SIZE=6 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=256MB -sMAXIMUM_MEMORY=2GB -sSTACK_SIZE=1MB \
  -sDEFAULT_PTHREAD_STACK_SIZE=2MB -sEXIT_RUNTIME=0 -sINCOMING_MODULE_JS_API=ENVIRONMENT,arguments,instantiateWasm,locateFile,monitorRunDependencies,noExitRuntime,noInitialRun,onAbort,onExit,onRuntimeInitialized,postRun,preInit,preRun,print,printErr,setStatus,thisProgram,wasm,wasmBinary \
  -sEXPORTED_FUNCTIONS=_ens_start,_ens_shm,_ens_layout,_ens_tick,_ens_quiet,_ens_album,_ens_play,_ens_stop,_ens_colors,_ens_pos,_ens_emutime,_ens_mouse,_ens_button,_ens_key,_ens_pause,_ens_grant,_ens_snapshot,_ens_frame,_ens_info,_ens_stats,_b16_fetchfile,_b16_lazy_url,_b16_lazy_vars,_b16_lazy_chunk,_b16_lazy_put,_b16_lazy_has,_malloc,_free \
  -sEXPORTED_RUNTIME_METHODS=FS,ccall,cwrap,UTF8ToString,stringToNewUTF8,wasmMemory,HEAPU8,HEAPU32 \
  "$OBJ/web_engine.o" "$OBJ/ens_host.o" $CORE "$OBJ/fs.o" "$OBJ/libdbp.a" --post-js "$HERE/lazyfile.js" --extern-post-js "$HERE/worker-main.js" -o "$OUT/ens-worker.js" $LINKEXTRA
ls -la "$OUT"
