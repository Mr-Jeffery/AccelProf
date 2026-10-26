#!/usr/bin/env python3
"""X3 (b) atomicCAS: where hb_stats.hwm_kb steps along a store entry's kernels, and what the accounted terms
(vc.bytes_est, buckets.bytes, buckets.entries) are at those kernels (read only, CPU).

usage: hwm_changes.py DIR [DIR ...]
Prints, per DIR: number of kernel JSONs read, the min / max over kernels of vc.bytes_est, buckets.bytes,
buckets.entries, and every kernel index where hwm_kb differs from the previous kernel's.
"""
import json, os, re, sys

for d in sys.argv[1:]:
    ks = sorted(int(m.group(1)) for f in os.listdir(d) if (m := re.fullmatch(r"kernel_(\d+)\.json", f)))
    prev = None
    lo = {}
    hi = {}
    changes = []
    bad = 0
    for k in ks:
        try:
            j = json.load(open(os.path.join(d, f"kernel_{k}.json")))
        except Exception:
            bad += 1
            continue
        s = j.get("hb_stats") or {}
        c = s.get("hb_clock") or {}
        v = {"vc_bytes_est": (c.get("vc") or {}).get("bytes_est"), "buckets_bytes": (c.get("buckets") or {}).get("bytes"),
             "buckets_entries": (c.get("buckets") or {}).get("entries"), "hwm_kb": s.get("hwm_kb"), "rss_kb": s.get("rss_kb")}
        for n, x in v.items():
            if x is None:
                continue
            lo[n] = min(lo.get(n, x), x)
            hi[n] = max(hi.get(n, x), x)
        if prev is not None and v["hwm_kb"] != prev["hwm_kb"]:
            changes.append((k, prev["hwm_kb"], v["hwm_kb"], v["buckets_entries"], (j.get("hb_events") or {}).get("count") if False else s.get("hb_events", {}).get("count")))
        prev = v
    print(f"DIR {d}\n  kernel JSONs listed {len(ks)}, unreadable {bad}")
    for n in ("vc_bytes_est", "buckets_bytes", "buckets_entries", "hwm_kb", "rss_kb"):
        print(f"  {n}: min {lo.get(n)} max {hi.get(n)}")
    print(f"  hwm_kb steps (kernel, from, to, buckets_entries at that kernel, events): {len(changes)}")
    for ch in changes[:40]:
        print("   ", ch)
