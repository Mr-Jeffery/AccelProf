#!/bin/bash
#SBATCH --job-name=x9-anas
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --exclusive
#SBATCH --time=1-00:00:00
#SBATCH --exclude=c0,c1,c2,c11,c12,c13,c18,c21,c22,c23,c34,c35,c37,c46,c54
#SBATCH --output=/home/fzheng4/wt-x9/eval/x_logs/x9-anas-%j.log
# X9 step 4 (CPU) for whole-binary recordings: per parent id, x9_split.py (one sub-store + manifest row per recorded
# kernel name, eval/cutlass/manifests_k/<id>.csv), then per sub-id, PAR at a time: `parallel.py analyze --confirm
# --both-barrier-orders` (True half = scalar-clock mode -> main CSV, False half = collector-only mode -> bo0 CSV) and
# x9_pairs.py (pair level, both halves, file:line).
#   IDS="a b" [FLAVOR=main|t5400] [PAR=16] [MEMGB=28] [SPLIT=1] [SKIPDONE=1] sbatch eval/cutlass/harness/x9_analyze_split.sh
# PAR 16: each sub-id is one single-threaded process of < 0.1 GB RSS (load 4.00, 3 of 125 GB used at PAR=4, job 324864).
# SKIPDONE=1: a sub-id whose pair file already exists is not re-analyzed (resubmission after a cancel).
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
TIMEV="/usr/bin/time -v -o"; [ -x /usr/bin/time ] || TIMEV="$PY $W/eval/cutlass/harness/x9_timev.py -o"   # no GNU time on some nodes
FLAVOR=${FLAVOR:-main}; ST=$CB/traces/$FLAVOR; PAR=${PAR:-16}; MEMGB=${MEMGB:-28}; SKIPDONE=${SKIPDONE:-1}
export BASELINE_TRACE_DIR=$ST BASELINE_MODES=scalar-clock
M=$W/eval/cutlass/manifest_cutlass.csv; MK=$W/eval/cutlass/manifests_k; LOG=$W/eval/x_logs/anas/$FLAVOR
RES=$W/eval/results/cutlass/$FLAVOR; CONF=$W/eval/cutlass/confirm/$FLAVOR; PAIRS=$W/eval/results/cutlass/pairs/$FLAVOR
mkdir -p $RES $CONF $PAIRS $MK $LOG
cd $W || exit 1
one() {   # one sub-id: analyze + pairs
  local sid=$1 m=$2 s rc1 rc2
  [ "$SKIPDONE" = 1 ] && [ -s $PAIRS/$sid.json ] && { echo "  $sid skipped (pair file exists)"; return; }
  s=$(date +%s)
  $PY $W/eval/baselines/parallel.py analyze --manifest $m --id $sid --confirm --both-barrier-orders \
      --analysis-timeout 82800 --analysis-mem-gb $MEMGB --tag "$sid-" --results-dir $RES --confirm-dir $CONF \
      > $LOG/analyze-$sid.out 2>&1; rc1=$?
  local t1=$(( $(date +%s) - s )); s=$(date +%s)
  $TIMEV $LOG/time-pairs-$sid.txt $PY $W/eval/cutlass/harness/x9_pairs.py --id $sid --store $ST \
      --manifest $m --out $PAIRS/$sid.json --mem $MEMGB > $LOG/pairs-$sid.out 2>&1; rc2=$?
  echo "  $sid analyze rc=$rc1 ${t1}s pairs rc=$rc2 $(( $(date +%s) - s ))s maxrss_kb=$(awk -F': ' '/Maximum resident/{print $2}' $LOG/time-pairs-$sid.txt) | $(tail -1 $LOG/pairs-$sid.out | cut -c1-200)"
}
export -f one; export PY W RES CONF PAIRS LOG ST MEMGB TIMEV SKIPDONE
for id in ${IDS:-}; do
  echo "=== $(date -Is) split $id"
  if [ "${SPLIT:-1}" = 1 ] || [ ! -f $MK/$id.csv ]; then
    $PY $W/eval/cutlass/harness/x9_split.py --store $ST --id $id --manifest $M --manifest-out $MK/$id.csv \
        > $LOG/split-$id.out 2>&1 || { echo "  split FAILED: $(tail -2 $LOG/split-$id.out)"; continue; }
  fi
  tail -1 $LOG/split-$id.out
  tail -n +2 $MK/$id.csv | cut -d, -f1 | xargs -P $PAR -I{} bash -c "one {} $MK/$id.csv"
done
echo "=== $(date -Is) done"
