# Triage: llmc-new-3 (T21c step 3), result rows `llmc-new-3-buggy` (kernel 7) and `llmc-new-3-k8-buggy` (kernel 8)

Pinned commit: karpathy/llm.c `f1e2ace651495b74ae22d45d1723443fd00ecd3a`. Route R1: the repo's own `dev/cuda/attention_backward.cu` with host-only edits (B=1, T=64, benchmark sweep off; `targets/llmc-new-3/target.sh`). `attention_backward 7` and `attention_backward 8` each run the correctness pass at block size 256.
Detector run: scalar-clock only.
- `attrib/llmc-new-3-buggy.json`: `kernel_8.json` = `softmax_autoregressive_backward_kernel7<256>`, grid (64,12) × 256. `n_race = 2`. The other 5 kernel JSONs (permute, softmax_forward, unpermute…) have no reports, and the cuBLAS kernels have none either.
- `attrib/llmc-new-3-k8-buggy.json`: `kernel_8.json` = `softmax_autoregressive_backward_kernel8<256>`, grid (16,12) × 256. `n_race = 8`.
No rows for either id in `other_reports.csv`.

## Groups

| # | row | pcs | file:line pair | count | class | reason |
|---|---|---|---|---|---|---|
| 1 | k7 | `STS` 0x120 (288) / `STS` 0x680 (1664) | `attention_backward.cu:651` / `:659` | 1 (matched) | **(a) DR**, WAW | Warp 0 lane r initialises `block_acc[r] = 0` (L651). Warp r stores its partial sum into `block_acc[r]` (L659). The first barrier (`block.sync`, L660) comes after both. |
| 2 | k7 | `STS` 0x680 / `STS` 0x680 | `:659` / `:659` | 1 | **(a) DR, benign/same-value WAW** | All 32 lanes of warp r store the same `cg::reduce` result to `block_acc[r]` (one instruction instance, `warp_same_inst`). |
| 3 | k8 | `STS` 0xe0 (224) / `STS` 0x6e0 (1760) | `:691` / `:706` | 1 (matched) | **(a) DR**, WAW | The kernel-8 copy of group 1: the init (L691) vs iteration 0's L706. Later iterations are ordered by iteration 0's L707. |
| 4 | k8 | `LDS` 0x700/0x1320/0x1f40 (1792/4896/8000) → `STS` 0x1300/0x1f20/0x2b30 (4864/7968/11056) | `coalesced_reduce.h:66 < … < attention_backward.cu:708` / `:706` | 3 | **(a) DR**, WAR | Loop-carried: iteration `to` reads `block_acc[lane]` (L708). Iteration `to+1` writes `block_acc[warp]` (L706) with no barrier between. The loop is unrolled 4×; there is one report per iteration boundary (0→1, 1→2, 2→3). |
| 5 | k8 | `STS` 0x6e0, 0x1300, 0x1f20, 0x2b30, each with itself | `:706` / `:706` | 4 | **(a) DR, benign/same-value WAW** | As group 2, once per unrolled iteration. |

Class counts: (a) 5 groups (10 reports). Groups 2 and 5 (5 reports) are benign same-value WAWs. (b) 0, (c) 0, (d) 0.

Dossiers:
- groups 1 and 3, the init WAW (same statements in both kernels): `eval/realworld/findings/llmc-new-3.md`. **Already proposed upstream** as open PR #847 (see the dossier).
- group 4, the loop-carried WAR (kernel 8; also in `train_gpt2_fp32.cu` L478/L480, not built): `eval/realworld/findings/llmc-new-3-2.md`. PR #847 does not touch it.
- groups 2 and 5: no dossier. They are benign same-value WAWs, counted separately.

## Reasoning

- **SASS** (traced binary, sm_89).
  - Kernel 7: `@!P0 STS [R4], RZ` 0x120 (L651), the t2 loop, five `SHFL.BFLY`, `STS [R12], R11` 0x680 (L659), `BAR.SYNC` 0x690 (L660), then `LDS` 0x6a0 (L661, the `block_acc[lane]` read inside `cg::reduce`).
  - Kernel 8: the same shape at 0xe0 / 0x6e0 / 0x6f0 / 0x700, then three more copies of the loop body (0x1300/0x1310/0x1320, 0x1f20/0x1f30/0x1f40, 0x2b30/0x2b40/0x2b50).
  - There is no `BAR` between an iteration's `LDS` and the next iteration's `STS`. There is no `WARPSYNC` and no `MEMBAR` in either kernel.
- **Group 1/3 thread pair.** Block (t ≥ 32, ·): thread 1 (warp 0, lane 1) stores `block_acc[1] = 0` at L651. Thread 32 (warp 1, lane 0) stores warp 1's sum into `block_acc[1]` at L659.
  - Both stores come before the first barrier, so nothing orders them (cross-warp, same block). Plain vs plain overlapping writes: DR.
  - If warp 0's init lands second, warp 1's contribution is lost and row t's `local_sum` is wrong. For t < 32·r, warp r's sum is 0, so only blocks with t ≥ 32 can go wrong.
  - Trace edges, kernel 7: `288←1664` with `intra_block 69`, i.e. the init after the warp-sum store in trace order, 69 times. The opposite edge `1664←288`: `intra_block 5307`.
- **Group 4 thread pair.** Thread 32 (warp 1, lane 0) stores `block_acc[1]` in iteration `to = 1` (L706). Thread 1 (warp 0, lane 1) loads `block_acc[1]` in iteration `to = 0` (L708).
  - The last common barrier is iteration 0's L707. Both accesses follow it, so nothing orders them.
  - A late reader gets the next row's partial sum.
  - Trace edges, e.g. `4864←1792`: `intra_thread 33, intra_warp 159, intra_block 1344`. Both same-warp and cross-warp instances occurred (the intra-warp case is separated only by `SHFL.BFLY`).
- **Groups 2/5 (same value).** `cg::reduce(warp, x, plus<float>)` compiles to five `SHFL.BFLY` butterflies.
  - In each step lane i computes `v_i + v_{i^m}` and lane `i^m` computes `v_{i^m} + v_i`. IEEE addition is commutative, so by induction all 32 lanes hold bit-identical results.
  - The 32 stores of one `STS` instance therefore write one value. That is a formal DR (the PTX model has no "same instruction" ordering between threads) and benign/same-value.
  - Trace edges: `intra_instance_launch 190464` (k7) and `47616` per iteration (k8).
- **Racecheck** (`eval/realworld/racecheck/llmc-new-3-buggy.txt`). The command was `attention_backward 7 && attention_backward 8`.
  - Under racecheck, run 7 printed **"Mismatch of dpreatt at 14787: CPU_ref: 0.008248 vs GPU: 0.010148"** (and 9 more) and exited 1. So **kernel 8 never ran under racecheck**: the `k8` row has no racecheck result.
  - Natively both runs print "All results match" (3/3, `native/llmc-new-3-buggy.json`).
  - Kernel 7 under racecheck: 1523 errors, 0 warnings. 1522 are byte-level `Potential WAW hazard` lines. The other is the aggregate "Race reported between Write access at … +0x120 in attention_backward.cu:651 and Write access at … +0x680 in attention_backward.cu:659 [1522 hazards]". All are Write L651 vs Write L659. Example: block (37,1,0), threads (1,0,0)/(32,0,0), "Current Value : 0, Incoming Value : 22". The hazards are only in blocks with t ≥ 32, which fits value-based reporting: for t < 32·r both writes are 0.
  - The wrong index 14787 = head 3, row t = 39, column 3, in the range where warp 1's contribution matters.
  - Inference: under racecheck's schedule warp 0's init overwrote a warp's partial at least once. This is real evidence that the init race can change the output when the warp schedule changes. Natively, warp 0 initialises before the other warps finish their t2 loop.
  - Racecheck shows nothing for the same-value L659/L659 WAW (consistent with value filtering, not checked).
- **Coverage.**
  - The correctness pass uses T = 64, so only warps 0–1 carry data. The reproducers use T = 256.
  - The `train_gpt2_fp32.cu` copy of kernel 8 (L463 / L478 / L480) has the same two races. It was not built; the statement is from reading the code.
