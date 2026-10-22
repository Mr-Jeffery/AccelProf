#!/usr/bin/env python3
"""T24: where can the warp-barrier assembly change anything? Per kernel JSON of a kept store (with
hb_events): syncwarp records, partial ones (active_mask != sync_mask), the instances they form
(per (block, warp, pc), completed when the arrived lanes cover sync_mask minus exited and absent
lanes, as HbClock), records whose sync_mask names exited or absent lanes (where the expected lanes
differ from sync_mask). A kernel with none of these replays identically before and after T24: every
syncwarp record takes the fast path and joins its sync_mask, as the per-record join did.
  t24_census.py --store <dir> --out <jsonl> [--shard i/n] [--max-gb 8]
"""
import argparse
import collections
import glob
import json
import os


def census(t):
    c = collections.Counter()
    btc = t["kernel"].get("block_thread_count") or 0
    gone, opened = {}, {}
    for e in sorted(t.get("hb_events", ()), key=lambda e: e["seq"]):
        b, w = e["block"], e["warp"]
        if e["type"] == "exit":
            gone[(b, w)] = gone.get((b, w), 0) | e["active_mask"]
            continue
        if e["type"] != "syncwarp":
            continue
        c["syncwarp records"] += 1
        sm, am = e["sync_mask"], e["active_mask"]
        first = 32 * w
        lanes = 0xFFFFFFFF if not btc or btc >= first + 32 else ((1 << (btc - first)) - 1 if btc > first else 0)
        exp = sm & ~gone.get((b, w), 0) & lanes
        if exp != sm:
            c["records naming exited or absent lanes"] += 1
        if am != sm:
            c["partial records"] += 1
        k = (b, w, e["pc"])
        if k not in opened:
            if am & exp == exp:
                continue
            opened[k] = 0
        opened[k] |= am & sm
        if opened[k] & exp == exp:
            c["diverged instances"] += 1
            del opened[k]
    c["open at end"] += len(opened)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", default="0/1")
    ap.add_argument("--max-gb", type=float, default=8.0)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.store, "*", "*", "*", "kernel_*.json")) +
                   glob.glob(os.path.join(a.store, "*", "*", "kernel_*.json")))
    si, sn = map(int, a.shard.split("/"))
    with open(a.out, "w") as out:
        for f in files[si::sn]:
            rel = os.path.relpath(f, a.store)
            size = os.path.getsize(f)
            if size > a.max_gb * 2**30:
                out.write(json.dumps({"file": rel, "skipped_bytes": size}) + "\n")
                continue
            with open(f) as fh:
                t = json.load(fh)
            if not t.get("hb_events"):
                out.write(json.dumps({"file": rel, "no_events": True}) + "\n")
                continue
            out.write(json.dumps({"file": rel, **census(t)}) + "\n")
            out.flush()


if __name__ == "__main__":
    main()
