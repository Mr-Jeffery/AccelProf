# Triage: llmc-new-2 (T21c step 3)

Pinned commit: karpathy/llm.c `f1e2ace651495b74ae22d45d1723443fd00ecd3a`. Route R2: `llmc/attention.cuh`, `llmc/cuda_utils.cuh` and three headers they include, byte-identical (`targets/llmc-new-2/r2/blob.check` PASS), plus `r2/common/driver.cu`. The driver runs B·NH = 1, T = 64, grid (16,1) × 256, with a host reference.
Detector run: scalar-clock only (`eval/results/realworld_t21c/attrib/llmc-new-2-buggy.json`). 1 kernel JSON (`softmax_autoregressive_backward_inplace_kernel`), `n_race = 1`, `n_sc = 0`. The kernel summary shows `races: 2`, the two directions of one pc pair, merged into one report.
No rows for this id in `other_reports.csv`.

## Groups

| # | kernel | pcs | file:line pair | count | class | reason |
|---|---|---|---|---|---|---|
| 1 | `softmax_autoregressive_backward_inplace_kernel` | `STS` 0xa60 (2656) / `LDS` 0xa90 (2704) | `cuda_utils.cuh:175 < attention.cuh:176` / `cuda_utils.cuh:177 < attention.cuh:176` | 1 (site verdicts: WAR 2656←2704 and RAW 2704←2656, both RACE) | **(a) DR** | `shared_val` is reused by the next `blockReduce` call of the `to` loop (attention.cuh L164) with `final_sync = false`. No barrier separates iteration `to`'s read (L177) from iteration `to+1`'s write (L175). |

Class counts: (a) 1 group (1 report), with one dossier: `eval/realworld/findings/llmc-new-2.md`. (b) 0, (c) 0, (d) 0. It is not a same-value WAW: the next row's partial sum differs.

## Reasoning

- **SASS** (traced binary, sm_89). The loop body is: five `SHFL.BFLY`, `@!P0 STS [R25]` (L175, lane 0), `BAR.SYNC` 0xa70 (L176), `@!P3 LDS [R13]` (L177, lanes < 8), five `SHFL.BFLY`, the t3 store loop, then the back edge `BRA` 0x17d0 to L164.
  - There is no second `BAR.SYNC` in the loop.
  - There is no `WARPSYNC` and no `MEMBAR` in the kernel.
- **Cross-warp pair.** In block (0,0), thread 32 (warp 1, lane 0) stores `shared_val[1]` in iteration `to = 1`. Thread 1 (warp 0, lane 1) loads `shared_val[1]` in iteration `to = 0`.
  - The last barrier both executed is iteration 0's L176. The read follows it in program order, and so does the write (via the loop back edge).
  - Nothing orders the read before the write. Plain vs plain, so the pair is a DR (WAR).
  - If the write lands first, the reader gets row `t0-1`'s partial for row `t0`.
  - The trace recorded that order at least once: the RAW site verdict 2704←2656 is unordered (see below). Whether the recorded order is the hardware's memory order was not checked.
- **Intra-warp pair (also a DR).** Warp 1 lane 0 writes `shared_val[1]` in iteration `to+1`, and warp 1 lane 1 reads it in iteration `to`.
  - Between them lie only full-mask `SHFL.BFLY`, which is not memory ordering (T21 corpus note 2), and ptxas emitted no `WARPSYNC`.
  - The record's note "Intra-warp case … is ordered by the shuffles" does not hold under PTX. This is a correction to the record. It is the same race, one more thread pair.
- **Trace edges** (`kernel_0.json`):
  - WAR 2656←2704: `intra_warp 48, intra_block 336`.
  - RAW 2704←2656: `intra_thread 45, intra_warp 19, intra_block 448`.
  - Both relations, same warp and same block, occurred.
- **Observable.** Native runs gave `mismatches=0/4096` (3/3). Under racecheck the same binary printed **`mismatches=279/4096`** (`eval/realworld/racecheck/llmc-new-2-buggy.txt`).
  - All racecheck hazards are on this pair: 2,000 displayed (955 WAR and 773 RAW errors, 272 "Warp Level Programming" WAR warnings); totals 2105 errors and 348 warnings, all `cuda_utils.cuh:175` (Write, +0xa60) vs `:177` (Read, +0xa90).
  - The kernel's only shared variable is `shared_val`. So the wrong output under racecheck's schedule follows from this race. This is an inference, but no other shared-memory or cross-thread global dependence exists in the kernel: each thread reads and writes its own `t3` elements.
  - This is real evidence for the perturbation question. The race is not only formal, because a different warp schedule changes the result.

## Driver coverage

- T = 64 and BlockSize = 256, so at most 64 threads have a nonzero `local_sum` per row (t2 ≤ t < 64). Only warps 0–1 contribute.
- The wrong values come from those slots. Warps 2–7 write 0 in every iteration, which is harmless.
- The reproducer uses T = 256, so all 8 warps carry data.
