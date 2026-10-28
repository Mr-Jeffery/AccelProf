# droidslam-new-1-2: cross-warp race on the shared frame indices `ix`/`jx` in `frame_distance_kernel` (new)

Status: class (a), DR, cross-warp within one block; not lock-step dependent; wrong output expected under perturbation.
Found among the "other" reports of droidslam-new-1 (triage group G3). Not in the corpus record.

## 1. The accesses

princeton-vl/DROID-SLAM 2dfd39f0dcad44012ca7bbb8aa70b55edbfa9c99, `src/droid_kernels.cu`, `frame_distance_kernel` (L527-L666):

```
542   __shared__ int ix;
543   __shared__ int jx;
554   if (thread_id == 0) { ix = static_cast<int>(ii[block_id]); jx = static_cast<int>(jj[block_id]); ... }
588     __syncthreads();                       // inside for (int n=0; n<1; n++)
595     GPU_1D_KERNEL_LOOP(k, ht*wd) {
611       Xi[3] = disps[ix][i][j];             // read of ix (and again at L630)
646     }
648     if (threadIdx.x == 0) {
649       int tmp = ix;
650       ix = jx;
651       jx = tmp;
652     }
654     __syncthreads();
```

- Read: `ix` by every thread, hoisted by ptxas before the pixel loop: `LDS.128 R4, [RZ]` at 0x8b0 (line info L608; it loads
  ix, jx, fx, fy, offsets 0..15; R4 = ix feeds the disps row offset `IMAD R23, R4, c[0x0][0x18c]`). Plain.
- Write: thread 0's swap, `@!P2 STS.64 [RZ], R4` at 0x1840 (L651; writes ix and jx), after thread 0's own loop and before
  `BAR.SYNC` at 0x1850 (L654). Plain.

## 2. Thread pair and why nothing orders it

Block b, thread 0 (warp 0) writes `ix` at L650/L651; thread 32 (warp 1, any of warps 1-7) reads `ix` at L611 (SASS 0x8b0).
Different warps, same block. The only barriers around are L588 (before both) and L654 (after the write, and after the read
in program order of thread 32 only if thread 32 has already passed 0x8b0). Nothing forces thread 32's read to happen before
thread 0's write: if warp 0 finishes its 12 pixel iterations before warp 1 executes the ~60 instructions from the L588
barrier to 0x8b0, warp 1 reads `ix = jj[b]` and computes the distance of the wrong frame pair. Under PTX §8.7 the read and the
write are conflicting, both weak, and unordered: a data race. The loop runs once (`n < 1`), so the swap has no effect on the
result except through this race (it looks like a leftover from a version with two passes).

## 3. Trace evidence

`eval/results/realworld_t21c/attrib/droidslam-new-1-buggy.json`, scalar-clock, kernel `frame_distance_kernel(...)`,
kernel_0.json: 1 report, a_pc 0x8b0 (LDS.128, droid_kernels.cu:608) -> b_pc 0x1840 (STS.64, droid_kernels.cu:651), shared,
WAR, `RACE`, `conflict_class` DR; it is the row `0x8b0,0x1840` of `other_reports.csv`. Trace edges in the store
(`cuvein_traces/realworld-2026-10-t21c/droidslam-new-1-buggy/scalar-clock/kernel_0.json`): `0x8b0 -> 0x8b0` 168 intra_block,
`0x8b0 -> 0x17c0` (thread 0's `LDS.64 [RZ]`, L649) 6 intra_block, `0x17c0 -> 0x1840` 12 intra_thread, i.e. other warps' reads
of `[0]` and thread 0's swap with no barrier between them (one per block, 6 blocks). The three native runs of the target
(`eval/realworld/native/droidslam-new-1-buggy.json`) print identical distances (no sign of the race without perturbation;
whether those values are the race-free ones was not checked separately). racecheck (CUDA 13.4) reported 0 errors for that run.

## 4. Reproducer

`eval/realworld/findings/repro/droidslam-new-1-2/` (`build.sh`, `expected.md`). The kernel keeps thread 0's load of ix/jx,
one barrier (L563/L574/L588 merged: nothing between them touches ix/jx), the `n < 1` loop, the pixel loop reading
`disps[ix][i][j]`, the unsynchronized swap (L648-L652) and the L654 barrier, with the target driver's sizes (4 frames 48x64,
6 pairs, 256 threads). Trimmed: pose/projection math (registers only) and the blockReduce tail (replaced by a per-thread copy
of `total[]`, so the warpReduce race of droidslam-new-1 is not in this reproducer). Frame f holds the value f+1, so a thread
that read the swapped index is detected exactly.
- `repro.cu` (56 lines), `repro_fixed.cu` (57 lines, one `__syncthreads()` before the swap), `repro_perturb.cu` (60 lines:
  mode 1 makes warps 1-7 sleep 10 x `__nanosleep(1 ms)` after the barrier, followed by a compiler-only barrier
  `asm volatile("" ::: "memory")` so the `ix` load stays after the sleep). All compile (CUDA 13.4, sm_89); not run. The SASS
  of `repro` has the same shape as the target: hoisted `LDS R4, [RZ]`, swap `@!P1 STS.64 [RZ]` before the `BAR.SYNC`.

## 5. Minimal fix (against 2dfd39f0)

```diff
--- a/src/droid_kernels.cu
+++ b/src/droid_kernels.cu
@@ -645,6 +645,7 @@
       }
     }
 
+    __syncthreads();
     if (threadIdx.x == 0) {
       int tmp = ix;
       ix = jx;
```
Equivalent alternative: delete the swap (L648-L652), which has no effect with `n < 1`.

## 6. Already known?

- Issues/PRs: GitHub issue search in princeton-vl/DROID-SLAM ("frame_distance wrong distance race condition __syncthreads",
  "warpReduce volatile shared memory race syncwarp Volta"): 0 results. Web search (see droidslam-new-1): nothing.
- Commits: `git log --all -S'ix = jx' -- src/droid_kernels.cu` = 6463912 (2021-09-01, "monocular release") only: the swap and
  `n < 1` are in the first release and never changed.
- Nothing found describes this race.

## 7. Skeptic's strongest objection and the PTX answer

Objection: "The window is absurd: warp 0 must run 12 pixel iterations (global loads, divisions, sqrt) while warp 1 has not
yet executed ~60 arithmetic instructions after a barrier; no scheduler does that, so it never happens; and the swap is dead
code." Answer: PTX gives no fairness or progress-rate guarantee between warps of a block, and nothing orders the read before
the write; preemption, a debugger, a profiler replay or simply a heavier first iteration can stretch the window, and the
perturbation (mode 1) realizes it directly with a delay that does not touch the racing accesses. Unlike the warpReduce race,
this one does not depend on intra-warp lock-step at all. The impact is a wrong frame distance for the affected pairs
(callers of `droid_backends.frame_distance` not checked). The objection that the code is dead is an argument for the fix
(delete or fence the swap), not against the race.

## 8. Results

TO BE RUN (coordinator, after GPU approval):
- native `repro`, `repro_fixed`, `repro_perturb 0/1`: TO BE RUN
- cuVein scalar-clock on `repro` (expected: shared WAR LDS [0] -> STS.64 [0], cross-warp) and `repro_fixed` (expected clean): TO BE RUN
- racecheck on `repro`: TO BE RUN
- perturbation outcome (mode 1, predicted wrong output in all 6 blocks): TO BE RUN
