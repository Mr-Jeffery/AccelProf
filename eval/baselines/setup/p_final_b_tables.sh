#!/usr/bin/env bash
#SBATCH --job-name=x1b-tables
#SBATCH --partition=normal
#SBATCH --exclude=c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/finalb-tables-%j.log
# X1b's paper tables (Jeffery, 10-24): X1's table steps (p_final_post.sh: classify_endpoints.py,
# classify_fp_causes.py, the revision pin, make_tables.py) on X1b's merged results, every output in
# eval/results/final-b/tables/. The three scripts locate every input and output from their own file
# (HERE = their directory, APH = two levels up), so copies of them run inside a sandbox tree: its
# eval/results holds X1b's merged cuVein and diagnose CSVs plus symlinks to every other entry of the
# worktree's eval/results (the other tools' CSVs, read only); the four cuVein-derived files are written
# fresh inside the sandbox and copied out. A second sandbox runs the same steps on X1's own inputs and
# compares the result with X1's committed files (method check). X1's files are only read.
#   sbatch eval/baselines/setup/p_final_b_tables.sh
set -u
W=/home/fzheng4/wt-x1b
RT=/home/fzheng4/AccelProf
B=/mnt/beegfs/$USER/cuvein_traces
PY=$RT/.env/bin/python
R=$W/eval/results
OUTD=$R/final-b/tables
SBB=/home/fzheng4/x1b/tables_sandbox_b
SB1=/home/fzheng4/x1b/tables_sandbox_x1
VIEWB=$B/final-2026-11-view
CONFB=/home/fzheng4/x1b/confirm_final-b-merged
echo "host=$(hostname) W=$W HEAD=$(git -C $W rev-parse --short=12 HEAD) dirty=$(git -C $W status --porcelain -uno | wc -l) $(date -Is)"
[ -d $B/final-2026-11 ] || { echo "BeeGFS not readable on $(hostname)"; exit 2; }
others() { (cd $W && ls eval/results/baselines-*.csv | /usr/bin/grep -v "baselines-cuvein\|baselines-diagnose\|baselines-disagreements\|baselines-fp-causes" | sort | xargs sha256sum); }
TMPS=$(mktemp -d)
others > $TMPS/before.sha256

# sandbox <dir> <cuvein.csv> <diagnose.csv>
sandbox() {
  local d=$1 e n
  rm -rf $d; mkdir -p $d/eval/results $d/eval/baselines/setup
  ln -s $W/python $d/python
  for e in $R/*; do n=$(basename $e)
    case $n in baselines-cuvein.csv|baselines-diagnose.csv|baselines-disagreements.csv|baselines-fp-causes.csv) continue;; esac
    ln -s $e $d/eval/results/$n; done
  ln -s $2 $d/eval/results/baselines-cuvein.csv
  ln -s $3 $d/eval/results/baselines-diagnose.csv
  for e in $W/eval/baselines/*; do n=$(basename $e)
    case $n in setup|classify_endpoints.py|classify_fp_causes.py|make_tables.py) continue;; esac
    ln -s $e $d/eval/baselines/$n; done
  cp -p $W/eval/baselines/classify_endpoints.py $W/eval/baselines/classify_fp_causes.py $W/eval/baselines/make_tables.py $d/eval/baselines/
  for e in $W/eval/baselines/setup/*; do n=$(basename $e)
    case $n in cuvein_rev.status|cuvein_rev) continue;; esac
    ln -s $e $d/eval/baselines/setup/$n; done
}

echo "== X1b: sandbox $SBB"
sandbox $SBB $R/final-b/merged/baselines-cuvein.csv $R/final-b/merged/baselines-diagnose.csv
cat $W/eval/baselines/setup/final_b_long_vc_ids_s.txt $W/eval/baselines/setup/final_b_long_vc_ids_b.txt > $SBB/long_vc_ids.txt
echo "== X1b trace view for classify_fp_causes ($VIEWB; long ids: that mode from its long store), X1's code"
$PY - "$B/final-2026-11" "$B/final-2026-11-long" "$B/final-2026-11-long-sc" "$VIEWB" $SBB/long_vc_ids.txt $W/eval/baselines/setup/final_b_long_sc_ids_1.txt \
    "$B/final-2026-11-24h-vc" "$B/final-2026-11-24h-sc" $R/final-b-24h-kept-vc/baselines-cuvein-shard24h-kept-vc.csv \
    $R/final-b-24h-kept-sc/baselines-cuvein-shard24h-kept-sc.csv <<'PYEOF'
import os, sys, glob, shutil, csv
main, lvc, lsc, view, idf, idfs, hvc, hsc, kvc, ksc = sys.argv[1:]
rd = lambda f: set(l.strip() for l in open(f) if l.strip()) if os.path.exists(f) else set()
kept = lambda f: {r["id"] for r in csv.DictReader(open(f, newline=""))} if os.path.exists(f) else set()
longs = {"vector-clock": (lvc, rd(idf)), "scalar-clock": (lsc, rd(idfs))}
h24 = {"vector-clock": (hvc, kept(kvc)), "scalar-clock": (hsc, kept(ksc))}
shutil.rmtree(view, ignore_errors=True); os.makedirs(view)
n = 0
for idir in glob.glob(f"{main}/*/meta.json"):
    i = os.path.basename(os.path.dirname(idir)); src = os.path.dirname(idir)
    os.makedirs(f"{view}/{i}")
    for sub in ("dots", "meta.json", "scalar-clock", "vector-clock"):
        st, ids = longs.get(sub, ("", set()))
        hs, hids = h24.get(sub, ("", set()))
        s = f"{hs}/{i}/{sub}" if i in hids else (f"{st}/{i}/{sub}" if i in ids else f"{src}/{sub}")
        if os.path.exists(s):
            os.symlink(s, f"{view}/{i}/{sub}")
    n += 1
print(f"view: {n} ids; from the 5,400 s stores: " + ", ".join(f"{m} {len(v[1])}" for m, v in longs.items())
      + "; from the 24 h stores: " + ", ".join(f"{m} {len(v[1])}" for m, v in h24.items()))
PYEOF
export ACCEL_PROF_HOME=$SBB; cd $SBB
echo "== X1b classify_endpoints"; $PY $SBB/eval/baselines/classify_endpoints.py --confirm $CONFB; echo "classify_endpoints rc=$?"
echo "== X1b classify_fp_causes"; $PY $SBB/eval/baselines/classify_fp_causes.py --confirm $CONFB --traces $VIEWB; echo "classify_fp_causes rc=$?"
echo "== X1b revision pin (label final-2026-11) -> $OUTD"
mkdir -p $OUTD
CUVEIN_REV_OUT=$OUTD bash $W/eval/baselines/setup/cuvein_rev.sh final-2026-11 | tail -12; echo "cuvein_rev rc=${PIPESTATUS[0]}"
ln -s $OUTD/cuvein_rev.status $SBB/eval/baselines/setup/cuvein_rev.status
echo "== X1b make_tables"; $PY $SBB/eval/baselines/make_tables.py; echo "make_tables rc=$?"
for f in $SBB/eval/BASELINES.md $SBB/eval/BASELINES_SUMMARY.md $SBB/eval/results/baselines-disagreements.csv $SBB/eval/results/baselines-fp-causes.csv; do
  [ -L $f ] && { echo "UNEXPECTED SYMLINK $f"; exit 4; }; cp -p $f $OUTD/; done
ls -la $OUTD $OUTD/cuvein_rev

echo "== X1 method check: sandbox $SB1 with X1's own inputs"
sandbox $SB1 $R/baselines-cuvein.csv $R/baselines-diagnose.csv
ln -s $W/eval/baselines/setup/cuvein_rev.status $SB1/eval/baselines/setup/cuvein_rev.status
export ACCEL_PROF_HOME=$SB1; cd $SB1
if [ -d $RT/eval/baselines/confirm_final ] && [ -d $B/final-2026-10-view ]; then
  $PY $SB1/eval/baselines/classify_endpoints.py --confirm $RT/eval/baselines/confirm_final > /dev/null; echo "X1 classify_endpoints rc=$?"
  $PY $SB1/eval/baselines/classify_fp_causes.py --confirm $RT/eval/baselines/confirm_final --traces $B/final-2026-10-view > /dev/null; echo "X1 classify_fp_causes rc=$?"
else
  echo "X1's confirm dir or trace view missing: X1's committed disagreements / fp-causes CSVs copied in"
  cp -p $R/baselines-disagreements.csv $R/baselines-fp-causes.csv $SB1/eval/results/
fi
$PY $SB1/eval/baselines/make_tables.py > /dev/null; echo "X1 make_tables rc=$?"
for f in results/baselines-disagreements.csv results/baselines-fp-causes.csv BASELINES.md BASELINES_SUMMARY.md; do
  if cmp -s $SB1/eval/$f $W/eval/$f; then echo "X1 $f: reproduced byte for byte"
  else echo "X1 $f: DIFFERS from the committed file"; diff $SB1/eval/$f $W/eval/$f | head -30; fi
done

echo "== X1's files and the other tools"
others > $TMPS/after.sha256
cmp -s $TMPS/before.sha256 $TMPS/after.sha256 && echo "other tools' CSVs: before == after ($(wc -l < $TMPS/after.sha256) files)" || echo "OTHER TOOLS' CSVs CHANGED"
cmp -s $TMPS/after.sha256 $R/final-b/merged/other_tools.sha256.after && echo "equal to final-b/merged/other_tools.sha256.after" || echo "DIFFERENT from final-b/merged/other_tools.sha256.after"
rm -rf $TMPS
echo "tracked X1 files changed: $(git -C $W status --porcelain -uno -- eval/results eval/BASELINES.md eval/BASELINES_SUMMARY.md eval/baselines/setup/cuvein_rev.status eval/baselines/setup/cuvein_rev | wc -l)"
git -C $W status --porcelain -- eval/results eval/BASELINES.md eval/BASELINES_SUMMARY.md eval/baselines/setup | head
echo "== done $(date -Is)"
