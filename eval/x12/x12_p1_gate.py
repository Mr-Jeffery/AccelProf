#!/usr/bin/env python3
"""X12 parity gate on the Indigo3 (P1) set: every kept rep of the sharded recording against C1's -n 1 recording of the same id.
  x12_p1_gate.py NEWSTORE C1STORE OUTDIR [--parity-a A --parity-b B]
Per id and rep: co_json_diff (T26) on <new>/<id>/collector-only-rep<k> vs <c1>/<id>/collector-only. Writes OUTDIR/p1_gate.tsv and
p1_gate_summary.txt. With --parity-a/--parity-b (C1's two recordings of its 65-id parity set) also reports C1-vs-C1 for the ids both hold."""
import argparse, glob, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "baselines", "setup"))
import co_json_diff as D

def cmp(a, b):
    fa, fb = D.kernel_files(a), D.kernel_files(b)
    if not fa or not fb:
        return dict(status="MISSING", kernels=0, differ=0, edges=0, dist=0)
    ks = sorted(set(fa) & set(fb))
    differ = edges = dist = 0
    for k in ks:
        r = D.diff_kernel(fa[k], fb[k], 0)
        if not r["equal"]:
            differ += 1
            edges += r.get("edges_only_a", 0) + r.get("edges_only_b", 0) + r.get("edges_changed", 0)
            dist += r.get("dist_count_diffs", 0)
    miss = len(set(fa) ^ set(fb))
    return dict(status="EQUAL" if not differ and not miss else "DIFFER", kernels=len(ks), differ=differ, edges=edges, dist=dist, unmatched=miss)

ap = argparse.ArgumentParser()
ap.add_argument("new"); ap.add_argument("c1"); ap.add_argument("out")
ap.add_argument("--parity-a"); ap.add_argument("--parity-b")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
ids = sorted(d for d in os.listdir(a.new) if d.startswith("P1-") and os.path.isdir(f"{a.new}/{d}"))
rows = []
for i in ids:
    reps = sorted(glob.glob(f"{a.new}/{i}/collector-only-rep*"))
    if not reps:
        rows.append((i, "-", dict(status="NO-REPS", kernels=0, differ=0, edges=0, dist=0, unmatched=0))); continue
    for r in reps:
        rows.append((i, r.rsplit("rep", 1)[1], cmp(r, f"{a.c1}/{i}/collector-only")))
with open(f"{a.out}/p1_gate.tsv", "w") as f:
    f.write("id\trep\tstatus\tkernels\tdiffering_kernels\tedge_diffs\tdist_count_diffs\tunmatched\n")
    for i, r, c in rows:
        f.write(f"{i}\t{r}\t{c['status']}\t{c['kernels']}\t{c['differ']}\t{c['edges']}\t{c['dist']}\t{c.get('unmatched', 0)}\n")
from collections import Counter
cnt = Counter(c["status"] for _, _, c in rows)
bad_ids = sorted({i for i, _, c in rows if c["status"] != "EQUAL"})
lines = [f"ids in new store: {len(ids)}; id-reps compared: {len(rows)}; {dict(cnt)}",
         f"ids with any non-EQUAL rep: {len(bad_ids)}"]
if a.parity_a and a.parity_b:
    pa = {d for d in os.listdir(a.parity_a) if d.startswith("P1-")}; pb = {d for d in os.listdir(a.parity_b) if d.startswith("P1-")}
    both = sorted(pa & pb); c1c = Counter()
    for i in both:
        c1c[cmp(f"{a.parity_a}/{i}/collector-only", f"{a.parity_b}/{i}/collector-only")["status"]] += 1
    lines.append(f"C1 parity-a vs parity-b (rep1 JSONs, P1 ids in both: {len(both)}): {dict(c1c)}")
lines += ["non-EQUAL ids (first 40): " + ", ".join(bad_ids[:40])]
open(f"{a.out}/p1_gate_summary.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(0 if not bad_ids else 1)
