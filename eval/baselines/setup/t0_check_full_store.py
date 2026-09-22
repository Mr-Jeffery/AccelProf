#!/usr/bin/env python3
"""T0 acceptance check of an uncapped BeeGFS store (run where BeeGFS is mounted):

  .env/bin/python eval/baselines/setup/t0_check_full_store.py /mnt/beegfs/$USER/cuvein_traces/full-2026-09-22

For every <id>/meta.json: is each mode either SAVED (complete or partial-prefix dump),
PARTIAL-DUMP (timed-out rep's prefix kept under <mode>-partial-rep<k>/), TIMEOUT-EMPTY
(every rep timed out with a 0-byte dump -- nothing to keep, the TIMEOUT rows are the
marker), ERROR (collect_one recorded an error) -- anything else is UNEXPLAINED.
Also lists the programs whose saved dumps exceed 20 GB (the acceptance case) and the
biggest partial dumps. Prints a markdown table for eval/STORAGE.md.
"""
import glob
import json
import os
import sys


def size(paths):
    t = 0
    for p in paths:
        try:
            t += os.path.getsize(p)
        except OSError:
            pass
    return t


def classify(idir, meta, mode):
    mm = meta.get("modes", {}).get(mode)
    saved_b = size(glob.glob(f"{idir}/{mode}/kernel_*.json"))
    part = sorted(glob.glob(f"{idir}/{mode}-partial-rep*"))
    part_b = sum(size(glob.glob(f"{p}/kernel_*.json")) for p in part)
    if meta.get("error"):
        return "ERROR:" + meta["error"], saved_b, part_b
    if mm is None:
        return "UNEXPLAINED:mode-missing" + (":collecting" if meta.get("status") == "collecting" else ""), saved_b, part_b
    reps = mm.get("reps", [])
    if mm.get("saved"):
        if saved_b == 0:
            return "UNEXPLAINED:saved-but-empty-on-disk", saved_b, part_b
        return ("SAVED-partial-prefix" if mm.get("partial") else "SAVED"), saved_b, part_b
    if mm.get("partial_dump"):
        if part_b == 0:
            return "UNEXPLAINED:partial_dump-but-empty", saved_b, part_b
        return f"PARTIAL-DUMP:{mm['partial_dump']}", saved_b, part_b
    if reps and all(r.get("timed_out") for r in reps):
        if all((r.get("dump_mb") or 0) == 0 for r in reps):
            return "TIMEOUT-EMPTY", saved_b, part_b
        return "UNEXPLAINED:timed-out-with-dump-but-nothing-kept", saved_b, part_b
    if reps and all((r.get("nkernels") or 0) == 0 for r in reps):
        return "NO-KERNEL-JSON(rc=%s)" % reps[0].get("rc"), saved_b, part_b
    return "UNEXPLAINED", saved_b, part_b


def main():
    store = sys.argv[1].rstrip("/")
    modes = ("engine", "trace-only")
    try:
        modes = tuple(json.load(open(f"{store}/STORE_INFO.json")).get("modes") or modes)
    except (OSError, ValueError):
        pass
    rows, counts, big, unexplained = [], {}, [], []
    for md in sorted(glob.glob(f"{store}/*/meta.json")):
        idir = os.path.dirname(md)
        _id = os.path.basename(idir)
        try:
            meta = json.load(open(md))
        except ValueError:
            rows.append((_id, "UNREADABLE-META", "", 0, 0)); unexplained.append(_id); continue
        cells = []
        for mode in modes:
            c, sb, pb = classify(idir, meta, mode)
            counts[(mode, c.split(":")[0])] = counts.get((mode, c.split(":")[0]), 0) + 1
            if c.startswith("UNEXPLAINED"):
                unexplained.append(f"{_id}/{mode}: {c}")
            if sb > 20e9:
                big.append((_id, mode, sb))
            cells.append((c, sb, pb))
        rows.append((_id, meta.get("status"), meta.get("node"), cells))
    print(f"store {store}: {len(rows)} programs, modes {modes}")
    print("\n| mode | state | programs |\n|---|---|---|")
    for (mode, c), n in sorted(counts.items()):
        print(f"| {mode} | {c} | {n} |")
    print("\nSaved dumps above 20 GB (acceptance case):")
    for _id, mode, sb in sorted(big, key=lambda x: -x[2]):
        print(f"  {sb/1e9:7.1f} GB  {mode:10}  {_id}")
    print("\nUNEXPLAINED:", len(unexplained))
    for u in unexplained:
        print("  ", u)
    print("\n| id | status | node | " + " | ".join(f"{m}: state / saved / partial" for m in modes) + " |")
    print("|---|---|---|" + "---|" * len(modes))
    for _id, st, node, cells in rows:
        print(f"| `{_id}` | {st} | {node} | " + " | ".join(
            f"{c} / {sb/1e9:.2f} GB / {pb/1e9:.2f} GB" for c, sb, pb in cells) + " |")
    sys.exit(1 if unexplained else 0)


if __name__ == "__main__":
    main()
