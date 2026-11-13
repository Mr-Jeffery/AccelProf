#!/usr/bin/env python
"""X13: is the top segment of bfs's top shard d_over's? Reads a malloc-logged run (x13_sweep2.sh MALLOC=1):
DIR/malloc.txt (cudaMalloc ptr size, in bfs.cu's order: d_graph_nodes, d_graph_edges, d_graph_mask,
d_updating_graph_mask, d_graph_visited, d_cost, d_over) and DIR/shards/shards_*.json.
  x13_bfs_over.py DIR
"""
import glob, json, sys
from collections import defaultdict
d = sys.argv[1]
names = ["d_graph_nodes", "d_graph_edges", "d_graph_mask", "d_updating_graph_mask", "d_graph_visited", "d_cost", "d_over"]
al = [(int(l.split()[0], 16), int(l.split()[1])) for l in open(f"{d}/malloc.txt") if l.strip()]
assert len(al) == len(names), al
def owner(addr):
    for (p, n), nm in zip(al, names):
        if p <= addr < p + n:
            return nm
    return "other"
over = al[-1][0]
print("allocations:", ", ".join(f"{nm} {p:#x}+{n}" for (p, n), nm in zip(al, names)))
print("d_over", hex(over), "segment", hex(over >> 7 << 7))
for pas, pat in (("pcdep", "shards_[0-9]*.json"), ("sync", "shards_sync_[0-9]*.json")):
    files = glob.glob(f"{d}/shards/{pat}")
    if not files:
        continue
    ks = [json.load(open(f)) for f in files]
    n = ks[0]["shards"]
    lane = [sum(k["lane_records"][i] for k in ks) for i in range(n)]
    tot = sum(lane)
    ti = max(range(n), key=lambda i: lane[i])
    agg = defaultdict(int); kcount = defaultdict(int)
    for k in ks:
        for i, t in enumerate(k["top_segment_per_shard"]):
            if t and t["space"] == "global":
                agg[(i, t["offset"])] += t["lanes"]; kcount[(i, t["offset"])] += 1
    print(f"-- {pas}: {len(ks)} kernels, lane-records {tot:,}; top shard {ti} with {lane[ti]:,} ({100*lane[ti]/tot:.2f} %)")
    top = sorted(((v, k) for k, v in agg.items() if k[0] == ti), reverse=True)[:3]
    for v, (i, off) in top:
        print(f"   shard {i} segment {off:#x} ({owner(off)}): {v:,} lanes over {kcount[(i, off)]} kernels where it is the shard's top = {100*v/lane[ti]:.2f} % of the shard, {100*v/tot:.2f} % of all")
    ov = [(v, k) for k, v in agg.items() if (k[1] >> 7) == (over >> 7)]
    for v, (i, off) in ov:
        print(f"   d_over's segment {off:#x} on shard {i}: {v:,} lanes over {kcount[(i, off)]} kernels where it is that shard's top segment = {100*v/lane[i]:.2f} % of shard {i}, {100*v/tot:.2f} % of all lane-records; shard {i} has {100*lane[i]/tot:.2f} % of all; top shard is {ti}")
    if not ov:
        print("   d_over's segment is not the top segment of any shard in any kernel")
