# T24 — a diverged WARPSYNC is one warp-barrier instance

Branch `fix/syncwarp-instance` from `cuVein` 38af04e, worktree `/home/fzheng4/wt-t24`, pushed to
`origin/fix/syncwarp-instance`; unmerged, nothing pushed to `cuVein`. The runtime is **not installed**:
a private build in `/home/fzheng4/stage-t24` (§8), `wt-t24/lib` points at it; no installed file was
written (the install hashes are unchanged in every build/check log). Nothing under `nv-compute/` changes.
Hardware: RTX 4060 Ti (sm_89), driver 580.82.07, CUDA 13.3. Legend as in CLAUDE.md A4:
**proved-in-effect** (an invariant checked over N real traces), **tested** (a specific verdict asserted),
**assumed/unverified**.

**Two lines for Jeffery.**
- **Parity:** green set 341 passed / 3 skipped at N = 1, 8 and 16 (gate 58, `test_no_dump.py` 31,
  `test_sync_shapes.py` 4, default path identical); HbClock == specification 61/61 programs (430 kernels),
  aggregates == records 906/906 kernel JSONs over 123 program × mode rows (counts-le), 0 mismatches;
  P7 bfs (scalar-clock) still being compared when this was written (§3.2).
- **The 60 recordings:** none gained (or lost) a report — 0 race pc pairs differ in 680 launches, and the
  new assembly equals X5b's merged replay on every launch (§4).

Steps: 1 (test, failing first) §1; 2–3 (the change) §2; 4 (parity, the 60 recordings) §3–4; 5 (proof
paragraph, awaiting Jeffery's check) §6; 6 (timing) §5.

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

**Aggregates == records** — T4's parity protocol (NO_DUMP.md §3, which T4 ran on this same 65-program
set, a superset of the brief's 20 programs), in the form T22 cont. uses since its Fix 2 (scalar-clock
counts and contested weights compared as aggregates <= records, everything else equal):
`STEP=agg-le t24_parity.sh` -> `t22_parity_cmp.sh LE=1` (`t4_parity.py compare --counts-le`, CAP 7,200 s per
program and mode, 12 processes), job 316864 (c12, `normal`), plus `STEP=agg-ids` jobs 317321 / 317322 for
the five programs two of its processes held behind a long one (four of them later also finished in job
316864; the table counts each program once: `shard*.json` + `extra-4.json`). Table over everything
finished (`t4_parity.py table`, job 317349): **123 program × mode rows, 906 kernel JSONs, 906 ok, 0
MISMATCH** (78 of them above the production lane cutoff, compared all the same; the CC_Topo 1296n program
took 4,540 s and 2,515 s) — proved-in-effect. Not finished at the time of writing: **P7-bfs-cuda**
(scalar-clock; its Python record replay is the slow side — T22 cont. could not finish its kernels 15 and
17 in 14.7 h); job 316864 keeps running until its 6 h limit (23:37), and its log
(`eval/x_logs/t24-parity-agg-le-316864.log`, the full table at the end) and
`eval/baselines/setup/t22_parity/t24-parity/shard3.json` will hold bfs if it finishes.

The first comparison (`STEP=agg`, job 316796: `t4_parity.py compare` with exact counts, T4's original
form) was stopped on bfs after its other shards finished: 904 kernel results, 776 ok and 128 MISMATCH, and
every one of the 128 is a scalar-clock count difference with aggregates < records (T22 cont.'s Fix 2,
the early exit of the scalar-clock Check); in 3 of them the verdicts differ only in the count-derived
weight field (same pair, verdict, class and race type) — `t24_exact_check.py`, job 317337. That
comparison covered the CC_Topo 1296n program in full.

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

`eval/baselines/setup/t24_time.sh`, job 316800, **one node** (c55: AMD EPYC 9115 16-core, 125 GB, RTX 4060 Ti
sm_89), one run each, in the order heartwall before → after → CC before → after, through `t19_long.sh`
(accelprof directly, `YOSEMITE_HB_DUMP=0` — the production default — `YOSEMITE_HB_STATS=1` at kernel end).
Before = the installed runtime (38af04e, libsanalyzer `a01c16667b592e5d`); after = this branch's private
runtime (`d8c5d656394f3e01`). Traces under `/mnt/beegfs/fzheng4/t24-time-{before,after}/`.

| program | mode | before wall (s) | after wall (s) | after / before | max RSS before / after (KB) | kernel JSONs |
|---|---|---|---|---|---|---|
| P7-heartwall-cuda | scalar-clock, `YOSEMITE_HB_SHARDS=16` | 3,942.18 | 3,922.31 | 0.995 | 6,519,976 / 6,512,404 | 104 / 104 |
| P1 CC `…Push_NonDeterm…NonPersist_RaceBug_Warp…-default-1296n` | scalar-clock (serial) | 1.46 | 0.99 | 0.68 | 875,276 / 877,272 | 11 / 11 |
| same | vector-clock | 1.20 | 1.10 | 0.92 | 884,272 / 884,368 | 12 / 12 |

heartwall: −0.5 % in one pair of runs, no measurable change. The CC program, the X5b program with the
most diverged instances (9,480 / 9,239 in X5b's dumped recordings), runs about one second with the dump
off, so its walls are startup-dominated and show nothing either way; it says only that the slow path
costs no visible time there. One rep each: no variance estimate (unverified).

## 6. The proof paragraph (step 5) — written by Opus, **awaiting Jeffery's check**

In `design/proof/hb_proof.tex` (commit fe07ba5), three edits, nothing else in the document:
1. Definition "Instances": the sentence "A `syncwarp` arrival is an instance by itself: S(B) its masked
   lanes, cpl(B) its position" is replaced by the warp-barrier case (key (β, ω, pc); `arrived_k` gains
   `a ∩ m`; completion at the first syncwarp-with-key-k or exit-in-ω record after which `arrived_k ⊇
   exp_k`, `exp_k` = m minus `exited_β` minus the lanes of ω absent from a block of N_β threads; S(B) =
   exp_k; a converged record completes by itself).
2. Algorithm 1's syncwarp line (`\label{ln:syncwarp}`): `arrived_k ← arrived_k ∪ (lanes(e) ∩ m(e));
   Complete(k)`.
3. A new paragraph after the Definition:

```latex
\paragraph{Warp barriers (T24; awaiting Jeffery's check).} Before T24 a \texttt{syncwarp}
record was an instance by itself with $S(B)=m$, so the first group's record of a diverged warp
ordered the pre-arrival records of the lanes still to arrive after the arrived lanes'
pre-arrival records (\texttt{eval/X5\_BYTE\_PAIRS.md} \S4). The warp case needs three
statements more. (A3$'$), in the trusted base next to A3: a warp-barrier instance completes
exactly when the hardware releases the \texttt{bar.warp.sync}, i.e.\ the hardware waits for the
non-exited lanes of $m$ that exist in the block and for no other thread, and the records of one
instance carry one $m$ (the W1 analogue; not checked, the code joins the union of their masks).
(W2$'$), part of (W2): no record of a lane (memory, arrival, \texttt{syncwarp}, pipeline or exit)
lies strictly between its \texttt{syncwarp} record and the completion of that warp segment;
checked per lane in \texttt{HbClock} and the oracle (\texttt{TV-syncwarp-completion-order}),
while the exit of a lane that has not arrived is allowed and shrinks $\exp_k$. (W3) reads a
record's active lanes, a \texttt{syncwarp}'s included: its mask names participants, and one of
them may exit while the segment is open. The fifth check covers open warp segments
(\texttt{TV-syncwarp-pending-at-end}, the runtime form of A3$'$, in \texttt{HbClock}, the oracle
and \texttt{barrier\_only\_pairs}). In Algorithm~\ref{alg:detect} a warp key's
\textsc{Complete} is \textsc{Sync}$(\exp_k)$ once $\arrv_k\supseteq\exp_k\ne\emptyset$, called
after each \texttt{syncwarp} with that key (line~\ref{ln:syncwarp}) and each exit in its warp
(line~\ref{ln:exit}). Lemma~\ref{lem:assembly} holds for warp keys as stated ($\arrv_k$ only
grows, so no count argument is needed), and by (W2$'$) a waiting lane's clock at $\cpl(B)$ is
its clock at its own record, so \S\ref{sec:single} applies unchanged. The change only removes
happens-before edges. Let $p_1<\dots<p_n=\cpl(B)$ be the positions of a warp instance's
records and $p_j$ that of $s$'s group; an edge $a\PO\arr{s}{B}\HB\dep{t}{B}\PO b$ was, before
T24, $a\PO\arr{s}{B_j}\HB\dep{t}{B_j}\PO b$ through the one-record instance $B_j$ at $p_j$, whose
participants were all of $m\supseteq S(B)$, since $\seq(a)<p_j\le p_n<\seq(b)$. (PO) is
unchanged, and so is (ATOM): $\rel$ and $\acq$ (T12) and the A2 windows (T14) still take a
\texttt{syncwarp} record as the next record of every lane of its mask, as before T24. Hence
$\HB$ after T24 $\subseteq$ $\HB$ before on memory records, and by
Lemma~\ref{lem:mono} T24 can add reports and never removes one.
```

Points for the check: (i) the inclusion argument maps each warp-instance SYNC edge to the one-record
instance of the source lane's group; (ii) "(ATOM) unchanged" holds for the code as it is, because T12/T14
still read `sync_mask` (§7 item 2) — if that is changed to the active lanes, the inclusion needs a
separate argument for the gate; (iii) not compiled with LaTeX on this cluster (no TeX run was made).

## 7. What remains unverified, and decisions for Jeffery

1. **The key (block, warp, pc), as the brief specifies.** On sm_70+ lanes may meet at *different*
   `__syncwarp()` call sites with the same mask. Such an instance would never complete under this key:
   `TV-syncwarp-completion-order` (an arrived lane continues) and `TV-syncwarp-pending-at-end` would fire,
   and the join would be lost (reports added, flagged by the monitor, never hidden). Not observed: 0 open
   instances and 0 TV in the 680 X5b launches and the 992 parity-store kernel JSONs. A key of (block, warp,
   sync_mask) would assemble that case; not done (decision for Jeffery).
2. **T12's `note_pc` and T14's `a2_close_lanes` (and the oracle's `close_lanes`) still take a syncwarp
   record as the next record of every lane of `sync_mask`**, including lanes that have not arrived. Under
   the instance model only the arrived lanes' next record is that record. This affects R3 release points
   and `a2_uncertain` flags, not the HB joins; left unchanged (outside the brief's list, and it keeps
   (ATOM) identical, §6). Decision for Jeffery.
3. **`design/algorithms_check.py`** (the simulator `test_barrier_exit.py` and `test_hb_substitutions.py`
   compare with the oracle) still implements the per-record join; no green-set test feeds it a diverged
   syncwarp, so it did not fail. Not in the freeze exception; mirroring it is a decision for Jeffery.
4. **CLAUDE.md A4's green-set command** does not list `python/test_syncwarp.py`; `merge_check.sh` does.
   CLAUDE.md was not edited by this task.
5. **Old dumps without exit records (`hb_exits`)**: a syncwarp whose mask names a lane that exited
   early can no longer complete there (the end check is skipped on those dumps, as for block barriers),
   so such a dump loses that join on replay. Not measured on any pre-T3b store.
6. **The mask-agreement part of A3$'$/W1** (all records of an instance carry one sync_mask) is not
   checked; the code joins the union of the masks.
7. **Global records of the 1296-node X5b programs** were not replayed (shared-only, as X5b; memory).
8. **Corpus-wide effect** (beyond X5b's 60 recordings and the 65-program parity set): not measured here.
9. **The proof paragraph** is unchecked by Jeffery and was not compiled.
10. Hardware: every GPU run on RTX 4060 Ti (sm_89, driver 580.82.07); no other architecture.
11. **Timing**: one run per side; the CC program is too short to measure (§5).
12. **Aggregates == records for P7 bfs** (scalar-clock) under the counts-le protocol: not finished when
    this was written (§3.2); missing. Its HbClock == specification row does not exist either (bfs has no
    vector-clock dump: TIMEOUT at the 120 s floor).

## 8. Runtime, commands, jobs

Private runtime (`t24_build.sh`, job 316790, c63; the first try, 316789 on c13, failed to link: that
`normal` node has no `/usr/local/cuda-13.3/compute-sanitizer`): libsanalyzer from this tree with
`install_merged.sh`'s make line (`OBJ_DIR/LIB_DIR/INSTALL_DIR` under `/home/fzheng4/stage-t24`), the
collector relinked from `/home/fzheng4/stage-t22t23-59a98aa/nvc/obj/*.o` (the installed collector's objects)
with RPATH `stage-t24/san-install/lib` — libsanalyzer `d8c5d656394f3e01`, collector `3dad1ffdad521833`;
installed libsanalyzer `a01c16667b592e5d` and collector `83af143748adb80c` unchanged. The worktree links
`build .env nv-compute/lib eval/baselines/{bin,corpora}` to the main checkout and `lib` to
`stage-t24/rt-lib`; `ScoR/` and `cuHadron/` are directories of links with private
`ScoR/microbenchmarks/artifacts` and `cuHadron/_*`.

```
X=c2,c21,c23,c37,c46,c54; S=eval/baselines/setup; L=eval/x_logs
sbatch -p rtx4060ti16g -x $X -o $L/t24-explore-%j.log $S/t24_explore.sh                 # 316786 probe
sbatch -p rtx4060ti16g -x $X -o $L/t24-test-before-%j.log $S/t24_test.sh                # 316788 (lib -> installed)
sbatch -p rtx4060ti16g -x $X -o $L/t24-build-%j.log $S/t24_build.sh                     # 316790
sbatch -p rtx4060ti16g -x $X -o $L/t24-test-after-%j.log $S/t24_test.sh                 # 316792 (lib -> stage)
sbatch -p rtx4060ti16g -x $X -o $L/t24-check-%j.log $S/t24_check.sh                     # 316793 green set 1/8/16
sbatch -p rtx4060ti16g -x $X --cpus-per-task=16 --export=ALL,SHARDS=16,INLINE=0 $S/t24_test.sh   # 316806
sbatch -p rtx4060ti16g -x $X --array=0-7 --export=ALL,STEP=rec $S/t24_parity.sh         # 316794
sbatch -p normal -x $X --array=0-7 --dependency=afterany:316794 --export=ALL,STEP=spec $S/t24_parity.sh  # 316795
sbatch -p normal -x $X --array=0-7 --dependency=afterany:316794 --export=ALL,STEP=agg $S/t24_parity.sh   # 316796
sbatch -p normal -x $X --cpus-per-task=12 --time=06:00:00 --export=ALL,STEP=agg-le $S/t24_parity.sh     # 316864
sbatch -p normal -x $X --export=ALL,STEP=agg-ids,OFF=1,IDS=<id>:<id>:... $S/t24_parity.sh            # 317321, 317322
sbatch -p normal -x $X $S/t24_py.sh $S/t4_parity.py table $S/t22_parity/t24-parity/*.json           # 317339 (partial)
sbatch -p normal -x $X $S/t24_py.sh $S/t4_parity.py table $S/t22_parity/t24-parity/shard*.json $S/t22_parity/t24-parity/extra-4.json   # 317349
sbatch -p normal -x $X $S/t24_py.sh $S/t24_exact_check.py $S/t4_parity/t24-parity/shard*.json       # 317337
sbatch -p normal -x $X -o $L/t24-replay60-%j.log $S/t24_replay60.sh                     # 316799
sbatch -p normal -x $X -o $L/t24-census-%j.log $S/t24_census.sh                         # 316821
sbatch -p normal -x $X $S/t24_replay_store.sh                                           # 316823
sbatch -p normal -x $X --export=ALL,NPROC=3,SUF=-b,SKIP=eval/results/t24/replay-t24-parity.jsonl $S/t24_replay_store.sh  # 316831
sbatch -p rtx4060ti16g -x $X -o $L/t24-time-%j.log $S/t24_time.sh                       # 316800
```

Outputs: `eval/results/t24/` (replay60, census, store replays), `eval/results/t24-parity/` (rows),
`eval/baselines/setup/t5b_parity/t24-parity/`, `t4_parity/t24-parity/` (exact counts),
`t22_parity/t24-parity/` (counts-le), logs `eval/x_logs/t24-*` (force-added). Kept on BeeGFS:
`cuvein_traces/t24-parity`, `t24-check`, `t24-time-{before,after}`.

## Addendum (coordinating session, 2026-10-22): the P7-bfs scalar-clock aggregates row

Job 316864 (aggregates == records, counts-le, P7-bfs-cuda scalar-clock) ended TIMEOUT at its 6 h limit. Its partial output (t22_parity/t24-parity/shard3.json) covers all 24 kernels: 14 ok, 10 stopped at the per-kernel cap (not compared), 0 mismatches. The Python record-replay reference is quadratic on the flag word (T22 cont. could not finish bfs kernels 15 and 17 in 14.7 h either). Jeffery decided (2026-10-21) to merge with these 10 kernels not compared; every other parity row is 0 mismatches.
