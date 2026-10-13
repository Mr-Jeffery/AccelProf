#!/usr/bin/env python3
"""X0 (eval/AGGREGATES_DEFAULT.md): what the new default changes INSIDE the kernels above the
replay's lane cutoff. For every (id, mode, kernel) of x0_over_cutoff.txt in a kept store,
analyze() twice on the same kernel JSON:
  old  CUVEIN_PREFER_RECORDS=1, CUVEIN_BARRIER_PASS_MAX_LANES at its default (5 M) -- the
       pre-X0 production path: no offline sync pass, no R3 trace points above the cutoff
  new  no environment -- the aggregates (hb_sync_pass, hb_rmw_points)
and print, per kernel: the verdict count per (verdict, hb_class) on each side, the
reports (RACE/SC) lost and gained, every pair whose verdict or class changed, and the
candidate diagnostics. A report present in `old` and absent in `new` is LOST.

  x0_kernel_diff.py --store /mnt/beegfs/$USER/cuvein_traces/t20-parity2 \
      --over eval/baselines/setup/x0_over_cutoff.txt --out <json>
"""
import argparse
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "python"))
import sync_dominance as sd  # noqa: E402

CUTOFF = 5_000_000
ENV = ("CUVEIN_PREFER_RECORDS", "CUVEIN_PREFER_AGGREGATES", "CUVEIN_BARRIER_PASS_MAX_LANES")


def analyze(dots, kj, old):
    for k in ENV:
        os.environ.pop(k, None)
    if old:
        os.environ["CUVEIN_PREFER_RECORDS"] = "1"
    for dot in dots:
        try:
            return sd.analyze(dot, kj)
        except sd.AlignmentError:
            continue
    return None


def key(v):
    return (min(v["current_pc"], v["ancient_pc"]), max(v["current_pc"], v["ancient_pc"]),
            v["race_type"])


def compare(dots, kj):
    t = json.load(open(kj))
    lanes = sd.lane_count(t)
    r = {"kernel": os.path.basename(kj), "lanes": lanes, "over_cutoff": lanes > CUTOFF}
    if lanes <= CUTOFF:
        return r
    a, b = analyze(dots, kj, True), analyze(dots, kj, False)
    if a is None or b is None:
        r["status"] = "unaligned"
        return r
    va = {key(v): v for v in a["verdicts"]}
    vb = {key(v): v for v in b["verdicts"]}
    rep = ("RACE", "SC")
    r["old"] = dict(collections.Counter(f"{v['verdict']}/{v.get('hb_class')}" for v in va.values()))
    r["new"] = dict(collections.Counter(f"{v['verdict']}/{v.get('hb_class')}" for v in vb.values()))
    r["lost"] = [[hex(k[0]), hex(k[1]), k[2], va[k]["verdict"], va[k].get("hb_class")]
                 for k in sorted(va) if va[k]["verdict"] in rep
                 and (k not in vb or vb[k]["verdict"] not in rep)]
    r["gained"] = [[hex(k[0]), hex(k[1]), k[2], vb[k]["verdict"], vb[k].get("hb_class")]
                   for k in sorted(vb) if vb[k]["verdict"] in rep
                   and (k not in va or va[k]["verdict"] not in rep)]
    r["changed"] = [[hex(k[0]), hex(k[1]), k[2],
                     f"{va[k]['verdict']}/{va[k].get('hb_class')}/{va[k].get('conflict_class')}",
                     f"{vb[k]['verdict']}/{vb[k].get('hb_class')}/{vb[k].get('conflict_class')}"]
                    for k in sorted(set(va) & set(vb))
                    if (va[k]["verdict"], va[k].get("hb_class"), va[k].get("conflict_class"))
                    != (vb[k]["verdict"], vb[k].get("hb_class"), vb[k].get("conflict_class"))]
    r["only_old"] = len(set(va) - set(vb))
    r["only_new"] = len(set(vb) - set(va))
    r["cand_old"] = a["diagnostics"]["event_candidates"]
    r["cand_new"] = b["diagnostics"]["event_candidates"]
    r["skipped_old"], r["skipped_new"] = len(a["skipped_edges"]), len(b["skipped_edges"])
    r["status"] = "LOST" if r["lost"] else "ok"
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--over", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    todo = [l.split()[:2] for l in open(a.over) if l.strip() and not l.startswith("#")]
    res = []
    for pid, mode in todo:
        dots = sorted(glob.glob(f"{a.store}/{pid}/dots/*.dot"))
        for kj in sorted(glob.glob(f"{a.store}/{pid}/{mode}/kernel_*.json"),
                         key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0])):
            r = compare(dots, kj)
            if not r["over_cutoff"]:
                continue
            r.update(id=pid, mode=mode)
            res.append(r)
            print(json.dumps(r), flush=True)
    json.dump(res, open(a.out, "w"), indent=1)
    lost = sum(bool(r.get("lost")) for r in res)
    print(f"== {len(res)} kernels above the cutoff; {lost} with a lost report")
    sys.exit(1 if lost else 0)


if __name__ == "__main__":
    main()
