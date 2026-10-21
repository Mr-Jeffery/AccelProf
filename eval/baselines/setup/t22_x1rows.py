#!/usr/bin/env python3
"""T22 step D: X1's rows of given programs from its results directories (read-only), with notes.
  t22_x1rows.py <results dir>... -- <id substring>...
"""
import csv
import glob
import sys

args = sys.argv[1:]
dirs, subs = args[:args.index("--")], args[args.index("--") + 1:]
for d in dirs:
    for f in sorted(glob.glob(f"{d}/*.csv")):
        for r in csv.DictReader(open(f)):
            if any(s in r["id"] for s in subs) and r.get("mode") == "scalar-clock":
                print(d.rstrip("/").split("/")[-1], r["id"], r["verdict"], r["reports_dedup"], r["wall_s"],
                      r["native_wall_s"], r["peak_mb"], "|", r["notes"][:200])
