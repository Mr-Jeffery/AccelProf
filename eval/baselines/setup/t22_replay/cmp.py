#!/usr/bin/env python3
"""T22 replay, step 3: compare the scalar-clock aggregates of one trace across shard counts.

  cmp.py [--le] <recorded kernel_N.json> <replay kernel json, N=a> [<replay kernel json, N=b> ...]

Fields: hb_sync_pass (sorted rows: [pc_lo, pc_hi, count, dist, first_pc, second_pc]),
hb_rmw_points, tv_violation (absent = none), hb_events_count, hb_lanes_count. The recorded
file is the reference (its run's own aggregates); every replay must equal it field for field.
--le (T22 cont.: the reference is the pass before Fix 2, a full scan): hb_sync_pass rows must
have the same (pc_lo, pc_hi, dist, first_pc, second_pc) and a count with 1 <= count <= the
reference's; every other field equal. The summed counts are printed.
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


def sync_le(x, r):
    """x's rows equal r's but for the count, 1 <= x <= r."""
    if x is None or r is None:
        return x == r
    xr = {(a, b, d, f, s): n for a, b, n, d, f, s in x}
    rr = {(a, b, d, f, s): n for a, b, n, d, f, s in r}
    return len(xr) == len(x) and len(rr) == len(r) and set(xr) == set(rr) \
        and all(1 <= xr[k] <= rr[k] for k in xr)


def total(rows):
    return sum(row[2] for row in rows or ())


def main(*argv):
    le = argv[0] == "--le"
    ref, *others = argv[1:] if le else argv
    r = key(json.load(open(ref)))
    bad = 0
    print(f"ref {ref}: {len(r['hb_sync_pass'] or [])} pairs, "
          f"{len(r['hb_rmw_points']['release']) if r['hb_rmw_points'] else 0} rmw-point pcs, "
          f"events {r['hb_events_count']}, tv {r['tv_violation']!r}"
          + (f", count {total(r['hb_sync_pass'])}" if le else ""))
    for o in others:
        x = key(json.load(open(o)))
        diff = [f for f in FIELDS
                if not (sync_le(x[f], r[f]) if le and f == "hb_sync_pass" else x[f] == r[f])]
        bad += bool(diff)
        cnt = f" (count {total(x['hb_sync_pass'])})" if le else ""
        print(f"  {'EQUAL' if not diff else 'DIFF ' + ','.join(diff)}{cnt}  {o}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(*sys.argv[1:])
