#!/bin/bash
#SBATCH --job-name=x9-tools-vc
#SBATCH --partition=rtx4060ti16g
#SBATCH --nodes=1 --ntasks=1 --exclusive
#SBATCH --time=0-03:00:00
#SBATCH --exclude=c0,c1,c2,c11,c12,c13,c14,c15,c18,c21,c22,c23,c34,c35,c36,c37,c46,c54
#SBATCH --output=/home/fzheng4/wt-x9/eval/x_logs/x9-tools-vc-%j.log
# X9 follow-up (TOOLS_ON_STREAMK, vector clock): vector-clock recording of the stream-K reproducer, the four variants of
# eval/cutlass/tools_streamk/manifest.csv ({repro, repro_fixed} x {split 2, split 3}), the binaries built by job 340757
# (sha256 checked against why/sha256.txt; no rebuild). Cap 1,200 s per run (collect and analyze).
# Recording: this checkout's harness, BASELINE_MODES=vector-clock, default dump (BASELINE_HB_DUMP unset = 1: hb_events kept).
# Scoring: parallel.py analyze --confirm (as the production-set rows).
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
CAP=1200
D=$W/eval/cutlass/tools_streamk; M=$D/manifest.csv; T=$CB/tools_streamk; B=$T/build; R=$D/runs; RES=$W/eval/results/cutlass/tools_streamk
mkdir -p $R $RES $T/traces $D/confirm
for exe in repro repro_fixed; do
  want=$(grep " \$CB/tools_streamk/build/$exe\$" $D/why/sha256.txt | cut -d' ' -f1); got=$(sha256sum $B/$exe | cut -d' ' -f1)
  echo "sha256 $exe $got want $want"; [ "$got" = "$want" ] || { echo "binary changed: $exe" >&2; exit 95; }
done
IDX=$(nvidia-smi --query-gpu=index,compute_cap --format=csv,noheader | awk -F', *' '$2=="8.9"{print $1}' | head -1)
[ -n "$IDX" ] || { echo "no sm_89 GPU on $(hostname)" >&2; exit 98; }
export CUDA_VISIBLE_DEVICES=$IDX
nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader | tee $R/gpu-vc.txt
t() { date +%s.%N; }; dt() { awk -v a=$1 -v b=$(t) 'BEGIN{printf "%.1f", b-a}'; }
TIMES=$R/times-vc.tsv; echo -e "id\tstep\trc\twall_s" > $TIMES
mode=vector-clock
for id in $(tail -n +2 $M | cut -d, -f1); do
  echo "=== $(date -Is) $id"
  export BASELINE_TRACE_DIR=$T/traces/$mode BASELINE_MODES=$mode
  s=$(t); $PY $W/eval/cutlass/harness/x9_collect.py collect --manifest $M --id $id --reps 1 --timeout-floor $CAP --timeout-cap $CAP \
      --tag "tools-$mode-$id-" > $R/collect-$mode-$id.txt 2>&1
  rc=$?; w=$(dt $s); echo -e "$id\tcollect $mode\t$rc\t$w" >> $TIMES
  echo "  collect rc=$rc ${w}s kernel JSONs: $(ls $BASELINE_TRACE_DIR/$id/$mode 2>/dev/null | grep -c '^kernel_')"
  s=$(t)
  $PY $W/eval/baselines/parallel.py analyze --manifest $M --id $id --confirm --analysis-timeout $CAP --analysis-mem-gb 28 \
      --tag "$id-" --results-dir $RES/$mode --confirm-dir $D/confirm/$mode > $R/analyze-$mode-$id.txt 2>&1
  rc=$?; w=$(dt $s); echo -e "$id\tanalyze $mode\t$rc\t$w" >> $TIMES
  echo "  analyze rc=$rc ${w}s ($(tail -1 $R/analyze-$mode-$id.txt | cut -c1-200))"
  cp $BASELINE_TRACE_DIR/$id/meta.json $R/meta-$mode-$id.json 2>/dev/null
  du -sh $BASELINE_TRACE_DIR/$id/$mode 2>/dev/null
  unset BASELINE_TRACE_DIR BASELINE_MODES
done
echo "=== $(date -Is) done"
