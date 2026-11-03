#!/usr/bin/env python3
"""C4 items 4 and 5 (pair level), from the per-pair verdict records of X1b's scalar-clock recordings analysed with the
barrier-ordered rule on and off (co_offline_pairs.py, eval/results/co-offline/pairs/) and C3's records of C1's collector-only
recordings (eval/results/collector-only-tables/pairs/, no flags).
 reported(h)  pairs with a RACE or SC verdict in some launch, half h in {on = scalar-clock, off = CO-R}
 T            reported(off) - reported(on): the pairs CO-R reports and scalar-clock orders (all of them by the barrier clock)
 (a)/(b)      a reporting verdict of the pair in the OFF half is a candidate with no edge (e) or a rescued edge (r) -> (b), else (a)
 S1 (C3)      C1's collector-only run reports it, scalar-clock (X1b) orders it by the barrier clock: eval/results/collector-only-tables/item9_S1_pairs.csv
 shapes       X5's classification (eval/results/x5/barrier_ordered_pairs.csv, tab:eval-shapes), same bins and order
A pair is keyed (program, space, lowest pc, highest pc); race type ignored."""
import collections
import csv
import glob
import json
import os
import sys

W = "/home/fzheng4/wt-c4"
R = f"{W}/eval/results"
OUT = f"{R}/co-offline/tables"
os.makedirs(OUT, exist_ok=True)
man = {r["id"]: r for r in csv.DictReader(open(f"{W}/eval/baselines/manifest.csv"))}
suite = {i: r["pset"] for i, r in man.items()}
SUITENAME = {"P1": "Indigo3", "PI": "Indigo 1.3", "P3": "ECL graph codes", "P4": "ScoR applications", "P5": "ScoR litmus kernels",
             "P6": "cuHadron", "P7": "HeCBench, other applications", "P9": "HeCBench, SuperCollider's 10"}
BINS = ["loop-carried", "partial participation", "early exit", "branch arm", "other"]
BINCOL = ["Loop around the barrier", "Warp barrier between", "Exit before the barrier", "Barrier on one branch", "Other"]

rec = {}
for f in sorted(glob.glob(f"{R}/co-offline/pairs/shard*.jsonl")):
    for ln in open(f):
        r = json.loads(ln)
        rec[r["id"]] = r
c1 = {}
for f in sorted(glob.glob(f"{R}/collector-only-tables/pairs/shard*.jsonl")):
    for ln in open(f):
        r = json.loads(ln)
        if r["mode"] == "collector-only":
            c1[r["id"]] = r
X5 = {}
for r in csv.DictReader(open(f"{R}/x5/barrier_ordered_pairs.csv")):
    if r["mode"] != "scalar-clock":
        continue
    k = (r["id"], r["space"], *sorted((int(r["anc_pc"], 16), int(r["cur_pc"], 16))))
    X5.setdefault(k, r["bin"])
S1 = set()
for r in csv.DictReader(open(f"{R}/collector-only-tables/item9_S1_pairs.csv")):
    S1.add((r["id"], r["space"], int(r["pc_lo"], 16), int(r["pc_hi"], 16)))


def is_rep(t):
    return t.startswith(("RACE:", "SC:"))


def rep_pairs(half):
    return {(p[0], p[1], p[2]): p for p in half["pairs"] if any(is_rep(t) for t in p[3])}


def cmap(half):
    return {(p[0], p[1], p[2]): p for p in half["pairs"]}


fails = collections.Counter()
ok = []
for i in sorted(man):
    r = rec.get(i)
    if r is None:
        fails["no scalar-clock recording"] += 1
        continue
    if r["on"]["reason"] or r["off"]["reason"]:
        fails(f"analysis {r['on']['reason'] or 'ok'}/{r['off']['reason'] or 'ok'}") if False else fails.update([f"analysis {r['on']['reason'] or 'ok'}/{r['off']['reason'] or 'ok'}"])
        continue
    ok.append(i)

md = []
P = md.append
P("## Pair level: pairs CO-R reports and scalar-clock orders\n")
P(f"Scalar-clock recordings analysed with the rule on and off: {len(ok)} of {len(man)} programs; not analysed: {dict(fails)}.\n")
T = {}                        # (id, sp, lo, hi) -> category 'a' | 'b'
detail = []
non_bo = collections.Counter()
for i in ok:
    on, off = cmap(rec[i]["on"]), rep_pairs(rec[i]["off"])
    rep_on = rep_pairs(rec[i]["on"])
    for key, p in off.items():
        if key in rep_on:
            continue
        o = on.get(key)
        tags_on = o[3] if o else []
        if not tags_on or not all(t.startswith("ORDERED:barrier-ordered") for t in tags_on):
            non_bo[tuple(tags_on) or ("no record",)] += 1
        rep_tags = [t for t in p[3] if is_rep(t)]
        flags = "".join(t.split(":")[2] for t in rep_tags)
        cat = "b" if ("e" in flags or "r" in flags) else "a"
        kind = ("ext" if "e" in flags else "") + ("resc" if "r" in flags and "e" not in flags else "")
        T[(i, *key)] = (cat, kind or "-", tuple(sorted(rep_tags)))
P(f"CO-R reports, scalar-clock does not: **{len(T)} pairs** in {len({k[0] for k in T})} programs. Their scalar-clock record is ORDERED by the barrier clock in every launch: "
  + ("yes, all of them" if not non_bo else f"NO: {dict(non_bo)}") + ".\n")
a_set = {k for k, v in T.items() if v[0] == "a"}
b_set = {k for k, v in T.items() if v[0] == "b"}
P(f"(a) pairs with a cuVein edge: **{len(a_set)}**; (b) extended edges and rescued edges: **{len(b_set)}** "
  f"(candidate with no edge: {sum(1 for k in b_set if T[k][1] == 'ext')}, rescued edge: {sum(1 for k in b_set if T[k][1] == 'resc')}).\n")


def shape_table(keys, title):
    P(title + "\n")
    head = ["Suite", "Programs with a pair", "Pairs"] + BINCOL + ["not among X5's"]
    P("| " + " | ".join(head) + " |")
    P("|" + "---|" * len(head))
    tt = collections.Counter()
    tp = tn = 0
    rows = []
    for s in SUITENAME:
        ks = [k for k in keys if suite[k[0]] == s]
        t = collections.Counter(X5.get(k, "not in X5") for k in ks)
        n = len(ks)
        pr = len({k[0] for k in ks})
        cells = [t.get(b, 0) for b in BINS + ["not in X5"]]
        P(f"| {SUITENAME[s]} | {pr} | {n} | " + " | ".join(str(c) for c in cells) + " |")
        rows.append((SUITENAME[s], pr, n, *cells))
        tt.update(t)
        tp += pr
        tn += n
    P(f"| **All** | {tp} | {tn} | " + " | ".join(str(tt.get(b, 0)) for b in BINS + ["not in X5"]) + " |\n")
    return rows


rows_all = shape_table(set(T), "**All pairs CO-R reports that scalar-clock orders, by control-flow shape (X5's bins, same order as tab:eval-shapes)**")
rows_a = shape_table(a_set, "**(a) pairs with a cuVein edge**")
rows_b = shape_table(b_set, "**(b) extended and rescued edges**")
hdr = ["suite", "programs", "pairs"] + BINCOL + ["not_among_x5"]
for nm, rws in (("pairs_all", rows_all), ("pairs_a_edge", rows_a), ("pairs_b_ext_resc", rows_b)):
    with open(f"{OUT}/shapes_{nm}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        w.writerows(rws)
with open(f"{OUT}/pairs_cor_reports_sc_orders.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["suite", "id", "space", "pc_lo", "pc_hi", "category", "kind", "x5_bin", "in_S1", "cor_reporting_tags"])
    for k in sorted(T):
        w.writerow([suite[k[0]], k[0], k[1], hex(k[2]), hex(k[3]), T[k][0], T[k][1], X5.get(k, ""), k in S1, "/".join(T[k][2])])

# ---- (a) against S1 ----
P(f"**(a) against C3's S1 ({len(S1)} pairs)**: (a) has {len(a_set)} pairs; common {len(a_set & S1)}; in (a) only {len(a_set - S1)}; in S1 only {len(S1 - a_set)}.\n")
rows = []
reasons = collections.Counter()
for k in sorted(S1 - a_set):
    i = k[0]
    key = (k[1], k[2], k[3])
    if i not in ok:
        why = "program not analysed in this run (" + (rec[i]["on"]["reason"] or rec[i]["off"]["reason"] if i in rec else "no scalar-clock recording") + ")"
        cat = "program not analysed"
    elif k in b_set:
        cat = "CO-R: the pair is an extended/rescued edge"
        why = f"{T[k][1]}: the pair has no edge or a smaller observed distance in X1b's recording; C1's recording has the edge"
    else:
        o = cmap(rec[i]["off"]).get(key)
        if o is None:
            cat, why = "CO-R has no record", "the pair is not judged in X1b's recording (schedule: no edge, no candidate)"
        else:
            rep_on = rep_pairs(rec[i]["on"])
            if key in rep_on:
                cat, why = "scalar-clock reports it", "some launch of X1b's scalar-clock recording reports the pair (SC does not order it in all launches)"
            else:
                cat, why = "CO-R orders it", "off-half tags: " + "/".join(o[3])
    reasons[("in S1, not in (a)", cat)] += 1
    rows.append(("in S1, not in (a)", suite[i], i, k[1], hex(k[2]), hex(k[3]), cat, why))
for k in sorted(a_set - S1):
    i = k[0]
    key = (k[1], k[2], k[3])
    c = c1.get(i)
    if c is None or c["reason"]:
        cat, why = "C1 not analysed", f"C1 record: {'none' if c is None else c['reason']}"
    else:
        cc = cmap(c).get(key)
        if cc is None:
            cat, why = "C1 has no record", "the pair is not judged in C1's recording (schedule: no edge there)"
        elif any(is_rep(t) for t in cc[3]):
            cat, why = "C1 reports it, scalar-clock records differ", "C1 reports the pair; S1 requires X1b's scalar-clock record ORDERED:barrier-ordered in every launch (C3's run of the same recording)"
        else:
            cat, why = "C1 orders it", "C1 tags: " + "/".join(cc[3])
    reasons[("in (a), not in S1", cat)] += 1
    rows.append(("in (a), not in S1", suite[i], i, k[1], hex(k[2]), hex(k[3]), cat, why))
P("| set | reason | pairs |")
P("|---|---|---|")
for (s, r), n in sorted(reasons.items()):
    P(f"| {s} | {r} | {n} |")
with open(f"{OUT}/pairs_a_vs_S1.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["set", "suite", "id", "space", "pc_lo", "pc_hi", "reason", "detail"])
    w.writerows(rows)
P("\nEvery pair of the two lists, with its reason: `pairs_a_vs_S1.csv`.\n")

# ---- item 5: CO-R against C1 (separate recordings) ----
P("## CO-R against the collector-only run of C1 (separate recordings)\n")
P("reported pairs of CO-R (scalar-clock recording, rule off) against reported pairs of C1 (collector-only recording). Programs analysed in both: ")
both_ok = [i for i in ok if i in c1 and not c1[i]["reason"]]
P(f"{len(both_ok)} of {len(man)}.\n")
cause = collections.Counter()
per_suite = collections.defaultdict(lambda: collections.Counter())
progs = collections.defaultdict(set)
drows = []
other_rows = []
for i in both_ok:
    off, cc = rep_pairs(rec[i]["off"]), rep_pairs(c1[i])
    offm, c1m = cmap(rec[i]["off"]), cmap(c1[i])
    s = suite[i]
    per_suite[s]["common"] += len(set(off) & set(cc))
    for key in sorted(set(off) - set(cc)):
        p = off[key]
        rt = [t for t in p[3] if is_rep(t)]
        fl = "".join(t.split(":")[2] for t in rt)
        if "e" in fl:
            c = "extended edge (event-stream candidate, no edge)"
        elif "r" in fl:
            c = "rescue (edge distance lifted by the sync pass)"
        else:
            c = "other"
        x = c1m.get(key)
        why = ("C1 has no record of the pair" if x is None else "C1 tags " + "/".join(x[3]))
        cause[("CO-R only", c)] += 1
        per_suite[s][("CO-R only", c)] += 1
        progs[(s, "CO-R only")].add(i)
        drows.append(("CO-R only", s, i, key[0], hex(key[1]), hex(key[2]), c, why))
        if c == "other":
            other_rows.append(drows[-1])
    for key in sorted(set(cc) - set(off)):
        o = offm.get(key)
        if o is None:
            c, why = "other", "CO-R has no record of the pair (no edge in X1b's recording)"
        elif any(t.startswith("ORDERED") and t.split(":")[2].startswith("c") for t in o[3]):
            c, why = "RMW points (R3 chain from the sync pass's release/acquire points)", "CO-R tags " + "/".join(o[3])
        else:
            c, why = "other", "CO-R tags " + "/".join(o[3])
        cause[("C1 only", c)] += 1
        per_suite[s][("C1 only", c)] += 1
        progs[(s, "C1 only")].add(i)
        drows.append(("C1 only", s, i, key[0], hex(key[1]), hex(key[2]), c, why))
        if c == "other":
            other_rows.append(drows[-1])
P("| suite | pairs in both | CO-R only: extended edge | CO-R only: rescue | CO-R only: other | C1 only: RMW points | C1 only: other | programs with a CO-R-only pair | programs with a C1-only pair |")
P("|---|---|---|---|---|---|---|---|---|")
tot = collections.Counter()
for s in SUITENAME:
    c = per_suite[s]
    row = [c["common"], c[("CO-R only", "extended edge (event-stream candidate, no edge)")], c[("CO-R only", "rescue (edge distance lifted by the sync pass)")],
           c[("CO-R only", "other")], c[("C1 only", "RMW points (R3 chain from the sync pass's release/acquire points)")], c[("C1 only", "other")],
           len(progs[(s, "CO-R only")]), len(progs[(s, "C1 only")])]
    for j, v in enumerate(row):
        tot[j] += v
    P(f"| {SUITENAME[s]} | " + " | ".join(str(v) for v in row) + " |")
P("| **All** | " + " | ".join(str(tot[j]) for j in range(8)) + " |")
P(f"\nPairs in \"other\": **{len(other_rows)}**" + (" (each is a finding; `pairs_cor_vs_c1.csv`, kind column)." if other_rows else "."))
with open(f"{OUT}/pairs_cor_vs_c1.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["direction", "suite", "id", "space", "pc_lo", "pc_hi", "cause", "detail"])
    w.writerows(drows)
# other: what kind (schedule: no edge in the other recording)
oc = collections.Counter((r[0], r[7].split(" tags")[0].split(" (")[0][:60]) for r in other_rows)
for (d, w_), n in sorted(oc.items()):
    P(f"  - {d}: {w_} — {n}")
open(f"{OUT}/co_offline_pairs.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
