# CO_CHAIN: collector-only mode with the chain closure (C6, step 3)

Branch `eval/co-chain` (cuVein f551ca0 + the merge of `eval/collector-only-tables`; step 1 `9fa48e9` code, step 2 `d3e4e0d` results). Step 3 is analysis only: no recording, no GPU, no change to `python/`, the runtime, the collector or `hb_oracle.py`; cuRacePaper was only read (`git show`). Every number below comes from a CSV or a kernel JSON through the scripts `eval/baselines/setup/c6_*` and is also in `eval/results/co-chain/step3/` (`tables/`, `cost/`, `detect/`, `rw/`, `mt/`).

Name in this file: **CO** = C1's collector-only run (verdicts from the collector's edges, no sync pass, no closure), **CO+chain** = the same recordings re-analysed with `--chain-closure` (step 2), **VC** / **SC** = vector-clock / scalar-clock. "Table 3" is the paper's accuracy table (`tab:eval-accuracy`, `tables/coverage.tex`: Indigo 1.3 counted per code, aggregate row over Indigo3, Indigo 1.3, ECL, ScoR applications, cuHadron in scope); C3 and C4 call the per-program-input version "Table 6.1".

## 0. Results in short

- **Verdict changes against CO** (all CLEAN to RACE, 31 of 4,709 programs, parity violations 0): PI 26 (25 unlabelled, 1 racy-labelled), P4 2 (`uts-norace-small`, `uts-norace-large`, both race-free-labelled), P7 2 (`hotspot`, `lavaMD`, unlabelled), P9 1 (`knn`, scored race-free). P1, P3, P5, P6: 0. Real-world: `hecbench-surfel-1-fixed` CLEAN to RACE, `amrex-1` buggy and fixed ERROR to RACE (the reference timed out), candidate set none.
- **Table 3, aggregate row** (races alone; Indigo 1.3 per code): VC 486/486 recall, 18/468 FP; SC 486/486, 18/468; CO 485/486, 54/468; **CO+chain 485/486, 56/468**. Per program-input: CO 1,956/2,082 and 246/1,548, CO+chain 1,957/2,082 and 248/1,548. The two extra false positives are the two `uts-norace` ScoR applications; the extra detection is one racy-labelled Indigo 1.3 program-input (the only one the oracle calls a conflict that CO missed). CO's recall is 485/486, not the 486/486 of the draft text, because one cuHadron racy program (`P6-memcpy-shared_readwrite_race-racy`) is Clean in CO and in CO+chain; the draft `coverage.tex` shows 6/6 for CO on cuHadron, the recomputed C1 cell is 5/6 (section 2.1).
- **Against scalar-clock** (programs with a verdict in both): CO+chain finds 259 programs SC calls Clean (232 race-free-labelled: 224 Indigo 1.3, 6 ScoR applications, 2 HeCBench; 24 racy Indigo 1.3; 3 unlabelled HeCBench) and misses 2 that SC finds (`P5-race_interblock_none-lock_rtraw`, `P6-memcpy-shared_readwrite_race-racy`). In the 2,668 programs Race in both, scalar-clock reports 4,001 pc pairs in 345 programs that CO+chain does not. None of the 2 missed programs falls in a gap specific to collector-only mode; of the 4,001 pairs 74 (34 programs, all out-of-bounds `boundsBug` variants) have a dropped-word deficit at one of their pcs, none is a pool exhaustion that can be shown, 0 are pc-0 (section 3).
- **Production races**: CCCL top-k, Ginkgo range-minimum and Kokkos rw_sum are detected through chain-derived or rescued reports (8 / 3 / 3 matched pairs); RAFT select_k stays missed (its 3 matched pairs are joined only by a path through a non-read accessor); PCL's data-race half is detected (44 of the 102 matched pairs). Scoring in section 2.2.
- **Cost** (CAP_84600 section 3 rule, 4,685-program set): run alone 5.564 (= C1; over all 4,709 programs 5.652, the paper's 5.7), verdict step 2.098 (C1) and about 2.24 for CO+chain on A5's node class (bounds 2.10 to 2.56), end-to-end 7.773 (C1) and about 7.92 (bounds 7.77 to 8.25), against VC 7.320 / 2.454 / 9.966 and SC 7.015 / 2.173 / 9.339. Closure's share of the verdict step: 0.16 % over all programs, 5.6 % on HeCBench (section 5).

## 1. Setup and what the mode is

Step 2 (README in `eval/results/co-chain/`): the 4,725 C1 programs (`final-2026-11-co`, `-co-long`, `-co-24h`) and the 72 real-world recordings (`realworld-2026-10-co` 56, `realworld-2026-10-t21c-co` 16) re-analysed from the stored kernel JSONs with `parallel.py analyze --chain-closure` (`--analysis-workers 16 --confirm`), `BASELINE_MODES=collector-only`; recordings untouched. Parity rule: a program whose chain_derived and chain_rescued are both 0 must equal its C1 row on verdict, reports_dedup, report_ids, report_lines and the classes note: 3,394 C1 programs, 0 violations; 1,093 programs have derived pairs and 532 rescued ones.

**What the collector records** (c6 step 0, code at `98371ee`; C = `pc_dependency_analysis.cpp`). One last accessor per 4-byte word of an allocation (64-bit shadow word: thread, generation, pc); every access (read, write, atomic) exchanges it and gets the previous one, so the graph holds the transition last accessor -> current accessor, never writer + readers: R1, R2 gives the edge R1 -> R2, and a later write W gives R2 -> W, not R1 -> W. The kernel JSON has `nodes` (pc, flags, access size, lane and address counts) and `edges` `(current pc, ancient pc)` with five word counts: intra_thread (also the cold-miss count), intra_instance_launch (repeat lanes, self edges only), intra_warp, intra_block, intra_grid. No addresses, no thread ids, no order. Nothing is sampled or capped on the default path; an edge is one record per pc pair.

**What the closure does** (`sync_dominance.chain_closure_pairs`). A chain is a walk a -> h1 -> ... -> hk -> c over recorded edges with every inner pc a read; its end threads are related by at most the widest hop (same warp < same block < same grid), so the pair is judged by `judge()` at the narrowest such bound over all chains (a minimax). Pairs an edge already joins are judged as before, except that an edge at thread-local distance is **rescued** when a chain gives it a cross-thread bound (`chain_rescue`); pairs only a chain joins are **derived** (`chain`). The closure is over pcs, not addresses. It stops with an ERROR past 10^6 derived pairs per kernel (never reached: 0 chain-cap rows).

## 2. Tables (make_tables.py with a fourth cuVein column)

Method (C4's, as in `p_co_offline_tables.sh`): `c6_stage.sh` builds a sandbox of `eval/results` in which `baselines-cuvein*.csv` are the paper's current state (eval/cap-84600: VC and SC, C1's CO with the atomicCAS re-analysis, iGUARD, racecheck) plus `baselines-cuvein-cc.csv` (the step-2 rows as mode `collector-only-chain`), and a **copy** of `make_tables.py` that gets C4's fourth-mode patch with the names changed (`git apply` of `git diff eval/co-chain...eval/co-offline -- make_tables.py`, `collector-only-rescored` -> `collector-only-chain`, `--co-offline` -> `--co-chain`). The tracked `make_tables.py` is untouched. The full 4-column matrix is `step3/mt/BASELINES_SUMMARY_4col.md`; `c6_tables.py` (C4's `co_offline_tables.py` plus a per-code section and the oracle section) writes the tables below. Every VC and SC cell recomputes to the paper's value (check at the end of the generated section).

### Table 3 (tab:eval-accuracy): accuracy per suite, data races alone, Indigo 1.3 counted per code, four cuVein columns

Cells: recall TP/(TP+FN) · false-positive rate FP/(FP+TN). Indigo 1.3 labels a code, so its rows count codes: a code is reported when the mode reports Race on any of its seven inputs. All other rows count program-inputs as in the paper. Aggregate = Indigo3 + Indigo 1.3 (codes) + ECL + ScoR applications + cuHadron in scope. CO (C1) = C1's collector-only run (atomicCAS row as in eval/cap-84600), CO+chain = the same recordings with the chain closure in the verdict step. `n codes` is the number of Indigo 1.3 codes found.

| suite | vector-clock | scalar-clock | CO (C1) | CO+chain |
|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 |
| Indigo 1.3 (590 codes) | 266/266 · 0/180 | 266/266 · 0/180 | 266/266 · 32/180 | 266/266 · 32/180 |
| Indigo 1.3, SC's 99 (99 codes) | 45/45 · 0/44 | 45/45 · 0/44 | 45/45 · 4/44 | 45/45 · 4/44 |
| ECL | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 |
| ScoR applications | 14/14 · 2/14 | 14/14 · 2/14 | 14/14 · 6/14 | 14/14 · 8/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/7 | 3/3 · 2/7 |
| **All pre-registered** | 486/486 · 18/468; 16 ERR | 486/486 · 18/468; 16 ERR | 485/486 · 54/468; 16 ERR | 485/486 · 56/468; 16 ERR |

Aggregate check, vector-clock: paper (486, 486, 18, 468), recomputed (486, 486, 18, 468) -> equal

Aggregate check, scalar-clock: paper (486, 486, 18, 468), recomputed (486, 486, 18, 468) -> equal

Aggregate check, CO (C1): paper (486, 486, 54, 468), recomputed (485, 486, 54, 468) -> DIFFERENT

### Accuracy per program-input (Indigo 1.3 counted per run), four columns

| suite | vector-clock | scalar-clock | CO (C1) | CO+chain |
|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 |
| Indigo 1.3, SC's 99 | 43/45 · 0/44 | 43/45 · 0/44 | 43/45 · 4/44 | 43/45 · 4/44 |
| ECL | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 |
| ScoR applications | 14/14 · 2/14 | 14/14 · 2/14 | 14/14 · 6/14 | 14/14 · 8/14 |
| ScoR litmus + canary | 4/19 · 1/14 | 3/19 · 0/14 | 2/19 · 0/14 | 2/19 · 0/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/7 | 3/3 · 2/7 |
| **All pre-registered** | 1,934/2,082 · 18/1,548; 16 ERR | 1,934/2,082 · 18/1,548; 16 ERR | 1,956/2,082 · 246/1,548; 16 ERR | 1,957/2,082 · 248/1,548; 16 ERR |

### tab:eval-accuracy-union and tab:eval-countings: the three countings, four columns (per program-input)

races = Race alone; strong = a program with an unordered strong conflict reported (class `sc`); union = Race or strong. Cells TP/(TP+FN) · FP/(FP+TN). VC = vector-clock, SC = scalar-clock, CO = C1, CC = CO+chain.

| suite | VC races | VC strong | VC union | SC races | SC strong | SC union | CO races | CO strong | CO union | CC races | CC strong | CC union |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 0/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 | 0/1,862 · 0/1,260 | 1,738/1,862 · 224/1,260 |
| ECL | — · 16/60 | — · 36/60 | — · 44/60 | — · 16/60 | — · 32/60 | — · 40/60 | — · 16/60 | — · 36/60 | — · 44/60 | — · 16/60 | — · 36/60 | — · 44/60 |
| ScoR applications | 14/14 · 2/14 | 8/14 · 7/14 | 14/14 · 7/14 | 14/14 · 2/14 | 8/14 · 4/14 | 14/14 · 4/14 | 14/14 · 6/14 | 6/14 · 4/14 | 14/14 · 8/14 | 14/14 · 8/14 | 6/14 · 4/14 | 14/14 · 10/14 |
| ScoR litmus + canary | 4/19 · 1/14 | 17/19 · 4/14 | 19/19 · 5/14 | 3/19 · 0/14 | 17/19 · 0/14 | 18/19 · 0/14 | 2/19 · 0/14 | 16/19 · 0/14 | 17/19 · 0/14 | 2/19 · 0/14 | 17/19 · 0/14 | 18/19 · 0/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 0/2 · 0/6; 2 TO | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 0/3 · 0/6; 1 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/7 | 0/3 · 1/7 | 3/3 · 2/7 | 3/3 · 2/7 | 0/3 · 1/7 | 3/3 · 3/7 |
| **All pre-registered** | 1,934/2,082 · 18/1,548; 16 ERR | 8/2,082 · 115/1,548; 16 ERR | 1,934/2,082 · 123/1,548; 16 ERR | 1,934/2,082 · 18/1,548; 16 ERR | 8/2,082 · 108/1,548; 16 ERR | 1,934/2,082 · 116/1,548; 16 ERR | 1,956/2,082 · 246/1,548; 16 ERR | 6/2,082 · 112/1,548; 16 ERR | 1,956/2,082 · 348/1,548; 16 ERR | 1,957/2,082 · 248/1,548; 16 ERR | 6/2,082 · 112/1,548; 16 ERR | 1,957/2,082 · 350/1,548; 16 ERR |

### tab:eval-litmus: the 33 ScoR litmus kernels, four columns

Race = a data race is reported; Strong = only an unordered strong conflict is reported; — = nothing reported. `rtraw` counted as recorded.

| kernel | ScoR label | VC | SC | CO (C1) | CO+chain |
|---|---|---|---|---|---|
| `canary_pc_level_false_negative` | racy | Race | — | — | — |
| `norace_interblock_atom` | race-free | — | — | — | — |
| `norace_interblock_fence_raw` | race-free | Strong | — | — | — |
| `norace_interblock_lock_waw` | race-free | — | — | — | — |
| `norace_interwarp-block_fence-atom_hrd-indirect` | race-free | Race | — | — | — |
| `norace_interwarp-block_fence_hrf-indirect` | race-free | Strong | — | — | — |
| `norace_interwarp_blkatom` | race-free | — | — | — | — |
| `norace_interwarp_blkfence_raw` | race-free | Strong | — | — | — |
| `norace_interwarp_blklock_waw` | race-free | — | — | — | — |
| `norace_interwarp_dev-blkatom` | race-free | — | — | — | — |
| `norace_interwarp_dev-blklock_waw` | race-free | — | — | — | — |
| `norace_interwarp_fence_raw` | race-free | Strong | — | — | — |
| `norace_intrawarp_none-blkatom` | race-free | — | — | — | — |
| `norace_intrawarp_none-blklock-no-tf_waw` | race-free | — | — | — | — |
| `norace_intrawarp_none-blklock_waw` | race-free | — | — | — | — |
| `race_interblock_blkatom` | racy | Race | Race | Race | Race |
| `race_interblock_blkfence_raw` | racy | Strong | Strong | Strong | Strong |
| `race_interblock_blklock_waw` | racy | Race | Race | Race | Race |
| `race_interblock_fence_rtraw` | racy | Strong | Strong | Strong | Strong |
| `race_interblock_lock-blkfence_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interblock_lock-no-stf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interblock_lock-no-tf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interblock_none-atom_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interblock_none-lock_rtraw` | racy | Race | Race | — | Strong **changed** |
| `race_interblock_none-lock_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_blklock-no-stf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_blklock-no-tf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_dev-blklock-no-stf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_dev-blklock-no-tf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_none-atom_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_none-blkatom_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_none-blklock_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_none-lock_waw` | racy | Strong | Strong | Strong | Strong |

Litmus kernels whose cell differs between C1 and CO+chain: 1
  - `race_interblock_none-lock_rtraw` — -> Strong

33 P5 programs; 33 kernels parsed from the paper's table; 0 vector/scalar cells differ from the paper.

### Program level: CO+chain against CO

| suite | programs | same verdict | CO Race → CO+chain Clean | CO Clean → CO+chain Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 4104 | 0 | 26 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 26 | 0 | 2 | 0 |
| P5 | 33 | 33 | 0 | 0 | 0 |
| P6 | 34 | 34 | 0 | 0 | 0 |
| P7 | 14 | 12 | 0 | 2 | 0 |
| P9 | 10 | 9 | 0 | 1 | 0 |
| **all** | 4709 | 4678 | 0 | 31 | 0 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P4 | CO CLEAN → CO+chain RACE | 0 | 2 | 0 |
| P7 | CO CLEAN → CO+chain RACE | 0 | 0 | 2 |
| P9 | CO CLEAN → CO+chain RACE | 0 | 1 | 0 |
| PI | CO CLEAN → CO+chain RACE | 1 | 0 | 25 |

### Program level: CO+chain against SC

| suite | programs | same verdict | SC Race → CO+chain Clean | SC Clean → CO+chain Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 3882 | 0 | 248 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 22 | 0 | 6 | 0 |
| P5 | 33 | 32 | 1 | 0 | 0 |
| P6 | 34 | 33 | 1 | 0 | 0 |
| P7 | 14 | 10 | 0 | 3 | 1 |
| P9 | 10 | 7 | 0 | 2 | 1 |
| **all** | 4709 | 4446 | 2 | 259 | 2 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P4 | SC CLEAN → CO+chain RACE | 0 | 6 | 0 |
| P5 | SC RACE → CO+chain CLEAN | 1 | 0 | 0 |
| P6 | SC RACE → CO+chain CLEAN | 1 | 0 | 0 |
| P7 | SC CLEAN → CO+chain RACE | 0 | 0 | 3 |
| P7 | SC TIMEOUT → CO+chain CLEAN | 0 | 0 | 1 |
| P9 | SC CLEAN → CO+chain RACE | 0 | 2 | 0 |
| P9 | SC TIMEOUT → CO+chain CLEAN | 0 | 1 | 0 |
| PI | SC CLEAN → CO+chain RACE | 24 | 224 | 0 |

Race-free-labelled programs Race in CO+chain and Clean in scalar-clock: **232**; per suite: P4 6, P9 2, PI 224

Race-free-labelled programs Race in CO+chain and Clean in C1's CO: **3**: `P4-uts-norace-small`, `P4-uts-norace-large`, `P9-knn-cuda`

All race-free-labelled programs that are Race in CO+chain: 251 (Race in scalar-clock too: 19; in C1's CO: 248)

Scalar-clock Race, CO+chain Clean: 2 programs (labels: {'racy': 2}; per suite {'P6': 1, 'P5': 1})

Scalar-clock Clean, CO+chain Race: 259 programs (labels: {'race-free': 232, 'racy': 24, 'unlabelled': 3}; per suite {'PI': 248, 'P4': 6, 'P9': 2, 'P7': 3})

### Indigo 1.3 per program-input against the input-level oracle (baselines-pi-oracle.csv)

The oracle file has 1338 rows (ids found in the runs: 1338). Cell: programs with that verdict. Rows are the oracle's answer (CONFLICT = two threads touch one location, one writes, not both atomic, no barrier between; NO-CONFLICT otherwise) by the suite's label.

| label | oracle | n | vector-clock Race | scalar-clock Race | CO (C1) Race | CO+chain Race |
|---|---|---|---|---|---|---|
| racy | CONFLICT | 650 | 650 | 650 | 649 | 650 |
| racy | NO-CONFLICT | 148 | 0 | 0 | 24 | 24 |
| race-free | NO-CONFLICT | 540 | 0 | 0 | 96 | 96 |

Racy-labelled Indigo 1.3 program-inputs a mode does not report (verdict not Race), split by the oracle's answer:

| mode | missed | oracle CONFLICT | oracle NO-CONFLICT | not in oracle file |
|---|---|---|---|---|
| vector-clock | 148 | 0 | 148 | 0 |
| scalar-clock | 148 | 0 | 148 | 0 |
| CO (C1) | 125 | 1 | 124 | 0 |
| CO+chain | 124 | 0 | 124 | 0 |

Missed by CO+chain and reported by scalar-clock (racy-labelled PI): 0; missed by scalar-clock and reported by CO+chain: 24; missed by C1 and reported by CO+chain: 1; missed by CO+chain and reported by C1: 0.

Race verdicts on Indigo 1.3 program-inputs the oracle says have NO-CONFLICT, by label:

| mode | race-free-labelled | racy-labelled | unlabelled |
|---|---|---|---|
| vector-clock | 0 | 0 | 0 |
| scalar-clock | 0 | 0 | 0 |
| CO (C1) | 96 | 24 | 0 |
| CO+chain | 96 | 24 | 0 |

### Check against the paper (vector-clock and scalar-clock cells)

Every vector-clock and scalar-clock cell of the per-program-input accuracy table, the union and three-countings tables and the litmus table recomputes to the paper's value.


### 2.1 Reading the tables

- Table 3 differs from CO in two cells only: ScoR applications FP 6/14 -> 8/14 (`uts-norace-small` and `-large`) and HeCBench SC's 10 FP 1/7 -> 2/7 (`knn`, scored race-free). Indigo 1.3 per code stays 266/266 and 32/180 (the 26 changed programs are 25 unlabelled out-of-bounds variants and one racy program in a code already reported on another input). The aggregate FP therefore moves from 54 to 56 of 468.
- The C1 aggregate recomputes to 485/486 against the 486/486 of the draft text; the one racy cuHadron program CO misses is `P6-memcpy-shared_readwrite_race-racy` (SC reports shared:0x70-0x90 RAW; CO has the edge only at thread-local distance, section 3.2). The closure does not rescue it.
- Union and the three countings: the chain column equals CO's except Indigo 1.3 (+1 race), ScoR applications (races FP 6 -> 8, union FP 8 -> 10) and HeCBench SC's 10 (FP 1 -> 2, union FP 2 -> 3). Litmus: one kernel changes, `race_interblock_none-lock_rtraw`, from `—` to Strong; no litmus cell becomes Race.
- Against the oracle, CO+chain misses 124 racy-labelled Indigo 1.3 program-inputs, all 124 with no conflict in the oracle (VC and SC miss 148, all NO-CONFLICT; CO misses 125, one of them a CONFLICT). It reports Race on 96 race-free-labelled and 24 racy-labelled program-inputs the oracle says have no conflict, the same counts as CO; so the closure removes the only oracle-confirmed miss of CO and adds no report on a no-conflict input.

### 2.2 Real-world recall and candidate counts

Method (C4's, `p_co_rw.sh`): the 56 recall-set and 16 candidate-set recordings of C2 (`realworld-2026-10-co`, `realworld-2026-10-t21c-co`) re-attributed with `rw_attribute.py` of the branch that produced each table (copies of `study/realworld-recall` / `study/realworld-candidates` with C4's `RW_MODES` edit) with two edits: `sd.analyze(dot, kj, chain_closure=True)` and `chain_src` / `chain_path` on every report record (`c6_rw_setup.sh`); the per-id CSVs are the step-2 rows; `rw_score.py` scores them against the pre-registered oracles (`recall_pairs.json`). One attribution per id, serial, `c6_rw_run.sh`. Vector-clock and scalar-clock cells are T21b / T21c's `recall.csv`, the CO column is C2's.

### Recall set (T21b): per target and component, CO+chain next to vector-clock, scalar-clock and C2's collector-only run

CO+chain rows: `rw_score.py` of study/realworld-recall on the chain-closure attribution of the C2 recordings (`rw_attribute.py` with `chain_closure=True`). `NOT-SCORED` = no row: the id was not attributed (see the missing list in CO_CHAIN.md).

| target | variant | comp | vector-clock | scalar-clock | CO (C2) | CO+chain | CO+chain n_race / n_sc |
|---|---|---|---|---|---|---|---|
| amrex-1 | buggy | DR | MISSED | MISSED | MISSED | NOT-SCORED | / **changed** |
| amrex-1 | fixed | - | — | — | NOT-SCORED | NOT-SCORED | / |
| bitsandbytes-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 65/0 |
| bitsandbytes-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 64/0 |
| cccl-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 16/0 |
| cccl-1 | fixed | - | STILL | STILL | STILL | STILL | 16/0 |
| cccl-2 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 457/0 |
| cccl-2 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 447/0 |
| cccl-3 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 57/8 **changed** |
| cccl-3 | buggy | SC | DETECTED | DETECTED | DETECTED | DETECTED | 57/8 |
| cccl-3 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 58/8 |
| cccl-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/15 |
| cccl-4 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/15 |
| cmssw-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 5/0 |
| cmssw-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 0/6 |
| ginkgo-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 15/0 |
| ginkgo-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| ginkgo-5 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 6/0 **changed** |
| ginkgo-5 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| hecbench-dxtc2-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 114/0 |
| hecbench-dxtc2-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 3/0 |
| hecbench-hungarian-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | NOT-SCORED | / **changed** |
| hecbench-hungarian-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | NOT-SCORED | / **changed** |
| hecbench-morphology-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 52/0 |
| hecbench-morphology-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 68/0 |
| hecbench-surfel-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 27/0 |
| hecbench-surfel-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 13/0 |
| kokkos-5 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 69/0 **changed** |
| kokkos-5 | fixed | - | CLEAN | CLEAN | RESIDUAL | RESIDUAL | 71/0 |
| kokkos-6 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 94/0 |
| kokkos-6 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 87/0 |
| lit-arrayfire-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 10/0 |
| lit-arrayfire-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 8/0 |
| lit-exllamav3-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 176/0 |
| lit-exllamav3-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 156/0 |
| lit-fbgemm-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| lit-fbgemm-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| lit-shoc-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 134/0 |
| lit-shoc-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 134/0 |
| lit-shoc-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 120/0 |
| llamacpp-2 | buggy | DR | DETECTED | DETECTED | DETECTED | NOT-SCORED | / **changed** |
| llamacpp-2 | fixed | - | CLEAN | CLEAN | STILL | NOT-SCORED | / **changed** |
| llamacpp-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| llamacpp-4 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| llamacpp-5 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1546/0 |
| llamacpp-5 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 1026/0 |
| opencv-2 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 2521/0 |
| opencv-2 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 9/0 |
| pytorch-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 5/0 |
| pytorch-1 | fixed | - | CLEAN | CLEAN | STILL | STILL | 5/0 |
| pytorch-3 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| pytorch-3 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| pytorch-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/0 |
| pytorch-4 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 1/0 |
| pytorch_cluster-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 18/0 |
| pytorch_cluster-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| raft-1 | buggy | DR | DETECTED | DETECTED | MISSED | MISSED | 29/2 |
| raft-1 | buggy | SC | DETECTED | DETECTED | DETECTED | DETECTED | 29/2 |
| raft-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 27/2 |

**Counts** (rows of each mode):

| components | outcome | vector-clock | scalar-clock | CO (C2) | CO+chain |
|---|---|---|---|---|---|
| buggy, data-race components | DETECTED | 25 | 25 | 21 | 23 |
| buggy, data-race components | MISSED | 1 | 1 | 5 | 1 |
| buggy, data-race components | **total** | 26 | 26 | 26 | 24 |
| buggy, strong-conflict components | DETECTED | 2 | 2 | 2 | 2 |
| buggy, strong-conflict components | DETECTED-AS-DR | 3 | 3 | 3 | 2 |
| buggy, strong-conflict components | **total** | 5 | 5 | 5 | 4 |
| fixed builds | CLEAN-FOR-PAIR | 20 | 20 | 17 | 17 |
| fixed builds | NOT-SCORED | 0 | 0 | 1 | 0 |
| fixed builds | RESIDUAL-AS-EXPECTED | 6 | 6 | 7 | 6 |
| fixed builds | STILL-REPORTED | 1 | 1 | 3 | 2 |
| fixed builds | **total** | 27 | 27 | 28 | 25 |

### The data-race components C2's run missed and scalar-clock detected

| target (component) | scalar-clock | CO (C2) | CO+chain |
|---|---|---|---|
| CCCL top-k (cccl-3, DR) | DETECTED | MISSED | DETECTED |
| Ginkgo range-minimum (ginkgo-5, DR) | DETECTED | MISSED | DETECTED |
| Kokkos rw_sum (kokkos-5, DR) | DETECTED | MISSED | DETECTED |
| RAFT select_k (raft-1, DR) | DETECTED | MISSED | MISSED |

Buggy data-race components scalar-clock DETECTED and C2 MISSED (computed): [('cccl-3', 'DR'), ('ginkgo-5', 'DR'), ('kokkos-5', 'DR'), ('raft-1', 'DR')]

### Candidate set (T21c)

| id | component | expected | scalar-clock | CO (C2) | CO+chain | CO+chain n_race / n_sc |
|---|---|---|---|---|---|---|
| autogptq-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 128/0 |
| colmap-new-1-buggy | DR | DR | DETECTED | DETECTED | NOT-SCORED | / **changed** |
| cuml-tsne-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 72/43 |
| droidslam-new-1-buggy | SC | SC | DET-as-DR | DET-as-DR | DET-as-DR | 187/0 |
| llamacpp-open-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 17/0 |
| llamacpp-open-2-buggy | DR | DR | MISSED | — | NOT-SCORED | / **changed** |
| llamacpp-open-2-fixed | - | DR | CLEAN | — | NOT-SCORED | / **changed** |
| llmc-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 8/0 |
| llmc-new-2-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 2/0 |
| llmc-new-3-buggy | DR | DR | DETECTED (family) | DETECTED (family) | DETECTED (family) | 2/0 |
| llmc-new-3-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 18/0 |
| mmcv-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 6/0 |
| opencv_contrib-new-1-buggy | DR | DR+SC | DETECTED | DETECTED | DETECTED | 64/0 |
| opencv_contrib-new-1-buggy | SC | DR+SC | DET-as-DR | DET-as-DR | DET-as-DR | 64/0 |
| openpcdet-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 9/0 |
| pcl-new-1-buggy | DR | DR+SC | DETECTED | MISSED | DETECTED | 550/0 **changed** |
| pcl-new-1-buggy | SC | DR+SC | DET-as-DR | DET-as-DR | DET-as-DR | 550/0 |
| pointnet2pt-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 3/0 |
| pytorch_cluster-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 23/0 |
| sglang-open-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 2/0 |

scalar-clock: {'DETECTED': 14, 'DETECTED-AS-DR': 3, 'MISSED': 1, 'DETECTED (family)': 1}

CO (C2): {'DETECTED': 13, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1, 'MISSED': 1}

CO+chain: {'DETECTED': 13, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1}

PCL (pcl-new-1) data-race half: scalar-clock DETECTED, C2 MISSED, CO+chain DETECTED

### CO+chain components detected through derived / rescued reports

Per attributed id: how many of the id's reports in the attribution are edge / rescued / derived (chain_src); components where the matched reports are all non-edge are listed in the attribution JSON (`c6-step3/rw/*/attrib`).

- cccl-1-buggy: 16 reports: edge 12, rescued 4, derived 0
- cccl-1-fixed: 16 reports: edge 12, rescued 4, derived 0
- cccl-2-buggy: 457 reports: edge 454, rescued 0, derived 3
- cccl-3-buggy: 65 reports: edge 44, rescued 0, derived 21
- cccl-3-fixed: 66 reports: edge 44, rescued 0, derived 22
- cccl-4-buggy: 17 reports: edge 5, rescued 2, derived 10
- cccl-4-fixed: 15 reports: edge 5, rescued 1, derived 9
- cmssw-1-buggy: 5 reports: edge 3, rescued 0, derived 2
- cmssw-1-fixed: 6 reports: edge 3, rescued 0, derived 3
- ginkgo-5-buggy: 6 reports: edge 3, rescued 3, derived 0
- hecbench-dxtc2-1-buggy: 114 reports: edge 92, rescued 10, derived 12
- hecbench-morphology-1-buggy: 52 reports: edge 8, rescued 16, derived 28
- hecbench-morphology-1-fixed: 68 reports: edge 8, rescued 8, derived 52
- hecbench-surfel-1-buggy: 27 reports: edge 14, rescued 0, derived 13
- hecbench-surfel-1-fixed: 13 reports: edge 0, rescued 0, derived 13
- kokkos-5-buggy: 69 reports: edge 19, rescued 14, derived 36
- kokkos-5-fixed: 71 reports: edge 23, rescued 10, derived 38
- kokkos-6-buggy: 94 reports: edge 32, rescued 10, derived 52
- kokkos-6-fixed: 87 reports: edge 26, rescued 10, derived 51
- lit-arrayfire-1-buggy: 10 reports: edge 6, rescued 1, derived 3
- lit-arrayfire-1-fixed: 8 reports: edge 4, rescued 1, derived 3
- lit-exllamav3-1-buggy: 176 reports: edge 84, rescued 0, derived 92
- lit-exllamav3-1-fixed: 156 reports: edge 64, rescued 0, derived 92
- lit-shoc-1-buggy: 134 reports: edge 22, rescued 10, derived 102
- lit-shoc-1-fixed: 120 reports: edge 10, rescued 10, derived 100
- llamacpp-5-buggy: 1546 reports: edge 1032, rescued 0, derived 514
- llamacpp-5-fixed: 1026 reports: edge 768, rescued 0, derived 258
- opencv-2-buggy: 2521 reports: edge 105, rescued 27, derived 2389
- opencv-2-fixed: 9 reports: edge 8, rescued 1, derived 0
- pytorch-1-buggy: 5 reports: edge 3, rescued 0, derived 2
- pytorch-1-fixed: 5 reports: edge 3, rescued 0, derived 2
- pytorch_cluster-1-buggy: 18 reports: edge 12, rescued 6, derived 0
- raft-1-buggy: 31 reports: edge 24, rescued 3, derived 4
- raft-1-fixed: 29 reports: edge 22, rescued 3, derived 4
- cuml-tsne-new-1-buggy: 115 reports: edge 80, rescued 3, derived 32
- droidslam-new-1-buggy: 187 reports: edge 21, rescued 15, derived 151
- llmc-new-2-buggy: 2 reports: edge 1, rescued 0, derived 1
- llmc-new-3-k8-buggy: 18 reports: edge 9, rescued 0, derived 9
- mmcv-fps-new-1-buggy: 6 reports: edge 2, rescued 0, derived 4
- openpcdet-fps-new-1-buggy: 9 reports: edge 3, rescued 0, derived 6
- pcl-new-1-buggy: 550 reports: edge 136, rescued 42, derived 372
- pointnet2pt-fps-new-1-buggy: 3 reports: edge 1, rescued 0, derived 2
- pytorch_cluster-new-1-buggy: 23 reports: edge 14, rescued 9, derived 0
- sglang-open-1-buggy: 2 reports: edge 1, rescued 1, derived 0


## 3. Detections against scalar-clock

Pair sets are the `report_ids` of each mode (unordered pc pairs per space, union over the reps; SC and CO+chain are separate recordings of nondeterministic programs). Reasons come from the collector-only kernel JSONs of the program (the chain-kernels jsonl of step 2 lists them): for each pair, the kernels that contain both pcs as nodes, then whether an edge or a chain of reads joins them, then (for a joined pair) the verdict step's own record for it (`sd.analyze` re-run on that kernel), then (for an unjoined pair) the gap evidence. The kernel JSON has no addresses, so "joined" means joined in the pc graph.

### Detections of CO+chain against scalar-clock (verdicts: races alone)

Programs that have a verdict in both modes. `chain only` = Race in CO+chain, Clean in scalar-clock; `sc only` = Race in scalar-clock, Clean in CO+chain, split by the paper's label (racy / race-free / unlabelled). `both` = Race in both; of those `with sc-only pairs` = programs where scalar-clock reports a pc pair the chain mode does not (pair sets compared as unordered pc pairs per space, over the union of the reps; scalar-clock and CO are separate recordings).

| suite | programs | chain only (racy / race-free / unl.) | sc only (racy / race-free / unl.) | both Race | both, with sc-only pairs | sc-only pairs | chain-only pairs in those | scalar-clock pairs in programs Race in sc | of them also in C1 | of them also in chain |
|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0 / 0 / 0 | 0 / 0 / 0 | 200 | 0 | 0 | 228 | 1294 | 1089 | 1294 |
| Indigo 1.3 (PI) | 4130 | 24 / 224 / 0 | 0 / 0 / 0 | 2420 | 331 | 3912 | 1223 | 16538 | 8970 | 12626 |
| ECL (P3) | 60 | 0 / 0 / 0 | 0 / 0 / 0 | 16 | 0 | 0 | 28 | 16 | 16 | 16 |
| ScoR apps (P4) | 28 | 0 / 6 / 0 | 0 / 0 / 0 | 16 | 9 | 13 | 53 | 77 | 64 | 64 |
| ScoR litmus (P5) | 33 | 0 / 0 / 0 | 1 / 0 / 0 | 2 | 1 | 1 | 0 | 5 | 3 | 3 |
| cuHadron (P6) | 34 | 0 / 0 / 0 | 1 / 0 / 0 | 7 | 3 | 71 | 80 | 94 | 22 | 22 |
| HeCBench other 14 (P7) | 13 | 0 / 0 / 3 | 0 / 0 / 0 | 4 | 0 | 0 | 2 | 65 | 64 | 65 |
| HeCBench SC 10 (P9) | 9 | 0 / 2 / 0 | 0 / 0 / 0 | 3 | 1 | 4 | 73 | 49 | 35 | 45 |
| **all** | 4707 | 24 / 232 / 3 | 2 / 0 / 0 | 2668 | 345 | 4001 | 1687 | 18138 | 10263 | 14135 |

Pair sets cut by the CSV (fewer report_ids than reports_dedup) in 0 of the Race-in-both programs.

### Why scalar-clock's pairs are missing: classification in the collector-only kernel JSONs

For each pc pair that scalar-clock reports and the chain mode does not, over all kernel JSONs of the program's CO recording that contain both pcs as nodes. The classes are tried in this order and the first that applies in any kernel is used:

1. pcs not both recorded
2. edge/chain cross-thread, judged not reported
3. edge/chain only thread-local
4. only via a non-read hop (intervening write/atomic)
5. not reachable: dropped-word deficit at a or c
6. not reachable: deficit at another pc of the kernel
7. not reachable: shared-pool exhaustion not excluded (grid > 4608 CTAs)
8. not reachable: no gap evidence

'Judged not reported' = the verdict step has a recorded transition (edge, or a chain of reads) joining the pair across threads, and its own record for the pair is not a Race (the verdict is given in the csv: ORDERED by a certificate, benign, read-read, etc.). 'deficit' = static check (b): expected shadow words from the node's lane and address counts exceed the words on the edges (c6_static_out.json, per kernel name and pc, estimate). 'pool' = a shared-space pair in a kernel with more than 4,608 CTAs: `pool_miss_count` is not emitted, so exhaustion cannot be confirmed, only not excluded.


**program missed**: pairs per suite and class

| suite | programs | pairs | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|---|
| ScoR litmus (P5) | 1 | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| **all** | 2 | 2 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

**pair missed, program Race**: pairs per suite and class

| suite | programs | pairs | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|---|
| Indigo 1.3 (PI) | 331 | 3912 | 227 | 0 | 35 | 3558 | 74 | 0 | 0 | 18 |
| ScoR apps (P4) | 9 | 13 | 0 | 1 | 4 | 8 | 0 | 0 | 0 | 0 |
| ScoR litmus (P5) | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 3 | 71 | 0 | 1 | 18 | 52 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 1 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| **all** | 345 | 4001 | 227 | 2 | 61 | 3619 | 74 | 0 | 0 | 18 |

Programs Race in both with sc-only pairs: 345; classified: 345 (cap 700, seeded sample).

**Programs Race in scalar-clock and Clean in CO+chain, one by one**

| suite | id | label | sc pairs | classes of the sc pairs (counts) | oracle (PI) |
|---|---|---|---|---|---|
| P5 | `P5-race_interblock_none-lock_rtraw` | racy | 1 | edge/chain cross-thread, judged not reported x1 |  |
| P6 | `P6-memcpy-shared_readwrite_race-racy` | racy | 1 | edge/chain only thread-local x1 |  |

Static check (b) deficit programs among Indigo 1.3 program-inputs here: 612; among the programs Race in scalar-clock and Clean in CO+chain: 0 of 2.

### The production races (CCCL top-k, Ginkgo range-minimum, Kokkos rw_sum, RAFT select_k) and PCL: scalar-clock's matched pairs in the CO recording

| case | id | SC reports matching the oracle's pair(s) | in the chain run's reports | by source (edge / rescued / derived) | classes of the others in the CO recording |
|---|---|---|---|---|---|
| CCCL top-k | cccl-3-buggy | 8 | 8 | 0 / 0 / 8 | - |
| Ginkgo range-minimum | ginkgo-5-buggy | 3 | 3 | 0 / 3 / 0 | - |
| Kokkos rw_sum | kokkos-5-buggy | 3 | 3 | 0 / 3 / 0 | - |
| RAFT select_k | raft-1-buggy | 3 | 0 | 0 / 0 / 0 | only via a non-read hop (intervening write/atomic) [bound grid] x3 |
| PCL (data-race half) | pcl-new-1-buggy | 102 | 44 | 15 / 1 / 28 | only via a non-read hop (intervening write/atomic) [bound warp] x58 |


### 3.1 Classes per program

| suite | class | pairs | programs |
|---|---|---|---|
| P4 | edge/chain cross-thread, judged not reported | 1 | 1 |
| P4 | edge/chain only thread-local | 4 | 4 |
| P4 | only via a non-read hop (intervening write/atomic) | 8 | 4 |
| P5 | edge/chain cross-thread, judged not reported | 1 | 1 |
| P5 | only via a non-read hop (intervening write/atomic) | 1 | 1 |
| P6 | edge/chain cross-thread, judged not reported | 1 | 1 |
| P6 | edge/chain only thread-local | 19 | 3 |
| P6 | only via a non-read hop (intervening write/atomic) | 52 | 2 |
| P9 | edge/chain only thread-local | 4 | 1 |
| PI | edge/chain only thread-local | 35 | 23 |
| PI | not reachable: dropped-word deficit at a or c | 74 | 34 |
| PI | not reachable: no gap evidence | 18 | 9 |
| PI | only via a non-read hop (intervening write/atomic) | 3558 | 303 |
| PI | pcs not both recorded | 227 | 15 |

- all suites: edge/chain cross-thread, judged not reported: 3 pairs in 3 programs
- all suites: edge/chain only thread-local: 62 pairs in 31 programs
- all suites: not reachable: dropped-word deficit at a or c: 74 pairs in 34 programs
- all suites: not reachable: no gap evidence: 18 pairs in 9 programs
- all suites: only via a non-read hop (intervening write/atomic): 3619 pairs in 310 programs
- all suites: pcs not both recorded: 227 pairs in 15 programs

Dispositions of the 'judged not reported' pairs: {'judged ORDERED(,edge)': 1, 'skipped rmw_pair_morally_strong': 1, 'judged RACE(,edge)': 1}

not reachable: dropped-word deficit at a or c: PI-conditional_edge_neighbors_boundsBug-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_atomicBug_break-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_break-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_break-counterDAG_5n_5e, PI-conditional_edge_neighbors_boundsBug_cond-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_cond-DAG_200n_400e, PI-conditional_edge_neighbors_boundsBug_cond-power_law_200n_1000e, PI-conditional_edge_neighbors_boundsBug_cond_atomicBug-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_cond_guardBug-DAG_100n_100e, PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-DAG_10, PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-DAG_20, PI-conditional_edge_neighbors_boundsBug_guardBug-DAG_100n_100e

not reachable: no gap evidence: PI-conditional_edge_neighbors_persistent_reverse_cond_guardBug_atomicB, PI-conditional_edge_neighbors_reverse_guardBug_atomicBug-DAG_200n_400e, PI-populate_worklist_neighbors_atomicBug-DAG_100n_200e, PI-populate_worklist_neighbors_persistent_atomicBug-DAG_100n_200e, PI-populate_worklist_neighbors_persistent_atomicBug-DAG_200n_400e, PI-populate_worklist_neighbors_persistent_reverse_atomicBug-DAG_200n_4, PI-populate_worklist_neighbors_persistent_reverse_atomicBug-counterDAG, PI-populate_worklist_neighbors_persistent_reverse_atomicBug-power_law_, PI-populate_worklist_neighbors_warp_persistent_atomicBug-power_law_200


### 3.2 The two programs SC finds and CO+chain does not

- `P5-race_interblock_none-lock_rtraw` (litmus, racy in the manifest; X1b's footnote counts it a false report): an edge joins the pair (`global:0x170-0x2f0:WAW`) across blocks, and the verdict step's record for it is ORDERED by a certificate (the lock the pair sits behind). Not a collector gap; SC's event stream reports it as Race, CO+chain as Strong only.
- `P6-memcpy-shared_readwrite_race-racy` (`shared:0x70-0x90:RAW`): the edge exists only at thread-local distance and no chain gives it a cross-thread bound. Neither a dropped-word deficit (static check (b), 0 of the 2 programs) nor a shared pool of more than 4,608 CTAs applies; pc 0 does not occur (check (a)). The transition that makes it a race (another thread's access in between) is not in the recording: category "something else" (an intervening access the single-last-accessor shadow overwrote and a non-read hop the closure does not cross, or a schedule difference between the SC and CO recordings; the JSON cannot tell which).

### 3.3 Which gap, for the pairs in programs that are Race in both

Classes are tried in the order of the list above; the counts are pairs. **First-lane allocation lookup / allocation-end words**: the evidence is a dropped-word deficit at a or c (static check (b)): 74 pairs in 34 programs, all of them Indigo 1.3 `boundsBug` variants (programs that index out of the allocation on purpose); another 0 pairs have a deficit only at another pc of their kernel. **Shared-pool exhaustion**: 0 pairs have a shared-space pair in a kernel with more than 4,608 CTAs; `pool_miss_count` is not emitted, so exhaustion cannot be confirmed in any kernel, only excluded where the grid is small. **pc-0 previous accessor**: 0 (no memory instruction at offset 0 in the 1,327 distinct CFGs). **No gap evidence** (unreachable and nothing found): 18 pairs in 9 programs, all `atomicBug`/`boundsBug`/`guardBug` Indigo 1.3 variants. **Not a gap**: 3,619 pairs in 310 programs are reachable in the pc graph only through a hop that is not a read (an intervening write or atomic: the shadow keeps one last accessor, and the closure crosses reads only), 62 pairs in 31 programs are joined only at thread-local distance, 3 pairs have an edge or read chain whose verdict-step record is not a Race, and 227 pairs in 15 programs have a pc that is not a node of the CO recording (the SC run executed code the CO run did not).

## 4. False reports

Race-free-labelled programs that are Race: 251 in CO+chain, 248 in CO, 19 in scalar-clock (Table 3 counts the program-inputs of Indigo 1.3 per code, so its 56 of 468 is smaller). The closure adds three: `P4-uts-norace-small` and `-large` (two `chain_rescue` records each, chain depth at most 8 and 18; no derived pair) and `P9-knn-cuda` (four derived pairs, all in shared memory). Split of the reports on **race-free-labelled programs** by how the verdict step found them: against C1, **25 derived, 12 rescued, 0 other** (every report CO+chain adds to C1 is the closure's, by the parity rule); against scalar-clock, 25 derived, 12 rescued and **281 other** (ordinary edge reports C1 already has and SC's barrier clock orders: 224 Indigo 1.3, 30 ScoR applications, 20 ECL, 7 HeCBench). The per-suite and per-label split is in the table below; on racy-labelled programs the same columns are the bulk of the closure's additions (Indigo 1.3 racy: 1,764 derived and 204 rescued against C1), none of them a false report by label.

Sample of 20: the derived-only pairs of the programs that turned Race are four, all `P9-knn-cuda` (the `uts-norace` flips are rescued, not derived), so the sample is those four plus 16 from the race-free-labelled programs that were already Race in CO (one pair per program first). What the kernel JSON can say about a derived pair a -> h -> c: it has no addresses, so "the hops can share an address" is provable only where the counts force it. The test is a pigeonhole on the inner pc h: N(h) words entered the shadow at h; n(a,h) of its accesses had a as predecessor and n(h,c) had c as successor; if n(a,h) + n(h,c) > N(h) some access of h has both, so a, h, c are consecutive at one address. It holds for the pairs marked "all inner nodes proven" in the table below (10 of 20); for the other 10 it fails to hold (the sets could be disjoint) and the JSON cannot show that they are not, so they are **undetermined**, not "different addresses". All 20 have one inner node (k = 1), 19 are in shared memory, and no pair has an edge between its ends in either direction in the kernel (by construction of "derived"). Reading notes: all 20 hops are block-level, and a = c (the same pc at both ends) in 18 of the 20, so the derived pair is a statement against itself through a reader: a -> h -> a. Whether the barrier that orders it in the program is the reason it is a false report cannot be read from the JSON (no barrier information per address).

### Reports of CO+chain that C1 and scalar-clock do not have, split by how the verdict step found them

Unit: a deduped pc pair of a program that is Race in CO+chain (union of the reps in the CSV for C1 and scalar-clock; the raw records of the chain run's confirm JSON for the source). derived = `chain_src` chain (a pair no edge joins, only a chain of reads), rescued = chain_rescue (an edge whose own distance is thread-local, judged at its chain's bound), other = an ordinary edge or event record.

| suite | label | reports in CO+chain | not in C1: derived | rescued | other | not in scalar-clock: derived | rescued | other |
|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | racy | 1522 | 328 | 46 | 0 | 153 | 16 | 59 |
| Indigo 1.3 (PI) | racy | 8680 | 1764 | 204 | 0 | 149 | 14 | 680 |
| Indigo 1.3 (PI) | race-free | 240 | 16 | 0 | 0 | 16 | 0 | 224 |
| Indigo 1.3 (PI) | unlabelled | 5193 | 2051 | 181 | 0 | 279 | 102 | 23 |
| ECL (P3) | race-free | 44 | 0 | 8 | 0 | 0 | 8 | 20 |
| ScoR apps (P4) | racy | 111 | 25 | 4 | 0 | 25 | 4 | 18 |
| ScoR apps (P4) | race-free | 37 | 3 | 4 | 0 | 3 | 4 | 30 |
| ScoR litmus (P5) | racy | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | racy | 93 | 79 | 0 | 0 | 79 | 0 | 1 |
| cuHadron (P6) | race-free | 9 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | unlabelled | 72 | 5 | 1 | 0 | 5 | 0 | 2 |
| HeCBench SC 10 (P9) | racy | 118 | 67 | 6 | 0 | 63 | 0 | 10 |
| HeCBench SC 10 (P9) | race-free | 13 | 6 | 0 | 0 | 6 | 0 | 7 |

On race-free-labelled programs (all suites): reports not in C1 25 derived / 12 rescued / 0 other; not in scalar-clock 25 derived / 12 rescued / 281 other.
Race-free-labelled programs Race in CO+chain: 251; in C1: 248; in scalar-clock: 19.
Programs Race in CO+chain without a confirm JSON: {}

### Sample of 20 derived-only pairs on race-free programs: can the hops of the chain share an address?

Pool A = derived pairs (not in C1's reports) of race-free-labelled programs whose verdict changed Clean -> Race (norace programs); pool B = such pairs of race-free-labelled programs that were already Race in C1. Pool sizes: A 4, B 21. Sample: up to 10 from A, the rest from B, seeded random (20261102), one pair per program first. The kernel JSON has no addresses, only words per (pc, ancient pc) edge. For an inner node h with in-hop words n(a,h), out-hop words n(h,c) and N(h) the words that entered the shadow at h (all incoming edge words except the same-instruction repeat lanes), the accesses of h that follow a and the accesses of h that precede c are subsets of the N(h) accesses of h; if n(a,h) + n(h,c) > N(h) they share at least n(a,h) + n(h,c) - N(h) accesses of h, so a, h, c are consecutive at one address: **proven**. Otherwise the JSON cannot say: **undetermined** (the sets may or may not coincide). For a chain with two or more inner nodes the test is per inner node.

| # | program | label | space | a -> ... -> c | k | hop levels | hop words (non-repeat) | N(h) | proven same address (inner nodes) | direct edge a-c / c-a in the kernel |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `P9-knn-cuda` | race-free | shared | 0x460 -> 0x4c0 -> 0x460 | 1 | block/block | 5242880/4194304 | 5242880 | all inner nodes proven | False / False |
| 2 | `P9-knn-cuda` | race-free | shared | 0x480 -> 0x4d0 -> 0x480 | 1 | block/block | 5242880/4194304 | 41943040 | undetermined | False / False |
| 3 | `P9-knn-cuda` | race-free | shared | 0x380 -> 0x550 -> 0x460 | 1 | block/block | 1048576/3145728 | 5242880 | undetermined | False / False |
| 4 | `P9-knn-cuda` | race-free | shared | 0x380 -> 0x550 -> 0x380 | 1 | block/block | 1048576/1048576 | 5242880 | undetermined | False / False |
| 5 | `PI-pull_node_neighbors_block_persistent_cond-DAG_100n_100e` | race-free | shared | 0x250 -> 0x2e0 -> 0x250 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 6 | `PI-pull_node_neighbors_block_shfl_persistent-DAG_100n_100e` | race-free | shared | 0x2e0 -> 0x310 -> 0x2e0 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 7 | `PI-pull_node_neighbors_block_shfl_persistent_reverse-DAG_100n_100e` | race-free | shared | 0x2f0 -> 0x320 -> 0x2f0 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 8 | `PI-conditional_edge_neighbors_block_shfl_persistent-DAG_100n_100e` | race-free | shared | 0x2f0 -> 0x320 -> 0x2f0 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 9 | `P4-graph-coloring-norace-large` | race-free | global | 0x550 -> 0x580 -> 0x550 | 1 | block/block | 60/45 | 480 | undetermined | False / False |
| 10 | `P9-crs-cuda` | race-free | shared | 0x500 -> 0x570 -> 0x970 | 1 | block/block | 52430/52430 | 58722 | all inner nodes proven | False / False |
| 11 | `PI-pull_node_neighbors_block_persistent_reverse-DAG_100n_100e` | race-free | shared | 0x210 -> 0x2a0 -> 0x210 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 12 | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-DAG_100n_100e` | race-free | shared | 0x300 -> 0x330 -> 0x300 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 13 | `PI-conditional_edge_neighbors_block_persistent_reverse-DAG_100n_100e` | race-free | shared | 0x220 -> 0x2c0 -> 0x220 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 14 | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-DAG_100n_100e` | race-free | shared | 0x250 -> 0x2e0 -> 0x250 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 15 | `PI-conditional_edge_neighbors_block_persistent_cond-DAG_100n_100e` | race-free | shared | 0x240 -> 0x2d0 -> 0x240 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 16 | `PI-pull_node_neighbors_block_persistent_reverse_cond-DAG_100n_100e` | race-free | shared | 0x260 -> 0x2f0 -> 0x260 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 17 | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-DAG_100n_100e` | race-free | shared | 0x320 -> 0x350 -> 0x320 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 18 | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-DAG_100n_100e` | race-free | shared | 0x340 -> 0x370 -> 0x340 | 1 | block/block | 800/768 | 3200 | undetermined | False / False |
| 19 | `PI-pull_node_neighbors_block_persistent-DAG_100n_100e` | race-free | shared | 0x200 -> 0x290 -> 0x200 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |
| 20 | `PI-conditional_edge_neighbors_block_persistent-DAG_100n_100e` | race-free | shared | 0x210 -> 0x2b0 -> 0x210 | 1 | block/block | 12800/24480 | 25500 | all inner nodes proven | False / False |

Of the 20 sampled pairs: 10 all inner nodes proven; 10 undetermined



## 5. Cost

Rule and script of `eval/CAP_84600.md` section 3 (geometric means; run only = tool wall / native wall over the finished programs, verdict step = analysis_s / native and end-to-end = (wall + analysis_s) / native over the finished programs that carry analysis_s; "All" = P1, PI, P3, P4, P5, P6 = the 4,685-program set). `c6_cost.py` reproduces CAP's three rows exactly (check lines below: VC 7.320 / 2.454 / 9.966, SC 7.015 / 2.173 / 9.339, CO 5.564 / 2.098 / 7.773, n = 4,685 each), then applies the rule to CO+chain.

- **(a) Run alone.** CO+chain re-uses C1's recordings, so its run wall is C1's: 0 of 4,709 rows differ in `wall_s`. Over the 4,685 programs 5.564; over all 4,709 finished programs **5.652**, which is the paper's "5.7x over all programs" (make_tables' `All suites` row, n = 4,709, 5.7). The paper's 4,685-set figures (7.320, 7.015, 5.564) differ from its 7.5 / 7.1 / 5.7 only because HeCBench is in the latter (n = 4,705 / 4,707 / 4,709: 7.488 / 7.142 / 5.652).
- **(b), (c) Verdict step and end-to-end** with the closure: measured as step 2 ran them (EPYC nodes) 1.860 / 7.550 on the 4,685-set; **estimated on A5's node class 2.242 / 7.923**, bounds 2.098 / 7.773 (closure free) and 2.555 / 8.251 (every program at its group's largest measured ratio). Against C1 the step grows by 7 % (estimate), against SC (2.173 / 9.339) it is 3 % above in the step and 15 % below end-to-end; against VC (2.454 / 9.966) 9 % below and 20 % below.
- **Why step 2's analysis_s cannot be used as it stands.** It ran on c5 (EPYC 9115, 2,360 programs) and c45 (EPYC 7302P, 2,349), not on A5's class (the C1 reference analysis ran on c36 / c79; their CPU was not measured, both were allocated to other jobs, and the re-time was done on c26, the Xeon Silver 4110 that the brief names as A5's class). Over the same programs the ratio chain(step 2) / C1 reference is 0.708 on c5 and 1.081 on c45: the host effect (about 1.20 between c26 and c25 on the re-time: 66.81 s against 55.65 s for the same 47 recordings with the closure off) is larger than the closure's own cost.
- **Correction used.** The re-time ran 47 programs (8 P1, 4 P3, 8 P4, 4 P5, 4 P6, 12 PI, 7 HeCBench) with the closure off and on, twice in a row, on c26 and on c25. On c26, pass 2, sum of analysis_s: VC 135.40 s, SC 67.03 s, CO (closure off) 66.81 s, CO+chain 69.72 s: the closure costs **+4.4 %** (c25: 55.65 s -> 57.41 s, +3.2 %), of which chain_s is 0.218 s (0.3 %); the rest is judging the derived and rescued pairs. Per group the c26 factor (sum on / sum off, pass 2) is P1 1.089, P3 1.044, P4 1.046, P5 1.002, P6 1.095, PI 1.068, HeCBench 1.014; the largest per-program ratio is 1.534 (P4). The estimate multiplies the A5 reference analysis_s of each program by its group's factor; the upper bound by the group's largest per-program ratio (programs with at least 0.2 s); the lower bound by 1. The sample is 47 of 4,709 programs: the factors are a measurement on that sample, not on the corpus.
- **Per suite, median and max of analysis_s and the closure's share** (step 2 values, EPYC; the C1 reference columns are A5's): see the generated table (HeCBench separate). Over all programs the closure is 0.16 % of the verdict step (3.48 s of 2,119.4 s), 0.03 % without HeCBench, 5.56 % on HeCBench (P7 6.6 %, P9 4.7 %), largest single share `P7-stencil1d-cuda` 0.631 s of 0.663 s. Largest step: 9.072 s (`P4-reduction-norace-large`, chain_s 0.000).

### Re-time on A5's node class (c26, Xeon Silver 4110) and on c25 (EPYC 7302P): closure off vs on, same 47 recordings

analysis_s of rep 1, mode collector-only (one value per program), sum over the sample; factor = sum(on) / sum(off); per-program max = largest on/off over the programs of the group with off >= 0.2 s.

| host | pass | group | n | sum off (s) | sum on (s) | factor | per-program max | sum chain_s (s) |
|---|---|---|---|---|---|---|---|---|
| c26 | 1 | P1 | 8 | 8.01 | 7.57 | 0.9446 | 1.283 | 0.018 |
| c26 | 1 | P3 | 4 | 3.81 | 5.41 | 1.4196 | 2.237 | 0.007 |
| c26 | 1 | P4 | 8 | 28.17 | 28.30 | 1.0047 | 1.182 | 0.055 |
| c26 | 1 | P5 | 4 | 1.84 | 1.92 | 1.0425 | 1.267 | 0.000 |
| c26 | 1 | P6 | 4 | 1.54 | 1.66 | 1.0731 | 1.092 | 0.002 |
| c26 | 1 | PI | 12 | 5.76 | 6.31 | 1.0955 | 1.398 | 0.000 |
| c26 | 1 | HeCBench | 7 | 18.66 | 18.83 | 1.0093 | 1.101 | 0.133 |
| c26 | 1 | all | 47 | 67.78 | 69.98 | 1.0324 | 2.237 | 0.215 |
| c26 | 2 | P1 | 8 | 7.05 | 7.68 | 1.0891 | 1.254 | 0.018 |
| c26 | 2 | P3 | 4 | 3.82 | 3.98 | 1.0438 | 1.193 | 0.006 |
| c26 | 2 | P4 | 8 | 27.93 | 29.22 | 1.0462 | 1.534 | 0.055 |
| c26 | 2 | P5 | 4 | 2.05 | 2.06 | 1.0020 | 1.196 | 0.000 |
| c26 | 2 | P6 | 4 | 1.75 | 1.92 | 1.0949 | 1.180 | 0.002 |
| c26 | 2 | PI | 12 | 5.82 | 6.21 | 1.0675 | 1.213 | 0.000 |
| c26 | 2 | HeCBench | 7 | 18.40 | 18.66 | 1.0142 | 1.061 | 0.137 |
| c26 | 2 | all | 47 | 66.81 | 69.72 | 1.0436 | 1.534 | 0.218 |
| c25 | 1 | P1 | 8 | 5.85 | 6.12 | 1.0458 | 1.089 | 0.010 |
| c25 | 1 | P3 | 4 | 3.09 | 3.29 | 1.0643 | 1.169 | 0.004 |
| c25 | 1 | P4 | 8 | 22.51 | 22.79 | 1.0125 | 1.109 | 0.038 |
| c25 | 1 | P5 | 4 | 1.50 | 1.58 | 1.0581 | 1.128 | 0.000 |
| c25 | 1 | P6 | 4 | 1.37 | 1.40 | 1.0182 | 1.053 | 0.002 |
| c25 | 1 | PI | 12 | 5.01 | 5.46 | 1.0894 | 1.517 | 0.000 |
| c25 | 1 | HeCBench | 7 | 14.84 | 15.59 | 1.0510 | 1.401 | 0.088 |
| c25 | 1 | all | 47 | 54.17 | 56.23 | 1.0381 | 1.517 | 0.142 |
| c25 | 2 | P1 | 8 | 5.98 | 6.87 | 1.1491 | 1.915 | 0.011 |
| c25 | 2 | P3 | 4 | 3.30 | 3.39 | 1.0276 | 1.091 | 0.004 |
| c25 | 2 | P4 | 8 | 22.96 | 23.50 | 1.0233 | 1.367 | 0.038 |
| c25 | 2 | P5 | 4 | 1.61 | 1.65 | 1.0229 | 1.168 | 0.000 |
| c25 | 2 | P6 | 4 | 1.39 | 1.54 | 1.1050 | 1.194 | 0.002 |
| c25 | 2 | PI | 12 | 5.24 | 5.17 | 0.9868 | 1.110 | 0.000 |
| c25 | 2 | HeCBench | 7 | 15.17 | 15.29 | 1.0082 | 1.106 | 0.088 |
| c25 | 2 | all | 47 | 55.65 | 57.41 | 1.0315 | 1.915 | 0.143 |

c26, pass 2, sum of analysis_s over the 47 programs: vc 135.40 s, sc 67.03 s, co-off 66.81 s, co-on 69.72 s

c25, pass 2, sum of analysis_s over the 47 programs: vc 108.40 s, sc 54.48 s, co-off 55.65 s, co-on 57.41 s

Host effect (co-off, pass 2, all 47): c26 / c25 = 1.201

### Cost by the rule of CAP_84600.md section 3: geometric means (n programs)

| suite | mode | run only (n) | verdict step (n) | end-to-end (n) | run only, same programs as end-to-end |
|---|---|---|---|---|---|
| Indigo3 | vector-clock | 10.421 (400) | 3.607 (400) | 14.662 (400) | 10.421 (400) |
| Indigo3 | scalar-clock | 8.730 (400) | 3.384 (400) | 12.409 (400) | 8.730 (400) |
| Indigo3 | CO (C1) | 6.470 (400) | 3.296 (400) | 10.005 (400) | 6.470 (400) |
| Indigo3 | CO+chain, step-2 analysis_s as measured (EPYC) | 6.470 (400) | 2.781 (400) | 9.489 (400) | 6.470 (400) |
| Indigo3 | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 6.470 (400) | 3.590 (400) | 10.313 (400) | 6.470 (400) |
| Indigo3 | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 6.470 (400) | 4.134 (400) | 10.880 (400) | 6.470 (400) |
| Indigo3 | CO+chain, lower bound (= C1 analysis_s) | 6.470 (400) | 3.296 (400) | 10.005 (400) | 6.470 (400) |
| Indigo 1.3 | vector-clock | 6.932 (4130) | 2.349 (4130) | 9.405 (4130) | 6.932 (4130) |
| Indigo 1.3 | scalar-clock | 6.805 (4130) | 2.075 (4130) | 8.984 (4130) | 6.805 (4130) |
| Indigo 1.3 | CO (C1) | 5.458 (4130) | 1.999 (4130) | 7.521 (4130) | 5.458 (4130) |
| Indigo 1.3 | CO+chain, step-2 analysis_s as measured (EPYC) | 5.458 (4130) | 1.783 (4130) | 7.327 (4130) | 5.458 (4130) |
| Indigo 1.3 | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 5.458 (4130) | 2.134 (4130) | 7.660 (4130) | 5.458 (4130) |
| Indigo 1.3 | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 5.458 (4130) | 2.426 (4130) | 7.957 (4130) | 5.458 (4130) |
| Indigo 1.3 | CO+chain, lower bound (= C1 analysis_s) | 5.458 (4130) | 1.999 (4130) | 7.521 (4130) | 5.458 (4130) |
| ECL | vector-clock | 10.149 (60) | 3.477 (60) | 13.897 (60) | 10.149 (60) |
| ECL | scalar-clock | 8.820 (60) | 3.274 (60) | 12.351 (60) | 8.820 (60) |
| ECL | CO (C1) | 6.006 (60) | 3.147 (60) | 9.348 (60) | 6.006 (60) |
| ECL | CO+chain, step-2 analysis_s as measured (EPYC) | 6.006 (60) | 2.704 (60) | 8.952 (60) | 6.006 (60) |
| ECL | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 6.006 (60) | 3.285 (60) | 9.492 (60) | 6.006 (60) |
| ECL | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 6.006 (60) | 3.754 (60) | 9.979 (60) | 6.006 (60) |
| ECL | CO+chain, lower bound (= C1 analysis_s) | 6.006 (60) | 3.147 (60) | 9.348 (60) | 6.006 (60) |
| ScoR apps | vector-clock | 28.849 (28) | 15.380 (28) | 55.364 (28) | 28.849 (28) |
| ScoR apps | scalar-clock | 9.360 (28) | 8.079 (28) | 20.115 (28) | 9.360 (28) |
| ScoR apps | CO (C1) | 6.834 (28) | 7.941 (28) | 17.293 (28) | 6.834 (28) |
| ScoR apps | CO+chain, step-2 analysis_s as measured (EPYC) | 6.834 (28) | 6.327 (28) | 15.255 (28) | 6.834 (28) |
| ScoR apps | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 6.834 (28) | 8.308 (28) | 17.703 (28) | 6.834 (28) |
| ScoR apps | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 6.834 (28) | 12.179 (28) | 21.942 (28) | 6.834 (28) |
| ScoR apps | CO+chain, lower bound (= C1 analysis_s) | 6.834 (28) | 7.941 (28) | 17.293 (28) | 6.834 (28) |
| ScoR litmus | vector-clock | 8.845 (33) | 1.909 (33) | 10.839 (33) | 8.845 (33) |
| ScoR litmus | scalar-clock | 7.361 (33) | 1.639 (33) | 9.060 (33) | 7.361 (33) |
| ScoR litmus | CO (C1) | 5.637 (33) | 1.702 (33) | 7.406 (33) | 5.637 (33) |
| ScoR litmus | CO+chain, step-2 analysis_s as measured (EPYC) | 5.637 (33) | 1.560 (33) | 7.276 (33) | 5.637 (33) |
| ScoR litmus | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 5.637 (33) | 1.705 (33) | 7.409 (33) | 5.637 (33) |
| ScoR litmus | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 5.637 (33) | 2.035 (33) | 7.748 (33) | 5.637 (33) |
| ScoR litmus | CO+chain, lower bound (= C1 analysis_s) | 5.637 (33) | 1.702 (33) | 7.406 (33) | 5.637 (33) |
| cuHadron | vector-clock | 12.993 (34) | 0.819 (34) | 15.096 (34) | 12.993 (34) |
| cuHadron | scalar-clock | 10.752 (34) | 0.709 (34) | 12.180 (34) | 10.752 (34) |
| cuHadron | CO (C1) | 7.124 (34) | 0.722 (34) | 8.530 (34) | 7.124 (34) |
| cuHadron | CO+chain, step-2 analysis_s as measured (EPYC) | 7.124 (34) | 0.646 (34) | 8.419 (34) | 7.124 (34) |
| cuHadron | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 7.124 (34) | 0.790 (34) | 8.658 (34) | 7.124 (34) |
| cuHadron | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 7.124 (34) | 0.852 (34) | 8.772 (34) | 7.124 (34) |
| cuHadron | CO+chain, lower bound (= C1 analysis_s) | 7.124 (34) | 0.722 (34) | 8.530 (34) | 7.124 (34) |
| HeCBench other 14 | vector-clock | 1411.497 (12) | 0.663 (12) | 1421.126 (12) | 1411.497 (12) |
| HeCBench other 14 | scalar-clock | 246.314 (13) | 0.752 (13) | 249.588 (13) | 246.314 (13) |
| HeCBench other 14 | CO (C1) | 99.881 (14) | 0.626 (14) | 103.355 (14) | 99.881 (14) |
| HeCBench other 14 | CO+chain, step-2 analysis_s as measured (EPYC) | 99.881 (14) | 0.519 (14) | 103.406 (14) | 99.881 (14) |
| HeCBench other 14 | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 99.881 (14) | 0.635 (14) | 103.402 (14) | 99.881 (14) |
| HeCBench other 14 | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 99.881 (14) | 0.664 (14) | 103.559 (14) | 99.881 (14) |
| HeCBench other 14 | CO+chain, lower bound (= C1 analysis_s) | 99.881 (14) | 0.626 (14) | 103.355 (14) | 99.881 (14) |
| HeCBench SC 10 | vector-clock | 1694.363 (8) | 3.405 (8) | 1708.741 (8) | 1694.363 (8) |
| HeCBench SC 10 | scalar-clock | 512.634 (9) | 2.609 (9) | 520.908 (9) | 512.634 (9) |
| HeCBench SC 10 | CO (C1) | 150.442 (10) | 2.439 (10) | 159.563 (10) | 150.442 (10) |
| HeCBench SC 10 | CO+chain, step-2 analysis_s as measured (EPYC) | 150.442 (10) | 1.862 (10) | 156.697 (10) | 150.442 (10) |
| HeCBench SC 10 | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 150.442 (10) | 2.473 (10) | 159.683 (10) | 150.442 (10) |
| HeCBench SC 10 | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 150.442 (10) | 2.588 (10) | 160.081 (10) | 150.442 (10) |
| HeCBench SC 10 | CO+chain, lower bound (= C1 analysis_s) | 150.442 (10) | 2.439 (10) | 159.563 (10) | 150.442 (10) |
| HeCBench (P7+P9) | vector-clock | 1518.485 (20) | 1.275 (20) | 1529.854 (20) | 1518.485 (20) |
| HeCBench (P7+P9) | scalar-clock | 332.438 (22) | 1.251 (22) | 337.243 (22) | 332.438 (22) |
| HeCBench (P7+P9) | CO (C1) | 118.468 (24) | 1.103 (24) | 123.855 (24) | 118.468 (24) |
| HeCBench (P7+P9) | CO+chain, step-2 analysis_s as measured (EPYC) | 118.468 (24) | 0.884 (24) | 122.959 (24) | 118.468 (24) |
| HeCBench (P7+P9) | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 118.468 (24) | 1.119 (24) | 123.927 (24) | 118.468 (24) |
| HeCBench (P7+P9) | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 118.468 (24) | 1.171 (24) | 124.166 (24) | 118.468 (24) |
| HeCBench (P7+P9) | CO+chain, lower bound (= C1 analysis_s) | 118.468 (24) | 1.103 (24) | 123.855 (24) | 118.468 (24) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | vector-clock | 7.320 (4685) | 2.454 (4685) | 9.966 (4685) | 7.320 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | scalar-clock | 7.015 (4685) | 2.173 (4685) | 9.339 (4685) | 7.015 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO (C1) | 5.564 (4685) | 2.098 (4685) | 7.773 (4685) | 5.564 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO+chain, step-2 analysis_s as measured (EPYC) | 5.564 (4685) | 1.860 (4685) | 7.550 (4685) | 5.564 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 5.564 (4685) | 2.242 (4685) | 7.923 (4685) | 5.564 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 5.564 (4685) | 2.555 (4685) | 8.251 (4685) | 5.564 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | CO+chain, lower bound (= C1 analysis_s) | 5.564 (4685) | 2.098 (4685) | 7.773 (4685) | 5.564 (4685) |
| All incl. HeCBench (unrestricted) | vector-clock | 7.488 (4705) | 2.447 (4705) | 10.182 (4705) | 7.488 (4705) |
| All incl. HeCBench (unrestricted) | scalar-clock | 7.142 (4707) | 2.168 (4707) | 9.497 (4707) | 7.142 (4707) |
| All incl. HeCBench (unrestricted) | CO (C1) | 5.652 (4709) | 2.091 (4709) | 7.884 (4709) | 5.652 (4709) |
| All incl. HeCBench (unrestricted) | CO+chain, step-2 analysis_s as measured (EPYC) | 5.652 (4709) | 1.853 (4709) | 7.658 (4709) | 5.652 (4709) |
| All incl. HeCBench (unrestricted) | CO+chain, A5-class estimate (C1 analysis_s x c26 factor) | 5.652 (4709) | 2.234 (4709) | 8.035 (4709) | 5.652 (4709) |
| All incl. HeCBench (unrestricted) | CO+chain, A5-class upper bound (x largest per-program c26 ratio of the group) | 5.652 (4709) | 2.545 (4709) | 8.365 (4709) | 5.652 (4709) |
| All incl. HeCBench (unrestricted) | CO+chain, lower bound (= C1 analysis_s) | 5.652 (4709) | 2.091 (4709) | 7.884 (4709) | 5.652 (4709) |

Check against CAP_84600.md section 3 (All, 4,685-set; run only / verdict step / end-to-end):
  - vector-clock: CAP (7.32, 2.454, 9.966), recomputed (7.32, 2.454, 9.966) (n 4685/4685/4685) -> equal
  - scalar-clock: CAP (7.015, 2.173, 9.339), recomputed (7.015, 2.173, 9.339) (n 4685/4685/4685) -> equal
  - collector-only: CAP (5.564, 2.098, 7.773), recomputed (5.564, 2.098, 7.773) (n 4685/4685/4685) -> equal
  - collector alone over all finished programs (the paper's 5.7x): 5.652 (n 4709)

Chain rows whose run wall differs from C1's row of the same program: 0 of 4709 (run-only cost of the chain mode is C1's by construction when 0).

### analysis_s of the verdict step per suite: median, max, and the closure's share

Step 2 (chain, EPYC nodes) next to the A5 reference (C1, A5's node class). share = sum(chain_s) / sum(analysis_s) and the median of chain_s / analysis_s per program.

| suite | n | chain median (s) | chain max (s) | C1 ref median (s) | C1 ref max (s) | sum chain (s) | sum C1 ref (s) | sum chain_s (s) | share (sums) | share (median) |
|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0.607 | 1.512 | 0.784 | 1.630 | 269.5 | 312.5 | 0.53 | 0.0020 | 0.0018 |
| Indigo 1.3 (PI) | 4130 | 0.383 | 1.410 | 0.408 | 1.782 | 1669.1 | 1839.6 | 0.04 | 0.0000 | 0.0000 |
| ECL (P3) | 60 | 0.608 | 1.292 | 0.728 | 1.366 | 39.9 | 44.9 | 0.07 | 0.0017 | 0.0018 |
| ScoR apps (P4) | 28 | 1.236 | 9.072 | 1.382 | 14.529 | 68.4 | 96.2 | 0.05 | 0.0007 | 0.0000 |
| ScoR litmus (P5) | 33 | 0.352 | 0.816 | 0.361 | 0.465 | 11.7 | 12.4 | 0.00 | 0.0000 | 0.0000 |
| cuHadron (P6) | 34 | 0.314 | 0.443 | 0.356 | 0.488 | 10.9 | 12.1 | 0.01 | 0.0010 | 0.0000 |
| HeCBench other 14 (P7) | 14 | 0.678 | 5.991 | 0.792 | 11.836 | 22.2 | 31.4 | 1.46 | 0.0658 | 0.0092 |
| HeCBench SC 10 (P9) | 10 | 2.052 | 7.860 | 2.166 | 11.310 | 27.8 | 34.9 | 1.31 | 0.0474 | 0.0095 |
| HeCBench (P7+P9) | 24 | 0.944 | 7.860 | 1.153 | 11.836 | 50.0 | 66.3 | 2.77 | 0.0556 | 0.0095 |
| all but HeCBench | 4685 | 0.393 | 9.072 | 0.417 | 14.529 | 2069.5 | 2317.7 | 0.70 | 0.0003 | 0.0000 |
| all | 4709 | 0.394 | 9.072 | 0.418 | 14.529 | 2119.4 | 2384.0 | 3.48 | 0.0016 | 0.0000 |

Largest chain analysis_s: 9.072 s (P4-reduction-norace-large), its chain_s 0.000 s.
Largest chain_s: P7-stencil1d-cuda 0.631 s of 0.663 s; P9-atomicCAS-cuda 0.613 s of 7.860 s; P7-heartwall-cuda 0.434 s of 5.991 s; P9-dxtc2-cuda 0.339 s of 2.829 s; P7-srad-cuda 0.333 s of 2.281 s

Analysis nodes of step 2 (anode= in the notes, one per program): {'c5': 2360, 'c45': 2349}

Step-2 chain analysis_s over the A5 reference analysis_s, by analysis node (sums over the programs of that node; node class from the README: c5 EPYC 9115, c45 EPYC 7302P, c4/c58/c2 EPYC 9115, c25/c39 EPYC 7302P, c62 EPYC 8124P, c14/c26 Xeon 4110): c45 1.081 (ref sum 1154 s), c5 0.708 (ref sum 1229 s)



## 6. The property

Closure gives every pair reachable by a chain of transitions cuVein recorded (by construction): for every kernel, every (anc, cur) the pc graph joins by a walk whose inner pcs are reads is judged at the narrowest bound of any such walk (tests in `python/test_co_chain.py`; parity: a program with no derived and no rescued pair equals C1 on all five fields, 0 violations over 3,394 programs). It can miss a pair that the clock modes' frontier finds only where a hop falls in a gap specific to this mode (first-lane allocation, pool exhaustion). Section 3's missed-detection list measures that effect: of the 4,001 pairs SC reports in the 345 programs that are Race in both modes and that CO+chain does not, 74 (34 programs, all out-of-bounds variants) lie in a kernel where the static check (b) finds dropped words at one of the pair's pcs, 0 can be tied to pool exhaustion (not measurable: `pool_miss_count` is not emitted), 0 to a pc-0 previous accessor; the remaining pairs are not collector-gap misses but misses of the closure's own rule (3,619 reachable only through a non-read hop, 62 thread-local only) or of the comparison (227 pcs not executed in the CO recording, 18 unexplained). At program level, the gap-specific loss is 0 of 2. So the property holds with the stated exception, and the exception is small and confined to the out-of-bounds corner of Indigo 1.3.

## 7. Gaps

Source: c6 step 0 (code reading at `98371ee`) and the interim gap note (classification and two static checks, job 325602 on c57, 1:09:47, `/home/fzheng4/c6-static/c6_static_out.json`; scripts `c6_static_checks.py`, `c6_static_agg.py`). Jeffery's classification of what the graph can lose:

**Shared / outside the model** (the same in every mode, by design, decided in `design/T6_REVIEW.md:18`, CLAUDE.md:18, 409, 588; the clock modes lose them too):
- width / alignment: only `ptr + 4k` of an access is tracked (C:3802, 3861, 3934), so differently sized or misaligned accesses to the same bytes never meet; the HbClock key is the lane's start address with no size, sub-word addresses go to a plain table (HbClock 407-413);
- drain order: transitions are formed in drain-buffer order, not memory-effect order (G:10-24, 126; HbClock consumes the same order, 2084, 4248; D15 / A2);
- cross-launch: the shadow is per kernel (generation check ~3829 / 3880; HbClock per kernel);
- local memory: no shadow (C:4038-4040, 4072-4075; the HB side excludes it, D14 / I5).

**Specific to collector-only** (Jeffery's classification): the first-lane allocation lookup (C:4124-4127, rebase 4152, `break` without count 3806-3808) and shared-pool exhaustion (pool cap 4,608 for `-n 1`, C:2752-2762, 3975-4001, 4079-4087, `pool_miss_count` 3992 / 2847 / H:196, never emitted).

**Unreachable in this corpus**: a previous accessor at pc offset 0 (indistinguishable from cold, C:3613, 3622-3632; consumers skip it, sync_dominance.py:1444, 1559, 1706) and shared offsets >= 102,400 (C:3936-3940, default 2762, low 32 bits).

**Check result: the classification is partly wrong.** The first-lane lookup and the pool exhaustion are on the collector path in **every** mode: the edges come from this shadow in vector-clock and scalar-clock as well. What differs is compensation: the clock modes recover pairs the shadow loses through HbClock's per-lane event candidates (`hb_races`, the barrier pass), which have no counterpart here; they do not compensate for R3, whose `sync_edges` and `same_loc` are built from the same edges. So the two gaps are not "collector-only gaps"; they are collector defects whose effect on the verdict is smaller in the clock modes for data-race pairs and the same for the certificate chains.

**Static check (a), pc 0**: 5,920 CFG files, 1,327 distinct (md5), 41,718 kernels, 3,170,033 memory instructions: **0 memory instructions at offset 0** (the opcodes at offset 0 are IMAD 18,312, MOV 8,243, IADD3 46, WARPSYNC 18, BSSY 6, BMOV 10, ISETP 10, I2F 4, SHF 2, LOP3 2, DSETP 2, FSETP 2). 1 parse error (`P4-1dconv-norace-large`, no kernel clusters); 16 cuHadron bulkcpy / dsmem programs have no CFG (need sm_90). Shared >= 102,400: `YOSEMITE_GPU_MAX_SHARED_MEMORY_PER_BLOCK` is set in no `meta.json`; arch is 8.9 for all 4,803 programs (4,725 + 5 + 1 + 56 + 16; job 325608); the sm_89 opt-in maximum is 101,376 B (CUDA programming guide, not in the repo, not checked here), below the 102,400 threshold.

**Static check (b), access sizes** (distinct (program, kernel, pc), non-local; ids in two stores counted once; RW = the 72 real-world ids):

| suite | programs | pcs 1 B (programs) | pcs 2 B | pcs 4 B | pcs 8 B | pcs 16 B | local-only pcs |
|---|---|---|---|---|---|---|---|
| P1 | 400 | 144 (48) | 0 | 8,748 (400) | 0 | 0 | 0 |
| PI | 4130 | 0 | 0 | 34,356 (4,130) | 0 | 0 | 0 |
| P3 | 60 | 48 (16) | 0 | 1,232 (60) | 0 | 0 | 0 |
| P4 | 28 | 20 (8) | 0 | 1,320 (28) | 0 | 0 | 0 |
| P5 | 33 | 0 | 0 | 165 (33) | 0 | 0 | 0 |
| P6 | 34 | 16 (8) | 0 | 515 (34) | 0 | 0 | 0 |
| P7 | 14 | 22 (2) | 0 | 1,029 (13) | 1 (1) | 142 (2) | 0 |
| P9 | 10 | 0 | 0 | 757 (9) | 427 (6) | 77 (2) | 0 |
| RW | 72 | 499 (12) | 320 (14) | 5,967 (66) | 4,225 (36) | 786 (32) | 0 |
| all | 4781 | 749 (94) | 320 (14) | 54,089 (4,773) | 4,653 (43) | 1,005 (36) | 0 |

(other sizes: 12 B in 2 P9 and 6 RW pcs.) Dropped-word deficit (expected 4-byte words from the node's lane and address counts exceed the words on the edges; an estimate that assumes one access width per pc): P1 0 / 8,892 pcs; **PI 1,300 / 34,356 pcs in 612 programs**; P3, P4, P5, P6, P7, P9 0; **RW 2 / 11,803 pcs in 2 programs**. In this step all 34 programs with a deficit among the pairs SC reports and CO+chain does not are Indigo 1.3 `boundsBug` variants (an access past the allocation end, which the `break` of C:3806-3808 drops without a count).

### 7.1 The first-lane allocation lookup is a collector defect that affects cuVein's default tool too

`pc_dependency_analysis.cpp` (98371ee): the shadow region of a global warp access is looked up from the **first active lane's** address only (C:4124-4127, `find_memory_region_containing(..., trace.addresses[first_lane])`); the other lanes' addresses are rebased on that region's start (C:4152, `trace.addresses[j] - memory_region_start`). A lane in another allocation is then either dropped by the bounds test (`if (addr >= shadow_memory._size) break;`, C:3806-3808, no cold count, no edge, no flag in the JSON) or aliased onto a wrong word of the first region; if the first lane lies in no region, all lanes go to the absolute-address hash map (`unit_access_unknown`, C:4129-4147), which never meets the per-region shadow. Words of an access that extend past the allocation end are dropped the same way. Every mode reads these edges (vector-clock and scalar-clock run the same collector; the clock modes only add HbClock on top), so the default tool loses these transitions in the same places; the evidence in this corpus is the deficit of check (b) (Indigo 1.3, 1,300 pcs in 612 programs; real-world 2 pcs in 2 programs) and the 74 pairs above. **Not fixed here**: the collector is frozen for C6. A fix would look the region up per lane (or count the dropped lanes and expose the count in the JSON, as `pool_miss_count` should be), and would need a re-record.

## 8. Missing, and why

- `pool_miss_count` is not in the JSON: pool exhaustion cannot be confirmed for any kernel, only excluded where the grid is at most 4,608 CTAs; no unreachable shared-space pair of this step lies in a kernel with a larger grid (class count 0).
- Addresses: the kernel JSON holds no addresses or thread ids, so whether the hops of a derived pair can share an address is decided only where the counts force it (pigeonhole, section 4); 10 of 20 sampled pairs are undetermined.
- CPU class of c36 and c79 (A5's analysis nodes): not measured (both were allocated to other jobs); the re-time on c26 stands in for A5's class as the brief states.
- The re-time covers 47 of 4,709 programs; the A5-class cost is an estimate with bounds, not a measurement of the whole corpus.
- Static deficit counts are an estimate (one access width per pc; aggregated over launches of the same kernel name).
- Dropped-word attribution for a missed pair is by the pair's own pcs; a deficit at a pc of a hidden intermediate hop cannot be seen (no addresses), so the 74 pairs are a lower bound for the first-lane effect on pairs classed "via a non-read hop".
- Real-world: ids whose attribution had not finished when this file was written show `NOT-SCORED` in the tables above and are in no count (see section 2.2).


## 9. Jobs

Step 2 jobs are in `eval/results/co-chain/README.md`. Step 3: one SLURM job on one node (the node cap was held by another session until 23:09 on 2 Nov): **325769** (`c6-step3`, `normal`, `--exclusive`, c4, EPYC 9115 16-core, 125 GB), a worker that ran the queued steps `c6_stage.sh` (sandbox and `make_tables.py --collector-only --co-chain`), `c6_tables.py`, `c6_cost.py`, `c6_detect.py` (twice), `c6_extra.py`, and the real-world attribution `c6_rw_setup.sh` / `c6_rw_run.sh` (12 h limit per id) with `c6_rw_report.py`. No other job was submitted. Scripts: `eval/baselines/setup/c6_{stage,tables,cost,detect,extra,rw_setup,rw_run,rw_report,static_checks,static_agg}.*`, `c6_worker.sbatch`, `c6_env.sh`.
