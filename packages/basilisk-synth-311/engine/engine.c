/* BASILISK 16 engine: see engine.h. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include "libretro.h"
#include "engine.h"
#ifdef _WIN32
#include <windows.h>
#include <mmsystem.h>
#define DLOPEN(p) (void *)LoadLibraryA(p)
#define DLSYM(h, n) (void *)GetProcAddress((HMODULE)(h), n)
#define DLCLOSE(h) FreeLibrary((HMODULE)(h))
#else
#include <dlfcn.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
#define DLOPEN(p) dlopen(p, RTLD_NOW | RTLD_LOCAL)
#define DLSYM(h, n) dlsym(h, n)
#define DLCLOSE(h) dlclose(h)
#endif

struct bs_engine {
  bshm *S;
  char core[1024], conf[1024], state[1024], make_state[1024], sysdir[1024];
  FILE *log;
  void *lib;
  int btn;
  unsigned char held[512];     /* keys the host holds down (the core checks, and releases keys nobody holds) */
  retro_keyboard_event_t kbcb;
#ifdef _WIN32
  HANDLE thread;
#else
  pthread_t thread; int has_thread;
#endif
  void (*c_init)(void), (*c_run)(void), (*c_deinit)(void), (*c_unload)(void);
  bool (*c_load)(const struct retro_game_info *);
  size_t (*c_ssize)(void);
  bool (*c_save)(void *, size_t), (*c_restore)(const void *, size_t);
  void (*c_set_env)(retro_environment_t), (*c_set_video)(retro_video_refresh_t), (*c_set_audio1)(retro_audio_sample_t),
    (*c_set_audio)(retro_audio_sample_batch_t), (*c_set_poll)(retro_input_poll_t), (*c_set_state)(retro_input_state_t);
  void (*h_event)(const uint16_t *, int, uint32_t, uint64_t);
  int (*h_reports)(uint16_t *, int);
  uint64_t (*h_dac)(void);
  int (*h_read)(uint64_t, float *, int);
  void (*h_stats)(uint32_t *, uint32_t *, uint32_t *);
};

/* libretro callbacks carry no context: each engine runs the core on its own thread, so the thread says which */
static
#ifdef _MSC_VER
__declspec(thread)
#else
__thread
#endif
bs_engine *cur;

static void say(bs_engine *e, const char *fmt, ...)
{
  va_list a;
  if (!e || !e->log) return;
  va_start(a, fmt); vfprintf(e->log, fmt, a); va_end(a); fputc('\n', e->log); fflush(e->log);
}
static double now(void)
{
#ifdef _WIN32
  static LARGE_INTEGER f; LARGE_INTEGER c;
  if (!f.QuadPart) QueryPerformanceFrequency(&f);
  QueryPerformanceCounter(&c); return (double)c.QuadPart / (double)f.QuadPart;
#else
  struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9;
#endif
}
static void nap(double s)
{
#ifdef _WIN32
  Sleep((DWORD)(s * 1000 + 0.5));
#else
  struct timespec t = { 0, (long)(s * 1e9) }; nanosleep(&t, NULL);
#endif
}
static void barrier(void) { __sync_synchronize(); }

static void clog_(enum retro_log_level l, const char *fmt, ...)
{
  va_list a;
  if (!cur || !cur->log || l < RETRO_LOG_WARN) return;
  va_start(a, fmt); fprintf(cur->log, "[core] "); vfprintf(cur->log, fmt, a); va_end(a); fflush(cur->log);
}
static const char *optval(const char *k)
{
  if (!strcmp(k, "dosbox_pure_audiorate")) return "48000";
  if (!strcmp(k, "dosbox_pure_perfstats")) return "none";
  if (!strcmp(k, "dosbox_pure_savestate")) return "on";
  return NULL;
}
static bool env(unsigned cmd, void *data)
{
  switch (cmd) {
  case RETRO_ENVIRONMENT_GET_LOG_INTERFACE: ((struct retro_log_callback *)data)->log = clog_; return true;
  case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT: return *(enum retro_pixel_format *)data == RETRO_PIXEL_FORMAT_XRGB8888;
  case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY: case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
    if (!cur) return false;
    *(const char **)data = cur->sysdir; return true;
  case RETRO_ENVIRONMENT_GET_VARIABLE: { struct retro_variable *v = data; v->value = optval(v->key); return v->value != NULL; }
  case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE: *(bool *)data = false; return true;
  case RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION: *(unsigned *)data = 0; return true;
  case RETRO_ENVIRONMENT_SET_KEYBOARD_CALLBACK: if (cur) cur->kbcb = ((struct retro_keyboard_callback *)data)->callback; return true;
  case RETRO_ENVIRONMENT_GET_THROTTLE_STATE: {
    /* unthrottled, one emulated frame per retro_run: the engine paces itself. (Claiming a slower display to make
       DOSBox Pure skip drawing was tried: it then emulates ten frames per call, and the pacing gets too coarse.) */
    struct retro_throttle_state *t = data; t->mode = RETRO_THROTTLE_UNBLOCKED; t->rate = 0; return true; }
  case RETRO_ENVIRONMENT_SET_VARIABLES: case RETRO_ENVIRONMENT_SET_SUPPORT_NO_GAME: case RETRO_ENVIRONMENT_SET_GEOMETRY:
  case RETRO_ENVIRONMENT_SET_SYSTEM_AV_INFO: return true;
  default: return false;
  }
}
static void video(const void *d, unsigned w, unsigned h, size_t pitch)
{
  bshm *S; unsigned y;
  if (!cur || !d) return;
  S = cur->S;
  if (!S->vid_want || w > BSHM_W || h > BSHM_H) return;
  S->vid_seq++; barrier();
  for (y = 0; y < h; y++) memcpy(S->vid + y * w, (const char *)d + y * pitch, w * 4);
  S->vid_w = w; S->vid_h = h;
  barrier(); S->vid_seq++;
}
static void audio1(int16_t l, int16_t r) { (void)l; (void)r; }
static size_t audiob(const int16_t *d, size_t n) { (void)d; return n; }   /* the SB16 mix is not used: the BSYN DAC is */
static void poll_(void) {}
static int16_t istate(unsigned port, unsigned dev, unsigned idx, unsigned id)
{
  (void)idx;
  if (cur && !port && dev == RETRO_DEVICE_KEYBOARD) return id < 512 ? cur->held[id] : 0;
  if (!cur || port || dev != RETRO_DEVICE_MOUSE) return 0;
  if (id == RETRO_DEVICE_ID_MOUSE_LEFT) return cur->btn & 1;
  if (id == RETRO_DEVICE_ID_MOUSE_RIGHT) return (cur->btn >> 1) & 1;
  return 0;
}

static void *load_file(const char *p, size_t *n)
{
  FILE *f = fopen(p, "rb"); void *b; long len;
  if (!f) return NULL;
  fseek(f, 0, SEEK_END); len = ftell(f); fseek(f, 0, SEEK_SET);
  b = malloc(len ? len : 1); *n = fread(b, 1, len, f); fclose(f);
  return b;
}

static void fail(bs_engine *e, const char *m)
{
  snprintf(e->S->error, sizeof e->S->error, "%s", m);
  e->S->state = BS_FAILED;
  say(e, "failed: %s", m);
}

bs_engine *bs_engine_new(bshm *S, const char *core, const char *conf, const char *state, const char *make_state, const char *log)
{
  bs_engine *e = (bs_engine *)calloc(1, sizeof *e);
  char *slash;
  e->S = S;
  snprintf(e->core, sizeof e->core, "%s", core);
  snprintf(e->conf, sizeof e->conf, "%s", conf);
  if (state) snprintf(e->state, sizeof e->state, "%s", state);
  if (make_state) snprintf(e->make_state, sizeof e->make_state, "%s", make_state);
  snprintf(e->sysdir, sizeof e->sysdir, "%s", conf);
  slash = strrchr(e->sysdir, '/'); if (!slash) slash = strrchr(e->sysdir, '\\'); if (slash) *slash = 0;
  if (log) e->log = fopen(log, "a");
  return e;
}

int bs_engine_run(bs_engine *e)
{
  bshm *S = e->S;
  size_t n;
  uint64_t copied = 0, last_hr = 0, pace_beat = 0; double t_hr, t0, busy = 0, t_load = 0, t_beat_seen = 0;
  uint16_t rep[512]; int snap_now = 0;
  int32_t mx = -1, my = -1; uint32_t mseq = 0;
  uint32_t click_r = S->click_w; int cphase = 0, cframes = 0;   /* the click queue: 1 to its place, 2 pressed, 3 held while the host holds, 4 released */
  cur = e;
  say(e, "engine: core %s conf %s state %s", e->core, e->conf, e->state);
  e->lib = DLOPEN(e->core);
  if (!e->lib) { fail(e, "cannot load the core"); return 4; }
#define GET(v, nm) *(void **)&e->v = DLSYM(e->lib, nm)
  GET(c_init, "retro_init"); GET(c_run, "retro_run"); GET(c_deinit, "retro_deinit"); GET(c_unload, "retro_unload_game");
  GET(c_load, "retro_load_game"); GET(c_ssize, "retro_serialize_size"); GET(c_save, "retro_serialize"); GET(c_restore, "retro_unserialize");
  GET(c_set_env, "retro_set_environment"); GET(c_set_video, "retro_set_video_refresh"); GET(c_set_audio1, "retro_set_audio_sample");
  GET(c_set_audio, "retro_set_audio_sample_batch"); GET(c_set_poll, "retro_set_input_poll"); GET(c_set_state, "retro_set_input_state");
  GET(h_event, "bsyn_host_event"); GET(h_reports, "bsyn_host_reports"); GET(h_dac, "bsyn_host_dac"); GET(h_read, "bsyn_host_read"); GET(h_stats, "bsyn_host_stats");
  if (!e->c_run || !e->h_event) { fail(e, "the core lacks the BSYN card"); return 4; }
  e->c_set_env(env); e->c_set_video(video); e->c_set_audio1(audio1); e->c_set_audio(audiob); e->c_set_poll(poll_); e->c_set_state(istate);
  e->c_init();
  {
    struct retro_game_info gi; memset(&gi, 0, sizeof gi); gi.path = e->conf;
    S->state = BS_BOOTING;
    if (!e->c_load(&gi)) { fail(e, "cannot start the machine"); e->c_deinit(); return 5; }
  }
  t0 = now();
  if (e->state[0]) {           /* warm start: the machine as the build froze it */
    void *st = load_file(e->state, &n); int i;
    if (!st) { fail(e, "the machine snapshot is missing"); goto out; }
    for (i = 0; i < 600 && !S->quit; i++) {
      e->c_run();
      if (e->c_restore(st, n)) break;
    }
    free(st);
    if (i == 600) { fail(e, "the machine snapshot does not fit this engine"); goto out; }
    say(e, "restored after %d frames, %.3f s", i + 1, now() - t0);
  }
  S->state = BS_RUNNING;
  copied = e->h_dac();
  S->dac_w = copied;
  t_hr = now(); last_hr = S->host_r;

  while (!S->quit) {
    double t = now();
    uint64_t dac, target;
    int k;
    S->engine_beat++;
    while (S->ev_r != S->ev_w) {           /* events in */
      bshm_ev *ev = &S->ev[S->ev_r % BSHM_EV];
      barrier();
      e->h_event(ev->w, (int)ev->n, ev->id, ev->at);
      barrier(); S->ev_r++;
    }
    if (cphase == 0 && click_r != S->click_w) {   /* a click: to its place first, then pressed for 3 frames at least */
      uint16_t w[3];
      if (S->click_w - click_r > 4) click_r = S->click_w - 4;
      mx = S->click_x[click_r % 4]; my = S->click_y[click_r % 4]; click_r++;
      w[0] = (uint16_t)(0x0600 | 3); w[1] = (uint16_t)mx; w[2] = (uint16_t)my;
      e->h_event(w, 3, 0, 0);
      cphase = 1; cframes = 0;
    }
    /* the pointer: the guest moves it (absolute). Not while a click is going on, unless it is a held press that
       nothing waits behind (a drag): a click's release must happen where it was pressed */
    if (S->mouse_seq != mseq && (cphase == 0 || (cphase == 3 && click_r == S->click_w))) {
      mseq = S->mouse_seq;
      if (S->mouse_x != mx || S->mouse_y != my) {
        uint16_t w[3]; mx = S->mouse_x; my = S->mouse_y;
        w[0] = (uint16_t)(0x0600 | 3); w[1] = (uint16_t)mx; w[2] = (uint16_t)my;
        e->h_event(w, 3, 0, 0);
      }
    }
    if (cphase == 3 && !(S->mouse_btn & 1)) { cphase = 4; cframes = 0; }   /* let go: a short release, then the next click */
    e->btn = (cphase == 1 || cphase == 4 ? 0 : cphase == 2 ? 1 : (int)(S->mouse_btn & 1)) | (int)(S->mouse_btn & 2);
    while (S->key_r != S->key_w) {
      uint32_t kk = S->keys[S->key_r % BSHM_KEYS];
      if ((kk & 0xFFFF) < 512) e->held[kk & 0xFFFF] = (unsigned char)((kk >> 31) & 1);
      if (e->kbcb) e->kbcb((kk >> 31) & 1, kk & 0xFFFF, 0, (uint16_t)((kk >> 16) & 0x7FFF));
      S->key_r++;
    }
    while ((k = e->h_reports(rep, 512)) > 0) {   /* reports out */
      int i;
      for (i = 0; i < k; i++) {
        if (S->rep_w - S->rep_r >= BSHM_REP) break;
        S->rep[S->rep_w % BSHM_REP] = rep[i]; barrier(); S->rep_w++;
      }
      for (i = 0; i < k; i += (rep[i] & 0xFF) ? (rep[i] & 0xFF) : 1) {
        int ty = rep[i] >> 8;
        if (ty == 1) { S->state = BS_READY; say(e, "synth ready at %.3f s", now() - t0); }
        if (ty == 2 && e->make_state[0]) snap_now = 1;
      }
    }
    dac = e->h_dac();                      /* DAC out */
    while (copied < dac) {
      float buf[2048 * 2]; int want = (int)(dac - copied > 2048 ? 2048 : dac - copied), got, i;
      got = e->h_read(copied, buf, want);
      if (got <= 0) { copied = dac; break; }
      for (i = 0; i < got; i++) {
        uint32_t j = (uint32_t)((copied + i) % BSHM_RING);
        S->ring[j * 2] = buf[i * 2]; S->ring[j * 2 + 1] = buf[i * 2 + 1];
      }
      copied += got;
    }
    barrier(); S->dac_w = copied;
    /* pacing: keep the DAC `lead` frames ahead of what the host consumed; when the host's audio clock is not
       running (no audio device, the DAW stopped processing), run at real time by our own clock */
    if (S->host_r != last_hr) { last_hr = S->host_r; t_hr = t; }
    if (S->host_beat != pace_beat) { pace_beat = S->host_beat; t_beat_seen = t; }
    if (S->offline || (S->realtime && t - t_beat_seen < 0.2)) {
      /* the host is processing (it beats every block, and while it waits for us): its pace exactly, plus what it
         grants while it waits for Windows */
      uint64_t base = S->host_r > S->grant_until ? S->host_r : S->grant_until;
      target = base + S->lead;
    }
    else target = last_hr + (uint64_t)((t - t_hr) * S->rate) + S->lead;   /* no audio from the host: real time */
    if (copied < target) {
      double a = now();
      e->c_run();
      busy += now() - a;
      if (cphase && ++cframes >= (cphase == 2 ? 3 : 2)) { cphase = cphase == 1 ? 2 : cphase == 2 ? 3 : cphase == 4 ? 0 : cphase; cframes = 0; }
    } else nap(0.001);
    if (snap_now) {
      size_t sz = e->c_ssize(); void *b = malloc(sz);
      if (b && e->c_save(b, sz)) {
        FILE *f = fopen(e->make_state, "wb");
        if (f) { fwrite(b, 1, sz, f); fclose(f); }
        say(e, "snapshot %u bytes -> %s", (unsigned)sz, e->make_state);
      }
      free(b);
      snap_now = 0; e->make_state[0] = 0;
    }
    if (e->h_stats) { uint32_t a, b, c; e->h_stats(&a, &b, &c); S->sched_ontime = a; S->sched_late = b; S->sched_latemax = c; }
    if (t - t_load > 1) { S->emu_load = (uint32_t)(busy / (t - t_load + 1e-9) * 1000); busy = 0; t_load = t; }
  }
out:
  say(e, "exit");
  e->c_unload(); e->c_deinit();
  cur = NULL;
  return 0;
}

int bs_engine_event(bs_engine *e, const uint16_t *w, int n, uint32_t id, uint64_t at)
{
  if (!e || !e->h_event || e->S->state < BS_RUNNING || e->S->state == BS_FAILED || e->S->quit) return 0;
  e->h_event(w, n, id, at);
  return 1;
}

#ifdef _WIN32
static DWORD WINAPI thread_main(LPVOID p) { timeBeginPeriod(1); bs_engine_run((bs_engine *)p); timeEndPeriod(1); return 0; }
#else
static void *thread_main(void *p) { bs_engine_run((bs_engine *)p); return NULL; }
#endif

bs_engine *bs_engine_start(bshm *S, const char *core, const char *conf, const char *state, const char *make_state, const char *log)
{
  bs_engine *e = bs_engine_new(S, core, conf, state, make_state, log);
#ifdef _WIN32
  e->thread = CreateThread(NULL, 1 << 20, thread_main, e, 0, NULL);
  if (e->thread) SetThreadPriority(e->thread, THREAD_PRIORITY_ABOVE_NORMAL);
#else
  {
    pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setstacksize(&at, 1 << 20);
    e->has_thread = pthread_create(&e->thread, &at, thread_main, e) == 0;
    pthread_attr_destroy(&at);
  }
#endif
  return e;
}

void bs_engine_stop(bs_engine *e)
{
  if (!e) return;
  e->S->quit = 1;
#ifdef _WIN32
  if (e->thread) { WaitForSingleObject(e->thread, 10000); CloseHandle(e->thread); }
#else
  if (e->has_thread) pthread_join(e->thread, NULL);
#endif
  if (e->lib) DLCLOSE(e->lib);
  if (e->log) fclose(e->log);
  free(e);
}
