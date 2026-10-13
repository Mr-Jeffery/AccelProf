#!/usr/bin/env python3
"""T4: why the sync instance is slow on a program the dump-only scalar-clock mode finished.
Procedure Check walks, for every lane access, every OTHER thread's bucket entries on the
location (one entry per (thread, key); R-R pairs and whole grid-scope RMW groups are skipped).
On a location that N threads touch with a conflicting key the walk is O(N) per access, so the
run is O(sum over accesses of the location's thread count). Over a kept dump's hb_events
(streamed, one record per line) this script reports, per kernel: lane-accesses, locations,
the walk estimate (sum over memory lane-accesses of the number of distinct other threads
that wrote or RMW'd the location before, or read it before when the access is a write/RMW),
and the hottest locations (distinct threads, accesses).

    .env/bin/python eval/baselines/setup/t4_hotloc.py <kernel_N.json> [...]
"""
import json
import sys


def stream(path):
    """(header dict, iterator over hb_events records) of a kernel JSON written by the tool."""
    f = open(path, "rb")
    head = []
    for line in f:
        if line.startswith(b'  "hb_events": ['):
            break
        if line.startswith(b'  "nodes": ['):
            # skip nodes/edges, which can be long: read until hb_events
            continue
        head.append(line)

    def events():
        for ln in f:
            s = ln.strip()
            if s == b"]" or s.startswith(b"],") or s == b"],":
                return
            if s.endswith(b","):
                s = s[:-1]
            if s.startswith(b"{"):
                yield json.loads(s)

    return events()


def main(paths):
    for p in paths:
        locs = {}           # loc -> [writers set, readers set, accesses]
        walk = lanes = 0
        for e in stream(p):
            if "lanes" not in e or e.get("space") == "local":
                continue
            typ = e["type"]
            blk = e["block"]
            for ln in e["lanes"]:
                lanes += 1
                t = (blk << 10) | (e["warp"] << 5) | ln["lane"]
                key = (e["space"], blk, ln["addr"]) if e["space"] == "shared" else (e["space"], ln["addr"])
                st = locs.get(key)
                if st is None:
                    st = locs[key] = [set(), set(), 0]
                st[2] += 1
                w, r, _ = st
                if typ == "read":
                    walk += len(w) - (t in w)
                    r.add(t)
                else:
                    walk += len(w) - (t in w) + len(r) - (t in r)
                    w.add(t)
        hot = sorted(locs.items(), key=lambda kv: -(len(kv[1][0]) + len(kv[1][1])))[:8]
        print(f"{p}: lane-accesses {lanes:,}, locations {len(locs):,}, walk estimate {walk:,} "
              f"({walk / max(lanes, 1):.1f} entries per lane-access)")
        for key, (w, r, n) in hot:
            print(f"   {key[0]} addr {key[-1]:#x}: writers/RMW {len(w):,}, readers {len(r):,}, accesses {n:,}")


if __name__ == "__main__":
    main(sys.argv[1:])
