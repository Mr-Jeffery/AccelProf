#!/usr/bin/env python3
"""X1: the id list of the 5,400 s long pass (p_final_long.sh).

  .env/bin/python eval/baselines/setup/final_long_ids.py eval/results/final \
      > eval/baselines/setup/final_long_ids.txt

Every id of P1, P3, P4, P6, P7, P9 (never PI) with at least one vector-clock TIMEOUT rep in the
first pass's shard CSVs. "At least one rep" rather than the collapsed verdict: an id whose reps
are CLEAN, TIMEOUT, TIMEOUT finished once just under 1,200 s, and replacing all three reps by the
long pass keeps one cap per (id, mode) (parallel.py merge --override). The per-pset counts go to
stderr.
"""
import collections
import csv
import glob
import sys

PSETS = ("P1", "P3", "P4", "P6", "P7", "P9")


def main():
    src = sys.argv[1]
    ids, n = set(), collections.Counter()
    for f in sorted(glob.glob(f"{src}/baselines-cuvein-shard*.csv")):
        for r in csv.DictReader(open(f, newline="")):
            if r["pset"] in PSETS and r["mode"] == "vector-clock" and r["verdict"] == "TIMEOUT":
                if r["id"] not in ids:
                    n[r["pset"]] += 1
                ids.add(r["id"])
    for i in sorted(ids):
        print(i)
    print(f"{len(ids)} ids: " + ", ".join(f"{p} {n[p]}" for p in PSETS), file=sys.stderr)


if __name__ == "__main__":
    main()
