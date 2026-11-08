## Table 3 (tab:eval-accuracy): accuracy per suite, data races alone, Indigo 1.3 counted per code, four cuVein columns

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

## Accuracy per program-input (Indigo 1.3 counted per run), four columns

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

## tab:eval-accuracy-union and tab:eval-countings: the three countings, four columns (per program-input)

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

## tab:eval-litmus: the 33 ScoR litmus kernels, four columns

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

## Program level: CO+chain against CO

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

## Program level: CO+chain against SC

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

## Indigo 1.3 per program-input against the input-level oracle (baselines-pi-oracle.csv)

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

## Check against the paper (vector-clock and scalar-clock cells)

Every vector-clock and scalar-clock cell of the per-program-input accuracy table, the union and three-countings tables and the litmus table recomputes to the paper's value.
