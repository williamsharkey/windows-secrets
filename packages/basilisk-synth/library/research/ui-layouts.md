# UI layouts: what popular soft synths do, and how our 16-recorder synth could look

Research note for BASILISK SYNTH (XP) and BASILISK 16 (3.11). The question is which layouts of well-known synths are
worth borrowing for a UI built only from real Windows program parts.

**How this was checked.** Rob Papen colours were checked against the official screenshots on robpapen.com, using
Wayback snapshots for the old versions. Other layout facts come from manuals and reviews (see Sources). Lines marked
*(memory)* were not re-checked against a screenshot in this pass.

---

## 1. Which products the user means

| User's words | Product | Evidence |
|---|---|---|
| "albino" | **LinPlug Albino** (1, 2, 3; now sold as Rob Papen *Albino 3 Legend*). Rob Papen made many of its factory sounds, and Rob Papen now distributes it. | robpapen.com `albino-3-legend.html`; the screenshot carries "Rob Papen / powered by LinPlug". |
| "blue" | **Rob Papen Blue** (2006, built with RPCX), **Blue II** (2014), **Blue III** (current). | robpapen.com `blue.html` (Wayback 2011) and `blue3.html`; Sound On Sound reviews of Blue and Blue 2. |
| "the other Rob Papen design that was red and whitish" | **Rob Papen Predator** (most likely). **Vecto** is the runner-up. | See below. |

**Why Predator.** These are the colours in the official screenshots:

- **Predator (1, 2008):** the top half is a black panel with **red knob caps** and red LCD readouts. The lower half is
  **light grey/white** panels holding the arp grid, FX and preset sections, with red-on-black displays.
- **Predator 2 and 3:** the whole panel is **off-white/light grey**, and every knob has a **red value ring**. A dark
  display strip runs across the middle. This is the closest match to "red and whitish". Predator was also Papen's
  flagship and best seller, and the SubBoomBass reviews describe it as the design the other synths copied.
- **Vecto (2022):** a light grey/white panel with **red section headers**, a red ring around the vector pad and red
  knobs. The colours match just as well, but Vecto is newer and far less widely known, so it is the runner-up.
- **The others do not match:**

  | Product | Colours |
  |---|---|
  | Punch (1) | grey with **cyan** displays |
  | Punch 2 | dark grey/cyan |
  | SubBoomBass 1 and 2 | **orange/amber** on black |
  | RAW / RAW 2 | **green** on grey/black |
  | Blade / Blade 2 | **dark navy** with blue glow (SOS: "dark and brooding … glowing blue text") |
  | Go2 | **black/teal** |
  | Blue / Blue III | **blue/white** |

- **Albino is itself red and white.** Albino 3 Legend is a silver/white chassis with **red-on-black LED displays and
  red knobs**. If the user's memory is fuzzy, the "red and whitish" image may partly be Albino. Albino and Predator
  share that look, and both are worth copying.

---

## 2. Layouts, product by product

Notation: zones run **top to bottom, then left to right**. *KB* is the on-screen keyboard. *PB/MW* are the pitch bend
and mod wheel.

### LinPlug Albino 3 (Legend)
- **Zones:**
  - Two rows of **OSC 1 / OSC 2** on the left, each a framed sub-panel with knobs and a red LED readout.
  - **FILTER 1 / FILTER 2** in the middle, each with its own little LED parameter row.
  - **AMP** in a narrow column on the right.
  - Third row: **ENV** with four small envelope-shape thumbnails, then the **ARPEGGIATOR** as a red-on-black step table.
  - Fourth row: **FX** and **MASTER**, holding the preset name LED, glide, voices and ECS/CHORD buttons.
  - Bottom: a full-width **layer table** in a dark tray. It has rows *Layer 1–4* and these columns: location, layer
    name, **vol, pan, note offset**, filter, **PW MW AT SP enable toggles**, **key-range, vel-range**.
- **KB:** none in the panel. **PB/MW:** there are no wheels. Each layer has a toggle that says whether it *responds* to
  PW/MW/AT/sustain.
- **Colours:** silver/white brushed chassis, red knobs, red-on-black 7-segment-style LEDs. A KVR reviewer liked the
  look but found the red-on-black text hard to read in the matrix.
- **Why it works:** every module is a framed box with a title tab, and the layer table is a spreadsheet. **The layer
  table is the single best model for our per-sound layer section** (see §3).

### Rob Papen Blue / Blue II / Blue III
- **Zones:**
  - Blue 1 starts with **six oscillator columns A–F** side by side across the top. Each column has a waveform name
    box, Free/Inv/Trk buttons, mode, ratio and knobs.
  - Below them is a **FILTER** strip with two filters as one long knob row.
  - Then a **tab bar**: Presets, Easy, Alg, PD/WS, Env, Multi-Env, LFO, Mods, Step Seq, Arp/Seq, FX, Global.
  - Under the tabs is a **large shared page area** that holds the preset browser as a list of names plus banks.
  - The footer has the logo, a parameter readout LCD and a master volume.
- **Blue II/III:** Blue II moved Presets/Easy/FX into the upper strip and added a **right-hand column** with a global
  AMP ADSR and a PLAY section (SOS). Its lower half is an **XY pad** on the left beside a tabbed display. The Mods tab
  has 20 slots.
- **KB:** none. **PB/MW:** these are mod sources in the matrix. Blue II/III have a pitch-bend range in Play.
- **Colours:** pale blue-grey panels, navy LCD fields, white text. Blue III is darker navy.
- **Why it works:** the six identical oscillator columns read like a mixing desk. Everything editable sits in the top
  half, and the bottom half is one swappable "screen". **This is the pattern for 16 identical recorder strips.**

### Rob Papen Predator (1/2/3)
- **Zones:**
  - **Predator 1:** the top row is OSC1, OSC2, OSC3, FILTER, F2 and FILTER LFO/AMP, with the filter envelope and amp
    ADSR under their sections. The bottom row is Pitch-mod LFO / P-Bend, the **ARP/step grid** (16 columns), FX, and
    PLAY MODE + **PRESET** (bank, name, variation knob, morph).
  - **Predator 3:** the **header** strip holds preset, bank, EDIT/ORIG and a "Fun Display". Below it come OSC 1–3 (each
    with a little waveform scope), FILTER 1/2 with their envelopes, and ROUTING. Then the lower half has an **XY pad**
    on the left and a **big tabbed display** in the middle (Arp, XY, Env-LFO-AF, Mod, EQ, Special, Play mode) showing
    a 3-D wave plot. AMP and EFFECTS are in the right column.
- **KB:** none. **PB/MW:** a P-BEND range box in the pitch-mod section, and MW as a matrix source.
- **Colours:**
  - Predator 1: black top, light grey bottom, red knobs, red LCD readouts.
  - Predator 2/3: off-white panels, **red value arcs**, a dark display.
- **Why it works:** the same knob style is used everywhere, and red only marks the value. Section titles are small caps
  in the panel's top-left. There is one big dark display in a light panel.

### Rob Papen Vecto
- **Zones:**
  - A **header** with preset/bank and a manager.
  - Four oscillator blocks around a **central red-framed vector pad** (a spider-web path display).
  - FILTERS, AMP and PLAY MODE in the right column.
  - MODULATION as a table bottom-left, then LFO, ARP and ENVELOPES strips along the bottom.
  - **PB/MW as two vertical sliders at bottom-left.**
- **Colours:** light grey/white, red headers and pad frame.

### Native Instruments Absynth (5, 6)
- **Zones:**
  - Absynth 5 has separate windows: Browser, Attributes, Perform, Patch, Effect, Wave, Envelope and LFO (manual).
  - **Absynth 6:** an always-visible **header** (preset selector, Save, Undo, **Mutate**, seven page buttons, meters,
    CPU) above one large **page** area. The **Macro row is "always visible at the bottom"**: 8 knobs, paged to 16.
  - The Patch page shows **three oscillator channels as horizontal rows** of module slots (osc, filter/mod, waveshaper)
    feeding a main channel.
  - The Envelope page is a **huge drawn breakpoint envelope** editor.
- **KB:** none in the plugin.
- **Colours:** charcoal, white text, a single highlight colour.
- **Why it works:**
  - The signal flow reads left to right in rows.
  - Envelopes get the whole screen.
  - Macros never move.
  - *Mutate* sits in the header. We already have `Mutate` in the XP menus, so put it in the header too.

### Native Instruments Massive *(memory, plus the manual's structure)*
- **Zones:**
  - The **header** has the browser/preset name and the **8 macro knobs in the top right**.
  - Middle: OSC1–3 plus noise and modulation osc in a **left column**, then Filter 1/2, Amp and Bypass, then FX1/FX2
    and EQ, all on the right.
  - Bottom: a **tabbed modulation panel** holding 4 envelopes and 4 LFO/Stepper/Performer slots, shown as large
    graphs.
- **Colours:** dark grey, blue mod indicators.
- **KB:** none. **PB/MW:** on a Voicing/Routing tab.
- **Why it works:** drag-and-drop mod sockets show numbered, coloured links, and the large envelope graph is at the
  bottom.

### Native Instruments FM8
- **Zones:**
  - A **header**.
  - The **Easy/Morph page**: a few timbre knobs, effect knobs and a large **X/Y morph square**.
  - The **Expert pages**: an **FM matrix** grid (operators A–F plus X/Z) and per-operator envelopes.
- **KB:** a full-width keyboard strip along the bottom in standalone, with **PB/MW wheels to its left**
  *(memory; NI community threads confirm a working virtual PB/MW)*.
- **Colours:** dark grey/silver, orange/amber highlights.
- **Why it works:** a matrix grid is a natural "table" control, and our Character Map grid is one.

### Kontakt instruments (the most common third-party layout)
- **Zones:**
  - The Kontakt **rack header**: instrument name, output, voices, MIDI channel, tune, volume and pan.
  - The **performance view** below it. This is a scripted wallpaper whose base width is **633 px** (up to 1000 px in
    later versions), with the height set by `set_ui_height_px`.
  - Typical instrument UIs fill it with a hero image across the top, a **row of 4–8 big knobs** in the middle (often
    macros named like "Attack/Release/Tone/Reverb"), and tabs for Main/Mod/FX/Seq.
- **KB:** Kontakt's own **85-key on-screen keyboard** runs the full width of the window at the very bottom. Keys are
  colour-coded: mapped zones in blue, keyswitches in red. It is about **1/10 of the window height**, roughly 70–90 px
  tall on a ~1000 px wide window. **PB/MW are two thin vertical wheels at the left end of the keyboard.**
- **Why it works:** it is the de facto standard players expect. The keyboard colours tell you which keys make sound.

### Spectrasonics Omnisphere 2
- **Zones:**
  - The **header** has the patch name, browser toggle, multi/part tabs 1–8 and utility.
  - The **Main page** is the "dashboard": a **large centre area** with a Notes View and a **Layers View of four layers
    A–D**, each with a **level slider** to blend them. A **Master Filter** applies to all layers.
  - Flanking columns hold the global controls. Separate **Layer pages** hold oscillator, filter, envelopes, LFOs and
    mod.
  - The **Orb** (a circular gesture controller) sits on the Main page.
- **KB:** none in the plugin.
- **Colours:** dark slate/blue with backlit-glass panels.
- **Why it works:** one overview page shows all layers as a small mixer, and the deep editing is one click away per
  layer. **Copy this "overview + per-layer page" split.**

### u-he Zebra2 / Diva *(memory)*
- **Zebra2:**
  - Top-left is a **synthesis grid** of 4 columns × 4 rows of module slots, with the signal flowing down.
  - A **tabbed lower panel** shows the selected modules.
  - On the right are **4 XY pads**, envelope/LFO tabs and a mod matrix.
  - Grey with blue accents. No KB.
- **Diva:**
  - **Horizontal strips** stacked like a real synth: Main, Modifications, Osc, HPF, Filter, Amplifier, Envelope 1,
    Envelope 2, LFOs, Effects. Each strip's colour/skin follows the model chosen.
  - No KB.
- **Why it works:**
  - Zebra2 shows that a grid can carry the architecture.
  - Diva shows that strips of uniform height scan very fast. That suits our strips.

### reFX Nexus (2, 3, 4)
- **Nexus 2** *(memory)*:
  - A big central "LCD" screen with tabs: Library, Mod, Arp, Trancegate, Mixer, FX.
  - Macro knobs on either side.
  - A **full-width keyboard at the bottom with PB/MW wheels to its left**.
- **Nexus 4:** a top bar with search, preset, CPU and output, then a **Preset Librarian** in three columns (Folder |
  Categories | Presets, with colour-coded attributes), then a **Macros** section and a Mod matrix. Generators are
  grouped into **layers**, more than 6. Assigned modulation shows as an **orange ring** on the knob (edmprod).
- **Why it works:** the browser *is* the product, and the three-column librarian is the fastest preset browsing of any
  of these.

### Arturia Analog Lab (4, V)
- **Zones:**
  - The **header** has the logo, preset name, prev/next, and Explore/Play toggles.
  - **Explore:** a big preset **browser** with type/style/bank filters and a result list.
  - **Play:** a picture of the source instrument, plus a **row of macros labelled Brightness, Timbre, Time, Movement**
    and FX/mix controls.
- **KB:** a **virtual keyboard along the bottom**, about 10% of the height, with **PB and MW wheels on its left**. The
  manual has a "Virtual Keyboard" section.
- **Why it works:** four plain-English macros cover most tweaking. **Our 4 macros should get names like these.**

### LennarDigital Sylenth1 *(memory)*
- **Zones:**
  - The left half has **4 oscillators in a 2×2 grid**: Part A osc 1/2 and Part B osc 1/2, two parts layered.
  - The centre has **Filter A / Filter B** and the filter controller.
  - On the right are the **Amp Env A/B, Mod Env 1/2 and LFO 1/2**, each with a destination dropdown pair. Modulation
    is assigned in place; there is no separate matrix page.
  - The bottom-right is a **tabbed "display" box** for Arp, Effects, Mixer and Menu, with an LCD showing the selected
    parameter.
  - PB/Mono/Portamento sit in a small Misc block.
- **Colours:** slate blue/grey, light-blue LCD text.
- **KB:** none.
- **Why it works:** it fits on one page and every control is visible. Layering two parts reads as A/B.

### Xfer Serum *(memory)*
- **Zones:**
  - The **header** has the preset name and arrows, a menu and the CPU meter, plus **page tabs** OSC, FX, MATRIX and
    GLOBAL.
  - The **OSC page** has OSC A and OSC B as large wavetable displays side by side, with Sub and Noise in a narrow left
    column and the Filter on the right.
  - The **bottom band** holds **ENV 1–3 and LFO 1–4** in one tabbed, large graph editor. Assignments are made by
    dragging.
  - **4 macros are at bottom-left.** Voicing/porta are at bottom-right.
- **KB:** none. **PB:** a range box in the bottom bar.
- **Colours:** charcoal, cyan/blue graphs.
- **Why it works:**
  - The envelope/LFO graph is big and always in the same place.
  - Macros sit at the corner.
  - Animated wave displays show what is playing. Our green Sound Recorder waves do the same job.

### Hardware romplers' front panels *(memory)*
- **Roland D-50:**
  - A 61-key board.
  - **Bender/mod lever left of the keys** (one combined Roland paddle).
  - A centre **2×40 backlit LCD**.
  - A **joystick** for tone balance.
  - Rows of membrane buttons for Upper/Lower × Partial 1/2. That is a *4-sound layer structure shown as buttons*.
- **Roland JV-1080 (1U rack):**
  - A big backlit LCD left of centre.
  - Groups of **Tone 1–4 select/on buttons**, which toggle each of the patch's 4 layers.
  - Patch/Performance/Rhythm mode buttons.
  - A **value dial** on the right.
- **E-mu Proteus/1:**
  - 1U, a **2×16 LCD**, a data knob, a master volume knob and a few buttons.
  - Minimal. The preset *number + name* is the whole UI.
- **Korg M1:**
  - A 61-key board with a **joystick left of the keys** (X = PB, Y = mod/vibrato).
  - A **2×40 LCD**.
  - A numeric pad, 0–9 bank buttons and a value slider.
- **Lessons:**
  - The "**Tone 1–4 on/off**" button row is the classic layer section.
  - The **number pad + 2-line LCD** preset browser is iconic. 3.11 Calculator buttons can play exactly that role.
  - **Bend controls always sit at the left end of the keyboard.**

### Patterns common to all of them
1. A **header strip** (preset name, prev/next, bank, save/manager) is always at the top, one row tall, and spans the
   whole width.
2. **Sources come before shaping, and shaping before output**, reading left to right or top to bottom. Effects are on
   the right or behind a tab.
3. **One large display region** (envelope, wave, XY, browser) sits in the lower-middle and is swapped by tabs.
4. **Macros, 4 to 8 of them, are fixed and always visible**: top-right in Massive, bottom-left in Serum, a bottom row
   in Absynth 6.
5. **A keyboard, when present, is at the very bottom.** It spans the full width and is about 8–12% of the window
   height. **PB/MW are two narrow vertical controls at its left end.**
6. **Layers are a small table or mixer** with rows for layers and columns for level, pan, transpose, key range and
   on/mute (Albino, Omnisphere, JV Tone buttons).
7. **Restraint with colour:** a neutral panel, one accent colour for values (Predator's red arcs, Nexus's orange
   rings), and one dark display.

---

## 3. Recommended layout for the 16-recorder synth

Our raw material: **16 Sound Recorder strips**, which already glide into place, and up to **8 DNA layers**. The UI
shows **1–6 layers**. We have **4 macros** (`Macro 1-4`), **per-layer breakpoint envelopes** (`lenv`), and a library +
preset browser.

### Zone → real Windows part

| Zone (borrowed from) | XP part | 3.11 part |
|---|---|---|
| **Header / preset browser** (Nexus librarian, Analog Lab Explore, Proteus LCD) | An Explorer-style **ListView** in Details view (Category, Name, Layers) beside a **TreeView** of the library CD folders. A title bar with ◀ ▶ buttons for prev/next and a menu bar (Effects, Edit, Voices, Layers, **Mutate**, Undo). | A **File Manager** split pane (directory tree + file list) for the library. A preset number/name in a **Calculator** display, with Calculator digit buttons to type a preset number (Proteus/M1 style). |
| **Sources: 16 voice strips** (Blue's six osc columns, Diva strips) | 16 **Sound Recorder** strips: the green wave, seek slider, ◀◀ ▶ ■ ●. These are the voices. Group them visually by layer, with each layer's pool `#N` contiguous. | 16 **SOUNDREC** strips, the same idea. A 3.11 SOUNDREC window is smaller, so they fit 4×4. |
| **Layer section, 1–6 rows** (Albino layer table, Omnisphere layer mixer, JV Tone 1–4) | **Volume Control** (`sndvol32`) channel strips: one per layer, each with a vertical **level** trackbar (`L`), a **balance** trackbar for pan, a **Mute** checkbox and the layer name as the channel label. A **ListView row** per layer to the side shows source, `#N`, key range, `F` and the step count. | **Control Panel › Sound / Desktop / Mouse sliders** (horizontal scrollbars) as level/pan, one row per layer. Calculator-style **buttons** for Layer 1–6 on/off, a direct copy of the JV-1080 Tone buttons. |
| **Envelope graph** (Serum/Massive bottom band, Absynth's Envelope page) | **Task Manager › Performance**: the CPU Usage History graph shows the selected layer's `lenv` (green on black grid). The PF Usage bar is the current level meter. The existing **XP trackbar envelope editor** under the strips is the place to edit breakpoints. | **Clock** (analog face) as an "envelope time" dial. A **Paintbrush** or **Media Player** scale/slider strip for the envelope curve. |
| **4 macros** (Analog Lab's Brightness/Timbre/Time/Movement; Serum bottom-left) | Four **trackbars** from **Mouse Properties** (Pointer speed, Double-click speed) and **Keyboard Properties** (Repeat delay, Repeat rate). Each has a built-in "Slow … Fast" caption, so relabel them **Tone / Body / Time / Motion**. | Four **Control Panel** sliders (Mouse tracking speed, Double-click speed; Keyboard delay and rate). These are 3.11's only native sliders besides scrollbars. |
| **Mod wheel / pitch bend** (left of the keys on every keyboard UI) | Two **vertical trackbars** from the **Volume Control** at the far left of the keyboard. PB springs to the centre detent; MW stays where it is left. | Two vertical **scrollbars**, or Media Player's position slider turned on end. |
| **Keyboard** (Kontakt, Analog Lab, FM8) | **On-Screen Keyboard (`osk.exe`)**: real keys, already drawn by XP. Use the QWERTY rows as a 2.5-octave "tracker" keyboard: Z–M is the lower octave, Q–I the upper, with S D G H J and 2 3 5 6 7 as black keys (FL/Ableton style). | **Character Map** grid (32×7 cells) as the key strip. Map one row to the white keys and highlight the cells of held notes. Or use a row of **Calculator** buttons. |
| **Clock / tempo / transport** | The **Date and Time** analog clock (already a donor) as the arp/LFO rate indicator or "time" macro display. | **Clock.exe**. |
| **Voice usage / CPU** | The **disk-usage pie** from the Drive Properties page shows the share of the 16 recorders held by each layer (pool split), which a pie suits well. | n/a (or Calculator memory "M" as the voices-busy flag). |

### Colour and type rules
- Keep the **Luna** (XP) or **3.11 grey** chrome untouched. That is the brand.
- Use exactly **one accent**, taken from the parts themselves:
  - **Sound Recorder green-on-black** is our "display" colour, like Predator's dark centre strip.
  - Selected-state blue is the highlight.
- Do **not** add red LEDs. That is Albino's job, and recoloured Windows parts stop looking real.
- Title each zone with a real **group box** caption ("Layers", "Envelope", "Macros"). That is our version of
  Albino's/Predator's small-caps section headers.

### Layer section in detail (adapted from Albino's table)

```
 Layers ───────────────────────────────────────────────────────────────────────────
 #  On  Source     Voices  Level    Pan       Key        Vel     Steps   Env
 1  [x] chimes     6 ▮▮▮▮▮▮  ═══▼══   ══▼══    C1–C6      1–127   12      ▁▃▇▅▂
 2  [x] ding       4 ▮▮▮▮    ══▼═══   ▼════    C1–C4      1–100    5      ▇▃▁▁▁
 3  [ ] chord      3 ▮▮▮     ═▼════   ════▼    C3–C6      1–127    0      ▅▅▅▅▃
 …  up to 6 rows; rows beyond the DNA's layers are greyed out (disabled ListView items)
```

### XP mockup (1024×768)

```
┌─ BASILISK SYNTH ─────────────────────────────────────────────────────────────── _ □ X ┐
│ File  Effects  Edit  Voices  Layers  Mutate  Undo  Help                               │
├───────────────────────────────────────────────────────────────────────────────────────┤
│ [◀][▶] Pads: Frutiger Morning     Bank: Library CD  [Save] [Mutate]   ◔ pie  🕓 clock │  ← header 40px
├──────────────────────────────── 16 Sound Recorder strips (4 × 4) ─────────────────────┤
│ ┌Sound-1 L1┐ ┌Sound-2 L1┐ ┌Sound-3 L1┐ ┌Sound-4 L1┐  each: green wave, seek slider,     │
│ │~~~▁▃▇▅▂~~│ │~~▁▃▇▅▂~~~│ │~▁▃▇▅▂~~~~│ │▁▃▇▅▂~~~~~│  ◀◀ ▶ ■ ●  (Play lights per voice)  │
│ │◀◀ ▶ ■ ● ═│ │◀◀ ▶ ■ ● ═│ │◀◀ ▶ ■ ● ═│ │◀◀ ▶ ■ ● ═│                                     │  ← 4 rows,
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘  strips grouped by layer;             │    ~360px
│   … rows 2–4 (Sound-5 … Sound-16) …                  layer number in each title bar      │
├───────────────────────────────────────────┬───────────────────────────────────────────┤
│ Layers (ListView + Volume Control strips) │ Envelope – Layer 2 (Task Manager graph)   │
│ # On Source  #N  Lvl  Pan  Key    Steps   │ ┌─────────────────────────────────────┐   │  ← ~200px
│ 1 [x] chimes  6  ▐█▌  ◄►  C1–C6   12      │ │  ▁▃▇█▇▆▅▅▅▅▅▄▃▂▁    (CPU history)   │   │
│ 2 [x] ding    4  ▐█▌  ◄►  C1–C4    5      │ └─────────────────────────────────────┘   │
│ 3 [ ] chord   3  ▐▌   ◄►  C3–C6    0      │  breakpoint trackbars: ┃ ┃ ┃ ┃ ┃ ┃ ┃ ┃     │
│ 4–6  (greyed)                             │  PF bar = live level ▕████░░░▏            │
├───────────────────────────┬───────────────┴───────────────────────────────────────────┤
│ Macros (Mouse/Keyboard    │  Presets  ┌Category─┐┌Name──────────────┐                  │
│ trackbars)                │           │Pads     ││Frutiger Morning  │                  │  ← ~70px
│ Tone   Slow ═══▼═══ Fast  │           │Keys     ││Mallsoft Escalator│                  │
│ Body   Slow ══▼════ Fast  │           │Bells    ││Y2K Boot Chime    │                  │
│ Time   Short ════▼═ Long  │           └─────────┘└──────────────────┘                  │
│ Motion Slow ═▼═════ Fast  │                                                            │
├────┬──────────────────────┴───────────────────────────────────────────────────────────┤
│ PB │ On-Screen Keyboard (osk.exe)                                                     │
│ ║  │ [Esc][F1]…  [`][1][2][3][4][5][6][7][8][9][0][-][=][Bksp]                        │  ← ~110px
│ ▼  │ [Tab][Q][W][E][R][T][Y][U][I][O][P][[][]]   ← upper octave (2 3 5 6 7 = black)   │    (~14% of
│ MW │ [Caps][A][S][D][F][G][H][J][K][L][;][']     ← S D G H J = black keys             │    height,
│ ║▼ │ [Shift][Z][X][C][V][B][N][M][,][.][/]       ← lower octave                       │    full width)
└────┴──────────────────────────────────────────────────────────────────────────────────┘
```

Proportions:

| Zone | Height | Share |
|---|---:|---:|
| Header | ~40 px | ~5% |
| Strips | ~360 px | ~47% |
| Layers + envelope | ~200 px | ~26% |
| Macros + browser | ~70 px | |
| Keyboard | ~100 px | ~13% |

The strips are the hero, as Blue's oscillator columns are. The keyboard spans the full width, with PB/MW in a ~40 px
column on its left.

If the window is too short, follow Omnisphere and Blue: put the **browser and layers on one tabbed area** and swap
them, rather than shrinking the strips.

### 3.11 mockup (800×600; at 640×480, drop the browser list into a tab)

```
┌─ BASILISK 16 ───────────────────────────────────────────────────────────── ▼ ▲ ┐
│ File  Effects  Edit  Voices  Layers  Mutate                                     │
├──────────────────────────────────────────────────────────────────────────────────┤
│ ┌Calculator display┐ [7][8][9] [◄][►]   Bank: LIBRARY   [Save]     ⌚ Clock     │ ← Proteus/M1
│ │ 042 GLASS PAD    │ [4][5][6]                                                  │   style preset
│ └──────────────────┘ [1][2][3][0]                                               │   browser, 70px
├──────────────── 16 SOUNDREC strips (4 × 4, 3.11 grey, black/green wave) ────────┤
│ [Snd1 ~▁▃▇▅~ ◀◀▶■●]  [Snd2 ...]  [Snd3 ...]  [Snd4 ...]                         │ ← ~240px
│ [Snd5 ...]  [Snd6 ...]  [Snd7 ...]  [Snd8 ...]                                  │
│ [Snd9 ...]  [Snd10 ...] [Snd11 ...] [Snd12 ...]                                 │
│ [Snd13 ...] [Snd14 ...] [Snd15 ...] [Snd16 ...]                                 │
├────────────────────────────────────────┬─────────────────────────────────────────┤
│ Layers  (JV-1080 "Tone" buttons)       │ Envelope (Media Player scale + Clock)   │
│ [1●][2●][3○][4○][5○][6○]               │ 0 ──┬───┬───┬───┬── 100%                │ ← ~130px
│ Level  ◄▒▒▒▒█▒▒▒►  (Control Panel)     │     ▁▃▇▇▅▃▂▁                            │
│ Pan    ◄▒▒█▒▒▒▒▒►                      │ ◄▒▒▒▒▒█▒▒▒▒▒▒▒►  (MPlayer slider)       │
├────────────────────────────────────────┴─────────────────────────────────────────┤
│ Macros (Mouse / Keyboard Control Panel sliders)                                  │
│ Tone ◄▒▒█▒▒► Body ◄▒█▒▒▒►  Time ◄▒▒▒█▒► Motion ◄█▒▒▒▒►                           │ ← 40px
├──┬───────────────────────────────────────────────────────────────────────────────┤
│PB│ Character Map grid as keys:                                                   │
│▒ │ │ │█│ │█│ │ │█│ │█│ │█│ │ │█│ │█│ │ │█│ │█│ │█│ │ │  (held notes = selected)  │ ← ~80px
│MW│ │C│ │D│ │E│F│ │G│ │A│ │B│C│ │D│ │E│F│ │G│ │A│ │B│ │                            │   (~13%)
└──┴───────────────────────────────────────────────────────────────────────────────┘
```

**At 640×480:**
- Strips become 4×4 at ~150×55 px each.
- The Layers and Envelope panes become **two tabs** in one 110 px area.
- Macros and PB/MW share the keyboard row: PB/MW on the left, macros as four small sliders on the right of a shortened
  CharMap row.

### Priorities, if only some of this gets built
1. **Keyboard strip at the bottom with PB/MW on its left.** Every keyboard-bearing synth does this, and players look
   for it.
2. **Layer table** (Albino) with level and pan from Volume Control.
3. **Macros always visible**, with four plain names (Analog Lab).
4. **One large envelope display** in a fixed place (Serum, Massive, Absynth): the Task Manager graph.
5. **Header browser with prev/next**, then a full librarian (Nexus) in a tab.

---

## Sources

**Rob Papen and LinPlug, official pages and screenshots**
- Albino 3 Legend: https://www.robpapen.com/albino-3-legend.html (screenshot `/images/Albino-3_Legend/RobPapen_Albino-3_Legend_Shadow400px.png`)
- Predator 3: https://www.robpapen.com/Predator-3.html (screenshot `/images/Predator-3/RobPapen_Predator-3_Shadow_HomePage_400.png`)
- Predator 1 (Wayback 2011): http://web.archive.org/web/20110208090323/http://robpapen.com/predator.html (screenshot `Rob_Papen_Predator_screenshot_.jpg`)
- Predator 2 (Wayback 2020): http://web.archive.org/web/20200117212236/https://www.robpapen.com/Predator2.html
- Vecto: https://www.robpapen.com/Vecto-vst.html (screenshot `RobPapen_Vecto_vst.png`)
- Blue 1 (Wayback 2011): http://web.archive.org/web/20110208091911/http://robpapen.com/blue.html
- Blue III: https://www.robpapen.com/blue3.html
- Punch 1 (Wayback 2013): http://web.archive.org/web/20131209064349/http://www.robpapen.com/punch.html
- Punch 2: https://www.robpapen.com/Punch2.html
- SubBoomBass 1 (Wayback 2012): http://web.archive.org/web/20120102053514/http://www.robpapen.com:80/subboombass.html
- SubBoomBass 2: https://www.robpapen.com/subboombass-2.html
- RAW 2: https://www.robpapen.com/RAW-2.html
- Blade 2: https://www.robpapen.com/BLADE-2.html
- Go2: https://www.robpapen.com/go2-re-main.html

**Rob Papen and LinPlug, reviews**
- Sound On Sound, Blue 2: https://www.soundonsound.com/reviews/rob-papen-blue-2
- MusicRadar, Blue II: https://www.musicradar.com/reviews/tech/rob-papen-blue-ii-601399
- Sound On Sound, Blade ("dark and brooding"): https://www.soundonsound.com/reviews/rob-papen-blade
- Age of Audio, SubBoomBass (copies Predator's design): https://ageofaudio.com/en/rob-papen-subboombass/
- KVR user review, Albino (red-on-black displays): https://www.kvraudio.com/reviews.php?user=4036
- Albino 3 manual (2006): https://www.scribd.com/doc/65087825/Albino-3-Manual-300

**Native Instruments**
- Absynth 6 overview (header, pages, bottom macro row): https://docs.native-instruments.com/online-guides/absynth-6-user-guide/en/absynth-6-overview
- Absynth 5 reference manual (windows list): https://www.deepsonic.ch/deep/docs_manuals/native_instruments_absynth_v.5.0_reference_manual.pdf
- FM8 manual (Easy/Morph and Expert pages): https://www.deepsonic.ch/deep/docs_manuals/native_instruments_fm8_v.1.0_manual.pdf
- FM8 virtual PB/MW (NI community): https://community.native-instruments.com/discussion/28158/fm8-and-pitch-bend-wheel
- Kontakt 633 px base width: https://community.native-instruments.com/discussion/comment/45745
- Kontakt `set_ui_width_px` / `set_ui_height_px`: https://danielrdehaan-website.pages.dev/garden/knowledge/sampling-instruments/kontakt/kontakt-basic-user-interface-creation/
- KSP UI commands: https://www.native-instruments.com/ni-tech-manuals/ksp-manual/en/user-interface-commands.html
- Kontakt 85-key keyboard: https://community.native-instruments.com/discussion/comment/23298

**Other synths**
- Omnisphere 2 Layers A–D and Main page: https://support.spectrasonics.net/manual/Omnisphere2/25/en/topic/layers
- Omnisphere 2 manual index: https://support.spectrasonics.net/manual/Omnisphere2/main
- Nexus 4 layout (edmprod): https://www.edmprod.com/refx-nexus-4/
- Nexus 2 manual: https://www.scribd.com/document/380627053/Nexus-2-Manual-English-pdf
- Analog Lab macros (KVR thread): https://www.kvraudio.com/forum/viewtopic.php?p=8296634
- Analog Lab manual: https://downloads.arturia.com/products/analoglab/manual/Analog_Lab_Manual_1_1_EN.pdf
- Analog Lab V manual: https://manualsnet.com/arturia/analog-lab-v

**Not re-verified in this pass:** the Zebra2/Diva, Sylenth1, Serum, Massive and hardware panel descriptions (marked
*memory*). Check them against the u-he, LennarDigital and Xfer manuals and the Roland/E-mu/Korg owner's manuals before
quoting them as exact.
