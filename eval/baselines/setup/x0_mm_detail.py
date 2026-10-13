#!/usr/bin/env python3
"""X0: the one kernel whose content the new default changes (P4-matrix-multiplication-norace-small,
scalar-clock, t20-parity2): the verdicts and skipped edges present on one path only."""
import os,sys,glob,json
sys.path.insert(0,"python"); import sync_dominance as sd
S="/mnt/beegfs/fzheng4/cuvein_traces/t20-parity2/P4-matrix-multiplication-norace-small"
dots=sorted(glob.glob(S+"/dots/*.dot")); kj=S+"/scalar-clock/kernel_0.json"
def run(old):
    for k in ("CUVEIN_PREFER_RECORDS","CUVEIN_PREFER_AGGREGATES","CUVEIN_BARRIER_PASS_MAX_LANES"): os.environ.pop(k,None)
    if old: os.environ["CUVEIN_PREFER_RECORDS"]="1"
    for d in dots:
        try: return sd.analyze(d,kj)
        except sd.AlignmentError: pass
a,b=run(True),run(False)
K=lambda v:(v["ancient_pc"],v["current_pc"],v["race_type"])
ka={K(v) for v in a["verdicts"]}
for v in b["verdicts"]:
    if K(v) not in ka:
        print("NEW", {x:v.get(x) for x in ("ancient_pc_hex","current_pc_hex","race_type","verdict","reason","hb_class","conflict_class","observed_distance","event_candidate","edge_rescued","rule","ordered_by","static")})
sk=lambda r: json.dumps(r,sort_keys=True)
sa={sk(r) for r in a["skipped_edges"]}; sb={sk(r) for r in b["skipped_edges"]}
for r in sorted(sa-sb): print("SKIPPED only old:", r[:300])
for r in sorted(sb-sa): print("SKIPPED only new:", r[:300])
print("cand", a["diagnostics"]["event_candidates"], b["diagnostics"]["event_candidates"])
print("keys of a verdict:", sorted(b["verdicts"][0].keys()))
