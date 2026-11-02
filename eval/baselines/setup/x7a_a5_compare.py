#!/usr/bin/env python3
"""X7 A5: merge the re-analysis shards as X1b / C1 merged theirs, then compare row by row.
  x7a_a5_compare.py <wt> {final-b|co}
final-b: results final-b (+pi) with --override final-b-long, final-b-long-sc, 24h-kept-vc, 24h-kept-sc
         (the 24 h rule of p_final_b_post.sh: an 84,600 s key replaces earlier rows when every row is
         RACE/CLEAN/TIMEOUT), against /home/fzheng4/wt-x1b/eval/results/final-b/merged/baselines-cuvein.csv
co:      results collector-only with --override collector-only-long, collector-only-24h,
         against /home/fzheng4/wt-co/eval/results/collector-only/merged/baselines-cuvein.csv
Compared per (id, mode, rep): verdict, reports_dedup, report_ids, report_lines, the classes= note."""
import csv, collections, glob, os, subprocess, sys
W, which = sys.argv[1], sys.argv[2]
R = f"{W}/eval/results/verdict-timing"
PY = "/home/fzheng4/AccelProf/.env/bin/python"
if which == "final-b":
    ovs = ["final-b-long", "final-b-long-sc"]
    for sfx in ("vc", "sc"):
        rows = [r for f in sorted(glob.glob(f"{R}/final-b-24h-{sfx}/baselines-cuvein-shard*.csv"))
                for r in csv.DictReader(open(f, newline=""))]
        per = collections.defaultdict(list)
        for r in rows: per[(r["id"], r["mode"])].append(r)
        keep = {k for k, rs in per.items() if {x["verdict"] for x in rs} <= {"RACE", "CLEAN", "TIMEOUT"}}
        dst = f"{R}/final-b-24h-kept-{sfx}"; os.makedirs(dst, exist_ok=True)
        with open(f"{dst}/baselines-cuvein-shard24h-kept-{sfx}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
            for k in sorted(keep): w.writerows(per[k])
        print(f"24h {sfx}: {len(per)} keys, kept {len(keep)}")
        ovs.append(f"final-b-24h-kept-{sfx}")
    res, ref = f"{R}/final-b", "/home/fzheng4/wt-x1b/eval/results/final-b/merged/baselines-cuvein.csv"
    out = f"{R}/final-b-merged"
else:
    ovs = ["collector-only-long", "collector-only-24h"]
    res, ref = f"{R}/collector-only", "/home/fzheng4/wt-co/eval/results/collector-only/merged/baselines-cuvein.csv"
    out = f"{R}/collector-only-merged"
os.makedirs(out, exist_ok=True)
subprocess.run([PY, f"{W}/eval/baselines/parallel.py", "merge", "--tool", "cuvein", "--results-dir", res,
                "--out-dir", out, "--override", ",".join(f"{R}/{o}" for o in ovs)], check=True)
new = list(csv.DictReader(open(f"{out}/baselines-cuvein.csv", newline="")))
old = list(csv.DictReader(open(ref, newline="")))
def cls(n):
    return next((t for t in n.split(";") if t.startswith("classes=")), "")
def key(r): return (r["id"], r["mode"], r["rep"])
FIELDS = ("verdict", "reports_dedup", "report_ids", "report_lines")
def table(rows):
    d = {}
    for r in rows:
        k = key(r)
        if k in d: print("DUPLICATE KEY", k, file=sys.stderr)
        d[k] = r
    return d
N, O = table(new), table(old)
diffs = []
for k in sorted(set(N) | set(O)):
    if k not in N: diffs.append((k, "missing-in-new", "", "")); continue
    if k not in O: diffs.append((k, "missing-in-ref", "", "")); continue
    for f in FIELDS:
        if N[k][f] != O[k][f]: diffs.append((k, f, O[k][f][:120], N[k][f][:120]))
    if cls(N[k]["notes"]) != cls(O[k]["notes"]): diffs.append((k, "classes", cls(O[k]["notes"]), cls(N[k]["notes"])))
print(f"{which}: ref rows {len(O)}, new rows {len(N)}, ids ref {len({k[0] for k in O})} new {len({k[0] for k in N})}")
print(f"{which}: differences {len(diffs)} over {len({d[0] for d in diffs})} rows")
with open(f"{out}/parity_diffs.tsv", "w") as fh:
    for d in diffs: fh.write("\t".join(map(str, (*d[0], *d[1:]))) + "\n")
for d in diffs[:40]: print(d)
