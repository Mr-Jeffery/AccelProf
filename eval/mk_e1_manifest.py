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
import re

# pinned style axes / boilerplate tokens that carry no information in the slug
NOISE = {"CUDA", "V", "Thread", "NonPersist", "IntType", "Atomic", "CudaAtomic",
         "Data", "Push", "ReadWrite", "NonDup"}
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
    ap.add_argument("--graph", required=True, action="append",
                    help="abs path to a .egr input (repeatable: one program per graph)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--detail-dir", required=True)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--only", default="", help="comma substrings; keep matching names")
    args = ap.parse_args()
    only = [s for s in args.only.split(",") if s]

    progs, skipped = [], 0
    for p in sorted(glob.glob(f"{args.exe_dir}/**/*", recursive=True)):
        if not (os.path.isfile(p) and os.access(p, os.X_OK)):
            continue
        name = os.path.basename(p)
        if only and not any(s in name for s in only):
            continue
        bugs = active_bugs(name)
        if bugs - RACE_BUGS:            # some non-race bug present -> skip
            skipped += 1
            continue
        racy = bool(bugs & RACE_BUGS)
        parts = name.split("_")
        algo = parts[0]
        atomic = "CudaAtomic" if "CudaAtomic" in parts else "Atomic"
        # keep every distinguishing style token (e.g. TC's BlockAdd/GlobalAdd/Reduction,
        # Determ/NonDeterm) in the slug: it keys the detail file, and flavors that
        # shared a slug overwrote each other's details.
        extra = [t for t in parts[1:]
                 if t not in NOISE and t not in BUGS and not t.startswith("No")]
        style = "+".join([algo, *extra, atomic, *(sorted(bugs) or ["nobug"])])
        for graph in args.graph:
            m = re.search(r"(\d+)n_", os.path.basename(graph))
            tag = (m.group(1) + "n") if m else os.path.splitext(os.path.basename(graph))[0]
            progs.append({
                "suite": "E1", "program": algo, "variant": style,
                "label": "racy" if racy else "race-free", "input": tag,
                "exe": os.path.abspath(p),
                "args": [graph, "1", "0", "1"], "oracle": False,
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
