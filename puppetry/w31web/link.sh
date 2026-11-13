#!/bin/sh
# Link BASILISK 3.11's web engine: DOSBox Pure + the BSYN card (libdbp.a, built by tools/basilisk16-web/core.mk
# from the plugin's patched DOSBox Pure), the plugin's engine thread (web_engine.c, copied from the web lane) and
# host31.cpp.   link.sh REPO LIBDBP_DIR OUT
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=${1:?repo}; OBJ=${2:?dir with libdbp.a}; OUT=${3:?out}
mkdir -p "$OUT" "$OUT/obj"
E=$REPO/packages/basilisk-synth-311/engine
CF="-O3 -pthread -fwasm-exceptions -I$E"
emcc $CF -c "$HERE/web_engine.c" -o "$OUT/obj/web_engine.o"
em++ $CF -std=c++17 -c "$HERE/host31.cpp" -o "$OUT/obj/host31.o"
em++ -O3 -pthread -fwasm-exceptions -sWASMFS -sFORCE_FILESYSTEM \
  -sMODULARIZE -sEXPORT_NAME=B31Module -sENVIRONMENT=worker,node \
  -sPTHREAD_POOL_SIZE=4 -sALLOW_MEMORY_GROWTH=1 -sINITIAL_MEMORY=192MB -sMAXIMUM_MEMORY=2GB -sSTACK_SIZE=1MB \
  -sDEFAULT_PTHREAD_STACK_SIZE=2MB -sEXIT_RUNTIME=0 -sINCOMING_MODULE_JS_API=ENVIRONMENT,arguments,instantiateWasm,locateFile,monitorRunDependencies,noExitRuntime,noInitialRun,onAbort,onExit,onRuntimeInitialized,postRun,preInit,preRun,print,printErr,setStatus,thisProgram,wasm,wasmBinary \
  -sEXPORTED_FUNCTIONS=_b31_start,_b31_shm,_b31_dac_off,_b31_send,_b31_tick,_b31_mouse,_b31_button,_b31_relscale,_b31_key,_b31_grant,_b31_pause,_b31_snapshot,_b31_stop,_b31_frame,_b31_info,_malloc,_free \
  -sEXPORTED_RUNTIME_METHODS=FS,ccall,cwrap,UTF8ToString,stringToNewUTF8,wasmMemory,HEAPU8,HEAPU32 \
  "$OUT/obj/web_engine.o" "$OUT/obj/host31.o" "$OBJ/libdbp.a" --extern-post-js "$HERE/worker31.js" -o "$OUT/b31-worker.js" 2>&1 | grep -v "pthread + ALLOW_MEMORY_GROWTH" || true
ls -la "$OUT"
