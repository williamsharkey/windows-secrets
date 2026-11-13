#!/bin/sh
# Link the BASILISK 16 web engine: DOSBox Pure + BSYN (core.mk), the plugin's engine thread (web_engine.c), the
# shared core (DNA, voices) and the web host (host.cpp).   link.sh SRC OBJ OUT
#   SRC: a tree with packages/basilisk-synth-311 and packages/basilisk-synth/core (the repo, or a git archive of it)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=${1:?src}; OBJ=${2:?obj}; OUT=${3:?out}
mkdir -p "$OUT"
P=$SRC/packages/basilisk-synth-311; C=$SRC/packages/basilisk-synth/core
CF="-O3 -pthread -fwasm-exceptions -I$P/engine -I$C"
emcc $CF -c "$HERE/web_engine.c" -o "$OBJ/web_engine.o"
em++ $CF -std=c++17 -c "$HERE/host.cpp" -o "$OBJ/host.o"
em++ $CF -std=c++17 -c "$C/dna.cpp" -o "$OBJ/dna.o"
em++ $CF -std=c++17 -c "$C/voices.cpp" -o "$OBJ/voices.o"
em++ $CF -std=c++17 -c "$HERE/fs.cpp" -o "$OBJ/fs.o"
em++ -O3 -pthread -fwasm-exceptions -sWASMFS -sFORCE_FILESYSTEM \
  -sMODULARIZE -sEXPORT_NAME=B16Module -sENVIRONMENT=worker,node \
  -sPTHREAD_POOL_SIZE=6 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=192MB -sMAXIMUM_MEMORY=2GB -sSTACK_SIZE=1MB \
  -sDEFAULT_PTHREAD_STACK_SIZE=2MB -sEXIT_RUNTIME=0 -sINCOMING_MODULE_JS_API=ENVIRONMENT,arguments,instantiateWasm,locateFile,monitorRunDependencies,noExitRuntime,noInitialRun,onAbort,onExit,onRuntimeInitialized,postRun,preInit,preRun,print,printErr,setStatus,thisProgram,wasm,wasmBinary \
  -sEXPORTED_FUNCTIONS=_b16_start,_b16_shm,_b16_layout,_b16_tick,_b16_midi,_b16_dna,_b16_mouse,_b16_button,_b16_key,_b16_rel,_b16_relscale,_b16_pause,_b16_grant,_b16_snapshot,_b16_stop,_b16_layer,_b16_info,_b16_frame,_b16_fetchfile,_b16_lazy_url,_b16_lazy_vars,_b16_lazy_chunk,_b16_lazy_put,_b16_lazy_has,_malloc,_free \
  -sEXPORTED_RUNTIME_METHODS=FS,ccall,cwrap,UTF8ToString,stringToNewUTF8,wasmMemory,HEAPU8,HEAPU32 \
  "$OBJ/web_engine.o" "$OBJ/host.o" "$OBJ/dna.o" "$OBJ/voices.o" "$OBJ/fs.o" "$OBJ/libdbp.a" --post-js "$HERE/lazyfile.js" --extern-post-js "$HERE/worker-main.js" -o "$OUT/b16-worker.js" $LINKEXTRA
ls -la "$OUT"
