#include <stdio.h>
#include <stddef.h>
#include "bshm.h"
#define O(f) printf("%s=%zu\n", #f, offsetof(bshm, f));
int main(void){O(magic)O(version)O(state)O(quit)O(host_beat)O(engine_beat)O(rate)O(ring_len)O(dac_w)O(host_r)O(lead)O(realtime)O(ev_w)O(ev_r)O(rep_w)O(rep_r)O(vid_seq)O(vid_w)O(vid_h)O(vid_want)O(mouse_x)O(mouse_y)O(mouse_btn)O(mouse_seq)O(key_w)O(key_r)O(keys)O(emu_load)O(underruns)O(error)O(sched_ontime)O(sched_late)O(sched_latemax)O(offline)O(grant_until)O(click_w)O(ev)O(rep)O(ring)O(vid)printf("size=%zu\nevsize=%zu\n",sizeof(bshm),sizeof(bshm_ev));return 0;}
