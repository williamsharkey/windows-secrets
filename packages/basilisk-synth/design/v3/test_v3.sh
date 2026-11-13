#!/bin/bash
# DNA v3 tests against two cores (both read-only): this branch's core/ (v2) and, if given, a checkout whose core has
# DNA.md 5.7 (unknown tokens kept). Builds under $HOME only.
#   design/v3/test_v3.sh [/path/to/main/checkout]
set -e
here=$(cd "$(dirname "$0")" && pwd)
out=${PE2_BUILD:-$HOME/pe2-build}; mkdir -p "$out"
core=$here/../../core
g++ -std=c++17 -O1 -Wall -Wextra -I"$core" "$here/test_v3.cpp" "$here/dna3.cpp" "$here/engine3.cpp" "$core/dna.cpp" -o "$out/v3-branchcore"
echo "== against this branch's core"; "$out/v3-branchcore"
if [ -n "$1" ]; then
  mc=$1/packages/basilisk-synth/core
  g++ -std=c++17 -O1 -Wall -Wextra -DCORE_KEEPS=1 -I"$mc" "$here/test_v3.cpp" "$here/dna3.cpp" "$here/engine3.cpp" "$mc/dna.cpp" -o "$out/v3-maincore"
  echo "== against $mc (DNA.md 5.7)"; "$out/v3-maincore"
fi
