#!/usr/bin/env python3
"""C6b step 4 re-time summary (c6b_retime.sbatch): per host, configuration and pass, analysis_s (rep 1, one value per program) summed per group,
the ratios of S1, S2, scalar-clock and C1's rules (co-off) on the one node, and the same programs' analysis_s as step 2 measured them for S1 / S2
(c14) and as the C1 reference (A5) and C6 recorded them.  Writes $OUTD/retime_summary.md."""
import csv, glob, os, re, statistics, sys
W = "/home/fzheng4/wt-c6b"
R = f"{W}/eval/results/co-chain-b"
OUT = os.environ.get("OUTD", f"{R}/step4")
md = []


def P(*a):
    md.append(" ".join(str(x) for x in a))


def tok(n, name):
    m = re.search(r"(?:^|;)" + name + r"=([^;]*)", n or "")
    return m.group(1) if m else None


def grp(ps):
    return "HeCBench" if ps in ("P7", "P9") else ps


def load(f, mode=None):
    out = {}
    for r in csv.DictReader(open(f, newline="")):
        if r["rep"] != "1" or (mode and r["mode"] != mode):
            continue
        a = tok(r["notes"], "analysis_s")
        if a is not None:
            out[r["id"]] = (r["pset"], float(a), float(tok(r["notes"], "chain_s") or 0))
    return out


ref = {}
for tag, f, mode in (("c1", f"{W}/eval/results/verdict-timing/collector-only-merged/baselines-cuvein.csv", "collector-only"),
                     ("c6", f"{W}/eval/results/co-chain/merged/baselines-cuvein.csv", "collector-only"),
                     ("s1", f"{R}/merged-s1/baselines-cuvein.csv", "collector-only"),
                     ("s2", f"{R}/merged-s2/baselines-cuvein.csv", "collector-only"),
                     ("vc", f"{W}/eval/results/verdict-timing/final-b-merged/baselines-cuvein.csv", "vector-clock"),
                     ("sc", f"{W}/eval/results/verdict-timing/final-b-merged/baselines-cuvein.csv", "scalar-clock")):
    ref[tag] = load(f, mode) if os.path.exists(f) else {}
P("## Re-time: the 47-program sample on one Xeon Silver 4110 node\n")
GROUPS = ("P1", "P3", "P4", "P5", "P6", "PI", "HeCBench", "all")
for hostdir in sorted(glob.glob(f"{R}/step4/retime/*/")):
    host = os.path.basename(hostdir.rstrip("/"))
    data = {}
    for d in sorted(glob.glob(f"{hostdir}*-p[12]")):
        cfg, ps = os.path.basename(d).rsplit("-p", 1)
        fs = glob.glob(f"{d}/baselines-cuvein-shard*.csv")
        if fs:
            data[(cfg, int(ps))] = load(fs[0])
    if not data:
        continue
    ids = sorted(set.intersection(*[set(v) for v in data.values()]))
    P(f"\n### Host {host}: {len(ids)} programs in every configuration and pass (sum of analysis_s per group, seconds)\n")
    P("| group | n | " + " | ".join(f"{c} p{p}" for c, p in sorted(data)) + " | step 2 S1 (c14) | step 2 S2 (c14) | C1 ref (A5) | C6 step 2 (EPYC) | clock modes (A5) vc | sc |")
    P("|---|---|" + "---|" * (len(data) + 6))
    for g in GROUPS:
        sel = [i for i in ids if g == "all" or grp(data[sorted(data)[0]][i][0]) == g]
        if not sel:
            continue
        cells = [f"{sum(data[k][i][1] for i in sel):.2f}" for k in sorted(data)]
        extra = [f"{sum(ref[t][i][1] for i in sel if i in ref[t]):.2f}" for t in ("s1", "s2", "c1", "c6", "vc", "sc")]
        P(f"| {g} | {len(sel)} | " + " | ".join(cells) + " | " + " | ".join(extra) + " |")
    P(f"\n**Ratios on {host}, pass 2 (sum over the group of analysis_s of the numerator over the denominator)**\n")
    P("| group | S1 / co-off | S2 / co-off | co-off / C1 ref (A5) | S1 / step-2 S1 (c14) | S2 / step-2 S2 (c14) | sc / co-off | vc / co-off | sc / A5 sc | vc / A5 vc | C6 (EPYC, step 2) / C1 ref | max per-program S1 / co-off (co-off >= 0.2 s) | max S2 / co-off |")
    P("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for g in GROUPS:
        sel = [i for i in ids if g == "all" or grp(data[sorted(data)[0]][i][0]) == g]
        if not sel:
            continue
        s = lambda cfg: sum(data[(cfg, 2)][i][1] for i in sel) if (cfg, 2) in data else float("nan")
        sr = lambda t: sum(ref[t][i][1] for i in sel if i in ref[t])
        big = [i for i in sel if data[("co-off", 2)][i][1] >= 0.2]
        m1 = max((data[("co-s1", 2)][i][1] / data[("co-off", 2)][i][1] for i in big), default=float("nan"))
        m2 = max((data[("co-s2", 2)][i][1] / data[("co-off", 2)][i][1] for i in big), default=float("nan"))
        P(f"| {g} | {s('co-s1') / s('co-off'):.3f} | {s('co-s2') / s('co-off'):.3f} | {s('co-off') / sr('c1'):.3f} | {s('co-s1') / sr('s1'):.3f} | {s('co-s2') / sr('s2'):.3f} | "
          f"{s('sc') / s('co-off'):.3f} | {s('vc') / s('co-off'):.3f} | {s('sc') / sr('sc'):.3f} | {s('vc') / sr('vc'):.3f} | {sr('c6') / sr('c1'):.3f} | {m1:.3f} | {m2:.3f} |")
    P("\nchain_s sums, pass 2: " + ", ".join(f"{c} {sum(data[(c, 2)][i][2] for i in ids):.3f} s" for c in ("co-off", "co-s1", "co-s2") if (c, 2) in data))
open(f"{OUT}/retime_summary.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
