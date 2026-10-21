# T24 — a diverged WARPSYNC is one warp-barrier instance (DRAFT, in progress)

Branch `fix/syncwarp-instance` from `cuVein` 38af04e, worktree `/home/fzheng4/wt-t24`. Unmerged; the
runtime is not installed (a private build in `/home/fzheng4/stage-t24`, see §6). Nothing under
`nv-compute/` changes. Legend as in CLAUDE.md A4: **proved-in-effect** (an invariant checked over N real
traces), **tested** (a specific verdict asserted), **assumed/unverified**.

Status of this draft: steps 1–3 and 5 done; step 4 (parity) and step 6 (timing) running.

## 1. The test (step 1) — tested

- `python/testdata/syncwarp_diverged_waw.cu`: X5b's counterfactual as a kernel of its own. The shape of
  ECL-CC's `cc_vertex_data`: lane 0 clears `updated[warp]`, lane 16 sets it, every lane reads it after a
  `__syncwarp()`. The first `__syncwarp()` is removed; the remaining one sits inside a two-round loop
  (`lanes 0..15` in round 0, `16..31` in round 1, one call site), so the warp reaches it diverged.
- `python/testdata/syncwarp_converged_clean.cu`: the same with the first `__syncwarp()` put back
  (converged): the positive control.
- SASS on sm_89 (probe job 316786, c62): the `__syncwarp()` compiles to `BRA.CONV ~URZ` + `CALL.REL.NOINC`
  to the helper `WARPSYNC 0xffffffff` (0x2c0) + `NOP` (0x1c0), the shape X5b found in ECL-CC. Records per
  warp: syncwarp 0x2c0 active `0x0000ffff`, lane 16's set, syncwarp 0x2c0 active `0xffff0000`, syncwarp
  0x1c0 active `0xffffffff` (converged after the helper). **2 records per diverged instance in all 8
  warps.**
- `python/test_syncwarp.py`: 11 synthetic cases (oracle against `barrier_only_pairs`) and 10 GPU cases
  (both kernels, both modes).

| run | runtime | result |
|---|---|---|
| job 316788 (c63), 38af04e + the test | installed (libsanalyzer `a01c16667b592e5d`) | **11 failed**, 9 passed, 1 skipped — the WAW is reported in neither mode |
| job 316792 (c63), the fix | private (libsanalyzer `d8c5d656394f3e01`) | **20 passed, 1 skipped** |

The skip is by design (the specification is compared on the vector-clock recording).

## 2. The change (steps 2, 3)

Same assembly in the three implementations, in one commit (fe07ba5): `HbClock`
(`sanalyzer/src/tools/pc_dependency_analysis.cpp`: `pending_syncwarps`, `syncwarp_waiting`, `warp_lanes`,
`sw_expected`, `sw_fire`, `sw_complete`, `on_syncwarp`, `on_exit`, `check_pending_at_end`, `process_one`),
the specification (`python/hb_oracle.py`: `pending_sw`, `sw_waiting`, `on_syncwarp`, `sw_complete`) and the
record-replay reference (`python/sync_dominance.barrier_only_pairs`).

- **Instance.** An open entry per (block, warp, pc) accumulates `active_mask & sync_mask` of its records.
  It completes when the arrived lanes cover the **expected lanes** = `sync_mask` minus the warp's exited
  lanes (`exited_lanes`) minus the lanes past the block's last thread (a warp of a block whose size is not
  a multiple of 32: those lanes never run and have no exit record). On completion the expected lanes join
  (`sync_group`), the entry is erased, its lanes leave `syncwarp_waiting`. A new instance at the same key
  starts with the next record (a lane cannot reach instance k+1 before k completes).
- **Fast path.** No open entry and the record's active lanes already hold every expected lane: join at
  once (the code before T24 for a converged warp).
- **Exit.** After the block's barrier segments (unchanged order), each open instance of the exiting warp:
  the W2 check below, then the completion test with the new exited lanes. An exit of a lane that has not
  arrived can complete the instance, as for a block barrier.
- **Who joins.** The expected lanes, not every lane of `sync_mask`: a lane that exited before the instance
  completed is not a participant. Before T24 this case could not arise on a valid trace, because W3 read
  `sync_mask` (below).
- **W2 analogue, `TV-syncwarp-completion-order`** (strict only; HbClock records it, the oracle raises): a
  lane that has arrived at an open instance issues no record (memory, barrier, syncwarp, pipeline: checked
  before the record is dispatched) and does not exit before the instance completes. Per lane.
- **A3 analogue at runtime, `TV-syncwarp-pending-at-end`**: an instance still open at the end of the kernel.
  HbClock whatever the strict setting (as `TV-barrier-pending-at-end`); the oracle under strict and on dumps
  with `hb_exits`; `barrier_only_pairs` into `tv_out` on dumps with `hb_exits`.
- **W3 (`TV-record-after-exit`) — decision: it reads `active_mask` for a syncwarp record too.** Under the
  instance assembly `sync_mask` names the participants and `active_mask` the lanes that issue the record.
  A lane of `sync_mask` may exit while the instance is open (CUDA allows exited lanes in the mask; the
  hardware stops waiting for them), and the later groups' records still carry it in `sync_mask`. Reading
  `sync_mask` would flag that valid trace and would leave the "minus exited lanes" rule able to act only
  on exits that happen while an instance is open. The cost: an exited lane named in a mask is no longer a
  TV violation, so the join must exclude it — which the expected-lanes rule does.
- **Unchanged, deliberately:** the memory-record path; T12's `note_pc` and T14's `a2_close_lanes` (and the
  oracle's `close_lanes`) still treat a syncwarp record as the next record of every lane of `sync_mask`
  (§7); `design/algorithms_check.py` (not in the freeze exception) still implements the per-record join
  (§7).
- **Sharded scalar-clock pass.** Every synchronization record already goes to every shard, so every shard
  assembles the same instances (the open-instance map is maintained whatever a shard's TV flag says);
  the W2 check runs in the block's monitoring shard; `merge_into` copies shard 0's open instances to the
  emitter for the end-of-kernel check, as it does for `pending_barriers`.
- The green set gains `python/test_syncwarp.py` in `eval/baselines/setup/merge_check.sh`. CLAUDE.md A4's
  command list is not edited here (§7).

## 3. Parity (step 4)

### 3.1 The green set at N = 1, 8, 16 — tested

`eval/baselines/setup/t24_check.sh`, job 316793 (c62, RTX 4060 Ti sm_89, driver 580.82.07, 16 min), the
private runtime (collector `3dad1ffdad521833` -> libsanalyzer `d8c5d656394f3e01`), every trace re-recorded
per configuration (`ScoR/microbenchmarks/artifacts` and `cuHadron/_*` are private to the worktree, so no
other checkout's artifacts were wiped or read). (1a) = CLAUDE.md A4's seven files + `test_instance_gate.py`
+ `test_syncwarp.py`.

| configuration | (1a) green set | (1b) gate alone | (1c) `test_no_dump.py` | (1d) `test_sync_shapes.py` |
|---|---|---|---|---|
| `YOSEMITE_HB_SHARDS` unset (serial) | **341 passed, 3 skipped** | **58 passed** | **31 passed** | **4 passed** |
| `YOSEMITE_HB_SHARDS=8` | **341 passed, 3 skipped** | **58 passed** | **31 passed** | **4 passed** |
| `YOSEMITE_HB_SHARDS=16` | **341 passed, 3 skipped** | **58 passed** | **31 passed** | **4 passed** |

Against the 59a98aa install check (job 315525: 321 passed / 2 skipped, 58, 31, 4): +20 passed and +1
skipped, which are `test_syncwarp.py`'s 20 and its one by-design skip; the other two skips are the two
empty-parameter gate cases, as before. 0 failed, no xfail. (0) the default tool path (no
`YOSEMITE_HB_TRACE`), installed runtime vs this one and two runs of this one on two ScoR programs:
**ALL IDENTICAL** (`kernel_pc` 0).

The test kernel's drains are far below the sharded pass's inline threshold, so `test_syncwarp.py` was
also run with every drain through the shard threads: `SHARDS=16 INLINE=0 t24_test.sh`
(`YOSEMITE_HB_SHARDS=16 YOSEMITE_HB_SHARD_INLINE_MAX=0`), job 316806 (c63): **20 passed, 1 skipped**; the
tool's notices in the kept temp dirs: `scalar-clock pass sharded by location: 16 shards` for the two
scalar-clock recordings, `YOSEMITE_HB_SHARDS=16 ignored: vector-clock mode runs the serial pass` for the
two vector-clock ones.

### 3.2 The T20 parity set re-recorded with the dump

**Recording** (`STEP=rec t24_parity.sh` -> `p_t5b_timeout.sh`, job 316794, 8 shards on `rtx4060ti16g`
c3/c55/c56/c63/c64, all RTX 4060 Ti sm_89; 15:37–16:14): the 65 ids of `setup/t5b_parity_ids.txt`, both
modes, dump on, the 120 s floor, one rep, `YOSEMITE_HB_SHARDS=16` (scalar-clock; vector-clock runs the
serial pass), `YOSEMITE_HB_STATS=1`; store `cuvein_traces/t24-parity`, rows
`eval/results/t24-parity/`. Scalar-clock: 37 CLEAN, 26 RACE, 2 TIMEOUT (P6 interkernel-global_writewrite
racy, P7 particlefilter); vector-clock: 35 CLEAN, 26 RACE, 4 TIMEOUT (those two, P7 bfs, P9 crs); 0 ERROR.

**HbClock == specification** (`STEP=spec` -> `p_t5b_parity_cmp.sh` -> `t5b_parity.py compare`, job 316795,
8 shards on `normal`) — proved-in-effect: **61/61 programs with a vector-clock dump ok, 430 kernels, 0
mismatches**; the 4 vector-clock TIMEOUTs have no dump to compare.

**Aggregates == records** (`STEP=agg` -> `p_t4_parity_cmp.sh` -> `t4_parity.py compare`, cap 25,000 s,
job 316796): (running). This is T4's own parity protocol (NO_DUMP.md §3, run by T4 on this same 65-program
set, a superset of the brief's 20 programs).

**Rows against earlier recordings of the same ids** (different GPU executions, so schedule-dependent
counts can move): against T22 cont.'s `t22c-parity` (scalar-clock, N=8; 65 rows) one row differs,
`PI-populate_worklist_neighbors_persistent_atomicBug-counterDAG_200n_1000e` RACE 90 -> 91; against T20's
`t20-parity2` (130 rows) the same program (90 <-> 91 in both directions), P4 graph-coloring-racy-small
scalar-clock 13 -> 12 (T22 cont. saw the same 12), P7 bfs scalar-clock TIMEOUT -> RACE 31 (T22 cont.'s
Fix 2), P9 crs vector-clock CLEAN -> TIMEOUT and P9 overlap TIMEOUT -> CLEAN in both modes (the 120 s cap).
The populate_worklist program has no syncwarp record that T24 reads differently (§3.3), so its ±1 is the
schedule, not this change.

### 3.3 Where T24 can act in the parity store, and before/after on the same records — proved-in-effect

`t24_census.py` (job 316821, `normal`): 992 kernel JSONs (4 above 3 GB not read: P6
interkernel-global_writewrite and P7 particlefilter, both modes), 174,784 syncwarp records, 15,673 partial
ones, **7,525 diverged instances, 0 open at a kernel's end**, 150 records whose sync_mask names lanes
outside the expected set (P4 graph-connectivity-racy-small, 75 per mode). 20 (program, mode) dirs have
syncwarp records; 16 have a diverged instance or such a record: P3 CC ×3 programs, P4 graph-coloring-racy-
small, graph-connectivity-racy-small, reduction-norace-large, reduction-racy-large, reduction-racy-small
(both modes each). Every other kernel replays identically by construction (every syncwarp record takes the
fast path and joins its sync_mask, as before).

`t24_replay_store.py` over those 16 dirs (jobs 316823 and 316831; the first job's 8 processes ran a node
out of memory — one process killed, three stopped on a host-side dot without kernel clusters — and the 7
dirs they left were replayed by the second with 3 processes and the dot skipped): 168 kernel JSONs, each
replayed with 38af04e's oracle and `barrier_only_pairs` and with this tree's, the records as recorded:
**race pc pairs only after T24: 0, only before: 0** (oracle `races`, `races_sync_only`, and the offline
pass's pairs); **trace-validity violations: 0 before, 0 after** (strict; includes the two new checks).
38af04e's strict W3 accepted the 150 graph-connectivity records, so the lanes they name outside the
expected set are absent lanes (a partial last warp), not exited ones.

## 4. The 60 recordings of X5b §4 (step 4) — tested, 60 recordings

`eval/baselines/setup/t24_replay60.py`, job 316799 (c15, partition `normal`, 16 shard processes, 6.5 min;
`eval/x_logs/t24-replay60-316799*.log`, rows `eval/results/t24/replay60.jsonl`). Groups: X5b's
`eval/results/x5b/partial.jsonl` (b5e10b4) — the 60 (program, mode) recordings of the byte-pair rows in
`cuvein_traces/t16-certain` (sm_89, same dot md5 as X1). Every launch, the records as recorded, replayed
three times: 38af04e's oracle (extracted from git), this tree's oracle (strict; a TV message would be
recorded and the launch replayed with checks off), and 38af04e's oracle on X5b's merged records (each
completed partial instance one record at its completion). As X5b, the 1296-node programs replay without
their global records (memory; X5b checked the shared-only answer against the full replay on 104 rows).

| | count |
|---|---|
| recordings (program × mode) / launches | 60 / 680 |
| recordings with a diverged `WARPSYNC` | 24 |
| instances of 2 records / of 3 records / never completed | 72,160 / 1,734 / 0 |
| race pc pairs only after T24 (`races` + `races_sync_only`) | **0** |
| race pc pairs only before T24 | 0 |
| launches where this tree's oracle ≠ X5b's merged replay | **0** |
| trace-validity violations under strict, this tree (incl. `TV-syncwarp-completion-order`, `TV-syncwarp-pending-at-end`) | **0** |
| replay errors | 0 |

**No recording gained a report**, as X5b's merged replay predicted, and the new assembly gives exactly
X5b's merged construction on every launch. The W2 analogue holds on all 73,894 diverged instances (no lane
that has arrived issues a replayed record before its instance completes) and A3's runtime form holds (no
instance open at a kernel's end) — proved-in-effect over these 680 launches. Not covered: the 1296-node
programs' global records (shared-only replay: neither their pairs nor W2 on them).

## 5. Timing (step 6)

(pending)

## 6. The proof paragraph (step 5) — awaiting Jeffery's check

In `design/proof/hb_proof.tex` (Definition "Instances", the paragraph "Warp barriers (T24)", Algorithm 1's
syncwarp line).

## 7. What remains unverified

(to be completed)
