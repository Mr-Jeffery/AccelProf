#!/usr/bin/env python3
"""T21b: render eval/REALWORLD.md section "2. Recall (T21b)" from eval/results/realworld_t21c/recall.csv (+ notes file
eval/realworld/harness/recall_notes.md, hand-written, copied verbatim after the tables). The section is appended at the end of
REALWORLD.md (an existing 'Recall (T21b)' section is replaced)."""
import csv, os, re, collections, json
WT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
rows = list(csv.DictReader(open(f"{WT}/eval/results/realworld_t21c/recall.csv")))
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
out += ["", "`amrex-1` (buggy, both modes): **final m4** (see 2.6). It is listed as MISSED in the tables only because the scorer has no separate m4 outcome; it counts as neither detected nor missed on the evidence. `hecbench-hungarian-1` was m4 and is scored since the reanalysis and recording of 2.6."]
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
        "Every target and flavor already run was re-attributed on `normal` and rescored; the old table is `eval/results/realworld_t21c/recall_before_dt2.csv`.", "",
        "| target | variant | mode | flavor | old | new | reason |", "|---|---|---|---|---|---|---|"]
old = {(r["target"], r["variant"], r["mode"], r["flavor"], r["component"]): r for r in csv.DictReader(open(f"{WT}/eval/results/realworld_t21c/recall_before_dt2.csv"))}
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
out += ["", "### 2.6 Long-cap pass: not run; m4 reanalysis (amrex-1, hecbench-hungarian-1)", "",
        "Jeffery's separate long-cap pass (tool cap 84,600 s inside 24 h jobs) for `amrex-1`, `hecbench-hungarian-1` and `llamacpp-2` was **not run**: its collections were void and the jobs were cancelled (collection jobs 319051-319060, analysis jobs 319139-319146). "
        "Harness defect, not fixed: `eval/baselines/parallel.py` `cmd_collect` passes `--timeout-cap` to `collect_one` but drops `--timeout-floor`, so `collect` used the default floor of 120 s and the tool timeout was `min(max(10 x native, 120), 84,600)` = 120 s "
        "(`timeout=120s`, rc 124, `nkernels=0` in the notes of the amrex-1 rows). One-line fix: `collect_one(m, cuda, a.reps, floor=getattr(a, \"timeout_floor\", 120), cap=...)`. The `main` flavor is unaffected (the `run` command passes both). "
        "The void rows are not in `recall.csv`; their files remain under `eval/results/realworld_t21c/longcap-*/`.", "",
        "Instead, CPU reanalysis of the existing recordings with `run_cuvein.py` 0d30817 (dots that name the kernel first) and `--analysis-timeout 82800`, array 319392:", "",
        "- **`hecbench-hungarian-1`: m4 lifted.** Buggy: same main-store recording, reanalyzed (319392_2, c33): RACE in both modes (vector-clock 293 structural + 243 SC, scalar-clock 293 race + 241 SC); oracle kernel seen in 974 kernel JSONs, 14 site verdicts. "
        "Fixed: the main flavor had never produced a recording (all 6 retries died on BeeGFS), so it was recorded fresh into the main store, both modes, cap 1200 (GPU job 319540, c28, 5.6 min) and analyzed on CPU (319541): RACE in both modes (vector-clock 241 structural + 247 SC, scalar-clock 240 + 243 SC); 4 site verdicts. "
        "Both are scored per the oracle and D20 option (i) (2.2); `tv_violation` is 0 of 6,910 / 6,946 (buggy) and 0 of 7,000 / 6,898 (fixed) kernel JSONs. The REVIEW.md item 2 residual label for the fixed build is scored as committed.",
        "- **`amrex-1`: final m4.** Scalar-clock reanalysis (319392_0 buggy, 319392_1 fixed): ERROR at `--analysis-timeout` 82,800 s after about 23 h, and the attribution was then cut off by the 24 h job limit. "
        "Vector-clock long-cap re-recording of the buggy build (319403, c44, 125 GB node): killed for running out of memory at 60,717 s, MaxRSS 122 GiB, no kernel JSON. Jeffery's decision: \"M4 is okay\", no retry on a 188 GB node.",
        "", "`llamacpp-2/-4/-5`: see 2.7."]
out += ["", "### 2.7 llamacpp-2/-4/-5: Opus triage (`eval/realworld/triage_llamacpp.md`, 1efb1ac)", "",
        "`llamacpp-2/-4` ERROR (scored m4 before): not a detector failure. `run_cuvein._analyze_reports` tried every `.dot` of the program in sorted order for each kernel JSON; llamacpp builds ship many large dots, so the search alone passed `--analysis-timeout 3600`. Fixed by 0d30817 (dots that name the kernel first; verdicts unchanged, only time). "
        "Reanalysis of the main-flavor recordings (nothing re-recorded): `llamacpp-2` buggy DETECTED, fixed CLEAN-FOR-PAIR (both oracle site pairs ORDERED, barrier-ordered); `llamacpp-4` buggy DETECTED, fixed CLEAN-FOR-PAIR; "
        "`llamacpp-5` buggy MISSED -> DETECTED (the MISSED came from a stale pre-D-T2 attribution; re-attributed with the fixed parser, all 16 oracle site pairs RACE, structural; the m1/m3 proposal is withdrawn), fixed stays CLEAN-FOR-PAIR. All in both modes. "
        "Effect on the DR component, main flavor, buggy builds: 19 detected / 4 missed -> 22 detected / 1 missed (the miss is `amrex-1`, final m4).", "",
        "Known unfixed side defect (cosmetic): `eval/baselines/parallel.py` lines 296-299 build the pc -> line map with `pcmap.update(...)` over every cubin of the executable; pcs are per-cubin offsets, so a pc present in several cubins keeps the line of the last cubin and the CSV column `report_lines` is wrong for multi-cubin builds "
        "(`llamacpp-4` buggy shows `fattn-tile.cuh:1131` for a `softmax.cu` race). Scoring does not use that column, so no outcome changes."]
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
