# BASILISK LIVE - end-to-end performance study (2026-11-07)

Measured on the shared droplet (8 vCPU, 15 GB) with the two other XP VMs running, over
`https://live.williamsharkey.com` and through an SSH tunnel, with Playwright/Chromium as the
viewer. "Before" = the first working build of the day; "after" = what is deployed now.

## Headline

| | before | after | how |
|---|---|---|---|
| show length (Wake -> idle again) | 13-14 min raw (film take: 857 s); first live run hit the 480 s hard stop before question 2 | **5 min 20-26 s** | puppet back-pressure (below) |
| visitor's question posted -> answer back in the guest | 186-220 s | **1.5 s** (4.4 s on a cold server, now pre-warmed) | same |
| answer in -> first audible syllable (reversed Sam) | ~205 s | 18.4 s -> **11.6 s** | TTS rendered while the swarm spells; throbber exits early |
| answer in -> typing starts on XP + page caption | ~220 s | 31.6 s -> **24.9 s** (the voice plays first, by design) | same |
| glass-to-glass video delay | ~7-8 s (buffer-ahead median 5.47 s, p90 6.39) | **~4 s** (buffer-ahead median 1.68-1.71 s, p90 2.46-2.53, two shows) | own MSE player preferred over Chrome's new native HLS (which starts 3 segments back), 1.25x playback-rate creep instead of seeks |
| HLS segment cadence | pairs every 4 s | **one every 2.0 s** | poster JPEG moved out of the ffmpeg graph |
| idle desktop bitrate | ~1.0 Mb/s (P-frames "repairing" VBV-starved keyframes) | **~0.75 Mb/s** | bufsize 2x maxrate |
| show-content bitrate | - | ~0.5 Mb/s (x264 veryfast CRF 26) | |
| API cost per show (2 answers, Haiku 5.5) | - | **$0.00022** ($0.00016 + $0.00006) | cached frame: cr=900 on Q2 |
| page rAF during the flood | ~58-60 fps, one 50 ms hitch | **60 fps, worst frame 16.8 ms** (375 px and 1280 px) | per-column tongues, 24 fps flood redraw, idle short-circuit |

## 1. API

| per call | value |
|---|---|
| model / effort / max_tokens | claude-haiku-5-5 / low / 1024 (replies are 50-90 output tokens) |
| time to first token | 0.44-0.83 s (median ~0.66 s) |
| total | 0.86-1.35 s |
| Q1 tokens | in 22, cache write 900, out 83-87 -> $0.00016 |
| Q2 tokens (Q1+A1 included for coherence) | in 118-125, cache read 900, out 50-78 -> $0.00005-6 |

* One `AsyncAnthropic` per process (keep-alive), built at startup together with the ~2 s
  `import anthropic`: the first answer after a restart went from 4.4 s to ~1.5 s.
* Prompt caching works as intended: the fixed SYSTEM frame (FRAME + live-show guidance,
  ~900 tokens) is written once and read on every later call within 5 minutes. A 1-hour TTL
  doubles the write price to save at most one write per idle gap: at $0.10/MTok that is
  $0.00009 per show at best - not worth it.
* Q2 now carries Q1+A1 (adds ~100 input tokens, $0.00001) so the second answer can refer to
  the first.
* The reply is streamed (to measure TTFT), but not pushed to XP token by token: the console
  speaks the whole answer before typing it, so the full text is needed anyway, and the
  whole call is ~1 s of a ~60 s answer sequence.
* Billing/credit/auth errors (400/401/402/403 mentioning credit, billing, balance...) switch
  everyone to recorded answers for an hour, quietly, like reaching the cap.

## 2. Stage pipeline (puppet log, guest clock, show #2 vs #1)

| step | before | after |
|---|---|---|
| console asks -> visitor's question typed into the console (11 cps) | 6 s | 6 s |
| typed -> reply in (`POST /claude`) | 186-220 s | 1.5 s |
| reply -> "answer arrived" (throbber finishes its word) | ~3 s | ~0-1 s (breaks out as soon as the reply is in) |
| swarm spells the first words | 6 s | 6 s |
| Sam renders the WAV | 2.3 s (serial) | 0 s (rendered in the background while the swarm spells) |
| reply in -> first audible / -> typing starts | 18.4 s / 31.6 s | 11.6 s / 24.9 s |
| Sound Recorder launched, swallowed, reversed | 10 s | 10 s |
| reversed play -> forward echo play -> typing starts | 13 s | 13 s |

**The big one:** the show spent 3-4 minutes per question frozen. Killing calc.exe released it
instantly, which pinned it: the 70 calculator keys are liberated top-level windows, and the
swarm moved all of them with async `SetWindowPos` ~70 times a second. calc.exe's one UI thread
never caught up (51 s of CPU in 5 minutes), and every synchronous call into it - `ShowWindow`,
`WM_SETTEXT` for the swarm's letters, `BM_GETCHECK` on a follower - waited behind that backlog.
The raw film takes had the same gaps (they were edited out). Fixes in `puppet.c`/`scenes.h`:
the world moves at most 25 times a second (`FRAME_MS 40`, the films are 25 fps, the stream
15), a window's thread that doesn't answer a `WM_NULL` probe within 8 ms gets no new moves
that frame, and the swarm uses `ShowWindowAsync`/`SendMessageTimeout`. The films keep their
look; only the dead air is gone.

Not changed (art, not waste): the swarm spelling the first words, Sound Recorder being eaten,
the reversed-then-forward playback.

## 3. Video

| | value |
|---|---|
| grab rate (HMP screendump) | 14.7-15.0 of 15 fps target |
| CPU, idle desktop | stage QEMU 25-56 %, ffmpeg 35-43 %, streamer.py 7-9 %, PulseAudio 8-17 %, parec 3-6 % |
| CPU, show running | stage QEMU ~135 % (two busy vCPUs), others as idle |
| x264 preset bench (30 s of show footage, CPU-s / size) | superfast 3.7 / 1.95 MB, **veryfast 4.4 / 1.85 MB**, faster 6.1 / 1.78 MB; CRF 23/26/28: 2.15/1.85/1.62 MB |
| dropped frames in the player | 24 / 4892 (0.5 %) -> 13 / 4810 and 30 / 4766 (0.3-0.6 %) |
| player startup (page load -> playing) | ~0.3 s locally, segments are 2 s |

* Kept veryfast + CRF 26: superfast saves 15 % encode CPU for 5 % more bits; the encode is
  a small part of ffmpeg's 35-43 % (PPM parsing + RGB->YUV + AAC).
* GOP 2 s is the latency/bitrate knob: Bliss keyframes are 130-190 KB, so a 4 s GOP would
  halve idle bitrate (~0.4 Mb/s) but add 2 s of delay. Kept 2 s.
* Readability: the console's transcript is Notepad's edit; Notepad now starts at 14 pt
  Lucida Console in the stage snapshot (was 10 pt). It stays unwrapped, so a 260-char answer
  scrolls sideways in the console and the stage shows fragments - turning Notepad's word
  wrap on was tried and reverted: a wrapped Notepad's edit is not picked up as the console
  transcript and vanishes from the scene. On phones the stage is 1/3 scale, so the
  page also shows **captions**: the server's own answer text (never anything read back from
  Windows), released when the puppet reports `speak`, typed out at the console's pace when
  it reports `type`.

## 4. Spend

A show is ~5.5 min plus ~20 s of reset/curtain, so one stage can run at most ~250 shows/day.

| shows/day | API $/day | $/month | vs $25 cap |
|---|---|---|---|
| 50 | $0.011 | $0.33 | 1.3 % |
| 200 | $0.044 | $1.32 | 5 % |
| 1000 (impossible on one stage; i.e. a bug or abuse) | $0.22 | $6.60 | 26 % |

Cold-cache shows (gaps over 5 min) cost $0.00022; back-to-back shows ~$0.00011. The cap is a
backstop against bugs and key misuse, not something normal traffic can reach; the global 90
calls/hour limit (~45 shows/hour, more than one stage can play) bounds a runaway at ~$0.4/day.
Per-IP limits (1 wake / 20 min, 6 questions / hour, 20 / day) are about fairness of the one
stage rather than money; with ~6 min shows, 1 wake per 20 min lets a single visitor hold at
most a third of the stage's time when nobody else is waiting. Tested: second question in an
hour of a 2/hour allowance got the 2 s "your words are on the wire" delay; the third got
"BASILISK is resting for you until 6:11 PM"; a second tab from the same IP got "You are
already in line"; 20 sockets from one IP -> 8 served, 12 refused.
