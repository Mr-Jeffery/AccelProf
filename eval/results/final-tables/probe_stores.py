#!/usr/bin/env python3
"""X3 probe: list the trace stores and the layout of an atomicCAS / particlefilter store entry."""
import os, json, sys
B = "/mnt/beegfs/fzheng4/cuvein_traces"
for d in sorted(os.listdir(B)):
    if "final" in d:
        print("STORE", d)
for st in ("final-2026-10-long", "final-2026-11-24h-vc", "final-2026-11-long"):
    for sub in ("P9-atomicCAS-cuda", "P7-particlefilter-cuda"):
        p = os.path.join(B, st, sub)
        if os.path.isdir(p):
            print("DIR", p)
            for r, ds, fs in os.walk(p):
                depth = r[len(p):].count("/")
                if depth <= 2:
                    print("  ", r[len(p):] or ".", len(fs), "files", sorted(fs)[:4])
