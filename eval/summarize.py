#!/usr/bin/env python3
"""Summarize eval CSV rows: confusion counts, precision/recall, tripwires.

    python eval/summarize.py eval/results/E5-micro.csv [more.csv ...]

Precision/recall are computed only over labeled rows (bug_label racy/race-free).
Flags any FN, FP, nonzero tv_violations/unknown_sync, or oracle mismatch.
"""
import csv
import sys
from collections import Counter


def load(paths):
    rows = []
    for p in paths:
        with open(p) as f:
            rows.extend(csv.DictReader(f))
    return rows


def num(r, k):
    v = r.get(k, "")
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def summarize(rows, title=""):
    racy = [r for r in rows if r["bug_label"] == "racy"]
    rf = [r for r in rows if r["bug_label"] in ("race-free", "racefree")]
    TP = sum(num(r, "TP") for r in racy)
    FN = sum(num(r, "FN") for r in racy)
    FP = sum(num(r, "FP") for r in rf)
    TN = sum(num(r, "TN") for r in rf)
    tv = sum(num(r, "tv_violations") for r in rows)
    us = sum(num(r, "unknown_sync") for r in rows)
    struct = sum(num(r, "structural") for r in rows)
    lat = sum(num(r, "latent") for r in rows)
    print(f"=== {title or 'summary'} ===")
    print(f"rows={len(rows)}  labeled: racy={len(racy)} race-free={len(rf)}  "
          f"unlabeled={len(rows)-len(racy)-len(rf)}")
    print(f"TP={TP} FN={FN} FP={FP} TN={TN}")
    if TP + FP:
        print(f"precision = TP/(TP+FP) = {TP/(TP+FP):.4f}")
    if TP + FN:
        print(f"recall    = TP/(TP+FN) = {TP/(TP+FN):.4f}")
    if TN + FP:
        print(f"specificity(race-free clean) = TN/(TN+FP) = {TN/(TN+FP):.4f}")
    print(f"structural(total)={struct} latent(total)={lat}")
    print(f"tv_violations(total)={tv}  unknown_sync(total)={us}")
    print("oracle_verified:", dict(Counter(r.get("oracle_verified", "") for r in rows)))
    fn = [r["program"] for r in racy if num(r, "FN")]
    fp = [r["program"] for r in rf if num(r, "FP")]
    mm = [r["program"] for r in rows if r.get("oracle_verified") == "MISMATCH"]
    tvp = [r["program"] for r in rows if num(r, "tv_violations")]
    if fn:  print("FALSE NEGATIVES:", fn)
    if fp:  print("FALSE POSITIVES:", fp)
    if mm:  print("ORACLE MISMATCH:", mm)
    if tvp: print("TV VIOLATIONS (model_bug):", tvp)
    if not (fn or fp or mm or tvp):
        print("clean: no FN/FP, no oracle mismatch, no tripwire")


if __name__ == "__main__":
    summarize(load(sys.argv[1:]), title=sys.argv[1])
