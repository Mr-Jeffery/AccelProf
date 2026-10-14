#!/usr/bin/env bash
#SBATCH --job-name=x1-post
#SBATCH --partition=normal
#SBATCH --exclude=c54,c2
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=06:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/final-post-%j.log
# X1 steps 3-5 (eval/FINAL_SWEEP.md), CPU only, on a compute node (the stores are on BeeGFS):
# merge the cuVein shards of the final recording (eval/results/final/, the 5,400 s passes'
# eval/results/final-long/ (vector-clock) and final-long-sc/ (scalar-clock) as --override) into eval/results/baselines-cuvein.csv -- the previous
# file kept once as superseded_baselines-cuvein-2026-09-22.csv; ONLY cuvein is merged (p_final2.sh
# also re-merges sanitizer/iguard/supercollider/hirace from their shards: not re-run here, and their
# CSVs must not change -- sha256 before and after) -- then p_final2.sh's post-processing with the
# final recording's own inputs, the revision pin, make_tables.py and the sanity checks.
#   sbatch eval/baselines/setup/p_final_post.sh
set -u
W=${W:-/home/fzheng4/AccelProf/.claude/worktrees/wt-x1}
RT=/home/fzheng4/AccelProf
B=/mnt/beegfs/$USER/cuvein_traces
MAIN=$B/final-2026-10; LONG=$B/final-2026-10-long; LONGSC=$B/final-2026-10-long-sc; VIEW=$B/final-2026-10-view
CONF=$RT/eval/baselines/confirm_final
cd $W || exit 1
export ACCEL_PROF_HOME=$W
PY=$RT/.env/bin/python
R=eval/results
echo "host=$(hostname) W=$W HEAD=$(git rev-parse --short=12 HEAD) $(date -Is)"
# the other tools' result CSVs (and the static inputs next to them); the cuVein-derived analysis
# CSVs (diagnose, disagreements, fp-causes) are regenerated below by design
others() { ls $R/baselines-*.csv | /usr/bin/grep -v "baselines-cuvein\|baselines-diagnose\|baselines-disagreements\|baselines-fp-causes" \
             | sort | xargs sha256sum; }
others > $R/final/other_tools.sha256.before
echo "== merge"
[ -e $R/superseded_baselines-cuvein-2026-09-22.csv ] || cp -p $R/baselines-cuvein.csv $R/superseded_baselines-cuvein-2026-09-22.csv
# the 5,400 s passes: vector-clock (final-long) and scalar-clock (final-long-sc, added 2026-10-14)
OVS=""; for d in final-long final-long-sc; do ls $R/$d/baselines-cuvein-shard*.csv > /dev/null 2>&1 && OVS="$OVS${OVS:+,}$W/$R/$d"; done
$PY eval/baselines/parallel.py merge --tool cuvein --results-dir $W/$R/final --out-dir $W/$R ${OVS:+--override $OVS}
echo "== confirmation details: the long passes' files replace the first pass's (kept under pass1/)"
mkdir -p $CONF/pass1
for mode in vector-clock scalar-clock; do
  if [ $mode = vector-clock ]; then CONFL=$RT/eval/baselines/confirm_final-long; IDF=eval/baselines/setup/final_long_ids.txt
  else CONFL=$RT/eval/baselines/confirm_final-long-sc; IDF=eval/baselines/setup/final_long_sc_ids.txt; fi
  [ -e $IDF ] || continue
  # every long id's first-pass file (if any: a rep that finished under 1,200 s) no longer matches the
  # merged rows -> pass1/; the long pass's file (if it analysed a dump) takes its place
  for i in $(cat $IDF); do
    b="${i}__cuvein__${mode}.json"
    [ -e $CONF/$b ] && [ ! -e $CONF/pass1/$b ] && mv $CONF/$b $CONF/pass1/$b
    [ -e $CONFL/$b ] && cp -p $CONFL/$b $CONF/$b
  done
done
echo "== trace view for classify_fp_causes (long ids: that mode from its long store)"
$PY - "$MAIN" "$LONG" "$LONGSC" "$VIEW" eval/baselines/setup/final_long_ids.txt eval/baselines/setup/final_long_sc_ids.txt <<'EOF'
import os, sys, glob, shutil
main, lvc, lsc, view, idf, idfs = sys.argv[1:]
rd = lambda f: set(l.strip() for l in open(f) if l.strip()) if os.path.exists(f) else set()
longs = {"vector-clock": (lvc, rd(idf)), "scalar-clock": (lsc, rd(idfs))}
shutil.rmtree(view, ignore_errors=True); os.makedirs(view)
n = 0
for idir in glob.glob(f"{main}/*/meta.json"):
    i = os.path.basename(os.path.dirname(idir)); src = os.path.dirname(idir)
    os.makedirs(f"{view}/{i}")
    for sub in ("dots", "meta.json", "scalar-clock", "vector-clock"):
        st, ids = longs.get(sub, ("", set()))
        s = f"{st}/{i}/{sub}" if i in ids else f"{src}/{sub}"
        if os.path.exists(s):
            os.symlink(s, f"{view}/{i}/{sub}")
    n += 1
print(f"view: {n} ids; from the long stores: " + ", ".join(f"{m} {len(v[1])}" for m, v in longs.items()))
EOF
echo "== residual ids (collapsed ERROR/TIMEOUT in some mode)"
$PY - $R/baselines-cuvein.csv > eval/baselines/setup/final_residual_ids.txt <<'EOF'
import csv, sys, collections
per = collections.defaultdict(set)
for r in csv.DictReader(open(sys.argv[1], newline="")):
    per[(r["id"], r["mode"])].add(r["verdict"])
bad = sorted({i for (i, m), v in per.items() if not v & {"RACE", "CLEAN"}})
print("\n".join(bad))
EOF
wc -l < eval/baselines/setup/final_residual_ids.txt
$PY eval/baselines/classify_residuals.py --no-dump --ids eval/baselines/setup/final_residual_ids.txt \
    --diag $W/$R/baselines-cuvein.csv --base "" \
    --logs "$RT/eval/baselines/setup/build_logs/final-[0-9]*.log,$RT/eval/baselines/setup/build_logs/finalpi-*.log,$RT/eval/baselines/setup/build_logs/final-long-*.log"
$PY eval/baselines/classify_endpoints.py --confirm $CONF
$PY eval/baselines/classify_fp_causes.py --confirm $CONF --traces $VIEW
echo "== revision pin"
CUVEIN_REV_OUT=$W/eval/baselines/setup bash eval/baselines/setup/cuvein_rev.sh final-2026-10 | tail -12
echo "== make_tables"
$PY eval/baselines/make_tables.py
others > $R/final/other_tools.sha256.after
echo "against the committed cuVein tree: $(git diff --stat cuVein -- $(awk '{print $2}' $R/final/other_tools.sha256.after) | tail -1)"
for f in $R/final/other_tools.sha256.pre-sweep; do [ -e $f ] && { cmp -s $f $R/final/other_tools.sha256.after && echo "== pre-sweep sha256 (before submission): equal" || { echo "PRE-SWEEP SHA256 DIFFER"; diff $f $R/final/other_tools.sha256.after; }; }; done
if cmp -s $R/final/other_tools.sha256.before $R/final/other_tools.sha256.after; then
  echo "other tools' CSVs: unchanged ($(wc -l < $R/final/other_tools.sha256.after) files)"
else
  echo "OTHER TOOLS' CSVs CHANGED:"; diff $R/final/other_tools.sha256.before $R/final/other_tools.sha256.after
fi
echo "== sanity"
$PY eval/baselines/setup/final_sanity.py --merged $R/baselines-cuvein.csv --store $MAIN:1200 \
    --store $LONG:5400:$R/final-long --store $LONGSC:5400:$R/final-long-sc --out $R/final/sanity.json
echo "== done $(date -Is)"
