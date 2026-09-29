#!/usr/bin/env python3
"""T5b: where does a vector-clock run spend its time? One manifest program, vector-clock mode,
the runtime of ACCEL_PROF_HOME, under `perf record -g` (sampling every process of the tree);
prints the top symbols of the flat profile. GPU node only.

  t5b_profile.py --id P4-graph-coloring-norace-large [--mode vector-clock] [--cap 900]
"""
import argparse
import csv
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import blib  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--mode", default="vector-clock")
    ap.add_argument("--cap", type=int, default=900)
    ap.add_argument("--work", default=f"/mnt/beegfs/{os.environ['USER']}/t5b_profile")
    a = ap.parse_args()
    row = next(r for r in csv.DictReader(open(f"{os.path.dirname(HERE)}/manifest.csv")) if r["id"] == a.id)
    work = f"{a.work}/{a.id}-{a.mode}"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    exe = os.path.realpath(row["exe"])
    base = os.path.basename(exe)
    os.symlink(exe, f"{work}/{base}")
    env0 = blib.base_env()
    scope, _ = blib.extract(exe, f"{work}/cubins", env0)
    env = blib.base_env(hb_trace=True, hb_mode=a.mode, scope_file=scope or None)
    env["YOSEMITE_HB_STATS"] = "1"
    args = [x for x in row["args"].split() if x] if row["args"] else []
    cmd = ["timeout", str(a.cap), "perf", "record", "-F", "199", "-g", "-o", f"{work}/perf.data",
           "--", "accelprof", "-v", "-t", "pc_dependency_analysis", "-n", "1", f"./{base}", *args]
    stdin = open(row["stdin"]) if row["stdin"] else subprocess.DEVNULL
    print(" ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=work, env=env, stdin=stdin, stdout=subprocess.DEVNULL,
                       stderr=open(f"{work}/stderr.txt", "w"))
    print(f"rc={r.returncode}", flush=True)
    rep = subprocess.run(["perf", "report", "-i", f"{work}/perf.data", "--no-children", "--stdio",
                          "--sort", "dso,symbol", "-g", "none", "--percent-limit", "0.5"],
                         capture_output=True, text=True, cwd=work)
    print("\n".join(ln for ln in rep.stdout.splitlines() if ln.strip() and not ln.startswith("#"))[:6000])
    print(rep.stderr[-1500:])


if __name__ == "__main__":
    main()
