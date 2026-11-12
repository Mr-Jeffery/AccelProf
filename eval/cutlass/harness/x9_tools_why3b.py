#!/usr/bin/env python3
"""TOOLS_ON_STREAMK follow-up step 3b: R3's release/acquire points in the scalar-clock recordings (kernel JSON
hb_rmw_points, HbClock's online per-thread table: release[u] = pcs of the PO-next RMW of u's thread after each
instance of u, acquire[q] = PO-previous RMW) for the reported store and load pcs, plus the RMW pcs and opcodes.
usage: x9_tools_why3b.py <tools_streamk dir> <store root>"""
import json, glob, sys
D, ST = sys.argv[1], sys.argv[2]
for cf in sorted(glob.glob(f"{D}/confirm/scalar-clock/*.json")):
    c = json.load(open(cf)); i = c["id"]; pl = c.get("pc_lines", {})
    k = json.load(open(glob.glob(f"{ST}/scalar-clock/{i}/scalar-clock/kernel_*.json")[0]))
    rp = k.get("hb_rmw_points", {}); rel, acq = rp.get("release", {}), rp.get("acquire", {})
    st = sorted({r[x] for r in c["raw"] for x in ("a_pc", "b_pc") if pl.get(str(r[x])) == "block_striped.h:194"})
    ld = sorted({r[x] for r in c["raw"] for x in ("a_pc", "b_pc") if pl.get(str(r[x])) != "block_striped.h:194"})
    def show(tab, pcs):
        vals = {}
        for p in pcs:
            v = tab.get(str(p), tab.get(p, "absent"))
            vals.setdefault(json.dumps(v), []).append(p)
        return {kk: len(vv) for kk, vv in vals.items()}
    print(f"== {i}: store pcs {len(st)}, load pcs {len(ld)}; hb_rmw_points release {len(rel)} keys, acquire {len(acq)} keys")
    print("   release[store pc] ->", show(rel, st))
    print("   acquire[load pc]  ->", show(acq, ld))
    ex = list(rel.items())[:2]; print("   sample release entries:", ex)
    nonempty = {kk: v for kk, v in rel.items() if v}; print("   release keys with a non-empty value:", len(nonempty), list(nonempty.items())[:4])
    nonempty = {kk: v for kk, v in acq.items() if v}; print("   acquire keys with a non-empty value:", len(nonempty), list(nonempty.items())[:4])
