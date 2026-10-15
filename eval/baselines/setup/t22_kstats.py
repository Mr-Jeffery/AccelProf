#!/usr/bin/env python3
"""T22: print the sharded pass's statistics of kernel JSONs (hb_stats.hb_clock.sharded, the summed
buckets and sync clocks, the merged pair count) -- the evidence that a run used the sharded pass
and how its lanes spread over the shards.
  t22_kstats.py <kernel_N.json | dir>...
"""
import glob
import json
import os
import sys


def show(path):
    t = json.load(open(path))
    s = (t.get("hb_stats") or {}).get("hb_clock") or {}
    sh = s.get("sharded")
    lanes = sh.get("lanes") if sh else None
    bal = ""
    if lanes and sum(lanes):
        bal = f" lanes max/mean {max(lanes) / (sum(lanes) / len(lanes)):.2f}"
    print(f"{path}: events {t.get('hb_events_count')} lanes {t.get('hb_lanes_count')} "
          f"pairs {len(t.get('hb_sync_pass', []))} tv {t.get('tv_violation', '-')!r}")
    if sh:
        print(f"  sharded {sh['shards']} drain {sh.get('drain_s', float('nan')):.2f}s "
              f"route {sh['route_s']:.2f}s wait {sh['wait_s']:.2f}s bcast {sh.get('bcast')} "
              f"busy {[round(x, 2) for x in sh['busy_s']]} stall {[round(x, 2) for x in sh.get('stall_s', [])]}{bal}")
    if s:
        print(f"  buckets {s.get('buckets')} vs {s.get('vs')} sync_pairs {s.get('sync_pairs')}")


for a in sys.argv[1:]:
    for p in (sorted(glob.glob(os.path.join(a, "**", "kernel_*.json"), recursive=True))
              if os.path.isdir(a) else [a]):
        show(p)
