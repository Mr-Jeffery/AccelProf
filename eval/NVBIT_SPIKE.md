# T13 — NVBit feasibility spike: atomics recorded after execution, with the value read

Branch `study/nvbit-spike` (based on `cuVein` ebc464f, the T3b + T9 merge). Run
2026-09-28 on node **c53** (`rtx4060ti16g`, RTX 4060 Ti 16 GB, sm_89, driver
**580.105.08**, CUDA 13.3 V13.3.73, host g++ 8.5.0 for the NVBit tools), one
allocation (SLURM job 292740). Measurement only: the detector, the collector and the
proof are unchanged. Every NVBit run was in a clean environment (no `YOSEMITE_*`,
no Sanitizer collector in the process).

## Summary (for the paper)

Recording atomics after execution, with the value they read, **is feasible on this
toolchain**. NVBit 1.8 loads under driver 580 / CUDA 13.3 on sm_89, although its README
limits support to drivers ≤ 575. A tool that reads an `ATOM*` instruction's
destination register at `IPOINT_AFTER` returned the correct old value in every test:
8/8 sequential adds, 256/256 per-lane adds (a permutation of 0..255), and 1,760
contended lock critical sections in which every successful CAS, failed CAS and
unlocking `atomicExch` read exactly the value coherence order implies. Reading the
register at the next instruction's `IPOINT_BEFORE` works equally well.

With the values as ground truth, the Sanitizer's view (one record per atomic at
issue) inverts coherence order on the matrix-multiplication lock idiom:

| contending warps | hand-offs where the successful CAS was recorded before the unlock it read from |
|---|---|
| 2 | 0 of 155 |
| 4 | 4 of 315 (1.3 %) |
| 16 | 52 of 1,275 (4.1 %) |

These are 5 runs each, with the value read at `IPOINT_AFTER`. Every inversion lies
inside overlapping issue windows, so the "executes before the thread's next record"
half of A2 held in all runs. The rates were measured under NVBit's own timing (see
the unverified list).

Cost relative to native:
- `atom_after`, unoptimised (one global `atomicAdd` and one channel push per lane per
  record): 2.1× on the rtraw litmus, 16× on matrix-multiplication (small input), 427×
  on the large input. The large input is the only kernel-dominated point; the small
  runs are dominated by start-up.
- The Sanitizer HB collector (scalar-clock): 7.8×, 10.7× and 134× on the same three.
- NVBit's stock `mem_trace`: 2.1×, 5.1× and 127×.

So `atom_after` costs 0.27×, 1.5× and 3.2× the current collector.

## Answers to the three questions

| question | answer | evidence |
|---|---|---|
| Does NVBit run on this toolchain? | **yes, 1.8**; the pinned 1.7.1 does not | §2 |
| Does the after-point yield an atomic's old value correctly? | **yes**, at `IPOINT_AFTER` and at the next instruction's `IPOINT_BEFORE` | §3 |
| What does it cost? | 127× native for stock `mem_trace` and 427× for the unoptimised `atom_after` on the one kernel-dominated input; Sanitizer HB is 134× there | §5 |

The Sanitizer patching API has no after-instruction hook. In
`$CUDA_HOME/compute-sanitizer/include/sanitizer_patching.h` (Compute Sanitizer
2026.2.1.0), `sanitizerPatchInstructions(instructionId, module, callbackName)` takes
no insertion-point argument. All 44 `Sanitizer_InstructionId` values (1 = BLOCK_ENTER
… 44 = TMA_STORE) are single callbacks; the only "after" wording belongs to BLOCK_EXIT
("called after all user code has executed") and the `*_RELEASE` barrier variants. The
memory-access callback `SanitizerCallbackMemoryAccess(userdata, pc, ptr, accessSize,
flags, pData)` documents: "If the access is an atomic, the pointer will be NULL", so
the callback never sees the value an atomic reads.

## 1. Inventory

- **NVBit releases** (from the GitHub API on the login node, into `~/incoming/nvbit/`):
  - Newest: **v1.8**, published 2026-04-06, `nvbit-Linux-x86_64-1.8.tar.bz2`, md5
    `8ef39c4745e83ed5d6207de4b22449fb`. It is identical to the tarball iGUARD already
    uses (`eval/baselines/setup/tools/`).
    - README: SM 3.5–12.1, GCC ≥ 8.5, CUDA ≥ 12.0, **CUDA driver ≤ 575.xx**.
    - Release notes: TMA support (alpha), `getSassBinary()`, green contexts, CUDA 13.2
      headers.
  - Pinned by the submodule: **1.7.1**, md5 `9bb3ccdc81ff2164a2998228a7d17b49`. README:
    SM 3.5–9.2, **driver ≤ 555.xx**.
- **Both READMEs exclude driver 580**, so both were tried.
- **`nv-nvbit` submodule** (`AccelProf/nv-nvbit` @ 23b721b):
  - AccelProf's NVBit front end (`libnv-nvbit.so`, `accelprof -d nvbit`), with
    backends `app_analysis`, `app_metric`, `mem_trace` and `roofline_flops`.
  - It bundles NVBit **1.7.1** (`core/libnvbit.a`, `NVBIT_VERSION "1.7.1"`;
    `bin/install-nvbit` downloads 1.7.1).
  - Its `mem_trace` backend already traces memory, but only at `IPOINT_BEFORE`
    (`nvbit_add_call_arg_mref_addr64`) and with no register values.
  - It is not built in this checkout (`lib/` has no `libnv-nvbit.so`). It was not run
    here: it would load the same 1.7.1 core that fails in §2.

## 2. Load test (unchanged `tools/mem_trace` on `race_interblock_fence_rtraw`)

Script: `eval/nvbit_spike/build_mem_trace.sh`, then `eval/nvbit_spike/load_test.sh`.
Raw output: `eval/nvbit_spike/results/load_test/`.

| NVBit | builds with nvcc 13.3 | loads under driver 580.105.08 | trace produced |
|---|---|---|---|
| 1.8 | yes | **yes**, rc 0 | **yes**: 10 warp records (see below) |
| 1.7.1 | yes | **no**, rc 1: `ASSERT FAIL: nvbit_imp.cpp:1099:void Nvbit::module_loaded(CUcontext, const void*, size_t, CUmodule): FAIL !(header)` | no |

The 1.8 trace has 10 warp records from the 2 CTAs: `ATOMG.E.EXCH.STRONG.GPU`,
`LDG.E.STRONG.SYS`, `STG.E`, `STG.E.STRONG.SYS`. The only warning 1.8 prints is its
standard banner line ("Do not call CUDA memory allocation in nvbit_at_ctx_init()"),
which is the tool template's concern and not a failure. The banner also says
`NO_EAGER_LOAD = 1` (lazy module loading is the default in 1.8). Everything below
uses 1.8.

## 3. Value test (`atom_after`)

Source: `eval/nvbit_spike/atom_after/`. It is NVBit 1.8's `tools/mem_trace` with the
instrumentation and the receiver replaced (~150 lines).

- **Atomics.** Every `ATOM*` (not `RED`) gets two calls:
  - `aa_before` at `IPOINT_BEFORE`: pc, address (`nvbit_add_call_arg_mref_addr64`),
    guard predicate.
  - `aa_value` at `IPOINT_AFTER`: the first `REG` operand before the `MREF`, which is
    the destination (`nvbit_add_call_arg_reg_val`).
- **Other memory instructions** get an `IPOINT_BEFORE` record. That makes each
  thread's "next record", the end of an atomic's window in the Sanitizer's view,
  known.
- **Ordering.** Each call takes its sequence number from one global `atomicAdd`
  counter and pushes one record per lane. The records of all threads, before and
  after, therefore sit in one total order.
- **Fallback.** `ATOM_VALUE_AT=next` reads the same register at the next
  instruction's `IPOINT_BEFORE`.

Test kernel: `eval/nvbit_spike/atom_values.cu`. It lives in this directory, not
`python/testdata/`, because the brief restricts changes to `eval/nvbit_spike/` and
this report. SASS: `results/atom_values.sass.txt`. Analyzer:
`eval/nvbit_spike/analyze_atom.py`. Driver: `run_values.sh 5`. Table:
`summarize.py` → `results/values_summary.md`.

**Compiler finding.** ptxas **warp-aggregates** `atomicAdd(&x, 1)` whenever the address
is a compile-time constant:
- Part 2 (`&x`, all lanes) compiles to one `@P0 ATOMG.E.ADD` per warp. The leader adds
  `popc(mask)` and the other lanes get their values by `SHFL`.
- A per-lane increment with the same constant address becomes a `VOTE.ANY` full-warp
  test plus a `SHFL.UP` scan and one leader `ATOMG`.

So the hardware performs 8 RMWs for 256 source-level atomics. A value-recording
collector sees the hardware RMWs, which is what coherence order is defined on. Part 4
was added to test per-lane values: the address is `&x + off[tid]` with `off[] = 0`
loaded from memory, which compiles to a single un-aggregated per-lane `ATOMG`.

| part | kernel | expected | `IPOINT_AFTER` | next-instr `BEFORE` |
|---|---|---|---|---|
| 1 | 1 warp, lane 0, 8 × `atomicAdd(&x,1)` (8 unrolled `ATOMG`, destination registers reused) | 0..7 in order | **0..7 in order** | **0..7 in order** |
| 2 | 8 warps × 32 lanes, `atomicAdd(&x,1)` (aggregated) | 8 leader RMWs reading a permutation of {0,32,…,224} | **ok** (trace order 0,160,32,64,96,128,224,192) | **ok** (the 248 non-leader lanes are predicated off; their `N` records are dropped as designed) |
| 4 | 8 warps × 32 lanes, per-lane `ATOMG` | permutation of 0..255 | **ok** | **ok** |
| 3 | lock idiom (below), 2/4/16 warps × 16 acquisitions × 5 runs | see below | **ok**, 30/30 runs | **ok**, 30/30 runs |

Part 4 also shows that each warp's 32 lanes occupy one **contiguous** block of the
coherence order (for example, warp 5 read 0..31 and warp 0 read 64..95 in the `after`
run). Only the order of whole warps differs from trace order.

**Part 3 (the matrix-multiplication lock idiom).**
- Lane 0 of each warp runs `while (atomicCAS(&lock, 0, tag) != 0); __threadfence();`,
  then a plain critical section, then `__threadfence(); atomicExch(&lock, 0)`. The SASS
  is the idiom's: `ATOMG.E.CAS.STRONG.GPU`, `MEMBAR.SC.GPU; CCTL.IVALL`, then
  `ATOMG.E.EXCH.STRONG.GPU`.
- One deviation from the brief: the CAS writes a tag unique per critical section,
  not `1`. A failed CAS's old value then names the critical section it ran in, and the
  Exch's old value names the one it ends. With the critical-section order the program
  prints, this pins S_k and E_k to coherence positions 2k and 2k+1, and every failed
  CAS strictly between them.
- Checked in all 30 runs:
  - every successful CAS read 0;
  - every Exch read the tag of its own critical section, and its thread's preceding
    CAS was the successful one;
  - every failed CAS read a live tag, never 0;
  - S/E positions form exactly 0, 1, …, 2n−1, so successful CASes and unlocks
    alternate.
- Sanity check of the method: for every pair ordered by the values, the earlier RMW's
  BEFORE seq precedes the later RMW's AFTER seq. There were **0 violations** in about
  3.5·10⁸ cross-warp pairs checked (both read points, all parts).

No stale value was observed on the long-latency global atomics at `IPOINT_AFTER`. The
likely reason is that NVBit's trampoline saves the registers, which waits on the
scoreboard; this is inferred, not checked in the instrumented SASS.

## 4. A2 in vivo (part 3, Sanitizer's view = the BEFORE positions only)

Definitions:
- **Trace order** = order of the BEFORE seqs. This is what the Sanitizer collector
  records.
- **Window** of an RMW = [its BEFORE seq, the thread's next memory record).
- **Overlap**: the later-issued RMW of a pair is issued inside the earlier one's
  window.
- **Inverted**: coherence order, where the values determine it, is opposite to trace
  order.

Pairs counted: same location (the lock word), different warps. Failed CASes of the same
critical section are not ordered against each other and are never counted. The last
column is the T9 shape (`matrix-multiplication-norace-small`): the successful CAS
S_{k+1} is recorded before the unlock E_k it read from.

| warps | value at | runs | crit. sections | failed CAS | cross-warp pairs | overlapping | inverted | inverted, non-overlapping | S_{k+1} recorded before E_k |
|---|---|---|---|---|---|---|---|---|---|
| 2 (1 × 2) | after | 5 | 160 | 165 | 11,750 | 320 | 0 | 0 | **0 / 155** |
| 4 (1 × 4) | after | 5 | 320 | 1,955 | 504,170 | 5,461 | 11 | 0 | **4 / 315 (1.3 %)** — 1, 0, 1, 1, 1 |
| 16 (4 × 4) | after | 5 | 1,280 | 39,835 | 168,161,867 | 533,628 | 140 | 0 | **52 / 1,275 (4.1 %)** — 10, 11, 5, 15, 11 |
| 2 | next | 5 | 160 | 165 | 11,750 | 320 | 0 | 0 | 0 / 155 |
| 4 | next | 5 | 320 | 1,948 | 500,828 | 5,462 | 10 | 0 | 2 / 315 (0.6 %) |
| 16 | next | 5 | 1,280 | 40,930 | 177,205,381 | 562,648 | 184 | 0 | 48 / 1,275 (3.8 %) |

Inverted pairs by type, in the form "X recorded first, Y first in coherence":

| warps, value at | S<trace E | F<trace S | E<trace F | F<trace E | S<trace F | F<trace F (different k) |
|---|---|---|---|---|---|---|
| 4, after | 4 | 4 | 3 | — | — | — |
| 16, after | 52 | 41 | 28 | 7 | 9 | 3 |

What this says about A2 and D15:
1. **Overlapping windows are common and inversions are rare, but not negligible, per
   hand-off.**
   - 16 warps: 0.03 % of overlapping lock-RMW pairs are inverted, but 4 % of lock
     hand-offs record the acquiring CAS before the release it read from.
   - 4 warps: 1.3 % of hand-offs.
   - 2 warps: none in 155.
   - Under the trusting gate every RMW is a release and an acquire. An `S<trace E`
     inversion therefore makes the engine derive S_{k+1} → E_k instead of
     E_k → S_{k+1}: it both drops the real hand-off edge (the T9 false positive) and
     manufactures the reverse one (the missed-race risk named in D15).
2. **The other half of A2 held.** No inversion occurred between non-overlapping windows
   (0 in every configuration). The "executes before the thread's next record"
   premise, which D15's `a2_uncertain` flag relies on, was never contradicted.
3. **Part 2 and part 4 (atomic counters, 8 warps issuing at once):**
   - Part 2: 5 of 28 warp pairs recorded in the opposite order to coherence.
   - Part 4: 4 of 28 at `IPOINT_AFTER` (1 of 28 at `next`), counted as 4,096 and 1,024
     lane pairs.
   - These are all overlapping. Non-hand-off atomics invert far more often, but they
     only matter to HB when they are used as synchronisation.

Against D15's wording, "A2 holds when RMW windows on a location do not overlap" is
consistent with every run. Whether the rate is "not negligible" is a judgement call:
it is zero at 2 contending warps and 1–4 % of hand-offs at 4–16. By D15's own rule,
that argues for the offline window count over the kept dumps and the `a2_uncertain`
column.

## 5. Cost

Script: `eval/nvbit_spike/cost.sh 3`, plus `cost.sh 1 large`. Logs: `results/cost.txt`,
`results/cost_large.txt`.
- Binaries are copied to node-local `/tmp`.
- NVBit tool output goes to `/dev/null`: formatting cost included, disk excluded.
- The Sanitizer collector writes its kernel JSON to node-local disk.
- "Sanitizer HB" = `accelprof -t pc_dependency_analysis -n 1` with
  `YOSEMITE_HB_TRACE=1 YOSEMITE_HB_MODE=scalar-clock`, the harness-built atomic-scope
  sidecar, and the installed runtime (VERSION ebc464f). It covers collection only, with
  no offline `sync_dominance` analysis.
- It needs `/opt/ohpc/pub/compiler/gcc/12.4.0/lib64` on `LD_LIBRARY_PATH` (GLIBCXX_3.4.29
  and 3.4.30); without it the collector fails to load.

Minimum wall time over the runs (all runs in the logs):

| program | native | Sanitizer HB | `mem_trace` | `atom_after` | `atom_after` / Sanitizer HB |
|---|---|---|---|---|---|
| `race_interblock_fence_rtraw` (3 runs) | 0.156 s | 1.215 s (7.8×) | 0.326 s (2.1×) | 0.327 s (2.1×) | 0.27× |
| `matrix-multiplication_norace`, small input (3 runs) | 0.164 s | 1.760 s (10.7×) | 0.830 s (5.1×) | 2.637 s (16.1×) | 1.5× |
| `matrix-multiplication_norace`, large input (1 run) | 0.232 s | 31.18 s (134×) | 29.40 s (127×) | 98.97 s (427×) | 3.2× |

Record volume:
- Sanitizer dump on the large input: 9.8 GB, 7.67 M `hb_events`.
- On the small input: 246 MB and 189,306 events for the Sanitizer, against 180 k warp
  records for `mem_trace` and 7.9 M lane records for `atom_after` (6.8 M of them
  atomic BEFORE/AFTER).

One run per configuration is not enough for tight ratios. The small-program rows are
dominated by process and CUDA start-up (rtraw's kernel is 2 × 1 threads), so they bound
fixed cost only. The large-input row is the one kernel-dominated point, and it is a
single run.

`atom_after` is deliberately unoptimised: a global `atomicAdd` and a channel push per
lane per record, and records for every memory instruction. `mem_trace` pushes one
record per warp with no counter and runs at the Sanitizer collector's speed (0.94×). A
collector that records per warp and takes one sequence number per warp instruction
should land near `mem_trace` plus the AFTER calls on atomics only; that is an
estimate, not measured.

## 6. Blockers and limits found

1. **Support status.** NVBit 1.8 runs on driver 580 but its README says ≤ 575, so a
   collector on it rests on an unsupported combination until NVIDIA updates the table.
   The `nv-nvbit` submodule's 1.7.1 core **does not load** (assert in
   `Nvbit::module_loaded`) and would have to move to 1.8.
2. **One tool per process.** NVBit and the Sanitizer collector cannot share a process.
   A value-recording collector means porting the whole HB collector to NVBit: barrier
   arrivals and counts, exit records (T3b), cp.async commit/wait (T1a), the atomic-scope
   sidecar path, `hb_events` serialisation. As D15 says, that is post-submission and
   forces a full re-evaluation.
3. **Warp-aggregated atomics.** Source-level `atomicAdd`s on a constant address become
   one leader RMW plus shuffles. The value recorded is the leader's, and the other
   lanes' results are computed in registers afterwards. This is correct for coherence
   order, but any per-lane attribution has to recognise the idiom.
4. **No value for `RED`.** `RED` has no destination register, so its coherence position
   cannot be read. It was excluded as the brief says, but a `RED` used as a release
   (a flag set by `atomicAdd` with the result unused) stays at its issue position.
5. **Not covered by `atom_after`:**
   - 64-bit atomics: only the low destination register is read;
   - shared-memory `ATOMS`: present in the code path, not exercised by the tests;
   - atomics whose destination is `RZ`: they are reported and skipped, and none
     occurred.

## 7. What remains unverified

- The inversion rates are measured **under NVBit's instrumentation**. Its per-record
  global `atomicAdd` and channel push change timing relative to the Sanitizer
  collector. The Sanitizer's own rate cannot be measured without values. The numbers
  are an order of magnitude for this lock on this GPU, not a property of the collector.
- The seq counter's coherence order is taken as global time across locations. PTX does
  not guarantee this without fences. It was checked empirically (0 execution-interval
  violations) but not proved.
- The rate on real applications: `matrix-multiplication` itself was traced by
  `atom_after` (`~/incoming/nvbit/work/matmul_atom_after.rec`, not committed, 7.9 M
  records), but its lock word holds only 0/1. Coherence order is not recoverable from
  its values alone, so no rate is given for it. The offline window count over the kept
  dumps (D15) is not done.
- Why the `IPOINT_AFTER` read is never stale (scoreboard wait in NVBit's trampoline) is
  inferred, not read off the instrumented SASS.
- The cost figures rest on at most 3 runs, and 1 for the only kernel-dominated input.
- Other architectures (sm_86, sm_90, sm_120) were not tried.

## Reproduce

```
# login node (GitHub reachable)
mkdir -p ~/incoming/nvbit && cd ~/incoming/nvbit
curl -sSL -o nvbit-Linux-x86_64-1.8.tar.bz2   https://github.com/NVlabs/NVBit/releases/download/v1.8/nvbit-Linux-x86_64-1.8.tar.bz2
curl -sSL -o nvbit-Linux-x86_64-1.7.1.tar.bz2 https://github.com/NVlabs/NVBit/releases/download/1.7.1/nvbit-Linux-x86_64-1.7.1.tar.bz2
mkdir -p 1.8 1.7.1 && tar -xjf nvbit-Linux-x86_64-1.8.tar.bz2 -C 1.8 && tar -xjf nvbit-Linux-x86_64-1.7.1.tar.bz2 -C 1.7.1

# one allocation for the day (no gres on this cluster: nodes are allocated whole)
salloc --no-shell -p rtx4060ti16g -x c54,c2 --nodes=1 --time=8:00:00 -J t13-nvbit   # -> job J
cd <checkout>
srun --jobid=J bash eval/nvbit_spike/build_mem_trace.sh    # step 2 build (1.8 and 1.7.1)
srun --jobid=J bash eval/nvbit_spike/load_test.sh          # step 2
srun --jobid=J bash eval/nvbit_spike/build_atom_after.sh   # step 3 build + SASS
srun --jobid=J bash eval/nvbit_spike/run_values.sh 5       # steps 3-4
python3 eval/nvbit_spike/summarize.py ~/incoming/nvbit/work/values
srun --jobid=J bash eval/nvbit_spike/cost.sh 3             # step 5
srun --jobid=J bash eval/nvbit_spike/cost.sh 1 large       # step 5, kernel-dominated point
scancel J
```
