#!/usr/bin/env python3
"""X11 control gate. For the 4 SAME applications (overlap, fpc, gpp, crs): compare the new collector-only verdicts
(plain collector-only rows and the chain-closure verdict of origin/eval/co-chain) with the old collector-only rows.
Exit 0 = all equal, 1 = at least one verdict differs, 2 = incomplete (a run produced no verdict).
  python x11_gate.py LOGDIR COCHAIN_WT OUT.txt"""
import csv, glob, sys
L, W, OUT = sys.argv[1:4]
APPS = ["overlap", "fpc", "gpp", "crs"]
def rows(p): return list(csv.DictReader(open(p, newline="")))
def verdict(rs):
    v = [r["verdict"] for r in rs]
    if not v: return "missing"
    if "RACE" in v: return "RACE"
    if all(x == "CLEAN" for x in v): return "CLEAN"
    return "TO" if "TIMEOUT" in v else "ERR"
oc = rows(f"{W}/eval/results/co-chain/merged/baselines-cuvein.csv")
oo = rows(f"{W}/eval/results/collector-only/merged/baselines-cuvein.csv")
old = lambda rs, a: [r for r in rs if r["id"] == f"P9-{a}-cuda" and r["mode"] == "collector-only"]
status, lines = 0, []
for a in APPS:
    co, ch = [], []
    for n in (1, 2, 3):
        for f in glob.glob(f"{L}/stageA-x11-co-r{n}-{a}/baselines-cuvein-shard*.csv"): co += rows(f)
        for f in glob.glob(f"{L}/stageA-chain-r{n}-{a}/baselines-cuvein-shard*.csv"): ch += rows(f)
    ncv, nhv, ocv, ohv = verdict(co), verdict(ch), verdict(old(oo, a)), verdict(old(oc, a))
    n_ok = (len(co), len(ch))
    if "missing" in (ncv, nhv) or n_ok != (3, 3):
        st = "INCOMPLETE"; status = max(status, 2) if status != 1 else 1
    elif ncv != ocv or nhv != ohv:
        st = "MISMATCH"; status = 1
    else:
        st = "equal"
    lines.append(f"{st} {a}: old CO {ocv} / old CO+chain {ohv} / new CO {ncv} ({','.join(r['verdict'] for r in co)}; reports {','.join(r['reports_dedup'] for r in co)}) / new CO+chain {nhv} ({','.join(r['verdict'] for r in ch)}; reports {','.join(r['reports_dedup'] for r in ch)}) old reports CO {old(oo,a)[0]['reports_dedup']} chain {old(oc,a)[0]['reports_dedup']}")
open(OUT, "w").write("\n".join(lines) + f"\nstatus={status}\n")
print("\n".join(lines)); sys.exit(status)
