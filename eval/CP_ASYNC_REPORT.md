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
  (the copy is ordered after `t`'s earlier accesses), and the access is recorded at `α(t)`'s
  current epoch;
* `commit` by `t`: push `vc[α(t)]` onto `t`'s group list, then `α(t)` ticks, so the copies of
  later groups get a newer epoch (as implemented; an earlier draft of this list ticked at issue,
  which gives the same orders);
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

**Flag for the async write** (considered, not implemented; the next paragraph says why).
Memory records carry the Sanitizer's `SANITIZER_MEMORY_DEVICE_FLAG_*`
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

**Plan** (as drafted before implementation; §2 lists what was built, and the static-leg part
went differently, see below): new `MemoryType::PipelineCommit` / `PipelineWait` emitted through
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

**The static leg gets no cp.async rule — a deviation from the brief's step 4, on purpose.** The
`0x80 ← 0x70` edge (the read after the thread's own copy) is intra-thread in the dependency
graph, and `sync_dominance.analyze` already judges such an edge whenever the event stream
shows the pair cross-agent: the engine's race record (vector-clock mode) or the offline barrier
pass's unordered pair (scalar-clock mode) rescues it with the thread-pair distance, and R1
finds no ordering sync, so the pair is RACE; when the wait orders it, neither source lists it
and the edge stays dropped. A static rule would have to decide, per path, which `DEPBAR.LE N`
covers which `LDGSTS` (commit-group counting across the CFG); without it, a static rescue would
report the fixed build as racy. Cost of the choice: scalar-clock mode sees an async race only
when the offline pass runs (it skips dumps above `CUVEIN_BARRIER_PASS_MAX_LANES`, 5 M lanes).
*Correction from the review (§6):* "R1 finds no ordering sync" holds only when nothing
separates the copy from the read. With a `__syncthreads()` in between, R1 credits the barrier,
although a barrier completes no copy. Scalar-clock mode then returned ORDERED before it
consulted the offline pass, and vector-clock mode labelled the race `model_bug`. The static
rules therefore now give no credit to a pair whose *earlier* access is a copy, and R3 gives no
credit to any pair with a copy.

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
| static leg (`analyze`), review | no R1/R2 credit when the earlier access of a pair is a copy, no R3 credit for a pair with a copy (§6) |
| copies completed through an mbarrier, review | `sd.async_pcs` is empty for a kernel with `ARRIVES.LDGSTSBAR` (`cp.async.mbarrier.arrive`): pre-T1a reading, for the engine (sidecar) and the oracle / offline pass (CFG) alike (§6) |
| two copies of one thread, review | engine, oracle and offline pass report the pair (WAW) unless a wait completed the first: the thread's view of its agent decides (§6) |
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
binaries are not built. So no other program's verdict can move through the cp.async
model. The one other engine change, the 64-bit thread ids, matters only for a launch of
2²² or more blocks, where the 32-bit ids used to collide (`block << 10` overflowed); no
such launch was checked for here.

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
* **The static leg** has no cp.async rule of its own (§1); since the review it only withholds
  credit from pairs with a copy (§6). So in scalar-clock mode an async race is seen only when
  the offline pass runs, which it skips above `CUVEIN_BARRIER_PASS_MAX_LANES`; above the cap
  a pair whose earlier access is a copy is reported (no static proof), fixed or not.
* **Copies completed through an mbarrier** (`cuda::memcpy_async` with a `cuda::barrier`) keep
  the pre-T1a reading (§6): their races are not seen until mbarriers are modelled (T1b).
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

## 6. Fresh-context review (follow-up branch `fix/cp-async-review`)

The brief asks for a verifier in a fresh context. A read-only Opus review of the merged T1a
(`bc32a1f`) found the dynamic model right in all three implementations, including uncommitted
copies at a wait, `N >= G`, repeated waits, divergent warps, a write to the source before the
wait, and a barrier between issue and wait. It also found the parity of issue / commit / wait,
both clocks, the `async` field and the agent distance, the 64-bit ids, the marker gating and
the default path in order. Each finding below was checked against the code, and each
behavioural one was reproduced before it was fixed. `python/testdata/cp_async_wait.cu` gained
six builds for this: `barrier`, `barrier_fixed`, `barrier_own`, `twice`, `twice_fixed` and
`mbarrier`. A full-mask `__syncwarp()` on a converged warp compiles to a `NOP` (checked with
a runtime mask too), so the "a syncwarp suffices" case is covered by `barrier_own`.

| # | finding | verified | fix |
|---|---|---|---|
| 1 | a `__syncthreads()` between a copy and the read is credited by R1 | reproduced: scalar-clock ORDERED (FN), vector-clock RACE classed `model_bug` | no R1/R2 credit when the earlier access is a copy; no R3 credit for a pair with a copy (`analyze`) |
| 2 | copies completed through an mbarrier (`ARRIVES.LDGSTSBAR`) never complete | reproduced: spurious RAW copy → own read, vector-clock | such a kernel keeps the pre-T1a reading (`sd.async_pcs`, so sidecar and CFG agree) |
| 3 | two copies of one thread are unordered (PTX orders no two cp.async operations) but never raced: one agent per thread, and same-tid pairs are skipped | reproduced: no race | a same-agent write is checked against the thread's view of the agent (engine `conflict(..., obs)`, oracle `observer=`, offline pass) |
| 4 | `--assume-warp-lockstep` orders the copy vs the read (same warp, program order) | read from the code (the harness does not pass the flag) | no lock-step rescue for records with `async` |
| 5 | inputs: the sidecar's copy pcs were last-cubin-wins for a multi-arch binary; the engine falls back to all kernels' copy pcs for an unmatched kernel name; the marker is written even when the engine had no copy pcs (no sidecar) | read from the code | union per kernel, like the coherent-pc table. The fallback is unchanged (the coherent table does the same, with a warning). A missing sidecar already degrades every atomic to a plain access (`eval/FIX_REPORT.md`, Verification), so it is documented rather than special-cased |
| 6 | doc errors: tick at issue (the code ticks at commit), the `ASYNC_COPY` flag and the static-leg plan described as if built, the corpus claim without the 64-bit ids | read | corrected in §1 and §3 |
| 7 | `async_issue` copies the sync-only base per copied lane (O(block) each) | not measured | left for T5b (shared-base clocks); noted in §5 |

**Before → after**, from the same nine builds on c20 (RTX 4060 Ti, sm_89): the T1a runtime
and Python (job 288377) against the review runtime (libsanalyzer `95659970773ed751`, fatbin
unchanged `a2d7368bc1c61986`) and Python (job 288384). The probe is `.probe/run_variants.sh`,
kept out of the repository; the same assertions are `python/test_cp_async.py`.

| build | engine races on a copy, before → after | vector-clock | scalar-clock |
|---|---|---|---|
| racy, groups | the copy/read RAW → same | RACE `structural` → same | RACE → same |
| fixed, barrier_fixed, twice_fixed | none → none | CLEAN → CLEAN | CLEAN → CLEAN |
| barrier, barrier_own | the copy/read RAW → same | RACE `model_bug` → RACE `structural` | **ORDERED → RACE** |
| twice | none → **WAW `"ab"`** | CLEAN → **RACE** | CLEAN → **RACE** |
| mbarrier | **spurious RAW** → none | **RACE** → CLEAN on the copy | CLEAN → CLEAN |

In the mbarrier build the `cuda::barrier`'s own polling of its state word (`ATOMS.ADD` vs
`LDS`) is also an engine race, classed `benign`, before and after. mbarriers are T1b. Engine
== oracle holds on all nine builds.

**Checks after the fixes** (c20):
* `setup/review_check.sh`, job 288385. The default tool path is IDENTICAL to the installed
  runtime's for the two ScoR programs, and the vector-clock dumps are IDENTICAL minus
  `hb_async`. `python/test_cp_async.py`: 67 passed. The green set with it: 203 passed,
  1 xfailed (136 + 67).
* `setup/review_rescore.sh`, job 288383 (CPU, c1). The T1a evaluation store (`t1a-p56`,
  marked dumps, 59 programs, both modes), re-scored with the review Python against the T1a
  Python's rows, gives 118 rows, **0 differ**. The pre-T1a store evcand against the merged
  detector gives 354 rows, **0 differ**. The engine change (#3) is not in those dumps'
  `hb_races`, but no kept program has two copies of one thread to one location (only the six
  P6 `memcpy` programs contain `LDGSTS`, one copy per thread each).
