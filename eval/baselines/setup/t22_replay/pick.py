#!/usr/bin/env python3
"""T22 cross-N: pick kernels of a recorded store for the replay comparison -- kernels whose
hb_sync_pass is non-empty (so pair counts, distances and first pcs are compared), the largest
by record count, one per program, below a size limit.

  pick.py <store> [--n 3] [--max-gb 3] -> "<id>/scalar-clock/kernel_K.json ..." on stdout
"""
import glob
import json
import os
import sys


def main(store, n=3, max_gb=3.0):
    cands = []
    for kj in glob.glob(f"{store}/*/scalar-clock/kernel_*.json"):
        if os.path.getsize(kj) > max_gb * 2 ** 30:
            continue
        t = json.load(open(kj))
        if t.get("hb_sync_pass") and t.get("hb_events"):
            cands.append((t["hb_events_count"], kj))
    cands.sort(reverse=True)
    out, seen = [], set()
    for _, kj in cands:
        pid = kj[len(store) + 1:].split("/")[0]
        if pid in seen:
            continue
        seen.add(pid)
        out.append(kj[len(store) + 1:])
        if len(out) == n:
            break
    print(" ".join(out))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], int(a[a.index("--n") + 1]) if "--n" in a else 3,
         float(a[a.index("--max-gb") + 1]) if "--max-gb" in a else 3.0)
