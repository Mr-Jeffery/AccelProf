#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
# X11 stage A: chain-closure verdict (co-chain be325e03, read-only) for one non-control app, runs 1-3. Usage: APP=knn sbatch -J x11-chain-knn x11_a_chain_app.sbatch
W=/home/fzheng4/wt-x11-cochain; PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces; L=/home/fzheng4/wt-x11/eval/x_logs/x11; a=$APP
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) co-chain=$(git -C $W rev-parse HEAD) $(date -Is)"
for r in 1 2 3; do
  if [ $a = atomicCAS ]; then T=x11-co-r$r; else T=x11-co-r$r-$a; fi
  M=/mnt/beegfs/fzheng4/x11_work/runtree-$T/manifest.csv
  [ -f $M ] || { echo "no manifest $M"; continue; }
  d=$L/stageA-chain-r$r-$a; mkdir -p $d/confirm
  BASELINE_TRACE_DIR=$B/$T BASELINE_MODES=collector-only $PY $W/eval/baselines/parallel.py analyze --manifest $M --id X11-$a \
     --tag chain-r$r-$a --results-dir $d --confirm --confirm-dir $d/confirm --chain-closure \
     --analysis-timeout 14400 --analysis-workers 16 > $d/analyze.log 2>&1
  echo "chain $a r$r rc=$?"
done
echo "done $(date -Is)"
