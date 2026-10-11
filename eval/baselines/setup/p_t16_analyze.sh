#!/usr/bin/env bash
#SBATCH --job-name=cv-t16-analyze
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
source /home/fzheng4/AccelProf/eval/baselines/setup/home_quota_guard.sh
# T16 step 4: `parallel.py analyze` of one set under one policy with this worktree's detector:
#   SET=main   recorded: store t12-after;      certain: store t16-certain       (manifest.t9.csv)
#   SET=exits  recorded: store t16-recorded-exits (symlinks to the dumps' own stores);
#              certain: store t16-certain-exits (manifest.csv)
# The verdict layer is the same; only hb_races differ (the policy they were computed under).
#   W=<worktree> SET=main WHICH=recorded|certain sbatch --array=0-31 -o <W>/build_logs/t16-analyze-%A_%a.log \
#       <W>/eval/baselines/setup/p_t16_analyze.sh
set -u
W=${W:?W=<the T16 worktree>}; SET=${SET:-main}; WHICH=${WHICH:?WHICH=recorded|certain}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
unset CUVEIN_STRONG_LDST CUVEIN_GATE CUVEIN_GATE_POLICY CUVEIN_R3_TRACE_RELEASE CUVEIN_R3_TRACE_ACQUIRE \
    CUVEIN_R3_BEFORE_ACQUIRE CUVEIN_R1_LOOP_SCOPE CUVEIN_R3_LANDING
case $SET-$WHICH in
  main-recorded)  STORE=t12-after; MAN=$W/eval/results/t9-rescore/manifest.t9.csv ;;
  main-certain)   STORE=t16-certain; MAN=$W/eval/results/t9-rescore/manifest.t9.csv ;;
  exits-recorded) STORE=t16-recorded-exits; MAN=$W/eval/baselines/manifest.csv ;;
  exits-certain)  STORE=t16-certain-exits; MAN=$W/eval/baselines/manifest.csv ;;
  *) echo "bad SET=$SET WHICH=$WHICH"; exit 2 ;;
esac
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$STORE
export BASELINE_MODES=vector-clock,scalar-clock
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
OUT=$W/eval/results/t16-rescore/$SET-$WHICH
IDFILE=${IDFILE:-$W/eval/results/t16-rescore/ids_$SET.txt}
echo "host=$(hostname) set=$SET which=$WHICH store=$BASELINE_TRACE_DIR shard=$K/$N HEAD=$(git -C $W rev-parse --short HEAD) python-diff=$(git -C $W diff HEAD -- python | sha256sum | cut -c1-16)"
$W/.env/bin/python eval/baselines/parallel.py analyze --manifest $MAN --id-file $IDFILE --shard $K/$N \
    --confirm --tag "t16$SET$WHICH" --results-dir "$OUT" \
    --confirm-dir "/mnt/beegfs/$USER/t16-confirm/$SET-$WHICH" --analysis-timeout ${ATMO:-14400}
echo "== done $(date -Is)"
