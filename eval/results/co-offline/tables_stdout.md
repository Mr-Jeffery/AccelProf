## Table 6.1 (tab:eval-accuracy): accuracy per suite, data races alone, CO-R next to the three other cuVein columns

Cells: recall TP/(TP+FN) · false-positive rate FP/(FP+TN); TO = timed out, ERR = errored. Race-alone verdict = `race_alone_verdict` of `make_tables.py`. CO-R: a conflicting reuse pair no certificate orders is Race (class `race`) or SC; no Latent. "Edges only" = C1's collector-only run (separate recording, no sync pass).

| suite | vector-clock | scalar-clock | cuVein edges only (C1) | CO-R |
|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 | 200/200 · 0/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 |
| Indigo 1.3, SC's 99 | 43/45 · 0/44 | 43/45 · 0/44 | 43/45 · 4/44 | 43/45 · 4/44 |
| ECL | — · 16/60 | — · 16/60 | — · 16/60 | — · 16/60 |
| ScoR applications | 14/14 · 2/14 | 14/14 · 2/14 | 14/14 · 6/14 | 14/14 · 6/14 |
| ScoR litmus + canary | 4/19 · 1/14 | 3/19 · 0/14 | 2/19 · 0/14 | 3/19 · 0/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/6; 1 ERR | 3/3 · 1/6; 1 TO |
| **All pre-registered** | 1,934/2,082 · 18/1,548; 16 ERR | 1,934/2,082 · 18/1,548; 16 ERR | 1,956/2,082 · 246/1,548; 16 ERR | 1,958/2,082 · 246/1,548; 16 ERR |

## tab:eval-accuracy-union and tab:eval-countings: the three countings, four columns

races = Race alone; strong = a program with an unordered strong conflict reported (class `sc`); union = Race or strong. Cells TP/(TP+FN) · FP/(FP+TN). VC = vector-clock, SC = scalar-clock, EO = cuVein edges only (C1), CO-R.

| suite | VC races | VC strong | VC union | SC races | SC strong | SC union | EO races | EO strong | EO union | CO-R races | CO-R strong | CO-R union |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 | 200/200 · 0/200 | 0/200 · 72/200 | 200/200 · 72/200 |
| Indigo 1.3 | 1,714/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 0/1,862 · 0/1,260 | 1,714/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 0/1,862 · 0/1,260 | 1,737/1,862 · 224/1,260 | 1,738/1,862 · 224/1,260 | 0/1,862 · 0/1,260 | 1,738/1,862 · 224/1,260 |
| ECL | — · 16/60 | — · 36/60 | — · 44/60 | — · 16/60 | — · 32/60 | — · 40/60 | — · 16/60 | — · 36/60 | — · 44/60 | — · 16/60 | — · 32/60 | — · 40/60 |
| ScoR applications | 14/14 · 2/14 | 8/14 · 7/14 | 14/14 · 7/14 | 14/14 · 2/14 | 8/14 · 4/14 | 14/14 · 4/14 | 14/14 · 6/14 | 6/14 · 4/14 | 14/14 · 8/14 | 14/14 · 6/14 | 8/14 · 4/14 | 14/14 · 8/14 |
| ScoR litmus + canary | 4/19 · 1/14 | 17/19 · 4/14 | 19/19 · 5/14 | 3/19 · 0/14 | 17/19 · 0/14 | 18/19 · 0/14 | 2/19 · 0/14 | 16/19 · 0/14 | 17/19 · 0/14 | 3/19 · 0/14 | 17/19 · 0/14 | 18/19 · 0/14 |
| cuHadron (in scope) | 6/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 5/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR | 0/6 · 0/14; 16 ERR | 6/6 · 0/14; 16 ERR |
| HeCBench, SC's 10 | 2/2 · 0/6; 2 TO | 0/2 · 0/6; 2 TO | 2/2 · 0/6; 2 TO | 3/3 · 0/6; 1 TO | 0/3 · 0/6; 1 TO | 3/3 · 0/6; 1 TO | 3/3 · 1/6; 1 ERR | 0/3 · 0/6; 1 ERR | 3/3 · 1/6; 1 ERR | 3/3 · 1/6; 1 TO | 0/3 · 0/6; 1 TO | 3/3 · 1/6; 1 TO |
| **All pre-registered** | 1,934/2,082 · 18/1,548; 16 ERR | 8/2,082 · 115/1,548; 16 ERR | 1,934/2,082 · 123/1,548; 16 ERR | 1,934/2,082 · 18/1,548; 16 ERR | 8/2,082 · 108/1,548; 16 ERR | 1,934/2,082 · 116/1,548; 16 ERR | 1,956/2,082 · 246/1,548; 16 ERR | 6/2,082 · 112/1,548; 16 ERR | 1,956/2,082 · 348/1,548; 16 ERR | 1,958/2,082 · 246/1,548; 16 ERR | 8/2,082 · 108/1,548; 16 ERR | 1,958/2,082 · 344/1,548; 16 ERR |

## tab:eval-litmus: the 33 ScoR litmus kernels, four columns

Race = a data race is reported; Strong = only an unordered strong conflict is reported; — = nothing reported. `rtraw` counted as recorded (Race, a false report).

| kernel | ScoR label | VC | SC | edges only | CO-R |
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
| `race_interblock_none-lock_rtraw` | racy | Race | Race | — | Race |
| `race_interblock_none-lock_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_blklock-no-stf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_blklock-no-tf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_dev-blklock-no-stf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_dev-blklock-no-tf_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_none-atom_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_none-blkatom_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_none-blklock_waw` | racy | Strong | Strong | Strong | Strong |
| `race_interwarp_none-lock_waw` | racy | Strong | Strong | Strong | Strong |

33 P5 programs; 33 kernels parsed from the paper's table; 0 vector/scalar cells differ from the paper.

## Program level: CO-R against scalar-clock (the same recordings; every difference is the barrier-ordered rule)

| suite | programs | same verdict | SC Race → CO-R Clean | SC Clean → CO-R Race | other differences |
|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 |
| PI | 4130 | 3882 | 0 | 248 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 |
| P4 | 28 | 24 | 0 | 4 | 0 |
| P5 | 33 | 33 | 0 | 0 | 0 |
| P6 | 34 | 34 | 0 | 0 | 0 |
| P7 | 14 | 13 | 0 | 1 | 0 |
| P9 | 10 | 9 | 0 | 1 | 0 |
| **all** | 4709 | 4455 | 0 | 254 | 0 |

The programs that differ, by suite, direction and label (the paper's label: racy / race-free / unlabelled):

| suite | direction | racy | race-free | unlabelled |
|---|---|---|---|---|
| P4 | SC CLEAN → CO-R RACE | 0 | 4 | 0 |
| P7 | SC CLEAN → CO-R RACE | 0 | 0 | 1 |
| P9 | SC CLEAN → CO-R RACE | 0 | 1 | 0 |
| PI | SC CLEAN → CO-R RACE | 24 | 224 | 0 |

Race-free (labelled) programs that are Race in CO-R and Clean in scalar-clock: **229**; per suite: P4 4, P9 1, PI 224. Each with its pairs: `race_free_cor_race_sc_clean.csv`.

All race-free-labelled programs that are Race in CO-R: 248 (of them Race in scalar-clock too: 19).

Other differences (a side TIMEOUT / ERROR / none): 0

Scalar-clock Race, CO-R Clean: 0

## Check against the paper (vector-clock and scalar-clock cells)

Every vector-clock and scalar-clock cell of Table 6.1, the union table, the three-countings table and the litmus table recomputes to the paper's value.
