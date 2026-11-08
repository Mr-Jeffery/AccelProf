#!/usr/bin/env python3
"""X1 step 5 sanity checks over the final recording's stores (BeeGFS: run on a compute node).

  .env/bin/python eval/baselines/setup/final_sanity.py --merged eval/results/baselines-cuvein.csv \
      --store /mnt/beegfs/$USER/cuvein_traces/final-2026-10:1200 \
      --store /mnt/beegfs/$USER/cuvein_traces/final-2026-10-long:5400:eval/results/final-long \
      --store /mnt/beegfs/$USER/cuvein_traces/final-2026-10-long-sc:5400:eval/results/final-long-sc \
      --out eval/results/final/sanity.json

(a) every <store>/<id>/meta.json: hb_dump false, the frozen runtime hashes (FROZEN), status
    done, arch 8.9, no excluded node, the store's cap as tool_timeout_cap AND as tool_timeout
    (floor = cap); every saved kernel JSON: no hb_events, hb_aggregates 1, hb_sync_pass,
    hb_rmw_points, hb_stats present (vector-clock also hb_races, hb_chain).
(c) the (id, mode) rows whose saved kernel JSONs carry a non-empty tv_violation, per suite.
(d) no merged RACE/CLEAN row rests on the static leg alone: a vector-clock row needs hb_races
    in every saved kernel JSON of its mode, a scalar-clock row hb_sync_pass (the barrier-only
    pass's stand-in without a dump); a row that lacks it is listed (it should be ERROR).
--store DIR:CAP[:RESULTS]: the (id, mode) -> store mapping: a store given with RESULTS (a shard-CSV
directory) owns every (id, mode) those CSVs hold; the first store owns the rest -- the same rule as
merge --override.
"""
import argparse
import collections
import csv
import glob
import json
import os

FROZEN = dict(collector="ee78cb899e8a0a65", libsanalyzer="2201fcb7d57ae783",
              fatbin="a2d7368bc1c61986", fatbin_late="e96343121c74ca0a")
BAD_NODES = {"c54", "c2", "c21", "c37"}
if os.environ.get("FINAL_B"):   # X1b: the T22 cont. + T23 + T24 install (f551ca0); c23, c46 have no /home
    FROZEN = dict(collector="b746b4dd23e90f46", libsanalyzer="5a20fd14ab6c6806",
                  fatbin="a2d7368bc1c61986", fatbin_late="e96343121c74ca0a")
    BAD_NODES |= {"c23", "c46"}
MODES = ("vector-clock", "scalar-clock")
NEED = {"vector-clock": ("hb_aggregates", "hb_sync_pass", "hb_rmw_points", "hb_stats",
                         "hb_races", "hb_chain"),
        "scalar-clock": ("hb_aggregates", "hb_sync_pass", "hb_rmw_points", "hb_stats")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", required=True)
    ap.add_argument("--store", action="append", required=True, help="DIR:CAP[:RESULTS]")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    stores, owner = [], {}
    for spec in a.store:
        parts = spec.split(":")
        stores.append((parts[0], int(parts[1])))
        if len(parts) > 2:
            for f in glob.glob(f"{parts[2]}/baselines-cuvein-shard*.csv"):
                owner.update({(r["id"], r["mode"]): parts[0] for r in csv.DictReader(open(f, newline=""))})

    res = dict(meta=collections.Counter(), meta_bad=[], kernels=collections.Counter(),
               kernel_bad=[], tv=collections.defaultdict(list), static_only=[],
               nodes=collections.Counter(), mem_gb=collections.Counter())
    kinfo = {}                                     # (store, id, mode) -> per-kernel summary
    for store, cap in stores:
        for md in sorted(glob.glob(f"{store}/*/meta.json")):
            idir = os.path.dirname(md)
            _id = os.path.basename(idir)
            try:
                m = json.load(open(md))
            except (OSError, ValueError) as e:
                res["meta_bad"].append([store, _id, f"unreadable meta: {e}"])
                continue
            res["meta"][os.path.basename(store)] += 1
            res["nodes"][m.get("node", "?")] += 1
            res["mem_gb"][str(m.get("mem_total_gb"))] += 1
            bad = []
            if m.get("hb_dump") is not False:
                bad.append(f"hb_dump={m.get('hb_dump')}")
            rt = m.get("runtime") or {}
            for k, v in FROZEN.items():
                if rt.get(k) != v:
                    bad.append(f"{k}={rt.get(k)}")
            if m.get("status") != "done":
                bad.append(f"status={m.get('status')}")
            if m.get("error"):
                bad.append(f"error={m.get('error')}")   # missing-exe: reported, not a defect
            if os.environ.get("FINAL_B") and not m.get("error") and                     (m.get("hb_shards") or {}).get("scalar-clock") != int(os.environ.get("FINAL_B_SHARDS", "16")):
                bad.append(f"hb_shards={m.get('hb_shards')}")
            if str(m.get("arch")) != "8.9":
                bad.append(f"arch={m.get('arch')}")
            if m.get("node") in BAD_NODES:
                bad.append(f"node={m.get('node')}")
            if not m.get("error"):
                if m.get("tool_timeout_cap") != cap:
                    bad.append(f"cap={m.get('tool_timeout_cap')}")
                if m.get("tool_timeout") != cap:
                    bad.append(f"tool_timeout={m.get('tool_timeout')}")
            if bad:
                res["meta_bad"].append([os.path.basename(store), _id, ";".join(bad)])
            for mode in MODES:
                kjs = sorted(glob.glob(f"{idir}/{mode}/kernel_*.json"))
                if not kjs:
                    continue
                summ = dict(n=len(kjs), tv=[], missing=collections.Counter())
                for kj in kjs:
                    try:
                        t = json.load(open(kj))
                    except (OSError, ValueError) as e:
                        res["kernel_bad"].append([os.path.basename(store), _id, mode,
                                                  os.path.basename(kj), f"unreadable: {e}"])
                        continue
                    res["kernels"][mode] += 1
                    if "hb_events" in t:
                        res["kernel_bad"].append([os.path.basename(store), _id, mode,
                                                  os.path.basename(kj), "hb_events present"])
                    if t.get("hb_aggregates") != 1:
                        res["kernel_bad"].append([os.path.basename(store), _id, mode,
                                                  os.path.basename(kj), "hb_aggregates != 1"])
                    for k in NEED[mode]:
                        if k not in t:
                            summ["missing"][k] += 1
                    if t.get("tv_violation"):
                        summ["tv"].append([os.path.basename(kj), str(t["tv_violation"])[:200]])
                kinfo[(store, _id, mode)] = summ
                if summ["missing"]:
                    res["kernel_bad"].append([os.path.basename(store), _id, mode, "*",
                                              f"missing {dict(summ['missing'])} of {len(kjs)}"])

    main_store = stores[0][0]
    rows = list(csv.DictReader(open(a.merged, newline="")))
    seen = set()
    for r in rows:
        key = (r["id"], r["mode"])
        if not r["mode"] or key in seen:
            continue
        seen.add(key)
        store = owner.get(key, main_store)
        s = kinfo.get((store, r["id"], r["mode"]))
        if s and s["tv"]:
            res["tv"][f"{r['pset']}|{r['mode']}"].append([r["id"], len(s["tv"]), s["n"], s["tv"][0][1]])
        need = "hb_races" if r["mode"] == "vector-clock" else "hb_sync_pass"
        if r["verdict"] in ("RACE", "CLEAN") and (not s or s["missing"].get(need)):
            res["static_only"].append([r["id"], r["mode"], r["verdict"],
                                       "no saved kernel JSON" if not s else
                                       f"{need} missing in {s['missing'][need]} of {s['n']}"])
    out = dict(meta=dict(res["meta"]), meta_bad=res["meta_bad"], kernels=dict(res["kernels"]),
               kernel_bad=res["kernel_bad"], nodes=dict(res["nodes"]), mem_gb=dict(res["mem_gb"]),
               tv={k: v for k, v in sorted(res["tv"].items())},
               tv_counts={k: len(v) for k, v in sorted(res["tv"].items())},
               static_only=res["static_only"], frozen=FROZEN)
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"meta.json: {dict(res['meta'])}; bad {len(res['meta_bad'])}")
    for b in res["meta_bad"][:40]:
        print("  meta", b)
    print(f"kernel JSONs: {dict(res['kernels'])}; bad {len(res['kernel_bad'])}")
    for b in res["kernel_bad"][:40]:
        print("  kernel", b)
    print(f"nodes: {dict(sorted(res['nodes'].items()))}")
    print(f"tv_violation (id, mode) rows per suite|mode: {out['tv_counts']}")
    print(f"static-leg-only RACE/CLEAN rows: {len(res['static_only'])}")
    for b in res["static_only"][:40]:
        print("  static", b)


if __name__ == "__main__":
    main()
