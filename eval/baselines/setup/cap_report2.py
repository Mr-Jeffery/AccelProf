#!/usr/bin/env python3
"""X7 Part B4 part 2: per-row table, cost columns, breakdown, common sets, remaining TIMEOUT rows."""
import json, csv, math, re, collections, statistics, sys
N = "eval/results/cap-84600"
old = json.load(open(f"{N}/tables/old/cells.json")); new = json.load(open(f"{N}/tables/new/cells.json"))
newkeys = [tuple(k) for k in json.load(open(f"{N}/newkeys.json"))]
out = []
def P(*a): out.append(" ".join(str(x) for x in a))
def f1(x): return "missing" if x is None else (f"{x:,.1f}" if abs(x) < 100000 else f"{x:,.0f}")
def gb(mb): return "missing" if mb is None else f"{mb/1000:,.1f} GB"
def capn(c): return "missing" if not c else f"{int(c):,} s"
TN = {"iguard": "iGUARD", "racecheck": "racecheck", "cuvein": "cuRace"}
P("## 1. Per re-run row\n")
P("Old cap = the cap of the rows that stood before; slowdown = tool wall / native wall of the same job (the new run's own `native_wall_s`). Reports = deduped reports. Peak = peak resident set of the tool's process tree (racecheck: not recorded by the runner).\n")
P("| tool | mode | row | old cap, old verdict | new verdict | reports | tool wall (s) | native wall (s) | slowdown | peak memory | node |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
for k in newkeys:
    ks = "|".join(k); d = new["detail"].get(ks); o = old["detail"].get(ks)
    if not d: continue
    sl = d["wall"] / d["native"] if d["wall"] and d["native"] else None
    ov = f"{capn(o['cap'])}, {o['verdict']}" if o else "missing"
    P(f"| {TN[k[1]]} | {k[2] or '—'} | {k[0]} | {ov} | {d['verdict']} | {d['reports']} | {f1(d['wall']) if d['wall'] else 'not run'} | {f1(d['native'])} | {f1(sl) if sl else 'missing'} | {gb(d['peak'])} | {d['node'] or 'missing'} |")
P("\nA TIMEOUT row has no verdict; its slowdown column is the lower bound cap / native. The iGUARD P7 rows heartwall, mandelbrot, particlefilter and stencil1d come from the 5,400 s long pass (cap 5,400 s, 1 rep), not from a re-run at 84,600 s. The cuRace collector-only atomicCAS row is a re-analysis of the stored recording (tool wall = the recording's, cap 1,200 s), not a new recording.")
SL = ["Indigo3", "Indigo 1.3", "ECL", "ScoR apps", "ScoR litmus", "cuHadron", "HeCBench other 14", "HeCBench SC 10", "All"]
MODES = ["vector-clock", "scalar-clock", "collector-only"]
P("\n## 2. cuRace cost per suite and mode (geometric means over the programs that finished)\n")
P("Run only = tool wall / native (today's slowdown, all finished programs). Verdict step = analysis_s / native, end-to-end = (tool wall + analysis_s) / native; both over the finished programs that carry analysis_s (n in brackets; programs without it are TIMEOUT/ERROR rows). analysis_s: Part A ea98fef, N = 16, from the A5 re-analysis (P7-haversine vector-clock: 1.530 s from its own re-analysis; P9-atomicCAS collector-only: 6.147 s).\n")
P("| suite | mode | run only (n) | verdict step (n) | end-to-end (n) | run only, same programs as end-to-end |"); P("|---|---|---|---|---|---|")
for s in SL:
    for m in MODES:
        c = new["cost"].get(f"{s}|{m}")
        if not c: continue
        def g(k): return f"{c[k][1]:,.3f} ({c[k][0]})" if k in c and c[k][0] else "missing"
        P(f"| {s} | {m} | {g('run')} | {g('verdict')} | {g('e2e')} | {g('run_on_analysed')} |")
R = N
def rd(p): return list(csv.DictReader(open(p, newline="")))
vcsc = rd(f"{R}/baselines-cuvein.csv"); co = rd(f"{R}/baselines-cuvein-co.csv")
def pick(rows, i, mode):
    rs = [r for r in rows if r["id"] == i and r["mode"] == mode]
    if not rs: return None
    w = sorted(float(r["wall_s"]) for r in rs if r["wall_s"])
    a = [float(m.group(1)) for r in rs for m in [re.search(r"analysis_s=([0-9.]+)", r["notes"])] if m]
    nat = [float(r["native_wall_s"]) for r in rs if r["native_wall_s"]]
    nd = re.search(r"node=([a-z0-9]+)", rs[0]["notes"])
    return dict(verdict=rs[0]["verdict"], wall=statistics.median(w) if w else None, an=a[0] if a else None, native=min(nat) if nat else None, node=nd.group(1) if nd else None)
ids = ["P7-heartwall-cuda", "P9-knn-cuda", "P7-nbody-cuda", "P7-bfs-cuda"]
ind = sorted(r["id"] for r in vcsc if r["id"].startswith("P1-BFS_CUDA_E_Topo_Determ") and "slower_atomic-100n" in r["id"])
ids.append(ind[0] if ind else "P1-missing")
P("\n## 3. Where the time goes: five programs\n")
P("Seconds, median of the rep walls. Collector = the collector-only recording (collector and static certificates, no HbClock); clock = the mode's recording wall minus the collector-only recording wall (two separate recordings, on the nodes in the last column, so the subtraction mixes hosts); verdict step = `analysis_s` (Part A ea98fef, N = 16); CFG extraction = `cfg_s` of meta.json (A1), which exists only in recordings made with Part A's harness: missing for every row below (no stored meta.json of final-2026-11, -co or -24h-vc has it).\n")
P("| program | native | collector (co wall) | co verdict step | mode | mode wall | clock (mode wall - co wall) | verdict step | CFG extraction (cfg_s) | verdict | nodes (co / mode) |"); P("|---|---|---|---|---|---|---|---|---|---|---|")
for i in ids:
    c = pick(co, i, "collector-only")
    for m in ("scalar-clock", "vector-clock"):
        r = pick(vcsc, i, m)
        if not r or not c:
            P(f"| {i} | missing | | | {m} | | | | missing | | |"); continue
        clk = r["wall"] - c["wall"] if r["wall"] and c["wall"] else None
        nat = r["native"] or c["native"]
        P(f"| {i} | {f1(nat)} | {f1(c['wall'])} | {f1(c['an'])} | {m} | {f1(r['wall'])} | {f1(clk)} | {f1(r['an'])} | missing | {r['verdict']} | {c['node']} / {r['node']} |")
P("\n## 4. Geometric-mean slowdown over the common set\n")
P("Common set = the programs on which every tool that runs on the suite finished (RACE or CLEAN) in this merge; the tools defining it are listed per suite. Collector-only is shown on the same programs but does not define the set. Each cell: common-set geometric mean (n) / today's set (Figure 6: the tool's own finished programs) (n).\n")
TK = ["cuvein/vector-clock", "cuvein/scalar-clock", "cuvein/collector-only", "racecheck/", "iguard/", "hirace/", "supercollider/"]
TN2 = {"cuvein/vector-clock": "cuRace vector", "cuvein/scalar-clock": "cuRace scalar", "cuvein/collector-only": "cuRace co", "racecheck/": "racecheck", "iguard/": "iGUARD", "hirace/": "HiRace", "supercollider/": "SuperCollider"}
P("The All row's common set is Indigo 1.3 alone: HiRace runs only there, so it also defines that row's set.\n")
P("| suite | common n | tools defining the set | " + " | ".join(TN2[t] for t in TK) + " |"); P("|---|---|---|" + "---|" * len(TK))
for s in SL:
    cm = new["common"][s]; cells = []
    for t in TK:
        a = cm.get(t); b = new["fig"].get(f"{s}|{t}")
        ca = f"{a[1]:,.1f} ({a[0]})" if a and a[0] else "—"; cb = f"{b[1]:,.1f} ({b[0]})" if b and b[0] else "—"
        cells.append(f"{ca} / {cb}")
    P(f"| {s} | {cm['n_common']} | {', '.join(x.replace('cuvein/', 'cuRace ').rstrip('/') for x in cm['tools'])} | " + " | ".join(cells) + " |")
P("\n## 5. Rows still TIMEOUT at 84,600 s\n")
P("Kernels completed = `nkernels` of the row (kernel JSONs written before the kill; for scalar-clock stencil1d the last of the 435 is cut mid-write). racecheck reports its hazards only when the run ends, so how far a killed racecheck run got is not recorded (missing); likewise the kernel count of the not-run particlefilter row.\n")
P("| tool | mode | row | cap | kernels completed (nkernels in the row) | peak memory | wall (s) | node | note |"); P("|---|---|---|---|---|---|---|---|---|")
n = 0
for ks, d in new["timeouts"]:
    k = ks.split("|")
    if d["cap"] != "84600" and "not run at cap=84600" not in d["notes"]: continue
    n += 1
    P(f"| {k[1]} | {k[2] or '—'} | {k[0]} | {capn(d['cap'])} | {d['nkernels'] if d['nkernels'] is not None else 'missing'} | {gb(d['peak'])} | {f1(d['wall']) if d['wall'] else 'not run'} | {d['node'] or 'missing'} | {d['notes'][:110].replace('|', '/')} |")
if not n: P("| none | | | | | | | | |")
print("\n".join(out))
