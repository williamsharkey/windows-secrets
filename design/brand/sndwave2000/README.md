# SNDWAVE2000 brand kit

The owner chose boutique design 1 from round 3 of the names page, with Algorithmic Industries as the company. This kit is the single source for every SNDWAVE2000 surface: the 3.11 instrument, the website, the web edition and the sound packs. `preview.png` shows all the pieces on one sheet, and `COPY.md` has the exact strings.

## Rules

- **Pixel art stays pixel art.** Every image is drawn at its native size, hard-edged (no anti-aliasing) and snapped to a fixed palette. Scale only by whole numbers (2x, 3x), with `image-rendering: pixelated` (`palette/palette.css` has a `.pix` class). Never resample smoothly.
- **Palette.** The brand uses 4 colours: Ink `#141414`, Paper `#f6f3ea`, Stripe Red `#8a1c1c` and Rose `#d9b8b0`. Pinks and greys inside the art are dither patterns of those four. Icons and dialogs use VGA 16 (`palette/vga16.gpl`), as Windows 3.1 did.
- **Look.** Technical Book: Stripe, meaning a paper ground with a red spine stripe on the left (a wide band plus a thin rule). The Grid sun mark is dithered with Floyd-Steinberg error diffusion.
- **Type.** All type is DejaVu (free licence, `fonts/LICENSE-DejaVu.txt`):
  - wordmark: DejaVu Serif Bold, slanted (the wordmark PNGs are already drawn; don't re-typeset them)
  - company line: DejaVu Sans Bold, capitals, letter-spacing 0.3em
  - edition: DejaVu Sans Bold Oblique
  - tagline: DejaVu Serif Italic
  - UI and dialogs: DejaVu Sans

  On Windows 3.11 itself, use the system dialog font (MS Sans Serif / System) for UI text.
- **Names.** "SNDWAVE2000" is one word, all caps. The company is "Algorithmic Industries". "BASILISK 16" is retired.

## Files

| Path | Size (px) | Use |
|---|---|---|
| `logo/sndwave2000-wordmark-{192,320,384,768}.png` | width as named | The wordmark, transparent. Pick the width you need; don't scale except by whole numbers. |
| `logo/sndwave2000-lockup-horizontal.png` | 480×104 | Grid sun + company line + wordmark, for headers. |
| `logo/sndwave2000-lockup-stacked.png` | 401×229 | Stacked lockup, for title cards and posters. |
| `mark/gridsun-{16,32,48,64,256}.png` | square | The Grid sun mark in the brand palette, transparent. 16 and 32 are posterized for clarity; 48 and up are dithered. |
| `mark/gridsun-*-vga16.png` | square | The same mark snapped to VGA 16, for icons and favicons on 16-colour displays. |
| `screens/title-640.png` | 640×390 | Title/splash screen with all text and the footer band, for the 3.11 splash and the site hero. |
| `screens/title-384.png` | 384×246 | Same at the names page's native size. |
| `screens/title-*-art-only.png` | 640×360 / 384×216 | The splash bitmap without text, for re-typesetting. |
| `box/box-front.png` | 336×420 | Big-box front. |
| `box/box-spine.png` | 108×420 | Box spine. |
| `box/box-top.png` | 336×108 | Box top. |
| `box/box-3d-render.png` | 420×357 | The box at a 3/4 angle, transparent, for product shots. |
| `media/diskette-label-3.5in.png` | 264×204 | 3.5-inch diskette label (96 dpi; Disk 1 of 7). |
| `media/cd-label.png` | 480×480 | CD label, round, with a transparent centre hole. |
| `ui/about-box.png` | 360×284 | The About dialog in Windows 3.1 style (text in COPY.md). |
| `icons/*.png` + `icons/*.ico` | 32×32 | Program Manager icons: SNDWAVE2000, 16 Recorders, Voice Mixer, Read Me, Setup. The .ICO files are real Windows 3.x icons (32×32, 4-bit VGA, AND mask) that load in 3.11. |
| `icons/brand-palette/*.png` | 32×32 | The same icons in the 4-colour brand palette, for the web. |
| `palette/` | | `sndwave2000.gpl` (GIMP/Aseprite), `palette.json`, `palette.css` and `swatch.png`; `vga16.gpl` for icons. |
| `fonts/` | | DejaVu Sans and Serif TTFs with their licence. |

## Provenance

Everything here is drawn procedurally by the names page engine (`names-v2.html`): canvas scenes, SVG marks and wordmark, and the dither and palette pipeline. No outside images are used. Renders were made headlessly and snapped to the palette by `kit_post.py`, which lives in the names-page scratch build.
