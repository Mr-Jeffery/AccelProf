#!/bin/bash
# X5 step 2: the analysis shards (no GPU; reads the BeeGFS stores).
#   TASK=bo  NSHARDS=24 sbatch --array=0-23 eval/baselines/setup/p_x5_collect.sh   # barrier_ordered_bins
#   TASK=var NSHARDS=8  sbatch --array=0-7  eval/baselines/setup/p_x5_collect.sh   # pcdg_variance
# Each shard appends to eval/results/x5/<task>_shard<k>.jsonl and skips what is already there, so a
# shard killed by the time limit is resubmitted as it is.
#SBATCH -p normal
#SBATCH -t 1-00:00:00
#SBATCH -c 1
#SBATCH -o /home/fzheng4/wt-x5/eval/x_logs/x5-%x-%A_%a.log
W=${W:-/home/fzheng4/wt-x5}
RT=${RT:-/home/fzheng4/AccelProf}
PY=$RT/.env/bin/python
TASK=${TASK:?TASK=bo|var}
N=${NSHARDS:?NSHARDS}
cd "$W" || exit 1
export CUVEIN_HOME=$W
echo "node $(hostname) job ${SLURM_JOB_ID} task ${SLURM_ARRAY_TASK_ID}/$N $(date -Is)"; git rev-parse HEAD
case $TASK in
  bo)  SCRIPT=barrier_ordered_bins.py ;;
  var) SCRIPT=pcdg_variance.py ;;
  *)   echo "bad TASK"; exit 2 ;;
esac
# PLAN / OUTPFX default to the task's own plan and shard files; the barrier-binning keys that waited
# behind a heavy key were re-planned with `barrier_ordered_bins.py resplit` and run as
#   TASK=bo NSHARDS=10 PLAN=eval/results/x5/bo_extra_plan.json OUTPFX=bo_xshard sbatch --array=0-9 ...
PLAN=${PLAN:-eval/results/x5/${TASK}_plan.json}
OUTPFX=${OUTPFX:-${TASK}_shard}
$PY eval/baselines/setup/$SCRIPT collect --plan $PLAN \
    --shard ${SLURM_ARRAY_TASK_ID}/$N --out "eval/results/x5/${OUTPFX}{shard}.jsonl" \
    --analysis-timeout ${ANALYSIS_TIMEOUT:-14400} --mem-gb ${MEM_GB:-60}
rc=$?
echo "done $(date -Is) rc=$rc"
exit $rc
