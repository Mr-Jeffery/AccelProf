#!/usr/bin/env python3
"""X9 deliverable eval/results/cutlass/x9.csv: one row per binary x kernel x mode.
Analyzed kernels (sub-ids <parent>__kNNN and the gate ids): two rows, mode scalar-clock (the True half of
--both-barrier-orders, results/<flavor>/baselines-cuvein-shard<sid>-all.csv) and mode collector-only (the False half,
baselines-cuvein-bo0-shard<sid>-all.csv); pair counts by status from pairs/<flavor>/<sid>.json; recording figures from
the parent's meta.json copy (eval/x_logs/store_copy/<flavor>/<parent>/meta.json).
Recorded ids with no analyzed kernel get one row, kernel "-", mode "record", and `outcome` saying why (TIMEOUT
re-recorded at 5,400 s or split, TIMEOUT1 final, NO-KERNELS, DUPLICATE of another id, NOT-ANALYZED).
usage: x9_csv.py [--out eval/results/cutlass/x9.csv] [--timeout1 ids...] [--duplicate ids...]"""
import argparse, csv, glob, json, os, re
W = "/home/fzheng4/wt-x9"
ap = argparse.ArgumentParser()
ap.add_argument("--out", default=f"{W}/eval/results/cutlass/x9.csv")
ap.add_argument("--timeout1", nargs="*", default=[])
ap.add_argument("--duplicate", nargs="*", default=[])
a = ap.parse_args()
man = {r["id"]: r for r in csv.DictReader(open(f"{W}/eval/cutlass/manifest_cutlass.csv", newline=""))}
kname = {}
for f in glob.glob(f"{W}/eval/cutlass/manifests_k/*.csv"):
    for r in csv.DictReader(open(f, newline="")):
        kname[r["id"]] = r.get("kernel", "")
def meta(fl, pid):
    try:
        m = json.load(open(f"{W}/eval/x_logs/store_copy/{fl}/{pid}/meta.json"))
        return m, m["modes"]["scalar-clock"]["reps"][0]
    except (OSError, ValueError, KeyError, IndexError):
        return {}, {}
def row1(path):
    try:
        return next(csv.DictReader(open(path, newline="")))
    except (OSError, StopIteration):
        return {}
COLS = ["binary", "family", "parent_id", "flavor", "sub_id", "kernel", "launches", "mode", "outcome", "verdict",
        "reports_dedup", "report_lines", "pairs", "CONFIRMED", "BARRIER_ORDERED", "RECLASSIFIED", "ON_ONLY",
        "analysis_s", "record_wall_s", "record_peak_mb", "record_rc", "record_timed_out", "record_complete",
        "record_nkernels", "native_wall_s", "tool_timeout_s", "node"]
rows, analyzed_parents = [], set()
for fl in ("main", "t5400"):
    for p in sorted(glob.glob(f"{W}/eval/results/cutlass/pairs/{fl}/*.json")):
        sid = os.path.basename(p)[:-5]
        pid = sid.split("__k")[0]
        mr = man.get(pid, {})
        d = json.load(open(p))
        sc = d.get("status_counts", {}) or {}
        ks = d.get("kernels", {}) or {}
        kn = kname.get(sid) or (";".join(k.split("::", 1)[-1] for k in ks) if isinstance(ks, dict) else "")
        launches = sum(ks.values()) if isinstance(ks, dict) else ""
        m, r = meta(fl, pid)
        tm = row1(f"{W}/eval/results/cutlass/{fl}/analysis-time-shard{sid}-all.csv")
        analyzed_parents.add((fl, pid))
        for mode, pre, tk in (("scalar-clock", "baselines-cuvein-shard", "t_barrier_order_on_s"),
                              ("collector-only", "baselines-cuvein-bo0-shard", "t_barrier_order_off_s")):
            v = row1(f"{W}/eval/results/cutlass/{fl}/{pre}{sid}-all.csv")
            rows.append(dict(binary=os.path.basename(mr.get("exe", "")), family=mr.get("target", ""), parent_id=pid,
                             flavor=fl, sub_id=sid, kernel=kn, launches=launches, mode=mode, outcome="ANALYZED",
                             verdict=v.get("verdict", "missing"), reports_dedup=v.get("reports_dedup", ""),
                             report_lines=v.get("report_lines", ""), pairs=d.get("pairs", ""),
                             CONFIRMED=sc.get("CONFIRMED", 0), BARRIER_ORDERED=sc.get("BARRIER-ORDERED", 0),
                             RECLASSIFIED=sc.get("RECLASSIFIED", 0), ON_ONLY=sc.get("ON-ONLY", 0),
                             analysis_s=tm.get(tk, ""), record_wall_s=r.get("wall", ""), record_peak_mb=r.get("peak_mb", ""),
                             record_rc=r.get("rc", ""), record_timed_out=r.get("timed_out", ""),
                             record_complete=r.get("complete", ""), record_nkernels=r.get("nkernels", ""),
                             native_wall_s=m.get("native_wall", ""), tool_timeout_s=m.get("tool_timeout", ""),
                             node=m.get("node", "")))
for fl in ("main", "t5400"):
    for md in sorted(glob.glob(f"{W}/eval/x_logs/store_copy/{fl}/*")):
        pid = os.path.basename(md)
        if (fl, pid) in analyzed_parents:
            continue
        m, r = meta(fl, pid)
        mr = man.get(pid, {})
        if pid in a.duplicate:
            out = "DUPLICATE"
        elif r.get("timed_out"):
            out = "TIMEOUT1" if pid in a.timeout1 else "TIMEOUT"
        elif r.get("nkernels", 0) == 0:
            out = "NO-KERNELS"
        else:
            out = "NOT-ANALYZED"
        rows.append(dict(binary=os.path.basename(mr.get("exe", "")), family=mr.get("target", ""), parent_id=pid, flavor=fl,
                         sub_id="", kernel="-", launches="", mode="record", outcome=out, verdict="",
                         record_wall_s=r.get("wall", ""), record_peak_mb=r.get("peak_mb", ""), record_rc=r.get("rc", ""),
                         record_timed_out=r.get("timed_out", ""), record_complete=r.get("complete", ""),
                         record_nkernels=r.get("nkernels", ""), native_wall_s=m.get("native_wall", ""),
                         tool_timeout_s=m.get("tool_timeout", ""), node=m.get("node", "")))
with open(a.out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)
c = {}
for x in rows:
    c[x["outcome"]] = c.get(x["outcome"], 0) + 1
print(f"{len(rows)} rows -> {a.out}; by outcome {c}")
