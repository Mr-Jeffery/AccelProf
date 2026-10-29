#!/usr/bin/env python3
"""C2: builds eval/results/realworld_co/{perf.csv,tables.md} and eval/COLLECTOR_ONLY_REALWORLD.csv from the scored CSVs.
Reads: realworld_co*/recall.csv (collector-only), the T21b/T21c recall.csv (scalar-clock, vector-clock), the per-id baselines CSVs
(wall, native wall, peak RSS), other_reports.csv (both), co_only*.csv (co_diff.py)."""
import csv, collections, glob, json, os
W = "/home/fzheng4/wt-co-rw"
B = "/home/fzheng4/wt-t21b/eval/results/realworld"
C = "/home/fzheng4/wt-t21c/eval/results/realworld_t21c"
rd = lambda p: list(csv.DictReader(open(p))) if os.path.exists(p) else []
out = []
P = out.append

co_r, co_c = rd(f"{W}/eval/results/realworld_co/recall.csv"), rd(f"{W}/eval/results/realworld_co_t21c/recall.csv")
sc_r, sc_c = rd(f"{B}/recall.csv"), rd(f"{C}/recall.csv")


def idx(rows, mode):
    return {(r["target"], r["variant"], r["component"], r.get("id", "")) : r for r in rows if r["mode"] == mode}


def short(o):
    return o.replace("DETECTED-AS-DR", "DET-as-DR").replace("RESIDUAL-AS-EXPECTED", "RESIDUAL").replace("CLEAN-FOR-PAIR", "CLEAN").replace("STILL-REPORTED", "STILL").replace(" (family)", "(fam)")


# ---- 1. recall set
P("## 1. Recall set (T21b: 28 targets, buggy and fixed builds)\n")
P("Outcome per target and component, collector-only (CO) next to scalar-clock (SC) and vector-clock (VC) from the T21b run (`eval/results/realworld/recall.csv`, same oracle pairs `recall_pairs.json`). "
  "DET-as-DR = detected as the other class; RESIDUAL = residual as registered; STILL = pair still reported on the fixed build; NOT-SCORED = the run ended ERROR (see 5).\n")
co_i, sc_i, vc_i = idx(co_r, "collector-only"), idx(sc_r, "scalar-clock"), idx(sc_r, "vector-clock")
keys = sorted({k[:3] for k in co_i}, key=lambda k: (k[0], k[1] != "buggy", k[2]))
P("| target | variant | comp | CO | SC | VC | CO n_race/n_sc | CO run |")
P("|---|---|---|---|---|---|---|---|")
tot = collections.Counter()
for k in keys:
    c = next(v for kk, v in co_i.items() if kk[:3] == k)
    s = next((v for kk, v in sc_i.items() if kk[:3] == k), {})
    v = next((v for kk, v in vc_i.items() if kk[:3] == k), {})
    oc = c["outcome"] if c["run_verdict"] in ("RACE", "CLEAN") else ("pending (re-analysis running)" if c["target"] == "amrex-1" else "NOT-SCORED")
    tot[(c["variant"], oc)] += 1
    P(f"| {k[0]} | {k[1]} | {k[2] or '-'} | {short(oc)} | {short(s.get('outcome', '-'))} | {short(v.get('outcome', '-'))} | {c['n_race']}/{c['n_sc']} | {c['run_verdict']} |")
P("")
for mode, idm, label in (("CO", co_i, "collector-only"), ("SC", sc_i, "scalar-clock"), ("VC", vc_i, "vector-clock")):
    cnt = collections.Counter()
    for kk, r in idm.items():
        oc = r["outcome"] if (mode != "CO" or r["run_verdict"] in ("RACE", "CLEAN")) else ("pending (re-analysis running)" if r["target"] == "amrex-1" else "NOT-SCORED")
        cnt[(r["variant"], oc)] += 1
    P(f"- {label}: " + "; ".join(f"{v} {o} ({n})" for (v, o), n in sorted(cnt.items())))
P("")

# ---- 2. candidates
P("## 2. Candidate set (T21c)\n")
P("| id | comp | expected | CO | CO class reported | SC (T21c) | CO n_race/n_sc |")
P("|---|---|---|---|---|---|---|")
sci = {(r["id"], r["component"]): r for r in sc_c if r["mode"] == "scalar-clock"}
for c in co_c:
    s = sci.get((c["id"], c["component"]), {})
    oc = c["outcome"] if c["run_verdict"] in ("RACE", "CLEAN") else "NOT-SCORED"
    P(f"| {c['id']} | {c['component']} | {c['expected_class']} | {short(oc)} | {c['n_race']} RACE / {c['n_sc']} SC | {short(s.get('outcome', '-'))} | {c['n_race']}/{c['n_sc']} |")
for i in ("colmap-new-1-buggy", "lightgbm-new-1-buggy", "lightgbm-new-2-buggy", "llamacpp-open-2-buggy", "llamacpp-open-2-fixed"):
    if not any(c["id"] == i for c in co_c):
        why = {"lightgbm-new-1-buggy": "not run: analysis did not finish in 23 h under scalar-clock (Jeffery's decision)",
               "lightgbm-new-2-buggy": "not run: analysis did not finish in 23 h under scalar-clock (Jeffery's decision)",
               "llamacpp-open-2-buggy": "not run: deprioritised (Jeffery)", "llamacpp-open-2-fixed": "not run: deprioritised (Jeffery)"}.get(i, "see 5")
        P(f"| {i} | | | not scored | | {short(next((s['outcome'] for s in sc_c if s['id'] == i and s['mode'] == 'scalar-clock'), '-'))} | {why} |")
P("")

# ---- 3. other reports and CO-only
P("## 3. Reports on the buggy builds\n")
oth = {}
for lab, p in (("CO", f"{W}/eval/results/realworld_co/other_reports.csv"), ("CO", f"{W}/eval/results/realworld_co_t21c/other_reports.csv"),
               ("SC", f"{B}/other_reports.csv"), ("SC", f"{C}/other_reports.csv")):
    for r in rd(p):
        if r["variant"] == "buggy" and (r["mode"] == "collector-only" if lab == "CO" else r["mode"] == "scalar-clock"):
            oth[(lab, r["target"], r.get("id", ""))] = oth.get((lab, r["target"], r.get("id", "")), 0) + 1
targets = sorted({(k[1]) for k in oth})
P("Other reports = reports no oracle pair, registered residual or both-builds pair explains (the scorer's `other_reports.csv`, deduplicated pc pairs), buggy builds.\n")
P("| target | CO other | SC other |")
P("|---|---|---|")
tco = tsc = 0
for t in targets:
    a = sum(v for k, v in oth.items() if k[0] == "CO" and k[1] == t)
    b = sum(v for k, v in oth.items() if k[0] == "SC" and k[1] == t)
    tco += a
    tsc += b
    P(f"| {t} | {a} | {b} |")
P(f"| **total** | **{tco}** | **{tsc}** |\n")

dif = rd(f"{W}/eval/results/realworld_co/co_only.csv") + rd(f"{W}/eval/results/realworld_co_t21c/co_only.csv")
summ = []
for p in (f"{W}/eval/results/realworld_co/co_only_summary.json", f"{W}/eval/results/realworld_co_t21c/co_only_summary.json"):
    if os.path.exists(p):
        summ += json.load(open(p))
P("### Reports collector-only makes and scalar-clock does not (same target, buggy build)\n")
P("Key = (kernel, unordered pc pair, space), over all reports of both modes (RACE and SC verdicts), attributed runs only.\n")
P("| id | CO reports | SC reports | both | CO only | SC only | note |")
P("|---|---|---|---|---|---|---|")
for s in summ:
    P(f"| {s['id']} | {s.get('n_co', '')} | {s.get('n_sc', '')} | {s.get('n_both', '')} | {s.get('n_co_only', '')} | {s.get('n_sc_only', '')} | {s.get('note', '')} |")
P("")
P(f"CO-only reports: {len(dif)}.\n")
sh_order = ["loop around the barrier", "warp barrier between", "exit before the barrier", "barrier on one branch", "other"]
P("Shape between the two pcs (definitions in `harness/co_diff.py`) against the scalar-clock verdict for the same pair (read from the scalar-clock kernel JSONs of the same kernel):\n")
P("| shape | CO-only reports | SC: ORDERED (barrier-ordered) | SC: ORDERED (other) | SC: RACE/SC | SC: no verdict for the pair |")
P("|---|---|---|---|---|---|")
for sh in sh_order:
    rs = [r for r in dif if r["shape"] == sh]
    bo = sum(1 for r in rs if r["sc_verdict"] == "ORDERED" and r["sc_hb_class"] == "barrier-ordered")
    oo = sum(1 for r in rs if r["sc_verdict"] == "ORDERED" and r["sc_hb_class"] != "barrier-ordered")
    rc = sum(1 for r in rs if r["sc_verdict"] in ("RACE", "SC"))
    no = sum(1 for r in rs if r["sc_verdict"] in ("none", ""))
    P(f"| {sh} | {len(rs)} | {bo} | {oo} | {rc} | {no} |")
P(f"| **total** | **{len(dif)}** | {sum(1 for r in dif if r['sc_verdict'] == 'ORDERED' and r['sc_hb_class'] == 'barrier-ordered')} | "
  f"{sum(1 for r in dif if r['sc_verdict'] == 'ORDERED' and r['sc_hb_class'] != 'barrier-ordered')} | {sum(1 for r in dif if r['sc_verdict'] in ('RACE', 'SC'))} | {sum(1 for r in dif if r['sc_verdict'] in ('none', ''))} |\n")
P("Per target:\n")
P("| id | CO-only | " + " | ".join(sh_order) + " | SC barrier-ordered |")
P("|---|---|" + "---|" * (len(sh_order) + 1))
by = collections.defaultdict(list)
for r in dif:
    by[r["id"]].append(r)
for i, rs in sorted(by.items()):
    P(f"| {i} | {len(rs)} | " + " | ".join(str(sum(1 for r in rs if r['shape'] == sh)) for sh in sh_order) +
      f" | {sum(1 for r in rs if r['sc_verdict'] == 'ORDERED' and r['sc_hb_class'] == 'barrier-ordered')} |")
P("")

# ---- 4. perf
P("## 4. Slowdown and peak RSS (one rep per id; slowdown = tool wall / native wall)\n")
perf = []
def perf_rows(resdir, mode, tag):
    d = {}
    for p in glob.glob(f"{resdir}/baselines-cuvein-shard*-all.csv"):
        if "shardrean-" in p:
            continue
        for r in csv.DictReader(open(p)):
            if r["mode"] == mode:
                d[r["id"]] = r
    return d
co_p = {**perf_rows(f"{W}/eval/results/realworld_co", "collector-only", "co"), **perf_rows(f"{W}/eval/results/realworld_co_t21c", "collector-only", "co")}
sc_p = {**perf_rows(B, "scalar-clock", "sc"), **perf_rows(C, "scalar-clock", "sc")}
vc_p = perf_rows(B, "vector-clock", "vc")
def sd(r, k):
    try:
        return float(r[k])
    except (KeyError, ValueError, TypeError):
        return None
P("| id | CO verdict | CO wall s | native s | CO slowdown | CO peak MB | SC slowdown | SC peak MB | VC slowdown | VC peak MB |")
P("|---|---|---|---|---|---|---|---|---|---|")
f1 = lambda x: "" if x is None else f"{x:.1f}"
for i in sorted(co_p):
    c = co_p[i]
    s, v = sc_p.get(i, {}), vc_p.get(i, {})
    def sl(r):
        w, n = sd(r, "wall_s"), sd(r, "native_wall_s")
        return (w / n) if (w is not None and n) else None
    row = dict(id=i, co_verdict=c["verdict"], co_wall_s=sd(c, "wall_s"), native_wall_s=sd(c, "native_wall_s"), co_slowdown=sl(c), co_peak_mb=sd(c, "peak_mb"),
               sc_verdict=s.get("verdict", ""), sc_wall_s=sd(s, "wall_s"), sc_slowdown=sl(s), sc_peak_mb=sd(s, "peak_mb"),
               vc_verdict=v.get("verdict", ""), vc_wall_s=sd(v, "wall_s"), vc_slowdown=sl(v), vc_peak_mb=sd(v, "peak_mb"))
    perf.append(row)
    P(f"| {i} | {c['verdict']} | {f1(row['co_wall_s'])} | {f1(row['native_wall_s'])} | {f1(row['co_slowdown'])} | {f1(row['co_peak_mb'])} | {f1(row['sc_slowdown'])} | {f1(row['sc_peak_mb'])} | {f1(row['vc_slowdown'])} | {f1(row['vc_peak_mb'])} |")
with open(f"{W}/eval/results/realworld_co/perf.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(perf[0]))
    w.writeheader()
    w.writerows(perf)
import statistics as st
okc = [r["co_slowdown"] for r in perf if r["co_slowdown"] is not None and r["co_verdict"] in ("RACE", "CLEAN")]
oks = [r["sc_slowdown"] for r in perf if r["sc_slowdown"] is not None and r["sc_verdict"] in ("RACE", "CLEAN") and r["co_verdict"] in ("RACE", "CLEAN")]
P(f"\nMedian slowdown over the {len(okc)} CO runs that ended RACE/CLEAN: {st.median(okc):.1f}x (min {min(okc):.1f}x, max {max(okc):.1f}x); "
  f"median SC slowdown over the {len(oks)} ids where both ended RACE/CLEAN: {st.median(oks):.1f}x.\n" if okc and oks else "\n")

# ---- combined CSV in recall.csv format
rows = co_r + co_c
for r in rows:
    if r["target"] == "amrex-1" and r["run_verdict"] not in ("RACE", "CLEAN"):
        r["outcome"] = "pending (re-analysis running)"
        r["miss_cause"] = "analysis timeout at 3,600 s; long re-analysis (jobs 322934/322935) running"
cols = ["id"] + [c for c in co_r[0].keys() if c != "id"]
with open(f"{W}/eval/COLLECTOR_ONLY_REALWORLD.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
open(f"{W}/eval/results/realworld_co/tables.md", "w").write("\n".join(out) + "\n")
print("\n".join(out)[:200000])
