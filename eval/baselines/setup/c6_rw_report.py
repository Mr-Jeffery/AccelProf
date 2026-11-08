#!/usr/bin/env python3
"""C6 step 3: the real-world recall table (T21b, 28 targets, buggy and fixed builds) and the candidate counts (T21c) with the chain-closure
mode next to vector-clock, scalar-clock and C2's collector-only run.  Based on C4's co_offline_rw_report.py.  Sources (read only):
  vector-clock, scalar-clock  origin/study/realworld-recall  eval/results/realworld/recall.csv (flavor main)
  scalar-clock candidates     origin/study/realworld-candidates eval/results/realworld_t21c/recall.csv
  C2 (CO)                     origin/eval/collector-only-realworld eval/results/realworld_co{,_t21c}/recall.csv
  CO+chain                    c6-step3/rw/realworld{,_t21c}/recall.csv (rw_score.py on the chain-closure attribution)"""
import collections
import csv
import io
import json
import os
import subprocess

W = "/home/fzheng4/wt-c6"
RW = os.environ.get("RWDIR", "/home/fzheng4/c6-step3/rw")
OUT = os.environ.get("OUTD", f"{W}/eval/results/co-chain/step3") + os.environ.get("RWOUT", "/rw")
os.makedirs(OUT, exist_ok=True)


def show(ref, path):
    t = subprocess.run(["git", "-C", W, "show", f"{ref}:{path}"], capture_output=True, text=True).stdout
    return list(csv.DictReader(io.StringIO(t)))


def rd(p):
    return list(csv.DictReader(open(p, newline=""))) if os.path.exists(p) else []


t21b = [r for r in show("origin/study/realworld-recall", "eval/results/realworld/recall.csv") if r["flavor"] == "main"]
t21c = show("origin/study/realworld-candidates", "eval/results/realworld_t21c/recall.csv")
c2b = show("origin/eval/collector-only-realworld", "eval/results/realworld_co/recall.csv")
c2c = show("origin/eval/collector-only-realworld", "eval/results/realworld_co_t21c/recall.csv")
ccb, ccc = rd(f"{RW}/realworld/recall.csv"), rd(f"{RW}/realworld_t21c/recall.csv")


def table(rows, mode):
    t, seen = {}, collections.Counter()
    for r in rows:
        if r["mode"] != mode:
            continue
        k = (r["target"], r["variant"], r["component"])
        t[k + (seen[k],)] = r
        seen[k] += 1
    return t


def short(o):
    return (o.replace("DETECTED-AS-DR", "DET-as-DR").replace("RESIDUAL-AS-EXPECTED", "RESIDUAL").replace("CLEAN-FOR-PAIR", "CLEAN").replace("STILL-REPORTED", "STILL"))


modes = {"vector-clock": table(t21b, "vector-clock"), "scalar-clock": table(t21b, "scalar-clock"),
         "CO (C2)": table(c2b, "collector-only"), "CO+chain": table(ccb, "collector-only")}
md = []
P = md.append
P("## Recall set (T21b): per target and component, CO+chain next to vector-clock, scalar-clock and C2's collector-only run\n")
P("CO+chain rows: `rw_score.py` of study/realworld-recall on the chain-closure attribution of the C2 recordings (`rw_attribute.py` with `chain_closure=True`). "
  "`NOT-SCORED` = no row: the id was not attributed (see the missing list in CO_CHAIN.md).\n")
allk = sorted({k for t in modes.values() for k in t})
P("| target | variant | comp | vector-clock | scalar-clock | CO (C2) | CO+chain | CO+chain n_race / n_sc |")
P("|---|---|---|---|---|---|---|---|")
per = []
for k in allk:
    cells = []
    for m in modes:
        r = modes[m].get(k)
        cells.append(short(r["outcome"]) if r else ("NOT-SCORED" if m == "CO+chain" else "—"))
    cr = modes["CO+chain"].get(k) or {}
    flag = " **changed**" if cells[2] != cells[3] else ""
    P(f"| {k[0]} | {k[1]} | {k[2] or '-'} | " + " | ".join(cells) + f" | {cr.get('n_race', '')}/{cr.get('n_sc', '')}{flag} |")
    per.append((k[0], k[1], k[2] or "-", *cells, cr.get("n_race", ""), cr.get("n_sc", "")))
with open(f"{OUT}/recall_per_target.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["target", "variant", "component", "vector_clock", "scalar_clock", "co_c2", "co_chain", "co_chain_n_race", "co_chain_n_sc"])
    w.writerows(per)


def counts(tab, variant, comp=None):
    c = collections.Counter()
    for (tg, v, cp, _n), r in tab.items():
        if v != variant or (comp is not None and cp != comp):
            continue
        c[r["outcome"]] += 1
    return c


P("\n**Counts** (rows of each mode):\n")
P("| components | outcome | vector-clock | scalar-clock | CO (C2) | CO+chain |")
P("|---|---|---|---|---|---|")
rows = []
for comp, name, var in (("DR", "buggy, data-race components", "buggy"), ("SC", "buggy, strong-conflict components", "buggy"), (None, "fixed builds", "fixed")):
    cs = {m: counts(modes[m], var, comp) for m in modes}
    for o in sorted({o for c in cs.values() for o in c}):
        P(f"| {name} | {o} | " + " | ".join(str(cs[m].get(o, 0)) for m in modes) + " |")
        rows.append((name, o, *[cs[m].get(o, 0) for m in modes]))
    P(f"| {name} | **total** | " + " | ".join(str(sum(cs[m].values())) for m in modes) + " |")
with open(f"{OUT}/recall_counts.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["scope", "outcome", "vector_clock", "scalar_clock", "co_c2", "co_chain"])
    w.writerows(rows)
P("\n## The data-race components C2's run missed and scalar-clock detected\n")
P("| target (component) | scalar-clock | CO (C2) | CO+chain |")
P("|---|---|---|---|")
for tg, comp, nm in (("cccl-3", "DR", "CCCL top-k"), ("ginkgo-5", "DR", "Ginkgo range-minimum"), ("kokkos-5", "DR", "Kokkos rw_sum"), ("raft-1", "DR", "RAFT select_k")):
    for k in [k for k in allk if k[0] == tg and k[1] == "buggy" and k[2] == comp]:
        g = lambda m: (short(modes[m][k]["outcome"]) if modes[m].get(k) else "NOT-SCORED")
        P(f"| {nm} ({tg}, {comp}) | {g('scalar-clock')} | {g('CO (C2)')} | {g('CO+chain')} |")
rp = [(k[0], k[2]) for k in allk if k[1] == "buggy" and modes["CO (C2)"].get(k) and modes["CO (C2)"][k]["outcome"] == "MISSED"
      and modes["scalar-clock"].get(k) and modes["scalar-clock"][k]["outcome"] == "DETECTED"]
P(f"\nBuggy data-race components scalar-clock DETECTED and C2 MISSED (computed): {rp}")
mc = {"scalar-clock": table(t21c, "scalar-clock"), "CO (C2)": table(c2c, "collector-only"), "CO+chain": table(ccc, "collector-only")}
P("\n## Candidate set (T21c)\n")
P("| id | component | expected | scalar-clock | CO (C2) | CO+chain | CO+chain n_race / n_sc |")
P("|---|---|---|---|---|---|---|")
crow = []
for k in sorted(set().union(*[set(t) for t in mc.values()])):
    cells = [short(mc[m][k]["outcome"]) if mc[m].get(k) else ("NOT-SCORED" if m == "CO+chain" else "—") for m in mc]
    r = next((mc[m][k] for m in ("CO+chain", "scalar-clock") if mc[m].get(k)), {})
    cr = mc["CO+chain"].get(k) or {}
    flag = " **changed**" if cells[1] != cells[2] else ""
    P(f"| {k[0]}-{k[1]} | {k[2] or '-'} | {r.get('expected_class', '')} | " + " | ".join(cells) + f" | {cr.get('n_race', '')}/{cr.get('n_sc', '')}{flag} |")
    crow.append((k[0], k[1], k[2], r.get("expected_class", ""), *cells))
with open(f"{OUT}/recall_candidates.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["target", "variant", "component", "expected", "scalar_clock", "co_c2", "co_chain"])
    w.writerows(crow)
for m in mc:
    P(f"\n{m}: " + str(dict(collections.Counter(r["outcome"] for r in mc[m].values() if r["variant"] == "buggy"))))
pcl = [k for k in mc["scalar-clock"] if k[0] == "pcl-new-1" and k[2] == "DR"]
P("\nPCL (pcl-new-1) data-race half: " + "; ".join(f"scalar-clock {mc['scalar-clock'][k]['outcome']}, C2 {mc['CO (C2)'].get(k, {}).get('outcome', '—')}, CO+chain "
                                                  f"{mc['CO+chain'].get(k, {}).get('outcome', 'NOT-SCORED')}" for k in pcl))
# where the chain mode detects through a derived or rescued report only
P("\n## CO+chain components detected through derived / rescued reports\n")
P("Per attributed id: how many of the id's reports in the attribution are edge / rescued / derived (chain_src); components where the matched reports are all non-edge are listed in the attribution JSON (`c6-step3/rw/*/attrib`).\n")
for st, d in (("t21b", f"{RW}/realworld/attrib"), ("t21c", f"{RW}/realworld_t21c/attrib")):
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        try:
            j = json.load(open(f"{d}/{f}"))
        except Exception:      # noqa: BLE001
            continue
        rs = j["modes"].get("collector-only", {}).get("reports", [])
        c = collections.Counter(r.get("chain_src", "edge") for r in rs)
        if c["chain"] or c["chain_rescue"]:
            P(f"- {j['id']}: {len(rs)} reports: edge {c['edge']}, rescued {c['chain_rescue']}, derived {c['chain']}")
open(f"{OUT}/c6_rw_report.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
