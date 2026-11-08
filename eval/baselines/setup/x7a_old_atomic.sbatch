#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -c 2
#SBATCH -t 24:00:00
#SBATCH -x c0,c1,c22,c23,c34,c46
#SBATCH -J x7a-old-cas
#SBATCH -o /home/fzheng4/wt-x7a/eval/x_logs/x7a-old-cas-%j.log
# X7 A5 follow-up: the ORIGINAL code (wt-x7a-base = 40b5222's python/ and harness, serial, no cache) on
# P9-atomicCAS-cuda collector-only from final-2026-11-co, analysis cap lifted to 86400 s, to get the
# reference verdict C1's row (ERROR, analysis-timeout 14400 s) does not have.
B=/home/fzheng4/wt-x7a-base
PY=/home/fzheng4/AccelProf/.env/bin/python
O=/home/fzheng4/wt-x7a/eval/results/verdict-timing/old-atomicCAS
mkdir -p $O; cd $B || exit 1
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$B CUVEIN_HOME=$B
echo "host=$(hostname) rev=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) start=$(date -Is)"
BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11-co BASELINE_MODES=collector-only \
  $PY eval/baselines/parallel.py analyze --manifest eval/baselines/manifest.csv --id P9-atomicCAS-cuda \
  --tag old-cas --results-dir $O --analysis-timeout 86400
echo "rc=$? end=$(date -Is)"
