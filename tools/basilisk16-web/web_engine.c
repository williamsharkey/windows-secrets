/* BASILISK 16 in the browser: the plugin's own engine thread (packages/basilisk-synth-311/engine/engine.c), compiled
   unchanged. Only how it finds the core differs: in WebAssembly the DOSBox Pure core (with the BSYN card) is linked
   in statically, so dlopen/dlsym hand out the linked functions instead of loading a library.

   One hook, for the build only: the engine writes a snapshot when the guest sends a type-2 report and a snapshot
   path is set. The browser resumes from a machine that is already assembled and ready, so the snapshot must be
   taken later than the guest's own type-2 (which it sends at boot, before the assembly). The reports are therefore
   passed through with the guest's type-2 dropped, and one is added when web_snapshot_request is set. */
#include <dlfcn.h>
#include <stdint.h>
#include <string.h>

static void *web_dlopen(const char *p, int flags) { (void)p; (void)flags; return (void *)1; }
static void *web_dlsym(void *h, const char *name);
#define dlopen web_dlopen
#define dlsym web_dlsym
#define dlclose(h) ((void)(h), 0)
#include "engine.c"
#undef dlopen
#undef dlsym
#undef dlclose

void bsyn_host_event(const uint16_t *w, int n, uint32_t id, uint64_t at);
int bsyn_host_reports(uint16_t *w, int max);
uint64_t bsyn_host_dac(void);
int bsyn_host_read(uint64_t from, float *out, int n);
void bsyn_host_stats(uint32_t *ontime, uint32_t *late, uint32_t *latemax);

volatile int web_snapshot_request;

/* The pointer while a button is held. The plugin's engine moves Windows' pointer through the guest program
   (SetCursorPos, the 0x0600 packet), which runs only between messages: inside Windows' own modal loops (dragging a
   scroll-bar thumb) it never runs, and the thumb would stay put. So while the host holds the left button, the moves
   also go to the emulated mouse itself, as relative motion, which Windows' mouse driver follows in any loop. */
volatile int web_mouse_dx, web_mouse_dy;
static retro_input_state_t web_engine_state;
static int16_t web_istate(unsigned port, unsigned dev, unsigned idx, unsigned id)
{
  if (!port && dev == RETRO_DEVICE_MOUSE && (id == RETRO_DEVICE_ID_MOUSE_X || id == RETRO_DEVICE_ID_MOUSE_Y)) {
    int v = __sync_lock_test_and_set(id == RETRO_DEVICE_ID_MOUSE_X ? &web_mouse_dx : &web_mouse_dy, 0);
    return (int16_t)(v < -32767 ? -32767 : v > 32767 ? 32767 : v);
  }
  return web_engine_state ? web_engine_state(port, dev, idx, id) : 0;
}
static void web_set_input_state(retro_input_state_t cb) { web_engine_state = cb; retro_set_input_state(web_istate); }

static int web_reports(uint16_t *w, int max)
{
  int k = bsyn_host_reports(w, max - 1), i = 0, o = 0;
  while (i < k) {               /* packets: [type << 8 | words] [...]; drop the guest's own type 2 */
    int n = (w[i] & 0xFF) ? (w[i] & 0xFF) : 1, ty = w[i] >> 8, j;
    if (i + n > k) n = k - i;
    if (ty != 2) for (j = 0; j < n; j++) w[o++] = w[i + j];
    i += n;
  }
  if (web_snapshot_request) { web_snapshot_request = 0; w[o++] = (uint16_t)(2 << 8 | 1); }
  return o;
}

static void *web_dlsym(void *h, const char *n)
{
  static const struct { const char *name; void *fn; } t[] = {
    {"retro_init", (void *)retro_init}, {"retro_run", (void *)retro_run}, {"retro_deinit", (void *)retro_deinit},
    {"retro_unload_game", (void *)retro_unload_game}, {"retro_load_game", (void *)retro_load_game},
    {"retro_serialize_size", (void *)retro_serialize_size}, {"retro_serialize", (void *)retro_serialize},
    {"retro_unserialize", (void *)retro_unserialize}, {"retro_set_environment", (void *)retro_set_environment},
    {"retro_set_video_refresh", (void *)retro_set_video_refresh}, {"retro_set_audio_sample", (void *)retro_set_audio_sample},
    {"retro_set_audio_sample_batch", (void *)retro_set_audio_sample_batch}, {"retro_set_input_poll", (void *)retro_set_input_poll},
    {"retro_set_input_state", (void *)web_set_input_state},
    {"bsyn_host_event", (void *)bsyn_host_event}, {"bsyn_host_reports", (void *)web_reports}, {"bsyn_host_dac", (void *)bsyn_host_dac},
    {"bsyn_host_read", (void *)bsyn_host_read}, {"bsyn_host_stats", (void *)bsyn_host_stats},
  };
  size_t i;
  (void)h;
  for (i = 0; i < sizeof t / sizeof t[0]; i++) if (!strcmp(t[i].name, n)) return t[i].fn;
  return NULL;
}
