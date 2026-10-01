#!/usr/bin/env bash
#SBATCH --job-name=cv-t9-analyze
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/t9-analyze-%A_%a.log
source /home/fzheng4/AccelProf/eval/baselines/setup/home_quota_guard.sh
# T9 step 6: `parallel.py analyze` of the re-score stores (eval/baselines/t9_rescore.py).
#   WHICH=before  the BEFORE store (recorded dumps) with the detector code of 1a3aea5
#                 (CODE=<a `git archive 1a3aea5 python eval/baselines eval/aggregate.py` tree>)
#   WHICH=after   the AFTER store (vector-clock dumps re-scored by the T9 oracle) with this
#                 worktree's code
# ACCEL_PROF_HOME is pinned to the code tree, so python/ (sync_dominance, hb_oracle) is its own.
#   CODE=... WHICH=before sbatch --array=0-15 eval/baselines/setup/p_t9_analyze.sh
set -u
W=/home/fzheng4/wt-T9
case ${WHICH:?WHICH=before|after} in
  before) CV=${CODE:?CODE=<1a3aea5 tree>}; TAG=t9-before;;
  after)  CV=$W; TAG=t9-after;;
esac
cd "$CV" || exit 1
export ACCEL_PROF_HOME=$CV CUVEIN_HOME=$CV
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$TAG
export BASELINE_MODES=vector-clock,scalar-clock
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
OUT=$W/eval/results/t9-rescore/$WHICH
echo "host=$(hostname) which=$WHICH code=$CV store=$BASELINE_TRACE_DIR shard=$K/$N"
$W/.env/bin/python eval/baselines/parallel.py analyze --manifest $W/eval/results/t9-rescore/manifest.t9.csv \
    --shard $K/$N --confirm --tag "t9$WHICH" --results-dir "$OUT" \
    --confirm-dir "$W/eval/baselines/confirm_t9_$WHICH" --analysis-timeout ${ATMO:-14400}
echo "== done $(date -Is)"
