#!/usr/bin/env bash
# Clone the corpora not vendored in the tree, into eval/baselines/corpora/
# (gitignored). Network only -- run on the login node. Records a status line per
# repo. Present-in-tree corpora (ScoR = P4/P5, cuHadron = P6) are NOT cloned here.
#
#   bash eval/baselines/fetch_corpora.sh
set -u
cd "$(dirname "$0")" || exit 1
mkdir -p corpora && cd corpora || exit 1

# P1 Indigo3  (100-program sample; also carries the ECL racefree egr-input codes
#              CC/GC/MIS/MST used for P3).  SLOWER_ATOMIC is a compile define here.
# P2 Indigo   (ISPASS'22 original suite; the task's github.com/burtscher/Indigo
#              404s -- IndigoSuite is the actual repo).
# P7 HeCBench (overhead-only subset).
declare -A REPOS=(
  [Indigo3Suite]="https://github.com/burtscher/Indigo3Suite.git"
  [IndigoSuite]="https://github.com/burtscher/IndigoSuite.git"
  [HeCBench]="https://github.com/zjin-lcf/HeCBench.git"
)
for name in "${!REPOS[@]}"; do
  url="${REPOS[$name]}"
  if [ -d "$name/.git" ]; then
    echo "HAVE $name"; continue
  fi
  echo "CLONE $name <- $url"
  if git clone --depth 1 "$url" "$name" 2>"clone_${name}.err"; then
    echo "  OK $name ($(find "$name" -name '*.cu' | wc -l) .cu files)"
  else
    echo "  FAIL $name -- see corpora/clone_${name}.err"
  fi
done
# ECL-suite is the Indigo3Suite racefree/egr-input subtree; build_corpora --pset P3
# points at it. Symlink for build_ecl.py's expected --ecl root.
[ -d Indigo3Suite ] && ln -sfn Indigo3Suite ECL-suite
echo "fetch: done"
