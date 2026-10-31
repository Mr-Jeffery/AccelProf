#!/usr/bin/env python3
"""X7 Part B4: cell values from one sandbox (old or new). usage: cap_cells.py <sandbox> <out.json> [keys.json]
The sandbox holds eval/baselines/make_tables.py and an eval/results/ tree (see cap_tables.sh)."""
import sys, os, json, math, re, csv, collections, statistics
SB, OUTJ = sys.argv[1], sys.argv[2]
NEW = set(tuple(k) for k in json.load(open(sys.argv[3]))) if len(sys.argv) > 3 else set()
sys.argv = [sys.argv[0], "--collector-only"]
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt
runs, meta = mt.load_runs(); man = mt.load_manifest()
VC, SC, CO = mt.VC, mt.SC, mt.CO
LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN", "P9-atomicCAS-cuda": "CLEAN"}   # evaluation.tex: atomicCAS and knn are scored race-free
OUT_OF_SCOPE = ("asyncmemcpy/", "hostdevice/", "interkernel/")
def label(i): return LABEL_OVERRIDE.get(i, man[i].get("label", ""))
SUITES = [("Indigo3", lambda i, m: m[0] == "P1"), ("Indigo 1.3", lambda i, m: m[0] == "PI"),
          ("Indigo 1.3, SC's 99", lambda i, m: mt._in(m, ("PI@sc",))), ("ECL", lambda i, m: m[0] == "P3"),
          ("ScoR applications", lambda i, m: m[0] == "P4"), ("ScoR litmus + canary", lambda i, m: m[0] == "P5"),
          ("cuHadron (in scope)", lambda i, m: m[0] == "P6" and not m[1].startswith(OUT_OF_SCOPE)),
          ("HeCBench, SC's 10", lambda i, m: m[0] == "P9")]
AGG = ("Indigo3", "Indigo 1.3", "ECL", "ScoR applications", "cuHadron (in scope)")
def cnt(): return dict(tp=0, pos=0, fp=0, neg=0, to=0, err=0)
def tool_cell(keys, pred, restrict=None):
    """keys: list of (tool, mode) -- one tool, or several (union: positive if any RACE; TO/ERR if any is)."""
    c = cnt()
    for i, m in meta.items():
        if not pred(i, m): continue
        rs = [runs.get((i,) + k) for k in keys]
        rs = [r for r in rs if r is not None]
        if len(rs) < len(keys): continue
        vs = [r["verdict"] for r in rs]
        lab = label(i)
        if "TIMEOUT" in vs: 
            if lab in ("RACE", "CLEAN"): c["to"] += 1
            continue
        if "ERROR" in vs:
            if lab in ("RACE", "CLEAN"): c["err"] += 1
            continue
        if lab == "RACE":
            if restrict is not None and str(man[i].get("shared_mem", "0")) != restrict: continue
            c["pos"] += 1; c["tp"] += "RACE" in vs
        elif lab == "CLEAN": c["neg"] += 1; c["fp"] += "RACE" in vs
    return c
def agg(f):
    t = cnt()
    for name, pred in SUITES:
        if name in AGG:
            for k, v in f(pred).items(): t[k] += v
    return t
out = {}
TOOLS = {"racecheck": [("racecheck", "")], "iguard": [("iguard", "")], "union": [("racecheck", ""), ("iguard", "")],
         "hirace": [("hirace", "")], "supercollider": [("supercollider", "")]}
t4 = {}
for name, pred in SUITES + [("All pre-registered", None)]:
    t4[name] = {}
    for tn, ks in TOOLS.items():
        t4[name][tn] = (agg(lambda p: tool_cell(ks, p)) if pred is None else tool_cell(ks, pred))
    # union table: racecheck over shared memory, iGUARD over global memory
    t4[name]["racecheck_shared"] = agg(lambda p: tool_cell(TOOLS["racecheck"], p, "1")) if pred is None else tool_cell(TOOLS["racecheck"], pred, "1")
    t4[name]["iguard_global"] = agg(lambda p: tool_cell(TOOLS["iguard"], p, "0")) if pred is None else tool_cell(TOOLS["iguard"], pred, "0")
out["baseline_cells"] = t4
# ---- ratios with the same-job native wall for re-run rows ----
# id-level native walls exactly as mt._ratios builds them
nat_id, nat_co = {}, {}
for (i, t, m), r in runs.items():
    if r["native"] and t != "supercollider":
        d = nat_co if (t == "cuvein" and m == CO) else nat_id
        d[i] = min(d.get(i, r["native"]), r["native"])
out["native_id"] = {i: [nat_id.get(i), nat_co.get(i)] for i in set(nat_id) | set(nat_co)}
rat = dict(mt._ratios(runs, meta))
if os.environ.get("CAP_OVERRIDE_NATIVE") == "1":
    # new merge: a row that stayed keeps the denominator it had in the old merge (the replaced rows' natives left the id-level minimum);
    # a re-run row divides by its own native wall (same job)
    oldn = json.load(open(os.environ["CAP_OLD_JSON"]))["native_id"]
    for k, r in runs.items():
        if not r["wall"]: continue
        if k in NEW:
            if r["native"]: rat[k] = r["wall"] / r["native"]
        elif k[1] != "supercollider" and k[0] in oldn:
            a, b = oldn[k[0]]
            n = (min(x for x in (a, b) if x) if (k[1] == "cuvein" and k[2] == CO and (a or b)) else a)
            if n: rat[k] = r["wall"] / n
SL = [("Indigo3", ("P1",)), ("Indigo 1.3", ("PI",)), ("ECL", ("P3",)), ("ScoR apps", ("P4",)), ("ScoR litmus", ("P5",)),
      ("cuHadron", ("P6",)), ("HeCBench other 14", ("P7",)), ("HeCBench SC 10", ("P9",)), ("All", ("P1", "PI", "P3", "P4", "P5", "P6"))]
TK = [("cuvein", VC), ("cuvein", SC), ("cuvein", CO), ("racecheck", ""), ("iguard", ""), ("hirace", ""), ("supercollider", "")]
def gm(xs): return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None
def ok(k): return runs[k]["verdict"] in ("RACE", "CLEAN") and k in rat
fig = {}
for name, ps in SL:
    for tk in TK:
        xs = [x for k, x in rat.items() if k[1:] == tk and meta[k[0]][0] in ps and ok(k)]
        fig[f"{name}|{tk[0]}/{tk[1]}"] = (len(xs), gm(xs))
out["fig"] = fig
# ---- common set per suite: programs every tool on that suite finished ----
common = {}
COMMON_TOOLS = [("cuvein", VC), ("cuvein", SC), ("racecheck", ""), ("iguard", ""), ("hirace", ""), ("supercollider", "")]
for name, ps in SL:
    ids = [i for i in meta if meta[i][0] in ps]
    present = [tk for tk in COMMON_TOOLS if any((i,) + tk in runs for i in ids)]
    # a tool "runs on the suite" if it has a row for at least half of the suite's programs
    present = [tk for tk in present if sum((i,) + tk in runs for i in ids) >= 0.5 * len(ids)]
    cs = [i for i in ids if all(((i,) + tk) in runs and ok((i,) + tk) for tk in present)]
    d = {"tools": [f"{a}/{b}" for a, b in present], "n_common": len(cs)}
    for tk in TK:
        xs = [rat[(i,) + tk] for i in cs if ((i,) + tk) in rat and ok((i,) + tk)]
        d[f"{tk[0]}/{tk[1]}"] = (len(xs), gm(xs))
    common[name] = d
out["common"] = common
# ---- cost columns (cuRace) ----
def an_s(r):
    m = re.search(r"analysis_s=([0-9.]+)", r["notes"]); return float(m.group(1)) if m else None
cost = collections.defaultdict(lambda: collections.defaultdict(list))
for k, r in runs.items():
    if k[1] != "cuvein" or k[2] not in (VC, SC, CO) or not ok(k): continue
    a = an_s(r)
    nat = r["wall"] / rat[k]
    for name, ps in SL:
        if meta[k[0]][0] in ps:
            cost[f"{name}|{k[2]}"]["run"].append(r["wall"] / nat)
            if a is not None:
                cost[f"{name}|{k[2]}"]["verdict"].append(max(a, 1e-3) / nat)
                cost[f"{name}|{k[2]}"]["e2e"].append((r["wall"] + a) / nat)
                cost[f"{name}|{k[2]}"]["run_on_analysed"].append(r["wall"] / nat)
out["cost"] = {k: {c: (len(v), gm(v)) for c, v in d.items()} for k, d in cost.items()}
# ---- per-key detail for the re-run rows and the TIMEOUT list ----
def detail(k):
    r = runs.get(k)
    if not r: return None
    nk = re.search(r"nkernels=(\d+)", r["notes"]); nd = re.search(r"node=([a-z0-9]+)", r["notes"]); cp = re.search(r"cap=(\d+)", r["notes"]) or re.search(r"timeout=(\d+)s", r["notes"])
    return dict(verdict=r["verdict"], reports=r["reports"], wall=r["wall"], native=r["native"], peak=r["peak"], ratio=rat.get(k),
                nkernels=int(nk.group(1)) if nk else None, node=nd.group(1) if nd else None, cap=cp.group(1) if cp else None,
                analysis_s=an_s(r), notes=r["notes"][:300])
out["detail"] = {"|".join(k): detail(k) for k in NEW}
tos = []
for k, r in runs.items():
    if r["verdict"] == "TIMEOUT": tos.append(("|".join(k), detail(k)))
out["timeouts"] = tos
out["verdict_counts"] = {f"{t}/{m}": dict(collections.Counter(r["verdict"] for k, r in runs.items() if k[1:] == (t, m))) for t, m in TK}
json.dump(out, open(OUTJ, "w"), indent=1, default=str)
print("ok", OUTJ, len(runs))
