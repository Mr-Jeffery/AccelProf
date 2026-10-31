#!/bin/bash
# X7 Part B4: sandboxes (old = X1b/C1/branch CSVs + the iGUARD P7 job-321654 rows; new = eval/results/cap-84600), make_tables.py --collector-only,
# co_tables1.py (cuVein columns of Table 4, countings, fig 6, memory), cap_cells.py (cells of every tool).
set -u
W=/home/fzheng4/wt-x7b; PY=/home/fzheng4/AccelProf/.env/bin/python; R=$W/eval/results; N=$R/cap-84600
cd $W
sandbox() { # dir cuvein.csv co.csv iguard.csv sanitizer.csv
  local d=$1 e n; rm -rf $d; mkdir -p $d/eval/results $d/eval/baselines/setup
  ln -s $W/python $d/python
  for e in $R/*; do n=$(basename $e)
    case $n in baselines-cuvein.csv|baselines-diagnose.csv|baselines-disagreements.csv|baselines-fp-causes.csv|baselines-iguard.csv|baselines-sanitizer.csv|collector-only-tables|cap-84600) continue;; esac
    case $n in baselines-*-shard*) continue;; esac
    ln -s $e $d/eval/results/$n; done
  ln -s $2 $d/eval/results/baselines-cuvein.csv
  ln -s $3 $d/eval/results/baselines-cuvein-co.csv
  ln -s $4 $d/eval/results/baselines-iguard.csv
  ln -s $5 $d/eval/results/baselines-sanitizer.csv
  ln -s $R/final-b/merged/baselines-diagnose.csv $d/eval/results/baselines-diagnose.csv
  ln -s $R/final-b/tables/baselines-disagreements.csv $d/eval/results/baselines-disagreements.csv
  ln -s $R/final-b/tables/baselines-fp-causes.csv $d/eval/results/baselines-fp-causes.csv
  for e in $W/eval/baselines/*; do n=$(basename $e)
    case $n in setup|make_tables.py) continue;; esac; ln -s $e $d/eval/baselines/$n; done
  cp -p $W/eval/baselines/make_tables.py $d/eval/baselines/
  for e in $W/eval/baselines/setup/*; do n=$(basename $e); ln -s $e $d/eval/baselines/setup/$n; done
}
mkdir -p $N/tables/old $N/tables/new
S=/home/fzheng4/x7b-sandbox
sandbox $S-old $R/final-b/merged/baselines-cuvein.csv $R/collector-only/merged/baselines-cuvein.csv $N/old-inputs/baselines-iguard.csv $R/baselines-sanitizer.csv
sandbox $S-new $N/baselines-cuvein.csv $N/baselines-cuvein-co.csv $N/baselines-iguard.csv $N/baselines-sanitizer.csv
for v in old new; do
  d=$S-$v
  (cd $d && $PY eval/baselines/make_tables.py --collector-only > $N/tables/$v/make_tables.log 2>&1; cp eval/BASELINES.md $N/tables/$v/BASELINES.md; cp eval/BASELINES_SUMMARY.md $N/tables/$v/BASELINES_SUMMARY.md)
  (cd $d && sed 's/LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN"}/LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN", "P9-atomicCAS-cuda": "CLEAN"}/' $W/eval/baselines/setup/co_tables/co_tables1.py > $d/co_tables1_cap.py; COSB=$d $PY $d/co_tables1_cap.py > $N/tables/$v/co_tables1.log 2>&1; mkdir -p $N/tables/$v/co; cp eval/results/collector-only-tables/*.csv eval/results/collector-only-tables/co_tables1.md $N/tables/$v/co/)
  if [ $v = new ]; then export CAP_OVERRIDE_NATIVE=1 CAP_OLD_JSON=$N/tables/old/cells.json; else unset CAP_OVERRIDE_NATIVE; fi
  $PY $W/eval/baselines/setup/cap_cells.py $d $N/tables/$v/cells.json $N/newkeys.json
done
echo done
