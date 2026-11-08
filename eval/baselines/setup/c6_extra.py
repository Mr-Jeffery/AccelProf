#!/usr/bin/env python3
"""C6 step 3: programs per class of the sc-only pairs (detect/sc_only_pairs_classified.csv), by suite; the programs of the
deficit class (first-lane / allocation-end words dropped) and of the unexplained class."""
import csv, collections, os
D = os.environ.get("OUTD", "/home/fzheng4/wt-c6/eval/results/co-chain/step3") + "/detect"
rows = list(csv.DictReader(open(f"{D}/sc_only_pairs_classified.csv", newline="")))
by = collections.defaultdict(lambda: [0, set()])
for r in rows:
    k = (r["suite"], r["category"])
    by[k][0] += 1
    by[k][1].add(r["id"])
out = ["| suite | class | pairs | programs |", "|---|---|---|---|"]
for (s, c), (n, ids) in sorted(by.items()):
    out.append(f"| {s} | {c} | {n} | {len(ids)} |")
tot = collections.defaultdict(lambda: [0, set()])
for r in rows:
    tot[r["category"]][0] += 1
    tot[r["category"]][1].add(r["id"])
out.append("")
for c, (n, ids) in sorted(tot.items()):
    out.append(f"- all suites: {c}: {n} pairs in {len(ids)} programs")
dis = collections.Counter()
for r in rows:
    if r["category"].startswith("edge/chain cross-thread"):
        dis[r["detail"].split(";")[-1].strip()[:60]] += 1
out.append("\nDispositions of the 'judged not reported' pairs: " + str(dict(dis.most_common(8))))
for c in ("not reachable: dropped-word deficit at a or c", "not reachable: no gap evidence"):
    out.append(f"\n{c}: " + ", ".join(sorted({r['id'][:70] for r in rows if r['category'] == c})[:12]))
open(f"{D}/classes_by_program.md", "w").write("\n".join(out) + "\n")
print("\n".join(out))
