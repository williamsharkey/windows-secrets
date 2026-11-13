/* BASILISK synth 3.11: the shared-memory block between the plugin (host) and the engine process.
   One block per plugin instance, named by the plugin. Single-producer/single-consumer rings throughout. */
#ifndef BSHM_H_INCLUDED
#define BSHM_H_INCLUDED
#include <stdint.h>
#define BSHM_MAGIC 0x4D485342u   /* "BSHM" */
#define BSHM_VERSION 1
#define BSHM_RING 65536          /* stereo float frames of DAC output (1.37 s at 48 kHz) */
#define BSHM_W 1024
#define BSHM_H 768
#define BSHM_EV 1024
#define BSHM_REP 32768
#define BSHM_KEYS 64

typedef struct { uint32_t n; uint32_t id; uint64_t at; uint16_t w[136]; } bshm_ev;   /* 288 bytes: a packet of up to 136 words */

enum { BS_STARTING = 0, BS_BOOTING = 1, BS_RUNNING = 2, BS_READY = 3, BS_FAILED = 9 };

typedef struct {
  uint32_t magic, version;
  volatile uint32_t state;      /* engine: BS_* */
  volatile uint32_t quit;       /* host: 1 = engine must exit */
  volatile uint64_t host_beat;  /* host: bumped every process block / timer */
  volatile uint64_t engine_beat;
  uint32_t rate, ring_len;
  volatile uint64_t dac_w;      /* engine: DAC frames available up to here */
  volatile uint64_t host_r;     /* host: DAC frames consumed up to here */
  volatile uint32_t lead;       /* host: how far ahead of host_r the engine keeps the DAC (frames) */
  volatile uint32_t realtime;   /* host: 1 = the host's audio clock is running (else engine paces itself) */
  volatile uint32_t ev_w, ev_r;
  volatile uint32_t rep_w, rep_r;
  volatile uint32_t vid_seq;    /* odd while the engine writes a frame */
  volatile uint32_t vid_w, vid_h;
  volatile uint32_t vid_want;   /* host: 1 = an editor is showing the screen */
  volatile int32_t mouse_x, mouse_y;
  volatile uint32_t mouse_btn, mouse_seq;
  volatile uint32_t key_w, key_r;
  volatile uint32_t keys[BSHM_KEYS];   /* (down << 31) | (mods << 16) | retro keycode */
  volatile uint32_t emu_load;   /* engine: per-mille of real time spent emulating */
  volatile uint32_t underruns;  /* host: count */
  char error[128];
  volatile uint32_t sched_ontime, sched_late, sched_latemax;   /* engine: the card's scheduling statistics */
  volatile uint32_t offline;    /* host: rendering offline: never run ahead of host_r + lead on our own clock */
  volatile uint32_t grant_pad;
  volatile uint64_t grant_until; /* host: while it waits for Windows (offline), the engine may run up to here */
  uint32_t reserved[25];
  bshm_ev ev[BSHM_EV];
  volatile uint16_t rep[BSHM_REP];
  float ring[BSHM_RING * 2];
  uint32_t vid[BSHM_W * BSHM_H];
} bshm;

#endif
