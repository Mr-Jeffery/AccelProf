#!/usr/bin/env python3
"""X3 (d): the list of programs above the lane cutoff, with X1b's collapsed verdicts, for FINAL_TABLES.md.

Reads eval/results/final-tables/sept_over_cutoff.csv (sept_cutoff.py) and X1b's merged CSV.
Writes eval/results/final-tables/sept_superseded.md. The 2026-09-22 verdicts are not read or written.
"""
import csv, os, collections

R = os.path.join(os.getcwd(), "eval", "results")
OUT = os.path.join(R, "final-tables")
RANK = {"RACE": 0, "CLEAN": 1, "TIMEOUT": 2, "ERROR": 3}
v = collections.defaultdict(list)
cap = collections.defaultdict(set)
for r in csv.DictReader(open(os.path.join(R, "final-b", "merged", "baselines-cuvein.csv"), newline="")):
    v[(r["id"], r["mode"])].append(r["verdict"])
    cap[r["id"]].add(r["notes"].split("cap=")[1].split(";")[0] if "cap=" in r["notes"] else "?")
rows = [r for r in csv.DictReader(open(os.path.join(OUT, "sept_over_cutoff.csv"), newline="")) if r["above_cutoff"] == "1"]


def col(i, m):
    x = v.get((i, m))
    return min(x, key=lambda t: RANK.get(t, 9)) if x else "missing"


with open(os.path.join(OUT, "sept_superseded.md"), "w") as f:
    f.write("| id | max lane-accesses in one kernel (X1b store) | 2026-09-22 row | X1b vector-clock | X1b scalar-clock |\n|---|---|---|---|---|\n")
    for r in rows:
        f.write(f"| {r['id']} | {int(r['max_lanes_per_kernel']):,} | SUPERSEDED (not cited) | {col(r['id'], 'vector-clock')} | {col(r['id'], 'scalar-clock')} |\n")
print(open(os.path.join(OUT, "sept_superseded.md")).read())
