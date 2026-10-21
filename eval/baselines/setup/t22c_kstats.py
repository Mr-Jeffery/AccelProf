#!/usr/bin/env python3
"""T22 cont.: per kernel JSON of a run's store, in launch order -- its write time (mtime, s since the
epoch) and the time since the previous kernel's write (the launch's analysis time when launches are
back to back), events, kernel name, hb_sync_pass pairs and summed counts, and HB_STATS' buckets
(locations, entries, bytes). A kernel being written when a cap killed the run is reported as such.
  t22c_kstats.py <store dir | kernel_N.json>...
"""
import glob
import json
import os
import re
import sys


def kernels(arg):
    if os.path.isfile(arg):
        return [arg]
    ps = glob.glob(os.path.join(arg, "**", "kernel_*.json"), recursive=True)
    return sorted(ps, key=lambda p: (os.path.dirname(p), int(re.search(r"kernel_(\d+)", p).group(1))))


for a in sys.argv[1:]:
    prev = None
    print(f"== {a}")
    for p in kernels(a):
        mt = os.path.getmtime(p)
        d = f"{mt - prev:9.1f}" if prev is not None else "        -"
        prev = mt
        try:
            t = json.load(open(p))
        except json.JSONDecodeError:
            print(f"  {os.path.basename(p):16s} {mt:.1f} {d}  not JSON ({os.path.getsize(p)} bytes)")
            continue
        b = ((t.get("hb_stats") or {}).get("hb_clock") or {}).get("buckets") or {}
        sp = t.get("hb_sync_pass") or []
        name = (t.get("kernel") or {}).get("kernel_name", "?")
        print(f"  {os.path.basename(p):16s} {mt:.1f} {d}  events {t.get('hb_events_count')} "
              f"{name[:40]:40s} pairs {len(sp)} count {sum(r[2] for r in sp)} "
              f"locs {b.get('locations')} entries {b.get('entries')} bytes {b.get('bytes')}")
