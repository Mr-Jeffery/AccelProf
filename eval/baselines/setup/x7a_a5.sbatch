#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 24:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -o /home/fzheng4/wt-x7a/eval/x_logs/x7a-a5-%x-%j.log
# X7 A5 parity: re-analyse every stored program of the three final stores with the X7 code at
# --analysis-workers 16, X1b's / C1's shard layout, one node, sequential. GROUP selects:
#   main    final-2026-11 (both modes), P1,P3,P4,P5,P6,P7,P9, shards k/48     -> final-b
#   pi      final-2026-11, PI, shards k/64                                    -> final-b-pi
#   long    final-2026-11-long (vc), -long-sc (sc), -24h-vc, -24h-sc          -> final-b-long, -long-sc, -24h-vc, -24h-sc
#   co      final-2026-11-co, P1..P9 shards k/48 -> collector-only; PI k/64 -> collector-only-pi
#   colong  final-2026-11-co-long, final-2026-11-co-24h
# A finished shard (its final csv exists; a running shard writes to .tmp) is skipped, so a killed job is resubmitted as is.
W=/home/fzheng4/wt-x7a
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
O=$W/eval/results/verdict-timing
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) nproc=$(nproc) group=$GROUP rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
# run <store tag> <modes> <results dir> <tag> <selector...>
run() {
  local store=$1 modes=$2 res=$3 tag=$4; shift 4
  local d=$O/$res; mkdir -p $d
  local f=$d/baselines-cuvein-shard$tag.csv
  [ -s $f ] && { echo "skip $res $tag"; return; }
  echo "== $res $tag $(date -Is)"
  local t=$d/.tmp$tag; rm -rf $t; mkdir -p $t
  BASELINE_TRACE_DIR=$B/$store BASELINE_MODES=$modes $PY eval/baselines/parallel.py analyze       --manifest eval/baselines/manifest.csv "$@" --tag "$tag" --results-dir $t       --analysis-timeout 14400 --analysis-workers 16 > $d/shard$tag.log 2>&1
  local rc=$?
  tail -1 $d/shard$tag.log
  local g=$(ls $t/baselines-cuvein-shard*.csv 2>/dev/null | head -1)
  if [ $rc -eq 0 ] && [ -n "$g" ] && [ -s "$g" ]; then mv "$g" $f; rm -rf $t
  else echo "FAILED rc=$rc $res $tag"; fi
}
shards() { # store modes res tag-prefix N selector...
  local store=$1 modes=$2 res=$3 pre=$4 n=$5; shift 5
  for k in $(seq 0 $((n-1))); do run $store $modes $res $pre$k\_$n "$@" --shard $k/$n; done
}
BOTH=vector-clock,scalar-clock
case $GROUP in
  main)   shards final-2026-11 $BOTH final-b "" 48 --pset P1,P3,P4,P5,P6,P7,P9 ;;
  pi)     shards final-2026-11 $BOTH final-b "pi" 64 --pset PI ;;
  long)   run final-2026-11-long vector-clock final-b-long long-vc --id-file $S/x7_a5_long_vc.txt
          run final-2026-11-long-sc scalar-clock final-b-long-sc long-sc --id-file $S/x7_a5_long_sc.txt
          run final-2026-11-24h-vc vector-clock final-b-24h-vc 24h-vc --id-file $S/x7_a5_24h_vc.txt
          run final-2026-11-24h-sc scalar-clock final-b-24h-sc 24h-sc --id-file $S/x7_a5_24h_sc.txt ;;
  co)     shards final-2026-11-co collector-only collector-only "" 48 --pset P1,P3,P4,P5,P6,P7,P9
          shards final-2026-11-co collector-only collector-only "pi" 64 --pset PI ;;
  colong) run final-2026-11-co-long collector-only collector-only-long co-long --id-file $S/x7_a5_co_long.txt
          run final-2026-11-co-24h collector-only collector-only-24h co-24h --id-file $S/x7_a5_co_24h.txt ;;
esac
echo "end $(date -Is)"
