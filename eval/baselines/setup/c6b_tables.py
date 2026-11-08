#!/usr/bin/env python3
"""C6b step 4, tables: the paper's Table 3 (tab:eval-accuracy, Indigo 1.3 per code), the per-program-input version, the three
countings (races / strong / union), the litmus table, the Indigo 1.3 per-input table against the input-level oracle and the
program-level comparisons, with the C6b settings S1 (--chain-closure --co-async --co-r3 strict) and S2 (... --co-r3 off) as two extra
cuVein columns next to vector-clock, scalar-clock, C1's collector-only run and C6's chain-closure run.  Based on C6's c6_tables.py
(same method; its fourth column is here the fifth and sixth).
make_tables.py is the tracked file (copied into the sandbox of c6b_stage.sh, no patch): its load_runs() reads every
baselines-*.csv of the sandbox and passes mode names through unchanged, so the C6 / S1 / S2 rows enter as the modes
collector-only-chain / -s1 / -s2.  Run from anywhere: python c6b_tables.py  (writes $OUTD/tables/)."""
import collections
import csv
import os
import re
import subprocess
import sys

sys.argv = [sys.argv[0], "--collector-only"]
SB = os.environ.get("COSB", "/home/fzheng4/c6b-step4/sand")
sys.path.insert(0, f"{SB}/eval/baselines")
import make_tables as mt  # noqa: E402

OUT = os.environ.get("OUTD", "/home/fzheng4/wt-c6b/eval/results/co-chain-b/step4") + "/tables"
os.makedirs(OUT, exist_ok=True)
runs, meta = mt.load_runs()
man = mt.load_manifest()
VC, SC, CO = mt.VC, mt.SC, mt.CO
CC, S1, S2 = "collector-only-chain", "collector-only-s1", "collector-only-s2"
MODES = (VC, SC, CO, CC, S1, S2)
NAME = {VC: "vector-clock", SC: "scalar-clock", CO: "C1", CC: "C6", S1: "S1", S2: "S2"}
md = []


def P(*a):
    md.append(" ".join(str(x) for x in a))


def wcsv(name, header, rows):
    with open(f"{OUT}/{name}", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN", "P9-atomicCAS-cuda": "CLEAN"}   # evaluation.tex: scored race-free
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


# the paper's own VC / SC cells (appendix_eval.tex, per program-input), for the check
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
EXP_AGG = {VC: (1934, 2082, 18, 1548), SC: (1934, 2082, 18, 1548)}      # per program-input
mism = []


def check(suite, kind, mode, c):
    e = EXP.get((suite, kind), {}).get(mode)
    if e is None:
        return
    got = (c["tp"], c["pos"], c["fp"], c["neg"], c["to"])
    if got != e:
        mism.append((suite, kind, mode, e, got))


HDR = "| suite | " + " | ".join(NAME[m] for m in MODES) + " |"
SEP = "|---|" + "---|" * len(MODES)

# ------------------------------------------------------------------ Table 3 per code (the paper's layout)
IN_RE = re.compile(r"^(?:counter)?DAG_\d+n_\d+e$|^power_law_\d+n_\d+e$")


def code_of(i):
    return meta[i][1]                      # PI: program = the code; input = the graph


def code_counts(mode, codes_of_pi):
    """Indigo 1.3 counted per code: a code is reported when any of its inputs is Race (races alone)."""
    c = dict(tp=0, pos=0, fp=0, neg=0, to=0, err=0, unl=0)
    byc = collections.defaultdict(list)
    for i, m in meta.items():
        if m[0] == "PI" and code_of(i) in codes_of_pi:
            byc[code_of(i)].append(i)
    for code, ids in byc.items():
        labs = {label(i) for i in ids}
        lab = labs.pop() if len(labs) == 1 else "MIXED"
        rs = [runs.get((i, "cuvein", mode)) for i in ids]
        rs = [r for r in rs if r is not None]
        if not rs:
            continue
        rep = any(races_verdict(r) == "RACE" for r in rs)
        if lab == "RACE":
            c["pos"] += 1
            c["tp"] += rep
        elif lab == "CLEAN":
            c["neg"] += 1
            c["fp"] += rep
        else:
            c["unl"] += 1
    return c, len(byc)


all_pi_codes = {code_of(i) for i, m in meta.items() if m[0] == "PI"}
sc_codes = {code_of(i) for i, m in meta.items() if mt._in(m, ("PI@sc",))}
P("## Table 3 (tab:eval-accuracy): accuracy per suite, data races alone, Indigo 1.3 counted per code, six cuVein columns\n")
P("Cells: recall TP/(TP+FN) · false-positive rate FP/(FP+TN). Indigo 1.3 labels a code, so its rows count codes: a code is reported when "
  "the mode reports Race on any of its seven inputs. All other rows count program-inputs as in the paper. Aggregate = Indigo3 + Indigo 1.3 "
  "(codes) + ECL + ScoR applications + cuHadron in scope. C1 = C1's collector-only run (atomicCAS row as in eval/cap-84600), "
  "C6 = C6's chain-closure re-analysis of the same recordings, S1 / S2 = the C6b re-analyses of the same recordings "
  "(S1: `--chain-closure --co-async --co-r3 strict`, S2: `--chain-closure --co-async --co-r3 off`).\n")
P(HDR)
P(SEP)
rows3 = []
agg3 = {m: collections.Counter() for m in MODES}
for name, pred in SUITES:
    if name == "ScoR litmus + canary":
        continue                      # not in Table 3 (Appendix litmus table)
    cells = []
    for m in MODES:
        if name == "Indigo 1.3":
            c, ncodes = code_counts(m, all_pi_codes)
        elif name == "Indigo 1.3, SC's 99":
            c, ncodes = code_counts(m, sc_codes)
        else:
            c = counts(m, pred, "races")
        rows3.append((name, m, "races-per-code" if name.startswith("Indigo 1.3") else "races",
                      *[c[k] for k in ("tp", "pos", "fp", "neg", "to", "err")]))
        cells.append(fmt(c))
        if name in AGG:
            for k, v in c.items():
                agg3[m][k] += v
    P(f"| {name}{' (' + str(ncodes) + ' codes)' if name.startswith('Indigo 1.3') else ''} | " + " | ".join(cells) + " |")
P("| **All pre-registered** | " + " | ".join(fmt(agg3[m]) for m in MODES) + " |")
for m in MODES:
    rows3.append(("All pre-registered", m, "races-per-code", *[agg3[m][k] for k in ("tp", "pos", "fp", "neg", "to", "err")]))
P("\n**Table 3, aggregate row (races alone; Indigo 1.3 per code), explicitly:**\n")
for m in MODES:
    a = agg3[m]
    P(f"- {NAME[m]}: recall {a['tp']}/{a['pos']} · FP {a['fp']}/{a['neg']}" + (f"; {a['err']} ERR" if a["err"] else "") + (f"; {a['to']} TO" if a["to"] else ""))
EXP3 = {VC: (486, 486, 18, 468), SC: (486, 486, 18, 468), CO: (486, 486, 54, 468)}
for m, e in EXP3.items():
    got = (agg3[m]["tp"], agg3[m]["pos"], agg3[m]["fp"], agg3[m]["neg"])
    P(f"\nAggregate check, {NAME[m]}: paper {e}, recomputed {got} -> {'equal' if got == e else 'DIFFERENT'}")
wcsv("table3_per_code.csv", ["suite", "mode", "counting", "tp", "positives", "fp", "negatives", "timeout", "error"], rows3)

# ------------------------------------------------------------------ per program-input
rows61 = []
P("\n## Accuracy per program-input (Indigo 1.3 counted per run), six columns\n")
P(HDR)
P(SEP)


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
wcsv("table61_accuracy_per_input.csv", ["suite", "mode", "counting", "tp", "positives", "fp", "negatives", "timeout", "error"], rows61)

# ------------------------------------------------------------------ union and countings
P("\n## tab:eval-accuracy-union and tab:eval-countings: the three countings, six columns (per program-input)\n")
P("races = Race alone; strong = a program with an unordered strong conflict reported (class `sc`); union = Race or strong. "
  "Cells TP/(TP+FN) · FP/(FP+TN).\n")
rows_c = []
tot = {}
for kind in ("races", "strong", "union"):
    P(f"\n**{kind}**\n")
    P(HDR)
    P(SEP)
    for name, pred in SUITES:
        if name == "Indigo 1.3, SC's 99":
            continue
        cells = []
        for m in MODES:
            c = counts(m, pred, kind)
            check(name, kind, m, c)
            rows_c.append((name, m, kind, *[c[k] for k in ("tp", "pos", "fp", "neg", "to", "err")]))
            cells.append(fmt(c))
        P(f"| {name} | " + " | ".join(cells) + " |")
    for m in MODES:
        tot[(m, kind)] = agg_counts(m, kind)
        rows_c.append(("All pre-registered", m, kind, *[tot[(m, kind)][k] for k in ("tp", "pos", "fp", "neg", "to", "err")]))
    P("| **All pre-registered** | " + " | ".join(fmt(tot[(m, kind)]) for m in MODES) + " |")
wcsv("table_countings.csv", ["suite", "mode", "counting", "tp", "positives", "fp", "negatives", "timeout", "error"], rows_c)

# ------------------------------------------------------------------ litmus
P("\n## tab:eval-litmus: the 33 ScoR litmus kernels, six columns\n")
P("Race = a data race is reported; Strong = only an unordered strong conflict is reported; — = nothing reported. `rtraw` counted as recorded.\n")


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
P("| kernel | ScoR label | " + " | ".join(NAME[m] for m in MODES) + " | moved |")
P("|---|---|" + "---|" * (len(MODES) + 1))
for i in p5:
    lab = {"RACE": "racy", "CLEAN": "race-free"}.get(man[i]["label"], "?")
    v = [lit(m, i) for m in MODES]
    lrows.append((i, lab, *v))
    mv = []
    if v[3] != v[4]:
        mv.append(f"S1 vs C6: {v[3]} -> {v[4]}")
    if v[3] != v[5]:
        mv.append(f"S2 vs C6: {v[3]} -> {v[5]}")
    P(f"| `{meta[i][1]}` | {lab} | " + " | ".join(v) + " | " + ("; ".join(mv) if mv else "") + " |")
wcsv("table_litmus.csv", ["id", "scor_label", *[NAME[m] for m in MODES]], lrows)
for a, b in ((CO, CC), (CC, S1), (CC, S2), (CO, S1), (CO, S2), (SC, S1), (SC, S2)):
    ch = [(meta[i][1], lit(a, i), lit(b, i)) for i in p5 if lit(a, i) != lit(b, i)]
    P(f"\nLitmus kernels whose cell differs between {NAME[a]} and {NAME[b]}: {len(ch)}" + "".join(f"\n  - `{k}` {x} -> {y}" for k, x, y in ch))
tex = subprocess.run(["git", "-C", os.path.expanduser("~/cuRacePaper"), "show", "origin/main:appendix_eval.tex"], capture_output=True, text=True).stdout
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
P(f"\n{len(p5)} P5 programs; {len(exp_lit)} kernels parsed from the paper's table (read only, `git show origin/main:appendix_eval.tex`); {len(litmism)} vector/scalar cells differ from the paper.")
for x in litmism:
    P("  - " + repr(x))

# ------------------------------------------------------------------ program level
LAB = {"RACE": "racy", "CLEAN": "race-free", "": "unlabelled"}


def vlab(r):
    return races_verdict(r) if r and r["verdict"] in ("RACE", "CLEAN") else (r["verdict"] if r else "none")


def program_level(mA, mB, tag):
    nameA, nameB = NAME[mA], NAME[mB]
    dirn = collections.defaultdict(collections.Counter)
    diffs = []
    for i, m in meta.items():
        a, b = runs.get((i, "cuvein", mA)), runs.get((i, "cuvein", mB))
        if a is None and b is None:
            continue
        va, vb = vlab(a), vlab(b)
        dirn[m[0]][(va, vb)] += 1
        if va != vb:
            diffs.append((m[0], i, label(i), va, vb, a["reports"] if a else "", b["reports"] if b else "",
                          (b or {}).get("report_ids", ""), (a or {}).get("report_ids", "")))
    P(f"\n### Program level: {nameB} against {nameA}\n")
    P(f"| suite | programs | same verdict | {nameA} Race → {nameB} Clean | {nameA} Clean → {nameB} Race | other differences |")
    P("|---|---|---|---|---|---|")
    sumrows = []
    for suite in ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9"):
        d = dirn[suite]
        n = sum(d.values())
        same = sum(v for (a, b), v in d.items() if a == b)
        rc, cr = d[("RACE", "CLEAN")], d[("CLEAN", "RACE")]
        sumrows.append((suite, n, same, rc, cr, n - same - rc - cr))
        P(f"| {suite} | {n} | {same} | {rc} | {cr} | {n - same - rc - cr} |")
    tn = [sum(r[j] for r in sumrows) for j in range(1, 6)]
    P(f"| **all** | {tn[0]} | {tn[1]} | {tn[2]} | {tn[3]} | {tn[4]} |")
    wcsv(f"program_level_{tag}_summary.csv", ["suite", "programs", "same", f"{nameA}_race_{nameB}_clean", f"{nameA}_clean_{nameB}_race", "other"], sumrows)
    wcsv(f"program_level_{tag}_diffs.csv", ["suite", "id", "label", f"{nameA}_verdict", f"{nameB}_verdict", f"{nameA}_reports", f"{nameB}_reports",
                                          f"{nameB}_report_ids", f"{nameA}_report_ids"], diffs)
    bl = collections.Counter()
    for d in diffs:
        bl[(d[0], f"{nameA} {d[3]} → {nameB} {d[4]}", LAB.get(d[2], d[2] or "unlabelled"))] += 1
    if diffs:
        P("\nPrograms that differ, by suite, direction and the paper's label:\n")
        P("| suite | direction | racy | race-free | unlabelled |")
        P("|---|---|---|---|---|")
        for s, dr in sorted({(s, dr) for s, dr, _ in bl}):
            P(f"| {s} | {dr} | {bl[(s, dr, 'racy')]} | {bl[(s, dr, 'race-free')]} | {bl[(s, dr, 'unlabelled')]} |")
        if len(diffs) <= 12:
            P("\nThe programs: " + ", ".join(f"`{d[1]}` ({LAB.get(d[2], d[2] or 'unlabelled')}, {d[3]} → {d[4]})" for d in diffs))
    return diffs


P("\n## Program level\n")
pl = {}
for mA, mB, tag in ((CC, S1, "s1_vs_c6"), (CC, S2, "s2_vs_c6"), (CO, S1, "s1_vs_c1"), (CO, S2, "s2_vs_c1"),
                    (SC, S1, "s1_vs_sc"), (SC, S2, "s2_vs_sc"), (S1, S2, "s2_vs_s1")):
    pl[tag] = program_level(mA, mB, tag)
for s, tag in (("S1", "s1_vs_sc"), ("S2", "s2_vs_sc")):
    d_sc = pl[tag]
    rf = [d for d in d_sc if d[2] == "CLEAN" and d[3] == "CLEAN" and d[4] == "RACE"]
    P(f"\n{s}: race-free-labelled programs Race in {s} and Clean in scalar-clock: **{len(rf)}**; per suite: "
      + ", ".join(f"{k} {v}" for k, v in sorted(collections.Counter(d[0] for d in rf).items())))
    scr = [d for d in d_sc if d[3] == "RACE" and d[4] == "CLEAN"]
    P(f"{s}: scalar-clock Race, {s} Clean: {len(scr)} programs (labels: "
      + str(dict(collections.Counter(LAB.get(d[2], d[2] or 'unlabelled') for d in scr))) + "; per suite " + str(dict(collections.Counter(d[0] for d in scr)))
      + "): " + ", ".join(f"`{d[1]}`" for d in scr))
    cr = [d for d in d_sc if d[3] == "CLEAN" and d[4] == "RACE"]
    P(f"{s}: scalar-clock Clean, {s} Race: {len(cr)} programs (labels: "
      + str(dict(collections.Counter(LAB.get(d[2], d[2] or 'unlabelled') for d in cr))) + "; per suite " + str(dict(collections.Counter(d[0] for d in cr))) + ")")
    wcsv(f"sc_race_{s.lower()}_clean.csv", ["suite", "id", "label", "sc_reports", "sc_pairs"], [(d[0], d[1], d[2], d[5], d[8]) for d in scr])
    wcsv(f"{s.lower()}_race_sc_clean.csv", ["suite", "id", "label", f"{s}_reports", f"{s}_pairs"], [(d[0], d[1], d[2], d[6], d[7]) for d in cr])
P("\nRace-free-labelled programs that are Race, per mode (programs):\n")
P("| mode | " + " | ".join(["total"] + ["P1", "PI", "P3", "P4", "P6", "P7", "P9"]) + " |")
P("|---|" + "---|" * 8)
for m in MODES:
    ids = [i for i in meta if label(i) == "CLEAN" and (runs.get((i, "cuvein", m)) or {}).get("verdict") in ("RACE", "CLEAN")
           and races_verdict(runs[(i, "cuvein", m)]) == "RACE"]
    cnt = collections.Counter(meta[i][0] for i in ids)
    P(f"| {NAME[m]} | {len(ids)} | " + " | ".join(str(cnt[s]) for s in ("P1", "PI", "P3", "P4", "P6", "P7", "P9")) + " |")

# ------------------------------------------------------------------ Indigo 1.3 per input against the oracle
orc = {}
for r in csv.DictReader(open(f"{SB}/eval/results/baselines-pi-oracle.csv", newline="")):
    orc[r["id"]] = r
P("\n## Indigo 1.3 per program-input against the input-level oracle (baselines-pi-oracle.csv)\n")
P(f"The oracle file has {len(orc)} rows (ids found in the runs: {sum(1 for i in orc if (i, 'cuvein', SC) in runs)}). "
  "Cell: programs with that verdict. Rows are the oracle's answer (CONFLICT = two threads touch one location, one writes, not both atomic, no barrier between; "
  "NO-CONFLICT otherwise) by the suite's label.\n")
P("| label | oracle | n | " + " | ".join(f"{NAME[m]} Race" for m in MODES) + " |")
P("|---|---|---|" + "---|" * len(MODES))
orows = []
for lab in ("RACE", "CLEAN", ""):
    for ov in sorted({r["oracle"] for r in orc.values()}):
        ids = [i for i, r in orc.items() if (i, "cuvein", SC) in runs and label(i) == lab and r["oracle"] == ov]
        if not ids:
            continue
        cells = [sum(1 for i in ids if (runs.get((i, "cuvein", m)) or {}).get("verdict") == "RACE") for m in MODES]
        P(f"| {LAB.get(lab, lab)} | {ov} | {len(ids)} | " + " | ".join(str(c) for c in cells) + " |")
        orows.append((LAB.get(lab, lab), ov, len(ids), *cells))
wcsv("pi_oracle_crosstab.csv", ["label", "oracle", "n", *[NAME[m] for m in MODES]], orows)
P("\nRacy-labelled Indigo 1.3 program-inputs a mode does not report (verdict not Race), split by the oracle's answer:\n")
P("| mode | missed | oracle CONFLICT | oracle NO-CONFLICT | not in oracle file |")
P("|---|---|---|---|---|")
mrows = []
for m in MODES:
    miss = [i for i, mm in meta.items() if mm[0] == "PI" and label(i) == "RACE" and (runs.get((i, "cuvein", m)) or {}).get("verdict") != "RACE"
            and (i, "cuvein", m) in runs]
    a = sum(1 for i in miss if i in orc and orc[i]["oracle"] == "CONFLICT")
    b = sum(1 for i in miss if i in orc and orc[i]["oracle"] == "NO-CONFLICT")
    c = sum(1 for i in miss if i not in orc)
    P(f"| {NAME[m]} | {len(miss)} | {a} | {b} | {c} |")
    mrows.append((NAME[m], len(miss), a, b, c))
wcsv("pi_oracle_misses.csv", ["mode", "missed", "oracle_conflict", "oracle_no_conflict", "not_in_oracle"], mrows)
P("\nRace verdicts on Indigo 1.3 program-inputs the oracle says have NO-CONFLICT, by label:\n")
P("| mode | race-free-labelled | racy-labelled | unlabelled |")
P("|---|---|---|---|")
for m in MODES:
    cnt = collections.Counter()
    for i, r in orc.items():
        if r["oracle"] == "NO-CONFLICT" and (runs.get((i, "cuvein", m)) or {}).get("verdict") == "RACE":
            cnt[LAB.get(label(i), "unlabelled")] += 1
    P(f"| {NAME[m]} | {cnt['race-free']} | {cnt['racy']} | {cnt['unlabelled']} |")

P("\n## Check against the paper (vector-clock and scalar-clock cells)\n")
if mism or litmism:
    P(f"**{len(mism)} accuracy/countings cells and {len(litmism)} litmus cells differ from the paper's.** (suite, counting, mode, paper, recomputed):")
    for x in mism:
        P("  - " + repr(x))
else:
    P("Every vector-clock and scalar-clock cell of the per-program-input accuracy table, the union and three-countings tables and the litmus table recomputes to the paper's value.")
open(f"{OUT}/c6b_tables.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
