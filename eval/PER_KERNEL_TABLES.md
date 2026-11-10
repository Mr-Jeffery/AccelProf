# X13 - accuracy per kernel (2026-11-10)

Branch `eval/per-kernel-tables` (worktree `/home/fzheng4/wt-x13`), from X10 (per-binary tables, `b7421b45`). Measurement and tables only:
no change to `python/`, `sanalyzer/`, `nv-compute/`, `bin/`, `hb_oracle.py`; no recording of cuRace, racecheck, iGUARD or HiRace; no existing results CSV or store changed.
The only code outside `eval/baselines/per_kernel/` that changed: `eval/baselines/make_tables.py` (`--unit kernel`, 6 lines) and the one permitted conflict resolution in `eval/baselines/parallel.py` (section 7).
The only GPU work: step 3b, job 331594 (SuperCollider on three HeCBench programs, 15 rows).

Unit: one kernel = one `__global__` function (one template instantiation = one kernel) of one binary. A kernel's verdict for a tool and mode folds every launch of every run of its binary:
RACE if any run has a report attributed to it; CLEAN if every run has a finished launch of it and none reports; TO if some run has no finished launch of it (and that run is a TIMEOUT run) and none reports; ERR otherwise.
A kernel no run launched is not counted (`fold_kernel` in `eval/baselines/per_kernel/kfold.py`).

## 0. Inputs (steps 0a-0c)

- **0a.** Ancestors of `b7421b45` already: `eval/final-sweep-b` (X1b final sweep, `94fde732`), `eval/cap-84600` (`3de35b29`), `eval/sc-all-inputs` (`e4084279`) - nothing to merge.
  `eval/co-chain-b` (`f31a5067`) conflicts in `CLAUDE.md`, `eval/baselines/parallel.py`, `python/sync_dominance.py`: **data-only import** of `eval/results/co-chain-b/` (commit `08161a40`, decided by Jeffery); no code from it.
  Table 4's HeCBench row comes from X11 (`coverage.tex` % comment of 2026-11-07; `eval/results/sc_native/summary.csv`): `eval/sc-native-hecbench` (`5ee0e3d0`) merged (`d881d072`), one conflict (section 7). The row is SuperCollider's 10 applications on the artifact's native binaries; every tool's lines on them are mapped against HeCBench `6a8c46c4`.
- **0b. Gate (`--unit run`, the paper's `numbers/table-accuracy.csv` is per program-input; Indigo 1.3 rows per code).** Every cell of `coverage.tex` / `numbers/table-accuracy.csv` is reproduced; no cell differs. Computed by `eval/baselines/per_kernel/gate_table4.py` (imports `make_tables`' loaders and confusion functions; `make_tables.py` itself writes `eval/BASELINES*.md`, which I did not overwrite). Output `eval/results/per-kernel/gate_run.md`:

| suite | kind | labels (racy/free/unl) | racecheck | iGUARD | HiRace | SuperCollider | collector-only | scalar-clock | vector-clock |
|---|---|---|---|---|---|---|---|---|---|
| Indigo3 | recall | 200/200 | 4/200 | 196/200 | - | - | 200/200 | 200/200 | 200/200 |
| | FP | | 0/200 | 100/200 | - | - | 0/200 | 0/200 | 0/200 |
| Indigo 1.3 | recall | 266/180 | 40/266 | 258/266 | 266/266 | 42/45 | 266/266 | 266/266 | 266/266 |
| | FP | | 0/180 | 108/180 | 0/180 | 0/44 | 32/180 | 0/180 | 0/180 |
| Indigo 1.3, SC's 99 | recall | 45/44 | 3/45 | 42/45 | 45/45 | 42/45 | 45/45 | 45/45 | 45/45 |
| | FP | | 0/44 | 24/44 | 0/44 | 0/44 | 4/44 | 0/44 | 0/44 |
| ScoR applications | recall | 14/14 | 0/13, 1 TO/ERR | 12/14 | - | - | 14/14 | 14/14 | 14/14 |
| | FP | | 0/14 | 7/14 | - | - | 8/14 | 2/14 | 2/14 |
| cuHadron (20 in scope) | recall | 14/22 | 4/6, 16 TO/ERR | 1/6, 16 TO/ERR | - | 9/13, 16 TO/ERR | 6/6, 16 TO/ERR | 6/6, 16 TO/ERR | 6/6, 16 TO/ERR |
| | FP | | 0/14 | 4/14 | - | 0/21 | 0/14 | 0/14 | 0/14 |
| HeCBench, SC's 10 | recall | 5/5 | 3/5 | 2/5 | - | 5/5 | 5/5 | 4/4, 1 TO/ERR | 3/3, 2 TO/ERR |
| | FP | | 0/5 | 3/5 | - | 0/5 | 1/5 | 0/5 | 0/5 |
| All (P1+PI+P4+P6@in) | recall | | 48/485, 17 TO/ERR | 467/486, 16 TO/ERR | 266/266 | 51/58, 16 TO/ERR | 486/486, 16 TO/ERR | 486/486, 16 TO/ERR | 486/486, 16 TO/ERR |
| | FP | | 0/408 | 219/408 | 0/180 | 0/65 | 40/408 | 2/408 | 2/408 |

  The cuHadron cells carry "16 TO/ERR" in my output: the 16 sm_90 binaries (no executable, counted ERR by every tool); `coverage.tex` does not print them. The All row's racecheck "17 TO/ERR" = 1 TO (ScoR) + those 16; the paper prints "1 TO".
  Feeding CSVs per column: racecheck = `baselines-sanitizer.csv` (+ X11 `eval/x_logs/x11/stageB/x11b-racecheck-*/racecheck.csv` for the five re-run HeCBench rows); iGUARD = `baselines-iguard.csv` / `cap-84600/baselines-iguard.csv` (+ X11 `x11b-iguard-*`); HiRace = `baselines-hirace.csv`; SuperCollider = `baselines-supercollider.csv` + `baselines-supercollider-allinputs.csv`; vector-clock and scalar-clock = `eval/results/final-b/merged/baselines-cuvein.csv` (X1b) with the HeCBench cells from X11 stage B; collector-only = `eval/results/co-chain-b/merged-s1/baselines-cuvein.csv` (S1) with the HeCBench cells from X11 stage A (`stageA-chain-*`, chain closure only).
  `--unit binary` (X10), reported beside it, not gated (`gate_binary.md`):

| suite | kind | labels (racy/free/unl) | racecheck | iGUARD | HiRace | SuperCollider | collector-only | scalar-clock | vector-clock |
|---|---|---|---|---|---|---|---|---|---|
| Indigo3 | recall | 100/100 | 4/100 | 100/100 | - | - | 100/100 | 100/100 | 100/100 |
| | FP | | 0/100 | 52/100 | - | - | 0/100 | 0/100 | 0/100 |
| Indigo 1.3 | recall | 266/180 | 40/266 | 258/266 | 266/266 | 42/45 | 266/266 | 266/266 | 266/266 |
| | FP | | 0/180 | 108/180 | 0/180 | 0/44 | 32/180 | 0/180 | 0/180 |
| Indigo 1.3, SC's 99 | recall | 45/44 | 3/45 | 42/45 | 45/45 | 42/45 | 45/45 | 45/45 | 45/45 |
| | FP | | 0/44 | 24/44 | 0/44 | 0/44 | 4/44 | 0/44 | 0/44 |
| ScoR applications | recall | 7/7 | 0/6, 1 TO/ERR | 7/7 | - | - | 7/7 | 7/7 | 7/7 |
| | FP | | 0/7 | 4/7 | - | - | 4/7 | 1/7 | 1/7 |
| cuHadron (20 in scope) | recall | 14/22 | 4/6, 16 TO/ERR | 1/6, 16 TO/ERR | - | 9/13, 16 TO/ERR | 6/6, 16 TO/ERR | 6/6, 16 TO/ERR | 6/6, 16 TO/ERR |
| | FP | | 0/14 | 4/14 | - | 0/21 | 0/14 | 0/14 | 0/14 |
| HeCBench, SC's 10 | recall | 5/5 | 3/5 | 2/5 | - | 5/5 | 5/5 | 4/4, 1 TO/ERR | 3/3, 2 TO/ERR |
| | FP | | 0/5 | 3/5 | - | 0/5 | 1/5 | 0/5 | 0/5 |
| All (P1+PI+P4+P6@in) | recall | | 48/378, 17 TO/ERR | 366/379, 16 TO/ERR | 266/266 | 51/58, 16 TO/ERR | 379/379, 16 TO/ERR | 379/379, 16 TO/ERR | 379/379, 16 TO/ERR |
| | FP | | 0/301 | 168/301 | 0/180 | 0/65 | 36/301 | 1/301 | 1/301 |

- **0c. Kept stores.** `eval/results/per-kernel/store_scan.csv` (job 330056) lists kernel JSONs per (store, id, mode): X1b `final-2026-11` (+`-long`, `-long-sc`, `-24h-vc`, `-24h-sc`) and `final-2026-11-co` (+`-co-long`, `-co-24h`). Every table id has kernel JSONs in its mode directory except the 16 cuHadron sm_90 ids (no binary, no store: the same 16 the paper counts as ERR). X11's rows: `x11b-<mode>-<app>-r<k>` (clock modes), `x11-co-r<k>[-<app>]` (collector-only); atomicCAS: vector-clock and scalar-clock not run at the 84,600 s cap (TIMEOUT, no kernel JSON; scalar-clock recorded TO per `coverage.tex`, X11 jobs 329004/329005 pending, section 7), expdist vector-clock: recorded (4 kernel JSONs) but the verdict step ran out of memory (108 GB): no analysis output, TIMEOUT. No row of the table is without a store.

## 1. The per-kernel Table 4 and the side-by-side

Per kernel (`eval/results/per-kernel/table4_kernel.md`; `python eval/baselines/make_tables.py --unit kernel`; cells `table4_kernel_cells.csv`). Cell = TP/(TP+FN) on a recall row, FP/(FP+TN) on a false-positive row, TO/ERR kernels after a comma. Header = racy / race-free / unlabelled kernels. cuHadron: in-scope view for every tool except SuperCollider, which counts all 34 runnable binaries (38 kernels: the four `interkernel/*` binaries have two kernels, labels proposed in section 5). Tridiagonal labels are the agent's proposal adopted by Jeffery without review (section 5).

| suite | kind | racy / race-free / unlabelled kernels | racecheck | iGUARD | HiRace | SuperCollider | collector-only | scalar-clock | vector-clock |
|---|---|---|---|---|---|---|---|---|---|
| Indigo3 | recall | 100 / 300 / 0 | 4/100 | 100/100 | - | - | 100/100 | 100/100 | 100/100 |
| | FP | | 0/300 | 52/300 | - | - | 0/300 | 0/300 | 0/300 |
| Indigo 1.3 | recall | 266 / 180 / 144 | 40/266 | 258/266 | 266/266 | 42/45 | 266/266 | 266/266 | 266/266 |
| | FP | | 0/180 | 108/180 | 0/180 | 0/44 | 32/180 | 0/180 | 0/180 |
| Indigo 1.3, SC's 99 | recall | 45 / 44 / 10 | 3/45 | 42/45 | 45/45 | 42/45 | 45/45 | 45/45 | 45/45 |
| | FP | | 0/44 | 24/44 | 0/44 | 0/44 | 4/44 | 0/44 | 0/44 |
| ScoR applications | recall | 11 / 13 / 0 | 0/8, 3 TO/ERR | 11/11 | - | - | 11/11 | 11/11 | 11/11 |
| | FP | | 0/13 | 4/13 | - | - | 8/13 | 1/13 | 1/13 |
| cuHadron (in scope; SuperCollider: all 34) | recall | 6 / 14 / 0 | 4/6 | 1/6 | - | 9/15 | 6/6 | 6/6 | 6/6 |
| | FP | | 0/14 | 4/14 | - | 0/23 | 0/14 | 0/14 | 0/14 |
| HeCBench, SC's 10 | recall | 15 / 34 / 0 | 4/15 | 9/15 | - | 15/15 | 15/15 | 6/6, 9 TO/ERR | 4/4, 13 TO/ERR |
| | FP | | 0/34 | 6/34 | - | 0/34 | 6/34 | 2/34 | 0/32 |
| All (P1+PI+P4+P6@in) | recall | 383 / 507 / - | 48/380, 3 TO/ERR | 370/383 | 266/266 | 51/60 | 383/383 | 383/383 | 383/383 |
| | FP | | 0/507 | 168/507 | 0/180 | 0/67 | 40/507 | 1/507 | 1/507 |

Side by side, Table 4 "All" row (recall, then false positives):

| unit | racecheck | iGUARD | HiRace | SuperCollider | collector-only | scalar-clock | vector-clock |
|---|---|---|---|---|---|---|---|
| per program-input (paper, Indigo 1.3 per code) | 48/485, 1 TO; 0/408 | 467/486; 219/408 | 266/266; 0/180 | 51/58; 0/65 | 486/486; 40/408 | 486/486; 2/408 | 486/486; 2/408 |
| per binary (X10) | 48/378, 1 TO; 0/301 | 366/379; 168/301 | 266/266; 0/180 | 51/58; 0/65 | 379/379; 36/301 | 379/379; 1/301 | 379/379; 1/301 |
| **per kernel (X13)** | 48/380, 3 TO/ERR; 0/507 | 370/383; 168/507 | 266/266; 0/180 | 51/60; 0/67 | 383/383; 40/507 | 383/383; 1/507 | 383/383; 1/507 |

Per-run and per-binary numbers of the other rows are in sections 0b and above; the per-run, per-binary and per-kernel versions of every row are in `gate_run.md`, `gate_binary.md`, `table4_kernel.md`.
Fold-back check (step 2): folding the per-kernel verdicts of cuRace (three modes, all binaries of the table) back per binary reproduces the per-binary verdict of every (binary, mode) (`curace_checks.txt`: no difference in the final build). A first build differed on expdist vector-clock (no analysis output, an empty run list folded to CLEAN); fixed by recording the run as TIMEOUT. No pc pair is attributed to two kernels (`curace_conflicts.csv`: 0 rows). For every id the set of kernels holding RACE reports agrees with the per-binary verdict and the report count equals the CSV's `reports_dedup` (checked in `build_curace.py`; no exception).

## 2. Inventory

`eval/results/per-kernel/inventory.csv` (binary, kernel, in_cubin, mode, run_id, launches; 1 row per kernel x run), cubin lists in `cubin_kernels.csv` (entry kernels = functions with a `.nv.constant0.<name>` section in `cuobjdump -elf`; demangled with GNU `c++filt`, the collector's `kernel_name` style). Launches: kernel JSONs of the kept stores (one per launch).

| suite | binaries | kernels in cubin per binary | kernels launched per binary |
|---|---|---|---|
| Indigo3 | 200 | 2 (200) | 2 (200): `init` + the main kernel |
| Indigo 1.3 | 590 | 1 (590) | 1 (590): `test_kernel` |
| ScoR applications | 14 | 1x6, 2x2, 3x4, 20x2 | 1x6, 2x2, 3x4, 1x2 |
| cuHadron | 34 runnable (+16 sm_90, no binary) | 1x30, 2x4 | same |
| HeCBench, SC's 10 | 10 | 1 (dxtc2, gpp, overlap), 2 (fpc, mr), 3 (knn), 4 (expdist), 8 (tridiagonal), 9 (atomicCAS), 20 (crs) | same, except tridiagonal 6 |

Source mismatches (every difference to the brief's expectations):
1. ScoR `reduction` (racy and race-free build): 20 `reduceSinglePass<N, bool>` instantiations in the cubin, 1 launched (`reduceSinglePass<512u, true>`); the brief expected 1. The other 19 are never launched, not counted.
2. HeCBench `crs`: all 20 candidates are launched by the run (arguments `1 1`); the brief said one picked by its arguments.
3. HeCBench `tridiagonal`: 8 in the cubin, 6 launched. `sweep_small_systems_local_kernel` and `sweep_small_systems_global_vec4_kernel` are selected by the flags `-lmem` / `-vec4` (`main.cu`, 6a8c46c4); the default arguments (`-num_systems=30000`) launch neither. Not counted.
4. HeCBench `expdist`: 4 kernels (`distance<double>`, `distance<float>`, `reduce_cross_term<double>`, `reduce_cross_term<float>`), the brief counts 2 (source functions). Both instantiations of each are launched.
5. HeCBench `atomicCAS` 9 and `knn` 3 launched kernels: not in the brief (X11 added the two programs).
6. HeCBench: our builds' cubin and the SuperCollider native binaries list the same number of kernels for all ten programs (names not diffed).
7. Not checked: "Indigo 1.3 has 21 generator templates"; I checked that all 590 binaries have exactly one entry kernel and that it is launched in every run. The `kernel_name` of the 21 templates was not enumerated.
8. Kernels launched in some runs of a binary and not in others were not enumerated separately; `inventory.csv` has the launches per kernel and run id (`launches=0` rows exist for those).

## 3. Reports in kernels labelled race-free

All rows: `eval/results/per-kernel/fp_kernels.csv` (suite, tool, mode, binary, kernel, pc pairs or lines | class). Counts of kernels (a kernel counts once per tool/mode):

| tool / mode | Indigo3 | Indigo 1.3 | ScoR | cuHadron (in scope) | HeCBench | total |
|---|---|---|---|---|---|---|
| racecheck | 0 | 0 | 0 | 0 | 0 | **0** |
| iGUARD | 52 | 108 | 4 | 4 | 6 | **174** |
| HiRace | - | 0 | - | - | - | **0** |
| SuperCollider | - | 0 | - | 0 | 0 | **0** |
| collector-only | 0 | 32 | 8 | 0 (1 in `asyncmemcpy`) | 6 | **47** |
| scalar-clock | 0 | 0 | 1 | 0 (1 in `asyncmemcpy`) | 2 | **4** |
| vector-clock | 0 | 0 | 1 | 0 (1 in `asyncmemcpy`) | 0 | **2** |

(The cuHadron `asyncmemcpy` `write_kernel` report of cuRace is in a binary of the 34 runnable, outside the in-scope view of the table; it is included in the counts of the last column: collector-only 47 = 32 + 8 + 1 + 6, scalar-clock 4 = 1 + 1 + 2, vector-clock 2 = 1 + 1.)
Indigo3: iGUARD's 52 are main kernels of 52 race-free binaries (`init` kernels: none). Indigo 1.3: iGUARD 108 and collector-only 32 are the single `test_kernel` of the 108 / 32 race-free codes.

Non-Indigo rows (tool, mode, binary, kernel; pc pair or line | class):
- collector-only, ScoR `graph-coloring_norace`: `assignColorsKernel` (global:0x160-0x4d0, 0x500-0x6b0 | race), `detectConflictsKernel` (0x160-0x4b0, 0x4b0-0x4b0, 0x4e0-0x690 | race), `forbidColorsKernel` (0x160-0x550, 0x550-0x550, 0x580-0x730 | race); `graph-connectivity_norace`: `initKernel` (0x160-0x260, 0x290-0x440 | race), `linkKernel` (0x160-0x410, 0x410-0x410, 0x440-0x5f0 | race), `compressKernel` (0x160-0x400, 0x430-0x5e0 | race); `reduction_norace` `reduceSinglePass<512u, true>` (0x3b0-0xf60, 0x550-0xf60, 0x6e0-0xf60 | race; scalar-clock global:0xab0-0x1690 | race; vector-clock same pair | structural); `uts_norace` `parTreeSearch` (shared:0x3b50-0x3b50 and others | race).
- iGUARD, ScoR: `1dconv_norace` `convolveKernel`, `graph-coloring_norace` `forbidColorsKernel`, `reduction_norace` `reduceSinglePass<512u, true>`, `uts_norace` `parTreeSearch`.
- cuHadron: cuRace vector-clock / scalar-clock / collector-only `write_kernel(int*, int)` of `asyncmemcpy/kernel_memcpy_dto...` (name cut in my listing) (labelled race-free build; pairs global:0x890-0x9a0 and others | race); iGUARD `false_positives/global_bytewise_readwrite` `bytewise_readwrite_kernel` and `bytewise_race_kernel` (4 kernel entries over the `false_positives/global_bytewise_*` binaries).
- HeCBench (6a8c46c4 labels): collector-only `crs` `gcrs_m_1_w_4_coding_dotprod`, `gcrs_m_1_w_5_coding_dotprod` (shared:0x3e0-0x810, 0x460-0x810, ... | race); collector-only `tridiagonal` `pcr_small_systems_kernel`, `pcr_branch_free_kernel` (shared pairs | race); iGUARD `fpc` `fpc_kernel`, `fpc2_kernel`, `gpp` `solver`, `knn` `cuInsertionSort`, `mr` `mr32_sf`, `mr32_eff`.
- **expdist `reduce_cross_term`:** the CAS-loop reports are there. cuRace scalar-clock and collector-only report shared:0x7b0-0x7d0 in `reduce_cross_term<double>` and shared:0x7a0-0x7c0 in `reduce_cross_term<float>` (class race), the kernel labelled race-free (section 5). Vector-clock expdist is a TIMEOUT. In a kernel of a racy-labelled binary the race-free kernels reported are: scalar-clock 2 (`reduce_cross_term<double/float>`), collector-only 4 (those two + `pcr_small_systems_kernel`, `pcr_branch_free_kernel` of tridiagonal), iGUARD 1 (`knn` `cuInsertionSort`).

## 4. Racy kernels a tool missed in a binary it reported

`eval/results/per-kernel/missed_kernels.csv`: three kernels, no cuRace mode among them.
- iGUARD, `knn`: reports only in `cuInsertionSort` (race-free); the racy `cuComputeDistanceGlobal` (the `__shared__ int begin_A ... end_A` assignments, `main.cu:60-64`) is CLEAN. The binary scores a TP per binary, a wrong-kernel report per kernel.
- racecheck, `tridiagonal`: reports lines in `cyclic_small_systems_kernel` (`cyclic_kernels.cu:108,113,81,...`); the racy `cyclic_branch_free_kernel` has no report.
- SuperCollider, cuHadron `interkernel/global_readwrite_race` (racy): reports in `consumer_kernel` only; `producer_kernel` (labelled racy, proposed) CLEAN.
The two cases known from the CSVs (brief): iGUARD reports in all three kernels of ScoR graph-coloring and of graph-connectivity - confirmed, in the racy builds (`kernel_verdicts_baselines.csv`: `assignColorsKernel`, `detectConflictsKernel`, `forbidColorsKernel`, `initKernel`, `linkKernel`, `compressKernel` all RACE); those kernels are all labelled racy, so they are not false reports and not misses. In the race-free builds iGUARD reports `forbidColorsKernel` only (graph-coloring) and nothing in graph-connectivity. The second case, the expdist CAS-loop reports in `reduce_cross_term`, is in section 3.

## 5. Labels

`eval/results/per-kernel/labels.csv` (binary, kernel, label, rule, source lines; 1,101 kernels): 407 racy, 550 race-free, 144 unlabelled (Indigo 1.3 codes without a label). Evidence quotes in `label_sources.md`. Rules as the brief: one launched kernel = the binary's label; Indigo3 `init` race-free (templates for BFS, CC, MIS, MST read: each thread writes only its own element, the one-thread write `*wlsize`; the other algorithm templates were not read, section 7); ScoR racy iff the kernel contains a `#ifdef RACEY` block (1dconv `convolveKernel` racy, `initKernel` race-free; graph-coloring, graph-connectivity all three racy; matMult, rule110, parTreeSearch, reduceSinglePass racy); HeCBench on 6a8c46c4: atomicCAS all 9 racy (plain `*address` read racing with `atomicCAS` in every overload), dxtc2 `compress` racy, knn `cuComputeDistanceGlobal` racy / `cuInsertionSort`, `cuParallelSqrt` race-free, expdist `distance<*>` racy (`kernel.h:28`) / `reduce_cross_term<*>` race-free (`sum` set by thread 0, `__syncthreads()`, per-thread private accumulation over `cross_term[tx + k*256]`, atomicAdd then `__syncthreads()` before thread 0 reads; atomicAdd on a double in shared memory is an atomic CAS loop, not a plain conflicting access), the race-free applications every kernel race-free.
cuHadron `interkernel/*` (two kernels, outside the in-scope view): **proposal** - racy build both kernels racy (the race is between the two kernels' accesses), fixed build both race-free; used only in SuperCollider's all-34 cell. Not a gate (the source is unambiguous).
**Tridiagonal (gate), decision as taken:** Jeffery, 2026-11-09: "I would rather not review the labels for now and use your proposed labels." The labels are the agent's source-based proposal, adopted by Jeffery without review: `cyclic_small_systems_kernel` and `cyclic_branch_free_kernel` racy (the last forward-elimination iteration writes `b/c/a/d[addr]` at `cyclic_kernels.cu:81-98` / `207-210`; threads `thid < 2` read them at `:104-116` / `:216-228` with no `__syncthreads()` in between); `pcr_small_systems_kernel`, `pcr_branch_free_kernel`, `sweep_small_systems_local_kernel`, `sweep_small_systems_global_kernel`, `sweep_small_systems_global_vec4_kernel`, `transpose` race-free. The two follow-up checks: `sweep_small_systems_global_vec4_kernel` read in full (`sweep_kernels.cu:269-357`): no shared memory, thread `j` owns systems 4j..4j+3 with disjoint float4 ranges - race-free confirmed; launched kernels under the default arguments: pcr (both), cyclic (both), `sweep_small_systems_global_kernel`, `transpose` = 6; `local` and `vec4` are not launched. Neither check contradicts a label. Under these labels cuRace's collector-only mode reports in `pcr_small_systems_kernel` and `pcr_branch_free_kernel` (section 3), a false report per kernel; the clock modes report in the two cyclic kernels only (recall 2/2 on the tridiagonal racy kernels).

## 6. SuperCollider

- Rows needing lines: PI codes (one kernel each, the report is in it; no log needed), cuHadron (lines present in `baselines-supercollider.csv`; its binaries' kernels mapped through our `nvdisasm` line map of the same program, SAME program for 17 of the 27), HeCBench: 15 RACE rows without lines in `baselines-supercollider.csv` (atomicCAS, dxtc2, expdist, 5 attempts each) - run_supercollider.py's regex expects "In function", the artifact prints "Inlined function ... at file:line" (defect recorded in `eval/FINAL_SWEEP_B.md`). knn (`main.cu:60-64`) and tridiagonal (`cyclic_kernels.cu:108,225,226`) have lines.
- **Surviving logs:** the X8 logs `/mnt/local/fzheng4/sc_logs_x8` still exist on c40 (149 directories), c41 (149), c42 (118), c43 (88), c76 (31) and c77 (60) (jobs 334126-334131, `eval/x_logs/x13/x8logs-*.log`); not re-parsed, because all X8 rows are Indigo codes with a single kernel.
- **Re-run (step 3b):** job 331594 (c2, rtx4060ti16g, `--exclusive`), artifact protocol, 5 attempts per program, log root `/mnt/beegfs/fzheng4/x13_sc_logs`: atomicCAS RACE (9 races), expdist RACE (24 races), dxtc2 ERROR (`loadPPM()` fails: its data files `../dxtc2-sycl/data/*` are not on disk). 15 rows, well under the 100-row limit. Parsed by `sc_parse.py` (both headers): atomicCAS reports `atomic_{min,max,add}` overloads `Pyy`, `Pxx`, `Pdd` at `kernels.h:19,5,89,59,45,103,73,33,119` (inlined functions), mapped by function name to `atomic{Min,Max,Add}Derived<unsigned long long | long long | double>` (the overload each kernel calls): all 9 kernels; expdist reports `fill_shared_mem_tiled_1D<4,8,double|float>` at `kernel.h:28` (60 report rows over 5 attempts), mapped to `distance<double>` and `distance<float>` (the only callers of `distance_tiled<T>`, 6a8c46c4 `kernel.h:101-113`); dxtc2 is attributed to its only kernel `compress` (inferred from the single-kernel binary, not from a log line).
- **6a8c46c4 mapping:** `nvdisasm --print-line-info` of the artifact's native binaries (`bin/hecbench/native/<app>`), file:line -> kernel: tridiagonal `cyclic_kernels.cu:108` -> `cyclic_small_systems_kernel`, `:225,226` -> `cyclic_branch_free_kernel` (unique); knn `main.cu:60-64` -> `cuComputeDistanceGlobal` (unique). racecheck X11 rows on the native binaries use the same maps (dxtc2 `main.cu` lines -> `compress`; tridiagonal -> `cyclic_small_systems_kernel`); racecheck expdist has no file:line in the stored row (`report_lines` empty): its notes name `distance_tiled<double>` and `<float>`, mapped to `distance<double>` and `distance<float>`.
- **Rows whose kernel stayed ambiguous:** none (`baselines_notes.csv`: no "ambiguous" or "unmapped" entry). racecheck, SuperCollider and iGUARD "fold-back" notes (16 each) are the 16 cuHadron sm_90 binaries (no kernels).
- iGUARD: rows cut at 2,000 characters: none in `baselines-iguard.csv`; in `cap-84600/baselines-iguard.csv` three (two P7, outside Table 4, and `P9-atomicCAS-cuda`); X11's atomicCAS row (new, 18 reports) is cut at 2,000 characters in `iguard.csv`, its full log `/mnt/beegfs/fzheng4/x11_work/iguard_logs/x11b-iguard-atomicCAS-r1/X11-atomicCAS/iguard_rep1.txt` (9 MB) re-read: `mr` is not cut (512 characters; the full log names `mr32_sf` and `mr32_eff`).
- HiRace: runs only on Indigo 1.3 codes; all 590 binaries have one entry kernel (checked on our build; the twin's cubin was not inspected).

## 7. Unverified, missing, and the harness edit

- **parallel.py conflict (the one harness-runner edit Jeffery allowed):** merge `d881d072` of `origin/eval/sc-native-hecbench` (`5ee0e3d0`). One conflict hunk in `cmd_analyze`: HEAD had the C4 second pass (`both_w`, `CUVEIN_BARRIER_ORDER=0`, timing csv) calling `analyze_one(idir, w, confirm_dir, analysis_timeout, analysis_mem)`; the X11 side had `analyze_one(..., analysis_mem, analysis_workers)` (X7 parallel verdict code). Combined: both `analyze_one` calls (first and second pass) pass `getattr(a, "analysis_workers", None)`; no line of either side's logic dropped. Harness tests after the merge: `python/test_sync_dominance.py test_barrier_soundness test_coherent_ldst test_atomic_memory_model test_barrier_exit test_hb_substitutions test_cp_async test_co_offline` on a compute node (job 330053): **69 passed, 155 skipped, 0 failed** (CLAUDE.md expects 305 passed, 2 skipped on a GPU node with the installed runtime; the skips are the GPU halves and the runtime-dependent tests, so this run does not reproduce that expectation - unverified). `test_co_chain.py` and `test_co_rules.py` do not exist in this branch (co-chain-b code not merged).
- Tests added: `eval/baselines/per_kernel/test_fold_kernel.py` (6: several launches with one reporting; a kernel with no finished launch -> TO, an errored one -> ERR; a never-launched kernel not counted; a report in a race-free kernel of a racy binary -> FP + TP; race beats a missing launch; folding back equals X10's `fold_verdict` over all verdict triples) and X10's `test_make_tables_fold.py` (11): **17 passed** (job 332784).
- The first-pass shards of `curace_kernels.py` that hit time limits (tasks 5, 7, 22 of array 330060; X11 jobs 330111, 330256; ck11b tasks 3, 8, 17, 50, 83, 116) were rerun (ck2, ck3, ck11b, ck11t, ck11t_ssh) and their partial files ignored.
- **atomicCAS scalar-clock** (X11 jobs 329004/329005 pending when `coverage.tex` was written): treated as TO as `coverage.tex` does, no kernel JSON; all 9 atomicCAS kernels TO in scalar-clock and vector-clock.
- **expdist vector-clock:** recorded, verdict step out of memory (108 GB), TIMEOUT for all 4 kernels; per-kernel verdicts of the recorded 4 kernels JSONs unavailable.
- Collector-only per-kernel verdicts: re-run of the verdict layer per kernel JSON with the S1 setting of co-chain-b (`--chain-closure --co-async --co-r3 strict`, code `wt-c6b` f31a5067); X11's HeCBench collector-only: chain closure only (code `wt-x11-cochain` be325e03), as X11's stage A. The per-binary verdict of every (id, mode) was reproduced from the kernel-level reports (check above); the clock modes use this branch's merged code (X1b stores, cuVein 98371ee1 verdict code).
- Baselines' "launched" sets: a baseline's kernel universe is cuRace's launched set of the same binary (the baselines do not record launches); a TIMEOUT/ERR baseline row marks every kernel TO/ERR. SuperCollider and iGUARD reps: lines/names taken from the stored row (first non-empty rep) except the re-run.
- Not verified: the Indigo3 `init` kernel in every one of the 100 templates (four algorithm families read); the `test_kernel` of the 21 Indigo 1.3 templates; iGUARD names are matched against the cubin list by normalised string, a handful of templated names were checked by count only.
- Never read: cuHadron sources beyond the binaries' kernel names; cuHadron per-kernel labels for the 20 in-scope binaries are their binary labels (one kernel each).
- Jobs: gate 330057; stores scan 330056; cuRace per kernel 330060, 330214, 330247, 331600, 330111/330256 (timed out), 331622, 332672 (+ssh packing, 332938); cubin 330257; line maps 330097; SuperCollider re-run 331594; builds 332671, 334118, 334121, 334132; tests 330053, 332784.
