#!/usr/bin/env python3
"""C6b step 2: append ;anode=<host> (the node the offline analysis ran on) to the notes of every row of a shard CSV.
usage: c6b_anode.py <csv> <host>"""
import csv, sys
p, host = sys.argv[1], sys.argv[2]
with open(p, newline="") as fh:
    rd = csv.DictReader(fh); rows = list(rd); fields = rd.fieldnames
for r in rows:
    r["notes"] = (r["notes"] + ";" if r["notes"] else "") + f"anode={host}"
with open(p, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
print(f"anode={host} appended to {len(rows)} rows of {p}")
