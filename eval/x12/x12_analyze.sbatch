#!/usr/bin/env bash
#SBATCH --partition=normal
#SBATCH --exclusive
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=12:00:00
# X12 step 7: the C6 analysis (VERDICT_PARALLEL §7 command + --chain-closure, as X11's x11_a_chain_app.sbatch) of a parity-clean recording.
# Code = the read-only co-chain worktree ~/wt-x11-cochain (be325e03; T26's branch has no --chain-closure). ONLY after the gate passed.
#   APP=crs [STORE=final-2026-11-co-sh] [RES=co-sharded] sbatch -J x12-chain-crs x12_analyze.sbatch
set -u
APP=${APP:?}; STORE=${STORE:-final-2026-11-co-sh}; RES=${RES:-co-sharded}; W=${W:?}
C=/home/fzheng4/wt-x11-cochain; PY=/home/fzheng4/AccelProf/.env/bin/python; B=/mnt/beegfs/fzheng4/cuvein_traces
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
unset BASELINE_MODES BASELINE_TRACE_ALLOW_NONBEEGFS
export ACCEL_PROF_HOME=$C CUVEIN_HOME=$C
M=/mnt/beegfs/fzheng4/x12_work/runtree-$STORE-$APP/manifest.csv; d=$W/eval/results/$RES/chain-$APP; mkdir -p $d/confirm
echo "host=$(hostname) nproc=$(nproc) co-chain=$(git -C $C rev-parse HEAD) $(date -Is)"
BASELINE_TRACE_DIR=$B/$STORE BASELINE_MODES=collector-only $PY $C/eval/baselines/parallel.py analyze --manifest $M --id X11-$APP \
    --tag chain-$APP --results-dir $d --confirm --confirm-dir $d/confirm --chain-closure --analysis-timeout ${ATO:-14400} --analysis-workers 16
echo "== done rc=$? $(date -Is)"
