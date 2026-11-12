#!/bin/bash
#SBATCH --job-name=x9-tools
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1 --exclusive
#SBATCH --time=0-06:00:00
#SBATCH --exclude=c2,c21,c37,c54
#SBATCH --output=/home/fzheng4/wt-x9/eval/x_logs/x9-tools-%j.log
# X9 follow-up (TOOLS_ON_STREAMK): four tools on the stream-K reproducer (findings/streamk-wait-eq-reset), four variants
# = {repro, repro_fixed} x {split 2, split 3} (manifest eval/cutlass/tools_streamk/manifest.csv). Cap 1,200 s per run.
#   1. racecheck   compute-sanitizer --tool racecheck --racecheck-report all
#   2. iGUARD      eval/baselines/run_iguard.py (the runner of every iGUARD row; LD_PRELOAD iguard.so, TIMEOUT=0,
#                  per-rep timeout min(max(10 x native,120),1200), 3 reps), install /home/fzheng4/AccelProf/eval/baselines/setup/iguard/iguard.so
#   3. cuRace S2   collector-only recording (this checkout's harness, BASELINE_MODES=collector-only), verdict layer from a
#                  read-only `git archive f31a5067 python eval/baselines` export (S2 is not in this checkout):
#                  parallel.py analyze --confirm --chain-closure --co-async --co-r3 off
#   4. cuRace + scalar clock: scalar-clock recording (X1b knobs, as X9), parallel.py analyze --confirm
# Outputs: eval/cutlass/tools_streamk/runs/, eval/results/cutlass/tools_streamk/, BeeGFS $CB/tools_streamk/.
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
CAP=1200
D=$W/eval/cutlass/tools_streamk; F=$W/eval/cutlass/findings/streamk-wait-eq-reset; M=$D/manifest.csv
T=$CB/tools_streamk; B=$T/build; EXP=$T/s2export; R=$D/runs; RES=$W/eval/results/cutlass/tools_streamk
mkdir -p $B $R $RES $T/traces $T/iguard_logs $D/confirm
IDX=$(nvidia-smi --query-gpu=index,compute_cap --format=csv,noheader | awk -F', *' '$2=="8.9"{print $1}' | head -1)
[ -n "$IDX" ] || { echo "no sm_89 GPU on $(hostname)" >&2; exit 98; }
export CUDA_VISIBLE_DEVICES=$IDX
nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | tee $R/gpu.txt
t() { date +%s.%N; }; dt() { awk -v a=$1 -v b=$(t) 'BEGIN{printf "%.1f", b-a}'; }

echo "=== $(date -Is) build"
CUTLASS=$CB/src/cutlass-v4.8.1 NVCC=$CUDA_HOME/bin/nvcc bash $F/build.sh $B > $R/build.txt 2>&1; echo "  build rc=$?"; tail -3 $R/build.txt
for exe in repro repro_fixed; do        # line info of every cubin in the executable (pc -> file:line, inlined frames)
  x=$(mktemp -d); (cd $x && cuobjdump -xelf all $B/$exe > /dev/null)
  for c in $x/*.cubin; do echo "## $(basename $c)"; nvdisasm -c --print-line-info-inline $c; done > $R/$exe.lineinfo.txt; rm -rf $x
done
echo "=== $(date -Is) export S2 verdict layer"
rm -rf $EXP && mkdir -p $EXP && git -C $W archive f31a5067 python eval/baselines | tar -x -C $EXP; echo "  export rc=$? $(du -sh $EXP | cut -f1)"

TIMES=$R/times.tsv; echo -e "id\tstep\trc\twall_s" > $TIMES
for id in $(tail -n +2 $M | cut -d, -f1); do
  row=$(grep "^$id," $M); exe=$(echo "$row" | cut -d, -f6); args=$(echo "$row" | cut -d, -f7)
  echo "=== $(date -Is) $id: $exe $args"
  s=$(t); timeout $CAP $exe $args > $R/native-$id.txt 2>&1; rc=$?; w=$(dt $s); echo -e "$id\tnative\t$rc\t$w" >> $TIMES; echo "  native rc=$rc ${w}s $(tail -1 $R/native-$id.txt)"
  s=$(t); timeout $CAP compute-sanitizer --tool racecheck --racecheck-report all --print-limit 10000 $exe $args > $R/racecheck-$id.txt 2>&1
  rc=$?; w=$(dt $s); echo -e "$id\tracecheck\t$rc\t$w" >> $TIMES; echo "  racecheck rc=$rc ${w}s $(grep 'RACECHECK SUMMARY' $R/racecheck-$id.txt | tail -1)"
  s=$(t); BASELINE_TRACE_DIR=$T/iguard_logs IGUARD_SO=$A/eval/baselines/setup/iguard/iguard.so \
    $PY $W/eval/baselines/run_iguard.py --manifest $M --id $id --out $RES/iguard-$id.csv > $R/iguard-run-$id.txt 2>&1
  rc=$?; w=$(dt $s); echo -e "$id\tiguard(3 reps)\t$rc\t$w" >> $TIMES; cp $T/iguard_logs/$id/*.txt $R/ 2>/dev/null
  for f in $T/iguard_logs/$id/iguard_rep*.txt; do mv $R/$(basename $f) $R/iguard-$id-$(basename $f) 2>/dev/null; done
  mv $R/native.txt $R/iguard-$id-native.txt 2>/dev/null
  echo "  iguard rc=$rc ${w}s $(tail -n +2 $RES/iguard-$id.csv | cut -d, -f1,8,9,10 | tr '\n' ' ' | cut -c1-300)"
  for mode in scalar-clock collector-only; do
    export BASELINE_TRACE_DIR=$T/traces/$mode BASELINE_MODES=$mode
    if [ $mode = scalar-clock ]; then export YOSEMITE_HB_STATS=1 BASELINE_HB_SHARDS=16 BASELINE_HB_DUMP=0; else unset YOSEMITE_HB_STATS BASELINE_HB_SHARDS BASELINE_HB_DUMP; fi
    s=$(t); $PY $W/eval/cutlass/harness/x9_collect.py collect --manifest $M --id $id --reps 1 --timeout-floor $CAP --timeout-cap $CAP \
        --tag "tools-$mode-$id-" > $R/collect-$mode-$id.txt 2>&1
    rc=$?; w=$(dt $s); echo -e "$id\tcollect $mode\t$rc\t$w" >> $TIMES
    echo "  collect $mode rc=$rc ${w}s kernel JSONs: $(ls $BASELINE_TRACE_DIR/$id/$mode 2>/dev/null | grep -c '^kernel_')"
    s=$(t)
    if [ $mode = scalar-clock ]; then
      $PY $W/eval/baselines/parallel.py analyze --manifest $M --id $id --confirm --analysis-timeout $CAP --analysis-mem-gb 28 \
        --tag "$id-" --results-dir $RES/scalar-clock --confirm-dir $D/confirm/scalar-clock > $R/analyze-$mode-$id.txt 2>&1
    else
      ACCEL_PROF_HOME=$EXP CUVEIN_HOME=$EXP $PY $EXP/eval/baselines/parallel.py analyze --manifest $M --id $id --confirm \
        --chain-closure --co-async --co-r3 off --analysis-timeout $CAP --analysis-mem-gb 28 \
        --tag "$id-" --results-dir $RES/s2 --confirm-dir $D/confirm/s2 > $R/analyze-s2-$id.txt 2>&1
    fi
    rc=$?; w=$(dt $s); echo -e "$id\tanalyze $([ $mode = scalar-clock ] && echo scalar-clock || echo S2)\t$rc\t$w" >> $TIMES
    echo "  analyze $mode rc=$rc ${w}s ($(tail -1 $R/analyze-*$([ $mode = scalar-clock ] && echo scalar-clock || echo s2)-$id.txt | cut -c1-200))"
    cp $BASELINE_TRACE_DIR/$id/meta.json $R/meta-$mode-$id.json 2>/dev/null
  done
  unset BASELINE_TRACE_DIR BASELINE_MODES YOSEMITE_HB_STATS BASELINE_HB_SHARDS BASELINE_HB_DUMP
done
echo "=== $(date -Is) done"
