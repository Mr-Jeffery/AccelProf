#!/usr/bin/env python3
"""X9 harness: split one manifest chunk id whose t5400 collect timed out again into --parts sub-chunks of consecutive
tests (as equal in test count as possible), appended as manifest rows <id>sNN (same exe/family, filter = the sub-chunk's
tests). The parent row stays (its timed-out store is reported, not analyzed).
A whole-binary id (filter *) takes its test names, in run order, from --tests-from (a native run log, `[       OK ] Suite.Test`).
usage: x9_rechunk.py --id cutlass-conv_device_simt-c00 --parts 6 [--tests-from native_rep1.txt] [--dry]"""
import argparse, csv, re
M = "/home/fzheng4/wt-x9/eval/cutlass/manifest_cutlass.csv"
ap = argparse.ArgumentParser()
ap.add_argument("--id", required=True)
ap.add_argument("--parts", type=int, required=True)
ap.add_argument("--tests-from", dest="tests_from")
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()
rows = list(csv.DictReader(open(M, newline="")))
cols = list(rows[0].keys())
p = next(r for r in rows if r["id"] == a.id)
tests = p["args"].split("=", 1)[1].split(":")
if a.tests_from:
    tests = re.findall(r"^\[       OK \] (\S+) \(", open(a.tests_from).read(), re.M)
have = {r["id"] for r in rows}
k, n = divmod(len(tests), a.parts)
i0 = 0
for i in range(a.parts):
    c = tests[i0:i0 + k + (i < n)]; i0 += len(c)
    rid = f"{a.id}s{i:02d}"
    flt = ":".join(c)
    print(f"{rid}\t{len(c)} tests\t{c[0]} .. {c[-1]}")
    if rid not in have:
        rows.append(dict(p, id=rid, input=f"gtest_filter=<{len(c)} tests, sub-chunk {i} of {a.parts} of {a.id}> (CUTLASS_TEST_LEVEL=0)",
                         args=f"--gtest_filter={flt}", cmd=f"{p['exe']} --gtest_filter={flt}"))
if not a.dry:
    with open(M, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
