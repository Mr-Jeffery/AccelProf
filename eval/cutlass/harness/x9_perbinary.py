#!/usr/bin/env python3
"""X9 report §5 from eval/results/cutlass/x9.csv: per binary, the recordings (one per recorded manifest id and flavor,
DUPLICATE and NOT-RECORDED excluded), their summed wall and max peak RSS, the kernels analyzed (sub-ids) and their
launches, the per-kernel analysis time of both halves summed, timeouts (TIMEOUT = superseded by a 5,400 s pass or a
split; TIMEOUT1 = final single-test timeout) and NO-KERNELS ids.
usage: x9_perbinary.py [x9.csv] > eval/results/cutlass/summary/per_binary.tsv"""
import csv, sys, collections
csv.field_size_limit(10 ** 9)
rs = list(csv.DictReader(open(sys.argv[1] if len(sys.argv) > 1 else "/home/fzheng4/wt-x9/eval/results/cutlass/x9.csv")))
B = collections.defaultdict(lambda: dict(rec=set(), wall=0.0, peak=0.0, subs=set(), launches=0, ana=0.0,
                                         to=0, to1=0, nok=0, t5=0))
seen = set()
def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):   # "", None, "missing"
        return 0.0
for r in rs:
    b = B[r["binary"]]
    key = (r["flavor"], r["parent_id"])
    if r["outcome"] in ("DUPLICATE", "NOT-RECORDED"):
        continue
    if key not in seen:
        seen.add(key)
        b["rec"].add(key)
        b["wall"] += f(r["record_wall_s"])
        b["peak"] = max(b["peak"], f(r["record_peak_mb"]))
        b["t5"] += r["flavor"] == "t5400"
        b["to"] += r["outcome"] == "TIMEOUT"
        b["to1"] += r["outcome"] == "TIMEOUT1"
        b["nok"] += r["outcome"] == "NO-KERNELS"
    if r["outcome"] == "ANALYZED":
        if r["sub_id"] not in b["subs"]:
            b["subs"].add(r["sub_id"])
            b["launches"] += int(f(r["launches"]))
        b["ana"] += f(r["analysis_s"])
print("binary\trecordings\tof_them_t5400\trecord_wall_s\tmax_peak_mb\tkernels_analyzed\tlaunches\tanalysis_s_both_halves"
      "\ttimeouts_superseded\ttimeouts_final\tno_kernel_ids")
for k in sorted(B):
    b = B[k]
    print(f"{k}\t{len(b['rec'])}\t{b['t5']}\t{b['wall']:.0f}\t{b['peak']:.0f}\t{len(b['subs'])}\t{b['launches']}\t{b['ana']:.0f}"
          f"\t{b['to']}\t{b['to1']}\t{b['nok']}")
