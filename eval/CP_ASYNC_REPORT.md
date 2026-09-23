# `cp.async` (LDGSTS) wait modelling: design check and results (T1a)

Branch `feat/cp-async-wait` (worktree `/home/fzheng4/wt-T1a`), based on `cuVein` @ `07d2798`
(T2 merged). Claude.md T1a; the design it checks is F4 in `eval/FIX_REPORT.md`.

## 1. Design check (step 1 and the F4 design)

**Instruction ids** (read from the CUDA 13.3 toolkit's `compute-sanitizer/include/sanitizer_patching.h`
on c20, 2026-09-23; header copyright 2018-2025; the full enumerator list and every patch
callback signature are in `eval/baselines/setup/t2_evidence/sanitizer_api.txt`):
`SANITIZER_INSTRUCTION_MEMCPY_ASYNC = 14` (`(userdata, pc, void* src, uint32_t dst, uint32_t
accessSize)`, already registered), `PIPELINE_COMMIT = 15` (`(userdata, pc)`), `PIPELINE_WAIT = 16`
(`(userdata, pc, uint32_t groups)`). For T1b: `REMOTE_SHARED_MEMORY_ACCESS = 17`,
`CUDA_BARRIER = 13` / `CUDA_BARRIER_ATTEMPT = 39` (mbarrier), `CLUSTER_BARRIER_ARRIVE/WAIT = 21/22`,
`BULK_COPY_* = 30, 35-38`, `TMA_LOAD/STORE = 43/44`, `MEMCPY_ASYNC_BARRIER = 34`.

**Correction to F4 — commit groups.** F4 joins the thread's async agent into the thread at any
`PIPELINE_WAIT`. `cp.async.wait_group N` only completes the groups older than the N most recent
committed ones, and copies not yet committed are not covered by it; `wait_all` is
`commit_group; wait_group 0`. Joining everything at every wait would order copies that are
still in flight, i.e. hide real races whenever N > 0. The model below therefore also registers
`PIPELINE_COMMIT` and keeps one clock snapshot per committed group:
* issue of an async copy by thread `t`: the access belongs to the agent `α(t)`; `vc[α(t)] ⊔= vc[t]`
  (the copy is ordered after `t`'s earlier accesses), then `α(t)` ticks and the access is
  recorded at `α(t)`'s epoch;
* `commit` by `t`: push `vc[α(t)]` onto `t`'s group list;
* `wait_group N` by `t`: with G committed groups, join the snapshot of group `G-N` (1-based;
  snapshots only grow) into `vc[t]`; N ≥ G joins nothing.
The same in the sync-only clock (`vs`): the join is schedule-independent, like a barrier.

**Thread ids.** `tid_of` packs `(block << 10) | (warp << 5) | lane` into 32 bits in `HbEngine`, so
there is no free high bit (and block ids ≥ 2²² already collide). The agent id needs a 64-bit tid:
`α(t) = t | 1 << 62`. In the engine's hash nodes a `uint64_t` key costs nothing (the
`pair<const uint32_t, uint64_t>` is already padded to 16 bytes). Race records keep the issuing
thread's id and gain `"async"`: `"a"`, `"b"` or `"ab"`, the side(s) the copy performed. That is a
string rather than the brief's boolean, because either side of a pair can be a copy. No virtual
id leaks into reports.

**Flag for the async write.** Memory records carry the Sanitizer's `SANITIZER_MEMORY_DEVICE_FLAG_*`
bits (0x1-0x80; barrier records reuse `flags` for the bar index but are a different
`MemoryType`), so `ASYNC_COPY = 0x40000000` on the two records `MemcpyAsyncCallback` emits (the
global read and the shared write, both performed by the copy, not by the thread) cannot collide.

**Where asyncness comes from — a revision of F4.** F4 flags the LDGSTS shared write on the device
(`ASYNC_COPY` bit). But the default tool path prints each record's `flags` (`current_flags` in
`kernel_N.json`), so a new bit there changes the default output, which Claude.md A3 forbids.
Asyncness is a static property of the instruction: every record `MemcpyAsyncCallback` emits sits
at an `LDGSTS` pc, and the atomic-scope sidecar already maps pcs to access kinds from the CFG
(`python/atomic_scope_sidecar.py` → `<pc> <scope> <kind> <kernel>`). The sidecar gains
`# async <pc> <kernel>` lines for `LDGSTS` pcs, which the engine reads. The oracle and
`barrier_only_pairs` take the same set from the CFG (`sd.async_pcs`: opcode `LDGSTS`), so no
device-side flag is needed. These are comment lines, not a new kind in
`<pc> <scope> <kind> <kernel>`: the engine's loader maps every kind other than `ldst` to an
atomic RMW (`PcInfo{scope, kind != "ldst"}`), so an older engine would read an `async` kind as
an atomic. It skips a `#` line instead. The two new patch points (`PIPELINE_COMMIT`, `PIPELINE_WAIT`) are
registered only when `YOSEMITE_HB_TRACE=1`, so the default path does not change at all.

**Plan** (unchanged otherwise): new `MemoryType::PipelineCommit` / `PipelineWait` emitted through
`EmitSyncEvent` (`groups` in `accessSize`); serialized as `"pipeline_commit"` /
`"pipeline_wait"` events; 64-bit thread ids in `HbEngine`; the agent model above in engine +
oracle + `barrier_only_pairs` in one commit; the static leg treats an `LDGSTS` writer as another
agent (its `0x90←0x70` edge is judged, not dropped as `intra_thread_only`) and `DEPBAR` as the
ordering sync of that pair; tests `python/testdata/cp_async_wait.cu` (read-before-wait racy,
wait-before-read fixed, plus a `wait_group 1` case whose last group stays in flight); tripwire:
if `PIPELINE_WAIT` does not fire for `DEPBAR.LE` on sm_89, stop and report.

**What sm_89 emits** (measured on c34, CUDA 13.3 V13.3.73, `python/testdata/cp_async_wait.cu`
compiled with `-arch=sm_89`): `cp.async` → `LDGSTS.E [shared], [global]`;
`cp.async.commit_group` → `LDGDEPBAR`; `cp.async.wait_group N` → `DEPBAR.LE SB0, N`;
`cp.async.wait_all` → `LDGDEPBAR` + `DEPBAR.LE SB0, 0x0`. Racy variant: `LDGSTS @0x70, LDS @0x80,
LDGDEPBAR @0x90, STG, DEPBAR.LE SB0,0x0 @0xb0`; fixed: the `LDS` moves after the `DEPBAR`;
groups: `LDGSTS, LDGDEPBAR, LDGSTS, LDGDEPBAR, DEPBAR.LE SB0,0x1, LDS, LDS, …, DEPBAR.LE SB0,0x0`.
So the commit/wait model maps one-to-one onto `LDGDEPBAR` / `DEPBAR.LE`; whether the Sanitizer's
`PIPELINE_COMMIT` / `PIPELINE_WAIT` callbacks fire on them is the tripwire experiment.
(Node note: c11 in `normal` has no CUDA 13.3 — up to 13.2 only; builds needing it run on the
GPU partitions.)

**The static leg is left unchanged — a deviation from the brief's step 4, on purpose.** The
`0x80 ← 0x70` edge (the read after the thread's own copy) is intra-thread in the dependency
graph, and `sync_dominance.analyze` already judges such an edge whenever the event stream
shows the pair cross-agent: the engine's race record (vector-clock mode) or the offline barrier
pass's unordered pair (scalar-clock mode) rescues it with the thread-pair distance, and R1
finds no ordering sync, so the pair is RACE; when the wait orders it, neither source lists it
and the edge stays dropped. A static rule would have to decide, per path, which `DEPBAR.LE N`
covers which `LDGSTS` (commit-group counting across the CFG); without it, a static rescue would
report the fixed build as racy. Cost of the choice: scalar-clock mode sees an async race only
when the offline pass runs (it skips dumps above `CUVEIN_BARRIER_PASS_MAX_LANES`, 5 M lanes).

**Old dumps: the `hb_async` marker** (added after the first evaluation run, §3). Every
LDGSTS access in a dump from an older collector is present, but its commit and wait events
are not. Under the agent model, such a copy never completes, so re-scoring a kept pre-T1a
store with the new Python would report every read after a copy. Measured: on the kept evcand
dump of `memcpy/global_readwrite_race`, the thread's own `LDS 0x120` after its copy became a
RAW. The engine therefore writes `"hb_async": 1` after `hb_events`, in HB-trace mode only.
The oracle and the offline pass apply the agent model only to a dump that carries it
(`sd.dump_async_pcs(eng, trace)`). An unmarked dump keeps the pre-T1a reading, where the copy
is the issuing thread's own access, so re-scoring any kept store gives the verdicts it gave
before. The marker is written by the engine and certifies the collector's events, so a T1a
libsanalyzer must run with the T1a collector and fatbin. The staged install carries all three.
`python/test_cp_async.py` skips on a runtime that has neither the marker nor pipeline events,
and fails on one that has only one of them (a partial install).

## 2. Implementation

| layer | change |
|---|---|
| device (`nv-compute/gpu_src`) | `MemoryType::PipelineCommit` / `PipelineWait`; `PipelineCommitCallback(pc)` and `PipelineWaitCallback(pc, groups)` emit one record per warp through `EmitSyncEvent` (`accessSize` = N) |
| collector (`compute_sanitizer.cpp`) | registers `SANITIZER_INSTRUCTION_PIPELINE_COMMIT` / `_WAIT` for `pc_dependency_analysis` only when `YOSEMITE_HB_TRACE` is set |
| serializer (`hb_collect_events`) | `{"type": "pipeline_commit"}` / `{"type": "pipeline_wait", "groups": N}`; the default-path record switch skips both types |
| sidecar (`atomic_scope_sidecar.py`) | `# async <pc> <kernel>` lines for `LDGSTS` pcs (comment lines: an older engine skips them) |
| engine (`HbEngine`) | 64-bit `Tid`; `ASYNC_BIT = 1 << 62`; `async_issue` / `async_commit` / `async_wait` on both clocks; race records keep the thread's id and add `"async": "a"|"b"|"ab"`; the dump gains `"hb_async": 1` after `hb_events` (HB-trace mode only) |
| oracle (`hb_oracle.py`) | the same model, one-to-one; the async pcs from the CFG (`sd.async_pcs`: opcode `LDGSTS`), for a dump with the `hb_async` marker only (`sd.dump_async_pcs`) |
| offline pass (`barrier_only_pairs`) | the same model on its shared-base clocks (`async_pc=`, from `sd.dump_async_pcs` in `analyze`); an agent's distance is its thread's |
| tests | `python/testdata/cp_async_wait.cu` (racy / fixed / groups), `python/test_cp_async.py` (21 cases, incl. the marker and an unmarked dump), the two parity tests pass the dump's async pcs |

## 3. Results

All runs are on the NCSU ARC cluster, c20: RTX 4060 Ti, sm_89, driver 610.43.02, CUDA 13.3.
The T1a runtime is built by `setup/t1a_build.sh` (job 288237, c26, GCC 12.4.0): collector
`247bed46a5c4cd37`, libsanalyzer `892f963bbe5d0cd5`, pc_dependency fatbin `a2d7368bc1c61986`.
The collector and fatbin are unchanged from the first build, 288050. The main checkout's
installed runtime, the "before" side, is collector `368bea48d8d8ab35` with libsanalyzer
`785d27a28b6456c5`.

**Tripwire and model** (measured, `setup/t1a_check.sh`, job 288294):
`python/test_cp_async.py` 21 passed.
* `PIPELINE_COMMIT` and `PIPELINE_WAIT` fire for `LDGDEPBAR` and `DEPBAR.LE` on sm_89. The dumps
  carry `pipeline_commit` events and `pipeline_wait` with `groups` 0 (racy, fixed) and 1, 0
  (groups), so the tripwire does not trigger. Every dump carries `"hb_async": 1`.
* Engine `hb_races`: racy = exactly `(LDGSTS, LDS)` RAW with `"async": "a"`; fixed = none;
  groups = exactly the second group's `(LDGSTS, LDS)`, with the first group's read ordered.
* Engine == oracle (races with the `async` field, and `hb_races_sync_only`), and offline
  barrier pass == oracle, on all three builds.
* Verdicts in both vector-clock and scalar-clock mode: racy RACE {(copy, read)}, fixed CLEAN,
  groups RACE {(second copy, its read)}.
* A dump stripped of the marker and the commit/wait events (what a pre-T1a collector writes)
  gets no race from the oracle or `analyze` in any build, which is the pre-T1a reading.

**Default tool path byte-identical; the HB-trace dump adds exactly one key** (measured, same
job). For `race_interblock_none-lock_rtraw` and `norace_interblock_atom`, the T1a runtime's
dumps were compared with the installed runtime's up to device addresses
(`setup/dump_compare.py`). The default path (no `YOSEMITE_HB_TRACE`) is IDENTICAL, with no
`hb_async` key. The vector-clock dump is IDENTICAL once the one new key is dropped
(`--drop hb_async`), and that key is `1`.

**Green set with `test_cp_async.py`** (measured, T1a runtime, jobs 288294 and 288295):
157 passed, 1 xfailed (`test_relaxed_handoff_should_race`). That is the four green-set files
(136) plus the 21 new cases. On the installed pre-T1a runtime, `test_cp_async.py` skips all
21 with the reason "the traced runtime predates T1a" (job 288360, which also re-checked the T1a
runtime: 21 passed).

**Evaluation: P5 + P6, both modes, against the merged baseline rows** (measured,
`setup/t1a_eval.sh`, job 288295; 59 programs, 1 rep, `--confirm`; 14.4 GB of traces in
`/mnt/beegfs/fzheng4/cuvein_traces/t1a-p56`). The 59 are the 33 ScoR litmus + canary and the
26 built P6 programs outside `asyncmemcpy/*` and `interkernel/*` (host-level, T2) and
`bulkcpy/*` and `dsmem/*` (sm_90 only, not built).

| program | mode | baseline | T1a |
|---|---|---|---|
| `P6-memcpy-shared_readwrite_race-racy` | vector-clock | CLEAN | **RACE** `shared:0x70-0x90:RAW` |
| `P6-memcpy-shared_readwrite_race-racy` | scalar-clock | CLEAN | **RACE** `shared:0x70-0x90:RAW` |

The other 116 (program, mode) rows keep their verdict and report ids. That meets the F4
expectation (racy → 1 RAW, fixed → 0) and the acceptance (no other P5/P6 verdict changes).

*The first evaluation run* (job 288064, before the marker existed; its CSV and store were
replaced by the re-run) showed one more difference:
`P6-memcpy-global_readwrite_race-racy` scalar-clock kept its single report, but its id changed
from `shared:0xf0-0x190:WAW` to `global:0xf0-0x190:WAW`. It is not a T1a effect.
`aggregate._dedup_key` takes the space of the verdict's current pc, and the trace edge between
the copy (`0xf0`, flags `READWRITE GLOBALSHARED`, so space "shared") and warp 1's `STG` (`0x190`,
"global") points whichever way the two warps' accesses were recorded. Re-analysed with the
merged Python, the kept evcand dumps give "global/shared" for vector-clock and "shared/global"
for scalar-clock. The re-run's report id matches the baseline again. The report's type `WAW` is
the same flags reading (`READWRITE` → write), even though the conflict is the copy's global
*read* against the `STG`. Both are pre-existing and left alone (§5).

**E6a agreement** (computed): racecheck's verdicts (`eval/results/E6a-racecheck.csv`, not
re-run) against the T1a rows for the nine shared-memory cases (`intersubwarp/*` racy and fixed,
`memcpy/shared_*`, `false_positives/shared_bytewise_*` racy) agree **9/9 in both modes**, up
from 8/9. The one disagreement was this FN.

**E2** (`eval/manifests/e2_fix.json`): the manifest's binaries lived in the removed eval-suite
worktree. Its 14 programs are the baselines harness's P6 `memcpy/*` (6), `intersubwarp/*` (4)
and `asyncmemcpy/*` (4). The first ten are among the 59 evaluated above and are unchanged
except for the FN. The `asyncmemcpy` four contain no cp.async (next paragraph), and their
baseline rows are TIMEOUT or ERROR on trace volume (T2 evaluated them through its `P6small`
variants).

**Which programs T1a can change at all** (measured): the agent model acts only at `LDGSTS`
pcs. Across the CFG dots kept in every store (720 of the 4,725 manifest rows, covering every
P1, P3, P4, P5, P7 and P9 binary, 33 of the 34 built P6 binaries, and 130 of the 590 PI
binaries), plus a `cuobjdump -sass` scan of the 461 built binaries the dots do not cover, only
the six `P6-memcpy-*` programs contain `LDGSTS`. The 16 sm_90-only `bulkcpy` and `dsmem`
binaries are not built. So no other program's verdict can move under T1a.

**Kept pre-T1a stores are unaffected** (measured, `setup/t1a_oldstore.sh`, CPU re-score of the
same dumps by the merged detector and by T1a's):

| store | job | rows | differ |
|---|---|---|---|
| evcand (all 59 programs, 3 reps, both modes) | 288297 (c55) | 354 | **0** |
| full-2026-09-22 (holds 6 of the 59; the other 53 are ERROR rows on both sides) | 288250 (c0) | 65 | **0** |

Without the marker, the first of these would have differed (the `LDS 0x120` above).

## 4. Commands

| step | command | job | output |
|---|---|---|---|
| build | `sbatch -p rtx4060ti8g eval/baselines/setup/t1a_build.sh` | 288050, then 288237 after the marker | `wt_install/`, `wt_nvc_lib/`, `wt_rt_lib/` |
| check | `PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t1a_check.sh` | 288051, then 288294 | `build_logs/t1a-check-*.log` |
| evaluation | `PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t1a_eval.sh` | 288064, then 288295 | `eval/results/t1a-p56/` |
| old stores | `sbatch --export=ALL,TAG=evcand eval/baselines/setup/t1a_oldstore.sh` (and `TAG=full-2026-09-22`) | 288297, 288250 | `eval/results/t1a-oldstore-<store>-{head,t1a}/` |
| skip check | `PIN8G=1 sbatch -p rtx4060ti8g -w c20 eval/baselines/setup/t1a_skipcheck.sh` | 288360 | `build_logs/t1a-skipcheck-288360.log` |

The first evaluation's comparison printed "0 rows": `make_tables.load_runs` skips any file
named `*-shard*`, and the per-run CSV is one. `t1a_eval.sh` now compares through a plain copy.

## 5. What remains unverified, and other findings

* **Other architectures.** Measured on sm_89 only. The brief's tripwire names sm_86 as well,
  and no sm_86 node was used.
* **The static leg** still has no cp.async rule (§1), so in scalar-clock mode an async race is
  seen only when the offline pass runs, which it skips above `CUVEIN_BARRIER_PASS_MAX_LANES`.
* **Mixed runtimes.** A T1a libsanalyzer with an older collector writes the marker without the
  events: copies never complete, and reads after them are reported. `test_cp_async.py` fails
  in that state, but nothing in the tool refuses it.
* **`YOSEMITE_HB_TRACE` parsing differs slightly.** The collector registers the two patch
  points for any value other than empty or `0`. The engine turns HB tracing on for a positive
  integer. Every value that turns the engine on also turns the collector on. The reverse
  (`00`, `yes`) only adds records that the default path skips.
* **Cost** of the extra commit/wait records: not measured. They are one record per warp per
  `LDGDEPBAR` / `DEPBAR.LE`, and only in HB-trace mode.
* **The dedup key's space for a pc with two spaces** (the copy) depends on record order, and
  the copy's `READWRITE` flags make its pairs `WAW` (§3). Both are pre-existing, in
  `aggregate._dedup_key` and `sync_dominance.parse_flags`. A canonical key would re-key every
  mixed-space report in every stored table, so it is left for a task that re-keys them.
* **Green-set definition.** The brief adds `test_cp_async.py` to the green set. The command in
  `Claude.md` Part A still lists four files; it was not edited here.
