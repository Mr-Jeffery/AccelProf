#!/usr/bin/env python3
"""X7 Part B3: merge the cap=84600 rows into the final CSVs (X1b's rule, FINAL_SWEEP_B.md 1 (i)).
Run from the worktree root. Writes eval/results/cap-84600/{baselines-cuvein.csv,baselines-cuvein-co.csv,
baselines-iguard.csv,baselines-sanitizer.csv,dropped.txt,merge_log.txt} and old-inputs/baselines-iguard.csv
(= the branch's iGUARD CSV + the P7 job-321654 rows, the 'old' state)."""
import csv, glob, os, re, subprocess, collections, sys
R = "eval/results"; OUT = f"{R}/cap-84600"; OLD = f"{OUT}/old-inputs"
os.makedirs(OLD, exist_ok=True)
PARTA = "ea98fef"
A5 = "/home/fzheng4/wt-x7a/eval/results/verdict-timing"
COLS = ["id","pset","program","build","input","tool","mode","rep","verdict","reports_dedup","report_ids","report_lines","wall_s","native_wall_s","peak_mb","rc","notes"]
log = []
def L(*a):
    s = " ".join(str(x) for x in a); log.append(s); print(s)
def rd(p): return list(csv.DictReader(open(p, newline="")))
def wr(p, rows):
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in COLS})
dropped = []; APPLIED = []
def key(r): return (r["id"], r.get("tool", ""), r.get("mode", ""))
def apply(base, new_rows, what, tool_filter=None):
    """replace all rows of each (id, tool, mode) in new_rows (grouped) when verdicts are all RACE/CLEAN/TIMEOUT"""
    grp = collections.OrderedDict()
    for r in new_rows: grp.setdefault(key(r), []).append(r)
    out = list(base)
    for k, rs in grp.items():
        v = {r["verdict"] for r in rs}
        old = [r for r in out if key(r) == k]
        if not v <= {"RACE", "CLEAN", "TIMEOUT"}:
            reason = "; ".join(sorted({r["notes"] for r in rs}))
            peak = max([float(r["peak_mb"]) for r in rs if r.get("peak_mb")] or [0])
            dropped.append(f"{k[0]} {k[1]} {k[2] or '-'}: new verdict {sorted(v)} wall {rs[0]['wall_s']} s peak_mb {rs[0].get('peak_mb') or 'missing'} rc {rs[0]['rc']} notes[{reason}]; old rows kept ({len(old)})")
            L(f"{what}: {k} NOT merged (ERROR); {len(old)} old rows stay")
            continue
        out = [r for r in out if key(r) != k]
        out.extend(rs); APPLIED.append(k)
        L(f"{what}: {k}: {len(old)} old rows ({','.join(sorted({r['verdict'] for r in old})) or 'none'}) -> {len(rs)} new ({','.join(sorted(v))})")
    return out
def tag(rows, note):
    for r in rows: r["notes"] = (r.get("notes", "") + (";" if r.get("notes") else "") + note)
    return rows

# ---- iGUARD / racecheck ----
ig_old = rd(f"{R}/baselines-iguard.csv")
p7sh = subprocess.run("for k in 0 1 2 3; do git show eval/iguard-p7:eval/results/baselines-iguard-shardp7_${k}_4.csv | tail -n +2; done", shell=True, capture_output=True, text=True, executable="/bin/bash").stdout
hdr = open(f"{R}/baselines-iguard.csv").readline()
import io
p7rows = list(csv.DictReader(io.StringIO(hdr + p7sh)))
L("old iGUARD P7 rows (job 321654):", len(p7rows), collections.Counter((r["id"], r["verdict"]) for r in p7rows if r["verdict"] == "TIMEOUT"))
assert not any(r["id"].startswith("P7-") for r in ig_old)
ig_oldfull = ig_old + p7rows
wr(f"{OLD}/baselines-iguard.csv", ig_oldfull)
ig_new = list(ig_oldfull)
long_rows = []
for f in sorted(glob.glob(f"{R}/iguard-p7long/baselines-iguard-p7long-*.csv")):
    if "haversine" in f: continue          # replaced by the 84,600 s row below
    long_rows += tag(rd(f), "pass=p7long;cap=5400;from=eval/iguard-p7 e90dba0")
ig_new = apply(ig_new, long_rows, "iguard p7long")
cap_rows = []
for f in sorted(glob.glob(f"{R}/cap84600/iguard-*.csv")): cap_rows += rd(f)
ig_new = apply(ig_new, cap_rows, "iguard cap84600")
wr(f"{OUT}/baselines-iguard.csv", ig_new)
sa_old = rd(f"{R}/baselines-sanitizer.csv")
sa_new = list(sa_old)
cap_rows = []
for f in sorted(glob.glob(f"{R}/cap84600/racecheck-*.csv")): cap_rows += [r for r in rd(f)]
L("racecheck cap84600 files:", [(r['id'], r['tool'], r['verdict'], r['wall_s']) for r in cap_rows])
sa_new = apply(sa_new, cap_rows, "racecheck cap84600")
wr(f"{OUT}/baselines-sanitizer.csv", sa_new)

# ---- cuVein ----
def a5map(path):
    m = {}
    for r in rd(path):
        mm = {t.split("=")[0]: t.split("=")[1] for t in r["notes"].split(";") if t.startswith(("analysis_s=", "analysis_workers=", "analysis_kjsons="))}
        if mm: m[(r["id"], r["mode"], r["rep"])] = mm
    return m
def fold(rows, a5):
    n = miss = 0
    for r in rows:
        if r.get("tool") != "cuvein" or "analysis_s=" in r["notes"]: continue
        if "x7b-new" in r["notes"]: continue   # new rows: not in A5
        mm = a5.get((r["id"], r["mode"], r["rep"]))
        if mm:
            r["notes"] += ";analysis_s=%s;analysis_workers=%s;analysis_kjsons=%s;analysis_code=partA-%s" % (mm["analysis_s"], mm.get("analysis_workers", ""), mm.get("analysis_kjsons", ""), PARTA); n += 1
        else: miss += 1
    return n, miss
vc = rd(f"{R}/final-b/merged/baselines-cuvein.csv")
vc_new = list(vc)
hav = tag(rd(f"{R}/final-b-24h-vc/baselines-cuvein-shardcap84600-vc-haversine0_1.csv"), "x7b-new")
ha = rd(f"{R}/cap84600/vc-haversine-analysis/baselines-cuvein-shardx7b-havall.csv")[0]
assert ha["verdict"] == hav[0]["verdict"]
tag(hav, ";".join(t for t in ha["notes"].split(";") if t.startswith(("analysis_s=", "analysis_workers=", "analysis_kjsons="))) + ";analysis_code=partA-" + PARTA)
vc_new = apply(vc_new, hav, "cuvein vc haversine")
pf_old = [r for r in vc if r["id"] == "P7-particlefilter-cuda" and r["mode"] == "vector-clock"]
pf = dict(pf_old[0]); pf.update(rep="1", verdict="TIMEOUT", reports_dedup="0", report_ids="", report_lines="", wall_s="", peak_mb="185300", rc="",
    notes="x7b-new;cap=84600;not run at cap=84600; memory (>=185.3 GB at ~5,320 s on a 202 GB host);peak_mb from X1 (c64, killed at 185.3 GB after 5,313-5,331 s);Jeffery 2026-10-30 rule: called TO without running")
vc_new = apply(vc_new, [pf], "cuvein vc particlefilter")
a5vc = a5map(f"{A5}/final-b-merged/baselines-cuvein.csv")
L("fold vc/sc: (folded, missing) =", fold(vc_new, a5vc))
wr(f"{OUT}/baselines-cuvein.csv", vc_new)
co = rd(f"{R}/collector-only/merged/baselines-cuvein.csv")
co_new_rows = rd(f"{R}/cap84600/co-atomicCAS/final-2026-11-co/baselines-cuvein-shardx7b-acasall.csv")
co_new_rows = tag(co_new_rows, "analysis-cap=84600s;reanalysis=PartA-%s" % PARTA)
co_new = apply(list(co), co_new_rows, "cuvein co atomicCAS")
L("fold co: (folded, missing) =", fold(co_new, a5map(f"{A5}/collector-only-merged/baselines-cuvein.csv")))
wr(f"{OUT}/baselines-cuvein-co.csv", co_new)
open(f"{OUT}/dropped.txt", "w").write("\n".join(dropped) + ("\n" if dropped else ""))
open(f"{OUT}/merge_log.txt", "w").write("\n".join(log) + "\n")
import json
json.dump(sorted(APPLIED), open(f"{OUT}/newkeys.json", "w"))
