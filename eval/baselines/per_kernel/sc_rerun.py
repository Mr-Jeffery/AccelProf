#!/usr/bin/env python3
"""X13 step 3b: SuperCollider on the HeCBench rows whose stored rows carry no lines (atomicCAS, dxtc2, expdist), artifact
protocol (5 attempts, RACE if any attempt reports), into a log root on BeeGFS. run_supercollider.run_one is imported
unchanged; the logs are re-parsed afterwards by sc_parse.py for "Inlined function ... at file:line".
Usage: sc_rerun.py OUT.csv LOGROOT PROGRAM..."""
import csv, os, sys
sys.path.insert(0, "/home/fzheng4/wt-x13/eval/baselines")
import blib, run_supercollider as rs
# the artifact and image live in the main checkout (git-ignored, not in this worktree)
A = "/home/fzheng4/AccelProf/eval/baselines/setup/tools/supercollider"
rs.ROOT = A; rs.SC = f"{A}/supercollider-artifacts"; rs.SIF = f"{A}/ubuntu2204.sif"; rs.LIB = f"{rs.SC}/lib64/librc-release.so"
out, logroot, progs = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(logroot, exist_ok=True)
cuda = blib.resolve_cuda_home()
rows = [m for m in blib.read_manifest("/home/fzheng4/wt-x13/eval/baselines/manifest.csv")
        if m["pset"] == "P9" and m["program"][:-5] in progs]
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=blib.COLUMNS); w.writeheader()
    for m in rows:
        print("run", m["id"], flush=True)
        for r in rs.run_one(m, cuda, 5, logroot):
            w.writerow(r)
        fh.flush()
