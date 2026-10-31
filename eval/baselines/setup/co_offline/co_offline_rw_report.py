#!/usr/bin/env python3
"""C4 item 2: the real-world recall table (T21b, per target and component, buggy and fixed) and the candidate counts (T21c) for CO-R.
CO-R = the scalar-clock recordings re-analysed with CUVEIN_BARRIER_ORDER=0, attributed by rw_attribute.py and scored by rw_score.py (the
branches' own scripts, run on copies; recall.csv in eval/results/co-offline/realworld{,_t21c}/).  Compared with scalar-clock and
vector-clock (T21b / T21c recall.csv, read from the worktrees) and with C2's collector-only run (here "edges only").
Reads only CSVs; every number is one of their cells."""
import collections
import csv
import os

W = "/home/fzheng4/wt-c4/eval/results/co-offline"
rd = lambda p: list(csv.DictReader(open(p, newline=""))) if os.path.exists(p) else []
cor_b, cor_c = rd(f"{W}/realworld/recall.csv"), rd(f"{W}/realworld_t21c/recall.csv")
t21b = [r for r in rd("/home/fzheng4/wt-t21b/eval/results/realworld/recall.csv") if r["flavor"] == "main"]
t21c = rd("/home/fzheng4/wt-t21c/eval/results/realworld_t21c/recall.csv")
c2b = rd("/home/fzheng4/wt-co-rw/eval/results/realworld_co/recall.csv")
c2c = rd("/home/fzheng4/wt-co-rw/eval/results/realworld_co_t21c/recall.csv")


def table(rows, mode):
    t = {}
    seen = collections.Counter()
    for r in rows:
        if r["mode"] != mode:
            continue
        k = (r["target"], r["variant"], r["component"])
        t[k + (seen[k],)] = r
        seen[k] += 1
    return t


def short(o):
    return (o.replace("DETECTED-AS-DR", "DET-as-DR").replace("RESIDUAL-AS-EXPECTED", "RESIDUAL").replace("CLEAN-FOR-PAIR", "CLEAN")
             .replace("STILL-REPORTED", "STILL"))


modes = {"vector-clock": table(t21b, "vector-clock"), "scalar-clock": table(t21b, "scalar-clock"),
         "edges only (C2)": table(c2b, "collector-only"), "CO-R": table(cor_b, "scalar-clock")}
md = []
P = md.append
P("## Recall set (T21b): per target and component, CO-R next to vector-clock, scalar-clock and the edges-only run (C2)\n")
P("CO-R rows come from `eval/results/co-offline/realworld/recall.csv` (rw_score.py of study/realworld-recall on the re-analysed, re-attributed scalar-clock recordings). "
  "`NOT-SCORED` = the id has no row: its scalar-clock analysis did not finish (amrex-1: ERROR analysis-timeout at 82,800 s in T21b, not re-run).\n")
allk = sorted({k for t in modes.values() for k in t})
P("| target | variant | comp | vector-clock | scalar-clock | edges only (C2) | CO-R | CO-R n_race / n_sc |")
P("|---|---|---|---|---|---|---|---|")
per = []
for k in allk:
    cells = []
    for m in modes:
        r = modes[m].get(k)
        if r is None and m == "CO-R":
            sr = modes["scalar-clock"].get(k)
            r_txt = f"stays {sr['run_verdict']} (not re-run)" if sr and sr.get("run_verdict") in ("ERROR", "TIMEOUT") else "NOT-SCORED"
            cells.append(r_txt)
            continue
        cells.append(short(r["outcome"]) if r else "—")
    cr = modes["CO-R"].get(k) or {}
    P(f"| {k[0]} | {k[1]} | {k[2] or '-'} | " + " | ".join(cells) + f" | {cr.get('n_race', '')}/{cr.get('n_sc', '')} |")
    per.append((k[0], k[1], k[2] or "-", *cells, cr.get("n_race", ""), cr.get("n_sc", "")))
with open(f"{W}/tables/recall_per_target.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["target", "variant", "component", "vector_clock", "scalar_clock", "edges_only_c2", "co_r", "co_r_n_race", "co_r_n_sc"])
    w.writerows(per)


def counts(tab, variant, comp=None):
    c = collections.Counter()
    for (tg, v, cp, _n), r in tab.items():
        if v != variant or (comp is not None and cp != comp):
            continue
        c[r["outcome"]] += 1
    return c


P("\n**Counts** (rows of each mode; CO-R: ids without a row are not in the count):\n")
P("| components | outcome | vector-clock | scalar-clock | edges only (C2) | CO-R |")
P("|---|---|---|---|---|---|")
rows = []
for comp, name, var in (("DR", "buggy, data-race components", "buggy"), ("SC", "buggy, strong-conflict components", "buggy"), (None, "fixed builds", "fixed")):
    cs = {m: counts(modes[m], var, comp) for m in modes}
    for o in sorted({o for c in cs.values() for o in c}):
        P(f"| {name} | {o} | " + " | ".join(str(cs[m].get(o, 0)) for m in modes) + " |")
        rows.append((name, o, *[cs[m].get(o, 0) for m in modes]))
    P(f"| {name} | **total** | " + " | ".join(str(sum(cs[m].values())) for m in modes) + " |")
with open(f"{W}/tables/recall_counts.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["scope", "outcome", "vector_clock", "scalar_clock", "edges_only_c2", "co_r"])
    w.writerows(rows)

# ---- the named targets
P("\n## The detections the edges-only run missed\n")
P("| target (component) | scalar-clock | edges only (C2) | CO-R | verdict |")
P("|---|---|---|---|---|")
names = [("cccl-3", "DR", "CCCL top-k"), ("ginkgo-5", "DR", "Ginkgo range-minimum"), ("kokkos-5", "DR", "Kokkos rw_sum")]
rp = [(k[0], k[2]) for k in allk if k[1] == "buggy" and modes["edges only (C2)"].get(k) and modes["edges only (C2)"][k]["outcome"] == "MISSED"
      and modes["scalar-clock"].get(k) and modes["scalar-clock"][k]["outcome"] == "DETECTED"]
P(f"\nBuggy data-race components DETECTED by scalar-clock and MISSED by the edges-only run (computed): {rp}\n")
named = []
for tg, comp, nm in names + [(t, c, t) for t, c in rp if t not in {x[0] for x in names}]:
    ks = [k for k in allk if k[0] == tg and k[1] == "buggy" and k[2] == comp]
    for k in ks:
        g = lambda m: (short(modes[m][k]["outcome"]) if modes[m].get(k) else "NOT-SCORED")
        v = g("CO-R")
        named.append((nm, tg, comp, g("scalar-clock"), g("edges only (C2)"), v))
        P(f"| {nm} ({tg}, {comp}) | {g('scalar-clock')} | {g('edges only (C2)')} | {v} | {'detected' if v == 'DETECTED' else v} |")
# ---- candidates
mc = {"scalar-clock": table(t21c, "scalar-clock"), "edges only (C2)": table(c2c, "collector-only"), "CO-R": table(cor_c, "scalar-clock")}
P("\n## Candidate set (T21c)\n")
P("| id | component | expected | scalar-clock | edges only (C2) | CO-R | CO-R n_race / n_sc |")
P("|---|---|---|---|---|---|---|")
crow = []
for k in sorted(set().union(*[set(t) for t in mc.values()])):
    cells = [short(mc[m][k]["outcome"]) if mc[m].get(k) else (("stays " + mc["scalar-clock"][k]["run_verdict"] + " (not re-run)" if mc["scalar-clock"].get(k, {}).get("run_verdict") in ("ERROR", "TIMEOUT") else "NOT-SCORED") if m == "CO-R" else "—") for m in mc]
    r = next((mc[m][k] for m in ("CO-R", "scalar-clock") if mc[m].get(k)), {})
    cr = mc["CO-R"].get(k) or {}
    P(f"| {k[0]}-{k[1]} | {k[2] or '-'} | {r.get('expected_class', '')} | " + " | ".join(cells) + f" | {cr.get('n_race', '')}/{cr.get('n_sc', '')} |")
    crow.append((k[0], k[1], k[2], r.get("expected_class", ""), *cells))
with open(f"{W}/tables/recall_candidates.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["target", "variant", "component", "expected", "scalar_clock", "edges_only_c2", "co_r"])
    w.writerows(crow)
for m in mc:
    P(f"\n{m}: " + str(dict(collections.Counter(r["outcome"] for r in mc[m].values() if r["variant"] == "buggy"))))
pcl = [k for k in mc["scalar-clock"] if k[0] == "pcl-new-1" and k[2] == "DR"]
P("\nPCL (pcl-new-1) data-race half: " + "; ".join(f"scalar-clock {mc['scalar-clock'][k]['outcome']}, edges only {mc['edges only (C2)'].get(k, {}).get('outcome', '—')}, CO-R "
                                                      f"{mc['CO-R'].get(k, {}).get('outcome', 'NOT-SCORED')}" for k in pcl))
open(f"{W}/tables/co_offline_recall.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
