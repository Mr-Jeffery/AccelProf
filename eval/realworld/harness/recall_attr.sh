#!/bin/bash
# T21b attribution on a CPU node (partition normal; needs nvdisasm/cuobjdump, no GPU). Env: FLAVOR, IDS.
# Same inputs and outputs as the attribution step of recall_job.sh (store S, results RES, manifest_t21b.csv).
source /home/fzheng4/wt-t21b/eval/realworld/harness/recall_header.sh || exit $?
FLAVOR=${FLAVOR:-main}
export ACCEL_PROF_HOME=$A
for CH in ${RW_CUDA_HOME:-/usr/local/cuda-13.3} /usr/local/cuda-13.4 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
[ -n "$CUDA_HOME" ] || { echo "T21b attr: host=$(hostname) no CUDA toolkit with nvdisasm" >&2; exit 96; }
source $W/eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
cd $W || exit 1
case "$FLAVOR" in
  main)    S=$S0;         RES=$W/eval/results/realworld ;;
  certain) S=$S0/certain; RES=$W/eval/results/realworld/certain ;;
  vc5400)  S=$S0/vc5400;  RES=$W/eval/results/realworld/vc5400 ;;
  longcap) S=$S0/longcap; RES=$W/eval/results/realworld/longcap ;;
  *) echo bad FLAVOR >&2; exit 2 ;;
esac
MANIFEST=${MANIFEST:-$W/eval/realworld/manifest_t21b.csv}
LOG=$W/eval/x_logs; mkdir -p $RES/attrib
echo "T21b attr: host=$(hostname) job=${SLURM_JOB_ID:-none} flavor=$FLAVOR cuda=$CUDA_HOME date=$(date -Is)"
for id in ${IDS:-}; do
  echo "=== $(date -Is) attribute $id flavor=$FLAVOR"
  [ -s "$S/$id/meta.json" ] || { echo "T21b attr: $S/$id/meta.json unreadable on $(hostname)" >&2; exit 97; }
  if ! $PY -c "import csv,sys; sys.exit(0 if any(r['verdict'] in ('RACE','CLEAN') for r in csv.DictReader(open('$RES/baselines-cuvein-shard$id-all.csv'))) else 1)" 2>/dev/null; then echo "  no mode of $id ended RACE or CLEAN: attribution skipped (not scoreable)"; continue; fi
  $PY $W/eval/realworld/harness/rw_attribute.py --id $id --store $S --manifest $MANIFEST --out $RES/attrib/$id.json > $LOG/attrib-$FLAVOR-$id.out 2>&1
  echo "  attribute rc=$? ($(tail -1 $LOG/attrib-$FLAVOR-$id.out | cut -c1-200))"
  CP=$W/eval/x_logs/store_copy/$FLAVOR/$id; mkdir -p $CP; cp $S/$id/meta.json $CP/ 2>/dev/null; for f in $S/$id/logs/*.txt; do tail -c 30000 "$f" > $CP/$(basename $f); done 2>/dev/null
done
echo "=== $(date -Is) attr done"
