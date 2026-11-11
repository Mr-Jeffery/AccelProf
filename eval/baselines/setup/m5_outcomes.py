#!/usr/bin/env python3
"""M5 lines 1-2: rw_score.py recall.csv of sw0 and sw1 (T21b, T21c) compared per (target, variant, component): outcome, matched, n_race, n_sc."""
import csv, collections
R = "/home/fzheng4/wt-m5/eval/results/closure-atomic-hop/rw"
rows = {}
for sw in ("0", "1"):
    for d in ("realworld", "realworld_t21c"):
        for r in csv.DictReader(open(f"{R}/sw{sw}/{d}/recall.csv", newline="")):
            if r["flavor"] == "main" and r["mode"] == "collector-only":
                rows[(sw, d, r["target"], r["variant"], r["component"])] = r
keys = sorted({k[1:] for k in rows})
chg, cnt = [], collections.Counter()
for k in keys:
    a, b = rows.get(("0",) + k), rows.get(("1",) + k)
    if a is None or b is None:
        print("only in one:", k, bool(a), bool(b)); continue
    cnt[(k[0], k[2], b["outcome"])] += 1
    if (a["outcome"], a["matched"]) != (b["outcome"], b["matched"]):
        chg.append((k, a["outcome"], b["outcome"]))
    if (a["n_race"], a["n_sc"], a["run_verdict"]) != (b["n_race"], b["n_sc"], b["run_verdict"]):
        print("COUNTS", k, "n_race", a["n_race"], "->", b["n_race"], "n_sc", a["n_sc"], "->", b["n_sc"], "verdict", a["run_verdict"], "->", b["run_verdict"], "|", a["outcome"], "->", b["outcome"])
print("outcome/matched changes:", chg)
for k, v in sorted(cnt.items()):
    print(k, v)
for k in keys:
    if k[1] == "raft-1":
        print("raft-1 sw1:", k, rows[("1",) + k]["outcome"], rows[("1",) + k]["matched"], "| sw0:", rows[("0",) + k]["outcome"])
