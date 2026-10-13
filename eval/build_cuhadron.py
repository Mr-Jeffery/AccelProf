#!/usr/bin/env python3
"""Build cuHadron for sm_86, both FIXED variants (race-present / synchronized).

The Makefile auto-selects categories whose min_arch <= 86 (skips bulkcpy, dsmem
= sm_90). FIXED=0 and FIXED=1 produce the same filenames, so we build one, copy
with a suffix, clean, build the other. Copies land in <out> as
<category>__<name>__{racy,fixed}.sm86.out.

    python eval/build_cuhadron.py --dir /abs/cuHadron --out /abs/eval/bin/E2
"""
import argparse
import glob
import os
import shutil
import subprocess

CUDA_HOME = "/home/fzheng4/spack/opt/spack/linux-zen2/cuda-12.9.0-owxskbbrhugkzflau7xe3gyqnvdqlfyw"


def env():
    e = os.environ.copy()
    e["PATH"] = f"{CUDA_HOME}/bin:/usr/bin:/bin"
    e["CUDA_HOME"] = CUDA_HOME
    return e


def build_variant(cdir, fixed, out, suffix):
    subprocess.run(["make", "clean", "ARCH=sm_86"], cwd=cdir, env=env(),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    r = subprocess.run(["make", "-j4", "ARCH=sm_86", f"FIXED={fixed}"], cwd=cdir,
                       env=env(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    bins = glob.glob(f"{cdir}/**/*.sm86.out", recursive=True)
    n = 0
    for b in bins:
        cat = os.path.basename(os.path.dirname(b))
        name = os.path.basename(b).replace(".sm86.out", "")
        dst = os.path.join(out, f"{cat}__{name}__{suffix}.sm86.out")
        shutil.copy(b, dst)
        n += 1
    print(f"  FIXED={fixed} ({suffix}): built {n} binaries "
          f"(rc={r.returncode}){' err:'+r.stderr.decode()[-160:] if r.returncode and not n else ''}")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    build_variant(args.dir, 0, args.out, "racy")
    build_variant(args.dir, 1, args.out, "fixed")
    subprocess.run(["make", "clean", "ARCH=sm_86"], cwd=args.dir, env=env(),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    got = sorted(os.path.basename(p) for p in glob.glob(f"{args.out}/*.sm86.out"))
    print(f"total {len(got)} binaries in {args.out}")
    for g in got:
        print("  " + g)


if __name__ == "__main__":
    main()
