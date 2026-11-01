#!/usr/bin/env python3
"""X9 harness: `parallel.py collect` with --timeout-floor honoured. parallel.cmd_collect calls
collect_one(m, cuda, reps, cap=...) without floor, so the tool timeout there is min(max(10x native, 120), cap):
a CUTLASS gtest chunk with 22 s native gets 221 s (blas3-c00, job 324776: timed out after 200 kernels). This wrapper
binds floor=--timeout-floor onto parallel.collect_one and runs parallel.main() unchanged (parallel.py not edited).
usage: same arguments as `parallel.py collect ...`   (x9_collect.py collect --manifest M --id ID --reps 1
       --timeout-floor 1200 --timeout-cap 1200 --tag T)"""
import functools, os, sys
sys.path.insert(0, "/home/fzheng4/wt-x9/eval/baselines")
import parallel
fl = 120
for i, x in enumerate(sys.argv):
    if x == "--timeout-floor":
        fl = int(sys.argv[i + 1])
    elif x.startswith("--timeout-floor="):
        fl = int(x.split("=", 1)[1])
parallel.collect_one = functools.partial(parallel.collect_one, floor=fl)
print(f"x9_collect: collect_one floor={fl}", flush=True)
sys.argv[0] = parallel.__file__
parallel.main()
