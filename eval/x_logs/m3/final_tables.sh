#!/bin/bash
cd /home/fzheng4/wt-m2
PY=/home/fzheng4/AccelProf/.env/bin/python
for S in before after; do
  OUT=eval/results/r1-distance/mode-pairs-$S
  $PY eval/baselines/mode_pairs.py tables --out $OUT --md $OUT/MODE_PAIRS.md
done
$PY eval/baselines/r1_distance.py report
$PY eval/baselines/pairs_per_tier.py bclass --workers 8 --timeout 14400 --mem-gb 20
$PY eval/baselines/pairs_per_tier.py report
