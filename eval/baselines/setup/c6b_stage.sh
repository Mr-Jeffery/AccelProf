#!/usr/bin/env bash
# C6b step 4, stage 1: inputs and the sandbox tree for the tables (as c6_stage.sh of C6, six cuVein columns).
#   inputs/  = vector-clock / scalar-clock (eval/cap-84600 baselines-cuvein.csv), C1 (baselines-cuvein-co.csv, mode collector-only),
#              iGUARD, racecheck (cap-84600), C6 (eval/co-chain merged CSV, mode renamed collector-only-chain),
#              S1 / S2 (eval/results/co-chain-b/merged-s{1,2}, mode renamed collector-only-s1 / collector-only-s2).
#   sand/    = eval/results of the worktree (symlinks, but for the CSVs above) + a COPY of the tracked make_tables.py (no patch).
set -u
. /home/fzheng4/c6b-step4/c6b_env.sh
I=$S4/inputs; R=$W/eval/results
mkdir -p $I
for f in baselines-cuvein.csv baselines-cuvein-co.csv baselines-iguard.csv baselines-sanitizer.csv; do
  git -C $W show eval/cap-84600:eval/results/cap-84600/$f > $I/$f || exit 1
done
git -C $W show eval/co-chain:eval/results/co-chain/merged/baselines-cuvein.csv > $I/c6_merged.csv || exit 1
$PY - <<PYEOF
import csv
def rows(p):
    return list(csv.DictReader(open(p, newline="")))
def put(rows, dst, newmode):
    flds = list(rows[0].keys()); n = 0
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, flds); w.writeheader()
        for r in rows:
            if r["mode"] == "collector-only":
                r = dict(r); r["mode"] = newmode; w.writerow(r); n += 1
    print(dst, n, "rows as", newmode)
put(rows("$I/c6_merged.csv"), "$I/baselines-cuvein-cc.csv", "collector-only-chain")
put(rows("$R/co-chain-b/merged-s1/baselines-cuvein.csv"), "$I/baselines-cuvein-s1.csv", "collector-only-s1")
put(rows("$R/co-chain-b/merged-s2/baselines-cuvein.csv"), "$I/baselines-cuvein-s2.csv", "collector-only-s2")
PYEOF
d=$S4/sand; rm -rf $d; mkdir -p $d/eval/results $d/eval/baselines/setup
ln -s $W/python $d/python
for e in $R/*; do n=$(basename $e)
  case $n in baselines-cuvein.csv|baselines-diagnose.csv|baselines-disagreements.csv|baselines-fp-causes.csv|baselines-iguard.csv|baselines-sanitizer.csv|collector-only-tables|co-chain|co-chain-b|cap-84600) continue;; esac
  case $n in baselines-*-shard*) continue;; esac
  ln -s $e $d/eval/results/$n
done
for n in baselines-cuvein baselines-cuvein-co baselines-cuvein-cc baselines-cuvein-s1 baselines-cuvein-s2 baselines-iguard baselines-sanitizer; do ln -s $I/$n.csv $d/eval/results/$n.csv; done
ln -s $R/final-b/merged/baselines-diagnose.csv $d/eval/results/baselines-diagnose.csv
ln -s $R/final-b/tables/baselines-disagreements.csv $d/eval/results/baselines-disagreements.csv
ln -s $R/final-b/tables/baselines-fp-causes.csv $d/eval/results/baselines-fp-causes.csv
for e in $W/eval/baselines/*; do n=$(basename $e)
  case $n in setup|make_tables.py) continue;; esac; ln -s $e $d/eval/baselines/$n; done
cp -p $W/eval/baselines/make_tables.py $d/eval/baselines/
for e in $W/eval/baselines/setup/*; do n=$(basename $e); ln -s $e $d/eval/baselines/setup/$n; done
echo "baselines csvs in the sandbox:"; ls $d/eval/results | grep '^baselines-' | tr '\n' ' '
echo; (cd $d && git -C $W diff --stat -- eval/baselines/make_tables.py | tail -1; cmp $W/eval/baselines/make_tables.py $d/eval/baselines/make_tables.py && echo "make_tables.py: tracked copy, unpatched")
