#!/usr/bin/env python3
"""Row-by-row verdict diff of two sets of harness CSVs (same schema, blib.COLUMNS).

  python3 eval/baselines/verdict_diff.py 'eval/results/full-2026-09-22/*.csv' \
                                          'eval/results/full-2026-09-22-cpu/*.csv'

Keys rows by (id, mode, rep) and reports every key whose verdict, reports_dedup or
report_ids differ, plus keys present on one side only. Exit 0 iff nothing differs.
Used for T0's acceptance (GPU-phase inline analysis == CPU-node re-score of the
same BeeGFS store) and for any "identical up to labels" check on migrated stores.

X2 (eval/FINAL_CERTAIN.md) options, for comparing two recordings of the same programs (X1's
P4/P5 rows against final-certain-recorded):
  --pset P4,P5          only rows of these program sets (both sides)
  --mode vector-clock   only rows of this mode (both sides)
  --verdict-only        compare the verdict only (two recordings may differ in report sets)
  --collapse            one key per (id, mode): the program verdict make_tables takes (RACE if
                        any rep reports, else CLEAN, else TIMEOUT, else ERROR) and, beside it,
                        the Race-alone verdict (make_tables.race_alone_verdict); with
                        --verdict-only both are compared
"""
import argparse
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(pattern, psets=None, mode=None):
    rows = {}
    for f in sorted(glob.glob(pattern)):
        for r in csv.DictReader(open(f, newline="")):
            if psets and r.get("pset") not in psets:
                continue
            if mode and r.get("mode", "") != mode:
                continue
            k = (r["id"], r.get("mode", ""), r.get("rep", ""))
            rows[k] = (r["verdict"], r.get("reports_dedup", ""), r.get("report_ids", ""), r.get("notes", ""))
    return rows


def collapse(rows):
    """(id, mode, rep) rows -> (id, mode, '*') with (verdict, race-alone verdict, max reports, notes)."""
    sys.path.insert(0, HERE)
    import make_tables as mt
    per = {}
    for (i, m, _), v in rows.items():
        per.setdefault((i, m), []).append(v)
    out = {}
    for (i, m), vs in per.items():
        verds = [v[0] for v in vs]
        v = next((x for x in ("RACE", "CLEAN", "TIMEOUT") if x in verds), "ERROR")
        notes = ";".join(sorted({x[3] for x in vs if x[3]}))
        ra = mt.race_alone_verdict({"verdict": v, "notes": notes}) or "n/a"
        nrep = max((int(x[1]) for x in vs if str(x[1]).isdigit()), default=0)
        out[(i, m, "*")] = (v, ra, str(nrep), notes)
    return out


def main():
    ap = argparse.ArgumentParser(description="verdict diff of two sets of harness CSVs")
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--pset", default="")
    ap.add_argument("--mode", default="")
    ap.add_argument("--verdict-only", dest="verdict_only", action="store_true")
    ap.add_argument("--collapse", action="store_true")
    o = ap.parse_args()
    psets = set(o.pset.split(",")) if o.pset else None
    a, b = load(o.a, psets, o.mode or None), load(o.b, psets, o.mode or None)
    if o.collapse:
        a, b = collapse(a), collapse(b)
    # compared fields: (verdict, reports_dedup, report_ids), or with --collapse
    # (verdict, race-alone, reports); --verdict-only keeps the verdict(s) only
    n = (2 if o.collapse else 1) if o.verdict_only else 3
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diff = [(k, a[k], b[k]) for k in sorted(set(a) & set(b)) if a[k][:n] != b[k][:n]]
    print(f"A: {len(a)} rows  B: {len(b)} rows  common: {len(set(a) & set(b))}  "
          f"only-A: {len(only_a)}  only-B: {len(only_b)}  differing: {len(diff)}"
          + (f"  (fields compared: {'verdict, race-alone' if o.collapse else 'verdict'})"
             if o.verdict_only else ""))
    for k in only_a:
        print(f"  only A: {k} {a[k][:3]}")
    for k in only_b:
        print(f"  only B: {k} {b[k][:3]}")
    for k, va, vb in diff:
        print(f"  DIFF {k}\n     A: {va[:3]}  notes={va[3][:120]}\n     B: {vb[:3]}  notes={vb[3][:120]}")
    same = [k for k in set(a) & set(b) if a[k][:n] == b[k][:n]]
    print(f"identical verdict/report rows: {len(same)}")
    sys.exit(0 if not (only_a or only_b or diff) else 1)


if __name__ == "__main__":
    main()
