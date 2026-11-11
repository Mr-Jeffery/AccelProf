#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 08:00:00
#SBATCH -J m5-c1
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/c1-%j.log
# M5: the C1 collector-only store (final-2026-11-co, -long, -24h) re-analysed at S2 (--chain-closure --co-async --co-r3 off)
# with CUVEIN_CHAIN_ATOMIC_HOP=1 (after) and =0 (same-node control of the existing S2 result), one shard after the other,
# both settings on this one node. Command as eval/results/co-chain-b/README.md (c6b_step2.sbatch) minus the Xeon 4110 check.
#   KS="0 1 .." (default 0..15); SWS="1 0"
W=/home/fzheng4/wt-m5
PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces
O=$W/eval/results/closure-atomic-hop/c1
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
HOST=$(hostname); MODEL=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p')
echo "host=$HOST nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
echo "lscpu model name: $MODEL"
MAN=eval/baselines/manifest.csv
run() {   # run <sw> <store> <results dir> <tag> <selector...>
  local sw=$1 store=$2 res=$3 tag=$4; shift 4
  local d=$O/sw$sw/$res; mkdir -p $d
  local f=$d/baselines-cuvein-shard$tag.csv
  [ -s $f ] && { echo "skip sw$sw $res $tag"; return; }
  echo "== sw$sw $res $tag $(date -Is)"
  local t=$d/.tmp$tag; rm -rf $t; mkdir -p $t
  CUVEIN_CHAIN_ATOMIC_HOP=$sw BASELINE_TRACE_DIR=$B/$store BASELINE_MODES=collector-only $PY eval/baselines/parallel.py analyze --manifest $MAN "$@" \
      --tag "$tag" --results-dir $t --confirm --confirm-dir $t/confirm --chain-closure --co-async --co-r3 off \
      --analysis-timeout 14400 --analysis-workers 16 > $d/shard$tag.log 2>&1
  local rc=$?
  tail -1 $d/shard$tag.log
  local g=$(ls $t/baselines-cuvein-shard*.csv 2>/dev/null | head -1)
  if [ $rc -eq 0 ] && [ -n "$g" ] && [ -s "$g" ]; then
    $PY $S/c6b_anode.py "$g" $HOST
    printf 'host=%s\nmodel=%s\nshard=%s\njob=%s\nrev=%s\nsw=%s\n' "$HOST" "$MODEL" "$tag" "$SLURM_JOB_ID" "$(git rev-parse --short=12 HEAD)" "$sw" > $d/cpu-$tag.txt
    mkdir -p $d/confirm
    mv $t/chain-kernels-*.jsonl $d/ 2>/dev/null
    [ -d $t/confirm ] && mv $t/confirm/* $d/confirm/ 2>/dev/null
    mv "$g" $f; rm -rf $t
  else echo "FAILED rc=$rc sw$sw $res $tag"; fi
}
for k in ${KS:-$(seq 0 15)}; do
  for sw in ${SWS:-1 0}; do run $sw final-2026-11-co c1-main ${k}_16 --pset P1,P3,P4,P5,P6,P7,P9,PI --shard $k/16; done
done
for sw in ${SWS:-1 0}; do
  run $sw final-2026-11-co-long c1-long co-long --id-file $S/x7_a5_co_long.txt
  run $sw final-2026-11-co-24h c1-24h co-24h --id-file $S/x7_a5_co_24h.txt
done
echo "end $(date -Is)"
