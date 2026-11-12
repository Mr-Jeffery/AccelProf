#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 09:30:00
#SBATCH -J x15-s2
#SBATCH -x c0,c1,c22,c23,c34,c46,c11,c12,c13,c18
#SBATCH -o /home/fzheng4/wt-x15/eval/results/x15/x15-s2-%j.log
# X15: colmap-new-1-buggy at S2 (collector-only, --chain-closure --co-async --co-r3 off): verdict step (parallel.py analyze, cap 14400 s),
# then attribution (rw_attribute with chain_closure / co_async / co_r3=off, timeout 14400 s), then rw_score.
. /home/fzheng4/wt-x15/eval/baselines/setup/x15_common.sh
cd $W || exit 1
D=$OUT/s2; mkdir -p $D/attrib
echo "host=$(hostname) job=$SLURM_JOB_ID nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) cuda=$CUDA_HOME start=$(date -Is)"
lscpu | grep -E "Model name|^Socket|^Core|^Thread"
STORE=$B/realworld-2026-10-t21c-co
ls -l $STORE/$ID | head; du -sh $STORE/$ID 2>/dev/null
T=$D/.tmpv; rm -rf $T; mkdir -p $T
echo $ID > $D/ids.txt
echo "== verdict start $(date -Is)"
tv0=$(date +%s)
CUVEIN_DOT_PREFILTER=1 BASELINE_TRACE_DIR=$STORE BASELINE_MODES=collector-only $PY eval/baselines/parallel.py analyze \
  --manifest eval/realworld/manifest_t21c.csv --id-file $D/ids.txt --tag x15 --results-dir $T --confirm --confirm-dir $T/confirm \
  --chain-closure --co-async --co-r3 off --analysis-timeout 14400 --analysis-workers 16 > $D/verdict.log 2>&1
rc=$?; tv1=$(date +%s)
echo "== verdict rc=$rc wall_s=$((tv1-tv0)) end $(date -Is)"; tail -3 $D/verdict.log
echo "verdict_rc=$rc verdict_wall_s=$((tv1-tv0))" > $D/verdict_wall.txt
g=$(ls $T/baselines-cuvein-shard*.csv 2>/dev/null | head -1)
if [ -n "$g" ]; then
  cp $g $D/baselines-cuvein-shardx15.csv
  cp $g $D/baselines-cuvein-shard$ID-all.csv
  mkdir -p $D/confirm; mv $T/confirm/* $D/confirm/ 2>/dev/null; mv $T/chain-kernels-*.jsonl $D/ 2>/dev/null
  $PY -c "
import csv
for r in csv.DictReader(open('$D/baselines-cuvein-shardx15.csv', newline='')):
    print({k: r[k] for k in ('id','mode','verdict','reports_dedup','notes') if k in r})
"
fi
export RW_MODES=collector-only
KD=$(ls -d $STORE/$ID/collector-only* 2>/dev/null | head -1); echo "kernel jsons ($KD):"; ls -l $KD/kernel_*.json 2>/dev/null
mkdir -p /tmp/x15s2; export TMPDIR=/tmp/x15s2
echo "== attribution start $(date -Is)"
ta0=$(date +%s)
timeout -s TERM 14400 $PY $SU/x15_launch.py $HD/rw_attribute_s2.py --id $ID --store $STORE --manifest $HX/eval/realworld/manifest_t21c.csv --out $D/attrib/$ID.json > $D/attrib.log 2>&1
arc=$?; ta1=$(date +%s)
echo "== attribution rc=$arc wall_s=$((ta1-ta0)) end $(date -Is)"; tail -3 $D/attrib.log
echo "attrib_rc=$arc attrib_wall_s=$((ta1-ta0))" > $D/attrib_wall.txt
if [ $arc -eq 0 ] && [ -s $D/attrib/$ID.json ]; then
  $PY $HD/rw_score.py --results $D --manifest $HX/eval/realworld/manifest_t21c.csv --pairs $HX/eval/realworld/recall_pairs.json --write > $D/score.out 2>&1; echo "score rc=$?"; tail -20 $D/score.out
fi
rm -rf /tmp/x15s2
echo "end $(date -Is)"
