#!/usr/bin/env python3
"""X12: Table 3 (tab:eval-accuracy) collector-only column recomputed from the N=16 verdicts (C6 --chain-closure), per suite, next to the
rows it is compared with (C6's chain-closure rows on eval/co-chain, i.e. the paper's current collector-only cells). Races alone,
Indigo 1.3 per code, labels as the paper (knn and atomicCAS scored race-free by evaluation.tex).
  x12_table3.py MAKE_TABLES_DIR C6_CSV OUT.md  SUITE=CSV[,CSV...] ...      (SUITE in P1 PI P4 P6 P9)"""
import collections, csv, glob, os, sys
csv.field_size_limit(1 << 30)
mtdir, c6csv, out = sys.argv[1:4]
spec = dict(a.split("=", 1) for a in sys.argv[4:])
sys.argv = [sys.argv[0], "--collector-only"]
sys.path.insert(0, mtdir)
import make_tables as mt
man = mt.load_manifest()
OOS = ("asyncmemcpy/", "hostdevice/", "interkernel/")
OVR = {}   # SC artifact_subset.json: atomicCAS, dxtc2, knn, tridiagonal, expdist racy; overlap, fpc, gpp, crs, mr race-free = manifest labels
def label(i): return OVR.get(i, man.get(i, {}).get("label", ""))
def load(paths):
    runs, meta = mt.load_runs(paths=paths, shards=True)
    return {i: r for (i, t, m), r in runs.items() if t == "cuvein" and m == mt.CO or m == "collector-only"}, meta
def pos(r):
    v = mt.race_alone_verdict(r); v = r["verdict"] if v is None else v
    return v == "RACE"
SUITES = [("Indigo3", lambda m: m[0] == "P1"), ("Indigo 1.3 (per code)", lambda m: m[0] == "PI"),
          ("Indigo 1.3, SC's 99 (per code)", lambda m: mt._in(m, ("PI@sc",))),
          ("ScoR applications", lambda m: m[0] == "P4"),
          ("cuHadron (in scope)", lambda m: m[0] == "P6" and not m[1].startswith(OOS)),
          ("HeCBench, 10 (SC's 8 + knn + atomicCAS)", lambda m: m[0] == "P9")]
def cells(runs, meta, pred, percode):
    c = dict(tp=0, pos=0, fp=0, neg=0, to=0, err=0, unl=0)
    if percode:   # a code is reported when any of its inputs is RACE; labels per code (all inputs share it)
        codes = collections.defaultdict(list)
        for i, m in meta.items():
            if pred(m) and i in runs: codes[(m[1], m[2])].append(i)
        for _, ids in codes.items():
            vs = [runs[i]["verdict"] for i in ids]
            if all(v in ("ERROR",) for v in vs): c["err"] += 1; continue
            if all(v == "TIMEOUT" for v in vs): c["to"] += 1; continue
            lab = label(ids[0]); p = any(pos(runs[i]) for i in ids)
            if lab == "RACE": c["pos"] += 1; c["tp"] += p
            elif lab == "CLEAN": c["neg"] += 1; c["fp"] += p
            else: c["unl"] += 1
        return c
    for i, m in meta.items():
        if not pred(m) or i not in runs: continue
        r = runs[i]; v = r["verdict"]
        if v == "TIMEOUT": c["to"] += 1; continue
        if v == "ERROR": c["err"] += 1; continue
        lab = label(i)
        if lab == "RACE": c["pos"] += 1; c["tp"] += pos(r)
        elif lab == "CLEAN": c["neg"] += 1; c["fp"] += pos(r)
        else: c["unl"] += 1
    return c
def fmt(c):
    a = f"{c['tp']:,}/{c['pos']:,}" if c["pos"] else "—"; b = f"{c['fp']:,}/{c['neg']:,}" if c["neg"] else "—"
    return f"{a} · {b}" + (f"; {c['err']} ERR" if c["err"] else "") + (f"; {c['to']} TO" if c["to"] else "")
new = {}; newmeta = {}
for s, files in spec.items():
    paths = []
    for f in files.split(","): paths += glob.glob(f)
    r, m = mt.load_runs(paths=paths, shards=True)
    import re as _re
    ren = lambda i: _re.sub(r"^X11-(.+)$", r"P9-\1-cuda", i)   # SC-binary ids (X11-<app>) = manifest P9-<app>-cuda
    for (i, t, mode), v in r.items(): new[ren(i)] = v
    newmeta.update({ren(i): v for i, v in m.items()})
c6r, c6m = mt.load_runs(paths=[c6csv], shards=True)
for _i in list(new):
    if _i not in newmeta and _i in c6m: newmeta[_i] = c6m[_i]
c6 = {i: v for (i, t, mode), v in c6r.items()}
ids_new = set(new)
lines = ["| suite | N=16 (this sweep) | C6 `-n 1` rows (the paper's current collector-only cell) | ids in N=16 / in C6 |", "|---|---|---|---|"]
for name, pred in SUITES:
    percode = "per code" in name
    sub = {i for i, m in newmeta.items() if pred(m)}
    if not sub: continue
    cn = cells(new, {i: newmeta[i] for i in sub}, pred, percode)
    cm = {i: m for i, m in c6m.items() if pred(m) and (i in sub or True)}
    if name.startswith("HeCBench"):   # also the SC's-8 view the paper's row uses
        pass
    cc = cells(c6, {i: c6m[i] for i in c6m if pred(c6m[i]) and i in sub}, pred, percode)   # same ids
    cca = cells(c6, {i: c6m[i] for i in c6m if pred(c6m[i])}, pred, percode)                # all of C6's ids of the suite
    lines.append(f"| {name} | **{fmt(cn)}** | {fmt(cc)}" + (f" (C6, all its ids of the suite: {fmt(cca)})" if cca != cc else "") + f" | {len(sub)} / {sum(1 for i in c6m if pred(c6m[i]))} |")
    if name.startswith("HeCBench"):
        eight = lambda m: m[0] == "P9" and m[1] not in ("knn-cuda", "atomicCAS-cuda")
        s8 = {i for i in sub if eight(newmeta[i])}
        cn8 = cells(new, {i: newmeta[i] for i in s8}, eight, False); cc8 = cells(c6, {i: c6m[i] for i in c6m if i in s8}, eight, False)
        lines.append(f"| HeCBench, SC's 8 (Table 3's row; without knn, atomicCAS) | **{fmt(cn8)}** | {fmt(cc8)} | {len(s8)} / {len(s8)} |")
if os.environ.get("X11CSV"):
    xp = []
    for f in os.environ["X11CSV"].split(","): xp += glob.glob(f)
    xr, xm = mt.load_runs(paths=xp, shards=True)
    import re as _re2
    ren2 = lambda i: _re2.sub(r"^X11-(.+)$", r"P9-\1-cuda", i)
    xx = {ren2(i): v for (i, t, mode), v in xr.items()}
    xmeta = {ren2(i): v for i, v in xm.items()}
    for k in xx:
        if k not in xmeta and k in c6m: xmeta[k] = c6m[k]
    p9 = lambda m: m[0] == "P9"
    cx = cells(xx, {i: xmeta[i] for i in xx if i in xmeta}, p9, False)
    lines.append(f"| HeCBench, 10, X11 `-n 1` rows (SC binaries; reference for the 6 apps whose build differs from C1's) | | {fmt(cx)} | {len(xx)} |")
open(out, "w").write("\n".join(lines) + "\n"); print("\n".join(lines))
