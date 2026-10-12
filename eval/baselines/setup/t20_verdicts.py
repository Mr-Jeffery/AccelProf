#!/usr/bin/env python3
"""T20 step 3: the verdicts of two recordings of the same programs (parallel.py shard CSVs),
per (id, mode): verdict and dedup report count. Prints every differing row and a summary.
  t20_verdicts.py '<before glob>' '<after glob>'"""
import csv
import glob
import sys


def load(pat):
    rows = {}
    for f in sorted(glob.glob(pat)):
        for r in csv.DictReader(open(f)):
            rows[(r["id"], r["mode"])] = (r["verdict"], r["reports_dedup"])
    return rows


def main(before, after):
    a, b = load(before), load(after)
    keys = sorted(set(a) | set(b))
    verdict_diff = report_diff = 0
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if va is None or vb is None:
            print(f"MISSING {k}: before {va} after {vb}")
            continue
        if va[0] != vb[0]:
            verdict_diff += 1
            print(f"VERDICT {k[1]:13s} {k[0]}: {va[0]} ({va[1]}) -> {vb[0]} ({vb[1]})")
        elif va[1] != vb[1]:
            report_diff += 1
            print(f"reports {k[1]:13s} {k[0]}: {va[0]} {va[1]} -> {vb[1]}")
    print(f"{len(keys)} rows: {verdict_diff} verdicts differ, {report_diff} rows differ in the "
          f"report count only")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
