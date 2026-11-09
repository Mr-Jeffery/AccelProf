#!/usr/bin/env python3
"""C2: reports collector-only makes that scalar-clock does not (same target, buggy build), with
(1) the control-flow shape between the two pcs and (2) the scalar-clock verdict for the same pair, read from the scalar-clock
kernel JSON of the same kernel (sync_dominance.analyze, installed rules, unchanged).  Facts only; a field that could not be obtained is empty.
  co_diff.py --set recall|cand --out <csv> [--ids a,b]
Shapes (first match, the order of the brief's table), on the region graph of the kernel's CFG (HBGraph.G), u/v = the two pcs:
  loop around the barrier  a qualifying block barrier lies on every path u->v but a wrap-around path of a loop skips it (R1 declines), or
                           a block barrier lies on every cycle through the region of u or of v (HBGraph.loop_scope)
  warp barrier between     no block barrier lies between u and v on every path, a qualifying warp barrier (WARPSYNC) does (or lies on every cycle)
  exit before the barrier  a block barrier is reachable from u or v, and u or v reaches EXIT on a path that crosses no block barrier
  barrier on one branch    a block barrier lies on some path u->v (or v->u) but not on every path
  other                    none of the above (no block barrier reachable between the pcs, or the dot is missing)"""
import argparse, csv, glob, json, os, re, sys
APH = "/home/fzheng4/AccelProf"
sys.path.insert(0, f"{APH}/python")
import networkx as nx
import sync_dominance as sd

ap = argparse.ArgumentParser()
ap.add_argument("--set", required=True, choices=["recall", "cand"])
ap.add_argument("--out", required=True)
ap.add_argument("--ids", default="")
a = ap.parse_args()
W = "/home/fzheng4/wt-co-rw"
if a.set == "recall":
    man, co_res, sc_res = f"{W}/eval/realworld/manifest_t21b.csv", f"{W}/eval/results/realworld_co", "/home/fzheng4/wt-t21b/eval/results/realworld"
    co_store, sc_store = "/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-co", "/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10"
else:
    man, co_res, sc_res = f"{W}/eval/realworld/manifest_t21c.csv", f"{W}/eval/results/realworld_co_t21c", "/home/fzheng4/wt-t21c/eval/results/realworld_t21c"
    co_store, sc_store = "/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-t21c-co", "/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-t21c"
ids = [r["id"] for r in csv.DictReader(open(man)) if r["variant"] == "buggy"]
if a.ids:
    ids = [i for i in ids if i in a.ids.split(",")]
excluded = {"lightgbm-new-1-buggy", "lightgbm-new-2-buggy", "llamacpp-open-2-buggy"}


def key(r):
    return (r["mangled"], frozenset((r["a_pc"], r["b_pc"])), r["space"])


_g = {}


def graph(dot, mangled):
    k = (dot, mangled)
    if k not in _g:
        try:
            _g[k] = sd.HBGraph(*sd.parse_dot(dot)[mangled])
        except Exception:                                       # noqa: BLE001
            _g[k] = None
    return _g[k]


def shape(g, u, v):
    if g is None or u not in g.pc_node or v not in g.pc_node:
        return "other", "no-graph"
    ru, rv = g.pc_node[u], g.pc_node[v]
    qual = list(g.qualifying)
    B = [s for s in qual if g.syncs[s][2] in (sd.BLOCK, sd.GRID)]
    Wp = [s for s in qual if g.syncs[s][2] == sd.WARP]

    def between(S):
        return [s for s in S if (s in g.postdom.get(ru, ()) and s in g.dom.get(rv, ())) or (s in g.postdom.get(rv, ()) and s in g.dom.get(ru, ()))]

    def wrap_path(S):
        sub = g.G.subgraph(n for n in g.G if n not in set(S))
        return nx.has_path(sub, ru, rv) or nx.has_path(sub, rv, ru)
    bb = between(B)
    if bb and wrap_path(bb):
        return "loop around the barrier", ",".join(hex(g.syncs[s][0]) for s in bb)
    ls = [g.loop_scope(u), g.loop_scope(v)]
    lb = [x for x in ls if x[0] in (sd.BLOCK, sd.GRID)]
    if lb:
        return "loop around the barrier", ",".join(hex(p) for p in sorted({p for x in lb for p in x[1]}))
    lw = [x for x in ls if x[0] == sd.WARP]
    ww = between(Wp)
    if not bb and (ww or lw):
        return "warp barrier between", ",".join([hex(g.syncs[s][0]) for s in ww] + [hex(p) for x in lw for p in x[1]])
    reach = [s for s in B if nx.has_path(g.G, ru, s) or nx.has_path(g.G, rv, s)]
    if reach:
        sub = g.G.subgraph(n for n in g.G if n not in set(B))
        for r in (ru, rv):
            if sd.VEXIT in g.G and nx.has_path(sub, r, sd.VEXIT) and any(nx.has_path(g.G, r, s) for s in B):
                return "exit before the barrier", ",".join(hex(g.syncs[s][0]) for s in reach)
        some = [s for s in B if (nx.has_path(g.G, ru, s) and nx.has_path(g.G, s, rv)) or (nx.has_path(g.G, rv, s) and nx.has_path(g.G, s, ru))]
        if some:
            return "barrier on one branch", ",".join(hex(g.syncs[s][0]) for s in some)
    return "other", ""


_an = {}


def sc_verdict(id_, dot, pcs, kname):
    """scalar-clock verdict for the pair: (verdict, hb_class, note) from the scalar-clock kernel JSONs of that kernel that judge it."""
    d = f"{sc_store}/{id_}/scalar-clock"
    if not os.path.isdir(d):
        return "", "", "no scalar-clock kernel JSONs"
    seen, n = [], 0
    for kj in sorted(glob.glob(f"{d}/kernel_*.json"), key=lambda p: int(re.findall(r"(\d+)", os.path.basename(p))[-1])):
        try:
            kn = json.load(open(kj))["kernel"]["kernel_name"]
        except Exception:                                       # noqa: BLE001
            continue
        if kn != kname:
            continue
        n += 1
        if n > 40:
            break
        if kj not in _an:
            try:
                _an[kj] = sd.analyze(dot, kj)
            except Exception:                                   # noqa: BLE001
                _an[kj] = None
        rep = _an[kj]
        if not rep:
            continue
        for v in rep["verdicts"]:
            if frozenset((v["current_pc"], v["ancient_pc"])) == pcs:
                seen.append((v["verdict"], v.get("hb_class")))
        if any(x[0] != "ORDERED" for x in seen):
            break
    if not seen:
        return "none", "", f"no scalar-clock verdict for the pair in {n} kernel JSON(s) of the kernel"
    bad = [s for s in seen if s[0] != "ORDERED"]
    s = bad[0] if bad else seen[0]
    return s[0], s[1] or "", ""


rows, summary = [], []
for id_ in ids:
    t = id_.rsplit("-", 1)[0]
    if id_ in excluded:
        summary.append(dict(id=id_, note="not run (excluded by the brief)"))
        continue
    p_co = f"{co_res}/attrib/{id_}.json"
    p_sc = f"{sc_res}/attrib/{id_}.json"
    if not os.path.exists(p_co):
        summary.append(dict(id=id_, note="no collector-only attribution"))
        continue
    co = json.load(open(p_co))["modes"].get("collector-only")
    scj = json.load(open(p_sc)) if os.path.exists(p_sc) else None
    sc = (scj or {}).get("modes", {}).get("scalar-clock")
    if co is None or sc is None:
        summary.append(dict(id=id_, n_co=len(co["reports"]) if co else None, note="no scalar-clock attribution" if sc is None else "no collector-only mode data"))
        continue
    ks = {key(r) for r in sc["reports"]}
    kc = {key(r) for r in co["reports"]}
    only = [r for r in co["reports"] if key(r) not in ks]
    summary.append(dict(id=id_, n_co=len(co["reports"]), n_sc=len(sc["reports"]), n_both=len(kc & ks), n_co_only=len(kc - ks), n_sc_only=len(ks - kc), note=""))
    for r in only:
        dot = f"{co_store}/{id_}/dots/{r['dot']}"
        g = graph(dot, r["mangled"]) if os.path.exists(dot) else None
        u, v = r["a_pc"], r["b_pc"]
        sh, bpcs = shape(g, u, v)
        kname = r.get("kernel") or ""
        v_sc, c_sc, why = sc_verdict(id_, dot, frozenset((u, v)), kname)
        fa = (r.get("a_frames") or [{}])[0]
        fb = (r.get("b_frames") or [{}])[0]
        rows.append(dict(id=id_, target=t, kernel=kname[:80], a_pc=hex(u), b_pc=hex(v), space=r["space"], race_type=r.get("race_type"),
                         co_verdict=r["verdict"], co_class=r.get("matrix_class"), a_op=r.get("a_op"), b_op=r.get("b_op"),
                         a=f"{fa.get('file', '')}:{fa.get('line', '')}", b=f"{fb.get('file', '')}:{fb.get('line', '')}",
                         shape=sh, barrier_pcs=bpcs, sc_verdict=v_sc, sc_hb_class=c_sc, sc_note=why))
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
if rows:
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
with open(a.out.replace(".csv", "_summary.json"), "w") as f:
    json.dump(summary, f, indent=1)
for s in summary:
    print(s)
print("co-only rows", len(rows))
