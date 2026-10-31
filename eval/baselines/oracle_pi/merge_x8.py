#!/usr/bin/env python3
"""X8: merge eval/x_logs/oracle-x8-{all590,sc99}-<graph>.csv -> eval/results/baselines-pi-oracle-x8.csv
(same schema as baselines-pi-oracle.csv; an all590 row wins over the sc99 row of the same id)."""
import csv, glob, os, collections
H = os.path.dirname(os.path.abspath(__file__)); L = f"{H}/../../x_logs"
F = ["id", "code", "graph", "label", "oracle", "pairs", "example", "notes"]
rows = {}
for pat in ("sc99", "all590*"):
    for p in sorted(glob.glob(f"{L}/oracle-x8-{pat}.csv" if "*" in pat else f"{L}/oracle-x8-{pat}-*.csv")):
        for r in csv.DictReader(open(p)):
            rows[r["id"]] = r
with open(f"{H}/../../results/baselines-pi-oracle-x8.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=F); w.writeheader()
    for i in sorted(rows):
        w.writerow({k: rows[i][k] for k in F})
print(len(rows), collections.Counter(r["oracle"] for r in rows.values()))
print(collections.Counter(r["graph"] for r in rows.values()))
