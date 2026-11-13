import numpy as np, sys
t = np.array(open(sys.argv[1]).read().split(), dtype=np.int64)
n = int(t[0]); body = t[1:1 + 2 * n].reshape(n, 2); st, deg = body[:, 0], body[:, 1]
src = int(t[1 + 2 * n]); m = int(t[2 + 2 * n]); e = t[3 + 2 * n:].reshape(-1, 2)
print("n", n, "m", m, "src", src, "edge pairs", e.shape, "cost uniq", np.unique(e[:, 1])[:5])
dst = e[:, 0]
print("deg min/max/mean", deg.min(), deg.max(), deg.mean(), "sum", deg.sum())
print("deg hist", np.bincount(deg).tolist())
node = np.repeat(np.arange(n), deg)
d = dst - node
print("dst min/max", dst.min(), dst.max(), "frac |dst-node|<1000:", np.mean(np.abs(d) < 1000), "dst mean/n", dst.mean() / n)
print("self-loop frac", np.mean(dst == node), "unique dst frac", len(np.unique(dst)) / n)
