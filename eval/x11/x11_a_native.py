#!/usr/bin/env python3
"""X11 stage A: native wall time of the artifact's native binaries, 3 runs each (inside the container),
same cwd/args as the collector runs. python x11_a_native.py TREE OUT.csv"""
import csv, os, statistics, subprocess, sys, time
TREE, OUT = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(f"{TREE}/manifest.csv")))
with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "run1_s", "run2_s", "run3_s", "median_s", "rc"])
    for r in rows:
        d = os.path.dirname(r["exe"]); args = r["args"].split()
        ts, rcs = [], []
        for _ in range(3):
            t = time.perf_counter()
            p = subprocess.run([f"./{os.path.basename(r['exe'])}", *args], cwd=d, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=84600)
            ts.append(round(time.perf_counter() - t, 3)); rcs.append(p.returncode)
        w.writerow([r["id"], *ts, statistics.median(ts), max(rcs)]); f.flush()
        print(r["id"], ts, rcs, flush=True)
