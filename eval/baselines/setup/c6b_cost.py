#!/usr/bin/env python3
"""C6b step 4, cost: the rule and script of eval/CAP_84600.md section 3 (cap_cells.py "cost columns") applied to vector-clock,
scalar-clock, C1's collector-only, C6's chain-closure run and the C6b settings S1 and S2 (same recordings and run walls as C1, verdict
step re-run; their run-only cost is C1's by construction).
  run only        = tool wall / native wall, geometric mean over the finished programs (RACE / CLEAN);
  verdict step    = analysis_s / native, end-to-end = (tool wall + analysis_s) / native, over the finished programs that carry analysis_s;
  restricted set  = P1 + PI + P3 + P4 + P5 + P6 programs (CAP's "All", 4,685 programs with analysis_s), unrestricted = also P7 + P9.
analysis_s of S1 / S2 is their own measurement on c14 (Xeon Silver 4110; anode= in the notes, one per program), not an estimate.
C6 is given as step 2 measured it (EPYC nodes) and as C6's A5-class estimate (C1 analysis_s x the closure factor C6 measured on c26).
Also: per-suite median / max of analysis_s, the closure share chain_s / analysis_s, and the analysis_s of each setting against C1's reference.
Run in the sandbox of c6b_stage.sh."""
import collections
import csv
import glob
import math
import os
import re
import statistics
import sys

sys.argv = [sys.argv[0], "--collector-only"]
SB = os.environ.get("COSB", "/home/fzheng4/c6b-step4/sand")
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt  # noqa: E402

W = "/home/fzheng4/wt-c6b"
OUT = os.environ.get("OUTD", f"{W}/eval/results/co-chain-b/step4") + "/cost"
os.makedirs(OUT, exist_ok=True)
VC, SC, CO = mt.VC, mt.SC, mt.CO
CC, S1, S2 = "collector-only-chain", "collector-only-s1", "collector-only-s2"
EXTRA = (CC, S1, S2)
runs, meta = mt.load_runs()
# native walls: as the paper's make_tables / cap_cells, from the vector-clock, scalar-clock and C1 rows only (the C6 / S1 / S2 rows are copies of C1's
# recording rows, left out so that they cannot move the denominators of the other modes)
rat = dict(mt._ratios({k: v for k, v in runs.items() if k[2] not in EXTRA}, meta))
md = []


def P(*a):
    md.append(" ".join(str(x) for x in a))


def tok(notes, name):
    m = re.search(r"(?:^|;)" + name + r"=([^;]*)", notes or "")
    return m.group(1) if m else None


def num(notes, name):
    t = tok(notes, name)
    try:
        return float(t) if t is not None else None
    except ValueError:
        return None


def gm(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None


def fin(r):
    return r is not None and r["verdict"] in ("RACE", "CLEAN")


def native(i, mode):
    k = (i, "cuvein", CO if mode in EXTRA else mode)
    r = runs.get(k)
    if r and r["wall"] and k in rat:
        return r["wall"] / rat[k]
    return None


SL = [("Indigo3", ("P1",)), ("Indigo 1.3", ("PI",)), ("ECL", ("P3",)), ("ScoR apps", ("P4",)), ("ScoR litmus", ("P5",)),
      ("cuHadron", ("P6",)), ("HeCBench other 14", ("P7",)), ("HeCBench SC 10", ("P9",)),
      ("HeCBench (P7+P9)", ("P7", "P9")),
      ("All (4,685-set: P1 PI P3 P4 P5 P6)", ("P1", "PI", "P3", "P4", "P5", "P6")),
      ("All incl. HeCBench (unrestricted)", ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"))]

# ---- C6's A5-class factor from its re-time (c26, pass 2)
RT = f"{W}/eval/results/co-chain/retime"


def retime(host, cfg, ps):
    f = f"{RT}/{host}/{cfg}-p{ps}/baselines-cuvein-shardrtall.csv"
    out = {}
    if not os.path.exists(f):
        return out
    for r in csv.DictReader(open(f, newline="")):
        if r["rep"] != "1":
            continue
        a = num(r["notes"], "analysis_s")
        if a is not None:
            out[(r["id"], r["mode"])] = (r["pset"], a)
    return out


def grp(ps):
    return "HeCBench" if ps in ("P7", "P9") else ps


factor = {}
off, on = retime("c26", "co-off", 2), retime("c26", "co-on", 2)
keys = [k for k in off if k in on and k[1] == "collector-only"]
for g in ("P1", "P3", "P4", "P5", "P6", "PI", "HeCBench", "all"):
    ks = [k for k in keys if g == "all" or grp(off[k][0]) == g]
    if ks:
        factor[g] = sum(on[k][1] for k in ks) / sum(off[k][1] for k in ks)
P("C6's closure factors on c26 (its re-time, pass 2, sum on / sum off): " + ", ".join(f"{g} {v:.4f}" for g, v in factor.items()) + f" (n programs {len(keys)})")

# ---- per-program analysis_s sources
an = {m: {} for m in (VC, SC, CO, CC, S1, S2)}
chs = {m: {} for m in (CC, S1, S2)}
node = {m: {} for m in (VC, SC, CO, CC, S1, S2)}
anode = {m: {} for m in (VC, SC, CO, CC, S1, S2)}
for (i, t, m), r in runs.items():
    if t != "cuvein" or m not in an:
        continue
    a = num(r["notes"], "analysis_s")
    if a is not None:
        an[m][i] = a
        node[m][i] = tok(r["notes"], "node")
        anode[m][i] = tok(r["notes"], "anode")
        if m in chs:
            chs[m][i] = num(r["notes"], "chain_s") or 0.0


def est_c6(i):
    a = an[CO].get(i)
    if a is None:
        return None
    return a * factor.get(grp(meta[i][0]), factor.get("all", 1.0))


# ---- S1 / S2 scaled to the re-time node (estimate): analysis_s of step 2 (c14) x (re-time node, pass 2) / (step 2 on c14) per group, same 47 programs
RT4 = f"{W}/eval/results/co-chain-b/step4/retime"
fac4 = {}
if os.path.isdir(RT4):
    for host in sorted(os.listdir(RT4)):
        for cfg, m in (("co-s1", S1), ("co-s2", S2)):
            fs = sorted(glob.glob(f"{RT4}/{host}/{cfg}-p2/baselines-cuvein-shard*.csv"))
            if not fs:
                continue
            d = {}
            for r in csv.DictReader(open(fs[0], newline="")):
                a = num(r["notes"], "analysis_s")
                if r["rep"] == "1" and a is not None:
                    d[r["id"]] = (r["pset"], a)
            for g in ("P1", "P3", "P4", "P5", "P6", "PI", "HeCBench", "all"):
                ks = [i for i in d if i in an[m] and (g == "all" or grp(d[i][0]) == g)]
                if ks:
                    fac4[(host, m, g)] = sum(d[i][1] for i in ks) / sum(an[m][i] for i in ks)
RTHOST = sorted({h for (h, _, _) in fac4})[0] if fac4 else None
if RTHOST:
    P(f"Re-time factors (host {RTHOST}, pass 2 of the re-time over step 2's analysis_s on c14, same 47 programs): "
      + "; ".join(f"{NAME_}: " + ", ".join(f"{g} {fac4[(RTHOST, m, g)]:.3f}" for g in ("P1", "P3", "P4", "P5", "P6", "PI", "HeCBench", "all") if (RTHOST, m, g) in fac4) for m, NAME_ in ((S1, "S1"), (S2, "S2"))))


def scaled(m):
    def f(i):
        a = an[m].get(i)
        if a is None or RTHOST is None:
            return None
        return a * fac4.get((RTHOST, m, grp(meta[i][0])), fac4.get((RTHOST, m, "all"), 1.0))
    return f


def cost(mode, psets, an_of):
    run, ver, e2e, onan = [], [], [], []
    for (i, t, m), r in runs.items():
        if t != "cuvein" or m != mode or meta[i][0] not in psets or not fin(r):
            continue
        nat = native(i, mode)
        if nat is None or not r["wall"]:
            continue
        run.append(r["wall"] / nat)
        a = an_of(i)
        if a is not None:
            ver.append(max(a, 1e-3) / nat)
            e2e.append((r["wall"] + a) / nat)
            onan.append(r["wall"] / nat)
    return dict(run=(len(run), gm(run)), ver=(len(ver), gm(ver)), e2e=(len(e2e), gm(e2e)), run_an=(len(onan), gm(onan)))


CAP = {VC: (7.320, 2.454, 9.966), SC: (7.015, 2.173, 9.339), CO: (5.564, 2.098, 7.773)}
variants = [("vector-clock", VC, an[VC].get), ("scalar-clock", SC, an[SC].get), ("C1", CO, an[CO].get),
            ("C6, step-2 analysis_s as measured (EPYC nodes)", CC, an[CC].get),
            ("C6, A5-class estimate (C1 analysis_s x c26 closure factor)", CC, est_c6),
            ("S1, analysis_s measured on c14", S1, an[S1].get),
            ("S2, analysis_s measured on c14", S2, an[S2].get)] + ([("S1, c14 analysis_s x factor of the re-time node (estimate)", S1, scaled(S1)), ("S2, c14 analysis_s x factor of the re-time node (estimate)", S2, scaled(S2))] if RTHOST else [])
P("\n## Cost by the rule of CAP_84600.md section 3: geometric means (n programs)\n")
P("| suite | mode | run only (n) | verdict step (n) | end-to-end (n) |")
P("|---|---|---|---|---|")
rows = []
res = {}
for sname, ps in SL:
    for vname, mode, f_an in variants:
        c = cost(mode, ps, f_an)
        res[(sname, vname)] = c
        f = lambda x: f"{x[1]:.3f} ({x[0]})" if x[1] else "—"
        P(f"| {sname} | {vname} | {f(c['run'])} | {f(c['ver'])} | {f(c['e2e'])} |")
        rows.append((sname, vname, *c["run"], *c["ver"], *c["e2e"]))
with open(f"{OUT}/cost_gm.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["suite", "mode", "run_n", "run_gm", "ver_n", "ver_gm", "e2e_n", "e2e_gm"])
    w.writerows(rows)
P("\nCheck against CAP_84600.md section 3 (All, 4,685-set; run only / verdict step / end-to-end):")
for mode, e in CAP.items():
    c = res[("All (4,685-set: P1 PI P3 P4 P5 P6)", {VC: "vector-clock", SC: "scalar-clock", CO: "C1"}[mode])]
    got = (round(c["run"][1], 3), round(c["ver"][1], 3), round(c["e2e"][1], 3))
    P(f"  - {mode}: CAP {e}, recomputed {got} (n {c['run'][0]}/{c['ver'][0]}/{c['e2e'][0]}) -> {'equal' if got == e else 'DIFFERENT'}")
c = res[("All incl. HeCBench (unrestricted)", "C1")]
P(f"  - collector alone over all finished programs (the paper's 5.7x): {c['run'][1]:.3f} (n {c['run'][0]})")
for m, nm in ((CC, "C6"), (S1, "S1"), (S2, "S2")):
    neq = tot = 0
    for (i, t, mm), r in runs.items():
        if t == "cuvein" and mm == m:
            o = runs.get((i, "cuvein", CO))
            tot += 1
            if o is None or o["wall"] != r["wall"]:
                neq += 1
    P(f"  - {nm} rows whose run wall differs from C1's row of the same program: {neq} of {tot}")

# ---- where the analysis ran
P("\n## Nodes of the analysis_s figures\n")
for m, nm in ((VC, "vector-clock"), (SC, "scalar-clock"), (CO, "C1"), (CC, "C6"), (S1, "S1"), (S2, "S2")):
    ans = collections.Counter(anode[m].values())
    nds = collections.Counter(node[m].values())
    P(f"- {nm}: programs with analysis_s {len(an[m])}; `anode=` in the notes: {dict(ans) if any(k for k in ans) else 'none recorded'}; `node=` (recording node): "
      + ", ".join(f"{k} {v}" for k, v in nds.most_common(12)) + (" ..." if len(nds) > 12 else ""))

# ---- per-suite analysis_s statistics
P("\n## analysis_s of the verdict step per suite: median, max, sum, and the closure's share\n")
P("share = sum(chain_s) / sum(analysis_s). C1 is the reference column (A5's node class as C6 recorded it; its analysis node is not recorded). "
  "S1 / S2 on c14.\n")
P("| suite | n | C1 median | C1 max | C6 median | C6 max | S1 median | S1 max | S2 median | S2 max | sum C1 | sum C6 | sum S1 | sum S2 | S1 chain_s sum | S1 share | S2 chain_s sum | S2 share |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
srows = []
for sname, ps in (("Indigo3 (P1)", ("P1",)), ("Indigo 1.3 (PI)", ("PI",)), ("ECL (P3)", ("P3",)), ("ScoR apps (P4)", ("P4",)), ("ScoR litmus (P5)", ("P5",)),
                  ("cuHadron (P6)", ("P6",)), ("HeCBench other 14 (P7)", ("P7",)), ("HeCBench SC 10 (P9)", ("P9",)), ("HeCBench (P7+P9)", ("P7", "P9")),
                  ("all but HeCBench", ("P1", "PI", "P3", "P4", "P5", "P6")), ("all", ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"))):
    ids = [i for i in an[S1] if meta[i][0] in ps and i in an[S2] and i in an[CC] and i in an[CO]]
    if not ids:
        continue
    d = {m: [an[m][i] for i in ids] for m in (CO, CC, S1, S2)}
    sh = {m: sum(chs[m][i] for i in ids) for m in (S1, S2)}
    row = (sname, len(ids), *[x for m in (CO, CC, S1, S2) for x in (statistics.median(d[m]), max(d[m]))], *[sum(d[m]) for m in (CO, CC, S1, S2)],
           sh[S1], sh[S1] / sum(d[S1]), sh[S2], sh[S2] / sum(d[S2]))
    srows.append(row)
    P(f"| {sname} | {len(ids)} | " + " | ".join(f"{x:.3f}" for x in row[2:10]) + " | " + " | ".join(f"{x:.1f}" for x in row[10:14]) + f" | {row[14]:.2f} | {row[15]:.4f} | {row[16]:.2f} | {row[17]:.4f} |")
with open(f"{OUT}/analysis_s_by_suite.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["suite", "n", "c1_median", "c1_max", "c6_median", "c6_max", "s1_median", "s1_max", "s2_median", "s2_max",
                "c1_sum", "c6_sum", "s1_sum", "s2_sum", "s1_chain_s", "s1_share", "s2_chain_s", "s2_share"])
    w.writerows(srows)
for m, nm in ((S1, "S1"), (S2, "S2")):
    mx = max(an[m], key=lambda i: an[m][i])
    P(f"\n{nm}: largest analysis_s {an[m][mx]:.3f} s (`{mx}`), its chain_s {chs[m][mx]:.3f} s. Largest chain_s: "
      + "; ".join(f"`{i}` {chs[m][i]:.3f} s of {an[m][i]:.3f} s" for i in sorted(chs[m], key=lambda i: -chs[m][i])[:5]))
    r1 = [(an[m][i] / an[CO][i]) for i in an[m] if i in an[CO] and an[CO][i] >= 0.2]
    P(f"{nm} analysis_s over C1's per program (programs with C1 analysis_s >= 0.2 s, n {len(r1)}): median {statistics.median(r1):.3f}, max {max(r1):.3f}; "
      f"sum over all programs {sum(an[m].values()):.1f} s against C1 {sum(an[CO][i] for i in an[m] if i in an[CO]):.1f} s and C6 {sum(an[CC][i] for i in an[m] if i in an[CC]):.1f} s.")
open(f"{OUT}/cost.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
