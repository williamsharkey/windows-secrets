#!/bin/bash
# DNA v3 tests against two cores (both read-only): this branch's core/ (v2) and, if given, a checkout whose core
# has DNA.md 5.7 (unknown tokens kept). The recipe test runs against the checkout's core only (it needs DNA.md 2.4's
# displayName/dnaName, on main from 18f77d5). Builds under $HOME only.
#   design/v3/test_v3.sh [/path/to/main/checkout [aesthetic-presets.json]]
# With a checkout, the recipe test also round-trips every real preset (collect_presets.py).
set -e
here=$(cd "$(dirname "$0")" && pwd)
out=${PE2_BUILD:-$HOME/pe2-build}; mkdir -p "$out"
core=$here/../../core
src="$here/dna3.cpp $here/engine3.cpp $here/scales.cpp"
rsrc="$src $here/recipe.cpp"
presets=""
if [ -n "$1" ]; then
  python3 "$here/collect_presets.py" "$out/presets.txt" --main "$1" ${2:+--aes "$2"}
  presets="$out/presets.txt"
fi
g++ -std=c++17 -O1 -Wall -Wextra -I"$core" "$here/test_v3.cpp" $src "$core/dna.cpp" -o "$out/v3-branchcore"
# recipe.cpp uses core's displayName/dnaName (DNA.md 2.4, main 18f77d5): the recipe test needs main's core
echo "== against this branch's core"; "$out/v3-branchcore"
if [ -n "$1" ]; then
  mc=$1/packages/basilisk-synth/core
  g++ -std=c++17 -O1 -Wall -Wextra -DCORE_KEEPS=1 -I"$mc" "$here/test_v3.cpp" $src "$mc/dna.cpp" -o "$out/v3-maincore"
  g++ -std=c++17 -O1 -Wall -I"$mc" "$here/test_recipe.cpp" $rsrc "$mc/dna.cpp" -o "$out/recipe-maincore"
  echo "== against $mc (DNA.md 5.7)"; "$out/v3-maincore"; "$out/recipe-maincore" $presets
fi
