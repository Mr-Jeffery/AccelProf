# T4 — No-dump mode: both clocks during the run, aggregates only

Branch `feat/no-dump` (based on `fix/late-seq-gating` 69d9594 = `cuVein` 8263e04 + T18).
Design note: `design/no_dump.md`. Written 2026-10-01; the numbers below are from the jobs
named in §6. Hardware: RTX 4060 Ti 16 GB (sm_89, driver 580.82.07) nodes of `rtx4060ti16g`
for every recording; `normal` nodes for the builds and the CPU comparisons.

## 1. What was built

`YOSEMITE_HB_DUMP=0` records an HB run without the `hb_events` array. The analyzer library
(`sanalyzer/src/tools/pc_dependency_analysis.cpp`; the collector is untouched) then:

- counts the drain instead of serialising it (`hb_events_count`, `hb_lanes_count`), and holds
  no record in host memory;
- runs `HbClock` on every drain in **both** modes: in vector-clock mode the vector clock and
  the barrier-only clock as before; in scalar-clock mode the barrier-only instance alone
  (`vector_pass = false`: Detect(T, sync) — barrier/syncwarp/exit assembly, `vs`, the
  buckets' `sclock`, the sync pairs, the TV monitor; no `vc`, `released`, gate, possible
  clock, `hb_races`, coherence profile — so `hb_races` stays absent and `sync_dominance`
  keeps its static-only branch);
- writes, at kernel end, under `"hb_aggregates": 1`, what the verdict layer used to derive
  from the records (design note §2): `hb_sync_pass` = the offline barrier-only pass as
  `[pc_lo, pc_hi, count, dist, first_pc, second_pc]` (the pairs plus `dist_out` /
  `order_out`), `hb_rmw_points` = R3's release/acquire points from the trace
  (`trace_rmw_points`, no lane cutoff), the counts, and in both modes `tv_violation`.

The default (`YOSEMITE_HB_DUMP=1`) is unchanged and lossless: the dump plus the same
aggregates beside it. `sync_dominance.analyze` reads the records when present and the
aggregates otherwise; `CUVEIN_PREFER_AGGREGATES=1` forces the aggregates on a full dump,
which is how parity is checked on one recording (§3). D4: `YOSEMITE_HB_HOST_MEMCPY` with
`YOSEMITE_HB_DUMP=0` is refused at start (T2's host analysis takes each kernel's footprint
from the records). `hb_oracle.py` is untouched: no clock value changed.

Harness: `BASELINE_HB_DUMP=0` puts a `parallel.py` sweep in no-dump mode (`blib.base_env`;
`meta.json` carries `hb_dump`); `aggregate.py`, `parallel.py._count_events`,
`latent_census.py` and `scale_harness.py` take `hb_events_count` from a no-dump kernel JSON.

Commits: d517db2 (runtime, reader, tests, scripts), 7cd70af (README, check results),
then the results commits listed in §6.

## 2. Checks on the private runtime (tested)

Runtime: `libsanalyzer` 2fc83fe0 built from the branch with GCC 12.4.0 (`-g -O3
-mtune=znver4`, no warnings; `setup/t4_build.sh`, job 296294), a private collector 024125b2
relinked from the objects the installed collector c9b862f9 was linked from (T18's
`/home/fzheng4/t18-stage/nvc/obj`) with RPATH to the private library; the installed fatbins.
`setup/t4_check.sh`, job 296310, node c3:

- the default tool path (no `YOSEMITE_HB_TRACE`): live runtime vs T4 runtime **IDENTICAL** up
  to device addresses and dist histograms on `race_interblock_none-lock_rtraw` and
  `norace_interblock_atom` (`setup/t5a_compare.norm`);
- the green set (CLAUDE.md A4 files + `test_instance_gate.py`) plus the new
  `python/test_no_dump.py`, every trace re-recorded: **332 passed, 2 skipped, 0 failed**
  (the two skips are the gate suite's empty parameter sets, as before T4; T18's count on the
  same files without the new test was 305 + 2 skipped).

`test_no_dump.py` (27 tests, two green-set kernels — `strong_stores_barrier_weak_load.cu`
and `write_after_unlock_other_schedule.cu` — recorded four ways each: vector-clock /
scalar-clock, with and without the dump) asserts on the dump recordings that `hb_sync_pass`
equals `barrier_only_pairs` as (pairs, dist, order), that in vector-clock mode
`hb_races_sync_only` equals its triples, that `hb_rmw_points` equals `trace_rmw_points`,
and that `analyze()` from the aggregates equals `analyze()` from the records in every field
of every verdict (plus `skipped_edges` and the candidate diagnostics); on the no-dump
recordings that `hb_events` is absent, `hb_aggregates` = 1, the counts are positive,
`analyze()` runs, the oracle raises its "no hb_events" error, and the verdicts (pair,
verdict, class, race type) equal the dump recording's; that the no-dump file is smaller;
and D4's refusal.

## 3. Parity on the kept store (design note §6) — proved-in-effect

Recording: `setup/t5b_parity_ids.txt` (65 programs, the T5b parity set) with the T4 runtime,
both modes, the default dump, one rep, tool cap `min(max(10 × native, 120), 1200)` s, kept
on BeeGFS (`cuvein_traces/t4-parity`; job 296311, 8 shards, rtx4060ti16g). Rows: 69 CLEAN,
50 RACE, 9 TIMEOUT (crs, interkernel-writewrite, one P1 1296n, particlefilter, overlap,
bfs: the 120 s floor, as in T5b's parity run), 2 ERROR (P7-bfs before the worktree's
`corpora` link existed; re-recorded as `t4-parity-fix`, where it times out at 120 s).
Comparison: `setup/t4_parity.py compare` (job 296312, 8 shards on `normal` nodes; the
P7-bfs re-recording job 296373), per kernel JSON:

- `hb_sync_pass` == `barrier_only_pairs(records)` as (pairs, widest distance, first
  orientation), and in vector-clock mode `hb_races_sync_only` == its triples;
- `hb_rmw_points` == `trace_rmw_points(records)`, the lane cutoff lifted on the records'
  side (`CUVEIN_BARRIER_PASS_MAX_LANES=10^12`);
- `analyze()` from the records == `analyze()` from the aggregates
  (`CUVEIN_PREFER_AGGREGATES=1`): every field of every verdict (pair, verdict, class,
  matrix class, conflict class, race type, observed distance, weight, candidate / rescued
  flags, `a2_uncertain`, `model_bug`, chain, strength), `skipped_edges`, and the candidate
  diagnostics.

Result: **799 kernel JSONs over 119 program × mode rows (56 programs with a dump in both
modes): 794 compared, 794 ok, 0 MISMATCH**; 12 of the 794 are above the production 5 M-lane
cutoff (P6-interkernel-readwrite 2 kernels × 2 modes, P7-backprop 2 × 2, and 4 in the P1 1296n
programs) and agree as well. The 5 remaining kernels (one P1 CC_Topo 1296n program,
scalar-clock, kernels 10–14) hit the comparison's 3,600 s per-program cap — the offline
`barrier_only_pairs` in Python is the slow side — and were re-compared with a 25,000 s cap
(job 296423, §3.1).

So on every kernel the store holds, the sync instance computed online is the offline pass,
R3's trace points are `trace_rmw_points`, and the verdict layer cannot tell a no-dump
file from a full dump (assumptions A1 and A2 of the design note hold on this corpus).

### 3.1 The five capped kernels

Job 296423 (`t4_parity.py compare --ids <that program> --cap 25000`, node c25): all 15
scalar-clock kernels of P1-CC_CUDA_V_Topo_Pull_Determ_…slower_atomic-1296n compare ok in
3,984 s (the offline `barrier_only_pairs` and `trace_rmw_points` in Python over 1296n
dumps are the slow side; the runtime had done the same work online in the 1,200 s run).
With them, the parity set is **799 of 799 kernel JSONs ok, 0 MISMATCH**, over 56 programs
with a dump in both modes (119 program × mode rows).

## 4. The timeout set and P7/P9 under no-dump (brief step 4)

`setup/hb_clock_timeout_ids.txt` (58 programs) in both modes with `BASELINE_HB_DUMP=0
YOSEMITE_HB_STATS=1` (job 296320, 16 shards, `p_t5b_timeout.sh`, tool cap 1,200 s = the
20-minute protocol, 125 GB `rtx4060ti16g` nodes), then the four P7/P9 programs not in that
set (`setup/t4_p7p9_ids.txt`; job 296334), and the HeCBench programs whose inputs the
worktree could not find on the first pass (`../data/...` is mirrored from
`eval/baselines/corpora`, which the worktree had not linked: heartwall, hotspot, srad,
dxtc2, bfs re-run as `t4-nodump-rerun{,2}`, jobs 296370 / 296374). The dump side is T5b's
run of the same programs (`eval/results/t5b-final-timeout`, `eval/MEMORY_FOOTPRINT.md` §7.4;
T5b runtime, same cap, same partition). Table: `setup/t4_sweep_table.py` (the `hb_stats`
columns read the kept no-dump dumps on BeeGFS: job 296393, `p_t4_table.sh`).

### 4.1 The table

`setup/t4_sweep_table.md` (job 296393; regenerate with `p_t4_table.sh`). Cells: verdict
(with the deduped report count for RACE), wall, peak RSS of the tool run. `buckets VC / SC`
= `hb_stats.hb_clock.buckets.bytes_est` at kernel end (max over the kernels; GB unless
marked MB) in the no-dump vector-clock / scalar-clock run; `vc / vs` = the two clocks'
`bytes_est`; `records` = `hb_events_count`, summed over the kernels. "—" = the run did not
reach a kernel end (no `hb_stats`), or the program is outside the timeout set.

| program | T5b dump vector-clock | T4 no-dump vector-clock | T5b dump scalar-clock | T4 no-dump scalar-clock | buckets VC / SC | vc / vs | records |
|---|---|---|---|---|---|---|---|
| **barriers, no atomics** (10) | | | | | | | |
| P7-heartwall-cuda | TIMEOUT 1200 s, 98.0 GB | TIMEOUT 1200 s, 16.5 GB | TIMEOUT 1200 s, 82.9 GB | TIMEOUT 1200 s, 16.5 GB | — / — | — | — |
| P7-hotspot-cuda | CLEAN 522 s, 2.2 GB | CLEAN 481 s, 2.0 GB | CLEAN 135 s, 1.1 GB | CLEAN 430 s, 1.9 GB | 1.01 / 1.01 | 66 MB / 36 MB | 37,410,000 |
| P7-lavaMD-cuda | TIMEOUT 1200 s, 102.5 GB | TIMEOUT 1200 s, 13.2 GB | ERROR 671 s, 181.0 GB | TIMEOUT 1200 s, 14.9 GB | — / — | — | — |
| P7-particlefilter-cuda | TIMEOUT 1230 s, 121.6 GB | TIMEOUT 1203 s, 119.3 GB | TIMEOUT 1217 s, 121.6 GB | TIMEOUT 1202 s, 119.3 GB | — / — | — | — |
| P7-pathfinder-cuda | TIMEOUT 1200 s, 30.3 GB | TIMEOUT 1200 s, 22.3 GB | TIMEOUT 1200 s, 7.6 GB | TIMEOUT 1200 s, 8.9 GB | — / — | — | — |
| P7-srad-cuda | TIMEOUT 1200 s, 1.6 GB | TIMEOUT 1200 s, 1.5 GB | TIMEOUT 1200 s, 1.0 GB | TIMEOUT 1200 s, 1.4 GB | — / — | — | — |
| P7-stencil1d-cuda | ERROR 721 s, 115.8 GB | ERROR 434 s, 118.6 GB | TIMEOUT 1200 s, 82.4 GB | ERROR 1093 s, 118.8 GB | — / — | — | — |
| P9-dxtc2-cuda | TIMEOUT 1200 s, 11.1 GB | TIMEOUT 1200 s, 8.0 GB | TIMEOUT 1200 s, 4.4 GB | TIMEOUT 1200 s, 7.9 GB | — / — | — | — |
| P9-knn-cuda | TIMEOUT 1204 s, 119.3 GB | TIMEOUT 1200 s, 43.7 GB | TIMEOUT 1200 s, 96.3 GB | TIMEOUT 1200 s, 50.8 GB | — / — | — | — |
| P9-tridiagonal-cuda | TIMEOUT 1200 s, 39.8 GB | TIMEOUT 1200 s, 27.3 GB | TIMEOUT 1200 s, 14.6 GB | TIMEOUT 1200 s, 26.8 GB | — / — | — | — |
| **atomics + barriers** (30) | | | | | | | |
| P1-CC_V_Data_Pull_…1296n | RACE 8 157 s, 20.7 GB | RACE 8 39 s, 1.3 GB | RACE 8 12 s, 1.0 GB | RACE 8 17 s, 1.2 GB | 0.23 / 0.23 | 91 MB / 48 MB | 1,949,121 |
| P1-CC_V_Data_Pull_…1296n | RACE 8 74 s, 22.0 GB | RACE 8 43 s, 1.3 GB | RACE 8 8 s, 1.0 GB | RACE 8 17 s, 1.2 GB | 0.23 / 0.23 | 91 MB / 48 MB | 2,009,133 |
| P1-CC_V_Data_Pull_…100n | RACE 8 2 s, 1.0 GB | RACE 8 2 s, 0.9 GB | RACE 8 1 s, 0.8 GB | RACE 8 1 s, 0.9 GB | 17 MB / 17 MB | 7 MB / 4 MB | 171,884 |
| P1-CC_V_Data_Pull_…1296n | RACE 9 215 s, 6.1 GB | RACE 9 52 s, 1.0 GB | RACE 9 12 s, 1.0 GB | RACE 9 26 s, 1.0 GB | 0.19 / 0.19 | 7 MB / 4 MB | 2,106,553 |
| P1-CC_V_Data_Pull_…100n | RACE 8 4 s, 1.0 GB | RACE 8 2 s, 0.9 GB | RACE 8 2 s, 0.8 GB | RACE 8 2 s, 0.9 GB | 17 MB / 17 MB | 7 MB / 4 MB | 174,119 |
| P1-CC_V_Data_Pull_…1296n | RACE 9 108 s, 6.2 GB | RACE 9 93 s, 1.0 GB | RACE 9 8 s, 1.0 GB | RACE 9 32 s, 1.0 GB | 0.19 / 0.19 | 7 MB / 4 MB | 2,101,088 |
| P1-CC_V_Data_Pull_…1296n | RACE 4 39 s, 24.0 GB | RACE 4 11 s, 1.2 GB | RACE 4 5 s, 1.0 GB | RACE 4 8 s, 1.1 GB | 0.19 / 0.19 | 91 MB / 48 MB | 1,199,405 |
| P1-CC_V_Data_Pull_…1296n | RACE 4 39 s, 24.5 GB | RACE 4 11 s, 1.2 GB | RACE 4 5 s, 1.0 GB | RACE 4 8 s, 1.1 GB | 0.19 / 0.19 | 91 MB / 48 MB | 1,236,204 |
| P1-CC_V_Data_Pull_…100n | RACE 4 2 s, 1.0 GB | RACE 4 1 s, 0.9 GB | RACE 4 1 s, 0.8 GB | RACE 4 1 s, 0.9 GB | 15 MB / 15 MB | 7 MB / 4 MB | 157,163 |
| P1-CC_V_Data_Pull_…1296n | RACE 5 77 s, 6.1 GB | RACE 5 15 s, 1.0 GB | RACE 5 6 s, 1.0 GB | RACE 5 9 s, 1.0 GB | 0.16 / 0.16 | 7 MB / 4 MB | 1,319,791 |
| P1-CC_V_Data_Pull_…100n | RACE 4 4 s, 1.0 GB | RACE 4 1 s, 0.9 GB | RACE 4 2 s, 0.8 GB | RACE 4 1 s, 0.9 GB | 15 MB / 15 MB | 7 MB / 4 MB | 155,434 |
| P1-CC_V_Data_Pull_…1296n | RACE 5 79 s, 6.2 GB | RACE 5 10 s, 1.0 GB | RACE 5 6 s, 1.0 GB | RACE 5 6 s, 1.0 GB | 0.16 / 0.16 | 7 MB / 4 MB | 1,317,011 |
| P1-CC_V_Data_Push_…1296n | RACE 4 19 s, 6.8 GB | RACE 4 6 s, 1.2 GB | RACE 4 4 s, 1.0 GB | RACE 4 4 s, 1.1 GB | 0.19 / 0.19 | 91 MB / 48 MB | 525,336 |
| P1-CC_V_Data_Push_…1296n | RACE 4 10 s, 6.9 GB | RACE 4 6 s, 1.2 GB | RACE 4 2 s, 1.0 GB | RACE 4 4 s, 1.1 GB | 0.19 / 0.19 | 91 MB / 48 MB | 501,616 |
| P1-CC_V_Data_Push_…1296n | RACE 4 19 s, 5.6 GB | RACE 4 4 s, 1.0 GB | RACE 4 2 s, 1.0 GB | RACE 4 3 s, 1.0 GB | 0.16 / 0.16 | 7 MB / 4 MB | 488,760 |
| P1-CC_V_Data_Push_…1296n | RACE 4 35 s, 5.6 GB | RACE 4 6 s, 1.0 GB | RACE 4 4 s, 1.0 GB | RACE 4 4 s, 1.0 GB | 0.16 / 0.16 | 7 MB / 4 MB | 501,852 |
| P3-CC_V_Data_Pull_…100n | RACE 1 7 s, 1.3 GB | RACE 1 2 s, 0.9 GB | RACE 1 1 s, 0.8 GB | RACE 1 2 s, 0.9 GB | 17 MB / 17 MB | 7 MB / 4 MB | 141,173 |
| P3-CC_V_Data_Pull_…100n | RACE 1 6 s, 1.4 GB | RACE 1 9 s, 1.2 GB | RACE 1 1 s, 0.8 GB | RACE 1 2 s, 0.9 GB | 17 MB / 17 MB | 55 MB / 4 MB | 141,597 |
| P4-graph-coloring-norace-large | CLEAN 36 s, 1.9 GB | CLEAN 3 s, 0.8 GB | CLEAN 1 s, 0.8 GB | CLEAN 1 s, 0.8 GB | 13 MB / 13 MB | 1 MB / 0 MB | 147,006 |
| P4-graph-coloring-racy-large | RACE 14 51 s, 1.8 GB | RACE 14 3 s, 0.8 GB | RACE 14 2 s, 0.8 GB | RACE 14 2 s, 0.8 GB | 13 MB / 13 MB | 1 MB / 0 MB | 186,283 |
| P4-graph-connectivity-norace-large | CLEAN 268 s, 3.0 GB | CLEAN 4 s, 0.9 GB | CLEAN 2 s, 0.9 GB | CLEAN 2 s, 0.9 GB | 49 MB / 62 MB | 1 MB / 1 MB | 104,181 |
| P4-graph-connectivity-racy-large | RACE 9 427 s, 3.2 GB | RACE 10 4 s, 0.9 GB | RACE 4 2 s, 0.9 GB | RACE 4 2 s, 0.9 GB | 54 MB / 58 MB | 1 MB / 1 MB | 123,279 |
| P4-matrix-multiplication-norace-large | CLEAN 705 s, 15.5 GB | CLEAN 1154 s, 5.3 GB | CLEAN 42 s, 10.9 GB | CLEAN 73 s, 1.3 GB | 0.46 / 0.46 | 69 MB / 1 MB | 7,675,094 |
| P4-matrix-multiplication-racy-large | RACE 3 806 s, 16.6 GB | RACE 3 567 s, 4.5 GB | RACE 3 45 s, 10.9 GB | RACE 3 80 s, 1.3 GB | 0.46 / 0.46 | 2 MB / 1 MB | 7,678,810 |
| P4-uts-norace-large | CLEAN 805 s, 6.0 GB | CLEAN 54 s, 1.3 GB | CLEAN 7 s, 2.5 GB | CLEAN 11 s, 1.0 GB | 0.15 / 0.14 | 2 MB / 1 MB | 8,019,120 |
| P4-uts-norace-small | CLEAN 26 s, 1.8 GB | CLEAN 2 s, 0.9 GB | CLEAN 1 s, 0.9 GB | CLEAN 1 s, 0.8 GB | 11 MB / 11 MB | 2 MB / 1 MB | 356,350 |
| P4-uts-racy-large | RACE 23 802 s, 6.5 GB | RACE 28 103 s, 1.3 GB | RACE 11 7 s, 2.5 GB | RACE 12 16 s, 1.0 GB | 0.14 / 0.14 | 2 MB / 1 MB | 8,387,364 |
| P4-uts-racy-small | RACE 11 26 s, 1.8 GB | RACE 11 2 s, 0.9 GB | RACE 9 1 s, 0.9 GB | RACE 11 1 s, 0.8 GB | 11 MB / 11 MB | 2 MB / 1 MB | 310,694 |
| P9-expdist-cuda | TIMEOUT 1200 s, 5.7 GB | TIMEOUT 1200 s, 12.0 GB | TIMEOUT 1200 s, 59.8 GB | TIMEOUT 1200 s, 7.7 GB | — / — | — | — |
| P9-fpc-cuda | ERROR 1160 s, 118.3 GB | TIMEOUT 1200 s, 4.3 GB | CLEAN 258 s, 1.3 GB | TIMEOUT 1200 s, 3.1 GB | — / — | — | — |
| **atomics only** (8) | | | | | | | |
| P1-BFS_V_Data_Pull_…1296n | CLEAN 73 s, 5.2 GB | CLEAN 3 s, 0.9 GB | CLEAN 3 s, 0.9 GB | CLEAN 2 s, 0.9 GB | 56 MB / 56 MB | 7 MB / 3 MB | 217,790 |
| P1-CC_V_Data_Pull_…1296n | RACE 8 17 s, 3.4 GB | RACE 8 3 s, 0.9 GB | RACE 8 2 s, 0.8 GB | RACE 8 2 s, 0.9 GB | 24 MB / 24 MB | 7 MB / 4 MB | 352,229 |
| P1-CC_V_Data_Pull_…1296n | RACE 8 17 s, 3.6 GB | RACE 8 2 s, 0.9 GB | RACE 8 1 s, 0.8 GB | RACE 8 1 s, 0.9 GB | 24 MB / 24 MB | 7 MB / 4 MB | 353,427 |
| P1-CC_V_Data_Pull_…1296n | RACE 4 23 s, 3.5 GB | RACE 4 2 s, 0.9 GB | RACE 4 2 s, 0.8 GB | RACE 4 1 s, 0.9 GB | 21 MB / 21 MB | 7 MB / 4 MB | 315,129 |
| P1-CC_V_Data_Pull_…1296n | RACE 4 24 s, 3.7 GB | RACE 4 3 s, 0.9 GB | RACE 4 2 s, 0.8 GB | RACE 4 2 s, 0.9 GB | 21 MB / 21 MB | 7 MB / 4 MB | 327,525 |
| P9-atomicCAS-cuda | TIMEOUT 1200 s, 73.1 GB | TIMEOUT 1200 s, 96.1 GB | TIMEOUT 1200 s, 0.8 GB | TIMEOUT 1200 s, 0.9 GB | — / — | — | — |
| P9-gpp-cuda | TIMEOUT 1200 s, 73.4 GB | CLEAN 115 s, 2.8 GB | CLEAN 61 s, 2.2 GB | CLEAN 89 s, 2.7 GB | 1.90 / 1.90 | 52 MB / 25 MB | 10,368,000 |
| P9-mr-cuda | ERROR 693 s, 1.0 GB | ERROR 317 s, 0.9 GB | ERROR 177 s, 0.9 GB | ERROR 237 s, 0.9 GB | 52 MB / 52 MB | 13 MB / 6 MB | 82,019,200 |
| **neither** (10) | | | | | | | |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-fixed | TIMEOUT 1200 s, 123.7 GB | TIMEOUT 1200 s, 47.3 GB | ERROR 598 s, 181.3 GB | TIMEOUT 1200 s, 51.3 GB | — / — | — | — |
| P6-asyncmemcpy-kernel_memcpy_dtoh_race-racy | TIMEOUT 1200 s, 125.2 GB | TIMEOUT 1200 s, 40.5 GB | TIMEOUT 1201 s, 165.7 GB | TIMEOUT 1200 s, 43.9 GB | — / — | — | — |
| P6-asyncmemcpy-memcpy_htod_kernel_race-racy | CLEAN 231 s, 100.1 GB | CLEAN 128 s, 88.8 GB | CLEAN 77 s, 16.0 GB | CLEAN 127 s, 88.8 GB | 88.05 / 88.05 | 0 MB / 0 MB | 8,388,610 |
| P6-interkernel-global_writewrite_race-fixed | CLEAN 255 s, 11.7 GB | CLEAN 173 s, 0.8 GB | CLEAN 252 s, 11.7 GB | CLEAN 172 s, 0.8 GB | 0 MB / 0 MB | 0 MB / 0 MB | 109,375,002 |
| P6-interkernel-global_writewrite_race-racy | CLEAN 252 s, 11.1 GB | CLEAN 153 s, 0.8 GB | CLEAN 248 s, 11.1 GB | CLEAN 151 s, 0.8 GB | 0 MB / 0 MB | 0 MB / 0 MB | 106,250,002 |
| P7-bezier-surface-cuda | ERROR 713 s, 102.6 GB | CLEAN 766 s, 66.9 GB | ERROR 815 s, 102.7 GB | CLEAN 732 s, 66.9 GB | 66.06 / 66.06 | 1 MB / 0 MB | 106,955,008 |
| P7-bitonic-sort-cuda | TIMEOUT 1200 s, 21.2 GB | TIMEOUT 1200 s, 20.1 GB | TIMEOUT 1200 s, 4.3 GB | TIMEOUT 1200 s, 18.0 GB | — / — | — | — |
| P7-haversine-cuda | TIMEOUT 1200 s, 28.3 GB | TIMEOUT 1200 s, 22.3 GB | TIMEOUT 1200 s, 10.1 GB | TIMEOUT 1200 s, 20.8 GB | — / — | — | — |
| P7-mandelbrot-cuda | TIMEOUT 1200 s, 2.6 GB | TIMEOUT 1200 s, 2.4 GB | TIMEOUT 1200 s, 1.2 GB | TIMEOUT 1200 s, 2.2 GB | — / — | — | — |
| P7-nbody-cuda | TIMEOUT 1200 s, 99.0 GB | TIMEOUT 1200 s, 56.6 GB | TIMEOUT 1200 s, 43.3 GB | TIMEOUT 1200 s, 56.6 GB | — / — | — | — |
| **P7/P9 not in the timeout set** (4) | | | | | | | |
| P7-backprop-cuda | — | CLEAN 15 s, 2.5 GB | — | CLEAN 13 s, 2.4 GB | 1.33 / 1.33 | — | — |
| P7-bfs-cuda | — | TIMEOUT 1200 s, 2.5 GB | — | TIMEOUT 1200 s, 2.4 GB | — / — | — | — |
| P9-crs-cuda | — | CLEAN 161 s, 1.6 GB | — | CLEAN 137 s, 1.6 GB | 0.67 / 0.67 | — | — |
| P9-overlap-cuda | — | CLEAN 245 s, 5.9 GB | — | CLEAN 204 s, 5.4 GB | 3.66 / 3.66 | — | — |

Totals over the 58: finish (RACE/CLEAN) in vector-clock mode 37 with the dump (T5b) → 39
without (gpp and bezier-surface gained); scalar-clock 39 → 39 (bezier-surface gained, fpc
lost); under 120 s: 32
(vector-clock) and 34 (scalar-clock) of the 58 without the dump. The rows with the dump are
T5b's recordings (a different schedule and node): verdicts and report counts agree except
graph-connectivity-racy-large (RACE 9 → 10 in vector-clock) and uts-racy-large (23 → 28
vector-clock, 11 → 12 scalar-clock), the schedule-dependent report counts those two
programs always had (T5b, T12).

### 4.2 What it says

1. **Where the dump was the bound, no-dump finishes or shrinks the run.** P9-gpp
   vector-clock: TIMEOUT at 73 GB → CLEAN in 115 s, 2.8 GB. P7-bezier-surface: ERROR
   (102 GB) in both modes → CLEAN 766 s / 732 s at 67 GB. P9-crs-cuda (the T9-0 cutoff
   program, 50 kernels): CLEAN in both modes, 161 s / 137 s, 1.7 GB — scalar-clock mode now
   judges every kernel of it. P9-overlap: CLEAN 245 s / 204 s, 6 GB. P7-hotspot: CLEAN
   481 s / 430 s at 2.0 GB (T5b: 522 s / 135 s at 2.2 / 1.1 GB). Peak RSS of the runs that
   still time out drops where the records dominated it: lavaMD 102 → 14 GB, knn 119 → 44 GB,
   nbody 99 → 57 GB, memcpy_dtoh 124 → 47 GB, heartwall 98 → 17 GB, atomicCAS scalar-clock
   stays at 0.9 GB. The P1/P3/P4 rows keep T5b's verdicts (report counts included) at a
   fraction of the RSS (CC 1296n vector-clock 21–25 GB → 1.0–1.3 GB).
2. **Same node, same binary (A/B, job 296383, c50, build 2fc83fe0):** dump → no-dump,
   vector-clock / scalar-clock —
   matrix-multiplication-norace-large 717 s, 15.4 GB → 647 s, 5.5 GB / 88 s, 11.6 GB →
   47 s, 1.3 GB; uts-racy-large 113 s, 3.2 GB → 92 s, 1.3 GB / 25 s, 2.9 GB → 17 s, 1.0 GB;
   CC 1296n (Pull_Determ_Persist, default) 46 s, 1.24 GB → 40 s, 1.06 GB / 23 s, 1.23 GB →
   18 s, 1.05 GB. (The sweep's 1,154 s for matmul vector-clock on c78 was schedule/node
   variance: the lock program's run time depends on the schedule.)
3. **The programs that still do not finish are bounded by the instrumented run itself,
   not by the dump.** Every remaining TIMEOUT has a native wall of 0.4–20 s, so the harness
   cap is the 1,200 s ceiling, and the tool is at it in both modes with the dump gone. Two
   kinds, measured with a 5,400 s cap per mode and `YOSEMITE_HB_STATS_EVERY=2·10⁶` growth
   lines (`setup/t4_long.sh`, job 296382 / 296421, §4.3):
   - *memory*: P7-stencil1d dies at 174 GB on a 188 GB node in both modes, and
     P7-particlefilter reached 122 GB at the 1,200 s cap. stencil1d's growth lines: after
     2 M / 4 M / 8 M / 16 M / 32 M records the sync instance holds 9.6 M / 19.1 M / 38.2 M /
     76.3 M / 152.6 M locations, 56.5 M / 113 M / 226 M / 452 M / 905 M bucket entries
     (6.3 / 12.6 / 25.3 / 50.6 / 101 GB estimated), 3.1 M / 6.3 M / 12.5 M / 25 M / 50 M
     threads, RSS 8.6 / 15.9 / 30.5 / 59.6 / 118 GB — linear in the records, identical in
     both modes (the vector clock adds ~6 %): a kernel of tens of millions of threads each
     touching its own neighbourhood, where the per-(location, thread) buckets the soundness
     theorem requires (no FastTrack collapse, hb_proof.tex Theorem "Sound") are as many as
     the lane-accesses. The dump was O(lane-accesses) too; no-dump removes its serialisation
     and parsing, not this term. A compact bucket representation (flat per-location vectors
     instead of a hash node per entry, ~20 B instead of ~110 B per entry) would divide the
     term by ~5 but not change its order; that is a follow-up (T7's profiling scope), not
     this task.
   - *time*: the rest run under a few GB (srad 1.5, mandelbrot 2.4, fpc 3–4, expdist 8–12,
     dxtc2 8, pathfinder 9–23, bitonic 18–21, haversine 21–23, tridiagonal 27 GB) and simply
     do not reach the end of the instrumented run in 1,200 s: `HbClock` consumes a record
     stream of 10⁸–10⁹ lane-accesses at roughly 1 µs per lane-access, and the collector's
     own instrumentation is paid as well. The 5,400 s runs (§4.3) say which of them finish
     at all.
4. **One regression of scalar-clock mode, by construction.** Before T4 scalar-clock mode
   only serialised; now it runs the sync instance online, whose per-access cost on a
   program with as many locations as accesses exceeds the old serialisation cost. P9-fpc
   (202 kernels, 145.6 M records, 4.2 M locations for 4.4 M lane-accesses per kernel —
   `setup/t4_hotloc.py` on T5b's kept dump): scalar-clock CLEAN in 258 s with the dump (T5b)
   → TIMEOUT at 1,200 s without it; the offline pass over that dump is the same work in
   Python and never finished either (T9-0: fpc and mr under the 4 h analysis cap), so the
   verdict T5b reported for fpc in scalar-clock mode was the static leg alone. hotspot
   shows the same shift in the other direction's proportions (scalar-clock 135 s → 430 s,
   both CLEAN). Where the sync instance is cheap relative to the records (every P1/P3/P4
   row, uts, matmul, gpp, crs, overlap) scalar-clock no-dump is faster than scalar-clock
   dump. The per-access cost is `buckets` (a `std::map` keyed by location with a hash map
   per key group) — the same follow-up as item 3.
5. **The acceptance bar of the brief — the nine barrier-only programs produce verdicts in
   both modes — is not met at the 1,200 s cap**: of the ten barrier-only programs, hotspot
   finishes in both modes (and did with the dump in T5b); heartwall, lavaMD, pathfinder,
   srad, dxtc2, knn, tridiagonal hit the 1,200 s cap in both modes (RSS 1.5–51 GB);
   stencil1d and particlefilter exceed the node's memory. Past the cap (§4.3) lavaMD and
   srad finish in scalar-clock mode. The vector-clock verdicts T4 adds on the realistic
   suites are the ones in item 1 (gpp, bezier-surface, crs, overlap, hotspot, backprop) and
   the P1/P3/P4 rows at a fraction of the memory.
6. **Two rows that are not what their cell says.** P9-mr-cuda: the *run* now finishes in
   both modes (317 s / 237 s, 0.9 GB; T5b: 693 s / 177 s) and 1,600 kernel JSONs are written;
   the ERROR is the harness's 3,600 s *analysis* cap — `sync_dominance.analyze` over 1,600
   kernels, each tried against every CFG dot — the same bound T9-0 met on mr-cuda (4 h), and
   T7's subject, not T4's. P9-knn-cuda: 44–51 GB of RSS with an HB state of 44 MB (9 kernels
   of 9,216 records, 82 K threads, §4.3): the memory is the dependency tool's own per-kernel
   shadow of knn's working set, not `HbClock`'s; the dump run's 96–119 GB was that plus the
   records.

### 4.3 Past the 1,200 s cap (`setup/t4_long.sh`, 5,400 s per mode)

The ten barrier-only programs, `accelprof` run directly (the harness cap is hard) with
`YOSEMITE_HB_DUMP=0 YOSEMITE_HB_STATS=1 YOSEMITE_HB_STATS_EVERY=2000000`, scalar-clock
mode first, then vector-clock, 5,400 s each, one program per node (job 296382; lavaMD and
particlefilter re-run as 296421 after the first attempt failed to start on nodes without
GNU `time`). "kernels" = kernel JSONs written (= kernels that reached their end); RSS = the
`hb_stats` line of the last finished kernel (`rss_kb`), or `maxrss` of GNU time where the
run ended by itself; "records" = `hb_events_count` of that kernel; buckets = entries /
`bytes_est`.

| program | scalar-clock: outcome, kernels | RSS, HB state at the last kernel end | vector-clock |
|---|---|---|---|
| P7-hotspot (100 kernels) | **finishes, 619 s** | 2.0 GB; 374 K records/kernel, 2.07 M locations, 4.95 M entries (1.0 GB est), 473 K threads | **finishes, 712 s**, 2.1 GB |
| P7-srad (6,002 kernels) | **finishes, 4,651 s** | 1.5 GB; 21.6 K records/kernel, 230 K locations, 460 K entries (125 MB) | _pending_ (2,455 kernels at the cap? — filled when the job ends) |
| P7-lavaMD (1 kernel) | **finishes, 3,214 s** | 64.9 GB; 398.8 M records, 33.1 M locations, 866.8 M entries (60.8 GB est), 3.46 M threads | _pending_ |
| P7-heartwall | killed at 5,400 s after 5 kernels | 17.3 GB; 78.4 M records/kernel, 10.6 M locations, 205 M entries (16.2 GB est), 13 K threads | _pending_ (2 kernels) |
| P7-pathfinder | killed at 5,400 s after 41 kernels | 9.4 GB; 35.3 M records/kernel, 908 K locations, 1.33 M entries (353 MB), **100 M threads** (`vs`) | _pending_ (7 kernels; 23.3 GB — the main clock's per-thread entries) |
| P9-dxtc2 | killed at 5,400 s after 94 kernels | 8.2 GB; 6.34 M records/kernel, 7.9 M locations, 60.2 M entries (6.7 GB est), 1.05 M threads | _pending_ (20 kernels) |
| P9-knn | killed at 5,400 s after 9 kernels | 68.1 GB RSS with an HB state of 44 MB (9.2 K records/kernel, 82 K locations, 164 K entries): the dependency tool's shadow, not HbClock | _pending_ |
| P9-tridiagonal | killed at 5,400 s after 15 kernels | 28.1 GB; 16.7 M records/kernel, 38.4 M locations, 232.5 M entries (25.5 GB est), 3.84 M threads | _pending_ (3 kernels) |
| P7-stencil1d | **dies at 174 GB** (rc 1) after 1,050 s, 0 kernels | growth: 32 M records → 152.6 M locations, 905 M entries (101 GB est), 50 M threads, RSS 118 GB (§4.2 item 3) | dies at 174 GB after 1,034 s |
| P7-particlefilter | **dies at 122.6 GB** (rc 1) after 938 s, 3 kernels | growth in its 4th kernel: 2 M / 4 M / 8 M / 16 M / 32 M / 64 M records → 64 M / 128 M / 256 M / 512 M / 1.02 G / 2.05 G entries on only 59 K / 66 K / 79 K / 106 K / 152 K / 234 K locations (3.9 / 7.7 / 15.4 / 30.7 / 60.7 / 122 GB est), 54–94 K threads, RSS 22 / 22 / 22 / 31 / 60 / 120 GB | dies at 122.8 GB after 1,068 s, 3 kernels |

Two shapes, then. stencil1d is *many threads, each its own locations*: entries ≈ lane
accesses (6 per location, one per thread), 50 M threads in one kernel. particlefilter is
*few locations, many threads each*: 2.05 G entries on 234 K locations is ~8,800 threads
per location — every thread reads (and some write) the same arrays, and a per-(location,
thread) bucket keeps every such pair; this is the regime where the FastTrack epoch collapse
Theorem "Sound" forbids for writers would also collapse the readers. lavaMD (867 M
entries, 61 GB) and tridiagonal (232 M, 25.5 GB per kernel) are the same shape at a size
the node holds; heartwall and dxtc2 are bounded by time (78 M and 6.3 M records per kernel
at roughly 1 µs each, times the kernel count); pathfinder by its 100 M-thread grid (a `vs`
entry per thread, and a main-clock entry per thread in vector-clock mode: 9.4 → 23.3 GB).

## 5. What remains unverified / not done

- Step 5 (streaming lossless encoding for the mid-size suites) and step 6 (the A2-gap tail
  steps) were not started.
- Parity is established on programs that dump (§3); a no-dump program's verdict rests on the
  runtime alone, as the design note §7 states.
- The sync instance's cost in scalar-clock mode (the bucket term) is measured in §4; whether
  it stays within the node on every program is a result of §4, not a property.

## 6. Commands, revision, jobs

```
# private runtime (normal node)
W=/home/fzheng4/wt-T4 sbatch -p normal eval/baselines/setup/t4_build.sh            # 296294
# default path unchanged + green set + test_no_dump (GPU node)
W=/home/fzheng4/wt-T4 sbatch -p rtx4060ti16g -x c54,c2 eval/baselines/setup/t4_check.sh   # 296310
# parity recording (both modes, default dump, kept) and comparison
W=/home/fzheng4/wt-T4 IDS=eval/baselines/setup/t5b_parity_ids.txt TAG=t4-parity \
  BASELINE_MODES=vector-clock,scalar-clock FLOOR=120 sbatch --array=0-7 \
  -o /home/fzheng4/wt-T4/build_logs/t4-parity-%A_%a.log eval/baselines/setup/p_t5b_timeout.sh   # 296311
W=/home/fzheng4/wt-T4 TAG=t4-parity sbatch --dependency=afterany:296311 \
  -o /home/fzheng4/wt-T4/build_logs/t4-parity-cmp-%A_%a.log eval/baselines/setup/p_t4_parity_cmp.sh   # 296312
# the timeout set and the P7/P9 remainder under no-dump, both modes, HB_STATS on
W=/home/fzheng4/wt-T4 TAG=t4-nodump BASELINE_HB_DUMP=0 YOSEMITE_HB_STATS=1 \
  BASELINE_MODES=vector-clock,scalar-clock sbatch --array=0-15 \
  -o /home/fzheng4/wt-T4/build_logs/t4-nodump-%A_%a.log eval/baselines/setup/p_t5b_timeout.sh   # 296320
W=/home/fzheng4/wt-T4 IDS=eval/baselines/setup/t4_p7p9_ids.txt TAG=t4-nodump-p7p9 BASELINE_HB_DUMP=0 \
  YOSEMITE_HB_STATS=1 BASELINE_MODES=vector-clock,scalar-clock sbatch --array=0-1 \
  -o /home/fzheng4/wt-T4/build_logs/t4-nodump-p7p9-%A_%a.log eval/baselines/setup/p_t5b_timeout.sh
```
