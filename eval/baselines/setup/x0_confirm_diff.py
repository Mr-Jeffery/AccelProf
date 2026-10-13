#!/usr/bin/env python3
"""X0 (eval/AGGREGATES_DEFAULT.md): report-level diff of two `parallel.py analyze --confirm`
detail directories of the SAME store -- A = the record replay (CUVEIN_PREFER_RECORDS=1, the
old default), B = the aggregates (the default since X0).

verdict_diff.py compares rows on (verdict, reports_dedup, report_ids); this goes one level
down, to the report objects of each <id>__cuvein__<mode>.json: `raw` (DR reports) and
`raw_sc` (SC, informational), keyed by (a_pc, b_pc, space, race_type), every other field
compared. A key present in A and missing in B is a LOST report (the brief's stop condition);
a key only in B is a gained report; a key in both with any field changed is listed with the
fields. Exit 0 iff nothing is lost.

  x0_confirm_diff.py <confirm_dir_A> <confirm_dir_B> [--over <id,mode list file>]
"""
import argparse
import glob
import json
import os
import sys


def load(d):
    out = {}
    for f in glob.glob(f"{d}/*__cuvein__*.json"):
        j = json.load(open(f))
        out[(j["id"], j["mode"])] = j
    return out


def reports(j):
    rs = {}
    for kind in ("raw", "raw_sc"):
        for r in j.get(kind) or ():
            k = (kind, r.get("a_pc"), r.get("b_pc"), r.get("space"), r.get("race_type"))
            rs.setdefault(k, []).append({x: v for x, v in r.items()
                                         if x not in ("a_pc", "b_pc", "space", "race_type")})
    return rs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--over", default="", help="file of '<id> <mode>' lines above the cutoff")
    a = ap.parse_args()
    A, B = load(a.a), load(a.b)
    over = set()
    if a.over and os.path.exists(a.over):
        over = {tuple(l.split()[:2]) for l in open(a.over) if l.strip()}
    lost = 0
    print(f"A: {len(A)} detail files  B: {len(B)}  common: {len(set(A) & set(B))}")
    for k in sorted(set(A) ^ set(B)):
        print(f"  only {'A' if k in A else 'B'}: {k}")
    ndiff = 0
    for k in sorted(set(A) & set(B)):
        ja, jb = A[k], B[k]
        ra, rb = reports(ja), reports(jb)
        ids_a, ids_b = set(ja["report_ids"]), set(jb["report_ids"])
        if ja["verdict"] == jb["verdict"] and ids_a == ids_b and ra == rb:
            continue
        ndiff += 1
        tag = "over-cutoff" if k in over else "UNDER-CUTOFF"
        print(f"DIFF {k[0]} {k[1]} [{tag}] verdict {ja['verdict']} -> {jb['verdict']}  "
              f"report_ids {len(ids_a)} -> {len(ids_b)}")
        for i in sorted(ids_a - ids_b):
            print(f"    LOST id   {i}")
            lost += 1
        for i in sorted(ids_b - ids_a):
            print(f"    gained id {i}")
        for rk in sorted(set(ra) | set(rb), key=str):
            if rk not in rb:
                print(f"    LOST report {rk} {ra[rk]}")
                lost += 1
            elif rk not in ra:
                print(f"    gained report {rk} {rb[rk]}")
            elif ra[rk] != rb[rk]:
                fa = ra[rk][0] if len(ra[rk]) == 1 else ra[rk]
                fb = rb[rk][0] if len(rb[rk]) == 1 else rb[rk]
                ch = {x: (fa.get(x), fb.get(x)) for x in set(fa) | set(fb)
                      if fa.get(x) != fb.get(x)} if isinstance(fa, dict) and isinstance(fb, dict) \
                    else (fa, fb)
                print(f"    changed {rk} {ch}")
    print(f"differing detail files: {ndiff}; lost reports: {lost}")
    sys.exit(1 if lost else 0)


if __name__ == "__main__":
    main()
