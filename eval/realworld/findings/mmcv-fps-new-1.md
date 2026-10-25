# Finding mmcv-fps-new-1: cross-iteration WAR on `dists_i[0]` in mmcv's furthest point sampling

**Status:** class (a) DR, observed as wrong output under compute-sanitizer racecheck's schedule. Verifier: not yet (step 5).
**Repository:** open-mmlab/mmcv at `d2111bda571f3b3eb53954af6f9cff25f34e626f` (HEAD of the default branch when T21c re-checked it).
**Lineage:** this kernel is one copy of a widely copied PointNet++ FPS kernel; see "Common ancestry". Counting rule suggestion: one bug pattern, reported per repository.

## 1. The two accesses

File `mmcv/ops/csrc/common/cuda/furthest_point_sample_cuda_kernel.cuh`:

| kernel | write (iteration j+1, thread 0) | read (iteration j, every thread) |
|---|---|---|
| `furthest_point_sampling_forward_cuda_kernel<1024>` | L67 `dists_i[tid] = besti;`: `STS [R0.X4+0x1000]` at pc 0xbd0 (3024) | L80 `old = dists_i[0];`: `LDS R7, [0x1000]` at pc 0x14b0 (5296) |
| `furthest_point_sampling_with_dist_forward_cuda_kernel<1024>` | L134: `STS [R0.X4+0x1000]` at 0x7d0 (2000) | L147: `LDS R17, [0x1000]` at 0x10b0 (4272) |

- Both accesses are plain 32-bit shared accesses: no `volatile`, no atomics, no `.STRONG`.
- Barriers in the loop body: L68 (`BAR` at 0xbe0) and the ten L77 barriers of the unrolled reduction (last at 0x1470).
- After the read at 0x14b0 the code branches back to the loop head (0x14e0 `BRA`) without a barrier.

## 2. Thread pair and why nothing orders it

- Block b (1024 threads, 32 warps), any reader thread t ≥ 32 against thread 0. Racecheck names Read thread 607 (block 1, warp 18) and Read thread 383 (block 0, warp 11) against Write thread 0.
- Reader t executes L80 in iteration j after the last L77 barrier.
- Thread 0 executes L80 and L81 in iteration j, then the loop increment, then the distance loop L44–L65 (global loads/stores only), then L66–L67 of iteration j+1, where tid = 0 writes `dists_i[0]`.
- The first barrier thread 0 meets after its own L80 is L68, which comes after the write.
- So no `bar.sync` lies between reader t's read and thread 0's write on any path. Under PTX §8.7.1 there is no causality order between them. They conflict (same address, one write), so this is a data race. Same block, different warps.
- The two accesses are not in one warp, so `__syncwarp` lock-step arguments do not apply even informally.

## 3. Trace evidence (cuVein scalar-clock, `eval/results/realworld_t21c/attrib/mmcv-fps-new-1-buggy.json`)

- `kernel_0.json`, forward kernel:
  - report `a_pc 3024 STS (.cuh:67)` / `b_pc 5296 LDS (.cuh:80)`, WAR, `verdict RACE`, `strength none`, `conflict_class DR`;
  - kernel summary `races 1, sc 0, ordered 41`.
- `kernel_1.json`, with_dist: `a_pc 2000 STS (.cuh:134)` / `b_pc 4272 LDS (.cuh:147)`, WAR, RACE, DR.
- Total `n_race = 2`, `n_sc = 0`, no other reports. Store: `/mnt/beegfs/fzheng4/cuvein_traces/realworld-2026-10-t21c/mmcv-fps-new-1-buggy/scalar-clock/`.
- Reuse edge `3024 ← 5296`: `intra_block 424`, `intra_thread 84`, `intra_warp 0`.
- `hb_sync_pass [3024, 5296, 508, 2, 5296, 3024]`; 508 = 2 blocks × 254 iteration pairs (field semantics not checked).
- The scalar-clock JSON has no thread ids; the racecheck file gives them (section 2).
- Racecheck (`eval/realworld/racecheck/mmcv-fps-new-1-buggy.txt`, print limit 2000, all displayed hazards in the forward kernel):
  - WAR `R@+0x14b0 / W@+0xbd0`: 992 cross-warp errors and 64 same-warp warnings;
  - RAW `W@+0xbd0 / R@+0x14b0`: 944 errors.
- The driver's host FPS reference check:
  - native (3 runs): `mismatches=0/512` and `0/128`;
  - under racecheck: `mismatches=505/512` (forward) and `121/128` (with_dist).

## 4. Reproducer: `eval/realworld/findings/repro/mmcv-fps-new-1/`

- **`repro.cu`** (58 lines):
  - The forward kernel and `__update` are copied from L11–L83. Trimmed: comments, blank lines, the with_dist kernel (same race) and the torch launcher. Several statements are joined onto one line (whitespace only); no token of the kernel is changed.
  - Launch as the launcher does for N = 2048: `<1024><<<2, 1024>>>`, B = 2, M = 256 (argv[1] overrides M), `temp = 1e10`.
  - Input: integer coordinates in [1, 1000], so every squared distance is exact in fp32 and the host check needs no FMA tolerance.
  - The host checks *validity*, not one particular tie-break: each `idx[j]` must maximise the min-distance to `idx[0..j-1]`. It prints `invalid=k/512 -> OK | WRONG OUTPUT`.
- **`repro_fixed.cu`**: adds one `__syncthreads()` after L81 (marked `FIX`).
- **`repro_perturb.cu`**: adds a `clock64`/`__nanosleep` busy-wait of 200 000 cycles (about 100 µs) for warp 1 only (`tid` 32..63), just before the L80 read (marked `PERTURB`).
  - This delays one side of the race, the reader. Thread 0 is not delayed. It finishes its two-point distance loop (a few µs) and stores its local best into `dists_i[0]` while warp 1 sleeps.
  - Warp 1 then reads that value as `old`, so it measures iteration j+1 from the wrong point.
  - SASS check: `NANOSLEEP` at 0x1540 precedes the `LDS [0x1000]` at 0x15d0, and the `asm volatile("" ::: "memory")` fences keep the compiler from hoisting the load.
- **Compile check:** all three files compiled with `build.sh` (`nvcc -arch=sm_89 -lineinfo --cudart shared -O3`, CUDA 13.4) on a `normal` node, with no warnings. They were not run (no GPU).
- The `repro` SASS has the read at the same pc as the upstream build (`LDS R7, [0x1000]` at 0x14b0, `BRA` back with no barrier). `repro_fixed` has `BAR.SYNC` at 0x14d0 right after it.
- Expected outputs: `expected.md` in the reproducer folder.

## 5. Minimal fix (diff against the pinned source)

```diff
--- a/mmcv/ops/csrc/common/cuda/furthest_point_sample_cuda_kernel.cuh
+++ b/mmcv/ops/csrc/common/cuda/furthest_point_sample_cuda_kernel.cuh
@@ -79,6 +79,7 @@
 
     old = dists_i[0];
     if (tid == 0) idxs[j] = old;
+    __syncthreads();
   }
 }
 
@@ -146,6 +147,7 @@
 
     old = dists_i[0];
     if (tid == 0) idxs[j] = old;
+    __syncthreads();
   }
 }
```

The fix costs one block barrier per sampled point. An alternative with no extra barrier is to double-buffer `dists_i` across iterations (`dists_i[(j & 1) * block_size + tid]`); it is not proposed here.

**Same code in another backend:** `git grep -n "old = dists_i[0]" d2111bda` also finds `mmcv/ops/csrc/common/musa/furthest_point_sample_musa_kernel.muh` L76 and L143. That is the MUSA (Moore Threads) port, with the same missing barrier after the read. It is outside the PTX model and was not built or run. An upstream patch should add the same `__syncthreads()` there. No other CUDA copy of the kernel is in the repository.

## 6. Already known?

- **Issues and PRs:**
  - GitHub issue search in open-mmlab/mmcv for "furthest point sampling race condition missing __syncthreads wrong index": 0 results.
  - Issue search in open-mmlab/mmdetection3d (where mmcv's kernel came from) for "furthest point sample race condition missing syncthreads": 0 results.
  - GitHub-wide PR search "furthest point sample syncthreads race": 0 results.
  - Web search "furthest point sampling cuda kernel race condition dists_i[0] __syncthreads missing" found no report of this race. Hits: arxiv.org/pdf/1905.01833 (a CUDA bug study, unrelated kernels), a gemfury mirror of the mmcv .cuh, NVIDIA forum thread 49771 (unrelated), and a llama.cpp race fix.
- **Commits** (blobless clone `~/incoming/realworld/cand/mmcv.git`):
  - `git log --follow -- <file>` at the pinned commit: `63a6cbe` "[Feature] Add fps op from mmdet3d (#1337)" (2021-10-13), `b484aba` "Fix furthest_sample_point (#1405)" (2021-10-15), and `d2111bd` (SUPA backend).
  - `b484aba` added the `tid < tid_thres` guard and `#pragma unroll` to the reduction loop. It did not touch the L80/L67 pair.
  - `git log -S'__syncthreads' -- <file>`: only `63a6cbe`.
  - `git log --all -i --grep='furthest\|fps'`: the NPU fixes `0d3cdc6` and `528e466` (#3094/#3095, `furthest_point_sampling_with_dist_npu.cpp` only), `d77557b`, `b9a96e5` and video-fps commits. None concerns this race.
- **Verdict:** nothing found describes this race. The search was not exhaustive (no search of mmcv forks or Chinese-language forums).

## 7. Skeptic's strongest objection and the PTX answer

**Objection:** "Formal only. Thread 0 has to do a whole distance pass over n/1024 points (global loads) before it stores, while a late warp needs one `LDS`. It never fails. The existing tests pass, and native runs give the reference answer."

**Answer:**
- (i) PTX §8.7.1 has no timing argument. The read and the write are unordered conflicting plain accesses, so the program has a data race and its result is not defined by the memory model.
- (ii) It is not only formal. A legal schedule already produced wrong output: under compute-sanitizer racecheck the same binary's FPS indices mismatched the host reference in 505 of 512 slots (forward) and 121 of 128 (with_dist), against 0 natively.
- (iii) The perturbation reproducer forces the same schedule with a delay on the reader side alone.
- (iv) Possible real triggers for a late warp (not demonstrated): preemption, time-slicing, a debugger, or other resident warps saturating the SM's schedulers. With small n (≤ 1024 points, one point per thread) thread 0's distance pass is tiny.

Second objection: "Benign: the late warp picks up *some* point." **Answer:** No. It uses the wrong reference point for a whole iteration. That corrupts `temp[]` for its points and every later selection, and the result is no longer a farthest-point sequence (the repro's validity check counts this).

## 8. Results: TO BE RUN

| run | command | result |
|---|---|---|
| native `repro` | `./repro` | TO BE RUN |
| native `repro_fixed` | `./repro_fixed` | TO BE RUN |
| perturbation | `./repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` | harness on the binary | TO BE RUN |
| cuVein scalar-clock on `repro_fixed` | harness on the binary | TO BE RUN |
| racecheck on `repro` | `compute-sanitizer --tool racecheck ./repro` | TO BE RUN |
| (optional) racecheck on `repro_fixed` | same | TO BE RUN |

## Common ancestry (shared with openpcdet-fps-new-1 and pointnet2pt-fps-new-1)

- **Original:** PointNet++ TensorFlow op `charlesq34/pointnet2/tf_ops/sampling/tf_sampling_g.cu`, `farthestpointsamplingKernel`. Its header reads "Original author: Haoqiang Fan, Modified by Charles R. Qi, 2017".
  - It has the same race, read by WebFetch of the raw file: `dists_i[threadIdx.x]=besti;` is followed by the reduction loop, whose first `__syncthreads()` comes after that store; the loop ends with `__syncthreads(); old=dists_i[0];`.
  - Between `old=dists_i[0]` and the next iteration's `dists_i[threadIdx.x]=besti` there is no barrier.
- **erikwijmans/Pointnet2_PyTorch:** the templated `block_size` / `__update` / unrolled-ladder form with the identical trailing `old = dists_i[0];` and no barrier is already in its initial commit `dc4e2b0` (2017-12-26, `utils/csrc/sampling_gpu.cu`). The same trailing read with no barrier is present in `65a127f` (2018-02-10, "Some faster/better kernels") and at the pinned `b5ceb6d9`. Commits in between were not read one by one.
- **sshaoshuai/Pointnet2.PyTorch:** its README acknowledges erikwijmans/Pointnet2_PyTorch as the initial work.
  - **OpenPCDet:** commit `adbb322` (2020-07-23, Shaoshuai Shi) is "add PointNet2 batch version from https://github.com/sshaoshuai/Pointnet2.PyTorch". The stack kernels came in `3fdecc8` (2020-06-23) and `8922371` (2021-12-26).
  - **mmdetection3d:** `mmdet3d/ops/furthest_point_sample/src/furthest_point_sample_cuda.cu` (v0.17.0) is headed "Modified from https://github.com/sshaoshuai/Pointnet2.PyTorch/tree/master/pointnet2/src/sampling_gpu.cu". Its with_dist kernel is headed "Modified from https://github.com/qiqihaer/3DSSD-pytorch/…".
  - **mmcv:** `63a6cbe` "Add fps op from mmdet3d" carries both headers over.
- **Conclusion:** the three FPS-family findings (mmcv, OpenPCDet, Pointnet2_PyTorch) are copies of one kernel and one bug, inherited from the 2017 TF original. Suggestion for the paper: count one distinct bug pattern, present in three audited repositories (six kernels).
- pytorch_cluster-new-1 is **not** in this lineage. It is an independent implementation with a different reduction and a different race.
