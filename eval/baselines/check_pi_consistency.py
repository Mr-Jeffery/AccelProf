#!/usr/bin/env python3
"""Consolidation check: the retired partial Indigo sets (P2 = 60-code sample, P8 =
SuperCollider's 99 tests; both ran on DAG_100n_100e 256x4) vs the same codes on the same
input inside PI. Same tool, same code, same input -> the verdict should be the same;
every difference is listed (nondeterministic schedules can flip a few). No GPU.
  .env/bin/python eval/baselines/check_pi_consistency.py
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_tables as mt


def main():
    runs, meta = mt.load_runs()
    new = {}
    for (i, t, m), r in runs.items():
        mm = meta.get(i)
        if mm and mm[0] == "PI" and mm[3] == "DAG_100n_100e":
            new[(mm[1], t, m)] = r["verdict"]
    stat = defaultdict(lambda: [0, 0, []])
    for (i, t, m), r in runs.items():
        mm = meta.get(i)
        if not mm or mm[0] not in ("P2", "P8") or mm[2] == "hirace-instrumented":
            continue
        v = new.get((mm[1], t, m))
        if v is None:
            continue
        s = stat[(t, m)]
        s[0] += 1
        if v == r["verdict"]:
            s[1] += 1
        else:
            s[2].append(f"{mm[0]}:{mm[1]} {r['verdict']}->{v}")
    print("tool/mode            compared  same  differences")
    for (t, m), (n, same, diff) in sorted(stat.items()):
        print(f"{(t + '/' + m).rstrip('/'):20} {n:8} {same:5}  " + "; ".join(diff[:8]) + (" ..." if len(diff) > 8 else ""))


if __name__ == "__main__":
    main()
