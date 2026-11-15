# CITYPOP night scene: API

Onomichi after the rain, around 2 a.m. The scene has five layers drawn at device-pixel resolution. One art pixel is one device pixel, or a whole multiple of one. Everything is generated deterministically by `gen/scene.py`, using seed 20261114.

## Files
- `scene/scene.js`: the runtime. It is a plain script with no module and no dependencies.
- `scene/img/{variant}-{layer}.png`: indexed PNGs (≤64 colours) with 1-bit alpha.
  - Variants: `desktop` 2560×1440, `hd` 1920×1080, `portrait` 1170×2532.
  - Layers, back to front: `sky far mid near fg`.
- `art/scene2.json`: per variant, the layer list, each layer's palette and four mood palettes, the camera, and the **anchors**.
- `scene/gen/`: the generator, in Python 3 with numpy, Pillow and scipy. To rebuild: `cd scene/gen && nice -n 10 python3 scene.py all`, about 4 minutes.

## Mounting (UI lane)
```html
<div id="scene" style="position:fixed;inset:0;z-index:0"></div>
<script src="scene/scene.js"></script>
<script>
  const c = CityScene.start(document.getElementById('scene'), { dpr: devicePixelRatio, reduced, time: 24.5 });
  c.ready.then(() => fadeOutOldCanvas());
</script>
```
- `CityScene.start(container, opts)` returns a controller synchronously. `window.Scene` is the same object, and `CityScene.current` is the last controller.
  - `opts`: `{dpr, reduced, time, variant, base, json}`. `base` is prefixed to every URL, and `json` defaults to `art/scene2.json`.
- `c.ready` is a Promise that resolves once all five layers have painted. The sky and far layers paint first.
- **Variant choice:** if the viewport aspect is below 0.8, the portrait variant is used. Otherwise the scene uses the landscape variant whose whole-number scale covers the screen with the least crop. For example, 1080p at 1× uses hd, 1440p at 1× uses desktop, and 4K and 2880×1800 use hd at 2×. A fractional nearest-neighbour scale is used only when a whole-number scale would crop more than about 30%.
- **Crop:** cover-fit, cropped around `focus` (per variant, in scene2.json). The moon, the stair lane and the pagoda are right of centre, and the left ~830 css px may sit under the windows.
- **Time:**
  - `c.setTime(hours)` uses a 24+ clock: 19.5 is rain just ended, 24.5 is deep night, 27.8 is pre-dawn blue and 29.5 is dawn. Values in between interpolate.
  - Palette steps are recoloured one layer per frame, and only when the palette has visibly changed (240 steps per mood segment). Calling `setTime` often costs nothing.
  - `c.setMood(t)` takes t from 0 to 1 across the same night. `c.mood()` returns the current t, and `c.time()` returns the hours.
- `c.pause()`, `c.resume()` and `c.resize()` are available. The scene also listens to resize and devicePixelRatio changes itself. `c.destroy()` removes everything.
- **CPU:** the scene runs no per-frame loop. Each layer is drawn once into an oversized canvas (a margin of `ceil(10*scale)+2` device px on every side, `will-change: transform`). Parallax slides the canvases with a CSS translate snapped to whole device pixels, so a pointer move costs no redraw. Layers redraw only on mood steps and resize. Parallax eases at about 15 fps, then idles, and is off when `reduced` is set.

## Stacking (life lane)
- The container holds one `<canvas class="scene-layer scene-{name}">` per layer.
  - z-index is `sky 0, far 10, mid 20, near 30, fg 40`.
  - Each canvas is position:absolute, with its backing store at `cssW*dpr × cssH*dpr`.
- `c.overlay(name)` returns the same canvas on every call. It sits at `z = layer*10 + 5`, directly above that layer, and is already sized. Draw sprites that the nearer layers must hide into the overlay of the sprite's anchor layer.
- `c.view()` returns `{variant, w, h, scale, dpr, ox, oy, dw, dh, parallax:{sky:[dx,dy],…}}`, where parallax is in art px.
  - The device position of art point (x,y) on a layer is `round((x+dx)*scale+ox), round((y+dy)*scale+oy)`.
  - `c.toScreen(x,y,layer)` does this for you.
- `c.onChange(cb)` fires after every transform change (parallax step, resize, variant switch), with the overlays already resized. Do a full redraw then.
- `c.onMood(cb(t, colors))` and `c.moodColors(t)` give `{sky, glow, warm, water, haze, moon}` as css rgb strings.
- `c.anchors` holds the current variant's anchors.

## Anchors (`variants[v].anchors`, art px, every item has `layer`)
- `windows`: arrays laid out by `windowsFields` = `x y w h lit baked hue curtain room layer dark`.
  - `baked:1` means the window is lit in the art. The life lane may add flicker or dim it by painting `dark` (rgb) over it.
  - `baked:0` means the window is dark glass. If `lit:1`, the life lane should light it at start.
- `lamps[]`: `{x,y,r,kind:street|porch|lantern|vending,bulb:[x,y,w,h],cool?}`. Glows are baked; bulbs are yours to breathe.
- `puddles[]`: `{x,y,w,h,src:[[x,y]]}`.
- `water[0]`: `{x,y,w,h,moonPath:{x,y0,y1,w0,w1}}`.
- `stars`: `{regions, points:[[x,y,mag,hue]]}`. Points are not baked (yours); the faint field is baked.
- `moon`: `{x,y,r,halo}`. The disc and halo are baked.
- `bridge`: `{lights (deck order, fixtures baked dim), towers:[{x,y,kind}] (warning lights), cables, deck}`.
- `train`: `{path,y,car,h}` on far. Not baked.
- `ferry`: `{dock,path}`. Only the docked ferry is baked.
- `boats[]` are baked (anchored and squid boats).
- `far`: `[[x,y]]`, island lights.
- `crossing`: `{lamps}`, the rail crossing lamps, unlit in the art.
- `ped`: `{red,green}`, the pedestrian light.
- Points of interest:
  - `cat {x,y,w,h,head,tail}`
  - `vending {panel}`
  - `shrine {lantern (not baked), hang}`
  - `mailbox`, `bench`, `shop`
  - `signs[] {neon}`
  - `bikes[]`, `plants[]`, `trees[]`, `poles[] {arms}`
- Places for drips and drifting motes:
  - `drips[]`: leaf tips in fg
  - `ac[]`: AC drip points
  - `eaves[] {x0,x1,y}`
  - `wires[] {pts}`
  - `laundry[]`
  - `vents[] {kind: fan|windbell}`
  - `regions {sky, haze:[[y0,y1]], motes:[[x,y,w,h]]}`
- Paths for movers: `stairs[] {pts,w}`, `paths[] {pts,kind:lane|road}`.
