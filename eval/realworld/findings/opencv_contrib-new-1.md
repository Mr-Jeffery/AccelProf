# opencv_contrib-new-1: warp-synchronous histogram reduction in CUDA HOG (`compute_hists_kernel_many_blocks`)

Status: class (a), intra-warp, DR (plain store vs volatile load) and volatile-volatile steps (SC in PTX source, DR as
compiled); formal only on the traced sm_89 build. Triage: `eval/realworld/candidates/triage/opencv_contrib-new-1.md`.

## 1. The accesses

opencv/opencv_contrib eca97a4adb2fa32afc82478947d7f049fce57ee1, `modules/cudaobjdetect/src/cuda/hog.cu`:

```
163   float* hist = hists + patch_size * (cell_y * blockDim.z * cncells_block_y + cell_x + block_x * cncells_block_x) + cell_thread_x;
166   for (int bin_id = 0; bin_id < cnbins; ++bin_id)
167       hist[bin_id * block_patch_size * nblocks] = 0.f;
191       hist[bin.x * block_patch_size * nblocks] += gaussian * interp_weight * vote.x;
192       hist[bin.y * block_patch_size * nblocks] += gaussian * interp_weight * vote.y;
196   volatile float* hist_ = hist;
197   for (int bin_id = 0; bin_id < cnbins; ++bin_id, hist_ += block_patch_size * nblocks)
199       if (cell_thread_x < patch_size/2) hist_[0] += hist_[patch_size/2];
200       if (cell_thread_x < patch_size/4 && (!((patch_size/4) < 3 && cell_thread_x == 0)))
201               hist_[0] += hist_[patch_size/4];
202       if (cell_thread_x == 0)
203           final_hist[...] =
204               hist_[0] + hist_[1] + hist_[2];
208   __syncthreads();
```

Default configuration (cell 8x8, block 2x2 cells): patch_size 12, threads_cell 16, `<<<grid, (32,2,4)>>>`; a cell is 16 lanes
of one warp, 12 active. SASS (traced build): L167 `STS [Rx], RZ`; L191/L192 `LDS`+`STS` (plain, e.g. `STS [R16], R21` at
0x1cc0); L199 `@!P4 LDS [R3]`, `@!P4 LDS [R14]` (0x1ed0), `@!P4 STS [R3]` (0x1f20); L201 `@P3 LDS [R3]`, `@P3 LDS [R15]` (0x1f60),
`@P3 STS [R3]` (0x1f90); L204 `@!P1 LDS [R3]`, `[R3+0x4]` (0x1fb0), `[R3+0x8]` (0x1fc0). Every volatile access is present
(8 LDS + 2 STS per bin, loop unrolled by 4 plus a remainder); none is `.STRONG`.

Three race pairs (all intra-warp):
- **R1 (DR)**: L191/L192 (and L167) plain store of column t+6 by lane t+6 vs L199 volatile load `hist_[6]` by lane t, t < 6.
- **R2**: L199 volatile store `hist_[0]` by lane t+3 vs L201 volatile load `hist_[3]` by lane t, t < 3.
- **R3**: L201 volatile store by lanes 1, 2 vs L204 volatile loads `hist_[1]`, `hist_[2]` by lane 0.

## 2. Thread pair and why nothing orders it

Block (1,8,0), threadIdx.y = 0, threadIdx.z = 1 (one warp): thread (6,0,1) stores column 6 at L192, thread (0,0,1) loads
it at L199 (R1); thread (3,0,1) stores `hist_[3]` at L199, thread (0,0,1) loads it at L201 (R2) — the pairs racecheck shows.
Same warp, same block. The only barrier is L208, after all of them; there is no `__syncwarp`, shuffle or fence in
L153-L206, and `volatile` only keeps the accesses in memory, it orders nothing between threads. PTX §8.7: unordered
conflicting accesses, at least one weak in R1 (DR); in R2/R3 both are volatile (strong at the PTX level: SC; plain LDS/STS on
sm_89: DR per D20, hence DETECTED-AS-DR for the SC component).

## 3. Trace evidence

`eval/results/realworld_t21c/attrib/opencv_contrib-new-1-buggy.json`, scalar-clock, kernel
`void cv::cuda::device::hog::compute_hists_kernel_many_blocks<4>(int, cv::cuda::PtrStep<float>, cv::cuda::PtrStep<unsigned char>, float, float*, int, int, int, int, int, int)`,
kernel_0.json, 64 reports, all RACE / DR: R1 49 (L191->L199 20, L192->L199 20, e.g. 0x1cc0 -> 0x1ed0; L167->L199 9, the
`other_reports.csv` rows, e.g. 0x5f0 -> 0x1ed0), R2 5 (0x1f20 -> 0x1f60 and the unrolled copies), R3 10 (0x1f90 -> 0x1fb0/0x1fc0
...). `recall.csv`: DR component DETECTED (L191-192 vs L199), SC component DETECTED-AS-DR (L199 vs L201). Trace edges of all
64 pc pairs: 41,580 `intra_warp`, 0 intra-block. racecheck: 166,335 "Warp Level Programming" warnings, 0 errors.

## 4. Reproducer

`eval/realworld/findings/repro/opencv_contrib-new-1/` (`build.sh`, `expected.md`). The kernel is L134-L208 with the
indexing, L167, L191/L192, the volatile reduction and L208 unchanged, launched with compute_hists()'s grid/block/smem for the
default 64x128 HOG. Trimmed: the gaussian/interp weight (L170-L189, registers only; votes added unweighted so every bin is an
exact integer), PtrStep (raw pointer + pitch), the copy-out L210-L233 (final_hist copied directly). Host reference: the vote
sums of each cell's 12x12 patch.
- `repro.cu` (55 lines), `repro_fixed.cu` (59 lines), `repro_perturb.cu` (59 lines). All compile (CUDA 13.4, sm_89); not run.
- Perturbation on the writer side of R2: mode 1 `if (cell_thread_x == 3) __nanosleep(ns);` just before L199 (faithful);
  mode 2 lane 3 runs the reduction in its own noinline instance (forced divergence). Predictions: mode 1 correct, mode 2 wrong.

## 5. Minimal fix (against eca97a4a)

```diff
--- a/modules/cudaobjdetect/src/cuda/hog.cu
+++ b/modules/cudaobjdetect/src/cuda/hog.cu
@@ -142,6 +142,9 @@
             const int cell_y = threadIdx.y;
             const int cell_thread_x = threadIdx.x & (threads_cell - 1);
 
+            // lanes of this warp that take part in the reduction (all lanes are still present here)
+            const unsigned mask = __ballot_sync(0xffffffff,
+                blockIdx.x * blockDim.z + block_x < img_block_width && cell_thread_x < patch_size);
             if (blockIdx.x * blockDim.z + block_x >= img_block_width)
                 return;
 
@@ -194,9 +197,12 @@
 
                 //reduction of the histograms
+                __syncwarp(mask);
                 volatile float* hist_ = hist;
                 for (int bin_id = 0; bin_id < cnbins; ++bin_id, hist_ += block_patch_size * nblocks)
                 {
                     if (cell_thread_x < patch_size/2) hist_[0] += hist_[patch_size/2];
+                    __syncwarp(mask);
                     if (cell_thread_x < patch_size/4 && (!((patch_size/4) < 3 && cell_thread_x == 0)))
                             hist_[0] += hist_[patch_size/4];
+                    __syncwarp(mask);
                     if (cell_thread_x == 0)
```
The full-mask ballot assumes the block size is a multiple of 32 (true for the default configuration, 256 threads; other
configurations not checked). No WAR exists in this reduction (no step stores what a later step of the same row loads from
another lane before its own store), so one sync per step suffices. `repro_fixed.cu` places the ballot after the L145 return,
which is equivalent for the default configuration (a warp is one (y, z) and returns as a whole).

## 6. Already known?

- Issues/PRs: GitHub search in opencv/opencv_contrib (issues: "HOG cuda compute_hists warp synchronous volatile race
  syncwarp racecheck", "cuda HOG wrong descriptors Volta Turing Ampere race condition shared memory"; PRs: "syncwarp OR warp
  synchronous OR Volta OR racecheck") and opencv/opencv (issues: "cuda hog compute_hists race shared memory syncthreads
  volatile warp"): nothing about this reduction (hits: unrelated CUDA bugs, e.g. opencv_contrib#4211, opencv#5567). Web search
  "opencv cudaobjdetect hog.cu compute_hists_kernel_many_blocks volatile warp race syncwarp": nothing; the closest is a 2014
  report of a missing `__syncthreads` in CUDA Canny (https://code.opencv.org/issues/3562), a different kernel.
- Commits (`~/incoming/realworld/cand/opencv_contrib.git`): `git log -- modules/cudaobjdetect/src/cuda/hog.cu` = 8a6ea82e
  (2022-10-15, texture objects), a7417334 (2019-08-08), 82733fe5 (2018-09-18, move from opencv);
  `git log --all -S'volatile float* hist_'` = 82733fe5 only; `git grep __syncwarp` in cudaobjdetect: none. The only earlier
  sync fix in this file is 5a72be08 (normalize_hists, cross-warp; corpus record opencv-1, per the record, not re-checked).
- Nothing found describes this race.

## 7. Skeptic's strongest objection and the PTX answer

Objection: "Deliberately warp-synchronous, a cell never crosses a warp, HOG tests pass on Volta through Ada; formal only."
On this build that is right about behaviour: the reduction is one predicated, branch-free (apart from uniform loop control)
instruction stream for the 12 active lanes, the accumulation stores precede it in program order, and a sleep inserted on one
lane is bracketed by BSSY/BSYNC. **No wrong output can be produced by perturbing timing in this code as compiled**
(prediction; mode 1 tests it). The PTX answer: nothing orders lanes of a warp without `bar.warp.sync`; the plain stores of
L191/L192 are not even volatile, so a compiler may legally keep them in registers or sink them past the volatile loads of
other lanes' columns; and once the warp diverges (mode 2), the histogram is wrong.

## 8. Results

TO BE RUN (coordinator, after GPU approval):
- native `repro`, `repro_fixed`, `repro_perturb 0/1/2`: TO BE RUN
- cuVein scalar-clock on `repro` (expected R1-R3) and `repro_fixed` (expected clean under PTX; a report would be the BRA.CONV
  model gap described in `expected.md`): TO BE RUN
- racecheck on `repro`: TO BE RUN
- perturbation outcome: TO BE RUN
