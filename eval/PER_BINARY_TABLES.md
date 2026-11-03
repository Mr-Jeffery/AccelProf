# X10 — accuracy tables per binary (2026-11-03)

Branch `eval/per-binary-tables`, from `eval/cap-84600` (3de35b2) with `eval/sc-all-inputs` (X8, SuperCollider on all
seven inputs) and `eval/co-offline` (C4, collector-only re-scoring) merged (`fa25cde`, `fbfb030`; no conflicts).
Tables only: no GPU, no recording, no results CSV touched. Code changed: `eval/baselines/make_tables.py` (the fold)
and the new `eval/baselines/test_make_tables_fold.py`. Computed in the claude.ai workspace (Linux, Python 3), not on
the cluster.

## 0. What changed and how to reproduce

- `make_tables.py --unit binary` (the default now) writes `eval/BASELINES_SUMMARY.md` with table 1 per binary and
  `eval/BASELINES_SUMMARY_PER_RUN.md` with the per-run summary (appendix version). `eval/BASELINES.md` (the full
  document) is unchanged and per run.
- `make_tables.py --unit run` reproduces the previous `BASELINES_SUMMARY.md` and `BASELINES.md` **byte for byte**
  (checked with `git diff` on the merged branch: no change). `BASELINES_SUMMARY_PER_RUN.md` equals it apart from
  the title line.
- Unit: one binary = the manifest's `exe`. Fold: RACE if any run reports; CLEAN if every run finished and none
  reports; TIMEOUT if a run timed out and none reports; otherwise ERROR. Same rule for every tool. A binary whose
  runs carry different labels raises (none does). HiRace and SuperCollider rows carry our manifest ids, so their
  instrumented builds fold into the same binary. Table 2 (overhead) stays per run.
- New rows: cuHadron in scope (without `hostdevice/*`, `interkernel/*`, `asyncmemcpy/*`), with SuperCollider on
  the same denominator as every tool, and a fourth aggregate "SuperCollider-matched, in scope".
- Footnote 8 per binary reads both oracle CSVs (`baselines-pi-oracle.csv`, `-x8.csv`; the per-run table reads only
  the first).

Commands: `python3 eval/baselines/make_tables.py --unit run` (parity), `python3 eval/baselines/make_tables.py`,
`python3 -m pytest -q eval/baselines/test_make_tables_fold.py` → **11 passed**. No other test file exists under
`eval/baselines/`.

## 1. Table 1 per binary

In `eval/BASELINES_SUMMARY.md` §1 (all tools, the two clock modes, notes per detector). Collector-only mode
(C4's re-scoring, read from `eval/results/co-offline/merged/baselines-cuvein-cor.csv`, the CSV `--co-offline`
uses in C4's sandbox) per suite:

| row | per run | per binary |
|---|---|---|
| P1 | 200/200, 0/200, 0, 0 | 100/100, 0/100, 0, 0 |
| PI | 1738/1862, 224/1260, 0, 0 | 266/266, 32/180, 0, 0 |
| PI@sc | 43/45, 4/44, 0, 0 | 43/45, 4/44, 0, 0 |
| PI@sc7 | 294/315, 28/308, 0, 0 | 45/45, 4/44, 0, 0 |
| P3 | -, 16/60, 0, 0 | -, 16/60, 0, 0 |
| P4 | 14/14, 6/14, 0, 0 | 7/7, 3/7, 0, 0 |
| P5 | 3/19, 0/14, 0, 0 | 3/19, 0/14, 0, 0 |
| P6 | 7/13, 1/21, 0, 16 | 7/13, 1/21, 0, 16 |
| P6@in | 6/6, 0/14, 0, 16 | 6/6, 0/14, 0, 16 |
| P7 | -, -, 1, 0 | -, -, 1, 0 |
| P9 | 3/4, 1/5, 1, 0 | 3/4, 1/5, 1, 0 |

| TOTAL All pre-registered labelled suites (Indigo3 + Indi | | 383/405, 52/382, 0, 16 |
| TOTAL SuperCollider-matched suites (cuHadron + the 99-te | | 53/62, 6/70, 1, 16 |
| TOTAL SuperCollider-matched suites, second view (cuHadro | | 55/62, 6/70, 1, 16 |
| TOTAL in scope | | 54/55, 5/63, 1, 16 |

The committed summary is generated without `--co-offline`, as before; with C4's CSV linked into `eval/results/`
(`p_co_offline_tables.sh`'s method) the same code adds the column.

## 2. ids → binaries

| suite | ids | binaries |
|---|---|---|
| Indigo3 | 400 | 200 (100 codes × default / `-DSLOWER_ATOMIC`) |
| Indigo 1.3 | 4,130 | 590 |
| — SuperCollider's 99, own input | 99 | 99 |
| — SuperCollider's 99 × 7 inputs | 693 | 99 |
| ECL | 60 | 60 (one input each, from the manifest) |
| ScoR applications | 28 | 14 |
| ScoR litmus + canary | 33 | 33 |
| cuHadron | 50 | 50 (34 runnable) |
| — in scope | 36 | 36 (20 runnable) |
| HeCBench overhead | 14 | 14 |
| HeCBench SC subset | 10 | 10 |

Key function: `binary_key()` = manifest `exe`; the counts are asserted in `comparison_matrix_binary_section`.
No tool ran a binary on only some of its inputs (footnote 7: none).

## 3. Indigo3 build agreement

Codes whose default and `-DSLOWER_ATOMIC` binaries get different verdicts: cuRace vector-clock **0**, scalar-clock
**0**, collector-only **0**; racecheck 0; compute-sanitizer (any) 0; **iGUARD 8 of 100**. All 8 are race-free BFS
codes reported on the default build only (iGUARD class `Missing blkfence`, at a `ST.E.STRONG.SYS` or
`ATOMG.E.MIN.S32.STRONG.GPU` — the `cuda::atomic` relaxed store / `atomicMin` of the default helpers) and clean
on the `-DSLOWER_ATOMIC` build, where the same accesses are RMW atomics:
BFS_CUDA_E_Data_IntType_ReadWrite_{{NonPersist…NoExcessThreadsBug, Persist…NoBoundsBug}},
BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite_{{NonPersist, Persist}},
BFS_CUDA_E_Topo_NonDeterm_IntType_{{ReadModifyWrite, ReadWrite}}_{{NonPersist, Persist}}.

## 4. Footnote 8 per binary

The oracle covers all seven inputs of all 266 racy-labelled Indigo 1.3 binaries. **None** of them is conflict-free
on every input (every planted race fires on some graph), and none of the 180 race-free binaries shows a conflict.
Per binary, cuRace (both clock modes) and HiRace miss no racy binary; the FN binaries of the others are all real
misses: racecheck 226, iGUARD 8, SuperCollider 3 (of its 45). The per-run 148 FN rows are all inputs on which the
binary's race does not fire.

## 5. Aggregates, per run vs per binary

**All pre-registered labelled suites (Indigo3 + Indigo origina…**

| tool | per run | per binary |
|---|---|---|
| cuVein-VC | 1938/2108, 20/1569, 0, 16 | 383/405, 19/382, 0, 16 |
| cuVein-SC | 1937/2108, 19/1569, 0, 16 | 382/405, 18/382, 0, 16 |
| racecheck | 288/2107, 0/1569, 1, 16 | 48/404, 0/382, 1, 16 |
| sanitizer(any) | 307/2108, 37/1569, 0, 16 | 63/405, 33/382, 0, 16 |
| HiRace | 1714/1862, 0/1260, 0, 0 | 266/266, 0/180, 0, 0 |
| iGUARD | 1761/2107, 794/1568, 2, 16 | 380/404, 217/381, 2, 16 |
| SuperCollider | 271/328, 0/329, 0, 16 | 51/58, 0/65, 0, 16 |

**SuperCollider-matched suites (cuHadron + the 99-test subset …**

| tool | per run | per binary |
|---|---|---|
| cuVein-VC | 52/61, 1/70, 2, 16 | 52/61, 1/70, 2, 16 |
| cuVein-SC | 52/61, 1/70, 2, 16 | 52/61, 1/70, 2, 16 |
| racecheck | 7/61, 0/70, 2, 16 | 7/61, 0/70, 2, 16 |
| sanitizer(any) | 8/61, 0/70, 2, 16 | 8/61, 0/70, 2, 16 |
| HiRace | 43/45, 0/44, 0, 0 | 43/45, 0/44, 0, 0 |
| iGUARD | 41/60, 29/69, 4, 16 | 41/60, 29/69, 4, 16 |
| SuperCollider | 53/63, 0/70, 0, 16 | 53/63, 0/70, 0, 16 |

**SuperCollider-matched suites, second view (cuHadron + the 99…**

| tool | per run | per binary |
|---|---|---|
| cuVein-VC | 301/331, 1/334, 2, 16 | 54/61, 1/70, 2, 16 |
| cuVein-SC | 301/331, 1/334, 2, 16 | 54/61, 1/70, 2, 16 |
| racecheck | 25/331, 0/334, 2, 16 | 7/61, 0/70, 2, 16 |
| sanitizer(any) | 26/331, 0/334, 2, 16 | 8/61, 0/70, 2, 16 |
| HiRace | 292/315, 0/308, 0, 0 | 45/45, 0/44, 0, 0 |
| iGUARD | 248/330, 149/333, 4, 16 | 43/60, 31/69, 4, 16 |
| SuperCollider | 276/333, 0/334, 0, 16 | 56/63, 0/70, 0, 16 |

**in scope…**

| tool | per run | per binary |
|---|---|---|
| cuVein-VC | 300/324, 0/327, 2, 16 | 53/54, 0/63, 2, 16 |
| cuVein-SC | 300/324, 0/327, 2, 16 | 53/54, 0/63, 2, 16 |
| racecheck | 25/324, 0/327, 2, 16 | 7/54, 0/63, 2, 16 |
| sanitizer(any) | 26/324, 0/327, 2, 16 | 8/54, 0/63, 2, 16 |
| HiRace | 292/315, 0/308, 0, 0 | 45/45, 0/44, 0, 0 |
| iGUARD | 248/324, 149/327, 2, 16 | 43/54, 31/63, 2, 16 |
| SuperCollider | 272/326, 0/327, 0, 16 | 52/56, 0/63, 0, 16 |



## 6. Paper cells

`eval/per_binary_paper_cells.md`.

## 7. What remains unverified

- Computed in the claude.ai workspace from the committed CSVs, not on the cluster; nothing depends on the cluster.
- Indigo3's memory-space split is settled in §8 from the generator source. Indigo 1.3's split rests on the
  space of cuRace's reported pairs and racecheck's reports (§8), not on its source.
- The paper's HeCBench rows (atomicCAS and knn scored race-free, expdist) come from a relabel that is not in
  `make_tables.py`; they are one run per binary and do not change.

## 8. Memory space of the labelled races (added 2026-11-03)

The paper states that 196 of the 200 Indigo3 races lie in global memory and that racecheck finds 4 of 4 within shared
memory. No experiment recorded that split: the manifest's `shared_mem` is 0 for every Indigo row, so
`make_tables.py` labels every racecheck miss "global", and the shared-memory count equals racecheck's own detections.

**Independent evidence 1, cuRace's reports.** Every reported pair carries its space (`shared:` / `global:` in
`report_ids`, scalar-clock rows). Per binary:

| suite | racy binaries | global pairs only | shared pairs only | both | racecheck reports |
|---|---|---|---|---|---|
| Indigo 1.3 | 266 | 226 | 16 | 24 | the 40 with a shared pair, none of the 226 |
| Indigo3 | 100 | 76 | 0 | 24 | 4 of the 24 with a shared pair |

**Independent evidence 2, the Indigo3 generator** (`burtscher/Indigo3Suite`, `codeGen/cuda/CC-CUDA/`, read, not
run). `RaceBug` replaces the atomics on the global arrays `label` / `label_n` with plain loads and stores
(`CC_CUDA_V_Data_Pull.idg` lines 74, 77, 97, 104, 115–127; the same in `CC_CUDA_V_Data_Push.idg`). The planted race
is therefore in global memory in every racy Indigo3 code: 100 of 100 binaries, 200 of 200 runs.

The 24 binaries with a shared pair are the CC `Warp` and `Block` codes. Their shared pairs come from the flag
`__shared__ bool updated`, which the template declares in every variant, the race-free `Atomic` ones included:

- `updated = true` is written by every thread that lowers its label (`CC_CUDA_V_Data_Pull.idg:100`, `Push:154`).
  It is a same-value write from one PC, a data race under PTX, of the same kind as ECL's idempotent
  `updated = true`. cuRace reports it on all 24 (`shared:<pc>-<pc>:WAW`).
- In the persistent pull codes with a block per vertex, thread 0 resets `updated = false` at the top of the next
  iteration (line 85) while the other threads may still read it (`if (updated)`, line 110). The barrier that
  would separate them sits after the loop (lines 139–141), not inside it. The push template has the barrier inside
  its loop (line 178), so its persistent codes do not have this WAR. cuRace reports it as `shared:…:WAR`.

racecheck reports exactly the four `Pull…Persist…Block` binaries (2 codes × 2 atomic builds), each at two
generated `.cu` lines (76 and 91 in the `Determ` code, 74 and 87 in the `NonDeterm` one). That these are the reset
and the read is inferred from the template, not checked against the generated file, which was not produced here. It reports none of the 20 binaries that have only the same-value write.

Consequences:

- Indigo3 has no planted race in shared memory. racecheck's 4 Indigo3 detections are true races in the
  scaffolding, but not the labelled race. Under label-level scoring they count as TPs. "4 of 4 within shared
  memory" has no denominator on Indigo3.
- The same reset/read WAR is in the race-free `Atomic` variants of the persistent block pull codes. Those variants
  are not in the stratified sample: its race-free half is all BFS, whose `updated` is thread-local. The sample
  therefore cannot show it as a false positive of any tool.
- cuRace's extra shared reports on the 24 binaries are races under PTX, reported alongside the planted global
  race. They change no per-binary verdict.
- Indigo 1.3's split (226 / 40) agrees with both cuRace's spaces and racecheck's reports. It was not read from
  the Indigo 1.3 source.

Not verified: whether racecheck reports a same-value write-write hazard at all. It reported none of the 20, but
this was not tested on a micro kernel. Not run: the generated codes (the session's policy blocks running
downloaded generator scripts). Line numbers refer to the templates at the clone of 2026-11-03.
