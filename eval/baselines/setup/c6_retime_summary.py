#!/usr/bin/env python3
"""C6 step 2 re-time summary: per host, configuration and pass, per suite (P1 P3 P4 P5 P6 PI, HeCBench = P7+P9):
n programs, median / max analysis_s (one value per (program, mode), rep 1 row), and for co-on the sum of chain_s.
usage: c6_retime_summary.py <wt>   -> eval/results/co-chain/retime/summary.tsv (and stdout)"""
import csv, glob, os, re, statistics, sys
W = sys.argv[1]
R = f"{W}/eval/results/co-chain/retime"


def tok(n, name):
    m = re.search(r"(?:^|;)" + name + r"=([^;]*)", n)
    return m.group(1) if m else None


out = []
hdr = ["host", "cfg", "pass", "suite", "n", "analysis_s_median", "analysis_s_max", "analysis_s_sum", "chain_s_sum"]
for hostdir in sorted(glob.glob(f"{R}/*/")):
    host = os.path.basename(hostdir.rstrip("/"))
    for d in sorted(glob.glob(f"{hostdir}*-p[12]")):
        cfg, ps = os.path.basename(d).rsplit("-p", 1)
        f = f"{d}/baselines-cuvein-shardrtall.csv"
        if not os.path.exists(f):
            continue
        by = {}
        for r in csv.DictReader(open(f, newline="")):
            if r["rep"] != "1" or tok(r["notes"], "analysis_s") is None:
                continue
            suite = "HeCBench" if r["pset"] in ("P7", "P9") else r["pset"]
            by.setdefault(suite, []).append((float(tok(r["notes"], "analysis_s")), float(tok(r["notes"], "chain_s") or 0)))
        allv = [x for v in by.values() for x in v]
        by["all"] = allv
        for s in ("P1", "P3", "P4", "P5", "P6", "PI", "HeCBench", "all"):
            v = by.get(s, [])
            if not v:
                continue
            a = [x[0] for x in v]
            out.append([host, cfg, ps, s, len(v), f"{statistics.median(a):.3f}", f"{max(a):.3f}", f"{sum(a):.2f}",
                        f"{sum(x[1] for x in v):.3f}"])
with open(f"{R}/summary.tsv", "w") as fh:
    fh.write("\t".join(hdr) + "\n")
    for r in out:
        fh.write("\t".join(map(str, r)) + "\n")
print("\t".join(hdr))
for r in out:
    print("\t".join(map(str, r)))
