# X1-follow — collector-only cost, the bfs bisect, where nbody's time goes, partial rows

Side task of X1 (`eval/FINAL_SWEEP.md`), 2026-10-15. Branch `eval/final-sweep` (worktree
`wt-x1`), unmerged. Results and harness scripts only: nothing under `sanalyzer/`, `nv-compute/` or
`python/hb_oracle.py` changed; every run uses existing knobs. The running X1 24 h tasks
(312332_8, 312333_2/5/6 on c60–c63) were not touched; every X1-follow run is its own `--exclusive`
job on another rtx4060ti16g host. Raw logs: `eval/x1_follow/` (per-run summary JSON, `*.log.gz` =
accelprof stderr + the `-v` log, perf reports). Facts only; a number that could not be obtained is
written **missing**.

{{STATUS}}

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


{{S2}}

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


{{S4}}

## 5. What remains unverified

{{UNVERIFIED}}
