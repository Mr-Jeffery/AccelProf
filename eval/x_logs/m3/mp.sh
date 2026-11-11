#!/bin/bash
# usage: mp.sh before|after   (before: CUVEIN_R1_OBSERVED_ONLY=1)
cd /home/fzheng4/wt-m2
PY=/home/fzheng4/AccelProf/.env/bin/python
S=$1
[ "$S" = before ] && export CUVEIN_R1_OBSERVED_ONLY=1
OUT=eval/results/r1-distance/mode-pairs-$S
mkdir -p $OUT
seq 0 15 | xargs -P16 -I{} $PY eval/baselines/mode_pairs.py collect --out $OUT --shard {}/16 --mem-gb 6 --timeout 3600
$PY eval/baselines/mode_pairs.py tables --out $OUT --md $OUT/MODE_PAIRS.md
