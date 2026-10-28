# Finding cuml-tsne-new-1-3: `__syncthreads()` inside a loop whose trip count depends on `threadIdx.x` (`BoundingBoxKernel` min/max reduction)

Repository rapidsai/cuml, pinned commit `c7e7738bb6386186bc031d821e71ce1c1abfe3c8`. Class **DR**, shared memory, cross-warp and same-warp RAW. Formal under the PTX memory model; it also breaks the CUDA rule for barriers in conditional code. **Not in the oracle**: found among the other reports. It is also what all 2,000 displayed racecheck hazards of this target are. Triage: `eval/realworld/candidates/triage/cuml-tsne-new-1.md`, groups B1 and B2.

## 1. The accesses (`cpp/src/tsne/barnes_hut_kernels.cuh` @ c7e7738b, `BoundingBoxKernel<int,float>`)

| role | line | statement | SASS (traced R2 build) |
|---|---|---|---|
| initial write (every thread i) | 122–125 | `sminx[i] = minx; smaxx[i] = maxx; sminy[i] = miny; smaxy[i] = maxy;` | `STS` 0x260 (608), 0x290, 0x2a0, 0x2b0 |
| the loop and its barrier | 127–128 | `for (auto j = THREADS1 / 2; j > i; j /= 2) { __syncthreads();` | `WARPSYNC 0xffffffff` 0x2f0 + `BAR.SYNC` 0x300 |
| read partner, write own | 130–133 | `sminx[i] = minx = fminf(minx, sminx[k]);` … (k = i + j) | `LDS` 0x350 (848) / `STS` 0x370 (880), … `LDS` 0x3e0 / `STS` 0x400 |
| exit of threads i ≠ 0 | 136 | `if (i == 0) { … }` | `@P1 EXIT` 0x420 |

THREADS1 = 512. The launch is `<<<blocks * FACTOR1, THREADS1>>>` (`barnes_hut_tsne.cuh` L200).

## 2. Thread pairs and why nothing orders them

- **The loop.** For thread i the loop runs while `j > i`.
  - Threads i ≥ 256 never enter it and never execute `__syncthreads()`.
  - Thread k enters iteration j only if k < j. After its last iteration it leaves the loop and, since k ≠ 0, exits.
- **B1 pair (L122 → L130).** Thread 300 (warp 9) stores `sminx[300]` (L122) and exits without executing any barrier. Thread 44 (warp 1) executes `BAR.SYNC` (j = 256) and then loads `sminx[44 + 256]` (L130).
  - In PTX §8.7, CTA-scope synchronization comes only from barrier operations. Thread 300 performs none, so there is no synchronizes-with edge from its store to thread 44's load. Plain vs plain: DR.
- **B2 pair (L130 → L130).** Thread 3 stores `sminx[3]` in iteration j = 4 (4 > 3). It then leaves the loop (2 > 3 is false) and exits. Thread 1 loads `sminx[1 + 2]` after iteration j = 2's barrier, which thread 3 never executes. DR (same-warp here; cross-warp for j ≥ 32).
- **Why it works in practice.** A CTA barrier completes when every non-exited thread has arrived. The PTX `exit` description, paraphrased (not re-read verbatim), releases a barrier that waits only on exiting threads. So thread 44's `bar.sync` returns only after thread 300 has exited, which is after its store.
  - That is a scheduling guarantee. The memory model gives `exit` no ordering, so the race is formal.
  - The CUDA C++ Programming Guide allows `__syncthreads()` in conditional code "only if the conditional evaluates identically across the entire thread block". Wording as quoted in NVIDIA forum threads; the current guide was not re-read. This loop violates that rule.
- **Origin.** The reference `cpp/src/tsne/cannylab/bh.cu` L134–L136 in the same repository uses `for (j = THREADS1 / 2; j > 0; j /= 2) { __syncthreads(); if (i < j) { … } }`, which is uniform. The cuML port moved `i < j` into the loop condition.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/cuml-tsne-new-1-buggy.json`, `kernel_4.json`, grid 102 × 512)

- **Reports.** 8 RACE reports, RAW, DR, shared:
  - B1: `STS` 608/656/672/688 → `LDS` 848/896/944/992 (L122–L125 → L130–L133).
  - B2: `STS` 880/928/976/1024 → `LDS` 848/896/944/992 (L130–L133 → itself).
  - All 8 are in `other_reports.csv`.
- **Edges.** `848←608`: `intra_block 26112`. `848←880`: `intra_warp 3162, intra_block 22848`.
- **Racecheck** (`eval/realworld/racecheck/cuml-tsne-new-1-buggy.txt`): 800,261 errors and 382 warnings. All 2,000 displayed are `Potential RAW hazard`, Write `BoundingBoxKernel<int,float>+0x260` (L122) vs Read `+0x350` (L130).
- **Output.** The driver printed a finite result (`finite=2000/2000`) under racecheck and natively. The native checksum varies in the 7th digit across runs, which is not attributed to this race.

## 4. Reproducer (`eval/realworld/findings/repro/cuml-tsne-new-1-3/`)

- **`repro.cu`.** `BoundingBoxKernel` L81–L142 copied: the body loop, the shared reduction with the non-uniform loop, and thread 0's per-block result store.
  - Trimmed: the cross-block combine L143–L166 and the unused pointer arguments.
  - 2^20 random points, grid 3 × SMs, block 512, 20 launches. The host checks every block's min/max exactly.
- **`repro_fixed.cu`.** `for (j = THREADS1 / 2; j > 0; j /= 2) { __syncthreads(); if (i >= j) continue; … }`, the uniform form. The compile check shows 9 `BAR.SYNC` (unrolled) against 1.
- **`repro_perturb.cu`.** `__nanosleep(100000)` for threads i ≥ 256 before their L122–L125 stores, so the writers that never barrier store late.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings). Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/cpp/src/tsne/barnes_hut_kernels.cuh   (c7e7738b)
+++ b/cpp/src/tsne/barnes_hut_kernels.cuh
@@ -127,7 +127,8 @@ CUML_KERNEL __launch_bounds__(THREADS1) void BoundingBoxKernel(value_idx* restrict startd,
-  for (auto j = THREADS1 / 2; j > i; j /= 2) {
+  for (auto j = THREADS1 / 2; j > 0; j /= 2) {
     __syncthreads();
+    if (i >= j) continue;  // every thread reaches every barrier
     const auto k = i + j;
     sminx[i] = minx = fminf(minx, sminx[k]);
     smaxx[i] = maxx = fmaxf(maxx, smaxx[k]);
     sminy[i] = miny = fminf(miny, sminy[k]);
     smaxy[i] = maxy = fmaxf(maxy, smaxy[k]);
```

Thread 0's result is unchanged.

## 6. Already known?

- **cuML.** The web issue search "tsne race" found #3816, #2565 and #8037, none about the bounding-box reduction; #2565 fixed tree-build races. The PR search "tsne syncthreads" found nothing relevant. Web search: nothing.
- **Elsewhere.** HeCBench's bh fix `40e3c96b` (record `hecbench-bh-1`) concerns the force kernel only, not the bounding box. The original ECL/cannylab code has the uniform loop.
- **Commits.** The commit that introduced `j > i` was not identified (the history before `72758506` was not followed). `git log -S'j > i; j /= 2' c7e7738b -- cpp/src/tsne` failed in the partial clone (`error: Could not stat objects/pack/tmp_pack_…` during lazy fetch). Not checked.
- **Verdict.** **New**, as far as checked.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "Threads that skip the loop exit right away, and `bar.sync` waits for them to exit. So their stores are complete before anyone reads: it is ordered."
- **Answer.**
  - That ordering comes from the hardware's barrier-release-on-exit scheduling rule, not from the PTX memory model. In the model only barrier operations synchronize, and the writer executes none.
  - The CUDA programming guide forbids `__syncthreads()` in non-uniform conditional code, and this loop is such code.
  - Both racecheck and cuRace report it.
  - We claim a formal race and no observed corruption. The perturbation test is expected to stay correct; report that plainly.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` and `repro_fixed` | TO BE RUN |
