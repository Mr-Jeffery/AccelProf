## Table 3 (tab:eval-accuracy): accuracy per suite, data races alone, Indigo 1.3 counted per code, six cuVein columns

Cells: recall TP/(TP+FN) · false-positive rate FP/(FP+TN). Indigo 1.3 labels a code, so its rows count codes: a code is reported when the mode reports Race on any of its seven inputs. All other rows count program-inputs as in the paper. Aggregate = Indigo3 + Indigo 1.3 (codes) + ECL + ScoR applications + cuHadron in scope. C1 = C1's collector-only run (atomicCAS row as in eval/cap-84600), C6 = C6's chain-closure re-analysis of the same recordings, S1 / S2 = the C6b re-analyses of the same recordings (S1: `--chain-closure --co-async --co-r3 strict`, S2: `--chain-closure --co-async --co-r3 off`).

| suite | vector-clock | scalar-clock | C1 | C6 | S1 | S2 |
|---|---|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 |
| Indigo 1.3 (590 codes) | 266/266 · 0/180 | 266/266 · 0/180 | 266/266 · 32/180 | 266/266 · 32/180 | 266/266 · 32/180 | 266/266 · 32/180 |
| Indigo 1.3, SC's 99 (99 codes) | 45/45 · 0/44 | 45/45 · 0/44 | 45/45 · 4/44 | 45/45 · 4/44 | 45/45 · 4/44 | 45/45 · 4/44 |
| ECL | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 |
| ScoR applications | 14/14 · 2/14 | 14/14 · 2/14 | 14/14 · 6/14 | 14/14 · 8/14 | 14/14 · 8/14 | 14/14 · 8/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/7 | 3/3 · 2/7 | 3/3 · 2/7 | 3/3 · 2/7 |
| **All pre-registered** | 486/486 · 18/468; 16 ERR | 486/486 · 18/468; 16 ERR | 485/486 · 54/468; 16 ERR | 485/486 · 56/468; 16 ERR | 486/486 · 56/468; 16 ERR | 486/486 · 56/468; 16 ERR |

**Table 3, aggregate row (races alone; Indigo 1.3 per code), explicitly:**

- vector-clock: recall 486/486 · FP 18/468; 16 ERR
- scalar-clock: recall 486/486 · FP 18/468; 16 ERR
- C1: recall 485/486 · FP 54/468; 16 ERR
- C6: recall 485/486 · FP 56/468; 16 ERR
- S1: recall 486/486 · FP 56/468; 16 ERR
- S2: recall 486/486 · FP 56/468; 16 ERR

Aggregate check, vector-clock: paper (486, 486, 18, 468), recomputed (486, 486, 18, 468) -> equal

Aggregate check, scalar-clock: paper (486, 486, 18, 468), recomputed (486, 486, 18, 468) -> equal

Aggregate check, C1: paper (486, 486, 54, 468), recomputed (485, 486, 54, 468) -> DIFFERENT

## Accuracy per program-input (Indigo 1.3 counted per run), six columns

| suite | vector-clock | scalar-clock | C1 | C6 | S1 | S2 |
|---|---|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 |
| Indigo 1.3, SC's 99 | 43/45 · 0/44 | 43/45 · 0/44 | 43/45 · 4/44 | 43/45 · 4/44 | 43/45 · 4/44 | 43/45 · 4/44 |
| ECL | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 |
| ScoR applications | 14/14 · 2/14 | 14/14 · 2/14 | 14/14 · 6/14 | 14/14 · 8/14 | 14/14 · 8/14 | 14/14 · 8/14 |
| ScoR litmus + canary | 4/19 · 1/14 | 3/19 · 0/14 | 2/19 · 0/14 | 2/19 · 0/14 | 2/19 · 0/14 | 4/19 · 1/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/7 | 3/3 · 2/7 | 3/3 · 2/7 | 3/3 · 2/7 |
| **All pre-registered** | 1,934/2,082 · 18/1,548; 16 ERR | 1,934/2,082 · 18/1,548; 16 ERR | 1,956/2,082 · 246/1,548; 16 ERR | 1,957/2,082 · 248/1,548; 16 ERR | 1,958/2,082 · 248/1,548; 16 ERR | 1,958/2,082 · 248/1,548; 16 ERR |

## tab:eval-accuracy-union and tab:eval-countings: the three countings, six columns (per program-input)

races = Race alone; strong = a program with an unordered strong conflict reported (class `sc`); union = Race or strong. Cells TP/(TP+FN) · FP/(FP+TN).


**races**

| suite | vector-clock | scalar-clock | C1 | C6 | S1 | S2 |
|---|---|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 |
| ECL | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 |
| ScoR applications | 14/14 · 2/14 | 14/14 · 2/14 | 14/14 · 6/14 | 14/14 · 8/14 | 14/14 · 8/14 | 14/14 · 8/14 |
| ScoR litmus + canary | 4/19 · 1/14 | 3/19 · 0/14 | 2/19 · 0/14 | 2/19 · 0/14 | 2/19 · 0/14 | 4/19 · 1/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/7 | 3/3 · 2/7 | 3/3 · 2/7 | 3/3 · 2/7 |
| **All pre-registered** | 1,934/2,082 · 18/1,548; 16 ERR | 1,934/2,082 · 18/1,548; 16 ERR | 1,956/2,082 · 246/1,548; 16 ERR | 1,957/2,082 · 248/1,548; 16 ERR | 1,958/2,082 · 248/1,548; 16 ERR | 1,958/2,082 · 248/1,548; 16 ERR |

**strong**

| suite | vector-clock | scalar-clock | C1 | C6 | S1 | S2 |
|---|---|---|---|---|---|---|
| Indigo3 | 0/200 · 72/200 | 0/200 · 72/200 | 0/200 · 72/200 | 0/200 · 72/200 | 0/200 · 72/200 | 0/200 · 72/200 |
| Indigo 1.3 | 0/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 0/1,862 · 0/1,260 |
| ECL | — · 36/60 | — · 32/60 | — · 36/60 | — · 36/60 | — · 36/60 | — · 36/60 |
| ScoR applications | 8/14 · 7/14 | 8/14 · 4/14 | 6/14 · 4/14 | 6/14 · 4/14 | 8/14 · 6/14 | 8/14 · 8/14 |
| ScoR litmus + canary | 17/19 · 4/14 | 17/19 · 0/14 | 16/19 · 0/14 | 17/19 · 0/14 | 17/19 · 0/14 | 17/19 · 7/14 |
| cuHadron (in scope) | 0/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 0/2 · 0/6; 2 TO | 0/3 · 0/6; 1 TO | 0/3 · 1/7 | 0/3 · 1/7 | 0/3 · 1/7 | 0/3 · 1/7 |
| **All pre-registered** | 8/2,082 · 115/1,548; 16 ERR | 8/2,082 · 108/1,548; 16 ERR | 6/2,082 · 112/1,548; 16 ERR | 6/2,082 · 112/1,548; 16 ERR | 8/2,082 · 114/1,548; 16 ERR | 8/2,082 · 116/1,548; 16 ERR |

**union**

| suite | vector-clock | scalar-clock | C1 | C6 | S1 | S2 |
|---|---|---|---|---|---|---|
| Indigo3 | 200/200 · 72/200 | 200/200 · 72/200 | 200/200 · 72/200 | 200/200 · 72/200 | 200/200 · 72/200 | 200/200 · 72/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 |
| ECL | — · 44/60 | — · 40/60 | — · 44/60 | — · 44/60 | — · 44/60 | — · 44/60 |
| ScoR applications | 14/14 · 7/14 | 14/14 · 4/14 | 14/14 · 8/14 | 14/14 · 10/14 | 14/14 · 10/14 | 14/14 · 12/14 |
| ScoR litmus + canary | 19/19 · 5/14 | 18/19 · 0/14 | 17/19 · 0/14 | 18/19 · 0/14 | 18/19 · 0/14 | 19/19 · 8/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 3/3 · 2/7 | 3/3 · 3/7 | 3/3 · 3/7 | 3/3 · 3/7 |
| **All pre-registered** | 1,934/2,082 · 123/1,548; 16 ERR | 1,934/2,082 · 116/1,548; 16 ERR | 1,956/2,082 · 348/1,548; 16 ERR | 1,957/2,082 · 350/1,548; 16 ERR | 1,958/2,082 · 350/1,548; 16 ERR | 1,958/2,082 · 352/1,548; 16 ERR |

## tab:eval-litmus: the 33 ScoR litmus kernels, six columns

Race = a data race is reported; Strong = only an unordered strong conflict is reported; — = nothing reported. `rtraw` counted as recorded.

| kernel | ScoR label | vector-clock | scalar-clock | C1 | C6 | S1 | S2 | moved |
|---|---|---|---|---|---|---|---|---|
| `canary_pc_level_false_negative` | racy | Race | — | — | — | — | Race | S2 vs C6: — -> Race |
| `norace_interblock_atom` | race-free | — | — | — | — | — | — |  |
| `norace_interblock_fence_raw` | race-free | Strong | — | — | — | — | Strong | S2 vs C6: — -> Strong |
| `norace_interblock_lock_waw` | race-free | — | — | — | — | — | Strong | S2 vs C6: — -> Strong |
| `norace_interwarp-block_fence-atom_hrd-indirect` | race-free | Race | — | — | — | — | Race | S2 vs C6: — -> Race |
| `norace_interwarp-block_fence_hrf-indirect` | race-free | Strong | — | — | — | — | Strong | S2 vs C6: — -> Strong |
| `norace_interwarp_blkatom` | race-free | — | — | — | — | — | — |  |
| `norace_interwarp_blkfence_raw` | race-free | Strong | — | — | — | — | Strong | S2 vs C6: — -> Strong |
| `norace_interwarp_blklock_waw` | race-free | — | — | — | — | — | Strong | S2 vs C6: — -> Strong |
| `norace_interwarp_dev-blkatom` | race-free | — | — | — | — | — | — |  |
| `norace_interwarp_dev-blklock_waw` | race-free | — | — | — | — | — | Strong | S2 vs C6: — -> Strong |
| `norace_interwarp_fence_raw` | race-free | Strong | — | — | — | — | Strong | S2 vs C6: — -> Strong |
| `norace_intrawarp_none-blkatom` | race-free | — | — | — | — | — | — |  |
| `norace_intrawarp_none-blklock-no-tf_waw` | race-free | — | — | — | — | — | — |  |
| `norace_intrawarp_none-blklock_waw` | race-free | — | — | — | — | — | — |  |
| `race_interblock_blkatom` | racy | Race | Race | Race | Race | Race | Race |  |
| `race_interblock_blkfence_raw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interblock_blklock_waw` | racy | Race | Race | Race | Race | Race | Race |  |
| `race_interblock_fence_rtraw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interblock_lock-blkfence_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interblock_lock-no-stf_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interblock_lock-no-tf_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interblock_none-atom_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interblock_none-lock_rtraw` | racy | Race | Race | — | Strong | Strong | Race | S2 vs C6: Strong -> Race |
| `race_interblock_none-lock_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interwarp_blklock-no-stf_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interwarp_blklock-no-tf_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interwarp_dev-blklock-no-stf_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interwarp_dev-blklock-no-tf_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interwarp_none-atom_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interwarp_none-blkatom_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interwarp_none-blklock_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |
| `race_interwarp_none-lock_waw` | racy | Strong | Strong | Strong | Strong | Strong | Strong |  |

Litmus kernels whose cell differs between C1 and C6: 1
  - `race_interblock_none-lock_rtraw` — -> Strong

Litmus kernels whose cell differs between C6 and S1: 0

Litmus kernels whose cell differs between C6 and S2: 10
  - `canary_pc_level_false_negative` — -> Race
  - `norace_interblock_fence_raw` — -> Strong
  - `norace_interblock_lock_waw` — -> Strong
  - `norace_interwarp-block_fence-atom_hrd-indirect` — -> Race
  - `norace_interwarp-block_fence_hrf-indirect` — -> Strong
  - `norace_interwarp_blkfence_raw` — -> Strong
  - `norace_interwarp_blklock_waw` — -> Strong
  - `norace_interwarp_dev-blklock_waw` — -> Strong
  - `norace_interwarp_fence_raw` — -> Strong
  - `race_interblock_none-lock_rtraw` Strong -> Race

Litmus kernels whose cell differs between C1 and S1: 1
  - `race_interblock_none-lock_rtraw` — -> Strong

Litmus kernels whose cell differs between C1 and S2: 10
  - `canary_pc_level_false_negative` — -> Race
  - `norace_interblock_fence_raw` — -> Strong
  - `norace_interblock_lock_waw` — -> Strong
  - `norace_interwarp-block_fence-atom_hrd-indirect` — -> Race
  - `norace_interwarp-block_fence_hrf-indirect` — -> Strong
  - `norace_interwarp_blkfence_raw` — -> Strong
  - `norace_interwarp_blklock_waw` — -> Strong
  - `norace_interwarp_dev-blklock_waw` — -> Strong
  - `norace_interwarp_fence_raw` — -> Strong
  - `race_interblock_none-lock_rtraw` — -> Race

Litmus kernels whose cell differs between scalar-clock and S1: 1
  - `race_interblock_none-lock_rtraw` Race -> Strong

Litmus kernels whose cell differs between scalar-clock and S2: 9
  - `canary_pc_level_false_negative` — -> Race
  - `norace_interblock_fence_raw` — -> Strong
  - `norace_interblock_lock_waw` — -> Strong
  - `norace_interwarp-block_fence-atom_hrd-indirect` — -> Race
  - `norace_interwarp-block_fence_hrf-indirect` — -> Strong
  - `norace_interwarp_blkfence_raw` — -> Strong
  - `norace_interwarp_blklock_waw` — -> Strong
  - `norace_interwarp_dev-blklock_waw` — -> Strong
  - `norace_interwarp_fence_raw` — -> Strong

33 P5 programs; 33 kernels parsed from the paper's table (read only, `git show origin/main:appendix_eval.tex`); 0 vector/scalar cells differ from the paper.

## Program level


### Program level: S1 against C6

| suite | programs | same verdict | C6 Race → S1 Clean | C6 Clean → S1 Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 4130 | 0 | 0 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 28 | 0 | 0 | 0 |
| P5 | 33 | 33 | 0 | 0 | 0 |
| P6 | 34 | 33 | 0 | 1 | 0 |
| P7 | 14 | 14 | 0 | 0 | 0 |
| P9 | 10 | 10 | 0 | 0 | 0 |
| **all** | 4709 | 4708 | 0 | 1 | 0 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P6 | C6 CLEAN → S1 RACE | 1 | 0 | 0 |

The programs: `P6-memcpy-shared_readwrite_race-racy` (racy, CLEAN → RACE)

### Program level: S2 against C6

| suite | programs | same verdict | C6 Race → S2 Clean | C6 Clean → S2 Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 4130 | 0 | 0 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 28 | 0 | 0 | 0 |
| P5 | 33 | 30 | 0 | 3 | 0 |
| P6 | 34 | 33 | 0 | 1 | 0 |
| P7 | 14 | 14 | 0 | 0 | 0 |
| P9 | 10 | 10 | 0 | 0 | 0 |
| **all** | 4709 | 4705 | 0 | 4 | 0 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P5 | C6 CLEAN → S2 RACE | 2 | 1 | 0 |
| P6 | C6 CLEAN → S2 RACE | 1 | 0 | 0 |

The programs: `P6-memcpy-shared_readwrite_race-racy` (racy, CLEAN → RACE), `P5-canary` (racy, CLEAN → RACE), `P5-race_interblock_none-lock_rtraw` (racy, CLEAN → RACE), `P5-norace_interwarp-block_fence-atom_hrd-indirect` (race-free, CLEAN → RACE)

### Program level: S1 against C1

| suite | programs | same verdict | C1 Race → S1 Clean | C1 Clean → S1 Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 4104 | 0 | 26 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 26 | 0 | 2 | 0 |
| P5 | 33 | 33 | 0 | 0 | 0 |
| P6 | 34 | 33 | 0 | 1 | 0 |
| P7 | 14 | 12 | 0 | 2 | 0 |
| P9 | 10 | 9 | 0 | 1 | 0 |
| **all** | 4709 | 4677 | 0 | 32 | 0 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P4 | C1 CLEAN → S1 RACE | 0 | 2 | 0 |
| P6 | C1 CLEAN → S1 RACE | 1 | 0 | 0 |
| P7 | C1 CLEAN → S1 RACE | 0 | 0 | 2 |
| P9 | C1 CLEAN → S1 RACE | 0 | 1 | 0 |
| PI | C1 CLEAN → S1 RACE | 1 | 0 | 25 |

### Program level: S2 against C1

| suite | programs | same verdict | C1 Race → S2 Clean | C1 Clean → S2 Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 4104 | 0 | 26 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 26 | 0 | 2 | 0 |
| P5 | 33 | 30 | 0 | 3 | 0 |
| P6 | 34 | 33 | 0 | 1 | 0 |
| P7 | 14 | 12 | 0 | 2 | 0 |
| P9 | 10 | 9 | 0 | 1 | 0 |
| **all** | 4709 | 4674 | 0 | 35 | 0 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P4 | C1 CLEAN → S2 RACE | 0 | 2 | 0 |
| P5 | C1 CLEAN → S2 RACE | 2 | 1 | 0 |
| P6 | C1 CLEAN → S2 RACE | 1 | 0 | 0 |
| P7 | C1 CLEAN → S2 RACE | 0 | 0 | 2 |
| P9 | C1 CLEAN → S2 RACE | 0 | 1 | 0 |
| PI | C1 CLEAN → S2 RACE | 1 | 0 | 25 |

### Program level: S1 against scalar-clock

| suite | programs | same verdict | scalar-clock Race → S1 Clean | scalar-clock Clean → S1 Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 3882 | 0 | 248 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 22 | 0 | 6 | 0 |
| P5 | 33 | 32 | 1 | 0 | 0 |
| P6 | 34 | 34 | 0 | 0 | 0 |
| P7 | 14 | 10 | 0 | 3 | 1 |
| P9 | 10 | 7 | 0 | 2 | 1 |
| **all** | 4709 | 4447 | 1 | 259 | 2 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P4 | scalar-clock CLEAN → S1 RACE | 0 | 6 | 0 |
| P5 | scalar-clock RACE → S1 CLEAN | 1 | 0 | 0 |
| P7 | scalar-clock CLEAN → S1 RACE | 0 | 0 | 3 |
| P7 | scalar-clock TIMEOUT → S1 CLEAN | 0 | 0 | 1 |
| P9 | scalar-clock CLEAN → S1 RACE | 0 | 2 | 0 |
| P9 | scalar-clock TIMEOUT → S1 CLEAN | 0 | 1 | 0 |
| PI | scalar-clock CLEAN → S1 RACE | 24 | 224 | 0 |

### Program level: S2 against scalar-clock

| suite | programs | same verdict | scalar-clock Race → S2 Clean | scalar-clock Clean → S2 Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 3882 | 0 | 248 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 22 | 0 | 6 | 0 |
| P5 | 33 | 31 | 0 | 2 | 0 |
| P6 | 34 | 34 | 0 | 0 | 0 |
| P7 | 14 | 10 | 0 | 3 | 1 |
| P9 | 10 | 7 | 0 | 2 | 1 |
| **all** | 4709 | 4446 | 0 | 261 | 2 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P4 | scalar-clock CLEAN → S2 RACE | 0 | 6 | 0 |
| P5 | scalar-clock CLEAN → S2 RACE | 1 | 1 | 0 |
| P7 | scalar-clock CLEAN → S2 RACE | 0 | 0 | 3 |
| P7 | scalar-clock TIMEOUT → S2 CLEAN | 0 | 0 | 1 |
| P9 | scalar-clock CLEAN → S2 RACE | 0 | 2 | 0 |
| P9 | scalar-clock TIMEOUT → S2 CLEAN | 0 | 1 | 0 |
| PI | scalar-clock CLEAN → S2 RACE | 24 | 224 | 0 |

### Program level: S2 against S1

| suite | programs | same verdict | S1 Race → S2 Clean | S1 Clean → S2 Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 4130 | 0 | 0 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 28 | 0 | 0 | 0 |
| P5 | 33 | 30 | 0 | 3 | 0 |
| P6 | 34 | 34 | 0 | 0 | 0 |
| P7 | 14 | 14 | 0 | 0 | 0 |
| P9 | 10 | 10 | 0 | 0 | 0 |
| **all** | 4709 | 4706 | 0 | 3 | 0 |

Programs that differ, by suite, direction and the paper's label:

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P5 | S1 CLEAN → S2 RACE | 2 | 1 | 0 |

The programs: `P5-canary` (racy, CLEAN → RACE), `P5-race_interblock_none-lock_rtraw` (racy, CLEAN → RACE), `P5-norace_interwarp-block_fence-atom_hrd-indirect` (race-free, CLEAN → RACE)

S1: race-free-labelled programs Race in S1 and Clean in scalar-clock: **232**; per suite: P4 6, P9 2, PI 224
S1: scalar-clock Race, S1 Clean: 1 programs (labels: {'racy': 1}; per suite {'P5': 1}): `P5-race_interblock_none-lock_rtraw`
S1: scalar-clock Clean, S1 Race: 259 programs (labels: {'race-free': 232, 'racy': 24, 'unlabelled': 3}; per suite {'PI': 248, 'P4': 6, 'P9': 2, 'P7': 3})

S2: race-free-labelled programs Race in S2 and Clean in scalar-clock: **233**; per suite: P4 6, P5 1, P9 2, PI 224
S2: scalar-clock Race, S2 Clean: 0 programs (labels: {}; per suite {}): 
S2: scalar-clock Clean, S2 Race: 261 programs (labels: {'race-free': 233, 'racy': 25, 'unlabelled': 3}; per suite {'PI': 248, 'P4': 6, 'P9': 2, 'P5': 2, 'P7': 3})

Race-free-labelled programs that are Race, per mode (programs):

| mode | total | P1 | PI | P3 | P4 | P6 | P7 | P9 |
|---|---|---|---|---|---|---|---|---|
| vector-clock | 20 | 0 | 0 | 16 | 2 | 1 | 0 | 0 |
| scalar-clock | 19 | 0 | 0 | 16 | 2 | 1 | 0 | 0 |
| C1 | 248 | 0 | 224 | 16 | 6 | 1 | 0 | 1 |
| C6 | 251 | 0 | 224 | 16 | 8 | 1 | 0 | 2 |
| S1 | 251 | 0 | 224 | 16 | 8 | 1 | 0 | 2 |
| S2 | 252 | 0 | 224 | 16 | 8 | 1 | 0 | 2 |

## Indigo 1.3 per program-input against the input-level oracle (baselines-pi-oracle.csv)

The oracle file has 1338 rows (ids found in the runs: 1338). Cell: programs with that verdict. Rows are the oracle's answer (CONFLICT = two threads touch one location, one writes, not both atomic, no barrier between; NO-CONFLICT otherwise) by the suite's label.

| label | oracle | n | vector-clock Race | scalar-clock Race | C1 Race | C6 Race | S1 Race | S2 Race |
|---|---|---|---|---|---|---|---|---|
| racy | CONFLICT | 650 | 650 | 650 | 649 | 650 | 650 | 650 |
| racy | NO-CONFLICT | 148 | 0 | 0 | 24 | 24 | 24 | 24 |
| race-free | NO-CONFLICT | 540 | 0 | 0 | 96 | 96 | 96 | 96 |

Racy-labelled Indigo 1.3 program-inputs a mode does not report (verdict not Race), split by the oracle's answer:

| mode | missed | oracle CONFLICT | oracle NO-CONFLICT | not in oracle file |
|---|---|---|---|---|
| vector-clock | 148 | 0 | 148 | 0 |
| scalar-clock | 148 | 0 | 148 | 0 |
| C1 | 125 | 1 | 124 | 0 |
| C6 | 124 | 0 | 124 | 0 |
| S1 | 124 | 0 | 124 | 0 |
| S2 | 124 | 0 | 124 | 0 |

Race verdicts on Indigo 1.3 program-inputs the oracle says have NO-CONFLICT, by label:

| mode | race-free-labelled | racy-labelled | unlabelled |
|---|---|---|---|
| vector-clock | 0 | 0 | 0 |
| scalar-clock | 0 | 0 | 0 |
| C1 | 96 | 24 | 0 |
| C6 | 96 | 24 | 0 |
| S1 | 96 | 24 | 0 |
| S2 | 96 | 24 | 0 |

## Check against the paper (vector-clock and scalar-clock cells)

Every vector-clock and scalar-clock cell of the per-program-input accuracy table, the union and three-countings tables and the litmus table recomputes to the paper's value.
