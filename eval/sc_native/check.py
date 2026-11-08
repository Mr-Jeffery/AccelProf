#!/usr/bin/env python3
"""X11: print the result table and the aggregate cells from eval/results/sc_native/summary.csv (no cluster access, <1 s).
  python eval/sc_native/check.py [path/to/summary.csv]"""
import csv, math, os, sys
P = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "sc_native", "summary.csv")
rows = list(csv.DictReader(open(P, newline="")))
TOOLS = [("racecheck", "racecheck"), ("iguard", "iGUARD"), ("vector-clock", "vector-clock"),
         ("scalar-clock", "scalar-clock"), ("collector-only", "collector-only mode"), ("supercollider", "SuperCollider")]
APPS = list(dict.fromkeys(r["program"] for r in rows))
by = {(r["program"], r["tool"]): r for r in rows}
need = {"suite", "program", "tool", "mode", "label", "same_program", "old_verdict", "new_verdict", "old_slowdown",
        "new_slowdown", "old_native_s", "new_native_s", "runs", "source_files"}
assert need <= set(rows[0]), f"missing columns: {need - set(rows[0])}"
assert len(rows) == len(APPS) * len(TOOLS) and all((a, t) in by for a in APPS for t, _ in TOOLS), "rows missing"

def s(x): return f"{float(x):.0f}x" if float(x) >= 100 else f"{float(x):.1f}x"
def cell(r, which):
    v, sl = r[f"{which}_verdict"], r[f"{which}_slowdown"]
    return v + (f" {s(sl)}" if sl else "")
def show(r):
    o, n = cell(r, "old"), cell(r, "new")
    c = n if o == n else f"{o} → {n}"
    if "new:" not in r["source_files"]: c += " †"
    if str(r["runs"]).startswith("1 run"): c += " *"
    return c

print("| program (label) | " + " | ".join(l for _, l in TOOLS) + " |")
print("|---|" + "---|" * len(TOOLS))
for a in APPS:
    r0 = by[(a, TOOLS[0][0])]
    print(f"| {a} ({r0['label']}) | " + " | ".join(show(by[(a, t)]) for t, _ in TOOLS) + " |")
print("\n† old row kept (not re-run: SAME program, or SuperCollider); * 1 run; cell = verdict slowdown, changed cell = old → new; TO = timeout, ERR = error.\n")

def geo(xs): return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None
def agg(which):
    out = {}
    for t, _ in TOOLS:
        c = dict(tp=0, fn=0, fp=0, tn=0, to=0, err=0); sl = []
        for a in APPS:
            r = by[(a, t)]; v, lab = r[f"{which}_verdict"], r["label"]
            if v == "TO": c["to"] += 1
            elif v == "ERR" or v == "missing": c["err"] += 1
            elif lab == "RACE": c["tp" if v == "RACE" else "fn"] += 1
            else: c["fp" if v == "RACE" else "tn"] += 1
            if r[f"{which}_slowdown"]: sl.append(float(r[f"{which}_slowdown"]))
        out[t] = (c, geo(sl), len(sl))
    return out
O, N = agg("old"), agg("new")
def two(o, n): return str(o) if o == n else f"{o} → {n}"
def frac(c, a, b): d = c[a] + c[b]; return f"{c[a]}/{d}"
print("HeCBench SuperCollider subset (10 programs), old → new:\n")
print("| tool | TP/(TP+FN) | FP/(FP+TN) | TO | ERR | geomean slowdown (n) |")
print("|---|---|---|---|---|---|")
for t, l in TOOLS:
    (co, go, no), (cn, gn, nn) = O[t], N[t]
    g = lambda x: "—" if x is None else f"{x:.1f}x"
    print(f"| {l} | {two(frac(co,'tp','fn'), frac(cn,'tp','fn'))} | {two(frac(co,'fp','tn'), frac(cn,'fp','tn'))} | {two(co['to'], cn['to'])} | {two(co['err'], cn['err'])} | {two(g(go)+f' ({no})', g(gn)+f' ({nn})')} |")
