#!/usr/bin/env python3
"""T5b: before/after table of the HB_STATS runs (setup/t5b_stats.sh ->
setup/t5b_stats/<label>-{main,t5b}.json, written by t5a_stats.py). Prints, per program and
runtime, the run (rc, wall, peak RSS, kernels) and, for the kernel whose hb_stats has the
largest vc, the main clock's layout; for a run with mid-kernel snapshots, the last one."""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = sys.argv[1] if len(sys.argv) > 1 else f"{HERE}/t5b_stats"


def gb(x):
    return f"{x / 1e9:.2f}" if isinstance(x, (int, float)) else "-"


for p in sorted(glob.glob(f"{D}/*.json")):
    d = json.load(open(p))
    lab = os.path.basename(p)[:-5]
    run = {k: d.get(k) for k in ("node", "rc", "timed_out", "wall_s", "peak_rss_mb", "engine_lib_sha16")}
    ks = [k for k in d.get("kernels", []) if (k.get("hb_stats") or {}).get("engine")]
    print(f"== {lab}: {run} kernels_with_stats={len(ks)}")
    if ks:
        k = max(ks, key=lambda k: k["hb_stats"]["engine"]["vc"].get("bytes_est", 0))
        s = k["hb_stats"]["engine"]
        print(f"   largest-vc kernel {k.get('file')}: vc={json.dumps(s['vc'])}")
        print(f"   released={json.dumps(s['released'])} buckets_bytes={gb(s['buckets']['bytes_est'])} GB "
              f"vs={json.dumps(s['vs'])} merge_memo={s.get('merge_memo')}")
        print(f"   hb_events={json.dumps(k['hb_stats'].get('hb_events'))} rss_kb={k['hb_stats'].get('rss_kb')} "
              f"hwm_kb={k['hb_stats'].get('hwm_kb')}")
    mids = d.get("mid_kernel") or []
    if mids:
        m = mids[-1]
        print(f"   {len(mids)} snapshots; last: {json.dumps(m)[:700]}")
    if not ks and not mids:
        print(f"   keys: {list(d)}")
