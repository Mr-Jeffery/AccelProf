#!/usr/bin/env python3
"""Build selected HeCBench CUDA apps for sm_86 (each Makefile builds `main`).

    python eval/build_hecbench.py --src /abs/HeCBench/src --out /abs/eval/bin/E4 \
        --apps nbody-cuda,mandelbrot-cuda,stencil1d-cuda,bitonic-sort-cuda
"""
import argparse
import os
import shutil
import subprocess

CUDA_HOME = "/home/fzheng4/spack/opt/spack/linux-zen2/cuda-12.9.0-owxskbbrhugkzflau7xe3gyqnvdqlfyw"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apps", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    env = os.environ.copy()
    env["PATH"] = f"{CUDA_HOME}/bin:/usr/bin:/bin"
    env["CUDA_HOME"] = CUDA_HOME
    for app in args.apps.split(","):
        d = os.path.join(args.src, app)
        if not os.path.isdir(d):
            print(f"  MISS {app}: no dir"); continue
        subprocess.run(["make", "clean"], cwd=d, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        r = subprocess.run(["make", "ARCH=sm_86", "CC=nvcc",
                            'EXTRA_CFLAGS=-ccbin /usr/bin/g++'], cwd=d, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        prog = os.path.join(d, "main")
        if r.returncode == 0 and os.path.exists(prog):
            shutil.copy(prog, os.path.join(args.out, app))
            print(f"  OK   {app}")
        else:
            print(f"  FAIL {app}: {r.stderr.decode()[-160:].strip()}")


if __name__ == "__main__":
    main()
