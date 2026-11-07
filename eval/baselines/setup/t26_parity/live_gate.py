#!/usr/bin/env python3
"""T26 -> X12: live-recording gate for collector-only kernel JSONs, judged against the baseline's own spread.

Two live recordings of one binary are two executions: the GPU's warp/block interleaving decides which thread touched a
4-byte word last, so the dist split (intra_warp / intra_block / intra_grid) and, when different PCs interleave, the
ancient-PC edge a count lands on move between runs. Exact equality of a live recording is therefore only expected where
the baseline's own runs are exactly equal. This gate enforces, per program and per check, exactly the invariants that ALL
baseline runs satisfy with each other on EVERY kernel of the program, and nothing more (a per-kernel rule overfits: in
dxtc2 the X11 runs gain or lose a rare edge on 11 of 100 kernels, and other runs on other kernels):

  exact        kernel JSON bytes equal
  nodes        the set of node PCs equal
  edges        the set of (current_pc, ancient_pc) edges equal
  edge_totals  per edge, the sum over the dist classes equal (on the common edges)
  grand        the sum of every dist count in the kernel equal
plus per run: the same kernel files, and the drained-record count (meta.json modes.collector-only.events / the rep's
drained_records) equal to the baseline's when the baseline's runs agree on it.

A new rep FAILS if it breaks an enforced check against base[0]. It is a screen for live recordings; it cannot see a pass
bug that only moves counts within the schedule noise -- that is the job of the same-stream replay (t26_parity/sc.sh),
which must be byte-identical. With 3 baseline runs a check can hold in all 3 by luck and break in a 4th run by noise: a
FAIL here is decided by the same-stream replay of that program, not explained away.

  live_gate.py --label crs --base B1 B2 B3 --new N1 [N2 ...] [--json out.json]
     B*/N*: dirs of kernel_<i>.json (X11: .../x11-co-rI-<app>/X11-<app>/collector-only; X12: .../X11-<app>/collector-only-repK)
exit 0 = PASS, 1 = FAIL, 2 = usage / missing data
"""
import argparse
import glob
import itertools
import json
import os
import re
import sys

CHECKS = ("exact", "nodes", "edges", "edge_totals", "grand")


def kfiles(d):
    out = {}
    for f in glob.glob(os.path.join(d, "kernel_*.json")):
        m = re.fullmatch(r"kernel_(\d+)\.json", os.path.basename(f))
        if m:
            out[int(m.group(1))] = f
    return out


def total(e):
    d = e.get("dist") or {}
    return sum(v for v in d.values() if isinstance(v, (int, float)))


def summary(path):
    raw = open(path, "rb").read()
    j = json.loads(raw)
    edges = {(e.get("current_pc"), e.get("ancient_pc")): total(e) for e in j.get("edges") or []}
    nodes = frozenset(n.get("pc") for n in j.get("nodes") or [])
    return {"raw": raw, "nodes": nodes, "edges": edges, "grand": sum(edges.values())}


def checks(a, b):
    common = a["edges"].keys() & b["edges"].keys()
    return {
        "exact": a["raw"] == b["raw"],
        "nodes": a["nodes"] == b["nodes"],
        "edges": a["edges"].keys() == b["edges"].keys(),
        "edge_totals": all(a["edges"][k] == b["edges"][k] for k in common),
        "grand": a["grand"] == b["grand"],
    }


def events(d):
    """drained records of the recording in d (meta.json one level up); None when not recorded."""
    m = os.path.join(os.path.dirname(os.path.abspath(d)), "meta.json")
    if not os.path.exists(m):
        return None
    mode = json.load(open(m)).get("modes", {}).get("collector-only", {})
    rep = re.search(r"-rep(\d+)$", os.path.abspath(d))
    reps = mode.get("reps") or []
    if rep and len(reps) >= int(rep.group(1)) and reps[int(rep.group(1)) - 1].get("drained_records") is not None:
        return reps[int(rep.group(1)) - 1]["drained_records"]
    return mode.get("events")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="")
    ap.add_argument("--base", nargs="+", required=True)
    ap.add_argument("--new", nargs="+", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()
    if len(a.base) < 2:
        print("need >= 2 baseline runs to know their spread"); return 2
    bf = [kfiles(d) for d in a.base]
    if not bf[0]:
        print(f"{a.label} NO-KERNELS in {a.base[0]}"); return 2
    ks = sorted(bf[0])
    base_sets_equal = all(set(f) == set(bf[0]) for f in bf)
    # the checks every baseline pair satisfies on every kernel (nb: per check, kernels where all pairs agree)
    en_prog, nb = set(CHECKS), {c: 0 for c in CHECKS}
    for k in ks:
        sums = [summary(f[k]) for f in bf if k in f]
        en = set(CHECKS)
        for x, y in itertools.combinations(sums, 2):
            r = checks(x, y)
            en &= {c for c in CHECKS if r[c]}
        en_prog &= en
        for c in en:
            nb[c] += 1
    enforced = {k: en_prog for k in ks}
    bev = [events(d) for d in a.base]
    ev_enforced = None not in bev and len(set(bev)) == 1
    print(f"{a.label} baseline: {len(a.base)} runs, {len(ks)} kernels, kernel sets equal={base_sets_equal}, "
          f"drained records {bev} ({'enforced' if ev_enforced else 'not enforced'}); kernels where all baseline runs agree: "
          + " ".join(f"{c}={nb[c]}" for c in CHECKS) + f"; enforced: {' '.join(c for c in CHECKS if c in en_prog) or 'none'}")
    rc, report = 0, {"label": a.label, "kernels": len(ks), "agree_counts": nb, "enforced": sorted(en_prog), "base_events": bev, "new": []}
    for d in a.new:
        nf = kfiles(d)
        fails = {c: [] for c in CHECKS}
        missing = sorted(set(ks) - set(nf)); extra = sorted(set(nf) - set(ks))
        held = {c: 0 for c in CHECKS}
        for k in ks:
            if k not in nf:
                continue
            r = checks(summary(bf[0][k]), summary(nf[k]))
            for c in CHECKS:
                held[c] += bool(r[c])
                if c in enforced[k] and not r[c]:
                    fails[c].append(k)
        ne = events(d)
        ev_fail = ev_enforced and ne != bev[0]
        bad = bool(missing or extra or ev_fail or any(fails.values()))
        rc |= bad
        print(f"{a.label} {'FAIL' if bad else 'PASS'} {d}: missing={len(missing)} extra={len(extra)} drained={ne}"
              f"{' (differs)' if ev_fail else ''}; vs base[0] held " + " ".join(f"{c}={held[c]}" for c in CHECKS)
              + "; enforced-and-broken " + " ".join(f"{c}={len(fails[c])}{fails[c][:5] if fails[c] else ''}" for c in CHECKS))
        report["new"].append({"dir": d, "pass": not bad, "missing": missing, "extra": extra, "events": ne,
                              "held": held, "broken": fails})
    if a.json:
        with open(a.json, "w") as f:
            json.dump(report, f, indent=1)
    print(f"{a.label} GATE {'PASS' if rc == 0 else 'FAIL'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
