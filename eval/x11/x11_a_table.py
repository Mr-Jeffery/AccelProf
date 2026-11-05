#!/usr/bin/env python3
"""X11 stage A table: verdict old -> new, native old -> new, collector slowdown old -> new, 10 HeCBench apps,
plus the control check (overlap, fpc, gpp, crs: new verdict must equal the old collector-only rows).
  python x11_a_table.py LOGDIR COCHAIN_WT OUT.md"""
import csv, glob, statistics, sys
L, W, OUT = sys.argv[1:4]
APPS = ["atomicCAS", "dxtc2", "knn", "tridiagonal", "expdist", "overlap", "fpc", "gpp", "crs", "mr"]
SAME = ["overlap", "fpc", "gpp", "crs"]

def rows(path):
    return list(csv.DictReader(open(path, newline="")))

def verdict(rs):
    v = [r["verdict"] for r in rs]
    if "RACE" in v: return "RACE"
    if v and all(x == "CLEAN" for x in v): return "CLEAN"
    return "TO" if "TIMEOUT" in v else "ERR"

old_chain = rows(f"{W}/eval/results/co-chain/merged/baselines-cuvein.csv")
old_co = rows(f"{W}/eval/results/collector-only/merged/baselines-cuvein.csv")
def old(rs, app):
    return [r for r in rs if r["id"] == f"P9-{app}-cuda" and r["mode"] == "collector-only"]
new_co, new_ch = {}, {}
for n in (1, 2, 3):
    for f in glob.glob(f"{L}/stageA-x11-co-r{n}/baselines-cuvein-shard*.csv"):
        for r in rows(f): new_co.setdefault(r["id"], []).append(r)
    for f in glob.glob(f"{L}/stageA-chain-r{n}/baselines-cuvein-shard*.csv"):
        for r in rows(f): new_ch.setdefault(r["id"], []).append(r)
nat = {r["id"]: r for r in rows(f"{L}/stageA-native.csv")}
fmt = lambda a, b: a if a == b else f"{a} → {b}"
out = ["| program | verdict (old → new) | native s (old → new) | collector slowdown (old → new) | new runs: verdict / wall s |", "|---|---|---|---|---|"]
mism = []
for app in APPS:
    oc, oo = old(old_chain, app), old(old_co, app)
    nc, nn = new_ch.get(f"X11-{app}", []), new_co.get(f"X11-{app}", [])
    ov, nv = verdict(oc), (verdict(nc) if nc else "missing")
    onat = oc[0]["native_wall_s"] if oc else "missing"
    nnat = nat[f"X11-{app}"]["median_s"] if f"X11-{app}" in nat else "missing"
    def slow(rs, n):
        try: return f"{statistics.median(float(r['wall_s']) for r in rs) / float(n):.1f}"
        except Exception: return "missing"
    osl, nsl = slow(oc, onat), slow(nn, nnat)
    walls = "; ".join(f"{r['verdict']}/{r['wall_s']}" for r in nn)
    out.append(f"| {app} | {fmt(ov, nv)} | {fmt(onat, nnat)} | {fmt(osl + 'x', nsl + 'x')} | co: {walls} |")
    if app in SAME:
        ocv = verdict(oo)
        info = f"{app}: old CO {ocv} ({oo[0]['reports_dedup']} rep), old CO+chain {ov} ({oc[0]['reports_dedup']} rep), new CO {verdict(nn) if nn else 'missing'} ({','.join(r['reports_dedup'] for r in nn)} rep), new CO+chain {nv} ({','.join(r['reports_dedup'] for r in nc)} rep)"
        if nv != ov or nv != ocv: mism.append("MISMATCH " + info)
        else: mism.append("equal " + info)
open(OUT, "w").write("\n".join(out) + "\n\nControl (SAME apps):\n" + "\n".join(mism) + "\n")
print(open(OUT).read())
