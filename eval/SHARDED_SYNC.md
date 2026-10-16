# T22 — the sharded scalar-clock sync pass

Branch `perf/sharded-sync-pass` from `cuVein` 4094187 (X0 merged). Unmerged and uninstalled (the
merge and install are Jeffery's). Freeze exception of the brief: only HbClock's sync pass under
`sanalyzer/` changed — not vector-clock mode's clock, not `nv-compute/`, not `python/hb_oracle.py`,
not the PCDepGraph worker pool (`-n 1` stays). Written 2026-10-15/16. Facts only; legend:
**proved-in-effect** = an invariant checked over the stated traces; **tested** = a specific result
asserted by a test; **assumed/unverified** = said so.

## 0. Runtime and hardware

Code: `48f1ff7` (first design), `3cf25a1` (router thread; monitor and R3 points distributed),
`b6a615e` (chunked routing; **the build every verification below uses**). Private runtime as T20's
(`setup/t22_build.sh`): the worktree's libsanalyzer, built with GCC 12.4.0 `-g -O3 -mtune=znver4`,
and a collector relinked from the d67ed41 install's objects (`git diff d67ed41 HEAD -- nv-compute`
is empty) with RPATH to it; the installed fatbins. The shared runtime was not touched.

| component | sha256[:16] |
|---|---|
| libsanalyzer, `b6a615e` (final) | `d9c16d82d2465602` |
| libsanalyzer, `3cf25a1` / `48f1ff7` (diagnostics only) | `718fb1586f958958` / `435f283ecadd2f7d` (with drain timing) |
| collector (private relink) | `bf629f05757b1d73` |
| fatbin (installed) | `a2d7368bc1c61986` |
| installed libsanalyzer, for comparison | `2201fcb7d57ae783` |

Hardware: the rtx4060ti16g partition was fully allocated (X1's 24 h pass, X1-follow, other users),
so every GPU run so far is on **c28** (partition rtx4060ti8g: RTX 4060 Ti 8 GB, sm_89, driver
580.65.06; AMD Turin, `nproc` 128 in the job, 755 GB). The rtx4060ti16g hosts have 16 cores
(2 × 8). CPU-only replays ran on c28 or, for the small synthetic traces, the login node.

## 1. Design as built

**Knob.** `YOSEMITE_HB_SHARDS=N` (read once; 2..64, above 64 clamped with a notice). Unset, 0 or 1:
the serial pass, unchanged (the per-record step became `process_one<ROLE_SERIAL>`, the same code;
§1.6). N > 1 shards the pass in scalar-clock mode only; in vector-clock mode, or with
`YOSEMITE_HB_NO_SYNC_ONLY` (no sync pass to shard), the knob is ignored with one stderr line.
`YOSEMITE_HB_SHARD_INLINE_MAX` (default 4,096) runs a drain below that many records on the drain
thread (routing and the shards one after the other: no thread wake-ups for the small drains of
many-kernel programs); 0 sends every drain through the threads (the tests' small kernels).

**1.1 Partition.** A memory record's lane goes to the shard owning its location. The location key
is the serial pass's (`(space, block for shared else 0, address)`); the shard is a hash of
`(space, block, address >> 7)`, i.e. of the 128-byte segment the location lies in (a function of
the location, so every record of a location reaches one shard; a coalesced warp access is one
segment, hence usually one shard). The hash is not FlatBuckets' (whose low bits index each
shard's own segment directory).

**1.2 What every shard replays.** Every exit, barrier arrival, syncwarp and cp.async
commit/wait record, and every cp.async copy (its issue joins the issuing thread's sync clock into
its agent's: a clock operation carried by a memory record, Definition "Agents" of `hb_proof.tex`;
the copy's Check and bucket update happen only in the shard owning its location). Each shard has
its own HbClock: per-thread sync clocks (T20's dense `ThreadArray`), exit- and count-aware barrier
assembly (Definition "Instances", the serial code), and its slice of the T19 buckets. Check and the
conflict test are the serial ones, called unchanged.

**1.3 What one shard does per record.** Two outputs of scalar-clock mode are not per location:
R3's trace points (`hb_rmw_points`, per thread: a thread's non-RMW pcs since its last RMW) and the
trace-validity monitor (`tv_violation`; its state — `warp_waiting`, `bar_warps_seen`, the exit
lanes — is per block or warp). Each record is therefore also given, by an entry flag, to one shard
for the monitor (the shard of the record's block) and, for a memory record, to one shard for R3's
points (the shard of the warp's chunk of 2^b consecutive thread indices, b in 5..14 chosen from
the grid so that at least 64 chunks per shard exist; page-aligned on large grids, so the dense
per-thread arrays are not touched by every shard). A shard monitors exactly its flagged records
(`strict` is set per record); the barrier assembly the monitor reads is every shard's.

**1.4 Dispatch.** The drain thread copies nothing: the collector's buffer is valid until
`gpu_data_analysis` returns, and that function joins the sharded pass before returning (an RAII
guard on every return path). A router thread walks the drain in record order (T15's late order if
given) and appends, per shard, entries `flags | position << 32 | own lane mask` — each 32,768-record
chunk is published as soon as it is routed, and the shards consume chunk by chunk, so a drain costs
about max(routing, slowest shard) and runs beside the PCDepGraph pass on the drain thread. The
position is the record's drain position (`seq`), carried in every entry; each shard sees its
records in that order.

**1.5 Kernel end.** The singleton HbClock, which processes no record in sharded mode, receives the
shards' results (merge rules, §2) and emits exactly as the serial pass does.

**1.6 Serial path.** `process()` now calls `process_one<ROLE_SERIAL>(record, 0)`; the role-specific
lines are `if constexpr` branches compiled out of that instantiation, the one new store in the
serial path is `SyncPair::first_seq` (written when a pair's first conflict is found; the serial
emit does not print it). `stats()` sums its bucket and sync-clock sections over a list of parts,
which is `{this}` in the serial pass (same output).

**1.7 Deviations from the brief, with the reason.**
1. *Dispatcher.* A router thread with chunked publication instead of the drain thread with
   per-shard FIFO queues of copied records: routing on the drain thread added 3.6–6.1 s per
   heartwall kernel in series with the shards (§5.1); the buffer is read in place, so the queues
   hold 8-byte entries, not records.
2. *R3 points and the monitor* are not per location; the brief's per-shard state (clocks,
   assembly, shadow slice) does not produce them. A first build gave them to one extra "control"
   HbClock that saw every record: at N=8 it was busy 24 s per heartwall kernel and 23 s per knn
   kernel, a floor above the shards at N ≥ 16 (§5.1). They are now distributed by block / warp
   chunk (§1.3).
3. *cp.async copies* go to every shard (their issue is a clock operation); the brief lists only
   arrivals and exits. The proof remark says the same (§7).
4. *`hb_stats`* differs from the serial pass by design: sums over the shards plus a `sharded` block
   (§2). It is diagnostic; no verdict reads it.

## 2. Merge rules per field

The aggregates scalar-clock mode writes (`python/test_no_dump.py::test_dump_carries_the_aggregates`
and `kernel_trace_flush`):

| field | produced by | merge rule |
|---|---|---|
| `hb_sync_pass` `[pc_lo, pc_hi, count, dist, first_pc, second_pc]` | the shards owning the conflicting records' location | per `(pc_lo, pc_hi)`: `count` summed; `dist` max; `(first_pc, second_pc)` from the shard whose first conflict on the pair was found at the smallest record position (`first_seq`). Conflicts found at one record on one pair all have the same pcs (the record's own pc and the pair's other one), so a tie cannot change them. Emitted in key order, as before. |
| `hb_rmw_points` `{release: {pc: [rmw pcs]}, acquire: {…}}` | the shard keeping each warp chunk's points | after each shard's `rmw_finish()`: per pc, `rel` and `acq` sets unioned, `stranded` and `orphan` OR-ed (each is a union over threads, and every thread's lanes went to one shard); emitted sorted, as before. |
| `tv_violation` (first violation) | the shard monitoring the record's block | the shard whose first violation is at the smallest record position; then `TV-barrier-pending-at-end`, from shard 0's assembly state (every shard's is the same), appended only if no record-time violation exists — the serial order. |
| `hb_events_count`, `hb_lanes_count`, `hb_aggregates`, `hb_async`, `hb_exits` | drain thread (unchanged) | — |
| `hb_stats.hb_clock` (HB_STATS only) | all | buckets and sync clocks summed over the shards (`vs.threads` = max), the rest the singleton's; plus `sharded`: `shards`, `drain_s`, `route_s`, `wait_s`, `bcast`, `rmw_bits`, per shard `busy_s`, `stall_s`, `lanes`, `tv_records`, `rmw_lanes`. |

## 3. Verification A — the green set (tested)

`setup/t22_check.sh`, job 312955 (c28, final build), the merge-check protocol: (0) the default tool
path; (1a) the CLAUDE.md A4 files + `test_instance_gate.py`; (1b) `test_instance_gate.py` alone on
the fresh artifacts (the ScoR-parametrised gate tests); (1c) `test_no_dump.py`; every trace
re-recorded, the knob exported for the whole pytest run (vector-clock recordings ignore it).

| configuration | (1a) | (1b) | (1c) |
|---|---|---|---|
| `YOSEMITE_HB_SHARDS` unset (serial) | **312 passed, 2 skipped** | **55 passed** | **31 passed** |
| `YOSEMITE_HB_SHARDS=8`, `YOSEMITE_HB_SHARD_INLINE_MAX=0` (every drain through the threads) | **312 passed, 2 skipped** | **55 passed** | **31 passed** |
| `YOSEMITE_HB_SHARDS=8` (default inline threshold) | **312 passed, 2 skipped** | **55 passed** | **31 passed** |

These are X0's merge-check counts (`eval/AGGREGATES_DEFAULT.md`: 312 + 2 skipped, 55/55, 31/31).
(0) Default path (no `YOSEMITE_HB_TRACE`), `race_interblock_none-lock_rtraw` and
`norace_interblock_atom`: installed runtime vs this one identical, and two runs of this one byte for
byte (`t20_default_compare.py`: ALL IDENTICAL; `kernel_pc` 0).

That the scalar-clock recordings of the sharded configurations ran sharded: the green set's
pytest temp dirs are node-local, so `setup/t22_confirm.sh` (job 313074) re-ran `test_no_dump.py` with
`YOSEMITE_HB_SHARDS=8 YOSEMITE_HB_SHARD_INLINE_MAX=0` and the temp dirs kept: 31 passed; of its 8
recordings' accelprof logs, the 4 scalar-clock ones contain `scalar-clock pass sharded by location:
8 shards` and the 4 vector-clock ones `YOSEMITE_HB_SHARDS=8 ignored: vector-clock mode runs the serial
pass`.

## 4. Verification B — parity within one run, and across shard counts

**B1. Sharded aggregates == the replay of the same run's records** (proved-in-effect; the T20
method, `eval/THREAD_INDEX.md` §2). The 65 T20 parity ids (`setup/t5b_parity_ids.txt`) recorded in
scalar-clock mode with the dump on, `YOSEMITE_HB_SHARDS=8` (default inline threshold, so small
drains took the inline path and large ones the threads), `HB_STATS`, the 120 s floor, one rep
(job 312952, c28; store `cuvein_traces/t22-parity-b`, 33 GB; rows `eval/results/t22-parity-b/`):
37 CLEAN, 25 RACE, 3 TIMEOUT (P6 interkernel WW racy, P7 particlefilter, P7 bfs — the same three
scalar-clock TIMEOUTs as T20's parity recording; T20's fourth, P9 overlap, finished here), 0
ERROR. Then `t4_parity.py compare` with the lane cutoff lifted (`CUVEIN_BARRIER_PASS_MAX_LANES=10**12`),
32 comparer processes in one job (312953, `setup/t22_parity_cmp.sh`, cap 7,200 s per program):
for every kernel JSON, `hb_sync_pass == barrier_only_pairs(records)` (pairs, distance, order),
`hb_rmw_points == trace_rmw_points(records)`, and `analyze()` from the aggregates (X0's default)
== `analyze()` under `CUVEIN_PREFER_RECORDS=1` on every verdict field, `skipped_edges` and the
event-candidate diagnostics.

| programs | kernel JSONs | equal | MISMATCH | above the 5 M-lane cutoff |
|---|---|---|---|---|
| **62** (the 3 TIMEOUTs left no dump) | **477** | **477** | **0** | 52 (crs-cuda 26, overlap 20, backprop 2, 1dconv-norace-large 1, matrix-multiplication-norace-small 1, hostdevice WW fixed 1, interkernel RW racy 1) |

Table per program: `setup/t22_parity/t22-parity-b/table.md`.
Every one of the store's 496 scalar-clock kernel JSONs (the 477 above plus the TIMEOUTs' partial
dumps) carries `hb_stats.hb_clock.sharded` with `shards: 8` (`setup/t22_inspect.py shards`, job 313068).

**B2. The same trace at N = 1, 2, 8, 32** (proved-in-effect on these kernels). A GPU re-recording is
another execution (warp interleavings differ run to run), so the cross-N comparison replays one
recorded trace through the runtime without a GPU: `setup/t22_replay/pack.py` turns a kernel JSON's
`hb_events` into the `MemoryAccess` records HbClock reads (type, block, warp, pc, active mask,
`accessSize`, flags, lane addresses; an `atomic` event gets the ATOMIC flag alone, as the offline
pass reads an atomic the sidecar does not list as a read), `replay.cpp` feeds them through
libsanalyzer's `yosemite_kernel_start / gpu_data_analysis / kernel_end` in drains of 262,144
records, and `cmp.py` compares `hb_sync_pass` (sorted), `hb_rmw_points`, `tv_violation`,
`hb_events_count`, `hb_lanes_count` with the recording's own. Every drain threaded
(`YOSEMITE_HB_SHARD_INLINE_MAX=0`). Job 312954 (`setup/t22_replay/crossn.sh`); kernels picked by
`pick.py` (non-empty `hb_sync_pass`, the largest, one per program):

| kernel (store t22-parity-b) | records | pairs / R3 pcs | N=1 | N=2 | N=8 | N=32 |
|---|---|---|---|---|---|---|
| P4-matrix-multiplication-norace-small k0 | 189,441 | 4 / 11 | equal | equal | equal | equal |
| PI-push_node_neighbors_boundsBug_reverse_atomicBug-counterDAG_200n_1000e k0 | 159,159 | 50 / 22 | equal | equal | equal | equal |
| P1-CC_CUDA_V_Topo_Pull_Determ_…-slower_atomic-1296n k2 | 122,844 | 3 / 8 | equal | equal | equal | equal |

Replay times of these kernels (one host thread for PCDepGraph, CPU only, c28): 0.58 / 0.34 / 0.33 /
0.34 s, 6.18 / 3.37 / 2.08 / 1.37 s, 2.62 / 1.37 / 0.55 / 0.33 s at N = 1 / 2 / 8 / 32.

The same check on the smoke store (4 programs recorded at N=8 with the first build; jobs 312860 and
312918 with the later builds): P4-1dconv-racy-small k1 (1 pair), P7-backprop k0 (970,752 records,
12.6 M lanes) and k1 — equal at N = 1, 2, 8, 32 on every build.

**B3. Synthetic traces** (tested; what the recorded corpus rarely exercises). `setup/t22_replay/synth.py`
writes traces of kernel `synth` with an rmw sidecar: five trace-validity cases — two violations
in two blocks in either position order (`TV-record-after-exit`: exit twice, and a read after an
exit), a completion-order violation with pending segments, pending segments only
(`TV-barrier-pending-at-end`), a counted-barrier overfill — and random traces (7 blocks × 4 warps,
5 barrier phases, syncwarps, early exits that complete a block's open barrier, 10 % RMWs on a 4-word
pool, 40 % shared, half the lanes scattered over 64 global words or 96 shared words). Each is replayed
at N=1 (the reference, the serial pass) and at N = 2, 8, 32, threaded and inline
(`setup/t22_replay/synth_run.sh`, login node): **105 traces (5 + 100 random seeds) × 6 configurations,
0 differences** on build `d9c16d82` (and 25 × 6 on `718fb158`). The random traces carry 209–250
sync pairs and 20 R3 pcs each; the TV cases' `tv_violation` strings are reproduced exactly,
including which of two violations is first. A second generation adds cp.async copies (8 % of the
non-RMW accesses: shared writes at an `# async` pc, a commit after 60 % of them, `wait_group 0` or
`1` before 70 % of the barrier arrivals): again **105 × 6, 0 differences**; e.g. seeds 0/1/2 carry
268/265/266 pairs, 19/19/16 of them on the copy's pc.

## 5. Performance

### 5.1 Design diagnostics (c28, 900 s cap, not step C)

Before step C, short same-node runs (`setup/t22_diag.sh`: the harness, scalar-clock mode, no dump,
`HB_STATS`, one rep, 900 s cap; partial dumps kept) decided the design. "Period" = the median
interval between consecutive completions of the program's big kernel (kernel JSON mtimes; heartwall:
one 78.4 M-record kernel per frame; knn: one iteration = a 11.6 M-, a 9 K- and a 99.9 M-record
kernel). Per-kernel times are `hb_stats.hb_clock.sharded` of the big kernel: `drain` = the drain
thread's time in `gpu_data_analysis`, `route` = routing, `wait` = the drain thread's wait for the
shards after its PCDepGraph pass (so PCDepGraph ≈ drain − wait), `busy` = the shards' range.
Summary: `setup/t22_diag_summary.txt`; logs `build_logs/t22-diag{,2,3}-*.log`.

| program | build | N | period | kernels in 900 s | big kernel: drain / route / wait / shards busy | peak RSS (harness) |
|---|---|---|---|---|---|---|
| heartwall | (serial) | 1 | **376 s** (360, 376) | 3 | — | 6,114 MB |
| heartwall | first (`48f1ff7`) | 8 | 46 s | 20 | — / 3.6 / 22.8 / 35.1–37.3, control 24.0 | 6,175 MB |
| heartwall | router (`3cf25a1`) | 8 | 53 s | 18 | 49.0 / 6.1 / 33.5 / 38.5–42.0 | 6,205 MB |
| heartwall | router (`3cf25a1`) | 16 | 33 s | 28 | 29.1 / 6.0 / 13.3 / 18.7–22.1 | 6,249 MB |
| heartwall | **final** (`b6a615e`) | 8 | 49 s | 19 | 44.6 / 6.2 / 29.0 / 40.4–43.4 | 6,237 MB |
| heartwall | **final** | 16 | **27 s** | 34 | 23.1 / 6.3 / 7.1 / 18.8–21.4 | 6,302 MB |
| heartwall | **final** | 32 | **20 s** | 40 | (one kept kernel JSON unreadable, see below) | 6,364 MB |
| knn | (serial) | 1 | **378 s** | 6 | — | 20,034 MB |
| knn | first | 8 | 66 s | 39 | 48.8 / 2.5 / 27.8 / 43.5–44.7, control 22.9 | 24,895 MB |
| knn | **final** | 16 | **49 s** | 40 | 31.0 / 7.4 / 10.6 / 27.4–28.0 | 30,343 MB |

Readings. (1) Heartwall has almost no replicated work (14,688 arrival/exit records per 78.4 M-record
kernel); knn's big kernel 5.77 M of 99.9 M. Shards' busy time halves from N=8 to N=16 in both: the
work divides. (2) In the first design the control thread (24 s / kernel) was a floor at N ≥ 16, and
routing on the drain thread added in series; the router thread alone did not help (routing then
preceded the shards: drain ≈ route + shards); chunked routing did (drain ≈ shards). (3) At N=8 the
final build is slower than the first (49 vs 46 s on heartwall): the shards now carry the monitor
and R3 points that the first design ran on a ninth thread. (4) Same-node speedups of the big-kernel
period, final build: heartwall 7.7× (N=8), 13.9× (N=16), 18.8× (N=32); knn 7.7× (N=16). (5) Floor:
PCDepGraph on the drain thread ≈ drain − wait = 16 s (heartwall) / 20 s (knn) per big kernel,
plus the collector's time outside the drains.

The N=32 heartwall run's kept partial dump contains one kernel JSON that does not parse
(`JSONDecodeError … char 958932`): it is `kernel_46.json`, the run's last kernel, 958,932 bytes ending
inside `hb_rmw_points` without the closing brace — the 900 s kill landed while it was being written
(`t22_inspect.py unreadable`, job 313068). The N=16 run has no such file.

{{C}}

## 6. Memory

The brief expected no change in total memory. Measured: the buckets do not change — they are
partitioned, and their sum over the shards equals the serial pass's (knn's 99.9 M-record kernel:
17.41 GiB and 729,808,896 entries at N = 1, 8, 16; heartwall's: 5.02 GiB, 205,357,670 entries at
N = 1, 8, 16) — but **every shard keeps every thread's sync clock** (the brief's design: its own
per-thread epoch array and barrier assembly), so that term is multiplied by N. `HB_STATS` of the
first big kernel (`t22_inspect.py mem`, job 313068; c28, the §5.1 runs):

| program | N | threads | sync clocks (`vs.bytes_est`, summed over shards) | buckets | RSS at kernel end | harness peak (summed VmRSS) |
|---|---|---|---|---|---|---|
| knn | 1 | 16,777,216 | 0.63 GiB | 17.41 GiB | 19.43 GiB | 20,034 MB |
| knn | 8 | 16,777,216 | 5.05 GiB | 17.41 GiB | 24.24 GiB | 24,895 MB |
| knn | 16 | 16,777,216 | 10.09 GiB | 17.41 GiB | 29.57 GiB | 30,343 MB |
| heartwall | 1 | 13,056 | < 0.01 GiB | 5.02 GiB | 5.96 GiB | 6,114 MB |
| heartwall | 8 | 13,056 | < 0.01 GiB | 5.02 GiB | 6.05 GiB | 6,237 MB |
| heartwall | 16 | 13,056 | 0.01 GiB | 5.02 GiB | 6.09 GiB | 6,302 MB |

So the extra memory is (N − 1) × the serial pass's sync-clock state (≈ 40 B per thread of the grid:
T20's dense 24-byte `SyncClock` pages plus one 16-byte base entry per thread), plus the routing
entries of one drain in flight (8 bytes per record per shard it reaches; the broadcast records reach
all N). It is small for grids of thousands of threads (heartwall) and grows with the grid (knn:
+0.63 GiB per shard). Larger grids (pathfinder: 100 M threads) were not measured here. The R3 points' per-thread state is not replicated (each warp
chunk's in one shard), and the monitor's state is per block in one shard.

{{D}}

## 9. What remains unverified

- **Assumed:** the drain buffer stays valid and unchanged until `gpu_data_analysis` returns (the
  collector refills it only after the call: `nv-compute/src/compute_sanitizer.cpp`, the pc_dependency
  drain loop); the sharded pass reads it in place and joins before returning.
- The sharded pass under T15's late key (`YOSEMITE_HB_LATE_SEQ`, a separate fatbin, off by
  default): the order array is copied and honoured in routing, but no run used it.
- cp.async copies: covered by two recorded programs of B1 (P6 memcpy global RW fixed and shared WW
  racy: one LDGSTS pc each, 1 / 2 commit and wait records; `setup/t22_async_check.sh`, job 313080)
  and by the synthetic traces (B3). `test_cp_async.py` records in vector-clock mode only (its
  scalar-clock view is derived offline), so the green set does not exercise the sharded copy path.
- Hosts: every GPU run is on c28 (Turin, 128 hardware threads in the job); the rtx4060ti16g hosts
  (16 cores) were allocated. {{HOSTNOTE}}
- `hb_stats` of a sharded run is a sum, not the serial pass's numbers (by design, §2).
- The proof remark (§7) is checked by Jeffery, not by a second reader here.

## 10. Commands

```
# private runtime (GPU-partition node: the collector relink needs /usr/local/cuda/compute-sanitizer)
sbatch -p rtx4060ti8g -w c28 -o <W>/eval/baselines/setup/build_logs/t22-build-%j.log eval/baselines/setup/t22_build.sh
# A: default path + green set at N=1, N=8 threaded, N=8
sbatch -p rtx4060ti8g -w c28 -o <log> eval/baselines/setup/t22_check.sh
BASETEMP=<dir> sbatch -p rtx4060ti8g -w c28 -o <log> eval/baselines/setup/t22_confirm.sh
# B1: record, then compare (32 comparers)
sbatch -p rtx4060ti8g -w c28 --array=0 --time=12:00:00 --export=ALL,W=<W>,TAG=t22-parity-b,\
  IDS=eval/baselines/setup/t5b_parity_ids.txt,BASELINE_MODES=scalar-clock,FLOOR=120,YOSEMITE_HB_SHARDS=8,\
  YOSEMITE_HB_STATS=1 -o <log> eval/baselines/setup/p_t5b_timeout.sh
sbatch -p rtx4060ti8g -w c28 --export=ALL,TAG=t22-parity-b,PAR=32,CAP=7200 -o <log> eval/baselines/setup/t22_parity_cmp.sh
# B2: cross-N replay; B3: synthetic traces (login node)
sbatch -p rtx4060ti8g -w c28 --export=ALL,STORE=/mnt/beegfs/$USER/cuvein_traces/t22-parity-b,NPICK=3,\
  NS="1 2 8 32",OUT=/mnt/beegfs/$USER/t22-replay-b -o <log> eval/baselines/setup/t22_replay/crossn.sh
OUT=<dir> SEEDS=100 bash eval/baselines/setup/t22_replay/synth_run.sh
# 5.1 diagnostics; inspections
sbatch -p rtx4060ti8g -w c28 --export=ALL,RUNS="P7-heartwall-cuda:16 P7-heartwall-cuda:32 P9-knn-cuda:16 \
  P7-heartwall-cuda:8",CAP=900,TAG=t22-diag3 -o <log> eval/baselines/setup/t22_diag.sh
.env/bin/python eval/baselines/setup/t22_diag_summary.py <diag logs>
sbatch -p rtx4060ti8g -w c28 -o <log> eval/baselines/setup/t22_inspect.sh
{{CCMD}}
```
