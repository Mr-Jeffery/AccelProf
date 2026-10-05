#!/usr/bin/env python3
"""T4 parity (design/no_dump.md section 6): on every kernel JSON of a kept store that carries
both the records (hb_events) and HbClock's online aggregates (a T4 runtime with the default
YOSEMITE_HB_DUMP=1), check, per kernel and mode:
  sync   hb_sync_pass == barrier_only_pairs(records) as (pairs, dist, order) -- and in
         vector-clock mode hb_races_sync_only == its triples;
  rmw    hb_rmw_points == trace_rmw_points(records), the lane cutoff lifted;
  verdicts  analyze() from the records == analyze() with CUVEIN_PREFER_AGGREGATES=1, every
         field of every verdict, plus skipped_edges and the candidate diagnostics.
The dump side runs with CUVEIN_BARRIER_PASS_MAX_LANES lifted, so a kernel above the
production cutoff (5 M lane-accesses) is compared on its content; `over_cutoff` marks it (in
production the records give R3 no trace points and no offline pass there, the aggregates do).

  compare  --store <store> --out <json> [--shard k/n] [--cap <s per program>]
  table    <json>...                      -> the per-program / per-mode table
"""
import argparse
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "python"))
import sync_dominance as sd  # noqa: E402

MODES = ("vector-clock", "scalar-clock")
CUTOFF = 5_000_000


def _vkey(v):
    return (frozenset((v["current_pc"], v["ancient_pc"])), v["verdict"], v.get("hb_class"),
            v.get("conflict_class"), v["race_type"], v.get("matrix_class"),
            v["observed_distance"], v["contested_weight"], bool(v.get("event_candidate")),
            bool(v.get("edge_rescued")), v.get("a2_uncertain"), v.get("model_bug"),
            tuple(v["hb_chain"]) if v.get("hb_chain") else None, v["strength"])


def _analyze(dots, kj, prefer):
    if prefer:
        os.environ["CUVEIN_PREFER_AGGREGATES"] = "1"
    else:
        os.environ.pop("CUVEIN_PREFER_AGGREGATES", None)
    for dot in dots:
        try:
            return sd.analyze(dot, kj), dot
        except sd.AlignmentError:
            continue
    return None, None


def compare_kernel(dots, kj):
    t = json.load(open(kj))
    r = {"kernel": os.path.basename(kj), "events": sd.event_count(t), "lanes": sd.lane_count(t)}
    if not t.get("hb_events"):
        r["status"] = "no-hb_events"
        return r
    if "hb_sync_pass" not in t or "hb_rmw_points" not in t:
        r["status"] = "no-aggregates"
        return r
    r["over_cutoff"] = r["lanes"] > CUTOFF
    rep_a, dot = _analyze(dots, kj, False)
    if rep_a is None:
        r["status"] = "unaligned"
        return r
    rep_b, _ = _analyze(dots, kj, True)
    kernels = sd.parse_dot(dot)
    eng = sd.HBGraph(*kernels[sd.select_kernel(kernels, t["kernel"]["kernel_name"])])
    policy = sd.strong_ldst_policy()
    rmw_all = {pc: sc for pc, op in eng.pc_opcode.items() if (sc := sd.atomic_scope(op)) is not None}
    coh_all = {pc: sc for pc, op in eng.pc_opcode.items()
               if (sc := sd.coherent_scope(op, policy)) is not None}
    plain = {k: v for k, v in t.items() if k not in ("hb_sync_pass", "hb_rmw_points")}
    dist, order = {}, {}
    pairs = sd.barrier_only_pairs(plain, rmw_all, coh_all, None, dist, order,
                                  sd.dump_async_pcs(eng, t))
    agg_sync = sd.aggregated_sync_pass(t)
    ok = {"sync": agg_sync == (pairs, dist, order),
          "rmw": sd.aggregated_rmw_points(t) == sd.trace_rmw_points(plain, set(rmw_all), None),
          "verdicts": sorted(map(str, map(_vkey, rep_a["verdicts"])))
                      == sorted(map(str, map(_vkey, rep_b["verdicts"]))),
          "skipped": rep_a["skipped_edges"] == rep_b["skipped_edges"],
          "candidates": rep_a["diagnostics"]["event_candidates"]
                        == rep_b["diagnostics"]["event_candidates"]}
    if t.get("hb_races_sync_only") is not None:
        ok["sync_only_triples"] = t["hb_races_sync_only"] == [[a, b, n] for a, b, n, *_ in t["hb_sync_pass"]]
    r.update(status="ok" if all(ok.values()) else "MISMATCH", checks=ok,
             pairs=len(pairs), verdicts=len(rep_a["verdicts"]),
             sync_diff=_diff(agg_sync, (pairs, dist, order)) if not ok["sync"] else None,
             verdict_diff=_vdiff(rep_a, rep_b) if not ok["verdicts"] else None)
    return r


def _diff(a, b):
    if a is None:
        return "aggregate absent"
    out = []
    for name, x, y in zip(("pairs", "dist", "order"), a, b):
        for k in sorted(set(x) | set(y)):
            if x.get(k) != y.get(k):
                out.append(f"{name}{list(k)}: agg={x.get(k)} rec={y.get(k)}")
            if len(out) >= 10:
                return out
    return out


def _vdiff(a, b):
    ka = {str(_vkey(v)) for v in a["verdicts"]}
    kb = {str(_vkey(v)) for v in b["verdicts"]}
    return {"records_only": sorted(ka - kb)[:5], "aggregates_only": sorted(kb - ka)[:5]}


def compare_program(idir, cap):
    dots = sorted(glob.glob(f"{idir}/dots/*.dot"))
    out = {"id": os.path.basename(idir), "modes": {}}
    for mode in MODES:
        t0 = time.time()
        res = []
        for kj in sorted(glob.glob(f"{idir}/{mode}/kernel_*.json"),
                         key=lambda p: int(re.search(r"kernel_(\d+)", p).group(1))):
            if cap and time.time() - t0 > cap:
                res.append({"kernel": os.path.basename(kj), "status": "cap"})
                continue
            try:
                res.append(compare_kernel(dots, kj))
            except Exception as e:   # a malformed dump is a finding, not a crash of the shard
                res.append({"kernel": os.path.basename(kj), "status": f"error:{type(e).__name__}:{e}"[:200]})
        if res:
            out["modes"][mode] = {"kernels": res, "secs": round(time.time() - t0, 1)}
    return out


def cmd_compare(a):
    os.environ["CUVEIN_BARRIER_PASS_MAX_LANES"] = str(10 ** 12)   # the cutoff lifted (section 6)
    ids = sorted(os.path.basename(p) for p in glob.glob(f"{a.store}/*") if os.path.isdir(p)
                 and os.path.exists(f"{p}/meta.json"))
    if a.ids:
        ids = [i for i in ids if i in set(a.ids.split(","))]
    if a.shard:
        k, n = map(int, a.shard.split("/"))
        ids = ids[k::n]
    results = []
    for i, _id in enumerate(ids):
        print(f"[{i + 1}/{len(ids)}] {_id}", flush=True)
        results.append(compare_program(f"{a.store}/{_id}", a.cap))
        json.dump(results, open(a.out, "w"), indent=1)
    print(f"{len(results)} program(s) -> {a.out}")


def cmd_table(a):
    rows, tot = [], {"kernels": 0, "ok": 0, "mismatch": 0, "no_events": 0, "other": 0, "over_cutoff": 0}
    for f in a.files:
        for prog in json.load(open(f)):
            for mode, m in prog["modes"].items():
                ks = m["kernels"]
                n_ok = sum(k.get("status") == "ok" for k in ks)
                n_mm = sum(k.get("status") == "MISMATCH" for k in ks)
                n_ne = sum(k.get("status") == "no-hb_events" for k in ks)
                n_oc = sum(bool(k.get("over_cutoff")) for k in ks)
                other = len(ks) - n_ok - n_mm - n_ne
                rows.append((prog["id"], mode, len(ks), n_ok, n_mm, n_ne, other, n_oc, m["secs"]))
                for key, v in (("kernels", len(ks)), ("ok", n_ok), ("mismatch", n_mm),
                               ("no_events", n_ne), ("other", other), ("over_cutoff", n_oc)):
                    tot[key] += v
    print("| program | mode | kernels | ok | MISMATCH | no hb_events | other | over cutoff | s |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows):
        print("| " + " | ".join(map(str, r)) + " |")
    print(f"\ntotal: {tot}")
    for f in a.files:
        for prog in json.load(open(f)):
            for mode, m in prog["modes"].items():
                for k in m["kernels"]:
                    if k.get("status") == "MISMATCH":
                        print(f"MISMATCH {prog['id']} {mode} {k['kernel']}: "
                              f"{ {c: v for c, v in k['checks'].items() if not v} } "
                              f"sync={k.get('sync_diff')} verdicts={k.get('verdict_diff')}")
                    elif k.get("status", "ok") not in ("ok", "no-hb_events"):
                        print(f"{k.get('status')} {prog['id']} {mode} {k['kernel']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--store", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--shard", default="")
    c.add_argument("--ids", default="", help="comma list: only these program ids")
    c.add_argument("--cap", type=int, default=3600, help="seconds per program and mode")
    c.set_defaults(fn=cmd_compare)
    t = sub.add_parser("table")
    t.add_argument("files", nargs="+")
    t.set_defaults(fn=cmd_table)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
