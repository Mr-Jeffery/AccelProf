#!/usr/bin/env python3
"""cuVein slowdown per suite and mode, X1 against X1b, two ways:
  shared  = make_tables.py's rule: tool wall / the id's native wall, the minimum over every runner
            that timed our build (cuVein, iGUARD, the sanitizer runners); this is what §4/§4a/summary show;
  own     = tool wall / the native wall in cuVein's own rows of that (id, mode): same node, same job.
Finished runs only (RACE/CLEAN), as the tables. Also: in how many ids the shared native came from a
runner other than cuVein, and how cuVein's own native walls moved between the two runs.

  overhead_check.py <X1 sandbox> <X1b sandbox>      (the sandboxes of p_final_b_tables.sh)
"""
import importlib.util
import math
import statistics
import sys


def load(sb):
    spec = importlib.util.spec_from_file_location(f"mt_{abs(hash(sb))}", f"{sb}/eval/baselines/make_tables.py")
    mt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mt)
    runs, meta = mt.load_runs()
    return mt, runs, meta


def gm(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else float("nan")


def main():
    res = {}
    for tag, sb in (("X1", sys.argv[1]), ("X1b", sys.argv[2])):
        mt, runs, meta = load(sb)
        shared = mt._ratios(runs, meta)
        nat_all = {}
        for (i, t, m), r in runs.items():
            if r["native"] and t != "supercollider":
                nat_all.setdefault(i, []).append((r["native"], t))
        res[tag] = (runs, meta, shared, nat_all)
    print("| suite | mode | n X1 / X1b | shared native: X1 → X1b geomean× | own native: X1 → X1b geomean× |")
    print("|---|---|---|---|---|")
    meta1 = res["X1"][1]
    suites = sorted({meta1[i][0] for (i, t, m) in res["X1"][0] if t == "cuvein"})
    for s in suites + ["all"]:
        for m in ("vector-clock", "scalar-clock"):
            cells = []
            for tag in ("X1", "X1b"):
                runs, meta, shared, _ = res[tag]
                ks = [k for k, r in runs.items() if k[1] == "cuvein" and k[2] == m
                      and (s == "all" or meta[k[0]][0] == s) and r["verdict"] in ("RACE", "CLEAN")]
                sh = [shared[k] for k in ks if k in shared]
                ow = [runs[k]["wall"] / runs[k]["native"] for k in ks if runs[k]["wall"] and runs[k]["native"]]
                cells.append((len(ks), gm(sh), gm(ow)))
            (n1, s1, o1), (n2, s2, o2) = cells
            print(f"| {s} | {m} | {n1} / {n2} | {s1:.1f} → {s2:.1f} | {o1:.1f} → {o2:.1f} |")
    for tag in ("X1", "X1b"):
        runs, meta, shared, nat_all = res[tag]
        other = sum(1 for i, v in nat_all.items() if min(v)[1] != "cuvein")
        print(f"\n{tag}: ids with a native wall {len(nat_all)}; the shared (minimum) native is another runner's in {other}")
    r1, r2 = res["X1"][0], res["X1b"][0]
    q = [r2[k]["native"] / r1[k]["native"] for k in r1 if k[1] == "cuvein" and k in r2
         and r1[k]["native"] and r2[k]["native"]]
    q.sort()
    print(f"cuVein's own native wall, X1b / X1 over {len(q)} (id, mode): median {statistics.median(q):.2f}, "
          f"p10 {q[len(q) // 10]:.2f}, p90 {q[9 * len(q) // 10]:.2f}")


if __name__ == "__main__":
    main()
