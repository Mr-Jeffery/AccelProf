#!/usr/bin/env python3
"""X5 byte pairs: print the hb_events records of one kernel launch at chosen pcs (read only).

  x5b_events.py <kernel_N.json> <pc,pc,...> [--block B] [--warp W] [--max N]

Prints, in trace order, every record whose pc is in the list (memory records with their
lane -> address map, sync records with their masks), plus a census of record types by pc
over the whole launch. A record type the census shows at a pc the CFG prints as NOP is what
the Sanitizer patched there. Nothing is written.
"""
import argparse
import collections
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kj")
    ap.add_argument("pcs")
    ap.add_argument("--block", type=int)
    ap.add_argument("--warp", type=int)
    ap.add_argument("--max", type=int, default=60)
    a = ap.parse_args()
    pcs = {int(x, 16) for x in a.pcs.split(",")}
    t = json.load(open(a.kj))
    ev = t.get("hb_events")
    k = t["kernel"]
    print(f"kernel {k['kernel_name']} grid {k['grid_dim']} block {k['block_dim']}; "
          f"hb_events {'absent' if ev is None else len(ev)}")
    if not ev:
        return
    census = collections.Counter()
    for e in ev:
        census[(e.get("type"), e.get("pc"), e.get("space"))] += 1
    print("record census by (type, pc, space), sync/exit records and the listed pcs:")
    for (ty, pc, sp), n in sorted(census.items(), key=lambda kv: (kv[0][1] or 0, str(kv[0][0]))):
        if ty not in ("read", "write", "atomic") or pc in pcs:
            print(f"   {str(ty):10s} {hex(pc) if pc is not None else None:>8} {str(sp):7s} {n}")
    shown = 0
    for seq, e in enumerate(ev):
        if e.get("pc") not in pcs:
            continue
        if a.block is not None and e.get("block") != a.block:
            continue
        if a.warp is not None and e.get("warp") != a.warp:
            continue
        keep = {x: e[x] for x in e if x != "lanes"}
        lanes = e.get("lanes")
        if lanes is not None:
            keep["lanes"] = [(ln.get("lane"), ln.get("addr")) for ln in lanes]
        print(f"   seq {seq}: {keep}")
        shown += 1
        if shown >= a.max:
            break


if __name__ == "__main__":
    main()
