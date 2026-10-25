# Finding llmc-new-3: `block_acc` initialisation races with the warp-sum stores (WAW) in `softmax_autoregressive_backward_kernel7/8`

Repository karpathy/llm.c, pinned commit `f1e2ace651495b74ae22d45d1723443fd00ecd3a`, which equals `origin/master`. Class **DR**, shared memory, cross-warp WAW. **Already proposed upstream: open PR #847.** **Wrong output observed under racecheck** (kernel 7). Triage: `eval/realworld/candidates/triage/llmc-new-3.md`, groups 1 and 3.

## 1. The accesses

| role | file:line @ f1e2ace6 | statement | SASS (traced build) |
|---|---|---|---|
| write A (warp 0, lane r) | `dev/cuda/attention_backward.cu:651` (kernel 7), `:691` (kernel 8) | `block_acc[warp.thread_rank()] = 0;` | k7 `@!P0 STS [R4], RZ` 0x120; k8 0x0e0 |
| write B (warp r, all lanes) | `:659` (k7), `:706` (k8, iteration 0) | `block_acc[warp.meta_group_rank()] = cg::reduce(warp, local_sum, cg::plus<float>{});` | k7 `STS [R12], R11` 0x680; k8 0x6e0 |
| first barrier | `:660` (k7), `:707` (k8) | `block.sync();` | k7 `BAR.SYNC` 0x690; k8 0x6f0 |

The same statements are in `train_gpt2_fp32.cu` L463 / L478 / L479 (the repo's fp32 trainer). Not built.

## 2. Thread pair and why nothing orders it

- **Pair.** Block (t, h) with t ≥ 32: thread 1 (warp 0, lane 1) stores `block_acc[1] = 0` (L651). Thread 32 (warp 1, lane 0) stores warp 1's partial sum into `block_acc[1]` (L659).
  - Both stores come before the kernel's first barrier (L660), and the kernel has no `WARPSYNC` or `MEMBAR`. So they are unordered conflicting plain writes by different warps: DR.
- **Effect.** If warp 0's zero lands second, warp 1's contribution to row t is lost. `local_sum`, read by every thread at L661 after the barrier, is then wrong for the whole row.
  - For t < 32·r warp r's sum is 0, so only rows t ≥ 32 can be affected.

## 3. Trace evidence (scalar-clock)

- **Kernel 7.** `attrib/llmc-new-3-buggy.json`, `kernel_8.json` = `softmax_autoregressive_backward_kernel7<256>`, grid (64,12).
  - Report 288/1664 WAW, DR, `observed_distance: block`.
  - Edges: `288←1664` `intra_block 69` (the init after the sum store in trace order) and `1664←288` `intra_block 5307`.
- **Kernel 8.** `attrib/llmc-new-3-k8-buggy.json`, `kernel_8.json` = `kernel8<256>`, grid (16,12).
  - Report 224/1760 WAW. Edge `1760←224`: `intra_thread 192, intra_block 1344`.
- **Racecheck** (`eval/realworld/racecheck/llmc-new-3-buggy.txt`, kernel 7 only).
  - 1523 errors: 1522 byte-level WAW hazards Write +0x120 (L651) vs Write +0x680 (L659) and one aggregate line. Example: block (37,1,0), threads (1,0,0)/(32,0,0), "Current Value : 0, Incoming Value : 22".
  - The program's own check then printed **"Mismatch of dpreatt at 14787: CPU_ref: 0.008248 vs GPU: 0.010148"** (index 14787 = head 3, row 39, column 3) plus 9 more, and exited 1.
  - Natively: "All results match" (3/3).
  - Kernel 8 never ran under racecheck (`attention_backward 7 && attention_backward 8`).

## 4. Reproducer (`eval/realworld/findings/repro/llmc-new-3/`, kernel 7)

- **`repro.cu`.** Kernel 7 statements copied from L631–L667 (some lines joined), launched as `launch_softmax_7` with block 256. B·NH = 1, T = 256 (all 8 warps carry data), 20 launches, host reference.
- **`repro_fixed.cu`.** `block.sync()` after the init, as PR #847.
- **`repro_perturb.cu`.** `__nanosleep(100000)` in warp 0 before its init. Expected: warps 1..7 store first, then warp 0 zeroes them, a deterministic wrong output.
- Kernel 8 has the identical init statements. Its reproducer is under finding llmc-new-3-2, with PR #847's barrier applied there to isolate that finding's race.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings). Not run.

## 5. Minimal fix

This is the diff of open PR #847 (ea74abf, ziqiaozhou), copied from https://patch-diff.githubusercontent.com/raw/karpathy/llm.c/pull/847.diff:

```diff
--- a/dev/cuda/attention_backward.cu
+++ b/dev/cuda/attention_backward.cu
@@ -650,6 +650,7 @@ __global__ void softmax_autoregressive_backward_kernel7(...)
     if(warp.meta_group_rank() == 0) {
         block_acc[warp.thread_rank()] = 0;
     }
+    block.sync();
@@ -690,6 +691,7 @@ __global__ void softmax_autoregressive_backward_kernel8(...)
     if (warp.meta_group_rank() == 0) {
         block_acc[warp.thread_rank()] = 0;
     }
+    block.sync();
--- a/train_gpt2_fp32.cu
+++ b/train_gpt2_fp32.cu
@@ -462,6 +462,7 @@ __global__ void softmax_autoregressive_backward_kernel(...)
     if (warp.meta_group_rank() == 0) {
         block_acc[warp.thread_rank()] = 0;
     }
+    block.sync();
```

## 6. Already known?

- **Yes, proposed, not merged.**
  - https://github.com/karpathy/llm.c/pull/847, "Fix data race between two writes on a shared memory in soft_max_autoregressive_backward_kernel". Opened 2026-04-22 by ziqiaozhou, state **open**, no reviews or comments, one commit (ea74abf).
  - It describes exactly this WAW: "if warp 1 starts before warp 0, warp 0 may set that element to zero".
  - It was found by GitHub PR search "repo:karpathy/llm.c race" on 2026-10-25. The record's earlier `already_reported_check` ("No dedicated search yet") predates finding it.
- **Commits.** `git log --oneline f1e2ace6 -- dev/cuda/attention_backward.cu train_gpt2_fp32.cu` has no fix commit (the PR is unmerged). The pinned commit is `origin/master`. `git log --oneline --all -S'block_acc'` lists only commits that introduced or moved the code: `50e105a`, `a360f10`, `095d276` (fp32 checkpoint) and `b581810`.
- **Verdict.** For the paper this is **already reported upstream**, not new. cuRace detects a race that a third party had already found and proposed a fix for. PR #847 does not address the loop-carried WAR of finding llmc-new-3-2.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "Warp 0 initialises as its first instruction, while warp r stores only after a global-load loop and five shuffles. The bad order needs warp 0 to be descheduled for that long, which never happens."
- **Answer.**
  - Under PTX the two writes are unordered, a data race; nothing guarantees warps start together.
  - It did happen under racecheck's schedule: the program's own correctness check failed ("Mismatch of dpreatt"), and racecheck shows the WAW at exactly these lines with different values.
  - Natively it passes. The perturbation reproducer should make it deterministic.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` | TO BE RUN |
