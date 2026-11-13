# BASILISK SYNTH: the Visualizers tab (design)

Status: design and a small prototype (`proto/vizproto.c`). Nothing here is in the product. This file does not change
`DNA.md` or `core/`. The saved settings in section 5 are a proposal for a v3 state key, beside the DNA.

Related designs:

- `design/preset-engine-2` (another lane) owns the editor tab system. Section 3 says how this tab fits into it.
- `PRESET-ARTWORK.md` (this folder): backgrounds that Paint draws when the preset changes. It uses the governor in
  section 6.
- `design/aesthetic-presets` (another lane) owns pack names. The scene examples in section 4.4 use placeholders.

---

## 1. Who it is for, and the one rule

Some musicians make screen-capture videos of their songs: the DAW on screen, a theme on the DAW, and a few plugins
open because they look good. Vaporwave and Frutiger Aero videos often do this. BASILISK SYNTH already looks like a
Windows XP desktop. The Visualizers tab makes it a stage for those videos.

Every visualizer is a real Windows part inside the guest: Sound Recorder's green wave, Task Manager's graphs,
progress bars, Volume Control sliders, Windows Media Player's visualizations, screen savers, the Date and Time
clock, wallpapers. The plugin only gives them data.

**The one rule: a visualizer never lags or disturbs the sound.** Section 6 is the design that keeps this rule.
Section 7 gives the measurements behind it.

---

## 2. What the sound path can spare (facts)

These facts come from the code (`guest/`, `plugin/`) and from `PROGRESS.md`. Section 7 adds new measurements.

| Fact | Where | What it means for visualizers |
|---|---|---|
| The machine has **1 vCPU**, single-threaded TCG. | `Machine.cpp`, `-smp 1`, `thread=single` | Every guest instruction, the sound included, runs on one host thread. A visualizer that keeps the guest busy competes with Sound Recorder for that thread. |
| XP's idle loop **halts** (PoIdle patched to `sti; hlt; ret`). | README, round 2 | When the guest is idle, the host thread sleeps. Guest idle time is real spare capacity, and a governor can read it. |
| A note goes: COM1 line -> synth.exe's COM thread -> an event -> srhook's **TIME_CRITICAL** note thread -> `waveOutWrite` -> kmixer -> AC97 -> QEMU's wav writer -> pipe -> plugin. | `guest/synth.c`, `guest/srhook.c` | Only the note thread has a raised priority. synth.exe's COM reader runs at **normal** priority, so any normal-priority guest work can delay a note before it reaches the note thread. |
| Each recorder's envelope thread wakes every 5 ms and each recorder calls `timeBeginPeriod(1)`. | `srhook.c` | The guest clock already ticks at 1 kHz. A visualizer timer gets fine resolution for free, and must not add many more wakeups. |
| Each playing strip already redraws its wave, position and slider every 50 ms (`vis_tick`). | `srhook.c` | The "scope" visual exists and is paid for. |
| Notes are **not** sample-accurate on XP. The plugin reports 100 ms latency and keeps a 40-50 ms jitter buffer. | `BasiliskSynthPlugin.cpp` | Lateness above the jitter buffer is audible as a late note. Visual load must not widen the note-time spread. |
| The plugin pulls the screen over **VNC at most 30 times a second**, as Raw and CopyRect rectangles, on a thread of its own. QEMU encodes on its main thread, which holds the big lock that the vCPU also needs. | `Machine.cpp` `vncLoop` | A large area that changes every frame (a full-screen screen saver) costs host time on the thread that also serves the audio timer. Keep the changing area small. |
| The machine **sleeps** after 4 s with no voice and no editor. | `Machine.hpp` | With the editor open (the tab visible), the machine stays awake. A visualizer must not keep it awake when the editor is closed. |
| The plugin already has XP's sound, 96 kHz stereo float, in a lock-free ring (`AudioRing`), 40-50 ms before it plays it. | `Machine.hpp` | Spectrum, levels and beats can be computed **host side**, on a non-audio thread, at no guest cost, and in time for the picture. |
| The 3.11 edition runs DOSBox Pure at fixed 60000 cycles, with cooperative multitasking, and notes are stamped to a DAC sample. | `basilisk-synth-311` | A 3.11 visualizer must give the CPU back after each small step, or synth.exe arms a note too late. |

---

## 3. The tab, in the tab system

The main view stays as it is: the 16 strips, the panels, Task Manager, the clock, the keyboard. The Visualizers tab
is a deeper tab. design/preset-engine-2 owns the tab strip. This design needs four things from it:

| Need | Form (proposal) |
|---|---|
| A tab id | `vis` |
| Show/hide lines from host to guest | the tab system's own tab line, for example `tab vis` and `tab main`. The guest starts the visual work when the tab shows and stops it when the tab hides. |
| A page area | the screen below the tab strip. The tab system decides the strip height. The mockups assume 24 px. |
| A state key | `vis` (section 5), saved with the preset and the project |

If design/preset-engine-2 chooses another line name or tab id, use that. Nothing below depends on the name.

### 3.1 The tab (edit view), 1024 x 768

```
┌[ Main ][ Layers ][ Library ][ Visualizers ][ Look ]───────────────────────────────────────────────┐ tab strip (preset-engine-2)
│ Scene: [ Mall Plaza (scene 3)       ▼] [Save] [New] [Delete]    Aspect: [16:9 ▼] [ ] Video mode │
├──────────────────────────────────────────────────────────────┬───────────────────────────────────┤
│ STAGE (the visualizers, exactly as the video shows them)     │ Layers in this scene (ListView)   │
│ ┌──────────────────────────────────────────────────────────┐ │ [x] Backdrop    Bliss (stretch)   │
│ │ ~~~ Bliss / artwork backdrop ~~~                         │ │ [x] Scope wall  16 waves, 4 x 4   │
│ │  ┌wave┐┌wave┐┌wave┐┌wave┐     ┌Task Manager┐            │ │ [x] Meters      CPU = mix level   │
│ │  │~~~~││~/\~││~~~~││_/\_│     │▁▃▇█▇▅▃▂▁▁▁▂│            │ │ [x] Bars        16 progress bars  │
│ │  └────┘└────┘└────┘└────┘     └────────────┘            │ │ [ ] WMP effect  Bars and Waves    │
│ │  ┌wave┐┌wave┐┌wave┐┌wave┐  ▐█▌▐█▌▐▌ ▐█▌▐▌ ▐▌▐█▌▐▌       │ │ [x] Marquee     "{preset}"        │
│ │  └────┘└────┘└────┘└────┘  progress-bar spectrum        │ │ [ ] Saver       Mystify (preview) │
│ │  ── Marquee: ＭＡＬＬ ＰＬＡＺＡ ───────────────>        │ │ [ ] Copy anim   files -> folder   │
│ │                                    🕓 clock             │ │ [Up] [Down] [Add...] [Remove]     │
│ └──────────────────────────────────────────────────────────┘ ├───────────────────────────────────┤
│  Stage size 960 x 540 (16:9, x2 = 1920 x 1080)              │ Layer: Meters (property page)     │
│                                                              │ React to: (•) Mix ( ) Layer [1▼]  │
│                                                              │           ( ) Voice [ 3 ]  ( ) Beat│
│                                                              │ Speed     Slow ├──▼────┤ Fast     │
│                                                              │ Reactivity Low ├────▼──┤ High     │
│                                                              │ Smoothing None ├──▼────┤ Heavy    │
│                                                              │ Colors    [ Luna green      ▼]    │
│                                                              │ Position  X[ 620] Y[ 40] W[300]...│
│                                                              │ Text      [{preset} - {song}    ] │
├──────────────────────────────────────────────────────────────┴───────────────────────────────────┤
│ Load: guest idle 61 %  Visual budget: GREEN  Frame rate 30   [ ] Pause visuals while playing     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Stage.** A plain window (the stage host) at a fixed size for the chosen aspect. The visualizer windows are its
  children. What the stage shows is what video mode shows.
- **Layers list.** A real ListView with check boxes, in z-order (top row = back). Each row is one visualizer.
- **Property page.** Real trackbars, combo boxes, radio buttons and edit boxes. The page changes with the selected
  row. The parameters are in section 4.
- **Status line.** The governor's state (section 6.3) in plain words. The visitor sees why a layer slowed or stopped.

### 3.2 Video mode (stage only)

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│        (only the stage: no tab strip, no lists, no pointer)    │
│                                                                │
│   the plugin window shows the stage at an exact scale          │
│   (x1, x1.5, x2, x3), nearest-neighbor, with black bars        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
          Esc or a right click -> back to the edit view
```

Details are in section 8.

---

## 4. The catalog

Cost classes come from section 7. "Host" means the plugin computes the data. "Guest" means the data is already in
the guest (synth.exe's shared memory: each recorder's envelope level, playing flag and note times).

### 4.1 XP visualizers

| # | Visualizer | Real Windows parts | Data | Cost | Verdict |
|---|---|---|---|---|---|
| V1 | **Scope wall** | The 16 Sound Recorder waves (`SR_WAVE`), each strip moved into a grid on the stage: 4 x 4, 2 x 8, 1 x 16 or "one big" | Guest: each recorder draws its own buffer at its own play position (`vis_tick`, 50 ms). Nothing is new. | **None extra** (the strips already redraw while they play). Moving the strips costs one repaint. | **First.** The signature look. Note: the wave control draws at a fixed size (section 7.3), so the "scope wall" groups the strips; it does not stretch the waves. |
| V2 | **Progress-bar spectrum** | 8 to 32 vertical progress bars (`msctls_progress32`, `PBS_VERTICAL`), Luna green blocks or the classic look; optional "smooth" style | Host: band levels. Or guest: one bar per recorder or layer (prototype mode `bars`) | **Very low**: one `PBM_SETPOS` per bar per frame; each bar repaints only its own small rectangle | **First.** Cheap, very XP, and works as level meters too. |
| V3 | **Task Manager meters** | The Performance page already on the main view: CPU Usage gauge, CPU Usage History, PF Usage, Page File History | Host or guest levels, given to Task Manager through a hook DLL in `taskmgr.exe` that answers its `NtQuerySystemInformation` calls (processor times, page file) with the levels. A hooked `SetTimer` gives a 100-250 ms update instead of 500 ms ("High"). | Low: Task Manager already runs. Hook work is tiny. | **Second.** Big payoff: real graphs that dance. A switch keeps "honest CPU" (the real machine) as the default. Risk: needs a probe of Task Manager's data calls. |
| V4 | **Volume Control mixer** | `sndvol32.exe`: Master, Wave, SW Synth, CD Player (the 4 lines this machine shows), with Balance and Mute | Host levels per band or layer, set as **thumb positions only** (`TBM_SETPOS` on the trackbars). A hook in sndvol32 blocks every mixer write, so the real volume never changes. The Mute boxes flash on beats. | Medium: sndvol32 itself costs guest CPU (section 7) | **Third.** Only 4 channels. Must be read-only to the mixer, or it changes the sound. |
| V5 | **Windows Media Player visualization** | WMP 9 Series is in the machine. Its effects (Ambience, Bars and Waves, Battery, Musical Colors, Particle, Plenoptic, Spikes, Alchemy; the exact list is in WMP's registry key `Objects\Effects`) are COM objects with `IWMPEffects::Render(TimedLevel, HDC, RECT)` | Host: a 1024-bin spectrum and waveform per channel, sent small (section 6.4) and expanded in the guest. WMP itself does not play anything and makes no sound. | Medium to high, by effect and size. Render at a small size (for example 320 x 240) and stretch. | **Second.** The most "music visualizer" look. The prototype hosts the effects in its own window (mode `wmp`). |
| V6 | **Screen saver window** | 2D screen savers in **preview mode** (`scr /p <hwnd>`) inside a stage window: Mystify (`ssmyst.scr`), Marquee (`ssmarque.scr`), Starfield (`ssstars.scr`), Beziers (`ssbezier.scr`), Windows XP (`logon.scr`) | Own animation. Optional reactivity: a hook in the saver scales its timer by level or tempo (Mystify speeds up on loud parts). Marquee text, font, colors and speed come from its registry values before it starts. | Low (Starfield) to medium (Mystify full screen). Small in a window. | **First** for Marquee (song title text) and Starfield; Mystify as a layer. **Not possible:** 3D Pipes, 3D Flying Objects and the other Direct3D savers fail in this machine ("Could not create the Direct3D device"). |
| V7 | **Copy animation** | The shell's AVI clips in `shell32.dll` (file copy, move, delete, empty Recycle Bin, search) in a real Animate control (`SysAnimate32`), inside a "Copying..." dialog with a real progress bar and text | Host: song position for the bar, tempo for the clip rate (restart per beat), text from `{song}` | Very low | **Second.** A strong Y2K "office" look. |
| V8 | **Clock and calendar** | The Date and Time page (already a donor) | Host: song time or real time; the second hand can tick on beats | None extra | **First** (it is there). |
| V9 | **Backdrop** | Desktop wallpapers in the machine (Bliss, Azul, and the others in `C:\WINDOWS\Web\Wallpaper`; section 7), solid colors, or the preset artwork (`PRESET-ARTWORK.md`) | None, or the artwork recipe | None while still | **First.** Every scene has one. |
| V10 | **Typewriter** | Notepad or WordPad; text typed one character per note-on (lyrics, the preset name, a poem) | Guest: note-ons (synth.exe sees every `on` line) | Very low | Later. Fun for lyric videos. |
| V11 | **Error trail** | A real message box (Critical Stop, Exclamation) dragged over a window that does not repaint, so it leaves the famous trail; it moves on beats | Host: beats | Low | Later. A meme visual; keep it optional. |
| V12 | **Magnifier lens** | `magnify.exe`: a docked zoom of part of the stage | none | Medium (a stretch every refresh) | Later, maybe. |

### 4.2 Windows 3.11 visualizers (BASILISK 16)

| Visualizer | Real parts | Note |
|---|---|---|
| Scope wall | the 16 SOUNDREC waves | as V1 |
| Scroll-bar meters | Control Panel style scroll bars, one per band | the 3.11 version of V2 |
| Media Player | `MPLAYER.EXE` scale and track bar as the song position | as V7's bar |
| Clock | `CLOCK.EXE`, analog | as V8 |
| Screen savers | Flying Windows (`SSFLYWIN.SCR`), Mystify, Starfield, Marquee | 3.11 savers have no preview mode. Run them with `/s` and make their window a child of the stage (`SetParent`); needs a probe. |
| Backdrops | the 3.11 wallpapers and patterns, the color schemes (Hotdog Stand, Plasma Power Saver, ...) | see `PRESET-ARTWORK.md` 8 |
| Program Manager | group windows as "panels", minimized icons that arrange on beats | later |

Cooperative multitasking: every 3.11 visualizer step runs from a `WM_TIMER` and returns at once. No loop may run
longer than about 2 ms of guest time.

### 4.3 Parameters (all visualizers)

Every layer of a scene has these. A visualizer ignores the ones it does not use.

| Parameter | Values | Meaning |
|---|---|---|
| `src` | `mix`, `layer N`, `voice N`, `beat`, `macro K`, `none` | What it reacts to. `mix` and `beat` are host data. `layer` and `voice` come from the guest. `macro K` follows the DAW's Macro K. |
| `react` | 0-100 | How far the data moves it (gain). |
| `smooth` | 0-100 | Attack/release smoothing of the data (0 = raw). |
| `speed` | 0-100 | The visualizer's own speed (scroll, rotation, Marquee speed, saver timer). |
| `fps` | 5, 10, 15, 20, 30 | Upper limit. The governor can lower it. |
| `rect` | x,y,w,h on the stage | Where it sits. |
| `colors` | a named scheme or up to 4 RGB values | Luna green, Luna blue, classic, vaporwave pink/cyan, aqua, or custom. Applied only where the part allows it (progress bar color `PBM_SETBARCOLOR` works in the classic look only; WMP presets; Marquee colors; saver registry values). |
| `text` | text with `{preset}`, `{pack}`, `{song}`, `{bpm}`, `{time}` | Marquee, copy dialog, typewriter, window titles. |
| `preset` | a number | A WMP effect preset, a Task Manager view. |
| `prio` | 1-3 | Which layer the governor slows first (3 first). |

### 4.4 Scenes

A scene is a backdrop and an ordered list of layers. The tab ships with a few scenes. Names are placeholders until
design/aesthetic-presets publishes its packs.

| Scene | Layers |
|---|---|
| Tape Machine | Bliss, the 16-wave scope wall (4 x 4), Task Manager meters (`src mix`), clock |
| Mall Plaza (vaporwave) | artwork or a pink/cyan backdrop, Marquee with `{preset}` in full width letters, progress-bar spectrum in the classic look with pink bars, Starfield preview window |
| Aqua Office (Frutiger Aero) | Azul or Bliss, WMP "Bars and Waves" in a small window, copy animation with `{song}`, Luna progress bars |
| Night Shift | black backdrop, scope wall 1 x 16, Mystify preview (`src beat`, `speed` on beats), clock |

---

## 5. Saved settings (v3 proposal)

The plugin state gets a key `vis`, beside `dna` and `art`. It is one line of printable ASCII, at most 2048 bytes.
It is not part of the DNA string, so a DNA stays portable between editions.

```
VIS     := 'v1' ( ';' SCENE )+
SCENE   := 'scene=' NAME ',' 'bg=' BG ( ',' LAYER )*
LAYER   := KIND '(' PARAM ( ' ' PARAM )* ')'
PARAM   := KEY '=' VALUE            keys as in 4.3
```

Example:

```
v1;scene=Mall Plaza,bg=art,bars(n=16 src=mix react=70 smooth=40 colors=ff71ce rect=40,300,420,180),
mq(text={preset} speed=30 colors=000080.ff00ff rect=0,500,960,40),saver(scr=ssstars speed=50 rect=520,40,400,240)
```

- A preset can carry a `vis` value. A pack can carry a default scene. The DAW project carries the visitor's choice.
- "Follow the preset" (a check box on the tab) uses the preset's scene when the preset changes. Off: the scene
  stays.
- Unknown kinds and keys are ignored, so an older guest shows what it knows.

---

## 6. Performance design: never disturb the sound

### 6.1 Principles

1. **Analysis on the host, drawing in the guest.** The plugin computes levels, bands, beats and the waveform from the
   audio it already has (`AudioRing`), on a thread that is not the audio thread. The guest only moves real controls.
   No guest code reads audio or does an FFT.
2. **Lowest priority for anything visual.** Every visual process and thread in the guest runs at
   `IDLE_PRIORITY_CLASS` (or `THREAD_PRIORITY_IDLE`). Screen savers, WMP effects, the stage host, Task Manager in
   "meters" mode, Paint for the artwork.
3. **Raise the note path, not only the note thread.** synth.exe's COM reader thread goes to
   `THREAD_PRIORITY_TIME_CRITICAL` (today it is normal). This is a fix for the main view too: Task Manager runs at
   High priority in XP by default and so outranks the COM reader now. Lower Task Manager to `BELOW_NORMAL` once
   the assembly is done.
4. **Small changing areas.** The stage is at most 960 x 540. The visualizer windows inside it are smaller. Nothing
   full-screen animates. This keeps QEMU's screen work (dirty tracking, VNC) small on the thread that also runs the
   audio timer.
5. **Notes before pictures, on the wire.** Visual data never waits in front of a note line. The host sends visual
   data only when the note queue is empty, drops visual frames that are stale, and sends at most 20 a second.
6. **One governor decides.** It can slow or stop every visual layer. It acts on measured guest load and measured
   note health, with hysteresis.
7. **Off when not seen.** Visual work stops when the tab hides, when the editor closes, while the host renders
   offline, and when the machine sleeps. The visual work never keeps the machine awake by itself.

### 6.2 Data flow

```
 plugin (host)                                                       guest (XP)
 ─────────────                                                       ──────────
 audio thread ──> AudioRing (96 kHz, 40-50 ms ahead of output)
                       │
 viz thread  <─────────┘ every 33 ms (or 50 ms): read the newest 2048 frames
   - level L/R (peak, RMS), 16 log bands (FFT 2048), beat (spectral flux),
     a 64-point waveform, song position and tempo from the DAW transport
   - smoothing per layer is NOT done here (the guest does it per parameter)
   - pack into one 'viz' line (≤ 48 bytes)             ──COM1 (low lane)──> synth.exe COM thread (TIME_CRITICAL)
                                                                          -> shared memory "BasiliskVizShm1"
 health monitor: note-open time (SYE_OPEN), unprimes,                       (a seqlock: no locks, no waits)
   jitter buffer minimum  ──> governor level ──> 'vizgov <0..3>'        stage host (IDLE class) reads it on its
                                                                          own timer and moves the controls;
                                                                          hook DLLs (taskmgr, sndvol32, savers)
                                                                          read it from the same memory
```

- **Timing.** The analysis reads audio 40-50 ms before the plugin plays it. The guest draws within one frame. VNC
  shows it within 33 ms. So the picture is close to the sound with no extra delay. A "picture offset" parameter
  (−200..+200 ms) lets a video maker line it up with their capture setup.
- **Guest data with no host cost.** Per-voice and per-layer levels, note-ons and the playing flag are already in
  synth.exe's shared memory (`SySlot.level`, `playing`). The prototype's `bars` mode uses only these.

### 6.3 The governor

Inputs (each read every 500 ms):

| Input | Where | Bad when |
|---|---|---|
| Guest idle % | the stage host, `GetSystemTimes` (idle time is halt time in this machine) | < 25 % |
| Note open time | `SYE_OPEN` in synth.exe (ms from request to `waveOutOpen`) | median > 20 ms or any > 60 ms |
| Jitter buffer minimum | the plugin (`minAvail_`) | < 30 % of the target |
| Stream restarts | the plugin (`unprimes_`) | any while awake |

Levels (the guest and the host both know the level; the host decides it and sends `vizgov N`):

| Level | Name | What happens |
|---|---|---|
| 0 | GREEN | everything at its `fps` |
| 1 | YELLOW | half `fps`; `prio 3` layers pause; WMP renders at half size |
| 2 | ORANGE | 5 fps; only `prio 1` layers draw; screen savers are suspended (`SuspendThread`, they keep their last frame) |
| 3 | RED | nothing draws; the stage shows its last frame |

- **Up fast, down slow.** One bad sample moves the level up at once. The level moves down one step only after 5 s
  of good samples.
- **Guest-side guard.** If no `vizgov` line arrives for 2 s (a busy link), the stage host uses its own idle reading
  with the same thresholds.
- **"Pause visuals while playing"** (a check box): level 3 while any voice sounds. For people who perform live and
  capture the video later from a render.

### 6.4 The wire (v3 proposal)

Host -> guest, new lines (old guests ignore them):

| Line | Meaning |
|---|---|
| `tab vis` / `tab main` | from the tab system (section 3) |
| `vis <state>` | the `vis` setting (section 5) |
| `viz <t> <lL> <lR> <b0..b15> <beat> <pos>` | one analysis frame. Levels and bands are base-64 digits (one character each, 0-63), so a frame is about 30 bytes. `t` is a frame counter. |
| `vizw <64 chars>` | the waveform, 64 points, one base-64 character each; sent only when a layer needs it (WMP, typewriter does not) |
| `vizgov <0..3>` | the governor level |

Cost on the link: 20 frames a second x about 32 bytes = 640 bytes a second. The host already sends about 67
keep-alive bytes a second. XP's UART FIFO is off in this machine, so each byte is one guest interrupt. 640 more
interrupts a second is small next to the 1 kHz timer. If a probe shows it is not small, add COM2 as a visual-only
port (a machine change, so a new machine build).

### 6.5 Host-side rules

- The viz thread never runs on the audio thread and never takes a lock the audio thread takes. It reads
  `AudioRing::written()` and the samples, as the audio thread does.
- The viz thread has normal or below-normal OS priority. It uses about 0.1 ms per frame for a 2048-point FFT.
- `Machine::send` gets a second, lower lane: visual lines go out only after every queued note line. A visual line
  older than 100 ms is dropped.
- The VNC pull rate stays at 30 fps or less. In video mode the plugin can ask VNC for the stage rectangle only.
- The plugin does not call `touch()` for visual reasons. With the editor closed, the machine sleeps as before.
- Offline render: no `viz` lines and `vizgov 3`. The render stays the same, note for note, with the tab open or
  closed.

### 6.6 What the guest must never do for a visual

- Never call a mixer or `waveOut` function (sndvol32's hook blocks mixer writes; WMP never plays).
- Never take a lock that srhook's note thread or envelope thread takes.
- Never `SendMessage` to a Sound Recorder window from the stage host (use `PostMessage` or the strip's own timer),
  because a busy recorder thread would block the stage host, and the stage host must never block the reverse way.
- Never run a loop longer than one frame. Each frame is one timer callback.

---

## 7. Measurements

Rig: a private copy of the shipped machine 3 (base disk + state) under `~/vis-rig`, QEMU 6.2 for Linux, with the
plugin's exact devices and accelerator settings (`tcg,thread=single,tb-size=1024`, 1 vCPU, AC97 to a wav file at
96 kHz). A small VNC client pulls the screen at 30 fps like the plugin. The script sends notes over COM1 (`on`, then
`cut`), one every 0.5 s after 60 ms of silence, and measures from the send to the first loud sample in QEMU's wav
output. This is the guest part of the latency (no pipe and no jitter buffer). The host is a 16-thread PC with other
work running, so expect ±10 ms noise in the medians and more in the maxima. Screen savers ran full screen with `/s`
(the worst case: 1024 x 768 changing).

"vCPU" is the QEMU vCPU thread's share of one host core (guest busy). "main" is QEMU's main thread (I/O, timers,
VNC).

MEASUREMENTS_TABLE

### 7.1 What the numbers say

MEASUREMENTS_NOTES

### 7.2 Not possible in this machine

- **Direct3D screen savers** (3D Pipes, 3D Flying Objects, and the other 3D savers): "Could not create the
  Direct3D device." The Cirrus card has no 3D. Do not offer them.
- **WMP's own window** shows its first-run wizard in this machine. The design does not use WMP's window. It hosts
  the effects directly (V5).

### 7.3 Prototype results

PROTO_NOTES

---

## 8. Video creator mode

### 8.1 What changes

| Item | Edit view | Video mode |
|---|---|---|
| Tab strip, lists, property page, status line | shown | hidden |
| Mouse pointer | shown | hidden on the stage (the stage host sets a blank cursor; the pointer still works if moved) |
| Plugin window | the 1024 x 768 screen | the stage only, scaled by an exact factor |
| Scale filter | as now | nearest-neighbor (crisp pixels), or "sharp" (integer scale, then a smooth step to the window) |
| Governor | as section 6 | the same. Video mode never turns it off. |

### 8.2 Stage sizes

Each size fits inside the 1024 x 768 guest screen and reaches a common video size with a simple factor.

| Aspect | Stage (guest pixels) | Factor | Video size |
|---|---|---|---|
| 16:9 | 960 x 540 | x2 / x4 | 1920 x 1080 / 3840 x 2160 |
| 16:9 (small) | 640 x 360 | x3 | 1920 x 1080 |
| 9:16 (Shorts, Reels, TikTok) | 360 x 640 | x3 | 1080 x 1920 |
| 1:1 | 540 x 540 | x2 | 1080 x 1080 |
| 4:5 | 540 x 675 | x2 | 1080 x 1350 |
| 4:3 | 1024 x 768 (the whole screen) | x1 / x1.40625 | 1024 x 768 / 1440 x 1080 |

### 8.3 Recording tips (for the help text)

1. Record the DAW's audio from the DAW (a render or a loopback), not from the speakers.
2. Capture the plugin window with a window capture (OBS "Window Capture" or the system recorder) at 30 or 60 fps.
   The stage changes at most 30 times a second.
3. Set the capture to the exact video size in 8.2, so no second scaling blurs the pixels.
4. Line up the picture: play a click track; adjust "picture offset" until the meters jump on the click.
5. For a perfect take, use **Frame dump** (below) and build the video offline.
6. Keep other heavy programs closed. The governor protects the sound, so a busy PC means a calmer picture, not a
   worse sound.

### 8.4 Frame dump (optional)

The plugin already has a debug frame dumper (`BSYNTH_DUMP_FRAMES`). A "Frame dump" button writes the stage as PNG
files with the DAW song time in the name, while the DAW plays or renders in real time. A video tool then joins them
with the rendered audio at an exact frame rate. This removes capture drops. It is host-side work only: the guest
does not do more.

---

## 9. Effort and order

| Step | Work | Size | Depends on |
|---|---|---|---|
| 1 | **Priority fixes** (good for the main view too): COM reader thread TIME_CRITICAL; Task Manager BELOW_NORMAL after assembly. Measure note spread before and after with the rig. | 0.5 day | nothing |
| 2 | Host analysis thread + `viz` low lane + `vizgov`; health monitor | 2 days | nothing |
| 3 | Stage host in synth.exe (or a separate `stage.exe` at IDLE class): the tab page, scenes, layers list, property page, shared memory | 3 days | the tab system (preset-engine-2) |
| 4 | V1 scope wall, V2 progress-bar spectrum, V8 clock, V9 backdrop, V6 Marquee/Starfield preview | 2 days | 3 |
| 5 | Video mode in the plugin UI: stage crop, scale, pointer, sizes | 1.5 days | 3 |
| 6 | V5 WMP effects (from the prototype), V7 copy animation | 2 days | 2, 3 |
| 7 | V3 Task Manager hook (probe first), V4 sndvol32 hook | 3 days | probe |
| 8 | 3.11: scope wall, scroll-bar meters, Clock, savers as children (probe) | 3 days | 2 |
| 9 | Frame dump | 1 day | 5 |

Steps 1 to 5 give a useful tab in about two weeks. Step 1 can ship alone, now.
