#!/usr/bin/env bash
#SBATCH --job-name=cv-t10-analyze
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
# T10 step 3: `parallel.py analyze` of the AFTER store t10-after (eval/baselines/t10_rescore.py)
# with this worktree's detector (default strength policy `token`), over T9's manifest; the
# BEFORE rows are T9's AFTER rows (eval/results/t9-rescore/after/). IDFILE restricts the ids.
# ACCEL_PROF_HOME is pinned to the worktree, so python/ (sync_dominance, hb_oracle) is its own.
#   W=<worktree> IDFILE=<ids> sbatch --array=0-31 -o <W>/build_logs/t10-analyze-%A_%a.log \
#       <W>/eval/baselines/setup/p_t10_analyze.sh
set -u
W=${W:?W=<the T10 worktree>}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/t10-after
export BASELINE_MODES=vector-clock,scalar-clock
unset CUVEIN_STRONG_LDST
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
OUT=$W/eval/results/t10-rescore/${WHICH:-after}
echo "host=$(hostname) store=$BASELINE_TRACE_DIR shard=$K/$N HEAD=$(git -C $W rev-parse --short HEAD) python-diff=$(git -C $W diff HEAD -- python | sha256sum | cut -c1-16)"
$W/.env/bin/python eval/baselines/parallel.py analyze --manifest $W/eval/results/t9-rescore/manifest.t9.csv \
    ${IDFILE:+--id-file $IDFILE} --shard $K/$N --confirm --tag "t10${WHICH:-after}" --results-dir "$OUT" \
    --confirm-dir "/mnt/beegfs/$USER/t10-confirm/${WHICH:-after}" --analysis-timeout ${ATMO:-14400}
echo "== done $(date -Is)"
