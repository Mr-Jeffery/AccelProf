#!/usr/bin/env python3
"""T26: compare two recordings' kernel JSONs (collector-only, or any mode) kernel by kernel.

    co_json_diff.py A B [--label NAME] [--json OUT] [--max-list N]

A and B are kernel JSON files or directories holding kernel_<i>.json (a store's <id>/<mode>/ or a
tool's dependency_* directory). Nothing is ignored except the tool/runtime hash fields (top-level keys
named in IGNORE; a kernel JSON carries none today, meta.json does). Per kernel it reports whether the
files are byte-identical and, when they are not, the PCDepGraph differences: edges (current_pc,
ancient_pc) only in A, only in B, edges in both whose dist counts or flags differ (each count's A and B
value), nodes only in A / only in B / whose fields differ (flags, access size, the three histograms),
kernel-header fields that differ, and every other top-level key (hb_* aggregates included) that is not
equal. Exit status 0 iff every kernel present in either side is present in both and equal (parsed JSON
equal; byte identity is reported separately).
"""
import argparse
import glob
import json
import os
import re
import sys

IGNORE = {"tool_hash", "runtime", "runtime_hash", "libsanalyzer", "collector"}   # hash fields only


def kernel_files(p):
    if os.path.isfile(p):
        return {os.path.basename(p): p}
    out = {}
    for f in glob.glob(os.path.join(p, "kernel_*.json")):
        if re.fullmatch(r"kernel_\d+\.json", os.path.basename(f)):
            out[os.path.basename(f)] = f
    return out


def edge_key(e):
    return (e.get("current_pc"), e.get("ancient_pc"))


def diff_kernel(fa, fb, max_list):
    ba, bb = open(fa, "rb").read(), open(fb, "rb").read()
    r = {"bytes_equal": ba == bb}
    if r["bytes_equal"]:
        r["equal"] = True
        return r
    try:
        ja, jb = json.loads(ba), json.loads(bb)
    except ValueError as ex:
        r.update(equal=False, error=f"unparsable: {ex}")
        return r
    for k in IGNORE:
        ja.pop(k, None)
        jb.pop(k, None)
    ea = {edge_key(e): e for e in ja.get("edges") or []}
    eb = {edge_key(e): e for e in jb.get("edges") or []}
    only_a = sorted(set(ea) - set(eb), key=str)
    only_b = sorted(set(eb) - set(ea), key=str)
    changed = []
    for k in sorted(set(ea) & set(eb), key=str):
        if ea[k] != eb[k]:
            d = {}
            for f in sorted(set(ea[k]) | set(eb[k])):
                va, vb = ea[k].get(f), eb[k].get(f)
                if f == "dist" and isinstance(va, dict) and isinstance(vb, dict):
                    for c in sorted(set(va) | set(vb)):
                        if va.get(c) != vb.get(c):
                            d[f"dist.{c}"] = [va.get(c), vb.get(c)]
                elif va != vb:
                    d[f] = [va, vb]
            changed.append({"edge": list(k), "diff": d})
    na = {n.get("pc"): n for n in ja.get("nodes") or []}
    nb = {n.get("pc"): n for n in jb.get("nodes") or []}
    nodes_only_a = sorted(set(na) - set(nb), key=str)
    nodes_only_b = sorted(set(nb) - set(na), key=str)
    nodes_changed = []
    for k in sorted(set(na) & set(nb), key=str):
        if na[k] != nb[k]:
            nodes_changed.append({"pc": k, "fields": sorted(f for f in set(na[k]) | set(nb[k])
                                                            if na[k].get(f) != nb[k].get(f))})
    header = {}
    ka, kb = ja.get("kernel") or {}, jb.get("kernel") or {}
    for f in sorted(set(ka) | set(kb)):
        if ka.get(f) != kb.get(f):
            header[f] = [ka.get(f), kb.get(f)]
    other = sorted(k for k in set(ja) | set(jb)
                   if k not in ("edges", "nodes", "kernel") and ja.get(k) != jb.get(k))
    r.update(edges_only_a=len(only_a), edges_only_b=len(only_b), edges_changed=len(changed),
             nodes_only_a=len(nodes_only_a), nodes_only_b=len(nodes_only_b),
             nodes_changed=len(nodes_changed), header=header, other_keys=other,
             dist_count_diffs=sum(1 for c in changed for f in c["diff"] if f.startswith("dist.")))
    r["equal"] = not (only_a or only_b or changed or nodes_only_a or nodes_only_b or nodes_changed
                      or header or other)
    if not r["equal"]:
        r["examples"] = {"edges_only_a": [list(k) for k in only_a[:max_list]],
                         "edges_only_b": [list(k) for k in only_b[:max_list]],
                         "edges_changed": changed[:max_list],
                         "nodes_only_a": nodes_only_a[:max_list], "nodes_only_b": nodes_only_b[:max_list],
                         "nodes_changed": nodes_changed[:max_list]}
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--label", default="")
    ap.add_argument("--json", help="write the per-kernel report here")
    ap.add_argument("--max-list", type=int, default=5)
    ap.add_argument("--quiet", action="store_true", help="one summary line only")
    a = ap.parse_args()
    fa, fb = kernel_files(a.a), kernel_files(a.b)
    if not fa and not fb:
        print(f"{a.label} NO-KERNELS a={a.a} b={a.b}")
        return 2
    rep = {"a": a.a, "b": a.b, "kernels": {}, "only_in_a": sorted(set(fa) - set(fb)),
           "only_in_b": sorted(set(fb) - set(fa))}
    for k in sorted(set(fa) & set(fb), key=lambda s: int(re.findall(r"\d+", s)[0])):
        rep["kernels"][k] = diff_kernel(fa[k], fb[k], a.max_list)
    ks = rep["kernels"].values()
    summ = {"kernels": len(rep["kernels"]), "bytes_equal": sum(r["bytes_equal"] for r in ks),
            "differ": sum(not r["equal"] for r in ks), "only_in_a": len(rep["only_in_a"]),
            "only_in_b": len(rep["only_in_b"]),
            "edges_only_a": sum(r.get("edges_only_a", 0) for r in ks),
            "edges_only_b": sum(r.get("edges_only_b", 0) for r in ks),
            "edges_changed": sum(r.get("edges_changed", 0) for r in ks),
            "dist_count_diffs": sum(r.get("dist_count_diffs", 0) for r in ks),
            "nodes_differ": sum(r.get("nodes_only_a", 0) + r.get("nodes_only_b", 0) + r.get("nodes_changed", 0)
                                for r in ks)}
    rep["summary"] = summ
    ok = summ["differ"] == 0 and summ["only_in_a"] == 0 and summ["only_in_b"] == 0
    print(f"{a.label} {'EQUAL' if ok else 'DIFFER'} " + " ".join(f"{k}={v}" for k, v in summ.items()))
    if not a.quiet and not ok:
        for k, r in rep["kernels"].items():
            if not r["equal"]:
                print(f"  {k}: " + json.dumps({x: r[x] for x in r if x not in ("examples",)}))
                print(f"    examples: {json.dumps(r.get('examples'))[:2000]}")
        if rep["only_in_a"] or rep["only_in_b"]:
            print(f"  only in A: {rep['only_in_a'][:20]}  only in B: {rep['only_in_b'][:20]}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(rep, f, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
