#!/bin/bash
#SBATCH --job-name=x9-repro
#SBATCH --partition=rtx4060ti16g,rtx4060ti8g
#SBATCH --nodes=1 --ntasks=1 --exclusive
#SBATCH --time=0-06:00:00
#SBATCH --exclude=c[0-2],c[4-47],c54
#SBATCH --output=/home/fzheng4/wt-x9/eval/x_logs/x9-repro-%j.log
# X9 step 6: one finding's reproducer. FIND=<finding id> (eval/cutlass/findings/<id>/: build.sh, repro.cu, patches,
# manifest_repro.csv). Builds repro / repro_fixed / repro_perturb on the node (BeeGFS), native runs (REPS each),
# racecheck on repro, then per manifest row: collect (scalar-clock mode, X1b knobs, cap 1200 s) + analyze
# --both-barrier-orders --confirm + x9_pairs.py. Outputs: eval/cutlass/findings/<id>/runs/, results/pairs under repro/.
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
FIND=${FIND:?}; REPS=${REPS:-200}
D=$W/eval/cutlass/findings/$FIND; B=$CB/findings/$FIND/build; R=$D/runs; mkdir -p $B $R
IDX=$(nvidia-smi --query-gpu=index,compute_cap --format=csv,noheader | awk -F', *' '$2=="8.9"{print $1}' | head -1)
[ -n "$IDX" ] || { echo "X9: no sm_89 GPU on $(hostname)" >&2; exit 98; }
export CUDA_VISIBLE_DEVICES=$IDX
nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | tee $R/gpu.txt
echo "=== $(date -Is) build"; CUTLASS=$CB/src/cutlass-v4.8.1 NVCC=$CUDA_HOME/bin/nvcc bash $D/build.sh $B > $R/build.txt 2>&1; echo "  build rc=$?"; tail -4 $R/build.txt
for exe in repro repro_fixed repro_perturb; do
  echo "=== $(date -Is) native $exe $REPS"; s=$(date +%s)
  $B/$exe $REPS > $R/native_$exe.txt 2>&1; echo "  rc=$? wall=$(( $(date +%s) - s ))s $(tail -1 $R/native_$exe.txt)"
done
echo "=== $(date -Is) racecheck repro"
compute-sanitizer --tool racecheck --racecheck-report all --print-limit 10000 $B/repro 1 > $R/racecheck_repro.txt 2>&1; echo "# exit $?" >> $R/racecheck_repro.txt
echo "  $(tail -1 $R/racecheck_repro.txt) $(grep 'RACECHECK SUMMARY' $R/racecheck_repro.txt | tail -1)"
ST=$CB/traces/repro; M=$D/manifest_repro.csv; LOG=$W/eval/x_logs
RES=$W/eval/results/cutlass/repro; CONF=$W/eval/cutlass/confirm/repro; PAIRS=$W/eval/results/cutlass/pairs/repro; mkdir -p $ST $RES $CONF $PAIRS
export BASELINE_TRACE_DIR=$ST BASELINE_MODES=scalar-clock YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16 BASELINE_HB_DUMP=0
cd $W || exit 1
for id in $(tail -n +2 $M | cut -d, -f1); do
  echo "=== $(date -Is) collect $id"; s=$(date +%s)
  $PY $W/eval/cutlass/harness/x9_collect.py collect --manifest $M --id $id --reps 1 --timeout-floor 1200 --timeout-cap 1200 \
      --tag "repro-$id-" > $LOG/collect-repro-$id.out 2>&1
  echo "  collect rc=$? wall=$(( $(date +%s) - s ))s kernel JSONs: $(ls $ST/$id/scalar-clock 2>/dev/null | grep -c '^kernel_')"
  [ -f $W/eval/cutlass/harness/x9_prune_dots.py ] && $PY $W/eval/cutlass/harness/x9_prune_dots.py $ST/$id
  s=$(date +%s)
  $PY $W/eval/baselines/parallel.py analyze --manifest $M --id $id --confirm --both-barrier-orders \
      --analysis-timeout 14400 --analysis-mem-gb 28 --tag "$id-" --results-dir $RES --confirm-dir $CONF > $LOG/analyze-repro-$id.out 2>&1
  echo "  analyze rc=$? wall=$(( $(date +%s) - s ))s ($(tail -1 $LOG/analyze-repro-$id.out | cut -c1-200))"
  $PY $W/eval/cutlass/harness/x9_pairs.py --id $id --store $ST --manifest $M --out $PAIRS/$id.json > $LOG/pairs-repro-$id.out 2>&1
  echo "  pairs rc=$? ($(tail -1 $LOG/pairs-repro-$id.out | cut -c1-300))"
done
echo "=== $(date -Is) done"
