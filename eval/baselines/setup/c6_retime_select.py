#!/usr/bin/env python3
"""C6 step 2 re-time sample: VERDICT_PARALLEL.md section 6's sampling (x7_old.py select), as an id list.
Non-HeCBench suites P1 8, P3 4, P4 8, P5 4, P6 4, PI 12 = 40 programs, evenly spaced over the sorted A5
vector-clock analysis_s (rep 1) and including each suite's slowest; plus every P7/P9 id that has an analysed A5 row
and was not re-run by a long / 24 h pass. usage: c6_retime_select.py <wt> <out ids file>"""
import csv, glob, re, sys
W, out = sys.argv[1], sys.argv[2]
longids = set()
for f in glob.glob(W + "/eval/baselines/setup/x7_a5_*.txt"):
    longids |= {l.strip() for l in open(f) if l.strip()}
rows = [r for r in csv.DictReader(open(W + "/eval/results/verdict-timing/final-b-merged/baselines-cuvein.csv"))
        if r["rep"] == "1" and "analysis_s=" in r["notes"] and r["id"] not in longids]


def s(r):
    return float(re.search(r"analysis_s=([0-9.]+)", r["notes"]).group(1))


ids = []
for ps, q in [("P1", 8), ("P3", 4), ("P4", 8), ("P5", 4), ("P6", 4), ("PI", 12)]:
    v = sorted((r for r in rows if r["pset"] == ps and r["mode"] == "vector-clock"), key=lambda r: (s(r), r["id"]))
    idx = sorted({round(i * (len(v) - 1) / (q - 1)) for i in range(q)})
    ids += [v[i]["id"] for i in idx]
n_non = len(ids)
hb = sorted({r["id"] for r in rows if r["pset"] in ("P7", "P9")})
ids += hb
with open(out, "w") as fh:
    for i in ids:
        fh.write(i + "\n")
print(f"{n_non} non-HeCBench ids + {len(hb)} HeCBench ids = {len(ids)}")
