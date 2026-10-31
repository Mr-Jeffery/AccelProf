#!/usr/bin/env bash
# C4 step 4 (CPU, run on a compute node: srun -p normal ... bash this): make_tables.py in sandbox trees (C3's method, p_co_tables.sh):
#   A: --collector-only                (C3's run: vector-clock, scalar-clock, C1's collector-only)
#   B: --collector-only --co-offline   (A plus the fourth column, CO-R, from merged/baselines-cuvein-cor.csv)
# then co_offline_strip_compare.py (B with every CO-R column, row and note segment removed, against A) and co_offline_tables.py.
set -u
W=/home/fzheng4/wt-c4; PY=/home/fzheng4/AccelProf/.env/bin/python; R=$W/eval/results
OUT=$R/co-offline/mt
mkdir -p $OUT
sandbox() {
  local d=$1 e n; rm -rf $d; mkdir -p $d/eval/results $d/eval/baselines/setup
  ln -s $W/python $d/python
  for e in $R/*; do n=$(basename $e)
    case $n in baselines-cuvein.csv|baselines-diagnose.csv|baselines-disagreements.csv|baselines-fp-causes.csv) continue;; esac
    ln -s $e $d/eval/results/$n; done
  ln -s $R/final-b/merged/baselines-cuvein.csv $d/eval/results/baselines-cuvein.csv
  ln -s $R/final-b/merged/baselines-diagnose.csv $d/eval/results/baselines-diagnose.csv
  ln -s $R/final-b/tables/baselines-disagreements.csv $d/eval/results/baselines-disagreements.csv
  ln -s $R/final-b/tables/baselines-fp-causes.csv $d/eval/results/baselines-fp-causes.csv
  ln -s $R/collector-only/merged/baselines-cuvein.csv $d/eval/results/baselines-cuvein-co.csv
  for e in $W/eval/baselines/*; do n=$(basename $e)
    case $n in setup|make_tables.py) continue;; esac; ln -s $e $d/eval/baselines/$n; done
  cp -p $W/eval/baselines/make_tables.py $d/eval/baselines/
  for e in $W/eval/baselines/setup/*; do n=$(basename $e)
    case $n in cuvein_rev.status|cuvein_rev) continue;; esac; ln -s $e $d/eval/baselines/setup/$n; done
  ln -s $W/eval/baselines/setup/cuvein_rev.status $d/eval/baselines/setup/cuvein_rev.status 2>/dev/null
}
S=/home/fzheng4/co-offline-sandbox
echo "host=$(hostname) $(date -Is) HEAD=$(git -C $W rev-parse --short HEAD)"
sandbox $S-a
(cd $S-a && $PY eval/baselines/make_tables.py --collector-only) && cp $S-a/eval/BASELINES.md $OUT/BASELINES_A.md && cp $S-a/eval/BASELINES_SUMMARY.md $OUT/BASELINES_SUMMARY_A.md
sandbox $S-b
ln -s $R/co-offline/merged/baselines-cuvein-cor.csv $S-b/eval/results/baselines-cuvein-cor.csv
(cd $S-b && $PY eval/baselines/make_tables.py --collector-only --co-offline) && cp $S-b/eval/BASELINES.md $OUT/BASELINES_B.md && cp $S-b/eval/BASELINES_SUMMARY.md $OUT/BASELINES_SUMMARY_B.md
cd $W
echo "== strip compare"
$PY eval/baselines/setup/co_offline/co_offline_strip_compare.py
echo "== tables"
COSB=$S-b $PY eval/baselines/setup/co_offline/co_offline_tables.py > $R/co-offline/tables_stdout.md
echo "== done"
