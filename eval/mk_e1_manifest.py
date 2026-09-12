#!/usr/bin/env python3
"""Build the E1 (Indigo3) manifest from compiled executables.

Filters to a clean labeled sample: a program is kept only if its sole active
planted bug is RaceBug and/or SyncBug (data-race / missing-barrier — the classes
this detector targets); programs with other active bugs (bounds, uninitialized,
livelock, ...) are skipped. Label: racy if RaceBug|SyncBug active, else race-free
(pure nobug baseline). Indigo binaries run as: <exe> <graph.egr> <runs> <src> <threads>.
"""
import argparse
import glob
import json
import os

BUGS = ["RaceBug", "SyncBug", "NbrBoundsBug", "NborBoundsBug", "ExcessThreadsBug",
        "LivelockBug", "FieldBug", "OverflowBug", "BoundsBug", "PrecedenceBug",
        "UninitializedBug"]
RACE_BUGS = {"RaceBug", "SyncBug"}


def active_bugs(name):
    # match underscore-delimited tokens exactly: "BoundsBug" is a substring of
    # "NbrBoundsBug", so substring matching false-flags every bounds-bug name.
    # The inactive form is a distinct token ("NoNbrBoundsBug"), so token membership
    # of the bare bug name already means "active".
    parts = set(os.path.splitext(name)[0].split("_"))
    return {b for b in BUGS if b in parts}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe-dir", required=True)
    ap.add_argument("--graph", required=True, help="abs path to a .egr input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--detail-dir", required=True)
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    progs, skipped = [], 0
    for p in sorted(glob.glob(f"{args.exe_dir}/**/*", recursive=True)):
        if not (os.path.isfile(p) and os.access(p, os.X_OK)):
            continue
        name = os.path.basename(p)
        bugs = active_bugs(name)
        if bugs - RACE_BUGS:            # some non-race bug present -> skip
            skipped += 1
            continue
        racy = bool(bugs & RACE_BUGS)
        algo = name.split("_")[0]
        atomic = "CudaAtomic" if "CudaAtomic" in name else "Atomic"
        style = "+".join([algo, atomic] + sorted(bugs) if bugs else [algo, atomic, "nobug"])
        progs.append({
            "suite": "E1", "program": algo, "variant": style,
            "label": "racy" if racy else "race-free", "input": "torus100",
            "exe": os.path.abspath(p),
            "args": [args.graph, "1", "0", "1"], "oracle": False,
            "reps": 1, "timeout": args.timeout,
        })
    man = {"csv": os.path.abspath(args.csv),
           "detail_dir": os.path.abspath(args.detail_dir), "programs": progs}
    with open(args.out, "w") as f:
        json.dump(man, f, indent=2)
    racy = sum(p["label"] == "racy" for p in progs)
    print(f"{len(progs)} clean programs ({racy} racy, {len(progs)-racy} race-free); "
          f"{skipped} skipped (other bug) -> {args.out}")


if __name__ == "__main__":
    main()
