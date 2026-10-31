#!/usr/bin/env python3
"""C4 supplement to co_offline_tables.py / co_offline_pairs_report.py: (1) program level, CO-R against C1's collector-only run, per suite, with
the cause of each differing program taken from the cause of its differing pairs (pairs_cor_vs_c1.csv); (2) the pair-pass analysis failures;
(3) S1 pairs not in (a). Reads CSV / jsonl only (and make_tables' verdict helpers through the sandbox, as co_offline_tables.py does)."""
import collections
import csv
import glob
import json
import os
import sys

sys.argv = [sys.argv[0], "--collector-only", "--co-offline"]
SB = os.environ.get("COSB", "/home/fzheng4/co-offline-sandbox-b")
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt  # noqa: E402

R = "/home/fzheng4/wt-c4/eval/results/co-offline"
runs, meta = mt.load_runs()
CO, COR = mt.CO, mt.CORS
md = []
P = md.append
pc = collections.defaultdict(lambda: collections.defaultdict(set))   # id -> direction -> causes
cnt = collections.defaultdict(collections.Counter)
for r in csv.DictReader(open(f"{R}/tables/pairs_cor_vs_c1.csv")):
    pc[r["id"]][r["direction"]].add(r["cause"].split(" (")[0])
P("## Program level: CO-R against C1's collector-only run (separate recordings), per suite\n")
P("Programs whose verdict differs (RACE / CLEAN / TIMEOUT / ERROR as recorded), with the cause of the program's differing pairs "
  "(the causes of the CO-R-only pairs when CO-R is Race, of the C1-only pairs when C1 is Race; a program can have several).\n")
P("| suite | programs in both | same verdict | C1 Clean → CO-R Race | C1 Race → CO-R Clean | other differences | of the first: extended edge | rescue | other | none found (no differing pair) |")
P("|---|---|---|---|---|---|---|---|---|---|")
tot = collections.Counter()
rows = []
for s in ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"):
    c = collections.Counter()
    for i, m in meta.items():
        if m[0] != s:
            continue
        a, b = runs.get((i, "cuvein", CO)), runs.get((i, "cuvein", COR))
        if a is None or b is None:
            continue
        c["n"] += 1
        va, vb = a["verdict"], b["verdict"]
        if va == vb:
            c["same"] += 1
        elif va == "CLEAN" and vb == "RACE":
            c["up"] += 1
            cs = pc[i]["CO-R only"]
            for k, key in (("extended edge", "x"), ("rescue", "r"), ("other", "o")):
                if k in cs:
                    c[key] += 1
            if not cs:
                c["none"] += 1
            rows.append((s, i, "C1 CLEAN -> CO-R RACE", ";".join(sorted(cs))))
        elif va == "RACE" and vb == "CLEAN":
            c["down"] += 1
            rows.append((s, i, "C1 RACE -> CO-R CLEAN", ";".join(sorted(pc[i]["C1 only"]))))
        else:
            c["oth"] += 1
            rows.append((s, i, f"C1 {va} -> CO-R {vb}", ""))
    tot.update(c)
    P(f"| {s} | {c['n']} | {c['same']} | {c['up']} | {c['down']} | {c['oth']} | {c['x']} | {c['r']} | {c['o']} | {c['none']} |")
P(f"| **all** | {tot['n']} | {tot['same']} | {tot['up']} | {tot['down']} | {tot['oth']} | {tot['x']} | {tot['r']} | {tot['o']} | {tot['none']} |")
with open(f"{R}/tables/program_level_cor_vs_c1.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["suite", "id", "direction", "pair_causes"])
    w.writerows(rows)
recs, first = {}, {}
for f in sorted(glob.glob(f"{R}/pairs/shard*.jsonl")):
    for ln in open(f):
        r = json.loads(ln)
        first.setdefault(r["id"], r)
        recs[r["id"]] = r          # a shard_long_* record (longer cap) comes last in sort order and replaces the first
P("\n## Pair pass: recordings whose first pair-level analysis hit the 3,600 s cap\n")
for i, r0 in first.items():
    if r0["on"]["reason"] or r0["off"]["reason"]:
        r = recs[i]
        P(f"- `{i}`: first pass rule on `{r0['on']['reason'] or 'ok'}` ({r0['on']['elapsed']} s), rule off `{r0['off']['reason'] or 'ok'}` ({r0['off']['elapsed']} s); "
          f"re-run with a 16,200 s cap: rule on `{r['on']['reason'] or 'ok'}` ({r['on']['elapsed']} s), rule off `{r['off']['reason'] or 'ok'}` ({r['off']['elapsed']} s)")
P("\n## S1 pairs not in (a)\n")
P("| program | space | pc lo | pc hi | reason |")
P("|---|---|---|---|---|")
for r in csv.DictReader(open(f"{R}/tables/pairs_a_vs_S1.csv")):
    P(f"| `{r['id']}` | {r['space']} | {r['pc_lo']} | {r['pc_hi']} | {r['reason']}: {r['detail']} |")
P("\n(a) and S1 hold the same pairs: both difference lists above are empty." if not any(True for _ in csv.DictReader(open(f"{R}/tables/pairs_a_vs_S1.csv"))) else "")
open(f"{R}/tables/co_offline_extra.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
