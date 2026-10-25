# Finding llmc-new-1: cross-block hand-off without release/acquire in `layernorm_backward_kernel10` (global scratch partials)

Repository karpathy/llm.c, pinned commit `f1e2ace651495b74ae22d45d1723443fd00ecd3a`, which equals `origin/master` (T21c step 1). Class **DR**, global memory, cross-block RAW, formal under PTX. Triage: `eval/realworld/candidates/triage/llmc-new-1.md`.

## 1. The accesses

| role | file:line @ f1e2ace6 | statement | SASS (traced build, sm_89) |
|---|---|---|---|
| write (block A) | `dev/cuda/layernorm_backward.cu:1194` | `store128(scratch_dbias + i + 2*C*blockIdx.x, load128(dbias_shared + i));` | `STG.E.128 [R2.64+0x80]` 0x4a50 |
| write (block A) | `:1195` | `store128(scratch_dweight + i + 2*C*blockIdx.x, load128(dweight_shared + i));` | `STG.E.128 [R12.64+0x80]` 0x4a60 (line table: 1194) |
| read (last block) | `:1214` | `f128 dbias128 = load128(scratch_dbias + offset);` | `LDG.E.128` 0x4e60, 0x4ed0, 0x4f00, 0x4f40 (line table: 1217) |
| read (last block) | `:1215` | `f128 dweight128 = load128(scratch_dweight + offset);` | `LDG.E.128` 0x4eb0, 0x4f20, 0x4f50, 0x4f60 (line table: 1218) |
| attempted hand-off | `:1197`, `:1201`, `:1203` | `__syncthreads(); … *tmp_flag = atomicInc(scratchFlag, gridDim.x); … __syncthreads();` | `BAR.SYNC` 0x4a90, `ATOMG.E.INC.STRONG.GPU` 0x4af0, `BAR.SYNC` 0x4b20 |

The production copy has the same statements at `llmc/layernorm.cuh` L371–L372 (stores), L378 (atomicInc) and L391–L392 (loads). It was not built. Kernels 6–9 of the dev file have the same hand-off; not built.

## 2. Thread pair and why nothing orders it

- **Pair.** In the 68-block × 512 launch, block 0 thread 0 stores `scratch_dbias[0..3]` (L1194). The block whose `atomicInc` returns `gridDim.x-1`, e.g. block 67, has thread 0 load the same 16 bytes at `read_block_idx = 0` (L1214). Cross-block.
- **What lies between.** Block 0's `bar.sync` (CTA scope), its thread 0's relaxed `atom.inc.gpu` on `scratch[0]`, the last block's own `atom.inc` and its `bar.sync`.
- **Why that is not enough.**
  - In PTX §8.7, a relaxed RMW is part of a release pattern only if a `fence.sc`/`fence.acq_rel` precedes it in the same thread.
  - The reader needs an acquire pattern: a fence after its strong read.
  - The kernel's SASS contains no `MEMBAR` at all. So no synchronizes-with edge exists across blocks, and `bar.sync` orders only within a CTA.
  - The store and the load are plain and overlap: a data race.
- **The author's own idiom.** The earlier kernel 5 in the same file has `__threadfence();` before its flag `atomicAdd` (L535). Kernels 6–10 and the production `layernorm.cuh` dropped it.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/llmc-new-1-buggy.json`, scalar-clock)

- **Reports.** 8 RACE reports, `space: global`, `race_type: RAW`, `conflict_class: DR`, each in all 6 kernel JSONs (grids 1088×32 … 68×512).
  - (0x4a50 → 0x4e60, 0x4ed0, 0x4f00, 0x4f40) is the dbias half.
  - (0x4a60 → 0x4eb0, 0x4f20, 0x4f50, 0x4f60) is the dweight half.
- **Site verdict.** `observed_distance: grid`, `ordering_syncs: [19088, 19232]` (the two `BAR.SYNC`), `atomic_coherence: none`.
- **Edges.** E.g. `kernel_4.json` 0x4e60←0x4a50: `intra_grid 25600, intra_thread 1600`.
- **Scoring.** `recall.csv` matched the four L1217 reports. The four L1218 reports are in `other_reports.csv`. They are the same race (the line table tags each load with its first use; see the triage).

## 4. Reproducer (`eval/realworld/findings/repro/llmc-new-1/`)

- **`repro.cu`.** The kernel tail L1183–L1223 copied: the scratch stores, `__syncthreads`, `atomicInc` into shared `tmp_flag`, `__syncthreads`, and the last block's load loop.
  - Trimmed: the row loop L1083–L1182, replaced by each block writing known values (`b+1`, `2(b+1)`) into `dbias_shared`/`dweight_shared`; and the bf16 write-back L1226–L1248, replaced by the last block writing its sums to `out`.
  - `f128`/`load128`/`store128` are reduced to a 4-float struct with the same `int4` reinterpret.
  - C = 1600, block 512, grid = 2 × SMs, as `layernorm_backward10()`. 200 launches; the host checks the sums exactly.
- **`repro_fixed.cu`.** `__threadfence()` before and after the `atomicInc` in thread 0.
- **`repro_perturb.cu`.** `__nanosleep(20000)` in odd blocks just before their partial stores, so their stores are the last memory operations before their barrier and atomic.
- `build.sh` and `expected.md`. Compile-checked on a `normal` node with CUDA 13.4: all three compile with 0 warnings; `repro_fixed` has 2 `MEMBAR`, the others 0. Not run.

## 5. Minimal fix (against the pinned source)

```diff
--- a/dev/cuda/layernorm_backward.cu   (f1e2ace6)
+++ b/dev/cuda/layernorm_backward.cu
@@ -1199,5 +1199,7 @@
     unsigned int *tmp_flag = (unsigned int*)(shared + 2*rounded_C);
     if (threadIdx.x == 0) {
+        __threadfence();  // release: publish this block's scratch partials (ordered after them by the __syncthreads above)
         *tmp_flag = atomicInc(scratchFlag, gridDim.x);
+        __threadfence();  // acquire: the last block must see every other block's partials
     }
     __syncthreads();
```

- The same two lines go into `llmc/layernorm.cuh` around L378, and into kernels 6–9 of the dev file.
- An alternative is `cuda::atomic_ref<unsigned, cuda::thread_scope_device>` with `fetch_add(…, memory_order_acq_rel)`.

## 6. Already known?

- **Issues and PRs** (GitHub search, karpathy/llm.c, 2026-10-25):
  - PR searches "race", "data race", "syncthreads", "threadfence", "layernorm backward scratch" found no fence/hand-off report. The race hits were #847, which is llmc-new-3, and unrelated PRs (#593, #303, #128…).
  - Issue search "race condition missing __syncthreads or __threadfence shared memory": 0 results.
  - The record's earlier search (issues #190, #428, #794, #176, #178) found nothing either.
  - A web search for "llm.c layernorm_backward_kernel10 threadfence scratch atomicInc race" returned nothing relevant.
  - URLs checked: https://github.com/karpathy/llm.c/pull/847, https://github.com/karpathy/llm.c/pull/487, https://github.com/karpathy/llm.c/pull/495.
- **Commits.** `git log --oneline f1e2ace6 -- dev/cuda/layernorm_backward.cu llmc/layernorm.cuh` in `~/incoming/realworld/cand/llm.c.git` lists no fence- or race-related commit. The nearest are `f27ca4d fix the issue Mismatch of dweight`, `d35daf1 fail fast and hard; don't go into the deadlock` and `5f73ecf fix C % 256 != 0`.
  - `git log --oneline --all -S'threadfence'` finds two commits. `8768f6b` (2024-04-28, "Full BF16 including layernorm at good perf by minimising BF16 atomics") added the fenced last-block kernel to `train_gpt2.cu`. `82fef03` (2024-04-29, "Use kernel6 for train_gpt2, and add all other kernels to /dev/cuda (+bugfixes)") removed that `__threadfence()` from `train_gpt2.cu`, moved the fenced kernel into `dev/cuda` as kernel 5, and switched training to the unfenced kernel 6.
  - So the production path lost the fence on 2024-04-29 with the switch to kernel 6. The commit message does not mention the fence.
- **Verdict.** Nothing found describes this race. **New**, as far as checked.

## 7. Skeptic's strongest objection and the PTX answer

- **Objection.** "It cannot fail on real GPUs."
  - The stores are issued before the barrier; the atomic is issued after it by the same SM and executes at L2.
  - SM-to-L2 traffic is in order for a single SM, so the partials reach L2 first.
  - The last block reads with `LDG` that miss its L1 (the lines were never loaded there).
  - No failure was observed: 3/3 native runs match.
- **Answer.** Under the PTX memory model, which is the contract the compiler and future hardware keep, the program has a data race. Its behaviour is then not defined by the model.
  - The author's own kernel 5 shows the intended idiom.
  - The compiler may legally sink or cache the weak loads; nothing in the source forbids it.
  - We claim a formal race. We claim no observed corruption.
- **Racecheck.** It cannot report this pair: it checks only shared memory ("Currently, this tool only supports detecting accesses to on-chip shared memory.", Compute Sanitizer v2026.3.0 docs). cuRace reports it from one run.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb` | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` (expected: no hazards, global memory) | TO BE RUN |
