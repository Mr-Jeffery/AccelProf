"""T21c step 3: merge the per-target triage CSVs of T21b's other reports into one CSV, normalised.
Normalisation (the triagers' own labels kept in orig_class / orig_race_class):
- volatile shared accesses: race_class SC (the oracles' convention, D20 option (i); cuVein reports DR): lit-shoc-1.
- llamacpp-5#01: the oracle's own hazard (1), unregistered pair: class a, DR (was c, "harness scoring data").
relation = oracle: the pair belongs to its target's oracle race or registered residual but recall_pairs.json does not register it."""
import csv, glob, os, re
O = os.path.expanduser("~/t21c_triage/out")
lines = []
for f in sorted(glob.glob(f"{O}/*.csv")):
    for r in csv.DictReader(open(f)):
        lines.append({k: (v or "").strip() for k, v in r.items()})
def n(g): return int(g.split("#")[1])
def tgt(g): return g.split("#")[0]
def mech(g, sub):
    t, k = tgt(g), n(g)
    if t == "hecbench-dxtc2-1": return "oracle", "warp-synchronous loadColorBlock chains named by the oracle"
    if t == "hecbench-morphology-1": return "oracle", "reverse-scan pair L98 named by the oracle"
    if t == "llamacpp-5": return "oracle", "the oracle's hazard (1): CUB BlockLoad TempStorage reuse, ssm-scan.cu L69-70"
    if t == "ginkgo-5": return "oracle", "write-write half of the oracle's lost update (L154)"
    if t == "cmssw-1": return "oracle", "oracle bug / registered residual on pairs recall_pairs.json does not list"
    if t == "raft-1" and k == 10: return "oracle", "registered residual L322 vs fixed L786 (registered under buggy numbering)"
    if t == "hecbench-hungarian-1":
        if k <= 37: return "oracle", "warp-synchronous volatile min reductions without __syncwarp (oracle race family)"
        if 53 <= k <= 65: return "oracle", "intra-step warp-reduce pairs of the fixed build (the oracle's residual family)"
        if k in (38, 39, 40, 66, 67): return "other", "step_2 cover_row/cover_column claim: plain pre-check / reset vs atomicExch"
        if k in (41, 42, 43, 47, 48, 49, 50, 68, 69, 70, 74, 75, 76, 77): return "other", "same-value flag / cover writes by many threads (step_2, step_4)"
        if k in (44, 45, 71, 72): return "other", "step_4 volatile global cover load vs another thread's store (SC)"
        if k in (46, 73): return "other", "step_4 different-value WAW column_of_prime_at_row[l]"
        if k in (51, 52, 78, 79): return "other", "step_5a/5b augmenting-path writes where paths join"
    if t == "lit-shoc-1": return "other", "warp-synchronous volatile reduce tail (scan_kernel.h L126-131)"
    if t == "lit-exllamav3-1": return "other", "same-value WAW: all 32 lanes store max_red[warp_id]"
    if t == "cccl-4": return "other", "decoupled look-back: relaxed tile-descriptor publish vs relaxed poll (by design)"
    if (t, k) in (("cccl-3", 6), ("raft-1", 6)): return "other", "emulated 64-bit shared atomicAdd: LDS.64 vs ATOMS.CAST.SPIN.64 (false report)"
    if t in ("cccl-3", "raft-1") or (t == "kokkos-5" and k in (1, 4)): return "other", "last-block counter idiom: no acquire after the counter atomic (REVIEW item 2)"
    if t == "kokkos-5" and k in (2, 5): return "other", "relaxed RMW chain + barrier orders the reset (observation order, not modelled)"
    if t in ("kokkos-5", "kokkos-6") and k in (3, 5, 6): return "other", "same-value global_flags reset by every thread of the last block"
    if t == "kokkos-6" and k == 1 and sub == "a": return "other", "warp-synchronous tree step, scalar_intra_warp_reduction width 32"
    if t == "kokkos-6": return "other", "width-8 intra-warp reduction: __syncwarp with 8-lane masks, cross-group reads"
    raise SystemExit(f"no mechanism for {g} {sub}")
out = []
for r in lines:
    g, sub = r["group"], r.get("sub", "")
    cls, rc = r["class"], r.get("race_class", "")
    oc, orc = cls, rc
    if tgt(g) == "lit-shoc-1": rc = "SC"
    if g == "llamacpp-5#01": cls, rc = "a", "DR"
    rel, m = mech(g, sub)
    out.append(dict(group=g, sub=sub, target=tgt(g), rows=r["rows"], cls=cls, race_class=rc, relation=rel, mechanism=m,
                    confidence=r.get("confidence", ""), same_in_fixed=r.get("same_in_fixed", ""), summary=r.get("summary", ""),
                    orig_class=oc, orig_race_class=orc))
dst = os.path.expanduser("~/wt-t21b/eval/results/realworld/other_reports_triage.csv")
with open(dst, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
import collections
tot = collections.Counter(); by = collections.Counter(); bym = collections.Counter(); byt = collections.defaultdict(collections.Counter)
for o in out:
    k = int(o["rows"]); tot[(o["cls"], o["race_class"])] += k; by[(o["relation"], o["cls"])] += k; bym[(o["relation"], o["cls"], o["race_class"], o["mechanism"])] += k
    byt[o["target"]][(o["cls"] + (o["race_class"] and "/" + o["race_class"]))] += k
print("rows", sum(int(o["rows"]) for o in out), "lines", len(out))
print("class:", dict(tot)); print("relation x class:", dict(by))
for k, v in sorted(bym.items(), key=lambda x: (x[0][0], -x[1])): print(f"  {v:5d} | {k[0]} | {k[1]}{('/' + k[2]) if k[2] else ''} | {k[3]}")
for t, c in sorted(byt.items()): print(f"  T {t}: {dict(c)} total {sum(c.values())}")
