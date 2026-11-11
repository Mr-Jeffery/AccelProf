#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 14:00:00
#SBATCH -J m5-s3
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/s3-%j.log
# M5 line 4: C6b step 3 repeated at S2 (--chain-closure --co-async --co-r3 off) with CUVEIN_CHAIN_ATOMIC_HOP=1 (sw1) and =0 (sw0, control: must
# reproduce 3,702 pairs / 349 programs): the collector-only verdict layer on the hb-stripped scalar-clock recordings
# (/mnt/beegfs/fzheng4/c6b-step3/store, built by C6b; read only), guarded loader c6b_s3_harness.py, then m5_s3_post.py (c6b_s3_post.py, S2 only).
W=/home/fzheng4/wt-m5; PY=/home/fzheng4/AccelProf/.env/bin/python; S=$W/eval/baselines/setup
ST=/mnt/beegfs/fzheng4/c6b-step3/store
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) model=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p') rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
[ -d $ST ] && [ -s $ST/ov_ids.txt ] || { echo "stripped store missing on $(hostname): $ST"; exit 97; }
export BASELINE_TRACE_DIR=$ST BASELINE_MODES=collector-only
for sw in ${SWS:-1 0}; do
  O=$W/eval/results/closure-atomic-hop/step3-sw$sw/run-s2
  mkdir -p $O/probes $O/confirm $O/ov/probes $O/ov/confirm
  export CUVEIN_CHAIN_ATOMIC_HOP=$sw
  for k in ${KS:-$(seq 0 15)}; do
    f=$O/baselines-cuvein-shard${k}_16.csv
    [ -s $f ] && { echo "skip $k"; continue; }
    echo "== sw$sw shard $k $(date -Is)"
    t=$O/.tmp$k; rm -rf $t; mkdir -p $t
    S3_PROBES=$O/probes $PY $S/c6b_s3_harness.py analyze --manifest eval/baselines/manifest.csv --pset P1,P3,P4,P5,P6,P7,P9,PI --shard $k/16 \
        --tag "$k" --results-dir $t --confirm --confirm-dir $t/confirm --chain-closure --co-async --co-r3 off \
        --analysis-timeout 14400 --analysis-workers 16 > $O/shard$k.log 2>&1
    rc=$?; tail -1 $O/shard$k.log
    g=$(ls $t/baselines-cuvein-shard*.csv 2>/dev/null | head -1)
    if [ $rc -eq 0 ] && [ -n "$g" ] && [ -s "$g" ]; then
      $PY $S/c6b_anode.py "$g" $(hostname)
      mv $t/chain-kernels-*.jsonl $O/ 2>/dev/null
      [ -d $t/confirm ] && mv $t/confirm/* $O/confirm/ 2>/dev/null
      mv "$g" $f; rm -rf $t
    else echo "FAILED rc=$rc sw$sw $k"; fi
  done
  cp $ST/ov_ids.txt $O/ov/ov_ids.txt
  S3_PROBES=$O/ov/probes $PY $S/c6b_s3_harness.py analyze --manifest eval/baselines/manifest.csv --id-file $O/ov/ov_ids.txt \
      --tag ov --results-dir $O/ov --confirm --confirm-dir $O/ov/confirm --chain-closure --co-async --co-r3 off \
      --analysis-timeout 14400 --analysis-workers 16 > $O/ov/shard.log 2>&1
  echo "ov sw$sw rc=$?"
  $PY $S/c6b_anode.py $O/ov/baselines-cuvein-shardovall.csv $(hostname)
done
for sw in ${SWS:-1 0}; do
  echo "== post sw$sw $(date -Is)"
  M5_TAG=sw$sw $PY $S/m5_s3_post.py > $W/eval/x_logs/m5/s3-post-sw$sw.log 2>&1; echo "post sw$sw rc=$?"
done
echo "end $(date -Is)"
