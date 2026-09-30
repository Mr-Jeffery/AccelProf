#!/usr/bin/env bash
#SBATCH --job-name=cv-t12-analyze
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=24:00:00
#SBATCH --exclude=c54,c2
# T12 step 4: `parallel.py analyze` of one of the three analyses of eval/baselines/t12_rescore.py
# over T9's manifest, with this worktree's detector:
#   WHICH=before  store t10-after, CUVEIN_R3_TRACE_{RELEASE,ACQUIRE}=0 CUVEIN_R3_BEFORE_ACQUIRE=0 (pre-T12)
#   WHICH=r3only  store t10-after, defaults (R3 amendments; trusting-gate hb_races)
#   WHICH=after   store t12-after, defaults (R3 amendments; instance-gate hb_races)
# IDFILE restricts the ids (eval/results/t12-rescore/ids_affected.txt).
#   W=<worktree> WHICH=... IDFILE=<ids> sbatch --array=0-31 -o <W>/build_logs/t12-analyze-%A_%a.log \
#       <W>/eval/baselines/setup/p_t12_analyze.sh
set -u
W=${W:?W=<the T12 worktree>}
WHICH=${WHICH:?WHICH=before|r3only|after}
cd "$W" || exit 1
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
unset CUVEIN_STRONG_LDST CUVEIN_GATE CUVEIN_R3_TRACE_RELEASE CUVEIN_R3_TRACE_ACQUIRE CUVEIN_R3_BEFORE_ACQUIRE
case $WHICH in
  before) STORE=t10-after; export CUVEIN_R3_TRACE_RELEASE=0 CUVEIN_R3_TRACE_ACQUIRE=0 CUVEIN_R3_BEFORE_ACQUIRE=0 ;;
  r3only) STORE=t10-after ;;
  after)  STORE=t12-after ;;
  *) echo "bad WHICH=$WHICH"; exit 2 ;;
esac
export BASELINE_TRACE_DIR=/mnt/beegfs/$USER/cuvein_traces/$STORE
export BASELINE_MODES=vector-clock,scalar-clock
N=${SLURM_ARRAY_TASK_COUNT:-1}; K=${SLURM_ARRAY_TASK_ID:-0}
OUT=$W/eval/results/t12-rescore/$WHICH
echo "host=$(hostname) which=$WHICH store=$BASELINE_TRACE_DIR shard=$K/$N HEAD=$(git -C $W rev-parse --short HEAD) python-diff=$(git -C $W diff HEAD -- python | sha256sum | cut -c1-16)"
$W/.env/bin/python eval/baselines/parallel.py analyze --manifest $W/eval/results/t9-rescore/manifest.t9.csv \
    ${IDFILE:+--id-file $IDFILE} --shard $K/$N --confirm --tag "t12$WHICH" --results-dir "$OUT" \
    --confirm-dir "/mnt/beegfs/$USER/t12-confirm/$WHICH" --analysis-timeout ${ATMO:-14400}
echo "== done $(date -Is)"
