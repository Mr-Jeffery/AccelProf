# Finding cuml-tsne-new-1-2: per-warp traversal stack in shared memory without `__syncwarp` (`RepulsionKernel`, lane 0 writes, all lanes read)

Repository rapidsai/cuml, pinned commit `c7e7738bb6386186bc031d821e71ce1c1abfe3c8`. Class **DR**, shared memory, intra-warp RAW (and WAR), warp-synchronous, formal only. Triage: `eval/realworld/candidates/triage/cuml-tsne-new-1.md`, group R3.

## 1. The accesses (`cpp/src/tsne/barnes_hut_kernels.cuh` @ c7e7738b)

| role | line | statement | SASS (traced R2 build) |
|---|---|---|---|
| write, root push (lane 0) | 624–627 | `if (SBASE_EQ_THREAD == true) { pos[sbase] = 0; node[sbase] = FOUR_NNODES; }` | `@!P0 STS [R0.X4], RZ` 0xdd0 (3536), `@!P0 STS [R0.X4+0x1000]` 0xde0 (3552) |
| read stack top (all lanes) | 631–632 | `auto pd = pos[depth]; auto nd = node[depth];` | `LDS` 0xe10 (3600), `LDS` 0xe40 (3648) |
| write, cell push (lane 0) | 654–657 | `if (SBASE_EQ_THREAD == true) { pos[depth] = pd; node[depth] = nd; }` | `@!P0 STS` 0x1110 (4368), 0x1130 (4400) |

`__shared__ value_idx pos[THREADS5], node[THREADS5]` (L567) are plain. The reference `cannylab/bh.cu` L594 declares them `volatile`. There is no `__syncwarp` in the kernel. The only `WARPSYNC` in the SASS belongs to the post-loop `__shfl_down_sync` (0x1700/0x1740) and to the divergent vote path.

## 2. Thread pair and why nothing orders it

- **Pair.** Warp 1: lane 0 (thread 32) stores `pos[32] = 0` and `node[32] = FOUR_NNODES` (L625/L626). Lane 1 (thread 33) loads `pos[32]` and `node[32]` (L631/L632).
  - Different threads, no `bar.warp.sync` and no `WARPSYNC`: unordered. Plain vs plain: DR (RAW).
- **Later pushes.** The same holds for the pushes at L655/L656 vs the reads at L631/L632 after `--depth`. It also holds for the WAR between lane 1's L631 read and lane 0's later L655 overwrite of the same stack slot.
  - The `__all_sync` (L647) does not help the reads: they come before it, and its own `dq[depth]` argument is read before the vote.
- **Effect.** A lane that reads a stale `pos`/`node` walks the wrong subtree, which gives wrong or missing force contributions.
- **In practice.** The warp is converged: all control decisions are warp-uniform through the shared stack and the vote, and `BSYNC` reconverges after lane 0's `if`. Formal only (T21 corpus note 4).

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/cuml-tsne-new-1-buggy.json`, scalar-clock, `kernel_10.json`)

- **Reports.** Two RACE reports, RAW, DR: `STS` 3536 → `LDS` 3600 (L625→L631) and `STS` 3552 → `LDS` 3648 (L626→L632).
  - Site verdicts `observed_distance: warp`, `edge_rescued: true`, weight 1. The last-accessor edge recorded only `intra_thread 32`; the event stream recorded the cross-lane conflict.
  - They are the oracle's `additional_pairs[0]`.
- **Coverage.** The pushes 0x1110/0x1130 (L655/L656) are absent from `kernel_10.json`'s `nodes`, so they never executed with the driver's input: every vote accepted the root's children. The push pairs are therefore untested on the upstream build. The reproducer's tree forces pushes.
- **Racecheck.** No information on this kernel (the print limit was filled by `BoundingBoxKernel`).

## 4. Reproducer (`eval/realworld/findings/repro/cuml-tsne-new-1-2/`)

- **`repro.cu`.** The tree walk L589–L664 copied (statements verbatim, `value_t = float`, some lines joined), on a full quadtree over a 32×32 grid of unit-mass bodies: 1,024 bodies, 341 cells, root = NNODES. One block of 1,024 threads, θ = 0.5, so the walk opens and pushes cells.
  - Trimmed: the `dq` prologue L565–L599 is replaced by a host-built `dq` copied once per warp, then `__syncthreads`. This keeps finding cuml-tsne-new-1's race out.
  - Trimmed: the force terms L648–L651 and L666–L678 become `normsum += massd[n]`. A correct walk accepts a set of nodes that partitions the bodies, so `normsum == N` exactly for every body.
- **`repro_fixed.cu`.** `__syncwarp(__activemask())` after the root push, after the L631/L632 reads, and after the cell push.
  - **Detector caveat.** The compile check shows ptxas 13.4 keeps only some of these as `WARPSYNC`: `repro_fixed` has 2 `WARPSYNC` against 1 in `repro`, not one per call.
  - Where the warp is provably converged ptxas drops the instruction. cuVein, which orders intra-warp pairs only at `WARPSYNC`, may therefore still report some pairs on `repro_fixed`. That is a model gap, not a remaining race under PTX.
- **`repro_perturb.cu`.** `__nanosleep(20000)` in lane 0 before each stack write.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings). Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/cpp/src/tsne/barnes_hut_kernels.cuh   (c7e7738b)
+++ b/cpp/src/tsne/barnes_hut_kernels.cuh
@@ -624,10 +624,12 @@
     if (SBASE_EQ_THREAD == true) {
       pos[sbase]  = 0;
       node[sbase] = FOUR_NNODES;
     }
+    __syncwarp(__activemask());
 
     do {
       // stack is not empty
       auto pd = pos[depth];
       auto nd = node[depth];
+      __syncwarp(__activemask());
 
@@ -654,5 +656,6 @@
           if (SBASE_EQ_THREAD == true) {
             pos[depth]  = pd;
             node[depth] = nd;
           }
+          __syncwarp(__activemask());
           depth++;
```

This matches the HeCBench fix of the same code (`40e3c96b`: `__syncwarp()` after the stack init, after loading pos/node, and at the end of each stack level).

## 6. Already known?

- **cuML.** As for cuml-tsne-new-1: issues #3816 and #2565 and the PR searches found nothing on the traversal stack.
- **Elsewhere.** The same warp stack race was fixed in HeCBench's bh (corpus record `hecbench-bh-1`, fix `40e3c96b`, 2026-04-18, credited to Burtscher; SuperCollider lists HeCBench bh). The original ECL/cannylab code avoids a data race by declaring `pos`/`node` `volatile`, which makes the accesses strong (SC class, not DR).
- **Commits.** The cuML port dropped `volatile`. That commit was not identified (the history of `bh_kernels.cuh` was not followed).
- **Verdict.** **New for cuML** as far as checked. Known as a pattern.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "Classic warp-synchronous code: the warp is converged, and `__all_sync` re-synchronises it every step."
- **Answer.**
  - Under PTX the lanes are separate threads and `shfl`/`vote` are not memory ordering (T21 corpus note 2). The reads at L631/L632 precede the vote in each iteration anyway. So this is a data race.
  - We claim formal only. The perturbation test is expected to show **no** wrong output, because reconvergence holds the readers. Report that plainly.
  - The volatile in the original turned it into strong accesses. The port's plain accesses also let the compiler legally cache `pos[depth]` in a register.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` (note the WARPSYNC caveat in section 4) | TO BE RUN |
| racecheck on `repro` | TO BE RUN |
