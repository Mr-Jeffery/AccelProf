#!/usr/bin/env python3
"""T3b step 4: per-kernel summary of a fresh P9-crs-cuda recording (both modes) -- exit
records, the hb_exits marker, the engine's tv_violation and hb_races, and, per kernel, the
offline barrier-only pass with its TV-barrier-pending-at-end check (what scalar-clock mode
runs). Streams nothing: each kernel JSON is loaded once (~320 MB for the largest).
  t3b_crs_summary.py <store>/P9-crs-cuda  -> TSV on stdout + a totals line per mode"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "python"))
import sync_dominance as sd  # noqa: E402

root = sys.argv[1]
print("mode\tkernel\tname\tevents\texit_records\texited_threads\thb_exits\ttv_violation\t"
      "hb_races\tsync_only_pairs\toffline_pairs\toffline_tv")
for mode in ("vector-clock", "scalar-clock"):
    files = sorted(glob.glob(os.path.join(root, mode, "**", "kernel_*.json"), recursive=True),
                   key=lambda f: int(os.path.basename(f)[7:-5]))
    tot = dict(kernels=0, tv=0, races=0, offline_pairs=0, offline_tv=0, no_marker=0)
    for f in files:
        j = json.load(open(f))
        ev = j.get("hb_events") or []
        ex = [e for e in ev if e["type"] == "exit"]
        tv = []
        off = sd.barrier_only_pairs(j, {}, {}, tv_out=tv) if ev else None
        n_races = len(j["hb_races"]) if "hb_races" in j else "-"
        print(f"{mode}\t{os.path.basename(f)}\t{j['kernel']['kernel_name'][:40]}\t{len(ev)}\t"
              f"{len(ex)}\t{sum(bin(e['active_mask']).count('1') for e in ex)}\t"
              f"{j.get('hb_exits')}\t{j.get('tv_violation')}\t{n_races}\t"
              f"{len(j['hb_races_sync_only']) if 'hb_races_sync_only' in j else '-'}\t"
              f"{len(off) if off is not None else '-'}\t{tv[0] if tv else None}")
        tot["kernels"] += 1
        tot["tv"] += j.get("tv_violation") is not None
        tot["races"] += n_races if isinstance(n_races, int) else 0
        tot["offline_pairs"] += len(off or {})
        tot["offline_tv"] += bool(tv)
        tot["no_marker"] += not j.get("hb_exits")
        del j, ev
    print(f"# {mode}: {tot}")
