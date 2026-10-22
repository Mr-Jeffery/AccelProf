#!/usr/bin/env python3
"""X1-follow section 1: the collector-only rows (eval/x1_follow/collector/*.json) next to X1's rows of the
same programs (eval/results/final*/ shard CSVs: wall = median of the rep walls, as make_tables), as markdown."""
import csv, glob, json, re, statistics, sys, os
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../..")
SHORT = {"P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n": "P1-BFS_CUDA_E_Topo_Determ_IntType_ReadMo",
         "P6-interkernel-global_readwrite_race-fixed": "P6-interkernel-global_readwrite_race-fix"}
LONG = {"P7-heartwall-cuda": "P7-heartwall-cuda", "P9-knn-cuda": "P9-knn-cuda"}
X1DIRS = {"P7-heartwall-cuda": ["final-24h-vc", "final-24h-sc"], "P9-knn-cuda": ["final-24h-vc", "final-24h-sc"]}
CPU = {"c51": "9115", "c52": "9115", "c58": "9115", "c60": "8124P", "c61": "8124P", "c62": "8124P", "c63": "8124P",
       "c64": "8124P", "c66": "8124P", "c73": "7302P", "c74": "7302P", "c77": "7302P", "c78": "7302P", "c79": "7302P"}

def x1rows(i, dirs):
    out = {}
    for d in dirs:
        for f in glob.glob(f"{W}/eval/results/{d}/baselines-cuvein-shard*.csv"):
            for r in csv.DictReader(open(f, newline="")):
                if r["id"] == i:
                    out.setdefault(r["mode"], []).append(r)
    return out

def fmt(x, nd=0):
    return f"{x:,.{nd}f}"

def row(label, node, wall, native, rss, rss_kind, events, ev_src, nk, extra=""):
    ratio = wall / native if native else float("nan")
    us = wall / events * 1e6 if events else float("nan")
    return (f"| {label} | {node} ({CPU.get(node, '?')}) | {fmt(wall, 1 if wall >= 100 else 3)} | {fmt(native, 3)} | {fmt(ratio)}× | "
            f"{fmt(rss)} {rss_kind} | {fmt(events)} {ev_src} | {us:.4g} | {nk} | {extra} |")

def main():
    print("| program / configuration | host (CPU) | tool wall (s) | native wall (s) | wall / native | memory (MB) | events | µs / event | kernels | |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for i, short in list(LONG.items()) + list(SHORT.items()):
        dirs = X1DIRS.get(i, ["final"])
        xr = x1rows(i, dirs)
        for mode in ("vector-clock", "scalar-clock"):
            rs = xr.get(mode, [])
            if not rs:
                continue
            ev = int(re.search(r"events=(\d+)", rs[0]["notes"]).group(1))
            node = re.search(r"node=(c\d+)", rs[0]["notes"]).group(1)
            nk = re.search(r"nkernels=(\d+)", rs[0]["notes"]).group(1)
            w = statistics.median(float(r["wall_s"]) for r in rs)
            pk = max(float(r["peak_mb"]) for r in rs)
            print(row(f"{i.split('-')[0]} {short[3:30]} — X1 {mode} ({len(rs)} rep{'s' if len(rs) > 1 else ''}, {dirs[0] if mode == 'vector-clock' else dirs[-1]})",
                      node, w, float(rs[0]["native_wall_s"]), pk, "peak (summed VmRSS)", ev, "(X1 `events=`)", nk))
        for cfg in ("collector-n1", "collector-ndefault", "scalar-clock-n1", "vector-clock-n1"):
            p = f"{W}/eval/x1_follow/collector/{short}-{cfg}.json"
            if not os.path.exists(p):
                continue
            d = json.load(open(p))
            nat = statistics.median(n["wall"] for n in d["native"])
            ev = d["drained_records"]
            lab = {"collector-n1": "collector-only, -n 1", "collector-ndefault": "collector-only, default workers",
                   "scalar-clock-n1": "X1 configuration, scalar-clock, same host", "vector-clock-n1": "X1 configuration, vector-clock, same host"}[cfg]
            st = "TIMEOUT" if d["timed_out"] else ("" if d["rc"] == 0 else f"rc={d['rc']}")
            print(row(f"{i.split('-')[0]} {short[3:30]} — {lab}", d["node"], d["wall"], nat, d["maxrss_mb_hwm"], "MaxRSS (VmHWM)",
                      ev, "(drained, this run)", d["nkernels"], st))
main()
