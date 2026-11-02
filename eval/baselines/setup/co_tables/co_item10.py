#!/usr/bin/env python3
"""C3 item 10: repeatability of collector-only mode on the parity-set programs C1 kept per rep, recorded twice on
different nodes (final-2026-11-co-parity-a on c41-c43, -b on c40/c55/c62; 3 reps each).  A recording is one kept rep
directory <store>/<id>/collector-only-rep<k>.  For every pair of recordings of a program: same program verdict?
same set of reported instruction pairs?  Jaccard of the edge sets {(kernel, ancient pc, current pc)} over all kernel_N.json
(cold-miss edges excluded) -- the measures of X5 / the paper's "Is one run enough?" section."""
import os, sys, csv, json, glob, statistics, itertools, collections
B = "/mnt/beegfs/fzheng4/cuvein_traces"
R = "eval/results"
OUT = f"{R}/collector-only-tables"
STORES = {"A": ("final-2026-11-co-parity-a", f"{R}/collector-only-parity-a"),
          "B": ("final-2026-11-co-parity-b", f"{R}/collector-only-parity-b")}

def rows_of(d):
    out = {}
    for f in sorted(glob.glob(f"{d}/baselines-cuvein-shard*.csv")):
        for r in csv.DictReader(open(f)):
            if r["mode"] == "collector-only":
                out[(r["id"], int(r["rep"]))] = r
    return out

def edges_of(d):
    s = set()
    for f in glob.glob(f"{d}/kernel_*.json"):
        j = json.load(open(f))
        k = j["kernel"]["kernel_name"]
        for e in j.get("edges", []):
            if e.get("cold_miss") or e.get("ancient_pc") is None: continue
            s.add((k, e["ancient_pc"], e["current_pc"]))
    return s

recs = collections.defaultdict(list)       # id -> recordings
for tag, (store, rd) in STORES.items():
    rows = rows_of(rd)
    for pid in sorted(os.listdir(f"{B}/{store}")):
        for k in (1, 2, 3):
            d = f"{B}/{store}/{pid}/collector-only-rep{k}"
            if not os.path.isdir(d): continue
            r = rows.get((pid, k))
            if r is None: continue
            notes = dict(x.split("=", 1) for x in r["notes"].split(";") if "=" in x)
            recs[pid].append(dict(set=tag, rep=k, node=notes.get("node", ""), verdict=r["verdict"],
                                  ids=frozenset(r["report_ids"].split()), edges=edges_of(d), nk=notes.get("nkernels", "")))
def untyped(ids): return frozenset(i.rsplit(":", 1)[0] for i in ids)

pairs = []
for pid, rs in sorted(recs.items()):
    for a, b in itertools.combinations(rs, 2):
        u = a["edges"] | b["edges"]
        j = (len(a["edges"] & b["edges"]) / len(u)) if u else 1.0
        scope = "same set" if a["set"] == b["set"] else "cross set"
        pairs.append(dict(id=pid, a=f"{a['set']}{a['rep']}@{a['node']}", b=f"{b['set']}{b['rep']}@{b['node']}", scope=scope,
                          same_node=a["node"] == b["node"], verdict_same=a["verdict"] == b["verdict"],
                          verdicts=f"{a['verdict']}/{b['verdict']}", ids_same=a["ids"] == b["ids"],
                          ids_same_untyped=untyped(a["ids"]) == untyped(b["ids"]), nrep_a=len(a["ids"]), nrep_b=len(b["ids"]),
                          edges_same=a["edges"] == b["edges"], jaccard=j, ne_a=len(a["edges"]), ne_b=len(b["edges"])))
with open(f"{OUT}/item10_parity_pairs.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(pairs[0])); w.writeheader(); w.writerows(pairs)
md = []
def P(x=""): md.append(x)
P("## Item 10: repeatability of collector-only mode (the \"Is one run enough?\" measures)\n")
P(f"Programs with kept reps: {len(recs)} (recordings per program: " + str(dict(collections.Counter(len(v) for v in recs.values()))) +
  "); recordings = kept rep directories of the two parity recordings A (c41-c43) and B (c40, c55, c62). Pairs of recordings: " + f"{len(pairs)}.\n")
def summ(sel, label):
    n = len(sel)
    if not n: return f"| {label} | 0 | | | | | |"
    js = [p["jaccard"] for p in sel]
    ne = sum(p["edges_same"] for p in sel)
    return (f"| {label} | {len({p['id'] for p in sel})} | {n} | {sum(p['verdict_same'] for p in sel)} | {sum(p['ids_same'] for p in sel)} "
            f"({sum(p['ids_same_untyped'] for p in sel)}) | {ne} | {min(js):.4f} / {statistics.median(js):.4f} / {statistics.mean(js):.4f} |")
P("| scope | programs | pairs of recordings | same program verdict | same reported pair set (race type removed) | identical edge sets | edge Jaccard min / median / mean |")
P("|---|---|---|---|---|---|---|")
P(summ(pairs, "all pairs"))
P(summ([p for p in pairs if p["scope"] == "same set"], "same recording set (same 3 nodes, different reps)"))
P(summ([p for p in pairs if p["scope"] == "cross set"], "across the two sets (A against B)"))
P(summ([p for p in pairs if not p["same_node"]], "recordings on different nodes"))
P(summ([p for p in pairs if p["same_node"]], "recordings on the same node"))
by = collections.defaultdict(list)
for p in pairs: by[p["id"].split("-")[0]].append(p)
P("\nBy suite:\n"); P("| scope | programs | pairs | same verdict | same reported set (untyped) | identical edge sets | edge J min / median / mean |"); P("|---|---|---|---|---|---|---|")
for s in sorted(by): P(summ(by[s], s))
bad_v = [p for p in pairs if not p["verdict_same"]]
bad_i = [p for p in pairs if not p["ids_same"]]
P(f"\nPairs of recordings with a different program verdict: {len(bad_v)}")
for p in bad_v[:40]: P(f"  - `{p['id']}` {p['a']} vs {p['b']}: {p['verdicts']}")
P(f"\nPairs of recordings with a different reported pair set: {len(bad_i)}; programs: " + ", ".join(sorted({f"`{p['id']}`" for p in bad_i})))
for p in bad_i[:40]: P(f"  - `{p['id']}` {p['a']} vs {p['b']}: {p['nrep_a']} vs {p['nrep_b']} pairs; untyped sets equal: {p['ids_same_untyped']}")
low = sorted(pairs, key=lambda p: p["jaccard"])[:15]
P("\nLowest edge Jaccard:\n"); P("| program | recording a | recording b | edges a | edges b | Jaccard | verdicts |"); P("|---|---|---|---|---|---|---|")
for p in low: P(f"| `{p['id']}` | {p['a']} | {p['b']} | {p['ne_a']} | {p['ne_b']} | {p['jaccard']:.4f} | {p['verdicts']} |")
open(f"{OUT}/item10.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))

