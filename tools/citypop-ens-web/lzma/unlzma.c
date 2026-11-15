/* The page's snapshot comes packed (.lzma, `xz --format=lzma`: its many copies of the same sounds, one per recorder,
   cost little); the worker unpacks it here, in the engine's own memory (worker-main.js). */
#include <emscripten.h>
#include <stdlib.h>
#include "LzmaDec.h"
static void *lzAlloc(ISzAllocPtr p, size_t n) { (void)p; return malloc(n); }
static void lzFree(ISzAllocPtr p, void *q) { (void)p; free(q); }
EMSCRIPTEN_KEEPALIVE long ens_unlzma_size(const unsigned char *src) { unsigned long long n = 0; int i; for (i = 0; i < 8; i++) n |= (unsigned long long)src[5 + i] << (8 * i); return (long)n; }
EMSCRIPTEN_KEEPALIVE long ens_unlzma(const unsigned char *src, long n, unsigned char *dst, long dstCap)
{
    ISzAlloc a; SizeT outLen = (SizeT)dstCap, inLen; ELzmaStatus st; SRes r;
    if (n < 13) return -1;
    a.Alloc = lzAlloc; a.Free = lzFree; inLen = (SizeT)(n - 13);
    r = LzmaDecode(dst, &outLen, src + 13, &inLen, src, 5, LZMA_FINISH_ANY, &st, &a);
    return r == SZ_OK ? (long)outLen : -1;
}
