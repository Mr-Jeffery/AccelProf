#!/usr/bin/env python3
"""C3 item 4: the recall table (T21b, 28 targets, buggy and fixed builds) and the candidate counts (T21c) with the collector-only
mode (C2) beside vector-clock and scalar-clock.  Sources (all read with `git show`, nothing merged):
  CO recall      origin/eval/collector-only-realworld : eval/results/realworld_co/recall.csv            (C2)
  CO candidates  origin/eval/collector-only-realworld : eval/results/realworld_co_t21c/recall.csv       (C2)
  VC, SC recall  origin/study/realworld-recall        : eval/results/realworld/recall.csv               (T21b, flavor main)
  SC candidates  origin/study/realworld-candidates    : eval/results/realworld_t21c/recall.csv          (T21c)
amrex-1 (buggy and fixed) in collector-only mode: analysis re-run still running at the time of writing -> 'pending', left out of the
collector-only counts (footnote)."""
import csv, io, subprocess, collections, os
def show(ref, path):
    return list(csv.DictReader(io.StringIO(subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True, check=True).stdout)))
C2 = "origin/eval/collector-only-realworld"
co = show(C2, "eval/results/realworld_co/recall.csv")
cot = show(C2, "eval/results/realworld_co_t21c/recall.csv")
t21b = [r for r in show("origin/study/realworld-recall", "eval/results/realworld/recall.csv") if r["flavor"] == "main"]
t21c = show("origin/study/realworld-candidates", "eval/results/realworld_t21c/recall.csv")
PENDING = {("amrex-1", "buggy"), ("amrex-1", "fixed")}
OUT = "eval/results/collector-only-tables"
def key(r): return (r["target"], r["variant"], r["component"])
_seen = collections.Counter()
def table(rows, mode):
    t = {}; seen = collections.Counter()
    for r in rows:
        if r["mode"] != mode: continue
        k = key(r); t[k + (seen[k],)] = r; seen[k] += 1   # duplicate (target, variant, component) rows = distinct kernels (llmc-new-3, k8)
    return t
tabs = {"vector-clock": table(t21b, "vector-clock"), "scalar-clock": table(t21b, "scalar-clock"), "collector-only": table(co, "collector-only")}
# T21b stores scalar-clock as the 'main' flavor too? report which modes exist
modes_b = collections.Counter((r["mode"], r["flavor"]) for r in show("origin/study/realworld-recall", "eval/results/realworld/recall.csv"))
md = []; P = md.append
P("## Item 4: recall table (T21b, 28 targets) and candidate counts (T21c), third mode added\n")
P("Sources: C2's `eval/results/realworld_co/recall.csv` and `realworld_co_t21c/recall.csv` at origin/eval/collector-only-realworld " + subprocess.run(["git", "rev-parse", "--short", C2], capture_output=True, text=True).stdout.strip() +
  "; T21b `eval/results/realworld/recall.csv` (study/realworld-recall) for vector-clock and scalar-clock; T21c `eval/results/realworld_t21c/recall.csv` for the candidates. "
  "(C2's aggregate `eval/COLLECTOR_ONLY_REALWORLD.md/.csv` still shows hecbench-hungarian-1, raft-1 and colmap-new-1 as NOT-SCORED/ERROR; the per-set recall.csv files hold their re-analysis rows, so the counts below use those files. Reported to C2 / the coordinator as a finding.)\n")
P(f"T21b recall.csv (mode, flavor) rows: {dict(modes_b)}\n")
def counts(tab, variant, comp=None, exclude_pending=False):
    c = collections.Counter()
    for (tg, v, cp, _n), r in tab.items():
        if v != variant: continue
        if comp is not None and cp != comp: continue
        if exclude_pending and (tg, v) in PENDING: c["PENDING (left out)"] += 1; continue
        c[r["outcome"]] += 1
    return c
rows = []
P("**Buggy builds, per component** (outcome counts; CO excludes the pending amrex-1 row):\n")
P("| components | outcome | vector-clock | scalar-clock | collector-only |"); P("|---|---|---|---|---|")
for comp, name in (("DR", "data-race components (oracle expects DR)"), ("SC", "strong-conflict components (oracle expects SC)")):
    cs = {m: counts(tabs[m], "buggy", comp, exclude_pending=(m == "collector-only")) for m in tabs}
    outs = sorted({o for c in cs.values() for o in c})
    for o in outs:
        P(f"| {name} | {o} | " + " | ".join(str(cs[m].get(o, 0)) for m in tabs) + " |")
        rows.append((f"buggy {comp}", o, *[cs[m].get(o, 0) for m in tabs]))
    P(f"| {name} | **total** | " + " | ".join(str(sum(cs[m].values())) for m in tabs) + " |")
P("\n**Fixed builds** (one per target):\n")
P("| outcome | vector-clock | scalar-clock | collector-only |"); P("|---|---|---|---|")
cf = {m: counts(tabs[m], "fixed", None, exclude_pending=(m == "collector-only")) for m in tabs}
for o in sorted({o for c in cf.values() for o in c}):
    P(f"| {o} | " + " | ".join(str(cf[m].get(o, 0)) for m in tabs) + " |"); rows.append(("fixed", o, *[cf[m].get(o, 0) for m in tabs]))
P("| **total** | " + " | ".join(str(sum(cf[m].values())) for m in tabs) + " |")
P("\nPaper (both modes): 25 of 26 data-race components, 5 of 5 strong-conflict components; fixed builds 21 clean for the pair, 6 residual, 1 still reported.")
# per target outcome table
P("\n**Per target and component** (outcome per mode; pending = analysis re-run running):\n")
P("| target | variant | comp | vector-clock | scalar-clock | collector-only |"); P("|---|---|---|---|---|---|")
allk = sorted(set().union(*[set(t) for t in tabs.values()]))
prow = []
for k in allk:
    cells = []
    for m in tabs:
        r = tabs[m].get(k)
        o = r["outcome"] if r else "—"
        if m == "collector-only" and (k[0], k[1]) in PENDING: o = "pending"
        cells.append(o)
    prow.append((*k[:3], *cells)); P(f"| {k[0]} | {k[1]} | {k[2] or '-'} | " + " | ".join(cells) + " |")
with open(f"{OUT}/item4_recall_per_target.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["target", "variant", "component", "vector_clock", "scalar_clock", "collector_only"]); w.writerows(prow)
with open(f"{OUT}/item4_recall_counts.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["scope", "outcome", "vector_clock", "scalar_clock", "collector_only"]); w.writerows(rows)
# candidates
P("\n## Candidate set (T21c): scored components\n")
ct = {"scalar-clock": table(t21c, "scalar-clock"), "collector-only": table(cot, "collector-only")}
P("| id | component | expected | scalar-clock | collector-only | CO n_race / n_sc |"); P("|---|---|---|---|---|---|")
crow = []
for k in sorted(set(ct["scalar-clock"]) | set(ct["collector-only"])):
    s, c = ct["scalar-clock"].get(k), ct["collector-only"].get(k)
    if (s and s["variant"] != "buggy") and not c: continue
    P(f"| {k[0]}-{k[1]} | {k[2] or '-'} | {(c or s)['expected_class']} | {s['outcome'] if s else '—'} | {c['outcome'] if c else 'not run'} | {(c or {}).get('n_race','')}/{(c or {}).get('n_sc','')} |")
    crow.append((k[0], k[1], k[2], (c or s)["expected_class"], s["outcome"] if s else "", c["outcome"] if c else "not run"))
with open(f"{OUT}/item4_candidates.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["target", "variant", "component", "expected", "scalar_clock", "collector_only"]); w.writerows(crow)
sc_out = collections.Counter(r[4] for r in crow if r[4] and r[5] != "not run" or (r[4] and r[1] == "buggy"))
co_out = collections.Counter(r[5] for r in crow if r[5] not in ("", "not run"))
P(f"\nCollector-only candidate outcomes (components run): {dict(co_out)}. Scalar-clock outcomes over the same components: " + str(dict(collections.Counter(r[4] for r in crow if r[5] != 'not run'))) + ".")
P("lightgbm-new-1/2 are unscored (Jeffery's decision); llamacpp-open-2 was not run in C2.")
open(f"{OUT}/item4.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))

