# pcl-new-1: warp-synchronous `Warp::reduce` in PCL GPU normal estimation (`normal_3d.cu`, `warp.hpp`)

Status: class (a), intra-warp; DR (plain vs volatile) and volatile-volatile pairs (SC in PTX source, DR as compiled); formal
only on the traced sm_89 build. Covers all 657 reports (triage groups P1-P9 in `eval/realworld/candidates/triage/pcl-new-1.md`),
including the 381 "other" reports, which are the same race at other step boundaries of the same kernel.

## 1. The accesses

PointCloudLibrary/pcl 66e1d0ea8cc3fa54820eb38e18ad0adac6345b94.
`gpu/utils/include/pcl/gpu/utils/device/warp.hpp`:
```
145  static __device__ __forceinline__ void reduce(volatile T* buffer, BinOp op) {
148      T val =  buffer[lane];
150      if (lane < 16) {
152          buffer[lane] = val = op(val, buffer[lane + 16]);
153..156      ... buffer[lane + 8], + 4, + 2, + 1 ...
161  static __device__ __forceinline__ T reduce(volatile T* buffer, T init, BinOp op) {
164      T val = buffer[lane] = init;
166      if (lane < 16) {
168          buffer[lane] = val = op(val, buffer[lane + 16]);
169..172      ... + 8, + 4, + 2, + 1 ...
174      return buffer[0];
```
`gpu/features/src/normal_3d.cu` (`NormalsEstimator::operator()`, one warp per point, `__shared__ float cov_buffer[6][257]`):
```
101  volatile float *buffer = &cov_buffer[0][threadIdx.x - lane];
103  c.x = Warp::reduce(buffer, c.x, plus());   // 104: c.y, 105: c.z
108  //nvcc bug workaround. if comment this => c.z == 0 at line: float3 d = fetch(*t) - c;
109  __threadfence_block();
115      cov_buffer[i][tid] = 0.f;
124      cov_buffer[0][tid] += d.x * d.x;        // ... 129: cov_buffer[5][tid] += d.z * d.z;
132  Warp::reduce(&cov_buffer[0][tid - lane], plus());   // ... 137: row 5
139  volatile float *cov = &cov_buffer[0][tid-lane];
141      cov[lane] = cov_buffer[lane][tid-lane];   // lane < 6
148  Eigen33 eigen33(&cov[lane]);  150-152: tmp/vec_tmp/evecs = rows 1/2/3;  155: eigen33.compute(...)   // lane 0 only
```

The two oracle pairs (SASS of the traced build, all plain LDS/STS, every volatile access kept):
- DR: L124 plain `STS [R6.X4]` at 0x19b0 (lane l+16 stores its partial cov00; ptxas keeps the `+=` in a register and stores once)
  vs warp.hpp:152 volatile `LDS [R18.X4+0x40]` at 0x1ac0 (lane l loads `buffer[l+16]`; line info shows the `plus` functor,
  normal_3d.cu:64).
- SC (source level): warp.hpp:164 `STS [R21]` at 0x9d0 (lane 16 stores `buffer[16] = c.x`) vs warp.hpp:168 `LDS [R6.X4+0x40]`
  at 0xa00 (lane 0 loads `buffer[16]`).
The other boundaries (P2-P4, P6-P9): consecutive reduces on row 0 (L174 load vs next L164 store), the c.z reduce vs L115/L124
across the fence, row reduces vs the L141 gather, and the reduces/gather vs lane 0's Eigen33 (which reuses rows 0-3 as
`mat_pkg`, `tmp`, `vec_tmp`, `evecs`).

## 2. Thread pair and why nothing orders it

Block 0, warp 0 (racecheck shows the same with threads 112/96, lanes 16/0 of warp 3): lane 16 stores `buffer[16]` at
warp.hpp:164, lane 0 loads `buffer[16]` at :168 (SC pair); lane 16 stores `cov_buffer[0][16]` at L124, lane 0 loads it at
warp.hpp:152 (DR pair); lane 5 loads `buffer[0]` (c.z) at :174, lane 0 stores `cov_buffer[0][0] = 0` at L115 (P3); lane 1
stores `cov[1]` at L141, lane 0 reads it as `mat_pkg[1]` at eigen.hpp:215 (P9). Same warp, same block. There is no
`__syncthreads`, `__syncwarp`/`bar.warp.sync` or shuffle anywhere in the kernel (no `__syncwarp` under `gpu/` at the pin).
`__threadfence_block()` (fence.sc.cta, SASS `MEMBAR.SC.CTA`) sits between P3's accesses but orders a load in lane 5 before a
store in lane 0 only in executions where lane 5's fence comes first in Fence-SC order; with the opposite order nothing relates
them, so the race remains (class (a), not (b)). PTX §8.7: unordered conflicting accesses.

## 3. Trace evidence

`eval/results/realworld_t21c/attrib/pcl-new-1-buggy.json`, scalar-clock, kernel
`pcl::device::EstimateNormalsKernel(pcl::device::NormalsEstimator)` (`_ZN3pcl6device21EstimateNormalsKernelENS0_16NormalsEstimatorE`),
kernel_0.json: 657 reports, all RACE / DR, 0 ordered; DR oracle pair 0x19b0 -> 0x1ac0 (and the five rows 0x19c0..0x1a00 ->
their reduces, 30 reports, P5), SC oracle pair 0x9d0 -> 0xa00 (P1, 60 reports over the three centroid reduces). Groups and
counts: P1 60, P2 42, P3 12, P4 17, P5 30, P6 84, P7 8, P8 330, P9 74. `recall.csv`: DR component DETECTED, SC component
DETECTED-AS-DR. Trace edges of the reported pc pairs: 967,000 `intra_warp`, 0 intra-block. racecheck: 4,465,057 "Warp Level
Programming" warnings, 0 errors; first hazard Write Thread (112) warp.hpp:164 / Read Thread (96) warp.hpp:168 (via
normal_3d.cu:64), block (0,0,0).

## 4. Reproducer

`eval/realworld/findings/repro/pcl-new-1/` (`build.sh`, `expected.md`). Kernel = normal_3d.cu L73-L141 with both
Warp::reduce overloads copied (same statements), launched as computeNormals() (CTA 256, one warp per point), 2,000 points x
40 neighbours. Kept: the centroid reductions, the fence, cov zeroing/accumulation, the six row reductions, the L141 gather.
Trimmed: Warp/PtrStep plumbing (the `%laneid` asm kept), float3 operators written per component, the size<3 exit (sizes are
40), and the Eigen33 solve (lane 0 writes the six cov values instead), so P8/P9 are not exercised. Host reference in double.
- `repro.cu` (59 lines), `repro_fixed.cu` (60), `repro_perturb.cu` (60). All compile (CUDA 13.4, sm_89); not run.
- Perturbation on the writer side of the SC pair: mode 1 `if (lane == 16) __nanosleep(NS);` before the c.x reduce
  (faithful); mode 2 lane 16 enters the c.x reduce through its own noinline instance (forced divergence). Predictions: mode 1
  correct, mode 2 wrong.

## 5. Minimal fix (against 66e1d0ea)

```diff
--- a/gpu/utils/include/pcl/gpu/utils/device/warp.hpp
+++ b/gpu/utils/include/pcl/gpu/utils/device/warp.hpp
@@ static __device__ __forceinline__ void reduce(volatile T* buffer, BinOp op)
                 unsigned int lane = laneId();
-                T val =  buffer[lane];
+                __syncwarp();
+                T val =  buffer[lane];
 
                 if (lane < 16)
-                {
-                    buffer[lane] = val = op(val, buffer[lane + 16]);
-                    buffer[lane] = val = op(val, buffer[lane +  8]);
-                    buffer[lane] = val = op(val, buffer[lane +  4]);
-                    buffer[lane] = val = op(val, buffer[lane +  2]);
-                    buffer[lane] = val = op(val, buffer[lane +  1]);
-                }
+                    for (int k = 16; k >= 1; k >>= 1)
+                    { val = op(val, buffer[lane + k]); __syncwarp(0xffff); buffer[lane] = val; __syncwarp(0xffff); }
+                __syncwarp();
             }
@@ static __device__ __forceinline__ T reduce(volatile T* buffer, T init, BinOp op)
                 unsigned int lane = laneId();
-                T val = buffer[lane] = init;
+                __syncwarp();
+                T val = buffer[lane] = init;
+                __syncwarp();
 
                 if (lane < 16)
-                { ... same five steps ... }
+                    for (int k = 16; k >= 1; k >>= 1)
+                    { val = op(val, buffer[lane + k]); __syncwarp(0xffff); buffer[lane] = val; __syncwarp(0xffff); }
+                __syncwarp();
                 return buffer[0];
--- a/gpu/features/src/normal_3d.cu
+++ b/gpu/features/src/normal_3d.cu
@@ -108,2 +108,2 @@
                 //nvcc bug workaround. if comment this => c.z == 0 at line: float3 d = fetch(*t) - c;
-                __threadfence_block();
+                __syncwarp();
@@ -140,2 +140,3 @@
                 if (lane < 6)
                     cov[lane] = cov_buffer[lane][tid-lane];
+                __syncwarp();
```
(The warp.hpp hunks are schematic: positioned by function, original whitespace not reproduced; the exact fixed code is in `repro_fixed.cu`.) The entry
`__syncwarp()` of each reduce orders the callers' plain stores (L115, L124-L129) and the previous reduce's L174 loads before
the reduce; the exit one orders the reduce before L141 and the next statement; the one after L141 orders the gather before
lane 0's Eigen33 accesses (P8/P9 also need the rows' reduce stores before Eigen's writes, covered by the exit syncs). Caveat:
for `size < 3` only lane 0 returns at L90; full-mask `__syncwarp` with an exited lane was not checked. The alternative used by
PCL for its octree (PRs 4306, 4313) is to replace the shared-memory reduction by `__shfl_down_sync`.

## 6. Already known?

- Issues: GitHub issue search in PointCloudLibrary/pcl ("gpu normal estimation warp reduce volatile race syncwarp Volta wrong
  normals", "volatile shared memory warp reduction gpu features kinfu syncwarp independent thread scheduling"). Checked hits:
  #5846 "GPU normal estimation does not work with CUDA 12" (closed; cause: Thrust 2.x symbol clash in the octree sort, not
  this), #5731 "[pcl::gpu::NormalEstimation] Unexpected Results" (closed together with #5846, same thread), #2419, #6219 (not
  related), #5638 (open since 2023-03-23, no reply): asks whether `scan_warp` in `gpu/octree/src/utils/scan_block.hpp` needs
  `__syncwarp()` — the same idiom in a different file, not this kernel.
- PRs: "syncwarp OR shfl_sync OR warp synchronous OR volatile" in PointCloudLibrary/pcl: #4306 "[gpu] Replace volatile shared
  memory with shfl_sync in KNNSearch" (merged 2020-08-11, "Fix for distance calculation issue caused by the use of volatile
  shared memory"), #4313 (same for ApproxNearestSearch, merged 2020-08-18), #4146 (octree radiusSearch). None touches
  gpu/features or warp.hpp.
- Web search "PCL gpu normal_3d.cu Warp::reduce volatile nvcc bug workaround threadfence_block": nothing specific.
- Commits (`~/incoming/realworld/cand/pcl.git`, blobless): `git log -- gpu/features/src/normal_3d.cu`: 1d8fd52a0 (2025-08-19
  spelling), fc8fb1163 (2024-05-24), 2019 clang-tidy/numeric_limits commits, 0b39f15ad (2012-01-23, file move);
  `git log -- warp.hpp`: 81ac552fb (2019-06-13, `__CUDA_ARCH__` checks), 0b39f15ad; `-S'__threadfence_block'` on normal_3d.cu:
  0b39f15ad only (the workaround predates the move).
- Nothing found describes this race in gpu/features. PCL fixed the same idiom in its octree in 2020 after observing wrong
  distances (#4306), which is evidence that the idiom has produced wrong output in this code base on some toolchain/GPU, but
  not in this kernel. The L108 comment records a wrong `c.z` at the P3 boundary in 2012 or earlier, attributed to nvcc.

## 7. Skeptic's strongest objection and the PTX answer

Objection: "Classic warp-synchronous code with volatile; the warp is converged; PCL's tests and users never saw wrong normals
on Volta+; formal only." On this build the behaviour matches the objection: each `if (lane < 16)` block is bracketed by
`BSSY/BSYNC`, so lanes 16-31 wait for 0-15 before the next cross-lane access; within the block the steps are straight-line;
after L141 lanes 1-31 `EXIT` and lane 0 runs Eigen33 alone; and a sleep inserted on one lane is itself bracketed by
BSSY/BSYNC. **No wrong output can be produced by perturbing timing in this code as compiled** (prediction; mode 1 tests it).
The PTX answer: without `bar.warp.sync` the lanes are unordered and the compiler may schedule them diverged; volatile does not
order threads; the plain L115/L124 stores could legally move relative to other lanes' volatile loads (the L108 comment shows
that something of that kind happened once and was patched with a fence, which does not order the pair under PTX); and once
the warp is diverged (mode 2) the covariance is wrong.

## 8. Results

TO BE RUN (coordinator, after GPU approval):
- native `repro`, `repro_fixed`, `repro_perturb 0/1/2`: TO BE RUN
- cuVein scalar-clock on `repro` (expected P1-P7 groups) and `repro_fixed` (expected clean under PTX; a report would be the
  BRA.CONV model gap in `expected.md`): TO BE RUN
- racecheck on `repro`: TO BE RUN
- perturbation outcome: TO BE RUN
