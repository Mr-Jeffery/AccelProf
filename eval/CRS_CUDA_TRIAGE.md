# crs-cuda: the HeCBench program cuVein reports and SuperCollider calls race-free (T3)

Branch `triage/crs-cuda` (worktree `/home/fzheng4/wt-T3`), based on `cuVein` @ `81b4262`.
2026-09-23. Claude.md T3.

**Verdict: cuVein false positive, class (c) — a detector bug.** crs-cuda is race-free, as
SuperCollider's label says. Every cuVein report on it, in both modes, comes from one modelling
error: the barrier assembly waits for all `block_thread_count` threads of a block at a
`__syncthreads()`, but crs-cuda's kernels let 2-3 threads per 128-thread block (or the threads
past `size` in the last block) return before the loop's barriers. A thread that has exited no
longer takes part in a CTA barrier, so the hardware releases the barrier; cuVein's engine and
its offline barrier pass never do. The label stands (no footnote hook needed). The fix is
proposed in §6, together with an offline check of its effect: every report of the 8 re-scored
launches disappears in both modes. A failing test is in `python/test_barrier_exit.py`.

Legend: **measured** = a command ran and its output is quoted or saved; **read from the
code/source**; **unverified**.

## 1. The trace (step 1)

The home copy `eval/baselines/traces_keep/P9-crs-cuda/` kept only `dots/` and `meta.json`: its
10.2 GB scalar-clock dump exceeded the pre-T0 300 MB cap (`keep_reason:
trace-too-large`), and its vector-clock reps had timed out at 120 s. The T0 store has it whole:
`/mnt/beegfs/fzheng4/cuvein_traces/full-2026-09-22/P9-crs-cuda/` (node c51, RTX 4060 Ti, sm_89,
job 286811, 1200 s cap): vector-clock 50 kernel dumps, 16.1 GB, 9,617,332 events, 260 s,
complete; scalar-clock 50 dumps, 10.2 GB, 44 s, complete. The program: `crs-cuda 1 1`
(`sc-artifact` input), 50 launches of 20 kernels `gcrs_m_<m>_w_<w>_coding_dotprod` (m = 1..4,
w = 4..8), 128 threads per block.

## 2. Re-score with the current detector (step 2)

Measured, job 287909 on c26 (`setup/t3_crs.sh`, `parallel.py analyze` of that store with the
worktree at `81b4262`, i.e. the current detector; `eval/results/t3-crs/`,
`eval/baselines/confirm_t3-crs/`): **vector-clock RACE, 155 deduped reports (142 `model_bug`,
13 `structural`); scalar-clock RACE, 7 reports (static leg, no class)** — the same report ids as
the committed P9 row and the T0 CPU re-score, so the verdict does not predate anything.
`eval/triage.py` on the per-mode detail files: `setup/t3_crs/triage_py.txt`. The per-kernel
table (`setup/t3_crs_triage.py` → `setup/t3_crs/triage.{json,md}`) follows.

| kernel (w) | launches | grid × 128 | threads that exit per block (blocks) | barrier instances fired / released short (all launches) | TV-flagged launches | vector-clock RACE verdicts per launch | classes | scalar-clock RACE per launch |
|---|---|---|---|---|---|---|---|---|
| gcrs_m_1_w_4 (4) | 4 | 1024 | 0 (1024) | 20480 / 0 | 0 | 0, 0, 0, 0 | barrier-ordered 2 | 0, 0, 0, 0 |
| gcrs_m_1_w_5 (5) | 4 | 1093 | 3 (1048), 53 (1) | 0 / 20980 | 4 | 5, 15, 25, 20 | model_bug 60, structural 5 | 0, 0, 5, 0 |
| gcrs_m_1_w_6 (6) | 4 | 1093 | 2 (1040), 92 (1) | 0 / 20820 | 4 | 6, 18, 30, 24 | model_bug 72, structural 6 | 0, 0, 0, 0 |
| gcrs_m_1_w_7 (7) | 4 | 1171 | 2 (1040), 86 (1) | 0 / 20820 | 4 | 7, 7, 7, 7 | model_bug 28 | 0, 0, 0, 0 |
| gcrs_m_1_w_8 (8) | 4 | 1025 | 0 (1024), 112 (1) | 20480 / 20 | 4 | 4, 4, 4, 4 | model_bug 16 | 0, 0, 0, 0 |
| gcrs_m_2_w_4 (4) | 3 | 1025 | 0 (1024), 112 (1) | 18432 / 18 | 3 | 6, 10, 8 | model_bug 22, structural 2 | 0, 2, 0 |
| gcrs_m_2_w_5 (5) | 3 | 1093 | 3 (1048), 38 (1) | 0 / 18882 | 3 | 5, 5, 5 | model_bug 15 | 0, 0, 0 |
| gcrs_m_2_w_6 (6) | 3 | 1093 | 2 (1040), 74 (1) | 0 / 18738 | 3 | 6, 6, 6 | model_bug 18 | 0, 0, 0 |
| gcrs_m_2_w_7 (7) | 3 | 1171 | 2 (1040), 72 (1) | 0 / 18738 | 3 | 7, 7, 7 | model_bug 21 | 0, 0, 0 |
| gcrs_m_2_w_8 (8) | 3 | 1025 | 0 (1024), 104 (1) | 18432 / 18 | 3 | 4, 4, 4 | model_bug 12 | 0, 0, 0 |
| gcrs_m_3_w_4 (4) | 2 | 1025 | 0 (1024), 104 (1) | 14336 / 14 | 2 | 2, 2 | model_bug 4 | 0, 0 |
| gcrs_m_3_w_5 (5) | 2 | 1093 | 3 (1048), 28 (1) | 0 / 14686 | 2 | 5, 5 | model_bug 10 | 0, 0 |
| gcrs_m_3_w_6 (6) | 2 | 1093 | 2 (1040), 68 (1) | 0 / 14574 | 2 | 6, 6 | model_bug 12 | 0, 0 |
| gcrs_m_3_w_7 (7) | 2 | 1171 | 2 (1040), 65 (1) | 0 / 14574 | 2 | 7, 7 | model_bug 14 | 0, 0 |
| gcrs_m_3_w_8 (8) | 2 | 1025 | 0 (1024), 96 (1) | 14336 / 14 | 2 | 4, 4 | model_bug 8 | 0, 0 |
| gcrs_m_4_w_4 (4) | 1 | 1025 | 0 (1024), 96 (1) | 8192 / 8 | 1 | 2 | model_bug 2 | 0 |
| gcrs_m_4_w_5 (5) | 1 | 1093 | 3 (1048), 23 (1) | 0 / 8392 | 1 | 5 | model_bug 5 | 0 |
| gcrs_m_4_w_6 (6) | 1 | 1093 | 2 (1040), 62 (1) | 0 / 8328 | 1 | 6 | model_bug 6 | 0 |
| gcrs_m_4_w_7 (7) | 1 | 1171 | 2 (1040), 58 (1) | 0 / 8328 | 1 | 7 | model_bug 7 | 0 |
| gcrs_m_4_w_8 (8) | 1 | 1025 | 0 (1024), 88 (1) | 8192 / 8 | 1 | 4 | model_bug 4 | 0 |

Read the table by the fifth column. A block whose threads all arrive completes its barrier
instances ("fired"). A block with exited threads never does: its warps are released by the
hardware, and the dump records the instance as "released short" (arrivals below the expected
128). `gcrs_m_1_w_4` is the control: the same code shape, `size` a multiple of the grid, and no
thread exits. All 20,480 of its instances fire, and it has no report. Every launch that has a
single released-short instance carries `tv_violation` and reports. For w = 4 and 8 that is only
the partial last block. The exit column counts only blocks that appear in the event stream.
Blocks in which every thread returns record nothing and do not matter (44 of
`gcrs_m_1_w_5`'s 1,093 blocks, 52 for `w_6`, 130 for `w_7`).

## 3. Source mapping (step 3)

The binary was built with `-lineinfo`; `nvdisasm --print-line-info` on its `main.sm_89.cubin`
(`setup/t3_crs/lineinfo.txt.gz`) maps every reported pc. crs-cuda has 20 kernels,
`gcrs_m_<m>_w_<w>_coding_dotprod` for m = 1..4, w = 4..8 (`kernels.cu`), launched with 128
threads per block (`MAX_THREAD_NUM`). Each has the shape of `gcrs_m_1_w_5` (lines 53-103):

```
int worksize_perblock = blockDim.x / w * w;          // 125 for w = 5, 126 for w = 6 and 7
if (threadIdx.x >= worksize_perblock) return;         // lines 71-73  SASS 0x00a0  @P0 EXIT
if (idx >= size) return;                              // lines 75-77  (same EXIT)
for (i = 0; i < k; i++) {
  shared_data[threadIdx.x] = *(in + i*size + idx);   // line 88      0x03a0  STS.64
  __syncthreads();                                    // line 90      0x03b0  BAR.SYNC 0x0
  for (j = 0; j < w; j++)                             // line 93-95   0x03c0-0x04c0  LDS.64
    result ^= ... & shared_data[group_offset + j];
  __syncthreads();                                    // line 98      0x04d0  BAR.SYNC 0x0
}
```

With w = 5, 6 or 7, 2-3 threads of every 128-thread block return before the first barrier;
with w = 4 or 8 only the threads past `size` in the last block do.

## 4. Verdict per pair (steps 4 and 6)

**What the 155 reports are** (measured, `setup/t3_crs/triage.json`). The 50 vector-clock
dumps hold 349 kernel-level RACE verdicts. Collapsed per kernel, they are 159 distinct
(kernel, pc pair) reports. The harness dedup key (pc pair + space) ignores the kernel, and pcs
are function-relative, so four pc pairs that occur in two kernels each are merged: 155. Every
one of the 159 is a shared-memory pair between the store `shared_data[threadIdx.x] = …` (line
L of its kernel, `STS.64`) and a load `shared_data[group_offset + j]` (line L+7, `LDS.64`, one
pc per unrolled `j`):

| kernel | store line | RAW store→load pairs (model_bug) | WAR load→next-iteration store pairs: model_bug / structural |
|---|---|---|---|
| gcrs_m_1_w_5 | kernels.cu:88 | 15 | 10 / 5 |
| gcrs_m_1_w_6 | kernels.cu:140 | 18 | 12 / 6 |
| gcrs_m_1_w_7 | kernels.cu:192 | 7 | 0 / 0 |
| gcrs_m_1_w_8 | kernels.cu:244 | 4 | 0 / 0 |
| gcrs_m_2_w_4 | kernels.cu:299 | 6 | 4 / 2 |
| gcrs_m_2_w_5 | kernels.cu:357 | 5 | 0 / 0 |
| gcrs_m_2_w_6 | kernels.cu:415 | 6 | 0 / 0 |
| gcrs_m_2_w_7 | kernels.cu:473 | 7 | 0 / 0 |
| gcrs_m_2_w_8 | kernels.cu:531 | 4 | 0 / 0 |
| gcrs_m_3_w_4 | kernels.cu:591 | 2 | 0 / 0 |
| gcrs_m_3_w_5 | kernels.cu:653 | 5 | 0 / 0 |
| gcrs_m_3_w_6 | kernels.cu:715 | 6 | 0 / 0 |
| gcrs_m_3_w_7 | kernels.cu:777 | 7 | 0 / 0 |
| gcrs_m_3_w_8 | kernels.cu:839 | 4 | 0 / 0 |
| gcrs_m_4_w_4 | kernels.cu:901 | 2 | 0 / 0 |
| gcrs_m_4_w_5 | kernels.cu:965 | 5 | 0 / 0 |
| gcrs_m_4_w_6 | kernels.cu:1029 | 6 | 0 / 0 |
| gcrs_m_4_w_7 | kernels.cu:1093 | 7 | 0 / 0 |
| gcrs_m_4_w_8 | kernels.cu:1157 | 4 | 0 / 0 |
| **total** (159 distinct kernel-level pairs) | | 120 | 26 / 13 |

**Per pair, the decision is (c) for all 159: a detector bug.** Each pair is ordered in every
schedule by a `__syncthreads()` in the source:
* **RAW store (L) → load (L+7), same iteration.** The barrier at line L+2 separates them, and
  no thread returns between the store and the barrier. The static leg agrees: R1 finds
  `BAR.SYNC` dominating the load (strength `block`). So the verdict matrix puts all 120 in the
  `model_bug` cell: the engine saw them race, but a static proof says they cannot.
* **WAR load (L+7) → store (L) of the next iteration.** The `__syncthreads()` that closes the
  loop body separates them. 26 are `model_bug` (R1 proves them). 13 are `structural`: R1 finds
  no dominating barrier on some path between the unrolled loop's last load and the peeled
  next-iteration store in `gcrs_m_1_w_5`, `gcrs_m_1_w_6` and `gcrs_m_2_w_4`. That is a
  limitation of the static rule on this unrolled shape (read from the report's `strength
  none`; the CFG was not examined further). The pairs are still ordered by the barrier in the
  source.
* Neither is a genuine race (a): the only unordered window is the one the model invents by
  never completing the barrier. Nor is either (b): nothing outside the model is needed. The
  barrier is in the trace and the engine processes it, but it waits for arrivals that cannot
  come (§5).

**The "did race in the run" check (step 6).** The engine's race records behind the reports
name their threads. 41,767,544 are intra-warp and 2,673,620 cross-warp in the same block; none
cross blocks. This is what the source implies: thread `t` reads the `w` elements of its
coding group `[group_offset, group_offset + w)`, written by its neighbours, which are mostly
in the same warp. So the threads really are different threads, as the source says. What is
false is "unordered": the records exist only because the barrier between the two accesses
never completed in the model. The earlier attribution in `eval/BASELINES.md` §P9, "pair
mis-attribution in the engine + plain conflicting accesses that did race in the run", is
superseded. The pairs are attributed correctly (exact pc-pair records), and they did not race.

**Scalar-clock (7 reports).** These are the WAR pairs of `gcrs_m_1_w_5` (`kernel_6`: five
load pcs against the peeled store `0x970`) and `gcrs_m_2_w_4` (`kernel_21`: two against
`0xb50`). Each is the same pair, in the same launch, that vector-clock classifies
`structural` (checked pair by pair in `triage.json`). The static leg has no proof for them, and the offline barrier pass that could
order them has the same assembly bug: its instances in those launches never fire either
(the scalar-clock detail records 0 fired / 6,294 released short for `kernel_6`). Why
`gcrs_m_1_w_6`'s six structural pairs do not surface in scalar-clock mode was not
investigated: its scalar-clock dump yields no RACE verdict at all.

## 5. Why: a barrier the model never completes (the root cause, both modes)

A thread that has exited no longer takes part in a CTA-wide `bar.sync`: the barrier completes
when every thread that has not exited has arrived, which is why crs-cuda neither hangs nor
computes wrong codes. The detector's barrier assembly does not know this. `HbEngine` and
`hb_oracle.py` buffer the arrivals of a plain `__syncthreads()` per `(block, bar_index)` and fire
the instance once `thread_count`, or `block_thread_count` for a plain `__syncthreads()`, threads
have arrived. With 125 of 128 threads ever arriving, the instance never fires. The released
warps' next accesses then trip `TV-barrier-completion-order` — the engine records it in
`tv_violation` and continues ("verdict for this kernel is untrustworthy") — and every
store → barrier → load pair stays unordered in the engine's main clock, so it lands in
`hb_races`. The static leg proves those pairs ordered (R1: the `BAR.SYNC` dominates the load),
which is exactly the verdict matrix's `model_bug` cell: "R1/R2 claim every-schedule
race-freedom yet it raced -> a soundness bug in R1/R2 or a trace/CFG misalignment". Here the
bug is in the engine, not in R1.

The collector already reports the exits: `BlockExitCallback`
(`nv-compute/gpu_src/gpu_patch_pc_dependency.cu`) writes one `MemoryType::BlockExit` record per
warp with the exiting lanes in `active_mask`. Nothing downstream uses it: `HbEngine::process`
skips it (`if (a.type == MemoryType::BlockExit) continue;`) and `hb_collect_events` does not
serialize it ("block exit is not a happens-before event").

**Reproducer** (step 5 — here a failing test for class (c), not a race):
`python/testdata/barrier_exited_threads.cu` (30 lines, the `w = 5` kernel with k = 2, 2 blocks)
and `python/test_barrier_exit.py` (not part of the green set; needs a GPU). Job 287973 (c24,
RTX 4060 Ti, sm_89, the installed library `785d27a28b6456c5`): **3 passed, 4 xfailed (strict)** —
passed: exactly 125 of 128 threads per block appear in the event stream; the scalar-clock
verdict is CLEAN; engine and oracle agree (both wrong the same way, TV checks off);
xfailed: the engine's `hb_races` is not empty, the dump carries `tv_violation`, the
vector-clock verdict is RACE, the strict oracle raises `TV-barrier-completion-order`.
Independent checks on the same binary: Compute Sanitizer **racecheck: 0 hazards**,
**synccheck: 0 errors** (a `__syncthreads()` with exited threads is legal).

## 6. Proposal (not implemented: the brief asks for a proposal for class (c))

Make block-barrier assembly exit-aware, in `HbEngine`, `hb_oracle.py` and
`sync_dominance.barrier_only_pairs` in one commit (engine = oracle stays the gate):
1. `hb_collect_events` serializes `BlockExit` records as `{"type": "exit", "block", "warp",
   "active_mask", "pc", "seq"}` (additive; readers that do not know the type must skip it, so the
   oracle and the offline pass change in the same commit).
2. Per block, a set of exited threads. The expected participant count of a plain
   `__syncthreads()` instance becomes `block_thread_count - |exited(block)|`; an explicit
   `thread_count` (`bar.sync id, count`) is left as is.
3. On an exit record, re-check the block's pending instances: one whose arrivals now reach the
   reduced count fires (`sync_group` of the arrived threads). This covers a whole warp exiting
   after the other warps arrived.
4. Exited threads never join a barrier: their earlier accesses stay unordered against the
   post-barrier accesses of others, which is the hardware's semantics (their writes are not
   released by a barrier they never reached).

**Offline check of the effect** (measured, job 288290 on c26, 519 s,
`setup/t3_exit_prototype.py` → `setup/t3_crs/exit_prototype.json`). This is not the fix. In
crs-cuda every exiting thread returns before its first access, so there the threads of a
block that ever appear in the event stream are exactly its non-exited threads. The check
gives each plain `__syncthreads()` event that count as its expected participants, the count
steps 2-3 would reach, and re-scores eight launches (one per `w` for m = 1, plus the three
launches with `structural` pairs and one more m = 2). For scalar-clock it runs
`sync_dominance.analyze` on the rewritten dump. For vector-clock it runs `hb_oracle` on the
rewritten dump, strict, with the trace-validity checks on, and substitutes its race records
for the engine's:

| launch | kernel | barrier events given a short count | scalar-clock RACE before → after | vector-clock RACE before → after |
|---|---|---|---|---|
| kernel_4 | gcrs_m_1_w_5 | 8,390 | 0 → 0 | 5 → 0 |
| kernel_6 | gcrs_m_1_w_5 | 25,170 | 5 → 0 | 25 → 0 |
| kernel_8 | gcrs_m_1_w_6 | 8,324 | 0 → 0 | 6 → 0 |
| kernel_10 | gcrs_m_1_w_6 | 24,972 | 0 → 0 | 30 → 0 |
| kernel_12 | gcrs_m_1_w_7 | 8,324 | 0 → 0 | 7 → 0 |
| kernel_16 | gcrs_m_1_w_8 | 2 | 0 → 0 | 4 → 0 |
| kernel_20 | gcrs_m_2_w_4 | 4 | 0 → 0 | 6 → 0 |
| kernel_21 | gcrs_m_2_w_4 | 6 | 2 → 0 | 10 → 0 |

Every report of the eight launches disappears in both modes, and the strict oracle raises no
`TV-barrier-completion-order`. That covers all 7 scalar-clock reports and 93 of the 349
vector-clock kernel-level verdicts. The other 42 launches have the same shape and were not
re-scored. The `structural` WAR pairs disappear too: once the barrier completes, the offline
pass (scalar-clock) and the oracle (vector-clock) order them. The static leg still has no
proof for them, but it no longer has to supply one.

Still unverified until implemented: the engine side of the fix, the exit records' route
through `hb_collect_events`, and exits that happen after a thread's first access, which the
proxy above cannot represent. Also unverified: `python/test_barrier_exit.py`'s four xfails
flipping (strict, so the markers must be removed in the same change), and no other kept
program changing (§7 bounds this). Cost: one set per block and a re-check on exit records.

## 7. How far it reaches in the corpus

`setup/t3_tv_scan.py` read the last 64 KiB of every vector-clock `kernel_N.json` in every
kept BeeGFS store (evcand, full-2026-09-22, t0-smoke, t0-smoke2, t8-fresh, t2-*; about 700
programs), where `HbEngine` writes `tv_violation` (`setup/t3_crs/tv_scan.tsv`). Two programs
carry one: **P9-crs-cuda** (46 of 50 kernels, `TV-barrier-completion-order`) and
**P4-graph-coloring-racy-small** (36 of 36). The latter occurs only in the RACEY build (the
norace build's kept vector-clock dumps have none), and that build deletes one
`__syncthreads()` (`ScoR/benchmarks/graph-coloring/gcol_kernel.cu:118-121`), after which threads
can reach different barriers (`if (*base < n_t_last) continue;`) — consistent with barrier
divergence, not investigated further. Its label is racy and its verdict RACE either way. So in
the kept corpus the exited-thread bug decides one verdict: crs-cuda's.

## 8. For the paper

> crs-cuda (HeCBench) is race-free, as SuperCollider labels it, and cuVein's reports on it are
> false positives from one modelling error. crs-cuda's kernels return 2-3 threads of each
> 128-thread block (those outside a whole coding group), or the threads past the input in the
> last block, before a loop of paired `__syncthreads()`. A thread that has exited no longer
> takes part in a CTA barrier, so the hardware releases the barrier once the remaining threads
> arrive. cuVein's barrier assembly waits for every thread of the block, never completes those
> instances, and leaves each store → barrier → load pair on `shared_data` unordered. Its
> trace-validity check flags 46 of the 50 launches, and the static rule proves 146 of the 159
> reported pairs barrier-ordered (the `model_bug` cell). Counting exited threads out of a
> barrier's expected participants, from the block-exit records the collector already emits,
> removes every report of the launches we re-scored in both modes (offline check). In the kept
> corpus this bug decides no other verdict.

(146 = 120 RAW + 26 WAR `model_bug` pairs; the 13 `structural` pairs have no static proof, and
the barrier orders them too. "Removes every report": 8 of the 50 launches were re-scored, §6.)

## 9. Commands (all on the NCSU ARC cluster, worktree `/home/fzheng4/wt-T3` @ `81b4262`)

| step | command | where / job | output |
|---|---|---|---|
| 1-3 | `sbatch eval/baselines/setup/t3_crs.sh`: `parallel.py analyze` of `P9-crs-cuda` from the T0 store `full-2026-09-22`, both modes; `setup/t3_crs_triage.py`; `eval/triage.py`; `cuobjdump -xelf` + `nvdisasm --print-line-info` | c36 (287905: failed at start, no `/usr/bin/time` on the node), c26 (287909: analyze 4267 s, triage 2542 s) | `eval/results/t3-crs/`, `eval/baselines/confirm_t3-crs/`, `setup/t3_crs/{triage.json,triage.md,detail_*.json,lineinfo.txt.gz}` |
| 2 | `.env/bin/python eval/triage.py setup/t3_crs/detail_vector-clock.json setup/t3_crs/detail_scalar-clock.json` (after the `hb_class: None` fix, §10) | login node | `setup/t3_crs/triage_py.txt` |
| 4 | `.env/bin/python eval/baselines/setup/t3_crs_tables.py` and the per-kernel / per-pair roll-ups in §2 / §4 (from `triage.json`) | login node | this report |
| 5 | `sbatch -p rtx4060ti16g eval/baselines/setup/t3_repro.sh`: builds `python/testdata/barrier_exited_threads.cu`, runs `python/test_barrier_exit.py`, racecheck, synccheck | c24, RTX 4060 Ti sm_89, installed library `785d27a28b6456c5` (287973) | `build_logs/t3-repro-287973.log` |
| 6 | `sbatch eval/baselines/setup/t3_exit_prototype.sh` | c26 (288290, 519 s) | `setup/t3_crs/exit_prototype.json` |
| 7 | `srun -p normal -c2 .env/bin/python eval/baselines/setup/t3_tv_scan.py > setup/t3_crs/tv_scan.tsv` | a `normal` node, interactive | `setup/t3_crs/tv_scan.tsv` |

The green set was not re-run for this task: no detector code changes. `sanalyzer/` and
`nv-compute/` are untouched, and `python/` gains only a test file and its test data. The
branch adds a report, evaluation scripts and a crash fix in `eval/triage.py`. `python/test_barrier_exit.py` is not in the
green set (its four strict xfails document the bug).

## 10. What remains unverified, and other findings

* **The fix itself** (§6): not implemented. The offline check covers 8 of 50 launches and uses
  "threads seen" as the non-exited set, which is exact only for exits before any access.
* **Why `gcrs_m_1_w_6`'s six `structural` WAR pairs do not surface in scalar-clock mode**
  (§4): not investigated.
* **The R1 miss on the peeled loop tail** (§4): the 13 `structural` WAR pairs mean R1 finds no
  dominating barrier between the unrolled loop's last loads and the next iteration's peeled
  store. Read from the reports' `strength none`; the CFG was not examined. Once the barrier
  completes it does not matter here, but it is a static-leg limitation worth a regression
  case.
* **`P4-graph-coloring-racy-small`** also carries `TV-barrier-completion-order` (§7). It is
  consistent with barrier divergence in the racy build, not investigated.
* **The harness dedup key ignores the kernel** (§4): pcs are function-relative, so in a
  multi-kernel binary equal pc pairs of different kernels are merged (159 → 155 here). The
  same holds for `classify_fp_causes.py`'s `lookup()`, which types a report's endpoints from
  the first CFG cluster containing both pcs, possibly another kernel's. That script also files
  every vector-clock `model_bug` as `RC3-attribution`. For crs-cuda the cause is this barrier
  bug, so `eval/BASELINES.md`'s "RC3+other" for P9 is superseded by this report, and the rows
  are not regenerated here.
* **`eval/triage.py` crashed** on a scalar-clock detail (`hb_class` is `None` there). Fixed
  on this branch (`str()` in the one format call).
* **`run_cuvein._analyze_reports` tries the dots in name order**, and `sync_dominance.analyze`
  parses the kernel JSON before it finds that a dot does not align. crs-cuda's store has five
  empty dots (14 bytes each) that sort before `main.sm_89.dot`, so each of its 100 kernel
  JSONs (both modes) was parsed six times: the harness re-score took 4267 s (job 287909).
  `t3_crs_triage.py` tries dots largest first. The harness itself is unchanged (a T7 item).
