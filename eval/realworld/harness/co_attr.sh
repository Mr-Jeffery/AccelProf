#!/bin/bash
# C2: kernel-aware attribution of collector-only runs on a CPU node. Env: SET, FLAVOR, IDS.
source /home/fzheng4/wt-co-rw/eval/realworld/harness/co_header.sh || exit $?
FLAVOR=${FLAVOR:-main}
export ACCEL_PROF_HOME=$A RW_MODES=collector-only
for CH in ${RW_CUDA_HOME:-/usr/local/cuda-13.4} /usr/local/cuda-13.3 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
[ -n "$CUDA_HOME" ] || { echo "C2 attr: host=$(hostname) no CUDA toolkit with nvdisasm" >&2; exit 96; }
source $W/eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
cd $W || exit 1
case "$FLAVOR" in
  main)  S=$S0;       RES=$W/eval/results/$RESNAME ;;
  c5400) S=$S0/c5400; RES=$W/eval/results/$RESNAME/c5400 ;;
  *) echo bad FLAVOR >&2; exit 2 ;;
esac
LOG=$W/eval/x_logs; mkdir -p $RES/attrib
echo "C2 attr: host=$(hostname) job=${SLURM_JOB_ID:-none} set=$SET flavor=$FLAVOR cuda=$CUDA_HOME date=$(date -Is)"
for id in ${IDS:-}; do
  echo "=== $(date -Is) attribute $id"
  [ -s "$S/$id/meta.json" ] || { echo "C2 attr: $S/$id/meta.json unreadable on $(hostname)" >&2; exit 97; }
  if ! $PY -c "import csv,sys; sys.exit(0 if any(r['verdict'] in ('RACE','CLEAN') for r in csv.DictReader(open('$RES/baselines-cuvein-shard$id-all.csv'))) else 1)" 2>/dev/null; then echo "  $id did not end RACE or CLEAN: attribution skipped (not scoreable)"; continue; fi
  $PY $W/eval/realworld/harness/rw_attribute.py --id $id --store $S --manifest $MANIFEST --out $RES/attrib/$id.json > $LOG/co-attrib-$FLAVOR-$id.out 2>&1
  echo "  attribute rc=$? ($(tail -1 $LOG/co-attrib-$FLAVOR-$id.out | cut -c1-200))"
done
echo "=== $(date -Is) attr done"
