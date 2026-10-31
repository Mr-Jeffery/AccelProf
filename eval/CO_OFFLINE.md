# CO-R: collector-only, re-scored (C4)

Branch `eval/co-offline`, cut from cuVein f551ca0 (`eval/collector-only-tables` 1c97571 fast-forwarded in, c45e1b3 cherry-picked for `test_collector_only.py`). Not merged. No GPU, no recording: X1b's scalar-clock kernel JSONs (`final-2026-11`, `-long`, `-long-sc`, `-24h-sc`) and the real-world scalar-clock recordings of T21b / T21c re-analysed on `normal` nodes.

**CO-R** = the verdict layer run on the scalar-clock kernel JSONs with the barrier-ordered rule off (`CUVEIN_BARRIER_ORDER=0`, `sync_dominance.analyze(barrier_order=False)`). Everything else is as in scalar-clock mode: the candidates (cuVein's edges plus the event-stream candidates from hb_sync_pass), the edge rescue (observed distances from hb_sync_pass), the RMW points (hb_rmw_points) and all three certificates. A conflicting pair no certificate orders is Race or Strong conflict; there is no Latent. "cuVein edges only" = C1's collector-only run (separate recordings, no sync pass).

Numbers in this file come from kernel JSONs through the CSVs / jsonl in `eval/results/co-offline/` (named per section); a number that could not be obtained is stated as missing.

## Findings

1. **Parity (rule on):** 0 differences between the re-analysis with the rule on and X1b's own CSVs, on verdict, reports_dedup, report_ids, report_lines and the classes note: 14,157 (id, mode, rep) rows in 122 shard files (112 main + PI, 2 long-sc, 8 24h-sc), 0 shard files missing; merged with X1b's rule, 14,111 scalar-clock rows against 14,111, 0 differences (`parity_shards.md`, `merged_report.md`).
2. **Table 6.1 aggregate row, CO-R:** 1,958/2,082 recall, 246/1,548 false-positive rate, 16 ERR; scalar-clock 1,934/2,082 and 18/1,548; cuVein edges only 1,956/2,082 and 246/1,548.
3. **Program level, CO-R against scalar-clock (same recordings):** 254 programs go Clean to Race (Indigo 1.3 248: 24 racy-labelled, 224 race-free; ScoR applications 4 race-free; HeCBench other 1 unlabelled; HeCBench SC's 10 1 race-free); 0 programs go Race to Clean; 0 other differences. 229 race-free-labelled programs are Race in CO-R and Clean in scalar-clock.
4. **Pair level:** CO-R reports 1,016 pairs in 893 programs that scalar-clock orders; scalar-clock ordered every one by the barrier clock in every launch. All 1,016 have a cuVein edge (a); 0 are extended or rescued edges (b). They are the same 1,016 pairs as C3's S1: no pair in one set and not the other. The shape counts equal X5's.
5. **Real-world:** CO-R detects the four data-race components that the edges-only run missed (CCCL top-k, Ginkgo range-minimum, Kokkos rw_sum, RAFT select_k), and PCL's data-race half. Details, and the llama.cpp-open-2 difference, in section 2.
6. **CO-R against C1:** 4,679 of 4,709 programs have the same verdict; 28 are Clean in C1 and Race in CO-R, 0 the other way, 2 other differences. 551 pairs fall in "other" (455 CO-R only, 96 C1 only): these are findings, listed in section 5.

## Run state

- Re-analysis job 323878 (c76, 5:32:03, COMPLETED): X1b's shard counts (48 main, 64 PI, 2 long-sc, 4+2+2 for 24h-sc), each program analysed serially with the rule on and off, both analysis times recorded (`final-b*/analysis-time-*.csv`). All 122 shards wrote the on CSV, the off CSV (`baselines-cuvein-bo0-*`) and the timing CSV.
- Pair-level pass: 28 shards over the 4,725 programs; 4,707 recordings analysed (18 have no scalar-clock recording). Three recordings hit the 3,600 s cap in the first pass (P7-srad-cuda, P9-tridiagonal-cuda, P9-mr-cuda) and were re-run with a 16,200 s cap (job 324010, 4:54:28): all three finished, both halves.
- Real-world heavy ids (hecbench-hungarian-1 buggy and fixed, colmap-new-1, raft-1 buggy and fixed): job 323983 (c26, 7:47:57). Analysis walls 20,982 s and 23,749 s (hungarian buggy, fixed), 23,392 s (colmap-new-1), 4,694 s and 4,669 s (raft-1 buggy, fixed); all rc=0.
- Analysis cap 84,600 s. Merge rule: X1b's (FINAL_SWEEP_B.md section 1 (i)): the first pass, overridden per (id, mode) by the 5,400 s pass and by the 84,600 s pass for the keys X1b kept (8 keys; an ERROR leaves the earlier rows). Partial-row rule (a run a cap stopped keeps the reports it wrote, Race if it holds one, else unfinished): P7-particlefilter-cuda (3 reps) is `partial(rc=1)` with 31 race reports in both halves, so Race in both.

### Rows that stay TIMEOUT / ERROR

- `P7-stencil1d-cuda` rep 1 and `P9-atomicCAS-cuda` rep 1: scalar-clock TIMEOUT (cap=84600) in X1b; TIMEOUT in both halves here.
- 16 runner-level rows with no recording (`missing-exe`, ERROR): `P6-bulkcpy-*` (12) and `P6-dsmem-*` (4); they are the ERR count of the cuHadron row.
- Real-world: `amrex-1` buggy and fixed (scalar-clock analysis ERROR at 82,800 s in T21b; buggy ERROR, fixed has no row) not re-run; `lightgbm-new-1` and `lightgbm-new-2` unscored.

## Parity report (rule on, against X1b)


# C4 step 2: parity, barrier-ordered rule ON, against X1b's shard CSVs

| X1b results dir | shard files compared | (id, mode, rep) rows compared |
|---|---|---|
| final-b | 112 | 14143 |
| final-b-long-sc | 2 | 6 |
| final-b-24h-sc | 8 | 8 |

Shard files X1b has and the re-analysis lacks: 0

Differences (verdict, reports_dedup, report_ids, report_lines, classes note; notes on analysed rows): **0**


Rows whose full `notes` string differs at all (scalar-clock rows): 0
Runner-level rows without a mode: 16 compared on verdict only; notes text differs in 0 (X1b `missing-exe`, re-analysis `no-trace-collected`)

## Merge report

# C4 step 3: merged re-analysis

- half `on`: 14127 first-pass scalar-clock rows, 2 keys overridden by the 5,400 s pass, 8 by the 84,600 s pass -> 14127 rows in merged/baselines-cuvein.csv
- parity of the merged ON half against X1b's merged scalar-clock rows: 14111 X1b rows, 14111 re-analysis rows, **0 differences**
- half `off`: 14127 first-pass scalar-clock rows, 2 keys overridden by the 5,400 s pass, 8 by the 84,600 s pass -> 14127 rows in merged/baselines-cuvein-bo0.csv

X1b's kept 84,600 s scalar-clock keys: 8; keys of the 84,600 s re-analysis not taken, per half: []


## 1. Tables: Table 6.1, union, three countings, litmus (CO-R next to vector-clock, scalar-clock and "cuVein edges only")

`make_tables.py --co-offline` (with `--collector-only`) adds a fourth cuVein column "collector-only, re-scored" (CO-R) from `merged/baselines-cuvein-cor.csv`. It is run in two sandbox trees (C3's method, `p_co_offline_tables.sh`): A = `--collector-only`, B = `--collector-only --co-offline`; `co_offline_strip_compare.py` removes every CO-R column, row, note segment and sentence clause from B and compares it with A: **0 diff lines** (the other columns are byte-identical). The outputs are `mt/BASELINES_A.md` and `mt/BASELINES_B.md` (and the summaries). A leak was found and fixed in `make_tables.py` on the way: CO-R rows would have fed the native-wall denominator of the revision-delta section; they are now excluded there and in `_ratios`. The overhead and memory sections leave the column out.


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


### Race-free-labelled programs that are Race in CO-R (with their pairs)

All 248 race-free-labelled programs that are Race in CO-R; `scalar-clock` shows which of them scalar-clock calls Clean (the 229 programs this change creates) and which are Race in scalar-clock too (19). Pairs = space:lo-hi:type. Source: `tables/race_free_cor_race_all.csv`.

<details><summary>248 programs</summary>

| suite | program | scalar-clock | CO-R reports | pairs |
|---|---|---|---|---|
| PI | `PI-conditional_edge_neighbors_block-DAG_100n_200e` | CLEAN | 1 | shared:0x280-0x2a0:RAW |
| PI | `PI-conditional_edge_neighbors_block_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-pull_node_neighbors_block_persistent_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2a0-0x2c0:RAW |
| PI | `PI-pull_node_neighbors_block_reverse-DAG_200n_400e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-pull_node_neighbors_block_shfl-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x340:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_persistent-DAG_100n_100e` | CLEAN | 1 | shared:0x2b0-0x2d0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse-DAG_5n_5e` | CLEAN | 1 | shared:0x2c0-0x2e0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse-DAG_100n_100e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x2b0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-pull_node_neighbors_block_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_reverse_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x320-0x340:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x2e0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x2d0:WAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2c0-0x2e0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-pull_node_neighbors_block_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent-counterDAG_5n_5e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_reverse_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x320-0x340:RAW |
| PI | `PI-pull_node_neighbors_block_shfl-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2e0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x2d0:WAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2c0-0x2e0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-pull_node_neighbors_block_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent-power_law_200n_1000e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse-DAG_100n_200e` | CLEAN | 1 | shared:0x2a0-0x2c0:RAW |
| PI | `PI-pull_node_neighbors_block_reverse_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x320-0x340:RAW |
| PI | `PI-pull_node_neighbors_block_shfl-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x2e0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse-power_law_200n_1000e` | CLEAN | 1 | shared:0x2c0-0x2e0:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-pull_node_neighbors_block_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent-DAG_100n_100e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse-DAG_200n_400e` | CLEAN | 1 | shared:0x2a0-0x2c0:RAW |
| PI | `PI-pull_node_neighbors_block_shfl-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2e0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse-DAG_100n_100e` | CLEAN | 1 | shared:0x2c0-0x2e0:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-pull_node_neighbors_block_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse-DAG_5n_5e` | CLEAN | 1 | shared:0x2a0-0x2c0:RAW |
| PI | `PI-pull_node_neighbors_block_shfl-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x2e0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x340:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-pull_node_neighbors_block_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2a0-0x2c0:RAW |
| PI | `PI-pull_node_neighbors_block_reverse-DAG_100n_200e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-pull_node_neighbors_block_shfl-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x2e0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x340:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block-DAG_200n_400e` | CLEAN | 1 | shared:0x280-0x2a0:RAW |
| PI | `PI-conditional_edge_neighbors_block_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block_persistent_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse-power_law_200n_1000e` | CLEAN | 1 | shared:0x2a0-0x2c0:RAW |
| PI | `PI-pull_node_neighbors_block_reverse-DAG_5n_5e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-pull_node_neighbors_block_shfl-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x340:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block-DAG_5n_5e` | CLEAN | 1 | shared:0x280-0x2a0:RAW |
| PI | `PI-conditional_edge_neighbors_block_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x310-0x330:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_reverse-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x2c0:WAW |
| PI | `PI-pull_node_neighbors_block-DAG_100n_200e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse-DAG_100n_100e` | CLEAN | 1 | shared:0x2a0-0x2c0:RAW |
| PI | `PI-pull_node_neighbors_block_reverse-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x310:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x340:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x320:WAW |
| PI | `PI-conditional_edge_neighbors_block-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x280-0x2a0:RAW |
| PI | `PI-conditional_edge_neighbors_block_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x310-0x330:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block-DAG_200n_400e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x2f0-0x310:RAW |
| PI | `PI-pull_node_neighbors_block_reverse-counterDAG_5n_5e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x310:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x340:WAW |
| PI | `PI-conditional_edge_neighbors_block-counterDAG_5n_5e` | CLEAN | 1 | shared:0x280-0x2a0:RAW |
| PI | `PI-conditional_edge_neighbors_block_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent-DAG_100n_200e` | CLEAN | 1 | shared:0x2b0-0x2d0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse-DAG_100n_200e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x310-0x330:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x2b0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block-DAG_5n_5e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x2f0-0x310:RAW |
| PI | `PI-pull_node_neighbors_block_reverse-power_law_200n_1000e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x310:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x340:WAW |
| PI | `PI-conditional_edge_neighbors_block-power_law_200n_1000e` | CLEAN | 1 | shared:0x280-0x2a0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent-DAG_200n_400e` | CLEAN | 1 | shared:0x2b0-0x2d0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse-DAG_200n_400e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x310-0x330:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x2b0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x2f0-0x310:RAW |
| PI | `PI-pull_node_neighbors_block_reverse-DAG_100n_100e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x310:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x2d0:WAW |
| PI | `PI-conditional_edge_neighbors_block-DAG_100n_100e` | CLEAN | 1 | shared:0x280-0x2a0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent-DAG_5n_5e` | CLEAN | 1 | shared:0x2b0-0x2d0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse-DAG_5n_5e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x310-0x330:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2b0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block-counterDAG_5n_5e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2f0-0x310:RAW |
| PI | `PI-pull_node_neighbors_block_reverse_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x320-0x340:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x310:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x2d0:WAW |
| PI | `PI-conditional_edge_neighbors_block_persistent-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2b0-0x2d0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x310-0x330:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x2b0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block-power_law_200n_1000e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent-DAG_100n_200e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse_cond-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2f0-0x310:RAW |
| PI | `PI-pull_node_neighbors_block_reverse_cond-DAG_200n_400e` | CLEAN | 1 | shared:0x320-0x340:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x310:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2d0:WAW |
| PI | `PI-conditional_edge_neighbors_block_persistent-counterDAG_5n_5e` | CLEAN | 1 | shared:0x2b0-0x2d0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x2d0-0x2f0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse-DAG_100n_200e` | CLEAN | 1 | shared:0x2c0-0x2e0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse-counterDAG_5n_5e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x310-0x330:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2b0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x330:WAW |
| PI | `PI-pull_node_neighbors_block-DAG_100n_100e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent-DAG_200n_400e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse_cond-power_law_200n_1000e` | CLEAN | 1 | shared:0x2f0-0x310:RAW |
| PI | `PI-pull_node_neighbors_block_reverse_cond-DAG_5n_5e` | CLEAN | 1 | shared:0x320-0x340:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x80-0x310:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse-DAG_200n_400e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x80-0x2d0:WAW |
| PI | `PI-conditional_edge_neighbors_block_persistent-power_law_200n_1000e` | CLEAN | 1 | shared:0x2b0-0x2d0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse-DAG_200n_400e` | CLEAN | 1 | shared:0x2c0-0x2e0:RAW |
| PI | `PI-conditional_edge_neighbors_block_persistent_reverse_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-conditional_edge_neighbors_block_reverse-power_law_200n_1000e` | CLEAN | 1 | shared:0x330-0x350:RAW |
| PI | `PI-conditional_edge_neighbors_block_shfl-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x2b0:WAW |
| PI | `PI-conditional_edge_neighbors_block_shfl_persistent_reverse-power_law_200n_1000e` | CLEAN | 1 | shared:0x80-0x300:WAW |
| PI | `PI-pull_node_neighbors_block_cond-DAG_100n_200e` | CLEAN | 1 | shared:0x2e0-0x300:RAW |
| PI | `PI-pull_node_neighbors_block_persistent-DAG_5n_5e` | CLEAN | 1 | shared:0x290-0x2b0:RAW |
| PI | `PI-pull_node_neighbors_block_persistent_reverse_cond-DAG_100n_100e` | CLEAN | 1 | shared:0x2f0-0x310:RAW |
| PI | `PI-pull_node_neighbors_block_reverse_cond-counterDAG_200n_1000e` | CLEAN | 1 | shared:0x320-0x340:RAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent-DAG_100n_200e` | CLEAN | 1 | shared:0x80-0x2e0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_persistent_reverse-DAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2f0:WAW |
| PI | `PI-pull_node_neighbors_block_shfl_reverse-counterDAG_5n_5e` | CLEAN | 1 | shared:0x80-0x2d0:WAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 3 | shared:0x1e0-0x420:WAW shared:0x420-0x420:WAW shared:0x420-0xcc0:RAW |
| P4 | `P4-reduction-norace-small` | RACE | 4 | global:0x3b0-0xf60:WAW global:0x550-0xf60:WAW global:0x6e0-0xf60:WAW global:0xab0-0x1690:WAW |
| P4 | `P4-reduction-norace-large` | RACE | 4 | global:0x3b0-0xf60:WAW global:0x550-0xf60:WAW global:0x6e0-0xf60:WAW global:0xab0-0x1690:WAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 1 | shared:0x310-0x310:WAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 3 | shared:0x140-0x2e0:WAW shared:0x2e0-0x2e0:WAW shared:0x2e0-0x10b0:RAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 3 | shared:0x140-0x340:WAW shared:0x340-0x340:WAW shared:0x340-0x740:RAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 1 | shared:0x350-0x350:WAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 3 | shared:0x180-0x380:WAW shared:0x380-0x380:WAW shared:0x380-0xc50:RAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 2 | shared:0xf0-0x870:RAW shared:0x2e0-0x2e0:WAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 3 | shared:0x130-0x380:WAW shared:0x380-0x380:WAW shared:0x380-0x980:RAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 2 | shared:0x170-0xf20:RAW shared:0x370-0x370:WAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 1 | shared:0x320-0x320:WAW |
| P6 | `P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed` | RACE | 44 | global:0x890-0x890:WAW global:0x890-0x9a0:WAW global:0x890-0x9c0:WAW global:0x890-0x9e0:WAW global:0x890-0x9f0:WAW global:0x890-0xa00:WAW global:0x890-0xa10:WAW global:0x890-0xa20:WAW global:0x890-0xa60:WAW global:0x9a0-0x9a0:WAW global:0x9a0-0x9c0:WAW global:0x9a0-0x9e0:WAW global:0x9a0-0x9f0:WAW global:0x9a0-0xa00:WAW global:0x9a0-0xa10:WAW global:0x9a0-0xa20:WAW global:0x9a0-0xa60:WAW global:0x9c0-0x9c0:WAW global:0x9c0-0x9e0:WAW global:0x9c0-0x9f0:WAW global:0x9c0-0xa00:WAW global:0x9c0-0xa10:WAW global:0x9c0-0xa20:WAW global:0x9c0-0xa60:WAW global:0x9e0-0x9e0:WAW global:0x9e0-0x9f0:WAW global:0x9e0-0xa00:WAW global:0x9e0-0xa10:WAW global:0x9e0-0xa20:WAW global:0x9e0-0xa60:WAW global:0x9f0-0x9f0:WAW global:0x9f0-0xa00:WAW global:0x9f0-0xa10:WAW global:0x9f0-0xa20:WAW global:0x9f0-0xa60:WAW global:0xa00-0xa00:WAW global:0xa00-0xa10:WAW global:0xa00-0xa20:WAW global:0xa00-0xa60:WAW global:0xa10-0xa10:WAW global:0xa10-0xa20:WAW global:0xa10-0xa60:WAW global:0xa20-0xa20:WAW global:0xa20-0xa60:WAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 3 | shared:0x1f0-0x450:WAW shared:0x450-0x450:WAW shared:0x450-0x1150:RAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Block_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 1 | shared:0x2a0-0x2a0:WAW |
| P4 | `P4-graph-coloring-norace-small` | CLEAN | 6 | global:0x160-0x4b0:WAR global:0x160-0x4d0:WAR global:0x160-0x550:WAR global:0x4e0-0x690:WAR global:0x500-0x6b0:WAR global:0x580-0x730:WAR |
| P3 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 3 | shared:0x170-0x340:WAW shared:0x340-0x340:WAW shared:0x340-0x8d0:RAW |
| P4 | `P4-graph-coloring-norace-large` | CLEAN | 6 | global:0x160-0x4b0:WAR global:0x160-0x4d0:WAR global:0x160-0x550:WAR global:0x4e0-0x690:WAR global:0x500-0x6b0:WAR global:0x580-0x730:WAR |
| P3 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 2 | shared:0x130-0x1180:RAW shared:0x280-0x280:WAW |
| P3 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 3 | shared:0x1a0-0x340:WAW shared:0x340-0x340:WAW shared:0x340-0x1280:RAW |
| P4 | `P4-graph-connectivity-norace-small` | CLEAN | 6 | global:0x160-0x260:WAR global:0x160-0x400:WAR global:0x160-0x410:WAR global:0x290-0x440:WAR global:0x430-0x5e0:WAR global:0x440-0x5f0:WAR |
| P3 | `P3-CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Block_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug-100n` | RACE | 2 | shared:0x170-0xad0:RAW shared:0x340-0x340:WAW |
| P4 | `P4-graph-connectivity-norace-large` | CLEAN | 6 | global:0x160-0x260:WAR global:0x160-0x400:WAR global:0x160-0x410:WAR global:0x290-0x440:WAR global:0x430-0x5e0:WAR global:0x440-0x5f0:WAR |
| P9 | `P9-crs-cuda` | CLEAN | 7 | shared:0x460-0x810:WAR shared:0x550-0x810:WAR shared:0x570-0x970:WAR shared:0x580-0x970:WAR shared:0x5a0-0x970:WAR shared:0x640-0x970:WAR shared:0x690-0x970:WAR |

</details>


## 2. Real-world recall (T21b) and candidates (T21c)

CO-R = the real-world scalar-clock recordings re-analysed with the rule off, attributed by `rw_attribute.py` and scored by `rw_score.py`, the scripts that produced `eval/results/realworld/recall.csv` and `realworld_t21c` (run from copies of their branches under `~/c4rw`; the only edit is `RW_MODES`). Results: `realworld/recall.csv`, `realworld_t21c/recall.csv`. T21c is scored with `--exclude lightgbm-new-1,lightgbm-new-2`, as T21c did.

**Confirmed (CO-R DETECTED):** CCCL top-k (cccl-3 DR), Ginkgo range-minimum (ginkgo-5 DR), Kokkos rw_sum (kokkos-5 DR), RAFT select_k (raft-1 DR), and PCL's data-race half (pcl-new-1 DR). Refuted: none.


## Recall set (T21b): per target and component, CO-R next to vector-clock, scalar-clock and the edges-only run (C2)

CO-R rows come from `eval/results/co-offline/realworld/recall.csv` (rw_score.py of study/realworld-recall on the re-analysed, re-attributed scalar-clock recordings). `NOT-SCORED` = the id has no row: its scalar-clock analysis did not finish (amrex-1: ERROR analysis-timeout at 82,800 s in T21b, not re-run).

| target | variant | comp | vector-clock | scalar-clock | edges only (C2) | CO-R | CO-R n_race / n_sc |
|---|---|---|---|---|---|---|---|
| amrex-1 | buggy | DR | MISSED | MISSED | MISSED | stays ERROR (not re-run) | / |
| amrex-1 | fixed | - | — | — | NOT-SCORED | NOT-SCORED | / |
| bitsandbytes-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 65/0 |
| bitsandbytes-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 64/0 |
| cccl-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 30/0 |
| cccl-1 | fixed | - | STILL | STILL | STILL | STILL | 30/0 |
| cccl-2 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 493/0 |
| cccl-2 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 486/0 |
| cccl-3 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 51/8 |
| cccl-3 | buggy | SC | DETECTED | DETECTED | DETECTED | DETECTED | 51/8 |
| cccl-3 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 51/8 |
| cccl-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/9 |
| cccl-4 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/9 |
| cmssw-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 7/0 |
| cmssw-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 0/8 |
| ginkgo-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 15/0 |
| ginkgo-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| ginkgo-5 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 6/0 |
| ginkgo-5 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| hecbench-dxtc2-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 114/0 |
| hecbench-dxtc2-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 3/0 |
| hecbench-hungarian-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 298/251 |
| hecbench-hungarian-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 259/253 |
| hecbench-morphology-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 8/0 |
| hecbench-morphology-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 8/0 |
| hecbench-surfel-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 14/0 |
| hecbench-surfel-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| kokkos-5 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 24/0 |
| kokkos-5 | fixed | - | CLEAN | CLEAN | RESIDUAL | RESIDUAL | 23/0 |
| kokkos-6 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 32/0 |
| kokkos-6 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 26/0 |
| lit-arrayfire-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 6/0 |
| lit-arrayfire-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 4/0 |
| lit-exllamav3-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 84/0 |
| lit-exllamav3-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 64/0 |
| lit-fbgemm-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| lit-fbgemm-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| lit-shoc-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 52/0 |
| lit-shoc-1 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 52/0 |
| lit-shoc-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 40/0 |
| llamacpp-2 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 8/0 |
| llamacpp-2 | fixed | - | CLEAN | CLEAN | STILL | STILL | 8/0 |
| llamacpp-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1/0 |
| llamacpp-4 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| llamacpp-5 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 1032/0 |
| llamacpp-5 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 768/0 |
| opencv-2 | buggy | SC | DET-as-DR | DET-as-DR | DET-as-DR | DET-as-DR | 411/0 |
| opencv-2 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 8/0 |
| pytorch-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 3/0 |
| pytorch-1 | fixed | - | CLEAN | CLEAN | STILL | STILL | 3/0 |
| pytorch-3 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/0 |
| pytorch-3 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| pytorch-4 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 2/0 |
| pytorch-4 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 1/0 |
| pytorch_cluster-1 | buggy | DR | DETECTED | DETECTED | DETECTED | DETECTED | 12/0 |
| pytorch_cluster-1 | fixed | - | CLEAN | CLEAN | CLEAN | CLEAN | 0/0 |
| raft-1 | buggy | DR | DETECTED | DETECTED | MISSED | DETECTED | 32/2 |
| raft-1 | buggy | SC | DETECTED | DETECTED | DETECTED | DETECTED | 32/2 |
| raft-1 | fixed | - | RESIDUAL | RESIDUAL | RESIDUAL | RESIDUAL | 32/2 |

**Counts** (rows of each mode; CO-R: ids without a row are not in the count):

| components | outcome | vector-clock | scalar-clock | edges only (C2) | CO-R |
|---|---|---|---|---|---|
| buggy, data-race components | DETECTED | 25 | 25 | 21 | 25 |
| buggy, data-race components | MISSED | 1 | 1 | 5 | 0 |
| buggy, data-race components | **total** | 26 | 26 | 26 | 25 |
| buggy, strong-conflict components | DETECTED | 2 | 2 | 2 | 2 |
| buggy, strong-conflict components | DETECTED-AS-DR | 3 | 3 | 3 | 3 |
| buggy, strong-conflict components | **total** | 5 | 5 | 5 | 5 |
| fixed builds | CLEAN-FOR-PAIR | 20 | 20 | 17 | 17 |
| fixed builds | NOT-SCORED | 0 | 0 | 1 | 0 |
| fixed builds | RESIDUAL-AS-EXPECTED | 6 | 6 | 7 | 7 |
| fixed builds | STILL-REPORTED | 1 | 1 | 3 | 3 |
| fixed builds | **total** | 27 | 27 | 28 | 27 |

## The detections the edges-only run missed

| target (component) | scalar-clock | edges only (C2) | CO-R | verdict |
|---|---|---|---|---|

Buggy data-race components DETECTED by scalar-clock and MISSED by the edges-only run (computed): [('cccl-3', 'DR'), ('ginkgo-5', 'DR'), ('kokkos-5', 'DR'), ('raft-1', 'DR')]

| CCCL top-k (cccl-3, DR) | DETECTED | MISSED | DETECTED | detected |
| Ginkgo range-minimum (ginkgo-5, DR) | DETECTED | MISSED | DETECTED | detected |
| Kokkos rw_sum (kokkos-5, DR) | DETECTED | MISSED | DETECTED | detected |
| raft-1 (raft-1, DR) | DETECTED | MISSED | DETECTED | detected |

## Candidate set (T21c)

| id | component | expected | scalar-clock | edges only (C2) | CO-R | CO-R n_race / n_sc |
|---|---|---|---|---|---|---|
| autogptq-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 128/0 |
| colmap-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 620/0 |
| cuml-tsne-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 67/28 |
| droidslam-new-1-buggy | SC | SC | DET-as-DR | DET-as-DR | DET-as-DR | 67/0 |
| llamacpp-open-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 17/0 |
| llamacpp-open-2-buggy | DR | DR | MISSED | — | DETECTED | 16/0 |
| llamacpp-open-2-fixed | - | DR | CLEAN | — | STILL | 16/0 |
| llmc-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 8/0 |
| llmc-new-2-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 1/0 |
| llmc-new-3-buggy | DR | DR | DETECTED (family) | DETECTED (family) | DETECTED (family) | 2/0 |
| llmc-new-3-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 9/0 |
| mmcv-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 2/0 |
| opencv_contrib-new-1-buggy | DR | DR+SC | DETECTED | DETECTED | DETECTED | 64/0 |
| opencv_contrib-new-1-buggy | SC | DR+SC | DET-as-DR | DET-as-DR | DET-as-DR | 64/0 |
| openpcdet-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 3/0 |
| pcl-new-1-buggy | DR | DR+SC | DETECTED | MISSED | DETECTED | 657/0 |
| pcl-new-1-buggy | SC | DR+SC | DET-as-DR | DET-as-DR | DET-as-DR | 657/0 |
| pointnet2pt-fps-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 1/0 |
| pytorch_cluster-new-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 15/0 |
| sglang-open-1-buggy | DR | DR | DETECTED | DETECTED | DETECTED | 1/0 |

scalar-clock: {'DETECTED': 14, 'DETECTED-AS-DR': 3, 'MISSED': 1, 'DETECTED (family)': 1}

edges only (C2): {'DETECTED': 13, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1, 'MISSED': 1}

CO-R: {'DETECTED': 15, 'DETECTED-AS-DR': 3, 'DETECTED (family)': 1}

PCL (pcl-new-1) data-race half: scalar-clock DETECTED, edges only MISSED, CO-R DETECTED


Other differences from scalar-clock: the fixed builds `kokkos-5` (CLEAN to RESIDUAL), `llamacpp-2` and `pytorch-1` (CLEAN to STILL-REPORTED) change as in the edges-only run; in the candidate set `llamacpp-open-2` buggy is MISSED in scalar-clock and DETECTED in CO-R, and its fixed build is CLEAN in scalar-clock and STILL-REPORTED in CO-R (n_race 16 in both builds), so that detection does not separate the buggy build from the fixed one.

## 3. Program level, CO-R against scalar-clock

The program-level table, the by-label table, the race-free list and the "other differences" lines are in section 1 (block "Program level"). Files: `tables/program_level_summary.csv`, `tables/program_level_diffs.csv`.


## 4. Pair level: pairs CO-R reports and scalar-clock orders

Scalar-clock recordings analysed with the rule on and off: 4707 of 4725 programs; not analysed: {'no scalar-clock recording': 18}.

CO-R reports, scalar-clock does not: **1016 pairs** in 893 programs. Their scalar-clock record is ORDERED by the barrier clock in every launch: yes, all of them.

(a) pairs with a cuVein edge: **1016**; (b) extended edges and rescued edges: **0** (candidate with no edge: 0, rescued edge: 0).

**All pairs CO-R reports that scalar-clock orders, by control-flow shape (X5's bins, same order as tab:eval-shapes)**

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

**(a) pairs with a cuVein edge**

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

**(b) extended and rescued edges**

| Suite | Programs with a pair | Pairs | Loop around the barrier | Warp barrier between | Exit before the barrier | Barrier on one branch | Other | not among X5's |
|---|---|---|---|---|---|---|---|---|
| Indigo3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Indigo 1.3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ECL graph codes | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR applications | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ScoR litmus kernels | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cuHadron | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, other applications | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| HeCBench, SuperCollider's 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **All** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**(a) against C3's S1 (1016 pairs)**: (a) has 1016 pairs; common 1016; in (a) only 0; in S1 only 0.

| set | reason | pairs |
|---|---|---|

Every pair of the two lists, with its reason: `pairs_a_vs_S1.csv`.



## 5. CO-R against C1 (cuVein edges only), per suite

Pairs: reported pairs of CO-R (scalar-clock recording, rule off) against reported pairs of C1 (separate recording). A CO-R-only pair is classed by its tags in CO-R: `e` = event-stream candidate with no edge (extended edge), `r` = edge rescued by the sync pass, neither = other. A C1-only pair is classed RMW points when CO-R orders it by an R3 chain (the `c` flag, from hb_rmw_points), otherwise other.

 (separate recordings)

reported pairs of CO-R (scalar-clock recording, rule off) against reported pairs of C1 (collector-only recording). Programs analysed in both: 
4707 of 4725.

| suite | pairs in both | CO-R only: extended edge | CO-R only: rescue | CO-R only: other | C1 only: RMW points | C1 only: other | programs with a CO-R-only pair | programs with a C1-only pair |
|---|---|---|---|---|---|---|---|---|
| Indigo3 | 1266 | 181 | 30 | 1 | 0 | 7 | 58 | 4 |
| Indigo 1.3 | 9810 | 6889 | 248 | 431 | 0 | 87 | 866 | 32 |
| ECL graph codes | 102 | 4 | 0 | 0 | 16 | 0 | 4 | 4 |
| ScoR applications | 210 | 45 | 10 | 21 | 10 | 1 | 14 | 3 |
| ScoR litmus kernels | 19 | 2 | 0 | 1 | 0 | 0 | 2 | 0 |
| cuHadron | 22 | 68 | 3 | 1 | 0 | 1 | 4 | 1 |
| HeCBench, other applications | 66 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| HeCBench, SuperCollider's 10 | 52 | 8 | 6 | 0 | 0 | 0 | 1 | 0 |
| **All** | 11547 | 7197 | 298 | 455 | 26 | 96 | 950 | 44 |

Pairs in "other": **551** (each is a finding; `pairs_cor_vs_c1.csv`, kind column).
  - C1 only: CO-R has no record of the pair — 96
  - CO-R only: C1 — 20
  - CO-R only: C1 has no record of the pair — 435


### Anything in "other" is a finding

- **CO-R only, C1 has no record of the pair (435 pairs: Indigo 1.3 431, Indigo3 1, ScoR applications 2, cuHadron 1):** the pair has a cuVein edge in X1b's recording (it is not an extended or rescued edge) and no edge in C1's separate recording, so C1 never judged it. Cause not established beyond the two recordings differing.
- **CO-R only, C1 orders the pair (20 pairs: P4 `uts-*` 19, P5 `race_interblock_none-lock_rtraw` 1; C1 tag `ORDERED:None`):** C1 orders the pair by a certificate, CO-R does not. `race_interblock_none-lock_rtraw` is the program C1 misses and scalar-clock reports (litmus table). The mechanism is not established in this run.
- **C1 only, CO-R has no record of the pair (96 pairs: Indigo 1.3 87, Indigo3 7, ScoR applications 1, cuHadron 1):** the converse; no edge in X1b's recording.
- The pair sets are per recording; C1 and X1b are different runs of the same programs, so the pair set differs with the schedule.


## Program level: CO-R against C1's collector-only run (separate recordings), per suite

Programs whose verdict differs (RACE / CLEAN / TIMEOUT / ERROR as recorded), with the cause of the program's differing pairs (the causes of the CO-R-only pairs when CO-R is Race, of the C1-only pairs when C1 is Race; a program can have several).

| suite | programs in both | same verdict | C1 Clean → CO-R Race | C1 Race → CO-R Clean | other differences | of the first: extended edge | rescue | other | none found (no differing pair) |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 400 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| PI | 4130 | 4104 | 26 | 0 | 0 | 25 | 0 | 1 | 0 |
| P3 | 60 | 60 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P4 | 28 | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| P5 | 33 | 32 | 1 | 0 | 0 | 1 | 0 | 1 | 0 |
| P6 | 34 | 33 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| P7 | 14 | 13 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| P9 | 10 | 9 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| **all** | 4709 | 4679 | 28 | 0 | 2 | 26 | 1 | 2 | 0 |

## Pair pass: recordings whose first pair-level analysis hit the 3,600 s cap

- `P7-srad-cuda`: first pass rule on `analysis-timeout` (3603.8 s), rule off `analysis-timeout` (3603.7 s); re-run with a 16,200 s cap: rule on `ok` (8401.4 s), rule off `ok` (8294.1 s)
- `P9-tridiagonal-cuda`: first pass rule on `analysis-timeout` (3603.7 s), rule off `analysis-timeout` (3603.7 s); re-run with a 16,200 s cap: rule on `ok` (8814.3 s), rule off `ok` (8848.8 s)
- `P9-mr-cuda`: first pass rule on `analysis-timeout` (3603.7 s), rule off `analysis-timeout` (3603.7 s); re-run with a 16,200 s cap: rule on `ok` (6897.4 s), rule off `ok` (6904.4 s)

## S1 pairs not in (a)

| program | space | pc lo | pc hi | reason |
|---|---|---|---|---|

(a) and S1 hold the same pairs: both difference lists above are empty.


## 6. What this cannot see

CO-R re-scores recordings that were taken with the barrier clock on. Extended edges and rescues that the barrier clock ordered were dropped at run time, so they are not in the kernel JSONs and CO-R cannot report them: CO-R's false positives are a lower bound of what a collector-only run reports (the (b) class above is 0 for this reason, not because such pairs do not exist). It measures no run time and no memory (the recordings are the scalar-clock ones), so Figure 6 and the memory table keep C1's numbers, labelled "cuVein edges only". The pair-level analysis times are not overhead figures.

## Pool-safety

The env toggle behind `parallel.py analyze --both-barrier-orders` (`CUVEIN_BARRIER_ORDER`, set around `analyze_one` in `cmd_analyze`) is not pool-safe and must move into `_analyze_reports` when this branch is rebased onto X7 Part A.

## Files

`eval/results/co-offline/`: `final-b*/` (shard CSVs, both halves, timing), `merged/` (merged on / off / `baselines-cuvein-cor.csv`), `parity_shards.md`, `merged_report.md`, `pairs/` (per-program pair records, on and off), `realworld/`, `realworld_t21c/` (CSVs, attribution, `recall.csv`), `mt/` (sandbox BASELINES A and B), `tables/`. Scripts in `eval/baselines/setup/co_offline/` and `p_co_*.sh`.

