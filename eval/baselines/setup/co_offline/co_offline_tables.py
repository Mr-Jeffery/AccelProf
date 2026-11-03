#!/usr/bin/env python3
"""C4 items 1 and 3: the paper's accuracy / union / countings / litmus tables with the fourth cuVein column (CO-R:
collector-only, re-scored = the verdict layer on the scalar-clock kernel JSONs with the barrier-ordered rule off), next to
vector-clock, scalar-clock and C1's collector-only run (here "cuVein edges only"); and the program-level comparison of CO-R
against scalar-clock (the same recordings).  Based on C3's co_tables1.py.  Run from the worktree root in the sandbox tree
of p_co_offline_tables.sh (COSB)."""
import collections
import csv
import os
import re
import subprocess
import sys

sys.argv = [sys.argv[0], "--collector-only", "--co-offline"]
SB = os.environ.get("COSB", "/home/fzheng4/co-offline-sandbox")
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt  # noqa: E402

OUT = "/home/fzheng4/wt-c4/eval/results/co-offline/tables"
os.makedirs(OUT, exist_ok=True)
runs, meta = mt.load_runs()
man = mt.load_manifest()
VC, SC, CO, COR = mt.VC, mt.SC, mt.CO, mt.CORS
MODES = (VC, SC, CO, COR)
NAME = {VC: "vector-clock", SC: "scalar-clock", CO: "cuVein edges only", COR: "CO-R"}
md = []


def P(*a):
    md.append(" ".join(str(x) for x in a))


def wcsv(name, header, rows):
    with open(f"{OUT}/{name}", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN"}
OUT_OF_SCOPE = ("asyncmemcpy/", "hostdevice/", "interkernel/")


def label(i):
    return LABEL_OVERRIDE.get(i, man.get(i, {}).get("label", ""))


SUITES = [("Indigo3", lambda i, m: m[0] == "P1"),
          ("Indigo 1.3", lambda i, m: m[0] == "PI"),
          ("Indigo 1.3, SC's 99", lambda i, m: mt._in(m, ("PI@sc",))),
          ("ECL", lambda i, m: m[0] == "P3"),
          ("ScoR applications", lambda i, m: m[0] == "P4"),
          ("ScoR litmus + canary", lambda i, m: m[0] == "P5"),
          ("cuHadron (in scope)", lambda i, m: m[0] == "P6" and not m[1].startswith(OUT_OF_SCOPE)),
          ("HeCBench, SC's 10", lambda i, m: m[0] == "P9")]
AGG = ("Indigo3", "Indigo 1.3", "ECL", "ScoR applications", "cuHadron (in scope)")


def classes(r):
    return mt.report_classes(r) or {}


def has_strong(r):
    c = classes(r)
    return bool(c.get("sc") or c.get("latent-sc"))


def races_verdict(r):
    v = mt.race_alone_verdict(r)
    return r["verdict"] if v is None else v


def positive(kind, r):
    if kind == "races":
        return races_verdict(r) == "RACE"
    if kind == "strong":
        return has_strong(r)
    return races_verdict(r) == "RACE" or has_strong(r)


def counts(mode, pred, kind):
    c = dict(tp=0, pos=0, fp=0, neg=0, to=0, err=0, unl=0)
    for i, m in meta.items():
        if not pred(i, m):
            continue
        r = runs.get((i, "cuvein", mode)) or runs.get((i, "cuvein", ""))
        if r is None:
            continue
        v = r["verdict"]
        if v == "TIMEOUT":
            c["to"] += 1
            continue
        if v == "ERROR":
            c["err"] += 1
            continue
        lab = label(i)
        if lab == "RACE":
            c["pos"] += 1
            c["tp"] += positive(kind, r)
        elif lab == "CLEAN":
            c["neg"] += 1
            c["fp"] += positive(kind, r)
        else:
            c["unl"] += 1
    return c


def fmt(c):
    a = f"{c['tp']:,}/{c['pos']:,}" if c["pos"] else "—"
    b = f"{c['fp']:,}/{c['neg']:,}" if c["neg"] else "—"
    extra = (f"; {c['to']} TO" if c["to"] else "") + (f"; {c['err']} ERR" if c["err"] else "")
    return f"{a} · {b}{extra}"


EXP = {
 ("Indigo3", "races"): {VC: (200, 200, 0, 200, 0), SC: (200, 200, 0, 200, 0)},
 ("Indigo 1.3", "races"): {VC: (1714, 1862, 0, 1260, 0), SC: (1714, 1862, 0, 1260, 0)},
 ("Indigo 1.3, SC's 99", "races"): {VC: (43, 45, 0, 44, 0), SC: (43, 45, 0, 44, 0)},
 ("ECL", "races"): {VC: (0, 0, 16, 60, 0), SC: (0, 0, 16, 60, 0)},
 ("ScoR applications", "races"): {VC: (14, 14, 2, 14, 0), SC: (14, 14, 2, 14, 0)},
 ("ScoR litmus + canary", "races"): {VC: (4, 19, 1, 14, 0), SC: (3, 19, 0, 14, 0)},
 ("cuHadron (in scope)", "races"): {VC: (6, 6, 0, 14, 0), SC: (6, 6, 0, 14, 0)},
 ("HeCBench, SC's 10", "races"): {VC: (2, 2, 0, 6, 2), SC: (3, 3, 0, 6, 1)},
 ("Indigo3", "strong"): {VC: (0, 200, 72, 200, 0), SC: (0, 200, 72, 200, 0)},
 ("Indigo 1.3", "strong"): {VC: (0, 1862, 0, 1260, 0), SC: (0, 1862, 0, 1260, 0)},
 ("ECL", "strong"): {VC: (0, 0, 36, 60, 0), SC: (0, 0, 32, 60, 0)},
 ("ScoR applications", "strong"): {VC: (8, 14, 7, 14, 0), SC: (8, 14, 4, 14, 0)},
 ("ScoR litmus + canary", "strong"): {VC: (17, 19, 4, 14, 0), SC: (17, 19, 0, 14, 0)},
 ("cuHadron (in scope)", "strong"): {VC: (0, 6, 0, 14, 0), SC: (0, 6, 0, 14, 0)},
 ("HeCBench, SC's 10", "strong"): {VC: (0, 2, 0, 6, 2), SC: (0, 3, 0, 6, 1)},
 ("Indigo3", "union"): {VC: (200, 200, 72, 200, 0), SC: (200, 200, 72, 200, 0)},
 ("Indigo 1.3", "union"): {VC: (1714, 1862, 0, 1260, 0), SC: (1714, 1862, 0, 1260, 0)},
 ("ECL", "union"): {VC: (0, 0, 44, 60, 0), SC: (0, 0, 40, 60, 0)},
 ("ScoR applications", "union"): {VC: (14, 14, 7, 14, 0), SC: (14, 14, 4, 14, 0)},
 ("ScoR litmus + canary", "union"): {VC: (19, 19, 5, 14, 0), SC: (18, 19, 0, 14, 0)},
 ("cuHadron (in scope)", "union"): {VC: (6, 6, 0, 14, 0), SC: (6, 6, 0, 14, 0)},
 ("HeCBench, SC's 10", "union"): {VC: (2, 2, 0, 6, 2), SC: (3, 3, 0, 6, 1)},
}
EXP_AGG = {VC: (1934, 2082, 18, 1548), SC: (1934, 2082, 18, 1548)}
mism = []


def check(suite, kind, mode, c):
    e = EXP.get((suite, kind), {}).get(mode)
    if e is None:
        return
    got = (c["tp"], c["pos"], c["fp"], c["neg"], c["to"])
    if got != e:
        mism.append((suite, kind, mode, e, got))


rows61 = []
P("## Table 6.1 (tab:eval-accuracy): accuracy per suite, data races alone, CO-R next to the three other cuVein columns\n")
P("Cells: recall TP/(TP+FN) · false-positive rate FP/(FP+TN); TO = timed out, ERR = errored. Race-alone verdict = `race_alone_verdict` of "
  "`make_tables.py`. CO-R: a conflicting reuse pair no certificate orders is Race (class `race`) or SC; no Latent. "
  "\"Edges only\" = C1's collector-only run (separate recording, no sync pass).\n")
P("| suite | vector-clock | scalar-clock | cuVein edges only (C1) | CO-R |")
P("|---|---|---|---|---|")


def agg_counts(mode, kind):
    tot = collections.Counter()
    for name, pred in SUITES:
        if name in AGG:
            for k, v in counts(mode, pred, kind).items():
                tot[k] += v
    return tot


for name, pred in SUITES:
    cs = {m: counts(m, pred, "races") for m in MODES}
    for m in MODES:
        check(name, "races", m, cs[m])
        rows61.append((name, m, "races", *[cs[m][k] for k in ("tp", "pos", "fp", "neg", "to", "err")]))
    P(f"| {name} | " + " | ".join(fmt(cs[m]) for m in MODES) + " |")
ag = {m: agg_counts(m, "races") for m in MODES}
for m in MODES:
    rows61.append(("All pre-registered", m, "races", *[ag[m][k] for k in ("tp", "pos", "fp", "neg", "to", "err")]))
P("| **All pre-registered** | " + " | ".join(fmt(ag[m]) for m in MODES) + " |")
for m in (VC, SC):
    got = (ag[m]["tp"], ag[m]["pos"], ag[m]["fp"], ag[m]["neg"])
    if got != EXP_AGG[m]:
        mism.append(("All pre-registered", "races", m, EXP_AGG[m], got))
wcsv("table61_accuracy.csv", ["suite", "mode", "counting", "tp", "positives", "fp", "negatives", "timeout", "error"], rows61)

P("\n## tab:eval-accuracy-union and tab:eval-countings: the three countings, four columns\n")
P("races = Race alone; strong = a program with an unordered strong conflict reported (class `sc`); union = Race or strong. "
  "Cells TP/(TP+FN) · FP/(FP+TN). VC = vector-clock, SC = scalar-clock, EO = cuVein edges only (C1), CO-R.\n")
hdr = "| suite | " + " | ".join(f"{t} {k}" for t in ("VC", "SC", "EO", "CO-R") for k in ("races", "strong", "union")) + " |"
P(hdr)
P("|---|" + "---|" * 12)
rows_c = []
for name, pred in SUITES:
    if name == "Indigo 1.3, SC's 99":
        continue
    cells = []
    for m in MODES:
        for kind in ("races", "strong", "union"):
            c = counts(m, pred, kind)
            check(name, kind, m, c)
            rows_c.append((name, m, kind, *[c[k] for k in ("tp", "pos", "fp", "neg", "to", "err")]))
            cells.append(fmt(c))
    P(f"| {name} | " + " | ".join(cells) + " |")
tot = {}
for m in MODES:
    for kind in ("races", "strong", "union"):
        a = agg_counts(m, kind)
        tot[(m, kind)] = a
        rows_c.append(("All pre-registered", m, kind, *[a[k] for k in ("tp", "pos", "fp", "neg", "to", "err")]))
P("| **All pre-registered** | " + " | ".join(fmt(tot[(m, k)]) for m in MODES for k in ("races", "strong", "union")) + " |")
wcsv("table_countings.csv", ["suite", "mode", "counting", "tp", "positives", "fp", "negatives", "timeout", "error"], rows_c)

P("\n## tab:eval-litmus: the 33 ScoR litmus kernels, four columns\n")
P("Race = a data race is reported; Strong = only an unordered strong conflict is reported; — = nothing reported. "
  "`rtraw` counted as recorded (Race, a false report).\n")


def lit(mode, i):
    r = runs.get((i, "cuvein", mode))
    if r is None:
        return "n/a"
    if r["verdict"] in ("TIMEOUT", "ERROR"):
        return r["verdict"]
    if races_verdict(r) == "RACE":
        return "Race"
    return "Strong" if has_strong(r) else "—"


p5 = sorted(i for i, m in meta.items() if m[0] == "P5")
lrows = []
P("| kernel | ScoR label | VC | SC | edges only | CO-R |")
P("|---|---|---|---|---|---|")
for i in p5:
    lab = {"RACE": "racy", "CLEAN": "race-free"}.get(man[i]["label"], "?")
    v = [lit(m, i) for m in MODES]
    lrows.append((i, lab, *v))
    P(f"| `{meta[i][1]}` | {lab} | " + " | ".join(v) + " |")
wcsv("table_litmus.csv", ["id", "scor_label", "vector_clock", "scalar_clock", "edges_only", "co_r"], lrows)
tex = subprocess.run(["git", "-C", os.path.expanduser("~/cuRacePaper"), "show", "origin/HEAD:appendix_eval.tex"],
                     capture_output=True, text=True).stdout
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
        if got != exp_lit[k]:
            litmism.append((k, exp_lit[k], got))
    else:
        litmism.append((k, "not in paper table", None))
P(f"\n{len(p5)} P5 programs; {len(exp_lit)} kernels parsed from the paper's table; {len(litmism)} vector/scalar cells differ from the paper.")
for x in litmism:
    P("  - " + repr(x))

# ---- item 3: program level, CO-R against scalar-clock (same recordings) ----
P("\n## Program level: CO-R against scalar-clock (the same recordings; every difference is the barrier-ordered rule)\n")
LAB = {"RACE": "racy", "CLEAN": "race-free", "": "unlabelled"}
dirn = collections.defaultdict(collections.Counter)
diffs = []


def vlab(r):
    return r["verdict"] if r else "none"


for i, m in meta.items():
    a, b = runs.get((i, "cuvein", SC)), runs.get((i, "cuvein", COR))
    if a is None and b is None:
        continue
    va, vb = vlab(a), vlab(b)
    dirn[m[0]][(va, vb)] += 1
    if va != vb:
        diffs.append((m[0], i, label(i), va, vb, a["reports"] if a else "", b["reports"] if b else "",
                      (b or {}).get("report_ids", ""), (a or {}).get("report_ids", "")))
P("| suite | programs | same verdict | SC Race → CO-R Clean | SC Clean → CO-R Race | other differences |")
P("|---|---|---|---|---|---|")
sumrows = []
for suite in ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"):
    d = dirn[suite]
    n = sum(d.values())
    same = sum(v for (a, b), v in d.items() if a == b)
    rc = d[("RACE", "CLEAN")]
    cr = d[("CLEAN", "RACE")]
    sumrows.append((suite, n, same, rc, cr, n - same - rc - cr))
    P(f"| {suite} | {n} | {same} | {rc} | {cr} | {n - same - rc - cr} |")
tn = [sum(r[j] for r in sumrows) for j in range(1, 6)]
P(f"| **all** | {tn[0]} | {tn[1]} | {tn[2]} | {tn[3]} | {tn[4]} |")
wcsv("program_level_summary.csv", ["suite", "programs", "same", "sc_race_cor_clean", "sc_clean_cor_race", "other"], sumrows)
wcsv("program_level_diffs.csv", ["suite", "id", "label", "sc_verdict", "cor_verdict", "sc_reports", "cor_reports", "cor_report_ids", "sc_report_ids"], diffs)
P("\nThe programs that differ, by suite, direction and label (the paper's label: racy / race-free / unlabelled):\n")
P("| suite | direction | racy | race-free | unlabelled |")
P("|---|---|---|---|---|")
bl = collections.Counter()
for d in diffs:
    bl[(d[0], f"SC {d[3]} → CO-R {d[4]}", LAB.get(d[2], d[2] or "unlabelled"))] += 1
keys = sorted({(s, dr) for s, dr, _ in bl})
for s, dr in keys:
    P(f"| {s} | {dr} | {bl[(s, dr, 'racy')]} | {bl[(s, dr, 'race-free')]} | {bl[(s, dr, 'unlabelled')]} |")
rf = [d for d in diffs if d[2] == "CLEAN" and d[3] == "CLEAN" and d[4] == "RACE"]
P(f"\nRace-free (labelled) programs that are Race in CO-R and Clean in scalar-clock: **{len(rf)}**; per suite: "
  + ", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(d[0] for d in rf).items())) + ". Each with its pairs: `race_free_cor_race_sc_clean.csv`.")
wcsv("race_free_cor_race_sc_clean.csv", ["suite", "id", "cor_reports", "cor_pairs"], [(d[0], d[1], d[6], d[7]) for d in rf])
# race-free programs Race in CO-R, including those already Race in SC (false positives of both)
rf_all = [i for i, m in meta.items() if label(i) == "CLEAN" and (runs.get((i, "cuvein", COR)) or {}).get("verdict") == "RACE"]
wcsv("race_free_cor_race_all.csv", ["suite", "id", "sc_verdict", "cor_reports", "cor_report_ids"],
     [(meta[i][0], i, (runs.get((i, "cuvein", SC)) or {}).get("verdict", ""), runs[(i, "cuvein", COR)]["reports"], runs[(i, "cuvein", COR)].get("report_ids", "")) for i in rf_all])
P(f"\nAll race-free-labelled programs that are Race in CO-R: {len(rf_all)} (of them Race in scalar-clock too: "
  f"{sum(1 for i in rf_all if (runs.get((i, 'cuvein', SC)) or {}).get('verdict') == 'RACE')}).")
other = [d for d in diffs if not (d[3] == "CLEAN" and d[4] == "RACE") and not (d[3] == "RACE" and d[4] == "CLEAN")]
P(f"\nOther differences (a side TIMEOUT / ERROR / none): {len(other)}")
for d in other:
    P(f"  - `{d[1]}` SC {d[3]} / CO-R {d[4]}")
rcr = [d for d in diffs if d[3] == "RACE" and d[4] == "CLEAN"]
P(f"\nScalar-clock Race, CO-R Clean: {len(rcr)}" + (" (impossible by construction unless a run differs)" if rcr else ""))
for d in rcr[:50]:
    P(f"  - `{d[1]}`")

P("\n## Check against the paper (vector-clock and scalar-clock cells)\n")
if mism or litmism:
    P(f"**{len(mism)} accuracy/countings cells and {len(litmism)} litmus cells differ from the paper's.** (suite, counting, mode, paper, recomputed):")
    for x in mism:
        P("  - " + repr(x))
else:
    P("Every vector-clock and scalar-clock cell of Table 6.1, the union table, the three-countings table and the litmus table recomputes to the paper's value.")
open(f"{OUT}/co_offline_tables.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
