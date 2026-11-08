#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 24:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -o /home/fzheng4/wt-c6/eval/x_logs/c6-step2-%x-%j.log
# C6 step 2: re-analyse every collector-only recording of C1 and C2 with the chain closure on
# (parallel.py analyze --chain-closure, --analysis-workers 16, --analysis-timeout 14400), CPU only,
# one node per job, shards one after the other (analysis_s uncontended). As x7a_a5.sbatch.
#   GROUP=c1main [KS="0 1 .."]  final-2026-11-co, all psets, shards k/16        -> co-chain/c1-main
#   GROUP=c1long                final-2026-11-co-long, final-2026-11-co-24h (id files) -> c1-long, c1-24h
#   GROUP=c2recall [KS=..]      realworld-2026-10-co (C2 recall set, manifest_t21b), shards k/16 -> c2-recall
#   GROUP=c2cand [KS=..]        realworld-2026-10-t21c-co (C2 candidate set, 16 ids of co_main.list), k/16 -> c2-cand
# A finished shard (its final csv exists; a running shard writes to .tmp) is skipped, so a killed job is resubmitted as is.
# After each shard: ;anode=<this host> is appended to every row's notes (c6_anode.py), chain-kernels jsonl and the
# confirm records are moved next to the csv, and the csv is moved last.
W=/home/fzheng4/wt-c6
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
O=$W/eval/results/co-chain
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
HOST=$(hostname)
echo "host=$HOST nproc=$(nproc) group=$GROUP ks=${KS:-} rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
lscpu | grep -E "^(Model name|Socket|Core|Thread|CPU MHz|CPU max MHz)"
MAN=eval/baselines/manifest.csv
# run <store> <results dir> <tag> <selector...>
run() {
  local store=$1 res=$2 tag=$3; shift 3
  local d=$O/$res; mkdir -p $d
  local f=$d/baselines-cuvein-shard$tag.csv
  [ -s $f ] && { echo "skip $res $tag"; return; }
  echo "== $res $tag $(date -Is)"
  local t=$d/.tmp$tag; rm -rf $t; mkdir -p $t
  BASELINE_TRACE_DIR=$B/$store BASELINE_MODES=collector-only $PY eval/baselines/parallel.py analyze --manifest $MAN "$@" \
      --tag "$tag" --results-dir $t --confirm --confirm-dir $t/confirm --chain-closure \
      --analysis-timeout 14400 --analysis-workers 16 > $d/shard$tag.log 2>&1
  local rc=$?
  tail -1 $d/shard$tag.log
  local g=$(ls $t/baselines-cuvein-shard*.csv 2>/dev/null | head -1)
  if [ $rc -eq 0 ] && [ -n "$g" ] && [ -s "$g" ]; then
    $PY $S/c6_anode.py "$g" $HOST
    mkdir -p $d/confirm
    mv $t/chain-kernels-*.jsonl $d/ 2>/dev/null
    [ -d $t/confirm ] && mv $t/confirm/* $d/confirm/ 2>/dev/null
    mv "$g" $f; rm -rf $t
  else echo "FAILED rc=$rc $res $tag"; fi
}
shards() { # store res N selector...   (KS = the shard indices of this job)
  local store=$1 res=$2 n=$3; shift 3
  for k in ${KS:-$(seq 0 $((n-1)))}; do run $store $res $k\_$n "$@" --shard $k/$n; done
}
case $GROUP in
  c1main)   shards final-2026-11-co c1-main 16 --pset P1,P3,P4,P5,P6,P7,P9,PI ;;
  c1long)   run final-2026-11-co-long c1-long co-long --id-file $S/x7_a5_co_long.txt
            run final-2026-11-co-24h c1-24h co-24h --id-file $S/x7_a5_co_24h.txt ;;
  c2recall) export CUVEIN_DOT_PREFILTER=1; MAN=eval/realworld/manifest_t21b.csv
            shards realworld-2026-10-co c2-recall 16 --pset RW ;;
  c2cand)   export CUVEIN_DOT_PREFILTER=1; MAN=eval/realworld/manifest_t21c.csv
            shards realworld-2026-10-t21c-co c2-cand 16 --id-file $S/c6_c2_cand_ids.txt ;;
esac
echo "end $(date -Is)"
