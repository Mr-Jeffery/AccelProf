#!/usr/bin/env python3
"""C4 step 2: parity of the barrier-ordered-ON half of the re-analysis against X1b's own shard CSVs.

For every shard CSV X1b wrote for a scalar-clock analysis (final-b main + PI, final-b-long-sc, final-b-24h-sc), the
re-analysis wrote the same-named file (same ids, same X1b shard split). Compared per (id, mode, rep) on verdict,
reports_dedup, report_ids, report_lines and the classes note (the part of `notes` after nkernels / partial(...)),
plus the rest of notes as a separate count. Only scalar-clock rows (and rows without a mode) are compared: vector-clock
rows of X1b's files were not re-analysed.
  co_parity.py [X1b results dir] [co-offline results dir] > parity.md
"""
import csv
import glob
import os
import re
import sys
from collections import Counter, defaultdict

X = sys.argv[1] if len(sys.argv) > 1 else "/home/fzheng4/wt-x1b/eval/results"
M = sys.argv[2] if len(sys.argv) > 2 else "/home/fzheng4/wt-c4/eval/results/co-offline"
DIRS = ["final-b", "final-b-long-sc", "final-b-24h-sc"]
FIELDS = ["verdict", "reports_dedup", "report_ids", "report_lines"]
META_PREFIX = ("cap=", "node=", "arch=", "events=", "nkernels=", "partial(")


def classes_note(notes):
    """tokens of a RACE/CLEAN row's notes that are not run metadata: the classes note"""
    return ";".join(t for t in (notes or "").split(";") if t and not t.startswith(META_PREFIX))


def rows(path):
    return [r for r in csv.DictReader(open(path, newline="")) if r.get("mode", "") in ("scalar-clock", "")]


tot = Counter()
diffs = []
per_dir = {}
missing_files = []
for d in DIRS:
    nfiles = nrows = 0
    for xf in sorted(glob.glob(f"{X}/{d}/baselines-cuvein-shard*.csv")):
        mf = f"{M}/{d}/{os.path.basename(xf)}"
        if not os.path.exists(mf):
            missing_files.append(mf)
            continue
        xr, mr = rows(xf), rows(mf)
        nfiles += 1
        kx = {(r["id"], r["mode"], r["rep"]): r for r in xr}
        km = {(r["id"], r["mode"], r["rep"]): r for r in mr}
        for k in sorted(set(kx) | set(km)):
            a, b = kx.get(k), km.get(k)
            if a is None or b is None:
                diffs.append((d, k, "row only in " + ("co-offline" if a is None else "X1b"), "", ""))
                continue
            nrows += 1
            for f in FIELDS:
                if a[f] != b[f]:
                    diffs.append((d, k, f, a[f][:200], b[f][:200]))
            if classes_note(a["notes"]) != classes_note(b["notes"]):
                diffs.append((d, k, "classes_note", classes_note(a["notes"])[:200], classes_note(b["notes"])[:200]))
            if a["notes"] != b["notes"]:
                tot["notes_other_diff"] += 1
                if (a["mode"] != "") and a["verdict"] in ("RACE", "CLEAN"):
                    diffs.append((d, k, "notes", a["notes"][:200], b["notes"][:200]))
    per_dir[d] = (nfiles, nrows)

print("# C4 step 2: parity, barrier-ordered rule ON, against X1b's shard CSVs\n")
print("| X1b results dir | shard files compared | (id, mode, rep) rows compared |\n|---|---|---|")
for d, (nf, nr) in per_dir.items():
    print(f"| {d} | {nf} | {nr} |")
print(f"\nShard files X1b has and the re-analysis lacks: {len(missing_files)}")
for m in missing_files:
    print(f"- {m}")
print(f"\nDifferences (verdict, reports_dedup, report_ids, report_lines, classes note; notes on analysed rows): **{len(diffs)}**\n")
for d, k, f, a, b in diffs[:200]:
    print(f"- {d} {k} {f}: X1b `{a}` vs re-analysis `{b}`")
print(f"\nRows whose full `notes` string differs at all (incl. mode-less runner rows): {tot['notes_other_diff']}")
sys.exit(1 if diffs or missing_files else 0)
