#!/usr/bin/env python3
"""X3 (a): cost table, us per warp-level record, from files in eval/results and eval/x1_follow.

Reads only (stdlib, CPU). Writes eval/results/final-tables/cost_rows.csv, cost_fit.csv, cost_table.md.
Run from the worktree root: python3 -I eval/results/final-tables/cost_table.py

Records = the `events=` field of the harness row (hb_events_count; for collector-only runs the
analyzer's drained-record count). Wall = tool wall; native = native_wall_s.
Rows that are TIMEOUT / ERROR / partial(...) are not points of a fit.
"""
import csv, glob, json, os, re, statistics as st

ROOT = os.getcwd()
R = os.path.join(ROOT, "eval", "results")
OUT = os.path.join(R, "final-tables")
X1B = os.path.join(R, "final-b", "merged", "baselines-cuvein.csv")
X1 = os.path.join(R, "baselines-cuvein.csv")
FOL = os.path.join(ROOT, "eval", "x1_follow", "collector")

# the programs X1_FOLLOW.md / SHARDED_SYNC.md measure: (label, harness id, collector-run file prefix)
PROGS = [
    ("P7-heartwall-cuda", "P7-heartwall-cuda", "P7-heartwall-cuda-collector"),
    ("P9-knn-cuda", "P9-knn-cuda", "P9-knn-cuda-collector"),
    ("P7-nbody-cuda", "P7-nbody-cuda", None),
    ("P7-bfs-cuda", "P7-bfs-cuda", None),
    ("P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n",
     "P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n",
     "P1-BFS_CUDA_E_Topo_Determ_IntType_ReadMo-collector"),
    ("P6-interkernel-global_readwrite_race-fixed", "P6-interkernel-global_readwrite_race-fixed",
     "P6-interkernel-global_readwrite_race-fix-collector"),
]


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def note(r, key):
    m = re.search(r"(?:^|;)" + key + r"=([^;]*)", r.get("notes", ""))
    return m.group(1) if m else None


def agg(rows, idv, mode):
    """median over the complete reps of one (id, mode); None when there is no complete rep."""
    rs = [r for r in rows if r["id"] == idv and r["mode"] == mode and r["verdict"] in ("RACE", "CLEAN")
          and "partial" not in r.get("notes", "") and note(r, "events")]
    if not rs:
        return None
    return {
        "wall": st.median(float(r["wall_s"]) for r in rs),
        "native": st.median(float(r["native_wall_s"]) for r in rs),
        "events": int(note(rs[0], "events")),
        "nreps": len(rs),
        "node": ",".join(sorted({note(r, "node") or "?" for r in rs})),
        "peak_mb": max(float(r["peak_mb"]) for r in rs),
    }


def ols(pts):
    n = len(pts)
    if n < 2:
        return None
    mx = sum(x for x, _ in pts) / n
    my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx == 0:
        return None
    b = sum((x - mx) * (y - my) for x, y in pts) / sxx
    a = my - b * mx
    sst = sum((y - my) ** 2 for _, y in pts)
    sse = sum((y - (a + b * x)) ** 2 for x, y in pts)
    return {"n": n, "intercept_s": a, "slope_us_per_record": b * 1e6, "r2": (1 - sse / sst) if sst else float("nan")}


x1b, x1 = load(X1B), load(X1)
rows_out, cols = [], {}


def put(prog, col, runtime, d, src):
    if d is None:
        rows_out.append({"program": prog, "column": col, "runtime": runtime, "wall_s": "missing", "records": "",
                         "native_s": "", "us_per_record": "", "node": "", "source": src})
        return
    us = d["wall"] / d["events"] * 1e6
    rows_out.append({"program": prog, "column": col, "runtime": runtime, "wall_s": f"{d['wall']:.3f}",
                     "records": d["events"], "native_s": f"{d['native']:.3f}", "us_per_record": f"{us:.4g}",
                     "node": d["node"], "source": src})
    cols.setdefault((col, runtime), []).append((d["events"], d["wall"]))


for label, idv, pre in PROGS:
    # collector-only: X1-follow, runtime d38d057 (before T22 cont. / T23 / T24)
    for wk, tag in (("1", "n1"), ("default", "ndefault")):
        d = None
        src = "no collector-only run"
        if pre:
            fn = os.path.join(FOL, f"{pre}-{tag}.json")
            src = f"eval/x1_follow/collector/{pre}-{tag}.json"
            if os.path.exists(fn):
                j = json.load(open(fn))
                nat = sorted(x["wall"] for x in j["native"])
                d = {"wall": j["wall"], "native": nat[len(nat) // 2], "events": j["drained_records"], "node": j["node"]}
        put(label, f"collector-only (-n {wk})", "d38d057 (X1-follow)", d, src)
    put(label, "scalar-clock serial N=1", "d38d057 (X1)", agg(x1, idv, "scalar-clock"), "eval/results/baselines-cuvein.csv")
    for n in (1, 16):
        fn = glob.glob(os.path.join(R, f"t22c-c-{idv}-n{n}", "baselines-cuvein-shard*.csv"))
        d = agg(load(fn[0]), idv, "scalar-clock") if fn else None
        put(label, f"scalar-clock N={n} (T22-cont perf build)", "T22-cont perf build (SHARDED_SYNC II.10)", d,
            f"eval/results/t22c-c-{idv}-n{n}/" if fn else "no step-C run for this id")
    put(label, "scalar-clock sharded N=16", "f551ca0 (X1b)", agg(x1b, idv, "scalar-clock"), "eval/results/final-b/merged/baselines-cuvein.csv")
    put(label, "vector-clock", "d38d057 (X1)", agg(x1, idv, "vector-clock"), "eval/results/baselines-cuvein.csv")
    put(label, "vector-clock", "f551ca0 (X1b)", agg(x1b, idv, "vector-clock"), "eval/results/final-b/merged/baselines-cuvein.csv")

fits = []
for (col, rt), pts in sorted(cols.items()):
    f = ols(pts)
    fits.append({"scope": "program set above", "column": col, "runtime": rt, **(f or {"n": len(pts)})})


def sweep_fit(rows, mode, rt, label):
    ids = {}
    for r in rows:
        if r["mode"] == mode and r["tool"] == "cuvein":
            ids.setdefault(r["id"], r["pset"])
    pts_all, pts_suite = [], {}
    for idv, ps in ids.items():
        d = agg(rows, idv, mode)
        if d and d["events"] > 0:
            pts_all.append((d["events"], d["wall"]))
            pts_suite.setdefault(ps, []).append((d["events"], d["wall"]))
    out = [{"scope": "all complete (id,mode) rows", "column": label, "runtime": rt, **(ols(pts_all) or {})}]
    for ps, pts in sorted(pts_suite.items()):
        out.append({"scope": f"suite {ps}", "column": label, "runtime": rt, **(ols(pts) or {"n": len(pts)})})
    return out


fits += sweep_fit(x1b, "scalar-clock", "f551ca0 (X1b)", "scalar-clock sharded N=16")
fits += sweep_fit(x1b, "vector-clock", "f551ca0 (X1b)", "vector-clock")
fits += sweep_fit(x1, "scalar-clock", "d38d057 (X1)", "scalar-clock serial N=1")
fits += sweep_fit(x1, "vector-clock", "d38d057 (X1)", "vector-clock")

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "cost_rows.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, list(rows_out[0]))
    w.writeheader()
    w.writerows(rows_out)
keys = ["scope", "column", "runtime", "n", "intercept_s", "slope_us_per_record", "r2"]
with open(os.path.join(OUT, "cost_fit.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, keys)
    w.writeheader()
    for r in fits:
        w.writerow({k: (f"{r[k]:.6g}" if isinstance(r.get(k), float) else r.get(k, "")) for k in keys})

with open(os.path.join(OUT, "cost_table.md"), "w") as f:
    f.write("| program | column | runtime | records | native (s) | tool wall (s) | us / record | node(s) |\n|---|---|---|---|---|---|---|---|\n")
    for r in rows_out:
        f.write(f"| {r['program']} | {r['column']} | {r['runtime']} | {r['records']} | {r['native_s']} | {r['wall_s']} | {r['us_per_record']} | {r['node']} |\n")
    f.write("\n| scope | column | runtime | n | intercept (s) | slope (us/record) | R2 |\n|---|---|---|---|---|---|---|\n")
    for r in fits:
        def g(k):
            return f"{r[k]:.4g}" if isinstance(r.get(k), float) else r.get(k, "missing")
        f.write(f"| {r['scope']} | {r['column']} | {r['runtime']} | {r.get('n', '')} | {g('intercept_s')} | {g('slope_us_per_record')} | {g('r2')} |\n")
print(open(os.path.join(OUT, "cost_table.md")).read())
