#!/bin/bash
# T21b long pass, CPU half: `parallel.py analyze` of the stored traces of <ids> with a long --analysis-timeout, then the attribution.
# Env: FLAVOR (longcap-vc | longcap-sc), IDS, LONG_ATO (default 84600 s, Jeffery: tool cap inside a 24 h job).
source /home/fzheng4/wt-t21b/eval/realworld/harness/recall_header.sh || exit $?
export ACCEL_PROF_HOME=$A
for CH in ${RW_CUDA_HOME:-/usr/local/cuda-13.3} /usr/local/cuda-13.4 /usr/local/cuda; do [ -x $CH/bin/nvdisasm ] && { export CUDA_HOME=$CH; break; }; done
[ -n "$CUDA_HOME" ] || { echo "T21b analyze: host=$(hostname) no CUDA toolkit" >&2; exit 96; }
source $W/eval/baselines/gpu_env.sh
export LD_LIBRARY_PATH=/opt/ohpc/pub/compiler/gcc/12.4.0/lib64:${LD_LIBRARY_PATH:-}
cd $W || exit 1
ATO=${LONG_ATO:-84600}
case "$FLAVOR" in
  longcap-vc) M=vector-clock ;;
  longcap-sc) M=scalar-clock ;;
  *) echo "bad FLAVOR $FLAVOR" >&2; exit 2 ;;
esac
S=$S0/$FLAVOR; RES=$W/eval/results/realworld/$FLAVOR; CONF=$W/eval/baselines/confirm_realworld/$FLAVOR
export BASELINE_TRACE_DIR=$S BASELINE_MODES=$M
MANIFEST=$W/eval/realworld/manifest_t21b.csv; LOG=$W/eval/x_logs; mkdir -p $RES/attrib $CONF
echo "T21b analyze: host=$(hostname) job=${SLURM_JOB_ID:-none} flavor=$FLAVOR mode=$M analysis-timeout=$ATO date=$(date -Is)"
for id in ${IDS:-}; do
  [ -s "$S/$id/meta.json" ] || { echo "T21b analyze: $S/$id/meta.json unreadable on $(hostname)" >&2; exit 97; }
  echo "=== $(date -Is) analyze $id"
  $PY $W/eval/baselines/parallel.py analyze --manifest $MANIFEST --id $id --confirm --analysis-timeout $ATO --tag "$id-" \
      --results-dir $RES --confirm-dir $CONF > $LOG/analyze-$FLAVOR-$id.out 2>&1
  echo "  analyze rc=$? ($(tail -1 $LOG/analyze-$FLAVOR-$id.out | cut -c1-120))"
  if ! $PY -c "import csv,sys; sys.exit(0 if any(r['verdict'] in ('RACE','CLEAN') for r in csv.DictReader(open('$RES/baselines-cuvein-shard$id-all.csv'))) else 1)" 2>/dev/null; then echo "  no mode of $id ended RACE or CLEAN: attribution skipped (not scoreable)"; continue; fi
  $PY $W/eval/realworld/harness/rw_attribute.py --id $id --store $S --manifest $MANIFEST --out $RES/attrib/$id.json > $LOG/attrib-$FLAVOR-$id.out 2>&1
  echo "  attribute rc=$? ($(tail -1 $LOG/attrib-$FLAVOR-$id.out | cut -c1-200))"
done
echo "=== $(date -Is) analyze done"
