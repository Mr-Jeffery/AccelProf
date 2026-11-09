#!/usr/bin/env python3
"""T21c (from T21b's mk_manifest_t21b.py): the candidate rows (ids with new-/open-) of eval/realworld/manifest.csv -> eval/realworld/manifest_t21c.csv.
llmc-new-3 (cmd `attention_backward 7 && attention_backward 8`) becomes two rows of the same target: llmc-new-3-buggy (args 7) and llmc-new-3-k8-buggy (args 8). Every row whose artifact was relinked with
--cudart shared (all but llamacpp-*, which already load libcudart.so.13) points at /mnt/beegfs/fzheng4/realworld_t21c/build.
Run on the login node (text only)."""
import csv, sys
src = "/home/fzheng4/wt-t21c/eval/realworld/manifest.csv"
dst = "/home/fzheng4/wt-t21c/eval/realworld/manifest_t21c.csv"
OLD, NEW = "/mnt/beegfs/fzheng4/realworld/build/", "/mnt/beegfs/fzheng4/realworld_t21c/build/"
rows = list(csv.DictReader(open(src, newline="")))
rows = [r for r in rows if "new-" in r["id"] or "open-" in r["id"]]
out = []
for r in rows:
    if r["id"] == "llmc-new-3-buggy":
        for k, rid in (("7", "llmc-new-3-buggy"), ("8", "llmc-new-3-k8-buggy")):
            q = dict(r); q["id"] = rid; q["args"] = k; q["needs_wrapper"] = "0"; q["cmd"] = r["exe"] + " " + k; out.append(q)
    else:
        out.append(r)
rows = out
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
