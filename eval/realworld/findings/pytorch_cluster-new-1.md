# Finding pytorch_cluster-new-1: in-place stride-doubling argmax reduction races in `fps_kernel` (torn value/index pair)

**Status:** class (a) DR. A wrong result needs a torn (value, index) read. Racecheck's schedule changed the output (61/256 mismatches vs 0 natively). The two-sided perturbation forces the tear. Verifier: not yet (step 5).
**Repository:** rusty1s/pytorch_cluster at `e9a855c284b45edcbf0282cf70ac09bee0ce4e49` (equal to the fetched default branch; the repository is deprecated in favour of pyg-lib, commit #271).
**Lineage:** independent of the PointNet++ FPS family. It uses a different reduction and has a different race. The same author fixed the same reduction shape in `nearest_cuda.cu` (commit `a5abfee`, 2020-12-07) but not in `fps_cuda.cu`.

## 1. The accesses

File `csrc/cuda/fps_cuda.cu`, kernel `fps_kernel<float>` (`THREADS` = 256), reduction loop L51–L58, unrolled for i = 1, 2, …, 128. Per step, the SASS of the built driver is:
- `BAR.SYNC` (L52);
- `LDS R0, [R3.X4]` (own slot);
- `LDS R2, [R3.X4+4i]` (**read** `best_dist[t+i]`, L54; the L55 re-load is merged into it);
- `@!P5 LDS.64 R6, [R3.X8+0x400+8i]` (**read** `best_dist_idx[t+i]`, L56);
- `@!P5 STS [R3.X4], R2` (**write** `best_dist[t]`, L55);
- `@!P5 STS.64 [R3.X8+0x400], R6` (**write** `best_dist_idx[t]`, L56).

| step i | value read / write pcs | index read / write pcs |
|---|---|---|
| 1 | 5168 / 5216 | 5200 / 5232 |
| 2 | 5344 / 5392 | 5376 / 5408 |
| 4 | 5520 / 5568 | 5552 / 5584 |
| 8 | 5680 / 5728 | 5712 / 5744 |
| 16 | 5840 / 5888 | 5872 / 5904 |
| 32 | 6000 / 6048 | 6032 / 6064 |
| 64 | 6160 / 6208 | 6192 / 6224 |

Step 128 has no conflict: slots ≥ 128 are never written. All accesses are plain; no `WARPSYNC` is emitted.

## 2. Thread pair and why nothing orders it

- **Cross-warp:** step i = 64, block 0. Thread 0 (warp 0) reads `best_dist[64]` and `best_dist_idx[64]`. Thread 64 (warp 2) evaluates `best_dist[64] < best_dist[128]` and overwrites both slots.
- Both accesses lie between the L52 barrier of step 64 and the L52 barrier of step 128, with no barrier between them. So no causality order exists under PTX §8.7.1, and this is a data race.
- Racecheck shows the cross-warp form at warp boundaries too, e.g. Read 95 / Write 96 (i = 1) and Read 30 / Write 32 (i = 2).
- **Intra-warp, i < 32:** e.g. Read 161 / Write 162. PTX orders lanes of a warp only through `bar.warp.sync` (none here), so these are DR as well. In practice a converged warp issues all `LDS` before any `STS`, so they read the old values.

## 3. Trace evidence (`eval/results/realworld_t21c/attrib/pytorch_cluster-new-1-buggy.json`, scalar-clock)

- 14 reports, all WAR, `RACE`, `strength none`, `DR`. For each step in the table, `LDS fps_cuda.cu:54` / `STS :55` and `LDS.64 :56` / `STS.64 :56`. `n_race 14`, `n_sc 0`, no other reports.
- Reuse edges show both relations:
  - `5216 ← 5168` (i = 1): `intra_warp 31486, intra_block 1142`;
  - `6048 ← 6000` (i = 32): `intra_block 23789, intra_warp 0`.
- `hb_sync_pass` lists the 14 pc pairs (counts 32628 … 4289).
- Racecheck (print limit 2000; displayed hazards are in steps 1, 2, 4 only): mostly same-warp WAR warnings, cross-warp WAR errors, and 4 RAW errors (`W@0x15c0/R@0x1590`, a reader that saw the new value).
- Driver's host reference (plain FPS on random floats): native `0/256` mismatches (3 runs); under racecheck `61/256`.

## 4. When is the race harmful? (reasoning, then the reproducer)

- **Newer consistent pair.** Thread t may read slot t+i either before or after thread t+i updated it. A consistent newer (value, index) pair is harmless. The value is the max over a superset of slots, `<` is strict, and later steps still cover every slot.
- **Old value, new index.** Slot t gets an under-estimated value with the index of a farther point. In the cases worked through (reader thread 0, i = 1 … 64), the next step reads a slot whose range contains that farther point with its true value, which corrects it. This was not proved for every interleaving.
- **New value, old index.** This is harmful.
  - At i = 64, thread 0 loads `best_dist[64]` after thread 64 stored the value copied from slot 128, but loads `best_dist_idx[64]` before thread 64 stored the index.
  - Slot 0 now holds the global maximum value with the index of the best point in 64..127, which is a smaller distance.
  - At i = 128, `best_dist[0] < best_dist[128]` is false for the equal value, so `out[m]` is a point that is not the farthest one.
  - This needs the reader's value load to fall after the writer's value store and the reader's index load to fall before the writer's index store. One delay on one side cannot create it: the reader normally loads well before the writer stores.

**Reproducer:** `eval/realworld/findings/repro/pytorch_cluster-new-1/`.
- **`repro.cu`** (56 lines):
  - `fps_kernel` copied from L7–L65. Trimmed: blank lines and the torch host function `fps_cuda`; statements joined (whitespace only); comments added on the racing lines.
  - Launch `<<<B = 2, THREADS = 256>>>`, N = 512 points per batch, M = 128, `dist = 5e4` (as `fps_cuda`), `start = 0`.
  - Integer coordinates in [0, 100): squared distances are exact in fp32 and stay below 5e4.
  - The host checks that every `out[m]` is a farthest point given the GPU's own previous picks.
- **`repro_fixed.cu`** (54 lines): the loop replaced by the pairwise tree upstream used for `nearest_cuda.cu` in `a5abfee`, with `<` (max) instead of `>`. In step u, writers touch even multiples of 2^(u+1) and readers odd multiples of 2^u, so no slot is both read and written in one step. Marked `FIX`.
- **`repro_perturb.cu`** (60 lines) runs the same input three times, with `g_mode` = 0, 1, 2. The delays apply only to step i = 64 (marked `PERTURB`).
  - **mode 0:** no delay.
  - **mode 1, one side only:** writer thread 64 waits 400 000 cycles between its value store (L55) and its index load/store (L56).
  - **mode 2:** mode 1 plus reader thread 0 waiting 20 000 cycles before its L54 loads. This forces the new-value/old-index tear whenever thread 64 updates slot 64. A wrong pick then follows whenever the farthest point's slot is in 128..191 and strictly beats 0..127, which happens in roughly a quarter of the iterations with random data (estimate, not measured).
  - SASS (the loop is not unrolled in this build): the reader delay (`NANOSLEEP` at 0x1150) precedes the `LDS`s at 0x1250/0x1270. The writer's `STS` value at 0x12c0 precedes its delay (0x1370), which precedes `LDS.64`/`STS.64` at 0x1420/0x1430.
- **Compile check:** all three compiled on a `normal` node with CUDA 13.4 (`build.sh`). Not run.
- The `repro` SASS has the same LDS/LDS.64/STS/STS.64 order per step as the upstream build.

## 5. Minimal fix (diff against the pinned source)

This is the same rewrite upstream applied to `nearest_cuda.cu` in `a5abfee` ("fix nearest parallel reduction"), with the comparison flipped for a max.

```diff
--- a/csrc/cuda/fps_cuda.cu
+++ b/csrc/cuda/fps_cuda.cu
@@ -48,12 +48,15 @@
     best_dist[thread_idx] = best;
     best_dist_idx[thread_idx] = best_idx;
 
-    for (int64_t i = 1; i < THREADS; i *= 2) {
+    for (int64_t u = 0; (1 << u) < THREADS; u++) {
       __syncthreads();
-      if ((thread_idx + i) < THREADS &&
-          best_dist[thread_idx] < best_dist[thread_idx + i]) {
-        best_dist[thread_idx] = best_dist[thread_idx + i];
-        best_dist_idx[thread_idx] = best_dist_idx[thread_idx + i];
+      if (thread_idx < (THREADS >> (u + 1))) {
+        int64_t idx_1 = (thread_idx * 2) << u;
+        int64_t idx_2 = (thread_idx * 2 + 1) << u;
+        if (best_dist[idx_1] < best_dist[idx_2]) {
+          best_dist[idx_1] = best_dist[idx_2];
+          best_dist_idx[idx_1] = best_dist_idx[idx_2];
+        }
       }
     }
```

A smaller alternative: keep the stride-doubling, load slot t+i into registers, add a `__syncthreads()`, then store. This costs one extra barrier per step. It is not chosen because upstream's own fix for the sibling kernel is the tree.

## 6. Already known?

- **Issues:**
  - GitHub issue search in rusty1s/pytorch_cluster:
    - "fps cuda race condition wrong sampled index reduction": 0;
    - "fps returns wrong or duplicate indices on GPU": #148 "gpu execution error", #49 "fps seems broken", #3 "Data on different GPUs";
    - "fps CUDA differs from CPU farthest point sampling result": #90 (CPU performance), #91 "Possible bug in the gpu implementation of the nearest method".
  - **#49** (2020-02-03): all CUDA fps indices are 0. It predates the current kernel (rewritten 2020-03, commits `06d9038` … `5f855a2`). No cause is given.
  - **#91** (2020-12-04) is the sibling. GPU `nearest` gave different results from CPU, and the maintainer answered that "there was a bug in the parallel reduction scheme". The fix is `a5abfee` (2020-12-07), which rewrote the `nearest_cuda.cu` reduction and also changed a `continue` to `break` in the batch lookup. `fps_cuda.cu` was not touched and is not mentioned.
  - Web search "pytorch_cluster fps_cuda race condition best_dist reduction": nothing relevant. The torch-cluster changelog (pyup.io) mentions an unspecified CUDA fps bug fix in 1.5.4 (2020), before the pinned code, which still has the race.
- **Commits** (`~/incoming/realworld/pytorch_cluster.git`): `git log` of `csrc/cuda/fps_cuda.cu` at the pinned commit lists `49e0fe8` (2024-04-15 update #213), `01fa24e`, `e8620a8` (half support), `53959ee`, `82968b9`, `5f855a2` (fix illegal memory access), `9c33077` (fix fps implementation), `bc47687`, `9436b36`, `8c8014b`, `5a485e9`, `06d9038` (fps kernel, 2020-03-12), `4a61d70`. None changes the reduction scheme.
- **Verdict:** this race in `fps_cuda.cu` is not described anywhere found. The same reduction shape was recognised as buggy and fixed in `nearest_cuda.cu` by the maintainer (#91 / `a5abfee`). That strongly suggests a fix would be accepted, but the repository is deprecated.

## 7. Skeptic's strongest objection and the PTX answer

**Objection:** "A max-reduction is monotone. Reading a newer value is harmless, so the race is benign. A torn pair needs thread t+i to commit its value store between two of thread t's loads that are issued back-to-back. That never happens on real hardware, and for i < 32 the warp is converged anyway."

**Answer:**
- (i) Under PTX the reads and writes of a slot in one step are unordered conflicting plain accesses. That is a data race whatever the reduction's algebra.
- (ii) Monotonicity covers consistent pairs only. Value and index are separate accesses (`LDS` and `LDS.64`, `STS` and `STS.64`), and the new-value/old-index tear yields a wrong `out[m]` (section 4).
- (iii) The same binary gave 61/256 mismatched indices under racecheck's legal schedule against 0 natively. With random floats (no ties) only a torn pair can change the argmax, so racecheck's schedule apparently produced one. This is an inference: the hazard listing is truncated and does not show the tear directly.
- (iv) The two-sided perturbation forces the tear.

**Concession:** a one-sided delay (mode 1) is not expected to produce wrong output. If the coordinator's run confirms that, the dossier should state plainly that the tear needs two threads to be mis-timed, and that natively it is a latent race whose manifestation needs a schedule like racecheck's or mode 2's.

## 8. Results: TO BE RUN

| run | result |
|---|---|
| native `repro`, `repro_fixed` | TO BE RUN |
| `repro_perturb`: mode 0 / mode 1 (writer-side only) / mode 2 (writer + reader) | TO BE RUN |
| cuVein scalar-clock on `repro` and `repro_fixed` | TO BE RUN |
| racecheck on `repro` (and on `repro_fixed`, optional) | TO BE RUN |

## Ancestry

- Not copied from the PointNet++ FPS lineage. The kernel was written in this repository in March 2020 (`06d9038` "fps kernel", rusty1s), with a stride-doubling in-place reduction instead of the PointNet++ `__update` tree. Its loop structure (barrier at the top of each sampling iteration, L28, and a barrier before the final read, L60) does **not** have the PointNet++ cross-iteration `dists_i[0]` race.
- It shares its reduction code shape with this repository's own `nearest_cuda.cu`, fixed in `a5abfee`. Count it as a separate bug pattern in the paper.
- `git grep -n "[thread_idx + i]" e9a855c2 -- "*.cu"` finds only `fps_cuda.cu` L54-L56: no other CUDA file at the pinned commit uses this in-place loop.
