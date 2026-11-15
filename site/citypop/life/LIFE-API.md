# life.js: the life in the night

`site/citypop/life/life.js` is a plain script with no dependencies and no module. It defines `window.CityLife`, with `window.Life` as an alias.
It draws hundreds of small, slow things at exact device pixels: stars, glints, windows, drips, a cat, the train.
Each one is a pure function of (seed, time, hour of night), and each one says when it next changes. One scheduler
wakes only for those changes and redraws only the 16 px tiles that changed.

## Starting it

```js
const ctl = CityLife.start(containerDiv, { dpr, reduced, scene, analyser, seed, hours });
// or, with your own canvas:
const ctl = CityLife.mount(canvas, scene, { analyser, dpr, reduced, seed });
```

| option | meaning |
|---|---|
| `scene` | The scene controller (`CityScene.start(...)` / `Scene.current`). If it has `overlay(layer)`, life draws into the per-layer overlay canvases, so things are hidden behind nearer layers. It reads `scene.anchors` (art/scene2.json for the current variant), `scene.view()` and `scene.onChange(cb)`. With `null`, life fetches `art/scene.json` (the old 320x200 night) and places itself the way app.js scales that art: integer scale, cover, 62% down. |
| `dpr` | Device pixel ratio. Defaults to `devicePixelRatio`. |
| `reduced` | When true, or when `prefers-reduced-motion` is set, nothing moves. Windows, stars and lamps change only slowly, and there are no movers, drips or ripples. |
| `seed` | An integer. It is mixed into every schedule, so the same seed and the same moment give the same night. |
| `hours` | The starting hour on the 24+ clock. The default is 26 (2 a.m.). |
| `analyser` | An `AnalyserNode`. It is optional, and you can also pass it later with `setAnalyser`. |
| `container` | (start only) Life adds one absolutely positioned, full-size canvas here, for things above every layer: mist and motes. Give the container `position:fixed; inset:0; pointer-events:none`. |

## Controller

| method | |
|---|---|
| `setAnalyser(node)` | Read at 10 Hz. The bass breathes the lamps, bridge lights and moon halo slightly. Note onsets (at most one every 0.7 s) start a ripple in a puddle. When the level is near silence, nothing reacts. |
| `setTime(h)` | The hour of night, 19.5 to 29.5. The night deepens: fewer windows lit, fewer trains, the roofs and puddles drying (fewer drips and rings, thinner mist). Toward 29.5 the stars fade, early risers' lights come on and birds cross. Call it as often as you like. |
| `onTrack(n, {bpm, title})` | A ripple in the first puddle. |
| `onBeat(i, meter)` | Without an analyser, a tiny breath on the lamps. With one, it is ignored. |
| `setOccluders([{x,y,w,h}])` | Rects in CSS px, such as your windows. Things wholly under them are not drawn or redrawn. Pass `[]` when the windows are hidden. |
| `pause()` / `resume()` | Life also pauses itself while the tab is hidden. After a `pause()` from you, it waits for your `resume()`. |
| `resize()` | Re-lays-out everything. Life listens to `resize` itself, debounced, and to `scene.onChange`. |
| `stats()` | `{fps, actors, kinds, kindList, drawnPxPerSec, U, hours}` |
| `destroy()` | |

Note: on the album page `window.life` is the `#life` div (an element id), not the controller. Use your own reference.

## Anchors it reads (art/scene2.json, per variant, art px)

`windows[{x,y,w,h,lit,baked,dark,room,curtain,hue,layer}]`, `stars{points[[x,y,mag]],regions}`, `moon{x,y,r,halo}`,
`bridge{lights[[x,y]] in deck order, towers, layer}`, `water[{x,y,w,h}]`, `moonPath{x,y0,y1,w}`, `train{path,layer}`,
`boats[{path}]`, `ferry{path}`, `far[[x,y]]`, `buoys[{x,y,c:'g'|'r'}]`, `lighthouse`, `antenna`, `signal`, `fisher`,
`puddles[{x,y,w,h,src,layer}]`, `lamps[{x,y,r,kind,layer}]`, `signs[]`, `vending`, `shop`, `shrine{x,y,hang}`, `cat`, `bikes[]`,
`bench`, `crossing`, `ped`, `laundry[]`, `vents[]`, `ac[]`, `eaves[{x0,x1,y}]`, `drips[]`, `wires[{pts}]`, `furin[]`, `phone[]`,
`stairs[{pts,w0,w1}]`, `streets[{pts}]`, `regions{sky, haze[{y0,y1}], ghost[]}`.
Every anchor is optional. A missing one just means fewer things.

## What lives here (52 kinds)

**Sky:** stars twinkling at their own rates under passing veils of damp, a satellite, a rare meteor, a late aircraft's strobe, the moon halo breathing, a faint 22-degree moisture ring, thin clouds drifting, birds at dawn.

**Water:** moon-path glints, swell lines, boats with masthead lights and trembling reflections, the late ferry, a green and a red buoy, far-shore house lights, an antenna, a lighthouse's pair of flashes, a far traffic light, an anchored fishing boat's lantern bobbing.

**Bridge:** deck lights in a slow travelling wave (one sodium lamp hesitates), the tower aviation lights.

**Town:** every window on its own slow schedule (warm, TV flicker, desk lamp, swaying curtain, a silhouette crossing), neon hum and stutter, lamps breathing with moths, a vending machine with stepping selection lamps, laundry and a wind chime in one shared breeze, steam puffs, a cat that wakes, looks about and stretches, AC drips, a phone glowing on a balcony, wet roof glints.

**Street:** eave and leaf drips, beads sliding along the wires, puddle rings, a lamp and the moon shivering in the puddles, the shrine lantern swaying, the night train with lit windows and their reflection, the level-crossing lamps, a pedestrian signal, a far scooter's tail light, bicycle glints.

**Presence:** the empty corner shop's tubes (one hesitates), a warmth lifting off a just-left bench, a walker under an umbrella on the stair lane whose footprints shine and dry over three minutes, warm motes drifting in the open, the mist.

## Cost

Frames fall on a shared grid: ambient things on a 6 fps beat, fast movers (a train, a satellite) on 15 fps. Life is idle between changes.
For the measured numbers, see the commit log and the report to the coordinator.

## Testing

`life/test.html?speed=20&h=26&reduced=0&only=star,window&off=1&hud=0`: the old scene with life over it. `speed` multiplies time, and `only` limits life to the listed kinds.
