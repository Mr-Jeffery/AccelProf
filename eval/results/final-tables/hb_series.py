#!/usr/bin/env python3
"""X3: sample hb_stats memory terms along a store entry's kernel JSONs (read only, CPU).

usage: hb_series.py DIR [STEP]   -> one line per sampled kernel: index, mtime, hwm_kb, vc.bytes_est,
buckets.bytes, buckets.entries, buckets.locations, sharded shards (scalar-clock), plus first/last mtime.
"""
import json, os, re, sys

d = sys.argv[1]
step = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
ks = sorted(int(m.group(1)) for f in os.listdir(d) if (m := re.fullmatch(r"kernel_(\d+)\.json", f)))
print(f"DIR {d} nkernel_files={len(ks)} last_index={ks[-1] if ks else None}")
pick = sorted(set(ks[::step] + ks[-3:]))
for k in pick:
    p = os.path.join(d, f"kernel_{k}.json")
    try:
        j = json.load(open(p))
    except Exception as e:
        print(f"{k} unreadable {type(e).__name__} bytes={os.path.getsize(p)}"); continue
    s = j.get("hb_stats") or {}
    c = s.get("hb_clock") or {}
    b = c.get("buckets") or {}
    vc = c.get("vc") or {}
    sh = c.get("sharded") or {}
    print(json.dumps({"k": k, "mtime": int(os.path.getmtime(p)), "hwm_kb": s.get("hwm_kb"),
                      "vc_bytes_est": vc.get("bytes_est"), "vc_threads": vc.get("threads"),
                      "buckets_bytes": b.get("bytes"), "buckets_bytes_est": b.get("bytes_est"),
                      "buckets_entries": b.get("entries"), "buckets_locations": b.get("locations"),
                      "shards": sh.get("shards"), "sharded_keys": sorted(sh)[:12],
                      "events": (s.get("hb_events") or {}).get("count"),
                      "kernel": str(j.get("kernel"))[:60]}, sort_keys=True))
