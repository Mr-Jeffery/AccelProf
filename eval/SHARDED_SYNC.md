# T22 — the sharded scalar-clock sync pass

Branch `perf/sharded-sync-pass` from `cuVein` 4094187 (X0 merged). Unmerged and uninstalled (the
merge and install are Jeffery's). Freeze exception of the brief: only HbClock's sync pass under
`sanalyzer/` changed — not vector-clock mode's clock, not `nv-compute/`, not `python/hb_oracle.py`,
not the PCDepGraph worker pool (`-n 1` stays). Written 2026-10-15/16. Facts only; legend:
**proved-in-effect** = an invariant checked over the stated traces; **tested** = a specific result
asserted by a test; **assumed/unverified** = said so.

**Summary for Jeffery.** At N = 32 on c28 (128 cores), scalar-clock heartwall finishes in 2,015 s
against X1's 32,057 s (15.9×, cross-host; 18.8× per big kernel on the same node) and knn in
4,361 s against 44,762 s (10.3×, cross-host), parity 477/477 kernel JSONs, controls unchanged.
Of X1's partial scalar-clock rows, expdist now finishes (RACE 22, 3,388 s); particlefilter is
still partial (OOM after 3 kernels, on a 755 GB node); **stencil1d and atomicCAS are still
running** at the time of this report (§7) and their rows are filled when the jobs end.

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
   arrivals and exits. The proof remark says the same (§8).
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

### 2.1 Who reads the per-pair instance counts

The merge sums `count` (the third element of `hb_races_sync_only` rows and of `hb_sync_pass`
rows). Whether anything but display depends on that number — read from the code at `cuVein`
4094187 (no `python/` or `eval/` change on this branch touches these readers):

- **`python/sync_dominance.py` (`analyze`)** — `hb_races_sync_only` is reduced to the set of its pc
  pairs, `sync_pcsets = {frozenset((a, b)) for a, b, _ in sync_only}`: the count is dropped.
  `hb_sync_pass` goes through `aggregated_sync_pass()` into `(pairs, dist, order)`; `analyze`
  uses the keys (`sync_pcsets`, the barrier-ordered test of `_hb_class` and of the static-only
  path), `dist` (`observed_dyn`, the widest observed distance) and `order` (the orientation of an
  event-stream candidate). The count enters at exactly one place: an event-stream candidate is
  judged with `judge(cur, anc, dist, n, …)`, where `n` is the pass's count (or, in vector-clock
  mode, the summed `count` of its `hb_races` records), and `judge` writes that argument only into
  the verdict record's `contested_weight` field. `weight` is not passed to `eng.ordered()`,
  `_hb_class()`, `CLASS_VERDICT`, the benign tag or the lock-step relabel; edge-based verdicts take
  their `contested_weight` from the PCDepGraph edge's histogram, not from the pass.
- **`eval/baselines/make_tables.py`** — reads none of `hb_sync_pass`, `hb_races_sync_only` or
  `contested_weight` (no occurrence); its tables count programs and pc pairs.
- **`eval/LATENT_CENSUS.md` / `eval/baselines/latent_census.py`** — the script keeps
  `sync_count` (the `hb_races_sync_only` count of a verdict's pair) and prints it in the
  "barrier-pass conflicts" column of its generated latent-pair tables; nothing computes with it,
  and the report `eval/LATENT_CENSUS.md` neither shows nor uses it.
- Elsewhere the counts are compared, not used: `setup/t4_parity.py` (`contested_weight` is one
  field of its verdict key; the aggregates' counts are part of the equality check),
  `t5b_parity.py`, `t16_parity.py`, `nodump_spot_cmp.py`, `a2_window_count.py`.
- Not asked, for completeness: the vector-clock `hb_races[*].count` is read by `_a2_flag` (a pair is
  `a2_uncertain` iff its flagged instances reach the summed count), which feeds the
  `a2_uncertain=<k>:<m>` row note and `make_tables.py`'s informational A2 column — never a verdict
  or class. Scalar-clock mode writes no `hb_races`.

So no verdict, class or table cell depends on the sync-pass counts; they appear as
`contested_weight` of event-stream candidates and in the census script's display column.

### 2.2 Slots tested per access: bfs and nbody at the installed runtime (private build)

Requested 2026-10-16: on bfs at the current runtime (the T20 build), count the bucket slots
Check tests per access, beside `conflict()`, in a private build only (no commit); the same for
nbody's main kernel. **Build:** `git archive cuVein sanalyzer` (= the installed libsanalyzer's
source: `git diff ba99486 cuVein -- sanalyzer` is empty) into a scratch directory outside the repo,
patched there only — in `HbClock::check()`: per kernel, `accesses` (Check calls, one per lane
access), `in_bucket` (the slots of the location's bucket when Check met one), `visited` (slots the
loop reaches after the whole-key-group skip: read meets read, or two RMWs whose scope makes them
morally strong), `tested` (`conflict()` calls: visited minus the accessor's own slot and morally
strong RMW pairs), the largest bucket Check met (its size, the access's pc, the location), and at
kernel end the largest bucket with its slots' pcs and keys; written into `hb_stats.hb_clock`.
libsanalyzer `5a0442ca409571d3`, collector relinked `bdd364de89a3b185`, installed fatbins; serial
pass (no sharding), scalar-clock mode, no dump, `HB_STATS`, c28. bfs full run, 5,400 s cap (job
313217: RACE, 31 reports, 842.8 s, 24 kernels — X1's row: RACE, 31, 1,507 s on c74); nbody 1,800 s
cap, which holds its first six launches (job 313218). Printout `setup/t22_slots.txt`
(`t22_inspect.py slots`). Keys: `kind << 3 | (scope + 1)` — 8 = weak write, 0 = weak read.

| program | kernel | name | records | accesses (lanes) | slots tested (`conflict()` calls) | tested / access | largest bucket met (slots) | access pc there | address | largest bucket at kernel end: slots, slot pcs |
|---|---|---|---|---|---|---|---|---|---|---|
| bfs | 0–23 even | `Kernel` (12 launches) | 62,525 – 1,881,112 | 1.0 – 11.3 M | 0 – 2,764,634 | ≤ 0.2 | ≤ 14 | various | various | ≤ 15, mixed reads |
| bfs | 1, 3, 5, 7 | `Kernel2` | 62,521 – 65,951 | ≈ 1.0 M | 3 / 276 / 8,911 / 318,801 | ≤ 0.3 | 2 / 23 / 133 / 798 | 0x160 | 0x7ff29b9e8800 (global) | +1, all pc 0x160, key 8 |
| bfs | 9 | `Kernel2` | 81,116 | 1,018,284 | 10,444,735 | 10.3 | 4,570 | 0x160 | 0x7ff29b9e8800 | 4,571, all 0x160 |
| bfs | 11 | `Kernel2` | 142,441 | 1,101,708 | 323,253,451 | 293.4 | 25,426 | 0x160 | 0x7ff29b9e8800 | 25,427, all 0x160 |
| bfs | **13** | `Kernel2` | 215,886 | 1,525,044 | **8,614,659,430** | **5,648.8** | **131,260** | 0x160 | 0x7ff29b9e8800 | 131,261, all 0x160 |
| bfs | **15** | `Kernel2` | 218,756 | 2,803,400 | **101,632,635,825** | **36,253.3** | **450,849** | 0x160 | 0x7ff29b9e8800 | 450,850, all 0x160 |
| bfs | **17** | `Kernel2` | 218,751 | 2,478,512 | **68,312,244,378** | **27,561.8** | **369,627** | 0x160 | 0x7ff29b9e8800 | 369,628, all 0x160 |
| bfs | 19, 21, 23 | `Kernel2` | 124,721 / 62,646 / 62,506 | ≈ 1.0 M | 149,169,628 / 406 / 0 | 139.5 / 0.0 / 0.0 | 17,272 / 28 / 0 | 0x160 | 0x7ff29b9e8800 | 17,273 / 29 / 1 |
| bfs | **all 24** | | 7,436,165 | 48,792,045 | **179,046,138,430** | **3,669.6** | | | | |
| nbody | 0, 3 | `accelerate_particles` | 32,005,004 each | 1,024,144,000 each | **0** (48,000 visited) | **0.0** | 16,000 | 0x230 | 0x7fc27b036ad8 | 16,000, all pc 0x290, key 0 (at 0x7fc27b01c88c) |
| nbody | 1, 4 | `update_particles` | 10,504 | 320,000 | 0 (144,000 visited) | 0.0 | 1 | 0x200 | 0x7fc27b04f600 | 2 |
| nbody | 2, 5 | `accumulate_energy` | 20,004 | 20,003 | 0 (8,004 visited) | 0.0 | 2 | 0x2f0 | 0x7fc27b09c400 | 2 |

Full per-kernel rows (incl. slots in the buckets met and visited): `setup/t22_slots.txt`.
The hot pcs, from `nvdisasm -c -g` of the cubins extracted from the two binaries
(`eval/baselines/bin/P7/{bfs,nbody}-cuda`, on c58): bfs `Kernel2` +0x160 is `STG.E.U8 [R2.64], R0`
at `HeCBench/src/bfs-cuda/bfs.cu:59`, `*d_over=1;`; nbody `accelerate_particles` +0x230 and +0x290
are `LDG.E R33, [R4.64+0x78]` and `LDG.E R12, [R4.64+0x4c]` at
`HeCBench/src/nbody-cuda/GSimulationKernels.hpp:16`, `auto pj = p[j];` (every thread loads every
particle, n = 16,000). (A first attempt, job 313254, printed no instruction: its function-name
lookup failed; the lines above were taken by hand from the full listing.)

Reading. **bfs:** of the 179,046,138,430 slots tested, `Kernel2` holds 179,042,735,844 (99.998 %)
and its launches 13, 15, 17 alone 178,559,539,633 (99.73 %); the largest bucket of every `Kernel2`
launch is the same global location, `0x7ff29b9e8800`, holding one weak-write slot per thread that
has written it at pc 0x160 — it grows by one slot per writing thread (end size = largest met + 1) to
450,850 slots in launch 15, and a write there tests every other writer's slot: 36,253 slots per access
averaged over all of launch 15's accesses. This is X1-follow §2's `*d_over = 1` (`bfs.cu:59`, one byte
written by every frontier thread), which T4 put on the scalar-clock path. The `Kernel` launches test
≤ 0.2 slots per access. **nbody:** `accelerate_particles` tests **no** slot: its accesses are reads,
the bucket they meet holds reads only (key 0), and Check skips the read–read key group whole —
8.19·10¹² slots sit in the buckets met (≈ 8,000 per access, 16,000 = one per thread at most) but only
48,000 are visited. nbody's time is therefore not the conflict test: X1-follow §3 places 80 % of it
in the bucket insertion (`merge_tail`), which this counter does not count.

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

### 5.2 Step C — heartwall and knn, X1 inputs, full runs

Released by Jeffery on 2026-10-16 (X1-follow's bisect: scalar-clock mode flat through T15, its only
crossing at T4 — the first online sync pass, not a regression — and the vector-clock culprit at T9
cannot change the scalar-clock N=1 baseline). `setup/t22_perf.sh`: the harness, scalar-clock mode,
no dump, `HB_STATS`, one rep, cap = floor = 86,400 s (X1's 24 h pass), c28. N=1 is X1's own 24 h
row (not repeated: it is 9–12 h per program; the same-node N=1 per-kernel time is §5.1's). "Peak" is
the harness's peak of summed VmRSS (X1's column).

| program | N | host | tool wall | native | events | µs / event | peak (MB) | verdict | vs X1 N=1 |
|---|---|---|---|---|---|---|---|---|---|
| heartwall | 1 (X1, final-24h-sc) | c52 (EPYC 9115) | 32,057.2 s | 0.778 s | 8,071,484,636 | 3.972 | 6,186 | RACE, 2 | — |
| heartwall | **32** | c28 (EPYC 9745) | **2,014.8 s** | 0.820 s | 8,071,484,636 | **0.250** | 6,390 | RACE, 2 | 15.9× (cross-host) |
| heartwall | 8 | c28 | 4,951.4 s | 0.870 s | 8,071,484,636 | 0.613 | 6,319 | RACE, 2 | 6.5× (cross-host) |
| knn | 1 (X1, final-24h-sc) | c66 (EPYC 8124P) | 44,762.4 s | 13.744 s | 11,144,912,500 | 4.016 | 20,558 | CLEAN | — |
| knn | **32** | c28 | **4,361.4 s** | 6.427 s | 11,144,912,500 | **0.391** | 41,537 | CLEAN | 10.3× (cross-host) |
| knn | 8 | c28 | 6,758.6 s | 6.582 s | 11,144,912,500 | 0.606 | 24,960 | CLEAN | 6.6× (cross-host) |

Same events and same verdicts as X1's rows (heartwall 104 kernels, knn 300). Cross-host caveat: the
same-node per-kernel ratios of §5.1 (heartwall 376 → 20 s per big kernel at N=32, 18.8×; knn 378 → 49 s
per iteration at N=16) are the like-for-like numbers; the walls above compare c28 with X1's hosts.
X1-follow's collector-only runs (`YOSEMITE_HB_TRACE` unset, `-n 1`, c66/c61, EPYC 8124P) took 2,345 s
(heartwall) and 3,304 s (knn) — the collector plus the single-worker PCDepGraph pass, a floor the
sharded pass cannot go below on those hosts.

**Controls** (two short programs from X1's 4–5× band; 3 reps each at N = 1, 8, 32, cap 1,200 s,
c28, job 313143): no regression at N > 1.

| program | events | N=1 walls (s) | N=8 | N=32 | verdict (all reps) | peak (MB), N=1 / 8 / 32 |
|---|---|---|---|---|---|---|
| P5-norace_interblock_atom (X1: 4.9×) | 4 | 3.673, 0.768, 0.819 | 0.868, 0.818, 0.718 | 1.119, 0.718, 0.768 | CLEAN | 791–845 / 673–843 / 789–845 |
| P1-CC_CUDA_V_Topo_Push_…_Warp_…-slower_atomic-1296n (X1: 4.9×) | 93,477 / 85,410 / 93,828 | 1.168, 1.118, 1.068 | 1.069, 1.269, 1.118 | 1.068, 1.169, 1.068 | RACE, 4 | 847–851 / 863–867 / 923–927 |

Medians: 0.819 / 0.818 / 0.768 s and 1.118 / 1.118 / 1.068 s. (The 3.673 s first rep at N=1 is
the first launch after the build; it is not repeated.) The P1 program's event count differs run
to run (atomics-driven worklist), not with N. Native 0.217 s for both.

**Choice of N.** On c28 (128 cores) N=32 is the fastest measured on both programs (heartwall per
big kernel: 49 / 27 / 20 s at N = 8 / 16 / 32, §5.1; full runs 4,951 vs 2,015 s; knn 6,759 vs
4,361 s), so step D uses N=32. On a 16-core rtx4060ti16g host the shards would share 16 cores with the
router, the PCDepGraph worker and the collector's threads; no run there was possible (§0).

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

## 7. Step D — the X1 partial rows, scalar-clock mode, N = 32

Released by Jeffery on 2026-10-16 for every partial row except bfs and nbody. X1's scalar-clock rows
that are partial at their last cap (`final-24h-sc`, with X1-follow's `partial:` notes): particlefilter,
stencil1d, expdist, atomicCAS. State at 2026-10-16 18:41: expdist and particlefilter done,
stencil1d running, atomicCAS queued behind it. The other rows the brief named are finished in scalar-clock mode in
X1 and were not re-recorded ("do not re-record finished rows"): heartwall (RACE, 32,057 s) and knn
(CLEAN, 44,762 s) — run in full in step C anyway; tridiagonal (RACE, 36,768 s); pathfinder (RACE,
19,225 s); bfs (RACE, 1,507 s at the 5,400 s pass) and nbody (CLEAN, 8,015 s), which are also gated.
**Cap:** c28 is admitted only by `rtx4060ti8g` (1-day job limit; `all` and `qc` refuse the submission,
`max` does not contain c28), so the tool cap is 84,600 s, 1,800 s under X1's 86,400 s, to leave the
harness's native runs, sidecar and analysis inside one job — a shorter cap can only make a row
harder to finish. `setup/t22_perf.sh`, harness, no dump, `HB_STATS`, one rep.

| program | X1 N=1 (final-24h-sc) | T22 N=32 (c28) | note now |
|---|---|---|---|
| P9-expdist-cuda | TIMEOUT, 86,400 s, partial: 32 kernels; peak 9,912 MB (5,400 s pass: 0 kernels) | **RACE, 22 reports, 3,387.7 s, 40 kernels, 1,652,680,826 events (2.05 µs/event), peak 18,173 MB** | finished: the partial note goes |
| P7-particlefilter-cuda | RACE, 31 (partial: OOM after 3 kernels, 5,791 s, peak 186,169 MB on c66, a 188 GB host) | RACE, 31 (partial(rc=1): **OOM after 3 kernels, 915.0 s, peak 757,785 MB** on c28, 755 GB) | still partial: "partial: OOM after 3 of ? kernels, 915 s, cap=84600" |
| P7-stencil1d-cuda | TIMEOUT, 86,400 s, partial: 147 kernels; peak 84,061 MB | **running** (job 313229, started 2026-10-16 07:59; 223 of 1,000 kernels at 10.7 h, ≈ 172 s per kernel; the 84,600 s cap ends ≈ 07:30 on 10-17) | pending; at this rate ≈ 490 kernels by the cap, so expected still partial (X1: 147) |
| P9-atomicCAS-cuda | TIMEOUT, 86,400 s, partial: 60,000 kernels; peak 908 MB | **queued** (job 313230, chained after stencil1d; ends by ≈ 08:00 on 10-18 at the latest) | pending |

particlefilter: the run reached the same 3 completed kernels and the same 31 reports as X1's, and ran
out of memory in the 4th kernel on a node with four times the memory; the memory growth inside that
kernel cannot be attributed from these runs (no kernel-end statistics for an unfinished kernel, and
`YOSEMITE_HB_STATS_EVERY` is ignored with sharding — §1). It grew at ≈ 830 MB/s against X1's ≈ 32 MB/s;
whether the sharded pass holds more per record than the serial one there (allocator arenas of 32
threads, per-shard slot-array slack) is **not measured**.

## 8. Proof

`design/proof/hb_proof.tex`: one remark after Corollary "The sync instance", Remark "Partition by
location" (`\label{rem:partition}`): under M = sync the clocks and the assembly state are written only
at exits, barrier arrivals, syncwarps, commits, waits and copy issues; a memory record on ℓ reads the
clocks and B_ℓ and writes B_ℓ alone; so runs that each process every such record and the memory
records of one part of a partition of the locations compute, by induction on seq, the serial clocks
and the serial buckets of their part, and their reports union to Rep of the sync instance; the
per-pair aggregate is then the runs' sum, maximum and seq-earliest; it does not extend to M = vec
(an RMW joins Ch_ℓ into clk[t]). The document compiles (TeX Live 2026, `pdflatex` twice: 20 pages,
no undefined reference; the same font-shape warnings as the cuVein version, 19 pages). **For
Jeffery's check**; no other proof change.

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
  (16 cores) were allocated. Step C's and D's walls are c28's (EPYC 9745) against X1's N=1 rows on c52 (EPYC 9115) and c66 (EPYC 8124P): those ratios are cross-host; §5.1's same-node per-kernel ratios are like for like. N=16 on a 16-core host (the core-count case of the brief) was not run.
- Step D for stencil1d and atomicCAS: still running / queued at this report (§7); their verdicts,
  walls and peaks are not in it.
- `hb_stats` of a sharded run is a sum, not the serial pass's numbers (by design, §2).
- The proof remark (§8) is checked by Jeffery, not by a second reader here.

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
# C (c28, partition rtx4060ti8g, one job per pair; N=1 is X1's row)
sbatch -p rtx4060ti8g -w c28 --export=ALL,RUNS="P7-heartwall-cuda:32 P9-knn-cuda:32",CAP=86400,TAG=t22-perf \
  -o <log> eval/baselines/setup/t22_perf.sh          # and RUNS="P7-heartwall-cuda:8 P9-knn-cuda:8"
sbatch -p rtx4060ti8g -w c28 --export=ALL,RUNS="P5-norace_interblock_atom:1:3 …:8:3 …:32:3 <P1 id>:1:3 …",\
  CAP=1200,TAG=t22-ctl -o <log> eval/baselines/setup/t22_perf.sh
# D (one job per program, chained)
sbatch -p rtx4060ti8g -w c28 --time=1-00:00:00 --export=ALL,RUNS="P9-expdist-cuda:32",CAP=84600,TAG=t22-d \
  -o <log> eval/baselines/setup/t22_perf.sh          # particlefilter, stencil1d, atomicCAS likewise
# 2.2 (private counter build: an export of cuVein's sanalyzer/ patched outside the repo)
W=<scratch> sbatch -p rtx4060ti8g -w c28 eval/baselines/setup/t22_build.sh
W=<scratch> RUNS="P7-bfs-cuda:1" CAP=5400 TAG=t22-slot sbatch … eval/baselines/setup/t22_perf.sh   # nbody: CAP=1800
sbatch -p rtx4060ti8g -w c28 eval/baselines/setup/t22_slots.sh
```
