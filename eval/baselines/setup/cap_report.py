#!/usr/bin/env python3
"""X7 Part B4: eval/CAP_84600.md body tables from cap-84600/tables/{old,new}. Run from the worktree root; prints markdown."""
import json, csv, math, statistics, re, collections, os, sys
N = "eval/results/cap-84600"
old = json.load(open(f"{N}/tables/old/cells.json")); new = json.load(open(f"{N}/tables/new/cells.json"))
def rdc(v, f): return list(csv.DictReader(open(f"{N}/tables/{v}/co/{f}")))
out = []
def P(*a): out.append(" ".join(str(x) for x in a))
def cs(c):
    a = f"{c['tp']:,}/{c['pos']:,}" if c["pos"] else "—"
    b = f"{c['fp']:,}/{c['neg']:,}" if c["neg"] else "—"
    return f"{a} · {b}" + (f"; {c['to']} TO" if c["to"] else "") + (f"; {c['err']} ERR" if c["err"] else "")
def f1(x): return "—" if x is None else (f"{x:,.1f}" if x < 100000 else f"{x:,.0f}")
SUITES = ["Indigo3", "Indigo 1.3", "Indigo 1.3, SC's 99", "ECL", "ScoR applications", "ScoR litmus + canary", "cuHadron (in scope)", "HeCBench, SC's 10", "All pre-registered"]
MODES = ["vector-clock", "scalar-clock", "collector-only"]
MS = {"vector-clock": "cuRace vector-clock", "scalar-clock": "cuRace scalar-clock", "collector-only": "cuRace collector-only"}
def cu(v, kind):
    d = {}
    f = "table61_accuracy.csv" if kind == "races" else "table_countings.csv"
    for r in rdc(v, f):
        if r["counting"] == kind:
            d[(r["suite"], r["mode"])] = dict(tp=int(r["tp"]), pos=int(r["positives"]), fp=int(r["fp"]), neg=int(r["negatives"]), to=int(r["timeout"]), err=int(r["error"]))
    return d
def diff_table(title, cols, getold, getnew, rows=SUITES):
    P(f"\n{title}\n"); P("| suite | column | old | new |"); P("|---|---|---|---|")
    n = 0
    for s in rows:
        for c in cols:
            o, w = getold(s, c), getnew(s, c)
            if o != w: P(f"| {s} | {c} | {o} | {w} |"); n += 1
    if not n: P("| (no cell changes) | | | |")
    return n
BASE = {"racecheck": "racecheck", "iguard": "iGUARD", "union": "racecheck ∪ iGUARD", "hirace": "HiRace", "supercollider": "SuperCollider"}
def t4(v, data):
    cuv = cu(v, "races")
    def g(s, c):
        if c in MODES: return cs(cuv[(s, c)])
        k = [k for k, n in BASE.items() if n == c][0]
        return cs(data["baseline_cells"][s][k])
    return g
cols4 = [MS[m] for m in MODES] + list(BASE.values())
def gm_(s, c, v, data):
    pass
P("## Table 4 (tab:eval-accuracy) cells that change\n\nRecall TP/(TP+FN) · FP/(FP+TN); TO = timed out, ERR = errored.")
g_o, g_n = t4("old", old), t4("new", new)
# cuRace columns carry their own names in the cu dict: map names
def wrap(g, data, v):
    cuv = cu(v, "races")
    def f(s, c):
        for m in MODES:
            if MS[m] == c: return cs(cuv[(s, m)])
        k = [k for k, n in BASE.items() if n == c][0]; return cs(data["baseline_cells"][s][k])
    return f
n4 = diff_table("", cols4, wrap(g_o, old, "old"), wrap(g_n, new, "new"))
# union table
P("\n## Union table (tab:eval-accuracy-union) cells that change\n\nUnion counting for cuRace; racecheck over shared memory, iGUARD over global memory (manifest `shared_mem`), and the two together (as in Table 4).")
colsU = [MS[m] + " (union)" for m in MODES] + ["racecheck (shared memory)", "iGUARD (global memory)", "racecheck ∪ iGUARD"]
def wrapU(data, v):
    cuv = cu(v, "union")
    def f(s, c):
        for m in MODES:
            if MS[m] + " (union)" == c: return cs(cuv[(s, m)])
        k = {"racecheck (shared memory)": "racecheck_shared", "iGUARD (global memory)": "iguard_global", "racecheck ∪ iGUARD": "union"}[c]
        return cs(data["baseline_cells"][s][k])
    return f
nU = diff_table("", colsU, wrapU(old, "old"), wrapU(new, "new"), [s for s in SUITES if s != "Indigo 1.3, SC's 99"])
# countings
P("\n## Countings table (tab:eval-countings) cells that change\n")
colsC = [f"{MS[m]}: {k}" for m in MODES for k in ("races", "strong", "union")]
def wrapC(v):
    d = {k: cu(v, k) for k in ("races", "strong", "union")}
    return lambda s, c: cs(d[c.split(": ")[1]][(s, [m for m in MODES if MS[m] == c.split(": ")[0]][0])])
nC = diff_table("", colsC, wrapC("old"), wrapC("new"), [s for s in SUITES if s != "Indigo 1.3, SC's 99"])
# memory
P("\n## Memory table (tab:eval-memory) cells that change\n\nGB; unfinished runs show the last peak seen.\n"); P("| row | mode | old | new |"); P("|---|---|---|---|")
mo = {(r["row"], r["mode"]): r["value"] for r in rdc("old", "table_memory.csv")}; mn = {(r["row"], r["mode"]): r["value"] for r in rdc("new", "table_memory.csv")}
nM = 0
for k in mn:
    if mo.get(k) != mn[k]: P(f"| {k[0]} | {k[1]} | {mo.get(k)} | {mn[k]} |"); nM += 1
if not nM: P("| (no cell changes) | | | |")
# fig 6
P("\n## Figure 6 (fig:eval-slowdown) cells that change\n\nGeometric-mean slowdown (n finished programs). Same-job native wall for the re-run rows.\n"); P("| suite | tool | old | new |"); P("|---|---|---|---|")
TN = {"cuvein/vector-clock": "cuRace vector-clock", "cuvein/scalar-clock": "cuRace scalar-clock", "cuvein/collector-only": "cuRace collector-only", "racecheck/": "racecheck", "iguard/": "iGUARD", "hirace/": "HiRace", "supercollider/": "SuperCollider"}
SL = ["Indigo3", "Indigo 1.3", "ECL", "ScoR apps", "ScoR litmus", "cuHadron", "HeCBench other 14", "HeCBench SC 10", "All"]
nF = 0
for s in SL:
    for t, tn in TN.items():
        a, b = old["fig"].get(f"{s}|{t}"), new["fig"].get(f"{s}|{t}")
        fa = f"{f1(a[1])} ({a[0]})" if a and a[0] else "—"; fb = f"{f1(b[1])} ({b[0]})" if b and b[0] else "—"
        if fa != fb: P(f"| {s} | {tn} | {fa} | {fb} |"); nF += 1
if not nF: P("| (no cell changes) | | | |")
print("\n".join(out)); sys.stderr.write(f"changed cells: table4 {n4}, union {nU}, countings {nC}, memory {nM}, fig6 {nF}\n")
json.dump(dict(t4=n4, union=nU, countings=nC, memory=nM, fig6=nF), open(f"{N}/tables/changed_counts.json", "w"))
