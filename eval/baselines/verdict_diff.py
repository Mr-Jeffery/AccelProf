#!/usr/bin/env python3
"""Row-by-row verdict diff of two sets of harness CSVs (same schema, blib.COLUMNS).

  python3 eval/baselines/verdict_diff.py 'eval/results/full-2026-09-22/*.csv' \
                                          'eval/results/full-2026-09-22-cpu/*.csv'

Keys rows by (id, mode, rep) and reports every key whose verdict, reports_dedup or
report_ids differ, plus keys present on one side only. Exit 0 iff nothing differs.
Used for T0's acceptance (GPU-phase inline analysis == CPU-node re-score of the
same BeeGFS store) and for any "identical up to labels" check on migrated stores.
"""
import csv
import glob
import sys


def load(pattern):
    rows = {}
    for f in sorted(glob.glob(pattern)):
        for r in csv.DictReader(open(f, newline="")):
            k = (r["id"], r.get("mode", ""), r.get("rep", ""))
            rows[k] = (r["verdict"], r.get("reports_dedup", ""), r.get("report_ids", ""), r.get("notes", ""))
    return rows


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diff = [(k, a[k], b[k]) for k in sorted(set(a) & set(b)) if a[k][:3] != b[k][:3]]
    print(f"A: {len(a)} rows  B: {len(b)} rows  common: {len(set(a) & set(b))}  "
          f"only-A: {len(only_a)}  only-B: {len(only_b)}  differing: {len(diff)}")
    for k in only_a:
        print(f"  only A: {k} {a[k][:3]}")
    for k in only_b:
        print(f"  only B: {k} {b[k][:3]}")
    for k, va, vb in diff:
        print(f"  DIFF {k}\n     A: {va[:3]}  notes={va[3][:120]}\n     B: {vb[:3]}  notes={vb[3][:120]}")
    same = [k for k in set(a) & set(b) if a[k][:3] == b[k][:3]]
    print(f"identical verdict/report rows: {len(same)}")
    sys.exit(0 if not (only_a or only_b or diff) else 1)


if __name__ == "__main__":
    main()
