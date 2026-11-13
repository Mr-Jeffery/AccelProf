#!/usr/bin/env python
"""X13: a Rodinia-format BFS graph (HeCBench bfs-cuda input) with the statistics of graph1MW_6.txt
(measured with x13_gstat.py: degree = 2 + Poisson(4), mean 6, targets: one third within +-1000 ids of
the node, the rest uniform, no self loops, edge cost 1..5) at a chosen node count.
  gen_graph.py N out.txt [seed]
"""
import sys
import numpy as np

n = int(sys.argv[1])
out = sys.argv[2]
rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 13)
deg = 2 + rng.poisson(4, n)
start = np.concatenate(([0], np.cumsum(deg)[:-1]))
m = int(deg.sum())
node = np.repeat(np.arange(n), deg)
local = rng.random(m) < 1 / 3
dst = np.where(local, node + rng.integers(-1000, 1001, m), rng.integers(0, n, m))
dst = np.clip(dst, 0, n - 1)
bad = dst == node
dst[bad] = (dst[bad] + 1) % n
cost = rng.integers(1, 6, m)
with open(out, "w") as f:
    f.write(f"{n}\n")
    f.write("\n".join(f"{s} {d}" for s, d in zip(start.tolist(), deg.tolist())) + "\n")
    f.write("0\n")
    f.write(f"{m}\n")
    f.write("\n".join(f"{d} {c}" for d, c in zip(dst.tolist(), cost.tolist())) + "\n")
print("wrote", out, "nodes", n, "edges", m)
