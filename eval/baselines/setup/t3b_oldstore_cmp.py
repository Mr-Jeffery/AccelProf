#!/usr/bin/env python3
"""T3b: compare the base and T3b re-scores of one kept store (setup/t3b_oldstore.sh) row by
row: verdict, report ids and hb_class counts per (id, mode, rep). Exit 0 iff all agree.
  t3b_oldstore_cmp.py <TAG>"""
import csv
import glob
import sys

tag = sys.argv[1]


def rows(side):
    out = {}
    for f in glob.glob(f"eval/results/t3b-oldstore-{tag}-{side}/*.csv"):
        for r in csv.DictReader(open(f)):
            out[(r["id"], r["mode"], r["rep"])] = r
    return out


b, t = rows("base"), rows("t3b")
keys = sorted(set(b) | set(t))
diff = 0
cols = ("verdict", "report_ids", "reports", "structural", "latent")
for k in keys:
    rb, rt = b.get(k), t.get(k)
    if rb is None or rt is None:
        diff += 1
        print(f"MISSING {k}: base={'yes' if rb else 'no'} t3b={'yes' if rt else 'no'}")
        continue
    d = [c for c in cols if c in rb and rb.get(c) != rt.get(c)]
    if d:
        diff += 1
        print(f"DIFF {k}: " + "; ".join(f"{c}: {rb[c][:80]} -> {rt[c][:80]}" for c in d))
verdicts = {}
for r in t.values():
    verdicts[(r["mode"], r["verdict"])] = verdicts.get((r["mode"], r["verdict"]), 0) + 1
print(f"{len(keys)} (id, mode, rep) rows; {diff} differ; t3b verdicts {sorted(verdicts.items())}")
sys.exit(1 if diff else 0)
