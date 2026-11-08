#!/usr/bin/env python3
"""X12: how far apart are two recordings of one program, in a way that separates schedule noise from a different pass.
Per kernel pair: (1) edge sets equal? (2) node sets equal? (3) per-edge TOTAL over all dist classes equal (counts conserved, only their
split between dist classes moves)? (4) total records (sum of all dist counts) equal? Reports kernel counts for each check.
  x12_noise.py LABEL A_DIR B_DIR      (dirs of kernel_<i>.json)"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "baselines", "setup"))
import co_json_diff as D

def total(e):
    d = e.get("dist") or {}
    return sum(v for v in d.values() if isinstance(v, (int, float)))

def pair(a, b):
    ja, jb = json.load(open(a)), json.load(open(b))
    ea = {D.edge_key(e): e for e in ja.get("edges") or []}; eb = {D.edge_key(e): e for e in jb.get("edges") or []}
    na = {n.get("pc") for n in ja.get("nodes") or []}; nb = {n.get("pc") for n in jb.get("nodes") or []}
    same_edges = set(ea) == set(eb)
    same_nodes = na == nb
    common = set(ea) & set(eb)
    edge_tot_eq = all(total(ea[k]) == total(eb[k]) for k in common)
    grand = sum(map(total, ea.values())) == sum(map(total, eb.values()))
    exact = ja == jb
    return exact, same_edges, same_nodes, edge_tot_eq, grand

def run(label, A, B):
    fa, fb = D.kernel_files(A), D.kernel_files(B)
    ks = sorted(set(fa) & set(fb))
    c = [0] * 5
    for k in ks:
        r = pair(fa[k], fb[k])
        for i, v in enumerate(r):
            c[i] += bool(v)
    n = len(ks)
    print(f"{label}: kernels={n} exact={c[0]} same_edge_set={c[1]} same_node_set={c[2]} per_edge_total_equal={c[3]} grand_total_equal={c[4]} (unmatched files {len(set(fa) ^ set(fb))})")

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
