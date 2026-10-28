# Finding llmc-new-2: `blockReduce` called in a loop without `final_sync` (shared_val reuse WAR) in `softmax_autoregressive_backward_inplace_kernel`

Repository karpathy/llm.c, pinned commit `f1e2ace651495b74ae22d45d1723443fd00ecd3a`, which equals `origin/master`. Class **DR**, shared memory, cross-warp and same-warp WAR. **Wrong output observed under racecheck.** Triage: `eval/realworld/candidates/triage/llmc-new-2.md`.

## 1. The accesses

| role | file:line @ f1e2ace6 | statement | SASS (traced build) |
|---|---|---|---|
| read, iteration `to` | `llmc/cuda_utils.cuh:177`, via `llmc/attention.cuh:176` | `warp_val = (lane_id < num_warps) ? shared_val[lane_id] : out_of_bounds;` | `@!P3 LDS R7, [R13]` 0xa90 |
| write, iteration `to+1` | `llmc/cuda_utils.cuh:175`, via `attention.cuh:176` | `if (lane_id == 0) { shared_val[warp_id] = warp_val; }` | `@!P0 STS [R25], R12` 0xa60 |
| the only barrier | `cuda_utils.cuh:176` | `__syncthreads();` | `BAR.SYNC` 0xa70 |
| the call in the loop | `attention.cuh:164`, `:176` | `for(int to = 0; to < T_per_block; ++to) { … local_sum = blockReduce<warpReduceSum>(local_sum); …` | the back edge `BRA` 0x17d0 |

`blockReduce`'s `final_sync` (L180–L182) defaults to `false`. The comment above `blockReduce` (`cuda_utils.cuh` L160–L163) says that "if called inside a loop, the shared memory will be implicitly reused, so set final_sync to 1". The call at `attention.cuh:176` sits inside such a loop and does not set it.

## 2. Thread pair and why nothing orders it

- **Cross-warp pair.** In block (0,0): thread 1 (warp 0, lane 1) loads `shared_val[1]` in iteration `to = 0`. Thread 32 (warp 1, lane 0) stores `shared_val[1]` in iteration `to = 1`.
  - The last barrier both executed is iteration 0's L176. Neither access is ordered before the other: same block, different warps, plain accesses. DR (WAR).
  - Between the two lie only the t3 global store loop and the next row's t2 load loop (`attention.cuh` L170–L188), with no barrier.
- **Same-warp pair.** Warp 1: lane 1 reads `shared_val[1]` in iteration `to`. Lane 0 writes it in iteration `to+1`.
  - Only `SHFL.BFLY` (full mask) separates them, and shuffles are not memory ordering (T21 corpus note 2). ptxas emitted no `WARPSYNC`, and the kernel has no `MEMBAR`.
  - The record's note that the intra-warp case is ordered by the shuffles is therefore corrected: it is part of the race.
- **Effect.** If the write lands first, the reader adds row `t0-1`'s warp partial into row `t0`'s `local_sum`, and the whole row's gradients are wrong.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/llmc-new-2-buggy.json`, scalar-clock)

- **Report.** 1 RACE report, `STS` 2656 / `LDS` 2704, WAR, shared, DR. The kernel summary has `races: 2`: site verdicts WAR 2656←2704 and RAW 2704←2656, both `observed_distance: block`, `ordering_syncs: []`.
- **Edges** (`kernel_0.json`, grid (16,1) × 256):
  - WAR `intra_warp 48, intra_block 336`.
  - RAW `intra_thread 45, intra_warp 19, intra_block 448`.
- **Racecheck** on the same binary (`eval/realworld/racecheck/llmc-new-2-buggy.txt`): totals 2105 errors and 348 warnings. Displayed: 955 WAR and 773 RAW errors plus 272 warp-level WAR warnings, all `cuda_utils.cuh:175` vs `:177`.
- **Output.** The driver's host check printed **`mismatches=279/4096`** under racecheck and `mismatches=0/4096` in 3/3 native runs.

## 4. Reproducer (`eval/realworld/findings/repro/llmc-new-2/`)

- **`repro.cu`.** `WARP_SIZE`, `warpReduceSum` and `blockReduce` copied from `cuda_utils.cuh`, and `softmax_autoregressive_backward_inplace_kernel` from `attention.cuh` L152–L190, launched as L266.
  - Trimmed: `floatX = float` instead of bf16, and comments.
  - B·NH = 1, T = 256 (rows up to 255, so all 8 warps carry data). 20 launches, host reference.
- **`repro_fixed.cu`.** `blockReduce<warpReduceSum>(local_sum, true)`.
- **`repro_perturb.cu`.** `if (warp_id == 0) __nanosleep(100000);` between L176's barrier and L177's read.
  - Warps 1–7 then run into the next iteration and store their next partials while warp 0 has not read yet. Expected: deterministic wrong output.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings). Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/llmc/attention.cuh   (f1e2ace6)
+++ b/llmc/attention.cuh
@@ -173,6 +173,6 @@ __global__ void softmax_autoregressive_backward_inplace_kernel(floatX* datt, const floatX* att,
             local_sum += (float)att_bth[t2] * (float)datt_bth[t2];
         }
 
-        local_sum = blockReduce<warpReduceSum>(local_sum);
+        local_sum = blockReduce<warpReduceSum>(local_sum, true);  // shared_val is reused by the next iteration
 
         for (int t3 = threadIdx.x; t3 < T; t3 += BlockSize) {
```

## 6. Already known?

- **Issues and PRs** (GitHub search, karpathy/llm.c, 2026-10-25):
  - PR search "blockReduce": #854 (ROCm build), #495 and #487 (removed unused dynamic shared memory from this kernel's launch; the discussion mentions `shared_val[WARP_SIZE]` but no race), #343, #378.
  - PR searches "race", "data race", "syncthreads": only #847 (llmc-new-3, a different kernel), #593, #303, #616, #472, #382, #336, #282. None concerns `blockReduce`.
  - Issue semantic search "race condition missing __syncthreads …": 0 results.
  - A web search for "karpathy llm.c blockReduce final_sync softmax_autoregressive_backward race shared_val" returned nothing relevant.
  - Checked: https://github.com/karpathy/llm.c/pull/487, https://github.com/karpathy/llm.c/pull/495.
- **Commits.** `git log --oneline f1e2ace6 -- llmc/attention.cuh llmc/cuda_utils.cuh` lists no `final_sync` or race commit. `git log --oneline --all -S'final_sync'` lists 7 commits that add or move `blockReduce`: `66b9755` (template + `out_of_bounds`), `9b55ea8`, `b581810`, `804d069`, `67502c7` (move to `cuda_utils.cuh`), `0f6853d`, `09910ac`. None changes the `attention.cuh` call or mentions a race (subjects only).
- **Verdict.** Nothing found describes this race. **New**, as far as checked. The code comment shows the authors knew the hazard in general.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "The window is tiny: between the read and the next write each warp runs a global store loop and a global load loop, so in practice nobody laps warp 0."
- **Answer.**
  - Under PTX the two accesses are unordered plain accesses, a data race, whatever the window.
  - The window is also reachable in practice: the same binary under racecheck's schedule printed `mismatches=279/4096`, while native printed 0. A different but legal warp schedule changes the output.
  - The perturbation reproducer should show it deterministically.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` | TO BE RUN |

