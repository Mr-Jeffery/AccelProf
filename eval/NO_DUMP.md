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

## 3. Parity on the kept store (design note §6) — _pending_

Recording: `setup/t5b_parity_ids.txt` (65 programs, the T5b parity set) with the T4 runtime,
both modes, the default dump, kept on BeeGFS (`cuvein_traces/t4-parity`; job 296311, 8
shards). Comparison: `setup/t4_parity.py compare` (job 296312, `normal` nodes), per kernel
JSON: `hb_sync_pass` vs `barrier_only_pairs` (pairs, dist, order), `hb_races_sync_only` vs
the triples, `hb_rmw_points` vs `trace_rmw_points` (the lane cutoff lifted on the records'
side), and `analyze()` from the records vs from the aggregates (every verdict field,
`skipped_edges`, the candidate diagnostics).

_Table: per program and mode — kernels, ok, MISMATCH, no hb_events, over the 5 M-lane
cutoff — to be filled from `setup/t4_parity.py table`._

## 4. The timeout set and P7/P9 under no-dump (brief step 4) — _pending_

`setup/hb_clock_timeout_ids.txt` (58 programs) in both modes with `BASELINE_HB_DUMP=0
YOSEMITE_HB_STATS=1` (job 296320, 16 shards, `p_t5b_timeout.sh`, tool cap 1,200 s), then
the four P7/P9 programs not in that set (`setup/t4_p7p9_ids.txt`: P7-backprop, P7-bfs,
P9-crs, P9-overlap; job 296334). Against the dump runs of T5b (`eval/MEMORY_FOOTPRINT.md`
§7.4, `eval/results/t5b-final-timeout`): which finish, wall, peak RSS, the bucket term from
`hb_stats`, and the first vector-clock verdicts on those suites.

_Tables to be filled._

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
