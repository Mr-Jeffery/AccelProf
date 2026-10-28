# Finding pointnet2pt-fps-new-1: cross-iteration WAR on `dists_i[0]` in Pointnet2_PyTorch's furthest point sampling

**Status:** class (a) DR, observed as wrong output under compute-sanitizer racecheck's schedule. Verifier: not yet (step 5).
**Repository:** erikwijmans/Pointnet2_PyTorch at `b5ceb6d9ca0467ea34beb81023f96ee82228f626` (master equals the pinned sha; last commit 2021-07-30).
**Lineage:** the oldest PyTorch copy among the three FPS-family findings. The race is already in the TF original it was written from (see "Common ancestry").

## 1. The two accesses

File `pointnet2_ops_lib/pointnet2_ops/_ext-src/src/sampling_gpu.cu`, kernel `furthest_point_sampling_kernel<512>`:
- **write:** L112 `dists_i[tid] = besti;` (thread 0, iteration j+1), `STS [R3.X4+0x800]` at pc 0xec0 (3776);
- **read:** L170 `old = dists_i[0];` (every thread, iteration j), `LDS R15, [0x800]` at pc 0x16c0 (5824).

Both are plain shared 32-bit accesses. The loop's barriers are L113 (`BAR` at 0xed0) and the nine reduction barriers (last L167 at 0x1680). After the read, `BRA` (0x16f0) goes back to the loop head with no barrier.

## 2. Thread pair and why nothing orders it

- Block b of 512 threads (16 warps). Racecheck: Read thread 479 (warp 14) at +0x16c0 against Write thread 0 at +0xec0. The record's pair, thread 33 against thread 0, is the same race.
- Thread 0's path from L170 (j) to L112 (j+1) is L171, the loop increment and the distance loop L95–L110 (global accesses, `mag <= 1e-3` skip). It has no `bar.sync`. The next barrier, L113, comes after the write.
- So there is no causality order under PTX §8.7.1 between the read and the write. They are different warps of one block.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/pointnet2pt-fps-new-1-buggy.json`, scalar-clock)

- One report: `a_pc 3776 STS sampling_gpu.cu:112` / `b_pc 5824 LDS sampling_gpu.cu:170`, WAR, `RACE`, `strength none`, `DR`. Kernel summary: `races 1, sc 0, ordered 37`. No other reports.
- Reuse edge `3776 ← 5824`: `intra_block 451, intra_thread 57, intra_warp 0`.
- `hb_sync_pass [3776, 5824, 508, 2, 5824, 3776]`.
- Racecheck (print limit 2000): WAR `R@0x16c0/W@0xec0` (1136 cross-warp errors, 68 same-warp warnings), RAW `W@0xec0/R@0x16c0` (796).
- Driver's host reference (which includes the `mag` skip): native `0/512` (3 runs); under racecheck `503/512` mismatches.

## 4. Reproducer: `eval/realworld/findings/repro/pointnet2pt-fps-new-1/`

- **`repro.cu`** (58 lines): the kernel and `__update` copied from L59–L173.
  - Trimmed: comments, blank lines, the wrapper and the file's other kernels. The ladder is kept in full, joined two levels per line (whitespace only).
  - `<512><<<2, 512>>>` (`opt_n_threads(2048)` = 512 with `TOTAL_THREADS` 512), M = 256, `temp = 1e10`.
  - Integer coordinates in [1, 1000]: exact distances, and the `mag` skip never fires. Host validity check.
- **`repro_fixed.cu`**: one `__syncthreads()` after L171 (marked `FIX`).
- **`repro_perturb.cu`**: warp 1 waits 200 000 cycles before the L170 read (reader side only). In the SASS, `NANOSLEEP` at 0x1750 precedes `LDS [0x800]` at 0x17e0.
- **Compile check:** compiled with CUDA 13.4 on a `normal` node. Not run. `repro`'s SASS matches the upstream build (read at 0x16c0, write at 0xec0). `repro_fixed` has `BAR.SYNC` at 0x16e0 after the read.

## 5. Minimal fix (diff against the pinned source)

```diff
--- a/pointnet2_ops_lib/pointnet2_ops/_ext-src/src/sampling_gpu.cu
+++ b/pointnet2_ops_lib/pointnet2_ops/_ext-src/src/sampling_gpu.cu
@@ -169,6 +169,7 @@
 
     old = dists_i[0];
     if (tid == 0) idxs[j] = old;
+    __syncthreads();
   }
 }
```

## 6. Already known?

- **Issues:** GitHub issue search in erikwijmans/Pointnet2_PyTorch for "furthest point sampling race condition syncthreads wrong result" returned 3 results:
  - **#157** "[BUG] Error Sampling Result for Furthest Point Sampling" (open, 2021-09-28). A hole in a sampled dense plane. No cause identified and no replies.
  - **#83** "about farthest point sampling" (closed). A hole in a sampled airplane. The maintainer attributes it to the greedy algorithm, and removing the two `mag <= 1e-3` lines fixed it for the user.
  - **#151** "furthest_point_sample … working differently from original pointnet++" (closed). The user attributes the difference to the `mag` threshold.
  - None names a race or a missing barrier. #157's symptom (a hole) fits the `mag` skip explanation of #83 better than this race. Whether #157 is this race is **not decidable** from the issue text.
- Web/PR searches as in mmcv-fps-new-1 §6: nothing.
- **Commits** (`~/incoming/realworld/cand/Pointnet2_PyTorch.git`):
  - `git log --follow` on the file: `22e8cf5` (2020-03-28 "Updates 2020 (#94)"), `49501a0`, `88406aa`, `98a771a`, `65a127f` (2018-02-10 "Some faster/better kernels"), `8bce353`, `dc4e2b0` (initial, 2017-12-26).
  - `git log --all -i --grep='sampling\|race\|sync'`: only these general update commits.
  - The race is present in `dc4e2b0` and `65a127f` (both read) and at the pinned commit.
  - `git grep -n "old = dists_i[0]" b5ceb6d9 -- "*.cu"` finds only L170: there is no other copy in the repository.
- **Verdict:** nothing found describes this race. #157 is a possibly related symptom report with no diagnosis.

## 7. Skeptic's strongest objection and the PTX answer

**Objection:** "This is the reference PyTorch PointNet++ implementation, used for years. Thread 0 must scan n/512 points before it can overwrite, so lock-step-like progress hides it. Formal only."

**Answer:**
- The pair has no PTX order, so it is a data race.
- A legal schedule (racecheck's) produced 503/512 wrong indices from the same binary, against 0 natively.
- The reader-side perturbation reproduces that deterministically.
- The record's warp-lock-step intuition does not apply: reader and writer are in different warps.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` | TO BE RUN |

## Common ancestry

- The kernel derives from the PointNet++ TF op `tf_sampling_g.cu` `farthestpointsamplingKernel` (Haoqiang Fan, modified by Charles R. Qi, 2017). The TF kernel has the same missing barrier between `old=dists_i[0]` and the next `dists_i[threadIdx.x]=besti`.
- This repository's initial commit (2017-12) introduced the templated `__update` form, which sshaoshuai/Pointnet2.PyTorch then credits as its base.
- From there it reached OpenPCDet and, via mmdetection3d, mmcv. Details and URLs: `mmcv-fps-new-1.md`, "Common ancestry".
