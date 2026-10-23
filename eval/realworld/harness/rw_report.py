#!/usr/bin/env python3
"""T21b: render eval/REALWORLD.md section "2. Recall (T21b)" from eval/results/realworld/recall.csv (+ notes file
eval/realworld/harness/recall_notes.md, hand-written, copied verbatim after the tables). The section is appended at the end of
REALWORLD.md (an existing 'Recall (T21b)' section is replaced)."""
import csv, os, re, collections, json
WT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
rows = list(csv.DictReader(open(f"{WT}/eval/results/realworld/recall.csv")))
notes = open(f"{WT}/eval/realworld/harness/recall_notes.md").read(); pending = open(f"{WT}/eval/realworld/harness/recall_pending.md").read()
main = [r for r in rows if r["flavor"] == "main"]
out = ["## 2. Recall (T21b)", "", notes.rstrip(), ""]
# counts
out += ["### 2.1 Detected, by mode and expected_class (main flavor, buggy builds, rows scored so far)", "",
        "A target of class DR+SC has two components (DR pair, SC pair), counted separately. Outcome words as in the T21b brief; "
        "`DETECTED-AS-DR` = reported in the other class (D20 option (i)).", "",
        "| mode | expected_class | component | DETECTED | DETECTED-AS-other | MISSED | n |", "|---|---|---|---|---|---|---|"]
c = collections.defaultdict(collections.Counter)
for r in main:
    if r["variant"] != "buggy":
        continue
    o = r["outcome"]
    if o in ("VOID", "NOT-SCORED"):
        continue
    k = "DETECTED" if o.startswith("DETECTED") and not o.startswith("DETECTED-AS") else ("DETECTED-AS" if o.startswith("DETECTED-AS") else "MISSED")
    c[(r["mode"], r["expected_class"], r["component"])][k] += 1
for (m, e, comp), v in sorted(c.items()):
    n = sum(v.values())
    out.append(f"| {m} | {e} | {comp} | {v['DETECTED']} | {v['DETECTED-AS']} | {v['MISSED']} | {n} |")
out += ["", "### 2.2 Per target (main flavor; vc = vector-clock mode, sc = scalar-clock mode; fixed: outcome per mode)", "",
        "| target | wave | class | buggy vc | buggy sc | op. point (vc) | a2 | .STRONG | fixed vc | fixed sc | racecheck (buggy) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
out += ["", "`amrex-1` and `hecbench-hungarian-1` (buggy, both modes): **final m4** (TIMEOUT / ERROR at the X1b caps; see 2.6). They are listed as MISSED in the tables only because the scorer has no separate m4 outcome; they count as neither detected nor missed on the evidence."]
by = collections.defaultdict(dict)
for r in main:
    by[r["target"]][(r["variant"], r["mode"], r["component"])] = r
for t in sorted(by, key=lambda t: (list(by[t].values())[0]["wave"], t)):
    d = by[t]; any_ = list(d.values())[0]
    def cell(var, mode):
        rs = [r for (v, m, comp), r in d.items() if v == var and m == mode]
        return " / ".join(f"{(r['component']+': ') if r['component'] else ''}{r['outcome']}" for r in rs) or "-"
    vc = [r for (v, m, comp), r in d.items() if v == "buggy" and m == "vector-clock"]
    op = ", ".join(sorted({r["operating_point"] for r in vc if r["operating_point"]})) or ""
    a2 = ",".join(sorted({r["a2"] for r in vc if r["a2"]}))
    st = ",".join(sorted({r["strong_token"] for r in vc if r["strong_token"]}))
    rc = next((r["racecheck"] for r in vc), "")
    out.append(f"| {t} | {any_['wave']} | {any_['expected_class']} | {cell('buggy','vector-clock')} | {cell('buggy','scalar-clock')} | {op} | {a2} | {st} | {cell('fixed','vector-clock')} | {cell('fixed','scalar-clock')} | {rc} |")
other = [r for r in rows if r["flavor"] != "main" and not r["flavor"].startswith("longcap")]
if other:
    out += ["", "### 2.3 Other flavors (vector-clock only)", "", "| flavor | target | variant | component | run | outcome | operating point |", "|---|---|---|---|---|---|---|"]
    for r in other:
        out.append(f"| {r['flavor']} | {r['target']} | {r['variant']} | {r['component']} | {r['run_verdict']} | {r['outcome']} | {r['operating_point']} |")

out += ["", "### 2.5 Changes by the attribution parser fix (D-T2) and by the Opus triage (`triage_opus.md`, 7eb1eb9)", "",
        "D-T2: `rw_attribute.cubin_frames` ran `nvdisasm --print-line-info-inline` without `-c` and let a non-`.text` section's `/*offset*/` lines "
        "overwrite the frames of the current function; fixed by `-c` and by resetting the current function at every `.section` line. Check on "
        "`eval/realworld/defects/attrib-global-init-frames/` (`dt2_fix_check.txt`): the STS at line 12 and the LDS at line 14 attribute to 12 and 14. "
        "Every target and flavor already run was re-attributed on `normal` and rescored; the old table is `eval/results/realworld/recall_before_dt2.csv`.", "",
        "| target | variant | mode | flavor | old | new | reason |", "|---|---|---|---|---|---|---|"]
old = {(r["target"], r["variant"], r["mode"], r["flavor"], r["component"]): r for r in csv.DictReader(open(f"{WT}/eval/results/realworld/recall_before_dt2.csv"))}
for r in rows:
    k = (r["target"], r["variant"], r["mode"], r["flavor"], r["component"])
    if k in old and old[k]["outcome"] != r["outcome"] and old[k]["outcome"] not in ("VOID", "NOT-SCORED"):
        out.append(f"| {r['target']} | {r['variant']} | {r['mode']} | {r['flavor']} | {old[k]['outcome']} | {r['outcome']} ({r['operating_point']}) | attribution parser fix (D-T2) |")
out += ["", "Rows new since that table (void or unrun before) are not D-T2 changes: `llamacpp-2/-4/-5` (re-run after Defect 1), `cmssw-1` `certain`.", "",
        "Opus triage outcomes applied: the 4 `DETECTED-AS-DR` rows (`opencv-2`, `lit-shoc-1` SC half, both modes) stay (SASS of volatile shared on sm_89 has no `.STRONG` token; D20 option (i)); "
        "the 9 `RESIDUAL-AS-EXPECTED` rows are confirmed; `cccl-1` outcomes are final (D-T1 decided by Jeffery, \"score it\": kernels with `tv_violation` are scored as normal): buggy DETECTED, fixed STILL-REPORTED, both modes; the fixed-build reports trace back to the syncwarp-record detector defect D-T3 (the trace records `__syncwarp(0x3fffff)` with mask 0xffffffff; its fix is post-deadline and not applied here); "
        "`recall.csv` has a `tv_violation` column (kernel JSONs with `tv_violation` / kernel JSONs, fact only, from `harness/scan_tv.py`): set only on the four `cccl-1` stores "
        "(buggy and fixed, both modes); `hecbench-hungarian-1` (whose fix adds `__syncwarp`): 0 of 6,874 (vector-clock) and 0 of 7,018 (scalar-clock) kernel JSONs of the fixed build, but those are the truncated long-cap collections (2.6); no main-flavor run of the fixed build exists yet, and the buggy main-flavor stores have 0. The `cccl-1` reports in the other-reports queue "
        "(artifacts of the syncwarp-record defect) were moved to `other_reports_removed.csv`; the `lit-fbgemm-1` duplicate disappeared because the pair now matches."]
out += ["", "### 2.6 Long-cap pass: not run", "",
        "Jeffery's separate pass (tool cap 84,600 s inside 24 h jobs, collection on a GPU node, analysis on `normal`) for `amrex-1`, `hecbench-hungarian-1` and `llamacpp-2` was **not run**. "
        "Decision: `amrex-1` and `hecbench-hungarian-1` stay **final m4** (TIMEOUT / ERROR at the X1b caps: vector-clock 1,200 s, analysis timeout 3,600 s); "
        "they are neither detected nor missed on the evidence. The attempted collections were void and the jobs were cancelled (collection jobs 319051-319060, analysis jobs 319139-319146). "
        "Harness defect, not fixed: `eval/baselines/parallel.py` `cmd_collect` passes `--timeout-cap` to `collect_one` but drops `--timeout-floor`, so `collect` used the default floor of 120 s and "
        "the tool timeout was `min(max(10 x native, 120), 84,600)` = 120 s (`timeout=120s`, rc 124, `nkernels=0` in the notes of the amrex-1 rows; the hecbench-hungarian-1 collections ended in about 2 minutes). "
        "One-line fix: `collect_one(m, cuda, a.reps, floor=getattr(a, \"timeout_floor\", 120), cap=...)`. The `main` flavor is unaffected (the `run` command passes both). "
        "The void rows are not in `recall.csv`; their files remain under `eval/results/realworld/longcap-*/`. `llamacpp-2/-4/-5` are with the fresh Opus triage (`triage_llamacpp.md`); their rows are unchanged until it lands."]
sec = "\n".join(out) + "\n"
p = f"{WT}/eval/REALWORLD.md"
s = open(p).read()
i = s.find("## 2. Recall (T21b)")
if i >= 0:
    s = s[:i]
if not s.endswith("\n"):
    s += "\n"
open(p, "w").write(s + "\n" + sec)
print("REALWORLD.md section written,", len(sec), "bytes")
