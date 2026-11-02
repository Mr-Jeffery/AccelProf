#!/usr/bin/env bash
#SBATCH --job-name=x1b-post
#SBATCH --partition=normal
#SBATCH --exclude=c2,c21,c23,c37,c43,c46,c54,c77
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/finalb-post-%j.log
# X1b post-processing (eval/FINAL_SWEEP_B.md), CPU only, on a compute node (the stores are on BeeGFS):
# p_final_post.sh's steps with X1b's inputs, every output in X1b's own places -- X1's files
# (eval/results/baselines-*.csv, eval/results/final*/, the tables, the runtime checkout's
# confirm_final* directories) are read, never written:
#   1. the other tools' sha256 (as X1 section 7) -> eval/results/final-b/merged/other_tools.sha256.before
#   2. the 24 h pass's kept / dropped keys (X1's rule: a 84,600 s row replaces the earlier rows of its
#      (id, mode) when it reached RACE, CLEAN or TIMEOUT; an ERROR leaves the earlier rows standing)
#      -> eval/results/final-b-24h-kept-{vc,sc}/
#   3. merge (cuvein only): eval/results/final-b/ (first pass + PI) with --override final-b-long,
#      final-b-long-sc, final-b-24h-kept-vc, final-b-24h-kept-sc (later dirs win)
#      -> eval/results/final-b/merged/baselines-cuvein.csv
#   4. the confirmation-detail view of the merged rows (symlinks; the files stay where the runs put them)
#      -> $VIEW (default ~/x1b/confirm_final-b-merged)
#   5. residual ids and their classes (classify_residuals.py --no-dump, its output path redirected)
#      -> eval/results/final-b/merged/{residual_ids.txt,baselines-diagnose.csv}
#   6. sanity, FINAL_B=1 (frozen hashes of the f551ca0 install, hb_shards 16) -> merged/sanity.json
#   7. the verdict diff against T20's parity recording (X1 section 6 (b)) -> merged/verdict_diff_t20*.txt
#   8. old vs new against X1's merged file, with the direction check -> merged/old_vs_new.md
#   9. the report tables -> merged/report_tables.md; the other tools' sha256 again (after)
# Not run: classify_endpoints.py, classify_fp_causes.py, make_tables.py, cuvein_rev.sh (they write X1's
# eval/results/baselines-{disagreements,fp-causes}.csv, tables and revision pin).
#   sbatch eval/baselines/setup/p_final_b_post.sh
set -u
W=${W:-/home/fzheng4/wt-x1b}
RT=/home/fzheng4/AccelProf
B=/mnt/beegfs/$USER/cuvein_traces
MAIN=$B/final-2026-11; LONG=$B/final-2026-11-long; LONGSC=$B/final-2026-11-long-sc
H24VC=$B/final-2026-11-24h-vc; H24SC=$B/final-2026-11-24h-sc
CB=$RT/eval/baselines; VIEW=${VIEW:-$HOME/x1b/confirm_final-b-merged}
cd $W || exit 1
export ACCEL_PROF_HOME=$W
PY=$RT/.env/bin/python
R=eval/results; O=$R/final-b/merged
mkdir -p $O
echo "host=$(hostname) W=$W HEAD=$(git rev-parse --short=12 HEAD) dirty=$(git status --porcelain -uno | wc -l) $(date -Is)"
others() { ls $R/baselines-*.csv | /usr/bin/grep -v "baselines-cuvein\|baselines-diagnose\|baselines-disagreements\|baselines-fp-causes" \
             | sort | xargs sha256sum; }
others > $O/other_tools.sha256.before
echo "== 24 h pass: kept / dropped"
$PY - $W/$R <<'EOF'
import csv, glob, os, sys, collections
R = sys.argv[1]
for sfx in ("vc", "sc"):
    rows = [r for f in sorted(glob.glob(f"{R}/final-b-24h-{sfx}/baselines-cuvein-shard*.csv"))
            for r in csv.DictReader(open(f, newline=""))]
    per = collections.defaultdict(list)
    for r in rows:
        per[(r["id"], r["mode"])].append(r)
    keep = {k for k, rs in per.items() if {x["verdict"] for x in rs} <= {"RACE", "CLEAN", "TIMEOUT"}}
    dst = f"{R}/final-b-24h-kept-{sfx}"
    os.makedirs(dst, exist_ok=True)
    with open(f"{dst}/baselines-cuvein-shard24h-kept-{sfx}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for k in sorted(keep):
            w.writerows(per[k])
    with open(f"{dst}/dropped.txt", "w") as fh:
        for k in sorted(set(per) - keep):
            for x in per[k]:
                fh.write(f"{k[0]} {k[1]} {x['verdict']} wall={x['wall_s']} peak_mb={x['peak_mb']} rc={x['rc']} {x['notes'][:200]}\n")
    print(f"24 h {sfx}: {len(per)} keys with a row, kept {len(keep)}, dropped {len(per) - len(keep)}")
EOF
echo "== merge"
OVS=""; for d in final-b-long final-b-long-sc final-b-24h-kept-vc final-b-24h-kept-sc; do OVS="$OVS${OVS:+,}$W/$R/$d"; done
$PY eval/baselines/parallel.py merge --tool cuvein --results-dir $W/$R/final-b --out-dir $W/$O --override $OVS
echo "== confirmation-detail view of the merged rows: $VIEW"
$PY - "$CB" "$VIEW" $W/$R <<'EOF'
import csv, glob, os, shutil, sys
cb, view, R = sys.argv[1:]
shutil.rmtree(view, ignore_errors=True); os.makedirs(view)
n = 0
for f in glob.glob(f"{cb}/confirm_final-b/*.json"):
    os.symlink(f, f"{view}/{os.path.basename(f)}"); n += 1
moved = {}
for d, conf in (("final-b-long", "confirm_final-b-long"), ("final-b-long-sc", "confirm_final-b-long-sc"),
                ("final-b-24h-kept-vc", "confirm_final-b-24h-vc"), ("final-b-24h-kept-sc", "confirm_final-b-24h-sc")):
    keys = {(r["id"], r["mode"]) for f in glob.glob(f"{R}/{d}/baselines-cuvein-shard*.csv")
            for r in csv.DictReader(open(f, newline=""))}
    for i, m in keys:
        b = f"{i}__cuvein__{m}.json"
        if os.path.lexists(f"{view}/{b}"):
            os.remove(f"{view}/{b}")
        src = f"{cb}/{conf}/{b}"
        moved[(i, m)] = conf if os.path.exists(src) else "(no detail: TIMEOUT/ERROR)"
        if os.path.exists(src):
            os.symlink(src, f"{view}/{b}")
print(f"view: {n} first-pass details; {len(moved)} (id, mode) keys from the long passes:")
for k in sorted(moved):
    print(f"  {k[0]} {k[1]} <- {moved[k]}")
EOF
echo "== residual ids (no RACE/CLEAN in some mode) and their classes"
$PY - $O/baselines-cuvein.csv > $O/residual_ids.txt <<'EOF'
import csv, sys, collections
per = collections.defaultdict(set)
for r in csv.DictReader(open(sys.argv[1], newline="")):
    for m in ([r["mode"]] if r["mode"] else ["vector-clock", "scalar-clock"]):
        per[(r["id"], m)].add(r["verdict"])
print("\n".join(sorted({i for (i, m), v in per.items() if not v & {"RACE", "CLEAN"}})))
EOF
wc -l < $O/residual_ids.txt
LG=$CB/setup/build_logs
$PY - "$W" "$O" "$LG" <<'EOF'
import sys
W, O, LG = sys.argv[1:]
sys.path.insert(0, f"{W}/eval/baselines")
import classify_residuals as c
c.RES = f"{W}/{O}"          # the output goes to X1b's merged dir, not eval/results/baselines-diagnose.csv
sys.argv = ["classify_residuals.py", "--no-dump", "--ids", f"{W}/{O}/residual_ids.txt",
            "--diag", f"{W}/{O}/baselines-cuvein.csv", "--base", "",
            "--logs", f"{LG}/finalb-[0-9]*.log,{LG}/finalb-pi-*.log,{LG}/finalb-long-*.log,{LG}/finalb-24h-*.log"]
c.main()
EOF
echo "== sanity (FINAL_B=1)"
FINAL_B=1 FINAL_B_SHARDS=16 $PY eval/baselines/setup/final_sanity.py --merged $O/baselines-cuvein.csv --store $MAIN:1200 \
    --store $LONG:5400:$R/final-b-long --store $LONGSC:5400:$R/final-b-long-sc \
    --store $H24VC:84600:$R/final-b-24h-kept-vc --store $H24SC:84600:$R/final-b-24h-kept-sc \
    --out $O/sanity.json
echo "== nproc / hb_shards / harness heads over every meta.json"
$PY - $MAIN $LONG $LONGSC $H24VC $H24SC <<'EOF'
import json, glob, os, sys, collections
for st in sys.argv[1:]:
    c = collections.Counter()
    for f in glob.glob(f"{st}/*/meta.json"):
        try:
            m = json.load(open(f))
        except (OSError, ValueError):
            c["unreadable"] += 1; continue
        rt = m.get("runtime") or {}
        c[(json.dumps(m.get("hb_shards"), sort_keys=True), m.get("nproc"), rt.get("runtime_head"), rt.get("harness_head"),
           rt.get("harness_dirty"), m.get("status"))] += 1
    print(os.path.basename(st), sum(c.values()))
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print("   ", v, k)
EOF
echo "== verdict diff against T20's parity recording"
$PY eval/baselines/setup/final_verdict_diff.py --final $O/baselines-cuvein.csv --parity "$W/$R/x0-default/*.csv" \
    --ids eval/baselines/setup/t5b_parity_ids.txt --final-confirm $VIEW \
    --parity-confirm $RT/.claude/worktrees/wt-x0/eval/baselines/confirm_x0-default \
    --rep1-csv $O/parity_rep1.csv > $O/verdict_diff_t20.txt; echo "final_verdict_diff rc=$?"
tail -1 $O/verdict_diff_t20.txt
$PY eval/baselines/verdict_diff.py "$W/$R/x0-default/*.csv" $O/parity_rep1.csv > $O/verdict_diff_t20_rep1_literal.txt; echo "verdict_diff rc=$?"
tail -3 $O/verdict_diff_t20_rep1_literal.txt
echo "== old vs new (X1's merged file against X1b's)"
$PY eval/baselines/setup/final_b_old_vs_new.py --old $R/baselines-cuvein.csv --new $O/baselines-cuvein.csv > $O/old_vs_new.md
echo "final_b_old_vs_new rc=$? (3 = a RACE in X1 is CLEAN in X1b)"
tail -4 $O/old_vs_new.md
echo "== report tables"
[ -e $R/final-b/sacct.txt ] && SA="--sacct $R/final-b/sacct.txt" || SA=""
$PY eval/baselines/setup/final_report_tables.py --merged $O/baselines-cuvein.csv --first $R/final-b \
    --long $R/final-b-long,$R/final-b-long-sc --h24 $R/final-b-24h-vc,$R/final-b-24h-sc \
    --diagnose $O/baselines-diagnose.csv $SA > $O/report_tables.md
echo "report_tables rc=$?"
echo "== the other tools' CSVs"
others > $O/other_tools.sha256.after
if cmp -s $O/other_tools.sha256.before $O/other_tools.sha256.after; then
  echo "before == after ($(wc -l < $O/other_tools.sha256.after) files)"
else
  echo "OTHER TOOLS' CSVs CHANGED during this job:"; diff $O/other_tools.sha256.before $O/other_tools.sha256.after
fi
for f in $R/final/other_tools.sha256.after $R/final/other_tools.sha256.pre-sweep; do
  cmp -s $f $O/other_tools.sha256.after && echo "equal to X1's $f" || { echo "DIFFERS from X1's $f:"; diff $f $O/other_tools.sha256.after | head -20; }
done
echo "against f551ca0 (the install commit X1b's branch starts from): $(git diff --stat f551ca0 -- $(awk '{print $2}' $O/other_tools.sha256.after) | tail -1)"
echo "against cuVein: $(git diff --stat cuVein -- $(awk '{print $2}' $O/other_tools.sha256.after) | tail -1)"
echo "X1's files under eval/results (tracked): $(git status --porcelain -- eval/results/baselines-cuvein.csv eval/results/final eval/results/final-long eval/results/final-long-sc eval/results/final-24h-vc eval/results/final-24h-sc eval/results/final-24h-kept-vc eval/results/final-24h-kept-sc | wc -l) changed entries"
echo "== done $(date -Is)"
