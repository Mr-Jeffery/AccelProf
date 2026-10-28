# Finding cuml-tsne-new-1-5: lock-free quadtree build publishes `childd` with plain accesses (`TreeBuildingKernel`, `childd` lost its `volatile`)

Repository rapidsai/cuml, pinned commit `c7e7738bb6386186bc031d821e71ce1c1abfe3c8`. Class **DR**, global memory, cross-block and cross-warp: mixed atomic/plain and plain/plain conflicts on `childd`. Formal under PTX. This is a lock-free design whose correctness rests on CAS re-validation and on the L1 invalidation inside `__threadfence`. **Not in the oracle.** Triage: `eval/realworld/candidates/triage/cuml-tsne-new-1.md`, groups T1–T4.

## 1. The accesses (`cpp/src/tsne/barnes_hut_kernels.cuh` @ c7e7738b, `TreeBuildingKernel<int,float>`, `childd` declared `value_idx* restrict childd`, L194)

| role | line | statement | SASS (traced R2 build) |
|---|---|---|---|
| traversal read (plain) | 239 | `while ((ch = childd[n * 4 + j]) >= N) {` | `LDG.E` 0x2d0 (720), 0x390 (912) |
| insert into empty slot (CAS) | 259 | `atomicCAS(&childd[locked], (value_idx)-1, i)` | `ATOMG.E.CAS.STRONG.GPU` 0xa60 (2656) |
| lock a full slot (CAS → −2) | 268 | `ch == atomicCAS(&childd[locked], ch, (value_idx)-2)` | `ATOMG.E.CAS.STRONG.GPU` 0x4d0 (1232) |
| build the new cells (plain) | 283, 291, 299, 303 | `childd[n * 4 + j] = cell;` `childd[cell * 4 + j] = ch;` `ch = childd[n * 4 + j];` `childd[n * 4 + j] = i;` | `STG.E` 0x830, 0x8c0; `LDG.E` 0x960; `STG.E` 0x9f0 |
| fence, then unlock (plain) | 313, 315 | `__threadfence(); if (skip == 2) childd[locked] = patch;` | `MEMBAR.SC.GPU; ERRBAR; CCTL.IVALL` 0xaf0–0xb20, `@!P0 STG.E` 0xb40 (2880) |

The launch is `<<<blocks * FACTOR2, THREADS2>>>` (`barnes_hut_tsne.cuh` L225), i.e. 3 × SMs blocks of 512.

## 2. Thread pair and why nothing orders it

- **Pair (T2/T4).** Thread A finds slot `locked` occupied by body `ch` and locks it: CAS → −2 (L268).
  - It allocates cell c with `atomicAdd(bottomd, -1)`, stores `childd[c*4 + j1] = ch` (L291) and `childd[c*4 + j2] = i` (L303, plain), and executes `__threadfence()` (L313).
  - It then unlocks with `childd[locked] = c` (L315, **plain**).
- **Reader.** Thread B, in another block (edges show `intra_grid`), descends through `locked`. It reads `childd[locked] = c` (L239, plain) and then `childd[c*4 + j]` (L239, plain).
- **Why that is a DR.**
  - A release pattern needs a fence followed by a **strong** write. L315 is weak, so A's fence releases nothing.
  - An acquire pattern needs a strong read followed by a fence. B's reads are weak.
  - No synchronizes-with edge exists, so A's L291/L303 stores and B's L239 loads are an unordered plain/plain conflict: DR.
- **T1/T3.** The CAS pairs (L259/L268 vs L239/L291/L303) are atomic vs plain on the same word. Those are not morally strong, so also DR.
- **Why it works in practice.**
  - A thread that reads a stale `-1` tries CAS(−1 → i), which fails against the real value and retries after the next `__threadfence`. On sm_89 that fence also emits `CCTL.IVALL`, which invalidates L1.
  - A stale −2 (locked) only causes a retry.
  - The risky case is a stale *cell* entry read during descent (L239, inside the inner loop, no fence). It needs a cached L1 line from a neighbouring cell. Possible in principle, not tested.
- **Reference code.** `cpp/src/tsne/cannylab/bh.cu` L218 declares `volatile int* const __restrict__ childd`, which makes every access strong (SC class at worst, no DR). The cuML port dropped the `volatile`.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/cuml-tsne-new-1-buggy.json`, `kernel_6.json`, grid 102 × 512)

- **Reports.** 16 RACE reports, DR, global, all in `other_reports.csv`:
  - L239 vs CAS L259/L268: 4 (720/912 vs 1232/2656);
  - L239 vs `STG` L283/L291/L303/L315: 7;
  - CAS L268 vs `STG` L291/L303: 2;
  - `STG` L291/L303 → `STG` L315 and `LDG` L299 → `STG` L315: 3.
- **Edges.** E.g. `720←1232`: `intra_thread 30, intra_warp 2, intra_block 56, intra_grid 62`. `912←1232`: `intra_block 135, intra_grid 133`.
- **Racecheck.** Not applicable: global memory.

## 4. Reproducer (`eval/realworld/findings/repro/cuml-tsne-new-1-5/`)

- **`repro.cu`.** `TreeBuildingKernel` L192–L324, statements copied (several joined per line, comments dropped, `value_idx = int`).
  - Input: 50,000 random points in [0,1)², root at (0.5, 0.5), radius 0.5 + 1e-5, `childd = -1`, `bottom = NNODES`. That is the state `ClearKernel1`/`BoundingBoxKernel`/`Reset_Normalization` leave. Grid 3 × SMs × 512, 20 launches.
  - The host walks the tree from the root. It must find each body exactly once, no cycle and no leftover lock (−2).
- **`repro_fixed.cu`.** `childd` declared `volatile int*`, as in the reference, with the atomics cast back to `int*`. The compile check shows 12 `.STRONG` accesses against 5.
  - cuVein will still report **SC** pairs on it: strong vs strong conflicts, the intended lock-free protocol. The DR pairs should disappear.
- **`repro_perturb.cu`.** `__nanosleep(20000)` while a thread holds a lock, before L313/L315. Readers spin longer on locked slots and newly built cells.
- Compile-checked (CUDA 13.4, sm_89, 0 warnings). Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/cpp/src/tsne/barnes_hut_kernels.cuh   (c7e7738b)
+++ b/cpp/src/tsne/barnes_hut_kernels.cuh
@@ -193,3 +193,3 @@
 CUML_KERNEL __launch_bounds__(THREADS2) void TreeBuildingKernel(/* int *restrict errd, */
-                                                                value_idx* restrict childd,
+                                                                volatile value_idx* restrict childd,
                                                                 const value_t* restrict posxd,
```

The two `atomicCAS(&childd[locked], …)` calls (L259, L268) then need `(value_idx*)&childd[locked]`. An alternative is `cuda::atomic_ref` with release on the L315 unlock and acquire on the L239 reads.

## 6. Already known?

- **cuML.** PR #2565 ("[BUG] tSNE Lock up", merged 2020-07-29) fixed *other* races in this kernel: cell index selection, which allowed loops in the tree, and the `bottomd` decrement. That shows the kernel has a history of races. It did not concern the plain `childd` publication (page checked: https://github.com/rapidsai/cuml/pull/2565).
  - Issue #3816 (TSNE stuck at gradient updates, 2021) was closed without a diagnosis.
  - No issue or PR found about `volatile`/plain `childd`.
- **Commits.** The commit that dropped `volatile` was not identified.
- **Verdict.** **New**, as far as checked. It is related to the fixed #2565 class.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "This is Burtscher's published lock-free algorithm. Every stale read is caught by a failing CAS or retried after a fence, so it is benign by design."
- **Answer.**
  - The published algorithm uses `volatile` for exactly this reason. With plain accesses the PTX model calls these data races, so the compiler may cache or reorder the weak loads.
  - The guarantee that keeps it working (`CCTL.IVALL` inside `MEMBAR.GPU`) is a property of current hardware, not of the PTX contract.
  - The descent read at L239 inside the inner loop has no CAS check. A stale cell entry there would route a body down a stale path, and the host check catches that.
  - We claim a formal race. A wrong tree is not expected natively.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` (`repro_fixed`: SC reports expected, no DR) | TO BE RUN |
| racecheck (n/a: global memory) | not applicable |
