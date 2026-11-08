#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH --exclusive
#SBATCH -t 02:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46,c11,c12,c13,c18
#SBATCH -o /home/fzheng4/wt-c6b/eval/x_logs/c6b-s3-prep-%x-%j.log
# C6b step 3 prep: strip hb_* from the scalar-clock recordings (store final-2026-11-view), then a strict-guard demo and a P5 smoke run.
W=/home/fzheng4/wt-c6b
PY=/home/fzheng4/AccelProf/.env/bin/python
S=$W/eval/baselines/setup
cd $W || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) nproc=$(nproc) rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
date +%T; $PY -I $S/c6b_s3_strip.py; date +%T
O=$W/eval/results/co-chain-b/step3
export BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/c6b-step3/store BASELINE_MODES=collector-only
mkdir -p $O/strict-demo $O/smoke/probes
echo "== strict demo (S3_STRICT=1, P5-canary): expected to fail at the first probe of an absent hb_ key"
S3_STRICT=1 S3_PROBES=$O/strict-demo $PY $S/c6b_s3_harness.py analyze --manifest eval/baselines/manifest.csv --id P5-canary --tag strict --results-dir $O/strict-demo --analysis-workers 1 --chain-closure --co-async --co-r3 strict 2>&1 | tail -5
cut -c1-500 $O/strict-demo/baselines-cuvein-shardstrictall.csv
echo "== smoke: P5 pset, S1, 16 workers"
S3_PROBES=$O/smoke/probes $PY $S/c6b_s3_harness.py analyze --manifest eval/baselines/manifest.csv --pset P5 --tag smoke --results-dir $O/smoke --confirm --confirm-dir $O/smoke/confirm \
   --chain-closure --co-async --co-r3 strict --analysis-timeout 14400 --analysis-workers 16 2>&1 | tail -3
$PY -c "
import csv
for r in csv.DictReader(open('$O/smoke/baselines-cuvein-shardsmokeall.csv')): print(r['id'], r['mode'], r['verdict'], r['reports_dedup'], r['notes'][-80:])
" | head -40
echo end $(date -Is)
