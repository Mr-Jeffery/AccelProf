#!/bin/bash
#SBATCH --job-name=x9-ana
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=16 --exclusive
#SBATCH --time=1-00:00:00
#SBATCH --exclude=c0,c1,c2,c11,c12,c13,c18,c21,c22,c23,c34,c37,c46,c54
#SBATCH --output=/home/fzheng4/wt-x9/eval/x_logs/x9-ana-%j.log
# X9 step 4 (CPU): per id, `parallel.py analyze --both-barrier-orders --confirm` (True half = scalar-clock mode -> the
# main CSV + confirm files, False half = collector-only mode -> the bo0 CSV), then x9_pairs.py (pair level, both halves,
# file:line). IDS="a b" [FLAVOR=main|t5400|prunetest] [PRUNE=1] sbatch eval/cutlass/harness/x9_analyze.sh
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
TIMEV="/usr/bin/time -v -o"; [ -x /usr/bin/time ] || TIMEV="$PY $W/eval/cutlass/harness/x9_timev.py -o"   # no GNU time on some nodes
FLAVOR=${FLAVOR:-main}; ST=$CB/traces/$FLAVOR
export BASELINE_TRACE_DIR=$ST BASELINE_MODES=scalar-clock
M=$W/eval/cutlass/manifest_cutlass.csv; LOG=$W/eval/x_logs
RES=$W/eval/results/cutlass/$FLAVOR; CONF=$W/eval/cutlass/confirm/$FLAVOR; PAIRS=$W/eval/results/cutlass/pairs/$FLAVOR
mkdir -p $RES $CONF $PAIRS
cd $W || exit 1
for id in ${IDS:-}; do
  # dots that cannot align a recorded kernel -> dots_pruned/ (x9_prune_dots.py; PRUNE=0 keeps all)
  [ "${PRUNE:-1}" = 1 ] && $PY $W/eval/cutlass/harness/x9_prune_dots.py $ST/$id
  echo "=== $(date -Is) analyze $id"
  s=$(date +%s)
  $PY $W/eval/baselines/parallel.py analyze --manifest $M --id $id --confirm --both-barrier-orders \
      --analysis-timeout 82800 --analysis-mem-gb 48 --tag "$id-" --results-dir $RES --confirm-dir $CONF \
      > $LOG/analyze-$FLAVOR-$id.out 2>&1
  echo "  analyze rc=$? wall=$(( $(date +%s) - s ))s ($(tail -1 $LOG/analyze-$FLAVOR-$id.out | cut -c1-160))"
  s=$(date +%s)
  $TIMEV $LOG/time-pairs-$FLAVOR-$id.txt $PY $W/eval/cutlass/harness/x9_pairs.py --id $id --store $ST \
      --manifest $M --out $PAIRS/$id.json > $LOG/pairs-$FLAVOR-$id.out 2>&1
  echo "  pairs rc=$? wall=$(( $(date +%s) - s ))s maxrss_kb=$(awk -F': ' '/Maximum resident/{print $2}' $LOG/time-pairs-$FLAVOR-$id.txt) ($(tail -1 $LOG/pairs-$FLAVOR-$id.out | cut -c1-300))"
done
echo "=== $(date -Is) done"
