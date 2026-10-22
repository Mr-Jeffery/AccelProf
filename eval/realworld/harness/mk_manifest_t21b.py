#!/usr/bin/env python3
"""T21b: eval/realworld/manifest.csv -> eval/realworld/manifest_t21b.csv. Every row whose artifact was relinked with
--cudart shared (all but llamacpp-*, which already load libcudart.so.13) points at /mnt/beegfs/fzheng4/realworld_t21b/build.
Run on the login node (text only)."""
import csv, sys
src = "/home/fzheng4/wt-t21b/eval/realworld/manifest.csv"
dst = "/home/fzheng4/wt-t21b/eval/realworld/manifest_t21b.csv"
OLD, NEW = "/mnt/beegfs/fzheng4/realworld/build/", "/mnt/beegfs/fzheng4/realworld_t21b/build/"
rows = list(csv.DictReader(open(src, newline="")))
n = 0
with open(dst, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    for r in rows:
        if not r["target"].startswith("llamacpp-"):
            for k, v in r.items():
                if OLD in v:
                    r[k] = v.replace(OLD, NEW)
            n += 1
        if r["target"].startswith("llamacpp-"):
            r["args"] = r["args"].replace("'", "")   # parallel.py splits args on whitespace (no shell): the quotes would reach -p literally
        w.writerow(r)
print(f"{len(rows)} rows, {n} repointed to {NEW}")
