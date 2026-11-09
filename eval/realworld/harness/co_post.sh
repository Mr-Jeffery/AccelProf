#!/bin/bash
# C2: score (collector-only), diff against scalar-clock, tables. CPU node, after the attribution/re-analysis jobs.
source /home/fzheng4/wt-co-rw/eval/baselines/gpu_env.sh
export ACCEL_PROF_HOME=/home/fzheng4/AccelProf RW_MODES=collector-only
cd /home/fzheng4/wt-co-rw || exit 1
$PY eval/realworld/harness/rw_score.py --results eval/results/realworld_co --manifest eval/realworld/manifest_t21b.csv --write
$PY eval/realworld/harness/rw_score.py --results eval/results/realworld_co_t21c --manifest eval/realworld/manifest_t21c.csv --exclude lightgbm-new-1,lightgbm-new-2,llamacpp-open-2 --write
unset RW_MODES
$PY eval/realworld/harness/co_diff.py --set recall --out eval/results/realworld_co/co_only.csv
$PY eval/realworld/harness/co_diff.py --set cand --out eval/results/realworld_co_t21c/co_only.csv
$PY eval/realworld/harness/co_tables.py > eval/x_logs/co-tables.out 2>&1; tail -3 eval/x_logs/co-tables.out
