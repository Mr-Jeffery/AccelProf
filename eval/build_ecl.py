#!/usr/bin/env python3
"""Build the ECL-suite egr-input racefree codes (benign races removed) for sm_86.

These read a single ECL binary-CSR .egr graph (same format Indigo uses), so they
run on the Indigo torus100 input. Expected verdict: race-free. Grid/mesh-input
codes (APSP/SCC) use other input formats and are skipped.

    python eval/build_ecl.py --ecl /abs/ECL-suite --out /abs/eval/bin/E3
"""
import argparse
import glob
import os
import subprocess

CUDA_HOME = "/home/fzheng4/spack/opt/spack/linux-zen2/cuda-12.9.0-owxskbbrhugkzflau7xe3gyqnvdqlfyw"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecl", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = f"{CUDA_HOME}/bin:/usr/bin:/bin"
    env["CUDA_HOME"] = CUDA_HOME
    lib = os.path.join(args.ecl, "library")
    srcs = glob.glob(f"{args.ecl}/src/racefree/egr-input/**/*.cu", recursive=True)
    for s in sorted(srcs):
        name = os.path.basename(s)[:-3]              # strip .cu
        out = os.path.join(args.out, name)
        r = subprocess.run(["nvcc", "-arch=sm_86", "-ccbin", "/usr/bin/g++",
                            "-I", lib, "-O3", s, "-o", out],
                           env=env, stderr=subprocess.PIPE)
        ok = r.returncode == 0 and os.path.exists(out)
        print(f"  {'OK  ' if ok else 'FAIL'} {name}"
              + ("" if ok else f": {r.stderr.decode()[-200:].strip()}"))


if __name__ == "__main__":
    main()
