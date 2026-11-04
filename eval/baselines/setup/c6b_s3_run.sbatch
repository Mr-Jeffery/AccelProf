#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 12:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46,c11,c12,c13,c18
#SBATCH -o /home/fzheng4/wt-c6b/eval/x_logs/c6b-s3-run-%x-%j.log
# C6b step 3: collector-only verdict layer (hb-stripped scalar-clock recordings, guarded loader) at one setting.
#   SET=s1 (--co-r3 strict) | s2 (--co-r3 off) | cfg (--co-r3 cfg), all with --chain-closure --co-async;  KS="0 1 .." (default 0..15)
W=/home/fzheng4/wt-c6b
PY=/home/fzheng4/AccelProf/.env/bin/python
S=$W/eval/baselines/setup
O=$W/eval/results/co-chain-b/step3/run-$SET
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/c6b-step3/store BASELINE_MODES=collector-only
case $SET in s1) R3=strict;; s2) R3=off;; cfg) R3=cfg;; *) echo bad SET; exit 4;; esac
HOST=$(hostname)
echo "host=$HOST nproc=$(nproc) model=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p') set=$SET r3=$R3 rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
mkdir -p $O/probes $O/confirm
for k in ${KS:-$(seq 0 15)}; do
  f=$O/baselines-cuvein-shard${k}_16.csv
  [ -s $f ] && { echo "skip $k"; continue; }
  echo "== $SET shard $k $(date -Is)"
  t=$O/.tmp$k; rm -rf $t; mkdir -p $t
  S3_PROBES=$O/probes $PY $S/c6b_s3_harness.py analyze --manifest eval/baselines/manifest.csv --pset P1,P3,P4,P5,P6,P7,P9,PI --shard $k/16 \
      --tag "$k" --results-dir $t --confirm --confirm-dir $t/confirm --chain-closure --co-async --co-r3 $R3 \
      --analysis-timeout 14400 --analysis-workers 16 > $O/shard$k.log 2>&1
  rc=$?
  tail -1 $O/shard$k.log
  g=$(ls $t/baselines-cuvein-shard*.csv 2>/dev/null | head -1)
  if [ $rc -eq 0 ] && [ -n "$g" ] && [ -s "$g" ]; then
    $PY $S/c6b_anode.py "$g" $HOST
    mv $t/chain-kernels-*.jsonl $O/ 2>/dev/null
    [ -d $t/confirm ] && mv $t/confirm/* $O/confirm/ 2>/dev/null
    mv "$g" $f; rm -rf $t
  else echo "FAILED rc=$rc $SET $k"; fi
done
echo "end $(date -Is)"
