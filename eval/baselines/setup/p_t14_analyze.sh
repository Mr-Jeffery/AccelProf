#!/usr/bin/env bash
#SBATCH --job-name=cv-t14-analyze
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
# T14 step 5: `parallel.py analyze` of the store t14-after (T9's selection, vector-clock dumps
# re-oracled with the a2_uncertain flag; eval/baselines/a2_window_count.py rescore), vector-clock
# rows only (scalar-clock dumps carry no flag), twice:
#   WHICH=base  with the detector code of the base f127790 (CODE=<a `git archive f127790 python
#               eval/baselines eval/aggregate.py` tree>), which ignores the new field
#   WHICH=t14   with this worktree's code
# Same dumps, so any verdict difference is the T14 code's. ACCEL_PROF_HOME is pinned to the code
# tree, so python/ (sync_dominance, hb_oracle) is its own.
#   W=<wt> CODE=<tree> WHICH=base sbatch --array=0-15 -o <W>/build_logs/t14-analyze-%A_%a.log \
#       eval/baselines/setup/p_t14_analyze.sh
# IDS=<absolute id file> TAG=<suffix>: only those programs (re-scores that finished after the
# arrays), rows in their own shard CSV next to the arrays' (the tables keep the best row per id).
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/agent-a132f9279c0d8edd0}
case ${WHICH:?WHICH=base|t14} in
  base) CV=${CODE:?CODE=<f127790 tree>};;
  t14)  CV=$W;;
esac
cd "$CV" || exit 1
export ACCEL_PROF_HOME=$CV CUVEIN_HOME=$CV
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/t14-after
export BASELINE_MODES=vector-clock
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
OUT=$W/eval/results/t14-a2/analyze-$WHICH
echo "host=$(hostname) which=$WHICH code=$CV store=$BASELINE_TRACE_DIR shard=$K/$N"
$W/.env/bin/python eval/baselines/parallel.py analyze --manifest $W/eval/results/t9-rescore/manifest.t9.csv \
    --shard $K/$N --confirm --tag "t14$WHICH${TAG:-}" --results-dir "$OUT" ${IDS:+--id-file "$IDS"} \
    --confirm-dir "/mnt/beegfs/$USER/t14-a2/confirm-$WHICH" --analysis-timeout ${ATMO:-14400}
echo "== done $(date -Is)"
