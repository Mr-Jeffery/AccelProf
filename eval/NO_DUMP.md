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

_filled from job 296423_

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

_pasted from `setup/t4_sweep_table.md` (job 296393)_

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
   both modes — is not met**: of the ten barrier-only programs, hotspot finishes in both
   modes (and did with the dump in T5b); heartwall, lavaMD, pathfinder, srad, dxtc2, knn,
   tridiagonal hit the 1,200 s cap in both modes (RSS 1.5–44 GB); stencil1d and
   particlefilter exceed the node's memory. The vector-clock verdicts T4 adds on the
   realistic suites are the ones in item 1 (gpp, bezier-surface, crs, overlap, hotspot,
   backprop) and the P1/P3/P4 rows at a fraction of the memory.

### 4.3 Past the 1,200 s cap (`setup/t4_long.sh`, 5,400 s per mode)

_filled from jobs 296382 / 296421_

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
