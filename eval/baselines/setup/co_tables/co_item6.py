#!/usr/bin/env python3
"""C3 item 6: the cost table of FINAL_TABLES.md section (a) with the collector-only column taken from C1's rows (not X1-follow):
us per record, record count, native wall, and the fitted intercept and slope (OLS of tool wall on records, same method as
eval/results/final-tables/cost_table.py).  Records = the row's `events=` (C1: analyzer drained-record count, accelprof -v).
Rows that are TIMEOUT / ERROR / partial are not points of a fit.  Run from the worktree root."""
import csv, os, re, statistics as st, collections
R = "eval/results"; OUT = f"{R}/collector-only-tables"
X1B = f"{R}/final-b/merged/baselines-cuvein.csv"; C1 = f"{R}/collector-only/merged/baselines-cuvein.csv"
def load(p): return list(csv.DictReader(open(p, newline="")))
def note(r, k):
    m = re.search(r"(?:^|;)" + k + r"=([^;]*)", r.get("notes", "")); return m.group(1) if m else None
def agg(rows, i, mode):
    rs = [r for r in rows if r["id"] == i and r["mode"] == mode and r["verdict"] in ("RACE", "CLEAN") and "partial" not in r.get("notes", "") and note(r, "events")]
    if not rs: return None
    return dict(wall=st.median(float(r["wall_s"]) for r in rs), native=st.median(float(r["native_wall_s"]) for r in rs), events=int(note(rs[0], "events")),
                nreps=len(rs), node=",".join(sorted({note(r, "node") or "?" for r in rs})), peak=max(float(r["peak_mb"]) for r in rs))
def ols(pts):
    n = len(pts)
    if n < 2: return None
    mx = sum(x for x, _ in pts) / n; my = sum(y for _, y in pts) / n
    sxx = sum((x - mx) ** 2 for x, _ in pts)
    if sxx == 0: return None
    b = sum((x - mx) * (y - my) for x, y in pts) / sxx; a = my - b * mx
    sst = sum((y - my) ** 2 for _, y in pts); sse = sum((y - (a + b * x)) ** 2 for x, y in pts)
    return dict(n=n, intercept_s=a, slope_us=b * 1e6, r2=(1 - sse / sst) if sst else float("nan"))
x1b, co = load(X1B), load(C1)
PROGS = [("P7-heartwall-cuda", "P7-heartwall-cuda"), ("P9-knn-cuda", "P9-knn-cuda"), ("P7-nbody-cuda", "P7-nbody-cuda"), ("P7-bfs-cuda", "P7-bfs-cuda"),
         ("P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n", "P1-BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_NonPersist_Atomic_NoExcessThreadsBug_NoLivelockBug_NoFieldBug_NoOverflowBug-slower_atomic-100n"),
         ("P6-interkernel-global_readwrite_race-fixed", "P6-interkernel-global_readwrite_race-fixed")]
md = []; P = md.append
rows = []; cols = collections.defaultdict(list)
P("## Item 6: cost table (section (a) of FINAL_TABLES.md), collector-only from C1's rows\n")
P("Wall in seconds, µs per record in parentheses; native wall = median of the program's native runs in the same job. Records = `events=` (collector-only: records drained, `accelprof -v`; scalar/vector-clock: `hb_events_count`). Different hosts per column (node in `cost_co_rows.csv`).\n")
P("| program | records (C1) | native (s) C1 / X1b | **collector-only (C1)** | scalar-clock sharded N=16 (X1b) | vector-clock (X1b) | C1 node |"); P("|---|---|---|---|---|---|---|")
def cell(d): return f"{d['wall']:,.1f} ({d['wall']/d['events']*1e6:,.4g})" if d else "missing"
for label, i in PROGS:
    c, s, v = agg(co, i, "collector-only"), agg(x1b, i, "scalar-clock"), agg(x1b, i, "vector-clock")
    for col, d, rt in (("collector-only", c, "f551ca0 (C1)"), ("scalar-clock sharded N=16", s, "f551ca0 (X1b)"), ("vector-clock", v, "f551ca0 (X1b)")):
        rows.append(dict(program=label, column=col, runtime=rt, wall_s=f"{d['wall']:.3f}" if d else "missing", records=d["events"] if d else "",
                         native_s=f"{d['native']:.3f}" if d else "", us_per_record=f"{d['wall']/d['events']*1e6:.4g}" if d else "", node=d["node"] if d else ""))
        if d: cols[(col, rt)].append((d["events"], d["wall"]))
    P(f"| {label} | {c['events']:,} | {c['native']:.3f} / {s['native']:.3f} | **{cell(c)}** | {cell(s)} | {cell(v)} | {c['node']} |" if c and s and v else f"| {label} | missing |")
fits = []
for (col, rt), pts in sorted(cols.items()):
    f = ols(pts); fits.append(dict(scope="program set above", column=col, runtime=rt, **(f or {"n": len(pts)})))
def sweep(rowsx, mode, rt, label):
    ids = {}
    for r in rowsx:
        if r["mode"] == mode and r["tool"] == "cuvein": ids.setdefault(r["id"], r["pset"])
    allp, bys = [], collections.defaultdict(list)
    for i, ps in ids.items():
        d = agg(rowsx, i, mode)
        if d and d["events"] > 0: allp.append((d["events"], d["wall"])); bys[ps].append((d["events"], d["wall"]))
    out = [dict(scope="all complete (id,mode) rows", column=label, runtime=rt, **(ols(allp) or {}))]
    for ps, pts in sorted(bys.items()): out.append(dict(scope=f"suite {ps}", column=label, runtime=rt, **(ols(pts) or {"n": len(pts)})))
    return out
fits += sweep(co, "collector-only", "f551ca0 (C1)", "collector-only")
fits += sweep(x1b, "scalar-clock", "f551ca0 (X1b)", "scalar-clock sharded N=16")
fits += sweep(x1b, "vector-clock", "f551ca0 (X1b)", "vector-clock")
def ff(x, p=4): return "" if x is None or x == "" else (f"{x:,.{p}g}" if isinstance(x, float) else str(x))
P("\nFits (OLS of tool wall on records), wall = intercept + slope × records:\n")
P("| scope | column | runtime | n | intercept (s) | slope (µs/record) | R² |"); P("|---|---|---|---|---|---|---|")
for f in fits:
    if f["scope"].startswith("suite") and "collector" not in f["column"] and f["scope"] not in ("suite P7", "suite P9", "suite P6"): pass
    P(f"| {f['scope']} | {f['column']} | {f['runtime']} | {f.get('n','')} | {ff(f.get('intercept_s'))} | {ff(f.get('slope_us'))} | {ff(f.get('r2'), 3)} |")
P("\nX3's section (a) collector-only fit (X1-follow, d38d057, 4 points on one host type each): intercept −1.757 s (`-n 1`) / 4.128 s (default), slope 0.2946 / 0.07542 µs per record. C1's runs are `-n 1`; the six-program fit above uses the six programs of the section.")
with open(f"{OUT}/cost_co_rows.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
with open(f"{OUT}/cost_co_fit.csv", "w", newline="") as f:
    keys = ["scope", "column", "runtime", "n", "intercept_s", "slope_us", "r2"]
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows([{k: x.get(k, "") for k in keys} for x in fits])
open(f"{OUT}/cost_co.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))

