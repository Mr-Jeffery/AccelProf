# C1: collector-only mode (eval/collector-only from eval/final-tables d484e42)

Step 1 (2026-10-28), steps 2 and 3 (2026-10-28/29) below. Branch `eval/collector-only`, unmerged; harness commits c45e1b3, 1dd5c05 (step 1: fd03443), aa15012 (step 2).

## Step 1a: the verdict path on a kernel JSON without hb_* keys

Code path: `parallel.analyze_one` -> `_analyze_capped` -> `run_cuvein._analyze_reports` -> `sync_dominance.analyze(dot, kernel_N.json)`
for every kernel JSON of the saved store; `make_tables.py` reads only the CSV rows (`classes_note`), not the JSONs.
Runtime and harness read the same `python/` (diff of `~/AccelProf/python` and `wt-co/python`: empty).

With no `hb_*` key (`python/sync_dominance.py`, analyze()):
- `hb_races` is None, so `raced_pcsets` is None, `observed_dyn` and `legacy_war_writers` are empty, `model_bug` is None, `a2_uncertain` is None.
  `judge()` takes its "static leg only (no HbClock)" branch (sync_dominance.py:1527-1538).
- `use_aggregates(trace)` is True (no `hb_events`), `aggregated_sync_pass` returns None (no `hb_sync_pass`), the replay
  `barrier_only_pairs` returns None (no `hb_events`): `offline_pass()` is None, so `sync_pcsets` stays None.
  `trace_rmw_points` returns (None, None): R3 keeps region dominance for its release/acquire points (the T12 instance points are off).
- R1 (barrier dominance), R3 (PC-level chain over the `sync_edges` the PCDepGraph edges show), and R2 (the coherence class) run unchanged.
- A conflicting pair no certificate orders: `r1_ordered or chain_ordered` false; `sync_pcsets is not None` false, so the
  "barrier-ordered" arm is not taken; then `strong` (R2 at the widest observed distance) gives SC, else RACE. `hb_class` is None for every
  verdict, so `classes_note` counts them `race:<n>` and `sc:<n>`.
- Nothing missing is read as "ordered". What is skipped is listed in `skipped_edges`: `cold_miss`; `read_read`; `intra_thread_only` (an edge at
  intra-thread distance with no `same_inst` weight; with HB data `observed_dyn` rescues such an edge as cross-thread, here it cannot);
  `rmw_pair_morally_strong`.
- Off without the sync pass: `CUVEIN_EVENT_CANDIDATES` has no effect (`event_pairs` = `sync_pcsets | raced_pcsets` = empty, so no
  pair that has no PCDepGraph edge is judged), the `observed_dyn` rescue, the barrier-only clock (so the barrier-in-loop
  reduction no certificate can show is a RACE here and `barrier-ordered` here never occurs), the `hb_races` veto and the
  `model_bug` annotation, the event-stream writers of the benign-read test, `r3_loc_closure` input from observed RMW points. `CUVEIN_BARRIER_PASS` is moot.
- Consequences: collector-only can only add RACE or SC relative to scalar-clock where a barrier-ordered pair has no dominance proof; it
  can lose a race that only the event stream shows (a pair with no edge, or an edge recorded at intra-thread distance).

## Step 1b: the harness mode

The existing path scores collector-only JSONs; no rule and nothing a rule reads changed. Added: `hb_modes.COLLECTOR_ONLY` (in `ALL_MODES`,
not in `MODES`, so the default two-mode sweeps are unchanged), `blib.base_env` (no `YOSEMITE_HB_*` variable, `YOSEMITE_HB_STATS` dropped), `meta.hb_shards`
gets a 0 for the mode, `meta.modes.collector-only.{hb_trace=false, yosemite_env}`, `-v` on the accelprof command of this mode (X1-follow's
collector-only runs used `-v`; the per-drain lines are the only record count the mode has; stored per rep as `drains` / `drained_records`, the
row's `events=` is the saved rep's `drained_records`), `setup/p_co.sh` (X1b's `p_final.sh` with one mode; no `BASELINE_HB_DUMP`, `YOSEMITE_HB_STATS`, `BASELINE_HB_SHARDS`).
No change in `nv-compute/`, `sanalyzer/`, `python/hb_oracle.py`, `python/sync_dominance.py`.

## Step 1c: tests

`python/test_collector_only.py` on `python/testdata/collector_only.cu` (1 block, 2 warps; recorded in both modes with the installed runtime):

| kernel | collector-only | scalar-clock |
|---|---|---|
| `co_straight` (write, `__syncthreads`, cross-warp read) | ORDERED (dominance) | ORDERED |
| `co_loop_red` (reduction, one barrier in the loop, pairs loop-carried around it) | 1 ORDERED + 1 RACE (RAW) | 0 RACE, `barrier-ordered` |
| `co_loop_tile` (write, barrier, read, barrier, in a loop) | ORDERED (dominance, both pairs) | ORDERED |
| `co_missing` (no barrier) | RACE | RACE |

The brief's "tile kernel loop variant" has no fixture in the repo; the loop-carried case above is the reduction shape (`coherent_ldst.cu` `reduce_barrier`).
A tile loop with two barriers is certified by R1 and is ORDERED in collector-only mode too (row 3).
Green set (`python/test_sync_dominance.py test_barrier_soundness.py test_coherent_ldst.py test_atomic_memory_model.py test_barrier_exit.py
test_hb_substitutions.py test_cp_async.py` + the new file), job 322543 on c24, wt-co harness copy: **306 passed, 0 skipped**; `test_no_dump.py`: **31 passed**.
(CLAUDE.md A4's "305 passed, 2 skipped / 27" predates T22-T24; the new file accounts for 5 of the 306.)

## Step 1d: dry run

Jobs 322545 (c45e1b3, before `-v`) and 322547 (`1dd5c05`, dirty=0), c24 (AMD EPYC 7302P, 125 GB, driver 580.82.07), `REPS=1`, 16 ids (2 per pset
P1 PI P3 P4 P5 P6 P7 P9 from `setup/co_dryrun_ids.txt`), store `/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11-co-dryrun`, CSV
`eval/results/collector-only-dryrun/`, log `eval/x_logs/co-dryrun2-322547_0.log`.
- meta: `modes` has only `collector-only`, `hb_trace=false`, `yosemite_env=[YOSEMITE_ATOMIC_SCOPE_FILE]`, `hb_shards.collector-only=0`.
- 120 kernel JSONs: all carry `nodes` and `edges`, none carries an `hb_*` key (keys: edges, kernel, nodes, sample_stride_bytes, shadow_memory_granularity_bytes, tool).
- Runtime: libsanalyzer `5a20fd14ab6c6806`, collector `b746b4dd23e90f46`, fatbin `a2d7368bc1c61986`, late `e96343121c74ca0a`, runtime HEAD f551ca00947e.
- Peak RSS: `blib.run_timed(poll_mem=True)`, the function X1b used (summed VmRSS poll; unchanged by C1). Dry run 812-1,235 MB; X1b scalar-clock on the same ids 847-952 MB
  (P4-P6, P1, P3, PI) and 2,054-3,717 MB (P7, P9).
- Verdicts: RACE on P4 x2, P6 x2, P1-CC, PI persistent, P7-bfs; CLEAN on the other 9 (P5 x2 and P3 x2 carry an `sc` report only).
- Analyzer worker count: `accelprof -n 1`, as in `parallel.py` for X1b's runs. X1b's meta also carries `hb_shards` {vector-clock 0, scalar-clock 16}; the
  sync pass does not exist in this mode, so the mode's value is 0.

## Runtime and hardware

| component | sha256[:16] | where checked |
|---|---|---|
| `build/sanalyzer/lib/libsanalyzer.so` (what the collector's RPATH loads) | `5a20fd14ab6c6806` | installed file before step 1 (login node, 2026-10-28); `runtime.libsanalyzer` of all 4,725 + 5 + 1 + 65 + 65 `meta.json` |
| `lib/libcompute_sanitizer.so` | `b746b4dd23e90f46` | every `meta.json` |
| `gpu_patch_pc_dependency.fatbin` | `a2d7368bc1c61986` | every `meta.json` |
| `gpu_patch_pc_dependency_late.fatbin` | `e96343121c74ca0a` | every `meta.json` |
| runtime checkout HEAD | `f551ca00947e` | every `meta.json` |
| harness | `eval/collector-only` fd03443 (main, PI, 5,400 s; `dirty=0`), aa15012 (84,600 s, parity A and B; `dirty=0`) | every `meta.json` (`harness_head`, `harness_dirty`) |

All five stores show 0 `meta.json` whose four hashes differ from X1b's. The installed `libsanalyzer.so` equals X1b's (§0 of `FINAL_SWEEP_B.md`), so the stop condition did not apply.

nvidia-smi line (name, compute capability, driver), counted over the 124 job logs: `NVIDIA GeForce RTX 4060 Ti, 8.9, 580.82.07` 109 jobs; `580.95.05` 6; `615.71.09` 7; `580.105.08` 2. Host CPUs seen: AMD EPYC 8124P (c61-c64, c68, c69; 188 GB), 7302P (c40-c43, c74-c79; 125 GB), 9115 (c55, c56; 125 GB). Analyzer: `accelprof -n 1`, as in X1b; X1b's `hb_shards` (scalar-clock 16) does not apply to this mode (0).

## Coverage

Manifest ids in P1, PI, P3, P4, P5, P6, P7, P9: **4,725**, every one with a row in `eval/results/collector-only/merged/baselines-cuvein.csv` (14,141 rows: 14,125 with mode `collector-only`, 16 runner-level `missing-exe` rows).

| pass | job | tasks | cap | reps | node-hours (sum of task Elapsed) | stores |
|---|---|---|---|---|---|---|
| 1,200 s, main (P1 P3 P4 P5 P6 P7 P9, 595 ids) | 322638 | 48 | 1,200 s | 3 | 20.10 | `/mnt/beegfs/fzheng4/cuvein_traces/final-2026-11-co` |
| 1,200 s, PI (4,130 ids) | 322639 | 64 | 1,200 s | 3 | 7.11 | same store |
| 5,400 s, the 5 ids with a TIMEOUT rep | 322941 | 5 | 5,400 s | 3 | 19.08 | `final-2026-11-co-long` |
| 84,600 s, the 1 id still TIMEOUT | 323036 | 1 | 84,600 s | 1 | 10.12 | `final-2026-11-co-24h` |
| parity set, recording A (65 ids of `t5b_parity_ids.txt`) | 322947 | 3 | 1,200 s | 3, kept apart | 1.44 | `final-2026-11-co-parity-a` |
| parity set, recording B | 323033 | 3 | 1,200 s | 3, kept apart | 1.39 | `final-2026-11-co-parity-b` |
| dry runs (step 1) | 322545, 322547 | 2 | 1,200 s | 1 | not summed | `final-2026-11-co-dryrun` |

Total of the six sweep jobs: **59.24 node-hours** on `rtx4060ti16g`, 124 tasks, all COMPLETED, all with `== done rc=0`; no `NODE-PROBLEM` exit in any log, so no task was resubmitted. At most 8 GPU nodes at a time were mine (main/PI `%8`; 5 + 3 during the 5,400 s pass and recording A); C2's array held 2. Excluded: c0, c1, c2, c21, c22, c23, c34, c37, c46, c54 (parity B also c41-c43, so that every id's second recording ran on another node).
The ssh path to ARC was down from 12:09 to 18:56 EDT on 2026-10-28; the jobs ran through it (the poller only reads `sacct`).

First pass: 5 ids with a TIMEOUT rep at 1,200 s (`setup/co_long_ids.txt`): P7 heartwall, particlefilter, stencil1d; P9 knn, tridiagonal. At 5,400 s heartwall (2,347.6 s), particlefilter (3,200.2 s), knn (3,739.8 s) and tridiagonal (4,551.3 s) finish; stencil1d times out 3 of 3 (peak RSS 3,433 MB, 79-86 kernels); at 84,600 s it finishes: 36,373.3 s, CLEAN, 85,983,231,000 records, 1,000 kernels, peak RSS 4,240 MB.

Residual keys (no RACE/CLEAN verdict after all passes):

| id | rows | verdict | reason |
|---|---|---|---|
| 16 P6 ids (`P6-bulkcpy-*`, `P6-dsmem-*`) | 16 | ERROR | `missing-exe`: the manifest's binary is not present; the same 16 rows are `missing-exe` in X1b's merged file |
| `P9-atomicCAS-cuda` | 3 reps | ERROR | `analysis-timeout=14400s`: the collector finished (tool wall 1,130 s, 60,000 kernels) and the offline `sync_dominance` analysis passed its 14,400 s cap; X1b has this id as TIMEOUT in scalar-clock mode (84,600 s) |

No TIMEOUT row remains; the analysis timeout is the harness's X1b policy (`--analysis-timeout 14400`), not a verdict.

## Parity set (the "Is one run enough?" recordings)

65 ids (`eval/baselines/setup/t5b_parity_ids.txt`), three reps each, recorded twice (`final-2026-11-co-parity-a` on c41, c42, c43; `-b` on c40, c55, c62), `BASELINE_KEEP_REPS=1`: every rep's kernel JSONs are in `<id>/collector-only-rep<k>/` (hard links to the first rep's files in `<id>/collector-only/`). 64 ids have 3 rep directories in each recording (2,025 and 2,040 kernel JSONs); 1 id has none in either, because all 3 reps hit the 1,200 s cap in both recordings (6 TIMEOUT rows of 390). The node of A differs from the node of B for 65 of 65 ids. Per-id multiset of rep verdicts, A against B: 0 of 65 differ (216 CLEAN, 168 RACE, 6 TIMEOUT rows over both). `setup/co_parity_check.py` is the check.

## Checks on the stores

- Kernel JSONs scanned for an `hb_` key: `final-2026-11-co` 80,423 files, `-long` 1,637, `-24h` 1,000, `-parity-a` 2,025, `-parity-b` 2,040: **0** with an `hb_` key.
- `modes` in `meta.json`: only `collector-only`; `hb_trace` is false in every one (4,709 + 5 + 1 + 65 + 65; the 16 `missing-exe` metas hold no mode).
- Peak RSS: `blib.run_timed(poll_mem=True)`, the X1b function (summed VmRSS poll), unchanged.

## Results (`eval/results/collector-only/merged/report_tables.md`, `setup/post_co.py`)

Program-level verdict = RACE if any rep RACE; no program has reps that disagree between RACE and CLEAN. Slowdown = median tool wall / native wall of the same job; native wall is the median over the program's 3 native runs on the same node.

| pset | programs | RACE | CLEAN | TIMEOUT | ERROR | geomean slowdown | median peak RSS (MB) | max peak RSS (MB) |
|---|---|---|---|---|---|---|---|---|
| P1 | 400 | 200 | 200 | 0 | 0 | 6.38 | 847 | 850 |
| PI | 4,130 | 2,642 | 1,488 | 0 | 0 | 5.03 | 835 | 947 |
| P3 | 60 | 16 | 44 | 0 | 0 | 5.95 | 847 | 850 |
| P4 | 28 | 20 | 8 | 0 | 0 | 6.62 | 848 | 875 |
| P5 | 33 | 2 | 31 | 0 | 0 | 5.55 | 847 | 849 |
| P6 | 50 | 7 | 27 | 0 | 16 | 6.67 (34 measured) | 847 | 4,960 |
| P7 | 14 | 5 | 9 | 0 | 0 | 93.52 | 1,077 | 4,240 |
| P9 | 10 | 4 | 5 | 0 | 1 | 94.19 (9 measured) | 954 | 1,428 |
| all | 4,725 | 2,896 | 1,812 | 0 | 17 | | | |

The 14 P7 and 10 P9 ids are the HeCBench programs; records = records drained (`accelprof -v`, per-drain lines; local-memory records included), from the row's `events=`:

| id | verdict | reports | tool wall (s) | native (s) | peak RSS (MB) | records drained | cap (s) |
|---|---|---|---|---|---|---|---|
| P7-backprop-cuda | CLEAN | 0 | 1.7 | 0.268 | 897 | 1,232,901 | 1200 |
| P7-bezier-surface-cuda | CLEAN | 0 | 45.4 | 24.463 | 3,934 | 106,955,008 | 1200 |
| P7-bitonic-sort-cuda | CLEAN | 0 | 635.3 | 31.94 | 1,379 | 1,226,469,735 | 1200 |
| P7-heartwall-cuda | RACE | 2 | 2,347.6 | 0.769 | 987 | 8,071,484,636 | 5400 |
| P7-haversine-cuda | CLEAN | 0 | 227.4 | 3.123 | 2,306 | 629,145,600 | 1200 |
| P7-nbody-cuda | CLEAN | 0 | 59.9 | 14.57 | 867 | 320,355,120 | 1200 |
| P7-mandelbrot-cuda | CLEAN | 0 | 162.4 | 3.825 | 876 | 327,687,360 | 1200 |
| P7-pathfinder-cuda | RACE | 1 | 702.4 | 1.47 | 2,023 | 7,058,581,010 | 1200 |
| P7-srad-cuda | RACE | 2 | 401.3 | 0.371 | 889 | 589,889,126 | 1200 |
| P7-lavaMD-cuda | CLEAN | 0 | 83.4 | 0.383 | 1,217 | 398,843,648 | 1200 |
| P7-stencil1d-cuda | CLEAN | 0 | 36,373.3 | 4.774 | 4,240 | 85,983,231,000 | 84600 |
| P7-particlefilter-cuda | RACE | 30 | 3,200.2 | 1.171 | 1,152 | 22,515,702,514 | 5400 |
| P7-hotspot-cuda | CLEAN | 0 | 21.5 | 0.518 | 871 | 37,410,000 | 1200 |
| P7-bfs-cuda | RACE | 31 | 4.8 | 1.069 | 1,002 | 7,436,165 | 1200 |
| P9-atomicCAS-cuda | ERROR (analysis-timeout) | | 1,130.4 | 3.824 | 892 | missing | 1200 |
| P9-dxtc2-cuda | RACE | 3 | 186.6 | 0.318 | 882 | 634,278,100 | 1200 |
| P9-knn-cuda | CLEAN | 0 | 3,739.8 | 13.092 | 1,015 | 11,144,912,500 | 5400 |
| P9-tridiagonal-cuda | RACE | 20 | 4,551.3 | 0.719 | 1,428 | 5,598,992,570 | 5400 |
| P9-expdist-cuda | RACE | 22 | 374.6 | 2.021 | 878 | 1,650,594,744 | 1200 |
| P9-overlap-cuda | CLEAN | 0 | 13.0 | 0.418 | 1,237 | 13,107,200 | 1200 |
| P9-fpc-cuda | CLEAN | 0 | 49.0 | 1.57 | 1,013 | 145,620,992 | 1200 |
| P9-gpp-cuda | CLEAN | 0 | 9.1 | 0.268 | 881 | 10,368,000 | 1200 |
| P9-crs-cuda | RACE | 7 | 5.1 | 1.521 | 954 | 9,864,919 | 1200 |
| P9-mr-cuda | CLEAN | 0 | 47.7 | 1.771 | 852 | 149,519,200 | 1200 |

## Comparison with X1-follow's collector-only numbers (`eval/x1_follow/table1.md`, `-n 1`)

µs per record = tool wall / records drained.

| program | this run: wall (s) / records / µs per record / node (CPU) | X1-follow: µs per record / host | difference |
|---|---|---|---|
| P7 heartwall-cuda | 2,347.6 / 8,071,484,636 / 0.2908 / c61 (8124P) | 0.2905 / c66 (8124P) | +0.1 % |
| P9 knn-cuda | 3,739.8 / 11,144,912,500 / 0.3356 / c76 (7302P) | 0.2965 / c61 (8124P) | +13.2 %; different CPU type |
| P1 BFS_CUDA_E_Topo_Determ_IntType_ReadModifyWrite..._100n | 1.1 / 1,023 / 1,045 / c62 (8124P) | 1,449 / c66 (8124P) | -27.9 %: above 20 %; 1.1 s of wall for 1,023 records is start-up, not a per-record cost (X1-follow says the same of this row) |
| P7 bfs-cuda | 4.8 / 7,436,165 / 0.649 / c63 (8124P) | missing | X1-follow has no collector-only run of P7-bfs |
| P7 nbody-cuda | 59.9 / 320,355,120 / 0.1868 / c74 (7302P) | missing | X1-follow has no collector-only run of nbody (its nbody numbers are scalar-clock) |

Findings above the 20 % bar: one (the P1 BFS row, a start-up-dominated 1.1 s run). heartwall agrees to 0.1 %; knn differs by 13.2 % on a different CPU type (X1-follow notes T20's up to 2x between host types).

## Deviations from X1b's harness and policy

- `-v` on the accelprof command of this mode (X1-follow's runs used it; it is the only record count the mode has). X1b's runs had no `-v`.
- `BASELINE_HB_DUMP`, `YOSEMITE_HB_STATS` and `BASELINE_HB_SHARDS` are not set (each belongs to HbClock or the sync pass); `meta.json` records `yosemite_env=[YOSEMITE_ATOMIC_SCOPE_FILE]` for every run.
- `BASELINE_KEEP_REPS=1` (new, aa15012) for the two parity recordings only.
- Native runs: 3 per program in the same job on the same node (`collect_one`, unchanged).
- The 5,400 s pass has every TIMEOUT id of the first pass in one task each; the 84,600 s pass has one rep (X1b's choice); P7-stencil1d-cuda reached a verdict there, so no TIMEOUT stands.
