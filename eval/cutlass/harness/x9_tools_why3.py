#!/usr/bin/env python3
"""TOOLS_ON_STREAMK follow-up step 3: for every pc pair cuRace reported (confirm JSON raw), the recorded edge(s) between
the two pcs in the kernel JSON of the same recording and their instance counts by relation of the earlier (ancient) and
later (current) accessor: dist.intra_thread / intra_warp / intra_block / intra_grid (intra_grid = different CTAs).
usage: x9_tools_why3.py <tools_streamk dir> <store root> > why/edges.tsv   (compute node: stores on BeeGFS)"""
import json, glob, sys, collections
D, ST = sys.argv[1], sys.argv[2]
attr = {}
for ln in open(f"{D}/attribution.tsv").read().split("\n")[1:]:
    x = ln.split("\t")
    if len(x) > 11 and x[0].startswith("cuRace"): pass
print("mode\tid\tstore_pc\tload_pc\tedges\tintra_thread\tintra_warp\tintra_block\tintra_grid\tintra_instance_launch\tcold_miss")
for mode, sub, sm in (("scalar-clock", "scalar-clock", "scalar-clock"), ("S2", "s2", "collector-only")):
    for cf in sorted(glob.glob(f"{D}/confirm/{sub}/*.json")):
        c = json.load(open(cf)); i = c["id"]; pl = c.get("pc_lines", {})
        kj = glob.glob(f"{ST}/{sm}/{i}/{sm}/kernel_*.json")
        k = json.load(open(kj[0]))
        E = collections.defaultdict(list)
        for e in k["edges"]:
            E[(e.get("ancient_pc"), e["current_pc"])].append(e)
        agg = collections.defaultdict(collections.Counter)
        for r in c["raw"]:
            if r["space"] != "global": continue
            a, b = r["a_pc"], r["b_pc"]
            la, lb = pl.get(str(a), "?"), pl.get(str(b), "?")
            st, ld = (a, b) if la == "block_striped.h:194" else (b, a)
            es = E.get((st, ld), []) + E.get((ld, st), [])
            key = (i, pl.get(str(st)), pl.get(str(ld)))
            agg[key]["pairs"] += 1; agg[key]["edges"] += len(es)
            for e in es:
                for kk, v in e["dist"].items(): agg[key][kk] += v
                agg[key]["cold"] += bool(e.get("cold_miss"))
                agg[key]["dir_" + ("store->load" if e.get("ancient_pc") == st else "load->store")] += 1
        for (i2, s, l), cn in agg.items():
            print(f"{mode}\t{i2}\t{s}\t{l}\tpairs={cn['pairs']} edges={cn['edges']} {dict((k,v) for k,v in cn.items() if k.startswith('dir_'))}"
                  f"\t{cn['intra_thread']}\t{cn['intra_warp']}\t{cn['intra_block']}\t{cn['intra_grid']}\t{cn['intra_instance_launch']}\t{cn['cold']}")
