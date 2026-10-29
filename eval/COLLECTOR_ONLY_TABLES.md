# Collector-only tables (C3)

Branch `eval/collector-only-tables`, cut from `origin/eval/final-tables` (d484e42). Nothing recorded, no GPU, no detector or rule change, cuRacePaper not edited, C1/C2 branches read only (not merged). Every number below is computed from kernel JSONs (item 9, 10) or results CSVs (all other items) by the scripts in `eval/baselines/setup/co_tables/`; the CSVs are in `eval/results/collector-only-tables/`.

Third mode = collector-only (CO): no HbClock, verdicts from the static certificates alone; a conflicting reuse pair no certificate orders is Race or Strong-conflict, never Latent. Sources: X1b (`final-2026-11`, vector-clock and scalar-clock), C1 (`eval/collector-only` 0c28634, `final-2026-11-co`), C2 (`eval/collector-only-realworld` 016d93f, real-world recall and candidates). `make_tables.py` gained only the third mode (`--collector-only`); with the flag off its output equals X1b's, and with it on, the vector-clock/scalar-clock columns are unchanged (`co_strip_compare.py`; the 13 remaining diff hunks are single-column separator artifacts of the comparison).

## Which paper cell each table fills

| paper cell | table below |
|---|---|
| Table 6.1 (tab:eval-accuracy) and the aggregate row | Table 6.1 section |
| tab:eval-accuracy-union, tab:eval-countings | union/countings section |
| tab:eval-litmus | litmus section |
| tab:eval-recall, candidate counts | Item 4 |
| fig_slowdown (fig:eval-slowdown) | fig_slowdown section |
| tab:eval-memory | memory section |
| cost table (FINAL_TABLES.md section (a)) | Item 6 |
| app:eval-noverdict | no-verdict section |
| program-level comparison (not in the paper) | Item 8 |
| tab:eval-shapes (X5's 1,021 pairs) | Item 9 |
| sec:onerun "Is one run enough?" | Item 10 |

## Findings

1. Every vector-clock and scalar-clock cell of Table 6.1, the union table, the countings table and the litmus table recomputes to the paper's value (check section after the tables).
2. Mismatches with the paper (reported, not edited): the slowdown figure's HeCBench "other 14" and "All" cells (paper 1349.0/249.7 and 7.5/7.1; recomputed values are in the fig_slowdown table); the memory table's HeCBench scalar-clock median (paper 14.0 GB, recomputed 5.39); the real-world fixed-build clean count (paper 21, 20 recomputed from T21b's `main` flavor); candidate count 16 against the paper's 18.
3. Collector-only on race-free programs: 224 false reports in Indigo 1.3 (paper-style FP 224/1,260), against 0 for vector- and scalar-clock; 229 race-free programs are Race in CO and Clean in SC (listed in `item8_race_free_co_race_sc_clean.csv`). Pair-level cause (Item 9): 1,016 of the 1,138 CO-only pairs are the barrier-ordered pairs of X5's shapes table (S1, a subset of X5's 1,021), 96 have no edge in the scalar-clock recording (schedule-dependent edge) and 26 are ordered in SC by an R3 certificate chain that CO lacks. Pairs fitting none of the reasons: 0.
4. CO is Clean where SC is Race for 28 programs (appendix list in Item 8), 26 of them in PI, all unlabelled or racy-labelled; no race-free program is Clean-in-CO-only.
5. Real-world recall: CO detects 21 of 25 scored data-race components (SC/VC 25 of 26), 5 of 5 strong-conflict components as in the paper.
6. Footnotes: amrex-1 (buggy and fixed) is pending (CO re-analysis running) and is left out of every CO count. C2's aggregate `COLLECTOR_ONLY_REALWORLD.md/.csv` still shows hecbench-hungarian-1, raft-1 and colmap-new-1 as NOT-SCORED/ERROR while its per-set recall.csv files hold the re-analysis rows; Item 4 uses the per-set files. lock_rtraw is counted as recorded (Race, a false report) in X1b [^rtraw]. lightgbm-new-1/2 are unscored. 18 programs have no scalar-clock recording and 3 analyses hit their time cap in Item 9; 17 CO ERROR rows are in C1's report (sm_90 programs and `P9-atomicCAS-cuda`).

[^rtraw]: `race_interblock_none-lock_rtraw` is a race-free-labelled false report in X1b; counted as recorded.


## Table 6.1 (tab:eval-accuracy): accuracy per suite, data races alone, third column added

Cells: recall TP/(TP+FN) · false-positive rate FP/(FP+TN); TO = timed out, ERR = errored. Race-alone verdict = `race_alone_verdict` of `make_tables.py`. Collector-only: a conflicting reuse pair no certificate orders is Race (class `race`) or SC; no Latent.

| suite | cuVein vector-clock | cuVein scalar-clock | cuVein collector-only |
|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 |
| Indigo 1.3, SC's 99 | 43/45 · 0/44 | 43/45 · 0/44 | 43/45 · 4/44 |
| ECL | — · 16/60 | — · 16/60 | — · 16/60 |
| ScoR applications | 14/14 · 2/14 | 14/14 · 2/14 | 14/14 · 6/14 |
| ScoR litmus + canary | 4/19 · 1/14 | 3/19 · 0/14 | 2/19 · 0/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/6; 1 ERR |
| **All pre-registered** | 1,934/2,082 · 18/1,548; 16 ERR | 1,934/2,082 · 18/1,548; 16 ERR | 1,956/2,082 · 246/1,548; 16 ERR |

## tab:eval-accuracy-union and tab:eval-countings: the three countings, third mode added

races = Race alone; strong = a program with an unordered strong conflict reported (class `sc`); union = Race or strong. Cells TP/(TP+FN) · FP/(FP+TN). The paper's vector-clock and scalar-clock cells are recomputed and compared (last section).

| suite | VC races | VC strong | VC union | SC races | SC strong | SC union | CO races | CO strong | CO union |
|---|---|---|---|---|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 0/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 |
| ECL | — · 16/60 | — · 36/60 | — · 44/60 | — · 16/60 | — · 32/60 | — · 40/60 | — · 16/60 | — · 36/60 | — · 44/60 |
| ScoR applications | 14/14 · 2/14 | 8/14 · 7/14 | 14/14 · 7/14 | 14/14 · 2/14 | 8/14 · 4/14 | 14/14 · 4/14 | 14/14 · 6/14 | 6/14 · 4/14 | 14/14 · 8/14 |
| ScoR litmus + canary | 4/19 · 1/14 | 17/19 · 4/14 | 19/19 · 5/14 | 3/19 · 0/14 | 17/19 · 0/14 | 18/19 · 0/14 | 2/19 · 0/14 | 16/19 · 0/14 | 17/19 · 0/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 0/2 · 0/6; 2 TO | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 0/3 · 0/6; 1 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/6; 1 ERR | 0/3 · 0/6; 1 ERR | 3/3 · 1/6; 1 ERR |
| **All pre-registered** | 1,934/2,082 · 18/1,548; 16 ERR | 8/2,082 · 115/1,548; 16 ERR | 1,934/2,082 · 123/1,548; 16 ERR | 1,934/2,082 · 18/1,548; 16 ERR | 8/2,082 · 108/1,548; 16 ERR | 1,934/2,082 · 116/1,548; 16 ERR | 1,956/2,082 · 246/1,548; 16 ERR | 6/2,082 · 112/1,548; 16 ERR | 1,956/2,082 · 348/1,548; 16 ERR |

## tab:eval-litmus: the 33 ScoR litmus kernels, third mode added

Race = a data race is reported; Strong = only an unordered strong conflict is reported; — = nothing reported. `rtraw` counted as recorded (Race, a false report, footnote [^rtraw]).

| kernel | ScoR label | VC | SC | CO |
|---|---|---|---|---|
| `canary_pc_level_false_negative` | racy | Race | — | — |
| `norace_interblock_atom` | race-free | — | — | — |
| `norace_interblock_fence_raw` | race-free | Strong | — | — |
| `norace_interblock_lock_waw` | race-free | — | — | — |
| `norace_interwarp-block_fence-atom_hrd-indirect` | race-free | Race | — | — |
| `norace_interwarp-block_fence_hrf-indirect` | race-free | Strong | — | — |
| `norace_interwarp_blkatom` | race-free | — | — | — |
| `norace_interwarp_blkfence_raw` | race-free | Strong | — | — |
| `norace_interwarp_blklock_waw` | race-free | — | — | — |
| `norace_interwarp_dev-blkatom` | race-free | — | — | — |
| `norace_interwarp_dev-blklock_waw` | race-free | — | — | — |
| `norace_interwarp_fence_raw` | race-free | Strong | — | — |
| `norace_intrawarp_none-blkatom` | race-free | — | — | — |
| `norace_intrawarp_none-blklock-no-tf_waw` | race-free | — | — | — |
| `norace_intrawarp_none-blklock_waw` | race-free | — | — | — |
| `race_interblock_blkatom` | racy | Race | Race | Race |
| `race_interblock_blkfence_raw` | racy | Strong | Strong | Strong |
| `race_interblock_blklock_waw` | racy | Race | Race | Race |
| `race_interblock_fence_rtraw` | racy | Strong | Strong | Strong |
| `race_interblock_lock-blkfence_waw` | racy | Strong | Strong | Strong |
| `race_interblock_lock-no-stf_waw` | racy | Strong | Strong | Strong |
| `race_interblock_lock-no-tf_waw` | racy | Strong | Strong | Strong |
| `race_interblock_none-atom_waw` | racy | Strong | Strong | Strong |
| `race_interblock_none-lock_rtraw` | racy | Race | Race | — |
| `race_interblock_none-lock_waw` | racy | Strong | Strong | Strong |
| `race_interwarp_blklock-no-stf_waw` | racy | Strong | Strong | Strong |
| `race_interwarp_blklock-no-tf_waw` | racy | Strong | Strong | Strong |
| `race_interwarp_dev-blklock-no-stf_waw` | racy | Strong | Strong | Strong |
| `race_interwarp_dev-blklock-no-tf_waw` | racy | Strong | Strong | Strong |
| `race_interwarp_none-atom_waw` | racy | Strong | Strong | Strong |
| `race_interwarp_none-blkatom_waw` | racy | Strong | Strong | Strong |
| `race_interwarp_none-blklock_waw` | racy | Strong | Strong | Strong |
| `race_interwarp_none-lock_waw` | racy | Strong | Strong | Strong |

33 P5 programs; 33 kernels parsed from the paper's table; 0 vector/scalar cells differ from the paper.

## fig_slowdown: per-suite geometric-mean slowdown, third mode added

| suite | VC geomean (n) | SC geomean (n) | CO geomean (n) |
|---|---|---|---|
| Indigo3 | 10.4 (400) | 8.7 (400) | 6.5 (400) |
| Indigo 1.3 | 6.9 (4130) | 6.8 (4130) | 5.5 (4130) |
| ECL | 10.1 (60) | 8.8 (60) | 6.0 (60) |
| ScoR apps | 28.8 (28) | 9.4 (28) | 6.8 (28) |
| ScoR litmus | 8.8 (33) | 7.4 (33) | 5.6 (33) |
| cuHadron | 13.0 (34) | 10.8 (34) | 7.1 (34) |
| HeCBench other 14 | 1249.0 (11) | 230.0 (13) | 95.0 (14) |
| HeCBench SC 10 | 1694.4 (8) | 512.6 (9) | 139.4 (9) |
| All | 7.3 (4685) | 7.0 (4685) | 5.6 (4685) |

Paper figure (VC / SC): Indigo3 10.4/8.7, Indigo 1.3 6.9/6.8, ECL 10.1/8.8, ScoR apps 28.8/9.4, litmus 8.8/7.4, cuHadron 13.0/10.8, HeCBench other 14 1349.0/249.7, SC 10 1694.4/512.6, All 7.5/7.1.

C1's own report (`eval/COLLECTOR_ONLY.md`, native wall of the same job): P1 6.38, PI 5.03, P3 5.95, P4 6.62, P5 5.55, P6 6.67, P7 93.52, P9 94.19. Here the denominator is the smaller of the X1b id-level native wall and C1's own (the X1b convention of `_ratios`), so the vector- and scalar-clock figures are unchanged by the third mode.

## tab:eval-memory: peak memory (GB), third mode added

| | VC | SC | CO |
|---|---|---|---|
| Labelled suites, median | 0.85 | 0.86 | 0.85 |
| HeCBench applications that finished, median | 2.85 | 5.39 | 1.00 |
| `P9-atomicCAS-cuda` | TIMEOUT 100.0 | TIMEOUT 1.1 | ERROR 0.9 |
| `P7-stencil1d-cuda` | TIMEOUT 98.5 | TIMEOUT 168.1 | CLEAN 4.2 |
| `P7-particlefilter-cuda` | TIMEOUT 125.4 | RACE 189.7 | RACE 1.2 |

(peak = max over a program's reps of the summed-VmRSS poll; for unfinished runs the last peak seen.) Paper: labelled 0.85 / 0.86; HeCBench scalar-clock median 14.0 GB.

## app:eval-noverdict: programs without a verdict, per mode

| program | VC | SC | CO |
|---|---|---|---|
| `P7-haversine-cuda` | TIMEOUT (cap) | CLEAN | CLEAN |
| `P7-particlefilter-cuda` | TIMEOUT (cap) | RACE | RACE |
| `P7-stencil1d-cuda` | TIMEOUT (cap) | TIMEOUT (cap) | CLEAN |
| `P9-atomicCAS-cuda` | TIMEOUT (cap) | TIMEOUT (cap) | ERROR (analysis-timeout) |
| `P9-expdist-cuda` | TIMEOUT (cap) | RACE | RACE |
| 16 `P6-bulkcpy-*` / `P6-dsmem-*` | ERROR (needs sm_90) | ERROR | ERROR |

vector-clock: CLEAN 2034, RACE 2670, TIMEOUT 5 of 4709 programs

scalar-clock: CLEAN 2037, RACE 2670, TIMEOUT 2 of 4709 programs

collector-only: CLEAN 1812, ERROR 1, RACE 2896 of 4709 programs

## Item 8: program-level verdicts, scalar-clock (X1b) against collector-only (C1), separate recordings

| suite | programs | same verdict | SC Race → CO Clean | SC Clean → CO Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 3856 | 26 | 248 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 24 | 0 | 4 | 0 |
| P5 | 33 | 32 | 1 | 0 | 0 |
| P6 | 34 | 33 | 1 | 0 | 0 |
| P7 | 14 | 12 | 0 | 1 | 1 |
| P9 | 10 | 8 | 0 | 1 | 1 |
| **all** | 4709 | 4425 | 28 | 254 | 2 |

Race-free (labelled) programs that are Race in collector-only and Clean in scalar-clock: **229**; per suite: P4 4, P9 1, PI 224. All of them with their pairs: `item8_race_free_co_race_sc_clean.csv`.

Not race-free-labelled, SC Clean → CO Race: 25 (labels: {'RACE': 24, 'unlabelled': 1})

Other differences (a side TIMEOUT/ERROR/none): 2
  - `P9-atomicCAS-cuda` SC TIMEOUT / CO ERROR
  - `P7-stencil1d-cuda` SC TIMEOUT / CO CLEAN

Scalar-clock Race, collector-only Clean: 28
  - `PI-pull_node_neighbors_boundsBug_cond-DAG_200n_400e` label unlabelled: SC 10 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond-power_law_200n_1000e` label unlabelled: SC 10 reports
  - `PI-pull_node_neighbors_boundsBug_cond_break-counterDAG_5n_5e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_cond_break-power_law_200n_1000e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond-DAG_100n_200e` label unlabelled: SC 10 reports
  - `PI-pull_node_neighbors_boundsBug_cond_break-DAG_100n_100e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond-DAG_200n_400e` label unlabelled: SC 10 reports
  - `PI-push_node_neighbors_boundsBug_reverse_cond_atomicBug_break-counterDAG_5n_5e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond-counterDAG_200n_1000e` label unlabelled: SC 10 reports
  - `PI-pull_node_neighbors_boundsBug_cond-DAG_100n_200e` label unlabelled: SC 10 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond-counterDAG_5n_5e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond-DAG_100n_100e` label unlabelled: SC 8 reports
  - `PI-pull_node_neighbors_boundsBug_cond-counterDAG_200n_1000e` label unlabelled: SC 10 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond_break-DAG_100n_200e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_cond-counterDAG_5n_5e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond_break-DAG_200n_400e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_cond-power_law_200n_1000e` label unlabelled: SC 10 reports
  - `PI-pull_node_neighbors_boundsBug_cond-DAG_100n_100e` label unlabelled: SC 8 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond_break-counterDAG_200n_1000e` label unlabelled: SC 2 reports
  - `PI-conditional_edge_neighbors_warp_persistent_guardBug-counterDAG_5n_5e` label RACE: SC 1 reports
  - `PI-pull_node_neighbors_boundsBug_cond_break-DAG_100n_200e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond_break-counterDAG_5n_5e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_cond_break-DAG_200n_400e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond_break-power_law_200n_1000e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_reverse_cond_break-DAG_100n_100e` label unlabelled: SC 2 reports
  - `PI-pull_node_neighbors_boundsBug_cond_break-counterDAG_200n_1000e` label unlabelled: SC 2 reports
  - `P6-memcpy-shared_readwrite_race-racy` label RACE: SC 1 reports
  - `P5-race_interblock_none-lock_rtraw` label RACE: SC 1 reports

## Check against the paper (vector-clock and scalar-clock cells)

Every vector-clock and scalar-clock cell of Table 6.1, the union table, the three-countings table and the litmus table recomputes to the paper's value.



## Item 4: recall table (T21b, 28 targets) and candidate counts (T21c), third mode added

Sources: C2's `eval/results/realworld_co/recall.csv` and `realworld_co_t21c/recall.csv` at origin/eval/collector-only-realworld 016d93f; T21b `eval/results/realworld/recall.csv` (study/realworld-recall) for vector-clock and scalar-clock; T21c `eval/results/realworld_t21c/recall.csv` for the candidates. (C2's aggregate `eval/COLLECTOR_ONLY_REALWORLD.md/.csv` still shows hecbench-hungarian-1, raft-1 and colmap-new-1 as NOT-SCORED/ERROR; the per-set recall.csv files hold their re-analysis rows, so the counts below use those files. Reported to C2 / the coordinator as a finding.)

T21b recall.csv (mode, flavor) rows: {('vector-clock', 'main'): 58, ('scalar-clock', 'main'): 58, ('vector-clock', 'certain'): 8}

**Buggy builds, per component** (outcome counts; CO excludes the pending amrex-1 row):

| components | outcome | vector-clock | scalar-clock | collector-only |
|---|---|---|---|---|
| data-race components (oracle expects DR) | DETECTED | 25 | 25 | 21 |
| data-race components (oracle expects DR) | MISSED | 1 | 1 | 4 |
| data-race components (oracle expects DR) | PENDING (left out) | 0 | 0 | 1 |
| data-race components (oracle expects DR) | **total** | 26 | 26 | 26 |
| strong-conflict components (oracle expects SC) | DETECTED | 2 | 2 | 2 |
| strong-conflict components (oracle expects SC) | DETECTED-AS-DR | 3 | 3 | 3 |
| strong-conflict components (oracle expects SC) | **total** | 5 | 5 | 5 |

**Fixed builds** (one per target):

| outcome | vector-clock | scalar-clock | collector-only |
|---|---|---|---|
| CLEAN-FOR-PAIR | 20 | 20 | 17 |
| PENDING (left out) | 0 | 0 | 1 |
| RESIDUAL-AS-EXPECTED | 6 | 6 | 7 |
| STILL-REPORTED | 1 | 1 | 3 |
| **total** | 27 | 27 | 28 |

Paper (both modes): 25 of 26 data-race components, 5 of 5 strong-conflict components; fixed builds 21 clean for the pair, 6 residual, 1 still reported.

**Per target and component** (outcome per mode; pending = analysis re-run running):

| target | variant | comp | vector-clock | scalar-clock | collector-only |
|---|---|---|---|---|---|
| amrex-1 | buggy | DR | MISSED | MISSED | pending |
| amrex-1 | fixed | - | — | — | pending |
| bitsandbytes-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| bitsandbytes-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| cccl-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| cccl-1 | fixed | - | STILL-REPORTED | STILL-REPORTED | STILL-REPORTED |
| cccl-2 | buggy | DR | DETECTED | DETECTED | DETECTED |
| cccl-2 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| cccl-3 | buggy | DR | DETECTED | DETECTED | MISSED |
| cccl-3 | buggy | SC | DETECTED | DETECTED | DETECTED |
| cccl-3 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| cccl-4 | buggy | DR | DETECTED | DETECTED | DETECTED |
| cccl-4 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| cmssw-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| cmssw-1 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| ginkgo-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| ginkgo-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| ginkgo-5 | buggy | DR | DETECTED | DETECTED | MISSED |
| ginkgo-5 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| hecbench-dxtc2-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| hecbench-dxtc2-1 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| hecbench-hungarian-1 | buggy | SC | DETECTED-AS-DR | DETECTED-AS-DR | DETECTED-AS-DR |
| hecbench-hungarian-1 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| hecbench-morphology-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| hecbench-morphology-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| hecbench-surfel-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| hecbench-surfel-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| kokkos-5 | buggy | DR | DETECTED | DETECTED | MISSED |
| kokkos-5 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | RESIDUAL-AS-EXPECTED |
| kokkos-6 | buggy | DR | DETECTED | DETECTED | DETECTED |
| kokkos-6 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| lit-arrayfire-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| lit-arrayfire-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| lit-exllamav3-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| lit-exllamav3-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| lit-fbgemm-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| lit-fbgemm-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| lit-shoc-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| lit-shoc-1 | buggy | SC | DETECTED-AS-DR | DETECTED-AS-DR | DETECTED-AS-DR |
| lit-shoc-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| llamacpp-2 | buggy | DR | DETECTED | DETECTED | DETECTED |
| llamacpp-2 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | STILL-REPORTED |
| llamacpp-4 | buggy | DR | DETECTED | DETECTED | DETECTED |
| llamacpp-4 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| llamacpp-5 | buggy | DR | DETECTED | DETECTED | DETECTED |
| llamacpp-5 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| opencv-2 | buggy | SC | DETECTED-AS-DR | DETECTED-AS-DR | DETECTED-AS-DR |
| opencv-2 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| pytorch-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| pytorch-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | STILL-REPORTED |
| pytorch-3 | buggy | DR | DETECTED | DETECTED | DETECTED |
| pytorch-3 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| pytorch-4 | buggy | DR | DETECTED | DETECTED | DETECTED |
| pytorch-4 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |
| pytorch_cluster-1 | buggy | DR | DETECTED | DETECTED | DETECTED |
| pytorch_cluster-1 | fixed | - | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR | CLEAN-FOR-PAIR |
| raft-1 | buggy | DR | DETECTED | DETECTED | MISSED |
| raft-1 | buggy | SC | DETECTED | DETECTED | DETECTED |
| raft-1 | fixed | - | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED | RESIDUAL-AS-EXPECTED |

## Candidate set (T21c): scored components

| id | component | expected | scalar-clock | collector-only | CO n_race / n_sc |
|---|---|---|---|---|---|
| autogptq-new-1-buggy | DR | DR | DETECTED | DETECTED | 128/0 |
| colmap-new-1-buggy | DR | DR | DETECTED | DETECTED | 272/0 |
| cuml-tsne-new-1-buggy | DR | DR | DETECTED | DETECTED | 56/24 |
| droidslam-new-1-buggy | SC | SC | DETECTED-AS-DR | DETECTED-AS-DR | 21/0 |
| llamacpp-open-1-buggy | DR | DR | DETECTED | DETECTED | 17/0 |
| llamacpp-open-2-buggy | DR | DR | MISSED | not run | / |
| llmc-new-1-buggy | DR | DR | DETECTED | DETECTED | 8/0 |
| llmc-new-2-buggy | DR | DR | DETECTED | DETECTED | 1/0 |
| llmc-new-3-buggy | DR | DR | DETECTED (family) | DETECTED (family) | 2/0 |
| llmc-new-3-buggy | DR | DR | DETECTED | DETECTED | 9/0 |
| mmcv-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | 2/0 |
| opencv_contrib-new-1-buggy | DR | DR+SC | DETECTED | DETECTED | 64/0 |
| opencv_contrib-new-1-buggy | SC | DR+SC | DETECTED-AS-DR | DETECTED-AS-DR | 64/0 |
| openpcdet-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | 3/0 |
| pcl-new-1-buggy | DR | DR+SC | DETECTED | MISSED | 136/0 |
| pcl-new-1-buggy | SC | DR+SC | DETECTED-AS-DR | DETECTED-AS-DR | 136/0 |
| pointnet2pt-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | 1/0 |
| pytorch_cluster-new-1-buggy | DR | DR | DETECTED | DETECTED | 14/0 |
| sglang-open-1-buggy | DR | DR | DETECTED | DETECTED | 1/0 |

Collector-only candidate outcomes (components run): {'DETECTED': 13, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1, 'MISSED': 1}. Scalar-clock outcomes over the same components: {'DETECTED': 14, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1}.
lightgbm-new-1/2 are unscored (Jeffery's decision); llamacpp-open-2 was not run in C2.



## Item 6: cost table (section (a) of FINAL_TABLES.md), collector-only from C1's rows

Wall in seconds, µs per record in parentheses; native wall = median of the program's native runs in the same job. Records = `events=` (collector-only: records drained, `accelprof -v`; scalar/vector-clock: `hb_events_count`). Different hosts per column (node in `cost_co_rows.csv`).

| program | records (C1) | native (s) C1 / X1b | **collector-only (C1)** | scalar-clock sharded N=16 (X1b) | vector-clock (X1b) | C1 node |
|---|---|---|---|---|---|---|
| P7-heartwall-cuda | 8,071,484,636 | 0.769 / 0.872 | **2,347.6 (0.2908)** | 5,728.7 (0.7097) | 61,435.9 (7.611) | c61 |
| P9-knn-cuda | 11,144,912,500 | 13.092 / 12.001 | **3,739.8 (0.3356)** | 9,680.4 (0.8686) | 58,674.2 (5.265) | c76 |
| P7-nbody-cuda | 320,355,120 | 14.570 / 14.144 | **59.9 (0.1868)** | 391.0 (1.221) | 11,252.4 (35.12) | c74 |
| P7-bfs-cuda | 7,436,165 | 1.069 / 1.371 | **4.8 (0.649)** | 12.1 (1.625) | 11,500.6 (1,547) | c63 |
| P1-BFS_CUDA_E_Topo_Determ_..._slower_atomic-100n | 1,023 | 0.218 / 0.271 | **1.1 (1,045)** | 2.6 (2,582) | 1.6 (1,547) | c62 |
| P6-interkernel-global_readwrite_race-fixed | 1,000,004 | 0.771 / 0.770 | **5.3 (5.342)** | 5.5 (5.478) | 6.9 (6.933) | c74 |

Fits (OLS of tool wall on records), wall = intercept + slope × records:

| scope | column | runtime | n | intercept (s) | slope (µs/record) | R² |
|---|---|---|---|---|---|---|
| program set above | collector-only | f551ca0 (C1) | 6 | -24.61 | 0.3226 | 0.994 |
| program set above | scalar-clock sharded N=16 | f551ca0 (X1b) | 6 | -23.26 | 0.8166 | 0.987 |
| program set above | vector-clock | f551ca0 (X1b) | 6 | 5,993 | 5.47 | 0.924 |
| all complete (id,mode) rows | collector-only | f551ca0 (C1) | 4708 | 0.1028 | 0.4027 | 0.964 |
| suite P1 | collector-only | f551ca0 (C1) | 400 | 1.473 | 0.04359 | 0.000707 |
| suite P3 | collector-only | f551ca0 (C1) | 60 | 1.373 | -0.6025 | 0.00468 |
| suite P4 | collector-only | f551ca0 (C1) | 28 | 1.513 | 0.3555 | 0.591 |
| suite P5 | collector-only | f551ca0 (C1) | 33 | 1.333 | -2,853 | 0.000958 |
| suite P6 | collector-only | f551ca0 (C1) | 34 | 6.242 | 0.8157 | 0.938 |
| suite P7 | collector-only | f551ca0 (C1) | 14 | -577.9 | 0.4114 | 0.968 |
| suite P9 | collector-only | f551ca0 (C1) | 9 | 104.5 | 0.4151 | 0.778 |
| suite PI | collector-only | f551ca0 (C1) | 4130 | 1.181 | 0.7144 | 0.0028 |
| all complete (id,mode) rows | scalar-clock sharded N=16 | f551ca0 (X1b) | 4706 | 3.741 | 1.32 | 0.706 |
| suite P1 | scalar-clock sharded N=16 | f551ca0 (X1b) | 400 | 2.041 | 1.672 | 0.311 |
| suite P3 | scalar-clock sharded N=16 | f551ca0 (X1b) | 60 | 2.109 | 6.471 | 0.055 |
| suite P4 | scalar-clock sharded N=16 | f551ca0 (X1b) | 28 | 2.184 | 0.6983 | 0.885 |
| suite P5 | scalar-clock sharded N=16 | f551ca0 (X1b) | 33 | 1.725 | 9,420 | 0.00859 |
| suite P6 | scalar-clock sharded N=16 | f551ca0 (X1b) | 34 | 4.742 | 1.719 | 0.987 |
| suite P7 | scalar-clock sharded N=16 | f551ca0 (X1b) | 12 | 537.8 | 1.616 | 0.603 |
| suite P9 | scalar-clock sharded N=16 | f551ca0 (X1b) | 9 | 473.5 | 0.9792 | 0.883 |
| suite PI | scalar-clock sharded N=16 | f551ca0 (X1b) | 4130 | 1.453 | 5.42 | 0.0333 |
| all complete (id,mode) rows | vector-clock | f551ca0 (X1b) | 4704 | 11.92 | 6.256 | 0.91 |
| suite P1 | vector-clock | f551ca0 (X1b) | 400 | 0.7736 | 29.24 | 0.535 |
| suite P3 | vector-clock | f551ca0 (X1b) | 60 | 1.902 | 29.61 | 0.474 |
| suite P4 | vector-clock | f551ca0 (X1b) | 28 | -0.8294 | 48.73 | 0.495 |
| suite P5 | vector-clock | f551ca0 (X1b) | 33 | 1.867 | 3.827e+04 | 0.0654 |
| suite P6 | vector-clock | f551ca0 (X1b) | 34 | -158.6 | 29.89 | 0.944 |
| suite P7 | vector-clock | f551ca0 (X1b) | 11 | 2,066 | 6.132 | 0.891 |
| suite P9 | vector-clock | f551ca0 (X1b) | 8 | 1,537 | 5.88 | 0.916 |
| suite PI | vector-clock | f551ca0 (X1b) | 4130 | 0.9801 | 46.56 | 0.113 |

X3's section (a) collector-only fit (X1-follow, d38d057, 4 points on one host type each): intercept −1.757 s (`-n 1`) / 4.128 s (default), slope 0.2946 / 0.07542 µs per record. C1's runs are `-n 1`; the six-program fit above uses the six programs of the section.



## Item 9: pairs collector-only mode reports that scalar-clock mode orders, by control-flow shape, next to X5's derived 1,021

Programs analysed in both recordings: 4707 of 4725; not analysed: {'no recording: SC': 18}. Reported by both modes: 10531 pairs. Reported by scalar-clock only: 7950 pairs (by suite {'P1': 212, 'P3': 4, 'P4': 76, 'P5': 3, 'P6': 72, 'P7': 1, 'P9': 14, 'PI': 7568}; not part of the comparison).

Collector-only reports, scalar-clock does not, and scalar-clock's record of the pair is: 
ORDERED by the barrier clock (1016 pairs, S1); SC has no record of the pair: 96; SC orders it by a certificate (hb_class none): 26. Total CO-only reports: 1138.

**S1: collector-only reports that scalar-clock orders (barrier-only clock, no certificate)**; the last column = pairs in S1 that are not among X5's pairs (no shape recorded):

| Suite | Programs with a pair | Pairs | Loop around the barrier | Warp barrier between | Exit before the barrier | Barrier on one branch | Other | not among X5's |
|---|---|---|---|---|---|---|---|---|
| Indigo3 | 28 | 52 | 4 | 0 | 0 | 0 | 48 | 0 |
| Indigo 1.3 | 840 | 840 | 560 | 140 | 140 | 0 | 0 | 0 |
| ECL graph codes | 12 | 22 | 6 | 0 | 0 | 0 | 16 | 0 |
| ScoR applications | 10 | 83 | 23 | 60 | 0 | 0 | 0 | 0 |
| ScoR litmus kernels | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, other applications | 1 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, SuperCollider's 10 | 2 | 17 | 0 | 0 | 0 | 17 | 0 | 0 |
| **All** | 893 | 1016 | 595 | 200 | 140 | 17 | 64 | 0 |

**S2: X5's derived 1,021 pairs** (tab:eval-shapes; separate X1 recordings, same pairs in both modes):

| Suite | Programs with a pair | Pairs | Loop around the barrier | Warp barrier between | Exit before the barrier | Barrier on one branch | Other |
|---|---|---|---|---|---|---|---|
| Indigo3 | 32 | 56 | 8 | 0 | 0 | 0 | 48 |
| Indigo 1.3 | 840 | 840 | 560 | 140 | 140 | 0 | 0 |
| ECL graph codes | 12 | 22 | 6 | 0 | 0 | 0 | 16 |
| ScoR applications | 10 | 83 | 23 | 60 | 0 | 0 | 0 |
| ScoR litmus kernels | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| HeCBench, other applications | 1 | 2 | 2 | 0 | 0 | 0 | 0 |
| HeCBench, SuperCollider's 10 | 2 | 17 | 0 | 0 | 0 | 17 | 0 |
| **All** | 898 | 1021 | 599 | 200 | 140 | 17 | 65 |

S1 and S2 share 1016 pairs; 0 pairs are in S1 only and 5 in S2 only.

**Pairs in one set and not the other**, by reason (every pair, with its evidence: `item9_pair_differences.csv`):

| set | reason | pairs |
|---|---|---|
| in X5, not in S1 | scalar-clock reports it too | 4 |
| in X5, not in S1 | schedule-dependent edge | 1 |

By suite:

| suite | set | reason | pairs |
|---|---|---|---|
| P1 | in X5, not in S1 | scalar-clock reports it too | 4 |
| P6 | in X5, not in S1 | schedule-dependent edge | 1 |

Pairs that fit none of the three reasons (schedule-dependent edge, candidate mechanism off, scalar-clock reports it too): **0**.

**Collector-only reports outside S1** (122 pairs: scalar-clock does not report them, and does not order them by the barrier clock either; `item9_CO_only_outside_S1.csv`):

| suite | scalar-clock's record of the pair | edge in X1b's scalar-clock recording | pairs |
|---|---|---|---|
| P1 | no record | False | 7 |
| P3 | ORDERED:None | True | 16 |
| P4 | ORDERED:None | True | 10 |
| P4 | no record | True | 1 |
| P6 | no record | True | 1 |
| PI | no record | False | 87 |



## Item 10: repeatability of collector-only mode (the "Is one run enough?" measures)

Programs with kept reps: 64 (recordings per program: {6: 64}); recordings = kept rep directories of the two parity recordings A (c41-c43) and B (c40, c55, c62). Pairs of recordings: 960.

| scope | programs | pairs of recordings | same program verdict | same reported pair set (race type removed) | identical edge sets | edge Jaccard min / median / mean |
|---|---|---|---|---|---|---|
| all pairs | 64 | 960 | 960 | 906 (933) | 723 | 0.6566 / 1.0000 / 0.9847 |
| same recording set (same 3 nodes, different reps) | 64 | 384 | 384 | 384 (384) | 294 | 0.6566 / 1.0000 / 0.9859 |
| across the two sets (A against B) | 64 | 576 | 576 | 522 (549) | 429 | 0.6765 / 1.0000 / 0.9839 |
| recordings on different nodes | 64 | 576 | 576 | 522 (549) | 429 | 0.6765 / 1.0000 / 0.9839 |
| recordings on the same node | 64 | 384 | 384 | 384 (384) | 294 | 0.6566 / 1.0000 / 0.9859 |

By suite:

| scope | programs | pairs | same verdict | same reported set (untyped) | identical edge sets | edge J min / median / mean |
|---|---|---|---|---|---|---|
| P1 | 10 | 150 | 150 | 123 (150) | 102 | 0.9000 / 1.0000 / 0.9852 |
| P3 | 10 | 150 | 150 | 150 (150) | 98 | 0.7500 / 1.0000 / 0.9812 |
| P4 | 10 | 150 | 150 | 141 (141) | 67 | 0.9184 / 0.9895 / 0.9805 |
| P5 | 10 | 150 | 150 | 150 (150) | 150 | 1.0000 / 1.0000 / 1.0000 |
| P6 | 10 | 150 | 150 | 150 (150) | 150 | 1.0000 / 1.0000 / 1.0000 |
| P7 | 2 | 30 | 30 | 30 (30) | 30 | 1.0000 / 1.0000 / 1.0000 |
| P9 | 2 | 30 | 30 | 30 (30) | 30 | 1.0000 / 1.0000 / 1.0000 |
| PI | 10 | 150 | 150 | 132 (132) | 96 | 0.6566 / 1.0000 / 0.9552 |

Pairs of recordings with a different program verdict: 0

Pairs of recordings with a different reported pair set: 54; programs: `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n`, `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n`, `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n`, `P4-graph-coloring-racy-small`, `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e`, `PI-push_node_neighbors_boundsBug_reverse_atomicBug-counterDAG_200n_1000e`
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A1@c41 vs B1@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A1@c41 vs B2@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A1@c41 vs B3@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A2@c41 vs B1@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A2@c41 vs B2@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A2@c41 vs B3@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A3@c41 vs B1@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A3@c41 vs B2@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_RaceBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-100n` A3@c41 vs B3@c40: 4 vs 4 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A1@c43 vs B1@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A1@c43 vs B2@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A1@c43 vs B3@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A2@c43 vs B1@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A2@c43 vs B2@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A2@c43 vs B3@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A3@c43 vs B1@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A3@c43 vs B2@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Pull_Determ_IntType_NonPersist_RaceBug_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-slower_atomic-1296n` A3@c43 vs B3@c55: 3 vs 3 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A1@c41 vs B1@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A1@c41 vs B2@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A1@c41 vs B3@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A2@c41 vs B1@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A2@c41 vs B2@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A2@c41 vs B3@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A3@c41 vs B1@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A3@c41 vs B2@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P1-CC_CUDA_V_Topo_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Thread_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug-default-1296n` A3@c41 vs B3@c40: 29 vs 29 pairs; untyped sets equal: True
  - `P4-graph-coloring-racy-small` A1@c43 vs B1@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A1@c43 vs B2@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A1@c43 vs B3@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A2@c43 vs B1@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A2@c43 vs B2@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A2@c43 vs B3@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A3@c43 vs B1@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A3@c43 vs B2@c55: 11 vs 9 pairs; untyped sets equal: False
  - `P4-graph-coloring-racy-small` A3@c43 vs B3@c55: 11 vs 9 pairs; untyped sets equal: False
  - `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` A1@c42 vs B1@c62: 47 vs 48 pairs; untyped sets equal: False
  - `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` A1@c42 vs B2@c62: 47 vs 48 pairs; untyped sets equal: False
  - `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` A1@c42 vs B3@c62: 47 vs 48 pairs; untyped sets equal: False
  - `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` A2@c42 vs B1@c62: 47 vs 48 pairs; untyped sets equal: False

Lowest edge Jaccard:

| program | recording a | recording b | edges a | edges b | Jaccard | verdicts |
|---|---|---|---|---|---|---|
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | B2@c62 | B3@c62 | 76 | 88 | 0.6566 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A2@c42 | B2@c62 | 95 | 76 | 0.6765 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | B1@c62 | B3@c62 | 87 | 88 | 0.6827 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A1@c42 | B2@c62 | 89 | 76 | 0.6837 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A1@c42 | B1@c62 | 89 | 87 | 0.7087 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A3@c42 | B3@c62 | 85 | 88 | 0.7300 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A3@c42 | B2@c62 | 85 | 76 | 0.7312 | RACE/RACE |
| `P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n` | B1@c55 | B2@c55 | 6 | 8 | 0.7500 | CLEAN/CLEAN |
| `P3-CC_CUDA_E_Topo_NonDeterm_IntType_ReadWrite_Persist_CudaAtomic_NoBoundsBug_NoLivelockBug_NoFieldBug-100n` | B1@c55 | B3@c55 | 6 | 8 | 0.7500 | CLEAN/CLEAN |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A2@c42 | B1@c62 | 95 | 87 | 0.7500 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A2@c42 | B3@c62 | 95 | 88 | 0.7596 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A3@c42 | B1@c62 | 85 | 87 | 0.7732 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A1@c42 | B3@c62 | 89 | 88 | 0.8061 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | B1@c62 | B2@c62 | 87 | 76 | 0.8111 | RACE/RACE |
| `PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` | A2@c42 | A3@c42 | 95 | 85 | 0.8182 | RACE/RACE |
