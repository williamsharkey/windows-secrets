#!/bin/bash
# DNA v3 and recipe tests against two cores (both read-only): this branch's core/ (v2) and, if given, a checkout
# whose core has DNA.md 5.7 (unknown tokens kept). Builds under $HOME only.
#   design/v3/test_v3.sh [/path/to/main/checkout [aesthetic-presets.json]]
# With a checkout, the recipe test also round-trips every real preset (collect_presets.py).
set -e
here=$(cd "$(dirname "$0")" && pwd)
out=${PE2_BUILD:-$HOME/pe2-build}; mkdir -p "$out"
core=$here/../../core
src="$here/dna3.cpp $here/engine3.cpp $here/recipe.cpp"
presets=""
if [ -n "$1" ]; then
  python3 "$here/collect_presets.py" "$out/presets.txt" --main "$1" ${2:+--aes "$2"}
  presets="$out/presets.txt"
fi
g++ -std=c++17 -O1 -Wall -Wextra -I"$core" "$here/test_v3.cpp" $src "$core/dna.cpp" -o "$out/v3-branchcore"
g++ -std=c++17 -O1 -Wall -I"$core" "$here/test_recipe.cpp" $src "$core/dna.cpp" -o "$out/recipe-branchcore"
echo "== against this branch's core"; "$out/v3-branchcore"; "$out/recipe-branchcore" $presets
if [ -n "$1" ]; then
  mc=$1/packages/basilisk-synth/core
  g++ -std=c++17 -O1 -Wall -Wextra -DCORE_KEEPS=1 -I"$mc" "$here/test_v3.cpp" $src "$mc/dna.cpp" -o "$out/v3-maincore"
  g++ -std=c++17 -O1 -Wall -I"$mc" "$here/test_recipe.cpp" $src "$mc/dna.cpp" -o "$out/recipe-maincore"
  echo "== against $mc (DNA.md 5.7)"; "$out/v3-maincore"; "$out/recipe-maincore" $presets
fi
