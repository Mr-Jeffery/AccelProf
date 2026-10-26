#!/usr/bin/env python3
"""X3 (d): which 2026-09-22 rows are for programs above the lane cutoff (read only, CPU).

Lane cutoff: CUVEIN_BARRIER_PASS_MAX_LANES, default 5,000,000 lane-accesses per kernel
(python/sync_dominance.py:1350, eval/README.md "Re-analyzing existing traces"): the September stores were
recorded before T4 and analysed by replaying hb_events, and above the cutoff scalar-clock mode loses the
barrier pass. A program is "above the cutoff" here when any kernel JSON written for it in X1b's stores
(any mode, first pass and long passes, partial dirs included) has hb_lanes_count > 5,000,000.
That is a lower bound for programs whose run was cut by a cap (kernels after the cut are unseen).

Writes eval/results/final-tables/sept_over_cutoff.csv (+ sept_over_cutoff_summary.md).
September verdicts are NOT written: those rows are superseded and are not cited.
Run from the worktree root:  python3 -I eval/results/final-tables/sept_cutoff.py
"""
import csv, os, re, sys, collections
from multiprocessing import Pool

ROOT = os.getcwd()
R = os.path.join(ROOT, "eval", "results")
OUT = os.path.join(R, "final-tables")
B = "/mnt/beegfs/fzheng4/cuvein_traces"
STORES = ["final-2026-11", "final-2026-11-long", "final-2026-11-long-sc", "final-2026-11-24h-vc", "final-2026-11-24h-sc"]
CUT = 5_000_000
PAT = re.compile(rb'"hb_lanes_count":\s*(\d+)')


def scan(idv):
    best, where, nk = 0, "", 0
    for s in STORES:
        d = os.path.join(B, s, idv)
        if not os.path.isdir(d):
            continue
        for sub in os.listdir(d):
            if not (sub.startswith("vector-clock") or sub.startswith("scalar-clock")):
                continue
            p = os.path.join(d, sub)
            try:
                names = os.listdir(p)
            except OSError:
                continue
            for fn in names:
                if not (fn.startswith("kernel_") and fn.endswith(".json")):
                    continue
                try:
                    with open(os.path.join(p, fn), "rb") as f:
                        m = PAT.search(f.read())
                except OSError:
                    continue
                nk += 1
                if m and int(m.group(1)) > best:
                    best, where = int(m.group(1)), f"{s}/{sub}/{fn}"
    return idv, best, where, nk


def main():
    cu = {}
    for r in csv.DictReader(open(os.path.join(R, "final-b", "merged", "baselines-cuvein.csv"), newline="")):
        cu.setdefault(r["id"], r["pset"])
    sept = collections.defaultdict(set)
    sp = {}
    for r in csv.DictReader(open(os.path.join(R, "superseded_baselines-cuvein-2026-09-22.csv"), newline="")):
        sept[r["id"]].add(r["mode"])
        sp[r["id"]] = r["pset"]
    ids = sorted(i for i in cu if cu[i] != "")
    with Pool(int(os.environ.get("NPROC", "16"))) as pool:
        res = pool.map(scan, ids, chunksize=8)
    rows = []
    for idv, best, where, nk in res:
        rows.append({"id": idv, "pset": cu[idv], "max_lanes_per_kernel": best, "kernels_read": nk, "where": where,
                     "above_cutoff": int(best > CUT), "in_sept_file": int(idv in sept), "sept_modes": ",".join(sorted(sept.get(idv, ())))})
    with open(os.path.join(OUT, "sept_over_cutoff.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    c = collections.Counter()
    for r in rows:
        c[(r["pset"], "ids")] += 1
        c[(r["pset"], "above")] += r["above_cutoff"]
        c[(r["pset"], "above_in_sept")] += r["above_cutoff"] and r["in_sept_file"]
        c[(r["pset"], "no_kernels")] += r["kernels_read"] == 0
    with open(os.path.join(OUT, "sept_over_cutoff_summary.md"), "w") as f:
        f.write("| suite | ids | ids above the 5 M-lane cutoff | of them with a 2026-09-22 row | ids with no kernel JSON read |\n|---|---|---|---|---|\n")
        for ps in sorted({r["pset"] for r in rows}):
            f.write(f"| {ps} | {c[(ps,'ids')]} | {c[(ps,'above')]} | {c[(ps,'above_in_sept')]} | {c[(ps,'no_kernels')]} |\n")
        tot = lambda k: sum(v for (p, kk), v in c.items() if kk == k)
        f.write(f"| all | {tot('ids')} | {tot('above')} | {tot('above_in_sept')} | {tot('no_kernels')} |\n")
    print(open(os.path.join(OUT, "sept_over_cutoff_summary.md")).read())
    for r in rows:
        if r["above_cutoff"] and r["pset"] != "PI":
            print(r["id"][:70], r["max_lanes_per_kernel"], r["in_sept_file"], r["sept_modes"])
    print("PI above cutoff:", sum(r["above_cutoff"] for r in rows if r["pset"] == "PI"))


main()
