#!/usr/bin/env python3
"""X9 step 0c probe: print the structure of hb_events around LDGSTS pcs of one dump kernel JSON."""
import glob, json, os, sys
from collections import Counter
sys.path.insert(0, "/home/fzheng4/wt-x9/python")
import sync_dominance as sd
idir = sys.argv[1]
dots = sorted(glob.glob(f"{idir}/dots/*.dot"))
for kj in sorted(glob.glob(f"{idir}/scalar-clock/kernel_*.json"), key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0])):
    t = json.load(open(kj))
    name = t["kernel"]["kernel_name"]
    if "MmaMultistage" not in name:
        continue
    for d in dots:
        try:
            ks = sd.parse_dot(d)
        except Exception:
            continue
        try:
            m = sd.select_kernel(ks, name)
        except Exception:
            continue
        g = sd.HBGraph(*ks[m]); break
    ldg = {pc: op for pc, op in g.pc_opcode.items() if op.startswith("LDGSTS")}
    dep = {pc: op for pc, op in g.pc_opcode.items() if op.startswith(("DEPBAR", "LDGDEPBAR"))}
    print(os.path.basename(kj), "keys:", sorted(t.keys()))
    print(" hb_async:", t.get("hb_async"), " LDGSTS pcs:", len(ldg), sorted(set(ldg.values())), " DEPBAR/LDGDEPBAR:", sorted(set(dep.values())))
    ev = t.get("hb_events", [])
    print(" events:", len(ev), Counter(e["type"] for e in ev).most_common(12))
    sample = [e for e in ev if e.get("pc") in ldg][:2]
    for e in sample:
        print(" LDGSTS event:", json.dumps({k: (v[:3] if isinstance(v, list) else v) for k, v in e.items()})[:700])
    sample = [e for e in ev if e["type"] in ("pipeline_commit", "pipeline_wait")][:2]
    for e in sample:
        print(" pipeline event:", json.dumps({k: (v[:3] if isinstance(v, list) else v) for k, v in e.items()})[:400])
    print(" async_pcs (sd):", len(sd.dump_async_pcs(g, t)), "== LDGSTS pcs" if sd.dump_async_pcs(g, t) == set(ldg) else "!= LDGSTS pcs")
    break
