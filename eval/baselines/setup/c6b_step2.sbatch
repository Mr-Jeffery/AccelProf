#!/bin/bash
#SBATCH -p skylake
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 24:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46,c11,c12,c13,c18
#SBATCH -o /home/fzheng4/wt-c6b/eval/x_logs/c6b-step2-%x-%j.log
# C6b step 2: re-analyse every collector-only recording of C1 with --chain-closure --co-async and --co-r3 strict (S1) / off (S2),
# CPU only, one Xeon Silver 4110 node per job (checked from lscpu, job aborts otherwise), shards one after the other.
#   SET=s1|s2   GROUP=main [KS="0 1 .."] | long      (main: final-2026-11-co shards k/16; long: -long and -24h id files)
W=/home/fzheng4/wt-c6b
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
O=$W/eval/results/co-chain-b/$SET
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
HOST=$(hostname)
MODEL=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p')
echo "host=$HOST nproc=$(nproc) set=$SET group=$GROUP ks=${KS:-} rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
echo "lscpu model name: $MODEL"
lscpu | grep -E "^(Socket|Core|Thread|CPU MHz|CPU max MHz)"
case "$MODEL" in *"Xeon"*"Silver 4110"*) ;; *) echo "NOT A XEON SILVER 4110 NODE ($HOST: $MODEL); aborting, nothing run"; exit 3;; esac
case $SET in s1) R3=strict;; s2) R3=off;; *) echo bad SET; exit 4;; esac
MAN=eval/baselines/manifest.csv
run() {   # run <store> <results dir> <tag> <selector...>
  local store=$1 res=$2 tag=$3; shift 3
  local d=$O/$res; mkdir -p $d
  local f=$d/baselines-cuvein-shard$tag.csv
  [ -s $f ] && { echo "skip $res $tag"; return; }
  echo "== $SET $res $tag $(date -Is)"
  local t=$d/.tmp$tag; rm -rf $t; mkdir -p $t
  BASELINE_TRACE_DIR=$B/$store BASELINE_MODES=collector-only $PY eval/baselines/parallel.py analyze --manifest $MAN "$@" \
      --tag "$tag" --results-dir $t --confirm --confirm-dir $t/confirm --chain-closure --co-async --co-r3 $R3 \
      --analysis-timeout 14400 --analysis-workers 16 > $d/shard$tag.log 2>&1
  local rc=$?
  tail -1 $d/shard$tag.log
  local g=$(ls $t/baselines-cuvein-shard*.csv 2>/dev/null | head -1)
  if [ $rc -eq 0 ] && [ -n "$g" ] && [ -s "$g" ]; then
    $PY $S/c6b_anode.py "$g" $HOST
    printf 'host=%s\nmodel=%s\nshard=%s\njob=%s\nrev=%s\n' "$HOST" "$MODEL" "$tag" "$SLURM_JOB_ID" "$(git rev-parse --short=12 HEAD)" > $d/cpu-$tag.txt
    mkdir -p $d/confirm
    mv $t/chain-kernels-*.jsonl $d/ 2>/dev/null
    [ -d $t/confirm ] && mv $t/confirm/* $d/confirm/ 2>/dev/null
    mv "$g" $f; rm -rf $t
  else echo "FAILED rc=$rc $res $tag"; fi
}
case $GROUP in
  main) for k in ${KS:-$(seq 0 15)}; do run final-2026-11-co c1-main $k\_16 --pset P1,P3,P4,P5,P6,P7,P9,PI --shard $k/16; done ;;
  long) run final-2026-11-co-long c1-long co-long --id-file $S/x7_a5_co_long.txt
        run final-2026-11-co-24h c1-24h co-24h --id-file $S/x7_a5_co_24h.txt ;;
esac
echo "end $(date -Is)"
