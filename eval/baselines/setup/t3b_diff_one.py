#!/usr/bin/env python3
"""T3b: where two kernel dumps (main vs T3b, exit records filtered) differ -- the top-level
keys, and for hb_events the first differing record and the per-(block, warp) record order.
  t3b_diff_one.py <kernel A.json> <kernel B.json>"""
import json
import sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])
for k in sorted(set(a) | set(b)):
    if a.get(k) != b.get(k):
        va, vb = a.get(k), b.get(k)
        print(f"key {k}: differs ({type(va).__name__} len {len(va) if hasattr(va, '__len__') else '-'}"
              f" vs {type(vb).__name__} len {len(vb) if hasattr(vb, '__len__') else '-'})")
ea, eb = a.get("hb_events", []), b.get("hb_events", [])
strip = lambda e: {k: v for k, v in e.items() if k not in ("seq",)}
for i, (x, y) in enumerate(zip(ea, eb)):
    if strip(x) != strip(y):
        print(f"first hb_events difference at index {i}:\n  A {json.dumps(x)[:300]}\n  B {json.dumps(y)[:300]}")
        break
order = lambda ev: [(e["block"], e["warp"], e["type"], e["pc"]) for e in ev]
print("same multiset of (block, warp, type, pc):", sorted(order(ea)) == sorted(order(eb)))
print("A block order:", [e["block"] for e in ea if e["type"] == "atomic"][:12])
print("B block order:", [e["block"] for e in eb if e["type"] == "atomic"][:12])
for k in ("hb_races", "hb_races_sync_only", "tv_violation"):
    print(k, "A:", json.dumps(a.get(k))[:200], "| B:", json.dumps(b.get(k))[:200])
