#!/usr/bin/env bash
#SBATCH --job-name=x11-gate
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/gate-%j.log
# X11 control gate: runs when the 12 control collector-only jobs (overlap, fpc, gpp, crs x 3 runs) have ended.
# Chain-closure verdict (origin/eval/co-chain be325e03, read-only ~/wt-x11-cochain) of each control recording, then the
# comparison with the old collector-only rows, and the clock-mode smoke test (overlap, scalar-clock) against its old row.
# A verdict that differs (control or smoke) => scancel every stage B job (x11b-*).
W=/home/fzheng4/wt-x11-cochain; PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces; L=/home/fzheng4/wt-x11/eval/x_logs/x11
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) co-chain=$(git -C $W rev-parse HEAD) $(date -Is)"
for a in overlap fpc gpp crs; do for r in 1 2 3; do
  T=x11-co-r$r-$a; M=/mnt/beegfs/fzheng4/x11_work/runtree-$T/manifest.csv
  [ -f $M ] || { echo "no manifest $M"; continue; }
  d=$L/stageA-chain-r$r-$a; mkdir -p $d/confirm
  BASELINE_TRACE_DIR=$B/$T BASELINE_MODES=collector-only $PY $W/eval/baselines/parallel.py analyze --manifest $M --id X11-$a \
     --tag chain-r$r-$a --results-dir $d --confirm --confirm-dir $d/confirm --chain-closure \
     --analysis-timeout 14400 --analysis-workers 16 > $d/analyze.log 2>&1
  echo "chain $a r$r rc=$?"
done; done
$PY $L/../../../eval/x11/x11_gate.py $L $W $L/gate_result.txt; rc=$?
echo "gate rc=$rc ($(date -Is))"
$PY $L/../../../eval/x11/x11_smoke_cmp.py $L/stageB/x11smoke-scalar-clock-overlap-r1 $L/smoke_result.txt; src=$?
echo "smoke rc=$src"
[ $src -eq 1 ] && rc=1
if [ $rc -eq 1 ]; then
  echo "MISMATCH: scancel all stage B jobs"; squeue -u fzheng4 -h -o "%i %j" | awk '$2 ~ /^x11b-/{print $1}' | xargs -r scancel
  squeue -u fzheng4 -h -o "%i %j" | awk '$2 ~ /^x11b-/' | wc -l | sed 's/^/stage B jobs still queued after scancel: /'
fi
