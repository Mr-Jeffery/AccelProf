#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=04:00:00
# X11: re-score a finished clock-mode recording with the verdict code of the old rows (origin/cuVein 98371ee1 = partA, ~/wt-x11),
# 16 analysis workers, as the old rows (analysis_workers=16). No re-recording. Usage: MODE=scalar-clock APP=tridiagonal sbatch ...
W=/home/fzheng4/wt-x11; PY=/home/fzheng4/AccelProf/.env/bin/python
T=x11b-$MODE-$APP-r1; L=$W/eval/x_logs/x11/stageB/$T-reanalysis
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
mkdir -p $L/confirm
echo "host=$(hostname) code=$(git -C $W rev-parse HEAD) $(date -Is)"
BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/$T BASELINE_MODES=$MODE $PY $W/eval/baselines/parallel.py analyze \
  --manifest /mnt/beegfs/fzheng4/x11_work/runtree-$T/manifest.csv --id X11-$APP --tag $T-reanalysis --results-dir $L \
  --confirm --confirm-dir $L/confirm --analysis-timeout 13800 --analysis-workers 16
echo "rc=$? $(date -Is)"; cat $L/*.csv
