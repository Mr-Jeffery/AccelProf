#!/usr/bin/env python3
"""X9 harness: split one test binary's level-0 tests into gtest-filter chunks whose estimated scalar-clock collect
time is <= --budget seconds, and append one manifest row per chunk (id cutlass-<prog>-cNN, filter = the chunk's
`Suite.Test` names joined by ':'). Estimate per test = native ms (smoke run, `[       OK ] Suite.Test (N ms)`) / 1000
+ PER_LAUNCH * (binary's launches / tests run) (PER_LAUNCH from the X9 gate: (tool wall - native wall) / launches =
0.40 s and 0.33 s; 0.40 used). Tests are kept in run order and a suite is never split unless it alone exceeds the
budget. Prints one line per chunk: id, tests, estimated s.
usage: x9_chunks.py --prog gemm_device_tensorop_f32_sm80 --family F [--budget 900] [--dry]   (compute node: smoke files)"""
import argparse, csv, os, re, sys
SMOKE = "/mnt/beegfs/fzheng4/cutlass/smoke"
M = "/home/fzheng4/wt-x9/eval/cutlass/manifest_cutlass.csv"
PER_LAUNCH = 0.40
ap = argparse.ArgumentParser()
ap.add_argument("--prog", required=True)
ap.add_argument("--family", required=True)
ap.add_argument("--budget", type=float, default=900)
ap.add_argument("--dry", action="store_true")
ap.add_argument("--per-launch", dest="per_launch", type=float, default=PER_LAUNCH,
                help="s per launch (X9 R4: simt_3x-c00 timed out at 1200 s after 1756 launches, 0.68)")
a = ap.parse_args()
PER_LAUNCH = a.per_launch
n = f"cutlass_test_unit_{a.prog}"
tests = [(m.group(1), int(m.group(2))) for m in
         re.finditer(r"^\[       OK \] (\S+) \((\d+) ms\)", open(f"{SMOKE}/{n}.native.txt").read(), re.M)]
ks = [f for f in os.listdir(SMOKE) if f.startswith(n + "_cuda_gpu_kern_sum") or f.startswith(n + "_") and "kern_sum" in f]
ks = [f for f in ks if f.startswith(n + "_cuda_gpu_kern_sum")]
launches = sum(int(r["Instances"]) for r in csv.DictReader(open(f"{SMOKE}/{ks[0]}"))) if ks else None
if not tests:
    sys.exit(f"{n}: no tests ran")
per = PER_LAUNCH * (launches / len(tests)) if launches else PER_LAUNCH * 16
est = [(t, ms / 1000 + per) for t, ms in tests]
suites = []
for t, e in est:
    s = t.split(".")[0]
    if suites and suites[-1][0] == s:
        suites[-1][1].append((t, e))
    else:
        suites.append((s, [(t, e)]))
chunks, cur = [], []
for s, ts in suites:
    units = [[x] for x in ts] if sum(e for _, e in ts) > a.budget else [ts]
    for u in units:
        if cur and sum(e for _, e in cur) + sum(e for _, e in u) > a.budget:
            chunks.append(cur); cur = []
        cur = cur + u
if cur:
    chunks.append(cur)
BLD = "/mnt/beegfs/fzheng4/cutlass/build"
rows = list(csv.DictReader(open(M, newline="")))
cols = list(rows[0].keys())
parent = next(r for r in rows if r["id"] == f"cutlass-{a.prog}-all")
have = {r["id"] for r in rows}
print(f"{n}: {len(tests)} tests, launches={launches}, est/test launch part={per:.1f}s, total est={sum(e for _, e in est):.0f}s,"
      f" {len(chunks)} chunks")
for i, c in enumerate(chunks):
    rid = f"cutlass-{a.prog}-c{i:02d}"
    flt = ":".join(t for t, _ in c)
    print(f"{rid}\t{len(c)} tests\test {sum(e for _, e in c):.0f}s")
    if rid in have:
        continue
    rows.append(dict(parent, id=rid, input=f"gtest_filter=<{len(c)} tests, chunk {i} of {len(chunks)}> (CUTLASS_TEST_LEVEL=0)",
                     args=f"--gtest_filter={flt}", cmd=f"{parent['exe']} --gtest_filter={flt}", target=a.family))
if not a.dry:
    with open(M, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
