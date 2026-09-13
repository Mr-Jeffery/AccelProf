#!/usr/bin/env python3
"""Re-run the static leg + aggregation on EXISTING traces (no GPU, no re-tracing).

Validates pure-Python detector changes (sync_dominance) fast: for each program
stem, find the newest dependency_<stem>_* dir and its <stem>_eval_cubins next to
it, run aggregate.emit_row, print the summary line. Optional --csv appends rows.

    python eval/reanalyze.py --bindir eval/bin/E0 --python-dir python \
        reduction_norace graph-connectivity_racy [--assume-warp-lockstep] [--label racy]
"""
import argparse
import glob
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aggregate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stems", nargs="+")
    ap.add_argument("--bindir", required=True)
    ap.add_argument("--python-dir", required=True)
    ap.add_argument("--suite", default="reanalyze")
    ap.add_argument("--label", default="")
    ap.add_argument("--csv", default="")
    ap.add_argument("--detail-dir", default="")
    ap.add_argument("--assume-warp-lockstep", action="store_true")
    args = ap.parse_args()
    for stem in args.stems:
        deps = sorted(glob.glob(os.path.join(args.bindir, f"dependency_{stem}_*")),
                      key=os.path.getmtime)
        cub = os.path.join(args.bindir, f"{stem}_eval_cubins")
        if not deps or not os.path.isdir(cub):
            print(f"{stem}: no depdir/cubins under {args.bindir}")
            continue
        ns = types.SimpleNamespace(
            python_dir=args.python_dir, depdir=deps[-1], cubindir=cub, log="",
            suite=args.suite, program=stem, variant="reanalyze", label=args.label,
            input="", csv=args.csv,
            detail=(os.path.join(args.detail_dir, f"{stem}__reanalyze.json")
                    if args.detail_dir else ""),
            assume_warp_lockstep=args.assume_warp_lockstep)
        aggregate.emit_row(ns)


if __name__ == "__main__":
    main()
