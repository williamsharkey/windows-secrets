# CITYPOP1993

(The album was first called CITYPOP DEPROGRAMMED, and this folder keeps that name. SNDWAVE1993 was SNDWAVE2000.)

An album performed on SNDWAVE1993: a theme and eleven variations for a quiet night in a harbour town, about 41
minutes. Every note is played by the Windows 3.11 Sound Recorders through `render311`
(`tools/songrender`), one engine per part. Page: williamsharkey.com/citypop/ (`site/citypop/`).

| Folder | Contents |
|---|---|
| `tracks/` | `_album.py` (harmony, voicing, comping, bass, drums, the theme and its transforms, humaniser) and one script per track that writes its `.mid` and `.song` |
| `sounds/` | `build_sounds.py` and `dsp.py` (offline sample preparation), `rainy_loft.json` (the CC0 sources with proof) |
| `pack/` | `presets.tsv` (the Rainy Loft Collection, pack id `rainy-loft`) and `make_disc.py` (the disc, standalone) |
| `art/` | `make_art.py`: the cover and the page's night scene, drawn from code |
| `tools/` | `check_presets.py`, `analyze.py` (stems: clipping, balance, silent bars, pitch match against the MIDI), `master.py`, `build_site.py` |

## Rebuilding

```
python3 -I ../../tools/fetch.py freesound citypop <id>            # sources (see sounds/rainy_loft.json)
python3 sounds/build_sounds.py ~/cpd/sounds                       # needs the private Bele Dance render harness for the EP and bass
python3 pack/make_disc.py ~/cpd/sounds ~/cpd/disc/RAINYLOFT --install ~/cpd/machine/packs
for f in tracks/[0-9]*.py; do python3 $f; done
# render311 with --lookahead 150 (073d464), e.g. a wrapper as SONGRENDER_RENDER311
SONGRENDER_MACHINE=~/cpd/machine songrender.py tracks/*.song --stems --keep-wav --out-dir ~/cpd/out
python3 tools/analyze.py ~/cpd/out <slug> --song tracks/<slug>.song
python3 tools/build_site.py ~/cpd/out site/citypop --master
python3 art/make_art.py site/citypop/art
```

The compositions and arrangements are CC0. The audio files are not in git; they are on the web host.
