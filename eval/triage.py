#!/usr/bin/env python3
"""Triage helper: summarize the deduped race reports in a driver detail JSON.

    python eval/inspect.py eval/detail/reduction__norace__small.json
    python eval/inspect.py A.json B.json   # also diffs the two report sets

Per-report line: space | race_type | dist | strength | hb_class | chain?
Totals cross space x hb_class and count reports that carry a static hb_chain
(these would be ORDERED in static-only mode — a fence-blind-engine false positive
when the program is race-free).
"""
import collections
import json
import sys


def load(p):
    return json.loads(open(p).read())


def key(r):
    a, b = sorted((r["ancient_pc"], r["current_pc"]))
    return (a, b, r["space"].split("/")[0])


def show(path):
    d = load(path)
    reps = d.get("dedup_reports", [])
    print(f"\n=== {path} ===  ({len(reps)} deduped reports)")
    by = collections.Counter()
    chain_ct = collections.Counter()
    for r in reps:
        has = "chain" if r.get("hb_chain") else "-"
        by[(r["space"].split("/")[0], r.get("hb_class"))] += 1
        chain_ct[(r.get("hb_class"), bool(r.get("hb_chain")))] += 1
        print(f"  {r['ancient_pc_hex']:>7}->{r['current_pc_hex']:<7} "
              f"{r['space']:<16} {r['race_type']:<4} d={r['observed_distance']:<5} "
              f"str={r['strength']:<5} {r.get('hb_class'):<10} {has} "
              f"{'/'.join(r['opcodes'])}")
    print("  totals (space,class):", dict(by))
    print("  (class, has_chain):", dict(chain_ct))
    with_chain = sum(1 for r in reps if r.get("hb_chain"))
    print(f"  reports with static hb_chain (would be ORDERED static-only): "
          f"{with_chain}/{len(reps)}")
    return {key(r) for r in reps}


def main():
    sets = [(p, show(p)) for p in sys.argv[1:]]
    if len(sets) == 2:
        (pa, a), (pb, b) = sets
        print(f"\n=== diff ===")
        print(f"  only in {pa}: {sorted(a - b)}")
        print(f"  only in {pb}: {sorted(b - a)}")
        print(f"  shared: {len(a & b)}")


if __name__ == "__main__":
    main()
