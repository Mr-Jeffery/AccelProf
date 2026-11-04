# CO_CHAIN_B: collector-only mode with the C6b rules (C6b, step 4)

Branch `eval/co-chain-b` (base `eval/co-chain` be325e03 = C6's CO_CHAIN.md, cuVein 98371ee + C3; step 1 `3b2e91f8` rules, step 2 `93ae2d66` / `ea2b9c9f` re-analysis, step 3 `90cc7e9d` hb-stripped run). Step 4 is analysis only: no recording, no GPU, no change to `python/`, the runtime, the collector, `hb_oracle.py`, `make_tables.py` or cuRacePaper (read only, `git show origin/main:appendix_eval.tex`). Every number comes from a CSV or a confirm JSON through the scripts `eval/baselines/setup/c6b_*` and is also in `eval/results/co-chain-b/step4/`. Nothing is hand-entered except the text.

Names: **VC** / **SC** = vector-clock / scalar-clock; **C1** = C1's collector-only run (verdicts from the collector's edges, no sync pass, no closure); **C6** = C6's re-analysis of C1's recordings with `--chain-closure` (narrowest chain bound, `CO_CHAIN.md`); **S1** = the same recordings with `--chain-closure --co-async --co-r3 strict`; **S2** = `--chain-closure --co-async --co-r3 off`. All of S1, S2, C6, C1 are the 4,709 analysed programs of `final-2026-11-co` (+ `-long`, `-24h`); recordings are not modified. "Table 3" is the paper's accuracy table (`tab:eval-accuracy`: Indigo 1.3 counted per code, aggregate over Indigo3, Indigo 1.3, ECL, ScoR applications, cuHadron in scope). "Race" is the races-alone verdict (`make_tables.race_alone_verdict`) unless said otherwise.

## 0. Results in short

- **Table 3, aggregate row** (races alone; Indigo 1.3 per code; recall · false-positive rate): **S1 486/486 · 56/468; S2 486/486 · 56/468**; VC 486/486 · 18/468; SC 486/486 · 18/468; C1 485/486 · 54/468; C6 485/486 · 56/468. Per program-input (Indigo 1.3 per run): S1 and S2 1,958/2,082 · 248/1,548; C6 1,957/2,082 · 248/1,548; C1 1,956/2,082 · 246/1,548; VC and SC 1,934/2,082 · 18/1,548. Against C6 the recall moves by one program in both settings (`P6-memcpy-shared_readwrite_race-racy`, cuHadron 5/6 to 6/6); no false-positive cell of Table 3 moves.
- **Verdict changes against C6** (all CLEAN to RACE; none RACE to CLEAN): S1 1 program of 4,709 (P6 1, `P6-memcpy-shared_readwrite_race-racy`, cause: `async`); S2 4 (P5 3: `P5-canary`, `P5-norace_interwarp-block_fence-atom_hrd-indirect`, `P5-race_interblock_none-lock_rtraw`, cause `atomic_chain_off`; P6 1, the same `async` program). P1, PI, P3, P4, P7, P9: 0 in both. Against C1: S1 32, S2 35 (section 3.1).
- **Against scalar-clock** (programs with a verdict in both): S1 finds 259 programs SC calls Clean (232 race-free-labelled, 24 racy, 3 unlabelled) and misses 1 that SC finds (`P5-race_interblock_none-lock_rtraw`); S2 finds 261 and misses 0.
- **Step 3** (collector-only verdict layer on the hb-stripped scalar-clock recordings of the same programs): program-level violations (scalar-clock Race, collector-only not Race) **0 at S1, 0 at S2, 0 at cfg**; reverse programs 259 / 261 / 259 (collector-only Race, scalar-clock Clean); 3,702 scalar-clock pairs absent from the collector-only reports in 349 programs (certificate granted 3 pairs in P4, candidate missing 3,611, lane drop 88 in PI, other 0). Deviation, verbatim from step 3: the unmodified `sync_dominance.analyze` probes absent `hb_*` keys unguarded (153,786 probes per setting at 8 call sites, each returning the key-absent default), so "reads none" holds for values, not for probes (section 4.5).
- **False-report split** (RACE-class pc pairs of race-free-labelled programs that are Race; derived / rescued / async / atomic-chain-off / other): S1 347 pairs (29 / 12 / 0 / 0 / 306), S2 348 (29 / 12 / 0 / 1 / 306), C6 343 (25 / 12 / 0 / 0 / 306). Not in C1: S1 41 (29 / 12 / 0 / 0 / 0), S2 42 (29 / 12 / 0 / 1 / 0), C6 37. Not in SC: S1 322, S2 323, C6 318. Race-free-labelled programs that are Race: VC 20, SC 19, C1 248, C6 251, S1 251, S2 252 (section 2).
- **Closure bound, narrowest to widest** (C6 to S1/S2): programs with rescued > 0 532 to 687, programs with derived > 0 1,093 to 1,093; sum of derived 132,522 to 142,465, sum of rescued 11,793 to 25,197; pair-level, S1 against C6: 0 pairs lost, 87 gained (62 derived, 8 rescued, 1 async, 16 atomic-chain-off) in 49 programs (section 3.2).
- **Cost** (CAP_84600 section 3 rule, 4,685-program set; run alone / verdict step / end-to-end): VC 7.320 / 2.454 / 9.966; SC 7.015 / 2.173 / **9.339**; C1 5.564 / 2.098 / 7.773; C6 5.564 / 2.242 (A5-class estimate; 1.860 as measured on EPYC) / 7.923 (7.550); **S1 5.564 / 3.280 / 8.988; S2 5.564 / 3.143 / 8.851** (S1/S2 analysis_s measured on c14, which a same-node re-time on c19 finds 15 to 17 % slower than another node of the same class; scaled to c19's level the estimates are 3.036 / 8.733 and 2.845 / 8.541; section 5.1). On one node the rules cost 1.041 (S1) and 1.056 (S2) times C1's rules in the verdict step.

## 1. Tables (six cuVein columns)

Method (C6's, `c6_stage.sh`): `c6b_stage.sh` builds a sandbox of `eval/results` in which the `baselines-cuvein*.csv` are the paper's current state (eval/cap-84600: VC and SC; C1's collector-only run with the atomicCAS re-analysis; iGUARD; racecheck) plus the rows of C6 (`eval/co-chain/merged`, mode renamed `collector-only-chain`) and of S1 and S2 (`merged-s1`, `merged-s2`, modes `collector-only-s1` / `-s2`), and a **copy of the tracked `make_tables.py`**. C6 patched that copy (`--co-chain`, C4's patch) to add one mode; here the copy is unpatched, because `make_tables.load_runs()` passes mode names through unchanged and the wrapper `c6b_tables.py` takes the three extra modes from the CSVs itself (the same functions, `report_classes`, `race_alone_verdict`, `effective_verdict`, `load_manifest`, decide every verdict). The tracked `make_tables.py` is untouched. The one thing C6's patch did beyond naming was to keep its rows out of the native-wall denominators; `c6b_cost.py` does the same by dropping the C6/S1/S2 rows before calling `make_tables._ratios`. Every VC and SC cell recomputes to the paper's value (check at the end of the section); C1's aggregate recomputes to 485/486 against the paper's 486/486 (the one racy cuHadron program C1 misses is `P6-memcpy-shared_readwrite_race-racy`, `CO_CHAIN.md` section 2.1; S1 and S2 detect it).

### Table 3 (tab:eval-accuracy): accuracy per suite, data races alone, Indigo 1.3 counted per code, six cuVein columns

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

### Accuracy per program-input (Indigo 1.3 counted per run), six columns

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

### tab:eval-accuracy-union and tab:eval-countings: the three countings, six columns (per program-input)

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

### tab:eval-litmus: the 33 ScoR litmus kernels, six columns

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

### Program level


#### Program level: S1 against C6

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

#### Program level: S2 against C6

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

#### Program level: S1 against C1

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

#### Program level: S2 against C1

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

#### Program level: S1 against scalar-clock

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

#### Program level: S2 against scalar-clock

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

#### Program level: S2 against S1

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

### Indigo 1.3 per program-input against the input-level oracle (baselines-pi-oracle.csv)

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

### Check against the paper (vector-clock and scalar-clock cells)

Every vector-clock and scalar-clock cell of the per-program-input accuracy table, the union and three-countings tables and the litmus table recomputes to the paper's value.



## 2. False reports: the split by how the verdict step found them

Race-free-labelled programs that are Race (races alone): VC 20, SC 19, C1 248, C6 251, **S1 251, S2 252** (table at the end of section 1). Unit and classes below; the tables follow C6's section 4 (per suite and label, reports not in C1 and not in scalar-clock) and add the C6 reference column and the two new classes.

Programs with a confirm JSON: C6 4709, S1 4709, S2 4709
Programs whose CSV report_ids hold fewer pairs than reports_dedup (pair sets cut by the CSV): scalar-clock 0, C1 0, C6 0, S1 0, S2 0
Check C6: programs Race with a confirm JSON 2927; race-class raw pair set differs from the CSV report_ids in 0.
Check S1: programs Race with a confirm JSON 2928; race-class raw pair set differs from the CSV report_ids in 0.
Check S2: programs Race with a confirm JSON 2931; race-class raw pair set differs from the CSV report_ids in 0.


Definitions (record = one entry of the confirm JSON's `raw`; pair = deduped (space, pc, pc)):
- **derived**: `chain_src` = `chain`: no recorded edge joins the pair, only a chain of reads (the closure's own pair).
- **rescued**: `chain_src` = `chain_rescue`: an edge whose own distance is thread-local (or narrower than the chain's) judged at the chain's widest bound.
- **async**: `async` = true: the cp.async cross-agent rule (`--co-async`): an edge with a same-thread instance whose earlier access is a `LDGSTS` copy and whose later access is not, unless an unguarded `DEPBAR.LE SB0, 0x0` lies on every CFG path between them; judged at no narrower than warp, with no R1/R3 credit.
- **atomic-chain-off**: `atomic_chain_off` = true: the region-dominance certificate (R3, the PC-level atomic hand-off chain) that `--co-r3 cfg` grants was withheld (S1 strict: R3 must also find a chain with scalar-clock's CFG-decidable declines; S2 off: no R3 certificate), so the pair is reported where cfg orders it.
- **other**: none of the four: an ordinary edge or event record.
Precedence for a record: atomic-chain-off, async, derived, rescued, other. A pair has the least special class among its records (a pair that an ordinary record also reports is `other`). C6's confirm JSONs predate the async / atomic_chain_off tags (they count as false), so for C6 only derived / rescued / other occur.


#### C6: reports (RACE-class pc pairs) of the programs that are Race, split by class, per suite and label

Programs counted: those Race in C6 (races alone). Columns: pairs in all / of them not in C1 / not in C6 / not in scalar-clock, each split into derived / rescued / async / atomic-chain-off / other (definitions above the tables).

| suite | label | programs | all: total | derived | rescued | async | atomic_chain_off | other | not in C1: total | derived | rescued | async | atomic_chain_off | other | not in scalar-clock: total | derived | rescued | async | atomic_chain_off | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | racy | 200 | 1522 | 328 | 46 | 0 | 0 | 1148 | 374 | 328 | 46 | 0 | 0 | 0 | 228 | 153 | 16 | 0 | 0 | 59 |
| Indigo 1.3 (PI) | racy | 1738 | 8680 | 1764 | 204 | 0 | 0 | 6712 | 1968 | 1764 | 204 | 0 | 0 | 0 | 843 | 149 | 14 | 0 | 0 | 680 |
| Indigo 1.3 (PI) | race-free | 224 | 240 | 16 | 0 | 0 | 0 | 224 | 16 | 16 | 0 | 0 | 0 | 0 | 240 | 16 | 0 | 0 | 0 | 224 |
| Indigo 1.3 (PI) | unlabelled | 706 | 5193 | 2051 | 181 | 0 | 0 | 2961 | 2232 | 2051 | 181 | 0 | 0 | 0 | 404 | 279 | 102 | 0 | 0 | 23 |
| ECL (P3) | race-free | 16 | 44 | 0 | 8 | 0 | 0 | 36 | 8 | 0 | 8 | 0 | 0 | 0 | 28 | 0 | 8 | 0 | 0 | 20 |
| ScoR apps (P4) | racy | 14 | 111 | 25 | 4 | 0 | 0 | 82 | 29 | 25 | 4 | 0 | 0 | 0 | 47 | 25 | 4 | 0 | 0 | 18 |
| ScoR apps (P4) | race-free | 8 | 37 | 3 | 4 | 0 | 0 | 30 | 7 | 3 | 4 | 0 | 0 | 0 | 37 | 3 | 4 | 0 | 0 | 30 |
| ScoR litmus (P5) | racy | 2 | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | racy | 6 | 93 | 79 | 0 | 0 | 0 | 14 | 79 | 79 | 0 | 0 | 0 | 0 | 80 | 79 | 0 | 0 | 0 | 1 |
| cuHadron (P6) | race-free | 1 | 9 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | unlabelled | 7 | 72 | 5 | 1 | 0 | 0 | 66 | 6 | 5 | 1 | 0 | 0 | 0 | 7 | 5 | 0 | 0 | 0 | 2 |
| HeCBench SC 10 (P9) | racy | 3 | 118 | 67 | 6 | 0 | 0 | 45 | 73 | 67 | 6 | 0 | 0 | 0 | 73 | 63 | 0 | 0 | 0 | 10 |
| HeCBench SC 10 (P9) | race-free | 2 | 13 | 6 | 0 | 0 | 0 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 13 | 6 | 0 | 0 | 0 | 7 |
| **all** | **racy** | 1963 | 10527 | 2263 | 260 | 0 | 0 | 8004 | 2523 | 2263 | 260 | 0 | 0 | 0 | 1271 | 469 | 34 | 0 | 0 | 768 |
| **all** | **race-free** | 251 | 343 | 25 | 12 | 0 | 0 | 306 | 37 | 25 | 12 | 0 | 0 | 0 | 318 | 25 | 12 | 0 | 0 | 281 |
| **all** | **unlabelled** | 713 | 5265 | 2056 | 182 | 0 | 0 | 3027 | 2238 | 2056 | 182 | 0 | 0 | 0 | 411 | 284 | 102 | 0 | 0 | 25 |
| **all** | **ALL** | 2927 | 16135 | 4344 | 454 | 0 | 0 | 11337 | 4798 | 4344 | 454 | 0 | 0 | 0 | 2000 | 778 | 148 | 0 | 0 | 1074 |

Race-free-labelled programs, C6: all reports: 343 (derived 25, rescued 12, async 0, atomic_chain_off 0, other 306); not in C1: 37 (derived 25, rescued 12, async 0, atomic_chain_off 0, other 0); not in scalar-clock: 318 (derived 25, rescued 12, async 0, atomic_chain_off 0, other 281)

Record-level tag counts for C6 (not exclusive; pairs with the tag on their chosen record): pairs 16135, chain_src=chain 4344, chain_src=chain_rescue 454, async 0, atomic_chain_off 0.
Strong-conflict-class pairs (raw_sc) of the Race programs, C6: 197 (derived 81, rescued 6, async 0, atomic_chain_off 0, other 110)

#### S1: reports (RACE-class pc pairs) of the programs that are Race, split by class, per suite and label

Programs counted: those Race in S1 (races alone). Columns: pairs in all / of them not in C1 / not in C6 / not in scalar-clock, each split into derived / rescued / async / atomic-chain-off / other (definitions above the tables).

| suite | label | programs | all: total | derived | rescued | async | atomic_chain_off | other | not in C1: total | derived | rescued | async | atomic_chain_off | other | not in C6: total | derived | rescued | async | atomic_chain_off | other | not in scalar-clock: total | derived | rescued | async | atomic_chain_off | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | racy | 200 | 1522 | 328 | 97 | 0 | 0 | 1097 | 374 | 328 | 46 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 228 | 153 | 16 | 0 | 0 | 59 |
| Indigo 1.3 (PI) | racy | 1738 | 8723 | 1799 | 331 | 0 | 0 | 6593 | 2011 | 1799 | 212 | 0 | 0 | 0 | 43 | 35 | 8 | 0 | 0 | 0 | 864 | 162 | 25 | 0 | 0 | 677 |
| Indigo 1.3 (PI) | race-free | 224 | 240 | 16 | 0 | 0 | 0 | 224 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 240 | 16 | 0 | 0 | 0 | 224 |
| Indigo 1.3 (PI) | unlabelled | 706 | 5202 | 2060 | 253 | 0 | 0 | 2889 | 2241 | 2060 | 181 | 0 | 0 | 0 | 9 | 9 | 0 | 0 | 0 | 0 | 405 | 280 | 102 | 0 | 0 | 23 |
| ECL (P3) | race-free | 16 | 44 | 0 | 8 | 0 | 0 | 36 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 28 | 0 | 8 | 0 | 0 | 20 |
| ScoR apps (P4) | racy | 14 | 131 | 29 | 4 | 0 | 16 | 82 | 49 | 29 | 4 | 0 | 16 | 0 | 20 | 4 | 0 | 0 | 16 | 0 | 67 | 29 | 4 | 0 | 16 | 18 |
| ScoR apps (P4) | race-free | 8 | 41 | 7 | 4 | 0 | 0 | 30 | 11 | 7 | 4 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 41 | 7 | 4 | 0 | 0 | 30 |
| ScoR litmus (P5) | racy | 2 | 3 | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | racy | 7 | 94 | 79 | 0 | 1 | 0 | 14 | 80 | 79 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 80 | 79 | 0 | 0 | 0 | 1 |
| cuHadron (P6) | race-free | 1 | 9 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | unlabelled | 7 | 73 | 6 | 1 | 0 | 0 | 66 | 7 | 6 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 8 | 6 | 0 | 0 | 0 | 2 |
| HeCBench SC 10 (P9) | racy | 3 | 127 | 76 | 10 | 0 | 0 | 41 | 82 | 76 | 6 | 0 | 0 | 0 | 9 | 9 | 0 | 0 | 0 | 0 | 78 | 68 | 4 | 0 | 0 | 6 |
| HeCBench SC 10 (P9) | race-free | 2 | 13 | 6 | 0 | 0 | 0 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 6 | 0 | 0 | 0 | 7 |
| **all** | **racy** | 1964 | 10600 | 2311 | 442 | 1 | 16 | 7830 | 2596 | 2311 | 268 | 1 | 16 | 0 | 73 | 48 | 8 | 1 | 16 | 0 | 1317 | 491 | 49 | 0 | 16 | 761 |
| **all** | **race-free** | 251 | 347 | 29 | 12 | 0 | 0 | 306 | 41 | 29 | 12 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 322 | 29 | 12 | 0 | 0 | 281 |
| **all** | **unlabelled** | 713 | 5275 | 2066 | 254 | 0 | 0 | 2955 | 2248 | 2066 | 182 | 0 | 0 | 0 | 10 | 10 | 0 | 0 | 0 | 0 | 413 | 286 | 102 | 0 | 0 | 25 |
| **all** | **ALL** | 2928 | 16222 | 4406 | 708 | 1 | 16 | 11091 | 4885 | 4406 | 462 | 1 | 16 | 0 | 87 | 62 | 8 | 1 | 16 | 0 | 2052 | 806 | 163 | 0 | 16 | 1067 |

Race-free-labelled programs, S1: all reports: 347 (derived 29, rescued 12, async 0, atomic_chain_off 0, other 306); not in C1: 41 (derived 29, rescued 12, async 0, atomic_chain_off 0, other 0); not in C6: 4 (derived 4, rescued 0, async 0, atomic_chain_off 0, other 0); not in scalar-clock: 322 (derived 29, rescued 12, async 0, atomic_chain_off 0, other 281)

Record-level tag counts for S1 (not exclusive; pairs with the tag on their chosen record): pairs 16222, chain_src=chain 4406, chain_src=chain_rescue 708, async 1, atomic_chain_off 16.
Strong-conflict-class pairs (raw_sc) of the Race programs, S1: 305 (derived 79, rescued 10, async 0, atomic_chain_off 108, other 108)

#### S2: reports (RACE-class pc pairs) of the programs that are Race, split by class, per suite and label

Programs counted: those Race in S2 (races alone). Columns: pairs in all / of them not in C1 / not in C6 / not in scalar-clock, each split into derived / rescued / async / atomic-chain-off / other (definitions above the tables).

| suite | label | programs | all: total | derived | rescued | async | atomic_chain_off | other | not in C1: total | derived | rescued | async | atomic_chain_off | other | not in C6: total | derived | rescued | async | atomic_chain_off | other | not in scalar-clock: total | derived | rescued | async | atomic_chain_off | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | racy | 200 | 1522 | 328 | 97 | 0 | 0 | 1097 | 374 | 328 | 46 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 228 | 153 | 16 | 0 | 0 | 59 |
| Indigo 1.3 (PI) | racy | 1738 | 8723 | 1799 | 331 | 0 | 0 | 6593 | 2011 | 1799 | 212 | 0 | 0 | 0 | 43 | 35 | 8 | 0 | 0 | 0 | 864 | 162 | 25 | 0 | 0 | 677 |
| Indigo 1.3 (PI) | race-free | 224 | 240 | 16 | 0 | 0 | 0 | 224 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 240 | 16 | 0 | 0 | 0 | 224 |
| Indigo 1.3 (PI) | unlabelled | 706 | 5203 | 2060 | 253 | 0 | 1 | 2889 | 2242 | 2060 | 181 | 0 | 1 | 0 | 10 | 9 | 0 | 0 | 1 | 0 | 406 | 280 | 102 | 0 | 1 | 23 |
| ECL (P3) | race-free | 16 | 44 | 0 | 8 | 0 | 0 | 36 | 8 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 28 | 0 | 8 | 0 | 0 | 20 |
| ScoR apps (P4) | racy | 14 | 131 | 29 | 4 | 0 | 16 | 82 | 49 | 29 | 4 | 0 | 16 | 0 | 20 | 4 | 0 | 0 | 16 | 0 | 67 | 29 | 4 | 0 | 16 | 18 |
| ScoR apps (P4) | race-free | 8 | 41 | 7 | 4 | 0 | 0 | 30 | 11 | 7 | 4 | 0 | 0 | 0 | 4 | 4 | 0 | 0 | 0 | 0 | 41 | 7 | 4 | 0 | 0 | 30 |
| ScoR litmus (P5) | racy | 4 | 5 | 0 | 0 | 0 | 2 | 3 | 2 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| ScoR litmus (P5) | race-free | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| cuHadron (P6) | racy | 7 | 94 | 79 | 0 | 1 | 0 | 14 | 80 | 79 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 80 | 79 | 0 | 0 | 0 | 1 |
| cuHadron (P6) | race-free | 1 | 9 | 0 | 0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | unlabelled | 7 | 73 | 6 | 1 | 0 | 0 | 66 | 7 | 6 | 1 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 8 | 6 | 0 | 0 | 0 | 2 |
| HeCBench SC 10 (P9) | racy | 3 | 127 | 76 | 10 | 0 | 0 | 41 | 82 | 76 | 6 | 0 | 0 | 0 | 9 | 9 | 0 | 0 | 0 | 0 | 78 | 68 | 4 | 0 | 0 | 6 |
| HeCBench SC 10 (P9) | race-free | 2 | 13 | 6 | 0 | 0 | 0 | 7 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 | 6 | 0 | 0 | 0 | 7 |
| **all** | **racy** | 1966 | 10602 | 2311 | 442 | 1 | 18 | 7830 | 2598 | 2311 | 268 | 1 | 18 | 0 | 75 | 48 | 8 | 1 | 18 | 0 | 1318 | 491 | 49 | 0 | 17 | 761 |
| **all** | **race-free** | 252 | 348 | 29 | 12 | 0 | 1 | 306 | 42 | 29 | 12 | 0 | 1 | 0 | 5 | 4 | 0 | 0 | 1 | 0 | 323 | 29 | 12 | 0 | 1 | 281 |
| **all** | **unlabelled** | 713 | 5276 | 2066 | 254 | 0 | 1 | 2955 | 2249 | 2066 | 182 | 0 | 1 | 0 | 11 | 10 | 0 | 0 | 1 | 0 | 414 | 286 | 102 | 0 | 1 | 25 |
| **all** | **ALL** | 2931 | 16226 | 4406 | 708 | 1 | 20 | 11091 | 4889 | 4406 | 462 | 1 | 20 | 0 | 91 | 62 | 8 | 1 | 20 | 0 | 2055 | 806 | 163 | 0 | 19 | 1067 |

Race-free-labelled programs, S2: all reports: 348 (derived 29, rescued 12, async 0, atomic_chain_off 1, other 306); not in C1: 42 (derived 29, rescued 12, async 0, atomic_chain_off 1, other 0); not in C6: 5 (derived 4, rescued 0, async 0, atomic_chain_off 1, other 0); not in scalar-clock: 323 (derived 29, rescued 12, async 0, atomic_chain_off 1, other 281)

Record-level tag counts for S2 (not exclusive; pairs with the tag on their chosen record): pairs 16226, chain_src=chain 4407, chain_src=chain_rescue 708, async 1, atomic_chain_off 20.
Strong-conflict-class pairs (raw_sc) of the Race programs, S2: 326 (derived 80, rescued 10, async 0, atomic_chain_off 128, other 108)



Reading (race-free-labelled programs only, pairs):

- Against C1, every pair S1 adds is the closure's: 41 = 29 derived + 12 rescued + 0 async + 0 atomic-chain-off + 0 other (C6: 37 = 25 + 12). S2 adds one more, an atomic-chain-off pair (42). The four extra derived pairs over C6 are all in ScoR applications (P4, race-free-labelled); the S2-only pair is `P5-norace_interwarp-block_fence-atom_hrd-indirect` (shared:0x2d0-0x3f0), the litmus kernel S2 turns Race (section 3.1); Table 3 does not contain the litmus rows, so its FP cells do not move, but the litmus FP cell does (S2 1/14 against 0/14, per-input table).
- Against scalar-clock, 281 pairs are `other` in all three (ordinary edge reports C1 already has and SC's frontier does not); the derived and rescued counts are the same as against C1.
- The async rule adds 1 pair (cuHadron, racy-labelled `P6-memcpy-shared_readwrite_race-racy`, shared:0x70-0x90) and no pair on a race-free-labelled program. The atomic-chain-off rule adds 16 pairs in S1 (all in P4 racy-labelled programs, which were Race in C6) and 20 in S2 (the 16, the 3 P5 pairs and 1 unlabelled Indigo 1.3 pair); 1 of the 20 is on a race-free-labelled program.
- Strong-conflict-class pairs are tabulated per setting under each table (S1 305 pairs, 108 of them atomic-chain-off; S2 326, 128; C6 197): `strong` countings move accordingly (section 1: ScoR applications strong 8/14 · 6/14 in S1 and 8/14 · 8/14 in S2 against C6's 6/14 · 4/14; S2 litmus strong FP 7/14).

## 3. What moved against C6

### 3.1 Verdict changes

Program level, S1 and S2 against C6 and C1 (tables in section 1, "Program level"); tags of the records that cause the changes (from the confirm JSONs):


#### Verdict changes against C6 (races alone), with the tags of the records that cause them

| setting | suite | program | label | C6 | S | reports C6 -> S | pairs of S not in C6 (class) | pairs of C6 not in S |
|---|---|---|---|---|---|---|---|---|
| S1 | P6 | `P6-memcpy-shared_readwrite_race-racy` | racy | CLEAN | RACE | 0 -> 1 | shared:0x70-0x90 (async) |  |
| S2 | P5 | `P5-canary` | racy | CLEAN | RACE | 0 -> 1 | global:0x160-0x1f0 (atomic_chain_off) |  |
| S2 | P5 | `P5-norace_interwarp-block_fence-atom_hrd-indirect` | race-free | CLEAN | RACE | 0 -> 1 | shared:0x2d0-0x3f0 (atomic_chain_off) |  |
| S2 | P5 | `P5-race_interblock_none-lock_rtraw` | racy | CLEAN | RACE | 0 -> 1 | global:0x170-0x2f0 (atomic_chain_off) |  |
| S2 | P6 | `P6-memcpy-shared_readwrite_race-racy` | racy | CLEAN | RACE | 0 -> 1 | shared:0x70-0x90 (async) |  |

Programs whose verdict changed against C6, per suite: S1: P6 1 (total 1); S2: P5 3, P6 1 (total 4)



Causes:

- **S1, `P6-memcpy-shared_readwrite_race-racy` (async).** The kernel does a `LDGSTS` (the async global-to-shared copy) at 0x70, reads the destination with `LDS` at 0x90 and waits only afterwards (`DEPBAR.LE SB0, 0x0` at 0xa0): C6's report of this program is `CO_CHAIN.md` section 3.2 (case F4 of `eval/FIX_REPORT.md`). `--co-async` treats a `LDGSTS` pc's accesses as the issuing thread's async agent's: an edge with a same-thread instance (`intra_thread` > 0) whose earlier access is a copy and whose later access is not is a cross-agent candidate, judged at no narrower than warp with no R1/R3 credit, unless an unguarded `DEPBAR.LE SB0, 0x0` lies on every CFG path from the copy to the later access (`HBGraph.async_waited`; a wait with a non-zero count never orders it). The record is tagged `async`: the raw record `shared:0x70-0x90` in S1 and S2, nothing in C6.
- **S2, three P5 programs (atomic_chain_off).** `--co-r3 off` withholds the PC-level atomic hand-off certificate (R3) that cfg grants; `--co-r3 strict` keeps it only where R3 also finds a chain with scalar-clock's CFG-decidable declines (the landing check of `_past_release` and the write-before-lock check of `_before_acquire`, decided on the CFG alone, the location condition taken as true). The three records, all `atomic_chain_off`: `P5-canary` global:0x160-0x1f0 WAW, `P5-race_interblock_none-lock_rtraw` global:0x170-0x2f0 WAW, `P5-norace_interwarp-block_fence-atom_hrd-indirect` shared:0x2d0-0x3f0. In S1 none of the three is reported: no record carries the tag, i.e. the strict certificate was not withheld. Labels: canary racy, lock_rtraw racy, `...hrd-indirect` race-free (a false report of S2; scalar-clock reports none, VC reports Race on it).
- Programs with atomic_chain_off records (any class) in the notes: S1 6 (P4), S2 24 (P4 12, P5 11, PI 1); their Race-class pairs are the 16 and 20 above, the rest are strong-conflict-class pairs.

### 3.2 Narrowest against widest closure bound (C6 to S1/S2)

C6 judged a derived pair at the narrowest bound over all chains of reads (a minimax); C6b judges every edge at max(its own widest distance, the widest hop over every such chain), so an edge whose chain bound is wider than its own distance is a rescue (C6: only edges whose own distance was thread-local). Counts below are the notes' `chain_derived` / `chain_rescued` (rep 1, one row per program) and the pairs of the confirm JSONs:

#### Pair-level moves against C6 (RACE-class pc pairs, programs Race in either)

Per suite: pairs only in S (gained), by the class of the gained pair in S; pairs only in C6 (lost), by C6's class (derived / rescued / other); programs with any move; programs whose verdict is the same in both but whose pair set moved.


**S1 against C6**

| suite | programs compared | programs with a pair move | of them, same verdict | pairs in both | gained | gained: derived | rescued | async | atomic-chain-off | other | lost | lost: derived | rescued | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0 | 0 | 1522 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 4130 | 40 | 40 | 14113 | 52 | 44 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 0 | 0 | 44 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 6 | 6 | 148 | 24 | 8 | 0 | 0 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR litmus (P5) | 33 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 34 | 1 | 0 | 102 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 1 | 1 | 72 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 10 | 1 | 1 | 131 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **all** | 4709 | 49 | 48 | 16135 | 87 | 62 | 8 | 1 | 16 | 0 | 0 | 0 | 0 | 0 |

**S2 against C6**

| suite | programs compared | programs with a pair move | of them, same verdict | pairs in both | gained | gained: derived | rescued | async | atomic-chain-off | other | lost | lost: derived | rescued | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0 | 0 | 1522 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 4130 | 41 | 41 | 14113 | 53 | 44 | 8 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 0 | 0 | 44 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 6 | 6 | 148 | 24 | 8 | 0 | 0 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR litmus (P5) | 33 | 3 | 0 | 3 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 34 | 1 | 0 | 102 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 1 | 1 | 72 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 10 | 1 | 1 | 131 | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **all** | 4709 | 53 | 49 | 16135 | 91 | 62 | 8 | 1 | 20 | 0 | 0 | 0 | 0 | 0 |

#### Derived and rescued counts, narrowest bound (C6) against widest bound (S1, S2)

Programs with chain_derived > 0 / chain_rescued > 0 and the sums of the per-program counts (notes `chain_derived`, `chain_rescued`, one row per program: rep 1), per suite. A derived pair is a pair no edge joins; a rescued one is an edge judged at its chain's bound (C6: edges whose own distance was thread-local; C6b: every edge whose chain bound is wider than its own distance).

| suite | programs | C6 derived>0 | S1 | S2 | C6 rescued>0 | S1 | S2 | C6 sum derived | S1 | S2 | C6 sum rescued | S1 | S2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 172 | 172 | 172 | 138 | 173 | 173 | 6656 | 6671 | 6671 | 877 | 2292 | 2292 |
| Indigo 1.3 (PI) | 4130 | 861 | 861 | 861 | 359 | 472 | 472 | 5532 | 5604 | 5604 | 550 | 818 | 818 |
| ECL (P3) | 60 | 20 | 20 | 20 | 15 | 22 | 22 | 148 | 148 | 148 | 147 | 213 | 213 |
| ScoR apps (P4) | 28 | 24 | 24 | 24 | 10 | 10 | 10 | 5576 | 5590 | 5590 | 244 | 316 | 316 |
| ScoR litmus (P5) | 33 | 3 | 3 | 3 | 0 | 0 | 0 | 4 | 4 | 4 | 0 | 0 | 0 |
| cuHadron (P6) | 34 | 1 | 1 | 1 | 2 | 2 | 2 | 159 | 159 | 159 | 2 | 2 | 2 |
| HeCBench other 14 (P7) | 14 | 7 | 7 | 7 | 5 | 5 | 5 | 56089 | 56098 | 56098 | 2080 | 9383 | 9383 |
| HeCBench SC 10 (P9) | 10 | 5 | 5 | 5 | 3 | 3 | 3 | 58358 | 68191 | 68191 | 7893 | 12173 | 12173 |
| **all** | 4709 | 1093 | 1093 | 1093 | 532 | 687 | 687 | 132522 | 142465 | 142465 | 11793 | 25197 | 25197 |

Programs by change of the per-program count against C6: S1 derived same 4632; S1 derived up 77; S1 rescued same 4393; S1 rescued up 316; S2 derived same 4632; S2 derived up 77; S2 rescued same 4393; S2 rescued up 316



- The widening adds rescues (programs with rescued > 0: 532 to 687; sum of rescued 11,793 to 25,197) and almost no derived pairs (programs 1,093 to 1,093; sum 132,522 to 142,465, +9,943, of which 9,833 in P9 and 9 in P7: the two HeCBench suites; the rest 101 over P1, PI, P4). The per-program counts against C6: derived up in 77 programs, rescued up in 316, none down.
- At pair level the widening only adds: S1 against C6 loses 0 pairs and gains 87 (62 derived, 8 rescued, 1 async, 16 atomic-chain-off) in 49 programs; 48 of them keep their verdict (PI 40, P4 6, P7 1, P9 1), the 49th is the `async` P6 program. S2 gains 91 (S1's plus 3 P5 and 1 PI atomic-chain-off pairs) in 53 programs, 49 with the same verdict. No program loses a Race verdict; no pair of C6 disappears.
- Race-free-labelled programs: the four derived pairs C6 does not have are in P4 (race-free-labelled, already Race in C6).

### 3.3 `lock_rtraw` and `matrix-multiplication-norace`

#### lock_rtraw and matrix-multiplication-norace in every setting

Cells: races-alone verdict; reports (Race-class pairs); `classes=` of the notes; the RACE-class and strong-class pairs of the confirm JSON with their tags (src = chain_src; A = async, O = atomic_chain_off).

| program | label | mode | verdict | reports | classes | RACE-class pairs (src, tags) | strong-class pairs (src, tags) |
|---|---|---|---|---|---|---|---|
| `P4-matrix-multiplication-norace-large` | race-free | scalar-clock | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-large` | race-free | C1 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-large` | race-free | C6 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-large` | race-free | S1 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-large` | race-free | S2 | CLEAN | 0 | sc:6 |  | global:0x590-0x5a0 (RAW, edge, O), global:0x5a0-0x5a0 (WAW, chain, O), global:0x960-0x980 (RAW, edge, O), global:0x980-0x980 (WAW, chain, O), global:0xb80-0xbb0 (RAW, edge, O), global:0xbb0-0xbb0 (WAW, chain, O) |
| `P4-matrix-multiplication-norace-small` | race-free | scalar-clock | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-small` | race-free | C1 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-small` | race-free | C6 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-small` | race-free | S1 | CLEAN | 0 |  |  |  |
| `P4-matrix-multiplication-norace-small` | race-free | S2 | CLEAN | 0 | sc:4 |  | global:0x590-0x5a0 (RAW, edge, O), global:0x5a0-0x5a0 (WAW, chain, O), global:0x960-0x980 (RAW, edge, O), global:0x980-0x980 (WAW, chain, O) |
| `P5-race_interblock_none-lock_rtraw` | racy | scalar-clock | RACE | 1 | race:1,sc:1 | global:0x170-0x2f0 |  |
| `P5-race_interblock_none-lock_rtraw` | racy | C1 | CLEAN | 0 |  |  |  |
| `P5-race_interblock_none-lock_rtraw` | racy | C6 | CLEAN | 0 | sc:1 |  | global:0x140-0x340 (WAR, chain) |
| `P5-race_interblock_none-lock_rtraw` | racy | S1 | CLEAN | 0 | sc:1 |  | global:0x140-0x340 (WAR, chain) |
| `P5-race_interblock_none-lock_rtraw` | racy | S2 | RACE | 1 | race:1,sc:1 | global:0x170-0x2f0 (WAW, edge, O) | global:0x140-0x340 (WAR, chain) |


- `P5-race_interblock_none-lock_rtraw`: SC reports `global:0x170-0x2f0` (WAW) as Race. C1 reports nothing; C6 orders that pair by the R3 chain 0x1b0 to 0x230 (`results/co-chain-b/step0/rtraw.md`) and reports only the strong-conflict pair 0x140/0x340 (WAR, derived). **S1 still orders the recorded pair**: no raw record for it, `classes=sc:1`, verdict Clean (Strong in the litmus table), the same as C6. **S2 reports it**: the Race-class record `global:0x170-0x2f0` WAW, source `edge`, tagged `atomic_chain_off`, plus the same 0x140/0x340 strong pair; verdict Race, litmus Race, as SC. Step 0's caveat stands: SC's recording has `0x330 <- 0x1b0` where the collector-only recording has `0x230 <- 0x1b0`, so the S2 report agrees with SC's verdict on a different recording and for a different reason (certificate withheld, not an edge that fails to land).
- `P4-matrix-multiplication-norace-small` and `-large` (race-free): Clean (Race alone) in SC, C1, C6, S1 and S2. S1 has no record. S2 has strong-conflict-class records only, all tagged `atomic_chain_off` (4 pairs in `-small`, 6 in `-large`, the `classes=` of the notes `sc:4` / `sc:6`), so the races-alone verdict does not move and the `strong` counting can (S2's ScoR-applications strong FP cell is 8/14 against S1's 6/14; these two race-free-labelled programs are among the programs with strong-class records in S2 only).

## 4. Step 3: the collector-only verdict layer on the hb-stripped scalar-clock recordings

Question: on the same recording, is every program that scalar-clock mode reports Race also Race in collector-only mode? Input: the scalar-clock kernel JSONs of X1b's `final-2026-11-view` (4,725 ids) with every `hb_*` key deleted (`c6b_s3_strip.py`), analysed by the unmodified `parallel.py analyze` in collector-only mode at three settings (S1, S2, cfg: `--chain-closure --co-async --co-r3 cfg`, C6's R3 with the widest bound and async). Scalar-clock verdicts: the scalar-clock rows of `eval/results/final-b/merged`. Method, jobs and the 8 ids re-run after a metadata mismatch are in `results/co-chain-b/step3/step3_summary.md`; its result, reproduced here by `c6b_step3_frag.py` from the committed TSVs:

### 4.1 Per-suite tables (step 3's own, unchanged)

Source: `results/co-chain-b/step3/step3_summary.md`. Violation = scalar-clock Race and collector-only not Race, on the same programs (scalar-clock recordings with every `hb_*` key deleted, run through the unmodified `parallel.py analyze` in collector-only mode). Reverse = collector-only Race and scalar-clock not Race.

#### Setting s1 (`--chain-closure --co-async --co-r3 strict`)

16 shard CSVs, 14131 rows. collector-only verdicts: CLEAN 1778, NONE 16, RACE 2929, TIMEOUT 2

| suite | programs | sc=Race | co=Race | both Race | violations | candidate missing | certificate granted | collector lane drop | other | reverse (co Race, sc not) | of which sc CLEAN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 200 | 200 | 200 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 16 | 22 | 16 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| ScoR litmus (P5) | 33 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 50 | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 4 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| HeCBench SC 10 (P9) | 10 | 3 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| Indigo 1.3 (PI) | 4130 | 2420 | 2668 | 2420 | 0 | 0 | 0 | 0 | 0 | 248 | 248 |
| HeCBench (P7+P9) | 24 | 7 | 12 | 7 | 0 | 0 | 0 | 0 | 0 | 5 | 5 |
| ALL | 4725 | 2670 | 2929 | 2670 | 0 | 0 | 0 | 0 | 0 | 259 | 259 |


Pairs (information only): sc pairs found in co / missing, by cause class of the missing ones (all sc=Race programs):

| suite | programs | sc pairs | found in co | missing | certificate granted | candidate missing | lane drop | other |
|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 200 | 1294 | 1294 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 16 | 77 | 63 | 14 | 3 | 11 | 0 | 0 |
| ScoR litmus (P5) | 3 | 5 | 4 | 1 | 0 | 1 | 0 | 0 |
| cuHadron (P6) | 8 | 94 | 24 | 70 | 0 | 70 | 0 | 0 |
| HeCBench other 14 (P7) | 4 | 65 | 65 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 3 | 49 | 49 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 2420 | 16538 | 12921 | 3617 | 0 | 3529 | 88 | 0 |
| ALL | 2670 | 18138 | 14436 | 3702 | 3 | 3611 | 88 | 0 |

#### Setting s2 (`--chain-closure --co-async --co-r3 off`)

16 shard CSVs, 14131 rows. collector-only verdicts: CLEAN 1776, NONE 16, RACE 2931, TIMEOUT 2

| suite | programs | sc=Race | co=Race | both Race | violations | candidate missing | certificate granted | collector lane drop | other | reverse (co Race, sc not) | of which sc CLEAN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 200 | 200 | 200 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 16 | 22 | 16 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| ScoR litmus (P5) | 33 | 3 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| cuHadron (P6) | 50 | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 4 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| HeCBench SC 10 (P9) | 10 | 3 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| Indigo 1.3 (PI) | 4130 | 2420 | 2668 | 2420 | 0 | 0 | 0 | 0 | 0 | 248 | 248 |
| HeCBench (P7+P9) | 24 | 7 | 12 | 7 | 0 | 0 | 0 | 0 | 0 | 5 | 5 |
| ALL | 4725 | 2670 | 2931 | 2670 | 0 | 0 | 0 | 0 | 0 | 261 | 261 |


Pairs (information only): sc pairs found in co / missing, by cause class of the missing ones (all sc=Race programs):

| suite | programs | sc pairs | found in co | missing | certificate granted | candidate missing | lane drop | other |
|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 200 | 1294 | 1294 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 16 | 77 | 63 | 14 | 3 | 11 | 0 | 0 |
| ScoR litmus (P5) | 3 | 5 | 4 | 1 | 0 | 1 | 0 | 0 |
| cuHadron (P6) | 8 | 94 | 24 | 70 | 0 | 70 | 0 | 0 |
| HeCBench other 14 (P7) | 4 | 65 | 65 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 3 | 49 | 49 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 2420 | 16538 | 12921 | 3617 | 0 | 3529 | 88 | 0 |
| ALL | 2670 | 18138 | 14436 | 3702 | 3 | 3611 | 88 | 0 |

#### Setting cfg (`--chain-closure --co-async --co-r3 cfg`)

16 shard CSVs, 14131 rows. collector-only verdicts: CLEAN 1778, NONE 16, RACE 2929, TIMEOUT 2

| suite | programs | sc=Race | co=Race | both Race | violations | candidate missing | certificate granted | collector lane drop | other | reverse (co Race, sc not) | of which sc CLEAN |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 200 | 200 | 200 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 60 | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 28 | 16 | 22 | 16 | 0 | 0 | 0 | 0 | 0 | 6 | 6 |
| ScoR litmus (P5) | 33 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron (P6) | 50 | 8 | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench other 14 (P7) | 14 | 4 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 3 | 3 |
| HeCBench SC 10 (P9) | 10 | 3 | 5 | 3 | 0 | 0 | 0 | 0 | 0 | 2 | 2 |
| Indigo 1.3 (PI) | 4130 | 2420 | 2668 | 2420 | 0 | 0 | 0 | 0 | 0 | 248 | 248 |
| HeCBench (P7+P9) | 24 | 7 | 12 | 7 | 0 | 0 | 0 | 0 | 0 | 5 | 5 |
| ALL | 4725 | 2670 | 2929 | 2670 | 0 | 0 | 0 | 0 | 0 | 259 | 259 |


Pairs (information only): sc pairs found in co / missing, by cause class of the missing ones (all sc=Race programs):

| suite | programs | sc pairs | found in co | missing | certificate granted | candidate missing | lane drop | other |
|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 200 | 1294 | 1294 | 0 | 0 | 0 | 0 | 0 |
| ECL (P3) | 16 | 16 | 16 | 0 | 0 | 0 | 0 | 0 |
| ScoR apps (P4) | 16 | 77 | 63 | 14 | 3 | 11 | 0 | 0 |
| ScoR litmus (P5) | 3 | 5 | 4 | 1 | 0 | 1 | 0 | 0 |
| cuHadron (P6) | 8 | 94 | 24 | 70 | 0 | 70 | 0 | 0 |
| HeCBench other 14 (P7) | 4 | 65 | 65 | 0 | 0 | 0 | 0 | 0 |
| HeCBench SC 10 (P9) | 3 | 49 | 49 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 (PI) | 2420 | 16538 | 12921 | 3617 | 0 | 3529 | 88 | 0 |
| ALL | 2670 | 18138 | 14436 | 3702 | 3 | 3611 | 88 | 0 |


### 4.2 Program-level violations

| setting | programs scalar-clock Race | collector-only Race | both Race | violations (scalar-clock Race, collector-only not Race) | reverse (collector-only Race, scalar-clock not) | of which scalar-clock Clean |
|---|---|---|---|---|---|---|
| S1 (strict) | 2670 | 2929 | 2670 | **0** | 259 | 259 |
| S2 (off) | 2670 | 2931 | 2670 | **0** | 261 | 261 |
| cfg (C6's R3, with the widest bound and async) | 2670 | 2929 | 2670 | **0** | 259 | 259 |

### 4.3 Per-program causes of the missing pairs (programs where scalar-clock Race and a pair of scalar-clock is not in collector-only's reports)

Per program the cause class is: certificate granted if any missing pair is of that class, else candidate missing if any, else other; lane drop only if every missing pair is a lane drop (step 3's rule). Candidate missing = the collector-only recording has no candidate pair for the scalar-clock pair (the pair's pcs are not joined by an edge or chain of reads, or are joined only thread-locally, or only through a non-read hop; sub-causes are in `pairs_*_by_program.tsv`). Certificate granted = the pair is a candidate and the verdict step orders it by a certificate (R2 coherence, morally strong RMW pair). Lane drop = the pair's pc has a dropped-word deficit (first-lane allocation lookup / words past an allocation end; static check (b) of C6).


**S1**: programs with at least one missing pair, by suite and program cause class

| suite | programs | missing pairs | certificate granted | candidate missing | lane drop only | other |
|---|---|---|---|---|---|---|
| P4 | 9 | 14 | 2 | 7 | 0 | 0 |
| P5 | 1 | 1 | 0 | 1 | 0 | 0 |
| P6 | 2 | 70 | 0 | 2 | 0 | 0 |
| PI | 337 | 3617 | 0 | 309 | 28 | 0 |
| **all** | 349 | 3702 | 2 | 319 | 28 | 0 |

**S2**: programs with at least one missing pair, by suite and program cause class

| suite | programs | missing pairs | certificate granted | candidate missing | lane drop only | other |
|---|---|---|---|---|---|---|
| P4 | 9 | 14 | 2 | 7 | 0 | 0 |
| P5 | 1 | 1 | 0 | 1 | 0 | 0 |
| P6 | 2 | 70 | 0 | 2 | 0 | 0 |
| PI | 337 | 3617 | 0 | 309 | 28 | 0 |
| **all** | 349 | 3702 | 2 | 319 | 28 | 0 |

Programs whose pair counts differ between S1 and S2: 0.

### 4.4 The programs with a granted certificate and the programs with a lane drop (S1; S2 identical where the line above says 0 differ)

| program | suite | scalar-clock pairs | found in collector-only | missing | certificate granted | lane drop | sub-causes (step 3) |
|---|---|---|---|---|---|---|---|
| `P4-rule-110-racy-large` | P4 | 2 | 1 | 1 | 1 | 0 | R2 coherence (morally strong RMW pair) x1 |
| `P4-uts-racy-small` | P4 | 11 | 9 | 2 | 2 | 0 | R2 coherence (morally strong RMW pair) x2 |
| `PI-conditional_edge_neighbors_boundsBug-DAG_5n_5e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug-power_law_200n_1000e` | PI | 10 | 1 | 9 | 0 | 5 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5; reachable only through a non-read hop x4 |
| `PI-conditional_edge_neighbors_boundsBug-DAG_100n_100e` | PI | 10 | 1 | 9 | 0 | 5 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5; reachable only through a non-read hop x4 |
| `PI-conditional_edge_neighbors_boundsBug_atomicBug_break-DAG_100n_100e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_break-DAG_100n_100e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_cond-DAG_100n_100e` | PI | 8 | 1 | 7 | 0 | 4 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4; reachable only through a non-read hop x3 |
| `PI-conditional_edge_neighbors_boundsBug_cond_atomicBug-DAG_100n_100e` | PI | 33 | 20 | 13 | 0 | 4 | reachable only through a non-read hop x9; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug-DAG_100n_100e` | PI | 6 | 5 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-DAG_100n_200e` | PI | 45 | 37 | 8 | 0 | 5 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5; reachable only through a non-read hop x3 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-counterDAG_200n_1000e` | PI | 49 | 42 | 7 | 0 | 5 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5; reachable only through a non-read hop x2 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-counterDAG_5n_5e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_cond_guardBug_atomicBug-DAG_100n_100e` | PI | 7 | 6 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug-DAG_200n_400e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug-counterDAG_200n_1000e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug-DAG_100n_100e` | PI | 8 | 6 | 2 | 0 | 2 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x2 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug-counterDAG_200n_1000e` | PI | 30 | 19 | 11 | 0 | 5 | reachable only through a non-read hop x6; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug-counterDAG_5n_5e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug-DAG_100n_100e` | PI | 30 | 17 | 13 | 0 | 5 | reachable only through a non-read hop x8; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug_break-counterDAG_200n_1000e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_atomicBug_break-DAG_100n_100e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_break-counterDAG_200n_1000e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_break-counterDAG_5n_5e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_guardBug_break-DAG_100n_100e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_atomicBug_break-DAG_100n_100e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_break-DAG_100n_100e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_guardBug_atomicBug_break-DAG_100n_200e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_guardBug_atomicBug_break-DAG_100n_100e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_edge_neighbors_boundsBug_reverse_cond_guardBug_break-DAG_100n_100e` | PI | 3 | 2 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_vertex_neighbors_boundsBug-DAG_100n_100e` | PI | 8 | 1 | 7 | 0 | 4 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4; reachable only through a non-read hop x3 |
| `PI-conditional_vertex_neighbors_boundsBug_atomicBug-counterDAG_5n_5e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_vertex_neighbors_boundsBug_atomicBug-DAG_100n_100e` | PI | 32 | 17 | 15 | 0 | 4 | reachable only through a non-read hop x11; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4 |
| `PI-conditional_vertex_neighbors_boundsBug_reverse_atomicBug_break-DAG_200n_400e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_vertex_neighbors_boundsBug_reverse_atomicBug_break-DAG_100n_100e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-conditional_vertex_neighbors_boundsBug_reverse_break-DAG_100n_100e` | PI | 2 | 1 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-populate_worklist_neighbors_boundsBug-counterDAG_5n_5e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-populate_worklist_neighbors_boundsBug-DAG_100n_100e` | PI | 16 | 9 | 7 | 0 | 4 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4; reachable only through a non-read hop x3 |
| `PI-populate_worklist_neighbors_boundsBug_atomicBug-DAG_200n_400e` | PI | 68 | 54 | 14 | 0 | 5 | reachable only through a non-read hop x9; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x5 |
| `PI-populate_worklist_neighbors_boundsBug_atomicBug-DAG_100n_100e` | PI | 46 | 33 | 13 | 0 | 4 | reachable only through a non-read hop x9; dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x4 |
| `PI-populate_worklist_neighbors_boundsBug_reverse_atomicBug_break-DAG_100n_100e` | PI | 7 | 6 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-populate_worklist_neighbors_boundsBug_reverse_break-DAG_200n_400e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |
| `PI-populate_worklist_neighbors_boundsBug_reverse_break-DAG_100n_100e` | PI | 4 | 3 | 1 | 0 | 1 | dropped-word deficit at a pair pc (first-lane allocation lookup / words past an allocation end) x1 |

Programs with a lane drop: 41, all Indigo 1.3 (`boundsBug` variants: an access past the allocation end): True; each of them is Race in collector-only (0 violations), so the lane drop removes pairs, not programs.

### 4.5 The deviation: probes of absent `hb_*` keys

From `assert_no_hb.txt` section 2 (the guarded loader over the three runs), verbatim:

```
## 2. Guarded loader, dynamic result over the three runs
Every kernel JSON is parsed with an object_hook that raises HbGuardError on a dict holding an hb_* key, and into a dict subclass whose
__getitem__/get/__contains__/pop/setdefault raise on an hb_* key that is PRESENT. A probe of an ABSENT hb_* key is counted per call site (the
unmodified verdict layer probes such keys on every dump, collector-only recordings included; the answer is the key-absent default).

run s1: sd.analyze calls 24271; value reads / hb keys present in memory (assert == 0): 0; probes of absent hb_* keys: 153786
    sync_dominance.py:1108|hb_events: 7990
    sync_dominance.py:1170|hb_events: 21636
    sync_dominance.py:1608|hb_races: 21636
    sync_dominance.py:1638|hb_races_sync_only: 21636
    sync_dominance.py:227|hb_events: 29626
    sync_dominance.py:251|hb_sync_pass: 21636
    sync_dominance.py:263|hb_rmw_points: 7990
    sync_dominance.py:321|hb_async: 21636
run s2: sd.analyze calls 24271; value reads / hb keys present in memory (assert == 0): 0; probes of absent hb_* keys: 153786
    sync_dominance.py:1108|hb_events: 7990
    sync_dominance.py:1170|hb_events: 21636
    sync_dominance.py:1608|hb_races: 21636
    sync_dominance.py:1638|hb_races_sync_only: 21636
    sync_dominance.py:227|hb_events: 29626
    sync_dominance.py:251|hb_sync_pass: 21636
    sync_dominance.py:263|hb_rmw_points: 7990
    sync_dominance.py:321|hb_async: 21636
run cfg: sd.analyze calls 24271; value reads / hb keys present in memory (assert == 0): 0; probes of absent hb_* keys: 153786
    sync_dominance.py:1108|hb_events: 7990
    sync_dominance.py:1170|hb_events: 21636
    sync_dominance.py:1608|hb_races: 21636
    sync_dominance.py:1638|hb_races_sync_only: 21636
    sync_dominance.py:227|hb_events: 29626
    sync_dominance.py:251|hb_sync_pass: 21636
    sync_dominance.py:263|hb_rmw_points: 7990
    sync_dominance.py:321|hb_async: 21636

Strict demonstration (S3_STRICT=1, P5-canary, one worker): the unmodified analysis raises at its first probe of an absent key -> strict mode cannot be run through to a verdict without changing sync_dominance.py:
    HbGuardError:STRICT: probe of hb key 'hb_async' at sync_dominance.py:321;chain=1
```


Reading. The acceptance claim is met at program level: 2,670 programs are Race in scalar-clock, all 2,670 are Race in collector-only at S1, S2 and cfg (0 violations). It is not met at pair level: 3,702 scalar-clock pairs in 349 programs are not among the collector-only reports, 3,611 of them because the collector-only recording has no candidate pair (no edge or chain of reads joins the pcs across threads: thread-local only, or only through a non-read hop), 3 because the verdict step orders a candidate by a certificate (R2 coherence, morally strong RMW pair; `P4-rule-110-racy-large` 1, `P4-uts-racy-small` 2), and 88 because a lane was dropped by the collector. The exception the claim names, the collector dropping a lane that HbClock sees (first-lane allocation lookup, words past an allocation's end), accounts for 88 pairs in 41 Indigo 1.3 `boundsBug` programs; its evidence is step 3's per-pair sub-cause "dropped-word deficit at a pair pc" (the static check (b) of C6: the words expected from the node's lane and address counts exceed the words on the edges; `CO_CHAIN.md` sections 3.3 and 7.1), and every one of those 41 programs is nevertheless Race in collector-only (the lane drop removes pairs, not programs). The other 319 programs with missing pairs (3,611 candidate-missing pairs; 13 of them also hold lane-drop pairs, 28 programs are lane-drop only) are not lane drops: the pairs are not joined across threads by an edge or a chain of reads in the recording (thread-local only, or only through a non-read accessor), the closure's own rule; sub-causes per pair are in `pairs_*_by_program.tsv`.

## 5. Cost

Rule and script of `eval/CAP_84600.md` section 3 (`3de35b29`, found with `git log --all -- eval/CAP_84600.md`), geometric means: run alone = tool wall / native wall over the finished programs, verdict step = analysis_s / native, end-to-end = (wall + analysis_s) / native over the finished programs that carry analysis_s; "All" = P1, PI, P3, P4, P5, P6 (4,685 programs); unrestricted adds P7 and P9 (HeCBench, 24 programs). `c6b_cost.py` reproduces CAP's rows exactly (check lines below: VC 7.320 / 2.454 / 9.966, SC 7.015 / 2.173 / 9.339, C1 5.564 / 2.098 / 7.773, n = 4,685 each), then applies the rule to C6, S1 and S2.

- **(a) Run alone.** S1, S2 and C6 re-use C1's recordings: their run wall is C1's in 4,709 of 4,709 rows, so run alone is C1's: 5.564 over the 4,685 programs, 5.652 over all 4,709.
- **(b) Verdict step**, 4,685-set: VC 2.454, SC 2.173, C1 2.098, C6 2.242 (A5-class estimate; 1.860 as measured on EPYC nodes), **S1 3.280, S2 3.143**. Over all 4,709: VC 2.447 (4,705), SC 2.168 (4,707), C1 2.091, C6 2.234 / 1.853, S1 3.269, S2 3.133. HeCBench (P7+P9, 24): C1 1.103, C6 1.119 / 0.884, S1 and S2 in the generated table.
- **(c) End-to-end**, 4,685-set: VC 9.966, SC **9.339**, C1 7.773, C6 7.923 (7.550), **S1 8.988, S2 8.851**. Over all 4,709: VC 10.182 (4,705), SC 9.497 (4,707), C1 7.884, C6 8.035 / 7.658, S1 9.110, S2 8.972. S1 and S2 are 3.8 % and 5.2 % below scalar-clock's 9.339 on the 4,685-set, and 15.6 % and 13.9 % above C1's 7.773.
- **Where the analysis ran.** S1 and S2: c14 for all 4,709 programs each (Xeon Silver 4110, `anode=c14` in every row, lscpu-checked by the job). C6: c5 (EPYC 9115, 2,360 programs) and c45 (EPYC 7302P, 2,349). C1, VC and SC: no `anode` is recorded in their rows; the rows carry `node=`, the recording node (listed below), and the analysis node of C1's reference rows is not recorded (C6 recorded c36 / c79 from the job logs and could not measure their CPU). So the clock modes' analysis_s and S1/S2's were **not** measured on one node, and which nodes the clock modes' ran on cannot be told from the rows (the task states the class, Xeon Silver 4110). Section 5.1 measures it: on one 4110 node (c19) the recorded VC and SC figures of 47 programs are reproduced within 5 %, and c14 is 15 to 17 % slower than c19 for S1/S2.

C6's closure factors on c26 (its re-time, pass 2, sum on / sum off): P1 1.0891, P3 1.0438, P4 1.0462, P5 1.0020, P6 1.0949, PI 1.0675, HeCBench 1.0142, all 1.0436 (n programs 47)
Re-time factors (host c19, pass 2 of the re-time over step 2's analysis_s on c14, same 47 programs): S1: P1 0.858, P3 0.899, P4 0.844, P5 0.763, P6 0.944, PI 0.935, HeCBench 0.828, all 0.852; S2: P1 0.883, P3 0.927, P4 0.841, P5 0.993, P6 1.011, PI 0.906, HeCBench 0.862, all 0.871

### Cost by the rule of CAP_84600.md section 3: geometric means (n programs)

| suite | mode | run only (n) | verdict step (n) | end-to-end (n) |
|---|---|---|---|---|
| Indigo3 | vector-clock | 10.421 (400) | 3.607 (400) | 14.662 (400) |
| Indigo3 | scalar-clock | 8.730 (400) | 3.384 (400) | 12.409 (400) |
| Indigo3 | C1 | 6.470 (400) | 3.296 (400) | 10.005 (400) |
| Indigo3 | C6, step-2 analysis_s as measured (EPYC nodes) | 6.470 (400) | 2.781 (400) | 9.489 (400) |
| Indigo3 | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 6.470 (400) | 3.590 (400) | 10.313 (400) |
| Indigo3 | S1, analysis_s measured on c14 | 6.470 (400) | 4.957 (400) | 11.715 (400) |
| Indigo3 | S2, analysis_s measured on c14 | 6.470 (400) | 4.833 (400) | 11.602 (400) |
| Indigo3 | S1, c14 analysis_s x factor of the re-time node (estimate) | 6.470 (400) | 4.251 (400) | 10.984 (400) |
| Indigo3 | S2, c14 analysis_s x factor of the re-time node (estimate) | 6.470 (400) | 4.269 (400) | 11.016 (400) |
| Indigo 1.3 | vector-clock | 6.932 (4130) | 2.349 (4130) | 9.405 (4130) |
| Indigo 1.3 | scalar-clock | 6.805 (4130) | 2.075 (4130) | 8.984 (4130) |
| Indigo 1.3 | C1 | 5.458 (4130) | 1.999 (4130) | 7.521 (4130) |
| Indigo 1.3 | C6, step-2 analysis_s as measured (EPYC nodes) | 5.458 (4130) | 1.783 (4130) | 7.327 (4130) |
| Indigo 1.3 | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 5.458 (4130) | 2.134 (4130) | 7.660 (4130) |
| Indigo 1.3 | S1, analysis_s measured on c14 | 5.458 (4130) | 3.132 (4130) | 8.673 (4130) |
| Indigo 1.3 | S2, analysis_s measured on c14 | 5.458 (4130) | 3.003 (4130) | 8.546 (4130) |
| Indigo 1.3 | S1, c14 analysis_s x factor of the re-time node (estimate) | 5.458 (4130) | 2.928 (4130) | 8.465 (4130) |
| Indigo 1.3 | S2, c14 analysis_s x factor of the re-time node (estimate) | 5.458 (4130) | 2.721 (4130) | 8.258 (4130) |
| ECL | vector-clock | 10.149 (60) | 3.477 (60) | 13.897 (60) |
| ECL | scalar-clock | 8.820 (60) | 3.274 (60) | 12.351 (60) |
| ECL | C1 | 6.006 (60) | 3.147 (60) | 9.348 (60) |
| ECL | C6, step-2 analysis_s as measured (EPYC nodes) | 6.006 (60) | 2.704 (60) | 8.952 (60) |
| ECL | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 6.006 (60) | 3.285 (60) | 9.492 (60) |
| ECL | S1, analysis_s measured on c14 | 6.006 (60) | 4.946 (60) | 11.177 (60) |
| ECL | S2, analysis_s measured on c14 | 6.006 (60) | 4.647 (60) | 10.917 (60) |
| ECL | S1, c14 analysis_s x factor of the re-time node (estimate) | 6.006 (60) | 4.446 (60) | 10.663 (60) |
| ECL | S2, c14 analysis_s x factor of the re-time node (estimate) | 6.006 (60) | 4.306 (60) | 10.564 (60) |
| ScoR apps | vector-clock | 28.849 (28) | 15.380 (28) | 55.364 (28) |
| ScoR apps | scalar-clock | 9.360 (28) | 8.079 (28) | 20.115 (28) |
| ScoR apps | C1 | 6.834 (28) | 7.941 (28) | 17.293 (28) |
| ScoR apps | C6, step-2 analysis_s as measured (EPYC nodes) | 6.834 (28) | 6.327 (28) | 15.255 (28) |
| ScoR apps | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 6.834 (28) | 8.308 (28) | 17.703 (28) |
| ScoR apps | S1, analysis_s measured on c14 | 6.834 (28) | 14.251 (28) | 24.857 (28) |
| ScoR apps | S2, analysis_s measured on c14 | 6.834 (28) | 11.550 (28) | 21.255 (28) |
| ScoR apps | S1, c14 analysis_s x factor of the re-time node (estimate) | 6.834 (28) | 12.022 (28) | 22.412 (28) |
| ScoR apps | S2, c14 analysis_s x factor of the re-time node (estimate) | 6.834 (28) | 9.711 (28) | 19.249 (28) |
| ScoR litmus | vector-clock | 8.845 (33) | 1.909 (33) | 10.839 (33) |
| ScoR litmus | scalar-clock | 7.361 (33) | 1.639 (33) | 9.060 (33) |
| ScoR litmus | C1 | 5.637 (33) | 1.702 (33) | 7.406 (33) |
| ScoR litmus | C6, step-2 analysis_s as measured (EPYC nodes) | 5.637 (33) | 1.560 (33) | 7.276 (33) |
| ScoR litmus | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 5.637 (33) | 1.705 (33) | 7.409 (33) |
| ScoR litmus | S1, analysis_s measured on c14 | 5.637 (33) | 2.792 (33) | 8.537 (33) |
| ScoR litmus | S2, analysis_s measured on c14 | 5.637 (33) | 2.530 (33) | 8.263 (33) |
| ScoR litmus | S1, c14 analysis_s x factor of the re-time node (estimate) | 5.637 (33) | 2.131 (33) | 7.857 (33) |
| ScoR litmus | S2, c14 analysis_s x factor of the re-time node (estimate) | 5.637 (33) | 2.512 (33) | 8.245 (33) |
| cuHadron | vector-clock | 12.993 (34) | 0.819 (34) | 15.096 (34) |
| cuHadron | scalar-clock | 10.752 (34) | 0.709 (34) | 12.180 (34) |
| cuHadron | C1 | 7.124 (34) | 0.722 (34) | 8.530 (34) |
| cuHadron | C6, step-2 analysis_s as measured (EPYC nodes) | 7.124 (34) | 0.646 (34) | 8.419 (34) |
| cuHadron | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 7.124 (34) | 0.790 (34) | 8.658 (34) |
| cuHadron | S1, analysis_s measured on c14 | 7.124 (34) | 1.147 (34) | 9.395 (34) |
| cuHadron | S2, analysis_s measured on c14 | 7.124 (34) | 1.065 (34) | 9.270 (34) |
| cuHadron | S1, c14 analysis_s x factor of the re-time node (estimate) | 7.124 (34) | 1.082 (34) | 9.274 (34) |
| cuHadron | S2, c14 analysis_s x factor of the re-time node (estimate) | 7.124 (34) | 1.077 (34) | 9.293 (34) |
| HeCBench other 14 | vector-clock | 1411.497 (12) | 0.663 (12) | 1421.126 (12) |
| HeCBench other 14 | scalar-clock | 246.314 (13) | 0.752 (13) | 249.588 (13) |
| HeCBench other 14 | C1 | 99.881 (14) | 0.626 (14) | 103.355 (14) |
| HeCBench other 14 | C6, step-2 analysis_s as measured (EPYC nodes) | 99.881 (14) | 0.519 (14) | 103.406 (14) |
| HeCBench other 14 | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 99.881 (14) | 0.635 (14) | 103.402 (14) |
| HeCBench other 14 | S1, analysis_s measured on c14 | 99.881 (14) | 0.989 (14) | 105.345 (14) |
| HeCBench other 14 | S2, analysis_s measured on c14 | 99.881 (14) | 0.935 (14) | 105.362 (14) |
| HeCBench other 14 | S1, c14 analysis_s x factor of the re-time node (estimate) | 99.881 (14) | 0.819 (14) | 104.457 (14) |
| HeCBench other 14 | S2, c14 analysis_s x factor of the re-time node (estimate) | 99.881 (14) | 0.806 (14) | 104.654 (14) |
| HeCBench SC 10 | vector-clock | 1694.363 (8) | 3.405 (8) | 1708.741 (8) |
| HeCBench SC 10 | scalar-clock | 512.634 (9) | 2.609 (9) | 520.908 (9) |
| HeCBench SC 10 | C1 | 150.442 (10) | 2.439 (10) | 159.563 (10) |
| HeCBench SC 10 | C6, step-2 analysis_s as measured (EPYC nodes) | 150.442 (10) | 1.862 (10) | 156.697 (10) |
| HeCBench SC 10 | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 150.442 (10) | 2.473 (10) | 159.683 (10) |
| HeCBench SC 10 | S1, analysis_s measured on c14 | 150.442 (10) | 3.849 (10) | 163.845 (10) |
| HeCBench SC 10 | S2, analysis_s measured on c14 | 150.442 (10) | 3.516 (10) | 163.436 (10) |
| HeCBench SC 10 | S1, c14 analysis_s x factor of the re-time node (estimate) | 150.442 (10) | 3.187 (10) | 161.717 (10) |
| HeCBench SC 10 | S2, c14 analysis_s x factor of the re-time node (estimate) | 150.442 (10) | 3.033 (10) | 161.800 (10) |
| HeCBench (P7+P9) | vector-clock | 1518.485 (20) | 1.275 (20) | 1529.854 (20) |
| HeCBench (P7+P9) | scalar-clock | 332.438 (22) | 1.251 (22) | 337.243 (22) |
| HeCBench (P7+P9) | C1 | 118.468 (24) | 1.103 (24) | 123.855 (24) |
| HeCBench (P7+P9) | C6, step-2 analysis_s as measured (EPYC nodes) | 118.468 (24) | 0.884 (24) | 122.959 (24) |
| HeCBench (P7+P9) | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 118.468 (24) | 1.119 (24) | 123.927 (24) |
| HeCBench (P7+P9) | S1, analysis_s measured on c14 | 118.468 (24) | 1.742 (24) | 126.631 (24) |
| HeCBench (P7+P9) | S2, analysis_s measured on c14 | 118.468 (24) | 1.623 (24) | 126.511 (24) |
| HeCBench (P7+P9) | S1, c14 analysis_s x factor of the re-time node (estimate) | 118.468 (24) | 1.442 (24) | 125.322 (24) |
| HeCBench (P7+P9) | S2, c14 analysis_s x factor of the re-time node (estimate) | 118.468 (24) | 1.400 (24) | 125.487 (24) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | vector-clock | 7.320 (4685) | 2.454 (4685) | 9.966 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | scalar-clock | 7.015 (4685) | 2.173 (4685) | 9.339 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | C1 | 5.564 (4685) | 2.098 (4685) | 7.773 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | C6, step-2 analysis_s as measured (EPYC nodes) | 5.564 (4685) | 1.860 (4685) | 7.550 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 5.564 (4685) | 2.242 (4685) | 7.923 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | S1, analysis_s measured on c14 | 5.564 (4685) | 3.280 (4685) | 8.988 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | S2, analysis_s measured on c14 | 5.564 (4685) | 3.143 (4685) | 8.851 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | S1, c14 analysis_s x factor of the re-time node (estimate) | 5.564 (4685) | 3.036 (4685) | 8.733 (4685) |
| All (4,685-set: P1 PI P3 P4 P5 P6) | S2, c14 analysis_s x factor of the re-time node (estimate) | 5.564 (4685) | 2.845 (4685) | 8.541 (4685) |
| All incl. HeCBench (unrestricted) | vector-clock | 7.488 (4705) | 2.447 (4705) | 10.182 (4705) |
| All incl. HeCBench (unrestricted) | scalar-clock | 7.142 (4707) | 2.168 (4707) | 9.497 (4707) |
| All incl. HeCBench (unrestricted) | C1 | 5.652 (4709) | 2.091 (4709) | 7.884 (4709) |
| All incl. HeCBench (unrestricted) | C6, step-2 analysis_s as measured (EPYC nodes) | 5.652 (4709) | 1.853 (4709) | 7.658 (4709) |
| All incl. HeCBench (unrestricted) | C6, A5-class estimate (C1 analysis_s x c26 closure factor) | 5.652 (4709) | 2.234 (4709) | 8.035 (4709) |
| All incl. HeCBench (unrestricted) | S1, analysis_s measured on c14 | 5.652 (4709) | 3.269 (4709) | 9.110 (4709) |
| All incl. HeCBench (unrestricted) | S2, analysis_s measured on c14 | 5.652 (4709) | 3.133 (4709) | 8.972 (4709) |
| All incl. HeCBench (unrestricted) | S1, c14 analysis_s x factor of the re-time node (estimate) | 5.652 (4709) | 3.024 (4709) | 8.852 (4709) |
| All incl. HeCBench (unrestricted) | S2, c14 analysis_s x factor of the re-time node (estimate) | 5.652 (4709) | 2.835 (4709) | 8.659 (4709) |

Check against CAP_84600.md section 3 (All, 4,685-set; run only / verdict step / end-to-end):
  - vector-clock: CAP (7.32, 2.454, 9.966), recomputed (7.32, 2.454, 9.966) (n 4685/4685/4685) -> equal
  - scalar-clock: CAP (7.015, 2.173, 9.339), recomputed (7.015, 2.173, 9.339) (n 4685/4685/4685) -> equal
  - collector-only: CAP (5.564, 2.098, 7.773), recomputed (5.564, 2.098, 7.773) (n 4685/4685/4685) -> equal
  - collector alone over all finished programs (the paper's 5.7x): 5.652 (n 4709)
  - C6 rows whose run wall differs from C1's row of the same program: 0 of 4709
  - S1 rows whose run wall differs from C1's row of the same program: 0 of 4709
  - S2 rows whose run wall differs from C1's row of the same program: 0 of 4709

### Nodes of the analysis_s figures

- vector-clock: programs with analysis_s 4705; `anode=` in the notes: none recorded; `node=` (recording node): c24 771, c40 747, c74 404, c42 397, c0 386, c1 385, c79 337, c76 286, c75 285, c73 245, c44 114, c41 113 ...
- scalar-clock: programs with analysis_s 4707; `anode=` in the notes: none recorded; `node=` (recording node): c24 773, c40 747, c74 407, c42 397, c0 386, c1 385, c79 337, c76 284, c75 284, c73 245, c41 114, c44 114 ...
- C1: programs with analysis_s 4709; `anode=` in the notes: none recorded; `node=` (recording node): c68 607, c76 599, c61 582, c69 553, c75 540, c78 516, c74 491, c79 452, c62 166, c63 130, c64 71, c56 1 ...
- C6: programs with analysis_s 4709; `anode=` in the notes: {'c5': 2360, 'c45': 2349}; `node=` (recording node): c68 607, c76 599, c61 582, c69 553, c75 540, c78 516, c74 491, c79 452, c62 166, c63 130, c64 71, c56 1 ...
- S1: programs with analysis_s 4709; `anode=` in the notes: {'c14': 4709}; `node=` (recording node): c68 607, c76 599, c61 582, c69 553, c75 540, c78 516, c74 491, c79 452, c62 166, c63 130, c64 71, c56 1 ...
- S2: programs with analysis_s 4709; `anode=` in the notes: {'c14': 4709}; `node=` (recording node): c68 607, c76 599, c61 582, c69 553, c75 540, c78 516, c74 491, c79 452, c62 166, c63 130, c64 71, c56 1 ...

### analysis_s of the verdict step per suite: median, max, sum, and the closure's share

share = sum(chain_s) / sum(analysis_s). C1 is the reference column (A5's node class as C6 recorded it; its analysis node is not recorded). S1 / S2 on c14.

| suite | n | C1 median | C1 max | C6 median | C6 max | S1 median | S1 max | S2 median | S2 max | sum C1 | sum C6 | sum S1 | sum S2 | S1 chain_s sum | S1 share | S2 chain_s sum | S2 share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Indigo3 (P1) | 400 | 0.784 | 1.630 | 0.607 | 1.512 | 1.155 | 2.147 | 1.150 | 2.706 | 312.5 | 269.5 | 467.0 | 459.0 | 1.13 | 0.0024 | 1.10 | 0.0024 |
| Indigo 1.3 (PI) | 4130 | 0.408 | 1.782 | 0.383 | 1.410 | 0.641 | 2.921 | 0.615 | 1.908 | 1839.6 | 1669.1 | 2877.6 | 2763.5 | 0.20 | 0.0001 | 0.19 | 0.0001 |
| ECL (P3) | 60 | 0.728 | 1.366 | 0.608 | 1.292 | 1.149 | 2.053 | 1.095 | 1.998 | 44.9 | 39.9 | 70.0 | 66.4 | 0.13 | 0.0018 | 0.12 | 0.0018 |
| ScoR apps (P4) | 28 | 1.382 | 14.529 | 1.236 | 9.072 | 2.287 | 39.600 | 2.098 | 21.756 | 96.2 | 68.4 | 210.1 | 140.3 | 0.14 | 0.0007 | 0.14 | 0.0010 |
| ScoR litmus (P5) | 33 | 0.361 | 0.465 | 0.352 | 0.816 | 0.605 | 0.881 | 0.535 | 0.897 | 12.4 | 11.7 | 20.5 | 18.6 | 0.00 | 0.0000 | 0.00 | 0.0000 |
| cuHadron (P6) | 34 | 0.356 | 0.488 | 0.314 | 0.443 | 0.561 | 0.897 | 0.524 | 0.847 | 12.1 | 10.9 | 19.2 | 17.9 | 0.02 | 0.0012 | 0.02 | 0.0013 |
| HeCBench other 14 (P7) | 14 | 0.792 | 11.836 | 0.678 | 5.991 | 1.603 | 14.622 | 1.317 | 14.291 | 31.4 | 22.2 | 43.9 | 41.3 | 4.81 | 0.1098 | 4.86 | 0.1177 |
| HeCBench SC 10 (P9) | 10 | 2.166 | 11.310 | 2.052 | 7.860 | 3.397 | 13.935 | 3.426 | 13.767 | 34.9 | 27.8 | 51.1 | 49.3 | 2.92 | 0.0571 | 2.89 | 0.0585 |
| HeCBench (P7+P9) | 24 | 1.153 | 11.836 | 0.944 | 7.860 | 1.927 | 14.622 | 1.782 | 14.291 | 66.3 | 50.0 | 95.0 | 90.6 | 7.73 | 0.0814 | 7.75 | 0.0855 |
| all but HeCBench | 4685 | 0.417 | 14.529 | 0.393 | 9.072 | 0.658 | 39.600 | 0.630 | 21.756 | 2317.7 | 2069.5 | 3664.4 | 3465.7 | 1.63 | 0.0004 | 1.57 | 0.0005 |
| all | 4709 | 0.418 | 14.529 | 0.394 | 9.072 | 0.659 | 39.600 | 0.631 | 21.756 | 2384.0 | 2119.4 | 3759.4 | 3556.4 | 9.36 | 0.0025 | 9.32 | 0.0026 |

S1: largest analysis_s 39.600 s (`P4-uts-racy-large`), its chain_s 0.001 s. Largest chain_s: `P7-stencil1d-cuda` 2.306 s of 1.731 s; `P9-atomicCAS-cuda` 1.317 s of 10.806 s; `P7-heartwall-cuda` 1.305 s of 14.622 s; `P7-srad-cuda` 1.033 s of 4.797 s; `P9-tridiagonal-cuda` 0.576 s of 13.935 s
S1 analysis_s over C1's per program (programs with C1 analysis_s >= 0.2 s, n 4709): median 1.540, max 13.069; sum over all programs 3759.4 s against C1 2384.0 s and C6 2119.4 s.

S2: largest analysis_s 21.756 s (`P4-reduction-racy-large`), its chain_s 0.000 s. Largest chain_s: `P7-stencil1d-cuda` 2.375 s of 1.372 s; `P9-atomicCAS-cuda` 1.299 s of 10.217 s; `P7-heartwall-cuda` 1.258 s of 14.291 s; `P7-srad-cuda` 1.059 s of 4.194 s; `P9-tridiagonal-cuda` 0.580 s of 13.767 s
S2 analysis_s over C1's per program (programs with C1 analysis_s >= 0.2 s, n 4709): median 1.488, max 4.764; sum over all programs 3556.4 s against C1 2384.0 s and C6 2119.4 s.


### 5.1 Same-node re-time

Because the node of the clock-mode figures is not recorded, the question "how much of S1/S2's verdict step is the rules and how much is c14" is measured directly: C6's 47-program re-time sample (8 P1, 4 P3, 8 P4, 4 P5, 4 P6, 12 PI, 7 HeCBench), five configurations on one Xeon Silver 4110 node (`c6b_retime.sbatch`; each configuration twice in a row, pass 2 warm): VC and SC (as recorded, no flags), C1's rules (`--confirm` only), S1 and S2 (`--confirm --chain-closure --co-async --co-r3 {strict,off}`), all `--analysis-workers 16`, one program at a time.

Results (host c19, Xeon Silver 4110, job 326502; pass 2, sums of analysis_s over the 47 programs, seconds; ratios are in the table below the sums):

- **Cost of the rules on one node.** C1's rules 66.25 s; S1 69.00 s (**1.041**); S2 69.99 s (**1.056**); per group S1 / C1's rules: P1 1.045, P3 1.090, P4 1.018, P5 1.129, P6 1.285, PI 1.150, HeCBench 1.001; the largest single program ratio (C1's rules >= 0.2 s) is 1.776 (S1) and 1.914 (S2). The closure's own time (chain_s sum) is 0.251 s (S1) and 0.253 s (S2) of 69 s. Pass 1 (cold) and pass 2 differ by less than 2 % for S1 and S2 (69.15 / 69.00; 68.80 / 69.99).
- **c14 against c19, same CPU model, same code, same programs.** Step 2 measured the 47 programs on c14 at 80.96 s (S1) and 80.40 s (S2); c19 measures 69.00 s and 69.99 s: c14's figures are 1.173 (S1) and 1.149 (S2) times c19's (per group 0.99 to 1.31, table). So S1/S2's step-2 analysis_s were measured on a node 15 to 17 % slower than another node of the same class.
- **Which node level the recorded clock-mode and C1 figures sit at.** For the same 47 programs the recorded (A5) analysis_s sum to VC 139.01 s and SC 64.16 s; on c19 VC takes 132.34 s (0.952) and SC 65.74 s (1.025): the clock modes' recorded figures are at c19's level, within 5 %. C1's recorded reference sums to 54.89 s, while C1's own rules take 66.25 s on c19 (**1.207** times the reference; 66.81 s on c26 in C6's re-time) and 55.65 s on the EPYC 7302P node c25 in C6's re-time: C1's recorded figures are at the level of that EPYC node, not of a 4110 node. C6's step-2 figures (EPYC, mixed) sum to 42.01 s (0.765 of the reference).
- **Decomposition of S1's step-2 figure against C1's reference** (sums over the 47 programs): 80.96 / 54.89 = 1.475 = 1.207 (node: c19 against the C1 reference) x 1.041 (rules, one node) x 1.173 (c14 against c19); the product is 1.474.
- **What it does to the cost rows.** The measured S1/S2 rows (analysis_s as step 2 recorded on c14) are 3.280 / 3.143 for the verdict step and 8.988 / 8.851 end-to-end on the 4,685-set. Scaled to c19's level by the per-group c19 / c14 factor of the re-time (an estimate, not a measurement over the corpus): S1 3.036 / 8.733, S2 2.845 / 8.541; with HeCBench, 3.024 / 8.852 and 2.835 / 8.659. Against scalar-clock's 9.339 end-to-end, S1 and S2 are below it by 3.8 % and 5.2 % as measured and by 6.5 % and 8.5 % at c19's level; against C1's 7.773 the measured rows are 15.6 % and 13.9 % above and the c19-level estimates 12.4 % and 9.9 % above, of which the node factor between C1's reference level and a 4110 node (1.207 on the sums) is part, the rules' own factor on one node 1.041 / 1.056 being the rest of the verdict step.


### Re-time: the 47-program sample on one Xeon Silver 4110 node


#### Host c19: 47 programs in every configuration and pass (sum of analysis_s per group, seconds)

| group | n | co-off p1 | co-off p2 | co-s1 p1 | co-s1 p2 | co-s2 p1 | co-s2 p2 | sc p1 | sc p2 | vc p1 | vc p2 | step 2 S1 (c14) | step 2 S2 (c14) | C1 ref (A5) | C6 step 2 (EPYC) | clock modes (A5) vc | sc |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 8 | 7.42 | 7.32 | 7.45 | 7.65 | 7.43 | 7.85 | 7.24 | 7.04 | 7.13 | 7.08 | 8.92 | 8.88 | 5.96 | 5.02 | 8.20 | 6.77 |
| P3 | 4 | 3.82 | 3.77 | 4.23 | 4.11 | 3.99 | 4.13 | 3.89 | 3.77 | 3.77 | 3.84 | 4.58 | 4.46 | 3.15 | 2.44 | 3.89 | 3.68 |
| P4 | 8 | 27.65 | 27.47 | 28.37 | 27.96 | 28.07 | 28.34 | 28.29 | 27.75 | 95.05 | 92.08 | 33.14 | 33.71 | 23.06 | 15.20 | 95.36 | 27.31 |
| P5 | 4 | 1.89 | 1.80 | 1.90 | 2.03 | 2.03 | 2.17 | 1.83 | 1.76 | 1.85 | 1.86 | 2.66 | 2.18 | 1.58 | 1.19 | 1.86 | 1.63 |
| P6 | 4 | 1.60 | 1.54 | 1.91 | 1.98 | 1.87 | 2.12 | 2.05 | 1.60 | 1.90 | 1.63 | 2.10 | 2.10 | 1.38 | 1.30 | 2.01 | 1.43 |
| PI | 12 | 6.19 | 5.98 | 6.76 | 6.88 | 6.73 | 6.57 | 6.01 | 5.88 | 6.09 | 6.41 | 7.36 | 7.25 | 4.90 | 4.69 | 6.96 | 5.24 |
| HeCBench | 7 | 18.05 | 18.36 | 18.54 | 18.39 | 18.67 | 18.82 | 18.01 | 17.94 | 20.49 | 19.44 | 22.21 | 21.82 | 14.86 | 12.17 | 20.74 | 18.10 |
| all | 47 | 66.63 | 66.25 | 69.15 | 69.00 | 68.80 | 69.99 | 67.33 | 65.74 | 136.27 | 132.34 | 80.96 | 80.40 | 54.89 | 42.01 | 139.01 | 64.16 |

**Ratios on c19, pass 2 (sum over the group of analysis_s of the numerator over the denominator)**

| group | S1 / co-off | S2 / co-off | co-off / C1 ref (A5) | S1 / step-2 S1 (c14) | S2 / step-2 S2 (c14) | sc / co-off | vc / co-off | sc / A5 sc | vc / A5 vc | C6 (EPYC, step 2) / C1 ref | max per-program S1 / co-off (co-off >= 0.2 s) | max S2 / co-off |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 1.045 | 1.072 | 1.228 | 0.858 | 0.883 | 0.962 | 0.967 | 1.040 | 0.864 | 0.842 | 1.277 | 1.350 |
| P3 | 1.090 | 1.094 | 1.197 | 0.899 | 0.927 | 0.998 | 1.017 | 1.023 | 0.988 | 0.773 | 1.419 | 1.289 |
| P4 | 1.018 | 1.032 | 1.192 | 0.844 | 0.841 | 1.010 | 3.351 | 1.016 | 0.966 | 0.659 | 1.124 | 1.108 |
| P5 | 1.129 | 1.203 | 1.139 | 0.763 | 0.993 | 0.978 | 1.036 | 1.083 | 1.002 | 0.754 | 1.250 | 1.409 |
| P6 | 1.285 | 1.378 | 1.116 | 0.944 | 1.011 | 1.040 | 1.062 | 1.121 | 0.814 | 0.943 | 1.396 | 1.914 |
| PI | 1.150 | 1.098 | 1.220 | 0.935 | 0.906 | 0.983 | 1.071 | 1.123 | 0.921 | 0.957 | 1.776 | 1.651 |
| HeCBench | 1.001 | 1.025 | 1.236 | 0.828 | 0.862 | 0.977 | 1.059 | 0.991 | 0.937 | 0.819 | 1.064 | 1.119 |
| all | 1.041 | 1.056 | 1.207 | 0.852 | 0.871 | 0.992 | 1.998 | 1.025 | 0.952 | 0.765 | 1.776 | 1.914 |

chain_s sums, pass 2: co-off 0.000 s, co-s1 0.251 s, co-s2 0.253 s


## 6. Setup

- **Base and branch.** `eval/co-chain-b`, cut from `eval/co-chain` be325e03 (C6; cuVein 98371ee + C3 + the merge of `eval/collector-only-tables`). Commits: `d150eb40`, `7e9417fd` (step 0: lock_rtraw, `results/co-chain-b/step0/rtraw.md`), `3b2e91f8` (step 1: the three rules, `test_co_rules.py`, `test_co_chain.py`; green set 11 files, before 85 passed 156 skipped, after 107 passed 156 skipped), `93ae2d66` (step 2 scripts), `ea2b9c9f` (step 2 results), `90cc7e9d` (step 3), and this step's commit. Step 2 ran at code rev `93ae2d664256` (`dirty=0`); `python/` is unchanged by step 4.
- **The three switches** (`python/sync_dominance.py` at `3b2e91f8`; `parallel.py analyze` flags; all default off and byte-identical when off; `co_async` and `co_r3` act only on collector-only dumps, i.e. kernel JSONs with no `hb_*` key):
  1. `--chain-closure`, rule (a): `chain_closure_pairs` finds, per source pc a, the **widest** hop over **every** walk a to h1..hk to c whose inner pcs are reads (C6: the narrowest chain, a minimax). Each chain bounds only its own instances, and a chain whose hops lay on different addresses can give a bound below a real instance's distance. Implementation: a breadth-first search over (inner node, widest hop so far) states, a state kept only when it widens its node's level (at most 4 per node); the witness is the walk to the state that gives the bound (shallowest, then smallest pc). Every edge is judged at max(its own widest distance, its widest chain bound) (a same-instruction edge's own distance is WARP); where the chain bound is wider the record is a rescue (`chain_rescue`); a pair joined only by a chain is derived (`chain`). Closure is over pcs, not addresses. Cap: `ChainCapError` past the cap (no program in S1 or S2 hit it).
  2. `--co-async`, rule (b): an `LDGSTS` (cp.async) pc's accesses are the issuing thread's async agent's (T1a `async_pcs`; a kernel with `ARRIVES.LDGSTSBAR` keeps the pre-T1a reading). An edge with a same-thread instance whose earlier access is a copy and whose later one is not is a cross-agent candidate: judged at max(WARP, the edge's own and chain distance) with no R1/R3 credit, unless `HBGraph.async_waited(copy, later)`: an unguarded `DEPBAR.LE SB0, 0x0` (`_DEPBAR_ALL`, the `cp.async.wait_all` / `wait_group 0` form) lies on every CFG path (instruction graph) from the copy to the later access; False for a pc the CFG does not know, vacuously True for a later access no path reaches; a wait with a non-zero count never orders it. Every verdict record gets `async` (true on the candidates).
  3. `--co-r3 cfg|strict|off`, rule (c): `cfg` (default) region-dominance certificate of R3; `strict`: the certificate stands only if R3 also finds a chain with scalar-clock's CFG-decidable declines (`_past_release`'s landing check, `_before_acquire`'s write-before-lock), decided on the CFG alone (`HBGraph.r3_cfg_only`, location condition taken as true); `off`: no R3 certificate, R1 alone orders. Every verdict record gets `atomic_chain_off` (true where the cfg certificate was withheld). S1 = `--co-r3 strict`, S2 = `--co-r3 off`, both with `--chain-closure --co-async`.
- **Step 2 parity** (`merged-s*/parity_report.txt`): a program whose derived, rescued, async and atomic_chain_off are all 0 equals C1 on verdict, reports_dedup, report_ids, report_lines and `classes=`: 4,725 programs, 4,709 analysed (the 16 not analysed are P6 `missing-exe` rows, equal to C1), **0 violations** at S1 and S2; programs with derived > 0 1,093, rescued > 0 687, async > 0 1, atomic_chain_off > 0 6 (S1) / 24 (S2); no chain-cap. Verdict changes against C1 (all CLEAN to RACE): S1 32, S2 35.
- **Step 2 jobs** (one node at a time; all on c14, Xeon Silver 4110 2 sockets x 8 cores, `lscpu` checked, no job aborted): 326257 (S1 shards 0-7, 00:37:55), 326276 (S1 8-15, 00:35:22), 326288 (S2 0-7, 00:33:33), 326292 (S2 8-15, 00:34:45), 326308 (S1 long + 24h, 00:00:43), 326319 (S2 long + 24h, 00:00:42); merges 326333 (S1), 326334 (S2) on c7. Step 0: 326237, 326247. Step 1: tests (jobs named c6b-job1..3: 326244, 326248, 326250; which of them ran the green set is not recorded in the commit). Step 3: 326348, 326351 (prep), 326352 (S1, c2), 326353 (S2, c14), 326354 (cfg, c42), 326435 (cancelled), 326463 (strip), 326467 to 326469 (re-run of 8 ids), 326479 to 326481 (post), 326491, 326494 (final).
- **Step 4 jobs.** A single worker on `normal` (326496, c3, `--exclusive`, queued command files: stage, tables, cost, detect, step-3 fragment, document) and the same-node re-time 326502 (`skylake`, `--exclusive`, c19, Xeon Silver 4110). Never more than 2 of my nodes at a time (the cap of 10 held by the `x9-*` jobs, which were not touched). Python is `/home/fzheng4/AccelProf/.env/bin/python`; `CUVEIN_HOME=ACCEL_PROF_HOME=/home/fzheng4/wt-c6b`, every other `CUVEIN_*` and `YOSEMITE_*` unset. Scripts: `eval/baselines/setup/c6b_{env.sh,stage.sh,tables.py,cost.py,detect.py,step3_frag.py,retime.sbatch,retime_summary.py,doc.py,worker.sbatch}`; outputs `eval/results/co-chain-b/step4/` (`tables/`, `cost/`, `detect/`, `retime/`, `*.stdout`, fragments).

## 7. Missing, and why

- Real-world recall and candidate sets (C2's recordings): not re-analysed at S1 or S2; step 2 covered only the 4,725 C1 programs, so section 1 has no real-world rows for them.
- Analysis node of the clock modes' and C1's analysis_s: not recorded in their rows (no `anode`); only the recording node (`node=`) is. The same-node re-time (5.1) replaces the missing record with a measurement on one node for 47 programs, not for the whole corpus.
- Step 1's report was not a separate file; the rules above are from the step 1 commit message and diff (`git show 3b2e91f8`). Which of the jobs 326244, 326248, 326250 ran which test is not recorded.
- `lock_rtraw`: the recordings still cannot separate the effect of the recording (`0x230 <- 0x1b0` against `0x330 <- 0x1b0`) from the effect of the rule (step 0); S2's Race agrees with SC's by a different route.
- Raw confirm JSONs of step 3 (`run-*/confirm`, `.state-*.pkl`) are not committed (size); step 3's tables are from the committed TSVs. The 20-pair address-sharing sample of `CO_CHAIN.md` section 4 was not repeated (no addresses in the kernel JSONs).
- Step-2 confirm JSONs hold Race-class (`raw`) and strong-class (`raw_sc`) records; the false-report tables count `raw` pairs and list `raw_sc` totals separately. A pair is a pc pair, not an address pair.
