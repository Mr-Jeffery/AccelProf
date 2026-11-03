#!/usr/bin/env bash
# C6 step 3: score what is attributed so far (ids with an attribution JSON only) into c6-step3/rw_interim and report it.
. /home/fzheng4/c6-step3/env.sh
RWH=/home/fzheng4/c6rw; RWR=$S3/rw; I=$S3/rw_interim
rm -rf $I; mkdir -p $I/realworld/attrib $I/realworld_t21c/attrib
for d in realworld realworld_t21c; do
  for a in $RWR/$d/attrib/*.json; do id=$(basename $a .json); cp $a $I/$d/attrib/; cp $RWR/$d/baselines-cuvein-shard$id-all.csv $I/$d/; done
done
export RW_MODES=collector-only
$PY $RWH/t21b/eval/realworld/harness/rw_score.py --results $I/realworld --manifest $W/eval/realworld/manifest_t21b.csv --pairs $RWH/t21b/eval/realworld/recall_pairs.json --write > $I/score_t21b.out 2>&1; echo "score t21b rc=$?"
$PY $RWH/t21c/eval/realworld/harness/rw_score.py --results $I/realworld_t21c --manifest $W/eval/realworld/manifest_t21c.csv --pairs $RWH/t21c/eval/realworld/recall_pairs.json --exclude lightgbm-new-1,lightgbm-new-2,llamacpp-open-2 --write > $I/score_t21c.out 2>&1; echo "score t21c rc=$?"
RWDIR=$I RWOUT=/rw_interim $PY $W/eval/baselines/setup/c6_rw_report.py
