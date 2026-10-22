# X1-follow — collector-only cost, the bfs bisect, where nbody's time goes, partial rows

Side task of X1 (`eval/FINAL_SWEEP.md`), 2026-10-15. Branch `eval/final-sweep` (worktree
`wt-x1`), unmerged. Results and harness scripts only: nothing under `sanalyzer/`, `nv-compute/` or
`python/hb_oracle.py` changed; every run uses existing knobs. The running X1 24 h tasks
(312332_8, 312333_2/5/6 on c60–c63) were not touched; every X1-follow run is its own `--exclusive`
job on another rtx4060ti16g host. Raw logs: `eval/x1_follow/` (per-run summary JSON, `*.log.gz` =
accelprof stderr + the `-v` log, perf reports). Facts only; a number that could not be obtained is
written **missing**.

**Summary** (each number's source is in its section):
- **Collector-only cost** (`YOSEMITE_HB_TRACE` unset, §1): **0.29 µs/event** (heartwall) and **0.30**
  (knn) with `-n 1`; **0.078** and **0.075** with the default worker count; every run finished, MaxRSS
  ~1 GB. X1's rows of the same programs: 3.97–5.13 µs/event.
- **bfs** (§2): scalar-clock crosses from seconds to minutes at **`d67ed41`, the T4 merge** — scalar-clock
  mode starts running HbClock's sync instance (the bucket scan) online; the vector-clock crossing is
  **`ebc464f`, the T9 merge** (per-location buckets). nbody's 25 µs/event appears at neither commit
  (6.8–7.2 µs/event at T4, 13.0 / 13.5 at T3b / T9); where it appears between T4 and T20 is not
  measured.
- **nbody** (§3): **yes, the time is in the reader list** — ≈ 90 % of CPU self time in operations on a
  location's slot array (80 % insertion: `merge_tail`'s merge and the slot sort key, 33.85 points of it
  by elimination), clock comparison < 0.3 %, allocation 0.5 %, other threads 0.22 %; broadcast-read
  regime (9,144 entries per location on average, 16,000 threads; the maximum is not recorded).
- **Partial rows** (§4): 183 shard rows annotated (178 TIMEOUT, 5 OOM), no verdict changed.

Commits on `eval/final-sweep` (unmerged): `6c9f7b0`, `ae382af`, `9a26839`, `01d5c65`, `dad0a65`, and the
one that adds this report's last sections.


## 0. Setup, and two facts from the code

**Runtime.** The installed one (X1's): `d38d057`, built from `ba99486` — libsanalyzer `2201fcb7`,
collector `ee78cb89`, fatbin `a2d7368b` (X0's `4094187` changes no file under `sanalyzer/`,
`nv-compute/` or `bin/`; `git diff --stat ba99486 4094187 -- sanalyzer nv-compute bin` is empty).
The bisect builds its own runtimes into a BeeGFS scratch prefix (§2), never installed.

**Hosts.** Every X1-follow run is pinned to c60–c72 (RTX 4060 Ti 16 GB, AMD EPYC 8124P, 188 GB) —
the host type of X1's knn and nbody rows. X1's heartwall rows ran on EPYC 9115 hosts (c58 VC, c52
SC), which are draining/down today (c50–c58); X1's 24 h bfs VC row ran on c51 (9115), its 5,400 s
SC row on c74 (EPYC 7302P). Cross-host walls on this partition differ by up to 2× (T20).

**Scripts** (`eval/baselines/setup/`): `x1f_run.py` (one timed run with the harness's own pieces —
`blib.base_env`, `blib.run_timed`, `blib.extract`, `collect_one`'s input layout and command —
under a chosen configuration and runtime), `x1f_collector.sh` (Part 1, long programs),
`x1f_bisect.sh` (Part 2), `x1f_nbody_perf.sh` (Part 3 and Part 1's short programs),
`x1f_extract.py` (read-only extraction from X1's stores → `eval/x1_follow/x1_meta.json`),
`x1f_partial_notes.py` (Part 4). Differences from `collect_one`, recorded in every summary JSON:
accelprof runs with `-v` (the app's stdout, which carries the analyzer's per-drain line
`[PC_DEPENDENCY] GPU data analysis called with size = N`, goes to a file instead of `/dev/null`, so
the run's own drained-record count is known); one tool run per configuration (X1: 3 reps, 1 for the
24 h pass); MaxRSS = the largest `VmHWM` of any process of the tree (polled every 0.2 s), next to
`getrusage(RUSAGE_CHILDREN).ru_maxrss` and the harness's summed-VmRSS peak.

**(a) `YOSEMITE_HB_NO_ENGINE=1` is not "PcDependency only".** It is the deprecated alias of
scalar-clock mode (`hb_scalar_clock_mode()`, `sanalyzer/src/tools/pc_dependency_analysis.cpp:2261–2287`:
the variable set ⇒ scalar-clock, with a deprecation warning), and since T4 scalar-clock mode runs
`HbClock`'s sync instance online (`hb_clock_reset`, `:2599`: `vector_pass = !hb_scalar_clock_mode()`;
the drain calls `hb_clock_process` in both modes, `:3473–3480`). So a `NO_ENGINE=1` run is X1's
scalar-clock configuration, whose rows are in the table below. The harness cannot pass it in any case
(`blib.base_env` drops it: `hb_modes.LEGACY_ENV`). The existing configuration without any `HbClock`
state is **`YOSEMITE_HB_TRACE` unset**: `hb_clock_reset` returns at once (`:2579`), the drain skips
`hb_collect_events` and `hb_clock_process` (`:3456`), and what remains is the collector plus the
PcDependency graph on `YOSEMITE_WORKER_COUNT` workers (`:2358`, default
`std::thread::hardware_concurrency()`). That is the "collector-only" configuration of §1.

**(b) Arrival and exit records are emitted with `YOSEMITE_HB_TRACE` unset.** The collector patches
`BlockExitCallback`, `BarrierCallback` and `SyncwarpCallback` for the pc_dependency tool
unconditionally (`nv-compute/src/compute_sanitizer.cpp:290–309`); only the cp.async commit/wait
callbacks (`PIPELINE_COMMIT`, `PIPELINE_WAIT`, T1a) are behind `YOSEMITE_HB_TRACE` (`:312–317`). On the
device the barrier/syncwarp records (`EmitSyncEvent`) and the exit record (`BlockExitCallback`) are
gated only on `enabled_instrumenting` (`nv-compute/gpu_src/gpu_patch_pc_dependency.cu:218–242`,
`:277–311`), the same in both paths. On the host the default path receives them in every drain:
an exit releases the CTA's shared shadow object, barrier and syncwarp records are skipped
(`pc_dependency_analysis.cpp:3398–3409`). So the collector-only floor of §1 includes the arrival
and exit records; the only HB records it lacks are cp.async commit/wait records (and, conversely,
it drains local-memory records, which the HB trace drops — I5).

## 1. Collector-only cost

**Configuration:** `YOSEMITE_HB_TRACE` unset (§0 (a)), the installed runtime, the harness's command
`accelprof -v -t pc_dependency_analysis [-n 1] ./<exe> <args>`, one run per worker setting, cap 24 h
(heartwall, knn) or 1,200 s (the short programs), 3 native runs (median shown). `-n 1` is X1's setting;
"default workers" omits `-n`, so the analyzer takes `std::thread::hardware_concurrency()` — the hosts
have 32 online CPUs (16 in the job's affinity mask, `nproc`), and a snapshot of the running heartwall
process showed 36 threads with the default against 6 with `-n 1` (`ps -o nlwp`, ~1.5 min into each run).
Jobs: heartwall `-n 1` 312732 (c66), default 312733 (c61); knn `-n 1` 312734 (c61), default 312735
(c66); the short programs in 312731 (c66), with a same-host run of X1's configuration (both modes,
`-n 1`, `YOSEMITE_HB_DUMP=0 YOSEMITE_HB_STATS=1`) beside them. Every run finished (rc 0, no kill).
Table: `eval/x1_follow/table1.md` (`setup/x1f_table1.py`); per-run JSON and logs:
`eval/x1_follow/collector/`.

**Columns.** X1 rows: wall = median of the rep walls (1 rep in the 24 h pass, 3 in the first pass);
memory = the harness's peak of summed VmRSS (X1 records no MaxRSS); events = the row's `events=`
(`hb_events_count`, local records excluded). X1-follow rows: memory = MaxRSS (largest VmHWM of the
process tree; `getrusage` agrees in every run); events = the records drained in that run, from the
analyzer's per-drain line — for heartwall, knn and the P6 program it equals X1's count exactly
(8,071,484,636; 11,144,912,500; 1,000,004), so the collector-only runs consumed the same record stream
(no local and no cp.async records in these programs). µs / event = tool wall / events; for the two
short programs the wall is dominated by the fixed start-up, so their µs / event is not a per-event cost.

| program / configuration | host (CPU) | tool wall (s) | native wall (s) | wall / native | memory (MB) | events | µs / event | kernels | |
|---|---|---|---|---|---|---|---|---|---|
| P7 heartwall-cuda — X1 vector-clock (1 rep, final-24h-vc) | c58 (9115) | 35,574.7 | 0.883 | 40,288× | 6,194 peak (summed VmRSS) | 8,071,484,636 (X1 `events=`) | 4.407 | 104 |  |
| P7 heartwall-cuda — X1 scalar-clock (1 rep, final-24h-sc) | c52 (9115) | 32,057.2 | 0.778 | 41,205× | 6,186 peak (summed VmRSS) | 8,071,484,636 (X1 `events=`) | 3.972 | 104 |  |
| P7 heartwall-cuda — collector-only, -n 1 | c66 (8124P) | 2,345.1 | 0.768 | 3,053× | 986 MaxRSS (VmHWM) | 8,071,484,636 (drained, this run) | 0.2905 | 104 |  |
| P7 heartwall-cuda — collector-only, default workers | c61 (8124P) | 626.4 | 0.818 | 766× | 1,009 MaxRSS (VmHWM) | 8,071,484,636 (drained, this run) | 0.07761 | 104 |  |
| P9 knn-cuda — X1 vector-clock (1 rep, final-24h-vc) | c62 (8124P) | 57,215.7 | 13.549 | 4,223× | 22,198 peak (summed VmRSS) | 11,144,912,500 (X1 `events=`) | 5.134 | 300 |  |
| P9 knn-cuda — X1 scalar-clock (1 rep, final-24h-sc) | c66 (8124P) | 44,762.4 | 13.744 | 3,257× | 20,558 peak (summed VmRSS) | 11,144,912,500 (X1 `events=`) | 4.016 | 300 |  |
| P9 knn-cuda — collector-only, -n 1 | c61 (8124P) | 3,304.1 | 13.542 | 244× | 1,009 MaxRSS (VmHWM) | 11,144,912,500 (drained, this run) | 0.2965 | 300 |  |
| P9 knn-cuda — collector-only, default workers | c66 (8124P) | 835.0 | 13.692 | 61× | 1,048 MaxRSS (VmHWM) | 11,144,912,500 (drained, this run) | 0.07492 | 300 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — X1 vector-clock (3 reps, final) | c51 (9115) | 0.868 | 0.217 | 4× | 851 peak (summed VmRSS) | 1,019 (X1 `events=`) | 851.8 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — X1 scalar-clock (3 reps, final) | c51 (9115) | 0.868 | 0.217 | 4× | 848 peak (summed VmRSS) | 1,019 (X1 `events=`) | 851.8 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — collector-only, -n 1 | c66 (8124P) | 1.477 | 0.267 | 6× | 848 MaxRSS (VmHWM) | 1,019 (drained, this run) | 1449 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — collector-only, default workers | c66 (8124P) | 1.060 | 0.217 | 5× | 850 MaxRSS (VmHWM) | 1,023 (drained, this run) | 1036 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — X1 configuration, scalar-clock, same host | c66 (8124P) | 1.094 | 0.217 | 5× | 849 MaxRSS (VmHWM) | 1,005 (drained, this run) | 1089 | 13 |  |
| P1 BFS_CUDA_E_Topo_Determ_IntT — X1 configuration, vector-clock, same host | c66 (8124P) | 1.197 | 0.216 | 6× | 852 MaxRSS (VmHWM) | 1,019 (drained, this run) | 1175 | 13 |  |
| P6 interkernel-global_readwrit — X1 vector-clock (3 reps, final) | c60 (8124P) | 5.578 | 0.719 | 8× | 856 peak (summed VmRSS) | 1,000,004 (X1 `events=`) | 5.578 | 2 |  |
| P6 interkernel-global_readwrit — X1 scalar-clock (3 reps, final) | c60 (8124P) | 4.926 | 0.719 | 7× | 855 peak (summed VmRSS) | 1,000,004 (X1 `events=`) | 4.926 | 2 |  |
| P6 interkernel-global_readwrit — collector-only, -n 1 | c66 (8124P) | 3.871 | 0.768 | 5× | 856 MaxRSS (VmHWM) | 1,000,004 (drained, this run) | 3.871 | 2 |  |
| P6 interkernel-global_readwrit — collector-only, default workers | c66 (8124P) | 3.553 | 0.718 | 5× | 861 MaxRSS (VmHWM) | 1,000,004 (drained, this run) | 3.553 | 2 |  |
| P6 interkernel-global_readwrit — X1 configuration, scalar-clock, same host | c66 (8124P) | 4.907 | 0.717 | 7× | 857 MaxRSS (VmHWM) | 1,000,004 (drained, this run) | 4.907 | 2 |  |
| P6 interkernel-global_readwrit — X1 configuration, vector-clock, same host | c66 (8124P) | 5.256 | 0.768 | 7× | 858 MaxRSS (VmHWM) | 1,000,004 (drained, this run) | 5.256 | 2 |  |

**What the table shows** (facts, no extrapolation):
- heartwall: collector-only 0.29 µs/event with `-n 1` (2,345 s) and 0.078 with the default workers
  (626 s), against X1's 4.41 (vector-clock) and 3.97 (scalar-clock). X1's heartwall rows ran on EPYC
  9115 hosts, these on EPYC 8124P hosts (the 9115 hosts c50–c58 are draining/down today), so this pair
  is cross-host.
- knn (all rows on EPYC 8124P hosts): collector-only 0.30 µs/event with `-n 1` (3,304 s) and 0.075 with
  the default workers (835 s), against X1's 5.13 (vector-clock) and 4.02 (scalar-clock).
- MaxRSS of every collector-only run is 0.99–1.05 GB; X1's rows of the same programs peaked at 6.2 GB
  (heartwall) and 20.6–22.2 GB (knn).
- Short programs: the flat-band P1 program takes 1.06–1.48 s under the collector alone and 1.09–1.20 s
  in X1's configuration on the same host (one run each); the P6 program (10⁶ events) takes 3.55–3.87 s
  collector-only and 4.91 / 5.26 s in X1's scalar-/vector-clock configuration on the same host.
- No collector-only run was killed; nothing to report on where a run stopped.


## 2. The bfs bisect

**Candidates** (`git log --first-parent cuVein`, b7d463e..ba99486): every first-parent commit that
changes `sanalyzer/`, `nv-compute/` or `bin/` — 20 merges, from the head-to-head eval merge of 09-22
(`b7d463e`, the Sept-22 runtime) to the T16 + T20 merge (`ba99486`). This list contains the T5b
(`b3bfdf3`), T18 (`0a25f7d`), T4 (`d67ed41`), T19 (`3c7eefd`), T16 (`d3f1e98`) and T20 (`ba99486`) merges
the brief names, and the T3b/T9/T10/T14/T12/T15/T17 merges between them. The install commits (`96698c1`
for `b6c9055`, `59b239a` for `d67ed41`, `bc9e4b0`/`d38d057` for `ba99486`) change no file under those three
directories (`git diff --stat` empty), so the merge's build is the install's code; installs recorded only
in CLAUDE.md (75f46012 at `6c34736` = `870dbb6`'s tree, e527875d at `7849a70`) are covered by those
merges. X0 (`4094187`) changes none of the three directories either.

**Method** (`setup/x1f_bisect.sh`, job 312742, c66 — EPYC 8124P, driver 595.58.03 — 2026-10-15 21:53 to
10-16 02:29, every run on that one host): per candidate, `git archive <c> sanalyzer nv-compute bin python`
into `/mnt/beegfs/$USER/x1_follow/bisect/<c>/`, both components built there with
`install_merged.sh`'s recipe (GCC 12.4, CUDA 13.3, `-g -mtune=znver4`; 13–22 s per candidate), a private
runtime prefix (the candidate's `bin/accelprof`, its collector linked with RPATH to its own
`libsanalyzer.so` — checked with `ldd` before every run — its `gpu_patch_pc_dependency.fatbin`, the
installed runtime's other fatbins by symlink); the installed runtime was never touched. Then
`x1f_run.py`: P7-bfs-cuda (`../data/bfs/graph1MW_6.txt`), 3 native runs, one tool run per mode at a
600 s cap, `-n 1`, the candidate's own `atomic_scope_sidecar.py` over the same CFG dots. Mode knob:
`YOSEMITE_HB_NO_ENGINE=1` on `b7d463e` (no `YOSEMITE_HB_MODE` there), `YOSEMITE_HB_MODE` from T8 on;
`YOSEMITE_HB_DUMP=0` from T4 on (before T4 the switch does not exist and every HB run dumps
`hb_events`); `YOSEMITE_HB_STATS=1` everywhere (X1's configuration; absent before T5a). The
scratch builds reproduce the installed device patches byte for byte where a backup exists (`b7d463e`'s
fatbin = `ef6c993d`, the backup `gpu_patch_pc_dependency.fatbin.pre-t1a-ef6c993d`; from T1a on
`a2d7368b` = the installed one, except `de565c0`/`b6c9055` = `e9634312`, the T15 fatbin installed at T17); the host libraries are
not byte-identical to the backed-up installs (different build environment). Kernel times = deltas of
the kernel JSONs' mtimes (1 s resolution); "kernels" = kernel JSONs on disk at the end (in a capped
run the last one may be a write cut by the kill). The Sept-22 rows of the superseded CSV on the same
CPU type (c69, EPYC 8124P) were 15.6 s scalar-clock / 71.4 s vector-clock (medians of 3 reps; the c0 rows
12.1 / 54.9 s) with 24 kernels; the `b7d463e` build gives 18.6 / 75.3 s here (one run each).

Where X1's bfs time is (X1's own kernel JSONs, `x1_meta.json`): 24 kernels, `Kernel` and `Kernel2`
alternating; launches 13, 15 and 17 are `Kernel2` and hold 72 + 841 + 566 s of the 1,507 s scalar-clock
5,400 s row (c74) and 304 + 3,558 + 2,389 s of the 6,290 s vector-clock 24 h row (c51), with 215,886,
218,756 and 218,751 events. `Kernel2` (`HeCBench/src/bfs-cuda/bfs.cu:48–62`, `eval/x1_follow/src_excerpts.txt`)
runs, for every frontier thread, `d_graph_mask[tid]=1; d_graph_visited[tid]=1; *d_over=1;
d_updatind_graph_mask[tid]=0;` — line 59 is one byte written by every thread of the frontier.

**The full sequence** (`eval/x1_follow/table2.md`, `setup/x1f_table2.py`; JSON and logs
`eval/x1_follow/bisect/`):

| # | commit | date | merge | scalar-clock mode at this commit | knobs | bfs SC wall (s) | SC kernels | SC Kernel2 #13 / #15 (s) | bfs VC wall (s) | VC kernels | VC Kernel2 #13 / #15 (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | `d38d057 (= ba99486 build)` | 2026-10-13 | installed runtime (X1) | sync instance online | MODE, DUMP=0, STATS | **600.1 (cap)** | 15/24 | 69 / not reached | **600.0 (cap)** | 15/24 | 483 / not reached |
| 1 | `b7d463e` | 2026-09-22 | Sept-22 runtime (eval merge) | records dumped only (no HbClock) | NO_ENGINE, dump | 18.6 | 24/24 | 0 / 0 | 75.3 | 24/24 | 2 / 4 |
| 2 | `1a45653` | 2026-09-23 | T8 | records dumped only (no HbClock) | MODE, dump | 18.6 | 24/24 | 0 / 0 | 75.1 | 24/24 | 3 / 4 |
| 3 | `6d843e3` | 2026-09-23 | T5a | records dumped only (no HbClock) | MODE, dump, STATS | 18.6 | 24/24 | 0 / 1 | 80.7 | 24/24 | 2 / 4 |
| 4 | `07d2798` | 2026-09-23 | T2 | records dumped only (no HbClock) | MODE, dump, STATS | 18.6 | 24/24 | 0 / 0 | 81.6 | 24/24 | 3 / 5 |
| 5 | `bc32a1f` | 2026-09-23 | T1a | records dumped only (no HbClock) | MODE, dump, STATS | 18.9 | 24/24 | 1 / 1 | 80.3 | 24/24 | 3 / 5 |
| 6 | `3331d35` | 2026-09-23 | T1a review | records dumped only (no HbClock) | MODE, dump, STATS | 18.3 | 24/24 | 0 / 1 | 80.8 | 24/24 | 3 / 5 |
| 7 | `0b64d34` | 2026-09-28 | T3b | records dumped only (no HbClock) | MODE, dump, STATS | 19.1 | 24/24 | 0 / 1 | 83.3 | 24/24 | 3 / 4 |
| 8 | `ebc464f` | 2026-09-28 | T9 | records dumped only (no HbClock) | MODE, dump, STATS | 19.2 | 24/24 | 0 / 0 | **600.1 (cap)** | 15/24 | 316 / not reached |
| 9 | `870dbb6` | 2026-09-28 | T3b×T9 fix | records dumped only (no HbClock) | MODE, dump, STATS | 19.0 | 24/24 | 1 / 1 | **600.1 (cap)** | 15/24 | 323 / not reached |
| 10 | `33a985c` | 2026-09-29 | T14 | records dumped only (no HbClock) | MODE, dump, STATS | 19.0 | 24/24 | 1 / 1 | **600.0 (cap)** | 13/24 | not reached / not reached |
| 11 | `be82754` | 2026-09-29 | T10 | records dumped only (no HbClock) | MODE, dump, STATS | 19.2 | 24/24 | 1 / 1 | **600.0 (cap)** | 13/24 | not reached / not reached |
| 12 | `b3bfdf3` | 2026-09-30 | T5b | records dumped only (no HbClock) | MODE, dump, STATS | 19.5 | 24/24 | 1 / 1 | **600.1 (cap)** | 13/24 | not reached / not reached |
| 13 | `7849a70` | 2026-09-30 | T12 | records dumped only (no HbClock) | MODE, dump, STATS | 19.1 | 24/24 | 0 / 1 | **600.0 (cap)** | 15/24 | 457 / not reached |
| 14 | `de565c0` | 2026-09-30 | T15 | records dumped only (no HbClock) | MODE, dump, STATS | 19.4 | 24/24 | 1 / 1 | **600.1 (cap)** | 15/24 | 447 / not reached |
| 15 | `b6c9055` | 2026-10-01 | T17 | records dumped only (no HbClock) | MODE, dump, STATS | 19.3 | 24/24 | 0 / 1 | **600.0 (cap)** | 15/24 | 440 / not reached |
| 16 | `0a25f7d` | 2026-10-05 | T18 | records dumped only (no HbClock) | MODE, dump, STATS | 19.3 | 24/24 | 1 / 0 | **600.0 (cap)** | 15/24 | 444 / not reached |
| 17 | `d67ed41` | 2026-10-05 | T4 | sync instance online (T4) | MODE, DUMP=0, STATS | **600.1 (cap)** | 15/24 | 209 / not reached | **600.1 (cap)** | 15/24 | 428 / not reached |
| 18 | `3c7eefd` | 2026-10-10 | T19 | sync instance online (T4) | MODE, DUMP=0, STATS | **600.1 (cap)** | 15/24 | 82 / not reached | **600.0 (cap)** | 15/24 | 495 / not reached |
| 19 | `d3f1e98` | 2026-10-11 | T16 | sync instance online (T4) | MODE, DUMP=0, STATS | **600.1 (cap)** | 15/24 | 83 / not reached | **600.1 (cap)** | 15/24 | 492 / not reached |
| 20 | `ba99486` | 2026-10-12 | T20 | sync instance online (T4) | MODE, DUMP=0, STATS | **600.0 (cap)** | 15/24 | 67 / not reached | **600.0 (cap)** | 15/24 | 487 / not reached |
| — | `installed`, YOSEMITE_HB_STATS unset | | control | sync instance online | MODE, DUMP=0 | **600.0 (cap)** | 15/24 | 67 / not reached | | | |

| nbody run | wall (s) | kernels finished | per-kernel time of the finished kernels (s) | µs / event of finished `accelerate_particles` launches |
|---|---|---|---|---|
| nbody-sc-0a25f7d | 600.1 (cap) | 6 + #6 truncated at the kill (19,609,470 records) | #0: 219, #1: 0, #2: 0, #3: 209, #4: 1, #5: 0 | #0: 6.84, #3: 6.53 |
| nbody-sc-d67ed41 | 600.1 (cap) | 6 | #0: 230, #1: 43, #2: 0, #3: 216, #4: 43, #5: 0 | #0: 7.19, #3: 6.75 |
| nbody-vc-0b64d34 | 600.0 (cap) | 3 | #0: 416, #1: 45, #2: 0 | #0: 13.00 |
| nbody-vc-ebc464f | 600.1 (cap) | 3 | #0: 431, #1: 43, #2: 0 | #0: 13.47 |

**Scalar-clock crossing (the brief's criterion): `d67ed41`, the T4 merge (feat/no-dump, 2026-10-05).**
bfs scalar-clock is 18.3–19.5 s on all 16 builds from `b7d463e` to `0a25f7d` (T18) and hits the 600 s cap
with 15 of 24 kernels on `d67ed41` and on every later build; `Kernel2` #13 takes 0–1 s before and 209 s
at `d67ed41` (82, 83, 67 s on T19, T16, T20; 67–69 s on the installed runtime, 72 s in X1). Not
monotone in that per-kernel time (T19 recovers part of it), monotone in the wall at this cap. **What
the commit changed on the per-event path (from the diff `0a25f7d..d67ed41` of
`pc_dependency_analysis.cpp`):** before T4 the drain called `HbClock` only outside scalar-clock mode —
`if (!hb_scalar_clock_mode()) hb_clock_process(accesses_buffer, size, order);` in
`PcDependency::gpu_data_analysis` — so a scalar-clock run recorded and dumped `hb_events` and nothing
else (the barrier-only pass ran afterwards in Python, outside the tool's wall). T4 calls
`hb_clock_process` unconditionally and sets `vector_pass = !hb_scalar_clock_mode()` in
`hb_clock_reset`, so scalar-clock mode now runs `HbClock`'s sync instance (`Detect(T, sync)`) on every
drained record during the run: each access goes through `check()` (`d67ed41:1316`), which visits every
other thread's entry in every conflicting key group of the location's buckets and, per entry, compares
the entry's scalar epoch with the accessor's sync clock (`p.sclock > vs_get(obs, p_tid)`, `:981`; the
vector test at `:970` is skipped with `vector_pass` false), then writes the accessor's own entry
(`g.by_tid[t] = Entry{…}`, `:1325`). The scalar-clock tool wall therefore includes, from T4 on, the
per-location bucket scan that vector-clock mode has run since T9.

**Vector-clock crossing (recorded beside it): `ebc464f`, the T9 merge (fix/publish-then-tick,
2026-09-28).** bfs vector-clock is 75–83 s with 24 kernels on the 7 builds `b7d463e`…`0b64d34` and hits
the cap from `ebc464f` on (15 kernels; 13 on T14, T10, T5b; 15 again from T12); `Kernel2` #13 takes 2–3 s
before and 316 s at `ebc464f` (323–495 s later; not reached within 600 s on T14, T10, T5b) — not monotone
in kernels finished (T12 partly recovers from T14–T5b). **What T9 changed on the per-event path (diff
`0b64d34..ebc464f`):** `HbEngine` kept per location one `last_write` (`std::map<Loc, Writer>`) and a
reader map (`std::map<Loc, std::unordered_map<Tid, Reader>>`) that every write cleared, so a write was
checked against one last writer and the reads since it. T9 (I2, buckets) replaced both by
`std::map<Loc, std::vector<KeyGroup>>`, one `std::unordered_map<Tid, Entry>` per (kind, scope) key,
holding one entry per thread that is replaced by the same thread and never cleared; the new `check()`
walks every other thread's entry of every conflicting key group and calls `conflict()` per entry —
the FastTrack-style epoch test `p.clock > clk_get(vc[obs], p_tid)` (one entry of the accessor's
sparse clock) plus `p.sclock > vs_get(obs, p_tid)`, and on a report a `race_index` lookup and count.
A write to a location that many threads write (`*d_over`) is thereby checked against every earlier
writer's entry instead of one.

**nbody on the crossing builds** (same host, same 600 s cap; per-kernel times as above):

- scalar-clock, `0a25f7d` (before T4, dump only) vs `d67ed41` (T4): `accelerate_particles` launches 0 and
  3 take 219 / 209 s and 230 / 216 s — **6.84 / 6.53 and 7.19 / 6.75 µs/event**;
- vector-clock, `0b64d34` (before T9) vs `ebc464f` (T9): launch 0 takes 416 s and 431 s — **13.00 and
  13.47 µs/event** (both builds also dump `hb_events`, 44 GB of JSON per launch).
- X1's 25 µs/event (795–802 s per launch, scalar-clock, c66 — the same host — on the installed
  `ba99486` runtime) therefore **does not appear at either crossing commit**; at T4 nbody is at
  6.8–7.2 µs/event. Which commit between `d67ed41` and `ba99486` brings it to 25 µs/event: **missing**
  (not run; the three builds `3c7eefd`, `d3f1e98`, `ba99486` are kept under
  `/mnt/beegfs/fzheng4/x1_follow/bisect/`).


## 3. Where nbody's time goes (scalar-clock, installed runtime)

**Method** — T20's (`eval/THREAD_INDEX.md` §4; `setup/t20_profile.sh` → `setup/t5b_profile.py`):
`timeout 1500 perf record -F 49 --call-graph dwarf,16384 -- accelprof -v -t pc_dependency_analysis -n 1
./nbody-cuda 16000 10` with `YOSEMITE_HB_DUMP=0 YOSEMITE_HB_STATS=1`, then T20's reports (self time,
`--no-children -g none`, by symbol, by symbol + source line, by thread; `setup/t20_perf_flat.sh`,
`t20_perf_alloc.sh`), plus the same reports without the 0.3 % listing limit and with `--inline` call
chains. Job 312731 (perf run, 2026-10-15 20:33, c66: EPYC 8124P, driver 595.58.03 — the host of X1's
nbody scalar-clock 24 h row) and jobs 313000, 313013 (reports, `normal`). perf 4.18.0-553.147.1.
Files: `eval/x1_follow/perf/nbody-sc.*` (`profile.txt` = t5b_profile's output, `sym*.txt`, `lines*.txt`,
`tid*.txt`, `alloc*.txt`, `profile-kernels.json`), `nbody_hb_stats.json`.
**Window:** the first 1,500 s of the run — kernel 0 (`accelerate_particles`, its JSON written ~13 min in),
kernels 1–2, and the remainder inside kernel 3 (`rc=124` at the cap); 73,565 samples; perf reported
2 lost chunks.

**Which kernel holds the time** (X1's own 24 h rows, from the kernel JSONs' write times and
`hb_events_count`; `eval/x1_follow/x1_meta.json`): nbody launches 30 kernels, 10 rounds of
`accelerate_particles` → `update_particles` → `accumulate_energy`. Each `accelerate_particles` launch has
32,005,004 events (1,024,144,000 lane accesses: full warps) and took 795–802 s in scalar-clock mode
(c66) and 814–819 s in vector-clock mode (c62) — 24.8–25.1 and 25.4–25.6 µs/event; the other two
kernels have 10,504 and 20,004 events and took ≤ 1 s each (the stores' mtimes have 1 s resolution).
nbody's 25 µs/event is therefore `accelerate_particles`'s, in both modes.

**Top ten functions, CPU self time, share of all samples** (`nbody-sc.sym-all.txt`):

| # | function | self % |
|---|---|---|
| 1 | `yosemite::HbClock::process` (with everything inlined into it) | 95.14 |
| 2 | `HbClock::ThreadArray<SyncClock>::at` (the per-thread sync clock lookup) | 1.40 |
| 3 | `HbClock::rmw_note` (R3 trace points) | 0.91 |
| 4 | `std::__insertion_sort<Slot*, merge_tail's comparator>` (sorting a location's 8-slot tail) | 0.61 |
| 5 | `__memmove_avx512_unaligned_erms` (libc) | 0.43 |
| 6 | `HbClock::FlatBuckets::seg_find` (the location index) | 0.35 |
| 7 | `std::_Hashtable<unsigned long, pair<const unsigned long, unsigned int>>` | 0.17 |
| 8 | `std::_Hashtable<unsigned int, pair<const unsigned int, int>>` | 0.12 |
| 9 | `phmap::raw_hash_map<…, PC_statisitics>` (the PcDependency graph) | 0.09 |
| 10 | `PcDependency::unit_access` (the PcDependency graph) | 0.08 |

**Inside `HbClock::process`, by source line** (`nbody-sc.lines.txt`: every (symbol, line) of `process` ≥ 0.3 %; `lines-inline.txt` for the inline chains):

| line | code | self % |
|---|---|---|
| `pc_dependency_analysis.cpp:561` | `merge_tail`: `if (i >= 0 && slot_order(p[i]) > slot_order(tmp[j])) p[k--] = p[i--];` — the backward merge that inserts a location's 8-slot tail into its sorted slot array | 44.46 |
| `:359` | `slot_order(s)` = `(key << 32) \| tid`, the array's sort key — 4.13 named by perf as `own_slot`'s binary-search comparator; the other 33.85 under unnamed inline frames | 37.98 in `process` (38.29 over all symbols) |
| `stl_algo.h:2030` | `std::__upper_bound` — `check()`'s skip over a location's key runs (`:1485`) | 1.72 |
| `:363` | `cap_of`: `while (c < n) c += c / 2;` — the slot array's capacity rule, evaluated on every `append` | 1.39 |
| `stl_algobase.h:1460/1465/1468/1472` | `std::__lower_bound` — `own_slot`'s binary search (`:529`) | 2.22 |
| `stl_iterator_base_funcs.h:105/194` | `__distance` / `__advance` inside the two binary searches | 1.44 |
| `:1502` | `epoch32`'s range check when a slot is written | 0.60 |
| `:533` | `own_slot`'s scan of the unsorted tail | 0.48 |

`slot_order` is called at four places (`:530`, `:531` — `own_slot`; `:558` — `merge_tail`'s tail sort, which is
the separate symbol #4; `:561` — `merge_tail`'s merge). perf names the `own_slot` comparator (4.13 %); the
remaining 33.85 % is in `process`'s own code under unnamed inline frames, which leaves `:531` (one
compare per access) and `:561` (two compares per prefix slot moved); the attribution of those 33.85 % to
`:561` is by this elimination, not by a named frame.

**The split asked for** (shares of all samples):
- **operations on a location's slot array (here: its reader entries): ≈ 90 %** — insertion
  (`merge_tail`'s merge `:561` 44.46 + the 33.85 of `:359` outside `own_slot` + the tail sort 0.61 +
  `cap_of` 1.39 = **80.3**), lookup (`own_slot`: binary search 2.22 + comparator 4.13 + tail scan 0.48 =
  **6.8**), scan (`check()`'s run skip 1.72), and 1.44 in `__distance`/`__advance` shared by the lookup and
  the scan; plus `seg_find` 0.35 finding the location.
- **clock comparison:** no line of the conflict test (`conflict()`, the scalar-epoch compare) reaches
  0.3 %; the per-thread clock lookup `ThreadArray<SyncClock>::at` is 1.40 (its page-bit line `:96` 0.47 of it).
- **allocation:** `__memmove_avx512_unaligned_erms` 0.43 (callers not resolved), `_int_malloc` 0.07; no
  other allocator symbol in the listing.
- **Sanitizer / CUDA threads:** 0.22 % of samples are outside thread 1927779 (0.20 % one other
  `nbody-cuda` thread, 0.01 % `cuda-EvtHandlr`); thread 1927779 runs the drain itself — its call chains
  are `main → GSimulation::Start → cudaLaunchKernel → … → LaunchEndCallback → gpu_data_analysis →
  HbClock::process` — so the Sanitizer callback and the analysis share that thread and are not separable
  by thread.
- R3 trace points (`rmw_note`) 0.91; the PcDependency graph (#9, #10) 0.17; `HbClock::stats` 0.05.

**HB_STATS of the main kernel** (`accelerate_particles`; identical in all 10 launches and in both
modes, X1's 24 h kernel JSONs and this profile's kernel 0): `buckets.locations` = **112,000**;
`buckets.entries` = **1,024,096,000**; `buckets.groups` = 160,000; `buckets.bytes` = 23,311,413,376
(23.3 GB; `rss_kb` at the kernel end 28.8–29.1 GB); `vs.threads` = 16,000; lane accesses
1,024,144,000. `entries` counts every slot (HB_STATS does not separate reader from writer slots);
entries per location = 1,024,096,000 / 112,000 = **9,143.7 on average**. **Max readers per location:
missing** — `HbClock::stats()` (`pc_dependency_analysis.cpp:1899–1990`) reports locations, segments,
groups, entries and bytes for the buckets, no per-location maximum.

**Broadcast-read regime: yes** — 1.02·10⁹ slots on 112,000 locations, 9,144 per location on average
with 16,000 threads, nearly one new slot per lane access (1,024,096,000 entries for 1,024,144,000 lane
accesses), i.e. readers per location in the thousands (the maximum itself is not recorded).


## 4. Partial rows

**Rule** (this brief): a run killed by OOM or by the time limit keeps every verdict it produced; its row's
notes start with `partial: <OOM|TIMEOUT> after <N> of <M> kernels, <wall> s, cap=<s>`. Applied with
`setup/x1f_partial_notes.py --apply` (2026-10-16 17:29, after the last 24 h task ended) to every cuVein
shard CSV of X1 — `eval/results/{final, final-long, final-long-sc, final-24h-vc, final-24h-sc}/` — and
carried into `eval/results/baselines-cuvein.csv` (the file `make_tables.py` reads) by the merge of
`setup/p_final_post.sh`, which X1 never writes directly. Committed in `dad0a65`; the merge (run
2026-10-16 17:34–17:42, `eval/FINAL_SWEEP.md` §5) carries 12 of the 183 into the merged file — the rows
of the pass that decides each key: particlefilter (vector-clock 5,400 s ×3, scalar-clock 24 h),
stencil1d (24 h, both modes), atomicCAS (vector-clock 5,400 s ×3, scalar-clock 24 h), expdist (24 h, both).

**Which rows** (`eval/x1_follow/x1_meta.json`, re-extracted after the last 24 h task; one record per rep):
- **TIMEOUT** — the rep timed out (`timed_out`, rc 124, verdict TIMEOUT): **178 rows**.
- **OOM** — the rep did not complete, did not time out, and its accelprof stderr shows the app SIGKILLed
  (`… Killed  LD_PRELOAD=…`; the harness makes the traced app the OOM killer's first victim,
  `blib._prefer_oom_victim`), with peaks of 185.3–186.3 GB on 188 GB hosts: **5 rows** —
  particlefilter vector-clock at 5,400 s (3 reps, RACE), particlefilter scalar-clock at 24 h (RACE),
  atomicCAS vector-clock at 24 h (ERROR `incomplete-trace`; the 5,400 s TIMEOUT rows stand in the merge,
  Jeffery's 10-14 choice). No partial row of any other kind exists in X1 (every rep that did not
  complete is one of these two).
- `N` = the row's `nkernels` (kernel JSONs on disk at the end); `M` = the kernel count of a complete X1
  run of the same program (any store, any mode), **"?"** for the four programs no X1 run completed —
  P9-expdist, P7-stencil1d, P7-particlefilter, P9-atomicCAS.

**Nothing else changed:** sha256 over every field except `notes` of all 28,402 cuVein shard rows
`612fcc0eb8b809b9` before and after (verdicts alone `6ebde8fc82908294` before and after); a second run of
the script writes nothing (all 183 "already").

**The 183 rows touched** (66 (pass, program, mode) groups in 47 files; per-row list with file names:
`eval/x1_follow/partial_rows.csv`):

| pass | program | mode | verdict (unchanged) | kind | reps | note(s) written (one per rep) |
|---|---|---|---|---|---|---|
| first pass (1,200 s) | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of 1 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of 1 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of 1 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of 1 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-bfs-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 15 of 24 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-bfs-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 17 of 24 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-bitonic-sort-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 73 of 325 kernels, 1200 s, cap=1200<br>TIMEOUT after 74 of 325 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-bitonic-sort-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 79 of 325 kernels, 1200 s, cap=1200<br>TIMEOUT after 80 of 325 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-haversine-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 23 of 100 kernels, 1200 s, cap=1200<br>TIMEOUT after 24 of 100 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-haversine-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 24 of 100 kernels, 1200 s, cap=1200<br>TIMEOUT after 25 of 100 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-heartwall-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of 104 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-heartwall-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of 104 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-lavaMD-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of 1 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-lavaMD-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of 1 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-mandelbrot-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 299 of 1001 kernels, 1200 s, cap=1200<br>TIMEOUT after 313 of 1001 kernels, 1200 s, cap=1200<br>TIMEOUT after 325 of 1001 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-mandelbrot-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 333 of 1001 kernels, 1200 s, cap=1200<br>TIMEOUT after 350 of 1001 kernels, 1200 s, cap=1200<br>TIMEOUT after 356 of 1001 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-nbody-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of 30 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-nbody-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of 30 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-particlefilter-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of ? kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-particlefilter-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of ? kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-pathfinder-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 8 of 200 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-pathfinder-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 14 of 200 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-srad-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3165 of 6002 kernels, 1200 s, cap=1200<br>TIMEOUT after 3272 of 6002 kernels, 1200 s, cap=1200<br>TIMEOUT after 3371 of 6002 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-srad-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3842 of 6002 kernels, 1200 s, cap=1200<br>TIMEOUT after 3869 of 6002 kernels, 1200 s, cap=1200<br>TIMEOUT after 3871 of 6002 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-stencil1d-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 2 of ? kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P7-stencil1d-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of ? kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-atomicCAS-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of ? kernels, 1200 s, cap=1200<br>TIMEOUT after 1537 of ? kernels, 1200 s, cap=1200<br>TIMEOUT after 2221 of ? kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-atomicCAS-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 10210 of ? kernels, 1200 s, cap=1200<br>TIMEOUT after 10308 of ? kernels, 1200 s, cap=1200<br>TIMEOUT after 10436 of ? kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-dxtc2-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 33 of 100 kernels, 1200 s, cap=1200<br>TIMEOUT after 36 of 100 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-dxtc2-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 46 of 100 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-expdist-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of ? kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-expdist-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of ? kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-fpc-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 3 | TIMEOUT after 196 of 202 kernels, 1200 s, cap=1200<br>TIMEOUT after 198 of 202 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-knn-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of 300 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-knn-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 6 of 300 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-tridiagonal-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 8 of 1111 kernels, 1200 s, cap=1200 |
| first pass (1,200 s) | P9-tridiagonal-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 9 of 1111 kernels, 1200 s, cap=1200 |
| 5,400 s, vector-clock | P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of 1 kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of 1 kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P7-bfs-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 15 of 24 kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P7-heartwall-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 9 of 104 kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P7-nbody-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 18 of 30 kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P7-particlefilter-cuda | vector-clock | RACE | OOM | 1, 2, 3 | OOM after 3 of ? kernels, 5313 s, cap=5400<br>OOM after 3 of ? kernels, 5321 s, cap=5400<br>OOM after 3 of ? kernels, 5331 s, cap=5400 |
| 5,400 s, vector-clock | P7-pathfinder-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 37 of 200 kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P7-stencil1d-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 7 of ? kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P9-atomicCAS-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 10000 of ? kernels, 5400 s, cap=5400<br>TIMEOUT after 13636 of ? kernels, 5400 s, cap=5400<br>TIMEOUT after 13948 of ? kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P9-expdist-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of ? kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P9-knn-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 24 of 300 kernels, 5400 s, cap=5400 |
| 5,400 s, vector-clock | P9-tridiagonal-cuda | vector-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 26 of 1111 kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P7-haversine-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 63 of 100 kernels, 5400 s, cap=5400<br>TIMEOUT after 67 of 100 kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P7-heartwall-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 17 of 104 kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P7-nbody-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 18 of 30 kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P7-particlefilter-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 3 of ? kernels, 5401 s, cap=5400<br>TIMEOUT after 3 of ? kernels, 5402 s, cap=5400 |
| 5,400 s, scalar-clock | P7-pathfinder-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 53 of 200 kernels, 5400 s, cap=5400<br>TIMEOUT after 55 of 200 kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P7-stencil1d-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 8 of ? kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P9-atomicCAS-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 40000 of ? kernels, 5400 s, cap=5400<br>TIMEOUT after 40480 of ? kernels, 5400 s, cap=5400<br>TIMEOUT after 40666 of ? kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P9-expdist-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 0 of ? kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P9-knn-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 33 of 300 kernels, 5400 s, cap=5400 |
| 5,400 s, scalar-clock | P9-tridiagonal-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1, 2, 3 | TIMEOUT after 37 of 1111 kernels, 5400 s, cap=5400<br>TIMEOUT after 38 of 1111 kernels, 5400 s, cap=5400<br>TIMEOUT after 39 of 1111 kernels, 5400 s, cap=5400 |
| 24 h, vector-clock | P7-stencil1d-cuda | vector-clock | TIMEOUT | TIMEOUT | 1 | TIMEOUT after 120 of ? kernels, 86400 s, cap=86400 |
| 24 h, vector-clock | P9-atomicCAS-cuda | vector-clock | ERROR | OOM | 1 | OOM after 30000 of ? kernels, 17625 s, cap=86400 |
| 24 h, vector-clock | P9-expdist-cuda | vector-clock | TIMEOUT | TIMEOUT | 1 | TIMEOUT after 0 of ? kernels, 86400 s, cap=86400 |
| 24 h, scalar-clock | P7-particlefilter-cuda | scalar-clock | RACE | OOM | 1 | OOM after 3 of ? kernels, 5791 s, cap=86400 |
| 24 h, scalar-clock | P7-stencil1d-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1 | TIMEOUT after 147 of ? kernels, 86400 s, cap=86400 |
| 24 h, scalar-clock | P9-atomicCAS-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1 | TIMEOUT after 60000 of ? kernels, 86400 s, cap=86400 |
| 24 h, scalar-clock | P9-expdist-cuda | scalar-clock | TIMEOUT | TIMEOUT | 1 | TIMEOUT after 32 of ? kernels, 86400 s, cap=86400 |


## 5. What remains unverified

- **Single runs.** Every X1-follow measurement is one run per configuration (X1's rows are medians of
  3 reps, or one rep in the 24 h pass). Run-to-run spread of the X1-follow walls is not measured.
- **Cross-host comparisons.** heartwall's X1 rows ran on EPYC 9115 hosts (c58, c52) and its
  collector-only runs on EPYC 8124P hosts; T20 measured up to 2× between host types. knn, nbody and the
  bisect are same-type (8124P), the bisect and the nbody profile on one host (c66, driver 595.58.03,
  the one host with that driver).
- **The default worker count** is `std::thread::hardware_concurrency()` by the code; the analyzer does
  not print it. The thread counts (36 vs 6) are one `ps` snapshot each. Those snapshots were taken with
  `srun --overlap` steps inside jobs 312732/312733; a project memory written the same day by another
  session records that the end of such a step once cut a harness job's BeeGFS access. Both jobs
  completed and read their BeeGFS kernel JSONs afterwards (104 kernels each); no effect observed.
- **`-v`.** The X1-follow runs send the app's stdout to a file (X1: `/dev/null`); the effect on wall
  time is not measured (one ~0.65 MB log for heartwall).
- **MaxRSS of X1's rows** is not recorded (the harness keeps the summed-VmRSS peak); the memory column
  mixes the two measures and says which is which.
- **nbody profile.** It covers the first 1,500 s (kernels 0–2, part of 3), perf lost 2 chunks, and
  33.85 points of `slot_order` are attributed to `merge_tail` by elimination, not by a named frame.
  The Sanitizer callback runs on the same thread as the analysis, so their split is not measured.
  Max readers per location: not recorded by HB_STATS.
- **Where nbody reaches 25 µs/event** between `d67ed41` (6.8–7.2) and `ba99486` (25): not measured.
- **Bisect builds** reproduce the historical device patches byte for byte where a backup exists, but
  not the host libraries (different build environment; the historical installs used, at times, the
  conda compiler). The historical installs also mixed components from different commits (e.g. the
  T3b + T9 install replaced only `libsanalyzer`); every bisect runtime builds both components from one
  commit. The per-kernel times have the stores' 1 s mtime resolution; in a capped run the last kernel
  JSON may be a write cut by the kill (nbody `0a25f7d` #6, excluded).
- **Part 4.** "OOM" means SIGKILL ("Killed" in the accelprof stderr) with the peak at 185–186 GB of the
  node's 202 GB `MemTotal`; the kernel log (`dmesg`) of those nodes was not read. M is taken from a
  complete X1 run of the same program in any store and mode; for every program with a partial row all
  its complete runs have the same count (109 other programs — data-dependent graph codes of P1/P3/P4 —
  finish with different counts in different complete runs); "?" where no X1 run of the program completed. N counts kernel JSONs at
  the end of the run; the last one may be a truncated write.

