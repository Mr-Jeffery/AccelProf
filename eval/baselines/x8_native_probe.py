#!/usr/bin/env python3
"""X8 step 5.7: does the artifact's NATIVE (uninstrumented) binary run at the manifest row's launch?
One run per row of the 99 shipped codes x 7 inputs, same container / env as run_supercollider.py;
records rc, timeout, wall and the first line of stdout/stderr (a usage message would show here).
  x8_native_probe.py --out eval/x_logs/x8_native_probe_<k>_<n>.csv [--shard k/n]"""
import argparse, csv, os, socket, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blib, run_supercollider as rs

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--shard", default="")
a = ap.parse_args()
rows = [m for m in blib.read_manifest(f"{HERE}/manifest.csv") if m["pset"] == "PI" and m["build"] == "sc-subset"]
rows = rs._shard(rows, a.shard)
nenv = {k: v for k, v in os.environ.items() if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD")}
node = socket.gethostname().split(".")[0]
with open(a.out, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["id", "input", "launch", "rc", "timeout", "wall_s", "first_line", "node"])
    for m in rows:
        inst, nat = rs.sc_binaries(m)
        args = m["args"].split()
        t0 = time.time(); to = 0
        try:
            p = subprocess.run([rs.SING, "exec", "--nv", rs.SIF, nat, *args], env=nenv, cwd=os.path.dirname(inst),
                               capture_output=True, text=True, timeout=300)
            rc, out = p.returncode, (p.stdout + "\n" + p.stderr)
        except subprocess.TimeoutExpired as e:
            rc, to, out = "", 1, ""
        line = next((l.strip() for l in out.splitlines() if l.strip() and not l.startswith("INFO")), "")
        w.writerow([m["id"], m["input"], " ".join(args[1:]), rc, to, f"{time.time() - t0:.2f}", line[:160].replace(",", ";"), node])
        fh.flush()
