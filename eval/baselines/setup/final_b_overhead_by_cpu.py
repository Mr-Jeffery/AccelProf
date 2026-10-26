#!/usr/bin/env python3
"""cuVein slowdown (median wall of the finished reps / the same rows' own native wall, one node) per
suite, mode and host CPU, X1 against X1b; and the paired change over the (id, mode) keys whose rows ran
on the same CPU type in both recordings. Host CPUs from FINAL_SWEEP.md / FINAL_SWEEP_B.md section 0.

  overhead_by_cpu.py <X1 merged baselines-cuvein.csv> <X1b merged baselines-cuvein.csv>
"""
import collections
import csv
import math
import re
import statistics
import sys

CPU = {}
for n in (0, 1, 51, 52, 56, 58):
    CPU[f"c{n}"] = "9115 (Zen 5)"
for n in range(60, 67):
    CPU[f"c{n}"] = "8124P (Zen 4)"
for n in [24] + list(range(39, 45)) + list(range(73, 80)):
    CPU[f"c{n}"] = "7302P (Zen 2)"


def load(path):
    per = collections.defaultdict(list)
    for r in csv.DictReader(open(path, newline="")):
        if r["tool"] != "cuvein":
            continue
        per[(r["id"], r["mode"])].append(r)
    out = {}
    for k, rs in per.items():
        fin = [r for r in rs if r["verdict"] in ("RACE", "CLEAN")]
        if not fin:
            continue
        try:
            wall = statistics.median(float(r["wall_s"]) for r in fin)
            nat = min(float(r["native_wall_s"]) for r in rs if r["native_wall_s"])
        except ValueError:
            continue
        m = re.search(r"node=(c\d+)", rs[0]["notes"])
        node = m.group(1) if m else "?"
        out[k] = (rs[0]["pset"], wall / nat, CPU.get(node, "?"))
    return out


def gm(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else float("nan")


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    cpus = ["9115 (Zen 5)", "8124P (Zen 4)", "7302P (Zen 2)"]
    print("Slowdown geomean× (n) per host CPU, X1 → X1b:\n")
    print("| suite | mode | " + " | ".join(cpus) + " | paired, same CPU type: median X1b/X1 (n) |")
    print("|---|---|" + "---|" * (len(cpus) + 1))
    for s in sorted({v[0] for v in a.values()}):
        for m in ("vector-clock", "scalar-clock"):
            cells = []
            for c in cpus:
                x = [v[1] for k, v in a.items() if k[1] == m and v[0] == s and v[2] == c]
                y = [v[1] for k, v in b.items() if k[1] == m and v[0] == s and v[2] == c]
                cells.append(f"{gm(x):.1f} ({len(x)}) → {gm(y):.1f} ({len(y)})" if x or y else "—")
            pr = [b[k][1] / a[k][1] for k in a if k in b and k[1] == m and a[k][0] == s and a[k][2] == b[k][2] != "?"]
            pc = f"{statistics.median(pr):.2f} ({len(pr)})" if pr else "—"
            print(f"| {s} | {m} | " + " | ".join(cells) + f" | {pc} |")


if __name__ == "__main__":
    main()
