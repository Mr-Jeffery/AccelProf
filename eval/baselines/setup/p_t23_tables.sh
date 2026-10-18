#!/usr/bin/env bash
#SBATCH --job-name=t23-tables
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=2
#SBATCH --time=01:00:00
#SBATCH --exclude=c54,c2
#SBATCH --output=/home/fzheng4/wt-t23/eval/x_logs/t23-tables-%j.log
# T23 step 3 (eval/R3_CLOSURE.md): make_tables.py over X1's committed tree, once as merged and once
# with the T23-patched baselines-cuvein.csv, in a node-local export (nothing in any worktree is
# touched). The tables go to eval/results/t23/tables/.
#   AFTER_CSV=<path>   the patched eval/results/baselines-cuvein.csv   (required)
#   BRANCH=eval/final-sweep   whose committed tree is exported
W=${W:-/home/fzheng4/wt-t23}
BRANCH=${BRANCH:-eval/final-sweep}
: "${AFTER_CSV:?set AFTER_CSV=<patched baselines-cuvein.csv>}"
OUTD=$W/eval/results/t23/tables
mkdir -p "$OUTD"
T=$(mktemp -d /tmp/t23-tables-XXXXXX)
trap 'rm -rf "$T"' EXIT
echo "host=$(hostname) date=$(date -Is) branch=$BRANCH commit=$(git -C /home/fzheng4/AccelProf rev-parse "$BRANCH")"
git -C /home/fzheng4/AccelProf archive "$BRANCH" | tar -x -C "$T"
cd "$T" || exit 1
PY=/home/fzheng4/AccelProf/.env/bin/python
cp eval/BASELINES.md "$OUTD/BASELINES.committed.md"
cp eval/BASELINES_SUMMARY.md "$OUTD/BASELINES_SUMMARY.committed.md"
sha256sum eval/results/baselines-cuvein.csv "$AFTER_CSV"
$PY eval/baselines/make_tables.py > "$OUTD/make_tables.before.stdout" 2> "$OUTD/make_tables.before.stderr"
echo "make_tables (as merged) rc=$?"
cp eval/BASELINES.md "$OUTD/BASELINES.before.md"
cp eval/BASELINES_SUMMARY.md "$OUTD/BASELINES_SUMMARY.before.md"
cp "$AFTER_CSV" eval/results/baselines-cuvein.csv
$PY eval/baselines/make_tables.py > "$OUTD/make_tables.after.stdout" 2> "$OUTD/make_tables.after.stderr"
echo "make_tables (T23 rows) rc=$?"
cp eval/BASELINES.md "$OUTD/BASELINES.after.md"
cp eval/BASELINES_SUMMARY.md "$OUTD/BASELINES_SUMMARY.after.md"
cd "$OUTD" || exit 1
echo "== regenerated-as-merged vs the committed BASELINES.md:"; cmp BASELINES.committed.md BASELINES.before.md && echo identical
echo "== regenerated-as-merged vs the committed BASELINES_SUMMARY.md:"; cmp BASELINES_SUMMARY.committed.md BASELINES_SUMMARY.before.md && echo identical
diff -u BASELINES.before.md BASELINES.after.md > BASELINES.diff; echo "BASELINES.md diff lines: $(wc -l < BASELINES.diff)"
diff -u BASELINES_SUMMARY.before.md BASELINES_SUMMARY.after.md > BASELINES_SUMMARY.diff; echo "SUMMARY diff lines: $(wc -l < BASELINES_SUMMARY.diff)"
