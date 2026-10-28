# Triage: mmcv-fps-new-1 (T21c step 3)

Pinned commit: open-mmlab/mmcv `d2111bda571f3b3eb53954af6f9cff25f34e626f`, file
`mmcv/ops/csrc/common/cuda/furthest_point_sample_cuda_kernel.cuh` (R2 copy, blob.check PASS).
Detector run: scalar-clock only (`eval/results/realworld_t21c/attrib/mmcv-fps-new-1-buggy.json`), 2 kernel JSONs, `n_race = 2`, `n_sc = 0`.
`other_reports.csv` and `other_reports_removed.csv` have no rows for this id (checked with `cut -d, -f1 | sort | uniq -c`).

## Groups

| # | kernel | pcs (a / b) | file:line pair | count | class | reason |
|---|---|---|---|---|---|---|
| 1 | `furthest_point_sampling_forward_cuda_kernel<1024>` | 3024 `STS` / 5296 `LDS` | `.cuh:67` / `.cuh:80` | 1 report | **(a) DR** | WAR on `dists_i[0]`. Every thread reads it at L80 (iteration j). Thread 0 overwrites it at L67 (iteration j+1). No barrier between the two. Cross-warp, same block. |
| 2 | `furthest_point_sampling_with_dist_forward_cuda_kernel<1024>` | 2000 `STS` / 4272 `LDS` | `.cuh:134` / `.cuh:147` | 1 report | **(a) DR** | The same race in the with_dist copy of the kernel (L147 read, next-iteration L134 write). |

Class counts: (a) 2, (b) 0, (c) 0, (d) 0. Both groups are the oracle pair. There are no other reports.
Neither group is a same-value WAW. Both are WAR pairs whose reader can observe a different value.

## Reasoning

**SASS** (from `nvdisasm -g` of the built `driver`, sm_89, CUDA 13.3 build):
- Forward kernel: `STS [R0.X4+0x1000]` at 0xbd0 (L67), then `BAR.SYNC` at 0xbe0 (L68). Ten reduction levels follow, each closed by a `BAR.SYNC` (L77). The last one is at 0x1470.
- After it: `LDS R7, [0x1000]` at 0x14b0 (L80), then `BRA` 0x14e0 back to the loop head. No `BAR`, `MEMBAR` or `WARPSYNC` lies between 0x14b0 and the next execution of 0xbd0.
- The with_dist kernel has the same shape: `STS` at 0x7d0 (L134), last `BAR` at 0x1070, `LDS [0x1000]` at 0x10b0 (L147).
- Both accesses are plain (`STS`/`LDS`, no `.STRONG`, no atomics), so a conflict between them is a DR, not an SC (CLAUDE.md T21 corpus note 1).

**Thread pair.**
- A reader in warp w ≥ 1 executes L80 `old = dists_i[0]` in iteration j. Racecheck shows thread 607 (block 1, warp 18) and thread 383 (block 0, warp 11).
- Thread 0 (warp 0) executes L67 `dists_i[tid] = besti` with tid = 0 in iteration j+1.
- Both are in the same block. Under PTX §8.7.1 the two accesses would be ordered only by a `bar.sync` that both threads execute between them. Thread 0's path from L80(j) to L67(j+1) contains no barrier: L81, then the loop increment, then the distance loop L44–L65, which uses global memory only. The reader's L80 comes after the last reduction barrier L77 of iteration j.
- So the read and the write are not ordered by happens-before. Both are morally-strong-free plain accesses, and they conflict. This is a data race.
- The thread relation is cross-warp, same block, matching the record's `cross-warp-same-block`.

**Trace evidence.**
- The scalar-clock report carries no thread ids.
- The kernel JSON's reuse edge `current_pc 3024 / ancient_pc 5296` has `intra_block = 424`, `intra_warp = 0` and `intra_thread = 84`. In 424 of 508 cases, the access to `dists_i[0]` just before thread 0's write was a read by a thread of another warp in the same block.
- `hb_sync_pass` holds `[3024, 5296, 508, 2, 5296, 3024]`. The third field is 508 = 2 blocks × 254 consecutive-iteration pairs. The meaning of the fields was not checked in the detector source.

**Is it observable? Yes, already in the existing racecheck run.**
- `eval/realworld/racecheck/mmcv-fps-new-1-buggy.txt` lists this pair as a WAR error. Read thread (607,0,0) at +0x14b0 and Write thread (0,0,0) at +0xbd0: 992 of the displayed hazards.
- It also lists the RAW direction, `W@0xbd0` then `R@0x14b0`: 944 displayed. That means a reader actually observed thread 0's next-iteration value.
- All 2000 displayed hazards are in the forward kernel. The print limit hides the with_dist kernel's hazards.
- Under racecheck, the driver's own host-reference check printed `mismatches=505/512` (forward) and `mismatches=121/128` (with_dist).
- The three native runs printed `mismatches=0/512` and `0/128` (`eval/realworld/native/mmcv-fps-new-1-buggy.json`).
- Racecheck does not change memory values; it only changes the schedule. The same binary therefore produces wrong FPS indices under a legal schedule that racecheck happens to induce.
- So the race is not formal-only. It is latent under the native schedule and corrupts the output under another legal one. The reproducer's `repro_perturb.cu` forces that schedule with a delay on the reader side alone (see the dossier).

**Benign?** No.
- A lagging warp reads thread 0's local best index for iteration j+1 instead of the selected point.
- It then measures iteration j+1's distances from the wrong point. That corrupts `temp[k]` for its points and every later selection.
- The output (`idxs[j]` is written by thread 0 alone) stays plausible-looking but is no longer the farthest point sequence.

Finding: `eval/realworld/findings/mmcv-fps-new-1.md` (one finding covering both kernels of the file).
