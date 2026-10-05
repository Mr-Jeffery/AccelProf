#!/usr/bin/env python3
"""No-dump spot check (merge_check.sh step 2): per program and mode, the kernel-end aggregates of a
YOSEMITE_HB_DUMP=0 recording against two YOSEMITE_HB_DUMP=1 recordings of the same binary, at the
parity key -- hb_races per test_sync_dominance._race_key (device addresses and representative tids
left out: they change run to run), hb_races_sync_only, hb_sync_pass, hb_rmw_points, the counts,
tv_violation. The hb_aggregates marker is written by no-dump files only and is not compared; the
verdicts of sync_dominance.analyze on each recording are compared as well.

    .env/bin/python eval/baselines/setup/nodump_spot_cmp.py /mnt/beegfs/$USER/merge-check-nodump
"""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "python"))
import sync_dominance as sd  # noqa: E402


def race_key(r):   # = python/test_sync_dominance._race_key
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"), r.get("a2_uncertain"))


def canon(t):
    c = lambda v: sorted(json.dumps(x, sort_keys=True) for x in v) if isinstance(v, list) else v
    return {
        "hb_races": sorted(collections.Counter(race_key(r) for r in t.get("hb_races") or []).items(), key=repr),
        "hb_races_sync_only": c(t.get("hb_races_sync_only")),
        "hb_sync_pass": c(t.get("hb_sync_pass")),
        "hb_rmw_points": json.dumps(t.get("hb_rmw_points"), sort_keys=True),
        "hb_events_count": t.get("hb_events_count"),
        "hb_lanes_count": t.get("hb_lanes_count"),
        "tv_violation": t.get("tv_violation"),
    }


def verdicts(run_dir, kj):
    dots = sorted(glob.glob(f"{run_dir}/*_extracted_cubins/*.dot"))
    os.environ["CUVEIN_PREFER_AGGREGATES"] = "1"      # same reader path for every recording
    for dot in dots:
        try:
            rep = sd.analyze(dot, kj)
        except sd.AlignmentError:
            continue
        return sorted((v["current_pc"], v["ancient_pc"], v["verdict"], v.get("hb_class"),
                       v.get("conflict_class"), v["race_type"]) for v in rep["verdicts"])
    return None


root, bad = sys.argv[1], 0
for prog in sorted(os.listdir(root)):
    for mode in sorted(os.listdir(f"{root}/{prog}")):
        got = {}
        for run in ("dump1a", "dump1b", "dump0"):
            d = f"{root}/{prog}/{mode}/{run}"
            ks = sorted(glob.glob(f"{d}/dependency_*/kernel_*.json"))
            got[run] = [(canon(t := json.load(open(k))), "hb_events" in t, verdicts(d, k)) for k in ks]
        def diff(a, b):
            if len(a) != len(b):
                return ["kernel count"]
            out = sorted({f for x, y in zip(a, b) for f in x[0] if x[0][f] != y[0][f]})
            if any(x[2] != y[2] for x, y in zip(a, b)):
                out.append("verdicts")
            return out or None
        d0, d1 = diff(got["dump1a"], got["dump0"]), diff(got["dump1a"], got["dump1b"])
        ok = got["dump0"] and not any(x[1] for x in got["dump0"]) and d0 is None
        bad += not ok
        nv = len(got["dump0"][0][2] or []) if got["dump0"] else 0
        races = sum(c for _, c in got["dump0"][0][0]["hb_races"]) if got["dump0"] else 0
        print(f"{prog} {mode}: {len(got['dump0'])} kernel(s), {nv} verdict(s), {races} hb_races aggregate(s); "
              f"no-dump file has hb_events: {any(x[1] for x in got['dump0'])}; "
              f"dump vs no-dump differ in {d0}; dump vs dump differ in {d1} -> {'EQUAL' if ok else 'NOT EQUAL'}")
print("SPOT CHECK: ALL EQUAL" if not bad else f"SPOT CHECK: {bad} NOT EQUAL")
