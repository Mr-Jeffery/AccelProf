#!/usr/bin/env python3
"""HiRace artifact `make table1` results (sqlite) -> eval/results/baselines-hirace-table1.csv.

The artifact's scripts/hirace_experiments.py stores one row per (code, graph) and tool
table (indigo = uninstrumented run + sequential comparison, memcheck with tool in
{memcheck, racecheck}, iguard, hirace) in results/hirace_correctness_results.sqlite3.
This dumps them unchanged (errors, time_ns) so the report reads a CSV, plus the label
by the artifact's own predicate (scripts/gen_table1.py): racy = "Bug" and not
"boundsBug"; boundsBug codes excluded.  No GPU.
"""
import csv
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = f"{HERE}/setup/tools/HiRace/results/hirace_correctness_results.sqlite3"
OUT = f"{os.path.dirname(os.path.dirname(HERE))}/eval/results/baselines-hirace-table1.csv"


def label(code):
    if "boundsBug" in code:
        return ""
    return "RACE" if "Bug" in code else "CLEAN"


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else DB
    if not os.path.exists(db):
        sys.exit(f"no table-1 database at {db} (run setup/p_hirace_table1.sh)")
    con = sqlite3.connect(db)
    n = 0
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "graph", "table", "tool", "threads_per_block", "number_of_blocks",
                    "errors", "time_ns", "label"])
        for tbl in ("indigo", "memcheck", "iguard", "hirace"):
            for code, graph, tool, tpb, nb, errs, t in con.execute(
                    f"SELECT code, graph, tool, threads_per_block, number_of_blocks, errors, time_ns FROM {tbl}"):
                code = code.replace("_hirace", "")
                w.writerow([code[:-3] if code.endswith(".cu") else code, graph[:-4] if graph.endswith(".egr") else graph,
                            tbl, tool, tpb, nb, errs, t, label(code)])
                n += 1
    print(f"{n} rows -> {OUT}")


if __name__ == "__main__":
    main()
