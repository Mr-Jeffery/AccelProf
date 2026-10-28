# C1: collector-only mode (eval/collector-only from eval/final-tables d484e42)

Step 1 only so far (written 2026-10-28). Steps 2 and 3 (the sweep, the numbers) are not started.

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
