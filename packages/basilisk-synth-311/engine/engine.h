/* BASILISK 16 engine: Windows for Workgroups 3.11 (the DOSBox Pure core with the BSYN card) run on a thread of
   its own, talking to its owner only through a bshm block. Used in-process by the plugin, and by engine_main.c
   (a standalone process over named shared memory) for the test rigs. */
#ifndef BS_ENGINE_H
#define BS_ENGINE_H
#include "bshm.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct bs_engine bs_engine;
/* core: the DOSBox Pure library to load (the plugin passes a private copy per instance, so each instance has its
   own machine); conf: the DOSBox configuration; state: machine snapshot to resume, or NULL to boot;
   make_state: write a snapshot there when the guest says it is idle (build time), or NULL; log: or NULL */
bs_engine *bs_engine_start(bshm *S, const char *core, const char *conf, const char *state, const char *make_state, const char *log);
void bs_engine_stop(bs_engine *e);           /* sets quit, joins the thread, unloads the core */
int bs_engine_run(bs_engine *e);             /* the loop itself (the thread body), for engine_main.c */
bs_engine *bs_engine_new(bshm *S, const char *core, const char *conf, const char *state, const char *make_state, const char *log);
#ifdef __cplusplus
}
#endif
#endif
