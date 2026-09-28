#!/usr/bin/env python3
"""Tabulate analyze_atom.py outputs of run_values.sh (markdown to stdout).
usage: summarize.py DIR   (DIR = $WORK/values)"""
import glob
import json
import os
import re
import sys

d = sys.argv[1]
print("| run | value at | RMWs | values ok | cross-warp pairs | overlapping | inverted | inverted, non-overlapping | exec-interval violations |")
print("|---|---|---|---|---|---|---|---|---|")
for at in ("after", "next"):
    for part in (1, 2, 4):
        j = json.load(open(f"{d}/p{part}_{at}.json"))
        print(f"| part {part} | {at} | {j['rmws']} | {j['ok']} | {j['pairs']} | {j['overlapping']} | "
              f"{j['inverted']} | {j['inverted_nonoverlapping']} | {j['exec_interval_violations']} |")
print()
print("| warps | value at | reps | critical sections | failed CAS | values ok | cross-warp lock-RMW pairs | overlapping | inverted | inverted, non-overlapping | S_k+1 recorded before E_k | hand-offs (k>=1) | rate | inverted by type ('X<trace Y': X recorded first, Y first in coherence order) |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for at in ("after", "next"):
    for cfg, w in (("1x2", 2), ("1x4", 4), ("4x4", 16)):
        js = [json.load(open(f)) for f in sorted(glob.glob(f"{d}/p3_{cfg}_{at}_r*.json"))]
        if not js:
            continue
        s = lambda k: sum(j[k] for j in js)
        ok = all(j["alternation_ok"] and j["n_value_errors"] == 0 for j in js)
        types = {}
        for j in js:
            for k, v in j["inverted_by_type"].items():
                types[k] = types.get(k, 0) + v
        hand = sum(j["critical_sections"] - 1 for j in js)
        sb = s("success_recorded_before_release_read")
        per = ", ".join(str(j["success_recorded_before_release_read"]) for j in js)
        print(f"| {w} | {at} | {len(js)} | {s('critical_sections')} | {s('cas_fail')} | {ok} | {s('pairs')} | "
              f"{s('overlapping')} | {s('inverted')} | {s('inverted_nonoverlapping')} | {sb} ({per}) | {hand} | "
              f"{100.0 * sb / hand:.1f}% | {types} |")
