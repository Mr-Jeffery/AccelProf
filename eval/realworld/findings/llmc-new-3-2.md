# Finding llmc-new-3-2: loop-carried WAR on `block_acc` in `softmax_autoregressive_backward_kernel8` (read in row `to` vs write in row `to+1`)

Repository karpathy/llm.c, pinned commit `f1e2ace651495b74ae22d45d1723443fd00ecd3a`, which equals `origin/master`. Class **DR**, shared memory, cross-warp (and same-warp) WAR. Triage: `eval/realworld/candidates/triage/llmc-new-3.md`, group 4. **Not addressed by open PR #847**, which fixes only the init WAW (finding llmc-new-3).

## 1. The accesses

| role | file:line @ f1e2ace6 | statement | SASS (traced build, loop unrolled ×4) |
|---|---|---|---|
| read, iteration `to` | `dev/cuda/attention_backward.cu:708` | `local_sum = cg::reduce(warp, block_acc[warp.thread_rank()], cg::plus<float>{});` | `LDS` 0x700 / 0x1320 / 0x1f40 (`coalesced_reduce.h:66` inlined) |
| write, iteration `to+1` | `:706` | `block_acc[warp.meta_group_rank()] = cg::reduce(warp, local_sum, cg::plus<float>{});` | `STS` 0x1300 / 0x1f20 / 0x2b30 |
| the only barrier per iteration | `:707` | `block.sync();` | `BAR.SYNC` 0x6f0 / 0x1310 / 0x1f30 / 0x2b40 |

The same three statements are in `train_gpt2_fp32.cu` L478–L480 inside `for (to < T_per_block)`. Not built.

## 2. Thread pair and why nothing orders it

- **Cross-warp pair.** Thread 1 (warp 0, lane 1) loads `block_acc[1]` in iteration `to = 0` (L708). Thread 32 (warp 1, lane 0) stores `block_acc[1]` in iteration `to = 1` (L706).
  - The last barrier both executed is iteration 0's L707. Between the read and the write lie only the t3 loop (`__ldcs`/`__stcs`) and the t2 load loop of row `t0-1`.
  - No barrier, `WARPSYNC` or `MEMBAR` lies between them. Plain vs plain, different warps: DR.
- **Same-warp pair.** Lane 1 of warp 1 reads `block_acc[1]` in iteration `to`. Lane 0 of warp 1 writes it in iteration `to+1`. They are separated only by `SHFL.BFLY` (not ordering) and no `WARPSYNC`.
- **Effect.** A late reader sums the next row's partial into this row's `local_sum`, and every element of row t3 ≤ t gets a wrong gradient. This is the same failure mode as llmc-new-2, which is the production version of this kernel.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/llmc-new-3-k8-buggy.json`, scalar-clock)

- **Reports.** `kernel_8.json` = `softmax_autoregressive_backward_kernel8<256>`, grid (16,12) × 256. Three WAR reports, shared, DR: `LDS` 1792 → `STS` 4864, 4896 → 7968, 8000 → 11056 (iteration boundaries 0→1, 1→2, 2→3).
- **Edges.** E.g. `4864←1792`: `intra_thread 33, intra_warp 159, intra_block 1344`. Both same-warp and cross-warp instances occurred.
- **Racecheck.** None: kernel 8 never ran under racecheck, because the command was `attention_backward 7 && attention_backward 8` and run 7 failed.
- **Native.** "All results match" (3/3).

## 4. Reproducer (`eval/realworld/findings/repro/llmc-new-3-2/`)

- **`repro.cu`.** Kernel 8 statements copied from L673–L717 (some lines joined), launched as `launch_softmax_8` with block 256, T = 256, B·NH = 1, 20 launches, host reference.
  - **One deliberate change:** PR #847's `block.sync()` after the init is added, so that finding llmc-new-3's WAW is absent and only this WAR remains (marked in the source).
- **`repro_fixed.cu`.** Also `block.sync()` right after L708.
- **`repro_perturb.cu`.** `if (warp.meta_group_rank() == 0) __nanosleep(100000);` between L707 and L708, so warp 0 reads late. Expected: deterministic wrong output.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings). Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/dev/cuda/attention_backward.cu   (f1e2ace6)
+++ b/dev/cuda/attention_backward.cu
@@ -706,5 +706,6 @@ __global__ void softmax_autoregressive_backward_kernel8(float* dpreatt, const float* datt, const flo
         block_acc[warp.meta_group_rank()] = cg::reduce(warp, local_sum, cg::plus<float>{});
         block.sync();
         local_sum = cg::reduce(warp, block_acc[warp.thread_rank()], cg::plus<float>{});
+        block.sync();  // block_acc is overwritten by the next iteration
 
         for (int t3 = block.thread_rank(); t3 <= t; t3 += BlockSize) {
```

- The same line goes after `train_gpt2_fp32.cu` L480.
- The early `if(t < 0) return;` (L696) is block-uniform, because t depends only on `blockIdx.x`, so the added barrier is safe.

## 6. Already known?

- **Issues and PRs** (GitHub search, karpathy/llm.c, 2026-10-25): "race" and "data race" found only #847, which fixes the init WAW, not this. "syncthreads" and "blockReduce" found nothing on `block_acc` reuse. The issue search found 0. Checked: https://github.com/karpathy/llm.c/pull/847 and its diff.
- **Commits.** `git log --oneline f1e2ace6 -- dev/cuda/attention_backward.cu train_gpt2_fp32.cu` has no related fix. `git log --oneline --all -S'block_acc'` lists only `50e105a`, `a360f10`, `095d276` and `b581810`, which introduced or moved the code.
- **Verdict.** **New**, as far as checked. The open PR #847 leaves it in place.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "These are benchmark kernels in `dev/cuda/`, and the window (two global loops) is long."
- **Answer.**
  - `train_gpt2_fp32.cu`, the repo's own fp32 trainer, contains the same loop.
  - Under PTX the pair is unordered, a DR.
  - The production descendant (llmc-new-2, the same reuse via `blockReduce`) printed 279/4096 wrong values under racecheck. So this window is reachable under a legal schedule; for kernel 8 itself that is not yet observed.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` | TO BE RUN |
