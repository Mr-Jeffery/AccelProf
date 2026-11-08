#!/usr/bin/env bash
#SBATCH --job-name=x11-chain
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/wt-x11/eval/x_logs/x11/stageA-chain-%j.log
# X11 stage A: the chain-closure verdict layer of origin/eval/co-chain (be325e03, read-only worktree ~/wt-x11-cochain,
# nothing merged) applied to the collector recordings of the three runs: parallel.py analyze --chain-closure,
# as eval/baselines/setup/c6_step2.sbatch (CPU only, --analysis-workers 16, --analysis-timeout 14400).
# Usage: [RUNS="1 2 3"] sbatch x11_a_chain.sbatch
W=/home/fzheng4/wt-x11-cochain; PY=/home/fzheng4/AccelProf/.env/bin/python
B=/mnt/beegfs/fzheng4/cuvein_traces; L=/home/fzheng4/wt-x11/eval/x_logs/x11
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) nproc=$(nproc) co-chain=$(git -C $W rev-parse HEAD) $(lscpu | sed -n 's/^Model name: *//p') $(date -Is)"
for r in ${RUNS:-1 2 3}; do
  T=x11-co-r$r; M=/mnt/beegfs/fzheng4/x11_work/runtree-$T/manifest.csv
  ids=$($PY -c "import csv;print(','.join(x['id'] for x in csv.DictReader(open('$M'))))")
  d=$L/stageA-chain-r$r; mkdir -p $d/confirm
  echo "== run $r $(date -Is)"
  BASELINE_TRACE_DIR=$B/$T BASELINE_MODES=collector-only $PY $W/eval/baselines/parallel.py analyze --manifest $M --id $ids \
      --tag chain-r$r --results-dir $d --confirm --confirm-dir $d/confirm --chain-closure \
      --analysis-timeout 14400 --analysis-workers 16 > $d/analyze.log 2>&1
  echo "rc=$? $(tail -1 $d/analyze.log)"
done
echo "== done $(date -Is)"
