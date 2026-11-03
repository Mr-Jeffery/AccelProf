#!/usr/bin/env python3
"""C6 step 3, cost: the rule and script of eval/CAP_84600.md section 3 (cap_cells.py "cost columns") applied to vector-clock,
scalar-clock, C1's collector-only and the chain-closure mode (same recordings and run walls as C1, verdict step re-run with
--chain-closure, so its run-only cost is C1's by construction).
  run only        = tool wall / native wall, geometric mean over the finished programs (RACE / CLEAN);
  verdict step    = analysis_s / native, end-to-end = (tool wall + analysis_s) / native, over the finished programs that carry analysis_s;
  restricted set  = P1 + PI + P3 + P4 + P5 + P6 programs (CAP's "All", 4,685 programs with analysis_s), unrestricted = also P7 + P9.
analysis_s of the chain rows is the step-2 value (EPYC nodes, anode= in the notes); the chain mode is therefore given three ways:
  step-2 as measured (EPYC), A5-class estimate = the A5 reference analysis_s of C1's row x the closure factor measured on c26
  (A5's node class) by the re-time (c6_retime.sbatch, 47 programs, pass 2), and the lower bound = C1's own analysis_s.
Also: per-suite median / max of analysis_s and the closure share chain_s / analysis_s.   Run in the sandbox of c6_stage.sh."""
import collections
import csv
import glob
import math
import os
import re
import statistics
import sys

sys.argv = [sys.argv[0], "--collector-only", "--co-chain"]
SB = os.environ.get("COSB", "/home/fzheng4/c6-step3/sand-b")
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt  # noqa: E402

W = "/home/fzheng4/wt-c6"
OUT = os.environ.get("OUTD", f"{W}/eval/results/co-chain/step3") + "/cost"
os.makedirs(OUT, exist_ok=True)
VC, SC, CO, CC = mt.VC, mt.SC, mt.CO, mt.CCHN
runs, meta = mt.load_runs()
rat = dict(mt._ratios(runs, meta))
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


# native wall per program and mode, as cap_cells.py: nat = wall / ratio (C1's native for CO and CC rows)
def native(i, mode):
    k = (i, "cuvein", CO if mode == CC else mode)
    r = runs.get(k)
    if r and r["wall"] and k in rat:
        return r["wall"] / rat[k]
    return None


SL = [("Indigo3", ("P1",)), ("Indigo 1.3", ("PI",)), ("ECL", ("P3",)), ("ScoR apps", ("P4",)), ("ScoR litmus", ("P5",)),
      ("cuHadron", ("P6",)), ("HeCBench other 14", ("P7",)), ("HeCBench SC 10", ("P9",)),
      ("HeCBench (P7+P9)", ("P7", "P9")),
      ("All (4,685-set: P1 PI P3 P4 P5 P6)", ("P1", "PI", "P3", "P4", "P5", "P6")),
      ("All incl. HeCBench (unrestricted)", ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"))]

# ---- A5-class factor from the re-time
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
            out[(r["id"], r["mode"])] = (r["pset"], a, num(r["notes"], "chain_s") or 0.0, tok(r["notes"], "anode"))
    return out


def grp(ps):
    return "HeCBench" if ps in ("P7", "P9") else ps


factor, fmax, fn = {}, {}, {}
P("## Re-time on A5's node class (c26, Xeon Silver 4110) and on c25 (EPYC 7302P): closure off vs on, same 47 recordings\n")
P("analysis_s of rep 1, mode collector-only (one value per program), sum over the sample; factor = sum(on) / sum(off); per-program max = largest on/off over the programs of the group with off >= 0.2 s.\n")
P("| host | pass | group | n | sum off (s) | sum on (s) | factor | per-program max | sum chain_s (s) |")
P("|---|---|---|---|---|---|---|---|---|")
for host in ("c26", "c25"):
    for ps in (1, 2):
        off, on = retime(host, "co-off", ps), retime(host, "co-on", ps)
        keys = [k for k in off if k in on and k[1] == "collector-only"]
        for g in ("P1", "P3", "P4", "P5", "P6", "PI", "HeCBench", "all"):
            ks = [k for k in keys if g == "all" or grp(off[k][0]) == g]
            if not ks:
                continue
            so, sn = sum(off[k][1] for k in ks), sum(on[k][1] for k in ks)
            rr = [on[k][1] / off[k][1] for k in ks if off[k][1] >= 0.2]
            P(f"| {host} | {ps} | {g} | {len(ks)} | {so:.2f} | {sn:.2f} | {sn / so:.4f} | {max(rr):.3f} | {sum(on[k][2] for k in ks):.3f} |" if rr else
              f"| {host} | {ps} | {g} | {len(ks)} | {so:.2f} | {sn:.2f} | {sn / so:.4f} | — | {sum(on[k][2] for k in ks):.3f} |")
            if ps == 2:
                factor[(host, g)] = sn / so
                fmax[(host, g)] = max(rr) if rr else sn / so
                fn[(host, g)] = len(ks)
# the other modes of the re-time, for scale
for host in ("c26", "c25"):
    tot = {}
    for cfg in ("vc", "sc", "co-off", "co-on"):
        d = retime(host, cfg, 2)
        tot[cfg] = sum(v[1] for k, v in d.items() if k[1] in ("vector-clock", "scalar-clock", "collector-only") and
                       ((cfg == "vc" and k[1] == "vector-clock") or (cfg == "sc" and k[1] == "scalar-clock") or (cfg.startswith("co") and k[1] == "collector-only")))
    P(f"\n{host}, pass 2, sum of analysis_s over the 47 programs: " + ", ".join(f"{k} {v:.2f} s" for k, v in tot.items()))
P("\nHost effect (co-off, pass 2, all 47): c26 / c25 = "
  + (f"{sum(v[1] for v in retime('c26', 'co-off', 2).values()) / sum(v[1] for v in retime('c25', 'co-off', 2).values()):.3f}"
     if retime("c25", "co-off", 2) and retime("c26", "co-off", 2) else "missing"))

# ---- per-program analysis_s sources
ref_an, cc_an, cc_chain, cc_node = {}, {}, {}, {}
for (i, t, m), r in runs.items():
    if t != "cuvein":
        continue
    a = num(r["notes"], "analysis_s")
    if m == CO and a is not None:
        ref_an[i] = a
    if m == CC and a is not None:
        cc_an[i] = a
        cc_chain[i] = num(r["notes"], "chain_s") or 0.0
        cc_node[i] = tok(r["notes"], "anode")


def est_an(i, host="c26", mode="est"):
    a = ref_an.get(i)
    if a is None:
        return None
    g = grp(meta[i][0])
    f = factor.get((host, g), factor.get((host, "all"), 1.0))
    if mode == "upper":
        f = fmax.get((host, g), fmax.get((host, "all"), 1.0))
    if mode == "lower":
        f = 1.0
    return a * f


def cost(mode, psets, an_of, restrict_an=True):
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


def an_of_mode(mode):
    def f(i):
        r = runs.get((i, "cuvein", mode))
        return num(r["notes"], "analysis_s") if r else None
    return f


CAP = {VC: (7.320, 2.454, 9.966), SC: (7.015, 2.173, 9.339), CO: (5.564, 2.098, 7.773)}
variants = [("vector-clock", VC, an_of_mode(VC)), ("scalar-clock", SC, an_of_mode(SC)), ("CO (C1)", CO, an_of_mode(CO)),
            ("CO+chain, step-2 analysis_s as measured (EPYC)", CC, lambda i: cc_an.get(i)),
            ("CO+chain, A5-class estimate (C1 analysis_s x c26 factor)", CC, lambda i: est_an(i, "c26", "est")),
            ("CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group)", CC, lambda i: est_an(i, "c26", "upper")),
            ("CO+chain, lower bound (= C1 analysis_s)", CC, lambda i: est_an(i, "c26", "lower"))]
P("\n## Cost by the rule of CAP_84600.md section 3: geometric means (n programs)\n")
P("| suite | mode | run only (n) | verdict step (n) | end-to-end (n) | run only, same programs as end-to-end |")
P("|---|---|---|---|---|---|")
rows = []
res = {}
for sname, ps in SL:
    for vname, mode, an in variants:
        c = cost(mode, ps, an)
        res[(sname, vname)] = c
        f = lambda x: f"{x[1]:.3f} ({x[0]})" if x[1] else "—"
        P(f"| {sname} | {vname} | {f(c['run'])} | {f(c['ver'])} | {f(c['e2e'])} | {f(c['run_an'])} |")
        rows.append((sname, vname, *c["run"], *c["ver"], *c["e2e"], *c["run_an"]))
with open(f"{OUT}/cost_gm.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["suite", "mode", "run_n", "run_gm", "ver_n", "ver_gm", "e2e_n", "e2e_gm", "run_on_analysed_n", "run_on_analysed_gm"])
    w.writerows(rows)
P("\nCheck against CAP_84600.md section 3 (All, 4,685-set; run only / verdict step / end-to-end):")
for mode, e in CAP.items():
    c = res[("All (4,685-set: P1 PI P3 P4 P5 P6)", {VC: "vector-clock", SC: "scalar-clock", CO: "CO (C1)"}[mode])]
    got = (round(c["run"][1], 3), round(c["ver"][1], 3), round(c["e2e"][1], 3))
    P(f"  - {mode}: CAP {e}, recomputed {got} (n {c['run'][0]}/{c['ver'][0]}/{c['e2e'][0]}) -> {'equal' if got == e else 'DIFFERENT'}")
c = res[("All incl. HeCBench (unrestricted)", "CO (C1)")]
P(f"  - collector alone over all finished programs (the paper's 5.7x): {c['run'][1]:.3f} (n {c['run'][0]})")
# chain run wall == C1 run wall?
neq = 0
tot = 0
for (i, t, m), r in runs.items():
    if t == "cuvein" and m == CC:
        o = runs.get((i, "cuvein", CO))
        tot += 1
        if o is None or o["wall"] != r["wall"]:
            neq += 1
P(f"\nChain rows whose run wall differs from C1's row of the same program: {neq} of {tot} (run-only cost of the chain mode is C1's by construction when 0).")

# ---- per-suite analysis_s statistics of the chain mode (step 2, EPYC) and of C1's reference
P("\n## analysis_s of the verdict step per suite: median, max, and the closure's share\n")
P("Step 2 (chain, EPYC nodes) next to the A5 reference (C1, A5's node class). share = sum(chain_s) / sum(analysis_s) and the median of chain_s / analysis_s per program.\n")
P("| suite | n | chain median (s) | chain max (s) | C1 ref median (s) | C1 ref max (s) | sum chain (s) | sum C1 ref (s) | sum chain_s (s) | share (sums) | share (median) |")
P("|---|---|---|---|---|---|---|---|---|---|---|")
srows = []
for sname, ps in (("Indigo3 (P1)", ("P1",)), ("Indigo 1.3 (PI)", ("PI",)), ("ECL (P3)", ("P3",)), ("ScoR apps (P4)", ("P4",)), ("ScoR litmus (P5)", ("P5",)),
                  ("cuHadron (P6)", ("P6",)), ("HeCBench other 14 (P7)", ("P7",)), ("HeCBench SC 10 (P9)", ("P9",)), ("HeCBench (P7+P9)", ("P7", "P9")),
                  ("all but HeCBench", ("P1", "PI", "P3", "P4", "P5", "P6")), ("all", ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"))):
    ids = [i for i in cc_an if meta[i][0] in ps]
    if not ids:
        continue
    a = [cc_an[i] for i in ids]
    ra = [ref_an[i] for i in ids if i in ref_an]
    sh = [cc_chain[i] / cc_an[i] for i in ids if cc_an[i] > 0]
    P(f"| {sname} | {len(ids)} | {statistics.median(a):.3f} | {max(a):.3f} | {statistics.median(ra):.3f} | {max(ra):.3f} | {sum(a):.1f} | {sum(ra):.1f} | "
      f"{sum(cc_chain[i] for i in ids):.2f} | {sum(cc_chain[i] for i in ids) / sum(a):.4f} | {statistics.median(sh):.4f} |")
    srows.append((sname, len(ids), statistics.median(a), max(a), statistics.median(ra), max(ra), sum(a), sum(ra), sum(cc_chain[i] for i in ids)))
with open(f"{OUT}/analysis_s_by_suite.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["suite", "n", "chain_median", "chain_max", "c1ref_median", "c1ref_max", "chain_sum", "c1ref_sum", "chain_s_sum"])
    w.writerows(srows)
mx = max(cc_an, key=lambda i: cc_an[i])
P(f"\nLargest chain analysis_s: {cc_an[mx]:.3f} s ({mx}), its chain_s {cc_chain[mx]:.3f} s.")
bigc = sorted(cc_chain, key=lambda i: -cc_chain[i])[:5]
P("Largest chain_s: " + "; ".join(f"{i} {cc_chain[i]:.3f} s of {cc_an[i]:.3f} s" for i in bigc))
P("\nAnalysis nodes of step 2 (anode= in the notes, one per program): " + str(dict(collections.Counter(cc_node.values()))))
ratio_by = collections.defaultdict(lambda: [0.0, 0.0])
for i in cc_an:
    if i in ref_an and cc_node.get(i):
        ratio_by[cc_node[i]][0] += cc_an[i]
        ratio_by[cc_node[i]][1] += ref_an[i]
P("\nStep-2 chain analysis_s over the A5 reference analysis_s, by analysis node (sums over the programs of that node; node class from the README: c5 EPYC 9115, c45 EPYC 7302P, c4/c58/c2 EPYC 9115, c25/c39 EPYC 7302P, c62 EPYC 8124P, c14/c26 Xeon 4110): "
  + ", ".join(f"{k} {v[0] / v[1]:.3f} (ref sum {v[1]:.0f} s)" for k, v in sorted(ratio_by.items())))
open(f"{OUT}/cost.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
