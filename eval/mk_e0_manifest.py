#!/usr/bin/env python3
"""Build the E0 (ScoR apps) driver manifest: 7 benchmarks x {norace,racy} x
{small,large}. small -> oracle cross-check; large -> engine-only. Each reads its
stdin input file. false-positive control = the norace (fixed) build."""
import argparse
import json
import os

BENCHES = ["1dconv", "graph-coloring", "graph-connectivity",
           "matrix-multiplication", "reduction", "rule-110", "uts"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True, help="dir with <bench>_{norace,racy}")
    ap.add_argument("--inputs", required=True, help="dir with <bench>.<size>.in")
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--detail-dir", required=True)
    ap.add_argument("--sizes", default="small,large")
    ap.add_argument("--benches", default=",".join(BENCHES))
    args = ap.parse_args()
    sizes = [s for s in args.sizes.split(",") if s]
    benches = [b for b in args.benches.split(",") if b]

    progs = []
    for b in benches:
        for variant, label in (("norace", "race-free"), ("racy", "racy")):
            exe = os.path.join(args.bin, f"{b}_{variant}")
            for size in sizes:
                stdin = os.path.join(args.inputs, f"{b}.{size}.in")
                progs.append({
                    "suite": "E0", "program": b, "variant": variant, "label": label,
                    "input": size, "exe": exe, "args": [], "stdin": stdin,
                    # engine-only: the exact VC oracle is O(threads) per conflict and
                    # impractical on many-kernel real apps (graph-*). engine==oracle
                    # already established on the 33 ScoR litmus + canary.
                    "oracle": False, "reps": 2,
                    "timeout": 200 if size == "small" else 600,
                })
    man = {"csv": os.path.abspath(args.csv),
           "detail_dir": os.path.abspath(args.detail_dir), "programs": progs}
    with open(args.out, "w") as f:
        json.dump(man, f, indent=2)
    print(f"{len(progs)} programs -> {args.out}")


if __name__ == "__main__":
    main()
