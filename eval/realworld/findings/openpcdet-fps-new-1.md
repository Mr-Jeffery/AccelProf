# Finding openpcdet-fps-new-1: cross-iteration WAR on `dists_i[0]` in OpenPCDet's farthest point sampling (3 kernels)

**Status:** class (a) DR, observed as wrong output under compute-sanitizer racecheck's schedule. Verifier: not yet (step 5).
**Repository:** open-mmlab/OpenPCDet at `233f849829b6ac19afb8af8837a0246890908755` (equal to the fetched default branch at the T21c re-check; `pcdet/ops/pointnet2` unchanged).
**Lineage:** the same kernel and bug as mmcv-fps-new-1 and pointnet2pt-fps-new-1, inherited from the PointNet++ TF op (see "Common ancestry"). It is a distinct repository and a distinct finding, but the same bug pattern.

## 1. The two accesses

| kernel (file) | write (iteration j+1, thread 0) | read (iteration j, every thread) |
|---|---|---|
| `farthest_point_sampling_kernel<1024>` (`pcdet/ops/pointnet2/pointnet2_batch/src/sampling_gpu.cu`) | L147 `dists_i[tid] = besti;`: `STS [R0.X4+0x1000]` at pc 0xbd0 (3024) | L212 `old = dists_i[0];`: `LDS R7, [0x1000]` at 0x14b0 (5296) |
| `farthest_point_sampling_kernel<1024>` (`pointnet2_stack/src/sampling_gpu.cu`) | L71: `STS` at 0xbd0 | L136: `LDS [0x1000]` at 0x14b0 |
| `stack_farthest_point_sampling_kernel<1024>` (`pointnet2_stack/src/sampling_gpu.cu`) | L250: `STS [R18.X4+0x1000]` at 0x16e0 (5856) | L315: `LDS R9, [0x1000]` at 0x1fc0 (8128) |

- All accesses are plain shared 32-bit accesses.
- In each kernel, the barriers of the loop body are one after the store (L148 / L72 / L251) and one per reduction level (last: L209 / L133 / L312).
- After the read, the code branches back to the loop head with no `BAR`, `MEMBAR` or `WARPSYNC` (SASS of the built driver).

## 2. Thread pair and why nothing orders it

- Batch kernel, block b of 1024 threads: reader thread t ≥ 32 (racecheck: Read thread 191, warp 5) against Write thread 0.
- t reads `dists_i[0]` at L212 in iteration j after the last reduction barrier L209.
- Thread 0 goes from its own L212 through L213–L214, the loop increment and the distance loop L131–L145 (global memory only) to L146–L147, where it writes `dists_i[0]`. The first barrier on that path, L148, comes after the write.
- No `bar.sync` separates the two accesses, so there is no causality order under PTX §8.7.1. This is a data race between different warps of one block.
- The stack kernels have the identical structure (L136 vs L71; L315 vs L250).

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/openpcdet-fps-new-1-buggy.json`, scalar-clock)

- Three reports, one per kernel JSON: `kernel_0` (batch) `3024 STS :147 / 5296 LDS :212`, `kernel_1` (stack) `3024 :71 / 5296 :136`, `kernel_2` (stacked) `5856 :250 / 8128 :315`.
- All are WAR, `RACE`, `strength none`, `DR`. `n_race 3`, `n_sc 0`, no other reports.
- Reuse edges: `intra_block 421/102/96`, `intra_thread 87/22/28`, `intra_warp 0`.
- `hb_sync_pass` counts 508/124/124 (2 blocks × (M−2)).
- Racecheck (print limit 2000, all displayed hazards in the batch kernel): WAR `R@0x14b0/W@0xbd0` (1024 cross-warp errors, 20 same-warp warnings), RAW `W@0xbd0/R@0x14b0` (956).
- Driver's host-reference check, native (3 runs): 0 mismatches in all three kernels. Under racecheck: `507/512`, `124/128` and `124/128`.

## 4. Reproducer: `eval/realworld/findings/repro/openpcdet-fps-new-1/`

- **`repro.cu`** (57 lines): the batch kernel and `__update` copied from `pointnet2_batch/src/sampling_gpu.cu` L92–L216.
  - Trimmed: comments (including the commented-out `mag` check), blank lines, the launcher, and the two stack-file kernels (same race; not reproduced separately).
  - The unrolled reduction ladder is kept in full, two levels per line (whitespace-only joins).
  - Launch `<1024><<<2, 1024>>>` (as the launcher does for N = 2048), M = 256, `temp = 1e10`, integer coordinates in [1, 1000], with the host validity check (each pick must be a farthest point).
- **`repro_fixed.cu`**: one `__syncthreads()` after `idxs[j] = old;` (marked `FIX`).
- **`repro_perturb.cu`**: warp 1 (tid 32..63) waits 200 000 cycles before the L212 read (marked `PERTURB`), a reader-side delay only. In the SASS, `NANOSLEEP` at 0x1540 comes before `LDS [0x1000]` at 0x15d0.
- **Compile check:** all three compiled on a `normal` node with CUDA 13.4 (`build.sh`). Not run.
- The `repro` SASS matches the upstream build at the racy pcs (0xbd0 / 0x14b0).

## 5. Minimal fix (diff against the pinned sources)

```diff
--- a/pcdet/ops/pointnet2/pointnet2_batch/src/sampling_gpu.cu
+++ b/pcdet/ops/pointnet2/pointnet2_batch/src/sampling_gpu.cu
@@ -212,6 +212,7 @@
     old = dists_i[0];
     if (tid == 0)
         idxs[j] = old;
+    __syncthreads();
     }
 }
 
--- a/pcdet/ops/pointnet2/pointnet2_stack/src/sampling_gpu.cu
+++ b/pcdet/ops/pointnet2/pointnet2_stack/src/sampling_gpu.cu
@@ -136,6 +136,7 @@
     old = dists_i[0];
     if (tid == 0)
         idxs[j] = old;
+    __syncthreads();
     }
 }
 
@@ -315,6 +316,7 @@
         old = dists_i[0];
         if (tid == 0)
             idxs[j] = old + xyz_batch_start_idx;
+        __syncthreads();
     }
 }
```

## 6. Already known?

- **Issues:**
  - GitHub issue search in open-mmlab/OpenPCDet for "farthest point sampling CUDA kernel race condition syncthreads dists_i" returned 3 unrelated issues: #816 "CUDA error in boxes_iou3d_gpu", #322 "limits of cuda hash failure", #223 "CUDA kernel failed".
  - In sshaoshuai/Pointnet2.PyTorch (the source of the copy), "farthest point sampling race condition __syncthreads" returned 0 results.
  - GitHub-wide PR search "furthest point sample syncthreads race": 0. The web search is the one listed in mmcv-fps-new-1 §6 (no report found).
- **Commits** (blobless clone `~/incoming/realworld/cand/OpenPCDet.git`):
  - batch file history: `adbb322` (2020-07-23, "add PointNet2 batch version from https://github.com/sshaoshuai/Pointnet2.PyTorch"), `4db4978` (2020-07-29, PyTorch 1.1/1.5 support), `df299e7` (2021-12-26, rename furthest→farthest);
  - stack file history: `3fdecc8` (2020-06-23), `4db4978`, `df299e7`, `8922371` (2021-12-26, "Support StackFarthestPointSampling");
  - `git log -S'__syncthreads'` on the files: only the commits that added them;
  - `git log --all -i --grep='farthest\|fps\|race'`: only `8922371` and `df299e7`.
- **Verdict:** nothing found describes this race.

## 7. Skeptic's strongest objection and the PTX answer

**Objection:** "The same kernel has run in OpenPCDet's PointNet++/PV-RCNN models since 2020 without a report. Thread 0 needs a full n/1024-point distance pass before it can overwrite `dists_i[0]`, so a lagging warp never loses. It is formal only."

**Answer:**
- PTX gives the pair no order, so the program has a data race regardless of timing.
- Under racecheck's legal schedule, the same binary returned wrong FPS indices in all three kernels (507/512, 124/128, 124/128 mismatches against 0 natively).
- The reader-side delay in `repro_perturb.cu` makes the bad interleaving deterministic.
- "Never reported" can also be explained by the symptom: the output is a plausible-looking, slightly worse point subset, which downstream detection metrics would not flag.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` (reader-side delay) | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` | TO BE RUN |

## Common ancestry

The chain, summarised (sources and URLs in `mmcv-fps-new-1.md`, "Common ancestry"):

```
TF farthestpointsamplingKernel (Fan/Qi 2017, same race)
  -> erikwijmans/Pointnet2_PyTorch (dc4e2b0, 2017-12)
  -> sshaoshuai/Pointnet2.PyTorch (README credits erikwijmans)
  -> OpenPCDet adbb322 (commit message names sshaoshuai/Pointnet2.PyTorch)
```

OpenPCDet's two stack kernels are later copies of the batch kernel inside the same repository. `git grep -n "old = dists_i[0]" 233f8498 -- "*.cu" "*.cuh"` finds exactly these three kernels (batch L212, stack L136 and L315).
