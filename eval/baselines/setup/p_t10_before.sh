#!/usr/bin/env bash
#SBATCH --job-name=cv-t10-before
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=06:00:00
#SBATCH --exclude=c54,c2
# T10: the BEFORE baseline of the re-score, checked where it matters. T9's AFTER rows (the T9
# code b1a6408 on t9-after) are the BEFORE of every program; this re-runs the pre-T10 detector of
# cuVein f127790 (CODE = `git archive f127790 python eval/baselines eval/aggregate.py`, default
# policy `generic`) on t9-after for the affected programs (IDFILE), so the rows it is compared with
# come from the code T10 replaces, not only from T9's branch.
#   W=<worktree> CODE=<tree> IDFILE=<ids> sbatch --array=0-3 -o <W>/build_logs/t10-before-%A_%a.log \
#       <W>/eval/baselines/setup/p_t10_before.sh
set -u
W=${W:?}; CV=${CODE:?}
cd "$CV" || exit 1
export ACCEL_PROF_HOME=$CV CUVEIN_HOME=$CV
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/t9-after
export BASELINE_MODES=vector-clock,scalar-clock
unset CUVEIN_STRONG_LDST
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
echo "host=$(hostname) code=$CV store=$BASELINE_TRACE_DIR shard=$K/$N"
$W/.env/bin/python eval/baselines/parallel.py analyze --manifest $W/eval/results/t9-rescore/manifest.t9.csv \
    --id-file ${IDFILE:?} --shard $K/$N --confirm --tag "t10before" \
    --results-dir "$W/eval/results/t10-rescore/before-affected" \
    --confirm-dir "/mnt/beegfs/$USER/t10-confirm/before-affected" --analysis-timeout ${ATMO:-14400}
echo "== done $(date -Is)"
