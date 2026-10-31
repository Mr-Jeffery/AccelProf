# X7 Part A: the verdict step, faster and parallel

Branch `perf/verdict-parallel` (worktree `~/wt-x7a`), from `cuVein` f551ca0 (base commit 40b5222 adds only the
collector-only harness mode). Left unmerged. Freeze exception used: `python/sync_dominance.py` (graph construction
only), `eval/baselines/run_cuvein.py` (`_analyze_reports`), `eval/baselines/parallel.py` (`analyze_one`,
`_analyze_capped`), new tests and job scripts. No rule, verdict, class, dedup key or output field changed.

## 1. Parity (A5)

**0 differences on 28,234 + 14,138 rows; 3 atomicCAS collector-only rows whose reference is an analysis-cap ERROR,
accepted by Jeffery on 2026-10-31.**

Every program of every X1b / C1 store was re-analysed with the new code at `--analysis-workers 16`
(`eval/baselines/setup/x7a_a5.sbatch`; shards and merged CSVs in `eval/results/verdict-timing/`), merged by the same
rules as X1b / C1 (`x7a_a5_compare.py`), and compared per (id, mode, rep) on verdict, reports_dedup, report_ids,
report_lines and the `classes=` note.

| set | reference | ref rows | new rows | ids | differences |
|---|---|---|---|---|---|
| final-b (final-2026-11, vector-clock + scalar-clock, plus -long, -long-sc, -24h-vc, -24h-sc) | X1b merged | 28,234 | 28,234 | 4,725 | 0 |
| collector-only (final-2026-11-co, plus -co-long, -co-24h) | C1 merged (`eval/collector-only`) | 14,141 | 14,141 | 4,725 | 6 field differences on 3 rows (below) |

Coverage per store (programs in the store against programs analysed): final-2026-11 4,725 / 4,725 (the 4,726th entry is
`STORE_INFO.json`); -long 9 / 9; -long-sc 2 / 2; -24h-sc 8 / 8; -24h-vc 11 analysed (12 directories, below);
-co 4,725 / 4,725; -co-long 5 / 5; -co-24h 1 / 1. The 24 h merge rule gave vc 11 keys with 10 kept (P9-atomicCAS vc is
an ERROR and stays dropped, as in X1b), sc 8 keys with 8 kept.

**Capped / partial reference rows, and how they were compared.**
- final-b: 13 reference TIMEOUT rows (11 vector-clock, 2 scalar-clock) and 16 ERROR rows (empty mode) have no analysed
  verdict; the new CSV carries the same verdict (it does not re-analyse them). They are matched by carry-over, not by
  analysis. The 3 reference partial-RACE rows (`partial(rc=...)`) were re-analysed and agree on all five fields.
- collector-only: the 16 empty-mode ERROR rows are carried over and equal.
- The 3 differing rows are P9-atomicCAS-cuda collector-only reps 1 to 3. Reference: verdict ERROR, note
  `analysis-timeout=14400s` (the offline analysis passed its cap, `eval/COLLECTOR_ONLY.md`), so the reference holds no
  verdict. New: CLEAN, reports_dedup 0, `classes=sc:4`, `analysis_s=6.547`, 60,003 kernel JSONs. The new code
  analysed the same recording at N=1 and N=16 to the same output sha256 (`x7a_mem`). Jeffery accepted these 3 rows as
  they stand. An uncapped run of the original code on the same recording was started as supplementary evidence
  (job 324004, `eval/results/verdict-timing/old-atomicCAS/`); see the follow-up commit if it landed.
- Excluded from A5: `final-2026-11-24h-vc/P7-haversine-cuda`. It is Part B's new 84,600 s vector-clock run
  (`p_final_24h.sh` writes into that store), not part of X1b's A5 set.

## 2. A2: where the time goes (original code, one worker)

`cProfile` of `run_cuvein._analyze_reports` on stored recordings (job 323746, `eval/baselines/setup/x7a_prof.sbatch`,
`x7_profile.py`; logs `eval/x_logs/x7a-prof-*-323746.log`). The code profiled is f551ca0's `python/`.
Cumulative seconds:

| program (mode) | wall | analyze | parse_dot | of which pydot `graph_from_dot_file` | `_label_lines` | HBGraph.__init__ | immediate_dominators | judge | ordered | chain |
|---|---|---|---|---|---|---|---|---|---|---|
| P9-atomicCAS (collector-only), stopped at 1 h: 7,523 of 60,003 kernels | 3600 | 3599.6 | 3589.8 | 3552.6 | 31.6 | 2.7 | 0.76 | 0.01 | 0.00 | 0.00 |
| P7-heartwall (scalar-clock), 104 kernels | 1029.5 | 1029.4 | 998.1 | 984.9 | 11.4 | 5.3 | 0.72 | 21.3 | 20.8 | 0.00 |
| P9-knn (scalar-clock), 300 kernels | 390.7 | 390.7 | 386.2 | 381.7 | 3.7 | 0.51 | 0.11 | 0.63 | 0.57 | 0.00 |
| P7-stencil1d (collector-only), 1000 kernels | 66.2 | 66.2 | 62.6 | 61.6 | 0.82 | 0.47 | 0.12 | 1.23 | 1.02 | 0.00 |
| Indigo PI-conditional_edge_neighbor-DAG_100n_100e (vector-clock) | 0.59 | 0.59 | 0.55 | 0.55 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

Top of every profile by cumulative time: `_analyze_reports` / `analyze` (the whole run), then `parse_dot`, then pydot's
`graph_from_dot_file`. Split, graph construction (parse_dot + HBGraph.__init__ + dominators) against judging (judge):
atomicCAS 3593 s against 0.01 s; heartwall 1004 s against 21 s; knn 387 s against 0.6 s; stencil1d 63 s against 1.2 s.
Graph construction is 98 to 99.9 % of the wall in every case (heartwall 97.5 %). Every kernel launch re-parses the same
`.dot` (atomicCAS: 0.48 s per kernel for 60,003 launches of one kernel).

## 3. A3: the static-graph cache (split by copying, not by class)

`sync_dominance.graph_cache()` is a context manager; `run_cuvein._analyze_reports` opens it once per program, and
outside it every call parses and builds as before (`CUVEIN_GRAPH_CACHE=0` or `cache=False` is the pre-X7 path).
Inside it three dictionaries are kept: `dot` (path -> `parse_dot` result or its AlignmentError), `select`
((path, kernel name) -> `select_kernel` result or its AlignmentError) and `static` ((path, mangled) -> a never-attached
prototype `HBGraph`).

`HBGraph` is **not** split into two classes; it is split **by copying**. `HBGraph.from_static(proto)` creates a fresh
object that references (by reference, no copy) the prototype's static fields and re-creates all per-trace fields.
- Static, shared, read-only after `__init__` (`HBGraph._STATIC`): `G`, `pc_opcode`, `pc_node`, `syncs`,
  `unknown_syncs`, `ins_succ`, `ins_pred_pcs`, `ins_preds`, `qualifying`, `dom`, `postdom`.
- Per trace, fresh for every kernel JSON (`_init_trace_state`, then `attach_trace`): `atom`, `coh`, `sync_edges`,
  `release_points`, `acquire_points`, and `_reach` (the `fenced()` memo, so it never outlives one trace).
- Only graph construction is cached. The trace, the pc alignment check and every verdict are computed per kernel JSON
  exactly as before. A cached AlignmentError is re-raised as a fresh copy (same type and message).

A4 (`parallel.py`, `run_cuvein.py`): with W > 1 the parent parses each `.dot` once, then forks a pool of W workers over
the kernel JSONs; results are merged in kernel-JSON order, so the output is independent of W. A pool-worker exception is
re-raised as itself and the first exception in kernel order wins (`python/test_verdict_parallel.py`: N=1 serial,
N=1 cached, N=8 cached give identical merged output). A1 adds `analysis_s`, `analysis_workers` and `analysis_kjsons` to the
notes.

## 4. Green set (job logs in `eval/x_logs/`)

All GPU-dependent cases skip on the no-GPU `normal` nodes (the `nvcc` stub); no test failed anywhere.

| job | code | A4 set | gate | test_no_dump | test_collector_only | test_verdict_parallel |
|---|---|---|---|---|---|---|
| 323935 | new, 1dcdfcb | 157 passed, 144 skipped | 55 passed, 3 skipped | 31 skipped | 5 skipped | 10 passed |
| 323939 | base, 40b5222 | 157 passed, 144 skipped | 55 passed, 3 skipped | 31 skipped | 5 skipped | (not in base) |
| 323938 | base, 40b5222 | 60 passed, 148 skipped (208 collected, not 301) | 55 passed, 3 skipped | 31 skipped | 5 skipped | - |

323938 is not a valid baseline. Its log shows `test_sync_dominance.py` getting "empty parameter set for (binary)" on
three parametrised tests (`_binaries()` lists the executables in `ScoR/microbenchmarks/bin`) and the corpus test
skipping "corpus not generated", so the ScoR microbenchmark cases (97 passes in 323939) were never collected. Same
worktree, same rev (40b5222), same node (c26) as 323939, which ran 99 seconds later and collected 301; `ScoR/.../bin`
(63 files) was last modified 2026-10-28 04:32, before both. So it is not a checkout difference; the cause of the empty
listing at collection time is not in the log. 323939 is the valid baseline and equals the new run.

## 5. Peak memory (`x7a_mem`, job 323755, rev 73eca8d, cache on, c35)

Sum of RSS and PSS over the analysis' process group, sampled every 0.25 s.

| program | N=1 RSS / PSS (MB) | N=16 RSS / PSS (MB) | N=16 processes | N=1 cache off RSS (MB) |
|---|---|---|---|---|
| P9-knn sc | 68.5 / 62.3 | 786.9 / 69.3 | 13 | 69.9 |
| P7-stencil1d co | 62.1 / 56.0 | 943.7 / 142.0 | 17 | 71.8 |
| P7-heartwall sc | 79.9 / 73.6 | 1255.4 / 744.2 | 17 | not run |
| P9-atomicCAS co | 76.4 / 70.2 | 1304.0 / 291.6 | 17 | not run |

Largest N=16 value: 1,304 MB RSS (summed over parent and 16 workers, which share pages copy-on-write; the PSS column
counts shared pages once). The run predates the pool-exception commit 9e85726; it was not repeated.

## 6. Verdict-step time, old against new (per suite)

Sample: 40 programs from the non-HeCBench suites (P1 8, P3 4, P4 8, P5 4, P6 4, PI 12, vector-clock, picked evenly over
the sorted new-code time, so each suite's maximum is included) plus every HeCBench (P7, P9) key that finished within
the cap, both modes (6 P7 and 8 P9 keys). `x7_old.py` (`select`, `run`) times `_analyze_reports` per (id, mode) in its
own process, 8 processes at a time on a whole node, N = 1. Seconds, median / max over the sample:

| suite | n | old (40b5222, N=1, no cache) | new N=1, cache off | new N=1, cache on | new N=16 (A5, all rows of the suite) |
|---|---|---|---|---|---|
| P1 | 8 | 5.73 / 10.04 | 8.10 / 14.58 | 0.96 / 1.52 | 0.89 / 2.27 |
| P3 | 4 | 4.52 / 13.04 | 6.02 / 18.32 | 0.85 / 1.72 | 0.87 / 1.74 |
| P4 | 8 | 24.75 / 142.81 | 35.52 / 194.98 | 3.70 / 53.69 | 2.80 / 61.60 |
| P5 | 4 | 0.31 / 0.40 | 0.41 / 0.47 | 0.42 / 0.46 | 0.45 / 0.57 |
| P6 | 4 | 0.29 / 0.31 | 0.36 / 0.39 | 0.39 / 0.42 | 0.42 / 0.83 |
| PI | 12 | 0.34 / 0.44 | 0.43 / 0.56 | 0.43 / 0.60 | 0.49 / 1.53 |
| HeCBench P7 | 6 | 5.27 / 66.94 | 7.17 / 90.69 | 1.32 / 7.33 | 1.25 / 6.58 |
| HeCBench P9 | 8 | 47.09 / 7058.59 | 9.82 / 113.62 | 2.76 / 12.86 | 2.43 / 6.84 |

The new N=16 column is the A5 re-analysis of every row of that suite (not only the sample), so it is a different
population from the first three columns. Caveats:
- Old ran on c76, the new passes on c35 (different hosts, same 8-wide load); the cache-off column is 1.3 to 1.4 times
  the old time, which this run cannot separate from the host difference. It was not investigated.
- New cache-off for P9-mr-cuda hit its 900 s limit (both modes) and has no value; old P9-mr took 6,916 s (scalar-clock)
  and 7,059 s (vector-clock), under the 7,200 s limit. The HeCBench P9 cache-off median/max above therefore exclude it.
- The sample's old and new-cache outputs have identical sha256 for all 54 (id, mode) keys, P9-mr included.
- A first new-code run (job 324025) lacked `CUVEIN_HOME` and imported the default checkout's `sync_dominance`
  (no `graph_cache`); it was discarded and redone (job 324040). Files with the discarded runs are kept as
  `new-*-wrongenv.csv` / `new-cache-failed.csv`.
- The old pass had `CUVEIN_HOME` unset as well, so its `sync_dominance` came from `/home/fzheng4/AccelProf`
  (f551ca0); `git diff f551ca0 40b5222 -- python/sync_dominance.py` is empty (40b5222 changes `hb_modes.py` and adds
  collector-only tests), so the old numbers are the original verdict code.

Slowest programs, one worker, same recording (seconds):

| program | old | new N=1 cached | new N=16 (A5) |
|---|---|---|---|
| P9-mr-cuda vector-clock (1600 kernels) | 7058.6 | 12.9 | 6.8 |
| P9-mr-cuda scalar-clock | 6916.0 | 8.6 | 6.2 |
| P4-rule-110-racy-large vc (64) | 142.8 | 6.4 | 3.0 |
| P9-crs-cuda vc / sc (50) | 81.1 / 80.5 | 2.8 / 2.7 | 2.5 / 2.4 |
| P7-hotspot-cuda sc / vc (100) | 66.9 / 65.2 | 1.3 / 1.3 | 1.2 / 1.3 |
| P4-matrix-multiplication-racy-large vc (1 kernel) | 46.3 | 53.7 | 61.6 |

A one-kernel program gains nothing (46 s old; no launch repeats a graph). From the A4 memory run (same recording,
cache toggled): knn sc 345.2 s (N=1, no cache) against 2.5 s (N=1 cached) and 1.68 s (N=16); stencil1d co 57.4 against
2.74 and 0.58; heartwall sc 1,030 s (profiled run) against 22.6 and 10.1; atomicCAS co no old value (more than the
14,400 s cap) against 31.3 and 6.9.

## 7. Re-analysing a stored recording at N = 16 (Part B)

```
cd /home/fzheng4/wt-x7a && BASELINE_TRACE_DIR=/mnt/beegfs/fzheng4/cuvein_traces/<store> BASELINE_MODES=<mode> \
  /home/fzheng4/AccelProf/.env/bin/python eval/baselines/parallel.py analyze --manifest eval/baselines/manifest.csv \
  [--pset P | --id ID | --id-file F] [--shard k/N] --tag <tag> --results-dir <dir> --analysis-timeout 14400 --analysis-workers 16
```
Run on a compute node (BeeGFS), with `ACCEL_PROF_HOME` and `CUVEIN_HOME` set to the worktree and all `CUVEIN_*` /
`YOSEMITE_*` variables unset. `<mode>` is `vector-clock`, `scalar-clock` or `collector-only`.
