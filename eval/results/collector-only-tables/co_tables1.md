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
