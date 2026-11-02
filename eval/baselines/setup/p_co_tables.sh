#!/usr/bin/env bash
#SBATCH --job-name=co-tables
#SBATCH --partition=normal
#SBATCH --exclude=c0,c1,c23,c46
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=02:00:00
#SBATCH --output=/home/fzheng4/wt-co-tables/eval/x_logs/co-tables-%j.log
# C3 step 2: make_tables.py with and without --collector-only, in sandbox trees (the X1b method,
# p_final_b_tables.sh): eval/results = symlinks to the worktree's, with baselines-cuvein.csv = X1b's merged
# file and fp-causes / disagreements / diagnose = X1b's. A: no flag (must equal final-b/tables/BASELINES.md
# but for the disagreements listing). B: --collector-only with C1's merged rows added.
set -u
W=/home/fzheng4/wt-co-tables; PY=/home/fzheng4/AccelProf/.env/bin/python; R=$W/eval/results
OUT=$R/collector-only-tables/mt
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
  for e in $W/eval/baselines/*; do n=$(basename $e)
    case $n in setup|make_tables.py) continue;; esac; ln -s $e $d/eval/baselines/$n; done
  cp -p $W/eval/baselines/make_tables.py $d/eval/baselines/
  for e in $W/eval/baselines/setup/*; do n=$(basename $e)
    case $n in cuvein_rev.status|cuvein_rev) continue;; esac; ln -s $e $d/eval/baselines/setup/$n; done
  ln -s $W/eval/baselines/setup/cuvein_rev.status $d/eval/baselines/setup/cuvein_rev.status 2>/dev/null
}
S=/home/fzheng4/co-tables-sandbox
echo "host=$(hostname) $(date -Is) HEAD=$(git -C $W rev-parse --short HEAD)"
sandbox $S-a
(cd $S-a && $PY eval/baselines/make_tables.py) && cp $S-a/eval/BASELINES.md $OUT/BASELINES_A.md && cp $S-a/eval/BASELINES_SUMMARY.md $OUT/BASELINES_SUMMARY_A.md
sandbox $S-b
ln -s $R/collector-only/merged/baselines-cuvein.csv $S-b/eval/results/baselines-cuvein-co.csv
(cd $S-b && $PY eval/baselines/make_tables.py --collector-only) && cp $S-b/eval/BASELINES.md $OUT/BASELINES_B.md && cp $S-b/eval/BASELINES_SUMMARY.md $OUT/BASELINES_SUMMARY_B.md
cmp $OUT/BASELINES_SUMMARY_A.md $R/final-b/tables/BASELINES_SUMMARY.md && echo "A summary == X1b summary"
diff <(grep -v '^| .* | .* | .* | .* | .* | .* | .* | .* | .* |$' $OUT/BASELINES_A.md | head -c 100000000) <(grep -v '^| .* | .* | .* | .* | .* | .* | .* | .* | .* |$' $R/final-b/tables/BASELINES.md) | head -20
diff <(sed -n '1,5600p' $OUT/BASELINES_A.md) <(sed -n '1,5600p' $R/final-b/tables/BASELINES.md) | head -20
echo "== done"
