# T20: per-thread lookups

Branch `perf/thread-index`, from `cuVein` 3c7eefd (T19 merged; the installed runtime is its build:
libsanalyzer `a37ad29a`, collector `619b788b`). Design note: `design/thread_index.md`. Written
2026-10-11. Code: 3482e65 (step 0), e6beeb6 (dense arrays, pending trie, hoisting, off-path
teardown; "first build"), 31845b3 (barrier arrivals as lane masks; "final build").

Runtimes, each a private libsanalyzer built with GCC 12.4.0 (`-g -O3 -mtune=znver4`) and a collector
relinked from the d67ed41 install's objects with RPATH to it (`setup/t20_build.sh`):

| name | libsanalyzer | collector | what |
|---|---|---|---|
| d67 | `9ae97c27` | `2c0ef711` | the d67ed41 install (T4 + T18, node-based buckets): T4's bar, run on the same node (`setup/t20_rt_d67.sh`, the `pre-t19` backup library) |
| T19 | `a37ad29a` | `619b788b` | the installed runtime, 3c7eefd (flat buckets) |
| T20 first build | `f9d2996a` | `7ad4125b` | e6beeb6 |
| **T20 final** | **`391cf9cc`** | **`7ad4125b`** | **31845b3** |

All use the installed fatbins (default `a2d7368bc1c61986`, late `e96343121c74ca0a`); no collector or
device source changed (`git diff 3c7eefd -- nv-compute` is empty). Hardware: RTX 4060 Ti 16 GB nodes
of `rtx4060ti16g` (sm_89; driver 580.82.07 and, on c51, 580.95.05); CPU work on `normal` nodes.
Legend: **proved-in-effect** = an invariant checked over the stated traces; **tested** = a specific
result asserted by a test.

## 1. What changed

| | before (T19) | after (T20) |
|---|---|---|
| `vc`, `vs` (per-thread clocks) | `unordered_map<Tid, …>`, a hash lookup per lane, and per bucket slot visited in Check | `ThreadArray`: index `block · bt + (warp << 5 \| lane)` computed from the tid (`bt` = block size rounded to 32), 2¹⁴-thread pages allocated on first touch, a side map for async agents; Check looks the observer's two clocks up once |
| `rmw_thr` (T4's R3 trace points) | `unordered_map<Tid, RmwThread>` with a `std::vector` of pending pcs, deduplicated by a linear `std::find` per lane | a dense 16-byte state per thread; the pending set is a node of a shared trie (memoised transitions, `rel` insertions once per distinct (set, RMW pc)); `rmw_pts[pc]` once per record |
| instance gate's `last_pc`, open-window mask | a hash probe per lane | once per record |
| barrier assembly (`Pending::arrived`) | `std::set<Tid>`, one tree node per arriving thread | 32 lane masks + a count (31845b3) |
| previous kernel's state | freed in `reset()` on the launch path | moved into a bundle destroyed on a background thread (joined at the next reset and in `~HbClock`; in line below 2¹⁶ elements or with `YOSEMITE_HB_SYNC_RESET=1`) |
| `KernelLaunch::kernel_pc` | uninitialised (default path printed heap memory) | 0 |

`hb_oracle.py` is unchanged. No value changes: every container holds the same entries; outputs that
iterate a changed container are sorted (`hb_rmw_points`) or counts (`HB_STATS`); Check visits the
buckets in T19's order, so even an aggregate's representative instance is the same. `HB_STATS`
`vc`/`vs` `bytes_est` now count the dense pages, and `pending_barriers.bytes_est` drops the
per-arrival node term.

Memory at the largest grid (P7 pathfinder, 100 M threads, all touched): `vc` 88 B and `vs` 24 B per
thread dense against ~120 B and ~56 B per hash node (design note §2); the lavaMD and step-5 peak
RSS below are equal or lower on every program.

## 2. Parity (step 3)

Every check ran on both builds; the final build's numbers are the acceptance.

| check | first build `f9d2996a` | **final `391cf9cc`** |
|---|---|---|
| green set (CLAUDE.md A4 files + `test_instance_gate.py`) + `test_no_dump.py`, every trace re-recorded (`setup/t20_check.sh`) — tested | **332 passed, 2 skipped, 0 failed** (job 310862, c51) | **332 passed, 2 skipped, 0 failed** (job 310918) |
| default tool path (no `YOSEMITE_HB_TRACE`), `race_interblock_none-lock_rtraw` and `norace_interblock_atom`: installed T19 vs T20, up to device addresses and dist histograms, `kernel_pc` dropped | identical | identical |
| the same, two T20 runs, `kernel_pc` kept | identical, and **byte for byte** (`cmp`); `kernel_pc` = 0 | identical, and **byte for byte**; `kernel_pc` = 0 |
| implementation == specification, T5b's 65-program set recorded with the 120 s floor (`p_t5b_timeout.sh`, both modes) then `t5b_parity.py` — proved-in-effect | **61/61 programs that dumped, 459 kernels, 0 mismatches** (jobs 310843, 310851) | **61/61, 460 kernels, 0 mismatches** (jobs 310920 + 311129/311130, 311131) |
| no-dump aggregates == records, the same recordings, both modes (`t4_parity.py`, cap 25,000 s) — proved-in-effect | **916 kernel JSONs, 916 equal, 0 mismatches** (job 310852; 64 above the size cutoff, compared all the same) | **918 kernel JSONs, 918 equal, 0 mismatches** (job 311132; 64 above the cutoff) |
| verdicts against T19's recording of the same 65 programs × 2 modes (`wt-t19/eval/results/t19-parity-v4`; `setup/t20_verdicts.py`) | 130 rows: 3 verdicts differ, all TIMEOUT under T19 that now finish (below); 2 rows differ by one report (below) | 130 rows: **the same 3 verdicts differ, no report count differs** |

The 4 programs without a vector-clock dump at the 120 s floor are the same in both builds (e.g.
P7-bfs, P9-overlap). The three verdicts that differ from T19's recording:
- P1 CC_CUDA_V_Topo_Pull_Determ…slower_atomic-1296n, vector-clock: TIMEOUT → RACE (3 reports). The
  program is labelled racy (RaceBug).
- P9-crs-cuda, both modes: TIMEOUT → CLEAN (T3b's verdict, `eval/CRS_CUDA_TRIAGE.md` §11).

The first build's one-report differences are PI populate_worklist_neighbors_persistent_atomicBug
(scalar-clock 90 → 91, vector-clock 91 → 90). T19 recorded the same kind of ±1–2 on this program
between its own runs, a run-to-run schedule difference of contended atomics, and the final build's
recording matches T19's count exactly.

A re-score of kept dumps cannot move a verdict here (it runs the Python oracle and verdict layer,
which T20 does not touch); the re-recorded comparisons above are the tests that can.

**Incident (no effect on the results above).** The final build's first parity recording lost
shards 0 and 2 to node c54, which reports no CUDA device: my `-x c37` on the command line replaced
the script's `#SBATCH --exclude=c54,c2` instead of adding to it. 32 rows read ERROR with
`native_err=no CUDA-capable device`. Re-running only those shards as a two-task array changed
`SLURM_ARRAY_TASK_COUNT` and with it the shard split, so I re-recorded each as a plain job with
the shard fixed (`setup/t20_shard.sh`). The comparisons above read the repaired store; the stray
CSVs were deleted. The same store also holds 18 programs re-recorded by the wrong-split run, with
the same build; their CSV rows are from the first recording.

## 3. Time (step 4)

No-dump mode (`YOSEMITE_HB_DUMP=0`), `HB_STATS` at kernel end; each comparison on one node, one
runtime after the other. Nodes: c50 and c58 are EPYC 9115 (Zen 4), c60–c64 and c77 below as
labelled (EPYC 8124P / 7302P). Each row is one run per runtime unless it says reps.

### 3.1 lavaMD, full input (`-boxes1d 30`, one kernel of 398.8 M records) — the bar

`setup/t20_lavamd.sh` (T20 first build, then T19, then d67) and the final build afterwards on the
same node (jobs 310855 + 310926 on c64, 310856 + 310927 on c50).

| mode, node | d67ed41 (T4's runtime) | T19 | T20 first build | **T20 final** |
|---|---|---|---|---|
| scalar-clock, c64 (EPYC 8124P) | 4,659 s, 64.9 GB | 7,247 s, 26.4 GB | 1,545 s, 23.2 GB | **1,494 s, 23.2 GB** |
| vector-clock, c50 (EPYC 9115) | 3,547 s, 65.4 GB | 5,473 s, 26.8 GB | 1,309 s, 23.6 GB | **1,286 s, 23.6 GB** |

**The bar is met in both modes**: T20 takes 32 % (scalar-clock) and 36 % (vector-clock) of the
d67ed41 runtime on the same node, and is under T4's absolute 3,162 / 3,505 s (measured on c3, which
another user's 8-day job held; c64 is slower than c3 for this program: d67ed41 4,659 s here against
3,162 s there). Against T19: 4.9× and 4.3× faster. T19's 7,247 s on c64 is well above its 3,858 s
on c3 in `eval/FLAT_BUCKETS.md`; only same-node ratios are compared here.

Reduced input (`-boxes1d 12`, `setup/t20_ab_small.sh`, two interleaved reps, the second under perf):

| mode, node | T19 | T20 first build | T20 final |
|---|---|---|---|
| scalar-clock, c61 (8124P) | 252.6 / 256.1 s | 85.1 / 86.1 s | — |
| vector-clock, c62 (8124P) | 302.9 / 304.1 s | 106.3 / 107.2 s | — |
| scalar-clock, c74 (7302P) | 295.4 / 299.8 s | — | 96.5 / 98.0 s |
| vector-clock, c51 (9115) | 182.8 / 183.2 s | — | 70.8 / 73.5 s |

Bucket state at kernel end is identical across runtimes (52,335,296 entries on 2,114,632 locations).

### 3.2 The step-5 programs (`setup/t20_time.sh`)

| program (mode) | T19, c60 | T20 first, c60 | T19, c77 | **T20 final, c77** |
|---|---|---|---|---|
| tiled_gemm N=256 (vector-clock) | 10.3 s, 1,001 MB | 5.8 s, 974 MB | 12.6 s, 1,001 MB | **7.4 s, 974 MB** |
| reduction-norace large (vector-clock) | 1.92 s | 1.37 s | 4.23 s | **1.57 s** |
| Indigo3 CC push 1296n (vector-clock) | 7.68 s | 4.32 s | 8.23 s | **4.53 s** |
| P7-hotspot (vector-clock, 100 kernels) | 315 s, 1.23 GB | 209 s, 1.22 GB | 366 s, 1.23 GB | **219 s, 1.19 GB** |
| P9-fpc (scalar-clock, 202 kernels) | 847 s, 2.18 GB | 645 s, 1.68 GB | 1,013 s, 2.18 GB | **478 s, 1.68 GB** |

(c60: EPYC 8124P, job 310857; c77: EPYC 7302P, job 310925.) **Every program is faster, and none
has a higher peak RSS.** fpc's ratio against T19 is 1.31× for the first build (c60) and 2.12× for
the final build (c77) — different nodes, so the share of the barrier change is indicated, not
measured; the first build's profile (§4) is what located it.

### 3.3 pathfinder (100 M threads), same node, 1,800 s each (`setup/t20_ab_long.sh`)

The program whose dense pages are largest (13 GB per kernel across `vc`, `vs`, `rmw_thr`), so the
one place the dense layout could have been slower. Kernels completed within the cap:

| mode, node | T19 | **T20 final** |
|---|---|---|
| scalar-clock, c77 | 8 | **18** |
| vector-clock, c58 | 10 | **17** |

(jobs 311174, 311173.)

### 3.4 The 5,400 s barrier-only set (`t4_long_ids.txt`, final build)

`setup/t19_long.sh` with `CAP=5400`, `YOSEMITE_HB_STATS_EVERY=2·10⁶`, scalar-clock then
vector-clock, one program per node (jobs 310932, 310934, 310935). T4's column is `eval/NO_DUMP.md`
§4.3 (other nodes, T4's build), so this compares outcomes, not time.

| program | T20: scalar-clock | T20: vector-clock | T4 (5,400 s): scalar / vector |
|---|---|---|---|
| P7-hotspot (100 kernels) | **finishes, 108 s**, 1.1 GB | **finishes, 128 s**, 1.2 GB | 619 s / 712 s |
| P7-srad (6,002 kernels) | **finishes, 1,501 s**, 1.1 GB | **finishes, 1,639 s**, 1.1 GB | 4,651 s / 5,234 s |
| P7-lavaMD (1 kernel) | **finishes, 1,511 s**, 23.2 GB (c60) | **finishes, 1,858 s**, 23.6 GB (c60) | 3,214 s / 3,614 s |
| P9-dxtc2 (100 kernels) | **finishes, 2,662 s**, 2.7 GB | **finishes, 3,193 s**, 2.8 GB | killed after 94 / 83 kernels |
| P7-heartwall | killed after 12 kernels | killed after 11 | killed after 5 / 4 |
| P7-pathfinder | killed after 52 kernels | killed after 27 | killed after 41 / 28 |
| P9-knn | killed after 27 kernels | killed after 18 | killed after 9 / 6 |
| P9-tridiagonal | killed after 36 kernels | killed after 27 | killed after 15 / 13 |
| P7-stencil1d (1,000 kernels) | STENCIL_SC | STENCIL_VC | dies at 174 GB, 0 kernels (both) |
| P7-particlefilter | OOM-killed at 174 GB after 4,770 s, 3 kernels | OOM-killed at 174 GB after 4,957 s, 3 kernels | dies at 123 GB, 3 kernels (both) |

**Four of the ten now finish in both modes** (T4: hotspot, srad and lavaMD at 5,400 s; dxtc2 is
new), and every program that does not finish completes more kernels than under T4 — except
pathfinder in vector-clock mode (27 against 28, on a different node; the same-node A/B of §3.3 has
T20 ahead of T19 there). particlefilter is the bucket term T19 measured (4.09 G entries at 128 M
records; `eval/FLAT_BUCKETS.md` §3.2): a limitation of every per-entry layout, not of T20.
The lavaMD row here (c60, with the growth snapshots) is not a same-node comparison; §3.1 is.

## 4. Where the remaining time goes

perf (`-F 199`, DWARF call graphs, self time) of the final build: lavaMD reduced input in both
modes (the second reps of §3.1, `setup/t20_ab_small.sh`, c74 and c51) and hotspot (vector-clock) /
fpc (scalar-clock) at `-F 49` (`setup/t20_profile.sh`, job 310931, then `t20_perf_flat.sh` /
`t20_perf_alloc.sh`). Files: `eval/baselines/setup/t20_perf/` (`v1-*` = the first build).

What T20 removed (T19 → T20 on reduced lavaMD, share of samples; T19's profile is
`t20_perf/v1-lavaMD-small-*-t19.lines.txt`, c61/c62): the per-thread hash maps
(`_Map_base<…SyncClock>`, `<…RmwThread>`, `<…RmwPc>`, `<…array<uint32_t, 32>>` = `last_pc`, and `V`)
took **34 % (scalar-clock) and 38 % (vector-clock)** of T19's samples; under T20 the
dense lookups (`ThreadArray::at`) are 5 % and 9 %, `rmw_note` 3 % and 2 %. On hotspot and fpc the
first build's profile showed the barrier assembly's `std::set<Tid>` (tree nodes per arriving
thread, freed at each instance) as the main allocator cost of the analysis thread; the final build
removed it.

What remains, final build, share of all samples:

| part | lavaMD sc | lavaMD vc | hotspot vc | fpc sc |
|---|---|---|---|---|
| `HbClock::process` with what is inlined into it — mostly T19's bucket layout (the hottest lines are `slot_order` and the `lower_bound`/`upper_bound` of the own-slot search and Check's run skips, then the slot scan and the tail merge), plus the lane loop and record decode — and `FlatBuckets::seg_find` | 59.8 | 45.0 | 19.5 | 9.5 |
| clock lookups: `base_get` (binary search in a shared base, per conflict test), `VClock::get` | 9.5 | 22.2 | 8.4 | — |
| dense per-thread arrays (`ThreadArray::at`) | 5.2 | 8.5 | 5.5 | 4.0 |
| R3 trace points (`rmw_note`) | 3.0 | 2.2 | 2.3 | 1.1 |
| barrier/sync joins (`sync_group`, `sync_group_vc`, `fire`) | <1 | <1 | 6.0 | 6.5 |
| allocator in the analysis thread (`_int_malloc`, `malloc`, `malloc_consolidate`, `unlink_chunk`): per-location slot arrays and the barrier maps (`pending_barriers`, `bar_warps_seen`, one node per instance) | <2 | <2 | 12.5 | 18.5 |
| outside the analysis thread: the teardown threads (one per kernel, each under perf's 1 % listing) and the CUDA / Sanitizer runtime threads, not separable here | — | — | 19.4 | 20.8 |
| `HB_STATS` scan (measurement only; the profile runs set it) | — | — | 7.0 | 12.6 |

The paper's overhead attribution, in one sentence: after T20 the reference mode's per-access cost
is the conflict test itself — the scan of a location's bucket slots (T19's layout) and the clock
comparison per conflicting slot (a binary search in a shared base) — and, on programs with many
short kernels, the allocation of per-location slot arrays and per-barrier-instance map nodes;
per-thread bookkeeping is below 10 %.

## 5. Commands

```
# private runtime (GPU-partition node for /usr/local/cuda); final build = job 310909
sbatch -p rtx4060ti16g -x c54,c2,c37 eval/baselines/setup/t20_build.sh
sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t20_rt_d67.sh          # the d67ed41 mirror
# step 3
sbatch -p rtx4060ti16g -x c54,c2,c37 -o <log> eval/baselines/setup/t20_check.sh            # 310918
W=<wt> IDS=eval/baselines/setup/t5b_parity_ids.txt TAG=t20-parity2 BASELINE_MODES=vector-clock,scalar-clock \
  FLOOR=120 sbatch --array=0-7 -x c54,c2,c37 eval/baselines/setup/p_t5b_timeout.sh          # 310920
... SHARD=0|2 NSHARDS=8 sbatch eval/baselines/setup/t20_shard.sh                           # 311129, 311130
W=<wt> TAG=t20-parity2 sbatch --dependency=afterany:<rec> eval/baselines/setup/p_t5b_parity_cmp.sh   # 311131
W=<wt> TAG=t20-parity2 CAP=25000 sbatch --dependency=afterany:<rec> eval/baselines/setup/p_t4_parity_cmp.sh   # 311132
.env/bin/python eval/baselines/setup/t4_parity.py table eval/baselines/setup/t4_parity/t20-parity2/shard*.json
.env/bin/python eval/baselines/setup/t20_verdicts.py '<wt-t19>/eval/results/t19-parity-v4/*.csv' 'eval/results/t20-parity2/*_8.csv'
# step 4
MODE=scalar-clock|vector-clock [RTS=t20] sbatch [-w <node>] eval/baselines/setup/t20_lavamd.sh
RUNTIMES="before after" sbatch -x c54,c2,c37 eval/baselines/setup/t20_time.sh
MODE=... PERF=1 RTS="t19=/home/fzheng4/AccelProf t20=<wt>" sbatch eval/baselines/setup/t20_ab_small.sh
ID=P7-pathfinder-cuda MODE=... sbatch eval/baselines/setup/t20_ab_long.sh
W=<wt> IDS=<ids> CAP=5400 OUTDIR=t20-long sbatch --array=... eval/baselines/setup/t19_long.sh
sbatch eval/baselines/setup/t20_profile.sh; sbatch eval/baselines/setup/t20_perf_flat.sh; sbatch eval/baselines/setup/t20_perf_alloc.sh
```

Kept on BeeGFS (`/mnt/beegfs/fzheng4/`): `cuvein_traces/t20-parity{,2}`, `t20-check`,
`t20-lavamd-{t20,t19,d67}`, `t20-time-{before,after}`, `t20-ab-small-*`, `t20-ab-long-*`,
`t20-long`, `t20_profile`.

## 6. What remains unverified

- One run per configuration (two reps on the reduced lavaMD, which agree within 1–4 %). The nodes are
  shared with other users' jobs; same-node ratios are reported, cross-node comparisons only as
  outcomes.
- T4's lavaMD bar was measured on c3, unavailable today; the same-node d67ed41 run stands in for it
  (on c50 it reproduces T4's vector-clock time within 1 %, 3,547 vs 3,505 s).
- T19's lavaMD scalar-clock time on c64 (7,247 s) is 1.9× its c3 time; not investigated.
- The final build's lavaMD numbers in §3.1 come from separate jobs on the same node as the other
  runtimes, a few hours apart.
- The perf attribution is self time; part of `process` is inlined STL that the line table places
  in library headers (assigned to buckets by the call sites at `slot_order`/`own_slot`).
- Not exercised by any test: the `ThreadArray` side map for tids outside the computed index other
  than async agents (`test_cp_async.py` exercises the agents), and grids above 2⁴⁰ thread indices.
- The background teardown frees the previous kernel's state while the next kernel runs: peak memory
  can briefly be both kernels' state. Not observed to matter in any run here (no RSS rose), but
  not measured specifically for back-to-back large kernels (stencil1d).
- The brief's "re-score of one kept program per suite" was replaced by the re-recorded verdict
  comparison of §2 (a re-score cannot exercise `HbClock`).
