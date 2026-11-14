# Integrating the library packs (for the synth lanes)

The builder only writes `library/builder/out/`; it does not touch either plugin. To ship the packs:

## Files

| File | Format | For |
|---|---|---|
| `out/w311/<pack>.tsv` | `category <TAB> name <TAB> DNA`, `#` comments: the format of `basilisk-synth-311/presets/b16.tsv` and `library/presets/*.tsv` | BASILISK 16: every preset of the pack, including the v3 (W/Y) ones |
| `out/xp/<pack>.tsv` | the same, the format of `library/presets/factory.tsv` | BASILISK SYNTH: the v2 presets (the v3 ones wait for XP's v3 phase) |
| `out/packs.json` | per pack: id, name, blurb, counts per category, XP count, W3.11-badge count, v3 and library counts, files | the pack discs (packs/make_packs.py), the browsers |
| `out/library.json` | per preset: pack, category, name, canonical DNA, badge (W3.11/XP), library flag, v3 flag, ships, tags, sources, recipe (pretty lines and one line), lineage and research target, scores, G, phrase loudness and peak | site, help, browsers |
| `out/vstpreset/<plugin>/<win\|mac>/<Pack>/<Category> - <Name>.vstpreset` | VST3 preset: the DPF component state (`__dpf_state_begin__`, key, core State text, `__dpf_state_end__`) under the plugin's class id | DAW users; the class-id string is written in the platform's form (Windows COM GUID order, macOS byte order) |

- The DNA is the canonical form (recipe_cli `canonical`). It is what a plugin stores, it is at most 1024 bytes, and
  its recipe round-trips (`recipe_ok`).
- Category is the program-list prefix from pack-plan 1.4 (Bass, Sub, Lead, Pad, Keys, Organ, Stab, Chord, Pluck,
  Bell, Mallet, Strings, Brass, Vocal, Arp, FX, Texture, Drone, Perc). The pack is the disc, so a program shows as
  "Category: Name" inside its pack.
- The badge is derived from the DNA (`core::dnaEdition`), never stored. [W3.11] means it uses only chimes, chord,
  ding, tada, ringin and ringout; library sounds do not count.
- Library sounds: both discs carry the same 510 names (BASILISK 16's L: list equals XP's library.iso list as a
  set), so library presets ship to both. `library: true` marks them.
- v3: `v3: true` presets use only W and Y (available in BASILISK 16 at main 4bda617). Ship them in BASILISK 16
  1.3.0. XP gets them when its v3 phase lands; until then they are left out of `out/xp/`.

## Disc images for the Library tab (PRESET-ENGINE-2.md 16)

`make_discs.py` writes `out/discs311/` for BASILISK 16. `--edition xp` writes `out/discsxp/`, which holds only
the XP-shipping presets and their XP DNA.

| File | Contents |
|---|---|
| `<LABEL>.ISO` | ISO 9660 level 1 (8.3 names, for DOSBox Pure `imgmount -t iso`) + Joliet (long names); volume id = LABEL |
| `<LABEL>/` | the same files as a folder (for a DOSBox `mount` or a zip) |
| `DISCS.TSV` | one line per disc: id, label, iso, title, presets, presets_xp, favourites |

On each disc:
- `PACK.INF` (`[Pack]` Id, Title, Version, Author, Date, Presets, PresetsXP, Favourites, Description). `PACK.TXT` is
  the same as text, for Notepad, plus the favourites list.
- `AUTORUN.INF` (label).
- `PRESETS.TSV` (category, name, DNA, pack, editions, rating, verdict, file). Readers that take the first three
  columns see the plugins' preset table.
- `LIBRARY.TSV` (header only: the packs use the built-in sounds and drive L:).
- `<CATEGORY>\<NAME>.BSP` (one CRLF line, the DNA) and `FAVORITE\<NAME>.BSP`: the owner's keeps and presets rated
  6.5 or more, from `builder/ratings/`.

Pack ids, volume labels, titles, authors and dates follow the packs lane's personas (`library/packs/*/persona.json`).
Their retail discs (`library/packs/out/*.ISO`, with manuals and art) are the same packs.

## Steps

1. **As disc packs (pack-plan 1.1):** give `out/<edition>/<pack>.tsv` to `packs/make_packs.py` as the pack's
   `\PRESETS.TSV`. The program names are already "Category" + "Name".
2. **Or as built-in programs:**
   - XP: copy the chosen `out/xp/*.tsv` into `library/presets/`. `tools/make_presets.py` takes factory.tsv first,
     then the other files by name.
   - 3.11: `make_presets311.py` reads the same folder.
   - Rebuild presets_gen.h and the disc's PRESETS.TSV (make_library*.py).
   - 1000+ programs is a long program list. The plan's disc packs are the better fit for most of them.
3. **XP check and overrides:**
   - Every preset was rendered and checked on the 3.11 machine.
   - The XP-badge presets were also rendered on BASILISK SYNTH 1.2.1 (the release, `xpcheck.py`, 2 VMs), and
     their results are in `xp_check`.
   - 1.2.1 drops 10-30 ms of exact silence many times a minute (srhook streaming; fixed in 1.2.2). Gaps and
     level are recorded but never held against a preset.
   - A preset is left out of `out/xp/` (`xp_excluded`, ships 3.11 only) only for:
     - a silent take
     - half or more of its notes missing
     - the wrong pitch (chroma under 0.7 against the 3.11 render)
     - band levels more than 9 dB off (a missing layer)
   - Re-run `xpcheck.py` when 1.2.2 ships (`rerender_on`). Excluded presets may come back then.
   - A preset that needs a different recipe on one edition would go in
     `basilisk-synth-311/presets/overrides311.tsv` (by category and name), as before. None are needed now.
4. **.vstpreset:** these are optional extras for DAW users. Load one in BasiliskHost (`--load-state X.vstpreset`)
   on each platform before shipping, because the class-id string form is platform-specific.

## Rebuilding the library

```
cd packages/basilisk-synth/library/builder
python3 analyze_sources.py                         # data/sources.json from the machine's files
PYTHONHASHSEED=0 python3 evolve.py --parallel 8    # renders and checks (LIBBUILD=~/libbuild; pinned render311 + machine there)
python3 curate.py $LIBBUILD/state/main*.json       # data/selection.json
python3 finalize.py                                # data/library.json (+ MP3s)
python3 review.py                                  # Desktop/sndrec-library/review.html
python3 ship.py                                    # out/
```
