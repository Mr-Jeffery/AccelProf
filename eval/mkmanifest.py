#!/usr/bin/env python3
"""Build a driver manifest from the executables in a directory.

    python eval/mkmanifest.py --suite E5 --dir ScoR/microbenchmarks/bin \
        --label-rule race_:racy,norace_:race-free --oracle \
        --out eval/manifests/e5.json --csv eval/results/E5.csv

Label rule: comma list of prefix:label; a bare 'all:LABEL' labels every file.
Executable = regular file with +x and no data/source/artifact extension.
"""
import argparse
import json
import os
from pathlib import Path

SKIP_EXT = {".log", ".dot", ".cu", ".cpp", ".c", ".h", ".cuh", ".py", ".txt",
            ".json", ".csv", ".md", ".o", ".so", ".a", ".sh", ".mk", ".in",
            ".png", ".jpg", ".pdf", ".dat", ".bin"}


def label_for(name, rules):
    for pref, lab in rules:
        if pref == "all" or name.startswith(pref):
            return lab
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--detail-dir", default="")
    ap.add_argument("--label-rule", default="all:")
    ap.add_argument("--oracle", action="store_true")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--args", default="", help="space-joined args passed to every exe")
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--only", default="", help="comma substrings; keep only matching")
    ap.add_argument("--exclude", default="", help="comma substrings; drop matching")
    args = ap.parse_args()

    rules = [tuple(r.split(":", 1)) for r in args.label_rule.split(",") if ":" in r]
    d = Path(args.dir)
    files = d.rglob("*") if args.recursive else d.iterdir()
    only = [s for s in args.only.split(",") if s]
    excl = [s for s in args.exclude.split(",") if s]

    progs = []
    for p in sorted(files):
        if not (p.is_file() and os.access(p, os.X_OK)):
            continue
        if p.suffix in SKIP_EXT:
            continue
        if only and not any(s in p.name for s in only):
            continue
        if excl and any(s in p.name for s in excl):
            continue
        progs.append({
            "suite": args.suite, "program": p.name, "variant": "",
            "label": label_for(p.name, rules), "input": "default",
            "exe": str(p.resolve()),
            "args": args.args.split() if args.args else [],
            "oracle": args.oracle, "timeout": args.timeout, "reps": args.reps,
        })

    man = {"csv": str(Path(args.csv).resolve()), "programs": progs}
    if args.detail_dir:
        man["detail_dir"] = str(Path(args.detail_dir).resolve())
    Path(args.out).write_text(json.dumps(man, indent=2) + "\n")
    print(f"{len(progs)} program(s) -> {args.out}")
    for pr in progs:
        print(f"  {pr['program']}  [{pr['label'] or 'unlabeled'}]")


if __name__ == "__main__":
    main()
