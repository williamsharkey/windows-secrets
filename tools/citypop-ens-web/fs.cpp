// BASILISK 16 in the browser: the library disc (drive L:, library.zip, 107 MB) is read in pieces over HTTP when
// Windows reads it, so only the sounds a DNA uses are ever downloaded. It is a WasmFS JS-implemented file
// (lazyfile.js asks b16_lazy_chunk for each piece). A piece is fetched with a synchronous ranged XMLHttpRequest on
// the worker's own thread (Chrome refuses those requests from the engine's threads, and neither WasmFS's fetch
// backend nor Emscripten's proxying reach that thread from them: they ask it over a BroadcastChannel and wait on a
// shared flag), and kept in memory for every thread.
#include <emscripten.h>
#include <emscripten/wasmfs.h>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <mutex>

namespace {
char lazyUrl[1024];
uint32_t lazyVars[8] = {0, 262144, 0, 0, 0};   // size, chunk, pieces fetched, bytes fetched, channel token
uint8_t **pieces = nullptr; uint32_t *pieceLen = nullptr; uint32_t npieces = 0;
std::mutex mtx;
int32_t flag[2];   // [0]: 0 asked, 1 answered; [1]: bytes or -1
}

// fetch bytes [a, e] of the file into dst: here if this is the worker's own thread, else asked of it (lazyfile.js)
EM_JS(int, lazy_fetch, (uint8_t *dst, uint32_t a, uint32_t e, int32_t *flag), {
  return b16LazyFetch(dst, a, e, flag);
});
// on the worker's own thread: answer the engine threads' requests (returns the channel's token)
EM_JS(uint32_t, lazy_listen, (void), { return b16LazyListen(); });

extern "C" {
EMSCRIPTEN_KEEPALIVE char *b16_lazy_url() { return lazyUrl; }
EMSCRIPTEN_KEEPALIVE uint32_t *b16_lazy_vars() { return lazyVars; }

// path: where it appears (/machine/library.zip); url: its absolute URL; size: its length; chunk: bytes per request
EMSCRIPTEN_KEEPALIVE int b16_fetchfile(const char *path, const char *url, unsigned size, unsigned chunk)
{
    std::strncpy(lazyUrl, url, sizeof lazyUrl - 1);
    lazyVars[0] = size; if (chunk) lazyVars[1] = chunk;
    npieces = (size + lazyVars[1] - 1) / lazyVars[1];
    pieces = (uint8_t **)std::calloc(npieces, sizeof *pieces);
    pieceLen = (uint32_t *)std::calloc(npieces, sizeof *pieceLen);
    lazyVars[4] = lazy_listen();
    backend_t b = wasmfs_create_jsimpl_backend();
    return b && wasmfs_create_file(path, 0444, b) >= 0;
}

// piece i of the file (fetched now if it is not here yet); its length in *len. NULL if it cannot be had.
EMSCRIPTEN_KEEPALIVE uint8_t *b16_lazy_chunk(uint32_t i, uint32_t *len)
{
    std::lock_guard<std::mutex> l(mtx);
    if (i >= npieces) return nullptr;
    if (!pieces[i]) {
        const uint32_t a = i * lazyVars[1], e = (a + lazyVars[1] < lazyVars[0] ? a + lazyVars[1] : lazyVars[0]) - 1;
        uint8_t *dst = (uint8_t *)std::malloc(e - a + 1);
        const int n = lazy_fetch(dst, a, e, flag);
        if (n <= 0) { std::free(dst); return nullptr; }
        pieces[i] = dst; pieceLen[i] = (uint32_t)n;
        lazyVars[2]++; lazyVars[3] += (uint32_t)n;
    }
    *len = pieceLen[i];
    return pieces[i];
}

// the worker fetches pieces ahead of time (asynchronously, so the emulator never waits for them): piece i's bytes,
// copied in. 1: kept; 0: busy (a read holds the lock: try again later); -1: already here or out of range.
EMSCRIPTEN_KEEPALIVE int b16_lazy_put(uint32_t i, const uint8_t *src, uint32_t len)
{
    if (!mtx.try_lock()) return 0;
    int r = -1;
    if (i < npieces && !pieces[i]) {
        uint8_t *d = (uint8_t *)std::malloc(len);
        std::memcpy(d, src, len);
        pieces[i] = d; pieceLen[i] = len; lazyVars[2]++; lazyVars[3] += len; r = 1;
    }
    mtx.unlock();
    return r;
}
EMSCRIPTEN_KEEPALIVE int b16_lazy_has(uint32_t i) { return i < npieces && pieces[i] ? 1 : 0; }
}
