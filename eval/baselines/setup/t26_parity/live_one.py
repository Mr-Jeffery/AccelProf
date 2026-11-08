#!/usr/bin/env python3
"""T26 parity: one live recording of a manifest id with a fixed tool timeout (t20.sh with LIVE=direct).

    live_one.py --id ID --mode MODE --workers N --out DIR [--cap S]

`parallel.py collect` takes its tool timeout as min(max(10 x native, 120), --timeout-cap) -- its
--timeout-floor is not passed to collect_one -- so an id whose tool run needs more than 10x native and
more than 120 s is cut there in every configuration (P6-interkernel-global_writewrite_race-racy). This
runs the same thing the harness runs -- blib.extract for the dots and the atomic-scope sidecar, blib.base_env
for the mode's environment, the manifest's exe/args/stdin, `accelprof -t pc_dependency_analysis -n N`
in a scratch work dir (HeCBench data links as collect_one makes them) -- with the tool timeout = --cap,
and writes the kernel JSONs to DIR/<mode>/, the dots to DIR/dots/ and DIR/meta.json (rc, timed_out, wall,
nkernels, analyzer_workers) in the layout t20.sh reads. ACCEL_PROF_HOME picks the runtime (blib.APH).
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # eval/baselines/setup
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))   # eval/baselines
import blib        # noqa: E402
import parallel    # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--workers", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap", type=int, default=1200)
    a = ap.parse_args()
    rows = list(parallel._rows(f"{os.path.dirname(os.path.dirname(HERE))}/manifest.csv", None, {a.id}))
    if len(rows) != 1:
        raise SystemExit(f"{a.id}: {len(rows)} manifest rows")
    m = rows[0]
    shutil.rmtree(a.out, ignore_errors=True)
    work = f"{a.out}/work"
    os.makedirs(work)
    exe = m["exe"]
    base = os.path.basename(exe)
    os.symlink(os.path.realpath(exe), f"{work}/{base}")
    args = [x for x in m["args"].split() if x] if m["args"] else []
    if m["pset"] in ("P7", "P9"):
        hec = f"{os.path.dirname(os.path.dirname(HERE))}/corpora/HeCBench/src"
        for lnk, target in ((f"{a.out}/data", f"{hec}/data"), (f"{work}/input", f"{hec}/{m['program']}/input"),
                            (f"{work}/data", f"{hec}/{m['program']}/data")):
            if os.path.isdir(target) and not os.path.lexists(lnk):
                os.symlink(target, lnk)
    cuda = blib.resolve_cuda_home()
    nenv = blib.base_env(cuda)
    scope, _ = blib.extract(os.path.realpath(exe), f"{work}/cubins", nenv)
    os.makedirs(f"{a.out}/dots")
    for d in glob.glob(f"{work}/cubins/*.dot"):
        shutil.copy(d, f"{a.out}/dots/")
    env = blib.base_env(cuda, hb_trace=True, hb_mode=a.mode, scope_file=scope or None)
    cmd = ["accelprof", "-t", "pc_dependency_analysis", "-n", str(a.workers), f"./{base}", *args]
    stdin = open(m["stdin"]) if m["stdin"] else subprocess.DEVNULL
    t0 = time.time()
    p = subprocess.Popen(cmd, cwd=work, env=env, stdin=stdin, stdout=subprocess.DEVNULL,
                         stderr=open(f"{a.out}/tool_stderr.txt", "w"), start_new_session=True)
    timed_out = False
    try:
        rc = p.wait(timeout=a.cap)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(p.pid, 9)
        rc = p.wait()
    wall = round(time.time() - t0, 3)
    md = f"{a.out}/{a.mode}"
    os.makedirs(md)
    kjs = []
    for dd in glob.glob(f"{work}/dependency_{base}_*"):
        kjs += glob.glob(f"{dd}/kernel_*.json")
    for kj in kjs:
        shutil.move(kj, f"{md}/{os.path.basename(kj)}")
    meta = {"id": a.id, "analyzer_workers": a.workers, "runtime_home": blib.APH, "tool_timeout": a.cap,
            "modes": {a.mode: {"reps": [{"rc": rc, "timed_out": timed_out, "wall": wall, "nkernels": len(kjs)}]}}}
    with open(f"{a.out}/meta.json", "w") as f:
        json.dump(meta, f)
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(meta["modes"][a.mode]["reps"][0]))


if __name__ == "__main__":
    main()
