#!/bin/bash
# TOOLS_ON_STREAMK, S2 verdict layer only (re-run after job 340757's export lacked eval/aggregate.py): re-export
# f31a5067's python/, eval/baselines/ and eval/*.py read-only into $CB/tools_streamk/s2export, then per manifest id
# analyze the collector-only recording of 340757 with --confirm --chain-closure --co-async --co-r3 off. CPU, `normal`.
source /home/fzheng4/wt-x9/eval/cutlass/harness/x9_env.sh || exit $?
CAP=1200; D=$W/eval/cutlass/tools_streamk; M=$D/manifest.csv; T=$CB/tools_streamk; EXP=$T/s2export; R=$D/runs
RES=$W/eval/results/cutlass/tools_streamk
rm -rf $EXP && mkdir -p $EXP
git -C $W archive f31a5067 python eval/baselines $(git -C $W ls-tree --name-only f31a5067 eval/ | grep '\.py$') | tar -x -C $EXP
echo "export rc=$? $(du -sh $EXP | cut -f1) eval/*.py: $(ls $EXP/eval/*.py | wc -l)"
for id in $(tail -n +2 $M | cut -d, -f1); do
  s=$(date +%s.%N)
  BASELINE_TRACE_DIR=$T/traces/collector-only BASELINE_MODES=collector-only ACCEL_PROF_HOME=$EXP CUVEIN_HOME=$EXP \
    $PY $EXP/eval/baselines/parallel.py analyze --manifest $M --id $id --confirm \
    --chain-closure --co-async --co-r3 off --analysis-timeout $CAP --analysis-mem-gb 28 \
    --tag "$id-" --results-dir $RES/s2 --confirm-dir $D/confirm/s2 > $R/analyze-s2-$id.txt 2>&1
  rc=$?; w=$(awk -v a=$s -v b=$(date +%s.%N) 'BEGIN{printf "%.1f", b-a}')
  sed -i "/^$id\tanalyze S2\t/d" $R/times.tsv; echo -e "$id\tanalyze S2\t$rc\t$w" >> $R/times.tsv
  echo "$id analyze S2 rc=$rc ${w}s $(tail -1 $R/analyze-s2-$id.txt | cut -c1-200)"
done
