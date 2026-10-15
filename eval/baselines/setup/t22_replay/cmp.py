#!/usr/bin/env python3
"""T22 replay, step 3: compare the scalar-clock aggregates of one trace across shard counts.

  cmp.py <recorded kernel_N.json> <replay kernel json, N=a> [<replay kernel json, N=b> ...]

Fields: hb_sync_pass (sorted rows: [pc_lo, pc_hi, count, dist, first_pc, second_pc]),
hb_rmw_points, tv_violation (absent = none), hb_events_count, hb_lanes_count. The recorded
file is the reference (its run's own aggregates); every replay must equal it field for field.
Prints one line per file and exits 1 on any difference.
"""
import json
import sys

FIELDS = ("hb_sync_pass", "hb_rmw_points", "tv_violation", "hb_events_count", "hb_lanes_count")


def key(t):
    out = {}
    for f in FIELDS:
        v = t.get(f)
        if f == "hb_sync_pass" and v is not None:
            v = sorted(map(tuple, v))
        out[f] = v
    return out


def main(ref, *others):
    r = key(json.load(open(ref)))
    bad = 0
    print(f"ref {ref}: {len(r['hb_sync_pass'] or [])} pairs, "
          f"{len(r['hb_rmw_points']['release']) if r['hb_rmw_points'] else 0} rmw-point pcs, "
          f"events {r['hb_events_count']}, tv {r['tv_violation']!r}")
    for o in others:
        x = key(json.load(open(o)))
        diff = [f for f in FIELDS if x[f] != r[f]]
        bad += bool(diff)
        print(f"  {'EQUAL' if not diff else 'DIFF ' + ','.join(diff)}  {o}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(*sys.argv[1:])
