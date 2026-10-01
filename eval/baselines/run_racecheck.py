#!/usr/bin/env python3
"""B1 -- compute-sanitizer racecheck runner into the unified baseline schema.

racecheck detects only __shared__ hazards (its documented scope), so it runs only
on manifest rows with shared_mem=1; a CLEAN verdict here says nothing about global
races. Native identifiers are source lines parsed from the analysis report (needs
-lineinfo in the binary). Mirrors eval/racecheck.py's invocation but resolves a
real CUDA_HOME (blib) and emits the shared schema. Must run on a GPU node.

  srun -p rtx3060ti -N1 -n1 -t 02:00:00 \
    .env/bin/python eval/baselines/run_racecheck.py --pset P5,P6
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib

_HAZ = re.compile(r"RACECHECK SUMMARY:\s*(\d+)\s+hazard")
# analysis lines look like: "========= Race reported ... at 0x.. in /path/file.cu:NN:kernel"
_LOC = re.compile(r"in \S*?([\w.+-]+\.cu:\d+)")


def run_one(mrow, cs, cuda, reps):
    exe = mrow["exe"]
    if not (os.path.exists(exe) and os.access(exe, os.X_OK)):
        return blib.row(id=mrow["id"], pset=mrow["pset"], program=mrow["program"],
                        build=mrow["build"], input=mrow["input"], tool="racecheck",
                        verdict="ERROR", notes="missing-exe")
    exe_dir = os.path.dirname(exe)
    args = [a for a in mrow["args"].split() if a] if mrow["args"] else []
    stdin = mrow["stdin"] or None
    env = blib.base_env(cuda)
    timeout = int(mrow["timeout"] or 300)
    cmd = [cs, "--tool", "racecheck", "--racecheck-report", "analysis",
           os.path.abspath(exe), *args]
    best = None
    hz, lines, rc, verdict = None, [], "", "CLEAN"
    for _ in range(reps):
        fin = open(stdin, "rb") if stdin else subprocess.DEVNULL
        import time
        t0 = time.perf_counter()
        try:
            p = subprocess.run(cmd, cwd=exe_dir, env=env, stdin=fin,
                               capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            if stdin:
                fin.close()
            return blib.row(id=mrow["id"], pset=mrow["pset"], program=mrow["program"],
                            build=mrow["build"], input=mrow["input"],
                            tool="racecheck", verdict="TIMEOUT", rc=124)
        finally:
            if stdin and not fin.closed:
                fin.close()
        wall = round(time.perf_counter() - t0, 3)
        best = wall if best is None else min(best, wall)
        out = p.stdout + p.stderr
        m = _HAZ.search(out)
        hz = int(m.group(1)) if m else hz
        lines = sorted(set(_LOC.findall(out)))
        rc = p.returncode
    if hz is None:
        verdict = "ERROR"; notes = "no-summary"
    else:
        verdict = "RACE" if hz > 0 else "CLEAN"; notes = f"hazards={hz}"
    return blib.row(id=mrow["id"], pset=mrow["pset"], program=mrow["program"],
                    build=mrow["build"], input=mrow["input"], tool="racecheck",
                    verdict=verdict, reports_dedup=len(lines),
                    report_ids=" ".join(lines), report_lines=" ".join(lines),
                    wall_s=best, rc=rc, notes=notes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=f"{HERE}/manifest.csv")
    ap.add_argument("--pset", default="")
    ap.add_argument("--id", default="", help="run only these ids (comma list)")
    ap.add_argument("--reps", type=int, default=1,
                    help="racecheck is deterministic; 1 rep by default")
    ap.add_argument("--all", action="store_true",
                    help="also run rows with shared_mem=0 (records CLEAN/scope note)")
    a = ap.parse_args()
    cuda = blib.resolve_cuda_home()
    cs = f"{cuda}/compute-sanitizer/compute-sanitizer"
    if not os.path.exists(cs):
        cs = "compute-sanitizer"  # rely on PATH
    psets = set(a.pset.split(",")) if a.pset else None
    ids = set(a.id.split(",")) if a.id else None
    writer, fh, path = blib.open_results("racecheck")
    n = 0
    try:
        for mrow in blib.read_manifest(a.manifest):
            if psets and mrow["pset"] not in psets:
                continue
            if ids and mrow["id"] not in ids:
                continue
            if mrow["shared_mem"] != "1" and not a.all and not ids:
                continue
            n += 1
            print(f"[{n}] {mrow['id']}")
            writer.writerow(run_one(mrow, cs, cuda, a.reps))
            fh.flush()
    finally:
        fh.close()
    print(f"racecheck: {n} shared-mem program(s) -> {path}")


if __name__ == "__main__":
    main()
