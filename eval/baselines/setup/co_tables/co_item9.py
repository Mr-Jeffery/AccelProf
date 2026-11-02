#!/usr/bin/env python3
"""C3 item 9 (pair level), from the per-pair verdict records of two separate recordings of every program (co_pairs_collect.py):
X1b's scalar-clock recording and C1's collector-only recording.

 reported(mode)   pairs with a RACE or SC verdict in some launch (the harness's report set, both classes)
 CO-only          reported by collector-only, not reported by scalar-clock
 "SC orders it"   scalar-clock's record of the pair is ORDERED; hb_class 'barrier-ordered' = the barrier-only clock ordered it and no
                  certificate (R1/R3) did; hb_class None = a certificate did
 S1 (this run)    CO-only pairs that scalar-clock orders by the barrier clock
 S2 (X5)          X5's derived 1,021 barrier-ordered pairs (X1 recordings, d38d057), eval/results/x5/barrier_ordered_pairs.csv
A pair is keyed (program, space, lowest pc, highest pc); race type ignored.  Reasons for a pair in one of S1, S2 and not the other are read
from the verdict records and, for the edge test, the PCDG edges of the kernel JSONs of the three recordings (X1, X1b, C1)."""
import csv, collections, json, glob, os, sys, statistics
R = "eval/results"; OUT = f"{R}/collector-only-tables"; B = "/mnt/beegfs/fzheng4/cuvein_traces"
rec = {}
for f in sorted(glob.glob(f"{OUT}/pairs/shard*.jsonl")):
    for ln in open(f):
        r = json.loads(ln); rec[(r["id"], r["mode"])] = r
man = {r["id"]: r for r in csv.DictReader(open("eval/baselines/manifest.csv"))}
suite = {i: r["pset"] for i, r in man.items()}
def reported(r): return {(p[0], p[1], p[2]) for p in r["pairs"] if any(c.startswith(("RACE:", "SC:")) for c in p[3])}
def clsmap(r): return {(p[0], p[1], p[2]): p for p in r["pairs"]}
X5 = {}
for r in csv.DictReader(open(f"{R}/x5/barrier_ordered_pairs.csv")):
    if r["mode"] != "scalar-clock": continue
    k = (r["id"], r["space"], *sorted((int(r["anc_pc"], 16), int(r["cur_pc"], 16))))
    X5.setdefault(k, {"bin": r["bin"], "store": r["store"], "kernel": r["kernel"]})
SUITENAME = {"P1": "Indigo3", "PI": "Indigo 1.3", "P3": "ECL graph codes", "P4": "ScoR applications", "P5": "ScoR litmus kernels",
             "P6": "cuHadron", "P7": "HeCBench, other applications", "P9": "HeCBench, SuperCollider's 10"}
BINS = ["loop-carried", "partial participation", "early exit", "branch arm", "other"]
BINCOL = ["Loop around the barrier", "Warp barrier between", "Exit before the barrier", "Barrier on one branch", "Other"]
fails = collections.Counter()
ok_ids = []
for i in sorted(man):
    a, b = rec.get((i, "scalar-clock")), rec.get((i, "collector-only"))
    if a is None or b is None: fails["no recording: " + ("SC" if a is None else "CO")] += 1; continue
    if a["reason"] or b["reason"]:
        fails[f"analysis {a['reason'] or ''}/{b['reason'] or ''}".strip()] += 1; continue
    ok_ids.append(i)
S1 = {}; both = 0; co_only_other = collections.Counter(); sc_only_n = collections.Counter()
for i in ok_ids:
    A, Bm = rec[(i, "scalar-clock")], rec[(i, "collector-only")]
    rs, rc_ = reported(A), reported(Bm); cm = clsmap(A)
    both += len(rs & rc_)
    sc_only_n[suite[i]] += len(rs - rc_)
    for p in rc_ - rs:
        e = cm.get(p)
        if e is None: co_only_other["SC has no record of the pair"] += 1; continue
        cl = e[3]
        if all(c == "ORDERED:barrier-ordered" for c in cl): S1[(i, *p)] = suite[i]
        elif all(c.startswith("ORDERED") for c in cl): co_only_other["SC orders it by a certificate (hb_class none)"] += 1
        else: co_only_other["SC: " + "/".join(sorted(cl))] += 1
inx5 = {k for k in S1 if k in X5}
shape = collections.defaultdict(collections.Counter); progs = collections.defaultdict(set)
for k, s in S1.items():
    shape[s][X5[k]["bin"] if k in X5 else "not in X5"] += 1; progs[s].add(k[0])
# ---- reasons -------------------------------------------------------------------------------------------------
edge_cache = {}
def edges(store, pid, mode):
    key = (store, pid, mode)
    if key not in edge_cache:
        d = f"{B}/{store}/{pid}/{mode}"
        if not os.path.isdir(d): edge_cache[key] = None
        else:
            s = set()
            for f in glob.glob(f"{d}/kernel_*.json"):
                try: j = json.load(open(f))
                except Exception: continue
                for e in j.get("edges", []):
                    if e.get("cold_miss") or e.get("ancient_pc") is None: continue
                    s.add((min(e["ancient_pc"], e["current_pc"]), max(e["ancient_pc"], e["current_pc"])))
            edge_cache[key] = s
    return edge_cache[key]
def has(store, pid, mode, p):
    s = edges(store, pid, mode); return None if s is None else ((p[2], p[3]) in s)
def dist_sig(store, pid, mode, p):
    """the non-zero `dist` buckets summed over the pair's edges in a recording, e.g. 'intra_block'"""
    d = f"{B}/{store}/{pid}/{mode}"; tot = collections.Counter()
    for f in glob.glob(f"{d}/kernel_*.json"):
        try: j = json.load(open(f))
        except Exception: continue
        for e in j.get("edges", []):
            if e.get("cold_miss") or e.get("ancient_pc") is None: continue
            if {e["ancient_pc"], e["current_pc"]} == {p[2], p[3]}:
                for kk, v in e["dist"].items(): tot[kk] += v
    return "+".join(sorted(kk for kk, v in tot.items() if v)) or "none"
# the CO-only pairs outside S1: what scalar-clock's record is, and whether the pair's edge is in X1b's recording
oth_rows = []
for i in ok_ids:
    A, Bm = rec[(i, "scalar-clock")], rec[(i, "collector-only")]
    rs, rc_ = reported(A), reported(Bm); cm = clsmap(A)
    for p in sorted(rc_ - rs):
        e = cm.get(p)
        if e is not None and all(c == "ORDERED:barrier-ordered" for c in e[3]): continue
        pp = (i, *p)
        oth_rows.append(dict(suite=suite[i], id=i, space=p[0], pc_lo=hex(p[1]), pc_hi=hex(p[2]), sc_record="/".join(sorted(e[3])) if e else "no record",
                             in_x5=pp in X5, edge_in_x1b_sc=has(A["store"], i, "scalar-clock", pp), edge_in_c1=has(Bm["store"], i, "collector-only", pp),
                             dist_x1b_sc=dist_sig(A["store"], i, "scalar-clock", pp) if e else "", dist_c1=dist_sig(Bm["store"], i, "collector-only", pp)))
with open(f"{OUT}/item9_CO_only_outside_S1.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(oth_rows[0]) if oth_rows else ["suite"]); w.writeheader(); w.writerows(oth_rows)
rows = []
def addrow(kind, k, reason, detail):
    rows.append(dict(kind=kind, suite=suite[k[0]], id=k[0], space=k[1], pc_lo=hex(k[2]), pc_hi=hex(k[3]), x5_bin=X5.get(k, {}).get("bin", ""), reason=reason, detail=detail))
def store_of(r): return r["store"] if r else None
for k in sorted(k for k in S1 if k not in X5):          # in this run's set, not in X5's
    pid = k[0]; p = k
    x1 = has("final-2026-10", pid, "scalar-clock", p)
    if x1 is False: addrow("in S1, not in X5", k, "schedule-dependent edge", "X1's (X5's) scalar-clock recording has no edge between the two pcs; X1b's and C1's recordings have it")
    elif x1 is None: addrow("in S1, not in X5", k, "other", "X1 store not readable")
    else: addrow("in S1, not in X5", k, "other", "X1's recording has the edge, X5 does not list the pair as barrier-ordered")
for k in sorted(X5):                                    # in X5's set, not in this run's
    if k in S1: continue
    pid = k[0]; p = k
    A, Bm = rec.get((pid, "scalar-clock")), rec.get((pid, "collector-only"))
    if A is None or Bm is None or A["reason"] or Bm["reason"]:
        addrow("in X5, not in S1", k, "other", f"a recording could not be analysed: SC {None if A is None else A['reason']}, CO {None if Bm is None else Bm['reason']}"); continue
    ca, cb = clsmap(A).get((k[1], k[2], k[3])), clsmap(Bm).get((k[1], k[2], k[3]))
    sc_cls = "/".join(sorted(ca[3])) if ca else "no record"
    co_cls = "/".join(sorted(cb[3])) if cb else "no record"
    e_co = has(Bm["store"], pid, "collector-only", p); e_x1b = has(A["store"], pid, "scalar-clock", p); e_x1 = has(X5[k]["store"], pid, "scalar-clock", p)
    det = f"X1b SC record: {sc_cls}; C1 CO record: {co_cls}; edge in X1/X1b/C1: {e_x1}/{e_x1b}/{e_co}"
    if cb is None and e_co is False and e_x1 is False: addrow("in X5, not in S1", k, "candidate mechanism off", det + " -- X1's recording has no edge either: the pair was judged from the event stream")
    elif cb is None and e_co is False: addrow("in X5, not in S1", k, "schedule-dependent edge", det)
    elif ca is None and e_x1b is False: addrow("in X5, not in S1", k, "schedule-dependent edge", det + " -- X1b's scalar-clock recording has no edge")
    elif ca and any(c.startswith(("RACE:", "SC:")) for c in ca[3]) and cb and any(c.startswith(("RACE:", "SC:")) for c in cb[3]):
        addrow("in X5, not in S1", k, "scalar-clock reports it too", det + " -- barrier-ordered in one launch, reported in another (same kernel recording)")
    else:
        sig = {t: dist_sig(st, pid, md, p) for t, st, md in (("X1", X5[k]["store"], "scalar-clock"), ("X1b-SC", A["store"], "scalar-clock"), ("C1-CO", Bm["store"], "collector-only"))}
        if len(set(sig.values())) > 1:
            addrow("in X5, not in S1", k, "schedule-dependent edge", det + f" -- the edge exists in all three recordings but its observed distance differs: {sig}")
        else: addrow("in X5, not in S1", k, "other", det + f" -- observed distance {sig}")
with open(f"{OUT}/item9_pair_differences.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["kind", "suite", "id", "space", "pc_lo", "pc_hi", "x5_bin", "reason", "detail"]); w.writeheader(); w.writerows(rows)
# shape tables
with open(f"{OUT}/item9_shapes_co.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["suite", "programs_with_a_pair", "pairs"] + BINCOL + ["not among X5's pairs"])
    for s in SUITENAME:
        t = shape.get(s, collections.Counter()); w.writerow([SUITENAME[s], len(progs.get(s, ())), sum(t.values())] + [t.get(b, 0) for b in BINS] + [t.get("not in X5", 0)])
x5t = collections.defaultdict(collections.Counter); x5p = collections.defaultdict(set)
for k, v in X5.items(): x5t[suite[k[0]]][v["bin"]] += 1; x5p[suite[k[0]]].add(k[0])
with open(f"{OUT}/item9_shapes_x5_1021.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["suite", "programs_with_a_pair", "pairs"] + BINCOL)
    for s in SUITENAME:
        t = x5t.get(s, collections.Counter()); w.writerow([SUITENAME[s], len(x5p.get(s, ())), sum(t.values())] + [t.get(b, 0) for b in BINS])
with open(f"{OUT}/item9_S1_pairs.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["suite", "id", "space", "pc_lo", "pc_hi", "x5_bin"])
    for k in sorted(S1): w.writerow([S1[k], k[0], k[1], hex(k[2]), hex(k[3]), X5.get(k, {}).get("bin", "")])
# ---- markdown ---------------------------------------------------------------------------------------------
md = []; P = md.append
P("## Item 9: pairs collector-only mode reports that scalar-clock mode orders, by control-flow shape, next to X5's derived 1,021\n")
P(f"Programs analysed in both recordings: {len(ok_ids)} of {len(man)}; not analysed: {dict(fails)}. Reported by both modes: {both} pairs. "
  f"Reported by scalar-clock only: {sum(sc_only_n.values())} pairs (by suite {dict(sc_only_n)}; not part of the comparison).\n")
P("Collector-only reports, scalar-clock does not, and scalar-clock's record of the pair is: ")
tot_co_only = sum(len(S1) for _ in [0]) + sum(co_only_other.values())
P(f"ORDERED by the barrier clock ({len(S1)} pairs, S1); " + "; ".join(f"{k}: {v}" for k, v in co_only_other.items()) + f". Total CO-only reports: {tot_co_only}.\n")
head = ["Suite", "Programs with a pair", "Pairs"] + BINCOL
P("**S1: collector-only reports that scalar-clock orders (barrier-only clock, no certificate)**; the last column = pairs in S1 that are not among X5's pairs (no shape recorded):\n")
P("| " + " | ".join(head + ["not among X5's"]) + " |"); P("|" + "---|" * (len(head) + 1))
tt = collections.Counter(); tp = 0; tn = 0
for s in SUITENAME:
    t = shape.get(s, collections.Counter()); n = sum(t.values())
    P(f"| {SUITENAME[s]} | {len(progs.get(s, ()))} | {n} | " + " | ".join(str(t.get(b, 0)) for b in BINS + ["not in X5"]) + " |"); tt.update(t); tp += len(progs.get(s, ())); tn += n
P(f"| **All** | {tp} | {tn} | " + " | ".join(str(tt.get(b, 0)) for b in BINS + ["not in X5"]) + " |")
P("\n**S2: X5's derived 1,021 pairs** (tab:eval-shapes; separate X1 recordings, same pairs in both modes):\n")
P("| " + " | ".join(head) + " |"); P("|" + "---|" * len(head))
tt2 = collections.Counter(); tp2 = 0; tn2 = 0
for s in SUITENAME:
    t = x5t.get(s, collections.Counter()); n = sum(t.values())
    P(f"| {SUITENAME[s]} | {len(x5p.get(s, ()))} | {n} | " + " | ".join(str(t.get(b, 0)) for b in BINS) + " |"); tt2.update(t); tp2 += len(x5p.get(s, ())); tn2 += n
P(f"| **All** | {tp2} | {tn2} | " + " | ".join(str(tt2.get(b, 0)) for b in BINS) + " |")
P(f"\nS1 and S2 share {len(inx5)} pairs; {len([k for k in S1 if k not in X5])} pairs are in S1 only and {len([k for k in X5 if k not in S1])} in S2 only.\n")
cnt = collections.Counter((r["kind"], r["reason"]) for r in rows)
P("**Pairs in one set and not the other**, by reason (every pair, with its evidence: `item9_pair_differences.csv`):\n")
P("| set | reason | pairs |"); P("|---|---|---|")
for (kd, rs_), n in sorted(cnt.items()): P(f"| {kd} | {rs_} | {n} |")
cnt2 = collections.Counter((r["suite"], r["kind"], r["reason"]) for r in rows)
P("\nBy suite:\n"); P("| suite | set | reason | pairs |"); P("|---|---|---|---|")
for (s, kd, rs_), n in sorted(cnt2.items()): P(f"| {s} | {kd} | {rs_} | {n} |")
oth = [r for r in rows if r["reason"] == "other"]
P(f"\nPairs that fit none of the three reasons (schedule-dependent edge, candidate mechanism off, scalar-clock reports it too): **{len(oth)}**" + (" (each is a finding):" if oth else "."))
for r in oth[:80]: P(f"  - {r['suite']} `{r['id']}` {r['space']} {r['pc_lo']}-{r['pc_hi']} [{r['kind']}, X5 bin {r['x5_bin'] or '-'}]: {r['detail']}")
P(f"\n**Collector-only reports outside S1** ({len(oth_rows)} pairs: scalar-clock does not report them, and does not order them by the barrier clock either; `item9_CO_only_outside_S1.csv`):\n")
P("| suite | scalar-clock's record of the pair | edge in X1b's scalar-clock recording | pairs |"); P("|---|---|---|---|")
for (s, rcd, ed), n in sorted(collections.Counter((r["suite"], r["sc_record"], r["edge_in_x1b_sc"]) for r in oth_rows).items()): P(f"| {s} | {rcd} | {ed} | {n} |")
open(f"{OUT}/item9.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))

