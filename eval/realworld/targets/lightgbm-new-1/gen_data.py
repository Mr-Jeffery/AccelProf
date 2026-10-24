#!/usr/bin/env python3
# lightgbm-new-1 dataset: 1,000 rows x 6 float features, tab-separated, label in column 0 (LightGBM CLI default).
# Features 0-2: N(0,1).  Features 3-5: 70% exactly 5.0, otherwise N(0,3), so their most frequent bin is the bin of 5.0
# (not bin 0) -> CUDAHistogramConstructor marks them need_fix and FixHistogramKernel<<<3, 512>>> runs.
# Deterministic (random.Random(1)); standard library only.
import random, sys
out = sys.argv[1]
r = random.Random(1)
with open(out, "w") as f:
    for _ in range(1000):
        x = [r.gauss(0, 1) for _ in range(3)] + [5.0 if r.random() < 0.7 else r.gauss(0, 3) for _ in range(3)]
        y = x[0] + 0.5 * x[1] - 0.3 * x[3] + r.gauss(0, 0.1)
        f.write("\t".join(["%.6f" % y] + ["%.6f" % v for v in x]) + "\n")
