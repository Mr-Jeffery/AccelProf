#!/usr/bin/env python3
"""M2: the five barrier-dominance pairs of eval/MODE_PAIRS.md (difference
"finding:vc-reports/sc-ORDERED+R1": vector-clock mode reports the pair, barrier dominance R1
certifies it; sync_dominance annotates it model_bug), one analyze() call per kernel JSON.

MEASUREMENT ONLY, read-only. python/sync_dominance.py is imported as it is (the capture of its
trace and HBGraph is done by shadowing names in this process, as mode_pairs.py does). The same
recordings mode_pairs.py reads: store realworld-2026-10, the vector-clock no-dump recording.

ONE COMMAND (the analysis needs BeeGFS, so it runs in a SLURM job on partition normal, from the
repository root):
    sbatch -p normal -N 1 -t 00:30:00 -o eval/x_logs/m2/job-%j.log --wrap \
      "/home/fzheng4/AccelProf/.env/bin/python eval/baselines/model_bug_pairs.py"
writes eval/MODEL_BUG_PAIRS.md, eval/results/model-bug-pairs/pairs.csv and pairs_detail.json.
`... model_bug_pairs.py report` redoes the two tables from pairs_detail.json (no BeeGFS needed).
"""
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, f"{APH}/python")
sys.path.insert(0, f"{APH}/eval")
sys.path.insert(0, HERE)
import latent_census as lc  # noqa: E402

VC = lc.VC
STORE = "realworld-2026-10"
DIFF = f"{APH}/eval/results/mode-pairs/differences.csv"
WANT = "finding:vc-reports/sc-ORDERED+R1"
OUT = f"{APH}/eval/results/model-bug-pairs"
MD = f"{APH}/eval/MODEL_BUG_PAIRS.md"
COCHAIN_S2 = "/home/fzheng4/wt-c6b/eval/results/co-chain-b/merged-s2/baselines-cuvein.csv"
SCOPES = ["none", "warp", "block", "grid"]


def tid_parts(t):
    return {"block": t >> 10, "warp": (t >> 5) & 31, "thread": t & 31}


def tidstr(t):
    p = tid_parts(t)
    return f"b{p['block']}.w{p['warp']}.t{p['thread']}"


def cochain_ids():
    if not os.path.exists(COCHAIN_S2):
        return None
    return {r["id"]: r for r in csv.DictReader(open(COCHAIN_S2, newline=""))}


# ---------------------------------------------------------------- collect


def study(row, sd, nx, src, why, co):
    """-> the detail dict of one difference row."""
    _id = row["id"]
    key = frozenset((int(row["pc_a"], 16), int(row["pc_b"], 16)))
    pa, pb = sorted(key)
    d = {"id": _id, "kernel": row["kernel"], "pc_a": hex(pa), "pc_b": hex(pb),
         "kernel_file": row["kernel_file"], "store": STORE, "status": "ok"}
    # item 6: cuRace alone (collector-only mode), setting S2 of eval/co-chain-b
    if co is None:
        d["cochain_s2"] = f"missing: {COCHAIN_S2} not readable"
    elif _id not in co:
        d["cochain_s2"] = ("missing: id not in eval/co-chain-b S2 results (its store "
                           "final-2026-11-co has no realworld ids); not substituted")
    else:
        d["cochain_s2"] = f"program row present (verdict {co[_id]['verdict']}); pair-level missing: not read"
    s = src.get((_id, VC))
    if s is None:
        d["status"] = "missing: no vector-clock recording in the store (%s)" % why.get((_id, VC))
        return d
    pdir = s["pdir"]
    d["pdir"] = pdir
    kj = f"{pdir}/{VC}/{row['kernel_file']}"
    if not os.path.exists(kj):
        d["status"] = f"missing: {kj}"
        return d
    cap = {}

    class _J:                                  # shadows sync_dominance's `json` name
        def __getattr__(self, k):
            return getattr(json, k)

        def loads(self, s):
            cap["trace"] = json.loads(s)
            return cap["trace"]

    class _G(sd.HBGraph):                      # keeps the graph analyze() builds
        def __init__(self, *a):
            super().__init__(*a)
            cap["eng"] = self

    sd.json, sd.HBGraph = _J(), _G
    rep = dot = None
    for dot in sorted(glob.glob(f"{pdir}/dots/*.dot")):
        try:
            rep = sd.analyze(dot, kj)
            break
        except sd.AlignmentError as e:
            d["alignment_error"] = str(e)
    if rep is None:
        d["status"] = "missing: AlignmentError against every dot of the recording (trace/CFG misalignment)"
        return d
    tr, eng = cap["trace"], cap["eng"]
    d["dot"] = dot
    d["cfg_cluster"] = rep["kernel"]["mangled"]
    d["kernel_name_in_report"] = rep["kernel"]["name"]
    # 1. verdict records of the pair
    vs = [v for v in rep["verdicts"] if frozenset((v["current_pc"], v["ancient_pc"])) == key]
    d["verdicts"] = [{k: v.get(k) for k in (
        "current_pc_hex", "ancient_pc_hex", "opcodes", "space", "race_type", "verdict",
        "hb_class", "matrix_class", "strength", "observed_distance", "ordering_syncs",
        "hb_chain", "event_candidate", "edge_rescued", "model_bug", "conflict_class",
        "contested_weight")} for v in vs]
    for v in d["verdicts"]:
        v["ordering_syncs"] = [hex(p) for p in v["ordering_syncs"]]
    # 2. every hb_races record of the pair
    recs = []
    for r in tr.get("hb_races") or ():
        if frozenset((r["a_pc"], r["b_pc"])) == key:
            recs.append({"a_pc": hex(r["a_pc"]) if r["a_pc"] is not None else None,
                         "b_pc": hex(r["b_pc"]), "a": tid_parts(r["a_tid"]),
                         "b": tid_parts(r["b_tid"]),
                         "distance": SCOPES[sd.thread_distance(r["a_tid"], r["b_tid"])],
                         "record_dist": r.get("dist"), "class": r.get("class"),
                         "space": r.get("space"), "kind": r.get("kind"),
                         "count": r.get("count"), "loc_block": r.get("loc_block"),
                         "addr": r.get("addr"), "async": r.get("async")})
    d["hb_races"] = recs
    # 3. hb_races_sync_only
    so = tr.get("hb_races_sync_only")
    if so is None:
        d["sync_only"] = "missing: key absent in the recording"
    else:
        m = [x for x in so if frozenset((x[0], x[1])) == key]
        d["sync_only"] = {"in": bool(m), "count": sum(x[2] for x in m)}
    # 4. PC dependency graph edges between the two PCs
    d["edges"] = []
    for e in tr.get("edges", []):
        if e.get("ancient_pc") is not None and \
                frozenset((e["current_pc"], e["ancient_pc"])) == key:
            ee = {k: v for k, v in e.items() if "flags" not in k}
            sc, n = sd._observed(e.get("dist", {}))
            ee["observed_bucket"], ee["observed_count"] = SCOPES[sc], n
            d["edges"].append(ee)
    # 5. loop membership: SCC of the sync-split region graph (HBGraph.G, built from the CFG in
    # `dot`) containing the certifying barrier node sync@<pc>
    comp_of = {}
    for i, c in enumerate(nx.strongly_connected_components(eng.G)):
        for n in c:
            comp_of[n] = i
    comps = {}
    for n, i in comp_of.items():
        comps.setdefault(i, set()).add(n)
    ru, rv = eng.pc_node[pa], eng.pc_node[pb]
    loops = []
    for v in vs:
        for p in v["ordering_syncs"]:
            sid = f"sync@{p:#x}"
            c = comps[comp_of[sid]]
            cyc = len(c) > 1 or eng.G.has_edge(sid, sid)
            loops.append({"sync": hex(p), "barrier_on_cycle": cyc,
                          "pc_a_in_barrier_cycle": ru in c, "pc_b_in_barrier_cycle": rv in c,
                          "both": bool(cyc and ru in c and rv in c)})
    d["loop"] = {"regions": [ru, rv], "per_sync": loops,
                 "both_in_loop_with_barrier": any(x["both"] for x in loops),
                 "pc_a_on_any_cycle": len(comps[comp_of[ru]]) > 1,
                 "pc_b_on_any_cycle": len(comps[comp_of[rv]]) > 1,
                 "source": f"{dot} cluster {d['cfg_cluster']}: HBGraph.G strongly connected "
                           "component of the sync node"}
    d["opcodes_in_cfg"] = [eng.pc_opcode[pa], eng.pc_opcode[pb]]
    return d


def collect():
    import networkx as nx
    import sync_dominance as sd
    rows = [r for r in csv.DictReader(open(DIFF, newline="")) if r["difference"] == WANT]
    src, why = lc.select_sources([STORE])
    co = cochain_ids()
    det = [study(r, sd, nx, src, why, co) for r in rows]
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/pairs_detail.json", "w") as f:
        json.dump({"difference": WANT, "rows_in_differences_csv": len(rows), "pairs": det},
                  f, indent=1)
    return det


# ---------------------------------------------------------------- report


def _thr(r):
    return f"b{r['a']['block']}.w{r['a']['warp']}.t{r['a']['thread']}~b{r['b']['block']}.w{r['b']['warp']}.t{r['b']['thread']}"


def summarize(d):
    """-> flat dict (one csv row) of one detail dict."""
    o = {"id": d["id"], "kernel": d["kernel"], "pc_a": d["pc_a"], "pc_b": d["pc_b"],
         "kernel_file": d["kernel_file"], "status": d["status"]}
    if d["status"] != "ok":
        o["cochain_s2"] = d["cochain_s2"]
        return o
    v = d["verdicts"][0] if d["verdicts"] else {}
    o.update(n_verdict_records=len(d["verdicts"]), verdict=v.get("verdict"),
             strength=v.get("strength"), observed_distance=v.get("observed_distance"),
             syncs=" ".join(v.get("ordering_syncs") or []), hb_chain=v.get("hb_chain"),
             event_candidate=v.get("event_candidate"), model_bug=v.get("model_bug"))
    rs = d["hb_races"]
    groups = {}
    for r in rs:
        groups.setdefault((r["distance"], r["class"], r["space"], r["kind"]), []).append(r)
    o["hb_races_n"] = len(rs)
    o["hb_races"] = " ; ".join(
        f"{k[0]}/{k[1]}/{k[2]}/{k[3]} x{len(g)} (instances {sum(x['count'] or 0 for x in g)}): "
        + ", ".join(_thr(x) for x in g[:2]) + (f", +{len(g) - 2}" if len(g) > 2 else "")
        for k, g in sorted(groups.items()))
    o["hb_races_distances"] = "/".join(sorted({r["distance"] for r in rs}, key=SCOPES.index))
    so = d["sync_only"]
    o["in_hb_races_sync_only"] = so if isinstance(so, str) else \
        (f"yes (count {so['count']})" if so["in"] else "no")
    o["edges"] = " ; ".join(
        f"{e['current_pc_hex']}<-{e['ancient_pc_hex']} " + " ".join(
            f"{k.replace('intra_', '')}={n}" for k, n in e["dist"].items() if n) +
        f" (observed {e['observed_bucket']}x{e['observed_count']})" for e in d["edges"]) or "none"
    lp = d["loop"]
    o["loop_with_barrier"] = lp["both_in_loop_with_barrier"]
    o["loop_detail"] = "; ".join(
        f"{x['sync']}: barrier_on_cycle={x['barrier_on_cycle']} a={x['pc_a_in_barrier_cycle']} "
        f"b={x['pc_b_in_barrier_cycle']}" for x in lp["per_sync"])
    o["cochain_s2"] = d["cochain_s2"]
    return o


def sentence(group, ds):
    """One sentence per kernel: which of (a)-(d) holds, from the data."""
    ok = [d for d in ds if d["status"] == "ok"]
    if not ok:
        return f"`{group}`: not decided, no analysable recording ({'; '.join(d['status'] for d in ds)})."
    wide = loop = False
    obs, races, edge_b = set(), set(), set()
    for d in ok:
        o = d["verdicts"][0]["observed_distance"]
        obs.add(o)
        rd = {r["distance"] for r in d["hb_races"]}
        races |= rd
        edge_b |= {e["observed_bucket"] for e in d["edges"]}
        wide = wide or any(SCOPES.index(x) > SCOPES.index(o) for x in rd)
        loop = loop or d["loop"]["both_in_loop_with_barrier"]
    mis = any("alignment_error" in d for d in ok)
    strn = "/".join(sorted({d["verdicts"][0]["strength"] for d in ok}))
    facts = (f"strength {strn}, observed_distance {'/'.join(sorted(obs))} (edge buckets "
             f"{'/'.join(sorted(edge_b)) or 'none, event candidate'}), hb_races instances at "
             f"{'/'.join(sorted(races, key=SCOPES.index)) or 'none'}")
    holds = [t for t, f in (("(a) raced instance at a wider distance than observed_distance", wide),
                            ("(b) loop around the barrier", loop)) if f]
    if holds:
        return f"`{group}`: {' and '.join(holds)}; {facts}."
    return (f"`{group}`: (d) none of (a), (b), (c); {facts}, the pcs are not both in a cycle "
            f"through the certifying barrier, and no AlignmentError{' (but one dot misaligned)' if mis else ''}.")


def report(det=None):
    if det is None:
        det = json.load(open(f"{OUT}/pairs_detail.json"))["pairs"]
    rows = [summarize(d) for d in det]
    cols = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/pairs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, cols, restval="")
        w.writeheader()
        w.writerows(rows)
    heads = ["pair (id, kernel file, kernel, pcs)", "1 verdict record", "2 hb_races records",
             "3 in sync_only", "4 PC-graph edges", "5 loop around barrier", "6 cuRace alone S2"]
    t = ["| " + " | ".join(heads) + " |", "|" + "---|" * len(heads)]
    for r in rows:
        head = f"{r['id']}, {r['kernel_file']}, {r['kernel']}, {r['pc_a']} / {r['pc_b']}"
        if r["status"] != "ok":
            t.append(f"| {head} | {r['status']} | | | | | {r['cochain_s2']} |")
            continue
        vr = (f"{r['verdict']}; strength {r['strength']}; observed {r['observed_distance']}; syncs "
              f"{r['syncs'] or 'none'}; hb_chain {r['hb_chain']}; event_candidate "
              f"{r['event_candidate']}; model_bug {r['model_bug']}")
        t.append(f"| {head} | {vr} | {r['hb_races_n']} records: {r['hb_races']} | "
                 f"{r['in_hb_races_sync_only']} | {r['edges']} | {r['loop_with_barrier']} "
                 f"({r['loop_detail']}) | {r['cochain_s2']} |")
    groups = {}
    for d in det:
        groups.setdefault(d["id"].rsplit("-", 1)[0], []).append(d)
    md = ["# M2: the five barrier-dominance pairs of MODE_PAIRS.md", "",
          "Run: `sbatch -p normal -N 1 -t 00:30:00 -o eval/x_logs/m2/job-%j.log --wrap "
          "\"/home/fzheng4/AccelProf/.env/bin/python eval/baselines/model_bug_pairs.py\"` "
          "(repository root; one `analyze()` per kernel JSON; `report` redoes these tables from "
          "`eval/results/model-bug-pairs/pairs_detail.json`).", "",
          f"Pairs: the rows of `eval/results/mode-pairs/differences.csv` with difference "
          f"`{WANT}` (vector-clock mode reports the pair, barrier dominance R1 certifies it; "
          f"annotated model_bug). Store `{STORE}`, vector-clock no-dump recording, the files "
          "`mode_pairs.py` reads. Thread = block.warp.thread; `~` joins the two threads of a "
          "record; records are grouped by distance/class/space/kind (count of records, sum of "
          "their instance counts, first two thread pairs); every record is in `pairs_detail.json`. "
          "The kernel name is cut to 70 characters here (full in the csv). Distance is from the two thread ids (warp: same warp, block: same block, grid: "
          "different blocks).", ""]
    md += t + ["", "Item 5 is read from the sync-split region graph `HBGraph.G` that `analyze()` "
               "builds from the recording's `.dot` CFG: true iff the certifying barrier node lies "
               "on a cycle and both pcs' regions are in its strongly connected component. "
               "Item 6: the table of `eval/results/co-chain-b/merged-s2/baselines-cuvein.csv` "
               "(branch eval/co-chain-b) holds the store `final-2026-11-co` only.", "",
          "## Per kernel", ""]
    md += [f"- {sentence(g, ds)}" for g, ds in groups.items()]
    open(MD, "w").write("\n".join(md) + "\n")


if __name__ == "__main__":
    report(None if sys.argv[1:] == ["report"] else collect())
