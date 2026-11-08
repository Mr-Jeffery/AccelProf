#!/usr/bin/env bash
# C6 step 3, stage 1: inputs and the sandbox tree for make_tables.py with a fourth cuVein column.
#   inputs/  = the paper's current state: cap-84600's merged CSVs (vector/scalar-clock, C1's collector-only with the atomicCAS
#              re-analysis, iGUARD, racecheck; eval/cap-84600 3de35b2) + the chain-closure rows as mode `collector-only-chain`.
#   sand-b/  = eval/results of the worktree (symlinks, but for the CSVs above) + eval/baselines + a COPY of make_tables.py that
#              gets C4's `--co-offline` patch with the names changed (mode collector-only-chain, flag --co-chain). The tracked
#              make_tables.py is not touched.
set -u
. /home/fzheng4/c6-step3/env.sh
I=$S3/inputs; R=$W/eval/results; N=$R/co-chain
mkdir -p $I
for f in baselines-cuvein.csv baselines-cuvein-co.csv baselines-iguard.csv baselines-sanitizer.csv; do
  git -C $W show eval/cap-84600:eval/results/cap-84600/$f > $I/$f || exit 1
done
git -C $W show eval/cap-84600:eval/results/cap-84600/tables/new/co/co_tables1.md > $I/cap_co_tables1.md
$PY - <<PYEOF
import csv
src = "$N/merged/baselines-cuvein.csv"
rows = list(csv.DictReader(open(src, newline="")))
flds = list(rows[0].keys())
with open("$I/baselines-cuvein-cc.csv", "w", newline="") as f:
    w = csv.DictWriter(f, flds); w.writeheader()
    for r in rows:
        r = dict(r); r["mode"] = "collector-only-chain" if r["mode"] == "collector-only" else r["mode"]
        if r["mode"] == "collector-only-chain": w.writerow(r)
print("cc rows", sum(1 for r in rows if r["mode"] == "collector-only"))
PYEOF
git -C $W diff eval/co-chain...eval/co-offline -- eval/baselines/make_tables.py \
  | sed 's/collector-only-rescored/collector-only-chain/g; s/CORS/CCHN/g; s/CO-R/CO-C/g; s/--co-offline/--co-chain/g' > $I/mt_chain.patch
d=$S3/sand-b; rm -rf $d; mkdir -p $d/eval/results $d/eval/baselines/setup
ln -s $W/python $d/python
for e in $R/*; do n=$(basename $e)
  case $n in baselines-cuvein.csv|baselines-diagnose.csv|baselines-disagreements.csv|baselines-fp-causes.csv|baselines-iguard.csv|baselines-sanitizer.csv|collector-only-tables|co-chain|cap-84600) continue;; esac
  case $n in baselines-*-shard*) continue;; esac
  ln -s $e $d/eval/results/$n
done
ln -s $I/baselines-cuvein.csv $d/eval/results/baselines-cuvein.csv
ln -s $I/baselines-cuvein-co.csv $d/eval/results/baselines-cuvein-co.csv
ln -s $I/baselines-cuvein-cc.csv $d/eval/results/baselines-cuvein-cc.csv
ln -s $I/baselines-iguard.csv $d/eval/results/baselines-iguard.csv
ln -s $I/baselines-sanitizer.csv $d/eval/results/baselines-sanitizer.csv
ln -s $R/final-b/merged/baselines-diagnose.csv $d/eval/results/baselines-diagnose.csv
ln -s $R/final-b/tables/baselines-disagreements.csv $d/eval/results/baselines-disagreements.csv
ln -s $R/final-b/tables/baselines-fp-causes.csv $d/eval/results/baselines-fp-causes.csv
for e in $W/eval/baselines/*; do n=$(basename $e)
  case $n in setup|make_tables.py) continue;; esac; ln -s $e $d/eval/baselines/$n; done
cp -p $W/eval/baselines/make_tables.py $d/eval/baselines/
for e in $W/eval/baselines/setup/*; do n=$(basename $e); ln -s $e $d/eval/baselines/setup/$n; done
(cd $d && git apply --check $I/mt_chain.patch && git apply $I/mt_chain.patch && echo "make_tables patch applied") || exit 2
echo "== make_tables.py --collector-only --co-chain"
(cd $d && $PY eval/baselines/make_tables.py --collector-only --co-chain) > $S3/make_tables_b.log 2>&1; echo "rc=$?"; tail -3 $S3/make_tables_b.log
mkdir -p $OUTD/mt
cp $d/eval/BASELINES_SUMMARY.md $OUTD/mt/BASELINES_SUMMARY_4col.md
ls -la $d/eval/*.md | head
