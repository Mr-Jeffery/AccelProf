#!/bin/bash
# usage: mp_long.sh before|after : the 13 recordings that hit the 3600 s / 6 GB cap, with a 10 h / 10 GB cap, 7 shards
cd /home/fzheng4/wt-m2
PY=/home/fzheng4/AccelProf/.env/bin/python
S=$1
[ "$S" = before ] && export CUVEIN_R1_OBSERVED_ONLY=1
OUT=eval/results/r1-distance/mode-pairs-$S
seq 0 7 | xargs -P8 -I{} $PY eval/baselines/mode_pairs.py collect --out $OUT --shard {}/8 --id-file eval/x_logs/m3/long_ids_$S.txt --force --mem-gb 10 --timeout 36000
