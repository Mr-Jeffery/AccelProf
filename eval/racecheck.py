#!/usr/bin/env python3
"""E6a baseline: run compute-sanitizer racecheck (shared-memory hazards only) on a
set of binaries and tabulate hazard counts, for cross-checking cuVein's verdicts.

    python eval/racecheck.py --out eval/results/E6a-racecheck.csv \
        --exe NAME=/abs/path[,stdin=/abs/in] ...

racecheck detects only __shared__ hazards (its documented scope); a 'clean' verdict
says nothing about global-memory races. Output columns: name, hazards, verdict, rc.
"""
import argparse
import csv
import os
import re
import subprocess

CUDA_HOME = "/home/fzheng4/spack/opt/spack/linux-zen2/cuda-12.9.0-owxskbbrhugkzflau7xe3gyqnvdqlfyw"
CS = f"{CUDA_HOME}/compute-sanitizer/compute-sanitizer"
_HAZ = re.compile(r"RACECHECK SUMMARY:\s*(\d+)\s+hazard")


def env():
    e = os.environ.copy()
    e["PATH"] = f"{CUDA_HOME}/bin:/usr/bin:/bin"
    e["CUDA_HOME"] = CUDA_HOME
    e["LD_LIBRARY_PATH"] = f"{CUDA_HOME}/compute-sanitizer:" + e.get("LD_LIBRARY_PATH", "")
    return e


def run(name, exe, stdin, timeout):
    if not (os.path.exists(exe) and os.access(exe, os.X_OK)):
        return {"name": name, "hazards": "", "verdict": "missing-exe", "rc": ""}
    cwd = os.path.dirname(exe)
    fin = open(stdin, "rb") if stdin else subprocess.DEVNULL
    cmd = [CS, "--tool", "racecheck", "--racecheck-report", "analysis",
           os.path.abspath(exe)]
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env(), stdin=fin,
                           capture_output=True, text=True, timeout=timeout)
        out = p.stdout + p.stderr
        m = _HAZ.search(out)
        hz = int(m.group(1)) if m else None
        if hz is None:
            verdict = "no-summary"
        else:
            verdict = "RACE" if hz > 0 else "clean"
        return {"name": name, "hazards": hz if hz is not None else "",
                "verdict": verdict, "rc": p.returncode}
    except subprocess.TimeoutExpired:
        return {"name": name, "hazards": "", "verdict": "timeout", "rc": 124}
    finally:
        if stdin:
            fin.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--exe", action="append", default=[],
                    help="NAME=/abs/exe[,stdin=/abs/in]")
    args = ap.parse_args()
    rows = []
    for spec in args.exe:
        name, rest = spec.split("=", 1)
        parts = rest.split(",")
        exe = parts[0]
        stdin = None
        for extra in parts[1:]:
            if extra.startswith("stdin="):
                stdin = extra[len("stdin="):]
        r = run(name, exe, stdin, args.timeout)
        rows.append(r)
        print(f"  {name}: {r['verdict']} hazards={r['hazards']} rc={r['rc']}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "hazards", "verdict", "rc"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
