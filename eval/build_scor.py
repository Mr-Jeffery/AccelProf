#!/usr/bin/env python3
"""Build the 7 ScoR benchmark apps for sm_86, both variants (RACEY=0/1).

Each per-dir Makefile builds a binary named after its directory; we copy it to
<outdir>/<name>_{norace,racy}. sm_86 (not the suite's default compute_60) so real
SASS lands in the fatbin for cubin/CFG extraction. Host compiler g++ 13.3.

    python eval/build_scor.py --bench-dir /abs/ScoR/benchmarks --out /abs/eval/bin/E0
"""
import argparse
import os
import shutil
import subprocess

CUDA_HOME = "/home/fzheng4/spack/opt/spack/linux-zen2/cuda-12.9.0-owxskbbrhugkzflau7xe3gyqnvdqlfyw"
BENCHES = ["1dconv", "graph-coloring", "graph-connectivity",
           "matrix-multiplication", "reduction", "rule-110", "uts"]


def env():
    e = os.environ.copy()
    e["PATH"] = f"{CUDA_HOME}/bin:/usr/bin:/bin"
    e["CUDA_HOME"] = CUDA_HOME
    return e


def build(bench_dir, out):
    os.makedirs(out, exist_ok=True)
    for b in BENCHES:
        d = os.path.join(bench_dir, b)
        if not os.path.isdir(d):
            print(f"  SKIP {b}: no dir"); continue
        for racey, tag in ((0, "norace"), (1, "racy")):
            subprocess.run(["make", "clean"], cwd=d, env=env(),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cmd = ["make", "ARCH=-arch=sm_86", "NVCC=nvcc -ccbin /usr/bin/g++"]
            if racey:
                cmd.append("RACEY=1")
            r = subprocess.run(cmd, cwd=d, env=env(),
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            src = os.path.join(d, b)
            dst = os.path.join(out, f"{b}_{tag}")
            if r.returncode == 0 and os.path.exists(src):
                shutil.copy(src, dst)
                print(f"  OK   {b}_{tag}")
            else:
                print(f"  FAIL {b}_{tag}: {r.stderr.decode()[-200:].strip()}")
    subprocess.run(["make", "clean"], cwd=os.path.join(bench_dir, BENCHES[-1]),
                   env=env(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build(args.bench_dir, args.out)


if __name__ == "__main__":
    main()
