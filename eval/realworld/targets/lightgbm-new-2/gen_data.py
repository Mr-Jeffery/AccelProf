#!/usr/bin/env python3
# lightgbm-new-2 datasets: train.tsv (1,000 rows) and valid.tsv (5,000 rows) x 6 N(0,1) float features, label in column 0,
# plus valid.tsv.weight (one weight per validation row, uniform(0.5,1.5)); the CLI picks up <data>.weight automatically, so the
# validation Dataset is weighted and the l2 metric runs EvalKernel<..., USE_WEIGHTS=true> <<<5, 1024>>> (blocks 0-3 full).
# Deterministic (random.Random(2)); standard library only.
import random, sys
d = sys.argv[1]
r = random.Random(2)
def rows(n, path, wpath=None):
    with open(path, "w") as f, (open(wpath, "w") if wpath else open("/dev/null", "w")) as w:
        for _ in range(n):
            x = [r.gauss(0, 1) for _ in range(6)]
            y = x[0] + 0.5 * x[1] - 0.3 * x[3] + r.gauss(0, 0.1)
            f.write("\t".join(["%.6f" % y] + ["%.6f" % v for v in x]) + "\n")
            if wpath: w.write("%.6f\n" % r.uniform(0.5, 1.5))
rows(1000, d + "/train.tsv")
rows(5000, d + "/valid.tsv", d + "/valid.tsv.weight")
