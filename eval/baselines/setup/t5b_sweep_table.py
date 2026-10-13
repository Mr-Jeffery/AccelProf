#!/usr/bin/env python3
"""T5b acceptance table: the 58 programs of setup/engine_timeout_ids.txt re-run with the T5b
runtime (p_t5b_timeout.sh -> eval/results/<tag>/), both modes, against their baseline
vector-clock rows (eval/results/baselines-cuvein*.csv). Categories: T6's SASS classification
(design/T6_REVIEW.md, re-derived with setup/t6_sass_scan.py's section 3 on 2026-09-29).

    .env/bin/python eval/baselines/setup/t5b_sweep_table.py [--tag t5b-final-timeout]
"""
import argparse
import collections
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BARRIERS_ONLY = {"P7-heartwall-cuda", "P7-hotspot-cuda", "P7-lavaMD-cuda", "P7-particlefilter-cuda",
                 "P7-pathfinder-cuda", "P7-srad-cuda", "P7-stencil1d-cuda", "P9-dxtc2-cuda",
                 "P9-knn-cuda", "P9-tridiagonal-cuda"}
NEITHER = {"P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed", "P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy",
           "P6-asyncmemcpy-memcpy_htod_kernel_race-racy", "P6-interkernel-global_writewrite_race-fixed",
           "P6-interkernel-global_writewrite_race-racy", "P7-bezier-surface-cuda", "P7-bitonic-sort-cuda",
           "P7-haversine-cuda", "P7-mandelbrot-cuda", "P7-nbody-cuda"}
ATOMICS_ONLY = {"P9-atomicCAS-cuda", "P9-gpp-cuda", "P9-mr-cuda"}   # + the five P1 *_Warp_/BFS rows


def category(i):
    if i in BARRIERS_ONLY:
        return "barriers, no atomics"
    if i in NEITHER:
        return "neither"
    if i in ATOMICS_ONLY or "_Warp_" in i or i.startswith("P1-BFS"):
        return "atomics only"
    return "atomics + barriers"


def short(i):
    if i.startswith(("P1-", "P3-")):
        p = i.split("_")
        return f"{i[:3]}{p[0][3:]}_{p[2]}_{p[3]}_{p[4]}_…{i.rsplit('-', 1)[-1]}".replace("CUDA_", "")
    return i


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="t5b-final-timeout")
    a = ap.parse_args()
    ids = [ln.strip() for ln in open(f"{HERE}/engine_timeout_ids.txt") if ln.strip()]
    base = {}
    for p in sorted(glob.glob(f"{APH}/eval/results/baselines-cuvein*.csv")):
        for r in csv.DictReader(open(p)):
            if r["mode"] == "vector-clock" and r["id"] in ids:
                base[r["id"]] = r
    new = {}
    for p in glob.glob(f"{APH}/eval/results/{a.tag}/*.csv"):
        for r in csv.DictReader(open(p)):
            new[(r["id"], r["mode"])] = r

    def cell(r):
        if not r:
            return "—"
        pk = f"{float(r['peak_mb']) / 1024:.1f} GB" if r.get("peak_mb") else "?"
        return f"{r['verdict']} {float(r['wall_s']):.0f} s, {pk}"

    by = collections.defaultdict(list)
    for i in ids:
        by[category(i)].append(i)
    summ = []
    print("| program | baseline vector-clock | T5b vector-clock | T5b scalar-clock |")
    print("|---|---|---|---|")
    for cat in ("barriers, no atomics", "atomics + barriers", "atomics only", "neither"):
        fin = fin120 = scfin = 0
        print(f"| **{cat}** ({len(by[cat])}) | | | |")
        for i in by[cat]:
            b, v, s = base.get(i), new.get((i, "vector-clock")), new.get((i, "scalar-clock"))
            bc = f"{b['verdict']} {float(b['peak_mb']) / 1024:.1f} GB" if b and b.get("peak_mb") else (b or {}).get("verdict", "—")
            print(f"| {short(i)} | {bc} | {cell(v)} | {cell(s)} |")
            ok = v and v["verdict"] in ("RACE", "CLEAN")
            fin += bool(ok)
            fin120 += bool(ok and float(v["wall_s"]) <= 120)
            scfin += bool(s and s["verdict"] in ("RACE", "CLEAN"))
        summ.append((cat, len(by[cat]), fin, fin120, scfin))
    print()
    print("| category | programs | vector-clock finishes | … within 120 s | scalar-clock finishes |")
    print("|---|---|---|---|---|")
    for c, n, f, f1, sf in summ:
        print(f"| {c} | {n} | {f} | {f1} | {sf} |")
    tot = [sum(x[k] for x in summ) for k in (1, 2, 3, 4)]
    print(f"| all | {tot[0]} | {tot[1]} | {tot[2]} | {tot[3]} |")
    missing = [i for i in ids if (i, "vector-clock") not in new]
    if missing:
        print(f"\nno row yet: {len(missing)}: {', '.join(missing)}")


if __name__ == "__main__":
    main()
