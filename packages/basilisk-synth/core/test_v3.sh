#!/bin/bash
# DNA v3 (design/PRESET-ENGINE-2.md, branch design/preset-engine-2): the v3 checks (test_v3.cpp, with the 20,000
# string fuzz against this core's v2 parser) and the recipe checks (test_recipe.cpp). Builds under $HOME only.
#   core/test_v3.sh [presets.txt]      (presets.txt: design/v3/collect_presets.py's list, for the recipe round trips)
set -e
here=$(cd "$(dirname "$0")" && pwd)
out=${PE2_BUILD:-$HOME/pe2-build}; mkdir -p "$out"
g++ -std=c++17 -O1 -Wall -Wextra -DCORE_KEEPS=1 -I"$here" "$here/test_v3.cpp" "$here/dna3.cpp" "$here/engine3.cpp" "$here/scales.cpp" "$here/dna.cpp" -o "$out/v3-core"
g++ -std=c++17 -O1 -Wall -I"$here" "$here/test_recipe.cpp" "$here/dna3.cpp" "$here/engine3.cpp" "$here/scales.cpp" "$here/recipe.cpp" "$here/dna.cpp" -o "$out/recipe-core"
"$out/v3-core"; "$out/recipe-core" ${1:+"$1"}
