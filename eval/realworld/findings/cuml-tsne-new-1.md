# Finding cuml-tsne-new-1: the per-warp `dq` copy in `RepulsionKernel` runs without its barrier (`//__syncthreads();` at L598)

Repository rapidsai/cuml, pinned commit `c7e7738bb6386186bc031d821e71ce1c1abfe3c8`. Origin HEAD was identical when checked; `cpp/src/tsne` was unchanged. Class **DR**, shared memory. Two pairs on the one statement L596:
- cross-warp, **value-benign**: warp 0's self-copy;
- intra-warp: each warp's fresh copy, read before the vote.

Triage: `eval/realworld/candidates/triage/cuml-tsne-new-1.md`, groups R1 and R2.

## 1. The accesses

| role | file:line @ c7e7738b (`cpp/src/tsne/barnes_hut_kernels.cuh`) | statement | SASS (traced R2 build) |
|---|---|---|---|
| read `dq[diff]` (all threads) | 596 | `dq[diff + sbase] = dq[diff];` | `LDS R3, [R3.X4+0x2000]` 0xbd0 (3024) |
| write `dq[threadIdx.x]` (all threads) | 596 | (same) | `STS [R0.X4+0x2000], R3` 0xc00 (3072) |
| the missing barrier | 598 | `//__syncthreads();` | (none) |
| fence | 599 | `__threadfence_block();` | `MEMBAR.SC.CTA` 0xc10 |
| later read `dq[depth]` | 647 | `if ((n < N) or __all_sync(__activemask(), dxy1 >= dq[depth])) {` | `LDS R3, [R5+0x2000]` 0x1060 (4192), before `VOTE.ALL` 0x10a0 |

`__shared__ value_t dq[THREADS5]` (L568), THREADS5 = 1024. `dq[0..max_depth-1]` is written by thread 0 (L570–L583) before `__syncthreads` (L585). The launch is `<<<blocks * FACTOR5, THREADS5>>>` (`barnes_hut_tsne.cuh`).

## 2. Thread pairs and why nothing orders them

- **R1 (cross-warp, value-benign).** Block 0: thread 5 (warp 0, sbase 0) executes `dq[5] = dq[5]`, i.e. it writes `dq[5]`. Thread 37 (warp 1) reads `dq[5]` for `dq[37] = dq[5]`.
  - Both follow L585's barrier, and no barrier follows L596. `__threadfence_block()` is a fence executed by one thread. Without a matching strong access it synchronizes with nothing (PTX §8.7).
  - Plain vs plain, different warps: DR. The value stored equals the value already there, so this pair cannot change the output.
- **R2 (intra-warp, not value-benign).** Warp 1: lane 5 (thread 37) writes `dq[37]` (L596). Lane 0 (thread 32) reads `dq[32 + 5]` at L647 when `depth = sbase + 5`. The read is the argument of `__all_sync`, evaluated before the vote.
  - Before lane 5's write, `dq[32..1023]` holds uninitialised shared memory. A read before the write gives a garbage threshold, a wrong accept/open decision for the whole warp, and wrong forces.
  - Only the fence lies between the write and the read, and ptxas emitted no `WARPSYNC` on the converged path. So the pair is a DR.
  - It is formal in practice, because the warp is converged at L596.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/cuml-tsne-new-1-buggy.json`, scalar-clock, `kernel_10.json`, grid 68 × 1024)

- **R1.** Report `LDS` 3024 / `STS` 3072, WAR, DR. Site verdict WAR, `observed_distance: block`, `contested_weight 2112`, `ordering_syncs: []`. Edge `3072←3024`: `intra_thread 64, intra_block 2112`. Matched as the oracle's primary pair (`recall.csv`).
- **R2.** Report `STS` 3072 → `LDS` 4192, RAW, DR. Site verdict `observed_distance: warp`, `edge_rescued: true`, weight 1. The cross-lane conflict came from the event stream; the last-accessor edge saw only `intra_thread 32`. It is the oracle's `additional_pairs[1]`.
- **Racecheck.** Nothing about this kernel: its 2,000 displayed hazards were all `BoundingBoxKernel` (L122/L130), out of 800,261 errors.

## 4. Reproducer (`eval/realworld/findings/repro/cuml-tsne-new-1/`)

- **`repro.cu`.** `RepulsionKernel`'s prologue L565–L599 copied (statements verbatim, `value_t = float`), launched `<<<2 × SMs, 1024>>>`.
  - Trimmed: the tree walk L601–L678. It is replaced by a walk over the levels that reads `dq[depth]` for `depth = sbase .. sbase + max_depth - 1`, as L647 does. `pos`/`node` are dropped.
  - Check: every thread's sum of its warp's copy equals warp 0's, and matches the host value.
- **`repro_fixed.cu`.** L598's `__syncthreads()` restored.
- **`repro_perturb.cu`.** `__nanosleep(100000)` before the L596 copy, in warp 0 (R1) and in lanes 16..31 of every warp (R2), inside the branch that does the copy.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings): `repro` has 1 `BAR.SYNC`, `repro_fixed` 2. Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/cpp/src/tsne/barnes_hut_kernels.cuh   (c7e7738b)
+++ b/cpp/src/tsne/barnes_hut_kernels.cuh
@@ -596,5 +596,5 @@ CUML_KERNEL __launch_bounds__(
   dq[diff + sbase] = dq[diff];
 
-  //__syncthreads();
+  __syncthreads();
   __threadfence_block();
 
```

- This is what the reference code in the same repository does: `cpp/src/tsne/cannylab/bh.cu` L616–L617 at c7e7738b, i.e. `if (diff < MAXDEPTH) { dq[diff + j] = dq[diff]; }` followed by `__syncthreads();`, with `j = base * MAXDEPTH`.
- HeCBench's fix of the same code (below) instead skips the copy for warp 0 and adds `__syncwarp()`.

## 6. Already known?

- **cuML issues and PRs** (GitHub web search, 2026-10-25; the API search on rapidsai repositories was refused):
  - https://github.com/rapidsai/cuml/issues?q=tsne+race lists #3816 (TSNE hang, closed without a fix), #2565 ("[BUG] tSNE Lock up", merged 2020-07-29; it fixed races in cell allocation and in the `bottomd` decrement of the tree build, not the `dq` copy) and #8037 (symbol export).
  - The PR search "tsne syncthreads" returned nothing relevant (#8037, #1757).
  - Checked: https://github.com/rapidsai/cuml/pull/2565, https://github.com/rapidsai/cuml/issues/3816.
  - A web search for "cuml TSNE barnes hut race condition syncthreads RepulsionKernel …" found no report.
- **The same pattern, fixed elsewhere.** The HeCBench Barnes-Hut port (`src/bh-cuda/main.cu`, corpus record `hecbench-bh-1`, fix `40e3c96b`, 2026-04-18, "address memory access races in the kernel; appreciate Dr. Burtscher for the help") had the same `dq[diff+j] = dq[diff]` self-store and the same warp stack.
  - Its fix restricts the copy to base > 0 and adds `__syncwarp()`.
  - SuperCollider (PLDI 2026) lists HeCBench bh among the programs where it found races.
  - So the pattern is known in another code base, but nothing found reports it in cuML.
- **Commits.** `git log --oneline c7e7738b -- cpp/src/tsne/barnes_hut_kernels.cuh` in the partial clone lists one commit, `72758506` ("Warp-aggregate the attractive-force atomics in t-SNE (#8565)"). The earlier history (the file was `bh_kernels.cuh`) was not followed (`--follow` not run). `git log --oneline -S'//__syncthreads();' c7e7738b -- cpp/src/tsne` returned no commit in the partial clone, so the commit that commented the barrier out was not identified.
- **Verdict.** **New for cuML** as far as checked. Known as a pattern from HeCBench's fixed copy.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "R1 writes back the value it read: benign. R2 is inside one converged warp: lockstep."
- **Answer.**
  - R1 is still a data race under PTX. We count it as value-benign and never as an observable bug.
  - R2 is not value-benign: a lagging lane leaves uninitialised data in the slot that the vote reads. Under PTX nothing orders the lanes, because `MEMBAR.SC.CTA` is not a barrier.
  - The perturbation test is expected to produce **no** wrong output: the branch reconverges before the reads. Say so plainly if it stays OK.
  - The fix costs one barrier, and the reference code in the same repository has it.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` | TO BE RUN |
