#!/usr/bin/env python3
"""X9: append rows to eval/cutlass/manifest_cutlass.csv (T21c's manifest schema). One row = one (binary, gtest filter).
usage: mk_manifest.py <family> <binary path relative to the build dir> <gtest filter> [...more triples]"""
import csv, os, re, sys
M = "/home/fzheng4/wt-x9/eval/cutlass/manifest_cutlass.csv"
BLD = "/mnt/beegfs/fzheng4/cutlass/build"
COLS = ("id,pset,program,build,input,exe,args,stdin,shared_mem,label,arrays_to_wrap,monitored_kernels,reps,timeout,"
        "target,variant,wave,route,kernel,expected_class,oracle,cmd,needs_wrapper").split(",")
rows = list(csv.DictReader(open(M))) if os.path.exists(M) else []
have = {r["id"] for r in rows}
a = sys.argv[1:]
for fam, b, flt in zip(a[0::3], a[1::3], a[2::3]):
    prog = os.path.basename(b).replace("cutlass_test_unit_", "")
    rid = "cutlass-" + prog + "-" + ("all" if flt == "*" else re.sub(r"[^A-Za-z0-9]+", "_", flt).strip("_"))
    if rid in have:
        continue
    r = {c: "" for c in COLS}
    r.update(id=rid, pset="CUTLASS", program=prog, build="v4.8.1", input=f"gtest_filter={flt} (CUTLASS_TEST_LEVEL=0)",
             exe=f"{BLD}/{b}", args=f"--gtest_filter={flt}", reps="1", timeout="1200", target=fam, variant="sm89",
             label="", cmd=f"{BLD}/{b} --gtest_filter={flt}", needs_wrapper="0")
    rows.append(r); have.add(rid); print(rid)
with open(M, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
