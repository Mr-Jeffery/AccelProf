#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 12:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46,c11,c12,c13,c18
#SBATCH -o /home/fzheng4/wt-c6b/eval/x_logs/c6b-s3-ov-%x-%j.log
# C6b step 3 override: the ids whose scalar-clock recording comes from a long / 24 h pass (meta of that pass, ov_ids.txt) re-run at one setting.
#   MODE=strip : only rebuild the stripped store (writes ov_ids.txt);   SET=s1|s2|cfg : run the ov ids at that setting into run-$SET/ov
W=/home/fzheng4/wt-c6b
PY=/home/fzheng4/AccelProf/.env/bin/python
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) set=${SET:-} mode=${MODE:-} rev=$(git rev-parse --short=12 HEAD) start=$(date -Is)"
if [ "$MODE" = strip ]; then $PY -I $S/c6b_s3_strip.py; echo end $(date -Is); exit 0; fi
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/c6b-step3/store BASELINE_MODES=collector-only
case $SET in s1) R3=strict;; s2) R3=off;; cfg) R3=cfg;; *) echo bad SET; exit 4;; esac
O=$W/eval/results/co-chain-b/step3/run-$SET/ov
mkdir -p $O/probes $O/confirm
cp /mnt/beegfs/fzheng4/c6b-step3/store/ov_ids.txt $O/ov_ids.txt
S3_PROBES=$O/probes $PY $S/c6b_s3_harness.py analyze --manifest eval/baselines/manifest.csv --id-file $O/ov_ids.txt \
    --tag ov --results-dir $O --confirm --confirm-dir $O/confirm --chain-closure --co-async --co-r3 $R3 \
    --analysis-timeout 14400 --analysis-workers 16 > $O/shard.log 2>&1
echo rc=$?
tail -2 $O/shard.log
$PY $S/c6b_anode.py $O/baselines-cuvein-shardovall.csv $(hostname)
echo "end $(date -Is)"
