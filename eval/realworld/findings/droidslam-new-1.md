# droidslam-new-1: warp-synchronous `warpReduce` in DROID-SLAM (`src/droid_kernels.cu`)

Status: class (a), intra-warp, formal only on the traced sm_89 build (no wrong output from timing perturbation of the
upstream code; wrong output only under a forced divergent schedule). Triage: `eval/realworld/candidates/triage/droidslam-new-1.md` (G1).

## 1. The accesses

Repository princeton-vl/DROID-SLAM, pinned commit 2dfd39f0dcad44012ca7bbb8aa70b55edbfa9c99 (origin HEAD when re-checked).

```
45 __device__ void warpReduce(volatile float *sdata, unsigned int tid) {
46   sdata[tid] += sdata[tid + 32];
47   sdata[tid] += sdata[tid + 16];
48   sdata[tid] += sdata[tid +  8];
49   sdata[tid] += sdata[tid +  4];
50   sdata[tid] += sdata[tid +  2];
51   sdata[tid] += sdata[tid +  1];
52 }
...
62   if (tid < 32) warpReduce(sdata, tid);      // in blockReduce, between __syncthreads() at L60 and L63
```

- Write: L46 `sdata[tid] = ...` by lane 16 (and generally lane t+k writes sdata[t+k] in every step), SASS `STS [R13.X4+0x50]`
  at 0x1960 (call from L657; also 0x1be0 from L658, 0x1e60 from L659).
- Read: L47 `sdata[tid + 16]` by lane 0, SASS `LDS [R13.X4+0x90]` at 0x1980 (0x1c00, 0x1e80).
- Both are `ld.volatile`/`st.volatile` in PTX source; on sm_89 they are plain `LDS`/`STS` (no `.STRONG`). The compiler kept
  every volatile access: per call 12 LDS (sdata[tid] and sdata[tid+k] for each step) and 6 STS.
- Same idiom for every step pair L46..L51: 20 reported pc pairs per call (5 RAW, 15 WAR), 3 calls.

## 2. Thread pair and why nothing orders it

`frame_distance_kernel<<<num_pairs, 256>>>`, any block, warp 0: thread 16 executes L46 (`sdata[16] += sdata[48]`), thread 0
executes L47 (`sdata[0] += sdata[16]`). RAW on `sdata[16]`; also WAR, thread 0's L47 load of sdata[16] vs thread 16's L47
store of sdata[16]. Same warp, same block. Between them there is no `__syncthreads()` (L60 before, L63 after), no
`__syncwarp()`/`bar.warp.sync`, no shuffle and no fence. Under PTX §8.7 the lanes of a warp are not ordered by being in one
warp, so the conflicting accesses are unordered: a race (SC under PTX at the source level since both are volatile; DR as
compiled to plain LDS/STS on sm_89, the class the frozen detector reports, D20).

## 3. Trace evidence

`eval/results/realworld_t21c/attrib/droidslam-new-1-buggy.json`, scalar-clock, kernel `frame_distance_kernel(...)`
(`_Z21frame_distance_kernelN5torch10headeronly6detail27GenericPackedTensorAccessor...`), kernel_0.json: 60 reports of 67 in
this group, all `RACE`, `conflict_class` DR, `strength` none: the oracle pair 0x1960 -> 0x1980 (STS L46 -> LDS L47, RAW) and
0x1be0 -> 0x1c00, 0x1e60 -> 0x1e80 for the other two calls, plus the other 57 step pairs (pcs 0x1960..0x1aa0, 0x1be0..0x1d20,
0x1e60..0x1fa0). `recall.csv`: SC component DETECTED-AS-DR. Trace edges for these pcs are `intra_warp` only. racecheck (same
binary, CUDA 13.4): 18,591 "Warp Level Programming" warnings, 0 errors; first hazard: Write Thread (16,0,0) L46 / Read
Thread (0,0,0) L47, block (0,0,0).

## 4. Reproducer

`eval/realworld/findings/repro/droidslam-new-1/` (`build.sh`, `expected.md`). warpReduce/blockReduce copied verbatim
(L45-L64); the kernel keeps frame_distance_kernel's reduction tail (`accum[thread_id]` written, `__syncthreads(); blockReduce(accum);`,
thread 0 reads `accum[0]`). Trimmed: pose/projection math and the pixel loop (L539-L656), replaced by known integers in
`accum[]`. 4,096 blocks, exact expected sums.
- `repro.cu` (51 lines), `repro_fixed.cu` (48 lines: `__syncwarp()` between each step's load and store),
  `repro_perturb.cu` (55 lines, modes 0/1/2). All three compile with CUDA 13.4 for sm_89 (checked 2026-10-25); not run.
- Perturbation (writer side of L46 -> L47): mode 1 inserts `if (tid == 16) __nanosleep(ns);` at the top of warpReduce
  (faithful). Mode 2 makes lane 16 enter warpReduce through its own noinline instance, so the warp diverges for the whole
  reduction (a schedule PTX permits). Predictions in `expected.md`: mode 1 correct, mode 2 wrong.

## 5. Minimal fix (against 2dfd39f0)

```diff
--- a/src/droid_kernels.cu
+++ b/src/droid_kernels.cu
@@ -45,8 +45,4 @@
 __device__ void warpReduce(volatile float *sdata, unsigned int tid) {
-  sdata[tid] += sdata[tid + 32];
-  sdata[tid] += sdata[tid + 16];
-  sdata[tid] += sdata[tid +  8];
-  sdata[tid] += sdata[tid +  4];
-  sdata[tid] += sdata[tid +  2];
-  sdata[tid] += sdata[tid +  1];
+  float v = sdata[tid];
+  for (int k = 32; k >= 1; k >>= 1) { v += sdata[tid + k]; __syncwarp(); sdata[tid] = v; __syncwarp(); }
 }
```
All 32 lanes of warp 0 call warpReduce (`tid < 32`), so the full mask is valid. The load-sync-store-sync split is needed
because every lane also stores in every step (WAR within a step). A `__shfl_down_sync` reduction after the L46 step is the
alternative (no shared traffic, as PCL did for its octree in PR 4306).

## 6. Already known?

- Issues/PRs: GitHub issue search scoped to princeton-vl/DROID-SLAM ("warpReduce volatile shared memory race syncwarp Volta",
  "frame_distance wrong distance race condition __syncthreads"): 0 results. Web search "DROID-SLAM droid_kernels.cu warpReduce
  volatile syncwarp race": nothing on DROID-SLAM (only generic material, e.g. https://developer.nvidia.com/blog/using-cuda-warp-level-primitives/,
  https://forums.developer.nvidia.com/t/warps-not-executing-in-lock-step/269773).
- Commits (`~/incoming/realworld/cand/DROID-SLAM.git`, 27 commits): `git log -- src/droid_kernels.cu` = c252db7 (2025-05-05
  multi-gpu inference), 7234a93 (2021-09-09), 6463912 (2021-09-01 monocular release); `git log --all -S'warpReduce'` and
  `-S'volatile float *sdata'` = 6463912 only. No sync-related commit.
- Nothing found describes this race. The record notes the same warpReduce in many DROID-SLAM forks (not checked here).

## 7. Skeptic's strongest objection and the PTX answer

Objection: "Textbook warp-synchronous reduction; warp 0 executes it converged on every GPU, `volatile` forces the memory
traffic, results are correct, so this is formal only." On this build the objection is right about behaviour: the six steps
are straight-line LDS/STS inside one `if (tid < 32)` taken by the whole warp, there is no divergence point between the steps,
and a `__nanosleep` inserted on one lane is bracketed by BSSY/BSYNC, so the lanes reconverge before the next step. **No wrong
output can be produced by perturbing timing in this code as compiled** (prediction; mode 1 tests it). The PTX answer: the
memory model gives no ordering between lanes of a warp without `bar.warp.sync`, and since Volta (independent thread
scheduling) the compiler and hardware may run the lanes of a warp diverged; CUDA 9 made implicit warp-synchronous code
unsupported for exactly this reason. Mode 2 shows that once the warp is diverged, the same code gives a wrong sum. Note also
that the PTX-correct fix does not change the executed SASS much: CUDA 13.4 lowers each `__syncwarp()` to `BRA.CONV` around a
call to a WARPSYNC stub, which a converged warp skips.

## 8. Results

TO BE RUN (coordinator, after GPU approval):
- native `repro`, `repro_fixed`, `repro_perturb 0/1/2`: TO BE RUN
- cuVein scalar-clock on `repro`: TO BE RUN (expected: the L46..L51 intra-warp pairs)
- cuVein scalar-clock on `repro_fixed`: TO BE RUN (expected clean under PTX; see `expected.md` on BRA.CONV, a report here
  would be a detector-model gap)
- racecheck on `repro`: TO BE RUN (expected: Warp Level Programming warnings at L46..L51)
- perturbation outcome (modes 1 and 2): TO BE RUN
