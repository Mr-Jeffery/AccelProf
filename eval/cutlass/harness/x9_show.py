#!/usr/bin/env python3
"""X9: summarize one pairs JSON: per kernel and status, and the pairs grouped by (innermost file:line pair, class)."""
import json, os, sys, re
from collections import Counter, defaultdict
d = json.load(open(sys.argv[1]))
def short(k):
    m = re.match(r"_ZN7cutlass(\d+)", k)
    return k[:90]
def fr(f):
    if not f: return "?"
    return " <- ".join(f"{os.path.basename(x['file'])}:{x['line']}" for x in f[:3])
print("kernels:", {k.split('::')[1][:70]: v for k, v in d["kernels"].items()})
print("status:", d["status_counts"], "on:", d["on"], "off:", d["off"])
g = defaultdict(list)
for p in d["pairs"]:
    cls = ",".join(sorted(v for v in (p["off"] or p["on"])["verdicts"] if v in ("RACE", "SC")))
    fa = p["frames_a"][0] if p["frames_a"] else None; fb = p["frames_b"][0] if p["frames_b"] else None
    key = (p["kernel"][:60], p["status"], p["space"], cls,
           f"{os.path.basename(fa['file'])}:{fa['line']}" if fa else "?", f"{os.path.basename(fb['file'])}:{fb['line']}" if fb else "?")
    g[key].append(p)
for k, ps in sorted(g.items(), key=lambda x: -len(x[1])):
    p = ps[0]; e = p["off"] or p["on"]
    print(f"{len(ps):4d} {k[1]:15s} {k[2]:7s} {k[3]:4s} {k[4]} x {k[5]}  rt={e['rt']} hb_on={(p['on'] or {}).get('hb')} n={e['n']}")
    print(f"      a: {p['sass_a']}  [{fr(p['frames_a'])}]")
    print(f"      b: {p['sass_b']}  [{fr(p['frames_b'])}]")
    print(f"      kernel: {p['kernel'][:160]}")
