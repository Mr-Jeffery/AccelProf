#!/usr/bin/env python3
"""C3 items 1,2,3,5,7,8: collector-only column of the paper's accuracy / union / countings / litmus / slowdown /
memory / no-verdict tables, and the program-level comparison against X1b's scalar-clock run.
Every number is a function of two CSVs: X1b's merged file (vector-clock, scalar-clock) and C1's merged file
(collector-only).  Run from the worktree root."""
import sys, os, csv, re, math, statistics, subprocess, collections
sys.argv = [sys.argv[0], "--collector-only"]
# make_tables is loaded from the sandbox tree of p_co_tables.sh (its eval/results holds X1b's merged file, C1's merged
# file as baselines-cuvein-co.csv and every other tool's CSVs), so _ratios sees the same native walls as BASELINES.md.
SB = os.environ.get("COSB", "/home/fzheng4/co-tables-sandbox-b")
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt
R = "eval/results"
OUT = f"{R}/collector-only-tables"
os.makedirs(OUT, exist_ok=True)
X1B = f"{R}/final-b/merged/baselines-cuvein.csv"
C1 = f"{R}/collector-only/merged/baselines-cuvein.csv"
runs, meta = mt.load_runs()
man = mt.load_manifest()
VC, SC, CO = mt.VC, mt.SC, mt.CO
MODES = (VC, SC, CO)
md = []
def P(*a): md.append(" ".join(str(x) for x in a))
def wcsv(name, header, rows):
    with open(f"{OUT}/{name}", "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

# ---- labels as in the paper's tables ----
# P9-knn-cuda is labelled racy in the manifest but race-free upstream; the paper's HeCBench cell (3 racy / 7 race-free)
# scores it race-free.  cuHadron "in scope" = 20 per-kernel inputs: asyncmemcpy, hostdevice and interkernel categories
# are outside the per-kernel model.
LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN"}
OUT_OF_SCOPE = ("asyncmemcpy/", "hostdevice/", "interkernel/")
def label(i):
    return LABEL_OVERRIDE.get(i, man[i].get("label", ""))
SUITES = [("Indigo3", lambda i, m: m[0] == "P1"),
          ("Indigo 1.3", lambda i, m: m[0] == "PI"),
          ("Indigo 1.3, SC's 99", lambda i, m: mt._in(m, ("PI@sc",))),
          ("ECL", lambda i, m: m[0] == "P3"),
          ("ScoR applications", lambda i, m: m[0] == "P4"),
          ("ScoR litmus + canary", lambda i, m: m[0] == "P5"),
          ("cuHadron (in scope)", lambda i, m: m[0] == "P6" and not m[1].startswith(OUT_OF_SCOPE)),
          ("HeCBench, SC's 10", lambda i, m: m[0] == "P9")]
AGG = ("Indigo3", "Indigo 1.3", "ECL", "ScoR applications", "cuHadron (in scope)")   # "All pre-registered"

def classes(r):
    return mt.report_classes(r) or {}
def has_strong(r):
    c = classes(r); return bool(c.get("sc") or c.get("latent-sc"))
def races_verdict(r):
    v = mt.race_alone_verdict(r)
    return r["verdict"] if v is None else v
def positive(kind, r):
    if kind == "races": return races_verdict(r) == "RACE"
    if kind == "strong": return has_strong(r)
    return races_verdict(r) == "RACE" or has_strong(r)

def counts(mode, pred, kind):
    c = dict(tp=0, pos=0, fp=0, neg=0, to=0, err=0, unl=0)
    for i, m in meta.items():
        if not pred(i, m): continue
        r = runs.get((i, "cuvein", mode)) or runs.get((i, "cuvein", ""))
        if r is None: continue
        v = r["verdict"]
        if v == "TIMEOUT": c["to"] += 1; continue
        if v == "ERROR": c["err"] += 1; continue
        lab = label(i)
        if lab == "RACE": c["pos"] += 1; c["tp"] += positive(kind, r)
        elif lab == "CLEAN": c["neg"] += 1; c["fp"] += positive(kind, r)
        else: c["unl"] += 1
    return c
def fmt(c):
    a = f"{c['tp']:,}/{c['pos']:,}" if c["pos"] else "—"
    b = f"{c['fp']:,}/{c['neg']:,}" if c["neg"] else "—"
    extra = (f"; {c['to']} TO" if c["to"] else "") + (f"; {c['err']} ERR" if c["err"] else "")
    return f"{a} · {b}{extra}"

# the paper's own VC / SC cells (appendix_eval.tex, evaluation.tex at paper origin/HEAD faeef1c), for the check:
# (suite, counting) -> {mode: (tp, positives, fp, negatives, timeouts)}
EXP = {
 ("Indigo3","races"): {VC:(200,200,0,200,0), SC:(200,200,0,200,0)},
 ("Indigo 1.3","races"): {VC:(1714,1862,0,1260,0), SC:(1714,1862,0,1260,0)},
 ("Indigo 1.3, SC's 99","races"): {VC:(43,45,0,44,0), SC:(43,45,0,44,0)},
 ("ECL","races"): {VC:(0,0,16,60,0), SC:(0,0,16,60,0)},
 ("ScoR applications","races"): {VC:(14,14,2,14,0), SC:(14,14,2,14,0)},
 ("ScoR litmus + canary","races"): {VC:(4,19,1,14,0), SC:(3,19,0,14,0)},
 ("cuHadron (in scope)","races"): {VC:(6,6,0,14,0), SC:(6,6,0,14,0)},
 ("HeCBench, SC's 10","races"): {VC:(2,2,0,6,2), SC:(3,3,0,6,1)},
 ("Indigo3","strong"): {VC:(0,200,72,200,0), SC:(0,200,72,200,0)},
 ("Indigo 1.3","strong"): {VC:(0,1862,0,1260,0), SC:(0,1862,0,1260,0)},
 ("ECL","strong"): {VC:(0,0,36,60,0), SC:(0,0,32,60,0)},
 ("ScoR applications","strong"): {VC:(8,14,7,14,0), SC:(8,14,4,14,0)},
 ("ScoR litmus + canary","strong"): {VC:(17,19,4,14,0), SC:(17,19,0,14,0)},
 ("cuHadron (in scope)","strong"): {VC:(0,6,0,14,0), SC:(0,6,0,14,0)},
 ("HeCBench, SC's 10","strong"): {VC:(0,2,0,6,2), SC:(0,3,0,6,1)},
 ("Indigo3","union"): {VC:(200,200,72,200,0), SC:(200,200,72,200,0)},
 ("Indigo 1.3","union"): {VC:(1714,1862,0,1260,0), SC:(1714,1862,0,1260,0)},
 ("ECL","union"): {VC:(0,0,44,60,0), SC:(0,0,40,60,0)},
 ("ScoR applications","union"): {VC:(14,14,7,14,0), SC:(14,14,4,14,0)},
 ("ScoR litmus + canary","union"): {VC:(19,19,5,14,0), SC:(18,19,0,14,0)},
 ("cuHadron (in scope)","union"): {VC:(6,6,0,14,0), SC:(6,6,0,14,0)},
 ("HeCBench, SC's 10","union"): {VC:(2,2,0,6,2), SC:(3,3,0,6,1)},
}
EXP_AGG = {VC:(1934,2082,18,1548), SC:(1934,2082,18,1548)}
mism = []
def check(suite, kind, mode, c):
    e = EXP.get((suite, kind), {}).get(mode)
    if e is None: return
    got = (c["tp"], c["pos"], c["fp"], c["neg"], c["to"])
    if got != e: mism.append((suite, kind, mode, e, got))

rows61 = []
P("## Table 6.1 (tab:eval-accuracy): accuracy per suite, data races alone, third column added\n")
P("Cells: recall TP/(TP+FN) · false-positive rate FP/(FP+TN); TO = timed out, ERR = errored. Race-alone verdict = "
  "`race_alone_verdict` of `make_tables.py`. Collector-only: a conflicting reuse pair no certificate orders is Race (class `race`) or SC; no Latent.\n")
P("| suite | cuVein vector-clock | cuVein scalar-clock | cuVein collector-only |"); P("|---|---|---|---|")
def agg_counts(mode, kind):
    tot = collections.Counter()
    for name, pred in SUITES:
        if name in AGG:
            for k, v in counts(mode, pred, kind).items(): tot[k] += v
    return tot
for name, pred in SUITES:
    cs = {m: counts(m, pred, "races") for m in MODES}
    for m in MODES:
        check(name, "races", m, cs[m]); rows61.append((name, m, "races", *[cs[m][k] for k in ("tp","pos","fp","neg","to","err")]))
    P(f"| {name} | " + " | ".join(fmt(cs[m]) for m in MODES) + " |")
ag = {m: agg_counts(m, "races") for m in MODES}
for m in MODES: rows61.append(("All pre-registered", m, "races", *[ag[m][k] for k in ("tp","pos","fp","neg","to","err")]))
P("| **All pre-registered** | " + " | ".join(fmt(ag[m]) for m in MODES) + " |")
for m in (VC, SC):
    got = (ag[m]["tp"], ag[m]["pos"], ag[m]["fp"], ag[m]["neg"])
    if got != EXP_AGG[m]: mism.append(("All pre-registered", "races", m, EXP_AGG[m], got))
wcsv("table61_accuracy.csv", ["suite","mode","counting","tp","positives","fp","negatives","timeout","error"], rows61)

# ---- union and three countings ----
P("\n## tab:eval-accuracy-union and tab:eval-countings: the three countings, third mode added\n")
P("races = Race alone; strong = a program with an unordered strong conflict reported (class `sc`); union = Race or strong. "
  "Cells TP/(TP+FN) · FP/(FP+TN). The paper's vector-clock and scalar-clock cells are recomputed and compared (last section).\n")
P("| suite | VC races | VC strong | VC union | SC races | SC strong | SC union | CO races | CO strong | CO union |"); P("|---|---|---|---|---|---|---|---|---|---|")
rows_c = []
for name, pred in SUITES:
    if name == "Indigo 1.3, SC's 99": continue
    cells = []
    for m in MODES:
        for kind in ("races", "strong", "union"):
            c = counts(m, pred, kind); check(name, kind, m, c)
            rows_c.append((name, m, kind, *[c[k] for k in ("tp","pos","fp","neg","to","err")])); cells.append(fmt(c))
    P(f"| {name} | " + " | ".join(cells) + " |")
tot = {}
for m in MODES:
    for kind in ("races", "strong", "union"):
        a = agg_counts(m, kind); tot[(m, kind)] = a
        rows_c.append(("All pre-registered", m, kind, *[a[k] for k in ("tp","pos","fp","neg","to","err")]))
P("| **All pre-registered** | " + " | ".join(fmt(tot[(m, k)]) for m in MODES for k in ("races","strong","union")) + " |")
wcsv("table_countings.csv", ["suite","mode","counting","tp","positives","fp","negatives","timeout","error"], rows_c)

# ---- litmus ----
P("\n## tab:eval-litmus: the 33 ScoR litmus kernels, third mode added\n")
P("Race = a data race is reported; Strong = only an unordered strong conflict is reported; — = nothing reported. "
  "`rtraw` counted as recorded (Race, a false report, footnote [^rtraw]).\n")
def lit(mode, i):
    r = runs.get((i, "cuvein", mode))
    if r is None: return "n/a"
    if r["verdict"] in ("TIMEOUT", "ERROR"): return r["verdict"]
    if races_verdict(r) == "RACE": return "Race"
    return "Strong" if has_strong(r) else "—"
p5 = sorted(i for i, m in meta.items() if m[0] == "P5")
lrows = []
P("| kernel | ScoR label | VC | SC | CO |"); P("|---|---|---|---|---|")
for i in p5:
    lab = {"RACE": "racy", "CLEAN": "race-free"}.get(man[i]["label"], "?")
    v = [lit(m, i) for m in MODES]; lrows.append((i, lab, *v))
    P(f"| `{meta[i][1]}` | {lab} | " + " | ".join(v) + " |")
wcsv("table_litmus.csv", ["id","scor_label","vector_clock","scalar_clock","collector_only"], lrows)
tex = subprocess.run(["git", "-C", os.path.expanduser("~/cuRacePaper"), "show", "origin/HEAD:appendix_eval.tex"], capture_output=True, text=True).stdout
exp_lit = {}
sec = tex.split("\\label{tab:eval-litmus}")[1].split("\\bottomrule")[0] if "\\label{tab:eval-litmus}" in tex else ""
for line in sec.split("\n"):
    mm = re.match(r"\\texttt\{(.+?)\}\s*&\s*(.+?)\s*&\s*(.+?)\s*&\s*(.+?)\s*&\s*(.+?)\s*&", line)
    if mm:
        k = mm.group(1).replace("\\_", "_")
        norm = lambda s: re.sub(r"\\textsuperscript\{.*?\}|\^\{.*?\}|\$.*?\$|†|\*", "", s).strip().replace("---", "—").replace("--", "—")
        exp_lit[k] = (norm(mm.group(4)), norm(mm.group(5)))
litmism = []
for i in p5:
    k = meta[i][1]
    if k in exp_lit:
        got = (lit(VC, i), lit(SC, i))
        # the paper's litmus table shows, per cell, Race if a data race is reported, Strong if only a strong conflict
        if got != exp_lit[k]: litmism.append((k, exp_lit[k], got))
    else: litmism.append((k, "not in paper table", None))
P(f"\n{len(p5)} P5 programs; {len(exp_lit)} kernels parsed from the paper's table; {len(litmism)} vector/scalar cells differ from the paper.")
for x in litmism: P("  - " + repr(x))

# ---- slowdown, memory ----
P("\n## fig_slowdown: per-suite geometric-mean slowdown, third mode added\n")
rat = mt._ratios(runs, meta)
SL = [("Indigo3", ("P1",)), ("Indigo 1.3", ("PI",)), ("ECL", ("P3",)), ("ScoR apps", ("P4",)), ("ScoR litmus", ("P5",)),
      ("cuHadron", ("P6",)), ("HeCBench other 14", ("P7",)), ("HeCBench SC 10", ("P9",)),
      ("All", ("P1","PI","P3","P4","P5","P6"))]
def gm(xs): return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None
sl_rows = []; P("| suite | VC geomean (n) | SC geomean (n) | CO geomean (n) |"); P("|---|---|---|---|")
for name, ps in SL:
    cells = []
    for m in MODES:
        xs = [x for (i, t, mm), x in rat.items() if t == "cuvein" and mm == m and meta[i][0] in ps
              and runs[(i, t, mm)]["verdict"] in ("RACE", "CLEAN")]
        sl_rows.append((name, m, len(xs), f"{gm(xs):.4f}" if xs else "")); cells.append(f"{gm(xs):.1f} ({len(xs)})" if xs else "—")
    P(f"| {name} | " + " | ".join(cells) + " |")
wcsv("fig_slowdown_geomeans.csv", ["suite","mode","n","geomean"], sl_rows)
P("\nPaper figure (VC / SC): Indigo3 10.4/8.7, Indigo 1.3 6.9/6.8, ECL 10.1/8.8, ScoR apps 28.8/9.4, litmus 8.8/7.4, cuHadron 13.0/10.8, HeCBench other 14 1349.0/249.7, SC 10 1694.4/512.6, All 7.5/7.1.")
P("\nC1's own report (`eval/COLLECTOR_ONLY.md`, native wall of the same job): P1 6.38, PI 5.03, P3 5.95, P4 6.62, P5 5.55, P6 6.67, P7 93.52, P9 94.19. "
  "Here the denominator is the smaller of the X1b id-level native wall and C1's own (the X1b convention of `_ratios`), so the vector- and scalar-clock figures are unchanged by the third mode.")

P("\n## tab:eval-memory: peak memory (GB), third mode added\n")
def peaks(mode, psets, finished=True):
    return [r["peak"] for (i, t, m), r in runs.items() if t == "cuvein" and m == mode and meta[i][0] in psets and r["peak"] is not None
            and ((r["verdict"] in ("RACE", "CLEAN")) == finished)]
P("| | VC | SC | CO |"); P("|---|---|---|---|")
lab_ps = ("P1","PI","P3","P4","P5","P6")
mrows = []
def gbm(xs): return f"{statistics.median(xs)/1000:.2f}" if xs else "—"
P("| Labelled suites, median | " + " | ".join(gbm(peaks(m, lab_ps)) for m in MODES) + " |")
P("| HeCBench applications that finished, median | " + " | ".join(gbm(peaks(m, ("P7","P9"))) for m in MODES) + " |")
for m in MODES: mrows += [("labelled median GB", m, gbm(peaks(m, lab_ps))), ("hecbench finished median GB", m, gbm(peaks(m, ("P7","P9"))))]
for nm in ("P9-atomicCAS-cuda", "P7-stencil1d-cuda", "P7-particlefilter-cuda"):
    cells = []
    for m in MODES:
        r = runs.get((nm, "cuvein", m))
        cells.append(f"{r['verdict']} {r['peak']/1000:.1f}" if r and r["peak"] is not None else "—"); mrows.append((nm, m, cells[-1]))
    P(f"| `{nm}` | " + " | ".join(cells) + " |")
P("\n(peak = max over a program's reps of the summed-VmRSS poll; for unfinished runs the last peak seen.) Paper: labelled 0.85 / 0.86; HeCBench scalar-clock median 14.0 GB.")
wcsv("table_memory.csv", ["row","mode","value"], mrows)

# ---- programs without a verdict ----
P("\n## app:eval-noverdict: programs without a verdict, per mode\n")
nv = collections.defaultdict(dict)
for (i, t, m), r in runs.items():
    if t == "cuvein" and m in MODES and r["verdict"] in ("TIMEOUT", "ERROR"): nv[i][m] = r
    if t == "cuvein" and m == "" and r["verdict"] == "ERROR": nv[i]["all"] = r   # runner-level rows without a mode (missing-exe)
P("| program | VC | SC | CO |"); P("|---|---|---|---|")
nrows = []
sm90 = [i for i in nv if i.startswith(("P6-bulkcpy", "P6-dsmem"))]
for i in sorted(nv):
    if i in sm90: continue
    cells = []
    for m in MODES:
        r = runs.get((i, "cuvein", m))
        cells.append((f"{r['verdict']} ({'analysis-timeout' if 'analysis-timeout' in r['notes'] else 'cap'})" if r["verdict"] in ("TIMEOUT","ERROR") else r["verdict"]) if r else "—")
    nrows.append((i, *cells)); P(f"| `{i}` | " + " | ".join(cells) + " |")
P(f"| {len(sm90)} `P6-bulkcpy-*` / `P6-dsmem-*` | ERROR (needs sm_90) | ERROR | ERROR |")
wcsv("table_noverdict.csv", ["id","vector_clock","scalar_clock","collector_only"], nrows + [(f"{len(sm90)} sm_90 programs", "ERROR", "ERROR", "ERROR")])
for m in MODES:
    k = collections.Counter(r["verdict"] for (i, t, mm), r in runs.items() if t == "cuvein" and mm == m)
    P(f"\n{m}: " + ", ".join(f"{v} {n}" for v, n in sorted(k.items())) + f" of {sum(k.values())} programs")

# ---- item 8 ----
P("\n## Item 8: program-level verdicts, scalar-clock (X1b) against collector-only (C1), separate recordings\n")
dirn = collections.defaultdict(collections.Counter)
diffs = []
def vlab(r): return r["verdict"] if r else "none"
for i, m in meta.items():
    a, b = runs.get((i, "cuvein", SC)), runs.get((i, "cuvein", CO))
    if a is None and b is None: continue
    va, vb = vlab(a), vlab(b)
    dirn[m[0]][(va, vb)] += 1
    if va != vb:
        diffs.append((m[0], i, label(i), va, vb, a["reports"] if a else "", b["reports"] if b else "",
                      (b or {}).get("report_ids", ""), (a or {}).get("report_ids", "")))
P("| suite | programs | same verdict | SC Race → CO Clean | SC Clean → CO Race | other differences |"); P("|---|---|---|---|---|---|")
sumrows = []
for suite in ("P1","PI","P3","P4","P5","P6","P7","P9"):
    d = dirn[suite]; n = sum(d.values()); same = sum(v for (a, b), v in d.items() if a == b)
    rc = d[("RACE","CLEAN")]; cr = d[("CLEAN","RACE")]
    sumrows.append((suite, n, same, rc, cr, n - same - rc - cr)); P(f"| {suite} | {n} | {same} | {rc} | {cr} | {n-same-rc-cr} |")
tn = [sum(r[j] for r in sumrows) for j in range(1, 6)]
P(f"| **all** | {tn[0]} | {tn[1]} | {tn[2]} | {tn[3]} | {tn[4]} |")
wcsv("item8_program_level_summary.csv", ["suite","programs","same","sc_race_co_clean","sc_clean_co_race","other"], sumrows)
wcsv("item8_program_level_diffs.csv", ["suite","id","label","sc_verdict","co_verdict","sc_reports","co_reports","co_report_ids","sc_report_ids"], diffs)
rf = [d for d in diffs if d[2] == "CLEAN" and d[3] == "CLEAN" and d[4] == "RACE"]
P(f"\nRace-free (labelled) programs that are Race in collector-only and Clean in scalar-clock: **{len(rf)}**; per suite: "
  + ", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(d[0] for d in rf).items())) + ". All of them with their pairs: `item8_race_free_co_race_sc_clean.csv`.")
wcsv("item8_race_free_co_race_sc_clean.csv", ["suite","id","co_reports","co_pairs"], [(d[0], d[1], d[6], d[7]) for d in rf])
racy_cr = [d for d in diffs if d[3] == "CLEAN" and d[4] == "RACE" and d[2] != "CLEAN"]
P(f"\nNot race-free-labelled, SC Clean → CO Race: {len(racy_cr)} (labels: " + str(dict(collections.Counter(d[2] or 'unlabelled' for d in racy_cr))) + ")")
other = [d for d in diffs if not (d[3] == "CLEAN" and d[4] == "RACE") and not (d[3] == "RACE" and d[4] == "CLEAN")]
P(f"\nOther differences (a side TIMEOUT/ERROR/none): {len(other)}")
for d in other: P(f"  - `{d[1]}` SC {d[3]} / CO {d[4]}")
rc_ = [d for d in diffs if d[3] == "RACE" and d[4] == "CLEAN"]
P(f"\nScalar-clock Race, collector-only Clean: {len(rc_)}")
for d in rc_[:100]: P(f"  - `{d[1]}` label {d[2] or 'unlabelled'}: SC {d[5]} reports")
wcsv("item8_sc_race_co_clean.csv", ["suite","id","label","sc_reports","sc_pairs"], [(d[0], d[1], d[2], d[5], d[8]) for d in rc_])

# ---- check ----
P("\n## Check against the paper (vector-clock and scalar-clock cells)\n")
if mism or litmism:
    P(f"**{len(mism)} accuracy/countings cells and {len(litmism)} litmus cells differ from the paper's.** (suite, counting, mode, paper, recomputed):")
    for x in mism: P("  - " + repr(x))
else:
    P("Every vector-clock and scalar-clock cell of Table 6.1, the union table, the three-countings table and the litmus table recomputes to the paper's value.")
open(f"{OUT}/co_tables1.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))

