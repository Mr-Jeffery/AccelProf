#!/bin/bash
#SBATCH --job-name=x9-rec
#SBATCH --partition=rtx4060ti16g,rtx4060ti8g
#SBATCH --nodes=1 --ntasks=1 --exclusive
#SBATCH --time=1-00:00:00
#SBATCH --exclude=c0,c1,c2,c21,c22,c23,c34,c37,c46,c54
#SBATCH --output=/home/fzheng4/wt-x9/eval/x_logs/x9-rec-%j.log
# X9 step 3: scalar-clock recordings (collector run only; step 4 analyzes on `normal`) + racecheck, per manifest id.
#   IDS="a b" [FLAVOR=main|t5400|dump] [PHASES="rec racecheck"] sbatch eval/cutlass/harness/x9_record.sh
# FLAVOR main   X1b's knobs: BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16, cap 1200 s, store traces/main
# FLAVOR t5400  the same at a 5,400 s cap (the second pass for the timeouts), store traces/t5400
# FLAVOR dump   step 0c: the dump on (BASELINE_HB_DUMP=1, hb_events kept), store traces/dump
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
TIMEV="/usr/bin/time -v -o"; [ -x /usr/bin/time ] || TIMEV="$PY $W/eval/cutlass/harness/x9_timev.py -o"   # no GNU time on some nodes
FLAVOR=${FLAVOR:-main}
GPU=$(nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | tr '\n' ';')
IDX=$(nvidia-smi --query-gpu=index,compute_cap --format=csv,noheader | awk -F', *' '$2=="8.9"{print $1}')
IDX=$(echo "$IDX" | head -1)   # exclusive node; multi-GPU nodes (a5000ada): pin the first sm_89 GPU
[ -n "$IDX" ] || { echo "X9: no sm_89 GPU on $(hostname): $GPU" >&2; exit 98; }
export CUDA_VISIBLE_DEVICES=$IDX
NP=$(nproc); N=16
echo "X9 rec: flavor=$FLAVOR gpu=[$GPU] idx=$IDX nproc=$NP shards=$N cpu=[$(lscpu | sed -n 's/^Model name: *//p')] mem=$(free -g | awk '/Mem:/{print $2}')G"
TO=1200
case "$FLAVOR" in
  main)  ST=$CB/traces/main;  export BASELINE_HB_DUMP=0 ;;
  t5400) ST=$CB/traces/t5400; export BASELINE_HB_DUMP=0; TO=5400 ;;
  dump)  ST=$CB/traces/dump;  export BASELINE_HB_DUMP=1 ;;
  *) echo "bad FLAVOR $FLAVOR" >&2; exit 2 ;;
esac
# blib.collector_env drops inherited YOSEMITE_HB_SHARDS and sets it from BASELINE_HB_SHARDS (scalar-clock only)
export BASELINE_TRACE_DIR=$ST BASELINE_MODES=scalar-clock YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=$N
M=$W/eval/cutlass/manifest_cutlass.csv; LOG=$W/eval/x_logs; RC=$W/eval/cutlass/racecheck
mkdir -p $ST $LOG $RC
cd $W || exit 1
for id in ${IDS:-}; do
  if [[ " ${PHASES:-rec racecheck} " == *" rec "* ]]; then
    echo "=== $(date -Is) collect $id flavor=$FLAVOR"
    s=$(date +%s)
    $TIMEV $LOG/time-$FLAVOR-$id.txt $PY $W/eval/cutlass/harness/x9_collect.py collect --manifest $M --id $id --reps 1 \
        --timeout-floor $TO --timeout-cap $TO --tag "$FLAVOR-$id-" > $LOG/collect-$FLAVOR-$id.out 2>&1
    echo "  collect rc=$? wall=$(( $(date +%s) - s ))s maxrss_kb=$(awk -F': ' '/Maximum resident/{print $2}' $LOG/time-$FLAVOR-$id.txt) ($(tail -1 $LOG/collect-$FLAVOR-$id.out | cut -c1-160))"
    $PY $W/eval/cutlass/harness/x9_postmeta.py --meta $ST/$id/meta.json --flavor $FLAVOR --shards $N --nproc $NP \
        --libsanalyzer $X9_HS --collector $X9_HC --fatbin $X9_HF --fatbin-late $X9_HL --cuda-home $CUDA_HOME --gpu "$GPU" \
        --job "${SLURM_JOB_ID:-none}" --head "$(git -C $W rev-parse HEAD)" --timeout $TO 2>&1 | tail -2
    ls $ST/$id/scalar-clock 2>/dev/null | grep -c '^kernel_' | sed 's/^/  kernel JSONs: /'
    CP=$W/eval/x_logs/store_copy/$FLAVOR/$id; mkdir -p $CP; cp $ST/$id/meta.json $CP/ 2>/dev/null
    for f in $ST/$id/logs/*.txt; do tail -c 30000 "$f" > $CP/$(basename $f); done 2>/dev/null
  fi
  if [[ " ${PHASES:-rec racecheck} " == *" racecheck "* ]] && [ "$FLAVOR" = main ]; then
    exe=$($PY -c "import csv,sys; r=[r for r in csv.DictReader(open('$M')) if r['id']=='$id'][0]; print(r['exe']); print(r['args'])" | sed -n 1p)
    args=$($PY -c "import csv,sys; r=[r for r in csv.DictReader(open('$M')) if r['id']=='$id'][0]; print(r['args'])")
    echo "=== $(date -Is) racecheck $id: $exe $args"
    s=$(date +%s)
    ( cd $(dirname $exe) && timeout 21600 compute-sanitizer --tool racecheck --racecheck-report all --print-limit 10000 $exe $args > $RC/$id.txt 2>&1; echo "# exit $?" >> $RC/$id.txt )
    echo "  racecheck $(tail -1 $RC/$id.txt) wall=$(( $(date +%s) - s ))s $(grep -E 'RACECHECK SUMMARY' $RC/$id.txt | tail -1)"
  fi
done
echo "=== $(date -Is) done"
