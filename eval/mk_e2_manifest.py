#!/usr/bin/env python3
"""Build the E2 (cuHadron) manifest from eval/bin/E2/<cat>__<name>__<variant>.sm86.out.

Labels: FIXED build (variant 'fixed') -> race-free; the false_positives category is
benign by design -> race-free even in its 'racy' build (the detector must NOT flag
it); every other 'racy' build -> racy. cuHadron tests are self-contained (no args)."""
import argparse
import glob
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--detail-dir", required=True)
    args = ap.parse_args()

    progs = []
    for p in sorted(glob.glob(f"{args.bin}/*.sm86.out")):
        base = os.path.basename(p)[:-len(".sm86.out")]
        cat, name, variant = base.split("__")
        if variant == "fixed":
            label = "race-free"
        elif cat == "false_positives":
            label = "race-free"
        else:
            label = "racy"
        progs.append({
            "suite": "E2", "program": f"{cat}/{name}", "variant": variant,
            "label": label, "input": "default", "exe": os.path.abspath(p),
            # cuHadron microbenchmarks run in <5s natively; some (cp.async, multigpu)
            # can hang under Compute-Sanitizer, so cap timeout low so hangs self-recover.
            "args": [], "oracle": True, "reps": 1, "timeout": 30,
        })
    man = {"csv": os.path.abspath(args.csv),
           "detail_dir": os.path.abspath(args.detail_dir), "programs": progs}
    with open(args.out, "w") as f:
        json.dump(man, f, indent=2)
    print(f"{len(progs)} programs -> {args.out}")


if __name__ == "__main__":
    main()
