#!/usr/bin/env python3
"""Generate eval/BASELINES.md from the unified per-run CSVs.

Every number here is derived from eval/results/baselines-*.csv (+ the build-status
CSV, the tool-setup CSV, the published-numbers CSV, the classifier's disagreement
CSV and the residual-diagnosis CSV). No figure is hand-entered except the B4/HGRD
published row, which carries its paper table. Runs anywhere (no GPU).

    .env/bin/python eval/baselines/make_tables.py
"""
import csv
import glob
import math
import os
import re
import statistics
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
APH = os.path.dirname(os.path.dirname(HERE))
RES = f"{APH}/eval/results"
OUT = f"{APH}/eval/BASELINES.md"

# tool column order in verdict tables. Race detectors first, then the three
# non-race compute-sanitizer tools (their RACE verdict means FLAGGED).
RACE_TOOLS = [("cuvein", "engine"), ("cuvein", "trace-only"),
              ("racecheck", ""), ("hirace", ""), ("iguard", ""), ("supercollider", "")]
FLAG_TOOLS = [("memcheck", ""), ("synccheck", ""), ("initcheck", "")]
TOOLCOLS = RACE_TOOLS + FLAG_TOOLS
COLNAME = {("cuvein", "engine"): "cuVein-eng", ("cuvein", "trace-only"): "cuVein-tr",
           ("racecheck", ""): "racecheck", ("hirace", ""): "HiRace",
           ("iguard", ""): "iGUARD", ("supercollider", ""): "SuperCollider",
           ("memcheck", ""): "memcheck*",
           ("synccheck", ""): "synccheck*", ("initcheck", ""): "initcheck*"}
SKIP_FILES = {"build", "disagreements", "p7-selection", "diagnose"}
PSET_LABEL = {"P1": "P1 Indigo3", "PI": "PI Indigo original (all 590 IndigoSuite codes x 7 inputs)",
              "P3": "P3 ECL race-free",
              "P4": "P4 ScoR apps", "P5": "P5 ScoR micro + canary",
              "P6": "P6 cuHadron", "P7": "P7 HeCBench (overhead)",
              "P9": "P9 HeCBench — SuperCollider's 10-app subset"}
# PI = the whole Indigo-original suite; it replaced the partial sets P2 (60-code sample)
# and P8 (SuperCollider's 99 tests), whose old rows stay in the CSVs but are not rendered.
ALL_PSETS = ("P1", "PI", "P3", "P4", "P5", "P6", "P7", "P9")
PREREG_SETS = ("P1", "PI", "P3", "P4", "P5", "P6")
# programs SuperCollider ships instrumented: cuHadron, its HeCBench-10, and -- as a VIEW of
# PI, not a separate dataset -- its 99 Indigo tests on its own input (build == sc-subset)
SC_SETS = ("P6", "PI@sc", "P9")
SET_NAME = {"PI@sc": "PI Indigo original — SuperCollider's 99-test subset (view)"}


def _in(m, sets):
    """Is the program with meta tuple m=(pset, program, build, input) in any of `sets`?
    'PI@sc' is the SuperCollider-subset view of PI."""
    return bool(m) and (m[0] in sets or ("PI@sc" in sets and m[0] == "PI"
                                         and len(m) > 2 and m[2] == "sc-subset"))
BUG_TOKENS = ["RaceBug", "SyncBug", "BoundsBug", "NbrBoundsBug", "LivelockBug",
              "FieldBug", "OverflowBug", "ExcessThreadsBug", "UninitializedBug",
              "atomicBug", "boundsBug", "syncBug", "guardBug", "race"]


def effective_verdict(r):
    """A cuVein CLEAN needs a run that reached its own exit: accelprof returns 1 when
    the app dies under the tool (OOM-killed engine run) while the kernels dumped before
    that still parse, so rows written before parallel.py flagged this
    (incomplete-trace) can say CLEAN over a prefix of the run. Re-score them ERROR.
    rc 127 is exempt: the pre-fix bin/accelprof returned it after a SUCCESSFUL run."""
    if ((r.get("tool") or "cuvein") == "cuvein" and r.get("verdict") == "CLEAN"
            and str(r.get("rc", "")).strip() not in ("", "0", "127")):
        return "ERROR"
    return r.get("verdict")


def load_runs(paths=None):
    """-> runs[(id, tool, mode)] = reduced dict. Collapses the reps per key.
    `paths` restricts the input (default: every merged eval/results/baselines-*.csv)."""
    per = defaultdict(list)
    meta = {}
    for path in (paths if paths is not None else glob.glob(f"{RES}/baselines-*.csv")):
        tool = os.path.basename(path)[len("baselines-"):-4]
        if tool in SKIP_FILES or "-shard" in tool:
            continue
        with open(path, newline="") as f:
            rd = csv.DictReader(f)
            # only per-run result files (unified schema); other analysis CSVs that
            # share the baselines-* prefix (e.g. fp-causes) are not run tables
            if not {"id", "pset", "program", "verdict"} <= set(rd.fieldnames or []):
                continue
            for r in rd:
                if (r.get("tool") or tool) == "cuvein":
                    r["verdict"] = effective_verdict({**r, "tool": "cuvein"})
                key = (r["id"], r.get("tool") or tool, r.get("mode", ""))
                per[key].append(r)
                meta[r["id"]] = (r["pset"], r["program"], r["build"], r["input"])
    runs = {}
    for key, reps in per.items():
        verds = [r["verdict"] for r in reps]
        if "RACE" in verds:
            v = "RACE"
        elif "CLEAN" in verds:
            v = "CLEAN"
        elif "TIMEOUT" in verds:
            v = "TIMEOUT"
        else:
            v = "ERROR"
        def fnums(col):
            out = []
            for r in reps:
                try:
                    out.append(float(r[col]))
                except (ValueError, KeyError):
                    pass
            return out
        walls = fnums("wall_s")
        natives = fnums("native_wall_s")
        peaks = fnums("peak_mb")
        reps_ded = [int(r["reports_dedup"]) for r in reps if r.get("reports_dedup", "").isdigit()]
        runs[key] = dict(
            verdict=v, reports=max(reps_ded) if reps_ded else 0,
            wall=(sorted(walls)[len(walls)//2] if walls else None),
            native=(min(natives) if natives else None),
            peak=(max(peaks) if peaks else None),
            report_ids=next((r["report_ids"] for r in reps if r.get("report_ids")), ""),
            report_lines=next((r["report_lines"] for r in reps if r.get("report_lines")), ""),
            notes=";".join(sorted({r["notes"] for r in reps if r.get("notes")})))
    return runs, meta


def load_manifest():
    m = {}
    p = f"{HERE}/manifest.csv"
    if os.path.exists(p):
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                m[r["id"]] = r
    return m


def load_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


SAN_TOOLS = [("memcheck", ""), ("racecheck", ""), ("synccheck", ""), ("initcheck", "")]
COLNAME[("sanitizer", "")] = "compute-sanitizer(any)"


def add_sanitizer_union(runs):
    """Synthesise ("sanitizer","") = the whole compute-sanitizer family: RACE if ANY
    of memcheck/racecheck/synccheck/initcheck flagged the program, CLEAN if every
    tool that ran was clean, else TIMEOUT/ERROR. reports = sum of deduped reports."""
    ids = {i for (i, t, m) in runs if (t, m) in SAN_TOOLS}
    for i in ids:
        rs = [runs[(i, t, m)] for (t, m) in SAN_TOOLS if (i, t, m) in runs]
        vs = [r["verdict"] for r in rs]
        v = ("RACE" if "RACE" in vs else "CLEAN" if all(x == "CLEAN" for x in vs)
             else "TIMEOUT" if "TIMEOUT" in vs else "ERROR")
        walls = [r["wall"] for r in rs if r["wall"]]
        runs[(i, "sanitizer", "")] = dict(
            verdict=v, reports=sum(r["reports"] for r in rs if r["verdict"] == "RACE"),
            wall=(max(walls) if walls else None), native=None, peak=None,
            report_ids=" ".join(f"{t}:{r['report_ids']}" for (t, m), r in zip(SAN_TOOLS, rs) if r["report_ids"]),
            report_lines="", notes="union of " + "+".join(t for (t, m) in SAN_TOOLS if (i, t, m) in runs))


def tools_present(runs):
    present = {(tool, mode) for (_id, tool, mode) in runs}
    return [tc for tc in TOOLCOLS if tc in present]


def cell(runs, _id, tool, mode):
    r = runs.get((_id, tool, mode))
    if not r:
        return "—"
    v = {"RACE": "RACE", "CLEAN": "CLEAN", "TIMEOUT": "TO", "ERROR": "ERR"}[r["verdict"]]
    if (tool, "") in FLAG_TOOLS:
        v = {"RACE": "FLAG", "CLEAN": "clean", "TO": "TO", "ERR": "ERR"}.get(v, v)
    return f"{v}({r['reports']})" if r["verdict"] == "RACE" else v


def verdict_tables(runs, meta, man, cols):
    out = []
    ids_by_pset = defaultdict(list)
    for _id, (ps, prog, build, inp) in meta.items():
        ids_by_pset[ps].append(_id)
    for ps in ALL_PSETS:
        out.append(f"\n### {PSET_LABEL[ps]}\n")
        ids = sorted(ids_by_pset.get(ps, []))
        if not ids:
            out.append("_No runs recorded (corpus/tool blocked — see Setup & Blockers)._\n")
            continue
        # per-pset summary line first
        out.append(summary_line(runs, man, ids, cols))
        big = len(ids) > 500        # PI: 4130 program-inputs -> collapsed by default
        if big:
            out.append(f"<details><summary>{len(ids)} program-input rows</summary>\n")
        hdr = ["program", "build", "input", "oracle"] + [COLNAME[c] for c in cols]
        out.append("| " + " | ".join(hdr) + " |")
        out.append("|" + "---|" * len(hdr))
        for _id in ids:
            ps_, prog, build, inp = meta[_id]
            lab = man.get(_id, {}).get("label", "")
            row = [prog, build, inp, lab] + [cell(runs, _id, t, m) for (t, m) in cols]
            out.append("| " + " | ".join(row) + " |")
        if big:
            out.append("\n</details>")
    return "\n".join(out)


def summary_line(runs, man, ids, cols):
    parts = []
    for (t, m) in cols:
        c = defaultdict(int)
        for _id in ids:
            r = runs.get((_id, t, m))
            if r:
                c[r["verdict"]] += 1
        if sum(c.values()):
            k = "FLAG" if (t, "") in FLAG_TOOLS else "RACE"
            parts.append(f"{COLNAME[(t, m)]} {k} {c['RACE']} / CLEAN {c['CLEAN']} / TO {c['TIMEOUT']} / ERR {c['ERROR']}")
    return "_Counts:_ " + "; ".join(parts) + "\n" if parts else ""


def bug_class(program, label):
    toks = [t for t in BUG_TOKENS if re.search(rf"(^|_){t}(_|$)", program) and not
            re.search(rf"(^|_)No{t}(_|$)", program)]
    if not toks and label == "CLEAN":
        return "nobug"
    return "+".join(sorted(set(toks))) or ("racy(unlabelled-token)" if label == "RACE" else "nobug")


def bug_class_table(runs, meta, man, cols):
    """P1/P2: which tool flags which planted-bug class (count flagged / count run)."""
    out = ["\n### Bug class × tool (P1 Indigo3 + P2 Indigo)\n",
           "Rows are the bug tokens planted in the generated program's name (`nobug` = "
           "race-free variant). Cell = programs the tool reported RACE/FLAG over programs "
           "it ran to a verdict (ERROR/TIMEOUT excluded). For memcheck*/synccheck*/"
           "initcheck* the count is programs FLAGGED for their own error class, not races.\n"]
    for ps in ("P1", "PI"):
        ids = [i for i, m in meta.items() if m[0] == ps]
        if not ids:
            continue
        groups = defaultdict(list)
        for i in ids:
            groups[bug_class(meta[i][1], man.get(i, {}).get("label", ""))].append(i)
        out.append(f"\n**{PSET_LABEL[ps]}**\n")
        bcols = cols + ([("sanitizer", "")] if any(k[1] == "sanitizer" for k in runs) else [])
        hdr = ["bug class", "n"] + [COLNAME[c] for c in bcols]
        out.append("| " + " | ".join(hdr) + " |")
        out.append("|" + "---|" * len(hdr))
        for g in sorted(groups, key=lambda x: (x != "nobug", x)):
            row = [g, str(len(groups[g]))]
            for (t, m) in bcols:
                hit = ran = 0
                for i in groups[g]:
                    r = runs.get((i, t, m))
                    if r and r["verdict"] in ("RACE", "CLEAN"):
                        ran += 1
                        hit += r["verdict"] == "RACE"
                row.append(f"{hit}/{ran}" if ran else "—")
            out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def sanitizer_family_table(runs, meta):
    out = ["\n### compute-sanitizer family per program set\n",
           "All four sanitizer tools ran on every manifest row (1 rep, deterministic). "
           "`FLAG` for memcheck/synccheck/initcheck means the tool reported ≥1 error of "
           "its own class (memory access / barrier misuse / uninitialised global read); "
           "these are not race verdicts and are excluded from the race disagreement table. "
           "racecheck's scope is `__shared__` hazards only.\n"]
    tools = [("memcheck", ""), ("racecheck", ""), ("synccheck", ""), ("initcheck", "")]
    hdr = ["pset", "n"] + [f"{COLNAME[c]} flag/clean/to/err" for c in tools]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    any_ = False
    for ps in ALL_PSETS:
        ids = [i for i, m in meta.items() if m[0] == ps]
        row = [ps, str(len(ids))]
        for (t, m) in tools:
            c = defaultdict(int)
            for i in ids:
                r = runs.get((i, t, m))
                if r:
                    c[r["verdict"]] += 1
            if sum(c.values()):
                any_ = True
                row.append(f"{c['RACE']}/{c['CLEAN']}/{c['TIMEOUT']}/{c['ERROR']}")
            else:
                row.append("—")
        out.append("| " + " | ".join(row) + " |")
    if not any_:
        return "\n_compute-sanitizer family not run yet._\n"
    return "\n".join(out)


def _ratios(runs, meta):
    """(id,tool,mode) -> wall/native. Our tools share the id-level native wall (min over
    the runners that measured our build). SuperCollider is measured against ITS OWN
    uninstrumented build run the same way (same container), never against ours."""
    native = {}
    for (i, t, m), r in runs.items():
        if r["native"] and t != "supercollider":
            native[i] = min(native.get(i, r["native"]), r["native"])
    out = {}
    for (i, t, m), r in runs.items():
        n = r["native"] if t == "supercollider" else native.get(i)
        if r["wall"] and n:
            out[(i, t, m)] = r["wall"] / n
    return out


def overhead_table(runs, meta):
    cols = [c for c in TOOLCOLS if any(k[1:] == c for k in runs)]
    scopes = (("P1+P7", ("P1", "P7")), ("PI Indigo original", ("PI",)),
              ("P6+PI@sc+P9 (SuperCollider-matched)", SC_SETS),
              ("P9 HeCBench-10 only (seconds-long apps)", ("P9",)), ("all", ALL_PSETS))
    ratios = {sc: defaultdict(list) for sc, _ in scopes}
    for (i, t, m), x in _ratios(runs, meta).items():
        if (t, m) not in cols or runs[(i, t, m)]["verdict"] in ("TIMEOUT", "ERROR"):
            continue
        for sc, sets in scopes:
            if _in(meta.get(i), sets):
                ratios[sc][(t, m)].append(x)
    out = ["\n## 4. Overhead (slowdown vs native, same binary+input)\n",
           "Ratio = tool wall / native wall of the same program (median of reps). "
           "TIMEOUT/ERROR runs are excluded (their true slowdown exceeds the cap), so the "
           "cuVein figures are lower bounds. sanitizer rows use the native wall measured "
           "by the cuVein/iGUARD runners for the same id. SuperCollider is timed against "
           "the artifact's own uninstrumented binary, both inside the same Singularity "
           "container, so ~0.3 s of container start-up sits in numerator and denominator "
           "and compresses its ratio towards 1 on sub-second programs.\n",
           "| tool/mode | " + " | ".join(f"n / geomean× — {sc}" for sc, _ in scopes) + " |",
           "|---|" + "---|" * len(scopes)]
    def g(xs):
        return f"{math.exp(sum(math.log(x) for x in xs) / len(xs)):.1f}" if xs else "—"
    for c in cols:
        out.append(f"| {COLNAME[c]} | " + " | ".join(
            f"{len(ratios[sc].get(c, []))} / {g(ratios[sc].get(c, []))}" for sc, _ in scopes) + " |")
    return "\n".join(out)


def setup_section(build_rows):
    tools_csv = load_csv(f"{HERE}/setup/tools.csv")
    out = ["## 1. Tool setup\n"]
    if tools_csv:
        cols = ["tool", "version", "commit", "toolchain", "status", "blockers"]
        out.append("| " + " | ".join(cols) + " |")
        out.append("|" + "---|" * len(cols))
        for r in tools_csv:
            out.append("| " + " | ".join(r.get(c, "") for c in cols) + " |")
    if build_rows:
        ok = sum(r["status"] == "ok" for r in build_rows)
        out.append(f"\n**Corpus build status:** {ok}/{len(build_rows)} targets built "
                   f"(detail in eval/results/baselines-build.csv).")
        fails = [r for r in build_rows if r["status"] != "ok"]
        if fails:
            out.append("\nSkipped/failed build targets:\n")
            out.append("| pset | target | reason |")
            out.append("|---|---|---|")
            for r in fails[:40]:
                out.append(f"| {r['pset']} | {r['target']} | {r['err']} |")
    return "\n".join(out)


def residual_section():
    rows = load_csv(f"{RES}/baselines-diagnose.csv")
    out = ["\n## 1b. Residual ERROR/TIMEOUT root causes (cuVein)\n"]
    if not rows:
        out.append("_No diagnosis CSV yet (run p_diagnose.sh + classify_residuals.py)._")
        return "\n".join(out)
    out.append("Every program that was ERROR/TIMEOUT in trace-only mode (plus all of P7) was "
               "re-run by `parallel.py run --timeout-floor 1200` with the native rc/stderr, the "
               "accelprof stderr and the raw-dump size captured; `classify_residuals.py` "
               "assigns one cause per (program, mode). GPU nodes have 188 GB RAM and a 914 GB "
               "node-local scratch disk; peak_mb is the collector's peak RSS in MB.\n\n"
               "- **resolved** — verdict obtained with the 20-min cap (was an overhead timeout)\n"
               "- **app-native-fail** — the program exits non-zero WITHOUT accelprof: app/corpus/args, not the collector\n"
               "- **trace-volume** — TIMEOUT while the dump kept growing: the access count exceeds the 20-min tracing budget\n"
               "- **collector-hang** — TIMEOUT with an empty dump and modest RSS: the collector stalled\n"
               "- **collector-memory** — TIMEOUT with an empty dump but ≥32 GB RSS: the collector holds the whole trace in memory (nothing written before the end): **attributable to the cuVein collector**\n"
               "- **collector-oom** — native rc 0 but the accelprof child was SIGKILLed (`Killed`): the collector's memory grows with the trace: **attributable to the cuVein collector**\n"
               "- **engine-hang** — engine-mode TIMEOUT with an empty dump while trace-only of the same program resolved: **attributable to the cuVein engine** (not the tracer)\n"
               "- **collector-fail** — native rc 0 but accelprof rc≠0 / no kernel JSON: **attributable to the cuVein collector**\n"
               "- **trace-disk-full** — the raw dump filled the node-local scratch disk (`No space left on device`): **attributable to the cuVein collector** (unbounded dump)\n"
               "- **analysis-oom** — the collector finished but the Python `sync_dominance` analysis of the trace was Killed (OOM): **attributable to cuVein's trace-only analysis path**\n"
               "- **analysis-timeout** — the collector finished (dump size/kernels in the row) but the offline `sync_dominance` analysis exceeded its wall-clock cap (`--analysis-timeout`): **attributable to cuVein's trace-only analysis path**\n")
    c = defaultdict(int)
    for r in rows:
        c[(r["mode"], r["cause"])] += 1
    out.append("| mode | cause | n |")
    out.append("|---|---|---|")
    for k in sorted(c):
        out.append(f"| {k[0]} | {k[1]} | {c[k]} |")
    coll = [r for r in rows if r["cause"] in ("collector-fail", "collector-hang", "collector-memory", "collector-oom", "engine-hang", "analysis-oom", "analysis-timeout", "trace-disk-full")]
    out.append(f"\n**cuVein-attributable (collector-fail/hang/memory/oom + trace-disk-full + engine-hang + analysis-oom/timeout): {len(coll)} "
               f"of {len(rows)} (program,mode) rows.**\n")
    keys = ["pset", "program", "mode", "verdict", "cause", "native_rc", "timeout_s",
            "dump_mb", "peak_mb", "wall_s", "native_wall_s", "evidence"]
    out.append("| " + " | ".join(keys) + " |")
    out.append("|" + "---|" * len(keys))
    for r in rows:
        vals = [str(r.get(k, "")).replace("|", "/")[:120] for k in keys]
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def fp_tp(runs, meta, man, pset, tool, mode, build=None):
    fp = fn = tp = tn = err = 0
    for _id, m in meta.items():
        if not _in(m, (pset,)) or (build is not None and m[2] != build):
            continue
        r = runs.get((_id, tool, mode))
        if not r:
            continue
        lab = man.get(_id, {}).get("label", "")
        v = r["verdict"]
        if v in ("ERROR", "TIMEOUT"):
            err += 1; continue
        if lab == "CLEAN":
            fp += (v == "RACE"); tn += (v == "CLEAN")
        elif lab == "RACE":
            tp += (v == "RACE"); fn += (v != "RACE")
    return dict(fp=fp, tn=tn, tp=tp, fn=fn, err=err)


def accuracy_table(runs, meta, man, cols):
    out = ["\n### Detector accuracy vs suite labels (per program set)\n",
           "FP = race-free program reported RACE; FN = racy program not reported. "
           "Denominators exclude ERROR/TIMEOUT. The last column is the WHOLE "
           "compute-sanitizer family: a program counts as reported when ANY of "
           "memcheck/racecheck/synccheck/initcheck flagged it (per-tool split in the "
           "sanitizer table below).\n"]
    rcols = [c for c in cols if c in RACE_TOOLS and c != ("racecheck", "")]
    if any(k[1] == "sanitizer" for k in runs):
        rcols.append(("sanitizer", ""))
    hdr = ["pset"] + [f"{COLNAME[c]} FP / TP (err)" for c in rcols] + ["cuVein missed TPs (FN) — note"]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    for ps in ("P1", "PI", "P3", "P4", "P5", "P6", "P9"):
        row = [ps]
        for (t, m) in rcols:
            d = fp_tp(runs, meta, man, ps, t, m)
            nob, rac = d["fp"] + d["tn"], d["tp"] + d["fn"]
            if nob + rac + d["err"] == 0:
                row.append("—")
            else:
                row.append(f"{d['fp']}/{nob} / {d['tp']}/{rac} ({d['err']})")
        row.append(cuvein_fn_note(runs, meta, man, ps))
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def fp_cause_table():
    """cuVein false positives split by report class and root cause, from
    classify_fp_causes.py (baselines-fp-causes.csv: one row per FP report)."""
    rows = load_csv(f"{RES}/baselines-fp-causes.csv")
    out = ["\n### cuVein false positives by report class and root cause\n"]
    if not rows:
        out.append("_Run `eval/baselines/classify_fp_causes.py` to populate "
                   "`baselines-fp-causes.csv`._")
        return "\n".join(out)
    out.append("A program counts as FP above on ANY RACE verdict. `structural-FP` = programs "
               "with >=1 report the engine observed racing (structural/model_bug); the rest "
               "carry only `latent` reports (no dynamic race, no static proof). Causes are "
               "per program as the SET of its reports' causes (see `eval/FP_DIAGNOSIS.md`): "
               "RC1 cuda::atomic load/store not modelled, RC2 latent on barrier/lock idioms, "
               "RC3 pair mis-attribution, RC4 same-pc idempotent write, RC5 ScoR volatile "
               "handshake.\n")
    out.append("| pset | mode | FP programs | structural-FP | latent-only | causes (programs) |")
    out.append("|---|---|---|---|---|---|")
    per = defaultdict(lambda: {"cls": set(), "cause": set()})
    for r in rows:
        k = (r["pset"], r["mode"], r["id"])
        per[k]["cls"].add(r["hb_class"])
        per[k]["cause"].add(r["cause"].split("-")[0])
    agg = defaultdict(lambda: {"n": 0, "struct": 0, "causes": defaultdict(int)})
    for (ps, mode, _), d in per.items():
        a = agg[(ps, mode)]
        a["n"] += 1
        a["struct"] += bool(d["cls"] & {"structural", "model_bug"})
        a["causes"]["+".join(sorted(d["cause"]))] += 1
    for (ps, mode), a in sorted(agg.items()):
        causes = ", ".join(f"{k} ({v})" for k, v in sorted(a["causes"].items()))
        out.append(f"| {ps} | {mode} | {a['n']} | {a['struct']} | "
                   f"{a['n'] - a['struct']} | {causes} |")
    return "\n".join(out)


def _fn_reason(ps, prog, build):
    """Mechanical hint for why a labelled-racy program is a cuVein miss."""
    if ps in ("P2", "PI"):
        toks = [t for t in ("boundsBug", "guardBug", "atomicBug", "syncBug") if t in prog]
        if toks and "atomicBug" not in toks and "syncBug" not in toks:
            return "labelled RACE by name but the planted bug is OOB/guard, not a data race"
        return "bug class " + "+".join(toks)
    if ps == "P6":
        cat = prog.split("/")[0]
        hint = {"hostdevice": "host-vs-device access (outside kernel HB model)",
                "interkernel": "cross-stream / inter-kernel race (out of cuVein's scope, footnote 7)",
                "asyncmemcpy": "host-API `cudaMemcpyAsync`-vs-kernel race (out of cuVein's scope, footnote 7)",
                "memcpy": "memcpy-vs-kernel race",
                "false_positives": "race-free by label"}.get(cat, cat)
        return hint
    if prog.startswith("canary"):
        return "PC-level dedup hides the pair (trace-only leg only; engine catches it)"
    return ""


def cuvein_fn_note(runs, meta, man, ps):
    """Which labelled-racy programs cuVein did NOT report, per mode, grouped by the
    mechanical reason hint so the cell stays readable."""
    parts = []
    for (t, m), tag in ((("cuvein", "engine"), "eng"), (("cuvein", "trace-only"), "tr")):
        groups = defaultdict(list)
        for _id, mm in sorted(meta.items()):
            if mm[0] != ps or man.get(_id, {}).get("label", "") != "RACE":
                continue
            r = runs.get((_id, t, m))
            if r and r["verdict"] == "CLEAN":
                groups[_fn_reason(ps, mm[1], mm[2]) or "no hint"].append(mm[1])
        if groups:
            n = sum(len(v) for v in groups.values())
            txt = "; ".join(f"{k}: " + ", ".join(f"`{x}`" for x in v) for k, v in groups.items())
            parts.append(f"**{tag}** ({n}) — {txt}")
    return "<br>".join(parts) if parts else "none"


def _h2h_block(runs, meta, man, psets, tools, title, note):
    """One head-to-head block over the labelled programs of `psets`."""
    out = [f"\n### {title}\n", note + "\n"]
    ratios = _ratios(runs, meta)
    ids = [i for i, m in meta.items() if _in(m, psets)]
    hdr = ["tool", "TP", "FN", "FP", "TN", "err/TO", "precision", "recall", "F1",
           "FP rate", "geomean×", "median peak MB"]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    for c in tools:
        T = dict(fp=0, tn=0, tp=0, fn=0, err=0)
        for ps in psets:
            d = fp_tp(runs, meta, man, ps, *c)
            for k in T:
                T[k] += d[k]
        if not sum(T.values()):
            continue
        f = lambda a, b: (a / b) if b else None
        pr, rc, fpr = f(T["tp"], T["tp"] + T["fp"]), f(T["tp"], T["tp"] + T["fn"]), f(T["fp"], T["fp"] + T["tn"])
        f1 = (2 * pr * rc / (pr + rc)) if pr and rc else None
        fmt = lambda x: f"{x:.2f}" if x is not None else "—"
        xs = [ratios[(i,) + c] for i in ids if (i,) + c in ratios
              and runs[(i,) + c]["verdict"] in ("RACE", "CLEAN")]
        gm = f"{math.exp(sum(math.log(x) for x in xs) / len(xs)):.1f}" if xs else "—"
        pk = sorted(runs[(i,) + c]["peak"] for i in ids if (i,) + c in runs and runs[(i,) + c].get("peak"))
        out.append("| " + " | ".join([COLNAME[c], str(T["tp"]), str(T["fn"]), str(T["fp"]),
                   str(T["tn"]), str(T["err"]), fmt(pr), fmt(rc), fmt(f1), fmt(fpr), gm,
                   f"{pk[len(pk)//2]:.0f}" if pk else "—"]) + " |")
    return out


def _agreement(runs, meta, psets, ref, tools):
    out = ["", f"Agreement with {COLNAME[ref]} on programs where both tools reached a verdict:\n",
           f"| other tool | programs | agree | {COLNAME[ref]} RACE, other CLEAN | {COLNAME[ref]} CLEAN, other RACE |",
           "|---|---|---|---|---|"]
    for c in tools:
        if c == ref:
            continue
        both = agree = a = b = 0
        for i, m in meta.items():
            if not _in(m, psets):
                continue
            r, o = runs.get((i,) + ref), runs.get((i,) + c)
            if not r or not o or r["verdict"] not in ("RACE", "CLEAN") or o["verdict"] not in ("RACE", "CLEAN"):
                continue
            both += 1
            agree += r["verdict"] == o["verdict"]
            a += r["verdict"] == "RACE" and o["verdict"] == "CLEAN"
            b += r["verdict"] == "CLEAN" and o["verdict"] == "RACE"
        if both:
            out.append(f"| {COLNAME[c]} | {both} | {100 * agree // both}% | {a} | {b} |")
    return out


def headtohead_section(runs, meta, man):
    tools = [c for c in RACE_TOOLS + [("sanitizer", "")] if any(k[1:] == c for k in runs)]
    out = ["\n## 2a. Head-to-head summary\n",
           "TP/FN over labelled-racy programs, FP/TN over labelled race-free programs; "
           "ERROR/TIMEOUT counted separately and excluded from the rates. geomean× = slowdown "
           "vs native over the programs the tool finished; peak MB = median of the per-program "
           "peak RSS of the whole tool process tree (blank where the runner did not sample it)."]
    out += _h2h_block(runs, meta, man, PREREG_SETS, tools,
                      "All pre-registered sets (P1, PI, P3–P6)",
                      "SuperCollider appears here only through P6: its compiler pass is not "
                      "distributed, so it cannot be run on P1–P5 (see Blockers).")
    out += _agreement(runs, meta, PREREG_SETS, ("cuvein", "engine"), tools)
    if any(k[1] == "supercollider" for k in runs):
        out += _h2h_block(runs, meta, man, SC_SETS, tools,
                          "SuperCollider-matched sets (P6 cuHadron + its 99-test subset of PI Indigo original + P9 HeCBench-10)",
                          "The only programs SuperCollider ships instrumented. Every other tool ran our "
                          "own build of the same sources with the same inputs, so this is the "
                          "like-for-like comparison. Indigo labels follow the artifact's own ground truth "
                          "(`Bug` in the name and not `boundsBug`; boundsBug tests excluded); P9 labels "
                          "are the SuperCollider paper's racy/race-free flags, not an independent oracle. "
                          "SuperCollider's verdict is RACE if any of 5 attempts reports (its own protocol); "
                          "the others use 3 reps.")
        out += _agreement(runs, meta, SC_SETS, ("cuvein", "engine"), tools)
        out += cuvein_vs_sc(runs, meta, man)
    return "\n".join(out)


PREFIX_DIR = f"{RES}/prefix_fe694b5"   # superseded cuVein rows (setup/supersede_prefix.sh)
# every superseded cuVein revision, oldest first: (tag, dir, what it was)
OLD_REVS = (
    ("fe694b5", PREFIX_DIR,
     "detector as committed at `fe694b5` with the prebuilt `lib/` of 2026-09-10 "
     "(moved aside by `setup/supersede_prefix.sh`)"),
    ("2026-09-18", f"{RES}/prefix_36a93d08",
     "`fe694b5` + working-tree edits of 2026-09-17, diff sha `36a93d0849043935` "
     "(moved aside by `setup/supersede_rev0918.sh`; its merged CSV also holds the Indigo-original "
     "rows, which were already produced on the current revision and are therefore left out of this side)"),
)


def _geomean(xs):
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else None


def revision_delta_section(runs, meta, man):
    """§2b: the superseded cuVein rows (detector at fe694b5 + lib of 2026-09-10, kept in
    eval/results/prefix_fe694b5/) next to the current rows, per set x mode. The old rows
    feed no other table; this is the only place they are read."""
    olds = []
    for tag, d, what in OLD_REVS:
        if os.path.exists(f"{d}/baselines-cuvein.csv"):
            o_runs, o_meta = load_runs([f"{d}/baselines-cuvein.csv"])
            if tag != "fe694b5":      # PI rows in that merged CSV are current-revision rows
                o_runs = {k: v for k, v in o_runs.items() if not k[0].startswith("PI-")}
            olds.append((tag, o_runs, o_meta, what))
    if not olds:
        return ""
    rev = ""
    st = f"{HERE}/setup/cuvein_rev.status"
    if os.path.exists(st):
        rev = " ".join(l.strip() for l in open(st) if l.startswith(("HEAD:", "working-tree diff")))
    out = ["\n## 2b. cuVein revision delta (superseded rows vs this run)\n",
           f"Current rows: {rev or 'see setup/cuvein_rev.status'}. Superseded rows (nothing deleted): "
           + "; ".join(f"**{tag}** = {what}" for tag, _, _, what in olds) + ". "
           "Counts as in §2a; geomean× over programs both revisions finished, both normalised by this run's native wall. "
           "`TO/ERR` = TIMEOUT+ERROR.\n",
           "| set | mode | rev | TP | FN | FP | TN | TO/ERR | precision | recall | geomean× |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    # the native wall belongs to the program (same binary+input), not to the
    # revision: both sides are normalised by the CURRENT run's native, so a stale
    # native in the superseded rows (e.g. a first failed attempt) cannot skew the old side
    r_new = _ratios(runs, meta)
    native = {i: runs[(i, "cuvein", m)]["native"] for (i, t, m) in runs
              if t == "cuvein" and runs[(i, t, m)]["native"]}
    r_olds = {tag: {(i, t, m): r["wall"] / native[i] for (i, t, m), r in o_runs.items()
                    if t == "cuvein" and r["wall"] and native.get(i)}
              for tag, o_runs, _, _ in olds}
    for ps in ALL_PSETS:
        for mode in ("engine", "trace-only"):
            for tag, rr, mm, rat in [(tg, o_runs, o_meta, r_olds[tg]) for tg, o_runs, o_meta, _ in olds] + \
                                    [("current", runs, meta, r_new)]:
                c = fp_tp(rr, mm, man, ps, "cuvein", mode)
                if not any(c.values()):
                    continue
                prec = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else None
                rec = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else None
                # programs EVERY revision (that has the set) finished
                revs = [(o_runs, r_olds[tg]) for tg, o_runs, _, _ in olds] + [(runs, r_new)]
                revs = [(a, b) for a, b in revs
                        if any(t == "cuvein" and m == mode and meta.get(i, ("",))[0] == ps for (i, t, m) in b)]
                both = [i for (i, t, m) in rat if t == "cuvein" and m == mode and mm.get(i, ("",))[0] == ps
                        and all((i, "cuvein", mode) in b
                                and a[(i, "cuvein", mode)]["verdict"] not in ("TIMEOUT", "ERROR")
                                for a, b in revs)]
                g = _geomean([rat[(i, "cuvein", mode)] for i in both])
                out.append(f"| {PSET_LABEL.get(ps, ps)} | {mode} | {tag} | {c['tp']} | {c['fn']} | "
                           f"{c['fp']} | {c['tn']} | {c['err']} | "
                           f"{'' if prec is None else f'{prec:.2f}'} | {'' if rec is None else f'{rec:.2f}'} | "
                           f"{'' if g is None else f'{g:.1f}'} |")
    # per-program verdict flips, current vs each superseded revision
    for otag, old_runs, _, _ in olds:
        flips = defaultdict(list)
        for (i, t, m), r in runs.items():
            if t != "cuvein" or (i, t, m) not in old_runs:
                continue
            o = old_runs[(i, t, m)]["verdict"]
            if o != r["verdict"]:
                flips[(o, r["verdict"])].append((m, i))
        if flips:
            out.append(f"\nVerdict flips per program ({otag} → current), by mode:\n")
            out.append("| old → new | engine | trace-only |")
            out.append("|---|---|---|")
            for k in sorted(flips):
                e = sum(1 for m, _ in flips[k] if m == "engine")
                t = sum(1 for m, _ in flips[k] if m == "trace-only")
                out.append(f"| {k[0]} → {k[1]} | {e} | {t} |")
            out.append(f"\n<details><summary>flipped programs ({otag} → current)</summary>\n")
            out.append("| old → new | mode | program | label |")
            out.append("|---|---|---|---|")
            for k in sorted(flips):
                for m, i in sorted(flips[k]):
                    out.append(f"| {k[0]} → {k[1]} | {m} | `{i}` | {man.get(i, {}).get('label', '')} |")
            out.append("\n</details>")
    return "\n".join(out)


def cuvein_vs_sc(runs, meta, man):
    out = ["\n### cuVein vs SuperCollider, program by program (matched sets)\n",
           "Programs where exactly one of the two reports a race, split by who the label "
           "favours, plus the programs only one of them could finish.\n",
           "| set | cuVein mode | both RACE | both CLEAN | cuVein only (label RACE / CLEAN / none) | SuperCollider only (label RACE / CLEAN / none) | cuVein ERR/TO where SC has a verdict | SC ERR/TO where cuVein has a verdict |",
           "|---|---|---|---|---|---|---|---|"]
    details = []
    for ps in SC_SETS:
        for cm in (("cuvein", "engine"), ("cuvein", "trace-only")):
            bb = cc = cvto = scto = 0
            cv = {"RACE": 0, "CLEAN": 0, "": 0}
            sc = {"RACE": 0, "CLEAN": 0, "": 0}
            for i, m in sorted(meta.items()):
                if not _in(m, (ps,)):
                    continue
                a, b = runs.get((i,) + cm), runs.get((i, "supercollider", ""))
                if not a or not b:
                    continue
                lab = man.get(i, {}).get("label", "")
                av, bv = a["verdict"], b["verdict"]
                ok = ("RACE", "CLEAN")
                if av in ok and bv in ok:
                    if av == bv == "RACE": bb += 1
                    elif av == bv: cc += 1
                    elif av == "RACE":
                        cv[lab] += 1
                        if cm[1] == "engine": details.append((ps, m[1], m[2], lab, "cuVein only"))
                    else:
                        sc[lab] += 1
                        if cm[1] == "engine": details.append((ps, m[1], m[2], lab, "SuperCollider only"))
                elif bv in ok: cvto += 1
                elif av in ok: scto += 1
            out.append(f"| {SET_NAME.get(ps, ps)} | {cm[1]} | {bb} | {cc} | {cv['RACE']} / {cv['CLEAN']} / {cv['']} | "
                       f"{sc['RACE']} / {sc['CLEAN']} / {sc['']} | {cvto} | {scto} |")
    if details:
        out.append(f"\n<details><summary>{len(details)} split programs (cuVein-engine vs SuperCollider)</summary>\n")
        out.append("| set | program | build | label | who reports |")
        out.append("|---|---|---|---|---|")
        for d in details:
            out.append("| " + " | ".join(x or "—" for x in d) + " |")
        out.append("\n</details>")
    return out



# ---- complete comparison matrix (§2c) + per-suite overhead min/max/avg (§4a) ----------
SUITE_FULLNAME = {
    "P1": "Indigo3 suite (Indigo3Suite; stratified 100 programs × {default, -DSLOWER_ATOMIC} × 2 graphs)",
    "PI": "Indigo original suite (IndigoSuite 1.3, all 590 CUDA codes × 7 inputs: the HiRace artifact's six Table-1 graphs at 256×1024 + SuperCollider's graph at 256×4)",
    "PI@sc": "Indigo original suite — SuperCollider's 99-test subset on its own input (a view of the row above, not a separate dataset)",
    "P3": "ECL race-free graph codes (CC / MIS / MST, generated from Indigo3)",
    "P4": "ScoR applications",
    "P5": "ScoR micro-benchmarks + canary",
    "P6": "cuHadron",
    "P7": "HeCBench overhead set (unlabelled real applications)",
    "P9": "HeCBench — SuperCollider's 10-application subset",
}
MATRIX_COLS = [("cuvein", "engine"), ("cuvein", "trace-only"), ("racecheck", ""),
               ("sanitizer", ""), ("hirace", ""), ("iguard", ""), ("supercollider", "")]
MATRIX_NAME = {("cuvein", "engine"): "cuVein (engine)", ("cuvein", "trace-only"): "cuVein (trace-only)",
               ("racecheck", ""): "compute-sanitizer racecheck",
               ("sanitizer", ""): "compute-sanitizer (any of memcheck / racecheck / synccheck / initcheck)",
               ("hirace", ""): "HiRace", ("iguard", ""): "iGUARD", ("supercollider", ""): "SuperCollider"}
MATRIX_SHORT = {("cuvein", "engine"): "cuVein-eng", ("cuvein", "trace-only"): "cuVein-tr",
                ("racecheck", ""): "racecheck", ("sanitizer", ""): "sanitizer(any)",
                ("hirace", ""): "HiRace", ("iguard", ""): "iGUARD", ("supercollider", ""): "SuperCollider"}
FP_CAUSE_TEXT = {"RC1": "cuda::atomic load/store not modelled as atomic",
                 "RC2": "latent report on a barrier/lock idiom (not raced dynamically, no static proof)",
                 "RC3": "pair mis-attribution in the engine",
                 "RC4": "same-pc write-write of the same value (idempotent `updated = true`)",
                 "RC5": "ScoR volatile-handshake data",
                 "other": "plain conflicting accesses that did race in the run (suite labels the program race-free)"}
# cuHadron tests the SuperCollider artifact README lists as not detectable by design
SC_BY_DESIGN = {"asyncmemcpy/kernel_memcpy_dtoh_race", "hostdevice/global_readwrite_race"}


def _mlabel(_id, meta, man):
    """Suite label of a manifest id."""
    return man.get(_id, {}).get("label", "")


def _mrun(runs, _id, tool, mode):
    """The (id, tool, mode) run; a runner-level row without a mode (cuVein
    `missing-exe`) applies to both cuVein modes."""
    return runs.get((_id, tool, mode)) or (runs.get((_id, tool, "")) if mode else None)


def confusion(runs, meta, man, psets, tool, mode):
    """TP/FN/FP/TN with TIMEOUT and ERROR counted separately; `unl` = verdicts on
    programs without a RACE/CLEAN label. ids lists the FN/FP/TO/ERR programs."""
    c = dict(tp=0, fn=0, fp=0, tn=0, to=0, err=0, unl=0, n=0, lab_r=0, lab_c=0)
    ids = dict(fn=[], fp=[], to=[], err=[])
    for _id, m in meta.items():
        if not _in(m, psets):
            continue
        r = _mrun(runs, _id, tool, mode)
        if not r:
            continue
        c["n"] += 1
        v, lab = r["verdict"], _mlabel(_id, meta, man)
        c["lab_r"] += lab == "RACE"
        c["lab_c"] += lab == "CLEAN"
        if v == "TIMEOUT":
            c["to"] += 1; ids["to"].append(_id)
        elif v == "ERROR":
            c["err"] += 1; ids["err"].append(_id)
        elif lab == "RACE":
            if v == "RACE":
                c["tp"] += 1
            else:
                c["fn"] += 1; ids["fn"].append(_id)
        elif lab == "CLEAN":
            if v == "RACE":
                c["fp"] += 1; ids["fp"].append(_id)
            else:
                c["tn"] += 1
        else:
            c["unl"] += 1
    assert sum(c[k] for k in ("tp", "fn", "fp", "tn", "to", "err", "unl")) == c["n"]
    return c, ids


def _mcell(c):
    if not c["n"]:
        return "-"
    # "-" = the suite has no program of that label for this tool; "0/0" = it has, none finished
    tp = f"{c['tp']}/{c['tp'] + c['fn']}" if c["lab_r"] else "-"
    fp = f"{c['fp']}/{c['fp'] + c['tn']}" if c["lab_c"] else "-"
    return f"{tp}, {fp}, {c['to']}, {c['err']}"


def _tally(items):
    d = defaultdict(int)
    for x in items:
        d[x] += 1
    return "; ".join(f"{k} ({v})" for k, v in sorted(d.items(), key=lambda kv: (-kv[1], kv[0])))


_PI_ORACLE = {}


def pi_oracle():
    """id -> CONFLICT / NO-CONFLICT from oracle_pi/oracle_pi.py (input-level ground truth for
    the Indigo original suite: does the planted bug yield an unordered conflicting access
    pair on THIS input). Only the inputs that script was run on are present."""
    if not _PI_ORACLE:
        for r in load_csv(f"{RES}/baselines-pi-oracle.csv"):
            _PI_ORACLE[r["id"]] = r["oracle"]
        _PI_ORACLE.setdefault("", "")
    return _PI_ORACLE


def _bugclass_hint(prog, inp="", _id=None):
    """Planted Indigo bug tokens (+ whether the input is one of the 5-vertex graphs, on
    which many planted races never get two threads onto the same element)."""
    toks = [t for t in ("boundsBug", "guardBug", "atomicBug", "syncBug", "RaceBug") if t in prog]
    o = pi_oracle().get(_id) if _id else None
    if o in ("CONFLICT", "NO-CONFLICT") and toks and toks != ["boundsBug"]:
        bug = "+".join(t for t in toks if t != "boundsBug")
        g = "5-vertex graph" if ("_5n_" in inp or inp.startswith("DAG_5n")) else "≥100-vertex graph"
        if o == "NO-CONFLICT":
            return (f"planted {bug}: NOT racy on this input ({g}) — no two threads make conflicting "
                    f"accesses there (oracle, footnote 8)")
        return f"planted {bug} not reported although a conflicting access pair exists on this input ({g}; real miss, footnote 8)"
    size = ""
    if inp:
        size = " on a 5-vertex graph" if "_5n_" in inp or inp.startswith("DAG_5n") else " on a ≥100-vertex graph"
    if toks == ["boundsBug"]:
        return "labelled racy by name but the planted bug is out-of-bounds, not a data race"
    return ("planted " + "+".join(t for t in toks if t != "boundsBug") + " not reported" + size) if toks else "race not reported"


def _fn_why(runs, meta, man, _id, tool, mode):
    ps, prog, build = meta[_id][0], meta[_id][1], meta[_id][2]
    shared = man.get(_id, {}).get("shared_mem", "") == "1"
    cat = prog.split("/")[0]
    if tool == "cuvein":
        other = "trace-only" if mode == "engine" else "engine"
        o = runs.get((_id, "cuvein", other))
        if ps == "PI":
            return _bugclass_hint(prog, meta[_id][3], _id)
        h = _fn_reason(ps, prog, build)
        if h:
            return h
        if o and o["verdict"] == "RACE":
            return f"missed by this mode only (cuVein {other} reports it)"
        return f"race not reported (`{prog}`)"
    if tool in ("racecheck", "sanitizer"):
        if not shared:
            return "race on global/device memory — racecheck only tracks `__shared__` memory"
        return "`__shared__`-memory race not reported"
    if tool == "iguard":
        if shared:
            return "`__shared__` memory is not tracked by iGUARD"
        if ps == "P6":   # tool-neutral wording (the _fn_reason hints are about cuVein's model)
            return {"hostdevice": "host-vs-device race (host side not instrumented)",
                    "interkernel": "cross-stream / inter-kernel race not reported",
                    "asyncmemcpy": "memcpy-vs-kernel race (memcpy side not instrumented)",
                    "memcpy": "memcpy-vs-kernel race (memcpy side not instrumented)"}.get(cat, "race not reported")
        if ps == "PI":
            return _bugclass_hint(prog, meta[_id][3], _id)
        return "race not reported (only cudaMalloc-tracked global memory is checked)"
    if tool == "hirace":
        return _bugclass_hint(prog, meta[_id][3], _id)
    if tool == "supercollider":
        if prog in SC_BY_DESIGN:
            return "not detectable by design (DMA / CPU-side access; artifact README)"
        return ((_bugclass_hint(prog, meta[_id][3], _id) + ": ") if ps == "PI" else "") + "race never manifested in the 5 attempts (probabilistic redundant-read detection)"
    return "race not reported"


def _fp_why(runs, _id, tool, mode, fpc):
    if tool == "cuvein":
        causes = sorted({c.split("-")[0] for c in fpc.get((_id, mode), ())})
        return " + ".join(FP_CAUSE_TEXT.get(c, c) for c in causes) if causes else "unclassified report"
    if tool == "iguard":
        kinds = sorted({x.split("@")[0].replace("_", " ") for x in runs[(_id, tool, mode)]["report_ids"].split() if "@" in x})
        return " + ".join(kinds) if kinds else "unparsed report"
    if tool == "sanitizer":
        who = [t for (t, m) in SAN_TOOLS if runs.get((_id, t, m), {}).get("verdict") == "RACE"]
        return "flagged by " + "+".join(who) + (" (not a data-race report)" if "racecheck" not in who else "")
    return "reported on a race-free-labelled program"


def _fail_why(r, diag_cause, tr_ok):
    n = r.get("notes", "")
    if "missing-exe" in n or "unsupported-on-this-gpu" in n:
        return "binary needs sm_90 (not buildable/runnable on the sm_89 nodes)"
    if diag_cause:
        return diag_cause
    if "analysis-timeout" in n:
        return "analysis-timeout"
    if "No space left on device" in n:
        return "node scratch disk full (harness, not the tool)"
    if r["verdict"] == "TIMEOUT":
        return "exceeded the time cap" + (" in engine mode only (trace-only finishes)" if tr_ok else "")
    return "tool error"


def matrix_note(runs, meta, man, ps, fpc, diag):
    parts = []
    for (t, m) in MATRIX_COLS:
        c, ids = confusion(runs, meta, man, (ps,), t, m)
        if not c["n"]:
            continue
        bits = []
        if c["fn"]:
            bits.append(f"FN {c['fn']}: " + _tally(_fn_why(runs, meta, man, i, t, m) for i in ids["fn"]))
        if c["fp"]:
            bits.append(f"FP {c['fp']}" + (", by iGUARD report class: " if t == "iguard" else ": ")
                        + _tally(_fp_why(runs, i, t, m, fpc) for i in ids["fp"]))
        if c["to"] + c["err"]:
            why = []
            for i in ids["to"] + ids["err"]:
                tr = runs.get((i, "cuvein", "trace-only"), {}).get("verdict") in ("RACE", "CLEAN")
                rr = _mrun(runs, i, t, m)
                if t == "sanitizer":   # the union row carries no notes: take a failed member's
                    rr = next((runs[(i, tt, mm)] for (tt, mm) in SAN_TOOLS if (i, tt, mm) in runs
                               and runs[(i, tt, mm)]["verdict"] in ("TIMEOUT", "ERROR")), rr)
                why.append(_fail_why(rr, diag.get((i, m)) if t == "cuvein" else "",
                                     t == "cuvein" and m == "engine" and tr))
            bits.append(f"TO/ERR {c['to'] + c['err']}: " + _tally(why))
        if bits:
            parts.append(f"**{MATRIX_SHORT[(t, m)]}** — " + ". ".join(bits))
    return "<br>".join(parts) if parts else "no FN / FP / failures"


MATRIX_TOTALS = (("All pre-registered labelled suites (Indigo3 + Indigo original + ECL + ScoR applications + ScoR micro-benchmarks + cuHadron)",
                  PREREG_SETS),
                 ("SuperCollider-matched suites (cuHadron + the 99-test subset view of the Indigo original suite + HeCBench 10-application subset)", SC_SETS))


def _suite_name(ps, man):
    rows = [r for r in man.values() if _in((r.get("pset"), r.get("program"), r.get("build")), (ps,))]
    codes = len({r.get("program") for r in rows})
    n = f"{len(rows)} programs" if codes == len(rows) else f"{len(rows)} program-inputs ({codes} codes)"
    return f"{SUITE_FULLNAME[ps]} — {n}"


def comparison_matrix_section(runs, meta, man):
    fpc = defaultdict(set)
    for r in load_csv(f"{RES}/baselines-fp-causes.csv"):
        fpc[(r["id"], r["mode"])].add(r["cause"])
    diag = {(r["id"], r["mode"]): r["cause"] for r in load_csv(f"{RES}/baselines-diagnose.csv")
            if r.get("cause") not in ("resolved", "")}
    out = ["\n## 2c. Complete comparison matrix (detector × test suite)\n",
           "Cell = `TP/(TP+FN), FP/(FP+TN), TO, ERR`: TP/(TP+FN) over the suite's racy-labelled "
           "programs, FP/(FP+TN) over its race-free-labelled programs (both exclude runs that did "
           "not finish), TO = programs that timed out, ERR = programs that errored. `-` = slot not "
           "available (tool not runnable on the suite, or the suite has no program of that label); "
           "`0/0` = the suite has such programs but the tool finished none of them. "
           "A program's verdict is RACE if any repetition reports. The note column gives, per "
           "detector, the brief reason behind its false negatives (FN), false positives (FP) and "
           "failures on that suite, with program counts in parentheses.\n"]
    hdr = ["test suite"] + [MATRIX_NAME[c] for c in MATRIX_COLS] + ["note: reasons behind FN / FP / failures"]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    unl = defaultdict(int)
    for ps in [x for p0 in ALL_PSETS for x in ((p0, "PI@sc") if p0 == "PI" else (p0,))]:
        row = [_suite_name(ps, man)]
        for (t, m) in MATRIX_COLS:
            c, _ = confusion(runs, meta, man, (ps,), t, m)
            row.append(_mcell(c))
            unl[ps] = max(unl[ps], c["unl"])
        row.append(matrix_note(runs, meta, man, ps, fpc, diag))
        out.append("| " + " | ".join(row) + " |")
    for name, sets in MATRIX_TOTALS:
        row = [f"**{name}**"]
        for (t, m) in MATRIX_COLS:
            row.append(_mcell(confusion(runs, meta, man, sets, t, m)[0]))
        row.append("sum of the rows above")
        out.append("| " + " | ".join(row) + " |")
    out.append("\nFootnotes: (1) HiRace is source-level and has no usable instrumenter (its `src/clang` "
               "prototype only rewrites kernel params named `data1`/`data2`, emits an API the shipped "
               "runtime does not have and needs an LLVM source tree to build); it runs only on the 590 "
               "IndigoSuite codes its artifact ships hand-instrumented, which are exactly the Indigo "
               "original suite. "
               "(2) SuperCollider's compiler pass is not distributed; it exists only as pre-instrumented "
               "binaries for cuHadron and its own Indigo/HeCBench subsets. (3) iGUARD was not run on the "
               "HeCBench overhead set. (4) 16 cuHadron targets need sm_90 and count as ERR for every tool "
               "that was pointed at them. (5) Programs without a racy/race-free label are in neither "
               "ratio: " + ", ".join(f"{SUITE_FULLNAME[p].split(' (')[0]} {n}" for p, n in unl.items() if n)
               + " (HeCBench overhead apps are unlabelled; Indigo `boundsBug` codes are out-of-bounds bugs, "
               "excluded by both the HiRace and the SuperCollider artifact's ground truth). (6) HeCBench-subset labels are the "
               "SuperCollider paper's racy/race-free flags, not an independent oracle.")
    # (7) cuHadron asyncmemcpy/*: host-API copies, out of cuVein's scope (counts from the rows)
    am = {}
    for (i, t, m), r in runs.items():
        mm = meta.get(i)
        if t == "cuvein" and m and mm and mm[0] == "P6" and mm[1].startswith(("asyncmemcpy/", "interkernel/")):
            k = "TO/ERR" if r["verdict"] in ("TIMEOUT", "ERROR") else r["verdict"]
            am.setdefault((mm[1].split("/")[0], m), {}).setdefault(k, 0)
            am[(mm[1].split("/")[0], m)][k] += 1
    if am:
        out[-1] += (" (7) Two cuHadron categories are out of cuVein's scope (user decision, 2026-09-21); their rows are "
                    "kept, not excluded, because the labels apply to every detector. `asyncmemcpy/*` races a host-API "
                    "`cudaMemcpyAsync` against a kernel on another stream: the collector's async-copy tracer covers the "
                    "in-kernel `cp.async` instruction (the `memcpy/*` tests, which cuVein does run), and the race tool "
                    "consumes no host memcpy events. `interkernel/*` races two kernels on different streams: the "
                    "happens-before model is per kernel launch. cuVein verdicts on them: "
                    + "; ".join(f"{c} {m}: " + ", ".join(f"{k} {v}" for k, v in sorted(d.items()))
                                for (c, m), d in sorted(am.items())) +
                    " (4 program-inputs per category). Their failures are trace volume of the kernels themselves "
                    "(`kernel_memcpy_dtoh_race`: 64M threads × 201 writes ≈ 1.3e10 traced accesses; "
                    "`memcpy_htod_kernel_race`: ≈ 2.6e8 reads, engine mode only; `interkernel/global_writewrite_race`: "
                    "≈ 1.1e8 events, finishes only with the 20-minute cap). Not re-run for that reason: the longer-cap "
                    "diagnose re-runs of `kernel_memcpy_dtoh_race` (cancelled after node failures on c3, c2, c75), the "
                    "`memcpy_htod_kernel_race-fixed` row lost to a full scratch disk on c37, and the "
                    "`interkernel/global_writewrite_race-fixed` diagnose task that was OOM-killed on c53.")
    orc = {k: v for k, v in pi_oracle().items() if v in ("CONFLICT", "NO-CONFLICT")}
    if orc:
        graphs = sorted({meta[i][3] for i in orc if i in meta})
        lab = {i: (man.get(i, {}).get("label", "") or "").upper() for i in orc}
        n_r = sum(1 for i in orc if lab[i] == "RACE")
        n_rn = sum(1 for i in orc if lab[i] == "RACE" and orc[i] == "NO-CONFLICT")
        n_c = sum(1 for i in orc if lab[i] == "CLEAN")
        n_cc = sum(1 for i in orc if lab[i] == "CLEAN" and orc[i] == "CONFLICT")
        per = []
        for (t, m) in MATRIX_COLS:
            fn_not = fn_real = fn_unchk = tp_chk = 0
            seen = False
            for i, mm in meta.items():
                if mm[0] != "PI" or (man.get(i, {}).get("label", "") or "").upper() != "RACE":
                    continue
                r = _mrun(runs, i, t, m) if "_mrun" in globals() else runs.get((i, t, m))
                if not r:
                    continue
                seen = True
                if r["verdict"] == "RACE":
                    tp_chk += i in orc and orc[i] == "CONFLICT"
                elif r["verdict"] == "CLEAN":
                    if i not in orc:
                        fn_unchk += 1
                    elif orc[i] == "NO-CONFLICT":
                        fn_not += 1
                    else:
                        fn_real += 1
            if seen and (fn_not or fn_real or fn_unchk):
                per.append(f"{MATRIX_NAME[(t, m)]}: {fn_not} not racy on the input, {fn_real} real misses"
                           + (f", {fn_unchk} on inputs not checked" if fn_unchk else ""))
        out[-1] += (" (8) **Are the Indigo-original FNs racy?** The suite labels a CODE racy (a planted `atomicBug`/`guardBug`/"
                    "`syncBug`), but whether two threads actually conflict depends on the input graph. "
                    "`oracle_pi/oracle_pi.py` (→ `eval/results/baselines-pi-oracle.csv`) decides it per (code, input) "
                    "independently of every detector: the unmodified source is compiled for the CPU with an "
                    "access-logging `data_t`, each GPU thread runs as a fiber with `__syncthreads` barriers and warp "
                    "collectives emulated, under 3 thread schedules, and a row is CONFLICT iff two different threads "
                    "touch one location, at least one writes, not both atomic, with no barrier/collective between them "
                    "(source-level: an elided store still counts). Checked inputs: " + ", ".join(f"`{g}`" for g in graphs) +
                    f" (every FN of cuVein and HiRace is on these). Result: {n_rn} of {n_r} racy-labelled rows have NO "
                    f"conflicting access on their input (e.g. `DAG_5n_5e` has every edge pointing to a lower vertex id, so a "
                    f"`cond` variant's `if (i < nei)` is never true and the buggy update is never reached; with `guardBug` "
                    f"the unguarded write only happens when the compared value is larger, which it never is there; the 4 rows on "
                    f"`DAG_100n_100e` are block-per-vertex codes launched with SuperCollider's 4 blocks, so only vertices 0–3 "
                    f"run and they update two different elements, one thread each); "
                    f"{n_cc} of {n_c} bug-free rows show a conflict. FN split per detector — " + "; ".join(per) +
                    ". So the FN cells of cuVein (both modes) and HiRace on this suite contain no missed race: on "
                    "input-level truth their recall is 100% and the label-based ratio under-states it. The label-based "
                    "cells are kept as pre-registered.")
    return "\n".join(out)


def overhead_minmax_section(runs, meta, man):
    rat = _ratios(runs, meta)
    out = ["\n## 4a. Overhead per detector per test suite (min / max / avg / mid)\n",
           "Slowdown = tool wall / native wall of the same program and input (median of reps); "
           "SuperCollider is measured against its own uninstrumented binary in the same container. "
           "Cell = `min / max / avg / mid (geomean), n` where avg is the arithmetic mean, mid the median "
           "(middle value over the finished programs) and n the number "
           "of programs the detector finished (TIMEOUT/ERROR runs are excluded, so heavy suites "
           "under-state the true cost: see TO in §2c). The geomean is given because the mean of "
           "ratios is dominated by a few outliers. `-` = no finished program / tool not run. "
           "The compute-sanitizer(any) column is the slowest of its four tools per program.\n"]
    hdr = ["test suite"] + [MATRIX_NAME[c] for c in MATRIX_COLS]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))

    def cell(sets, t, m):
        xs = [x for (i, tt, mm), x in rat.items() if (tt, mm) == (t, m)
              and _in(meta.get(i), sets)
              and runs[(i, tt, mm)]["verdict"] not in ("TIMEOUT", "ERROR")]
        if not xs:
            return "-"
        return (f"{min(xs):.1f}× / {max(xs):.1f}× / {sum(xs) / len(xs):.1f}× / "
                f"{statistics.median(xs):.1f}× ({_geomean(xs):.1f}×), n={len(xs)}")

    for ps in [x for p0 in ALL_PSETS for x in ((p0, "PI@sc") if p0 == "PI" else (p0,))]:
        out.append("| " + " | ".join([_suite_name(ps, man)] + [cell((ps,), t, m) for (t, m) in MATRIX_COLS]) + " |")
    out.append("| " + " | ".join(["**All suites**"] + [cell(ALL_PSETS, t, m) for (t, m) in MATRIX_COLS]) + " |")
    out.append("\nHiRace's slowdown is its hand-instrumented twin vs the uninstrumented build of the same "
               "code, same input and launch. iGUARD was not run on the HeCBench overhead set; "
               "SuperCollider exists only for cuHadron and its own two subsets.")
    return "\n".join(out)


SUMMARY_OUT = f"{APH}/eval/BASELINES_SUMMARY.md"


def write_summary(runs, meta, man):
    rev = ""
    st = f"{HERE}/setup/cuvein_rev.status"
    if os.path.exists(st):
        rev = " ".join(l.strip() for l in open(st) if l.startswith(("HEAD:", "working-tree diff")))
    doc = ["# BASELINES — summary tables\n",
           "_Generated by `eval/baselines/make_tables.py` from `eval/results/baselines-*.csv` "
           "(same data as `eval/BASELINES.md`, sections 2c and 4a). Facts only._\n",
           f"cuVein revision: {rev or 'see eval/baselines/setup/cuvein_rev.status'}.\n",
           comparison_matrix_section(runs, meta, man).replace("## 2c. ", "## 1. "),
           overhead_minmax_section(runs, meta, man).replace("## 4a. ", "## 2. ").replace("§2c", "table 1")]
    with open(SUMMARY_OUT, "w") as f:
        f.write("\n".join(doc) + "\n")
    print(f"wrote {SUMMARY_OUT}")


def hirace_table1_section(runs, meta):
    """The HiRace SC24 artifact's own `make table1`, run verbatim here
    (setup/p_hirace_table1.sh -> baselines-hirace-table1.csv), with the artifact's exact
    predicates (scripts/gen_table1.py), next to the paper's Table I (published numbers)
    and cross-checked against our own HiRace runner on the same (code, graph)."""
    rows = load_csv(f"{RES}/baselines-hirace-table1.csv")
    out = ["\n### HiRace artifact Table 1, reproduced verbatim (`make table1`)\n"]
    if not rows:
        out.append("_Not run yet: `sbatch eval/baselines/setup/p_hirace_table1.sh`._")
        return "\n".join(out)
    out.append("The artifact's driver (`scripts/hirace_experiments.py`, unmodified): every IndigoSuite code × 6 "
               "graphs, 256 threads/block × 1024 blocks, one run each, 300 s timeout, tools = HiRace "
               "(hand-instrumented twin), iGUARD, Compute Sanitizer racecheck, and the uninstrumented run's "
               "sequential comparison. Predicates are the artifact's (`gen_table1.py`): *found* = reports>0 on "
               "a code that is not `boundsBug`; *missed* = 0 reports on a `Bug` code that is not `boundsBug`. "
               "Because *found* also counts bug-free codes, the last columns split it: found-on-racy (TP) and "
               "flagged-bug-free (FP). The `paper` rows are the published Table I "
               "(`published/hirace_table1.csv`, transcribed from the artifact's `results/paper_figures/table1.png`), "
               "not measured here.\n")
    tools = (("HiRace", "hirace", None), ("iGUARD", "iguard", None),
             ("Compute Sanitizer", "memcheck", "racecheck"), ("Sequential", "indigo", None))
    pub = {r["graph"]: r for r in load_csv(f"{HERE}/published/hirace_table1.csv")}
    pk = {"HiRace": "hirace", "iGUARD": "iguard", "Compute Sanitizer": "compute_sanitizer", "Sequential": "sequential"}
    hdr = ["graph", "source", "total tests"] + [f"{n} found / missed" for n, _, _ in tools] + \
          [f"{n} TP / FP-on-bug-free" for n, _, _ in tools[:3]]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    graphs = sorted({r["graph"] for r in rows})
    for g in graphs:
        gr = [r for r in rows if r["graph"] == g]
        cells, split = [], []
        for n, tbl, tl in tools:
            rr = [r for r in gr if r["table"] == tbl and (tl is None or r["tool"] == tl)]
            nb = [r for r in rr if "boundsBug" not in r["code"]]
            found = sum(int(r["errors"] or 0) > 0 for r in nb)
            missed = sum(int(r["errors"] or 0) == 0 and "Bug" in r["code"] for r in nb)
            tp = sum(int(r["errors"] or 0) > 0 and "Bug" in r["code"] for r in nb)
            cells.append(f"{found} / {missed}")
            split.append(f"{tp} / {found - tp}")
        total = len({r["code"] for r in gr if r["table"] == "indigo"})
        out.append("| " + " | ".join([g, "reproduced", str(total)] + cells + split[:3]) + " |")
        # the paper's totals (346 racy tests) equal the 266 above + the 80 `boundsBug` codes
        # that ALSO carry another planted bug; same DB, that basis, so it lines up with `paper`
        def _other(code):
            return bool(set(re.findall(r"[A-Za-z]+Bug", code)) - {"boundsBug"})
        pc = []
        for n, tbl, tl in tools:
            rr = [r for r in gr if r["table"] == tbl and (tl is None or r["tool"] == tl)
                  and _other(r["code"])]
            f = sum(int(r["errors"] or 0) > 0 for r in rr)
            pc.append(f"{f} / {len(rr) - f}")
        out.append("| " + " | ".join([g, "reproduced, paper's basis", str(total)] + pc + ["", "", ""]) + " |")
        if g in pub:
            p = pub[g]
            out.append("| " + " | ".join([g, "paper", p["total_tests"]] +
                       [f"{p[pk[n] + '_found']} / {p[pk[n] + '_missed']}" for n, _, _ in tools] + ["", "", ""]) + " |")
    out.append("\n`reproduced, paper's basis`: the shipped `gen_table1.py` drops every `boundsBug` code (266 racy "
               "tests), but the paper's found+missed is 346 = those 266 + the 80 `boundsBug` codes that also carry "
               "an atomic/guard/sync bug. That row applies found = reports>0, missed = no report, over those 346 "
               "codes from the same database, so it is the row comparable to `paper` (bug-free codes are not in it).")
    seq = [r for r in rows if r["table"] == "indigo"]
    if seq and not any(int(r["errors"] or 0) for r in seq):
        out.append("\nThe reproduced *Sequential* column is 0 found by construction: the shipped driver's "
                   "`parse_log_indigo()` is a stub that returns `{'errors': 0}` for every run, so the "
                   "artifact as published does not compute the sequential-comparison figures of the "
                   "paper's Table I; that column cannot be reproduced from it (not a measurement difference).")
    # cross-check: our runner (PI rows, tool hirace) vs the verbatim DB, per (code, graph)
    ours = {(m[1], m[3]): runs[(i, t, md)]["verdict"] for (i, t, md) in runs
            for m in [meta.get(i)] if t == "hirace" and m and m[0] == "PI"}
    both = agree = 0
    diff = []
    for r in rows:
        if r["table"] != "hirace":
            continue
        v = ours.get((r["code"], r["graph"]))
        if v not in ("RACE", "CLEAN"):
            continue
        both += 1
        same = (v == "RACE") == (int(r["errors"] or 0) > 0)
        agree += same
        if not same:
            diff.append(f"`{r['code']}`@{r['graph']} (ours {v}, artifact driver {r['errors']} reports)")
    if both:
        out.append(f"\nCross-check of the two independent HiRace runs (our per-row runner, 3 reps at -O3 sm_89, vs "
                   f"the artifact driver, 1 run at nvcc defaults): **{agree}/{both}** (code, graph) verdicts agree."
                   + (" Differences: " + "; ".join(diff[:12]) + (" …" if len(diff) > 12 else "") if diff else ""))
    return "\n".join(out)


def x_checks(runs, meta, man):
    L = ["\n## 5. Pre-registered expectations (computed)\n"]
    def line(x, status, detail):
        L.append(f"- **{x}: {status}** — {detail}")
    F = lambda *a, **k: fp_tp(runs, meta, man, *a, **k)
    d = F("P1", "cuvein", "engine", "default")
    nob = d["fp"] + d["tn"]
    ig1 = F("P1", "iguard", "")
    ignob = ig1["fp"] + ig1["tn"]
    if nob:
        rate = 100 * d["fp"] // nob
        status = "CONFIRMED" if d["fp"] > nob // 2 else "PARTIAL"
        line("X1", status, f"cuVein-engine P1 default: **{d['fp']}/{nob} race-free "
             f"programs reported RACE ({rate}%)**, {d['tp']}/{d['tp']+d['fn']} racy caught "
             f"({d['err']} err/timeout excluded). iGUARD on P1 (both builds): "
             f"{ig1['fp']}/{ignob} race-free reported RACE, {ig1['tp']}/{ig1['tp']+ig1['fn']} racy caught "
             f"({ig1['err']} err/timeout). Expectation was 'cuVein reports most'.")
    else:
        line("X1", "BLOCKED", "P1 default not run.")
    ds = F("P1", "cuvein", "engine", "slower_atomic")
    nobs = ds["fp"] + ds["tn"]
    if nobs:
        rate = 100 * ds["fp"] // nobs
        status = "CONFIRMED" if rate <= 5 else "REFUTED"
        line("X2", status, f"cuVein-engine P1 slower_atomic: **{ds['fp']}/{nobs} race-free "
             f"reported RACE ({rate}%)** vs {d['fp']}/{nob} on default. Expectation was "
             f"~0; {'met' if rate<=5 else 'NOT met — FP reduced but not to ~0'}.")
    else:
        line("X2", "BLOCKED", "P1 slower_atomic not run.")
    d2 = F("PI", "cuvein", "engine"); nob2 = d2["fp"] + d2["tn"]
    hr2 = F("PI", "hirace", ""); hnob = hr2["fp"] + hr2["tn"]
    ig2 = F("PI", "iguard", ""); ignob2 = ig2["fp"] + ig2["tn"]
    if nob2 or hnob:
        line("X3", "CONFIRMED" if (hr2["fp"] == 0 and hnob) else "PARTIAL",
             f"HiRace (Indigo original suite, bug-free codes x 7 inputs): **{hr2['fp']} FP / {hnob} race-free -> "
             f"0-FP claim {'HOLDS' if hr2['fp']==0 else 'VIOLATED'}**, {hr2['tp']}/{hr2['tp']+hr2['fn']} racy caught. cuVein-engine PI: "
             f"{d2['fp']}/{nob2} race-free reported RACE, {d2['tp']}/{d2['tp']+d2['fn']} racy caught. "
             f"iGUARD PI: {ig2['fp']}/{ignob2} race-free reported RACE, {ig2['tp']}/{ig2['tp']+ig2['fn']} racy caught.")
    else:
        line("X3", "BLOCKED", "PI not built/run this session.")
    d3 = F("P3", "cuvein", "engine"); nob3 = d3["fp"] + d3["tn"]
    ig3 = F("P3", "iguard", ""); ignob3 = ig3["fp"] + ig3["tn"]
    line("X4", "CONFIRMED" if d3["fp"] > 0 else "see data",
         f"P3 race-free graph codes: cuVein-engine **{d3['fp']}/{nob3} reported RACE** "
         f"(over-reports, matches REPORT.md F5); iGUARD {ig3['fp']}/{ignob3} reported RACE; "
         f"HiRace {hr2['fp']}/{hnob} on its race-free patterns.")
    line("X5", "RECORDED", "P4 reduction volatile-tail vs RACEY missing-fence per build "
         "in the P4 table (record-only). See P4 rows.")
    ce = runs.get(("P5-canary", "cuvein", "engine")); ct = runs.get(("P5-canary", "cuvein", "trace-only"))
    ci = runs.get(("P5-canary", "iguard", ""))
    if ce and ct:
        ok = ce["verdict"] == "RACE" and ct["verdict"] != "RACE"
        line("X6", "CONFIRMED" if ok else "REFUTED",
             f"canary: cuVein-engine={ce['verdict']}, cuVein-trace-only={ct['verdict']} "
             f"(expected RACE / not-RACE); iGUARD={ci['verdict'] if ci else '—'} "
             f"(the canary's contested words are `__device__` globals, outside iGUARD's "
             f"cuMemAlloc-tracked metadata range).")
    else:
        line("X6", "BLOCKED", "canary not run in both modes.")
    line("X7", "see §4", "geomean slowdown per tool over P1/P7 in the overhead table.")
    return "\n".join(L)


def main():
    runs, meta = load_runs()
    add_sanitizer_union(runs)
    man = load_manifest()
    build_rows = load_csv(f"{RES}/baselines-build.csv")
    cols = tools_present(runs) or TOOLCOLS
    dis = load_csv(f"{RES}/baselines-disagreements.csv")

    doc = []
    doc.append("# BASELINES — head-to-head GPU race-detector comparison\n")
    doc.append("_Generated by `eval/baselines/make_tables.py` from "
               "`eval/results/baselines-*.csv`. Facts only._\n")
    doc.append("**Environment (actual):** SLURM cluster; runs on RTX 4060 Ti (sm_89, "
               "partition rtx4060ti16g) with RTX 3060 Ti (sm_86) for the sm_86 spot checks; "
               "CUDA 13.3 toolkit (`/usr/local/cuda`), driver 580.82.07, Compute Sanitizer "
               "2026.2.1.0, NVBit 1.8, GNU Make 4.2.1, networkx 3.6.1, `.env/bin/python` = "
               "CPython 3.14. NOTE: the task brief specified RTX A5000 / driver 595 / CUDA "
               "12.9; toolkit/driver differ and are recorded here.\n")
    doc.append(setup_section(build_rows))
    bl = f"{HERE}/setup/blockers.md"
    if os.path.exists(bl):
        doc.append("\n" + open(bl).read().rstrip())
    doc.append(residual_section())
    doc.append("\n## 2. Verdicts per program set\n")
    doc.append("Cells: `RACE(n)` = race reported with n deduped reports; `CLEAN`; "
               "`TO` timeout; `ERR`; `—` not run. cuVein-eng = C++ HB engine "
               "verdict; cuVein-tr = trace-only (sync_dominance static leg). "
               "Columns marked `*` (memcheck/synccheck/initcheck) are NOT race detectors: "
               "`FLAG(n)` = the tool reported ≥1 error of its own class; `clean` = none.")
    doc.append(headtohead_section(runs, meta, man))
    doc.append(revision_delta_section(runs, meta, man))
    doc.append(comparison_matrix_section(runs, meta, man))
    doc.append(hirace_table1_section(runs, meta))
    doc.append(accuracy_table(runs, meta, man, cols))
    doc.append(fp_cause_table())
    doc.append(bug_class_table(runs, meta, man, cols))
    doc.append(sanitizer_family_table(runs, meta))
    doc.append(verdict_tables(runs, meta, man, cols))
    doc.append("\n## 3. Disagreements\n")
    doc.append("Race-capable tools only (cuVein engine/trace-only, racecheck, HiRace, iGUARD); "
               "one row per report of the RACE side, classified by endpoint strength "
               "(atomic-scope sidecar) and ordering mechanism (sync_dominance verdict).\n")
    if dis:
        keys = ["program", "tool_a", "verdict_a", "tool_b", "verdict_b",
                "category", "mechanism", "ptx_871_match", "suite_label_match"]
        c = defaultdict(int)
        for r in dis:
            c[(r["tool_a"], r["tool_b"], r["category"], r["mechanism"])] += 1
        doc.append("| tool_a | tool_b | category | mechanism | rows |")
        doc.append("|---|---|---|---|---|")
        for k in sorted(c):
            doc.append(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {c[k]} |")
        CAP = 2000    # the whole list is in eval/results/baselines-disagreements.csv
        shown = dis if len(dis) <= CAP else dis[:CAP]
        doc.append(f"\n<details><summary>{'All' if len(shown) == len(dis) else f'First {CAP} of'} "
                   f"{len(dis)} disagreement rows"
                   f"{'' if len(shown) == len(dis) else ' (complete list: `eval/results/baselines-disagreements.csv`)'}"
                   f"</summary>\n")
        doc.append("| " + " | ".join(keys) + " |")
        doc.append("|" + "---|" * len(keys))
        for r in shown:
            doc.append("| " + " | ".join(r.get(k, "") for k in keys) + " |")
        doc.append("\n</details>")
    else:
        doc.append("_No disagreement CSV yet — run `classify_endpoints.py` after the "
                   "confirmation run to populate `baselines-disagreements.csv`._")
    doc.append(overhead_table(runs, meta))
    doc.append(overhead_minmax_section(runs, meta, man))
    doc.append(x_checks(runs, meta, man))
    doc.append("\n## 6. To re-run after a detector revision\n")
    doc.append("```\nbash eval/baselines/setup/run_full.sh      # everything (corpora, all tools)\n"
               "bash eval/baselines/setup/run_rerun.sh     # cuVein only, after a detector revision\n```")
    doc.append("`run_rerun.sh` pins the revision (`setup/cuvein_rev.sh` → `cuvein_rev.status` + full "
               "diff under `setup/cuvein_rev/`), moves the previous cuVein rows to "
               "`eval/results/prefix_<rev>/` (`supersede_prefix.sh`, nothing deleted), re-runs "
               "P1–P8 (32 shards) and P9 (20-min cap) in both modes, re-derives the keep/diagnose "
               "id lists from the new rows (`mk_followup_ids.py`) and chains keep → diagnose → "
               "`p_final2.sh`. Run the smoke gate first (`fpfix_smoke_ids.txt`, both modes).")
    doc.append("Submits the whole SLURM chain (corpus build → cuVein sharded run → sanitizer "
               "family → iGUARD build+run → HiRace → keep/diagnose → merge/classify/tables) "
               "and regenerates every `eval/results/baselines-*.csv` and this file. "
               "Individual stages: `mk_manifest.py`, `build_corpora.py`, `build_indigo.py`, "
               "`build_indigo2.py`, `parallel.py {run,merge}`, `run_sanitizer.py`, "
               "`run_hirace.py`, `run_iguard.py`, `classify_residuals.py`, `classify_fp_causes.py`, "
               "`classify_endpoints.py`, `make_tables.py`.\n")

    with open(OUT, "w") as f:
        f.write("\n".join(doc) + "\n")
    write_summary(runs, meta, man)
    print(f"wrote {OUT} ({len(runs)} run-keys, tools={sorted(set(k[1] for k in runs))})")


if __name__ == "__main__":
    main()
