#!/usr/bin/env python3
"""C7: the tier funnel. Analysis only; reads CSVs, runs nothing.

usage: tier_funnel.py <collector-only.csv> [--inputs DIR] [--out eval/TIER_FUNNEL.md] [--csv-dir DIR] [--title TEXT]

<collector-only.csv> is a baselines-cuvein-style CSV whose mode is collector-only (C1: cap-84600's
baselines-cuvein-co.csv; C6: eval/results/co-chain/merged/baselines-cuvein.csv; later C6b's two settings).
DIR (default: the folder of this script's tier_funnel_inputs.sh output) holds the other inputs, extracted with
git show from their branches (tier_funnel_inputs.sh): cap-baselines-cuvein.csv (vector-clock, scalar-clock),
cap-baselines-iguard.csv, cap-baselines-sanitizer.csv, cap-baselines-racecheck.csv, cap-baselines-hirace.csv
(native walls only), manifest.csv, cap-newkeys.json, cap-old-cells.json, cap-cells.json, fig_slowdown.tex, CAP_84600.md.
Rows are reduced to one per (id, tool, mode) the way make_tables.load_runs does; no number is typed in here.
"""
import argparse, collections, csv, glob, json, math, os, re, statistics, sys

ap = argparse.ArgumentParser()
ap.add_argument("co_csv")
ap.add_argument("--inputs", default=os.path.expanduser("~/c7-data"))
ap.add_argument("--out", default="TIER_FUNNEL.md")
ap.add_argument("--csv-dir", default=None)
ap.add_argument("--title", default=None)
ap.add_argument("--max-list", type=int, default=400, help="longest per-program list printed in the markdown (full lists go to --csv-dir)")
A = ap.parse_args()
IN = A.inputs
VC, SC, CO = "vector-clock", "scalar-clock", "collector-only"
LABEL_OVERRIDE = {"P9-knn-cuda": "CLEAN", "P9-atomicCAS-cuda": "CLEAN"}   # evaluation.tex scores both race-free (cap_cells.py)
SUITES = [("P1", "Indigo3"), ("PI", "Indigo 1.3"), ("P3", "ECL"), ("P4", "ScoR apps"), ("P5", "ScoR litmus"),
          ("P6", "cuHadron"), ("P7", "HeCBench other 14"), ("P9", "HeCBench SC 10")]
PS_NAME = dict(SUITES)
LAB6 = ("P1", "PI", "P3", "P4", "P5", "P6")
ALL_PS = tuple(p for p, _ in SUITES)


# ---------------------------------------------------------------- loading (make_tables.load_runs' reduction)
def effective_verdict(r):
    if (r.get("tool") == "cuvein" and r.get("verdict") == "CLEAN" and str(r.get("rc", "")).strip() not in ("", "0", "127")):
        return "ERROR"
    return r.get("verdict")


def load(paths):
    per, meta = collections.defaultdict(list), {}
    for path in paths:
        base = os.path.basename(path)
        ftool = re.sub(r"^(cap-|c6-)?baselines-", "", base)[:-4]
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                t = r.get("tool") or ftool
                if t == "cuvein":
                    r["verdict"] = effective_verdict({**r, "tool": "cuvein"})
                per[(r["id"], t, r.get("mode", ""))].append(r)
                meta[r["id"]] = (r["pset"], r["program"], r["build"], r["input"])
    runs = {}
    for key, reps in per.items():
        verds = [r["verdict"] for r in reps]
        v = "RACE" if "RACE" in verds else "CLEAN" if "CLEAN" in verds else "TIMEOUT" if "TIMEOUT" in verds else "ERROR"
        def fn(col):
            o = []
            for r in reps:
                try: o.append(float(r[col]))
                except (ValueError, KeyError): pass
            return o
        walls, nats, peaks = fn("wall_s"), fn("native_wall_s"), fn("peak_mb")
        notes = ";".join(sorted({r["notes"] for r in reps if r.get("notes")}))
        m = re.search(r"analysis_s=([0-9.]+)", notes)
        c = re.findall(r"(?:^|;)cap=(\d+)", notes)
        runs[key] = dict(verdict=v, wall=(sorted(walls)[len(walls) // 2] if walls else None),
                         native=(min(nats) if nats else None), peak=(max(peaks) if peaks else None),
                         an=(float(m.group(1)) if m else None), cap=(max(int(x) for x in c) if c else None),
                         reports=max([int(r["reports_dedup"]) for r in reps if r.get("reports_dedup", "").isdigit()] or [0]),
                         rc=",".join(sorted({r.get("rc", "") for r in reps})), notes=notes, reps=len(reps))
    return runs, meta


def P(name): return os.path.join(IN, name)


cv_files = [P("cap-baselines-cuvein.csv"), A.co_csv]
other = [P("cap-baselines-iguard.csv"), P("cap-baselines-sanitizer.csv"), P("cap-baselines-racecheck.csv")]
natives_only = [P("cap-baselines-hirace.csv")]
runs, meta = load(cv_files + other)
man = {r["id"]: r for r in csv.DictReader(open(P("manifest.csv"), newline=""))}
# the collector-only file of CAP (C1), loaded the way make_tables sees it, only to build the paper's slowdown denominators
runs_cap, meta_cap = load([P("cap-baselines-cuvein.csv"), P("cap-baselines-cuvein-co.csv")] + other + natives_only)


def label(i):
    return LABEL_OVERRIDE.get(i, man.get(i, {}).get("label", ""))


def lab3(i):
    l = label(i)
    return "racy" if l == "RACE" else "race-free" if l == "CLEAN" else "unlabelled"


def run(i, tool, mode):
    """make_tables._mrun: a runner-level row without a mode (missing-exe) applies to both cuVein modes"""
    return runs.get((i, tool, mode)) or (runs.get((i, tool, "")) if mode else None)


def V(i, tool, mode):
    r = run(i, tool, mode)
    return r["verdict"] if r else "none"


# universe: the manifest's programs of the eight suites; the 16 sm_90 cuHadron programs have no executable (ERROR missing-exe in every tool)
ids_all = [i for i in meta if meta[i][0] in ALL_PS]
unrunnable = sorted(i for i in ids_all if (i, "cuvein", "") in runs and "missing-exe" in runs[(i, "cuvein", "")]["notes"]
                    and (i, "cuvein", VC) not in runs and (i, "cuvein", CO) not in runs)
IDS = [i for i in ids_all if i not in set(unrunnable)]
SUITE_OF = {i: meta[i][0] for i in ids_all}
IDS_BY = {p: [i for i in IDS if SUITE_OF[i] == p] for p in ALL_PS}

out = []
def W(*a): out.append(" ".join(str(x) for x in a))
def fmt(x, d=1): return "missing" if x is None else f"{x:,.{d}f}"
def gm(xs): return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None
def pct(a, b): return "—" if not b else f"{100 * a / b:.1f}%"
CSVD = A.csv_dir
if CSVD: os.makedirs(CSVD, exist_ok=True)
def wcsv(name, header, rows):
    if not CSVD: return
    with open(os.path.join(CSVD, name), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
def md(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


# ---------------------------------------------------------------- units: program-inputs, plus Indigo 1.3 per code (Table 3)
def unit_of(i, tool_mode):
    return V(i, *tool_mode)


def collapse(vs):
    """a code is Race when any of its inputs is Race (Table 3); else TIMEOUT / ERROR if any input did not finish, else CLEAN"""
    vs = [v for v in vs if v != "none"]
    if not vs: return "none"
    if "RACE" in vs: return "RACE"
    if "TIMEOUT" in vs: return "TIMEOUT"
    if "ERROR" in vs: return "ERROR"
    return "CLEAN"


def units(ps, per_code=False):
    """-> list of dict(key, label, co, sc, vc, ids)"""
    ids = IDS_BY[ps] if isinstance(ps, str) else [i for p in ps for i in IDS_BY[p]]
    if not per_code:
        return [dict(key=i, label=lab3(i), co=V(i, "cuvein", CO), sc=V(i, "cuvein", SC), vc=V(i, "cuvein", VC), ids=[i]) for i in ids]
    g = collections.defaultdict(list)
    for i in ids: g[(meta[i][1], meta[i][2])].append(i)
    us = []
    for k, ii in g.items():
        ls = {lab3(i) for i in ii}
        lab = ls.pop() if len(ls) == 1 else "mixed"
        us.append(dict(key="/".join(k), label=lab, co=collapse([V(i, "cuvein", CO) for i in ii]),
                       sc=collapse([V(i, "cuvein", SC) for i in ii]), vc=collapse([V(i, "cuvein", VC) for i in ii]), ids=ii))
    return us


VERD = ("RACE", "CLEAN", "TIMEOUT", "ERROR", "none")
def tally(us, f):
    c = collections.Counter(f(u) for u in us)
    return [c.get(v, 0) for v in VERD]


if A.title:
    W(f"# {A.title}\n")
else:
    W(f"# C7: the tier funnel, {os.path.basename(A.co_csv)}\n")
W(f"Collector-only input: `{A.co_csv}`. Generated by `eval/baselines/setup/tier_funnel.py`; nothing was run, every number is a count or a sum over rows of the input CSVs.\n")
W("## Inputs and conventions\n")
nrows = {"collector-only": sum(1 for k in runs if k[1] == "cuvein" and k[2] == CO)}
W("| item | value |\n|---|---|")
W(f"| programs | {len(IDS):,} (the manifest's eight suites: " + ", ".join(f"{n} {len(IDS_BY[p]):,}" for p, n in SUITES) + f"); {len(unrunnable)} cuHadron sm_90 programs with no executable (`missing-exe`, ERROR in every tool) are left out; no real-world set |")
W("| vector-clock, scalar-clock | `cap-baselines-cuvein.csv` = origin/eval/cap-84600 `eval/results/cap-84600/baselines-cuvein.csv` (the paper's current rows, tool cap 84,600 s) |")
W(f"| collector-only | `{A.co_csv}` |")
W("| racecheck, iGUARD | origin/eval/cap-84600 `baselines-sanitizer.csv` (+ `eval/results/baselines-racecheck.csv`, as make_tables merges them), `baselines-iguard.csv` |")
W("| labels | `eval/baselines/manifest.csv` (98371ee) `label`: RACE = racy, CLEAN = race-free, anything else = unlabelled; `P9-knn-cuda` and `P9-atomicCAS-cuda` scored race-free as `eval/CAP_84600.md` does. Indigo 1.3 is counted per program-input (7 inputs per code); the per-code rows count a code as Race when any input is Race, as Table 3 does |")
W("| one row per (program, tool, mode) | make_tables.load_runs' reduction: verdict RACE if any rep is RACE, else CLEAN, else TIMEOUT, else ERROR; wall = median of the rep walls; native = minimum; `analysis_s` = the first value in the row's notes |")
W("| time of a run | `wall_s` + `analysis_s` for a cuRace mode (the offline verdict step, Part A N = 16); `wall_s` alone for racecheck and iGUARD. A TIMEOUT row counts its `cap` note (else its wall), an ERROR row its wall: both are lower bounds and are flagged `LB` |")
W("| native time of a program | the minimum over all tools' `native_wall_s` for the id (collector-only's own native included) |")
W("| a tier \"flagged\" | verdict RACE; Clean, TIMEOUT, ERROR and `none` (no row) are listed apart |\n")


# ---------------------------------------------------------------- Table 1
W("## 1. The funnel\n")
W("Columns: programs; collector-only (CO) verdict; of the CO-flagged programs, scalar-clock (SC) and vector-clock (VC) verdict (Race / Clean / TIMEOUT / ERROR / none = no row). Rows: label.\n")
hdr = ["suite", "label", "programs", "CO Race", "CO Clean", "CO TIMEOUT", "CO ERROR", "SC on flagged: Race", "Clean", "TIMEOUT", "ERROR", "none",
       "VC on flagged: Race", "Clean", "TIMEOUT", "ERROR", "none"]
def funnel_rows(name, us):
    rows = []
    for lab in ("racy", "race-free", "unlabelled", "all"):
        sel = [u for u in us if lab == "all" or u["label"] == lab]
        if not sel and lab != "all": continue
        fl = [u for u in sel if u["co"] == "RACE"]
        rows.append([name, lab if lab != "all" else "**all**", f"{len(sel):,}"] + tally(sel, lambda u: u["co"])[:4]
                    + tally(fl, lambda u: u["sc"]) + tally(fl, lambda u: u["vc"]))
    return rows
frows, fcsv = [], []
for p, n in SUITES:
    frows += funnel_rows(n, units(p))
frows += funnel_rows("**All (8 suites)**", units(ALL_PS))
frows += funnel_rows("All labelled (6 suites)", units(LAB6))
frows += funnel_rows("HeCBench (P7 + P9)", units(("P7", "P9")))
frows += funnel_rows("Indigo 1.3 per code (Table 3)", units("PI", per_code=True))
W("\n".join(md(hdr, frows)))
wcsv("funnel.csv", hdr, frows)
W("\nThe per-code Indigo 1.3 row has one unit per (code, build); a code's CO verdict is Race when any of its inputs is Race, and its SC / VC verdict is Race when any input is Race (not necessarily the input CO flagged), so the SC and VC columns of that row are over the CO-flagged codes.\n")

W("### 1b. Race-free programs flagged and then cleared; racy programs confirmed\n")
W("Race-free: of the CO-flagged race-free-labelled programs, what each higher tier says. Racy: of the CO-flagged racy-labelled programs, how many each higher tier confirms (Race). \"Not finished\" = TIMEOUT, ERROR or no row.\n")
hdr = ["suite", "race-free flagged by CO", "SC clears (Clean)", "SC still Race", "SC not finished", "VC clears (Clean)", "VC still Race", "VC not finished",
       "cleared by both", "Race in all three", "racy flagged by CO", "SC confirms", "VC confirms", "racy CO flagged, SC and VC both not Race"]
brow = []
def hl_row(name, us):
    rf = [u for u in us if u["label"] == "race-free" and u["co"] == "RACE"]
    ry = [u for u in us if u["label"] == "racy" and u["co"] == "RACE"]
    nf = lambda v: v not in ("RACE", "CLEAN")
    return [name, len(rf), sum(u["sc"] == "CLEAN" for u in rf), sum(u["sc"] == "RACE" for u in rf), sum(nf(u["sc"]) for u in rf),
            sum(u["vc"] == "CLEAN" for u in rf), sum(u["vc"] == "RACE" for u in rf), sum(nf(u["vc"]) for u in rf),
            sum(u["sc"] == "CLEAN" and u["vc"] == "CLEAN" for u in rf), sum(u["sc"] == "RACE" and u["vc"] == "RACE" for u in rf),
            len(ry), sum(u["sc"] == "RACE" for u in ry), sum(u["vc"] == "RACE" for u in ry),
            sum(u["sc"] != "RACE" and u["vc"] != "RACE" for u in ry)]
for p, n in SUITES: brow.append(hl_row(n, units(p)))
brow.append(hl_row("**All (8 suites)**", units(ALL_PS)))
brow.append(hl_row("All labelled (6 suites)", units(LAB6)))
brow.append(hl_row("Indigo 1.3 per code", units("PI", per_code=True)))
W("\n".join(md(hdr, brow)))
wcsv("funnel_highlights.csv", hdr, brow)
W("")

# per-program lists for the race-free flagged that a tier clears / does not clear
rf_flag = [i for i in IDS if lab3(i) == "race-free" and V(i, "cuvein", CO) == "RACE"]
rf_list = [[i, PS_NAME[SUITE_OF[i]], V(i, "cuvein", SC), V(i, "cuvein", VC)] for i in rf_flag]
wcsv("race_free_flagged.csv", ["id", "suite", "SC", "VC"], rf_list)
W(f"Race-free-labelled programs flagged by CO and still Race in scalar-clock (the false positives that survive the first escalation): " +
  (", ".join(f"`{r[0]}`" for r in rf_list if r[2] == "RACE") or "none") + f". In vector-clock: " + (", ".join(f"`{r[0]}`" for r in rf_list if r[3] == "RACE") or "none") + ".\n")
W(f"Full list of the {len(rf_list):,} race-free-labelled CO-flagged program-inputs with both higher verdicts: `race_free_flagged.csv` in the CSV directory.\n")


# ---------------------------------------------------------------- Table 2
W("## 2. Missed by the first tier\n")
W("Every program a higher tier reports Race and collector-only does not (CO Clean or not finished). Kind: **SC Race** = scalar-clock reports Race (vector-clock agrees or not); **VC-only Race** = vector-clock reports Race, scalar-clock does not, CO is Clean (a certificate the run vetoed); **CO not finished** = CO is TIMEOUT / ERROR / no row and a higher tier reports Race.\n")
miss = []
for i in IDS:
    co, sc, vc = V(i, "cuvein", CO), V(i, "cuvein", SC), V(i, "cuvein", VC)
    if co == "RACE" or (sc != "RACE" and vc != "RACE"): continue
    kind = ("CO not finished" if co != "CLEAN" else "SC Race" if sc == "RACE" else "VC-only Race")
    miss.append(dict(id=i, suite=PS_NAME[SUITE_OF[i]], label=lab3(i), co=co, sc=sc, vc=vc, kind=kind,
                     scr=(run(i, "cuvein", SC) or {}).get("reports"), vcr=(run(i, "cuvein", VC) or {}).get("reports")))
KINDS = ("SC Race", "VC-only Race", "CO not finished")
hdr = ["suite", "label"] + list(KINDS) + ["total"]
rows = []
for sn in [n for _, n in SUITES] + ["All"]:
    for lab in ("racy", "race-free", "unlabelled"):
        sel = [m for m in miss if (sn == "All" or m["suite"] == sn) and m["label"] == lab]
        if sel: rows.append([sn, lab] + [sum(m["kind"] == k for m in sel) for k in KINDS] + [len(sel)])
    sel = [m for m in miss if sn == "All" or m["suite"] == sn]
    rows.append([f"**{sn}**", "**all**"] + [sum(m["kind"] == k for m in sel) for k in KINDS] + [len(sel)])
W("\n".join(md(hdr, rows)))
wcsv("missed_by_first_tier_counts.csv", hdr, rows)
W("")
hdr = ["program", "suite", "label", "CO", "SC (reports)", "VC (reports)", "kind"]
lrows = [[f"`{m['id']}`", m["suite"], m["label"], m["co"], f"{m['sc']} ({m['scr']})" if m["scr"] is not None else m["sc"],
          f"{m['vc']} ({m['vcr']})" if m["vcr"] is not None else m["vc"], m["kind"]] for m in miss]
wcsv("missed_by_first_tier.csv", ["id", "suite", "label", "CO", "SC", "SC_reports", "VC", "VC_reports", "kind"],
     [[m["id"], m["suite"], m["label"], m["co"], m["sc"], m["scr"], m["vc"], m["vcr"], m["kind"]] for m in miss])
if len(lrows) <= A.max_list:
    W(f"One by one ({len(lrows)}):\n")
    W("\n".join(md(hdr, lrows)))
else:
    W(f"{len(lrows)} programs; first {A.max_list} here, all in `missed_by_first_tier.csv`:\n")
    W("\n".join(md(hdr, lrows[:A.max_list])))
W("\nWhich of these C6b is meant to remove: C6b's definition is not among this analysis's inputs, so this document does not say. The kinds above are the unit to count it in: a change to the collector can only remove the \"SC Race\" and \"CO not finished\" kinds; the \"VC-only Race\" kind is a certificate the run vetoed and sits above the collector.\n")


# ---------------------------------------------------------------- Table 3
W("## 3. Escalation dead ends\n")
W("CO-flagged programs on which a higher tier does not finish: TIMEOUT (at the cap of the surviving row), ERROR (OOM, killed, missing executable, analysis cap), or no row. Counts per mode, then one by one.\n")
dead = []
for i in IDS:
    if V(i, "cuvein", CO) != "RACE": continue
    for mode, mn in ((SC, "scalar-clock"), (VC, "vector-clock")):
        v = V(i, "cuvein", mode)
        if v in ("TIMEOUT", "ERROR", "none"):
            r = run(i, "cuvein", mode) or {}
            dead.append(dict(id=i, suite=PS_NAME[SUITE_OF[i]], label=lab3(i), mode=mn, verdict=v, cap=r.get("cap"), wall=r.get("wall"),
                             peak=r.get("peak"), rc=r.get("rc"), notes=(r.get("notes") or "")[:200]))
hdr = ["suite", "mode", "TIMEOUT", "ERROR", "no row"]
rows = []
for sn in [n for _, n in SUITES] + ["All"]:
    for mn in ("scalar-clock", "vector-clock"):
        sel = [d for d in dead if (sn == "All" or d["suite"] == sn) and d["mode"] == mn]
        if sel: rows.append([sn, mn] + [sum(d["verdict"] == v for d in sel) for v in ("TIMEOUT", "ERROR", "none")])
W("\n".join(md(hdr, rows)))
wcsv("dead_ends_counts.csv", hdr, rows)
W("")
hdr = ["program", "label", "mode", "verdict", "cap (s)", "wall (s)", "peak (GB)", "rc", "notes"]
drows = [[f"`{d['id']}`", d["label"], d["mode"], d["verdict"], fmt(d["cap"], 0), fmt(d["wall"], 1),
          fmt(d["peak"] / 1000, 1) if d["peak"] else "missing", d["rc"], d["notes"].replace("|", "/")] for d in dead]
wcsv("dead_ends.csv", ["id", "suite", "label", "mode", "verdict", "cap", "wall", "peak_mb", "rc", "notes"],
     [[d["id"], d["suite"], d["label"], d["mode"], d["verdict"], d["cap"], d["wall"], d["peak"], d["rc"], d["notes"]] for d in dead])
W("\n".join(md(hdr, drows[:A.max_list])))
if len(drows) > A.max_list: W(f"\n(first {A.max_list} of {len(drows)}; all in `dead_ends.csv`)")
W("")


# ---------------------------------------------------------------- Table 4
W("## 4. Workflow cost\n")
W("Cost of a policy on a program = time spent / native time. Time of a mode run = `wall_s` + `analysis_s`; TIMEOUT counts its cap and ERROR its wall (both **LB**, lower bounds). Policies: **A** CO on all, SC on the CO-flagged; **B** CO on all, VC on the CO-flagged; **C** CO on all, SC on the CO-flagged, VC on what SC still reports. Against: SC on all, VC on all, racecheck, iGUARD. A program enters a policy's mean when every run the policy needs for it has a time and a native; \"n\" is that count. Geometric mean of cost per suite; total machine time = sum of the times over the same programs, in hours. Flag rate = share of the n programs the policy's first tier flags (CO Race; for SC, VC, racecheck, iGUARD: their own Race); reported = share whose final verdict of the policy is Race.\n")


def native_of(i):
    xs = [r["native"] for (j, t, m), r in runs.items() if j == i and r["native"]] if False else NAT.get(i)
    return xs


NAT = {}
for (j, t, m), r in runs.items():
    if r["native"] and t != "supercollider":
        NAT[j] = min(NAT.get(j, r["native"]), r["native"])


def tm(i, tool, mode):
    """-> (seconds, lower_bound) or None"""
    r = run(i, tool, mode)
    if not r or r["wall"] is None and r["verdict"] not in ("TIMEOUT",): return None
    if r["verdict"] == "TIMEOUT":
        t = r["cap"] if r["cap"] else r["wall"]
        return None if t is None else (float(t), True)
    if r["verdict"] == "ERROR":
        return None if r["wall"] is None else (r["wall"], True)
    if tool == "cuvein":
        if r["an"] is None: return None
        return (r["wall"] + r["an"], False)
    return (r["wall"], False)


def policy(i, pol):
    """-> (time, lb, flagged_first, reported) or None"""
    n = NAT.get(i)
    if not n: return None
    if pol in ("SC", "VC", "racecheck", "iGUARD"):
        spec = {"SC": ("cuvein", SC), "VC": ("cuvein", VC), "racecheck": ("racecheck", ""), "iGUARD": ("iguard", "")}[pol]
        t = tm(i, *spec)
        if t is None: return None
        return (t[0], t[1], V(i, *spec) == "RACE", V(i, *spec) == "RACE")
    c = tm(i, "cuvein", CO)
    if c is None: return None
    tot, lb = c
    fl = V(i, "cuvein", CO) == "RACE"
    rep = False
    if fl:
        if pol in ("A", "C"):
            t = tm(i, "cuvein", SC)
            if t is None: return None
            tot += t[0]; lb = lb or t[1]
            rep = V(i, "cuvein", SC) == "RACE"
            if pol == "C" and rep:
                t2 = tm(i, "cuvein", VC)
                if t2 is None: return None
                tot += t2[0]; lb = lb or t2[1]
                rep = V(i, "cuvein", VC) == "RACE"
        else:
            t = tm(i, "cuvein", VC)
            if t is None: return None
            tot += t[0]; lb = lb or t[1]
            rep = V(i, "cuvein", VC) == "RACE"
    return (tot, lb, fl, rep)


POLS = [("A: CO, then SC on flagged", "A"), ("B: CO, then VC on flagged", "B"), ("C: CO, SC on flagged, VC on SC's Race", "C"),
        ("scalar-clock on all", "SC"), ("vector-clock on all", "VC"), ("racecheck on all", "racecheck"), ("iGUARD on all", "iGUARD")]
SUBSETS = [(n, IDS_BY[p]) for p, n in SUITES]
SUBSETS += [("**All (8 suites)**", IDS), ("All labelled (6 suites)", [i for p in LAB6 for i in IDS_BY[p]]),
            ("**Race-free-labelled (all suites)**", [i for i in IDS if lab3(i) == "race-free"]),
            ("**HeCBench (P7 + P9)**", IDS_BY["P7"] + IDS_BY["P9"])]
cost_rows, cost_csv = [], []
hdr = ["subset", "policy", "n", "flag rate", "reported Race", "geomean cost (×native)", "total machine time (h)", "programs with an LB component"]
for sname, sids in SUBSETS:
    for pname, pol in POLS:
        res = [(i, policy(i, pol)) for i in sids]
        ok = [(i, r) for i, r in res if r]
        costs = [r[0] / NAT[i] for i, r in ok]
        hrs = sum(r[0] for _, r in ok) / 3600
        nl = sum(1 for _, r in ok if r[1])
        cost_rows.append([sname, pname, f"{len(ok):,} of {len(sids):,}", pct(sum(r[2] for _, r in ok), len(ok)), pct(sum(r[3] for _, r in ok), len(ok)),
                          fmt(gm(costs), 2), fmt(hrs, 2), nl])
        cost_csv.append([sname.replace("*", ""), pol, len(ok), len(sids), sum(r[2] for _, r in ok), sum(r[3] for _, r in ok), gm(costs), hrs, nl])
W("\n".join(md(hdr, cost_rows)))
wcsv("workflow_cost.csv", ["subset", "policy", "n", "subset_size", "first_tier_flagged", "reported_race", "geomean_cost", "total_hours", "lb_programs"], cost_csv)
W("")
# programs excluded from a policy (a needed run has no time)
exc = collections.Counter()
for p, n in SUITES:
    for pname, pol in POLS:
        exc[(n, pol)] = sum(1 for i in IDS_BY[p] if not policy(i, pol))
W("Programs left out of a policy because a run it needs has no row / no time / no native (suite × policy; zero cells omitted): " +
  ("; ".join(f"{n} {pol} {c}" for (n, pol), c in exc.items() if c) or "none") + ".\n")


lbs = []
for i in IDS:
    for pol, spec in (("scalar-clock", ("cuvein", SC)), ("vector-clock", ("cuvein", VC)), ("racecheck", ("racecheck", "")), ("iGUARD", ("iguard", ""))):
        t = tm(i, *spec)
        if t and t[1]:
            r = run(i, *spec)
            lbs.append([f"`{i}`", pol, r["verdict"], fmt(t[0], 1), fmt(NAT.get(i), 2)])
W("Lower-bound runs (TIMEOUT counted at its cap, ERROR at its wall) among the single-tool rows:\n")
W("\n".join(md(["program", "tool", "verdict", "time counted (s)", "native (s)"], lbs)))
W("")

# ---------------------------------------------------------------- Table 5: check lines
W("## 5. Check lines\n")
W("Per-suite slowdowns recomputed with CAP's rule (tool wall / native wall, `make_tables._ratios`: id-level native = minimum over the non-SuperCollider runners, collector-only divides by the smaller of its own and that; a row re-run in X7 Part B divides by its own native and a row that stayed keeps the id-level native of the state before the merge, `cap-old-cells.json`; geometric mean over the tool's finished programs), against `cells.json` of `eval/results/cap-84600/tables/new` (the source of `CAP_84600.md` section 3's run-only column and Figure 6's cells) and against the coordinates of Figure `fig:eval-slowdown` in `cuRacePaper` `figures/fig_slowdown.tex` (origin/main).\n")
old = json.load(open(P("cap-old-cells.json")))["native_id"]
newk = {tuple(k) for k in json.load(open(P("cap-newkeys.json")))}
nat_id, nat_co = {}, {}
for (i, t, m), r in runs_cap.items():
    if r["native"] and t != "supercollider":
        d = nat_co if (t == "cuvein" and m == CO) else nat_id
        d[i] = min(d.get(i, r["native"]), r["native"])
rat = {}
for k, r in runs_cap.items():
    if not r["wall"]: continue
    i, t, m = k
    if k in newk:
        if r["native"]: rat[k] = r["wall"] / r["native"]
    elif t != "supercollider" and i in old:
        a, b = old[i]
        n = (min(x for x in (a, b) if x) if (t == "cuvein" and m == CO and (a or b)) else a)
        if n: rat[k] = r["wall"] / n
SL = [("Indigo3", ("P1",)), ("Indigo 1.3", ("PI",)), ("ECL", ("P3",)), ("ScoR apps", ("P4",)), ("ScoR litmus", ("P5",)), ("cuHadron", ("P6",)),
      ("HeCBench other 14", ("P7",)), ("HeCBench SC 10", ("P9",)), ("All", LAB6)]
cells = json.load(open(P("cap-cells.json")))
figtex = open(P("fig_slowdown.tex")).read()
fig = {}
for legend, coords in zip(re.findall(r"\\addlegendentry\{([^}]*)\}", figtex), re.findall(r"\\addplot\[[^\]]*\]\s*coordinates\s*\{([^}]*)\}", figtex)):
    fig[legend] = {a: float(b) for a, b in re.findall(r"\(([^,)]+),([0-9.,]+)\)", coords.replace(",", ",", 0))}
FIGNAME = {("cuvein", VC): "cuRace, vector-clock", ("cuvein", SC): "cuRace, scalar-clock", ("racecheck", ""): "racecheck", ("iguard", ""): "iGUARD"}
TOOLS = [("cuvein", VC), ("cuvein", SC), ("racecheck", ""), ("iguard", "")]
hdr = ["suite", "tool", "recomputed geomean (n)", "cells.json (n)", "Figure 4 bar", "recomputed = cells.json (n, 1e-9)", "rounds to the bar (1 decimal)"]
rows, bad = [], 0
for sn, ps in SL:
    for tk in TOOLS:
        xs = [x for k, x in rat.items() if k[1:] == tk and meta_cap[k[0]][0] in ps and runs_cap[k]["verdict"] in ("RACE", "CLEAN")]
        g = gm(xs); n = len(xs)
        cj = cells["fig"].get(f"{sn}|{tk[0]}/{tk[1]}")
        bar = fig.get(FIGNAME[tk], {}).get(sn)
        same = bool(cj) and cj[0] == n and g is not None and abs(cj[1] - g) < 1e-9
        rnd = None if bar is None or g is None else (f"{g:.1f}" == f"{bar:.1f}" or (bar >= 1000 and f"{g:,.1f}" == f"{bar:,.1f}"))
        bad += (not same) + (rnd is False)
        rows.append([sn, FIGNAME[tk], f"{g:,.3f} ({n})" if g else "missing", f"{cj[1]:,.3f} ({cj[0]})" if cj else "missing",
                     f"{bar:,}" if bar is not None else "missing", "yes" if same else "**no**", "n/a" if rnd is None else ("yes" if rnd else "**no**")])
W("\n".join(md(hdr, rows)))
wcsv("check_slowdowns.csv", hdr, rows)
W(f"\nRows that do not recompute to cells.json or do not round to the figure's bar: **{bad}** of {len(rows)}.\n")
# CAP_84600.md section 3 (run only / end-to-end), cuRace modes
doc = open(P("CAP_84600.md")).read()
docrows = {}
for m in re.finditer(r"^\| ([^|]+) \| (vector-clock|scalar-clock|collector-only) \| ([0-9,.]+) \((\d+)\) \| ([0-9,.]+) \((\d+)\) \| ([0-9,.]+) \((\d+)\) \|", doc, re.M):
    docrows[(m.group(1).strip(), m.group(2))] = (float(m.group(3).replace(",", "")), int(m.group(4)), float(m.group(5).replace(",", "")), float(m.group(7).replace(",", "")))
hdr = ["suite", "mode", "run only: recomputed (n)", "CAP_84600.md §3", "verdict step: recomputed", "§3", "end-to-end: recomputed", "§3", "all three agree to the 3 decimals printed"]
rows, bad2 = [], 0
for sn, ps in SL:
    for mode in (VC, SC):
        runv, ver, e2e = [], [], []
        for i in [j for p in ps for j in IDS_BY[p]] + [j for j in meta_cap if meta_cap[j][0] in ps and j not in set(IDS)]:
            k = (i, "cuvein", mode)
            r = runs_cap.get(k)
            if not r or r["verdict"] not in ("RACE", "CLEAN") or k not in rat: continue
            nat = r["wall"] / rat[k]
            runv.append(r["wall"] / nat)
            if r["an"] is not None:
                ver.append(max(r["an"], 1e-3) / nat); e2e.append((r["wall"] + r["an"]) / nat)
        d = docrows.get((sn if sn != "All" else "All", mode))
        okk = d and round(gm(runv), 3) == d[0] and len(runv) == d[1] and round(gm(e2e), 3) == d[3]
        bad2 += not okk
        rows.append([sn, mode, f"{gm(runv):,.3f} ({len(runv)})", f"{d[0]:,.3f} ({d[1]})" if d else "missing", f"{gm(ver):,.3f}", f"{d[2]:,.3f}" if d else "missing",
                     f"{gm(e2e):,.3f}", f"{d[3]:,.3f}" if d else "missing", "yes" if okk else "**no**"])
W("\n".join(md(hdr, rows)))
W(f"\nRows that disagree with `CAP_84600.md` section 3: **{bad2}** of {len(rows)}.\n")
wcsv("check_cap_section3.csv", hdr, rows)

# ---------------------------------------------------------------- headline, inserted after the first two lines
_all = units(ALL_PS)
_fl = [u for u in _all if u["co"] == "RACE"]
_rf = [u for u in _fl if u["label"] == "race-free"]
_costs = {}
for pol in ("A", "SC", "iGUARD"):
    rs = [(i, policy(i, pol)) for i in IDS]
    rs = [(i, r) for i, r in rs if r]
    _costs[pol] = (gm([r[0] / NAT[i] for i, r in rs]), sum(r[0] for _, r in rs) / 3600)
H = ["## Headline (all programs, 8 suites)\n",
     f"- Over-all flag rate of the first tier: {len(_fl):,} of {len(_all):,} programs ({pct(len(_fl), len(_all))}); {sum(u['co'] == 'CLEAN' for u in _all):,} Clean, {sum(u['co'] == 'TIMEOUT' for u in _all)} TIMEOUT, {sum(u['co'] == 'ERROR' for u in _all)} ERROR, {sum(u['co'] == 'none' for u in _all)} without a row.",
     f"- Race-free-labelled programs flagged: {len(_rf)}; scalar-clock clears {sum(u['sc'] == 'CLEAN' for u in _rf)} of them (still Race {sum(u['sc'] == 'RACE' for u in _rf)}, not finished {sum(u['sc'] not in ('RACE', 'CLEAN') for u in _rf)}); vector-clock clears {sum(u['vc'] == 'CLEAN' for u in _rf)}.",
     f"- Missed by the first tier: {len(miss)} programs (" + ", ".join(f"{sum(m['kind'] == k for m in miss)} {k}" for k in KINDS) + ").",
     f"- Policy A over all: geomean cost {_costs['A'][0]:.2f}x native, {_costs['A'][1]:.2f} h machine time; scalar-clock on all {_costs['SC'][0]:.2f}x, {_costs['SC'][1]:.2f} h; iGUARD {_costs['iGUARD'][0]:.2f}x, {_costs['iGUARD'][1]:.2f} h (section 4 has the other subsets and policies).",
     ""]
out[2:2] = H

open(A.out, "w").write("\n".join(out) + "\n")
print(f"wrote {A.out}: {len(IDS)} programs, {len(miss)} missed by the first tier, {len(dead)} dead-end rows; check rows off: {bad} + {bad2}")
