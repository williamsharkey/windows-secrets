# BASILISK SYNTH: preset artwork (design, v3 proposal)

Status: design. Nothing here is built. This file does not change `DNA.md`. The "art recipe" below is a proposal for
a v3 state key. It lives beside the DNA. It is not part of the DNA string.

Related designs:

- `VISUALIZERS.md` (same folder). The artwork uses the same priority, throttle and "never disturb the sound" rules.
  Section 6 of that file is the shared performance design. This file refers to it as "the governor".
- `design/preset-engine-2` (another lane) owns the editor tab system. The artwork setting is one page of that
  system. Section 2 says what this design needs from it.
- `design/aesthetic-presets` (another lane) owns the names of the sound packs and the aesthetic presets. Section 8
  uses placeholder pack names. Replace them with that lane's names when it publishes them.

---

## 1. What it is

When the visitor changes the preset, Windows paints a new background under the synth. Real Windows programs do the
painting while the visitor watches:

- **Paint** (`mspaint.exe`) with its own tools: Brush, Airbrush, Line, Curve, Rectangle, Ellipse, Polygon, Fill
  With Color, Text, Select and the Image menu (Flip/Rotate, Stretch/Skew, Invert Colors).
- **Paint's selection tricks**: a selection dragged with Shift held leaves a trail (a "custom brush"). A selection
  dragged with Ctrl held leaves one copy. These two tricks make the repeated patterns.
- **Other Windows parts**: desktop wallpaper (tiled, centered, stretched), the classic desktop patterns, the
  window color schemes, Character Map glyphs (Webdings, Wingdings, Symbol), WordPad text, Marquee text.

The result becomes the desktop wallpaper. The strips and panels stay on top. The visitor can use them during the
draw and after it.

Every draw is different. The recipe sets the style. A seed sets the random factors: positions, sizes, color
jitter, how many stamps, which glyphs. A saved seed gives the same image again.

**Default: OFF.** With the setting off, nothing in this file runs and the machine costs nothing extra.

---

## 2. Where the setting lives

The setting is a page of the editor tab system (design/preset-engine-2). This design needs these things from that
system:

| Need | Why |
|---|---|
| A page id, `look`, with the controls in section 2.1 | The visitor turns the artwork on and picks the options. |
| A host -> guest line when the page opens and closes | The guest stops the backdrop work when nobody can see it (section 6). |
| A place in the plugin state for the key `art` | The recipe and the last seed travel with the DAW project. |

If the tab system puts all look options on the Visualizers tab instead, put this page there as a group box called
"Artwork". The controls do not change.

### 2.1 Controls (real XP controls)

```
 ┌ Artwork ────────────────────────────────────────────────────────────────────────┐
 │ [ ] Paint a new background when the preset changes          (check box, OFF)   │
 │ Recipe:  (•) From the preset   ( ) From the pack   ( ) Mine: [__________] [..] │
 │ Draw:    (•) New every time    ( ) Same every time (seed [ 48213 ] [Dice])     │
 │ Speed:   Slow ├────────▼──────┤ Fast        (trackbar, 1 to 6 seconds)         │
 │ Show:    [x] the drawing (Paint visible)   [ ] only the result                 │
 │ Also:    [ ] window colors   [ ] desktop pattern   [ ] Marquee text            │
 │ [ Draw now ]  [ Keep this one ]  [ Back to plain ]                              │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

- "Keep this one" writes the current seed into the state, so the project reopens with this image.
- "Back to plain" puts back the machine's own wallpaper and colors.
- "only the result" draws with Paint hidden (fastest; the visitor sees the wallpaper change once).

---

## 3. The art recipe (v3 proposal)

A recipe is one line of printable ASCII, at most 512 bytes. It looks like a DNA on purpose, but it is a separate
string. The plugin state stores it under the key `art`. The library disc can give each preset a recipe (a 4th column
in `PRESETS.TSV`) and each pack a default recipe (a new file, `\PACKS.TSV`: pack name, recipe).

```
ART     := 'a1' ( ';' ITEM )*
ITEM    := KEY '=' VALUE
```

| Key | Meaning | Example |
|---|---|---|
| `s` | seed (0 to 2^31-1). Missing: a new seed for each draw. | `s=48213` |
| `pal` | palette: up to 8 RGB hex colors. The random factors pick from it. | `pal=ff71ce.01cdfe.05ffa1.b967ff.fffb96` |
| `bg` | base: `fill(c)`, `bands(c1,c2,n)` (n horizontal bands, a stepped gradient), `wall(NAME)` (a machine wallpaper: Bliss, Azul, Autumn, ...), `pattern(NAME)` | `bg=bands(ff71ce,01cdfe,12)` |
| `p` | Paint program: steps, run left to right (section 3.1) | `p=sun(c,40%).grid(persp,16).air(30,b967ff)` |
| `txt` | a text, drawn with Paint's Text tool. `{preset}`, `{pack}` and `{song}` are replaced. | `txt={preset}` |
| `font` | font for `txt`: an installed XP font | `font=Arial Black,48,b` |
| `glyph` | Character Map glyphs to stamp: font + characters | `glyph=Webdings:~.` |
| `scheme` | a window color scheme (section 5) | `scheme=Lilac` |
| `place` | how the result becomes the backdrop: `stretch`, `center`, `tile` | `place=tile` |
| `size` | the canvas size in pixels; small canvases plus `tile` are fast | `size=256x256` |
| `mq` | Marquee text for the Visualizers tab (VISUALIZERS.md) | `mq={preset}` |

Unknown keys are ignored. A missing key takes the pack's value, then the default. The plugin canonicalizes the
recipe the same way it does the DNA: the keys in table order, no repeats.

### 3.1 Paint steps

Each step is a "motif". A motif expands into Paint operations with the seed. The motif list is fixed and versioned
with the guest program. The operations are Paint's own tools.

| Motif | What Paint does |
|---|---|
| `air(n,c)` | Airbrush, n bursts in color c at random places. |
| `brush(n,c,w)` | Brush strokes along random curves. |
| `stamp(r)` | Select a random rectangle r % of the canvas and drag it with Shift held along a random curve. This is the "custom brush". |
| `copies(n)` | Select a part and drag it with Ctrl held n times. |
| `grid(flat\|persp,n)` | Lines tool: an n x n grid. `persp`: then Image > Stretch/Skew (skew) to make a floor. |
| `sun(c,y)` | Ellipse filled in c, then horizontal lines in the background color cut it into bands. |
| `bubbles(n)` | Ellipses with a white arc on the top left (the glossy highlight). |
| `hill(c)` | The Curve tool, then Fill With Color below it. |
| `rays(n,c)` | Lines from one point. |
| `flip`, `mirror`, `invert` | Image > Flip/Rotate, Image > Invert Colors. |
| `glyphs(n)` | Character Map: copy `glyph` characters, then Paint's Text tool pastes them at random places and sizes. |
| `text` | `txt` in `font`, at a random place inside the middle third. |
| `shadow` | the last text again, 3 px down-right, in a darker palette color, under the text. |

Each motif has a fixed cost class (S, M, L) and a time share. The guest scales the motif counts so the whole draw
fits the Speed setting (default 3 s).

### 3.2 Seeds

- The seed feeds one small random generator (xorshift32) in the guest. The same seed, recipe, canvas size and guest
  program version give the same image.
- "New every time": the host picks the seed. It sends it in the `art` line, and stores it as "last seed".
- "Keep this one" copies "last seed" into the recipe as `s=`.
- Timing does not change the result. The draw can run slower under load (section 6), but the operations and their
  order do not change.

---

## 4. How Paint is driven

Three ways were considered.

| Way | How | For | Against | Verdict |
|---|---|---|---|---|
| A. Input replay | SendInput, or QMP/VNC mouse events, drag the real pointer | The most "real": every stroke is a real mouse stroke | Takes the visitor's mouse and keyboard during the draw. The UI is not usable. Focus changes. A wrong click lands in a strip. | **No.** |
| B. Messages to Paint | A hook DLL inside `mspaint.exe` (the srhook technique: a `WH_GETMESSAGE` hook, work done on Paint's own thread) picks tools with `WM_COMMAND` and the tool box, and sends `WM_LBUTTONDOWN` / `WM_MOUSEMOVE` (with `MK_LBUTTON`, `MK_SHIFT`, `MK_CONTROL`) / `WM_LBUTTONUP` to the canvas window | Paint's own code draws every pixel. The real pointer does not move. Paint does not need focus. The visitor keeps the mouse. | Paint may read the real key or button state (`GetKeyState`, `GetAsyncKeyState`) for Shift, Ctrl and the Airbrush timer. The hook then also patches those two imports inside Paint (the srhook IAT technique). Must be checked tool by tool. | **Yes, main way.** |
| C. GDI in the guest program | synth.exe draws with GDI (`Ellipse`, `FloodFill`, `PatBlt`, `StretchBlt`) into a bitmap | Fastest and simplest. Exact. | Not Paint. The look is the same primitives, but nobody sees a real program at work. | **Fallback**, and for parts Paint cannot do quickly (very many bands). Also for "only the result" when the governor is tight. |

How the result becomes the backdrop:

1. Paint's own **File > Set As Background (Tiled / Centered)** sets the wallpaper. This command is in XP Paint.
   The hook answers the Save dialog (the srhook technique for Sound Recorder's Open/Save dialogs), so no dialog
   shows.
2. For `stretch`, the guest program calls `SystemParametersInfo(SPI_SETDESKWALLPAPER)` with the BMP Paint saved,
   and sets `WallpaperStyle=2` first.
3. While Paint draws, its window is the backdrop: it sits at the bottom of the z-order (`HWND_BOTTOM`, never
   activated), without menu, title bar, tool box or color box (the same steps the recorders take in the assembly).
   Its canvas fills the screen area behind the strips. The visitor sees the painting appear in the gaps between the
   parts. When "Set As Background" is done, Paint's window hides. The wallpaper shows the same pixels, so there is no
   jump.
4. The next draw paints over the current image (Paint opens the current BMP first), unless the recipe starts with a
   `bg`. So a new preset can "overdraw" the previous artwork.

Paint runs all the time once the setting is on: one process, started at low priority, kept hidden between draws.
Starting Paint for each draw would cost about a second of guest CPU.

---

## 5. Styling other parts

| Part | How | Cost | Note |
|---|---|---|---|
| Desktop wallpaper | Section 4 | low: the desktop repaints only where it shows | the main way |
| Desktop pattern (classic) | `SystemParametersInfo(SPI_SETDESKPATTERN)` with the 8x8 pattern bytes ("Boxes", "Critters", "Diamonds", "Paisley", "Quilt", "Scottie", "Thatches", "Tulip", "Waffle", "Weave", "50% Gray") | low | Shows only where no wallpaper covers it: use with `place=center` and a small image. |
| Window colors | `SetSysColors` with a classic scheme: "Lilac", "Rose", "Plum", "Marine", "Spruce", "Eggplant", "Desert", "Pumpkin", "Rainy Day", "Wheat", "Brick", "High Contrast" | **high**: every window repaints, 16 recorders included | With the Luna visual style on, most controls ignore system colors. A full scheme needs the Windows Classic style. A style change sends `WM_THEMECHANGED` to every window. Do it only on a preset change, after `built`, at low priority. Measure before shipping. |
| XP visual style | Luna Blue, Olive Green, Silver (the machine has only these) | **very high** | Frutiger Aero packs use Luna Blue or Silver. Change only on an explicit choice, never on each preset. |
| Fonts | `SPI_SETNONCLIENTMETRICS` (menu and caption fonts) | high | The strips have no captions. Leave this out of v3. |
| Marquee text | the Marquee screen saver's registry values | none until it runs | See VISUALIZERS.md. |

---

## 6. Never disturb the sound

The artwork follows the governor in VISUALIZERS.md section 6. In short:

1. **Priority.** Paint and the drawing thread run in `IDLE_PRIORITY_CLASS`. Sound Recorder's note threads are
   `THREAD_PRIORITY_TIME_CRITICAL` and its UI threads are normal priority. So any note work takes the CPU first.
2. **Pacing.** The hook does one Paint operation per tick (a stroke segment, a fill, a select). Between ticks it
   sleeps. The tick length comes from the Speed setting and from the governor's budget level.
3. **Order of events on a preset change.** The DNA rebuild comes first: it uses Sound Recorder's menus and is the
   heaviest guest work. The draw starts only after the guest has sent `built`. If a new `dna` line comes during a
   draw, the draw stops at once and starts again after the next `built`.
4. **Budget.** The governor gives the artwork the same "visual" budget as the visualizers. When the budget is low,
   the draw slows down (more seconds, same image). When the governor says "red", the draw pauses, and Paint stays
   at its last operation. A draw that cannot finish in 15 s switches to way C ("only the result") for the rest.
5. **No draw while rendering offline.** The plugin knows when the host renders faster than real time. Then the
   guest gets no `art` line. The last image stays.
6. **No input capture.** Way B never moves the pointer and never takes focus. The visitor can click a strip or
   type a DNA in the middle of a draw.

Expected cost (to be measured with the rig in VISUALIZERS.md section 7): a Paint stroke segment is one small GDI
operation and one small screen update. At 3 s per draw and about 150 operations, that is 50 operations a second.
Fills and Stretch/Skew are the large ones. The screen update is small, because only the gaps between the parts show
the backdrop.

---

## 7. The wire (v3 proposal)

Host -> guest (DNA.md 4 style; old guests ignore unknown lines):

| Line | Meaning |
|---|---|
| `art <seed> <recipe>` | Draw this recipe with this seed, after the next `built` (or now, if no build runs). |
| `art off` | Stop drawing. Put back the machine's own wallpaper and colors. |

Guest -> host:

| Line | Meaning |
|---|---|
| `artdone <seed> <ms>` | The draw finished. ms is how long it took. |
| `artstop <seed> <reason>` | The draw stopped: `dna`, `budget`, `off`. |

The host keeps the last seed in the state. A project reload sends `art <that seed> <recipe>`, so the visitor sees
the same image again.

---

## 8. Examples

Pack names are placeholders until design/aesthetic-presets publishes its names.

### Vaporwave ("Mall Plaza" pack, placeholder)

```
a1;pal=ff71ce.01cdfe.05ffa1.b967ff.fffb96;bg=bands(ff71ce,01cdfe,12);p=sun(fffb96,35%).grid(persp,14).glyphs(6).text.shadow;
txt={preset};font=Arial Black,40,b;glyph=Webdings:~;scheme=Lilac;place=stretch
```

- A stepped pink-to-cyan sky in 12 bands.
- A yellow sun cut by horizontal lines, a perspective grid floor (Line tool, then Stretch/Skew).
- Six Webdings glyphs in palette colors, the preset name in Arial Black with a drop shadow.
- Window colors: Lilac.

### Frutiger Aero ("Aqua Office" pack, placeholder)

```
a1;pal=1e90ff.7fdbff.ffffff.39cccc.2ecc40;bg=wall(Bliss);p=bubbles(14).air(25,ffffff).hill(2ecc40).rays(9,ffffff);
place=stretch
```

- Bliss as the base, glossy bubbles, white airbrush "light", a green hill curve, faint rays from the top left.
- No window colors: Luna Blue stays.

### Mallsoft tiles ("Food Court" pack, placeholder)

```
a1;size=128x128;pal=ffd1dc.c1e1c1.fdfd96;bg=fill(ffd1dc);p=stamp(20).copies(3).glyphs(2);glyph=Wingdings:{|;place=tile
```

- A 128 x 128 tile: one stamp trail, three copies and two glyphs. Tiled over the desktop.
- The fastest kind: a small canvas.

### Windows 3.11 edition

The same recipe works with 3.11 parts:

- **Paintbrush** (`PBRUSH.EXE`) replaces Paint. Its tools are the same idea: Airbrush, Paint Roller, Brush, Curve,
  Box, Circle, Text, Scissors, and Pick > Shrink + Grow, Tilt, Flip, Inverse. The 3.11 guest drives it with
  messages from a Win16 hook (the synhook technique).
- Backgrounds: the 3.11 wallpapers (`ARCADE`, `ARGYLE`, `CARS`, `CASTLE`, `CHITZ`, `EGYPT`, `FLOCK`, `HONEY`,
  `LEAVES`, `MARBLE`, `REDBRICK`, `RIVETS`, `SQUARES`, `TARTAN`, `WINLOGO`, `ZIGZAG`) and the same desktop patterns.
- Color schemes: the 3.11 Control Panel schemes, for example "Hotdog Stand", "Fluorescent", "Ocean", "Plasma Power
  Saver", "Valentine", "The Blues", "Pastel".
- Windows 3.11 multitasks cooperatively. Paintbrush must give the CPU back after each operation. The hook does one
  operation per `WM_TIMER` and returns, so synth.exe still polls the card each time.

---

## 9. Cost and order

| Step | Work | Risk |
|---|---|---|
| 1. Probe Paint in the machine | Check way B tool by tool: posted mouse messages, Shift/Ctrl drags, Airbrush, Text, Set As Background. Measure guest CPU per tool with the rig. | Paint reads the real key state: then also patch `GetKeyState`/`GetAsyncKeyState` in Paint. |
| 2. Way C and the recipe parser | GDI motifs in synth.exe, the `art` line, seeds, wallpaper. | low |
| 3. Paint hook (way B) | `painthook.dll`, the backdrop window steps, pacing. | medium |
| 4. Governor link | Use the visualizers' governor (VISUALIZERS.md 6). | depends on that work |
| 5. Page in the tab system | the `look` page | depends on design/preset-engine-2 |
| 6. Pack recipes | one recipe per pack, with design/aesthetic-presets | low |
| 7. Window color schemes | after measuring the repaint cost | medium |
| 8. 3.11 Paintbrush | the same design on Win16 | medium |

Steps 1 to 4 are about one week of work. Step 1 decides between way B and way C for each motif.
