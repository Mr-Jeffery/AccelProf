#!/bin/bash
# C7: extract the inputs of tier_funnel.py with git show (nothing is merged or checked out).
# usage: tier_funnel_inputs.sh [DIR]   (default ~/c7-data; run inside a cuVein clone that has fetched origin; cuRacePaper at ~/cuRacePaper)
set -eu
D=${1:-$HOME/c7-data}; mkdir -p "$D"
B=origin/eval/cap-84600; R=eval/results/cap-84600
for f in baselines-cuvein baselines-cuvein-co baselines-iguard baselines-sanitizer; do git show $B:$R/$f.csv > "$D/cap-$f.csv"; done
git show $B:eval/results/baselines-racecheck.csv > "$D/cap-baselines-racecheck.csv"
git show $B:eval/results/baselines-hirace.csv > "$D/cap-baselines-hirace.csv"     # native walls only (slowdown denominators)
git show $B:$R/newkeys.json > "$D/cap-newkeys.json"
git show $B:$R/tables/new/cells.json > "$D/cap-cells.json"
git show $B:$R/tables/old/cells.json > "$D/cap-old-cells.json"
git show $B:eval/CAP_84600.md > "$D/CAP_84600.md"
git show origin/eval/co-chain:eval/results/co-chain/merged/baselines-cuvein.csv > "$D/c6-baselines-cuvein.csv"
git show 98371ee:eval/baselines/manifest.csv > "$D/manifest.csv"
(cd "${PAPER:-$HOME/cuRacePaper}" && git show origin/main:figures/fig_slowdown.tex) > "$D/fig_slowdown.tex"
ls -l "$D"
